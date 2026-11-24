"""Approval-gated workspace writes."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from mxready.agent.permissions import ApprovalRequest, PermissionManager
from mxready.agent.tools.base import ToolError, WorkspaceGuard, text_argument

MAX_WRITE_BYTES = 256 * 1024
MAX_PATCH_BYTES = 16 * 1024
MAX_PATCH_FILE_BYTES = 2 * 1024 * 1024


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".mxready-write-", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            with contextlib.suppress(OSError):
                os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(temporary)


def _relative(guard: WorkspaceGuard, path: Path) -> str:
    try:
        return str(path.relative_to(guard.root))
    except ValueError:
        return path.name


class WriteFileTool:
    name = "write_file"
    description = (
        "Create or overwrite a workspace text file. Requires elevated permissions and "
        "one-time user approval for every call."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path"},
            "content": {"type": "string", "description": "Complete UTF-8 file content"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    }

    def __init__(self, guard: WorkspaceGuard, permissions: PermissionManager) -> None:
        self.guard = guard
        self.permissions = permissions

    def run(self, arguments: dict[str, object]) -> str:
        value = text_argument(arguments, "path")
        content = text_argument(
            arguments, "content", limit=MAX_WRITE_BYTES
        )
        assert content is not None
        if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
            raise ToolError("The content exceeds the 256 KiB write limit")
        path = self.guard.resolve(value, must_exist=False)
        if path.exists() and path.is_dir():
            raise ToolError("The path is a directory")
        relative = _relative(self.guard, path)
        self.permissions.require(
            ApprovalRequest(
                tool=self.name,
                summary=f"write {relative}",
                detail=f"{len(content.encode('utf-8'))} bytes; full overwrite",
            )
        )
        _atomic_write(path, content)
        return f"Wrote {relative} ({len(content.encode('utf-8'))} bytes)"


class ApplyPatchTool:
    name = "apply_patch"
    description = (
        "Replace one unique text occurrence in an existing workspace file. Requires "
        "elevated permissions and one-time user approval."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path"},
            "old": {"type": "string", "description": "Exact text that must occur once"},
            "new": {"type": "string", "description": "Replacement text"},
        },
        "required": ["path", "old", "new"],
        "additionalProperties": False,
    }

    def __init__(self, guard: WorkspaceGuard, permissions: PermissionManager) -> None:
        self.guard = guard
        self.permissions = permissions

    def run(self, arguments: dict[str, object]) -> str:
        value = text_argument(arguments, "path")
        old = text_argument(arguments, "old", limit=MAX_PATCH_BYTES)
        new = text_argument(arguments, "new", limit=MAX_WRITE_BYTES)
        assert old is not None and new is not None
        if not old:
            raise ToolError("The old text must not be empty")
        if len(new.encode("utf-8")) > MAX_WRITE_BYTES:
            raise ToolError("The replacement exceeds the 256 KiB write limit")
        path = self.guard.resolve(value, must_exist=True)
        if not path.is_file():
            raise ToolError("The path is not a file")
        if path.stat().st_size > MAX_PATCH_FILE_BYTES:
            raise ToolError("The file exceeds the 2 MiB patch limit")
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ToolError(f"Cannot read the UTF-8 file: {error}") from error
        if original.count(old) != 1:
            raise ToolError("The old text must occur exactly once in the file")
        relative = _relative(self.guard, path)
        self.permissions.require(
            ApprovalRequest(
                tool=self.name,
                summary=f"patch {relative}",
                detail=f"replace {len(old)} characters with {len(new)} characters",
            )
        )
        _atomic_write(path, original.replace(old, new, 1))
        return f"Patched {relative}"
