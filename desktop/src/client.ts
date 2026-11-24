/**
 * 最小 fetch 封装 — Q2-M2-D 临时层。
 * M2-A 的 src/api/ 合并后应替换为从 @/api 导入的客户端；本文件只做三件事：
 * 1. 统一 base URL（开发经 vite proxy 反代到 8618，生产用相对路径）；
 * 2. 统一 JSON 解析与错误抛出（非 2xx 抛 ApiError）；
 * 3. 提供类型化的薄方法，返回后端真实形状（字段与 src/dexatlas/api/app.py 对齐）。
 * 注意：类型为局部定义，字段以后端为准；不编造后端没有的能力。
 */

/** 后端返回的项目条目（GET /api/projects、GET /api/projects/{id} 的 project 字段） */
export interface ProjectInfo {
  id: string;
  apk_name: string;
  apk_sha256: string;
  status: "pending" | "running" | "completed" | "failed" | string;
  created_at: string;
  class_count: number;
  method_count: number;
  call_site_count: number;
  call_edge_count: number;
  evidence_count: number;
  missing_backends: string[];
  truncated: boolean;
}

/** GET /api/projects/{id} 的完整返回 */
export interface ProjectDetailResponse {
  project: ProjectInfo;
  completeness: {
    complete: boolean;
    missing_backends: string[];
    truncated: boolean;
    errors: BackendError[];
  };
  published_run: RunInfo | null;
  runs: RunInfo[];
}

/** 分析轮次 */
export interface RunInfo {
  id: string;
  status: string;
  completeness: "complete" | "partial" | string;
  tool_versions: Record<string, string | null>;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
}

/** 后端错误（partial 状态横幅的数据来源） */
export interface BackendError {
  tool: string;
  code: string;
  message: string;
  detail?: string | null;
}

/** 证据记录（GET /api/projects/{id}/evidence 的 evidence[] 元素） */
export interface EvidenceRecord {
  id: string;
  kind: "observation" | "declaration" | "cross_reference" | "code_located" | "behaviour" | string;
  level: string;
  summary: string;
  detail: Record<string, unknown>;
  /** 形如 "jadx:sources/a/Foo.java" 或 "androguard:classes.dex#..." 的 locator 串 */
  provenance: string[];
}

/** 符号搜索结果（GET /api/projects/{id}/symbols） */
export interface SymbolHit {
  kind: string;
  name: { text: string };
  detail: { text: string } | null;
  provenance: unknown[];
}

/** locator 解析结果（GET /api/projects/{id}/locators/resolve） */
export interface LocatorResolution {
  resolved: boolean;
  /** 已解析时为机器路径或人读说明；未解析时为原因 */
  reason: string | null;
  kind: string | null;
  text: { text: string; truncated: boolean } | null;
  provenance: string[];
}

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* body 非 JSON 时保留状态行 */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const client = {
  listProjects: () => request<{ projects: ProjectInfo[] }>("/projects").then((d) => d.projects),

  getProject: (id: string) => request<ProjectDetailResponse>(`/projects/${encodeURIComponent(id)}`),

  getEvidence: (id: string) =>
    request<EvidenceRecord[]>(`/projects/${encodeURIComponent(id)}/evidence`),

  /** 符号全文搜索（索引：类/方法/字段） */
  searchSymbols: (id: string, q: string, limit = 50) =>
    request<{ symbols: SymbolHit[] }>(
      `/projects/${encodeURIComponent(id)}/symbols?q=${encodeURIComponent(q)}&limit=${limit}`,
    ).then((d) => d.symbols),

  /** locator 解析：返回真实机器路径或解析说明 */
  resolveLocator: (id: string, locator: string) =>
    request<LocatorResolution>(
      `/projects/${encodeURIComponent(id)}/locators/resolve?locator=${encodeURIComponent(locator)}`,
    ),

  /** 报告导出：返回原始文本（markdown/json），由调用方触发下载 */
  getReport: async (id: string, format: "markdown" | "json"): Promise<string> => {
    const res = await fetch(
      `${BASE}/projects/${encodeURIComponent(id)}/report?format=${format}`,
    );
    if (!res.ok) throw new ApiError(res.status, `报告导出失败：${res.status} ${res.statusText}`);
    return res.text();
  },
};

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
