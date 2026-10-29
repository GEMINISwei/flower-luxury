import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr
from sqlalchemy import select

from modules.line_collection import model, service
from modules.line_collection.config import LineSettings
from modules.line_collection.rules import fingerprint
from modules.line_collection.schema import GroupUpdate
from modules.product_drafts import photos, review, storage
from modules.product_drafts.model import MessageTable
from modules.product_drafts.schema import VersionRequest
from modules.product_drafts.service import get_draft, get_draft_list
from shared.db.session import active_session, session_scope
from shared.http.errors import LangException
from shared.jobs.model import JobTable
from tests.modules.line_collection.helpers import BASE, body, event
from tests.modules.line_collection.test_rules import SECRET, signature
from tests.modules.product_drafts.helpers import ACTOR, image_bytes
from tests.modules.product_drafts.test_integration import prepared_draft

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
SETTINGS = LineSettings(
        line_channel_secret=SecretStr(SECRET), line_channel_access_token=SecretStr("test-token"))


async def receive(*events):
    content = body(events)
    return await service.receive_webhook(content, signature(content), SETTINGS)


async def enable_group():
    await receive(event(event_type="join"))
    group = await model.group_for("group-a")
    assert group is not None
    await service.update_group(str(group.id), GroupUpdate(enabled=True))
    return group


@pytest.fixture(autouse=True)
def settings(monkeypatch, tmp_path):
    from modules.line_collection import jobs
    from modules.products import photos as product_photos

    monkeypatch.setattr(jobs, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(service, "utc_now", lambda: BASE + timedelta(milliseconds=500))
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")


async def test_group_discovery_does_not_require_manual_id(db):
    await receive(event())
    groups = await service.list_groups(limit=20)
    assert groups.total_count == 1
    group = groups.list_data[0]
    assert group.group_id == "group-a" and not group.enabled and group.joined
    assert await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "line_collection.group_name",
    )) is not None


async def test_disabled_group_does_not_collect_content(db):
    await receive(event("text", text="機密原文"))
    assert await active_session().scalar(select(MessageTable.id)) is None
    assert await active_session().scalar(select(model.MessageLinkTable.id)) is None
    jobs = list(await active_session().scalars(select(JobTable)))
    assert all("機密原文" not in str(job.payload) for job in jobs)


async def test_direct_messages_are_ignored(db):
    direct = event().model_copy(update={"source": {"type": "user", "userId": "sender"}})
    await receive(direct)
    assert (await service.list_groups(limit=20)).total_count == 0


async def test_duplicate_webhook_does_not_duplicate_messages(db):
    await enable_group()
    image = event(second=1)
    await receive(image, event("text", event_id="text", message_id="text", second=2))
    await receive(image)
    page = await get_draft_list(limit=20)
    draft = await get_draft(page.list_data[0].id)
    assert len(draft.messages) == 2 and draft.messages[1].text == "原文\n  保留空白  "
    downloads = list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "line_collection.download",
    )))
    assert len(downloads) == 1 and set(downloads[0].payload) == {"link_id"}


async def test_concurrent_redelivery_creates_one_message(db):
    await enable_group()
    await active_session().commit()

    async def send():
        async with session_scope():
            await receive(event(second=1))

    await asyncio.gather(send(), send())
    assert len(list(await active_session().scalars(select(MessageTable)))) == 1


async def test_late_message_is_unassigned(db):
    await enable_group()
    await receive(event(second=3))
    await receive(event("text", event_id="late", message_id="late", second=1))
    row = await active_session().scalar(select(MessageTable).where(MessageTable.kind == "text"))
    assert row is not None and row.draft_id is None


async def test_ingest_failure_rolls_back_receipts_and_jobs(db, monkeypatch):
    await enable_group()
    await active_session().commit()
    monkeypatch.setattr(service, "ingest_message", AsyncMock(side_effect=RuntimeError("failed")))
    with pytest.raises(RuntimeError):
        await receive(event(second=1))
    assert await active_session().scalar(select(model.MessageLinkTable.id)) is None
    assert await active_session().scalar(select(model.EventReceiptTable.id)) is None
    assert await active_session().scalar(select(JobTable.id).where(
        JobTable.task_name == "line_collection.download",
    )) is None


