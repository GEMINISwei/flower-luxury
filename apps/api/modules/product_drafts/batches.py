from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import func, select

from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangText, resolve_text

from . import model
from .collection import _remember, _store_message
from .prefill import schedule_prefill
from .schema import BatchControl, BatchIssueInfo, BatchState, IncomingMessage, IngestResult
from .service import _bump

ISSUE_TEXTS = {
    "ambiguous": LangText(zh="無法確認訊息歸屬，請核對 LINE 原始內容。",
                          en="Message assignment is ambiguous; check the original LINE messages."),
    "boundary": LangText(zh="延遲訊息會改變商品分界，請核對 LINE 原始內容。",
                         en="A delayed message would change product boundaries; check LINE."),
    "removed": LangText(zh="延遲訊息的商品已審核或放棄，請人工確認。",
                        en="The target draft was reviewed or discarded; check manually."),
    "command": LangText(zh="收集指令延遲或順序不明，請確認目前收集狀態。",
                        en="A collection command arrived out of order; check the current state."),
}


async def record_issue(source_key: str, occurred_at: datetime, reason: str) -> None:
    active_session().add(model.BatchIssueTable(
        source_key=source_key, occurred_at=occurred_at, reason=reason))
    await active_session().flush()


async def get_collection_state(source_key: str) -> BatchState:
    batch = await model.latest_batch(source_key)
    stream = await active_session().scalar(select(model.StreamTable).where(
        model.StreamTable.source_key == source_key))
    issues = list(await active_session().scalars(select(model.BatchIssueTable).where(
        model.BatchIssueTable.source_key == source_key,
    ).order_by(model.BatchIssueTable.created_at.desc(), model.BatchIssueTable.id.desc()).limit(5)))
    count = await active_session().scalar(select(func.count()).select_from(
        model.BatchIssueTable).where(model.BatchIssueTable.source_key == source_key))
    return BatchState(
        collecting=bool(batch and batch.ended_at is None),
        processing=bool(getattr(stream, "buffer_until", None)),
        batch_started_at=batch.started_at if batch else None,
        batch_ended_at=batch.ended_at if batch else None, issue_count=count or 0,
        issues=[BatchIssueInfo(occurred_at=row.occurred_at,
                              reason=resolve_text(ISSUE_TEXTS[row.reason])) for row in issues])


async def attach_buffered_message(form: IncomingMessage,
                                  message: model.MessageTable) -> IngestResult:
    stream = await model.stream_for(form.source_key)
    batch = await model.batch_at(form.source_key, form.occurred_at)
    if batch is None:
        return IngestResult()
    if form.occurred_at in {batch.started_at, batch.ended_at}:
        await record_issue(form.source_key, form.occurred_at, "ambiguous")
        return IngestResult()
    window = await _resolve_window(batch, form)
    batch.latest_at = max(batch.latest_at, form.occurred_at)
    stream.last_occurred_at = max(stream.last_occurred_at or form.occurred_at, form.occurred_at)
    if window is None:
        return IngestResult()
    draft = await model.get_draft_row(window.draft_key)
    if draft is None:
        await record_issue(form.source_key, form.occurred_at, "removed")
        return IngestResult()
    message.draft_id = draft.id
    if form.kind == "text":
        window.first_text_at = min(window.first_text_at or form.occurred_at, form.occurred_at)
    else:
        window.last_image_at = max(window.last_image_at, form.occurred_at)
        photo = await model.photo_for_message(str(message.id))
        if photo:
            photo.draft_id = draft.id
            photo.sort_order = max((row.sort_order for row in
                                   await model.photos_for(str(draft.id))), default=0) + 1
            if draft.main_photo_id is None:
                draft.main_photo_id = photo.id
    draft.has_text = draft.has_text or form.kind == "text"
    _bump(draft)
    await active_session().flush()
    return IngestResult(message_id=str(message.id), draft_id=str(draft.id))


async def _close_draft(draft_key: str) -> None:
    draft = await model.get_draft_row(draft_key)
    if draft and draft.collecting:
        draft.collecting = False
        await schedule_prefill(draft)
        _bump(draft)
        await active_session().flush()


async def _close_batch(batch: model.BatchTable, occurred_at: datetime) -> None:
    windows = await model.batch_windows(batch.id)
    if windows:
        windows[-1].ended_at = occurred_at
        await _close_draft(windows[-1].draft_key)
    batch.ended_at = occurred_at
    await active_session().flush()


