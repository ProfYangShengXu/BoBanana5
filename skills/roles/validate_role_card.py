#!/usr/bin/env python3
"""
Bobanana 5.0 — Role Card Validator
验证 role-card.yaml 是否符合 role-card.schema.yaml 的定义。

用法：
    python3 validate_role_card.py skills/roles/architect/role-card.yaml
    python3 validate_role_card.py --all    # 验证 skills/roles/ 下所有角色卡
"""

import sys
import os
import re
import yaml


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def validate_role_card(card_path, schema_path=None):
    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(__file__), 'role-card.schema.yaml')

    errors = []

    # 加载 Schema
    try:
        schema = load_yaml(schema_path)
    except Exception as e:
        return [f"无法加载 Schema 文件 {schema_path}: {e}"]

    # 加载角色卡
    try:
        card = load_yaml(card_path)
    except Exception as e:
        return [f"无法加载角色卡文件 {card_path}: {e}"]

    fields = schema.get('schema', {}).get('fields', {})

    # 1. 检查必填字段
    for field_name, field_def in fields.items():
        if field_def.get('required') and field_name not in card:
            errors.append(f"[必填缺失] {field_name}: {field_def.get('description', '')}")

    # 2. 检查已有字段类型
    for field_name, value in card.items():
        if field_name not in fields:
            errors.append(f"[未知字段] {field_name}: 不在 Schema 定义中")
            continue

        field_def = fields[field_name]
        expected_type = field_def.get('type')

        if expected_type == 'string':
            if not isinstance(value, str):
                errors.append(f"[类型错误] {field_name}: 期望 string，实际 {type(value).__name__}")
            else:
                # 检查最小长度
                min_len = field_def.get('min_length')
                if min_len and len(value) < min_len:
                    errors.append(f"[长度不足] {field_name}: 最少 {min_len} 字符，当前 {len(value)}")
                # 检查最大长度
                max_len = field_def.get('max_length')
                if max_len and len(value) > max_len:
                    errors.append(f"[长度超限] {field_name}: 最多 {max_len} 字符，当前 {len(value)}")
                # 检查正则
                pattern = field_def.get('pattern')
                if pattern and not re.match(pattern, value):
                    errors.append(f"[格式错误] {field_name}: 不符合模式 {pattern}")

        elif expected_type == 'array':
            if not isinstance(value, list):
                errors.append(f"[类型错误] {field_name}: 期望 array，实际 {type(value).__name__}")
            else:
                items_def = field_def.get('items', {})

                # 检查枚举值
                enum_vals = items_def.get('enum')
                if enum_vals:
                    for item in value:
                        if item not in enum_vals:
                            errors.append(f"[枚举值错误] {field_name}: '{item}' 不在允许值 {enum_vals} 中")

                # 检查数组字段唯一性
                if field_def.get('unique') and len(value) != len(set(value)):
                    errors.append(f"[重复值] {field_name}: 数组元素不唯一")

                # 检查最大数量
                max_items = field_def.get('max_items')
                if max_items and len(value) > max_items:
                    errors.append(f"[数量超限] {field_name}: 最多 {max_items} 项，当前 {len(value)} 项")

                # 如果是对象数组，检查每个对象的字段
                if items_def.get('type') == 'object':
                    obj_fields = items_def.get('fields', {})
                    for i, obj in enumerate(value):
                        for obj_field_name, obj_field_def in obj_fields.items():
                            if obj_field_def.get('required') and obj_field_name not in obj:
                                errors.append(f"[对象必填缺失] {field_name}[{i}].{obj_field_name}")

        elif expected_type == 'object':
            if not isinstance(value, dict):
                errors.append(f"[类型错误] {field_name}: 期望 object，实际 {type(value).__name__}")
            else:
                obj_fields = field_def.get('fields', {})
                for obj_field_name, obj_field_def in obj_fields.items():
                    if obj_field_name in value:
                        val = value[obj_field_name]
                        exp_type = obj_field_def.get('type')
                        if exp_type == 'integer' and not isinstance(val, int):
                            errors.append(f"[类型错误] {field_name}.{obj_field_name}: 期望 integer")
                        elif exp_type == 'array' and not isinstance(val, list):
                            errors.append(f"[类型错误] {field_name}.{obj_field_name}: 期望 array")
                        # 检查枚举
                        enum_vals = obj_field_def.get('enum')
                        if enum_vals and val not in enum_vals:
                            errors.append(f"[枚举值错误] {field_name}.{obj_field_name}: '{val}'")

    return errors


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate_role_card.py <path-to-role-card.yaml>")
        print("  或: python3 validate_role_card.py --all")
        sys.exit(1)

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    roles_dir = os.path.join(os.path.dirname(scripts_dir), 'skills', 'roles')

    if sys.argv[1] == '--all':
        card_files = []
        for root, dirs, files in os.walk(roles_dir):
            for f in files:
                if f == 'role-card.yaml':
                    card_files.append(os.path.join(root, f))
        if not card_files:
            print(f"未在 {roles_dir} 下找到任何 role-card.yaml 文件")
            sys.exit(0)
    else:
        card_files = [sys.argv[1]]

    all_errors = {}
    for card_path in card_files:
        errors = validate_role_card(card_path)
        rel_path = os.path.relpath(card_path)
        if errors:
            all_errors[rel_path] = errors
            print(f"FAIL {rel_path}: {len(errors)} 个错误")
            for e in errors:
                print(f"   - {e}")
        else:
            print(f"PASS {rel_path}: 验证通过")

    if all_errors:
        sys.exit(1)
    else:
        print(f"\n共验证 {len(card_files)} 张角色卡，all passed PASS")
        sys.exit(0)


if __name__ == '__main__':
    main()
