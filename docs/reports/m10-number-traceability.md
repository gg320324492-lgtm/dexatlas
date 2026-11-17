# M10 数字同源核对报告（v1.0.0 发版前）

> **基线之后的变动（2026-11-17 发版完整测量落盘）：** 发版树的重测量已完成，
> 权威值随之变为 **1,588 个测试（1,441 快 + 147 集成）、一方代码覆盖率 93.3%
> （7,117/7,631 行）**，源指纹 `sha256:787282…`。本报告下文表格里的
> 1,584 / 93.2% 是**基线 `78102a8` 当时**的值，留作对照；§3 A 类那三处污染已由
> 那次测量复原。§3 C 类的五处（退出码 6、MCP 工具数、M8-4）已由主线程改完。

**状态：只读核对。本文件只新增本文件本身，未修改任何其他文件；未运行 pytest / coverage / uv sync。**

本报告回答一个问题：v1.0.0 对外发出的每个数字，能不能在仓库里找到出处？

核对方法是把每个对外数字回追到**重算脚本生成的基准报告**（基准报告的数字由脚本从 trace 重算，见各报告开头声明），再与被核文档逐行比对。凡是追不到出处的，记为「无法核实」或「待核项」。

## 0. 核对基线与口径

### 0.1 被核基线（重要）

本次核对的「现状」不是一个已提交的 commit，而是**共享工作树的实时状态**：

| 项 | 值 |
|---|---|
| 共享树路径 | `E:\Dexatlas`（**未改动**，本窗口只读） |
| 共享树分支 / HEAD | `claude/m6-level2-verify` @ `78102a8` |
| 共享树未提交改动 | `CHANGELOG.md`、`README.md`、`README.zh-CN.md`、`docs/HANDOVER.md`、`docs/portfolio.md`、`docs/reports/m10-acceptance-pack.md`、`docs/reports/m10-invitation-final.md`、`docs/reports/m10-invitation-template.md`、`docs/reports/phase1-execution-report.md`、`docs/roadmap/ROADMAP.md`、`docs/roadmap/phase3-plan.md`、`docs/status.md`、`src/dexatlas/__init__.py`（共 13 个） |
| 本报告所在分支 | `audit/m10-number-traceability`，基线 `origin/claude/m6-level2-verify` @ `78102a8`（含本报告所引用的全部基准报告与读者材料，`docs/benchmarks/m6-level2-retest4.md`、`docs/reports/m10-reader-kit.md`、`docs/reports/m10-acceptance-pack.md` 等在本分支上可直接打开） |

**核对方式**：对这 13 个已改文件取共享树工作目录版本；其余文件取 `git show claude/m6-level2-verify:<path>`（= 共享树 HEAD 的内容）。两者的并集即为「现状」。

**核对期间的基线漂移（已复核）**：本核对进行中，共享树从 `78102a8` 前进到 `7910195`（「测量隔离：覆盖率数据文件按次私有 + 同 checkout 互斥锁 + 红→绿回归」），脏文件从 13 个增至 15 个（新增 `scripts/refresh-report-figures.py`、`tests/test_refresh_coverage_hygiene.py`）。核对收尾时已对 `7910195` + 15 个脏文件**重新逐条复核本报告 §3 的 10 处**：全部仍然成立，行号未变（新提交只碰了测量脚本与新增测试，没有动 §3 涉及的 8 个文档）。主线程修的是**污染的根因**（覆盖率隔离），§3 列的是**已被写坏的文案**，两者都要做。

`78102a8` 的祖先关系（已用 `git merge-base --is-ancestor` 验证）：`fbca3d5`（main）→ `277d0fa` → `78102a8`。`main` @ `fbca3d5` 与发版树不是同一棵树，**两者的测试数/覆盖率不同**，核对时必须区分（见 §2.6）。

### 0.2 基准报告清单

| 基准报告 | 在共享树 HEAD | 用途 |
|---|---|---|
| `docs/benchmarks/m6-level2-real.md` | 是 | 首测（2026-11-15） |
| `docs/benchmarks/m6-level2-retest3.md` | 是 | 三轮完整复测（B1 关闭测量，2026-11-16） |
| `docs/benchmarks/m6-level2-retest4.md` | 是 | 三轮完整重测（B1 验收测量，2026-11-17） |
| `docs/benchmarks/m6-level2-verify.md` | 是 | 单轮验证复测（2026-11-16） |
| `docs/benchmarks/m6-level2-narrow-verify-incomplete.md` | 是 | 窄验证一轮（INCOMPLETE，53/54 trace） |
| `docs/benchmarks/m6-level2-narrow-verify2.md` | 是 | 窄验证二轮 |
| `docs/benchmarks/m6-level2-narrow-verify3.md` | 是 | 窄验证三轮 |
| `docs/benchmarks/m6-verify3-plan.md` | 是 | 窄验证三轮的验收方案与 §7 停止规则 |
| `docs/benchmarks/m6-level1-scripted.md` | 是 | 层级 0 / 层级 1 口径 |
| `docs/architecture/public-contracts.md` | 是 | 26 REST / 6 MCP / 14 CLI、退出码语义 |

