from __future__ import annotations

import io
import json
import shutil
import stat
import struct
import time
import zipfile
from collections.abc import Callable
from contextlib import suppress
from http.client import HTTPException, HTTPSConnection
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from urllib.parse import quote, urlsplit

from mxready.errors import MxReadyError
from mxready.repository.git_client import RepositoryLimits
from mxready.repository.identity import (
    RepositoryIdentity,
    validate_git_ref,
)

_COMMIT_LENGTH = 40
_METADATA_LIMIT_BYTES = 1_048_576
_COPY_CHUNK_BYTES = 65_536
_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_END_OF_CENTRAL_DIRECTORY_SIGNATURE = b"PK\x05\x06"
_END_OF_CENTRAL_DIRECTORY_SIZE = 22
_MAX_ZIP_COMMENT_BYTES = 65_535
_ZIP64_COUNT = 0xFFFF
_ZIP64_SIZE = 0xFFFFFFFF
_ALLOWED_HTTP_HOSTS = {"api.github.com", "codeload.github.com"}

HttpReader = Callable[..., bytes]
ConnectionFactory = Callable[[str, float], HTTPSConnection]
Clock = Callable[[], float]


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
        staging = destination.with_name(f".{destination.name}.mxready-partial")
        if destination.exists() or staging.exists():
            raise MxReadyError(
                "INVALID_REPOSITORY_ARCHIVE",
                "Archive extraction destination already exists.",
            )

        staging_created = False
        try:
            declared_members = _validate_central_directory(
                archive_bytes,
                max_members=self.limits.max_files,
            )
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                archive_members = archive.infolist()
                if len(archive_members) != declared_members:
                    raise MxReadyError(
                        "INVALID_REPOSITORY_ARCHIVE",
                        "Repository archive member count is inconsistent.",
                    )
                members = self._validate_members(archive_members)
                staging.mkdir(parents=True)
                staging_created = True
                for info, relative_parts in members:
                    target = staging.joinpath(*relative_parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    self._extract_file(archive, info, target)
            staging.replace(destination)
        except MxReadyError:
            if staging_created:
                _remove_owned_staging(staging)
            raise
        except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            if staging_created:
                _remove_owned_staging(staging)
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

        if len(archive_members) > self.limits.max_files:
            raise MxReadyError(
                "TOO_MANY_FILES",
                f"Repository archive contains more than {self.limits.max_files} entries.",
            )

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


def read_bounded_url(
    url: str,
    *,
    timeout: float,
    max_bytes: int,
    connection_factory: ConnectionFactory | None = None,
    clock: Clock = time.monotonic,
) -> bytes:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _ALLOWED_HTTP_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.fragment
        or parsed.netloc != parsed.hostname
    ):
        raise MxReadyError(
            "ARCHIVE_FETCH_FAILED",
            "Archive request target is not allowed.",
        )
    if timeout <= 0 or max_bytes <= 0:
        raise ValueError("HTTP limits must be positive.")

    deadline = clock() + timeout
    factory = connection_factory or _create_https_connection
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"

    outcomes: Queue[bytes | Exception] = Queue(maxsize=1)
    connection_lock = Lock()
    active_connections: list[HTTPSConnection] = []

    def observe_connection(connection: HTTPSConnection | None) -> None:
        with connection_lock:
            active_connections.clear()
            if connection is not None:
                active_connections.append(connection)

    def perform_request() -> None:
        try:
            outcome: bytes | Exception = _read_bounded_connection(
                parsed.hostname,
                target,
                deadline=deadline,
                max_bytes=max_bytes,
                connection_factory=factory,
                clock=clock,
                connection_observer=observe_connection,
            )
        except Exception as error:
            outcome = error
        outcomes.put(outcome)

    worker = Thread(
        target=perform_request,
        name="mxready-github-archive-fetch",
        daemon=True,
    )
    worker.start()

    try:
        outcome = outcomes.get(timeout=_remaining_seconds(deadline, clock))
    except Empty as error:
        with connection_lock:
            connection = active_connections[0] if active_connections else None
        if connection is not None:
            _close_connection(connection)
        raise _archive_deadline_exceeded() from error

    _remaining_seconds(deadline, clock)
    if isinstance(outcome, Exception):
        raise outcome
    return outcome


