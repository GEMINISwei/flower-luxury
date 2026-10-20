import re
from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import func, select

from modules.brands import service as brands
from modules.brands.schema import BrandCreate
from modules.products import photos, service
from modules.products.model import ProductHistoryTable, ProductTable
from modules.products.schema import ProductCreate, StatusChange, StatusReturn
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.http.errors import LangException

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


@pytest.fixture(autouse=True)
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "UPLOADS_DIR", tmp_path)


async def product(name="手袋", serial="same"):
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    return await service.create_product(ProductCreate(
        name=name, brand_id=brand.id, category="包包", cost_price=3000, serial_number=serial,
    ), ACTOR)


def image_file():
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buffer, format="PNG")
    return UploadFile(filename="phone.png", file=BytesIO(buffer.getvalue()))


async def test_sold_product_rejects_all_mutations_until_return(db):
    item = await product()
    uploaded = await photos.upload_photos(item.id, [image_file()], ACTOR)
    await service.change_status(item.id, StatusChange(to_status="sold"), ACTOR)
    original = await service.get_product(item.id)
    actions = [
        lambda: service.update_product(item.id, ProductCreate(
            name="changed", brand_id=original.brand_id, category="包包", cost_price=1,
        ), ACTOR),
        lambda: service.delete_product(item.id, ACTOR),
        lambda: photos.upload_photos(item.id, [image_file()], ACTOR),
        lambda: photos.delete_photo(item.id, uploaded.list_data[0].id, ACTOR),
        lambda: photos.set_main_photo(item.id, uploaded.list_data[0].id, ACTOR),
        lambda: service.change_status(item.id, StatusChange(to_status="in_stock"), ACTOR),
    ]
    for action in actions:
        with pytest.raises(LangException) as error:
            await action()
        assert error.value.status_code == 409
    await service.return_status(
        item.id, StatusReturn(to_status="not_acquired", reason="客戶退貨"), ACTOR,
    )
    await service.update_product(item.id, ProductCreate(
        name="changed", brand_id=original.brand_id, category="包包", cost_price=1,
    ), ACTOR)
    assert (await service.get_product(item.id)).name == "changed"


async def test_status_history_preserves_actor_and_reason(db):
    item = await product()
    assert re.fullmatch(r"LX\d{8}[A-Z0-9]{5}", item.sku)
    assert item.status == "not_acquired"
    await service.change_status(item.id, StatusChange(to_status="sold", reason="成交"), ACTOR)
    await service.return_status(
        item.id, StatusReturn(to_status="in_stock", reason="退貨"), ACTOR,
    )
    await service.return_status(
        item.id, StatusReturn(to_status="not_acquired", reason="收購取消"), ACTOR,
    )
    histories = (await service.get_history(item.id)).list_data
    assert len(histories) == 4
    assert [row.to_status for row in histories] == [
        "not_acquired", "in_stock", "sold", "not_acquired",
    ]
    assert histories[0].reason == "收購取消"
    assert all(row.changed_by == ACTOR["id"] for row in histories)
    assert all(row.operator_name == "staff" for row in histories)
    assert all(row.changed_at for row in histories)


async def test_status_history_failure_rolls_back_status(db, monkeypatch):
    item = await product()

    async def fail(*args, **kwargs):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(ProductHistoryTable, "create", fail)
    with pytest.raises(RuntimeError, match="history unavailable"):
        await service.change_status(item.id, StatusChange(to_status="sold"), ACTOR)
    assert (await service.get_product(item.id)).status == "not_acquired"


async def test_products_filter_page_and_allow_duplicate_serials(db):
    first = await product()
    await service.create_product(ProductCreate(
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
    assert filtered.total_count == 1 and filtered.list_data[0].cost_price == 0


async def test_delete_product_hides_detail_and_photos(db):
    item = await product()
    photo = (await photos.upload_photos(item.id, [image_file()], ACTOR)).list_data[0]
    await service.delete_product(item.id, ACTOR)
    with pytest.raises(LangException) as error:
        await service.get_product(item.id)
    assert error.value.status_code == 404
    with pytest.raises(LangException):
        await photos.photo_path(photo.id)
    assert (await service.get_product_list(limit=20)).total_count == 0


async def test_more_than_ten_photos_and_main_replacement(db):
    item = await product()
    uploaded = await photos.upload_photos(item.id, [image_file() for _ in range(12)], ACTOR)
    assert len(uploaded.list_data) == 12
    assert uploaded.list_data[0].is_main
    assert sum(photo.is_main for photo in uploaded.list_data) == 1
    await photos.set_main_photo(item.id, uploaded.list_data[3].id, ACTOR)
    assert (await service.get_product(item.id)).main_photo_id == uploaded.list_data[3].id
    await photos.delete_photo(item.id, uploaded.list_data[3].id, ACTOR)
    assert (await service.get_product(item.id)).main_photo_id == uploaded.list_data[0].id
    listed = await photos.list_photos(item.id)
    assert len(listed.list_data) == 11 and sum(photo.is_main for photo in listed.list_data) == 1


async def test_photo_batch_limit_and_atomic_validation(db):
    item = await product()
    for files in [
        [image_file(), UploadFile(filename="fake.png", file=BytesIO(b"invalid"))],
        [UploadFile(filename="large.png", file=BytesIO(b"x" * (15 * 1024 * 1024 + 1)))],
    ]:
        with pytest.raises(LangException):
            await photos.upload_photos(item.id, files, ACTOR)
    assert (await photos.list_photos(item.id)).count == 0
    assert await active_session().scalar(select(func.count()).select_from(ProductTable)) == 1
