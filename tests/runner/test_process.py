import sys
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
