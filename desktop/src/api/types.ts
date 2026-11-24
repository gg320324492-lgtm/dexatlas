/**
 * DexAtlas REST API 类型 — 与 src/dexatlas/api/app.py 的响应模型逐字段对齐。
 *
 * 字段名保留后端 snake_case 原样，不做 camelCase 改写，保证和 JSON 响应
 * 一一对应、调试时可直接对照。
 *
 * 对齐来源（2026-11-24 核对）：
 * - ProjectSummary / ProjectDetail ← ProjectResponse（app.py:188）
 * - AnalyzeJob ← AnalyzeJobResponse（app.py:223）
 * - RunInfo ← RunResponse（app.py:229）
 * - Evidence / Provenance ← core/models.py 的 Evidence（models.py:574）与
 *   Provenance（models.py:142），即 /projects/{id}/evidence 的 model_dump 输出
 * - HealthInfo ← HealthResponse（app.py:175）
 * - BackendInfo ← GET /api/backends（app.py:349）的 dict 形状
 * - 枚举值 ← core/models.py 的 ProjectStatus / EvidenceKind / EvidenceLevel /
 *   ToolErrorCode 与 core/runs.py 的 RunStatus / RunCompleteness
 *
 * 注意：当前 8618 端口实际运行的是 workbench 应用（src/dexatlas/workbench/app.py），
 * 其 /api/health 与 /api/projects 的形状和 api/app.py 不同（workbench 的
 * /api/projects 返回 {projects, total, offset, limit} 分页信封，且没有
 * /runs、/backends、/cancel 端点）。本文件的类型以 api/app.py 契约为准；
 * client.ts 对两种真实响应做了归一化，切换后端时无需改类型。
 */

// ---------------------------------------------------------------------------
// 共享：后端失败是值，不是异常（core/models.py:55 ToolError）
// ---------------------------------------------------------------------------

/** ToolErrorCode（core/models.py:34） */
export type ToolErrorCode =
  | "not_installed"
  | "timeout"
  | "exit_nonzero"
  | "parse_error"
  | "unsupported"
  | "output_truncated"
  | "analysis_failed";

/** ErrorResponse（app.py:181）— 已按工作区脱敏的后端失败记录 */
export interface ToolErrorInfo {
  tool: string;
  code: ToolErrorCode;
  message: string;
  detail?: string | null;
}

// ---------------------------------------------------------------------------
// 项目
// ---------------------------------------------------------------------------

/** ProjectStatus（core/models.py:748） */
export type ProjectStatus = "pending" | "running" | "completed" | "failed";

/**
 * ProjectResponse（app.py:188）— 列表与详情共用同一模型。
 * 列表 GET /api/projects 返回 ProjectResponse[]（新→旧）。
 */
export interface ProjectSummary {
  id: string;
  status: ProjectStatus;
  apk_sha256: string;
  /** 被分析 APK 的文件名（服务端目录布局不发布，见 app.py:192 的字段说明） */
  apk_path: string;
  apk_size_bytes: number;
  class_count: number;
  method_count: number;
  /** 索引里的调用点数（app.py:201） */
  reference_count: number;
  /** 与 reference_count 同值，报告/MCP 侧的叫法（app.py:205） */
  call_site_count: number;
  /** 索引里的调用边数：两个方法之间的一条关系记一条（app.py:213） */
  call_edge_count: number;
  evidence_count: number;
  resource_count: number;
  tool_versions: Record<string, string | null>;
  errors: ToolErrorInfo[];
}

/** 项目详情 — 后端与列表同形（GET /api/projects/{id}，app.py:408） */
export interface ProjectDetail extends ProjectSummary {}

// ---------------------------------------------------------------------------
// 分析任务
// ---------------------------------------------------------------------------

/** AnalyzeJobResponse（app.py:223）— POST /api/analyze 的 202 响应 */
export interface AnalyzeJob {
  project_id: string;
  status: string;
  /** 去哪里轮询完成状态 */
  detail: string;
}

// ---------------------------------------------------------------------------
// 分析轮次
// ---------------------------------------------------------------------------

/** RunStatus（core/runs.py:52） */
export type RunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

/** RunCompleteness（core/runs.py:75） */
export type RunCompleteness = "complete" | "partial";

/** RunResponse（app.py:229）— 一次分析尝试 */
export interface RunInfo {
  id: string;
  project_id: string;
  status: RunStatus;
  completeness: RunCompleteness;
  apk_sha256: string;
  tool_versions: Record<string, string | null>;
  errors: ToolErrorInfo[];
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  /** 这一轮的结果是否就是项目当前发布的结果（app.py:249） */
  published: boolean;
}

/** GET /api/projects/{id}/runs 的响应（app.py:417） */
export interface RunList {
  project_id: string;
  total: number;
  published_run_id: string | null;
  runs: RunInfo[];
}

// ---------------------------------------------------------------------------
// 证据
// ---------------------------------------------------------------------------

/** Provenance（core/models.py:142）— 一个事实来自哪里 */
export interface Provenance {
  tool: string;
  tool_version?: string | null;
  apk_sha256: string;
  /** 形如 ``<tool>:<place>``，place 相对工具产物树（见 models.py:150 注释） */
  locator: string;
}

/** EvidenceKind（core/models.py:506） */
export type EvidenceKind =
  | "code_located"
  | "cross_reference"
  | "declaration"
  | "behaviour"
  | "observation";

/** EvidenceLevel（core/models.py:537） */
export type EvidenceLevel = "verified" | "lead" | "insufficient";

/** Evidence（core/models.py:574）— 一条可溯源的观察 */
export interface Evidence {
  id: string;
  kind: EvidenceKind;
  level: EvidenceLevel;
  summary: string;
  detail: Record<string, unknown>;
  provenance: Provenance[];
}

/** GET /api/projects/{id}/evidence 的响应（app.py:795） */
export interface EvidenceList {
  project_id: string;
  total: number;
  evidence: Evidence[];
}

// ---------------------------------------------------------------------------
// 元信息
// ---------------------------------------------------------------------------

/** HealthResponse（app.py:175）— GET /api/health */
export interface HealthInfo {
  status: string;
  version: string;
  /** 各后端版本；不可用的后端为 null */
  backends: Record<string, string | null>;
}

/** GET /api/backends（app.py:349）— 装了哪些分析后端 */
export interface BackendInfo {
  available: string[];
  missing: string[];
  versions: Record<string, string | null>;
}

// ---------------------------------------------------------------------------
// 取消与报告
// ---------------------------------------------------------------------------

/** POST /api/projects/{id}/cancel 的 202 响应（app.py:452） */
export interface CancelResponse {
  project_id: string;
  status: "cancelling";
}

/** 报告导出格式（app.py:810，query 参数 format） */
export type ReportFormat = "markdown" | "json";

/** getReport 的返回：markdown 是文本，json 是任意结构 */
export type ReportPayload = string | Record<string, unknown>;
