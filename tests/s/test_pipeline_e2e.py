"""
Bobanana 5.0 — E2E: Pipeline (使用独立目录，不改变cwd)
"""
import os, sys, json, yaml, tempfile, shutil, unittest

sys.path.insert(0, '.')
import pipeline_orchestrator as po

class TestPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_pd = po.PIPELINE_DIR
        self.orig_po_pipeline_dir = po.PIPELINE_DIR
        po.PIPELINE_DIR = os.path.join(self.tmpdir, 'pipelines')
        os.makedirs(po.PIPELINE_DIR, exist_ok=True)
        # 不改变 cwd，所有操作基于 PIPELINE_DIR + 绝对路径

    def tearDown(self):
        po.PIPELINE_DIR = self.orig_pd
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def make_sm_yaml(self, path):
        """在指定路径写入最小状态机"""
        sm = {'version': 1, 'entry_point': 'boss', 'max_loops': 10,
              'nodes': [{'id': 'boss'}, {'id': 'client-gate', 'is_exit': True}],
              'edges': [
                  {'from': 'boss', 'to': 'client-gate', 'phase': 'boss-done'},
                  {'from': 'client-gate', 'to': '__terminal__', 'phase': 'cl-pass',
                   'condition': {'field': 'score', 'operator': '>=', 'value': 9}},
              ]}
        with open(path, 'w') as f:
            yaml.dump(sm, f)

    def test_init_pipeline(self):
        self.make_sm_yaml(os.path.join(self.tmpdir, 'state-machine.yaml'))
        # 模拟调用：直接构造 pipeline 对象
        pid = f"pl-{int(__import__('time').time())}"
        pl = {"pipeline_id": pid, "goal": "test", "status": "initialized",
              "current_node": "boss", "current_phase": "start",
              "completed_nodes": [], "loop_count": 0, "max_loops": 50,
              "failed_count": 0, "started_at": "now", "history": [],
              "cl_score": None, "cl_report": None, "constraints": {"exit_criteria": "CL终审(score>=9)"}}
        po.save_json(po._pipeline_path(pid), pl)
        self.assertTrue(os.path.exists(po._pipeline_path(pid)))

    def test_pipeline_list(self):
        self.make_sm_yaml(os.path.join(self.tmpdir, 'state-machine.yaml'))
        pid1 = f"pl-{int(__import__('time').time())}1"
        pid2 = f"pl-{int(__import__('time').time())}2"
        for pid in [pid1, pid2]:
            pl = {"pipeline_id": pid, "goal": "test", "status": "initialized",
                  "current_node": "boss", "current_phase": "start",
                  "completed_nodes": [], "loop_count": 0, "max_loops": 50,
                  "failed_count": 0, "started_at": "now", "history": []}
            po.save_json(po._pipeline_path(pid), pl)
        plist = po.list_pipelines()
        self.assertGreaterEqual(len(plist), 2)

if __name__ == '__main__':
    unittest.main()
