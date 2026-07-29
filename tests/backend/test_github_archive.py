from __future__ import annotations

import io
import json
import stat
import zipfile
from pathlib import Path

import pytest
from mxready.errors import MxReadyError
from mxready.repository.git_client import RepositoryLimits
from mxready.repository.github_archive import GitHubArchiveClient, _safe_member_parts
from mxready.repository.identity import parse_repository_url


class RecordingHttpReader:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, float, int]] = []

    def __call__(self, url: str, *, timeout: float, max_bytes: int) -> bytes:
        self.calls.append((url, timeout, max_bytes))
        return self.responses.pop(0)


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


def test_archive_client_rejects_non_github_identity(tmp_path: Path) -> None:
    with pytest.raises(MxReadyError) as error:
        GitHubArchiveClient(http_reader=RecordingHttpReader([])).clone(
            parse_repository_url("https://gitee.com/owner/repo"),
            None,
            tmp_path / "repository",
        )

    assert error.value.code == "ARCHIVE_FALLBACK_UNAVAILABLE"
