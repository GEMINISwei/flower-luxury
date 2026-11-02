import uuid

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from modules.products.public import (
    PhotoSize,
    PreparedPhoto,
    prepare_photo,
    read_batch,
    resolve_photo_variant,
    validate_batch_size,
)
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.jobs.processes import ProcessExecutionError, run_process
from shared.time import utc_now

from . import model, storage
from .errors import DraftError
from .rules import check_version
from .schema import DraftInfo, MainPhoto, PhotoCompletion, PhotoOrder, StoredFile, VersionRequest
from .service import _bump, _photo_info, get_draft


async def upload_photos(
    id: str, version: int, files: list[UploadFile], actor: CurrentUser,
) -> DraftInfo:
    prepared = await read_batch(files, too_large_status=413)
    keys: list[str] = []
    try:
        async with transaction():
            draft, rows = await _owned(id, version)
            stream = await model.stream_for(draft.source_key)
            order = max((row.sort_order for row in rows), default=0)
            for item in prepared.photos:
                stream.next_sequence += 1
                order += 1
                photo = await _store_manual(draft, item, stream.next_sequence, order, actor)
                keys.extend(key for key in (photo.original_key, photo.display_key) if key)
                if draft.main_photo_id is None:
                    draft.main_photo_id = photo.id
            _bump(draft, actor)
            await active_session().flush()
            return await get_draft(id)
    except BaseException:
        await storage._unlink_keys(keys)
        raise


async def _store_manual(
    draft: model.DraftTable, prepared: PreparedPhoto, sequence: int, order: int, actor: CurrentUser,
) -> model.PhotoTable:
    # 人工補圖不推進 LINE 的時間游標或文字分組狀態.
    message = model.MessageTable(source_key=draft.source_key, draft_id=draft.id,
                                 external_id=f"manual:{uuid.uuid4().hex}", kind="image",
                                 occurred_at=utc_now(), sequence=sequence,
                                 sender_id=actor["id"], sender_name=actor["username"])
    active_session().add(message)
    await active_session().flush()
    row = model.PhotoTable(message_id=message.id, draft_id=draft.id,
                           status="ready", sort_order=order)
    active_session().add(row)
    await storage.write_photo(row, prepared)
    await active_session().flush()
    return row


async def complete_photo(id: str | None, content: bytes, filename: str | None) -> PhotoCompletion:
    keys: list[str] = []
    try:
        async with transaction():
            message = await model.get_message_row(id, lock=True)
            if message is None:
                return PhotoCompletion(accepted=False)
            row = await model.photo_for_message(id)
            if row is None:
                return PhotoCompletion(accepted=False)
            if row.status != "ready":
                validate_batch_size([len(content)])
                try:
                    prepared = await run_process(prepare_photo, content, filename)
                except ProcessExecutionError as error:
                    raise LangException(422, DraftError.INVALID_PHOTOS) from error
                await storage.write_photo(row, prepared)
                keys = [key for key in (row.original_key, row.display_key) if key]
                row.status = "ready"
                await _touch_draft(row)
                await active_session().flush()
            return PhotoCompletion(accepted=True, photo=_photo_info(row))
    except BaseException:
        await storage._unlink_keys(keys)
        raise


async def _touch_draft(row: model.PhotoTable) -> None:
    if row.draft_id:
        draft = await model.get_draft_row(str(row.draft_id))
        if draft:
            _bump(draft)


async def mark_photo_failed(id: str | None) -> PhotoCompletion:
    async with transaction():
        message = await model.get_message_row(id, lock=True)
        row = await model.photo_for_message(id) if message else None
        if row is None:
            return PhotoCompletion(accepted=False)
        if row.status != "ready":
            row.status = "failed"
            await _touch_draft(row)
            await active_session().flush()
        return PhotoCompletion(accepted=True, photo=_photo_info(row))


async def read_photo(id: str, *, original: bool = False, size: PhotoSize = "full") -> StoredFile:
    row = ensure_found(await model.get_photo_row(id), DraftError.NOT_FOUND)
    if row.status != "ready":
        raise LangException(409, DraftError.PHOTO_NOT_READY)
    key = ensure_found(row.original_key if original else row.display_key, DraftError.NOT_FOUND)
    path = storage._path(key)
    if original:
        exists = await run_in_threadpool(path.is_file)
        ensure_found(exists or None, DraftError.NOT_FOUND)
    else:
        source = storage._path(row.original_key) if row.original_key else None
        try:
            path = (await run_in_threadpool(resolve_photo_variant, path, source, size)).path
        except FileNotFoundError as error:
            raise LangException(404, DraftError.NOT_FOUND) from error
    media_type = (row.media_type or "image/png") if original else "image/webp"
    return StoredFile(path=path, media_type=media_type, filename=row.filename or "photo.webp")


async def _owned(id: str, version: int) -> tuple[model.DraftTable, list[model.PhotoTable]]:
    draft = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
    check_version(draft.version, version)
    return draft, await model.photos_for(id)


async def reorder_photos(id: str, form: PhotoOrder) -> DraftInfo:
    async with transaction():
        draft, rows = await _owned(id, form.version)
        if set(form.photo_ids) != {str(row.id) for row in rows}:
            raise LangException(422, DraftError.INVALID_PHOTOS)
        order = {photo_id: index for index, photo_id in enumerate(form.photo_ids, 1)}
        for row in rows:
            row.sort_order = order[str(row.id)]
        _bump(draft)
        await active_session().flush()
        return await get_draft(id)


async def set_main_photo(id: str, form: MainPhoto) -> DraftInfo:
    async with transaction():
        draft, rows = await _owned(id, form.version)
        photo = next((row for row in rows if str(row.id) == form.photo_id), None)
        if photo is None:
            raise LangException(422, DraftError.INVALID_PHOTOS)
        draft.main_photo_id = photo.id
        _bump(draft)
        await active_session().flush()
        return await get_draft(id)


async def delete_photo(id: str, photo_id: str, form: VersionRequest) -> DraftInfo:
    async with transaction():
        draft, rows = await _owned(id, form.version)
        photo = ensure_found(next((row for row in rows if str(row.id) == photo_id), None),
                             DraftError.NOT_FOUND)
        message = ensure_found(
            await model.get_message_row(str(photo.message_id)), DraftError.NOT_FOUND,
        )
        await storage.schedule_cleanup([photo])
        await active_session().delete(message)
        if draft.main_photo_id == photo.id:
            draft.main_photo_id = next((row.id for row in rows if row.id != photo.id), None)
        _bump(draft)
        await active_session().flush()
        return await get_draft(id)
