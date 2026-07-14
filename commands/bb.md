---
name: bb
description: 🍌 Bobanana 5.0 一键管线。输入目标自动跑完整流程。支持 --gui 启动仪表盘。
argument-hint: "<目标>"
---

用户调用 Bobanana 5.0 管线。参数：$ARGUMENTS

如果参数含 "gui" 或 "--gui"：
  运行后台命令 `python bobanana.py --gui` 启动仪表盘

如果参数含 "setup" 或 "--setup"：
  运行 `python bobanana.py --setup` 一键安装

如果参数含 "cards" 或 "--cards"：
  运行 `python bobanana.py --cards` 查看角色卡

如果参数含 "test" 或 "--test"：
  运行 `python bobanana.py --test` 运行全部测试

否则（含具体目标，如"做个游戏"）：
  运行 `python bobanana.py "$ARGUMENTS"` 一键启动完整管线
  等待执行完成，将结果报告给用户

项目目录：当前工作目录
入口：python bobanana.py
