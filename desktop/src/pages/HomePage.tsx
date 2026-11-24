import { useCallback, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./HomePage.css";

interface RecentProject {
  id: string;
  name: string;
  package: string;
  status: "done" | "running" | "failed" | "partial";
  findings: number;
  time: string;
}

// 占位数据：真实数据接入由后续窗口完成。
const RECENT_PROJECTS: RecentProject[] = [
  {
    id: "demo-weather",
    name: "com.example.weather",
    package: "3 个后端 · 42 个类",
    status: "done",
    findings: 7,
    time: "2 小时前",
  },
  {
    id: "demo-payment",
    name: "com.acme.payment",
    package: "3 个后端 · 128 个类",
    status: "partial",
    findings: 15,
    time: "昨天",
  },
];

const STATUS_LABEL: Record<RecentProject["status"], { label: string; cls: string }> = {
  done: { label: "已完成", cls: "badge-success" },
  running: { label: "分析中", cls: "badge-info" },
  failed: { label: "失败", cls: "badge-danger" },
  partial: { label: "部分完成", cls: "badge-warning" },
};

/** 首页：拖拽上传 + 最近项目（补充单 2-1）。 */
export default function HomePage() {
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dragDepth = useRef(0);

  const acceptFile = useCallback((file: File | undefined | null) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".apk")) {
      setFileName(null);
      setError("仅支持 .apk 文件");
      return;
    }
    setError(null);
    setFileName(file.name);
    // TODO(Q2-M2): 调用 Tauri 后端启动分析任务。
  }, []);

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
        {fileName ? (
          <>
            <strong className="dropzone-file">{fileName}</strong>
            <span className="page-subtitle">文件已选择，点击「开始分析」进入分析页。</span>
            <div className="dropzone-actions">
              <Link className="btn btn-primary" to="/analysis">
                开始分析
              </Link>
              <button className="btn btn-secondary" onClick={() => setFileName(null)}>
                重新选择
              </button>
            </div>
          </>
        ) : (
          <>
            <strong>拖拽 APK 到此处</strong>
            <span className="page-subtitle">或</span>
            <label className="btn btn-primary dropzone-browse">
              浏览文件
              <input
                type="file"
                accept=".apk"
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
        <div className="card project-list-card">
          <table className="table">
            <thead>
              <tr>
                <th>项目</th>
                <th>规模</th>
                <th>状态</th>
                <th>发现</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {RECENT_PROJECTS.map((p) => {
                const st = STATUS_LABEL[p.status];
                return (
                  <tr key={p.id}>
                    <td>
                      <Link to={`/analysis/${p.id}`} className="project-link">
                        {p.name}
                      </Link>
                    </td>
                    <td className="text-secondary">{p.package}</td>
                    <td>
                      <span className={`badge ${st.cls}`}>{st.label}</span>
                    </td>
                    <td>
                      {p.findings > 0 ? (
                        <span className="badge badge-warning">{p.findings} 项</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="text-muted">{p.time}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
