from typing import Literal

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found

from . import messages, model
from .errors import DraftError
from .schema import BufferedIssueInfo, BufferedIssueList, DiscardInfo, MessageMove, ResolveIssue
from .service import _photo_info


async def get_issues(limit: int, cursor: str | None = None,
                     direction: Literal["next", "prev"] = "next",
                     source_key: str | None = None) -> BufferedIssueList:
    page = await model.buffered_issue_page(limit, cursor, direction, source_key)
    items = []
    for row in page["list_data"]:
        message = await model.get_message_row(str(row["message_id"])) if row["message_id"] else None
        photo = await model.photo_for_message(str(message.id)) if message else None
        items.append(BufferedIssueInfo(id=str(row["id"]), source_key=row["source_key"],
            occurred_at=row["occurred_at"], kind=message.kind if message else row["kind"],
            text=message.text if message else None, photo=_photo_info(photo) if photo else None))
    return BufferedIssueList.model_validate({**page, "list_data": items})


async def resolve_issue(id: str, form: ResolveIssue, actor: CurrentUser) -> DiscardInfo:
    async with transaction():
        event = ensure_found(await model.get_buffered_event(id, lock=True), DraftError.NOT_FOUND)
        if event.status != "issue":
            raise LangException(409, DraftError.NOT_READY)
        if form.action == "attach":
            if not event.message_id or not form.target_draft_id or form.target_version is None:
                raise LangException(422, DraftError.INVALID_TARGET)
            target = ensure_found(await model.get_draft_row(form.target_draft_id),
                                  DraftError.NOT_FOUND)
            if target.collecting or target.processing:
                raise LangException(409, DraftError.NOT_READY)
            await messages.move_message(str(event.message_id), MessageMove(
                target_draft_id=form.target_draft_id, target_version=form.target_version), actor)
        elif event.message_id:
            await messages.discard_legacy_message(str(event.message_id))
        else:
            await active_session().delete(event)
            await active_session().flush()
            await model.refresh_source_confirmation(event.source_key)
        return DiscardInfo(id=id)
