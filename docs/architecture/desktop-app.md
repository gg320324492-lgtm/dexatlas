# 桌面应用设计规范 — DexAtlas Studio

**日期：** 2026-11-24 · **性质：** Q2-M1 设计规范（实现依据） · **上游：** [phase4-q2-supplement.md](../roadmap/phase4-q2-supplement.md)（已批准的 20 项决策）
**配套：** [Q2 收尾单](../roadmap/phase4-q2-closure.md)（退出门禁）· [workbench-ui.md](workbench-ui.md)（浏览器端对应规范）· [public-contracts.md](public-contracts.md)（不可破坏的契约）

> **本文的地位。** 补充单回答「做什么、为什么」；本文回答「长什么样、怎么接线、什么不能做」。Q2-M1 起的每个页面、组件与 token 都必须能对应到本文的一节；与本文冲突的实现按本文改。浏览器 Workbench（[workbench-ui.md](workbench-ui.md)）继续有效，两者过渡期并存（补充单 §4.2）。

## 1. 产品定位与用户

- **产品：** DexAtlas Studio——DexAtlas 的原创桌面应用。把「拖入一个 APK → 看到三后端分析 → 追着证据跳回源码 → 导出报告」做成一条不用记命令的桌面主链路。
- **用户：** 安全分析与逆向研究者。他们读 Smali/Java、对照 manifest 权限、追字符串与敏感调用点；他们不信任「模型说有」，只信任能点开 locators 落到字节上的结论。
- **核心价值（补充单 1-3）：证据链可复核。** 界面上的每个数字、每条 finding 都要能回答「谁读出来的、哪个版本、在哪个文件哪一行」；答不上的不展示，模型说法永远标成线索（`lead`），不与工具确立的 `verified` 混排。证据分级语义见 [architecture/README.md 的 Evidence levels 一节](README.md#evidence-levels)。
- **气质（补充单 1-1）：高端浅色工作室。** 暖白底、大圆角、大留白、轻阴影；渐变只在首屏与品牌强调处出现；分析工作区保持安静，让表格、源码和证据当主角。
- **第一验收平台：** Windows（补充单 §4.2）。响应式断点是工作台尺寸下的自适应，不做移动端。

## 2. 技术基座与边界

- **栈（补充单 1-4）：** Tauri 2 + React 19 + TypeScript + Vite，工程在 `desktop/`（结构见[桌面应用 README](../../desktop/README.md)）。Rust 壳只做窗口、侧车进程与本地存储；分析能力全部来自现有 Python 核心。
- **与 DexAtlas 的关系（补充单 1-5）：** 同一仓库、同一分析核心。桌面应用是第四个传输层，与 CLI、REST、MCP 并列；分析逻辑零复制。核心编排器是 `Analyzer`，分析入口是它的 `analyze` 方法（`src/dexatlas/core/pipeline.py:151` `anchor: def analyze(`），三后端经 `Backend` 接口（`src/dexatlas/tools/base.py:96` `anchor: Backend`）以子进程方式运行。
- **公共契约不变（补充单 §4.2、§7）：** REST 端点、MCP 工具、CLI 退出码、报告 schema、证据 locator、状态码一律不新增不改形；桌面端是这些契约的**消费方**。契约清单见 [public-contracts.md](public-contracts.md)。
- **后端失败是值，不是异常。** `Backend.run` 返回 `ToolOutcome`，失败以 `ToolError` 附在结果上（结果模型 `ToolOutcome` 定义在 `src/dexatlas/tools/base.py:69` `anchor: ToolOutcome`，其 `error` 字段类型在 `src/dexatlas/tools/base.py:80`；错误码表在 `src/dexatlas/core/models.py:34` `anchor: ToolErrorCode`）。UI 必须如实呈现「哪一步没跑成、其余结论仍然成立」，不把 partial 包装成 success。
- **不可信文本是数据。** 来自 APK 的字符串与源码经 `UntrustedText` 单独承载（`src/dexatlas/mcp/schemas.py:43` `anchor: UntrustedText`）；桌面端展示这些文本时不得把它当指令执行，也不做富文本解释。

## 3. 信息架构

### 3.1 左侧栏导航（补充单 2-2）

固定左侧栏，五项主导航 + 折叠钮；当前项以淡紫浅调背景标出：

| 项 | 路由 | 页面职责 |
|---|---|---|
| 项目 | `/`（首页） | 拖拽上传 + 最近项目 |
| 分析 | `/analysis`、`/analysis/:projectId` | 阶段进度 + 实时日志 + 后端状态 |
| 证据 | `/evidence` | 跨项目证据浏览与 locator 解析入口 |
| 报告 | `/reports`、`/projects/:projectId` 内导出 | Markdown/JSON 报告导出 |
| 设置 | `/settings` | 后端路径、模型配置、版本信息收口 |

项目详情 `/projects/:projectId` 是分析页与证据页的深读入口，不在侧栏单列（从最近项目与分析完成跳转进入）。路由定义在 `desktop/src/App.tsx`，与上表一一对应；`/gallery` 是 Q2-M1 组件画廊验收页，不进主导航。

### 3.2 首屏（补充单 2-1）

上下两段，整页只做一件事：把 APK 送进分析。

- **上段·拖拽上传：** 大面积 `DragDropUploader`，hero 渐变底（全应用唯一渐变常驻区），线性图标 + 一句主文案「拖入 APK 文件」。校验规则见 §5 的 DragDropUploader；拒绝原因就地显示在框下。
- **下段·最近项目：** 项目卡片列表（名称、包名、后端覆盖摘要、`StatusBadge`、findings 数、相对时间），点击进入详情。空态整卡引导「先拖入一个 APK」。
- **首屏不出现（补充单 2-5）：** 版本号、构建号、后端版本细节——全部收进设置页「关于」（§3.5）。

### 3.3 分析进行中页（补充单 2-3）

三区布局，对应一次真实分析的时间线：

| 区 | 位置 | 内容与数据来源 |
|---|---|---|
| 阶段进度 | 左列 | 采集 → 解析 → 索引 → 证据 → 报告 五阶段时间线；每阶段 `StatusBadge`（pending/running/done/error/skipped）。数据来自 run 轮询：`RunStatus`（`src/dexatlas/core/runs.py:52` `anchor: RunStatus`）与 `RunCompleteness`（`src/dexatlas/core/runs.py:75` `anchor: RunCompleteness`） |
| 实时日志 | 中间 | 等宽字体滚动区，按级别着色（info/debug/warn/error/success）。日志来自 Tauri 侧车进程对分析进程 stdout/stderr 的转发——现有后端没有日志流契约，桌面端不得为此新增 REST 端点；run 级错误另见 `run.errors` |
| 后端状态 | 右列 | Apktool / JADX / Androguard 三卡片：版本、可用性、当前阶段。数据来自 `GET /backends`（`src/dexatlas/api/app.py:349-350` `anchor: def list_backends(`）；缺失后端显示 `missing_error` 的安装提示（`src/dexatlas/tools/base.py:144` `anchor: missing_error`） |

顶部提供「取消分析」入口（REST 取消端点，`src/dexatlas/api/app.py:452-457`），取消后 run 的状态记为枚举值 `CANCELLED`（`src/dexatlas/core/runs.py:68-71` `anchor: CANCELLED`），界面呈现「已按请求停止」，不混入失败语义。

### 3.4 项目详情页（补充单 2-4）

三栏：**列表 / 主体 / 证据抽屉**。

- **左列·证据列表：** 符号、字符串、权限、组件、汇聚点条目，带来源工具标签（JADX/Apktool/Androguard）与等级（verified/lead/insufficient）。支持关键字与类别筛选。数据来自证据列表端点（`src/dexatlas/api/app.py:795-796` `anchor: def list_evidence(`），每条含来源工具、版本与 locator。
- **中间·主体：** 两种视图切换——源码阅读（class/method source，`src/dexatlas/api/app.py:637` 与 `src/dexatlas/api/app.py:699`，响应头带 `X-DexAtlas-Source-Kind`/`X-DexAtlas-Source-Locator`，见 `src/dexatlas/api/app.py:841-846`）与调用关系（callers/callees，`src/dexatlas/api/app.py:757` `anchor: xrefs`）。长包名、长签名、长路径换行显示，不截断。
- **右侧·证据抽屉：** `Drawer` 承载选中证据的完整记录：provenance locator 列表 + 每条 locator 的「解析」动作。解析走 `GET /api/projects/{id}/locators/resolve`（`src/dexatlas/workbench/app.py:238-239` `anchor: resolve_locator`），返回 `LocatorResolution`（`src/dexatlas/mcp/schemas.py:429` `anchor: LocatorResolution`）：`resolved` 布尔 + `reason` 人话 + 命中的源码文本。解析失败如实显示原因（「反编译器未安装」与「该文件不在本次分析中」是两种事实）。
- 顶部 `PartialBanner`：run 的 `completeness=partial` 或存在 `errors` 时常驻，列明未完成的步骤；横幅不阻塞下方数据展示。

### 3.5 设置页（补充单 2-5）

四个分组，全部是配置的**收口处**：

1. **分析后端：** Apktool jar 路径（`DEXATLAS_APKTOOL_JAR`，`src/dexatlas/tools/apktool/adapter.py:106` `anchor: DEXATLAS_APKTOOL_JAR`）、JADX 路径（`DEXATLAS_JADX_PATH`，`src/dexatlas/tools/jadx/adapter.py:183` `anchor: DEXATLAS_JADX_PATH`）、Androguard（内置，无路径）。改动写入 Tauri 本地配置并在下次分析时以环境变量注入侧车进程；设置页同时展示各后端当前探测到的版本（`BackendRegistry.versions`，`src/dexatlas/tools/registry.py:49` `anchor: versions`）。
2. **模型配置：** `DEXATLAS_AGENT_BASE_URL` / `DEXATLAS_AGENT_MODEL` / `DEXATLAS_AGENT_PROVIDER` / `DEXATLAS_AGENT_API_KEY`（`src/dexatlas/workbench/agent_tasks.py:56-68`）。API key 只写不读回；界面显示 provider 与 model 名，永不显示 key（`AgentConfigView` 的约定，`src/dexatlas/workbench/agent_tasks.py:353` `anchor: AgentConfigView`）。
3. **应用偏好：** 主题（当前固定浅色）、界面语言（简体中文）。
4. **关于：** 应用名、版本号、构建信息、分析核心说明——全应用唯一展示版本细节的地方。

## 4. 视觉 token

唯一来源：`desktop/src/styles/tokens.css`。新样式禁止写裸值；token 命名与下表一致。实现与下表冲突时，改实现不改表——表是规范。

### 4.1 设计原则（补充单 3-1 ~ 3-5）

- **深海军蓝**是品牌与主操作色；**淡紫/橙渐变**只出现在首屏 hero、品牌强调描边两处，不进工作区。
- **圆角 16px** 为卡片/面板基准；按钮、输入框 12px；徽章、小元素 8px。
- **阴影两级**：`--shadow-1` 静置卡片，`--shadow-2` 悬浮/弹层；不用更重的投影。
- **线性图标为主**（Lucide 风格，1.5–2px 描边）；插画只允许出现在首屏，且必须原创，不复制第三方资产。
- **按钮层级**：主按钮实心海军蓝（关键动作唯一）；次按钮描边；危险按钮红，且必须带确认（§5 Button）。

### 4.2 颜色 token

| Token | 值 | 用途 |
|---|---|---|
| `--color-navy-900` | `#101b30` | 侧栏底部、最深标题底 |
| `--color-navy-800` | `#16243d` | 主品牌：侧栏、主按钮 |
| `--color-navy-700` | `#1f3252` | 悬停态 |
| `--color-navy-600` | `#2c4370` | 次级强调 |
| `--color-lavender` | `#b8a7f5` | 渐变端点、焦点环 |
| `--color-lavender-soft` | `#d8cefc` | 选中背景、标签 |
| `--color-apricot` | `#f7c59f` | 渐变端点、警示强调 |
| `--color-apricot-soft` | `#fbe3cf` | 警示浅底 |
| `--color-bg` | `#fbf7f2` | 应用底色（暖白） |
| `--color-surface` | `#ffffff` | 卡片表面 |
| `--color-surface-muted` | `#f4efe8` | 日志区、表头 |
| `--color-border` / `--color-border-strong` | `#e8e0d5` / `#d8cdbd` | 描边 / 强调描边 |
| `--color-text` / `-secondary` / `-muted` / `-invert` | `#24303f` / `#5d6b7a` / `#8a95a1` / `#f6f9ff` | 文本四级 |
| `--color-success` / `-warning` / `-danger` / `-info` | `#2e9e6b` / `#d98a2b` / `#d64550` / `#4a7fd6` | 语义色，只表状态不做装饰 |

### 4.3 渐变、圆角、阴影、间距、字体

| Token | 值 | 约束 |
|---|---|---|
| `--gradient-brand` | `linear-gradient(135deg, #b8a7f5, #f7c59f)` | 品牌强调描边 |
| `--gradient-hero` | `linear-gradient(135deg, #e9e2fb, #fdeeda)` | **仅首屏** hero 底 |
| `--radius-lg` / `-md` / `-sm` / `-pill` | `16px` / `12px` / `8px` / `999px` | 卡片 / 按钮输入框 / 徽章 / 胶囊 |
| `--shadow-1` | `0 1px 3px rgba(22,36,61,.06), 0 1px 2px rgba(22,36,61,.04)` | 静置卡片 |
| `--shadow-2` | `0 8px 24px rgba(22,36,61,.10), 0 2px 6px rgba(22,36,61,.05)` | 悬浮、Dialog/Drawer |
| `--space-1…8` | `4/8/12/16/24/32/48/64px` | 8px 基线步进（4px 为半步） |
| `--text-xs…3xl` | `12/13/14/16/20/26/34px` | 正文 14px；页题 26px；数字展示 34px 等宽 |
| `--font-sans` / `--font-mono` | Inter 系 / JetBrains Mono 系 | 中文回退 PingFang SC、Microsoft YaHei |
| `--sidebar-width` | `232px` | 侧栏常宽 |
| `--transition-fast` | `140ms ease` | 全部过渡动效时长上限 |

焦点环：所有可交互元素 `:focus-visible` 时 `outline: 2px solid var(--color-lavender); outline-offset: 2px`；鼠标操作不出现双份描边。`prefers-reduced-motion: reduce` 时关闭进度动画与过渡。

## 5. 组件清单与职责

全部组件在 `desktop/src/components/` 同一处定义、经 `desktop/src/components/index.ts` 统一出口；页面只从这里导入（补充单 4-3）。组件不发请求、不造结论，数据一律由页面层传入。画廊页 `/gallery` 逐个展示各组件全部状态，是组件一致性的验收现场。

| 组件 | 职责 | 关键约定 |
|---|---|---|
| `Button` | 主/次/危险/ghost 四变体，三尺寸 | `loading`/`disabled` 禁点；`confirm` 非空时点击先弹确认（危险操作必带） |
| `Card` | 基础卡片（Header/Body/Footer） | 圆角 `--radius-lg` + `--shadow-1` |
| `Panel` | 可折叠内容分区 | 标题点击切换，箭头旋转 |
| `MetricCard` | 计数指标卡 | 数字等宽字体；数值由页面传入，组件不计算 |
| `Table` | 数据表 | 客户端排序、行可点；`empty` 插槽接 `EmptyState` |
| `StatusBadge` | 五态徽章：completed/running/failed/partial/pending | running 带呼吸动画；红绿不唯一表意（配图标与文字） |
| `Sidebar` | 左侧栏导航 | 受控折叠；当前项淡紫浅调背景 |
| `Breadcrumbs` | 层级路径 | 末项为当前页，不可点 |
| `Dialog` | 模态对话框 | Escape 关闭、遮罩点击关闭、焦点陷阱、关闭后焦点返回触发元素 |
| `Drawer` | 侧滑抽屉（证据抽屉容器） | 同 Dialog 的浮层四约定；右滑默认 |
| `Tabs` | 页内切换 | `role=tablist/tab/tabpanel`，方向键移动 |
| `Input` / `SearchInput` | 文本输入 / 检索框 | label 常显；错误信息与输入框关联 |
| `EmptyState` | 空态 | 一句说明 + 下一步动作 |
| `ErrorState` | 错误态 | 可读原因 + 重试入口 |
| `LoadingState` | 加载态 | 骨架屏；不做假进度条 |
| `PartialBanner` | 部分完成横幅 | `warning/info/danger` 三色调；列明失败步骤 + 重试入口；不阻塞页面其余部分 |
| `Timeline` | 阶段/工具调用时间线 | 顺序、状态、耗时 |
| `SourcePreview` | 源码预览 | 行号对齐、长行换行不截断；等宽字体 |
| `DragDropUploader` | 拖拽上传 | 扩展名白名单（默认 `.apk`）+ 大小上限（默认 512MB）前端校验；拒绝给中文原因；键盘 Enter/Space 触发文件选择 |
| `useDismissable` / `useFocusTrap` | 浮层行为 hooks | Escape、遮罩、滚动锁定、Tab 循环、焦点还原 |

## 6. 状态矩阵

每个页面的每次取数必须落在下表之一，不允许白屏或跳变。口径与 [workbench-ui.md §3](workbench-ui.md#3-状态模型) 一致，桌面端将 `unavailable` 并入 `error` 呈现（说明缺什么、怎么配）。

| 状态 | 语义 | UI 约定 |
|---|---|---|
| `loading` | 请求在途 | `LoadingState` 骨架屏；分析页日志区可显示进行中标记 |
| `empty` | 成功但集合为空 | `EmptyState`：一句说明 + 下一步动作 |
| `success` | 完整数据 | 正常渲染 |
| `partial` | 数据有但完整性打折 | `PartialBanner` 常驻 + 详情处标注；字段取自 `RunCompleteness`（`src/dexatlas/core/runs.py:75` `anchor: RunCompleteness`）与项目错误列表，不新造指标 |
| `error` | 请求失败或功能不可用 | `ErrorState`：可读原因 + 重试入口；agent 未配置模型时明确拒答（`configured=false`，`src/dexatlas/workbench/agent_tasks.py:353-356` `anchor: AgentConfigView`），不用替身回答 |

轮询与终态：分析进行中页与 agent 任务都是 accept → poll → 终态。agent 任务终态集合 `TERMINAL_STATUSES`（`src/dexatlas/workbench/agent_tasks.py:93` `anchor: TERMINAL_STATUSES`）之外的 `TaskStatus`（`src/dexatlas/agent/state.py:34` `anchor: TaskStatus`）都按进行中呈现；到达终态停止轮询。`budget_exhausted`/`interrupted` 如实显示「未跑完」，不写成完成。

## 7. 键盘与可访问性

- **全链路键盘可达：** 拖拽上传（Enter/Space 打开文件选择）、导航、筛选、证据跳转、locator 解析、报告导出、返回，全部 Tab/Enter 完成。
- **焦点可见：** 统一焦点环（§4.3）；浮层用 `useFocusTrap` 限制 Tab 循环，关闭后焦点还原到触发元素。
- **触控目标：** 交互元素最小 44px 命中区域。
- **语义化与标注：** 浮层 `role="dialog"` + `aria-modal`；Tab 组用 `tablist/tab/tabpanel`；图标按钮带 `aria-label`；状态不只靠颜色（徽章带图标与文字）。
- **动效克制：** 所有过渡 ≤140ms；`prefers-reduced-motion` 下停用呼吸/进度动画。
- **文本即数据：** 来自 APK 的源码与字符串按 `UntrustedText` 约定仅作展示（`src/dexatlas/mcp/schemas.py:43` `anchor: UntrustedText`），界面不渲染其可执行语义。

## 8. 与 DexAtlas 后端的接线边界

桌面应用通过 **Tauri 侧车进程**运行现有 DexAtlas（CLI/HTTP 均可），前端只经侧车的本地通道取数；**不复制分析逻辑，不新增公共契约**。页面 → 现有能力的映射：

| 页面/能力 | 调用的现有能力 | 说明 |
|---|---|---|
| 首页·项目列表 | MCP 工具 `list_projects`（`src/dexatlas/mcp/tools/projects.py:72` `anchor: list_projects`）或 REST `GET /projects`（`src/dexatlas/api/app.py:402-403` `anchor: def list_projects(`） | 同一函数，两种既有暴露 |
| 首页·上传分析 | REST `POST /analyze`（202，`src/dexatlas/api/app.py:359-365` `anchor: def analyze(`）或 workbench `POST /api/analyze`（`src/dexatlas/workbench/app.py:262-263`） | 复用共享上传策略与后台分析（`src/dexatlas/api/uploads.py:356` `anchor: run_background_analysis`）；同哈希已分析直接返回既有项目 |
| 分析页·进度 | REST `GET /projects/{id}/runs` 与 `GET /projects/{id}/runs/{run_id}`（`src/dexatlas/api/app.py:417-440`） | run 的 status/completeness/errors 驱动三区 |
| 分析页·后端状态 | REST `GET /backends`（`src/dexatlas/api/app.py:349-350` `anchor: def list_backends(`） | available/missing/versions |
| 详情页·检索 | MCP `search_symbols`（`src/dexatlas/mcp/tools/symbols.py:86` `anchor: search_symbols`） | 关键字 → 符号 |
| 详情页·源码 | MCP `class_source` / `method_source`（`src/dexatlas/mcp/tools/symbols.py:227`、`src/dexatlas/mcp/tools/symbols.py:227`） | Java 优先，Smali 回退 |
| 详情页·调用关系 | MCP `find_callers` / `find_callees`（`src/dexatlas/mcp/tools/references.py:56`、`src/dexatlas/mcp/tools/references.py:56`） | callers/callees 图 |
| 证据与抽屉 | MCP `get_evidence`（`src/dexatlas/mcp/tools/evidence.py:14` `anchor: get_evidence`）、`resolve_locator`（`src/dexatlas/mcp/tools/evidence.py:38` `anchor: resolve_locator`） | 证据记录与 locator 解析 |
| 报告导出 | workbench `GET /api/projects/{id}/report`（`src/dexatlas/workbench/app.py:304-305` `anchor: def export_report(`）或 REST `GET /projects/{id}/report`（`src/dexatlas/api/app.py:806`） | json/markdown 两种既有格式 |
| Agent 问答 | workbench `GET /api/agent/config`、`POST /api/projects/{id}/agent/tasks`、`GET /api/agent/tasks/{id}[/report]`（`src/dexatlas/workbench/app.py:361-456`） | 未配置模型时 `configured=false`，界面拒答 |

**边界红线：**

1. 桌面端不得引入第二套分析语义；页面上每个数字都能溯回 workspace（同 [workbench.md](workbench.md) 对浏览器端的要求）。
2. 不改 REST/MCP/CLI 契约、报告 schema、locator、状态码、退出码；侧车进程是这些契约的客户端。
3. 上传是唯一写路径，走与分析管线相同的 `stage_upload` + `Analyzer.analyze`；证据与报告只读。
4. 新增读取的字段必须先在消费的类型层对齐既有返回形状（如 `ProjectSummary`，`src/dexatlas/mcp/schemas.py:93` `anchor: ProjectSummary`），不发明字段。

## 9. E 盘 UI 库复用说明

策略（补充单 §3）：**看规范、抄结构、不整库依赖**。各库取什么、不取什么：

| 库 | 取 | 不取 |
|---|---|---|
| `design-systems/primer-primitives` | token 分层与命名方式：字号阶梯（12/14/16/20/32/40）、间距半步进（2/4/8/…）、圆角分档；「base → functional」两层结构 | 其颜色值与暗色主题（本文 §4 已定深海军蓝 + 暖白） |
| `design-systems/carbon` | 高密度场景的尺寸分级：表格/日志区行高取 container 档（24/32/40px），紧凑字号配 compact 行距；`_spacing.scss` 的 01–13 档命名法 | 其主题系统与组件实现 |
| `web/shadcn-ui` | 组件源码组织：一文件一组件 + 统一 index 出口 + 画廊页展示（对照其 `registry/new-york-v4/ui/` 结构）；复制式引入、按需改造 | 把 shadcn 作为运行时依赖整体引入 |
| `web/radix-primitives` | 复杂交互行为参考与按需单引：dialog、drawer（sheet）、tabs、focus-scope 的焦点管理与无障碍语义 | 整包引入或替换自有组件库 |
| `foundations/lucide` | 线性图标风格与图标源（4000+ 图标），匹配「线性图标为主」 | emoji 当产品图标；品牌插画（首屏插画原创） |

## 10. 验收对照（Q2-M1 退出口径）

| 补充单条目 | 本文落点 |
|---|---|
| 4-1 三步主链路 | §3.2 首屏 → §3.3 分析页 → §3.4 详情/证据 → §3.4 抽屉解析 → §8 报告导出 |
| 4-2 海报感统一 | §4 token 表；画廊页逐 token 展示 |
| 4-3 组件入库 | §5 清单 = `desktop/src/components/index.ts` 出口 = 画廊页分区 |
| 4-4 细节体验 | §6 状态矩阵、§7 键盘与可访问性、§5 DragDropUploader 校验 |
| 4-5 原型 + 截图 | 画廊页 + 核心页面在 Windows 可运行（Q2-M3 验收，见 [Q2 收尾单](../roadmap/phase4-q2-closure.md)） |
