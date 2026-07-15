---
name: portfolio-manager-rl
description: "组合经理RL：动态仓位优化、RL训练"
runAs: inline
profiles: balanced
cost: medium
---

# portfolio-manager-rl

## 使命

组合经理RL：动态仓位优化、RL训练

## 第 0 步：准备工作

1. 读取任务输入和方案
2. 确认数据和工具就绪

## 第 1 步：核心工作

按量化管线要求完成本角色工作。

## 质量门

- 无未来函数泄露
- 回测含实盘约束

## 不做

- 不跳过质量门
- 不修改其他角色产出

## 角色完成

**步骤 1** → queue_next_prompt: phase="dev-done_task-done"
**步骤 2** → 输出完成框
