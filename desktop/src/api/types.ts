/**
 * DexAtlas REST API 类型 — Q2-M3-T1 按 8618 workbench 实测契约对齐。
 *
 * 字段名保留后端 snake_case 原样，不做 camelCase 改写，保证和 JSON 响应
 * 一一对应、调试时可直接对照。
 *
 * 对齐来源（2026-11-24 用 8618 实测响应 + 源码核对）：
 * - ProjectSummary / RunSummary / Completeness ← src/dexatlas/mcp/schemas.py
 *   （ProjectList:128、RunSummary:139、ProjectStatus:166、Completeness:68）
 * - ProjectDetailEnvelope ← GET /api/projects/{id}（workbench app.py:124，
 *   实际调用 mcp/tools/projects.py project_status）
 * - EvidenceRecord ← EvidenceView（schemas.py:417），GET /evidence 返回裸数组
 * - SymbolHit ← SymbolView（schemas.py:230），name/detail 是 {text, notice}
 * - LocatorResolution ← schemas.py:429
 * - WorkbenchHealth ← workbench app.py:101（{version, workspace}）
 * - AnalyzeAccepted ← workbench app.py:249 UploadAccepted
 *
 * 与 api/app.py 契约的差异在 client.ts 归一化，切换后端时无需改类型。
 */

// ---------------------------------------------------------------------------
// 项目
// ---------------------------------------------------------------------------

/** workbench ProjectSummary.status（core/models.py:748 ProjectState 的值） */
export type ProjectStatus = "pending" | "running" | "completed" | "failed";

/** mcp/schemas.py:93 ProjectSummary — 一个已分析 APK 的概要 */
export interface ProjectSummary {
  id: string;
  apk_name: string;
  apk_sha256: string;
  status: ProjectStatus | string;
  created_at: string;
  class_count: number;
  method_count: number;
  /** 索引里的调用点数：一个字节码位置记一条（schemas.py:113） */
  call_site_count: number;
  /** 索引里的调用边数：两个方法之间的一条关系记一条（schemas.py:116） */
  call_edge_count: number;
  evidence_count: number;
  missing_backends: string[];
  truncated: boolean;
}

/** runs.py RunStage — pipeline 的阶段推进点（Phase 5 W2 起随 run 返回） */
export type RunStage =
  | "inspect"
  | "parse-apktool"
  | "index-androguard"
  | "decompile-jadx"
  | "publish";

/** runs.py RunStageEvent — 一次进入/离开某阶段的事件 */
export interface RunStageEvent {
  stage: RunStage | string;
  started_at: string;
  /** null = 阶段尚未结束（含中途失败/取消） */
  finished_at: string | null;
}

/** mcp/schemas.py:139 RunSummary — 一次分析尝试 */
export interface RunInfo {
  id: string;
  status: string;
  completeness: "complete" | "partial" | string;
  tool_versions: Record<string, string | null>;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  /** workbench PR #5 起附加：该轮是否为项目当前发布的快照 */
  published?: boolean;
  /** Phase 5 W2 起随 run 返回的 pipeline 阶段事件；空数组 = 无阶段事实 */
  stages?: RunStageEvent[];
}

/** workbench GET /api/projects/{id}/runs 的响应信封（app.py list_runs） */
export interface RunsEnvelope {
  project_id: string;
  total: number;
  published_run_id: string | null;
  runs: RunInfo[];
}

/**
 * Phase 5 W2 独立只读端点 GET …/runs/{run_id}/stages 的响应。
 * run 详情对象不带 stages；阶段事实从该端点取。
 */
export interface RunStagesEnvelope {
  project_id: string;
  run_id: string;
  run_status: string;
  stages: RunStageEvent[];
}

/**
 * mcp/schemas.py:68 Completeness.errors — workbench 实际返回字符串数组
 * （mcp/tools/projects.py:106 把 ToolError 格式化为 "tool: message"）。
 * 历史响应可能仍是对象数组，页面侧做两种形状的兼容。
 */
export type CompletenessError = string | { tool: string; code?: string; message: string };

