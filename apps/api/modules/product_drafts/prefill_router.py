from fastapi import APIRouter, Depends

from app.permissions import Permission
from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission

from . import prefill_settings
from .prefill_schema import PrefillPreview, PrefillSettingsInfo, PrefillSettingsUpdate
from .schema import DraftFields

router = APIRouter(prefix="/draft-prefill", tags=["draft-prefill"])


@router.get("/settings")
async def get_settings_route(
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> PrefillSettingsInfo:
    return await prefill_settings.get_settings()


@router.patch("/settings")
async def update_settings_route(
    form: PrefillSettingsUpdate,
    actor: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> PrefillSettingsInfo:
    return await prefill_settings.update_settings(form, actor)


@router.post("/preview")
async def preview_route(
    form: PrefillPreview,
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> DraftFields:
    return await prefill_settings.preview(form)
