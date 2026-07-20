"""批量更新游戏工作室角色卡 standards-brief.yaml — 填入行业研究数据"""

import os

ROLES_DIR = "skills/roles"

# 每个角色的研究数据映射
STUDIES = {
    # ── 策划类 ──
    "system-designer": ("系统策划", "经济/社交/养成/战斗系统设计", "设计",
       "MDA Framework, Core Loop Design, Systems Design Thinking, Resource Model, Top-down Planning",
       ["系统架构图（Miro/Visio）", "功能规格文档（输入/输出/边界/异常）", "资源循环图", "系统交互矩阵", "养成线配置表", "UI/UX 流程图"],
       ["System Bloat：加无意义系统", "边界条件遗漏", "系统间张力不足", "忽视新人体验"]),
    "level-designer": ("关卡策划", "关卡/地形/谜题/流程设计", "设计",
       "Blockout→Playtest→Polish, Paper Level Design, Difficulty Curve, Flow Channel, Golden Path",
       ["Bubble Diagram（泡泡图）", "Level Blockout 白盒", "Greybox Map 灰盒", "Intensity Arc 图", "Encounter 配置表", "Puzzle Logic 图"],
       ["Blockout 阶段 playtest 不够", "难度曲线设计不合理", "玩家 flow 被阻断", "谜题解法收束过窄"]),
    "narrative-designer": ("剧情策划", "主线/支线/世界观/对话设计", "设计",
       "Narrative Systems vs Content, Gameplay First, Ludonarrative Harmony, Arc Diagram, Branching Narrative",
       ["世界观圣经（World Bible）", "主线剧情大纲（三幕结构）", "任务流程表", "对话树（Twine/YAML）", "角色设定卡", "Intensity Arc"],
       ["Ludonarrative Dissonance: 玩法与故事冲突", "玩家动机与故事目标不一致", "跳过对话后目标不清", "分支覆盖率不均衡"]),
    "combat-designer": ("战斗策划", "动作/AI/手感/连招设计", "设计",
       "Core Combat Loop, Enemy Archetype System, Game Feel Tuning, Telegraphing, Input Canceling, Combo Tree",
       ["战斗系统设计文档", "技能配置表", "敌人设计文档", "AI Behavior Tree", "Game Feel 参数表", "连招树", "战斗 Prototype"],
       ["输入反馈延迟 >100ms", "玩家看不懂敌人攻击预告", "敌人类型单一", "Combo 深度不足/过深"]),
    "numerical-designer": ("数值策划", "战斗/经济/平衡/概率设计", "设计",
       "Spreadsheet Modeling, Economy Flow Design, Inflation Control, Difficulty Curve Modeling, Dominant Strategy Detection",
       ["数值模型（Excel）", "属性配置表", "经济循环图", "难度曲线表", "模拟运行结果", "平衡性调整日志"],
       ["Dominant Strategy: 存在最优解", "经济恶性通胀", "Edge Cases 未覆盖", "数值自洽性不足"]),

    # ── 程序类 ──
    "client-programmer": ("客户端程序", "Gameplay/UI/网络/渲染", "开发",
       "Component-based Architecture, Server Authority, MVVM for UI, Draw Call Budget, ECS Pattern",
       ["Gameplay 功能系统", "UI/HUD 交互逻辑", "客户端网络同步代码", "输入映射与绑定", "本地化系统", "发布构建脚本"],
       ["帧预算超 16.67ms(60fps)", "输入延迟处理不当", "网络同步状态不一致", "内存泄漏未检测"]),
    "server-programmer": ("服务端程序", "后端/数据库/网关/防外挂", "开发",
       "Microservices Architecture, ACID + Eventual Consistency, Server Authority, Rate Limiting, Anti-Cheat",
       ["游戏服务器框架", "匹配系统", "账号认证", "数据持久化方案", "日志监控(ELK/Grafana)", "Docker/K8s CI/CD"],
       ["SLA < 99.9%", "安全漏洞(OWASP Top 10)", "数据库事务隔离级别不当", "反作弊策略不足"]),
    "engine-programmer": ("引擎程序", "渲染/物理/工具链/内存", "开发",
       "Render Graph Architecture, Job System Parallelism, Memory Pooling, Asset Streaming, Editor Tooling",
       ["渲染管线实现", "物理系统集成", "内存管理系统", "编辑器工具", "资产流式加载系统"],
       ["内存碎片化", "物理碰撞检测性能不足", "资产管线缺失导致迭代慢", "线程安全问题"]),
    "graphics-programmer": ("图形程序", "Shader/光照/后处理/GPU", "开发",
       "PBR Pipeline, Deferred/Forward Rendering, Compute Shaders, GPU Optimization, Temporal Anti-aliasing",
       ["Shader 实现", "光照系统（动态/烘焙）", "后处理管线", "GPU Profiling 报告", "渲染特性实现"],
       ["移动端 GPU 不兼容", "Draw Call 超过预算", "后处理性能超支", "光照 Bake 时间过长"]),
    "tech-artist": ("技术美术(TA)", "流程/渲染/角色/工具开发", "开发",
       "Pipeline Bridge, Shader Support, Tool Development, Performance Budget, Automated Workflow",
       ["美术管线工具", "Shader 库/材质库", "自动化脚本", "性能监控工具", "资源验证脚本"],
       ["工具解决的是假痛点", "工具太复杂没人用", "文档缺失", "资产管线中断"]),
    "ai-programmer": ("AI程序", "行为树/寻路/机器学习", "开发",
       "Behavior Trees, Utility AI, A* Pathfinding, NavMesh, ML-Agents Integration",
       ["AI Behavior Tree", "寻路系统（NavMesh）", "AI 配置数据", "ML 训练管线", "AI 调试工具"],
       ["AI 行为可读性差", "NavMesh 配置不当", "寻路性能瓶颈（大量单位）", "Utility AI 权重难调"]),

    # ── 美术类 ──
    "concept-artist": ("原画设计师", "角色/场景/道具/概念设计", "美术",
       "Silhouette, Color Palette, Shape Language, Iterative Sketching, Mood Boarding",
       ["角色概念设计稿", "场景概念设计", "道具设计稿", "配色方案", "风格定调指南"],
       ["与 3D 建模沟通断层", "缺乏多视角设计", "概念过于艺术化无法实现", "风格不一致"]),
    "3d-modeler": ("3D建模师", "角色/场景/硬表面/生物建模", "美术",
       "PBR Workflow, High-poly→Low-poly, Retopology, UV Mapping, Texture Baking",
       ["高模（ZBrush/Maya）", "低模+UV", "PBR 材质(Substance)", "LOD 模型", "碰撞体模型"],
       ["面数超预算", "UV 拉伸", "材质表现不一致", "LOD 切换不自然"]),
    "animator": ("动画师", "角色/面部/技术/动捕处理", "美术",
       "12 Principles of Animation, FK/IK Rigging, Blend Tree, Motion Capture Cleanup, Retargeting",
       ["角色动画集", "面部动画 BlendShape", "动捕数据清理文件", "动画状态机配置", "Retargeting 结果"],
       ["动捕数据清理不干净", "Blend Tree 过渡不自然", "面部表情与语音不同步", "动画文件命名混乱"]),
    "vfx-artist": ("特效师(VFX)", "技能/环境/后期/粒子特效", "美术",
       "Particle Systems, Shader-based VFX, Timing/Sequencing, Performance Budgeting, Houdini Integration",
       ["技能特效", "环境特效（天气/破坏）", "后期特效（Post-process）", "粒子系统配置", "VFX 性能报告"],
       ["特效性能超预算", "粒子数过多导致帧率下降", "特效与游戏风格不匹配", "Shader 兼容性问题"]),
    "ui-artist": ("UI美术", "图标/界面/动效/交互原型", "美术",
       "Figma→Engine Workflow, Responsive Layout, Motion Design, Interaction Prototyping, Iconography",
       ["UI 界面设计稿", "图标集", "动效设计原型", "交互原型(Figma)", "UI 样式指南"],
       ["不同分辨率下 UI 错位", "动效与游戏帧率不匹配", "图标风格不统一", "可访问性不足"]),
    "environment-artist": ("场景美术", "地表/植被/灯光/氛围", "美术",
       "World Composition, Modular Building, Lighting/Lightmass, Vegetation Placement, Atmosphere Design",
       ["场景模型/地表", "植被系统", "光照/烘焙结果", "氛围设定", "场景性能报告"],
       ["场景物体过多 LOD 不当", "光照 Bake 结果不自然", "植被放置破坏可玩性", "场景氛围与剧情不匹配"]),

    # ── 音频类 ──
    "sound-designer": ("音效设计师", "拟音/声音/交互音频", "音频",
       "Foley Recording, Sound Layering, Dynamic Mixing, Interactive Audio, Wwise/FMOD Integration",
       ["音效库（Foley/环境/UI）", "交互音频配置", "混音配置文件", "声音集成文档"],
       ["音效风格与游戏不匹配", "交互音频响应不及时", "动态混音未配置", "文件命名/管径混乱"]),
    "composer": ("作曲家", "作曲/编曲/音乐总监", "音频",
       "Leitmotif, Dynamic Music System, Horizontal/Vertical Re-orchestration, Adaptive Music",
       ["主题旋律（Main Theme）", "环境音乐集", "战斗/UI 音乐 clip", "音乐系统集成指南"],
       ["音乐与游戏节奏不匹配", "循环点处理不当", "文件格式/码率不当", "动态音乐系统复杂度过高"]),
    "voice-director": ("配音导演", "配音导演/录音/编辑", "音频",
       "Voice Casting, Direction Session, ADR Recording, Lip Sync, Dialogue Integration",
       ["配音演员试音结果", "录音文件（干声+处理）", "唇形同步数据", "对话集成文件"],
       ["角色声音与形象不符", "录音环境噪音未清理", "口型同步误差大", "配音文件命名/版本混乱"]),
    "audio-programmer": ("音频程序", "Wwise/FMOD/音频引擎/空间音频", "音频",
       "Middleware Integration, Spatial Audio, Audio Engine Optimization, Dynamic Mixing System, Parameter Control",
       ["Wwise/FMOD 集成代码", "空间音频系统", "音频性能报告", "音频参数控制接口"],
       ["音频内存占用过高", "空间音频效果不理想", "音频加载延迟导致卡顿", "音频管线中断"]),

    # ── 测试类 ──
    "functional-tester": ("功能测试", "用例设计/回归测试/缺陷跟踪/探索性测试", "测试",
       "等价类划分, 边界值分析, 决策表测试, 状态转换测试, 探索性测试(SBT)",
       ["测试用例（前置/步骤/预期）", "Bug 报告（复现步骤/严重度）", "测试摘要报告", "探索性测试日志", "Badcase 文档"],
       ["重现步骤不清晰", "边界条件遗漏", "探索性测试章程不够聚焦", "Bug triage 延迟"]),
    "automation-tester": ("自动化测试", "脚本开发/CI集成/性能基准", "测试",
       "POM, Keyword-Driven, Data-Driven, CI Pipeline, Performance Benchmarking",
       ["自动化测试脚本", "CI 流水线配置", "测试执行报告", "性能基准报告", "覆盖率报告"],
       ["假阳性率 >5%", "脚本可维护性差(函数>30行)", "性能基准偏差 >5%", "CI 流水线不稳定"]),
    "compatibility-tester": ("兼容性测试", "多设备/多系统/硬件配置", "测试",
       "Device Fragmentation Matrix, OS Version Strategy, Hardware Config Grading, Cert Checklist",
       ["兼容性测试矩阵", "兼容性 Bug 报告", "平台认证清单", "硬件配置建议报告", "屏幕适配报告"],
       ["目标设备覆盖率 <95%", "平台认证一次通过率 <90%", "最低配置帧率 <30FPS", "OOM 测试不充分"]),
    "test-manager": ("测试管理", "测试计划/风险评估/流程规范", "测试",
       "V-Model, Risk-Based Testing, Shift-Left Testing, Agile/Scrum Testing, ISTQB CTAL-TM",
       ["测试策略文档", "测试计划", "风险评估报告", "测试指标仪表盘", "签审报告"],
       ["缺陷逃逸率 >5%", "测试与开发配比不当", "风险评估遗漏", "退出标准未严格执行"]),
}


