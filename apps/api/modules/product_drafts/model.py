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
    and_,
    delete,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable, Condition, PagedResult, PagePosition, parse_uuid
from shared.jobs.model import JobTable
from shared.time import utc_now


class StreamTable(BaseTable):
    __tablename__ = "product_draft_streams"
    source_key: Mapped[str] = mapped_column(String(200), unique=True)
    last_occurred_at: Mapped[datetime | None]
    next_sequence: Mapped[int] = mapped_column(default=0)


class DraftTable(BaseTable):
    __tablename__ = "product_drafts"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    # 舊版人工定稿的快照仍供 AI 讀取, 自動分組的暫存使用已加入的訊息.
    finalized_at: Mapped[datetime | None]
    finalized_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(default=1)
    received_at: Mapped[datetime] = mapped_column(default=utc_now)
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    manual_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    quotes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    selected_quote_id: Mapped[str | None] = mapped_column(String(200))
    prefill_revision: Mapped[int] = mapped_column(default=0)
    prefill_attempts: Mapped[int] = mapped_column(default=0)
    prefill_status: Mapped[str] = mapped_column(String(16), default="idle")
    collecting: Mapped[bool] = mapped_column(default=True)
    has_text: Mapped[bool] = mapped_column(default=False)
    main_photo_id: Mapped[uuid.UUID | None]
    updated_by: Mapped[str | None]
    __table_args__ = (
        CheckConstraint("version >= 1", name="positive_version"),
        CheckConstraint("prefill_revision >= 0", name="prefill_positive_revision"),
        CheckConstraint("prefill_attempts BETWEEN 0 AND 3", name="prefill_attempt_limit"),
        CheckConstraint("prefill_status IN "
                        "('idle', 'disabled', 'queued', 'ready', 'failed', 'unknown')",
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


async def get_prefill_job(row: DraftTable) -> JobTable | None:
    return await active_session().scalar(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill",
        or_(JobTable.idempotency_key == f"prefill:{row.id}:{row.prefill_revision}", and_(
            JobTable.payload["draft_id"].astext == str(row.id),
            JobTable.payload["revision"].astext == str(row.prefill_revision),
        )),
    ).order_by(JobTable.created_at.desc(), JobTable.id.desc()).limit(1))


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
    # 收集結束後才送達的訊息, 由人員決定加入或忽略之前不算商品內容.
    pending: Mapped[bool] = mapped_column(default=False)
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
    status: Mapped[Literal["pending", "stored", "ready", "failed"]] = mapped_column(
        String(8), default="pending",
    )
    sort_order: Mapped[int]
    original_key: Mapped[str | None]
    display_key: Mapped[str | None]
    filename: Mapped[str | None]
    extension: Mapped[str | None]
    media_type: Mapped[str | None]
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'stored', 'ready', 'failed')", name="valid_status"),
        CheckConstraint("status <> 'stored' OR original_key IS NOT NULL", name="stored_original"),
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


async def messages_for(id: str, *, pending: bool = False) -> list[MessageTable]:
    return list(await active_session().scalars(select(MessageTable).where(
        MessageTable.draft_id == parse_uuid(id or ""), MessageTable.pending.is_(pending),
    ).order_by(MessageTable.occurred_at, MessageTable.sequence, MessageTable.id)))


async def pending_counts(ids: list[str]) -> dict[str, int]:
    rows = await active_session().execute(select(MessageTable.draft_id, func.count()).where(
        MessageTable.draft_id.in_([parse_uuid(id) for id in ids]),
        MessageTable.pending.is_(True)).group_by(MessageTable.draft_id))
    return {str(draft_id): count for draft_id, count in rows.all()}


async def missing_originals(ids: list[str]) -> set[str]:
    rows = await active_session().scalars(select(PhotoTable.draft_id).where(
        PhotoTable.draft_id.in_([parse_uuid(id) for id in ids]),
        PhotoTable.status.not_in(["stored", "ready"])).distinct())
    return {str(id) for id in rows}


async def message_draft_id(id: str | None) -> str | None:
    row = await get_message_row(id)
    return str(row.draft_id) if row and row.draft_id else None


