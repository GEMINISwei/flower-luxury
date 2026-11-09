from sqlalchemy import Index, func, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import active_session
from shared.db.table import BaseTable, parse_uuid
from shared.http.errors import ensure_found
from shared.time import utc_now

from .rules import VendorError
from .schema import VendorInfo


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


async def locked_vendor_info(id: str) -> VendorInfo:
    return VendorInfo.model_validate((await lock_vendor(id)).to_dict())


async def mark_vendor_quoted(id: str) -> None:
    row = await lock_vendor(id)
    row.has_quotes, row.updated_at = True, utc_now()
    await active_session().flush()


async def find_vendor_names(ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    rows = await active_session().execute(select(VendorTable.id, VendorTable.name).where(
        VendorTable.id.in_([parse_uuid(id) for id in ids]),
    ))
    return {str(id): name for id, name in rows}
