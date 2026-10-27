import secrets
import string
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    exists,
    or_,
    select,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload
from sqlalchemy.sql.base import ExecutableOption

from modules.brands.public import BrandTable
from modules.vendors.public import VendorTable
from shared.db.query import ilike_contains
from shared.db.session import active_session
from shared.db.table import BaseTable, Condition, parse_uuid
from shared.http.errors import ensure_found
from shared.time import utc_now

from .errors import ProductError, QuoteError
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


async def load_quote(product_id: str, quote_id: str) -> ProductQuoteTable:
    row = await active_session().scalar(select(ProductQuoteTable).where(
        ProductQuoteTable.id == parse_uuid(quote_id),
        ProductQuoteTable.product_id == parse_uuid(product_id),
    ).execution_options(populate_existing=True))
    return ensure_found(row, QuoteError.NOT_FOUND)


async def quote_has_sales(quote_id: uuid.UUID) -> bool:
    return bool(await active_session().scalar(select(exists().where(
        ProductSaleTable.quote_id == quote_id,
    ))))


async def quote_rows(id: str) -> list[tuple[ProductQuoteTable, bool]]:
    used = exists().where(ProductSaleTable.quote_id == ProductQuoteTable.id).label("has_sales")
    statement = select(ProductQuoteTable, used).where(
        ProductQuoteTable.product_id == parse_uuid(id),
    ).options(selectinload(ProductQuoteTable.vendor_record)).order_by(
        ProductQuoteTable.created_at, ProductQuoteTable.id,
    )
    rows = (await active_session().execute(statement)).all()
    return [(row, has_sales) for row, has_sales in rows]


async def sale_rows(id: str) -> list[ProductSaleTable]:
    return list((await active_session().scalars(select(ProductSaleTable).where(
        ProductSaleTable.product_id == parse_uuid(id),
    ).order_by(ProductSaleTable.sold_at.desc(), ProductSaleTable.id.desc()))).all())


async def current_sale(id: uuid.UUID) -> ProductSaleTable | None:
    return await active_session().scalar(select(ProductSaleTable).where(
        ProductSaleTable.product_id == id, ProductSaleTable.is_current.is_(True),
    ))
