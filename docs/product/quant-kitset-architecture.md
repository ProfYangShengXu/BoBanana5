# Quant Kitset — 量化交易 Adaption Kitset for Bobanana 5.0

量化交易的 Bobanana 5.0 Adaption Kitset。7 张专业角色卡 + 6 个工具接口 + 量化状态机模板。

> **母公司**: [BoBanana5](https://github.com/ProfYangShengXu/BoBanana5)
> **参考**: [bobanana5-embedded-kitset](https://github.com/ProfYangShengXu/bobanana5-embedded-kitset) — 嵌入式 kitset 的格式与规范

---

## 设计目标

构建 AI 驱动的量化研究闭环：**角色卡决策 + 状态机编排 + 工具执行 + 绩效反馈迭代**。同时覆盖两个方向：

- **方向 1** — AI 量化研究管线（策略生成 → 数据 → 因子 → 模型 → 回测 → 执行）
- **方向 3** — 强化学习组合优化（RL agent 做动态仓位管理）

---

## 目录结构

```
kitsets/quant/
├── README.md
├── reasonix-plugin.json           # Kitset 元数据
├── state-machine-quant.yaml       # 量化状态机模板
│
├── roles/                         # 7 张角色卡
│   ├── .registry.yaml
│   ├── quant-architect/           # OP: 量化架构师
│   │   ├── role-card.yaml
│   │   ├── SKILL.md
│   │   └── standards-brief.yaml
│   ├── strategy-researcher/       # 策略研究员
│   ├── quant-analyst/             # 量化分析师
│   ├── data-engineer/             # 数据工程师
│   ├── ml-engineer/               # ML工程师
│   ├── risk-manager/              # 风控官
│   └── portfolio-manager-rl/      # 组合经理(RL)
│
└── tools/                         # 6 个工具接口
    ├── tools.py                   # Python 统一入口
    ├── crawler/                   # 新闻/研报爬虫
    │   └── crawler.py
    ├── akshare/                   # AKShare/Tushare 数据接口
    │   └── data_fetcher.py
    ├── factor-engine/             # 因子计算引擎
    │   └── factor_calc.py
    ├── ml-trainer/                # 模型训练器
    │   └── trainer.py
    ├── backtest-engine/           # 回测引擎
    │   └── backtest.py
    └── rl-env/                    # RL 训练环境
        └── env.py
```

---

## reasonix-plugin.json

```json
{
  "name": "bobanana5-quant-kitset",
  "version": "1.0.0",
  "description": "量化交易 Adaption Kitset — 策略研究/因子挖掘/ML训练/回测/RL优化",
  "kitset_name": "quant",
  "kitset_domains": ["quant", "trading", "stock", "backtest", "factor",
                     "finance", "a-share", "rl-trading", "algo-trading",
                     "portfolio", "risk-management"],
  "entry_role": "quant-architect",
  "skills": "roles",
  "commands": []
}
```

**匹配关键词**（Boss 启动时自动扫描，命中 ≥2 个即切换控制权给 `quant-architect`）:
`quant`, `trading`, `stock`, `backtest`, `factor`, `finance`, `a-share`, `rl`, `portfolio`, `量化`, `回测`, `选股`, `因子`, `交易策略`

---

## 角色卡（7 张）

### 总览

| 方向 | 角色 | ID | 说明 |
|------|------|----|------|
| **架构** | 量化架构师 | `quant-architect` | OP角色：系统架构设计、工具链编排、全流程质量把控 |
| **研究** | 策略研究员 | `strategy-researcher` | 交易idea生成、策略逻辑设计、文献调研 |
| **数据** | 数据工程师 | `data-engineer` | 行情/财务/另类数据采集、清洗、存储 |
| **因子** | 量化分析师 | `quant-analyst` | 因子挖掘、IC/IR分析、因子组合构建 |
| **模型** | ML工程师 | `ml-engineer` | 预测模型训练、特征筛选、模型评估与调参 |
| **风控** | 风控官 | `risk-manager` | 风险评估、止损设计、数据泄露检测、合规审查 |
| **组合** | 组合经理RL | `portfolio-manager-rl` | 动态仓位优化、RL训练、执行成本建模 |

### 角色卡格式

每张角色卡包含三个文件，以 `quant-architect` 为例：

#### role-card.yaml

```yaml
name: quant-architect
description: '量化架构师(OP)：策略管线架构设计、工具链编排、全流程质量把控'
input_contract:
  - name: task_input
    type: object
    required: true
    description: 任务输入（交易目标/市场范围/约束条件）
output_contract:
  - name: pipeline_output
    type: object
    description: 完整的策略管线产出（信号/持仓/绩效报告）
quality_gates:
  - id: QUANT-Q1
    check: 数据无未来函数泄露
    desc: 所有因子和特征工程确保时间点对齐，禁止使用未来数据
    layer: U
  - id: QUANT-Q2
    check: 回测与实盘一致性
    desc: 回测框架包含滑点、手续费、涨跌停限制等实盘约束
    layer: I
  - id: QUANT-Q3
    check: 过拟合检测
    desc: 策略在样本外/交叉验证集上的表现不得显著弱于样本内
    layer: U
  - id: QUANT-Q4
    check: 风险指标达标
    desc: 最大回撤、夏普比率、换手率等满足预设阈值
    layer: U
standards_file: standards-brief.yaml
tags: ['OP']
is_op_role: true
use_case: '适合策略管线架构设计、多角色编排、全流程质量评审'
```

#### SKILL.md（核心 prompt）

```markdown
---
name: quant-architect
description: "量化架构师(OP)：策略管线架构设计、工具链编排、全流程质量把控"
runAs: inline
profiles: delivery, balanced
cost: medium
---

# quant-architect

**语言指令：推理用英文，回复用中文。**

## 使命

作为量化架构师，负责统筹整个策略研究与执行管线。你需要：
1. 理解用户交易目标，拆解为可执行的子任务
2. 按状态机编排各角色卡的执行顺序
3. 在每个质量门进行评审，决定是否放行或打回

## 第 0 步：准备工作

1. 确认交易目标（市场范围、频率、资金规模、风险偏好）
2. 确认数据源可用性（AKShare/Tushare token、爬虫合规范围）
3. 检查工具链依赖是否就绪（Python 环境、ML框架、回测引擎）

## 第 1 步：策略方案设计

1. 与策略研究员协作，明确策略逻辑（信号规则/预测目标/持仓周期）
2. 确定所需数据范围（行情周期、财务指标、另类数据）
3. 制定因子列表和特征工程方案
4. 选择合适的模型类型（线性/树模型/深度学习/RL）

## 第 2 步：管线编排

按状态机模板触发各角色：
- `strategy-researcher` → 生成交易idea
- `data-engineer` → 采集并清洗数据
- `quant-analyst` → 因子计算与验证
- `ml-engineer` → 预测模型训练
- `risk-manager` → 风控审查（贯穿全流程）
- `portfolio-manager-rl` → RL组合优化

## 第 3 步：质量评审

每个阶段完成后检查质量门：
- QUANT-Q1: 数据无未来函数泄露
- QUANT-Q2: 回测包含实盘约束
- QUANT-Q3: 样本外表现不显著弱于样本内
- QUANT-Q4: 风险指标达标

不通过则打回对应角色重做。

## 不做

- 不直接操作具体数据和模型（交给对应角色）
- 不跳过质量门直接放行
- 不满仓赌单票（风控约束必须生效）

## 角色完成

**步骤 1** → queue_next_prompt: phase="arch-done"
**步骤 2** → 输出策略管线报告：信号逻辑、因子列表、回测绩效、风险评估
```

---

## 工具集

### 统一入口 `tools/tools.py`

```python
#!/usr/bin/env python3
"""
Bobanana 5.0 — 量化工具集 CLI 入口

用法:
    python tools.py crawler --source eastmoney --keyword "业绩预增"
    python tools.py akshare --fetch daily --symbol 000001 --start 2024-01-01
    python tools.py factor --calc momentum --symbols 000001,000002
    python tools.py ml --train --model lightgbm --features factor_df.pkl
    python tools.py backtest --strategy config.yaml --start 2024-01-01
    python tools.py rl --train --env portfolio-v0 --episodes 1000
"""
```

### 工具详情

| 工具 | 命令 | 功能 |
|------|------|------|
| 爬虫 | `crawler` | 东方财富/巨潮资讯/雪球等平台的新闻、公告、研报爬取；支持关键词筛选、时间范围过滤、正文提取 |
| 数据接口 | `akshare` | AKShare/Tushare/Baostock 封装；日线/分钟线/财务数据/资金流向/龙虎榜；自动缓存本地 parquet |
| 因子引擎 | `factor` | 量价因子（动量/波动率/换手率/均线偏离）/基本面因子/行业因子；IC分析、分层回测 |
| ML引擎 | `ml` | LightGBM/XGBoost/CatBoost 训练；交叉验证；特征重要性；样本外预测；模型持久化 |
| 回测引擎 | `backtest` | 事件驱动回测；支持滑点/手续费/A股涨跌停/T+1；输出绩效指标、交易记录、权益曲线 |
| RL环境 | `rl` | Gymnasium 兼容环境；状态=市场特征+持仓+预测信号；动作=调仓权重；奖励=夏普/CALMAR; 支持 Stable-Baselines3 |

### 工具接口规范

每个工具暴露统一的函数签名，供角色卡 SKILL.md 中直接调用：

```python
# crawler
def fetch_news(keyword: str, start_date: str, end_date: str) -> pd.DataFrame
def fetch_research_reports(stock_code: str, limit: int = 50) -> pd.DataFrame

# akshare
def get_daily(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame
def get_financials(symbol: str, report_type: str = "年报") -> pd.DataFrame
def get_money_flow(symbol: str, days: int = 5) -> pd.DataFrame

# factor
def calc_factor(symbols: list, factor_name: str, params: dict) -> pd.DataFrame
def factor_ic(factor_df: pd.DataFrame, forward_returns: pd.Series) -> dict

# ml
def train_model(features: pd.DataFrame, labels: pd.Series, config: dict) -> tuple
def predict(model, features: pd.DataFrame) -> np.ndarray

# backtest
def run_backtest(strategy_config: dict, data: pd.DataFrame) -> dict
def plot_equity_curve(backtest_result: dict) -> str  # returns path to chart

# rl
def create_env(portfolio_config: dict) -> gym.Env
def train_rl_agent(env: gym.Env, algo: str = "PPO", episodes: int = 1000) -> tuple
```

---

## 状态机模板 `state-machine-quant.yaml`

```yaml
# 量化交易状态机 v1-quant
# 适用场景：策略研究、因子挖掘、ML训练、回测、RL优化
# 角色数：7 张量化专业角色卡
# OP角色：quant-architect

version: 1
entry_point: "quant-architect"
max_loops: 30

nodes:
  # OP编排层
  - id: "quant-architect"         tags: ["OP"]      is_op_role: true

  # 研究链
  - id: "strategy-researcher"     tags: []
  - id: "data-engineer"           tags: []
  - id: "quant-analyst"           tags: []
  - id: "ml-engineer"             tags: []

  # 风控（并行贯穿）
  - id: "risk-manager"            tags: []

  # 组合优化
  - id: "portfolio-manager-rl"    tags: []

  # 出口
  - id: "client-gate"             tags: ["CL"]      is_exit: true

edges:
  # 架构师 → 策略研究（启动）
  - from: "quant-architect"       to: "strategy-researcher"   phase: "arch-start"

  # 策略研究 → 数据采集
  - from: "strategy-researcher"   to: "data-engineer"        phase: "strategy-done"

  # 数据采集 → 风控初审（数据质量检查）
  - from: "data-engineer"         to: "risk-manager"          phase: "data-ready"
  - from: "risk-manager"          to: "quant-analyst"         phase: "data-clean"

  # 因子分析 → 模型训练
  - from: "quant-analyst"         to: "ml-engineer"           phase: "factor-ready"

  # 模型训练 → 风控复审（过拟合检测）
  - from: "ml-engineer"           to: "risk-manager"          phase: "model-ready"
  - from: "risk-manager"          to: "portfolio-manager-rl"  phase: "model-clean"

  # RL优化 → 架构师终验
  - from: "portfolio-manager-rl"  to: "quant-architect"       phase: "rl-done"

  # 架构师终验 → 出口
  - from: "quant-architect"       to: "client-gate"           phase: "arch-gate-pass"

  # 打回路径
  - from: "risk-manager"          to: "data-engineer"         phase: "data-contaminated"
  - from: "risk-manager"          to: "ml-engineer"           phase: "model-overfit"
  - from: "quant-architect"       to: "strategy-researcher"   phase: "arch-gate-fail"

  # CL 出口
  - from: "client-gate"           to: "__terminal__"          phase: "cl-pass"
    condition: {field: sharpe, operator: ">=", value: 0.8}
  - from: "client-gate"           to: "quant-architect"       phase: "cl-fail"
    condition: {field: sharpe, operator: "<", value: 0.8}
```

---

## 数据流全景

```
用户输入交易目标
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              quant-architect (OP)                     │
│         "A股中线动量策略，月频调仓，沪深300成分股"      │
└──────┬───────────────────────────────────────────────┘
       │ phase: arch-start
       ▼
┌─────────────────┐    策略逻辑文档
│ strategy-       │────────────────────┐
│ researcher      │  "20日动量>0 + 成交 │
│                 │   量放大 + 基本面过滤" │
└─────────────────┘                    │
       │ phase: strategy-done          │
       ▼                               │
┌─────────────────┐                    │
│ data-engineer   │──► AKShare拉取     │
│                 │    ｜日线/财务     │
│                 │    ｜缓存parquet   │
└────────┬────────┘                    │
         │ phase: data-ready           │
         ▼                             │
┌─────────────────┐                    │
│ risk-manager    │──► 检查:           │
│ (数据质量)      │    ｜时间对齐      │
│                 │    ｜无未来泄露    │
│                 │    ｜缺失值处理    │
└────────┬────────┘                    │
         │ pass                        │
         ▼                             │
┌─────────────────┐                    │
│ quant-analyst   │──► 因子计算:       │
│                 │    ｜动量/波动率   │
│                 │    ｜IC分析        │
│                 │    ｜分层回测      │
└────────┬────────┘                    │
         │ phase: factor-ready         │
         ▼                             │
┌─────────────────┐                    │
│ ml-engineer     │──► LightGBM训练:   │
│                 │    ｜交叉验证      │
│                 │    ｜特征重要性    │
│                 │    ｜样本外预测    │
└────────┬────────┘                    │
         │ phase: model-ready          │
         ▼                             │
┌─────────────────┐                    │
│ risk-manager    │──► 检查:           │
│ (过拟合检测)    │    ｜样本外IC      │
│                 │    ｜参数稳定性    │
└────────┬────────┘                    │
         │ pass                        │
         ▼                             │
┌─────────────────┐                    │
│ portfolio-      │──► PPO训练:        │
│ manager-rl      │    ｜Gym环境       │
│                 │    ｜仓位优化      │
│                 │    ｜回测验证      │
└────────┬────────┘                    │
         │ phase: rl-done              │
         ▼                             │
┌─────────────────┐                    │
│ quant-architect │──► 终验:          │
│ (终审)          │    ｜绩效达标?     │
│                 │    ｜逻辑合理?     │
└────────┬────────┘                    │
         │ sharpe >= 0.8              │
         ▼                            │
┌─────────────────┐                   │
│ client-gate     │                   │
│ (输出报告)      │                   │
└────────┬────────┘                   │
         │                            │
         ▼                            │
    ┌──────────┐                      │
    │ 绩效反馈 │◄─────────────────────┘
    │ 闭环迭代 │   下一轮优化策略参数
    └──────────┘
```

---

## 角色卡协作模式

### 串行链（主流程）
```
strategy-researcher → data-engineer → quant-analyst → ml-engineer → portfolio-manager-rl
```
每个角色产出一份交接文档给下一个角色，状态机按 phase 驱动流转。

### 并行审查（risk-manager）
`risk-manager` 不参与主链，而是在两个关键节点被触发：
1. **数据就绪后** — 检测未来函数泄露、缺失值、异常值
2. **模型训练后** — 检测过拟合、参数敏感度、样本外衰减

任一审查不通过，打回上游角色。

### 闭环迭代
一次完整运行结束后，绩效结果反馈给 `quant-architect`：
- 夏普比率达标 → 输出最终报告
- 夏普不达标 → 打回 `strategy-researcher` 调整策略参数，重新走管线

---

## 第一步：最小闭环 MVP

从 7 张角色卡中抽取最小子集验证架构：

**角色卡**: `quant-architect` + `risk-manager` (2张)
**工具**: `akshare` + `backtest-engine` (2个)
**策略**: 双均线突破（不需要ML/RL）

```
quant-architect → data-engineer(akshare) → risk-manager → backtest → report
```

跑通后逐步加入 `strategy-researcher`（LLM生成idea）、`quant-analyst`（因子）、`ml-engineer`（模型）、`portfolio-manager-rl`（RL）。

---

## 接入 Bobanana 5.0

```bash
# 克隆到 BoBanana5 的 kitsets/ 目录下
cd path/to/BoBanana5/kitsets
git clone <this-repo>.git quant
```

Boss 启动时扫描 `kitsets/quant/`，通过 `reasonix-plugin.json` 中的 `kitset_domains` 匹配用户目标关键词。命中 ≥2 个量化相关关键词时，控制权切换给 `quant-architect`。

---

## 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 数据源 | AKShare (主) + Tushare (备) | 免费、A股覆盖全、Python原生 |
| 数据存储 | pandas + parquet | 列存压缩、读写快、生态好 |
| 因子计算 | pandas + numpy + alphalens | 因子分析标准库 |
| ML模型 | LightGBM + XGBoost | 表格数据SOTA、训练快、可解释 |
| 深度学习 | PyTorch | 灵活、RL支持好 |
| RL框架 | Gymnasium + Stable-Baselines3 | 标准RL生态 |
| 回测引擎 | 自建事件驱动（参考 backtrader 设计） | 完全可控、可嵌入管线 |
| 可视化 | matplotlib + plotly | 静态报告 + 交互图表 |

---

## 环境要求

- Python 3.12+
- AKShare (`pip install akshare`)
- pandas, numpy, scikit-learn
- LightGBM, XGBoost, CatBoost
- PyTorch (可选，RL训练需要)
- Gymnasium + Stable-Baselines3 (可选，RL训练需要)
- matplotlib, plotly
- Git
