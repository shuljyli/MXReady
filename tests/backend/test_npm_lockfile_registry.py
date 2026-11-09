"""依赖来源一致性：前端锁文件的下载地址必须是官方 npm registry。

`Dockerfile` 的前端阶段执行 `npm ci`，它会逐条照抄 `frontend/package-lock.json` 里的
`resolved` 下载地址；仓库内并不存在 `.npmrc`，所以一旦开发者本机的全局 npm 配置指向国内
镜像站，一次普通的 `npm install` 就会把若干条 `resolved` 写成镜像域名并随之提交。
镜像站随时可能返回 5xx 或尚未同步某个 tarball（`playwright-core` 就遇到过镜像数据库报
`ER_NO_SUCH_TABLE` 的情况），CI 会在 Docker 构建近两分钟后才失败，且重跑不可靠。
这条测试把问题拦在提交之前，失败信息直接列出被污染的包。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKFILE = ROOT / "frontend" / "package-lock.json"
OFFICIAL_REGISTRY = "https://registry.npmjs.org/"


def _offending_resolved_urls() -> list[tuple[str, str]]:
    packages = json.loads(LOCKFILE.read_text(encoding="utf-8"))["packages"]
    return [
        (name, str(url))
        for name, entry in packages.items()
        for url in [entry.get("resolved")]
        if url is not None and not str(url).startswith(OFFICIAL_REGISTRY)
    ]


def test_lockfile_resolves_every_dependency_from_official_registry() -> None:
    offenders = _offending_resolved_urls()

    assert not offenders, (
        "frontend/package-lock.json 中存在非官方源的 resolved 下载地址，"
        f"共 {len(offenders)} 条：\n" + "\n".join(f"  {name} -> {url}" for name, url in offenders)
        + "\n请在未配置镜像 registry 的环境下重装依赖，或把这些 URL 的域名改回 "
        f"{OFFICIAL_REGISTRY}（integrity 无需改动，两个源是同一份字节）。"
    )


def test_lockfile_declares_official_registry_for_frontend_dependencies() -> None:
    """至少要真正解析到依赖条目，避免测试因为锁文件结构变更而空跑通过。"""
    packages = json.loads(LOCKFILE.read_text(encoding="utf-8"))["packages"]
    resolved_count = sum(1 for entry in packages.values() if entry.get("resolved"))

    assert resolved_count > 100, f"锁文件中带 resolved 的条目仅 {resolved_count} 条，结构可能已变更"
