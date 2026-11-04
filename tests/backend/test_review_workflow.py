from test_scan_api import _persist_completed_report

from mxready.models import Finding, Severity


def test_reviews_append_history_without_changing_findings(client, report_factory):
    report = _persist_completed_report(client, report_factory)
    finding = Finding(
        rule_id="MXR-TEST-001",
        rule_version=1,
        severity=Severity.WARNING,
        category="test",
        title="Test",
        relative_path="a.cu",
        line_start=1,
        line_end=1,
        evidence="test",
        message="test",
        recommendation="review",
        references=[],
    )
    client.app.state.store.save_report(report.model_copy(update={"findings": [finding]}))
    url = f"/api/scans/{report.scan_id}/reviews"
    for state in ["false-positive", "confirmed"]:
        response = client.post(
            url,
            json={
                "rule_id": finding.rule_id,
                "relative_path": "a.cu",
                "status": state,
                "reason": "checked source",
            },
        )
        assert response.status_code == 200
    page = client.get(url, params={"rule_id": finding.rule_id, "relative_path": "a.cu"}).json()
    assert page["total"] == 2
    assert [r["status"] for r in page["items"]] == ["confirmed", "false-positive"]
    assert (
        client.get(f"/api/scans/{report.scan_id}/report").json()["static_status"]
        == report.static_status
    )
    assert (
        client.post(
            url,
            json={
                "rule_id": "missing",
                "relative_path": "a.cu",
                "status": "deferred",
                "reason": "reason",
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            url,
            json={
                "rule_id": finding.rule_id,
                "relative_path": "a.cu",
                "status": "deferred",
                "reason": "  ",
            },
        ).status_code
        == 400
    )


def test_review_storage_upgrades_old_schema_and_preserves_reports(tmp_path, report_factory):
    import sqlite3

    from mxready.models import FindingReviewInput
    from mxready.persistence.sqlite import _MIGRATIONS, SQLiteStore

    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as connection:
        for migration in _MIGRATIONS[:9]:
            connection.execute(migration)
        connection.execute("PRAGMA user_version = 9")
    store = SQLiteStore(path)
    job = store.create_job("https://github.com/example/project", None)
    report = report_factory(scan_id=job.id)
    store.save_report(report)
    store.initialize()
    payload = FindingReviewInput(
        rule_id="rule",
        relative_path="x'; DROP TABLE scan_jobs; --",
        status="deferred",
        reason="source review",
    )
    store.append_review(job.id, payload)
    store.initialize()
    assert store.get_report(job.id).scan_id == report.scan_id
    assert store.review_history(job.id, "rule", payload.relative_path, limit=1, offset=0).total == 1
