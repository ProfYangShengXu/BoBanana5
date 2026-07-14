#!/usr/bin/env python3
"""
Bobanana 5.0 — Reasonix 插件注册工具
将 Bobanana 注册为 Reasonix 的 MCP 插件，可通过桌面 GUI 插件面板管理。

用法:
    python plugin_register.py              # 交互式安装
    python plugin_register.py --check      # 检查安装状态
    python plugin_register.py --remove     # 卸载
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path


REASONIX_HOME = os.path.expanduser("~/.reasonix")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_JSON = os.path.join(PROJECT_DIR, ".mcp.json")
PLUGIN_NAME = "bobanana5"


def get_reasonix_config_path():
    """获取 Reasonix 配置文件路径"""
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(appdata, 'reasonix', 'config.toml')
    return os.path.join(REASONIX_HOME, 'config.toml')


def get_reasonix_toml():
    """查找项目或全局 reasonix.toml"""
    # 项目级优先
    for p in [os.path.join(PROJECT_DIR, 'reasonix.toml'),
              os.path.join(REASONIX_HOME, 'config.toml'),
              get_reasonix_config_path()]:
        if os.path.exists(p):
            return p
    return os.path.join(PROJECT_DIR, 'reasonix.toml')


def add_plugin_entry():
    """在 reasonix.toml 中添加 [[plugins]] 条目"""
    toml_path = get_reasonix_toml()
    plugin_entry = f"""
# Bobanana 5.0 — 可编程状态机管线
[[plugins]]
name    = "bobanana5"
command = "python {os.path.join(PROJECT_DIR, 'mcp_server.py').replace(os.sep, '/')}"
call_timeout_seconds = 600
"""

    if os.path.exists(toml_path):
        with open(toml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'bobanana5' in content:
            print(f"  [OK] 插件已存在于 {toml_path}")
            return True
        with open(toml_path, 'a', encoding='utf-8') as f:
            f.write(plugin_entry)
        print(f"  [+] 已添加到 {toml_path}")
    else:
        # 创建项目级 reasonix.toml
        tool_allowlist = ""
        base = f"""# Reasonix 配置 — 由 Bobanana 5.0 生成
default_model = "deepseek-flash"
language      = "zh"

[agent]
max_steps = 0

[[providers]]
name        = "deepseek-flash"
kind        = "openai"
base_url    = "https://api.deepseek.com"
model       = "deepseek-v4-flash"
api_key_env = "DEEP********_KEY"

{tool_allowlist}

