from typing import Literal

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found

from . import model, storage
from .errors import DraftError
from .rules import check_version
from .schema import DiscardInfo, DraftInfo, MessageList, MessageMove, WithdrawalResult
from .service import _bump, _photo_info, get_draft


async def get_unassigned_messages(
    limit: int, cursor: str | None = None, direction: Literal["next", "prev"] = "next",
    source_key: str | None = None,
) -> MessageList:
    page = MessageList.model_validate(
        await model.unassigned_page(limit, cursor, direction, source_key),
    )
    for item in page.list_data:
        if item.kind == "image":
            photo = await model.photo_for_message(item.id)
            item.photo = _photo_info(photo) if photo else None
    return page


async def move_message(id: str | None, form: MessageMove, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        message = ensure_found(await model.get_message_row(id, lock=True), DraftError.NOT_FOUND)
        target = ensure_found(await model.get_draft_row(form.target_draft_id), DraftError.NOT_FOUND)
        if message.source_key != target.source_key:
            raise LangException(409, DraftError.DIFFERENT_SOURCE)
        check_version(target.version, form.target_version)
        source = await model.get_draft_row(str(message.draft_id)) if message.draft_id else None
        if source:
            check_version(source.version, form.source_version)
        if source and source.id == target.id:
            return await get_draft(str(target.id))
        photo = await model.photo_for_message(id)
        if photo:
            photo.draft_id = target.id
            target_photos = await model.photos_for(str(target.id))
            photo.sort_order = max((row.sort_order for row in target_photos), default=0) + 1
            if target.main_photo_id is None:
                target.main_photo_id = photo.id
            if source and source.main_photo_id == photo.id:
                remaining = await model.photos_for(str(source.id))
                source.main_photo_id = next(
                    (row.id for row in remaining if row.id != photo.id), None,
                )
        stream = await model.stream_for(message.source_key)
        stream.next_sequence += 1
        message.sequence = stream.next_sequence
        message.draft_id = target.id
        target.has_text = target.has_text or message.kind == "text"
        for draft in (source, target):
            if draft:
                _bump(draft, actor)
        await active_session().flush()
        return await get_draft(str(target.id))


async def withdraw_message(source_key: str, external_id: str,
                           draft_id: str | None = None) -> WithdrawalResult:
    async with transaction():
        await model.stream_for(source_key)
        message = await model.message_by_external_id(source_key, external_id)
        if message is None:
            receipt = await model.receipt_for(model.message_fingerprint(source_key, external_id))
            if receipt and receipt.approved_product_id:
                return WithdrawalResult(product_id=receipt.approved_product_id)
            approval = await model.approval_for(draft_id) if draft_id else None
            return WithdrawalResult(product_id=str(approval.product_id) if approval else None)
        draft = await model.get_draft_row(str(message.draft_id)) if message.draft_id else None
        photo = await model.photo_for_message(str(message.id))
        if photo:
            await storage.schedule_cleanup([photo])
            if draft and draft.main_photo_id == photo.id:
                others = await model.photos_for(str(draft.id))
                draft.main_photo_id = next((row.id for row in others if row.id != photo.id), None)
        await active_session().delete(message)
        if draft:
            _bump(draft)
        await active_session().flush()
        return WithdrawalResult(removed=True)


async def discard_legacy_message(id: str) -> DiscardInfo:
    async with transaction():
        message = ensure_found(await model.get_message_row(id, lock=True), DraftError.NOT_FOUND)
        if message.draft_id is not None:
            raise LangException(409, DraftError.STALE)
        photo = await model.photo_for_message(id)
        if photo:
            await storage.schedule_cleanup([photo])
        await active_session().delete(message)
        await active_session().flush()
        return DiscardInfo(id=id)
