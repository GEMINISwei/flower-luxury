import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from modules.line_collection import jobs, transport
from modules.line_collection.config import LineSettings
from modules.line_collection.schema import DownloadedImage, DownloadTarget, GroupName
from modules.product_drafts.schema import PhotoCompletion
from shared.jobs.contracts import Job
from tests.modules.line_collection.helpers import BASE

pytestmark = pytest.mark.asyncio


def job(attempts=1):
    return Job(id=uuid4(), task_name="line_collection.download",
               payload={"link_id": str(uuid4())}, attempts=attempts)


@pytest.fixture
def download(monkeypatch):
    target = DownloadTarget(message_id=str(uuid4()), external_id="line-image")
    fetch = AsyncMock(return_value=DownloadedImage(content=b"image"))
    finish = AsyncMock(return_value=PhotoCompletion(accepted=True))
    monkeypatch.setattr(jobs.model, "download_target", AsyncMock(return_value=target))
    monkeypatch.setattr(jobs.model, "clear_download_id", AsyncMock())
    monkeypatch.setattr(jobs, "release_connection", AsyncMock())
    monkeypatch.setattr(jobs, "get_settings", lambda: LineSettings(
        line_channel_secret=SecretStr("secret"), line_channel_access_token=SecretStr("token"),
    ))
    monkeypatch.setattr(jobs.transport, "download_image", fetch)
    monkeypatch.setattr(jobs, "save_original", finish)
    return fetch, finish


async def test_image_download_retry_preserves_message_grouping(download):
    fetch, finish = download
    fetch.side_effect = [transport.LineTransportError(), DownloadedImage(content=b"image")]
    with pytest.raises(transport.LineTransportError):
        await jobs.download_photo(job())
    finish.assert_not_awaited()
    await jobs.download_photo(job(attempts=2))
    assert finish.await_args.args[1] == b"image" and finish.await_count == 1


async def test_final_download_failure_marks_photo_failed(download, monkeypatch):
    fetch, finish = download
    fetch.side_effect = transport.LineTransportError()
    failed = AsyncMock(return_value=PhotoCompletion(accepted=True))
    monkeypatch.setattr(jobs, "mark_photo_failed", failed)
    await jobs.download_photo(job(attempts=3))
    failed.assert_awaited_once()
    finish.assert_not_awaited()


async def test_download_cancellation_propagates(download):
    fetch, finish = download
    fetch.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await jobs.download_photo(job())
    finish.assert_not_awaited()


async def test_deleted_message_is_not_downloaded(download, monkeypatch):
    fetch, finish = download
    monkeypatch.setattr(jobs.model, "download_target", AsyncMock(return_value=None))
    await jobs.download_photo(job())
    fetch.assert_not_awaited()
    finish.assert_not_awaited()


async def test_download_rejects_oversized_content(monkeypatch):
    def reply(request):
        assert request.url.host == "api-data.line.me"
        assert request.headers["authorization"] == "Bearer token"
        return httpx.Response(200, content=b"x" * (15 * 1024 * 1024 + 1))

    client = httpx.AsyncClient(transport=httpx.MockTransport(reply))
    monkeypatch.setattr(transport, "LineClient", lambda: client)
    with pytest.raises(transport.LineTransportError):
        await transport.download_image("message", "token")


async def test_group_name_failure_keeps_group_pending(monkeypatch):
    group = SimpleNamespace(id=uuid4(), group_id="group", name=None, enabled=False,
                            joined=True, created_at=BASE, expires_at=BASE + timedelta(days=30))
    monkeypatch.setattr(jobs.model, "get_group", AsyncMock(return_value=group))
    monkeypatch.setattr(jobs.model, "save_group_name", AsyncMock())
    monkeypatch.setattr(jobs, "release_connection", AsyncMock())
    monkeypatch.setattr(jobs, "get_settings", lambda: LineSettings(
        line_channel_secret=SecretStr("secret"), line_channel_access_token=SecretStr("token"),
    ))
    monkeypatch.setattr(jobs.transport, "group_name",
                        AsyncMock(side_effect=transport.LineTransportError()))
    await jobs.refresh_group_name(job(attempts=3).model_copy(update={
        "payload": {"group_id": str(group.id)},
    }))
    assert not group.enabled and group.name is None


@pytest.mark.parametrize("status", [401, 404, 429, 500, 302])
async def test_transport_errors_do_not_expose_credentials(monkeypatch, status):
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _request: httpx.Response(status, text="private token"),
    ))
    monkeypatch.setattr(transport, "LineClient", lambda: client)
    with pytest.raises(transport.LineTransportError) as error:
        await transport.download_image("message", "private-token")
    assert "private" not in str(error.value)


async def test_transport_preserves_image_bytes_and_reads_group_name(monkeypatch):
    def reply(request):
        if request.url.host == "api-data.line.me":
            return httpx.Response(200, content=b"original-image",
                                  headers={"content-type": "image/png"})
        assert request.url.path == "/v2/bot/group/group-a/summary"
        return httpx.Response(200, json={"groupName": "精品群組"})

    monkeypatch.setattr(transport, "LineClient", lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(reply),
    ))
    assert (await transport.download_image("message", "token")).content == b"original-image"
    assert (await transport.group_name("group-a", "token")).name == "精品群組"


async def test_group_name_success_does_not_enable_collection(monkeypatch):
    group = SimpleNamespace(id=uuid4(), group_id="group", name=None, enabled=False)
    save = AsyncMock()
    monkeypatch.setattr(jobs.model, "get_group", AsyncMock(return_value=group))
    monkeypatch.setattr(jobs.model, "save_group_name", save)
    monkeypatch.setattr(jobs, "release_connection", AsyncMock())
    monkeypatch.setattr(jobs, "get_settings", lambda: LineSettings(
        line_channel_secret=SecretStr("secret"), line_channel_access_token=SecretStr("token"),
    ))
    monkeypatch.setattr(jobs.transport, "group_name",
                        AsyncMock(return_value=GroupName(name="精品群組")))
    await jobs.refresh_group_name(job().model_copy(update={"payload": {"group_id": str(group.id)}}))
    assert not group.enabled
    save.assert_awaited_once_with(str(group.id), "精品群組")
