from __future__ import annotations

import json

import pytest
from mxready_runner.schema import ManifestError, load_manifest


@pytest.mark.parametrize(
    "command",
    [
        ["sudo", "python", "-m", "pytest"],
        ["/usr/bin/apt-get", "install", "torch"],
        ["python", "-m", "pytest", ">", "result.txt"],
        ["bash", "-c", "pytest"],
        ["python", "-m", "pytest", "2>result.txt"],
        ["python", "-m", "pip", "install", "torch"],
        ["env", "sudo", "python", "-m", "pytest"],
    ],
)
def test_manifest_rejects_privileged_shell_or_package_commands(
    tmp_path,
    command: list[str],
) -> None:
    manifest = _manifest(command=command)
    path = tmp_path / "mxready.yml"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(path)


def test_manifest_rejects_unknown_fields_and_out_of_range_timeout(
    tmp_path,
) -> None:
    manifest = _manifest(command=["python", "-m", "pytest"])
    manifest["project_commands"][0]["timeout_seconds"] = 601
    manifest["unexpected"] = True
    path = tmp_path / "mxready.yml"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(path)


def test_manifest_accepts_json_compatible_yaml_fixture() -> None:
    manifest = load_manifest("tests/fixtures/verification/mxready.yml")

    assert manifest.repository_commit == "a" * 40
    assert manifest.project_commands[0].command == ["python", "-m", "pytest", "-q"]


def _manifest(*, command: list[str]) -> dict:
    return {
        "schema_version": "1.0",
        "scan_id": "00000000-0000-0000-0000-000000000000",
        "repository_url": "https://github.com/example/project",
        "repository_commit": "a" * 40,
        "runner_version": "0.1.0",
        "checks": [],
        "project_commands": [
            {
                "id": "tests",
                "command": command,
                "timeout_seconds": 60,
            }
        ],
    }
