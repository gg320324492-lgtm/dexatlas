/**
 * 阶段映射的单元测试 —— Phase 5 W2 复测 P1/P3 的拦截网。
 *
 * 这张场景表原先住在 `tests/test_desktop_stage_mapping.py`：Python 起一个 Node
 * 进程，把场景喂给 `desktop/src/stages.js`，再逐条断言。桌面端有了自己的
 * 测试框架之后，同一张表在这里跑——断言的是**函数的行为**，不是源码里有没有
 * 某个字符串。
 *
 * 复测报告（`.scratch/phase5-w2-retest.md` §P1）里那类回归——完成态下「证据」
 * 格显示「待处理」，而同一页面顶部写着「已完成」、横幅写着「12 条证据」——
 * 就是这张表拦住的（9/9 复现）。
 */

import { describe, expect, it } from "vitest";
import * as stagesModule from "./stages";
import {
  deriveBackends,
  deriveStageBadge,
  deriveStagesFromRun,
  isTerminalStatus,
  pollUntilTerminal,
  STAGES,
} from "./stages";
import type { RunStageEvent } from "./api/types";

/** 页面上的五个格子，顺序即页面上的顺序。 */
const SLOTS = [
  "collect",
  "parse-apktool",
  "index",
  "decompile-jadx",
  "report",
] as const;

/** 一个阶段事件；`finished=false` 表示这个阶段还没结束。 */
function stage(name: string, finished = true): RunStageEvent {
  return {
    stage: name,
    started_at: "2026-11-25T10:00:00Z",
    finished_at: finished ? "2026-11-25T10:00:01Z" : null,
  };
}

/** 一个 run 的最小事实。 */
function run(status: string, completeness = "complete", errors?: unknown) {
  return errors === undefined
    ? { status, completeness }
    : { status, completeness, errors };
}

/** 后端会发出的全部阶段，顺序即 pipeline 顺序。 */
const ALL_STAGES = [
  "inspect",
  "parse-apktool",
  "index-androguard",
  "decompile-jadx",
  "publish",
];

/** 完成的 run：每个阶段都结束了。 */
const COMPLETED_EVENTS = ALL_STAGES.map((name) => stage(name));
/** 正在跑 JADX（复测报告 t=5044ms 的采样点）。 */
const AT_JADX_EVENTS = [
  stage("inspect"),
  stage("parse-apktool"),
  stage("index-androguard"),
  stage("decompile-jadx", false),
];
/** 正在跑 Apktool（t=2204ms）。 */
const AT_APKTOOL_EVENTS = [stage("inspect"), stage("parse-apktool", false)];
/** 正在跑 Androguard（t=3011ms）。 */
const AT_INDEX_EVENTS = [
  stage("inspect"),
  stage("parse-apktool"),
  stage("index-androguard", false),
];
/** 跑 Apktool 时失败。 */
const FAILED_AT_APKTOOL_EVENTS = [stage("inspect"), stage("parse-apktool", false)];
/** 跑 JADX 时失败——证据格前一个阶段，也是旧推断把「证据」留在「进行中」
 *  的那个场景（run 其实已经结束了）。 */
const FAILED_AT_JADX_EVENTS = [
  stage("inspect"),
  stage("parse-apktool"),
  stage("index-androguard"),
  stage("decompile-jadx", false),
];
/** 跑 Androguard 时被取消。 */
const CANCELLED_AT_INDEX_EVENTS = [
  stage("inspect"),
  stage("parse-apktool"),
  stage("index-androguard", false),
];
/** 发布报告时失败。 */
const FAILED_AT_PUBLISH_EVENTS = [
  stage("inspect"),
  stage("parse-apktool"),
  stage("index-androguard"),
  stage("decompile-jadx"),
  stage("publish", false),
];

