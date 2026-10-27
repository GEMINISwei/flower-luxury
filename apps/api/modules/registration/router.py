from fastapi import APIRouter, Depends, Request

from app.permissions import Permission
from modules.users.public import UserOperate
from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.rate_limit import RateLimiter, client_ip

from . import service
from .schema import RegistrationSettings, RegistrationSettingsUpdate, SignupRequest

router = APIRouter(prefix="/registration", tags=["registration"])
signup_limiter = RateLimiter(max_attempts=10, window_seconds=300)


@router.post("/signup")
async def signup_route(request: Request, form_data: SignupRequest) -> UserOperate:
    """使用共用註冊碼建立立即啟用的店長帳號."""
    signup_limiter.check(client_ip(request))
    return await service.signup(form_data)


@router.get("/settings")
async def get_registration_settings_route(
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> RegistrationSettings:
    """取得註冊碼設定狀態."""
    return await service.get_settings()


@router.patch("/settings")
async def update_registration_settings_route(
    form_data: RegistrationSettingsUpdate,
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> RegistrationSettings:
    """設定或更換共用註冊碼.儲存後後續註冊須使用新碼."""
    return await service.update_settings(form_data)
