# Phase 4 Q2 验收报告 — 桌面应用（Tauri + React）

**日期：** 2026-11-24 · **性质：** Q2 收尾验收记录 · **基线：** 分支 `claude/youthful-clarke-db2263-wt` @ `215afcb`
**验收对象：** [Q2 补充单](../roadmap/phase4-q2-supplement.md) §6 验收矩阵 · [Q2 收尾单](../roadmap/phase4-q2-closure.md) §3 退出条件
**上游素材：** [设计规范](../architecture/desktop-app.md) · T2 可访问性审计（`.scratch/q2-m3-a11y-report.md`，工作区文件不入库） · T3 截图说明（`.scratch/q2-m3-screenshots.md`，工作区文件不入库）

> **本文的地位。** Q2 补充单 §6 要求按八个维度给验收结论，收尾单 §3 要求逐条勾选退出条件。本文是逐维度结论与证据的落点；截图一律指向 `docs/assets/phase4-q2/` 下的四张 Tauri 真窗口截图。**诚实优先于好看**：不能核验的条件标「未验证」并说明缺什么，不把「待完成」改写成「完成」。

## 0. 一页结论

| 维度 | 结论 | 一句话依据 |
|---|---|---|
| 产品方向 | ✅ 通过 | 首屏「拖拽上传 + 最近项目」、浅色工作室气质成立；截图 01 |
| 信息架构 | ✅ 通过（带 1 项如实标注的前端模拟） | demo.apk 三步链路 8618 实测走通；截图 02、03 |
| 视觉语言 | ✅ 通过 | navy/lavender/apricot token、圆角 16px、两级阴影统一生效；截图 04 |
| 组件一致 | ✅ 通过 | 19 个组件 + 3 个状态组件全部出自 `desktop/src/components/` |
| 状态诚实 | ✅ 通过 | loading/empty/error/partial 五页全覆盖（T2 审计）；部分态横幅如实 |
| 可访问性 | ✅ 通过（3 项低优先级遗留如实记录） | 键盘可达、焦点环、reduced-motion 降级实测；见 §3.6 |
| 技术边界 | ✅ 通过（1 项限制如实记录） | Windows 构建链打通、真窗口可启动；src/ 与 desktop/ 之外的公共契约零改动 |
| 冻结解除范围 | ✅ 符合 | 改动全部落在解冻范围（`desktop/` + 文档 + 截图资产） |

**总体判定：Q2 的八个验收维度全部通过**；带三项如实记录的遗留（无 skip-link、首页列表无骨架屏、FindingsPage 错误文案可读性）与两项已知边界（后端无 `/api/backends`、`/runs`、`/cancel` 端点；分析页阶段推进为前端模拟）。

## 1. 验收环境与真实链路验证

- **后端：** DexAtlas workbench 运行于 `127.0.0.1:8618`，`GET /api/health` → `{"version":"1.0.2","workspace":".dexatlas"}`（2026-11-24 实测）。
- **桌面应用：** Tauri release 产物 `desktop/src-tauri/target/release/dexatlas-desktop.exe`（13.1 MB，`f7a286a` 构建）直接运行，WebView2 加载 `desktop/dist`（`npm run build` 产物，HashRouter）——是 Tauri 真窗口，不是 dev server、不是浏览器页签。
- **真实链路（补充单 4-1 的三步）：** 用 `examples/demo-app/demo.apk`（项目 `apk_80a8fe0e81204c9f`）完成「拖入 APK → 查看证据 → 导出报告」；分析页另以 `examples/wide-app/wide.apk`（项目 `apk_d342e11b7931077d`）完成一次完整真实分析流。截图与页面数据全部来自 8618 真实 API，无 mock。
- **截图方法：** 窗口置前后 PowerShell `CopyFromScreen` 按物理像素截取（1280×840 逻辑 / 2264×1534 物理 @1.75x）；页面导航与拖拽交互经 WebView2 临时 CDP 端口注入**真实 UI 事件**完成，未改任何 `src/` 源码。画面内无用户名、无绝对路径（localhost 地址与 first-party 示例项目 ID 除外）。

## 2. 已知限制（如实记录，不包装）

