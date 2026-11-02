import asyncio
import multiprocessing
from collections.abc import Callable
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from typing import cast


class ProcessExecutionError(Exception):
    pass


def _execute(sender: Connection, handler: Callable, arguments: tuple[object, ...]) -> None:
    try:
        sender.send((True, handler(*arguments)))
    except Exception:
        # 子行程的例外可能帶著圖片內容或路徑, 只回傳安全分類。
        sender.send((False, None))
    finally:
        sender.close()


async def _stop(process: BaseProcess) -> None:
    if process.is_alive():
        process.terminate()
    await asyncio.to_thread(process.join, 1)
    if process.is_alive():
        process.kill()
        await asyncio.to_thread(process.join)
    process.close()


async def run_process[T](
    handler: Callable[..., T], *arguments: object, timeout_seconds: float = 45,
) -> T:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_execute, args=(sender, handler, arguments), daemon=True)
    started = False
    try:
        async with asyncio.timeout(timeout_seconds):
            process.start()
            started = True
            sender.close()
            while not await asyncio.to_thread(receiver.poll, 0.1):
                if not process.is_alive():
                    raise ProcessExecutionError("process_exited")
            try:
                success, result = await asyncio.to_thread(receiver.recv)
            except (EOFError, OSError) as error:
                raise ProcessExecutionError("process_exited") from error
            if not success:
                raise ProcessExecutionError("process_failed")
            return cast(T, result)
    finally:
        if started:
            await _stop(process)
        receiver.close()
        sender.close()
