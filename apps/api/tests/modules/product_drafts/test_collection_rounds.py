import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from modules.product_drafts import issues, model, prefill, raw_photos, rounds, service, storage
from modules.product_drafts.schema import ResolveIssue, VersionRequest
from shared.db.session import active_session, session_scope
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import ACTOR, image_bytes, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(db, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")


async def receive_pair(source="group-a"):
    image = await rounds.receive_message(incoming(source=source, second=1))
    await rounds.receive_message(incoming("text", source=source, second=3, text="原始說明"))
    current = await rounds.current_collection(source)
    assert current.id is not None
    return image, current


async def completed_draft():
    image, current = await receive_pair()
    result = await rounds.complete_collection(current.id)
    await raw_photos.save_original(image.message_id, image_bytes(), "original.png")
    return await service.get_draft(result.draft_ids[0])


async def test_receipt_persists_without_grouping_or_ai():
    image, current = await receive_pair()
    assert current.message_count == 2 and image.message_id is not None
    assert (await service.get_draft_list(20)).total_count == 0
    assert not list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name.in_(["product_drafts.prefill", "product_drafts.render_photo"]))))


async def test_complete_collection_is_idempotent_and_does_not_finalize():
    _, current = await receive_pair()
    first = await rounds.complete_collection(current.id)
    second = await rounds.complete_collection(current.id)
    assert first.draft_ids == second.draft_ids and len(first.draft_ids) == 1
    draft = await service.get_draft(first.draft_ids[0])
    assert draft.requires_finalization and not draft.finalized and draft.prefill_revision == 0
    assert len(draft.messages) == 2


async def test_new_receipts_are_not_closed_by_retrying_old_completion():
    _, current = await receive_pair()
    await rounds.complete_collection(current.id)
    await rounds.receive_message(incoming(second=5, external_id="next-round"))
    next_round = await rounds.current_collection("group-a")
    assert next_round.id != current.id and next_round.message_count == 1
    await rounds.complete_collection(current.id)
    assert (await rounds.current_collection("group-a")).id == next_round.id


async def test_concurrent_completion_creates_one_set_of_drafts():
    _, current = await receive_pair()
    await active_session().commit()

    async def finish():
        async with session_scope():
            return await rounds.complete_collection(current.id)

    first, second = await asyncio.gather(finish(), finish())
    assert first.draft_ids == second.draft_ids and len(first.draft_ids) == 1
    assert (await service.get_draft_list(20)).total_count == 1


async def test_concurrent_receipt_and_completion_preserve_every_message():
    _, current = await receive_pair()
    await active_session().commit()

    async def finish():
        async with session_scope():
            await rounds.complete_collection(current.id)

    async def receive():
        async with session_scope():
            await rounds.receive_message(incoming(second=5, external_id="concurrent"))

    await asyncio.gather(finish(), receive())
    rows = list(await active_session().scalars(select(model.MessageTable)))
    assert len(rows) == 3 and all(row.collection_id is not None for row in rows)


async def test_late_message_requires_manual_attachment_before_finalization():
    _, current = await receive_pair()
    completed = await rounds.complete_collection(current.id)
    draft = await service.get_draft(completed.draft_ids[0])
    late = await rounds.receive_message(incoming("text", second=2, text="晚到內容"))
    assert late.unassigned
    assert len((await service.get_draft(draft.id)).messages) == 2
    issue = (await issues.get_issues(20)).list_data[0]
    await issues.resolve_issue(issue.id, ResolveIssue(action="attach", target_draft_id=draft.id,
                               target_version=draft.version), ACTOR)
    updated = await service.get_draft(draft.id)
    texts = [item.text for item in updated.messages if item.kind == "text"]
    assert texts == ["晚到內容", "原始說明"]
    assert updated.prefill_revision == 0 and updated.requires_finalization


async def test_finalization_requires_saved_originals():
    _, current = await receive_pair()
    completed = await rounds.complete_collection(current.id)
    draft = await service.get_draft(completed.draft_ids[0])
    with pytest.raises(LangException) as error:
        await rounds.finalize_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert error.value.status_code == 409


async def test_finalization_locks_snapshot_and_schedules_once(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-key")
    draft = await completed_draft()
    first = await rounds.finalize_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    second = await rounds.finalize_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert first.finalized and not first.requires_finalization and first.version == second.version
    row = await model.get_draft_row(draft.id)
    assert row is not None
    snapshot = deepcopy(row.finalized_snapshot)
    queued = list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name.in_(["product_drafts.prefill", "product_drafts.render_photo"]))))
    assert len(queued) == 2 and all(set(job.payload) <= {"draft_id", "photo_id", "revision"}
                                    for job in queued)
    await rounds.receive_message(incoming("text", second=2, text="定稿後晚到"))
    assert row.finalized_snapshot == snapshot
    assert len((await service.get_draft(draft.id)).messages) == 2
    issue = (await issues.get_issues(20)).list_data[0]
    with pytest.raises(LangException) as error:
        await issues.resolve_issue(issue.id, ResolveIssue(action="attach", target_draft_id=draft.id,
                                   target_version=first.version), ACTOR)
    assert error.value.status_code == 409


async def test_unfinalized_draft_cannot_be_approved():
    draft = await completed_draft()
    from modules.product_drafts import review

    with pytest.raises(LangException) as error:
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert error.value.status_code == 409


async def test_unassigned_message_can_create_a_new_group():
    message = await rounds.receive_message(incoming("text", text="先到的文字"))
    current = await rounds.current_collection("group-a")
    completed = await rounds.complete_collection(current.id)
    assert completed.draft_ids == []
    issue = (await issues.get_issues(20)).list_data[0]
    await issues.resolve_issue(issue.id, ResolveIssue(action="new"), ACTOR)
    draft = await service.get_draft(await model.message_draft_id(message.message_id))
    assert draft.requires_finalization and draft.messages[0].text == "先到的文字"


async def test_message_can_be_split_before_finalization():
    draft = await completed_draft()
    text = next(message for message in draft.messages if message.kind == "text")
    created = await rounds.split_message(text.id, VersionRequest(version=draft.version), ACTOR)
    assert created.id != draft.id and created.requires_finalization
    assert [message.id for message in created.messages] == [text.id]
    source = await service.get_draft(draft.id)
    assert len(source.messages) == 1 and source.requires_finalization


async def test_prefill_reads_frozen_input_and_unknown_result_is_not_repeated(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-key")
    draft = await completed_draft()
    finalized = await rounds.finalize_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    await active_session().execute(update(model.MessageTable).where(
        model.MessageTable.draft_id == UUID(draft.id),
        model.MessageTable.kind == "text",
    ).values(text="不可當成新輸入"))
    await active_session().commit()
    sent = []

    async def generate(prompt, content, schema):
        sent.append(content)
        raise asyncio.CancelledError

    generate_mock = AsyncMock(side_effect=generate)
    monkeypatch.setattr(prefill, "generate_prefill", generate_mock)
    job = Job(id=uuid4(), task_name="product_drafts.prefill", attempts=1,
              payload={"draft_id": draft.id, "revision": finalized.prefill_revision})
    async with session_scope():
        with pytest.raises(asyncio.CancelledError):
            await prefill.run_prefill(job)
    async with session_scope():
        state = await service.get_draft(draft.id)
        assert state.prefill_status == "unknown"
        await prefill.run_prefill(job)
    assert len(sent) == 1 and "原始說明" in sent[0] and "不可當成新輸入" not in sent[0]
    generate_mock.assert_awaited_once()
