from datetime import datetime, timedelta
from typing import Literal

from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.jobs.contracts import Job
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import batches, model, storage
from .collection import _remember
from .schema import BatchControl, BatchState, IncomingMessage, IngestResult

BUFFER_SECONDS = 180


async def _schedule(stream: model.StreamTable) -> None:
    deadline = utc_now() + timedelta(seconds=BUFFER_SECONDS)
    if stream.buffer_until is None:
        await enqueue_job("product_drafts.buffer", {"source_key": stream.source_key},
                          available_at=deadline)
        await model.mark_source_processing(stream.source_key, True)
    stream.buffer_until = deadline
    await active_session().flush()


async def queue_control(source_key: str, command: Literal["start", "end"],
                        occurred_at: datetime) -> BatchControl:
    async with transaction():
        stream = await model.stream_for(source_key)
        active_session().add(model.BufferedEventTable(
            source_key=source_key, kind=command, occurred_at=occurred_at))
        await _schedule(stream)
        return BatchControl(result="queued_start" if command == "start" else "queued_end")


async def queue_message(form: IncomingMessage) -> IngestResult:
    async with transaction():
        stream = await model.stream_for(form.source_key)
        if not await _remember(form):
            return IngestResult(duplicate=True)
        stream.next_sequence += 1
        message = model.MessageTable(source_key=form.source_key, external_id=form.external_id,
            kind=form.kind, text=form.text, sender_id=form.sender_id, sender_name=form.sender_name,
            occurred_at=form.occurred_at, sequence=stream.next_sequence)
        active_session().add(message)
        await active_session().flush()
        if form.kind == "image":
            active_session().add(model.PhotoTable(message_id=message.id, status="pending",
                                                  sort_order=stream.next_sequence))
        active_session().add(model.BufferedEventTable(source_key=form.source_key, kind="message",
            occurred_at=form.occurred_at, message_id=message.id))
        await _schedule(stream)
        return IngestResult(message_id=str(message.id), unassigned=True)


async def finish_collection(source_key: str, occurred_at: datetime) -> BatchState:
    async with transaction():
        stream = await model.stream_for(source_key)
        if stream.buffer_until is not None:
            events = await model.pending_events(source_key)
            latest = max((event.occurred_at for event in events), default=occurred_at)
            await queue_control(source_key, "end",
                                max(occurred_at, latest + timedelta(microseconds=1)))
            return await batches.get_collection_state(source_key)
        return await batches.finish_collection(source_key, occurred_at)


async def _attach(event: model.BufferedEventTable) -> bool:
    message = await model.get_message_row(str(event.message_id))
    if message is None:
        return True
    form = IncomingMessage.model_validate(message.to_dict())
    result = await batches.attach_buffered_message(form, message)
    return result.message_id is not None


async def _discard(event: model.BufferedEventTable) -> None:
    if event.message_id:
        message = await model.get_message_row(str(event.message_id))
        if message and message.draft_id is None:
            photo = await model.photo_for_message(str(message.id))
            if photo:
                await storage.schedule_cleanup([photo])
            await active_session().delete(message)
            return
    await active_session().delete(event)


async def _apply(event: model.BufferedEventTable, *, ambiguous: bool) -> None:
    if ambiguous:
        await batches.record_issue(event.source_key, event.occurred_at, "ambiguous")
        event.status = "issue"
        return
    if event.kind == "message":
        applied = await _attach(event)
    else:
        result = await batches.control_collection(event.source_key,
            "start" if event.kind == "start" else "end", event.occurred_at)
        applied = result.result != "unsafe"
    if not applied and await model.issue_at(event.source_key, event.occurred_at):
        event.status = "issue"
    else:
        await _discard(event)


async def _ambiguous_times(events: list[model.BufferedEventTable]) -> set[datetime]:
    kinds: dict[datetime, set[str]] = {}
    for event in events:
        message = (await model.get_message_row(str(event.message_id))
                   if event.message_id else None)
        kind = message.kind if message else event.kind
        kinds.setdefault(event.occurred_at, set()).add(kind)
    return {time for time, values in kinds.items() if len(values) > 1}


async def process_buffer(job: Job) -> None:
    source_key = str(job.payload["source_key"])
    async with transaction():
        stream = await model.stream_for(source_key)
        if stream.buffer_until is None:
            return
        if stream.buffer_until > utc_now():
            await enqueue_job("product_drafts.buffer", {"source_key": source_key},
                              available_at=stream.buffer_until)
            return
        events = await model.pending_events(source_key)
        ambiguous = await _ambiguous_times(events)
        for event in events:
            await _apply(event, ambiguous=event.occurred_at in ambiguous)
        stream.buffer_until = None
        await active_session().flush()
        await model.mark_source_processing(source_key, False)
        await model.refresh_source_confirmation(source_key)
