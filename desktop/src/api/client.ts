/**
 * DexAtlas REST API 客户端 — Q2-M3-T1 统一层。
 *
 * 基于 fetch 的薄封装：统一 baseURL、JSON 解析和错误处理。所有方法返回
 * 解析后的数据，失败时抛出 {@link ApiError}（网络错误、非 2xx、JSON 损坏
 * 都归一为它），调用方只需 catch 一种错误类型。
 *
 * dev 模式下 baseURL 默认为 ``/api``，由 vite 代理转发到后端
 * （见 vite.config.ts）；生产/Tauri 打包后可传入完整地址。
 *
 * 后端差异说明（Q2-M3-T1 按 8618 workbench 实测核对，src/dexatlas/workbench/app.py）：
 * - GET /api/projects 返回 ``{projects, total, offset, limit}`` 分页信封
 *   （mcp/schemas.py:128 ProjectList）；listProjects 对此归一化为数组。
 * - GET /api/projects/{id} 返回 ProjectStatus 信封
 *   （mcp/schemas.py:166：{project, completeness, published_run, runs,
 *   evidence_catalog}）；getProject 返回该信封原样。
 * - GET /api/projects/{id}/evidence 返回裸数组（workbench app.py:209），
 *   getEvidence 归一化为 {project_id, total, evidence}。
 * - workbench 自 PR #5 起提供 GET /api/projects/{id}/runs（信封
 *   {project_id, total, published_run_id, runs: [... & {published}]}）与
 *   /cancel；仍没有 /api/backends：getBackends 会得到 404，调用方按
 *   "后端未提供"如实处理。
 * - 错误体是 MCP RequestError 的 as_dict（mcp/errors.py:27）：
 *   {code, message, detail}，HTTP 404=unknown_project、400=其余请求错误。
 */

import type {
  AnalyzeAccepted,
  AnalyzeJob,
  BackendInfo,
  CancelResponse,
  EvidenceList,
  EvidenceRecord,
  LocatorResolution,
  ProjectDetailEnvelope,
  ProjectSummary,
  ReportFormat,
  RunInfo,
  RunsEnvelope,
  SymbolHit,
  WorkbenchHealth,
} from "./types";

/**
 * Tauri 发布形态下的后端访问适配（X2-P1）。
 *
 * 打包后的 exe 运行在 tauri://localhost（生产 origin），而 workbench 后端
 * 在 http://127.0.0.1:8618 且不带 CORS 头，浏览器环境直接 fetch 会被 CORS
 * 拦截（X2 走查 CDP 实测 MissingAllowOriginHeader）。Tauri 环境下改用
 * @tauri-apps/plugin-http 的 fetch：请求走 Rust 侧 HTTP 插件发出，不受
 * WebKit/CORS 约束（capability 已放行 8618）。dev / 浏览器环境保持原生
 * fetch（vite 代理转发）。
 */
const TAURI_FETCH = import("@tauri-apps/plugin-http").then(
  (m) => m.fetch as typeof fetch,
);

/** 是否运行在 Tauri WebView 内（dev 窗口与发布 exe 都算）。 */
function isTauriRuntime(): boolean {
  return (
    typeof window !== "undefined" &&
    "__TAURI_INTERNALS__" in window
  );
}

/** 按运行环境取 fetch 实现；Tauri 下惰性加载 plugin-http。 */
function resolveFetch(): Promise<typeof fetch> {
  if (isTauriRuntime()) {
    return TAURI_FETCH;
  }
  return Promise.resolve(fetch.bind(globalThis));
}

/** 客户端可调的统一错误。status 为 undefined 表示请求根本没到服务器。 */
export class ApiError extends Error {
  readonly status?: number;
  /** 后端返回的原始 detail（FastAPI 的 HTTPException.detail），可能带结构 */
  readonly detail?: unknown;

