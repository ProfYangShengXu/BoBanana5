# Godot 游戏开发工具集 — 需求文档

## 目标

将 Godot 游戏开发工具集集成到 Bobanana 5.0 生态，形成完整的"AI 驱动的游戏开发管线"。

## 范围

### 产出物

| # | 产出物 | 说明 |
|---|--------|------|
| 1 | `kitsets/godot/` 目录 | 从 `C:\Users\45140\OneDrive\Desktop\code\Godot-adaption-kitset` 迁移，对齐 quant 工具集格式 |
| 2 | Godot 通信插件 | Godot addon 插件，WebSocket/JSON-RPC 双向通信，确保 Godot 和工具集实时交互 |
| 3 | 游戏工作室角色卡 | 40+ 张角色卡：系统策划/关卡策划/数值策划/战斗策划/客户端程序/服务端程序/引擎程序/图形程序/TA/AI程序/原画/3D建模/动画/VFX/UI美术/场景美术/音频/测试QA/管理 |
| 4 | 游戏架构师 OP 角色 | `game-architect` OP 标签角色卡，对齐 kitset 角色格式 |

### 角色清单（按部门）

**策划 Design (6 岗位)**
- system-designer — 经济/社交/养成/战斗系统
- level-designer — 关卡/地形/谜题/流程
- narrative-designer — 主线/支线/世界观/对话
- combat-designer — 动作/AI/手感/连招
- numerical-designer — 战斗/经济/平衡/概率

**程序 Engineering (6 岗位)**
- client-programmer — Gameplay/UI/网络/渲染
- server-programmer — 后端/数据库/网关/防外挂
- engine-programmer — 渲染/物理/工具链/内存
- graphics-programmer — Shader/光照/后处理/GPU
- tech-artist — 流程/渲染/角色/工具
- ai-programmer — 行为树/寻路/机器学习

**美术 Art (6 岗位)**
- concept-artist — 角色/场景/道具/概念
- 3d-modeler — 角色/场景/硬表面/生物
- animator — 角色/面部/技术/动捕
- vfx-artist — 技能/环境/后期/粒子
- ui-artist — 图标/界面/动效/交互
- environment-artist — 地表/植被/灯光/氛围

**音频 Audio (4 岗位)**
- sound-designer — 拟音/声音/交互
- composer — 作曲/编曲/音乐总监
- voice-director — 导演/录音/编辑
- audio-programmer — Wwise/FMOD/音频引擎

**测试 QA (4 岗位)**
- functional-tester — 用例/回归/跟踪/探索
- automation-tester — 脚本/CI/性能基准
- compatibility-tester — 多设备/多系统/硬件
- test-manager — 计划/风险评估/流程

## 关键约束

- godot 插件必须是独立的 Godot addon（`addons/godox/`），可安装在 Godot 项目中使用
- 角色卡格式对齐 `skills/roles/` 下的现有角色卡格式（role-card.yaml + SKILL.md + standards-brief.yaml）
- 游戏架构师 `game-architect` 带 OP 标签
- godot 通信插件的格式对齐其他工具集（`kitsets/godot/tools/`）
- 迁移时保留 Godot-adaption-kitset 原始的 M1-M11 工具模块

## 不做什么

- 不改 Bobanana 核心管线逻辑
- 不覆盖现有 skills/roles/ 下的角色
- 不生成游戏美术/音频资产
- 不重写 Godot-adaption-kitset 的 TypeScript 工具
