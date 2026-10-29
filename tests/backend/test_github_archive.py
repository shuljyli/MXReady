from __future__ import annotations

import io
import json
import stat
import struct
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
    _validate_central_directory,
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
    reader = RecordingHttpReader([json.dumps({"sha": commit}).encode(), archive])
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


# --- 畸形归档：解包器是唯一会向磁盘写文件的组件，攻面必须逐条钉住 ---


def _member_info(
    name: str,
    *,
    mode: int = stat.S_IFREG | 0o644,
    flag_bits: int = 0,
    size: int = 0,
) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.external_attr = mode << 16
    info.flag_bits = flag_bits
    info.file_size = size
    return info


@pytest.mark.parametrize(
    ("members", "expected_message", "limits"),
    [
        # ZipCrypto 条目：内容读不出，等于把不可审计的字节写进工作区
        (
            [_member_info("root/a.txt", flag_bits=0x1)],
            "Encrypted repository archive entries",
            RepositoryLimits(),
        ),
        # 命名管道 / 设备节点：解包后是特殊文件，后续扫描可能阻塞在 open() 上
        (
            [_member_info("root/fifo", mode=stat.S_IFIFO | 0o644)],
            "unsupported file type",
            RepositoryLimits(),
        ),
        (
            [_member_info("root/blk", mode=stat.S_IFBLK | 0o644)],
            "unsupported file type",
            RepositoryLimits(),
        ),
        # 只有一层且不是目录：无法确定仓库根，按不安全路径拒绝
        (
            [_member_info("root")],
            "unsafe path",
            RepositoryLimits(),
        ),
        # 两个顶层目录：无法判断哪个是仓库根
        (
            [_member_info("root/a.txt"), _member_info("other/b.txt")],
            "exactly one top-level directory",
            RepositoryLimits(),
        ),
    ],
)
def test_archive_members_reject_unsafe_entry_types(
    members: list[zipfile.ZipInfo],
    expected_message: str,
    limits: RepositoryLimits,
) -> None:
    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(limits=limits)._validate_members(members)

    assert error.value.code in {"INVALID_REPOSITORY_ARCHIVE", "TOO_MANY_FILES"}
    assert expected_message in error.value.message


def test_archive_members_skip_symbolic_links() -> None:
    """符号链接条目被丢弃而不是解包：否则最终落盘路径由归档自己决定。"""
    members = [
        _member_info("root/real.txt", size=1),
        _member_info("root/link", mode=stat.S_IFLNK | 0o777),
    ]

    regular = GitHubArchiveClient()._validate_members(members)

    assert [info.filename for info, _ in regular] == ["root/real.txt"]


def test_archive_members_skip_directory_entries() -> None:
    members = [
        _member_info("root/sub/"),
        _member_info("root/sub/a.txt", size=1),
    ]

    regular = GitHubArchiveClient()._validate_members(members)

    assert [parts for _, parts in regular] == [("sub", "a.txt")]


def test_archive_client_rejects_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "repository"
    destination.mkdir()
    reader = RecordingHttpReader([json.dumps({"sha": "a" * 40}).encode()])
    client = GitHubArchiveClient(http_reader=reader)

    with pytest.raises(MxReadyError) as error:
        client._extract_archive(b"", destination)

    assert error.value.code == "INVALID_REPOSITORY_ARCHIVE"
    assert "already exists" in error.value.message


def test_archive_client_rejects_existing_staging_directory(tmp_path: Path) -> None:
    destination = tmp_path / "repository"
    (tmp_path / ".repository.mxready-partial").mkdir()

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient()._extract_archive(b"", destination)

    assert "already exists" in error.value.message


class _StaticArchive:
    """只提供 `_extract_file` 所需的 `open()`，用于伪造声明尺寸与实际内容不一致。"""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def open(self, info: zipfile.ZipInfo, mode: str = "r") -> io.BytesIO:
        assert mode == "r"
        return io.BytesIO(self.payload)


def test_extract_file_rejects_expansion_beyond_declared_size(tmp_path: Path) -> None:
    """防 zip bomb 的声明欺骗：实际字节多于 `file_size` 时立即中止。"""
    info = _member_info("root/a.txt", size=3)
    target = tmp_path / "a.txt"

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient()._extract_file(
            _StaticArchive(b"1234567890"),
            info,
            target,
        )

    assert error.value.code == "INVALID_REPOSITORY_ARCHIVE"
    assert "expanded beyond its declared size" in error.value.message


def test_extract_file_rejects_truncated_content(tmp_path: Path) -> None:
    info = _member_info("root/a.txt", size=10)
    target = tmp_path / "a.txt"

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient()._extract_file(
            _StaticArchive(b"12345"),
            info,
            target,
        )

    assert "did not match its declaration" in error.value.message


