# Phase 5 验收报告 — 桌面应用自包含与阶段级可观测

**日期：** 2026-11-26 · **性质：** Phase 5 验收记录 · **基线：** `origin/main` @ `33e4ba9`（PR #22 合入后的树）
**验收对象：** [Phase 5 执行单](../roadmap/phase5-plan.md) W1–W4 与端到端验收
**上游素材：** [Q2 验收报告](phase4-q2-acceptance.md)（八维度口径）· [桌面应用设计规范](../architecture/desktop-app.md) · 端到端走查报告 `.scratch/q2-final-e2e-walkthrough.md`（工作区文件，不入库；截图已复制到 `docs/assets/phase5/`）· W2 合入后复测 `.scratch/phase5-w2-retest.md` · 打包 exe 首轮验收 `.scratch/phase5-exe-acceptance.md` 与二次验收 `.scratch/phase5-exe-recheck.md`（后三份为工作区文件，不入库；二次验收截图已复制到 `docs/assets/phase5/`）

> **本文的地位。** Phase 5 执行单 §2.1 为每项工作列了验收判据，§5 给了「完成定义」。本文逐项写判据、证据与结论。**诚实优先于好看**：没有证据的判据标「未验证」并写清缺什么；判据只满足一部分的，写「部分满足」，不把「在途中」改写成「完成」。
>
> **本文相对上一版的修订。** 上一版写在 `9614cb0` 上，把「打包 exe 未验证」「W2 未复测」「P1/P3/P4 未修」「契约活检不覆盖 stages」记为开放项。本版逐条重核：这些项目现已全部有结论，证据在下面。基线也从 `9614cb0` 前移到 `33e4ba9`（PR #21、#22 已合入）。§7 逐项列出**仍然开放**的验收项。

## 0. 一页结论

| 工作项 | 结论 | 一句话依据 |
|---|---|---|
| W1 侧车进程真接入 | ✅ **通过** | 首轮打包 exe 验收暴露的两个真实缺陷（侧车在安装形态下从未被拉起；前端把 baseUrl 锁死到 8618 回退）已由 PR #20（`4c86b2f`）修好；修复后的二次真机验收判据 (a)–(d) **全通过**——侧车自动拉起且端口为侧车自己的 64074（三处交叉印证），上传→分析→证据→导出全链路可用，杀侧车后 UI 如实报错且进程树被清理 |
| W2 阶段级进度契约 | ✅ **通过** | 复测已完成：判据 ①–④ 通过；⑤（文档与实际一致）当时不通过，已由 PR #18 修正；③ 附带的完成态缺陷（证据格停在「待处理」）已由 PR #19 修好。契约活检已覆盖 stages 路由，静态条数 55（31 REST + 6 MCP + 18 CLI） |
| W3 C12 仓库内备料 | ✅ **备料完成**（渠道核实按指示未做） | `docs/outreach/scope-ai-mcp-compact.md` 2,674 字节（≤5,000 字符）；核对表模板 `c12-field-check-template.md` 可直接填 |
| W4 发版后运营清单 | ✅ **落盘**（1 处口径出入，见 §6.2） | `docs/ops/post-release-checklist.md` 覆盖发布当天、发布后一周、反馈渠道与下一版触发条件；清单仍含「需作者账号」的行，与执行单「不含需要作者账号的执行步骤」不完全一致 |
| 端到端验收走查 | ✅ **通过**（遗留 P1/P3/P4 已修） | 2026-11-25 走查发现 P1–P4；P1 由 PR #15 修好，P3/P4 由 PR #17（`369fb89`）修好，W2 完成态缺陷由 PR #19 修好。走查本身的对象是 W2 合入前的树，W2 后由 §3 的复测覆盖 |
| 收尾批次（2026-11-26） | ✅ **通过** | 关闭 §7 的七项开放项：打包 exe 完整后端配置（12 条证据）、MSI 安装、强杀孤儿后端（作业对象 + CI 门禁）、失败/取消时间线真机走查、「打开来源」内联、角标不说谎、终态停止轮询；并修掉走查带出的一个后端缺陷（失败状态从未落库） |

**总体判定：Phase 5 的工程交付（W1–W4）与验收动作都已完成。** 首次验收挡在前面的两条——「打包 exe 全链路未验证」与「W2 合入后未复测」——都已做完并留下证据；2026-11-26 的收尾批次又关闭了 §7 里的七项（打包形态在完整后端配置下可用、MSI 能装、强杀不留孤儿、失败与取消的时间线真机走通、「打开来源」内联展示、角标不说谎、终态停止轮询），并修掉走查带出的一个后端缺陷（分析失败的状态从来没有落库，界面会永远停在「分析中」）。

