"""
Bobanana 5.0 — E2E: Pipeline Orchestrator 端到端测试
测试管线从 init → advance → CL → terminal 的完整流程。
"""
import os, sys, json, yaml, tempfile, shutil, unittest

sys.path.insert(0, '.')
import pipeline_orchestrator as po

class TestPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_pd = po.PIPELINE_DIR
        po.PIPELINE_DIR = os.path.join(self.tmpdir, 'pipelines')
        os.makedirs(po.PIPELINE_DIR, exist_ok=True)
        os.chdir(self.tmpdir)
        os.makedirs('.reasonix/cycle', exist_ok=True)

    def tearDown(self):
        po.PIPELINE_DIR = self.orig_pd
        os.chdir(self.orig_cwd if hasattr(self, 'orig_cwd') else '.')
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write_test_sm(self):
        sm = {
            'version': 1, 'entry_point': 'boss', 'max_loops': 10,
            'nodes': [
                {'id': 'boss'},
                {'id': 'architect'},
                {'id': 'client-gate', 'is_exit': True},
            ],
            'edges': [
                {'from': 'boss', 'to': 'architect', 'phase': 'boss-done'},
                {'from': 'architect', 'to': 'client-gate', 'phase': 'arch-done'},
                {'from': 'client-gate', 'to': '__terminal__', 'phase': 'cl-pass', 'condition': {'field': 'score', 'operator': '>=', 'value': 9}},
                {'from': 'client-gate', 'to': 'architect', 'phase': 'cl-fail', 'condition': {'field': 'score', 'operator': '<', 'value': 9}},
            ]
        }
        with open(os.path.join(self.tmpdir, 'state-machine.yaml'), 'w') as f:
            yaml.dump(sm, f)

    def test_init_pipeline(self):
        self.orig_cwd = os.getcwd()
        self.write_test_sm()
        p = po.init_pipeline('test e2e')
        self.assertIsNotNone(p)
        self.assertEqual(p['current_node'], 'boss')

    def test_has_pending_no_state(self):
        self.assertFalse(po.has_pending_pipeline())

    def test_list_pipelines_empty(self):
        self.assertEqual(po.list_pipelines(), [])

    def test_constraints_field(self):
        self.orig_cwd = os.getcwd()
        self.write_test_sm()
        p = po.init_pipeline('clean goal')
        self.assertEqual(p['goal'], 'clean goal')
        self.assertIn('constraints', p)
        self.assertEqual(p['constraints']['exit_criteria'], 'CL终审(score>=9)')

if __name__ == '__main__':
    unittest.main()
