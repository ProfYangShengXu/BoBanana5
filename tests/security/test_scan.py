"""
Bobanana 5.0 — Security: 安全扫描测试
静态分析检查常见安全问题。
跳过 tests/ 目录避免自检误报。
"""
import os, sys, glob, unittest

SKIP_DIRS = ('build-eui', '__pycache__', 'external', '.git', 'tests/')

def _skip_path(p):
    for s in SKIP_DIRS:
        if s in p:
            return True
    return False

class TestSecurityScan(unittest.TestCase):

    def test_no_os_system(self):
        for py_file in glob.glob('**/*.py', recursive=True):
            if _skip_path(py_file): continue
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if s.startswith('#') or s.startswith('"""') or s.startswith("'''"): continue
                    if 'os.system(' in s:
                        self.fail(f"{py_file}:{i}: os.system(): {s[:60]}")

    def test_safe_load_not_load(self):
        for py_file in glob.glob('**/*.py', recursive=True):
            if _skip_path(py_file): continue
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                c = f.read()
            if 'yaml.load(' in c and 'yaml.safe_load' not in c:
                # 找到非 safe_load 的行
                for i, line in enumerate(c.split('\n'), 1):
                    if 'yaml.load(' in line and 'yaml.safe_load' not in line:
                        self.fail(f"{py_file}:{i}: yaml.load() 禁止: {line.strip()[:60]}")

    def test_no_hardcoded_keys(self):
        patterns = ['api_key', 'api_secret', 'password=', 'token=']
        for py_file in glob.glob('**/*.py', recursive=True):
            if _skip_path(py_file): continue
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if s.startswith('#') or s.startswith('"""') or s.startswith("'''"): continue
                    for pat in patterns:
                        if pat in s.lower():
                            if 'environ.get' in s or 'os.getenv' in s or 'api_key_env' in s or 'example' in s:
                                continue
                            self.fail(f"{py_file}:{i}: 可能硬编码密钥: {s[:80]}")

    def test_no_bare_except(self):
        for py_file in glob.glob('*.py', recursive=True):
            if _skip_path(py_file) or 'test_' in py_file: continue
            with open(py_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if s == 'except:' and not any(x in s for x in ('Exception', 'JSONDecodeError')):
                        self.fail(f"{py_file}:{i}: bare except: {s[:60]}")

    def test_no_shell_true(self):
        for py_file in glob.glob('*.py', recursive=False):
            with open(py_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    s = line.strip()
                    if s.startswith('#'): continue
                    if 'shell=True' in s:
                        self.fail(f"{py_file}:{i}: shell=True 禁止: {s[:60]}")

if __name__ == '__main__':
    unittest.main()
