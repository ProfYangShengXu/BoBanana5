#!/usr/bin/env python3
"""Bobanana 5.0 — SessionStart hook (plugin版): 检测pending + 强制目标模式"""

import os
import sys
import json
import subprocess

PROJECT_ROOT = os.getcwd()


def _pending():
    nf = os.path.join(PROJECT_ROOT, '.reasonix', 'cycle', 'next_prompt.txt')
    sf = os.path.join(PROJECT_ROOT, '.reasonix', 'cycle', 'state.json')
    if os.path.exists(nf) and os.path.exists(sf):
        with open(nf, 'r', encoding='utf-8') as f:
            return len(f.read().strip()) > 0
    return False


def _get_goal():
    sf = os.path.join(PROJECT_ROOT, '.reasonix', 'cycle', 'state.json')
    if os.path.exists(sf):
        with open(sf, 'r', encoding='utf-8') as f:
            return json.load(f).get('goal', '')
    return ''


def _set_goal_mode(goal):
    import time
    tf = os.path.join(PROJECT_ROOT, '.reasonix', 'desktop-topic-titles.json')
    tid = f"topic_bobanana_p_{int(time.time())}"
    titles = {}
    if os.path.exists(tf):
        try:
            with open(tf, 'r', encoding='utf-8') as f:
                titles = json.load(f)
            titles = {k: v for k, v in titles.items() if 'bobanana_p_' not in k}
        except (json.JSONDecodeError, KeyError):
            pass
    titles[tid] = goal[:120]
    with open(tf, 'w', encoding='utf-8') as f:
        json.dump(titles, f, ensure_ascii=False, indent=2)


def main():
    if _pending():
        goal = _get_goal()
        print(f"[Bobanana Hook] 管线进行中，强制进目标模式")
        _set_goal_mode(goal)
        r = subprocess.run([sys.executable, os.path.join(PROJECT_ROOT, 'pipeline_orchestrator.py'), 'continue'],
                          capture_output=True, text=True, cwd=PROJECT_ROOT)
        for line in r.stdout.strip().split('\n'):
            if line.strip(): print(f"  > {line.strip()}")
    else:
        print("[Bobanana Hook] 就绪。/bb <目标> 启动新管线.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
