from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

_COMMIT = re.compile(r"[0-9a-f]{40}")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_COMMAND_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_REPOSITORY_SEGMENT = re.compile(r"[A-Za-z0-9_.-]+")
_FORBIDDEN_EXECUTABLES = {
    "apk",
    "apt",
    "apt-get",
    "bash",
    "brew",
    "busybox",
    "choco",
    "cmd",
    "command",
    "conda",
    "dnf",
    "env",
    "mamba",
    "nice",
    "nohup",
    "npm",
    "pacman",
    "pip",
    "pip3",
    "pnpm",
    "powershell",
    "pwsh",
    "sh",
    "sudo",
    "uv",
    "xargs",
    "yum",
    "yarn",
    "zsh",
}
_FORBIDDEN_PYTHON_MODULES = {
    "conda",
    "ensurepip",
    "pip",
    "pip3",
    "poetry",
    "uv",
}
_SHELL_TOKENS = {"&", "&&", ";", "<", "<<", ">", ">>", "|", "||"}
_REDIRECTION = re.compile(r"(?:[0-9]*)(?:>>?|<<?).+")
_MAX_MANIFEST_BYTES = 1_048_576


class ManifestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CommandSpec:
    id: str
    command: list[str]
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class Manifest:
    schema_version: str
    scan_id: str
    repository_url: str
    repository_commit: str
    runner_version: str
    checks: list[CommandSpec]
    project_commands: list[CommandSpec]


@dataclass(frozen=True, slots=True)
class CheckResult:
    id: str
    command: list[str]
    status: Literal["passed", "failed", "unavailable"]
    return_code: int | None
    stdout: str
    stderr: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CommandResult:
    id: str
    command: list[str]
    timeout_seconds: int
    status: Literal["passed", "failed", "timeout", "cancelled"]
    return_code: int | None
    stdout: str
    stderr: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RunResult:
    schema_version: str
    scan_id: str
    repository_commit: str
    runner_version: str
    environment_fingerprint: str
    checks: list[CheckResult]
    commands: list[CommandResult]
    started_at: str
    finished_at: str
    overall_status: Literal["passed", "failed", "cancelled"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scan_id": self.scan_id,
            "repository_commit": self.repository_commit,
            "runner_version": self.runner_version,
            "environment_fingerprint": self.environment_fingerprint,
            "checks": [item.to_dict() for item in self.checks],
            "commands": [item.to_dict() for item in self.commands],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "overall_status": self.overall_status,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )


def load_manifest(path: str | Path) -> Manifest:
    manifest_path = Path(path)
    try:
        if manifest_path.stat().st_size > _MAX_MANIFEST_BYTES:
            raise ManifestError("manifest is too large")
        document = json.loads(
            manifest_path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
        )
        return _validate_manifest(document)
    except ManifestError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ManifestError("manifest is not valid JSON-compatible YAML") from error


def _validate_manifest(document: Any) -> Manifest:
    if not isinstance(document, dict):
        raise ManifestError("manifest root must be an object")
    expected_fields = {
        "schema_version",
        "scan_id",
        "repository_url",
        "repository_commit",
        "runner_version",
        "checks",
        "project_commands",
    }
    if set(document) != expected_fields:
        raise ManifestError("manifest fields do not match the schema")
    if document["schema_version"] != "1.0":
        raise ManifestError("unsupported manifest schema version")

    scan_id = _validate_uuid(document["scan_id"])
    repository_url = _validate_repository_url(document["repository_url"])
    repository_commit = document["repository_commit"]
    if not isinstance(repository_commit, str) or _COMMIT.fullmatch(repository_commit) is None:
        raise ManifestError("repository commit must be 40 lowercase hexadecimal characters")
    runner_version = document["runner_version"]
    if not isinstance(runner_version, str) or _VERSION.fullmatch(runner_version) is None:
        raise ManifestError("runner version is invalid")

    checks = _validate_command_list(document["checks"], "checks")
    project_commands = _validate_command_list(
        document["project_commands"],
        "project_commands",
    )
    identifiers = [item.id for item in [*checks, *project_commands]]
    if len(identifiers) != len(set(identifiers)):
        raise ManifestError("command identifiers must be unique")

    return Manifest(
        schema_version="1.0",
        scan_id=scan_id,
        repository_url=repository_url,
        repository_commit=repository_commit,
        runner_version=runner_version,
        checks=checks,
        project_commands=project_commands,
    )


def _validate_command_list(value: Any, field_name: str) -> list[CommandSpec]:
    if not isinstance(value, list) or len(value) > 64:
        raise ManifestError(f"{field_name} must be a bounded list")
    return [_validate_command(item) for item in value]


def _validate_command(value: Any) -> CommandSpec:
    if not isinstance(value, dict) or set(value) != {
        "id",
        "command",
        "timeout_seconds",
    }:
        raise ManifestError("command fields do not match the schema")
    identifier = value["id"]
    if not isinstance(identifier, str) or _COMMAND_ID.fullmatch(identifier) is None:
        raise ManifestError("command id is invalid")
    command = value["command"]
    if (
        not isinstance(command, list)
        or not 1 <= len(command) <= 32
        or any(
            not isinstance(argument, str)
            or not argument
            or len(argument) > 4_096
            or any(ord(character) < 32 for character in argument)
            for argument in command
        )
    ):
        raise ManifestError("command must be a bounded array of strings")
    _validate_command_safety(command)

    timeout = value["timeout_seconds"]
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ManifestError("command timeout must be between 1 and 600 seconds")
    return CommandSpec(
        id=identifier,
        command=list(command),
        timeout_seconds=timeout,
    )


def _validate_command_safety(command: list[str]) -> None:
    executable = command[0].replace("\\", "/").rsplit("/", 1)[-1].casefold()
    executable = os.path.splitext(executable)[0]
    if executable in _FORBIDDEN_EXECUTABLES or command[0].startswith("-"):
        raise ManifestError("privileged, shell, and package-manager commands are forbidden")
    if (
        executable.startswith("python")
        and len(command) >= 3
        and command[1] == "-m"
        and command[2].split(".", 1)[0].casefold() in _FORBIDDEN_PYTHON_MODULES
    ):
        raise ManifestError("Python package-manager modules are forbidden")
    if any(argument in _SHELL_TOKENS or _REDIRECTION.fullmatch(argument) for argument in command):
        raise ManifestError("shell operators and redirection are forbidden")


def _validate_uuid(value: Any) -> str:
    if not isinstance(value, str):
        raise ManifestError("scan id must be a UUID")
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise ManifestError("scan id must be a UUID") from error
    if str(parsed) != value.casefold():
        raise ManifestError("scan id must use canonical UUID form")
    return str(parsed)


def _validate_repository_url(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ManifestError("repository URL must use HTTPS")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ManifestError("repository URL is invalid") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "gitee.com"}
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ManifestError("repository URL must identify a public GitHub or Gitee repo")
    parts = parsed.path.removesuffix(".git").strip("/").split("/")
    if len(parts) != 2 or any(_REPOSITORY_SEGMENT.fullmatch(part) is None for part in parts):
        raise ManifestError("repository URL path is invalid")
    return value.removesuffix(".git")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("duplicate manifest field")
        result[key] = value
    return result
