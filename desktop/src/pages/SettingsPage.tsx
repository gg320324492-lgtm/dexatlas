import { useState } from "react";
import "./SettingsPage.css";

interface BackendConfig {
  key: "apktool" | "jadx" | "androguard";
  name: string;
  path: string;
  enabled: boolean;
}

// 占位状态：真实配置读写（Tauri store / 后端命令）由后续窗口完成。
const INITIAL_BACKENDS: BackendConfig[] = [
  { key: "apktool", name: "Apktool", path: "C:\\tools\\apktool\\apktool.bat", enabled: true },
  { key: "jadx", name: "JADX", path: "C:\\tools\\jadx\\bin\\jadx.bat", enabled: true },
  { key: "androguard", name: "Androguard", path: "(内置 Python 后端)", enabled: true },
];

/** 设置页：版本信息与后端配置收纳处（补充单 2-5）。 */
export default function SettingsPage() {
  const [backends, setBackends] = useState(INITIAL_BACKENDS);

  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">设置</h1>
        <p className="page-subtitle">分析后端、应用偏好与版本信息。</p>
      </header>

      <section className="card">
        <h2 className="card-title">分析后端</h2>
        <ul className="backend-config-list">
          {backends.map((b, i) => (
            <li key={b.key} className="backend-config-item">
              <div className="backend-config-main">
                <strong>{b.name}</strong>
                <code className="backend-path">{b.path}</code>
              </div>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={b.enabled}
                  onChange={(e) => {
                    const next = [...backends];
                    next[i] = { ...b, enabled: e.target.checked };
                    setBackends(next);
                  }}
                />
                <span className="switch-track" aria-hidden="true" />
                <span className="visually-hidden">启用 {b.name}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2 className="card-title">应用偏好</h2>
        <div className="pref-row">
          <div>
            <strong>主题</strong>
            <p className="pref-desc">当前版本使用固定的浅色工作室主题。</p>
          </div>
          <span className="badge badge-muted">浅色（默认）</span>
        </div>
        <div className="pref-row">
          <div>
            <strong>界面语言</strong>
            <p className="pref-desc">界面文案当前为简体中文。</p>
          </div>
          <span className="badge badge-muted">简体中文</span>
        </div>
      </section>

      <section className="card">
        <h2 className="card-title">关于</h2>
        <dl className="about-list">
          <div>
            <dt>应用</dt>
            <dd>DexAtlas Studio</dd>
          </div>
          <div>
            <dt>版本</dt>
            <dd>v1.0.2 · Q2 原型</dd>
          </div>
          <div>
            <dt>分析核心</dt>
            <dd>与 CLI / API / MCP 共用同一分析核心</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
