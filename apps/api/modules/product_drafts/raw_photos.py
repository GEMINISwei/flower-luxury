import uuid
from pathlib import Path

from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from modules.products.public import (
    MAX_BATCH_BYTES,
    PreparedPhoto,
    prepare_photo,
    validate_batch_size,
)
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.jobs.contracts import Job
from shared.jobs.processes import ProcessExecutionError, run_process
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model, storage
from .collection_schema import FinalizedSnapshot
from .errors import DraftError
from .rules import check_version
from .schema import DraftInfo, PhotoCompletion
from .service import _bump, _photo_info, get_draft


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
                if row.draft_id:
                    draft = await model.get_draft_row(str(row.draft_id))
                    if draft:
                        if draft.collection_id is None and draft.finalized_at is not None:
                            await enqueue_job("product_drafts.render_photo", {
                                "photo_id": str(row.id), "draft_id": str(draft.id),
                            }, queue="images", idempotency_key=f"photo:{row.id}")
                            draft.processing = True
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


def _matches_snapshot(row: model.PhotoTable | None, draft: model.DraftTable) -> bool:
    if row is None or row.status != "stored" or row.draft_id != draft.id:
        return False
    # 已結束的舊版暫存沒有新分組快照, 尚未完成的下載仍需走背景加工.
    if draft.finalized_snapshot is None:
        return draft.collection_id is None and draft.finalized_at is not None
    snapshot = FinalizedSnapshot.model_validate(draft.finalized_snapshot)
    return any(item.id == str(row.id) and item.original_key == row.original_key
               for item in snapshot.photos)


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
    if draft is None or draft.finalized_at is None:
        return
    row = await active_session().scalar(select(model.PhotoTable).where(
        model.PhotoTable.id == str(job.payload["photo_id"])))
    if not _matches_snapshot(row, draft) or row is None:
        return
    # 解碼不持有來源鎖, 同群組仍能保存新收件與原圖.
    prepared = await _prepare(row, job)
    async with transaction():
        draft = await model.get_draft_row(str(job.payload["draft_id"]), lock=True)
        if draft is None:
            return
        row = await model.get_photo_row(str(job.payload["photo_id"]))
        if not _matches_snapshot(row, draft) or row is None:
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
        photos = await model.photos_for(str(draft.id))
        draft.processing = any(photo.status in {"pending", "stored"} for photo in photos)
        _bump(draft)
        await active_session().flush()


async def _read_uploads(files: list[UploadFile]) -> list[tuple[bytes, str | None]]:
    contents: list[tuple[bytes, str | None]] = []
    sizes: list[int] = []
    for file in files:
        content = await file.read(MAX_BATCH_BYTES + 1)
        sizes.append(len(content))
        validate_batch_size(sizes, status_code=413)
        contents.append((content, file.filename))
    validate_batch_size(sizes, status_code=413)
    return contents


async def upload_originals(
    id: str, version: int, files: list[UploadFile], actor: CurrentUser,
) -> DraftInfo:
    contents = await _read_uploads(files)
    keys: list[str] = []
    try:
        async with transaction():
            row = ensure_found(await model.get_draft_row(id), DraftError.NOT_FOUND)
            stream = await model.stream_for(row.source_key)
            row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
            check_version(row.version, version)
            if row.finalized_at is not None or row.processing:
                raise LangException(409, DraftError.NOT_READY)
            for content, filename in contents:
                stream.next_sequence += 1
                message = model.MessageTable(source_key=row.source_key,
                    collection_id=row.collection_id,
                    draft_id=row.id, external_id=f"manual:{uuid.uuid4().hex}", kind="image",
                    occurred_at=utc_now(), sequence=stream.next_sequence, sender_id=actor["id"])
                active_session().add(message)
                await active_session().flush()
                photo = model.PhotoTable(message_id=message.id, draft_id=row.id,
                                          sort_order=stream.next_sequence)
                active_session().add(photo)
                await active_session().flush()
                await save_original(str(message.id), content, filename)
                keys.append(photo.original_key or "")
                row.main_photo_id = row.main_photo_id or photo.id
            row.updated_by = actor["id"]
            await active_session().flush()
            return await get_draft(id)
    except BaseException:
        await storage._unlink_keys(keys)
        raise
