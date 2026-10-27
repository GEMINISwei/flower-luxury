from typing import Annotated

from fastapi import APIRouter, Depends, Query

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.schema import PaginationParams, UuidText

from . import service
from .schema import (
    ProductCategory,
    ProductCreate,
    ProductInfo,
    ProductList,
    ProductStatus,
    StatusHistoryList,
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
