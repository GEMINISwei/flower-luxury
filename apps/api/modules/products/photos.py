import uuid
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path

from fastapi import UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import ensure_found
from shared.time import utc_now

from .errors import ProductError
from .images import MAX_BATCH_BYTES, PreparedPhoto, prepare_photo, validate_batch_size
from .model import (
    ProductPhotoTable,
    ProductTable,
    lock_product,
    owned_photo,
    readable_photo,
    rows_for,
)
from .schema import OriginalPhotoFile, PhotoFile, PhotoInfo, PhotoList
from .storage import track_files

UPLOADS_DIR = Path("/app/uploads/products")


def info(row: ProductPhotoTable, main_id: str | None) -> PhotoInfo:
    return PhotoInfo(id=str(row.id), url=f"/api/products/photos/{row.id}/file",
                     is_main=str(row.id) == main_id, sort_order=row.sort_order,
                     download_url=(f"/api/products/photos/{row.id}/download"
                                   if row.original_storage_key else None))


class PreparedPhotoBatch(BaseModel):
    photos: list[PreparedPhoto]


async def read_batch(files: list[UploadFile]) -> PreparedPhotoBatch:
    data: list[bytes] = []
    total = 0
    for file in files:
        content = await file.read(MAX_BATCH_BYTES - total + 1)
        total += len(content)
        validate_batch_size([len(item) for item in data] + [len(content)])
        data.append(content)
    validate_batch_size([len(item) for item in data])
    return PreparedPhotoBatch(photos=[
        await run_in_threadpool(prepare_photo, content, file.filename)
        for content, file in zip(data, files, strict=True)
    ])


def _storage_path(key: str) -> Path:
    return UPLOADS_DIR / Path(key).relative_to("products")


async def _store_photo(
    photo: PreparedPhoto, product: ProductTable, order: int, actor: CurrentUser, paths: list[Path],
) -> ProductPhotoTable:
    key = uuid.uuid4().hex
    original_key = f"products/originals/{key}.{photo.extension}"
    display_key = f"products/display/{key}.webp"
    for storage_key, data in [(original_key, photo.original), (display_key, photo.display)]:
        path = _storage_path(storage_key)
        paths.append(path)
        await run_in_threadpool(path.parent.mkdir, parents=True, exist_ok=True)
        await run_in_threadpool(path.write_bytes, data)
    row = ProductPhotoTable(product_id=product.id, storage_key=display_key,
                            original_storage_key=original_key, original_filename=photo.filename,
                            original_media_type=photo.media_type, sort_order=order,
                            uploaded_by=actor["id"])
    active_session().add(row)
    await active_session().flush()
    return row


async def upload_photos(id: str, files: list[UploadFile], actor: CurrentUser) -> PhotoList:
    converted = await read_batch(files)
    return await store_prepared_photos(id, converted.photos, actor)


async def store_prepared_photos(
    id: str, prepared: list[PreparedPhoto] | AsyncIterable[PreparedPhoto], actor: CurrentUser,
    *, created_paths: list[Path] | None = None,
) -> PhotoList:
    paths: list[Path] = created_paths if created_paths is not None else []
    try:
        async with transaction():
            product = await lock_product(id)
            existing = await rows_for(id)
            order = max((row.sort_order for row in existing), default=0)
            async for content in _prepared_items(prepared):
                order += 1
                row = await _store_photo(content, product, order, actor, paths)
                if product.main_photo_id is None:
                    product.main_photo_id = str(row.id)
            product.updated_by, product.updated_at = actor["id"], utc_now()
            await active_session().flush()
            track_files(created=paths, deleted=[])
            return await list_photos(id)
    except BaseException:
        for path in paths:
            await run_in_threadpool(path.unlink, missing_ok=True)
        raise


async def _prepared_items(
    prepared: list[PreparedPhoto] | AsyncIterable[PreparedPhoto],
) -> AsyncIterator[PreparedPhoto]:
    if isinstance(prepared, list):
        for photo in prepared:
            yield photo
    else:
        async for photo in prepared:
            yield photo


async def list_photos(id: str) -> PhotoList:
    product = await lock_product(id, editable=False)
    rows = await rows_for(id)
    return PhotoList(list_data=[info(row, product.main_photo_id) for row in rows], count=len(rows))


async def set_main_photo(id: str, photo_id: str, actor: CurrentUser) -> PhotoList:
    async with transaction():
        product = await lock_product(id)
        await owned_photo(id, photo_id)
        product.main_photo_id = photo_id
        product.updated_by, product.updated_at = actor["id"], utc_now()
        await active_session().flush()
        return await list_photos(id)


async def delete_photo(id: str, photo_id: str, actor: CurrentUser) -> PhotoList:
    async with transaction():
        product = await lock_product(id)
        row = await owned_photo(id, photo_id)
        paths = [_storage_path(row.storage_key)]
        if row.original_storage_key:
            paths.append(_storage_path(row.original_storage_key))
        await active_session().delete(row)
        await active_session().flush()
        if product.main_photo_id == photo_id:
            remaining = await rows_for(id)
            product.main_photo_id = str(remaining[0].id) if remaining else None
        product.updated_by, product.updated_at = actor["id"], utc_now()
        await active_session().flush()
        track_files(created=[], deleted=paths)
        return await list_photos(id)


async def photo_path(photo_id: str) -> PhotoFile:
    row = await readable_photo(photo_id)
    path = _storage_path(row.storage_key)
    exists = await run_in_threadpool(path.is_file)
    ensure_found(exists or None, ProductError.PHOTO_NOT_FOUND)
    return PhotoFile(path=path)


async def original_file(photo_id: str) -> OriginalPhotoFile:
    row = await readable_photo(photo_id)
    key = ensure_found(row.original_storage_key, ProductError.ORIGINAL_UNAVAILABLE)
    path = _storage_path(key)
    exists = await run_in_threadpool(path.is_file)
    ensure_found(exists or None, ProductError.ORIGINAL_UNAVAILABLE)
    return OriginalPhotoFile(path=path,
                             filename=ensure_found(row.original_filename,
                                                   ProductError.ORIGINAL_UNAVAILABLE),
                             media_type=ensure_found(row.original_media_type,
                                                     ProductError.ORIGINAL_UNAVAILABLE))
