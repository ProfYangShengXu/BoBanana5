#!/usr/bin/env python3
"""
Bobanana 5.0 — HR Recruitment Skill
HR 招聘技能：4 并行 subagent 职业研究 + 角色卡生成。

用法:
    python hr_recruitment.py recruit <role_name> <description>     # 发起招聘
    python hr_recruitment.py status <recruitment_id>               # 查看状态
    python hr_recruitment.py generate <recruitment_id>             # 生成角色卡
    python hr_recruitment.py quick <role_name> <standards_path>    # 引用已有准则创建
"""

import os
import sys
import json
import time
import yaml
from datetime import datetime

RECRUIT_DIR = ".reasonix/recruitments"
ROLES_DIR = "skills/roles"


def _ensure_dirs():
    os.makedirs(RECRUIT_DIR, exist_ok=True)
    os.makedirs(ROLES_DIR, exist_ok=True)


def _recruitment_path(rid):
    return os.path.join(RECRUIT_DIR, f"{rid}.json")


def _next_recruitment_id():
    return f"rec-{int(time.time())}"


def simulate_subagent_research(topic, role_name):
    """模拟一个 subagent 的研究（实际场景中为 LLM/web_fetch）"""
    time.sleep(0.2)  # 模拟并行延迟

    results_db = {
        "standards": {
            "key_standards": [f"{role_name} 的标准工作流程", f"{role_name} 核心方法论", f"{role_name} 交付物规范"],
            "best_practices": [f"使用业界标准工具链", "遵循团队协作规范", "保持文档同步"],
            "industry_references": [f"IGDA {role_name} 课程体系", f"GDC {role_name} 最佳实践演讲"],
        },
        "deliverables": {
            "output_types": ["设计文档", "实现代码", "测试用例", "使用手册"],
            "quality_criteria": ["功能完整", "性能达标", "可维护性强", "文档齐全"],
            "review_process": ["同行评审", "技术评审会", "用户验收测试"],
        },
        "tools": {
            "software": ["标准 IDE", "版本控制工具", "CI/CD 工具", "项目管理平台"],
            "workflow": ["需求分析 -> 设计 -> 实现 -> 测试 -> 评审 -> 发布"],
            "collaboration": ["每日站会", "迭代计划", "回顾会议"],
        },
        "pitfalls": {
            "common_mistakes": ["需求理解偏差", "技术选型过度设计", "测试覆盖不足", "文档滞后"],
            "risk_factors": ["时间估算不足", "依赖变更未同步", "沟通断层"],
            "anti_patterns": ["过早优化", "镀金", "silos 孤岛"],
        },
    }

    # 尝试网络获取真实信息（失败则用本地数据）
    if topic == "standards":
        try:
            import urllib.request
            url = f"https://en.wikipedia.org/w/api.php?action=query&titles={role_name.replace(' ', '_')}&format=json&prop=extracts&exintro=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Bobanana5/1.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
                pages = data.get('query', {}).get('pages', {})
                for pid, page in pages.items():
                    if 'extract' in page:
                        results_db["standards"]["industry_references"].append(
                            page['extract'][:200]
                        )
        except Exception:
            import logging
            logging.warning("网络请求失败，使用本地数据")

    return results_db.get(topic, {})


def start_recruitment(role_name, description, existing_standards_file=None):
    """发起招聘：并行启动 4 subagent 研究"""
    rid = _next_recruitment_id()
    _ensure_dirs()

    recruitment = {
        "recruitment_id": rid,
        "role_name": role_name,
        "description": description,
        "status": "researching",
        "progress": 0,
        "started_at": datetime.now().isoformat(),
        "subagent_results": {},
        "completed_subagents": 0,
        "total_subagents": 4,
        "existing_standards_file": existing_standards_file,
        "card_generated": False,
        "card_path": None,
    }

    # 如果有已有准则文件，跳过 subagent
    if existing_standards_file:
        recruitment["status"] = "standards_found"
        recruitment["progress"] = 100
        recruitment["completed_subagents"] = 4
        recruitment["subagent_results"] = {
            "skipped": True,
            "reason": f"引用已有准则文件: {existing_standards_file}",
        }
        _save_recruitment(recruitment)
        return recruitment

    _save_recruitment(recruitment)

    # 模拟 4 个并行 subagent
    topics = ["standards", "deliverables", "tools", "pitfalls"]
    for topic in topics:
        result = simulate_subagent_research(topic, role_name)
        recruitment["subagent_results"][topic] = result
        recruitment["completed_subagents"] += 1
        recruitment["progress"] = int(recruitment["completed_subagents"] / 4 * 100)
        _save_recruitment(recruitment)

    recruitment["status"] = "research_done"
    recruitment["progress"] = 100
    _save_recruitment(recruitment)

    return recruitment


