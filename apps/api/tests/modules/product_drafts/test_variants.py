from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select

from modules.product_drafts import photos, review, storage
from modules.product_drafts.model import PhotoTable
from modules.product_drafts.schema import VersionRequest
from modules.products import photos as product_photos
from modules.products.images import PhotoSize
from shared.db.session import active_session
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import ACTOR, image_bytes
from tests.modules.product_drafts.test_integration import prepared_draft

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
SIZES: tuple[PhotoSize, ...] = ("128", "320", "640", "full")


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(product_photos, "UPLOADS_DIR", tmp_path / "products")


async def test_draft_photo_variants_survive_approval_and_cleanup(db, tmp_path):
    draft = await prepared_draft()
    assert len([path for path in (tmp_path / "drafts").rglob("*") if path.is_file()]) == 5
    for size in SIZES:
        stored = await photos.read_photo(draft.photos[0].id, size=size)
        with Image.open(stored.path) as image:
            assert image.size == ((8, 4) if size == "full" else (int(size), int(size)))
    approval = await review.approve_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    product = (await product_photos.list_photos(approval.product_id)).list_data[0]
    for size in SIZES:
        stored = await product_photos.photo_path(product.id, size=size)
        with Image.open(stored.path) as image:
            assert image.size == ((8, 4) if size == "full" else (int(size), int(size)))
    assert (await product_photos.original_file(product.id)).path.read_bytes() == image_bytes()
    await active_session().commit()
    job = await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "product_drafts.cleanup",
    ))
    assert job is not None
    await storage.cleanup_files(Job.model_validate(job))
    await storage.cleanup_files(Job.model_validate(job))
    assert not [path for path in (tmp_path / "drafts").rglob("*") if path.is_file()]
    assert len([path for path in (tmp_path / "products").rglob("*") if path.is_file()]) == 5


async def test_draft_legacy_photo_generates_variants_from_original(db, tmp_path):
    draft = await prepared_draft()
    row = await active_session().get(PhotoTable, draft.photos[0].id)
    assert row is not None
    legacy = tmp_path / "drafts" / "display" / "legacy.webp"
    Image.new("RGB", (2560, 2560), "blue").save(legacy, "WEBP", lossless=True)
    row.display_key = "product_drafts/display/legacy.webp"
    await active_session().flush()
    for size in SIZES:
        stored = await photos.read_photo(str(row.id), size=size)
        with Image.open(stored.path) as image:
            assert image.size == ((8, 4) if size == "full" else (int(size), int(size)))
            assert image.getpixel((image.width // 2, image.height // 2)) == (255, 0, 0, 255)


async def test_draft_variant_write_failure_preserves_existing_photos(db, tmp_path, monkeypatch):
    draft = await prepared_draft()
    before = {path for path in tmp_path.rglob("*") if path.is_file()}
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
        await photos.upload_photos(draft.id, draft.version, [UploadFile(
            filename="manual.png", file=BytesIO(image_bytes()),
        )], ACTOR)
    assert {path for path in tmp_path.rglob("*") if path.is_file()} == before
