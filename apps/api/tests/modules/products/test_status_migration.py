from pathlib import Path

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from modules.brands import service as brands
from modules.brands.schema import BrandCreate
from modules.products import service
from modules.products.model import ProductHistoryTable
from modules.products.schema import ProductCreate
from shared.auth.contracts import CurrentUser
from shared.db.session import active_session
from shared.time import utc_now

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
ACTOR: CurrentUser = {
    "id": "22222222-2222-4222-8222-222222222222", "username": "staff",
    "auth_version": 1, "permissions": [], "is_disabled": False,
}


def run_migration(connection, direction):
    api = Path(__file__).resolve().parents[3]
    scripts = ScriptDirectory.from_config(Config(str(api / "alembic.ini")))
    revision = scripts.get_revision("29e7062acabd")
    assert revision is not None
    migration = revision.module
    with Operations.context(MigrationContext.configure(connection)):
        getattr(migration, direction)()


async def test_two_status_migration_preserves_history_and_rejects_in_stock(db):
    brand = await brands.create_brand(BrandCreate(name="CHANEL"))
    product = await service.create_product(ProductCreate(
        name="手袋", brand_id=brand.id, category="包包", cost_price=0,
    ), ACTOR)
    session = active_session()
    connection = await session.connection()
    await connection.run_sync(run_migration, "downgrade")
    await session.execute(text("UPDATE products SET status = 'in_stock' WHERE id = :id"),
                          {"id": product.id})
    moment = utc_now()
    for source, target, reason in [("not_acquired", "in_stock", "舊庫存"),
                                   ("in_stock", "not_acquired", "舊退回")]:
        await ProductHistoryTable.create(data={
            "product_id": product.id, "from_status": source, "to_status": target,
            "action": "change", "reason": reason, "changed_by": ACTOR["id"],
            "operator_name": "staff", "changed_at": moment,
        })
    await session.flush()
    await connection.run_sync(run_migration, "upgrade")
    session.expire_all()
    assert (await service.get_product(product.id)).status == "not_acquired"
    histories = (await service.get_history(product.id)).list_data
    assert len(histories) == 3
    assert all(row.to_status == "not_acquired" for row in histories)
    assert {row.from_status for row in histories} == {None, "not_acquired"}
    assert {row.reason for row in histories} == {None, "舊庫存", "舊退回"}
    assert all(row.operator_name == "staff" and row.changed_by == ACTOR["id"] for row in histories)
    assert all(row.changed_at.replace(tzinfo=None) == moment for row in histories if row.reason)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(text("UPDATE products SET status = 'in_stock' WHERE id = :id"),
                                  {"id": product.id})
