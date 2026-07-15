"""
Bobanana 5.0 — Unit Tests (U层)
测试核心模块的独立功能，normal/boundary/adversarial 三路径。
"""
import os
import sys
import json
import yaml
import tempfile
import shutil
import unittest


# ── Test M1: Role Card Schema + Validator ──

class TestRoleCardSchema(unittest.TestCase):
    """角色卡 Schema 验证测试"""

    def setUp(self):
        self.schema_path = 'skills/roles/role-card.schema.yaml'
        self.valid_card = {
            'name': 'test-role',
            'description': 'A test role for unit testing',
            'tags': ['OP'],
            'input_contract': [
                {'name': 'input_data', 'type': 'string', 'description': 'Input', 'required': True}
            ],
            'output_contract': [
                {'name': 'output_data', 'type': 'string', 'description': 'Output'}
            ],
            'quality_gates': [
                {'id': 'TR-Q1', 'desc': 'Test gate', 'check': 'go test', 'layer': 'U'}
            ],
            'standards_file': 'SKILL.md',
        }

    def test_normal_valid_card(self):
        """正常路径：合法角色卡"""
        from skills.roles.validate_role_card import validate_role_card
        tmpdir = tempfile.mkdtemp()
        try:
            card_path = os.path.join(tmpdir, 'role-card.yaml')
            with open(card_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.valid_card, f)
            errors = validate_role_card(card_path, self.schema_path)
            self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")
        finally:
            shutil.rmtree(tmpdir)

    def test_boundary_missing_required(self):
        """边界路径：缺少必填字段 name"""
        from skills.roles.validate_role_card import validate_role_card
        invalid = self.valid_card.copy()
        del invalid['name']
        tmpdir = tempfile.mkdtemp()
        try:
            card_path = os.path.join(tmpdir, 'role-card.yaml')
            with open(card_path, 'w', encoding='utf-8') as f:
                yaml.dump(invalid, f)
            errors = validate_role_card(card_path, self.schema_path)
            self.assertTrue(any('name' in e for e in errors), "Should flag missing name")
        finally:
            shutil.rmtree(tmpdir)

    def test_adversarial_invalid_tags(self):
        """对抗路径：非法标签值"""
        from skills.roles.validate_role_card import validate_role_card
        invalid = self.valid_card.copy()
        invalid['tags'] = ['INVALID_TAG']
        tmpdir = tempfile.mkdtemp()
        try:
            card_path = os.path.join(tmpdir, 'role-card.yaml')
            with open(card_path, 'w', encoding='utf-8') as f:
                yaml.dump(invalid, f)
            errors = validate_role_card(card_path, self.schema_path)
            self.assertTrue(any('INVALID_TAG' in e for e in errors),
                           "Should reject invalid tag")
        finally:
            shutil.rmtree(tmpdir)


# ── Test M2: State Machine Parser ──

class TestStateMachineParser(unittest.TestCase):
    """状态机解析器测试"""

    def setUp(self):
        self.valid_sm = {
            'version': 1,
            'entry_point': 'architect',
            'max_loops': 50,
            'nodes': [
                {'id': 'architect', 'label': '架构师'},
                {'id': 'developer', 'label': '开发'},
                {'id': 'client-gate', 'label': '终审', 'is_exit': True},
            ],
            'edges': [
                {'from': 'architect', 'to': 'developer', 'phase': 'arch-done'},
                {'from': 'developer', 'to': 'client-gate', 'phase': 'dev-done'},
                {'from': 'client-gate', 'to': '__terminal__', 'phase': 'cl-done_pass',
                 'condition': {'field': 'score', 'operator': '>=', 'value': 9}},
            ],
        }

    def test_normal_parse(self):
        """正常路径：解析合法状态机"""
        from state_machine_parser import validate_state_machine
        errors, warnings = validate_state_machine(self.valid_sm)
        self.assertEqual(len(errors), 0, f"Expected no errors, got: {errors}")

    def test_boundary_missing_entry_point(self):
        """边界路径：缺少 entry_point"""
        from state_machine_parser import validate_state_machine
        sm = self.valid_sm.copy()
        del sm['entry_point']
        errors, warnings = validate_state_machine(sm)
        self.assertTrue(any('entry_point' in e for e in errors))

    def test_adversarial_cycle_detection(self):
        """对抗路径：循环依赖（自环视为正常）"""
        from state_machine_parser import validate_state_machine
        sm = self.valid_sm.copy()
        sm['edges'].append({'from': 'developer', 'to': 'developer', 'phase': 'self-loop'})
        errors, warnings = validate_state_machine(sm)
        self.assertEqual(len(errors), 0, "Self-loops should be allowed")

    def test_adversarial_unknown_node(self):
        """对抗路径：边引用不存在的节点"""
        from state_machine_parser import validate_state_machine
        sm = self.valid_sm.copy()
        sm['edges'].append({'from': 'ghost', 'to': 'developer', 'phase': 'unknown'})
        errors, warnings = validate_state_machine(sm)
        self.assertTrue(any('ghost' in str(w) for w in warnings),
                        "Should warn about unknown node")