async def test_disable_and_leave_preserve_existing_drafts(db):
    group = await enable_group()
    await receive(event(second=1))
    await service.update_group(str(group.id), GroupUpdate(enabled=False))
    await receive(event("text", event_id="off", message_id="off", second=2))
    await service.update_group(str(group.id), GroupUpdate(enabled=True))
    await receive(event(event_type="leave", event_id="leave", second=4))
    await receive(event("text", event_id="after-leave", message_id="after", second=5))
    assert len(list(await active_session().scalars(select(MessageTable)))) == 1
    assert (await get_draft_list(limit=20)).total_count == 1
    group = await model.group_for("group-a")
    assert group is not None and not group.joined and not group.enabled


async def test_left_group_cannot_be_enabled(db):
    group = await enable_group()
    await receive(event(event_type="leave", event_id="leave", second=4))
    with pytest.raises(LangException) as error:
        await service.update_group(str(group.id), GroupUpdate(enabled=True))
    assert error.value.status_code == 409


async def test_unsend_removes_content_and_blocks_redelivery(db):
    await enable_group()
    original = event(second=1)
    await receive(original)
    link = await active_session().scalar(select(model.MessageLinkTable))
    assert link is not None and link.message_id is not None
    result = await photos.complete_photo(str(link.message_id), image_bytes(), "original.png")
    assert result.photo is not None
    path = (await photos.read_photo(result.photo.id, original=True)).path
    await receive(event(event_type="unsend", event_id="unsend", second=2))
    assert await active_session().scalar(select(MessageTable.id)) is None
    assert path.exists()
    assert await active_session().scalar(select(JobTable.id).where(
        JobTable.task_name == "product_drafts.cleanup",
    )) is not None
    await receive(original.model_copy(update={"webhookEventId": "different-delivery"}))
    assert await active_session().scalar(select(MessageTable.id)) is None


async def test_unsend_before_message_prevents_collection(db):
    await enable_group()
    await receive(event(event_type="unsend", event_id="unsend", second=2))
    await receive(event(second=1))
    assert await active_session().scalar(select(MessageTable.id)) is None


async def test_unsend_after_approval_requires_manual_review(db, monkeypatch):
    group = await enable_group()
    draft = await prepared_draft()
    approval = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    link = model.MessageLinkTable(group_id=group.id,
                                 fingerprint=fingerprint("group-a", "approved").value,
                                 external_id="approved", draft_id=draft.id,
                                 expires_at=group.created_at + timedelta(days=30))
    active_session().add(link)
    await active_session().flush()
    await receive(event(event_type="unsend", event_id="unsend", message_id="approved", second=2))
    group = await model.group_for("group-a")
    assert group is not None and group.review_product_id == approval.product_id


async def test_unsend_after_moving_and_approval_requires_manual_review(db):
    from modules.brands.public import BrandTable
    from modules.product_drafts import messages
    from modules.product_drafts import service as drafts
    from modules.product_drafts.schema import DraftFields, DraftUpdate, MessageMove

    group = await enable_group()
    await receive(event(second=1))
    await receive(event("text", event_id="text", message_id="text", second=2))
    await receive(event(event_id="image-b", message_id="image-b", second=3))
    first = await model.message_link(fingerprint("group-a", "message-a").value)
    second = await model.message_link(fingerprint("group-a", "image-b").value)
    assert first is not None and second is not None
    assert first.message_id and first.draft_id and second.message_id and second.draft_id
    source = await get_draft(first.draft_id)
    target = await get_draft(second.draft_id)
    await messages.move_message(str(first.message_id), MessageMove(
        target_draft_id=target.id, target_version=target.version, source_version=source.version,
    ), ACTOR)
    await photos.complete_photo(str(first.message_id), image_bytes(), "a.png")
    await photos.complete_photo(str(second.message_id), image_bytes(), "b.png")
    target = await get_draft(target.id)
    brand = await BrandTable.create({"name": "brand", "is_active": True})
    target = await drafts.update_draft(target.id, DraftUpdate(
        version=target.version, fields=DraftFields(
            name="商品", brand_id=str(brand["id"]), category="包包", cost_price=3000,
        ),
    ), ACTOR)
    result = await review.approve_draft(target.id, VersionRequest(version=target.version), ACTOR)
    await receive(event(event_type="unsend", event_id="unsend", second=4))
    group = await model.group_for("group-a")
    assert group is not None and group.review_product_id == result.product_id
