from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from modules.exchange_rates import service
from modules.exchange_rates.model import ExchangeRateTable
from modules.exchange_rates.schema import ExchangeRateUpdate
from shared.auth.contracts import CurrentUser
from tests.modules.helpers import authenticate


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "1.1234567", "abc"])
def test_exchange_rate_validates_decimal(value):
    with pytest.raises(ValidationError):
        ExchangeRateUpdate(rate=value)
    assert ExchangeRateUpdate(rate="4.512345").rate == Decimal("4.512345")


@pytest.mark.asyncio
@pytest.mark.parametrize("user,code", [(None, 401), ("staff", 403)])
@pytest.mark.parametrize("method", ["GET", "PATCH"])
async def test_exchange_routes_reject_non_managers(client, set_current_users, user, code, method):
    set_current_users({"staff": {"id": "staff", "permissions": [], "is_disabled": False}})
    if user:
        authenticate(client, user)
    response = await client.request(method, "/api/exchange-rates/settings", json={"rate": "4.5"})
    assert response.status_code == code


@pytest.mark.asyncio
async def test_exchange_manager_can_read_and_update(client, set_current_users, monkeypatch):
    set_current_users({"manager": {"id": "manager", "permissions": ["*"], "is_disabled": False}})
    monkeypatch.setattr(ExchangeRateTable, "read_settings", AsyncMock(return_value=None))
    write = AsyncMock()
    monkeypatch.setattr(ExchangeRateTable, "write_rate", write)
    authenticate(client, "manager")
    result = await client.get("/api/exchange-rates/settings")
    assert result.status_code == 200 and result.json()["rate"] is None
    result = await client.patch("/api/exchange-rates/settings", json={"rate": "4.512345"})
    assert result.status_code == 200
    write.assert_awaited_once()
    assert write.call_args.args[0] == Decimal("4.512345")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_exchange_rate_upsert_keeps_decimal_and_actor(db):
    actor: CurrentUser = {
        "id": "22222222-2222-4222-8222-222222222222", "username": "manager",
        "auth_version": 1, "permissions": ["*"], "is_disabled": False,
    }
    assert (await service.get_settings()).rate is None
    await service.update_settings(ExchangeRateUpdate(rate="4.512345"), actor)
    result = await service.get_settings()
    assert result.rate == Decimal("4.512345")
    assert result.updated_by == actor["id"] and result.updated_at is not None
    await service.update_settings(ExchangeRateUpdate(rate="4.6"), actor)
    assert (await service.get_settings()).rate == Decimal("4.6")