1. **后端能力缺口：** workbench（8618）当前不提供 `GET /api/backends`（实测 404）、run 列表 `/runs`（实测 404）与分析取消 `/cancel`（POST 实测 405）。桌面端设置页已按「该端点在后端未提供」如实呈现，不为缺失端点造假数据。
2. **分析页阶段推进为前端模拟：** 现有后端无阶段级进度契约，分析页左侧「阶段进度」由前端根据轮询状态推进（页面内有角标注明）；日志区展示的是状态轮询时间线（同样有角标），不是后端日志流。设计规范 §3.3 已声明该边界。
3. **cargo release 构建通过、可运行，但尚未做安装包分发**（`npm run tauri build` 打包在 Windows 上受 WIX/RustGpt 工具链限制未走完）；补充单 §4.2 本就明确「不做应用商店分发、自动更新服务、签名证书采购或跨平台发布矩阵」，故不计为缺口，但分发形态当前只有「直接运行 release exe」一种。
4. **FindingsPage 错误文案可读性：** ApiError 对非 HTTP 错误的 message 拼接带原始 `undefined:` 前缀（T2 审计 A-9，低优先级遗留）。

## 3. 逐维度验收结论（对照补充单 §6）

### 3.1 产品方向 — ✅ 通过

**通过条件：** 高端浅色工作室气质成立，面向安全分析者，证据链可复核。

- 首屏为暖白底 + hero 渐变拖拽上传区 + 「最近项目」表格，气质与设计规范 §1「高端浅色工作室」一致：[01-product-home.png](../assets/phase4-q2/01-product-home.png)。
- 详情页把「来源后端 / detail JSON / locator / 打开来源 / resolve」做成一级 UI，证据链可复核的价值主张落在交互上：[03-detail-evidence.png](../assets/phase4-q2/03-detail-evidence.png)。
- 面向安全分析者：项目表格呈现「规模（类/方法/调用点）· 状态 · 证据数 · 时间」，分析页呈现后端版本与阶段（截图 02）。

### 3.2 信息架构 — ✅ 通过（带 1 项如实标注的前端模拟）

**通过条件：** 拖入 APK → 查看证据 → 导出报告 三步可完成。

- 第一步「拖入 APK」：首页拖拽上传区实测接受 `.apk`、拒绝非 `.apk`（行内 `role="alert"` 报错，见截图 01 中「仅支持 .apk 文件」的保留镜头）。
- 第二步「查看证据」：分析完成后跳转详情页，11 条真实证据（字符串/符号/权限/汇聚点，来源 APK Reader/Apktool/JADX/Androguard）可筛选、可打开抽屉、可 resolve locator：[03-detail-evidence.png](../assets/phase4-q2/03-detail-evidence.png)。
- 第三步「导出报告」：详情页与报告页提供 Markdown/JSON 导出，demo.apk 链路 8618 实测走通。
- 主导航五项（项目/分析/证据/报告/设置）与侧栏结构按设计规范 §3.1 落地（截图 01 侧栏可见）。
- 保留项：分析页「阶段进度」为前端模拟推进（角标如实标注），非后端阶段流——见 §2.2。

### 3.3 视觉语言 — ✅ 通过

**通过条件：** 深海军蓝 + 淡紫橙渐变、大圆角、轻阴影、线性图标统一。

- token 唯一来源 `desktop/src/styles/tokens.css`：暖白底 `#fbf7f2`、深海军蓝 `#16243d`、淡紫 `#b8a7f5`、淡橙 `#f7c59f`、圆角 16/12/8px、`--shadow-1/--shadow-2` 两级阴影、焦点环 2px 淡紫——与设计规范 §4 一致。
- 组件画廊逐 token 展示 12 枚颜色样卡 + Button 全变体：[04-visual-gallery.png](../assets/phase4-q2/04-visual-gallery.png)。
- 渐变仅出现在首屏 hero 与品牌强调处；页面工作区保持安静。侧栏 navy、卡片大圆角轻阴影、lucide 线性图标贯穿四张截图。

### 3.4 组件一致 — ✅ 通过

**通过条件：** 高频组件全部来自同一组件库。

- 组件库落在 `desktop/src/components/`：AppLayout、Sidebar、Breadcrumbs、Button、Card、Panel、Dialog、Drawer、Input、SearchInput、MetricCard、PartialBanner、SourcePreview、StatusBadge、Table、Tabs、Timeline、DragDropUploader + 状态组件 states/{LoadingState, EmptyState, ErrorState}，均在画廊页（`/gallery`）可预览（补充单 4-3）。
- 五个业务页面（首页/分析/详情/证据/报告）与设置页均复用该组件库与统一状态组件，无页面自造态（T2 审计 §一：「四态组件统一由 states 承担，五页均复用」）。
- 一次性校验：T1 已删除临时 `client.ts`、`mockData.ts` 与废弃页面 `Home.tsx`、`AnalysisPage.tsx`（grep 零引用后删除），无第二套 UI 数据轨。

