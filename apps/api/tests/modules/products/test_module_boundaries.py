from contextlib import contextmanager

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

from modules.brands import service as brands
from modules.brands.schema import BrandCreate
from modules.products import quotes, service
from modules.products.quote_schema import QuoteCreate
from modules.products.schema import ProductCreate
from modules.vendors import service as vendors
from modules.vendors.schema import VendorCreate
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


@contextmanager
def queries():
    bind = active_session().bind
    assert isinstance(bind, AsyncEngine)
    engine = bind.sync_engine
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


async def product(name):
    brand = await brands.create_brand(BrandCreate(name=name))
    return await service.create_product(ProductCreate(
        name=name, brand_id=brand.id, category="包包", cost_price=100,
    ), ACTOR)


async def test_product_list_batches_brand_lookup(db):
    items = [await product(f"brand-{index}") for index in range(5)]
    active_session().expire_all()
    with queries() as statements:
        result = await service.get_product_list(limit=20)
    assert {row.id for row in result.list_data} == {item.id for item in items}
    assert {row.brand for row in result.list_data} == {f"brand-{index}" for index in range(5)}
    assert len(statements) == 3


async def test_quote_list_batches_vendor_lookup(db):
    item = await product("batch-quotes")
    for index in range(5):
        vendor = await vendors.create_vendor(VendorCreate(name=f"vendor-{index}"))
        await quotes.create_quote(item.id, QuoteCreate(
            vendor_id=vendor.id, original_amount="100",
        ), ACTOR)
    active_session().expire_all()
    with queries() as statements:
        result = await quotes.get_quotes(item.id)
    assert {row.vendor_name for row in result.list_data} == {
        f"vendor-{index}" for index in range(5)
    }
    assert len(statements) == 4


async def test_quote_creation_rolls_back_vendor_usage_on_failure(db, monkeypatch):
    item = await product("rollback-quote")
    vendor = await vendors.create_vendor(VendorCreate(name="rollback-vendor"))

    async def fail(row):
        raise RuntimeError("response failed")

    monkeypatch.setattr(quotes, "quote_info", fail)
    with pytest.raises(RuntimeError, match="response failed"):
        await quotes.create_quote(item.id, QuoteCreate(
            vendor_id=vendor.id, original_amount="100",
        ), ACTOR)
    assert (await quotes.get_quotes(item.id)).count == 0
    removed = await vendors.delete_vendor(vendor.id)
    assert removed.is_active
    assert (await vendors.get_vendors(include_inactive=True)).count == 0
