import hashlib

import pytest
from sqlalchemy import func, select

from modules.registration import service
from modules.registration.model import RegistrationTable
from modules.registration.schema import RegistrationSettingsUpdate, SignupRequest
from modules.users.account import login_user
from modules.users.model import UserTable
from modules.users.schema import UserLogin
from shared.db.session import active_session, session_scope
from shared.http.errors import LangException

KEY = "first-manager-key"


def form(username="manager", key=KEY):
    return SignupRequest(
        username=username, nickname="店長", password="password123", registration_key=key,
    )


def test_registration_schema_preserves_legacy_columns():
    table = RegistrationTable.__table__
    assert table.name == "registration_settings"
    assert set(table.columns.keys()) == {"id", "created_at", "updated_at", "code", "key_hash"}
    assert table.c.code.unique is True
    assert table.c.code.nullable is False
    assert table.c.key_hash.nullable is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rotation_persists_hash_and_invalidates_old_key(db):
    async with session_scope():
        assert (await service.get_settings()).configured is False
        await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    async with session_scope():
        assert await RegistrationTable.read_key_hash() == hashlib.sha256(KEY.encode()).hexdigest()
        await service.update_settings(RegistrationSettingsUpdate(
            registration_key="second-manager-key",
        ))
    async with session_scope():
        count = await active_session().scalar(select(func.count()).select_from(RegistrationTable))
        assert count == 1
    async with session_scope():
        with pytest.raises(LangException) as error:
            await service.signup(form())
        assert error.value.status_code == 403
    async with session_scope():
        await service.signup(form(key="second-manager-key"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_signup_creates_active_manager_who_can_login(db, mock_app_env):
    from app.server import app

    async with session_scope():
        await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    async with session_scope():
        created = await service.signup(form())
    async with session_scope():
        detail = await UserTable.find_detail_by_id(created.id)
        assert detail is not None
        assert detail["permissions"] == ["*"]
        assert detail["is_disabled"] is False
        assert detail["role_ids"]
        row = await UserTable.find_by_id(created.id)
        assert row is not None and row.password != "password123"
    async with session_scope():
        token = await login_user(
            UserLogin(username="manager", password="password123"), app.state.env,
        )
        assert token.access_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_signup_duplicate_username_returns_409(db):
    async with session_scope():
        await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    async with session_scope():
        await service.signup(form())
    async with session_scope():
        with pytest.raises(LangException) as error:
            await service.signup(form())
        assert error.value.status_code == 409
    async with session_scope():
        assert await active_session().scalar(select(func.count()).select_from(UserTable)) == 1
