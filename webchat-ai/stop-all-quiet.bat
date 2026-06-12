@echo off
chcp 65001 >nul
set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "ROOT=%~dp0.."
set "ROOT=%ROOT:~0,-1%"
"%PY%" "%ROOT%\scripts\stop_listen.py" --all
