"""建立店長帳號, 由 CLI 或已驗證共用註冊碼的 registration 模組使用。

與員工建立流程分開, 避免一般的角色指派繞過店長註冊碼驗證。
"""

from sqlalchemy.exc import IntegrityError

from modules.roles.public import RoleTable
from shared.auth import passwords
from shared.db.table import is_unique_violation
from shared.http.errors import LangException

from .errors import UserError
from .model import UserTable
from .schema import SuperAdminCreate, UserOperate


async def create_super_admin(form_data: SuperAdminCreate) -> UserOperate:
    """建立擁有全部權限的店長帳號, 可重複建立。"""
    if await UserTable.find_detail_by_username(username=form_data.username):
        raise LangException(409, UserError.USERNAME_EXISTS)

    role_ids = [await RoleTable.get_super_admin_role_id()]
    password_hash = await passwords.hash_password_async(form_data.password)

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
        # 上面查過一次, 這裡只會是查完之後才被別人搶走的 username。
        raise LangException(409, UserError.USERNAME_EXISTS) from exc
    return UserOperate.model_validate(created)
