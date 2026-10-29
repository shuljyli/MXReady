from __future__ import annotations

import random
import re
import sys
from pathlib import Path

import pytest

from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import IndexedFile, build_file_index
from mxready.scanning.rule_engine import (
    _folded_view,
    _FoldedCache,
    _passes_prefilter,
    _required_prefilter,
    evaluate_rules,
)
from mxready.scanning.rule_loader import load_rule_catalog, regex_flags

FIXTURE = Path("tests/fixtures/repositories/cuda_extension")
RULES = Path("src/mxready/resources/rules/v1")


def _prefilter(expression: str, flags: int = 0):
    return _required_prefilter(expression, re.RegexFlag(flags))


def _needles(expression: str, flags: int = 0) -> tuple[tuple[str, bool], ...] | None:
    prefilter = _prefilter(expression, flags)
    if prefilter is None:
        return None
    return tuple((needle.text, needle.ignore_case) for needle in prefilter)


def _indexed(text: str, name: str = "sample.txt") -> IndexedFile:
    return IndexedFile(name, len(text), "0" * 64, text)


def _passes(expression: str, text: str, flags: int = 0) -> bool:
    prefilter = _prefilter(expression, flags)
    if prefilter is None:
        return True
    return _passes_prefilter(prefilter, _indexed(text), _FoldedCache())


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("abcdef", (("abcdef", False),)),
        # 顶层内联 flag 不产生节点，只体现在解析状态的 flags 上
        ("(?i)abcdef", (("abcdef", True),)),
        # scoped flag 在 SUBPATTERN 的 add_flags 上，且只作用于本作用域
        ("(?i:abcdef)", (("abcdef", True),)),
        ("(?-i:ABCDEFG)", (("ABCDEFG", False),)),
        ("abc(?i:DEFGH)", (("DEFGH", True),)),
        # 旧实现取最强 run 后按"模式级"flag 判定，这里会漏掉忽略大小写
        ("(?i:ABCDEF)ghi", (("ABCDEF", True),)),
        # 分支：每个分支各出一个候选，任一出现即放行
        ("(?:alpha|beta)", (("alpha", False), ("beta", False))),
        # 分支里唯一片段都短于阈值，整体放弃预过滤
        ("(?:a|bb)", None),
        ("(?:sm|compute)_[0-9]{2,3}", None),
    ],
)
def test_literals_carry_positional_flags(expression, expected) -> None:
    assert _needles(expression) == expected


@pytest.mark.parametrize(
    ("expression", "text", "flags"),
    [
        ("(?i)abc", "ABC", 0),
        ("(?i:abc)", "AbC", 0),
        ("(?i:ABCDEF)ghi", "abcdefghi", 0),
        # casefold 与 re 的 simple-fold 在土耳其语 I 家族上不同构，必须放行
        ("(?i)İstanbul", "istanbul", 0),
        ("(?i)internet", "ınternet", 0),
        ("(?i)sos", "ſos", 0),
        # 规则级 IGNORECASE 走的是另一条路径，不能回归
        ("NCCL_DEBUG", "nccl_debug", re.IGNORECASE),
        # 无 cased 字符的字面量走精确匹配，re.IGNORECASE 对它没有影响
        ("(?i)沐曦芯", "沐曦芯", 0),
    ],
)
def test_matching_text_is_never_rejected(expression, text, flags) -> None:
    assert re.search(expression, text, flags) is not None
    assert _passes(expression, text, flags) is True


def test_unrelated_text_is_rejected() -> None:
    assert _passes("(?i:abcdef)", "xyz") is False
    assert _passes("NCCL_DEBUG", "something else", re.IGNORECASE) is False


_ATOMS = ("abc", "NCCL_DEBUG", "cuda", "İstanbul", "ılık", "沐曦芯", "xyz_1", "GradScaler")


def _random_pattern(rng: random.Random) -> str:
    core = rng.choice(_ATOMS)
    if rng.random() < 0.35:
        core = f"(?:{core}|{rng.choice(_ATOMS)})"
    if rng.random() < 0.5:
        core = f"(?i:{core})"
    if rng.random() < 0.25:
        core = f"\\b{core}"
    if rng.random() < 0.25:
        core = f"{core}[0-9]*"
    return core


