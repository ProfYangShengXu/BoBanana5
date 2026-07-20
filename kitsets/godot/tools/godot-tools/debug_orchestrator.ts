/**
 * M10 · Debug Orchestrator
 *
 * 编排完整的调试会话——运行游戏、模拟输入、捕获日志、LLM 分析。
 * 将 M6（启动游戏）+ M8（捕获日志）+ M9（输入模拟）组合为一条命令。
 *
 * 核心流程：
 *   1. 通过 M6 的 RunGodot 启动游戏
 *   2. 通过 M9 的 SimulateKeySequence 模拟输入
 *   3. 通过 M8 的 CaptureLogs/ParseLogText 收集和分析日志
 *   4. 可选：调用 LLM API 分析日志 + 代码上下文 → 输出诊断报告
 *   5. 保存会话记录到 project/debug-sessions/
 *
 * @module tools/debug_orchestrator
 */

import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { join, relative } from "node:path";
import { existsSync } from "node:fs";
import { CaptureLogs, type CaptureLogsInput } from "./log_capture";
import { SummarizeLogs, type LogEntry } from "./log_parser";
import { SimulateKeySequence, type InputAction } from "./input_simulator";

// ─── 类型定义 ───

export interface DiagnosisReport {
  /** 根因描述 */
  root_cause: string;
  /** 严重程度 */
  severity: "critical" | "major" | "minor" | "info";
  /** 受影响的文件（Godot 资源路径） */
  affected_file?: string;
  /** 受影响的行号 */
  affected_line?: number;
  /** 修复建议 */
  suggested_fix?: string;
  /** 置信度 0-1 */
  confidence: number;
}

export interface DebugSessionInput {
  /** Godot 项目根目录 */
  project_root: string;
  /** 输入脚本 ID（从 input-scripts/ 加载）或内联序列 */
  input_script?: string | InputAction[];
  /** 游戏运行时长（秒），默认 10 */
  duration_sec?: number;
  /** 是否调用 LLM 分析日志 */
  llm_analysis?: boolean;
  /** Godot 可执行文件路径 */
  godot_path?: string;
  /** LLM API key（不传则从环境变量读取） */
  llm_api_key?: string;
  /** LLM API 地址（默认 OpenAI） */
  llm_api_url?: string;
  /** LLM 模型名 */
  llm_model?: string;
}

export interface DebugSessionOutput {
  /** 日志摘要 */
  log_summary: {
    stats: { total: number; errors: number; warnings: number; infos: number; debug: number };
    top_errors: Array<{ file: string; line: number; count: number; example: string }>;
    diagnosis_hints: string[];
  };
  /** 会话 ID（可用于追溯） */
  session_id: string;
  /** LLM 分析报告（如果启用且成功） */
  diagnosis?: DiagnosisReport;
  /** 完整日志条目数量 */
  entry_count: number;
  error?: string;
}

export interface AnalyzeLogsInput {
  /** 日志条目 */
  log_entries: LogEntry[];
  /** 项目根目录（用于读取相关代码片段） */
  project_root: string;
  /** 可选的指定文件分析范围 */
  relevant_files?: string[];
  /** LLM API key */
  api_key?: string;
  /** LLM API 地址 */
  api_url?: string;
  /** 模型名 */
  model?: string;
}

export interface ListDebugSessionsInput {
  /** 项目根目录（可选，不传则扫描当前目录） */
  project_root?: string;
  /** 返回条数上限 */
  limit?: number;
}

export interface DebugSessionMeta {
  session_id: string;
  project: string;
  timestamp: string;
  error_count: number;
  warning_count: number;
  status: "success" | "has_errors" | "failed";
  has_diagnosis: boolean;
}

export interface ListDebugSessionsOutput {
  sessions: DebugSessionMeta[];
  error?: string;
}

// ─── 常量 ───

const DEFAULT_DURATION_SEC = 10;
const SESSIONS_DIR = "debug-sessions";

// ─── 辅助函数 ───

function generateSessionId(): string {
  const now = new Date();
  const ts = now.toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const random = Math.random().toString(36).slice(2, 6);
  return `${ts}-${random}`;
}

function getSessionsDir(projectRoot: string): string {
  return join(projectRoot, SESSIONS_DIR);
}

