from unittest.mock import AsyncMock

import pytest

from modules.products import service
from modules.products.schema import FieldSuggestions, ProductList
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


@pytest.mark.asyncio
async def test_field_suggestions_require_login(client):
    assert (await client.get("/api/products/suggestions?field=name")).status_code == 401


@pytest.mark.asyncio
async def test_staff_can_get_field_suggestions(client, set_current_users, monkeypatch):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    lookup = AsyncMock(return_value=FieldSuggestions(values=["Black"]))
    monkeypatch.setattr(service, "get_field_suggestions", lookup)
    result = await client.get("/api/products/suggestions?field=color&q=bla")
    assert result.status_code == 200 and result.json() == {"values": ["Black"]}
    lookup.assert_awaited_once_with("color", "bla")


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [
    "field=cost_price", "field=internal_note", "field=year", "field=name&q=" + "x" * 101,
])
async def test_field_suggestions_reject_unknown_field_and_overlong_keyword(
    client, set_current_users, query,
):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    assert (await client.get(f"/api/products/suggestions?{query}")).status_code == 422
