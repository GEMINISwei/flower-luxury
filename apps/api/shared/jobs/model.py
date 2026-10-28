import uuid
from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.table import BaseTable
from shared.time import utc_now


class JobTable(BaseTable):
    __tablename__ = "background_jobs"
    __table_args__: tuple = (
        CheckConstraint("status IN ('pending', 'running', 'failed')", name="valid_status"),
        CheckConstraint("attempts >= 0", name="nonnegative_attempts"),
        CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND locked_until IS NOT NULL) "
            "OR (status <> 'running' AND lease_token IS NULL AND locked_until IS NULL)",
            name="valid_lease",
        ),
        Index("ix_background_jobs_ready", "status", "available_at", "id"),
        Index("ix_background_jobs_expired", "status", "locked_until"),
    )

    task_name: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utc_now)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
