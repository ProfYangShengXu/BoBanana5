#!/usr/bin/env python3
"""Bobanana 5.0 — SessionStart hook: 检测pending管线 + 强制进目标模式"""

import os
import sys
import json
import subprocess

PROJECT_ROOT = os.getcwd()


def _pending():
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from pipeline_orchestrator import has_pending_pipeline
        return has_pending_pipeline()
    except Exception:
        nf = os.path.join(PROJECT_ROOT, '.reasonix', 'cycle', 'next_prompt.txt')
        sf = os.path.join(PROJECT_ROOT, '.reasonix', 'cycle', 'state.json')
        if os.path.exists(nf) and os.path.exists(sf):
            with open(nf, 'r', encoding='utf-8') as f:
                return len(f.read().strip()) > 0
        return False


def _get_goal():
    """从 cycle state 读取目标"""
    sf = os.path.join(PROJECT_ROOT, '.reasonix', 'cycle', 'state.json')
    if os.path.exists(sf):
        with open(sf, 'r', encoding='utf-8') as f:
            return json.load(f).get('goal', '')
    return ''


def _set_goal_mode(goal):
    """写入 topic 文件 → 触发 Reasonix 目标模式"""
    import hashlib, time
    topic_file = os.path.join(PROJECT_ROOT, '.reasonix', 'desktop-topic-titles.json')
    tid = f"topic_bobanana_c_{int(time.time())}"
    titles = {}
    if os.path.exists(topic_file):
        try:
            with open(topic_file, 'r', encoding='utf-8') as f:
                titles = json.load(f)
            titles = {k: v for k, v in titles.items() if 'bobanana_c_' not in k}
        except:
            pass
    titles[tid] = goal[:120]
    with open(topic_file, 'w', encoding='utf-8') as f:
        json.dump(titles, f, ensure_ascii=False, indent=2)


def main():
    if _pending():
        goal = _get_goal()
        print(f"[Bobanana Hook] 管线进行中，强制进目标模式")
        _set_goal_mode(goal)
        print(f"[Bobanana Hook] 目标: {goal[:80]}...")
        # 调用 pre_boss_check 跳过 Boss 并继续管线
        r = subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, 'scripts', 'pre_boss_check.py')],
                          capture_output=True, text=True, cwd=PROJECT_ROOT)
        for line in r.stdout.strip().split('\n'):
            if line.strip():
                print(f"  > {line.strip()}")
        if r.returncode != 0:
            # fallback: 直接 continue
            r2 = subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, 'pipeline_orchestrator.py'), 'continue'],
                               capture_output=True, text=True, cwd=PROJECT_ROOT)
            for line in r2.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  > {line.strip()}")
    else:
        print("[Bobanana Hook] 无待办管线。/bb <目标> 启动新管线.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
