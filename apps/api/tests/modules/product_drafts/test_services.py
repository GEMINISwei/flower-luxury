import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from modules.product_drafts import collection, messages, model, photos, review, service, storage
from modules.product_drafts.model import (
    ApprovalTable,
    DraftTable,
    MessageTable,
    PhotoTable,
    ReceiptTable,
)
from modules.product_drafts.schema import (
    DraftFields,
    DraftUpdate,
    MainPhoto,
    MessageMove,
    PhotoOrder,
    VersionRequest,
)
from modules.products.public import ProductInfo
from shared.db.session import _current_session
from shared.db.table import BaseTable
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from tests.modules.product_drafts.helpers import ACTOR, BASE, ID, image_bytes, incoming

pytestmark = pytest.mark.asyncio


class MemorySession:
    def __init__(self, rows):
        self.rows = rows

    sync_session = Session()

    def add(self, row):
        row.id = row.id or uuid.uuid4()
        for key, value in {"created_at": BASE, "received_at": BASE, "version": 1, "fields": {},
                           "collecting": True, "has_text": False, "attempts": 0}.items():
            if hasattr(row, key) and getattr(row, key) is None:
                setattr(row, key, value)
        self.rows[type(row)][str(row.id)] = row

    async def flush(self):
        pass

    async def delete(self, row):
        self.rows[type(row)].pop(str(row.id), None)
        if isinstance(row, DraftTable):
            for cls in (MessageTable, PhotoTable):
                for key, item in list(self.rows[cls].items()):
                    if item.draft_id == row.id:
                        self.rows[cls].pop(key)
        if isinstance(row, MessageTable):
            for key, item in list(self.rows[PhotoTable].items()):
                if item.message_id == row.id:
                    self.rows[PhotoTable].pop(key)

    @asynccontextmanager
    async def begin_nested(self):
        yield


@pytest.fixture
def state(monkeypatch, tmp_path):
    rows: dict[type[BaseTable], dict[str, Any]] = {
        cls: {} for cls in (DraftTable, MessageTable, PhotoTable, ReceiptTable, ApprovalTable)
    }
    stream = SimpleNamespace(source_key="group-a", last_occurred_at=None, next_sequence=0)

    session = MemorySession(rows)
    token = _current_session.set(session)  # type: ignore[arg-type]
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path)
    monkeypatch.setattr(model, "stream_for", AsyncMock(return_value=stream))
    monkeypatch.setattr(model, "mark_source_processing", AsyncMock())
    monkeypatch.setattr(model, "refresh_source_confirmation", AsyncMock())
    monkeypatch.setattr(model, "current_draft", AsyncMock(side_effect=lambda key: next(
        (row for row in rows[DraftTable].values()
         if row.source_key == key and row.collecting), None,
    )))
    for name, cls in [("get_draft_row", DraftTable), ("get_message_row", MessageTable),
                      ("get_photo_row", PhotoTable), ("approval_for", ApprovalTable)]:
        monkeypatch.setattr(model, name, AsyncMock(side_effect=(
            lambda target: lambda id, **_kwargs: rows[target].get(str(id))
        )(cls)))
    monkeypatch.setattr(model, "receipt_for", AsyncMock(side_effect=lambda fingerprint: next(
        (row for row in rows[ReceiptTable].values() if row.fingerprint == fingerprint), None,
    )))
    monkeypatch.setattr(model, "messages_for", AsyncMock(side_effect=lambda id: sorted(
        [row for row in rows[MessageTable].values() if str(row.draft_id) == str(id)],
        key=lambda row: row.sequence,
    )))
    monkeypatch.setattr(model, "photos_for", AsyncMock(side_effect=lambda id: sorted(
        [row for row in rows[PhotoTable].values() if str(row.draft_id) == str(id)],
        key=lambda row: row.sort_order,
    )))
    monkeypatch.setattr(model, "photo_for_message", AsyncMock(side_effect=lambda id: next(
        (row for row in rows[PhotoTable].values() if str(row.message_id) == str(id)), None,
    )))
    monkeypatch.setattr(collection, "enqueue_job", AsyncMock())
    monkeypatch.setattr(storage, "enqueue_job", AsyncMock())
    yield rows
    _current_session.reset(token)


