"""文档字符串豁免的回归测试。

背景：`scanning/toolchain.py` 的模块文档字符串里写了 `subprocess.run(["nvcc", ...])`
作为反例说明，被 `MXR-TOOLCHAIN-001` 判成 blocker——一条**描述**规则的文字，
被当成了**违反**规则的行为。本仓库因此长期以"自我阻断"状态对外展示。

豁免范围刻意收窄：只认文档字符串（模块/类/函数首条字符串常量），普通字符串
不豁免——`os.system("nvcc main.cu")` 的命令就在字符串里，豁免会制造真实漏报。
"""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from mxready.models import Severity, StaticStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.python_source import docstring_spans, is_inside_docstring
from mxready.scanning.rule_loader import load_rule_catalog

CATALOG = load_rule_catalog(Path("src/mxready/resources/rules/v1"))


def _scan(root: Path):
    clone = "https://gitee.com/metax-maca/demo"
    commit = "c" * 40
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


def _finding(report, rule_id: str):
    return next(item for item in report.findings if item.rule_id == rule_id)


_DOCSTRING_ONLY = '''"""构建示例。

反例：subprocess.run(["nvcc", "main.cu"]) 会绕过包装器注入的 PATH。
"""
'''


def test_docstring_mention_is_downgraded_to_info(tmp_path: Path) -> None:
    _write(tmp_path, "notes.py", _DOCSTRING_ONLY)

    report = _scan(tmp_path)

    finding = _finding(report, "MXR-TOOLCHAIN-001")
    assert finding.severity is Severity.INFO
    assert "文档字符串" in finding.message
    assert report.static_status is not StaticStatus.BLOCKED


def test_code_outside_the_docstring_stays_a_blocker(tmp_path: Path) -> None:
    """同一文件里文档说一遍、代码真写一遍：代码那处仍是阻塞项。"""
    _write(
        tmp_path,
        "build.py",
        '"""反例：subprocess.run(["nvcc", "main.cu"]) 会绕过包装器。"""\n'
        "import subprocess\n"
        'subprocess.run(["nvcc", "main.cu"], check=True)\n',
    )

    report = _scan(tmp_path)

    assert _finding(report, "MXR-TOOLCHAIN-001").severity is Severity.BLOCKER
    assert report.static_status is StaticStatus.BLOCKED


def test_string_literal_command_is_not_exempt(tmp_path: Path) -> None:
    """命令行本身就在字符串里：豁免普通字符串等于放过真问题。"""
    _write(tmp_path, "run.py", 'import os\nos.system("nvcc -O3 main.cu")\n')

    report = _scan(tmp_path)

    assert _finding(report, "MXR-TOOLCHAIN-001").severity is Severity.BLOCKER


def test_unparsable_python_falls_back_to_no_exemption(tmp_path: Path) -> None:
    """解析失败时一律不豁免：宁可多报，也不能凭猜测放过。"""
    _write(tmp_path, "legacy.py", 'print "hello"\nsubprocess.run(["nvcc", "x.cu"])\n')

    report = _scan(tmp_path)

    assert _finding(report, "MXR-TOOLCHAIN-001").severity is Severity.BLOCKER


def test_docstring_spans_cover_module_class_and_function() -> None:
    source = '''"""module doc"""


class C:
    """class doc"""

    def method(self):
        """method doc"""
        return 1
'''

    spans = docstring_spans(source)

    assert spans == ((1, 1), (5, 5), (8, 8))


def test_docstring_spans_ignore_plain_strings_and_assignments() -> None:
    source = 'DOC = """not a docstring"""\nvalue = "nvcc"\n'

    assert docstring_spans(source) == ()


def test_is_inside_docstring_requires_full_containment() -> None:
    spans = ((10, 20),)

    assert is_inside_docstring(spans, 12, 14)
    assert not is_inside_docstring(spans, 19, 21)
    assert not is_inside_docstring(spans, 9, 12)
