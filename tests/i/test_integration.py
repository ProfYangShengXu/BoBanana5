"""
Bobanana 5.0 — Integration Tests (I层)
测试模块间交互，normal/boundary/adversarial 三路径。
"""
import os
import sys
import json
import yaml
import tempfile
import shutil
import unittest


sys.path.insert(0, '.')


class TestI_RegistryAndValidator(unittest.TestCase):
    """集成测试: M1 注册表 + 验证器交互"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_roles = 'skills/roles'

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _make_card(self, name='test-role', tags=None):
        return {
            'name': name,
            'description': 'Integration test role',
            'tags': tags or [],
            'input_contract': [{'name': 'in', 'type': 'string', 'required': True}],
            'output_contract': [{'name': 'out', 'type': 'string'}],
            'quality_gates': [{'id': 'IT-Q1', 'desc': 'Test', 'check': 'echo ok', 'layer': 'U'}],
        }

    def test_normal_validate_then_register(self):
        """正常路径: 先验证合法角色卡 → 再注册"""
        from skills.roles.validate_role_card import validate_role_card
        card = self._make_card('i-test-role')
        card_path = os.path.join(self.tmpdir, 'role-card.yaml')
        with open(card_path, 'w', encoding='utf-8') as f:
            yaml.dump(card, f)

        errors = validate_role_card(card_path, 'skills/roles/role-card.schema.yaml')
        self.assertEqual(len(errors), 0)

    def test_boundary_register_duplicate_name(self):
        """边界路径: 验证器应允许同名（注册表覆盖）"""
        from skills.roles.validate_role_card import validate_role_card
        card1 = self._make_card('dup-role')
        card2 = self._make_card('dup-role')

        p1 = os.path.join(self.tmpdir, 'c1.yaml')
        p2 = os.path.join(self.tmpdir, 'c2.yaml')
        with open(p1, 'w', encoding='utf-8') as f: yaml.dump(card1, f)
        with open(p2, 'w', encoding='utf-8') as f: yaml.dump(card2, f)

        e1 = validate_role_card(p1, 'skills/roles/role-card.schema.yaml')
        e2 = validate_role_card(p2, 'skills/roles/role-card.schema.yaml')
        self.assertEqual(len(e1), 0)
        self.assertEqual(len(e2), 0)

    def test_adversarial_register_invalid_then_valid(self):
        """对抗路径: 先非法 → 修复 → 合法"""
        from skills.roles.validate_role_card import validate_role_card
        bad = self._make_card('fix-role')
        del bad['description']
        path = os.path.join(self.tmpdir, 'bad.yaml')
        with open(path, 'w', encoding='utf-8') as f: yaml.dump(bad, f)
        errors = validate_role_card(path, 'skills/roles/role-card.schema.yaml')
        self.assertTrue(len(errors) > 0)

        # 修复后
        bad['description'] = 'Fixed role'
        with open(path, 'w', encoding='utf-8') as f: yaml.dump(bad, f)
        errors = validate_role_card(path, 'skills/roles/role-card.schema.yaml')
        self.assertEqual(len(errors), 0)


class TestI_EngineAndHandoff(unittest.TestCase):
    """集成测试: M2 状态机引擎 + M3 交接工单交互"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_dir = os.path.join(self.tmpdir, 'state')
        self.handoff_dir = os.path.join(self.tmpdir, 'handoffs')
        os.makedirs(self.state_dir)
        os.makedirs(self.handoff_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_normal_transition_creates_ticket(self):
        """正常路径: 状态机流转后创建交接工单"""
        from state_machine_engine import StateMachineRuntime
        import handoff_ticket
        handoff_ticket.HANDOFF_DIR = self.handoff_dir

        engine = StateMachineRuntime(state_dir=self.state_dir)
        engine.load('state-machine.yaml')
        engine.transition('arch-done')

        ticket = handoff_ticket.create_handoff_ticket(
            'architect', 'developer',
            artifacts=['state-machine.yaml'],
            pending_decisions=['Task list']
        )
        self.assertEqual(ticket['sender_id'], 'architect')
        self.assertEqual(ticket['version'], 1)

        # Verify ticket file exists
        self.assertTrue(os.path.exists(
            os.path.join(self.handoff_dir, f"{ticket['ticket_id']}.json")))

    def test_boundary_ticket_after_temp_node(self):
        """边界路径: 临时节点后创建工单"""
        from state_machine_engine import StateMachineRuntime
        import handoff_ticket
        handoff_ticket.HANDOFF_DIR = self.handoff_dir

        engine = StateMachineRuntime(state_dir=self.state_dir)
        engine.load('state-machine.yaml')
        engine.transition('arch-done')
        engine.insert_temporary_node('hr-recruiter', 'arch-needs-hiring')

        ticket = handoff_ticket.create_handoff_ticket(
            'hr-recruiter', 'developer',
            artifacts=['new-role-card.yaml']
        )
        self.assertTrue(ticket['ticket_id'].startswith('ht-hr-'))

    def test_adversarial_ticket_without_transition(self):
        """对抗路径: 无状态机流转时创建工单"""
        import handoff_ticket
        handoff_ticket.HANDOFF_DIR = self.handoff_dir
        ticket = handoff_ticket.create_handoff_ticket(
            'system', 'architect',
            artifacts=['init']
        )
        self.assertIsNotNone(ticket['ticket_id'],
                             "Should still create ticket without engine transition")


class TestI_TagsAndOrchestrator(unittest.TestCase):
    """集成测试: M4 标签 + M6 编排器交互"""

    def setUp(self):
        self.pipeline_dir = tempfile.mkdtemp()
        self.state_dir = tempfile.mkdtemp()
        self.handoff_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.pipeline_dir)
        shutil.rmtree(self.state_dir)
        shutil.rmtree(self.handoff_dir)

    def test_normal_op_can_write_state_machine(self):
        """正常路径: OP 标签角色可读写状态机"""
        from role_tag_system import has_tag, apply_tag_behavior
        self.assertTrue(has_tag('architect', 'OP'))
        behavior = apply_tag_behavior('architect')
        self.assertIn('write_state_machine', behavior['actions'])

    def test_boundary_hr_only_op_can_trigger(self):
        """边界路径: HR 只能由 OP 触发"""
        from role_tag_system import enforce_hr_restriction
        self.assertTrue(enforce_hr_restriction('architect')['allowed'])
        self.assertFalse(enforce_hr_restriction('developer')['allowed'])

    def test_adversarial_unknown_role_tag(self):
        """对抗路径: 不存在的角色检查标签"""
        from role_tag_system import has_tag
        self.assertFalse(has_tag('nonexistent-role', 'OP'))


