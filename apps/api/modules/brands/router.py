from fastapi import APIRouter, Depends

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.schema import UuidText

from . import service
from .schema import BrandCreate, BrandInfo, BrandList, BrandUpdate

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("/")
async def get_brands_route(
    include_inactive: bool = False,
    _: CurrentUser = Depends(check_user_permission()),
) -> BrandList:
    return await service.get_brands(include_inactive)


@router.post("/")
async def create_brand_route(
    form_data: BrandCreate, _: CurrentUser = Depends(check_user_permission()),
) -> BrandInfo:
    return await service.create_brand(form_data)


@router.patch("/{id}")
async def update_brand_route(
    id: UuidText, form_data: BrandUpdate, _: CurrentUser = Depends(check_user_permission()),
) -> BrandInfo:
    return await service.update_brand(id, form_data)


@router.delete("/{id}")
async def delete_brand_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> BrandInfo:
    return await service.delete_brand(id)