async def control_collection(
    source_key: str, command: Literal["start", "end"], occurred_at: datetime,
) -> BatchControl:
    async with transaction():
        stream = await model.stream_for(source_key)
        batch = await model.latest_batch(source_key)
        latest = max(filter(None, [stream.last_control_at, stream.last_occurred_at,
                                    batch.latest_at if batch else None]),
                     default=None)
        if latest and occurred_at < latest:
            await record_issue(source_key, occurred_at, "command")
            return BatchControl(result="unsafe")
        stream.last_control_at = occurred_at
        collecting = bool(batch and batch.ended_at is None)
        if command == "start":
            if collecting:
                return BatchControl(result="already_collecting")
            if batch and occurred_at <= (batch.ended_at or batch.started_at):
                await record_issue(source_key, occurred_at, "command")
                return BatchControl(result="unsafe")
            current = await model.current_draft(source_key)
            if current:
                await _close_draft(str(current.id))
            active_session().add(model.BatchTable(source_key=source_key,
                started_at=occurred_at, latest_at=occurred_at))
            await active_session().flush()
            return BatchControl(result="started")
        if not collecting or batch is None:
            return BatchControl(result="already_stopped")
        if occurred_at == batch.latest_at:
            await record_issue(source_key, occurred_at, "command")
            return BatchControl(result="unsafe")
        await _close_batch(batch, occurred_at)
        return BatchControl(result="stopped")


async def finish_collection(source_key: str, occurred_at: datetime) -> BatchState:
    async with transaction():
        stream = await model.stream_for(source_key)
        batch = await model.latest_batch(source_key)
        if batch and batch.ended_at is None:
            # 後台操作使用伺服器時間, 仍須涵蓋已提交的來源事件.
            boundary = max(occurred_at, batch.latest_at + timedelta(microseconds=1))
            stream.last_control_at = boundary
            await _close_batch(batch, boundary)
        return await get_collection_state(source_key)


def _unsafe_reason(form: IncomingMessage, window: model.WindowTable) -> str | None:
    time = form.occurred_at
    if (time == window.started_at and form.kind == "text") or time == window.ended_at:
        return "ambiguous"
    if form.kind == "image" and window.first_text_at and time >= window.first_text_at:
        return "boundary"
    if form.kind == "text" and time <= window.last_image_at:
        return "boundary"
    return None


async def _new_window(
    batch: model.BatchTable, form: IncomingMessage, previous: model.WindowTable | None,
) -> model.WindowTable:
    if previous:
        previous.ended_at = form.occurred_at
        await _close_draft(previous.draft_key)
    draft = model.DraftTable(source_key=form.source_key, received_at=form.occurred_at)
    active_session().add(draft)
    await active_session().flush()
    window = model.WindowTable(batch_id=batch.id, draft_key=str(draft.id),
                              started_at=form.occurred_at, last_image_at=form.occurred_at)
    active_session().add(window)
    await active_session().flush()
    return window


async def _resolve_window(
    batch: model.BatchTable, form: IncomingMessage,
) -> model.WindowTable | None:
    windows = await model.batch_windows(batch.id)
    time = form.occurred_at
    if not windows:
        if form.kind == "text":
            return None
        if time <= batch.latest_at:
            await record_issue(form.source_key, time, "ambiguous")
            return None
        return await _new_window(batch, form, None)
    if time < windows[0].started_at:
        if form.kind == "image":
            await record_issue(form.source_key, time, "ambiguous")
        return None
    if batch.ended_at is None and time > batch.latest_at:
        current = windows[-1]
        if form.kind == "image" and current.first_text_at:
            return await _new_window(batch, form, current)
        return current
    window = next((row for row in reversed(windows) if row.started_at <= time), None)
    if window:
        reason = _unsafe_reason(form, window)
        if reason:
            await record_issue(form.source_key, time, reason)
            return None
    return window


async def ingest_batch_message(form: IncomingMessage) -> IngestResult:
    async with transaction():
        stream = await model.stream_for(form.source_key)
        if not await _remember(form):
            return IngestResult(duplicate=True)
        stream.last_occurred_at = max(stream.last_occurred_at or form.occurred_at, form.occurred_at)
        batch = await model.batch_at(form.source_key, form.occurred_at)
        if batch is None:
            return IngestResult()
        if form.occurred_at in {batch.started_at, batch.ended_at}:
            await record_issue(form.source_key, form.occurred_at, "ambiguous")
            return IngestResult()
        window = await _resolve_window(batch, form)
        batch.latest_at = max(batch.latest_at, form.occurred_at)
        if window is None:
            return IngestResult()
        draft = await model.get_draft_row(window.draft_key)
        if draft is None:
            await record_issue(form.source_key, form.occurred_at, "removed")
            return IngestResult()
        if form.kind == "text":
            window.first_text_at = min(window.first_text_at or form.occurred_at, form.occurred_at)
        else:
            window.last_image_at = max(window.last_image_at, form.occurred_at)
        return await _store_message(form, stream, draft)
