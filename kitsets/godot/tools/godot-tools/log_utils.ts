/**
 * M11 · GDScript Log Utilities
 *
 * 提供结构化日志的 GDScript 模板和约定，供游戏脚本引用。
 * 生成 log_utils.gd 模板（log_info / log_warn / log_error），
 * 统一输出格式 "LOG:[LEVEL]:[message]" 方便 M8 精准解析。
 * 同时提供 InjectLogStatements 工具，在现有 .gd 文件中插入日志。
 *
 * @module tools/log_utils
 */

import { readFile, writeFile, access } from "node:fs/promises";
import { join, dirname } from "node:path";

// ─── 类型定义 ───

export interface GenerateLogScriptInput {
  /** 写入目标路径（可选，不传则只返回文本） */
  project_root?: string;
  /** 日志详细级别 */
  log_level?: "verbose" | "normal" | "minimal";
}

export interface GenerateLogScriptOutput {
  /** 生成的脚本源码 */
  script_content: string;
  /** 如果指定了 project_root，返回写入路径 */
  script_path?: string;
  error?: string;
}

export interface InjectPoint {
  /** 目标函数名 */
  function: string;
  /** 日志消息 */
  message: string;
  /** 日志级别 */
  level: "info" | "warn" | "error" | "debug";
}

export interface InjectLogStatementsInput {
  /** .gd 文件路径 */
  file_path: string;
  /** 注入点列表 */
  inject_points: InjectPoint[];
}

export interface InjectLogStatementsOutput {
  /** 是否实际修改了文件 */
  modified: boolean;
  error?: string;
}

// ─── 日志级别前缀 ───

const LEVEL_PREFIX: Record<string, string> = {
  error: "ERROR",
  warn: "WARN",
  info: "INFO",
  debug: "DEBUG",
};

// ─── log_utils.gd 模板 ───

function generateLogUtilsScript(level: "verbose" | "normal" | "minimal"): string {
  const hasVerbose = level === "verbose";
  const hasMinimal = level === "minimal";

  return `# log_utils.gd
# Godot Reasonix 结构化日志工具 — 自动生成
# 输出格式: LOG:[LEVEL]:[message]  — M8 日志解析器可直接解析
#
# 用法:
#   var log = preload("res://scripts/log_utils.gd")
#   log.log_info("玩家进入场景")
#   log.log_error("碰撞检测失败", "player.gd", 42)

static func _format_message(level: String, message: String, source_file: String = "", source_line: int = -1) -> String:
	var result := "LOG:" + level + ":" + message
	if source_file.length() > 0:
		result += " at " + source_file
		if source_line > 0:
			result += ":" + String.num(source_line)
	return result

# 输出 INFO 级别日志
static func log_info(message: String, source_file: String = "", source_line: int = -1) -> void:
	print(_format_message("INFO", message, source_file, source_line))
${hasVerbose ? `
# 输出 DEBUG 级别日志（仅在 verbose 模式下启用）
static func log_debug(message: String, source_file: String = "", source_line: int = -1) -> void:
	print(_format_message("DEBUG", message, source_file, source_line))
` : ""}
# 输出 WARN 级别日志
static func log_warn(message: String, source_file: String = "", source_line: int = -1) -> void:
	print(_format_message("WARN", message, source_file, source_line))
	push_warning(message)
${!hasMinimal ? `
# 输出 ERROR 级别日志 + 错误栈
static func log_error(message: String, source_file: String = "", source_line: int = -1) -> void:
	print(_format_message("ERROR", message, source_file, source_line))
	push_error(message)
` : `
# 输出 ERROR 级别日志
static func log_error(message: String, source_file: String = "", source_line: int = -1) -> void:
	print(_format_message("ERROR", message, source_file, source_line))
`}
# 断言条件，失败时记录 ERROR 并返回 false
static func log_assert(condition: bool, message: String, source_file: String = "", source_line: int = -1) -> bool:
	if not condition:
		log_error("ASSERT_FAILED: " + message, source_file, source_line)
	return condition
`;
}

// ─── 主接口 ───

/**
 * GenerateLogScript — 生成 log_utils.gd 脚本内容
 *
 * 如果指定 project_root，写入 scripts/log_utils.gd。
 * 支持三级日志详细度：verbose（含 debug）/ normal（标准）/ minimal（精简）。
 */
