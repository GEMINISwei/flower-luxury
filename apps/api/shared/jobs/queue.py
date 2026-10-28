from collections.abc import Mapping
from datetime import datetime, timedelta
from uuid import uuid4

from pydantic import JsonValue
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.sql.elements import ColumnElement

from shared.db.session import active_session
from shared.time import utc_now

from .contracts import Job, TaskSpec
from .model import JobTable

LEASE_GRACE_SECONDS = 30


async def enqueue_job(
    task_name: str, payload: dict[str, JsonValue], *, available_at: datetime | None = None,
) -> Job:
    row = JobTable(task_name=task_name, payload=payload, available_at=available_at or utc_now())
    active_session().add(row)
    await active_session().flush()
    return Job.model_validate(row)


async def claim_job(tasks: Mapping[str, TaskSpec]) -> Job | None:
    if not tasks:
        return None
    session = active_session()
    now = utc_now()
    statement = select(JobTable).where(
        JobTable.task_name.in_(tasks),
        or_(
            and_(JobTable.status == "pending", JobTable.available_at <= now),
            and_(JobTable.status == "running", JobTable.locked_until <= now),
        ),
    ).order_by(JobTable.available_at, JobTable.id).with_for_update(skip_locked=True).limit(1)
    while (row := await session.scalar(statement)) is not None:
        task = tasks[row.task_name]
        if row.attempts >= task.max_attempts:
            row.status, row.lease_token, row.locked_until = "failed", None, None
            row.updated_at = now
            await session.flush()
            continue
        row.status, row.lease_token = "running", uuid4()
        row.attempts += 1
        row.locked_until = now + timedelta(seconds=task.timeout_seconds + LEASE_GRACE_SECONDS)
        row.updated_at = now
        await session.flush()
        return Job.model_validate(row)
    return None


def _owned_claim(job: Job) -> ColumnElement[bool]:
    return and_(
        JobTable.id == job.id, JobTable.status == "running",
        JobTable.lease_token == job.lease_token, JobTable.locked_until > utc_now(),
    )


async def complete_job(job: Job) -> bool:
    result = await active_session().execute(
        delete(JobTable).where(_owned_claim(job)).returning(JobTable.id),
    )
    return result.scalar_one_or_none() is not None


async def fail_job(job: Job, *, max_attempts: int) -> bool:
    # 不保存 exception 字串: 外部服務錯誤可能含有商品內容或憑證。
    now = utc_now()
    result = await active_session().execute(update(JobTable).where(_owned_claim(job)).values(
        status="failed" if job.attempts >= max_attempts else "pending",
        available_at=now + timedelta(seconds=min(30 * 2 ** min(job.attempts - 1, 5), 900)),
        lease_token=None, locked_until=None, updated_at=now,
    ).returning(JobTable.id))
    return result.scalar_one_or_none() is not None
