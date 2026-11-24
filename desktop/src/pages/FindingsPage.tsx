import { Link } from "react-router-dom";
import "./FindingsPage.css";

interface Finding {
  id: string;
  title: string;
  severity: "high" | "medium" | "low" | "info";
  source: string;
  project: string;
}

// 占位数据：后续窗口接入真实发现列表。
const FINDINGS: Finding[] = [
  {
    id: "F-001",
    title: "明文传输敏感数据（HTTP）",
    severity: "high",
    source: "AndroidManifest.xml:42",
    project: "com.acme.payment",
  },
  {
    id: "F-002",
    title: "WebView 允许文件访问",
    severity: "medium",
    source: "MainActivity.smali:188",
    project: "com.acme.payment",
  },
  {
    id: "F-003",
    title: "可被外部调用的导出组件",
    severity: "medium",
    source: "AndroidManifest.xml:87",
    project: "com.example.weather",
  },
  {
    id: "F-004",
    title: "日志输出含设备标识",
    severity: "low",
    source: "Telemetry.smali:64",
    project: "com.example.weather",
  },
];

const SEVERITY: Record<Finding["severity"], { label: string; cls: string }> = {
  high: { label: "高", cls: "badge-danger" },
  medium: { label: "中", cls: "badge-warning" },
  low: { label: "低", cls: "badge-info" },
  info: { label: "提示", cls: "badge-muted" },
};

/** 证据页：跨项目发现总览（详情三栏结构在详情页落地）。 */
export default function FindingsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">证据</h1>
        <p className="page-subtitle">全部项目产生的发现，每一条都可回跳到来源代码。</p>
      </header>

      <div className="card findings-card">
        <table className="table">
          <thead>
            <tr>
              <th>编号</th>
              <th>发现</th>
              <th>等级</th>
              <th>来源</th>
              <th>项目</th>
            </tr>
          </thead>
          <tbody>
            {FINDINGS.map((f) => {
              const sev = SEVERITY[f.severity];
              return (
                <tr key={f.id}>
                  <td className="finding-id">{f.id}</td>
                  <td>
                    <Link to="/findings/detail" className="finding-link">
                      {f.title}
                    </Link>
                  </td>
                  <td>
                    <span className={`badge ${sev.cls}`}>{sev.label}</span>
                  </td>
                  <td className="finding-source">{f.source}</td>
                  <td className="finding-project">{f.project}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