async def ready():
    event = await collection.ingest_message(incoming())
    await photos.complete_photo(event.message_id, image_bytes(), "photo.png")
    row = await model.get_draft_row(event.draft_id)
    assert row is not None
    row.collecting = False
    return await service.get_draft(event.draft_id)


async def test_collection_preserves_text_and_duplicate_identity_without_database(state):
    first = incoming()
    event = await collection.ingest_message(first)
    assert (await collection.ingest_message(first)).duplicate
    await collection.ingest_message(incoming("text", text="  原文\n第二行", second=1))
    draft = await service.get_draft(event.draft_id)
    assert draft.messages[-1].text == "  原文\n第二行" and draft.version > 1
    next_item = await collection.ingest_message(incoming(second=2))
    assert next_item.draft_id != draft.id
    assert not (await service.get_draft(draft.id)).collecting


async def test_unassigned_and_late_messages_do_not_change_active_draft(state):
    assert (await collection.ingest_message(incoming("text", text="先到"))).unassigned
    current = await collection.ingest_message(incoming(second=2))
    before = await service.get_draft(current.draft_id)
    assert (await collection.ingest_message(incoming("text", text="延遲", second=1))).unassigned
    assert (await service.get_draft(current.draft_id)).version == before.version


async def test_missing_and_stale_draft_updates_are_rejected(state):
    with pytest.raises(LangException) as error:
        await service.get_draft(ID)
    assert error.value.status_code == 404
    draft = await ready()
    changed = await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(name="edited"),
    ), ACTOR)
    assert changed.fields.name == "edited"
    with pytest.raises(LangException) as error:
        await service.update_draft(
            draft.id, DraftUpdate(version=draft.version, fields=DraftFields()), ACTOR,
        )
    assert error.value.status_code == 409


async def test_photo_validation_retry_read_and_deletion(state):
    event = await collection.ingest_message(incoming())
    with pytest.raises(LangException):
        await photos.complete_photo(event.message_id, b"invalid", "bad.png")
    failed = await photos.mark_photo_failed(event.message_id)
    assert failed.photo is not None and failed.photo.status == "failed"
    completed = await photos.complete_photo(event.message_id, image_bytes(), "original.png")
    assert completed.photo is not None
    repeated = await photos.complete_photo(event.message_id, image_bytes(), "again.png")
    assert repeated.photo is not None and completed.photo is not None
    assert repeated.photo.id == completed.photo.id
    original = await photos.read_photo(completed.photo.id, original=True)
    assert original.path.read_bytes() == image_bytes()
    assert (await photos.read_photo(completed.photo.id)).media_type == "image/webp"
    draft = await service.get_draft(event.draft_id)
    await photos.delete_photo(draft.id, completed.photo.id, VersionRequest(version=draft.version))
    assert not (await photos.complete_photo(event.message_id, image_bytes(), "late.png")).accepted
    assert not (await photos.mark_photo_failed(event.message_id)).accepted
    with pytest.raises(LangException):
        await photos.read_photo(completed.photo.id)


async def test_photo_order_and_main_enforce_membership_without_database(state):
    first = await collection.ingest_message(incoming())
    second = await collection.ingest_message(incoming(second=1))
    draft = await service.get_draft(first.draft_id)
    ids = [row.id for row in draft.photos]
    with pytest.raises(LangException):
        await photos.reorder_photos(draft.id, PhotoOrder(version=draft.version, photo_ids=ids[:1]))
    draft = await photos.reorder_photos(
        draft.id, PhotoOrder(version=draft.version, photo_ids=ids[::-1]),
    )
    draft = await photos.set_main_photo(draft.id, MainPhoto(version=draft.version, photo_id=ids[1]))
    assert draft.main_photo_id == ids[1]
    with pytest.raises(LangException):
        await photos.set_main_photo(draft.id, MainPhoto(version=draft.version, photo_id=ID))
    assert second.draft_id == draft.id


