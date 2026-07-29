from __future__ import annotations

import json
from collections.abc import Sequence
from subprocess import CompletedProcess

import pytest


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], int]] = []

    def __call__(
        self,
        command: Sequence[str],
        *,
        timeout: int,
    ) -> CompletedProcess[str]:
        self.calls.append((list(command), timeout))
        return CompletedProcess(
            command,
            0,
            stdout="TOKEN=secret123 ok\n",
            stderr="",
        )


@pytest.fixture
def recording_runner() -> RecordingRunner:
    return RecordingRunner()


@pytest.fixture
def manifest_path(tmp_path):
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
                        "command": ["python", "-m", "pytest"],
                        "timeout_seconds": 60,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path
