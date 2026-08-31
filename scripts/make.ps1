# MXReady development command entry point for Windows PowerShell 5.1+.
# Usage: .\scripts\make.ps1 install|dev|test|lint|build|frontend|clean
param(
  [Parameter(Position = 0)]
  [ValidateSet("install", "dev", "test", "lint", "build", "frontend", "clean")]
  [string]$Target = "dev"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$Python = ".\.venv\Scripts\python.exe"

function Assert-LastExitCode {
  param([string]$Message)
  if ($LASTEXITCODE -ne 0) {
    throw "$Message (exit code $LASTEXITCODE)."
  }
}

function Assert-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' was not found on PATH."
  }
}

function New-VirtualEnv {
  $candidates = @(
    @{ Command = "py"; Arguments = @("-V:Astral/CPython3.11") },
    @{ Command = "py"; Arguments = @("-3.11") },
    @{ Command = "py"; Arguments = @("-3") },
    @{ Command = "python"; Arguments = @() }
  )

  foreach ($candidate in $candidates) {
    if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) {
      continue
    }
    & $candidate.Command @($candidate.Arguments) -m venv .venv 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $Python)) {
      return
    }
  }
  throw "Unable to create .venv. Install Python 3.11 or newer and try again."
}

function Assert-PythonEnv {
  if (-not (Test-Path -LiteralPath $Python)) {
    throw "Missing $Python. Run '.\scripts\make.ps1 install' first."
  }
}

function Assert-FrontendEnv {
  Assert-Command "npm.cmd"
  if (-not (Test-Path -LiteralPath "frontend\node_modules\vite\package.json")) {
    throw "Missing frontend dependencies. Run '.\scripts\make.ps1 install' first."
  }
}

if ($Target -eq "install") {
  Assert-Command "npm.cmd"
  if (-not (Test-Path -LiteralPath $Python)) {
    New-VirtualEnv
  }

  & $Python -m pip install -e ".[dev]"
  Assert-LastExitCode "Python dependency installation failed"

  Push-Location frontend
  try {
    & npm.cmd ci
    Assert-LastExitCode "Frontend dependency installation failed"
  } finally {
    Pop-Location
  }
  Write-Host "MXReady dependencies are ready. Run .\scripts\dev.ps1 to start development."
}
elseif ($Target -eq "dev") {
  Assert-PythonEnv
  & $Python -m uvicorn mxready.app:create_app --factory --reload --port 8000
  Assert-LastExitCode "Backend server exited with an error"
}
elseif ($Target -eq "test") {
  Assert-PythonEnv
  & $Python -m pytest `
    --cov=mxready `
    --cov=mxready_runner `
    --cov-report=term-missing `
    --cov-fail-under=80
  Assert-LastExitCode "Backend tests failed"
}
elseif ($Target -eq "lint") {
  Assert-PythonEnv
  & $Python -m ruff check backend runner scripts tests
  Assert-LastExitCode "Python lint failed"
}
elseif ($Target -eq "build") {
  Assert-FrontendEnv
  Push-Location frontend
  try {
    & npm.cmd run build
    Assert-LastExitCode "Frontend build failed"
  } finally {
    Pop-Location
  }
}
elseif ($Target -eq "frontend") {
  Assert-FrontendEnv
  Push-Location frontend
  try {
    & npm.cmd run dev
    Assert-LastExitCode "Frontend server exited with an error"
  } finally {
    Pop-Location
  }
}
elseif ($Target -eq "clean") {
  if (Test-Path -LiteralPath .pytest-temp) {
    Remove-Item -LiteralPath .pytest-temp -Recurse -Force
  }
  Write-Host "Removed .pytest-temp."
}
