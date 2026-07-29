from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from mxready.models import ScanStatus, StaticStatus, VerificationStatus
from mxready.scanning.analyzer import ScanAnalyzer
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
