/**
 * M6 · Godot CLI Bridge
 *
 * 封装 godot 可执行文件的所有 CLI 操作。
 * 职责单一：进程管理（参数构造、超时/kill、退出码解析）。
 *
 * @module tools/godot_cli
 */

import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import { join } from "node:path";
import { existsSync } from "node:fs";

// ─── 类型定义 ───

export interface RunGodotInput {
  /** Godot 项目根目录 */
  project_root: string;
  /** CLI 参数列表（不含 --path，会自动添加） */
  args: string[];
  /** 超时秒数，默认 60 */
  timeout_sec?: number;
  /** Godot 可执行文件路径（不传则自动查找 PATH） */
  godot_path?: string;
}

export interface RunGodotOutput {
  stdout: string;
  stderr: string;
  exit_code: number;
  error?: string;
}

export interface CheckGodotVersionInput {
  /** Godot 可执行文件路径（不传则自动查找 PATH） */
  godot_path?: string;
}

export interface CheckGodotVersionOutput {
  /** 完整版本号如 "4.3" */
  version: string;
  /** 是否兼容（≥ 4.0） */
  compatible: boolean;
  error?: string;
}

// ─── 常量 ───

const MINIMUM_MAJOR = 4;
const DEFAULT_TIMEOUT_SEC = 60;

// ─── 查找 godot 可执行文件 ───

/**
 * 在 PATH 中查找 godot 可执行文件。
 * Windows 下会尝试 godot.exe / godot_console.exe。
 */
function findGodotInPath(specified?: string): string | null {
  if (specified) {
    // 指定的路径必须存在
    if (existsSync(specified)) return specified;
    return null;
  }

  const isWindows = process.platform === "win32";
  const candidates = isWindows
    ? ["godot.exe", "godot_console.exe", "godot"]
    : ["godot"];

  // 检查 PATH
  const pathDirs = (process.env.PATH || "").split(
    isWindows ? ";" : ":",
  );

  for (const dir of pathDirs) {
    for (const name of candidates) {
      const fullPath = join(dir, name);
      if (existsSync(fullPath)) {
        return fullPath;
      }
    }
  }

  // 检查常见安装位置
  const commonPaths = isWindows
    ? [
        "C:\\Program Files\\Godot\\godot.exe",
        "C:\\Program Files (x86)\\Godot\\godot.exe",
        join(process.env.HOME || "", "AppData\\Local\\Godot\\godot.exe"),
      ]
    : [
        "/usr/bin/godot",
        "/usr/local/bin/godot",
        "/opt/godot/godot",
        join(process.env.HOME || "", "godot"),
      ];

  for (const p of commonPaths) {
    if (existsSync(p)) return p;
  }

  return null;
}

// ─── 版本解析 ───

/**
 * 从 godot --version 输出解析版本号
 * Godot 输出格式: "4.3.stable" 或 "4.2.1.stable"
 */
function parseGodotVersion(raw: string): { major: number; minor: number; full: string } | null {
  // 匹配 "X.Y" 或 "X.Y.Z"
  const match = raw.match(/(\d+)\.(\d+)(?:\.(\d+))?/);
  if (!match) return null;

  return {
    major: parseInt(match[1]),
    minor: parseInt(match[2]),
    full: match[0],
  };
}

// ─── 进程执行 ───

