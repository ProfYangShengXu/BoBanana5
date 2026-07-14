@echo off
chcp 65001 >nul
title 嵌入式工具集入口
echo ========================================
echo  Bobanana 5.0 — 嵌入式工具集
echo  位置: kitsets\embedded\tools\
echo ========================================
echo.
echo 可用工具:
echo.
echo   cubemx      STM32CubeMX MCU配置代码生成
echo     cubemx.bat -g              打开GUI
echo     cubemx.bat -s project.ioc  生成代码
echo.
echo   keil5       Keil MDK-ARM 编译
echo     keil5.bat -b project.uvprojx  编译
echo     keil5.bat -c project.uvprojx  清理
echo.
echo   jlink       SEGGER J-Link 烧录调试
echo     jlink.bat -flash DEVICE file.hex  烧录
echo     jlink.bat -gdb DEVICE             GDB Server
echo     jlink.bat -rtt                     RTT日志
echo.
echo 示例:
echo   cubemx -g
echo   keil5 -b my_project.uvprojx
echo   jlink -flash STM32F103C8 firmware.hex
echo.
echo 提示: 工具会自动检测安装路径，无需手动配置。
echo ========================================
