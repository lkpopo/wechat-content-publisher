$BASEDIR = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WeChat Content Publisher - Starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$envFile = Join-Path $BASEDIR "backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] backend\.env not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$backendDir = Join-Path $BASEDIR "backend"
$frontendDir = Join-Path $BASEDIR "frontend"

Write-Host "[1/2] Starting backend on port 8000..." -ForegroundColor Green
$backendScript = {
    Set-Location $args[0]
    & .venv\Scripts\activate
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
Start-Job -ScriptBlock $backendScript -ArgumentList $backendDir -Name "backend" | Out-Null

Start-Sleep -Seconds 5

Write-Host "[2/2] Starting frontend on port 5173..." -ForegroundColor Green
$frontendScript = {
    Set-Location $args[0]
    npm run dev
}
Start-Job -ScriptBlock $frontendScript -ArgumentList $frontendDir -Name "frontend" | Out-Null

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services started!" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  API Docs: http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "  Run .\stop.ps1 to stop services"
Write-Host "========================================" -ForegroundColor Cyan
