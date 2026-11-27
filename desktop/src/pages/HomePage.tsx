import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { StatusBadge, type StatusKind } from "../components/StatusBadge";
import { EmptyState } from "../components/states/EmptyState";
import { ErrorState } from "../components/states/ErrorState";
import { LoadingState } from "../components/states/LoadingState";
import { describeError, dexatlas } from "../api";
import type { AnalyzeAccepted, ProjectSummary as WorkbenchProject } from "../api";
import "./HomePage.css";

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

/** 首页拖拽区单文件大小上限（MB）。与后端工作台的常见样例体量对齐，超限前端直接拒绝。 */
const MAX_UPLOAD_MB = 512;

/** 首页：拖拽上传 + 最近项目（补充单 2-1；Q2-M3-T1 起统一走 api/ 客户端）。 */
export default function HomePage() {
  const navigate = useNavigate();
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  /**
   * 「这个 APK 之前分析过了」的提示。
   *
   * 旧实现把这句话塞进 `error` 然后立刻 `navigate(...)`：路由一变，首页被卸载，
   * 这句话跟着组件一起消失——**用户根本没看见**（打包 exe 实测 802 次采样 0 次抓到）。
   * 现在它是一份留在页面上的提示：不跳转，提示留在原地，配一个「打开已有项目」
   * 的动作由用户自己决定去不去。
   */
  const [duplicate, setDuplicate] = useState<{ projectId: string; sha12: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [projects, setProjects] = useState<WorkbenchProject[] | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const dragDepth = useRef(0);

  const loadProjects = useCallback(async () => {
    setProjectsError(null);
    try {
      setProjects(await dexatlas.listProjects());
    } catch (err) {
      setProjects(null);
      setProjectsError(describeError(err));
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
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        setFileName(null);
        setError(`文件过大：${(file.size / 1024 / 1024).toFixed(1)} MB 超过 ${MAX_UPLOAD_MB} MB 上限，请换更小的 APK。`);
        return;
      }
      setError(null);
      setDuplicate(null);
      setFileName(file.name);
      setUploading(true);
      dexatlas
        .analyzeUpload(file, file.name)
        .then((accepted: AnalyzeAccepted) => {
          if (accepted.already_analysed) {
            // 同 hash 已分析过：**留在原地**，把「没有重复分析」这句话留在页面上，
            // 并给一个去已有项目的入口。不跳转——跳转会把这句话一起带走（旧实现
            // 的缺陷：用户永远看不到这句提示）。
            setDuplicate({
              projectId: accepted.project_id,
              sha12: accepted.apk_sha256.slice(0, 12),
            });
            return;
          }
          void navigate(`/analysis/${accepted.project_id}`);
        })
        .catch((err: unknown) => {
          setError(describeError(err));
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
              {error ?? "正在上传并启动分析…"}
            </span>
          </>
        ) : (
          <>
            <strong>拖拽 APK 到此处</strong>
            <span className="page-subtitle">或 · 单个文件不超过 {MAX_UPLOAD_MB} MB；同一 APK 重复上传会打开已有项目，不会重复分析</span>
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
        {duplicate ? (
          // 留在页面上的提示：role="alert" 让读屏软件立刻念出来，视觉上是一块
          // 有底色的告示，不是悄悄溜走的一行字。
          <div className="dropzone-notice" role="alert">
            <strong className="dropzone-notice-title">这个 APK 已经分析过了</strong>
            <span className="dropzone-notice-text">
              sha256 前 12 位 {duplicate.sha12}；没有重复分析，已有的分析结果还在。
            </span>
            <Link className="btn btn-secondary dropzone-notice-action" to={`/analysis/${duplicate.projectId}`}>
              打开已有项目
            </Link>
          </div>
        ) : null}
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
        ) : projects === null ? (
          <div className="card project-list-card">
            <LoadingState variant="table" lines={5} label="正在加载最近项目" />
          </div>
        ) : projects.length === 0 ? (
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
