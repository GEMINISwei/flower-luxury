from unittest.mock import AsyncMock

import pytest

from modules.vendors import service
from modules.vendors.schema import VendorList
from tests.modules.helpers import authenticate


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/vendors/"), ("POST", "/api/vendors/"),
    ("PATCH", "/api/vendors/11111111-1111-4111-8111-111111111111"),
    ("DELETE", "/api/vendors/11111111-1111-4111-8111-111111111111"),
])
async def test_vendor_routes_require_login(client, method, path):
    assert (await client.request(method, path, json={})).status_code == 401


@pytest.mark.asyncio
async def test_staff_can_manage_vendors(client, set_current_users, monkeypatch):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    monkeypatch.setattr(service, "get_vendors", AsyncMock(return_value=VendorList(list_data=[], count=0)))
    assert (await client.get("/api/vendors/")).status_code == 200
