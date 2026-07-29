from __future__ import annotations

import io
import json
import stat
import zipfile
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from mxready.errors import MxReadyError
from mxready.repository.git_client import RepositoryLimits
from mxready.repository.identity import (
    RepositoryIdentity,
    validate_git_ref,
)

_COMMIT_LENGTH = 40
_METADATA_LIMIT_BYTES = 1_048_576
_COPY_CHUNK_BYTES = 65_536

HttpReader = Callable[..., bytes]


class GitHubArchiveClient:
    """Fetch a commit-pinned GitHub source archive without running repository code."""

    def __init__(
        self,
        *,
        http_reader: HttpReader | None = None,
        limits: RepositoryLimits | None = None,
    ) -> None:
        self._http_reader = http_reader or read_bounded_url
        self.limits = limits or RepositoryLimits()

    def clone(
        self,
        identity: RepositoryIdentity,
        requested_ref: str | None,
        destination: Path,
    ) -> str:
        if identity.provider != "github":
            raise MxReadyError(
                "ARCHIVE_FALLBACK_UNAVAILABLE",
                "The bounded archive fallback is available only for GitHub repositories.",
            )

        reference = validate_git_ref(requested_ref)
        commit = self._resolve_commit(identity, reference)
        archive_url = (
            f"https://codeload.github.com/{identity.owner}/{identity.name}/zip/{commit}"
        )
        archive_bytes = self._http_reader(
            archive_url,
            timeout=self.limits.clone_timeout_seconds,
            max_bytes=self.limits.max_bytes,
        )
        self._extract_archive(archive_bytes, Path(destination))
        return commit

    def _resolve_commit(
        self,
        identity: RepositoryIdentity,
        requested_ref: str | None,
    ) -> str:
        reference = quote(requested_ref or "HEAD", safe="")
        metadata_url = (
            f"https://api.github.com/repos/{identity.owner}/{identity.name}"
            f"/commits/{reference}"
        )
        metadata = self._http_reader(
            metadata_url,
            timeout=self.limits.clone_timeout_seconds,
            max_bytes=_METADATA_LIMIT_BYTES,
        )
        try:
            payload = json.loads(metadata)
            commit = payload["sha"].lower()
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, AttributeError) as error:
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "GitHub returned invalid commit metadata.",
            ) from error

        if (
            not isinstance(commit, str)
            or len(commit) != _COMMIT_LENGTH
            or any(character not in "0123456789abcdef" for character in commit)
        ):
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "GitHub returned an invalid commit identifier.",
            )
        if (
            requested_ref is not None
            and len(requested_ref) == _COMMIT_LENGTH
            and all(character in "0123456789abcdefABCDEF" for character in requested_ref)
            and commit != requested_ref.lower()
        ):
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "GitHub resolved a different commit than the one requested.",
            )
        return commit

    def _extract_archive(self, archive_bytes: bytes, destination: Path) -> None:
        if destination.exists():
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "Archive extraction destination already exists.",
            )

        try:
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                members = self._validate_members(archive.infolist())
                destination.mkdir(parents=True)
                for info, relative_parts in members:
                    target = destination.joinpath(*relative_parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    self._extract_file(archive, info, target)
        except MxReadyError:
            raise
        except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "GitHub returned an archive that could not be safely extracted.",
            ) from error

    def _validate_members(
        self,
        archive_members: list[zipfile.ZipInfo],
    ) -> list[tuple[zipfile.ZipInfo, tuple[str, ...]]]:
        roots: set[str] = set()
        seen_paths: set[str] = set()
        regular_files: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
        total_bytes = 0

        for info in archive_members:
            parts = _safe_member_parts(info.filename)
            roots.add(parts[0])
            if len(parts) == 1:
                if not info.is_dir():
                    raise _invalid_archive_path()
                continue

            relative_parts = tuple(parts[1:])
            normalized = "/".join(relative_parts).casefold()
            mode = (info.external_attr >> 16) & 0xFFFF

            if info.is_dir():
                continue
            if info.flag_bits & 0x1:
                raise MxReadyError(
                    "INVALID_REPOSITORY_ARCHIVE",
                    "Encrypted repository archive entries are not supported.",
                )
            file_type = stat.S_IFMT(mode)
            if file_type == stat.S_IFLNK:
                continue
            if file_type not in {0, stat.S_IFREG}:
                raise MxReadyError(
                    "INVALID_REPOSITORY_ARCHIVE",
                    "Repository archive contains an unsupported file type.",
                )
            if normalized in seen_paths:
                raise MxReadyError(
                    "INVALID_REPOSITORY_ARCHIVE",
                    "Repository archive contains duplicate file paths.",
                )

            seen_paths.add(normalized)
            if len(regular_files) + 1 > self.limits.max_files:
                raise MxReadyError(
                    "TOO_MANY_FILES",
                    f"Repository contains more than {self.limits.max_files} files.",
                )
            total_bytes += info.file_size
            if total_bytes > self.limits.max_bytes:
                raise MxReadyError(
                    "REPOSITORY_TOO_LARGE",
                    f"Repository content exceeds {self.limits.max_bytes} bytes.",
                )
            regular_files.append((info, relative_parts))

        if len(roots) != 1:
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "Repository archive must contain exactly one top-level directory.",
            )
        return regular_files

    def _extract_file(
        self,
        archive: zipfile.ZipFile,
        info: zipfile.ZipInfo,
        target: Path,
    ) -> None:
        written = 0
        with archive.open(info, mode="r") as source, target.open("xb") as output:
            while True:
                chunk = source.read(_COPY_CHUNK_BYTES)
                if not chunk:
                    break
                written += len(chunk)
                if written > info.file_size or written > self.limits.max_bytes:
                    raise MxReadyError(
                        "INVALID_REPOSITORY_ARCHIVE",
                        "Repository archive expanded beyond its declared size.",
                    )
                output.write(chunk)
        if written != info.file_size:
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "Repository archive file size did not match its declaration.",
            )


def read_bounded_url(url: str, *, timeout: float, max_bytes: int) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MXReady/0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > max_bytes:
                raise _repository_download_too_large(max_bytes)
            content = response.read(max_bytes + 1)
    except MxReadyError:
        raise
    except HTTPError as error:
        if error.code == 404:
            raise MxReadyError(
                "REPOSITORY_NOT_FOUND",
                "GitHub repository or requested reference was not found.",
            ) from error
        raise MxReadyError(
            "ARCHIVE_FETCH_FAILED",
            "GitHub refused the bounded archive request.",
        ) from error
    except (OSError, TimeoutError, URLError, ValueError) as error:
        raise MxReadyError(
            "ARCHIVE_FETCH_FAILED",
            "GitHub archive retrieval failed within the configured safety limit.",
        ) from error

    if len(content) > max_bytes:
        raise _repository_download_too_large(max_bytes)
    return content


def _safe_member_parts(name: str) -> list[str]:
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or "\x00" in name
        or any(ord(character) < 32 for character in name)
    ):
        raise _invalid_archive_path()

    parts = name.split("/")
    if parts[-1] == "":
        parts.pop()
    if (
        not parts
        or any(part in {"", ".", ".."} or ":" in part for part in parts)
    ):
        raise _invalid_archive_path()
    return parts


def _invalid_archive_path() -> MxReadyError:
    return MxReadyError(
        "INVALID_REPOSITORY_ARCHIVE",
        "Repository archive contains an unsafe path.",
    )


def _repository_download_too_large(max_bytes: int) -> MxReadyError:
    return MxReadyError(
        "REPOSITORY_TOO_LARGE",
        f"Repository download exceeds {max_bytes} bytes.",
    )
