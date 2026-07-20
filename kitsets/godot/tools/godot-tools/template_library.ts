/**
 * M5 · Template Library
 *
 * 三个内置 2D 游戏模板的列表、Fork、和定制化接口。
 * 职责单一：提供可复用的 Godot 游戏启动项目。
 *
 * @module tools/template_library
 */

import { cp, readFile, writeFile, access } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";

// ─── 类型定义 ───

export interface TemplateInfo {
  id: string;
  name: string;
  desc: string;
  complexity: "低" | "中" | "高";
  godot_version: string;
  tags: string[];
}

export interface ForkTemplateInput {
  template_id: string;
  target_path: string;
  project_name: string;
}

export interface CustomizeTemplateInput {
  project_root: string;
  overrides: Record<string, string | number | boolean>;
}

export interface TemplateOutput {
  project_root: string;
  error?: string;
}

// ─── 模板元数据 ───

const _filename = fileURLToPath(import.meta.url);
const _dirname = dirname(_filename);
const TEMPLATES_DIR = resolve(join(_dirname, "..", "templates"));

const TEMPLATES: TemplateInfo[] = [
  {
    id: "platformer",
    name: "平台跳跃",
    desc: "左右移动 + 跳跃，含地面和平台的 2D 平台跳跃游戏",
    complexity: "中",
    godot_version: "4.2+",
    tags: ["2D", "platformer", "physics"],
  },
  {
    id: "breakout",
    name: "打砖块",
    desc: "用挡板反弹小球击碎砖块的经典 Breakout 游戏",
    complexity: "中",
    godot_version: "4.2+",
    tags: ["2D", "arcade", "physics"],
  },
  {
    id: "clicker",
    name: "点击收集",
    desc: "点击屏幕上出现的物品收集积分的点击收集游戏",
    complexity: "低",
    godot_version: "4.2+",
    tags: ["2D", "casual", "mouse-input"],
  },
];

// ─── 主接口 ───

/**
 * ListTemplates — 列出可选模板
 */
export async function ListTemplates(): Promise<TemplateInfo[]> {
  return TEMPLATES;
}

/**
 * ForkTemplate — 复制模板到指定目录
 */
export async function ForkTemplate(
  input: ForkTemplateInput,
): Promise<TemplateOutput> {
  if (!input.template_id) {
    return { project_root: "", error: "template_id 不能为空" };
  }
  if (!input.target_path) {
    return { project_root: "", error: "target_path 不能为空" };
  }
  if (!input.project_name?.trim()) {
    return { project_root: "", error: "project_name 不能为空" };
  }

  // 查找模板
  const template = TEMPLATES.find((t) => t.id === input.template_id);
  if (!template) {
    return {
      project_root: "",
      error: `模板不存在: ${input.template_id}，可用: ${TEMPLATES.map((t) => t.id).join(", ")}`,
    };
  }

  const srcDir = resolve(join(TEMPLATES_DIR, input.template_id));

  // 检查模板目录是否存在
  try {
    await access(srcDir);
  } catch {
    return {
      project_root: "",
      error: `模板目录不存在: ${srcDir}`,
    };
  }

  // 检查目标目录是否已存在
  const destDir = resolve(input.target_path);
  if (existsSync(destDir) && existsSync(join(destDir, "project.godot"))) {
    return {
      project_root: "",
      error: `目标目录已包含 Godot 项目: ${destDir}`,
    };
  }

  // 复制模板目录
  try {
    await cp(srcDir, destDir, { recursive: true, force: false });
  } catch (err) {
    return {
      project_root: "",
      error: `复制模板失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  // 更新项目名称
  try {
    const godotPath = join(destDir, "project.godot");
    let content = await readFile(godotPath, "utf-8");
    content = content.replace(
      /config\/name="[^"]*"/,
      `config/name="${input.project_name}"`,
    );
    await writeFile(godotPath, content, "utf-8");
  } catch (err) {
    // 项目名更新失败不影响模板复制
    return {
      project_root: destDir,
      error: `模板已复制但更新项目名失败: ${err instanceof Error ? err.message : String(err)}`,
    };
  }

  return { project_root: destDir };
}

/**
 * CustomizeTemplate — 对已 fork 的模板做结构化修改
 *
 * 支持修改：player_color (颜色), gravity (重力), speed (速度)
 */
export async function CustomizeTemplate(
  input: CustomizeTemplateInput,
): Promise<TemplateOutput> {
  if (!input.project_root) {
    return { project_root: "", error: "project_root 不能为空" };
  }

  const overrides = input.overrides;
  const modified: string[] = [];

  // 查找并修改 player.gd
  const playerGdPath = join(input.project_root, "scripts", "player.gd");
  try {
    let content = await readFile(playerGdPath, "utf-8");
    let changed = false;

    if (overrides.speed !== undefined && typeof overrides.speed === "number") {
      content = content.replace(
        /@export var speed: int = \d+/,
        `@export var speed: int = ${overrides.speed}`,
      );
      changed = true;
    }
    if (overrides.jump_velocity !== undefined && typeof overrides.jump_velocity === "number") {
      content = content.replace(
        /@export var jump_velocity: float = -?[\d.]+/,
        `@export var jump_velocity: float = ${overrides.jump_velocity}`,
      );
      changed = true;
    }

    if (changed) {
      await writeFile(playerGdPath, content, "utf-8");
      modified.push(playerGdPath);
    }
  } catch {
    // player.gd 不存在则跳过
  }

  // 修改 project.godot 中的 gravity
  if (overrides.gravity !== undefined && typeof overrides.gravity === "number") {
    const godotPath = join(input.project_root, "project.godot");
    try {
      let content = await readFile(godotPath, "utf-8");
      // Godot 4.x 中重力在 Physics2D 设置里，但 project.godot 可以直接设置
      if (!content.includes("physics/2d/default_gravity")) {
        content += `\n[physics]\n2d/default_gravity=${overrides.gravity}\n`;
      } else {
        content = content.replace(
          /default_gravity=\d+/,
          `default_gravity=${overrides.gravity}`,
        );
      }
      await writeFile(godotPath, content, "utf-8");
      modified.push(godotPath);
    } catch {
      // 忽略
    }
  }

  return {
    project_root: input.project_root,
    error: modified.length === 0 ? "没有可定制的属性被修改" : undefined,
  };
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/template_library.ts <command> ...");
    console.error("命令: list");
    console.error("       fork <template_id> <target_path> <project_name>");
    process.exit(1);
  }

  const cmd = args[0];
  if (cmd === "list") {
    const templates = await ListTemplates();
    console.log("可用模板:");
    for (const t of templates) {
      console.log(`  [${t.id}] ${t.name} — ${t.desc} (${t.complexity})`);
    }
  } else if (cmd === "fork" && args.length >= 4) {
    const result = await ForkTemplate({
      template_id: args[1],
      target_path: args[2],
      project_name: args[3],
    });
    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }
    console.log("✅ 模板复制成功:", result.project_root);
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("template_library.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
