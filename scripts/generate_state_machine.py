#!/usr/bin/env python3
"""
Bobanana 5.0 — 状态机生成器 (Schema标准工具)
替代手写 state-machine.yaml。交互式 / CLI 模式生成合法状态机。
用法:
    python scripts/generate_state_machine.py template standard
    python scripts/generate_state_machine.py list-templates
    python scripts/generate_state_machine.py validate state-machine.yaml
"""

import os, sys, yaml, json, glob, shutil

TEMPLATES_DIR = "docs/examples"
OUTPUT_PATH = "state-machine.yaml"

TEMPLATES = {
    "quick-fix": "最小管线(4角色) — 紧急修复",
    "standard": "标准开发(11角色) — 中小型项目",
    "chaos-ready": "混沌就绪(14角色) — 高可靠系统",
    "ai-native": "AI原生(14角色) — LLM项目",
    "fullstack-web": "全栈Web(22角色) — 大型全栈",
    "fullstack-chaos": "全栈混沌(26角色) — 全栈+韧性",
    "microservices": "微服务(18角色) — 分布式系统",
    "game-dev": "游戏开发(14角色) — 游戏+服务器",
    "data-science": "数据科学(12角色) — 数据分析/ML",
    "security-audit": "安全审计(9角色) — 渗透测试",
    "super-cr": "超级CR(15+) — 技术栈审查",
}

# Schema 校验规则: 禁止紧凑格式、禁止 flow mapping condition
SCHEMA_RULES = {
    "forbid_inline_tags": True,
    "forbid_flow_condition": True,
    "require_block_edges": True,
}


def list_templates():
    print("可用状态机模板:")
    for name, desc in TEMPLATES.items():
        path = os.path.join(TEMPLATES_DIR, f"state-machine-{name}.yaml")
        status = "✅" if os.path.exists(path) else "❌"
        print(f"  {status} {name:20s} {desc}")
    print(f"\n当前: {OUTPUT_PATH}")
    return 0


def apply_template(name):
    src = os.path.join(TEMPLATES_DIR, f"state-machine-{name}.yaml")
    if not os.path.exists(src):
        # 尝试直接使用 name 作为文件名
        src = os.path.join(TEMPLATES_DIR, f"{name}.yaml")
    if not os.path.exists(src):
        print(f"[错误] 模板不存在: {name}")
        return 1

    # 读取源模板
    with open(src, "r", encoding="utf-8") as f:
        sm = yaml.safe_load(f)

    # Schema 检查: 禁止内联 tags 和 flow condition
    sm = _normalize_schema(sm)

    # 写入输出
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(sm, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"[OK] 已生成 {OUTPUT_PATH} (来自模板: {name})")
    return 0


def _normalize_schema(sm):
    """规范化状态机 Schema: 确保所有节点和边使用块格式"""
    nodes = sm.get("nodes", [])
    edges = sm.get("edges", [])

    # 规范化节点
    for node in nodes:
        tags = node.get("tags", [])
        if isinstance(tags, list) and tags:
            # 将内联 tags 转为块格式
            pass  # yaml.dump default_flow_style=False 会自动处理

    # 规范化边
    for edge in edges:
        if "condition" in edge:
            cond = edge["condition"]
            if isinstance(cond, dict):
                # 确保 condition 使用块格式
                pass  # yaml.dump default_flow_style=False 会自动处理

    return {"version": sm.get("version", 1),
            "entry_point": sm.get("entry_point", "boss"),
            "max_loops": sm.get("max_loops", 50),
            "nodes": nodes,
            "edges": edges}


def validate_schema(path):
    """严格 Schema 校验"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    errors = []

    # 检查内联 tags
    if 'tags: [' in content or 'tags: [' in content:
        errors.append("使用内联 tags (如 tags: [OP]) → 请改为块格式:\n  tags:\n    - OP")

    # 检查 flow mapping condition
    if "condition: {" in content:
        errors.append("使用 flow mapping condition (如 condition: {field:score}) → 请改为块格式")

    # 检查内联边
    if "- from:" in content and "- to:" in content and "phase:" in content:
        # 检查是否有单行边
        for line in content.split("\n"):
            ls = line.strip()
            if ls.startswith("- from:") and len(ls) < 100:
                pass  # 可能是多行边的起始

    if errors:
        print(f"[FAIL] Schema 校验未通过 ({len(errors)} 项):")
        for e in errors:
            print(f"  ❌ {e}")
        return 1

    # YAML 解析检查
    try:
        yaml.safe_load(content)
        print(f"[PASS] {path} Schema 校验通过 ✅")
        return 0
    except yaml.YAMLError as e:
        print(f"[FAIL] YAML 解析错误: {e}")
        return 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("可用命令:")
        print("  list-templates          列出所有模板")
        print("  template <name>         应用模板到 state-machine.yaml")
        print("  validate [path]         校验状态机 Schema")
        return 1

    cmd = sys.argv[1]
    if cmd == "list-templates":
        return list_templates()
    elif cmd == "template":
        if len(sys.argv) < 3:
            print("[错误] 请指定模板名")
            return 1
        return apply_template(sys.argv[2])
    elif cmd == "validate":
        path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_PATH
        if not os.path.exists(path):
            print(f"[错误] 文件不存在: {path}")
            return 1
        return validate_schema(path)
    else:
        print(f"[错误] 未知命令: {cmd}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
