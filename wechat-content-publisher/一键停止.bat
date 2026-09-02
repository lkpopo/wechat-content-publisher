@echo off
chcp 65001 >nul
title 停止微信文章发布系统

echo 正在停止 8000 端口上的服务进程...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 服务已安全停止。
timeout /t 2 >nul
