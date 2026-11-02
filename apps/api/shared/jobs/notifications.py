import asyncio
from types import TracebackType
from typing import Any

import asyncpg


class JobNotifications:
    def __init__(self, url: str | None) -> None:
        self.url = url
        self.event = asyncio.Event()
        self.connection: Any = None

    async def __aenter__(self) -> JobNotifications:
        return self

    async def __aexit__(self, kind: type[BaseException] | None,
                        error: BaseException | None, traceback: TracebackType | None) -> None:
        if self.connection is not None:
            await self.connection.close()

    def _notified(self, *_args: object) -> None:
        self.event.set()

    async def prepare(self) -> None:
        self.event.clear()
        if self.url is None or (self.connection and not self.connection.is_closed()):
            return
        try:
            self.connection = await asyncpg.connect(self.url.replace("+asyncpg", ""), timeout=5)
            await self.connection.add_listener("background_jobs", self._notified)
            self.connection.add_termination_listener(self._notified)
        except (OSError, asyncpg.PostgresError, TimeoutError):
            if self.connection is not None:
                await self.connection.close()
            self.connection = None

    async def wait(self, stop: asyncio.Event, *, delay_seconds: float) -> None:
        pending = [asyncio.create_task(self.event.wait()), asyncio.create_task(stop.wait())]
        try:
            await asyncio.wait(pending, timeout=delay_seconds, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
