import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { StatusBadge, type StatusKind } from "../components/StatusBadge";
import { EmptyState } from "../components/states/EmptyState";
import { ErrorState } from "../components/states/ErrorState";
import "./HomePage.css";

/** 工作台项目摘要（GET /api/projects 的条目）。 */
interface WorkbenchProject {
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

/** POST /api/analyze 的 202 应答（同 hash 已存在时返回已有项目）。 */
interface AnalyzeAccepted {
  project_id: string;
  status: string;
  apk_sha256: string;
  already_analysed: boolean;
}

/** 后端状态 → 徽章语义（与 components/StatusBadge 的五态对齐）。 */
function statusToKind(status: WorkbenchProject["status"]): StatusKind {
  switch (status) {
    case "completed":
      return "completed";
    case "running":
      return "running";
    case "failed":
      return "failed";
    default:
      return "pending";
  }
}

/** 证据/发现数：仅完成或部分完成时展示数字。 */
function hasFindings(p: WorkbenchProject): boolean {
  return p.status === "completed" || p.status === "failed";
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return date.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// 最小 fetch 封装（M2-A 的 api client 合并前先在此落地；合并后统一切换 import）。
// 浏览器 dev 下 /api 由 vite proxy 转发到 8618（见 vite.config.ts），Tauri 内
// 同源相对路径即可；因此统一用相对路径，不写死后端地址。
// ---------------------------------------------------------------------------

async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown; message?: string };
      if (typeof body.detail === "string") detail = body.detail;
      else if (typeof body.message === "string") detail = body.message;
    } catch {
      // 非 JSON 错误体：保留状态码信息
    }
    throw new Error(`请求失败（${detail}）`);
  }
  return (await response.json()) as T;
}

function listProjects(): Promise<{ projects: WorkbenchProject[]; total: number }> {
  return apiJson("/api/projects?limit=50");
}

function uploadApk(file: File): Promise<AnalyzeAccepted> {
  const form = new FormData();
  form.append("file", file, file.name);
  return apiJson("/api/analyze", { method: "POST", body: form });
}

/** 首页：拖拽上传 + 最近项目（补充单 2-1；Q2-M2-B 接入真实工作台 API）。 */
export default function HomePage() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [projects, setProjects] = useState<WorkbenchProject[] | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const dragDepth = useRef(0);

  const loadProjects = useCallback(async () => {
    setProjectsError(null);
    try {
      const data = await listProjects();
      setProjects(data.projects);
    } catch (err) {
      setProjects(null);
      setProjectsError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects, reloadTick]);

  const acceptFile = useCallback(
    (file: File | undefined | null) => {
      if (!file || uploading) return;
      if (!file.name.toLowerCase().endsWith(".apk")) {
        setFileName(null);
        setError("仅支持 .apk 文件");
        return;
      }
      setError(null);
      setFileName(file.name);
      setUploading(true);
      uploadApk(file)
        .then((accepted) => {
          // 同 hash 已存在时后端也返回已有项目，同样跳转。
          void navigate(`/analysis/${accepted.project_id}`);
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err.message : String(err));
          setFileName(null);
        })
        .finally(() => setUploading(false));
    },
    [navigate, uploading],
  );

  return (
    <div className="page home-page">
      <header className="page-header">
        <h1 className="page-title">开始一次分析</h1>
        <p className="page-subtitle">拖入 APK 文件，DexAtlas 将生成可复核的证据链报告。</p>
      </header>

      <section
        className={`dropzone card${dragging ? " is-dragging" : ""}${fileName ? " has-file" : ""}`}
        aria-label="上传 APK"
        onDragEnter={(e) => {
          e.preventDefault();
          dragDepth.current += 1;
          setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={(e) => {
          e.preventDefault();
          dragDepth.current -= 1;
          if (dragDepth.current <= 0) setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          dragDepth.current = 0;
          setDragging(false);
          acceptFile(e.dataTransfer.files?.[0]);
        }}
      >
        <div className="dropzone-art" aria-hidden="true">
          <div className="dropzone-art-ring" />
          <div className="dropzone-art-core">⇪</div>
        </div>
        {uploading ? (
          <>
            <strong className="dropzone-file">{fileName}</strong>
            <span className="page-subtitle" role="status">
              正在上传并启动分析…
            </span>
          </>
        ) : (
          <>
            <strong>拖拽 APK 到此处</strong>
            <span className="page-subtitle">或</span>
            <label className={`btn btn-primary dropzone-browse${uploading ? " is-busy" : ""}`}>
              浏览文件
              <input
                type="file"
                accept=".apk"
                disabled={uploading}
                onChange={(e) => acceptFile(e.target.files?.[0])}
              />
            </label>
            {error ? (
              <span className="dropzone-error" role="alert">
                {error}
              </span>
            ) : null}
          </>
        )}
      </section>

      <section aria-label="最近项目">
        <div className="section-head">
          <h2 className="section-title">最近项目</h2>
          <Link to="/findings" className="section-more">
            查看全部 →
          </Link>
        </div>
        {projectsError ? (
          <div className="card project-list-card">
            <ErrorState
              title="项目列表加载失败"
              description={projectsError}
              onRetry={() => setReloadTick((t) => t + 1)}
            />
          </div>
        ) : projects !== null && projects.length === 0 ? (
          <div className="card project-list-card">
            <EmptyState
              title="还没有分析过的项目"
              description="拖入一个 APK 文件，开始第一次分析。"
            />
          </div>
        ) : (
          <div className="card project-list-card">
            <table className="table">
              <thead>
                <tr>
                  <th>项目</th>
                  <th>规模</th>
                  <th>状态</th>
                  <th>证据</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {(projects ?? []).map((p) => (
                  <tr key={p.id}>
                    <td>
                      <Link to={`/projects/${p.id}`} className="project-link">
                        {p.apk_name}
                      </Link>
                    </td>
                    <td className="text-secondary">
                      {p.class_count} 类 · {p.method_count} 方法
                    </td>
                    <td>
                      <StatusBadge kind={statusToKind(p.status)} pulse={p.status === "running"} />
                    </td>
                    <td>
                      {hasFindings(p) && p.evidence_count > 0 ? (
                        <span className="badge badge-warning">{p.evidence_count} 条</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="text-muted">{formatTime(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
