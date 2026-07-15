#!/usr/bin/env python3
"""
Bobanana 5.0 — Pipeline Orchestrator
管线编排器：整合 M1-M5，驱动完整管线流程 OP -> 技术链 -> CL。

用法:
    python pipeline_orchestrator.py init <goal>                    # 初始化管线
    python pipeline_orchestrator.py status [--pipeline <id>]       # 管线状态
    python pipeline_orchestrator.py advance <phase> [--score N]   # 推进管线
    python pipeline_orchestrator.py list                           # 列出管线
"""

import os
import sys
import json
import logging
import time
import yaml
from datetime import datetime

CL_PASS_THRESHOLD = 9
PIPELINE_DIR = ".reasonix/pipelines"
CYCLE_DIR = ".reasonix/cycle"
STATE_MACHINE_DIR = ".reasonix/state"
STATE_MACHINE_PATH = "state-machine.yaml"


def _ensure_dirs():
    os.makedirs(PIPELINE_DIR, exist_ok=True)


def _pipeline_path(pid):
    return os.path.join(PIPELINE_DIR, f"{pid}.json")


def _next_pipeline_id():
    return f"pl-{int(time.time())}"


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_pipeline(goal, rounds=3):
    """初始化新管线 (rounds: 多轮循环次数，默认3轮)"""
    # 安全检查：如果有未完成管线，拒绝创建新管线
    if has_pending_pipeline():
        print("[!] 管线进行中，不能创建新管线！")
        print("    请先完成: python pipeline_orchestrator.py continue")
        return None
    state_path = os.path.join(STATE_MACHINE_DIR, 'machine_state.json')
    if os.path.exists(state_path):
        import json as _j
        with open(state_path, 'r', encoding='utf-8') as _f:
            try:
                _s = _j.load(_f)
                if _s.get('current_node') != '__terminal__':
                    print("[!] 状态机引擎中有未完成管线！")
                    print("   请先完成: python pipeline_orchestrator.py continue")
                    return None
            except Exception as e:
                logging.warning("读取 machine_state.json 失败: %s", e)

    pid = _next_pipeline_id()
    _ensure_dirs()

    # 框架约束（不污染用户目标字段）
    constraints = {"exit_criteria": "CL终审(score>=9)"}

    pipeline = {
        "pipeline_id": pid,
        "goal": goal,
        "constraints": constraints,
        "status": "initialized",
        "current_node": "boss",
        "current_phase": "start",
        "completed_nodes": [],
        "failed_count": 0,
        "loop_count": 0,
        "max_loops": 50,
        "emergency_hirings": 0,
        "max_hirings": 3,
        "started_at": datetime.now().isoformat(),
        "history": [],
        "round": 1,
        "max_rounds": rounds,
        "cl_score": None,
        "cl_report": None,
    }

    save_json(_pipeline_path(pid), pipeline)

    from handoff_ticket import create_handoff_ticket
    create_handoff_ticket("system", "architect",
                          artifacts=["state-machine.yaml"],
                          pending_decisions=[goal])

    import hashlib
    _cd = CYCLE_DIR
    os.makedirs(_cd, exist_ok=True)
    with open(os.path.join(_cd, 'state.json'), 'w', encoding='utf-8') as _f:
        json.dump({"goal": goal,
               "goal_hash": hashlib.sha256(goal.encode()).hexdigest()[:64],
               "phase": "init", "iteration": 0, "max_iterations": 50,
               "next_prompt": "", "summary": "pipeline initialized",
               "last_updated": datetime.now().isoformat()},
               _f, ensure_ascii=False, indent=2)

    print(f"管线已初始化: {pid}")
    print(f"  目标: {goal}")
    print(f"  入口: {pipeline['current_node']}")
    return pipeline


def get_pipeline(pid=None):
    """获取管线状态"""
    if pid:
        path = _pipeline_path(pid)
        if not os.path.exists(path):
            return None
        return load_json(path)

    # 获取最新管线
    pipelines = list_pipelines()
    if not pipelines:
        return None
    return pipelines[0]


