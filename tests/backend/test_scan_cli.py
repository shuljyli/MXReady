import io
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

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


def test_cli_preserves_previous_scan_when_worktree_changes(tmp_path: Path) -> None:
    repository = tmp_path / "clone"
    output = tmp_path / "reports"
    _make_git_clone(repository, "https://github.com/example/cuda-extension")
    arguments = [str(repository), "--output", str(output)]

    assert main(arguments) == 2
    original_files = {path.name: path.read_bytes() for path in output.iterdir()}
    original_report = json.loads(next(output.glob("*.json")).read_text(encoding="utf-8"))
    (repository / "new-kernel.cu").write_text("#define WARP_SIZE 32\n", encoding="utf-8")

    assert main(arguments) == 2

    for name, content in original_files.items():
        assert (output / name).read_bytes() == content
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in output.glob("*.json")]
    assert len(reports) == 2
    assert len({report["scan_id"] for report in reports}) == 2
    assert {report["repository"]["commit"] for report in reports} == {
        original_report["repository"]["commit"]
    }
    current = next(report for report in reports if report["scan_id"] != original_report["scan_id"])
    assert any(finding["relative_path"] == "new-kernel.cu" for finding in current["findings"])
    assert len(list(output.iterdir())) == 8


def test_cli_gives_each_scan_a_new_id_even_in_separate_output_directories(tmp_path: Path) -> None:
    repository = tmp_path / "clone"
    _make_git_clone(repository, "https://github.com/example/cuda-extension")
    reports = []
    for name in ("before", "after"):
        output = tmp_path / name
        assert main([str(repository), "--output", str(output)]) == 2
        reports.append(json.loads(next(output.glob("*.json")).read_text(encoding="utf-8")))

    assert reports[0]["scan_id"] != reports[1]["scan_id"]


@pytest.mark.parametrize("extension", ["json", "md", "svg", "sarif"])
def test_cli_preserves_existing_output_and_uses_one_new_stem(
    tmp_path: Path, extension: str
) -> None:
    output = tmp_path / "reports"
    output.mkdir()
    original = output / ("project-" + "d" * 12 + f".{extension}")
    original.write_text("previous evidence\n", encoding="utf-8")

    assert (
        main(
            [
                "tests/fixtures/repositories/cuda_extension",
                "--repo-url",
                "https://github.com/example/project",
                "--commit",
                "d" * 40,
                "--output",
                str(output),
            ]
        )
        == 2
    )

    assert original.read_text(encoding="utf-8") == "previous evidence\n"
    files = [path for path in output.iterdir() if path != original]
    assert len(files) == 4
    assert len({path.stem for path in files}) == 1
    assert files[0].stem != original.stem
    assert {path.suffix for path in files} == {".json", ".md", ".svg", ".sarif"}


def test_cli_does_not_follow_an_existing_output_symlink(tmp_path: Path, report_factory) -> None:
    target = tmp_path / "evidence.md"
    target.write_text("trusted evidence\n", encoding="utf-8")
    output = tmp_path / "reports"
    output.mkdir()
    link = output / "project.md"
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip(f"Symlink creation is not available: {error}")

    stem = scan_repository._write_outputs(output, "project", report_factory())

    assert stem != "project"
    assert link.is_symlink()
    assert target.read_text(encoding="utf-8") == "trusted evidence\n"
    assert not (output / "project.json").exists()
    assert {path.suffix for path in output.glob(f"{stem}.*")} == {
        ".json",
        ".md",
        ".svg",
        ".sarif",
    }


def test_cli_cleans_up_new_outputs_when_reservation_fails(
    tmp_path: Path, monkeypatch, report_factory
) -> None:
    original_open = Path.open

    def fail_sarif(path, *args, **kwargs):
        if path.suffix == ".sarif":
            raise PermissionError("output is not writable")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_sarif)
    with pytest.raises(PermissionError, match="not writable"):
        scan_repository._write_outputs(tmp_path, "project", report_factory())
    assert not list(tmp_path.iterdir())


def test_concurrent_local_scans_do_not_replace_each_others_outputs(tmp_path: Path, report_factory):
    reports = [report_factory(), report_factory()]
    ready = Barrier(2)

    def write(report):
        ready.wait(timeout=5)
        return scan_repository._write_outputs(tmp_path, "project", report)

    with ThreadPoolExecutor(max_workers=2) as pool:
        stems = list(pool.map(write, reports))

    assert len(set(stems)) == 2
    assert len(list(tmp_path.iterdir())) == 8
    for report, stem in zip(reports, stems, strict=True):
        payload = json.loads((tmp_path / f"{stem}.json").read_text(encoding="utf-8"))
        assert payload["scan_id"] == str(report.scan_id)
        for extension in ("md", "svg", "sarif"):
            assert (tmp_path / f"{stem}.{extension}").stat().st_size > 0


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
