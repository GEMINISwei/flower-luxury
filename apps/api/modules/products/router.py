from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import FileResponse

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.db.session import release_connection
from shared.http.schema import PaginationParams, UuidText

from . import photos, service
from .schema import (
    MainPhotoUpdate,
    PhotoList,
    ProductCategory,
    ProductCreate,
    ProductInfo,
    ProductList,
    ProductStatus,
    StatusChange,
    StatusHistoryList,
    StatusReturn,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/")
async def get_products_route(
    pagination: Annotated[PaginationParams, Depends()],
    keyword: str | None = None, brand_id: UuidText | None = None,
    category: ProductCategory | None = None, status: ProductStatus | None = None,
    color: str | None = None, year: int | None = Query(default=None, ge=1, le=9999),
    _: CurrentUser = Depends(check_user_permission()),
) -> ProductList:
    return await service.get_product_list(**pagination.model_dump(), keyword=keyword,
                                         brand_id=brand_id, category=category, status=status,
                                         color=color, year=year)


@router.post("/")
async def create_product_route(
    form_data: ProductCreate, actor: CurrentUser = Depends(check_user_permission()),
) -> ProductInfo:
    return await service.create_product(form_data, actor)


@router.get("/photos/{photo_id}/file")
async def get_photo_file_route(
    photo_id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> FileResponse:
    return FileResponse((await photos.photo_path(photo_id)).path, media_type="image/webp",
                        headers={"Cache-Control": "private, no-store", "Vary": "Cookie"})


@router.get("/photos/{photo_id}/download")
async def download_photo_route(
    photo_id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> FileResponse:
    original = await photos.original_file(photo_id)
    return FileResponse(original.path, media_type=original.media_type, filename=original.filename,
                        headers={"Cache-Control": "private, no-store", "Vary": "Cookie"})


@router.get("/{id}")
async def get_product_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> ProductInfo:
    return await service.get_product(id)


@router.patch("/{id}")
async def update_product_route(
    id: UuidText, form_data: ProductCreate,
    actor: CurrentUser = Depends(check_user_permission()),
) -> ProductInfo:
    return await service.update_product(id, form_data, actor)


@router.delete("/{id}")
async def delete_product_route(
    id: UuidText, actor: CurrentUser = Depends(check_user_permission()),
) -> ProductInfo:
    return await service.delete_product(id, actor)


@router.get("/{id}/history")
async def get_history_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> StatusHistoryList:
    return await service.get_history(id)


@router.get("/{id}/photos")
async def get_photos_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> PhotoList:
    return await photos.list_photos(id)


@router.post("/{id}/photos")
async def upload_photos_route(
    id: UuidText, files: list[UploadFile],
    actor: CurrentUser = Depends(check_user_permission()),
) -> PhotoList:
    await release_connection()
    return await photos.upload_photos(id, files, actor)


@router.patch("/{id}/photos/main")
async def set_main_photo_route(
    id: UuidText, form_data: MainPhotoUpdate,
    actor: CurrentUser = Depends(check_user_permission()),
) -> PhotoList:
    return await photos.set_main_photo(id, form_data.photo_id, actor)


@router.delete("/{id}/photos/{photo_id}")
async def delete_photo_route(
    id: UuidText, photo_id: UuidText, actor: CurrentUser = Depends(check_user_permission()),
) -> PhotoList:
    return await photos.delete_photo(id, photo_id, actor)


@router.post("/{id}/status")
async def change_status_route(
    id: UuidText, form_data: StatusChange, actor: CurrentUser = Depends(check_user_permission()),
) -> ProductInfo:
    return await service.change_status(id, form_data, actor)


@router.post("/{id}/return")
async def return_status_route(
    id: UuidText, form_data: StatusReturn, actor: CurrentUser = Depends(check_user_permission()),
) -> ProductInfo:
    return await service.return_status(id, form_data, actor)
