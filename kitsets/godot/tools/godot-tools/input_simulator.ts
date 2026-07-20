/**
 * M9 · Input Simulator
 *
 * 通过操作系统级 API 向运行中的 Godot 游戏窗口模拟键盘输入。
 * 支持三平台：
 *   - Windows: PowerShell SendKeys
 *   - Linux:   xdotool
 *   - macOS:   osascript (System Events)
 *
 * 支持三种按键原语：press / release / tap。
 * 支持按键序列保存为 JSON 脚本和重放。
 *
 * @module tools/input_simulator
 */

import { spawn } from "node:child_process";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { join } from "node:path";
import { existsSync } from "node:fs";

// ─── 类型定义 ───

export type InputActionType = "press" | "release" | "tap";

export interface InputAction {
  /** 动作类型 */
  action: InputActionType;
  /** 按键名（如 "Space", "W", "A", "Up", "Enter"） */
  key: string;
  /** 执行前等待毫秒（相对上一动作） */
  delay_ms: number;
}

export interface InputScript {
  name: string;
  created: string;
  sequence: InputAction[];
}

export interface SimulateKeySequenceInput {
  /** 按键序列 */
  keys: InputAction[];
  /** 目标窗口标题（用于查找窗口，不传则发送到当前活动窗口） */
  window_title?: string;
  /** 如果指定，先启动 godot 项目再模拟（需要 M6 RunGodot 支持后台运行） */
  godot_project?: string;
}

export interface SimulateKeySequenceOutput {
  /** 成功执行的动作数 */
  executed_actions: number;
  error?: string;
}

export interface CreateInputScriptInput {
  /** 按键序列 */
  sequence: InputAction[];
  /** 脚本名称 */
  name: string;
}

export interface CreateInputScriptOutput {
  /** 脚本 ID（文件名不含扩展名） */
  script_id: string;
  error?: string;
}

export interface ReplayInputScriptInput {
  /** 脚本 ID */
  script_id: string;
  /** 可选，在指定项目中启动游戏再重放 */
  godot_project?: string;
}

export interface ReplayInputScriptOutput {
  executed_actions: number;
  error?: string;
}

// ─── 常量 ───

const SCRIPTS_DIR = "input-scripts";

/** 按键名归一化映射（Godot 常用按键名 → 平台 API 按键名） */
const KEY_MAP_WINDOWS: Record<string, string> = {
  "Space": " ",
  "Enter": "{ENTER}",
  "Tab": "{TAB}",
  "Escape": "{ESC}",
  "Backspace": "{BACKSPACE}",
  "Up": "{UP}",
  "Down": "{DOWN}",
  "Left": "{LEFT}",
  "Right": "{RIGHT}",
  "Shift": "+",
  "Control": "^",
  "Alt": "%",
  "W": "w",
  "A": "a",
  "S": "s",
  "D": "d",
  "Q": "q",
  "E": "e",
  "R": "r",
  "F": "f",
  "X": "x",
  "Y": "y",
  "Z": "z",
  "1": "1",
  "2": "2",
  "3": "3",
};

const KEY_MAP_LINUX: Record<string, string> = {
  "Space": "space",
  "Enter": "Return",
  "Tab": "Tab",
  "Escape": "Escape",
  "Backspace": "BackSpace",
  "Up": "Up",
  "Down": "Down",
  "Left": "Left",
  "Right": "Right",
  "Shift": "Shift_L",
  "Control": "Control_L",
  "Alt": "Alt_L",
  "W": "w",
  "A": "a",
  "S": "s",
  "D": "d",
  "Q": "q",
  "E": "e",
  "R": "r",
  "F": "f",
  "X": "x",
  "Y": "y",
  "Z": "z",
};

const KEY_MAP_MACOS: Record<string, string> = {
  "Space": "space",
  "Enter": "return",
  "Tab": "tab",
  "Escape": "escape",
  "Backspace": "delete",
  "Up": "up",
  "Down": "down",
  "Left": "left",
  "Right": "right",
  "Shift": "shift",
  "Control": "control",
  "Alt": "option",
  "W": "w",
  "A": "a",
  "S": "s",
  "D": "d",
};

