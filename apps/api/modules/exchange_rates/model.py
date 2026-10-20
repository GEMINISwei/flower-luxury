import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, mapped_column

from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.db.table import BaseTable
from shared.time import utc_now


class ExchangeRateTable(BaseTable):
    __tablename__ = "exchange_rate_settings"

    currency: Mapped[str] = mapped_column(unique=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(16, 6))
    updated_by: Mapped[str]
    operator_name: Mapped[str]

    __table_args__ = (
        CheckConstraint("currency = 'CNY'", name="exchange_rate_cny_only"),
        CheckConstraint("rate > 0", name="exchange_rate_positive"),
    )

    @classmethod
    async def read_settings(cls) -> dict | None:
        row = await active_session().scalar(select(cls).where(cls.currency == "CNY"))
        return row.to_dict() if row is not None else None

    @classmethod
    async def write_rate(cls, rate: Decimal, actor: CurrentUser) -> None:
        values = {"rate": rate, "updated_by": actor["id"],
                  "operator_name": actor["username"], "updated_at": utc_now()}
        statement = insert(cls).values(id=uuid.uuid4(), currency="CNY", created_at=utc_now(),
                                       **values)
        await active_session().execute(statement.on_conflict_do_update(
            index_elements=[cls.currency], set_=values,
        ))
