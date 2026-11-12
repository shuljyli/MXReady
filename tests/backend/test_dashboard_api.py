from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from mxready.models import Finding, ScanStatus, ScanSummary, Severity
from mxready.persistence.sqlite import SQLiteStore


def test_dashboard_groups_repositories_and_orders_blocker_trend(client, report_factory) -> None:
    older = datetime(2026, 1, 1, tzinfo=UTC)
    newer = datetime(2026, 2, 1, tzinfo=UTC)
    first = _persist(
        client,
        report_factory,
        repo_url="https://github.com/example/alpha",
        repository_name="alpha",
        summary=_summary(1),
        scanned_at=older,
    )
    latest = _persist(
        client,
        report_factory,
        repo_url="https://github.com/example/alpha",
        repository_name="alpha",
        summary=_summary(3),
        scanned_at=newer,
    )
    _persist(
        client,
        report_factory,
        repo_url="https://github.com/example/beta",
        repository_name="beta",
        summary=_summary(0),
        scanned_at=older,
    )

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    alpha = next(item for item in data["items"] if item["repo_url"].endswith("alpha"))
    assert alpha["scan_count"] == 2
    assert alpha["latest_scan_id"] == str(latest.scan_id)
    assert alpha["latest_status"] == "completed"
    assert [point["blocker_count"] for point in alpha["blocker_trend"]] == [1, 3]
    assert [point["scan_id"] for point in alpha["blocker_trend"]] == [
        str(first.scan_id),
        str(latest.scan_id),
    ]

    beta = next(item for item in data["items"] if item["repo_url"].endswith("beta"))
    assert beta["scan_count"] == 1
    assert [point["blocker_count"] for point in beta["blocker_trend"]] == [0]


def test_legacy_report_without_coverage_or_occurrences_counts_into_trend(
    client, report_factory
) -> None:
    report = _persist(
        client,
        report_factory,
        repo_url="https://github.com/example/legacy",
        repository_name="legacy",
        findings=[
            _finding("MXR-TEST-001", Severity.BLOCKER),
            _finding("MXR-TEST-002", Severity.INFO),
        ],
    )

    assert report.coverage is None
    assert all(not finding.occurrences for finding in report.findings)

    items = client.get("/api/dashboard").json()["items"]
    legacy = next(item for item in items if item["repo_url"].endswith("legacy"))
    assert [point["blocker_count"] for point in legacy["blocker_trend"]] == [1]


def test_dashboard_exposes_counts_not_percentage_scores(client, report_factory) -> None:
    _persist(
        client,
        report_factory,
        repo_url="https://github.com/example/alpha",
        repository_name="alpha",
        summary=_summary(2),
    )

    text = client.get("/api/dashboard").text.casefold()

    assert "%" not in text
    for banned in ("percent", "percentage", "score", "compat", "ratio", "rate"):
        assert banned not in text


def test_trend_point_derives_counts_from_summary_and_legacy_findings() -> None:
    modern = SQLiteStore._trend_point(
        _row(
            {
                "scanned_at": "2026-01-01T00:00:00+00:00",
                "summary": {"blocker_count": 5},
                "findings": [{"severity": "blocker"}],
            }
        )
    )
    legacy = SQLiteStore._trend_point(
        _row(
            {
                "scanned_at": "2026-01-01T00:00:00+00:00",
                "findings": [
                    {"severity": "blocker"},
                    {"severity": "blocker"},
                    {"severity": "warning"},
                ],
            }
        )
    )
    corrupt = SQLiteStore._trend_point(_row({"findings": []}))

    assert modern is not None and modern.blocker_count == 5
    assert legacy is not None and legacy.blocker_count == 2
    assert corrupt is None


def _summary(blocker_count: int) -> ScanSummary:
    return ScanSummary(
        total_count=blocker_count,
        blocker_count=blocker_count,
        warning_count=0,
        info_count=0,
    )


def _finding(rule_id: str, severity: Severity) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_version=1,
        severity=severity,
        category="test",
        title=f"{severity.value} finding",
        relative_path="setup.py",
        line_start=1,
        line_end=1,
        evidence="example",
        message="Review this.",
        recommendation="Validate this.",
        references=[],
    )


def _row(payload: dict) -> sqlite3.Row:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    row = connection.execute(
        "SELECT ? AS id, ? AS report_json",
        ("12345678-1234-5678-1234-567812345678", json.dumps(payload)),
    ).fetchone()
    assert row is not None
    return row


def _persist(
    client,
    report_factory,
    *,
    repo_url: str,
    repository_name: str,
    summary: ScanSummary | None = None,
    findings: list[Finding] | None = None,
    scanned_at: datetime | None = None,
    commit: str = "a" * 40,
):
    created = client.post("/api/scans", json={"repo_url": repo_url, "ref": None}).json()
    report = report_factory(
        scan_id=created["id"],
        commit=commit,
        repository_name=repository_name,
        findings=findings,
        summary=summary,
    )
    if scanned_at is not None:
        report = report.model_copy(update={"scanned_at": scanned_at})
    client.app.state.store.save_report(report)
    client.app.state.store.update_job(
        report.scan_id,
        status=ScanStatus.COMPLETED,
        stage_message="Complete",
        resolved_commit=report.repository.commit,
    )
    return report
