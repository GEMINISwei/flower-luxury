from unittest.mock import AsyncMock

import pytest

from modules.products import service
from tests.modules.helpers import authenticate

ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["return", "status"])
async def test_status_workflow_routes_require_login(client, path):
    assert (await client.post(f"/api/products/{ID}/{path}", json={})).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["", "  ", None])
async def test_return_route_rejects_empty_reason(client, set_current_users, monkeypatch, reason):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    authenticate(client, "staff")
    operation = AsyncMock()
    monkeypatch.setattr(service, "return_status", operation)
    result = await client.post(f"/api/products/{ID}/return", json={
        "to_status": "not_acquired", "reason": reason,
    })
    assert result.status_code == 422
    operation.assert_not_awaited()
