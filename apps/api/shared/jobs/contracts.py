import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_name: str
    payload: dict[str, JsonValue]
    attempts: int
    lease_token: UUID | None = None
    worker_id: UUID | None = None
    queue: str = "general"
    max_attempts: int = 3


class PermanentJobError(Exception):
    pass


@dataclass(frozen=True)
class TaskSpec:
    name: str
    handler: Callable[[Job], Awaitable[None]]
    max_attempts: int = 3
    timeout_seconds: float = 60
    queue: str = "general"
    interval_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.name or self.max_attempts < 1:
            raise ValueError("task name and positive max_attempts are required")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("task timeout must be finite and positive")
        if not self.queue or len(self.queue) > 50:
            raise ValueError("task queue is required and limited to 50 characters")
        if self.interval_seconds is not None and (
            not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0
        ):
            raise ValueError("schedule interval must be finite and positive")