**剩下的只有四项**（§7.3）：平台覆盖（macOS/Linux 明确不纳入）、非 MSIX 容器下的启动、MCP 面是否暴露阶段工具的取舍记录、W4 清单的一处账号口径。**这些都不是挡住 Phase 5 的东西**——要么在执行单范围之外，要么是一处口径出入。**前端时间模拟兜底已于 2026-11-26 收尾删除**（§3.5 与 §7.1 就地标注）。

## 1. 验收环境与基线

- **代码基线：** `origin/main` @ `33e4ba9`（`Merge pull request #22`）。本报告在 `docs/phase5-closure` 分支上写，该分支相对 `origin/main` **只改文档与截图**，不改 `src/`、`tests/`、`desktop/src`、`scripts/`。
- **打包形态（二次验收）：** Windows 11 10.0.26300；MSVC 2022 Build Tools；`npm run tauri build` 退出码 0，产出 NSIS 与 MSI 两个 bundle；NSIS 安装器静默安装到用户目录，退出码 0。**验收全程 8618 端口无任何监听**——因此前端只要能取到数据，就必然是打到了侧车自己的端口。
- **开发形态（复测与走查）：** 后端 `uv run dexatlas-workbench`（`127.0.0.1:8618`），前端 Vite dev（`5173`，HashRouter）；JADX 1.5.2 / Apktool 2.11.1 / Androguard 4.1.4。
- **最后一次完整测量（本分支重跑，发布树，带 JADX 1.5.2 + Apktool 2.11.1）：** 测试 <!--fig:tests.total-->1863<!--/fig--> 个（<!--fig:tests.fast-->1714<!--/fig--> 快 + <!--fig:tests.slow-->149<!--/fig--> 集成），`suite.passed` <!--fig:suite.passed-->1862<!--/fig-->、`skipped` <!--fig:suite.skipped-->1<!--/fig-->、`failed` 0，一方代码覆盖率 <!--fig:coverage.pct-->93.3%<!--/fig-->（<!--fig:coverage.covered-->7468<!--/fig-->/<!--fig:coverage.total-->8001<!--/fig--> 行，见 `docs/reports/phase1-execution-report.md`）。**本分支新增了 Markdown 文件，文档篇数随之变化，已在本分支重跑完整测量刷新**（`scripts/refresh-report-figures.py`），本报告的所有生成数字均由该脚本写入，没有手写。

## 2. W1 — 侧车进程真接入

### 2.1 判据与实现

执行单 §2.1 的 W1 判据：打包后的 exe 在**不预先手动起后端**的情况下完成 上传 → 分析 → 证据 → 导出 全链路；侧车崩溃时页面显示可读错误而非静默白屏。

实现落在两处：Rust 侧 `desktop/src-tauri/src/sidecar.rs`（拉起子进程、转发端口、状态事件）与前端 `desktop/src/api/client.ts`（解析并使用侧车实际端口）。

### 2.2 首轮验收发现的两个真实缺陷（已修）

首轮打包 exe 验收（`.scratch/phase5-exe-acceptance.md`，基线 `9614cb0`）判据 (a) **不通过**、(b) 仅**部分通过**：侧车在安装形态下**从未被拉起**，前端即使在能起侧车的仓库形态下也会在启动瞬间把 baseUrl 锁死到 8618 回退端口。两个根因：

| 缺陷 | 根因 | 修法（PR #20） |
|---|---|---|
| 侧车在安装形态下起不来 | `backend_cwd()` 推断不出仓库根就返回错误，而 spawn 处用的是短路写法——推断失败时进程**从未被尝试启动** | cwd 改为可选（`None` = 不设 cwd，不是「不启动」），新增 `spawn_backend()`（`desktop/src-tauri/src/sidecar.rs:261`）与 `spawn_failure_reason()`（`:287`）把 spawn 失败翻译成人话 |
| 前端把 baseUrl 锁死 8618 | `DexAtlasClient` 是模块级单例，构造那一刻侧车还在启动、端口尚未出现 ⇒ `port: null` ⇒ 落回 `FALLBACK_BASE_URL` | 首次请求前**有界等待**端口（`desktop/src/api/client.ts:202` `waitForSidecarPort()`），订阅 `sidecar:status` 在端口变化时重解析（`:222`） |

同批还修了第三个同源问题：重启侧车时旧实例的退出线程会覆盖新实例状态，把「未能启动」显示成「已异常退出」。

### 2.3 二次验收：判据 (a)–(d) 全通过

修复后的二次真机验收（`.scratch/phase5-exe-recheck.md`，基线 `f880eff`）：

