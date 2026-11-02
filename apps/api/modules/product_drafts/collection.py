from datetime import datetime, timedelta

from sqlalchemy import func, select

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import ensure_found
from shared.jobs.contracts import Job
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model
from .errors import DraftError
from .prefill import schedule_prefill
from .rules import check_version
from .schema import DraftInfo, IncomingMessage, IngestResult, VersionRequest
from .service import _bump, get_draft

RECEIPT_DAYS = 30
_TICK = timedelta(microseconds=1)


async def _remember(form: IncomingMessage) -> bool:
    digest = model.message_fingerprint(form.source_key, form.external_id)
    if await model.receipt_for(digest):
        return False
    row = model.ReceiptTable(
        fingerprint=digest, expires_at=utc_now() + timedelta(days=RECEIPT_DAYS),
    )
    active_session().add(row)
    await active_session().flush()
    await enqueue_job("product_drafts.expire_receipt", {"receipt_id": str(row.id)},
                      available_at=row.expires_at, queue="maintenance")
    return True


async def _close(draft: model.DraftTable, interval: model.IntervalTable,
                 ended_at: datetime) -> None:
    interval.ended_at = ended_at
    if not draft.collecting:
        return
    draft.collecting = False
    draft.finalized_at = utc_now()
    await schedule_prefill(draft)
    _bump(draft)
    await active_session().flush()


async def _open(form: IncomingMessage) -> tuple[model.DraftTable, model.IntervalTable]:
    draft = model.DraftTable(source_key=form.source_key, received_at=form.occurred_at)
    active_session().add(draft)
    await active_session().flush()
    interval = model.IntervalTable(source_key=form.source_key, draft_key=str(draft.id),
                                   started_at=form.occurred_at)
    active_session().add(interval)
    await active_session().flush()
    return draft, interval


async def _split(current: model.DraftTable, interval: model.IntervalTable,
                 form: IncomingMessage) -> model.DraftTable:
    await _close(current, interval, form.occurred_at)
    draft, opened = await _open(form)
    # 先送達但原始時間較晚的內容, 依時間屬於新商品.
    later = [item for item in await model.messages_for(str(current.id))
             if item.occurred_at > form.occurred_at]
    for item in later:
        item.draft_id = draft.id
        photo = await model.photo_for_message(str(item.id))
        if photo:
            photo.draft_id = draft.id
            if current.main_photo_id == photo.id:
                current.main_photo_id = None
            draft.main_photo_id = draft.main_photo_id or photo.id
        if item.kind == "text":
            opened.first_text_at = min(opened.first_text_at or item.occurred_at, item.occurred_at)
    draft.has_text = opened.first_text_at is not None
    if later and current.main_photo_id is None:
        remaining = await model.photos_for(str(current.id))
        current.main_photo_id = remaining[0].id if remaining else None
    return draft


async def _late_target(interval: model.IntervalTable | None) -> model.DraftTable | None:
    if interval is None:
        return None
    return await model.get_draft_row(interval.draft_key)


async def _route(form: IncomingMessage) -> tuple[model.DraftTable | None, bool]:
    """回傳 (歸屬商品, 是否待加入); 商品為 None 代表略過."""
    time = form.occurred_at
    interval = await model.interval_at(form.source_key, time)
    if interval is not None and form.kind == "text" and time == interval.started_at:
        # 與商品首圖同一毫秒的文字分不出先後, 交給前一件由人員判斷.
        previous = await model.interval_at(form.source_key, time - _TICK)
        return await _late_target(previous), True
    if interval is None:
        if form.kind == "text" or await model.interval_after(form.source_key, time):
            return None, False
        current = await model.current_draft(form.source_key)
        if current:
            opened = ensure_found(await model.interval_for(str(current.id)), DraftError.NOT_FOUND)
            await _close(current, opened, time)
        opened_draft, _ = await _open(form)
        return opened_draft, False
    draft = await model.get_draft_row(interval.draft_key)
    if interval.ended_at is not None or draft is None or not draft.collecting:
        return await _late_target(interval), True
    if form.kind == "image" and interval.first_text_at is not None:
        if time == interval.first_text_at:
            return draft, True
        if time > interval.first_text_at:
            return await _split(draft, interval, form), False
    if form.kind == "text":
        interval.first_text_at = min(interval.first_text_at or time, time)
    return draft, False


async def ingest_message(form: IncomingMessage) -> IngestResult:
    async with transaction():
        stream = await model.stream_for(form.source_key)
        if not await _remember(form):
            return IngestResult(duplicate=True)
        draft, pending = await _route(form)
        if draft is None:
            return IngestResult()
        return await _store_message(form, stream, draft, pending=pending)


async def _store_message(
    form: IncomingMessage, stream: model.StreamTable, draft: model.DraftTable, *, pending: bool,
) -> IngestResult:
    stream.next_sequence += 1
    stream.last_occurred_at = max(stream.last_occurred_at or form.occurred_at, form.occurred_at)
    message = model.MessageTable(source_key=form.source_key, external_id=form.external_id,
                                 draft_id=draft.id, kind=form.kind, pending=pending,
                                 text=form.text, sender_id=form.sender_id,
                                 sender_name=form.sender_name,
                                 occurred_at=form.occurred_at, sequence=stream.next_sequence)
    active_session().add(message)
    await active_session().flush()
    if form.kind == "image":
        photo = model.PhotoTable(message_id=message.id, draft_id=None if pending else draft.id,
                                 sort_order=stream.next_sequence, status="pending")
        active_session().add(photo)
        await active_session().flush()
        if not pending and draft.main_photo_id is None:
            draft.main_photo_id = photo.id
    if not pending:
        draft.has_text = draft.has_text or form.kind == "text"
    _bump(draft)
    return IngestResult(message_id=str(message.id), draft_id=str(draft.id), pending=pending)


async def complete_draft(id: str, form: VersionRequest, actor: CurrentUser) -> DraftInfo:
    async with transaction():
        draft = ensure_found(await model.get_draft_row(id, lock=True), DraftError.NOT_FOUND)
        if not draft.collecting:
            return await get_draft(id)
        check_version(draft.version, form.version)
        await _complete(draft)
        _bump(draft, actor)
        await active_session().flush()
        return await get_draft(id)


async def _complete(draft: model.DraftTable) -> None:
    interval = ensure_found(await model.interval_for(str(draft.id)), DraftError.NOT_FOUND)
    latest = await active_session().scalar(select(func.max(model.MessageTable.occurred_at))
                                           .where(model.MessageTable.draft_id == draft.id))
    # 後台操作使用伺服器時間, 仍須涵蓋已收到的來源訊息.
    await _close(draft, interval, max(utc_now(), (latest or interval.started_at) + _TICK))


async def complete_source(source_key: str) -> None:
    async with transaction():
        await model.stream_for(source_key)
        current = await model.current_draft(source_key)
        if current:
            await _complete(current)


async def expire_receipt(job: Job) -> None:
    await model.expire_receipt_row(str(job.payload["receipt_id"]))
