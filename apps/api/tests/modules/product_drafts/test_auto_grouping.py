from datetime import timedelta

import pytest
from sqlalchemy import select

from modules.brands.public import BrandTable
from modules.product_drafts import collection, model, pending, raw_photos, review, service, storage
from modules.product_drafts.schema import DraftFields, DraftUpdate, VersionRequest
from shared.db.session import active_session
from shared.http.errors import LangException
from shared.jobs.model import JobTable
from shared.time import utc_now
from tests.modules.product_drafts.helpers import ACTOR, BASE, image_bytes, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(db, tmp_path, monkeypatch):
    from modules.products import photos as product_photos

    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")


async def receive(kind="image", *, second, text=None, source="group-a"):
    return await collection.ingest_message(incoming(
        kind, source=source, second=second, text=text if kind == "text" else None))


async def two_drafts(source="group-a"):
    first = await receive(second=1, source=source)
    await receive("text", second=2, text="A 說明", source=source)
    second = await receive(second=5, source=source)
    assert first.draft_id and second.draft_id and first.draft_id != second.draft_id
    return first.draft_id, second.draft_id


async def interval_of(draft_id):
    found = await model.interval_for(draft_id)
    assert found is not None
    return found


async def jobs(task_name):
    return list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == task_name)))


async def test_receipt_groups_by_original_time_without_commands():
    first, second = await two_drafts()
    await receive("text", second=6, text="B 說明")
    later_text = await receive("text", second=9, text="C 說明")
    assert later_text.draft_id == second and not later_text.pending
    # 晚到但仍屬收集中商品的圖片, 依原始時間切出新商品並帶走較晚的文字.
    late_image = await receive(second=7)
    assert late_image.draft_id not in {first, second} and not late_image.pending
    a, b = await service.get_draft(first), await service.get_draft(second)
    c = await service.get_draft(late_image.draft_id)
    assert not a.collecting and not b.collecting and c.collecting
    assert [(item.kind, item.text) for item in a.messages] == [("image", None), ("text", "A 說明")]
    assert [(item.kind, item.text) for item in b.messages] == [("image", None), ("text", "B 說明")]
    assert [(item.kind, item.text) for item in c.messages] == [("image", None), ("text", "C 說明")]


async def test_text_outside_any_interval_is_skipped():
    result = await receive("text", second=1, text="閒聊")
    assert result.message_id is None and result.draft_id is None
    assert not list(await active_session().scalars(select(model.MessageTable)))


