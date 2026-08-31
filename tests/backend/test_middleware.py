"""API 防护中间件测试：滑动窗口限流、请求体上限、验证上传放行语义。"""

from pathlib import Path

from fastapi.testclient import TestClient
from mxready.api.middleware import RateLimitMiddleware, RequestBodyLimitMiddleware
from mxready.app import create_app
from mxready.config import Settings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


def _echo_app(middleware):
    async def ok(request):
        await request.body()
        return JSONResponse({"ok": True})

    app = Starlette(
        routes=[
            Route("/api/scans", ok, methods=["POST"]),
            Route("/scans/1/verification-runs", ok, methods=["POST"]),
            Route("/ping", ok, methods=["POST"]),
        ]
    )
    return middleware(app)


def test_rate_limit_allows_burst_then_rejects() -> None:
    app = _echo_app(lambda target: RateLimitMiddleware(target, limit=2))

    with TestClient(app) as client:
        assert client.post("/api/scans").status_code == 200
        assert client.post("/api/scans").status_code == 200
        rejected = client.post("/api/scans")

    assert rejected.status_code == 429
    assert rejected.json()["error"]["code"] == "RATE_LIMITED"


def test_rate_limit_ignores_non_write_endpoints() -> None:
    app = _echo_app(lambda target: RateLimitMiddleware(target, limit=1))

    with TestClient(app) as client:
        for _ in range(3):
            assert client.post("/ping").status_code == 200


def test_request_body_limit_rejects_oversized_bodies() -> None:
    app = _echo_app(lambda target: RequestBodyLimitMiddleware(target, max_bytes=100))

    with TestClient(app) as client:
        small = client.post(
            "/api/scans",
            content=b"x" * 50,
            headers={"Content-Type": "application/json"},
        )
        large = client.post(
            "/api/scans",
            content=b"x" * 200,
            headers={"Content-Type": "application/json"},
        )

    assert small.status_code == 200
    assert large.status_code == 413
    assert large.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_request_body_limit_counts_stream_without_content_length() -> None:
    app = _echo_app(lambda target: RequestBodyLimitMiddleware(target, max_bytes=100))

    def chunks():
        yield b"x" * 60
        yield b"y" * 60

    with TestClient(app) as client:
        response = client.post(
            "/api/scans",
            content=chunks(),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_request_body_limit_skips_verification_uploads() -> None:
    app = _echo_app(lambda target: RequestBodyLimitMiddleware(target, max_bytes=100))

    with TestClient(app) as client:
        response = client.post(
            "/scans/1/verification-runs",
            content=b"x" * 200,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200


def test_app_enforces_rate_limit_when_enabled(tmp_path) -> None:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
            rate_limit_enabled=True,
            rate_limit_per_minute=1,
        )
    )

    with TestClient(app) as client:
        first = client.post(
            "/api/scans",
            json={"repo_url": "https://github.com/example/project", "ref": None},
        )
        second = client.post(
            "/api/scans",
            json={"repo_url": "https://github.com/example/project", "ref": None},
        )

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"


def test_app_rejects_oversized_requests_by_default(tmp_path) -> None:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("rules/v1"),
            temp_dir=tmp_path / "tmp",
            max_request_bytes=256,
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/scans",
            content=b"x" * 512,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
