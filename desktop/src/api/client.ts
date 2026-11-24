/**
 * DexAtlas REST API 客户端 — Q2-M2-A。
 *
 * 基于 fetch 的薄封装：统一 baseURL、JSON 解析和错误处理。所有方法返回
 * 解析后的数据，失败时抛出 {@link ApiError}（网络错误、非 2xx、JSON 损坏
 * 都归一为它），调用方只需 catch 一种错误类型。
 *
 * dev 模式下 baseURL 默认为 ``/api``，由 vite 代理转发到后端
 * （见 vite.config.ts）；生产/Tauri 打包后可传入完整地址。
 *
 * 后端差异说明：当前 8618 运行的是 workbench 应用，其 /api/projects 返回
 * ``{projects, total, offset, limit}`` 分页信封；api/app.py 契约则是裸数组。
 * listProjects 对两者做了归一化，其余端点按 api/app.py 契约直读。
 */

import type {
  AnalyzeJob,
  BackendInfo,
  CancelResponse,
  EvidenceList,
  HealthInfo,
  ProjectDetail,
  ProjectSummary,
  ReportFormat,
  ReportPayload,
  RunInfo,
  RunList,
} from "./types";

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

/** 从 FastAPI 的错误体里抠出一句人能读的话。 */
function messageFromDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  // 422 校验错误：detail 是 {loc, msg, type} 数组
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (first && typeof first.msg === "string") {
      return first.msg;
    }
  }
  return fallback;
}

export class DexAtlasClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: DexAtlasClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "/api").replace(/\/+$/, "");
    this.fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);
  }

  // -------------------------------------------------------------------------
  // 分析
  // -------------------------------------------------------------------------

  /**
   * 上传 APK 并在后台分析。返回 202 任务；同 hash 已分析过时后端直接返回
   * 已有项目。完成与否需轮询 {@link getProject} 的 status。
   */
  async analyzeUpload(file: File | Blob, filename?: string): Promise<AnalyzeJob> {
    const form = new FormData();
    form.append("file", file, filename ?? (file instanceof File ? file.name : "upload.apk"));
    return this.request<AnalyzeJob>("/analyze", { method: "POST", body: form });
  }

  /** 项目列表，新→旧。 */
  async listProjects(): Promise<ProjectSummary[]> {
    const raw = await this.request<unknown>("/projects");
    // api/app.py 契约是 ProjectResponse[]；workbench 是 {projects: [...]} 分页信封。
    if (Array.isArray(raw)) {
      return raw as ProjectSummary[];
    }
    if (raw && typeof raw === "object" && Array.isArray((raw as { projects?: unknown }).projects)) {
      return (raw as { projects: ProjectSummary[] }).projects;
    }
    throw new ApiError("/projects 返回了无法识别的形状", undefined, raw);
  }

  /** 一个项目的元数据、计数与后端错误。 */
  async getProject(projectId: string): Promise<ProjectDetail> {
    return this.request<ProjectDetail>(`/projects/${encodeURIComponent(projectId)}`);
  }

  /** 项目全部分析轮次，新→旧，含 published 标记。 */
  async getRuns(projectId: string): Promise<RunList> {
    return this.request<RunList>(`/projects/${encodeURIComponent(projectId)}/runs`);
  }

  /** 单个轮次。 */
  async getRun(projectId: string, runId: string): Promise<RunInfo> {
    return this.request<RunInfo>(
      `/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}`,
    );
  }

  /** 请求取消正在运行的分析（202 表示已受理，不表示已停止）。 */
  async cancelProject(projectId: string): Promise<CancelResponse> {
    return this.request<CancelResponse>(`/projects/${encodeURIComponent(projectId)}/cancel`, {
      method: "POST",
    });
  }

  /** 项目的全部证据记录，各带来源工具、版本与 locator。 */
  async getEvidence(projectId: string): Promise<EvidenceList> {
    return this.request<EvidenceList>(`/projects/${encodeURIComponent(projectId)}/evidence`);
  }

  /**
   * 导出报告。format=markdown 返回文本；format=json 返回结构化对象。
   */
  async getReport(projectId: string, format: ReportFormat = "json"): Promise<ReportPayload> {
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
  // 元信息
  // -------------------------------------------------------------------------

  /** 存活与后端就绪状态。 */
  async getHealth(): Promise<HealthInfo> {
    return this.request<HealthInfo>("/health");
  }

  /** 装了哪些分析后端、缺哪些、版本几何。 */
  async getBackends(): Promise<BackendInfo> {
    return this.request<BackendInfo>("/backends");
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
      response = await this.fetchImpl(`${this.baseUrl}${path}`, init);
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
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = undefined;
    }
    throw new ApiError(
      messageFromDetail(
        (detail as { detail?: unknown } | null)?.detail ?? detail,
        `请求失败（HTTP ${response.status}）`,
      ),
      response.status,
      detail,
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