def get_recruitment_status(recruitment_id):
    """获取招聘状态"""
    path = _recruitment_path(recruitment_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_standards_brief(recruitment):
    """Step 2: merge 4 subagent results into profession standards brief"""
    results = recruitment.get('subagent_results', {})
    if results.get('skipped'):
        return {'meta': {'source': 'existing_standards_file'}}

    return {
        'meta': {
            'role_name': recruitment['role_name'],
            'description': recruitment['description'],
            'research_date': datetime.now().isoformat(),
            'subagents_completed': recruitment.get('completed_subagents', 0),
        },
        'profession_standards': {
            'summary': f"{recruitment['role_name']} 职业准则",
            'key_standards': results.get('standards', {}).get('key_standards', []),
            'best_practices': results.get('standards', {}).get('best_practices', []),
        },
        'deliverables': {
            'output_types': results.get('deliverables', {}).get('output_types', []),
            'quality_criteria': results.get('deliverables', {}).get('quality_criteria', []),
        },
        'tools_and_methods': {
            'software': results.get('tools', {}).get('software', []),
            'workflow': results.get('tools', {}).get('workflow', []),
        },
        'pitfalls_and_risks': {
            'common_mistakes': results.get('pitfalls', {}).get('common_mistakes', []),
            'risk_factors': results.get('pitfalls', {}).get('risk_factors', []),
            'anti_patterns': results.get('pitfalls', {}).get('anti_patterns', []),
        },
    }


def generate_role_card(recruitment_id):
    """生成标准角色卡（与 architect 对齐的细颗粒度）"""
    recruitment = get_recruitment_status(recruitment_id)
    if not recruitment:
        print(f"招聘不存在: {recruitment_id}")
        return None

    if recruitment.get("card_generated"):
        print(f"角色卡已生成: {recruitment['card_path']}")
        return recruitment

    role_name = recruitment["role_name"]
    description = recruitment["description"]
    role_dir = os.path.join(ROLES_DIR, role_name)
    os.makedirs(role_dir, exist_ok=True)

    # ── 第 2 步：合并研究结果为职业准则简报 ──
    brief = generate_standards_brief(recruitment)
    brief_path = os.path.join(role_dir, "standards-brief.yaml")
    with open(brief_path, 'w', encoding='utf-8') as f:
        yaml.dump(brief, f, allow_unicode=True, default_flow_style=False)

    # ── 生成 role-card.yaml（与 architect 对齐的细颗粒度）──
    # 自动生成 example_state_machine 和 use_case
    role_slug = role_name.lower().replace(" ", "-")
    card = {
        "name": role_name,
        "description": description,
        "tags": [],
        "input_contract": [
            {"name": "task_input", "type": "object", "description": f"传递给 {role_name} 的任务输入", "required": True},
            {"name": "acceptance_criteria", "type": "object[]", "description": f"{role_name} 需满足的 PRD acceptance 标准", "required": True},
            {"name": "handoff_context", "type": "object", "description": "上一个角色的交接工单上下文", "required": False},
        ],
        "output_contract": [
            {"name": "implementation", "type": "object", "description": f"{role_name} 的实现产出（代码/设计/配置）"},
            {"name": "test_results", "type": "object[]", "description": f"测试结果（normal/boundary/adversarial 三路径）"},
            {"name": "risk_notes", "type": "object[]", "description": "7 维风险评估标注"},
        ],
        "quality_gates": [
            {"id": f"{role_name.upper()[:4]}-Q1", "desc": "所有 acceptance 已覆盖实现", "check": "逐条核对 PRD acceptance", "layer": "U"},
            {"id": f"{role_name.upper()[:4]}-Q2", "desc": "无空壳函数和死代码", "check": "grep TODO/FIXME/dead code", "layer": "U"},
            {"id": f"{role_name.upper()[:4]}-Q3", "desc": "每个函数 <= 30 行", "check": "行数检查", "layer": "U"},
        ],
        "standards_file": "standards-brief.yaml",
        "example_state_machine": {
            "entry_phase": "arch-done",
            "exit_phase": "dev-done_task-done",
            "description": f"{role_name} 在架构师分配任务后执行，完成后交回架构师验收",
            "typical_pipeline": ["architect", role_slug, "architect(验收)", "client-gate(CL)"],
        },
        "use_case": f"适合{description[:40]}，可替代fullstack-dev在该领域的专门工作",
    }

    card_path = os.path.join(role_dir, "role-card.yaml")
    with open(card_path, 'w', encoding='utf-8') as f:
        yaml.dump(card, f, allow_unicode=True, default_flow_style=False)

    # 生成 SKILL.md
    skill_content = f"""---
name: {role_name}
description: "{description}"
runAs: inline
profiles: balanced
cost: medium
---

# {role_name}

## Input Contract
- task_input: 任务输入
- acceptance_criteria: PRD acceptance 标准
- handoff_context: 交接上下文（可选）

## Output Contract
- implementation: 实现产出
- test_results: normal/boundary/adversarial 三路径
- risk_notes: 7 维风险评估

## Quality Gates
1. All acceptance covered
2. No dead code
3. Each function <= 30 lines

## 能力边界

本角色**严格限定**在以上 Input/Output Contract 范围内工作。

1. **不修不属于自己任务的代码**——发现其他模块的问题，记录到交接工单。
2. **不做其他角色的决策**——不代替架构师/测试/其他角色做决定。
3. **不顺手修问题**——看到小问题不能顺手改，必须通过交接工单传递。
4. **不代替后续角色做他们的工作**——各司其职。

违反以上任何一条，视为越权。

## Standards File
standards-brief.yaml
"""
    skill_path = os.path.join(role_dir, "SKILL.md")
    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write(skill_content)

    # 更新招聘记录
    recruitment["card_generated"] = True
    recruitment["card_path"] = card_path
    recruitment["skill_path"] = skill_path
    recruitment["status"] = "completed"
    _save_recruitment(recruitment)

    print(f"角色卡生成:")
    print(f"  role-card.yaml:     {card_path}")
    print(f"  SKILL.md:           {skill_path}")
    print(f"  standards-brief:    {brief_path}")
    print(f"  注册命令:           python skills/roles/role_card_registry.py scan")

    return recruitment


def reference_existing_standards(role_name, standards_path):
    """引用已有准则文件创建角色卡，跳过 subagent 研究"""
    if not os.path.exists(standards_path):
        print(f"准则文件不存在: {standards_path}")
        return None

    description = f"基于 {standards_path} 创建的角色"
    recruitment = start_recruitment(role_name, description, existing_standards_file=standards_path)
    recruitment["skipped_subagents"] = 4

    _save_recruitment(recruitment)
    return recruitment


def _save_recruitment(recruitment):
    _ensure_dirs()
    path = _recruitment_path(recruitment["recruitment_id"])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(recruitment, f, ensure_ascii=False, indent=2)


def cmd_recruit(args):
    recruitment = start_recruitment(args.role_name, args.description)
    print(f"招聘发起: {recruitment['recruitment_id']}")
    print(f"角色:      {recruitment['role_name']}")
    print(f"状态:      {recruitment['status']}")
    print(f"进度:      {recruitment['progress']}%")
    print(f"完成 subagent: {recruitment['completed_subagents']}/{recruitment['total_subagents']}")
    return 0


def cmd_status(args):
    recruitment = get_recruitment_status(args.recruitment_id)
    if not recruitment:
        print(f"招聘不存在: {args.recruitment_id}")
        return 1
    print(f"招聘 ID:    {recruitment['recruitment_id']}")
    print(f"角色:        {recruitment['role_name']}")
    print(f"描述:        {recruitment['description']}")
    print(f"状态:        {recruitment['status']}")
    print(f"进度:        {recruitment['progress']}%")
    print(f"完成 subagent: {recruitment['completed_subagents']}/{recruitment['total_subagents']}")
    if recruitment.get('existing_standards_file'):
        print(f"引用准则:    {recruitment['existing_standards_file']}")
    if recruitment.get('card_generated'):
        print(f"角色卡:      {recruitment['card_path']}")
    return 0


def cmd_generate(args):
    result = generate_role_card(args.recruitment_id)
    return 0 if result else 1


def cmd_quick(args):
    recruitment = reference_existing_standards(args.role_name, args.standards_path)
    if not recruitment:
        return 1
    print(f"快速创建角色卡:")
    print(f"  角色: {recruitment['role_name']}")
    print(f"  引用: {recruitment['existing_standards_file']}")
    print(f"  跳过 subagent: {recruitment.get('skipped_subagents', 0)} 个")
    print(f"\n生成角色卡:")
    generate_role_card(recruitment['recruitment_id'])
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 HR Recruitment Skill')
    sub = parser.add_subparsers(dest='command')

    p_r = sub.add_parser('recruit', help='发起招聘')
    p_r.add_argument('role_name', help='角色名称')
    p_r.add_argument('description', help='角色描述')

    p_s = sub.add_parser('status', help='查看招聘状态')
    p_s.add_argument('recruitment_id', help='招聘 ID')

    p_g = sub.add_parser('generate', help='生成角色卡')
    p_g.add_argument('recruitment_id', help='招聘 ID')

    p_q = sub.add_parser('quick', help='引用已有准则创建角色')
    p_q.add_argument('role_name', help='角色名称')
    p_q.add_argument('standards_path', help='已有准则文件路径')

    args = parser.parse_args()

    if args.command == 'recruit':
        return cmd_recruit(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'generate':
        return cmd_generate(args)
    elif args.command == 'quick':
        return cmd_quick(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
