from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from modules.products import imports, photos, service
from modules.products.images import PreparedPhoto
from modules.products.schema import PhotoInfo, PhotoList, ProductCreate, ProductInfo
from tests.modules.products.test_model import ACTOR

pytestmark = pytest.mark.asyncio
ID = "11111111-1111-4111-8111-111111111111"


async def test_imported_product_preserves_photo_order_and_main(monkeypatch):
    @asynccontextmanager
    async def transaction():
        yield

    form = ProductCreate(name="bag", brand_id=ID, category="包包", cost_price=0)
    item = ProductInfo(id=ID, sku="LX20261028ABCDE", brand="brand", status="not_acquired",
                       created_by=ACTOR["id"], created_at=datetime(2026, 10, 28),
                       **form.model_dump())
    batch = [PreparedPhoto(original=b"original", display=b"display", filename="photo.png",
                           extension="png", media_type="image/png") for _ in range(2)]
    created = PhotoList(list_data=[PhotoInfo(id=str(index), url="/file", is_main=index == 0,
                                           sort_order=index) for index in range(2)], count=2)
    monkeypatch.setattr(imports, "transaction", transaction)
    monkeypatch.setattr(service, "create_product", AsyncMock(return_value=item))
    monkeypatch.setattr(service, "get_product", AsyncMock(return_value=item))
    store = AsyncMock(return_value=created)
    main = AsyncMock(return_value=created)
    monkeypatch.setattr(photos, "store_prepared_photos", store)
    monkeypatch.setattr(photos, "set_main_photo", main)
    result = await imports.create_imported_product(form, batch, ACTOR, main_index=1)
    assert result.id == ID
    assert store.call_args.args == (ID, batch, ACTOR)
    assert main.call_args.args == (ID, "1", ACTOR)
