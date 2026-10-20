import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String, select, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.base import ExecutableOption

from modules.brands.public import BrandTable
from modules.vendors.public import VendorTable
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


class ProductQuoteTable(BaseTable):
    __tablename__ = "product_quotes"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"))
    vendor_country: Mapped[str]
    currency: Mapped[str]
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(16, 6))
    amount_twd: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None]
    revision: Mapped[int] = mapped_column(default=1)
    created_by: Mapped[str]
    updated_by: Mapped[str | None]
    vendor_record: Mapped[VendorTable] = relationship(lazy="raise")

    __table_args__ = (
        Index("uq_product_quotes_product_vendor", "product_id", "vendor_id", unique=True),
        Index("ix_product_quotes_vendor_id", "vendor_id"),
        CheckConstraint("original_amount > 0", name="quote_amount_positive"),
        CheckConstraint("exchange_rate > 0", name="quote_rate_positive"),
        CheckConstraint("amount_twd BETWEEN 0 AND 9007199254740991", name="quote_twd_range"),
        CheckConstraint("revision > 0", name="quote_revision_positive"),
        CheckConstraint(
            "(vendor_country = 'TW' AND currency = 'TWD' AND exchange_rate = 1 "
            "AND original_amount = trunc(original_amount)) "
            "OR (vendor_country = 'CN' AND currency = 'CNY')", name="quote_country_currency",
        ),
    )


class ProductSaleTable(BaseTable):
    __tablename__ = "product_sales"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    quote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_quotes.id", ondelete="RESTRICT"),
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"))
    vendor_name: Mapped[str]
    vendor_country: Mapped[str]
    currency: Mapped[str]
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(16, 6))
    amount_twd: Mapped[int] = mapped_column(BigInteger)
    cost_price: Mapped[int]
    profit_amount: Mapped[int] = mapped_column(BigInteger)
    is_current: Mapped[bool] = mapped_column(default=True)
    changed_by: Mapped[str]
    operator_name: Mapped[str]
    sold_at: Mapped[datetime]
    returned_at: Mapped[datetime | None]
    returned_by: Mapped[str | None]
    return_reason: Mapped[str | None]

    __table_args__ = (
        Index("uq_product_sales_current", "product_id", unique=True,
              postgresql_where=text("is_current")),
        Index("ix_product_sales_quote_id", "quote_id"),
        Index("ix_product_sales_vendor_id", "vendor_id"),
        CheckConstraint("cost_price >= 0", name="sale_cost_nonnegative"),
        CheckConstraint("profit_amount = amount_twd - cost_price", name="sale_profit_matches"),
        CheckConstraint("original_amount > 0 AND exchange_rate > 0", name="sale_positive_amounts"),
        CheckConstraint("amount_twd BETWEEN 0 AND 9007199254740991", name="sale_twd_range"),
        CheckConstraint(
            "(vendor_country = 'TW' AND currency = 'TWD' AND exchange_rate = 1 "
            "AND original_amount = trunc(original_amount)) "
            "OR (vendor_country = 'CN' AND currency = 'CNY')", name="sale_country_currency",
        ),
        CheckConstraint(
            "(is_current AND returned_at IS NULL AND returned_by IS NULL "
            "AND return_reason IS NULL) OR (NOT is_current AND returned_at IS NOT NULL "
            "AND returned_by IS NOT NULL AND length(trim(return_reason)) > 0)",
            name="sale_return_fields",
        ),
    )


async def lock_product(id: str, *, editable: bool = True) -> ProductTable:
    # 每一種寫入都鎖同一列, 避免售出與照片/欄位更新併發時繞過鎖定.
    row = ensure_found(await active_session().scalar(select(ProductTable).where(
        ProductTable.id == parse_uuid(id), ProductTable.deleted_at.is_(None),
    ).with_for_update().execution_options(populate_existing=True)), ProductError.NOT_FOUND)
    if editable:
        ensure_editable(row.status)
    return row
