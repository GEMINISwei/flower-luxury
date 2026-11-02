from datetime import datetime

from sqlalchemy import func, select

from shared.db.session import active_session
from shared.db.table import parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import ensure_found
from shared.time import utc_now

from . import batches, grouping, model
from .collection import _remember
from .collection_rules import GroupEvent, propose_groups
from .collection_schema import CollectionInfo
from .errors import DraftError
from .finalization import finalize_draft as finalize_draft
from .finalization import split_message as split_message
from .schema import BatchState, IncomingMessage, IngestResult


async def _current(source: str) -> model.CollectionRoundTable | None:
    return await active_session().scalar(select(model.CollectionRoundTable).where(
        model.CollectionRoundTable.source_key == source,
        model.CollectionRoundTable.status == "collecting",
    ).execution_options(populate_existing=True))


async def _info(row: model.CollectionRoundTable | None, source: str) -> CollectionInfo:
    if row is None:
        return CollectionInfo(source_key=source)
    count = await active_session().scalar(select(func.count()).select_from(model.MessageTable)
        .where(model.MessageTable.collection_id == row.id))
    ids = await active_session().scalars(select(model.DraftTable.id).where(
        model.DraftTable.collection_id == row.id).order_by(model.DraftTable.received_at))
    return CollectionInfo.model_validate({"id": str(row.id), "source_key": source,
        "status": row.status, "message_count": count or 0, "draft_ids": [str(id) for id in ids]})


async def current_collection(source_key: str) -> CollectionInfo:
    return await _info(await _current(source_key), source_key)


async def _receipt_collection(form: IncomingMessage) -> model.CollectionRoundTable | None:
    last = await active_session().scalar(select(func.max(model.CollectionRoundTable.last_event_at))
        .where(model.CollectionRoundTable.source_key == form.source_key,
               model.CollectionRoundTable.status != "collecting"))
    if last is not None and form.occurred_at <= last:
        return None
    row = await _current(form.source_key)
    if row is None:
        row = model.CollectionRoundTable(source_key=form.source_key,
            first_event_at=form.occurred_at, last_event_at=form.occurred_at)
        active_session().add(row)
        await active_session().flush()
    row.first_event_at = min(row.first_event_at, form.occurred_at)
    row.last_event_at = max(row.last_event_at, form.occurred_at)
    return row


async def receive_message(form: IncomingMessage) -> IngestResult:
    async with transaction():
        stream = await model.stream_for(form.source_key)
        if not await _remember(form):
            return IngestResult(duplicate=True)
        collection = await _receipt_collection(form)
        stream.next_sequence += 1
        message = model.MessageTable(**form.model_dump(), sequence=stream.next_sequence,
                                    collection_id=collection.id if collection else None)
        active_session().add(message)
        await active_session().flush()
        active_session().add(model.BufferedEventTable(source_key=form.source_key, kind="message",
            occurred_at=form.occurred_at, message_id=message.id,
            status="pending" if collection else "issue"))
        if form.kind == "image":
            active_session().add(model.PhotoTable(message_id=message.id, status="pending",
                                                  sort_order=stream.next_sequence))
        await active_session().flush()
        if collection is None:
            await model.refresh_source_confirmation(form.source_key)
        return IngestResult(message_id=str(message.id), unassigned=True)


async def _group(row: model.CollectionRoundTable) -> None:
    session = active_session()
    items = list(await session.scalars(select(model.MessageTable).where(
        model.MessageTable.collection_id == row.id).order_by(model.MessageTable.occurred_at,
                                                            model.MessageTable.sequence)))
    indexed = {str(item.id): item for item in items}
    plan = propose_groups([GroupEvent.model_validate(item.to_dict()) for item in items])
    for group in plan.groups:
        await grouping._new_group([indexed[id] for id in group], row)
    for id in plan.unassigned:
        event = await session.scalar(select(model.BufferedEventTable).where(
            model.BufferedEventTable.message_id == parse_uuid(id)))
        if event:
            event.status = "issue"
    await session.flush()
    await model.refresh_source_confirmation(row.source_key)


async def complete_collection(id: str | None) -> CollectionInfo:
    async with transaction():
        row = ensure_found(await active_session().get(model.CollectionRoundTable,
                           parse_uuid(id or "")), DraftError.NOT_FOUND)
        await model.stream_for(row.source_key)
        row = (await active_session().scalars(select(model.CollectionRoundTable).where(
            model.CollectionRoundTable.id == row.id).with_for_update()
            .execution_options(populate_existing=True))).one()
        if row.status == "collecting":
            row.status, row.completed_at = "confirmation", utc_now()
            await _group(row)
        return await _info(row, row.source_key)


async def get_collection_state(source_key: str) -> BatchState:
    state = await batches.get_collection_state(source_key)
    current = await _current(source_key)
    any_round = await active_session().scalar(select(model.CollectionRoundTable.id).where(
        model.CollectionRoundTable.source_key == source_key).limit(1))
    if current is not None or any_round is not None:
        state.collecting = current is not None
    info = await _info(current, source_key)
    state.current_round_id, state.received_count = info.id, info.message_count
    return state


async def finish_collection(source_key: str, occurred_at: datetime) -> BatchState:
    current = await current_collection(source_key)
    if current.id is not None:
        await complete_collection(current.id)
    else:
        await batches.finish_collection(source_key, occurred_at)
    return await get_collection_state(source_key)
