# 全库过期数字扫描（只读）

**本窗口为只读扫描：未修改任何文件（除新增本报告），未运行任何项目测量。**
未运行 `pytest` / `pytest --cov` / `coverage`，未运行 `uv sync`，未运行
`scripts/refresh-report-figures.py`；未向 `E:\Dexatlas` 共享树写入任何内容
（只读取；`git status` 在共享树里除另一会话的 `docs/reports/changelog-vs-release-notes.md`
外无变化）。

核对行号用的是 `Read` / `Grep` / `git show` / `git ls-tree`。另外调用了三样
**只读**的东西复算数字，均不写文件：`scripts/check-version-claims.py --base auto`
（版本声明核对）、`scripts/check-doc-citations.py`（引用核对）、以及用共享树自己的
`.venv` 导入 `benchmarks.tasks` / `benchmarks.comparison.run` 后直接调用其内部
函数复算题集分布与失败成因（`run.py::_failure_causes`、`run.py::_run_from_document`）。

- **扫描基准**：`E:\Dexatlas` 共享树 `8f9ddca`（"v1.0.0 发版：版本号 1.0.0、
  CHANGELOG 1.0.0 条目、完整重测量与文档状态同步"），tag `v1.0.0` 已存在。
- **扫描范围**：`docs/` 全部子目录、`README.md`、`README.zh-CN.md`、`CHANGELOG.md`。
- **上一轮已审过的材料**（M10 验收包、Upwork/外联素材、两份发布文本）本次仍
  一并扫了，但只报告**仍然存在**的问题；已修好的不再列出。

> **扫描期间的仓库变动**：本扫描开始时共享树还是发版前的未提交状态
> （`599ab67` + 工作区改动），中途发版提交 `8f9ddca` 落地并打了 `v1.0.0` tag。
> 下表的行号与结论**以 `8f9ddca` 为准**；发版提交没有修掉下表中的任何一条。

---

## 0. 权威基线（先核到出处，再用来判文档）

| 事实 | 值 | 出处 |
|---|---|---|
| MCP 只读工具数 | **11** | `src/dexatlas/mcp/server.py` 11 个 `@server.tool`（105/125/140/153/178/207/245/273/300/313/328），第 11 个是 `find_resource_declarations` |
| CLI 子命令 | **13** | `src/dexatlas/cli/main.py` 13 个 `@app.command()` |
| REST 端点 | **23** | `src/dexatlas/api/app.py` 23 条路由 |
| 活检 | 契约表写 **46/46** = 26 REST + 6 MCP + 14 CLI（2026-11-15 快照）；**脚本现为 49 项**（28 + 6 + 15） | `docs/architecture/public-contracts.md` §7；`scripts/verify-public-contracts.py`（见 §2 F 组） |
| JSON 报告顶层键 | **10**（`schema_version=3`） | `src/dexatlas/reports/json_report.py`；`docs/case-studies/attachments/demo-report.json` 顶层 10 键 |
| CLI 退出码 | **0/1/2/3/4/5/6**（6 = `EXIT_NO_INDEX`，v1.0.0 新增） | `src/dexatlas/cli/main.py:94-135` |
| 工作区 schema | **7** | `src/dexatlas/core/storage.py:44` |
| 包版本 | **1.0.0** | `src/dexatlas/__init__.py:11` |
| 后端版本 | JADX **1.5.2** / Apktool **2.11.1** / androguard 4.1.4 | `scripts/install-backends.sh:20-21` |
| APK 样例 | **5** | `examples/{demo,multidex,obfuscated,strings,wide}-app/*.apk` |
| case study | **3** | `docs/case-studies/README.md:3`「Three complete walkthroughs」 |
| 证据包 zip | **3** | `docs/case-studies/attachments/*.zip` |

**M6 基准数**（各自可追到源报告）：首测 24/60 = 40.0%（逐轮 45%/40%/35%，A 24/60、
B 18/60，token 853,103）；retest3 逐轮 **17/15/17** = 49/60（1,080,116 tokens）；
retest4 逐轮 **15/16/18** = 49/60（1,182,356 tokens）；窄验证 4/6（410,256，
不完整）→ 2/6（420,826）→ 3/6（380,881）；层级 0 = 20/20；层级 1 scripted
A 4/20、B 4/20、DexAtlas 1/20。**全库未发现把 17/15/17 与 15/16/18 挂反的地方。**

---

## 1. 已跳过（正在被发版测量重写）

按任务要求，**测试数与覆盖率一律跳过**，理由：**正在刷新**。

- 套件数、一方代码覆盖率百分比（以及 README / README.zh-CN 的徽章、
  `docs/status.md` 的 `<!--fig:-->` 标记、`docs/reports/phase1-execution-report.md`）。
  扫描期间重测量已落地：`8f9ddca` 写入 1588 个测试、一方代码覆盖率 93.3%
  （7117/7631 行）。这些数字本轮不判对错。
