import asyncio
from threading import Event

import pytest
from PIL import Image
from sqlalchemy import select

from modules.product_drafts import photos, review, storage
from modules.product_drafts.model import PhotoTable
from modules.product_drafts.schema import VersionRequest
from shared.db.session import active_session, session_scope
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import ACTOR, image_bytes
from tests.modules.product_drafts.test_integration import prepared_draft

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path)


async def original_only_draft(tmp_path):
    draft = await prepared_draft()
    for path in (tmp_path / "display").iterdir():
        path.unlink()
    return draft


async def cleanup():
    row = await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "product_drafts.cleanup",
    ))
    assert row is not None
    await storage.cleanup_files(Job.model_validate(row))


async def test_read_draft_with_only_original_repairs_then_discard_cleans_all_files(db, tmp_path):
    draft = await original_only_draft(tmp_path)
    photo_id = draft.photos[0].id
    result = await photos.read_photo(photo_id, size="128")
    assert list((tmp_path / "display").iterdir()) == [result.path]
    assert (await photos.read_photo(photo_id, original=True)).path.read_bytes() == image_bytes()
    await photos.read_photo(photo_id, size="full")
    await active_session().commit()
    await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)
    await active_session().commit()
    await cleanup()
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    with pytest.raises(LangException) as error:
        await photos.read_photo(photo_id, size="640")
    assert error.value.status_code == 404


async def test_read_draft_existing_preview_without_sources_succeeds(db, tmp_path):
    draft = await original_only_draft(tmp_path)
    photo_id = draft.photos[0].id
    result = await photos.read_photo(photo_id, size="128")
    for path in (tmp_path / "originals").iterdir():
        path.unlink()
    assert (await photos.read_photo(photo_id, size="128")).path == result.path
    with pytest.raises(LangException) as error:
        await photos.read_photo(photo_id, size="640")
    assert error.value.status_code == 404


async def test_discard_waits_for_repair_and_leaves_no_files(db, tmp_path, monkeypatch):
    draft = await original_only_draft(tmp_path)
    await active_session().commit()
    started = asyncio.Event()
    release = Event()
    loop = asyncio.get_running_loop()
    save = Image.Image.save

    def pause(image, *args, **kwargs):
        loop.call_soon_threadsafe(started.set)
        assert release.wait(timeout=10)
        return save(image, *args, **kwargs)

    async def read():
        async with session_scope():
            await photos.read_photo(draft.photos[0].id, size="128")

    async def discard():
        async with session_scope():
            await review.discard_draft(draft.id, VersionRequest(version=draft.version), ACTOR)

    monkeypatch.setattr(Image.Image, "save", pause)
    reader = asyncio.create_task(read())
    discarder = None
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        discarder = asyncio.create_task(discard())
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(discarder), timeout=0.1)
    finally:
        release.set()
        await reader
        if discarder:
            await discarder
    await cleanup()
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    assert await active_session().scalar(select(PhotoTable.id)) is None
