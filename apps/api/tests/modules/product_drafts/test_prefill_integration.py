import json
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from modules.product_drafts import (
    batches,
    collection,
    draft_quotes,
    messages,
    model,
    prefill,
    prefill_settings,
    service,
)
from modules.product_drafts.prefill_schema import (
    PrefillContent,
    PrefillResult,
    PrefillSettingsUpdate,
)
from modules.product_drafts.quote_schema import DraftQuoteUpdate
from modules.product_drafts.schema import DraftFields, DraftUpdate, MessageMove
from modules.vendors.public import VendorTable
from shared.db.session import active_session
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import ACTOR, BASE, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def worker_connection(monkeypatch):
    # 測試沿用 fixture 的未提交交易, 不歸還其中的連線.
    monkeypatch.setattr(prefill, "release_connection", AsyncMock())
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def job(id, revision):
    return Job(id=uuid.uuid4(), task_name="product_drafts.prefill", attempts=1,
               payload={"draft_id": id, "revision": revision})


def output(**fields):
    return PrefillContent(content=PrefillResult(**fields).model_dump_json())


async def draft_with_text(*, close=True):
    first = await collection.ingest_message(incoming())
    await collection.ingest_message(incoming("text", text="手袋 成本3000", second=1))
    if close:
        await collection.ingest_message(incoming(second=3))
    return await service.get_draft(first.draft_id)


async def test_prefill_schedules_once_when_collection_closes(db):
    draft = await draft_with_text(close=False)
    await collection.ingest_message(incoming("text", text="黑色", second=2))
    draft = await service.get_draft(draft.id)
    assert draft.collecting and draft.prefill_revision == 0 and draft.prefill_status == "idle"
    assert not list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill")))
    await collection.ingest_message(incoming(second=3))
    draft = await service.get_draft(draft.id)
    assert not draft.collecting and draft.prefill_status == "queued" and draft.prefill_revision == 1
    jobs = list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill")))
    assert len(jobs) == 1 and jobs[0].payload["draft_id"] == draft.id


async def test_batch_closure_schedules_prefill_once(db):
    from datetime import timedelta

    await batches.control_collection("batch", "start", BASE)
    first = await batches.ingest_batch_message(incoming(source="batch", second=1))
    await batches.ingest_batch_message(incoming("text", source="batch", second=2, text="A 100"))
    second = await batches.ingest_batch_message(incoming(source="batch", second=3))
    assert (await service.get_draft(first.draft_id)).prefill_status == "queued"
    assert (await service.get_draft(second.draft_id)).prefill_revision == 0
    await batches.control_collection("batch", "end", BASE + timedelta(seconds=4))
    await batches.finish_collection("batch", BASE + timedelta(seconds=5))
    assert (await service.get_draft(second.draft_id)).prefill_revision == 1
    jobs = list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill")))
    assert len(jobs) == 2


async def test_prefill_failure_is_final_and_preserves_fields(db, monkeypatch):
    draft = await draft_with_text()
    draft = await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(name="人工名稱")), ACTOR)
    generate = AsyncMock(side_effect=ValueError("invalid"))
    monkeypatch.setattr(prefill, "generate_prefill", generate)
    queued = job(draft.id, draft.prefill_revision)
    await prefill.run_prefill(queued)
    failed = await service.get_draft(draft.id)
    assert failed.prefill_status == "failed" and failed.fields.name == "人工名稱"
    await prefill.run_prefill(queued)
    generate.assert_awaited_once()


async def test_text_changes_do_not_reschedule_prefill(db):
    draft = await draft_with_text()
    target = await model.current_draft("group-a")
    assert target is not None
    text = next(item for item in draft.messages if item.kind == "text")
    moved = await messages.move_message(text.id, MessageMove(target_draft_id=str(target.id),
        target_version=target.version, source_version=draft.version), ACTOR)
    assert moved.prefill_revision == 0
    assert (await service.get_draft(draft.id)).prefill_revision == 1
    await messages.withdraw_message("group-a", text.external_id)
    assert (await service.get_draft(str(target.id))).prefill_revision == 0


async def test_prefill_uses_initial_settings_and_applies_once(db, monkeypatch):
    draft = await draft_with_text()
    settings = await prefill_settings.get_settings()

    async def generate(*args):
        await prefill_settings.update_settings(PrefillSettingsUpdate(
            supplement="新規則", revision=settings.revision), ACTOR)
        current = await service.get_draft(draft.id)
        await service.update_draft(draft.id, DraftUpdate(version=current.version,
            fields=DraftFields(name="人工名稱"), manual_fields=["color"]), ACTOR)
        return output(name="AI 名稱", color="黑色", year=2026)

    generate_mock = AsyncMock(side_effect=generate)
    monkeypatch.setattr(prefill, "generate_prefill", generate_mock)
    queued = job(draft.id, draft.prefill_revision)
    await prefill.run_prefill(queued)
    result = await service.get_draft(draft.id)
    assert result.fields.name == "人工名稱" and result.fields.color is None
    assert result.fields.year == 2026 and result.prefill_status == "ready"
    await prefill.run_prefill(queued)
    generate_mock.assert_awaited_once()
    assert result.prefill_revision == 1


async def test_prefill_imports_vendor_quotes_and_preserves_manual_quotes(db, monkeypatch):
    draft = await draft_with_text()
    first = await VendorTable.create({"name": "大明", "is_active": True, "has_quotes": False})
    second = await VendorTable.create({"name": "小華", "is_active": True, "has_quotes": False})
    draft = await draft_quotes.save_quote(draft.id, DraftQuoteUpdate(version=draft.version,
        vendor_id=str(first["id"]), original_amount="999", exchange_rate="2"), ACTOR)
    payload = PrefillResult(name="手袋").model_dump(mode="json")
    payload["vendor_info"] = [
        {"vendor_id": str(first["id"]), "original_amount": "100", "exchange_rate": "4.5"},
        {"vendor_id": str(second["id"]), "original_amount": "200", "exchange_rate": "1"},
    ]
    generate = AsyncMock(return_value=PrefillContent(content=json.dumps(payload)))
    monkeypatch.setattr(prefill, "generate_prefill", generate)
    await prefill.run_prefill(job(draft.id, draft.prefill_revision))
    result = await service.get_draft(draft.id)
    saved = {quote.vendor_id: quote for quote in result.quotes}
    assert len(saved) == 2
    assert saved[str(first["id"])].original_amount == 999
    assert saved[str(first["id"])].exchange_rate == 2
    assert saved[str(second["id"])].original_amount == 200
    assert saved[str(second["id"])].exchange_rate == 1
    sent = json.loads(generate.call_args.args[1])
    assert {item["name"] for item in sent["vendors"]} == {"大明", "小華"}
    assert sent["messages"][0]["text"] == "手袋 成本3000"


async def test_prefill_discards_deleted_draft_and_invalid_vendor(db, monkeypatch):
    draft = await draft_with_text()
    generate = AsyncMock(return_value=output(vendor_info=[{
        "vendor_id": "11111111-1111-4111-8111-111111111111", "original_amount": "100",
    }]))
    monkeypatch.setattr(prefill, "generate_prefill", generate)
    await prefill.run_prefill(job(draft.id, draft.prefill_revision))
    assert (await service.get_draft(draft.id)).prefill_status == "failed"
    await active_session().delete(await model.get_draft_row(draft.id))
    await active_session().flush()
    await prefill.run_prefill(job(draft.id, draft.prefill_revision))
    generate.assert_awaited_once()