function getSessionPath(projectRoot: string, sessionId: string): string {
  return join(getSessionsDir(projectRoot), `${sessionId}.json`);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ─── 内联输入脚本处理 ───

function isInlineSequence(val: string | InputAction[]): val is InputAction[] {
  return Array.isArray(val);
}

async function loadInputSequence(
  inputScript: string | InputAction[] | undefined,
): Promise<InputAction[] | null> {
  if (!inputScript) return null;
  if (isInlineSequence(inputScript)) return inputScript;

  // 按 ID 从 input-scripts/ 加载
  const scriptsDir = join(process.cwd(), "input-scripts");
  const scriptPath = join(scriptsDir, `${inputScript}.json`);

  try {
    const content = await readFile(scriptPath, "utf-8");
    const parsed = JSON.parse(content);
    return parsed.sequence ?? parsed;
  } catch {
    return null;
  }
}

// ─── LLM 分析 ───

/**
 * AnalyzeLogsWithLLM — 将日志 + 代码上下文发送给 LLM 分析
 *
 * 构建包含以下内容的 Prompt：
 *   - 日志摘要（stats + top_errors）
 *   - 关联的 .gd 代码片段
 *   - 项目结构上下文
 *
 * 调用 OpenAI/Anthropic 兼容 API，解析返回的诊断结构。
 * 失败时 graceful 降级（返回基于规则的分析结果）。
 */
export async function AnalyzeLogsWithLLM(
  input: AnalyzeLogsInput,
): Promise<{ diagnosis: DiagnosisReport | null; error?: string }> {
  const { log_entries, project_root, relevant_files, api_key, api_url, model } = input;

  if (log_entries.length === 0) {
    return { diagnosis: null, error: "没有日志条目可供分析" };
  }

  // 生成日志摘要
  const summaryResult = SummarizeLogs({ entries: log_entries });
  const summary = summaryResult.summary;

  // 读取相关 .gd 文件代码片段
  const codeSnippets: string[] = [];
  const filesToRead = new Set<string>();

  for (const err of summary.top_errors.slice(0, 5)) {
    if (err.file && err.file.startsWith("res://")) {
      const fsPath = err.file.replace("res://", project_root + "/");
      // 转换为实际文件路径
      const actualPath = join(project_root, err.file.replace("res://", ""));
      if (existsSync(actualPath)) {
        filesToRead.add(actualPath);
      }
    }
  }

  if (relevant_files) {
    for (const f of relevant_files) {
      const fp = join(project_root, f);
      if (existsSync(fp)) filesToRead.add(fp);
    }
  }

  for (const fp of filesToRead) {
    try {
      const content = await readFile(fp, "utf-8");
      const relPath = relative(project_root, fp);
      const lines = content.split("\n");
      // 只取前 100 行
      const snippet = lines.slice(0, 100).join("\n");
      codeSnippets.push(`--- ${relPath} ---\n${snippet}`);
    } catch {
      // 跳过无法读取的文件
    }
  }

  // 构建 LLM Prompt
  const prompt = buildAnalysisPrompt(summary, codeSnippets);

  // 尝试调用 LLM API
  const key = api_key || process.env.OPENAI_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!key) {
    // 无 API key 时返回基于规则的诊断
    return {
      diagnosis: ruleBasedDiagnosis(summary, log_entries),
    };
  }

  try {
    const result = await callLLMAPI(prompt, key, api_url, model);
    return { diagnosis: result };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    // LLM 调用失败，降级到规则分析
    return {
      diagnosis: ruleBasedDiagnosis(summary, log_entries),
      error: `LLM 调用失败，已切换到规则分析: ${message}`,
    };
  }
}

/**
 * 构建 LLM 分析 Prompt
 */
function buildAnalysisPrompt(
  summary: { stats: any; top_errors: any[]; diagnosis_hints: string[] },
  codeSnippets: string[],
): string {
  return `你是一个 Godot 4.x 游戏调试专家。分析以下日志并输出诊断报告。

## 日志统计
- 总条目: ${summary.stats.total}
- 错误: ${summary.stats.errors}
- 警告: ${summary.stats.warnings}

## 高频错误
${summary.top_errors.map((e) => `- ${e.file}:${e.line} (${e.count} 次): ${e.example}`).join("\n") || "(无)"}

## 诊断提示
${summary.diagnosis_hints.map((h) => `- ${h}`).join("\n") || "(无)"}

## 相关代码片段
${codeSnippets.join("\n\n") || "(无代码上下文)"}

请严格按照以下 JSON 格式输出诊断报告（不要输出其他内容）：
{
  "root_cause": "根因描述（中文）",
  "severity": "critical|major|minor|info",
  "affected_file": "res://相对路径（如果有）",
  "affected_line": 行号,
  "suggested_fix": "修复建议（中文）",
  "confidence": 0.0-1.0
}`;
}

