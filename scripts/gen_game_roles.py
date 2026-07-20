"""批量生成游戏工作室角色卡 — 快速引用模式"""

import os, sys, json, yaml, shutil

ROLES_DIR = "skills/roles"

ROLES = [
    # OP
    ("game-architect", "游戏架构师(OP)", "游戏开发管线的架构师和总设计师：技术选型、管线搭建、工具链编排、质量把关"),
    # 策划 Design (5)
    ("system-designer", "系统策划", "经济/社交/养成/战斗系统设计：系统框架设计、功能文档、数值架构"),
    ("level-designer", "关卡策划", "关卡/地形/谜题/流程设计：关卡布局、难度曲线、可玩性验证"),
    ("narrative-designer", "剧情策划", "主线/支线/世界观/对话设计：故事框架、角色设定、对话树"),
    ("combat-designer", "战斗策划", "动作/AI/手感/连招设计：战斗机制、技能设计、手感调优"),
    ("numerical-designer", "数值策划", "战斗/经济/平衡/概率设计：数值模型、资源循环、平衡性验证"),
    # 程序 Engineering (6)
    ("client-programmer", "客户端程序", "Gameplay/UI/网络/渲染：游戏逻辑、界面开发、客户端网络、渲染管线"),
    ("server-programmer", "服务端程序", "后端/数据库/网关/防外挂：游戏服务器、数据持久化、安全策略"),
    ("engine-programmer", "引擎程序", "渲染/物理/工具链/内存：引擎核心、物理系统、编辑器工具、内存优化"),
    ("graphics-programmer", "图形程序", "Shader/光照/后处理/GPU：渲染特效、光照系统、后期管线、GPU优化"),
    ("tech-artist", "技术美术(TA)", "流程/渲染/角色/工具开发：美术管线、Shader支持、工具开发、性能优化"),
    ("ai-programmer", "AI程序", "行为树/寻路/机器学习：角色AI、寻路系统、数据驱动行为、ML集成"),
    # 美术 Art (6)
    ("concept-artist", "原画设计师", "角色/场景/道具/概念设计：视觉概念、风格定调、设计稿、配色方案"),
    ("3d-modeler", "3D建模师", "角色/场景/硬表面/生物建模：高模低模、UV展开、材质烘焙、PBR流程"),
    ("animator", "动画师", "角色/面部/技术/动捕处理：骨骼绑定、关键帧动画、表情动画、动作捕捉"),
    ("vfx-artist", "特效师(VFX)", "技能/环境/后期/粒子特效：粒子系统、Shader特效、时序动画、性能预算"),
    ("ui-artist", "UI美术", "图标/界面/动效/交互原型：UI设计、图标绘制、动效设计、交互原型"),
    ("environment-artist", "场景美术", "地表/植被/灯光/氛围：场景搭建、光照烘焙、氛围营造、性能优化"),
    # 音频 Audio (4)
    ("sound-designer", "音效设计师", "拟音/声音设计/交互音频：音效制作、声音整合、交互音频系统"),
    ("composer", "作曲家", "作曲/编曲/音乐总监：主题旋律、氛围音乐、音乐系统集成"),
    ("voice-director", "配音导演", "配音导演/录音/编辑：角色配音、录音指导、音频编辑"),
    ("audio-programmer", "音频程序", "Wwise/FMOD集成/音频引擎/空间音频：音频中间件、引擎集成、3D音频"),
    # 测试 QA (4)
    ("functional-tester", "功能测试", "用例设计/回归测试/缺陷跟踪/探索性测试：测试用例、Bug验证、质量报告"),
    ("automation-tester", "自动化测试", "脚本开发/CI集成/性能基准：自动化框架、持续集成、性能基准测试"),
    ("compatibility-tester", "兼容性测试", "多设备/多系统/硬件配置：设备兼容性、系统兼容性、硬件配置测试"),
    ("test-manager", "测试管理", "测试计划/风险评估/流程规范：测试策略、资源规划、流程优化"),
]

def gen_role_card(name, desc, tags):
    return yaml.dump({
        "name": name,
        "description": desc,
        "tags": tags,
        "input_contract": [{"name": "handoff_context", "type": "object",
                           "description": "交接工单：上一步角色的产出物和注意事项", "required": True}],
        "output_contract": [{"name": f"{name}_deliverables", "type": "object[]",
                            "description": desc.split("：")[-1] if "：" in desc else desc,
                            "required": True}],
        "quality_gates": [
            {"id": f"GAME-Q1", "desc": "设计文档完整，需求可追溯",
             "check": "每个需求点都有对应的实现或设计依据", "layer": "U"},
            {"id": f"GAME-Q2", "desc": "产出物可验证",
             "check": "其他角色或工具可以验证该角色的产出", "layer": "I"},
        ],
        "standards_file": "SKILL.md",
        "use_case": f"适用于游戏开发管线中的{desc.split('：')[0] if '：' in desc else name}环节",
    }, default_flow_style=False, allow_unicode=True, sort_keys=False)

