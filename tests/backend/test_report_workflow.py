from pathlib import Path
from uuid import uuid4

from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog


def analyze(path):
    return ScanAnalyzer(load_rule_catalog(Path("src/mxready/resources/rules/v1"))).analyze(
        path,
        repository_url="https://github.com/example/project",
        commit="a" * 40,
        scan_id=uuid4(),
        stage_callback=lambda _: None,
    )


def test_occurrences_are_preserved(tmp_path):
    (tmp_path / "kernel.cu").write_text("cudaMalloc(&a, 10);\ncudaMalloc(&b, 20);\n")
    report = analyze(tmp_path)
    aggregated = [f for f in report.findings if f.count > 1]
    assert aggregated
    for finding in aggregated:
        assert len(finding.occurrences) == finding.count
        assert {o.line_start for o in finding.occurrences} == {1, 2}


def test_coverage_counts_skips_and_empty_source(tmp_path):
    (tmp_path / "image.png").write_bytes(b"image")
    (tmp_path / "bad.py").write_bytes(b"\x00")
    (tmp_path / "vendor").mkdir()
    report = analyze(tmp_path)
    assert report.coverage.analyzed_files == 0
    assert report.coverage.skipped_by_reason["UNSUPPORTED_FILE_TYPE"] == 1
    assert report.coverage.skipped_by_reason["BINARY_FILE_SKIPPED"] == 1
    assert report.coverage.excluded_directories == 1
    assert any(w.code == "NO_ANALYZABLE_SOURCE" for w in report.analysis_warnings)


def test_sarif_contains_each_occurrence_and_commit(tmp_path):
    import json

    from mxready.reporting.sarif import render_sarif

    (tmp_path / "kernel.cu").write_text("cudaMalloc(&a, 10);\ncudaMalloc(&b, 20);\n")
    report = analyze(tmp_path)
    sarif = json.loads(render_sarif(report))
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0"
    assert len(run["results"]) == sum(f.count for f in report.findings)
    assert run["versionControlProvenance"][0]["revisionId"] == report.repository.commit


def test_legacy_reports_keep_unknown_coverage_and_partial_locations(tmp_path):
    import json

    from mxready.models import ScanReport
    from mxready.reporting.sarif import render_sarif

    (tmp_path / "kernel.cu").write_text("cudaMalloc(&a, 10);\n")
    report = analyze(tmp_path)
    payload = report.model_dump(mode="json")
    payload.pop("coverage")
    for finding in payload["findings"]:
        finding.pop("occurrences")
        finding["count"] = 3
    legacy = ScanReport.model_validate(payload)
    assert legacy.coverage is None
    results = json.loads(render_sarif(legacy))["runs"][0]["results"]
    assert results
    assert all(not r["properties"]["occurrencesComplete"] for r in results)


def test_distinct_occurrences_on_same_line_are_not_lost(tmp_path):
    (tmp_path / "kernel.cu").write_text("cudaMalloc(&a, 10); cudaMalloc(&b, 20);\n")
    finding = next(f for f in analyze(tmp_path).findings if f.rule_id == "MXR-MEMORY-001")
    assert finding.count == 2
    assert len(finding.occurrences) == 2
