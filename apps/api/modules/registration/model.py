import uuid

from sqlalchemy import CheckConstraint, String, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable
from shared.time import utc_now


class RegistrationTable(BaseTable):
    __tablename__ = "registration_settings"

    code: Mapped[str] = mapped_column(String, unique=True)
    key_hash: Mapped[str]

    __table_args__ = (
        CheckConstraint("code = 'signup'", name="registration_settings_singleton"),
    )

    @classmethod
    async def read_key_hash(cls) -> str | None:
        return await active_session().scalar(select(cls.key_hash).where(cls.code == "signup"))

    @classmethod
    async def write_key_hash(cls, key_hash: str) -> None:
        # 固定唯一鍵的 upsert 讓首次設定與併發更換都只有一份設定, 不靠先查後建。
        statement = insert(cls).values(
            id=uuid.uuid4(), code="signup", key_hash=key_hash, created_at=utc_now(),
        )
        await active_session().execute(statement.on_conflict_do_update(
            index_elements=[cls.code],
            set_={"key_hash": key_hash, "updated_at": utc_now()},
        ))
