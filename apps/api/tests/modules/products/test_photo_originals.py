from io import BytesIO
from pathlib import Path

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


def source_file(format="PNG", filename="原始照片.png"):
    buffer = BytesIO()
    Image.new("RGB", (16, 8), "red").save(buffer, format=format)
    data = buffer.getvalue()
    return UploadFile(filename=filename, file=BytesIO(data)), data


def stored_paths(root):
    return sorted(path for path in root.rglob("*") if path.is_file())


@pytest.mark.parametrize("format,filename,mime", [
    ("PNG", "原始照片.png", "image/png"), ("JPEG", "phone.jpg", "image/jpeg"),
    ("WEBP", "phone.webp", "image/webp"), ("HEIF", "phone.heic", "image/heic"),
])
async def test_upload_preserves_original_and_pairs_display(db, tmp_path, format, filename, mime):
    item = await product()
    file, original = source_file(format, filename)
    photo = (await photos.upload_photos(item.id, [file], ACTOR)).list_data[0]
    row = await active_session().get(ProductPhotoTable, photo.id)
    assert row is not None
    assert row.original_storage_key is not None
    display = tmp_path / row.storage_key.removeprefix("products/")
    original_path = tmp_path / row.original_storage_key.removeprefix("products/")
    assert original_path.parent.name == "originals" and display.parent.name == "display"
    assert display.stem == original_path.stem and display != original_path
    assert original_path.read_bytes() == original
    download = await photos.original_file(photo.id)
    assert download.path == original_path and download.filename == filename
    assert download.media_type == mime
    assert photo.download_url == f"/api/products/photos/{photo.id}/download"
    assert (await photos.photo_path(photo.id)).path == display
    with Image.open(display) as image:
        assert image.format == "WEBP" and image.size == (2560, 2560)
    assert len(stored_paths(tmp_path)) == 2


async def test_legacy_photo_has_no_original_download(db, tmp_path):
    item = await product()
    path = tmp_path / "legacy.webp"
    path.write_bytes(b"legacy")
    row = ProductPhotoTable(product_id=item.id, storage_key="products/legacy.webp",
                            sort_order=1, uploaded_by=ACTOR["id"])
    active_session().add(row)
    await active_session().flush()
    photo = (await photos.list_photos(item.id)).list_data[0]
    assert photo.download_url is None
    assert (await photos.photo_path(photo.id)).path == path
    with pytest.raises(LangException) as error:
        await photos.original_file(photo.id)
    assert error.value.status_code == 404


async def test_invalid_batch_creates_no_files(db, tmp_path):
    item = await product()
    file, _ = source_file()
    with pytest.raises(LangException):
        await photos.upload_photos(item.id, [file, UploadFile(
            filename="invalid.png", file=BytesIO(b"invalid"),
        )], ACTOR)
    assert stored_paths(tmp_path) == []
    assert (await photos.list_photos(item.id)).count == 0


async def test_write_failure_cleans_both_files(db, tmp_path, monkeypatch):
    item = await product()
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
    with pytest.raises(OSError, match="disk unavailable"):
        await photos.upload_photos(item.id, [source_file()[0]], ACTOR)
    assert stored_paths(tmp_path) == []
    assert (await photos.list_photos(item.id)).count == 0


async def test_photo_rollback_removes_both_files(db, tmp_path):
    item = await product()
    await active_session().commit()
    await photos.upload_photos(item.id, [source_file()[0]], ACTOR)
    assert len(stored_paths(tmp_path)) == 2
    await active_session().rollback()
    assert stored_paths(tmp_path) == []
    assert (await photos.list_photos(item.id)).count == 0


async def test_delete_photo_removes_both_files(db, tmp_path):
    item = await product()
    photo = (await photos.upload_photos(item.id, [source_file()[0]], ACTOR)).list_data[0]
    await active_session().commit()
    await photos.delete_photo(item.id, photo.id, ACTOR)
    assert len(stored_paths(tmp_path)) == 2
    await active_session().commit()
    assert stored_paths(tmp_path) == []


async def test_deleted_product_original_is_not_accessible(db):
    item = await product()
    photo = (await photos.upload_photos(item.id, [source_file()[0]], ACTOR)).list_data[0]
    await service.delete_product(item.id, ACTOR)
    with pytest.raises(LangException) as error:
        await photos.original_file(photo.id)
    assert error.value.status_code == 404


async def test_photo_delete_rollback_preserves_both_files(db, tmp_path):
    item = await product()
    photo = (await photos.upload_photos(item.id, [source_file()[0]], ACTOR)).list_data[0]
    await active_session().commit()
    await photos.delete_photo(item.id, photo.id, ACTOR)
    await active_session().rollback()
    assert len(stored_paths(tmp_path)) == 2
    assert await active_session().scalar(select(ProductPhotoTable.id)) is not None
