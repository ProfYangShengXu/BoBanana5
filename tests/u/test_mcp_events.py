"""
Bobanana 5.0 — MCP Events Unit Tests (U层)
测试 mcp_events.py 的 PipelineEvent、EventSubscriber 独立功能，normal/boundary/adversarial 三路径。
"""
import os
import sys
import json
import time
import unittest
from unittest.mock import MagicMock, patch


class TestPipelineEvent(unittest.TestCase):
    """PipelineEvent 基础测试"""

    def test_normal_create_event(self):
        """正常路径：创建事件"""
        from mcp_events import PipelineEvent
        event = PipelineEvent('state_changed', {'node': 'boss'})
        self.assertEqual(event.type, 'state_changed')
        self.assertEqual(event.data, {'node': 'boss'})
        self.assertIsNotNone(event.timestamp)

    def test_normal_to_dict(self):
        """正常路径：to_dict 序列化"""
        from mcp_events import PipelineEvent
        event = PipelineEvent('test_event', {'key': 'value'})
        d = event.to_dict()
        self.assertEqual(d['type'], 'test_event')
        self.assertEqual(d['data'], {'key': 'value'})
        self.assertIn('timestamp', d)

    def test_boundary_empty_data(self):
        """边界路径：空 data 字典"""
        from mcp_events import PipelineEvent
        event = PipelineEvent('empty', {})
        d = event.to_dict()
        self.assertEqual(d['data'], {})

    def test_boundary_empty_type(self):
        """边界路径：空 type 字符串"""
        from mcp_events import PipelineEvent
        event = PipelineEvent('', {'a': 1})
        self.assertEqual(event.type, '')

    def test_boundary_complex_data(self):
        """边界路径：嵌套结构的数据"""
        from mcp_events import PipelineEvent
        complex_data = {'nodes': [{'id': 'a'}, {'id': 'b'}], 'edges': [{'from': 'a', 'to': 'b'}]}
        event = PipelineEvent('complex', complex_data)
        d = event.to_dict()
        self.assertEqual(len(d['data']['nodes']), 2)

    def test_adversarial_none_data(self):
        """对抗路径：data 为 None"""
        from mcp_events import PipelineEvent
        event = PipelineEvent('null_data', None)
        d = event.to_dict()
        self.assertIsNone(d['data'])

    def test_adversarial_non_string_type(self):
        """对抗路径：非字符串 type"""
        from mcp_events import PipelineEvent
        event = PipelineEvent(123, {'ok': True})
        d = event.to_dict()
        # type 应为字符串，但这里测试不会崩溃即可
        self.assertEqual(d['type'], 123)


class TestEventSubscriberInit(unittest.TestCase):
    """EventSubscriber 初始化测试"""

    def test_normal_init(self):
        """正常路径：默认初始化"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        self.assertEqual(len(sub._callbacks), 0)
        self.assertIsNotNone(sub._stop_event)
        self.assertIsNone(sub._thread)
        self.assertEqual(sub._last_hashes, {})

    def test_normal_subscribe(self):
        """正常路径：订阅回调"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        cb = lambda e: None
        sid = sub.subscribe(cb)
        self.assertEqual(sid, 0)
        self.assertEqual(len(sub._callbacks), 1)
        self.assertIs(sub._callbacks[0], cb)

    def test_normal_subscribe_multiple(self):
        """正常路径：订阅多个回调"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        ids = []
        for i in range(5):
            ids.append(sub.subscribe(lambda e, x=i: None))
        self.assertEqual(ids, [0, 1, 2, 3, 4])
        self.assertEqual(len(sub._callbacks), 5)

    def test_normal_unsubscribe(self):
        """正常路径：取消订阅"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sid = sub.subscribe(lambda e: None)
        sub.unsubscribe(sid)
        self.assertIsNone(sub._callbacks[sid])

    def test_boundary_unsubscribe_invalid_id(self):
        """边界路径：取消不存在的订阅 ID（代码中有安全检查，不抛异常）"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sub.unsubscribe(999)
        self.assertEqual(len(sub._callbacks), 0)

    def test_adversarial_unsubscribe_negative_id(self):
        """对抗路径：负数订阅 ID（代码中有安全检查，不抛异常）"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sub.unsubscribe(-1)