/**
 * 调用 LLM API（OpenAI 兼容格式）
 */
async function callLLMAPI(
  prompt: string,
  apiKey: string,
  apiUrl?: string,
  model?: string,
): Promise<DiagnosisReport> {
  const url = apiUrl || "https://api.openai.com/v1/chat/completions";
  const modelName = model || "gpt-4o-mini";

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: modelName,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.1,
      max_tokens: 1000,
    }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) {
    const errBody = await response.text().catch(() => "");
    throw new Error(`LLM API 返回 ${response.status}: ${errBody}`);
  }

  const data = await response.json() as any;
  const content: string = data.choices?.[0]?.message?.content || "";

  // 从响应中提取 JSON
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error("LLM 响应未包含 JSON");
  }

  const parsed = JSON.parse(jsonMatch[0]);
  return {
    root_cause: parsed.root_cause || "未知",
    severity: parsed.severity || "info",
    affected_file: parsed.affected_file,
    affected_line: parsed.affected_line,
    suggested_fix: parsed.suggested_fix,
    confidence: typeof parsed.confidence === "number" ? parsed.confidence : 0.5,
  };
}

/**
 * 基于规则的降级诊断（无 LLM 时使用）
 */
function ruleBasedDiagnosis(
  summary: { stats: { errors: number; warnings: number }; top_errors: Array<{ file: string; line: number; count: number; example: string }>; diagnosis_hints: string[] },
  _entries: LogEntry[],
): DiagnosisReport {
  if (summary.stats.errors === 0 && summary.stats.warnings === 0) {
    return {
      root_cause: "日志中未检测到错误或警告，游戏运行正常",
      severity: "info",
      confidence: 0.9,
    };
  }

  if (summary.top_errors.length > 0) {
    const top = summary.top_errors[0]!;
    return {
      root_cause: `检测到错误: "${top.example}"（位于 ${top.file}:${top.line}，出现 ${top.count} 次）`,
      severity: summary.stats.errors > 5 ? "critical" : "major",
      affected_file: top.file,
      affected_line: top.line,
      suggested_fix: `请检查 ${top.file} 第 ${top.line} 行附近的代码逻辑`,
      confidence: 0.4,
    };
  }

  return {
    root_cause: `检测到 ${summary.stats.errors} 个错误和 ${summary.stats.warnings} 个警告`,
    severity: summary.stats.errors > 0 ? "major" : "minor",
    confidence: 0.3,
  };
}

// ─── 主接口 ───

/**
 * RunDebugSession — 运行一次完整的调试会话
 *
 * 流程：
 *   1. 验证项目路径
 *   2. 加载输入脚本（如果有）
 *   3. 通过 CaptureLogs（→ M6 RunGodot）启动游戏并捕获日志
 *   4. 如果在输入脚本，通过 SimulateKeySequence（M9）模拟输入
 *   5. 等待指定时长
 *   6. 解析日志，生成摘要
 *   7. 如果启用 LLM 分析，调用 AnalyzeLogsWithLLM
 *   8. 保存会话记录
 */