def _read_bounded_connection(
    host: str,
    target: str,
    *,
    deadline: float,
    max_bytes: int,
    connection_factory: ConnectionFactory,
    clock: Clock,
    connection_observer: Callable[[HTTPSConnection | None], None],
) -> bytes:
    connection: HTTPSConnection | None = None
    try:
        connection = connection_factory(host, _remaining_seconds(deadline, clock))
        connection_observer(connection)
        _set_connection_timeout(connection, _remaining_seconds(deadline, clock))
        connection.request(
            "GET",
            target,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "MXReady/0.1",
            },
        )
        _set_connection_timeout(connection, _remaining_seconds(deadline, clock))
        response = connection.getresponse()
        _remaining_seconds(deadline, clock)

        if response.status == 404:
            raise MxReadyError(
                "REPOSITORY_NOT_FOUND",
                "GitHub repository or requested reference was not found.",
            )
        if not 200 <= response.status < 300:
            raise MxReadyError(
                "ARCHIVE_FETCH_FAILED",
                "GitHub refused the bounded archive request.",
            )

        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > max_bytes:
            raise _repository_download_too_large(max_bytes)

        chunks: list[bytes] = []
        downloaded = 0
        while True:
            remaining_time = _remaining_seconds(deadline, clock)
            _set_connection_timeout(connection, remaining_time)
            read_size = min(_COPY_CHUNK_BYTES, max_bytes + 1 - downloaded)
            chunk = response.read(read_size)
            _remaining_seconds(deadline, clock)
            if not chunk:
                break
            downloaded += len(chunk)
            if downloaded > max_bytes:
                raise _repository_download_too_large(max_bytes)
            chunks.append(chunk)
    except MxReadyError:
        raise
    except (HTTPException, OSError, TimeoutError, ValueError) as error:
        raise MxReadyError(
            "ARCHIVE_FETCH_FAILED",
            "GitHub archive retrieval failed within the configured safety limit.",
        ) from error
    finally:
        if connection is not None:
            _close_connection(connection)
        connection_observer(None)

    return b"".join(chunks)


def _create_https_connection(host: str, timeout: float) -> HTTPSConnection:
    return HTTPSConnection(host, timeout=timeout)


def _set_connection_timeout(connection: HTTPSConnection, timeout: float) -> None:
    connection.timeout = timeout
    if connection.sock is not None:
        connection.sock.settimeout(timeout)


def _close_connection(connection: HTTPSConnection) -> None:
    with suppress(OSError):
        connection.close()


def _remaining_seconds(deadline: float, clock: Clock) -> float:
    remaining = deadline - clock()
    if remaining <= 0:
        raise _archive_deadline_exceeded()
    return remaining


def _archive_deadline_exceeded() -> MxReadyError:
    return MxReadyError(
        "ARCHIVE_FETCH_FAILED",
        "GitHub archive retrieval exceeded the total time limit.",
    )


def _validate_central_directory(archive_bytes: bytes, *, max_members: int) -> int:
    record = _find_end_of_central_directory(archive_bytes)
    (
        _,
        disk_number,
        directory_disk,
        disk_entries,
        total_entries,
        directory_size,
        directory_offset,
        _,
    ) = record
    if disk_number != 0 or directory_disk != 0 or disk_entries != total_entries:
        raise _invalid_archive_structure()
    if total_entries == _ZIP64_COUNT:
        raise MxReadyError(
            "TOO_MANY_FILES",
            f"Repository archive contains more than {max_members} entries.",
        )
    if directory_size == _ZIP64_SIZE or directory_offset == _ZIP64_SIZE:
        raise _invalid_archive_structure()
    if total_entries > max_members:
        raise MxReadyError(
            "TOO_MANY_FILES",
            f"Repository archive contains more than {max_members} entries.",
        )

    directory_end = directory_offset + directory_size
    if directory_end > len(archive_bytes):
        raise _invalid_archive_structure()

    position = directory_offset
    counted = 0
    while position < directory_end:
        if archive_bytes[position : position + 4] != _CENTRAL_DIRECTORY_SIGNATURE:
            raise _invalid_archive_structure()
        if position + 46 > directory_end:
            raise _invalid_archive_structure()
        filename_length, extra_length, comment_length = struct.unpack_from(
            "<HHH",
            archive_bytes,
            position + 28,
        )
        entry_size = 46 + filename_length + extra_length + comment_length
        position += entry_size
        counted += 1
        if counted > max_members:
            raise MxReadyError(
                "TOO_MANY_FILES",
                f"Repository archive contains more than {max_members} entries.",
            )

    if position != directory_end or counted != total_entries:
        raise _invalid_archive_structure()
    return counted


def _find_end_of_central_directory(archive_bytes: bytes) -> tuple:
    search_start = max(
        0,
        len(archive_bytes)
        - _END_OF_CENTRAL_DIRECTORY_SIZE
        - _MAX_ZIP_COMMENT_BYTES,
    )
    search_end = len(archive_bytes)

    while search_end >= search_start:
        offset = archive_bytes.rfind(
            _END_OF_CENTRAL_DIRECTORY_SIGNATURE,
            search_start,
            search_end,
        )
        if offset < 0:
            break
        if offset + _END_OF_CENTRAL_DIRECTORY_SIZE <= len(archive_bytes):
            record = struct.unpack_from("<4s4H2LH", archive_bytes, offset)
            comment_length = record[-1]
            if offset + _END_OF_CENTRAL_DIRECTORY_SIZE + comment_length == len(
                archive_bytes
            ):
                return record
        search_end = offset
    raise _invalid_archive_structure()


def _invalid_archive_structure() -> MxReadyError:
    return MxReadyError(
        "INVALID_REPOSITORY_ARCHIVE",
        "Repository archive central directory is invalid.",
    )


def _remove_owned_staging(staging: Path) -> None:
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)


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
