/**
 * G5 · Agent-Side Bridge — Godox Plugin 桥接层
 *
 * 检测 Godot 项目是否安装了 godox-plugin，并调用其 MCP/UDP/TCP 接口。
 * 如果插件不可用，自动降级到文件操作模式。
 *
 * @module tools/godox_bridge
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";
import { createConnection } from "node:net";
import { createSocket } from "node:dgram";

// ─── 类型 ───

export interface DetectPluginInput {
  project_root: string;
}

export interface DetectPluginOutput {
  installed: boolean;
  version?: string;
  editor_running: boolean;
  channels?: {
    mcp_stdio: boolean;
    input_udp: boolean;
    log_tcp: boolean;
  };
}

export interface CallMcpInput {
  method: string;
  params?: Record<string, unknown>;
  timeout_sec?: number;
  godot_path?: string;
}

export interface CallMcpOutput {
  result?: unknown;
  error?: string;
}

export interface SendInputInput {
  key: string;
  event?: "key_press" | "key_down" | "key_up";
  godot_project?: string;
}

export interface SendInputOutput {
  status: string;
  error?: string;
}

// ─── 常量 ───

const PLUGIN_CFG = join("addons", "godox", "plugin.cfg");
const INPUT_UDP_PORT = 42069;
const LOG_TCP_PORT = 42070;

// ─── G5-A1: 检测插件 ───

/**
 * detect_plugin — 检测 Godot 项目是否安装了 godox-plugin
 *
 * 检查：
 *   1. addons/godox/plugin.cfg 是否存在
 *   2. 编辑器的 UDP/TCP 端口是否响应（判断编辑器是否在运行）
 */
export async function detectPlugin(
  input: DetectPluginInput,
): Promise<DetectPluginOutput> {
  const { project_root } = input;

  // 检查 plugin.cfg
  const pluginCfgPath = join(project_root, PLUGIN_CFG);
  const installed = existsSync(pluginCfgPath);

  let version: string | undefined;
  if (installed) {
    try {
      const cfg = readFileSync(pluginCfgPath, "utf-8");
      const vMatch = cfg.match(/^version\s*=\s*"(.+)"$/m);
      if (vMatch) version = vMatch[1];
    } catch { /* 版本读取失败不影响主流程 */ }
  }

  // 检查编辑器是否运行（通过尝试连接端口）
  const channels = {
    mcp_stdio: false,
    input_udp: false,
    log_tcp: false,
  };

  // 检查 UDP 端口
  channels.input_udp = await checkPort(INPUT_UDP_PORT, "udp");

  // 检查 TCP 端口
  channels.log_tcp = await checkPort(LOG_TCP_PORT, "tcp");

  const editor_running = channels.input_udp || channels.log_tcp;

  return {
    installed,
    version,
    editor_running,
    channels,
  };
}

// ─── G5-A3: 调用 MCP ───

/**
 * callMCP — 通过 godot --editor 的 stdin 发送 MCP JSON-RPC 调用
 *
 * 启动 godot 编辑器（如果未运行），发送 JSON-RPC 请求到 stdin，
 * 从 stdout 读取响应。超时兜底。
 */
export async function callMCP(
  input: CallMcpInput,
): Promise<CallMcpOutput> {
  const { method, params = {}, timeout_sec = 10, godot_path } = input;

  const request = {
    jsonrpc: "2.0",
    id: 1,
    method,
    params,
  };

  const requestStr = JSON.stringify(request) + "\n";

  try {
    const result = await sendStdioCommand(
      godot_path || "godot",
      ["--editor", "--headless"],
      requestStr,
      timeout_sec,
    );
    return { result };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    // 编辑器未运行或 MCP 不可用 → 降级
    return { error: `MCP 调用失败（已降级到文件模式）: ${message}` };
  }
}

// ─── 辅助：发送输入事件 ───

/**
 * sendInput — 通过 UDP 向运行中的游戏发送按键事件
 *
 * 需要 godox-plugin 的 Input Relay (G2) 在监听。
 */
export async function sendInput(
  input: SendInputInput,
): Promise<SendInputOutput> {
  const { key, event = "key_press", godot_project } = input;

  // 如果指定了项目，先检测插件是否在运行
  if (godot_project) {
    const status = await detectPlugin({ project_root: godot_project });
    if (!status.editor_running) {
      return {
        status: "error",
        error: "编辑器未运行，无法发送输入。请先启动 Godot 编辑器并运行游戏。",
      };
    }
  }

  const payload = JSON.stringify({ event, key });

  return new Promise((resolve) => {
    const client = createSocket("udp4");
    const timeout = setTimeout(() => {
      client.close();
      resolve({ status: "error", error: "UDP 发送超时" });
    }, 2000);

    client.on("message", (msg) => {
      clearTimeout(timeout);
      client.close();
      try {
        const resp = JSON.parse(msg.toString());
        resolve(resp);
      } catch {
        resolve({ status: "ok" });
      }
    });

    client.on("error", (err) => {
      clearTimeout(timeout);
      client.close();
      resolve({ status: "error", error: err.message });
    });

    client.send(payload, INPUT_UDP_PORT, "127.0.0.1", (err) => {
      if (err) {
        clearTimeout(timeout);
        client.close();
        resolve({ status: "error", error: err.message });
      }
    });
  });
}

// ─── 辅助函数 ───

/**
 * 检查指定端口是否可连接
 */
function checkPort(port: number, type: "tcp" | "udp"): Promise<boolean> {
  return new Promise((resolve) => {
    if (type === "tcp") {
      const socket = createConnection({ host: "127.0.0.1", port, timeout: 500 }, () => {
        socket.end();
        resolve(true);
      });
      socket.on("error", () => resolve(false));
      socket.setTimeout(500, () => { socket.destroy(); resolve(false); });
    } else {
      const socket = createSocket("udp4");
      socket.on("error", () => { socket.close(); resolve(false); });
      socket.on("message", () => { socket.close(); resolve(true); });

      // 发送空探测包
      socket.send(Buffer.from("ping"), port, "127.0.0.1", (err) => {
        if (err) { socket.close(); resolve(false); }
        setTimeout(() => { socket.close(); resolve(false); }, 500);
      });
    }
  });
}

/**
 * 发送 stdin 命令并读取 stdout 响应
 */
function sendStdioCommand(
  cmd: string,
  args: string[],
  input: string,
  timeoutSec: number,
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: ["pipe", "pipe", "pipe"],
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

    // 发送请求后关闭 stdin
    child.stdin?.write(input);
    child.stdin?.end();

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`进程超时 (${timeoutSec}s): ${stderr.slice(0, 200)}`));
    }, timeoutSec * 1000);

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0 && !stdout) {
        reject(new Error(`进程退出码 ${code}: ${stderr.slice(0, 200)}`));
        return;
      }
      try {
        const parsed = JSON.parse(stdout.trim());
        resolve(parsed);
      } catch {
        // 如果 stdout 不是 JSON，可能包含调试信息，尝试逐行解析
        const lines = stdout.trim().split("\n");
        for (const line of lines) {
          try {
            const parsed = JSON.parse(line.trim());
            resolve(parsed);
            return;
          } catch { /* 跳过非 JSON 行 */ }
        }
        reject(new Error(`无法解析 MCP 响应: ${stdout.slice(0, 200)}`));
      }
    });

    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });
}
