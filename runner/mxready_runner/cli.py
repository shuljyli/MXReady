from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from mxready_runner import __version__
from mxready_runner.execute import environment_fingerprint, run_manifest
from mxready_runner.inspect import collect_environment
from mxready_runner.schema import ManifestError, RunResult, load_manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.action == "inspect":
            result = _inspect_manifest(arguments.manifest)
        else:
            result = run_manifest(
                arguments.manifest,
                approve=_interactive_approval,
            )
        _write_result(arguments.output, result)
    except (ManifestError, OSError) as error:
        print(f"MXReady runner error: {error}", file=sys.stderr)
        return 2
    if result.overall_status == "passed":
        return 0
    return 2 if result.overall_status == "cancelled" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mxready-runner",
        description="Run reviewed MXReady checks on a user-controlled host.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("inspect", "run"):
        subparser = subparsers.add_parser(action)
        subparser.add_argument("--manifest", type=Path, required=True)
        subparser.add_argument("--output", type=Path, required=True)
    return parser


def _inspect_manifest(path: Path) -> RunResult:
    manifest = load_manifest(path)
    started = datetime.now(UTC).isoformat()
    checks = collect_environment(checks=manifest.checks)
    return RunResult(
        schema_version="1.0",
        scan_id=manifest.scan_id,
        repository_commit=manifest.repository_commit,
        runner_version=__version__,
        environment_fingerprint=environment_fingerprint(checks),
        checks=checks,
        commands=[],
        started_at=started,
        finished_at=datetime.now(UTC).isoformat(),
        overall_status="passed",
    )


def _interactive_approval(commands: list[str]) -> bool:
    print("Project commands proposed by the MXReady manifest:")
    for index, command in enumerate(commands, start=1):
        print(f"  {index}. {command}")
    response = input("Run these commands on this host? Type 'yes' to continue: ")
    return response.strip().casefold() == "yes"


def _write_result(path: Path, result: RunResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.to_json() + "\n", encoding="utf-8")