async def receipt_for(fingerprint: str) -> ReceiptTable | None:
    return await active_session().scalar(
        select(ReceiptTable).where(ReceiptTable.fingerprint == fingerprint),
    )


async def approval_for(id: str | None) -> ApprovalTable | None:
    return await active_session().get(ApprovalTable, parse_uuid(id or ""))


def _draft_filter(source_key: str | None) -> list[Condition]:
    return [DraftTable.source_key == source_key] if source_key else []


async def draft_page(limit: int, cursor: str | None, direction: Literal["next", "prev"],
                     source_key: str | None) -> PagedResult:
    return await DraftTable.get_page(limit=limit, cursor=cursor, direction=direction,
                                     sort_field="received_at", where=_draft_filter(source_key))


async def draft_position(row: DraftTable, limit: int, source_key: str | None) -> PagePosition:
    return await DraftTable.page_position(row, limit=limit, sort_field="received_at",
                                          where=_draft_filter(source_key))


async def next_review_row(source_key: str | None) -> DraftTable | None:
    unready = select(PhotoTable.id).where(PhotoTable.draft_id == DraftTable.id,
                                          PhotoTable.status.not_in(["stored", "ready"]))
    photographed = select(PhotoTable.id).where(PhotoTable.draft_id == DraftTable.id)
    late = select(MessageTable.id).where(MessageTable.draft_id == DraftTable.id,
                                         MessageTable.pending.is_(True))
    statement = select(DraftTable).where(DraftTable.collecting.is_(False),
        photographed.exists(), ~unready.exists(), ~late.exists())
    if source_key:
        statement = statement.where(DraftTable.source_key == source_key)
    return await active_session().scalar(statement.order_by(
        DraftTable.received_at, DraftTable.id).limit(1))


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
        MessageTable.source_key == source_key, MessageTable.external_id == external_id))


def message_fingerprint(source_key: str, external_id: str) -> str:
    return hashlib.sha256(json.dumps([source_key, external_id]).encode()).hexdigest()


async def remember_approved_messages(draft_id: str, product_id: str) -> None:
    rows = await messages_for(draft_id)
    for row in [*rows, *await messages_for(draft_id, pending=True)]:
        receipt = await receipt_for(message_fingerprint(row.source_key, row.external_id))
        if receipt:
            receipt.approved_product_id = product_id


class IntervalTable(BaseTable):
    __tablename__ = "product_draft_intervals"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    # 不設外鍵: 商品建檔或放棄後仍要認得這段時間, 遲到訊息才會略過而不是另開商品.
    draft_key: Mapped[str] = mapped_column(String(200), unique=True)
    started_at: Mapped[datetime]
    first_text_at: Mapped[datetime | None]
    ended_at: Mapped[datetime | None]
    __table_args__ = (Index("ix_product_draft_intervals_source_start", "source_key", "started_at"),)


async def interval_at(source_key: str, occurred_at: datetime) -> IntervalTable | None:
    return await active_session().scalar(select(IntervalTable).where(
        IntervalTable.source_key == source_key, IntervalTable.started_at <= occurred_at,
        (IntervalTable.ended_at.is_(None) | (IntervalTable.ended_at > occurred_at)),
    ).order_by(IntervalTable.started_at.desc()).limit(1)
        .execution_options(populate_existing=True))


async def interval_for(draft_key: str) -> IntervalTable | None:
    return await active_session().scalar(select(IntervalTable).where(
        IntervalTable.draft_key == draft_key).execution_options(populate_existing=True))


async def interval_following(source_key: str, occurred_at: datetime) -> IntervalTable | None:
    return await active_session().scalar(select(IntervalTable).where(
        IntervalTable.source_key == source_key, IntervalTable.started_at > occurred_at,
    ).order_by(IntervalTable.started_at).limit(1).execution_options(populate_existing=True))


async def interval_after(source_key: str, occurred_at: datetime) -> bool:
    return await active_session().scalar(select(IntervalTable.id).where(
        IntervalTable.source_key == source_key, IntervalTable.started_at > occurred_at,
    ).limit(1)) is not None
