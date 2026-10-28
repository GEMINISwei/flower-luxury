from starlette.concurrency import run_in_threadpool

from modules.products.public import prepare_photo, validate_batch_size
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found

from . import model, storage
from .errors import DraftError
from .rules import check_version
from .schema import DraftInfo, MainPhoto, PhotoCompletion, PhotoOrder, StoredFile, VersionRequest
from .service import _bump, _photo_info, get_draft


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
                prepared = await run_in_threadpool(prepare_photo, content, filename)
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


async def read_photo(id: str, *, original: bool = False) -> StoredFile:
    row = ensure_found(await model.get_photo_row(id), DraftError.NOT_FOUND)
    if row.status != "ready":
        raise LangException(409, DraftError.PHOTO_NOT_READY)
    key = ensure_found(row.original_key if original else row.display_key, DraftError.NOT_FOUND)
    path = storage._path(key)
    ensure_found(await run_in_threadpool(path.is_file), DraftError.NOT_FOUND)
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
