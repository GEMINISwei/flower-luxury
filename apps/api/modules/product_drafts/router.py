from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.schema import PaginationParams, UuidText

from . import messages, photos, review, service
from .schema import (
    ApprovalInfo,
    DiscardInfo,
    DraftInfo,
    DraftList,
    DraftUpdate,
    MainPhoto,
    MessageList,
    MessageMove,
    PhotoOrder,
    VersionRequest,
)

router = APIRouter(prefix="/product-drafts", tags=["product-drafts"])


@router.get("/")
async def get_drafts_route(
    pagination: Annotated[PaginationParams, Depends()], source_key: str | None = None,
    _: CurrentUser = Depends(check_user_permission()),
) -> DraftList:
    return await service.get_draft_list(**pagination.model_dump(), source_key=source_key)


@router.get("/messages")
async def get_unassigned_route(
    pagination: Annotated[PaginationParams, Depends()], source_key: str | None = None,
    _: CurrentUser = Depends(check_user_permission()),
) -> MessageList:
    return await messages.get_unassigned_messages(**pagination.model_dump(), source_key=source_key)


@router.post("/messages/{id}/move")
async def move_message_route(
    id: UuidText, form: MessageMove, actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await messages.move_message(id, form, actor)


@router.get("/photos/{id}/file")
async def get_draft_photo_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> FileResponse:
    stored = await photos.read_photo(id)
    return FileResponse(stored.path, media_type=stored.media_type,
                        headers={"Cache-Control": "private, no-store", "Vary": "Cookie"})


@router.get("/photos/{id}/download")
async def download_draft_photo_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> FileResponse:
    stored = await photos.read_photo(id, original=True)
    return FileResponse(stored.path, media_type=stored.media_type, filename=stored.filename,
                        headers={"Cache-Control": "private, no-store", "Vary": "Cookie"})


@router.get("/{id}")
async def get_draft_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await service.get_draft(id)


@router.patch("/{id}")
async def update_draft_route(
    id: UuidText, form: DraftUpdate, actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await service.update_draft(id, form, actor)


@router.delete("/{id}")
async def discard_draft_route(
    id: UuidText, form: VersionRequest, actor: CurrentUser = Depends(check_user_permission()),
) -> DiscardInfo:
    return await review.discard_draft(id, form, actor)


@router.post("/{id}/approve")
async def approve_draft_route(
    id: UuidText, form: VersionRequest, actor: CurrentUser = Depends(check_user_permission()),
) -> ApprovalInfo:
    return await review.approve_draft(id, form, actor)


@router.patch("/{id}/photos/order")
async def reorder_photos_route(
    id: UuidText, form: PhotoOrder, _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await photos.reorder_photos(id, form)


@router.patch("/{id}/photos/main")
async def set_main_photo_route(
    id: UuidText, form: MainPhoto, _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await photos.set_main_photo(id, form)


@router.delete("/{id}/photos/{photo_id}")
async def delete_photo_route(
    id: UuidText, photo_id: UuidText, form: VersionRequest,
    _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await photos.delete_photo(id, photo_id, form)
