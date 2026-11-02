import importlib.util
from datetime import timedelta
from pathlib import Path

import pytest

from modules.product_drafts import collection, model, rounds, service
from shared.db.session import active_session
from tests.modules.product_drafts.helpers import BASE, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def collection_migration():
    path = next(Path("migrations/versions").glob("*manual_collection_rounds*.py"))
    spec = importlib.util.spec_from_file_location("manual_collection_migration", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


async def test_migration_preserves_reviewed_input_and_adopts_unfinished_receipts(
    db, collection_migration,
):
    closed = await collection.ingest_message(incoming(source="legacy-closed"))
    row = await model.get_draft_row(closed.draft_id)
    assert row is not None
    row.collecting, row.fields, row.prefill_revision, row.prefill_status = (
        False, {"name": "人工名稱"}, 1, "ready")
    opened = await collection.ingest_message(incoming(source="legacy-open"))
    stream = await model.stream_for("legacy-buffer")
    stream.buffer_until = BASE + timedelta(minutes=3)
    message = model.MessageTable(source_key="legacy-buffer", external_id="legacy-raw", kind="text",
        text="尚未分組原文", occurred_at=BASE, sequence=1)
    active_session().add(message)
    await active_session().flush()
    active_session().add(model.BufferedEventTable(source_key="legacy-buffer", kind="message",
        occurred_at=BASE, message_id=message.id, status="pending"))
    await active_session().flush()
    connection = await active_session().connection()
    await connection.run_sync(collection_migration.adopt_collection_state)
    active_session().expire_all()
    kept = await service.get_draft(closed.draft_id)
    assert kept.finalized and kept.fields.name == "人工名稱" and kept.prefill_status == "ready"
    assert kept.prefill_revision == 1
    unfinished = await service.get_draft(opened.draft_id)
    assert unfinished.requires_finalization and unfinished.prefill_revision == 0
    current = await rounds.current_collection("legacy-buffer")
    assert current.message_count == 1
    stored = await model.message_by_external_id("legacy-buffer", "legacy-raw")
    assert stored is not None and stored.text == "尚未分組原文" and stored.collection_id is not None
