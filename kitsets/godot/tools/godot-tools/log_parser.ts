/**
 * M8 · Log Capture & Parser — 解析核心
 *
 * 将 godot --headless 的 stdout/stderr 原始文本解析为结构化日志条目。
 * 支持 Godot 4.x 的多种错误/警告格式、GDScript traceback、print() 输出。
 *
 * 解析策略：逐行正则匹配器链（不构建 AST，YAGNI）。
 *
 * @module tools/log_parser
 */

import { readFile } from "node:fs/promises";

// ─── 类型定义 ───

export type LogLevel = "error" | "warning" | "info" | "debug";
export type LogCategory = "script" | "engine" | "print" | "system";

export interface LogEntry {
  /** 日志级别 */
  level: LogLevel;
  /** 日志消息正文 */
  message: string;
  /** 关联的 Godot 资源路径（如 res://scripts/player.gd） */
  file?: string;
  /** 行号 */
  line?: number;
  /** 相对运行起点的毫秒时间戳 */
  timestamp: number;
  /** 原始日志行文本 */
  raw: string;
  /** 日志分类 */
  category: LogCategory;
  /** Godot 错误码（如果有） */
  error_code?: number;
}

export interface LogSummary {
  stats: {
    total: number;
    errors: number;
    warnings: number;
    infos: number;
    debug: number;
  };
  top_errors: Array<{
    file: string;
    line: number;
    count: number;
    example: string;
  }>;
  timeline: Array<{ ms: number; event: string }>;
  diagnosis_hints: string[];
}

export interface ParseLogTextInput {
  /** 原始日志文本 */
  raw_text: string;
  /** 来源（stdout / stderr） */
  source: "stdout" | "stderr";
  /** 可选的起始时间戳偏移 */
  start_time_ms?: number;
}

export interface ParseLogTextOutput {
  entries: LogEntry[];
  error?: string;
}

export interface SummarizeLogsInput {
  entries: LogEntry[];
  include_raw?: boolean;
}

export interface SummarizeLogsOutput {
  summary: LogSummary;
}

// ─── 常量 ───

/** 最大解析行数（防止日志风暴） */
const MAX_LINES = 100_000;

/** 最大条目数 */
const MAX_ENTRIES = 50_000;

// ─── 正则模式 ───

/** Godot 引擎 ERROR 消息：  ERROR: <message> */
const RE_ENGINE_ERROR = /^\s*(?:ERROR|ERR):\s*(.+)$/i;

/** Godot 引擎 WARNING 消息：  WARNING: <message> */
const RE_ENGINE_WARNING = /^\s*WARNING:\s*(.+)$/i;

/** GDScript 脚本错误：  SCRIPT ERROR: <message> */
const RE_SCRIPT_ERROR = /^\s*SCRIPT\s+ERROR:\s*(.+)$/i;

/** GDScript 解析错误：  Parse Error: <message> */
const RE_PARSE_ERROR = /^\s*Parse\s+Error:\s*(.+)$/i;

/** Godot 条件错误：  COND <condition> is false. Return: <value> */
const RE_COND_ERROR = /^\s*COND\s+(.+?)\.\s*Return(?:ing)?:\s*(.+)$/i;

/** GDScript traceback 行：  res://scripts/player.gd:42 */
const RE_TRACEBACK = /^\s*(?:at\s+)?(res:\/\/\S+\.gd):(\d+)/i;

/** 用户 print() 输出 */
// RE_PRINT kept for documentation — matching is handled inline in ParseLogText

/** 结构化 LOG 格式：  LOG:INFO:message 或 LOG:ERROR:message  */
const RE_STRUCTURED_LOG = /^LOG:(ERROR|WARN|INFO|DEBUG):(.+)$/;

/** Godot 运行起始标记 */
const RE_GODOT_START = /^Godot\s+Engine\s+v?[\d.]+/i;

// ─── 匹配器链 ───

interface Matcher {
  /** 正则模式 */
  pattern: RegExp;
  /** 对应的日志级别 */
  level: LogLevel;
  /** 分类 */
  category: LogCategory;
  /** 可选：从 match 中提取消息的索引 */
  messageIndex?: number;
  /** 可选：自定义处理函数 */
  handler?: (match: RegExpExecArray) => Partial<LogEntry>;
}

