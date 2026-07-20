/**
 * M1 · Project Scaffolder
 *
 * 创建 Godot 4.x 项目骨架 + project.godot 配置 + 默认空场景。
 * 职责单一：生成一个能被 Godot 4.x 打开的合法项目目录。
 *
 * @module tools/scaffolder
 */

import { mkdir, writeFile, access } from "node:fs/promises";
import { join, resolve, normalize } from "node:path";

// ─── 类型定义 ───

export interface ScaffoldInput {
  /** 目标目录（不存在则创建） */
  root_path: string;
  /** 项目显示名称（写入 project.godot config/name） */
  project_name: string;
  /** 分辨率，默认 1152×648（标准 16:9） */
  resolution?: { width: number; height: number };
  /** 渲染器，默认 forward_plus */
  renderer?: "forward_plus" | "mobile" | "gl_compatibility";
  /** Godot 主版本号，当前仅支持 "4.x" */
  version?: string;
}

export interface ScaffoldOutput {
  project_root: string;
  error?: string;
}

// ─── 常量 ───

const SUPPORTED_VERSIONS = new Set(["4.x"]);

const DIR_STRUCTURE = [
  "scenes",
  "scripts",
  "assets/textures",
  "assets/audio",
  "assets/fonts",
] as const;

const DEFAULT_RESOLUTION = { width: 1152, height: 648 };
const DEFAULT_RENDERER = "forward_plus" as const;

// ─── 路径安全 ───

/** 防路径穿越：确保 root_path 不含 ../ 且不为驱动器根目录 */
function sanitizePath(raw: string): string | null {
  // 在 normalize 之前检查原始输入是否含 .. 段
  const segments = raw.split(/[/\\]+/);
  if (segments.includes("..")) return null;
  // 拒绝绝对路径 / 或 Windows 盘符根目录
  if (/^[A-Za-z]:\\?$/i.test(raw)) return null;
  if (raw === "/") return null;
  return normalize(raw);
}

// ─── 文件内容生成（纯函数，可测试） ───

/** 生成 project.godot 内容 */
function renderProjectGodot(input: ScaffoldInput): string {
  const res = input.resolution ?? DEFAULT_RESOLUTION;
  const renderer = input.renderer ?? DEFAULT_RENDERER;
  const features =
    renderer === "mobile"
      ? `PackedStringArray("4.3", "mobile")`
      : `PackedStringArray("4.2")`;

  return `; Engine configuration file.
; It's best edited using the Godot engine editor.
;
; Documentation: https://docs.godotengine.org/en/stable/tutorials/editor/project_settings.html

[application]
config/name="${input.project_name}"
config/description=""
run/main_scene="res://scenes/Main.tscn"
config/features=${features}
config/icon="res://icon.svg"

[rendering]
renderer/rendering_method="${renderer}"
renderer/rendering_method.mobile="${renderer === "mobile" ? "mobile" : "forward_plus"}"
renderer/texture_filter/force_nearest_without_mipmaps=false

[display]
window/size/viewport_width=${res.width}
window/size/viewport_height=${res.height}
window/size/mode=0
window/size/always_on_top=false
window/dpi/allow_hidpi=true
window/energy_saving/keep_screen_on=true
`;
}

/** 生成 default_env.tres 内容 */
function renderDefaultEnv(): string {
  return `[gd_resource type="Environment" load_steps=1 format=3 uid="uid://default_env_tres"]

[resource]
background_mode = 2
background_color = Color(0.15, 0.15, 0.2, 1)
`;
}

/** 生成 icon.svg（Godot 风格占位图标） */
function renderIconSvg(): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <rect width="256" height="256" fill="#2a2a3a" rx="32"/>
  <circle cx="128" cy="128" r="64" fill="none" stroke="#4a8cf7" stroke-width="8"/>
  <polygon points="128,80 176,160 80,160" fill="none" stroke="#4a8cf7" stroke-width="6"/>
</svg>
`;
}

/** 生成默认 Main.tscn 场景 */
function renderDefaultScene(): string {
  return `[gd_scene load_steps=1 format=3 uid="uid://default_main_scene"]

