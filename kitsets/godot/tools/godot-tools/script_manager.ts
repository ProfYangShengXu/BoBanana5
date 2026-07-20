/**
 * M3 · Script Manager
 *
 * 生成 .gd GDScript 文件并挂载到场景节点。
 * 职责单一：创建 GDScript 文件、管理场景节点 ↔ 脚本的绑定关系。
 *
 * @module tools/script_manager
 */

import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { ParseTscn, serializeTscn } from "./scene_generator.js";

// ─── 类型定义 ───

/** 函数定义 */
export interface FunctionDef {
  name: string;
  /** 函数体（不含花括号缩进，会自动加入） */
  body: string;
  /** 参数列表，如 "delta: float" */
  args?: string;
  return_type?: string;
  /** 是否为静态函数 */
  is_static?: boolean;
}

/** 信号定义 */
export interface SignalDef {
  name: string;
  /** 参数列表，如 [{name: "damage", type: "int"}] */
  args?: Array<{ name: string; type: string }>;
}

/** 脚本创建输入 */
export interface CreateScriptInput {
  /** 保存路径（如 scripts/player.gd） */
  path: string;
  /** 继承的节点类型（如 "CharacterBody2D"） */
  extends: string;
  /** 可选 @tool 标记 */
  is_tool?: boolean;
  /** 可选 class_name（全局注册） */
  class_name?: string;
  /** 信号定义 */
  signals?: SignalDef[];
  /** 函数定义 */
  functions?: FunctionDef[];
  /** 成员变量（@export 或 var） */
  variables?: Array<{
    name: string;
    type?: string;
    default?: string;
    export?: boolean;
    export_group?: string;
  }>;
  /** 自定义头部注释 */
  header_comment?: string;
}

/** 脚本挂载输入 */
export interface AttachScriptInput {
  /** .tscn 场景文件路径 */
  scene_path: string;
  /** 场景中目标节点的路径（节点名） */
  node_path: string;
  /** .gd 脚本路径（相对于项目根，如 "res://scripts/player.gd"） */
  script_path: string;
  /** 脚本在 ext_resource 中的类型 */
  script_type?: string;
}

/** 信号连接输入 */
export interface ConnectSignalInput {
  /** .tscn 场景文件路径 */
  scene_path: string;
  /** 发出信号的节点路径 */
  signal_node_path: string;
  /** 信号名 */
  signal_name: string;
  /** 接收信号的节点路径 */
  target_node_path: string;
  /** 处理方法名 */
  method_name: string;
  /** 连接 flags */
  flags?: number;
}

/** 通用输出 */
export interface ScriptOutput {
  script_path: string;
  error?: string;
}

// ─── GDScript 生成 ───

/**
 * 生成 .gd 文件内容
 */
export function RenderGdScript(input: CreateScriptInput): string {
  const lines: string[] = [];

  // @tool
  if (input.is_tool) {
    lines.push("@tool");
  }

  // extends
  lines.push(`extends ${input.extends}`);
  lines.push("");

  // 头部注释
  if (input.header_comment) {
    for (const line of input.header_comment.split("\n")) {
      lines.push(`# ${line}`);
    }
    lines.push("");
  }

  // class_name
  if (input.class_name) {
    lines.push(`class_name ${input.class_name}`);
    lines.push("");
  }

  // signals
  if (input.signals) {
    for (const sig of input.signals) {
      const args = sig.args
        ? "(" + sig.args.map((a) => `${a.name}: ${a.type}`).join(", ") + ")"
        : "";
      lines.push(`signal ${sig.name}${args}`);
    }
    if (input.signals.length > 0) lines.push("");
  }

  // variables
  if (input.variables) {
    for (const v of input.variables) {
      if (v.export) {
        if (v.export_group) {
          lines.push(`@export_category("${v.export_group}")`);
        }
        const typeHint = v.type ? `: ${v.type}` : "";
        const defaultVal = v.default !== undefined ? ` = ${v.default}` : "";
        lines.push(`@export var ${v.name}${typeHint}${defaultVal}`);
      } else {
        const typeHint = v.type ? `: ${v.type}` : "";
        const defaultVal = v.default !== undefined ? ` = ${v.default}` : "";
        lines.push(`var ${v.name}${typeHint}${defaultVal}`);
      }
    }
    if (input.variables.length > 0) lines.push("");
  }

  // functions
  if (input.functions) {
    for (const fn of input.functions) {
      const staticKw = fn.is_static ? "static " : "";
      const args = fn.args ? `(${fn.args})` : "()";
      const retType = fn.return_type ? ` -> ${fn.return_type}` : "";
      lines.push(`${staticKw}func ${fn.name}${args}${retType}:`);

      if (fn.body.trim()) {
        // 自动缩进函数体
        const indentedBody = fn.body
          .split("\n")
          .map((l) => (l.trim() ? `\t${l}` : l))
          .join("\n");
        lines.push(indentedBody);
      } else {
        lines.push("\tpass");
      }
      lines.push("");
    }
  }

  return lines.join("\n") + "\n";
}

// ─── 生成 ext_resource ID ───

function makeExtResourceId(path: string): string {
  // Godot 用 "1_" + 6 字符哈希
  let hash = 0;
  for (let i = 0; i < path.length; i++) {
    const char = path.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & 0xffffffff; // Convert to 32-bit int
  }
  const suffix = Math.abs(hash).toString(36).slice(0, 6).padStart(6, "0");
  return `1_${suffix}`;
}

