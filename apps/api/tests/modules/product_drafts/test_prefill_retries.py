from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from modules.product_drafts import model, prefill, service
from modules.product_drafts.manifest import MODULE
from modules.product_drafts.prefill_transport import PrefillTransportError
from modules.product_drafts.schema import DraftFields, DraftUpdate, VersionRequest
from modules.vendors.model import VendorTable
from shared.db.session import active_session
from shared.http.errors import LangException
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from shared.jobs.queue import fail_job
from shared.jobs.workers import register_worker
from shared.time import utc_now
from tests.modules.product_drafts.helpers import ACTOR
from tests.modules.product_drafts.test_prefill_integration import draft_with_text, output

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def worker_connection(monkeypatch):
    monkeypatch.setattr(prefill, "release_connection", AsyncMock())
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


async def queued_for(id):
    return (await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill", JobTable.payload["draft_id"].astext == id,
    ).order_by(JobTable.created_at.desc(), JobTable.id.desc()))).first()


@pytest.mark.parametrize("error", [PrefillTransportError(), ValueError("invalid JSON"),
                                  RuntimeError("interrupted")])
async def test_prefill_failure_retries_every_minute_and_stops_after_three_attempts(
    db, monkeypatch, error,
):
    draft = await draft_with_text()
    queued = await queued_for(draft.id)
    task = next(task for task in MODULE.tasks if task.name == "product_drafts.prefill")
    assert queued is not None and queued.max_attempts == task.max_attempts == 3
    assert task.retry_delay_seconds == 60
    worker = uuid4()
    await register_worker(worker)
    generate = AsyncMock(side_effect=error)
    monkeypatch.setattr(prefill, "generate_prefill", generate)
    for attempt in range(1, 4):
        queued.status, queued.attempts = "running", attempt
        queued.worker_id, queued.lease_token = worker, uuid4()
        await active_session().flush()
        claimed = Job.model_validate(queued)
        before = utc_now()
        with pytest.raises(type(error)):
            await prefill.run_prefill(claimed)
        assert await fail_job(claimed, retry_delay_seconds=task.retry_delay_seconds)
        await active_session().refresh(queued)
        assert queued.status == ("dead" if attempt == 3 else "pending")
        assert before + timedelta(seconds=60) <= queued.available_at \
            <= utc_now() + timedelta(seconds=60)
    assert generate.await_count == 3
    assert (await service.get_draft(draft.id)).prefill_status == "failed"


async def test_prefill_recovery_respects_attempt_limit_and_completed_results(db):
    from modules.product_drafts.prefill_jobs import recover_prefill

    draft = await draft_with_text()
    queued = await queued_for(draft.id)
    assert queued is not None
    queued.idempotency_key = None
    queued.max_attempts, queued.attempts, queued.status = 1, 1, "dead"
    failed_at = queued.finished_at = utc_now()
    row = await model.get_draft_row(draft.id)
    assert row is not None
    row.prefill_status = "unknown"
    await active_session().flush()
    tick = Job(id=uuid4(), task_name="product_drafts.recover_prefill", payload={}, attempts=1)
    await recover_prefill(tick)
    await recover_prefill(tick)
    await active_session().refresh(queued)
    assert queued.status == "pending" and queued.max_attempts == 3 and queued.attempts == 1
    assert queued.available_at >= failed_at + timedelta(seconds=60)
    assert len(list(await active_session().scalars(select(JobTable).where(
        JobTable.task_name == "product_drafts.prefill")))) == 1
    queued.status, queued.attempts = "dead", 3
    await recover_prefill(tick)
    assert row.prefill_status == "failed" and queued.status == "dead"
    row.prefill_status = "ready"
    await recover_prefill(tick)
    assert row.prefill_status == "ready" and queued.status == "dead"


