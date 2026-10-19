#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bobanana 5.0 — Pipeline Dashboard (TUI v2)
UX 优化: 紧凑布局, 彩色, 实时刷新, 一键操作入口
"""

import os
import sys
import json
import time
import shutil
import logging
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):  # 非 TTY/重定向时不存在该方法
    sys.stdout.reconfigure(encoding='utf-8')
from mcp_client import MCPClient

# 布局常量
MIN_TERMINAL_COLS = 40      # 低于此宽度回退到默认列宽
MAX_CONTENT_COLS = 70       # 内容区最大宽度
CONTENT_MARGIN = 4          # 内容区两侧留白
PROGRESS_BAR_WIDTH = 25     # 进度条总格数
PCT_PER_BLOCK = 4           # 每个进度块代表的百分比
CL_PASS_THRESHOLD = 9       # CL 审查通过分数线（满分 10）
DEFAULT_TOTAL_NODES = 11    # 状态机节点数缺失时的兜底值
REFRESH_INTERVAL_SEC = 3

W, COL = shutil.get_terminal_size((80, 24)), MAX_CONTENT_COLS
W = W.columns if W and W.columns > MIN_TERMINAL_COLS else MAX_CONTENT_COLS
COL = min(W - CONTENT_MARGIN, MAX_CONTENT_COLS)

# ── 色 ─────────────────────────────────────
C = {
    'R': '\033[91m', 'G': '\033[92m', 'Y': '\033[93m',
    'B': '\033[94m', 'M': '\033[95m', 'C': '\033[96m',
    'W': '\033[97m', '0': '\033[0m', 'BOLD': '\033[1m',
    'DIM': '\033[2m',
}

def c(code, text):
    return f"{C.get(code, '')}{text}{C['0']}"

def line(char='─'):
    print(c('DIM', char * COL))

def header(title):
    print(f"\n{c('BOLD','')} {title}")
    line()

def badge(tag, active=False):
    colors = {'OP': 'Y', 'CL': 'R', 'HR': 'M', 'EXIT': 'R', 'TEMP': 'M', 'CUR': 'G'}
    col = colors.get(tag, 'B')
    return c(col, f"[{tag}]") if active else c('DIM', f"[{tag}]")

# ── Dashboard ───────────────────────────────

class Dashboard:
    def __init__(self):
        self.client = MCPClient(direct_mode=True)
        self.client.connect()
        self._last_status = ''
        self._refresh_count = 0

    # ── 顶部状态条 ─────────────────────────
    def show_status_bar(self, status, sm):
        current = status.get('current_node', sm.get('current_node', 'idle'))
        done = status.get('completed_count', len(sm.get('completed_nodes', [])))
        total_nodes = len(sm.get('nodes', sm.get('completed_nodes', []))) if sm.get('nodes') else DEFAULT_TOTAL_NODES
        total = max(total_nodes, done + 1)
        phase = status.get('current_phase', 'waiting')
        loops = status.get('loop_count', 0)
        pct = int(done / max(total, 1) * 100)

        bar1 = '█' * (pct // PCT_PER_BLOCK) if pct > 0 else ''
        bar2 = '░' * (PROGRESS_BAR_WIDTH - len(bar1))
        bar = c('G', bar1) + c('DIM', bar2)

        line('═')
        # 第一行: logo + 时间
        print(f" {c('BOLD','Bobanana 5.0')} {c('DIM','|')}  {c('C','●')} MCP Live  "
              f"{c('DIM',datetime.now().strftime('%H:%M:%S'))}"
              f"  {c('DIM',f'refreshing ({self._refresh_count})')}")
        # 第二行: 当前角色 + 阶段
        role_display = c('G' if 'idle' not in str(current) else 'DIM', str(current))
        phase_display = c('Y' if phase != 'waiting' else 'DIM', phase)
        print(f" {c('BOLD','▶')} {role_display}  {c('DIM','phase:')} {phase_display}"
              f"  {c('DIM','loops:')} {loops}")
        # 第三行: 进度条
        print(f" {bar}  {c('BOLD',str(pct))}%  {c('DIM',f'({done}/{total} nodes)')}")
        line('═')

    # ── 状态机图 ──────────────────────────
    def show_sm_graph(self, sm):
        header('State Machine')
        nodes = sm.get('state_machine', {}).get('nodes', [])
        edges = sm.get('state_machine', {}).get('edges', [])
        cur = sm.get('current_node', '')

        # 节点流水线
        flow = ''
        for n in nodes:
            is_cur = n['id'] == cur
            is_exit = n.get('is_exit', False)
            name = n.get('label', n['id'])[:12]
            if is_cur:
                flow += c('G', f"●{name}") + c('DIM', '→')
            elif is_exit:
                flow += c('R', f"○{name}") + c('DIM', '→')
            elif n.get('is_temporary'):
                flow += c('M', f"({name})") + c('DIM', '→')
            else:
                flow += c('DIM', f"○{name}→")
        # 末节点不带箭头，切掉最后一个 '→' 避免悬空
        print(f" {flow[:-1] if flow else c('DIM', 'no nodes')}")
        print(f" {c('DIM',f'{len(nodes)} nodes / {len(edges)} edges')}")

    # ── 角色卡 ────────────────────────────
    def show_roles(self, cards_data):
        header(f'Roles ({cards_data.get("total",0)})')
        cards = cards_data.get('cards', [])
        # 分两列显示
        pairs = []
        for i in range(0, len(cards), 2):
            a = cards[i]
            b = cards[i+1] if i+1 < len(cards) else None
            pairs.append((a, b))

        for a, b in pairs:
            # 字段缺失时退化为占位符，避免 KeyError 中断整个仪表盘
            tag_a = (a.get('tags') or ['-'])[0]
            name_a = a.get('name', '?')[:18]
            tag_b = (b.get('tags') or ['-'])[0] if b else ''
            name_b = b.get('name', '?')[:18] if b else ''
            print(f"  {badge(tag_a,True)} {name_a:20s}  {badge(tag_b,True) if b else ''} {name_b:20s}")

    # ── 管线进度 ──────────────────────────
    def show_pipeline(self, status):
        header('Pipeline')
        pl_id = status.get('pipeline_id', None)
        if pl_id:
            print(f"  ID: {c('DIM',pl_id)}")
        print(f"  Status: {c('G' if status.get('status')=='completed' else 'Y', str(status.get('status','-')))}")

        history = status.get('history', [])
        if history:
            for h in history[-3:]:
                frm = c('Y' if 'boss' in str(h.get('from')) else 'W', h.get('from','?')[:12])
                to = c('G' if h.get('to')=='__terminal__' else 'W',
                       (h.get('to','?') if h.get('to')!='__terminal__' else 'DONE')[:12])
                print(f"  {frm} {c('DIM','→')} {to}  {c('DIM',h.get('phase','')[:20])}")

    # ── CL ─────────────────────────────────
    def show_cl(self, report):
        header('CL Review')
        r = report.get('report')
        if r and r.get('score') is not None:
            s = r['score']
            bar = c('G','█'*s) + c('R','█'*(10-s)) if s < CL_PASS_THRESHOLD else c('G','█'*s)
            verdict = c('G','PASS') if s >= CL_PASS_THRESHOLD else c('R','FAIL')
            print(f"  Score: {c('BOLD',str(s))}/10  {bar}  {verdict}")
        else:
            print(f"  {c('DIM','No CL report yet')}")

    # ── 交接工单 ──────────────────────────
    def show_handoff(self, tickets_data):
        header('Handoff')
        tickets = tickets_data.get('tickets', [])
        if tickets:
            for t in tickets[:3]:
                s = c('Y', t.get('sender_id','?')[:12])
                r = c('C', t.get('receiver_id','?')[:12])
                print(f"  {s} {c('DIM','→')} {r}  v{t.get('version',1)}")
        else:
            print(f"  {c('DIM','No handoff tickets')}")

    # ── 完整仪表盘 ────────────────────────
    def show_all(self):
        self._refresh_count += 1
        # 任一远端调用返回 None 时统一退化为空字典，避免下游 .get() 崩溃
        sm = self.client.get_state_machine() or {}
        status = self.client.get_pipeline_status() or {}
        cards = self.client.get_role_cards() or {}
        cl = self.client.get_cl_report() or {}
        tickets = self.client.get_handoff_tickets() or {}

        self.show_status_bar(status, sm)
        self.show_sm_graph(sm)
        self.show_roles(cards)
        self.show_pipeline(status)
        self.show_cl(cl)
        self.show_handoff(tickets)
        print()
        print(f"  {c('DIM','/bb <goal>  |  Ctrl+C exit')}")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--json', '-j', action='store_true')
    p.add_argument('--recruit', '-r', help='HR recruit')
    args = p.parse_args()

    dash = Dashboard()
    if args.json:
        print(json.dumps(dash.client.full_dashboard_data(), ensure_ascii=False, indent=2))
        return
    if args.recruit:
        r = dash.client.trigger_hr_recruit(args.recruit, args.recruit)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    try:
        while True:
            print('\n' * 2 + f'=== Refresh #{dash._refresh_count} ===')
            try:
                dash.show_all()
            except Exception as e:  # 单帧渲染失败不应终止轮询
                logging.warning("Dashboard render error: %s", e)
            time.sleep(REFRESH_INTERVAL_SEC)
    except KeyboardInterrupt:
        print('\nBye!')
    except Exception as e:
        logging.warning("Dashboard fatal error: %s", e)
        input('\nPress Enter to exit...')
    finally:
        dash.client.disconnect()


if __name__ == '__main__':
    main()