def _random_text(rng: random.Random) -> str:
    parts = []
    for _ in range(rng.randint(1, 3)):
        atom = rng.choice((*_ATOMS, "", "some", "plain"))
        transform = rng.random()
        if transform < 0.25:
            atom = atom.upper()
        elif transform < 0.50:
            atom = atom.lower()
        elif transform < 0.60:
            atom = atom.replace("i", "ı").replace("I", "İ")
        parts.append(atom)
    return " ".join(parts)


def test_prefilter_never_rejects_a_matching_text() -> None:
    """核心安全属性：预过滤拒绝 ⇒ 正则一定不命中（零假阴性）。

    固定种子，覆盖内联 flag、分支、锚点、Unicode 与大小写变体。
    """
    rng = random.Random(20261029)
    rejected = 0
    for _ in range(600):
        expression = _random_pattern(rng)
        text = _random_text(rng)
        prefilter = _prefilter(expression)
        if prefilter is None:
            continue
        if _passes_prefilter(prefilter, _indexed(text), _FoldedCache()):
            continue
        rejected += 1
        assert re.search(expression, text) is None, (expression, text)
    assert rejected > 0


def test_prefilter_degrades_to_full_scan_without_parser(monkeypatch) -> None:
    from mxready.scanning import rule_engine

    index = build_file_index(FIXTURE)
    facts = extract_project_facts(index)
    catalog = load_rule_catalog(RULES)
    baseline = evaluate_rules(catalog, index, facts, enable_prefilter=False)

    monkeypatch.setattr(rule_engine, "_parser_ops", rule_engine._UNSET)
    monkeypatch.setattr(rule_engine, "_probe_parser", lambda: None)

    assert rule_engine._required_prefilter("(?i:abcdef)", re.NOFLAG) is None
    assert evaluate_rules(catalog, index, facts) == baseline


def test_folded_cache_stops_growing_past_budget() -> None:
    """预算用尽后只计算不缓存：常驻内存封顶，判定结果不受影响。"""
    one_file = sys.getsizeof("a" * 100)  # 折叠结果与原文字符数相同
    cache = _FoldedCache(budget=one_file * 2)
    for index in range(8):
        _folded_view(_indexed("A" * 100, f"f{index}.txt"), cache)

    assert cache.cached_files == 2
    assert cache.resident_bytes <= one_file * 2

    # 未缓存的文件仍然算得出正确视图，且不会把缓存撑大。
    folded = _folded_view(_indexed("GradScaler", "late.txt"), cache)
    assert folded.text == "gradscaler"
    assert cache.cached_files == 2
    assert cache.resident_bytes <= one_file * 2


def test_folded_cache_reuses_entry_for_same_file() -> None:
    cache = _FoldedCache()
    first = _folded_view(_indexed("NCCL_DEBUG"), cache)
    second = _folded_view(_indexed("NCCL_DEBUG"), cache)
    assert first is second
    assert cache.cached_files == 1


def test_saturated_cache_still_judges_correctly() -> None:
    """缓存饱和不能改变判定方向：放行/拒绝与空缓存时一致。"""
    cache = _FoldedCache(budget=1)  # 不放行任何缓存
    prefilter = _required_prefilter("(?i)nccl_debug", re.NOFLAG)
    assert prefilter is not None
    assert _passes_prefilter(prefilter, _indexed("NCCL_DEBUG=1"), cache) is True
    assert _passes_prefilter(prefilter, _indexed("totally unrelated"), cache) is False
    assert cache.cached_files == 0


def test_extraction_is_stable_across_calls() -> None:
    """提取结果不依赖哈希顺序：同一表达式两次提取必须逐项相同。"""
    catalog = load_rule_catalog(RULES)
    for rule in catalog.rules:
        for pattern in rule.patterns:
            if pattern.expression is None:
                continue
            flags = regex_flags(pattern.flags)
            first = _required_prefilter(pattern.expression, flags)
            second = _required_prefilter(pattern.expression, flags)
            assert first == second, (rule.id, pattern.expression)
            if first is not None:
                assert len({needle.text for needle in first}) == len(first), rule.id
