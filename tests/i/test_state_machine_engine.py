"""
Bobanana 5.0 — Integration: State Machine Engine
测试状态机引擎的加载、流转、条件分支、临时节点。
"""
import os, sys, yaml, json, tempfile, shutil, unittest

sys.path.insert(0, '.')
from state_machine_engine import StateMachineRuntime

SIMPLE_SM = """
version: 1
entry_point: "start"
max_loops: 10
nodes:
  - id: "start"
  - id: "middle"
  - id: "end"
  - id: "exit"
    is_exit: true
edges:
  - from: "start"
    to: "middle"
    phase: "start-done"
  - from: "middle"
    to: "end"
    phase: "middle-done"
  - from: "end"
    to: "exit"
    phase: "end-done"
  - from: "exit"
    to: "__terminal__"
    phase: "exit-pass"
    condition:
      field: score
      operator: ">="
      value: 9
  - from: "exit"
    to: "start"
    phase: "exit-fail"
    condition:
      field: score
      operator: "<"
      value: 9
"""

class TestStateMachine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.sm_path = os.path.join(self.tmpdir, 'test-sm.yaml')
        with open(self.sm_path, 'w') as f:
            f.write(SIMPLE_SM)
        self.engine = StateMachineRuntime(state_dir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_load(self):
        state = self.engine.load(self.sm_path)
        self.assertEqual(state['current_node'], 'start')
        self.assertEqual(state['current_phase'], 'start')

    def test_transition_normal(self):
        self.engine.load(self.sm_path)
        result = self.engine.transition('start-done')
        self.assertEqual(result['current_node'], 'middle')
        self.assertEqual(result['phase'], 'start-done')

    def test_transition_full_chain(self):
        self.engine.load(self.sm_path)
        self.engine.transition('start-done')
        self.engine.transition('middle-done')
        result = self.engine.transition('end-done')
        self.assertEqual(result['current_node'], 'exit')

    def test_condition_pass(self):
        self.engine.load(self.sm_path)
        self.engine.transition('start-done')
        self.engine.transition('middle-done')
        self.engine.transition('end-done')
        result = self.engine.transition('exit-pass', context={'score': 10})
        self.assertTrue(result['is_terminal'])

    def test_condition_fail(self):
        self.engine.load(self.sm_path)
        self.engine.transition('start-done')
        self.engine.transition('middle-done')
        self.engine.transition('end-done')
        result = self.engine.transition('exit-fail', context={'score': 5})
        self.assertEqual(result['current_node'], 'start')

    def test_invalid_phase(self):
        self.engine.load(self.sm_path)
        with self.assertRaises(ValueError):
            self.engine.transition('nonexistent-phase')

    def test_max_loops(self):
        sm_path2 = os.path.join(self.tmpdir, 'sm2.yaml')
        with open(sm_path2, 'w') as f:
            f.write(SIMPLE_SM.replace('max_loops: 10', 'max_loops: 2'))
        engine = StateMachineRuntime(state_dir=self.tmpdir)
        engine.load(sm_path2)
        engine.transition('start-done')
        engine.transition('middle-done')
        engine.state['loop_count'] = 2
        with self.assertRaises(RuntimeError):
            engine.transition('end-done')

    def test_available_transitions(self):
        self.engine.load(self.sm_path)
        trans = self.engine.get_available_transitions()
        self.assertEqual(len(trans), 1)
        self.assertEqual(trans[0]['phase'], 'start-done')

    def test_insert_temporary_node(self):
        self.engine.load(self.sm_path)
        self.engine.transition('start-done')
        self.engine.insert_temporary_node('urgent-fix', 'urgent')
        state = self.engine.state
        self.assertIn('urgent-fix', [n['id'] for n in self.engine.config['nodes']])

if __name__ == '__main__':
    unittest.main()