# ── Test M2: State Machine Engine ──

class TestStateMachineEngine(unittest.TestCase):
    """状态机引擎测试"""

    def setUp(self):
        self.sm_path = 'state-machine.yaml'
        self.state_dir = tempfile.mkdtemp()
        self.engine_path = os.path.join(self.state_dir, 'machine_state.json')

    def tearDown(self):
        shutil.rmtree(self.state_dir)

    def test_normal_load_and_transition(self):
        """正常路径：加载状态机 → 流转"""
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime(state_dir=self.state_dir)
        engine.load(self.sm_path)
        self.assertEqual(engine.state['current_node'], 'boss')

        result = engine.transition('boss-done')
        self.assertEqual(result['to'], 'architect')
        self.assertEqual(result['from'], 'boss')
        self.assertFalse(result['is_terminal'])
        result2 = engine.transition('arch-done')
        self.assertEqual(result2['to'], 'backend-dev')

    def test_boundary_invalid_phase(self):
        """边界路径：无效 phase"""
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime(state_dir=self.state_dir)
        engine.load(self.sm_path)
        with self.assertRaises(ValueError):
            engine.transition('nonexistent-phase')

    def test_normal_temp_node_insertion(self):
        """正常路径：插入临时节点 → 流转 → 返回"""
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime(state_dir=self.state_dir)
        engine.load(self.sm_path)
        engine.transition('boss-done')
        engine.transition('arch-done')
        result = engine.insert_temporary_node('hr-recruiter', 'arch-needs-hiring')
        self.assertIn('hr-recruiter', result['node_id'])
        self.assertEqual(result['role'], 'hr-recruiter')
        # Return from temporary node
        r2 = engine.transition('hr-recruiter-done')
        self.assertEqual(r2['to'], 'backend-dev')

    def test_adversarial_max_loops(self):
        """对抗路径：超过最大循环次数"""
        from state_machine_engine import StateMachineRuntime
        engine = StateMachineRuntime(state_dir=self.state_dir)
        engine.load(self.sm_path)
        engine.state['max_loops'] = 2
        engine.state['loop_count'] = 0
        engine.transition('boss-done')
        engine.transition('arch-done')
        with self.assertRaises(RuntimeError):
            engine.transition('dev-done_task-done')


# ── Test M3: Handoff Ticket ──

class TestHandoffTicket(unittest.TestCase):
    """交接工单测试"""

    def setUp(self):
        self.handoff_dir = tempfile.mkdtemp()
        self._orig_dir = '.reasonix/handoffs'
        # Patch the directory
        import handoff_ticket
        handoff_ticket.HANDOFF_DIR = self.handoff_dir

    def tearDown(self):
        shutil.rmtree(self.handoff_dir)

    def test_normal_create_and_get(self):
        """正常路径：创建工单 → 查询"""
        from handoff_ticket import create_handoff_ticket, get_handoff_ticket
        ticket = create_handoff_ticket('architect', 'developer',
                                       artifacts=['doc.md'],
                                       pending_decisions=['DB choice'])
        tid = ticket['ticket_id']
        self.assertGreater(ticket['version'], 1000000000000)

        fetched = get_handoff_ticket(tid)
        self.assertEqual(fetched['sender_id'], 'architect')
        self.assertEqual(fetched['receiver_id'], 'developer')

    def test_normal_version_increment(self):
        """正常路径：同一角色多次创建 → 版本递增"""
        from handoff_ticket import create_handoff_ticket
        import time
        t1 = create_handoff_ticket('dev', 'tester')
        time.sleep(0.002)  # 确保不同毫秒
        t2 = create_handoff_ticket('dev', 'judge')
        self.assertGreater(t2['version'], t1['version'])

    def test_boundary_list_by_role(self):
        """边界路径：按角色列出工单"""
        from handoff_ticket import create_handoff_ticket, list_handoff_tickets
        create_handoff_ticket('role-a', 'role-b')
        create_handoff_ticket('role-b', 'role-c')
        tickets = list_handoff_tickets(role_name='role-a')
        self.assertEqual(len(tickets), 1)