- `docs/reports/phase1-execution-report.md`、`README.md`/`README.zh-CN.md` 的
  徽章、`docs/status.md` 的图标记：本轮一律不作为发现列出。

---

## 2. 必须改的 51 处

严重度：**高** = 对外承诺与仓库事实直接冲突；**中** = 读者按它会得到错误结论；
**低** = 不影响结论但与仓库不符。

### A 组 —— 退出码 6 没有同步进全部落盘材料（6 处）

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/reports/m10-selfcheck.md:44` | `退出码 0–5：契约表 = CLI 常量（含隐式成功 0）` | 与脚本当前口径一致：三处（契约表 / CLI 常量 / 契约测试 `EXPECTED_EXIT_CODES`）互相印证，覆盖 **0–6** | `scripts/m10_selfcheck.py:417-451`：F1 现在**不再硬编码**期望，从 `EXPECTED_EXIT_CODES` 读；其 docstring 明写「a stale copy would fail a correct tree (as it did when exit code 6 landed and this set still read 0–5)」 | 高 |
| `docs/reports/m10-selfcheck.md:94` | `F1/F3/F4/D3/D1/D5/E1/E5 的静态契约核对全部一致（退出码 0–5、…）` | 退出码 **0–6** | 同上；另 `docs/status.md:137` 明写「退出码 6 落地后 F1 期望滞后已修复并带回归测试」，`CHANGELOG.md:249-255` 记了同一次修复 | 高 |
| `CHANGELOG.md:345-346` | v1.0.0 段：「CLI 全部 13 个子命令与退出码语义（0 成功 / 1 空答案 / 2 请求错误 / 3 分析失败 / 4 重载歧义 / **5 截断**）」 | 退出码集合补上 **6 跑完但无可用的代码索引** | 同一 `[1.0.0]` 段 `CHANGELOG.md:129` 已写「公共契约变更：新增退出码 6（`EXIT_NO_INDEX`）」；`src/dexatlas/cli/main.py:135` `EXIT_NO_INDEX = 6` | 高 |
| `docs/architecture/public-contracts.md:394-412`（§7.3 CLI 退出码实测） | 14 行活检表只覆盖退出码 0/1/2/3/4/5 | §1.2 的退出码表已有 **7 行**，活检表缺退出码 6 的一行 | `scripts/verify-public-contracts.py:571` 现在**有** `check("an analysis with no index exits 6", result.exit_code == 6, …)`（`1f6ef05` 引入）；表里的 14 行没有对应它。*注：14/14 这个数在 2026-11-15 当天是真的，要修的是补一行并重跑，不是改 14/14*。配套的分母问题见 §2 F 组 | 低 |
| `docs/releases/v0.2.0.md:369-374` | 「**A truncated run exits 0.** …the CLI's exit code is still 0」+「*(Fixed after this release: such a run now exits with the new code 5 — see the [Unreleased] section of the changelog.)*」 | v0.2.0 **已经**带退出码 5；该条不再是 v0.2.0 的已知限制；「见 [Unreleased] 段」的指针已失效 | `git show v0.2.0:src/dexatlas/cli/main.py` → `EXIT_TRUNCATED = 5`（v0.2.0 tag 内）；该改动记在 `CHANGELOG.md` 的 `[0.2.0]` 段（`:767`），`[Unreleased]` 段已在 `8f9ddca` 改题为 `[1.0.0]` | 中 |
| `docs/reports/v1.0.0-release-checklist.md:220-222` | 「## Upgrading from v0.2.0」段：「`analyze` now returns **exit code 5** when a step was truncated (was 0); 0/1/2/3/4 meanings unchanged」 | v0.2.0 → v1.0.0 新增的是**退出码 6**；5 早已随 v0.2.0 发布 | 同文件 `:212-214` 已正确写 exit code 6；已发布的 `docs/releases/v1.0.0.md:119` 写「exit 5 (`EXIT_TRUNCATED`) already shipped there」 | 中 |

### B 组 —— MCP 工具数 11 没有同步进全部文档（4 处）

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/architecture/diagram.md:26` | `│   10 read-only tools    │` | `11 read-only tools` | `src/dexatlas/mcp/server.py` 11 个 `@server.tool`；`docs/architecture/public-contracts.md:207-217` 工具清单 11 行 | 高 |
| `docs/architecture/README.md:258-260` | 「…and nothing else. **Ten** tools: `list_projects`, `get_project_status`, `get_manifest`, `search_symbols`, `get_class_source`, `get_method_source`, `find_callers`, `find_callees`, `get_evidence` and `resolve_locator`」 | **Eleven** tools，补 `find_resource_declarations` | 同上；`docs/releases/v1.0.0.md:127`「MCP tools: 10 → 11」 | 高 |
| `CHANGELOG.md:347` | v1.0.0 段：「…MCP **十个只读工具**的参数与返回形状…」 | **十一个** | 同一 `[1.0.0]` 段 `CHANGELOG.md:327` 已写「**公共契约变更：MCP 工具从十个增至十一个**」——同一段里两个数字 | 高 |
| `docs/reports/v1.0.0-release-checklist.md:60` | 「- [ ] **MCP 10 个只读工具**：…」并只列 10 个工具名 | **11** 个，第 11 个 `find_resource_declarations` | §2 标题是「公共契约核对项（**v1.0.0 要冻结的契约面**）」，而 v1.0.0 实际冻结了 11 个；同节 `:47`「CLI 13 个子命令」、`:55`「REST 23 个端点」都是对的 | 中 |

