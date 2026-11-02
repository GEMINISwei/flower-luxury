import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from modules.line_collection import jobs, model, service, transport
from modules.line_collection.schema import GroupUpdate
from modules.product_drafts import model as drafts
from modules.product_drafts import review
from modules.product_drafts.schema import VersionRequest
from modules.product_drafts.service import get_draft, get_draft_list
from shared.db.session import active_session, session_scope
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.line_collection.helpers import BASE, event
from tests.modules.line_collection.test_integration import SETTINGS, enable_group, receive
from tests.modules.line_collection.test_integration import settings as settings
from tests.modules.product_drafts.helpers import ACTOR

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def message(kind="image", *, second=1, text="說明", group="group-a"):
    key = f"{group}-{second}-{kind}"
    return event(kind, second=second, text=text, event_id=key, message_id=key, group=group)


async def command(text, second, *, reply=None):
    item = message("text", text=text, second=second)
    if reply:
        item = item.model_copy(update={"replyToken": reply})
    return await receive(item)


async def group_info():
    return (await service.list_groups()).list_data[0]


async def test_batch_requires_start_and_first_image(db):
    await receive(event(event_type="join"))
    group = await model.group_for("group-a")
    assert group is not None
    await service.update_group(str(group.id), GroupUpdate(enabled=True))
    await receive(message(second=1), message("text", second=2))
    assert (await get_draft_list(limit=20)).total_count == 0
    await command("/start", 3)
    await receive(message("text", second=4))
    assert await active_session().scalar(select(drafts.MessageTable.id)) is None
    await receive(message(second=5))
    assert (await get_draft_list(limit=20)).total_count == 1
    assert await active_session().scalar(select(drafts.MessageTable.id).where(
        drafts.MessageTable.draft_id.is_(None))) is None


async def test_batch_groups_products_and_closes_last_draft(db):
    await enable_group()
    await receive(message(second=1), message(second=2), message("text", second=3),
                  message("text", second=4), message(second=5), message("text", second=6))
    page = await get_draft_list(limit=20)
    assert page.total_count == 2
    first, last = sorted(page.list_data, key=lambda row: row.received_at)
    assert not first.collecting and last.collecting
    assert len((await get_draft(first.id)).messages) == 4
    await command("/end", 7)
    assert not (await get_draft(last.id)).collecting
    await receive(message(second=8))
    assert (await get_draft_list(limit=20)).total_count == 2
    await command("/start", 9)
    await receive(message("text", second=10), message(second=11))
    assert (await get_draft_list(limit=20)).total_count == 3
    assert len(list(await active_session().scalars(select(drafts.MessageTable)))) == 7


async def test_batch_commands_are_exact_and_idempotent(db):
    await enable_group()
    await command(" /start \n", 1)
    started = (await group_info()).batch_started_at
    await command("/start", 2)
    assert (await group_info()).batch_started_at == started
    await receive(message(second=3), message("text", second=4, text="/end 說明"))
    assert (await group_info()).collecting
    await command("/end", 5)
    await command("/end", 6)
    assert not (await group_info()).collecting
    assert (await get_draft_list(limit=20)).total_count == 1
    await command("/start", 7)
    await command("/end", 8)
    assert (await get_draft_list(limit=20)).total_count == 1


async def test_concurrent_start_creates_one_batch(db):
    await enable_group()
    await command("/end", 1)
    await active_session().commit()

    async def start(second):
        async with session_scope():
            await command("/start", second)

    await asyncio.gather(start(2), start(3))
    await receive(message(second=4), message("text", second=5))
    assert (await get_draft_list(limit=20)).total_count == 1
    assert (await group_info()).collecting


async def test_batch_state_survives_new_session(db):
    await enable_group()
    await active_session().commit()
    async with session_scope():
        await receive(message(second=1))
    async with session_scope():
        await command("/end", 2)
    await receive(message(second=3))
    assert (await get_draft_list(limit=20)).total_count == 1
    assert not (await group_info()).collecting


async def test_late_message_uses_original_product_interval(db):
    await enable_group()
    await receive(message(second=1), message("text", second=2), message(second=5),
                  message("text", second=6))
    await command("/end", 8)
    await command("/start", 9)
    await receive(message(second=10))
    await receive(message("text", second=3, text="晚到的第一件說明"))
    page = await get_draft_list(limit=20)
    first = min(page.list_data, key=lambda row: row.received_at)
    detail = await get_draft(first.id)
    texts = [item.text for item in detail.messages if item.kind == "text"]
    assert texts == ["說明", "晚到的第一件說明"]
    assert not detail.collecting and (await group_info()).issue_count == 0
    assert detail.received_at == BASE + timedelta(seconds=1)


