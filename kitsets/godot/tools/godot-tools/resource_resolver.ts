/**
 * M4 · Resource Resolver
 *
 * 管理纹理/音效/字体等资源的导入路径与引用。
 * 职责单一：将外部资源文件导入 Godot 项目，确保 res:// 路径正确。
 *
 * @module tools/resource_resolver
 */

import { copyFile, mkdir, access } from "node:fs/promises";
import { join, relative, dirname, basename, extname } from "node:path";

// ─── 类型定义 ───

export type ResourceType = "texture" | "audio" | "font" | "shader";

export interface ImportResourceInput {
  /** 源文件路径（外部文件系统） */
  source_path: string;
  /** 资源类型，决定目标子目录 */
  dest_type: ResourceType;
  /** Godot 项目根目录 */
  project_root: string;
  /** 可选：目标文件名（不传则用源文件名） */
  dest_name?: string;
  /** 可选：是否覆盖已存在的文件 */
  overwrite?: boolean;
}

export interface ImportResourceOutput {
  /** Godot 资源路径（res:// 格式） */
  resource_path: string;
  /** 实际文件系统路径 */
  fs_path: string;
  error?: string;
}

export interface ResolvePathInput {
  /** 要解析的路径 */
  path: string;
  /** 解析方向 */
  direction: "godot_to_fs" | "fs_to_godot";
  /** Godot 项目根目录（godot_to_fs 时需要） */
  project_root?: string;
}

export interface ResolvePathOutput {
  resolved: string;
  error?: string;
}

// ─── 常量 ───

const TYPE_DIR_MAP: Record<ResourceType, string> = {
  texture: "assets/textures",
  audio: "assets/audio",
  font: "assets/fonts",
  shader: "assets/shaders",
};

/** Godot 支持的常见拓展名 → 资源类型映射 */
const EXT_TO_TYPE: Record<string, ResourceType> = {
  png: "texture",
  jpg: "texture",
  jpeg: "texture",
  webp: "texture",
  svg: "texture",
  bmp: "texture",
  tga: "texture",
  ogg: "audio",
  mp3: "audio",
  wav: "audio",
  flac: "audio",
  ttf: "font",
  otf: "font",
  glsl: "shader",
  shader: "shader",
  gdshader: "shader",
};

// ─── 文件名清理 ───

