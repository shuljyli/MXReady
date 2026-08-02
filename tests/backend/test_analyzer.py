from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from mxready.models import (
    Finding,
    ScanStatus,
    Severity,
    SourceReference,
    StaticStatus,
    VerificationStatus,
)
from mxready.scanning.analyzer import ScanAnalyzer, _aggregate_findings
from mxready.scanning.rule_loader import load_rule_catalog


def test_analyzer_builds_report_and_migration_checklist() -> None:
    stages: list[ScanStatus] = []
    report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        Path("tests/fixtures/repositories/cuda_extension"),
        repository_url="https://github.com/example/cuda-extension",
        commit="b" * 40,
        scan_id=uuid4(),
        stage_callback=stages.append,
    )

    assert stages == [ScanStatus.INDEXING, ScanStatus.ANALYZING]
    assert report.static_status in {StaticStatus.BLOCKED, StaticStatus.WARNINGS}
    assert report.verification_status is VerificationStatus.NOT_RUN
    assert report.summary.total_count == len(report.findings)
    assert report.migration_checklist
    assert all(
        item.rule_id
        in {
            finding.rule_id
            for finding in report.findings
            if finding.severity.value in {"blocker", "warning"}
        }
        for item in report.migration_checklist
    )


def test_analyzer_keeps_index_warnings_separate_from_findings(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text(
        "x" * 1_048_577,
        encoding="utf-8",
    )

    report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        tmp_path,
        repository_url="https://gitee.com/example/large-project.git",
        commit="c" * 40,
        scan_id=uuid4(),
        stage_callback=lambda _: None,
    )

    assert report.findings == []
    assert report.analysis_warnings[0].code == "FILE_TOO_LARGE"
    assert report.analysis_warnings[0].relative_path == "large.py"


def test_checklist_groups_affected_files_by_unique_rule() -> None:
    report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        Path("tests/fixtures/repositories/cuda_extension"),
        repository_url="https://github.com/example/cuda-extension",
        commit="d" * 40,
        scan_id=uuid4(),
        stage_callback=lambda _: None,
    )

    assert len({item.rule_id for item in report.migration_checklist}) == len(
        report.migration_checklist
    )
    assert all(
        item.affected_files == sorted(set(item.affected_files))
        for item in report.migration_checklist
    )
    assert all(item.completed is False for item in report.migration_checklist)


def test_aggregate_findings_merges_duplicate_rule_file_hits() -> None:
    first = _finding(rule_id="MXR-TEST-001", path="a.py", line_start=1, line_end=2)
    second = _finding(rule_id="MXR-TEST-001", path="a.py", line_start=5, line_end=6)

    merged = _aggregate_findings([first, second])

    assert len(merged) == 1
    assert merged[0].count == 2
    assert merged[0].line_start == 1
    assert merged[0].line_end == 6
    assert merged[0].severity is Severity.WARNING


def test_aggregate_findings_keeps_distinct_rules_and_files_apart() -> None:
    findings = [
        _finding(rule_id="MXR-TEST-001", path="a.py"),
        _finding(rule_id="MXR-TEST-001", path="b.py"),
        _finding(rule_id="MXR-TEST-002", path="a.py"),
    ]

    merged = _aggregate_findings(findings)

    assert len(merged) == 3
    assert all(item.count == 1 for item in merged)


def test_analyzer_aggregates_repeated_hits_in_one_file(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(
        'import subprocess\n'
        'subprocess.run(["nvcc", "a.cu"], check=True)\n'
        'subprocess.run(["nvcc", "b.cu"], check=True)\n',
        encoding="utf-8",
    )

    report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        tmp_path,
        repository_url="https://github.com/example/project",
        commit="e" * 40,
        scan_id=uuid4(),
        stage_callback=lambda _: None,
    )

    nvcc = [item for item in report.findings if item.rule_id == "MXR-TOOLCHAIN-001"]
    assert len(nvcc) == 1
    assert nvcc[0].count == 2
    assert report.summary.total_count == len(report.findings)


def _finding(*, rule_id: str, path: str, line_start: int = 1, line_end: int = 1) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version=1,
        severity=Severity.WARNING,
        category="test",
        title="Test finding",
        relative_path=path,
        line_start=line_start,
        line_end=line_end,
        evidence="evidence",
        message="Test message",
        recommendation="Review it.",
        references=[SourceReference(title="Primary", url="https://example.com/docs")],
    )
