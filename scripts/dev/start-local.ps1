$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..\..")).Path
Set-Location $repoRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

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

$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Backend virtual environment was not found: $pythonExe. Create it first and install backend requirements."
}

Write-Step "Starting postgres"
Invoke-Native "Starting postgres" { docker compose up -d postgres }

Write-Step "Running migrations"
Push-Location $backendDir
try {
    Invoke-Native "Running migrations" { & $pythonExe -m alembic upgrade head }

    Write-Step "Running reference seed"
    Invoke-Native "Running reference seed" { & $pythonExe -m app.modules.reference.seed }

    Write-Step "Importing key rate events"
    Invoke-Native "Importing key rate events" { & $pythonExe -m app.modules.events.import_key_rate_events }
}
finally {
    Pop-Location
}

$backendCommand = @"
Set-Location '$backendDir'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"@

$frontendCommand = @"
Set-Location '$frontendDir'
`$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort --force
"@

Write-Step "Starting backend"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $backendCommand
)

Write-Step "Starting frontend"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $frontendCommand
)

Write-Host ""
Write-Host "FinLab local development environment is starting:" -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Swagger:  http://127.0.0.1:8000/docs"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host ""
Write-Host "Close the backend/frontend PowerShell windows manually when you are done."
