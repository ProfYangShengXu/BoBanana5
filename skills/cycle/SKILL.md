---
name: cycle
description: 🔄 [Delivery/Balanced] 多轮循环副管线 — 每轮架构师→全栈开发，自动连续运行直到max_rounds完成。
runAs: inline
profiles: delivery, balanced
cost: high
---

# cycle — 多轮循环副管线

**语言指令：推理用英文，回复用中文。**

## 核心机制

一轮 = **架构师设计 → 全栈开发实现**。所有轮次在**一个 session 内连续运行**，中间不停顿、不等待用户操作。

```
Round 1/3: 架构师(设计) → 全栈开发(实现) → 自动进入第 2 轮
Round 2/3: 架构师(设计) → 全栈开发(实现) → 自动进入第 3 轮
Round 3/3: 架构师(设计) → 全栈开发(实现) → signal_done ✅
```

**不经过 Boss**，**不影响主线 Bobanana 管线**。

## 执行流程（一次性完成所有轮次）

### 第 1 步：确定轮数

从 prompt 读取 `[ROUND]` 确定当前轮数。如无则从 round=1 开始。

默认 `max_rounds=3`，可通过 `--rounds N` 自定义。

### 第 2 步：架构师工作（plan）

```
[ROUND] X/Y
[GOAL] <用户原始目标>
[MISSION] 设计本轮实现方案
[PREV] 上一轮完成了什么（首轮无）
```

1. 读上一轮的 `[DONE]` 了解进度（首轮无）
2. 设计本轮要做的功能模块
3. 输出设计文档到 `docs/cycle/`
4. **不写代码**
5. 记录完成进度

### 第 3 步：全栈开发工作（exec）

```
[ROUND] X/Y
[GOAL] <用户原始目标>
[PLAN] 架构师的设计方案
[MISSION] 按方案实现代码
```

1. 按架构师方案实现
2. 不重构不属于本轮范围的代码
3. 编译/验证通过

### 第 4 步：判断是否还有下一轮

- `round < max_rounds` → **立刻回到第 2 步**，round+1，继续下一轮（不 queue_next_prompt，不结束 session）
- `round >= max_rounds` → `signal_done(summary="...")`，结束循环

## 关键差异（对比 Boss 管线）

| | 主管线 (/bb) | cycle 副管线 |
|---|---|---|
| 轮次 | 每轮单独 session | **同一 session 内连续执行** |
| 角色 | Boss→架构师→...→CL | 架构师↔全栈开发（来回切换） |
| 用户操作 | 每 session 后需手动继续 | **自动运行，无需干预** |
| prompt | 各角色 SKILL.md 灵活 | **锁定格式** |

## 轮数控制

```bash
# 默认 3 轮，可自定义
/cycle 目标
/cycle 目标 --rounds 5
/cycle 目标 -r 1  # 单轮
```

## 铁律

1. 架构师只设计不写代码
2. 全栈开发只实现不修改架构设计
3. **一轮结束后立即进入下一轮，不 queue_next_prompt，不等待用户**
4. 不影响 Bobanana 主管线状态
5. 所有轮次结束后才 signal_done
