from io import BytesIO

import pytest
from fastapi import UploadFile
from sqlalchemy import select

from modules.product_drafts import collection, photos, review, service, storage
from modules.product_drafts.model import PhotoTable
from modules.product_drafts.schema import VersionRequest
from modules.products.public import get_product
from shared.db.session import active_session
from shared.http.errors import LangException
from tests.modules.product_drafts.helpers import ACTOR, image_bytes, incoming
from tests.modules.product_drafts.test_integration import prepared_draft

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    from modules.products import photos as product_photos

    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")


def upload(content=None):
    return UploadFile(file=BytesIO(image_bytes() if content is None else content),
                      filename="manual.png")


async def test_upload_photos_to_draft(db):
    draft = await prepared_draft()
    result = await photos.upload_photos(draft.id, draft.version, [upload()], ACTOR)
    assert result.version == draft.version + 1
    assert len(result.photos) == 2 and all(p.status == "ready" for p in result.photos)
    manual = result.messages[-1]
    assert manual.kind == "image" and manual.sender_name == ACTOR["username"]
    original = await photos.read_photo(result.photos[-1].id, original=True)
    assert original.path.read_bytes() == image_bytes()
    approved = await review.approve_draft(result.id, VersionRequest(version=result.version), ACTOR)
    assert (await get_product(approved.product_id)).name == "手袋"


async def test_upload_stale_draft_is_rejected(db):
    draft = await prepared_draft()
    with pytest.raises(LangException) as exc:
        await photos.upload_photos(draft.id, draft.version - 1, [upload()], ACTOR)
    assert exc.value.status_code == 409
    assert (await service.get_draft(draft.id)).version == draft.version
    assert len((await service.get_draft(draft.id)).photos) == 1


async def test_invalid_upload_keeps_draft(db):
    draft = await prepared_draft()
    with pytest.raises(LangException):
        await photos.upload_photos(draft.id, draft.version, [upload(), upload(b"invalid")], ACTOR)
    current = await service.get_draft(draft.id)
    assert current.version == draft.version and len(current.photos) == 1
    with pytest.raises(LangException):
        await photos.upload_photos(draft.id, draft.version, [], ACTOR)
    with pytest.raises(LangException) as exc:
        oversized = upload(b"x" * (15 * 1024 * 1024 + 1))
        await photos.upload_photos(draft.id, draft.version, [oversized], ACTOR)
    assert exc.value.status_code == 413


async def test_manual_upload_does_not_change_line_grouping(db):
    draft = await prepared_draft()
    row = await collection.model.get_draft_row(draft.id)
    assert row is not None
    row.collecting = True
    result = await photos.upload_photos(draft.id, draft.version, [upload()], ACTOR)
    following = await collection.ingest_message(incoming(second=1))
    assert following.draft_id == result.id
    assert len((await service.get_draft(result.id)).photos) == 3


async def test_discard_removes_manual_photos(db):
    draft = await prepared_draft()
    result = await photos.upload_photos(draft.id, draft.version, [upload()], ACTOR)
    await review.discard_draft(result.id, VersionRequest(version=result.version), ACTOR)
    rows = list(await active_session().scalars(select(PhotoTable).where(
        PhotoTable.draft_id == draft.id,
    )))
    assert rows == []
    with pytest.raises(LangException):
        await photos.read_photo(result.photos[-1].id)


async def test_unassigned_image_exposes_preview(db):
    await collection.ingest_message(incoming(second=5))
    event = await collection.ingest_message(incoming(second=1))
    assert event.unassigned and event.message_id
    await photos.complete_photo(event.message_id, image_bytes(), "late.png")
    from modules.product_drafts import messages

    page = await messages.get_unassigned_messages(limit=20)
    item = next(item for item in page.list_data if item.id == event.message_id)
    assert item.photo and item.photo.status == "ready" and item.photo.url
