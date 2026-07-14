#!/usr/bin/env python3
"""
Bobanana 5.0 — MCP Server (JSON-RPC 2.0 over stdio)
为 EUI-NEO 桌面端提供 Reasonix MCP 协议通信层。

启动: python mcp_server.py
EUI-NEO 通过 stdio 发送 JSON-RPC 2.0 请求，本服务器处理并返回结果。
"""

import sys
import os
import json
import yaml
import traceback


def send_response(id, result=None, error=None):
    """发送 JSON-RPC 2.0 响应到 stdout"""
    response = {"jsonrpc": "2.0", "id": id}
    if error:
        response["error"] = {"code": error.get("code", -1), "message": error.get("message", "Unknown error")}
    else:
        response["result"] = result or {}
    line = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def handle_request(method, params):
    """处理 JSON-RPC 请求"""
    handlers = {
        # 状态机
        "get_state_machine": handle_get_state_machine,
        "get_pipeline_status": handle_get_pipeline_status,
        "queue_next_prompt": handle_queue_next_prompt,
        "signal_done": handle_signal_done,
        # 角色卡
        "get_role_cards": handle_get_role_cards,
        "get_role_card_detail": handle_get_role_card_detail,
        # HR
        "trigger_hr_recruit": handle_trigger_hr_recruit,
        # CL
        "get_cl_report": handle_get_cl_report,
        # 工单
        "get_handoff_tickets": handle_get_handoff_tickets,
        # 文件系统
        "read_file": handle_read_file,
    }

    handler = handlers.get(method)
    if not handler:
        return {"error": {"code": -32601, "message": f"Method not found: {method}"}}

    return handler(params or {})


# ── Handlers ─────────────────────────────────────


def handle_get_state_machine(params):
    path = params.get("path", "state-machine.yaml")
    if not os.path.exists(path):
        return {"state_machine": None, "error": f"File not found: {path}"}
    with open(path, 'r', encoding='utf-8') as f:
        sm = yaml.safe_load(f)

    nodes = []
    for n in sm.get("nodes", []):
        nodes.append({
            "id": n["id"],
            "label": n.get("label", n["id"]),
            "is_exit": n.get("is_exit", False),
            "is_temporary": n.get("is_temporary", False),
        })
    edges = []
    for e in sm.get("edges", []):
        edge = {"from": e["from"], "to": e["to"], "phase": e["phase"]}
        if "condition" in e:
            edge["condition"] = e["condition"]
        edges.append(edge)

    state_path = ".reasonix/state/machine_state.json"
    current_node = None
    completed = []
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            st = json.load(f)
            current_node = st.get("current_node")
            completed = st.get("completed_nodes", [])

    return {
        "state_machine": {
            "version": sm.get("version"),
            "entry_point": sm.get("entry_point"),
            "nodes": nodes,
            "edges": edges,
        },
        "current_node": current_node,
        "completed_nodes": completed,
    }


def handle_get_pipeline_status(params):
    pipeline_id = params.get("pipeline_id")
    pipeline_dir = ".reasonix/pipelines"
    if pipeline_id:
        path = os.path.join(pipeline_dir, f"{pipeline_id}.json")
    else:
        # 获取最新
        files = sorted([f for f in os.listdir(pipeline_dir) if f.endswith('.json')], reverse=True) if os.path.exists(pipeline_dir) else []
        path = os.path.join(pipeline_dir, files[0]) if files else None

    if not path or not os.path.exists(path):
        return {"status": "no_active_pipeline"}

    with open(path, 'r', encoding='utf-8') as f:
        pl = json.load(f)

    return {
        "pipeline_id": pl["pipeline_id"],
        "status": pl["status"],
        "current_node": pl["current_node"],
        "current_phase": pl["current_phase"],
        "completed_count": len(pl.get("completed_nodes", [])),
        "loop_count": pl.get("loop_count", 0),
        "max_loops": pl.get("max_loops", 50),
        "failed_count": pl.get("failed_count", 0),
        "history": pl.get("history", [])[-5:],
    }


