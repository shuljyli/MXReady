from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from mxready.app import create_app
from mxready.config import Settings
from mxready.models import ScanStatus
from mxready_runner.inspect import DEFAULT_CHECKS


def test_starting_another_app_does_not_fail_live_or_queued_jobs(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", temp_dir=tmp_path / "tmp")
    with TestClient(create_app(settings, start_worker=False)) as first:
        store = first.app.state.store
        live = store.create_job("https://github.com/example/live", None)
        assert store.claim_job(live.id, "first-worker", lease_seconds=120)
        queued = store.create_job("https://github.com/example/queued", None)
        with TestClient(create_app(settings, start_worker=False)):
            assert store.get_job(live.id).status is ScanStatus.CLONING
            assert store.get_job(queued.id).status is ScanStatus.QUEUED


def test_reports_and_badges_expire_without_another_upload(client, report_factory):
    store = client.app.state.store
    job = store.create_job("https://github.com/example/project", None)
    report = report_factory(scan_id=job.id)
    store.save_report(report)
    store.update_job(job.id, status=ScanStatus.COMPLETED, stage_message="Done")
    historical = datetime.now(UTC) - timedelta(days=31)
    import json

    payload = json.dumps(
        {
            "schema_version": "1.0",
            "scan_id": str(job.id),
            "repository_commit": report.repository.commit,
            "runner_version": "0.1.0",
            "environment_fingerprint": "sha256:" + "f" * 64,
            "checks": [
                {
                    "id": c.id,
                    "command": c.command,
                    "status": "passed",
                    "return_code": 0,
                    "stdout": "ok",
                    "stderr": "",
                    "duration_ms": 1,
                }
                for c in DEFAULT_CHECKS
            ],
            "commands": [],
            "started_at": (historical - timedelta(minutes=1)).isoformat(),
            "finished_at": historical.isoformat(),
            "overall_status": "passed",
        }
    ).encode()
    uploaded = client.app.state.scan_service.attach_verification(job.id, payload, now=historical)
    assert uploaded.verification_status == "verified"
    for suffix in ("report", "report.json"):
        assert client.get(f"/api/scans/{job.id}/{suffix}").json()["verification_status"] == "stale"
    assert "verification-stale" in client.get(f"/api/scans/{job.id}/badge.svg").text
    assert "stale" in client.get(f"/api/scans/{job.id}/report.md").text
