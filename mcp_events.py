#!/usr/bin/env python3
"""
Bobanana 5.0 — Event Subscription Mechanism
事件订阅机制，为 GUI 提供实时管线状态推送。
EUI-NEO C++ 端应通过命名管道或 WebSocket 替代此实现。

支持:
    1. 文件监视 (polling) — 通过 .reasonix/state/machine_state.json 变化
    2. 订阅回调 (callback) — 状态变化时通知
    3. JSON 事件流 (events) — 供外部进程订阅
"""

import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime
from threading import Thread, Event


class PipelineEvent:
    """管线事件"""

    def __init__(self, event_type, data):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            'type': self.type,
            'data': self.data,
            'timestamp': self.timestamp,
        }


class EventSubscriber:
    """
    事件订阅器。监视管线状态文件变化，触发回调。

    EUI-NEO 集成:
        // C++ 端通过 stdio 读取事件流:
        // FILE* events = popen("python3 mcp_events.py --json", "r");
        // while (fgets(line, sizeof(line), events)) {
        //     json_parse(line); // 解析事件 JSON
        //     render_update(event); // 更新 UI
        // }
    """

    def __init__(self):
        self._callbacks = []
        self._stop_event = Event()
        self._thread = None
        self._last_hashes = {}

    # ── 订阅管理 ──────────────────────────────────

    def subscribe(self, callback):
        """订阅状态变化事件"""
        self._callbacks.append(callback)
        return len(self._callbacks) - 1  # subscription_id

    def unsubscribe(self, subscription_id):
        """取消订阅"""
        if 0 <= subscription_id < len(self._callbacks):
            self._callbacks[subscription_id] = None

    # ── 文件监视 ──────────────────────────────────

    def _file_hash(self, path):
        """计算文件哈希"""
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _check_file(self, path, event_type):
        """检查单个文件变化"""
        current_hash = self._file_hash(path)
        last_hash = self._last_hashes.get(path)

        if current_hash != last_hash:
            self._last_hashes[path] = current_hash
            if last_hash is not None:  # 跳过首次
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    logging.warning("文件读取异常: %s", path)
                    data = {}
                event = PipelineEvent(event_type, data)
                self._notify(event)
                return event
        return None

    def _notify(self, event):
        """通知所有订阅者"""
        for callback in self._callbacks:
            if callback:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Event callback error: {e}", file=sys.stderr)

    # ── 启动/停止 ─────────────────────────────────

    def start(self, interval=1.0):
        """启动事件监视"""
        if self._thread and self._thread.is_alive():
            return

        def _loop():
            while not self._stop_event.is_set():
                # 检查状态机状态变化
                self._check_file('.reasonix/state/machine_state.json', 'state_changed')
                # 检查管线状态变化
                pipeline_dir = '.reasonix/pipelines'
                if os.path.exists(pipeline_dir):
                    files = sorted(os.listdir(pipeline_dir), reverse=True)
                    if files:
                        self._check_file(
                            os.path.join(pipeline_dir, files[0]),
                            'pipeline_changed'
                        )
                # 检查手单变化
                handoff_dir = '.reasonix/handoffs'
                if os.path.exists(handoff_dir):
                    # directory change check removed (use file-level monitoring)
                    # 监视新工单文件
                    for f in os.listdir(handoff_dir):
                        if f.endswith('.json'):
                            self._check_file(
                                os.path.join(handoff_dir, f),
                                'handoff_created'
                            )

                self._stop_event.wait(interval)

        self._stop_event.clear()
        self._thread = Thread(target=_loop, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        """停止事件监视"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)

    # ── 事件流（JSON Lines 格式，供子进程读取）───

    def event_stream(self):
        """
        生成 JSON Lines 事件流。
        EUI-NEO 可通过 popen 读取此流实现实时更新。
        """
        def callback(event):
            line = json.dumps(event.to_dict(), ensure_ascii=False)
            print(line, flush=True)

        sub_id = self.subscribe(callback)
        self.start(interval=0.5)

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
            self.unsubscribe(sub_id)


# ── 命令行 ──────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bobanana 5.0 Event Subscriber')
    parser.add_argument('--json', action='store_true', help='JSON Lines 事件流模式')
    parser.add_argument('--once', action='store_true', help='单次检查')
    args = parser.parse_args()

    sub = EventSubscriber()

    if args.json:
        sub.event_stream()
        return

    if args.once:
        sub._check_file('.reasonix/state/machine_state.json', 'state_changed')
        return

    # Demo: 打印事件
    def on_event(event):
        print(f"[{event.type}] {json.dumps(event.data, ensure_ascii=False)[:80]}")

    sub.subscribe(on_event)
    sub.start(interval=1)
    print("事件监视中 (Ctrl+C 退出)...")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        sub.stop()


if __name__ == '__main__':
    import sys
    main()
