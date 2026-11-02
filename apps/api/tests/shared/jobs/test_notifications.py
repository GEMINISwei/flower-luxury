import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest

from shared.jobs import notifications

pytestmark = pytest.mark.asyncio


class Connection:
    def __init__(self):
        self.closed = False
        self.listener: Callable[..., None] | None = None
        self.termination: Callable[..., None] | None = None

    async def add_listener(self, channel, callback):
        assert channel == "background_jobs"
        self.listener = callback

    def add_termination_listener(self, callback):
        self.termination = callback

    def is_closed(self):
        return self.closed

    async def close(self):
        self.closed = True


async def test_notification_wakes_waiter_and_connection_closes(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(notifications.asyncpg, "connect", AsyncMock(return_value=connection))
    async with notifications.JobNotifications("postgresql+asyncpg://test") as listener:
        await listener.prepare()
        assert connection.listener is not None
        connection.listener(None, 1, "background_jobs", "")
        await asyncio.wait_for(listener.wait(asyncio.Event(), delay_seconds=30), timeout=1)
    assert connection.closed


async def test_disconnected_listener_reconnects(monkeypatch):
    first, second = Connection(), Connection()
    connect = AsyncMock(side_effect=[first, second])
    monkeypatch.setattr(notifications.asyncpg, "connect", connect)
    async with notifications.JobNotifications("postgresql+asyncpg://test") as listener:
        await listener.prepare()
        first.closed = True
        assert first.termination is not None
        first.termination(first)
        await listener.prepare()
        assert connect.await_count == 2 and second.listener is not None


async def test_listener_failure_preserves_polling_and_later_reconnects(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(notifications.asyncpg, "connect",
                        AsyncMock(side_effect=[OSError(), connection]))
    async with notifications.JobNotifications("postgresql+asyncpg://test") as listener:
        await listener.prepare()
        await listener.wait(asyncio.Event(), delay_seconds=0.01)
        await listener.prepare()
        assert connection.listener is not None
        stop = asyncio.Event()
        stop.set()
        await asyncio.wait_for(listener.wait(stop, delay_seconds=30), timeout=1)
