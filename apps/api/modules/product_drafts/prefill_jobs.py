from datetime import timedelta

from sqlalchemy import String, and_, cast, or_, select

from shared.db.session import active_session
from shared.jobs.contracts import Job
from shared.jobs.model import JobTable
from shared.jobs.queue import enqueue_job
from shared.time import utc_now

from . import model
from .prefill_config import get_env

TASK_NAME = "product_drafts.prefill"
MAX_ATTEMPTS = 3
RETRY_SECONDS = 60


def job_key(row: model.DraftTable) -> str:
    return f"prefill:{row.id}:{row.prefill_revision}"


async def current_job(row: model.DraftTable) -> JobTable | None:
    return await active_session().scalar(select(JobTable).where(
        JobTable.task_name == TASK_NAME,
        or_(JobTable.idempotency_key == job_key(row), and_(
            JobTable.payload["draft_id"].astext == str(row.id),
            JobTable.payload["revision"].astext == str(row.prefill_revision),
        )),
    ).order_by(JobTable.created_at.desc(), JobTable.id.desc()).limit(1))


async def enqueue_prefill(row: model.DraftTable, *, delay: int = 2) -> Job:
    return await enqueue_job(TASK_NAME, {
        "draft_id": str(row.id), "revision": row.prefill_revision,
    }, idempotency_key=job_key(row), available_at=utc_now() + timedelta(seconds=delay),
        queue="ai", max_attempts=MAX_ATTEMPTS)


async def prefill_status(row: model.DraftTable) -> str:
    if row.collecting or row.prefill_status == "ready":
        return row.prefill_status or "idle"
    queued = await current_job(row)
    if queued is None:
        return row.prefill_status or "idle"
    return "queued" if queued.status in {"pending", "running"} else "failed"


def _set_status(row: model.DraftTable, status: str) -> None:
    if row.prefill_status != status:
        row.prefill_status = status
        row.version += 1
        row.updated_at = utc_now()


async def _recover(row: model.DraftTable) -> None:
    queued = await current_job(row)
    if queued is None:
        if row.prefill_attempts >= MAX_ATTEMPTS:
            _set_status(row, "failed")
        elif get_env().prefill_configured:
            row.prefill_revision = row.prefill_revision or 1
            await enqueue_prefill(row, delay=RETRY_SECONDS)
            _set_status(row, "queued")
        else:
            _set_status(row, "disabled")
        return
    # 舊工作沒有去重鍵且只允許一次, 接手後仍沿用已消耗的次數.
    if queued.idempotency_key is None:
        queued.idempotency_key = job_key(row)
        queued.max_attempts = MAX_ATTEMPTS
    row.prefill_attempts = max(row.prefill_attempts, queued.attempts)
    if queued.status in {"dead", "succeeded"}:
        if queued.attempts >= queued.max_attempts:
            row.prefill_attempts = MAX_ATTEMPTS
            _set_status(row, "failed")
            return
        queued.status = "pending"
        queued.payload = {"draft_id": str(row.id), "revision": row.prefill_revision}
        queued.available_at = utc_now() + timedelta(seconds=RETRY_SECONDS)
        queued.finished_at = None
    _set_status(row, "queued")


async def recover_prefill(_job: Job) -> None:
    # 已同步的工作不佔批次名額, 避免前面的排程或死信讓後面的漏排永遠輪不到.
    key = "prefill:" + cast(model.DraftTable.id, String) + ":" \
        + cast(model.DraftTable.prefill_revision, String)
    settled = select(JobTable.id).where(
        JobTable.idempotency_key == key, JobTable.task_name == TASK_NAME,
        JobTable.max_attempts == MAX_ATTEMPTS,
        model.DraftTable.prefill_attempts >= JobTable.attempts,
        JobTable.status.in_(("pending", "running")), model.DraftTable.prefill_status == "queued",
    ).exists()
    statuses = ["queued", "unknown", "failed"]
    if get_env().prefill_configured:
        statuses.extend(("idle", "disabled"))
    rows = await active_session().scalars(select(model.DraftTable).where(
        model.DraftTable.collecting.is_(False), model.DraftTable.prefill_status.in_(statuses),
        ~and_(model.DraftTable.prefill_status == "failed",
              model.DraftTable.prefill_attempts >= MAX_ATTEMPTS), ~settled,
    ).order_by(model.DraftTable.created_at, model.DraftTable.id)
        .with_for_update(skip_locked=True).limit(100))
    for row in rows:
        await _recover(row)
    await active_session().flush()
