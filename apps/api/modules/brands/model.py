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


async def find_brand_names(ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    rows = await active_session().execute(select(BrandTable.id, BrandTable.name).where(
        BrandTable.id.in_([parse_uuid(id) for id in ids]),
    ))
    return {str(id): name for id, name in rows}
