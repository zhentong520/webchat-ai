@echo off
chcp 65001 >nul
setlocal

set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"

set "ROOT=%~dp0.."
set "ROOT=%ROOT:~0,-1%"

echo ========================================
echo   WebChat AI - 一键停止全部监听
echo ========================================
echo.

"%PY%" "%ROOT%\scripts\stop_listen.py" --all
if errorlevel 1 (
    echo.
    echo [失败] 停止监听出错
    pause
    exit /b 1
)

echo.
echo [完成] 已全部停止私聊与群聊监听
pause
