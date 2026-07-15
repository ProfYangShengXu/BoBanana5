---
name: cycle
description: 🔄 [Delivery/Balanced] 多轮循环副管线 — 每轮2 session(架构师→全栈开发)，默认3轮，prompt锁定。
runAs: inline
profiles: delivery, balanced
cost: high
---

# cycle — 多轮循环副管线

**语言指令：推理用英文，回复用中文。**

## 核心机制

每轮 = **2 个 session**，只用架构师和全栈开发两个角色，prompt 固定格式。

```
Round 1/3:
  Session A: 架构师(plan)     → 设计方案/任务拆解 → queue_next_prompt
  Session B: 全栈开发(exec)   → 按方案实现 → queue_next_prompt
—— —— —— —— —— —— —— —— —— —— —— —— —— ——
Round 2/3: (同上)
Round 3/3: (同上) → signal_done
```

**不经过 Boss**，**不影响主线 Bobanana 管线**。

## Session A — 架构师（plan）

### Prompt 模板（锁定不变）

```
[ROUND] X/Y
[GOAL] <用户原始目标>
[PHASE] plan
[MISSION] 设计本轮实现方案
[PREV] 上一轮完成了什么（首轮无）
[NEXT] 全栈开发按此方案实现
```

### 执行

1. 读上一轮的 `[DONE]` 了解进度
2. 设计本轮要做的功能模块
3. 输出设计文档到 `docs/cycle/`
4. **不写代码**

→ `queue_next_prompt(phase="cycle-exec")`

## Session B — 全栈开发（exec）

### Prompt 模板（锁定不变）

```
[ROUND] X/Y
[GOAL] <用户原始目标>
[PHASE] exec
[PLAN] 架构师的设计方案
[MISSION] 按方案实现代码
[PREV] 上一轮完成进度
```

### 执行

1. 按架构师方案实现
2. 不重构不属于本轮的代码
3. 完成编译/验证

→ 检查轮数：
- `round < max_rounds` → `queue_next_prompt(phase="cycle-plan")`，下一轮
- `round >= max_rounds` → `signal_done(summary="...")`

## 轮数控制

```bash
# cycle 副管线（默认3轮，可自定义）
python pipeline_orchestrator.py init "目标" --rounds 3
python pipeline_orchestrator.py init "目标" -r 5

# 主管线单独控制（默认1轮）
/bb 目标
```

cycle 命令写死 `--rounds 3` 作为默认值。

## 铁律

1. 每轮 Session A 只设计不写代码
2. 每轮 Session B 只实现不修改架构
3. prompt 格式锁定，不加额外分析文字
4. 不影响 Bobanana 主管线状态
5. 跨轮优先级保持一致
