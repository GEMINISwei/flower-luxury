import uuid

import pytest
import pytest_asyncio
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, Uuid, insert, update

from modules.brands import service
from modules.brands.model import BrandTable
from modules.brands.schema import BrandCreate, BrandUpdate
from shared.db.session import active_session
from shared.http.errors import LangException
from shared.time import utc_now

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def reference_table(db):
    table = Table(
        "test_brand_references", BrandTable.metadata,
        Column("id", Integer, primary_key=True),
        Column("brand_id", Uuid, ForeignKey("brands.id", ondelete="RESTRICT")),
        Column("deleted_at", DateTime, nullable=True),
    )
    connection = await active_session().connection()
    await connection.run_sync(lambda sync: table.create(sync))
    try:
        yield table
    finally:
        await connection.run_sync(lambda sync: table.drop(sync))
        BrandTable.metadata.remove(table)


async def test_brand_names_are_unique_and_sorted(db):
    await service.create_brand(BrandCreate(name=" Dior "))
    await service.create_brand(BrandCreate(name="CHANEL"))
    with pytest.raises(LangException) as error:
        await service.create_brand(BrandCreate(name="dior"))
    assert error.value.status_code == 409
    result = await service.get_brands()
    assert [brand.name for brand in result.list_data] == ["CHANEL", "Dior"]
    removed = await service.delete_brand(result.list_data[0].id)
    assert removed.in_use is False
    assert (await service.get_brands(include_inactive=True)).count == 1


async def test_referenced_brand_is_deactivated_and_existing_reference_can_keep_it(reference_table):
    brand = await service.create_brand(BrandCreate(name="CHANEL"))
    await active_session().execute(insert(reference_table).values(
        id=1, brand_id=uuid.UUID(brand.id),
    ))
    assert (await service.get_brands()).list_data[0].in_use is True
    await active_session().execute(update(reference_table).values(deleted_at=utc_now()))
    removed = await service.delete_brand(brand.id)
    assert removed.in_use is True and removed.is_active is False
    assert (await service.get_brands()).count == 0
    with pytest.raises(LangException) as error:
        await service.require_active_brand(brand.id)
    assert error.value.status_code == 409
    await service.require_active_brand(brand.id, existing_id=brand.id)
    updated = await service.update_brand(brand.id, BrandUpdate(name="Chanel", is_active=True))
    assert updated.name == "Chanel" and updated.in_use is True
