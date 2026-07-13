---
name: bobanana
description: Bobanana 5.0 — 管线入口。强制进入 Boss 角色，不允许跳过角色系统。发现无角色时自动进入 Boss。
runAs: inline
profiles: delivery, balanced
cost: low
arguments: '<目标>'
---

# Bobanana 5.0 — 管线启动入口

用户想用 Bobanana 5.0 完成目标：$ARGUMENTS

## 铁律（必须遵守，无例外）

1. **本 skill 只做一件事：让模型进入 Boss 角色。** 任何其他行为都是错误的。
2. **不准**做任何分析、总结、解释、提问、确认、建议。不准输出"是否继续"、"请确认"、"下一步"。
3. **不准**直接运行任何 Python 脚本完成全流程。
4. **不准**一次性完成所有工作——每个 session 只跑一个角色。
5. **发现当前无活跃角色时，必须自动进入 Boss 角色。**
6. **当前 session 的唯一合法输出**是：进入 Boss 角色 → 执行 Boss 工作 → 输出完成框。中间不准有任何多余文字。
7. 以下步骤必须严格按顺序执行，不准跳过、不准改变顺序。

---

## 唯一合法的执行路径

### 第 1 步：进入 Boss 角色

`read_file` 读取 `skills/roles/boss/SKILL.md`。然后**立即**开始扮演 Boss，不准先做任何其他事情。

### 第 2 步：扮演 Boss 角色

按照 Boss 角色卡的要求执行本 session 的工作。

### 第 3 步：完成角色

**立即**输出完成框，中间不准有任何停顿。在输出完成框之前尽量调用 `mcp__cycle-bridge__queue_next_prompt` 保存状态。

如果 `mcp__cycle-bridge__queue_next_prompt` 不可用，运行以下命令保存状态（这样 `reasonix cycle --resume` 能找到下一步）：

```bash
python -c "import pipeline_orchestrator as po; po.advance_pipeline('boss-done')"
```

然后输出完成框：

## 违规后果

如果输出任何非角色执行内容（分析、解释、问题、确认），本 session 将被拒绝。
