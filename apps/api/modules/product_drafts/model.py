import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    delete,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from shared.db.session import active_session
from shared.db.table import BaseTable, Condition, PagedResult, parse_uuid
from shared.time import utc_now

from .buffer_model import BufferedEventTable as BufferedEventTable


class StreamTable(BaseTable):
    __tablename__ = "product_draft_streams"
    source_key: Mapped[str] = mapped_column(String(200), unique=True)
    last_occurred_at: Mapped[datetime | None]
    next_sequence: Mapped[int] = mapped_column(default=0)
    last_control_at: Mapped[datetime | None]
    buffer_until: Mapped[datetime | None]


class DraftTable(BaseTable):
    __tablename__ = "product_drafts"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    version: Mapped[int] = mapped_column(default=1)
    received_at: Mapped[datetime] = mapped_column(default=utc_now)
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    manual_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    quotes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    selected_quote_id: Mapped[str | None] = mapped_column(String(200))
    prefill_revision: Mapped[int] = mapped_column(default=0)
    prefill_status: Mapped[str] = mapped_column(String(16), default="idle")
    collecting: Mapped[bool] = mapped_column(default=True)
    processing: Mapped[bool] = mapped_column(default=False)
    needs_confirmation: Mapped[bool] = mapped_column(default=False)
    has_text: Mapped[bool] = mapped_column(default=False)
    main_photo_id: Mapped[uuid.UUID | None]
    updated_by: Mapped[str | None]
    __table_args__ = (
        CheckConstraint("version >= 1", name="positive_version"),
        CheckConstraint("prefill_revision >= 0", name="prefill_positive_revision"),
        CheckConstraint("prefill_status IN ('idle', 'disabled', 'queued', 'ready', 'failed')",
                        name="prefill_valid_status"),
        Index("uq_product_drafts_collecting_source", "source_key", unique=True,
              postgresql_where=text("collecting IS TRUE")),
        Index("ix_product_drafts_created_at_id", "created_at", "id"),
        Index("ix_product_drafts_received_at_id", "received_at", "id"),
    )


class PrefillSettingsTable(BaseTable):
    __tablename__ = "draft_prefill_settings"
    key: Mapped[str] = mapped_column(String(16), unique=True)
    supplement: Mapped[str] = mapped_column(Text, default="")
    revision: Mapped[int] = mapped_column(default=1)
    updated_by: Mapped[str]
    __table_args__ = (
        CheckConstraint("key = 'global'", name="prefill_global_only"),
        CheckConstraint("revision >= 1", name="prefill_settings_positive_revision"),
    )


async def prefill_settings_row(*, lock: bool = False) -> PrefillSettingsTable | None:
    if lock:
        # 首次設定還沒有資料列, 也必須與套用 AI 結果互斥.
        await active_session().execute(select(func.pg_advisory_xact_lock(58379211)))
    statement = select(PrefillSettingsTable).where(PrefillSettingsTable.key == "global")
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return await active_session().scalar(statement)


async def write_prefill_settings(supplement: str, revision: int, actor_id: str) -> bool:
    row = await prefill_settings_row(lock=True)
    if row:
        if row.revision != revision:
            return False
        row.supplement, row.revision = supplement, revision + 1
        row.updated_by, row.updated_at = actor_id, utc_now()
        await active_session().flush()
        return True
    if revision != 0:
        return False
    result = await active_session().execute(insert(PrefillSettingsTable).values(
        key="global", supplement=supplement, revision=1, updated_by=actor_id,
    ).on_conflict_do_nothing(index_elements=[PrefillSettingsTable.key])
        .returning(PrefillSettingsTable.id))
    return result.scalar_one_or_none() is not None


