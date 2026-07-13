"""
Bobanana 5.0 — Scenario Tests (S层)
完整端到端场景测试，每场景三路径。
"""
import os
import sys
import shutil
import unittest
import tempfile


sys.path.insert(0, '.')


def _clean():
    for d in ['.reasonix/pipelines', '.reasonix/state', '.reasonix/handoffs', '.reasonix/recruitments']:
        if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)


class TestS_FullPipeline(unittest.TestCase):
    """场景: 完整管线流程"""

    def setUp(self):
        _clean()

    def tearDown(self):
        _clean()

    def test_normal_full_pipeline_to_done(self):
        """正常场景: 完整管线 → CL通过 → signal_done"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline

        init_pipeline('S场景: 完整管线')
        steps = [
            'arch-done', 'dev-done_task-done',
            'test-done_layer-not-done', 'test-done_layer-not-done',
            'test-done_layer-not-done', 'test-done_layer-all-done',
            'judge-done_no-badcase', 'critic-done_pass',
        ]
        for p in steps:
            advance_pipeline(p)

        advance_pipeline('cl-done_pass', score=10)
        pl = get_pipeline()
        assert pl['status'] == 'completed', f"Expected completed, got {pl['status']}"
        assert pl['loop_count'] == 9
        assert len(pl['completed_nodes']) == 9
        assert pl['cl_score'] == 10

    def test_boundary_cl_failback_scenario(self):
        """边界场景: CL 打回 → 架构师重新规划"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline

        init_pipeline('S场景: CL打回')
        for p in ['arch-done', 'dev-done_task-done',
                  'test-done_layer-not-done', 'test-done_layer-not-done',
                  'test-done_layer-not-done', 'test-done_layer-all-done',
                  'judge-done_no-badcase', 'critic-done_pass']:
            advance_pipeline(p)

        advance_pipeline('cl-done_pass', score=4)
        pl = get_pipeline()
        assert pl['status'] == 'failback_to_architect', f"Expected failback, got {pl['status']}"
        assert pl['current_node'] == 'architect', f"Should return to architect"
        assert pl['failed_count'] == 1

    def test_adversarial_max_loops_reached(self):
        """对抗场景: 超过最大循环次数"""
        from pipeline_orchestrator import init_pipeline, get_pipeline
        init_pipeline('S场景: 上限测试')
        pl = get_pipeline()
        pl['loop_count'] = 49
        from pipeline_orchestrator import save_json, _pipeline_path
        save_json(_pipeline_path(pl['pipeline_id']), pl)

        from pipeline_orchestrator import advance_pipeline
        result = advance_pipeline('arch-done')
        assert result is not None, "Should still work at loop 49->50"

        result = advance_pipeline('dev-done_task-done')
        assert result is not None  # loop advances to 50


class TestS_EmergencyHiring(unittest.TestCase):
    """场景: 紧急招聘流程"""

    def setUp(self):
        _clean()

    def tearDown(self):
        _clean()

    def test_normal_hr_hiring_scenario(self):
        """正常场景: 检测缺口 → HR招聘 → 新卡就绪"""
        from state_machine_engine import StateMachineRuntime

        engine = StateMachineRuntime()
        engine.load('state-machine.yaml')
        engine.transition('arch-done')

        # OP 检测到缺少 '数值策划' 角色卡
        import os as _os
        card_exists = _os.path.exists('skills/roles/value-designer/role-card.yaml')
        if not card_exists:
            # 触发 HR 紧急招聘
            result = engine.insert_temporary_node('value-designer', 'arch-needs-hiring')
            assert 'value-designer' in result['node_id']

            # HR 完成, 返回
            engine.transition('value-designer-done')
            assert engine.state['current_node'] == 'developer'

    def test_boundary_hr_multiple_hirings(self):
        """边界场景: 多次紧急招聘"""
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime()
        engine.load('state-machine.yaml')
        engine.transition('arch-done')

        # 第一次招聘
        r1 = engine.insert_temporary_node('role-a', 'need-a')
        engine.transition('role-a-done')

        # 第二次招聘
        r2 = engine.insert_temporary_node('role-b', 'need-b')
        engine.transition('role-b-done')
        assert engine.state['current_node'] == 'developer'
        assert len(engine.state['temporary_nodes']) == 0


class TestS_HandoffFlow(unittest.TestCase):
    """场景: 交接工单流转"""

    def setUp(self):
        _clean()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        _clean()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_normal_handoff_chain(self):
        """正常场景: 多角色连续交接"""
        import handoff_ticket
        handoff_ticket.HANDOFF_DIR = self.tmpdir

        tickets = []
        pairs = [('architect', 'developer'), ('developer', 'tester-unit'),
                 ('tester-unit', 'judge'), ('judge', 'critic'), ('critic', 'client-gate')]
        for s, r in pairs:
            t = handoff_ticket.create_handoff_ticket(s, r, artifacts=[f'{s}_output'])
            tickets.append(t)

        assert len(tickets) == 5
        assert tickets[-1]['sender_id'] == 'critic'
        assert tickets[-1]['receiver_id'] == 'client-gate'

    def test_boundary_role_ticket_history(self):
        """边界场景: 某角色的完整工单历史"""
        import handoff_ticket
        handoff_ticket.HANDOFF_DIR = self.tmpdir

        handoff_ticket.create_handoff_ticket('dev', 't1')
        handoff_ticket.create_handoff_ticket('arch', 'dev')
        handoff_ticket.create_handoff_ticket('dev', 't2')

        dev_tickets = handoff_ticket.list_handoff_tickets(role_name='dev')
        assert len(dev_tickets) >= 2, f"Expected >=2, got {len(dev_tickets)}"

        latest = handoff_ticket.get_latest_for_role('dev')
        assert latest['receiver_id'] == 't2'


if __name__ == '__main__':
    import tempfile
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
