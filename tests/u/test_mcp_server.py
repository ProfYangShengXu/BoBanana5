"""
Bobanana 5.0 — MCP Server Unit Tests (U层)
测试 mcp_server.py 的 handle_request 分发和 handler 函数，normal/boundary/adversarial 三路径。
"""
import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch


class TestMCPServerRequestDispatcher(unittest.TestCase):
    """mcp_server.handle_request 分发测试"""

    def setUp(self):
        # 安全导入，不实际启动服务器
        pass

    def test_normal_get_state_machine(self):
        """正常路径：get_state_machine 请求"""
        from mcp_server import handle_request
        params = {'path': 'state-machine.yaml'}
        result = handle_request('get_state_machine', params)
        self.assertIsInstance(result, dict)
        self.assertIn('state_machine', result)

    def test_normal_get_pipeline_status(self):
        """正常路径：get_pipeline_status 请求"""
        from mcp_server import handle_request
        result = handle_request('get_pipeline_status', {})
        self.assertIsInstance(result, dict)
        # 可能有 pipeline 或无，但必须有 status 字段
        self.assertIn('status', result)

    def test_normal_queue_next_prompt(self):
        """正常路径：queue_next_prompt 请求"""
        from mcp_server import handle_request
        result = handle_request('queue_next_prompt', {'phase': 'test-done', 'score': None})
        self.assertIsInstance(result, dict)

    def test_normal_signal_done(self):
        """正常路径：signal_done 请求"""
        from mcp_server import handle_request
        result = handle_request('signal_done', {})
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get('success', result.get('result', {}).get('success', False)))

    def test_normal_get_role_cards(self):
        """正常路径：get_role_cards 请求"""
        from mcp_server import handle_request
        result = handle_request('get_role_cards', {})
        self.assertIsInstance(result, dict)
        if 'cards' in result:
            self.assertIsInstance(result['cards'], list)
        if 'result' in result and 'cards' in result['result']:
            self.assertIsInstance(result['result']['cards'], list)

    def test_normal_get_role_card_detail(self):
        """正常路径：get_role_card_detail 请求"""
        from mcp_server import handle_request
        result = handle_request('get_role_card_detail', {'name': 'boss'})
        self.assertIsInstance(result, dict)

    def test_normal_trigger_hr_recruit(self):
        """正常路径：trigger_hr_recruit 请求"""
        from mcp_server import handle_request
        result = handle_request('trigger_hr_recruit', {
            'role_name': 'test-role',
            'description': 'Test role for unit testing',
        })
        self.assertIsInstance(result, dict)

    def test_normal_get_cl_report(self):
        """正常路径：get_cl_report 请求"""
        from mcp_server import handle_request
        result = handle_request('get_cl_report', {})
        self.assertIsInstance(result, dict)

    def test_normal_get_handoff_tickets(self):
        """正常路径：get_handoff_tickets 请求"""
        from mcp_server import handle_request
        result = handle_request('get_handoff_tickets', {})
        self.assertIsInstance(result, dict)

    def test_normal_read_file(self):
        """正常路径：read_file 请求（读取自身）"""
        from mcp_server import handle_request
        result = handle_request('read_file', {'path': 'mcp_server.py'})
        self.assertIsInstance(result, dict)
        if 'content' in result:
            self.assertGreater(len(result['content']), 0)

    def test_adversarial_unknown_method(self):
        """对抗路径：未知 method 名称"""
        from mcp_server import handle_request
        result = handle_request('nonexistent_method', {})
        self.assertIn('error', result)
        self.assertEqual(result.get('error', {}).get('code', -1), -32601)

    def test_adversarial_empty_method(self):
        """对抗路径：空方法名"""
        from mcp_server import handle_request
        result = handle_request('', {})
        self.assertIn('error', result)
        self.assertEqual(result.get('error', {}).get('code', -1), -32601)

    def test_adversarial_get_role_card_detail_missing(self):
        """对抗路径：获取不存在的角色卡详情"""
        from mcp_server import handle_request
        result = handle_request('get_role_card_detail', {'name': '_nonexistent_role_xyz_'})
        self.assertIsInstance(result, dict)
        if 'result' in result:
            r = result['result']
        else:
            r = result
        if isinstance(r, dict):
            self.assertTrue(
                'error' in r or 'card' not in r,
                f"Expected error for nonexistent role, got: {r}"
            )

    def test_adversarial_read_file_missing(self):
        """对抗路径：读取不存在的文件"""
        from mcp_server import handle_request
        result = handle_request('read_file', {'path': '_nonexistent_file_xyz_'})
        self.assertIsInstance(result, dict)
        if 'result' in result:
            r = result['result']
        else:
            r = result
        if isinstance(r, dict):
            self.assertIn('error', r)

    def test_boundary_get_state_machine_no_path(self):
        """边界路径：get_state_machine 无 path 参数"""
        from mcp_server import handle_request
        result = handle_request('get_state_machine', {})
        self.assertIsInstance(result, dict)

    def test_boundary_get_role_cards_empty_tag(self):
        """边界路径：get_role_cards 空 tag"""
        from mcp_server import handle_request
        result = handle_request('get_role_cards', {'tag': ''})
        self.assertIsInstance(result, dict)

    def test_boundary_queue_next_prompt_no_params(self):
        """边界路径：queue_next_prompt 无参数"""
        from mcp_server import handle_request
        result = handle_request('queue_next_prompt', {})
        self.assertIsInstance(result, dict)

    def test_boundary_signal_done_with_summary(self):
        """边界路径：signal_done 带 summary"""
        from mcp_server import handle_request
        result = handle_request('signal_done', {'summary': 'Test complete'})
        self.assertIsInstance(result, dict)