async def test_prefill_recovery_requeues_orphan_and_waits_for_active_job(db):
    from modules.product_drafts.prefill_jobs import recover_prefill

    draft = await draft_with_text()
    await active_session().execute(delete(JobTable).where(
        JobTable.task_name == "product_drafts.prefill"))
    row = await model.get_draft_row(draft.id)
    assert row is not None
    row.prefill_status = "failed"
    tick = Job(id=uuid4(), task_name="product_drafts.recover_prefill", payload={}, attempts=1)
    await recover_prefill(tick)
    queued = await queued_for(draft.id)
    assert queued is not None and queued.status == "pending" and queued.max_attempts == 3
    await recover_prefill(tick)
    assert (await queued_for(draft.id)).id == queued.id
    queued.status, queued.worker_id, queued.lease_token = "running", uuid4(), uuid4()
    await recover_prefill(tick)
    assert queued.status == "running"


async def test_prefill_recovery_does_not_restart_exhausted_draft_after_job_cleanup(db):
    from modules.product_drafts.prefill_jobs import recover_prefill

    draft = await draft_with_text()
    queued = await queued_for(draft.id)
    queued.status, queued.attempts = "dead", 3
    tick = Job(id=uuid4(), task_name="product_drafts.recover_prefill", payload={}, attempts=1)
    await recover_prefill(tick)
    await active_session().delete(queued)
    await active_session().flush()
    await recover_prefill(tick)
    assert await queued_for(draft.id) is None
    assert (await service.get_draft(draft.id)).prefill_status == "failed"


async def test_prefill_retry_preserves_manual_fields_and_quotes(db, monkeypatch):
    draft = await draft_with_text()
    vendor = await VendorTable.create({"name": "buyer", "is_active": True, "has_quotes": False})
    draft = await service.update_draft(draft.id, DraftUpdate(version=draft.version,
        fields=DraftFields(name="人工名稱"), manual_fields=["color"]), ACTOR)
    row = await model.get_draft_row(draft.id)
    assert row is not None
    row.quotes = [{"id": str(uuid4()), "vendor_id": str(vendor["id"]),
                   "original_amount": "900", "exchange_rate": "1", "note": None}]
    original = list(row.quotes)
    generate = AsyncMock(return_value=output(name="AI 名稱", color="黑色", year=2026,
        vendor_info=[{"vendor_id": str(vendor["id"]), "original_amount": "100"}]))
    monkeypatch.setattr(prefill, "generate_prefill", generate)
    queued = await queued_for(draft.id)
    queued.attempts = 2
    await prefill.run_prefill(Job.model_validate(queued))
    assert row.fields["name"] == "人工名稱" and row.fields["color"] is None
    assert row.fields["year"] == 2026 and row.quotes == original and row.prefill_status == "ready"
    await prefill.run_prefill(Job.model_validate(queued))
    generate.assert_awaited_once()


async def test_manual_prefill_retry_starts_new_round_without_duplicate_jobs(db):
    draft = await draft_with_text()
    queued = await queued_for(draft.id)
    queued.status, queued.attempts = "dead", 3
    row = await model.get_draft_row(draft.id)
    assert row is not None
    row.prefill_status = "failed"
    before = row.prefill_revision
    result = await prefill.retry_prefill(draft.id, VersionRequest(version=row.version), ACTOR)
    assert result.prefill_status == "queued" and result.prefill_revision == before + 1
    new = await queued_for(draft.id)
    assert new.id != queued.id and new.max_attempts == 3 and new.attempts == 0
    repeated = await prefill.retry_prefill(draft.id, VersionRequest(version=result.version), ACTOR)
    assert repeated.prefill_revision == result.prefill_revision
    assert (await queued_for(draft.id)).id == new.id
    with pytest.raises(LangException):
        await prefill.retry_prefill(draft.id, VersionRequest(version=1), ACTOR)


async def test_manual_prefill_retry_does_not_restart_collecting_or_completed_drafts(db):
    draft = await draft_with_text(close=False)
    with pytest.raises(LangException):
        await prefill.retry_prefill(draft.id, VersionRequest(version=draft.version), ACTOR)
    row = await model.get_draft_row(draft.id)
    assert row is not None
    row.collecting, row.prefill_status = False, "ready"
    result = await prefill.retry_prefill(draft.id, VersionRequest(version=row.version), ACTOR)
    assert result.prefill_status == "ready"
    assert await queued_for(draft.id) is None