### C 组 —— 发版已落地为 1.0.0，文档仍写 0.2.0（3 处）

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/architecture/public-contracts.md:327` | 「版本号唯一来源是 `src/dexatlas/__init__.py:11` 的 `__version__`（**当前 `0.2.0`**）」 | （当前 `1.0.0`） | `src/dexatlas/__init__.py:11` = `__version__ = "1.0.0"`；同文第 8 行自述「本表描述的是**当前**契约」。`scripts/check-version-claims.py` 不覆盖这一句（实测 `findings: 3` 全是覆盖率/徽章类） | 高 |
| `docs/architecture/diagram.md:4` | 「drawn from the tree as it stands (**`v0.2.0`**, plus the workbench screens that shipped with it)」 | `v1.0.0` | `git tag` → `v1.0.0`；`src/dexatlas/__init__.py:11` = 1.0.0。*注：句子里的 "as it stands" 是现在时* | 中 |
| `docs/case-studies/api-integration.md:80` | `GET /health` 的示例输出 `{"status":"ok","version":"0.2.0",…}` | `"version":"1.0.0"` | `src/dexatlas/api/app.py` 的 `/health` 回报 `version=__version__`；`__init__.py:11` = 1.0.0。上下文「`GET /health` answers first」无日期，属现在时 | 中 |

### D 组 —— `docs/status.md` 的「真模型对照」段是**上一轮**测量（7 处）

这一组最系统：`status.md` 同一页里，§5 退出标准表（`:284-285`）已经是**新**数字，
而上面的叙述段（`:263-274`）还是**旧**数字，两处自相矛盾。旧数字逐字来自
`82523d0` 时的 `comparison-real` trace（本次已从 git 取回旧 trace 复算核对）。

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/status.md:267` | 「本次正确率 A **27.2%** / B 22.8% / DexAtlas agent **17.4%**」 | A **30.4%** / B 22.8% / DexAtlas **19.6%** | `docs/benchmarks/comparison-real.md:21`；`docs/reports/phase3-baseline.md:25` 也写「real：30.4/22.8/19.6」。旧值出自 `git show 82523d0:docs/benchmarks/comparison-real.md:21` | 高 |
| `docs/status.md:268` | 「无支撑断言率 100% / 100% / **2.8%**」 | DexAtlas **4.4%** | `comparison-real.md:23`；同页 `status.md:285` 已写 4.4% | 高 |
| `docs/status.md:268` | 「工具调用成功率 100% / 100% / **99.0%**」 | DexAtlas **98.9%** | `comparison-real.md:25`；同页 `status.md:284` 已写 98.9% | 高 |
| `docs/status.md:271` | 「agent 正确率低的主因是模型反复请求工具直到预算耗尽（**14 题**）」 | **15 题** | `comparison-real.md:45`「DexAtlas \| ran out of tool calls \| 15」。旧值出自 `82523d0` 的 14 | 中 |
| `docs/status.md:273` | 「unanswerable 那一类反而是 agent 最好（**12/13**，A **9/13**、B 8/13）」 | agent **11/13**，A **10/13**，B 8/13 | 用仓库自己的 trace 复算（`expects_absence` 的 13 道题）：当前 `comparison-real-traces.json` → DexAtlas 11/13、A 10/13、B 8/13；旧 trace（`git show 82523d0:docs/benchmarks/comparison-real-traces.json`）→ 12/13、9/13、8/13 | 中 |
| `docs/status.md:298` | 「agent 正确率 19.6% → 22.8%（**+3.2 个百分点**，21/92）」 | **+3.3 pp** | `docs/benchmarks/comparison-stronger.md:66`「22.8% vs 19.6% (+3.3 pp)」。21/92 = 22.83%、18/92 = 19.57%，差 3.26 pp；+3.2 是拿四舍五入后的数手减出来的 | 低 |
| `docs/status.md:302` | 「且 **72 题**仍撞在 24 轮的循环上限上」 | **61 题** | `docs/benchmarks/comparison-stronger.md:91`「DexAtlas \| ran out of iterations \| 61」；用仓库自己的 `benchmarks/comparison/run.py::_failure_causes` 对 `comparison-stronger-traces.json` 复算也是 61 | 中 |

