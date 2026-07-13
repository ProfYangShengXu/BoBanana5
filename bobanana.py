#!/usr/bin/env python3
# @legacy 旧版实现，优先使用角色卡管线替代
# -*- coding: utf-8 -*-
"""Bobanana 5.0 — 仅保留 TUI 仪表盘"""

import sys
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import os
import subprocess

def start_gui():
    subprocess.run([sys.executable, 'gui_dashboard.py'])

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    import argparse
    p = argparse.ArgumentParser(description='Bobanana 5.0')
    p.add_argument('--gui', '-g', action='store_true', help='启动 TUI 仪表盘')
    args = p.parse_args()
    if args.gui:
        start_gui()
    else:
        p.print_help()

if __name__ == '__main__':
    main()
