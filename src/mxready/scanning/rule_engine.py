from __future__ import annotations

import logging
import re
import sys
import time
from bisect import bisect_right
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from fnmatch import fnmatchcase
from importlib import import_module
from types import ModuleType
from typing import Any, cast

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

logger = logging.getLogger(__name__)

# 预过滤思路来自 Hyperscan NSDI'19 的 literal prefiltering，以及 Russ Cox
# 《Regular Expression Matching with a Trigram Index》：先用廉价子串判断缩小
# 候选，再交给完整正则确认。契约是「零假阴性、允许假阳性」——判定放行不等于
# 命中，判定跳过则一定不命中，所以任何提取失败都必须退化为全量扫描。
#
# 分解依赖 CPython 的 re._parser：它是私有 API（官方文档零次提及，3.11
# What's New 称其为 "Undocumented modules"），因此这里不直接 import，而是
# 惰性探测 + 失败降级。降级后预过滤自动关闭，结果集与开启时完全相同。
_UNSET = object()
_parser_ops: _ParserOps | None | object = _UNSET

# 短于该长度的字面量区分度不足，预过滤得不偿失，直接放弃。
_MIN_PREFILTER_LITERAL = 3
# 分支展开上限：超过即放弃约束，退化为全量扫描（放弃永远安全，只是变慢）。
_MAX_PREFILTER_ALTERNATIVES = 16
# 与 re 的 simple-fold 模型不同构的码位（土耳其语 I 家族）。穷举全部 1,112,064
# 个码位后，只有这两个会让 str.casefold() 与 re.IGNORECASE 产生分歧。
_CASEFOLD_DIVERGENT = ("ı", "İ")  # U+0131, U+0130
# 折叠视图缓存的常驻上限。索引层已把单文件限制在 1 MiB（即使全是最坏情况的
# 多码位折叠也远低于该值），所以预算只会限制"缓存多少文件"，不会出现单个文件
# 就把预算吃光、缓存彻底失效的退化。
_FOLDED_CACHE_BUDGET_BYTES = 48 * 1024 * 1024

_SEVERITY_ORDER = {
    Severity.BLOCKER: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}


@dataclass(frozen=True, slots=True)
class _RuleMatch:
    location: SourceLocation
    line_end: int


@dataclass(frozen=True, slots=True)
class _ParserOps:
    """探针验证过的 re._parser 接口切片，避免每次递归都做属性查找与形状判断。"""

    module: ModuleType
    literal: int
    at: int
    subpattern: int
    branch: int
    repeats: frozenset[int]


@dataclass(frozen=True, slots=True)
class _Needle:
    """一个"命中必然包含"的字面量，以及它在正则中所处位置的 effective flags。

    ignore_case 是**位置属性**而非模式属性：`(?i:ab)cd` 里 "ab" 折叠、"cd" 不折叠。
    """

    text: str
    ignore_case: bool


# OR 集：任一针出现即可能命中。每个候选只保留一个针——多针 AND 实测只再多过滤
# 3.3%，却要为每个候选多付一次全文扫描，得不偿失。
_Prefilter = tuple[_Needle, ...]


@dataclass(frozen=True, slots=True)
class _FoldedText:
    """折叠视图与"是否含折叠分歧字符"一次算清，未命中路径不再扫全文。"""

    text: str
    has_divergent: bool