def test_extract_file_writes_exact_declared_content(tmp_path: Path) -> None:
    info = _member_info("root/a.txt", size=5)
    target = tmp_path / "a.txt"

    GitHubArchiveClient()._extract_file(_StaticArchive(b"12345"), info, target)

    assert target.read_bytes() == b"12345"


# --- 中央目录自解析：zipfile 之前先独立核对结构，避免信任归档自报的条目数 ---


def _end_of_central_directory(
    *,
    disk_number: int = 0,
    directory_disk: int = 0,
    disk_entries: int = 1,
    total_entries: int = 1,
    directory_size: int = 46,
    directory_offset: int = 0,
    prefix: bytes | None = None,
) -> bytes:
    body = prefix if prefix is not None else b"PK\x01\x02" + bytes(42)
    record = struct.pack(
        "<4s4H2LH",
        b"PK\x05\x06",
        disk_number,
        directory_disk,
        disk_entries,
        total_entries,
        directory_size,
        directory_offset,
        0,
    )
    return body + record


def test_central_directory_accepts_a_minimal_consistent_archive() -> None:
    assert (
        _validate_central_directory(
            _end_of_central_directory(),
            max_members=10,
        )
        == 1
    )


def test_central_directory_rejects_missing_end_record() -> None:
    with pytest.raises(MxReadyError) as error:
        _validate_central_directory(b"not a zip archive at all", max_members=10)

    assert error.value.code == "INVALID_REPOSITORY_ARCHIVE"


@pytest.mark.parametrize(
    ("overrides", "expected_code", "expected_message"),
    [
        # 分卷归档：单文件解析出的目录不完整
        ({"disk_number": 1}, "INVALID_REPOSITORY_ARCHIVE", "central directory is invalid"),
        ({"disk_entries": 0}, "INVALID_REPOSITORY_ARCHIVE", "central directory is invalid"),
        # zip64 哨兵值：真实条目数交给别的字段表达，本解析器不跟进
        ({"total_entries": 0xFFFF, "disk_entries": 0xFFFF}, "TOO_MANY_FILES", "more than"),
        (
            {"directory_offset": 0xFFFFFFFF},
            "INVALID_REPOSITORY_ARCHIVE",
            "central directory is invalid",
        ),
        # 目录区越界
        ({"directory_size": 1 << 20}, "INVALID_REPOSITORY_ARCHIVE", "central directory is invalid"),
        # 条目数与实际遍历结果不符
        ({"total_entries": 2}, "INVALID_REPOSITORY_ARCHIVE", "central directory is invalid"),
    ],
)
def test_central_directory_rejects_structurally_invalid_archives(
    overrides: dict[str, int],
    expected_code: str,
    expected_message: str,
) -> None:
    with pytest.raises(MxReadyError) as error:
        _validate_central_directory(
            _end_of_central_directory(**overrides),
            max_members=10,
        )

    assert error.value.code == expected_code
    assert expected_message in error.value.message


def test_central_directory_rejects_bad_entry_signature() -> None:
    payload = _end_of_central_directory(prefix=b"XXXX" + bytes(42))

    with pytest.raises(MxReadyError) as error:
        _validate_central_directory(payload, max_members=10)

    assert "central directory is invalid" in error.value.message


def test_central_directory_rejects_truncated_entry_header() -> None:
    payload = _end_of_central_directory(
        directory_size=10,
        prefix=b"PK\x01\x02" + bytes(6),
    )

    with pytest.raises(MxReadyError) as error:
        _validate_central_directory(payload, max_members=10)

    assert "central directory is invalid" in error.value.message


def test_central_directory_rejects_entry_count_above_limit() -> None:
    with pytest.raises(MxReadyError) as error:
        _validate_central_directory(
            _end_of_central_directory(total_entries=5, disk_entries=5),
            max_members=4,
        )

    assert error.value.code == "TOO_MANY_FILES"


def test_central_directory_counts_entries_before_trusting_the_declaration() -> None:
    """声明 0 个条目却真的带一个条目：以遍历结果为准，不采信自报数。"""
    with pytest.raises(MxReadyError) as error:
        _validate_central_directory(
            _end_of_central_directory(total_entries=0, disk_entries=0),
            max_members=0,
        )

    assert error.value.code == "TOO_MANY_FILES"


# --- 提交解析：GitHub 返回的 sha 必须与请求的锁定提交一致 ---


