# SEGGER J-Link — 调试探针工具
# 工具路径：C:/Program Files/SEGGER/JLink/JLink.exe
# CLI模式：JLink.exe -device STM32F103C8 -if SWD -speed 4000

# 典型用法：
# JLink.exe -device STM32F103C8 -if SWD -speed 4000 -autoconnect 1
#   -Commander模式：loadfile firmware.hex, r, g
# JLinkRTTClient.exe  # RTT日志查看
# JLinkGDBServer.exe -device STM32F103C8 -endian little -if SWD

# 支持：JTAG, SWD, RTT实时日志, GDB Server
