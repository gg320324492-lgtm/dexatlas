/**
 * 侧车端口解析的单元测试 —— Phase 5 W1 打包 exe 验收的拦截网。
 *
 * 打包成 exe 真机验收（2026-11-25）发现的第二个缺陷：前端在**模块加载那一刻**
 * 就把 baseUrl 一次性锁到了 8618 回退端口上。侧车的端口是它启动之后才有的，
 * 于是后来侧车真的起来了，前端还是一直打在 8618（那可能压根是别人的后端）。
 *
 * 这份测试用**注入的假状态提供者**执行真实的等待逻辑：端口什么时候出现、
 * 壳说后端起不来、超时——三种收场都要有确定的结果。真的侧车进程和真的
 * Tauri 壳不在这里，也不必在。
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  sidecarBaseUrl,
  SIDECAR_PORT_POLL_MS,
  SIDECAR_PORT_WAIT_MS,
  waitForSidecarPort,
} from "./sidecarEndpoint";
import type { SidecarStatus } from "./sidecar";

/** 是不是 Tauri 壳：测试要能把它翻来覆去地切。 */
const runtime = vi.hoisted(() => ({ tauri: true }));

vi.mock("./sidecar", () => ({
  isTauriRuntime: () => runtime.tauri,
}));

/** 一个侧车状态。 */
function status(port: number | null, extra: Partial<SidecarStatus> = {}): SidecarStatus {
  return { running: port !== null, port, program: null, message: "", ...extra };
}

afterEach(() => {
  runtime.tauri = true;
  vi.useRealTimers();
});

describe("sidecarBaseUrl", () => {
  it("端口 → API 基地址", () => {
    expect(sidecarBaseUrl(8618)).toBe("http://127.0.0.1:8618/api");
    expect(sidecarBaseUrl(9123)).toBe("http://127.0.0.1:9123/api");
  });
});

describe("waitForSidecarPort —— 有界等待", () => {
  it("拿到端口就返回它", async () => {
    const provider = vi.fn(async () => status(9123));
    await expect(waitForSidecarPort(1000, 10, provider)).resolves.toBe(9123);
    expect(provider).toHaveBeenCalledTimes(1);
  });

  it("端口是 0 或 null 时继续等", async () => {
    let call = 0;
    const provider = vi.fn(async () => {
      call += 1;
      return call < 3 ? status(null) : status(9123);
    });
    await expect(waitForSidecarPort(1000, 10, provider)).resolves.toBe(9123);
    expect(provider.mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it("壳说后端起不来：立刻收场，不再等", async () => {
    const provider = vi.fn(async () => status(null, { failed: true }));
    await expect(waitForSidecarPort(8000, 250, provider)).resolves.toBeNull();
    expect(provider).toHaveBeenCalledTimes(1);
  });

  it("等不到就超时收场——等待是有界的", async () => {
    vi.useFakeTimers();
    const provider = vi.fn(async () => status(null));
    const pending = waitForSidecarPort(1000, 250, provider);
    await vi.advanceTimersByTimeAsync(5000);
    await expect(pending).resolves.toBeNull();
    // 有界：轮询次数与超时成正比，不是无限等。
    expect(provider.mock.calls.length).toBeLessThan(10);
  });

  it("非 Tauri 环境：没有壳就没有端口", async () => {
    runtime.tauri = false;
    const provider = vi.fn(async () => status(9123));
    await expect(waitForSidecarPort(1000, 10, provider)).resolves.toBeNull();
    expect(provider).not.toHaveBeenCalled();
  });
});

describe("等待的默认上限", () => {
  it("默认是有界的（8 秒 / 250 毫秒一次）", () => {
    expect(SIDECAR_PORT_WAIT_MS).toBe(8000);
    expect(SIDECAR_PORT_POLL_MS).toBe(250);
  });
});
