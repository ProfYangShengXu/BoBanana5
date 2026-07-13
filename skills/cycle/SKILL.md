---
name: cycle
description: 🔄 [Delivery/Balanced] 多 subagent 并行循环（跨 session）：每批 task 并行执行，每 session 一批，queue_next_prompt 续跑。
runAs: inline
profiles: delivery, balanced
cost: high
---

# cycle — 多 subagent 并行循环（跨 session）

**语言指令：推理用英文，回复用中文。**

**先读** `~/.reasonix/Bobanana.md`（不存在则跳过），践行其中的原则。

有 PRD（`docs/design/*.html`）时必须先 `read_file` 读 PRD，严格对齐。不一致时停下来问用户。

---

## 核心机制：跨 session 循环

> **每个 session 只执行一批并行任务。做完调 `queue_next_prompt`，`reasonix cycle` 拉起下一批。**
>
> 不自循环。不做多批。做完一批 → queue_next_prompt → 等下一轮。

```
Session N（一批）:
  task("模块A") ─┐
  task("模块B") ─┤ 并行 → 验证 → queue_next_prompt(phase="batch-N")
  task("模块C") ─┘
                        │
   reasonix cycle 检测   │
                        ▼
Session N+1（下一批）:
  task("模块D") ─┐
  task("模块E") ─┤ 并行 → 验证 → queue_next_prompt(phase="batch-N+1")
                 ┘
                        │
                     ... 直到 signal_done
```

## 本轮要做的事

1. **读 prompt 恢复上下文**：上一轮 queue_next_prompt 中的 prompt 包含剩余任务清单、已完成项。
2. **读 PRD**（如有）：提取当前批要做的任务
3. **并行执行**：用 `task` 派多个子 agent 并行干活
4. **验证**：子 agent 返回后审阅
5. **汇报**：输出 **「N/? + ≤20 字简报」**
6. **决定下一步**：
   - 全部完成 → `signal_done(summary=...)`
   - 还有任务 → `queue_next_prompt(phase="batch-N", prompt=...)` 续跑

## 铁律

1. **准并行不准串行**：独立子任务必须并行派发
2. **PRD 对齐**：有 PRD 时不走样，不一致必须停问用户
