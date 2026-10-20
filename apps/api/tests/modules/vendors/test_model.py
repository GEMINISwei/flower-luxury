import pytest
from pydantic import ValidationError

from modules.brands import service as brands
from modules.brands.schema import BrandCreate
from modules.products import quotes
from modules.products import service as products
from modules.products.quote_schema import QuoteCreate
from modules.products.schema import ProductCreate
from modules.vendors import service
from modules.vendors.schema import VendorCreate, VendorUpdate
from shared.auth.contracts import CurrentUser
from shared.http.errors import LangException

ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


@pytest.mark.parametrize("name,country", [(" ", "TW"), ("Buyer", "US"), ("Buyer", "")])
def test_vendor_form_validates_country_and_name(name, country):
    with pytest.raises(ValidationError):
        VendorCreate(name=name, country=country)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vendor_names_are_unique_and_sorted(db):
    await service.create_vendor(VendorCreate(name=" Zebra ", country="TW", note="note"))
    await service.create_vendor(VendorCreate(name="Buyer", country="CN"))
    with pytest.raises(LangException) as error:
        await service.create_vendor(VendorCreate(name="zebra", country="CN"))
    assert error.value.status_code == 409
    result = await service.get_vendors()
    assert [row.name for row in result.list_data] == ["Buyer", "Zebra"]
    assert [row.currency for row in result.list_data] == ["CNY", "TWD"]
    unused = await service.create_vendor(VendorCreate(name="Unused", country="TW"))
    await service.delete_vendor(unused.id)
    assert (await service.get_vendors(include_inactive=True)).count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quoted_vendor_country_is_locked_and_delete_disables(db):
    vendor = await service.create_vendor(VendorCreate(name="Buyer", country="TW"))
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    product = await products.create_product(ProductCreate(
        name="Bag", brand_id=brand.id, category="包包", cost_price=100,
    ), ACTOR)
    await quotes.create_quote(product.id, QuoteCreate(
        vendor_id=vendor.id, original_amount="100",
    ), ACTOR)
    with pytest.raises(LangException) as error:
        await service.update_vendor(vendor.id, VendorUpdate(
            name="Buyer", country="CN", note=None, is_active=True,
        ))
    assert error.value.status_code == 409
    updated = await service.update_vendor(vendor.id, VendorUpdate(
        name="Renamed", country="TW", note="new note", is_active=True,
    ))
    assert updated.country_locked and updated.name == "Renamed" and updated.note == "new note"
    await service.delete_vendor(vendor.id)
    assert (await service.get_vendors()).count == 0
    assert not (await service.get_vendors(include_inactive=True)).list_data[0].is_active
