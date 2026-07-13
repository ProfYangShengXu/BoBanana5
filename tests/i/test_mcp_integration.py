"""
Bobanana 5.0 — MCP Client+Server Integration Tests (I层)
测试 mcp_client 与 mcp_server 的 direct 模式完整交互。
normal/boundary/adversarial 三路径。
"""
import os
import sys
import json
import unittest


class TestMCPDirectIntegration(unittest.TestCase):
    """MCP Client + Server direct 模式集成测试"""

    @classmethod
    def setUpClass(cls):
        """全局初始化 MCP 客户端（direct 模式）"""
        from mcp_client import MCPClient
        cls.client = MCPClient(direct_mode=True)
        cls.client.connect()

    def test_normal_get_role_cards(self):
        """正常路径：获取角色卡列表（至少包含 boss 和 architect）"""
        result = self.client.get_role_cards()
        # direct 模式返回原始 handler 结果
        inner = result.get('result', result)
        cards = inner.get('cards', inner.get('cards', []))
        total = inner.get('total', len(cards))
        names = [c.get('name', '') for c in cards]
        self.assertIn('boss', names)
        self.assertIn('architect', names)
        self.assertGreaterEqual(total, 2)

    def test_normal_get_role_card_detail_boss(self):
        """正常路径：获取 boss 角色卡详情"""
        result = self.client.get_role_card_detail('boss')
        inner = result.get('result', result)
        self.assertIn('name', inner.get('card', inner))
        card_name = inner.get('card', inner).get('name', '')
        self.assertEqual(card_name, 'boss')

    def test_normal_get_state_machine(self):
        """正常路径：获取状态机"""
        result = self.client.get_state_machine()
        inner = result.get('result', result)
        sm = inner.get('state_machine', {})
        self.assertIn('nodes', sm)
        self.assertIn('edges', sm)

    def test_normal_signal_done(self):
        """正常路径：signal_done 调用"""
        result = self.client.signal_done(summary='Integration test complete')
        inner = result.get('result', result)
        # 返回成功状态
        self.assertIn('success', inner)

    def test_normal_read_file(self):
        """正常路径：读取已有文件"""
        result = self.client.read_file('mcp_client.py')
        inner = result.get('result', result)
        if 'content' in inner:
            self.assertGreater(len(inner['content']), 0)
        elif 'error' not in inner:
            self.fail(f"Unexpected response: {inner}")

    def test_normal_get_handoff_tickets(self):
        """正常路径：获取交接工单"""
        result = self.client.get_handoff_tickets()
        inner = result.get('result', result)
        # handoffs 目录可能为空，但不应该报错
        self.assertIn('total', inner)

    def test_boundary_get_role_cards_by_op_tag(self):
        """边界路径：按 OP tag 过滤角色卡"""
        result = self.client.get_role_cards(tag='OP')
        inner = result.get('result', result)
        cards = inner.get('cards', inner.get('cards', []))
        if cards:
            for c in cards:
                self.assertIn('OP', c.get('tags', []))

    def test_boundary_get_role_cards_by_cl_tag(self):
        """边界路径：按 CL tag 过滤角色卡"""
        result = self.client.get_role_cards(tag='CL')
        inner = result.get('result', result)
        cards = inner.get('cards', inner.get('cards', []))
        if cards:
            for c in cards:
                self.assertIn('CL', c.get('tags', []))

    def test_boundary_get_role_cards_by_nonexistent_tag(self):
        """边界路径：按不存在 tag 过滤"""
        result = self.client.get_role_cards(tag='_NEVER_EXISTS_')
        inner = result.get('result', result)
        total = inner.get('total', 0)
        self.assertEqual(total, 0)

    def test_adversarial_get_role_card_nonexistent(self):
        """对抗路径：获取不存在的角色卡（抛出 MCPError）"""
        from mcp_client import MCPError
        with self.assertRaises(MCPError):
            self.client.get_role_card_detail('_no_such_role_')

    def test_adversarial_read_nonexistent_file(self):
        """对抗路径：读取不存在的文件（抛出 MCPError）"""
        from mcp_client import MCPError
        with self.assertRaises(MCPError):
            self.client.read_file('/_no_such_file_')

    def test_boundary_get_pipeline_status(self):
        """边界路径：获取管线状态（可能无活跃管线）"""
        result = self.client.get_pipeline_status()
        inner = result.get('result', result)
        # 即使无活跃管线，也应返回状态描述
        self.assertIn('status', inner)

    def test_normal_queue_next_prompt(self):
        """对抗路径：queue_next_prompt 在无活跃管线时抛出 MCPError"""
        from mcp_client import MCPError
        with self.assertRaises(MCPError):
            self.client.queue_next_prompt(phase='test-done')


class TestMCPDirectErrorHandling(unittest.TestCase):
    """MCP 错误处理集成测试"""

    def test_adversarial_invalid_method(self):
        """对抗路径：调用不存在的方法"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client.connect()
        # 通过 _send_request 发送未知方法
        from mcp_client import MCPError
        with self.assertRaises(MCPError):
            client._send_request('nonexistent_method_xyz', {})

    def test_adversarial_empty_phase(self):
        """对抗路径：queue_next_prompt 空 phase（抛出 MCPError）"""
        from mcp_client import MCPClient, MCPError
        client = MCPClient(direct_mode=True)
        client.connect()
        with self.assertRaises(MCPError):
            client.queue_next_prompt(phase='')


if __name__ == '__main__':
    unittest.main()
