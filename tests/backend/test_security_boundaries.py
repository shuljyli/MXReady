from pathlib import Path
from uuid import uuid4

from mxready.models import ScanStatus
from mxready.reporting.badge import render_badge
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog


def test_repository_source_is_never_executed(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    marker = root / "EXECUTED"
    (root / "setup.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
        encoding="utf-8",
    )

    ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
        root,
        repository_url="https://github.com/example/hostile",
        commit="d" * 40,
        scan_id=uuid4(),
        stage_callback=lambda status: None,
    )

    assert not marker.exists()


def test_svg_does_not_embed_untrusted_repository_text(report_factory) -> None:
    report = report_factory(repository_name="<script>alert(1)</script>")

    svg = render_badge(report)

    assert "<script>" not in svg
    assert "alert(1)" not in svg


def test_verification_upload_rejects_extra_fields(
    client,
    report_factory,
) -> None:
    store = client.app.state.store
    job = store.create_job("https://github.com/example/project", None)
    report = report_factory(scan_id=job.id)
    store.save_report(report)
    store.update_job(
        job.id,
        status=ScanStatus.COMPLETED,
        stage_message="Scan complete",
        resolved_commit=report.repository.commit,
    )

    response = client.post(
        f"/api/scans/{job.id}/verification-runs",
        content=b'{"schema_version":"1.0","unexpected":"value"}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VERIFICATION_SCHEMA_INVALID"
