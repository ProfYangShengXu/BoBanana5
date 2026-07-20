# Bobanana 5.0 — 定时任务板块优化需求文档

## 1. 目标

提升 Bobanana 5.0 定时任务（Scheduled Tasks）板块的用户体验，使用户能**直接在 Reasonix 桌面端创建、查看、管理定时任务**，无需手动操作 CLI 或 Windows 任务计划程序。

## 2. 用户故事

| 编号 | 角色 | 故事 |
|------|------|------|
| US-01 | Reasonix 桌面用户 | 我希望能从桌面端直接创建定时任务，填写目标、执行时间和频率 |
| US-02 | Reasonix 桌面用户 | 我希望能查看所有已注册定时任务的状态、下次执行时间 |
| US-03 | Reasonix 桌面用户 | 我希望能暂停、恢复、删除一个定时任务 |
| US-04 | Reasonix 桌面用户 | 我希望能查看定时任务的执行历史日志 |
| US-05 | Reasonix 桌面用户 | 我希望能临时手动触发一个已注册的定时任务立即执行 |

## 3. 当前状况分析

### 已有基础（BoBanana5 项目内）

| 组件 | 状态 | 详情 |
|------|------|------|
| `scripts/pipeline_scheduler.py` | ✅ 已实现 | 完整的 CLI 调度器，支持 schedule/run/list/remove/install-winsch |
| `.reasonix/scheduler/tasks.json` | ✅ 数据层 | 定时任务持久化存储 |
| `.reasonix/scheduler/logs/` | ✅ 日志层 | 执行日志目录 |
| Windows Task Scheduler 集成 | ✅ | 通过 `schtasks` 命令注册 OS 级定时触发 |

### 缺失项（待优化）

| 组件 | 现状 | 目标 |
|------|------|------|
| **MCP Tool 暴露** | ❌ 无相关 MCP tool | 新增 `schedule_create/list/remove/trigger/logs` 等 MCP tools |
| **TUI 仪表盘** | ❌ `gui_dashboard.py` 不显示定时任务 | 集成定时任务面板（列表+状态+操作） |
| **EUI-NEO 桌面 GUI** | ❌ 无调度界面 | 新增定时任务管理页面/弹窗 |
| **mcp_server.py** | ❌ 无调度端点 | 新增 JSON-RPC 方法暴露调度所有功能 |
| **Reasonix 桌面端直接操作** | ❌ 需通过 CLI | 通过 MCP tools 直接在桌面端创建 |

### 参考项目（DeepSeek-Reasonix）

DeepSeek-Reasonix 仓库即是本项目的上游/镜像。其结构与 BoBanana5 完全一致，其中:
- `pipeline_scheduler.py` 存在于两个项目中，保持同步
- 桌面端集成方式通过 `bobanana-plugin/reasonix-plugin.json` + `.reasonix/desktop-topic-*.json` 实现
- **无 MCP 级别的调度接口是最明显的缺口**

## 4. 范围

### 包含（In Scope）

1. **MCP Tool 层**：在 `.mcp.json` 中注册至少 4 个调度相关 MCP tools
2. **MCP 服务器层**：在 `mcp_server.py` 中新增 schedule_* JSON-RPC 方法
3. **TUI 仪表盘集成**：在 `gui_dashboard.py` 中添加定时任务面板
4. **EUI-NEO 桌面端集成**：为桌面端提供 schedule 数据通道

### 不包含（Out of Scope）

- 跨平台调度（Linux cron / macOS launchd）— 本版本仅 Windows
- 定时任务的图形化拖拽式配置
- 定时任务的通知推送（邮件/短信）
- 多用户权限管理

## 5. 关键约束

1. **不破坏已有 CLI 功能**：`scripts/pipeline_scheduler.py` 的 CLI 接口必须保持向后兼容
2. **数据格式不变**：`.reasonix/scheduler/tasks.json` 的 JSON Schema 不变
3. **Windows 独占**：底层仍通过 `schtasks` 实现 OS 级触发
4. **管道兼容**：定时任务最终调用 `pipeline_orchestrator.py init`，不能修改其接口
5. **MCP 安全**：新增的 MCP tools 必须遵循 Reasonix 桌面端的安全沙箱限制

## 6. 成功指标

| 指标 | 目标 |
|------|------|
| Reasonix 桌面端可创建定时任务 | ✅ 用户可在聊天中通过 MCP tool 完成 |
| 功能覆盖度 | ✅ 覆盖 CRUD + 手动触发 + 日志查看 |
| 已有功能零破坏 | ✅ CLI 和 schtasks 集成不改动 |
