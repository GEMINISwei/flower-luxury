from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from shared.http.schema import (
    NonEmptyText,
    PaginatedResponse,
    SimpleListResponse,
    UtcDateTime,
    UuidText,
)

type ProductStatus = Literal["not_acquired", "sold"]
type ProductCategory = Literal["鞋子", "配飾", "皮件", "包包", "帽子", "衣服", "其他"]


class ProductCreate(BaseModel):
    name: NonEmptyText
    brand_id: UuidText
    category: ProductCategory
    model_name: str | None = None
    serial_number: str | None = None
    color: str | None = None
    year: Annotated[int, Field(ge=1, le=9999)] | None = None
    cost_price: Annotated[int, Field(ge=0, le=2147483647)]
    internal_note: str | None = None


class ProductInfo(ProductCreate):
    id: str
    sku: str
    brand: str
    status: ProductStatus
    main_photo_id: str | None = None
    created_by: str
    updated_by: str | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime | None = None


class ProductList(PaginatedResponse[ProductInfo]):
    pass


class StatusChange(BaseModel):
    to_status: ProductStatus
    reason: str | None = None


class StatusReturn(BaseModel):
    to_status: ProductStatus
    reason: NonEmptyText


class StatusHistoryInfo(BaseModel):
    id: str
    from_status: ProductStatus | None
    to_status: ProductStatus
    action: str
    reason: str | None
    changed_by: str
    operator_name: str
    changed_at: UtcDateTime


class StatusHistoryList(SimpleListResponse[StatusHistoryInfo]):
    pass


class PhotoInfo(BaseModel):
    id: str
    url: str
    is_main: bool
    sort_order: int
    download_url: str | None = None


class OriginalPhotoFile(BaseModel):
    path: Path
    filename: str
    media_type: str


class PhotoList(SimpleListResponse[PhotoInfo]):
    pass


class MainPhotoUpdate(BaseModel):
    photo_id: UuidText