@pytest.mark.parametrize(
    "metadata",
    [
        b"not json",
        b"[1, 2, 3]",
        b'{"sha": "abc"}',
        b'{"sha": "' + b"Z" * 40 + b'"}',
    ],
)
def test_archive_client_rejects_invalid_commit_metadata(
    metadata: bytes,
    tmp_path: Path,
) -> None:
    reader = RecordingHttpReader([metadata])

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=reader).clone(
            parse_repository_url("https://github.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == "INVALID_REPOSITORY_ARCHIVE"


def test_archive_client_rejects_substituted_commit(tmp_path: Path) -> None:
    """请求锁定提交、却被解析到另一个提交时必须失败，否则证据无法追责。"""
    requested = "1" * 40
    reader = RecordingHttpReader([json.dumps({"sha": "2" * 40}).encode()])

    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=reader).clone(
            parse_repository_url("https://github.com/owner/repo"),
            requested,
            tmp_path / "repository",
        )

    assert "different commit than the one requested" in error.value.message


# --- 受限 HTTP：状态码、Content-Length 与流式读取都必须落在上限内 ---


class FixedResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status = status
        self.headers = headers or {}
        self._body = body
        self._offset = 0

    def read(self, size: int) -> bytes:
        chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class FixedConnection:
    def __init__(self, response: FixedResponse) -> None:
        self.response = response
        self.sock = FakeSocket()
        self.closed = False

    def request(self, method: str, target: str, *, headers) -> None:
        self.method = method
        self.target = target

    def getresponse(self) -> FixedResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


def _read_with(response: FixedResponse, *, max_bytes: int = 100) -> bytes:
    connection = FixedConnection(response)
    return read_bounded_url(
        "https://codeload.github.com/owner/repo/zip/" + "a" * 40,
        timeout=5.0,
        max_bytes=max_bytes,
        connection_factory=lambda host, timeout: connection,
    )


def test_http_reader_maps_missing_repository_to_not_found() -> None:
    with pytest.raises(MxReadyError) as error:
        _read_with(FixedResponse(status=404))

    assert error.value.code == "REPOSITORY_NOT_FOUND"


@pytest.mark.parametrize("status", [301, 403, 429, 500, 503])
def test_http_reader_rejects_non_success_status(status: int) -> None:
    with pytest.raises(MxReadyError) as error:
        _read_with(FixedResponse(status=status))

    assert error.value.code == "ARCHIVE_FETCH_FAILED"


def test_http_reader_rejects_declared_content_length_above_limit() -> None:
    """先看 Content-Length 就能拒掉，避免为一个已知过大的归档开辟缓冲区。"""
    with pytest.raises(MxReadyError) as error:
        _read_with(
            FixedResponse(headers={"Content-Length": "999999"}),
            max_bytes=100,
        )

    assert error.value.code == "REPOSITORY_TOO_LARGE"


def test_http_reader_rejects_streamed_body_above_limit() -> None:
    """Content-Length 可以缺失或撒谎，流式累计才是真正的兜底。"""
    with pytest.raises(MxReadyError) as error:
        _read_with(FixedResponse(body=b"x" * 500), max_bytes=100)

    assert error.value.code == "REPOSITORY_TOO_LARGE"


def test_http_reader_returns_body_within_limit() -> None:
    assert _read_with(FixedResponse(body=b"payload"), max_bytes=100) == b"payload"


def test_http_reader_wraps_transport_failures() -> None:
    def explode(host: str, timeout: float):
        raise OSError("connection reset")

    with pytest.raises(MxReadyError) as error:
        read_bounded_url(
            "https://api.github.com/repos/owner/repo/commits/HEAD",
            timeout=5.0,
            max_bytes=100,
            connection_factory=explode,
        )

    assert error.value.code == "ARCHIVE_FETCH_FAILED"


@pytest.mark.parametrize(
    "url",
    [
        "http://api.github.com/repos/owner/repo",
        "https://evil.example.com/repos/owner/repo",
        "https://api.github.com.evil.example/x",
        "https://user:pass@api.github.com/x",
        "https://api.github.com:8443/x",
        "https://api.github.com/x#fragment",
        "https://127.0.0.1/x",
        "https://api.github.com@evil.example/x",
    ],
)
def test_http_reader_rejects_targets_outside_the_allowlist(url: str) -> None:
    """主机白名单是开放重定向与 SSRF 的唯一出口，任何变体都必须拒绝。"""
    with pytest.raises(MxReadyError) as error:
        read_bounded_url(url, timeout=5.0, max_bytes=100)

    assert error.value.code == "ARCHIVE_FETCH_FAILED"
    assert "not allowed" in error.value.message


def test_http_reader_rejects_non_positive_limits() -> None:
    with pytest.raises(ValueError):
        read_bounded_url("https://api.github.com/x", timeout=0, max_bytes=100)
    with pytest.raises(ValueError):
        read_bounded_url("https://api.github.com/x", timeout=1, max_bytes=0)
