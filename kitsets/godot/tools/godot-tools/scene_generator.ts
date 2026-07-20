/**
 * M2 · Scene Generator
 *
 * 生成/编辑 .tscn 场景文件，支持 2D 节点树操作。
 * 职责单一：将结构化节点描述转化为合法的 Godot 4.x .tscn 文本文件。
 *
 * 不做：可视化编辑、运行时渲染、资源管理（那是 M4 的事）。
 *
 * @module tools/scene_generator
 */

import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

// ─── 类型定义 ───

/** Godot 节点类型（MVP 支持的 2D 类型） */
export type NodeType2D =
  | "Node"
  | "Node2D"
  | "CharacterBody2D"
  | "StaticBody2D"
  | "RigidBody2D"
  | "Area2D"
  | "Sprite2D"
  | "AnimatedSprite2D"
  | "CollisionShape2D"
  | "CollisionPolygon2D"
  | "Camera2D"
  | "CanvasLayer"
  | "TileMap"
  | "Label"
  | "ColorRect"
  | "ColorRect"
  | "Control"
  | "TextureRect"
  | "Button"
  | "Marker2D"
  | "Path2D"
  | "Line2D"
  | "AudioStreamPlayer2D"
  | "ParallaxBackground"
  | "ParallaxLayer";

/** 节点结构描述 */
export interface NodeDesc {
  type: NodeType2D;
  name: string;
  position?: { x: number; y: number };
  rotation?: number;
  scale?: { x: number; y: number };
  visible?: boolean;
  /** Godot 属性键值对（自动序列化为基础类型） */
  properties?: Record<string, PropertyValue>;
  /** 原始属性键值对（不序列化，直接写入，用于 SubResource / ExtResource 引用） */
  raw_properties?: Record<string, string>;
  children?: NodeDesc[];
}

/** 支持序列化的属性值类型 */
export type PropertyValue =
  | string
  | number
  | boolean
  | null
  | { x: number; y: number; z?: number; w?: number }
  | { r: number; g: number; b: number; a?: number }
  | PropertyValue[];

/** 场景创建输入 */
export interface CreateSceneInput {
  /** 保存路径 */
  path: string;
  /** 根节点 */
  root_node: NodeDesc;
  /** 场景 uid（可选，自动生成） */
  uid?: string;
}

/** 添加节点输入 */
export interface AddNodeInput {
  scene_path: string;
  parent_path: string;
  node: NodeDesc;
}

/** 移除节点输入 */
export interface RemoveNodeInput {
  scene_path: string;
  node_path: string;
}

/** 设置属性输入 */
export interface SetNodePropertyInput {
  scene_path: string;
  node_path: string;
  properties: Record<string, PropertyValue>;
}

/** 通用输出 */
export interface SceneOutput {
  scene_path: string;
  error?: string;
}

// ─── 内部数据结构 ───

interface ExtResource {
  id: string;
  type: string;
  path: string;
}

interface TscnNode {
  name: string;
  type: string;
  parent: string;
  properties: Array<[string, string]>;
  groups: string[];
  children: TscnNode[];
}

interface TscnDocument {
  format: 3;
  uid: string;
  extResources: ExtResource[];
  subResources: Array<{ id: string; type: string; properties: Array<[string, string]> }>;
  nodes: TscnNode[];
  connections: Array<{ signal: string; from: string; to: string; method: string; flags?: number }>;
}

// ─── UID 生成 ───

/** 生成 Godot 4.x 合法的 uid（13 字符 a-z0-9） */
function generateUid(): string {
  const chars = "0123456789abcdefghijklmnopqrstuvwxyz";
  const buf = randomBytes(13);
  return (
    "uid://" +
    Array.from(buf)
      .map((b) => chars[b % 36])
      .join("")
  );
}

// ─── 属性序列化 ───

