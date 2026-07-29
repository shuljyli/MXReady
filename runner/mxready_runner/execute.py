from __future__ import annotations

import hashlib
import json
import shlex
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from subprocess import TimeoutExpired

from mxready_runner import __version__
from mxready_runner.inspect import CommandRunner, collect_environment, run_command
from mxready_runner.redact import sanitize_output
from mxready_runner.schema import CommandResult, RunResult, load_manifest


def run_manifest(
    manifest_path: Path,
    *,
    approve: Callable[[list[str]], bool],
    command_runner: CommandRunner = run_command,
) -> RunResult:
    manifest = load_manifest(manifest_path)
    started_at = _utc_now()
    checks = collect_environment(command_runner, manifest.checks)
    fingerprint = environment_fingerprint(checks)
    reviewed_commands = [shlex.join(item.command) for item in manifest.project_commands]

    if reviewed_commands and not approve(reviewed_commands):
        return RunResult(
            schema_version="1.0",
            scan_id=manifest.scan_id,
            repository_commit=manifest.repository_commit,
            runner_version=__version__,
            environment_fingerprint=fingerprint,
            checks=checks,
            commands=[],
            started_at=started_at,
            finished_at=_utc_now(),
            overall_status="cancelled",
        )

    results: list[CommandResult] = []
    for command in manifest.project_commands:
        command_started = time.monotonic()
        try:
            process = command_runner(
                command.command,
                timeout=command.timeout_seconds,
            )
            command_status = "passed" if process.returncode == 0 else "failed"
            result = CommandResult(
                id=command.id,
                command=_sanitize_command(command.command),
                timeout_seconds=command.timeout_seconds,
                status=command_status,
                return_code=process.returncode,
                stdout=sanitize_output(process.stdout),
                stderr=sanitize_output(process.stderr),
                duration_ms=_duration_ms(command_started),
            )
        except TimeoutExpired as error:
            result = CommandResult(
                id=command.id,
                command=_sanitize_command(command.command),
                timeout_seconds=command.timeout_seconds,
                status="timeout",
                return_code=None,
                stdout=sanitize_output(_timeout_stream(error.stdout)),
                stderr=sanitize_output(_timeout_stream(error.stderr)),
                duration_ms=_duration_ms(command_started),
            )
        except OSError as error:
            result = CommandResult(
                id=command.id,
                command=_sanitize_command(command.command),
                timeout_seconds=command.timeout_seconds,
                status="failed",
                return_code=None,
                stdout="",
                stderr=sanitize_output(str(error)),
                duration_ms=_duration_ms(command_started),
            )
        results.append(result)

    overall_status = "passed" if all(item.status == "passed" for item in results) else "failed"
    return RunResult(
        schema_version="1.0",
        scan_id=manifest.scan_id,
        repository_commit=manifest.repository_commit,
        runner_version=__version__,
        environment_fingerprint=fingerprint,
        checks=checks,
        commands=results,
        started_at=started_at,
        finished_at=_utc_now(),
        overall_status=overall_status,
    )


def environment_fingerprint(checks) -> str:
    public_summary = [
        {
            "id": item.id,
            "status": item.status,
            "return_code": item.return_code,
            "stdout": item.stdout,
            "stderr": item.stderr,
        }
        for item in checks
    ]
    payload = json.dumps(
        public_summary,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _duration_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1_000))


def _timeout_stream(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _sanitize_command(command: list[str]) -> list[str]:
    return [sanitize_output(argument) for argument in command]
