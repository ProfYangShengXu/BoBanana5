#!/usr/bin/env python3
"""
Bobanana 5.0 — Role Card Registry CLI
角色卡注册表命令行工具，支持 CRUD 操作和目录扫描。

用法:
    python role_card_registry.py list                    # 列出所有角色卡
    python role_card_registry.py list --tag OP           # 按标签过滤
    python role_card_registry.py get <name>              # 获取指定角色卡
    python role_card_registry.py register <path>         # 注册一张新角色卡
    python role_card_registry.py scan                    # 重新扫描
    python role_card_registry.py validate                # 验证所有角色卡
"""

import os
import sys
import json
import yaml
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, '..', '..'))
ROLES_DIR = SCRIPT_DIR
REGISTRY_PATH = os.path.join(ROLES_DIR, '.registry.yaml')
SCHEMA_PATH = os.path.join(ROLES_DIR, 'role-card.schema.yaml')
KITSETS_DIR = os.path.join(PROJECT_ROOT, 'kitsets')


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        return {'version': 1, 'last_scan': '', 'cards': []}
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {'version': 1, 'last_scan': '', 'cards': []}


def save_registry(registry):
    with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(registry, f, allow_unicode=True, default_flow_style=False)


def load_role_card(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def scan_directory():
    """扫描 skills/roles/ + skills/kitsets/，重建注册表"""
    registry = load_registry()
    seen_ids = set()

    def _scan_dir(base_dir, kitset_name=''):
        if not os.path.isdir(base_dir):
            return
        for item in sorted(os.listdir(base_dir)):
            card_path = os.path.join(base_dir, item, 'role-card.yaml')
            if not os.path.isfile(card_path):
                continue
            try:
                card = load_role_card(card_path)
                card_id = card.get('name', item)
                seen_ids.add(card_id)
                rel = os.path.relpath(card_path, ROLES_DIR).replace('\\', '/')
                entry = {
                    'id': card_id,
                    'name': card.get('name', card_id),
                    'path': rel,
                    'tags': card.get('tags', []),
                    'description': card.get('description', '')[:80],
                    'use_case': card.get('use_case', '')[:100],
                    'has_example_sm': 'example_state_machine' in card,
                    'kitset': kitset_name,
                    'registered_at': registry.get('last_scan', ''),
                }
                existing = [c for c in registry['cards'] if c['id'] == card_id]
                if existing:
                    idx = registry['cards'].index(existing[0])
                    registry['cards'][idx] = entry
                else:
                    entry['registered_at'] = ''
                    registry['cards'].append(entry)
            except Exception as e:
                print(f"WARN: {card_path}: {e}", file=sys.stderr)

    _scan_dir(ROLES_DIR, '')
    if os.path.isdir(KITSETS_DIR):
        for ks in sorted(os.listdir(KITSETS_DIR)):
            ks_dir = os.path.join(KITSETS_DIR, ks)
            if os.path.isdir(ks_dir):
                # Kitset 角色卡在 roles/ 子目录下
                ks_roles = os.path.join(ks_dir, 'roles')
                if os.path.isdir(ks_roles):
                    _scan_dir(ks_roles, ks)

    registry['cards'] = [c for c in registry['cards'] if c['id'] in seen_ids]
    registry['last_scan'] = ''
    save_registry(registry)
    return registry


def cmd_list(args):
    registry = load_registry()
    cards = registry['cards']
    if args.tag:
        cards = [c for c in cards if args.tag in c.get('tags', [])]
    if not cards:
        print("(空)")
        return 0
    for card in sorted(cards, key=lambda c: c['id']):
        tags = ','.join(card.get('tags', [])) if card.get('tags') else '-'
        ks = f" [{card['kitset']}]" if card.get('kitset') else ""
        desc = card.get('description', '')[:60]
        print(f"  {card['id']:20s} [{tags:6s}]{ks:20s} {desc}")
    print(f"\n共 {len(cards)} 张角色卡")
    return 0


def cmd_get(args):
    registry = load_registry()
    meta = next((c for c in registry['cards'] if c['id'] == args.name), None)
    if not meta:
        print(f"错误: 未找到 '{args.name}'")
        return 1
    card_path = os.path.join(ROLES_DIR, meta['path'])
    if not os.path.exists(card_path):
        # 尝试 kitsets 路径
        card_path = os.path.join(KITSETS_DIR, meta['path'])
    if not os.path.exists(card_path):
        print(f"错误: 文件不存在 {meta['path']}")
        return 1
    card = load_role_card(card_path)
    print(f"名称:    {card.get('name', '?')}")
    print(f"标签:    {', '.join(card.get('tags', [])) or '(无)'}")
    if meta.get('kitset'):
        print(f"工具集:  {meta['kitset']}")
    print(f"描述:    {card.get('description', '')}")
    print(f"输入:    {len(card.get('input_contract', []))} 项")
    print(f"输出:    {len(card.get('output_contract', []))} 项")
    print(f"质量门:  {len(card.get('quality_gates', []))} 项")
    if card.get('standards_file'):
        print(f"准则:    {card['standards_file']}")
    return 0


def cmd_register(args):
    path = args.path
    if not os.path.exists(path):
        print(f"错误: 文件不存在 {path}")
        return 1
    try:
        card = load_role_card(path)
    except Exception as e:
        print(f"错误: YAML解析失败 - {e}")
        return 1
    if 'name' not in card:
        print("错误: 缺少 'name' 字段")
        return 1
    card_id = card['name']
    registry = load_registry()
    rel_path = os.path.relpath(path, ROLES_DIR).replace('\\', '/')
    entry = {
        'id': card_id, 'name': card['name'], 'path': rel_path,
        'tags': card.get('tags', []), 'description': card.get('description', '')[:80],
        'registered_at': '',
    }
    existing = [c for c in registry['cards'] if c['id'] == card_id]
    if existing:
        idx = registry['cards'].index(existing[0])
        registry['cards'][idx] = entry
        print(f"更新: {card_id}")
    else:
        registry['cards'].append(entry)
        print(f"注册: {card_id}")
    save_registry(registry)
    return 0


def cmd_scan(args):
    registry = scan_directory()
    n = len(registry['cards'])
    ks = sum(1 for c in registry['cards'] if c.get('kitset'))
    print(f"扫描完成: {n} 张 ({ks} 来自外部工具集)")
    return 0


def cmd_validate(args):
    from validate_role_card import validate_role_card
    registry = load_registry()
    errors = passed = 0
    for meta in registry['cards']:
        # 尝试 roles 路径，再试 kitsets 路径
        card_path = os.path.join(ROLES_DIR, meta['path'])
        if not os.path.exists(card_path):
            card_path = os.path.join(KITSETS_DIR, meta['path'])
        if not os.path.exists(card_path):
            print(f"  NOT_FOUND: {meta['id']}")
            errors += 1
            continue
        card_errors = validate_role_card(card_path, SCHEMA_PATH)
        if card_errors:
            print(f"  FAIL: {meta['id']}")
            for e in card_errors:
                print(f"    - {e}")
            errors += 1
        else:
            print(f"  PASS: {meta['id']}")
            passed += 1
    print(f"\n验证: {passed} 通过, {errors} 失败")
    return 1 if errors else 0


def main():
    p = argparse.ArgumentParser(description='Bobanana 5.0 Role Card Registry')
    sub = p.add_subparsers(dest='command')
    pl = sub.add_parser('list', help='列出角色卡')
    pl.add_argument('--tag', '-t', help='按标签过滤')
    sub.add_parser('get', help='获取角色卡').add_argument('name')
    sub.add_parser('register', help='注册角色卡').add_argument('path')
    sub.add_parser('scan', help='重新扫描')
    sub.add_parser('validate', help='验证所有卡')
    args = p.parse_args()
    return {'list': cmd_list, 'get': cmd_get, 'register': cmd_register,
            'scan': cmd_scan, 'validate': cmd_validate}.get(
        args.command, lambda a: p.print_help() or 0)(args)


if __name__ == '__main__':
    sys.exit(main())
