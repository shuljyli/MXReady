from __future__ import annotations

import hashlib
from contextlib import suppress
from pathlib import Path

import pytest
from mxready.errors import MxReadyError
from mxready.scanning.indexer import build_file_index


def test_indexer_skips_build_binary_and_symlink(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    source = tmp_path / "src" / "extension.py"
    source.write_text("CUDA_HOME = '/usr/local/cuda'", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text(
        "ignored = True",
        encoding="utf-8",
    )
    (tmp_path / "weights.bin").write_bytes(b"\x00\x01")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "cached.py").write_text(
        "ignored = True",
        encoding="utf-8",
    )

    link = tmp_path / "linked.py"
    with suppress(OSError):
        link.symlink_to(source)

    index = build_file_index(tmp_path)

    assert [item.relative_path for item in index.files] == ["src/extension.py"]
    assert index.files[0].sha256 == hashlib.sha256(source.read_bytes()).hexdigest()


def test_indexer_decodes_utf8_bom_and_gb18030_in_lexical_order(
    tmp_path: Path,
) -> None:
    (tmp_path / "z.py").write_bytes("print('沐曦')".encode("gb18030"))
    (tmp_path / "a.py").write_bytes(b"\xef\xbb\xbfprint('MXReady')")
    (tmp_path / "CMakeLists.txt").write_text(
        "project(mxready LANGUAGES CXX CUDA)",
        encoding="utf-8",
    )

    index = build_file_index(tmp_path)

    assert [item.relative_path for item in index.files] == [
        "CMakeLists.txt",
        "a.py",
        "z.py",
    ]
    assert index.files[1].text == "print('MXReady')"
    assert index.files[2].text == "print('沐曦')"


def test_indexer_warns_and_skips_oversized_binary_and_undecodable_text(
    tmp_path: Path,
) -> None:
    (tmp_path / "large.py").write_text("x" * 5, encoding="utf-8")
    (tmp_path / "binary.py").write_bytes(b"x\x00")
    (tmp_path / "unknown.py").write_bytes(b"\xff\xff")

    index = build_file_index(tmp_path, max_file_bytes=4)

    assert index.files == ()
    assert {(warning.code, warning.relative_path) for warning in index.warnings} == {
        ("BINARY_FILE_SKIPPED", "binary.py"),
        ("FILE_TOO_LARGE", "large.py"),
        ("UNSUPPORTED_TEXT_ENCODING", "unknown.py"),
    }


def test_indexer_rejects_more_than_the_bounded_number_of_source_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "one.py").write_text("one = 1", encoding="utf-8")
    (tmp_path / "two.py").write_text("two = 2", encoding="utf-8")

    with pytest.raises(MxReadyError) as error:
        build_file_index(tmp_path, max_files=1)

    assert error.value.code == "TOO_MANY_FILES"