export async function RunDebugSession(
  input: DebugSessionInput,
): Promise<DebugSessionOutput> {
  const {
    project_root,
    input_script,
    duration_sec = DEFAULT_DURATION_SEC,
    llm_analysis = true,
    godot_path,
    llm_api_key,
    llm_api_url,
    llm_model,
  } = input;

  if (!project_root) {
    return {
      log_summary: emptyStats(),
      session_id: "",
      entry_count: 0,
      error: "project_root 不能为空",
    };
  }

  if (!existsSync(join(project_root, "project.godot"))) {
    return {
      log_summary: emptyStats(),
      session_id: "",
      entry_count: 0,
      error: `项目路径不存在或不是 Godot 项目: ${project_root}`,
    };
  }

  const sessionId = generateSessionId();
  const errors: string[] = [];

  // 加载输入序列
  const sequence = await loadInputSequence(input_script);

  // 第 1 步：运行游戏并捕获日志
  const captureInput: CaptureLogsInput = {
    project_root,
    timeout_sec: duration_sec + 10, // 比运行时多 10 秒缓冲
    godot_args: ["--headless"],
    godot_path,
  };

  const captureResult = await CaptureLogs(captureInput);

  if (captureResult.error) {
    errors.push(captureResult.error);
  }

  // 第 2 步：如果有输入脚本，等待游戏启动后模拟输入
  if (sequence && sequence.length > 0) {
    // 等待游戏初始化
    await sleep(2000);

    const simResult = await SimulateKeySequence({
      keys: sequence,
      godot_project: project_root,
    });

    if (simResult.error) {
      errors.push(`输入模拟: ${simResult.error}`);
    }
  }

  // 第 3 步：等待剩余时间
  const elapsedSec = 2 + (sequence ? sequence.length * 0.1 : 0);
  const remainingSec = Math.max(0, duration_sec - elapsedSec);
  if (remainingSec > 0) {
    await sleep(remainingSec * 1000);
  }

  // 第 4 步：LLM 分析（如果启用）
  let diagnosis: DiagnosisReport | undefined;

  if (llm_analysis && captureResult.entries.length > 0) {
    const analysisResult = await AnalyzeLogsWithLLM({
      log_entries: captureResult.entries,
      project_root,
      api_key: llm_api_key,
      api_url: llm_api_url,
      model: llm_model,
    });

    if (analysisResult.diagnosis) {
      diagnosis = analysisResult.diagnosis;
    }
    if (analysisResult.error) {
      errors.push(`LLM 分析: ${analysisResult.error}`);
    }
  }

  // 第 5 步：保存会话记录
  await saveSession(project_root, sessionId, {
    session_id: sessionId,
    project: project_root,
    timestamp: new Date().toISOString(),
    input_script: input_script,
    duration_sec,
    llm_analysis,
    log_summary: captureResult.summary,
    entry_count: captureResult.entries.length,
    exit_code: captureResult.exit_code,
    diagnosis,
    errors,
  }).catch(() => {
    // 会话保存失败不影响主流程
  });

  return {
    log_summary: captureResult.summary,
    session_id: sessionId,
    diagnosis,
    entry_count: captureResult.entries.length,
    error: errors.length > 0 ? errors.join("; ") : undefined,
  };
}

/**
 * 保存会话记录到 debug-sessions/
 */
async function saveSession(
  projectRoot: string,
  sessionId: string,
  data: Record<string, unknown>,
): Promise<void> {
  const sessionsDir = getSessionsDir(projectRoot);
  await mkdir(sessionsDir, { recursive: true });
  const sessionPath = getSessionPath(projectRoot, sessionId);

  // 只保存摘要，不保存完整日志（避免文件过大）
  const sessionData = {
    ...data,
    // 明确排除原始日志条目
    entry_count: data.entry_count,
  };

  await writeFile(sessionPath, JSON.stringify(sessionData, null, 2), "utf-8");
}

/**
 * ListDebugSessions — 列出历史调试会话
 */
export async function ListDebugSessions(
  input: ListDebugSessionsInput = {},
): Promise<ListDebugSessionsOutput> {
  const projectRoot = input.project_root;
  const limit = input.limit ?? 10;

  const dirs = projectRoot
    ? [projectRoot]
    : [process.cwd()];

  const sessions: DebugSessionMeta[] = [];

  for (const dir of dirs) {
    const sessionsDir = getSessionsDir(dir);
    try {
      const files = await readdir(sessionsDir);
      const jsonFiles = files
        .filter((f) => f.endsWith(".json"))
        .sort()
        .reverse()
        .slice(0, limit);

      for (const file of jsonFiles) {
        try {
          const content = await readFile(join(sessionsDir, file), "utf-8");
          const data = JSON.parse(content);
          sessions.push({
            session_id: data.session_id || file.replace(".json", ""),
            project: data.project || dir,
            timestamp: data.timestamp || "",
            error_count: data.log_summary?.stats?.errors ?? 0,
            warning_count: data.log_summary?.stats?.warnings ?? 0,
            status: data.error ? "failed" :
                    (data.log_summary?.stats?.errors ?? 0) > 0 ? "has_errors" : "success",
            has_diagnosis: !!data.diagnosis,
          });
        } catch {
          // 跳过损坏的 session 文件
        }
      }
    } catch {
      // sessionsDir 不存在
    }
  }

  return { sessions: sessions.slice(0, limit) };
}