async def test_message_move_enforces_versions_and_source_without_database(state):
    first = await collection.ingest_message(incoming())
    text = await collection.ingest_message(incoming("text", text="move", second=1))
    second = await collection.ingest_message(incoming(second=2))
    source = await service.get_draft(first.draft_id)
    target = await service.get_draft(second.draft_id)
    moved = await messages.move_message(text.message_id, MessageMove(
        target_draft_id=target.id, target_version=target.version, source_version=source.version,
    ), ACTOR)
    assert moved.messages[-1].text == "move"
    with pytest.raises(LangException):
        await messages.move_message(text.message_id, MessageMove(
            target_draft_id=source.id, target_version=1, source_version=1,
        ), ACTOR)


async def test_approval_guards_and_idempotency_without_database(state, monkeypatch):
    draft = await ready()
    with pytest.raises(LangException) as error:
        await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert error.value.status_code == 422
    draft = await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(
        name="bag", brand_id=ID, category="包包", cost_price=0,
    )), ACTOR)
    product = ProductInfo(id=ID, sku="LX20261028ABCDE", brand="brand", status="not_acquired",
                          created_by=ACTOR["id"], created_at=BASE, **draft.fields.model_dump())
    imported = AsyncMock(return_value=product)
    monkeypatch.setattr(review, "create_imported_product", imported)
    result = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    repeated = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert result.product_id == repeated.product_id == ID and imported.await_count == 1
    assert state[MessageTable] == {}


async def test_discard_removes_content_and_schedules_only_file_keys(state):
    draft = await ready()
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    assert state[DraftTable] == {} and state[MessageTable] == {} and state[PhotoTable] == {}
    assert state[ReceiptTable]
    assert isinstance(storage.enqueue_job, AsyncMock)
    assert storage.enqueue_job.await_count == 1
    assert "original.png" not in str(storage.enqueue_job.call_args)


async def test_cleanup_rejects_paths_outside_draft_namespace(state, tmp_path):
    safe = tmp_path / "originals" / "owned.png"
    safe.parent.mkdir()
    safe.write_bytes(b"data")
    job = Job(id=uuid.uuid4(), task_name="product_drafts.cleanup", attempts=1,
              payload={"keys": ["product_drafts/originals/owned.png"]})
    await storage.cleanup_files(job)
    await storage.cleanup_files(job)
    assert not safe.exists()
    job.payload = {"keys": ["product_drafts/../../outside"]}
    with pytest.raises(ValueError):
        await storage.cleanup_files(job)


async def test_photo_write_failure_cleans_partial_files(state, monkeypatch, tmp_path):
    event = await collection.ingest_message(incoming())
    write = Path.write_bytes
    calls = 0

    def fail_second(path, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            write(path, b"partial")
            raise OSError("disk unavailable")
        return write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_second)
    with pytest.raises(OSError):
        await photos.complete_photo(event.message_id, image_bytes(), "photo.png")
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


async def test_unassigned_text_can_be_attached_and_foreign_source_is_rejected(state):
    orphan = await collection.ingest_message(incoming("text", text="先到"))
    draft = await ready()
    result = await messages.move_message(orphan.message_id, MessageMove(
        target_draft_id=draft.id, target_version=draft.version,
    ), ACTOR)
    assert any(row.text == "先到" for row in result.messages)
    other = await collection.ingest_message(incoming(source="group-b", second=3))
    target = await service.get_draft(other.draft_id)
    with pytest.raises(LangException):
        await messages.move_message(orphan.message_id, MessageMove(
            target_draft_id=target.id, target_version=target.version,
            source_version=result.version,
        ), ACTOR)
