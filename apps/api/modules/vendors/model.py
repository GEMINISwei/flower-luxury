from sqlalchemy import Index, func, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable, parse_uuid
from shared.http.errors import ensure_found

from .rules import VendorError


class VendorTable(BaseTable):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column()
    note: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    has_quotes: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("uq_vendors_name_folded", func.lower(name), unique=True),
    )


async def lock_vendor(id: str) -> VendorTable:
    row = await active_session().scalar(select(VendorTable).where(
        VendorTable.id == parse_uuid(id),
    ).with_for_update().execution_options(populate_existing=True))
    return ensure_found(row, VendorError.NOT_FOUND)
