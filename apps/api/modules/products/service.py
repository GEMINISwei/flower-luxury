import secrets
import string
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select

from modules.brands.public import require_active_brand
from shared.auth.contracts import CurrentUser
from shared.db.query import ilike_contains
from shared.db.session import active_session
from shared.db.table import Condition, parse_uuid
from shared.db.transaction import transaction
from shared.http.errors import ensure_found
from shared.time import utc_now

from .model import ProductHistoryTable, ProductSaleTable, ProductTable, lock_product
from .rules import ProductError, ensure_transition
from .schema import (
    ProductCreate,
    ProductInfo,
    ProductList,
    StatusChange,
    StatusHistoryInfo,
    StatusHistoryList,
    StatusReturn,
)


def product_fields(form: ProductCreate) -> dict[str, Any]:
    return {"name": form.name, "brand_id": parse_uuid(form.brand_id),
            "category": form.category, "model_name": form.model_name,
            "serial_number": form.serial_number, "color": form.color, "year": form.year,
            "cost_price": form.cost_price, "internal_note": form.internal_note}


def generate_sku() -> str:
    date = utc_now().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Taipei"))
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return f"LX{date:%Y%m%d}{suffix}"


async def record_status(row: ProductTable, source: str | None, actor: CurrentUser,
                        action: str, reason: str | None) -> None:
    await ProductHistoryTable.create(data={
        "product_id": row.id, "from_status": source, "to_status": row.status,
        "action": action, "reason": reason, "changed_by": actor["id"],
        "operator_name": actor["username"], "changed_at": utc_now(),
    })


async def create_product(form_data: ProductCreate, actor: CurrentUser) -> ProductInfo:
    async with transaction():
        await require_active_brand(form_data.brand_id)
        row = ProductTable(**product_fields(form_data), sku=generate_sku(),
                           status="not_acquired", created_by=actor["id"])
        active_session().add(row)
        await active_session().flush()
        await record_status(row, None, actor, "create", None)
        return await get_product(str(row.id))


async def get_product(id: str) -> ProductInfo:
    result = ensure_found(await ProductTable.find_detail_by_id(id), ProductError.NOT_FOUND)
    ensure_found(result if result["deleted_at"] is None else None, ProductError.NOT_FOUND)
    return ProductInfo.model_validate(result)


async def update_product(id: str, form_data: ProductCreate, actor: CurrentUser) -> ProductInfo:
    async with transaction():
        row = await lock_product(id)
        await require_active_brand(form_data.brand_id, existing_id=str(row.brand_id))
        for field, value in product_fields(form_data).items():
            setattr(row, field, value)
        row.updated_by, row.updated_at = actor["id"], utc_now()
        await active_session().flush()
        # 品牌可能在同一個 session 變更, 避免關聯快取顯示舊名稱.
        active_session().expire(row, ["brand_record"])
        return await get_product(id)


async def delete_product(id: str, actor: CurrentUser) -> ProductInfo:
    async with transaction():
        row = await lock_product(id)
        result = await get_product(id)
        row.deleted_at, row.updated_at, row.updated_by = utc_now(), utc_now(), actor["id"]
        await active_session().flush()
        return result


async def apply_status(id: str, to_status: str, reason: str | None,
                       actor: CurrentUser, *, returning: bool) -> ProductInfo:
    async with transaction():
        row = await lock_product(id, editable=not returning)
        ensure_transition(row.status, to_status, returning=returning)
        source = row.status
        if returning and source == "sold":
            sale = await active_session().scalar(select(ProductSaleTable).where(
                ProductSaleTable.product_id == row.id, ProductSaleTable.is_current.is_(True),
            ))
            if sale is not None:
                sale.is_current, sale.returned_at = False, utc_now()
                sale.returned_by, sale.return_reason = actor["id"], reason
        row.status, row.updated_at, row.updated_by = to_status, utc_now(), actor["id"]
        await record_status(row, source, actor, "return" if returning else "change", reason)
        await active_session().flush()
        return await get_product(id)


async def change_status(id: str, form_data: StatusChange, actor: CurrentUser) -> ProductInfo:
    return await apply_status(id, form_data.to_status, form_data.reason, actor, returning=False)


async def return_status(id: str, form_data: StatusReturn, actor: CurrentUser) -> ProductInfo:
    return await apply_status(id, form_data.to_status, form_data.reason, actor, returning=True)


async def get_history(id: str) -> StatusHistoryList:
    await get_product(id)
    rows = (await active_session().scalars(select(ProductHistoryTable).where(
        ProductHistoryTable.product_id == parse_uuid(id),
    ).order_by(ProductHistoryTable.changed_at.desc(), ProductHistoryTable.id.desc()))).all()
    return StatusHistoryList(list_data=[StatusHistoryInfo.model_validate(row.to_dict())
                                       for row in rows], count=len(rows))


def product_filters(keyword: str | None, **filters: Any) -> list[Condition]:
    where: list[Condition] = [ProductTable.deleted_at.is_(None)]
    if keyword:
        where.append(or_(ilike_contains(ProductTable.name, keyword),
                         ilike_contains(ProductTable.sku, keyword),
                         ilike_contains(ProductTable.serial_number, keyword)))
    for field, value in filters.items():
        if value is not None and value != "":
            column = getattr(ProductTable, field)
            where.append(ilike_contains(column, value) if field == "color" else column == value)
    return where


async def get_product_list(
    limit: int, cursor: str | None = None, direction: Literal["next", "prev"] = "next",
    keyword: str | None = None, brand_id: str | None = None, category: str | None = None,
    status: str | None = None, color: str | None = None, year: int | None = None,
) -> ProductList:
    return ProductList.model_validate(await ProductTable.get_page(
        limit=limit, cursor=cursor, direction=direction,
        where=product_filters(keyword, brand_id=parse_uuid(brand_id) if brand_id else None,
                              category=category, status=status, color=color, year=year),
    ))
