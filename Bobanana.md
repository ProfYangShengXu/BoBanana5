# Bobanana.md — 核心工程大纲

> 每次调用 docs / cycle / loop 时，agent 必须读此文件并践行以下原则。

## 1. 禁止面向结果编程

不准用关键词匹配、正则、模式识别替代真正的逻辑处理。遇到问题必须查清根因，从对应层面根本解决，而不是修表面现象。修 bug 前先写一个暴露该 bug 的测试，再修代码。不准写"看起来对了"但经不起推敲的逻辑。

## 2. 架构设计原则（9 条）

高内聚低耦合 · 单一职责 · 开放封闭 · KISS · DRY · 迪米特法则 · 依赖倒置 · 关注点分离 · YAGNI

## 3. 风险与质量意识（7 个维度）

技术债（妥协要标记 TODO） · 回滚（可逆吗 API 兼容吗） · 灰度（feature flag?） · 熔断降级（超时/重试/降级） · 监控告警（有日志吗） · 容错冗余（单点在哪） · 安全（输入消毒/密钥不从代码来）

## 4. 代码规范

- **不随便重构**：不重构没问题的代码。重构必须有明确收益
- **不写未接线死函数**：定义了就必须有调用方，否则删掉
- **不自己造轮子**：实现前先搜 GitHub / 标准库 / 项目已有代码
- **改完即清理**：删未用 import、死变量、残留 TODO
- **PRD 一致性**：有 PRD 时实现必须一致，不一致时停下来问用户

## 5. 全局管线约定

### 5.1 统一流转入口
所有角色通过 `state-machine.yaml` + `pipeline_orchestrator.py` 流转，不绕过机制自行调用。每 session 只跑一个角色，通过 queue_next_prompt 交接。禁止：直接写代码完成任务不通过管线角色分配。

### 5.2 CL 唯一出口
任何管线最终必须经过 `client-gate` 评分 ≥ 9 才能到达 `__terminal__`。评分 < 9 自动打回给最近的 OP 角色。没有其他节点可以直达终点。

### 5.3 角色卡驱动
每张角色卡必须含 `example_state_machine` + `use_case` 字段，HR 招聘时自动生成。角色池由 `role_card_registry.py` 统一管理，不手工注册。

### 5.4 先复用再新建
新功能前先 `grep` / `glob` 搜索项目内已有代码，确认无复用可能后再 `web_fetch` 搜 GitHub / 生态（PyPI / NPM / Maven）找成熟方案。不自研已有开源实现的基础组件。

### 5.5 不并行造轮子
不开发功能重复的工具。如果项目内已有类似实现（如 MCP 客户端、状态机引擎、角色注册表），直接引用扩展，不另起炉灶。统一标准：同一类问题只用一套方案。

### 5.6 SessionStart 检测
`hooks/check_mcp.py` 在 SessionStart 时检测 `.reasonix/cycle/next_prompt.txt`。有内容 → 自动调用 `pipeline_orchestrator continue` 推进管线。无内容 → 正常进入 `/bb` 新管线。

### 5.7 提示词注入
所有管线目标自动追加「默认目标：通过 CL 终审(score≥9)」。由 `pipeline_orchestrator.init_pipeline()` 执行注入，各角色无需手动添加。

### 5.8 外部工具集（Adaption Kitsets）
领域特定任务优先引用外部适配集中的角色卡和工具。架构师/Boss 遍历角色卡库时额外扫描 `skills/kitsets/` 或配置的 `kitset_paths`，若用户目标匹配某 kitset 领域（如游戏开发→Godot-kitset），则在状态机中插入该 kitset 提供的角色卡节点。Kitset 角色卡遵循标准 `role-card.schema.yaml` 格式，可含 `kitset_name` 字段标记来源。优先使用 kitset 工具而非自研。
- Boss/架构师 Step 1 遍历角色卡库时增加 `skills/kitsets/` 扫描
- 检测用户目标关键词匹配 kitset 领域标签
- 匹配时在状态机中插入 kitset 角色卡作为执行节点
- 不匹配时使用默认角色池 < 该约定无需修改代码，由角色执行时遵循>

### 5.9 多文件变更规则
需求涉及多个文件时，状态机中**禁止使用 fullstack-dev 角色**，必须同时包含 `test-dev-engineer` + `security-engineer` 两个角色。理由：多文件变更意味着跨模块影响，必须有测试覆盖和安全审查兜底，不能由单一角色全包。单文件变更不受此限制。

