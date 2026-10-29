"""Render GitHub Release notes from the CHANGELOG section of one version.

发布正文以 CHANGELOG 为唯一事实源，避免"发版说明"和"变更记录"两份文本各自漂移。
找不到对应版本小节时直接失败——这正是发布前必须满足的门槛：版本号升了但没写
CHANGELOG，Release 就不该生成。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = ROOT / "CHANGELOG.md"

# 固定的契约声明：始终为真，不随版本状态漂移。
_STATUS_FOOTER = """
---

### 验证状态 / Verification status

- MXReady 只提供**静态迁移风险提示**，不提供兼容性结论，也不给百分比兼容分数。
- 任何"已在沐曦环境验证"的说法，必须绑定到具体提交、在受控沐曦 GPU 上跑出
  `verified` 结果，且结果不超过 30 天。静态检查通过**不代表**项目已兼容 MXMACA。
- 安装包 ZIP 不附带 Python 与 Git，使用前需预装 Python 3.11+ 与 Git。
"""


def render(changelog: str, version: str) -> str | None:
    """取出 `## [<version>]` 到下一个 `## [` 之间的内容。"""
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*$", re.MULTILINE)
    match = heading.search(changelog)
    if match is None:
        return None
    remainder = changelog[match.end() :]
    following = re.search(r"^## \[", remainder, re.MULTILINE)
    body = remainder[: following.start()] if following else remainder
    return body.strip("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True, help="要渲染的版本号，例如 0.3.0")
    parser.add_argument("--changelog", type=Path, default=DEFAULT_CHANGELOG)
    parser.add_argument("--output", type=Path, required=True, help="写入的 Markdown 路径")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    changelog = arguments.changelog.read_text(encoding="utf-8")
    section = render(changelog, arguments.version)
    if section is None:
        print(
            f"CHANGELOG.md 缺少 [{arguments.version}] 小节，拒绝生成发布说明。",
            file=sys.stderr,
        )
        return 1
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        f"## MXReady {arguments.version}\n\n{section}\n{_STATUS_FOOTER}",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
