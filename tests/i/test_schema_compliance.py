"""
Bobanana 5.0 — Integration: YAML Schema Compliance
验证全部59张角色卡的YAML格式和Schema合规性
"""
import os, yaml, glob, unittest, sys

class TestAllRoleCardsSchema(unittest.TestCase):
    """所有角色卡 Schema 验证"""

    def test_every_role_card_yaml_valid(self):
        for card_path in glob.glob('skills/roles/*/role-card.yaml'):
            with self.subTest(card=card_path):
                try:
                    with open(card_path) as f:
                        card = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    self.fail(f"YAML error in {card_path}: {e}")
                self.assertIsNotNone(card, f"Empty card: {card_path}")

    def test_every_skill_md_has_frontmatter(self):
        for skill_path in glob.glob('skills/roles/*/SKILL.md'):
            with self.subTest(skill=skill_path):
                with open(skill_path) as f:
                    content = f.read()
                self.assertTrue(content.startswith('---'), f"Missing frontmatter: {skill_path}")

    def test_every_standards_yaml_valid(self):
        for std_path in glob.glob('skills/roles/*/standards-brief.yaml'):
            with self.subTest(standard=std_path):
                try:
                    with open(std_path) as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    self.fail(f"YAML error in {std_path}: {e}")

    def test_role_card_has_descriptive_name(self):
        for card_path in glob.glob('skills/roles/*/role-card.yaml'):
            with open(card_path) as f:
                card = yaml.safe_load(f)
            self.assertIn('name', card, f"Missing 'name' in {card_path}")
            self.assertIn('description', card, f"Missing 'description' in {card_path}")
            self.assertGreater(len(card.get('description', '')), 10)

    def test_role_card_tags_format(self):
        for card_path in glob.glob('skills/roles/*/role-card.yaml'):
            with open(card_path) as f:
                card = yaml.safe_load(f)
            self.assertIn('tags', card, f"Missing 'tags' in {card_path}")
            self.assertIsInstance(card['tags'], list)

    def test_no_card_without_registration(self):
        """所有有role-card.yaml的目录都应在registry中"""
        with open('skills/roles/.registry.yaml') as f:
            registry = yaml.safe_load(f)
        registered_paths = {c['path'] for c in registry['cards']}
        for card_path in glob.glob('skills/roles/*/role-card.yaml'):
            rel = os.path.relpath(card_path, 'skills/roles')
            # registered paths are like "backend-dev/role-card.yaml"
            norm = rel.replace('\\', '/')
            self.assertIn(norm, registered_paths, f"Card {norm} not in .registry.yaml")

if __name__ == '__main__':
    unittest.main()
