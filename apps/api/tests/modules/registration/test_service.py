import hashlib
from unittest.mock import AsyncMock

import pytest

from modules.registration import service
from modules.registration.model import RegistrationTable
from modules.registration.schema import RegistrationSettingsUpdate, SignupRequest
from modules.users.public import SuperAdminCreate, UserOperate
from shared.http.errors import LangException

KEY = "shop-manager-key"


def signup_form(**overrides):
    return SignupRequest.model_validate({
        "username": "manager", "nickname": "店長", "password": "password123",
        "registration_key": KEY, **overrides,
    })


@pytest.mark.asyncio
async def test_signup_valid_key_creates_manager(monkeypatch):
    monkeypatch.setattr(
        RegistrationTable, "read_key_hash",
        AsyncMock(return_value=hashlib.sha256(KEY.encode()).hexdigest()),
    )
    create = AsyncMock(return_value=UserOperate(id="manager-id"))
    monkeypatch.setattr(service, "create_super_admin", create)
    result = await service.signup(signup_form(role_ids=["injected"], is_disabled=True))
    assert result.id == "manager-id"
    create.assert_awaited_once_with(form_data=SuperAdminCreate(
        username="manager", nickname="店長", password="password123",
    ))


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [None, hashlib.sha256(b"other-key").hexdigest()])
async def test_signup_invalid_or_unset_key_rejects_creation(monkeypatch, stored):
    monkeypatch.setattr(RegistrationTable, "read_key_hash", AsyncMock(return_value=stored))
    create = AsyncMock()
    monkeypatch.setattr(service, "create_super_admin", create)
    with pytest.raises(LangException) as error:
        await service.signup(signup_form())
    assert error.value.status_code == 403
    create.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [None, "hash-value"])
async def test_settings_response_does_not_expose_key(monkeypatch, stored):
    monkeypatch.setattr(RegistrationTable, "read_key_hash", AsyncMock(return_value=stored))
    result = await service.get_settings()
    assert result.model_dump() == {"configured": stored is not None}


@pytest.mark.asyncio
async def test_update_settings_stores_only_hash(monkeypatch):
    write = AsyncMock()
    monkeypatch.setattr(RegistrationTable, "write_key_hash", write)
    result = await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    write.assert_awaited_once_with(hashlib.sha256(KEY.encode()).hexdigest())
    assert result.model_dump() == {"configured": True}
