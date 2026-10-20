import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.table import parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import ensure_found
from shared.time import utc_now

from .images import MAX_BATCH_BYTES, decode_photo, validate_batch_size
from .model import ProductPhotoTable, ProductTable, lock_product
from .rules import ProductError
from .schema import PhotoInfo, PhotoList
from .storage import track_files

UPLOADS_DIR = Path("/app/uploads/products")


def info(row: ProductPhotoTable, main_id: str | None) -> PhotoInfo:
    return PhotoInfo(id=str(row.id), url=f"/api/products/photos/{row.id}/file",
                     is_main=str(row.id) == main_id, sort_order=row.sort_order)


async def rows_for(id: str) -> list[ProductPhotoTable]:
    return list((await active_session().scalars(select(ProductPhotoTable).where(
        ProductPhotoTable.product_id == parse_uuid(id),
    ).order_by(ProductPhotoTable.sort_order, ProductPhotoTable.id))).all())


async def read_batch(files: list[UploadFile]) -> list[bytes]:
    data: list[bytes] = []
    total = 0
    for file in files:
        content = await file.read(MAX_BATCH_BYTES - total + 1)
        total += len(content)
        validate_batch_size([len(item) for item in data] + [len(content)])
        data.append(content)
    validate_batch_size([len(item) for item in data])
    return [await run_in_threadpool(decode_photo, content) for content in data]


async def upload_photos(id: str, files: list[UploadFile], actor: CurrentUser) -> PhotoList:
    converted = await read_batch(files)
    paths: list[Path] = []
    try:
        async with transaction():
            product = await lock_product(id)
            existing = await rows_for(id)
            order = max((row.sort_order for row in existing), default=0)
            await run_in_threadpool(UPLOADS_DIR.mkdir, parents=True, exist_ok=True)
            for offset, content in enumerate(converted, 1):
                path = UPLOADS_DIR / f"{uuid.uuid4().hex}.webp"
                paths.append(path)
                await run_in_threadpool(path.write_bytes, content)
                row = ProductPhotoTable(product_id=product.id,
                                        storage_key=f"products/{path.name}",
                                        sort_order=order + offset, uploaded_by=actor["id"])
                active_session().add(row)
                await active_session().flush()
                if product.main_photo_id is None:
                    product.main_photo_id = str(row.id)
            product.updated_by, product.updated_at = actor["id"], utc_now()
            await active_session().flush()
            track_files(created=paths, deleted=[])
            return await list_photos(id)
    except Exception:
        for path in paths:
            await run_in_threadpool(path.unlink, missing_ok=True)
        raise


async def list_photos(id: str) -> PhotoList:
    product = await lock_product(id, editable=False)
    rows = await rows_for(id)
    return PhotoList(list_data=[info(row, product.main_photo_id) for row in rows], count=len(rows))


async def owned_photo(id: str, photo_id: str) -> ProductPhotoTable:
    row = await active_session().scalar(select(ProductPhotoTable).where(
        ProductPhotoTable.id == parse_uuid(photo_id),
        ProductPhotoTable.product_id == parse_uuid(id),
    ))
    return ensure_found(row, ProductError.PHOTO_NOT_FOUND)


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
        path = UPLOADS_DIR / Path(row.storage_key).name
        await active_session().delete(row)
        await active_session().flush()
        if product.main_photo_id == photo_id:
            remaining = await rows_for(id)
            product.main_photo_id = str(remaining[0].id) if remaining else None
        product.updated_by, product.updated_at = actor["id"], utc_now()
        await active_session().flush()
        track_files(created=[], deleted=[path])
        return await list_photos(id)


async def photo_path(photo_id: str) -> Path:
    row = ensure_found(await active_session().scalar(select(ProductPhotoTable).join(
        ProductTable, ProductPhotoTable.product_id == ProductTable.id,
    ).where(ProductPhotoTable.id == parse_uuid(photo_id), ProductTable.deleted_at.is_(None))),
        ProductError.PHOTO_NOT_FOUND)
    path = UPLOADS_DIR / Path(row.storage_key).name
    exists = await run_in_threadpool(path.is_file)
    ensure_found(exists or None, ProductError.PHOTO_NOT_FOUND)
    return path
