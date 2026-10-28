import uuid
from pathlib import Path

from pydantic import JsonValue
from sqlalchemy import event
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from modules.products.public import PreparedPhoto
from shared.db.session import active_session
from shared.jobs.contracts import Job
from shared.jobs.queue import enqueue_job

from .model import PhotoTable

UPLOADS_DIR = Path("/app/uploads/product_drafts")


def _path(key: str) -> Path:
    relative = Path(key).relative_to("product_drafts")
    path = (UPLOADS_DIR / relative).resolve()
    if not path.is_relative_to(UPLOADS_DIR.resolve()) or path == UPLOADS_DIR.resolve():
        raise ValueError("invalid draft storage key")
    return path


def _rolled_back(session: Session) -> None:
    if not session.in_nested_transaction():
        for path in session.info.pop("draft_created_files", []):
            path.unlink(missing_ok=True)


def _committed(session: Session) -> None:
    if not session.in_nested_transaction():
        session.info.pop("draft_created_files", None)


async def write_photo(row: PhotoTable, prepared: PreparedPhoto) -> None:
    key = uuid.uuid4().hex
    original = f"product_drafts/originals/{key}.{prepared.extension}"
    display = f"product_drafts/display/{key}.webp"
    paths: list[Path] = []
    try:
        for storage_key, content in [(original, prepared.original), (display, prepared.display)]:
            path = _path(storage_key)
            paths.append(path)
            await run_in_threadpool(path.parent.mkdir, parents=True, exist_ok=True)
            await run_in_threadpool(path.write_bytes, content)
        session = active_session().sync_session
        session.info.setdefault("draft_created_files", []).extend(paths)
        if not session.info.get("draft_file_hooks"):
            session.info["draft_file_hooks"] = True
            event.listen(session, "after_rollback", _rolled_back)
            event.listen(session, "after_commit", _committed)
        row.original_key, row.display_key = original, display
        row.filename = prepared.filename
        row.extension, row.media_type = prepared.extension, prepared.media_type
    except BaseException:
        for path in paths:
            await run_in_threadpool(path.unlink, missing_ok=True)
        raise


async def schedule_cleanup(rows: list[PhotoTable]) -> None:
    keys: list[JsonValue] = [
        key for row in rows for key in (row.original_key, row.display_key) if key
    ]
    if keys:
        await enqueue_job("product_drafts.cleanup", {"keys": keys})


async def cleanup_files(job: Job) -> None:
    keys = job.payload["keys"]
    if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
        raise ValueError("invalid cleanup payload")
    await _unlink_keys([str(key) for key in keys])


async def _unlink_keys(keys: list[str]) -> None:
    paths = [_path(key) for key in keys]
    for path in paths:
        await run_in_threadpool(path.unlink, missing_ok=True)


async def load_prepared(row: PhotoTable) -> PreparedPhoto:
    return PreparedPhoto(original=await run_in_threadpool(_path(row.original_key or "").read_bytes),
                         display=await run_in_threadpool(_path(row.display_key or "").read_bytes),
                         filename=row.filename or "photo", extension=row.extension or "png",
                         media_type=row.media_type or "image/png")
