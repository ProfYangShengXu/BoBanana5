<div align="center">
  <h1>🍌 Bobanana 5.0</h1>
  </b> Meta Agent 跨session的长编排引擎 · 基于可编程状态机 + 可插拔skill角色卡系统</p>
  <p>
    <a href="https://reasonix.io"><img src="https://img.shields.io/badge/Reasonix-0.54%2B-blue?style=flat-square" alt="Reasonix"></a>
    <a href="https://github.com/ProfYangShengXu/BoBanana5/blob/main/LICENSE"><img src="https://img.shields.io/github/license/ProfYangShengXu/BoBanana5?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/状态-活跃-brightgreen?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/角色卡-59%20张-7c3aed?style=flat-square" alt="Cards">
    <img src="https://img.shields.io/badge/测试-177%2B%20个-success?style=flat-square" alt="Tests">
  </p>
  <br>
</div>

---

## 📋 目录

- [这是什么？](#-这是什么)
- [快速上手](#-快速上手)
- [设计理念](#-设计理念)
- [架构概览](#-架构概览)
- [外部工具集](#-外部工具集)
- [相关文档](#-相关文档)

---

## 🤔 这是什么

**Bobanana 5.0 是一个 </b> Meta Agent 跨session的长编排引擎 · 基于可编程状态机 + 可插拔skill角色卡系统</p>

靠 Reasonix agent 通过特定的 skill 角色卡跨 session 地编排每一 session 使用的角色和子任务，以优质的完成长线开发任务。角色卡库已扩展至 **59 张专业角色卡**，覆盖前端/后端/数据库/测试/安全/运维/AI 等全技术栈。

```
Bobanana 5.0 核心（调度+状态机+质量门）         = 操作系统内核
Adaption Kitsets（领域角色卡 + 工具集）           = 驱动程序
外部工具生态（引擎/CLI/SDK）                      = 硬件设备
```

> **核心编排层（本项目）只适用通用领域开发，不涵盖特定方向的开发** 角色定义、工具调用、质检标准全部由外部的 Adaption Kitsets 提供。换领域 = 换适配集，内核不改一行代码。

### 两层架构

| 层 | 技术栈 | 职责 |
|---|--------|------|
| 🧠 **编排核心** | Python + Reasonix | 按状态机调度 Agent 角色、维护上下文、质量门 基础角色卡|
| 📦 **Adaption Kitsets** | YAML + Markdown | 特殊领域角色卡、工具实现、预设状态机模板 |

### 角色标签体系（59 张角色卡）

角色卡库目前包含 **59 张专业角色卡**，按标签分类：

| 标签 | 含义 | 代表角色 | 行为 |
|------|------|---------|------|
| 🔵 **OP** | Orchestration 编排者 | 架构师 / Boss | 动态编写 state-machine.yaml，可修改管线拓扑 |
| 🔴 **CL** | Client Gate 甲方终审 | client-gate | **唯一出口**，隔离 subagent 全量审查并打分 |
| 🟢 **HR** | 招聘专员 | hr-recruiter | 仅响应 OP 紧急招聘，研究职业后生成角色卡 |
| ⚪ **执行** | 专业开发者 | 51 张 | 前端/后端/数据库/测试/安全/运维/AI 各领域专业角色 |

**CL 是管线唯一终结出口。** 所有技术角色完成后，CL 在全新隔离的 subagent 中审查全项目并打分 1-10。≥ 9 分通过，< 9 分打回给 OP 角色修复。

---

## 🚀 快速上手

### 安装

安装有两种方式，选一个：

<details open>
<summary><b>🖥️ 方式一：从 Reasonix 桌面端安装（推荐，无需命令行）</b></summary>

1. 打开 Reasonix 桌面端，点右下角 **⚙️ 设置** → **插件管理**

2. 点 **安装插件** → **选择本地文件夹**

3. 浏览到本仓库目录，选中 `bobanana-plugin` 文件夹

4. Reasonix 自动识别插件配置，弹出确认框，点 **确认安装**

5. 回到聊天界面，输入：

```text
（reasonix 目标模式）/bb 帮我做一个记账软件
```

🎉 完成。

> 💡 本仓库已自带 `bobanana-plugin/` 文件夹，内含完整的 Reasonix 插件配置。无需下载 ZIP，直接指向该文件夹即可。
> 如果 Reasonix 桌面端没有插件管理界面，用方式二。
</details>

<details>
<summary><b>⌨️ 方式二：命令行安装</b></summary>

```bash
# 1. 克隆或下载本仓库
git clone https://github.com/ProfYangShengXu/BoBanana5.git
#    或者 ZIP: GitHub → Code → Download ZIP 后解压

# 2. 打开终端，进入项目目录
cd BoBanana5

# 3. 运行安装脚本（自动注册到 Reasonix）
install.bat
```

看到 `=== Done ===` 就装好了。装一次 = 所有项目通用。
</details>

### 启动

```bash
reasonix chat
```

### 开始第一个任务

```text
（reasonix目标模式）/bb 帮我做一个记账软件
```

AI 自动推进：设计 → 写代码 → 测试 → 审查

### 还不确定做什么？

先用 `/docs` 做产品调研，确认想法再动手。

```text
/docs 项目: 宠物社交APP, type: all
```

#### /docs 能做什么？

`/docs` 是一个**产品设计文档生成器**——它只回答 **WHAT**（做什么）和 **WHY**（为什么做），不碰 **HOW**（怎么实现）。

当你有一个产品想法但不确定方向时，`/docs` 帮你完成完整的**前期调研与产品定义**：

| 功能 | 说明 |
|------|------|
| 🔍 **竞争格局** | 搜索至少 5 个竞品，分析定位/定价/优劣势/空白机会 |
| 👥 **用户画像** | 构建 3-5 个真实感用户画像，含场景/痛点/诉求 |
| 📈 **市场趋势** | 行业规模、增长率、政策/技术趋势、融资动态 |
| 🛠️ **功能参考** | 同类产品功能矩阵，行业最佳实践 |
| 🎯 **MVP 定义** | Must-have / Nice-to-have / 明确不做什么 |
| 📊 **SWOT 分析** | 优劣势 + 机会威胁，数据驱动的风险评估 |

#### 产出物

```
docs/product/<项目名>-product-prd.html    ← 产品设计文档（给人读的）
docs/product/<项目名>-product-prd.yaml    ← 结构化产品定义（机器可读，后续/bb直接用）
```

每个数据和结论都标注来源 URL，不凭空编造。

#### 示例

```text
/docs 项目: AI 笔记助手, type: competitor,user
/docs 项目: 在线教育平台, type: all
/docs 项目: 开发者工具, type: competitor,market,tech
```

> 💡 产出的 YAML 文件后续会被 pipeline 的架构师角色自动读取，转换成技术 PRD 和开发任务。可以先 `/docs` 后 `/bb` 是最佳实践。
> 
### 想要自动化创建角色卡片？
使用 `/hr` 调用网络搜索职业研究，自动化生成标准职业角色卡片并注册到管线。

支持快速引用模式直接生成角色卡：
```bash
python hr_recruitment.py quick "<角色名>" "<准则文件路径>"
```

### 查看全部角色卡
```bash
python skills/roles/role_card_registry.py list
```
---

## 💡 设计理念

### 🧩 为什么核心编排层是领域无关的？

传统 AI 管线如bobanana4把角色和流程硬编码在一起——"架构→开发→测试→评审"固定不变，换领域就得重写。Bobanana 5.0 将编排逻辑抽象为独立核心层：

```
传统管线：角色 × 流程 × 领域 = 紧耦合 ❌
Bobanana 5.0：编排核心 + Adaption Kitsets（角色+流程+领域）= 松耦合 ✅
```

核心编排层只做三件事：
1. **按状态机调度 Agent 角色**——读 YAML 配置驱动流转
2. **维护上下文一致性**——结构化交接工单传递产出、决策、假设
3. **确保质量门通过**——CL 终审打分 + 打回机制

领域知识全部外置到 **Adaption Kitsets**（独立 Git 仓库），每个 kitset 含角色卡、工具实现、状态机模板、质检标准。

### ⚡ 为什么每个角色一个 session？

DeepSeek 模型有**自动前缀缓存**：如果两次请求的前缀完全相同，缓存命中，成本降 50-80%，速度快 2-3 倍。

```
❌ 一个 session 跑到底：每轮前缀都在变 → 缓存永远失效 → 又慢又贵
✅ 每角色一个 session：session 内前缀不变 → 缓存全程命中 → 又快又便宜
```

所以管线不是"故意复杂化"，而是**为了利用缓存机制省钱提速**。

### 🤝 为什么仿真人类团队？

| 现实团队 | Bobanana 管线 |
|---------|---------------|
| 产品经理 → 架构师 → 前端 → 后端 → 测试 → 安全 → 验收 | Boss → 架构师 → 开发 → 测试 → 安全 → CL 终审 |

各司其职的好处：
- **专注**：每个角色只关心自己的领域
- **质量门**：每阶段有明确产出和检查标准
- **可替换**：角色卡可替换升级，不影响上下游
- **可审计**：谁做了什么一目了然

### 🚪 为什么 CL 是唯一出口？

技术性评估（测试、评判、挑刺）和"业务方接受"是两回事。CL 用全新隔离的 subagent 审查全项目，不受历史上下文污染：

```
≥ 9 分 → 通过 🎉
< 9 分 → 打回架构师修复，附带审查报告
```

模仿现实中的**外部审计**——审计员不知道内部过程，只看结果。



---

## 🏗 架构概览

### 目录结构

```
BoBanana5/
├── README.md              ← 本文件
├── Bobanana.md            ← 核心工程大纲（agent 必读）
├── reasonix.toml          ← Reasonix 引擎配置（由 install.bat 写入）
├── state-machine.yaml     ← 当前管线状态机
│
├── bobanana-plugin/       ← 🧩 Reasonix 插件配置（桌面端安装时选择此文件夹）
│
├── skills/roles/          ← 🎴 角色卡系统（核心）
│   ├── .registry.yaml     ← 角色注册表（59 张）
│   ├── role-card.schema.yaml
│   ├── role_card_registry.py
│   └── <角色名>/           ← 每角色：role-card.yaml + SKILL.md + standards-brief.yaml
│
├── docs/examples/         ← 📐 11 个预置状态机模板（quick-fix → super-cr）
├── kitsets/               ← 🧩 外部工具集
├── hooks/                 ← 🔌 Reasonix 插件 hook
├── docs/                  ← 📄 文档产出
├── tests/                 ← 🧪 四层测试（177+）
└── *.py                   ← 核心 Python 模块
```

### 管线流转

```
SessionStart → hook 检测 next_prompt.txt
  ├─ 有内容 → 自动 advance → 下一角色
  ├─ 空     → /bb <目标> → Boss → 新管线
  └─ 说"继续" → 同上

每个角色:
  进入 → 读上下文 → 干活 → 写产出 → queue_next_prompt → ✅ 完成框
```

### 状态机示例（v15 贪心模板 — 默认推荐）

```
Boss → Architect → backend-dev → code-reviewer → frontend-dev
    → code-reviewer → test-dev-engineer → security-engineer
    → tech-writer → Architect(终验) → CL(终审)
```

> 还有 10 个可选模板见 `docs/examples/`，覆盖快速修复 / 全栈 / 数据科学 / 安全审计 / 游戏开发 / 超级CR 等场景。

### CL 终审 — 六维度审查

| 维度 | 检查项 |
|------|--------|
| 📖 可读性 | 命名、注释、函数长度、风格一致 |
| 📦 可维护性 | 耦合度、测试覆盖、文档、死代码 |
| 🔧 可扩展性 | 开闭原则、接口先行、配置驱动 |
| ⚡ 可靠性 | 异常处理、边界情况、超时重试 |
| 🔒 安全性 | 输入消毒、凭据管理、依赖漏洞 |
| 🧹 整洁度 | TODO/FIXME、DRY、无用 import |

### 📦 插件注册表结构

```json
{
  "name": "bobanana5",
  "skills": "skills",
  "commands": ["commands"],
  "hooks": { "SessionStart": ["python hooks/check_mcp.py"] },
  "mcpServers": {
    "bobanana5": {
      "type": "stdio",
      "command": "python mcp_server.py",
      "tier": "background"
    }
  }
}
```

安装时 `install.bat` 自动将此配置写入 Reasonix 的 `reasonix.toml`。

---

## 🧩 外部工具集

`kitsets/` 下每个子目录是一个独立工具集，有自己的角色卡和工具：

```
skills/kitsets/godot/
  ├── role-card.yaml       # 含 kitset_name: godot
  ├── SKILL.md             # 领域准则
  └── tools/               # 工具实现
```

Boss/架构师遍历角色卡时**自动扫描** `skills/kitsets/`，匹配用户目标领域标签后插入对应角色卡，无需手动配置。

---

## 📄 相关文档

| 文档 | 说明 |
|------|------|
| [`Bobanana.md`](Bobanana.md) | 核心工程大纲，所有 agent 必读 |
| [`docs/product/`](docs/product/) | 产品设计文档（HTML + YAML）|
| [`docs/prd/`](docs/prd/) | 技术方案 PRD |
| [`docs/adr/`](docs/adr/) | 架构决策记录 |
| [`docs/sm/`](docs/sm/) | 状态机说明 |
| [`docs/test/`](docs/test/) | 测试报告 |
| [`docs/changelog/`](docs/changelog/) | 变更日志 |
| [`docs/security/`](docs/security/) | 安全审查 |
| [`skills/roles/`](skills/roles/) | 59 张角色卡（前端/后端/数据库/测试/安全/运维/AI）|

---

<div align="center">
  <sub>Built on <a href="https://reasonix.io">Reasonix</a> · MIT License</sub>
  <br>
  <sub>🍌 Bobanana 5.0 — 你说话，AI 干活</sub>
</div>
