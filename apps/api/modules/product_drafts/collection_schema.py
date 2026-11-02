from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CollectionInfo(BaseModel):
    id: str | None = None
    source_key: str
    status: Literal["collecting", "confirmation", "finalized"] = "collecting"
    message_count: int = 0
    draft_ids: list[str] = Field(default_factory=list)


class SnapshotMessage(BaseModel):
    id: str
    kind: str
    text: str | None
    occurred_at: datetime
    sequence: int


class SnapshotPhoto(BaseModel):
    id: str
    original_key: str


class FinalizedSnapshot(BaseModel):
    messages: list[SnapshotMessage]
    photos: list[SnapshotPhoto]
