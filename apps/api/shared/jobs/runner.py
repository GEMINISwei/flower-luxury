import asyncio
import logging
from collections.abc import Mapping
from uuid import UUID

from shared.db.session import session_scope

from .contracts import Job, PermanentJobError, TaskSpec
from .queue import claim_job, complete_job, fail_job

logger = logging.getLogger(__name__)


class LeaseLostError(Exception):
    pass


async def _retry(job: Job, task: TaskSpec, *, permanent: bool = False,
                 error_code: str = "temporary") -> None:
    async with session_scope():
        await fail_job(job, max_attempts=task.max_attempts, permanent=permanent,
                       error_code=error_code)


async def run_once(tasks: Mapping[str, TaskSpec], *, worker_id: UUID) -> bool:
    # 領取先提交, 網路下載期間不持有領取交易的列鎖。
    async with session_scope():
        job = await claim_job(tasks, worker_id=worker_id)
    if job is None:
        return False
    task = tasks[job.task_name]
    logger.info("job started id=%s task=%s attempt=%d queue=%s",
                job.id, job.task_name, job.attempts, task.queue)
    try:
        async with session_scope():
            await asyncio.wait_for(task.handler(job), timeout=task.timeout_seconds)
            if not await complete_job(job):
                # 任務的資料庫寫入也要回滾, 避免過期 worker 寫入舊結果。
                raise LeaseLostError
    except asyncio.CancelledError:
        await _retry(job, task, error_code="cancelled")
        raise
    except Exception as error:
        logger.warning("job failed id=%s task=%s attempt=%d error_type=%s",
                       job.id, job.task_name, job.attempts, type(error).__name__)
        permanent = isinstance(error, PermanentJobError)
        code = "permanent" if permanent else "timeout" if isinstance(error, TimeoutError) \
            else "ownership_lost" if isinstance(error, LeaseLostError) else "temporary"
        await _retry(job, task, permanent=permanent, error_code=code)
    else:
        logger.info("job succeeded id=%s task=%s attempt=%d", job.id, job.task_name, job.attempts)
    return True