  constructor(message: string, status?: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export interface DexAtlasClientOptions {
  /** API 基地址，默认 "/api"（dev 下走 vite 代理）。也可传完整 URL。 */
  baseUrl?: string;
  /** 自定义 fetch（测试注入用），默认全局 fetch */
  fetchImpl?: typeof fetch;
}

/** 从后端错误体里抠出一句人能读的话（兼容 FastAPI detail 与 MCP {code,message}）。 */
function messageFromBody(body: unknown, statusText: string): string {
  if (body && typeof body === "object") {
    const obj = body as { message?: unknown; detail?: unknown };
    if (typeof obj.message === "string" && obj.message.trim()) {
      return obj.message;
    }
    if (typeof obj.detail === "string" && obj.detail.trim()) {
      return obj.detail;
    }
    // FastAPI 422 校验错误：detail 是 {loc, msg, type} 数组
    if (Array.isArray(obj.detail) && obj.detail.length > 0) {
      const first = obj.detail[0] as { msg?: unknown };
      if (first && typeof first.msg === "string") {
        return first.msg;
      }
    }
  }
  return statusText;
}

/**
 * 把任意抛出的错误转成一句人能读的话（不展示给最终用户的原始前缀）。
 *
 * 验收报告 T2-A9 遗留项：网络层失败的 fetch TypeError 会把 `undefined:`
 * 拼进 message（如 "undefined: Failed to fetch"），ApiError 构造时又拼了
 * baseURL，直接展示很费解。这里按错误类别给出中文说明，并保留原始
 * message 作为附注；HTTP 状态码在 statusText 里另配一句语义说明。
 */
export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    const statusNote =
      err.status === undefined
        ? "无法连接后端（网络错误或服务未启动）"
        : `请求失败（HTTP ${err.status}）`;
    const raw = err.message.trim();
    // HTTP 错误体已有可读 message 时直接用它；网络错误则用中文说明 + 原始附注
    const readable =
      err.status !== undefined && raw && !raw.startsWith("undefined")
        ? raw
        : `${statusNote}${raw && raw !== "undefined" ? `（${raw}）` : ""}`;
    return readable;
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message;
  }
  return String(err);
}

