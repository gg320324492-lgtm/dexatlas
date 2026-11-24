/**
 * 项目详情页 — 三栏布局：左列证据列表 / 中间源码或调用图主体 / 右侧证据抽屉（§2-4）。
 * Q2-M2-D：数据来自真实后端 GET /api/projects/{id} 与 /evidence；
 * 证据抽屉展示后端真实 locator（provenance 串），"打开来源"/"resolve" 调
 * /locators/resolve 显示真实机器路径。partial 横幅由项目 errors 真实生成。
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { Card, CardBody, CardHeader } from "../components/Card";
import { SearchInput } from "../components/SearchInput";
import { Drawer } from "../components/Drawer";
import { PartialBanner } from "../components/PartialBanner";
import { EmptyState } from "../components/states/EmptyState";
import { ErrorState } from "../components/states/ErrorState";
import { LoadingState } from "../components/states/LoadingState";
import { ApiError, dexatlas as client, downloadText } from "../api";
import type {
  CompletenessError,
  EvidenceRecord,
  LocatorResolution,
  ProjectDetailEnvelope,
} from "../api";

/** 证据列表的展示分类：由后端 kind + summary 归纳，标签与 M1 原型一致。 */
type EvidenceKind = "symbol" | "string" | "permission" | "component" | "sink";

const KIND_LABEL: Record<EvidenceKind, string> = {
  symbol: "符号",
  string: "字符串",
  permission: "权限",
  component: "组件",
  sink: "汇聚点",
};

const KIND_CLASS: Record<EvidenceKind, string> = {
  symbol: "da-ev-tag--symbol",
  string: "da-ev-tag--string",
  permission: "da-ev-tag--permission",
  component: "da-ev-tag--component",
  sink: "da-ev-tag--sink",
};

const KIND_ORDER: EvidenceKind[] = ["permission", "component", "symbol", "string", "sink"];

/** 从证据记录归纳展示分类（确定性规则，不是推断结论）。 */
function classify(rec: EvidenceRecord): EvidenceKind {
  const s = rec.summary.toLowerCase();
  const detail = JSON.stringify(rec.detail).toLowerCase();
  if (s.includes("permission") || detail.includes("android.permission")) return "permission";
  if (s.includes("exported") || s.includes("component") || detail.includes('"components"')) return "component";
  if (s.includes("called from") || rec.kind === "cross_reference") return "sink";
  if (rec.kind === "declaration") return "symbol";
  return "string";
}

/** provenance 串 → 展示后端名。 */
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
      return tool || "未知";
  }
}

/** 把 detail 里的结构化信息拼成一行次要说明。 */
function subtitleOf(rec: EvidenceRecord): string | undefined {
  const d = rec.detail as Record<string, unknown>;
  if (Array.isArray(d.permissions) && d.permissions.length) {
    return (d.permissions as string[]).join(", ");
  }
  if (Array.isArray(d.components)) {
    const names = (d.components as Array<{ name?: string }>).map((c) => c.name ?? "").filter(Boolean);
    if (names.length) return names.join(", ");
  }
  if (Array.isArray(d.callers) && d.callers.length) {
    return `调用方：${(d.callers as string[]).slice(0, 2).join(", ")}${d.callers.length > 2 ? "…" : ""}`;
  }
  if (typeof d.dex_files !== "undefined") return undefined;
  return undefined;
}

/** 从完整 provenance 串提取展示用 locator（tool:place → place）。 */
function displayLocator(provenance: string[]): string {
  const first = provenance[0] ?? "";
  const idx = first.indexOf(":");
  return idx >= 0 ? first.slice(idx + 1) : first;
}

/** 项目详情响应中的错误 → 横幅文案（真实 errors，非编造）。 */
function bannerFromErrors(errors: CompletenessError[], missing: string[]): string | null {
  if (!errors.length && !missing.length) return null;
  const parts: string[] = [];
  if (missing.length) parts.push(`缺失后端：${missing.join("、")}`);
  for (const e of errors.slice(0, 3)) {
    if (typeof e === "string") {
      parts.push(e);
    } else {
      parts.push(`${e.tool}${e.code ? ` [${e.code}]` : ""} ${e.message}`);
    }
  }
  if (errors.length > 3) parts.push(`…等 ${errors.length} 条错误`);
  return `部分状态：${parts.join("；")}`;
}

interface Loaded {
  project: ProjectDetailEnvelope;
  evidence: EvidenceRecord[];
}

