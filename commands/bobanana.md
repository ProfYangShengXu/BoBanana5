---
name: bobanana
description: 🍌 Bobanana 5.0 管线入口 — 进入 Boss 角色启动完整管线。快捷版用 /bb。
argument-hint: "<目标>"
---

用户调用 Bobanana 5.0 管线。参数：$ARGUMENTS

## 执行

1. 读 `skills/bobanana/SKILL.md`，按入口 skill 要求进入 Boss 角色
2. Boss 读角色卡库 → 架构师 → 按贪心状态机 v15 推进
3. 不询问确认，直接开干

## 特殊参数

如果参数含 "gui" 或 "--gui"：
  运行后台命令 `python bobanana.py --gui` 启动仪表盘
  然后退出（不走管线）

如果参数含 "test" 或 "--test"：
  运行 `python -m pytest tests/ -v` 运行全部测试
  然后退出（不走管线）

否则：启动完整管线（同 `/bb`）
