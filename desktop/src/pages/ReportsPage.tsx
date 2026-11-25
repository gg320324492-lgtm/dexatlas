/**
 * 报告页 — 历史项目报告导出入口。
 * Q2-M2-D：列表来自 GET /api/projects（真实项目），导出按钮调
 * GET /api/projects/{id}/report?format=markdown|json，Blob + a[download] 下载，
 * 文件名 {project_id}.md/.json；下载中 loading 态，失败 ErrorState。
 * 「生成时间」按本地时区显示，并附一行 UTC 标注（后端给的是 UTC 时刻，
 * 见 ../datetime 的规则）。
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "../components/Button";
import { ErrorState } from "../components/states/ErrorState";
import { LoadingState } from "../components/states/LoadingState";
import { EmptyState } from "../components/states/EmptyState";
import { describeError, dexatlas as client, downloadText } from "../api";
import type { ProjectSummary } from "../api";
import { timestampParts } from "../datetime";
import "./ReportsPage.css";

type Format = "markdown" | "json";

/** 报告页一行：项目 + 两种格式的导出按钮。 */
export default function ReportsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<{ id: string; format: Format } | null>(null);
  const [rowError, setRowError] = useState<{ id: string; message: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProjects(await client.listProjects());
    } catch (e) {
      setError(describeError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const doExport = async (project: ProjectSummary, format: Format) => {
    setExporting({ id: project.id, format });
    setRowError(null);
    const ext = format === "markdown" ? "md" : "json";
    try {
      const payload = await client.getReport(project.id, format);
      const text = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
      downloadText(`${project.id}.${ext}`, text, format === "markdown" ? "text/markdown" : "application/json");
    } catch (e) {
      setRowError({
        id: project.id,
        message: describeError(e),
      });
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <div className="page">
        <header className="page-header">
          <h1 className="page-title">报告</h1>
          <p className="page-subtitle">已生成的分析报告，可导出为 Markdown / JSON。</p>
        </header>
        <LoadingState variant="table" lines={5} label="正在加载项目报告" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <header className="page-header">
          <h1 className="page-title">报告</h1>
          <p className="page-subtitle">已生成的分析报告，可导出为 Markdown / JSON。</p>
        </header>
        <ErrorState title="报告列表加载失败" description="无法读取项目列表。" detail={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">报告</h1>
        <p className="page-subtitle">已生成的分析报告，可导出为 Markdown / JSON。</p>
      </header>

      {rowError && (
        <div className="reports-row-error" role="alert">
          {rowError.id} 导出失败：{rowError.message}
        </div>
      )}

      <div className="card reports-card">
        {(projects ?? []).length === 0 ? (
          <EmptyState title="还没有可导出的报告" description="先在首页上传并分析一个 APK。" />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>项目 ID</th>
                <th>APK</th>
                <th>状态</th>
                <th>证据数</th>
                <th>生成时间（本地）</th>
                <th>
                  <span className="visually-hidden">操作</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {(projects ?? []).map((p) => {
                // 后端给的是 UTC 时刻（created_at = datetime.now(UTC)），直接切前
                // 19 个字符就是把 UTC 的墙上时间当本地时间显示（打包 exe 二次
                // 验收实测差 8 小时）。这里按本地时区显示，并保留一行 UTC 标注。
                const parts = timestampParts(p.created_at);
                return (
                  <tr key={p.id}>
                    <td className="report-id">{p.id}</td>
                    <td className="report-project">{p.apk_name}</td>
                    <td>
                      <span className={`badge ${p.status === "completed" ? "badge-success" : "badge-muted"}`}>
                        {p.status}
                      </span>
                    </td>
                    <td>{p.evidence_count} 条</td>
                    <td className="report-time">
                      {parts ? (
                        <>
                          <span className="report-time__local">
                            {parts.local} {parts.offset}
                          </span>
                          <span className="report-time__utc">UTC {parts.utc}</span>
                        </>
                      ) : (
                        <span className="report-time__local">时间未知</span>
                      )}
                    </td>
                    <td>
                      <div className="report-actions">
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={exporting !== null}
                          onClick={() => void doExport(p, "markdown")}
                        >
                          {exporting?.id === p.id && exporting.format === "markdown" ? "导出中…" : "导出 Markdown"}
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={exporting !== null}
                          onClick={() => void doExport(p, "json")}
                        >
                          {exporting?.id === p.id && exporting.format === "json" ? "导出中…" : "导出 JSON"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
