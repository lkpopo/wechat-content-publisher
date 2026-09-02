@echo off
title WeChat Content Publisher

echo ========================================
echo   WeChat Content Publisher
echo ========================================
echo.

set BASEDIR=%~dp0

if not exist "%BASEDIR%backend\.env" (
    echo [ERROR] backend\.env not found!
    pause
    exit /b 1
)

echo [1/2] Starting backend...
start "Backend" cmd /k "cd /d %BASEDIR%backend && .venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 6 /nobreak >nul

echo [2/2] Starting frontend...
start "Frontend" cmd /k "cd /d %BASEDIR%frontend && npm run dev"

echo.
echo ========================================
echo   Services started!
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:5173
echo ========================================