"""按路径判定文件角色：非交付路径上的命中只作提示。

静态规则看不到"这段代码是交付产物还是验证材料"。仓库的 `tests/`、`examples/`、
`docs/` 里常常放着 `.cu` 夹具、构建脚本与代码片段——它们的写法与真实 kernel 一样，
但**不是**迁移对象。按原级别上报会让报告整体失真：本仓库自扫描一度出现 22 条
blocker，全部出自测试夹具，真实用户第一次运行就会看到"工具判定自己是阻塞状态"。

处理原则：

1. 不排除这些文件。仍然索引、仍然评估、仍然出现在报告里——"看不见"比"级别低"
   更危险，漏掉一条真实风险比看到一条弱提示代价大得多。
2. 只把**交付路径之外**的命中封顶为 `info`，不改变交付路径的任何结论。
3. 降级必须留痕。与工具链画像（`scanning/toolchain.py`）同一套约定：
   `Finding.message` 末尾追加原因，并往 `analysis_warnings` 写一条可追溯记录，
   含角色、规则 ID 与文件数。

路径判定按**路径段精确匹配**，不做子串匹配：`contest/`、`attestation/`、
`latest/` 都不是测试目录。
"""

from __future__ import annotations

from enum import StrEnum

from mxready.models import AnalysisWarning, Finding, Severity

PATH_CONTEXT_WARNING_CODE = "PATH_CONTEXT_DEMOTION"


class PathRole(StrEnum):
    SOURCE = "source"
    TEST = "test"
    EXAMPLE = "example"
    DOC = "doc"
    BENCHMARK = "benchmark"


# 判定顺序即优先级：`docs/examples/x.cu` 归为示例，而不是文档。
_ROLE_SEGMENTS: tuple[tuple[PathRole, frozenset[str]], ...] = (
    (
        PathRole.TEST,
        frozenset(
            {
                "__tests__",
                "fixture",
                "fixtures",
                "test",
                "test-data",
                "test_data",
                "testdata",
                "tests",
                "testing",
            }
        ),
    ),
    (
        PathRole.BENCHMARK,
        frozenset({"bench", "benches", "benchmark", "benchmarks"}),
    ),
    (
        PathRole.EXAMPLE,
        frozenset({"demo", "demos", "example", "examples", "sample", "samples"}),
    ),
    (
        PathRole.DOC,
        frozenset({"doc", "docs", "documentation"}),
    ),
)

# 只对这两档降级：info 本来就是提示，再写一遍原因只是噪音。
_DEMOTABLE = frozenset({Severity.BLOCKER, Severity.WARNING})

_ROLE_LABELS = {
    PathRole.TEST: "测试/夹具",
    PathRole.BENCHMARK: "基准测试",
    PathRole.EXAMPLE: "示例",
    PathRole.DOC: "文档",
}

_ROLE_NOTES = {
    PathRole.TEST: (
        "（该命中位于测试或夹具路径：规则命中的是测试代码本身，通常不代表交付产物的"
        "迁移风险，已从 {declared} 降为提示；若该夹具描述的正是交付行为，请另行复核。）"
    ),
    PathRole.BENCHMARK: (
        "（该命中位于基准测试路径：基准代码一般不随交付构建，已从 {declared} 降为提示。）"
    ),
    PathRole.EXAMPLE: (
        "（该命中位于示例路径：示例代码一般不随交付构建，已从 {declared} 降为提示。）"
    ),
    PathRole.DOC: ("（该命中位于文档路径：命中的是文档中的代码片段，已从 {declared} 降为提示。）"),
}

_SEVERITY_LABELS = {
    Severity.BLOCKER: "blocker",
    Severity.WARNING: "warning",
}


def classify_path(relative_path: str) -> PathRole:
    """按路径段给出文件角色；文件名本身只有 `test_*` / `*_test` 参与判定。"""
    segments = [segment.casefold() for segment in relative_path.split("/") if segment]
    if not segments:
        return PathRole.SOURCE

    directories = segments[:-1]
    for role, names in _ROLE_SEGMENTS:
        if any(segment in names for segment in directories):
            return role

    if _is_test_filename(segments[-1]):
        return PathRole.TEST
    return PathRole.SOURCE


def is_demoted(relative_path: str) -> bool:
    return classify_path(relative_path) is not PathRole.SOURCE


def apply_path_context(
    findings: list[Finding],
) -> tuple[list[Finding], list[AnalysisWarning]]:
    """把非交付路径上的 blocker/warning 封顶为 info，并返回需要写入报告的告警。"""
    adjusted: list[Finding] = []
    demoted: dict[PathRole, dict[str, set[str]]] = {}

    for finding in findings:
        role = classify_path(finding.relative_path)
        if role is PathRole.SOURCE or finding.severity not in _DEMOTABLE:
            adjusted.append(finding)
            continue
        demoted.setdefault(role, {}).setdefault(finding.rule_id, set()).add(finding.relative_path)
        adjusted.append(
            finding.model_copy(
                update={
                    "severity": Severity.INFO,
                    "message": _append_note(finding.message, role, finding.severity),
                }
            )
        )

    if not demoted:
        return adjusted, []

    warnings = [
        AnalysisWarning(
            code=PATH_CONTEXT_WARNING_CODE,
            relative_path=None,
            message=(
                f"{_ROLE_LABELS[role]}路径上的 {_describe_rules(rules)} 已封顶为提示，"
                "不参与静态状态判定；文件仍被扫描，结论可逐条复核。"
            ),
        )
        for role, rules in sorted(demoted.items(), key=lambda item: item[0].value)
    ]
    return adjusted, warnings


def _is_test_filename(name: str) -> bool:
    stem = name.rsplit(".", 1)[0]
    return stem.startswith("test_") or stem.endswith(("_test", "-test"))


def _append_note(message: str, role: PathRole, declared: Severity) -> str:
    note = _ROLE_NOTES[role].format(declared=_SEVERITY_LABELS[declared])
    if note in message:
        return message
    return f"{message}{note}"


def _describe_rules(rules: dict[str, set[str]]) -> str:
    return "；".join(
        f"{rule_id}（{len(paths)} 个文件）" for rule_id, paths in sorted(rules.items())
    )
