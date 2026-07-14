---
name: bobanana
description: 🍌 Bobanana 5.0 — 管线入口。进入 Boss 角色启动贪心状态机管线。
runAs: inline
profiles: delivery, balanced
cost: low
arguments: '<目标>'
---

# Bobanana 5.0 — 管线启动入口

用户想用 Bobanana 5.0 完成目标：$ARGUMENTS

## 执行路径

### 第 1 步：进入 Boss 角色

`read_file` 读取 `skills/roles/boss/SKILL.md`，然后立即开始扮演 Boss。

### 第 2 步：扮演 Boss

按 Boss 角色卡的要求执行本 session 的工作。

### 第 3 步：完成角色

调用 `mcp__cycle-bridge__queue_next_prompt` 保存状态。

如果 `mcp__cycle-bridge__queue_next_prompt` 不可用：

```bash
python -c "import pipeline_orchestrator as po; po.init_pipeline('$ARGUMENTS'); po.advance_pipeline('boss-done')"
```

然后输出完成框。

## 约束

- 每个 session 只跑一个角色
- 不一次性完成全流程
- 当前无活跃角色时自动进入 Boss
