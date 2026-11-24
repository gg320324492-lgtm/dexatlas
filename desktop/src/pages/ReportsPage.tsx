import { Link } from "react-router-dom";
import "./ReportsPage.css";

interface ReportEntry {
  id: string;
  project: string;
  format: "Markdown" | "JSON";
  findings: number;
  createdAt: string;
}

// 占位数据：报告导出动作由后续窗口接入 Tauri 文件对话框。
const REPORTS: ReportEntry[] = [
  {
    id: "R-2026-1124-01",
    project: "com.example.weather",
    format: "Markdown",
    findings: 7,
    createdAt: "2026-11-24 10:31",
  },
  {
    id: "R-2026-1123-03",
    project: "com.acme.payment",
    format: "JSON",
    findings: 15,
    createdAt: "2026-11-23 18:05",
  },
];

/** 报告页：历史报告与导出入口。 */
export default function ReportsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">报告</h1>
        <p className="page-subtitle">已生成的分析报告，可导出为 Markdown / JSON。</p>
      </header>

      <div className="card reports-card">
        <table className="table">
          <thead>
            <tr>
              <th>报告编号</th>
              <th>项目</th>
              <th>格式</th>
              <th>发现数</th>
              <th>生成时间</th>
              <th>
                <span className="visually-hidden">操作</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {REPORTS.map((r) => (
              <tr key={r.id}>
                <td className="report-id">{r.id}</td>
                <td className="report-project">{r.project}</td>
                <td>
                  <span className="badge badge-muted">{r.format}</span>
                </td>
                <td>{r.findings} 项</td>
                <td className="report-time">{r.createdAt}</td>
                <td>
                  <div className="report-actions">
                    <Link className="btn btn-secondary btn-sm" to="/reports/view">
                      查看
                    </Link>
                    <button className="btn btn-primary btn-sm">导出</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