| 判据 | 结论 | 证据 |
|---|---|---|
| (a) 侧车自动拉起；Rust 侧 `get_sidecar_status` 返回真实端口 | ✅ | 进程树显示 `python.exe -m dexatlas.workbench --port 0` 是 exe 的**直接子进程**，监听 `127.0.0.1:64074`；`get_sidecar_status` 返回 `{"running":true,"port":64074,…,"failed":false}`；设置页渲染同一个端口（截图 `exe-02-settings-sidecar.png`） |
| (b) 前端请求打在侧车自己的端口上（非 8618） | ✅ | **三处交叉印证，都是 64074**：Rust 权威端口 / 侧车 uvicorn 访问日志 / 前端错误文案里的实际 baseUrl；全程 8618 无监听 |
| (c) 上传 demo.apk → 分析 → 证据 → 导出全链路可用 | ✅ | 新轮次 `run_2fbf3ba0f8914635`（访问日志 `POST /api/analyze → 202`）；导出 Markdown 落盘（4,849 B，文件头 `**Run:** run_2fbf3ba0f8914635 (completed, partial)`）；截图 `exe-03-uploaded.png`、`exe-06-evidence.png`、`exe-07-reports.png` |
| (d) 杀侧车后 UI 如实显示可读错误；关闭 exe 后整棵进程树被清理 | ✅ | 杀掉侧车后页面显示「无法连接 DexAtlas 后端（http://127.0.0.1:64074/…）」而不是白屏（截图 `exe-09-evidence-sidecar-killed.png`）；**正常关闭 exe** 后进程树快照里 `dexatlas-desktop.exe` 与两个 `python.exe` 子进程**全部消失**，端口无残留监听；侧车重启换端口到 59532 后前端**不刷新**即恢复，新请求打在 59532（截图 `exe-11-evidence-after-sidecar-restart.png`） |

> **判据 (c) 的一条环境事实（不是缺陷）：** 打包 exe 拉起的侧车在本机**没有装 jadx 与 apktool**（设置页如实显示「jadx 缺失 / apktool 缺失 / androguard 可用 v4.1.4」），因此这轮分析是 `completeness=partial`、证据 **10 条**（后端齐全时是 12 条）。后端与 UI 都如实标注了缺失——证据 E-0002、E-0006 写明「apktool/jadx did not complete in this run」。这是「后端失败是一个值，不是一个异常」的正确表现，但**覆盖度低于装了后端时的水平**，见 §7。
>
> **首轮验收已通过的一项：** 安装形态 + 完全没有后端（8618 真空、全新安装态）时，首页 / 上传 / 报告 / 设置四页**全部是可读中文错误 + 重试按钮，不是白屏**（首轮验收判据 (e)）。该场景在首轮是因侧车起不来而退化的；PR #20 修好侧车后这个场景不再复现——但首轮那次**失败得体面**本身是一条独立的结论。

### 2.4 结论：通过

**W1 的验收判据已满足**，且是在**安装形态**（NSIS 安装器真装）下满足的，不是在 `tauri dev` 下。首轮验收的 (a)/(b) 失败项已由 PR #20 修好，二次验收 (a)–(d) 全通过。

## 3. W2 — 阶段级进度契约

### 3.1 契约形状（两次改过）

W2 的 stages 契约在评审中改过一次形状：`fa61cc4` 初版把 stages 做成 run 对象的扩展字段（`RunResponse.stages[]` / `RunSummary.stages[]`），`81a33d7` 改为**独立只读端点**并复原 run 契约字段集。当前形状：

- 端点：`GET /api/projects/{id}/runs/{run_id}/stages`
- 响应：`{"project_id","run_id","run_status","stages":[{"stage","started_at","finished_at"}]}`
- 实现：`src/dexatlas/api/app.py:471-499` `anchor: get_run_stages`；workbench 同形状端点 `src/dexatlas/workbench/app.py:603-616` `anchor: get_run_stages`
- 阶段枚举：`src/dexatlas/core/runs.py:75` `anchor: RunStage`（inspect → parse-apktool → index-androguard → decompile-jadx → publish）
- 既有 run 对象**零改动**：`RunResponse` 与 `RunSummary` 都不带 stages 字段

### 3.2 复测：判据 ①–⑤（`.scratch/phase5-w2-retest.md`）

W2 合入 `9614cb0` 后做过一次只读端到端复测，逐条判据的结论：

| 判据 | 当时结论 | 证据 |
|---|---|---|
| ① stages 端点存在、返回真实阶段、顺序与 pipeline 一致 | ✅ | HTTP 200；完成态返回 5 个阶段，顺序与 `RunStage` 枚举一致；`started_at` 严格递增、`finished_at ≥ started_at`；**运行中未结束阶段 `finished_at` 为 null**；旧 run 返回 `stages:[]`（读作「无阶段事实」，不是错误）；未知 run 404 |
| ② 既有 `/runs`、`/runs/{rid}` 字段集未被加上 stages | ✅ | 实测 `/runs/{rid}` 8 字段、`/runs` 信封 4 键，**均无 stages**；`RunResponse`、`RunSummary` 代码侧同样无该字段 |
| ③ 桌面时间线的状态与顺序来自真实 stages | ✅（带一处缺陷，见下） | 页面网络面板出现 `GET …/stages → 200`；**分析进行中**时对页面 DOM 连续采样（80ms），「进行中」格严格跟随后端尚未结束的那一个阶段 |
| ④ 角标如实说明数据来源 | ✅（按当时的三种来源） | 当时三种来源分别标注：有 stages → 「后端真实阶段事件」；旧 run → 「后端 run 状态 + 前端粒度模拟」；无 run → 「前端模拟」。**2026-11-26 收尾删除了无 run 的模拟一支**：角标只剩真实来源（stages / run-status） |
| ⑤ 文档与实际一致 | ❌ **当时不通过** | `public-contracts.md` 关于 stages 的整段描述与实现**相反**（把独立端点写成 run 对象的扩展字段），端点表也缺 stages 一行 |