async def test_closing_draft_schedules_prefill_once(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    first, _ = await two_drafts()
    closed = await service.get_draft(first)
    assert closed.prefill_revision == 1 and len(await jobs("product_drafts.prefill")) == 1
    late = await receive("text", second=3, text="補充")
    closed = await service.get_draft(first)
    await pending.accept_message(first, late.message_id, VersionRequest(version=closed.version),
                                 ACTOR)
    assert (await service.get_draft(first)).prefill_revision == 1
    assert len(await jobs("product_drafts.prefill")) == 1


async def test_saved_original_schedules_render_without_finalization():
    image = await receive(second=1)
    saved = await raw_photos.save_original(image.message_id, image_bytes(), "original.png")
    assert saved.photo is not None and saved.photo.status == "stored"
    queued = await jobs("product_drafts.render_photo")
    assert [job.payload["photo_id"] for job in queued] == [saved.photo.id]


async def test_complete_collecting_draft_closes_interval():
    image = await receive(second=1)
    await receive("text", second=2, text="唯一商品")
    draft = await service.get_draft(image.draft_id)
    with pytest.raises(LangException) as stale:
        await collection.complete_draft(draft.id, VersionRequest(version=draft.version + 1), ACTOR)
    assert stale.value.status_code == 409
    completed = await collection.complete_draft(draft.id, VersionRequest(version=draft.version),
                                                ACTOR)
    assert not completed.collecting and completed.prefill_revision == 1
    again = await collection.complete_draft(draft.id, VersionRequest(version=completed.version),
                                            ACTOR)
    assert again.version == completed.version
    late = await receive("text", second=3, text="完成後才到")
    assert late.draft_id == draft.id and late.pending
    fresh = await collection.ingest_message(incoming().model_copy(
        update={"occurred_at": utc_now() + timedelta(minutes=1)}))
    assert fresh.draft_id not in {None, draft.id} and not fresh.pending
    assert (await service.get_draft(fresh.draft_id)).collecting


async def test_late_message_becomes_pending_in_matching_interval():
    first, _ = await two_drafts()
    late = await receive("text", second=3, text="晚到說明")
    assert late.draft_id == first and late.pending
    draft = await service.get_draft(first)
    assert [item.text for item in draft.messages if item.kind == "text"] == ["A 說明"]
    assert [item.text for item in draft.pending_messages] == ["晚到說明"]
    listed = {item.id: item for item in (await service.get_draft_list(20)).list_data}
    assert listed[first].pending_count == 1


async def test_late_image_after_text_joins_next_draft_and_moves_its_start():
    first, second = await two_drafts()
    late = await receive(second=3)
    assert late.draft_id == second and not late.pending
    previous, following = await service.get_draft(first), await service.get_draft(second)
    assert len(previous.photos) == 1 and not previous.pending_messages
    assert len(following.photos) == 2 and following.collecting
    assert following.messages[0].id == late.message_id
    assert (await interval_of(first)).ended_at == BASE.replace(second=3)
    assert (await interval_of(second)).started_at == BASE.replace(second=3)
    text = await receive("text", second=4, text="B 說明")
    assert text.draft_id == second and not text.pending


async def test_late_image_moves_later_text_from_previous_to_next_draft():
    first = await receive(second=1)
    await receive("text", second=2, text="A 說明")
    await receive("text", second=4, text="B 說明")
    second = await receive(second=5)
    late = await receive(second=3)
    assert late.draft_id == second.draft_id and not late.pending
    previous = await service.get_draft(first.draft_id)
    following = await service.get_draft(second.draft_id)
    assert [(item.kind, item.text) for item in previous.messages] == [
        ("image", None), ("text", "A 說明")]
    assert [(item.kind, item.text) for item in following.messages] == [
        ("image", None), ("text", "B 說明"), ("image", None)]
    assert following.messages[0].id == late.message_id


async def test_late_image_after_completed_draft_opens_new_draft():
    first = await receive(second=1)
    await receive("text", second=2, text="A 說明")
    draft = await service.get_draft(first.draft_id)
    await collection.complete_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    late = await receive(second=3)
    assert late.draft_id not in {None, first.draft_id} and not late.pending
    assert (await service.get_draft(late.draft_id)).collecting
    assert (await interval_of(first.draft_id)).ended_at == BASE.replace(second=3)
    text = await receive("text", second=4, text="B 說明")
    assert text.draft_id == late.draft_id and not text.pending


async def test_late_image_for_completed_next_draft_is_pending_there():
    first, second = await two_drafts()
    await receive("text", second=6, text="B 說明")
    draft = await service.get_draft(second)
    await collection.complete_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    late = await receive(second=3)
    assert late.draft_id == second and late.pending
    assert not (await service.get_draft(first)).pending_messages


async def test_same_millisecond_message_is_pending_not_assigned():
    image = await receive(second=1)
    await receive("text", second=2, text="A 說明")
    same_as_text = await receive(second=2)
    assert same_as_text.draft_id == image.draft_id and same_as_text.pending
    assert (await service.get_draft(image.draft_id)).collecting
    second = await receive(second=5)
    same_as_image = await receive("text", second=5, text="分界文字")
    assert same_as_image.draft_id == image.draft_id and same_as_image.pending
    assert not (await service.get_draft(second.draft_id)).messages[1:]


async def test_late_message_for_removed_or_missing_interval_is_skipped():
    first, _ = await two_drafts()
    draft = await service.get_draft(first)
    await review.discard_draft(first, VersionRequest(version=draft.version), ACTOR)
    removed = await receive("text", second=3, text="已放棄商品的晚到內容")
    before = await receive(second=0)
    assert removed.message_id is None and before.message_id is None
    stored = list(await active_session().scalars(select(model.MessageTable)))
    assert len(stored) == 1


async def test_accept_and_ignore_pending_message():
    first, _ = await two_drafts()
    text = await receive("text", second=3, text="加入的內容")
    image = await receive(second=2)
    draft = await service.get_draft(first)
    with pytest.raises(LangException) as stale:
        await pending.accept_message(first, text.message_id,
                                     VersionRequest(version=draft.version + 1), ACTOR)
    assert stale.value.status_code == 409
    accepted = await pending.accept_message(first, text.message_id,
                                            VersionRequest(version=draft.version), ACTOR)
    assert "加入的內容" in [item.text for item in accepted.messages]
    assert [item.id for item in accepted.pending_messages] == [image.message_id]
    ignored = await pending.ignore_message(first, image.message_id,
                                           VersionRequest(version=accepted.version), ACTOR)
    assert not ignored.pending_messages and len(ignored.photos) == 1
    assert await model.get_message_row(image.message_id) is None
    with pytest.raises(LangException) as done:
        await pending.accept_message(first, text.message_id,
                                     VersionRequest(version=ignored.version), ACTOR)
    assert done.value.status_code in {404, 409}


async def ready_fields(id):
    brand = await BrandTable.create({"name": "brand", "is_active": True})
    draft = await service.get_draft(id)
    return await service.update_draft(id, DraftUpdate(version=draft.version, fields=DraftFields(
        name="bag", brand_id=str(brand["id"]), category="包包", cost_price=0)), ACTOR)


async def test_approve_requires_closed_originals_and_no_pending():
    first = await receive(second=1)
    await receive("text", second=2, text="A 說明")

    async def rejected():
        draft = await service.get_draft(first.draft_id)
        with pytest.raises(LangException) as error:
            await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
        assert error.value.status_code == 409

    await ready_fields(first.draft_id)
    await rejected()
    await receive(second=5)
    await rejected()
    await raw_photos.save_original(first.message_id, image_bytes(), "a.png")
    late = await receive("text", second=3, text="尚未決定")
    await rejected()
    draft = await service.get_draft(first.draft_id)
    await pending.ignore_message(draft.id, late.message_id, VersionRequest(version=draft.version),
                                 ACTOR)
    draft = await service.get_draft(first.draft_id)
    assert draft.photos[0].status == "stored"
    approval = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert approval.draft_id == draft.id and approval.product_id


async def test_next_review_skips_collecting_and_pending_drafts():
    ids = {}
    for source in ("pending", "ready", "missing-original"):
        first = await receive(second=1, source=source)
        await receive("text", second=2, text="說明", source=source)
        await receive(second=5, source=source)
        ids[source] = first
        if source != "missing-original":
            await raw_photos.save_original(first.message_id, image_bytes(), "a.png")
    await receive("text", second=3, text="待加入", source="pending")
    assert (await service.next_review()).id == ids["ready"].draft_id
    assert (await service.next_review(source_key="pending")).id is None
    summaries = {item.id: item for item in (await service.get_draft_list(20)).list_data}
    assert summaries[ids["missing-original"].draft_id].processing
    assert not summaries[ids["ready"].draft_id].processing
