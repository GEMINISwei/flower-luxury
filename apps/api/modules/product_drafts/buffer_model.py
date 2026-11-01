import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.table import BaseTable


class BufferedEventTable(BaseTable):
    __tablename__ = "product_draft_buffered_events"

    source_key: Mapped[str] = mapped_column(ForeignKey("product_draft_streams.source_key"))
    kind: Mapped[str] = mapped_column(String(10))
    occurred_at: Mapped[datetime]
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_draft_messages.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    __table_args__ = (
        CheckConstraint("kind IN ('message', 'start', 'end')", name="buffer_event_kind"),
        CheckConstraint("status IN ('pending', 'issue')", name="buffer_event_status"),
        Index("ix_product_draft_buffer_source_status_time", "source_key", "status", "occurred_at"),
    )


