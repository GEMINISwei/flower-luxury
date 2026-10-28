from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from modules.products.public import ProductCategory
from shared.http.errors import resolve_text
from shared.http.schema import NonEmptyText, PaginatedResponse, UtcDateTime, UuidText

from .errors import DraftError


class DraftFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    brand_id: UuidText | None = None
    category: ProductCategory | None = None
    model_name: str | None = None
    serial_number: str | None = None
    color: str | None = None
    year: Annotated[int, Field(ge=1, le=9999, strict=True)] | None = None
    cost_price: Annotated[int, Field(ge=0, le=2147483647, strict=True)] | None = None
    internal_note: str | None = None


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


class DraftUpdate(VersionRequest):
    fields: DraftFields


class PhotoOrder(VersionRequest):
    photo_ids: list[UuidText] = Field(min_length=1)

    @field_validator("photo_ids")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError(resolve_text(DraftError.INVALID_PHOTOS.value))
        return value


class MainPhoto(VersionRequest):
    photo_id: UuidText


class MessageMove(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_draft_id: UuidText
    target_version: int = Field(ge=1)
    source_version: int | None = Field(default=None, ge=1)


class IncomingMessage(BaseModel):
    source_key: Annotated[NonEmptyText, Field(max_length=200)]
    external_id: Annotated[NonEmptyText, Field(max_length=200)]
    kind: Literal["text", "image"]
    text: str | None = None
    occurred_at: datetime
    sender_id: str | None = None
    sender_name: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def naive_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value

    @model_validator(mode="after")
    def matching_content(self) -> Self:
        if (self.kind == "text") != (self.text is not None):
            raise ValueError("message kind and text do not match")
        return self


class IngestResult(BaseModel):
    message_id: str | None = None
    draft_id: str | None = None
    duplicate: bool = False
    unassigned: bool = False


class MessageInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_key: str
    draft_id: str | None
    external_id: str
    kind: Literal["text", "image"]
    text: str | None
    sender_id: str | None
    sender_name: str | None
    occurred_at: UtcDateTime
    sequence: int


class MessageList(PaginatedResponse[MessageInfo]):
    pass


class DraftPhotoInfo(BaseModel):
    id: str
    message_id: str
    draft_id: str | None
    status: Literal["pending", "ready", "failed"]
    sort_order: int
    is_main: bool
    url: str | None = None
    download_url: str | None = None


class DraftSummary(BaseModel):
    id: str
    source_key: str
    version: int
    fields: DraftFields
    main_photo_id: str | None = None
    collecting: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime | None = None


class DraftInfo(DraftSummary):
    messages: list[MessageInfo]
    photos: list[DraftPhotoInfo]


class DraftList(PaginatedResponse[DraftSummary]):
    pass


class PhotoCompletion(BaseModel):
    accepted: bool
    photo: DraftPhotoInfo | None = None


class ApprovalInfo(BaseModel):
    draft_id: str
    product_id: str
    sku: str
    reviewed_by: str
    reviewer_name: str
    reviewed_at: UtcDateTime


class DiscardInfo(BaseModel):
    id: str


class StoredFile(BaseModel):
    path: Path
    media_type: str
    filename: str


class CollectionDecision(BaseModel):
    assign: bool
    start_new: bool
