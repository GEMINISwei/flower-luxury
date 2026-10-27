from modules.vendors.public import lock_vendor
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException
from shared.time import utc_now

from .errors import QuoteError
from .model import ProductSaleTable, load_quote, lock_product, sale_rows
from .quote_schema import SaleCreate, SaleInfo, SaleList
from .service import get_product, record_status


async def get_sales(id: str) -> SaleList:
    await get_product(id)
    rows = await sale_rows(id)
    return SaleList(list_data=[SaleInfo.model_validate(row.to_dict()) for row in rows],
                    count=len(rows))


async def confirm_sale(id: str, form_data: SaleCreate, actor: CurrentUser) -> SaleInfo:
    async with transaction():
        product = await lock_product(id)
        quote = await load_quote(id, form_data.quote_id)
        if quote.revision != form_data.quote_revision or product.cost_price != form_data.cost_price:
            raise LangException(409, QuoteError.STALE)
        vendor = await lock_vendor(str(quote.vendor_id))
        snapshot = await ProductSaleTable.create(data={
            "vendor_country": quote.vendor_country, "currency": quote.currency,
            "original_amount": quote.original_amount, "exchange_rate": quote.exchange_rate,
            "amount_twd": quote.amount_twd, "product_id": product.id, "quote_id": quote.id,
            "vendor_id": vendor.id,
            "vendor_name": vendor.name, "cost_price": product.cost_price,
            "profit_amount": quote.amount_twd - product.cost_price,
            "changed_by": actor["id"], "operator_name": actor["username"], "sold_at": utc_now(),
        })
        source = product.status
        product.status, product.updated_at, product.updated_by = "sold", utc_now(), actor["id"]
        await record_status(product, source, actor, "sale", None)
        await active_session().flush()
        return SaleInfo.model_validate(snapshot)
