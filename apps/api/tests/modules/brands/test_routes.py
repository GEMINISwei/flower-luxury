from unittest.mock import AsyncMock

import pytest

from modules.brands import service
from modules.brands.schema import BrandList
from tests.modules.helpers import authenticate


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/brands/"), ("POST", "/api/brands/"),
    ("PATCH", "/api/brands/11111111-1111-4111-8111-111111111111"),
    ("DELETE", "/api/brands/11111111-1111-4111-8111-111111111111"),
])
async def test_brand_routes_require_login(client, method, path):
    assert (await client.request(method, path, json={})).status_code == 401


@pytest.mark.asyncio
async def test_staff_can_manage_brands(client, set_current_users, monkeypatch):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    monkeypatch.setattr(
        service, "get_brands", AsyncMock(return_value=BrandList(list_data=[], count=0)),
    )
    assert (await client.get("/api/brands/")).status_code == 200
