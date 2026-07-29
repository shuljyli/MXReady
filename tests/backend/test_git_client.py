from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

import pytest
from mxready.errors import MxReadyError
from mxready.repository.git_client import GitClient, RepositoryLimits
from mxready.repository.identity import parse_repository_url


class RecordingRunner:
    def __init__(self, *, commit: str = "a" * 40) -> None:
        self.calls: list[dict[str, object]] = []
        self.commit = commit

    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None,
        env: Mapping[str, str],
        timeout: float,
    ) -> CompletedProcess[str]:
        self.calls.append(
            {
                "args": list(args),
                "cwd": cwd,
                "env": dict(env),
                "timeout": timeout,
            }
        )
        if list(args) == ["git", "rev-parse", "HEAD"]:
            return CompletedProcess(args, 0, stdout=f"{self.commit}\n", stderr="")
        creates_destination = (len(args) >= 2 and args[1] == "clone") or list(args[:2]) == [
            "git",
            "init",
        ]
        if creates_destination:
            Path(args[-1]).mkdir(parents=True)
        return CompletedProcess(args, 0, stdout="", stderr="")


def test_clone_uses_bounded_argument_array_and_disables_credentials(tmp_path: Path) -> None:
    runner = RecordingRunner()
    client = GitClient(command_runner=runner)
    destination = tmp_path / "repo"

    commit = client.clone(
        parse_repository_url("https://github.com/pytorch/extension-cpp"),
        None,
        destination,
    )

    assert runner.calls[0]["args"] == [
        "git",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--no-tags",
        "https://github.com/pytorch/extension-cpp.git",
        str(destination),
    ]
    assert runner.calls[0]["cwd"] == tmp_path
    assert runner.calls[0]["timeout"] == 60
    environment = runner.calls[0]["env"]
    assert isinstance(environment, dict)
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_LFS_SKIP_SMUDGE"] == "1"
    assert environment["GIT_CONFIG_KEY_0"] == "credential.helper"
    assert environment["GIT_CONFIG_VALUE_0"] == ""
    assert commit == "a" * 40


def test_named_ref_is_inserted_as_branch_argument(tmp_path: Path) -> None:
    runner = RecordingRunner()

    GitClient(command_runner=runner).clone(
        parse_repository_url("https://gitee.com/owner/repo"),
        "release/v1",
        tmp_path / "repo",
    )

    assert runner.calls[0]["args"][-4:] == [
        "--branch",
        "release/v1",
        "https://gitee.com/owner/repo.git",
        str(tmp_path / "repo"),
    ]


def test_full_commit_ref_uses_exact_fetch_and_detached_checkout(tmp_path: Path) -> None:
    runner = RecordingRunner(commit="B" * 40)
    requested_commit = "B" * 40
    destination = tmp_path / "repo"

    resolved = GitClient(command_runner=runner).clone(
        parse_repository_url("https://github.com/owner/repo"),
        requested_commit,
        destination,
    )

    assert [call["args"] for call in runner.calls] == [
        ["git", "init", str(destination)],
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/owner/repo.git",
        ],
        [
            "git",
            "fetch",
            "--depth",
            "1",
            "--no-tags",
            "origin",
            requested_commit,
        ],
        ["git", "checkout", "--detach", "FETCH_HEAD"],
        ["git", "rev-parse", "HEAD"],
    ]
    assert all(call["cwd"] == destination for call in runner.calls[1:])
    assert resolved == requested_commit.lower()


class TimeoutRunner:
    def __call__(self, args, *, cwd, env, timeout):
        raise TimeoutExpired(args, timeout)


def test_timeout_is_mapped_to_stable_error(tmp_path: Path) -> None:
    client = GitClient(command_runner=TimeoutRunner())

    with pytest.raises(MxReadyError) as error:
        client.clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repo",
        )

    assert error.value.code == "CLONE_TIMEOUT"


@pytest.mark.parametrize(
    ("stderr", "expected_code"),
    [
        ("fatal: repository 'x' not found", "REPOSITORY_NOT_FOUND"),
        ("fatal: Authentication failed", "REPOSITORY_ACCESS_DENIED"),
        ("fatal: unexpected transport failure", "SCAN_INTERNAL_ERROR"),
    ],
)
def test_git_failures_are_mapped_without_exposing_stderr(
    tmp_path: Path,
    stderr: str,
    expected_code: str,
) -> None:
    def failing_runner(args, *, cwd, env, timeout):
        return CompletedProcess(args, 128, stdout="", stderr=stderr)

    client = GitClient(command_runner=failing_runner)

    with pytest.raises(MxReadyError) as error:
        client.clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repo",
        )

    assert error.value.code == expected_code
    assert stderr not in error.value.message
    assert stderr not in error.value.details.values()


@pytest.mark.parametrize(
    ("limits", "files", "expected_code"),
    [
        (RepositoryLimits(max_bytes=3), [b"1234"], "REPOSITORY_TOO_LARGE"),
        (RepositoryLimits(max_files=1), [b"1", b"2"], "TOO_MANY_FILES"),
    ],
)
def test_repository_limits_are_enforced_after_clone(
    tmp_path: Path,
    limits: RepositoryLimits,
    files: list[bytes],
    expected_code: str,
) -> None:
    class PopulatingRunner(RecordingRunner):
        def __call__(self, args, *, cwd, env, timeout):
            result = super().__call__(args, cwd=cwd, env=env, timeout=timeout)
            if len(args) >= 2 and args[1] == "clone":
                destination = Path(args[-1])
                for index, content in enumerate(files):
                    (destination / f"{index}.txt").write_bytes(content)
            return result

    client = GitClient(command_runner=PopulatingRunner(), limits=limits)

    with pytest.raises(MxReadyError) as error:
        client.clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repo",
        )

    assert error.value.code == expected_code
