from sqlalchemy import false, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import ColumnElement

from shared.db.session import active_session
from shared.db.transaction import transaction
from shared.http.errors import LangException
from shared.time import utc_now

from .errors import BrandError
from .model import BrandTable, lock_brand
from .schema import BrandCreate, BrandInfo, BrandList, BrandUpdate


async def require_active_brand(id: str, *, existing_id: str | None = None) -> None:
    brand = await lock_brand(id)
    if not brand.is_active and id != existing_id:
        raise LangException(409, BrandError.INACTIVE)


def _usage_expression() -> ColumnElement[bool]:
    # 跟刪除時的外鍵防線一致, 包含軟刪除資料, 且不讓品牌依賴引用它的模組.
    return or_(false(), *(
        select(table).where(key.parent == BrandTable.id).exists().correlate(BrandTable)
        for table in BrandTable.metadata.tables.values()
        for key in table.foreign_keys
        if key.column is BrandTable.__table__.c.id
        and key.ondelete in (None, "RESTRICT", "NO ACTION")
    ))


async def get_brands(include_inactive: bool = False) -> BrandList:
    statement = select(BrandTable, _usage_expression()).order_by(
        BrandTable.name.asc(), BrandTable.id.asc(),
    )
    if not include_inactive:
        statement = statement.where(BrandTable.is_active.is_(True))
    rows = (await active_session().execute(statement)).all()
    return BrandList(list_data=[
        BrandInfo(**row.to_dict(), in_use=in_use) for row, in_use in rows
    ], count=len(rows))


async def create_brand(form_data: BrandCreate) -> BrandInfo:
    try:
        async with transaction():
            row = await BrandTable.create(data={"name": form_data.name, "is_active": True})
            return BrandInfo(**row, in_use=False)
    except IntegrityError as error:
        raise LangException(409, BrandError.DUPLICATE) from error


async def update_brand(id: str, form_data: BrandUpdate) -> BrandInfo:
    try:
        async with transaction():
            row = await lock_brand(id)
            row.name, row.is_active = form_data.name, form_data.is_active
            row.updated_at = utc_now()
            await active_session().flush()
            in_use = await active_session().scalar(
                select(_usage_expression()).where(BrandTable.id == row.id),
            )
            return BrandInfo(**row.to_dict(), in_use=bool(in_use))
    except IntegrityError as error:
        raise LangException(409, BrandError.DUPLICATE) from error


async def delete_brand(id: str) -> BrandInfo:
    # 外鍵 RESTRICT 是併發與後續模組引用的最後防線, 不需要品牌模組認識每一種引用者.
    async with transaction():
        row = await lock_brand(id)
        result = BrandInfo(**row.to_dict(), in_use=False)
        try:
            async with transaction():
                await active_session().delete(row)
                await active_session().flush()
            return result
        except IntegrityError:
            row = await lock_brand(id)
            row.is_active = False
            row.updated_at = utc_now()
            await active_session().flush()
            return BrandInfo(**row.to_dict(), in_use=True)
