# Phase 4 M15 — 发布前本地评审

**日期：** 2026-11-23 · **性质：** 发布前本地评审（[发布规划 §5](phase4-release-plan.md)）
**基线：** `e5cb165`（Phase 4 M15 walkthrough；本地工作分支 `claude/youthful-clarke-db2263-wt`，与 `origin/main` 同 hash）。评审期间并行窗口在 README 双语、install.md、docs/reports/README.md、portfolio/、assets/、tech-talk 脚本上有未提交改动（其中 install.md 的两处改动恰好落实了 walkthrough F2/F3 的建议）；本评审的门禁与源码结论以已提交的 `e5cb165` 为准，他窗未提交内容只作交叉参考，不改变结论。
**范围：** 全量本地门禁、Phase 4 源码评审（M11–M15）、发布数字一致性、walkthrough 四项低危发现追踪。**未跑、未盯 GitHub CI**（用户明确 CI 需另行发话）。

> 纪律声明：发现只记录、不修；未触碰 `README.md` / `README.zh-CN.md`、`docs/portfolio/`、`docs/assets/` 与执行报告数字标记。所有门禁输出落在本仓库 `.scratch/release-review-logs/`（不入库）。

## 0. 结论摘要

**13 项本地门禁全部 PASS**（含完整 pytest：1807 passed / 1 skipped，唯一 skip 为 Windows 平台设计内跳过）；Phase 4 源码评审未见正确性缺陷或公共契约破坏（前端独立子评审的 5 项发现经逐项复核，2 项不成立、2 项低危非阻断、1 项可接受，唯一坐实的上传屏 `failed` 文案问题系 v1.0.0 既有行为，登记为 R-5）；发布数字四处口径一致（1808 total / 1807 passed / 1 skipped / 93.3%）；walkthrough 4 项低危发现均有归属，无阻断项。**建议：本地可发布（条件：按流程合入工作分支、用户发话后跑 CI）。**

## 1. 本地门禁逐项结果

| # | 门禁 | 结论 | 证据（命令 / 摘要） |
|---|---|---|---|
| 1 | 完整 pytest（带后端与 fixtures） | PASS | **1807 passed, 1 skipped in 545.05s (0:09:05)**。唯一 skip：POSIX launcher 测试（`tests/test_backend_timeout.py`，在 Windows 跳过，平台镜像的 Windows batch 测试已原生执行）——平台设计内跳过，非缺工具；skip 数与执行报告 `suite.skipped 1` 一致 |
| 2 | `ruff check .` | PASS | All checks passed! |
| 3 | `ruff format --check .` | PASS | 381 files already formatted |
| 4 | `mypy` | PASS | Success: no issues found in 69 source files |
| 5 | `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | PASS | 无输出，exit 0 |
| 6 | `check-doc-citations.py` | PASS | 771 citations；drifted 0；unresolved 0；values not matching 0。（2026-11-24 追记：文档事实错误修复后引用数增至 775，复跑仍 drifted 0 / unresolved 0 / values not matching 0，结论不变。） |
| 7 | `check-version-claims.py --base auto` | PASS | exit 0 |
| 8 | `check-unguarded-numbers.py` | PASS | PASS 21 watched statements agree with the tree |
| 9 | `check-release-numbers.py` | PASS（附记录） | exit 0；check-release-numbers --strict 亦 exit 0；有 2 处 `coverage.pct not written`（见发现 R-1）与 v1.0.0 release body 缺失提示（见发现 R-2） |
| 10 | `check-platform-gates.py` | PASS | PASS 13 CI jobs are declared, 4 platform-dependent tests are declared |
| 11 | `check-gate-coverage.py` | PASS | All 11 gates are run by something |
| 12 | `make-social-preview.py --check` | PASS | 所有 figure / sidecar / version / license 项 PASS |
| 13 | `git diff --check` | PASS | 无输出，exit 0 |

全部命令以 `uv run --no-sync ...` 运行；当前工作分支自有 `.venv`。`ffmpeg` 可用（`/e/MATLAB/Octave/Octave-11.3.0/mingw64/bin/ffmpeg`），Java 后端与第三方 fixtures 已就位（`DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 指向 `.scratch/backends/`），满足完整测量前置。

## 2. Phase 4 源码评审

逐提交审阅 M11–M15 的源码 diff（`e5cb165~12..e5cb165`），重点为任务单点名的 `App.tsx` / `components.tsx` / `styles.css`、`agent/state.py`、`scripts/check-doc-citations.py` 与 walkthrough/release-plan 文档。

