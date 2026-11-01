from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from modules.product_drafts import collection, model, review, service
from modules.product_drafts.schema import DraftFields, DraftUpdate, VersionRequest
from shared.http.errors import LangException
from tests.modules.product_drafts.helpers import ACTOR, BASE, ID, incoming
from tests.modules.product_drafts.test_services import ready
from tests.modules.product_drafts.test_services import state as state

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("flag", ["collecting", "processing", "needs_confirmation"])
async def test_approve_unfinished_or_unresolved_draft_is_rejected(state, monkeypatch, flag):
    draft = await ready()
    draft = await service.update_draft(draft.id, DraftUpdate(version=draft.version,
        fields=DraftFields(name="bag", brand_id=ID, category="包包", cost_price=0)), ACTOR)
    row = state[model.DraftTable][draft.id]
    row.collecting = False
    setattr(row, flag, True)
    imported = AsyncMock(side_effect=AssertionError("unfinished draft must not import"))
    monkeypatch.setattr(review, "create_imported_product", imported)
    with pytest.raises(LangException) as error:
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert error.value.status_code == 409
    imported.assert_not_awaited()


@pytest.mark.integration
async def test_next_review_uses_oldest_in_scope_and_skips_unfinished_or_resolved_rows(db):
    ids = []
    for second in (1, 2, 3, 4):
        result = await collection.ingest_message(incoming(source=f"source-{second}", second=second))
        assert result.draft_id
        row = await model.get_draft_row(result.draft_id)
        assert row is not None
        row.collecting = False
        ids.append(row.id)
    first = await model.get_draft_row(str(ids[0]))
    assert first is not None
    first.processing = True
    unresolved = await model.get_draft_row(str(ids[1]))
    assert unresolved is not None
    unresolved.needs_confirmation = True
    assert (await service.next_review()).id == str(ids[2])
    assert (await service.next_review(source_key="source-4")).id == str(ids[3])
    assert (await service.next_review(source_key="source-1")).id is None


@pytest.mark.integration
async def test_draft_list_is_oldest_first_across_pages_and_filter(db):
    expected = []
    for second in (5, 1, 3):
        result = await collection.ingest_message(incoming(source=f"group-{second}", second=second))
        assert result.draft_id
        expected.append((second, result.draft_id))
    ids = []
    cursor = None
    for _ in range(3):
        page = await service.get_draft_list(1, cursor=cursor)
        ids.append(page.list_data[0].id)
        cursor = page.next_cursor
    assert ids == [id for _, id in sorted(expected)]
    page = await service.get_draft_list(20, source_key="group-3")
    assert [item.id for item in page.list_data] == [expected[2][1]]


@pytest.mark.integration
async def test_resolve_buffer_issues_moves_text_and_discard_releases_review(db, monkeypatch):
    from uuid import uuid4

    from modules.product_drafts import buffer, messages
    from modules.product_drafts.schema import MessageMove
    from shared.jobs.contracts import Job

    target = await collection.ingest_message(incoming(second=1))
    assert target.draft_id
    row = await model.get_draft_row(target.draft_id)
    assert row is not None
    row.collecting = False
    now = [BASE]
    monkeypatch.setattr(buffer, "utc_now", lambda: now[0])
    await buffer.queue_control("group-a", "start", BASE + timedelta(seconds=2))
    image = await buffer.queue_message(incoming(second=3))
    text = await buffer.queue_message(incoming("text", second=3, text="待確認原文"))
    assert image.message_id and text.message_id
    now[0] += timedelta(minutes=3)
    await buffer.process_buffer(Job(id=uuid4(), task_name="product_drafts.buffer",
                                   payload={"source_key": "group-a"}, attempts=1))
    before = await service.get_draft(target.draft_id)
    assert before.needs_confirmation
    issues = await messages.get_unassigned_messages(20, source_key="group-a", issues_only=True)
    assert {item.id for item in issues.list_data} == {image.message_id, text.message_id}
    await messages.move_message(text.message_id, MessageMove(
        target_draft_id=before.id, target_version=before.version), ACTOR)
    assert (await service.get_draft(before.id)).needs_confirmation
    await messages.discard_legacy_message(image.message_id)
    after = await service.get_draft(before.id)
    assert not after.needs_confirmation
    assert any(message.text == "待確認原文" for message in after.messages)


@pytest.mark.integration
async def test_withdrawing_all_buffer_issues_releases_source_without_another_message(
    db, monkeypatch,
):
    from uuid import uuid4

    from modules.product_drafts import buffer, messages
    from shared.jobs.contracts import Job

    target = await collection.ingest_message(incoming(second=1))
    assert target.draft_id
    row = await model.get_draft_row(target.draft_id)
    assert row is not None
    row.collecting = False
    now = [BASE]
    monkeypatch.setattr(buffer, "utc_now", lambda: now[0])
    await buffer.queue_control("group-a", "start", BASE + timedelta(seconds=2))
    await buffer.queue_message(incoming(second=3, external_id="withdraw-image"))
    await buffer.queue_message(incoming("text", second=3, text="稍後撤回",
                                        external_id="withdraw-text"))
    now[0] += timedelta(minutes=3)
    await buffer.process_buffer(Job(id=uuid4(), task_name="product_drafts.buffer",
                                   payload={"source_key": "group-a"}, attempts=1))
    assert (await service.get_draft(target.draft_id)).needs_confirmation
    await messages.withdraw_message("group-a", "withdraw-text")
    assert (await service.get_draft(target.draft_id)).needs_confirmation
    await messages.withdraw_message("group-a", "withdraw-image")
    assert not (await service.get_draft(target.draft_id)).needs_confirmation
