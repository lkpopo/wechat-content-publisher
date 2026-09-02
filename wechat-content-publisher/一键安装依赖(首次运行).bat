@echo off
chcp 65001 >nul
title 微信文章发布系统 - 环境初始化安装

echo ======================================================
echo       📰 微信文章发布系统 - 运行环境自动安装
echo ======================================================
echo.

set BASEDIR=%~dp0
cd /d "%BASEDIR%"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到系统 Python！
    echo 请先前往 https://www.python.org 下载安装 Python 3.10~3.12
    echo 【重要提示】：安装时务必勾选 "Add Python to PATH"！
    echo.
    pause
    exit /b 1
)

echo [1/3] 正在创建独立的虚拟运行环境 (backend\.venv)...
python -m venv "%BASEDIR%backend\.venv"

echo [2/3] 正在通过国内高速镜像源安装必要依赖库 (约需 1~2 分钟)...
"%BASEDIR%backend\.venv\Scripts\python.exe" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
"%BASEDIR%backend\.venv\Scripts\python.exe" -m pip install -r "%BASEDIR%backend\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [3/3] 正在配置 Playwright 运行支持...
"%BASEDIR%backend\.venv\Scripts\python.exe" -m playwright install-deps >nul 2>nul

echo.
echo ======================================================
echo   🎉 环境安装成功！现在您可以直接双击 "一键启动.bat" 了！
echo ======================================================
echo.
pause
