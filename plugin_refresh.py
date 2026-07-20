#!/usr/bin/env python3
"""
Bobanana 5.0 — 插件刷新工具
让 Reasonix 桌面端立即发现新的技能和命令，无需重启。
"""

import os
import json
import shutil
import sys

PLUGIN_DIR = os.path.expandvars(r'%APPDATA%\reasonix\plugins\bobanana5')
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(PROJECT_DIR, 'bobanana-plugin')


def refresh():
    print("=== Bobanana 5.0 插件刷新 ===")
    print()

    if not os.path.exists(PLUGIN_DIR):
        print(f"  [!] 插件未安装，请先安装")
        print(f"      reasonix plugin install {SOURCE_DIR} --replace --yes")
        return False

    # 1. 同步 manifest
    src = os.path.join(SOURCE_DIR, 'reasonix-plugin.json')
    dst = os.path.join(PLUGIN_DIR, 'reasonix-plugin.json')
    shutil.copy2(src, dst)
    print(f"  [+] manifest 已同步")

    # 2. 同步 skills
    src_skills = os.path.join(SOURCE_DIR, 'skills')
    dst_skills = os.path.join(PLUGIN_DIR, 'skills')
    if os.path.exists(dst_skills):
        shutil.rmtree(dst_skills)
    shutil.copytree(src_skills, dst_skills)
    print(f"  [+] skills 已同步")

    # 3. 同步 commands
    src_cmds = os.path.join(SOURCE_DIR, 'commands')
    dst_cmds = os.path.join(PLUGIN_DIR, 'commands')
    if os.path.exists(dst_cmds):
        shutil.rmtree(dst_cmds)
    shutil.copytree(src_cmds, dst_cmds)
    print(f"  [+] commands 已同步")

    # 4. 通知 Reasonix 刷新（写入标记文件）
    refresh_file = os.path.join(PLUGIN_DIR, '.refresh')
    try:
        with open(refresh_file, 'w') as f:
            f.write('refresh')
        print(f"  [+] 刷新标记已写入，Reasonix 将在下次交互时检测")
    except OSError as e:
        print(f"  [!] 写入刷新标记失败: {e}")

    # 5. 同步全局 skills/commands（覆盖安装）
    for item_dir, item_type in [('skills', 'skill'), ('commands', 'command')]:
        src_dir = os.path.join(PLUGIN_DIR, item_dir)
        for name in os.listdir(src_dir):
            src_item = os.path.join(src_dir, name)
            dst_item = os.path.join(os.path.expandvars(r'%USERPROFILE%\.reasonix'), item_dir, name)
            if os.path.isfile(src_item):
                os.makedirs(os.path.dirname(dst_item), exist_ok=True)
                shutil.copy2(src_item, dst_item)
            elif os.path.isdir(src_item):
                if os.path.exists(dst_item):
                    shutil.rmtree(dst_item)
                shutil.copytree(src_item, dst_item)
            print(f"  [+] global {item_type}: {name}")

    print()
    print("  刷新完成！")
    print("  下次在 Reasonix 对话框输入 /bb 即可使用。")
    print("  新角色卡通过 HR 招聘创建：")
    print("    python hr_recruitment.py recruit \"角色名\" \"描述\"")
    print("    python hr_recruitment.py generate <recruitment_id>")
    return True


if __name__ == '__main__':
    refresh()
