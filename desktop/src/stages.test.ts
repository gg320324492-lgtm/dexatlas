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
import {
  deriveStageBadge,
  deriveStageStates,
  deriveStagesFromRun,
  STAGES,
} from "./stages";
import type { RunStageEvent } from "./api/types";

/** 页面上的五个格子，顺序即页面上的顺序。 */
const SLOTS = ["collect", "parse", "index", "evidence", "report"] as const;

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
  it("完成态五格全完成，「证据」格也在其中", () => {
    const { states } = deriveStagesFromRun(run("completed"), COMPLETED_EVENTS);
    expect(states).toEqual({
      collect: "done",
      parse: "done",
      index: "done",
      evidence: "done",
      report: "done",
    });
  });

  it("运行中「证据」格进行中（复测报告 t=5044ms 的采样）", () => {
    const { states } = deriveStagesFromRun(run("running"), AT_JADX_EVENTS);
    expect(states).toEqual({
      collect: "done",
      parse: "running",
      index: "done",
      evidence: "running",
      report: "pending",
    });
  });

  it("证据还没产出时，「证据」格保持待处理", () => {
    const atApktool = deriveStagesFromRun(run("running"), AT_APKTOOL_EVENTS);
    expect(atApktool.states.evidence).toBe("pending");
    expect(atApktool.states.parse).toBe("running");

    const atIndex = deriveStagesFromRun(run("running"), AT_INDEX_EVENTS);
    expect(atIndex.states.evidence).toBe("pending");
    expect(atIndex.states.index).toBe("running");
  });

  it("失败的 run 不会把某个格子留在「进行中」", () => {
    const atApktool = deriveStagesFromRun(run("failed"), FAILED_AT_APKTOOL_EVENTS);
    expect(atApktool.states.collect).toBe("done");
    expect(atApktool.states.parse).toBe("error");
    expect(atApktool.states.evidence).toBe("pending");
    expect(atApktool.states.report).toBe("pending");

    // 证据格前一个阶段：旧推断把它读成「进行中」，留在一个已经结束的 run 上。
    const atJadx = deriveStagesFromRun(run("failed"), FAILED_AT_JADX_EVENTS);
    expect(atJadx.states.collect).toBe("done");
    expect(atJadx.states.parse).toBe("error");
    expect(atJadx.states.index).toBe("done");
    expect(atJadx.states.evidence).toBe("pending");
    expect(atJadx.states.report).toBe("pending");
  });

  it("取消的 run 同样不会把某个格子留在「进行中」", () => {
    const { states } = deriveStagesFromRun(run("cancelled"), CANCELLED_AT_INDEX_EVENTS);
    expect(states.collect).toBe("done");
    expect(states.parse).toBe("done");
    expect(states.index).toBe("error");
    expect(states.evidence).toBe("pending");
    expect(states.report).toBe("pending");
  });

  it("发布阶段失败时，证据已经产出（pipeline 先建证据再发布）", () => {
    const { states } = deriveStagesFromRun(run("failed"), FAILED_AT_PUBLISH_EVENTS);
    expect(states.evidence).toBe("done");
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
    expect(states.parse).toBe("skipped");
    expect(partialLabels.parse).toBe("部分");
    expect(states.report).toBe("done");
  });
});

describe("deriveStagesFromRun —— 没有阶段事件（旧 run 走状态兜底）", () => {
  it("完成的 run 五格全完成", () => {
    const { states } = deriveStagesFromRun(run("completed"), []);
    expect(states).toEqual({
      collect: "done",
      parse: "done",
      index: "done",
      evidence: "done",
      report: "done",
    });
  });

  it("运行中的 run 走粗粒度映射", () => {
    const { states } = deriveStagesFromRun(run("running"), []);
    expect(states.collect).toBe("done");
    expect(states.parse).toBe("running");
    expect(states.index).toBe("pending");
  });

  it("失败的 run 把解析格标失败", () => {
    const { states } = deriveStagesFromRun(run("failed"), []);
    expect(states.collect).toBe("done");
    expect(states.parse).toBe("error");
  });

  it("还没开始的 run 不许声称某个阶段失败了", () => {
    const { states } = deriveStagesFromRun(run("pending"), []);
    expect(states).toEqual({
      collect: "pending",
      parse: "pending",
      index: "pending",
      evidence: "pending",
      report: "pending",
    });
  });
});

describe("deriveStagesFromRun —— 没有 run", () => {
  it("五格全是待处理", () => {
    const { states } = deriveStagesFromRun(null, null);
    expect(states).toEqual({
      collect: "pending",
      parse: "pending",
      index: "pending",
      evidence: "pending",
      report: "pending",
    });
  });
});

describe("deriveStageStates —— 前端时间模拟（最后的兜底）", () => {
  it("完成的 run 五格全完成", () => {
    expect(deriveStageStates(5, "completed")).toEqual({
      collect: "done",
      parse: "done",
      index: "done",
      evidence: "done",
      report: "done",
    });
  });

  it("运行中按已完成的格数推进", () => {
    expect(deriveStageStates(2, "running")).toEqual({
      collect: "done",
      parse: "done",
      index: "running",
      evidence: "pending",
      report: "pending",
    });
  });
});

describe("deriveStageBadge —— 角标如实说明数据来源", () => {
  it("有 stages 时说数据来自后端真实阶段事件", () => {
    const badge = deriveStageBadge("stages");
    expect(badge.text).toBe("阶段推进：后端真实阶段事件");
  });

  it("旧 run 说清楚是 run 状态 + 前端粒度模拟", () => {
    const badge = deriveStageBadge("run-status", false);
    expect(badge.text).toBe("阶段推进：后端 run 状态 + 前端粒度模拟");
  });

  it("stages 端点不可用时不能藏起来", () => {
    const badge = deriveStageBadge("run-status", true);
    expect(badge.text).toContain("stages 端点不可用");
  });

  it("什么都没有时说清楚是前端模拟", () => {
    const badge = deriveStageBadge("simulation");
    expect(badge.text).toBe("阶段推进为前端模拟");
  });

  it("每一种角标都要说明「证据」格是推断值、解析格合并了两个阶段", () => {
    for (const source of ["stages", "run-status", "simulation"] as const) {
      const { title } = deriveStageBadge(source);
      expect(title).toContain("证据");
      expect(title).toContain("推断");
      expect(title).toContain("parse-apktool");
    }
  });
});

describe("模块的形状", () => {
  it("页面上的五格就是这个顺序", () => {
    expect(STAGES.map((s) => s.id)).toEqual([...SLOTS]);
  });
});
