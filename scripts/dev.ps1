# MXReady combined development launcher for Windows PowerShell 5.1+.
# Starts Vite in a separate window and uvicorn in the current window.
param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
  throw "Missing $Python. Run '.\scripts\make.ps1 install' first."
}

if ($SkipFrontend -and $SkipBackend) {
  throw "Both frontend and backend were skipped; there is nothing to start."
}

if (-not $SkipFrontend) {
  if (-not (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)) {
    throw "Required command 'npm.cmd' was not found on PATH."
  }
  if (-not (Test-Path -LiteralPath "frontend\node_modules\vite\package.json")) {
    throw "Missing frontend dependencies. Run '.\scripts\make.ps1 install' first."
  }
  Write-Host "Starting the frontend at http://localhost:5173"
  Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm.cmd run dev" `
    -WorkingDirectory (Join-Path $PWD "frontend")
}

if (-not $SkipBackend) {
  Write-Host "Starting the backend at http://127.0.0.1:8000 (Ctrl+C to stop)"
  & $Python -m uvicorn mxready.app:create_app --factory --reload --port 8000
  if ($LASTEXITCODE -ne 0) {
    throw "Backend server exited with code $LASTEXITCODE."
  }
}