### 5.10 贪心状态机规则（G1-G5）

所有状态机编排必须遵守以下 5 条贪心规则，倾向拆分更多角色而非压缩管线：

| 规则 | 名称 | 强制要求 |
|------|------|---------|
| **G1** | 领域拆分贪心 | Architect 识别目标涉及 N 个领域，就在状态机中插入 N 个专业开发角色，不准合并成一个 fullstack-dev。默认拆分：后端 / 前端 / 数据库 |
| **G2** | 计划评审贪心 | 每个 OP 节点产出方案后必须先经 code-reviewer 审查再分配执行。不准"边写边想"。开发角色完成后也必须经 CR 才能进入下一节点 |
| **G3** | 测试不合并 | 只要变更 > 1 个模块，必须插入 test-dev-engineer 作为独立节点，不给开发角色兼职。禁止"顺手测一下代替" |
| **G4** | 安全不省略 | 任何涉及数据处理 / 网络 / 用户输入的项目，security-engineer 强制插入。不准"项目小就不做安全" |
| **G5** | 验收不跳过 | Architect 在 CL 之前必须做一次完整终验，检查所有模块的产出物完整性。不准"直接交给 CL 过" |

**默认状态机模板**（`state-machine.yaml` v15）已按以上规则编排：Boss → Architect(自审) → 后端→CR→数据库→CR→前端→CR → 集成测试 → 全量测试 → 安全审计 → 文档整理 → Architect终验 → CL → 出口。

### 模板选择指南

`docs/examples/` 下预置了多级模板，按项目复杂度选择：

| 模板 | 角色数 | 适用场景 | 文件 |
|------|--------|---------|------|
| 🐣 **quick-fix** | 6 | 紧急 bug 修复（含 chaos + AI 测试验证） | `docs/examples/state-machine-quick-fix.yaml` |
| 🏗️ **standard** | 14 | 中小型项目、标准 Web/API（**默认推荐**） | `state-machine.yaml` |
| 🛡️ **chaos-ready** | 14 | 高可靠系统，chaos + AI 测试深度协同 | `docs/examples/state-machine-chaos-ready.yaml` |
| 🤖 **ai-native** | 14 | AI/LLM 原生项目，全链路 AI 质量验证 | `docs/examples/state-machine-ai-native.yaml` |
| 🏙️ **fullstack-web** | 22 | 大型 Web 全栈 | `docs/examples/state-machine-fullstack-web.yaml` |
| 🌐 **fullstack-chaos** | 26 | 全栈 + chaos + AI 测试（最大规模） | `docs/examples/state-machine-fullstack-chaos.yaml` |
| 🏗️ **microservices** | 18 | 微服务架构、分布式系统 | `docs/examples/state-machine-microservices.yaml` |
| 🎮 **game-dev** | 14 | 游戏开发、AI NPC、服务器韧性 | `docs/examples/state-machine-game-dev.yaml` |
| 📊 **data-science** | 12 | 数据分析、ML 训练、推荐系统 | `docs/examples/state-machine-data-science.yaml` |
| 🔒 **security-audit** | 9 | 安全审计、渗透测试、合规检查 | `docs/examples/state-machine-security-audit.yaml` |

**chaos-engineer + ai-test-strategist 协同模式**：在所有含此二角色的模板中，它们构成"质量双核"——
1. chaos-engineer 先注入故障（网络中断、服务宕机、高延迟）验证系统韧性
2. ai-test-strategist 随后验证 AI 模型在故障下的行为是否符合预期
3. 任一发现退化，打回对应角色修复，修复后重新从该环节执行

**切换模板**：将目标模板内容覆盖 `state-machine.yaml` 即可。架构师在执行时会自动验证节点是否与角色卡库匹配。

**Boss 自动选择逻辑**：Boss 读取用户目标后，根据关键词匹配推荐模板：
- 含"修复"/"热修"/"bug"/"hotfix" → 推荐 quick-fix
- 含"数据"/"分析"/"模型"/"训练"/"ML"/"AI" → 推荐 data-science
- 含"安全"/"审计"/"渗透" → 推荐 security-audit
- 含"前端"/"后端"/"全栈"/"Web" → 根据团队规模推荐 standard 或 fullstack-web
- 其他 → 默认 standard