def gen_standards_brief(name, title, desc, role_type, methodology, outputs, pitfalls):
    method_lines = "\n".join(f"      - {m.strip()}" for m in methodology.split(",")) if methodology else "      - 行业通用实践"
    output_lines = "\n".join(f"  - {o}" for o in outputs)
    pitfall_lines = "\n".join(f"  - {p}" for p in pitfalls)
    tag = {"设计": "design", "开发": "dev", "美术": "art", "音频": "audio", "测试": "test"}.get(role_type, "general")

    return f"""# {name} 职业准则简报（补齐研究）
# 生成日期: 2026-07-19
# 来源: 游戏行业标准实践 + 结构化研究笔记

role: {name}
title: {title}
description: {desc}

## A — 工作准则
methodology:
{method_lines}
best_practices:
  - 每个设计决策有需求依据
  - 产出物的可验证性
  - 版本控制和变更记录
  - 定期同行评审
standards:
  - 设计文档完整性：覆盖全部需求
  - 产出物可验证性：其他角色可独立验证
  - 版本标记：每次变更有版本记录
  - 审查通过后才算完成

## B — 工作内容
outputs:
{output_lines}
quality_standards:
  - 通过同级审查（Peer Review）
  - 无残留 TODO/FIXME
  - 产出物路径和格式在交接工单中明确
  - 版本标记可追溯

## C — 工具与方法
tools:
  - Godot 4.x 引擎
  - Markdown / YAML / Excel 文档工具
  - Git 版本控制 + Git LFS
  - 部门专用工具（引擎编辑器/设计软件）

## D — 常见坑与风险
common_mistakes:
{pitfall_lines}
anti_patterns:
  - 跳过评审直接交付
  - 设计无需求依据
  - 版本控制缺失
"""


def main():
    for name, (title, desc, role_type, methodology, outputs, pitfalls) in STUDIES.items():
        role_dir = os.path.join(ROLES_DIR, name)
        os.makedirs(role_dir, exist_ok=True)

        sb = gen_standards_brief(name, title, desc, role_type, methodology, outputs, pitfalls)
        with open(os.path.join(role_dir, "standards-brief.yaml"), "w", encoding="utf-8") as f:
            f.write(sb)
        print(f"  ✅ {name:25s} standards-brief.yaml updated")

    print(f"\nDone! {len(STUDIES)} standards-brief.yaml files updated")


if __name__ == "__main__":
    main()
