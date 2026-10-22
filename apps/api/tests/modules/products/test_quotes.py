import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from modules.brands import service as brands
from modules.brands.schema import BrandCreate
from modules.exchange_rates import service as exchange
from modules.exchange_rates.schema import ExchangeRateUpdate
from modules.products import quotes, sales, service
from modules.products.model import ProductHistoryTable, ProductQuoteTable, ProductSaleTable
from modules.products.quote_schema import QuoteCreate, QuoteUpdate, SaleCreate
from modules.products.schema import ProductCreate, StatusChange, StatusReturn
from modules.vendors import service as vendors
from modules.vendors.schema import VendorCreate, VendorUpdate
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session, session_scope
from shared.http.errors import LangException

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


async def setup_trade(country="CN", cost=3000):
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    product = await service.create_product(ProductCreate(
        name="手袋", brand_id=brand.id, category="包包", cost_price=cost,
    ), ACTOR)
    vendor = await vendors.create_vendor(VendorCreate(name="Buyer", country=country))
    await exchange.update_settings(ExchangeRateUpdate(rate="4.512345"), ACTOR)
    quote = await quotes.create_quote(product.id, QuoteCreate(
        vendor_id=vendor.id, original_amount="100.25" if country == "CN" else "100",
    ), ACTOR)
    return product, vendor, quote


def confirmation(quote, cost=3000):
    return SaleCreate(quote_id=quote.id, quote_revision=quote.revision, cost_price=cost)


async def test_quote_is_unique_per_vendor_and_rejects_inactive_vendor(db):
    product, vendor, quote = await setup_trade()
    with pytest.raises(LangException) as error:
        await quotes.create_quote(product.id, QuoteCreate(
            vendor_id=vendor.id, original_amount="200",
        ), ACTOR)
    assert error.value.status_code == 409
    assert (await quotes.get_quotes(product.id)).count == 1
    await vendors.update_vendor(vendor.id, VendorUpdate(
        name=vendor.name, country="CN", note=None, is_active=False,
    ))
    await quotes.delete_quote(product.id, quote.id, ACTOR)
    with pytest.raises(LangException) as error:
        await quotes.create_quote(product.id, QuoteCreate(
            vendor_id=vendor.id, original_amount="200",
        ), ACTOR)
    assert error.value.status_code == 409


async def test_quote_edit_preserves_rate_until_explicit_refresh(db):
    product, _, quote = await setup_trade()
    await exchange.update_settings(ExchangeRateUpdate(rate="5.123456"), ACTOR)
    changed = await quotes.update_quote(product.id, quote.id, QuoteUpdate(
        original_amount="200.50", note="revised",
    ), ACTOR)
    assert changed.exchange_rate == Decimal("4.512345")
    assert changed.amount_twd == 905 and changed.note == "revised"
    assert changed.revision == quote.revision + 1
    refreshed = await quotes.refresh_quote(product.id, quote.id, ACTOR)
    assert refreshed.exchange_rate == Decimal("5.123456")
    assert refreshed.amount_twd == 1027 and refreshed.revision == changed.revision + 1
    assert refreshed.original_amount == Decimal("200.50")


async def test_direct_sale_is_rejected_and_quote_must_belong_to_product(db):
    product, _, quote = await setup_trade()
    with pytest.raises(LangException) as error:
        await service.change_status(product.id, StatusChange(to_status="sold"), ACTOR)
    assert error.value.status_code == 409
    other = await service.create_product(ProductCreate(
        name="other", brand_id=product.brand_id, category="包包", cost_price=3000,
    ), ACTOR)
    with pytest.raises(LangException) as error:
        await sales.confirm_sale(other.id, confirmation(quote), ACTOR)
    assert error.value.status_code == 404
    assert (await service.get_product(other.id)).status == "not_acquired"


