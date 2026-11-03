import json
from pathlib import Path

import pytest

from mxready_runner.cli import main
from mxready_runner.schema import CheckResult


def test_inspect_returns_failure_when_environment_check_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = tmp_path / "mxready.yml"
    output = tmp_path / "result.json"
    manifest.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "mxready_runner.cli.collect_environment",
        lambda **kwargs: [CheckResult("mx-smi", ["mx-smi"], "failed", 1, "", "no device", 0)],
    )

    exit_code = main(
        [
            "inspect",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["overall_status"] == "failed"


@pytest.mark.parametrize("action", ["inspect", "run"])
def test_cli_rejects_modified_checks_before_executing_anything(
    tmp_path: Path, monkeypatch, action: str, capsys
) -> None:
    manifest = tmp_path / "mxready.yml"
    payload = json.loads(Path("tests/fixtures/verification/mxready.yml").read_text())
    payload["checks"][0]["command"] = ["python", "-V"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    def unexpected(*args, **kwargs):
        pytest.fail("Modified environment checks must be rejected before execution or approval")

    monkeypatch.setattr("mxready_runner.cli.collect_environment", unexpected)
    monkeypatch.setattr("mxready_runner.execute.collect_environment", unexpected)
    monkeypatch.setattr("mxready_runner.cli._interactive_approval", unexpected)
    output = tmp_path / "result.json"

    assert main([action, "--manifest", str(manifest), "--output", str(output)]) == 2
    assert "environment check" in capsys.readouterr().err
    assert not output.exists()
