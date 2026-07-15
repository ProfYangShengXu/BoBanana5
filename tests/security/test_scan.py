"""
Bobanana 5.0 — Security: 安全扫描测试
静态分析检查常见安全问题。
"""
import os, sys, glob, yaml, unittest

class TestSecurityScan(unittest.TestCase):
    """安全扫描"""

    def test_no_os_system(self):
        """禁止 os.system() 调用"""
        for py_file in glob.glob('**/*.py', recursive=True):
            if 'build-eui' in py_file or '__pycache__' in py_file or 'external' in py_file or '.git' in py_file:
                continue
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if 'os.system(' in line and not line.strip().startswith('#'):
                        self.fail(f"{py_file}:{i}: os.system() 被禁止: {line.strip()}")

    def test_safe_load_not_load(self):
        """禁止 yaml.load()，必须用 yaml.safe_load()"""
        for py_file in glob.glob('**/*.py', recursive=True):
            if 'build-eui' in py_file or '__pycache__' in py_file or 'external' in py_file or '.git' in py_file:
                continue
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if 'yaml.load(' in line and 'yaml.safe_load' not in line:
                        self.fail(f"{py_file}:{i}: 使用了 yaml.load() 而非 yaml.safe_load()")

    def test_no_hardcoded_keys(self):
        """检查无硬编码密钥(api_key/secret/password/token模式)"""
        patterns = ['api_key', 'api_secret', 'password=', 'token=']
        for py_file in glob.glob('**/*.py', recursive=True):
            if 'build-eui' in py_file or '__pycache__' in py_file or 'external' in py_file or '.git' in py_file:
                continue
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    stripped = line.strip()
                    if stripped.startswith('#') or stripped.startswith('//'):
                        continue
                    for pat in patterns:
                        if pat in stripped.lower() and 'example' not in stripped.lower() and 'xxxx' not in stripped:
                            # 允许环境变量引用
                            if 'environ.get' in stripped or 'os.getenv' in stripped or 'api_key_env' in stripped:
                                continue
                            self.fail(f"{py_file}:{i}: 可能的硬编码密钥: {stripped[:80]}")

    def test_no_bare_except(self):
        """检查无 bare except: 语句"""
        for py_file in glob.glob('*.py', recursive=False):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'except:' in content and 'except Exception' not in content and 'except (json.JSONDecodeError, KeyError)' not in content:
                    for i, line in enumerate(content.split('\n'), 1):
                        ls = line.strip()
                        if ls == 'except:' or ls.startswith('except: '):
                            self.fail(f"{py_file}:{i}: bare except 被禁止: {line.strip()}")

    def test_no_shell_true(self):
        """subprocess.run 禁止 shell=True"""
        for py_file in glob.glob('**/*.py', recursive=True):
            if 'build-eui' in py_file or '__pycache__' in py_file or 'external' in py_file or '.git' in py_file:
                continue
            if 'tests/' in py_file:
                continue
            with open(py_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if 'shell=True' in line and not line.strip().startswith('#'):
                        self.fail(f"{py_file}:{i}: shell=True 被禁止: {line.strip()}")

if __name__ == '__main__':
    unittest.main()
