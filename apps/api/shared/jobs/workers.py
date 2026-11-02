from datetime import timedelta
from uuid import UUID

from sqlalchemy import Select, case, func, select, update

from shared.db.session import active_session
from shared.time import utc_now

from .model import JobTable, WorkerTable


def live_worker(worker_id: UUID | None) -> Select:
    # 資料庫時間讓不同主機的 worker 不受彼此時鐘偏差影響。
    cutoff = func.timezone("UTC", func.clock_timestamp()) - timedelta(seconds=30)
    return select(WorkerTable.id).where(WorkerTable.id == worker_id,
                                      WorkerTable.status == "active",
                                      WorkerTable.heartbeat_at > cutoff)


async def register_worker(worker_id: UUID) -> None:
    active_session().add(WorkerTable(id=worker_id))
    await active_session().flush()


async def beat_worker(worker_id: UUID) -> bool:
    result = await active_session().execute(update(WorkerTable).where(
        WorkerTable.id.in_(live_worker(worker_id)),
    ).values(heartbeat_at=func.timezone("UTC", func.clock_timestamp()),
             updated_at=utc_now()).returning(WorkerTable.id))
    return result.scalar_one_or_none() is not None


async def _release(worker_id: UUID) -> None:
    now = utc_now()
    exhausted = JobTable.attempts >= JobTable.max_attempts
    await active_session().execute(update(JobTable).where(
        JobTable.worker_id == worker_id, JobTable.status == "running",
    ).values(status=case((exhausted, "dead"), else_="pending"), worker_id=None,
             lease_token=None, available_at=now, updated_at=now, last_error="worker_lost",
             finished_at=case((exhausted, now), else_=None)))


async def recover_workers() -> None:
    session = active_session()
    cutoff = func.timezone("UTC", func.clock_timestamp()) - timedelta(seconds=30)
    stale = await session.scalars(select(WorkerTable).where(
        WorkerTable.status == "active", WorkerTable.heartbeat_at <= cutoff,
    ).with_for_update(skip_locked=True).limit(100))
    for row in stale:
        row.status, row.updated_at = "dead", utc_now()
        await _release(row.id)
    await session.flush()


async def retire_worker(worker_id: UUID) -> None:
    await active_session().execute(update(WorkerTable).where(WorkerTable.id == worker_id)
                                  .values(status="dead", updated_at=utc_now()))
    await _release(worker_id)
