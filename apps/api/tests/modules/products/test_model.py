import re

import pytest
from sqlalchemy import func, select

from modules.brands import service as brands
from modules.brands.schema import BrandCreate, BrandUpdate
from modules.products import service
from modules.products.model import ProductHistoryTable, ProductTable
from modules.products.schema import ProductCreate
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.http.errors import LangException

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


async def product():
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    return await service.create_product(ProductCreate(
        name="手袋", brand_id=brand.id, category="包包", cost_price=3000, serial_number="same",
    ), ACTOR)


async def test_create_records_sku_and_actor_history(db):
    item = await product()
    assert re.fullmatch(r"LX\d{8}[A-Z0-9]{5}", item.sku)
    assert item.status == "not_acquired" and item.main_photo_id is None
    histories = (await service.get_history(item.id)).list_data
    assert len(histories) == 1
    history = histories[0]
    assert history.from_status is None and history.to_status == "not_acquired"
    assert history.action == "create" and history.reason is None
    assert history.changed_by == ACTOR["id"] and history.operator_name == "staff"
    assert history.changed_at


async def test_create_history_failure_rolls_back_product(db, monkeypatch):
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))

    async def fail(*args, **kwargs):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(ProductHistoryTable, "create", fail)
    with pytest.raises(RuntimeError, match="history unavailable"):
        await service.create_product(ProductCreate(
            name="手袋", brand_id=brand.id, category="包包", cost_price=3000,
        ), ACTOR)
    assert await active_session().scalar(select(func.count()).select_from(ProductTable)) == 0


async def test_products_filter_page_and_allow_duplicate_serials(db):
    first = await product()
    second = await service.create_product(ProductCreate(
        name="鞋子", brand_id=first.brand_id, category="鞋子", cost_price=0,
        serial_number="same", color="black", year=2026,
    ), ACTOR)
    page = await service.get_product_list(limit=1)
    assert page.total_count == 2 and page.has_next
    next_page = await service.get_product_list(limit=1, cursor=page.next_cursor)
    assert next_page.list_data[0].id != page.list_data[0].id
    filtered = await service.get_product_list(
        limit=20, keyword="鞋", brand_id=first.brand_id, category="鞋子",
        status="not_acquired", color="black", year=2026,
    )
    assert filtered.total_count == 1 and filtered.list_data[0].id == second.id
    for keyword in [second.sku, "same"]:
        assert (await service.get_product_list(limit=20, keyword=keyword)).total_count >= 1


async def test_inactive_brand_rejects_new_products_but_existing_product_can_keep_it(db):
    item = await product()
    await brands.update_brand(item.brand_id, BrandUpdate(name="CHANEL", is_active=False))
    form = ProductCreate(name="Updated", brand_id=item.brand_id, category="包包", cost_price=10)
    with pytest.raises(LangException) as error:
        await service.create_product(form, ACTOR)
    assert error.value.status_code == 409
    updated = await service.update_product(item.id, form, ACTOR)
    assert updated.name == "Updated" and updated.sku == item.sku


async def test_sold_product_rejects_core_mutations(db):
    item = await product()
    row = await ProductTable.find_by_id(item.id)
    assert row is not None
    row.status = "sold"
    await active_session().flush()
    for operation in [
        lambda: service.update_product(item.id, ProductCreate(
            name="Changed", brand_id=item.brand_id, category="包包", cost_price=1,
        ), ACTOR),
        lambda: service.delete_product(item.id, ACTOR),
    ]:
        with pytest.raises(LangException) as error:
            await operation()
        assert error.value.status_code == 409
    assert (await service.get_product(item.id)).name == item.name


async def test_delete_hides_product_and_history_but_keeps_brand_reference(db):
    item = await product()
    await service.delete_product(item.id, ACTOR)
    for operation in [service.get_product, service.get_history]:
        with pytest.raises(LangException) as error:
            await operation(item.id)
        assert error.value.status_code == 404
    assert (await service.get_product_list(limit=20)).total_count == 0
    assert await active_session().scalar(select(func.count()).select_from(ProductTable)) == 1
    removed = await brands.delete_brand(item.brand_id)
    assert removed.in_use and not removed.is_active