| 提交 | 主题 | 评审结论 |
|---|---|---|
| `e88d630` / `ff4a12a` / `47bb236` | M12 样式 token 化 + 状态截图 + workbench-ui.md 设计规范 | 视觉零变化承诺由基线截图对照支撑；设计规范文档被 `check-doc-citations.py` 纳入收集（见 `6dbc9a3` 前的 `45384c2` 系列），与「文档引用可复核」纪律一致 |
| `0446b13` | 84.8 秒端到端 demo 重录（替换 8.8 秒旧素材） | 真实录屏 + scripted agent 披露清楚；顺带修复 React 崩溃：agent 报告 provenance 为对象数组而展示代码按字符串读（React #31 整树卸载，真实模型报告同样触发），`provenanceRef` 兼容两种形态取 locator——修复正确且必要 |
| `45384c2` | M13 共享基座组件（components.tsx +419 行）与六态接入 | 组件只经 props 取数、不自取数，符合 workbench-ui.md §4 约束；六态（loading/empty/error/partial/running/success）接入有 22 张真实运行截图佐证 |
| `22c0621` | M13 任务 B agent 成功流实测 | 截图均为真实运行产物；README 对 scripted provider 的披露口径与之一致 |
| `6dbc9a3` | M14 任务 C TaskStore Windows 并发写加固 | **正确且必要**。共享 `<id>.json.tmp` 改为每写者唯一 tmp 名（pid+对象 id+monotonic ns），`os.replace` 带 2s 上限指数退避；`load` 对 `PermissionError` 短重试、`FileNotFoundError` 仍返回 None；重试耗尽清理 tmp 再抛。回归测试 `test_concurrent_writers_do_not_lose_a_state`（2 写者×25 save + 2 读者并发 load）在旧实现下 102 个 PermissionError、新实现全过——满足「回归测试在旧实现上变红」的硬规矩；不改公共契约 |
| `acb9f0b` | M14 任务 A 可访问性补齐 | StatusBadge 增加非颜色符号（✓/…/✕/•），色盲可辨；Modal 焦点管理升级为 `useModalFocus`：打开时焦点入面板（首个可聚焦元素或面板自身 `tabindex=-1`），Tab/Shift+Tab 在面板内循环（焦点陷阱），关闭时焦点回到触发元素；`focusableIn` 过滤 disabled 与 `offsetParent === null`。实现与 WAI-ARIA dialog 惯例相符 |
| `dd76bd0` | 上传键盘路径修复 | `file input` 从受控 `value={inputValue}` 改为 `hasFile` 布尔——受控 value 会使键盘/程序化选择文件后 submit 按钮不启用的路径失效；修复方式正确且最小 |
| `44c21c3` / `a498849` | M14 验收截图与测量刷新到 1808 | 截图入 `docs/assets/phase4-m14/`；测量由脚本在完整运行后写入（见 §3） |
| `337e7d5` | M15 发布规划 | 纯规划文档，未宣称未执行步骤已通过，符合「证据优先」 |
| `e5cb165` | M15 独立 walkthrough 报告 | 结论「通过 + 4 低危」有逐步命令级记录支撑（见 §4） |
| `scripts/check-doc-citations.py` | 新增 `workbench-ui.md` 进收集清单 | 使新增设计文档同样受引用检查约束，方向正确 |

**回归风险与遗留：** 未见正确性缺陷或契约破坏。前端改动集中在展示层与交互层，公共契约（REST/MCP/CLI/退出码）在 diff 范围内未变，`check-contract-records` / `verify-public-contracts` 仍 PASS。walkthrough F2/F3 两处文档可用性小问题留待后续（见 §4）。

### 2.1 前端深度评审（独立子评审 + 逐项人工复核）

在 §2 逐 diff 评审之外，另以只读子评审对 `src/dexatlas/workbench/web/` 的 Phase 4 diff 做了一轮独立检查，返回 5 项发现；以下为逐项人工复核结论（复核基于当前工作树源码，非转述子评审）：

