from __future__ import annotations

import re
import time
from bisect import bisect_right
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from fnmatch import fnmatchcase
from importlib import import_module
from typing import Any

from mxready.errors import MxReadyError
from mxready.models import Finding, Severity
from mxready.scanning.facts import ProjectFacts, SourceLocation
from mxready.scanning.indexer import FileIndex, IndexedFile
from mxready.scanning.rule_loader import (
    RuleCatalog,
    RuleDefinition,
    RulePattern,
    regex_flags,
)

# re._parser 是 CPython 3.11+ 自带的标准库内部模块，re.compile 本身即由它驱动，
# 用于把规则正则分解为"必需字面量"做预过滤（Hyperscan NSDI'19 的 literal
# prefiltering 思路，另见 Russ Cox《Regular Expression Matching with a Trigram
# Index》：先用廉价子串判断缩小候选，再交给完整正则确认）。
_sre_parser = import_module("re._parser")
_REPEAT_OPS = frozenset(
    op
    for op in (
        getattr(_sre_parser, "MAX_REPEAT", None),
        getattr(_sre_parser, "MIN_REPEAT", None),
        getattr(_sre_parser, "POSSESSIVE_REPEAT", None),
    )
    if op is not None
)
# 短于该长度的字面量区分度不足，预过滤得不偿失，直接放弃。
_MIN_PREFILTER_LITERAL = 3

_SEVERITY_ORDER = {
    Severity.BLOCKER: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}


@dataclass(frozen=True, slots=True)
class _RuleMatch:
    location: SourceLocation
    line_end: int


def evaluate_rules(
    catalog: RuleCatalog,
    index: FileIndex,
    facts: ProjectFacts,
    *,
    max_findings: int = 10_000,
    timeout_seconds: float = 30,
    enable_prefilter: bool = True,
) -> list[Finding]:
    """Evaluate trusted rule data deterministically against a static index."""
    findings: dict[tuple[str, str, int, str], Finding] = {}
    if max_findings < 1 or timeout_seconds <= 0:
        raise ValueError("Rule evaluation budgets must be positive")
    deadline = time.monotonic() + timeout_seconds
    casefolded: dict[str, str] = {}

    def check_budget() -> None:
        if time.monotonic() >= deadline:
            raise MxReadyError("ANALYSIS_LIMIT_EXCEEDED", "规则评估超过时间预算，请缩小扫描范围。")

    for rule in catalog.rules:
        for pattern in rule.patterns:
            check_budget()
            for match in _evaluate_pattern(
                rule,
                pattern,
                index,
                facts,
                check_budget,
                casefolded,
                enable_prefilter,
            ):
                check_budget()
                finding = Finding(
                    rule_id=rule.id,
                    rule_version=rule.version,
                    severity=rule.severity,
                    category=rule.category,
                    title=rule.title,
                    relative_path=match.location.relative_path,
                    line_start=match.location.line,
                    line_end=match.line_end,
                    evidence=match.location.evidence[:240],
                    message=rule.message,
                    recommendation=rule.recommendation,
                    references=list(rule.references),
                )
                key = (
                    finding.rule_id,
                    finding.relative_path,
                    finding.line_start,
                    finding.evidence,
                )
                findings.setdefault(key, finding)
                if len(findings) > max_findings:
                    raise MxReadyError(
                        "ANALYSIS_LIMIT_EXCEEDED",
                        "规则命中数超过上限，请缩小扫描范围。",
                    )

    check_budget()

    return sorted(
        findings.values(),
        key=lambda item: (
            _SEVERITY_ORDER[item.severity],
            item.relative_path,
            item.line_start,
            item.rule_id,
        ),
    )


def _evaluate_pattern(
    rule: RuleDefinition,
    pattern: RulePattern,
    index: FileIndex,
    facts: ProjectFacts,
    check_budget: Callable[[], None],
    casefolded: dict[str, str],
    enable_prefilter: bool,
) -> Iterable[_RuleMatch]:
    if pattern.type == "regex":
        return _evaluate_regex(
            rule,
            pattern,
            index,
            check_budget,
            casefolded,
            enable_prefilter,
        )
    if pattern.type == "dependency":
        return _evaluate_dependency(rule, pattern, facts)
    return _evaluate_fact(rule, pattern, facts)


def _evaluate_regex(
    rule: RuleDefinition,
    pattern: RulePattern,
    index: FileIndex,
    check_budget: Callable[[], None],
    casefolded: dict[str, str],
    enable_prefilter: bool,
) -> Iterator[_RuleMatch]:
    expression = pattern.expression
    if expression is None:
        return
    flags = regex_flags(pattern.flags)
    compiled = re.compile(expression, flags)
    ignore_case = bool(flags & re.IGNORECASE)
    needle = (
        _required_literal(expression, flags)
        if enable_prefilter
        else None
    )

    for indexed_file in index.files:
        check_budget()
        if not _matches_any_glob(indexed_file.relative_path, rule.file_globs):
            continue
        if needle is not None and not _may_contain(
            needle,
            ignore_case,
            indexed_file,
            casefolded,
        ):
            continue
        for regex_match in compiled.finditer(indexed_file.text):
            line_start = bisect_right(indexed_file.line_offsets, regex_match.start())
            last_character = max(regex_match.start(), regex_match.end() - 1)
            line_end = bisect_right(indexed_file.line_offsets, last_character)
            yield _RuleMatch(
                location=SourceLocation(
                    relative_path=indexed_file.relative_path,
                    line=line_start,
                    evidence=_line_evidence(
                        indexed_file,
                        line_start,
                        line_end,
                    ),
                ),
                line_end=line_end,
            )


