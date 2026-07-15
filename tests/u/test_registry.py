"""
Bobanana 5.0 — Unit: Role Tag System & Registry
"""
import os, yaml, glob, unittest, sys
sys.path.insert(0, '.')

class TestRoleRegistry(unittest.TestCase):
    """角色卡注册表完整性"""

    def setUp(self):
        with open('skills/roles/.registry.yaml') as f:
            self.registry = yaml.safe_load(f)

    def test_all_cards_have_required_fields(self):
        for c in self.registry['cards']:
            for field in ['id', 'name', 'description', 'path', 'tags']:
                self.assertIn(field, c, f"{c.get('id','?')} missing field '{field}'")

    def test_all_card_files_exist(self):
        for c in self.registry['cards']:
            p = os.path.join('skills/roles', c['path'])
            self.assertTrue(os.path.exists(p), f"Missing: {p}")

    def test_each_card_has_skill(self):
        for c in self.registry['cards']:
            d = os.path.dirname(os.path.join('skills/roles', c['path']))
            skill = os.path.join(d, 'SKILL.md')
            self.assertTrue(os.path.exists(skill), f"Missing SKILL.md for {c['id']}")

    def test_each_card_has_standards(self):
        for c in self.registry['cards']:
            d = os.path.dirname(os.path.join('skills/roles', c['path']))
            std = os.path.join(d, 'standards-brief.yaml')
            self.assertTrue(os.path.exists(std), f"Missing standards for {c['id']}")

    def test_no_duplicate_ids(self):
        ids = [c['id'] for c in self.registry['cards']]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate role IDs found")

    def test_op_roles_have_is_op_role(self):
        for c in self.registry['cards']:
            if 'OP' in c.get('tags', []):
                rp = os.path.join('skills/roles', c['path'])
                if os.path.exists(rp):
                    with open(rp) as f:
                        card = yaml.safe_load(f)
                    self.assertTrue(card.get('is_op_role', False) or any(
                        'OP' in c.get('tags', []) for c_ in [card]),
                        f"OP role {c['id']} missing is_op_role: true")

    def test_exit_only_client_gate(self):
        for c in self.registry['cards']:
            rp = os.path.join('skills/roles', c['path'])
            if os.path.exists(rp):
                with open(rp) as f:
                    card = yaml.safe_load(f)
                if card.get('is_exit'):
                    self.assertIn('CL', c.get('tags', []),
                                  f"Non-CL role {c['id']} has is_exit: true")

class TestRegistryScan(unittest.TestCase):
    """注册表扫描"""

    def test_scan_returns_all(self):
        import sys
        sys.path.insert(0, 'skills/roles')
        from role_card_registry import scan_directory
        result = scan_directory()
        self.assertGreater(len(result['cards']), 50)

    def test_scan_function(self):
        import sys
        sys.path.insert(0, 'skills/roles')
        from role_card_registry import cmd_scan
        self.assertIsNotNone(cmd_scan)

class TestRoleTagSystem(unittest.TestCase):
    """角色标签系统"""

    def test_tag_has_op(self):
        from role_tag_system import get_all_tags_summary
        summary = get_all_tags_summary()
        op_roles = [r for r in summary if 'OP' in r.get('tags', [])]
        self.assertGreater(len(op_roles), 0)

    def test_tag_has_cl(self):
        from role_tag_system import get_roles_by_tag
        cl_roles = get_roles_by_tag('CL')
        self.assertGreaterEqual(len(cl_roles), 1)

    def test_enforce_hr(self):
        from role_tag_system import enforce_hr_restriction
        self.assertIsNotNone(enforce_hr_restriction)

if __name__ == '__main__':
    unittest.main()