class TestI_HRAndRegistry(unittest.TestCase):
    """集成测试: M5 HR + M1 注册表交互"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.recruit_dir = os.path.join(self.tmpdir, 'recruitments')
        os.makedirs(self.recruit_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_normal_hr_generates_registrable_card(self):
        """正常路径: HR 生成角色卡 → 可被注册表扫描发现"""
        import hr_recruitment
        hr_recruitment.RECRUIT_DIR = self.recruit_dir

        r = hr_recruitment.start_recruitment('integ-test', 'Integration test role')
        self.assertEqual(r['completed_subagents'], 4)

        result = hr_recruitment.generate_role_card(r['recruitment_id'])
        card_path = result['card_path']
        self.assertTrue(os.path.exists(card_path))

        # 验证符合 Schema
        from skills.roles.validate_role_card import validate_role_card
        errors = validate_role_card(card_path, 'skills/roles/role-card.schema.yaml')
        self.assertEqual(len(errors), 0)

    def test_boundary_hr_quick_skip_research(self):
        """边界路径: HR 快速创建跳过研究"""
        import hr_recruitment
        hr_recruitment.RECRUIT_DIR = self.recruit_dir
        r = hr_recruitment.reference_existing_standards('quick-integ', 'Bobanana.md')
        self.assertEqual(r['status'], 'standards_found')
        self.assertEqual(r.get('skipped_subagents'), 4)

    def test_adversarial_hr_nonexistent_standards(self):
        """对抗路径: 引用不存在的准则文件"""
        import hr_recruitment
        hr_recruitment.RECRUIT_DIR = self.recruit_dir
        r = hr_recruitment.reference_existing_standards('bad', '/tmp/nonexistent.md')
        self.assertIsNone(r)


class TestI_CLFailbackFlow(unittest.TestCase):
    """集成测试: CL 打回全流程"""

    def setUp(self):
        for d in ['.reasonix/pipelines', '.reasonix/state', '.reasonix/handoffs']:
            if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)

    def tearDown(self):
        for d in ['.reasonix/pipelines', '.reasonix/state', '.reasonix/handoffs']:
            if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)

    def test_normal_cl_pass(self):
        """正常路径: CL score=10 → terminal"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline
        init_pipeline('CL pass test')
        for p in ['arch-done', 'dev-done_task-done', 'test-done_layer-not-done',
                  'test-done_layer-not-done', 'test-done_layer-not-done',
                  'test-done_layer-all-done', 'judge-done_no-badcase', 'critic-done_pass']:
            advance_pipeline(p)
        advance_pipeline('cl-done_pass', score=10)
        pl = get_pipeline()
        self.assertEqual(pl['status'], 'completed')
        self.assertEqual(pl['cl_score'], 10)

    def test_boundary_cl_failback(self):
        """边界路径: CL score=5 → failback to architect"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline
        init_pipeline('CL failback test')
        for p in ['arch-done', 'dev-done_task-done', 'test-done_layer-not-done',
                  'test-done_layer-not-done', 'test-done_layer-not-done',
                  'test-done_layer-all-done', 'judge-done_no-badcase', 'critic-done_pass']:
            advance_pipeline(p)
        advance_pipeline('cl-done_pass', score=5)
        pl = get_pipeline()
        self.assertEqual(pl['status'], 'failback_to_architect')
        self.assertEqual(pl['current_node'], 'architect')
        self.assertEqual(pl['cl_score'], 5)

    def test_adversarial_cl_edge_9(self):
        """对抗路径: CL score=9 → pass (边界值)"""
        from pipeline_orchestrator import init_pipeline, advance_pipeline, get_pipeline
        init_pipeline('CL edge test')
        for p in ['arch-done', 'dev-done_task-done', 'test-done_layer-not-done',
                  'test-done_layer-not-done', 'test-done_layer-not-done',
                  'test-done_layer-all-done', 'judge-done_no-badcase', 'critic-done_pass']:
            advance_pipeline(p)
        advance_pipeline('cl-done_pass', score=9)
        pl = get_pipeline()
        self.assertEqual(pl['status'], 'completed',
                         "Score=9 should pass (>=9)")
        self.assertEqual(pl['cl_score'], 9)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
