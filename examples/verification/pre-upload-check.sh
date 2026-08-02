#!/usr/bin/env bash
# MXReady 服务器交接辅助脚本（3/3）：上传前敏感信息检查（只读）
# 扫描 result.json 中残留的主机名、用户名、绝对路径与敏感键。
#
# 用法:
#   ./pre-upload-check.sh [result.json]
set -euo pipefail

RESULT_FILE="${1:-result.json}"

if [[ ! -f "$RESULT_FILE" ]]; then
  echo "!! 找不到结果文件: $RESULT_FILE" >&2
  exit 1
fi

echo "==> 检查: $RESULT_FILE"
issues=0

# 1) 绝对 home / 用户目录路径
if grep -Eq '(/home/|/Users/|C:\\Users\\)' "$RESULT_FILE"; then
  echo "  ! 发现绝对 home 路径（/home、/Users、C:\\Users）"
  issues=$((issues + 1))
fi

# 2) 常见内网与回环地址
if grep -Eq '(127\.0\.0\.1|localhost|10\.[0-9]+\.|192\.168\.[0-9]+\.|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.)' "$RESULT_FILE"; then
  echo "  ! 发现内网/回环地址"
  issues=$((issues + 1))
fi

# 3) 敏感键名（大小写不敏感，取常见形态）
if grep -Eqi '(token|password|secret|authorization|api[_-]?key)' "$RESULT_FILE"; then
  echo "  ! 发现疑似敏感键（token/password/secret/authorization/api_key）"
  issues=$((issues + 1))
fi

# 4) 当前主机名
HOSTNAME_VALUE="$(hostname 2>/dev/null || true)"
if [[ -n "$HOSTNAME_VALUE" ]] && grep -Fq "$HOSTNAME_VALUE" "$RESULT_FILE"; then
  echo "  ! 发现当前主机名: $HOSTNAME_VALUE"
  issues=$((issues + 1))
fi

if [[ "$issues" -gt 0 ]]; then
  echo "!! 发现 $issues 类潜在泄露，请人工复核并脱敏后再上传。" >&2
  exit 1
fi
echo "==> 未发现常见敏感残留；仍建议人工复核后再上传。"
