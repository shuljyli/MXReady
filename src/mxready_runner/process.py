"""Execute reviewed argument arrays while bounding captured output in memory."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Sequence
from contextlib import suppress
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
            while chunk := stream.read(4096):
                remaining = MAX_OUTPUT_BYTES - len(self.data)
                self.data.extend(chunk[:remaining])
                self.truncated |= len(chunk) > remaining
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
    if os.name == "posix":
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    else:
        # Fixed system command, never interpolated project input or a shell command.
        with suppress(OSError, TimeoutExpired):
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
        if process.poll() is None:
            process.kill()


def run_command(command: Sequence[str], *, timeout: int) -> CompletedProcess[str]:
    with subprocess.Popen(
        list(command),
        shell=False,
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
            process.wait(timeout=timeout)
        except TimeoutExpired:
            timed_out = True
            _terminate_tree(process)
            process.wait()
        finally:
            for reader in readers:
                reader.join(timeout=0.1)
            if any(reader.is_alive() for reader in readers):
                _terminate_tree(process)
                for reader in readers:
                    reader.join(timeout=5)
        if timed_out:
            raise TimeoutExpired(command, timeout, output=stdout.text(), stderr=stderr.text())
        return CompletedProcess(list(command), process.returncode, stdout.text(), stderr.text())
