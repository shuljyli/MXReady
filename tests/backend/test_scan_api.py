from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from mxready.models import ScanStatus


def test_create_scan_returns_202_and_job(client) -> None:
    response = client.post(
        "/api/scans",
        json={
            "repo_url": "https://github.com/pytorch/extension-cpp",
            "ref": None,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert client.get(f"/api/scans/{body['id']}").status_code == 200
    client.app.state.scan_service.run_scan.assert_called_once()


def test_invalid_repository_input_returns_safe_400_error(client) -> None:
    response = client.post(
        "/api/scans",
        json={
            "repo_url": "https://user:secret@github.com/owner/repo",
            "ref": "--upload-pack=bad",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] in {
        "INVALID_REPOSITORY_URL",
        "INVALID_GIT_REF",
    }
    assert body["error"]["details"] == {}
    assert "secret" not in response.text


def test_unknown_scan_returns_structured_404(client) -> None:
    response = client.get(f"/api/scans/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCAN_NOT_FOUND"


def test_report_for_queued_scan_returns_409(client) -> None:
    created = client.post(
        "/api/scans",
        json={"repo_url": "https://gitee.com/example/project", "ref": None},
    ).json()

    response = client.get(f"/api/scans/{created['id']}/report")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCAN_NOT_COMPLETED"


def test_rules_endpoint_exposes_public_versioned_catalog(client) -> None:
    response = client.get("/api/rules")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "1"
    assert len(body["rules"]) == 24


def test_upload_verification_updates_and_persists_report(
    client,
    report_factory,
) -> None:
    report = _persist_completed_report(client, report_factory)
    payload = _make_payload(
        scan_id=report.scan_id,
        repository_commit=report.repository.commit,
        finished_at=datetime.now(UTC),
    )

    response = client.post(
        f"/api/scans/{report.scan_id}/verification-runs",
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert client.app.state.store.get_report(report.scan_id).verification_status.value == "verified"
    assert client.app.state.store.get_verification(report.scan_id) is not None


def test_upload_verification_rejects_mismatch_and_oversize(
    client,
    report_factory,
) -> None:
    report = _persist_completed_report(client, report_factory)
    mismatch = _make_payload(
        scan_id=report.scan_id,
        repository_commit="b" * 40,
        finished_at=datetime.now(UTC),
    )

    mismatch_response = client.post(
        f"/api/scans/{report.scan_id}/verification-runs",
        content=mismatch,
        headers={"Content-Type": "application/json"},
    )
    oversized_response = client.post(
        f"/api/scans/{report.scan_id}/verification-runs",
        content=b"x" * 1_048_577,
        headers={"Content-Type": "application/json"},
    )

    assert mismatch_response.status_code == 409
    assert mismatch_response.json()["error"]["code"] == "VERIFICATION_COMMIT_MISMATCH"
    assert oversized_response.status_code == 413
    assert oversized_response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"


def _persist_completed_report(client, report_factory):
    created = client.post(
        "/api/scans",
        json={"repo_url": "https://github.com/example/project", "ref": None},
    ).json()
    report = report_factory(scan_id=created["id"])
    client.app.state.store.save_report(report)
    client.app.state.store.update_job(
        report.scan_id,
        status=ScanStatus.COMPLETED,
        stage_message="Complete",
        resolved_commit=report.repository.commit,
    )
    return report


def _make_payload(
    *,
    scan_id,
    repository_commit: str,
    finished_at: datetime,
) -> bytes:
    return json.dumps(
        {
            "schema_version": "1.0",
            "scan_id": str(scan_id),
            "repository_commit": repository_commit,
            "runner_version": "0.1.0",
            "environment_fingerprint": f"sha256:{'f' * 64}",
            "checks": [
                {
                    "id": identifier,
                    "command": [identifier],
                    "status": "passed",
                    "return_code": 0,
                    "stdout": "ok",
                    "stderr": "",
                    "duration_ms": 1,
                }
                for identifier in ("mx-smi", "pytorch-device")
            ],
            "commands": [],
            "started_at": (finished_at - timedelta(minutes=1)).isoformat(),
            "finished_at": finished_at.isoformat(),
            "overall_status": "passed",
        }
    ).encode()