### 0.3 行号坐标系（读本报告前必读）

本报告的行号**一律指共享工作树 `E:\Dexatlas` 的当前内容**（含 13 个未提交的发版改动）——也就是主线程将要动笔的那一份。但本报告所在的分支 `audit/m10-number-traceability` 的基线 `78102a8` 是**提交态**，两者行号有系统性差异。

全文 **118 处 `file:line` 引用，在两套坐标下都能解析到非空行**（已用脚本逐对核过）。其中内容不同的 19 处，差异形态只有三种，已逐一归类：

| 形态 | 涉及文件与行 | 处数 | 说明 |
|---|---|---:|---|
| **行号平移** | `CHANGELOG.md` 共享树行 46 / 52 / 54 / 60 / 75 / 92 / 120 / 122 / 129 / 188 / 351 / 443 / 448 / 461 | 14 | 未提交的发版改动在其上方净增 5 行；**分支行号 = 共享树行号 + 5**（14 处偏移全部一致，无例外） |
| **行号相同、内容不同** | `README.md:13`、`docs/status.md:24`、`docs/reports/phase1-execution-report.md:77`（本报告里用了带目录与不带目录两种写法，故计为 2 对） | 4 | 这三处正是 §3 A 类的污染点：**分支（提交态）上是正确值 93.2%**，共享树上是**污染值 35.4%**；行号本身两边一致 |
| **仅存在于共享树** | `docs/reports/m10-invitation-final.md:47` | 1 | 那是主线程在共享树工作目录里**已改好但未提交**的那句补充说明，见 §5 |

其余 **95 处**引用（基准报告、契约表、读者材料等未改文件）**在两套坐标下逐字一致**，可直接按行号打开核对；另有 4 处引用指向快照外的文件（`service-regression-set.md`、`v1.0.0-release-runbook.md`、`m8-install-rehearsal.md`、`src/dexatlas/cli/main.py`），它们在两棵树上未被改动，行号无差异。

### 0.4 任务里给出但**仓库中不存在**的路径（按要求说明）

以下路径在**所有分支**（`git branch -a` 全量列举后逐一 `git cat-file -e` 验证）上的实际存在情况：

