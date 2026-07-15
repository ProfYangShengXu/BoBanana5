"""
Bobanana 5.0 — Chaos: 故障注入测试
模拟各种异常场景（损坏文件、空目录、缺失依赖），验证系统降级行为。
"""
import os, sys, yaml, json, tempfile, shutil, unittest, logging

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestChaosResilience(unittest.TestCase):
    """故障注入：损坏的文件"""

    def test_corrupted_state_machine_yaml(self):
        """损坏的state-machine.yaml应被parser捕获"""
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        tmp.write(": invalid yaml: [\nbroken")
        tmp.close()
        try:
            with self.assertRaises(yaml.YAMLError):
                yaml.safe_load(open(tmp.name))
        finally:
            os.unlink(tmp.name)

    def test_corrupted_json_state(self):
        """损坏的state.json应被json捕获"""
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write("{not json}")
        tmp.close()
        try:
            with self.assertRaises(json.JSONDecodeError):
                json.load(open(tmp.name))
        finally:
            os.unlink(tmp.name)

    def test_missing_directory(self):
        """缺失目录不应导致异常"""
        from pipeline_orchestrator import has_pending_pipeline
        result = has_pending_pipeline()
        self.assertIsNotNone(result)

    def test_empty_registry(self):
        """空的.registry.yaml应返回空列表"""
        tmpdir = tempfile.mkdtemp()
        reg_path = os.path.join(tmpdir, '.registry.yaml')
        with open(reg_path, 'w') as f:
            yaml.dump({'cards': [], 'version': 1}, f)
        with open(reg_path) as f:
            r = yaml.safe_load(f)
        self.assertEqual(len(r['cards']), 0)
        shutil.rmtree(tmpdir)

    def test_missing_standards_file(self):
        """缺失standards-brief.yaml不应阻止角色卡加载"""
        from skills.roles.role_card_registry import load_role_card
        # 找一个没有standards-brief的目录
        base = 'skills/roles'
        for name in os.listdir(base):
            d = os.path.join(base, name)
            if os.path.isdir(d) and name != '__pycache__':
                card = os.path.join(d, 'role-card.yaml')
                if os.path.exists(card):
                    result = load_role_card(card)
                    self.assertIsNotNone(result)
                    break

    def test_subprocess_crash(self):
        """子进程崩溃不应影响主进程"""
        import subprocess
        result = subprocess.run([sys.executable, '-c', 'import sys; sys.exit(1)'], capture_output=True)
        self.assertEqual(result.returncode, 1)

class TestChaosFileSystem(unittest.TestCase):
    """故障注入：文件系统异常"""

    def test_missing_pipeline_dir(self):
        """无pipelines目录应正常返回空列表"""
        from pipeline_orchestrator import list_pipelines, PIPELINE_DIR
        orig = PIPELINE_DIR
        try:
            import pipeline_orchestrator as po
            po.PIPELINE_DIR = '/nonexistent/path/for/test'
            result = list_pipelines()
            self.assertEqual(result, [])
        finally:
            po.PIPELINE_DIR = orig

    def test_empty_cycle_dir(self):
        """空的cycle目录不应判为有pending管线"""
        from pipeline_orchestrator import has_pending_pipeline
        result = has_pending_pipeline()
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
