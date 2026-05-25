$ErrorActionPreference = "Stop"

Write-Host "Checking Docker Engine..."

docker info *> $null

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Desktop не запущен или Docker Engine недоступен. Открой Docker Desktop, дождись запуска Docker Engine и повтори команду."
    exit 1
}

Write-Host "Starting PostgreSQL..."
docker compose up -d postgres

Write-Host ""
Write-Host "Running containers:"
docker ps

Write-Host ""
Write-Host "Backend:"
Write-Host "cd backend"
Write-Host "python -m uvicorn app.main:app --reload"

Write-Host ""
Write-Host "Frontend:"
Write-Host "cd frontend"
Write-Host "npm run dev"