### 3.3 当时的两处缺陷与它们的修复

| 缺陷 | 现象 | 修法 |
|---|---|---|
| **W2 完成态缺陷**（判据 ③ 附带） | completed 的 run，时间线显示「证据 • 待处理」，而同一页面顶部写「已完成」、横幅写「12 条证据」——9/9 复现 | 阶段映射抽成纯函数 `desktop/src/stages.js`（`deriveStagesFromRun()` `:115`）：完成态按 `publish` 的结束事件置完成（证据在 publish 之前产出，见 `desktop/src/stages.js:25`），运行中的推断保持不变。**PR #19**（`416e4fb`） |
| **契约文档过时**（判据 ⑤） | `docs/architecture/public-contracts.md` 把 stages 写成 `RunResponse.stages[]` 扩展字段，与实现相反；端点表缺一行；§2.3 与 §7 的条数也不同步 | 改写为真实形状并补端点表行；**PR #18** |

### 3.4 契约活检现在覆盖 stages（PR #18）

`scripts/verify-public-contracts.py` 的 REST 段新增 3 个调用点，对新端点发真实 HTTP：响应形状、阶段事实按 pipeline 顺序与时间戳排列、无此 run → 404 带 detail。**静态条数由 52 升至 55**（31 REST + 6 MCP + 18 CLI），由 `tests/test_public_contracts.py:765-768` 盯着。

### 3.5 结论：通过

**W2 的验收判据已满足。** 判据 ⑤ 在复测当时不通过，现已由 PR #18（`5a94d43`）修正；判据 ③ 附带的完成态缺陷已由 PR #19（`416e4fb`）修好。**「前端模拟代码删除」这条判据在验收当时不字面成立**——当时模拟仍作为「连 run 状态都拿不到」时的兜底，并在角标与横幅中如实标注来源。**2026-11-26 收尾已删除该路径**：无 run 数据时五格如实显示「待处理」（状态未知），runs 请求失败时显示「后端不可用，阶段进度无法取得」与重试入口，角标只标注真实来源（stages / run-status）；见 [phase5-plan §5 修订注 ②](../roadmap/phase5-plan.md)。

## 4. 端到端验收走查（2026-11-25）

### 4.1 逐页结论

走查（`.scratch/q2-final-e2e-walkthrough.md`，对象是 **W2 合入前**的树，数据全部来自 8618 真实 API，无 mock）：

| 页面 | 结论 | 关键观察 |
|---|---|---|
| 首页 | ✅ | 侧栏五项导航 + skip-link；上传卡（拖拽 / 512MB 限制 / 重复上传提示）；最近项目表格与 `GET /api/projects` 逐行一致，含 failed 状态如实显示 |
| 项目详情三栏 + 证据抽屉 | ✅ | 头部元信息与 API 一致；证据列表 12/12 条 + 类型筛选 chip；抽屉 `role="dialog"` / `aria-modal="true"` / `aria-label="证据详情"`，字段逐条核验正确；Esc 关闭、resolve 后显示「resolved：true」 |
| 分析页 | ✅ | 真实 APK 上传命中已有项目；非法文件被前端拦截并给出可读文案；五阶段时间线全部渲染 |
| 报告页 | ✅ | Markdown 导出内容为完整报告（Summary / Evidence 三级分布 / Manifest / Exported components / Evidence 逐条）；JSON 导出 schema_version 3、三后端 `tool_versions` 齐全 |
| 证据页 | ✅ | 项目选择器、符号检索入口、证据表逐条带 locator，与 API 一致 |
| 设置页 | ✅ | 三个分析后端卡（jadx / apktool / androguard）与最近 run 的 `tool_versions` 一致；侧车进程配置可改可重启 |

错误态与健壮性：后端被杀后首页显示「项目列表加载失败 / HTTP 502 / 重试」，**不白屏**且上传卡仍可用；后端恢复后点「重试」自愈；非法文件上传被前端拦截。

### 4.2 走查发现的问题及其修复

