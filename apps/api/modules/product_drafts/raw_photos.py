import uuid
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from modules.products.public import (
    PreparedPhoto,
    prepare_photo,
    validate_batch_size,
)
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from shared.jobs.processes import ProcessExecutionError, run_process
from shared.jobs.queue import enqueue_job

from . import model, storage
from .schema import PhotoCompletion
from .service import _bump, _photo_info


class OriginalInfo(BaseModel):
    extension: str
    media_type: str
    filename: str


def _original_info(content: bytes, filename: str | None) -> OriginalInfo:
    extension, media = "bin", "application/octet-stream"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        extension, media = "png", "image/png"
    elif content.startswith(b"\xff\xd8"):
        extension, media = "jpg", "image/jpeg"
    elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        extension, media = "webp", "image/webp"
    elif content[4:8] == b"ftyp":
        extension, media = "heic", "image/heic"
    name = (filename or f"photo.{extension}").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if 32 <= ord(char) != 127)[:255]
    return OriginalInfo(extension=extension, media_type=media,
                        filename=name or f"photo.{extension}")


async def save_original(id: str | None, content: bytes, filename: str | None) -> PhotoCompletion:
    async with transaction():
        message = await model.get_message_row(id)
        if message is None:
            return PhotoCompletion(accepted=False)
        await model.stream_for(message.source_key)
        message = await model.get_message_row(id, lock=True)
        row = await model.photo_for_message(id) if message else None
        if row is None:
            return PhotoCompletion(accepted=False)
        if row.status not in {"stored", "ready"}:
            validate_batch_size([len(content)])
            info = _original_info(content, filename)
            key = f"product_drafts/originals/{uuid.uuid4().hex}.{info.extension}"
            path = storage._path(key)
            try:
                await run_in_threadpool(path.parent.mkdir, parents=True, exist_ok=True)
                await run_in_threadpool(path.write_bytes, content)
                storage.remember_created_files([path])
                row.original_key, row.status = key, "stored"
                row.filename, row.extension, row.media_type = (
                    info.filename, info.extension, info.media_type)
                draft = (await model.get_draft_row(str(message.draft_id))
                         if message and message.draft_id else None)
                if draft:
                    # 分組只看原始時間, 加工不必等收集結束.
                    await enqueue_job("product_drafts.render_photo", {
                        "photo_id": str(row.id), "draft_id": str(draft.id),
                    }, queue="images", idempotency_key=f"photo:{row.id}")
                    _bump(draft)
                await active_session().flush()
            except BaseException:
                await run_in_threadpool(path.unlink, missing_ok=True)
                raise
        return PhotoCompletion(accepted=True, photo=_photo_info(row))


async def _render(row: model.PhotoTable, prepared: PreparedPhoto) -> None:
    key = f"product_drafts/display/{uuid.uuid4().hex}.full.webp"
    paths: list[Path] = []
    try:
        await run_in_threadpool(storage.write_photo_variants, storage._path(key), prepared, paths)
        storage.remember_created_files(paths)
        row.display_key, row.status = key, "ready"
        row.filename, row.extension, row.media_type = (
            prepared.filename, prepared.extension, prepared.media_type)
    except BaseException:
        for path in paths:
            await run_in_threadpool(path.unlink, missing_ok=True)
        raise


def _renderable(row: model.PhotoTable | None) -> bool:
    return row is not None and row.status == "stored" and row.original_key is not None


async def _prepare(row: model.PhotoTable, job: Job) -> PreparedPhoto | None:
    try:
        content = await run_in_threadpool(storage._path(row.original_key or "").read_bytes)
        return await run_process(prepare_photo, content, row.filename)
    except (OSError, ProcessExecutionError, TimeoutError, LangException):
        if job.attempts < 3:
            raise
        return None


async def render_photo(job: Job) -> None:
    draft = await model.get_draft_row(str(job.payload["draft_id"]))
    if draft is None:
        return
    row = await active_session().scalar(select(model.PhotoTable).where(
        model.PhotoTable.id == str(job.payload["photo_id"])))
    if not _renderable(row) or row is None:
        return
    # 解碼不持有來源鎖, 同群組仍能保存新收件與原圖.
    prepared = await _prepare(row, job)
    async with transaction():
        draft = await model.get_draft_row(str(job.payload["draft_id"]), lock=True)
        if draft is None:
            return
        row = await model.get_photo_row(str(job.payload["photo_id"]))
        if not _renderable(row) or row is None:
            return
        try:
            if prepared is None:
                row.status = "failed"
            else:
                await _render(row, prepared)
        except (OSError, ProcessExecutionError, TimeoutError, LangException):
            if job.attempts < 3:
                raise
            row.status = "failed"
        _bump(draft)
        await active_session().flush()
