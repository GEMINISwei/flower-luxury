import importlib.util
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from shared.db.session import active_session
from tests.modules.product_drafts.helpers import BASE

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
def auto_grouping_migration():
    path = next(Path("migrations/versions").glob("*auto_grouping*.py"))
    spec = importlib.util.spec_from_file_location("auto_grouping_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


async def legacy_tables():
    session = active_session()
    await session.execute(text("""CREATE TEMP TABLE product_drafts (
        id uuid PRIMARY KEY, source_key text, received_at timestamp, collecting boolean,
        collection_id uuid, finalized_at timestamp, version integer DEFAULT 1,
        fields jsonb DEFAULT '{}', manual_fields jsonb DEFAULT '[]', quotes jsonb DEFAULT '[]',
        prefill_revision integer DEFAULT 0, prefill_status text DEFAULT 'idle',
        has_text boolean DEFAULT false, main_photo_id uuid, created_at timestamp,
        updated_at timestamp) ON COMMIT DROP"""))
    await session.execute(text("""CREATE TEMP TABLE product_draft_messages (
        id uuid PRIMARY KEY, source_key text, draft_id uuid, kind text, text text,
        occurred_at timestamp, sequence integer, pending boolean DEFAULT false) ON COMMIT DROP"""))
    await session.execute(text("""CREATE TEMP TABLE product_draft_photos (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), message_id uuid, draft_id uuid)
        ON COMMIT DROP"""))
    await session.execute(text("""CREATE TEMP TABLE product_draft_intervals (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_key text, draft_key text,
        started_at timestamp, first_text_at timestamp, ended_at timestamp,
        created_at timestamp DEFAULT now(), updated_at timestamp) ON COMMIT DROP"""))


async def add_message(id, kind, second, draft=None, body=None):
    session = active_session()
    await session.execute(text(
        "INSERT INTO product_draft_messages (id, source_key, draft_id, kind, text, occurred_at, "
        "sequence) VALUES (CAST(:id AS uuid), 's', CAST(:draft AS uuid), :kind, :body, :at, :seq)"),
        {"id": id, "draft": draft, "kind": kind, "body": body,
         "at": BASE + timedelta(seconds=second), "seq": second})
    if kind == "image":
        await session.execute(text("INSERT INTO product_draft_photos (message_id, draft_id) "
            "VALUES (CAST(:id AS uuid), CAST(:draft AS uuid))"), {"id": id, "draft": draft})


def message_id(number):
    return f"00000000-0000-4000-8000-{number:012d}"


async def test_migration_converts_manual_rounds_to_auto_grouping(db, auto_grouping_migration):
    session = active_session()
    await legacy_tables()
    await session.execute(text(
        "INSERT INTO product_drafts (id, source_key, received_at, collecting, collection_id, "
        "finalized_at, fields, prefill_status, prefill_revision) VALUES "
        "(CAST(:a AS uuid), 's', :t1, false, gen_random_uuid(), NULL, '{\"name\":\"人工\"}', "
        "'idle', 0), "
        "(CAST(:b AS uuid), 's', :t5, false, gen_random_uuid(), :t5, '{}', 'ready', 1)"),
        {"a": A, "b": B, "t1": BASE + timedelta(seconds=1), "t5": BASE + timedelta(seconds=5)})
    await add_message(message_id(1), "image", 1, A)
    await add_message(message_id(2), "text", 2, A, "A 說明")
    await add_message(message_id(5), "image", 5, B)
    await add_message(message_id(6), "text", 6, B, "B 說明")
    await add_message(message_id(3), "text", 3, body="異常文字")
    await add_message(message_id(4), "image", 4)
    await add_message(message_id(8), "image", 8)
    await add_message(message_id(9), "text", 9, body="C 說明")
    await add_message(message_id(10), "image", 10)
    await add_message(message_id(20), "text", 0, body="無歸屬")
    connection = await session.connection()
    await connection.run_sync(auto_grouping_migration.convert_to_auto_grouping)

    rows = {str(row.id): row for row in await session.execute(text(
        "SELECT id, draft_id, pending FROM product_draft_messages"))}
    assert message_id(20) not in rows
    assert (str(rows[message_id(3)].draft_id), rows[message_id(3)].pending) == (A, True)
    assert (str(rows[message_id(4)].draft_id), rows[message_id(4)].pending) == (A, True)
    pending_photo = (await session.execute(text(
        "SELECT draft_id FROM product_draft_photos WHERE message_id = CAST(:id AS uuid)"),
        {"id": message_id(4)})).scalar_one()
    assert pending_photo is None
    c, d = str(rows[message_id(8)].draft_id), str(rows[message_id(10)].draft_id)
    assert str(rows[message_id(9)].draft_id) == c and c not in {A, B} and d not in {A, B, c}
    assert not any(rows[message_id(n)].pending for n in (1, 2, 5, 6, 8, 9, 10))
    drafts = {str(row.id): row for row in await session.execute(text(
        "SELECT id, collecting, fields, prefill_status FROM product_drafts"))}
    assert not drafts[A].collecting and drafts[A].fields == {"name": "人工"}
    assert drafts[B].prefill_status == "ready"
    assert not drafts[c].collecting and drafts[d].collecting
    intervals = {row.draft_key: row for row in await session.execute(text(
        "SELECT draft_key, started_at, first_text_at, ended_at FROM product_draft_intervals"))}
    assert set(intervals) == {A, B, c, d}
    assert intervals[A].ended_at == BASE + timedelta(seconds=5)
    assert intervals[c].first_text_at == BASE + timedelta(seconds=9)
    assert intervals[d].ended_at is None
