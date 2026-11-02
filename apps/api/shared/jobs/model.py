import uuid
from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.table import BaseTable
from shared.time import utc_now


class JobTable(BaseTable):
    __tablename__ = "background_jobs"
    __table_args__: tuple = (
        CheckConstraint("status IN ('pending', 'running', 'succeeded', 'dead')",
                        name="valid_status"),
        CheckConstraint("attempts >= 0", name="nonnegative_attempts"),
        CheckConstraint("max_attempts >= 1", name="positive_max_attempts"),
        CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND worker_id IS NOT NULL) "
            "OR (status <> 'running' AND lease_token IS NULL AND worker_id IS NULL)",
            name="valid_owner",
        ),
        Index("ix_background_jobs_ready", "status", "available_at", "id"),
        Index("ix_background_jobs_worker", "worker_id", "status"),
        UniqueConstraint("task_name", "idempotency_key"),
    )

    task_name: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    queue: Mapped[str] = mapped_column(String(50), default="general")
    idempotency_key: Mapped[str | None] = mapped_column(String(250))
    worker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_error: Mapped[str | None] = mapped_column(String(50))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utc_now)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class WorkerTable(BaseTable):
    __tablename__ = "background_workers"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'dead')", name="valid_status"),
        Index("ix_background_workers_heartbeat", "status", "heartbeat_at"),
    )

    status: Mapped[str] = mapped_column(String(16), default="active")
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utc_now)
