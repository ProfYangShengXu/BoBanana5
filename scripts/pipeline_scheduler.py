#!/usr/bin/env python3
"""
Bobanana 5.0 — 可编程定时任务调度器
定时启动主管线执行自动化任务。

用法:
    python scripts/pipeline_scheduler.py run --goal "每日数据更新"           # 立即执行一次
    python scripts/pipeline_scheduler.py schedule --goal "周报生成" --time "09:00" --weekday mon-fri  # 定时任务
    python scripts/pipeline_scheduler.py list                                  # 列出已注册任务
    python scripts/pipeline_scheduler.py remove <task-id>                      # 删除任务

Windows Task Scheduler:
    python scripts/pipeline_scheduler.py install-winsch                        # 安装到 Windows 任务计划程序
"""

import os, sys, json, time, datetime, logging, subprocess, argparse, hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('scheduler')

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.reasonix', 'scheduler')
TASKS_FILE = os.path.join(CONFIG_DIR, 'tasks.json')
LOG_DIR = os.path.join(CONFIG_DIR, 'logs')


def _ensure():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def _load_tasks():
    _ensure()
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"加载任务失败: {e}")
        return []


def _save_tasks(tasks):
    _ensure()
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"保存任务失败: {e}")


def _task_id(goal):
    return hashlib.md5(goal.encode()).hexdigest()[:8]


def cmd_run(args):
    """立即执行管线"""
    goal = args.goal
    rounds = getattr(args, 'rounds', 1)
    tid = _task_id(goal)
    logger.info(f"[{tid}] 启动管线: {goal[:50]} (rounds={rounds})")

    # 执行 pipeline init
    init_cmd = [sys.executable, '-m', 'pipeline_orchestrator', 'init', goal]
    if rounds != 1:
        init_cmd.extend(['--rounds', str(rounds)])

    r = subprocess.run(init_cmd, capture_output=True, text=True,
                       cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    logger.info(f"  init: {r.stdout.strip()[:100]}")

    # 记录日志
    log_entry = {
        "task_id": tid, "goal": goal, "rounds": rounds,
        "started_at": datetime.datetime.now().isoformat(),
        "status": "started",
        "output": r.stdout.strip()[:500],
    }
    with open(os.path.join(LOG_DIR, f"{tid}_{int(time.time())}.json"), 'w') as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    return 0


def cmd_schedule(args):
    """注册定时任务"""
    tasks = _load_tasks()
    tid = _task_id(args.goal)
    task = {
        "id": tid,
        "goal": args.goal,
        "rounds": getattr(args, 'rounds', 1),
        "time": args.time,
        "weekday": args.weekday or "*",
        "enabled": True,
        "created_at": datetime.datetime.now().isoformat(),
    }
    # 替换同名任务
    tasks = [t for t in tasks if t['id'] != tid]
    tasks.append(task)
    _save_tasks(tasks)
    logger.info(f"[{tid}] 定时任务已注册: {args.time} {args.weekday or '每天'} → {args.goal[:50]}")

    if sys.platform == 'win32':
        _install_winsch_task(task)
    return 0


def cmd_list(args):
    """列出所有任务"""
    tasks = _load_tasks()
    if not tasks:
        print("暂无定时任务")
        return 0
    print(f"{'ID':10s} {'目标':30s} {'时间':10s} {'周期':15s} {'状态':8s}")
    print("-" * 75)
    for t in tasks:
        status = "✅" if t.get("enabled", True) else "❌"
        print(f"{t['id']:10s} {t['goal'][:28]:30s} {t.get('time',''):10s} {t.get('weekday','*'):15s} {status:8s}")
    return 0


def cmd_remove(args):
    """删除任务"""
    tasks = _load_tasks()
    before = len(tasks)
    tasks = [t for t in tasks if t['id'] != args.task_id]
    _save_tasks(tasks)
    if len(tasks) < before:
        logger.info(f"已删除任务: {args.task_id}")
    else:
        logger.warning(f"未找到任务: {args.task_id}")
    return 0


def cmd_install_winsch(args):
    """安装所有任务到 Windows Task Scheduler"""
    tasks = _load_tasks()
    if not tasks:
        logger.warning("没有已注册的任务")
        return 1

    script_path = os.path.abspath(__file__)
    python_path = sys.executable

    for t in tasks:
        _install_winsch_task(t)
    logger.info(f"已安装 {len(tasks)} 个任务到 Windows 任务计划程序")
    return 0


def _install_winsch_task(task):
    """安装单个任务到 Windows Task Scheduler"""
    if sys.platform != 'win32':
        logger.warning("仅支持 Windows 任务计划程序")
        return

    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    task_name = f"Bobanana5_{task['id']}"
    action = f'"{python_path}" "{script_path}" run --goal "{task["goal"]}" --rounds {task["rounds"]}'

    # 构造 schtasks 命令
    time_parts = task['time'].split(':')
    hour = time_parts[0]
    minute = time_parts[1] if len(time_parts) > 1 else "00"

    weekday_map = {
        "mon-fri": "MON,TUE,WED,THU,FRI",
        "weekend": "SAT,SUN",
        "daily": "*",
        "mon": "MON", "tue": "TUE", "wed": "WED",
        "thu": "THU", "fri": "FRI", "sat": "SAT", "sun": "SUN",
    }
    days = weekday_map.get(task.get('weekday', '*'), task.get('weekday', '*'))

    cmd = [
        'schtasks', '/create', '/tn', task_name, '/tr', action,
        '/sc', 'daily', '/st', f"{hour}:{minute}",
        '/f'
    ]
    if days != '*':
        cmd.extend(['/d', days])

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        logger.info(f"  [WinSched] {task_name}: {task['time']} {days} → {task['goal'][:40]}")
    else:
        logger.warning(f"  [WinSched] 安装失败: {r.stderr[:100]}")


def main():
    parser = argparse.ArgumentParser(description="Bobanana 5.0 定时任务调度器")
    sub = parser.add_subparsers(dest='command')

    p_run = sub.add_parser('run', help='立即执行管线')
    p_run.add_argument('--goal', required=True, help='管线目标')
    p_run.add_argument('--rounds', '-r', type=int, default=1, help='轮数')

    p_sch = sub.add_parser('schedule', help='注册定时任务')
    p_sch.add_argument('--goal', required=True, help='管线目标')
    p_sch.add_argument('--time', required=True, help='执行时间 (HH:MM)')
    p_sch.add_argument('--weekday',
        choices=['mon-fri', 'weekend', 'daily', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
        default='daily')
    p_sch.add_argument('--rounds', '-r', type=int, default=1)

    sub.add_parser('list', help='列出任务')
    sub.add_parser('install-winsch', help='安装到 Windows 任务计划程序')

    p_rm = sub.add_parser('remove', help='删除任务')
    p_rm.add_argument('task_id', help='任务 ID')

    args = parser.parse_args()
    if args.command == 'run':
        return cmd_run(args)
    elif args.command == 'schedule':
        return cmd_schedule(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'remove':
        return cmd_remove(args)
    elif args.command == 'install-winsch':
        return cmd_install_winsch(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
