import hashlib
import hmac

from modules.users.public import SuperAdminCreate, UserOperate, create_super_admin
from shared.http.errors import BaseError, LangException, LangText

from .model import RegistrationTable
from .schema import RegistrationSettings, RegistrationSettingsUpdate, SignupRequest


class RegistrationError(BaseError):
    INVALID_KEY = LangText(
        zh="註冊碼錯誤或尚未設定，請聯絡店長",
        en="Registration code is incorrect or not configured. Please contact a store manager.",
    )


async def get_settings() -> RegistrationSettings:
    return RegistrationSettings(configured=await RegistrationTable.read_key_hash() is not None)


async def update_settings(form_data: RegistrationSettingsUpdate) -> RegistrationSettings:
    key_hash = hashlib.sha256(form_data.registration_key.encode()).hexdigest()
    await RegistrationTable.write_key_hash(key_hash)
    return RegistrationSettings(configured=True)


async def signup(form_data: SignupRequest) -> UserOperate:
    stored = await RegistrationTable.read_key_hash()
    candidate = hashlib.sha256(form_data.registration_key.encode()).hexdigest()
    # 未設定時也走相同比對, 對外統一回覆, 不提供設定狀態的公開探測入口。
    matched = hmac.compare_digest(candidate, stored or "0" * 64)
    if stored is None or not matched:
        raise LangException(403, RegistrationError.INVALID_KEY)
    return await create_super_admin(form_data=SuperAdminCreate(
        username=form_data.username, nickname=form_data.nickname, password=form_data.password,
    ))
