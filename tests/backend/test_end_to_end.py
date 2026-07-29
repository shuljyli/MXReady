from pathlib import Path

from fastapi.testclient import TestClient
from mxready.app import create_app
from mxready.config import Settings
from mxready.models import ScanStatus
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog


def test_fixture_scan_to_report_badge_and_verification_bundle(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
            frontend_dist=tmp_path / "missing-frontend",
        )
    )
    with TestClient(app) as client:
        store = app.state.store
        job = store.create_job("https://github.com/example/cuda-extension", None)
        report = ScanAnalyzer(load_rule_catalog(Path("rules/v1"))).analyze(
            Path("tests/fixtures/repositories/cuda_extension"),
            repository_url="https://github.com/example/cuda-extension",
            commit="c" * 40,
            scan_id=job.id,
            stage_callback=lambda status: None,
        )
        store.save_report(report)
        store.update_job(
            job.id,
            status=ScanStatus.COMPLETED,
            stage_message="Scan complete",
            resolved_commit="c" * 40,
        )

        json_report = client.get(f"/api/scans/{report.scan_id}/report.json")
        markdown = client.get(f"/api/scans/{report.scan_id}/report.md")
        badge = client.get(f"/api/scans/{report.scan_id}/badge.svg")
        bundle = client.get(f"/api/scans/{report.scan_id}/verification-bundle")

    assert report.summary.total_count > 0
    assert json_report.status_code == 200
    assert markdown.status_code == 200
    assert "# MXReady 适配体检报告" in markdown.text
    assert "## 结果摘要" in markdown.text
    assert badge.status_code == 200
    assert badge.headers["content-type"].startswith("image/svg+xml")
    assert bundle.status_code == 200
    assert bundle.content.startswith(b"PK")


def test_built_frontend_is_served_without_shadowing_api(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    (frontend / "index.html").write_text("<main>MXReady SPA</main>", encoding="utf-8")
    (assets / "app-test.js").write_text("console.log('ok')", encoding="utf-8")
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
            frontend_dist=frontend,
        )
    )

    with TestClient(app) as client:
        root = client.get("/")
        nested = client.get("/reports/example")
        asset = client.get("/assets/app-test.js")
        health = client.get("/api/health")
        missing_api = client.get("/api/not-a-real-endpoint")

    assert root.text == "<main>MXReady SPA</main>"
    assert nested.text == root.text
    assert root.headers["cache-control"] == "no-store"
    assert asset.text == "console.log('ok')"
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert health.json()["status"] == "ok"
    assert missing_api.status_code == 404
    assert "MXReady SPA" not in missing_api.text


def test_missing_frontend_keeps_api_only_mode(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
            frontend_dist=tmp_path / "not-built",
        )
    )
    with TestClient(app) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/health").status_code == 200
