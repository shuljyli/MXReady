from pathlib import Path

from fastapi.testclient import TestClient
from mxready.app import create_app
from mxready.config import Settings


def test_health_endpoint_uses_application_version(tmp_path):
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