// ─── 平台检测 ───

type Platform = "windows" | "linux" | "macos";

function detectPlatform(): Platform {
  const plat = process.platform;
  if (plat === "win32") return "windows";
  if (plat === "darwin") return "macos";
  return "linux";
}

// ─── 脚本存储路径 ───

function getScriptsDir(): string {
  return join(process.cwd(), SCRIPTS_DIR);
}

function getScriptPath(scriptId: string): string {
  return join(getScriptsDir(), `${scriptId}.json`);
}

// ─── 按键名归一化 ───

function mapKey(key: string, platform: Platform): string | null {
  const upper = key.charAt(0).toUpperCase() + key.slice(1);
  switch (platform) {
    case "windows":
      return KEY_MAP_WINDOWS[key] ?? KEY_MAP_WINDOWS[upper] ?? (key.length === 1 ? key.toLowerCase() : null);
    case "linux":
      return KEY_MAP_LINUX[key] ?? KEY_MAP_LINUX[upper] ?? (key.length === 1 ? key.toLowerCase() : null);
    case "macos":
      return KEY_MAP_MACOS[key] ?? KEY_MAP_MACOS[upper] ?? (key.length === 1 ? key.toLowerCase() : null);
  }
}

// ─── 平台执行器 ───

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Windows: 使用 PowerShell 调用 SendKeys
 */
async function executeWindows(
  actions: InputAction[],
  _windowTitle?: string,
): Promise<number> {
  // 构建 PowerShell 命令
  const sendKeysCalls: string[] = [];

  for (const act of actions) {
    const mappedKey = mapKey(act.key, "windows");
    if (!mappedKey) {
      console.warn(`[输入模拟] 未知按键: ${act.key}，跳过`);
      continue;
    }

    if (act.delay_ms > 0) {
      sendKeysCalls.push(`Start-Sleep -Milliseconds ${act.delay_ms}`);
    }

    if (act.action === "tap") {
      // SendKeys 直接用字符串表示按键
      const keyStr = mappedKey.length === 1 ? mappedKey : `'${mappedKey}'`;
      sendKeysCalls.push(`[System.Windows.Forms.SendKeys]::SendWait(${keyStr})`);
    } else if (act.action === "press") {
      // 纯按下——SendKeys 原生不支持独立按下，用 SendWait 等效于 tap
      const keyStr = mappedKey.length === 1 ? mappedKey : `'${mappedKey}'`;
      sendKeysCalls.push(`[System.Windows.Forms.SendKeys]::SendWait(${keyStr})`);
    }
    // release: SendKeys 不支持独立释放，忽略
  }

  if (sendKeysCalls.length === 0) return 0;

  const psScript = `
Add-Type -AssemblyName System.Windows.Forms
${sendKeysCalls.join("\n")}
`;

  return new Promise((resolve, reject) => {
    const child = spawn("powershell", [
      "-NoProfile",
      "-Command",
      psScript,
    ], {
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 30_000,
    });

    child.on("close", (code) => {
      resolve(actions.length);
    });

    child.on("error", (err) => {
      reject(new Error(`PowerShell 执行失败: ${err.message}`));
    });
  });
}

/**
 * Linux: 使用 xdotool
 */
async function executeLinux(
  actions: InputAction[],
  windowTitle?: string,
): Promise<number> {
  let executed = 0;

  for (const act of actions) {
    if (act.delay_ms > 0) {
      await sleep(act.delay_ms);
    }

    const mappedKey = mapKey(act.key, "linux");
    if (!mappedKey) {
      console.warn(`[输入模拟] 未知按键: ${act.key}，跳过`);
      continue;
    }

    // 尝试获取窗口
    let windowOpts = "";
    if (windowTitle) {
      windowOpts = `--window $(xdotool search --name "${windowTitle}" | tail -1)`;
    }

    try {
      if (act.action === "tap") {
        await runCommand("xdotool", [`key ${windowOpts} ${mappedKey}`]);
      } else if (act.action === "press") {
        await runCommand("xdotool", [`keydown ${windowOpts} ${mappedKey}`]);
      } else if (act.action === "release") {
        await runCommand("xdotool", [`keyup ${windowOpts} ${mappedKey}`]);
      }
      executed++;
    } catch {
      console.warn(`[输入模拟] 按键 ${act.key} 执行失败，跳过`);
    }
  }

  return executed;
}

