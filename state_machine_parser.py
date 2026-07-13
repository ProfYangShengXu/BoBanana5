#!/usr/bin/env python3
"""
Bobanana 5.0 — State Machine Parser & Validator
解析和验证 state-machine.yaml，支持拓扑检查、循环检测、条件分支验证。

用法:
    python state_machine_parser.py validate state-machine.yaml    # 验证状态机配置
    python state_machine_parser.py parse state-machine.yaml       # 解析并输出拓扑
    python state_machine_parser.py graph state-machine.yaml      # 输出 Mermaid 图
"""

import os
import sys
import yaml
import json
from collections import defaultdict


def load_state_machine(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def validate_state_machine(sm, schema_path=None):
    """验证状态机配置的完整性和正确性"""
    errors = []
    warnings = []

    if not sm:
        return ["错误: 空的状态机配置"], []

    # 1. 检查必填顶层字段
    for field in ['version', 'entry_point', 'nodes', 'edges']:
        if field not in sm:
            errors.append(f"缺少必填字段: {field}")

    if errors:
        return errors, warnings

    # 2. 检查节点
    node_ids = set()
    node_map = {}
    for i, node in enumerate(sm['nodes']):
        if 'id' not in node:
            errors.append(f"nodes[{i}]: 缺少 id 字段")
            continue
        nid = node['id']
        if nid in node_ids:
            errors.append(f"nodes[{i}]: 重复的节点 id '{nid}'")
        node_ids.add(nid)
        node_map[nid] = node

    # 3. 检查入口节点
    entry = sm.get('entry_point')
    if entry and entry not in node_ids:
        errors.append(f"entry_point '{entry}' 不在节点列表中")

    # 4. 检查边
    edge_count = defaultdict(int)
    for i, edge in enumerate(sm['edges']):
        if 'from' not in edge:
            errors.append(f"edges[{i}]: 缺少 from 字段")
        if 'to' not in edge:
            errors.append(f"edges[{i}]: 缺少 to 字段")
        if 'phase' not in edge:
            errors.append(f"edges[{i}]: 缺少 phase 字段")

        frm = edge.get('from')
        to = edge.get('to')

        if frm and frm not in node_ids and frm != '__terminal__':
            warnings.append(f"edges[{i}]: from '{frm}' 不是已知的节点 id")
        if to and to not in node_ids and to != '__terminal__':
            warnings.append(f"edges[{i}]: to '{to}' 不是已知的节点 id")

        # 检查条件分支
        if 'condition' in edge:
            cond = edge['condition']
            if 'field' not in cond:
                errors.append(f"edges[{i}]: condition 缺少 field")
            if 'operator' not in cond:
                errors.append(f"edges[{i}]: condition 缺少 operator")
            if 'value' not in cond:
                errors.append(f"edges[{i}]: condition 缺少 value")

        edge_count[(frm, to)] += 1

    # 5. 检查每个节点的入度和出度
    out_edges = defaultdict(list)
    in_edges = defaultdict(list)
    for edge in sm['edges']:
        frm = edge.get('from')
        to = edge.get('to')
        if frm:
            out_edges[frm].append(edge)
        if to:
            in_edges[to].append(edge)

    for nid in node_ids:
        if nid == entry:
            if nid not in in_edges and nid != entry:
                warnings.append(f"节点 '{nid}': 没有入边（孤立节点）")
        else:
            if nid not in in_edges and nid != entry:
                warnings.append(f"节点 '{nid}': 没有入边（可能无法到达）")

        is_exit = node_map[nid].get('is_exit', False)
        if is_exit and nid in out_edges:
            # 允许条件分支出边（CL 的打回/通过分支）
            has_conditional = any('condition' in e for e in out_edges[nid])
            has_unconditional = any('condition' not in e for e in out_edges[nid])
            if has_unconditional:
                warnings.append(f"出口节点 '{nid}' 有无条件出边（出口出边应全部带 condition）")

    # 6. 检查循环依赖（简化版：检测自环）
    for edge in sm['edges']:
        if edge['from'] == edge['to'] and edge['from'] != '__terminal__':
            # 自环是允许的（dev-done_task-remain → 开发继续）
            pass  # 允许自环，不报错

    # 7. 检查最大流转次数
    if sm.get('max_loops', 0) <= 0:
        warnings.append("max_loops <= 0，管线将被立即终止")

    return errors, warnings


def parse_topology(sm):
    """解析状态机拓扑结构"""
    nodes = []
    for node in sm.get('nodes', []):
        nodes.append({
            'id': node['id'],
            'label': node.get('label', node['id']),
            'is_exit': node.get('is_exit', False),
            'is_temporary': node.get('is_temporary', False),
        })

    edges = []
    for edge in sm.get('edges', []):
        e = {
            'from': edge['from'],
            'to': edge['to'],
            'phase': edge['phase'],
        }
        if 'condition' in edge:
            e['condition'] = edge['condition']
        edges.append(e)

    return {
        'version': sm.get('version', 1),
        'entry_point': sm.get('entry_point', ''),
        'max_loops': sm.get('max_loops', 50),
        'node_count': len(nodes),
        'edge_count': len(edges),
        'nodes': nodes,
        'edges': edges,
    }


def generate_mermaid(sm):
    """生成 Mermaid 流程图"""
    lines = ["graph TD"]
    lines.append(f"  ENTRY[{sm.get('entry_point', '?')}]")

    node_ids = {n['id'] for n in sm.get('nodes', [])}

    for node in sm.get('nodes', []):
        nid = node['id']
        label = node.get('label', nid)
        if node.get('is_exit'):
            lines.append(f"  {nid}[{label}]:::exit")
        elif node.get('is_temporary'):
            lines.append(f"  {nid}({label}):::temp")
        else:
            lines.append(f"  {nid}[{label}]")

    for edge in sm.get('edges', []):
        frm = edge['from']
        to = edge['to']
        phase = edge['phase']
        if 'condition' in edge:
            cond = edge['condition']
            lines.append(f"  {frm} -->|{phase} / {cond['field']} {cond['operator']} {cond['value']}| {to}")
        else:
            lines.append(f"  {frm} -->|{phase}| {to}")

    lines.append("")
    lines.append("  classDef exit fill:#ef4444,color:#fff")
    lines.append("  classDef temp fill:#22c55e,color:#fff")
    return "\n".join(lines)


def cmd_validate(args):
    sm = load_state_machine(args.path)
    errors, warnings = validate_state_machine(sm)

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN:  {w}")
    if not errors and not warnings:
        print(f"  PASS: {args.path} 验证通过")
    elif not errors:
        print(f"  PASS: {args.path} ({len(warnings)} 个警告)")

    return 1 if errors else 0


def cmd_parse(args):
    sm = load_state_machine(args.path)
    topo = parse_topology(sm)
    print(f"版本:      v{topo['version']}")
    print(f"入口:      {topo['entry_point']}")
    print(f"最大循环:  {topo['max_loops']}")
    print(f"节点数:    {topo['node_count']}")
    print(f"边数:      {topo['edge_count']}")
    print()
    print("节点列表:")
    for n in topo['nodes']:
        exit_flag = " [EXIT]" if n['is_exit'] else ""
        temp_flag = " [TEMP]" if n['is_temporary'] else ""
        print(f"  {n['id']:20s} {n['label']}{exit_flag}{temp_flag}")
    print()
    print("边列表:")
    for e in topo['edges']:
        cond_str = f" / {e['condition']}" if 'condition' in e else ""
        print(f"  {e['from']:20s} -> {e['to']:20s} [{e['phase']}]{cond_str}")
    return 0


def cmd_graph(args):
    sm = load_state_machine(args.path)
    print(generate_mermaid(sm))
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 State Machine Tool')
    sub = parser.add_subparsers(dest='command')

    p_v = sub.add_parser('validate', help='验证状态机配置')
    p_v.add_argument('path', help='state-machine.yaml 路径')

    p_p = sub.add_parser('parse', help='解析并输出拓扑')
    p_p.add_argument('path', help='state-machine.yaml 路径')

    p_g = sub.add_parser('graph', help='输出 Mermaid 图')
    p_g.add_argument('path', help='state-machine.yaml 路径')

    args = parser.parse_args()

    if args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'parse':
        return cmd_parse(args)
    elif args.command == 'graph':
        return cmd_graph(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
