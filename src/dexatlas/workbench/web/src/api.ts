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

export interface UntrustedText {
  text: string;
  truncated: boolean;
  bytes: number;
  notice: string;
}

export interface SymbolView {
  kind: string;
  name: UntrustedText;
  detail: UntrustedText;
  provenance: string[];
}

export interface SymbolList {
  symbols: SymbolView[];
  total: number;
  offset: number;
  limit: number;
}

export interface CallSiteView {
  caller: string;
  callee: string;
  kind: string;
  dex_name: string;
  instruction_offset: number;
  provenance: string[];
}

export interface CallerView {
  call_sites: CallSiteView[];
  call_site_count: number;
  call_edge_count: number;
  truncated: boolean;
}

export interface CalleeView {
  callees: SymbolView[];
  call_site_count: number;
  call_edge_count: number;
  truncated: boolean;
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

// A method id carries `(`, `)` and `;`, and a locator carries `#` and `->`, so
// every query value goes through URLSearchParams — otherwise a `#` in a method
// id would be read as the URL's own fragment and the request would ask for
// something else than the caller named.
function projectUrl(projectId: string, path: string, params: Record<string, string> = {}): string {
  const query = new URLSearchParams(params).toString();
  return `/api/projects/${encodeURIComponent(projectId)}/${path}${query ? `?${query}` : ""}`;
}

export function searchSymbols(
  projectId: string,
  query: string,
  offset = 0,
  limit = 50,
): Promise<SymbolList> {
  return fetchJson(
    projectUrl(projectId, "symbols", { q: query, offset: String(offset), limit: String(limit) }),
  );
}

export function findCallers(
  projectId: string,
  methodId: string,
  limit = 50,
): Promise<CallerView> {
  return fetchJson(projectUrl(projectId, "callers", { method_id: methodId, limit: String(limit) }));
}

export function findCallees(
  projectId: string,
  methodId: string,
  limit = 50,
): Promise<CalleeView> {
  return fetchJson(projectUrl(projectId, "callees", { method_id: methodId, limit: String(limit) }));
}
