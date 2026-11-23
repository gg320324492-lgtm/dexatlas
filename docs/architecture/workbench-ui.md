# Workbench UI — 信息架构、数据边界、状态模型与组件职责

**阶段：** Phase 4 M12（[执行单](../roadmap/phase4-plan.md)）· **基线：** `main` `29ea484`
**配套：** 现状盘点见 [phase4-baseline.md](../reports/phase4-baseline.md)；架构与取舍见
[workbench.md](workbench.md)。本文回答 M12 退出条件要的四件事：页面信息架构、数据
边界、状态模型、组件职责——以及键盘行为与公共契约的约束。

> **本文的地位。** `workbench.md` 说的是「Workbench 是什么、为什么这样设计」；
> 本文是 M12 之后的**实现规范**：页面上有什么、每块归谁、每种状态长什么样、
> 什么不能做。M13 起的新增样式必须能对应到本文的一个 token、组件与状态约定。

## 1. 技术基座与边界

- **栈：** React 19 + Vite 8 + TypeScript（`src/dexatlas/workbench/web/`），
  纯 CSS（`src/styles.css`），无 UI 框架、无 Tailwind、无组件运行时。行为复杂且
  收益明确时才按需引入单个 Radix primitive；不整体迁移 shadcn。
- **数据边界（继承 [workbench.md](workbench.md) 的决定）：** 前端只读
  `/api/*`（`src/api.ts` 是唯一的取数层，类型对齐 MCP 工具的返回形状）。
  前端状态不能创造新的分析结论、指标或证据；页面上每个数字都必须能溯回到
  workspace。上传是唯一写路径，走与分析管线相同的函数。
- **路由：** hash 路由（`#/`、`#/projects/{id}`、`#/projects/{id}/search`、
  `#/projects/{id}/calls`、`#/projects/{id}/agent`、`#/benchmarks`），无路由库。
- **图标：** SVG、Lucide 风格，不用 emoji 当产品图标。

## 2. 页面信息架构

六个路由，按「项目 → 深看 → 问 agent → 横向对比」组织：

| # | 路由 | 页面职责 | 主要数据源（api.ts） |
|---|---|---|---|
| 1 | `#/` | 项目列表 + APK 上传（唯一写路径） | `listProjects`、`uploadApk`、`getHealth` |
| 2 | `#/projects/{id}` | 项目详情：completeness、计数卡、runs 列表、报告导出链接 | `getProjectStatus` |
| 3 | `#/projects/{id}/search` | 符号检索 → 类/方法源码阅读 → 证据记录与溯源 | `searchSymbols`、`getClassSource`、`getMethodSource`、`listEvidence`、`getEvidence`、`resolveLocator` |
| 4 | `#/projects/{id}/calls` | 方法调用关系：选方法 → callers/callees 图与调用点 | `findCallers`、`findCallees` |
| 5 | `#/projects/{id}/agent` | Agent 问答工作台（配置检查 → 提问 → 任务轮询 → 报告/工具时间线/证据表） | `getAgentConfig`、`askAgent`、`getAgentTask`、`getAgentReport` |
| 6 | `#/benchmarks` | M3 基线对比（scripted 与 real model 两组 + 失败归因 + 免责面板） | benchmarks 数据源 |

页头（Topbar）固定四要素：产品名（回列表）、workspace 路径标注、Benchmarks
链接、后端状态警示位（`BackendsWarning`，缺失后端时全局提示）。

## 3. 状态模型

六态覆盖是 M13 的验收口径（[phase4-baseline.md](../reports/phase4-baseline.md)
§3 是 M11 时的实测缺口清单）。每个页面的数据获取都必须落到下表之一，
不允许「白屏或跳变」：

| 状态 | 语义 | UI 约定 |
|---|---|---|
| `loading` | 请求在途，无数据可示 | 骨架屏或 spinner（`.loading`），不闪白屏；不做假进度条 |
| `empty` | 请求成功但集合为空 | 一句说明 + 下一步动作（如「先 analyze 一个 APK」） |
| `success` | 完整数据 | 正常渲染 |
| `partial` | 数据有但完整性打折（completeness=partial、missing_backends、truncated） | 顶部横幅 + 详情处标注；沿用数据层已有字段，不新造指标 |
| `error` | 请求失败（`ApiError`、4xx/5xx、网络） | 错误面板：可读原因 + 重试入口；沿用 agent 页「无模型端点」面板的范式 |
| `unavailable` | 该功能在本环境不可用（如 agent 无模型端点） | 醒目但克制的说明面板：缺什么、怎么配、明确拒答语义 |

**轮询与终态。** agent 任务是异步的（accept → poll task → report），已有
`AGENT_TERMINAL_STATUSES` 终态集合；轮询 UI 必须区分「进行中 / 终态」，
终态后停止轮询。

**M12 状态实测（[17 张真实截图](../assets/phase4-states/)，Playwright 驱动
真实实例，笔记 `.scratch/m12-state-notes.md`）。** 对 M11 基线认知的修正与补全：

- **loading**：现有实现是**文字型占位**（"reading the project…" /
  "searching…" / "reading the calls…"，`App.tsx` 四处 `<p className="loading">`），
  无 spinner/骨架屏；本机 fetch 毫秒级完成，正常导航几乎不可感知（用 route
  拦截冻结后可截到）。M11 写的「全站无 loading 态」按「无视觉 loading 组件」
  成立，按「无任何提示」不成立——M13 的工作是把它升级为骨架屏/spinner。