/** 清理文件名：去特殊字符、转空格为下划线、保留扩展名 */
function sanitizeFileName(name: string): string {
  const ext = extname(name);
  const base = basename(name, ext);
  const cleaned = base
    .normalize("NFC")
    .replace(/[\x00-\x1f<>:"/\\|?*\x7f]/g, "")
    .replace(/\s+/g, "_")
    .replace(/[^\w\-\.\u4e00-\u9fff\u3400-\u4dbf]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_/, "")
    .replace(/_$/, "")
    .slice(0, 128); // 长度限制
  return cleaned + ext.toLowerCase();
}

// ─── 路径工具 ───

/** 文件系统路径 → Godot res:// 路径 */
function fsToGodotPath(fsPath: string, projectRoot: string): string | null {
  if (!fsPath.startsWith(projectRoot)) return null;
  const rel = relative(projectRoot, fsPath).replace(/\\/g, "/");
  return "res://" + rel;
}

/** Godot res:// 路径 → 文件系统路径 */
function godotToFsPath(resPath: string, projectRoot: string): string | null {
  if (!resPath.startsWith("res://")) return null;
  const rel = resPath.slice(6).replace(/\//g, "\\");
  return join(projectRoot, rel);
}

// ─── 主接口 ───

/**
 * ImportResource — 将外部资源复制到项目资产目录
 *
 * 1. 检查源文件是否存在
 * 2. 清理文件名
 * 3. 复制到 assets/<type>/
 * 4. 返回 res:// 路径
 */
export async function ImportResource(
  input: ImportResourceInput,
): Promise<ImportResourceOutput> {
  // ── 输入校验 ──
  if (!input.source_path) {
    return { resource_path: "", fs_path: "", error: "source_path 不能为空" };
  }
  if (!input.project_root) {
    return { resource_path: "", fs_path: "", error: "project_root 不能为空" };
  }
  if (!TYPE_DIR_MAP[input.dest_type]) {
    return {
      resource_path: "",
      fs_path: "",
      error: `不支持的资源类型: ${input.dest_type}，支持: ${Object.keys(TYPE_DIR_MAP).join(", ")}`,
    };
  }

  // ── 检查源文件是否存在 ──
  try {
    await access(input.source_path);
  } catch {
    return {
      resource_path: "",
      fs_path: "",
      error: `源文件不存在: ${input.source_path}`,
    };
  }

  // ── 确定目标文件名 ──
  const rawName = input.dest_name || basename(input.source_path);
  const safeName = sanitizeFileName(rawName);

  // ── 确定目标目录 ──
  const targetDir = join(input.project_root, TYPE_DIR_MAP[input.dest_type]);
  const targetPath = join(targetDir, safeName);

  // ── 检查是否已存在（不覆盖时） ──
  if (!input.overwrite) {
    try {
      await access(targetPath);
      return {
        resource_path: fsToGodotPath(targetPath, input.project_root) || "",
        fs_path: targetPath,
        error: `资源已存在: ${targetPath}，设置 overwrite=true 以覆盖`,
      };
    } catch {
      // 文件不存在，继续
    }
  }

  // ── 复制文件 ──
  try {
    await mkdir(targetDir, { recursive: true });
    await copyFile(input.source_path, targetPath);
  } catch (err) {
    return {
      resource_path: "",
      fs_path: "",
      error: `复制资源失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  const resourcePath = fsToGodotPath(targetPath, input.project_root) || "";

  return { resource_path: resourcePath, fs_path: targetPath };
}

/**
 * ResolvePath — 双向路径解析
 *
 * fs_to_godot: "C:/project/assets/textures/hero.png" → "res://assets/textures/hero.png"
 * godot_to_fs: "res://assets/textures/hero.png" → "C:/project/assets/textures/hero.png"
 */
export async function ResolvePath(
  input: ResolvePathInput,
): Promise<ResolvePathOutput> {
  if (!input.path) {
    return { resolved: "", error: "path 不能为空" };
  }
  if (!input.direction) {
    return { resolved: "", error: "direction 不能为空" };
  }

  if (input.direction === "fs_to_godot") {
    if (!input.project_root) {
      return { resolved: "", error: "fs_to_godot 方向需要 project_root" };
    }
    const result = fsToGodotPath(input.path, input.project_root);
    if (!result) {
      return {
        resolved: "",
        error: `路径不在项目目录内: ${input.path}`,
      };
    }
    return { resolved: result };
  }

  if (input.direction === "godot_to_fs") {
    if (!input.project_root) {
      return { resolved: "", error: "godot_to_fs 方向需要 project_root" };
    }
    const result = godotToFsPath(input.path, input.project_root);
    if (!result) {
      return {
        resolved: "",
        error: `非法的 res:// 路径: ${input.path}`,
      };
    }
    return { resolved: result };
  }

  return {
    resolved: "",
    error: `不支持的解析方向: ${input.direction}`,
  };
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/resource_resolver.ts <command> ...");
    console.error("命令: import <source> <type> <project_root>");
    process.exit(1);
  }

  const cmd = args[0];
  if (cmd === "import" && args.length >= 4) {
    const result = await ImportResource({
      source_path: args[1],
      dest_type: args[2] as ResourceType,
      project_root: args[3],
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log("✅ 资源导入成功:", result.resource_path);
  } else if (cmd === "resolve" && args.length >= 3) {
    const result = await ResolvePath({
      path: args[1],
      direction: args[2] as "godot_to_fs" | "fs_to_godot",
      project_root: args[3],
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log("✅ 解析结果:", result.resolved);
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("resource_resolver.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