def handle_queue_next_prompt(params):
    from pipeline_orchestrator import advance_pipeline
    phase = params.get("phase")
    score = params.get("score")
    result = advance_pipeline(phase, score=score)
    if result:
        return {"success": True, "next_node": result.get("current_node"), "status": result.get("status")}
    return {"success": False, "error": "Pipeline advance failed"}


def handle_signal_done(params):
    return {"success": True, "message": "Pipeline completed"}


def handle_get_role_cards(params):
    tag = params.get("tag")
    from role_tag_system import load_all_role_cards, get_roles_by_tag
    if tag:
        names = get_roles_by_tag(tag)
        cards = [c for c in load_all_role_cards() if c['name'] in names]
    else:
        cards = load_all_role_cards()

    result = []
    for c in cards:
        result.append({
            "name": c.get("name"),
            "tags": c.get("tags", []),
            "description": c.get("description", "")[:80],
            "input_count": len(c.get("input_contract", [])),
            "output_count": len(c.get("output_contract", [])),
        })
    return {"cards": result, "total": len(result)}


def handle_get_role_card_detail(params):
    name = params.get("name")
    path = f"skills/roles/{name}/role-card.yaml"
    if not os.path.exists(path):
        return {"error": f"Role card not found: {name}"}
    with open(path, 'r', encoding='utf-8') as f:
        card = yaml.safe_load(f)
    return {"card": card}


def handle_trigger_hr_recruit(params):
    role_name = params.get("role_name")
    description = params.get("description", "")
    standards_path = params.get("standards_path")

    from hr_recruitment import start_recruitment, reference_existing_standards

    if standards_path:
        recruitment = reference_existing_standards(role_name, standards_path)
    else:
        recruitment = start_recruitment(role_name, description)

    # 自动生成角色卡
    if recruitment.get("status") in ("research_done", "standards_found"):
        from hr_recruitment import generate_role_card
        generate_role_card(recruitment["recruitment_id"])

    return {
        "recruitment_id": recruitment["recruitment_id"],
        "role_name": role_name,
        "status": recruitment["status"],
    }


def handle_get_cl_report(params):
    pipeline_id = params.get("pipeline_id")
    pipeline_dir = ".reasonix/pipelines"
    if pipeline_id:
        path = os.path.join(pipeline_dir, f"{pipeline_id}.json")
    else:
        files = sorted([f for f in os.listdir(pipeline_dir) if f.endswith('.json')], reverse=True) if os.path.exists(pipeline_dir) else []
        path = os.path.join(pipeline_dir, files[0]) if files else None

    if not path or not os.path.exists(path):
        return {"report": None}

    with open(path, 'r', encoding='utf-8') as f:
        pl = json.load(f)

    return {
        "report": {
            "pipeline_id": pl["pipeline_id"],
            "score": pl.get("cl_score"),
            "status": pl["status"],
            "completed_nodes": pl.get("completed_nodes", []),
            "loop_count": pl.get("loop_count", 0),
        }
    }


def handle_get_handoff_tickets(params):
    role_name = params.get("role_name")
    from handoff_ticket import list_handoff_tickets
    tickets = list_handoff_tickets(role_name=role_name)
    return {"tickets": tickets, "total": len(tickets)}


def handle_read_file(params):
    path = params.get("path")
    if not path:
        return {"error": "No path provided"}
    # 路径消毒：禁止目录遍历
    safe_path = os.path.normpath(os.path.join(os.getcwd(), path))
    if not safe_path.startswith(os.getcwd()):
        return {"error": "Path traversal denied"}
    if not os.path.exists(safe_path):
        return {"error": f"File not found: {path}"}
    with open(safe_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return {"content": content, "path": path}


# ── Main Loop ────────────────────────────────────

def main():
    import sys
    # 确保 UTF-8 输出
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')

    print("MCP Server ready", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id")

            result = handle_request(method, params)
            if "error" in result:
                send_response(req_id, error=result["error"])
            else:
                send_response(req_id, result=result)

        except json.JSONDecodeError:
            send_response(None, error={"code": -32700, "message": "Parse error"})
        except Exception as e:
            send_response(None, error={"code": -32603, "message": str(e)})
            traceback.print_exc(file=sys.stderr)


if __name__ == '__main__':
    main()
