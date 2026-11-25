/**
 * locator 落点分类的单元测试 —— 证据抽屉「打开来源」按钮能不能用的依据。
 *
 * 这部分原先是 `tests/test_desktop_locator_open_source.py` 里的源码断言
 * （「源码里有 `openable: false` 就算过」）。这里改成真的调用分类函数，
 * 断言它**返回什么**——同一批用例，多一份能真正拦住回归的东西。
 *
 * 文件末尾另有三条**结构守卫**：抽屉（ProjectDetail.tsx）必须把分类结果接到
 * 按钮上。它们读的是源码文本，不是行为——真要验行为得渲染组件，那要 DOM 与
 * 一套组件测试脚手架；这里保留文本守卫，但把它和别的守卫分开写，别混在
 * 行为用例里冒充单测。
 */

import { describe, expect, it } from "vitest";
import {
  APK_READER,
  classifyLocator,
  DEX_BACKEND,
  ERROR_PREFIX,
  openSourceState,
  OUTPUT_BACKENDS,
} from "./locators";
import projectDetailSource from "./pages/ProjectDetail.tsx?raw";

/** 「没有单文件落点」——不能打开时必须说清的那句话。 */
const NO_SINGLE_FILE = "没有单文件落点";

describe("classifyLocator —— 没有单文件落点的三类", () => {
  it("包级来源（APK 包自身的事实）", () => {
    const info = classifyLocator(`${APK_READER}:zip-entries`);
    expect(info.target).toBe("package");
    expect(info.openable).toBe(false);
    expect(info.note).toBeDefined();
    expect(info.note?.startsWith("包级来源")).toBe(true);
    expect(info.note).toContain(NO_SINGLE_FILE);
  });

  it("DEX 内位置（APK 字节码里的符号）", () => {
    const info = classifyLocator(`${DEX_BACKEND}:classes/android/app/MainActivity`);
    expect(info.target).toBe("dex");
    expect(info.openable).toBe(false);
    expect(info.note).toContain(NO_SINGLE_FILE);
  });

  it("后端未完成（locator 指的就是「没跑完」这个事实）", () => {
    const info = classifyLocator(`jadx:${ERROR_PREFIX}timeout`);
    expect(info.target).toBe("error");
    expect(info.openable).toBe(false);
    expect(info.note).toContain("没有可打开的文件");
  });
});

describe("classifyLocator —— 有单文件落点的两类", () => {
  it("输出树里的文件（JADX / Apktool）", () => {
    for (const tool of OUTPUT_BACKENDS) {
      const info = classifyLocator(`${tool}:sources/MainActivity.java`);
      expect(info.target).toBe("file");
      expect(info.openable).toBe(true);
      expect(info.note).toBeUndefined();
    }
  });

  it("输出树里的文件，带 #成员 后缀也一样", () => {
    const info = classifyLocator("jadx:sources/MainActivity.java#onCreate");
    expect(info.target).toBe("file");
    expect(info.openable).toBe(true);
  });
});

describe("classifyLocator —— 认不出来的", () => {
  it("空 locator", () => {
    const info = classifyLocator("");
    expect(info.target).toBe("unknown");
    expect(info.openable).toBe(false);
    expect(info.note).toBeDefined();
  });

  it("不是「工具:位置」的形状", () => {
    const info = classifyLocator("just-some-text");
    expect(info.target).toBe("unknown");
    expect(info.openable).toBe(false);
  });

  it("后端不认的工具前缀", () => {
    const info = classifyLocator("mystery-tool:something");
    expect(info.target).toBe("unknown");
    expect(info.openable).toBe(false);
  });
});

describe("openSourceState —— 按钮的可用性", () => {
  it("没有落点的 locator：直接不可用，后端说什么都改不了", () => {
    const state = openSourceState(`${APK_READER}:zip-entries`);
    expect(state.openable).toBe(false);
    expect(state.note).toContain(NO_SINGLE_FILE);
  });

  it("有落点但还没问过后端：可用", () => {
    const state = openSourceState("jadx:sources/MainActivity.java");
    expect(state.openable).toBe(true);
    expect(state.note).toBeUndefined();
  });

  it("后端说这个来源不在这次分析里：不可用", () => {
    const state = openSourceState("jadx:sources/MainActivity.java", {
      resolved: false,
      reason: "不在这次分析的输出里",
      kind: null,
    });
    expect(state.openable).toBe(false);
    expect(state.note).toContain("不在这次分析里");
  });

  it("后端解析成功但没有单文件落点：不可用", () => {
    const state = openSourceState("jadx:sources/MainActivity.java", {
      resolved: true,
      reason: "命中的是目录不是文件",
      kind: null,
    });
    expect(state.openable).toBe(false);
    expect(state.note).toContain("没有单文件落点");
  });

  it("后端解析成功且有落点：可用", () => {
    const state = openSourceState("jadx:sources/MainActivity.java", {
      resolved: true,
      reason: "ok",
      kind: "file",
    });
    expect(state.openable).toBe(true);
    expect(state.note).toBeUndefined();
  });
});

describe("结构守卫 —— 抽屉把状态接到了按钮上", () => {
  it("抽屉从 locator 推出按钮状态", () => {
    expect(projectDetailSource).toContain("openSourceState(");
  });

  it("没有落点时按钮是禁用的", () => {
    expect(projectDetailSource).toMatch(/disabled=\{[^}]*openSource[^}]*\}/);
  });

  it("禁用时的说明是看得见的文本，不只是 tooltip", () => {
    expect(projectDetailSource).toMatch(/\{openSource\.note\s*&&/);
    const hint = projectDetailSource.slice(
      projectDetailSource.indexOf('className="da-ev-drawer__hint"'),
    );
    expect(hint.slice(0, 400)).toContain("openSource.note");
    expect(hint.slice(0, 400)).toContain('id="da-ev-open-source-hint"');
  });

  it("文件级 locator 的点击行为不变", () => {
    // 找的是 JSX 文本节点，不是注释里提到「打开来源」的那句话。
    const at = projectDetailSource.search(/>\s*打开来源\s*</);
    expect(at).toBeGreaterThan(-1);
    const button = projectDetailSource.slice(Math.max(0, at - 1200), at);
    expect(button).toContain("onClick");
    expect(button).toContain("displayLocator(selected.provenance)");
  });
});
