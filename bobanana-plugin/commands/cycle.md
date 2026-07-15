---
description: 🔄 启动多轮循环副管线 — 每轮2 session(架构师→全栈开发)，默认3轮，prompt锁定。
argument-hint: "<目标>"
---

用户启动 cycle 副管线。目标：$ARGUMENTS

## 执行

`read_skill("cycle")` 加载 cycle 管线 skill，按 cycle 流程执行。

### 要点

- 每轮 2 session：架构师(设计) → 全栈开发(实现)
- 默认 3 轮，可自定义
- prompt 格式锁定
- 不经过 Boss
- 不影响 Bobanana 主管线
