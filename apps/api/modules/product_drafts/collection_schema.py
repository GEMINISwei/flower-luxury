from datetime import datetime

from pydantic import BaseModel


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