### E 组 —— 其他与仓库不符的数字与说法（21 处）

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/install.md:97-98` | `dexatlas backends` 示例输出：`jadx 1.5.6` / `apktool 3.0.3` | `1.5.2` / `2.11.1` | `scripts/install-backends.sh:20-21`（`JADX_VERSION=1.5.2`、`APKTOOL_VERSION=2.11.1`）；同文 `:112`、`:117` 装的就是 2.11.1；`docs/case-studies/README.md:45`、`docs/analysis-provenance.md:318-322` 同为 1.5.2 / 2.11.1。`docs/install.md:3-4` 自称「output is what that command actually printed」 | 高 |
| `docs/install.md:154` | 「the three [case studies] run on **two of them**」 | **three of them**（demo-app、obfuscated-app、multidex-app） | `docs/case-studies/README.md:29-31` 的三行分别用这三个样本 | 中 |
| `docs/install.md:314-331` | REST 端点表 16 行 | **23** 个端点（缺 `/projects/{id}/runs`、`/projects/{id}/runs/{run_id}`、`POST /projects/{id}/cancel`、`GET /uploads`、`DELETE /uploads/{sha256}`、`POST /uploads/cleanup`、`/projects/{id}/resource-references`） | `src/dexatlas/api/app.py` 23 条路由；`docs/architecture/public-contracts.md` §2 的 23 行表 | 中 |
| `docs/architecture/analysis-runs.md:139` | 「## The schema / **Schema version 4** adds: `analysis_runs` / `projects.published_run_id`」 | 工作区 schema 现为 **7** | `src/dexatlas/core/storage.py:44` `SCHEMA_VERSION = 7`。该节用现在时描述「The schema」 | 中 |
| `docs/analysis-provenance.md:315` | `"evidence_count": 10` | `11` | `docs/case-studies/attachments/demo-report.json` → `project.evidence_count = 11`（E-0001…E-0011）；`attachments/demo-report.md` 实有 11 行证据 | 中 |
| `docs/analysis-provenance.md:395` | §4.4 表 demo.apk 行：证据 = **10** | **11** | 同上 | 中 |
| `docs/analysis-provenance.md:399` | §4.4 表 obfuscated.apk 行：证据 = **7** | **8** | `docs/case-studies/attachments/obfuscated-report.json` → `evidence_count = 8`（E-0001…E-0008） | 中 |
| `docs/analysis-provenance.md:408` | 「五个样本、**38 条证据**」 | **40 条**（按已证伪的 demo、obfuscated 两行各 +1，其余三行未变计） | 同上两行；表内其余三行（multidex 8 / wide 9 / strings 4）无对应附件，无法复算，故此处只给出下限 40 | 中 |
| `docs/architecture/README.md:403` | 「`mcp/` and `agent/` have landed. **`web/` has not.**」 | web/ 已落地 | `src/dexatlas/workbench/web/`（`src/`、`package.json`、`index.html`）；`pyproject.toml` 的 `dexatlas-workbench` 入口 | 中 |
| `docs/outreach/project-brief.md:68-69` | 「A CLI (`dexatlas analyze / manifest / search / source / **xref / evidence / report**`)」 | 实际 13 个子命令：`version, backends, analyze, projects, classes, methods, source, resources, resrefs, search, export, manifest, xrefs`——没有 `xref`（是 `xrefs`）、没有 `evidence`、没有 `report`（报告走 `analyze --json/--html`，证据包走 `export`） | `src/dexatlas/cli/main.py` 的 13 个 `@app.command()`；`docs/architecture/public-contracts.md` §1.1 | 中 |
| `docs/portfolio.md:108-110` | 「**Two** complete worked analyses — a walkthrough of the demo app … and an obfuscated-sample study」 | **三篇** case study | `docs/case-studies/README.md:3`「Three complete walkthroughs」；`docs/outreach/publish-review.md` §2 第 7 条已把 `project-brief.md` 的「two end-to-end case studies」改成「three complete case studies」，同一批材料里 portfolio 漏改 | 中 |
| `docs/case-studies/README.md:33` | 「**Both** APK samples are **first-party**」 | 三份研究用的是**三个**样本（demo-app / obfuscated-app / multidex-app） | 同文 `:29-31` 的表；`examples/` 下共 5 个样本 | 低 |
| `docs/case-studies/api-integration.md:205-207` | JSON 报告顶层键列举 7 个（`schema_version, project, run, tools, manifest, evidence, summary`） | **10** 个（另加 `generated_at`、`latest_attempt_status`、`errors`） | `src/dexatlas/reports/json_report.py`；`attachments/demo-report.json` 顶层 10 键；`docs/architecture/public-contracts.md` §5.1 | 低 |
| `docs/proposals/exit-code-partial-read.md:3` | 「状态：**提案，未实施**」 | 已实施（v1.0.0 新增退出码 6） | `CHANGELOG.md:129-134`；`src/dexatlas/cli/main.py:135`；`docs/architecture/public-contracts.md:64` 明写「由提案 … 批准实施（方案 A）」 | 低 |
| `docs/architecture/public-contracts.md:416` | §8 前言「本节记录当前版本**已知但未修复**的契约缺口」 | §8 唯一一条（§8.1）已标为「已按提案修复」 | 同文 `:420-424` | 低 |
| `docs/architecture/public-contracts.md:423` | 「修复以兼容变更显式版本化（§6、CHANGELOG **`[Unreleased]`**）」 | 指向 `[1.0.0]` 段 | `CHANGELOG.md:8` 已是 `## [1.0.0] — 2026-11-17`，文首再无 `[Unreleased]` 节 | 低 |
| `docs/architecture/evidence-invariants.md:174-175` 与 `:196-199` | 「A cross-reference is the one record whose citation goes unchecked **in the meantime**」／「**Until the analysis passes them**, the resolution half of the rule is off in the real pipeline … The change is one call site」 | 已接线：`EvidenceBuilder(workspace=workspace, dex_files=apk.dex_files)` | `src/dexatlas/core/pipeline.py:206-217`；同文 §6 末段已写「四后端配置都带这个改动跑过、每条交叉引用的引用都能解析」——前后自相矛盾 | 低 |
| `README.md:254`、`README.zh-CN.md:240-241`、`docs/status.md:76`、`:306` | 「**all eight screens** are built and shipped in `v0.2.0`」／「八屏已全部建成」 vs 「workbench **六屏**」 | 三处口径必须一致；按 `docs/architecture/workbench.md` 的表是 **8 屏、其中 3/4/7 三屏标注为部分建成** | `docs/architecture/workbench.md:25-34`（表）、`:132-135`（「This screen covers … plan screens 3, 4 and 7. It does **not** claim the rest of those screens」）；`docs/roadmap/phase2-plan.md:384-392` 的 8 屏清单 | 中 |
| `docs/reports/v1.0.0-dry-run.md:101-104`、`:172`、`:226`；`docs/reports/v1.0.0-release-checklist.md:254` | 「`docs/roadmap/ROADMAP.md` 在仓库中**不存在**」「清单引用悬空」「G3 清单 §3 步骤 7 引用 `docs/roadmap/ROADMAP.md` 悬空」 | 该文件**存在**，链接也**可解析** | `git log --diff-filter=A -- docs/roadmap/ROADMAP.md` → `91748b0`（**初始提交即有**）；`git ls-tree` 各级均在；`[ROADMAP.md](../roadmap/ROADMAP.md)` 从 `docs/reports/` 出发落在 `docs/roadmap/ROADMAP.md`。发版提交 `8f9ddca` 还改过这个文件（「README/README.zh-CN/status.md/**ROADMAP**/phase3-plan/portfolio 的 v1.0.0 表述由『计划/未发布』改为已 tag 事实」） | 高 |
| `docs/outreach/publish-review.md:240` | 「窄验证**二轮**转通过 **3/6**（门槛 ≥4）」 | 二轮是 **2/6**；3/6 是**三轮** | `docs/benchmarks/m6-level2-narrow-verify2.md:59`「转通过题（DexAtlas，3 轮中 ≥2 轮判过）：**2/6**」；`m6-level2-narrow-verify3.md` = 3/6 | 中 |
| `docs/reports/v1.0.0-release-checklist.md:250`、`:270` | 两个真标题都编号为 `## 6.` | 其一应为 `## 7.` | 同文件标题清单：`:250` = `## 6. dry-run 预演记录`、`:270` = `## 6. 决策归属`；GitHub 自动锚点会把后者算作 `#7` | 低 |

