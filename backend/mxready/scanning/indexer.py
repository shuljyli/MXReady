from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from mxready.errors import MxReadyError

_ALLOWED_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".cmake",
    ".cpp",
    ".cu",
    ".cuh",
    ".dockerfile",
    ".h",
    ".hpp",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
_ALLOWED_FILENAMES = {"CMakeLists.txt", "Dockerfile"}
_EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}
_HIDDEN_CACHE_DIRECTORIES = {
    ".cache",
    ".hypothesis",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
}


@dataclass(frozen=True, slots=True)
class IndexedFile:
    relative_path: str
    size: int
    sha256: str
    text: str


@dataclass(frozen=True, slots=True)
class IndexWarning:
    code: str
    relative_path: str
    message: str


@dataclass(frozen=True, slots=True)
class FileIndex:
    files: tuple[IndexedFile, ...]
    warnings: tuple[IndexWarning, ...]


def build_file_index(
    root: Path,
    *,
    max_files: int = 10_000,
    max_file_bytes: int = 1_048_576,
) -> FileIndex:
    """Build a deterministic text-only index without following symlinks."""
    if max_files <= 0 or max_file_bytes <= 0:
        raise ValueError("file index limits must be positive")

    root = Path(root)
    if not root.is_dir():
        raise MxReadyError(
            "SCAN_INTERNAL_ERROR",
            "待扫描的仓库目录不存在或不可读取。",
        )

    indexed_files: list[IndexedFile] = []
    warnings: list[IndexWarning] = []
    candidate_count = 0

    for path, relative_path in _walk_candidate_files(root, warnings):
        candidate_count += 1
        if candidate_count > max_files:
            raise MxReadyError(
                "TOO_MANY_FILES",
                f"可分析源码文件超过 {max_files} 个限制。",
            )

        try:
            size = path.stat(follow_symlinks=False).st_size
        except OSError:
            warnings.append(
                IndexWarning(
                    code="FILE_READ_ERROR",
                    relative_path=relative_path,
                    message="无法读取该文件的元数据，已跳过。",
                )
            )
            continue

        if size > max_file_bytes:
            warnings.append(
                IndexWarning(
                    code="FILE_TOO_LARGE",
                    relative_path=relative_path,
                    message=f"文件超过 {max_file_bytes} 字节限制，已跳过。",
                )
            )
            continue

        try:
            content = path.read_bytes()
        except OSError:
            warnings.append(
                IndexWarning(
                    code="FILE_READ_ERROR",
                    relative_path=relative_path,
                    message="无法安全读取该文件，已跳过。",
                )
            )
            continue

        if len(content) > max_file_bytes:
            warnings.append(
                IndexWarning(
                    code="FILE_TOO_LARGE",
                    relative_path=relative_path,
                    message=f"文件超过 {max_file_bytes} 字节限制，已跳过。",
                )
            )
            continue
        if _looks_binary(content):
            warnings.append(
                IndexWarning(
                    code="BINARY_FILE_SKIPPED",
                    relative_path=relative_path,
                    message="文件包含二进制内容，已跳过。",
                )
            )
            continue

        text = _decode_text(content)
        if text is None:
            warnings.append(
                IndexWarning(
                    code="UNSUPPORTED_TEXT_ENCODING",
                    relative_path=relative_path,
                    message="文件不是 UTF-8 或 GB18030 文本，已跳过。",
                )
            )
            continue

        indexed_files.append(
            IndexedFile(
                relative_path=relative_path,
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                text=text,
            )
        )

    return FileIndex(
        files=tuple(sorted(indexed_files, key=lambda item: item.relative_path)),
        warnings=tuple(sorted(warnings, key=lambda item: (item.relative_path, item.code))),
    )


def _walk_candidate_files(
    root: Path,
    warnings: list[IndexWarning],
):
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                ordered_entries = sorted(entries, key=lambda item: item.name)
        except OSError:
            relative_path = _relative_path(directory, root)
            warnings.append(
                IndexWarning(
                    code="DIRECTORY_READ_ERROR",
                    relative_path=relative_path,
                    message="无法读取该目录，已跳过。",
                )
            )
            continue

        child_directories: list[Path] = []
        for entry in ordered_entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if not _is_excluded_directory(entry.name):
                        child_directories.append(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError:
                continue

            path = Path(entry.path)
            if _is_allowed_file(path):
                yield path, _relative_path(path, root)

        pending.extend(reversed(child_directories))


def _is_excluded_directory(name: str) -> bool:
    return (
        name in _EXCLUDED_DIRECTORIES
        or name in _HIDDEN_CACHE_DIRECTORIES
        or name.startswith(".")
        and "cache" in name.casefold()
    )


def _is_allowed_file(path: Path) -> bool:
    return path.name in _ALLOWED_FILENAMES or path.suffix.casefold() in _ALLOWED_EXTENSIONS


def _relative_path(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    return relative or "."


def _looks_binary(content: bytes) -> bool:
    return b"\x00" in content


def _decode_text(content: bytes) -> str | None:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None