def run_cl_review(pipeline_id, score, context=None):
    """
    Badcase M4-A2 修复: CL 隔离 subagent 审查。
    创建一个隔离的审查上下文（模拟全新 subagent，不继承 pipeline 历史）。
    """
    pipeline = get_pipeline(pipeline_id)
    if not pipeline:
        print("管线不存在")
        return None

    # 隔离上下文：创建一个新的上下文快照，不包含 history 和中间状态
    isolated_context = {
        "pipeline_id": pipeline["pipeline_id"],
        "goal": pipeline["goal"],
        "completed_nodes": list(pipeline.get("completed_nodes", [])),
        "score": score,
        "reviewed_at": datetime.now().isoformat(),
        "is_isolated": True,  # 标记为隔离审查
    }

    # 更新管线中的 CL 报告
    pipeline["cl_report"] = isolated_context
    pipeline["cl_score"] = score
    save_json(_pipeline_path(pipeline_id), pipeline)

    # 输出隔离审查的工单
    from handoff_ticket import create_handoff_ticket
    status = "passed" if score >= CL_PASS_THRESHOLD else "failed"
    create_handoff_ticket(
        "client-gate(隔离审查)",
        "system",
        artifacts=[f"CL review score: {score}/10"],
        pending_decisions=[],
        assumptions=[f"隔离审查完成，状态: {status}"],
    )

    print(f"CL 隔离审查完成:")
    print(f"  管线:      {pipeline_id}")
    print(f"  分数:      {score}/10")
    print(f"  已完成节点: {len(isolated_context['completed_nodes'])} 个")
    print(f"  审查时间:  {isolated_context['reviewed_at']}")
    print(f"  结果:      {'通过' if score >= CL_PASS_THRESHOLD else '打回给 OP 角色'}")

    return isolated_context


def handle_cl_failback(pipeline_id, cl_report=None):
    """
    Badcase M6-A3 修复: CL 打回逻辑。
    CL 分数 < 9 时打回给最近的 OP 角色，并附带审查报告。
    """
    pipeline = get_pipeline(pipeline_id)
    if not pipeline:
        print("管线不存在")
        return None

    score = pipeline.get("cl_score", 0) if cl_report is None else cl_report.get("score", 0)

    if score >= CL_PASS_THRESHOLD:
        print(f"CL 分数 {score} >= {CL_PASS_THRESHOLD}，不触发打回")
        return {"failback": False, "reason": "Score sufficient"}

    # 生成打回工单
    from handoff_ticket import create_handoff_ticket
    report = cl_report or pipeline.get("cl_report", {})
    ticket = create_handoff_ticket(
        "client-gate",
        "architect",
        artifacts=[f"CL score: {score}/10"],
        pending_decisions=[
            f"CL 审查未通过 (score={score}/10)",
            "需要重新规划管线修复问题",
        ],
        assumptions=["架构师(OP)角色需重新编排状态机"],
    )

    # 更新管线状态：回退到架构师节点
    pipeline["current_node"] = "architect"
    pipeline["current_phase"] = "cl-failback"
    pipeline["status"] = "failback_to_architect"
    pipeline["failed_count"] += 1
    pipeline["history"].append({
        "from": "client-gate",
        "to": "architect",
        "phase": "cl-done_fail",
        "timestamp": datetime.now().isoformat(),
        "reason": f"CL score {score}/10 < 9",
    })
    save_json(_pipeline_path(pipeline_id), pipeline)

    print(f"CL 打回触发:")
    print(f"  分数:      {score}/10 (< 9)")
    print(f"  目标角色:  architect (OP)")
    print(f"  工单:      {ticket['ticket_id']}")
    print(f"  失败计数:  {pipeline['failed_count']}")

    return {
        "failback": True,
        "target_role": "architect",
        "target_phase": "cl-failback",
        "ticket_id": ticket["ticket_id"],
        "score": score,
    }


def has_pending_pipeline():
    """检查是否有未完成的管线（以 pipeline.json 为权威源）"""
    if not os.path.isdir(PIPELINE_DIR):
        return False
    pl_files = [f for f in os.listdir(PIPELINE_DIR) if f.endswith('.json')]
    for f in sorted(pl_files, reverse=True):
        try:
            with open(os.path.join(PIPELINE_DIR, f), 'r', encoding='utf-8') as fh:
                pl = json.load(fh)
            if pl.get('status') == 'completed':
                continue
            if pl.get('current_node') == '__terminal__':
                continue
            return True
        except Exception:
            continue
    return False




