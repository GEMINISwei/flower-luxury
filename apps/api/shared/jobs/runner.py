import asyncio
import logging
from collections.abc import Mapping

from shared.db.session import session_scope

from .contracts import Job, TaskSpec
from .queue import claim_job, complete_job, fail_job

logger = logging.getLogger(__name__)


class LeaseLostError(Exception):
    pass


async def _retry(job: Job, task: TaskSpec) -> None:
    async with session_scope():
        await fail_job(job, max_attempts=task.max_attempts)


async def run_once(tasks: Mapping[str, TaskSpec]) -> bool:
    # 領取先提交, 網路下載期間不持有領取交易的列鎖。
    async with session_scope():
        job = await claim_job(tasks)
    if job is None:
        return False
    task = tasks[job.task_name]
    try:
        async with session_scope():
            await asyncio.wait_for(task.handler(job), timeout=task.timeout_seconds)
            if not await complete_job(job):
                # 任務的資料庫寫入也要回滾, 避免過期 worker 寫入舊結果。
                raise LeaseLostError
    except asyncio.CancelledError:
        await _retry(job, task)
        raise
    except Exception as error:
        logger.warning("job failed id=%s task=%s error_type=%s",
                       job.id, job.task_name, type(error).__name__)
        await _retry(job, task)
    return True
