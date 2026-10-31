import pytest
from pydantic import ValidationError

from modules.vendors import service
from modules.vendors.model import VendorTable
from modules.vendors.schema import VendorCreate, VendorUpdate
from shared.db.session import active_session
from shared.http.errors import LangException


def test_vendor_form_requires_name_without_country():
    with pytest.raises(ValidationError):
        VendorCreate(name=" ")
    assert VendorCreate(name="Buyer").name == "Buyer"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vendor_names_are_unique_and_sorted(db):
    await service.create_vendor(VendorCreate(name=" Zebra ", note="note"))
    await service.create_vendor(VendorCreate(name="Buyer"))
    with pytest.raises(LangException) as error:
        await service.create_vendor(VendorCreate(name="zebra"))
    assert error.value.status_code == 409
    result = await service.get_vendors()
    assert [row.name for row in result.list_data] == ["Buyer", "Zebra"]
    assert all("country" not in row.model_dump() and "currency" not in row.model_dump()
               for row in result.list_data)
    unused = await service.create_vendor(VendorCreate(name="Unused"))
    await service.delete_vendor(unused.id)
    assert (await service.get_vendors(include_inactive=True)).count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quoted_vendor_can_be_renamed_and_delete_deactivates(db):
    vendor = await service.create_vendor(VendorCreate(name="Buyer"))
    row = await VendorTable.find_by_id(vendor.id)
    assert row is not None
    row.has_quotes = True
    await active_session().flush()
    updated = await service.update_vendor(vendor.id, VendorUpdate(
        name="Renamed", note="new note", is_active=True,
    ))
    assert updated.has_quotes and updated.note == "new note"
    await service.delete_vendor(vendor.id)
    assert (await service.get_vendors()).count == 0
    result = (await service.get_vendors(include_inactive=True)).list_data[0]
    assert result.has_quotes and not result.is_active