### F 组 —— 公共契约活检的分母过期（5 处）

**这是本轮最容易被读者当场抓到的一组。** 契约表 §7 的「26/26 + 6/6 + 14/14 = 46/46」
是 **2026-11-15** 的实测快照；退出码 6 落地（`1f6ef05`，2026-11-16）时脚本多了一个
CLI 检查，脚本**现在**静态可数 **28 REST + 6 MCP + 15 CLI = 49** 个 `check()` 调用。
凡是把这个分母当**现在的事实**写出去的文档，都已经对不上了——而 M10 验收包的 F6
项（`docs/reports/m10-acceptance-pack.md:149`）要求评审者亲自跑这个脚本看分母。

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/releases/v1.0.0.md:61-62` | 「the public contract table frozen with **46/46** live checks (**26 REST + 6 MCP + 14 CLI**)」 | 现为 **49** 项（脚本静态可数 28 + 6 + 15）；或改口径为「2026-11-15 的 46/46 快照 + 其后新增的退出码 6 检查」 | `scripts/verify-public-contracts.py`：`_rest_requests()` 28 个 `check()`、`mcp_checks()` 6 个、`cli_checks()` 15 个（`:571` 是退出码 6 那条）；`git show 80a9e64:scripts/verify-public-contracts.py` → 28 + 6 + 14 | 高 |
| `docs/reports/v1.0.0-github-release-body.md:96-97`、`:174`、`:248-249`、`:311` | 同上「**46/46** live checks (26 REST + 6 MCP + 14 CLI)」 | 同上 | 同上 | 高 |
| `CHANGELOG.md:351-352` | 「逐端点实测（**26 项**）、MCP 走协议实测（**6 项**）、CLI 退出码逐个触发（**14 项**），**46/46** 通过」 | 脚本现为 28 + 6 + 15 = 49 项 | 同上 | 高 |
| `docs/architecture/public-contracts.md:351`、`:381`、`:395` | 「26/26 通过」「6/6 通过」「14/14 通过」（均标 2026年11月15日） | 该表是快照，可保留；建议加一句「脚本自 2026-11-16（退出码 6）起增至 49 项」 | 同上 | 低 |
| `docs/reports/v1.0.0-release-checklist.md:45`、`:115`、`:195` | 「`scripts/verify-public-contracts.py`（**46/46** 通过，记录见契约表 §7）」「缺装会让 **46/46** 契约核对…」「the public contract table with **46/46** verified checks」 | 同 F1 | 同上 | 中 |

> 独立佐证：已提交的 `docs/reports/m10-reader-walkthrough.md:88` 已把同一处记为
> 「2 数字矛盾」，并给出同样的静态计数（28 + 6 + 15 = 49）。

### G 组 —— 基准文档里的数字错误（5 处）

| 文件:行 | 现写的数字/说法 | 应为 | 依据 | 严重度 |
|---|---|---|---|---|
| `docs/benchmarks/m6-level2-retest.md:26-30` | 表头「三轮首测合计」下的值：**A 8/60、B 6/60、DexAtlas 9/60** | A **24/60**、B **18/60**、DexAtlas **24/60** | `docs/benchmarks/m6-level2-real.md:27-29`（首测三轮合计 24/60、18/60、24/60）；按 `m6-level2-traces.json` 逐轮重算 r1 8/6/9、r2 8/6/8、r3 8/6/7 → 24/18/24。**根因在生成脚本**：`scripts/m6_level2_retest_report.py:126-136` 的 `_load_baseline_round1()` 只取 `items[3:63]`（只有 r1），`:318` 却拿它填「三轮首测合计」列并以 60 作分母 —— 同一行的「首测 r1 正确」列（8/20、6/20、9/20）是对的。**按 CLAUDE.md 第 3 条，改脚本重生成，不要手改这份 md** | 高 |
| `docs/benchmarks/task-set.md:110-114` | 「**Thirteen** tasks have an answer that is an absence… **sixteen per cent** of the set… the `unanswerable` category on its own is **fourteen per cent**」 | **Fourteen** tasks；缺席题 **15.2%**（14/92）；`unanswerable` 单类 **12.0%**（11/92） | 用仓库自己的任务清单复算：`benchmarks.tasks.ALL_TASKS` 共 92 题 → `unanswerable` 类 11、`expect_empty` 12、`expect_backend_failure` 2，三者并集 **14**（15.2%）。13/81=16.0%、11/81=13.6% 是 **81 题**时代（`6fc0e04`）的数，题集加到 92（`e28efca`）后未同步 | 中 |
| `docs/benchmarks/task-set.md:481` | 「the **81** tasks measured in `comparison-traces.json` are now a subset of the set, and that measurement needs to be **re-run** before any of the metrics are quoted against the full 92」 | 重跑已完成：92 题 × 3 配置 = 276 条 trace | `docs/benchmarks/comparison-traces.json` 实有 276 条 trace、92 个 distinct `task_id`；`docs/benchmarks/comparison.md:9`「Task count: 92」；重跑结果已在 `comparison.md` 里 | 中 |
| `docs/benchmarks/service-regression-set.md:132` | 「样本覆盖核对：demo-app（多数题）、**strings-app（2）**、obfuscated-app（3）、wide-app（1）、multidex-app（1）」 | **strings-app（1）**（合计仍是冻结的 20 题） | 本文 §3.1–§3.6 的题表里只有 1 题落在 strings-app（`:61` `manifest.permission.name-strings`）；`benchmarks/m6_service_set.py` 的冻结清单 `SERVICE_REGRESSION_PREFIXES`（20 项）同。按题表数：demo 14 / obfuscated 3 / multidex 1 / wide 1 / strings 1 = 20；写 2 会让合计成 21 ≠ 冻结 20 题 | 低 |
| `docs/benchmarks/m6-level2-narrow-verify2.md:3` | 指向首轮窄验证报告 `m6-level2-narrow-verify.md` | `m6-level2-narrow-verify-incomplete.md` | `docs/benchmarks/` 下无此文件，`git log --all --name-only` 显示该名从未存在过——首轮那轮是**不完整运行**，报告名自带 `-incomplete`（见该文 `:3` 自己的说明）。`docs/reports/m10-number-traceability.md:63` 已记过同一件事 | 中 |

---

**历史陈述**（说的是某个基准提交当时的真事，数字当时是对的）——共 **30 处**：

- `docs/reports/m4-acceptance.md:36`（10 个工具）、`docs/reports/m4-review.md:224`
  （十个只读工具）、`docs/reports/model-disable-verification.md:21`、`:115`
  （10 个工具）：三份都带日期与基准提交（2026-11-13/14，`ba770f6`/`71c8d8c`/`1f1d883`）；
  第 11 个工具 2026-11-15 22:51 才落地。
- `docs/reports/phase3-baseline.md:112`（十工具）、`:165`（退出码 0–5 语义）：
  日期 2026-11-15、基准 `6b08684`，两处变更都晚于该基准。
- `docs/reports/m8-install-rehearsal.md:138-145`（「全部后端超时仍 completed、退出码 0」）：
  那是 v1.0.0 用退出码 6 修掉的那条 M8-4 缺口，演练记录就是当时的样子。
- `docs/reports/phase1-maturity-assessment.md`（`:127` 16 个端点、`:411`、`:455` 等）、
  `phase1-review-report.md`、`phase1-findings-ledger.md`、`phase2-issue-list.md`、
  `docs/reports/claim-mismatches.md`：2026-10 的评估/复核快照，行号基准写在文内。
- `docs/reports/coverage-guard-audit.md`：2026-11-17 的审计记录。
- `docs/releases/v0.1.0.md`–`v0.2.0.md`、`phase1-acceptance-2026-10-21.md`：
  发布说明即历史（`v0.2.0.md` 里那一条退出码 5 的例外已列进 §2 A 组）。
- `docs/architecture/public-contracts.md:344`（§7 验证记录的**测量日期与基线**，
  2026-11-15）、`docs/architecture/analysis-runs.md:139` 之外的 §「The schema」
  历史叙述、`docs/architecture/evidence-invariants.md` §5「What this does not do」
  里其余各条。*注：§7.1–§7.3 的分母问题另见 §2 A 组与 F 组——那里的「26/6/14 通过」
  是当日实测记录，不判为事实错误；缺的是退出码 6 那一行与更新后的分母。*
- `docs/status.md:184`（「公共契约变更：0/1/2/3/4 的含义不变，5 是新增」——说的是
  v0.2.0 那一次截断修复）、`:366`（84.8 秒 ffprobe 实测，2026-11-14）、
  `:387`、`:399`、`:513`、`:518`（均为当时的一次性实测记录）。
- `docs/benchmarks/m6-level3-recheck.md:220`（「当前基线 24/60=40%」——该文自述是
  M6-③ 那一轮的复验记录）、`docs/benchmarks/m6-level2-failure-analysis.md:5`、`:28`。
- `docs/analysis-provenance.md:1107-1108`（「当时的现象」表）。
- `docs/architecture/call-sites-and-edges.md:75`（「a record that says ‘23
  cross-references’」——举例说明错误措辞，不是当前输出的声明）。

**计划 / 待办**（说的是将来，尚未发生，不要动）——共 **21 处**：

- `docs/benchmarks/m6-level2-retest-plan.md:125`、`:140-141`
  （`m6-level2-retest-r2-traces.json` / `-r2.md` 是当时约定的产出名，实际产出叫
  `m6-level2-retest-traces.json` / `m6-level2-retest.md`——那是计划里的名字）。
- `docs/benchmarks/m6-verify3-plan.md:186`、`:194`、`:239`
  （`m6-level2-retest5.md`、`scripts/m6_level2_retest5_report.py` 是计划要新开的
  文件，尚未存在）。
- `docs/reports/v1.0.0-release-runbook.md:20`、`:29`、`:34-35`
  （`__version__ = "0.2.0"` 与 `assert '__version__ = "0.2.0"'` 是**发版时执行**的
  步骤；发版已落地后这段脚本原样再跑会在 assert 处报错，但它是流程文档、不是事实
  陈述。*提醒：下个版本复用 runbook 前要改这一行。*）
- `docs/reports/v1.0.0-release-commit-draft.md:45`、`:56`、`:58`、`:69`、`:72`
  （发版 commit 草案里「现文 = 0.2.0 → 改成 1.0.0」的变更清单，commit 已落地，
  草案本身完成使命）。
- `docs/reports/v1.0.0-dry-run.md:5`、`:34`、`:38`、`:91-92`、`:105`、`:224`
  （版本 0.2.0、`docs/releases/v1.0.0.md` 尚不存在、「最新 release 当前为 v0.2.0」
  等预演当时的状态；该文 `:10-11` 已写明「**后续（2026-11-17）：v1.0.0 已发布
  （tag `v1.0.0`）……正文里『当前』『未发布』『仍写待授权』等表述指的是 2026-11-16
  预演当时的状态**」）。
- `docs/roadmap/phase2-plan.md`、`phase3-plan.md` 的里程碑与排期。
- `docs/proposals/exit-code-partial-read.md` §1「问题重述」等现状描述
  （文首标注了状态；§2 起的方案与路线是当时的提案）。*首行「状态：提案，未实施」
  本身已过期，见 §2 E 组。*

---

## 4. 系统性问题

有三类数字是**成片**过期的，不是个别处：

1. **退出码 6 只同步进了 4 份材料中的 3 份。** `599ab67`（「退出码 6 同步进三份
   验收材料」）改的是 `m10-acceptance-pack.md`、`m10-reader-kit.md`、
   `m10-reader-package.md`；**`m10-selfcheck.md` 被漏掉了**，而它正是那份定义
   F1 检查口径的文档。加上 CHANGELOG 的 v1.0.0 段与契约表的 §7.3 活检表，
   退出码 6 在 6 个落盘位置缺位。
2. **MCP 工具数 10 → 11 的同步漏了 4 处**，而且**全部集中在「11 个工具之前写
   的文档」**：架构总览（`architecture/README.md`）、架构图（`diagram.md`）、
   CHANGELOG 的 v1.0.0 段、发版清单。README、workbench.md、portfolio、
   project-brief、scope-ai-mcp 都已经改成 eleven/十一个了——**这四处的漏改与
   已改好的那批处在同一批文件里，不是一个「整体没改」的问题**。
3. **发版测量重跑后，`docs/status.md` 的叙述段没有跟着更新。**
   `comparison-real.md` 在 `bd48d61`（把「后端缺失」记成事实而不是失败任务）与
   `100b191`（Phase 3 M5 基线校准）两次重测，`status.md` 的 §5 表被更新了
   （`:284-285` 是新数字），**叙述段 `:263-274` 整段没动**，仍是 `82523d0`
   那一轮的原文。本报告 D 组前 5 条（正确率、断言率、题数）全部来自那一行旧原文。

另外还有两处**同一份文件内部自相矛盾**，比单纯的数字错更容易让读者困惑：
`status.md:268`（99.0%）vs `:284`（98.9%）；`status.md:268`（2.8%）vs `:285`
（4.4%）。

还有两处是**「机器算出来的数，但算错了」**，不是手抄的问题：

- `docs/benchmarks/m6-level2-retest.md` 的「三轮首测合计」列填的是 r1 的数（分母却是
  60）——根因是 `scripts/m6_level2_retest_report.py` 只加载了 r1 的 trace 却按
  三轮合计的口径输出。这类错不会被「数字由脚本生成、不许手改」这条纪律挡住：
  纪律保证了数字没被手抄，但没保证**脚本本身算对了**。
- 契约活检的分母（46 → 49）是**脚本长大后没人回来改文档**——改脚本的人和改文档
  的人不是同一波，脚本长一格、文档慢半拍。

---

## 5. 复核方法（每条都可用这些命令重放）

```bash
# 契约基线
grep -c "@server.tool" src/dexatlas/mcp/server.py        # 11
grep -c "@app.command()" src/dexatlas/cli/main.py         # 13
grep -cE "^@app\.(get|post|delete)" src/dexatlas/api/app.py # 23
grep -n "EXIT_" src/dexatlas/cli/main.py                  # 0..6
grep -n "SCHEMA_VERSION" src/dexatlas/core/storage.py     # 7
grep -n "__version__" src/dexatlas/__init__.py            # 1.0.0

