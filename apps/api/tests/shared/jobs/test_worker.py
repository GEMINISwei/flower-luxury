import asyncio
from contextlib import asynccontextmanager

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


async def test_heartbeat_updates_only_after_successful_database_probe(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat"
    statements = []

    class StopHeartbeatError(Exception):
        pass

    class Session:
        async def execute(self, statement):
            statements.append(str(statement))
            assert not path.exists()

    @asynccontextmanager
    async def session_scope():
        yield Session()

    async def pause(seconds):
        assert seconds == 5
        assert path.is_file()
        raise StopHeartbeatError

    monkeypatch.setattr(worker, "session_scope", session_scope)
    monkeypatch.setattr(worker.asyncio, "sleep", pause)
    with pytest.raises(StopHeartbeatError):
        await worker.heartbeat(path)
    assert statements == ["SELECT 1"]


async def test_failed_database_probe_does_not_publish_heartbeat(monkeypatch, tmp_path):
    path = tmp_path / "heartbeat"

    class Session:
        async def execute(self, statement):
            raise ConnectionError("database unavailable")

    @asynccontextmanager
    async def session_scope():
        yield Session()

    monkeypatch.setattr(worker, "session_scope", session_scope)
    with pytest.raises(ConnectionError):
        await worker.heartbeat(path)
    assert not path.exists()
