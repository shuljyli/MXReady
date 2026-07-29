import json
import sys
from pathlib import Path

from mxready_runner.cli import main


def test_inspect_returns_failure_when_environment_check_fails(
    tmp_path: Path,
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
                        "command": [sys.executable, "-c", "raise SystemExit(1)"],
                        "timeout_seconds": 10,
                    }
                ],
                "project_commands": [],
            }
        ),
        encoding="utf-8",
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
