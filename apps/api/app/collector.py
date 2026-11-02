"""line-collector 的程序入口, 與 API 共用 image 及模組清單。"""

import asyncio
import logging
import os
import signal
import sys

from shared.db.session import configure_session_factory, create_engine
from shared.jobs.health import HEARTBEAT_PATH, is_healthy
from shared.jobs.maintenance import CLEANUP_TASK
from shared.jobs.registry import collect_tasks
from shared.jobs.worker import serve

from .registry import ENABLED_MODULES


async def run() -> None:
    url = os.environ.get("POSTGRES_URL", "")
    if not url.startswith("postgresql+asyncpg://"):
        raise SystemExit("line-collector 需要 POSTGRES_URL (見 .env / .env.example)")
    tasks = {**collect_tasks(ENABLED_MODULES), CLEANUP_TASK.name: CLEANUP_TASK}
    engine = create_engine(url)
    configure_session_factory(engine)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(name, stop.set)
    logging.info("line-collector started registered_tasks=%d", len(tasks))
    try:
        await serve(tasks, stop, HEARTBEAT_PATH)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if sys.argv[1:] == ["--healthcheck"]:
        raise SystemExit(0 if is_healthy() else 1)
    if sys.argv[1:]:
        raise SystemExit("用法: python -m app.collector [--healthcheck]")
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run())
    except Exception as error:
        # 不印外部錯誤的 traceback, 其中可能含連線憑證與任務內容。
        logging.error("line-collector stopped error_type=%s", type(error).__name__)
        raise SystemExit(1) from None
