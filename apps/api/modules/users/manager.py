from sqlalchemy.exc import IntegrityError

from modules.roles.public import RoleTable
from shared.auth import passwords
from shared.db.session import release_connection
from shared.db.table import is_unique_violation
from shared.http.errors import LangException

from .errors import UserError
from .model import UserTable
from .schema import SuperAdminCreate, UserOperate


async def create_manager(form_data: SuperAdminCreate) -> UserOperate:
    """建立具有店長身分的帳號, 呼叫端須先完成 CLI 或註冊碼授權."""
    if await UserTable.find_detail_by_username(username=form_data.username):
        raise LangException(409, UserError.USERNAME_EXISTS)

    await release_connection()
    password_hash = await passwords.hash_password_async(form_data.password)
    role_ids = [await RoleTable.get_super_admin_role_id()]

    try:
        created = await UserTable.create(
            data={
                "username": form_data.username,
                "nickname": form_data.nickname,
                "password": password_hash,
                "role_ids": role_ids,
            },
        )
    except IntegrityError as exc:
        if not is_unique_violation(exc):
            raise
        # 上面查過一次, 這裡只會是查完之後才被別人搶走的 username.
        raise LangException(409, UserError.USERNAME_EXISTS) from exc
    return UserOperate.model_validate(created)

