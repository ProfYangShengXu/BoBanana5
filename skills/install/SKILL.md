---
name: install
description: 🍌 [All] 安装/更新 Bobanana 5.0 全部功能到当前项目（docs + cycle + loop + Bobanana.md）。
runAs: inline
profiles: economy, balanced, delivery
cost: low
---

# install — 安装/更新 Bobanana 5.0

## 步骤 0：检查全局

检查 `~/.reasonix/skills/` 下是否有 docs / cycle / loop 任一存在。全缺则报错——让用户先 `git clone` 后运行 `install.bat`。

## 步骤 1：读源文件

从全局读取：`docs/SKILL.md`、`cycle/SKILL.md`、`loop/SKILL.md`、`install/SKILL.md`（自更新）、`Bobanana.md`、`commands/cycle.md`。缺的跳过。

## 步骤 2：写入项目级

覆盖写入 `.reasonix/skills/{docs,cycle,loop,install}/SKILL.md`、`.reasonix/Bobanana.md`、`.reasonix/commands/cycle.md`。

## 步骤 3：修复 reasonix.toml

同旧版逻辑——文件不存在则创建，缺插件则追加。

## 步骤 4：汇报

安装结果清单。告知用户可用：
- `/docs 目标` — 产品设计文档
- `/cycle 目标` — 多 subagent 并行循环
- `/loop 目标` — 单 agent 串行循环
- `/skill install` — 本安装器
