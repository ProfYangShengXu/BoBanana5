#!/usr/bin/env python3
"""
Bobanana 5.0 — 修复已安装的插件
修复插件包中的路径和 missing file 问题。
"""

import os, json, shutil

# 已安装的插件路径（Reasonix 桌面端使用的）
INSTALLED_DIR = os.path.expandvars(r'%APPDATA%\reasonix\plugins\bobanana5')
# 项目中的插件源
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(PROJECT_DIR, 'bobanana-plugin')


def fix_installed_plugin():
    if not os.path.exists(INSTALLED_DIR):
        print(f"  [!] 未找到已安装的插件: {INSTALLED_DIR}")
        print(f"  [!] 请先在 Reasonix 桌面端安装插件")
        print(f"       Settings -> Plugins -> Install Plugin -> 选择 {SOURCE_DIR}")
        return False

    print(f"  已安装插件目录: {INSTALLED_DIR}")

    # 1. 修复 manifest - 去掉 contextFile 引用
    manifest_path = os.path.join(INSTALLED_DIR, 'reasonix-plugin.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # 清理 hooks 中的 contextFile
        for hook_list in manifest.get('hooks', {}).values():
            for hook in hook_list:
                hook.pop('contextFile', None)
        
        # 修复 MCP 服务器命令为绝对路径
        for server in manifest.get('mcpServers', {}).values():
            if server.get('command') == 'python':
                server['command'] = 'cmd.exe'
                server['args'] = ['/c', 'cd', '/d', PROJECT_DIR, '&&', 'python', '-m', 'mcp_server']
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"  [+] manifest 已修复")

    else:
        print(f"  [!] manifest 不存在")
        return False

    # 2. 复制 README.quick.md（如果 reference 还存在）
    readme_src = os.path.join(PROJECT_DIR, 'README.quick.md')
    readme_dst = os.path.join(INSTALLED_DIR, 'README.quick.md')
    if os.path.exists(readme_src):
        shutil.copy2(readme_src, readme_dst)
        print(f"  [+] README.quick.md 已复制")
    
    # 3. 复制更新后的 skills 和 commands
    for item in ['skills', 'commands']:
        src = os.path.join(SOURCE_DIR, item)
        dst = os.path.join(INSTALLED_DIR, item)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  [+] {item} 已更新")

    print(f"\n  修复完成！请重启 Reasonix 桌面端。")
    return True


if __name__ == '__main__':
    print("=== Bobanana 5.0 插件修复 ===")
    print()
    fix_installed_plugin()
    print()
    input("  按回车退出...")
