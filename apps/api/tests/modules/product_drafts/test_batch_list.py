from uuid import UUID

import pytest
from sqlalchemy import select

from modules.product_drafts import collection, messages, model, photos, storage
from modules.product_drafts.schema import DraftFields, DraftUpdate
from modules.product_drafts.service import get_draft, get_draft_list, update_draft
from shared.db.session import active_session
from shared.http.errors import LangException
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import ACTOR, image_bytes, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_draft_list_uses_original_received_time(db):
    newer = await collection.ingest_message(incoming(source="newer", second=20))
    older = await collection.ingest_message(incoming(source="older", second=10))
    detail = await get_draft(older.draft_id)
    await update_draft(detail.id, DraftUpdate(version=detail.version,
                       fields=DraftFields(name="編輯後名稱")), ACTOR)
    page = await get_draft_list(limit=1)
    assert page.list_data[0].id == older.draft_id and page.has_next
    following = await get_draft_list(limit=1, cursor=page.next_cursor)
    assert following.list_data[0].id == newer.draft_id
    assert following.list_data[0].received_at.second == 20


async def test_clear_legacy_messages_preserves_drafts(db, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path)
    first = await collection.ingest_message(incoming(second=10))
    legacy = await collection.ingest_message(incoming(second=5))
    assert first.message_id is not None and legacy.message_id is not None
    ready = await photos.complete_photo(legacy.message_id, image_bytes(), "legacy.png")
    assert ready.photo is not None
    path = (await photos.read_photo(ready.photo.id, original=True)).path
    await messages.discard_legacy_message(legacy.message_id)
    assert path.exists()
    assert await active_session().scalar(select(model.MessageTable.id).where(
        model.MessageTable.id == UUID(legacy.message_id))) is None
    assert await active_session().scalar(select(JobTable.id).where(
        JobTable.task_name == "product_drafts.cleanup")) is not None
    assert (await get_draft(first.draft_id)).id == first.draft_id
    with pytest.raises(LangException) as error:
        await messages.discard_legacy_message(first.message_id)
    assert error.value.status_code == 409
