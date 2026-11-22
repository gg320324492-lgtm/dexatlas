# Phase 4 — 作品集收尾、软件设计与 Workbench UI

> **最终决策：A + D + G**
>
> **A** 收尾稳妥版，10–15 个工程日。
>
> **D** 保留深色分析工作台，安静、数据优先、蓝色强调。
>
> **G** GitHub 作为主站；如作者自行选择外部发布渠道，复用同一套案例页和演示材料。

## 1. 阶段定位

Phase 3 已经完成核心技术交付。Phase 4 是 DexAtlas 作为 GitHub 个人作品集的最终收尾阶段，目标是让陌生读者能够安装项目、理解价值、运行 Workbench、查看证据链和阅读真实报告。

本阶段完成后，项目默认进入 Portfolio Freeze。没有真实用户、客户需求、外部贡献者或可复核的使用反馈时，不继续增加功能。冻结期间只维护安装阻塞、安全问题、依赖兼容性和文档事实错误。

## 2. 阶段终点

陌生读者应能独立完成以下路径。

> GitHub README → 启动 Workbench → 上传获得授权分析的 APK → 查看项目状态 → 搜索类、方法或字符串 → 打开证据 → 查看调用关系或源码片段 → 导出 Markdown/JSON 报告。

技术评审者应能从文档和代码看懂页面信息架构、状态模型、组件职责和数据边界。潜在客户应能在一分钟内理解项目能解决什么问题、交付什么结果以及证据如何回溯到来源。

## 3. 明确范围

### 3.1 必须完成

- 统一 README、中文 README、ROADMAP、status 和 HANDOVER 中的 Phase 3、M8、M9、M10 和 v1.0.1 状态。
- 记录 M8 的唯一公开措辞，并保留 macOS 尚未验证的限制。
- 建立 Workbench UI token、组件清单、页面信息架构和状态矩阵。
- 完成 Projects / Upload。
- 完成 Project Overview。
- 完成 Search & Evidence。
- 完成 Call Graph / Method。
- 完成 Agent Workspace。
- 统一 Report Export 和 Benchmarks 的视觉层级。
- 为核心页面补齐 loading、empty、success、partial、error 和 unavailable 状态。
- 检查 375、768、1024、1440 四种宽度。
- 完成键盘操作、可见焦点、对比度、触控目标和减少动画检查。
- 完成 GitHub README 截图、60–90 秒真实演示和外部渠道案例页（渠道由作者自行决定）。

### 3.2 明确不纳入

本阶段不新增 Ghidra、Frida、JNI 深度分析、新漏洞规则、认证、多租户、云端 APK 上传、分布式队列或新的数据库层。也不改变 REST、MCP、CLI、报告 schema、证据 locator、公共状态码和退出码。

Workbench 继续使用现有 React、Vite、TypeScript 和 CSS。参考 E 盘 UI 库中的 Primer、Carbon、shadcn、Radix 和 Lucide，但不整体迁移 Tailwind 或完整 shadcn 运行时。只有行为复杂且收益明确时，才按需引入单个 Radix primitive。

## 4. UI 方向

现有“dark, quiet, numbers first”方向继续作为基础。

- 深色背景、低饱和面板和清晰边界。
- 蓝色作为主强调色。
- 绿色、黄色、红色只表达成功、警告和失败。
- 采用 8px 间距基线。
- 表格、证据列表、路径、行号和源码片段优先保证可读性。
- 使用 SVG 图标，统一采用 Lucide 风格，避免 emoji 作为产品图标。
- 不使用玻璃拟态、紫色渐变、假进度条和无法由脚本复现的营销数字。
- 允许报告预览保留纸面感，但报告阅读区域必须和原始证据区域清楚区分。

## 5. 软件设计交付物

- `docs/architecture/workbench-ui.md`，记录页面信息架构、数据边界、状态模型、组件职责、键盘行为和公共契约。
- CSS token 表，记录颜色、字体层级、间距、圆角、边框、焦点环和响应式断点。
- P0 页面状态矩阵，覆盖 loading、empty、success、partial、error、unavailable。
- 共享组件清单，包含 AppShell、Topbar、Breadcrumbs、PageHeader、Panel、StatCard、StatusBadge、Button、Tabs、DataTable、EvidenceRow、SourcePreview、Timeline、Skeleton 和 Dialog / Drawer。
- 四种 viewport 的视觉检查记录。
- 一个真实 APK 的 60–90 秒演示脚本。
- 一个 3–5 分钟的技术讲解脚本。
- GitHub 作品集说明和外部渠道案例说明。

## 6. 里程碑

### M11 — Phase 3 状态收口和 UI 基线

**预计 0.5–2 个工程日。**