{plugin_entry}"""
        with open(toml_path, 'w', encoding='utf-8') as f:
            f.write(base)
        print(f"  [+] 已创建 {toml_path}")

    # 复制 .mcp.json 到 Reasonix 数据目录
    mcp_target = os.path.join(REASONIX_HOME, 'mcp', f'{PLUGIN_NAME}.mcp.json')
    os.makedirs(os.path.dirname(mcp_target), exist_ok=True)
    shutil.copy2(MCP_JSON, mcp_target)
    print(f"  [+] 已复制 .mcp.json -> {mcp_target}")

    return True


def copy_skills_and_commands():
    """将 skills 和 commands 复制到 Reasonix 全局目录"""
    # Skills
    for skill in ['bobanana', 'pipeline']:
        src = os.path.join(PROJECT_DIR, 'skills', skill, 'SKILL.md')
        dst_dir = os.path.join(REASONIX_HOME, 'skills', skill)
        if os.path.exists(src):
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(dst_dir, 'SKILL.md'))
            print(f"  [+] skill: {skill}")

    # Commands — 新增 bb.md 作为 /bb 快捷指令
    for cmd in ['bb.md', 'bobanana.md', 'cycle.md']:
        src = os.path.join(PROJECT_DIR, 'commands', cmd)
        dst = os.path.join(REASONIX_HOME, 'commands', cmd)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  [+] command: {cmd}")

    # 复制 pipeline.md（cycle.md 的别名）
    cycle_src = os.path.join(REASONIX_HOME, 'commands', 'cycle.md')
    pipeline_dst = os.path.join(REASONIX_HOME, 'commands', 'pipeline.md')
    if os.path.exists(cycle_src) and not os.path.exists(pipeline_dst):
        shutil.copy2(cycle_src, pipeline_dst)
        print(f"  [+] command: pipeline.md (alias)")


def check_status():
    """检查安装状态"""
    print("=== Bobanana 5.0 插件状态 ===")
    print()
    ok = True

    # 检查 .mcp.json
    if os.path.exists(MCP_JSON):
        print(f"  [OK] .mcp.json: 存在 (6 tools)")
    else:
        print(f"  [!!] .mcp.json: 缺失")
        ok = False

    # 检查 reasonix.toml 插件条目
    toml_path = get_reasonix_toml()
    if os.path.exists(toml_path):
        with open(toml_path, 'r', encoding='utf-8') as f:
            if 'bobanana5' in f.read():
                print(f"  [OK] reasonix.toml: 插件已注册")
            else:
                print(f"  [?] reasonix.toml: 存在但未注册 bobanana5 插件")
                ok = False
    else:
        print(f"  [?] reasonix.toml: 未找到")
        ok = False

    # 检查 MCP 服务器
    mcp_server = os.path.join(PROJECT_DIR, 'mcp_server.py')
    if os.path.exists(mcp_server):
        print(f"  [OK] MCP 服务器: {mcp_server}")
    else:
        print(f"  [!!] MCP 服务器: 缺失")
        ok = False

    # 检查技能
    for skill in ['bobanana', 'pipeline']:
        skill_path = os.path.join(REASONIX_HOME, 'skills', skill, 'SKILL.md')
        print(f"  {'[OK]' if os.path.exists(skill_path) else '[  ]'} skill: {skill}")

    # 检查命令
    for cmd in ['bobanana.md', 'pipeline.md']:
        cmd_path = os.path.join(REASONIX_HOME, 'commands', cmd)
        print(f"  {'[OK]' if os.path.exists(cmd_path) else '[  ]'} command: {cmd}")

    print()
    if ok:
        print("  状态: 全部就绪 ✓")
    else:
        print("  状态: 部分缺失，运行 python plugin_register.py 修复")
    return ok


def remove_plugin():
    """卸载插件"""
    print("=== 卸载 Bobanana 5.0 插件 ===")

    # 从 reasonix.toml 移除
    for toml_path in [get_reasonix_toml(),
                      os.path.join(REASONIX_HOME, 'config.toml')]:
        if os.path.exists(toml_path):
            with open(toml_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            new_lines = []
            skip = False
            for line in lines:
                if 'bobanana5' in line:
                    skip = True
                    continue
                if skip and line.strip().startswith('['):
                    skip = False
                if not skip:
                    new_lines.append(line)
            with open(toml_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  [-] 已从 {toml_path} 移除")

    # 删除 .mcp.json
    for p in [os.path.join(REASONIX_HOME, 'mcp', f'{PLUGIN_NAME}.mcp.json'),
              os.path.join(PROJECT_DIR, '.mcp.json')]:
        if os.path.exists(p):
            os.remove(p)
            print(f"  [-] 已删除 {p}")

    # 删除 skills
    for skill in ['bobanana']:
        skill_dir = os.path.join(REASONIX_HOME, 'skills', skill)
        if os.path.exists(skill_dir):
            shutil.rmtree(skill_dir)
            print(f"  [-] 已删除 skill: {skill}")

    print("  完成")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 Reasonix Plugin Manager')
    parser.add_argument('--check', action='store_true', help='检查安装状态')
    parser.add_argument('--remove', action='store_true', help='卸载插件')
    args = parser.parse_args()

    if args.check:
        check_status()
    elif args.remove:
        remove_plugin()
    else:
        print("=== Bobanana 5.0 Reasonix 插件安装 ===")
        print()
        add_plugin_entry()
        copy_skills_and_commands()
        print()
        print("  安装完成!")
        print("  重启 Reasonix 桌面端后，插件会自动加载。")
        print("  可在 Settings -> Plugins 中查看和管理。")
        print()
        check_status()


if __name__ == '__main__':
    main()
