from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from modules.exchange_rates.public import get_settings
from modules.vendors.public import VendorError, lock_vendor
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.table import is_unique_violation, parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.time import utc_now

from .model import ProductQuoteTable, ProductSaleTable, lock_product
from .quote_rules import QuoteError, price_quote
from .quote_schema import QuoteCreate, QuoteInfo, QuoteList, QuoteUpdate
from .service import get_product


async def load_quote(product_id: str, quote_id: str) -> ProductQuoteTable:
    row = await active_session().scalar(select(ProductQuoteTable).where(
        ProductQuoteTable.id == parse_uuid(quote_id),
        ProductQuoteTable.product_id == parse_uuid(product_id),
    ).execution_options(populate_existing=True))
    return ensure_found(row, QuoteError.NOT_FOUND)


async def quote_info(row: ProductQuoteTable) -> QuoteInfo:
    vendor = ensure_found(await lock_vendor(str(row.vendor_id)), VendorError.NOT_FOUND)
    used = await active_session().scalar(select(exists().where(
        ProductSaleTable.quote_id == row.id,
    )))
    return QuoteInfo.model_validate({
        **row.to_dict(), "vendor_name": vendor.name, "has_sales": used,
    })


async def get_quotes(id: str) -> QuoteList:
    await get_product(id)
    used = exists().where(ProductSaleTable.quote_id == ProductQuoteTable.id).label("has_sales")
    statement = select(ProductQuoteTable, used).where(
        ProductQuoteTable.product_id == parse_uuid(id),
    ).options(selectinload(ProductQuoteTable.vendor_record)).order_by(
        ProductQuoteTable.created_at, ProductQuoteTable.id,
    )
    rows = (await active_session().execute(statement)).all()
    return QuoteList(list_data=[QuoteInfo.model_validate({
        **row.to_dict(), "vendor_name": row.vendor_record.name, "has_sales": has_sales,
    }) for row, has_sales in rows], count=len(rows))


async def create_quote(id: str, form_data: QuoteCreate, actor: CurrentUser) -> QuoteInfo:
    try:
        async with transaction():
            await lock_product(id)
            vendor = await lock_vendor(form_data.vendor_id)
            if not vendor.is_active:
                raise LangException(409, VendorError.INACTIVE)
            rate = (await get_settings()).rate if vendor.country == "CN" else None
            amounts = price_quote(vendor.country, form_data.original_amount, rate)
            data = await ProductQuoteTable.create(data={
                **form_data.model_dump(), **amounts.model_dump(), "product_id": id,
                "vendor_country": vendor.country, "created_by": actor["id"],
            })
            vendor.country_locked, vendor.updated_at = True, utc_now()
            await active_session().flush()
            return await quote_info(await load_quote(id, data["id"]))
    except IntegrityError as error:
        if not is_unique_violation(error):
            raise
        raise LangException(409, QuoteError.DUPLICATE) from error


async def update_quote(id: str, quote_id: str, form_data: QuoteUpdate,
                       actor: CurrentUser) -> QuoteInfo:
    async with transaction():
        await lock_product(id)
        row = await load_quote(id, quote_id)
        amounts = price_quote(row.vendor_country, form_data.original_amount, row.exchange_rate)
        row.original_amount, row.note = form_data.original_amount, form_data.note
        row.amount_twd = amounts.amount_twd
        row.revision += 1
        row.updated_by, row.updated_at = actor["id"], utc_now()
        await active_session().flush()
        return await quote_info(row)


async def refresh_quote(id: str, quote_id: str, actor: CurrentUser) -> QuoteInfo:
    async with transaction():
        await lock_product(id)
        row = await load_quote(id, quote_id)
        rate = (await get_settings()).rate if row.vendor_country == "CN" else None
        amounts = price_quote(row.vendor_country, row.original_amount, rate)
        row.exchange_rate, row.amount_twd = amounts.exchange_rate, amounts.amount_twd
        row.revision += 1
        row.updated_by, row.updated_at = actor["id"], utc_now()
        await active_session().flush()
        return await quote_info(row)


async def delete_quote(id: str, quote_id: str, _: CurrentUser) -> QuoteInfo:
    async with transaction():
        await lock_product(id)
        row = await load_quote(id, quote_id)
        result = await quote_info(row)
        if result.has_sales:
            raise LangException(409, QuoteError.REFERENCED)
        await active_session().delete(row)
        await active_session().flush()
        return result
