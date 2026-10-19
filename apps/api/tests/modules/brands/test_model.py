import pytest
from modules.brands import service
from modules.brands.schema import BrandCreate, BrandUpdate
from modules.products import service as products
from modules.products.schema import ProductCreate

from shared.auth.contracts import CurrentUser
from shared.http.errors import LangException

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


async def test_brand_names_are_unique_and_sorted(db):
    await service.create_brand(BrandCreate(name=" Dior "))
    await service.create_brand(BrandCreate(name="CHANEL"))
    with pytest.raises(LangException) as error:
        await service.create_brand(BrandCreate(name="dior"))
    assert error.value.status_code == 409
    result = await service.get_brands()
    assert [brand.name for brand in result.list_data] == ["CHANEL", "Dior"]


async def test_referenced_brand_is_disabled_and_existing_product_can_keep_it(db):
    brand = await service.create_brand(BrandCreate(name="CHANEL"))
    form = ProductCreate(name="包包", brand_id=brand.id, category="包包", cost_price=10)
    item = await products.create_product(form, ACTOR)
    await service.delete_brand(brand.id)
    assert (await service.get_brands()).count == 0
    assert (await service.get_brands(include_inactive=True)).list_data[0].is_active is False
    with pytest.raises(LangException):
        await products.create_product(form, ACTOR)
    await products.update_product(item.id, form, ACTOR)
    await service.update_brand(brand.id, BrandUpdate(name="Chanel", is_active=True))
    assert (await products.get_product(item.id)).brand == "Chanel"