def gen_skill_md(name, desc, role_type, tags):
    part = desc.split("：")[0] if "：" in desc else name
    detail = desc.split("：")[-1] if "：" in desc else desc
    is_op = "OP" in tags
    phase_flag = {"design": "design-done", "dev": "dev-done_task-done",
                  "test": "test-done_layer-all-done", "art": "design-done",
                  "audio": "design-done"}.get(role_type, "dev-done_task-done")
    emoji = {"design": "📝", "dev": "💻", "test": "🧪", "art": "🎨", "audio": "🎵", "op": "👑"}.get(role_type, "🎮")

    template = f"""---
name: {name}
description: "{desc}"
runAs: inline
profiles: balanced
cost: medium
---

# {name}

**语言指令：推理用英文，回复用中文。**

## 使命

{desc}

## 第 0 步：准备工作

1. 读取交接工单，确认上一角色（或设计文档）的产出物已就绪
2. 检查需求文档和游戏设计文档中的相关模块定义
3. 如果缺输入 → 记录到交接工单并回退到上一角色

## 第 1 步：核心工作

#### 1. 核心原则：每个设计都有依据

```
每个:
  - 设计决策 → 满足什么需求？解决了什么问题？
  - 参数/阈值 → 这个数值有理论依据还是经验值？
  - 功能模块 → 单一职责是什么？能否被其他角色独立使用？
  - 验证方法 → 如何验证这个设计的正确性？谁来判断通过？

如果一句话说不出这个设计的理由，它就不该存在。
```

#### 2. 工作流程

1. **读需求** — 理解游戏设计文档中当前模块的定义
2. **设计方案** — 按需求输出设计方案（文档/原型/蓝图）
3. **实现** — 按设计方案执行（编码/配置/资源）
4. **自检** — 检查是否符合质量门标准
5. **产出** — 将产出物写入交接工单

#### 3. 质量门

工作完成后，立即检查：
  - 设计方案是否覆盖了所有需求点？
  - 产出物可被其他角色验证吗？
  - 有 TODO/FIXME 残留吗？清理掉再完成
  - 设计文档有版本标记吗？

## 不做

- 不覆盖其他角色的职责范围
- 不修改游戏核心机制（除非角色定义为系统设计）
- 不做资源资产生成（images/models/audio）——归专门的资源角色

## 角色完成（RED LINE #7）

完成角色工作后**立即执行**以下两步：

**步骤 1** → 调用 `mcp__cycle-bridge__queue_next_prompt`：
- `phase`: `"{phase_flag}"`
- `goal`: 原始目标（一字不改）
- `prompt`: 按模板填空

**步骤 2** → 输出完成框：
```
════════════════════════════════════
{emoji} {name}完成 · {phase_flag}
产出来 skills/roles/{name}/
▶ 终端: reasonix cycle --resume
════════════════════════════════════
```
"""
    return template.strip() + "\n"

def gen_standards_brief(name, desc):
    part = desc.split("：")[0] if "：" in desc else name
    detail = desc.split("：")[-1] if "：" in desc else desc
    return f"""# {name} 职业准则简报
# 生成日期: 2026-07-19
# 来源: 游戏行业标准实践

role: {name}
title: {part}
description: {desc}

## A — 工作准则
methodology:
  - name: 游戏开发工作流
    steps:
      - 需求分析 → 方案设计 → 评审 → 实现 → 验证 → 交付
best_practices:
  - 每个设计决策有需求依据
  - 产出物的可验证性
  - 版本控制和变更记录
standards:
  - 设计文档完整性：覆盖全部需求
  - 产出物可验证性：其他角色可独立验证
  - 版本标记：每次变更有版本记录

## B — 工作内容
daily_tasks:
  - 需求理解 → 方案设计 → 实现执行
  - 自检验证 → 产出物提交
outputs:
  - {name}_deliverables: {detail}
quality_standards:
  - 设计覆盖全部需求
  - 产出物可被验证
  - 无残留 TODO/FIXME

## C — 工具与方法
tools:
  - Godot 4.x 引擎
  - Markdown / YAML 文档工具
  - Git 版本控制

## D — 常见坑与风险
common_mistakes:
  - 设计无需求依据
  - 产出物不可验证
  - 越界覆盖其他角色职责
  - 版本控制缺失
"""


def main():
    print(f"Generating {len(ROLES)} role cards...")
    for name, short_desc, full_desc in ROLES:
        role_dir = os.path.join(ROLES_DIR, name)
        os.makedirs(role_dir, exist_ok=True)

        is_op = "OP" in name  # only game-architect is OP
        tags = ["OP", "game"] if is_op else ["game"]
        role_type = "op" if is_op else ("design" if name.endswith("designer") or name.endswith("designer") or "design" in full_desc else
                                        "dev" if "程序" in full_desc or "programmer" in name else
                                        "test" if "test" in name else
                                        "art" if "artist" in name or "美术" in full_desc else
                                        "audio" if "audio" in name or "音频" in full_desc else "design")

        # role-card.yaml
        rc = gen_role_card(name, short_desc + "：" + full_desc, tags)
        try:
            with open(os.path.join(role_dir, "role-card.yaml"), "w", encoding="utf-8") as f:
                f.write(rc)
        except OSError as e:
            print(f"  ❌ {name}: 写入 role-card.yaml 失败: {e}")
            continue

        # SKILL.md
        sm = gen_skill_md(name, short_desc + "：" + full_desc, role_type, tags)
        try:
            with open(os.path.join(role_dir, "SKILL.md"), "w", encoding="utf-8") as f:
                f.write(sm)
        except OSError as e:
            print(f"  ❌ {name}: 写入 SKILL.md 失败: {e}")
            continue

        # standards-brief.yaml
        sb = gen_standards_brief(name, short_desc + "：" + full_desc)
        try:
            with open(os.path.join(role_dir, "standards-brief.yaml"), "w", encoding="utf-8") as f:
                f.write(sb)
        except OSError as e:
            print(f"  ❌ {name}: 写入 standards-brief.yaml 失败: {e}")
            continue

        print(f"  ✅ {name:25s} {short_desc}")

    print(f"\nDone! {len(ROLES)} role cards created in {ROLES_DIR}/")

if __name__ == "__main__":
    main()
