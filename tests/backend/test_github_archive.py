from __future__ import annotations

import io
import json
import stat
import threading
import time
import zipfile
from pathlib import Path

import pytest
from mxready.errors import MxReadyError
from mxready.repository.git_client import RepositoryLimits
from mxready.repository.github_archive import (
    GitHubArchiveClient,
    _safe_member_parts,
    read_bounded_url,
)
from mxready.repository.identity import parse_repository_url


class RecordingHttpReader:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, float, int]] = []

    def __call__(self, url: str, *, timeout: float, max_bytes: int) -> bytes:
        self.calls.append((url, timeout, max_bytes))
        return self.responses.pop(0)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeSocket:
    def __init__(self) -> None:
        self.timeouts: list[float] = []

    def settimeout(self, timeout: float) -> None:
        self.timeouts.append(timeout)


class SlowResponse:
    status = 200
    headers: dict[str, str] = {}

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.read_count = 0

    def read(self, size: int) -> bytes:
        self.clock.advance(0.6)
        self.read_count += 1
        return b"x" if self.read_count <= 2 else b""


class FakeHttpsConnection:
    def __init__(self, response: SlowResponse) -> None:
        self.response = response
        self.sock = FakeSocket()
        self.requests: list[tuple[str, str]] = []
        self.closed = False

    def request(self, method: str, target: str, *, headers) -> None:
        self.requests.append((method, target))

    def getresponse(self) -> SlowResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


class EmptyResponse:
    status = 200
    headers: dict[str, str] = {}

    def read(self, size: int) -> bytes:
        return b""


class BlockingPhaseConnection:
    def __init__(self, blocked_phase: str) -> None:
        self.blocked_phase = blocked_phase
        self.sock = FakeSocket()
        self.release = threading.Event()
        self.closed = False

    def request(self, method: str, target: str, *, headers) -> None:
        if self.blocked_phase == "request":
            self.release.wait(timeout=1.0)

    def getresponse(self) -> EmptyResponse:
        if self.blocked_phase == "headers":
            self.release.wait(timeout=1.0)
        return EmptyResponse()

    def close(self) -> None:
        self.closed = True
        self.release.set()


def _zip(entries: list[tuple[str, bytes, int | None]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content, mode in entries:
            info = zipfile.ZipInfo("placeholder")
            info.filename = name
            if mode is not None:
                info.external_attr = mode << 16
            archive.writestr(info, content)
    payload = output.getvalue()
    for name, _, _ in entries:
        if "\\" in name:
            payload = payload.replace(
                name.replace("\\", "/").encode(),
                name.encode(),
            )
    return payload


def test_archive_client_resolves_commit_and_extracts_bounded_regular_files(
    tmp_path: Path,
) -> None:
    commit = "a" * 40
    archive = _zip(
        [
            (f"extension-cpp-{commit}/README.md", b"hello", stat.S_IFREG | 0o644),
            (f"extension-cpp-{commit}/src/op.cu", b"kernel", stat.S_IFREG | 0o644),
            (f"extension-cpp-{commit}/link", b"README.md", stat.S_IFLNK | 0o777),
        ]
    )
    reader = RecordingHttpReader(
        [json.dumps({"sha": commit}).encode(), archive]
    )
    destination = tmp_path / "repository"

    resolved = GitHubArchiveClient(http_reader=reader).clone(
        parse_repository_url("https://github.com/pytorch/extension-cpp"),
        None,
        destination,
    )

    assert resolved == commit
    assert (destination / "README.md").read_text(encoding="utf-8") == "hello"
    assert (destination / "src" / "op.cu").read_text(encoding="utf-8") == "kernel"
    assert not (destination / "link").exists()
    assert reader.calls == [
        (
            "https://api.github.com/repos/pytorch/extension-cpp/commits/HEAD",
            60,
            1_048_576,
        ),
        (
            f"https://codeload.github.com/pytorch/extension-cpp/zip/{commit}",
            60,
            52_428_800,
        ),
    ]


def test_archive_client_encodes_a_valid_named_ref(tmp_path: Path) -> None:
    commit = "b" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip([(f"repo-{commit}/README.md", b"ok", None)]),
        ]
    )

    GitHubArchiveClient(http_reader=reader).clone(
        parse_repository_url("https://github.com/owner/repo"),
        "release/v1",
        tmp_path / "repository",
    )

    assert reader.calls[0][0].endswith("/commits/release%2Fv1")


@pytest.mark.parametrize(
    "malicious_name",
    [
        "root/../../escape.txt",
        "/root/absolute.txt",
        "root/./ambiguous.txt",
    ],
)
def test_archive_client_rejects_unsafe_member_paths(
    malicious_name: str,
    tmp_path: Path,
) -> None:
    commit = "c" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip([(malicious_name, b"unsafe", None)]),
        ]
    )

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=reader).clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == "INVALID_REPOSITORY_ARCHIVE"
    assert not (tmp_path / "escape.txt").exists()


