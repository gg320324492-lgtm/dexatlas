/**
 * 侧车桥接 — 前端与 Tauri Rust 壳之间关于后端进程的全部交互。
 *
 * Phase 5 W1：设置页读写后端命令配置（Tauri 本地配置 backend.json）并触发
 * 侧车重启；baseUrl 的端口解析在 api/client.ts。非 Tauri 环境（vite dev
 * 浏览器预览）下这些操作不可用，返回如实的结果对象而不是抛错——调用方
 * （设置页）按提示展示。
 */

/** 后端命令配置（对应 Rust 侧 backend.json 的 {command, args}）。 */
export interface BackendCommandConfig {
  command: string;
  args: string[];
}

/**
 * Tauri 侧 get_sidecar_status 的返回形状（serde camelCase）。
 *
 * 这也是 `sidecar:status` 事件的载荷形状 —— **同一份定义**，
 * 端口解析模块（api/sidecarEndpoint.ts）复用它，不要另起一份。
 */
export interface SidecarStatus {
  running: boolean;
  port: number | null;
  program: string | null;
  message: string;
  /**
   * 后端**根本没起来**（Rust 侧 spawn 失败，如命令不在 PATH）。
   *
   * 只有"从来没能启动"时为 true：还在启动中是 false，运行过之后崩溃退出
   * 也是 false（那时端口仍然知道，UI 如实显示退出即可）。
   * 可选是因为老壳没有这个字段 —— 那时按 false 处理。
   */
  failed?: boolean;
}

/** 是否运行在 Tauri WebView 内（与 api/client.ts 的判定保持一致）。 */
export function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function defaultConfig(): BackendCommandConfig {
  return { command: "python", args: ["-m", "dexatlas.workbench"] };
}

/** 读取后端命令配置；非 Tauri 或读取失败时返回默认值。 */
export async function loadBackendCommandConfig(): Promise<BackendCommandConfig> {
  if (!isTauriRuntime()) {
    return defaultConfig();
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const cfg = await invoke<Partial<BackendCommandConfig> | null>("get_backend_command");
    if (cfg && typeof cfg.command === "string" && cfg.command.trim()) {
      return {
        command: cfg.command,
        args: Array.isArray(cfg.args) ? cfg.args.filter((a): a is string => typeof a === "string") : [],
      };
    }
  } catch {
    // 旧壳没有该命令：按默认配置展示，保存时会如实提示不可用。
  }
  return defaultConfig();
}

export interface SaveOutcome {
  ok: boolean;
  message: string;
}

/** 保存后端命令配置并按新配置重启侧车。 */
export async function saveBackendCommandConfig(config: BackendCommandConfig): Promise<SaveOutcome> {
  const command = config.command.trim();
  if (!command) {
    return { ok: false, message: "后端命令不能为空。" };
  }
  if (!isTauriRuntime()) {
    return {
      ok: false,
      message: "当前是浏览器预览环境，后端命令配置仅在 Tauri 桌面应用内生效。",
    };
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    await invoke("set_backend_command", {
      command,
      args: config.args,
    });
    const status = await invoke<SidecarStatus>("restart_sidecar");
    return {
      ok: status.running,
      message: status.running ? `已保存，后端已按新命令启动（${status.message}）` : `已保存；${status.message}`,
    };
  } catch (err) {
    return { ok: false, message: `保存失败：${String(err)}` };
  }
}

/** 查询侧车当前状态；非 Tauri 环境返回 null。 */
export async function getSidecarStatus(): Promise<SidecarStatus | null> {
  if (!isTauriRuntime()) {
    return null;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return await invoke<SidecarStatus>("get_sidecar_status");
  } catch {
    return null;
  }
}
