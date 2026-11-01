from typing import Literal

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import ensure_found
from shared.time import utc_now

from . import model
from .errors import DraftError
from .prefill_config import get_env
from .rules import check_version
from .schema import (
    DraftFields,
    DraftInfo,
    DraftList,
    DraftPhotoInfo,
    DraftUpdate,
    MessageInfo,
    NextReviewInfo,
)


def _message_info(row: model.MessageTable) -> MessageInfo:
    return MessageInfo(**{**row.to_dict(), "id": str(row.id),
                          "draft_id": str(row.draft_id) if row.draft_id else None})


def _photo_info(row: model.PhotoTable, main_id: object = None) -> DraftPhotoInfo:
    ready = row.status == "ready"
    return DraftPhotoInfo(id=str(row.id), message_id=str(row.message_id),
                          draft_id=str(row.draft_id) if row.draft_id else None,
                          status=row.status, sort_order=row.sort_order,
                          is_main=str(row.id) == str(main_id),
                          url=f"/api/product-drafts/photos/{row.id}/file" if ready else None,
                          download_url=(f"/api/product-drafts/photos/{row.id}/download"
                                        if ready else None))


def _bump(row: model.DraftTable, actor: CurrentUser | None = None) -> None:
    row.version += 1
    row.updated_at = utc_now()
    if actor:
        row.updated_by = actor["id"]


async def get_draft(id: str | None) -> DraftInfo:
    row = ensure_found(await model.get_draft_row(id), DraftError.NOT_FOUND)
    photos = [_photo_info(item, row.main_photo_id)
              for item in await model.photos_for(str(row.id))]
    photo_messages = {photo.message_id: photo for photo in photos}
    messages = [_message_info(item) for item in await model.messages_for(str(row.id))]
    for message in messages:
        message.photo = photo_messages.get(message.id)
    return DraftInfo(**{**row.to_dict(), "id": str(row.id),
                        "main_photo_id": str(row.main_photo_id) if row.main_photo_id else None,
                        "manual_fields": row.manual_fields or [], "quotes": row.quotes or [],
                        "prefill_revision": row.prefill_revision or 0,
                        "prefill_configured": get_env().prefill_configured,
                        "prefill_status": row.prefill_status or "idle",
                        "processing": bool(row.processing),
                        "needs_confirmation": bool(row.needs_confirmation)},
                     messages=messages, photos=photos)


async def next_review(source_key: str | None = None) -> NextReviewInfo:
    row = await model.next_review_row(source_key)
    return NextReviewInfo(id=str(row.id) if row else None)


async def get_draft_list(
    limit: int, cursor: str | None = None, direction: Literal["next", "prev"] = "next",
    source_key: str | None = None,
) -> DraftList:
    page = await model.draft_page(limit, cursor, direction, source_key)
    for row in page["list_data"]:
        row["id"] = str(row["id"])
        row["main_photo_id"] = str(row["main_photo_id"]) if row["main_photo_id"] else None
    return DraftList.model_validate(page)


async def update_draft(id: str, form: DraftUpdate, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        row = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        check_version(row.version, form.version)
        previous = DraftFields.model_validate(row.fields).model_dump(mode="json")
        values = form.fields.model_dump(mode="json")
        changed = {key for key, value in values.items() if previous[key] != value}
        row.manual_fields = sorted(set(row.manual_fields or []) | changed | set(form.manual_fields))
        row.fields = values
        _bump(row, actor)
        await active_session().flush()
        return await get_draft(id)
