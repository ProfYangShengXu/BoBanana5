"""
Bobanana 5.0 — 多轮循环测试 (E2E)
验证 round/max_rounds 字段, 多轮回Boss逻辑, cycle/plan/exec phase
"""
import os, sys, json, tempfile, shutil, unittest, time

sys.path.insert(0, '.')
import pipeline_orchestrator as po

class TestMultiRound(unittest.TestCase):
    """多轮循环测试"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.orig_pd = po.PIPELINE_DIR
        cls.orig_cd = po.CYCLE_DIR
        po.PIPELINE_DIR = os.path.join(cls.tmpdir, 'pipelines')
        po.CYCLE_DIR = os.path.join(cls.tmpdir, 'cycle')
        os.makedirs(po.PIPELINE_DIR, exist_ok=True)
        po.STATE_MACHINE_DIR = os.path.join(cls.tmpdir, "state")
        os.makedirs(po.CYCLE_DIR, exist_ok=True)
        os.makedirs(po.STATE_MACHINE_DIR, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        po.PIPELINE_DIR = cls.orig_pd
        po.CYCLE_DIR = cls.orig_cd
        po.STATE_MACHINE_DIR = ".reasonix/state"
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        for d in [po.PIPELINE_DIR, po.CYCLE_DIR]:
            if os.path.exists(d): shutil.rmtree(d)
            os.makedirs(d, exist_ok=True)
        if os.path.exists(po.STATE_MACHINE_DIR): shutil.rmtree(po.STATE_MACHINE_DIR)
        os.makedirs(po.STATE_MACHINE_DIR, exist_ok=True)
        self.counter = 0

    def _make_pl(self, goal="test", node="boss"):
        self.counter += 1
        pid = f"pl-{int(time.time()*1000)}-{self.counter}"
        pl = {"pipeline_id": pid, "goal": goal, "status": "initialized",
              "current_node": node, "current_phase": "start",
              "completed_nodes": [], "loop_count": 0, "max_loops": 50,
              "failed_count": 0, "round": 1, "max_rounds": 1,
              "started_at": "now", "history": [], "cl_score": None, "cl_report": None}
        return pl

    def test_default_rounds_is_1(self):
        """init_pipeline 默认 rounds=1"""
        p = po.init_pipeline("test")
        if p:
            self.assertEqual(p['max_rounds'], 1)
            self.assertEqual(p['round'], 1)

    def test_init_with_rounds_3(self):
        """init_pipeline(goal, rounds=3) 设置 max_rounds=3"""
        p = po.init_pipeline("test3", rounds=3)
        if p:
            self.assertEqual(p['max_rounds'], 3)
            self.assertEqual(p['round'], 1)

    def test_rounds_increments_in_pipeline(self):
        """pipeline 的 round 字段可递增"""
        pl = self._make_pl()
        pl['round'] = 2
        po.save_json(po._pipeline_path(pl['pipeline_id']), pl)
        loaded = po.get_pipeline(pl['pipeline_id'])
        self.assertEqual(loaded['round'], 2)

    def test_cycle_state_has_rounds(self):
        """cycle state 应包含 round/max_rounds"""
        p = po.init_pipeline("cycle_rounds", rounds=3)
        if not p:
            self.skipTest("pipeline already pending")
        state_path = os.path.join(po.CYCLE_DIR, 'state.json')
        self.assertTrue(os.path.exists(state_path))
        with open(state_path) as f:
            st = json.load(f)
        self.assertIn('round', st)
        self.assertIn('max_rounds', st)

    def test_has_pending_after_init(self):
        """init 后 has_pending_pipeline=True"""
        po.init_pipeline("pending_test")
        self.assertTrue(po.has_pending_pipeline())

    def test_rounds_available_in_cli(self):
        """CLI 应接受 --rounds 参数"""
        import subprocess, sys
        r = subprocess.run([sys.executable, '-m', 'pipeline_orchestrator', 'init', '--help'],
                          capture_output=True, text=True)
        self.assertIn('rounds', r.stdout)

if __name__ == '__main__':
    unittest.main()
