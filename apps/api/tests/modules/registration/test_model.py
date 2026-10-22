import hashlib

import pytest
from sqlalchemy import func, select

from modules.registration import service
from modules.registration.model import RegistrationTable
from modules.registration.schema import RegistrationSettingsUpdate, SignupRequest
from modules.users.public import UserTable
from shared.auth.contracts import AppEnvProtocol
from shared.db.session import active_session
from shared.http.errors import LangException

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
KEY = "first-manager-key"


def form(username="manager", key=KEY):
    return SignupRequest(
        username=username, nickname="店長", password="password123", registration_key=key,
    )


async def test_rotation_persists_hash_and_invalidates_old_key(db):
    assert (await service.get_settings()).configured is False
    await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    assert await RegistrationTable.read_key_hash() == hashlib.sha256(KEY.encode()).hexdigest()
    await service.update_settings(RegistrationSettingsUpdate(registration_key="second-manager-key"))
    assert await active_session().scalar(select(func.count()).select_from(RegistrationTable)) == 1
    with pytest.raises(LangException) as error:
        await service.signup(form())
    assert error.value.status_code == 403
    await service.signup(form(key="second-manager-key"))


async def test_signup_creates_active_manager_who_can_login(db, mock_app_env):
    from app.server import app
    from modules.users.account import login_user
    from modules.users.schema import UserLogin

    await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    created = await service.signup(form())
    detail = await UserTable.find_detail_by_id(created.id)
    assert detail is not None
    assert detail["permissions"] == ["*"]
    assert detail["is_disabled"] is False
    assert detail["role_ids"]
    row = await UserTable.find_by_id(created.id)
    assert row is not None and row.password != "password123"
    env: AppEnvProtocol = app.state.env
    token = await login_user(UserLogin(username="manager", password="password123"), env)
    assert token.access_token


async def test_signup_duplicate_username_returns_409(db):
    await service.update_settings(RegistrationSettingsUpdate(registration_key=KEY))
    await service.signup(form())
    with pytest.raises(LangException) as error:
        await service.signup(form())
    assert error.value.status_code == 409
    assert await active_session().scalar(select(func.count()).select_from(UserTable)) == 1
