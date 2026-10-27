from sqlalchemy import Index, func, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable, parse_uuid
from shared.http.errors import ensure_found

from .errors import BrandError


class BrandTable(BaseTable):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (Index("uq_brands_name_folded", func.lower(name), unique=True),)


async def lock_brand(id: str) -> BrandTable:
    row = await active_session().scalar(select(BrandTable).where(
        BrandTable.id == parse_uuid(id),
    ).with_for_update().execution_options(populate_existing=True))
    return ensure_found(row, BrandError.NOT_FOUND)