class TestEventSubscriberFileHash(unittest.TestCase):
    """EventSubscriber._file_hash 测试"""

    def setUp(self):
        from mcp_events import EventSubscriber
        self.sub = EventSubscriber()
        self.tmpfile = '_test_hash_file_.tmp'

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_normal_file_hash_exists(self):
        """正常路径：计算存在的文件 hash"""
        with open(self.tmpfile, 'w') as f:
            f.write('test content')
        h = self.sub._file_hash(self.tmpfile)
        self.assertIsNotNone(h)
        self.assertEqual(len(h), 32)  # MD5 hex digest 长度

    def test_normal_file_hash_consistent(self):
        """正常路径：相同内容 hash 一致"""
        with open(self.tmpfile, 'w') as f:
            f.write('consistent content')
        h1 = self.sub._file_hash(self.tmpfile)
        h2 = self.sub._file_hash(self.tmpfile)
        self.assertEqual(h1, h2)

    def test_boundary_empty_file(self):
        """边界路径：空文件"""
        with open(self.tmpfile, 'w') as f:
            pass  # 空文件
        h = self.sub._file_hash(self.tmpfile)
        self.assertIsNotNone(h)  # 空文件也有 MD5

    def test_adversarial_file_not_found(self):
        """对抗路径：文件不存在"""
        h = self.sub._file_hash('_nonexistent_file_xyz_')
        self.assertIsNone(h)

    def test_adversarial_large_content(self):
        """对抗路径：大文件"""
        with open(self.tmpfile, 'w') as f:
            f.write('x' * 100000)  # 100KB
        h = self.sub._file_hash(self.tmpfile)
        self.assertIsNotNone(h)


class TestEventSubscriberNotify(unittest.TestCase):
    """EventSubscriber._notify 测试"""

    def setUp(self):
        from mcp_events import EventSubscriber, PipelineEvent
        self.sub = EventSubscriber()
        self.event = PipelineEvent('test', {'ok': True})

    def test_normal_notify_single_callback(self):
        """正常路径：通知单个回调"""
        results = []
        self.sub.subscribe(lambda e: results.append(e.type))
        self.sub._notify(self.event)
        self.assertEqual(results, ['test'])

    def test_normal_notify_multiple_callbacks(self):
        """正常路径：通知多个回调"""
        results = []
        for i in range(3):
            self.sub.subscribe(lambda e, x=i: results.append(x))
        self.sub._notify(self.event)
        self.assertEqual(sorted(results), [0, 1, 2])

    def test_adversarial_callback_raises_exception(self):
        """对抗路径：回调抛出异常"""
        def bad_cb(e):
            raise ValueError('Callback error')
        good_results = []
        self.sub.subscribe(bad_cb)
        self.sub.subscribe(lambda e: good_results.append('ok'))
        # 不应抛出异常
        self.sub._notify(self.event)
        self.assertEqual(good_results, ['ok'])

    def test_boundary_notify_without_callbacks(self):
        """边界路径：无回调时通知"""
        # 不应崩溃
        self.sub._notify(self.event)

    def test_boundary_notify_none_event(self):
        """边界路径：通知 None"""
        # 不应崩溃（实际 _notify 不会收到 None，但防御性检查）
        self.sub._notify(None)