// ─── 主接口 ───

/**
 * CreateScript — 创建 .gd 脚本文件
 */
export async function CreateScript(
  input: CreateScriptInput,
): Promise<ScriptOutput> {
  if (!input.path) {
    return { script_path: "", error: "path 不能为空" };
  }
  if (!input.extends?.trim()) {
    return { script_path: "", error: "extends 不能为空" };
  }

  const content = RenderGdScript(input);

  try {
    await writeFile(input.path, content, "utf-8");
    return { script_path: input.path };
  } catch (err) {
    return {
      script_path: "",
      error: `写入脚本文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * AttachScript — 将脚本挂载到场景节点
 *
 * 读取 .tscn 文件 → 找到目标节点 → 添加 script = ExtResource("id") 属性
 * → 添加 ext_resource 引用 → 写回文件。
 */
export async function AttachScript(
  input: AttachScriptInput,
): Promise<ScriptOutput> {
  if (!input.scene_path) {
    return { script_path: "", error: "scene_path 不能为空" };
  }
  if (!input.node_path) {
    return { script_path: "", error: "node_path 不能为空" };
  }
  if (!input.script_path) {
    return { script_path: "", error: "script_path 不能为空" };
  }

  let content: string;
  try {
    content = await readFile(input.scene_path, "utf-8");
  } catch (err) {
    return {
      script_path: "",
      error: `读取场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const doc = ParseTscn(content);

  // 找到目标节点
  const targetIdx = doc.nodes.findIndex((n) => n.name === input.node_path);
  if (targetIdx === -1) {
    return { script_path: "", error: `节点 "${input.node_path}" 不存在` };
  }

  // 生成 ext_resource id
  const extId = makeExtResourceId(input.script_path);

  // 检查是否已添加该资源
  const existingExt = doc.extResources.find(
    (e) => e.path === input.script_path,
  );
  if (!existingExt) {
    doc.extResources.push({
      id: extId,
      type: input.script_type || "Script",
      path: input.script_path,
    });
  }

  const usedId = existingExt ? existingExt.id : extId;

  // 设置 script 属性（替换已有或追加）
  const node = doc.nodes[targetIdx];
  const scriptPropIdx = node.properties.findIndex(
    ([k]) => k === "script",
  );
  const scriptVal = `ExtResource("${usedId}")`;
  if (scriptPropIdx >= 0) {
    node.properties[scriptPropIdx] = ["script", scriptVal];
  } else {
    node.properties.push(["script", scriptVal]);
  }

  // 更新 load_steps
  const newContent = serializeTscn(doc);

  try {
    await writeFile(input.scene_path, newContent, "utf-8");
    return { script_path: input.scene_path };
  } catch (err) {
    return {
      script_path: "",
      error: `写入场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * ConnectSignal — 在场景中建立信号连接
 *
 * 读取 .tscn → 添加 [connection ...] 段 → 写回文件。
 */
export async function ConnectSignal(
  input: ConnectSignalInput,
): Promise<ScriptOutput> {
  if (!input.scene_path) {
    return { script_path: "", error: "scene_path 不能为空" };
  }
  if (!input.signal_name) {
    return { script_path: "", error: "signal_name 不能为空" };
  }
  if (!input.method_name) {
    return { script_path: "", error: "method_name 不能为空" };
  }

  let content: string;
  try {
    content = await readFile(input.scene_path, "utf-8");
  } catch (err) {
    return {
      script_path: "",
      error: `读取场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const doc = ParseTscn(content);

  // 验证节点存在性
  const fromExists = doc.nodes.some((n) => n.name === input.signal_node_path);
  if (!fromExists && input.signal_node_path !== ".") {
    return {
      script_path: "",
      error: `信号源节点 "${input.signal_node_path}" 不存在`,
    };
  }
  const toExists = doc.nodes.some((n) => n.name === input.target_node_path);
  if (!toExists && input.target_node_path !== ".") {
    return {
      script_path: "",
      error: `目标节点 "${input.target_node_path}" 不存在`,
    };
  }

  // 检查重复连接
  const duplicate = doc.connections.some(
    (c) =>
      c.signal === input.signal_name &&
      c.from === input.signal_node_path &&
      c.to === input.target_node_path &&
      c.method === input.method_name,
  );
  if (duplicate) {
    return {
      script_path: input.scene_path,
      error: `信号连接已存在: ${input.signal_node_path}.${input.signal_name} → ${input.target_node_path}.${input.method_name}`,
    };
  }

  doc.connections.push({
    signal: input.signal_name,
    from: input.signal_node_path,
    to: input.target_node_path,
    method: input.method_name,
    flags: input.flags,
  });

  const newContent = serializeTscn(doc);

  try {
    await writeFile(input.scene_path, newContent, "utf-8");
    return { script_path: input.scene_path };
  } catch (err) {
    return {
      script_path: "",
      error: `写入场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/script_manager.ts <command> ...");
    console.error("命令: create <path> <extends>");
    process.exit(1);
  }

  const cmd = args[0];
  if (cmd === "create" && args.length >= 3) {
    const result = await CreateScript({
      path: args[1],
      extends: args[2],
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log("✅ 脚本创建成功:", result.script_path);
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("script_manager.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
