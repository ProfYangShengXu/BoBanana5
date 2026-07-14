@echo off
chcp 65001 >nul
title Keil MDK-ARM 编译工具
echo ========================================
echo  Keil MDK-ARM — 工程编译/清理
echo ========================================

:: 自动检测 Keil UV4 路径
set UV4_PATH=
for %%P in (
    "C:\Keil_v5\UV4\UV4.exe"
    "C:\Keil\UV4\UV4.exe"
    "%PROGRAMFILES%\Keil\UV4\UV4.exe"
    "%PROGRAMFILES(x86)%\Keil\UV4\UV4.exe"
    "%PROGRAMFILES(x86)%\ARM\UV4\UV4.exe"
) do if exist %%P set UV4_PATH=%%P

:: 也检查 PATH 和注册表
where UV4.exe >nul 2>&1
if %errorlevel%==0 set UV4_PATH=UV4.exe

:: 注册表查找（如果上面的路径都没找到）
if "%UV4_PATH%"=="" (
    for /f "skip=2 tokens=2,*" %%A in (
        'reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\UV4.exe" /ve 2^>nul'
    ) do if exist "%%B" set UV4_PATH=%%B
)

if "%UV4_PATH%"=="" (
    echo [错误] 未找到 Keil MDK (UV4.exe)！
    echo   请从 ARM 官网下载安装：https://www.keil.com/download/
    echo.
    echo   安装后重试，或手动设置路径：
    echo   set UV4_PATH=C:\Keil_v5\UV4\UV4.exe
    echo   %~nx0
    pause
    exit /b 1
)

echo [OK] 找到 UV4: %UV4_PATH%

:: 检查参数
if "%1"=="" (
    echo.
    echo 用法: %~nx0 [选项] [project.uvprojx]
    echo.
    echo 选项:
    echo   -b [工程文件]   编译工程（默认）
    echo   -c [工程文件]   清理工程
    echo   -d [工程文件]   启动调试
    echo.
    echo 示例:
    echo   %~nx0 -b project.uvprojx    编译
    echo   %~nx0 -c project.uvprojx    清理
    echo   %~nx0 project.uvprojx       默认编译
    echo.
    exit /b 0
)

set ACTION=-r
set PROJ=%1

if "%1"=="-b" set ACTION=-r& set PROJ=%2
if "%1"=="-c" set ACTION=-f& set PROJ=%2
if "%1"=="-d" set ACTION=-d& set PROJ=%2

if "%PROJ%"=="" (
    echo [错误] 请指定 .uvprojx 工程文件
    exit /b 1
)
if not exist "%PROJ%" (
    echo [错误] 工程文件不存在: %PROJ%
    exit /b 1
)

echo [执行] UV4 %ACTION% "%PROJ%"
"%UV4_PATH%" %ACTION% "%PROJ%" -j0
if %errorlevel%==0 (
    echo [完成] 操作成功
) else (
    echo [完成] 操作完成（可能有警告）
)
pause
