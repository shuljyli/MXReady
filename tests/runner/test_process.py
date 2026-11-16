import sys
import time
from subprocess import TimeoutExpired

import pytest

from mxready_runner.process import run_command
from mxready_runner.redact import MAX_OUTPUT_BYTES


def test_noisy_commands_are_drained_with_bounded_capture():
    result = run_command(
        [sys.executable, "-c", "import os; os.write(1,b'x'*2000000); os.write(2,b'y'*2000000)"],
        timeout=10,
    )
    assert result.returncode == 0
    for output in (result.stdout, result.stderr):
        assert len(output.encode()) <= MAX_OUTPUT_BYTES
        assert output.endswith("[TRUNCATED]")


def test_timeout_preserves_partial_output_and_stops_the_command():
    with pytest.raises(TimeoutExpired) as raised:
        run_command(
            [sys.executable, "-c", "import time; print('started',flush=True); time.sleep(30)"],
            timeout=1,
        )
    assert "started" in raised.value.stdout


def test_timeout_includes_children_after_the_parent_exits(tmp_path):
    marker = tmp_path / "child-finished.txt"
    child = f"import time; from pathlib import Path; time.sleep(4); Path({str(marker)!r}).touch()"
    parent = (
        f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "print('parent-finished',flush=True)"
    )
    started = time.monotonic()
    with pytest.raises(TimeoutExpired) as raised:
        run_command([sys.executable, "-c", parent], timeout=1)
    assert time.monotonic() - started < 3
    assert "parent-finished" in raised.value.stdout
    time.sleep(4)
    assert not marker.exists(), "A timed-out descendant must not keep running"


def test_successful_children_are_drained_after_parent_exit():
    child = "import time; time.sleep(0.4); print('child-finished',flush=True)"
    parent = (
        f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "print('parent-finished',flush=True)"
    )
    result = run_command([sys.executable, "-c", parent], timeout=5)
    assert result.returncode == 0
    assert "parent-finished" in result.stdout
    assert "child-finished" in result.stdout
