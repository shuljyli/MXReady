import asyncio
import sys

from mxready.tui.process import run_tool


def test_tool_streams_output_and_returns_exit_code(tmp_path):
    async def scenario():
        lines = []
        result = await run_tool(
            [sys.executable, "-u", "-c", "print('first', flush=True); raise SystemExit(2)"],
            cwd=tmp_path,
            cancel=asyncio.Event(),
            on_output=lines.append,
        )
        assert result.return_code == 2 and not result.cancelled
        assert "first" in "\n".join(lines)

    asyncio.run(scenario())


def test_tool_cancellation_stops_process_and_keeps_ui_responsive(tmp_path):
    async def scenario():
        cancel = asyncio.Event()
        ready = asyncio.Event()

        def receive(line):
            ready.set()

        task = asyncio.create_task(
            run_tool(
                [
                    sys.executable,
                    "-u",
                    "-c",
                    "import time; print('ready', flush=True); time.sleep(30)",
                ],
                cwd=tmp_path,
                cancel=cancel,
                on_output=receive,
            )
        )
        await asyncio.wait_for(ready.wait(), 5)
        cancel.set()
        result = await asyncio.wait_for(task, 5)
        assert result.cancelled

    asyncio.run(scenario())


def test_tool_bounds_output_and_drains_long_lines(tmp_path):
    async def scenario():
        lines = []
        result = await run_tool(
            [sys.executable, "-c", "print('x' * 600000)"],
            cwd=tmp_path,
            cancel=asyncio.Event(),
            on_output=lines.append,
        )
        assert result.return_code == 0
        assert sum(len(line) for line in lines) < 270000
        assert any("TRUNCATED" in line for line in lines)

    asyncio.run(scenario())


def test_cancellation_terminates_descendants(tmp_path):
    async def scenario():
        marker = tmp_path / "child-survived"
        child = (
            f"import time; from pathlib import Path; time.sleep(1); Path({str(marker)!r}).touch()"
        )
        parent = (
            "import subprocess, sys, time; "
            f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
            "print('spawned', flush=True); time.sleep(30)"
        )
        cancel, ready = asyncio.Event(), asyncio.Event()
        task = asyncio.create_task(
            run_tool(
                [sys.executable, "-u", "-c", parent],
                cwd=tmp_path,
                cancel=cancel,
                on_output=lambda value: ready.set(),
            )
        )
        await asyncio.wait_for(ready.wait(), 5)
        cancel.set()
        assert (await asyncio.wait_for(task, 5)).cancelled
        await asyncio.sleep(1.1)
        assert not marker.exists()

    asyncio.run(scenario())
