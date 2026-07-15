# 📈 Quant Kitset — 量化交易 Adaption Kitset for Bobanana 5.0

量化交易的 [Bobanana 5.0](https://github.com/ProfYangShengXu/BoBanana5) Adaption Kitset。  
7 张专业角色卡 + 6 个工具接口 + 量化状态机模板。

> **前身**: 架构文档见 `docs/product/quant-kitset-architecture.md`  
> **参考**: [bobanana5-embedded-kitset](https://github.com/ProfYangShengXu/bobanana5-embedded-kitset)

---

## 🎯 设计目标

AI 驱动的量化研究闭环：角色卡决策 + 状态机编排 + 工具执行 + 绩效反馈迭代。

- **方向 1**: AI 量化研究管线（策略生成 → 数据 → 因子 → 模型 → 回测 → 执行）
- **方向 2**: 强化学习组合优化（RL agent 做动态仓位管理）

## 📋 角色卡（7 张）

| 方向 | 角色 | 标签 |
|------|------|------|
| 👑 **架构** | quant-architect | **OP** |
| 🔬 **研究** | strategy-researcher | 执行 |
| 📊 **数据** | data-engineer | 执行 |
| 📈 **因子** | quant-analyst | 执行 |
| 🤖 **模型** | ml-engineer | 执行 |
| 🛡️ **风控** | risk-manager | 执行 |
| 💼 **组合** | portfolio-manager-rl | 执行 |

## 🧰 工具集

| 工具 | 功能 |
|------|------|
| crawler | 新闻/研报爬虫 |
| akshare | AKShare 数据接口 |
| factor-engine | 因子计算引擎 |
| ml-trainer | ML 模型训练器 |
| backtest-engine | 事件驱动回测引擎 |
| rl-env | RL 训练环境 |

## 📊 状态机

```
quant-architect → strategy-researcher → data-engineer → risk-manager(数据质量)
  → quant-analyst → ml-engineer → risk-manager(过拟合) → portfolio-manager-rl
  → quant-architect(终验) → client-gate(sharpe≥0.8)
```

## 🚀 接入

```bash
cd path/to/BoBanana5/kitsets
git clone <this-repo>.git quant
```
