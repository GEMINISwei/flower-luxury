import pytest
from pydantic import ValidationError

from modules.vendors import service
from modules.vendors.model import VendorTable
from modules.vendors.schema import VendorCreate, VendorUpdate
from shared.db.session import active_session
from shared.http.errors import LangException


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
async def test_locked_vendor_country_cannot_change_and_delete_deactivates(db):
    vendor = await service.create_vendor(VendorCreate(name="Buyer", country="TW"))
    row = await VendorTable.find_by_id(vendor.id)
    assert row is not None
    row.country_locked = True
    await active_session().flush()
    with pytest.raises(LangException) as error:
        await service.update_vendor(vendor.id, VendorUpdate(
            name="Buyer", country="CN", is_active=True,
        ))
    assert error.value.status_code == 409
    updated = await service.update_vendor(vendor.id, VendorUpdate(
        name="Renamed", country="TW", note="new note", is_active=True,
    ))
    assert updated.country_locked and updated.note == "new note"
    await service.delete_vendor(vendor.id)
    assert (await service.get_vendors()).count == 0
    result = (await service.get_vendors(include_inactive=True)).list_data[0]
    assert result.country_locked and not result.is_active
