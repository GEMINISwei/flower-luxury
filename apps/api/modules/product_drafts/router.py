from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile
from fastapi.responses import FileResponse

from modules.products.public import PhotoSize
from shared.auth.contracts import CurrentUser
from shared.auth.dependency import check_user_permission
from shared.http.errors import LangException
from shared.http.schema import PaginationParams, UuidText

from . import draft_quotes, messages, photos, prefill, review, service
from .errors import DraftError
from .quote_schema import DraftQuoteUpdate
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


@router.post("/{id}/prefill")
async def retry_prefill_route(
    id: UuidText, form: VersionRequest,
    _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await prefill.retry_prefill(id, form)


@router.post("/{id}/quotes")
async def create_quote_route(
    id: UuidText, form: DraftQuoteUpdate,
    actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await draft_quotes.save_quote(id, form, actor)


@router.patch("/{id}/quotes/{quote_id}")
async def update_quote_route(
    id: UuidText, quote_id: UuidText, form: DraftQuoteUpdate,
    actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await draft_quotes.save_quote(id, form, actor, quote_id=quote_id)


@router.delete("/{id}/quotes/{quote_id}")
async def delete_quote_route(
    id: UuidText, quote_id: UuidText, version: int = Query(ge=1),
    _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await draft_quotes.delete_quote(id, quote_id, VersionRequest(version=version))


def _delete_version(form: VersionRequest | None, version: int | None) -> VersionRequest:
    # 瀏覽器接線使用 query, 保留既有內網呼叫的 body 相容性.
    if version is None:
        if form is None:
            raise LangException(422, DraftError.STALE)
        return form
    if form and form.version != version:
        raise LangException(422, DraftError.STALE)
    return VersionRequest(version=version)


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


@router.delete("/messages/{id}")
async def discard_legacy_message_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()),
) -> DiscardInfo:
    return await messages.discard_legacy_message(id)


@router.post("/messages/{id}/move")
async def move_message_route(
    id: UuidText, form: MessageMove, actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await messages.move_message(id, form, actor)


@router.get("/photos/{id}/file")
async def get_draft_photo_route(
    id: UuidText, _: CurrentUser = Depends(check_user_permission()), size: PhotoSize = "full",
) -> FileResponse:
    stored = await photos.read_photo(id, size=size)
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


@router.post("/{id}/photos")
async def upload_draft_photos_route(
    id: UuidText, version: Annotated[int, Form(ge=1)], files: list[UploadFile],
    actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await photos.upload_photos(id, version, files, actor)


@router.patch("/{id}")
async def update_draft_route(
    id: UuidText, form: DraftUpdate, actor: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await service.update_draft(id, form, actor)


@router.delete("/{id}")
async def discard_draft_route(
    id: UuidText, form: VersionRequest | None = None,
    version: int | None = Query(default=None, ge=1),
    actor: CurrentUser = Depends(check_user_permission()),
) -> DiscardInfo:
    return await review.discard_draft(id, _delete_version(form, version), actor)


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
    id: UuidText, photo_id: UuidText, form: VersionRequest | None = None,
    version: int | None = Query(default=None, ge=1),
    _: CurrentUser = Depends(check_user_permission()),
) -> DraftInfo:
    return await photos.delete_photo(id, photo_id, _delete_version(form, version))
