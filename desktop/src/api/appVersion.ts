/**
 * 桌面壳自身的版本号。
 *
 * 设置页原来把「后端（分析核心）的版本」当作「这个应用的版本」显示，
 * 读者会认错：装出来的是 DexAtlas Studio 1.2.0，页面上写的却是后端的
 * 版本号，两个数各说各的（见 docs/desktop-packaging.md）。
 *
 * 这里读的是 Tauri 壳的 `app_info` 命令（Rust 侧返回 CARGO_PKG_VERSION），
 * 它是**这个应用**的版本号，与 MSI 的 ProductVersion、exe 的文件版本同源
 * （四处数字的一致性由 tests/test_desktop_version.py 断言）。
 *
 * 非 Tauri 环境（vite dev 浏览器预览）里没有这个命令，返回 null，
 * 页面如实说「拿不到」，不编一个版本号出来。
 */

import { isTauriRuntime } from "./sidecar";

/** Tauri 侧 `app_info` 命令的返回形状。 */
export interface AppInfo {
  name: string;
  version: string;
}

/** 读取桌面应用自身的版本；非 Tauri 环境或读取失败时返回 null。 */
export async function loadAppInfo(): Promise<AppInfo | null> {
  if (!isTauriRuntime()) {
    return null;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const info = await invoke<AppInfo>("app_info");
    if (!info || typeof info.version !== "string" || !info.version.trim()) {
      return null;
    }
    return {
      name: typeof info.name === "string" ? info.name : "",
      version: info.version.trim(),
    };
  } catch {
    return null;
  }
}
