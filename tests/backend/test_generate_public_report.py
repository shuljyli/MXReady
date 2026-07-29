import json
import shutil
from pathlib import Path

import pytest
from mxready.errors import MxReadyError

from scripts.generate_public_report import generate_public_report, main


class FixtureGitClient:
    def __init__(self, fixture: Path, commit: str) -> None:
        self.fixture = fixture
        self.commit = commit
        self.requested_ref: str | None = "not-called"

    def clone(self, identity, requested_ref, destination: Path) -> str:
        self.requested_ref = requested_ref
        shutil.copytree(self.fixture, destination)
        return self.commit


class TimeoutGitClient:
    def clone(self, identity, requested_ref, destination: Path) -> str:
        raise MxReadyError("CLONE_TIMEOUT", "clone timed out")


class FixtureArchiveClient(FixtureGitClient):
    pass


def test_generate_public_report_clones_with_limits_and_writes_pinned_outputs(
    tmp_path: Path,
) -> None:
    commit = "a" * 40
    git_client = FixtureGitClient(
        Path("tests/fixtures/repositories/cuda_extension"),
        commit,
    )

    report = generate_public_report(
        "https://github.com/pytorch/extension-cpp",
        label="pytorch-extension-cpp",
        output_dir=tmp_path / "reports",
        work_dir=tmp_path / "work",
        git_client=git_client,
    )

    assert git_client.requested_ref is None
    assert report.repository.commit == commit
    assert {path.name for path in (tmp_path / "reports").iterdir()} == {
        "pytorch-extension-cpp.json",
        "pytorch-extension-cpp.md",
    }
    payload = json.loads(
        (tmp_path / "reports" / "pytorch-extension-cpp.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["repository"]["url"] == "https://github.com/pytorch/extension-cpp"
    assert payload["repository"]["commit"] == commit
    assert payload["verification_status"] == "not-run"
    assert not any((tmp_path / "work").iterdir())


@pytest.mark.parametrize("label", ["../escape", "Uppercase", "two words", ""])
def test_generate_public_report_rejects_unsafe_labels(
    label: str,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="lowercase"):
        generate_public_report(
            "https://github.com/pytorch/extension-cpp",
            label=label,
            output_dir=tmp_path / "reports",
            work_dir=tmp_path / "work",
            git_client=FixtureGitClient(tmp_path, "b" * 40),
        )


def test_generate_public_report_uses_github_archive_after_git_timeout(
    tmp_path: Path,
) -> None:
    commit = "c" * 40
    archive_client = FixtureArchiveClient(
        Path("tests/fixtures/repositories/cuda_extension"),
        commit,
    )

    report = generate_public_report(
        "https://github.com/pytorch/extension-cpp",
        label="pytorch-extension-cpp",
        output_dir=tmp_path / "reports",
        work_dir=tmp_path / "work",
        git_client=TimeoutGitClient(),
        archive_client=archive_client,
    )

    assert report.repository.commit == commit
    assert archive_client.requested_ref is None


def test_public_report_cli_reports_operational_errors_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "https://example.com/not-allowed/repository",
            "--label",
            "invalid-host",
            "--output",
            str(tmp_path / "reports"),
            "--work-dir",
            str(tmp_path / "work"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MXReady public scan error:" in captured.err
    assert "Traceback" not in captured.err
