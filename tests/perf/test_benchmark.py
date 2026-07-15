"""
Bobanana 5.0 — Performance: 性能基准测试
测量关键操作的耗时，建立基准线。
"""
import os, sys, time, yaml, json, tempfile, shutil, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, 'skills/roles')

class TestPerfBenchmark(unittest.TestCase):
    """性能基准"""

    def test_parse_state_machine(self):
        """解析state-machine.yaml的耗时"""
        path = 'state-machine.yaml'
        if not os.path.exists(path):
            self.skipTest("no state-machine.yaml")
        start = time.perf_counter()
        for _ in range(100):
            with open(path) as f:
                yaml.safe_load(f)
        elapsed = time.perf_counter() - start
        avg = elapsed / 100
        self.assertLess(avg, 0.05, f"SM解析耗时 {avg*1000:.1f}ms/次，超过50ms阈值")

    def test_create_100_handoffs(self):
        """批量创建100个handoff工单的耗时"""
        import handoff_ticket as ht
        tmpdir = tempfile.mkdtemp()
        orig = ht.HANDOFF_DIR
        ht.HANDOFF_DIR = tmpdir
        try:
            start = time.perf_counter()
            for i in range(100):
                ht.create_handoff_ticket(f"sender{i}", "receiver", artifacts=[str(i)])
            elapsed = time.perf_counter() - start
            self.assertLess(elapsed, 5.0, f"100次handoff耗时{elapsed:.1f}s，超过5s阈值")
        finally:
            ht.HANDOFF_DIR = orig
            shutil.rmtree(tmpdir)

    def test_scan_registry(self):
        """扫描角色卡注册表的耗时"""
        path = 'skills/roles/.registry.yaml'
        if not os.path.exists(path):
            self.skipTest("no registry")
        start = time.perf_counter()
        for _ in range(50):
            with open(path) as f:
                yaml.safe_load(f)
        elapsed = time.perf_counter() - start
        avg = elapsed / 50
        self.assertLess(avg, 0.02, f"Registry解析耗时{avg*1000:.1f}ms/次")

    def test_json_dumps_cycles(self):
        """序列化cycle state的耗时"""
        state = {"goal": "test", "phase": "done", "loop_count": 999}
        start = time.perf_counter()
        for _ in range(1000):
            json.dumps(state)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0, f"1000次序列化耗时{elapsed:.1f}s")

if __name__ == '__main__':
    unittest.main()
