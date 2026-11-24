/**
 * 证据页 — 跨项目证据检索视图。
 * Q2-M2-D：项目选择器（GET /api/projects）+ 搜索框（GET /api/projects/{id}/symbols?q=）
 * + 证据结果表（GET /api/projects/{id}/evidence）。
 * 搜索时同时返回符号命中与证据摘要命中，均为后端真实数据。
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ErrorState } from "../components/states/ErrorState";
import { LoadingState } from "../components/states/LoadingState";
import { EmptyState } from "../components/states/EmptyState";
import { SearchInput } from "../components/SearchInput";
import {
  ApiError,
  client,
  type EvidenceRecord,
  type ProjectInfo,
  type SymbolHit,
} from "../client";
import "./EvidencePage.css";

/** 一行检索结果（证据摘要或符号命中）。 */
interface ResultRow {
  key: string;
  type: "evidence" | "symbol";
  id: string;
  kind: string;
  content: string;
  backend: string;
  locator: string;
}

function backendOf(provenance: string[]): string {
  const tool = provenance[0]?.split(":", 1)[0] ?? "";
  if (!tool) return "—";
  return tool.charAt(0).toUpperCase() + tool.slice(1);
}

export default function EvidencePage() {
  const [projects, setProjects] = useState<ProjectInfo[] | null>(null);
  const [projectId, setProjectId] = useState<string>("");
  const [query, setQuery] = useState("");
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [symbols, setSymbols] = useState<SymbolHit[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 项目列表
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await client.listProjects();
        if (cancelled) return;
        setProjects(list);
        // 默认选最新的已完成项目
        const done = list.find((p) => p.status === "completed") ?? list[0];
        if (done) setProjectId(done.id);
      } catch (e) {
        if (!cancelled) setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // 证据列表跟随所选项目
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setSearching(true);
    (async () => {
      try {
        const ev = await client.getEvidence(projectId);
        if (!cancelled) setEvidence(ev);
      } catch (e) {
        if (!cancelled) {
          setEvidence([]);
          setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
        }
      } finally {
        if (!cancelled) setSearching(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // 搜索：调 /symbols（索引全文检索）；空关键词时清空符号命中
  const runSearch = useCallback(
    async (q: string) => {
      const term = q.trim();
      if (!projectId || term === "") {
        setSymbols([]);
        return;
      }
      setSearching(true);
      try {
        setSymbols(await client.searchSymbols(projectId, term, 50));
      } catch (e) {
        setSymbols([]);
        setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
      } finally {
        setSearching(false);
      }
    },
    [projectId],
  );

  const rows = useMemo<ResultRow[]>(() => {
    const evRows: ResultRow[] = evidence.map((rec) => ({
      key: `ev-${rec.id}`,
      type: "evidence",
      id: rec.id,
      kind: rec.kind,
      content: rec.summary,
      backend: backendOf(rec.provenance),
      locator: rec.provenance[0] ?? "—",
    }));
    const symRows: ResultRow[] = symbols.map((s, i) => ({
      key: `sym-${i}`,
      type: "symbol",
      id: s.kind,
      kind: s.kind,
      content: `${s.name.text}${s.detail ? ` — ${s.detail.text}` : ""}`,
      backend: "Index",
      locator: s.name.text,
    }));
    return [...evRows, ...symRows];
  }, [evidence, symbols]);

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
        <LoadingState variant="table" lines={6} label="正在加载证据" />
      </div>
    );
  }

  if (error && !projects) {
    return (
      <div className="page">
        <header className="page-header">
          <h1 className="page-title">证据</h1>
        </header>
        <ErrorState title="证据加载失败" description="无法读取项目列表。" detail={error} />
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">证据</h1>
        <p className="page-subtitle">跨项目证据检索：选择项目，按关键词查索引符号，或浏览全部证据记录。</p>
      </header>

      <div className="evidence-toolbar card">
        <label className="evidence-toolbar__field">
          <span className="evidence-toolbar__label">项目</span>
          <select
            className="evidence-toolbar__select"
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value);
              setSymbols([]);
              setQuery("");
            }}
            aria-label="选择项目"
          >
            {(projects ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.apk_name}（{p.id}）
              </option>
            ))}
          </select>
        </label>
        <div className="evidence-toolbar__search">
          <SearchInput
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onClear={() => {
              setQuery("");
              setSymbols([]);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") void runSearch(query);
            }}
            placeholder="搜索符号（类 / 方法 / 字段），回车触发"
            aria-label="搜索索引符号"
          />
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={searching || query.trim() === ""}
            onClick={() => void runSearch(query)}
          >
            {searching ? "搜索中…" : "搜索"}
          </button>
        </div>
      </div>

      {searching && <LoadingState lines={3} label="检索中" />}

      {!searching && rows.length === 0 ? (
        <div className="card">
          <EmptyState
            title="没有证据或命中"
            description={`项目 ${projectName} 暂无证据记录；输入关键词可检索其符号索引。`}
          />
        </div>
      ) : (
        !searching && (
          <div className="card">
            <div className="evidence-meta">
              项目 <code className="da-code">{projectName}</code> · 证据 {evidence.length} 条
              {symbols.length > 0 && ` · 符号命中 ${symbols.length} 条`}
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>来源</th>
                  <th>类型</th>
                  <th>内容</th>
                  <th>后端</th>
                  <th>Locator</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.key}>
                    <td className="evidence-id">{r.type === "evidence" ? r.id : "index"}</td>
                    <td>
                      <span className={`badge ${r.type === "symbol" ? "badge-info" : "badge-muted"}`}>
                        {r.kind}
                      </span>
                    </td>
                    <td className="evidence-label">{r.content}</td>
                    <td>{r.backend}</td>
                    <td className="evidence-locator" title={r.locator}>
                      {r.locator}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
