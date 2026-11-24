import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/states/EmptyState";
import { ErrorState } from "../components/states/ErrorState";
import { LoadingState } from "../components/states/LoadingState";
import { describeError, dexatlas } from "../api";
import type { EvidenceRecord, ProjectSummary } from "../api";
import "./FindingsPage.css";

/** 证据等级 → 徽章语义（core/models.py:537 EvidenceLevel；不做推断）。 */
const LEVEL_BADGE: Record<string, { label: string; cls: string }> = {
  verified: { label: "已验证", cls: "badge-success" },
  lead: { label: "线索", cls: "badge-warning" },
  insufficient: { label: "证据不足", cls: "badge-muted" },
};

function levelBadge(level: string): { label: string; cls: string } {
  return LEVEL_BADGE[level] ?? { label: level || "—", cls: "badge-muted" };
}

/** provenance 串 → 展示后端名（"jadx:..." → JADX）。 */
function originOf(provenance: string[]): string {
  const tool = provenance[0]?.split(":", 1)[0] ?? "";
  switch (tool) {
    case "jadx":
      return "JADX";
    case "apktool":
      return "Apktool";
    case "androguard":
      return "Androguard";
    case "apk-reader":
      return "APK Reader";
    default:
      return tool || "—";
  }
}

/** provenance 串 → 去掉工具前缀的展示 locator。 */
function displayLocator(provenance: string[]): string {
  const first = provenance[0] ?? "";
  const idx = first.indexOf(":");
  return idx >= 0 ? first.slice(idx + 1) : first;
}

/**
 * 证据总览页（侧栏"证据"）：跨项目证据检索视图。
 * Q2-M3-T1：接入真实后端 GET /api/projects + /evidence，逐条展示
 * 等级、来源后端与 locator；不再展示任何内置假数据。
 */
export default function FindingsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [projectId, setProjectId] = useState("");
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [evidenceNonce, setEvidenceNonce] = useState(0);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await dexatlas.listProjects();
      setProjects(list);
      const done = list.find((p) => p.status === "completed") ?? list[0];
      if (done) setProjectId(done.id);
    } catch (e) {
      setError(describeError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoadingEvidence(true);
    setEvidenceError(null);
    dexatlas
      .getEvidence(projectId)
      .then((list) => {
        if (!cancelled) setEvidence(list.evidence);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setEvidence([]);
          setEvidenceError(describeError(e));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingEvidence(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, evidenceNonce]);

  const projectName = useMemo(
    () => projects?.find((p) => p.id === projectId)?.apk_name ?? projectId,
    [projects, projectId],
  );

  if (loading) {
    return (
      <div className="page">
        <header className="page-header">
          <h1 className="page-title">证据</h1>
        </header>
        <LoadingState variant="table" lines={6} label="正在加载项目列表" />
      </div>
    );
  }

  if (error && !projects) {
    return (
      <div className="page">
        <header className="page-header">
          <h1 className="page-title">证据</h1>
        </header>
        <ErrorState
          title="证据加载失败"
          description="无法读取项目列表。请确认 DexAtlas 后端（127.0.0.1:8618）正在运行。"
          detail={error}
          onRetry={loadProjects}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">证据</h1>
        <p className="page-subtitle">全部项目产生的证据记录，每一条都带等级与可回跳的来源 locator。</p>
      </header>

      <div className="card findings-card">
        <div className="findings-toolbar">
          <label className="findings-toolbar__field">
            <span className="findings-toolbar__label">项目</span>
            <select
              className="findings-toolbar__select"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              aria-label="选择项目"
            >
              {(projects ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.apk_name}（{p.id}）
                </option>
              ))}
            </select>
          </label>
          <Link to="/evidence" className="findings-toolbar__more">
            符号检索 →
          </Link>
        </div>

        {loadingEvidence ? (
          <LoadingState lines={4} label="正在加载证据" />
        ) : evidenceError ? (
          <ErrorState
            title="证据加载失败"
            description={`无法读取项目「${projectName}」的证据记录。可切换其他项目，或稍后重试。`}
            detail={evidenceError}
            onRetry={() => setEvidenceNonce((n) => n + 1)}
          />
        ) : evidence.length === 0 ? (
          <EmptyState title="该项目暂无证据" description="完成分析的项目会在这里展示其全部证据记录。" />
        ) : (
          <>
            <div className="evidence-meta">
              项目 <code className="da-code">{projectName}</code> · 证据 {evidence.length} 条
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>编号</th>
                  <th>证据</th>
                  <th>等级</th>
                  <th>后端</th>
                  <th>来源 locator</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((rec) => {
                  const sev = levelBadge(rec.level);
                  return (
                    <tr key={rec.id}>
                      <td className="finding-id">{rec.id}</td>
                      <td>
                        <Link to={`/projects/${projectId}`} className="finding-link" title={rec.summary}>
                          {rec.summary}
                        </Link>
                      </td>
                      <td>
                        <span className={`badge ${sev.cls}`}>{sev.label}</span>
                      </td>
                      <td className="finding-project">{originOf(rec.provenance)}</td>
                      <td className="finding-source" title={rec.provenance.join("\n")}>
                        {displayLocator(rec.provenance)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