| | 问题 | 修法 |
|---|---|---|
| **P1**（中） | 侧栏版本徽标硬编码 `v1.0.2`，与真实版本 v1.1.0 不一致——违反「数字是生成的」纪律 | **PR #15**：删掉侧栏那块硬编码的版本徽标（`git diff cd846cf^1 cd846cf -- desktop/src/components/AppLayout.tsx` 显示整块 `sidebar-footer` 被移除），版本号只留在设置页「关于」区，读的是 `GET /api/health` 的真值（`desktop/src/pages/SettingsPage.tsx:12`、`:232`） |
| **P2**（中） | W2 契约未合入 main（`stages` 端点 404） | 随 PR #14 合入；见 §3 |
| **P3**（低） | 证据抽屉「打开来源」对非文件内 locator（`zip-entries` 等）点了没反应 | **PR #17**：新增 `desktop/src/locators.ts`（`classifyLocator()` `:53`、`openSourceState()` `:133`）镜像后端 `core/locators.py` 的工具词汇判定落点；没有单文件落点时按钮禁用并给出可见说明（`desktop/src/pages/ProjectDetail.tsx:414`），文件内 locator 行为不变 |
| **P4**（低） | 键盘全量遍历未做；且 skip-link 落点没有焦点指示 | **PR #17**：补 `.app-main:focus-visible` 规则（`desktop/src/components/AppLayout.css:130`，同特异度下排在 `:focus` 之后才赢），并按逐页 Tab 遍历复核六页的焦点环、抽屉焦点陷阱与 Esc 归还 |

### 4.3 走查截图

四张走查截图入库 `docs/assets/phase5/`（来自真实 API，非侧车链路）：

| 截图 | 证明什么 |
|---|---|
| `01-home-page.jpg` | 首页：侧栏五项导航 + 上传卡 + 最近项目表，数据与 API 逐行一致 |
| `02-project-detail-evidence-drawer.jpg` | 详情三栏 + 证据抽屉：抽屉为 `role="dialog"`，字段逐条可核 |
| `03-settings-page.jpg` | 设置页：三个分析后端卡与侧车进程配置 |
| `04-backend-down-error.jpg` | 后端被杀后的错误态：如实报错 + 重试按钮，不白屏 |

![走查：首页（数据与真实 API 逐行一致）](../assets/phase5/01-home-page.jpg)

![走查：项目详情三栏与证据抽屉（role="dialog"，字段逐条可核）](../assets/phase5/02-project-detail-evidence-drawer.jpg)

### 4.4 结论：通过

主链路与错误态全部通过，遗留问题已修。**注意走查的对象是 W2 合入前的树**——W2 之后的桌面行为由 §3 的复测与 §2 的打包验收覆盖。

## 5. 打包 exe 二次验收截图（2026-11-26）

十二张截图入库 `docs/assets/phase5/`（原样复制自 `.scratch/phase5-exe-recheck-screens/`，文件名加 `exe-` 前缀与走查截图区分；原始抓屏文件仍留在 `.scratch/`）。下表逐张说明它**证明什么**，正文嵌入其中关键的六张，其余在 `docs/assets/phase5/` 里可查：

| 截图 | 证明什么 |
|---|---|
| `exe-01-home.png` | 安装形态下打开 exe 即进入首页，无需任何设置 |
| `exe-02-settings-sidecar.png` | **判据 (a)**：设置页渲染侧车实际端口 `127.0.0.1:64074` 与「已就绪」状态 |
| `exe-03-uploaded.png` | **判据 (c)**：上传 demo.apk 后进入项目详情 |
| `exe-04-analysis-running.png` | **判据 (c)**：**分析页**——五格阶段进度按**后端真实阶段事件**推进（角标原文「阶段推进：后端真实阶段事件」），实时日志如实记录 `running → completed · 0.9s`；橙色横幅点名未参与的后端（apktool / jadx `not installed or not on PATH`），「后端状态」卡逐个写 JADX ❌失败 / Apktool ❌失败 / Androguard ✓已完成 v4.1.4 |
| `exe-05-analysis-done.png` | 与 `exe-04` **逐字节相同**（见下）：抓屏时页面标题还停在「分析进行中」，内容已是完成态 |
| `exe-06-evidence.png` | **判据 (c)**：证据列表（**10 条**，含来源 locator 如 `androguard:classes.dex#com.example.demo.Crypto`） |
| `exe-07-reports.png` | **判据 (c)**：报告页，Markdown/JSON 导出可用 |
| `exe-08-export-clicked.png` | 点击导出后；与 `exe-07` 逐字节相同（见下） |
| `exe-09-evidence-sidecar-killed.png` | **判据 (d)**：杀掉侧车后如实显示可读错误（实际 baseUrl 原样出现在文案里） |
| `exe-10-settings-sidecar-exited.png` | **判据 (d)**：设置页显示侧车「已退出」而不是仍说运行中 |
| `exe-11-evidence-after-sidecar-restart.png` | 侧车换端口重启后，证据页**不刷新**即恢复 |
| `exe-12-findings-sidecar-killed.png` | **PR #21 那处陈旧文案的现场**：证据页错误态的**描述行**硬编码「请确认 DexAtlas 后端（`127.0.0.1:8618`）正在运行」，而下面 detail 行里的**真实端口是 59011**（侧车重启后的新端口）——描述与事实当场对不上 |

