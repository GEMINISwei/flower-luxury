import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from shared.jobs import worker
from shared.jobs.contracts import TaskSpec

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def database(monkeypatch):
    @asynccontextmanager
    async def session_scope():
        yield

    monkeypatch.setattr(worker, "session_scope", session_scope)
    mocks = {name: AsyncMock() for name in ("register_worker", "retire_worker", "recover_workers")}
    for name, mock in mocks.items():
        monkeypatch.setattr(worker, name, mock)
    monkeypatch.setattr(worker, "beat_worker", AsyncMock(return_value=True))
    return mocks


async def test_shutdown_drains_active_job_before_retiring(database, monkeypatch, tmp_path):
    started, finished, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def work(tasks, **kwargs):
        started.set()
        await stop.wait()
        assert not database["retire_worker"].called
        finished.set()
        return True

    monkeypatch.setattr(worker, "run_once", work)
    serving = asyncio.create_task(worker.serve({}, stop, tmp_path / "heartbeat"))
    await asyncio.wait_for(started.wait(), timeout=1)
    stop.set()
    await asyncio.wait_for(serving, timeout=1)
    assert finished.is_set() and database["retire_worker"].called
    assert not (tmp_path / "heartbeat").exists()


async def test_shutdown_cancels_stalled_job_after_grace(monkeypatch, tmp_path):
    started, cleaned, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def work(tasks, **kwargs):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    monkeypatch.setattr(worker, "run_once", work)
    serving = asyncio.create_task(worker.serve({}, stop, tmp_path / "heartbeat",
                                               shutdown_seconds=0.01))
    await asyncio.wait_for(started.wait(), timeout=1)
    stop.set()
    await asyncio.wait_for(serving, timeout=1)
    assert cleaned.is_set()


async def test_heartbeat_failure_stops_worker(monkeypatch, tmp_path):
    monkeypatch.setattr(worker, "beat_worker", AsyncMock(side_effect=ConnectionError()))
    with pytest.raises(ConnectionError):
        await asyncio.wait_for(worker.serve({}, asyncio.Event(), tmp_path / "heartbeat"), timeout=1)


async def test_idle_worker_responds_to_shutdown(monkeypatch, tmp_path):
    stop = asyncio.Event()

    async def work(tasks, **kwargs):
        stop.set()
        return False

    monkeypatch.setattr(worker, "run_once", work)
    await asyncio.wait_for(worker.serve({}, stop, tmp_path / "heartbeat"), timeout=1)


async def test_heartbeat_publishes_file_only_after_database_update(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat"

    class StopHeartbeatError(Exception):
        pass

    async def beat(worker_id):
        assert not path.exists()
        return True

    async def pause(seconds):
        assert seconds == 5 and path.is_file()
        raise StopHeartbeatError

    monkeypatch.setattr(worker, "beat_worker", beat)
    monkeypatch.setattr(worker.asyncio, "sleep", pause)
    with pytest.raises(StopHeartbeatError):
        await worker.heartbeat(path, uuid4())


async def test_lost_worker_does_not_publish_heartbeat(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat"
    monkeypatch.setattr(worker, "beat_worker", AsyncMock(return_value=False))
    with pytest.raises(RuntimeError, match="heartbeat"):
        await worker.heartbeat(path, uuid4())
    assert not path.exists()


async def test_slow_queue_does_not_block_other_queue(monkeypatch, tmp_path):
    slow_started, fast_done, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def handler(job):
        pass

    tasks = {"slow": TaskSpec("slow", handler, queue="images"),
             "fast": TaskSpec("fast", handler, queue="general")}

    async def work(selected, **kwargs):
        if "slow" in selected:
            slow_started.set()
            await stop.wait()
        else:
            await slow_started.wait()
            fast_done.set()
            stop.set()
        return True

    monkeypatch.setattr(worker, "run_once", work)
    await asyncio.wait_for(worker.serve(tasks, stop, tmp_path / "heartbeat"), timeout=1)
    assert fast_done.is_set()
