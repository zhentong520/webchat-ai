@echo off
chcp 65001 >nul
set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

if "%~1"=="" (
    echo 用法: start-all-quiet.bat 联系人
    echo 示例: start-all-quiet.bat coco
    exit /b 1
)

"%PY%" "%ROOT%\scripts\start_listen.py" --private --contacts "%~1" --welcome
