# MXReady release launcher for Windows PowerShell 5.1+.
$ErrorActionPreference = "Stop"
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "Run .\install.ps1 first." }
& $Python -m mxready.cli.serve @args
if ($LASTEXITCODE -ne 0) { throw "MXReady exited with code $LASTEXITCODE." }
