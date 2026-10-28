import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import delete, select, update

from modules.brands.public import BrandTable
from modules.product_drafts import collection, messages, photos, review, service, storage
from modules.product_drafts.model import DraftTable, MessageTable, ReceiptTable
from modules.product_drafts.schema import (
    DraftFields,
    DraftUpdate,
    MainPhoto,
    MessageMove,
    PhotoOrder,
    VersionRequest,
)
from modules.products.public import get_history, get_product
from shared.db.session import active_session, session_scope
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from shared.time import utc_now
from tests.modules.product_drafts.helpers import ACTOR, image_bytes, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    from modules.products import photos as product_photos

    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")


async def prepared_draft(*, second=0):
    event = await collection.ingest_message(incoming(second=second))
    assert event.draft_id and event.message_id
    await photos.complete_photo(event.message_id, image_bytes(), "original.png")
    brand = await BrandTable.create({"name": f"brand-{event.draft_id}", "is_active": True})
    draft = await service.get_draft(event.draft_id)
    return await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(
        name="手袋", brand_id=str(brand["id"]), category="包包", cost_price=3000,
    )), ACTOR)


async def count_products():
    from shared.db.table import BaseTable

    table = BaseTable.metadata.tables["products"]
    return list((await active_session().execute(select(table.c.id))).scalars())


async def test_image_after_text_starts_next_draft(db):
    first = await collection.ingest_message(incoming())
    second = await collection.ingest_message(incoming(second=1))
    assert first.draft_id == second.draft_id
    await collection.ingest_message(incoming("text", text="第一段\n第二行", second=2))
    await collection.ingest_message(incoming("text", text="  保留空白  ", second=3))
    next_item = await collection.ingest_message(incoming(second=4))
    assert next_item.draft_id != first.draft_id
    draft = await service.get_draft(first.draft_id)
    assert not draft.collecting and len(draft.photos) == 2
    assert [row.text for row in draft.messages if row.kind == "text"] == [
        "第一段\n第二行", "  保留空白  ",
    ]
    assert (await service.get_draft_list(limit=1)).has_next


async def test_sources_and_unassigned_messages_preserve_originals(db):
    orphan = await collection.ingest_message(incoming("text", text="先到的文字"))
    assert orphan.unassigned and orphan.draft_id is None
    first = await collection.ingest_message(incoming(second=3))
    other = await collection.ingest_message(incoming(source="group-b", second=3))
    late = await collection.ingest_message(incoming("text", text="延遲文字", second=1))
    assert late.unassigned and first.draft_id != other.draft_id
    page = await messages.get_unassigned_messages(limit=20, source_key="group-a")
    assert {row.text for row in page.list_data} == {"先到的文字", "延遲文字"}
    assert all(row.sender_name == "供應商" for row in page.list_data)


async def test_duplicate_events_do_not_resurrect_discarded_drafts(db):
    event = incoming(external_id="same-event")
    first = await collection.ingest_message(event)
    assert (await collection.ingest_message(event)).duplicate
    draft = await service.get_draft(first.draft_id)
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert (await collection.ingest_message(event)).duplicate
    assert (await service.get_draft_list(limit=20)).total_count == 0
    assert await active_session().scalar(select(MessageTable.id)) is None
    receipt = await active_session().scalar(select(ReceiptTable))
    assert receipt is not None and "same-event" not in str(receipt.to_dict())


async def test_draft_update_preserves_messages_and_rejects_stale_version(db):
    event = await collection.ingest_message(incoming())
    await collection.ingest_message(incoming("text", text="原文", second=1))
    draft = await service.get_draft(event.draft_id)
    result = await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(name="整理後"),
    ), ACTOR)
    assert result.fields.name == "整理後" and result.messages[-1].text == "原文"
    with pytest.raises(LangException) as error:
        await service.update_draft(
            draft.id, DraftUpdate(version=draft.version, fields=DraftFields()), ACTOR,
        )
    assert error.value.status_code == 409


async def test_photo_completion_preserves_original_and_rechecks_ownership(db):
    event = await collection.ingest_message(incoming())
    failed = await photos.mark_photo_failed(event.message_id)
    assert failed.photo is not None
    assert failed.accepted and failed.photo.status == "failed"
    completed = await photos.complete_photo(event.message_id, image_bytes(), "原圖.png")
    assert completed.photo is not None
    assert completed.accepted and completed.photo.status == "ready"
    original = await photos.read_photo(completed.photo.id, original=True)
    assert original.path.read_bytes() == image_bytes() and original.filename == "原圖.png"
    repeated = await photos.complete_photo(event.message_id, image_bytes(), "again.png")
    assert repeated.photo is not None and completed.photo is not None
    assert repeated.photo.id == completed.photo.id
    draft = await service.get_draft(event.draft_id)
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert not (await photos.complete_photo(event.message_id, image_bytes(), "late.png")).accepted


