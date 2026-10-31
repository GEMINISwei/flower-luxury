from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from shared.db.session import active_session
from shared.db.table import is_unique_violation
from shared.db.transaction import transaction
from shared.http.errors import LangException
from shared.time import utc_now

from .model import VendorTable, lock_vendor
from .rules import VendorError
from .schema import VendorCreate, VendorInfo, VendorList, VendorUpdate


async def get_vendors(include_inactive: bool = False) -> VendorList:
    statement = select(VendorTable).order_by(VendorTable.name.asc(), VendorTable.id.asc())
    if not include_inactive:
        statement = statement.where(VendorTable.is_active.is_(True))
    rows = (await active_session().scalars(statement)).all()
    return VendorList(list_data=[VendorInfo.model_validate(row.to_dict()) for row in rows],
                      count=len(rows))


async def create_vendor(form_data: VendorCreate) -> VendorInfo:
    try:
        async with transaction():
            row = await VendorTable.create(data={**form_data.model_dump(), "is_active": True})
            return VendorInfo.model_validate(row)
    except IntegrityError as error:
        if not is_unique_violation(error):
            raise
        raise LangException(409, VendorError.DUPLICATE) from error


async def update_vendor(id: str, form_data: VendorUpdate) -> VendorInfo:
    try:
        async with transaction():
            row = await lock_vendor(id)
            for field, value in form_data.model_dump().items():
                setattr(row, field, value)
            row.updated_at = utc_now()
            await active_session().flush()
            return VendorInfo.model_validate(row.to_dict())
    except IntegrityError as error:
        if not is_unique_violation(error):
            raise
        raise LangException(409, VendorError.DUPLICATE) from error


async def delete_vendor(id: str) -> VendorInfo:
    async with transaction():
        row = await lock_vendor(id)
        result = VendorInfo.model_validate(row.to_dict())
        # 曾有正式詢價的廠商保留識別, 即使最後一筆未成交詢價已刪除.
        if row.has_quotes:
            row.is_active, row.updated_at = False, utc_now()
            await active_session().flush()
            return VendorInfo.model_validate(row.to_dict())
        await active_session().delete(row)
        await active_session().flush()
        return result
