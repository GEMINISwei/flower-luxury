from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select

from modules.products import photos, service
from modules.products.model import ProductPhotoTable
from shared.db.session import active_session
from shared.http.errors import LangException
from tests.modules.products.test_model import ACTOR, product

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOADS_DIR", tmp_path)


async def uploaded_photo(tmp_path):
    item = await product()
    output = BytesIO()
    Image.new("RGB", (3000, 1500), "red").save(output, "PNG")
    result = await photos.upload_photos(item.id, [UploadFile(
        filename="source.png", file=BytesIO(output.getvalue()),
    )], ACTOR)
    row = await active_session().scalar(select(ProductPhotoTable).where(
        ProductPhotoTable.id == result.list_data[0].id,
    ))
    assert row is not None
    for path in (tmp_path / "display").iterdir():
        path.unlink()
    return item.id, str(row.id), output.getvalue()


async def test_read_photo_with_only_original_repairs_requested_variant(db, tmp_path):
    item_id, photo_id, original = await uploaded_photo(tmp_path)
    result = await photos.photo_path(photo_id, size="128")
    assert list((tmp_path / "display").iterdir()) == [result.path]
    assert (await photos.original_file(photo_id)).path.read_bytes() == original
    assert (await service.get_product_list(limit=1)).list_data[0].id == item_id
    assert (await photos.photo_path(photo_id)).path.is_file()
    await active_session().commit()
    await photos.delete_photo(item_id, photo_id, ACTOR)
    await active_session().commit()
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    with pytest.raises(LangException) as error:
        await photos.photo_path(photo_id, size="128")
    assert error.value.status_code == 404


async def test_read_existing_preview_without_sources_succeeds(db, tmp_path):
    _, photo_id, _ = await uploaded_photo(tmp_path)
    preview = await photos.photo_path(photo_id, size="128")
    for path in (tmp_path / "originals").iterdir():
        path.unlink()
    assert (await photos.photo_path(photo_id, size="128")).path == preview.path
    with pytest.raises(LangException) as error:
        await photos.photo_path(photo_id, size="640")
    assert error.value.status_code == 404


async def test_deleted_product_does_not_repair_variants(db, tmp_path):
    item_id, photo_id, _ = await uploaded_photo(tmp_path)
    await service.delete_product(item_id, ACTOR)
    with pytest.raises(LangException) as error:
        await photos.photo_path(photo_id, size="128")
    assert error.value.status_code == 404 and not list((tmp_path / "display").iterdir())