async def test_photo_order_and_main_require_complete_owned_ids(db):
    first = await collection.ingest_message(incoming())
    second = await collection.ingest_message(incoming(second=1))
    await photos.complete_photo(first.message_id, image_bytes(), "1.png")
    await photos.complete_photo(second.message_id, image_bytes(), "2.png")
    draft = await service.get_draft(first.draft_id)
    ids = [photo.id for photo in draft.photos]
    with pytest.raises(LangException):
        await photos.reorder_photos(draft.id, PhotoOrder(version=draft.version, photo_ids=ids[:1]))
    draft = await photos.reorder_photos(
        draft.id, PhotoOrder(version=draft.version, photo_ids=ids[::-1]),
    )
    assert [photo.id for photo in draft.photos] == ids[::-1]
    draft = await photos.set_main_photo(draft.id, MainPhoto(version=draft.version, photo_id=ids[1]))
    assert draft.main_photo_id == ids[1]
    draft = await photos.delete_photo(draft.id, ids[1], VersionRequest(version=draft.version))
    assert draft.main_photo_id == ids[0]


async def test_move_message_checks_both_draft_versions(db):
    first = await collection.ingest_message(incoming())
    text = await collection.ingest_message(incoming("text", text="應該移到第二件", second=1))
    second = await collection.ingest_message(incoming(second=2))
    source = await service.get_draft(first.draft_id)
    target = await service.get_draft(second.draft_id)
    with pytest.raises(LangException):
        await messages.move_message(text.message_id, MessageMove(
            target_draft_id=target.id, target_version=target.version,
            source_version=source.version - 1,
        ), ACTOR)
    target = await messages.move_message(text.message_id, MessageMove(
        target_draft_id=target.id, target_version=target.version, source_version=source.version,
    ), ACTOR)
    assert target.messages[-1].text == "應該移到第二件"
    assert len((await service.get_draft(source.id)).messages) == 1


async def test_approval_requires_complete_fields_and_ready_photos(db):
    event = await collection.ingest_message(incoming())
    draft = await service.get_draft(event.draft_id)
    with pytest.raises(LangException) as error:
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert error.value.status_code == 422
    brand = await BrandTable.create({"name": "brand", "is_active": True})
    draft = await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(
        name="手袋", brand_id=str(brand["id"]), category="包包", cost_price=0,
    )), ACTOR)
    with pytest.raises(LangException) as error:
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert error.value.status_code == 409
    assert await count_products() == []


async def test_approval_creates_product_photos_and_actor_history(db):
    draft = await prepared_draft()
    result = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    product = await get_product(result.product_id)
    assert product.status == "not_acquired" and product.main_photo_id and product.sku == result.sku
    assert result.reviewed_by == ACTOR["id"] and result.reviewer_name == "staff"
    assert (await get_history(product.id)).list_data[0].operator_name == "staff"
    assert (await service.get_draft_list(limit=20)).total_count == 0
    assert await active_session().scalar(select(MessageTable.id)) is None
    repeated = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert repeated.product_id == result.product_id


async def test_concurrent_approval_creates_one_product(db):
    draft = await prepared_draft()
    await active_session().commit()

    async def approve():
        async with session_scope():
            return await review.approve_draft(
                draft.id, VersionRequest(version=draft.version), ACTOR,
            )

    first, second = await asyncio.gather(approve(), approve())
    assert first.product_id == second.product_id
    assert len(await count_products()) == 1


async def test_failed_approval_rolls_back_product_and_preserves_draft(db, monkeypatch, tmp_path):
    draft = await prepared_draft()
    from modules.products import photos as product_photos

    original = product_photos.store_prepared_photos

    async def fail_after_store(*args, **kwargs):
        await original(*args, **kwargs)
        raise OSError("disk unavailable")

    monkeypatch.setattr(product_photos, "store_prepared_photos", fail_after_store)
    with pytest.raises(OSError):
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert await count_products() == []
    assert (await service.get_draft(draft.id)).fields.name == "手袋"
    assert not [path for path in (tmp_path / "products").rglob("*") if path.is_file()]


async def test_discard_cleanup_is_retryable_and_transactional(db):
    draft = await prepared_draft()
    path = (await photos.read_photo(draft.photos[0].id, original=True)).path
    await active_session().commit()
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    await active_session().rollback()
    assert path.exists() and (await service.get_draft(draft.id)).id == draft.id
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    await active_session().commit()
    row = await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "product_drafts.cleanup",
    ))
    assert row is not None
    job = Job.model_validate(row)
    await storage.cleanup_files(job)
    await storage.cleanup_files(job)
    assert not path.exists() and await active_session().scalar(select(DraftTable.id)) is None


async def test_receipt_expiry_removes_only_expired_receipts(db):
    await collection.ingest_message(incoming())
    receipt = await active_session().scalar(select(ReceiptTable))
    assert receipt is not None
    row = await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "product_drafts.expire_receipt",
    ))
    assert row is not None
    job = Job.model_validate(row)
    await collection.expire_receipt(job)
    assert await active_session().get(ReceiptTable, receipt.id) is not None
    await active_session().execute(update(ReceiptTable).values(
        expires_at=utc_now() - timedelta(seconds=1),
    ))
    await collection.expire_receipt(job)
    assert await active_session().scalar(select(ReceiptTable.id)) is None
    await active_session().execute(delete(JobTable))