function serializePropertyValue(value: PropertyValue): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    // 整数输出不带小数点
    return Number.isInteger(value) ? String(value) : value.toFixed(4);
  }
  if (typeof value === "string") {
    // 对字符串做转义
    const escaped = value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    return `"${escaped}"`;
  }
  if (Array.isArray(value)) {
    // 简单数组（PackedStringArray / Array）
    const items = value.map((v) => serializePropertyValue(v)).join(", ");
    return `[${items}]`;
  }
  // 对象 → Vector2 / Vector3 / Color
  const obj = value as Record<string, number>;
  if ("r" in obj || "g" in obj || "b" in obj) {
    const r = (obj.r ?? 0).toFixed(4);
    const g = (obj.g ?? 0).toFixed(4);
    const b = (obj.b ?? 0).toFixed(4);
    const a = obj.a !== undefined ? `, ${obj.a.toFixed(4)}` : "";
    return `Color(${r}, ${g}, ${b}${a})`;
  }
  if ("z" in obj) {
    return `Vector3(${obj.x}, ${obj.y}, ${obj.z})`;
  }
  if ("w" in obj) {
    return `Quaternion(${obj.x}, ${obj.y}, ${obj.z}, ${obj.w})`;
  }
  return `Vector2(${obj.x}, ${obj.y})`;
}

// ─── 节点属性构建 ───

function buildNodeProperties(node: NodeDesc): Array<[string, string]> {
  const props: Array<[string, string]> = [];

  if (node.position && (node.position.x !== 0 || node.position.y !== 0)) {
    props.push([
      "position",
      `Vector2(${node.position.x}, ${node.position.y})`,
    ]);
  }
  if (node.rotation !== undefined && node.rotation !== 0) {
    props.push(["rotation", serializePropertyValue(node.rotation)]);
  }
  if (node.scale && (node.scale.x !== 1 || node.scale.y !== 1)) {
    props.push(["scale", `Vector2(${node.scale.x}, ${node.scale.y})`]);
  }
  if (node.visible === false) {
    props.push(["visible", "false"]);
  }
  if (node.properties) {
    for (const [key, val] of Object.entries(node.properties)) {
      props.push([key, serializePropertyValue(val)]);
    }
  }
  if (node.raw_properties) {
    for (const [key, val] of Object.entries(node.raw_properties)) {
      props.push([key, val]);
    }
  }
  return props;
}

// ─── 节点收集（展平树 → 列表） ───

interface FlatNode {
  name: string;
  type: string;
  parent: string;
  properties: Array<[string, string]>;
  groups: string[];
}

/** 将节点树展平为有序列表（先根遍历） */
function flattenNodes(
  node: NodeDesc,
  parentPath: string = ".",
): FlatNode[] {
  const result: FlatNode[] = [
    {
      name: node.name,
      type: node.type,
      parent: parentPath,
      properties: buildNodeProperties(node),
      groups: [],
    },
  ];
  if (node.children) {
    for (const child of node.children) {
      result.push(...flattenNodes(child, node.name));
    }
  }
  return result;
}

// ─── TSCN 序列化 ───

