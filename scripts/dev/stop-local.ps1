$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..\..")).Path
Set-Location $repoRoot

function Invoke-Native {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

Write-Host "==> Stopping postgres" -ForegroundColor Cyan
Invoke-Native "Stopping postgres" { docker compose stop postgres }

Write-Host ""
Write-Host "Postgres was stopped." -ForegroundColor Green
Write-Host "If backend/frontend dev PowerShell windows are still open, close them manually."