1. 对照实际版本、测试和发布材料，统一所有对外状态文案。
2. 将 M8 的公开措辞固定为“交付完成，macOS 尚未验证”，并在记录中保留限制。
3. 清理失效的外部展示链接和已移除素材引用。
4. 记录当前 Workbench 的页面、入口、接口和真实可运行流程。
5. 建立 UI 基线截图和页面状态矩阵。

交付物是 `docs/reports/phase4-baseline.md`。退出条件是文档检查通过，且所有对外页面对当前完成度只有一种解释。

### M12 — 软件设计和视觉规范

**预计 2–4 个工程日。**

1. 固定 P0 和 P1 页面范围。
2. 编写 `docs/architecture/workbench-ui.md`。
3. 将现有 CSS 变量整理为 token。
4. 固定共享组件的最小 API 和状态约定。
5. 为核心状态写出可复现的手工验证路径。

退出条件是新增样式都能对应一个 token、组件和状态约定。

### M13 — 核心 Workbench 实现

**预计 5–8 个工程日。**

按下面顺序实现。

1. AppShell、Topbar、Breadcrumbs、PageHeader、Panel、Button、StatusBadge。
2. Projects / Upload。
3. Project Overview。
4. Search & Evidence。
5. Call Graph / Method。
6. Agent Workspace。
7. Report Export 和 Benchmarks 的视觉统一。

每个页面都必须使用真实数据入口。前端状态不能创造新的分析结论、指标或证据。发现后端阻塞时，只有范围很小、已有回归测试且不改变公共契约的修复，才在本阶段处理。

### M14 — 响应式、可访问性和视觉质量

**预计 2–4 个工程日。**

验收宽度为 375、768、1024、1440。

- 键盘可以完成上传、搜索、筛选、证据跳转、导出和返回。
- 所有交互控件有可见焦点。
- 文本和状态颜色满足 WCAG AA。
- 成功和失败不只依赖颜色表达。
- 触控目标至少 44px。
- Dialog 和 Drawer 可以用 Escape 关闭，并把焦点返回触发控件。
- 长包名、长类名、长路径、空数据和错误文案不会破坏布局。
- 支持 `prefers-reduced-motion`。
- 截图必须来自真实运行结果。

### M15 — 发布冻结和作品集封装

**预计 1–2 个工程日。**

1. 从 README 开始完成一次独立用户 walkthrough。
2. 录制 60–90 秒真实演示和 3–5 分钟技术讲解。
3. 更新 GitHub README 的截图、入口和演示说明。
4. 准备外部渠道案例页、交付边界、技术栈和验收方式。
5. 执行测试、lint、format、mypy、vulture、文档引用、版本声明和 `git diff --check`。
6. 完成源代码评审，并把 Phase 4 标记为完成。
7. 写明没有真实用户信号时不启动下一阶段功能开发。

## 7. 验收矩阵

| 维度 | 通过条件 | 证据 |
| --- | --- | --- |
| 状态真实 | README、路线图、状态页和交接说明对 Phase 3 的完成度只有一种解释 | 文档检查和人工审阅 |
| 核心路径 | 上传、分析、搜索、证据、调用关系和导出可以用真实数据走通 | walkthrough 和演示 |
| 契约稳定 | UI 改动不改变 API、MCP、CLI、报告和退出码 | 合同测试和变更记录 |
| 组件一致 | P0 页面使用统一 token 和共享状态组件 | 组件清单和截图 |
| 响应式 | 四种 viewport 没有阻断布局问题 | 截图或检查表 |
| 可访问性 | 键盘、焦点、对比度、44px 目标和减少动画通过 | 手工验证记录 |
| 证据可读 | 结论可以跳回真实来源 | 真实 APK 演示和报告引用检查 |
| 作品集完整 | GitHub 材料能在一分钟内说清价值、边界和结果 | 文案审阅和链接检查 |
| 独立验收 | 读者无需口头解释即可完成核心路径 | 独立 walkthrough 记录 |

## 8. Portfolio Freeze 规则

Phase 4 完成后，项目默认冻结。只有出现以下真实信号之一，才重新规划新的开发阶段。

- 有真实用户按照公开文档完成安装，并留下可复核反馈。
- 有真实客户提出与证据链能力直接相关的需求。
- 有外部贡献者提交 issue、PR 或复现报告。
- 有实际使用记录表明核心流程存在阻塞问题。

冻结期间允许处理安装和发布阻塞、安全问题、依赖兼容性、文档错误和链接错误。新后端、新分析规则、新页面、新平台和展示性功能必须等到新的范围评审完成后再决定。

## 9. 最终决策记录

本执行单已经根据用户选择确定为 **A + D + G**。

- 开发范围采用收尾稳妥版。
- UI 采用现有深色分析工作台方向。
- 作品集以 GitHub 完整技术展示为主；作者自行选择的外部渠道复用同一套真实演示和案例材料。
- Phase 4 完成后默认冻结，是否进入下一阶段由真实用户信号决定。
