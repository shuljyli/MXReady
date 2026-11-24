"""Stream existing CLI output without blocking the UI; stop the whole process tree."""

from __future__ import annotations

import asyncio
import codecs
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolResult:
    return_code: int
    cancelled: bool


async def _stop(process: asyncio.subprocess.Process) -> None:
    if sys.platform != "win32":
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    else:
        # Fixed OS command with a numeric PID; project input is never executed as a shell.
        with suppress(OSError, TimeoutError):
            killer = await asyncio.create_subprocess_exec(
                "taskkill",
                "/PID",
                str(process.pid),
                "/T",
                "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(killer.wait(), timeout=5)
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
    await process.wait()


async def _drain(
    process: asyncio.subprocess.Process,
    on_output: Callable[[str], None],
    truncated_message: str,
) -> int:
    assert process.stdout is not None
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    budget = 256 * 1024
    truncated = False
    while chunk := await process.stdout.read(4096):
        allowed = min(len(chunk), budget)
        if allowed:
            on_output(decoder.decode(chunk[:allowed]))
            budget -= allowed
        if allowed < len(chunk) and not truncated:
            on_output(truncated_message)
            truncated = True
        # Continue draining discarded bytes so a full pipe cannot stall the child.
    tail = decoder.decode(b"", final=True)
    if tail:
        on_output(tail)
    return await process.wait()


async def run_tool(
    arguments: Sequence[str],
    *,
    cwd: Path,
    cancel: asyncio.Event,
    on_output: Callable[[str], None],
    truncated_message: str = "[TRUNCATED: 终端输出已达 256 KiB，完整结果请查看报告文件]",
) -> ToolResult:
    if cancel.is_set():
        return ToolResult(return_code=-1, cancelled=True)
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", NO_COLOR="1")
    launch = asyncio.create_task(
        asyncio.create_subprocess_exec(
            *arguments,
            cwd=cwd,
            env=environment,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=os.name == "posix",
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            if os.name == "nt"
            else 0,
        )
    )
    process: asyncio.subprocess.Process | None = None
    drain: asyncio.Task[int] | None = None
    cancellation: asyncio.Task[bool] | None = None
    completed = False
    try:
        # Shield creation so cancellation cannot lose a process created just before assignment.
        process = await asyncio.shield(launch)
        drain = asyncio.create_task(_drain(process, on_output, truncated_message))
        cancellation = asyncio.create_task(cancel.wait())
        done, _ = await asyncio.wait({drain, cancellation}, return_when=asyncio.FIRST_COMPLETED)
        cancelled = cancellation in done
        if cancelled:
            await _stop(process)
        code = await drain
        completed = True
        return ToolResult(return_code=code, cancelled=cancelled)
    finally:
        if process is None:
            process = await launch
        if not completed:
            await _stop(process)
        if cancellation is not None:
            cancellation.cancel()
            with suppress(asyncio.CancelledError):
                await cancellation
        if drain is not None:
            with suppress(asyncio.CancelledError):
                await drain