# 版本与 tag
git tag | tail -3
python scripts/check-version-claims.py --base auto

# M6 逐轮归属（17/15/17 属 retest3，15/16/18 属 retest4）
sed -n '25,41p' docs/benchmarks/m6-level2-retest3.md
sed -n '24,41p' docs/benchmarks/m6-level2-retest4.md

# 契约实测脚本的检查项分布（G 组 / F 组）
python - <<'PY'
import re
lines = open('scripts/verify-public-contracts.py', encoding='utf-8').read().splitlines()
cur, c = None, {}
for l in lines:
    m = re.match(r'def (\w+)', l)
    if m:
        cur = m.group(1); c.setdefault(cur, 0)
    if re.search(r'\bcheck\(', l) and not l.strip().startswith('def '):
        c[cur] = c.get(cur, 0) + 1
print({k: v for k, v in c.items() if v})   # 现在: _rest_requests 28 / mcp_checks 6 / cli_checks 15
PY

# status.md 的真模型数字（用仓库自己的代码复算，不写文件）
.venv/Scripts/python.exe -c "import json,sys; sys.path.insert(0,'.'); \
 import benchmarks.comparison.run as R; \
 d=json.loads(open('docs/benchmarks/comparison-real-traces.json',encoding='utf-8').read()); \
 print('\n'.join(R._failure_causes(R._run_from_document(d))))"
```

---

*本报告由一次只读扫描产生：仅新增本文件，未修改其他任何文件；未运行 pytest、
coverage、uv sync、refresh-report-figures.py；未写入共享树 `E:\Dexatlas`。*