@pytest.mark.parametrize("kind,second", [("image", 3), ("text", 1), ("image", 0)])
async def test_unsafe_late_message_records_batch_issue(db, kind, second):
    await enable_group()
    await receive(message(second=1), message("text", second=2), message(second=5))
    await receive(message(kind, second=second).model_copy(update={"webhookEventId": "late",
        "message": {"id": "late", "type": kind, "text": "晚到內容"}}))
    assert (await get_draft_list(limit=20)).total_count == 2
    # 區間外事件略過, 分界衝突保留原文供人工確認, 不改寫已成立商品.
    assert (await group_info()).issue_count == (0 if second == 0 else 1)
    stored = list(await active_session().scalars(select(drafts.MessageTable)))
    assert len([row for row in stored if row.draft_id]) == 3
    assert len([row for row in stored if row.draft_id is None]) == (0 if second == 0 else 1)
    if second != 0:
        assert next(row for row in stored if row.draft_id is None).external_id == "late"
        assert await active_session().scalar(select(drafts.BufferedEventTable.id).where(
            drafts.BufferedEventTable.status == "issue")) is not None
    assert all("晚到內容" not in str(row.payload) for row in
               await active_session().scalars(select(JobTable)))


async def test_late_text_cannot_split_existing_images(db):
    await enable_group()
    await receive(message(second=1), message(second=4), message("text", second=5))
    await receive(message("text", second=2))
    assert (await group_info()).issue_count == 1
    stored = list(await active_session().scalars(select(drafts.MessageTable)))
    assert len([row for row in stored if row.draft_id]) == 3
    pending = [row for row in stored if row.draft_id is None]
    assert len(pending) == 1 and pending[0].text == "說明"


async def test_discarded_product_is_not_recreated_by_late_message(db):
    await enable_group()
    await receive(message(second=1), message("text", second=2))
    draft = (await get_draft_list(limit=20)).list_data[0]
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    await command("/end", 5)
    await receive(message("text", second=3))
    assert (await get_draft_list(limit=20)).total_count == 0
    assert (await group_info()).issue_count == 1
    pending = list(await active_session().scalars(select(drafts.MessageTable)))
    assert len(pending) == 1 and pending[0].draft_id is None and pending[0].text == "說明"


async def test_out_of_order_command_does_not_rewrite_batch(db):
    await enable_group()
    await receive(message(second=4))
    await command("/end", 2)
    assert (await group_info()).collecting
    assert (await group_info()).issue_count == 1


@pytest.mark.parametrize("stop", ["manual", "disable", "leave"])
async def test_stop_disable_and_leave_close_batch(db, stop):
    group = await enable_group()
    await receive(message(second=1))
    if stop == "manual":
        await service.stop_group(str(group.id))
    elif stop == "disable":
        await service.update_group(str(group.id), GroupUpdate(enabled=False))
    else:
        await receive(event(event_type="leave", event_id="leave", second=2))
    assert not (await group_info()).collecting
    assert not (await get_draft_list(limit=20)).list_data[0].collecting
    await receive(message(second=3))
    assert len(list(await active_session().scalars(select(drafts.MessageTable)))) == 1
    await receive(event(event_type="unsend", message_id="group-a-1-image",
                        event_id="withdraw", second=4))
    assert await active_session().scalar(select(drafts.MessageTable.id)) is None


async def test_groups_have_independent_batches(db):
    await enable_group()
    await receive(message(second=1, group="group-b"))
    group = await model.group_for("group-b")
    assert group is not None
    await service.update_group(str(group.id), GroupUpdate(enabled=True))
    await receive(message(second=2, group="group-b"), message(second=2))
    assert (await get_draft_list(limit=20)).total_count == 1


async def test_reply_failure_preserves_batch_state(db, monkeypatch):
    await enable_group()
    item = message("text", text="/end", second=2).model_copy(update={"replyToken": "reply-secret"})
    await receive(item)
    queued = await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "line_collection.reply"))
    assert queued is not None and "reply-secret" not in str(queued.payload)
    await active_session().commit()
    send = AsyncMock(side_effect=transport.LineTransportError())
    monkeypatch.setattr(jobs.transport, "reply_message", send)
    await jobs.send_reply(Job.model_validate(queued))
    assert not (await group_info()).collecting
    assert (await group_info()).reply_failed
    await receive(item)
    send.assert_awaited_once()
    assert SETTINGS.configured


@pytest.mark.parametrize("text", ["/start", "/end"])
@pytest.mark.parametrize("previously_enabled", [False, True])
async def test_disabled_group_commands_do_not_change_state_or_enqueue_replies(
    db, text, previously_enabled,
):
    if previously_enabled:
        group = await enable_group()
        await receive(message(second=1))
        await service.update_group(str(group.id), GroupUpdate(enabled=False))
    else:
        await receive(event(event_type="join"))
    before = await group_info()
    batches_before = list(await active_session().scalars(select(drafts.BatchTable.id)))
    jobs_before = list(await active_session().scalars(select(JobTable.id)))
    receipts_before = list(await active_session().scalars(select(model.EventReceiptTable.id)))
    result = await command(text, 5, reply="ignored-reply-token")
    assert result.accepted == 0
    assert (await group_info()) == before
    assert list(await active_session().scalars(select(drafts.BatchTable.id))) == batches_before
    assert list(await active_session().scalars(select(JobTable.id))) == jobs_before
    assert list(await active_session().scalars(
        select(model.EventReceiptTable.id))) == receipts_before
    assert await active_session().scalar(select(model.ReplyTable.id)) is None
