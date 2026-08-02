#!/usr/bin/env bash
# MXReady 服务器交接辅助脚本（1/3）：锁定提交并校验
# 只读操作：不安装软件、不修改驱动、不改动任何源码内容。
#
# 用法:
#   ./checkout-commit.sh [目标目录]
#
# 环境变量（可选）:
#   MXREADY_REPO    仓库地址，默认 https://github.com/pytorch/extension-cpp.git
#   MXREADY_COMMIT  期望提交，默认 1c325b202ae5e11de3cefb9a65be28f47949edd4
set -euo pipefail

REPO_URL="${MXREADY_REPO:-https://github.com/pytorch/extension-cpp.git}"
EXPECTED_COMMIT="${MXREADY_COMMIT:-1c325b202ae5e11de3cefb9a65be28f47949edd4}"
TARGET_DIR="${1:-extension-cpp}"

if [[ ! "$REPO_URL" =~ ^https:// ]]; then
  echo "!! MXREADY_REPO 必须使用 HTTPS 地址" >&2
  exit 1
fi
if [[ ! "$EXPECTED_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "!! MXREADY_COMMIT 必须是 40 位小写十六进制" >&2
  exit 1
fi

echo "==> 仓库: $REPO_URL"
echo "==> 期望提交: $EXPECTED_COMMIT"

if [[ -d "$TARGET_DIR/.git" ]]; then
  echo "==> 复用已有仓库: $TARGET_DIR"
  git -C "$TARGET_DIR" fetch --depth 1 origin "$EXPECTED_COMMIT"
else
  git init "$TARGET_DIR"
  git -C "$TARGET_DIR" remote add origin "$REPO_URL"
  git -C "$TARGET_DIR" fetch --depth 1 origin "$EXPECTED_COMMIT"
fi

git -C "$TARGET_DIR" checkout --detach FETCH_HEAD
RESOLVED_COMMIT="$(git -C "$TARGET_DIR" rev-parse HEAD)"

echo "==> 实际提交: $RESOLVED_COMMIT"
if [[ "$RESOLVED_COMMIT" != "$EXPECTED_COMMIT" ]]; then
  echo "!! 提交不一致，停止后续步骤，请勿继续验证" >&2
  exit 1
fi
echo "==> 提交已锁定并通过校验。"
