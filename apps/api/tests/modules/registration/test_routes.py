import hashlib
from unittest.mock import AsyncMock

import pytest

from modules.registration import router, service
from modules.registration.model import RegistrationTable
from modules.users.public import UserOperate
from tests.modules.helpers import authenticate

KEY = "shop-manager-key"
FORM = {
    "username": "manager", "nickname": "店長", "password": "password123",
    "registration_key": KEY,
}


@pytest.fixture(autouse=True)
def registration_context(monkeypatch, set_current_users):
    router.signup_limiter.clear()
    set_current_users({
        "manager": {"id": "manager-id", "permissions": ["*"], "is_disabled": False},
        "staff": {"id": "staff-id", "permissions": [], "is_disabled": False},
    })
    monkeypatch.setattr(
        RegistrationTable, "read_key_hash",
        AsyncMock(return_value=hashlib.sha256(KEY.encode()).hexdigest()),
    )
    yield
    router.signup_limiter.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("user, status", [(None, 401), ("staff", 403)])
@pytest.mark.parametrize("method", ["GET", "PATCH"])
async def test_settings_routes_reject_non_managers(client, user, status, method):
    if user:
        authenticate(client, user)
    response = await client.request(
        method, "/api/registration/settings", json={"registration_key": KEY},
    )
    assert response.status_code == status


@pytest.mark.asyncio
async def test_manager_can_update_and_read_settings(client, monkeypatch):
    authenticate(client, "manager")
    write = AsyncMock()
    monkeypatch.setattr(RegistrationTable, "write_key_hash", write)
    response = await client.patch("/api/registration/settings", json={"registration_key": KEY})
    assert response.status_code == 200
    assert response.json() == {"configured": True}
    write.assert_awaited_once()
    response = await client.get("/api/registration/settings")
    assert response.json() == {"configured": True}


@pytest.mark.asyncio
async def test_signup_route_requires_valid_registration_key(client, monkeypatch):
    create = AsyncMock(return_value=UserOperate(id="new-manager"))
    monkeypatch.setattr(service, "create_manager", create)
    response = await client.post(
        "/api/registration/signup", json={**FORM, "registration_key": "wrong"},
    )
    assert response.status_code == 403
    create.assert_not_awaited()
    response = await client.post("/api/registration/signup", json=FORM)
    assert response.status_code == 200
    assert response.json() == {"id": "new-manager"}
    create.assert_awaited_once()


@pytest.mark.asyncio
async def test_signup_rate_limit_counts_successes(client, monkeypatch):
    create = AsyncMock(return_value=UserOperate(id="new-manager"))
    monkeypatch.setattr(service, "create_manager", create)
    for _ in range(10):
        response = await client.post("/api/registration/signup", json=FORM)
        assert response.status_code == 200
    response = await client.post("/api/registration/signup", json=FORM)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
    assert create.await_count == 10
    response = await client.post(
        "/api/registration/signup", json=FORM, headers={"x-real-ip": "192.0.2.2"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("field, value", [
    ("username", "  "), ("nickname", ""), ("password", "short"),
    ("registration_key", ""), ("registration_key", "a" * 129),
])
async def test_signup_invalid_fields_return_422(client, field, value):
    response = await client.post("/api/registration/signup", json={**FORM, field: value})
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["short", "a" * 129])
async def test_settings_invalid_key_returns_422(client, key):
    authenticate(client, "manager")
    response = await client.patch("/api/registration/settings", json={"registration_key": key})
    assert response.status_code == 422
