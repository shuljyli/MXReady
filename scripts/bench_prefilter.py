"""Measure the literal-prefilter cost/benefit for every regex rule in a corpus.

For each rule this reports how long it takes to decide "may this file match"
(prefilter) versus how long the full regex takes on the same files. The prefilter
only pays off when the former is clearly cheaper: CPython's `re` already does a
literal-prefix fast-scan, so for plain `nvcc`-style patterns the two costs are
close and the prefilter is a net loss.

Output is deliberately timestamp-free so two runs can be diffed directly.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from mxready.scanning.facts import extract_project_facts
from mxready.scanning.indexer import FileIndex, IndexedFile, build_file_index
from mxready.scanning.rule_engine import (
    _FoldedCache,
    _matches_any_glob,
    _passes_prefilter,
    _Prefilter,
    _required_prefilter,
    evaluate_rules,
)
from mxready.scanning.rule_loader import RuleCatalog, load_rule_catalog, regex_flags

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "src" / "mxready" / "resources" / "rules" / "v1"
# 默认用本仓库自身作语料：约 600 个文件、2 MiB，规模与一次真实扫描相当。
# tests/fixtures 只有 5 个文件，太小的语料会让缓存与探测开销盖过收益，
# 测出来的永远是"净亏"，没有参考价值。
DEFAULT_CORPUS = ROOT

# 低于正则成本的这个比例才算真赚到；否则视为持平或净亏。
_WIN_RATIO = 0.8


def _time(call: Callable[[], None], repeat: int) -> float:
    """取多轮最小值：微基准里最小值比均值更能反映真实成本，噪声只会抬高它。"""
    samples: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        call()
        samples.append((time.perf_counter() - start) * 1000)
    return min(samples)


def _scoped_files(index: FileIndex, rule_globs: list[str]) -> list[IndexedFile]:
    return [item for item in index.files if _matches_any_glob(item.relative_path, rule_globs)]


def _verdict(prefilter_ms: float, regex_ms: float) -> str:
    if prefilter_ms <= regex_ms * _WIN_RATIO:
        return "win"
    return "marginal" if prefilter_ms <= regex_ms else "loss"


def _time_regex(compiled: re.Pattern[str], files: list[IndexedFile], repeat: int) -> float:
    def run() -> None:
        for item in files:
            for _match in compiled.finditer(item.text):
                pass

    return _time(run, repeat)


def _time_prefilter(prefilter: _Prefilter, files: list[IndexedFile], repeat: int) -> float:
    def run() -> None:
        # 冷缓存：这里量的是"这条规则单独跑"的成本，是上限而不是常态。
        cache = _FoldedCache()
        for item in files:
            _passes_prefilter(prefilter, item, cache)

    return _time(run, repeat)


def _measure_rule(
    rule: Any,
    index: FileIndex,
    repeat: int,
) -> Iterable[dict[str, Any]]:
    for pattern in rule.patterns:
        if pattern.type != "regex" or pattern.expression is None:
            continue
        expression = pattern.expression
        flags = regex_flags(pattern.flags)
        compiled = re.compile(expression, flags)
        prefilter = _required_prefilter(expression, flags)
        files = _scoped_files(index, rule.file_globs)

        regex_ms = _time_regex(compiled, files, repeat)
        entry: dict[str, Any] = {
            "rule_id": rule.id,
            "expression": expression,
            "files_in_scope": len(files),
            "regex_ms": round(regex_ms, 4),
        }
        if prefilter is None:
            entry.update(needles=[], skipped=0, prefilter_ms=None, verdict="no-prefilter")
            yield entry
            continue

        prefilter_ms = _time_prefilter(prefilter, files, repeat)
        # 与 _time_prefilter 同口径：整轮共用一个缓存，一次遍历数出可跳过的文件。
        scan_cache = _FoldedCache()
        skipped = sum(1 for item in files if not _passes_prefilter(prefilter, item, scan_cache))
        entry.update(
            needles=[[needle.text, needle.ignore_case] for needle in prefilter],
            skipped=skipped,
            prefilter_ms=round(prefilter_ms, 4),
            verdict=_verdict(prefilter_ms, regex_ms),
        )
        yield entry


def benchmark(corpus: Path, rules: Path, repeat: int) -> dict[str, Any]:
    index = build_file_index(corpus)
    catalog: RuleCatalog = load_rule_catalog(rules)
    facts = extract_project_facts(index)

    entries = [entry for rule in catalog.rules for entry in _measure_rule(rule, index, repeat)]
    constrained = [entry for entry in entries if entry["prefilter_ms"] is not None]

    with_prefilter = evaluate_rules(catalog, index, facts)
    without_prefilter = evaluate_rules(catalog, index, facts, enable_prefilter=False)

    def run_with() -> None:
        evaluate_rules(catalog, index, facts)

    def run_without() -> None:
        evaluate_rules(catalog, index, facts, enable_prefilter=False)

    end_to_end_with = _time(run_with, max(3, repeat // 2))
    end_to_end_without = _time(run_without, max(3, repeat // 2))

    return {
        "corpus": {
            "path": str(corpus),
            "files": len(index.files),
            "chars": sum(len(item.text) for item in index.files),
        },
        "ruleset": {"path": str(rules), "version": catalog.version, "digest": catalog.digest},
        "rules": entries,
        "totals": {
            "rules": len(entries),
            "constrained": len(constrained),
            "unconstrained": len(entries) - len(constrained),
            "regex_ms": round(sum(entry["regex_ms"] for entry in entries), 4),
            "prefilter_ms": round(sum(entry["prefilter_ms"] or 0.0 for entry in entries), 4),
            "skipped_files": sum(entry["skipped"] for entry in entries),
            "verdicts": {
                name: sum(1 for entry in entries if entry["verdict"] == name)
                for name in ("win", "marginal", "loss", "no-prefilter")
            },
        },
        "end_to_end": {
            "with_prefilter_ms": round(end_to_end_with, 4),
            "without_prefilter_ms": round(end_to_end_without, 4),
            "speedup": round(end_to_end_without / end_to_end_with, 4) if end_to_end_with else None,
            "findings": len(with_prefilter),
            "findings_identical": with_prefilter == without_prefilter,
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="被扫描的目录")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES, help="规则目录")
    parser.add_argument("--repeat", type=int, default=5, help="每个计时的重复轮数")
    parser.add_argument("--output", type=Path, default=None, help="JSON 输出路径，缺省打印")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    if arguments.repeat < 1:
        raise SystemExit("--repeat must be at least 1")
    report = benchmark(arguments.corpus, arguments.rules, arguments.repeat)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(payload, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload, encoding="utf-8")
    if not report["end_to_end"]["findings_identical"]:
        print("WARNING: prefilter changed the finding set", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
