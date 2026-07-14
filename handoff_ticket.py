#!/usr/bin/env python3
"""
Bobanana 5.0 — Handoff Ticket System
交接工单系统：版本化的结构化上下文传递机制。

用法:
    python handoff_ticket.py create <sender> <receiver>    # 创建工单
    python handoff_ticket.py get <ticket_id>                # 获取工单
    python handoff_ticket.py list [--role <name>]           # 列出工单
    python handoff_ticket.py status                         # 系统状态
"""

import os
import sys
import json
import time
import logging
from datetime import datetime


HANDOFF_DIR = ".reasonix/handoffs"


def _ensure_dir():
    os.makedirs(HANDOFF_DIR, exist_ok=True)


def _ticket_path(ticket_id):
    return os.path.join(HANDOFF_DIR, f"{ticket_id}.json")


def _next_version(role_name):
    """使用毫秒时间戳作为版本号，避免 O(n) 全目录扫描"""
    return int(time.time() * 1000)


def create_handoff_ticket(sender_id, receiver_id, artifacts=None, pending_decisions=None,
                          assumptions=None, risks=None, references=None):
    """创建交接工单"""
    version = _next_version(sender_id)
    ticket_id = f"ht-{sender_id}-v{version}-{int(time.time())}"

    ticket = {
        "ticket_id": ticket_id,
        "version": version,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "created_at": datetime.now().isoformat(),
        "artifacts": artifacts or [],
        "pending_decisions": pending_decisions or [],
        "assumptions": assumptions or [],
        "risks": risks or [],
        "references": references or {},
    }

    _ensure_dir()
    with open(_ticket_path(ticket_id), 'w', encoding='utf-8') as f:
        json.dump(ticket, f, ensure_ascii=False, indent=2)

    return ticket


def get_handoff_ticket(ticket_id):
    """获取指定工单"""
    path = _ticket_path(ticket_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_handoff_tickets(role_name=None, limit=20):
    """列出工单，可选按角色过滤"""
    _ensure_dir()
    tickets = []
    for f in os.listdir(HANDOFF_DIR):
        if f.endswith('.json'):
            try:
                with open(os.path.join(HANDOFF_DIR, f), 'r', encoding='utf-8') as fh:
                    ticket = json.load(fh)
                if role_name and ticket.get('sender_id') != role_name and ticket.get('receiver_id') != role_name:
                    continue
                tickets.append(ticket)
            except (FileNotFoundError, json.JSONDecodeError):
                logging.warning("跳过损坏的工单文件: %s", f)

    # 按创建时间降序
    tickets.sort(key=lambda t: t.get('created_at', ''), reverse=True)
    return tickets[:limit]


def get_latest_for_role(role_name):
    """获取某个角色的最新工单（作为接收者或发送者）"""
    tickets = list_handoff_tickets(role_name=role_name, limit=1)
    return tickets[0] if tickets else None


def cmd_create(args):
    ticket = create_handoff_ticket(
        sender_id=args.sender,
        receiver_id=args.receiver,
        artifacts=[a for a in args.artifacts.split(',') if a] if args.artifacts else [],
        pending_decisions=[d for d in args.decisions.split(',') if d] if args.decisions else [],
        assumptions=[a for a in args.assumptions.split(',') if a] if args.assumptions else [],
    )
    print(f"工单创建: {ticket['ticket_id']}")
    print(f"  发送者:   {ticket['sender_id']}")
    print(f"  接收者:   {ticket['receiver_id']}")
    print(f"  版本:     v{ticket['version']}")
    print(f"  时间:     {ticket['created_at']}")
    return 0


def cmd_get(args):
    ticket = get_handoff_ticket(args.ticket_id)
    if not ticket:
        print(f"工单不存在: {args.ticket_id}")
        return 1
    print(json.dumps(ticket, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args):
    tickets = list_handoff_tickets(role_name=args.role)
    if not tickets:
        print("(空)")
        return 0
    for t in tickets:
        artifacts = ', '.join(t.get('artifacts', [])[:2])
        if len(t.get('artifacts', [])) > 2:
            artifacts += '...'
        print(f"  {t['ticket_id']:40s} v{t['version']}  {t['sender_id']:15s} -> {t['receiver_id']:15s}  {artifacts}")
    print(f"\n共 {len(tickets)} 张工单")
    return 0


def cmd_status(args):
    _ensure_dir()
    count = len([f for f in os.listdir(HANDOFF_DIR) if f.endswith('.json')]) if os.path.exists(HANDOFF_DIR) else 0
    print(f"工单目录: {HANDOFF_DIR}")
    print(f"工单总数: {count}")
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 Handoff Ticket System')
    sub = parser.add_subparsers(dest='command')

    p_c = sub.add_parser('create', help='创建交接工单')
    p_c.add_argument('sender', help='发送者角色名')
    p_c.add_argument('receiver', help='接收者角色名')
    p_c.add_argument('--artifacts', '-a', default='', help='产出物列表（逗号分隔）')
    p_c.add_argument('--decisions', '-d', default='', help='未决决策列表（逗号分隔）')
    p_c.add_argument('--assumptions', '-s', default='', help='显式假设列表（逗号分隔）')

    p_g = sub.add_parser('get', help='获取工单')
    p_g.add_argument('ticket_id', help='工单 ID')

    p_l = sub.add_parser('list', help='列出工单')
    p_l.add_argument('--role', '-r', help='按角色过滤')

    sub.add_parser('status', help='系统状态')

    args = parser.parse_args()

    if args.command == 'create':
        return cmd_create(args)
    elif args.command == 'get':
        return cmd_get(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'status':
        return cmd_status(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
