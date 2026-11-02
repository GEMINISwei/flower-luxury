from datetime import timedelta

import pytest
from sqlalchemy import select, update

from shared.db.session import session_scope
from shared.jobs import maintenance
from shared.jobs.model import JobTable
from shared.time import utc_now
from tests.shared.jobs.test_queue import TASKS, claim, enqueue, stored
from tests.shared.jobs.test_queue import database as database

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_cleanup_removes_only_expired_terminal_jobs():
    jobs = [await enqueue() for _ in range(5)]
    async with session_scope() as session:
        for job, status, days in zip(jobs, ["succeeded", "succeeded", "dead", "dead", "pending"],
                                     [8, 2, 31, 8, 40], strict=True):
            await session.execute(update(JobTable).where(JobTable.id == job.id).values(
                status=status, finished_at=utc_now() - timedelta(days=days)))
        assert await maintenance.cleanup_jobs() == 2
        remaining = set(await session.scalars(select(JobTable.id)))
        assert remaining == {jobs[1].id, jobs[3].id, jobs[4].id}


async def test_dead_job_requeue_is_explicit_and_idempotent():
    job = await enqueue()
    async with session_scope() as session:
        await session.execute(update(JobTable).where(JobTable.id == job.id).values(
            status="dead", attempts=3, last_error="temporary", finished_at=utc_now()))
        assert await maintenance.retry_dead_job(job.id, TASKS)
        assert not await maintenance.retry_dead_job(job.id, TASKS)
    claimed = await claim()
    assert claimed is not None and claimed.id == job.id and claimed.attempts == 1


async def test_unsafe_single_attempt_job_is_not_manually_requeued():
    job = await enqueue()
    async with session_scope() as session:
        await session.execute(update(JobTable).where(JobTable.id == job.id).values(
            status="dead", max_attempts=1, attempts=1, last_error="worker_lost"))
        assert not await maintenance.retry_dead_job(job.id, TASKS)
    assert (await stored(job)).status == "dead"


async def test_overview_distinguishes_delayed_jobs_from_backlog():
    await enqueue(queue="downloads", available_at=utc_now() - timedelta(seconds=60))
    await enqueue(queue="downloads", available_at=utc_now() + timedelta(days=1))
    async with session_scope():
        overview = await maintenance.job_overview()
    row = next(row for row in overview.queues if row.queue == "downloads")
    assert row.pending == 2 and row.ready == 1 and row.oldest_wait_seconds >= 60
