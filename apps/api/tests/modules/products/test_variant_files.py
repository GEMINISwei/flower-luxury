from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from fastapi import UploadFile
from PIL import Image

from modules.products import photos
from modules.products.images import PhotoSize
from modules.products.model import ProductPhotoTable
from shared.db.session import active_session
from shared.http.errors import LangException
from tests.modules.products.test_model import ACTOR, product

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
SIZES: tuple[PhotoSize, ...] = ("128", "320", "640", "full")


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOADS_DIR", tmp_path)


def image_bytes(size=(3000, 1500)):
    output = BytesIO()
    Image.new("RGB", size, (23, 100, 201)).save(output, "PNG")
    return output.getvalue()


async def legacy_photo(tmp_path, *, original=True):
    item = await product()
    display = tmp_path / "display" / "legacy.webp"
    display.parent.mkdir()
    Image.new("RGB", (2560, 2560), "blue").save(display, "WEBP", lossless=True)
    original_key = None
    if original:
        source = tmp_path / "originals" / "legacy.png"
        source.parent.mkdir()
        source.write_bytes(image_bytes())
        original_key = "products/originals/legacy.png"
    row = ProductPhotoTable(product_id=item.id, storage_key="products/display/legacy.webp",
                            original_storage_key=original_key,
                            original_filename="legacy.png" if original else None,
                            original_media_type="image/png" if original else None,
                            sort_order=1, uploaded_by=ACTOR["id"])
    active_session().add(row)
    await active_session().flush()
    return str(row.id), item.id


async def test_legacy_photo_variants_are_generated_from_original(db, tmp_path):
    photo_id, item_id = await legacy_photo(tmp_path)
    for size in SIZES:
        result = await photos.photo_path(photo_id, size=size)
        with Image.open(result.path) as image:
            assert image.size == ((2048, 1024) if size == "full" else (int(size), int(size)))
            center = cast(tuple[int, ...], image.convert("RGBA").getpixel(
                (image.width // 2, image.height // 2)))
            assert all(abs(actual - wanted) <= 6
                       for actual, wanted in zip(center, (23, 100, 201, 255), strict=True))
        before = result.path.stat().st_mtime_ns
        assert (await photos.photo_path(photo_id, size=size)).path.stat().st_mtime_ns == before
    assert (await photos.original_file(photo_id)).path.read_bytes() == image_bytes()
    assert (await photos.list_photos(item_id)).count == 1
    await active_session().commit()
    await photos.delete_photo(item_id, photo_id, ACTOR)
    await active_session().commit()
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    with pytest.raises(LangException):
        await photos.photo_path(photo_id, size="128")


async def test_legacy_photo_without_original_can_generate_previews(db, tmp_path):
    photo_id, _ = await legacy_photo(tmp_path, original=False)
    full = await photos.photo_path(photo_id)
    assert full.path == tmp_path / "display" / "legacy.webp"
    preview = await photos.photo_path(photo_id, size="128")
    with Image.open(preview.path) as image:
        assert image.size == (128, 128)
        color = cast(tuple[int, ...], image.convert("RGBA").getpixel((64, 64)))
        assert all(abs(actual - wanted) <= 6
                   for actual, wanted in zip(color, (0, 0, 255, 255), strict=True))


async def test_upload_writes_all_preview_sizes_before_reading(db, tmp_path):
    item = await product()
    result = await photos.upload_photos(item.id, [UploadFile(
        filename="large.png", file=BytesIO(image_bytes()),
    )], ACTOR)
    before = {path: path.stat().st_mtime_ns for path in tmp_path.rglob("*") if path.is_file()}
    assert len(before) == 5
    for size in SIZES:
        path = (await photos.photo_path(result.list_data[0].id, size=size)).path
        assert path in before and path.stat().st_mtime_ns == before[path]


async def test_variant_write_failure_cleans_all_files(db, tmp_path, monkeypatch):
    item = await product()
    write = Path.write_bytes
    calls = 0

    def fail_fourth(path, data):
        nonlocal calls
        calls += 1
        if calls == 4:
            write(path, b"partial")
            raise OSError("preview disk unavailable")
        return write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_fourth)
    with pytest.raises(OSError, match="preview disk unavailable"):
        await photos.upload_photos(item.id, [UploadFile(
            filename="large.png", file=BytesIO(image_bytes()),
        )], ACTOR)
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    assert (await photos.list_photos(item.id)).count == 0