- **error**：详情页整页红字 + 返回链接 ✅；搜索页两面板各自红字 ✅；**两个
  静默缺口**——calls 页不带 method 参数时不发请求、对不存在项目无任何提示；
  agent 页对未知项目不报错、被「无模型」面板遮蔽。M13 需统一为「先验项目
  存在性或显式错误」。
- **empty**：项目列表 0 项目是**黄金范式**（上传面板 + 引导文案）；搜索的
  empty 分支存在但被池枚举回退遮蔽、实际不可达（M12 讨论项）；调用关系
  method 无命中显示 0 计数 + 解释文案（契约如此）。
- **partial/truncated**：missing backends 与强制截断（预算 method=2 等）下，
  completeness 面板逐项黄/红提示、统计卡如实变小、runs 列表标注 partial——
  数据链路完整，实测确认。
- **agent 提问进行中**：无任何可见反馈，M13 需补。

## 4. 组件职责与最小 API

M13 按「先基座后页面」实现；每个组件只做一件事，数据一律由页面层传入
（组件内不直接 fetch）：

| 组件 | 职责 | 最小 API（props） |
|---|---|---|
| `AppShell` | 布局骨架：Topbar + 内容容器 + 焦点管理 | `children` |
| `Topbar` | 产品名回链、workspace 标注、导航链接、后端警示位 | `workspacePath`, `backendsWarning` |
| `Breadcrumbs` | 层级路径（列表 → 项目 → 子页） | `items: {label, to?}[]` |
| `PageHeader` | 页标题 + 副题 + 右侧动作区 | `title`, `subtitle?`, `actions?` |
| `Panel` | 内容分区容器（边框 + 面板底色） | `title?`, `children` |
| `StatCard` | 计数卡（数值 + 标签），数字用等宽字体 | `value`, `label` |
| `StatusBadge` | 状态徽章（completed/running/failed/pending/partial…） | `kind`, `label` |
| `Button` | 主/次按钮，禁用态明确 | `variant`, `disabled`, `onClick` |
| `Tabs` | 页内切换 | `tabs`, `active`, `onChange` |
| `DataTable` | 表格（项目、runs、符号、benchmark），列可配 | `columns`, `rows` |
| `EvidenceRow` | 证据条目行（kind/level/摘要 + 查看入口） | `evidence`, `onOpen` |
| `SourcePreview` | 源码片段（行号对齐、长行换行不截断） | `sourceView` |
| `Timeline` | agent 工具调用时间线（顺序、成败、耗时） | `calls` |
| `Skeleton` | loading 占位 | `rows?` |
| `Dialog` / `Drawer` | 模态/侧栏（Escape 关闭、焦点返回触发控件） | `open`, `onClose`, `title` |

现有 49 个类名在 M13 中逐一对号入座；不引入新的命名体系。

## 5. 视觉 token（8px 基线）

颜色已全部走 `:root` 变量（9 个语义色 + 面板/边框/文本三级）；M12-A 把间距、
字号层级、圆角、边框、焦点环补齐为 token。约定：

- **间距：** 8px 基线（0.5rem 步进），页面留白与组件内边距都取自 `--space-*`。
- **字号层级：** 页题 / 节题 / 正文 / 辅助说明 / 徽章 五级，全部 token 化。
- **圆角与边框：** 面板、按钮、徽章各有固定圆角 token；边框一律 `1px solid var(--line)`。
- **焦点环：** 所有可交互元素统一 `--focus-ring`（键盘可见，鼠标不双份）。
- **颜色语义：** 蓝色=交互/链接；绿/黄/红=成功/警告/失败，不做装饰用；
  文本与状态色满足 WCAG AA，成功失败不只靠颜色（配图标/文字）。
- **报告预览保留纸面感**，但报告阅读区与原始证据区视觉上清楚区分。

## 6. 响应式与可访问性

- **断点：** 375 / 768 / 1024 / 1440（与 M11 基线截图的四档一致）。窄屏允许
  换行与堆叠，不允许信息截断（长包名、长签名、长路径换行显示）。
- **键盘：** 上传、搜索、筛选、证据跳转、导出、返回全部可键盘完成；可见焦点环；
  Dialog/Drawer 支持 Escape 关闭并把焦点还给触发控件。
- **触控目标 ≥ 44px**；支持 `prefers-reduced-motion`（不做无谓动画）。
- **截图必须来自真实运行结果**（Playwright，参考 M11 的
  `.scratch/shot-workbench.mjs`），不用手工拼图。

## 7. 键盘行为与公共契约约束

- UI 改动**不得**触碰 REST、MCP、CLI、报告 schema、证据 locator、退出码——
  这些是 [public-contracts.md](public-contracts.md) 钉死的公共契约。
- 前端唯一写路径是上传；agent 提问走既有 `/api/agent/*`；报告导出走既有
  下载端点。新页面不允许自带新的分析语义。
- 前端对后端字段的**新增读取**必须对应 `api.ts` 里已有的类型；类型不够用
  时先扩 `api.ts` 的类型声明（对齐 MCP 返回形状），再在组件里用。

## 8. M13 的实现顺序（从本规范派生）

1. AppShell、Topbar、Breadcrumbs、PageHeader、Panel、Button、StatusBadge。
2. Projects / Upload（补 empty/loading/error）。
3. Project Overview（partial 横幅）。
4. Search & Evidence。
5. Call Graph / Method。
6. Agent Workspace（成功流补全）。
7. Report Export 与 Benchmarks 视觉统一。
8. 四宽度响应式核验 + 可访问性清单过一遍 + 真实运行截图更新基线。
