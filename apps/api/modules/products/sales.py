from sqlalchemy import select

from modules.vendors.public import lock_vendor
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.table import parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import LangException
from shared.time import utc_now

from .model import ProductSaleTable, lock_product
from .quote_rules import QuoteError
from .quote_schema import SaleCreate, SaleInfo, SaleList
from .quotes import load_quote
from .service import get_product, record_status


async def get_sales(id: str) -> SaleList:
    await get_product(id)
    rows = (await active_session().scalars(select(ProductSaleTable).where(
        ProductSaleTable.product_id == parse_uuid(id),
    ).order_by(ProductSaleTable.sold_at.desc(), ProductSaleTable.id.desc()))).all()
    return SaleList(list_data=[SaleInfo.model_validate(row.to_dict()) for row in rows],
                    count=len(rows))


async def confirm_sale(id: str, form_data: SaleCreate, actor: CurrentUser) -> SaleInfo:
    async with transaction():
        product = await lock_product(id)
        quote = await load_quote(id, form_data.quote_id)
        if quote.revision != form_data.quote_revision or product.cost_price != form_data.cost_price:
            raise LangException(409, QuoteError.STALE)
        vendor = await lock_vendor(str(quote.vendor_id))
        data = {key: getattr(quote, key) for key in (
            "vendor_country", "currency", "original_amount", "exchange_rate", "amount_twd",
        )}
        snapshot = await ProductSaleTable.create(data={
            **data, "product_id": product.id, "quote_id": quote.id, "vendor_id": vendor.id,
            "vendor_name": vendor.name, "cost_price": product.cost_price,
            "profit_amount": quote.amount_twd - product.cost_price,
            "changed_by": actor["id"], "operator_name": actor["username"], "sold_at": utc_now(),
        })
        source = product.status
        product.status, product.updated_at, product.updated_by = "sold", utc_now(), actor["id"]
        await record_status(product, source, actor, "sale", None)
        await active_session().flush()
        return SaleInfo.model_validate(snapshot)