[node name="Main" type="Node2D"]
`;
}

// ─── 目录结构 ───

/** 需要创建的目录列表（相对于项目根） */
function getDirectories(root: string): string[] {
  return DIR_STRUCTURE.map((d) => join(root, d));
}

// ─── 检测是否已存在合法 Godot 项目 ───

async function isExistingGodotProject(root: string): Promise<boolean> {
  try {
    await access(join(root, "project.godot"));
    return true;
  } catch {
    return false;
  }
}

// ─── 主要接口 ───

/**
 * ScaffoldProject — 在指定路径创建完整的 Godot 项目骨架。
 *
 * 如果 root_path 已存在且包含 project.godot，返回错误（不覆盖）。
 * 如果 root_path 不存在，自动创建。
 */
export async function ScaffoldProject(
  input: ScaffoldInput,
): Promise<ScaffoldOutput> {
  // ── 输入校验 ──
  if (!input.root_path) {
    return { project_root: "", error: "root_path 不能为空" };
  }
  if (!input.project_name?.trim()) {
    return { project_root: "", error: "project_name 不能为空" };
  }

  const sanitized = sanitizePath(input.root_path);
  if (!sanitized) {
    return { project_root: "", error: `非法路径: ${input.root_path}` };
  }

  const version = input.version ?? "4.x";
  if (!SUPPORTED_VERSIONS.has(version)) {
    return {
      project_root: "",
      error: `不支持的 Godot 版本: ${version}，当前仅支持 4.x`,
    };
  }

  const res = input.resolution ?? DEFAULT_RESOLUTION;
  if (res.width < 1 || res.height < 1) {
    return { project_root: "", error: "分辨率必须为正整数" };
  }
  if (res.width > 16384 || res.height > 16384) {
    return { project_root: "", error: "分辨率超出 Godot 支持范围（最大 16384）" };
  }

  // ── 检查是否已存在合法项目 ──
  const exists = await isExistingGodotProject(resolve(sanitized));
  if (exists) {
    return {
      project_root: "",
      error: `目标目录已包含 Godot 项目 (${sanitized})，如需覆盖请先删除现有项目`,
    };
  }

  // ── 创建目录结构 ──
  const root = resolve(sanitized);
  const allDirs = [root, ...getDirectories(root)];

  try {
    for (const dir of allDirs) {
      await mkdir(dir, { recursive: true });
    }
  } catch (err) {
    return {
      project_root: "",
      error: `创建目录失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  // ── 写入文件 ──
  const files: Array<[string, string]> = [
    [join(root, "project.godot"), renderProjectGodot(input)],
    [join(root, "default_env.tres"), renderDefaultEnv()],
    [join(root, "icon.svg"), renderIconSvg()],
    [join(root, "scenes", "Main.tscn"), renderDefaultScene()],
  ];

  for (const [filePath, content] of files) {
    try {
      await writeFile(filePath, content, "utf-8");
    } catch (err) {
      return {
        project_root: "",
        error: `写入文件失败 (${filePath}): ${err instanceof Error ? err.message : String(err)}`,
      };
    }
  }

  return { project_root: root };
}

// ─── CLI 入口 ───
// 支持通过命令行直接调用：npx tsx tools/scaffolder.ts <root_path> <project_name>

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error(
      "用法: npx tsx tools/scaffolder.ts <root_path> <project_name> [width] [height] [renderer]",
    );
    process.exit(1);
  }

  const input: ScaffoldInput = {
    root_path: args[0],
    project_name: args[1],
    resolution:
      args[2] && args[3]
        ? { width: Number(args[2]), height: Number(args[3]) }
        : undefined,
    renderer: args[4] as ScaffoldInput["renderer"],
  };

  const result = await ScaffoldProject(input);
  if (result.error) {
    console.error("❌", result.error);
    process.exit(1);
  }
  console.log("✅ 项目创建成功:", result.project_root);
}

if (process.argv[1]?.endsWith("scaffolder.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