### 3.5 状态诚实 — ✅ 通过

**通过条件：** loading/empty/error/partial 均有真实 UI 呈现。

T2 审计（`.scratch/q2-m3-a11y-report.md` §一）对五页逐一实测，摘要：

| 页面 | loading | empty | error | partial |
|---|---|---|---|---|
| 首页 | 上传中 `role="status"` | 空项目 EmptyState | 列表失败 ErrorState + 重试（fetch 拦截实测） | —（无部分概念） |
| 分析页 | 等待入库 LoadingState | 无 id EmptyState | 断后端/失败 ErrorState + 明细 | 404 长轮询横幅、轮询失败横幅、`errors.length>0`「结果不完整」横幅（均实测出现） |
| 详情页 | LoadingState | 筛选无命中 EmptyState | 404/断后端 ErrorState + 重试 | PartialBanner（missing_backends/errors，机制在） |
| 证据页 | LoadingState table | 无命中 EmptyState | 列表失败 ErrorState + onRetry（断后端实测可恢复） | — |
| 报告页 | LoadingState + 导出中文案 | 空列表 EmptyState | 列表失败/单行导出失败行内 `role="alert"` | — |

- 失败不被包装成完成：分析页 `errors.length>0` 时显示「结果不完整」横幅并列出错误明细，而不是只给绿色完成态；设置页对后端未提供的端点如实显示「该端点在后端未提供」。
- Agent/模型入口：模型未配置时明确拒答、不使用替身回答（Phase 4 已验证的能力，Q2 未改动该链路）。

### 3.6 可访问性 — ✅ 通过（3 项低优先级遗留如实记录）

**通过条件：** 键盘可达、焦点可见、危险操作有确认。

- 键盘可达（T2 审计 §二）：侧栏 `NavLink` 原生链接 Tab 可达（`aria-current` 自动管理）；表格行操作均经可聚焦元素；详情页证据条目为 `<button>` 且带 `aria-expanded`、筛选 chips 带 `aria-pressed`；抽屉/对话框有 Esc 关闭、焦点陷阱（Tab 循环不逃逸）、关闭后焦点返回触发元素、`role="dialog"` + `aria-modal`；Tabs roving tabindex + 方向键循环。
- 焦点可见：`global.css` 裸 `:focus-visible`（2px `--color-lavender` + offset 2px）全局兜底，Button/Card/DragDropUploader/Sidebar/Table/Tabs 等另有显式规则；T2 补齐 SearchInput 清除按钮与 Sidebar 折叠按钮两处。
- 动画尊重 `prefers-reduced-motion`：T2 在 `global.css` 新增全局降级块（时长 0.01ms、迭代 1 次、显式 `animation: none` 命中 shimmer/spinner/脉冲/滑入），已验证规则注入。
- 拖拽上传反馈：拖入非 `.apk` 行内 `role="alert"` 报错，无原生 alert（首页与画廊两处均实测）。
- 遗留（如实记录，均低优先级）：无 skip-link（A-7，侧栏仅 5 项、首屏可达成本低）；首页项目列表加载期无骨架屏（A-8，fetch 快、体感影响小）；FindingsPage 错误文案 `undefined:` 前缀（A-9）。三者均记入「后续迭代」。
- 危险操作确认：Q2 范围内无删除类危险操作入口；上传取消/覆盖不存在（重复上传为新项目），故无新增确认交互需求。

### 3.7 技术边界 — ✅ 通过（1 项限制如实记录）

**通过条件：** 不破坏现有公共契约；Tauri 原型可在 Windows 启动。

- **Tauri 原型 Windows 可启动：** ✅。构建链 `vcvarsall x64 → cargo build --release`（复现步骤 `.scratch/q2-windows-build-notes.md`），release exe 直接运行（截图 01–04 均为该真窗口）。
- **公共契约：** Q2 全部改动限于 `desktop/`（新增目录）、`docs/`（设计规范/补充单/收尾单/验收报告）与 `docs/assets/phase4-q2/`（截图）；`src/dexatlas/` 的 REST/MCP/CLI/报告 schema/locator/状态码/退出码零改动。桌面端是契约消费方，不复制分析逻辑（分析能力经本地 HTTP 调用 8618 workbench）。
- **仓库卫生：** 截图画面仅含 localhost 地址与 first-party 示例项目 ID；无第三方 APK/DEX/so、无秘密入库。
- 限制：`/api/backends`、`/runs`、`/cancel` 在 workbench 端不存在（实测 404/405），桌面端如实降级呈现——见 §2.1。

