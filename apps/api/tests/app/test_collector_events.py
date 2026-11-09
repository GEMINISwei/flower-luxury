import asyncio
from dataclasses import dataclass

import pytest

from app import collector
from shared.db.session import active_session, session_scope
from shared.events import Event, EventHandler, publish
from shared.module import ModuleManifest


@dataclass(frozen=True)
class Processed(Event):
    id: int


@pytest.mark.asyncio
async def test_worker_jobs_have_isolated_platform_scopes(monkeypatch, tmp_path):
    sessions = {}
    handled = {}

    async def handle(event: Processed) -> None:
        handled[event.id] = active_session()

    async def execute(id: int) -> None:
        async with session_scope():
            sessions[id] = active_session()
            await publish(Processed(id))
            await asyncio.sleep(0)
            assert active_session() is sessions[id]

    async def serve(tasks, stop, path):
        with pytest.raises(RuntimeError, match="session"):
            active_session()
        await asyncio.gather(execute(1), execute(2))

    monkeypatch.setattr(collector, "ENABLED_MODULES", (
        ModuleManifest("probe", event_handlers=(EventHandler(Processed, handle),)),
    ))
    monkeypatch.setattr(collector, "serve", serve)
    monkeypatch.setattr(asyncio.get_running_loop(), "add_signal_handler", lambda *_args: None)
    await collector.run()
    assert handled == sessions
    assert sessions[1] is not sessions[2]
