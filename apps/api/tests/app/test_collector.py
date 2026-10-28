import asyncio
import signal

import pytest

from app import collector
from shared.jobs.contracts import Job, TaskSpec
from shared.module import ModuleManifest

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("url", [None, "postgresql://private-credential@localhost/db"])
async def test_collector_rejects_missing_or_invalid_database_setting(monkeypatch, url):
    if url is None:
        monkeypatch.delenv("POSTGRES_URL", raising=False)
    else:
        monkeypatch.setenv("POSTGRES_URL", url)

    def create_engine(value):
        pytest.fail("invalid configuration must not create an engine")

    monkeypatch.setattr(collector, "create_engine", create_engine)
    with pytest.raises(SystemExit, match="POSTGRES_URL") as error:
        await collector.run()
    assert "private-credential" not in str(error.value)


@pytest.mark.parametrize("failure", [False, True])
async def test_collector_loads_tasks_and_disposes_engine_on_exit(monkeypatch, failure):
    seen: dict[str, object] = {}

    class Engine:
        async def dispose(self):
            seen["disposed"] = True

    async def handler(job: Job) -> None:
        pass

    task = TaskSpec("example.process", handler)
    engine = Engine()
    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setattr(collector, "ENABLED_MODULES", (ModuleManifest("example", tasks=(task,)),))
    monkeypatch.setattr(collector, "create_engine", lambda _url: engine)
    monkeypatch.setattr(collector, "configure_session_factory",
                        lambda value: seen.update(engine=value))
    signals = []
    monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler",
                        lambda name, callback: signals.append((name, callback)))

    async def serve(tasks, stop, path):
        assert tasks == {task.name: task}
        assert seen["engine"] is engine
        assert {name for name, _ in signals} == {signal.SIGINT, signal.SIGTERM}
        for _, callback in signals:
            callback()
        assert stop.is_set()
        if failure:
            raise ConnectionError("database unavailable")

    monkeypatch.setattr(collector, "serve", serve)
    if failure:
        with pytest.raises(ConnectionError):
            await collector.run()
    else:
        await collector.run()
    assert seen["disposed"]