/**
 * macOS: 使用 osascript (System Events)
 */
async function executeMacOS(
  actions: InputAction[],
  _windowTitle?: string,
): Promise<number> {
  let executed = 0;

  for (const act of actions) {
    if (act.delay_ms > 0) {
      await sleep(act.delay_ms);
    }

    const mappedKey = mapKey(act.key, "macos");
    if (!mappedKey) {
      console.warn(`[输入模拟] 未知按键: ${act.key}，跳过`);
      continue;
    }

    try {
      if (act.action === "tap") {
        const script = `
tell application "System Events"
  key code ${keyCodeMacOS(act.key)}
end tell`;
        await runCommand("osascript", ["-e", script]);
      } else if (act.action === "press") {
        const script = `
tell application "System Events"
  key down ${keyCodeMacOS(act.key)}
end tell`;
        await runCommand("osascript", ["-e", script]);
      } else if (act.action === "release") {
        const script = `
tell application "System Events"
  key up ${keyCodeMacOS(act.key)}
end tell`;
        await runCommand("osascript", ["-e", script]);
      }
      executed++;
    } catch {
      console.warn(`[输入模拟] 按键 ${act.key} 执行失败，跳过`);
    }
  }

  return executed;
}

/**
 * macOS 按键码映射（简化版——常用键）
 */
function keyCodeMacOS(key: string): number {
  const map: Record<string, number> = {
    "A": 0, "S": 1, "D": 2, "F": 3, "H": 4, "G": 5, "Z": 6, "X": 7,
    "C": 8, "V": 9, "B": 11, "Q": 12, "W": 13, "E": 14, "R": 15,
    "Y": 16, "T": 17, "1": 18, "2": 19, "3": 20, "4": 21, "5": 22,
    "6": 23, "7": 24, "8": 25, "9": 26, "0": 27,
    "Space": 49, "Up": 126, "Down": 125, "Left": 123, "Right": 124,
    "Enter": 36, "Tab": 48, "Escape": 53, "Backspace": 51,
  };
  return map[key.toUpperCase()] ?? map[key] ?? 0;
}

/**
 * 运行外部命令的辅助函数
 */
function runCommand(cmd: string, args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 10_000,
    });

    let stdout = "";
    let stderr = "";

    child.stdout?.on("data", (data: Buffer) => {
      stdout += data.toString();
    });

    child.stderr?.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    child.on("close", (code) => {
      if (code === 0) resolve(stdout.trim());
      else reject(new Error(stderr.trim() || `退出码 ${code}`));
    });

    child.on("error", (err) => {
      reject(err);
    });
  });
}

// ─── 主接口 ───

/**
 * SimulateKeySequence — 模拟按键序列
 *
 * 自动检测平台并选择对应的输入模拟方式。
 * 支持按键间延迟、窗口定位。
 */
export async function SimulateKeySequence(
  input: SimulateKeySequenceInput,
): Promise<SimulateKeySequenceOutput> {
  if (!input.keys || input.keys.length === 0) {
    return { executed_actions: 0, error: "按键序列为空" };
  }

  const platform = detectPlatform();

  try {
    let executed = 0;

    switch (platform) {
      case "windows":
        executed = await executeWindows(input.keys, input.window_title);
        break;
      case "linux":
        executed = await executeLinux(input.keys, input.window_title);
        break;
      case "macos":
        executed = await executeMacOS(input.keys, input.window_title);
        break;
    }

    return { executed_actions: executed };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      executed_actions: 0,
      error: `输入模拟失败: ${message}`,
    };
  }
}

