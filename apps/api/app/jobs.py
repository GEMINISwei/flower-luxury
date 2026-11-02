"""背景工作維運入口, 僅輸出安全 metadata。"""

import argparse
import asyncio
import os
from uuid import UUID

from shared.db.session import configure_session_factory, create_engine, session_scope
from shared.jobs.maintenance import CLEANUP_TASK, job_overview, retry_dead_job
from shared.jobs.registry import collect_tasks

from .registry import ENABLED_MODULES


async def run(command: str, job_id: UUID | None = None) -> None:
    url = os.environ.get("POSTGRES_URL", "")
    if not url.startswith("postgresql+asyncpg://"):
        raise SystemExit("需要 POSTGRES_URL / POSTGRES_URL is required")
    engine = create_engine(url)
    configure_session_factory(engine)
    try:
        async with session_scope():
            if command == "status":
                print((await job_overview()).model_dump_json())
            elif command == "retry" and job_id is not None:
                tasks = {**collect_tasks(ENABLED_MODULES), CLEANUP_TASK.name: CLEANUP_TASK}
                if not await retry_dead_job(job_id, tasks):
                    raise SystemExit("工作不可重排 / Job cannot be requeued")
                print("已重新排入 / Job requeued")
            else:
                raise SystemExit("無效指令 / Invalid command")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="背景工作維運 / Background job maintenance")
    parser.add_argument("command", choices=["status", "retry"])
    parser.add_argument("job_id", nargs="?", type=UUID)
    args = parser.parse_args()
    asyncio.run(run(args.command, args.job_id))
