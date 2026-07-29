from __future__ import annotations

from uuid import uuid4


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
    assert len(body["rules"]) == 4