const MATCHERS: Matcher[] = [
  // Godot 引擎错误
  { pattern: RE_ENGINE_ERROR, level: "error", category: "engine", messageIndex: 1 },
  // Godot 引擎警告
  { pattern: RE_ENGINE_WARNING, level: "warning", category: "engine", messageIndex: 1 },
  // GDScript 错误
  { pattern: RE_SCRIPT_ERROR, level: "error", category: "script", messageIndex: 1 },
  // 解析错误
  { pattern: RE_PARSE_ERROR, level: "error", category: "script", messageIndex: 1 },
  // 条件错误
  { pattern: RE_COND_ERROR, level: "error", category: "engine", messageIndex: 1 },
  // 结构化 LOG 格式
  { pattern: RE_STRUCTURED_LOG, level: "info", category: "print", messageIndex: 2 },
];

// ─── 核心解析函数 ───

/**
 * 检测一行是否为 GDScript traceback 行
 */
function isTracebackLine(line: string): boolean {
  return RE_TRACEBACK.test(line);
}

/**
 * 从 traceback 行提取文件和行号
 */
function extractTraceback(line: string): { file: string; line: number } | null {
  const match = line.match(RE_TRACEBACK);
  if (!match) return null;
  return {
    file: match[1]!,
    line: parseInt(match[2]!, 10),
  };
}

/**
 * 判断一行是否应被忽略（空行、Godot 启动横幅等）
 */
function isIgnorableLine(line: string): boolean {
  const trimmed = line.trim();
  if (trimmed.length === 0) return true;
  if (RE_GODOT_START.test(trimmed)) return true;
  // Godot 的 --- 调试分隔线
  if (/^---+\s*$/.test(trimmed)) return true;
  return false;
}

/**
 * 计算相对毫秒时间戳
 */
function computeTimestamp(lineIndex: number, startTimeMs: number): number {
  // 粗略估计：每行约 5ms（基于典型日志输出速率）
  return startTimeMs + lineIndex * 5;
}

/**
 * ParseLogText — 解析原始日志文本为结构化条目
 *
 * 逐行扫描，用匹配器链识别错误/警告/信息。
 * traceback 行与上一错误条目关联。
 * 忽略空行、启动横幅等噪音。
 */
export function ParseLogText(
  input: ParseLogTextInput,
): ParseLogTextOutput {
  const { raw_text, source, start_time_ms = 0 } = input;

  const lines = raw_text.split("\n");
  if (lines.length > MAX_LINES) {
    lines.length = MAX_LINES; // 截断防风暴
  }

  const entries: LogEntry[] = [];
  let lastEntry: LogEntry | null = null;
  let lineCount = 0;

  for (let i = 0; i < lines.length && entries.length < MAX_ENTRIES; i++) {
    const line = lines[i]!;
    lineCount++;

    if (isIgnorableLine(line)) continue;

    const timestamp = computeTimestamp(i, start_time_ms);
    let matched = false;

    // 尝试匹配结构化日志格式
    const structMatch = line.match(RE_STRUCTURED_LOG);
    if (structMatch) {
      const levelRaw = structMatch[1]!.toLowerCase();
      const level: LogLevel = levelRaw === "warn" ? "warning" : levelRaw as LogLevel;
      entries.push({
        level,
        message: structMatch[2]!.trim(),
        timestamp,
        raw: line,
        category: "print",
      });
      lastEntry = entries[entries.length - 1]!;
      continue;
    }

    // 遍历匹配器链
    for (const matcher of MATCHERS) {
      const match = matcher.pattern.exec(line);
      if (match) {
        const message = match[matcher.messageIndex ?? 1]?.trim() ?? line.trim();
        entries.push({
          level: matcher.level,
          message,
          timestamp,
          raw: line,
          category: matcher.category,
        });
        lastEntry = entries[entries.length - 1]!;
        matched = true;
        break;
      }
    }

    if (matched) continue;

    // 检查 traceback 行——关联到上一个 error 条目
    if (isTracebackLine(line) && lastEntry && lastEntry.level === "error") {
      const tb = extractTraceback(line);
      if (tb) {
        if (!lastEntry.file) {
          lastEntry.file = tb.file;
          lastEntry.line = tb.line;
        }
        // traceback 也作为独立 debug 条目
        entries.push({
          level: "debug",
          message: `traceback: ${tb.file}:${tb.line}`,
          file: tb.file,
          line: tb.line,
          timestamp,
          raw: line,
          category: "system",
        });
      }
      continue;
    }

    // 检查是否包含 "ERROR" 关键词（兜底）
    const trimmed = line.trim();
    if (/error/i.test(trimmed) && !trimmed.startsWith("LOG:")) {
      entries.push({
        level: "error",
        message: trimmed.length > 200 ? trimmed.slice(0, 200) + "..." : trimmed,
        timestamp,
        raw: line,
        category: "engine",
      });
      lastEntry = entries[entries.length - 1]!;
      continue;
    }

    // print 输出（兜底）
    if (source === "stdout") {
      entries.push({
        level: "info",
        message: trimmed.length > 200 ? trimmed.slice(0, 200) + "..." : trimmed,
        timestamp,
        raw: line,
        category: "print",
      });
      lastEntry = entries[entries.length - 1]!;
    }
  }

  return { entries };
}

