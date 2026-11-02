import json
from datetime import UTC, datetime, timedelta

from test_scan_api import _make_payload, _persist_completed_report

from mxready.models import MigrationChecklistItem, ScanStatus


def test_history_filters_and_pages_without_report_payloads(client, report_factory):
    report = _persist_completed_report(client, report_factory)
    client.post("/api/scans", json={"repo_url": "https://gitee.com/example/other"})
    response = client.get("/api/scans", params={"status": "completed", "q": "project", "limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == str(report.scan_id)
    assert "report_json" not in data["items"][0]
    assert client.get("/api/scans", params={"q": "%' OR 1=1 --"}).json()["total"] == 0
    assert client.get("/api/scans", params={"limit": 1000}).status_code == 400


def test_verification_history_keeps_runs_and_redacts_detail(client, report_factory):
    report = _persist_completed_report(client, report_factory)
    for days in (31, 0):
        payload = json.loads(
            _make_payload(
                scan_id=report.scan_id,
                repository_commit=report.repository.commit,
                finished_at=datetime.now(UTC) - timedelta(days=days),
            )
        )
        payload["checks"][0]["stdout"] = "TOKEN=private-test-value <script>alert(1)</script>"
        result = client.post(f"/api/scans/{report.scan_id}/verification-runs", json=payload)
        assert result.status_code == 200
    page = client.get(f"/api/scans/{report.scan_id}/verification-runs").json()
    assert page["total"] == 2
    assert [row["status"] for row in page["items"]] == ["verified", "stale"]
    assert page["items"][0]["is_latest"] is True
    assert page["items"][1]["is_latest"] is False
    detail = client.get(f"/api/scans/{report.scan_id}/verification-runs/{page['items'][0]['id']}")
    assert detail.status_code == 200
    assert "private-test-value" not in detail.text
    assert "[REDACTED]" in detail.text
    assert "expires_at" in detail.json()["summary"]


def test_checklist_is_persistent_independent_of_verification(client, report_factory):
    report = _persist_completed_report(client, report_factory)
    report = report.model_copy(
        update={
            "migration_checklist": [
                MigrationChecklistItem(
                    rule_id="MXR-TEST-001",
                    title="Review",
                    action="Review manually",
                    affected_files=["a.cu"],
                )
            ]
        }
    )
    store = client.app.state.store
    store.save_report(report)
    response = client.patch(
        f"/api/scans/{report.scan_id}/checklist/MXR-TEST-001", json={"completed": True}
    )
    assert response.status_code == 200
    assert response.json()["migration_checklist"][0]["completed"] is True
    payload = _make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=datetime.now(UTC),
    )
    client.post(
        f"/api/scans/{report.scan_id}/verification-runs",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    refreshed = client.get(f"/api/scans/{report.scan_id}/report").json()
    assert refreshed["migration_checklist"][0]["completed"] is True
    assert refreshed["static_status"] == report.static_status
    assert (
        client.patch(
            f"/api/scans/{report.scan_id}/checklist/MISSING", json={"completed": True}
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/scans/{report.scan_id}/checklist/MXR-TEST-001", json={"completed": "true"}
        ).status_code
        == 400
    )


def test_history_order_is_stable_and_offset_supported(client, report_factory):
    first = _persist_completed_report(client, report_factory)
    second = _persist_completed_report(client, report_factory)
    page = client.get("/api/scans", params={"limit": 1}).json()
    next_page = client.get("/api/scans", params={"limit": 1, "offset": 1}).json()
    assert page["items"][0]["id"] == str(second.scan_id)
    assert next_page["items"][0]["id"] == str(first.scan_id)
    client.app.state.store.update_job(
        first.scan_id, status=ScanStatus.FAILED, stage_message="failed"
    )
    assert client.get("/api/scans", params={"status": "failed"}).json()["total"] == 1


def test_verification_detail_is_bound_to_scan(client, report_factory):
    from uuid import uuid4

    report = _persist_completed_report(client, report_factory)
    other = _persist_completed_report(client, report_factory)
    payload = _make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=datetime.now(UTC),
    )
    client.post(
        f"/api/scans/{report.scan_id}/verification-runs",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    run_id = client.get(f"/api/scans/{report.scan_id}/verification-runs").json()["items"][0]["id"]
    assert client.get(f"/api/scans/{other.scan_id}/verification-runs/{run_id}").status_code == 404
    assert client.get(f"/api/scans/{uuid4()}/verification-runs").status_code == 404


def test_upgrade_preserves_last_legacy_verification_once(tmp_path, report_factory):
    import sqlite3
    from contextlib import closing

    from mxready.models import VerificationRun
    from mxready.persistence.sqlite import _MIGRATIONS, SQLiteStore

    path = tmp_path / "old.db"
    with closing(sqlite3.connect(path)) as connection, connection:
        for migration in _MIGRATIONS[:5]:
            connection.execute(migration)
        connection.execute("PRAGMA user_version = 5")
    store = SQLiteStore(path)
    job = store.create_job("https://github.com/example/project", None)
    report = report_factory(scan_id=job.id)
    run = VerificationRun.model_validate_json(
        _make_payload(
            scan_id=job.id,
            repository_commit=report.repository.commit,
            finished_at=datetime.now(UTC),
        )
    )
    store.save_report(report)
    store.save_verification(job.id, run)
    store.initialize()
    store.initialize()
    rows, total, latest = store.verification_history(job.id)
    assert total == 1 and rows[0][2] == run and latest == rows[0][0]
    # Legacy rows never recorded an upload timestamp separately from job updates.
    assert rows[0][1] is None
