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


@dataclass(frozen=True)
class TaskSpec:
    name: str
    handler: Callable[[Job], Awaitable[None]]
    max_attempts: int = 3
    timeout_seconds: float = 60

    def __post_init__(self) -> None:
        if not self.name or self.max_attempts < 1:
            raise ValueError("task name and positive max_attempts are required")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("task timeout must be finite and positive")
