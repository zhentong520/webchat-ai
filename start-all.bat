@echo off
chcp 65001 >nul
setlocal

set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe"

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo ========================================
echo   WebChat AI - 开启监听
echo ========================================
echo.
echo 请输入微信备注名（多个用逗号分隔）
echo 示例: Air,coco
echo.
set /p CONTACTS=监听对象: 
if "%CONTACTS%"=="" (
    echo.
    echo [取消] 未输入联系人
    pause
    exit /b 1
)

echo.
echo 即将监听: %CONTACTS%
echo 启动后会向 TA 发送 AI 小宝 自我介绍
echo.
set /p GROUPS=群聊名称（可选，直接回车跳过）: 

if "%GROUPS%"=="" (
    "%PY%" "%ROOT%\scripts\start_listen.py" --private --contacts "%CONTACTS%" --welcome
) else (
    "%PY%" "%ROOT%\scripts\start_listen.py" --private --contacts "%CONTACTS%" --groups --group-names "%GROUPS%" --welcome
)

if errorlevel 1 (
    echo.
    echo [失败] 启动监听出错
    pause
    exit /b 1
)

echo.
echo [完成] 已在后台最小化窗口运行
echo 停止监听请双击 stop-all.bat
pause