/** mcp/schemas.py:68 Completeness — 一次分析读到了什么、没读到什么 */
export interface Completeness {
  complete: boolean;
  missing_backends: string[];
  truncated: boolean;
  errors: CompletenessError[];
}

/** mcp/schemas.py:166 ProjectStatus — GET /api/projects/{id} 的完整信封 */
export interface ProjectDetailEnvelope {
  project: ProjectSummary;
  completeness: Completeness;
  published_run: RunInfo | null;
  runs: RunInfo[];
  /** 每条 {id, kind, summary}，指向 /evidence 里的完整记录 */
  evidence_catalog?: Array<{ id: string; kind: string; summary: string }>;
}

// ---------------------------------------------------------------------------
// 分析任务
// ---------------------------------------------------------------------------

/** workbench app.py:249 UploadAccepted — POST /api/analyze 的 202 响应 */
export interface AnalyzeAccepted {
  project_id: string;
  status: string;
  apk_sha256: string;
  /** 工作台已持有该 APK 的分析：没有新任务在跑，可直接打开项目 */
  already_analysed: boolean;
}

/** api/app.py 契约的 202 任务（workbench 无此形状；保留给 getAnalyzeJob） */
export interface AnalyzeJob {
  project_id: string;
  status: string;
  detail: string;
}

// ---------------------------------------------------------------------------
// 证据
// ---------------------------------------------------------------------------

/** EvidenceView.kind（core/models.py:506 EvidenceKind 的值） */
export type EvidenceKind =
  | "code_located"
  | "cross_reference"
  | "declaration"
  | "behaviour"
  | "observation";

/** EvidenceView.level（core/models.py:537 EvidenceLevel 的值） */
export type EvidenceLevel = "verified" | "lead" | "insufficient";

/** mcp/schemas.py:417 EvidenceView — 一条证据与其 provenance locator 串 */
export interface EvidenceRecord {
  id: string;
  kind: EvidenceKind | string;
  level: EvidenceLevel | string;
  summary: string;
  detail: Record<string, unknown>;
  /** 形如 "jadx:sources/a/Foo.java" 的 locator 串（schemas.py:425） */
  provenance: string[];
}

/** getEvidence 的归一化返回：workbench 裸数组 → 与 api/app.py 对齐的信封 */
export interface EvidenceList {
  project_id: string;
  total: number;
  evidence: EvidenceRecord[];
}

// ---------------------------------------------------------------------------
// 符号与 locator
// ---------------------------------------------------------------------------

/** UntrustedText（schemas.py:40 附近）— 从 APK 读出的文本，包一层 notice */
export interface UntrustedText {
  text: string;
  notice?: string;
  bytes?: number;
  truncated?: boolean;
}

/** mcp/schemas.py:230 SymbolView — 索引里的一个符号命中 */
export interface SymbolHit {
  kind: string;
  name: UntrustedText;
  detail: UntrustedText | null;
  provenance: string[];
}

/** mcp/schemas.py:429 LocatorResolution — 一个 locator 的解析结果 */
export interface LocatorResolution {
  resolved: boolean;
  /** 为什么解析/未解析，后端原话 */
  reason: string;
  kind: "java" | "smali" | null;
  text: UntrustedText | null;
  provenance: string[];
}

// ---------------------------------------------------------------------------
// 元信息与控制
// ---------------------------------------------------------------------------

/** workbench app.py:101 GET /api/health — 版本与工作区名（不含后端清单） */
export interface WorkbenchHealth {
  version: string;
  workspace: string;
}

/** api/app.py 契约的 health（workbench 不返回 status/backends 字段） */
export interface HealthInfo extends WorkbenchHealth {
  status?: string;
  backends?: Record<string, string | null>;
}

/** GET /api/backends（api/app.py:349）— workbench 未提供该端点 */
export interface BackendInfo {
  available: string[];
  missing: string[];
  versions: Record<string, string | null>;
}

/** POST /api/projects/{id}/cancel 的 202 响应（api/app.py 契约；workbench 405） */
export interface CancelResponse {
  project_id: string;
  status: "cancelling";
}

/** 报告导出格式（两个后端一致，workbench app.py:300） */
export type ReportFormat = "markdown" | "json";
