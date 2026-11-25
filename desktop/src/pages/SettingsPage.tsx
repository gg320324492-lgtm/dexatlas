import { useCallback, useEffect, useState } from "react";
import { LoadingState } from "../components/states/LoadingState";
import { ApiError, dexatlas } from "../api";
import type { BackendInfo, BackendCommandConfig, WorkbenchHealth } from "../api";
import { loadBackendCommandConfig, saveBackendCommandConfig, getSidecarStatus } from "../api";
import "./SettingsPage.css";

/**
 * 设置页：版本信息与后端配置收纳处（补充单 2-5）。
 * Q2-M3-T1：不再内置假配置。后端清单来自 GET /api/backends；当前 8618
 * 的 workbench 未提供该端点（HTTP 404），页面如实显示"该端点在后端未提供"。
 * 版本信息来自 GET /api/health（{version, workspace}）。
 * Phase 5 W1：新增 DexAtlas 后端命令路径配置（Tauri 本地配置 backend.json），
 * 保存后按新配置重启侧车；浏览器/dev 环境保存仅本地提示，不写真实配置。
 */
export default function SettingsPage() {
  const [health, setHealth] = useState<WorkbenchHealth | null>(null);
  const [backends, setBackends] = useState<BackendInfo | null>(null);
  const [backendsUnavailable, setBackendsUnavailable] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [command, setCommand] = useState<BackendCommandConfig>({
    command: "python",
    args: ["-m", "dexatlas.workbench"],
  });
  const [commandDirty, setCommandDirty] = useState(false);
  const [commandSaving, setCommandSaving] = useState(false);
  const [commandNotice, setCommandNotice] = useState<string | null>(null);
  const [sidecarLine, setSidecarLine] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBackendsUnavailable(null);
    const results = await Promise.allSettled([dexatlas.getHealth(), dexatlas.getBackends()]);
    if (results[0].status === "fulfilled") {
      setHealth(results[0].value);
    } else {
      const e = results[0].reason;
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e));
    }
    if (results[1].status === "fulfilled") {
      setBackends(results[1].value);
    } else {
      const e = results[1].reason;
      // 404 = 后端没有这个端点（当前 workbench 即如此），如实呈现而非编造清单
      setBackendsUnavailable(
        e instanceof ApiError && e.status === 404
          ? "该端点在后端未提供（GET /api/backends 返回 404）"
          : e instanceof ApiError
            ? `读取失败（${e.status}: ${e.message}）`
            : `读取失败（${String(e)}）`,
      );
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadBackendCommandConfig().then(setCommand);
    let cancelled = false;
    const poll = async () => {
      const status = await getSidecarStatus();
      if (!cancelled) {
        setSidecarLine(status ? `${status.running ? "运行中" : "未运行"}${status.port ? ` · 127.0.0.1:${status.port}` : ""} · ${status.message}` : null);
      }
    };
    void poll();
    const timer = window.setInterval(poll, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const handleSaveCommand = useCallback(async () => {
    setCommandSaving(true);
    setCommandNotice(null);
    const outcome = await saveBackendCommandConfig(command);
    setCommandNotice(outcome.message);
    setCommandSaving(false);
    setCommandDirty(false);
  }, [command]);

  return (
    <div className="page">
      <header className="page-header">
        <h1 className="page-title">设置</h1>
        <p className="page-subtitle">分析后端、应用偏好与版本信息。</p>
      </header>

      <section className="card">
        <h2 className="card-title">分析后端</h2>
        {loading ? (
          <LoadingState lines={3} label="正在读取后端配置" />
        ) : backendsUnavailable ? (
          <p className="settings-unavailable" role="status">
            {backendsUnavailable}
          </p>
        ) : backends ? (
          <ul className="backend-config-list">
            {["jadx", "apktool", "androguard"].map((key) => {
              const available = backends.available.includes(key);
              const version = backends.versions[key] ?? null;
              return (
                <li key={key} className="backend-config-item">
                  <div className="backend-config-main">
                    <strong>{key}</strong>
                    <code className="backend-path">
                      {available ? (version ? `已安装 · v${version}` : "已安装") : "未安装或未配置"}
                    </code>
                  </div>
                  <span className={`badge ${available ? "badge-success" : "badge-muted"}`}>
                    {available ? "可用" : "缺失"}
                  </span>
                </li>
              );
            })}
            {backends.missing.length > 0 && (
              <li className="backend-config-item">
                <div className="backend-config-main">
                  <code className="backend-path">缺失后端：{backends.missing.join("、")}</code>
                </div>
              </li>
            )}
          </ul>
        ) : (
          <p className="settings-unavailable" role="alert">
            {error ?? "后端状态不可用。"}
          </p>
        )}
      </section>

      <section className="card">
        <h2 className="card-title">DexAtlas 后端</h2>
        {sidecarLine ? (
          <p className="settings-unavailable" role="status">
            侧车：{sidecarLine}
          </p>
        ) : null}
        <p className="pref-desc">
          桌面应用启动时按此命令拉起 DexAtlas 后端（侧车进程）。默认
          <code className="backend-path"> python -m dexatlas.workbench </code>
          ；若 Python 不在 PATH 或后端装在虚拟环境，可改为完整路径（如
          <code className="backend-path"> E:\Dexatlas\.venv\Scripts\python.exe -m dexatlas.workbench</code>
          ）。
        </p>
        <div className="backend-command-row">
          <label className="backend-command-label" htmlFor="backend-command-input">
            后端命令
          </label>
          <input
            id="backend-command-input"
            className="backend-command-input"
            type="text"
            spellCheck={false}
            value={command.command}
            onChange={(e) => {
              setCommand({ ...command, command: e.target.value });
              setCommandDirty(true);
            }}
            placeholder="python"
          />
        </div>
        <div className="backend-command-row">
          <label className="backend-command-label" htmlFor="backend-args-input">
            启动参数
          </label>
          <input
            id="backend-args-input"
            className="backend-command-input"
            type="text"
            spellCheck={false}
            value={command.args.join(" ")}
            onChange={(e) => {
              setCommand({ ...command, args: e.target.value.split(/\s+/).filter(Boolean) });
              setCommandDirty(true);
            }}
            placeholder="-m dexatlas.workbench"
          />
        </div>
        <div className="backend-command-actions">
          <button
            type="button"
            className="backend-command-save"
            disabled={!commandDirty || commandSaving}
            onClick={() => void handleSaveCommand()}
          >
            {commandSaving ? "保存中…" : "保存并重启后端"}
          </button>
          {commandNotice ? (
            <span className="settings-unavailable" role="status">
              {commandNotice}
            </span>
          ) : null}
        </div>
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
            <dd>
              {health ? (
                <>
                  v{health.version}
                  {health.workspace ? <span className="settings-workspace"> · 工作区 {health.workspace}</span> : null}
                </>
              ) : (
                <span className="settings-unavailable">{error ?? "读取中…"}</span>
              )}
            </dd>
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
