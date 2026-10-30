"""工具链画像的回归测试。

背景：MXR-TOOLCHAIN-001 的前提是"项目尚未接入 MXMACA 兼容层"。cu-bridge 会在构建期
接管 nvcc/make，此时 `NVCC = nvcc` 是预期写法；继续报 blocker 等于把已迁移项目判成
未迁移。但降级必须只覆盖声明式构建文件——.py/.sh 里的 nvcc 是运行时命令，可能绕过
包装器的 PATH 注入，那属于真问题。
"""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from mxready.models import Severity, StaticStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog

CATALOG = load_rule_catalog(Path("src/mxready/resources/rules/v1"))

_CU_BRIDGE_MAKEFILE = """NVCC = nvcc
all:
\t$(NVCC) -O3 -o app main.cu

maca:
\tmake_maca
"""

_NVIDIA_MAKEFILE = """NVCC = nvcc
all:
\t$(NVCC) -O3 -o app main.cu
"""

_KERNEL = "#include <cuda_runtime.h>\n"


def _scan(root: Path):
    clone = "https://gitee.com/metax-maca/demo"
    commit = "d" * 40
    return ScanAnalyzer(CATALOG).analyze(
        root,
        repository_url=clone,
        commit=commit,
        scan_id=uuid5(NAMESPACE_URL, f"{clone}@{commit}"),
        stage_callback=lambda _status: None,
    )


def _write(root: Path, name: str, text: str) -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def _severities(report, rule_id: str) -> dict[str, Severity]:
    return {
        finding.relative_path: finding.severity
        for finding in report.findings
        if finding.rule_id == rule_id
    }


def test_makefile_nvcc_is_a_blocker_when_cu_bridge_is_absent(tmp_path: Path) -> None:
    """先钉住旧行为：没有 cu-bridge 时 Makefile 里的 nvcc 必须是阻塞项。

    这条用例在修复"Makefile 不在索引/规则作用域"之前是**失败**的——那时整个仓库
    返回 passed，等于把未迁移项目判成已迁移。
    """
    _write(tmp_path, "Makefile", _NVIDIA_MAKEFILE)
    _write(tmp_path, "main.cu", _KERNEL)

    report = _scan(tmp_path)

    assert _severities(report, "MXR-TOOLCHAIN-001") == {"Makefile": Severity.BLOCKER}
    assert report.static_status is StaticStatus.BLOCKED
    assert not [
        warning
        for warning in report.analysis_warnings
        if warning.code == "TOOLCHAIN_CU_BRIDGE_DOWNGRADE"
    ]


def test_cu_bridge_downgrades_build_definition_hits(tmp_path: Path) -> None:
    _write(tmp_path, "Makefile", _CU_BRIDGE_MAKEFILE)
    _write(tmp_path, "main.cu", _KERNEL)

    report = _scan(tmp_path)

    assert _severities(report, "MXR-TOOLCHAIN-001") == {"Makefile": Severity.WARNING}
    assert _severities(report, "MXR-TOOLCHAIN-002") == {"Makefile": Severity.INFO}
    assert report.static_status is StaticStatus.WARNINGS
    messages = [
        warning.message
        for warning in report.analysis_warnings
        if warning.code == "TOOLCHAIN_CU_BRIDGE_DOWNGRADE"
    ]
    assert len(messages) == 1
    assert "MXR-TOOLCHAIN-001" in messages[0]
    assert "1 个文件" in messages[0]


def test_downgraded_finding_keeps_an_audit_note(tmp_path: Path) -> None:
    """降级必须留痕：finding 自身要说明为什么不再是 blocker。"""
    _write(tmp_path, "Makefile", _CU_BRIDGE_MAKEFILE)

    report = _scan(tmp_path)

    finding = next(item for item in report.findings if item.rule_id == "MXR-TOOLCHAIN-001")
    assert "cu-bridge" in finding.message
    assert "blocker 降为 warning" in finding.message


def test_cu_bridge_keeps_imperative_nvcc_call_as_blocker(tmp_path: Path) -> None:
    """.py 里的 subprocess 调用是运行时行为，可能绕过 make_maca 的 PATH 注入。"""
    _write(tmp_path, "Makefile", _CU_BRIDGE_MAKEFILE)
    _write(
        tmp_path,
        "build.py",
        'import subprocess\nsubprocess.run(["nvcc", "main.cu"], check=True)\n',
    )

    report = _scan(tmp_path)

    assert _severities(report, "MXR-TOOLCHAIN-001") == {
        "Makefile": Severity.WARNING,
        "build.py": Severity.BLOCKER,
    }
    assert report.static_status is StaticStatus.BLOCKED


def test_cu_bridge_keeps_shell_nvcc_call_as_blocker(tmp_path: Path) -> None:
    _write(tmp_path, "Makefile", _CU_BRIDGE_MAKEFILE)
    _write(tmp_path, "scripts/build.sh", "#!/bin/sh\nnvcc -O3 -o app main.cu\n")

    report = _scan(tmp_path)

    assert _severities(report, "MXR-TOOLCHAIN-001")["scripts/build.sh"] is Severity.BLOCKER


def test_summary_counts_follow_the_downgraded_severity(tmp_path: Path) -> None:
    """降级若发生在汇总之后，summary 会与 findings 对不上。"""
    _write(tmp_path, "Makefile", _CU_BRIDGE_MAKEFILE)

    report = _scan(tmp_path)

    blockers = sum(1 for item in report.findings if item.severity is Severity.BLOCKER)
    warnings = sum(1 for item in report.findings if item.severity is Severity.WARNING)
    assert report.summary.blocker_count == blockers
    assert report.summary.warning_count == warnings


@pytest.mark.parametrize(
    ("name", "text"),
    [
        # 注释里的 make_maca 不算接入
        ("Makefile", "# 迁移时请改用 make_maca\nNVCC = nvcc\n"),
        # 只有 MACA_CLANG_PATH（MACA SDK 自带，非 cu-bridge 证据）
        ("run.sh", "export MACA_CLANG_PATH=/opt/maca/mxgpu_llvm/bin\n"),
        # 普通文本提及
        ("README.md", "本项目尚未接入 cu-bridge。\n"),
    ],
)
def test_cu_bridge_marker_requires_real_build_evidence(
    tmp_path: Path,
    name: str,
    text: str,
) -> None:
    _write(tmp_path, name, text)

    report = _scan(tmp_path)

    assert not [item for item in report.findings if item.rule_id == "MXR-TOOLCHAIN-002"], name


@pytest.mark.parametrize(
    "text",
    [
        "all:\n\tmake_maca\n",
        "cmake -B build && cmake_maca build\n",
        "export CUCC_PATH=/opt/maca/tools/cu-bridge\n",
        "export CUCC_CMAKE_ENTRY=2\n",
        "PATH=/opt/maca/tools/cu-bridge/bin:$PATH\n",
        "cucc -O3 -o app main.cu\n",
    ],
)
def test_cu_bridge_markers_cover_documented_entry_points(
    tmp_path: Path,
    text: str,
) -> None:
    _write(tmp_path, "Makefile", text)

    report = _scan(tmp_path)

    assert "MXR-TOOLCHAIN-002" in {item.rule_id for item in report.findings}, text