// ─── 辅助函数 ───

function emptyStats() {
  return {
    stats: { total: 0, errors: 0, warnings: 0, infos: 0, debug: 0 },
    top_errors: [],
    diagnosis_hints: [],
  };
}

/**
 * FormatPipelineState — 将调试结果格式化为 Bobanana 管线 [STATE] 格式
 *
 * 输出格式：
 *   test_coverage: U:N(N%) I:N(N%) S:N(N%)
 *   task_list: 日志捕获✅ 日志解析✅ 输入模拟✅ 调试编排✅ GDScript工具✅
 *
 * 可直接嵌入 queue_next_prompt 的 prompt 参数中。
 */
export function FormatPipelineState(
  moduleResults: Record<string, "done" | "partial" | "pending">,
  testResults?: { u: number; i: number; s: number; a: number },
): string {
  const lines: string[] = [];

  // task_list 部分
  if (Object.keys(moduleResults).length > 0) {
    const taskParts = Object.entries(moduleResults).map(([name, status]) => {
      const icon = status === "done" ? "✅" : status === "partial" ? "⏳" : "⬜";
      return `${name}${icon}`;
    });
    lines.push(`task_list: ${taskParts.join(" ")}`);
  }

  // test_coverage 部分
  if (testResults) {
    const total = testResults.u + testResults.i + testResults.s + testResults.a;
    if (total > 0) {
      const coverage = [
        `U:${testResults.u}/${testResults.u}(100%)`,
        `I:${testResults.i}/${testResults.i}(100%)`,
        `S:${testResults.s}/${testResults.s}(100%)` + (testResults.s > 0 ? "" : "*"),
        `A:${testResults.a}/${testResults.a}(100%)` + (testResults.a > 0 ? "" : "*"),
      ];
      lines.push(`test_coverage: ${coverage.join(" ")}`);
    }
  }

  return lines.join("\n");
}

/**
 * FormatDoneBlock — 输出 Bobanana 标准完成框
 */
export function FormatDoneBlock(
  role: string,
  summary: string,
  nextPhase: string,
): string {
  return [
    `════════════════════════════════════`,
    `${role}完成 · ${summary}`,
    `▶ 终端: reasonix cycle --resume`,
    `════════════════════════════════════`,
  ].join("\n");
}

