import { Link, useParams } from "react-router-dom";
import "./AnalysisPage.css";

interface Stage {
  key: string;
  label: string;
  state: "done" | "running" | "pending" | "failed";
}

interface BackendStatus {
  name: string;
  state: "ok" | "running" | "warn" | "error";
  detail: string;
}

// 占位数据：真实进度/日志/后端状态由后续窗口接入 Tauri 事件。
const STAGES: Stage[] = [
  { key: "upload", label: "上传与校验", state: "done" },
  { key: "apktool", label: "Apktool 资源与 Smali", state: "done" },
  { key: "jadx", label: "JADX 反编译", state: "running" },
  { key: "androguard", label: "Androguard 符号图", state: "pending" },
  { key: "evidence", label: "证据聚合", state: "pending" },
  { key: "report", label: "报告生成", state: "pending" },
];

const LOG_LINES = [
  "10:24:01  INFO  已接收 APK：com.example.weather (4.2 MB)",
  "10:24:02  INFO  SHA-256 校验完成：a3f1…9c02",
  "10:24:03  INFO  Apktool：解析 manifest 与资源表",
  "10:24:07  INFO  Apktool：smali 反编译完成（42 个类）",
  "10:24:08  INFO  JADX：启动 Java 反编译",
  "10:24:15  WARN  JADX：2 个方法反编译降级（goto 语句）",
  "10:24:16  INFO  JADX：继续处理…",
];

const BACKENDS: BackendStatus[] = [
  { name: "Apktool", state: "ok", detail: "v2.11.1 · 完成" },
  { name: "JADX", state: "running", detail: "运行中 · 68%" },
  { name: "Androguard", state: "warn", detail: "排队等待" },
];

const STAGE_BADGE: Record<Stage["state"], { label: string; cls: string }> = {
  done: { label: "完成", cls: "badge-success" },
  running: { label: "运行中", cls: "badge-info" },
  pending: { label: "等待", cls: "badge-muted" },
  failed: { label: "失败", cls: "badge-danger" },
};

const BACKEND_BADGE: Record<BackendStatus["state"], { label: string; cls: string }> = {
  ok: { label: "正常", cls: "badge-success" },
  running: { label: "运行中", cls: "badge-info" },
  warn: { label: "等待", cls: "badge-warning" },
  error: { label: "错误", cls: "badge-danger" },
};

/** 分析页：左侧阶段进度 + 中间实时日志 + 右侧后端状态（补充单 2-3）。 */
export default function AnalysisPage() {
  const { projectId } = useParams();

  return (
    <div className="page analysis-page">
      <header className="page-header analysis-header">
        <div>
          <h1 className="page-title">分析进行中</h1>
          <p className="page-subtitle">
            {projectId ? (
              <>
                项目 <code>{projectId}</code> · 任务已启动
              </>
            ) : (
              "等待上传 APK 后自动开始"
            )}
          </p>
        </div>
        <div className="analysis-actions">
          <button className="btn btn-secondary">暂停</button>
          <button className="btn btn-danger">取消</button>
        </div>
      </header>

      <div className="analysis-grid">
        <section className="card stage-card" aria-label="阶段进度">
          <h2 className="card-title">阶段进度</h2>
          <ol className="stage-list">
            {STAGES.map((s, i) => {
              const st = STAGE_BADGE[s.state];
              return (
                <li key={s.key} className={`stage-item is-${s.state}`}>
                  <span className="stage-index" aria-hidden="true">
                    {s.state === "done" ? "✓" : i + 1}
                  </span>
                  <span className="stage-label">{s.label}</span>
                  <span className={`badge ${st.cls}`}>{st.label}</span>
                </li>
              );
            })}
          </ol>
        </section>

        <section className="card log-card" aria-label="实时日志">
          <div className="log-head">
            <h2 className="card-title">实时日志</h2>
            <span className="badge badge-info">滚动更新</span>
          </div>
          <pre className="log-body" aria-live="polite">
            {LOG_LINES.join("\n")}
            {"\n"}
          </pre>
        </section>

        <section className="card backend-card" aria-label="后端状态">
          <h2 className="card-title">后端状态</h2>
          <ul className="backend-list">
            {BACKENDS.map((b) => {
              const st = BACKEND_BADGE[b.state];
              return (
                <li key={b.name} className="backend-item">
                  <div>
                    <div className="backend-name">{b.name}</div>
                    <div className="backend-detail">{b.detail}</div>
                  </div>
                  <span className={`badge ${st.cls}`}>{st.label}</span>
                </li>
              );
            })}
          </ul>
          <p className="backend-note">
            后端版本与路径等细节见 <Link to="/settings">设置</Link>。
          </p>
        </section>
      </div>
    </div>
  );
}
