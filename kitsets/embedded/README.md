# ⚙️ Bobanana 5.0 — 嵌入式系统开发 Adaption Kitset

嵌入式系统开发的 Bobanana 5.0 适配集。角色卡与工具分离，可被 Bobanana 编排引擎发现并调度。

## 🎯 覆盖的领域

| 方向 | 角色 |
|------|------|
| 🔵 固件开发 | stm32-firmware-engineer, mcu-firmware-engineer, motor-control-engineer |
| 🟢 Linux 开发 | linux-app-dev, linux-driver-engineer, bsp-engineer, qt-developer |
| 🟡 行业应用 | bms-software-engineer, domain-controller-engineer |
| 🔴 AI/边缘 | edge-computing-engineer, model-quantization-engineer |
| 🟣 FPGA | fpga-engineer |
| 🟠 硬件设计 | embedded-hardware-engineer, rf-engineer, power-engineer |
| ⚪ 安全 | functional-safety-engineer |
| 👑 架构 | embedded-architect (OP) |

## 🧰 工具集

工具与角色卡分离，位于 `tools/` 目录：

| 工具 | 用途 |
|------|------|
| cubemx | STM32CubeMX MCU配置 |
| keil5 | Keil MDK-ARM编译 |
| ltspice | SPICE电路仿真 |
| modelsim | Verilog/VHDL仿真 |
| quartus | FPGA综合布局 |
| kicad | PCB设计 |
| openocd | 开源调试烧录 |
| jlink | SEGGER J-Link调试 |

## 🚀 使用方式

### 方案A：作为 Bobanana 插件的一部分

```bash
# 让 Boss 或 embedded-architect 发现此 kitset
# 状态机中会包含嵌入式角色节点
cp kitsets/embedded/state-machine-embedded.yaml state-machine.yaml
```

### 方案B：作为独立仓库（推荐未来拆分）

```bash
git clone https://github.com/ProfYangShengXu/embedded-kitset.git
# 在 Bobanana 配置中添加 kitset 路径
```

## 📋 状态机模板

`state-machine-embedded.yaml` 提供了完整的嵌入式开发管线：

```
embedded-architect → 固件链(STM32→MCU→电机) 
                  → Linux链(应用→驱动→BSP→QT)
                  → 应用链(BMS→域控→边缘→量化)
                  → FPGA链
                  → 硬件链(硬件→射频→电源)
                  → 功能安全 → 架构师终验 → CL
```

## 🔧 安装要求

- Python 3.12+
- 对应MCU的IDE/工具链（Keil/IAR/STM32CubeIDE）
- JLink/ST-Link 调试探针
- Git + Git LFS（固件二进制管理）
