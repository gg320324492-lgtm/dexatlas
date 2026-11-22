# Phase 4 M11 基线 — 状态收口与 Workbench UI 现状

**日期：** 2026-11-23 · **阶段：** Phase 4（[执行单](../roadmap/phase4-plan.md)，最终决策 A + D + G）· **里程碑：** M11 — Phase 3 状态收口和 UI 基线
**基线树：** `main` `8333d25`（含 [M8 措辞统一](https://github.com/gg320324492-lgtm/dexatlas/commit/fa37483) 与 [Workbench 基线截图](https://github.com/gg320324492-lgtm/dexatlas/commit/8eb4ca9) 两个前置提交）

**回答的问题：** Phase 4 开工时，项目对外状态文案是否只有一种解释、Workbench 现在到底有什么、每页哪些状态可见、哪些缺口留给后续里程碑。

---

## 0. 阶段判断（M11-1 的结论）

Phase 3 已完成并经独立验收：M5 基线、M6 服务回归集（B1 于 2026-11-22 由
DeepSeek-V4.1-Flash 三轮 56/60 = 93.3% 关闭；GLM 88.3%、MiniMax 81.7% 分开陈述）、
M7 客户交付包、M8 安装与契约、M9 GitHub 展示、M10 独立验收通过（2026-11-20，
40 项 39 通过，重评 97.5% / 96.3%）。

M8 的对外措辞在本轮统一为**「交付完成（macOS 未验证）」**：干净安装 / Docker /
故障恢复演练完成，M8-2（`--workspace`）、M8-3（install.md extras）、M8-4
（退出码 6 `EXIT_NO_INDEX`）三项评审发现全部修复合入，公共契约表发布并有活体
检查；macOS 实测按计划「未测则标未验证」，保留为**已知限制**，不属于未完成的
验收项。README（callout、状态表、路线图说明三处）、中文 README 对应三处、
[status.md](../status.md) §4.0、[ROADMAP.md](../roadmap/ROADMAP.md) §3.4 现在对
M8 只有这一种解释。

## 1. Workbench 现状（M11-4 实测记录）

**运行方式（本机实测）：** 前端 `src/dexatlas/workbench/web/`（React 19 + Vite 8 +
TypeScript），`npm install` + `npm run build` 成功（tsc 无错误；产物约 262 kB JS）；
仓库根 `uv run dexatlas-workbench` 启动，FastAPI 直接服务 `web/dist/`，监听
`http://127.0.0.1:8618`。分析后端为本机 JADX 1.5.2 + Apktool 2.11.1 +
androguard 4.1.4。

**真实数据：** `uv run dexatlas analyze examples/demo-app/demo.apk` → 项目
`apk_80a8fe0e81204c9f`（5 classes / 8 methods / 23 call sites / 21 call edges /
12 evidence，completeness=complete）。工作区同时存有历史项目 multidex.apk、
obfuscated.apk。

**页面与入口（6 个路由，hash 路由）：**

| # | 路由 | 页面 | 入口 |
|---|---|---|---|
| 1 | `#/` | 项目列表 + APK 上传 | 页头 "DexAtlas Workbench" |
| 2 | `#/projects/{id}` | 项目详情（completeness、计数卡、报告导出、runs 列表） | 列表行链接 |
| 3 | `#/projects/{id}/search` | 符号检索 + 源码阅读 + 证据记录 | 详情页/列表行 |
| 4 | `#/projects/{id}/calls` | 调用关系图（pick a method → callers/callees） | 搜索结果 "call graph" |
| 5 | `#/projects/{id}/agent` | Agent 问答工作台 | 列表行 "ask the agent" |
| 6 | `#/benchmarks` | M3 基线对比（scripted + real model） | 页头 "Benchmarks" |

后端 API（`/openapi.json` 实测）：health、projects、project 详情、callers、
callees、symbols、source/class、source/method、evidence、evidence/{id}、
locators/resolve、agent/config、agent/question、benchmarks/m3、report 导出。
与 [workbench 架构文档](../architecture/workbench.md) 的 8 个计划 screen 对照：
全部有着落（screen 3+4 合并进检索页，screen 7 并入证据记录）。

**真实可运行流程（M11 验收路径）：** 上传 → 分析（同步，demo 约 3.5 s）→
项目详情看 completeness 与计数 → 检索类/方法/字符串 → 打开证据记录 →
调用关系图 → 导出 Markdown/JSON 报告。demo 数据下全链路可走通。

## 2. UI 基线截图（M11-5）

`docs/assets/phase4-baseline/`：**24 张**（6 页 × 4 宽度 375/768/1024/1440），
Playwright（本机 Edge headless，fullPage）生成，脚本存 `.scratch/shot-workbench.mjs`。
文件名 `01-project-list-*.png` … `06-benchmarks-*.png`。

代表性观察：

- 375 px：页头标题与 workspace 文字换行；项目表格仍以 8 列完整渲染（列内容挤
  但可读，未横向滚动）；calls/agent 页表单按钮换行为两行。
- 1024/1440 px：布局居中单列（约 900 px 内容宽），表格完整展开。
- 搜索页 375 px 下长方法签名溢出换行显示，未截断。
- 全部页面深色主题一致，无布局断裂或重叠。

## 3. 页面状态矩阵（现状盘点）

图例：✅ 有设计且实测可见 · ⚠️ 部分/有条件 · ❌ 缺失 · ❓ 未实测

| 页面 | loading | empty | success | partial | error | unavailable |
|---|---|---|---|---|---|---|
| 项目列表/上传 | ❌ | ❌（0 项目无文案） | ✅ 列表渲染 | ⚠️ 上传进行中反馈未实测 | ❌ | ❌ |
| 项目详情 | ❌ | ❌ | ✅ completeness/计数卡/runs | ✅ partial 与 missing_backends 在 runs 列表明示 | ❌ | ❌ |
| 检索与证据 | ❌ | ⚠️ 源码区初始态有设计 | ✅ | ❌ | ❌ | ❌ |
| 调用关系 | ❌ | ✅ 初始选择态 | ✅ | ❌ 单向缺失降级未实测 | ❌ | ❌ |
| Agent 工作台 | ❓ 提问进行中未实测 | ✅ 空输入 + 示例 | ❌ 本机未配模型 | ❌ | ✅ 无模型端点的醒目面板（全站最佳范式） | ✅ 拒答而非替身模型 |
| 基准对比 | ❌ 无 spinner | ❌ | ✅ 两组对比 + 免责面板 | ❌ | ❌ | ❌ |

**缺口汇总（供 M12/M13 排期）：**

1. **loading 态全站缺失**——无 spinner/骨架屏，数据未到时白屏或跳变。最普遍缺口。
2. **error 态基本缺失**——API 失败无统一展示；仅 agent 页对「模型未配置」有完整
   设计，可作为其余页面的范式。
3. **empty 态覆盖不均**——项目列表 0 项目、搜索无结果、benchmark 无数据无专门文案。
4. **partial 态数据层完整**（completeness/missing_backends/truncated），但 UI 强提示
   （顶部横幅等）未逐一验证。
5. **上传分析进行中**的进度反馈未实测（POST /api/analyze 为同步接口）。

## 4. 本轮收口动作

- M8 措辞统一（详见 §0）；全 docs 相对链接复查 0 死链；已移除的 M10/发布清单
  类文件名仅存于历史审计记录，无活链接指向。
- 本报告与 [执行单](../roadmap/phase4-plan.md) 的 M11 退出条件对照：文档检查通过
  （引用 0 finding、无守数 PASS、版本声明 PASS），对外页面对完成度只有一种解释 ✓。
- UI 基线截图与状态矩阵已建立；loading/error/empty 三类缺口的修复归 M13
  （核心 Workbench 实现），不在 M11 范围内。

## 5. 限制与未覆盖

- Agent 成功流（配置模型后的问答与工具调用展示）本机未配
  `DEXATLAS_AGENT_BASE_URL`/`MODEL`，未截图。
- partial/error 态的专项截图（构造 missing backend、错误项目 id 等）未做，
  在状态矩阵中标注为未实测。
- 截图为本机（Windows，Edge headless）单次运行结果；不同后端配置下
  completeness 显示会不同。
