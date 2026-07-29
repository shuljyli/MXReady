from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from uuid import UUID

from mxready.models import ScanStatus, VerificationRun
from mxready.verification.bundle import build_verification_bundle
from mxready_runner.inspect import DEFAULT_CHECKS


def test_bundle_contains_pinned_identity_runner_schema_and_safety_note(
    report_factory,
) -> None:
    report = report_factory()

    first_payload = build_verification_bundle(report)
    second_payload = build_verification_bundle(report)

    assert first_payload == second_payload
    with zipfile.ZipFile(io.BytesIO(first_payload)) as archive:
        manifest = json.loads(archive.read("mxready.yml"))
        names = archive.namelist()
        assert manifest["scan_id"] == str(report.scan_id)
        assert manifest["repository_commit"] == "a" * 40
        assert manifest["runner_version"] == "0.1.0"
        assert manifest["checks"] == [
            {
                "id": check.id,
                "command": check.command,
                "timeout_seconds": check.timeout_seconds,
            }
            for check in DEFAULT_CHECKS
        ]
        assert "SECURITY.md" in names
        assert "schemas/verification-result-v1.json" in names
        assert "mxready_runner/__main__.py" in names
        assert all(not name.startswith(("/", "../")) for name in names)
        assert b"explicit approval" in archive.read("SECURITY.md")


def test_verification_bundle_route_requires_completed_scan(
    client,
    report_factory,
) -> None:
    created = client.post(
        "/api/scans",
        json={"repo_url": "https://github.com/example/project", "ref": None},
    ).json()
    scan_id = UUID(created["id"])

    queued = client.get(f"/api/scans/{scan_id}/verification-bundle")
    assert queued.status_code == 409

    report = report_factory(scan_id=scan_id)
    client.app.state.store.save_report(report)
    client.app.state.store.update_job(
        scan_id,
        status=ScanStatus.COMPLETED,
        stage_message="Complete",
        resolved_commit=report.repository.commit,
    )

    response = client.get(f"/api/scans/{scan_id}/verification-bundle")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert "verification.zip" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "mxready.yml" in archive.namelist()


def test_extracted_bundle_runner_starts_without_project_dependencies(
    tmp_path,
    report_factory,
) -> None:
    with zipfile.ZipFile(io.BytesIO(build_verification_bundle(report_factory()))) as archive:
        archive.extractall(tmp_path)
    manifest_path = tmp_path / "mxready.yml"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["checks"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output_path = tmp_path / "result.json"

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "mxready_runner",
            "inspect",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert process.returncode == 0, process.stderr
    VerificationRun.model_validate_json(output_path.read_text(encoding="utf-8"))