describe("deriveStagesFromRun —— 有阶段事件（stages 端点）", () => {
  it("完成态五格全完成，每格对应后端的一个推进点", () => {
    const { states } = deriveStagesFromRun(run("completed"), COMPLETED_EVENTS);
    expect(states).toEqual({
      collect: "done",
      "parse-apktool": "done",
      index: "done",
      "decompile-jadx": "done",
      report: "done",
    });
  });

  it("运行中「反编译」格进行中（复测报告 t=5044ms 的采样）", () => {
    const { states } = deriveStagesFromRun(run("running"), AT_JADX_EVENTS);
    expect(states).toEqual({
      collect: "done",
      "parse-apktool": "done",
      index: "done",
      "decompile-jadx": "running",
      report: "pending",
    });
  });

  it("还没走到的阶段保持待处理", () => {
    const atApktool = deriveStagesFromRun(run("running"), AT_APKTOOL_EVENTS);
    expect(atApktool.states["parse-apktool"]).toBe("running");
    expect(atApktool.states.index).toBe("pending");
    expect(atApktool.states["decompile-jadx"]).toBe("pending");
    expect(atApktool.states.report).toBe("pending");

    const atIndex = deriveStagesFromRun(run("running"), AT_INDEX_EVENTS);
    expect(atIndex.states.index).toBe("running");
    expect(atIndex.states["decompile-jadx"]).toBe("pending");
  });

  it("失败的 run 不会把某个格子留在「进行中」", () => {
    const atApktool = deriveStagesFromRun(run("failed"), FAILED_AT_APKTOOL_EVENTS);
    expect(atApktool.states.collect).toBe("done");
    expect(atApktool.states["parse-apktool"]).toBe("error");
    expect(atApktool.states.index).toBe("pending");
    expect(atApktool.states["decompile-jadx"]).toBe("pending");
    expect(atApktool.states.report).toBe("pending");

    // 跑 JADX 时失败：反编译格标失败，报告格还没到。
    const atJadx = deriveStagesFromRun(run("failed"), FAILED_AT_JADX_EVENTS);
    expect(atJadx.states.collect).toBe("done");
    expect(atJadx.states["parse-apktool"]).toBe("done");
    expect(atJadx.states.index).toBe("done");
    expect(atJadx.states["decompile-jadx"]).toBe("error");
    expect(atJadx.states.report).toBe("pending");
  });

  it("取消的 run 同样不会把某个格子留在「进行中」", () => {
    const { states } = deriveStagesFromRun(run("cancelled"), CANCELLED_AT_INDEX_EVENTS);
    expect(states.collect).toBe("done");
    expect(states["parse-apktool"]).toBe("done");
    expect(states.index).toBe("error");
    expect(states["decompile-jadx"]).toBe("pending");
    expect(states.report).toBe("pending");
  });

  it("发布阶段失败时，报告格标失败", () => {
    const { states } = deriveStagesFromRun(run("failed"), FAILED_AT_PUBLISH_EVENTS);
    expect(states["decompile-jadx"]).toBe("done");
    expect(states.report).toBe("error");
  });

  it("同一个完成状态在新旧 run 上看起来一样", () => {
    // 复测报告 §P1：新 run 走 stages 路径显示「证据 · 待处理」，旧 run 走兜底
    // 显示五格全「已完成」——同一个状态，两种显示。
    const withStages = deriveStagesFromRun(run("completed"), COMPLETED_EVENTS);
    const withoutStages = deriveStagesFromRun(run("completed"), []);
    expect(withStages.states).toEqual(withoutStages.states);
  });

  it("completeness = partial 时标出没能做完的那一格", () => {
    // 后端没有点名是哪一件工具出的问题，就落在报告格上。
    const { states, partialLabels } = deriveStagesFromRun(
      run("completed", "partial"),
      COMPLETED_EVENTS,
    );
    expect(states.report).toBe("skipped");
    expect(partialLabels.report).toBe("部分");
  });

  it("partial 且点名了工具时，标的是那一格", () => {
    const { states, partialLabels } = deriveStagesFromRun(
      run("completed", "partial", ["jadx: 反编译失败"]),
      COMPLETED_EVENTS,
    );
    expect(states["decompile-jadx"]).toBe("skipped");
    expect(partialLabels["decompile-jadx"]).toBe("部分");
    expect(states.report).toBe("done");
  });
});

describe("deriveStagesFromRun —— 没有阶段事件（旧 run 走状态兜底）", () => {
  it("完成的 run 五格全完成", () => {
    const { states } = deriveStagesFromRun(run("completed"), []);
    expect(states).toEqual({
      collect: "done",
      "parse-apktool": "done",
      index: "done",
      "decompile-jadx": "done",
      report: "done",
    });
  });

  it("运行中的 run 走粗粒度映射", () => {
    const { states } = deriveStagesFromRun(run("running"), []);
    expect(states.collect).toBe("done");
    expect(states["parse-apktool"]).toBe("running");
    expect(states.index).toBe("pending");
  });

  it("失败的 run 把解析格标失败", () => {
    const { states } = deriveStagesFromRun(run("failed"), []);
    expect(states.collect).toBe("done");
    expect(states["parse-apktool"]).toBe("error");
  });

  it("还没开始的 run 不许声称某个阶段失败了", () => {
    const { states } = deriveStagesFromRun(run("pending"), []);
    expect(states).toEqual({
      collect: "pending",
      "parse-apktool": "pending",
      index: "pending",
      "decompile-jadx": "pending",
      report: "pending",
    });
  });
});

