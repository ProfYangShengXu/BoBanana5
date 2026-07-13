---
description: 🏭 启动多角色管线（架构师→开发→测试→评判→挑刺大王）。TUI 中跑当前角色，终端用 reasonix cycle --resume 继续。
argument-hint: [goal]
---
用户要求启动管线工作流。目标：$ARGUMENTS

请调用 `run_skill({name: "pipeline", arguments: "Goal: $ARGUMENTS"})` 开启多角色管线。

### 工作方式

1. **当前 session（TUI/chat）**：跑 **一个角色**（架构师→开发→测试→评判→挑刺大王其一）
2. 当前角色完成后 agent 调用 `queue_next_prompt` 保存状态到 `.reasonix/cycle/`
3. **终端继续**：用户执行 `reasonix cycle --resume`，orchestrator 自动进入下一角色

### Goal 模式兼容

如果 Reasonix 运行在 **Goal 模式**（协作方式选择"目标"），pipeline 自动兼容：
- Goal 的 `TASK_CONTRACT`（Context / Request / Output / Constraints）保留在 [DONE] 和 [NEXT] 段中
- 跨 session `queue_next_prompt` 链对接 Goal 的 AutoResearch 持久化路径
- 设一次目标，管线自动推进直到 `signal_done`

**不要**在 bash 里跑 `reasonix cycle`——那会启动子进程。当前 session 只跑一个角色，用 `queue_next_prompt` 传递给 terminal orchestrator。

完成后告知用户产物路径和下一步命令 `reasonix cycle --resume`。
