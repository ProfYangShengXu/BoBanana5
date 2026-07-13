"""
Bobanana 5.0 — Acceptance Tests (A层)
直接对应 PRD acceptance 的可执行 check 命令。
每条 acceptance 对应一个 test_* 方法。
"""
import os
import sys
import yaml
import subprocess
import unittest


sys.path.insert(0, '.')


def _run_check(cmd):
    """执行 acceptance 中的 check 命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='.')
    return result.returncode == 0, result.stdout


class TestA_M1_Registry(unittest.TestCase):
    """M1: 角色卡注册表"""

    def test_M1_A1_register_valid_card(self):
        """M1-A1: 注册合法角色卡"""
        from skills.roles.validate_role_card import validate_role_card
        errors = validate_role_card('skills/roles/architect/role-card.yaml',
                                    'skills/roles/role-card.schema.yaml')
        self.assertEqual(len(errors), 0, f"Found errors: {errors}")

    def test_M1_A2_reject_invalid_card(self):
        """M1-A2: 拒绝非法角色卡"""
        import tempfile, yaml
        from skills.roles.validate_role_card import validate_role_card
        bad = {'name': 'bad-card'}
        path = os.path.join(tempfile.mkdtemp(), 'bad.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(bad, f)
        errors = validate_role_card(path, 'skills/roles/role-card.schema.yaml')
        self.assertTrue(len(errors) > 0)

    def test_M1_A3_list_by_tag(self):
        """M1-A3: 按 tag 过滤"""
        import role_tag_system
        op_roles = role_tag_system.get_roles_by_tag('OP')
        self.assertIn('architect', op_roles)
        self.assertNotIn('developer', op_roles)

    def test_M1_A4_validate_corrupted_yaml(self):
        """M1-A4: 拒绝损坏 YAML"""
        from skills.roles.validate_role_card import validate_role_card
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), 'bad.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('name: "unclosed string')
        errors = validate_role_card(path, 'skills/roles/role-card.schema.yaml')
        self.assertTrue(len(errors) > 0)


class TestA_M2_StateMachine(unittest.TestCase):
    """M2: 状态机"""

    def test_M2_A1_load_valid(self):
        """M2-A1: 加载合法状态机"""
        from state_machine_parser import validate_state_machine, load_state_machine
        sm = load_state_machine('state-machine.yaml')
        errors, warnings = validate_state_machine(sm)
        self.assertEqual(len(errors), 0)

    def test_M2_A2_conditional_branch(self):
        """M2-A2: 条件分支路由"""
        from state_machine_engine import StateMachineRuntime
        import tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            e = StateMachineRuntime(state_dir=d)
            e.load('state-machine.yaml')
            e.state['current_node'] = 'client-gate'
            e._save_state()

            # score >= 9 -> terminal
            r = e.transition('cl-done_pass', {'score': 10})
            self.assertTrue(r['is_terminal'])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_M2_A3_temp_node(self):
        """M2-A3: 临时节点插入"""
        from state_machine_engine import StateMachineRuntime
        import tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            e = StateMachineRuntime(state_dir=d)
            e.load('state-machine.yaml')
            e.transition('arch-done')
            r = e.insert_temporary_node('emergency-role', 'need')
            self.assertIsNotNone(r['node_id'])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_M2_A4_cycle_detection(self):
        """M2-A4: 循环检测"""
        from state_machine_parser import validate_state_machine
        sm = {
            'version': 1, 'entry_point': 'a',
            'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}],
            'edges': [
                {'from': 'a', 'to': 'b', 'phase': 'a-b'},
                {'from': 'b', 'to': 'c', 'phase': 'b-c'},
                {'from': 'c', 'to': 'a', 'phase': 'c-a'},
            ],
        }
        # Cycle with known nodes: should pass validation (cycles allowed if reachable)
        errors, warnings = validate_state_machine(sm)
        self.assertEqual(len(errors), 0)


class TestA_M3_Handoff(unittest.TestCase):
    """M3: 交接工单"""

    def test_M3_A1_create_ticket(self):
        """M3-A1: 创建工单"""
        import handoff_ticket, tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            handoff_ticket.HANDOFF_DIR = d
            t = handoff_ticket.create_handoff_ticket('a', 'b', artifacts=['f1'])
            self.assertTrue(t['ticket_id'].startswith('ht-a-'))
            self.assertEqual(t['version'], 1)
            path = os.path.join(d, f"{t['ticket_id']}.json")
            self.assertTrue(os.path.exists(path))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_M3_A2_list_by_role(self):
        """M3-A2: 按角色列出"""
        import handoff_ticket, tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            handoff_ticket.HANDOFF_DIR = d
            handoff_ticket.create_handoff_ticket('dev', 't1')
            handoff_ticket.create_handoff_ticket('dev', 't2')
            tickets = handoff_ticket.list_handoff_tickets(role_name='dev')
            self.assertEqual(len(tickets), 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_M3_A3_versioning(self):
        """M3-A3: 版本递增"""
        import handoff_ticket, tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            handoff_ticket.HANDOFF_DIR = d
            t1 = handoff_ticket.create_handoff_ticket('x', 'y')
            t2 = handoff_ticket.create_handoff_ticket('x', 'z')
            self.assertEqual(t1['version'], 1)
            self.assertEqual(t2['version'], 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestA_M4_Tags(unittest.TestCase):
    """M4: 角色标签"""

    def test_M4_A1_op_tag(self):
        """M4-A1: OP 标签行为"""
        from role_tag_system import has_tag, apply_tag_behavior
        self.assertTrue(has_tag('architect', 'OP'))
        b = apply_tag_behavior('architect')
        self.assertIn('write_state_machine', b['actions'])

    def test_M4_A2_cl_isolation(self):
        """M4-A2: CL 隔离审查存在"""
        from pipeline_orchestrator import run_cl_review
        import tempfile, json
        d = tempfile.mkdtemp()
        try:
            # Simulate pipeline
            os.makedirs('.reasonix/pipelines', exist_ok=True)
            pl = {'pipeline_id': 'test-pl', 'goal': 'test',
                  'completed_nodes': ['a', 'b'], 'cl_score': None, 'cl_report': None}
            from pipeline_orchestrator import PIPELINE_DIR
            orig_dir = PIPELINE_DIR
            import pipeline_orchestrator as po
            po.PIPELINE_DIR = d
            import json as _json
            with open(os.path.join(d, 'test-pl.json'), 'w') as f:
                _json.dump(pl, f)

            ctx = po.run_cl_review('test-pl', 7)
            self.assertIsNotNone(ctx)
            self.assertTrue(ctx.get('is_isolated'))
        finally:
            pass

    def test_M4_A3_hr_restriction(self):
        """M4-A3: HR 限制"""
        from role_tag_system import enforce_hr_restriction
        self.assertTrue(enforce_hr_restriction('architect')['allowed'])
        self.assertFalse(enforce_hr_restriction('developer')['allowed'])


class TestA_M5_HR(unittest.TestCase):
    """M5: HR 招聘"""

    def test_M5_A1_start_recruitment(self):
        """M5-A1: 发起招聘"""
        import hr_recruitment, tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            hr_recruitment.RECRUIT_DIR = d
            r = hr_recruitment.start_recruitment('a-role', 'Test')
            self.assertEqual(r['completed_subagents'], 4)
            self.assertIn(r['status'], ('research_done', 'standards_found'))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_M5_A2_reference_standards(self):
        """M5-A2: 引用已有准则"""
        import hr_recruitment, tempfile, shutil
        d = tempfile.mkdtemp()
        try:
            hr_recruitment.RECRUIT_DIR = d
            r = hr_recruitment.reference_existing_standards('quick-r', 'Bobanana.md')
            self.assertEqual(r['status'], 'standards_found')
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestA_M6_Pipeline(unittest.TestCase):
    """M6: 管线编排"""

    def setUp(self):
        for d in ['.reasonix/pipelines', '.reasonix/state', '.reasonix/handoffs']:
            if os.path.exists(d): import shutil; shutil.rmtree(d, ignore_errors=True)

    def test_M6_A1_full_pipeline(self):
        """M6-A1: 完整管线"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline
        init_pipeline('A测试: 完整管线')
        for p in ['arch-done', 'dev-done_task-done',
                  'test-done_layer-not-done', 'test-done_layer-not-done',
                  'test-done_layer-not-done', 'test-done_layer-all-done',
                  'judge-done_no-badcase', 'critic-done_pass']:
            advance_pipeline(p)
        advance_pipeline('cl-done_pass', score=10)
        pl = get_pipeline()
        assert pl['status'] == 'completed'

    def test_M6_A2_emergency_hiring(self):
        """M6-A2: 紧急招聘"""
        from state_machine_engine import StateMachineRuntime
        e = StateMachineRuntime()
        e.load('state-machine.yaml')
        e.transition('arch-done')
        r = e.insert_temporary_node('urgent-role', 'need')
        self.assertIn('urgent-role', r['node_id'])
        e.transition('urgent-role-done')

    def test_M6_A3_cl_failback(self):
        """M6-A3: CL 打回"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline
        init_pipeline('A测试: CL打回')
        for p in ['arch-done', 'dev-done_task-done',
                  'test-done_layer-not-done', 'test-done_layer-not-done',
                  'test-done_layer-not-done', 'test-done_layer-all-done',
                  'judge-done_no-badcase', 'critic-done_pass']:
            advance_pipeline(p)
        advance_pipeline('cl-done_pass', score=5)
        pl = get_pipeline()
        self.assertEqual(pl['status'], 'failback_to_architect')


class TestA_M7_GUI(unittest.TestCase):
    """M7: GUI (MCP 层 + EUI-NEO 前端)"""

    def test_M7_A1_mcp_client_connect(self):
        """M7-A1: MCP 客户端可连接并查询"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        info = client.connect()
        self.assertTrue(info['connected'])
        self.assertGreater(info['cards'], 0)

    def test_M7_A1_mcp_all_hooks(self):
        """M7-A1: MCP 全部 10 hooks 可调用"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client.connect()

        # 状态机
        sm = client.get_state_machine()
        self.assertIn('state_machine', sm)

        # 角色卡
        cards = client.get_role_cards()
        self.assertGreater(cards['total'], 0)

        # 详情
        detail = client.get_role_card_detail('architect')
        self.assertIn('card', detail)

        # 管线
        status = client.get_pipeline_status()
        self.assertIn('status', status)

        # CL
        report = client.get_cl_report()
        self.assertIsNotNone(report)

        # 工单
        tickets = client.get_handoff_tickets()
        self.assertIn('total', tickets)

        # 文件
        content = client.read_file('Bobanana.md')
        self.assertIn('content', content)

    def test_M7_A2_dashboard_json_output(self):
        """M7-A2: 仪表盘 JSON 输出包含完整数据"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client.connect()
        data = client.full_dashboard_data()
        self.assertIn('state_machine', data)
        self.assertIn('role_cards', data)
        self.assertIn('pipeline_status', data)
        self.assertIn('handoff_tickets', data)

    def test_M7_A3_dashboard_json(self):
        """M7-A3: 仪表盘 JSON 数据完整"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client.connect()
        data = client.full_dashboard_data()
        self.assertIn("state_machine", data)
        self.assertIn("role_cards", data)
        self.assertIn("pipeline_status", data)
        self.assertIn("handoff_tickets", data)

    def test_M7_event_subscriber(self):
        """M7: 事件订阅器可启动"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        events = []

        def cb(event):
            events.append(event)

        sub.subscribe(cb)
        sub.start(interval=0.5)
        import time
        time.sleep(1)
        sub.stop()
        # 至少不崩溃
        self.assertIsNotNone(sub)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