describe("deriveStagesFromRun —— 没有 run", () => {
  it("五格全是待处理", () => {
    const { states } = deriveStagesFromRun(null, null);
    expect(states).toEqual({
      collect: "pending",
      "parse-apktool": "pending",
      index: "pending",
      "decompile-jadx": "pending",
      report: "pending",
    });
  });
});

describe("deriveStageBadge —— 角标如实说明数据来源", () => {
  it("有 stages 时说清楚：事件是后端给的，对应关系是前端映射的", () => {
    const badge = deriveStageBadge("stages");
    expect(badge.text).toBe("阶段推进：后端阶段事件 + 前端映射");
    // 旧文案整句都说成后端给的（"后端真实阶段事件"），读者分不清哪部分是
    // 后端事实、哪部分是前端映射：这条断言在旧实现上会红。
    expect(badge.text).not.toContain("真实阶段事件");
    expect(badge.title).toContain("后端事实");
    expect(badge.title).toContain("前端");
  });

  it("旧 run 说清楚是后端 run 状态，不再声称前端模拟", () => {
    const badge = deriveStageBadge("run-status", false);
    expect(badge.text).toBe("阶段推进：后端 run 状态 + 前端映射");
    expect(badge.text).not.toContain("模拟");
    expect(badge.title).toContain("不随时间推进");
    // 格子是前端按 run.status 映射出来的，这句话要说在明面上。
    expect(badge.title).toContain("前端");
  });

  it("stages 端点不可用时不能藏起来", () => {
    const badge = deriveStageBadge("run-status", true);
    expect(badge.text).toContain("stages 端点不可用");
  });

  it("每一种角标都要说明格子与后端推进点是一一对应", () => {
    for (const source of ["stages", "run-status"] as const) {
      const { title } = deriveStageBadge(source);
      expect(title).toContain("一一对应");
      // 以前角标还要解释「证据」格是推断值、「解析」格合并了两个阶段——
      // 现在每格对应后端的一个推进点，没有要解释的了。
      expect(title).not.toContain("推断得出");
      expect(title).not.toContain("合并了");
    }
  });

  it("每一种角标都要说明后端阶段是后端给的", () => {
    for (const source of ["stages", "run-status"] as const) {
      const { title } = deriveStageBadge(source);
      expect(title).toContain("后端");
      expect(title).toContain("前端");
    }
  });
});

describe("isTerminalStatus —— 终态只有一份口径", () => {
  it("completed / failed / cancelled 都是终态", () => {
    expect(isTerminalStatus("completed")).toBe(true);
    expect(isTerminalStatus("failed")).toBe(true);
    expect(isTerminalStatus("cancelled")).toBe(true);
  });

  it("pending / running 不是终态", () => {
    expect(isTerminalStatus("pending")).toBe(false);
    expect(isTerminalStatus("running")).toBe(false);
  });

  it("没读到状态就不算终态（宁可多问一次后端）", () => {
    expect(isTerminalStatus(null)).toBe(false);
    expect(isTerminalStatus(undefined)).toBe(false);
    expect(isTerminalStatus("")).toBe(false);
    // 后端将来新增的状态：在读到它之前，前端不替它做决定。
    expect(isTerminalStatus("queued")).toBe(false);
  });
});

/** 假的定时器：记下清掉过哪些句柄，并能手动触发每一次「到点」。 */
function fakeScheduler() {
  const cleared: number[] = [];
  let nextHandle = 1;
  let onTick: (() => void) | null = null;
  return {
    cleared,
    scheduler: {
      setInterval: (fn: () => void) => {
        onTick = fn;
        return nextHandle++;
      },
      clearInterval: (handle: number) => {
        cleared.push(handle);
      },
    },
    fire: () => {
      onTick?.();
    },
  };
}

