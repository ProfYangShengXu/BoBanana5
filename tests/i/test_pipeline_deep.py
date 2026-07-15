"""
Bobanana 5.0 — Integration: Pipeline Orchestrator 深入测试
"""
import os, sys, yaml, json, tempfile, shutil, unittest

sys.path.insert(0, '.')

class TestPipelineRepair(unittest.TestCase):
    """pipeline repair 命令测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('.reasonix/cycle', exist_ok=True)
        os.makedirs('.reasonix/pipelines', exist_ok=True)
        # Create minimal SM
        sm = {'version': 1, 'entry_point': 'boss', 'max_loops': 10,
              'nodes': [{'id': 'boss'}, {'id': 'client-gate', 'is_exit': True}],
              'edges': [{'from': 'boss', 'to': 'client-gate', 'phase': 'boss-done'},
                        {'from': 'client-gate', 'to': '__terminal__', 'phase': 'cl-pass'}]}
        with open('state-machine.yaml', 'w') as f:
            yaml.dump(sm, f)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def test_cmd_repair_creates_files(self):
        import pipeline_orchestrator as po
        po.PIPELINE_DIR = os.path.join(self.tmpdir, 'pipelines')
        p = po.init_pipeline('test repair')
        self.assertIsNotNone(p)
        pid = p['pipeline_id']
        # Delete cycle state to simulate corruption
        cycle_state = os.path.join(self.tmpdir, '.reasonix', 'cycle', 'state.json')
        if os.path.exists(cycle_state):
            os.remove(cycle_state)
        # Run repair
        import argparse
        args = argparse.Namespace(pipeline=pid)
        result = po.cmd_repair(args)
        self.assertEqual(result, 0)
        self.assertTrue(os.path.exists(cycle_state))

    def test_no_pending_after_terminal(self):
        import pipeline_orchestrator as po
        po.PIPELINE_DIR = os.path.join(self.tmpdir, 'pipelines')
        p = po.init_pipeline('term test')
        # Simulate CL pass
        p['status'] = 'completed'
        p['current_node'] = '__terminal__'
        with open(po._pipeline_path(p['pipeline_id']), 'w') as f:
            json.dump(p, f)
        self.assertFalse(po.has_pending_pipeline())

class TestPipelineConstraints(unittest.TestCase):
    """pipeline constraints 字段测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import pipeline_orchestrator as po
        self.orig_pd = po.PIPELINE_DIR
        self.orig_cd = po.CYCLE_DIR
        self.orig_sd = po.STATE_MACHINE_DIR
        po.PIPELINE_DIR = os.path.join(self.tmpdir, 'pipelines')
        po.CYCLE_DIR = os.path.join(self.tmpdir, 'cycle')
        po.STATE_MACHINE_DIR = os.path.join(self.tmpdir, 'state')
        os.makedirs(po.PIPELINE_DIR, exist_ok=True)

    def tearDown(self):
        import pipeline_orchestrator as po
        po.PIPELINE_DIR = self.orig_pd
        po.CYCLE_DIR = self.orig_cd
        po.STATE_MACHINE_DIR = self.orig_sd
        shutil.rmtree(self.tmpdir)

    def test_constraints_not_in_goal(self):
        import pipeline_orchestrator as po
        p = po.init_pipeline('clean goal text')
        self.assertEqual(p['goal'], 'clean goal text')
        self.assertIn('constraints', p)
        self.assertEqual(p['constraints']['exit_criteria'], 'CL终审(score>=9)')

    def test_init_creates_pipeline_file(self):
        import pipeline_orchestrator as po
        p = po.init_pipeline('test')
        pp = po._pipeline_path(p['pipeline_id'])
        self.assertTrue(os.path.exists(pp))

if __name__ == '__main__':
    unittest.main()
