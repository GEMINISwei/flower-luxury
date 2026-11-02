from datetime import timedelta

import pytest
from sqlalchemy import select

from shared.db.session import session_scope
from shared.jobs import scheduling
from shared.jobs.contracts import TaskSpec
from shared.jobs.model import JobTable
from shared.time import utc_now
from tests.shared.jobs.test_queue import database as database
from tests.shared.jobs.test_queue import noop

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_periodic_schedule_is_idempotent_and_skips_missed_intervals():
    task = TaskSpec("periodic.cleanup", noop, interval_seconds=60)
    now = utc_now()
    async with session_scope() as session:
        await scheduling.schedule_tasks({task.name: task}, now=now)
        await scheduling.schedule_tasks({task.name: task}, now=now)
        rows = list(await session.scalars(select(JobTable)))
        assert len(rows) == 1
        await scheduling.schedule_tasks({task.name: task}, now=now + timedelta(hours=1))
        assert len(list(await session.scalars(select(JobTable)))) == 2
