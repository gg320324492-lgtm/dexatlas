/**
 * 客户端的侧车端点解析 —— 「不在构造时锁死」与「端口变化重写」。
 *
 * 这两条原先是 `tests/test_desktop_sidecar_endpoint.py` 里的源码断言
 * （「源码里有 `this.baseUrl = ...port` 就算过」）。这里改成真的构造一个
 * 客户端、真的把端口事件喂进去，看 baseUrl 到底变没变——同一批性质，
 * 断言的是行为。
 *
 * 侧车端点模块（./sidecarEndpoint）在这里被替换成假的：它要等的那个侧车进程
 * 在测试里并不存在，而客户端**怎么用**它才是这里要验的东西。
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { DexAtlasClient } from "./client";
import type { SidecarStatus } from "./sidecar";

/** 假侧车端点模块：记录订阅回调，等测试把端口事件喂进来。 */
const mocks = vi.hoisted(() => ({
  emit: null as ((status: { running: boolean; port: number | null }) => void) | null,
  waitForSidecarPort: vi.fn(async (): Promise<number | null> => null),
  subscribeSidecarStatus: vi.fn(
    async (onStatus: (status: { running: boolean; port: number | null }) => void) => {
      mocks.emit = onStatus;
      return () => {};
    },
  ),
}));

vi.mock("./sidecarEndpoint", () => ({
  SIDECAR_PORT_RETRY_WAIT_MS: 2000,
  sidecarBaseUrl: (port: number) => `http://127.0.0.1:${port}/api`,
  waitForSidecarPort: mocks.waitForSidecarPort,
  subscribeSidecarStatus: mocks.subscribeSidecarStatus,
}));

/** 构造客户端并等它把侧车那套异步流程跑完。 */
async function makeClient(baseUrl = "http://127.0.0.1:8618/api"): Promise<DexAtlasClient> {
  const client = new DexAtlasClient({ baseUrl });
  await vi.waitFor(() => expect(mocks.subscribeSidecarStatus).toHaveBeenCalled());
  return client;
}

/** 一个侧车状态事件。 */
function status(port: number | null): SidecarStatus {
  return { running: port !== null, port, program: null, message: "" };
}

beforeEach(() => {
  mocks.emit = null;
  mocks.waitForSidecarPort.mockReset();
  mocks.waitForSidecarPort.mockResolvedValue(null);
  mocks.subscribeSidecarStatus.mockClear();
});

describe("构造时的侧车解析", () => {
  it("端口还拿不到时不锁死回退地址", async () => {
    const client = await makeClient();
    // 构造这一刻侧车还没起来，回退地址先用着。
    expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:8618/api");
  });

  it("构造时就能拿到端口，直接用它", async () => {
    mocks.waitForSidecarPort.mockResolvedValue(8619);
    const client = await makeClient();
    await vi.waitFor(() =>
      expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:8619/api"),
    );
  });

  it("客户端订阅了端口事件", async () => {
    await makeClient();
    expect(mocks.subscribeSidecarStatus).toHaveBeenCalledTimes(1);
    expect(mocks.waitForSidecarPort).toHaveBeenCalledTimes(1);
  });
});

describe("端口变化时重写 baseUrl", () => {
  it("端口后来出现：回退地址被改写", async () => {
    const client = await makeClient();
    expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:8618/api");

    mocks.emit?.(status(9123));

    expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:9123/api");
  });

  it("侧车重启换了端口：baseUrl 再改一次", async () => {
    const client = await makeClient();

    mocks.emit?.(status(9123));
    expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:9123/api");

    mocks.emit?.(status(9124));
    expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:9124/api");
  });

  it("端口没有的事件（null）不改写 baseUrl", async () => {
    const client = await makeClient();
    mocks.emit?.(status(9123));
    mocks.emit?.(status(null));
    expect(client.effectiveBaseUrl).toBe("http://127.0.0.1:9123/api");
  });
});
