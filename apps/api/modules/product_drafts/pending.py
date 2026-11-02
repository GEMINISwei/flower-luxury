from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found

from . import model, storage
from .errors import DraftError
from .rules import check_version
from .schema import DraftInfo, VersionRequest
from .service import _bump, get_draft


async def _pending(draft_id: str, message_id: str | None,
                   form: VersionRequest) -> tuple[model.DraftTable, model.MessageTable]:
    draft = ensure_found(await model.get_draft_row(draft_id, lock=True), DraftError.NOT_FOUND)
    check_version(draft.version, form.version)
    message = ensure_found(await model.get_message_row(message_id), DraftError.NOT_FOUND)
    if message.draft_id != draft.id or not message.pending:
        raise LangException(409, DraftError.STALE)
    return draft, message


async def accept_message(draft_id: str, message_id: str | None, form: VersionRequest,
                         actor: CurrentUser) -> DraftInfo:
    async with transaction():
        draft, message = await _pending(draft_id, message_id, form)
        message.pending = False
        photo = await model.photo_for_message(str(message.id))
        if photo:
            photo.draft_id = draft.id
            photo.sort_order = max((row.sort_order for row in
                                    await model.photos_for(draft_id)), default=0) + 1
            draft.main_photo_id = draft.main_photo_id or photo.id
        draft.has_text = draft.has_text or message.kind == "text"
        _bump(draft, actor)
        await active_session().flush()
        return await get_draft(draft_id)


async def ignore_message(draft_id: str, message_id: str | None, form: VersionRequest,
                         actor: CurrentUser) -> DraftInfo:
    async with transaction():
        draft, message = await _pending(draft_id, message_id, form)
        photo = await model.photo_for_message(str(message.id))
        if photo:
            await storage.schedule_cleanup([photo])
        await active_session().delete(message)
        _bump(draft, actor)
        await active_session().flush()
        return await get_draft(draft_id)
