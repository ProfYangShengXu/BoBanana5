# 管线信息下放到工作区 — 需求文档

## 目标

将 Bobanana 5.0 的管线状态存储从全局配置迁移到工作区级别，为未来多管线并行执行做准备。

## 现状问题

当前管线状态存储路径：

| 数据 | 路径 | 说明 |
|------|------|------|
| 管线元数据 | `.reasonix/pipelines/pl-<timestamp>.json` | 单个 JSON 文件，每管线一个文件 |
| 状态机运行态 | `.reasonix/state/machine_state.json` | **全局单例**，不支持并行 |
| Cycle 工作流 | `.reasonix/cycle/state.json` | 全局单例，不支持并行 |
| 下一提示 | `.reasonix/cycle/next_prompt.txt` | 全局单例 |

关键问题：
1. `state_machine_engine.py` 中 `state_dir` 默认硬编码为 `".reasonix/state"`，无法区分工作区
2. `pipeline_orchestrator.py` 中 `PIPELINE_DIR`/`CYCLE_DIR`/`STATE_MACHINE_DIR` 均硬编码为 `.reasonix/` 下固定路径
3. `has_pending_pipeline()` 仅扫描单一目录，不支持并行管线识别
4. cycle-bridge MCP 工具（`cycle_bridge.py`）同样将状态存储在固定路径
5. 同一个 Reasonix 实例切换工作区时，管线状态混淆

## 需求

### R1 — 工作区感知的管线存储

```
.reasonix/pipelines/<workspace>/<pipeline_id>/state.json
.reasonix/pipelines/<workspace>/<pipeline_id>/machine_state.json
.reasonix/pipelines/<workspace>/<pipeline_id>/cycle_state.json
.reasonix/pipelines/<workspace>/<pipeline_id>/next_prompt.txt
```

- 每个管线拥有独立子目录，包含自身全部状态
- `workspace` 由项目根目录名称推导（或配置指定）
- 切换工作区不影响其他工作区的管线

### R2 — 支持并行多管线

- 允许在同一工作区内同时运行多条管线（例如：Quant Kitset 管线 + 主开发管线）
- `list_pipelines()` 返回所有工作区的所有管线
- 每条管线用 `<workspace>/<pipeline_id>` 唯一标识
- 推进管线时需指定 `workspace_id`（默认当前工作区）

### R3 — 向后兼容

- 旧版 `pipeline.json` 格式自动识别并迁移到新版目录结构
- `state_machine_engine.StateMachineRuntime` 构造函数增加 `workspace_id` 参数
- cycle-bridge MCP 工具的 `get_cycle_state`/`queue_next_prompt` 增加 workspace 参数

### R4 — CLI 接口更新

```bash
# 初始化（指定 workspace，可选）
python pipeline_orchestrator.py init --workspace quant "策略研究管线"

# 列出所有管线（含 workspace）
python pipeline_orchestrator.py list --all

# 推进指定工作区的管线
python pipeline_orchestrator.py advance --workspace quant <phase>
```

## 非功能性要求

- 不破坏现有的 cycle-bridge MCP 协议（`queue_next_prompt`/`get_cycle_state`）
- 迁移过程中旧目录下的管线数据不丢失
- 默认 worksapce 兼容：不指定 workspace 时使用 `.reasonix/` 根目录（向后兼容）

## 范围

- **修改文件**：`pipeline_orchestrator.py`、`state_machine_engine.py`、`handoff_ticket.py`
- **可能涉及**：`cycle_bridge.py`（MCP 工具）、`mcp_server.py`（MCP 协议入口）
- **不修改**：角色卡、状态机定义文件、现有管线逻辑
