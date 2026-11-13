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

// -- the second screen: the source, the evidence and the place it cites -----

export interface SourceView {
  found: boolean;
  reason: string;
  kind: "java" | "smali" | null;
  text: UntrustedText | null;
  provenance: string[];
  candidates: string[];
}

export interface EvidenceView {
  id: string;
  kind: string;
  level: string;
  summary: string;
  detail: Record<string, unknown>;
  provenance: string[];
}

export interface LocatorResolution {
  resolved: boolean;
  reason: string;
  kind: "java" | "smali" | null;
  text: UntrustedText | null;
  provenance: string[];
}

// -- the third screen: the calls into and out of one method ----------------

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

// -- the upload screen: one endpoint, then the project it produces ----------

export interface UploadAccepted {
  project_id: string;
  status: string;
  apk_sha256: string;
  already_analysed: boolean;
}

// An upload is a multipart POST, so it goes around fetchJson: the response is
// the same JSON contract, but the request carries a file the server streams
// to disk under the shared upload policy.
export async function uploadApk(file: File): Promise<UploadAccepted> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch("/api/analyze", { method: "POST", body });
  const data = (await response.json()) as Record<string, unknown>;
  if (!response.ok) {
    throw new ApiError(
      String(data["code"] ?? "upload_failed"),
      String(data["detail"] ?? data["message"] ?? response.statusText),
    );
  }
  return data as unknown as UploadAccepted;
}

// A method id carries `(`, `)` and `;`, and a locator carries `#` and `->`, so
// every query value goes through URLSearchParams — otherwise a `#` in a method
// id would be read as the URL's own fragment and the request would ask for
// something else than the caller named.
function projectUrl(projectId: string, path: string, params: Record<string, string> = {}): string {
  const query = new URLSearchParams(params).toString();
  return `/api/projects/${encodeURIComponent(projectId)}/${path}${query ? `?${query}` : ""}`;
}

// -- the report export screen -----------------------------------------------

// The report is a download, not a JSON answer the browser unpacks: the
// endpoint returns the renderer's own Markdown text or JSON document, so the
// link points straight at it and the browser handles the rest.
export function reportUrl(projectId: string, format: "json" | "markdown"): string {
  return projectUrl(projectId, "report", { format });
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

// -- the second screen's five tools ----------------------------------------

export function getClassSource(projectId: string, className: string): Promise<SourceView> {
  return fetchJson(projectUrl(projectId, "source/class", { class_name: className }));
}

export function getMethodSource(
  projectId: string,
  className: string,
  methodName: string,
  descriptor?: string,
): Promise<SourceView> {
  const params: Record<string, string> = { class_name: className, method_name: methodName };
  if (descriptor !== undefined) params["descriptor"] = descriptor;
  return fetchJson(projectUrl(projectId, "source/method", params));
}

export function listEvidence(projectId: string): Promise<EvidenceView[]> {
  return fetchJson(projectUrl(projectId, "evidence"));
}

export function getEvidence(projectId: string, evidenceId: string): Promise<EvidenceView> {
  return fetchJson(
    projectUrl(projectId, `evidence/${encodeURIComponent(evidenceId)}`),
  );
}

export function resolveLocator(projectId: string, locator: string): Promise<LocatorResolution> {
  return fetchJson(projectUrl(projectId, "locators/resolve", { locator }));
}

// -- the third screen's two tools ------------------------------------------

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

// -- the agent workspace ----------------------------------------------------
//
// One question about one analysed APK. The task is accepted with a 202 and
// the answer arrives by polling, exactly as an upload's analysis does; the
// report is the agent's own document, not a shape this file invents.

export interface AgentConfig {
  configured: boolean;
  provider: string | null;
  model: string | null;
}

export interface AgentTaskAccepted {
  task_id: string;
  project_id: string;
  status: string;
  question: string;
}

export interface AgentBudgetUsage {
  tokens: number;
  iterations: number;
  seconds: number;
}

export interface AgentBudget {
  max_tokens: number;
  max_iterations: number;
  max_seconds: number;
}

export interface AgentPlan {
  project_id: string;
  question: string;
  allowed_tools: string[];
  steps: { tool: string; purpose: string; sensitive: boolean }[];
  max_steps: number;
  max_sensitive_calls: number;
  limits: AgentBudget;
}

export interface AgentToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  ok: boolean;
  attempt: number;
  error: string | null;
  error_kind: string | null;
  duration_seconds: number;
  started_at: string;
}

export interface AgentEvent {
  at: string;
  kind: string;
  message: string;
}

export interface AgentTask {
  task_id: string;
  question: string;
  status: string;
  project_id: string | null;
  run_id: string | null;
  plan: AgentPlan | null;
  tool_calls: AgentToolCall[];
  events: AgentEvent[];
  usage: AgentBudgetUsage;
  limits: AgentBudget;
  error: string | null;
  created_at: string;
  updated_at: string;
  findings_count: number;
}

// The evidence record, as the agent report carries it: the same shape the
// MCP `get_evidence` tool answers with, under this report's own id.
export interface AgentReportEvidence {
  id: string;
  kind: string;
  level: string;
  summary: string;
  detail: Record<string, unknown>;
  provenance: string[];
}

export interface AgentReportDocument {
  schema_version: number;
  kind: string;
  generated_at: string;
  task: {
    id: string;
    question: string;
    status: string;
    project_id: string | null;
    run_id: string | null;
  };
  findings: AgentReportEvidence[];
  findings_by_level: Record<string, number>;
  tool_calls: AgentToolCall[];
  budget: { used: AgentBudgetUsage; limits: AgentBudget };
  limitations: string[];
  events: AgentEvent[];
  error: string | null;
  sections: {
    established: AgentReportEvidence[];
    leads: AgentReportEvidence[];
    insufficient: AgentReportEvidence[];
  };
}

export function getAgentConfig(): Promise<AgentConfig> {
  return fetchJson("/api/agent/config");
}

// A question is a JSON POST, so it goes around fetchJson like the upload
// does: the acknowledgement is a 202, and a refused question (no model
// configured, an unknown project) is the error document in `detail`.
export async function askAgent(projectId: string, question: string): Promise<AgentTaskAccepted> {
  const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/agent/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = (await response.json()) as Record<string, unknown>;
  if (!response.ok) {
    const detail = data["detail"] as Record<string, unknown> | undefined;
    throw new ApiError(
      String(detail?.["code"] ?? data["code"] ?? "agent_task_refused"),
      String(detail?.["message"] ?? data["message"] ?? response.statusText),
    );
  }
  return data as unknown as AgentTaskAccepted;
}

export function getAgentTask(taskId: string): Promise<AgentTask> {
  return fetchJson(`/api/agent/tasks/${encodeURIComponent(taskId)}`);
}

export function getAgentReport(taskId: string): Promise<AgentReportDocument> {
  return fetchJson(`/api/agent/tasks/${encodeURIComponent(taskId)}/report`);
}

export function agentReportUrl(taskId: string, format: "json" | "markdown"): string {
  return `/api/agent/tasks/${encodeURIComponent(taskId)}/report?format=${format}`;
}

