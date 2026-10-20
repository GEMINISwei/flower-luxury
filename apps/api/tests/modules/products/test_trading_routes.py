from unittest.mock import AsyncMock

import pytest

from modules.products import quotes, sales
from modules.products.quote_schema import QuoteList, SaleList
from tests.modules.helpers import authenticate

PRODUCT = "11111111-1111-4111-8111-111111111111"
QUOTE = "22222222-2222-4222-8222-222222222222"


@pytest.mark.asyncio
@pytest.mark.parametrize("method,suffix", [
    ("GET", "/quotes"), ("POST", "/quotes"), ("PATCH", f"/quotes/{QUOTE}"),
    ("DELETE", f"/quotes/{QUOTE}"), ("POST", f"/quotes/{QUOTE}/refresh-rate"),
    ("GET", "/sales"), ("POST", "/sales"),
])
async def test_trading_routes_require_login(client, method, suffix):
    result = await client.request(method, f"/api/products/{PRODUCT}{suffix}", json={})
    assert result.status_code == 401


@pytest.mark.asyncio
async def test_staff_can_use_trading_routes(client, set_current_users, monkeypatch):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    monkeypatch.setattr(quotes, "get_quotes", AsyncMock(return_value=QuoteList(list_data=[], count=0)))
    monkeypatch.setattr(sales, "get_sales", AsyncMock(return_value=SaleList(list_data=[], count=0)))
    assert (await client.get(f"/api/products/{PRODUCT}/quotes")).status_code == 200
    assert (await client.get(f"/api/products/{PRODUCT}/sales")).status_code == 200
