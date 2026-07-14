@echo off
chcp 65001 >nul
title STM32CubeMX 代码生成工具
echo ========================================
echo  STM32CubeMX — MCU配置代码生成
echo ========================================

:: 自动检测 CubeMX 路径
set CUBEMX_PATH=
for %%P in (
    "%PROGRAMFILES%\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe"
    "%PROGRAMFILES%\STM32CubeMX\STM32CubeMX.exe"
    "%PROGRAMFILES(x86)%\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe"
    "%LOCALAPPDATA%\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe"
) do if exist %%P set CUBEMX_PATH=%%P

:: 也检查 PATH
where STM32CubeMX.exe >nul 2>&1
if %errorlevel%==0 set CUBEMX_PATH=STM32CubeMX.exe

if "%CUBEMX_PATH%"=="" (
    echo [错误] 未找到 STM32CubeMX！
    echo   请从 ST 官网下载安装：https://www.st.com/stm32cubemx
    echo.
    echo   或者手动设置路径后运行：
    echo   set CUBEMX_PATH=C:\你的路径\STM32CubeMX.exe
    echo   %~nx0
    pause
    exit /b 1
)

echo [OK] 找到 CubeMX: %CUBEMX_PATH%

:: 检查参数
if "%1"=="" (
    echo.
    echo 用法: %~nx0 [选项] [script.ioc]
    echo.
    echo 选项:
    echo   -g           启动 GUI 模式
    echo   -s           启动脚本模式（需提供 .ioc 文件）
    echo.
    echo 示例:
    echo   %~nx0 -g                    打开图形界面
    echo   %~nx0 -s project.ioc        从 .ioc 生成代码
    echo   %~nx0 project.ioc           同上
    echo.
    exit /b 0
)

if "%1"=="-g" (
    echo 启动 GUI 模式...
    start "" "%CUBEMX_PATH%"
    exit /b 0
)

:: 脚本模式
set IOC_FILE=%1
if "%1"=="-s" set IOC_FILE=%2
if "%IOC_FILE%"=="" (
    echo [错误] 请指定 .ioc 文件
    exit /b 1
)
if not exist "%IOC_FILE%" (
    echo [错误] 文件不存在: %IOC_FILE%
    exit /b 1
)

echo [执行] 生成代码: %IOC_FILE%
"%CUBEMX_PATH%" -q "%IOC_FILE%"
if %errorlevel%==0 (
    echo [完成] 代码生成成功
) else (
    echo [失败] 代码生成出错
)
pause
