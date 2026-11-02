from collections.abc import Mapping
from datetime import datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, update

from shared.db.session import active_session
from shared.time import utc_now

from .contracts import Job, TaskSpec
from .model import JobTable, WorkerTable


class QueueReport(BaseModel):
    queue: str
    pending: int = 0
    running: int = 0
    succeeded: int = 0
    dead: int = 0
    ready: int = 0
    oldest_wait_seconds: float = 0


class DeadJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_name: str
    queue: str
    attempts: int
    max_attempts: int
    last_error: str | None
    finished_at: datetime | None


class JobOverview(BaseModel):
    queues: list[QueueReport]
    dead_jobs: list[DeadJob] = Field(default_factory=list)


async def job_overview() -> JobOverview:
    now = utc_now()
    rows = await active_session().execute(select(
        JobTable.queue, JobTable.status, func.count(),
        func.count().filter(JobTable.available_at <= now), func.min(JobTable.available_at),
    ).group_by(JobTable.queue, JobTable.status))
    queues: dict[str, QueueReport] = {}
    for queue, status, count, ready, earliest in rows:
        item = queues.setdefault(queue, QueueReport(queue=queue))
        setattr(item, status, count)
        if status == "pending":
            item.ready = ready
            item.oldest_wait_seconds = max(0, (now - earliest).total_seconds())
    dead = await active_session().scalars(select(JobTable).where(JobTable.status == "dead")
                                          .order_by(JobTable.finished_at.desc()).limit(50))
    return JobOverview(queues=sorted(queues.values(), key=lambda item: item.queue),
                       dead_jobs=[DeadJob.model_validate(row) for row in dead])


async def cleanup_jobs() -> int:
    now = utc_now()
    expired = ((JobTable.status == "succeeded")
               & (JobTable.finished_at < now - timedelta(days=7))) | (
        (JobTable.status == "dead") & (JobTable.finished_at < now - timedelta(days=30)))
    selected = select(JobTable.id).where(expired).order_by(JobTable.finished_at).limit(500)
    result = await active_session().execute(delete(JobTable).where(
        JobTable.id.in_(selected.with_for_update(skip_locked=True)),
    ).returning(JobTable.id))
    await active_session().execute(delete(WorkerTable).where(
        WorkerTable.status == "dead", WorkerTable.heartbeat_at < now - timedelta(days=30),
        ~select(JobTable.id).where(JobTable.worker_id == WorkerTable.id).exists(),
    ))
    return len(result.all())


async def retry_dead_job(job_id: UUID, tasks: Mapping[str, TaskSpec]) -> bool:
    row = await active_session().scalar(select(JobTable).where(
        JobTable.id == job_id, JobTable.status == "dead",
    ).with_for_update())
    if row is None or row.task_name not in tasks or row.max_attempts <= 1:
        return False
    task = tasks[row.task_name]
    if task.max_attempts <= 1:
        return False
    await active_session().execute(update(JobTable).where(JobTable.id == job_id).values(
        status="pending", attempts=0, max_attempts=task.max_attempts, available_at=utc_now(),
        queue=task.queue, last_error=None, finished_at=None, updated_at=utc_now(),
    ))
    return True


async def _cleanup(_job: Job) -> None:
    await cleanup_jobs()


CLEANUP_TASK = TaskSpec("system.cleanup_jobs", _cleanup, queue="maintenance", interval_seconds=3600)
