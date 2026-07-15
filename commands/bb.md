---
name: bb
description: "🍌 Bobanana 5.0 快捷指令 — 清空状态→进入Boss→启动管线"
argument-hint: "<目标>"
---

直接启动 Bobanana 5.0 主力管线。参数：$ARGUMENTS

## 执行

### 第 0 步：清空残留状态（确保稳定）

```bash
rm -rf .reasonix/state .reasonix/pipelines .reasonix/cycle
```

**必须先做这步。** 旧管线残留会导致新管线无法启动。

### 第 1 步：进入 Boss 角色

`read_skill("bobanana")` 加载 Bobanana 入口 skill，按 skill 要求进入 Boss 角色。

### 第 2 步：启动管线

Boss → 架构师 → 按状态机推进。

**全流程不准询问确认、不准输出分析性文字、不准停顿。直接开干。**
