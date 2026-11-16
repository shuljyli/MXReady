"""Measure the fixed 10k findings/2k catalog workload; no CI wall-clock assertions."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
import tracemalloc
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from mxready.models import (
    Finding,
    RepositorySnapshot,
    ScanReport,
    Severity,
    StaticStatus,
    VerificationStatus,
    summarize_findings,
)
from mxready.tui.commands import Command
from mxready.tui.report_browser import FindingFilter, browse
from mxready.tui.report_catalog import load_report
from mxready.tui.state_store import StateStore


def elapsed(operation, repeats=1):
    times = []
    result = None
    for _ in range(repeats):
        started = time.perf_counter()
        result = operation()
        times.append((time.perf_counter() - started) * 1000)
    return result, statistics.median(times)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    findings = [
        Finding(
            rule_id="MXR-WARP-001",
            rule_version=1,
            severity=Severity.BLOCKER,
            category="warp",
            title=f"内核 kernel {i}",
            relative_path=f"csrc/{i}.cu",
            line_start=1,
            line_end=1,
            evidence="warpSize",
            message="固定 warp 假设",
            recommendation="检查目标线程组语义",
            references=[],
        )
        for i in range(10_000)
    ]
    report = ScanReport(
        scan_id=uuid4(),
        repository=RepositorySnapshot(
            provider="github",
            owner="example",
            name="benchmark",
            url="https://github.com/example/benchmark",
            commit="a" * 40,
        ),
        tool_version="benchmark",
        ruleset_version="1",
        scanned_at=datetime.now(UTC),
        summary=summarize_findings(findings),
        findings=findings,
        migration_checklist=[],
        analysis_warnings=[],
        static_status=StaticStatus.BLOCKED,
        verification_status=VerificationStatus.NOT_RUN,
    )
    path = args.output_dir / "synthetic.json"
    path.write_text(report.model_dump_json(), encoding="utf-8")
    del report, findings
    tracemalloc.start()
    loaded, cold_ms = elapsed(lambda: load_report(path))
    _, warm_ms = elapsed(lambda: load_report(path), 3)
    filters = FindingFilter(text_query="kernel")
    result, filter_ms = elapsed(lambda: browse(loaded.report, filters, 1, Command("findings")), 5)
    _, page, indices = result
    _, page_ms = elapsed(
        lambda: browse(loaded.report, filters, page.page, Command("findings", "2"), indices), 50
    )
    store = StateStore(args.output_dir / "state.db")
    for i in range(2000):
        store.register(
            args.output_dir,
            replace(loaded, path=args.output_dir / f"catalog-{i}.json"),
            visited=False,
        )
    entries, catalog_ms = elapsed(lambda: store.entries(args.output_dir), 5)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    store.close()
    result = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
        "textual": version("textual"),
        "findings": 10_000,
        "report_bytes": path.stat().st_size,
        "catalog_entries": len(entries),
        "first_read_ms": cold_ms,
        "warm_read_median_ms": warm_ms,
        "filter_median_ms": filter_ms,
        "cached_page_median_ms": page_ms,
        "catalog_read_median_ms": catalog_ms,
        "python_tracemalloc_peak_bytes": peak,
        "notes": (
            "Application-first read; OS cache was not evicted. "
            "Tracemalloc measures Python allocations; timing includes tracing overhead."
        ),
    }
    (args.output_dir / "benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