def _evaluate_dependency(
    rule: RuleDefinition,
    pattern: RulePattern,
    facts: ProjectFacts,
) -> list[_RuleMatch]:
    if pattern.name is None:
        return []
    name = _canonicalize_dependency(pattern.name)
    if name not in facts.dependencies:
        return []
    return _location_matches(
        facts.locations.get(f"dependency:{name}", ()),
        rule.file_globs,
    )


def _evaluate_fact(
    rule: RuleDefinition,
    pattern: RulePattern,
    facts: ProjectFacts,
) -> list[_RuleMatch]:
    if (
        pattern.name is None
        or pattern.name not in facts.flags
        or facts.flags[pattern.name] != pattern.equals
    ):
        return []
    return _location_matches(
        facts.locations.get(f"fact:{pattern.name}", ()),
        rule.file_globs,
    )


def _location_matches(
    locations: tuple[SourceLocation, ...],
    file_globs: list[str],
) -> list[_RuleMatch]:
    return [
        _RuleMatch(location=location, line_end=location.line)
        for location in locations
        if _matches_any_glob(location.relative_path, file_globs)
    ]


def _matches_any_glob(relative_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatchcase(relative_path, pattern):
            return True
        if pattern.startswith("**/") and fnmatchcase(relative_path, pattern[3:]):
            return True
    return False


def _may_contain(
    needle: str,
    ignore_case: bool,
    indexed_file: IndexedFile,
    casefolded: dict[str, str],
) -> bool:
    """Hyperscan 式预过滤：必需字面量都不出现的文件不可能命中，跳过正则扫描。"""
    if not ignore_case:
        return needle in indexed_file.text
    folded = casefolded.get(indexed_file.relative_path)
    if folded is None:
        folded = indexed_file.text.casefold()
        casefolded[indexed_file.relative_path] = folded
    return needle in folded


def _required_literal(expression: str, flags: re.RegexFlag) -> str | None:
    """从正则中保守提取一个"每个命中都必须包含"的子串。

    提取失败或字面量过短时返回 None（退化为全量扫描）。宁可漏提取
    （预过滤退化为直通）也不能提取出错误字面量（那会造成漏报）。
    """
    try:
        parsed = _sre_parser.parse(expression, flags)
        # 3.11/3.12 返回 (解析树, 状态) 二元组，3.13+ 直接返回解析树。
        tree = parsed[0] if isinstance(parsed, tuple) else parsed
    except (re.error, ValueError, TypeError, IndexError):
        return None
    literals = _sequence_literals(tree)
    if not literals:
        return None
    best = max(literals, key=len)
    if len(best) < _MIN_PREFILTER_LITERAL:
        return None
    return best.casefold() if flags & re.IGNORECASE else best


def _sequence_literals(sequence: Any) -> set[str]:
    """收集正则解析树中必然出现在匹配结果里的连续字面量片段。

    保守规则：分支只取各分支共同字面量；min=0 的重复段不产生必需字面量；
    字符类、断言、反向引用等一律终止当前连续段。
    """
    runs: list[str] = []
    current: list[str] = []
    nested: set[str] = set()

    def flush() -> None:
        if current:
            runs.append("".join(current))
            current.clear()

    for op, argument in sequence:
        if op == _sre_parser.LITERAL:
            current.append(chr(argument))
        elif op == _sre_parser.AT:
            flush()
        elif op == _sre_parser.SUBPATTERN:
            flush()
            nested |= _sequence_literals(argument[-1])
        elif op in _REPEAT_OPS:
            flush()
            if argument[0] >= 1:
                nested |= _sequence_literals(argument[-1])
        elif op == _sre_parser.BRANCH:
            flush()
            common: set[str] | None = None
            for branch in argument[1]:
                branch_literals = _sequence_literals(branch)
                common = branch_literals if common is None else common & branch_literals
            if common:
                nested |= common
        else:
            flush()
    flush()
    return set(runs) | nested


def _line_evidence(
    indexed_file: IndexedFile,
    line_start: int,
    line_end: int,
) -> str:
    start = indexed_file.line_offsets[line_start - 1]
    end = (
        indexed_file.line_offsets[line_end]
        if line_end < len(indexed_file.line_offsets)
        else len(indexed_file.text)
    )
    evidence = indexed_file.text[start:end].strip()
    return evidence[:240]


def _canonicalize_dependency(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()
