/**
 * 首页上传流程的 DOM 断言 —— 「重复上传的提示用户看不见」这条缺陷的回归网。
 *
 * 【为什么这条非要 DOM】
 * 这条缺陷不是"函数返回错了"，而是"提示渲染了但用户看不见"：旧实现在
 * `setError(...)` 之后紧接 `navigate(...)`，路由一变首页被卸载，那句话跟着
 * 组件一起消失。纯逻辑测试看不见这种消失——它只看函数返回值。所以这里渲染
 * 真的组件、真的派发一次 drop 事件，然后问 DOM：**这句话还在吗？用户还在
 * 首页吗？去已有项目的入口在吗？**
 *
 * 打包 exe 的实测（docs/reports/phase5-crash-and-race-paths.md）里，802 次
 * 采样 0 次抓到这句提示——正是"它渲染了，但没有人看得见"。
 *
 * 【环境】
 * 只有这一个文件需要 DOM（文件头的 `// @vitest-environment jsdom`），
 * 其余测试仍是 node 环境的纯逻辑测试。
 */

// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import HomePage from "./HomePage";

/** React 19 的 act 需要这个标志，否则会警告"当前测试环境不支持 act"。 */
(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

/** 后端 API 的替身：只接首页用到的两个方法。 */
const mocks = vi.hoisted(() => ({
  analyzeUpload: vi.fn(),
  listProjects: vi.fn(),
}));

vi.mock("../api", () => ({
  dexatlas: {
    analyzeUpload: mocks.analyzeUpload,
    listProjects: mocks.listProjects,
  },
  describeError: (err: unknown) => (err instanceof Error ? err.message : String(err)),
}));

/** 一个 64 位十六进制的 sha256（后端返回的就是这个形状）。 */
const SHA = "abcdef0123456789" + "0".repeat(48);

let container: HTMLDivElement | null = null;
let root: Root | null = null;

afterEach(async () => {
  const mounted = root;
  root = null;
  if (mounted) {
    await act(async () => {
      mounted.unmount();
    });
  }
  if (container) {
    container.remove();
    container = null;
  }
  mocks.analyzeUpload.mockReset();
  mocks.listProjects.mockReset();
});

/** 分析页的替身：路由到了这里就说明确实跳走了。 */
function AnalysisStub() {
  const { projectId } = useParams();
  return <div data-testid="analysis-page">{`分析页 ${projectId ?? ""}`}</div>;
}

/** 渲染首页（带路由，好知道用户被带到哪儿去了）。 */
async function renderHome(): Promise<void> {
  container = document.createElement("div");
  document.body.appendChild(container);
  const mounted = createRoot(container);
  root = mounted;
  await act(async () => {
    mounted.render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/analysis/:projectId" element={<AnalysisStub />} />
        </Routes>
      </MemoryRouter>,
    );
  });
}

/** 往拖拽区派发一次 drop（jsdom 没有 DataTransfer，用一个带 files 的假事件）。 */
function dropApk(name = "sample.apk"): void {
  const zone = container?.querySelector('[aria-label="上传 APK"]');
  if (!zone) throw new Error("首页上找不到拖拽区");
  const file = new File([new Uint8Array([0x50, 0x4b, 0x03, 0x04])], name, {
    type: "application/vnd.android.package-archive",
  });
  const event = new Event("drop", { bubbles: true, cancelable: true });
  Object.defineProperty(event, "dataTransfer", {
    value: { files: [file], types: ["Files"] },
  });
  zone.dispatchEvent(event);
}

/** 让 analyzeUpload 的 then/catch/finally 链跑完（微任务 + 一个宏任务）。 */
async function settle(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("首页上传：重复上传的提示", () => {
  it("同一个 APK 再传一次时，提示留在页面上，用户没被带走", async () => {
    mocks.listProjects.mockResolvedValue([]);
    mocks.analyzeUpload.mockResolvedValue({
      project_id: "p-dup",
      status: "completed",
      apk_sha256: SHA,
      already_analysed: true,
    });

    await renderHome();
    await act(async () => {
      dropApk();
    });
    await settle();

    // 1) 提示确实在 DOM 里，而且是会被立刻播报的 alert（不是悄悄溜走的一行字）。
    const alert = container?.querySelector('[role="alert"]');
    expect(alert, "重复上传后必须有一条提示留在页面上").not.toBeNull();
    expect(alert?.textContent ?? "").toContain("已经分析过");
    expect(alert?.textContent ?? "").toContain(SHA.slice(0, 12));

    // 2) 用户没有被带走：还在首页（跳走 = 那句话跟着组件一起消失）。
    expect(container?.querySelector('[data-testid="analysis-page"]')).toBeNull();

    // 3) 去已有项目的入口在，且指向那个项目。
    const link = container?.querySelector('a[href="/analysis/p-dup"]');
    expect(link?.textContent ?? "", "提示里要有去已有项目的入口").toContain("打开已有项目");
  });

  it("第一次分析（不是重复）仍然跳到分析页", async () => {
    mocks.listProjects.mockResolvedValue([]);
    mocks.analyzeUpload.mockResolvedValue({
      project_id: "p-new",
      status: "running",
      apk_sha256: SHA,
      already_analysed: false,
    });

    await renderHome();
    await act(async () => {
      dropApk();
    });
    await settle();

    const landed = container?.querySelector('[data-testid="analysis-page"]');
    expect(landed?.textContent ?? "", "新分析仍然要跳到分析页").toContain("p-new");
  });
});