def get_next_role():
    """获取下一个待执行的角色名（从 cycle state 中读取）"""
    cycle_dir = CYCLE_DIR
    state_file = os.path.join(cycle_dir, 'state.json')
    next_file = os.path.join(cycle_dir, 'next_prompt.txt')

    if not os.path.exists(state_file) or not os.path.exists(next_file):
        return None

    with open(next_file, 'r', encoding='utf-8') as f:
        prompt = f.read().strip()
    if not prompt:
        return None

    # 从 prompt 中提取 [NEXT] 段
    if '[NEXT]' in prompt:
        after = prompt.split('[NEXT]')[-1].strip()
        lines = after.split('\n')
        if lines:
            first_line = lines[0].strip()
            # 提取角色名（通常在冒号或空格前）
            for prefix in ['下一角色:', '下一角色']:
                if prefix in first_line:
                    return first_line.split(prefix)[-1].strip().split()[0]
            return first_line.split()[0] if first_line else None
    return None


def list_pipelines():
    """列出所有管线"""
    _ensure_dirs()
    pipelines = []
    for f in os.listdir(PIPELINE_DIR):
        if f.endswith('.json'):
            try:
                pl = load_json(os.path.join(PIPELINE_DIR, f))
                pipelines.append(pl)
            except (FileNotFoundError, json.JSONDecodeError):
                logging.warning("跳过损坏的管线文件: %s", f)
    pipelines.sort(key=lambda p: p.get('started_at', ''), reverse=True)
    return pipelines


def advance_pipeline(phase, score=None, pid=None):
    """推进管线按 phase 流转（以 pipeline.json 为唯一权威源）"""
    pipeline = get_pipeline(pid)
    if not pipeline:
        print("无活跃管线")
        return None

    if pipeline['loop_count'] >= pipeline['max_loops']:
        print(f"错误: 达到最大循环次数 ({pipeline['max_loops']})")
        return None

    # 初始化状态机引擎（从 pipeline.json 读取当前节点，不依赖 machine_state.json）
    from state_machine_engine import StateMachineRuntime
    engine = StateMachineRuntime()
    engine.load(STATE_MACHINE_PATH)
    engine.state['current_node'] = pipeline['current_node']
    engine.state['current_phase'] = pipeline['current_phase']
    engine.state['loop_count'] = pipeline['loop_count']
    engine.state['completed_nodes'] = list(pipeline.get('completed_nodes', []))

    # 处理 CL 分数
    from state_machine_parser import load_state_machine
    sm_config = load_state_machine(STATE_MACHINE_PATH)

    context = {}
    if score is not None:
        context['score'] = score
        if phase == 'cl-done_pass' and score < 9:
            phase = 'cl-done_fail'
        elif phase == 'cl-done_fail' and score >= CL_PASS_THRESHOLD:
            phase = 'cl-done_pass'

    try:
        result = engine.transition(phase, context)
    except ValueError as e:
        logging.warning("流转失败: %s", e)
        return None

    # 更新管线状态
    current = result['from']
    next_node = result['to']

    pipeline['current_node'] = next_node if not result['is_terminal'] else '__terminal__'
    pipeline['current_phase'] = phase
    pipeline['loop_count'] = result['loop_count']

    if next_node == '__terminal__':
        pipeline['status'] = 'completed'
        pipeline['cl_score'] = score
        run_cl_review(pipeline['pipeline_id'], score)
        from handoff_ticket import create_handoff_ticket
        create_handoff_ticket("client-gate", "system",
                              artifacts=[],
                              pending_decisions=[],
                              assumptions=[f"CL score: {score}"])
        print(f"管线完成! 总分: {score}")
    elif phase in ('cl-done_fail',) or ('fail' in phase.lower() and current == 'client-gate'):
        pipeline['failed_count'] += 1
        pipeline['status'] = 'failback_to_architect'
        pipeline['cl_score'] = score
        run_cl_review(pipeline['pipeline_id'], score if score else 0)
        handle_cl_failback(pipeline['pipeline_id'])

    pipeline['completed_nodes'].append(current)
    pipeline['history'].append({
        "from": current,
        "to": next_node,
        "phase": phase,
        "timestamp": datetime.now().isoformat(),
    })

    # 更新 handoff ticket
    from handoff_ticket import create_handoff_ticket
    receiver = next_node if not result['is_terminal'] else '__terminal__'
    create_handoff_ticket(current, receiver,
                          artifacts=[],
                          pending_decisions=[])

    # 先写 cycle state（辅助数据）
    import hashlib
    cycle_dir = CYCLE_DIR
    os.makedirs(cycle_dir, exist_ok=True)
    goal_hash = hashlib.sha256(pipeline.get('goal', '').encode()).hexdigest()[:64]
    cycle_state = {
        "goal": pipeline.get('goal', ''),
        "goal_hash": goal_hash,
        "phase": phase,
        "round": pipeline.get('round', 1),
        "max_rounds": pipeline.get('max_rounds', 3),
        "iteration": pipeline['loop_count'],
        "max_iterations": pipeline['max_loops'],
        "next_prompt": f"[GOAL] {pipeline.get('goal', '')}\n[PHASE] {phase}\n[ROLE] {current}\n[DONE] completed\n[STATE] {pipeline['loop_count']} loops\n[NEXT] next: {next_node}",
        "summary": f"{current} -> {next_node} ({phase})",
        "last_updated": datetime.now().isoformat(),
    }
    if result['is_terminal']:
        cycle_state['phase'] = 'done'
    with open(os.path.join(cycle_dir, 'state.json'), 'w', encoding='utf-8') as f:
        json.dump(cycle_state, f, ensure_ascii=False, indent=2)

    # pipeline.json 最后写——崩溃恢复时以此为准
    save_json(_pipeline_path(pipeline['pipeline_id']), pipeline)
    engine._save_state()

    # 管线完成时清理 next_prompt.txt，防止 has_pending_pipeline 误判
    if result['is_terminal']:
        npt = os.path.join('.reasonix', 'cycle', 'next_prompt.txt')
        if os.path.exists(npt):
            with open(npt, 'w', encoding='utf-8') as f:
                f.write('')

    status = "完成" if result['is_terminal'] else f"进行中 (-> {next_node})"
    print(f"管线流转: {current} -> {next_node}")
    print(f"  phase: {phase}")
    print(f"  状态:   {status}")
    print(f"  循环:   {pipeline['loop_count']}/{pipeline['max_loops']}")

    return pipeline