### 3.8 冻结解除范围 — ✅ 符合

**通过条件：** 仅桌面应用与必要接线被解冻，其余仍按 Freeze 规则。

- 本阶段提交（`9bbf87e`、`520bf4d`、`7c53a7d`、`6ed485c`、`7f56d5b`、`17bbd95`、`c92879b`、`1d7623b`、`f7a286a`、`1c08bfc`、`2579866`、`34a2790`、`215afcb`）全部落在解冻范围：`desktop/` 新增、`docs/roadmap|architecture|reports|assets` 文档与截图。
- 未触碰继续冻结项：无新分析后端、无新漏洞规则、无 REST/MCP/CLI 契约变更、无报告 schema 变更、无新外部平台发布动作；浏览器 Workbench 保留（两者过渡期并存）。

## 4. 截图对照（收尾单 §4 验收流程第 3 步）

四步标准与四张 Tauri 真窗口截图一一对应（逐图达标点详见 `.scratch/q2-m3-screenshots.md`）：

| 步骤 | 标准 | 截图 | 达标点 |
|---|---|---|---|
| 1 定义产品方向 | 首页 = 拖拽上传 + 最近项目；证据链可复核气质 | [01-product-home.png](../assets/phase4-q2/01-product-home.png) | hero 上传区（含拖拽校验报错镜头）、5 行真实最近项目、五项侧栏导航 |
| 2 搭建信息结构 | 分析页三区：阶段进度 / 实时日志 / 后端状态 | [02-structure-analysis.png](../assets/phase4-q2/02-structure-analysis.png) | 真实分析流（wide.apk）完成横幅；三区数据全部来自 8618 真实 API；模拟项有角标 |
| 3 控制视觉语言（信息架构延续：详情三栏 + 证据抽屉） | 三栏结构 + provenance 可视 | [03-detail-evidence.png](../assets/phase4-q2/03-detail-evidence.png) | 证据列表 / 证据正文 / 抽屉三栏；E-0001 抽屉含来源后端、detail JSON、locator、「打开来源」「resolve」 |
| 4 按标准迭代 | token 化视觉语言统一 | [04-visual-gallery.png](../assets/phase4-q2/04-visual-gallery.png) | token 总览横幅（色值/圆角/阴影/焦点环）、12 枚色卡、Button 全变体 |

## 5. 退出条件回填与门禁

收尾单 §2 交付物 12 项与 §3 退出条件的逐项勾选已回填至 [phase4-q2-closure.md](../roadmap/phase4-q2-closure.md)（本次同批提交）；勾选口径：能给出证据路径的才勾选，不能核验的如实标注。

**门禁复跑（收尾单 §4 第 4 步）：** Q2 改动限于 `desktop/` 与 `docs/`，Python 侧源码（`src/`、`tests/`、`scripts/`）零改动，因此本次验收未重跑 pytest/ruff/mypy/vulture 等仓库门禁——它们守护的树未被触碰；上次全绿记录见 v1.0.2 发布流程。**本报告自身的引用一致性由 `scripts/check-doc-citations.py` 核验**（结果见文末验证记录）。

## 6. 验证记录

- `uv run --no-sync python scripts/check-doc-citations.py`：820 条引用、0 条路径无法解析；检出 1 处漂移——`card-travels-with-the-measurement.md` 引用的 status.md Pillow 行因本分支在 status.md 顶部插入 Q2 状态行而偏移 1 行，已重锚并复跑通过（drifted: 0）。本报告自身无 `file:line` 引用（对代码的引用以文件路径与截图路径表述），不产生新的可漂移锚点。
- `GET http://127.0.0.1:8618/api/health` → 200 `{"version":"1.0.2","workspace":".dexatlas"}`；`/api/backends` → 404；`/runs` → 404；`POST /api/cancel` → 405（2026-11-24 实测，支撑 §2.1）。

## 7. 下一阶段定界建议

按收尾单 §5 三选一，本报告建议维持默认：**B. 部分解冻**——只允许修桌面应用的缺陷、性能与可用性问题（含本报告 §3.6 的 A-7/A-8/A-9 与 §2 的端点缺口跟进），新功能重新评审。最终以 status.md 回填为准。
