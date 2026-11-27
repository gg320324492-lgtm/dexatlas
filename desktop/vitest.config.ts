import { defineConfig } from "vitest/config";

/**
 * 桌面端的单元测试配置。
 *
 * 桌面前端以前没有测试框架：桌面上的每一条回归都由 Python 在 `tests/` 下
 * 对源码做断言式检查维持（见 docs/reports/phase1-execution-report.md 的
 * 测试文件表）。现在这里是真单测——跑的是 `desktop/src` 里那个模块本身，
 * 不是源码里有没有某个字符串。
 *
 * 【环境为什么是 node】
 * 被测的几处（阶段映射、locator 分类、侧车端口解析、API 客户端）都是无 DOM
 * 依赖的纯逻辑，所以默认不开 happy-dom / jsdom：少装两个包，也少两个会坏的
 * 东西。真的需要渲染组件时，在**那个测试文件的头部**单独开
 * `// @vitest-environment jsdom`（见 `src/pages/HomePage.test.tsx`）。
 */
export default defineConfig({
  test: {
    environment: "node",
    // `.tsx` 是组件渲染测试（HomePage 那条），其余是纯逻辑测试。
    include: ["src/**/*.test.ts", "src/**/*.test.tsx", "src/**/*.test.js"],
    // 桌面的失败信息里有中文，报告按 UTF-8 打印，免得看到乱码。
    reporters: ["default"],
  },
});
