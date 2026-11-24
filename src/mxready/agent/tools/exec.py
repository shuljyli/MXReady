"""Approval-gated command execution without a shell."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import IO

from mxready.agent.permissions import ApprovalRequest, PermissionManager
from mxready.agent.tools.base import ToolError, WorkspaceGuard, int_argument, text_argument
from mxready.sanitize import safe_text

MAX_ARGS = 32
MAX_ARG = 4096
MAX_ARGV_CHARS = 16_384
MAX_STREAM = 16 * 1024
MAX_OUTPUT = 40 * 1024
SHELL_HOSTS = frozenset(
    {
        "sh",
        "bash",
        "zsh",
        "dash",
        "fish",
        "ksh",
        "csh",
        "tcsh",
        "cmd",
        "powershell",
        "pwsh",
        "env",
        "xargs",
        "sudo",
        "su",
        "runas",
        "wsl",
        "start",
        "nohup",
    }
)
_SENSITIVE_ENV = ("key", "token", "secret", "password", "credential", "authorization")


def _command_name(value: str) -> str:
    name = Path(value).name.casefold()
    if name.endswith(".exe"):
        name = name[:-4]
    return name


def _validate_argv(arguments: dict[str, object]) -> list[str]:
    value = arguments.get("argv")
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ARGS:
        raise ToolError(f"argv must be an array of 1-{MAX_ARGS} strings")
    argv: list[str] = []
    total = 0
    for item in value:
        if not isinstance(item, str) or not item:
            raise ToolError("Every argv item must be a non-empty string")
        if len(item) > MAX_ARG:
            raise ToolError("An argv item is too long")
        if "\x00" in item:
            raise ToolError("argv items must not contain NUL")
        total += len(item)
        argv.append(item)
    if total > MAX_ARGV_CHARS:
        raise ToolError("The command is too long")
    if _command_name(argv[0]) in SHELL_HOSTS:
        raise ToolError("Shell hosts are not allowed; pass a program and arguments directly")
    return argv


def _safe_environment() -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        folded = key.casefold()
        if folded == "mxready_agent_api_key":
            continue
        if any(marker in folded for marker in _SENSITIVE_ENV):
            continue
        env[key] = value
    return env


def _drain(stream: IO[bytes] | None, buffer: bytearray, flags: dict[str, bool], name: str) -> None:
    if stream is None:
        return
    reader = stream.read
    while True:
        try:
            chunk = reader(4096)
        except (OSError, ValueError):
            break
        if not chunk:
            break
        remaining = MAX_STREAM - len(buffer)
        if remaining > 0:
            buffer.extend(chunk[:remaining])
        if len(chunk) > remaining:
            flags[name] = True


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        with contextlib.suppress(OSError, subprocess.SubprocessError):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    else:
        with contextlib.suppress(OSError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    with contextlib.suppress(OSError):
        process.kill()


def _decode(buffer: bytearray, truncated: bool) -> str:
    text = safe_text(buffer.decode("utf-8", errors="replace"))
    if truncated:
        text += "\n[stream truncated]"
    return text


class RunCommandTool:
    name = "run_command"
    description = (
        "Run one program with an argument array (never a shell). Requires elevated "
        "permissions and one-time user approval. Returns bounded stdout/stderr."
    )
    parameters = {
        "type": "object",
        "properties": {
            "argv": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": MAX_ARGS,
            },
            "cwd": {"type": "string", "description": "Workspace-relative directory"},
            "timeout": {"type": "integer", "minimum": 1, "maximum": 600},
        },
        "required": ["argv"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        guard: WorkspaceGuard,
        permissions: PermissionManager,
        cancel_provider: Callable[[], threading.Event | None] | None = None,
    ) -> None:
        self.guard = guard
        self.permissions = permissions
        self.cancel_provider = cancel_provider

    def run(self, arguments: dict[str, object]) -> str:
        argv = _validate_argv(arguments)
        cwd_value = text_argument(arguments, "cwd", required=False, limit=4096)
        cwd = self.guard.resolve(cwd_value, must_exist=True, default_root=True)
        if not cwd.is_dir():
            raise ToolError("cwd must be a directory")
        timeout = int_argument(arguments, "timeout", default=60, minimum=1, maximum=600)
        self.permissions.require(
            ApprovalRequest(
                tool=self.name,
                summary=f"run {argv[0]}",
                detail=(
                    f"argv: {' '.join(argv)[:900]}\ncwd: {cwd}\ntimeout: {timeout}s"
                ),
            )
        )
        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            process = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=_safe_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=os.name != "nt",
                creationflags=creationflags,
            )
        except OSError as error:
            raise ToolError(f"Cannot start the command: {error}") from error
        stdout = bytearray()
        stderr = bytearray()
        truncated = {"stdout": False, "stderr": False}
        threads = [
            threading.Thread(
                target=_drain,
                args=(process.stdout, stdout, truncated, "stdout"),
                daemon=True,
            ),
            threading.Thread(
                target=_drain,
                args=(process.stderr, stderr, truncated, "stderr"),
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()
        timed_out = False
        cancelled = False
        deadline = time.monotonic() + timeout
        cancel = self.cancel_provider() if self.cancel_provider is not None else None
        while process.poll() is None:
            if cancel is not None and cancel.is_set():
                cancelled = True
                _terminate_tree(process)
                break
            if time.monotonic() > deadline:
                timed_out = True
                _terminate_tree(process)
                break
            time.sleep(0.05)
        try:
            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _terminate_tree(process)
            return_code = process.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
        result = [
            f"exit code: {return_code}",
        ]
        if timed_out:
            result.append(f"[timed out after {timeout}s]")
        if cancelled:
            result.append("[cancelled]")
        result.extend(
            [
                "--- stdout ---",
                _decode(stdout, truncated["stdout"]),
                "--- stderr ---",
                _decode(stderr, truncated["stderr"]),
            ]
        )
        output = "\n".join(result)
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + "\n[output truncated]"
        return output