def test_archive_path_validation_rejects_raw_backslashes() -> None:
    with pytest.raises(MxReadyError):
        _safe_member_parts("root\\windows.txt")


def test_archive_client_rejects_case_insensitive_duplicate_paths(
    tmp_path: Path,
) -> None:
    commit = "d" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip(
                [
                    ("root/README.md", b"one", None),
                    ("root/readme.md", b"two", None),
                ]
            ),
        ]
    )

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=reader).clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == "INVALID_REPOSITORY_ARCHIVE"


def test_archive_client_bounds_all_members_including_directories(
    tmp_path: Path,
) -> None:
    commit = "f" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip(
                [
                    ("root/one/", b"", None),
                    ("root/two/", b"", None),
                ]
            ),
        ]
    )

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(
            http_reader=reader,
            limits=RepositoryLimits(max_files=1),
        ).clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == "TOO_MANY_FILES"


@pytest.mark.parametrize(
    ("limits", "entries", "expected_code"),
    [
        (
            RepositoryLimits(max_bytes=3),
            [("root/file.txt", b"1234", None)],
            "REPOSITORY_TOO_LARGE",
        ),
        (
            RepositoryLimits(max_files=1),
            [
                ("root/one.txt", b"1", None),
                ("root/two.txt", b"2", None),
            ],
            "TOO_MANY_FILES",
        ),
    ],
)
def test_archive_client_enforces_uncompressed_repository_limits(
    limits: RepositoryLimits,
    entries: list[tuple[str, bytes, int | None]],
    expected_code: str,
    tmp_path: Path,
) -> None:
    commit = "e" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip(entries),
        ]
    )

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=reader, limits=limits).clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == expected_code


def test_archive_client_removes_partial_staging_after_extraction_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    commit = "1" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip([("root/file.txt", b"content", None)]),
        ]
    )
    client = GitHubArchiveClient(http_reader=reader)

    def fail_extraction(*args, **kwargs) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(client, "_extract_file", fail_extraction)
    destination = tmp_path / "repository"

    with pytest.raises(MxReadyError):
        client.clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            destination,
        )

    assert not destination.exists()
    assert not (tmp_path / ".repository.mxready-partial").exists()


def test_archive_client_does_not_remove_staging_it_did_not_create(
    tmp_path: Path,
    monkeypatch,
) -> None:
    commit = "2" * 40
    reader = RecordingHttpReader(
        [
            json.dumps({"sha": commit}).encode(),
            _zip([("root/file.txt", b"content", None)]),
        ]
    )
    destination = tmp_path / "repository"
    staging = tmp_path / ".repository.mxready-partial"
    sentinel = staging / "owned-by-another-process.txt"
    original_mkdir = Path.mkdir

    def lose_creation_race(path: Path, *args, **kwargs) -> None:
        if path == staging:
            original_mkdir(path)
            sentinel.write_text("keep", encoding="utf-8")
            raise FileExistsError("simulated staging race")
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", lose_creation_race)

    with pytest.raises(MxReadyError):
        GitHubArchiveClient(http_reader=reader).clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            destination,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_archive_client_rejects_non_github_identity(tmp_path: Path) -> None:
    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=RecordingHttpReader([])).clone(
            parse_repository_url("https://gitee.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == "ARCHIVE_FALLBACK_UNAVAILABLE"


def test_http_reader_enforces_one_total_deadline_across_slow_chunks() -> None:
    clock = FakeClock()
    response = SlowResponse(clock)
    connection = FakeHttpsConnection(response)

    with pytest.raises(MxReadyError) as error:
        read_bounded_url(
            "https://api.github.com/repos/owner/repo/commits/HEAD",
            timeout=1.0,
            max_bytes=100,
            connection_factory=lambda host, timeout: connection,
            clock=clock,
        )

    assert error.value.code == "ARCHIVE_FETCH_FAILED"
    assert response.read_count == 2
    assert connection.closed is True
    assert connection.sock.timeouts[0] == pytest.approx(1.0)
    assert connection.sock.timeouts[-1] == pytest.approx(0.4)


@pytest.mark.parametrize("blocked_phase", ["request", "headers"])
def test_http_reader_hard_deadline_covers_connection_and_headers(
    blocked_phase: str,
) -> None:
    connection = BlockingPhaseConnection(blocked_phase)
    started = time.monotonic()

    with pytest.raises(MxReadyError) as error:
        read_bounded_url(
            "https://api.github.com/repos/owner/repo/commits/HEAD",
            timeout=0.05,
            max_bytes=100,
            connection_factory=lambda host, timeout: connection,
        )

    elapsed = time.monotonic() - started
    assert error.value.code == "ARCHIVE_FETCH_FAILED"
    assert elapsed < 0.5
    assert connection.closed is True
