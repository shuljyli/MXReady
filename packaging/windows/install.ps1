# MXReady release installer for Windows PowerShell 5.1+.
param([switch]$Offline)
$ErrorActionPreference = "Stop"
$Arguments = @((Join-Path $PSScriptRoot "install.py"))
if ($Offline) { $Arguments += "--offline" }
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 @Arguments
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python @Arguments
} else {
  throw "Install Python 3.11+ with pip and add it to PATH."
}
if ($LASTEXITCODE -ne 0) { throw "MXReady installation failed (exit $LASTEXITCODE)." }