/** 让挂起的 await 链跑完（要好几拍微任务）。 */
function flush(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

describe("pollUntilTerminal —— 进了终态就停", () => {
  it("还没进终态时定时器继续转", async () => {
    const fake = fakeScheduler();
    let calls = 0;
    const poller = pollUntilTerminal({
      poll: async () => {
        calls += 1;
      },
      isTerminal: () => false,
      intervalMs: 2000,
      scheduler: fake.scheduler,
    });

    await flush();
    expect(calls).toBe(1); // 立刻拉一次
    fake.fire();
    await flush();
    expect(calls).toBe(2);
    expect(fake.cleared).toEqual([]); // 还不是终态：不停

    poller.stop();
    expect(fake.cleared).toHaveLength(1);
  });

  it("run 进终态后定时器被清掉，不再发请求", async () => {
    const fake = fakeScheduler();
    let calls = 0;
    let status = "running";
    const poller = pollUntilTerminal({
      poll: async () => {
        calls += 1;
      },
      isTerminal: () => isTerminalStatus(status),
      intervalMs: 2000,
      scheduler: fake.scheduler,
    });

    await flush();
    expect(calls).toBe(1);
    expect(fake.cleared).toEqual([]);

    // 这一轮跑完了：后端把 run.status 写成终态。
    status = "completed";
    fake.fire();
    await flush();
    expect(calls).toBe(2);
    expect(fake.cleared).toEqual([1]); // 定时器被清掉了

    fake.fire(); // 定时器已经清掉：不会再有请求
    await flush();
    expect(calls).toBe(2);

    poller.stop();
  });

  it("cancelled 也算终态（被取消的分析不会再变）", async () => {
    const fake = fakeScheduler();
    let calls = 0;
    const poller = pollUntilTerminal({
      poll: async () => {
        calls += 1;
      },
      isTerminal: () => isTerminalStatus("cancelled"),
      intervalMs: 2000,
      scheduler: fake.scheduler,
    });

    await flush();
    expect(calls).toBe(1);
    expect(fake.cleared).toEqual([1]); // 第一次读完就是终态：立刻停

    fake.fire();
    await flush();
    expect(calls).toBe(1);
    poller.stop();
  });
});

describe("模块的形状", () => {
  it("页面上的五格就是这个顺序", () => {
    expect(STAGES.map((s) => s.id)).toEqual([...SLOTS]);
  });

  it("模块里没有时间模拟函数（拿不到事实时不推进）", () => {
    // Phase 5 收尾删除了前端时间模拟；这条断言在旧实现上会红。
    expect("deriveStageStates" in stagesModule).toBe(false);
  });
});

/**
 * 后端状态区的映射 —— Phase 5 收尾在打包 exe 上实测到的缺陷的拦截网。
 *
 * 实测现象：打包 exe 里分析进行中，右侧「后端状态」区把三个后端全说成
 * 「✕ 失败 未安装或未配置，未参与本次分析」，而那台机器上三个后端都装着
 * （侧车自己的 /api/backends 说得清清楚楚）。原因是那一轮 run 的
 * tool_versions 还没写进库，键不存在，前端把「键不存在」与「值是 null」
 * 当成了同一件事。
 *
 * 这里钉住的是**三态**：键不存在 = 没参与；键在、值为 null = 参与了但
 * 版本还没探测出来；键在、值是版本号 = 参与了，版本已知。
 */
describe("deriveBackends", () => {
  it("says a backend that is not in the run's record did not take part", () => {
    const backends = deriveBackends({
      runs: [{ tool_versions: { androguard: "4.1.4" } }],
    });
    const jadx = backends.find((b) => b.name === "JADX");
    expect(jadx?.state).toBe("error");
    expect(jadx?.detail).toContain("未安装或未配置");
  });

  it("does not call a backend uninstalled while its version is still being probed", () => {
    // The run has started: the backends are named, the versions are not
    // known yet. Saying "not installed" here would be a lie.
    const backends = deriveBackends({
      runs: [{ tool_versions: { jadx: null, apktool: null, androguard: null } }],
    });
    expect(backends.every((b) => b.state === "running")).toBe(true);
    const first = backends[0];
    expect(first).toBeDefined();
    expect(first?.detail).toContain("版本探测中");
    expect(first?.detail).not.toContain("未安装");
  });

  it("states the version once it is known", () => {
    const backends = deriveBackends({
      runs: [
        {
          tool_versions: {
            jadx: "1.5.2",
            apktool: "2.11.1",
            androguard: "4.1.4",
          },
        },
      ],
    });
    expect(backends.every((b) => b.state === "done")).toBe(true);
    expect(backends[0]?.detail).toBe("v1.5.2 · 参与本次分析");
  });

  it("waits for the run when there is none yet", () => {
    const backends = deriveBackends({ runs: [] });
    expect(backends.every((b) => b.state === "queued")).toBe(true);
    expect(backends[0]?.detail).toContain("等待分析轮次数据");
  });
});
