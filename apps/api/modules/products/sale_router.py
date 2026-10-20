from fastapi import APIRouter, Depends

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.schema import UuidText

from . import sales
from .quote_schema import SaleCreate, SaleInfo, SaleList

router = APIRouter(prefix="/products/{id}/sales", tags=["product sales"])


@router.get("")
async def get_sales_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> SaleList:
    return await sales.get_sales(id)


@router.post("")
async def confirm_sale_route(
    id: UuidText, form_data: SaleCreate, actor: CurrentUser = Depends(check_user_permission()),
) -> SaleInfo:
    return await sales.confirm_sale(id, form_data, actor)