| # | 子评审发现（原判级） | 复核结论 | 依据 |
|---|---|---|---|
| 1 | 项目页把带 errors 的分析当完整展示，无 partial 横幅（High） | **不成立** | `Completeness.complete = not absent and not truncated and not project.errors`（`src/dexatlas/mcp/tools/projects.py:103`）：errors 非空时 `complete` 必为 false，项目页走 gaps 分支把每条 error 红字列出（`src/dexatlas/workbench/web/src/App.tsx:535`），「every step of the analysis finished」仅在 `complete` 为真时渲染（`src/dexatlas/workbench/web/src/App.tsx:522`）——子评审描述的场景自相矛盾。errors 不触发顶部 PartialBanner 与 UI 规范一致（`docs/architecture/workbench-ui.md` §3 的 partial 触发条件为 missing_backends/truncated） |
| 2 | 上传轮询把项目 `failed` 终态并入成功分支，绿 ✓ 显示「analysis finished」（High） | **成立，但系 Phase 4 之前既有行为** | 轮询终止条件对 `completed` 与 `failed` 同样进入 `done`（`src/dexatlas/workbench/web/src/App.tsx:228`），该行为来自 `903195c`（2026-11-14，已含于 v1.0.0），非本评审范围引入；失败本身在项目页以红 ✕ 徽章与 completeness errors 明示，误导限于上传屏瞬时文案。登记为发现 R-5（见 §5），不阻断发布 |
| 3 | Dialog/Drawer 键盘用户无法关闭（Medium） | **不成立** | 面板头部有 `aria-label="close"` 的 ✕ 按钮，Escape 关闭路径独立存在（`useEscapeCloses`）；overlay 点击是鼠标的额外通道，键盘路径并未缺失 |
| 4 | Tabs 缺 aria-controls / tabpanel / roving tabIndex（Medium） | **成立，潜伏项** | 该组件当前未被任何页面使用；将来采用时会带入不完整的 tab 语义。登记为低危备忘，不阻断 |
| 5 | `useModalFocus` 在 window 上全局捕获 Tab（Low） | **成立，可接受** | 模态打开期间全局捕获 Tab 是常见的简单焦点陷阱实现，当前单页面板下行为正确；未来若出现「模态外保留可聚焦区域」的需求，应改为面板边界陷阱 |

小结：5 项中 2 项不成立、2 项成立但非阻断（1 项既有、1 项潜伏）、1 项成立可接受。**未发现 Phase 4 diff 引入的正确性缺陷**；子评审坐实的既有问题已登记为 R-5。

## 3. 发布数字一致性

**口径核对（全部一致，PASS）：**

| 数字 | 执行报告 figure | README 徽章（双语） | status.md | portfolio.md | social-preview --check |
|---|---|---|---|---|---|
| tests.total 1808（1659 快 + 149 集成） | ✅ | —（徽章用 passing 数） | ✅ | ✅ | PASS |
| suite.passed 1807 / skipped 1 / xfailed 0 | ✅ | ✅ 1807 passing | — | — | PASS |
| coverage 93.3%（7323/7852） | ✅ | ✅ 93.3% | ✅ | ✅ | PASS |
| 版本 / license | — | — | ✅ | — | PASS |

- `make-social-preview.py --check`：报告侧与卡片侧所有 figure、sidecar、version、license 逐项 PASS。
- `check-release-numbers.py`（普通与 `--strict`）：mismatches 0。输出里的两条 `coverage.pct -- not written (report: 93.3)` 指 `docs/how-to-verify.md` / `docs/how-to-verify.zh-CN.md` 本来就未手写该数字，脚本按设计提示，非缺陷。
- `missing document: docs/reports/v1.0.0-github-release-body.md`：脚本对可选发布正文的设计内提示（stderr 提示后继续），已有 `docs/releases/v1.0.0.md` 与已发布 GitHub body 兜底，不构成失败。
- v1.0.0 历史段（1795/1793/93.3%，7157/7671）与当前树（1808/1807/93.3%，7323/7852）各自成段、互不混淆，符合「不混排」纪律。

## 4. walkthrough 四项低危发现追踪

来源：[phase4-walkthrough.md](phase4-walkthrough.md)（结论「通过，4 项低危发现，均不阻断链路」）。

