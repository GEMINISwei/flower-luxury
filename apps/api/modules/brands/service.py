from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from shared.db.session import active_session
from shared.db.table import parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import BaseError, LangException, LangText, ensure_found
from shared.time import utc_now

from .model import BrandTable
from .schema import BrandCreate, BrandInfo, BrandList, BrandUpdate


class BrandError(BaseError):
    NOT_FOUND = LangText(zh="品牌不存在", en="Brand not found")
    DUPLICATE = LangText(zh="品牌名稱重複", en="Brand name already exists")
    INACTIVE = LangText(
        zh="品牌已停用，請選擇其他品牌", en="Brand is inactive; choose another brand",
    )


async def lock_brand(id: str) -> BrandTable:
    row = await active_session().scalar(select(BrandTable).where(
        BrandTable.id == parse_uuid(id),
    ).with_for_update().execution_options(populate_existing=True))
    return ensure_found(row, BrandError.NOT_FOUND)


async def require_active_brand(id: str, *, existing_id: str | None = None) -> None:
    brand = await lock_brand(id)
    if not brand.is_active and id != existing_id:
        raise LangException(409, BrandError.INACTIVE)


async def get_brands(include_inactive: bool = False) -> BrandList:
    statement = select(BrandTable).order_by(BrandTable.name.asc(), BrandTable.id.asc())
    if not include_inactive:
        statement = statement.where(BrandTable.is_active.is_(True))
    rows = (await active_session().scalars(statement)).all()
    return BrandList(list_data=[BrandInfo.model_validate(row.to_dict()) for row in rows],
                     count=len(rows))


async def create_brand(form_data: BrandCreate) -> BrandInfo:
    try:
        async with transaction():
            row = await BrandTable.create(data={"name": form_data.name, "is_active": True})
            return BrandInfo.model_validate(row)
    except IntegrityError as error:
        raise LangException(409, BrandError.DUPLICATE) from error


async def update_brand(id: str, form_data: BrandUpdate) -> BrandInfo:
    try:
        async with transaction():
            row = await lock_brand(id)
            row.name, row.is_active = form_data.name, form_data.is_active
            row.updated_at = utc_now()
            await active_session().flush()
            return BrandInfo.model_validate(row.to_dict())
    except IntegrityError as error:
        raise LangException(409, BrandError.DUPLICATE) from error


async def delete_brand(id: str) -> BrandInfo:
    # 外鍵 RESTRICT 是併發與後續模組引用的最後防線, 不需要品牌模組認識每一種引用者.
    async with transaction():
        row = await lock_brand(id)
        result = BrandInfo.model_validate(row.to_dict())
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
            return BrandInfo.model_validate(row.to_dict())
