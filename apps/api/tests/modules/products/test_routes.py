from unittest.mock import AsyncMock

import pytest

from modules.products import service
from modules.products.schema import ProductList
from tests.modules.helpers import authenticate

ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/products/"), ("POST", "/api/products/"),
    ("GET", f"/api/products/{ID}"), ("PATCH", f"/api/products/{ID}"),
    ("DELETE", f"/api/products/{ID}"), ("GET", f"/api/products/{ID}/history"),
])
async def test_product_routes_require_login(client, method, path):
    assert (await client.request(method, path, json={})).status_code == 401


@pytest.mark.asyncio
async def test_staff_can_list_products(client, set_current_users, monkeypatch):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    monkeypatch.setattr(service, "get_product_list", AsyncMock(return_value=ProductList(
        list_data=[], next_cursor=None, prev_cursor=None, has_next=False,
        has_previous=False, total_count=0,
    )))
    result = await client.get("/api/products/?limit=20")
    assert result.status_code == 200 and result.json()["total_count"] == 0
