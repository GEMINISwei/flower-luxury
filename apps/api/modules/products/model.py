import secrets
import string
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, or_, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.base import ExecutableOption

from modules.brands.public import BrandTable
from shared.db.query import ilike_contains
from shared.db.session import active_session
from shared.db.table import BaseTable, Condition, parse_uuid
from shared.http.errors import ensure_found
from shared.time import utc_now

from .errors import ProductError
from .rules import ensure_editable
from .schema import ProductCreate


class ProductTable(BaseTable):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str]
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"))
    category: Mapped[str]
    model_name: Mapped[str | None]
    serial_number: Mapped[str | None]
    color: Mapped[str | None]
    year: Mapped[int | None]
    cost_price: Mapped[int]
    internal_note: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="not_acquired")
    main_photo_id: Mapped[str | None]
    created_by: Mapped[str]
    updated_by: Mapped[str | None]
    deleted_at: Mapped[datetime | None]
    brand_record: Mapped[BrandTable] = relationship(lazy="raise")

    __table_args__ = (
        CheckConstraint("cost_price >= 0", name="product_cost_nonnegative"),
        CheckConstraint("year IS NULL OR year BETWEEN 1 AND 9999", name="product_year_range"),
        CheckConstraint("status IN ('not_acquired', 'sold')", name="product_status"),
        Index("ix_products_created_at_id", "created_at", "id"),
        Index("ix_products_brand_id", "brand_id"), Index("ix_products_status", "status"),
    )

    @classmethod
    def detail_loaders(cls) -> tuple[ExecutableOption, ...]:
        return (selectinload(cls.brand_record),)

    def to_detail(self) -> dict[str, Any]:
        return {**self.to_dict(), "brand": self.brand_record.name}


class ProductHistoryTable(BaseTable):
    __tablename__ = "product_status_history"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    from_status: Mapped[str | None]
    to_status: Mapped[str]
    action: Mapped[str]
    reason: Mapped[str | None]
    changed_by: Mapped[str]
    operator_name: Mapped[str]
    changed_at: Mapped[datetime]

    __table_args__ = (Index("ix_product_status_history_product_id", "product_id"),)


async def lock_product(id: str, *, editable: bool = True) -> ProductTable:
    # 每一種寫入都鎖同一列, 避免售出與照片/欄位更新併發時繞過鎖定.
    row = ensure_found(await active_session().scalar(select(ProductTable).where(
        ProductTable.id == parse_uuid(id), ProductTable.deleted_at.is_(None),
    ).with_for_update().execution_options(populate_existing=True)), ProductError.NOT_FOUND)
    if editable:
        ensure_editable(row.status)
    return row


def product_fields(form: ProductCreate) -> dict[str, Any]:
    return {"name": form.name, "brand_id": parse_uuid(form.brand_id),
            "category": form.category, "model_name": form.model_name,
            "serial_number": form.serial_number, "color": form.color, "year": form.year,
            "cost_price": form.cost_price, "internal_note": form.internal_note}


def generate_sku() -> str:
    date = utc_now().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Taipei"))
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return f"LX{date:%Y%m%d}{suffix}"


def product_filters(keyword: str | None, **filters: Any) -> list[Condition]:
    where: list[Condition] = [ProductTable.deleted_at.is_(None)]
    if keyword:
        where.append(or_(ilike_contains(ProductTable.name, keyword),
                         ilike_contains(ProductTable.sku, keyword),
                         ilike_contains(ProductTable.serial_number, keyword)))
    for field, value in filters.items():
        if value is not None and value != "":
            column = getattr(ProductTable, field)
            where.append(ilike_contains(column, value) if field == "color" else column == value)
    return where


class ProductPhotoTable(BaseTable):
    __tablename__ = "product_photos"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(unique=True)
    original_storage_key: Mapped[str | None] = mapped_column(unique=True)
    original_filename: Mapped[str | None]
    original_media_type: Mapped[str | None]
    sort_order: Mapped[int]
    uploaded_by: Mapped[str]

    __table_args__ = (
        Index("ix_product_photos_product_id", "product_id"),
        CheckConstraint(
            "(original_storage_key IS NULL AND original_filename IS NULL "
            "AND original_media_type IS NULL) OR (original_storage_key IS NOT NULL "
            "AND original_filename IS NOT NULL AND original_media_type IS NOT NULL)",
            name="original_complete",
        ),
    )



async def rows_for(id: str) -> list[ProductPhotoTable]:
    return list((await active_session().scalars(select(ProductPhotoTable).where(
        ProductPhotoTable.product_id == parse_uuid(id),
    ).order_by(ProductPhotoTable.sort_order, ProductPhotoTable.id))).all())

async def owned_photo(id: str, photo_id: str) -> ProductPhotoTable:
    row = await active_session().scalar(select(ProductPhotoTable).where(
        ProductPhotoTable.id == parse_uuid(photo_id),
        ProductPhotoTable.product_id == parse_uuid(id),
    ))
    return ensure_found(row, ProductError.PHOTO_NOT_FOUND)

async def readable_photo(photo_id: str) -> ProductPhotoTable:
    return ensure_found(await active_session().scalar(select(ProductPhotoTable).join(
        ProductTable, ProductPhotoTable.product_id == ProductTable.id,
    ).where(ProductPhotoTable.id == parse_uuid(photo_id), ProductTable.deleted_at.is_(None))),
        ProductError.PHOTO_NOT_FOUND)
