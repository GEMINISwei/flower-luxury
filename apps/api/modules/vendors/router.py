from fastapi import APIRouter, Depends

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.schema import UuidText

from . import service
from .schema import VendorCreate, VendorInfo, VendorList, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/")
async def get_vendors_route(
    include_inactive: bool = False, _: CurrentUser = Depends(check_user_permission()),
) -> VendorList:
    return await service.get_vendors(include_inactive)


@router.post("/")
async def create_vendor_route(
    form_data: VendorCreate, _: CurrentUser = Depends(check_user_permission()),
) -> VendorInfo:
    return await service.create_vendor(form_data)


@router.patch("/{id}")
async def update_vendor_route(
    id: UuidText, form_data: VendorUpdate, _: CurrentUser = Depends(check_user_permission()),
) -> VendorInfo:
    return await service.update_vendor(id, form_data)


@router.delete("/{id}")
async def delete_vendor_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> VendorInfo:
    return await service.delete_vendor(id)
