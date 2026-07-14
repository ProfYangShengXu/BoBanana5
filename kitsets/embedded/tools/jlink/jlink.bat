@echo off
chcp 65001 >nul
title SEGGER J-Link 烧录/调试工具
echo ========================================
echo  SEGGER J-Link — 烧录/调试/RTT
echo ========================================

:: 自动检测 JLink 路径
set JLINK_PATH=
for %%P in (
    "%PROGRAMFILES%\SEGGER\JLink\JLink.exe"
    "%PROGRAMFILES(x86)%\SEGGER\JLink\JLink.exe"
    "%LOCALAPPDATA%\SEGGER\JLink\JLink.exe"
) do if exist %%P set JLINK_PATH=%%P

where JLink.exe >nul 2>&1
if %errorlevel%==0 set JLINK_PATH=JLink.exe

if "%JLINK_PATH%"=="" (
    echo [错误] 未找到 JLink 工具！
    echo   请从 SEGGER 官网下载安装：https://www.segger.com/downloads/jlink/
    echo.
    pause
    exit /b 1
)

echo [OK] 找到 JLink: %JLINK_PATH%

:: 检查参数
if "%1"=="" (
    echo.
    echo 用法: %~nx0 [选项] [参数]
    echo.
    echo 选项:
    echo   -flash [device] [hex文件]   烧录固件
    echo   -rtt                       启动 RTT 日志
    echo   -gdb [device]              启动 GDB Server
    echo   -cmd [device]              启动命令行模式
    echo.
    echo 常用 device: STM32F103C8, STM32F407VG, STM32H743
    echo.
    echo 示例:
    echo   %~nx0 -flash STM32F103C8 firmware.hex
    echo   %~nx0 -gdb STM32F407VG
    echo   %~nx0 -rtt
    echo.
    exit /b 0
)

if "%1"=="-flash" (
    set DEVICE=%2
    set HEX=%3
    if "%HEX%"=="" (
        echo [错误] 用法: %~nx0 -flash [device] [hex文件]
        exit /b 1
    )
    if not exist "%HEX%" (
        echo [错误] 固件文件不存在: %HEX%
        exit /b 1
    )
    echo [执行] 烧录 %HEX% 到 %DEVICE% ...
    echo loadfile "%HEX%" > "%TEMP%\jlink_script.jlink"
    echo r >> "%TEMP%\jlink_script.jlink"
    echo g >> "%TEMP%\jlink_script.jlink"
    echo exit >> "%TEMP%\jlink_script.jlink"
    "%JLINK_PATH%" -device %DEVICE% -if SWD -speed 4000 -autoconnect 1 -CommanderScript "%TEMP%\jlink_script.jlink"
    if %errorlevel%==0 (echo [完成] 烧录成功) else (echo [失败] 烧录出错)
    goto :end
)

if "%1"=="-gdb" (
    set DEVICE=%2
    if "%DEVICE%"=="" set DEVICE=STM32F103C8
    echo [执行] 启动 GDB Server (设备: %DEVICE%) ...
    start "JLink GDB Server" "%JLINK_PATH:-gdb=%" -device %DEVICE% -if SWD -speed 4000
    goto :end
)

if "%1"=="-rtt" (
    start "JLinkRTTViewer" "%PROGRAMFILES%\SEGGER\JLink\JLinkRTTViewer.exe" 2>nul
    if errorlevel 1 start "JLinkRTTViewer" "%PROGRAMFILES(x86)%\SEGGER\JLink\JLinkRTTViewer.exe" 2>nul
    goto :end
)

if "%1"=="-cmd" (
    set DEVICE=%2
    if "%DEVICE%"=="" set DEVICE=STM32F103C8
    echo [执行] JLink 命令行模式 (设备: %DEVICE%) ...
    "%JLINK_PATH%" -device %DEVICE% -if SWD -speed 4000 -autoconnect 1
    goto :end
)

echo [错误] 未知选项: %1
exit /b 1

:end
if "%1"=="-flash" pause
