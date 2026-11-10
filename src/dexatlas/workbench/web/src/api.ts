// The shapes the MCP contract returns, as the browser sees them. They mirror
// the pydantic models in dexatlas.mcp.schemas; the workbench is a view over
// that contract and adds no fields of its own.

export interface ProjectSummary {
  id: string;
  apk_name: string;
  apk_sha256: string;
  status: string;
  created_at: string;
  class_count: number;
  method_count: number;
  call_site_count: number;
  call_edge_count: number;
  evidence_count: number;
  missing_backends: string[];
  truncated: boolean;
}

export interface ProjectList {
  projects: ProjectSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface Completeness {
  complete: boolean;
  missing_backends: string[];
  truncated: boolean;
  errors: string[];
}

export interface RunSummary {
  id: string;
  status: string;
  completeness: string;
  tool_versions: Record<string, string | null>;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
}

export interface ProjectStatus {
  project: ProjectSummary;
  completeness: Completeness;
  published_run: RunSummary | null;
  runs: RunSummary[];
}

export interface Health {
  version: string;
  workspace: string;
}

export class ApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const data = (await response.json()) as Record<string, unknown>;
  if (!response.ok) {
    throw new ApiError(
      String(data["code"] ?? "request_failed"),
      String(data["message"] ?? response.statusText),
    );
  }
  return data as T;
}

export function getHealth(): Promise<Health> {
  return fetchJson("/api/health");
}

export function listProjects(offset = 0, limit = 50): Promise<ProjectList> {
  return fetchJson(`/api/projects?offset=${offset}&limit=${limit}`);
}

export function getProjectStatus(projectId: string): Promise<ProjectStatus> {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}`);
}