export function serializeTscn(doc: TscnDocument): string {
  const lines: string[] = [];

  // Header
  const extCount = doc.extResources.length;
  const subCount = doc.subResources.length;
  const loadSteps = 1 + extCount + subCount + doc.nodes.length;
  const uid = doc.uid || generateUid();
  lines.push(`[gd_scene load_steps=${loadSteps} format=3 uid="${uid}"]`);
  lines.push("");

  // Ext resources
  for (const ext of doc.extResources) {
    const uidStr = ext.path.startsWith("uid://")
      ? ` uid="${ext.path}"`
      : "";
    lines.push(
      `[ext_resource type="${ext.type}"${uidStr} path="${ext.path}" id="${ext.id}"]`,
    );
  }
  if (doc.extResources.length > 0) lines.push("");

  // Sub resources
  for (const sub of doc.subResources) {
    lines.push(`[sub_resource type="${sub.type}" id="${sub.id}"]`);
    for (const [key, val] of sub.properties) {
      lines.push(`${key} = ${val}`);
    }
  }
  if (doc.subResources.length > 0) lines.push("");

  // Nodes
  for (const node of doc.nodes) {
    const parentAttr = node.parent === "." ? "" : ` parent="${node.parent}"`;
    lines.push(`[node name="${node.name}" type="${node.type}"${parentAttr}]`);
    for (const [key, val] of node.properties) {
      lines.push(`${key} = ${val}`);
    }
  }
  if (doc.nodes.length > 0) lines.push("");

  // Connections
  for (const conn of doc.connections) {
    const flags = conn.flags ? ` flags=${conn.flags}` : "";
    lines.push(
      `[connection signal="${conn.signal}" from="${conn.from}" to="${conn.to}" method="${conn.method}"${flags}]`,
    );
  }

  return lines.join("\n");
}

// ─── 简单的行式 TSCN 解析器 ───

function parseTscn(content: string): TscnDocument {
  const doc: TscnDocument = {
    format: 3,
    uid: "",
    extResources: [],
    subResources: [],
    nodes: [],
    connections: [],
  };

  let currentSection: string | null = null;
  let currentSubResource: TscnDocument["subResources"][number] | null = null;
  let currentNode: TscnNode | null = null;

  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // 空行 → 重置当前累积上下文
    if (line === "") {
      if (currentSubResource) {
        doc.subResources.push(currentSubResource);
        currentSubResource = null;
      }
      if (currentNode) {
        doc.nodes.push(currentNode);
        currentNode = null;
      }
      continue;
    }

    // Section headers
    const headerMatch = line.match(/^\[(\w+)\s+(.*?)\]$/);
    if (headerMatch) {
      const sectionType = headerMatch[1];
      const attrs = parseAttributes(headerMatch[2]);

      // 文件末的 nodes/connections 结束
      if (currentNode) {
        doc.nodes.push(currentNode);
        currentNode = null;
      }
      if (currentSubResource) {
        doc.subResources.push(currentSubResource);
        currentSubResource = null;
      }

      currentSection = sectionType;

      if (sectionType === "gd_scene") {
        doc.uid = attrs.uid || "";
        doc.format = parseInt(attrs.format || "3");
      } else if (sectionType === "ext_resource") {
        doc.extResources.push({
          id: attrs.id || "",
          type: attrs.type || "",
          path: attrs.path || "",
        });
      } else if (sectionType === "sub_resource") {
        currentSubResource = {
          id: attrs.id || "",
          type: attrs.type || "",
          properties: [],
        };
      } else if (sectionType === "node") {
        currentNode = {
          name: attrs.name || "",
          type: attrs.type || "",
          parent: attrs.parent || ".",
          properties: [],
          groups: attrs.groups
            ? attrs.groups.replace(/[\[\]"]/g, "").split(",").map((s: string) => s.trim()).filter(Boolean)
            : [],
          children: [],
        };
      } else if (sectionType === "connection") {
        doc.connections.push({
          signal: attrs.signal || "",
          from: attrs.from || "",
          to: attrs.to || "",
          method: attrs.method || "",
          flags: attrs.flags ? parseInt(attrs.flags) : undefined,
        });
      }
      continue;
    }

    // 属性行
    if (currentSubResource) {
      const eqIdx = line.indexOf("=");
      if (eqIdx > 0) {
        currentSubResource.properties.push([
          line.slice(0, eqIdx).trim(),
          line.slice(eqIdx + 1).trim(),
        ]);
      }
    } else if (currentNode) {
      const eqIdx = line.indexOf("=");
      if (eqIdx > 0) {
        currentNode.properties.push([
          line.slice(0, eqIdx).trim(),
          line.slice(eqIdx + 1).trim(),
        ]);
      }
    }
  }

  // 文件末不包含空行时的收尾
  if (currentSubResource) doc.subResources.push(currentSubResource);
  if (currentNode) doc.nodes.push(currentNode);

  return doc;
}

function parseAttributes(raw: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  // Simple key=value parser (handles quoted strings)
  const regex = /(\w+)=(?:"([^"]*)"|(\S+))/g;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    attrs[match[1]] = match[2] !== undefined ? match[2] : match[3];
  }
  return attrs;
}