export function ProjectDetail() {
  const { projectId = "" } = useParams();
  const [keyword, setKeyword] = useState("");
  const [kindFilter, setKindFilter] = useState<EvidenceKind | "all">("all");
  const [data, setData] = useState<Loaded | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<EvidenceRecord | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [resolution, setResolution] = useState<LocatorResolution | null>(null);
  const [resolving, setResolving] = useState(false);
  const [exporting, setExporting] = useState<"markdown" | "json" | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const [project, evidenceList] = await Promise.all([
        client.getProject(projectId),
        client.getEvidence(projectId),
      ]);
      setData({ project, evidence: evidenceList.evidence });
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return (data?.evidence ?? []).filter((rec) => {
      const kind = classify(rec);
      const matchKind = kindFilter === "all" || kind === kindFilter;
      const matchKw =
        kw === "" ||
        rec.summary.toLowerCase().includes(kw) ||
        rec.provenance.some((p) => p.toLowerCase().includes(kw));
      return matchKind && matchKw;
    });
  }, [data, keyword, kindFilter]);

  const banner = useMemo(() => {
    if (!data) return null;
    return bannerFromErrors(data.project.completeness.errors, data.project.completeness.missing_backends);
  }, [data]);

  const openEvidence = (rec: EvidenceRecord) => {
    setSelected(rec);
    setResolution(null);
    setDrawerOpen(true);
  };

  /** resolve 按钮：调后端 /locators/resolve，展示真实解析路径。 */
  const resolveSelected = async () => {
    if (!selected || !projectId) return;
    setResolving(true);
    try {
      const r = await client.resolveLocator(projectId, selected.provenance[0] ?? "");
      setResolution(r);
    } catch (e) {
      setResolution({
        resolved: false,
        reason: e instanceof ApiError ? `${e.status}: ${e.message}` : String(e),
        kind: null,
        text: null,
        provenance: [],
      });
    } finally {
      setResolving(false);
    }
  };

  /** 导出报告：Blob + a[download] 下载。 */
  const exportReport = async (format: "markdown" | "json") => {
    if (!projectId) return;
    setExporting(format);
    setExportError(null);
    try {
      const payload = await client.getReport(projectId, format);
      const text = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
      const ext = format === "markdown" ? "md" : "json";
      downloadText(`${projectId}.${ext}`, text, format === "markdown" ? "text/markdown" : "application/json");
    } catch (e) {
      setExportError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <div className="page detail">
        <header className="page-header">
          <h1 className="page-title">项目详情</h1>
        </header>
        <LoadingState variant="card" lines={4} label="正在加载项目详情" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page detail">
        <header className="page-header">
          <h1 className="page-title">项目详情</h1>
        </header>
        <ErrorState
          title="项目详情加载失败"
          description={`无法读取项目 ${projectId || "(未指定)"} 的分析数据。`}
          detail={error ?? undefined}
          onRetry={load}
        />
      </div>
    );
  }

  const p = data.project.project;
  const counts = [
    `类 ${p.class_count}`,
    `方法 ${p.method_count}`,
    `调用点 ${p.call_site_count}`,
    `边 ${p.call_edge_count}`,
  ].join(" · ");

  return (
    <div className="page detail">
      <header className="page-header detail__header">
        <div>
          <h1 className="page-title">{p.apk_name}</h1>
          <p className="page-subtitle">
            <code className="da-code">{p.id}</code> · {p.status} · {p.evidence_count} 条证据 · {counts}
          </p>
        </div>
        <div className="detail__actions">
          <Button
            variant="secondary"
            size="sm"
            iconEnd={<span aria-hidden="true">↧</span>}
            disabled={exporting !== null}
            onClick={() => void exportReport("markdown")}
          >
            {exporting === "markdown" ? "导出中…" : "导出 Markdown"}
          </Button>
          <Button
            variant="primary"
            size="sm"
            iconEnd={<span aria-hidden="true">↧</span>}
            disabled={exporting !== null}
            onClick={() => void exportReport("json")}
          >
            {exporting === "json" ? "导出中…" : "导出 JSON"}
          </Button>
        </div>
      </header>

      {exportError && (
        <div className="detail__export-error" role="alert">
          报告导出失败：{exportError}
        </div>
      )}

      {banner && <PartialBanner tone="warning" message={banner} />}

      <div className="detail__grid">
        {/* 左列：证据列表 */}
        <Card className="detail__list" aria-label="证据列表">
          <CardHeader
            title="证据"
            subtitle={`${filtered.length} / ${data.evidence.length} 条`}
            actions={
              <SearchInput
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onClear={() => setKeyword("")}
                placeholder="搜索摘要 / locator"
                aria-label="搜索证据"
              />
            }
          />
          <CardBody>
            <div className="detail__filters" role="group" aria-label="按证据类型筛选">
              {(["all", ...KIND_ORDER] as const).map((kind) => (
                <button
                  key={kind}
                  type="button"
                  className={`da-filter-chip${kindFilter === kind ? " is-active" : ""}`}
                  onClick={() => setKindFilter(kind)}
                  aria-pressed={kindFilter === kind}
                >
                  {kind === "all" ? "全部" : KIND_LABEL[kind]}
                </button>
              ))}
            </div>

            {filtered.length === 0 ? (
              <EmptyState title="没有匹配的证据" description="换个关键词，或清除筛选条件。" />
            ) : (
              <ul className="da-ev-list">
                {filtered.map((rec) => {
                  const kind = classify(rec);
                  return (
                    <li key={rec.id}>
                      <button
                        type="button"
                        className={`da-ev-item${selected?.id === rec.id && drawerOpen ? " is-selected" : ""}`}
                        onClick={() => openEvidence(rec)}
                        aria-expanded={selected?.id === rec.id && drawerOpen}
                      >
                        <div className="da-ev-item__top">
                          <span className={`da-ev-tag ${KIND_CLASS[kind]}`}>{KIND_LABEL[kind]}</span>
                          <span className="da-ev-item__origin">{originOf(rec.provenance)}</span>
                        </div>
                        <div className="da-ev-item__title">{rec.id} · {rec.summary}</div>
                        {subtitleOf(rec) && <div className="da-ev-item__subtitle">{subtitleOf(rec)}</div>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardBody>
        </Card>

        {/* 中间：选中证据的详情主体（来自后端真实数据） */}
        <Card className="detail__main" aria-label="证据正文">
          <CardHeader
            title={selected ? `${selected.id} · ${selected.kind}` : "选择一条证据"}
            subtitle={
              selected
                ? `${originOf(selected.provenance)} · level=${selected.level}`
                : "从左列选择证据查看正文与 provenance"
            }
          />
          <CardBody>
            {selected ? (
              <div className="da-ev-body">
                <p className="da-ev-body__summary">{selected.summary}</p>
                <pre className="da-source" tabIndex={0} aria-label="证据 detail 结构">
                  {JSON.stringify(selected.detail, null, 2)}
                </pre>
                <div className="da-ev-body__prov">
                  <div className="da-ev-body__prov-title">provenance（后端原始 locator）</div>
                  <ul>
                    {selected.provenance.map((prov, i) => (
                      <li key={`${prov}-${i}`}>
                        <code className="da-code">{prov}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <EmptyState
                title="尚未选择证据"
                description={`共 ${data.evidence.length} 条证据；点击左列任意条目在此查看其结构与来源。`}
              />
            )}
          </CardBody>
        </Card>
      </div>

      {/* 右侧：证据抽屉 */}
      <Drawer
        open={drawerOpen && selected !== null}
        title="证据详情"
        onClose={() => setDrawerOpen(false)}
        width={460}
        footer={
          selected && (
            <div className="da-ev-drawer__footer">
              <span className="da-ev-drawer__locator" title={displayLocator(selected.provenance)}>
                locator：{displayLocator(selected.provenance)}
              </span>
              <div className="da-ev-drawer__actions">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    window.alert(
                      `来源文件（后端解析）：${displayLocator(selected.provenance)}\n完整 provenance：${selected.provenance.join("\n")}`,
                    )
                  }
                >
                  打开来源
                </Button>
                <Button variant="primary" size="sm" disabled={resolving} onClick={() => void resolveSelected()}>
                  {resolving ? "解析中…" : "resolve"}
                </Button>
              </div>
              {resolution && (
                <div className="da-ev-drawer__resolution" role="status">
                  <div>
                    resolved：{String(resolution.resolved)}
                    {resolution.kind ? ` · kind=${resolution.kind}` : ""}
                  </div>
                  {resolution.reason && <div className="da-ev-drawer__resolution-path">{resolution.reason}</div>}
                  {resolution.text && (
                    <pre className="da-ev-drawer__resolution-text">{resolution.text.text.slice(0, 800)}</pre>
                  )}
                </div>
              )}
            </div>
          )
        }
      >
        {selected && (
          <div className="da-ev-drawer__body">
            <div className="da-ev-drawer__field">
              <span className="da-ev-drawer__label">编号</span>
              <code className="da-code">{selected.id}</code>
            </div>
            <div className="da-ev-drawer__field">
              <span className="da-ev-drawer__label">类型 / 级别</span>
              {selected.kind} · {selected.level}
            </div>
            <div className="da-ev-drawer__field">
              <span className="da-ev-drawer__label">摘要</span>
              {selected.summary}
            </div>
            <div className="da-ev-drawer__field">
              <span className="da-ev-drawer__label">来源后端</span>
              {originOf(selected.provenance)}
            </div>
            <div className="da-ev-drawer__field">
              <span className="da-ev-drawer__label">detail</span>
              <pre className="da-ev-drawer__detail">{JSON.stringify(selected.detail, null, 2)}</pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
