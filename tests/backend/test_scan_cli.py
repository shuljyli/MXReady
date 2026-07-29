import json
from pathlib import Path

from scripts.scan_repository import main


def test_cli_writes_three_commit_pinned_outputs(tmp_path: Path) -> None:
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
    assert {path.name for path in output.iterdir()} == {
        json_path.name,
        markdown_path.name,
        badge_path.name,
    }
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["repository"]["commit"] == commit
    assert payload["summary"]["total_count"] > 0
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# MXReady 适配体检报告"
    )
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
