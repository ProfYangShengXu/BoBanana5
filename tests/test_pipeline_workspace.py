"""
test_pipeline_workspace — 管线工作区隔离集成测试

测试项:
  1. 迁移测试 — 模拟旧 pl-*.json → migrate_legacy()
  2. 自定义工作区初始化
  3. 默认工作区兼容 (直接文件校验绕过 pending check)
  4. list --all 跨工作区列举
  5. 状态隔离
  6. get_pipeline 按 ID+workspace
  7. has_pending_pipeline
  8. CLI 兼容性
"""

import os, sys, json, shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pipeline_orchestrator as po

PASS = 0
FAIL = 0
MY_WS = "test-ws-" + str(int(__import__('time').time()))

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")


def cleanup_all():
    """清理所有测试管线和工作区"""
    for ws in po.WorkspaceManager.list_workspaces():
        if ws.startswith("test-ws-"):
            d = po.WorkspaceManager.get_workspace_dir(ws)
            if os.path.isdir(d):
                shutil.rmtree(d)
    # Clean up legacy test dir in .default
    legacy_dir = po.WorkspaceManager.get_pipeline_dir("pl-legacy-test", ".default")
    if os.path.isdir(legacy_dir):
        shutil.rmtree(legacy_dir)
    # Clean up .default test pipelines
    default_dir = po.WorkspaceManager.get_workspace_dir(".default")
    if os.path.isdir(default_dir):
        for d in os.listdir(default_dir):
            p = os.path.join(default_dir, d)
            pl_json = os.path.join(p, "pipeline.json")
            if os.path.isfile(pl_json):
                with open(pl_json, encoding='utf-8') as f:
                    try:
                        pl = json.load(f)
                        if 'test' in pl.get('goal', '').lower():
                            shutil.rmtree(p)
                    except:
                        pass


cleanup_all()

print("=" * 50)
print("Pipeline Workspace Isolation Tests")
print("=" * 50)

# T1: Legacy Migration
print("\n--- T1: Legacy migration ---")
legacy_root = ".reasonix/pipelines"
os.makedirs(legacy_root, exist_ok=True)
legacy_file = os.path.join(legacy_root, "pl-legacy-test.json")
with open(legacy_file, 'w', encoding='utf-8') as f:
    json.dump({"pipeline_id": "pl-legacy-test", "goal": "legacy-test", "status": "completed"}, f)

migrated = po.WorkspaceManager.migrate_legacy()
check("migrate_legacy migrated 1 file", migrated == 1)

new_path = po.WorkspaceManager.get_pipeline_path("pl-legacy-test", ".default")
check("migrated file exists at .default", os.path.isfile(new_path))
check("legacy file removed", not os.path.exists(legacy_file))
check("idempotent (second call=0)", po.WorkspaceManager.migrate_legacy() == 0)

# T2: Custom workspace init
print("\n--- T2: Custom workspace ---")
pl2 = po.init_pipeline("test-custom-ws", rounds=1, workspace=MY_WS)
check("init returns pipeline", pl2 is not None)
check(f"workspace={MY_WS}", pl2.get('workspace') == MY_WS)
check("workspace dir exists", os.path.isdir(po.WorkspaceManager.get_workspace_dir(MY_WS)))

pl2_path = po.WorkspaceManager.get_pipeline_path(pl2['pipeline_id'], MY_WS)
check("pipeline.json exists", os.path.isfile(pl2_path))
with open(pl2_path, encoding='utf-8') as f:
    check("pipeline.json has workspace field", json.load(f).get('workspace') == MY_WS)

# T3: Default workspace (direct file creation to avoid pending check)
print("\n--- T3: Default workspace ---")
# Use WorkspaceManager.ensure_dir + save_json directly to simulate init
sim_pid = "pl-sim-default"
sim_dir = po.WorkspaceManager.ensure_dir(sim_pid, ".default")
sim_data = {"pipeline_id": sim_pid, "goal": "test-default-sim", "workspace": ".default",
            "status": "initialized", "current_node": "boss", "current_phase": "start",
            "completed_nodes": [], "loop_count": 0, "max_loops": 50}
po.save_json(po.WorkspaceManager.get_pipeline_path(sim_pid, ".default"), sim_data)
check("simulated pipeline.json written", os.path.isfile(po.WorkspaceManager.get_pipeline_path(sim_pid, ".default")))

pl_found = po.get_pipeline(sim_pid, ".default")
check("get_pipeline by id+ws", pl_found is not None)
check("workspace field read back", pl_found.get('workspace') == ".default")

# T4: List all workspaces
print("\n--- T4: List all workspaces ---")
all_ws = po.WorkspaceManager.list_workspaces()
check(f"multiple workspaces ({len(all_ws)})", len(all_ws) >= 2)
check("test ws in list", MY_WS in all_ws)
check(".default in list", ".default" in all_ws)

all_pl = po.list_pipelines(all_workspaces=True)
check(f"list --all >1 ({len(all_pl)})", len(all_pl) >= 2)
all_ids = [p['pipeline_id'] for p in all_pl]
check("custom ws pipeline in --all", pl2['pipeline_id'] in all_ids)

# T5: State isolation
print("\n--- T5: State isolation ---")
pl_a_pid = "pl-isolation-a-" + str(int(__import__('time').time()))
pl_b_pid = "pl-isolation-b-" + str(int(__import__('time').time()))
pa_dir = po.WorkspaceManager.ensure_dir(pl_a_pid, MY_WS)
pb_dir = po.WorkspaceManager.ensure_dir(pl_b_pid, ".default")
for pid, ws in [(pl_a_pid, MY_WS), (pl_b_pid, ".default")]:
    po.save_json(po.WorkspaceManager.get_pipeline_path(pid, ws),
                 {"pipeline_id": pid, "goal": "isolation-test", "workspace": ws, "status": "initialized"})
check("different paths", po.WorkspaceManager.get_pipeline_path(pl_a_pid, MY_WS) !=
      po.WorkspaceManager.get_pipeline_path(pl_b_pid, ".default"))

# T6: get_pipeline workspace-aware
print("\n--- T6: get_pipeline workspace ---")
check("found in correct ws", po.get_pipeline(pl_a_pid, MY_WS) is not None)
check("not found in wrong ws", po.get_pipeline(pl_a_pid, ".default") is None)

# T7: has_pending_pipeline
print("\n--- T7: has_pending_pipeline ---")
check("custom ws has pending", po.has_pending_pipeline(MY_WS))
check(".default has pending", po.has_pending_pipeline(".default"))

# T8: CLI
print("\n--- T8: CLI ---")
import subprocess
r = subprocess.run([sys.executable, "pipeline_orchestrator.py", "list", "--all"],
                   capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
check("list --all returns 0", r.returncode == 0)
check("output has 'pl-'", "pl-" in r.stdout)

r2 = subprocess.run([sys.executable, "pipeline_orchestrator.py", "status"],
                    capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
check("status returns 0", r2.returncode == 0)

# Cleanup
print("\n--- Cleanup ---")
cleanup_all()
print("  Cleanup complete")

print()
print("=" * 50)
print(f"Results: {PASS} passed, {FAIL} failed")
print("=" * 50)
sys.exit(1 if FAIL > 0 else 0)