export class DexAtlasClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: Promise<typeof fetch>;

  constructor(options: DexAtlasClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "/api").replace(/\/+$/, "");
    this.fetchImpl = options.fetchImpl
      ? Promise.resolve(options.fetchImpl)
      : resolveFetch();
  }

  // -------------------------------------------------------------------------
  // 分析
  // -------------------------------------------------------------------------

  /**
   * 上传 APK 并在后台分析（workbench POST /api/analyze，202）。
   * 同 hash 已分析过时后端直接返回已有项目（already_analysed=true）。
   * 完成与否需轮询 {@link getProject} 的 status。
   */
  async analyzeUpload(file: File | Blob, filename?: string): Promise<AnalyzeAccepted> {
    const form = new FormData();
    form.append("file", file, filename ?? (file instanceof File ? file.name : "upload.apk"));
    return this.request<AnalyzeAccepted>("/analyze", { method: "POST", body: form });
  }

  /**
   * 项目列表，新→旧。workbench 的分页信封（{projects,...}）归一化为数组；
   * api/app.py 的裸数组契约同样兼容。
   */
  async listProjects(): Promise<ProjectSummary[]> {
    const raw = await this.request<unknown>("/projects?limit=50");
    if (Array.isArray(raw)) {
      return raw as ProjectSummary[];
    }
    if (raw && typeof raw === "object" && Array.isArray((raw as { projects?: unknown }).projects)) {
      return (raw as { projects: ProjectSummary[] }).projects;
    }
    throw new ApiError("/projects 返回了无法识别的形状", undefined, raw);
  }

  /**
   * 项目状态信封：{project, completeness, published_run, runs, evidence_catalog}。
   * workbench GET /api/projects/{id} 的原样返回。
   */
  async getProject(projectId: string): Promise<ProjectDetailEnvelope> {
    return this.request<ProjectDetailEnvelope>(`/projects/${encodeURIComponent(projectId)}`);
  }

  // -------------------------------------------------------------------------
  // 证据与符号
  // -------------------------------------------------------------------------

  /**
   * 项目的全部证据记录，各带 provenance locator。
   * workbench 返回裸数组；这里归一化为 {project_id, total, evidence}，
   * 与 api/app.py 的 EvidenceList 契约对齐，页面只需读 .evidence。
   */
  async getEvidence(projectId: string): Promise<EvidenceList> {
    const raw = await this.request<unknown>(`/projects/${encodeURIComponent(projectId)}/evidence`);
    const evidence = Array.isArray(raw)
      ? (raw as EvidenceRecord[])
      : Array.isArray((raw as { evidence?: unknown } | null)?.evidence)
        ? ((raw as { evidence: EvidenceRecord[] }).evidence)
        : null;
    if (evidence === null) {
      throw new ApiError("/evidence 返回了无法识别的形状", undefined, raw);
    }
    return { project_id: projectId, total: evidence.length, evidence };
  }

  /** 索引全文搜索（类/方法/字段/字符串），返回命中符号列表。 */
  async searchSymbols(projectId: string, q: string, limit = 50): Promise<SymbolHit[]> {
    const data = await this.request<{ symbols: SymbolHit[] }>(
      `/projects/${encodeURIComponent(projectId)}/symbols?q=${encodeURIComponent(q)}&limit=${limit}`,
    );
    return data.symbols;
  }

  /** locator 解析：返回真实机器路径或解析说明（workbench app.py:231）。 */
  async resolveLocator(projectId: string, locator: string): Promise<LocatorResolution> {
    return this.request<LocatorResolution>(
      `/projects/${encodeURIComponent(projectId)}/locators/resolve?locator=${encodeURIComponent(locator)}`,
    );
  }

  // -------------------------------------------------------------------------
  // 报告
  // -------------------------------------------------------------------------

  /**
   * 导出报告。format=markdown 返回文本；format=json 返回结构化对象。
   * 两个后端（workbench / api）对该端点的契约一致。
   */
  async getReport(projectId: string, format: ReportFormat = "json"): Promise<string | Record<string, unknown>> {
    const response = await this.raw(
      `/projects/${encodeURIComponent(projectId)}/report?format=${encodeURIComponent(format)}`,
    );
    await this.ensureOk(response);
    if (format === "markdown") {
      return response.text();
    }
    return this.parseJson(response);
  }

  // -------------------------------------------------------------------------
  // 元信息与控制
  // -------------------------------------------------------------------------

  /** 存活与版本（workbench 返回 {version, workspace}）。 */
  async getHealth(): Promise<WorkbenchHealth> {
    return this.request<WorkbenchHealth>("/health");
  }

  /**
   * 装了哪些分析后端。仅 api/app.py:349 提供该端点；workbench 没有，
   * 调用方会把 404 当作"后端未提供该端点"如实展示。
   */
  async getBackends(): Promise<BackendInfo> {
    return this.request<BackendInfo>("/backends");
  }

  /** 请求取消正在运行的分析（202 表示已受理）。workbench 未提供（405）。 */
  async cancelProject(projectId: string): Promise<CancelResponse> {
    return this.request<CancelResponse>(`/projects/${encodeURIComponent(projectId)}/cancel`, {
      method: "POST",
    });
  }

  /** 兼容旧调用点：按 id 读取分析任务（api/app.py 契约；workbench 无此端点）。 */
  async getAnalyzeJob(projectId: string): Promise<AnalyzeJob> {
    return this.request<AnalyzeJob>(`/analyze/${encodeURIComponent(projectId)}`);
  }

  /**
   * 项目的全部分析轮次，新→旧，并标注哪一轮是已发布快照。
   * workbench GET /api/projects/{id}/runs（PR #5 起）：信封
   * {project_id, total, published_run_id, runs: [RunSummary & {published}]}；
   * api/app.py 契约的裸数组同样兼容（旧后端无 published 字段）。
   */
  async getRuns(projectId: string): Promise<RunsEnvelope> {
    const raw = await this.request<unknown>(`/projects/${encodeURIComponent(projectId)}/runs`);
    if (Array.isArray(raw)) {
      return { project_id: projectId, total: raw.length, published_run_id: null, runs: raw as RunInfo[] };
    }
    if (raw && typeof raw === "object" && Array.isArray((raw as { runs?: unknown }).runs)) {
      return raw as RunsEnvelope;
    }
    throw new ApiError(`/projects/${projectId}/runs 返回了无法识别的形状`, undefined, raw);
  }

  // -------------------------------------------------------------------------
  // 内部：请求与错误归一
  // -------------------------------------------------------------------------

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await this.raw(path, init);
    await this.ensureOk(response);
    return this.parseJson<T>(response);
  }

  private async raw(path: string, init?: RequestInit): Promise<Response> {
    let response: Response;
    try {
      response = await (await this.fetchImpl)(`${this.baseUrl}${path}`, init);
    } catch (cause) {
      // fetch 只在网络层失败时 reject（断连、DNS、CORS 等）
      throw new ApiError(
        `无法连接 DexAtlas 后端（${this.baseUrl}${path}）：${String(cause)}`,
        undefined,
        cause,
      );
    }
    return response;
  }

  private async ensureOk(response: Response): Promise<void> {
    if (response.ok) {
      return;
    }
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw new ApiError(
      messageFromBody(body, `请求失败（HTTP ${response.status}）`),
      response.status,
      body,
    );
  }

  private async parseJson<T>(response: Response): Promise<T> {
    try {
      return (await response.json()) as T;
    } catch (cause) {
      throw new ApiError("后端返回了无法解析的 JSON", response.status, cause);
    }
  }
}

/** 默认客户端实例。页面组件可直接 import 使用；需要定制时再 new。 */
export const dexatlas = new DexAtlasClient();

/** 触发浏览器下载（Blob + a[download]）。 */
export function downloadText(filename: string, text: string, mime: string): void {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
