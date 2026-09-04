@echo off
chcp 65001 >nul
title 微信文章发布系统 - 一键启动

echo ======================================================
echo       📰 微信文章发布系统 (头条一键发布平台)
echo ======================================================
echo.

set BASEDIR=%~dp0
cd /d "%BASEDIR%"

set PYTHON_EXE=
if exist "%BASEDIR%backend\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BASEDIR%backend\.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [错误] 未检测到 Python 运行环境！
    echo 请先安装 Python (3.10 或更高版本)，安装时请勾选 "Add Python to PATH"。
    echo 或者请先双击运行 "一键安装依赖(首次运行).bat"。
    echo.
    pause
    exit /b 1
)

if not exist "%BASEDIR%backend\.env" (
    echo [提示] 正在创建默认配置文件 backend\.env ...
    (
        echo APP_NAME=WeChat Content Publisher
        echo DEBUG=false
        echo HOST=127.0.0.1
        echo PORT=8000
    ) > "%BASEDIR%backend\.env"
)

echo [1/2] 正在启动后台发布服务 (端口: 8000)...
start "WeChat-Publisher-Service" /min "%PYTHON_EXE%" -m uvicorn app.main:app --app-dir "%BASEDIR%backend" --host 127.0.0.1 --port 8000

echo [2/2] 正在检测服务就绪并打开浏览器...
timeout /t 3 /nobreak >nul

start http://127.0.0.1:8000

echo.
echo ======================================================
echo   🎉 系统已成功启动并在浏览器中打开！
echo   访问地址: http://127.0.0.1:8000
echo.
echo   【日常使用小贴士】
echo   1. 本窗口最小化即可，不要直接关闭。
echo   2. 若要彻底停止服务，双击运行 "一键停止.bat" 即可。
echo ======================================================
echo.
pause
