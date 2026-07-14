#!/usr/bin/env python3
"""
Bobanana 5.0 — Kitset 发现与匹配工具
Boss 角色用此模块自动扫描 kitsets/ 目录，匹配用户目标。
不修改任何核心模块代码（铁律）。
"""

import os
import json
import logging

KITSETS_DIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_CACHE = {}  # kitset_name -> {domains, entry_role, path}


def scan_kitsets():
    """扫描 kitsets/ 目录，返回所有发现的 Kitset 元数据列表"""
    kitsets = []
    if not os.path.isdir(KITSETS_DIR):
        return kitsets
    for name in sorted(os.listdir(KITSETS_DIR)):
        ks_dir = os.path.join(KITSETS_DIR, name)
        if not os.path.isdir(ks_dir):
            continue
        manifest_path = os.path.join(ks_dir, 'reasonix-plugin.json')
        if not os.path.exists(manifest_path):
            continue
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            ks_info = {
                'name': manifest.get('kitset_name', name),
                'domains': manifest.get('kitset_domains', []),
                'entry_role': manifest.get('entry_role', ''),
                'path': ks_dir,
                'description': manifest.get('description', ''),
            }
            if ks_info['entry_role']:
                REGISTRY_CACHE[ks_info['name']] = ks_info
                kitsets.append(ks_info)
                print(f"  [Kitset] 发现 {ks_info['name']}: {ks_info['domains']}")
        except Exception as e:
            logging.warning(f"Kitset {name} 加载失败: {e}")
    return kitsets


def match_kitset(goal, kitsets=None):
    """匹配用户目标和 Kitset 领域标签"""
    if kitsets is None:
        kitsets = scan_kitsets()
    if not kitsets:
        return None, 0

    goal_lower = goal.lower()
    best_match = None
    best_score = 0

    for ks in kitsets:
        score = 0
        for domain in ks['domains']:
            if domain.lower() in goal_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_match = ks

    return best_match, best_score


def get_kitset_state_machine(kitset_name):
    """获取 Kitset 的状态机模板路径（如果有）"""
    ks_info = REGISTRY_CACHE.get(kitset_name)
    if not ks_info:
        return None
    sm_path = os.path.join(ks_info['path'], f'state-machine-{kitset_name}.yaml')
    return sm_path if os.path.exists(sm_path) else None


if __name__ == '__main__':
    print("=== Kitset 发现工具 ===")
    kitsets = scan_kitsets()
    print(f"\n共发现 {len(kitsets)} 个 Kitset")
    for ks in kitsets:
        sm = get_kitset_state_machine(ks['name'])
        print(f"  {ks['name']:20s} 领域: {ks['domains']}  SM:{'有' if sm else '无'}  入口:{ks['entry_role']}")

    test_goals = ["帮我做一个STM32电机控制项目", "搭建一个Web后端服务", "FPGA图像处理加速"]
    print("\n=== 匹配测试 ===")
    for g in test_goals:
        match, score = match_kitset(g, kitsets)
        if match:
            print(f"  [{score}分] {g[:30]:30s} → {match['name']}({match['entry_role']})")
        else:
            print(f"  [0分] {g[:30]:30s} → 无匹配(使用默认角色池)")
