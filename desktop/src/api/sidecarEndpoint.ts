/**
 * 侧车端点解析 —— 前端怎么找到后端的**真实**端口。
 *
 * Phase 5 W1 打包 exe 真机验收（2026-11-25）的教训：侧车的端口是**启动之后**
 * 才有的，模块加载那一刻还拿不到。若那时把 baseUrl 一次性锁到 8618 回退，
 * 侧车后来真的起来了，前端也永远打在 8618 上（那可能压根是别人的后端）。
 *
 * 这里提供两件事：
 * - {@link waitForSidecarPort}：首次请求前**有界等待**端口出现。拿不到就
 *   返回 null（调用方回退），但回退**不是终态**。
 * - {@link subscribeSidecarStatus}：订阅 `sidecar:status`。侧车重启会换端口，
 *   端口一变就通知调用方重新解析。
 *
 * 非 Tauri 环境（vite dev 浏览器预览）这里一律返回 null：dev 下由 vite 代理
 * 转发，前端不需要知道端口。
 */

import { isTauriRuntime } from "./sidecar";
import type { SidecarStatus } from "./sidecar";

/**
 * 侧车状态的形状**只有一份**：`SidecarStatus`（api/sidecar.ts）。
 *
 * 那里同时是 Rust 侧 `get_sidecar_status` 的返回形状与 `sidecar:status`
 * 事件的载荷形状；这里不再另起一份，否则改 Rust 载荷时容易只改一处。
 */

/** 侧车端口等待上限（毫秒）。超时后回退，但事件仍会把它改回来。 */
export const SIDECAR_PORT_WAIT_MS = 8000;

/** 请求失败后重新解析端口的上限（毫秒）——比首次等待短。 */
export const SIDECAR_PORT_RETRY_WAIT_MS = 2000;

/** 轮询间隔（毫秒）。 */
export const SIDECAR_PORT_POLL_MS = 250;

/** 侧车端口 → API 基地址。 */
export function sidecarBaseUrl(port: number): string {
  return `http://127.0.0.1:${port}/api`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** 读一次侧车状态；读不到（老壳/非 Tauri）返回 null。 */
export async function querySidecarStatus(): Promise<SidecarStatus | null> {
  if (!isTauriRuntime()) {
    return null;
  }
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    const status = await invoke<SidecarStatus | null>("get_sidecar_status");
    return status ?? null;
  } catch {
    // 命令不可用（旧壳）：按"拿不到侧车端口"处理。
    return null;
  }
}

/**
 * 侧车状态的读取方式。
 *
 * 默认是 {@link querySidecarStatus}（Tauri 的 `get_sidecar_status`）。单元测试
 * 注入一个假的提供者，于是「有界等待」这套逻辑可以被直接执行——不必真的起
 * 一个侧车进程，也不必真的装一个 Tauri 壳。
 */
export type SidecarStatusProvider = () => Promise<SidecarStatus | null>;

/**
 * 有界等待侧车端口。
 *
 * 返回端口号；等不到就返回 null——三种收场：拿到端口、壳说后端起不来
 * （`failed`）、超时。**返回 null 不等于"永远没有"**：调用方仍应订阅事件，
 * 端口后来出现时照样能改写 baseUrl。
 *
 * @param timeoutMs 等待上限（毫秒）
 * @param pollMs 轮询间隔（毫秒）
 * @param statusProvider 状态来源（测试注入用；默认走 Tauri）
 */
export async function waitForSidecarPort(
  timeoutMs: number = SIDECAR_PORT_WAIT_MS,
  pollMs: number = SIDECAR_PORT_POLL_MS,
  statusProvider: SidecarStatusProvider = querySidecarStatus,
): Promise<number | null> {
  if (!isTauriRuntime()) {
    return null;
  }
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const status = await statusProvider();
    const port = status?.port;
    if (typeof port === "number" && port > 0) {
      return port;
    }
    if (status?.failed) {
      // 后端确定起不来，等下去也没有端口。
      return null;
    }
    if (Date.now() >= deadline) {
      return null;
    }
    await sleep(pollMs);
  }
}

/**
 * 订阅 `sidecar:status`，端口出现或变化时回调。
 *
 * 返回取消订阅的函数。非 Tauri 环境返回空函数（什么都不用取消）。
 */
export async function subscribeSidecarStatus(
  onStatus: (status: SidecarStatus) => void,
): Promise<() => void> {
  if (!isTauriRuntime()) {
    return () => {};
  }
  try {
    const { listen } = await import("@tauri-apps/api/event");
    const unlisten = await listen<SidecarStatus>("sidecar:status", (event) => {
      onStatus(event.payload);
    });
    return unlisten;
  } catch {
    // 老壳没有事件（或订阅失败）：退回轮询路径，不影响可用性。
    return () => {};
  }
}