| 编号 | 严重度 | 位置 | 摘要 | 本次评审处理 |
|---|---|---|---|---|
| F1 | 信息 | 分支状态 | `main`@`22c0621` 未含工作分支 M14 两修复（TaskStore 加固、a11y 补齐） | 已确认：本评审基线 `e5cb165` 已包含 `6dbc9a3`、`acb9f0b`；发布前随分支合入即消除，不阻断 |
| F2 | 低（文档可用性） | `scripts/install-backends.sh` ↔ `docs/install.md` | install.md 称脚本「prints the two lines」，脚本实际不打印 export 两行 | 归因核实：install.md 的如实表述「脚本只打印版本行、不打印 export」并非评审期内新改，而是由提交 `9ab7b43`（2026-11-18）早已落地（早于 walkthrough 的 2026-11-23）；walkthrough §1.4 记录的「prints the two lines」是当时所见的旧状态。结论方向不变：文档侧矛盾已消除（脚本侧打印 export 仍可作为后续改进）；不阻断发布 |
| F3 | 低（文档口径） | `docs/install.md` API 表 | 表列 REST API 路径，Workbench 实为另一套 `/api/` 子集；README 未做相同承诺，不构成冲突 | 评审期内发现他窗已在 API 表前加注「REST API 契约 / Workbench 另有 `/api/...` 子集并指路 workbench.md」；不阻断发布 |
| F4 | 低（Windows 首启体验） | Workbench 端口 8618 | 端口被占时报错清晰并提示 `--port`，README 未写换端口 | 环境体验点，报错已可自救；不修，不阻断 |

结论：4 项均已有明确归属（1 项随合入自动解决、2 项低危文档改进留后续、1 项环境点），无发布阻断项。

## 5. 发现清单

（评审过程中新发现，均只记录）

- **R-1（信息，按设计）**：`check-release-numbers.py` 对 `docs/how-to-verify{,.zh-CN}.md` 报 `coverage.pct not written (report: 93.3)`——这两份文档未手写覆盖率数字，脚本设计如此；非缺陷。
- **R-2（信息，按设计）**：`check-release-numbers.py` 对 `docs/reports/v1.0.0-github-release-body.md` 报 `missing document`——该可选文件不存在，脚本 stderr 提示后继续，已有 releases/v1.0.0.md 与 GitHub 已发布正文兜底；非缺陷。
- **R-3（流程注意）**：`check-release-numbers.py --strict` 在发布说明就绪后才应作为发布门；当前普通模式已 PASS，strict 亦 PASS，但若后续新增 release body 文件需重跑。
- **R-4（信息，证据补强）**：本次完整 pytest 实测 1807 passed / 1 skipped（545.05s），与执行报告 `<!--fig:suite.passed-->1807`、`<!--fig:suite.skipped-->1` 标记一致（见 `docs/reports/phase1-execution-report.md:901`），实测闭环了报告数字与当前树的一致性。
- **R-5（低危，既有行为，建议后续修）**：Workbench 上传屏的轮询把项目 `failed` 终态并入成功分支——`status.project.status === "completed" || status.project.status === "failed"` 都进入 `done`，绿 ✓ 显示「analysis finished: <name>」并提供「open the project」入口（`src/dexatlas/workbench/web/src/App.tsx:228`、`src/dexatlas/workbench/web/src/App.tsx:314`）。该行为由 `903195c`（2026-11-14，已含于 v1.0.0）引入，**不是 Phase 4 改动**；失败项目在跳转后的项目页有红 ✕ 徽章与 completeness errors 明示，故误导仅限上传屏的瞬时文案。建议后续把 `failed` 分支改走 `UploadPhase["failed"]`；不阻断本次发布。
- **R-6（低危备忘）**：`Tabs` 组件（`src/dexatlas/workbench/web/src/components.tsx:277`）缺 `aria-controls`/关联 tabpanel/roving tabIndex；当前未被任何页面使用，属潜伏项，采用前应补全 tab 模式。

## 6. 可发布建议

**建议：本地可发布。** 依据：

1. 13 项本地门禁全部 PASS，其中完整 pytest（带 JADX/Apktool 后端与第三方 fixtures）1807 passed / 1 skipped，skip 为平台镜像设计内跳过，与执行报告口径一致。
2. Phase 4 全部源码改动（M11–M15）逐 diff 评审 + 前端独立子评审复核，无正确性缺陷、无公共契约变化、回归测试满足「旧实现变红」纪律。
3. 发布数字（测试数/覆盖率）在执行报告、README 双语、status.md、portfolio.md、social-preview 卡之间完全一致，且全部由脚本生成，本次实测闭环。
4. walkthrough 4 项低危发现均不阻断：F1 随分支合入解决，F2/F3 评审期内他窗已落实，F4 为环境体验点。
5. 新登记的 R-5（上传屏 failed 文案，既有行为）与 R-6（Tabs 潜伏 a11y）均为低危、非阻断，建议随下一轮前端维护处理。

**发布前置（非本次执行）：** 按 [phase4-release-plan.md](phase4-release-plan.md) §5 完成工作分支合入 `main`；CI 由用户发话后运行。
