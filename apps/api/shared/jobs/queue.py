import random
from collections.abc import Mapping
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import and_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.elements import ColumnElement

from shared.db.session import active_session
from shared.time import utc_now

from .contracts import Job, TaskSpec
from .model import JobTable
from .workers import live_worker


async def enqueue_job(
    task_name: str, payload: dict[str, JsonValue], *, available_at: datetime | None = None,
    idempotency_key: str | None = None, queue: str = "general", max_attempts: int = 3,
) -> Job:
    if not task_name or not queue or max_attempts < 1:
        raise ValueError("task, queue and positive attempts are required")
    session = active_session()
    statement = insert(JobTable).values(
        task_name=task_name, payload=payload, available_at=available_at or utc_now(),
        idempotency_key=idempotency_key, queue=queue, max_attempts=max_attempts,
    ).on_conflict_do_nothing(index_elements=["task_name", "idempotency_key"]).returning(JobTable)
    row = (await session.scalars(statement)).one_or_none()
    if row is None:
        row = (await session.scalars(select(JobTable).where(
            JobTable.task_name == task_name, JobTable.idempotency_key == idempotency_key,
        ))).one()
    else:
        # PostgreSQL 只在交易提交後送通知, 回滾不會叫醒消費者。
        await session.execute(text("SELECT pg_notify('background_jobs', '')"))
    return Job.model_validate(row)


async def claim_job(tasks: Mapping[str, TaskSpec], *, worker_id: UUID) -> Job | None:
    # 與失聯回收鎖同一個 worker, 避免回收完成後又領到屬於死 worker 的新工作。
    if not tasks or not await active_session().scalar(live_worker(worker_id).with_for_update()):
        return None
    session = active_session()
    statement = select(JobTable).where(
        JobTable.task_name.in_(tasks), JobTable.status == "pending",
        JobTable.available_at <= utc_now(),
    ).order_by(JobTable.available_at, JobTable.id).with_for_update(skip_locked=True).limit(1)
    while (row := await session.scalar(statement)) is not None:
        task = tasks[row.task_name]
        if row.attempts == 0:
            row.max_attempts = min(row.max_attempts, task.max_attempts)
        if row.attempts >= row.max_attempts:
            row.status, row.finished_at = "dead", utc_now()
            await session.flush()
            continue
        row.status, row.lease_token, row.worker_id = "running", uuid4(), worker_id
        row.queue, row.updated_at = task.queue, utc_now()
        row.attempts += 1
        await session.flush()
        return Job.model_validate(row)
    return None


def _owned_claim(job: Job) -> ColumnElement[bool]:
    return and_(
        JobTable.id == job.id, JobTable.status == "running",
        JobTable.worker_id == job.worker_id, JobTable.lease_token == job.lease_token,
        live_worker(job.worker_id).exists(),
    )


async def complete_job(job: Job) -> bool:
    result = await active_session().execute(update(JobTable).where(_owned_claim(job)).values(
        status="succeeded", payload={}, worker_id=None, lease_token=None,
        last_error=None, finished_at=utc_now(), updated_at=utc_now(),
    ).returning(JobTable.id))
    return result.scalar_one_or_none() is not None


async def fail_job(
    job: Job, *, max_attempts: int | None = None, permanent: bool = False,
    error_code: str = "temporary",
) -> bool:
    # 儲存固定分類而非 exception 字串, 避免原文或憑證進入維運紀錄。
    now = utc_now()
    exhausted = permanent or job.attempts >= min(max_attempts or job.max_attempts,
                                                job.max_attempts)
    delay = min(30 * 2 ** min(job.attempts - 1, 5), 900) + random.uniform(0, 10)  # noqa: S311
    result = await active_session().execute(update(JobTable).where(_owned_claim(job)).values(
        status="dead" if exhausted else "pending",
        available_at=now + timedelta(seconds=delay), worker_id=None, lease_token=None,
        last_error=error_code if error_code in {"temporary", "permanent", "timeout",
                                              "cancelled", "ownership_lost"} else "temporary",
        finished_at=now if exhausted else None, updated_at=now,
    ).returning(JobTable.id))
    return result.scalar_one_or_none() is not None