> **关于重复：** 这十二张里有**三对逐字节相同**（`exe-04`=`exe-05`、`exe-06`=`exe-11`、`exe-07`=`exe-08`），是抓屏时同一画面被存了两份。它们的**文件名与判据的对应关系仍然成立**（每一张都是那一判据的现场），所以照原样入库，未做去重。

**关键的六张：**

![判据 (a)：安装形态下侧车自动拉起，端口为侧车自己的 64074（设置页如实渲染）](../assets/phase5/exe-02-settings-sidecar.png)

![判据 (c)：分析页——阶段进度按后端真实阶段事件推进，橙色横幅点名未参与的后端](../assets/phase5/exe-04-analysis-running.png)

![判据 (c)：证据列表 10 条，每条带来源 locator](../assets/phase5/exe-06-evidence.png)

![判据 (c)：报告页，Markdown/JSON 导出可用](../assets/phase5/exe-07-reports.png)

![判据 (d)：杀侧车后如实显示可读错误，实际 baseUrl 原样出现在文案里（不是白屏）](../assets/phase5/exe-09-evidence-sidecar-killed.png)

![判据 (d)：侧车换端口重启后，证据页不刷新即恢复](../assets/phase5/exe-11-evidence-after-sidecar-restart.png)

### 5.1 结论：通过

二次验收 (a)–(d) 全通过，见 §2.3。首轮验收撞出的两处真实缺陷已由 PR #20（`4c86b2f`）修好；二次验收又撞出**三处陈旧文案**，已由 PR #21（`b21b028`）修好（见 §6.3）。

**这些截图还顺手证明了两件事：**

1. **W2 的阶段契约在打包形态下同样成立。** `exe-04` 的时间线角标原文是
   「阶段推进：**后端真实阶段事件**」——不是「前端模拟」，也不是「run 状态
   映射」。侧车这条链路读的是 stages 端点。
2. **「后端失败是一个值，不是异常」在真机上是对的。** 同一个画面里：分析照常
   完成并产出 10 条证据、页面顶部写「已完成」；同时橙色横幅逐条点名
   `apktool is not installed or not on PATH` 与 `jadx is not installed or not on
   PATH`，「后端状态」卡把 JADX / Apktool 标成「失败 · 未参与本次分析」，
   Androguard 标成「已完成 · 参与本次分析」。**结果不完整这件事，页面自己说。**

## 6. W3 / W4 — 备料项

### 6.1 W3 C12 仓库内备料：完成

| 判据 | 证据 | 结论 |
|---|---|---|
| 压缩稿 ≤5,000 字符且关键条款完整 | `docs/outreach/scope-ai-mcp-compact.md`（2,674 字节；验收与排除条款保留） | ✅ |
| 两个方案并排、取舍写明 | 同文件与 `docs/outreach/project-brief.md`、`publish-review.md` | ✅ |
| 核对表模板可直接填 | `docs/outreach/c12-field-check-template.md`（字段/实测长度/门限/结论） | ✅ |
| 真实渠道核实 | 按作者指示等待渠道与账号，本轮**不做** | 未做（按计划） |

### 6.2 W4 发版后运营清单：落盘，1 处口径出入

`docs/ops/post-release-checklist.md` 覆盖发布当天核对、发布后一周 triage 节奏、反馈渠道、指标与下一版触发条件。执行单的判据里有一句「不含任何需要作者账号的执行步骤」；清单本身也这么写，但表格第 1 行「核对 GitHub Release 页面」的账号需求标的是「作者（或已登录 CI）」，§4 又写「需作者账号查看」。**陈述与表格不一致**，属口径出入，不影响「只备料不执行」的结论；下一次维护清单时把这两处对齐即可。

### 6.3 二次验收撞出的三处陈旧文案：已修（PR #21）

打包 exe 二次验收在真机上撞出三处与实现不符的文案，PR #21 已全部修好：

| 位置 | 原写法 | 现写法 |
|---|---|---|
| `desktop/src/pages/FindingsPage.tsx:131` | 错误描述硬编码回退端口 `127.0.0.1:8618` | 取实际后端地址（`desktop/src/backendAddress.js:27` `backendAddress()`），端口不可知时显示「后端地址未知」 |
| `desktop/src/pages/Analysis.tsx`（后端状态脚注） | 「8618 为只读 workbench API，无 `/api/backends` 端点」（实测返回 **200**） | 改述 `/api/backends` 的语义：它只说明「装没装」，「这次分析实际用了哪个版本」仍取自 `tool_versions` |
| `desktop/src/pages/ReportsPage.tsx:112` | 「生成时间」显示 UTC 原始串 | 本地时区 + 一行 UTC 标注（`desktop/src/datetime.js:118` `timestampParts()`） |

