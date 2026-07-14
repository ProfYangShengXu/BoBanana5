#!/usr/bin/env python3
"""
Bobanana 5.0 — 嵌入式工具集 CLI 入口
自动检测工具安装路径，提供统一的 CLI 接口。

用法:
    python tools.py cubemx --gui
    python tools.py keil5 --build project.uvprojx
    python tools.py jlink --flash STM32F103C8 firmware.hex
"""

import os
import sys
import subprocess
import glob

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))


def find_exe(names, paths=None):
    """查找可执行文件"""
    if paths is None:
        paths = [
            os.environ.get('PROGRAMFILES', 'C:/Program Files'),
            os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)'),
            os.environ.get('LOCALAPPDATA', ''),
            'C:/Keil_v5', 'C:/Keil',
        ]
    # 先检查 PATH
    for name in names:
        try:
            r = subprocess.run(['where', name], capture_output=True, text=True)
            if r.returncode == 0:
                return r.stdout.strip().split('\n')[0]
        except: pass
    # 再搜索常见路径
    for root in paths:
        if not root: continue
        for name in names:
            for p in glob.glob(os.path.join(root, '**', name), recursive=True):
                if os.path.isfile(p):
                    return p
    return None


def cmd_cubemx(args):
    exe = find_exe(['STM32CubeMX.exe', 'STM32CubeMX'])
    if not exe:
        print("[!] STM32CubeMX 未安装")
        print("    下载: https://www.st.com/stm32cubemx")
        return 1
    print(f"[OK] CubeMX: {exe}")
    if '--gui' in args or '-g' in args:
        subprocess.Popen([exe])
        print("[OK] GUI 已启动")
        return 0
    ioc = None
    for a in args:
        if a.endswith('.ioc'):
            ioc = a; break
    if ioc:
        subprocess.run([exe, '-q', ioc])
        return 0
    print("用法: cubemx --gui 或 cubemx project.ioc")
    return 1


def cmd_keil5(args):
    exe = find_exe(['UV4.exe', 'UV4'])
    if not exe:
        print("[!] Keil MDK 未安装")
        print("    下载: https://www.keil.com/download/")
        return 1
    print(f"[OK] UV4: {exe}")
    proj = None
    action = '-r'  # 默认编译
    for a in args:
        if a.endswith('.uvprojx') or a.endswith('.uvproj'):
            proj = a
        elif a in ('-b', '--build'): action = '-r'
        elif a in ('-c', '--clean'): action = '-f'
    if proj:
        subprocess.run([exe, action, proj, '-j0'])
        return 0
    print("用法: keil5 --build project.uvprojx")
    return 1


def cmd_jlink(args):
    exe = find_exe(['JLink.exe', 'JLink'])
    if not exe:
        print("[!] JLink 未安装")
        print("    下载: https://www.segger.com/downloads/jlink/")
        return 1
    print(f"[OK] JLink: {exe}")
    if '--rtt' in args or '-rtt' in args:
        rtt = find_exe(['JLinkRTTViewer.exe'])
        if rtt: subprocess.Popen([rtt])
        return 0
    if '--gdb' in args or '-gdb' in args:
        device = _get_arg(args, ('--gdb', '-gdb'))
        subprocess.Popen([exe.replace('JLink.exe','JLinkGDBServer.exe'), '-device', device or 'STM32F103C8', '-if', 'SWD'])
        return 0
    if '--flash' in args or '-flash' in args:
        parts = args[args.index('--flash' if '--flash' in args else '-flash')+1:]
        device = parts[0] if len(parts) > 0 else 'STM32F103C8'
        hex_file = parts[1] if len(parts) > 1 else None
        if not hex_file or not os.path.exists(hex_file):
            print(f"[!] 固件文件不存在: {hex_file}")
            return 1
        script = f'loadfile {hex_file}\nr\ng\nexit\n'
        sp = os.path.join(os.environ.get('TEMP','/tmp'), 'jlink_cmd.txt')
        with open(sp, 'w') as f: f.write(script)
        subprocess.run([exe, '-device', device, '-if', 'SWD', '-speed', '4000', '-autoconnect', '1', '-CommanderScript', sp])
        return 0
    print("用法: jlink --flash DEVICE file.hex")
    return 1


def _get_arg(args, keys):
    for i, a in enumerate(args):
        if a in keys and i+1 < len(args):
            return args[i+1]
    return None


CMDS = {
    'cubemx': cmd_cubemx,
    'keil5': cmd_keil5,
    'jlink': cmd_jlink,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        sys.exit(1)
    sys.exit(CMDS[sys.argv[1]](sys.argv[2:]))