// ─── CLI ───

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error("用法: npx tsx tools/debug_orchestrator.ts <command> ...");
    console.error("命令:");
    console.error("  run <project_root> [--script <script_id>] [--duration <sec>] [--no-llm]");
    console.error("  analyze <project_root> [--file <path>]");
    console.error("  list [--project <path>]");
    process.exit(1);
  }

  const cmd = args[0];

  if (cmd === "run" && args[1]) {
    const projectRoot = args[1];
    const scriptIdx = args.indexOf("--script");
    const durationIdx = args.indexOf("--duration");
    const noLLM = args.includes("--no-llm");

    const input: DebugSessionInput = {
      project_root: projectRoot,
      duration_sec: durationIdx >= 0 ? parseInt(args[durationIdx + 1]!, 10) : 10,
      llm_analysis: !noLLM,
    };

    if (scriptIdx >= 0 && args[scriptIdx + 1]) {
      // 尝试作为脚本 ID
      input.input_script = args[scriptIdx + 1];
    }

    console.log(`🔍 启动调试会话: ${projectRoot}`);
    if (input.duration_sec) console.log(`⏱  ���行时长: ${input.duration_sec}s`);
    if (input.input_script) console.log(`🎮 输入脚本: ${input.input_script}`);
    console.log("");

    const result = await RunDebugSession(input);

    if (result.error) {
      console.error("⚠️", result.error);
    }

    console.log(`📊 日志摘要:`);
    console.log(`   总计: ${result.log_summary.stats.total} 条`);
    console.log(`   ❌ 错误: ${result.log_summary.stats.errors}`);
    console.log(`   ⚠️  警告: ${result.log_summary.stats.warnings}`);
    console.log(`   🆔 会话 ID: ${result.session_id}`);

    if (result.log_summary.top_errors.length > 0) {
      console.log(`\n🔴 高频错误:`);
      for (const err of result.log_summary.top_errors.slice(0, 5)) {
        console.log(`   ${err.file}:${err.line} (${err.count} 次)`);
      }
    }

    if (result.diagnosis) {
      console.log(`\n🧠 LLM 诊断:`);
      console.log(`   根因: ${result.diagnosis.root_cause}`);
      console.log(`   严重度: ${result.diagnosis.severity}`);
      console.log(`   置信度: ${(result.diagnosis.confidence * 100).toFixed(0)}%`);
      if (result.diagnosis.affected_file) {
        console.log(`   文件: ${result.diagnosis.affected_file}:${result.diagnosis.affected_line ?? "?"}`);
      }
      if (result.diagnosis.suggested_fix) {
        console.log(`   建议: ${result.diagnosis.suggested_fix}`);
      }
    }
  } else if (cmd === "analyze" && args[1]) {
    const projectRoot = args[1];
    const fileIdx = args.indexOf("--file");

    // 读取最近的调试会话日志并重新分析
    const sessions = await ListDebugSessions({ project_root: projectRoot, limit: 1 });
    if (sessions.sessions.length === 0) {
      console.error("❌ 没有找到调试会话记录，请先运行调试会话");
      process.exit(1);
    }

    // 读取会话记录中的日志摘要
    const sessionPath = join(getSessionsDir(projectRoot), sessions.sessions[0]!.session_id + ".json");
    const sessionData = JSON.parse(await readFile(sessionPath, "utf-8"));

    console.log(`🧠 重新分析会话: ${sessions.sessions[0]!.session_id}`);
    console.log(`   项目: ${projectRoot}`);
    if (fileIdx >= 0 && args[fileIdx + 1]) {
      console.log(`   指定文件: ${args[fileIdx + 1]}`);
    }
    console.log("");

    // 构建分析输入
    const relevantFiles = fileIdx >= 0 && args[fileIdx + 1] ? [args[fileIdx + 1]!] : undefined;
    const analysisResult = await AnalyzeLogsWithLLM({
      log_entries: sessionData.log_entries ?? [],
      project_root: projectRoot,
      relevant_files: relevantFiles,
    });

    if (analysisResult.error) {
      console.error("⚠️", analysisResult.error);
    }

    if (analysisResult.diagnosis) {
      console.log(`🧠 诊断结果:`);
      console.log(`   根因: ${analysisResult.diagnosis.root_cause}`);
      console.log(`   严重度: ${analysisResult.diagnosis.severity}`);
      console.log(`   置信度: ${(analysisResult.diagnosis.confidence * 100).toFixed(0)}%`);
      if (analysisResult.diagnosis.affected_file) {
        console.log(`   文件: ${analysisResult.diagnosis.affected_file}:${analysisResult.diagnosis.affected_line ?? "?"}`);
      }
      if (analysisResult.diagnosis.suggested_fix) {
        console.log(`   建议: ${analysisResult.diagnosis.suggested_fix}`);
      }
    } else {
      console.log("ℹ️  无可用的诊断结果");
    }
  } else if (cmd === "list") {
    const projectIdx = args.indexOf("--project");
    const projectRoot = projectIdx >= 0 ? args[projectIdx + 1] : undefined;

    const result = await ListDebugSessions({ project_root: projectRoot });

    if (result.error) {
      console.error("❌", result.error);
      process.exit(1);
    }

    if (result.sessions.length === 0) {
      console.log("ℹ️  没有调试会话记录");
    } else {
      console.log(`📋 调试会话列表:`);
      for (const s of result.sessions) {
        const icon = s.status === "success" ? "✅" : s.status === "has_errors" ? "🔴" : "❌";
        console.log(`   ${icon} ${s.session_id}`);
        console.log(`       项目: ${s.project}`);
        console.log(`       时间: ${s.timestamp}`);
        console.log(`       错误: ${s.error_count}, 警告: ${s.warning_count}`);
        if (s.has_diagnosis) console.log(`       诊断: 有`);
        console.log("");
      }
    }
  } else {
    console.error("未知命令或参数不足");
    process.exit(1);
  }
}

if (process.argv[1]?.endsWith("debug_orchestrator.ts")) {
  main().catch((err) => {
    console.error("❌ 意外错误:", err);
    process.exit(1);
  });
}
