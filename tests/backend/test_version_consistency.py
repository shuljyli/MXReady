"""发布一致性：版本号在所有对外表面必须同源。

版本号散落在 `pyproject.toml`、两个包的 `__init__.py`、`frontend/package.json` 与其
lockfile、README 的徽章与四个安装包名、安装/接口文档的示例、以及 CHANGELOG 小节
共二十余处。发版时漏改任何一处，产物名、徽章和 `--version` 输出就会互相矛盾——
这是演示现场最容易暴露的问题。这条测试用极低的成本把它们钉死在同一来源。
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READMES = (ROOT / "README.md", ROOT / "README.en.md")
CHANGELOG = ROOT / "CHANGELOG.md"
INSTALL_DOC = ROOT / "docs" / "installation.md"
API_DOC = ROOT / "docs" / "api.md"
LOCKFILE = ROOT / "frontend" / "package-lock.json"

# 文档里出现的安装包名：`mxready-1.0.0-windows.zip`、`mxready-1.0.0.tar.gz` 等。
_DOCUMENTED_ARTIFACT = re.compile(r"mxready-(\d+\.\d+\.\d+)")


def _package_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_package_versions_match_pyproject() -> None:
    from mxready import __version__ as host_version
    from mxready_runner import __version__ as runner_version

    version = _package_version()
    assert host_version == version
    assert runner_version == version


def test_frontend_package_version_matches_pyproject() -> None:
    manifest = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert manifest["version"] == _package_version()


def test_frontend_lockfile_matches_package_json() -> None:
    """lockfile 里的根版本也要跟随，否则 `npm ci` 会报版本不一致。"""
    version = _package_version()
    lockfile = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    assert lockfile["version"] == version
    assert lockfile["packages"][""]["version"] == version


def test_installation_doc_lists_current_artifacts() -> None:
    """安装文档里的包名是用户真正要下载的东西，写错就等于给错文件名。"""
    version = _package_version()
    documented = set(_DOCUMENTED_ARTIFACT.findall(_read(INSTALL_DOC)))
    assert documented, "docs/installation.md 没有列出任何安装包名"
    assert documented == {version}, (
        f"docs/installation.md 的包名版本与 {version} 不一致：{sorted(documented)}"
    )


def test_api_doc_health_example_matches_current_version() -> None:
    version = _package_version()
    example = re.search(r'"version":\s*"(\d+\.\d+\.\d+)"', _read(API_DOC))
    assert example is not None, "docs/api.md 缺少 /api/health 响应示例"
    assert example.group(1) == version


def test_readme_badge_and_installer_names_match_pyproject() -> None:
    version = _package_version()
    for path in READMES:
        readme = _read(path)
        assert f"version-{version}-" in readme, f"{path.name} 版本徽章未同步"
        for artifact in (
            f"mxready-{version}-windows.zip",
            f"mxready-{version}-linux.zip",
            f"mxready-{version}-macos.zip",
            f"mxready-{version}-py3-none-any.whl",
        ):
            assert artifact in readme, f"{path.name} 安装包名未同步：{artifact}"


def test_changelog_documents_the_current_version() -> None:
    version = _package_version()
    changelog = _read(CHANGELOG)
    assert f"## [{version}]" in changelog, "CHANGELOG 缺少当前版本的条目"
    # 已发布版本的第一条 compare 链接必须指向该 tag，否则 Releases 页面的
    # "完整变更记录" 链接会给用户看到错误区间。
    assert f"compare/v{version}...HEAD" in changelog
