"""
Bobanana 5.0 — 真实端到端管线测试
使用真实 state-machine.yaml，直接操作 pipeline 文件，不调用 init_pipeline。
"""
import os, sys, yaml, json, tempfile, shutil, unittest, time

sys.path.insert(0, '.')
import pipeline_orchestrator as po
from state_machine_engine import StateMachineRuntime

_pipeline_counter = 0

def _create_test_pipeline(tmpdir, goal="test goal"):
    """创建测试用 pipeline 文件，返回 pipeline dict"""
    global _pipeline_counter
    _pipeline_counter += 1
    pid = f"pl-{int(time.time() * 1000)}-{_pipeline_counter}"
    pl = {
        "pipeline_id": pid, "goal": goal, "status": "initialized",
        "current_node": "boss", "current_phase": "start",
        "completed_nodes": [], "loop_count": 0, "max_loops": 50,
        "failed_count": 0, "started_at": "now", "history": [],
        "cl_score": None, "cl_report": None,
        "constraints": {"exit_criteria": "CL终审(score>=9)"},
    }
    po.save_json(os.path.join(po.PIPELINE_DIR, f"{pid}.json"), pl)
    return pl


class TestPipelineFullE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.orig_pd = po.PIPELINE_DIR
        po.PIPELINE_DIR = os.path.join(cls.tmpdir, 'pipelines')
        os.makedirs(po.PIPELINE_DIR, exist_ok=True)

        cls.real_sm_path = 'state-machine.yaml'
        cls.test_sm_path = os.path.join(cls.tmpdir, 'state-machine.yaml')
        if os.path.exists(cls.real_sm_path):
            shutil.copy2(cls.real_sm_path, cls.test_sm_path)

    @classmethod
    def tearDownClass(cls):
        po.PIPELINE_DIR = cls.orig_pd
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        if os.path.exists(po.PIPELINE_DIR):
            shutil.rmtree(po.PIPELINE_DIR)
        os.makedirs(po.PIPELINE_DIR, exist_ok=True)

    # ── 核心 E2E 测试 ──

    def test_engine_loads_real_sm(self):
        engine = StateMachineRuntime()
        if not os.path.exists(self.test_sm_path):
            self.skipTest("SM file not found")
        engine.load(self.test_sm_path)
        self.assertGreater(len(engine.config['nodes']), 5)
        self.assertGreater(len(engine.config['edges']), 5)

    def test_engine_boss_to_architect(self):
        engine = StateMachineRuntime()
        if not os.path.exists(self.test_sm_path):
            self.skipTest("SM file not found")
        engine.load(self.test_sm_path)
        r = engine.transition('boss-done')
        self.assertEqual(r['to'], 'architect')

    def test_engine_has_available_transitions(self):
        engine = StateMachineRuntime()
        if not os.path.exists(self.test_sm_path):
            self.skipTest("SM file not found")
        engine.load(self.test_sm_path)
        trans = engine.get_available_transitions()
        self.assertGreater(len(trans), 0)

    def test_pipeline_has_pending_false_empty(self):
        self.assertFalse(po.has_pending_pipeline())

    def test_pipeline_has_pending_true_after_create(self):
        _create_test_pipeline(self.tmpdir)
        self.assertTrue(po.has_pending_pipeline())

    def test_pipeline_has_pending_false_completed(self):
        pl = _create_test_pipeline(self.tmpdir)
        pl['status'] = 'completed'
        pl['current_node'] = '__terminal__'
        po.save_json(os.path.join(po.PIPELINE_DIR, f"{pl['pipeline_id']}.json"), pl)
        self.assertFalse(po.has_pending_pipeline())

    def test_pipeline_list(self):
        _create_test_pipeline(self.tmpdir, "goal1")
        _create_test_pipeline(self.tmpdir, "goal2")
        pipelines = po.list_pipelines()
        self.assertGreaterEqual(len(pipelines), 2)

    def test_get_pipeline_by_id(self):
        pl = _create_test_pipeline(self.tmpdir)
        found = po.get_pipeline(pl['pipeline_id'])
        self.assertEqual(found['goal'], pl['goal'])

    def test_get_pipeline_latest(self):
        pl1 = _create_test_pipeline(self.tmpdir, "first")
        pl2 = _create_test_pipeline(self.tmpdir, "second")
        latest = po.get_pipeline()
        self.assertEqual(latest['goal'], "second")

    def test_constraints_field(self):
        pl = _create_test_pipeline(self.tmpdir, "clean goal")
        self.assertEqual(pl['goal'], "clean goal")
        self.assertIn('constraints', pl)
        self.assertEqual(pl['constraints']['exit_criteria'], 'CL终审(score>=9)')

    def test_generate_sm_script_exists(self):
        self.assertTrue(os.path.exists('scripts/generate_state_machine.py'))

    def test_role_usage_script_exists(self):
        self.assertTrue(os.path.exists('scripts/role_usage.py'))

    def test_sm_yaml_parses(self):
        with open('state-machine.yaml') as f:
            sm = yaml.safe_load(f)
        self.assertIsNotNone(sm)
        self.assertIn('nodes', sm)
        self.assertIn('edges', sm)


if __name__ == '__main__':
    unittest.main()
