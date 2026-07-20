/**
 * M8 · Log Capture & Parser — 日志捕获
 *
 * 调用 M6（Godot CLI Bridge）的 RunGodot 运行 godot --headless，
 * 捕获 stdout/stderr 后再调用 ParseLogText 解析为结构化条目。
 * 提供一条命令完成「启动 → 捕获 → 解析」的完整流程。
 *
 * @module tools/log_capture
 */

import { RunGodot, type RunGodotInput, type RunGodotOutput } from "./godot_cli";
import { ParseLogText, SummarizeLogs, type LogEntry, type LogSummary } from "./log_parser";

// ─── 类型定义 ───

export interface CaptureLogsInput {
  /** Godot 项目根目录 */
  project_root: string;
  /** 超时秒数，默认 30 */
  timeout_sec?: number;
  /** 额外的 godot CLI 参数（如 --script run_test.gd） */
  godot_args?: string[];
  /** Godot 可执行文件路径 */
  godot_path?: string;
}

export interface CaptureLogsOutput {
  /** 原始 stdout */
  raw_stdout: string;
  /** 原始 stderr */
  raw_stderr: string;
  /** 结构化日志条目 */
  entries: LogEntry[];
  /** 日志摘要 */
  summary: LogSummary;
  /** Godot 进程退出码 */
  exit_code: number;
  error?: string;
}

// ─── 主接口 ───

/**
 * CaptureLogs — 运行 godot 并捕获完整输出
 *
 * 1. 调用 M6 RunGodot 启动 godot --headless
 * 2. 分别解析 stdout 和 stderr
 * 3. 合并条目，按时间戳排序
 * 4. 生成日志摘要
 *
 * 超时和错误处理由 M6 负责，本模块专注数据整合。
 */
export async function CaptureLogs(
  input: CaptureLogsInput,
): Promise<CaptureLogsOutput> {
  const { project_root, timeout_sec, godot_args, godot_path } = input;

  if (!project_root) {
    return {
      raw_stdout: "",
      raw_stderr: "",
      entries: [],
      summary: emptySummary(),
      exit_code: -1,
      error: "project_root 不能为空",
    };
  }

  // 构建 RunGodot 参数
  const runInput: RunGodotInput = {
    project_root,
    args: godot_args ?? [],
    timeout_sec: timeout_sec ?? 30,
    godot_path,
  };

  let result: RunGodotOutput;
  try {
    result = await RunGodot(runInput);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      raw_stdout: "",
      raw_stderr: "",
      entries: [],
      summary: emptySummary(),
      exit_code: -1,
      error: `调用 RunGodot 失败: ${message}`,
    };
  }

  // 解析 stdout
  const stdoutResult = ParseLogText({
    raw_text: result.stdout,
    source: "stdout",
  });

  // 解析 stderr
  const stderrResult = ParseLogText({
    raw_text: result.stderr,
    source: "stderr",
  });

  // 合并条目，按时间戳排序
  const allEntries = [...stdoutResult.entries, ...stderrResult.entries];

  // 如果 M6 返回了错误（如 Godot 未安装），添加到条目中
  if (result.error) {
    allEntries.push({
      level: "error",
      message: `[系统] ${result.error}`,
      timestamp: allEntries.length > 0
        ? allEntries[allEntries.length - 1]!.timestamp + 1
        : 0,
      raw: result.error,
      category: "system",
    });
  }

  // 生成摘要
  const summaryResult = SummarizeLogs({ entries: allEntries });

  return {
    raw_stdout: result.stdout,
    raw_stderr: result.stderr,
    entries: allEntries,
    summary: summaryResult.summary,
    exit_code: result.exit_code,
    error: result.error,
  };
}

// ─── 辅助函数 ───

function emptySummary(): LogSummary {
  return {
    stats: { total: 0, errors: 0, warnings: 0, infos: 0, debug: 0 },
    top_errors: [],
    timeline: [],
    diagnosis_hints: [],
  };
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/log_capture.ts <project_root> [--args <godot_args...>] [--timeout <sec>]");
    process.exit(1);
  }

  const projectRoot = args[0];
  const argsIdx = args.indexOf("--args");
  const timeoutIdx = args.indexOf("--timeout");

  const godotArgs: string[] = [];
  if (argsIdx >= 0 && args[argsIdx + 1]) {
    // 收集 --args 后的所有参数直到下一个 -- 或选项
    for (let i = argsIdx + 1; i < args.length; i++) {
      if (args[i]!.startsWith("--") && args[i] !== "--args") break;
      godotArgs.push(args[i]!);
    }
  }

  const timeoutSec = timeoutIdx >= 0 && args[timeoutIdx + 1]
    ? parseInt(args[timeoutIdx + 1]!, 10)
    : 30;

  const result = await CaptureLogs({
    project_root: projectRoot,
    timeout_sec: timeoutSec,
    godot_args: godotArgs.length > 0 ? godotArgs : undefined,
  });

  if (result.error) {
    console.error("❌", result.error);
  }

  // 输出摘要
  console.log(`\n📊 日志摘要:`);
  console.log(`   总计: ${result.summary.stats.total} 条`);
  console.log(`   ❌ 错误: ${result.summary.stats.errors}`);
  console.log(`   ⚠️  警告: ${result.summary.stats.warnings}`);
  console.log(`   ℹ️  信息: ${result.summary.stats.infos}`);
  console.log(`   🔍 调试: ${result.summary.stats.debug}`);
  console.log(`   🚪 退出码: ${result.exit_code}`);

  if (result.summary.top_errors.length > 0) {
    console.log(`\n🔴 前 ${result.summary.top_errors.length} 个高频错误:`);
    for (const err of result.summary.top_errors) {
      console.log(`   ${err.file}:${err.line} (${err.count} 次): ${err.example}`);
    }
  }

  if (result.summary.diagnosis_hints.length > 0) {
    console.log(`\n💡 诊断提示:`);
    for (const hint of result.summary.diagnosis_hints) {
      console.log(`   - ${hint}`);
    }
  }
}

if (process.argv[1]?.endsWith("log_capture.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
