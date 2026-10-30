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


@pytest.mark.parametrize(
    "filename",
    ["Makefile", "makefile", "GNUmakefile", "build.mk", "cmake/platform.mk"],
)
def test_indexer_collects_make_build_files(tmp_path: Path, filename: str) -> None:
    """Make 构建文件必须进索引：CUDA 侧大量项目（含 cuda-samples）靠它构建，
    cu-bridge 的 make_maca 也是 make 包装器。缺了它，`NVCC = nvcc` 永远不可见。"""
    target = tmp_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("NVCC = nvcc\n", encoding="utf-8")

    index = build_file_index(tmp_path)

    assert [item.relative_path for item in index.files] == [filename]


def test_indexer_ignores_make_like_names_with_other_extensions(tmp_path: Path) -> None:
    """`Makefile.bak` 不是构建入口——扩展名不在白名单、文件名也不完全匹配。"""
    (tmp_path / "Makefile.bak").write_text("NVCC = nvcc\n", encoding="utf-8")

    assert build_file_index(tmp_path).files == ()


@pytest.mark.parametrize(
    "directory",
    [".pytest-temp", ".pytest_tmp", ".pytest-tmp", ".pytest_cache", ".benchmarks"],
)
def test_indexer_skips_test_runner_scratch_directories(
    tmp_path: Path,
    directory: str,
) -> None:
    """测试运行器的临时目录是夹具副本，不属于仓库内容，且每次运行都会漂移。"""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "kernel.cu").write_text("__global__ void k() {}\n", encoding="utf-8")
    (tmp_path / directory).mkdir()
    (tmp_path / directory / "kernel.cu").write_text(
        'asm volatile ("mov.u32 %0, %%laneid;" : "=r"(x));\n',
        encoding="utf-8",
    )

    index = build_file_index(tmp_path)

    assert [item.relative_path for item in index.files] == ["src/kernel.cu"]


def test_indexer_keeps_pytest_like_names_that_are_not_scratch_dirs(tmp_path: Path) -> None:
    """按前缀排除，不做子串匹配：`pytest_plugin/` 这类真实目录仍需索引。"""
    (tmp_path / "pytest_plugin").mkdir()
    (tmp_path / "pytest_plugin" / "conftest.py").write_text("x = 1\n", encoding="utf-8")

    index = build_file_index(tmp_path)

    assert [item.relative_path for item in index.files] == ["pytest_plugin/conftest.py"]
