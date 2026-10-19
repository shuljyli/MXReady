from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from subprocess import CompletedProcess, TimeoutExpired
from typing import Literal

from mxready_runner.contracts import DEFAULT_CHECKS as DEFAULT_CHECKS
from mxready_runner.process import run_command as run_command
from mxready_runner.redact import sanitize_output
from mxready_runner.schema import CheckResult, CommandSpec

CommandRunner = Callable[..., CompletedProcess[str]]


def collect_environment(
    command_runner: CommandRunner = run_command,
    checks: Iterable[CommandSpec] | None = None,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    selected_checks = checks if checks is not None else DEFAULT_CHECKS
    for check in selected_checks:
        started = time.monotonic()
        try:
            process = command_runner(
                check.command,
                timeout=check.timeout_seconds,
            )
            status: Literal["passed", "failed"] = "passed" if process.returncode == 0 else "failed"
            result = CheckResult(
                id=check.id,
                command=_sanitize_command(check.command),
                status=status,
                return_code=process.returncode,
                stdout=_sanitize_check_stdout(check.id, process.stdout),
                stderr=sanitize_output(process.stderr),
                duration_ms=_duration_ms(started),
            )
        except (OSError, TimeoutExpired) as error:
            result = CheckResult(
                id=check.id,
                command=_sanitize_command(check.command),
                status="unavailable",
                return_code=None,
                stdout="",
                stderr=sanitize_output(str(error)),
                duration_ms=_duration_ms(started),
            )
        results.append(result)
    return results


def environment_checks_passed(results: Iterable[CheckResult]) -> bool:
    return all(result.status == "passed" for result in results)


def _duration_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1_000))


def _sanitize_check_stdout(check_id: str, value: str | None) -> str:
    output = value or ""
    if check_id == "uname":
        lines = output.splitlines(keepends=True)
        redacted_lines = []
        for line in lines:
            parts = line.split(maxsplit=2)
            if len(parts) >= 2:
                remainder = f" {parts[2]}" if len(parts) == 3 else ""
                newline = "\n" if line.endswith("\n") else ""
                redacted_lines.append(f"{parts[0]} [HOST]{remainder.rstrip()}{newline}")
            else:
                redacted_lines.append(line)
        output = "".join(redacted_lines)
    return sanitize_output(output)


def _sanitize_command(command: Sequence[str]) -> list[str]:
    return [sanitize_output(argument) for argument in command]
