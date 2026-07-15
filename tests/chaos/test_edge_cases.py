"""
Bobanana 5.0 — Chaos: 边角测试 (null/empty/large)
"""
import os, sys, yaml, json, tempfile, shutil, unittest

sys.path.insert(0, '.')

class TestChaosEdgeCases(unittest.TestCase):
    """边角场景"""

    def test_empty_string_goal(self):
        from pipeline_orchestrator import init_pipeline, has_pending_pipeline
        p = init_pipeline('')
        self.assertIsNotNone(p)
        # 清理
        import shutil
        for d in ['.reasonix/state', '.reasonix/pipelines', '.reasonix/cycle']:
            if os.path.exists(d): shutil.rmtree(d)

    def test_very_long_goal(self):
        from pipeline_orchestrator import init_pipeline
        long_goal = 'x' * 10000
        p = init_pipeline(long_goal)
        self.assertIsNotNone(p)

    def test_special_chars_in_goal(self):
        from pipeline_orchestrator import init_pipeline
        p = init_pipeline('!@#$%^&*()_+{}[]|\\:;"\'<>,.?/~`')
        self.assertIsNotNone(p)
        import shutil
        for d in ['.reasonix/state', '.reasonix/pipelines', '.reasonix/cycle']:
            if os.path.exists(d): shutil.rmtree(d)

    def test_empty_yaml_file(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        tmp.write('')
        tmp.close()
        try:
            result = yaml.safe_load(open(tmp.name))
            self.assertIsNone(result)
        finally:
            os.unlink(tmp.name)

    def test_nonexistent_state_machine(self):
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime()
        with self.assertRaises((FileNotFoundError, ValueError)):
            engine.load('/nonexistent/path.yaml')

    def test_dict_merge_edge(self):
        """handoff_ticket 的 assumptions 合并"""
        import handoff_ticket as ht
        tmpdir = tempfile.mkdtemp()
        orig = ht.HANDOFF_DIR
        ht.HANDOFF_DIR = tmpdir
        try:
            t = ht.create_handoff_ticket('a', 'b')
            self.assertIsNotNone(t)
            self.assertIn('assumptions', t)
        finally:
            ht.HANDOFF_DIR = orig
            shutil.rmtree(tmpdir)

if __name__ == '__main__':
    unittest.main()
