"""Tool schemas, workspace path guard, and bounded execution helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from mxready.agent.providers.base import ToolCall, ToolSpec

MAX_PATH = 4096
SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "dist",
        "build",
        ".mxready-agent",
        ".mxready",
    }
)
SENSITIVE_NAMES = frozenset(
    {
        ".ssh",
        ".aws",
        ".gnupg",
        ".git",
        ".hg",
        ".svn",
        ".mxready",
        ".mxready-agent",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "secrets.vault",
        "audit.jsonl",
        "state.db",
        "credentials",
    }
)


class ToolError(ValueError):
    """A tool call was rejected or failed; the message is fed back to the model."""


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, object]

    def run(self, arguments: dict[str, object]) -> str: ...


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(
            ToolSpec(tool.name, tool.description, tool.parameters)
            for tool in self._tools.values()
        )

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def run(self, call: ToolCall, arguments: dict[str, object]) -> str:
        tool = self._tools.get(call.name)
        if tool is None:
            raise ToolError(f"Unknown tool: {call.name}")
        return tool.run(arguments)


def _sensitive(part: str) -> bool:
    folded = part.casefold()
    return folded in SENSITIVE_NAMES or folded.startswith(".env")


class WorkspaceGuard:
    """Resolve paths inside one workspace and reject escapes and secrets."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve(strict=True)

    def resolve(
        self,
        value: object,
        *,
        must_exist: bool,
        default_root: bool = False,
    ) -> Path:
        if value is None:
            if not default_root:
                raise ToolError("A path is required")
            value = "."
        if not isinstance(value, str):
            raise ToolError("The path must be a string")
        raw = value.strip()
        if not raw:
            if not default_root:
                raise ToolError("A path is required")
            raw = "."
        if len(raw) > MAX_PATH:
            raise ToolError("The path is too long")
        if "\x00" in raw or any(ord(char) < 32 for char in raw):
            raise ToolError("The path contains control characters")
        if raw.startswith("~"):
            raise ToolError("Home-relative paths are not allowed")
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        absolute = Path(os.path.abspath(candidate))
        try:
            relative = absolute.relative_to(self.root)
        except ValueError as error:
            raise ToolError("The path escapes the workspace") from error
        for part in relative.parts:
            if part in {".", ".."}:
                raise ToolError("The path escapes the workspace")
            if _sensitive(part):
                raise ToolError("Access to sensitive paths is blocked")
        if must_exist:
            try:
                resolved = absolute.resolve(strict=True)
            except OSError as error:
                raise ToolError(f"The path does not exist: {raw}") from error
        else:
            try:
                parent = absolute.parent.resolve(strict=True)
            except OSError as error:
                raise ToolError(f"The parent directory does not exist: {raw}") from error
            resolved = parent / absolute.name
        if not resolved.is_relative_to(self.root):
            raise ToolError("The path escapes the workspace")
        cursor = self.root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ToolError("Symbolic links are not allowed in workspace paths")
        return resolved


def text_argument(
    arguments: dict[str, object], name: str, *, required: bool = True, limit: int = 4096
) -> str | None:
    value = arguments.get(name)
    if value is None:
        if required:
            raise ToolError(f"Missing argument: {name}")
        return None
    if not isinstance(value, str):
        raise ToolError(f"Argument {name} must be a string")
    if len(value) > limit:
        raise ToolError(f"Argument {name} is too long")
    return value


def int_argument(
    arguments: dict[str, object],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = arguments.get(name)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolError(f"Argument {name} must be an integer")
    if not minimum <= value <= maximum:
        raise ToolError(f"Argument {name} must be between {minimum} and {maximum}")
    return value
