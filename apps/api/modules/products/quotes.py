from sqlalchemy.exc import IntegrityError

from modules.vendors.public import VendorError, lock_vendor
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.table import is_unique_violation
from shared.db.transaction import transaction
from shared.http.errors import LangException, ensure_found
from shared.time import utc_now

from .errors import QuoteError
from .model import ProductQuoteTable, load_quote, lock_product, quote_has_sales, quote_rows
from .quote_rules import price_quote
from .quote_schema import QuoteCreate, QuoteInfo, QuoteList, QuoteUpdate
from .service import get_product


async def quote_info(row: ProductQuoteTable) -> QuoteInfo:
    vendor = ensure_found(await lock_vendor(str(row.vendor_id)), VendorError.NOT_FOUND)
    used = await quote_has_sales(row.id)
    return QuoteInfo.model_validate({
        **row.to_dict(), "vendor_name": vendor.name, "has_sales": used,
    })


async def get_quotes(id: str) -> QuoteList:
    await get_product(id)
    rows = await quote_rows(id)
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
            amounts = price_quote(form_data.original_amount, form_data.exchange_rate)
            data = await ProductQuoteTable.create(data={
                "vendor_id": form_data.vendor_id, "original_amount": form_data.original_amount,
                "note": form_data.note,
                "exchange_rate": amounts.exchange_rate, "amount_twd": amounts.amount_twd,
                "product_id": id,
                "created_by": actor["id"],
            })
            vendor.has_quotes, vendor.updated_at = True, utc_now()
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
        amounts = price_quote(form_data.original_amount, form_data.exchange_rate)
        row.original_amount, row.note = form_data.original_amount, form_data.note
        row.amount_twd, row.exchange_rate = amounts.amount_twd, amounts.exchange_rate
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