// ─── 将 NodeDesc 树添加到 TscnDocument ───

function addNodeDescToDoc(
  doc: TscnDocument,
  parentPath: string,
  node: NodeDesc,
): void {
  const flatNodes = flattenNodes(node);
  for (const fnode of flatNodes) {
    const parent = fnode.parent === node.name ? parentPath : fnode.parent;
    doc.nodes.push({
      name: fnode.name,
      type: fnode.type,
      parent: parent === node.name ? parentPath : parent,
      properties: fnode.properties,
      groups: fnode.groups,
      children: [],
    });
  }
}

// ─── 把子节点树递归加到 parentPath ───

function addChildrenToDoc(doc: TscnDocument, parentPath: string, children: NodeDesc[]): void {
  for (const child of children) {
    const flat = flattenNodes(child, parentPath);
    for (const f of flat) {
      doc.nodes.push({
        name: f.name,
        type: f.type,
        parent: f.parent,
        properties: f.properties,
        groups: [],
        children: [],
      });
    }
  }
}

// ─── 主接口 ───

/**
 * CreateScene — 创建新 .tscn 场景文件
 */
export async function CreateScene(
  input: CreateSceneInput,
): Promise<SceneOutput> {
  if (!input.path) {
    return { scene_path: "", error: "path 不能为空" };
  }
  if (!input.root_node?.name) {
    return { scene_path: "", error: "根节点 name 不能为空" };
  }
  if (!input.root_node?.type) {
    return { scene_path: "", error: "根节点 type 不能为空" };
  }

  const doc: TscnDocument = {
    format: 3,
    uid: input.uid || generateUid(),
    extResources: [],
    subResources: [],
    nodes: [],
    connections: [],
  };

  // 展平节点树
  const flatNodes = flattenNodes(input.root_node);
  for (const fnode of flatNodes) {
    doc.nodes.push({
      name: fnode.name,
      type: fnode.type,
      parent: fnode.parent,
      properties: fnode.properties,
      groups: fnode.groups,
      children: [],
    });
  }

  const content = serializeTscn(doc);

  try {
    await writeFile(input.path, content, "utf-8");
    return { scene_path: input.path };
  } catch (err) {
    return {
      scene_path: "",
      error: `写入场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * AddNode — 向已有场景添加子节点
 */
export async function AddNode(input: AddNodeInput): Promise<SceneOutput> {
  if (!input.node?.name || !input.node?.type) {
    return { scene_path: "", error: "节点 name 和 type 不能为空" };
  }

  let content: string;
  try {
    content = await readFile(input.scene_path, "utf-8");
  } catch (err) {
    return {
      scene_path: "",
      error: `读取场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const doc = parseTscn(content);

  // 找到父节点索引
  const parentIdx = doc.nodes.findIndex((n) => n.name === input.parent_path);
  if (parentIdx === -1 && input.parent_path !== ".") {
    return {
      scene_path: "",
      error: `父节点 "${input.parent_path}" 不存在`,
    };
  }

  // 添加节点及其子节点
  addChildrenToDoc(doc, input.parent_path, [input.node]);

  const newContent = serializeTscn(doc);

  try {
    await writeFile(input.scene_path, newContent, "utf-8");
    return { scene_path: input.scene_path };
  } catch (err) {
    return {
      scene_path: "",
      error: `写入场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * RemoveNode — 从场景中移除节点及其所有子节点
 */
export async function RemoveNode(
  input: RemoveNodeInput,
): Promise<SceneOutput> {
  let content: string;
  try {
    content = await readFile(input.scene_path, "utf-8");
  } catch (err) {
    return {
      scene_path: "",
      error: `读取场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const doc = parseTscn(content);

  const targetIdx = doc.nodes.findIndex((n) => n.name === input.node_path);
  if (targetIdx === -1) {
    return {
      scene_path: "",
      error: `节点 "${input.node_path}" 不存在`,
    };
  }

  // 收集要删除的节点名（自己 + 所有以 node_path 为 parent 的子节点）
  const toRemove = new Set<string>();
  toRemove.add(input.node_path);

  // 多遍收集子节点
  let changed = true;
  while (changed) {
    changed = false;
    for (const n of doc.nodes) {
      if (toRemove.has(n.parent) && !toRemove.has(n.name)) {
        toRemove.add(n.name);
        changed = true;
      }
    }
  }

  // 过滤掉要删除的节点
  doc.nodes = doc.nodes.filter((n) => !toRemove.has(n.name));

  const newContent = serializeTscn(doc);

  try {
    await writeFile(input.scene_path, newContent, "utf-8");
    return { scene_path: input.scene_path };
  } catch (err) {
    return {
      scene_path: "",
      error: `写入场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

/**
 * SetNodeProperty — 修改场景中某个节点的属性
 */
export async function SetNodeProperty(
  input: SetNodePropertyInput,
): Promise<SceneOutput> {
  let content: string;
  try {
    content = await readFile(input.scene_path, "utf-8");
  } catch (err) {
    return {
      scene_path: "",
      error: `读取场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const doc = parseTscn(content);

  const targetIdx = doc.nodes.findIndex((n) => n.name === input.node_path);
  if (targetIdx === -1) {
    return {
      scene_path: "",
      error: `节点 "${input.node_path}" 不存在`,
    };
  }

  const node = doc.nodes[targetIdx];
  for (const [key, val] of Object.entries(input.properties)) {
    const serialized = serializePropertyValue(val);
    // 替换已有属性或追加
    const existingIdx = node.properties.findIndex(([k]) => k === key);
    if (existingIdx >= 0) {
      node.properties[existingIdx] = [key, serialized];
    } else {
      node.properties.push([key, serialized]);
    }
  }

  const newContent = serializeTscn(doc);

  try {
    await writeFile(input.scene_path, newContent, "utf-8");
    return { scene_path: input.scene_path };
  } catch (err) {
    return {
      scene_path: "",
      error: `写入场景文件失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

// ─── 导出：场景内容生成纯函数（无 IO，可测试） ───

/** 只生成 .tscn 文本内容（不写磁盘），用于测试和预览 */
export function RenderTscn(input: CreateSceneInput): string {
  const doc: TscnDocument = {
    format: 3,
    uid: input.uid || generateUid(),
    extResources: [],
    subResources: [],
    nodes: [],
    connections: [],
  };

  const flatNodes = flattenNodes(input.root_node);
  for (const fnode of flatNodes) {
    doc.nodes.push({
      name: fnode.name,
      type: fnode.type,
      parent: fnode.parent,
      properties: fnode.properties,
      groups: fnode.groups,
      children: [],
    });
  }

  return serializeTscn(doc);
}

/** 解析 .tscn 字符串（不读磁盘），用于测试和预览 */
export function ParseTscn(content: string): TscnDocument {
  return parseTscn(content);
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/scene_generator.ts <command> ...");
    console.error("命令: create <path> <root_type> <root_name>");
    process.exit(1);
  }

  const cmd = args[0];
  if (cmd === "create" && args.length >= 4) {
    const result = await CreateScene({
      path: args[1],
      root_node: { type: args[2] as NodeType2D, name: args[3] },
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log("✅ 场景创建成功:", result.scene_path);
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("scene_generator.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
