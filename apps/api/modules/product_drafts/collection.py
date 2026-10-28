import hashlib
import json
from datetime import timedelta

from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.jobs.contracts import Job
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model
from .rules import decide_collection
from .schema import IncomingMessage, IngestResult
from .service import _bump

RECEIPT_DAYS = 30


async def _remember(form: IncomingMessage) -> bool:
    digest = hashlib.sha256(json.dumps([form.source_key, form.external_id]).encode()).hexdigest()
    if await model.receipt_for(digest):
        return False
    row = model.ReceiptTable(
        fingerprint=digest, expires_at=utc_now() + timedelta(days=RECEIPT_DAYS),
    )
    active_session().add(row)
    await active_session().flush()
    await enqueue_job("product_drafts.expire_receipt", {"receipt_id": str(row.id)},
                      available_at=row.expires_at)
    return True


async def ingest_message(form: IncomingMessage) -> IngestResult:
    async with transaction():
        stream = await model.stream_for(form.source_key)
        if not await _remember(form):
            return IngestResult(duplicate=True)
        draft = await model.current_draft(form.source_key)
        decision = decide_collection(form.kind, has_current=draft is not None,
                                     has_text=bool(draft and draft.has_text),
                                     is_late=bool(stream.last_occurred_at
                                                  and form.occurred_at < stream.last_occurred_at))
        if decision.start_new:
            if draft:
                draft.collecting = False
                _bump(draft)
                await active_session().flush()
            draft = model.DraftTable(source_key=form.source_key)
            active_session().add(draft)
            await active_session().flush()
        assigned = draft if decision.assign else None
        stream.next_sequence += 1
        stream.last_occurred_at = max(stream.last_occurred_at or form.occurred_at, form.occurred_at)
        message = model.MessageTable(source_key=form.source_key, external_id=form.external_id,
                                     draft_id=assigned.id if assigned else None, kind=form.kind,
                                     text=form.text, sender_id=form.sender_id,
                                     sender_name=form.sender_name,
                                     occurred_at=form.occurred_at, sequence=stream.next_sequence)
        active_session().add(message)
        await active_session().flush()
        if form.kind == "image":
            photo = model.PhotoTable(message_id=message.id, draft_id=message.draft_id,
                                     sort_order=stream.next_sequence, status="pending")
            active_session().add(photo)
            await active_session().flush()
            if assigned and assigned.main_photo_id is None:
                assigned.main_photo_id = photo.id
        if assigned:
            assigned.has_text = assigned.has_text or form.kind == "text"
            _bump(assigned)
        return IngestResult(message_id=str(message.id),
                            draft_id=str(assigned.id) if assigned else None,
                            unassigned=assigned is None)


async def expire_receipt(job: Job) -> None:
    await model.expire_receipt_row(str(job.payload["receipt_id"]))
