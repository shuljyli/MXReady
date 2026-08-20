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

if ($Target -eq "install") {
  $backendOk = $false
  if (Test-Path $Python) {
    & $Python -c "import fastapi, yaml, mxready" 2>$null
    $backendOk = ($LASTEXITCODE -eq 0)
  }

  $frontendOk = Test-Path "frontend\node_modules\vite\package.json"

  if ($backendOk -and $frontendOk) {
    Write-Host "==> 检测到完整环境（.venv + frontend/node_modules），跳过重复安装。"
    Write-Host "==> 如需强制重装，请先删除 .venv 和 frontend\node_modules。"
    return
  }

  New-VirtualEnv
  & $Pip install -e ".[dev]"
  Push-Location frontend
  npm.cmd ci
  Pop-Location
  Write-Host "==> 安装完成。运行 .\scripts\dev.ps1 或 .\scripts\make.ps1 dev 启动开发。"
}
elseif ($Target -eq "dev") {
  if (-not (Test-Path $Python)) { throw "未找到 $Python，请先执行 install。" }
  & $Python -m uvicorn mxready.app:create_app --factory --reload --port 8000
}
elseif ($Target -eq "test") {
  if (-not (Test-Path $Python)) { throw "未找到 $Python，请先执行 install。" }
  & $Python -m pytest
}
elseif ($Target -eq "lint") {
  if (-not (Test-Path $Python)) { throw "未找到 $Python，请先执行 install。" }
  & $Python -m ruff check backend runner scripts tests
}
elseif ($Target -eq "build") {
  Push-Location frontend
  npm.cmd run build
  Pop-Location
}
elseif ($Target -eq "frontend") {
  Push-Location frontend
  npm.cmd run dev
  Pop-Location
}
elseif ($Target -eq "clean") {
  if (Test-Path .pytest-temp) { Remove-Item -Recurse -Force .pytest-temp }
  Write-Host "==> 已清理 .pytest-temp。"
}
