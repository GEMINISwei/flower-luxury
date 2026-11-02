from collections.abc import Mapping
from datetime import UTC, datetime

from shared.time import utc_now

from .contracts import TaskSpec
from .queue import enqueue_job


async def schedule_tasks(tasks: Mapping[str, TaskSpec], *, now: datetime | None = None) -> None:
    now = now or utc_now()
    for task in tasks.values():
        if task.interval_seconds is None:
            continue
        # 僅補目前區間, 避免長時間停機後一次排入數千個清理工作。
        slot = int(now.replace(tzinfo=UTC).timestamp() // task.interval_seconds)
        await enqueue_job(task.name, {}, queue=task.queue, max_attempts=task.max_attempts,
                          idempotency_key=f"schedule:{slot}")
