#!/usr/bin/env bash
# MXReady 一键开发启动（Linux / macOS）
# 启动前端 Vite dev（后台）与后端 uvicorn --reload（前台，Ctrl+C 停止）。
#
# 用法:
#   bash ./scripts/dev.sh
#   bash ./scripts/dev.sh --skip-frontend
#   bash ./scripts/dev.sh --skip-backend
set -euo pipefail

cd "$(dirname "$0")/.."

SKIP_FRONTEND=0
SKIP_BACKEND=0
for arg in "$@"; do
  case "$arg" in
    --skip-frontend) SKIP_FRONTEND=1 ;;
    --skip-backend) SKIP_BACKEND=1 ;;
    *)
      echo "未知参数: $arg（支持 --skip-frontend / --skip-backend）" >&2
      exit 1
      ;;
  esac
done

if [ "$SKIP_FRONTEND" -eq 1 ] && [ "$SKIP_BACKEND" -eq 1 ]; then
  echo "前端和后端均被跳过，没有可启动的服务。" >&2
  exit 1
fi

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "!! 未找到 $PYTHON，请先执行:  make install" >&2
  exit 1
fi

if [ "$SKIP_FRONTEND" -eq 0 ]; then
  if [ ! -d "frontend/node_modules" ]; then
    echo "!! frontend/node_modules 不存在，请先执行:  make install" >&2
    exit 1
  fi
  echo "==> 启动前端开发服务器 http://localhost:5173"
  (cd frontend && npm run dev) &
  FRONTEND_PID=$!
  trap 'kill "$FRONTEND_PID" 2>/dev/null || true' EXIT
fi

if [ "$SKIP_BACKEND" -eq 0 ]; then
  echo "==> 启动后端 http://127.0.0.1:8000 （Ctrl+C 停止）"
  "$PYTHON" -m uvicorn mxready.app:create_app --factory --reload --port 8000
else
  echo "==> 后端已跳过（--skip-backend）"
  wait
fi
