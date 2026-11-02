import asyncio
import multiprocessing
import os
import threading
from pathlib import Path

import pytest

from shared.jobs import processes

pytestmark = pytest.mark.asyncio


def calculate(value):
    return {"result": value * 2, "pid": os.getpid()}


def broken():
    raise ValueError("private-image-content")


def stalled(path, ready=None):
    Path(path).write_text(str(os.getpid()))
    if ready is not None:
        ready.set()
    threading.Event().wait()


async def test_cpu_work_runs_in_separate_process():
    result = await processes.run_process(calculate, 21, timeout_seconds=10)
    assert result["result"] == 42 and result["pid"] != os.getpid()
    assert result["pid"] not in {child.pid for child in multiprocessing.active_children()}


async def test_child_error_does_not_expose_contents():
    with pytest.raises(processes.ProcessExecutionError) as error:
        await processes.run_process(broken, timeout_seconds=10)
    assert "private-image-content" not in str(error.value)


async def test_timeout_terminates_child(tmp_path):
    before = {child.pid for child in multiprocessing.active_children()}
    with pytest.raises(TimeoutError):
        await processes.run_process(stalled, str(tmp_path / "started"), timeout_seconds=0.3)
    assert {child.pid for child in multiprocessing.active_children()} == before


async def test_cancellation_terminates_child_and_waits_for_exit(tmp_path):
    started = tmp_path / "started"
    ready = multiprocessing.get_context("spawn").Event()
    running = asyncio.create_task(processes.run_process(stalled, str(started), ready,
                                                        timeout_seconds=10))
    assert await asyncio.to_thread(ready.wait, 5)
    pid = int(started.read_text())
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert pid not in {child.pid for child in multiprocessing.active_children()}
