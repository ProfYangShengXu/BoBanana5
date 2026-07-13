#!/usr/bin/env python3
"""
# @legacy 旧版实现，优先使用角色卡管线替代
Bobanana 5.0 — State Machine Runtime Engine
状态机运行时引擎，管理状态流转、临时节点插入、循环检测。

用法:
    python state_machine_engine.py load state-machine.yaml     # 加载状态机
    python state_machine_engine.py status                      # 当前状态
    python state_machine_engine.py transition <phase>          # 按 phase 流转
    python state_machine_engine.py insert <role> <phase>       # 插入临时节点
    python state_machine_engine.py reset                      # 重置状态机
"""

import os
import sys
import json
import yaml
import time
from datetime import datetime


class StateMachineRuntime:
    """状态机运行时引擎"""

    def __init__(self, state_dir=".reasonix/state"):
        self.state_dir = state_dir
        self.state_file = os.path.join(state_dir, "machine_state.json")
        self.config = None
        self.state = None

    # ── 状态机加载 ──────────────────────────────────

    def load(self, path):
        """加载并初始化状态机配置"""
        self._state_machine_path = path
        with open(path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        if not self.config:
            raise ValueError("空的状态机配置")

        # 初始化状态
        node_map = {n['id']: n for n in self.config.get('nodes', [])}
        entry = self.config.get('entry_point')

        if entry not in node_map:
            raise ValueError(f"入口节点 '{entry}' 不在节点列表中")

        self.state = {
            'version': self.config.get('version', 1),
            'current_node': entry,
            'current_phase': 'start',
            'completed_nodes': [],
            'loop_count': 0,
            'max_loops': self.config.get('max_loops', 50),
            'failed_count': 0,
            'started_at': datetime.now().isoformat(),
            'temporary_nodes': [],
            'history': [],
        }
        os.makedirs(self.state_dir, exist_ok=True)
        self._save_state()
        return self.state

    def load_state(self):
        """从文件加载已保存的状态"""
        if not os.path.exists(self.state_file):
            return None
        with open(self.state_file, 'r', encoding='utf-8') as f:
            self.state = json.load(f)
        # Also load config from state machine file
        if self.config is None:
            sm_path = getattr(self, '_state_machine_path', 'state-machine.yaml')
            if os.path.exists(sm_path):
                with open(sm_path, 'r', encoding='utf-8') as cf:
                    self.config = yaml.safe_load(cf)
        return self.state

    # ── 状态查询 ──────────────────────────────────

    def get_status(self):
        """获取当前状态"""
        return {
            'current_node': self.state['current_node'],
            'current_phase': self.state['current_phase'],
            'completed_nodes': self.state['completed_nodes'],
            'loop_count': self.state['loop_count'],
            'failed_count': self.state['failed_count'],
            'max_loops': self.state['max_loops'],
            'is_running': self.state['loop_count'] < self.state['max_loops'],
            'temporary_count': len(self.state['temporary_nodes']),
        }

    def get_available_transitions(self):
        """获取当前节点可用的转换"""
        current = self.state['current_node']
        transitions = []
        for edge in self.config.get('edges', []):
            if edge['from'] == current:
                trans = {
                    'phase': edge['phase'],
                    'to': edge['to'],
                }
                if 'condition' in edge:
                    trans['condition'] = edge['condition']
                transitions.append(trans)
        return transitions

    # ── 状态流转 ──────────────────────────────────

    def transition(self, phase, context=None):
        """按 phase 执行状态转换"""
        if self.state['loop_count'] >= self.state['max_loops']:
            raise RuntimeError(
                f"达到最大循环次数 ({self.state['max_loops']})，管线终止"
            )

        current = self.state['current_node']
        target_edge = None

        for edge in self.config.get('edges', []):
            if edge['from'] == current and edge['phase'] == phase:
                # 检查条件分支
                if 'condition' in edge:
                    if context and self._evaluate_condition(edge['condition'], context):
                        target_edge = edge
                        break
                else:
                    target_edge = edge
                    break

        if not target_edge:
            available = [e['phase'] for e in self.get_available_transitions()]
            raise ValueError(
                f"当前节点 '{current}' 没有匹配 phase='{phase}' 的转换"
                f"\n可用 phase: {available}"
            )

        next_node = target_edge['to']
        is_terminal = (next_node == '__terminal__')
        is_temporary = self._is_temporary_node(next_node)

        # 记录历史
        self.state['history'].append({
            'from': current,
            'to': next_node,
            'phase': phase,
            'timestamp': datetime.now().isoformat(),
        })

        if is_terminal:
            self.state['completed_nodes'].append(current)
            self.state['current_node'] = '__terminal__'
            self.state['current_phase'] = 'done'
        else:
            # 如果当前节点是临时节点且已完成，移出临时列表
            if current in self.state['temporary_nodes']:
                self.state['temporary_nodes'].remove(current)

            if is_temporary:
                self.state['temporary_nodes'].append(next_node)

            self.state['completed_nodes'].append(current)
            self.state['current_node'] = next_node
            self.state['current_phase'] = phase

        self.state['loop_count'] += 1
        self._save_state()

        return {
            'from': current,
            'to': next_node,
            'phase': phase,
            'is_terminal': is_terminal,
            'completed_nodes': self.state['completed_nodes'],
            'loop_count': self.state['loop_count'],
        }

    def insert_temporary_node(self, role_name, phase_flag, after_node=None):
        """在状态机中插入一个临时节点"""
        if after_node is None:
            after_node = self.state['current_node']

        temp_node_id = f"{role_name}-{int(time.time())}"

        # 添加临时节点
        self.config['nodes'].append({
            'id': temp_node_id,
            'label': role_name,
            'is_temporary': True,
        })

        # 添加：当前节点 → 临时节点
        self.config['edges'].append({
            'from': after_node,
            'to': temp_node_id,
            'phase': phase_flag,
        })

        # 添加：临时节点 → 当前节点 (返回)
        self.config['edges'].append({
            'from': temp_node_id,
            'to': after_node,
            'phase': f"{role_name}-done",
        })

        # 更新状态
        self.state['current_node'] = temp_node_id
        self.state['current_phase'] = phase_flag
        self.state['temporary_nodes'].append(temp_node_id)
        self._save_state()

        return {
            'node_id': temp_node_id,
            'role': role_name,
            'phase': phase_flag,
            'return_phase': f"{role_name}-done",
        }

    def reset(self):
        """重置状态机"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = None
        self.config = None
        return True

    # ── 内部方法 ──────────────────────────────────

    def _save_state(self):
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _evaluate_condition(self, condition, context):
        """评估条件表达式"""
        field = condition.get('field')
        op = condition.get('operator')
        value = condition.get('value')
        actual = context.get(field) if context else None

        if actual is None:
            return False

        if op == '<': return actual < value
        elif op == '>': return actual > value
        elif op == '<=': return actual <= value
        elif op == '>=': return actual >= value
        elif op == '==': return actual == value
        elif op == '!=': return actual != value
        return False

    def _is_temporary_node(self, node_id):
        for node in self.config.get('nodes', []):
            if node['id'] == node_id and node.get('is_temporary'):
                return True
        return False


# ── CLI ──────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 State Machine Engine')
    sub = parser.add_subparsers(dest='command')

    p_load = sub.add_parser('load', help='加载状态机')
    p_load.add_argument('path', help='state-machine.yaml 路径')

    sub.add_parser('status', help='当前状态')

    p_trans = sub.add_parser('transition', help='按 phase 流转')
    p_trans.add_argument('phase', help='转换 phase flag')

    p_ins = sub.add_parser('insert', help='插入临时节点')
    p_ins.add_argument('role', help='角色名称')
    p_ins.add_argument('phase', help='转换 phase flag')

    sub.add_parser('reset', help='重置状态机')

    args = parser.parse_args()

    engine = StateMachineRuntime()

    if args.command == 'load':
        result = engine.load(args.path)
        print(f"已加载状态机 v{result['version']}")
        print(f"入口节点: {result['current_node']}")
        print(f"状态文件: {engine.state_file}")

    elif args.command == 'status':
        state = engine.load_state()
        if not state:
            print("状态机未加载，请先运行 load")
            return 1
        status = engine.get_status()
        print(f"当前节点:     {status['current_node']}")
        print(f"当前 phase:   {status['current_phase']}")
        print(f"已完成:       {', '.join(status['completed_nodes']) or '(无)'}")
        print(f"流转次数:     {status['loop_count']}/{status['max_loops']}")
        print(f"失败计数:     {status['failed_count']}")
        print(f"运行中:       {'是' if status['is_running'] else '否（已终止）'}")

        trans = engine.get_available_transitions()
        if trans:
            print(f"\n可用转换 ({len(trans)}):")
            for t in trans:
                cond = f" / {t['condition']}" if 'condition' in t else ""
                print(f"  {t['phase']:30s} -> {t['to']}{cond}")

    elif args.command == 'transition':
        engine.load_state()
        if not engine.state:
            print("状态机未加载")
            return 1
        result = engine.transition(args.phase)
        print(f"流转: {result['from']} -> {result['to']}")
        print(f"phase: {result['phase']}")
        print(f"已完成: {len(result['completed_nodes'])} 个节点")
        if result['is_terminal']:
            print("管线已完成！")

    elif args.command == 'insert':
        engine.load_state()
        if not engine.state:
            print("状态机未加载")
            return 1
        result = engine.insert_temporary_node(args.role, args.phase)
        print(f"插入临时节点: {result['node_id']}")
        print(f"角色: {result['role']}")
        print(f"进入 phase: {result['phase']}")
        print(f"返回 phase: {result['return_phase']}")

    elif args.command == 'reset':
        engine.reset()
        print("状态机已重置")

    else:
        parser.print_help()

    return 0


if __name__ == '__main__':
    sys.exit(main())
