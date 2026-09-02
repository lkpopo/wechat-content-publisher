Write-Host "Stopping services..." -ForegroundColor Yellow

Get-Job -Name "backend","frontend" -ErrorAction SilentlyContinue | Stop-Job
Get-Job -Name "backend","frontend" -ErrorAction SilentlyContinue | Remove-Job -Force

Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2
Write-Host "Done." -ForegroundColor Green