class TestEventSubscriberStartStop(unittest.TestCase):
    """EventSubscriber.start/stop 测试"""

    def test_normal_start(self):
        """正常路径：启动轮询"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        result = sub.start(interval=0.1)
        self.assertIs(result, sub)  # 返回 self 支持链式调用
        self.assertIsNotNone(sub._thread)
        self.assertTrue(sub._thread.is_alive())
        sub.stop()

    def test_normal_stop(self):
        """正常路径：停止轮询"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sub.start(interval=0.1)
        sub.stop()
        self.assertTrue(sub._stop_event.is_set())  # stop 后 stop_event 被设置

    def test_normal_start_once(self):
        """正常路径：多次启动（幂等）"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sub.start(interval=0.1)
        sub.start(interval=0.1)  # 第二次不应启动新线程
        sub.stop()

    def test_boundary_stop_without_start(self):
        """边界路径：未启动时停止"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sub.stop()  # 不应崩溃
        self.assertIsNone(sub._thread)

    def test_boundary_stop_twice(self):
        """边界路径：重复停止"""
        from mcp_events import EventSubscriber
        sub = EventSubscriber()
        sub.start(interval=0.1)
        sub.stop()
        sub.stop()  # 再次停止不应崩溃
        self.assertTrue(sub._stop_event.is_set())


class TestEventSubscriberCheckFile(unittest.TestCase):
    """EventSubscriber._check_file 测试"""

    def setUp(self):
        from mcp_events import EventSubscriber
        self.sub = EventSubscriber()
        self.tmpfile = '_test_check_file_.json'

    def tearDown(self):
        if os.path.exists(self.tmpfile):
            os.remove(self.tmpfile)

    def test_normal_first_check_skipped(self):
        """正常路径：首次检查跳过（避免启动时误报）"""
        with open(self.tmpfile, 'w') as f:
            json.dump({'key': 'value'}, f)
        event = self.sub._check_file(self.tmpfile, 'file_changed')
        self.assertIsNone(event)  # 首次检查被跳过

    def test_normal_second_check_detects_change(self):
        """正常路径：第二次检查检测到变化"""
        with open(self.tmpfile, 'w') as f:
            json.dump({'key': 'v1'}, f)
        self.sub._check_file(self.tmpfile, 'file_changed')  # 首次，被跳过
        time.sleep(0.1)
        with open(self.tmpfile, 'w') as f:
            json.dump({'key': 'v2'}, f)
        event = self.sub._check_file(self.tmpfile, 'file_changed')  # 第二次，检测到变化
        self.assertIsNotNone(event)
        self.assertEqual(event.type, 'file_changed')
        self.assertEqual(event.data['key'], 'v2')

    def test_normal_check_no_change(self):
        """正常路径：文件未变化时无事件"""
        with open(self.tmpfile, 'w') as f:
            json.dump({'key': 'stable'}, f)
        self.sub._check_file(self.tmpfile, 'file_changed')  # 首次跳过
        event = self.sub._check_file(self.tmpfile, 'file_changed')  # 未变化
        self.assertIsNone(event)

    def test_adversarial_file_deleted_after_first_check(self):
        """对抗路径：首次检查后文件被删除"""
        with open(self.tmpfile, 'w') as f:
            json.dump({'key': 'value'}, f)
        self.sub._check_file(self.tmpfile, 'file_changed')  # 首次
        os.remove(self.tmpfile)  # 删除文件
        event = self.sub._check_file(self.tmpfile, 'file_changed')  # 检测到变化
        # 文件删除可能触发事件（hash 从 md5 → None）
        self.assertIsNotNone(event)

    def test_adversarial_corrupt_json(self):
        """对抗路径：文件内容不是合法 JSON，但 hash 变化时应触发事件"""
        # 首次写入合法 JSON
        with open(self.tmpfile, 'w') as f:
            f.write('{"valid": "first"}')
        self.sub._check_file(self.tmpfile, 'file_changed')  # 首次跳过
        # 写入非法 JSON（hash 变化）
        with open(self.tmpfile, 'w') as f:
            f.write('not valid json content')
        event = self.sub._check_file(self.tmpfile, 'file_changed')
        # 代码中 except 捕获 JSONDecodeError，data = {}
        self.assertIsNotNone(event)
        self.assertEqual(event.data, {})


if __name__ == '__main__':
    unittest.main()