/**
 * CreateInputScript — 创建可复用的输入脚本
 *
 * 将按键序列保存为 JSON 文件，存储在 input-scripts/ 目录。
 */
export async function CreateInputScript(
  input: CreateInputScriptInput,
): Promise<CreateInputScriptOutput> {
  if (!input.name || input.name.trim().length === 0) {
    return { script_id: "", error: "脚本名称不能为空" };
  }

  if (!input.sequence || input.sequence.length === 0) {
    return { script_id: "", error: "按键序列不能为空" };
  }

  const script: InputScript = {
    name: input.name.trim(),
    created: new Date().toISOString(),
    sequence: input.sequence,
  };

  const scriptsDir = getScriptsDir();

  try {
    await mkdir(scriptsDir, { recursive: true });
    const scriptPath = getScriptPath(script.name);
    await writeFile(scriptPath, JSON.stringify(script, null, 2), "utf-8");
    return { script_id: script.name };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return { script_id: "", error: `保存脚本失败: ${message}` };
  }
}

/**
 * ReplayInputScript — 重放已保存的输入脚本
 */
export async function ReplayInputScript(
  input: ReplayInputScriptInput,
): Promise<ReplayInputScriptOutput> {
  const scriptPath = getScriptPath(input.script_id);

  try {
    const content = await readFile(scriptPath, "utf-8");
    const script: InputScript = JSON.parse(content);

    if (!script.sequence || script.sequence.length === 0) {
      return { executed_actions: 0, error: "脚本中无按键序列" };
    }

    const result = await SimulateKeySequence({
      keys: script.sequence,
      godot_project: input.godot_project,
    });

    return result;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      executed_actions: 0,
      error: `重放脚本失败: ${message}`,
    };
  }
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/input_simulator.ts <command> ...");
    console.error("命令:");
    console.error("  send <key> [--window <title>]");
    console.error("  sequence <json> [--window <title>]");
    console.error('    json 示例: \'[{"action":"tap","key":"Space","delay_ms":100}]\'');
    console.error("  create-script <name> <json>");
    console.error("  replay <script_id>");
    console.error("  list-scripts");
    process.exit(1);
  }

  const cmd = args[0];

  if (cmd === "send" && args[1]) {
    const windowIdx = args.indexOf("--window");
    const windowTitle = windowIdx >= 0 ? args[windowIdx + 1] : undefined;
    const result = await SimulateKeySequence({
      keys: [{ action: "tap", key: args[1]!, delay_ms: 0 }],
      window_title: windowTitle,
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log(`✅ 按键 ${args[1]} 已发送`);
  } else if (cmd === "sequence" && args[1]) {
    const windowIdx = args.indexOf("--window");
    const windowTitle = windowIdx >= 0 ? args[windowIdx + 1] : undefined;
    const sequence = JSON.parse(args[1]) as InputAction[];
    const result = await SimulateKeySequence({
      keys: sequence,
      window_title: windowTitle,
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log(`✅ 已执行 ${result.executed_actions} 个按键动作`);
  } else if (cmd === "create-script" && args[1] && args[2]) {
    const sequence = JSON.parse(args[2]) as InputAction[];
    const result = await CreateInputScript({ name: args[1]!, sequence });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log(`✅ 脚本已创建: ${result.script_id}`);
  } else if (cmd === "replay" && args[1]) {
    const result = await ReplayInputScript({ script_id: args[1]! });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log(`✅ 已重放 ${result.executed_actions} 个按键动作`);
  } else if (cmd === "list-scripts") {
    try {
      const files = await readdir(getScriptsDir());
      const scripts = files.filter((f) => f.endsWith(".json"));
      if (scripts.length === 0) {
        console.log("ℹ️  没有已保存的输入脚本");
      } else {
        console.log("📋 已保存的输入脚本:");
        for (const s of scripts) {
          console.log(`   - ${s.replace(/\.json$/, "")}`);
        }
      }
    } catch {
      console.log("ℹ️  没有已保存的输入脚本");
    }
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("input_simulator.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
