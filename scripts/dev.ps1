# MXReady 一键开发启动（Windows PowerShell）
# 启动前端 Vite dev（新窗口）与后端 uvicorn --reload（当前窗口）。
#
# 用法:
#   .\scripts\dev.ps1
#   .\scripts\dev.ps1 -SkipFrontend
#   .\scripts\dev.ps1 -SkipBackend
param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend
)

# Force UTF-8 console/output encoding so Chinese text displays correctly.
try {
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  [Console]::InputEncoding = [System.Text.Encoding]::UTF8
  $OutputEncoding = [System.Text.Encoding]::UTF8
  & "$env:SystemRoot\System32\chcp.com" 65001 > $null
} catch {
}

Set-Location (Split-Path -Parent $PSScriptRoot)

$ErrorActionPreference = "Stop"
$Python = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  Write-Host "!! 未找到 $Python，请先执行:  .\scripts\make.ps1 install" -ForegroundColor Red
  exit 1
}

if (-not $SkipFrontend) {
  Write-Host "==> 启动前端开发服务器 http://localhost:5173"
  Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm.cmd run dev" `
    -WorkingDirectory (Join-Path $PWD "frontend")
}

if (-not $SkipBackend) {
  Write-Host "==> 启动后端 http://127.0.0.1:8000 （Ctrl+C 停止）"
  & $Python -m uvicorn mxready.app:create_app --factory --reload --port 8000
} else {
  Write-Host "==> 后端已跳过（-SkipBackend）"
}
