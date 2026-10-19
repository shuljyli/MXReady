from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from typing import Protocol

from mxready.errors import MxReadyError
from mxready.repository.identity import RepositoryIdentity, validate_git_ref

_COMMIT = re.compile(r"[0-9a-fA-F]{40}")


class CommandRunner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None,
        env: Mapping[str, str],
        timeout: float,
    ) -> CompletedProcess[str]: ...


@dataclass(frozen=True, slots=True)
class RepositoryLimits:
    clone_timeout_seconds: float = 60
    max_bytes: int = 52_428_800
    max_files: int = 10_000

    def __post_init__(self) -> None:
        if self.clone_timeout_seconds <= 0 or self.max_bytes <= 0 or self.max_files <= 0:
            raise ValueError("repository limits must be positive")


def run_command(
    args: Sequence[str],
    *,
    cwd: Path | None,
    env: Mapping[str, str],
    timeout: float,
) -> CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        env=dict(env),
        timeout=timeout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class GitClient:
    def __init__(
        self,
        *,
        command_runner: CommandRunner = run_command,
        limits: RepositoryLimits | None = None,
    ) -> None:
        self._command_runner = command_runner
        self.limits = limits or RepositoryLimits()

    def clone(
        self,
        identity: RepositoryIdentity,
        requested_ref: str | None,
        destination: Path,
    ) -> str:
        reference = validate_git_ref(requested_ref)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        environment = self._git_environment()

        if reference is not None and _COMMIT.fullmatch(reference):
            self._clone_commit(identity, reference, destination, environment)
        else:
            self._clone_branch_or_default(
                identity,
                reference,
                destination,
                environment,
            )

        self._enforce_repository_limits(destination)
        result = self._run(
            ["git", "rev-parse", "HEAD"],
            cwd=destination,
            environment=environment,
        )
        commit = result.stdout.strip().lower()
        if _COMMIT.fullmatch(commit) is None:
            raise MxReadyError(
                "SCAN_INTERNAL_ERROR",
                "Git 未能返回有效的提交编号，请稍后重试。",
            )
        return commit

    def _clone_branch_or_default(
        self,
        identity: RepositoryIdentity,
        reference: str | None,
        destination: Path,
        environment: Mapping[str, str],
    ) -> None:
        args = [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--no-tags",
        ]
        if reference is not None:
            args.extend(["--branch", reference])
        args.extend([identity.clone_url, str(destination)])
        self._run(args, cwd=destination.parent, environment=environment)

    def _clone_commit(
        self,
        identity: RepositoryIdentity,
        reference: str,
        destination: Path,
        environment: Mapping[str, str],
    ) -> None:
        self._run(
            ["git", "init", str(destination)],
            cwd=destination.parent,
            environment=environment,
        )
        self._run(
            ["git", "remote", "add", "origin", identity.clone_url],
            cwd=destination,
            environment=environment,
        )
        self._run(
            [
                "git",
                "fetch",
                "--depth",
                "1",
                "--no-tags",
                "origin",
                reference,
            ],
            cwd=destination,
            environment=environment,
        )
        self._run(
            ["git", "checkout", "--detach", "FETCH_HEAD"],
            cwd=destination,
            environment=environment,
        )

    def _run(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str],
    ) -> CompletedProcess[str]:
        try:
            result = self._command_runner(
                args,
                cwd=cwd,
                env=environment,
                timeout=self.limits.clone_timeout_seconds,
            )
        except TimeoutExpired as error:
            raise MxReadyError(
                "CLONE_TIMEOUT",
                "仓库获取超时，请确认仓库可公开访问或稍后重试。",
            ) from error
        except OSError as error:
            raise MxReadyError(
                "SCAN_INTERNAL_ERROR",
                "无法启动 Git，请检查服务环境后重试。",
            ) from error

        if result.returncode != 0:
            raise self._map_git_failure(result.stderr)
        return result

    def _enforce_repository_limits(self, destination: Path) -> None:
        total_bytes = 0
        total_files = 0
        pending = [destination]

        try:
            while pending:
                directory = pending.pop()
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue

                        total_files += 1
                        if total_files > self.limits.max_files:
                            raise MxReadyError(
                                "TOO_MANY_FILES",
                                f"仓库文件数超过 {self.limits.max_files} 个限制。",
                            )
                        total_bytes += entry.stat(follow_symlinks=False).st_size
                        if total_bytes > self.limits.max_bytes:
                            raise MxReadyError(
                                "REPOSITORY_TOO_LARGE",
                                f"仓库内容超过 {self.limits.max_bytes} 字节限制。",
                            )
        except MxReadyError:
            raise
        except OSError as error:
            raise MxReadyError(
                "SCAN_INTERNAL_ERROR",
                "无法安全读取克隆后的仓库。",
            ) from error

    @staticmethod
    def _git_environment() -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_LFS_SKIP_SMUDGE": "1",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "credential.helper",
                "GIT_CONFIG_VALUE_0": "",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            }
        )
        return environment

    @staticmethod
    def _map_git_failure(stderr: str) -> MxReadyError:
        normalized = stderr.casefold()
        access_markers = (
            "authentication failed",
            "access denied",
            "permission denied",
            "could not read username",
            "terminal prompts disabled",
        )
        not_found_markers = (
            "repository not found",
            "does not exist",
            "couldn't find remote ref",
            "could not find remote ref",
            "not found",
        )

        if any(marker in normalized for marker in access_markers):
            return MxReadyError(
                "REPOSITORY_ACCESS_DENIED",
                "仓库拒绝访问；MXReady 的 MVP 只支持无需登录的公开仓库。",
            )
        if any(marker in normalized for marker in not_found_markers):
            return MxReadyError(
                "REPOSITORY_NOT_FOUND",
                "未找到仓库或指定分支、标签、提交，请检查输入。",
            )
        return MxReadyError(
            "SCAN_INTERNAL_ERROR",
            "Git 获取仓库失败，请稍后重试。",
        )
