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
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable, Condition, PagedResult, parse_uuid
from shared.time import utc_now


class StreamTable(BaseTable):
    __tablename__ = "product_draft_streams"
    source_key: Mapped[str] = mapped_column(String(200), unique=True)
    last_occurred_at: Mapped[datetime | None]
    next_sequence: Mapped[int] = mapped_column(default=0)


class DraftTable(BaseTable):
    __tablename__ = "product_drafts"
    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    version: Mapped[int] = mapped_column(default=1)
    fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    collecting: Mapped[bool] = mapped_column(default=True)
    has_text: Mapped[bool] = mapped_column(default=False)
    main_photo_id: Mapped[uuid.UUID | None]
    updated_by: Mapped[str | None]
    __table_args__ = (
        CheckConstraint("version >= 1", name="positive_version"),
        Index("uq_product_drafts_collecting_source", "source_key", unique=True,
              postgresql_where=text("collecting IS TRUE")),
        Index("ix_product_drafts_created_at_id", "created_at", "id"),
    )


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
    return await active_session().scalar(statement.execution_options(populate_existing=True))


async def get_draft_row(id: str | None, *, lock: bool = False) -> DraftTable | None:
    return await _row(DraftTable, id, lock)


async def get_message_row(id: str | None, *, lock: bool = False) -> MessageTable | None:
    return await _row(MessageTable, id, lock)


async def get_photo_row(id: str) -> PhotoTable | None:
    return await active_session().scalar(select(PhotoTable).where(
        PhotoTable.id == parse_uuid(id),
    ).execution_options(populate_existing=True))


async def photo_for_message(id: str | None) -> PhotoTable | None:
    return await active_session().scalar(
        select(PhotoTable).where(PhotoTable.message_id == parse_uuid(id or "")),
    )


async def photos_for(id: str) -> list[PhotoTable]:
    return list(await active_session().scalars(select(PhotoTable).where(
        PhotoTable.draft_id == parse_uuid(id or ""),
    ).order_by(PhotoTable.sort_order, PhotoTable.id)))


async def messages_for(id: str) -> list[MessageTable]:
    return list(await active_session().scalars(select(MessageTable).where(
        MessageTable.draft_id == parse_uuid(id or ""),
    ).order_by(MessageTable.sequence, MessageTable.id)))


async def receipt_for(fingerprint: str) -> ReceiptTable | None:
    return await active_session().scalar(
        select(ReceiptTable).where(ReceiptTable.fingerprint == fingerprint),
    )


async def approval_for(id: str | None) -> ApprovalTable | None:
    return await active_session().get(ApprovalTable, parse_uuid(id or ""))


async def draft_page(limit: int, cursor: str | None, direction: Literal["next", "prev"],
                     source_key: str | None) -> PagedResult:
    where = [DraftTable.source_key == source_key] if source_key else []
    return await DraftTable.get_page(limit=limit, cursor=cursor, direction=direction, where=where)


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
