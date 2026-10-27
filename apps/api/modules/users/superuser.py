"""CLI 專用的店長建立與全員 Session 撤銷入口."""

from .manager import create_manager
from .model import UserTable
from .schema import SessionRevocation, SuperAdminCreate, UserOperate


async def create_super_admin(form_data: SuperAdminCreate) -> UserOperate:
    """由握有主機 shell 的維運人員建立店長, 可重複執行."""
    return await create_manager(form_data)


async def revoke_all_sessions() -> SessionRevocation:
    """讓所有使用者重新登入, 金鑰外洩時仍須更換 JWT_SECRET_KEY."""
    return SessionRevocation(affected=await UserTable.revoke_all_sessions())
