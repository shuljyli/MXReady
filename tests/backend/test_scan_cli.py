import io
import json
import shutil
import subprocess
from pathlib import Path

from mxready.cli import scan_repository
from mxready.cli.scan_repository import main

_FIXTURE_REPOSITORY = Path(__file__).resolve().parents[1] / "fixtures" / "repositories"


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), *arguments),
        capture_output=True,
        check=True,
        encoding="utf-8",
        shell=False,
        text=True,
    )
    return completed.stdout.strip()


def _make_git_clone(root: Path, remote: str) -> None:
    """把只读样例目录变成带 origin 的真实仓库。"""
    shutil.copytree(_FIXTURE_REPOSITORY / "cuda_extension", root)
    _git(root, "init", "-q")
    _git(root, "remote", "add", "origin", remote)
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=MXReady Test",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "initial",
    )


def test_cli_writes_four_commit_pinned_outputs(tmp_path: Path, capsys) -> None:
    output = tmp_path / "reports"
    commit = "d" * 40

    exit_code = main(
        [
            "tests/fixtures/repositories/cuda_extension",
            "--repo-url",
            "https://github.com/example/cuda-extension",
            "--commit",
            commit,
            "--output",
            str(output),
        ]
    )

    stem = "cuda-extension-dddddddddddd"
    json_path = output / f"{stem}.json"
    markdown_path = output / f"{stem}.md"
    badge_path = output / f"{stem}.svg"
    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.out.startswith("MXReady: blocked | ")
    assert "MXR-TOOLCHAIN-001" in captured.out
    assert f"报告: {stem}.json / {stem}.md / {stem}.svg" in captured.out
    assert {path.name for path in output.iterdir()} == {
        json_path.name,
        markdown_path.name,
        badge_path.name,
        f"{stem}.sarif",
    }
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["repository"]["commit"] == commit
    assert payload["summary"]["total_count"] > 0
    assert markdown_path.read_text(encoding="utf-8").startswith("# MXReady 适配体检报告")
    assert badge_path.read_text(encoding="utf-8").startswith("<svg")


def test_cli_returns_zero_for_a_clean_local_project(tmp_path: Path) -> None:
    repository = tmp_path / "clean-project"
    repository.mkdir()
    (repository / "pyproject.toml").write_text(
        "[project]\nname = 'clean-project'\nversion = '0.1.0'\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            str(repository),
            "--repo-url",
            "https://gitee.com/example/clean-project",
            "--commit",
            "e" * 40,
            "--output",
            str(tmp_path / "reports"),
        ]
    )

    assert exit_code == 0


def test_cli_rejects_missing_directories_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            str(tmp_path / "does-not-exist"),
            "--repo-url",
            "https://github.com/example/project",
            "--commit",
            "f" * 40,
            "--output",
            str(tmp_path / "reports"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Local repository directory does not exist" in captured.err
    assert "Traceback" not in captured.err


def test_cli_rejects_non_sha_commit(capsys, tmp_path: Path) -> None:
    exit_code = main(
        [
            "tests/fixtures/repositories/cuda_extension",
            "--repo-url",
            "https://github.com/example/project",
            "--commit",
            "main",
            "--output",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "40-character lowercase hexadecimal SHA" in captured.err


def test_cli_detects_identity_from_a_local_clone(tmp_path: Path, capsys) -> None:
    repository = tmp_path / "clone"
    _make_git_clone(repository, "git@github.com:example/cuda-extension.git")
    commit = _git(repository, "rev-parse", "HEAD")

    exit_code = main([str(repository), "--output", str(tmp_path / "reports")])

    captured = capsys.readouterr()
    assert exit_code == 2, captured.err
    payload = json.loads(
        (tmp_path / "reports" / f"cuda-extension-{commit[:12]}.json").read_text(encoding="utf-8")
    )
    assert payload["repository"]["url"] == "https://github.com/example/cuda-extension"
    assert payload["repository"]["commit"] == commit


def test_cli_reports_missing_git_identity_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    repository = tmp_path / "empty-repository"
    repository.mkdir()
    _git(repository, "init", "-q")

    exit_code = main([str(repository), "--output", str(tmp_path / "reports")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "pass --commit" in captured.err
    assert "Traceback" not in captured.err


def test_scp_and_ssh_remotes_become_https_urls() -> None:
    normalize = scan_repository._normalize_remote_url
    assert normalize("git@github.com:owner/repo.git") == "https://github.com/owner/repo.git"
    assert normalize("ssh://git@gitee.com/owner/repo.git") == "https://gitee.com/owner/repo.git"
    assert normalize("https://github.com/owner/repo") == "https://github.com/owner/repo"
    assert normalize("../local-mirror") == "../local-mirror"
    assert normalize("D:/local-mirror") == "D:/local-mirror"


class _LegacyCodePageStdout(io.StringIO):
    encoding = "cp1252"


def test_cli_falls_back_to_ascii_summary_on_legacy_code_page(
    tmp_path: Path,
    monkeypatch,
) -> None:
    stream = _LegacyCodePageStdout()
    monkeypatch.setattr(scan_repository.sys, "stdout", stream)

    exit_code = main(
        [
            "tests/fixtures/repositories/cuda_extension",
            "--repo-url",
            "https://github.com/example/cuda-extension",
            "--commit",
            "d" * 40,
            "--output",
            str(tmp_path / "reports"),
        ]
    )

    output = stream.getvalue()
    assert exit_code == 2
    assert output.isascii()
    assert "BLOCKER" in output
    assert "Report: cuda-extension-dddddddddddd.json" in output