def show_status(pid=None):
    """显示管线状态"""
    pipeline = get_pipeline(pid)
    if not pipeline:
        print("无活跃管线")
        # 检查是否有状态机引擎状态
        state_path = f"{STATE_MACHINE_DIR}/machine_state.json"
        if os.path.exists(state_path):
            state = load_json(state_path)
            print(f"状态机当前节点: {state.get('current_node', '?')}")
            print(f"已完成: {len(state.get('completed_nodes', []))} 个节点")
            print("提示: 管线元数据已丢失，但状态机数据仍在")
        return 1

    total = len(pipeline.get('completed_nodes', []))
    print(f"管线:       {pipeline['pipeline_id']}")
    print(f"目标:       {pipeline['goal'][:60]}...")
    print(f"状态:       {pipeline['status']}")
    print(f"当前节点:   {pipeline['current_node']}")
    print(f"当前 phase: {pipeline['current_phase']}")
    print(f"已完成:     {total} 个节点")
    print(f"流转次数:   {pipeline['loop_count']}/{pipeline['max_loops']}")
    print(f"失败次数:   {pipeline['failed_count']}")

    if pipeline['history']:
        print(f"\n最近流转:")
        for h in pipeline['history'][-5:]:
            print(f"  {h['from']:15s} -> {h['to']:15s}  [{h['phase']}]")

    if pipeline.get('cl_score') is not None:
        print(f"\nCL 终审分数: {pipeline['cl_score']}/10")
    return 0


def cmd_init(args):
    pipeline = init_pipeline(args.goal, rounds=getattr(args, 'rounds', 3))
    return 0


def cmd_status(args):
    return show_status(args.pipeline)


def cmd_advance(args):
    advance_pipeline(args.phase, score=args.score)
    return 0


def cmd_continue(args):
    """从 pipeline.json 读取下一 phase 并推进管线（以 pipeline.json 为权威源）"""
    import json as _json
    # 从 pipeline.json 获取当前状态（权威源），不依赖 cycle/state.json
    pipeline = get_pipeline()
    if not pipeline:
        print("无活跃管线")
        return 1
    if pipeline.get('status') == 'completed' or pipeline.get('current_node') == '__terminal__':
        print(f"管线已结束 (status={pipeline.get('status')})")
        return 0
    ph = pipeline.get('current_phase', '')
    if not ph or ph == 'done':
        print(f"管线已结束 (phase={ph})")
        return 0
    # phase='init' 是初始化标记，自动推进到 boss-done
    if ph == 'start':
        print("检测到初始 phase，自动推进到 boss-done")
        ph = 'boss-done'
    print(f"推进管线: phase={ph}")
    advance_pipeline(ph, score=args.score)
    return 0


