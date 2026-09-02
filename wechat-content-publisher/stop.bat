@echo off
title Stop WeChat Content Publisher

echo Stopping services...

taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

timeout /t 3 /nobreak >nul

echo Done.
timeout /t 1 /nobreak >nul