function runProcess(
  cmd: string,
  args: string[],
  cwd: string,
  timeoutSec: number,
): Promise<RunGodotOutput> {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
      timeout: timeoutSec * 1000,
    });

    let stdout = "";
    let stderr = "";

    child.stdout?.on("data", (data: Buffer) => {
      stdout += data.toString("utf-8");
    });

    child.stderr?.on("data", (data: Buffer) => {
      stderr += data.toString("utf-8");
    });

    let killed = false;
    const timer = setTimeout(() => {
      killed = true;
      child.kill("SIGTERM");
      // 如果 SIGTERM 后 2 秒未退出则 SIGKILL
      setTimeout(() => {
        try { child.kill("SIGKILL"); } catch { /* 进程已结束 */ }
      }, 2000);
    }, timeoutSec * 1000);

    child.on("close", (code) => {
      clearTimeout(timer);
      if (killed) {
        resolve({
          stdout,
          stderr: stderr + "\n[godot_cli] 进程超时，已杀死",
          exit_code: -1,
          error: `进程执行超时（${timeoutSec}秒）`,
        });
      } else {
        resolve({
          stdout,
          stderr,
          exit_code: code ?? -1,
        });
      }
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({
        stdout,
        stderr,
        exit_code: -1,
        error: `启动进程失败: ${err.message}`,
      });
    });
  });
}

// ─── 主接口 ───

/**
 * RunGodot — 运行 godot 命令
 *
 * 自动添加 --path <project_root> 参数。
 * 带超时控制，防止 godot 进程卡死。
 */
export async function RunGodot(
  input: RunGodotInput,
): Promise<RunGodotOutput> {
  if (!input.project_root) {
    return { stdout: "", stderr: "", exit_code: -1, error: "project_root 不能为空" };
  }

  const godotPath = findGodotInPath(input.godot_path);
  if (!godotPath) {
    return {
      stdout: "",
      stderr: "",
      exit_code: -1,
      error:
        "未找到 Godot 可执行文件。请确保 godot 已安装并在 PATH 中，" +
        "或通过 godot_path 参数指定路径。安装指引: https://godotengine.org/download",
    };
  }

  const timeout = input.timeout_sec ?? DEFAULT_TIMEOUT_SEC;

  // 构建参数: --path <project_root> 放在最前
  const allArgs = ["--path", input.project_root, ...input.args];

  return runProcess(godotPath, allArgs, input.project_root, timeout);
}

/**
 * CheckGodotVersion — 检测安装的 Godot 版本是否兼容
 */
export async function CheckGodotVersion(
  input: CheckGodotVersionInput = {},
): Promise<CheckGodotVersionOutput> {
  const godotPath = findGodotInPath(input.godot_path);
  if (!godotPath) {
    return {
      version: "",
      compatible: false,
      error:
        "未找到 Godot 可执行文件。请确保 godot 已安装并在 PATH 中。" +
        "安装指引: https://godotengine.org/download",
    };
  }

  const result = await runProcess(godotPath, ["--version"], process.cwd(), 10);
  if (result.error || result.exit_code !== 0) {
    return {
      version: "",
      compatible: false,
      error: `执行 godot --version 失败: ${result.stderr || result.error}`,
    };
  }

  const parsed = parseGodotVersion(result.stdout.trim());
  if (!parsed) {
    return {
      version: result.stdout.trim(),
      compatible: false,
      error: `无法解析版本号: "${result.stdout.trim()}"`,
    };
  }

  const compatible = parsed.major >= MINIMUM_MAJOR;

  return {
    version: parsed.full,
    compatible,
    error: compatible ? undefined : `Godot ${parsed.full} 不兼容，需要 Godot ${MINIMUM_MAJOR}.x 或更高版本`,
  };
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/godot_cli.ts <command> ...");
    console.error("命令: check-version");
    console.error("       run <project_root> <args...>");
    process.exit(1);
  }

  const cmd = args[0];
  if (cmd === "check-version") {
    const result = await CheckGodotVersion();
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log(`✅ Godot 版本: ${result.version} (兼容: ${result.compatible})`);
  } else if (cmd === "run" && args.length >= 2) {
    const projectRoot = args[1];
    const cliArgs = args.slice(2);
    const result = await RunGodot({
      project_root: projectRoot,
      args: cliArgs,
    });
    if (result.stdout) console.log(result.stdout);
    if (result.stderr) console.error(result.stderr);
    process.exit(result.exit_code);
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("godot_cli.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