def cmd_list(args):
    pipelines = list_pipelines()
    if not pipelines:
        print("(空)")
        return 0
    for pl in pipelines:
        status_icon = "DONE" if pl['status'] == 'completed' else "RUN"
        print(f"  {pl['pipeline_id']:35s} [{status_icon}] {pl['goal'][:50]}...")
    print(f"\n共 {len(pipelines)} 个管线")
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 Pipeline Orchestrator')
    sub = parser.add_subparsers(dest='command')

    p_i = sub.add_parser('init', help='初始化管线')
    p_i.add_argument('goal', help='管线目标')
    p_i.add_argument('--rounds', '-r', type=int, default=3, help='多轮循环次数（默认3轮）')

    p_s = sub.add_parser('status', help='管线状态')
    p_s.add_argument('--pipeline', '-p', help='管线 ID（默认最新）')

    p_c = sub.add_parser('continue', help='从 cycle-bridge 读取下一阶段并推进')
    p_c.add_argument('--score', '-s', type=int, help='CL 评分')

    p_a = sub.add_parser('advance', help='推进管线')
    p_a.add_argument('phase', help='phase flag')
    p_a.add_argument('--score', '-s', type=int, help='CL 评分（仅 cl-done_pass/fail 需要）')

    sub.add_parser('list', help='列出管线')

    p_r = sub.add_parser('repair', help='从 pipeline.json 重建 cycle/state（修复不一致）')
    p_r.add_argument('--pipeline', '-p', help='管线 ID（默认最新）')

    args = parser.parse_args()

    if args.command == 'init':
        return cmd_init(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'advance':
        return cmd_advance(args)
    elif args.command == 'continue':
        return cmd_continue(args)
    elif args.command == 'repair':
        return cmd_repair(args)
    elif args.command == 'list':
        return cmd_list(args)
    else:
        parser.print_help()
        return 0


def cmd_repair(args):
    """从 pipeline.json 重建 cycle state 和 machine state（修复不一致）"""
    pipeline = get_pipeline(args.pipeline)
    if not pipeline:
        print("无活跃管线可修复")
        return 1

    # 从 pipeline.json 重建 cycle/state.json
    import hashlib
    cycle_dir = CYCLE_DIR
    os.makedirs(cycle_dir, exist_ok=True)
    goal_hash = hashlib.sha256(pipeline.get('goal', '').encode()).hexdigest()[:64]
    phase = pipeline.get('current_phase', 'start')
    if pipeline.get('status') == 'completed':
        phase = 'done'
    cycle_state = {
        "goal": pipeline.get('goal', ''),
        "goal_hash": goal_hash,
        "phase": phase,
        "iteration": pipeline.get('loop_count', 0),
        "max_iterations": pipeline.get('max_loops', 50),
        "next_prompt": f"[GOAL] {pipeline.get('goal', '')}\n[PHASE] {phase}\n[ROLE] {pipeline.get('current_node', '?')}",
        "summary": f"重建自 pipeline.json | 节点: {pipeline.get('current_node')} | phase: {phase}",
        "last_updated": datetime.now().isoformat(),
    }
    with open(os.path.join(cycle_dir, 'state.json'), 'w', encoding='utf-8') as f:
        json.dump(cycle_state, f, ensure_ascii=False, indent=2)
    print(f"[修复] cycle/state.json 已从 pipeline.json 重建")

    # 重建 next_prompt.txt
    npt = os.path.join(cycle_dir, 'next_prompt.txt')
    if phase not in ('done', ''):
        with open(npt, 'w', encoding='utf-8') as f:
            f.write(cycle_state['next_prompt'])
    elif os.path.exists(npt):
        os.remove(npt)
    print(f"[修复] next_prompt.txt 已{'重建' if phase not in ('done','') else '清理'}")

    # 重建 machine_state.json（从 state-machine.yaml + pipeline 状态）
    from state_machine_engine import StateMachineRuntime
    engine = StateMachineRuntime()
    sm_path = getattr(engine, '_state_machine_path', 'state-machine.yaml')
    if os.path.exists(sm_path):
        engine.load(sm_path)
        engine.state['current_node'] = pipeline.get('current_node', engine.state['current_node'])
        engine.state['current_phase'] = pipeline.get('current_phase', 'start')
        engine.state['completed_nodes'] = pipeline.get('completed_nodes', [])
        engine.state['loop_count'] = pipeline.get('loop_count', 0)
        engine.state['max_loops'] = pipeline.get('max_loops', 50)
        engine.state['failed_count'] = pipeline.get('failed_count', 0)
        engine._save_state()
        print(f"[修复] machine_state.json 已从 pipeline.json 重建")

    print(f"\n修复完成。当前状态: phase={phase}, node={pipeline.get('current_node')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