class MessageTable(BaseTable):
    __tablename__ = "product_draft_messages"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_drafts.id", ondelete="CASCADE"),
    )
    external_id: Mapped[str] = mapped_column(String(200))
    kind: Mapped[Literal["text", "image"]] = mapped_column(String(8))
    text: Mapped[str | None] = mapped_column(Text)
    sender_id: Mapped[str | None]
    sender_name: Mapped[str | None]
    occurred_at: Mapped[datetime]
    sequence: Mapped[int]
    buffered_event: Mapped[BufferedEventTable | None] = relationship(
        lazy="raise", uselist=False, cascade="all, delete-orphan", single_parent=True,
        passive_deletes=True)
    __table_args__ = (
        CheckConstraint("(kind = 'text' AND text IS NOT NULL) OR (kind = 'image' AND text IS NULL)",
                        name="matching_content"),
        Index("ix_product_draft_messages_draft_order", "draft_id", "occurred_at", "sequence"),
        Index("ix_product_draft_messages_created_at_id", "created_at", "id"),
    )


class PhotoTable(BaseTable):
    __tablename__ = "product_draft_photos"
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_drafts.id", ondelete="CASCADE"),
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_draft_messages.id", ondelete="CASCADE"), unique=True,
    )
    status: Mapped[Literal["pending", "ready", "failed"]] = mapped_column(
        String(8), default="pending",
    )
    sort_order: Mapped[int]
    original_key: Mapped[str | None]
    display_key: Mapped[str | None]
    filename: Mapped[str | None]
    extension: Mapped[str | None]
    media_type: Mapped[str | None]
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'ready', 'failed')", name="valid_status"),
        CheckConstraint("status <> 'ready' OR (original_key IS NOT NULL "
                        "AND display_key IS NOT NULL "
                        "AND filename IS NOT NULL AND extension IS NOT NULL "
                        "AND media_type IS NOT NULL)",
                        name="ready_files"),
        Index("ix_product_draft_photos_draft_order", "draft_id", "sort_order"),
    )


class ReceiptTable(BaseTable):
    __tablename__ = "product_draft_receipts"
    approved_product_id: Mapped[str | None]
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(index=True)


class ApprovalTable(BaseTable):
    __tablename__ = "product_draft_approvals"
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), unique=True,
    )
    sku: Mapped[str]
    reviewed_by: Mapped[str]
    reviewer_name: Mapped[str]


