# 🎮 Godot Adaption Kitset — for BoBanana 5.0

让 AI Agent 操控 Godot 引擎，零门槛开发游戏。

> **定位**: 像 Cursor/Copilot 之于代码——但之于 Godot 引擎。
> **一句话**: AI Agent 通过工具集自动完成 Godot 项目的搭建、场景编排、脚本编写、资源管理。

## 快速开始

```bash
# 创建游戏项目
npx tsx tools/godot-tools/template_library.ts fork platformer ./my-game "MyGame"

# 用 Godot 打开
godot my-game/project.godot

# 启动通信插件
python tools/tools.py plugin start
```

## 工具模块

| 模块 | 工具 | 说明 |
|------|------|------|
| **M1 · 项目脚手架** | `scaffold` | 创建 Godot 4.x 项目骨架 |
| **M2 · 场景生成** | `scene` | 生成和编辑 .tscn 场景文件 |
| **M3 · 脚本管理** | `script` | 生成 GDScript 并挂载到场景 |
| **M4 · 资源管理** | `res` | 管理纹理/音频/字体路径 |
| **M5 · 模板库** | `template` | 3 个内置游戏模板，可 fork |
| **M6 · CLI 桥接** | `godot` | 封装 godot 命令行调用 |
| **M7 · 日志捕获** | `log` | 捕获 Godot 运行时日志 |
| **M8 · 日志解析** | `parse` | 结构化日志解析和摘要 |
| **M9 · 日志工具** | `logutil` | GDScript 日志工具模板 |
| **M10 · 输入模拟** | `input` | 模拟键盘/鼠标输入 |
| **M11 · 调试编排** | `debug` | 调试闭环 + LLM 分析 |
| **M12 · 通信桥** | `bridge` | WebSocket JSON-RPC 双向通信 |

## 通信插件 (`addons/godox/`)

Godot 编辑器插件，提供 WebSocket JSON-RPC 双向通信：

```
Agent (Python) ←→ WebSocket :9800 ←→ Godot (plugin.gd)
```

| 文件 | 功能 |
|------|------|
| `plugin.cfg` | 插件配置 |
| `plugin.gd` | EditorPlugin 入口，停靠面板 |
| `mcp_server.gd` | WebSocket JSON-RPC Server |
| `input_relay.gd` | 键盘/鼠标输入中继 |
| `log_channel.gd` | 实时日志通道 |
| `validator.gd` | 项目验证和完整性检查 |

## 角色卡

26 张游戏开发角色卡，覆盖 6 个部门：

| 部门 | 角色 |
|------|------|
| 👑 架构 | game-architect (OP) |
| 📝 策划 | system-designer, level-designer, narrative-designer, combat-designer, numerical-designer |
| 💻 程序 | client-programmer, server-programmer, engine-programmer, graphics-programmer, tech-artist, ai-programmer |
| 🎨 美术 | concept-artist, 3d-modeler, animator, vfx-artist, ui-artist, environment-artist |
| 🎵 音频 | sound-designer, composer, voice-director, audio-programmer |
| 🧪 测试 | functional-tester, automation-tester, compatibility-tester, test-manager |

## 统一入口

```bash
python tools/tools.py list              # 列出所有工具
python tools/tools.py godot --version   # 检查 Godot 版本
python tools/tools.py scaffold create MyGame  # 创建项目
python tools/tools.py scene add_node MyScene  # 添加节点到场景
python tools/tools.py log capture              # 捕获日志
```

## BoBanana 5.0 集成

作为 Kitset 自动注册到管线系统中：

```json
{
  "kitset_name": "godot",
  "kitset_domains": ["godot", "game", "gamedev", "gdscript"],
  "entry_role": "game-architect"
}
```

当用户输入"用 Godot 做一个游戏"时，系统自动匹配 Godot Kitset。
