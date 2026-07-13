#!/usr/bin/env python3
# @legacy 旧版实现，优先使用角色卡管线替代
# -*- coding: utf-8 -*-
"""
Bobanana 5.0 — Pipeline Dashboard (TUI v2)
UX 优化: 紧凑布局, 彩色, 实时刷新, 一键操作入口
"""

import os, sys, json, time, shutil
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
from mcp_client import MCPClient

W, COL = shutil.get_terminal_size((80, 24)), 70
W = W.columns if W and W.columns > 40 else 70
COL = min(W - 4, 70)

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
        total_nodes = len(sm.get('nodes', sm.get('completed_nodes', []))) if sm.get('nodes') else 11
        total = max(total_nodes, done + 1)
        phase = status.get('current_phase', 'waiting')
        loops = status.get('loop_count', 0)
        pct = int(done / max(total, 1) * 100)

        bar1 = '█' * (pct // 4) if pct > 0 else ''
        bar2 = '░' * (25 - len(bar1))
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
        for i, n in enumerate(nodes):
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
        print(f" {flow[:-1]}")
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
            tag_a = (a.get('tags') or ['-'])[0]
            name_a = a['name'][:18]
            tag_b = (b.get('tags') or ['-'])[0] if b else ''
            name_b = b['name'][:18] if b else ''
            mid = 38
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
                to = c('G' if h.get('to')=='__terminal__' else 'W', (h.get('to','?') if h.get('to')!='__terminal__' else 'DONE')[:12])
                print(f"  {frm} {c('DIM','→')} {to}  {c('DIM',h.get('phase','')[:20])}")

    # ── CL ─────────────────────────────────
    def show_cl(self, report):
        header('CL Review')
        r = report.get('report')
        if r and r.get('score') is not None:
            s = r['score']
            bar = c('G','█'*s) + c('R','█'*(10-s)) if s < 9 else c('G','█'*s)
            verdict = c('G','PASS') if s >= 9 else c('R','FAIL')
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
        sm = self.client.get_state_machine()
        status = self.client.get_pipeline_status()
        cards = self.client.get_role_cards()
        cl = self.client.get_cl_report()
        tickets = self.client.get_handoff_tickets()

        self.show_status_bar(status, sm)
        self.show_sm_graph(sm)
        self.show_roles(cards)
        self.show_pipeline(status)
        self.show_cl(cl)
        self.show_handoff(tickets)
        print()
        print(f"  {c('DIM','/bobanana <goal>  |  Ctrl+C exit')}")


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
            except Exception as e:
                import logging
                logging.warning("Dashboard render error: %s", e)
            time.sleep(3)
    except KeyboardInterrupt:
        print('\nBye!')
    except Exception as e:
        import logging
        logging.warning("Dashboard fatal error: %s", e)
        input('\nPress Enter to exit...')
    finally:
        dash.client.disconnect()


if __name__ == '__main__':
    main()