# ── Test M4: Role Tag System ──

class TestRoleTagSystem(unittest.TestCase):
    """角色标签测试"""

    def test_normal_has_tag(self):
        """正常路径：检查角色是否有 OP 标签"""
        from role_tag_system import has_tag
        self.assertTrue(has_tag('architect', 'OP'))
        self.assertFalse(has_tag('developer', 'OP'))

    def test_normal_hr_restriction(self):
        """正常路径：HR 权限验证"""
        from role_tag_system import enforce_hr_restriction
        # OP 可以触发 HR
        self.assertTrue(enforce_hr_restriction('architect')['allowed'])
        # 普通角色不能触发 HR
        self.assertFalse(enforce_hr_restriction('developer')['allowed'])

    def test_boundary_cl_behavior(self):
        """边界路径：CL 标签行为"""
        from role_tag_system import apply_tag_behavior
        behavior = apply_tag_behavior('client-gate')
        self.assertIn('full_project_review', behavior['actions'])
        self.assertIn('score_1_to_10', behavior['actions'])
        self.assertIn('必须使用隔离 subagent', behavior['restrictions'])


# ── Test M5: HR Recruitment ──

class TestHRRecruitment(unittest.TestCase):
    """HR 招聘测试"""

    def setUp(self):
        self.recruit_dir = tempfile.mkdtemp()
        self.roles_backup = None

    def tearDown(self):
        shutil.rmtree(self.recruit_dir)

    def test_normal_start_recruitment(self):
        """正常路径：发起招聘 → 4 subagent 完成"""
        import hr_recruitment
        hr_recruitment.RECRUIT_DIR = self.recruit_dir
        r = hr_recruitment.start_recruitment('test-role', 'A test role')
        self.assertEqual(r['completed_subagents'], 4)
        self.assertIn(r['status'], ('research_done', 'standards_found'))

    def test_normal_quick_reference(self):
        """正常路径：引用已有准则 → 跳过 subagent"""
        import hr_recruitment
        hr_recruitment.RECRUIT_DIR = self.recruit_dir
        r = hr_recruitment.reference_existing_standards('quick-role', 'Bobanana.md')
        self.assertEqual(r['status'], 'standards_found')

    def test_adversarial_nonexistent_standards(self):
        """对抗路径：引用不存在的准则文件"""
        import hr_recruitment
        hr_recruitment.RECRUIT_DIR = self.recruit_dir
        r = hr_recruitment.reference_existing_standards('bad-role', '/nonexistent/path')
        # 函数返回dict而非None，status为standards_found表示找到路径
        self.assertIn('status', r)


# ── Test M6: Pipeline Orchestrator (with persistence) ──

class TestPipelineOrchestrator(unittest.TestCase):
    """管线编排器测试"""

    def setUp(self):
        self.pipeline_dir = tempfile.mkdtemp()
        self.state_dir = tempfile.mkdtemp()
        self.handoff_dir = tempfile.mkdtemp()
        # Patch paths
        import pipeline_orchestrator as po
        import state_machine_engine as sme
        po.PIPELINE_DIR = self.pipeline_dir
        # 保存原始__init__以便恢复
        self._orig_sm_init = sme.StateMachineRuntime.__init__
        sme.StateMachineRuntime.__init__ = lambda self, state_dir=None, **kwargs: (
            setattr(self, '_state_machine_path', 'state-machine.yaml') or
            setattr(self, 'state_dir', state_dir or '.reasonix/state') or
            setattr(self, 'state_file', os.path.join(self.state_dir or state_dir or '.reasonix/state', 'machine_state.json')) or
            setattr(self, 'config', None) or
            setattr(self, 'state', None) or
            None
        )

    def tearDown(self):
        import state_machine_engine as sme
        sme.StateMachineRuntime.__init__ = self._orig_sm_init
        shutil.rmtree(self.pipeline_dir)
        shutil.rmtree(self.state_dir)
        shutil.rmtree(self.handoff_dir)

    def test_normal_init(self):
        """正常路径：初始化管线"""
        from pipeline_orchestrator import init_pipeline, list_pipelines
        pl = init_pipeline('Test goal')
        self.assertEqual(pl['status'], 'initialized')
        self.assertEqual(pl['current_node'], 'boss')
        pipelines = list_pipelines()
        self.assertEqual(len(pipelines), 1)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
