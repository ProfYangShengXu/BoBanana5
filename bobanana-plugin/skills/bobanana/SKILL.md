---
name: bobanana
description: 🍌 Bobanana 5.0 — 管线入口。清空状态→进入Boss→启动管线。
runAs: inline
profiles: delivery, balanced
cost: low
arguments: '<目标>'
---

# Bobanana 5.0 — 管线启动入口

用户想用 Bobanana 5.0 完成目标：$ARGUMENTS

## 第 0 步：清空残留状态

```bash
rm -rf .reasonix/state .reasonix/pipelines .reasonix/cycle
```

不管有没有残留，先清干净。这是保证稳定性的第一道防线。

## 第 1 步：进入 Boss 角色

`read_skill("boss")` 加载 Boss 角色卡，然后立即开始扮演 Boss。

## 第 2 步：扮演 Boss

按 Boss 角色卡的要求完成工作。

## 第 3 步：完成角色

调用 `mcp__cycle-bridge__queue_next_prompt` 保存状态。

如果不可用：
```bash
python -c "import pipeline_orchestrator as po; po.init_pipeline('$ARGUMENTS'); po.advance_pipeline('boss-done')"
```

然后输出完成框。

## 约束

- 每个 session 只跑一个角色
- 不一次性完成全流程
- 不分析、不解释、不确认——直接干活
