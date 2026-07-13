@echo off
chcp 65001 >nul
title Bobanana 5.0 — EUI-NEO 桌面端编译
cd /d "%~dp0"

echo === Bobanana 5.0 EUI-NEO Desktop Build ===
echo.

REM Check prerequisites
where cmake >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [FAIL] cmake not found. Install CMake 3.14+: https://cmake.org/download/
    pause
    exit /b 1
)

where git >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [FAIL] git not found. Install Git: https://git-scm.com/
    pause
    exit /b 1
)

REM Step 1: Clone EUI-NEO
echo [1/3] Cloning EUI-NEO v0.5.2...
if not exist "external\EUI-NEO" (
    git clone --depth=1 --branch v0.5.2 https://github.com/sudoevolve/EUI-NEO.git external\EUI-NEO
    if %ERRORLEVEL% neq 0 (
        echo [FAIL] Git clone failed
        pause
        exit /b 1
    )
    echo   + external/EUI-NEO
) else (
    echo   OK: external/EUI-NEO already exists
)

REM Step 2: CMake configure
echo [2/3] Configuring CMake...
if not exist "build-eui" mkdir build-eui
cd build-eui
cmake .. -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    cd ..
    echo [FAIL] CMake configure failed
    pause
    exit /b 1
)
cd ..
echo   + build-eui/

REM Step 3: Build
echo [3/3] Building...
cmake --build build-eui --config Release
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Build failed
    pause
    exit /b 1
)

echo.
echo === Build complete! ===
echo.
echo Run: .\build-eui\Release\bobanana_gui.exe
echo.
pause
