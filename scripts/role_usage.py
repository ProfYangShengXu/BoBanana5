#!/usr/bin/env python3
"""
Bobanana 5.0 — 角色卡使用追踪器
记录每个角色卡在会话中的使用次数，OP角色调用此数据做低频卡推荐。

用法:
    python scripts/role_usage.py record <role_id>   # 记录一次使用
    python scripts/role_usage.py stats               # 查看统计数据
    python scripts/role_usage.py low-usage            # 列出低频卡
"""

import os, json, datetime

USAGE_FILE = ".reasonix/role_usage.json"


def _ensure():
    os.makedirs(os.path.dirname(USAGE_FILE) or ".", exist_ok=True)
    if not os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "w") as f:
            json.dump({}, f)


def _load():
    _ensure()
    with open(USAGE_FILE, "r") as f:
        return json.load(f)


def _save(data):
    _ensure()
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def record_usage(role_id):
    """记录一个角色卡被使用一次"""
    data = _load()
    if role_id not in data:
        data[role_id] = {"count": 0, "first_used": datetime.datetime.now().isoformat()}
    data[role_id]["count"] += 1
    data[role_id]["last_used"] = datetime.datetime.now().isoformat()
    _save(data)
    return data[role_id]["count"]


def get_stats():
    """获取所有角色使用统计"""
    return _load()


def get_low_usage(threshold=2):
    """获取使用次数低于阈值的角色卡"""
    data = _load()
    low = {k: v for k, v in data.items() if v["count"] < threshold}
    # 加上从未使用过的角色卡
    return low


def cmd_record(args):
    if not args:
        print("[错误] 请指定角色ID")
        return 1
    role_id = args[0]
    count = record_usage(role_id)
    print(f"[OK] {role_id} 使用次数: {count}")
    return 0


def cmd_stats(args):
    data = get_stats()
    if not data:
        print("暂无使用记录")
        return 0
    print(f"{'角色ID':25s} {'次数':6s} {'首次使用':25s} {'最后使用':25s}")
    print("-" * 85)
    for role_id, info in sorted(data.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"{role_id:25s} {info['count']:6d} {info.get('first_used','')[:19]:25s} {info.get('last_used','')[:19]:25s}")
    return 0


def cmd_low_usage(args):
    threshold = int(args[0]) if args else 2
    low = get_low_usage(threshold)
    if not low:
        print(f"所有角色使用次数 >= {threshold}")
        return 0
    print(f"低频角色卡 (使用次数 < {threshold}):")
    for role_id, info in sorted(low.items(), key=lambda x: x[1]["count"]):
        print(f"  {role_id:25s} 已用 {info['count']} 次")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    commands = {"record": cmd_record, "stats": cmd_stats, "low-usage": cmd_low_usage}
    if cmd not in commands:
        print(f"[错误] 未知命令: {cmd}")
        return 1
    return commands[cmd](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