class _FoldedCache:
    """跨规则复用的折叠视图缓存，按字节预算封顶。

    预过滤对同一文件会被多条规则反复问到，缓存把"每规则折叠一次"降为
    "每文件折叠一次"。但折叠结果与原文件等长，无上限地缓存整仓会令常驻内存
    翻倍，所以预算用尽后只计算不缓存。

    这里刻意不淘汰旧项：一轮评估里文件是按索引顺序推进的，淘汰只会让后续文件
    反复重算，命中率归零而内存并不更省；"停止累积"则让已缓存部分持续生效。
    """

    __slots__ = ("_budget", "_store", "_used")

    def __init__(self, budget: int = _FOLDED_CACHE_BUDGET_BYTES) -> None:
        self._budget = budget
        self._store: dict[str, _FoldedText] = {}
        self._used = 0

    def get(self, key: str) -> _FoldedText | None:
        return self._store.get(key)

    def remember(self, key: str, value: _FoldedText) -> None:
        if self._used + sys.getsizeof(value.text) > self._budget:
            return
        self._store[key] = value
        self._used += sys.getsizeof(value.text)

    @property
    def cached_files(self) -> int:
        return len(self._store)

    @property
    def resident_bytes(self) -> int:
        return self._used


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
    folded_cache = _FoldedCache()

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
                folded_cache,
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
    folded_cache: _FoldedCache,
    enable_prefilter: bool,
) -> Iterable[_RuleMatch]:
    if pattern.type == "regex":
        return _evaluate_regex(
            rule,
            pattern,
            index,
            check_budget,
            folded_cache,
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
    folded_cache: _FoldedCache,
    enable_prefilter: bool,
) -> Iterator[_RuleMatch]:
    expression = pattern.expression
    if expression is None:
        return
    flags = regex_flags(pattern.flags)
    compiled = re.compile(expression, flags)
    prefilter = _required_prefilter(expression, flags) if enable_prefilter else None

    for indexed_file in index.files:
        check_budget()
        if not _matches_any_glob(indexed_file.relative_path, rule.file_globs):
            continue
        if prefilter is not None and not _passes_prefilter(
            prefilter,
            indexed_file,
            folded_cache,
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


def _passes_prefilter(
    prefilter: _Prefilter,
    indexed_file: IndexedFile,
    folded_cache: _FoldedCache,
) -> bool:
    """任一候选针出现即放行。放行不代表命中，只是允许跑正则确认。"""
    return any(_may_contain(needle, indexed_file, folded_cache) for needle in prefilter)


def _may_contain(
    needle: _Needle,
    indexed_file: IndexedFile,
    folded_cache: _FoldedCache,
) -> bool:
    """判断文件是否可能包含该针。False 表示"一定不命中"，可以跳过正则。

    三段式，逐段收紧成本：
    1. 该位置区分大小写时，子串判断直接成立；
    2. 区分大小写但字面量没有可大小写字符（CJK/符号/数字）时，re.I 对它没有影响，
       精确匹配即可，顺带免掉整文件折叠；
    3. 其余走折叠视图；折叠模型与 re 的 simple-fold 在 ı/İ 上不同构，未命中时兜底放行。
    """
    text = indexed_file.text
    if not needle.ignore_case:
        return needle.text in text
    if not _has_cased_char(needle.text):
        return needle.text in text
    folded = _folded_view(indexed_file, folded_cache)
    if needle.text.casefold() in folded.text:
        return True
    # casefold 未命中但文件含分歧码位时，re 仍可能命中：放行交给正则确认。
    return folded.has_divergent or any(ch in needle.text for ch in _CASEFOLD_DIVERGENT)


def _folded_view(
    indexed_file: IndexedFile,
    folded_cache: _FoldedCache,
) -> _FoldedText:
    """折叠视图按文件缓存一次；"是否含分歧码位"同时算清，未命中路径不再扫全文。"""
    cached = folded_cache.get(indexed_file.relative_path)
    if cached is not None:
        return cached
    text = indexed_file.text
    folded = _FoldedText(
        text=text.casefold(),
        has_divergent=any(ch in text for ch in _CASEFOLD_DIVERGENT),
    )
    folded_cache.remember(indexed_file.relative_path, folded)
    return folded


def _has_cased_char(value: str) -> bool:
    """字面量是否含可大小写字符；不含时 re.IGNORECASE 对它没有任何影响。"""
    return value.lower() != value or value.upper() != value


def _required_prefilter(expression: str, flags: re.RegexFlag) -> _Prefilter | None:
    """从正则中保守提取「命中必然包含其一」的字面量集合。

    提取失败或字面量过短时返回 None（退化为全量扫描）。宁可漏提取
    （预过滤退化为直通）也不能提取出错误字面量（那会造成漏报）。
    """
    ops = _load_parser()
    if ops is None:
        return None
    try:
        tree = ops.module.parse(expression, int(flags))
        # 顶层内联 flag（如 `(?i)abc`）不产生节点，只体现在 state.flags 上。
        top_flags = int(getattr(tree.state, "flags", int(flags)))
        return _collect(ops, tree.data, top_flags)
    except Exception:
        # 失败语义就是"放弃预过滤"：宁可全量扫描，也不能让扫描因优化而失败。
        logger.debug("literal prefilter extraction failed", exc_info=True)
        return None


def _collect(ops: _ParserOps, sequence: Any, flags: int) -> _Prefilter | None:
    """遍历解析树，收集每个命中都必须包含的字面量（OR 集）。

    保守规则：
    - 连续 LITERAL 合并成一个 run，短于阈值直接丢弃；
    - 分支要求**每个**分支都给得出约束，否则整节点放弃（只约束部分分支会误杀）；
    - min=0 的重复段可能完全缺席，不产生约束；
    - 断言、字符类等无法确定内容，仅终止当前 run。
    """
    alternatives: _Prefilter | None = None
    run: list[str] = []
    run_ignore_case = bool(flags & re.IGNORECASE)

    def flush() -> None:
        nonlocal alternatives
        if len(run) >= _MIN_PREFILTER_LITERAL:
            alternatives = _merge(alternatives, (_Needle("".join(run), run_ignore_case),))
        run.clear()

    def absorb(node: _Prefilter | None) -> None:
        nonlocal alternatives
        alternatives = _merge(alternatives, node)

    for op, argument in sequence:
        if op == ops.literal:
            ignore_case = bool(flags & re.IGNORECASE)
            if run and ignore_case != run_ignore_case:
                flush()  # 防御：flags 只在 SUBPATTERN 边界变化，正常不会触发
            run_ignore_case = ignore_case
            run.append(chr(argument))
            continue
        flush()
        if op == ops.subpattern:
            _, add_flags, delete_flags, sub = argument
            # flags 是位置属性：进入子模式时按 add/delete 位重算。
            absorb(_collect(ops, sub, (flags | add_flags) & ~delete_flags))
        elif op in ops.repeats:
            minimum, _, sub = argument
            if minimum >= 1:  # min=0 时子表达式可能完全缺席
                absorb(_collect(ops, sub, flags))
        elif op == ops.branch:
            absorb(_merge_branches([_collect(ops, branch, flags) for branch in argument[1]]))
        # AT / IN / ANY / GROUPREF / 断言等：不产生约束
    flush()
    return alternatives


def _merge(left: _Prefilter | None, right: _Prefilter | None) -> _Prefilter | None:
    """拼接两个子表达式的约束。

    两侧都只是「必须满足其一」的必要条件（命中会同时满足两者），因此保留任一侧
    都健全；这里保留区分度更高的一侧，避免多针 AND 带来的额外全文扫描。
    """
    if left is None:
        return right
    if right is None:
        return left
    return left if _selectivity(left) >= _selectivity(right) else right


def _merge_branches(groups: list[_Prefilter | None]) -> _Prefilter | None:
    """分支：任一分支给不出约束，整体放弃——只约束部分分支会误杀其余分支的命中。"""
    merged: list[_Needle] = []
    for group in groups:
        if group is None:
            return None
        merged.extend(group)
    unique = tuple(dict.fromkeys(merged))
    return unique if len(unique) <= _MAX_PREFILTER_ALTERNATIVES else None


def _selectivity(prefilter: _Prefilter) -> tuple[int, int]:
    """针越长越能区分文件；长度相同时，候选越多约束越弱。"""
    if not prefilter:
        return (0, 0)
    return (max(len(needle.text) for needle in prefilter), -len(prefilter))


def prefilter_status() -> str:
    """预过滤的实际生效状态，供扫描报告如实记录。

    只记录"是否可用"而不是"是否被要求开启"：解析器探测失败时预过滤并不生效，
    报告若写 "on" 会让排障时误以为优化已生效。
    """
    return "on" if _load_parser() is not None else "unavailable"


def _load_parser() -> _ParserOps | None:
    """探测一次 re._parser 的接口形状；失败则永久降级为"不预过滤"，结果集不变。"""
    global _parser_ops
    if _parser_ops is _UNSET:
        _parser_ops = _probe_parser()
        if _parser_ops is None:
            logger.warning(
                "literal prefilter disabled: re._parser unavailable or its shape changed"
            )
    return cast("_ParserOps | None", _parser_ops)


def _probe_parser() -> _ParserOps | None:
    """用行为断言接口形状，而不是判断版本号。

    3.13 改变了 parse() 的返回形态，但版本号判断看不出来；形状漂移也不会抛异常，
    只会静默错提取。所以三条探针都直接验证行为：常量存在、顶层 flag 落点、
    scoped flag 的元组形状。
    """
    try:
        module = import_module("re._parser")
        ops = _ParserOps(
            module=module,
            literal=int(module.LITERAL),
            at=int(module.AT),
            subpattern=int(module.SUBPATTERN),
            branch=int(module.BRANCH),
            repeats=frozenset(
                int(op)
                for op in (
                    getattr(module, "MAX_REPEAT", None),
                    getattr(module, "MIN_REPEAT", None),
                    getattr(module, "POSSESSIVE_REPEAT", None),
                )
                if op is not None
            ),
        )
        tree = module.parse("(?i)ab", 0)
        if not hasattr(tree, "data") or not hasattr(tree, "state"):
            return None
        if not (int(tree.state.flags) & int(re.IGNORECASE)):
            return None
        node = module.parse("(?i:ab)", 0).data[0]
        if node[0] != ops.subpattern or len(node[1]) != 4:
            return None
    except Exception:
        return None
    return ops


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
