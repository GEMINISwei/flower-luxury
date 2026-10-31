import json
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from modules.brands.public import BrandTable
from modules.product_drafts import collection, messages, model, prefill, prefill_settings, service
from modules.product_drafts.prefill_schema import PrefillContent, PrefillSettingsUpdate
from modules.product_drafts.schema import DraftFields, DraftUpdate, MessageMove, VersionRequest
from shared.db.session import active_session
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from tests.modules.product_drafts.helpers import ACTOR, incoming

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def worker_connection(monkeypatch):
    # 測試沿用 fixture 的未提交交易, 不歸還其中的連線.
    monkeypatch.setattr(prefill, "release_connection", AsyncMock())


def job(id, revision):
    return Job(id=uuid.uuid4(), task_name="product_drafts.prefill", attempts=1,
               payload={"draft_id": id, "revision": revision})


async def draft_with_text(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    first = await collection.ingest_message(incoming())
    await collection.ingest_message(incoming("text", text="手袋 成本3000", second=1))
    return await service.get_draft(first.draft_id)


async def test_prefill_discards_stale_and_deleted_results(db, monkeypatch):
    draft = await draft_with_text(monkeypatch)
    settings = await prefill_settings.get_settings()
    await collection.ingest_message(incoming("text", text="改為紅色", second=2))
    result = await prefill.apply_prefill(draft.id, draft.prefill_revision, settings.revision,
                                         DraftFields(name="舊結果"))
    assert not result.applied
    latest = await service.get_draft(draft.id)
    assert latest.fields.name is None
    row = await model.get_draft_row(draft.id)
    await active_session().delete(row)
    await active_session().flush()
    result = await prefill.apply_prefill(draft.id, latest.prefill_revision, settings.revision,
                                         DraftFields(name="不能復活"))
    assert not result.applied


async def test_prefill_failure_preserves_fields_and_can_retry(db, monkeypatch):
    draft = await draft_with_text(monkeypatch)
    draft = await service.update_draft(draft.id, DraftUpdate(
        version=draft.version, fields=DraftFields(name="人工名稱")), ACTOR)
    monkeypatch.setattr(prefill, "generate_prefill", AsyncMock(side_effect=ValueError("invalid")))
    await prefill.run_prefill(job(draft.id, draft.prefill_revision))
    failed = await service.get_draft(draft.id)
    assert failed.prefill_status == "failed" and failed.fields.name == "人工名稱"
    retried = await prefill.retry_prefill(draft.id, VersionRequest(version=failed.version))
    assert retried.prefill_status == "queued"
    monkeypatch.setattr(prefill, "generate_prefill", AsyncMock(return_value=PrefillContent(
        content=json.dumps(DraftFields(name="AI 名稱", color="紅色").model_dump()))))
    await prefill.run_prefill(job(draft.id, retried.prefill_revision))
    result = await service.get_draft(draft.id)
    assert result.prefill_status == "ready"
    assert result.fields.name == "人工名稱" and result.fields.color == "紅色"


async def test_text_changes_schedule_prefill_for_affected_drafts(db, monkeypatch):
    draft = await draft_with_text(monkeypatch)
    assert draft.prefill_status == "queued" and draft.prefill_revision == 1
    jobs = list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill")))
    assert len(jobs) == 1 and set(jobs[0].payload) == {"draft_id", "revision"}
    second = await collection.ingest_message(incoming(second=2))
    target = await service.get_draft(second.draft_id)
    assert target.prefill_revision == 0
    text = next(item for item in draft.messages if item.kind == "text")
    draft = await service.get_draft(draft.id)
    moved = await messages.move_message(text.id, MessageMove(target_draft_id=target.id,
        target_version=target.version, source_version=draft.version), ACTOR)
    assert moved.prefill_revision == 1
    assert (await service.get_draft(draft.id)).prefill_revision == 2
    await messages.withdraw_message("group-a", text.external_id)
    assert (await service.get_draft(target.id)).prefill_revision == 2


async def test_prefill_rechecks_settings_and_preserves_manual_clear(db, monkeypatch):
    draft = await draft_with_text(monkeypatch)
    settings = await prefill_settings.get_settings()
    applied = await prefill.apply_prefill(draft.id, draft.prefill_revision, settings.revision,
                                         DraftFields(name="舊名", color="紅色"))
    assert applied.applied
    draft = await service.get_draft(draft.id)
    draft = await service.update_draft(draft.id, DraftUpdate(version=draft.version,
        fields=DraftFields(color="紅色"), manual_fields=["name"]), ACTOR)
    assert "name" in draft.manual_fields and "color" not in draft.manual_fields
    await prefill_settings.update_settings(PrefillSettingsUpdate(
        supplement="底價代表成本", revision=settings.revision), ACTOR)
    applied = await prefill.apply_prefill(draft.id, draft.prefill_revision, settings.revision,
                                         DraftFields(name="不該寫入"))
    assert not applied.applied
    latest_settings = await prefill_settings.get_settings()
    latest = await service.get_draft(draft.id)
    applied = await prefill.apply_prefill(
        draft.id, latest.prefill_revision, latest_settings.revision,
        DraftFields(name="新名", color="黑色"))
    assert applied.applied
    result = await service.get_draft(draft.id)
    assert result.fields.name is None and result.fields.color == "黑色"


async def test_prefill_rejects_invalid_brand_and_uses_all_text(db, monkeypatch):
    draft = await draft_with_text(monkeypatch)
    brand = await BrandTable.create({"name": "測試品牌", "is_active": True})
    generate = AsyncMock(return_value=PrefillContent(content=json.dumps(DraftFields(
        brand_id=str(brand["id"]), name="手袋").model_dump())))
    monkeypatch.setattr(prefill, "generate_prefill", generate)
    await prefill.run_prefill(job(draft.id, draft.prefill_revision))
    assert (await service.get_draft(draft.id)).fields.brand_id == str(brand["id"])
    assert "手袋 成本3000" in str(generate.call_args)
