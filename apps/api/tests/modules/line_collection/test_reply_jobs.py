import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from modules.line_collection import jobs, transport
from modules.line_collection.config import LineSettings
from shared.jobs.contracts import Job
from tests.modules.line_collection.helpers import BASE

pytestmark = pytest.mark.asyncio


@pytest.fixture
def reply(monkeypatch):
    row = SimpleNamespace(id=uuid4(), group_id=uuid4(), reply_token="short-lived-token",
                          text="已停止收集", expires_at=BASE + timedelta(seconds=50))
    group = SimpleNamespace(reply_failed=False, collecting=False, enabled=True)
    session = SimpleNamespace(get=AsyncMock(return_value=row), delete=AsyncMock())
    send = AsyncMock()
    lookup = AsyncMock(return_value=group)
    monkeypatch.setattr(jobs, "active_session", lambda: session)
    monkeypatch.setattr(jobs, "utc_now", lambda: BASE)
    monkeypatch.setattr(jobs.model, "get_group", lookup)
    monkeypatch.setattr(jobs.transport, "reply_message", send)
    monkeypatch.setattr(jobs, "get_settings", lambda: LineSettings(
        line_channel_secret=SecretStr("secret"), line_channel_access_token=SecretStr("token")))
    work = Job(id=uuid4(), task_name="line_collection.reply", attempts=1,
               payload={"reply_id": str(row.id)})
    return SimpleNamespace(row=row, group=group, session=session,
                           send=send, lookup=lookup, job=work)


@pytest.mark.parametrize("outcome", ["success", "failure", "expired"])
async def test_reply_lifecycle_cleans_tokens_and_preserves_collection_state(reply, outcome):
    reply.group.reply_failed = True
    if outcome == "failure":
        reply.send.side_effect = transport.LineTransportError()
    elif outcome == "expired":
        reply.row.expires_at = BASE
    await jobs.send_reply(reply.job)
    assert reply.group.reply_failed == (outcome != "success")
    assert not reply.group.collecting and reply.group.enabled
    reply.session.delete.assert_awaited_once_with(reply.row)
    if outcome == "expired":
        reply.send.assert_not_awaited()
    else:
        reply.send.assert_awaited_once_with("short-lived-token", "已停止收集", "token")
    assert "short-lived-token" not in str(reply.job.payload)


async def test_completed_reply_job_is_safe_to_run_again(reply):
    reply.session.get.return_value = None
    await jobs.send_reply(reply.job)
    reply.send.assert_not_awaited()
    reply.session.delete.assert_not_awaited()
    reply.lookup.assert_not_awaited()


async def test_expired_reply_cleanup_never_sends_a_message(reply):
    reply.row.expires_at = BASE
    await jobs.expire_reply(reply.job)
    assert reply.group.reply_failed
    reply.session.delete.assert_awaited_once_with(reply.row)
    reply.send.assert_not_awaited()
    reply.session.get.return_value = None
    await jobs.expire_reply(reply.job)
    assert reply.session.delete.await_count == 1


async def test_cancelled_reply_keeps_token_for_expiry_cleanup(reply):
    reply.send.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await jobs.send_reply(reply.job)
    reply.session.delete.assert_not_awaited()
    await jobs.expire_reply(reply.job)
    reply.session.delete.assert_awaited_once_with(reply.row)
