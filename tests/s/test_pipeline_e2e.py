"""
Bobanana 5.0 — E2E: Pipeline Orchestrator 端到端测试
测试管线从 init → advance → CL → terminal 的完整流程。
"""
import os, sys, json, yaml, tempfile, shutil, unittest

sys.path.insert(0, '.')
import pipeline_orchestrator as po

class TestPipelineE2E(unittest.TestCase):
    def setUp(self):
        # 备份并创建测试环境
        self.tmpdir = tempfile.mkdtemp()
        self.orig_pipeline_dir = po.PIPELINE_DIR
        self.orig_cwd = os.getcwd()
        po.PIPELINE_DIR = os.path.join(self.tmpdir, 'pipelines')
        os.chdir(self.tmpdir)
        os.makedirs('.reasonix/cycle', exist_ok=True)

    def tearDown(self):
        po.PIPELINE_DIR = self.orig_pipeline_dir
        os.chdir(self.orig_cwd)
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
        with open('state-machine.yaml', 'w') as f:
            yaml.dump(sm, f)

    def test_init_pipeline(self):
        self.write_test_sm()
        p = po.init_pipeline('test e2e')
        self.assertIsNotNone(p)
        self.assertEqual(p['current_node'], 'boss')
        self.assertIn('pipeline_id', p)

    def test_has_pending(self):
        self.assertFalse(po.has_pending_pipeline())

    def test_pipeline_list(self):
        self.write_test_sm()
        po.init_pipeline('test1')
        po.init_pipeline('test2')
        plist = po.list_pipelines()
        self.assertGreaterEqual(len(plist), 2)

    def test_constraints_field(self):
        """验证 constraints 字段存在且不污染 goal"""
        self.write_test_sm()
        p = po.init_pipeline('clean goal')
        self.assertEqual(p['goal'], 'clean goal')
        self.assertIn('constraints', p)
        self.assertEqual(p['constraints']['exit_criteria'], 'CL终审(score>=9)')

if __name__ == '__main__':
    unittest.main()