async def stream_for(source_key: str) -> StreamTable:
    statement = insert(StreamTable).values(source_key=source_key).on_conflict_do_nothing(
        index_elements=[StreamTable.source_key],
    )
    await active_session().execute(statement)
    row = await active_session().scalar(select(StreamTable).where(
        StreamTable.source_key == source_key,
    ).with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise RuntimeError("draft stream could not be initialized")
    return row


async def current_draft(source_key: str) -> DraftTable | None:
    return await active_session().scalar(select(DraftTable).where(
        DraftTable.source_key == source_key, DraftTable.collecting.is_(True),
    ).execution_options(populate_existing=True))


async def _row(cls: Any, id: str | None, lock: bool) -> Any:
    if lock:
        source_key = await active_session().scalar(
            select(cls.source_key).where(cls.id == parse_uuid(id or "")),
        )
        if source_key is None:
            return None
        await stream_for(source_key)
    statement = select(cls).where(cls.id == parse_uuid(id or ""))
    if cls is MessageTable:
        statement = statement.options(selectinload(MessageTable.buffered_event))
    return await active_session().scalar(statement.execution_options(populate_existing=True))


async def get_draft_row(id: str | None, *, lock: bool = False) -> DraftTable | None:
    return await _row(DraftTable, id, lock)


async def get_message_row(id: str | None, *, lock: bool = False) -> MessageTable | None:
    return await _row(MessageTable, id, lock)


async def get_photo_row(id: str) -> PhotoTable | None:
    # 放棄暫存的 cascade delete 必須等讀取補產結束, 背景清檔才不會漏掉新檔.
    return await active_session().scalar(select(PhotoTable).where(
        PhotoTable.id == parse_uuid(id),
    ).with_for_update(read=True).execution_options(populate_existing=True))


async def photo_for_message(id: str | None) -> PhotoTable | None:
    return await active_session().scalar(
        select(PhotoTable).where(PhotoTable.message_id == parse_uuid(id or "")),
    )


async def photos_for(id: str) -> list[PhotoTable]:
    return list(await active_session().scalars(select(PhotoTable).where(
        PhotoTable.draft_id == parse_uuid(id or ""),
    ).order_by(PhotoTable.sort_order, PhotoTable.id)))


async def messages_for(id: str) -> list[MessageTable]:
    batched = await active_session().scalar(select(WindowTable.id).where(
        WindowTable.draft_key == id))
    order = ((MessageTable.occurred_at, MessageTable.sequence) if batched
             else (MessageTable.sequence,))
    return list(await active_session().scalars(select(MessageTable).where(
        MessageTable.draft_id == parse_uuid(id or ""),
    ).order_by(*order, MessageTable.id)))


async def message_draft_id(id: str) -> str | None:
    row = await get_message_row(id)
    return str(row.draft_id) if row and row.draft_id else None


async def pending_events(source_key: str) -> list[BufferedEventTable]:
    return list(await active_session().scalars(select(BufferedEventTable).where(
        BufferedEventTable.source_key == source_key, BufferedEventTable.status == "pending",
    ).order_by(BufferedEventTable.occurred_at, BufferedEventTable.id)))


async def issue_at(source_key: str, occurred_at: datetime) -> bool:
    return await active_session().scalar(select(BatchIssueTable.id).where(
        BatchIssueTable.source_key == source_key, BatchIssueTable.occurred_at == occurred_at,
    ).limit(1)) is not None


async def receipt_for(fingerprint: str) -> ReceiptTable | None:
    return await active_session().scalar(
        select(ReceiptTable).where(ReceiptTable.fingerprint == fingerprint),
    )


async def approval_for(id: str | None) -> ApprovalTable | None:
    return await active_session().get(ApprovalTable, parse_uuid(id or ""))


async def draft_page(limit: int, cursor: str | None, direction: Literal["next", "prev"],
                     source_key: str | None) -> PagedResult:
    where = [DraftTable.source_key == source_key] if source_key else []
    return await DraftTable.get_page(limit=limit, cursor=cursor, direction=direction,
                                     sort_field="received_at", where=where)


async def next_review_row(source_key: str | None) -> DraftTable | None:
    statement = select(DraftTable).where(DraftTable.collecting.is_(False),
        DraftTable.processing.is_(False), DraftTable.needs_confirmation.is_(False))
    if source_key:
        statement = statement.where(DraftTable.source_key == source_key)
    return await active_session().scalar(statement.order_by(
        DraftTable.received_at, DraftTable.id).limit(1))


async def mark_source_processing(source_key: str, processing: bool) -> None:
    await active_session().execute(update(DraftTable).where(
        DraftTable.source_key == source_key, DraftTable.processing != processing,
    ).values(processing=processing, version=DraftTable.version + 1, updated_at=utc_now()))


async def refresh_source_confirmation(source_key: str) -> None:
    pending = await active_session().scalar(select(BufferedEventTable.id).where(
        BufferedEventTable.source_key == source_key,
        BufferedEventTable.status == "issue").limit(1))
    needed = pending is not None
    await active_session().execute(update(DraftTable).where(
        DraftTable.source_key == source_key, DraftTable.needs_confirmation != needed,
    ).values(needs_confirmation=needed, version=DraftTable.version + 1, updated_at=utc_now()))


async def issue_page(limit: int, cursor: str | None, direction: Literal["next", "prev"],
                     source_key: str | None) -> PagedResult:
    where: list[Condition] = [MessageTable.draft_id.is_(None), MessageTable.id.in_(
        select(BufferedEventTable.message_id).where(BufferedEventTable.status == "issue"))]
    if source_key:
        where.append(MessageTable.source_key == source_key)
    return await MessageTable.get_page(limit=limit, cursor=cursor, direction=direction, where=where)


async def buffered_issue_page(limit: int, cursor: str | None, direction: Literal["next", "prev"],
                              source_key: str | None) -> PagedResult:
    where: list[Condition] = [BufferedEventTable.status == "issue"]
    if source_key:
        where.append(BufferedEventTable.source_key == source_key)
    return await BufferedEventTable.get_page(limit=limit, cursor=cursor, direction=direction,
                                             sort_field="occurred_at", where=where)


async def get_buffered_event(id: str, *, lock: bool = False) -> BufferedEventTable | None:
    return await _row(BufferedEventTable, id, lock)


async def unassigned_page(limit: int, cursor: str | None, direction: Literal["next", "prev"],
                          source_key: str | None) -> PagedResult:
    where: list[Condition] = [MessageTable.draft_id.is_(None)]
    if source_key:
        where.append(MessageTable.source_key == source_key)
    return await MessageTable.get_page(limit=limit, cursor=cursor, direction=direction, where=where)


async def expire_receipt_row(id: str) -> None:
    await active_session().execute(delete(ReceiptTable).where(
        ReceiptTable.id == parse_uuid(id), ReceiptTable.expires_at <= utc_now(),
    ))


async def message_by_external_id(source_key: str, external_id: str) -> MessageTable | None:
    return await active_session().scalar(select(MessageTable).where(
        MessageTable.source_key == source_key, MessageTable.external_id == external_id,
    ))


def message_fingerprint(source_key: str, external_id: str) -> str:
    return hashlib.sha256(json.dumps([source_key, external_id]).encode()).hexdigest()


async def remember_approved_messages(draft_id: str, product_id: str) -> None:
    rows = await messages_for(draft_id)
    for row in rows:
        receipt = await receipt_for(message_fingerprint(row.source_key, row.external_id))
        if receipt:
            receipt.approved_product_id = product_id


class BatchTable(BaseTable):
    __tablename__ = "product_draft_batches"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    latest_at: Mapped[datetime]
    __table_args__ = (
        Index("uq_product_draft_batches_active_source", "source_key", unique=True,
              postgresql_where=text("ended_at IS NULL")),
        Index("ix_product_draft_batches_source_start", "source_key", "started_at"),
    )


class WindowTable(BaseTable):
    __tablename__ = "product_draft_windows"
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_draft_batches.id", ondelete="CASCADE"))
    # 保留不含內容的歸屬鍵, 才能辨認已審核或放棄商品的延遲事件.
    draft_key: Mapped[str] = mapped_column(String(200), unique=True)
    started_at: Mapped[datetime]
    last_image_at: Mapped[datetime]
    first_text_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]
    __table_args__ = (Index("ix_product_draft_windows_batch_start", "batch_id", "started_at"),)


class BatchIssueTable(BaseTable):
    __tablename__ = "product_draft_batch_issues"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    occurred_at: Mapped[datetime]
    reason: Mapped[str] = mapped_column(String(30))
    __table_args__ = (Index("ix_product_draft_batch_issues_source", "source_key"),)


async def latest_batch(source_key: str) -> BatchTable | None:
    return await active_session().scalar(select(BatchTable).where(
        BatchTable.source_key == source_key,
    ).order_by(BatchTable.started_at.desc()).limit(1)
        .execution_options(populate_existing=True))


async def batch_at(source_key: str, occurred_at: datetime) -> BatchTable | None:
    return await active_session().scalar(select(BatchTable).where(
        BatchTable.source_key == source_key, BatchTable.started_at <= occurred_at,
        (BatchTable.ended_at.is_(None) | (BatchTable.ended_at >= occurred_at)),
    ).order_by(BatchTable.started_at.desc()).limit(1)
        .execution_options(populate_existing=True))


async def batch_windows(batch_id: uuid.UUID) -> list[WindowTable]:
    return list(await active_session().scalars(select(WindowTable).where(
        WindowTable.batch_id == batch_id,
    ).order_by(WindowTable.started_at).execution_options(populate_existing=True)))
