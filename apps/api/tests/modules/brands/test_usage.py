import pytest

from modules.brands import service
from modules.brands.schema import BrandCreate, BrandUpdate
from modules.products import service as products
from modules.products.schema import ProductCreate
from shared.auth.contracts import CurrentUser

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


async def test_brand_usage_matches_delete_or_deactivate_even_after_product_soft_delete(db):
    unused = await service.create_brand(BrandCreate(name="Unused"))
    used = await service.create_brand(BrandCreate(name="Used"))
    assert unused.in_use is False
    item = await products.create_product(ProductCreate(
        name="Bag", brand_id=used.id, category="包包", cost_price=10,
    ), ACTOR)
    listing = await service.get_brands(include_inactive=True)
    assert {row.id: row.in_use for row in listing.list_data} == {
        unused.id: False, used.id: True,
    }
    updated = await service.update_brand(used.id, BrandUpdate(name="Renamed", is_active=True))
    assert updated.in_use is True
    await products.delete_product(item.id, ACTOR)
    listing = await service.get_brands(include_inactive=True)
    assert next(row for row in listing.list_data if row.id == used.id).in_use is True
    removed = await service.delete_brand(unused.id)
    assert removed.in_use is False
    deactivated = await service.delete_brand(used.id)
    assert deactivated.in_use is True and deactivated.is_active is False
