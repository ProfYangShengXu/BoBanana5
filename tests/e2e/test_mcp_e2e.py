"""
Bobanana 5.0 — E2E: MCP Server 协议测试
启动 mcp_server.py 子进程 → 发 JSON-RPC 请求 → 验响应 → 关进程
"""
import os, sys, json, subprocess, time, signal, tempfile, unittest

class TestMCPE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.Popen(
            [sys.executable, '-m', 'mcp_server'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=os.path.dirname(os.path.abspath(__file__)) + '/..'
        )
        time.sleep(1)
        # 检查进程是否活着
        if cls.proc.poll() is not None:
            raise RuntimeError(f"MCP server failed to start (exit={cls.proc.poll()})")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)

    def _send_request(self, method, params=None):
        req = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1})
        self.proc.stdin.write(req + '\n')
        self.proc.stdin.flush()
        resp = self.proc.stdout.readline()
        return json.loads(resp)

    def test_ping(self):
        result = self._send_request("ping")
        self.assertIn("result", result)

    def test_get_state_machine(self):
        result = self._send_request("get_state_machine")
        if "result" in result:
            self.assertIn("state_machine", result["result"])

    def test_bad_json(self):
        self.proc.stdin.write('not json\n')
        self.proc.stdin.flush()
        resp = self.proc.stdout.readline()
        # 应该返回错误响应
        self.assertIn("error", json.loads(resp))

if __name__ == '__main__':
    unittest.main()
