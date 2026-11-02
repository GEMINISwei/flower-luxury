from datetime import datetime

import pytest
from sqlalchemy import update

from modules.brands import service as brands
from modules.brands.schema import BrandCreate
from modules.products import service
from modules.products.model import ProductTable
from modules.products.schema import ProductCreate
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


async def create(brand_id: str, **fields: str | None) -> str:
    values = {"name": "手袋", **fields}
    item = await service.create_product(ProductCreate(
        brand_id=brand_id, category="包包", cost_price=0, **values,  # type: ignore[arg-type]
    ), ACTOR)
    return item.id


async def brand(name: str = "CHANEL") -> str:
    return (await brands.create_brand(BrandCreate(name=name))).id


async def test_suggestions_match_keyword_ignoring_case_across_brands(db):
    chanel, hermes = await brand(), await brand("HERMES")
    await create(chanel, color="Black")
    await create(hermes, color="dark black")
    await create(hermes, color="White")
    result = await service.get_field_suggestions("color", "BLACK")
    assert sorted(result.values) == ["Black", "dark black"]


async def test_suggestions_rank_by_frequency_and_return_each_value_once(db):
    brand_id = await brand()
    for color in ["Red", "Blue", "Blue", "Blue", "Red"]:
        await create(brand_id, color=color)
    assert (await service.get_field_suggestions("color", "")).values == ["Blue", "Red"]


async def test_suggestions_tie_breaks_by_most_recent_use(db):
    brand_id = await brand()
    older = await create(brand_id, model_name="Classic 25")
    newer = await create(brand_id, model_name="Classic 30")
    for id, moment in [(older, datetime(2026, 1, 1)), (newer, datetime(2026, 6, 1))]:
        await active_session().execute(
            update(ProductTable).where(ProductTable.id == id).values(created_at=moment))
    result = await service.get_field_suggestions("model_name", "classic")
    assert result.values == ["Classic 30", "Classic 25"]


async def test_suggestions_return_at_most_ten_values(db):
    brand_id = await brand()
    for index in range(12):
        await create(brand_id, serial_number=f"SN-{index:02d}")
    assert len((await service.get_field_suggestions("serial_number", "SN")).values) == 10


async def test_suggestions_skip_deleted_products_and_blank_values(db):
    brand_id = await brand()
    removed = await create(brand_id, name="已刪除的包")
    await service.delete_product(removed, ACTOR)
    await create(brand_id, name="留下的包", model_name="")
    await create(brand_id, name="另一個包", model_name=None)
    names = (await service.get_field_suggestions("name", "包")).values
    assert sorted(names) == sorted(["留下的包", "另一個包"])
    assert (await service.get_field_suggestions("model_name", "")).values == []


async def test_suggestions_treat_like_wildcards_as_plain_text(db):
    brand_id = await brand()
    await create(brand_id, name="100% 羊毛")
    await create(brand_id, name="1000 羊毛")
    await create(brand_id, name="A_B")
    await create(brand_id, name="AXB")
    assert (await service.get_field_suggestions("name", "100%")).values == ["100% 羊毛"]
    assert (await service.get_field_suggestions("name", "A_B")).values == ["A_B"]