> **PR #21 的状态：** 已于 2026-11-26 合入 main（合并提交 `59bb9c9`），本报告基线 `33e4ba9` 已包含它。
>
> **脚注那处有截图作证：** `docs/assets/phase5/exe-04-analysis-running.png` 的右栏底部就写着那句「8618 为只读 workbench API，无 `/api/backends` 端点；以上由最近分析轮次的 `tool_versions` 推断。」——而同一张截图左边的日志显示请求打的是侧车自己的端口。**文字与事实当场对不上**，这正是 PR #21 改的那一句。
>
> **描述行那处也有截图作证：** `docs/assets/phase5/exe-12-findings-sidecar-killed.png` 里，错误态的描述行硬编码「`127.0.0.1:8618`」，detail 行里的真实端口却是 `59011`。**同一屏上两行自相矛盾**——而读者若只看描述行，会以为前端在打 8618 回退端口，那正是首轮验收假阳性的同类陷阱。

## 7. 未覆盖与未验证（逐项）

本节分三块：**本轮关闭的七项**（连同它们的证据）、**走查带出并已修的一个后端缺陷**、以及**仍然开放的四项**。已关闭的项目不在「仍然开放」里。

### 7.1 本轮（2026-11-26 收尾批次）关闭的七项

| 原编号 | 项目 | 怎么关闭的 | 证据 |
|---|---|---|---|
| 2 | 打包 exe 在「装了 jadx + apktool」的配置下未跑 | 用 JADX 1.5.2 + Apktool 2.11.1 + Androguard 4.1.4 齐全的配置跑打包 exe：五个阶段全「已完成」，**12 条证据**、`missing_backends: []`、`complete: true`（缺后端那档实测 10 条） | [真机补测报告](phase5-machine-verification.md) §2 + 24 张截图 |
| 3 | MSI 安装路径未验证 | `msiexec /i … /passive` 退出码 **0**，装到 `C:\Program Files\DexAtlas Studio\`；装完启动应用，侧车起来、连上后端、跑出同样的 12 条证据。**前提要写清**：`/qn`（静默）装不上，退出码 1603——静默模式下 Windows Installer 不做凭据提升，是机制问题不是包的毛病 | 同上 §3 |
| 4 | 「强制结束 exe」（`taskkill /F`）时的孤儿后端未测 | 改由 Windows **作业对象**兜底：后端挂起创建 → 加入作业 → 恢复主线程，于是它自己拉出来的后代也继承作业身份；宿主一死，系统关闭作业句柄，整棵进程树随之终止。**同时补上一扇门**：`cargo test --lib` 进 CI（`desktop-rust` 作业，只跑在 Windows 上）——此前 24 个 Rust 测试**没有任何门禁在跑** | PR #25；新增回归测试摘掉 `KILL_ON_JOB_CLOSE` 即红；机器对照：修复前测试跑完留下 **9 个**孤儿 `cmd` 进程，修复后 **0 个** |
| 7 | failed / cancelled run 的时间线未实跑 | 在浏览器 + 真后端上走通：「取消」这条路径**存在**（红色取消按钮 → 确认 → `POST /cancel` → 管线在下一个检查点才停 → run 记 cancelled、项目记 failed）；「失败」分叉成三种界面结果（上传被拒 / 分析跑完却读到空 / 后端失败但分析完成） | [走查报告](phase5-failure-timeline.md) + 9 张截图。**边界**：走查在开发模式（vite + 浏览器）里做，**未在打包的 exe 里复验** |
| 9 | 文件内 locator 的「打开来源」仍走 `window.alert` | 改为在文件内**内联展示后端返回的源码**：真实路径、行数与字节数等可核对信息、可滚动代码块、截断时明示上限；无落点 locator 仍禁用且说明可见 | PR #24 |
| 10 | 角标正文夸大（只在悬停提示里说清） | 角标改成「阶段推进：后端阶段事件 + 前端映射」，并把「哪一格算推进到位」是前端推断这件事写进 title | 前端收尾批次（`desktop/src/stages.js`）；vitest 61 例 |
| 11 | run 完成后仍每 2s 轮询 | 三处轮询（项目状态 / runs 列表 / 阶段事件）统一走**唯一一份终态口径**（`completed` / `failed` / `cancelled`；未知状态按「不是终态」处理），进终态即清定时器 | 同上；vitest 61 例 + 跨语言回归 6 例 |

### 7.2 走查带出的一个后端缺陷（已修）

管线在「分析跑完却什么也没读到」时算出了 `FAILED`，却**只在 `COMPLETED` 时调 `publish_run`**——失败状态从来没落库，项目行留在 `running`，界面在分析结束 **4 分 44 秒**后仍显示「分析中」，首页列表也显示「◌ 进行中」。只有后端进程重启时的孤儿轮次对账才把它改成 failed，而那句话说的是「服务端进程在分析结束前就结束了」，对这一次的情况恰好说反了。

现在失败状态与失败原因都写进数据库；「读到空的 run 不发布、已发布快照保持原样」这条不变量**不变**（取消路径与异常路径的行为也不变）。

### 7.3 仍然开放的四项

1. **macOS / Linux —— 明确不纳入。** 执行单 §2.2 的范围只写了 Windows；本轮所有真机验收都在 Windows 11 上完成。Linux 侧只有 CI 的单元测试跑过，**没有打包产物的真机验证**。
2. **非 MSIX 容器下的启动 —— 未单独验证。** 二次验收的 exe 由 Claude 桌面应用的 MSIX 容器启动，配置目录落在虚拟化路径下（真实路径与虚拟化路径的 `backend.json` 逐字节相同，结论不依赖读的是哪一份）。
3. **MCP 面是否该暴露阶段工具 —— 未决。** `run_stages` 未注册为 MCP 工具（工具清单仍是 11 个），阶段事实只走 REST 与 workbench。这是设计取舍，不是缺陷，但**没有记录谁做的取舍**。
4. **W4 运营清单的账号口径 —— 1 处不一致。** §6.2 已写明位置，不影响「只备料不执行」的结论。

### 7.4 一项已知且如实标注的低危残留

**阶段格与后端阶段不是一一对应 —— 未拆格。** 前端五格是「采集/解析/索引/证据/报告」，后端五阶段是 `inspect / parse-apktool / index-androguard / decompile-jadx / publish`：「解析」格**合并了两个后端阶段**，「证据」格**在后端没有对应阶段**、状态是推断的。这两点写在角标的 `title` 提示里（`desktop/src/stages.js` 的 `EVIDENCE_SLOT_NOTE` 与 `PARSE_SLOT_NOTE`），角标正文现在也点明了「前端映射」这一层——**说法不再夸大，但格子没有拆**。

## 8. 判定与下一步

**可以宣布的：**

- Phase 5 的 W1（**安装形态**）、W2、W3、W4 已实现并合入 main；W1 的首轮验收失败项已由 PR #20 修好，二次真机验收 (a)–(d) 全通过；W2 的复测五条判据已全部有结论（⑤ 当时不通过，已由 PR #18 修正），完成态缺陷已由 PR #19 修好；契约活检覆盖 stages 路由（静态条数 55）；端到端走查的 P1/P3/P4 已分别由 PR #15/#17 修好；打包 exe 二次验收撞出的三处陈旧文案已由 PR #21 修好。
- **打包形态在完整后端配置下可用**：JADX + Apktool + Androguard 齐全时，打包 exe 跑出 12 条证据、`complete: true`（§7.1 第 2 项）。
- **MSI 安装路径可用**：`msiexec /i … /passive` 装得上、装完能启动能分析（§7.1 第 3 项）。
- **强杀宿主不留孤儿后端**：Windows 作业对象兜底，且这一层**进了 CI 门禁**（`desktop-rust` 作业，`cargo test --lib`，只跑在 Windows 上）——此前 24 个 Rust 测试没有任何门禁在跑（§7.1 第 4 项）。
- **失败与取消两条时间线真机走通**，「取消」这条路径确实存在（§7.1 第 7 项）。
- **界面不再有夸大与多余**：角标说明「后端阶段事件 + 前端映射」，run 进终态即停止轮询（§7.1 第 10、11 项）。
- **「前端时间模拟兜底」已删除**（2026-11-26 收尾）：模拟路径已删除，无 run 数据时五格如实显示状态未知，runs 请求失败时显示可读错误与重试入口。

**不能宣布的：**

- 不宣布「Phase 5 在 macOS/Linux 上可用」——执行单明确不纳入，未验证。
- 不宣布「阶段格与后端阶段一一对应」——五格没有拆开；现在只是**把这件事说准了**（§7.4）。
- 不宣布「失败的分析在所有路径下都会被记成失败」——空结果那条路已修（§7.2），但「非 MSIX 容器下的启动」仍未单独验证（§7.3 第 2 项）。

**仍然开放的验收项**（详见 §7.3 的四项）：平台覆盖（macOS/Linux）、非 MSIX 容器启动、MCP 面是否暴露阶段工具的取舍记录、W4 清单的账号口径。
**这些都不是挡住 Phase 5 的东西**——要么在执行单范围之外，要么是一处口径出入。

**接下来该做的是 Phase 6**，不是继续补 Phase 5 的边角：桌面端已经能装、能跑、能说清自己在做什么；剩下四项要么需要别的平台，要么需要一次决策记录。
