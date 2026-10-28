import asyncio

import pytest

from shared.jobs import worker

pytestmark = pytest.mark.asyncio


async def test_shutdown_cancels_active_job_and_waits_for_cleanup(monkeypatch, tmp_path):
    started, cleaned, stop = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def work(tasks):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    async def heartbeat(path):
        await asyncio.Event().wait()

    monkeypatch.setattr(worker, "run_once", work)
    monkeypatch.setattr(worker, "heartbeat", heartbeat)
    serving = asyncio.create_task(worker.serve({}, stop, tmp_path / "heartbeat"))
    await asyncio.wait_for(started.wait(), timeout=1)
    stop.set()
    await asyncio.wait_for(serving, timeout=1)
    assert cleaned.is_set()


async def test_heartbeat_failure_stops_worker(monkeypatch, tmp_path):
    async def work(tasks):
        await asyncio.Event().wait()

    async def heartbeat(path):
        raise ConnectionError("database unavailable")

    monkeypatch.setattr(worker, "run_once", work)
    monkeypatch.setattr(worker, "heartbeat", heartbeat)
    with pytest.raises(ConnectionError):
        await asyncio.wait_for(worker.serve({}, asyncio.Event(), tmp_path / "heartbeat"), timeout=1)


async def test_idle_worker_responds_to_shutdown(monkeypatch, tmp_path):
    stop = asyncio.Event()

    async def work(tasks):
        stop.set()
        return False

    async def heartbeat(path):
        await asyncio.Event().wait()

    monkeypatch.setattr(worker, "run_once", work)
    monkeypatch.setattr(worker, "heartbeat", heartbeat)
    await asyncio.wait_for(worker.serve({}, stop, tmp_path / "heartbeat"), timeout=1)
