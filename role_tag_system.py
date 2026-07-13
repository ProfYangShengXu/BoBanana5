#!/usr/bin/env python3
"""
Bobanana 5.0 — Role Tag System
角色标签系统：OP/CL/HR 标签的查询和行为逻辑。

用法:
    python role_tag_system.py check <role_name>               # 检查角色标签
    python role_tag_system.py list --tag OP                   # 按标签列出角色
    python role_tag_system.py verify <caller> <target>         # 验证调用权限
    python role_tag_system.py scan                           # 扫描并输出所有标签
"""

import os
import sys
import yaml
import logging

ROLES_DIR = "skills/roles"


def load_all_role_cards():
    """加载 skills/roles/ 下所有角色卡"""
    cards = []
    if not os.path.exists(ROLES_DIR):
        return cards
    for item in os.listdir(ROLES_DIR):
        card_path = os.path.join(ROLES_DIR, item, 'role-card.yaml')
        if os.path.isfile(card_path):
            try:
                with open(card_path, 'r', encoding='utf-8') as f:
                    card = yaml.safe_load(f)
                if card and 'name' in card:
                    cards.append(card)
            except yaml.YAMLError:
                logging.warning("角色卡 YAML 损坏，跳过: %s", card_path)
    return cards


def has_tag(role_name, tag):
    """检查角色是否有指定标签"""
    cards = load_all_role_cards()
    for card in cards:
        if card['name'] == role_name:
            tags = card.get('tags', [])
            return tag in tags
    return False


def get_roles_by_tag(tag):
    """按标签列出所有角色名"""
    cards = load_all_role_cards()
    return [card['name'] for card in cards if tag in card.get('tags', [])]


def apply_tag_behavior(role_name, context=None):
    """获取角色的标签行为（动作 + 限制）"""
    actions = []
    restrictions = []

    cards = load_all_role_cards()
    card = None
    for c in cards:
        if c['name'] == role_name:
            card = c
            break

    if not card:
        return {'actions': [], 'restrictions': ['未找到角色卡']}

    tags = card.get('tags', [])

    if 'OP' in tags:
        actions.extend([
            'read_role_card_library',
            'write_state_machine',
            'detect_role_gaps',
            'trigger_emergency_hiring',
            'design_pipeline_topology',
        ])
        restrictions.append('CL 终审不可跳过')

    if 'CL' in tags:
        actions.extend([
            'full_project_review',
            'score_1_to_10',
            'failback_to_op',
        ])
        restrictions.extend([
            '必须使用隔离 subagent',
            '不可修改代码',
        ])

    if 'HR' in tags:
        actions.extend([
            'parallel_subagent_research',
            'generate_role_card',
        ])
        restrictions.extend([
            '仅可由 OP 角色触发',
            '不可作为出口节点',
            '不可作为普通节点',
        ])

    return {'actions': actions, 'restrictions': restrictions}


def enforce_hr_restriction(caller_role):
    """验证调用者是否有权限触发 HR"""
    if not has_tag(caller_role, 'OP'):
        return {'allowed': False, 'reason': f"'{caller_role}' 没有 OP 标签，无法触发 HR"}
    return {'allowed': True, 'reason': ''}


def get_all_tags_summary():
    """获取所有角色的标签摘要"""
    cards = load_all_role_cards()
    summary = []
    for card in sorted(cards, key=lambda c: c['name']):
        tags = card.get('tags', [])
        summary.append({
            'name': card['name'],
            'tags': tags,
            'tag_count': len(tags),
            'description': card.get('description', '')[:60],
        })
    return summary


def cmd_check(args):
    cards = load_all_role_cards()
    card = None
    for c in cards:
        if c['name'] == args.role_name:
            card = c
            break
    if not card:
        print(f"未找到角色: {args.role_name}")
        return 1

    tags = card.get('tags', [])
    tag_str = ', '.join(tags) if tags else '(无标签)'
    print(f"角色:      {card['name']}")
    print(f"标签:      {tag_str}")
    print(f"描述:      {card.get('description', '')[:80]}")

    behavior = apply_tag_behavior(args.role_name)
    if behavior['actions']:
        print(f"\n允许的操作:")
        for a in behavior['actions']:
            print(f"  + {a}")
    if behavior['restrictions']:
        print(f"\n限制:")
        for r in behavior['restrictions']:
            print(f"  ! {r}")

    return 0


def cmd_list(args):
    if args.tag:
        names = get_roles_by_tag(args.tag)
        if names:
            print(f"标签 '{args.tag}' 的角色:")
            for n in names:
                print(f"  - {n}")
        else:
            print(f"没有角色带有标签 '{args.tag}'")
    else:
        summary = get_all_tags_summary()
        if not summary:
            print("(空)")
            return 0
        for s in summary:
            tags = ','.join(s['tags']) if s['tags'] else '-'
            print(f"  {s['name']:20s} [{tags:10s}] {s['description']}")
        print(f"\n共 {len(summary)} 张角色卡")

    return 0


def cmd_verify(args):
    result = enforce_hr_restriction(args.caller)
    if result['allowed']:
        print(f"PASS: '{args.caller}' 可以调用 '{args.target}'")
    else:
        print(f"DENY: {result['reason']}")
    return 0 if result['allowed'] else 1


def cmd_scan(args):
    summary = get_all_tags_summary()
    print(f"标签系统概要:")
    for tag_name in ['OP', 'CL', 'HR']:
        roles = get_roles_by_tag(tag_name)
        print(f"  [{tag_name}] {len(roles)} 个角色: {', '.join(roles) if roles else '(无)'}")
    print(f"\n总计: {len(summary)} 张角色卡")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 Role Tag System')
    sub = parser.add_subparsers(dest='command')

    p_c = sub.add_parser('check', help='检查角色标签和行为')
    p_c.add_argument('role_name', help='角色名称')

    p_l = sub.add_parser('list', help='按标签列出角色')
    p_l.add_argument('--tag', '-t', help='标签名 (OP/CL/HR)')

    p_v = sub.add_parser('verify', help='验证调用权限')
    p_v.add_argument('caller', help='调用者角色')
    p_v.add_argument('target', help='被调用角色')

    sub.add_parser('scan', help='扫描所有标签')

    args = parser.parse_args()

    if args.command == 'check':
        return cmd_check(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'verify':
        return cmd_verify(args)
    elif args.command == 'scan':
        return cmd_scan(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