export async function GenerateLogScript(
  input: GenerateLogScriptInput,
): Promise<GenerateLogScriptOutput> {
  const level = input.log_level ?? "normal";

  if (!["verbose", "normal", "minimal"].includes(level)) {
    return {
      script_content: "",
      error: `无效日志级别: "${level}"，可选值: verbose / normal / minimal`,
    };
  }

  const scriptContent = generateLogUtilsScript(level);

  if (input.project_root) {
    const targetDir = join(input.project_root, "scripts");
    const targetPath = join(targetDir, "log_utils.gd");

    try {
      // 确保目录存在（简单检查，失败由 writeFile 抛出可读错误）
      await access(targetDir).catch(() => {
        // 目录不存在，不做自动创建——应由 ScaffoldProject 保证 scripts/ 存在
        throw new Error(`目标目录不存在: ${targetDir}，请先用 ScaffoldProject 创建项目`);
      });

      await writeFile(targetPath, scriptContent, "utf-8");
      return {
        script_content: scriptContent,
        script_path: targetPath,
      };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        script_content: scriptContent,
        error: `写入脚本失败: ${message}`,
      };
    }
  }

  return {
    script_content: scriptContent,
  };
}

// ─── .gd 文件行内注入 ───

/**
 * 在 GDScript 函数体内插入日志语句。
 * 使用行模式匹配：在目标函数的 body 起始后插入。
 */
function injectIntoFunctionBody(
  source: string,
  funcName: string,
  level: string,
  message: string,
): string {
  const prefix = LEVEL_PREFIX[level] ?? "INFO";

  // 匹配 func <name>(...): 行，在下一行插入日志语句
  // 支持 func _ready(): 和 func _ready() -> void: 等变体
  const funcRegex = new RegExp(
    `^[ \\t]*func[ \\t]+${escapeRegex(funcName)}\\s*\\([^)]*\\)\\s*(->\\s*\\w+)?\\s*:\\s*$`,
    "m",
  );

  const match = source.match(funcRegex);
  if (!match) {
    return source; // 函数未找到，不做修改
  }

  const matchIndex = match.index!;
  const matchEnd = matchIndex + match[0].length;

  // 在函数声明行后插入日志语句（函数体第一行）
  const logLine = `\tprint("LOG:${prefix}:${escapeGDScriptString(message)}")\n`;

  return source.slice(0, matchEnd) + "\n" + logLine + source.slice(matchEnd);
}

/**
 * 转义正则表达式中的特殊字符
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 转义 GDScript 字符串中的特殊字符
 */
function escapeGDScriptString(str: string): string {
  return str.replace(/"/g, '\\"').replace(/\n/g, "\\n");
}

/**
 * InjectLogStatements — 向现有 .gd 文件中注入日志语句
 *
 * 在指定函数的 body 起始位置插入 print("LOG:[LEVEL]:[message]") 调用。
 * 不会修改函数签名或其他已有代码。
 */
export async function InjectLogStatements(
  input: InjectLogStatementsInput,
): Promise<InjectLogStatementsOutput> {
  try {
    const content = await readFile(input.file_path, "utf-8");
    let modified = content;

    for (const point of input.inject_points) {
      const updated = injectIntoFunctionBody(
        modified,
        point.function,
        point.level,
        point.message,
      );
      if (updated !== modified) {
        modified = updated;
      }
    }

    if (modified === content) {
      return { modified: false };
    }

    await writeFile(input.file_path, modified, "utf-8");
    return { modified: true };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      modified: false,
      error: `注入日志失败: ${message}`,
    };
  }
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/log_utils.ts <command> ...");
    console.error("命令:");
    console.error("  generate [--project-root <path>] [--level verbose|normal|minimal]");
    console.error("  inject <file.gd> <func_name> <level> <message>");
    process.exit(1);
  }

  const cmd = args[0];

  if (cmd === "generate") {
    const projectRootIdx = args.indexOf("--project-root");
    const levelIdx = args.indexOf("--level");
    const input: GenerateLogScriptInput = {};

    if (projectRootIdx >= 0 && args[projectRootIdx + 1]) {
      input.project_root = args[projectRootIdx + 1];
    }
    if (levelIdx >= 0 && args[levelIdx + 1]) {
      input.log_level = args[levelIdx + 1] as GenerateLogScriptInput["log_level"];
    }

    const result = await GenerateLogScript(input);
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    if (result.script_path) {
      console.log(`✅ 已写入: ${result.script_path}`);
    } else {
      console.log(result.script_content);
    }
  } else if (cmd === "inject" && args.length >= 4) {
    const filePath = args[1];
    const funcName = args[2];
    const level = args[3] as InjectPoint["level"];
    const message = args[4] ?? `Enter ${funcName}`;

    const result = await InjectLogStatements({
      file_path: filePath,
      inject_points: [{ function: funcName, level, message }],
    });

    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    if (result.modified) {
      console.log(`✅ 已注入日志到: ${filePath} (函数: ${funcName})`);
    } else {
      console.log(`ℹ️  文件未修改（函数 "${funcName}" 未找到或已存在日志）`);
    }
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("log_utils.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
