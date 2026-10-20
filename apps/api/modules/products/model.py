import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.base import ExecutableOption

from modules.brands.public import BrandTable
from shared.db.session import active_session
from shared.db.table import BaseTable, parse_uuid
from shared.http.errors import ensure_found

from .rules import ProductError, ensure_editable


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
        CheckConstraint("status IN ('not_acquired', 'in_stock', 'sold')", name="product_status"),
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


class ProductPhotoTable(BaseTable):
    __tablename__ = "product_photos"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(unique=True)
    sort_order: Mapped[int]
    uploaded_by: Mapped[str]

    __table_args__ = (Index("ix_product_photos_product_id", "product_id"),)


async def lock_product(id: str, *, editable: bool = True) -> ProductTable:
    # 每一種寫入都鎖同一列, 避免售出與照片/欄位更新併發時繞過鎖定.
    row = ensure_found(await active_session().scalar(select(ProductTable).where(
        ProductTable.id == parse_uuid(id), ProductTable.deleted_at.is_(None),
    ).with_for_update().execution_options(populate_existing=True)), ProductError.NOT_FOUND)
    if editable:
        ensure_editable(row.status)
    return row
