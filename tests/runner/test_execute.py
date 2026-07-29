from __future__ import annotations

import json
from subprocess import CompletedProcess, TimeoutExpired

from mxready.models import VerificationRun
from mxready_runner.execute import run_manifest


def test_run_refuses_commands_without_explicit_approval(
    manifest_path,
    recording_runner,
) -> None:
    reviewed: list[list[str]] = []

    result = run_manifest(
        manifest_path,
        approve=lambda commands: reviewed.append(commands) or False,
        command_runner=recording_runner,
    )

    assert result.overall_status == "cancelled"
    assert recording_runner.calls == []
    assert reviewed == [["python -m pytest"]]


def test_run_executes_argument_array_and_redacts_bounded_output(
    manifest_path,
    recording_runner,
) -> None:
    result = run_manifest(
        manifest_path,
        approve=lambda commands: True,
        command_runner=recording_runner,
    )

    assert recording_runner.calls == [(["python", "-m", "pytest"], 60)]
    assert result.overall_status == "passed"
    assert result.commands[0].command == ["python", "-m", "pytest"]
    assert result.commands[0].status == "passed"
    assert "secret123" not in result.commands[0].stdout
    assert result.environment_fingerprint.startswith("sha256:")


def test_run_maps_timeout_to_failed_result(manifest_path) -> None:
    def timeout_runner(command, *, timeout):
        raise TimeoutExpired(command, timeout)

    result = run_manifest(
        manifest_path,
        approve=lambda commands: True,
        command_runner=timeout_runner,
    )

    assert result.overall_status == "failed"
    assert result.commands[0].status == "timeout"
    assert result.commands[0].return_code is None


def test_failed_environment_check_makes_run_fail(tmp_path) -> None:
    path = tmp_path / "mxready.yml"
    document = {
        "schema_version": "1.0",
        "scan_id": "00000000-0000-0000-0000-000000000000",
        "repository_url": "https://github.com/example/project",
        "repository_commit": "a" * 40,
        "runner_version": "0.1.0",
        "checks": [
            {
                "id": "mx-smi",
                "command": ["mx-smi"],
                "timeout_seconds": 10,
            }
        ],
        "project_commands": [],
    }
    path.write_text(json.dumps(document), encoding="utf-8")

    def failed_check(command, *, timeout):
        return CompletedProcess(command, 1, stdout="", stderr="no device")

    result = run_manifest(
        path,
        approve=lambda commands: True,
        command_runner=failed_check,
    )

    assert result.checks[0].status == "failed"
    assert result.overall_status == "failed"


def test_result_matches_backend_contract_and_redacts_command_arguments(
    tmp_path,
    recording_runner,
) -> None:
    path = tmp_path / "mxready.yml"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "scan_id": "00000000-0000-0000-0000-000000000000",
                "repository_url": "https://github.com/example/project",
                "repository_commit": "a" * 40,
                "runner_version": "0.1.0",
                "checks": [],
                "project_commands": [
                    {
                        "id": "tests",
                        "command": [
                            "python",
                            "-m",
                            "pytest",
                            "TOKEN=command-secret",
                        ],
                        "timeout_seconds": 60,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_manifest(
        path,
        approve=lambda commands: True,
        command_runner=recording_runner,
    )

    assert "command-secret" not in result.commands[0].command[-1]
    VerificationRun.model_validate(result.to_dict())