| 任务给出的路径 | 实际情况 | 替代路径 |
|---|---|---|
| `docs/benchmarks/m6-level2-narrow-verify.md` | 不存在 | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md`（首轮窄验证是**不完整运行**，报告名自带 `-incomplete`） |
| `docs/benchmarks/m6-level2-narrow-verify3.md` | **存在** | — |
| `docs/reports/m6-level2-narrow-verify2.md` | **不存在**（任何分支均无） | `docs/benchmarks/m6-level2-narrow-verify2.md` |
| `docs/reports/m6-verify3-plan.md` | **不存在**（任何分支均无） | `docs/benchmarks/m6-verify3-plan.md` |

---

## 1. retest3 / retest4 的区分规则（先说这条，因为它决定后面所有逐轮数怎么判）

### 1.1 两份报告的客观差异

| 维度 | retest3 | retest4 |
|---|---|---|
| 文件 | `docs/benchmarks/m6-level2-retest3.md` | `docs/benchmarks/m6-level2-retest4.md` |
| 标题 | M6 层级 2 —— 服务回归集真实模型三轮完整复测（**B1 关闭测量**） | M6 层级 2 —— 服务回归集真实模型三轮完整重测（**执行层修复后验收测量**） |
| 运行日期 | 2026-11-16（`:11`） | 2026-11-17（`:11`） |
| 代码状态 | `main` `c4922dc`（`:20`） | `claude/m6-level2-verify` `f9d9fd8`（`:20`） |
| DexAtlas 逐轮 | r1 17/20、r2 15/20、r3 17/20（`:29`–`:31`） | r1 15/20、r2 16/20、r3 18/20（`:28`–`:30`） |
| DexAtlas 三轮合计 | 49/60 = 81.7%（`:39`） | 49/60 = 81.7%（`:38`） |
| 三轮 trace 合计 token | 1,080,116（`:41`） | 1,182,356（`:40`） |
| A / B 合计 | 20/60 = 33.3% / 22/60 = 36.7%（`:37`–`:38`） | 21/60 = 35.0% / 21/60 = 35.0%（`:36`–`:37`） |
| 验收结论 | 未达标（`:88`） | 未达标（`:85`） |

### 1.2 结论

- **「最终完整重测」是 retest4**（`docs/benchmarks/m6-level2-retest4.md`）。依据有三条，互相独立：
  1. 运行日期更晚（2026-11-17 > 2026-11-16）；
  2. 标题自带定位语——retest4 是「执行层修复后**验收测量**」，retest3 是「**B1 关闭测量**」，后者在验收链条上更早；
  3. 代码状态更晚且**含执行层修复成套**（`f9d9fd8`），retest3 的树 `c4922dc` 不含这些修复——retest3 测的是修复前的树。
- **「更早的一次重测」是 retest3**。
- **对外表述应当用 retest4 的逐轮数 15/20、16/20、18/20**，理由：
  - 它是更晚一次测量、且是验收测量；
  - 它对应**发版树**所处的代码状态，而 retest3 的树已在发版树之外；
  - 仓库内所有「以当前事实为准」的文档已经统一指向 retest4（`docs/reports/m10-reader-kit.md:313`–`:315`、`docs/reports/m10-invitation-final.md:45`–`:47`、`docs/releases/v1.0.0.md:27`–`:31`、`README.md:44`–`:46`、`README.zh-CN.md:342`–`:343`、`docs/reports/m10-acceptance-pack.md:134`、`:543`–`:544`、`:639`）。
- **两次合计数相同是巧合，不是同一批数据。** 合计都是 49/60 = 81.7%，但 token 合计不同（1,080,116 vs 1,182,356，逐轮也不同：367581/356309/356226 vs 395740/395542/391074），A/B 合计也不同（20/60、22/60 vs 21/60、21/60）。两者是两次独立运行。

### 1.3 一个必须提醒的检索陷阱（推断，依据见下）

**逐轮数不能脱离出处单独 grep。** 「15/20」在两份基准报告里都出现：retest3 的 r2 是 15/20（`m6-level2-retest3.md:30`、`:85`），retest4 的 r1 也是 15/20（`m6-level2-retest4.md:28`、`:82`）。同理「17/20」在 retest3 里出现两次（r1、r3），而「16/20」「18/20」只在 retest4 里出现。

所以：**「15/16/18」这个序列只在 retest4 成立；「17/15/17」这个序列只在 retest3 成立。** 判断某处写的是哪一次，不能只看它出现的数字，必须同时看它引用的报告名。这一条是本节其余结论的方法论基础。

---

## 2. 逐个数字核对表

口径说明：
- **一致** = 该处数字与基准报告（及其行号）完全对得上。
- **不一致** = 能确定对不上，已列入 §3 清单。
- **无法核实** = 仓库内无法证实或证伪，记为待核项（§4）。

### 2.1 层级 2 得分与 token

| 数字 | 出现在哪个文档:行 | 出处（基准报告:行） | 结论 |
|---|---|---|---|
| 首测 DexAtlas 24/60 = 40.0% | `docs/status.md:133`；`docs/releases/v1.0.0.md:23`；`docs/reports/v1.0.0-github-release-body.md:289`；`README.md:42`；`README.zh-CN.md:29`；`CHANGELOG.md:52`；`docs/reports/m10-reader-package.md:264`；`docs/reports/m10-acceptance-pack.md:134`、`:544` | `docs/benchmarks/m6-level2-real.md:29` | 一致 |
| 首测逐轮 45% / 40% / 35% | `docs/status.md:133`；`docs/releases/v1.0.0.md:24`；`docs/reports/m10-reader-package.md:264`–`:263`；`CHANGELOG.md:52` | `m6-level2-real.md:42`、`:55`、`:68`（逐轮八指标） | 一致 |
| 首测 A 24/60、B 18/60 | `docs/status.md:133`；`CHANGELOG.md:52`–`:53` | `m6-level2-real.md:27`–`:28` | 一致 |
| 首测 token 853,103（超 800,000 授权 53,103） | `docs/status.md:133`；`docs/releases/v1.0.0.md`（同段）；`docs/reports/m10-reader-package.md:264`–`:263`；`CHANGELOG.md:54`–`:55` | `m6-level2-real.md:31`、`:112` | 一致 |
| **最终完整重测** DexAtlas 49/60 = 81.7%，逐轮 **15/20、16/20、18/20** | `docs/reports/m10-invitation-final.md:45`–`:46`；`docs/reports/m10-reader-kit.md:20`、`:232`；`docs/reports/m10-reader-package.md:239`、`:258`；`docs/reports/m10-acceptance-pack.md:35`、`:133`、`:543`–`:544`、`:639`；`docs/releases/v1.0.0.md:27`–`:28`；`docs/reports/v1.0.0-github-release-body.md:112`–`:113`、`:229`；`CHANGELOG.md:443`–`:444`；`docs/status.md:133`；`README.md:44`；`README.zh-CN.md:342` | `m6-level2-retest4.md:28`–`:30`、`:38`、`:82` | 一致 |
| 更早一次重测逐轮 **17/15/17**，合计同为 49/60 | `docs/reports/m10-invitation-final.md:47`；`docs/reports/m10-reader-kit.md:233`、`:315` | `m6-level2-retest3.md:29`–`:31`、`:39`、`:85` | 一致（已正确标注为「更早一次重测」；邀请函那一处**共享树已改好，待随发版提交**，不计入 §3） |
| retest4 token 合计 1,182,356 | `docs/releases/v1.0.0.md:30`；`docs/reports/v1.0.0-github-release-body.md:282`；`CHANGELOG.md:448`；`docs/status.md:133`；`README.zh-CN.md:343` | `m6-level2-retest4.md:40` | 一致 |
| retest3 token 合计 1,080,116 | `CHANGELOG.md:122`；`docs/status.md:133` | `m6-level2-retest3.md:41` | 一致（CHANGELOG 该条已标为「B1 关闭测量」，未冒用 retest4 名义） |
| retest4 逐轮 token 395,740 / 395,542 / 391,074 | 仅基准报告 | `m6-level2-retest4.md:98` | 一致（对外文档未引用，无冲突） |
| retest4 A 21/60、B 21/60 | `docs/releases/v1.0.0.md:29` | `m6-level2-retest4.md:36`–`:37` | 一致 |
| 单轮验证复测 DexAtlas 15/20 = 75.0%（非验收测量） | `docs/status.md:133`；`CHANGELOG.md:60` | `m6-level2-verify.md:83`、`:89`（并注明「单轮结果受模型方差影响，不外推」） | 一致 |

### 2.2 窄验证（三个口径必须分开）

| 数字 | 出现在哪个文档:行 | 出处（基准报告:行） | 结论 |
|---|---|---|---|
| 窄验证一轮：4/6 转通过、4/5 确定性，**且该轮不完整（53/54 trace）** | `CHANGELOG.md:188`；`docs/status.md:133`；`docs/reports/v1.0.0-github-release-body.md:118`–`:119` | `m6-level2-narrow-verify-incomplete.md:31`、`:32`、`:7`–`:10`、`:17` | 一致 —— 三处都带了「INCOMPLETE / 53 条 trace / 不是 54-trace 判定」的限定，**没有把 4/6 当成三次完整窄验证之一** |
| 窄验证一轮 token 410,256 | `docs/status.md:133`；`docs/reports/v1.0.0-github-release-body.md:119` | `m6-level2-narrow-verify-incomplete.md:16`–`:17` | 一致 |
| 窄验证二轮：转通过 2/6、确定性 2/5，token 420,826（超 410,000 授权 10,826） | `docs/status.md:133`；`CHANGELOG.md:461`–`:468`；`docs/releases/v1.0.0.md:36`；`docs/reports/v1.0.0-github-release-body.md:116` | `m6-level2-narrow-verify2.md:59`、`:60`、`:71`、`:21`（熔断 410,000） | 一致 |
| 窄验证三轮：转通过 3/6、确定性 3/5，token 380,881（在 450,000 授权内） | `docs/status.md:133`；`CHANGELOG.md:92`–`:95`；`docs/releases/v1.0.0.md:38`–`:39`；`docs/reports/v1.0.0-github-release-body.md:117`；`docs/reports/m10-reader-kit.md:22`、`:316`、`:317` | `m6-level2-narrow-verify3.md:59`、`:60`、`:71`、`:21` | 一致 |

**逐轮数列「4/6 → 2/6 → 3/6」在对外文档中的实际呈现**：对外文档只出现 2/6 与 3/6（`docs/releases/v1.0.0.md:36`、`:38`；`README.md:48`「post-fix narrow verification converted 2/6 then 3/6」；`README.md:51`）。**`README.zh-CN.md` 不含 2/6 与 3/6**（其 `:342`–`:344` 只给层级 2 三轮完整重测的 49/60 与逐轮数）——即中文版从未把窄验证的 4/6、2/6、3/6 串成一条序列，未发现混淆风险。4/6 只在**明确标注为不完整的一轮**上出现（`CHANGELOG.md:188`「53/54 条 trace」、`docs/status.md:133`「53 traces … 但这不是 54-trace 判定」、`docs/reports/v1.0.0-github-release-body.md:118`–`:120`）。这与基准一致，未发现把 4/6 混入三轮序列的地方。

### 2.3 验收线口径（B1 线 vs 窄验证闸）

| 数字 | 出现在哪个文档:行 | 出处（基准报告:行） | 结论 |
|---|---|---|---|
| B1 线：每轮 ≥16/20（≥80%）、三轮合计 ≥54/60（≥90%） | `docs/status.md:133`；`docs/releases/v1.0.0.md:24`、`:28`；`docs/reports/v1.0.0-github-release-body.md:111`、`:229`、`:276`；`docs/reports/m10-reader-kit.md:21`、`:314`；`docs/reports/m10-acceptance-pack.md:35`；`docs/reports/m10-invitation-final.md:45` | `m6-level2-retest3.md:3`、`:83`；`m6-level2-retest4.md:3`、`:83` | 一致 —— 各处引用的都是 B1 线 |
| 窄验证闸：转通过 ≥4/6、确定性 ≥3/5 | `docs/reports/v1.0.0-github-release-body.md:117`、`:232`；`docs/releases/v1.0.0.md:38`；`docs/reports/m10-reader-kit.md:22`、`:316`；`CHANGELOG.md:92`–`:95`、`:464` | `m6-level2-narrow-verify2.md:7`–`:8`、`:61`；`m6-level2-narrow-verify3.md:7`–`:8`、`:61` | 一致 —— 与 B1 线未混用 |
| 「连续三轮未达后按 §7 停止投入」 | `docs/status.md:133`；`docs/reports/m10-invitation-final.md:47`–`:48`；`docs/releases/v1.0.0.md:39`–`:41`；`docs/reports/v1.0.0-github-release-body.md:117`–`:120`、`:232` | `m6-level2-narrow-verify3.md:61`（引用 `m6-verify3-plan.md` §7）；`docs/benchmarks/m6-verify3-plan.md` | 一致 |

### 2.4 层级 0 / 层级 1

| 数字 | 出现在哪个文档:行 | 出处（基准报告:行） | 结论 |
|---|---|---|---|
| 层级 0 = 20/20（确定性判分，无模型） | `docs/reports/m10-reader-package.md:238`；`docs/reports/m10-acceptance-pack.md:133`、`:538`；`docs/releases/v1.0.0.md:21`；`docs/reports/v1.0.0-github-release-body.md:84`、`:290` | `m6-level1-scripted.md:106`、`:112`；`docs/benchmarks/service-regression-set.md:173` | 一致 |
| 层级 1：20 题 A 4/20、B 4/20、DexAtlas 1/20 | `docs/reports/m10-reader-package.md:287`；`docs/reports/m10-acceptance-pack.md:134`、`:540`；`CHANGELOG.md:46` | `m6-level1-scripted.md:113`、`:51`–`:53` | 一致 |
| 层级 1：92 题 A 15/92、B 15/92、DexAtlas 5/92 | `docs/reports/m10-acceptance-pack.md:540`–`:541`；`CHANGELOG.md:46`–`:47` | `m6-level1-scripted.md:54`–`:56` | 一致 |
| 层级 1 的口径是「替身模型，只证明管线端到端可用，不是模型能力基线」 | `docs/reports/m10-reader-kit.md:269`；`docs/reports/m10-reader-package.md:287`；`docs/reports/m10-acceptance-pack.md:134` | `m6-level1-scripted.md:4`、`:110`–`:113` | 一致 —— 全部带免责声明，未把 4/20、1/20 当模型通过率 |

### 2.5 公共契约与退出码

| 数字 | 出现在哪个文档:行 | 出处（基准报告:行） | 结论 |
|---|---|---|---|
| 26 REST + 6 MCP + 14 CLI = 46 项活检 | `docs/releases/v1.0.0.md:57`；`docs/reports/v1.0.0-github-release-body.md:97`、`:172`、`:239`、`:299`；`CHANGELOG.md:351`–`:352` | `docs/architecture/public-contracts.md:351`（26/26）、`:381`（6/6）、`:395`（14/14） | 一致 |
| 「6 MCP」= **被活检覆盖的 MCP 工具数**，不是 MCP 工具总数 | 同上 | `public-contracts.md:203`–`:217` 工具清单共 **11** 行；`src/dexatlas/mcp/server.py`（`78102a8`）注册 **11** 个 `@server.tool` | 一致（但见 §3 第 5、9 条：两处文档仍写 10） |
| 退出码 6 = `EXIT_NO_INDEX`（跑完但无可用代码索引） | `docs/releases/v1.0.0.md:63`；`docs/reports/v1.0.0-github-release-body.md:98`–`:99`、`:137`、`:186`、`:301`；`CHANGELOG.md:129`；`docs/status.md:135` | `public-contracts.md:54`、`:64`–`:66`；`src/dexatlas/cli/main.py:135`（`EXIT_NO_INDEX = 6`） | 一致 |
| 退出码 0–5 语义不变 | `public-contracts.md:65` 表述；`docs/status.md:135` | `public-contracts.md:43`–`:54` | 一致 |
| A6 项「Androguard 可用、至少一个外部后端不可用时，分析仍以 0 退出」 | `docs/reports/m10-acceptance-pack.md:87` | `public-contracts.md:60`（索引非空时落 0） | 一致 —— 该场景索引仍可用，落 0 正确，**不受退出码 6 影响** |

### 2.6 测试数与覆盖率（口径最易混的一节）

| 数字 | 出现在哪个文档:行 | 出处 | 结论 |
|---|---|---|---|
| **发版树**：1,584 个测试（1,437 快 + 147 集成）、覆盖率 93.2%（7109/7631 行）、1584 passed + 0 xfailed + 0 skipped | `docs/reports/v1.0.0-github-release-body.md:157`–`:158`、`:160`、`:166`、`:236`、`:262`–`:266`；`docs/status.md:23`；`docs/releases/v1.0.0.md:56` | `docs/reports/phase1-execution-report.md` @ `78102a8`：`:76`（1584/1437/147）、`:77`（93.2%，7109/7631）、`:878`（1584 passed + 0 xfailed + 0 skipped）、`:144`–`:146`、`:1083`（指纹）、`:1086`/`:1096`（JSON） | 一致（引用行号全部命中） |
| `main` @ `fbca3d5` 的测量：1,515 个测试（1,368 快 + 147 集成）、93.2%（6938/7445） | **仅** `main` 分支的 `phase1-execution-report.md` | `git show fbca3d5:docs/reports/phase1-execution-report.md` | 与发版树**不是同一棵树**（`fbca3d5` 是 `277d0fa`/`78102a8` 的祖先）。**对外文档一律不得引用 1,515 / 6938-7445** —— 核对结果：被核文档中**无一处**出现 1515 / 1368 / 6938 / 7445，一致 |
| `docs/portfolio.md:66`–`:67`「1,542 tests at 93.1% coverage」 | `docs/portfolio.md:66`–`:67` | `1,542 / 93.1%` 是 `origin/claude/m6-review-fixes`（`3c76c21`）那一次测量的值，**不是发版树的值** | **不一致** → §3 第 6 条 |
| `docs/portfolio.md:47`「Ten tools over stdio」 | `docs/portfolio.md:47` | 契约工具清单 **11** 个（`public-contracts.md:207`–`:217`）；`docs/releases/v1.0.0.md:119`「MCP tools: 10 → 11」 | **不一致** → §3 第 5 条 |
| `CHANGELOG.md:75`「全量 suite 1575 项通过，覆盖率 93.2%」 | `CHANGELOG.md:75` | 1,575 / 1,428 快 / 93.2%（7073/7590）是 `1e8d947` 那次测量的值（`git show 1e8d947:docs/reports/phase1-execution-report.md:76`–`:77`）；`1e8d947` 是 `277d0fa` 的祖先 | 数字**有出处**（不是编造），但与同一 `[1.0.0]` 段里的 1,584 不是同一次测量且未标注对应 commit → §3 第 11 条（建议） |
| `docs/reports/m10-acceptance-pack.md:605`「`scripts/check-doc-citations.py`：通过（226 条引用，0 漂移）」 | `docs/reports/m10-acceptance-pack.md:605` | 仓库内**没有**落盘这份检查结果 | 无法核实 → §4 待核项 |

### 2.7 其它

| 数字 | 出现在哪个文档:行 | 出处 | 结论 |
|---|---|---|---|
| M10 检查表 40 项 | `docs/reports/m10-invitation-final.md:40`–`:41`；`docs/reports/m10-acceptance-pack.md` | 实测 `docs/reports/m10-acceptance-pack.md` 中 `\| (A\|B\|C\|D\|E\|F\|G)\d+ \|` 行数 = **40** | 一致 |
| 阻断项 19 项 | `docs/reports/m10-invitation-final.md:40`（「19 项一票否决的阻断项」） | 同一表中含 `★` 的行数 = **19** | 一致 |
| 46/46 活检、26/26、6/6、14/14 | 见 §2.5 | 见 §2.5 | 一致 |

---

## 3. 必须改的 10 处

> 只列清单，**未替主线程改动这些文件**。行号以共享树 `E:\Dexatlas` 工作目录当前内容为准。

### A 类 —— 并发 `pytest --cov` 写入的污染（3 处，涉及 3 个文件）

污染源：主线程并发跑的 `pytest --cov` 与发版测量互抢 `.coverage`，写出的残缺覆盖率被脚本写回文档。**正确的发版树覆盖率是 93.2%（7109/7631 行），不是 35.4%。**

> 下列「现状文案」是**共享工作树当前内容**。在本报告分支的提交态（`78102a8`）上，这三行**已经显示正确值**——也就是说这 3 处的修复不需要改代码，只需把共享树的未提交改动提交上去；真正要改文案的只有 B 类和 C 类。

| # | 文件 | 行 | 现状文案 | 建议改成 | 依据 |
|---|---|---|---|---|---|
| 1 | `README.md` | 13 | 徽章上的覆盖率数字 `35.4%`（污染值；徽章 URL 形如 `coverage-35.4%25`） | `coverage-93.2%25` | `git show 78102a8:README.md:13`（提交版为 93.2%）；`phase1-execution-report.md:77` |
| 2 | `docs/status.md` | 24 | `\| 一方代码覆盖率 \| <!--fig:coverage.pct-->35.4%<!--/fig--> \|` | `<!--fig:coverage.pct-->93.2%<!--/fig-->` | `git show 78102a8:docs/status.md:24`（提交版为 93.2%） |
| 3 | `docs/reports/phase1-execution-report.md` | 77 | `\| 一方代码覆盖率 \| **<!--fig:coverage.pct-->35.4%<!--/fig-->**（<!--fig:coverage.covered-->2699<!--/fig-->/<!--fig:coverage.total-->7631<!--/fig--> 行） \| ≥80% \|` | `93.2%` + `7109`（`coverage.total` 7631 未被污染，保持不变） | `git show 78102a8:docs/reports/phase1-execution-report.md:77` |

**同一次污染还改写了弱模块清单表**。把两份文件的全部 `<!--fig:...-->` 标记做差集后，污染涉及的**恰好是 6 个标记、3 个文件**，没有别的：

| 文件 | 标记 | 提交版（正确） | 污染版 |
|---|---|---:|---:|
| `docs/reports/phase1-execution-report.md` | `coverage.pct`（3 处） | 93.2% | 35.4% |
| 同上 | `coverage.covered`（2 处） | 7109 | 2699 |
| 同上 | `coverage.file.tools/androguard/worker.py.pct` | 72.3% | 0.0% |
| 同上 | `coverage.file.tools/androguard/worker.py.missed` | 31 | 112 |
| 同上 | `coverage.file.tools/apktool/adapter.py.pct` | 93.1% | 18.3% |
| 同上 | `coverage.file.tools/apktool/adapter.py.missed` | 22 | 259 |
| `docs/status.md` | `coverage.pct` | 93.2% | 35.4% |
| `README.md` | shields.io 徽章（非 fig 标记） | `coverage-93.2%25` | `coverage-35.4%25` |

`coverage.total`（7631）**未被污染**，保持不变。另外污染把弱模块表的 `covered`/`total` 两列语义对调了（`0.0% | 112 / 112` 这类形态）。

**建议直接用 `git show 78102a8:docs/reports/phase1-execution-report.md` 的对应区段整段还原**（提交版 10 行的弱模块表被污染成了 52 行），不要手改数字；`docs/status.md:24` 与 `README.md:13` 同理，从提交版取回即可。（推断依据：污染写入的数值形态与被污染的 `pytest --cov` 部分运行一致；整段还原比逐格修补更安全。）

### B 类 —— 发版树已更新、两处陈旧数字未跟上（2 处）

| # | 文件 | 行 | 现状文案 | 建议改成 | 依据 |
|---|---|---|---|---|---|
| 4 | `docs/portfolio.md` | 47 | `**Read-only MCP server.** Ten tools over stdio that expose an existing` | `Eleven tools over stdio` | `docs/architecture/public-contracts.md:203`–`:217` 工具清单共 11 行；`src/dexatlas/mcp/server.py`（`78102a8`）注册 11 个 `@server.tool`；`docs/releases/v1.0.0.md:119`「MCP tools: 10 → 11」 |
| 5 | `docs/portfolio.md` | 66–67 | `**Quality gates.** Strict mypy typing, ruff lint/format, 1,542 tests at`<br>`93.1% coverage on the first-party code, and six CI jobs covering different` | `1,584 tests at`<br>`93.2% coverage` | `docs/reports/phase1-execution-report.md` @ `78102a8` `:76`（1584/1437/147）、`:77`（93.2%，7109/7631）；发版正文 `docs/reports/v1.0.0-github-release-body.md:157`、`:160` 已用 1584/93.2% |

### C 类 —— 退出码 6 契约未同步进验收材料（5 处）

这一组是本次核对里**最实质的错误**：退出码 6 已经随 v1.0.0 进入公共契约并落在代码里，但三份读者/验收材料仍在按「退出码 0–5」和「退出码仍为 0」写。

| # | 文件 | 行 | 现状文案 | 建议改成 | 依据 |
|---|---|---|---|---|---|
| 6 | `docs/reports/m10-reader-package.md` | 225–226 | `- **CLI 退出码（F1）**：0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、`<br>`  5 截断；至少实测 0/1/2 各一次。语义见[公共契约表](../architecture/public-contracts.md)。` | 补上 `6 无可用代码索引（EXIT_NO_INDEX：所有读取 DEX 的后端全部失败、索引为空，manifest 仍可读）`；实测项可加 6 | `docs/architecture/public-contracts.md:54`、`:64`–`:66`；`src/dexatlas/cli/main.py:135`（`EXIT_NO_INDEX = 6`）、`:377`、`:389` |
| 7 | `docs/reports/m10-acceptance-pack.md` | 144 | `\| F1 \| CLI 退出码：0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、5 截断；至少实测 0/1/2 各一次，并核对文档语义。 \| ★ \| …` | 同上，补 6 | 同上 |
| 8 | `docs/reports/m10-acceptance-pack.md` | 146 | `\| F3 \| MCP：工具清单为契约表的 10 个，全部只读注解；抽查 2 个工具的返回形状。 \| …` | `契约表的 11 个` | `public-contracts.md:203`–`:217`（11 行）；`docs/releases/v1.0.0.md:119` |
| 9 | `docs/reports/m10-reader-package.md` | 295–298 | `- **M8-4**：三个后端全部超时（或全部失败）时，分析状态仍为 `completed`、`<br>`  退出码仍为 0。项目已**决策为已知限制**，不改退出码契约；复现与理由见`<br>`  [M8 演练 §6](m8-install-rehearsal.md)。请核对你会不会把「全部后端失败」`<br>`  误读为「分析成功」。` | 改为已解决：M8-4 的「退出码仍是 0」缺口已由 v1.0.0 的 `EXIT_NO_INDEX = 6` 补上——全部读取 DEX 的后端失败且索引为空时落 6；原 M8 演练记录（`m8-install-rehearsal.md:138`–`:145`）是当时的实况，需加一句「已在 1.0.0 解决」或改指新契约 | `public-contracts.md:54`（6 的语义）、`:64`–`:66`（「原先错误地落在 0 的运行改落 6，0–5 语义不变」）；`docs/status.md:135`；`src/dexatlas/cli/main.py:135` |
| 10 | `docs/reports/m10-reader-kit.md` | 273 | `- 已知限制 M8-4（三个后端全部失败时退出码仍为 0）、M8-2、M8-3、macOS 未验证`<br>`  （`docs/reports/m10-reader-package.md:295`）；` | 从「已知限制」清单里移除 M8-4，或改为「M8-4 已在 v1.0.0 由退出码 6 解决」；同时 `:274` 的引用行号要随 §4.4 的改动重算 | 同上；且 `docs/status.md:135` 已经把退出码 6 记为 v1.0.0 的公共契约变更，与「不改退出码契约」直接矛盾 |

**这一组为什么最严重（推断，依据已列）**：这五处落在**三份发给外部读者的验收材料**里（`m10-reader-package.md`、`m10-acceptance-pack.md`、`m10-reader-kit.md`）。读者按 F1 实测退出码时，照着「0–5」枚举根本不会去构造退出码 6 的场景；照着 M8-4 又会得出「全部后端失败仍是 0」的错误结论。这与本项目「退出码即契约、只看退出码也要能分辨残缺运行」的设计（`public-contracts.md:62`）正面冲突，且方向是**低估**自己已交付的能力。

### 建议改（2 处，非事实错误）

| # | 文件 | 行 | 现状文案 | 建议 | 依据 |
|---|---|---|---|---|---|
| 11 | `CHANGELOG.md` | 75 | `全量 suite 1575 项通过，覆盖率 93.2%。` | 二选一：① 标明「该次测量对应 commit `1e8d947`」；② 统一为发版树口径「1,584 项，93.2%」。同一 `[1.0.0]` 段（`:8`–`:501`）内现在有两个套件数 | 1,575/1,428/93.2%(7073/7590) 来自 `1e8d947`；1,584/1,437/93.2%(7109/7631) 来自 `277d0fa`（发版树）。`1e8d947` 是 `277d0fa` 的祖先，两者不是同一次测量 |
| 12 | `docs/status.md` | 133 | 窄验证三轮「…54 条 trace 完整，代码 `9f0dae3`」 | 代码改为 `1e8d947`（与基准报告一致） | `docs/benchmarks/m6-level2-narrow-verify3.md:22`「代码状态 \| `claude/m6-level2-verify 1e8d947`」；`git merge-base --is-ancestor 9f0dae3 1e8d947` 为真，即 `9f0dae3` 是 `1e8d947` 的**祖先**——status.md 记的是更早的树 |

---

## 4. 待核项（仓库内无法证实或证伪）

| 项 | 位置 | 为什么无法核实 | 怎么复核 |
|---|---|---|---|
| 「226 条引用，0 漂移」 | `docs/reports/m10-acceptance-pack.md:605` | 仓库里没有落盘这次 `check-doc-citations.py` 的运行结果；本窗口受约束未运行任何 Python 测量命令 | 在发版树上跑 `uv run --no-sync python scripts/check-doc-citations.py`，读它打印的「校验了多少处、漂移了几处」，把实际数字填进去（`docs/status.md:431`–`:432` 明确要求这个数不要手抄） |
| 读者材料的 `file:line` 引用是否仍命中 | `docs/reports/m10-reader-package.md`、`m10-reader-kit.md`、`m10-acceptance-pack.md` 内多处 | 本次只核了**数字**；这些文档里的行号引用是否仍指向它说的东西，需由 `check-doc-citations.py` 判定 | 同上；注意 §3 第 10 条要求改动 `m10-reader-package.md:295` 附近后，相关引用行号会漂，须重跑 remapper + checker |
| `docs/releases/v1.0.0.md:56`–`:58`、`:108`–`:115` 的引用 | 发版说明 | 已逐条核对：`v1.0.0-github-release-body.md:299`、`:301` 引用的这几行**命中**，且 `docs/reports/v1.0.0-release-runbook.md:98` 也命中「46/46 活检（26 REST + 6 MCP + 14 CLI）」 | — （此项无需再核） |

---

## 5. 核对结论

1. **M6 逐轮数的混淆：共享树已改好，**不在本报告的「必须改」清单内**。** `docs/reports/m10-invitation-final.md:45`–`:47` 在共享工作树里已经改成「最终完整重测 … 逐轮 15/20、16/20、18/20，见 retest4 报告；更早一次重测逐轮为 17/15/17、合计同为 49/60」——归属正确、措辞正确，**待随发版提交**（该改动尚未进入 `origin/claude/m6-level2-verify`，故在分支提交态上看不到，见 §0.3 第三种形态）。**全量扫描未发现第二处把 17/15/17 挂到 retest4 名下的地方**；`CHANGELOG.md:120`（17/15/17）属于 retest3 自己的条目、标题即「B1 关闭测量」并指向 `m6-level2-retest3.md`，归属正确。
2. **层级 2 得分、token、验收线、窄验证闸、层级 0/1、公共契约 26/6/14 这几组数字，全部能追到基准报告的对应行，且逐轮数归属正确。**
3. **必须改的共 10 处**：3 处是并发 `pytest --cov` 的污染（README 徽章、status.md 覆盖率、执行报告覆盖率与弱模块表——实测只污染了 6 个 `fig` 标记、3 个文件），2 处是 `docs/portfolio.md` 的陈旧数字（MCP 工具数、测试数与覆盖率），5 处是**退出码 6 与 MCP 工具数 11 没有同步进读者/验收材料**（这是最实质的一组），另有 2 处建议改（CHANGELOG 的 1575 口径、status.md 的窄验证代码 commit）。
4. **发版树的权威测量是 1,584 测试 / 93.2%（7109/7631 行）**，测自 `277d0fa`；`main` @ `fbca3d5` 的 1,515 / 93.2%（6938/7445）是**另一棵树**的测量，被核文档中无一处引用它，一致。

---

*本报告由一次只读核对产生：仅新增本文件，未修改其他任何文件；未运行 pytest、coverage、uv sync；未触碰共享树 `E:\Dexatlas` 的任何文件内容（只读取）。*