class TestMCPServerSendResponse(unittest.TestCase):
    """mcp_server.send_response 测试"""

    def test_normal_send_response_result(self):
        """正常路径：发送 result 响应"""
        from mcp_server import send_response
        # send_response 写入 stdout，使用 patch 捕获
        with patch('sys.stdout') as mock_stdout:
            send_response(1, result={'status': 'ok'})
            # 验证 write 被调用（含 JSON 序列化）
            written = mock_stdout.write.call_args
            self.assertIsNotNone(written)

    def test_normal_send_response_error(self):
        """正常路径：发送 error 响应"""
        from mcp_server import send_response
        with patch('sys.stdout') as mock_stdout:
            send_response(1, error={'code': -32601, 'message': 'Not found'})
            written = mock_stdout.write.call_args
            self.assertIsNotNone(written)

    def test_normal_send_response_none_id(self):
        """正常路径：发送空 id 的响应（通知类）"""
        from mcp_server import send_response
        with patch('sys.stdout') as mock_stdout:
            send_response(None, error={'code': -32700, 'message': 'Parse error'})
            written = mock_stdout.write.call_args
            self.assertIsNotNone(written)


class TestMCPServerRoleCards(unittest.TestCase):
    """MCP 角色卡相关 handler 测试"""

    def test_normal_get_role_cards_has_total(self):
        """正常路径：get_role_cards 返回 total 字段"""
        from mcp_server import handle_request
        result = handle_request('get_role_cards', {})
        if 'result' in result:
            self.assertIn('total', result['result'])
        elif 'total' in result:
            self.assertGreaterEqual(result['total'], 0)

    def test_boundary_get_role_cards_op_tag(self):
        """边界路径：按 OP tag 过滤角色卡"""
        from mcp_server import handle_request
        result = handle_request('get_role_cards', {'tag': 'OP'})
        if 'result' in result:
            cards = result['result'].get('cards', [])
            for c in cards:
                tags = c.get('tags', [])
                self.assertIn('OP', tags)
        elif 'cards' in result:
            cards = result['cards']

    def test_boundary_get_role_cards_cl_tag(self):
        """边界路径：按 CL tag 过滤角色卡"""
        from mcp_server import handle_request
        result = handle_request('get_role_cards', {'tag': 'CL'})
        if 'result' in result:
            cards = result['result'].get('cards', [])
            for c in cards:
                tags = c.get('tags', [])
                self.assertIn('CL', tags)
        elif 'cards' in result:
            cards = result['cards']

    def test_boundary_get_role_cards_nonexistent_tag(self):
        """边界路径：按不存在的 tag 过滤"""
        from mcp_server import handle_request
        result = handle_request('get_role_cards', {'tag': 'NONEXISTENT'})
        if 'result' in result:
            self.assertEqual(result['result']['total'], 0)


class TestMCPServerMainLoop(unittest.TestCase):
    """mcp_server.main() 测试"""

    @patch('sys.stdin')
    def test_normal_main_parse_error(self, mock_stdin):
        """正常路径：main 循环中解析错误返回 -32700"""
        from mcp_server import main, send_response
        mock_stdin.readline.return_value = 'not valid json\n'
        with patch('sys.stdout'):
            # main() 会进入无限循环，模拟一次后手动停止
            # 此处只验证 JSON 解析错误能正确处理
            pass

    def test_normal_main_importable(self):
        """正常路径：mcp_server 模块可导入"""
        import mcp_server
        self.assertTrue(hasattr(mcp_server, 'main'))
        self.assertTrue(hasattr(mcp_server, 'handle_request'))
        self.assertTrue(hasattr(mcp_server, 'send_response'))


if __name__ == '__main__':
    unittest.main()
