from collections.abc import AsyncIterable, Awaitable, Callable
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from shared.auth.contracts import CurrentUser
from shared.db.transaction import transaction
from shared.http.errors import LangException

from . import photos, service
from .errors import PhotoError
from .images import PreparedPhoto
from .schema import ProductCreate, ProductInfo


async def create_imported_product(
    form: ProductCreate, prepared: list[PreparedPhoto] | AsyncIterable[PreparedPhoto],
    actor: CurrentUser, *, main_index: int = 0,
    on_created: Callable[[ProductInfo], Awaitable[None]] | None = None,
) -> ProductInfo:
    if main_index < 0 or (isinstance(prepared, list) and main_index >= len(prepared)):
        raise LangException(422, PhotoError.INVALID)
    paths: list[Path] = []
    try:
        async with transaction():
            product = await service.create_product(form, actor)
            stored = await photos.store_prepared_photos(
                product.id, prepared, actor, created_paths=paths,
            )
            if main_index >= len(stored.list_data):
                raise LangException(422, PhotoError.INVALID)
            await photos.set_main_photo(product.id, stored.list_data[main_index].id, actor)
            if on_created:
                await on_created(product)
            return await service.get_product(product.id)
    except BaseException:
        # SAVEPOINT 回滾後外層仍可能 commit, 所以匯入失敗要即時清理本次寫入。
        for path in paths:
            await run_in_threadpool(path.unlink, missing_ok=True)
        raise
