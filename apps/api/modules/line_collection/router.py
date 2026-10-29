from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.permissions import Permission
from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.errors import LangException

from . import service
from .config import LineSettings
from .errors import LineError
from .rules import MAX_WEBHOOK_BYTES
from .schema import GroupInfo, GroupList, GroupUpdate, WebhookResult

router = APIRouter(prefix="/line", tags=["line"])


@router.post("/webhook")
async def webhook_route(request: Request) -> WebhookResult:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_WEBHOOK_BYTES:
            raise LangException(413, LineError.TOO_LARGE)
        body.extend(chunk)
    env = request.app.state.env
    settings = LineSettings(line_channel_secret=env.line_channel_secret,
                            line_channel_access_token=env.line_channel_access_token)
    return await service.receive_webhook(
        bytes(body), request.headers.get("x-line-signature"), settings,
    )


@router.get("/groups")
async def group_list_route(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None, direction: Literal["next", "prev"] = "next",
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> GroupList:
    return await service.list_groups(limit=limit, cursor=cursor, direction=direction)


@router.patch("/groups/{id}")
async def group_update_route(
    id: str, form: GroupUpdate,
    _: CurrentUser = Depends(check_user_permission(Permission.ALL)),
) -> GroupInfo:
    return await service.update_group(id, form)
