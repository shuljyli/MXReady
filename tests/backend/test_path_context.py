"""路径上下文降级的回归测试。

背景：静态规则无法区分"交付代码"与"验证材料"。仓库的 `tests/`、`examples/`、
`docs/` 里常放 `.cu` 夹具与代码片段，写法与真实 kernel 一样，但不是迁移对象。
本仓库自扫描曾出现 22 条 blocker 全部出自测试夹具——真实用户第一次运行就会看到
"工具判定自己是阻塞状态"。

约定：非交付路径上的 blocker/warning 封顶为 `info`，文件仍被扫描、仍出现在报告里，
降级在 `message` 与 `analysis_warnings` 双重留痕。
"""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from mxready.models import Severity, StaticStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.path_context import PathRole, classify_path
from mxready.scanning.rule_loader import load_rule_catalog

CATALOG = load_rule_catalog(Path("src/mxready/resources/rules/v1"))

_PTX_KERNEL = (
    "__device__ int lane() {\n"
    '    int x; asm volatile ("mov.u32 %0, %%laneid;" : "=r"(x));\n'
    "    return x;\n"
    "}\n"
)


def _scan(root: Path):
    clone = "https://gitee.com/metax-maca/demo"
    commit = "e" * 40
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


def _path_warnings(report) -> list[str]:
    return [
        warning.message
        for warning in report.analysis_warnings
        if warning.code == "PATH_CONTEXT_DEMOTION"
    ]


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        ("csrc/kernel.cu", PathRole.SOURCE),
        ("setup.py", PathRole.SOURCE),
        ("src/mxready/scanning/indexer.py", PathRole.SOURCE),
        ("tests/kernel.cu", PathRole.TEST),
        ("tests/fixtures/repositories/cuda_extension/csrc/kernel.cu", PathRole.TEST),
        ("test/kernel.cu", PathRole.TEST),
        ("csrc/test_warp.cu", PathRole.TEST),
        ("csrc/warp_test.cpp", PathRole.TEST),
        ("fixtures/kernel.cu", PathRole.TEST),
        ("benchmarks/bench_conv.cu", PathRole.BENCHMARK),
        ("examples/kernel.cu", PathRole.EXAMPLE),
        ("samples/kernel.cu", PathRole.EXAMPLE),
        ("docs/snippets/kernel.cu", PathRole.DOC),
        # 子串不算：只有完整路径段才参与判定
        ("contest/kernel.cu", PathRole.SOURCE),
        ("attestation/kernel.cu", PathRole.SOURCE),
        ("latest/kernel.cu", PathRole.SOURCE),
        ("testing_notes/kernel.cu", PathRole.SOURCE),
    ],
)
def test_classify_path_uses_exact_segments(relative_path: str, expected: PathRole) -> None:
    assert classify_path(relative_path) is expected


def test_delivery_path_keeps_its_severity(tmp_path: Path) -> None:
    """先钉住旧行为：交付路径上的 blocker 必须原样保留。"""
    _write(tmp_path, "csrc/kernel.cu", _PTX_KERNEL)

    report = _scan(tmp_path)

    assert _severities(report, "MXR-PTX-001") == {"csrc/kernel.cu": Severity.BLOCKER}
    assert report.static_status is StaticStatus.BLOCKED
    assert _path_warnings(report) == []


def test_test_path_blocker_is_capped_to_info(tmp_path: Path) -> None:
    _write(tmp_path, "tests/kernel.cu", _PTX_KERNEL)

    report = _scan(tmp_path)

    assert _severities(report, "MXR-PTX-001") == {"tests/kernel.cu": Severity.INFO}
    assert report.summary.blocker_count == 0
    assert report.static_status is not StaticStatus.BLOCKED


@pytest.mark.parametrize(
    "relative_path",
    [
        "tests/kernel.cu",
        "tests/fixtures/repositories/cuda_extension/kernel.cu",
        "examples/kernel.cu",
        "docs/snippets/kernel.cu",
        "benchmarks/kernel.cu",
    ],
)
def test_non_delivery_paths_are_all_capped(tmp_path: Path, relative_path: str) -> None:
    _write(tmp_path, relative_path, _PTX_KERNEL)

    report = _scan(tmp_path)

    assert _severities(report, "MXR-PTX-001") == {relative_path: Severity.INFO}


def test_demoted_finding_keeps_an_audit_note(tmp_path: Path) -> None:
    """降级不能静默：finding 自身要说清为什么不再是 blocker。"""
    _write(tmp_path, "tests/kernel.cu", _PTX_KERNEL)

    report = _scan(tmp_path)

    finding = next(item for item in report.findings if item.rule_id == "MXR-PTX-001")
    assert "测试或夹具路径" in finding.message
    assert "从 blocker 降为提示" in finding.message


def test_report_records_one_warning_per_role_with_rule_counts(tmp_path: Path) -> None:
    _write(tmp_path, "tests/kernel.cu", _PTX_KERNEL)
    _write(tmp_path, "tests/warp.cu", "int lane = threadIdx.x % 32;\n")
    _write(tmp_path, "examples/kernel.cu", _PTX_KERNEL)

    report = _scan(tmp_path)

    messages = _path_warnings(report)
    assert len(messages) == 2
    test_message = next(message for message in messages if "测试/夹具路径" in message)
    assert "MXR-PTX-001（1 个文件）" in test_message
    assert "MXR-WARP-001（1 个文件）" in test_message
    assert any("示例路径" in message for message in messages)


def test_summary_and_checklist_follow_the_demoted_severity(tmp_path: Path) -> None:
    """降级若发生在汇总之后，summary 与迁移清单会与 findings 对不上。"""
    _write(tmp_path, "tests/kernel.cu", _PTX_KERNEL)

    report = _scan(tmp_path)

    assert report.summary.blocker_count == 0
    assert report.summary.info_count == len(report.findings)
    assert report.migration_checklist == []


def test_path_demotion_runs_before_toolchain_profile(tmp_path: Path) -> None:
    """工具链画像只处理交付路径，避免对已是提示的 finding 追加"降为 warning"。"""
    _write(tmp_path, "tests/Makefile", "NVCC = nvcc\nall:\n\t$(NVCC) -O3 main.cu\n")

    report = _scan(tmp_path)

    assert _severities(report, "MXR-TOOLCHAIN-001") == {"tests/Makefile": Severity.INFO}
    assert not [
        warning
        for warning in report.analysis_warnings
        if warning.code == "TOOLCHAIN_CU_BRIDGE_DOWNGRADE"
    ]
