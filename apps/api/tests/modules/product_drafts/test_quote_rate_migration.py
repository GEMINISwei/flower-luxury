import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text

from shared.db.session import active_session

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def quote_rate_migration():
    path = next(Path("migrations/versions").glob("*per_quote_rates*.py"))
    spec = importlib.util.spec_from_file_location("quote_rate_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


async def test_quote_rate_migration_preserves_legacy_data(db, quote_rate_migration):
    migration = quote_rate_migration
    session = active_session()
    await session.execute(text("CREATE TEMP TABLE vendors (id uuid, country text) ON COMMIT DROP"))
    await session.execute(text(
        "CREATE TEMP TABLE exchange_rate_settings (rate numeric) ON COMMIT DROP"))
    await session.execute(text(
        "CREATE TEMP TABLE product_drafts (id uuid, quotes jsonb) ON COMMIT DROP"))
    await session.execute(text("INSERT INTO vendors VALUES "
        "('11111111-1111-4111-8111-111111111111', 'TW'), "
        "('22222222-2222-4222-8222-222222222222', 'CN')"))
    await session.execute(text("INSERT INTO exchange_rate_settings VALUES (4.512345)"))
    await session.execute(text("""INSERT INTO product_drafts VALUES (
        '33333333-3333-4333-8333-333333333333',
        '[{"vendor_id":"11111111-1111-4111-8111-111111111111","original_amount":"1200"},
          {"vendor_id":"22222222-2222-4222-8222-222222222222","original_amount":"100.25"}]'
    )"""))
    connection = await session.connection()
    await connection.run_sync(migration.backfill_draft_quote_rates)
    quotes = (await session.execute(text("SELECT quotes FROM product_drafts"))).scalar_one()
    assert str(quotes[0]["exchange_rate"]) == "1"
    assert str(quotes[1]["exchange_rate"]) == "4.512345"
    assert [row["original_amount"] for row in quotes] == ["1200", "100.25"]
    await session.execute(text("TRUNCATE exchange_rate_settings"))
    await session.execute(text("UPDATE product_drafts SET quotes = "
        "jsonb_set(quotes, '{1,exchange_rate}', 'null'::jsonb)"))
    with pytest.raises(RuntimeError, match="匯率"):
        await connection.run_sync(migration.backfill_draft_quote_rates)
