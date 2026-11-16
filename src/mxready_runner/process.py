"""Execute reviewed argument arrays while bounding captured output in memory."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from threading import Thread
from typing import BinaryIO

from mxready_runner.redact import MAX_OUTPUT_BYTES


class _Capture:
    def __init__(self) -> None:
        self.data = bytearray()
        self.truncated = False

    def read(self, stream: BinaryIO) -> None:
        try:
            while chunk := os.read(stream.fileno(), 4096):
                remaining = MAX_OUTPUT_BYTES - len(self.data)
                self.data.extend(chunk[:remaining])
                self.truncated |= len(chunk) > remaining
        except OSError:
            pass  # The owning process may close the pipe during bounded cleanup.
        finally:
            stream.close()

    def text(self) -> str:
        suffix = b"[TRUNCATED]" if self.truncated else b""
        return (
            bytes(self.data[: MAX_OUTPUT_BYTES - len(suffix)]).decode(
                "utf-8",
                errors="replace",
            )
            + suffix.decode()
        )


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if sys.platform != "win32":
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    else:
        # Killing our supervisor closes its job handle and terminates every descendant.
        if process.poll() is None:
            process.kill()


def run_command(
    command: Sequence[str],
    *,
    timeout: int,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
) -> CompletedProcess[str]:
    deadline = time.monotonic() + timeout
    actual_command = list(command)
    if sys.platform == "win32":
        actual_command = [
            sys.executable,
            "-I",
            "-S",
            str(Path(__file__).with_name("_windows_job.py")),
            *actual_command,
        ]
    with subprocess.Popen(
        actual_command,
        shell=False,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=os.name == "posix",
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
    ) as process:
        assert process.stdout is not None and process.stderr is not None
        stdout, stderr = _Capture(), _Capture()
        readers = [
            Thread(target=stdout.read, args=(process.stdout,), daemon=True),
            Thread(target=stderr.read, args=(process.stderr,), daemon=True),
        ]
        for reader in readers:
            reader.start()
        timed_out = False
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
            for reader in readers:
                reader.join(timeout=max(0, deadline - time.monotonic()))
            timed_out = any(reader.is_alive() for reader in readers)
        except TimeoutExpired:
            timed_out = True
        finally:
            if timed_out:
                _terminate_tree(process)
                process.wait(timeout=5)
                for reader in readers:
                    reader.join(timeout=1)
        if timed_out:
            raise TimeoutExpired(command, timeout, output=stdout.text(), stderr=stderr.text())
        return CompletedProcess(list(command), process.returncode, stdout.text(), stderr.text())
