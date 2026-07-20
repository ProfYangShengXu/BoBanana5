"""
Bobanana 5.0 — 定时任务调度 API 单元测试
测试纯函数 API: validate_goal / validate_time / validate_task_id / schedule_create_task / list_tasks / remove_task / get_task_logs
"""

import os, sys, json, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.pipeline_scheduler import (
    validate_goal, validate_time, validate_task_id,
    schedule_create_task, list_tasks, remove_task, get_task_logs,
    CONFIG_DIR, LOG_DIR, TASKS_FILE,
)

import pytest


# ── Fixtures ─────────────────────────────────

@pytest.fixture(autouse=True)
def clean_scheduler_state():
    """每个测试前后清理 scheduler 状态文件"""
    # 保存原状态
    orig_config = None
    if os.path.exists(CONFIG_DIR) and os.path.exists(TASKS_FILE):
        try:
            import shutil
            orig_tmp = tempfile.mkdtemp()
            shutil.copytree(CONFIG_DIR, os.path.join(orig_tmp, 'scheduler'), dirs_exist_ok=True)
            orig_config = orig_tmp
        except Exception:
            pass

    yield

    # 清理测试数据
    if os.path.exists(CONFIG_DIR):
        shutil.rmtree(CONFIG_DIR)
    # 恢复原始配置
    if orig_config:
        src = os.path.join(orig_config, 'scheduler')
        if os.path.exists(src):
            shutil.copytree(src, CONFIG_DIR, dirs_exist_ok=True)
        shutil.rmtree(orig_config)


# ── U 层: validate_goal ──────────────────────

class TestValidateGoal:

    def test_normal_goal(self):
        ok, msg = validate_goal("每日数据更新")
        assert ok
        assert msg == ""

    def test_normal_english(self):
        ok, msg = validate_goal("Daily health check")
        assert ok

    def test_normal_mixed(self):
        ok, msg = validate_goal("定时任务 at 09:00")
        assert ok

    def test_empty_string(self):
        ok, msg = validate_goal("")
        assert not ok
        assert "required" in msg

    def test_none(self):
        ok, msg = validate_goal(None)
        assert not ok

    def test_not_string(self):
        ok, msg = validate_goal(123)
        assert not ok

    def test_too_long(self):
        ok, msg = validate_goal("a" * 201)
        assert not ok
        assert "exceeds" in msg

    def test_boundary_max_len(self):
        ok, msg = validate_goal("a" * 200)
        assert ok

    def test_special_chars_goal(self):
        ok, msg = validate_goal("测试<script>alert(1)</script>")
        assert not ok
        assert "invalid" in msg

    def test_path_traversal_attempt(self):
        # 路径穿越在 goal 层面不构成注入威胁（subprocess 已引用）
        # 实际防护在 task_id validate 和文件路径层
        ok, msg = validate_goal("../../etc/passwd")
        assert ok  # 字符在允许白名单内


# ── U 层: validate_time ──────────────────────

class TestValidateTime:

    def test_normal_time(self):
        ok, msg = validate_time("09:00")
        assert ok

    def test_midnight(self):
        ok, msg = validate_time("00:00")
        assert ok

    def test_end_of_day(self):
        ok, msg = validate_time("23:59")
        assert ok

    def test_empty_string(self):
        ok, msg = validate_time("")
        assert not ok

    def test_none(self):
        ok, msg = validate_time(None)
        assert not ok

    def test_invalid_format_no_colon(self):
        ok, msg = validate_time("0900")
        assert not ok

    def test_invalid_hour(self):
        ok, msg = validate_time("25:00")
        assert not ok

    def test_invalid_minute(self):
        ok, msg = validate_time("09:60")
        assert not ok

    def test_negative_hour(self):
        ok, msg = validate_time("-1:00")
        assert not ok


# ── U 层: validate_task_id ───────────────────

class TestValidateTaskId:

    def test_normal_id(self):
        ok, msg = validate_task_id("a1b2c3d4")
        assert ok

    def test_all_hex(self):
        ok, msg = validate_task_id("abcdef01")
        assert ok

    def test_too_short(self):
        ok, msg = validate_task_id("abc")
        assert not ok

    def test_too_long(self):
        ok, msg = validate_task_id("abcdef0123456789")
        assert not ok

    def test_invalid_chars(self):
        ok, msg = validate_task_id("xyz12345")
        assert not ok

    def test_empty(self):
        ok, msg = validate_task_id("")
        assert not ok

    def test_none(self):
        ok, msg = validate_task_id(None)
        assert not ok

    def test_path_traversal(self):
        ok, msg = validate_task_id("../../..")
        assert not ok


# ── U 层: schedule_create_task ───────────────

class TestScheduleCreate:

    def test_create_task(self):
        result = schedule_create_task("定时数据同步", "08:00", "daily")
        assert "task_id" in result
        assert result["status"] in ("created", "updated")

    def test_create_with_weekday(self):
        result = schedule_create_task("周报生成", "09:00", "mon-fri")
        assert "task_id" in result

    def test_create_with_rounds(self):
        result = schedule_create_task("批量处理", "10:00", "daily", 3)
        assert "task_id" in result

    def test_create_replaces_existing(self):
        r1 = schedule_create_task("替换测试", "08:00")
        assert r1["status"] == "created"
        r2 = schedule_create_task("替换测试", "09:00")
        assert r2["status"] == "updated"

    def test_invalid_goal_empty(self):
        result = schedule_create_task("", "08:00")
        assert "error" in result

    def test_invalid_time(self):
        result = schedule_create_task("test", "abc")
        assert "error" in result

    def test_invalid_weekday(self):
        result = schedule_create_task("test", "08:00", "invalid-day")
        assert "error" in result
        assert "invalid weekday" in result["error"]

    def test_invalid_rounds_zero(self):
        result = schedule_create_task("test", "08:00", "daily", 0)
        assert "error" in result

    def test_invalid_rounds_negative(self):
        result = schedule_create_task("test", "08:00", "daily", -1)
        assert "error" in result


# ── U 层: list_tasks ─────────────────────────

class TestListTasks:

    def test_list_empty(self):
        tasks = list_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) == 0

    def test_list_after_create(self):
        schedule_create_task("列表测试", "08:00")
        tasks = list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["goal"] == "列表测试"

    def test_list_multiple(self):
        schedule_create_task("任务A", "08:00")
        schedule_create_task("任务B", "09:00")
        tasks = list_tasks()
        assert len(tasks) == 2


# ── U 层: remove_task ────────────────────────

class TestRemoveTask:

    def test_remove_existing(self):
        r = schedule_create_task("删除测试", "08:00")
        result = remove_task(r["task_id"])
        assert result["removed"] is True
        assert len(list_tasks()) == 0

    def test_remove_nonexistent(self):
        result = remove_task("ffffffff")
        assert result["removed"] is False

    def test_remove_invalid_id(self):
        result = remove_task("bad")
        assert "error" in result


# ── U 层: get_task_logs ──────────────────────

class TestGetTaskLogs:

    def test_logs_empty(self):
        result = get_task_logs()
        assert "logs" in result
        assert isinstance(result["logs"], list)

    def test_logs_invalid_task_id(self):
        result = get_task_logs("bad-id")
        assert "error" in result