async def test_sale_snapshots_profit_and_locks_all_mutations(db):
    product, vendor, quote = await setup_trade()
    sale = await sales.confirm_sale(product.id, confirmation(quote), ACTOR)
    assert sale.vendor_name == "Buyer" and sale.vendor_country == "CN"
    assert sale.exchange_rate == Decimal("4.512345")
    assert sale.original_amount == Decimal("100.25") and sale.amount_twd == 452
    assert sale.cost_price == 3000 and sale.profit_amount == -2548 and sale.is_current
    assert sale.changed_by == ACTOR["id"] and sale.operator_name == "staff" and sale.sold_at
    assert (await service.get_product(product.id)).status == "sold"
    assert (await quotes.get_quotes(product.id)).list_data[0].has_sales
    for action in [
        lambda: quotes.update_quote(product.id, quote.id, QuoteUpdate(original_amount="1"), ACTOR),
        lambda: quotes.refresh_quote(product.id, quote.id, ACTOR),
        lambda: quotes.delete_quote(product.id, quote.id, ACTOR),
        lambda: quotes.create_quote(product.id, QuoteCreate(
            vendor_id=vendor.id, original_amount="1",
        ), ACTOR),
        lambda: sales.confirm_sale(product.id, confirmation(quote), ACTOR),
    ]:
        with pytest.raises(LangException) as error:
            await action()
        assert error.value.status_code == 409
    await vendors.update_vendor(vendor.id, VendorUpdate(
        name="Renamed", country="CN", note=None, is_active=True,
    ))
    assert (await sales.get_sales(product.id)).list_data[0].vendor_name == "Buyer"


async def test_sale_history_failure_rolls_back_entire_sale(db, monkeypatch):
    product, _, quote = await setup_trade()

    async def fail(*args, **kwargs):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(ProductHistoryTable, "create", fail)
    with pytest.raises(RuntimeError, match="history unavailable"):
        await sales.confirm_sale(product.id, confirmation(quote), ACTOR)
    assert (await service.get_product(product.id)).status == "not_acquired"
    assert (await sales.get_sales(product.id)).count == 0
    assert not (await quotes.get_quotes(product.id)).list_data[0].has_sales


async def test_sale_rejects_stale_quote_or_cost(db):
    product, _, quote = await setup_trade()
    await quotes.update_quote(product.id, quote.id, QuoteUpdate(original_amount="200"), ACTOR)
    with pytest.raises(LangException) as error:
        await sales.confirm_sale(product.id, confirmation(quote), ACTOR)
    assert error.value.status_code == 409
    updated = (await quotes.get_quotes(product.id)).list_data[0]
    with pytest.raises(LangException) as error:
        await sales.confirm_sale(product.id, confirmation(updated, cost=1), ACTOR)
    assert error.value.status_code == 409
    assert (await sales.get_sales(product.id)).count == 0


async def test_return_and_resale_preserve_snapshots_and_quote(db):
    product, _, quote = await setup_trade()
    original = await sales.confirm_sale(product.id, confirmation(quote), ACTOR)
    await service.return_status(
        product.id, StatusReturn(to_status="not_acquired", reason="退貨"), ACTOR,
    )
    past = (await sales.get_sales(product.id)).list_data[0]
    assert not past.is_current and past.return_reason == "退貨" and past.returned_at
    assert past.returned_by == ACTOR["id"]
    with pytest.raises(LangException) as error:
        await quotes.delete_quote(product.id, quote.id, ACTOR)
    assert error.value.status_code == 409
    await service.update_product(product.id, ProductCreate(
        name="changed", brand_id=product.brand_id, category="包包", cost_price=10,
    ), ACTOR)
    changed = await quotes.update_quote(
        product.id, quote.id, QuoteUpdate(original_amount="1000"), ACTOR,
    )
    second = await sales.confirm_sale(product.id, confirmation(changed, cost=10), ACTOR)
    assert second.profit_amount == 4502 and second.id != original.id
    history = (await sales.get_sales(product.id)).list_data
    assert len(history) == 2 and sum(row.is_current for row in history) == 1
    old = next(row for row in history if row.id == original.id)
    assert old.cost_price == 3000 and old.amount_twd == 452 and old.profit_amount == -2548
    assert (await quotes.get_quotes(product.id)).count == 1


