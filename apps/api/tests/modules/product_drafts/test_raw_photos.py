from io import BytesIO
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import UploadFile

from modules.product_drafts import model, photos, raw_photos, rounds, service, storage
from modules.product_drafts.schema import VersionRequest
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from tests.modules.product_drafts.helpers import ACTOR, image_bytes, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(db, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")


async def test_receiving_original_does_not_render_or_overwrite(monkeypatch):
    render = AsyncMock(side_effect=AssertionError("not finalized"))
    monkeypatch.setattr(raw_photos, "run_process", render)
    message = await rounds.receive_message(incoming())
    content = image_bytes()
    first = await raw_photos.save_original(message.message_id, content, "original.png")
    assert first.photo is not None and first.photo.status == "stored"
    photo = await model.get_photo_row(first.photo.id)
    assert photo is not None and photo.original_key is not None and photo.display_key is None
    path = storage._path(photo.original_key)
    assert path.read_bytes() == content
    await raw_photos.save_original(message.message_id, b"different", "other.jpg")
    assert path.read_bytes() == content
    render.assert_not_awaited()


async def test_render_runs_only_after_finalization_and_is_idempotent():
    message = await rounds.receive_message(incoming())
    original = await raw_photos.save_original(message.message_id, image_bytes(), "original.png")
    assert original.photo is not None
    current = await rounds.current_collection("group-a")
    completed = await rounds.complete_collection(current.id)
    draft = await service.get_draft(completed.draft_ids[0])
    job = Job(id=uuid4(), task_name="product_drafts.render_photo", attempts=1,
              payload={"photo_id": original.photo.id, "draft_id": draft.id})
    await raw_photos.render_photo(job)
    assert (await service.get_draft(draft.id)).photos[0].status == "stored"
    await rounds.finalize_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    await raw_photos.render_photo(job)
    photo = await model.get_photo_row(original.photo.id)
    assert photo is not None and photo.status == "ready"
    keys = (photo.original_key, photo.display_key)
    await raw_photos.render_photo(job)
    assert (photo.original_key, photo.display_key) == keys
    assert not (await service.get_draft(draft.id)).processing


async def test_finalization_rejects_failed_original_and_oversized_content():
    message = await rounds.receive_message(incoming())
    with pytest.raises(LangException):
        await raw_photos.save_original(message.message_id, b"x" * (15 * 1024 * 1024 + 1), None)
    current = await rounds.current_collection("group-a")
    completed = await rounds.complete_collection(current.id)
    draft = await service.get_draft(completed.draft_ids[0])
    with pytest.raises(LangException):
        await rounds.finalize_draft(draft.id, VersionRequest(version=draft.version), ACTOR)


async def test_manual_upload_before_finalization_only_saves_original(monkeypatch):
    message = await rounds.receive_message(incoming("text", text="待補圖"))
    current = await rounds.current_collection("group-a")
    await rounds.complete_collection(current.id)
    from modules.product_drafts import issues
    from modules.product_drafts.schema import ResolveIssue

    issue = (await issues.get_issues(20)).list_data[0]
    await issues.resolve_issue(issue.id, ResolveIssue(action="new"), ACTOR)
    draft = await service.get_draft(await model.message_draft_id(message.message_id))
    render = AsyncMock(side_effect=AssertionError("must wait for finalization"))
    monkeypatch.setattr(raw_photos, "run_process", render)
    result = await photos.upload_photos(draft.id, draft.version,
        [UploadFile(BytesIO(image_bytes()), filename="manual.png")], ACTOR)
    assert result.photos[0].status == "stored" and result.prefill_revision == 0
    render.assert_not_awaited()
