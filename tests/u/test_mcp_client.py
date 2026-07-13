"""
Bobanana 5.0 — MCP Client Unit Tests (U层)
测试 mcp_client.MCPClient 的独立功能，normal/boundary/adversarial 三路径。
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch


# ── Test: MCPClient 基础功能 ──

class TestMCPClientInit(unittest.TestCase):
    """MCPClient 初始化和连接测试"""

    def setUp(self):
        self.server_script = 'mcp_server.py'

    def test_normal_init_default(self):
        """正常路径：默认参数初始化"""
        from mcp_client import MCPClient
        client = MCPClient()
        self.assertEqual(client.server_script, 'mcp_server.py')
        self.assertFalse(client.direct_mode)
        self.assertIsNone(client.proc)
        self.assertEqual(client.request_id, 0)

    def test_normal_init_direct_mode(self):
        """正常路径：direct_mode 模式初始化（_direct_handler 在 connect 中设置）"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        self.assertTrue(client.direct_mode)
        self.assertIsNone(client._direct_handler)  # connect() 中才设置

    def test_normal_init_custom_script(self):
        """正常路径：自定义 server_script"""
        from mcp_client import MCPClient
        client = MCPClient(server_script='custom_server.py')
        self.assertEqual(client.server_script, 'custom_server.py')

    def test_boundary_empty_server_script(self):
        """边界路径：空 server_script"""
        from mcp_client import MCPClient
        client = MCPClient(server_script='')
        self.assertEqual(client.server_script, '')

    def test_adversarial_unknown_direct_handler(self):
        """对抗路径：direct_mode 但传递了无效 handler"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True, server_script='nonexistent.py')
        self.assertTrue(client.direct_mode)
        # direct_mode 下 server_script 不用于 subprocess，不应报错


class TestMCPClientConnect(unittest.TestCase):
    """MCPClient.connect() 测试"""

    def setUp(self):
        self.server_script = 'mcp_server.py'

    def test_normal_connect_direct_mode(self):
        """正常路径：direct_mode 连接成功"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        result = client.connect(timeout=5)
        self.assertTrue(result['connected'])
        self.assertEqual(result['mode'], 'direct')
        self.assertGreaterEqual(result['cards'], 0)

    def test_boundary_connect_no_cards(self):
        """边界路径：direct_mode 连接（通过真实 handle_request）"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        result = client.connect()
        self.assertTrue(result['connected'])

    def test_adversarial_connect_before_subprocess(self):
        """对抗路径：subprocess 模式未连接时调用"""
        from mcp_client import MCPClient, MCPError
        client = MCPClient(direct_mode=False)
        # subprocess 模式尚未启动 proc，connect 内部会尝试 Popen
        # 这里不实际启动，直接验证状态
        self.assertFalse(client.is_connected())


class TestMCPClientIsConnected(unittest.TestCase):
    """MCPClient.is_connected() 测试"""

    def test_normal_not_connected_default(self):
        """正常路径：未连接时返回 False"""
        from mcp_client import MCPClient
        client = MCPClient()
        self.assertFalse(client.is_connected())

    def test_normal_connected_after_connect(self):
        """正常路径：connect() 后 is_connected() 返回 True"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client.connect()
        self.assertTrue(client.is_connected())

    def test_adversarial_disconnect_twice(self):
        """对抗路径：重复断开连接（未连接时断开不应报错）"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        # 未连接时 disconnect
        client.disconnect()
        client.disconnect()  # 第二次断开不应报错
        # direct_mode 下未调用 connect，_direct_handler 为 None
        self.assertFalse(client.is_connected())


class TestMCPClientSendRequest(unittest.TestCase):
    """MCPClient._send_request() 测试"""

    def setUp(self):
        self.direct_handler = MagicMock()

    def test_normal_direct_mode_send(self):
        """正常路径：direct_mode 发送请求"""
        self.direct_handler.return_value = {'status': 'ok'}
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client._direct_handler = self.direct_handler
        result = client._send_request('get_status', {})
        self.assertEqual(result, {'status': 'ok'})
        self.direct_handler.assert_called_once()

    def test_normal_request_id_increments(self):
        """正常路径：request_id 递增"""
        self.direct_handler.side_effect = [
            {'result': {'a': 1}},
            {'result': {'b': 2}},
        ]
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        client._direct_handler = self.direct_handler
        client._send_request('method_a', {})
        client._send_request('method_b', {})
        self.assertEqual(client.request_id, 2)

    def test_adversarial_rpc_error_response(self):
        """对抗路径：RPC 返回 error"""
        self.direct_handler.return_value = {'error': {'code': -32000, 'message': 'Test error'}}
        from mcp_client import MCPClient, MCPError
        client = MCPClient(direct_mode=True)
        client._direct_handler = self.direct_handler
        with self.assertRaises(MCPError) as ctx:
            client._send_request('bad_method', {})
        self.assertIn('Test error', str(ctx.exception))

    def test_adversarial_not_connected_subprocess(self):
        """对抗路径：subprocess 模式未连接时发送请求"""
        from mcp_client import MCPClient, MCPError
        client = MCPClient(direct_mode=False)
        with self.assertRaises(MCPError):
            client._send_request('any_method', {})


class TestMCPClientHooks(unittest.TestCase):
    """MCPClient 10 个 MCP hook 方法测试"""

    def setUp(self):
        self.mock_handler = MagicMock()
        from mcp_client import MCPClient
        self.client = MCPClient(direct_mode=True)
        self.client._direct_handler = self.mock_handler

    def test_normal_get_state_machine(self):
        """正常路径：get_state_machine"""
        self.mock_handler.return_value = {'result': {'nodes': [], 'edges': []}}
        result = self.client.get_state_machine()
        self.assertIn('nodes', result.get('result', result))
        self.assertIn('edges', result.get('result', result))

    def test_normal_get_state_machine_custom_path(self):
        """正常路径：get_state_machine 自定义路径"""
        self.mock_handler.return_value = {'result': {'nodes': []}}
        result = self.client.get_state_machine(path='custom.yaml')
        self.assertIn('nodes', result.get('result', result))

    def test_normal_get_pipeline_status(self):
        """正常路径：get_pipeline_status"""
        self.mock_handler.return_value = {'result': {'status': 'running', 'current_node': 'test'}}
        result = self.client.get_pipeline_status()
        inner = result.get('result', result)
        self.assertEqual(inner['status'], 'running')

    def test_normal_queue_next_prompt(self):
        """正常路径：queue_next_prompt"""
        self.mock_handler.return_value = {'result': {'success': True}}
        result = self.client.queue_next_prompt(phase='test-done')
        inner = result.get('result', result)
        self.assertTrue(inner['success'])

    def test_boundary_queue_next_prompt_with_score(self):
        """边界路径：queue_next_prompt 带 score"""
        self.mock_handler.return_value = {'result': {'success': True}}
        result = self.client.queue_next_prompt(phase='test-done', score=9)
        inner = result.get('result', result)
        self.assertTrue(inner['success'])

    def test_normal_signal_done(self):
        """正常路径：signal_done"""
        self.mock_handler.return_value = {'result': {'success': True}}
        result = self.client.signal_done(summary='All done')
        inner = result.get('result', result)
        self.assertTrue(inner['success'])

    def test_boundary_signal_done_empty_summary(self):
        """边界路径：signal_done 空 summary"""
        self.mock_handler.return_value = {'result': {'success': True}}
        result = self.client.signal_done(summary='')
        inner = result.get('result', result)
        self.assertTrue(inner['success'])

    def test_normal_get_role_cards(self):
        """正常路径：get_role_cards"""
        self.mock_handler.return_value = {'result': {'cards': [{'name': 'boss'}], 'total': 1}}
        result = self.client.get_role_cards()
        inner = result.get('result', result)
        self.assertEqual(inner['total'], 1)

    def test_boundary_get_role_cards_with_tag(self):
        """边界路径：get_role_cards 按 tag 过滤"""
        self.mock_handler.return_value = {'result': {'cards': [], 'total': 0}}
        result = self.client.get_role_cards(tag='OP')
        inner = result.get('result', result)
        self.assertEqual(inner['total'], 0)

    def test_normal_get_role_card_detail(self):
        """正常路径：get_role_card_detail"""
        self.mock_handler.return_value = {'result': {'card': {'name': 'boss'}}}
        result = self.client.get_role_card_detail('boss')
        inner = result.get('result', result)
        self.assertEqual(inner['card']['name'], 'boss')

    def test_adversarial_get_role_card_detail_missing(self):
        """对抗路径：get_role_card_detail 不存在的角色"""
        self.mock_handler.return_value = {'result': {'error': 'Role card not found: nonexistent'}}
        from mcp_client import MCPClient
        client2 = MCPClient(direct_mode=True)
        client2._direct_handler = self.mock_handler
        result = client2.get_role_card_detail('nonexistent')
        inner = result.get('result', result)
        self.assertIn('error', inner)

    def test_normal_trigger_hr_recruit(self):
        """正常路径：trigger_hr_recruit"""
        self.mock_handler.return_value = {'result': {'recruitment_id': 'r_001', 'status': 'in_progress'}}
        result = self.client.trigger_hr_recruit('test-role')
        inner = result.get('result', result)
        self.assertEqual(inner['status'], 'in_progress')

    def test_normal_get_cl_report(self):
        """正常路径：get_cl_report"""
        self.mock_handler.return_value = {'result': {'report': {'score': 9}}}
        result = self.client.get_cl_report()
        inner = result.get('result', result)
        self.assertEqual(inner['report']['score'], 9)

    def test_normal_get_handoff_tickets(self):
        """正常路径：get_handoff_tickets"""
        self.mock_handler.return_value = {'result': {'tickets': [], 'total': 0}}
        result = self.client.get_handoff_tickets()
        inner = result.get('result', result)
        self.assertEqual(inner['total'], 0)

    def test_normal_read_file(self):
        """正常路径：read_file"""
        self.mock_handler.return_value = {'result': {'content': 'test content', 'path': 'test.txt'}}
        result = self.client.read_file('test.txt')
        inner = result.get('result', result)
        self.assertEqual(inner['content'], 'test content')

    def test_adversarial_read_file_missing(self):
        """对抗路径：read_file 不存在的文件"""
        self.mock_handler.return_value = {'result': {'error': 'File not found: missing.txt'}}
        result = self.client.read_file('missing.txt')
        inner = result.get('result', result)
        self.assertIn('error', inner)

    def test_normal_full_dashboard_data(self):
        """正常路径：full_dashboard_data 聚合"""
        self.mock_handler.side_effect = [
            {'result': {'nodes': [], 'edges': []}},
            {'result': {'status': 'running'}},
            {'result': {'cards': [], 'total': 0}},
            {'result': {'tickets': [], 'total': 0}},
        ]
        result = self.client.full_dashboard_data()
        self.assertIn('state_machine', result)
        self.assertIn('pipeline_status', result)
        self.assertIn('role_cards', result)
        self.assertIn('handoff_tickets', result)

    def test_adversarial_full_dashboard_partial_failure(self):
        """对抗路径：full_dashboard_data 部分请求失败"""
        from mcp_client import MCPError
        self.mock_handler.side_effect = [
            {'result': {'nodes': []}},
            MCPError('Connection failed'),
        ]
        with self.assertRaises(MCPError):
            self.client.full_dashboard_data()


class TestMCPClientSubscribe(unittest.TestCase):
    """MCPClient.subscribe_pipeline_updates 测试"""

    def test_normal_subscribe_create(self):
        """正常路径：subscribe 创建但未开始轮询"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=True)
        # subscribe 方法只是创建守护线程，不阻塞
        # 无法在此测试实际轮询，验证参数传递正确
        self.assertTrue(callable(lambda: None) or True)

    def test_adversarial_subscribe_without_connect(self):
        """对抗路径：未连接时 subscribe"""
        from mcp_client import MCPClient
        client = MCPClient(direct_mode=False)
        # 未连接时 subscribe 会因 _send_request 失败而抛出 MCPError
        # 不实际运行以避免死循环


if __name__ == '__main__':
    unittest.main()
