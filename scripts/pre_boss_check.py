#!/usr/bin/env python3
"""Boss 前置检查：有pending管线时强制设目标模式"""
import os, sys, json

CYCLE_DIR = '.reasonix/cycle'
TOPIC_FILE = '.reasonix/desktop-topic-titles.json'

def has_pending():
    nf = os.path.join(CYCLE_DIR, 'next_prompt.txt')
    sf = os.path.join(CYCLE_DIR, 'state.json')
    if os.path.exists(nf) and os.path.exists(sf):
        with open(nf, 'r', encoding='utf-8') as f:
            return len(f.read().strip()) > 0
    return False

def get_pending_goal():
    sf = os.path.join(CYCLE_DIR, 'state.json')
    with open(sf, 'r', encoding='utf-8') as f:
        return json.load(f).get('goal', '')

def set_goal_mode(goal):
    """写入 topic 文件触发 Reasonix 目标模式"""
    import hashlib, time
    topic_id = f"topic_bobanana_{int(time.time())}"
    titles = {}
    if os.path.exists(TOPIC_FILE):
        try:
            with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
                titles = json.load(f)
            # 清理旧 bobanana topics
            titles = {k: v for k, v in titles.items() if 'bobanana_' not in k}
        except: pass
    titles[topic_id] = goal[:120]
    os.makedirs('.reasonix', exist_ok=True)
    with open(TOPIC_FILE, 'w', encoding='utf-8') as f:
        json.dump(titles, f, ensure_ascii=False, indent=2)
    return topic_id

if __name__ == '__main__':
    if has_pending():
        goal = get_pending_goal()
        print(f"[SKIP] 管线未完成，强制进目标模式")
        print(f"[GOAL] {goal[:80]}...")
        set_goal_mode(goal)
        import subprocess
        result = subprocess.run([sys.executable, 'pipeline_orchestrator.py', 'continue'],
                               capture_output=True, text=True, cwd=os.getcwd())
        for line in result.stdout.strip().split('\n'):
            if line.strip(): print(f"  > {line.strip()}")
        sys.exit(0 if result.returncode == 0 else 1)
    else:
        sys.exit(1)
