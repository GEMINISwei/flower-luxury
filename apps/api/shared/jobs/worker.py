import asyncio
import logging
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from shared.db.session import active_session, session_scope
from shared.time import utc_now

from .contracts import TaskSpec
from .model import JobTable
from .notifications import JobNotifications
from .runner import run_once
from .scheduling import schedule_tasks
from .workers import beat_worker, recover_workers, register_worker, retire_worker

logger = logging.getLogger(__name__)


async def heartbeat(
    path: Path, worker_id: UUID, tasks: Mapping[str, TaskSpec] | None = None,
) -> None:
    while True:
        async with session_scope():
            if not await beat_worker(worker_id):
                raise RuntimeError("worker heartbeat ownership lost")
            await recover_workers()
            await schedule_tasks(tasks or {})
        await asyncio.to_thread(path.touch)
        await asyncio.sleep(5)


async def _next_due(tasks: Mapping[str, TaskSpec]) -> float:
    async with session_scope():
        due = await active_session().scalar(select(func.min(JobTable.available_at)).where(
            JobTable.task_name.in_(tasks), JobTable.status == "pending",
        ))
    return 30 if due is None else max(0.1, min(30, (due - utc_now()).total_seconds()))


async def _consume(
    tasks: Mapping[str, TaskSpec], stop: asyncio.Event, worker_id: UUID,
    database_url: str | None,
) -> None:
    async with JobNotifications(database_url) as notifications:
        while not stop.is_set():
            # 先訂閱再查詢, 避免查完沒工作到開始等待之間漏掉通知。
            await notifications.prepare()
            if not await run_once(tasks, worker_id=worker_id) and not stop.is_set():
                await notifications.wait(stop, delay_seconds=await _next_due(tasks))


async def _drain(consumers: list[asyncio.Task], pulse: asyncio.Task, seconds: float) -> None:
    drained = asyncio.gather(*consumers)
    done, _ = await asyncio.wait([drained, pulse], timeout=seconds,
                                return_when=asyncio.FIRST_COMPLETED)
    if pulse in done:
        await pulse
    if not drained.done():
        drained.cancel()
    await asyncio.gather(drained, return_exceptions=True)


async def _retire(worker_id: UUID) -> None:
    try:
        async with session_scope():
            await retire_worker(worker_id)
    except Exception as error:
        logger.warning("worker retirement failed error_type=%s", type(error).__name__)


async def serve(
    tasks: Mapping[str, TaskSpec], stop: asyncio.Event, heartbeat_path: Path, *,
    database_url: str | None = None, shutdown_seconds: float = 75,
) -> None:
    worker_id = uuid4()
    await asyncio.to_thread(heartbeat_path.unlink, missing_ok=True)
    async with session_scope() as session:
        await register_worker(worker_id)
        if database_url is None and session is not None and session.bind is not None:
            bind = session.bind
            engine = bind if isinstance(bind, AsyncEngine) else bind.engine
            database_url = engine.url.render_as_string(hide_password=False)
    queues: dict[str, dict[str, TaskSpec]] = {}
    for name, spec in tasks.items():
        queues.setdefault(spec.queue, {})[name] = spec
    consumers = [asyncio.create_task(_consume(selected, stop, worker_id, database_url))
                 for selected in (queues or {"general": {}}).values()]
    pulse = asyncio.create_task(heartbeat(heartbeat_path, worker_id, tasks))
    stopped = asyncio.create_task(stop.wait())
    running = [*consumers, pulse, stopped]
    try:
        done, _ = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            await task
        if stopped in done:
            await _drain(consumers, pulse, shutdown_seconds)
    finally:
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)
        await _retire(worker_id)
        await asyncio.to_thread(heartbeat_path.unlink, missing_ok=True)
