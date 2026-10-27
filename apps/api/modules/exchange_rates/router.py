from fastapi import APIRouter, Depends

from app.permissions import Permission
from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission

from . import service
from .schema import ExchangeRateSettings, ExchangeRateUpdate

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("/settings")
async def get_exchange_settings_route(
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> ExchangeRateSettings:
    return await service.get_settings()


@router.patch("/settings")
async def update_exchange_settings_route(
    form_data: ExchangeRateUpdate,
    actor: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> ExchangeRateSettings:
    return await service.update_settings(form_data, actor)
