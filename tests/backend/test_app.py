from pathlib import Path

from fastapi.testclient import TestClient

from mxready import __version__ as packaged_version
from mxready.app import create_app
from mxready.config import Settings


def test_health_endpoint_uses_application_version(tmp_path):
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            rules_dir=Path("src/mxready/resources/rules/v1"),
            temp_dir=tmp_path / "tmp",
        ),
        start_worker=False,
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    # 断言的是「健康检查上报的是包版本」这一接线关系，而不是某个具体字面量：
    # 发版时版本号变动不该让这条测试变成必须人工跟改的负担。
    assert response.json() == {"status": "ok", "version": packaged_version}
