#!/usr/bin/env bash
# MXReady 服务器交接辅助脚本（2/3）：自动 inspect + 摘要
# 只读检查：不构建、不运行项目命令、不安装软件。
#
# 用法:
#   ./run-inspect.sh [验证包ZIP] [源码目录]
set -euo pipefail

ZIP_FILE="${1:-pytorch-extension-cpp-verification.zip}"
SOURCE_DIR="${2:-extension-cpp}"

if [[ ! -f "$ZIP_FILE" ]]; then
  echo "!! 找不到验证包: $ZIP_FILE" >&2
  exit 1
fi
if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "!! 找不到源码目录: $SOURCE_DIR，请先运行 checkout-commit.sh" >&2
  exit 1
fi

if [[ ! -f "$SOURCE_DIR/mxready.yml" ]]; then
  echo "==> 解压验证包到 $SOURCE_DIR"
  python -m zipfile -e "$ZIP_FILE" "$SOURCE_DIR"
fi

if [[ ! -f "$SOURCE_DIR/SECURITY.md" ]]; then
  echo "!! 验证包缺少 SECURITY.md，来源不可信，停止。" >&2
  exit 1
fi

echo "==> SECURITY.md 前 40 行:"
head -n 40 "$SOURCE_DIR/SECURITY.md"

echo "==> 运行只读环境检查"
(
  cd "$SOURCE_DIR"
  python -m mxready_runner inspect --manifest mxready.yml --output inspect.json
)

echo "==> 检查摘要:"
python - "$SOURCE_DIR" <<'PY'
import json
import sys
from pathlib import Path

source_dir = Path(sys.argv[1])
result = json.loads((source_dir / "inspect.json").read_text(encoding="utf-8"))
print("  repository_commit:", result["repository_commit"])
for check in result["checks"]:
    print(f"  - {check['id']}: {check['status']}")
if not result["checks"] or any(
    check["status"] != "passed" for check in result["checks"]
):
    print("!! 环境检查未全部通过，停止并保存脱敏日志。")
    sys.exit(1)
print("==> 环境检查全部 passed，可继续构建。")
PY
