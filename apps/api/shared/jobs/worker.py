import asyncio
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import text

from shared.db.session import session_scope

from .contracts import TaskSpec
from .runner import run_once


async def heartbeat(path: Path) -> None:
    while True:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        await asyncio.to_thread(path.touch)
        await asyncio.sleep(5)


async def _consume(tasks: Mapping[str, TaskSpec], stop: asyncio.Event) -> None:
    while not stop.is_set():
        if not await run_once(tasks):
            try:
                await asyncio.wait_for(stop.wait(), timeout=1)
            except TimeoutError:
                pass


async def serve(tasks: Mapping[str, TaskSpec], stop: asyncio.Event, heartbeat_path: Path) -> None:
    await asyncio.to_thread(heartbeat_path.unlink, missing_ok=True)
    running = [
        asyncio.create_task(_consume(tasks, stop)),
        asyncio.create_task(heartbeat(heartbeat_path)),
        asyncio.create_task(stop.wait()),
    ]
    try:
        done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            await task
    finally:
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        await asyncio.to_thread(heartbeat_path.unlink, missing_ok=True)
