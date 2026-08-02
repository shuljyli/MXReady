"""本地压测专用 mock 服务：克隆阶段直接复制 fixture 仓库，不访问公网。

用法（先在项目根目录安装压测依赖）：
    pip install -e ".[load]"
    python tests/load/serve_mock.py

默认监听 127.0.0.1:8100，可通过环境变量覆盖：
    MXREADY_LOAD_HOST / MXREADY_LOAD_PORT / MXREADY_MAX_CONCURRENT_SCANS
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_FIXTURE_REPOSITORY = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "repositories"
    / "cuda_extension"
)
_FAKE_COMMIT = "a" * 40


class MockGitClient:
    """替换 `mxready.app.GitClient`：clone 时复制本地 fixture 并返回假提交号。

    仅覆盖 Git 交互环节，扫描（索引 + 规则分析 + 报告）仍走真实实现，
    从而在无公网环境下压测完整的扫描链路。
    """

    def clone(self, identity, requested_ref: str | None, destination: Path) -> str:
        del identity, requested_ref
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(_FIXTURE_REPOSITORY, destination)
        return _FAKE_COMMIT


def main() -> None:
    import mxready.app as app_module
    import uvicorn
    from mxready.config import Settings

    # 运行时替换 app 模块的全局名，create_app() 内部的 GitClient() 会解析到 MockGitClient
    app_module.GitClient = MockGitClient

    settings = Settings(
        data_dir=Path("data/load"),
        temp_dir=Path("data/load/tmp"),
        rate_limit_enabled=False,
        max_concurrent_scans=int(os.getenv("MXREADY_MAX_CONCURRENT_SCANS", "100")),
    )
    app = app_module.create_app(settings)

    host = os.getenv("MXREADY_LOAD_HOST", "127.0.0.1")
    port = int(os.getenv("MXREADY_LOAD_PORT", "8100"))
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
