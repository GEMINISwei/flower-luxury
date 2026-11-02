from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app import jobs
from shared.jobs import maintenance

pytestmark = pytest.mark.asyncio


async def test_status_command_reports_only_safe_queue_metadata(monkeypatch, capsys):
    class Engine:
        async def dispose(self):
            pass

    @asynccontextmanager
    async def scope():
        yield

    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://private-credential/test")
    monkeypatch.setattr(jobs, "create_engine", lambda _url: Engine())
    monkeypatch.setattr(jobs, "configure_session_factory", lambda _engine: None)
    monkeypatch.setattr(jobs, "session_scope", scope)
    monkeypatch.setattr(jobs, "job_overview", AsyncMock(return_value=maintenance.JobOverview(
        queues=[maintenance.QueueReport(queue="images", pending=2, ready=1,
                                         oldest_wait_seconds=60)])))
    await jobs.run("status")
    output = capsys.readouterr().out
    assert '"images"' in output and '"pending":2' in output
    assert "private-credential" not in output