// ─── 摘要生成 ───

/**
 * SummarizeLogs — 生成日志摘要报告（LLM 友好的结构化格式）
 */
export function SummarizeLogs(
  input: SummarizeLogsInput,
): SummarizeLogsOutput {
  const { entries, include_raw = false } = input;

  // 统计
  const stats = {
    total: entries.length,
    errors: 0,
    warnings: 0,
    infos: 0,
    debug: 0,
  };

  for (const entry of entries) {
    if (entry.level === "error") stats.errors++;
    else if (entry.level === "warning") stats.warnings++;
    else if (entry.level === "info") stats.infos++;
    else if (entry.level === "debug") stats.debug++;
  }

  // 按文件+行号聚合 error
  const errorMap = new Map<string, { file: string; line: number; count: number; example: string }>();
  for (const entry of entries) {
    if (entry.level === "error" && entry.file) {
      const key = `${entry.file}:${entry.line ?? 0}`;
      const existing = errorMap.get(key);
      if (existing) {
        existing.count++;
      } else {
        errorMap.set(key, {
          file: entry.file,
          line: entry.line ?? 0,
          count: 1,
          example: entry.message,
        });
      }
    }
  }

  // 按频率排序取前 10
  const topErrors = [...errorMap.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  // 时间线（采样关键事件：error 和 warning）
  const timeline: Array<{ ms: number; event: string }> = [];
  for (const entry of entries) {
    if (entry.level === "error" || entry.level === "warning") {
      timeline.push({
        ms: entry.timestamp,
        event: `[${entry.level.toUpperCase()}] ${entry.message}`,
      });
    }
  }
  // 限制时间线条目数
  const sampledTimeline = timeline.length > 50
    ? timeline.filter((_, i) => i % Math.ceil(timeline.length / 50) === 0)
    : timeline;

  // 诊断提示
  const diagnosisHints: string[] = [];
  if (stats.errors > 0) {
    diagnosisHints.push(`检测到 ${stats.errors} 个错误`);
    if (topErrors.length > 0) {
      diagnosisHints.push(`最频繁的错误位于 ${topErrors[0]!.file}:${topErrors[0]!.line}（${topErrors[0]!.count} 次）`);
    }
  }
  if (stats.warnings > 10) {
    diagnosisHints.push(`警告数量较多（${stats.warnings} 条），建议检查代码质量`);
  }
  if (stats.total === 0) {
    diagnosisHints.push("未捕获到任何日志输出——游戏可能未成功启动或全部输出被静默");
  }

  return {
    summary: {
      stats,
      top_errors: topErrors,
      timeline: sampledTimeline,
      diagnosis_hints: diagnosisHints,
    },
  };
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/log_parser.ts <command>");
    console.error("命令:");
    console.error("  parse <file_path> [--source stdout|stderr]");
    console.error("  parse-text <text> [--source stdout|stderr]");
    console.error("  summarize <file_path>");
    process.exit(1);
  }

  const cmd = args[0];

  if (cmd === "parse" && args[1]) {
    const sourceIdx = args.indexOf("--source");
    const source = sourceIdx >= 0 && args[sourceIdx + 1] === "stderr" ? "stderr" as const : "stdout" as const;

    const text = await readFile(args[1], "utf-8");
    const result = ParseLogText({ raw_text: text, source });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log(JSON.stringify(result.entries, null, 2));
  } else if (cmd === "parse-text" && args[1]) {
    const sourceIdx = args.indexOf("--source");
    const source = sourceIdx >= 0 && args[sourceIdx + 1] === "stderr" ? "stderr" as const : "stdout" as const;
    const result = ParseLogText({ raw_text: args[1], source });
    console.log(JSON.stringify(result.entries, null, 2));
  } else if (cmd === "summarize" && args[1]) {
    const text = await readFile(args[1], "utf-8");
    const parseResult = ParseLogText({ raw_text: text, source: "stdout" });
    const result = SummarizeLogs({ entries: parseResult.entries });
    console.log(JSON.stringify(result.summary, null, 2));
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("log_parser.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