async def test_unused_quote_can_be_deleted_without_unlocking_country(db):
    product, vendor, quote = await setup_trade()
    await quotes.delete_quote(product.id, quote.id, ACTOR)
    assert (await quotes.get_quotes(product.id)).count == 0
    with pytest.raises(LangException) as error:
        await vendors.update_vendor(vendor.id, VendorUpdate(
            name=vendor.name, country="TW", note=None, is_active=True,
        ))
    assert error.value.status_code == 409


async def test_deleted_products_hide_quotes_and_sales(db):
    product, _, _ = await setup_trade()
    await service.delete_product(product.id, ACTOR)
    for action in [lambda: quotes.get_quotes(product.id), lambda: sales.get_sales(product.id)]:
        with pytest.raises(LangException) as error:
            await action()
        assert error.value.status_code == 404


async def test_concurrent_sales_create_one_current_sale(db):
    product, _, quote = await setup_trade()
    await active_session().commit()

    async def sell():
        async with session_scope():
            return await sales.confirm_sale(product.id, confirmation(quote), ACTOR)

    results = await asyncio.gather(sell(), sell(), return_exceptions=True)
    errors = [result for result in results if isinstance(result, LangException)]
    assert len(errors) == 1 and errors[0].status_code == 409
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert await active_session().scalar(select(func.count()).select_from(ProductSaleTable)) == 1
    assert await active_session().scalar(select(func.count()).select_from(ProductQuoteTable)) == 1


async def test_concurrent_quotes_keep_one_vendor_quote(db):
    product, vendor, quote = await setup_trade()
    await quotes.delete_quote(product.id, quote.id, ACTOR)
    await active_session().commit()

    async def create():
        async with session_scope():
            return await quotes.create_quote(product.id, QuoteCreate(
                vendor_id=vendor.id, original_amount="100",
            ), ACTOR)

    results = await asyncio.gather(create(), create(), return_exceptions=True)
    errors = [result for result in results if isinstance(result, LangException)]
    assert len(errors) == 1 and errors[0].status_code == 409
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert await active_session().scalar(select(func.count()).select_from(ProductQuoteTable)) == 1


async def test_return_failure_keeps_current_sale(db, monkeypatch):
    product, _, quote = await setup_trade()
    await sales.confirm_sale(product.id, confirmation(quote), ACTOR)

    async def fail(*args, **kwargs):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(ProductHistoryTable, "create", fail)
    with pytest.raises(RuntimeError, match="history unavailable"):
        await service.return_status(product.id, StatusReturn(
            to_status="not_acquired", reason="退貨",
        ), ACTOR)
    assert (await service.get_product(product.id)).status == "sold"
    sale = (await sales.get_sales(product.id)).list_data[0]
    assert sale.is_current and sale.returned_at is None and sale.return_reason is None


async def test_twd_quote_requires_no_rate_and_cannot_change_currency(db):
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    product = await service.create_product(ProductCreate(
        name="Bag", brand_id=brand.id, category="包包", cost_price=100,
    ), ACTOR)
    vendor = await vendors.create_vendor(VendorCreate(name="Taiwan", country="TW"))
    form = QuoteCreate.model_validate({
        "vendor_id": vendor.id, "original_amount": "101", "exchange_rate": "99",
        "currency": "CNY", "amount_twd": 999999,
    })
    quote = await quotes.create_quote(product.id, form, ACTOR)
    assert quote.currency == "TWD" and quote.amount_twd == 101 and quote.exchange_rate == 1
    refreshed = await quotes.refresh_quote(product.id, quote.id, ACTOR)
    assert refreshed.currency == "TWD" and refreshed.exchange_rate == 1


async def test_cny_quote_missing_rate_does_not_lock_vendor(db):
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    product = await service.create_product(ProductCreate(
        name="Bag", brand_id=brand.id, category="包包", cost_price=100,
    ), ACTOR)
    vendor = await vendors.create_vendor(VendorCreate(name="China", country="CN"))
    with pytest.raises(LangException) as error:
        await quotes.create_quote(product.id, QuoteCreate(
            vendor_id=vendor.id, original_amount="100",
        ), ACTOR)
    assert error.value.status_code == 409
    assert not (await vendors.get_vendors()).list_data[0].country_locked
    assert (await quotes.get_quotes(product.id)).count == 0
