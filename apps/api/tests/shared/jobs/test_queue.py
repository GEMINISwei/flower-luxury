import asyncio
import os
from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy import String, delete, select, update
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.session import (
    active_session,
    configure_session_factory,
    create_engine,
    session_scope,
)
from shared.db.table import BaseTable
from shared.db.transaction import transaction
from shared.jobs.contracts import Job, TaskSpec
from shared.jobs.model import JobTable
from shared.jobs.queue import claim_job, complete_job, enqueue_job, fail_job
from shared.jobs.runner import run_once
from shared.time import utc_now
from tests.integration import require_postgres, restore_session_factory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class EffectTable(BaseTable):
    __tablename__ = "test_job_effects"
    value: Mapped[str] = mapped_column(String)


async def noop(job: Job) -> None:
    pass


TASK = TaskSpec("example.process", noop, max_attempts=2, timeout_seconds=1)
TASKS = {TASK.name: TASK}


@pytest_asyncio.fixture(autouse=True)
async def database():
    url = os.environ["POSTGRES_URL"]
    engine = create_engine(url)
    await require_postgres(engine, url)
    tables = [BaseTable.metadata.tables[name] for name in ("background_jobs", "test_job_effects")]
    async with engine.begin() as connection:
        await connection.run_sync(BaseTable.metadata.create_all, tables=tables)
        for table in tables:
            await connection.execute(delete(table))
    with restore_session_factory():
        configure_session_factory(engine)
        yield
    async with engine.begin() as connection:
        for table in tables:
            await connection.execute(delete(table))
    await engine.dispose()


async def enqueue(name: str = TASK.name, **kwargs) -> Job:
    async with session_scope():
        return await enqueue_job(name, {"message_id": "example"}, **kwargs)


async def claim(tasks=None) -> Job | None:
    async with session_scope():
        return await claim_job(TASKS if tasks is None else tasks)


async def expire(job: Job) -> None:
    async with session_scope() as session:
        await session.execute(update(JobTable).where(JobTable.id == job.id).values(
            locked_until=utc_now() - timedelta(seconds=1),
        ))


async def make_due(job: Job) -> None:
    async with session_scope() as session:
        await session.execute(update(JobTable).where(JobTable.id == job.id).values(
            available_at=utc_now() - timedelta(seconds=1),
        ))


async def stored(job: Job):
    async with session_scope() as session:
        return await session.get(JobTable, job.id)


async def test_job_enqueue_rolls_back_with_business_transaction():
    async with session_scope():
        with pytest.raises(ValueError, match="rollback"):
            async with transaction():
                await enqueue_job(TASK.name, {"message_id": "rolled-back"})
                raise ValueError("rollback")
    assert await claim() is None


async def test_workers_do_not_claim_same_job():
    await enqueue()
    claimed = await asyncio.gather(claim(), claim())
    assert sum(job is not None for job in claimed) == 1


async def test_claim_only_registered_due_jobs():
    await enqueue("disabled.process")
    await enqueue(available_at=utc_now() + timedelta(hours=1))
    assert await claim() is None
    due = await enqueue()
    job = await claim()
    assert job is not None and job.id == due.id and job.attempts == 1
    assert await claim({}) is None


async def test_expired_job_can_be_reclaimed():
    await enqueue()
    first = await claim()
    assert first is not None
    assert await claim() is None
    await expire(first)
    second = await claim()
    assert second is not None and second.id == first.id
    assert second.attempts == 2 and second.lease_token != first.lease_token


async def test_stale_claim_cannot_complete_or_retry():
    await enqueue()
    first = await claim()
    assert first is not None
    await expire(first)
    second = await claim()
    assert second is not None
    async with session_scope():
        assert not await complete_job(first)
        assert not await fail_job(first, max_attempts=TASK.max_attempts)
    row = await stored(second)
    assert row.status == "running" and row.lease_token == second.lease_token


async def test_expired_claim_cannot_finish_even_before_reclaim():
    await enqueue()
    job = await claim()
    assert job is not None
    await expire(job)
    async with session_scope():
        assert not await complete_job(job)


async def test_exhausted_job_stops_retrying():
    queued = await enqueue()
    for _ in range(TASK.max_attempts):
        job = await claim()
        assert job is not None
        async with session_scope():
            assert await fail_job(job, max_attempts=TASK.max_attempts)
        await make_due(job)
    assert await claim() is None
    row = await stored(queued)
    assert row.status == "failed" and row.attempts == TASK.max_attempts


async def test_expired_final_attempt_is_marked_failed():
    await enqueue()
    for _ in range(TASK.max_attempts):
        job = await claim()
        assert job is not None
        await expire(job)
    assert await claim() is None
    assert job is not None
    assert (await stored(job)).status == "failed"


async def test_successful_handler_commits_and_removes_job():
    async def handle(job: Job) -> None:
        active_session().add(EffectTable(value=str(job.payload["message_id"])))

    queued = await enqueue()
    assert await run_once({TASK.name: TaskSpec(TASK.name, handle)})
    assert await stored(queued) is None
    async with session_scope() as session:
        assert list(await session.scalars(select(EffectTable.value))) == ["example"]


async def test_failed_handler_rolls_back_and_retries(caplog):
    secret = "private-product-text"

    async def handle(job: Job) -> None:
        active_session().add(EffectTable(value="must-rollback"))
        await active_session().flush()
        raise ValueError(secret)

    async with session_scope():
        queued = await enqueue_job(TASK.name, {"text": secret})
    assert await run_once({TASK.name: TaskSpec(TASK.name, handle)})
    row = await stored(queued)
    assert row.status == "pending" and row.attempts == 1
    assert row.available_at > utc_now() and row.lease_token is None
    assert secret not in caplog.text
    assert await claim() is None
    async with session_scope() as session:
        assert list(await session.scalars(select(EffectTable))) == []


async def test_handler_timeout_retries():
    async def handle(job: Job) -> None:
        active_session().add(EffectTable(value="must-rollback"))
        await active_session().flush()
        await asyncio.Event().wait()

    queued = await enqueue()
    task = TaskSpec(TASK.name, handle, timeout_seconds=0.02)
    assert await run_once({task.name: task})
    assert (await stored(queued)).status == "pending"
    async with session_scope() as session:
        assert list(await session.scalars(select(EffectTable))) == []


async def test_lost_lease_rolls_back_handler_changes():
    async def handle(job: Job) -> None:
        active_session().add(EffectTable(value="stale-effect"))
        async with session_scope() as session:
            await session.execute(update(JobTable).where(JobTable.id == job.id).values(
                lease_token=None, status="pending", locked_until=None,
            ))

    await enqueue()
    assert await run_once({TASK.name: TaskSpec(TASK.name, handle)})
    async with session_scope() as session:
        assert list(await session.scalars(select(EffectTable))) == []


async def test_cancelled_handler_rolls_back_and_releases_job():
    started = asyncio.Event()

    async def handle(job: Job) -> None:
        active_session().add(EffectTable(value="cancelled"))
        await active_session().flush()
        started.set()
        await asyncio.Event().wait()

    queued = await enqueue()
    running = asyncio.create_task(run_once({TASK.name: TaskSpec(TASK.name, handle)}))
    await asyncio.wait_for(started.wait(), timeout=3)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert (await stored(queued)).status == "pending"
    async with session_scope() as session:
        assert list(await session.scalars(select(EffectTable))) == []


async def test_run_once_returns_false_when_idle():
    assert not await run_once(TASKS)
