"""
Bobanana 5.0 — Chaos: 边角测试
"""
import os, yaml, json, tempfile, shutil, unittest
import sys
sys.path.insert(0, '.')

def _clean():
    for d in ['.reasonix/state', '.reasonix/pipelines', '.reasonix/cycle']:
        if os.path.exists(d): shutil.rmtree(d)

class TestChaosEmptyGoal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _clean()
    def setUp(self):
        _clean()
    def test_empty_string_goal(self):
        from pipeline_orchestrator import init_pipeline
        p = init_pipeline('')
        self.assertIsNotNone(p)
        _clean()
    def test_very_long_goal(self):
        _clean()
        from pipeline_orchestrator import init_pipeline
        p = init_pipeline('x' * 10000)
        self.assertIsNotNone(p)
        _clean()
    def test_special_chars_in_goal(self):
        _clean()
        from pipeline_orchestrator import init_pipeline
        p = init_pipeline('!@#$%^&*()_+{}[]|\\:;"\'<>,.?/~`')
        self.assertIsNotNone(p)
        _clean()

class TestChaosEmptyFile(unittest.TestCase):
    def test_empty_yaml_file(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        tmp.write('')
        tmp.close()
        try:
            result = yaml.safe_load(open(tmp.name))
            self.assertIsNone(result)
        finally:
            os.unlink(tmp.name)

class TestChaosNonexistentSM(unittest.TestCase):
    def test_nonexistent_state_machine(self):
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime()
        with self.assertRaises((FileNotFoundError, ValueError)):
            engine.load('/nonexistent/path.yaml')

class TestChaosHandoffEdge(unittest.TestCase):
    def test_dict_merge_edge(self):
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
