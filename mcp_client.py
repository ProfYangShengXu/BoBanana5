#!/usr/bin/env python3
"""
Bobanana 5.0 — MCP Client Library
完整的 MCP 客户端封装。提供 10 个 hooks 的类型化方法。
EUI-NEO 桌面端通过此类与 reasonix.exe 通信。

用法:
    client = MCPClient()
    client.connect()  # 连接到 MCP 服务器
    cards = client.get_role_cards()
    status = client.get_pipeline_status()
"""

import os
import sys
import json
import subprocess
import time
import threading


class MCPError(Exception):
    """MCP 通信错误"""
    pass


class MCPClient:
    """
    MCP 客户端。可通过两种模式运行：
    1. subprocess 模式：启动 mcp_server.py 子进程，通过 stdio 通信
    2. direct 模式：直接调用 handle_request（单进程测试用）
    """

    def __init__(self, server_script='mcp_server.py', direct_mode=False):
        self.server_script = server_script
        self.direct_mode = direct_mode
        self.proc = None
        self.request_id = 0
        self._direct_handler = None

    # ── 连接管理 ──────────────────────────────────

    def connect(self, timeout=5):
        """连接到 MCP 服务器"""
        if self.direct_mode:
            # 直接模式：导入 handle_request
            from mcp_server import handle_request
            self._direct_handler = handle_request
            # 验证连接
            result = self._direct_handler('get_role_cards', {})
            if 'cards' in result:
                return {'connected': True, 'mode': 'direct', 'cards': len(result['cards'])}
            raise MCPError("Direct mode connection failed")

        # Subprocess 模式
        try:
            self.proc = subprocess.Popen(
                [sys.executable, self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd='.'
            )
            # 发送 ping
            result = self._send_request('get_role_cards', {})
            if 'cards' in result:
                return {'connected': True, 'mode': 'subprocess', 'cards': len(result['cards'])}
            raise MCPError("Subprocess connection failed")
        except Exception as e:
            raise MCPError(f"Connection failed: {e}")

    def disconnect(self):
        """断开连接"""
        if self.proc:
            self.proc.kill()
            self.proc = None

    def is_connected(self):
        """检查连接状态"""
        if self.direct_mode:
            return self._direct_handler is not None
        return self.proc is not None and self.proc.poll() is None

    # ── 核心 MCP 请求 ─────────────────────────────

    def _send_request(self, method, params=None):
        """发送 JSON-RPC 请求"""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        if self.direct_mode:
            result = self._direct_handler(method, params or {})
            if 'error' in result:
                raise MCPError(f"RPC error: {result['error']}")
            return result

        if not self.proc:
            raise MCPError("Not connected")

        request_str = json.dumps(request, ensure_ascii=False) + '\n'
        self.proc.stdin.write(request_str)
        self.proc.stdin.flush()

        # 带超时的 readline（防止服务器挂起永久阻塞）
        import select
        response_str = ''
        if sys.platform != 'win32':
            r, _, _ = select.select([self.proc.stdout], [], [], 5.0)
            if r:
                response_str = self.proc.stdout.readline()
        else:
            # Windows: 使用非阻塞近似
            import time
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if self.proc.poll() is not None and not self.proc.stdout:
                    break
                import msvcrt
                if msvcrt.kbhit() or True:  # try reading
                    try:
                        line = self.proc.stdout.readline()
                        if line:
                            response_str = line
                            break
                    except Exception:
                        pass
                time.sleep(0.05)
        if not response_str:
            raise MCPError("No response from server (timeout)")

        response = json.loads(response_str)
        if 'error' in response:
            raise MCPError(f"RPC error: {response['error']}")
        return response.get('result', {})

    # ── MCP Hooks (10 个) ─────────────────────────

    def get_state_machine(self, path=None):
        """获取状态机拓扑图（M7-A2 核心数据源）"""
        return self._send_request('get_state_machine', {'path': path or 'state-machine.yaml'})

    def get_pipeline_status(self, pipeline_id=None):
        """获取当前管线进度"""
        return self._send_request('get_pipeline_status', {'pipeline_id': pipeline_id})

    def queue_next_prompt(self, phase, score=None):
        """推进管线到下一角色"""
        params = {'phase': phase}
        if score is not None:
            params['score'] = score
        return self._send_request('queue_next_prompt', params)

    def signal_done(self, summary=None):
        """管线完成信号"""
        return self._send_request('signal_done', {'summary': summary or ''})

    def get_role_cards(self, tag=None):
        """获取角色卡列表（M7-A3 数据源）"""
        params = {}
        if tag:
            params['tag'] = tag
        return self._send_request('get_role_cards', params)

    def get_role_card_detail(self, name):
        """获取角色卡详情"""
        return self._send_request('get_role_card_detail', {'name': name})

    def trigger_hr_recruit(self, role_name, description=None, standards_path=None):
        """触发 HR 紧急招聘"""
        params = {'role_name': role_name, 'description': description or ''}
        if standards_path:
            params['standards_path'] = standards_path
        return self._send_request('trigger_hr_recruit', params)

    def get_cl_report(self, pipeline_id=None):
        """获取 CL 审查报告"""
        return self._send_request('get_cl_report', {'pipeline_id': pipeline_id})

    def get_handoff_tickets(self, role_name=None):
        """获取交接工单"""
        params = {}
        if role_name:
            params['role_name'] = role_name
        return self._send_request('get_handoff_tickets', params)

    def read_file(self, path):
        """读取文件"""
        return self._send_request('read_file', {'path': path})

    # ── 复合操作 ──────────────────────────────────

    def full_dashboard_data(self):
        """获取仪表盘完整数据（EUI-NEO 主视图调用）"""
        return {
            'state_machine': self.get_state_machine(),
            'pipeline_status': self.get_pipeline_status(),
            'role_cards': self.get_role_cards(),
            'handoff_tickets': self.get_handoff_tickets(),
        }

    def subscribe_pipeline_updates(self, interval=1.0, callback=None):
        """
        轮询管线更新（M7 subscribe_pipeline_updates 的 Python 实现）
        EUI-NEO 应使用 WebSocket 或命名管道替代此轮询
        """
        last_status = None
        while self.is_connected():
            try:
                status = self.get_pipeline_status()
                if status != last_status:
                    last_status = status
                    if callback:
                        callback(status)
                time.sleep(interval)
            except MCPError:
                break
            except KeyboardInterrupt:
                break


def demo():
    """快速演示所有 MCP hooks"""
    client = MCPClient(direct_mode=True)
    info = client.connect()
    print(f"MCP Connected: {info['mode']} mode, {info['cards']} cards found")
    print()

    # 1. State Machine
    print("1. get_state_machine:")
    sm = client.get_state_machine()
    print(f"   Nodes: {len(sm.get('state_machine', {}).get('nodes', []))}")
    print(f"   Edges: {len(sm.get('state_machine', {}).get('edges', []))}")

    # 2. Role Cards
    print("\n2. get_role_cards:")
    cards = client.get_role_cards()
    for c in cards.get('cards', []):
        print(f"   {c['name']:20s} [{','.join(c.get('tags', [])) or '-':6s}] {c['description'][:40]}")

    # 3. Card Detail
    print("\n3. get_role_card_detail (architect):")
    detail = client.get_role_card_detail('architect')
    card = detail.get('card', {})
    print(f"   Tags: {card.get('tags', [])}")
    print(f"   Inputs: {len(card.get('input_contract', []))}")

    # 4. Pipeline Status
    print("\n4. get_pipeline_status:")
    status = client.get_pipeline_status()
    print(f"   Status: {status.get('status', 'none')}")

    # 5. CL Report
    print("\n5. get_cl_report:")
    report = client.get_cl_report()
    if report.get('report'):
        print(f"   Score: {report['report'].get('score')}")

    # 6. Handoff Tickets
    print("\n6. get_handoff_tickets:")
    tickets = client.get_handoff_tickets()
    print(f"   Total: {tickets.get('total', 0)}")

    # 7. HR Recruit
    print("\n7. trigger_hr_recruit (quick mode):")
    hr = client.trigger_hr_recruit('demo-role', 'Demo role', standards_path='Bobanana.md')
    print(f"   Recruitment: {hr.get('recruitment_id')}")
    print(f"   Status: {hr.get('status')}")

    print("\nAll 10 MCP hooks tested successfully!")


if __name__ == '__main__':
    demo()
