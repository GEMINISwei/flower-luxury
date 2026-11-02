from datetime import datetime

from sqlalchemy import select

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session

from . import messages, model
from .schema import MessageMove


async def _new_confirmation(source: str, occurred_at: datetime) -> model.CollectionRoundTable:
    row = model.CollectionRoundTable(source_key=source, status="confirmation",
        first_event_at=occurred_at, last_event_at=occurred_at, completed_at=occurred_at)
    active_session().add(row)
    await active_session().flush()
    return row


async def _new_group(
    items: list[model.MessageTable], collection: model.CollectionRoundTable,
    actor: CurrentUser | None = None,
) -> model.DraftTable:
    row = model.DraftTable(source_key=collection.source_key, collection_id=collection.id,
                            collecting=False, received_at=min(item.occurred_at for item in items))
    active_session().add(row)
    await active_session().flush()
    for item in items:
        source = await model.get_draft_row(str(item.draft_id)) if item.draft_id else None
        await messages.move_message(str(item.id), MessageMove(target_draft_id=str(row.id),
            target_version=row.version, source_version=source.version if source else None), actor)
    return row


async def _collection_for_message(message: model.MessageTable) -> model.CollectionRoundTable:
    row = await active_session().scalar(select(model.CollectionRoundTable).where(
        model.CollectionRoundTable.id == message.collection_id)) if message.collection_id else None
    if row is None or row.status == "finalized":
        return await _new_confirmation(message.source_key, message.occurred_at)
    return row
