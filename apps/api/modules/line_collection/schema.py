from datetime import UTC, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.http.schema import PaginatedResponse, UtcDateTime


class LineEvent(BaseModel):
    type: str
    timestamp: int = Field(ge=0, strict=True)
    webhookEventId: str = Field(min_length=1, max_length=200)  # noqa: N815
    source: dict[str, str] = Field(default_factory=dict)
    message: dict[str, object] | None = None
    unsend: dict[str, str] | None = None
    mode: str = "active"
    replyToken: str | None = Field(default=None, max_length=200, repr=False)  # noqa: N815

    @property
    def occurred_at(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000, UTC).replace(tzinfo=None)

    @model_validator(mode="after")
    def valid_message(self) -> Self:
        # 未知事件保留向前相容, 支援的事件則不能靜默漏收.
        if self.type == "message":
            if not self.message or not isinstance(self.message.get("type"), str):
                raise ValueError("message type is required")
            if not isinstance(self.message.get("id"), str) or not self.message["id"]:
                raise ValueError("message id is required")
            if self.message["type"] == "text" and not isinstance(self.message.get("text"), str):
                raise ValueError("text is required")
        if self.type == "unsend" and not (self.unsend and self.unsend.get("messageId")):
            raise ValueError("unsent message id is required")
        _ = self.occurred_at
        return self


class WebhookBody(BaseModel):
    events: list[LineEvent] = Field(max_length=1000)


class WebhookResult(BaseModel):
    accepted: int


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = Field(strict=True)


class GroupIssue(BaseModel):
    occurred_at: UtcDateTime
    reason: str


class GroupInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    group_id: str
    name: str | None
    enabled: bool
    joined: bool
    created_at: UtcDateTime
    review_product_id: str | None
    collecting: bool = False
    processing: bool = False
    batch_started_at: UtcDateTime | None = None
    batch_ended_at: UtcDateTime | None = None
    issue_count: int = 0
    issues: list[GroupIssue] = Field(default_factory=list)
    reply_failed: bool = False


class GroupList(PaginatedResponse[GroupInfo]):
    pass


class SourceInfo(BaseModel):
    source_key: str
    name: str | None


class SourceList(BaseModel):
    list_data: list[SourceInfo]


class DownloadTarget(BaseModel):
    message_id: str
    external_id: str


class Fingerprint(BaseModel):
    value: str


class DownloadedImage(BaseModel):
    content: bytes


class GroupName(BaseModel):
    name: str
