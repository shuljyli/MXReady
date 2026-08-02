# MXReady 开发命令入口（Windows PowerShell）
# 统一 install / dev / test / lint / build / frontend / clean。
#
# 用法:
#   .\scripts\make.ps1 install
#   .\scripts\make.ps1 dev
#   .\scripts\make.ps1 test
#   .\scripts\make.ps1 lint
#   .\scripts\make.ps1 build
param(
  [Parameter(Position = 0)]
  [ValidateSet("install", "dev", "test", "lint", "build", "frontend", "clean")]
  [string]$Target = "dev"
)

$ErrorActionPreference = "Stop"
$Python = ".\.venv\Scripts\python.exe"
$Pip = ".\.venv\Scripts\pip.exe"

function New-VirtualEnv {
  $candidates = @("py -3.11", "py -3", "python")
  foreach ($candidate in $candidates) {
    $parts = $candidate -split " "
    $executable = $parts[0]
    $arguments = @()
    if ($parts.Count -gt 1) { $arguments += $parts[1] }
    $arguments += @("-m", "venv", ".venv")
    & $executable @arguments 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $Python)) { return }
  }
  throw "无法创建 .venv，请确认已安装 Python 3.11 或更高版本。"
}

switch ($Target) {
  "install" {
    New-VirtualEnv
    & $Pip install -e ".[dev]"
    Push-Location frontend
    npm.cmd ci
    Pop-Location
    Write-Host "==> 安装完成。运行 .\scripts\dev.ps1 或 .\scripts\make.ps1 dev 启动开发。"
  }
  "dev" {
    if (-not (Test-Path $Python)) { throw "未找到 $Python，请先执行 install。" }
    & $Python -m uvicorn mxready.app:create_app --factory --reload --port 8000
  }
  "test" {
    if (-not (Test-Path $Python)) { throw "未找到 $Python，请先执行 install。" }
    & $Python -m pytest
  }
  "lint" {
    if (-not (Test-Path $Python)) { throw "未找到 $Python，请先执行 install。" }
    & $Python -m ruff check backend runner scripts tests
  }
  "build" {
    Push-Location frontend
    npm.cmd run build
    Pop-Location
  }
  "frontend" {
    Push-Location frontend
    npm.cmd run dev
    Pop-Location
  }
  "clean" {
    if (Test-Path .pytest-temp) { Remove-Item -Recurse -Force .pytest-temp }
    Write-Host "==> 已清理 .pytest-temp。"
  }
}
