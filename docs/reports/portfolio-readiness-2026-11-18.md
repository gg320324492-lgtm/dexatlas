# GitHub / Upwork 作品集准备度复评（第二轮，作者自评）

日期：2026-11-18。评估基准：**`75976e0` 那棵树**（= **评估当时** `v1.0.0` tag 指向的提交，
本文把它称为「基线树」；**该 tag 后来被重打，现在指向 `b71bf30`**——本文评的仍是 `75976e0`）。
**本文的全部结论只对基线树 `75976e0` 成立。** 工作副本此后继续前进（截至 `d43369b` 已领先基线树
**19 个提交**，此数随工作副本前进而增长）；读者若按当前 checkout 复核，会看到不同的行号、
不同的「仓库现状」、不同的 CI 运行结果。要复核本文，请先 `git checkout 75976e0`。
**本文是作者自评（self-assessment），不是 [M10 准备包](m10-acceptance-pack.md)所要求的独立验收。
（「准备包」= 交给外部读者的 M10 验收材料包；「独立验收」= 由一个没参与实现的人执行该准备包里的
40 项检查并给出结论。）**
维度、两平台权重与 0–4 等级定义全部沿用 [2026-11-15 基线评估](portfolio-readiness-2026-11-15.md)；
「上一轮得分」取 [2026-11-15 复评](portfolio-readiness-2026-11-15-recheck.md) §6.5 的最终值
（GitHub 81.25% / Upwork 76.9%）。分值是作者按同一评分表对**基线树 `75976e0`**
的保守判断，供 M10 独立验收对照，**不是验收结论，不是生产成熟度认证，也不是「客户会买」的预测**。

> **一句话结论**：这一轮补上的证据几乎全部落在**「可复现」与「说法为真」**两件事上，
> 没有一件落在**「被外部验证」**上。因此两个平台的分数都涨了（GitHub +3.75 个百分点、
> Upwork +5.0 个百分点——**相对上一轮** [2026-11-15 复评](portfolio-readiness-2026-11-15-recheck.md)
> §6.5 的 81.25% / 76.9%；分母是同一张评分表下的两平台各自百分比分，见 §1、§2 的算式），
> 而最高权重、最能决定「能不能对外说『已验收』」的
> **独立使用验证** 一分未动，仍是 1 / 4。

> **更正（2026-11-18，主会话）**：本报告 §8 第 8 条原写「作者记录下的 CI 10 次并行
> 运行**全绿**」，并以此作为「有一个可引用的发布版本了」的证据之一。**那句话是错的**：
> tag `v1.0.0` 的那次 CI run（`44126968629`）以 `failure` 结束，**4 个 job 红**
> （`Tests (Python 3.12)`、`Tests (Python 3.13)`、`Tests (Apktool only, no JADX)`、
> `The report's figures describe the tagged tree`），根因是同一条契约判据，主会话已修。
> （本文说的「绿」= 那次 CI run 里每个 job 的结论都是 success；只要有一个不是，就不叫绿。）
> 本报告的**分数不变**——「核心工程与证据链 4/4」的依据是 `ci.yml` 里的**机制**
> （tag 触发、三个新 job、两处门禁盲区收口），不是那次运行的结果；但凡写着「全绿」
> 的地方都已改成事实。详见 §4.1、§7 第 7 条、§8 第 8 与第 17 条。

---

## 0. 这份复评是什么、不是什么

- **是**：作者在 v1.0.0 发布、门禁扩容、一次真实读者演练之后，按原评分表做的一次
  自测快照，逐项给出证据出处与扣分原因。
- **不是**：独立验收。没有未参与实现的读者执行过
  [准备包](m10-acceptance-pack.md)；本文不给任何验收项判「通过」。
- **不是**：M6 的最终 Agent 评分。层级 2 真实模型**三轮、每轮 20 题**（合计 60 题）的完整重测
  结果是 **49 / 60 = 81.7%**，未达验收线（每轮 ≥80%、三轮合计 ≥90%），
  见 [m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:83、:85。
- **不是**：对仓库全部质量的重测。本轮未重新执行完整测试矩阵与覆盖率测量，
  采用仓库里已落盘的最终测量：**套件数与一方代码覆盖率见
  [phase1-execution-report.md](phase1-execution-report.md):76-77 的落盘标记**
  （`<!--fig:tests.total-->` / `tests.fast` / `tests.slow` / `coverage.pct` /
  `coverage.covered` / `coverage.total`；源指纹见同文 :1097 的 `source_fingerprint`）。
  **本文不抄这些数字**：它们由 `scripts/refresh-report-figures.py` 写盘，重测量会整体替换；
  本文引用标记，读者按标记去该文对。
  （标记里的「快 / 集成」= fast / slow 两套——fast 是 pytest 没标 `slow` 的用例，
  slow 是标了 `@pytest.mark.slow`、要真调外部后端的集成用例。）
- **不是**：接单计划、报价单或市场调研。

---

## 1. 评分表：GitHub 作品集

等级定义（沿用基线）：0＝未见证据；1＝初步证据；2＝局部可用、仍有实质缺口；
3＝在声明环境内有完整演示或复现记录；4＝在该维度的限定范围内经过评审并有边界验证。
4 不表示软件无缺陷。

| 维度 | 权重 | 上一轮 | 这一轮 | 变化理由（出处） |
|---|---:|:---:|:---:|---|
| 核心工程与证据链 | 30% | 4 | 4 | 已到等级上限；证据变厚但未跨档：CI 新增 tag 触发与只在 tag 上跑的测量 job（[ci.yml](../../.github/workflows/ci.yml):18、:493-525），契约活检进 CI（`ci.yml:442`；契约活检 = 真的把公共契约面跑一遍、失败就非零退出的脚本），M10 自查进 CI（`ci.yml:471`）；两处门禁盲区收口（[check-doc-citations.py](../../scripts/check-doc-citations.py):107、[refresh-report-figures.py](../../scripts/refresh-report-figures.py):1012） |
| 首次试用与复现 | 20% | 3 | **3.5** | 升级：新增[读者实走演练](reader-dry-run.md)——真 clone 46 秒、`uv sync` 218 秒、后端 359 秒，九步路径与材料逐字相符，七道门禁退出码全 0（:39-45、:196-199）；并查出 **11 处材料与现实不符**（:108-118），已逐条改正。扣分见 §4.2 |
| Agent 可用性与评测可信度 | 10% | 3.5 | 3.5 | 未变：M6 层级 2 **三轮、每轮 20 题（合计 60 题）**，通过 **49/60 = 81.7%**，仍未达三轮合计 ≥90%（[m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:83）；层级 0/1 证据延续有效 |
| 客户交付件与服务边界 | 10% | 3 | **3.5** | 升级：契约活检真跑通（[public-contracts.md](../architecture/public-contracts.md):348-362，三后端齐备 = Apktool、JADX、androguard 三个后端都在，48/48、仅 androguard 47/47、退出码 0）；交付路径被演练全程走通。扣分见 §4.4 |
| 对外展示与个人贡献说明 | 25% | 3 | 3 | 未变：v1.0.0 已发布、LICENSE 已换成官方全文（[LICENSE](../../LICENSE):1、:176、:178）、两轮走查与两轮审计已落盘；但 Upwork 素材仍是草稿未发布（[project-brief.md](../outreach/project-brief.md):3），独立首读复核结论未回填 |
| 独立使用验证 | 5% | 1 | 1 | 未变：可见记录仍全部是作者自测；[M10 独立验收](m10-acceptance-pack.md)尚未发起（[status.md](../status.md):3、:138） |

**GitHub 加权：4×30 + 3.5×20 + 3.5×10 + 3.5×10 + 3×25 + 1×5 = 120 + 70 + 35 + 35 + 75 + 5 = 340 → 85.0%**

> **分母**：每一维的等级满分 **4 分**，权重是百分数且**各平台权重和 = 100%**，
> 所以一个平台的**满分是 4 × 100 = 400 分**；平台得分 = 400 × 百分比。
> GitHub 340 / 400 = **85.0%**。算法见 §3。

## 2. 评分表：Upwork 服务页

| 维度 | 权重 | 上一轮 | 这一轮 | 变化理由（出处） |
|---|---:|:---:|:---:|---|
| 核心工程与证据链 | 20% | 4 | 4 | 同 §1；契约活检与测量进 CI 对 Upwork 侧的意义更直接：对外承诺的每一条现在都有机器可复核的出处 |
| 首次试用与复现 | 15% | 3 | **3.5** | 同 §1：演练把「客户从零装一遍」这条路走通并留了实测耗时，可直接用于服务页的工时口径 |
| Agent 可用性与评测可信度 | 15% | 3.5 | 3.5 | 未变：49/60 = 81.7%（三轮、每轮 20 题）未达线，AI/MCP 方向的承诺只能按已实测口径写，不能按模型能力写 |
| 客户交付件与服务边界 | 25% | 3 | **3.5** | 升级：契约活检两套配置实测、已知限制节、发布前点检十项（[publish-review.md](../outreach/publish-review.md):307-340）；扣分见 §4.4 |
| 对外展示与个人贡献说明 | 15% | 3 | 3 | 未变：服务页与素材仍为草稿未发布（[project-brief.md](../outreach/project-brief.md):3）——这是 Upwork 侧唯一能开门的动作，没做就不能给分 |
| 独立使用验证 | 10% | 1 | 1 | 未变：没有外部读者执行过准备包 |

**Upwork 加权：4×20 + 3.5×15 + 3.5×15 + 3.5×25 + 3×15 + 1×10 = 80 + 52.5 + 52.5 + 87.5 + 45 + 10 = 327.5 → 81.9%**

> **分母**：同上（每维满分 4 分、权重和 = 100%、平台满分 400 分）。
> Upwork 327.5 / 400 = **81.875%**，本文四舍五入报 **81.9%**
> （读者若用 81.9 反推会得到 327.6，与 327.5 差 0.1 —— 那是四舍五入，不是算错）。
> GitHub 340 / 400 = 85.0% 恰好整除，无此偏差。

## 3. 加权计算与对照

计算方式与前两轮相同：每项贡献＝分值 ÷ 4 × 该平台权重，两平台分别求和。
**分母**：每维等级满分 **4 分**、权重为百分数、**各平台权重和 = 100%**，
故平台满分 = 4 × 100 = **400 分**，百分比 = 加权和 ÷ 400。

| 平台 | 2026-11-15 基线 | 上一轮复评（§6.5） | 这一轮 | 距 90% |
|---|---:|---:|---:|---:|
| GitHub | 约 75% | 81.25% | **85.0%** | 差 **5.0 个百分点** |
| Upwork | 约 65% | 76.9% | **81.9%** | 差 **8.1 个百分点** |
| 两平台平均 | 约 70% | 79.1% | **83.4%** | 差 6.6 个百分点 |

与上一轮同表相比：GitHub **+3.75**、Upwork **+5.0** 个百分点。
**这两个增量的分母是「上一轮复评 §6.5 的百分比分」**——
81.25% → 85.0%（+3.75）、76.9% → 81.9%（+5.0）；两边用的是同一张评分表、
同一个满分 400 的分母，所以可以直接相减。**不是**相对 2026-11-15 基线评估
（那一列是「约 75% / 约 65%」的粗值）。
增量全部来自两个半档（首次试用、客户交付件），而 Upwork 权重最高（25%）的客户交付件也是本轮涨得最多的
一维——但它仍差 0.5 分到 4，挡住它的不是证据，是**服务页没发布**。

> **口径校正（上一轮的算式）**：[上一轮复评](portfolio-readiness-2026-11-15-recheck.md):127-130
> 的收敛清单里，GitHub 增量列（+10.0 / +2.5）与其自述口径「分值 ÷ 4 × 权重」算不平：
> 按权重应为 +7.5（独立使用 1→3 = 2.5，首次试用 3→4 = 5.0）与
> +11.25（客户交付 2→4 = 5.0，对外展示 3→4 = 6.25）；同表的 Upwork 列与口径一致。
> 本文 §6 的增量一律按权重直接算出并写出算式。

---

## 4. 逐维度证据与扣分原因

### 4.1 核心工程与证据链 — 4 / 4（维持，已到等级上限）

**证据**：[Phase 2 计划](../roadmap/phase2-plan.md)、[M4 源码评审](m4-review.md)、
[公共契约表](../architecture/public-contracts.md)、`tests/test_evidence_invariants.py`、
`tests/test_upload_isolation.py`。本轮新增的硬证据有四条：

1. **CI 会验发版树本身**。[ci.yml](../../.github/workflows/ci.yml):4-18 的 push 触发
   同时收 `branches: [main, 'release/**']` 与 `tags: ['v*']`；`ci.yml:493-525` 新增的
   `measurement` job 以 `if: startsWith(github.ref, 'refs/tags/')` 为条件，
   在 tag 上装齐后端与 fixtures，跑 `scripts/refresh-report-figures.py --check`
   ——**只比较、不写盘**。它回答的是「报告里的数字描述的还是不是这棵被 tag 的树」。
2. **三道本地门禁进了 CI**：契约活检（`ci.yml:442`）、M10 自查（`ci.yml:471`）、
   测量比对（`ci.yml:493-525`）。上一轮 [CI 门禁覆盖复核](ci-gate-coverage.md):70-77 记录的
   「21 项门禁里 CI 只跑 14 项、6 道只在本地」是扩容前的状态。
3. **两处「没人核对」的盲区收口在门禁里**，不是靠改文档口径：
   出处按文档自己声明的树解析（[check-doc-citations.py](../../scripts/check-doc-citations.py):107
   的 `TREE_DOCUMENTS`，新 finding 类别 `not in the tree` / `unverified tree`），
   刷新脚本在**任何测量与写盘之前**核对报告 §2.1 的测试文件集合
   （[refresh-report-figures.py](../../scripts/refresh-report-figures.py):1012 的
   `test_file_table()`，不等就退出码 1、报告一字不动）。
   处置记录见 [ci-gate-coverage.md](ci-gate-coverage.md):340-386。
4. **契约表从「声称」变成「实测」**。[public-contracts.md](../architecture/public-contracts.md):348-362
   写明 **49 是静态条数**（28 REST + 6 MCP + 15 CLI），任何一次实跑都跑不满它；
   实跑执行条数依机器而定：三后端齐备 48 条、仅 androguard 47 条，两种配置都是
   **全通过、退出码 0**。

**扣分（为什么不是「范围之外的高分」）**：该维度已到等级定义上限 4，且 4 只在
「已验收能力」这个限定范围内成立——插件化调度、跨平台后端等扩展不在声明范围内。
本轮不构成下调理由。

**要提升它要做什么**：该维度没有可提的档位。真实风险不在分数，在**这个 4 分的证据
全是「机制在仓库里」**——tag `v1.0.0` 那次 CI run 实际是**红的**（§8 第 8 条），
而运行结果仓库里没有落盘记录——见 §7 与 §8 第 17 条。

### 4.2 首次试用与复现 — 3 → 3.5（升级）

**升级理由**：上一轮这一维的扣分是「演练由作者执行，macOS 未验证，仍无独立首次用户
从零安装的验收记录」（[上一轮复评](portfolio-readiness-2026-11-15-recheck.md):83-84）。
本轮新增的[读者实走演练](reader-dry-run.md)把「从零安装」这一段从**推断**变成了
**实测**：

| 材料说的 | 实测 | 出处 |
|---|---|---|
| `git clone` | 退出码 0，**46 秒**，37 MB | [reader-dry-run.md](reader-dry-run.md):39 |
| `git checkout v1.0.0` + `git status` | `HEAD detached at v1.0.0`，工作树干净 | :40 |
| `uv sync`（四 extras） | 退出码 0，**218 秒**，解析 97 个包 | :42 |
| 装后端（jadx 1.5.2 / apktool 2.11.1） | 退出码 0，**359 秒** | :44 |
| 首次分析（**无外部后端**） | 退出码 0，3 秒，产出报告；错误记录写明 `not_installed`，`completeness=partial` | :45 |

九步读者路径与材料逐字相符；七道门禁退出码全 0；契约实测 48/48
（[reader-dry-run.md](reader-dry-run.md):59）；M10 自查 40 通过 / 0 失败
（[reader-dry-run.md](reader-dry-run.md):196-199）。
**更重要的是它找出 11 处材料与现实不符**
（:108-118），逐条列了「材料说的 / 实际是 / 出处 / 状态」，并给出 §5 的必改清单（:122）；
这 11 处现已逐条改正（例如 [m10-acceptance-pack.md](m10-acceptance-pack.md):331 的时间预期
已改成「15 秒–4 分 30 秒」并附演练实测 4 分 24 秒；
[install.md](../install.md):132-135 已写明脚本里的 `export` 不跨进程、
Windows 要指向 `bin\jadx.bat`；`export` 提示改为按 manifest 实际文件数打印
（[cli/main.py](../../src/dexatlas/cli/main.py):898））。

**扣分（为什么是 3.5 而不是 4）**：

1. **执行者是作者**。演练文件第 3 行自己写着「**作者侧自测记录。本文件不是独立验收**」。
   等级 4 要求「经过评审并有边界验证」，作者自测不构成外部评审。
2. **演练树不是发布 tag**。演练跑在 `0104ccb` 上（[reader-dry-run.md](reader-dry-run.md):9-13），
   而 `v1.0.0` 现在指向 `75976e0`，两者相距 **23 个提交（19 个非合并提交）**。
   改动落在 27 个文档文件、3 个脚本、2 个测试文件、1 张图与 2 个 README 上，
   `src/` **一行未改**（`git diff --stat 0104ccb 75976e0 -- src/` 为空）。
   也就是说分析路径没变，但**最终 tag 上的读者路径没有再走一遍**——
   这是本轮新增的、也是最该被读者知道的一条限定。
3. **macOS 仍未验证**（[m8-install-rehearsal.md](m8-install-rehearsal.md):28，
   「无 Apple 硬件，如实标注」）。

**要提升它要做什么**：在最终 tag 上再走一遍读者路径（作者的机器即可，成本约 15 分钟），
并把这份记录与 CI 的 tag 运行记录一起落盘；再由一位外部读者走一遍，才够 4。

### 4.3 Agent 可用性与评测可信度 — 3.5 / 3.5（维持）

**证据**：[冻结回归集](../benchmarks/service-regression-set.md)（层级 0 确定性判分 20/20）、
[层级 1 scripted 演练](../benchmarks/m6-level1-scripted.md)（完整公开，含失败形态解读）、
[M5 声明核查](phase3-baseline.md)（三份 benchmark 可从已提交 trace 逐字节再生）、
默认预算上调与重复调用检测等有依据的收敛。

**扣分**：**层级 2 真实模型三轮完整重测 49/60 = 81.7%，未达验收线**
（**分母：三轮、每轮 20 题，合计 60 题**；逐轮 15/20 = 75.0%、16/20 = 80.0%、18/20 = 90.0%；
r1 未达每轮 ≥16/20，三轮合计未达 ≥54/60，
见 [m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:83、:85）。
按冻结纪律，只能修正系统或缩小并重述服务承诺后重测，不得删题换通过率
（同文件 :85）。因此维持 3.5，不给 4。

**要提升它要做什么**：两条路——(a) 授权真实模型预算，跑完三轮并达到每轮 ≥16/20、
合计 ≥54/60；(b) 按冻结纪律缩小并重述承诺后重测。两条都需要外部动作，仓库内做不完。

### 4.4 客户交付件与服务边界 — 3 → 3.5（升级）

**升级理由**：上一轮这一维停在 3，扣分是「逐例可下载附件已落盘且经校验；**不给 4**：
Upwork 服务页仍是草稿未发布，且无客户式审阅记录」
（[上一轮复评](portfolio-readiness-2026-11-15-recheck.md):223）。本轮把「服务边界」
这一半变成了实测：

1. **契约表原来说错了一句，已改**。「三后端齐备时是 49/49」不成立：49 是
   `check()` 调用点的静态条数，任何一次实跑都跑不满它；实测是 48/48（退出码 0）。
   两条 CLI 断言原先把**机器**当成了前提（「没有源码后端时退出码为 1」），
   三后端齐备时前提不成立，脚本把一棵正确的树判成不合格；现按「这次分析里有没有
   对应后端参与」分支，与后端无关的两条「答案为空即 1」在两种配置下都被核对。
   契约表与实跑对照见 [public-contracts.md](../architecture/public-contracts.md):348-362。
2. **交付路径被全程走通**：演练从首次分析走到三格式报告导出、证据包导出与校验、
   契约抽查（[reader-dry-run.md](reader-dry-run.md):59、:196-199）。
3. **对外素材的点检已成清单**：十项「发出去之前必须人工确认」，
   从版本号会过期到零联系方式零时区的补齐（[publish-review.md](../outreach/publish-review.md):307-340）。

**扣分（为什么是 3.5 而不是 4）**：4 分的两条前提**一条都没满足**——
服务页仍是草稿未发布（[project-brief.md](../outreach/project-brief.md):3
「Draft for review — not published」），且没有任何客户视角的审阅记录；
点检清单里第 3、7 两条（`scope-ai-mcp.md` 整篇还是节选、联系方式与时区怎么写）
还是作者本人才做得出的决定。

**要提升它要做什么**：把点检清单十条逐条做完并发布服务页，然后找一位按客户视角
读一遍的人留下书面意见（[客户视角指引](m10-acceptance-pack.md) 已备好）。

### 4.5 对外展示与个人贡献说明 — 3 / 3（维持）

**证据**：[双语 README](../../README.md) 首屏与文档地图、第三方归属表、路线图状态；
v1.0.0 已发布（tag `v1.0.0` = `75976e0`，GitHub Release 正文成稿在
[v1.0.0-github-release-body.md](v1.0.0-github-release-body.md)）；
**LICENSE 已修好**——原文件是「Apache-2.0 头部 + Apache-1.1 短版正文」的混本，
现换成与官方逐字节一致的全文（202 行、11,358 字节，末段含
`END OF TERMS AND CONDITIONS` 与 `APPENDIX: How to apply…`，见 [LICENSE](../../LICENSE):176、:178），
GitHub 现已识别为 Apache-2.0，与 README 徽章、`pyproject.toml` 的声明对得上；
两轮读者视角走查共 37 条（第一轮 29 条 + 第二轮新发现 8 条，见
[索引](README.md):126-127、[m10-reader-walkthrough-2nd.md](m10-reader-walkthrough-2nd.md)），
两轮审计逐条核到出处（过期数字 52 处见 [stale-number-scan.md](stale-number-scan.md):70；
跨文档口径 23 处见 [final-outward-consistency.md](final-outward-consistency.md) §4；
英文读者终检 16 处见 [english-reader-review.md](english-reader-review.md)；
数字同源 10 处见 [m10-number-traceability.md](m10-number-traceability.md)；
新页交叉校对 9 处见 [new-pages-crosscheck.md](new-pages-crosscheck.md)）。

**扣分**：

1. **Upwork 服务页与素材仍是草稿、未发布**（[project-brief.md](../outreach/project-brief.md):3）。
   这一条是 Upwork 侧唯一的门槛动作，没做就不能给 4。
2. **README 的独立首读复核结论仍未回填**（上一轮列为待办 #5，至今没有落盘的结论）。
3. **本轮自查发现的新不一致还没改**：README 徽章（**由脚本写入**，
   值见 [phase1-execution-report.md](phase1-execution-report.md):76 的 `<!--fig:tests.total-->`
   落盘值）与 README 正文、social preview 的说明文字（**手写**）当前不一致
   （见 §8 第 1–3 条）——展示维度上的「说法为真」还没做到全库一致。
   **这三个位置的数字由 `scripts/refresh-report-figures.py` 负责同步，本文不抄。**

**要提升它要做什么**：发布服务页、回填独立首读复核结论、把 §8 的前三条改掉。

### 4.6 独立使用验证 — 1 / 1（维持）

**这一轮没有拿到任何新的独立验证证据，也没有可以替代它的东西。**
可见的记录全部是作者侧材料：[M10 准备包](m10-acceptance-pack.md)（40 项验收检查表、
读者一站式入口、客户视角指引）、[记录模板](m10-review-record-template.md)、
[邀请函成稿](m10-invitation-final.md)（:60 的 commit 占位符仍待发起人填写）、
以及本轮新增的读者实走演练——而演练文件第 3 行就写明它是「作者侧自测记录」。
[status.md](../status.md):3、:138 记的是同一件事：M10 独立验收**尚未发起**。

按「证据缺失不给高分」原则维持 1 分。这不是推断项目没有外部用户，
而是**没有可引用的独立复现记录**。

**要提升它要做什么**：把[邀请函](m10-invitation-final.md)填好发出，
让一位未参与实现的读者按准备包执行并填记录模板。仓库内的活已经做完了，
剩下的是发出去。

---

## 5. 这一轮新增的证据改变了哪些判断

逐条列出：证据 → 它改掉了上一轮的哪个判断 → 影响了哪一维。

1. **「报告数字说的是哪棵树」有了机器答案。**
   证据：CI 的 `measurement` job 只在 tag 上跑，跑的是 `refresh-report-figures.py --check`
   （[ci.yml](../../.github/workflows/ci.yml):493-525）。
   改变的判断：上一轮 §6.6 的缺口表里没有这一项，因为那时 tag 推送根本不触发 CI
   （[ci-gate-coverage.md](ci-gate-coverage.md):13、:35、:49 仍记着旧状态）。
   影响：核心工程（4/4，但证据更硬）。

2. **「CI 只跑 14 项门禁、6 道只在本地」不再成立。**
   证据：契约活检（`ci.yml:442`）、M10 自查（`ci.yml:471`）、测量比对（`ci.yml:493-525`）三个 job；
   tag 推送也产生 run（`ci.yml:18`）。
   改变的判断：上一轮把「本地门禁无人守护」当成结构性缺口；现在这三项在每次
   push 到 `main`、PR 到 `main` 与 tag 推送时都会自动核对一次。
   影响：核心工程（4/4）。

3. **两处「没人核对」的盲区有了解法，且解法不是改文档口径。**
   证据：[check-doc-citations.py](../../scripts/check-doc-citations.py):107 的
   `TREE_DOCUMENTS`（出处按文档声明的树解析，并核对声明本身）；
   [refresh-report-figures.py](../../scripts/refresh-report-figures.py):1012 的
   `test_file_table()`（写盘前核对测试文件集合，不等就拒绝写）；
   处置记录 [ci-gate-coverage.md](ci-gate-coverage.md):340-386。
   改变的判断：上一轮把这两处列为「没人会红」的结构性缺口。
   影响：核心工程（4/4）。

4. **「材料说的是不是真的」第一次被真机验过。**
   证据：读者实走演练（[reader-dry-run.md](reader-dry-run.md):39-45）——真 clone、
   检出 tag、九步路径、七道门禁退出码全 0、契约 48/48、M10 自查 **43 条自动化判定全过、0 失败**（另有 40 项留人工——「留人工」= 这 40 项要由人读材料下结论，脚本判不了；两个分母不是一回事）；
   并查出 11 处材料与现实不符（:108-118）。
   改变的判断：上一轮所有安装/复现证据都来自项目自己的窗口（M8 演练也是作者执行），
   无法排除「材料按项目自己的想象写」。现在有了一份**逐字对照表**，
   而且它证明材料曾经错 11 处——这恰恰是可信度的来源，不是减分项。
   影响：首次试用（3 → 3.5）。

5. **「契约表说的 49/49」是错的，现在是实测。**
   证据：[public-contracts.md](../architecture/public-contracts.md):348-362：
   49 是静态条数，实跑 48/48（退出码 0）或 47/47；两条 CLI 断言原先把机器当前状态
   当成契约前提，已改成按「这次分析有没有对应后端参与」分支。
   改变的判断：上一轮把「契约表已成文并固化为测试」当作已完成项；实际上其中一条结论
   当时是错的，而且错在「机器齐备时反而不合格」这个方向。
   影响：客户交付件与服务边界（3 → 3.5）。

6. **对外文本的自相矛盾是被逐条数出来的，不是印象。**
   证据：读者视角走查两轮共 37 条（29 + 8，见 [索引](README.md):126-127）；
   审计五份：过期数字 52 处、跨文档口径 23 处、英文读者 16 处、数字同源 10 处、
   新页交叉校对 9 处（各报告的结论节）。
   改变的判断：上一轮把「对外文本口径一致」当作已达标项；现在能说清「一致到什么程度、
   剩哪几处不一致」，且其中若干处是本轮新产生的（§8 第 1–3 条）。
   影响：对外展示（3/3，不变——因为未发现的缺口比新发现的多）。

7. **仓库的许可证现在说得出确切版本。**
   证据：[LICENSE](../../LICENSE) 为官方 Apache-2.0 全文（202 行、11,358 字节，
   :176 `END OF TERMS AND CONDITIONS`、:178 `APPENDIX`），此前是 2.0 头部配 1.1 短版正文的混本。
   改变的判断：上一轮无法确认 GitHub 是否识别为 Apache-2.0；现在徽章、
   `pyproject.toml` 与 LICENSE 三处说的是同一件事。
   影响：对外展示（3/3，不变）、核心工程（4/4）。

8. **有一个可引用的发布版本了。**
   证据：**写就时** tag `v1.0.0` = `75976e0`，与 `origin/main` 同指
   （**该 tag 后来被重打，现在指向 `b71bf30`**；本文评的仍是 `75976e0`）；
   [发版说明](../releases/v1.0.0.md) 与 [GitHub Release 正文成稿](v1.0.0-github-release-body.md) 都在仓库里；
   **但该 tag 的 CI run 不是绿的**：run `44126968629` 以 `failure` 结束（耗时 14 分 32 秒），
   **4 个 job 红**——`Tests (Python 3.12)`、`Tests (Python 3.13)`、
   `Tests (Apktool only, no JADX)`、`The report's figures describe the tagged tree`；
   根因是同一条契约判据（`social-preview-howto.md` 写了分项却没在 40 字内写出总数 49），
   主会话已修（见 [release-process-dry-run.md](release-process-dry-run.md) §4.1）。
   tag 推送时的 CI 规模是 **9 个 job 定义、10 次并行运行**（`test` 是 3.12/3.13 矩阵）。
   **这一条结果是 2026-11-18 主会话用 `gh run view` 核出来的**（本报告写就时未联网）；
   仓库里也确实没有落盘记录（见 §7 第 7 条、§8 第 17 条）。
   改变的判断：上一轮评的是「一个工作分支上的树」；这一轮评的是「一个发布出去的版本」
   ——**指的是 tag `v1.0.0` 所指的那一棵树（`75976e0`），不是读者今天拿到的代码**
   （工作副本已领先它 19 个提交，见文首）。
   **但「发布出去」不等于「CI 验过」**，这一点本报告原版写反了。
   影响：核心工程（4/4，**依据是 `ci.yml` 里的机制，不是那次运行的结果**）、对外展示（3/3）。

9. **新增了一条限定：读者路径没在最终 tag 上再走一遍。**
   证据：演练基准 `0104ccb`（[reader-dry-run.md](reader-dry-run.md):9-13），
   而 tag 现在指向 `75976e0`，相距 **23 个提交（19 个非合并提交）**——
   改动全在文档、脚本与测试上，`src/` 一行未改。
   改变的判断：读者实走演练**不能**直接声称「v1.0.0 的读者路径已验证」——
   只能说「演练所在的树已验证，之后的差异是文档、门禁脚本与数字」。
   影响：首次试用（因此只给 3.5，不给 4）。

10. **新增了一条限定：CI 的运行结果，读者无法从仓库自行复核。**
    证据：机制落盘（[ci.yml](../../.github/workflows/ci.yml)），结果不落盘——
    仓库里没有一份记录写着哪一次 run 结论是什么、覆盖哪些 job、对应哪个 commit。
    改变的判断：上一轮的所有「全绿」都是作者口述；这一轮仍然如此，只是机制更硬了。
    影响：不改分，但写进 §7 与 §8。
    **2026-11-18 主会话更正**：tag `v1.0.0` 那次 run 实际以 `failure` 结束、4 个 job 红
    （§8 第 8 条）——所以「全绿」这个前提**本身不成立**，不只是读者无法复核。

---

## 6. 仍然最该先补的三件事

按对「**能不能接活 / 能不能被信任**」的影响排序。增量按「分值 ÷ 4 × 权重」直接算出。

### 第一件：真正把 M10 独立验收发起出去（被信任）

- 影响维度：**独立使用验证 1 → 3**（仓库里能做的已经做完了，缺的只是一个外部读者）；
  连带 **首次试用与复现 3.5 → 4**（有外部读者的首读记录才够 4）。
- 增量：GitHub **+2.5 + 2.5 = +5.0**；Upwork **+5.0 + 1.875 = +6.9**。
- 为什么排第一：这是所有对外声明的前置。当前仓库里没有任何一处可以写
  「已通过独立验收」——邀请函成稿已就绪（[m10-invitation-final.md](m10-invitation-final.md)），
  只差发出。
- 前置条件：把 :60 的 commit 占位符填上（`git rev-parse v1.0.0^{commit}`），
  然后发出邀请函。**这一步不需要改任何代码，需要的是作者的勇气和一次外部动作。**

### 第二件：发布 Upwork 英文服务页与可下载交付样例（接活）

- 影响维度：**对外展示与个人贡献说明 3 → 4**、**客户交付件与服务边界 3.5 → 4**。
- 增量：GitHub **+6.25 + 1.25 = +7.5**；Upwork **+3.75 + 3.125 = +6.9**。
- 为什么排第二：这是 Upwork 侧唯一能开门的动作——服务页没发布，
  「能不能接活」在字面意义上就不成立；点检清单十项
  （[publish-review.md](../outreach/publish-review.md):307-340）已经把要做的事列全了。
- 前置条件：作者本人拍板第 3、7 条（`scope-ai-mcp.md` 整篇还是节选、
  联系方式与时区怎么写），再逐条做完其余各项。

### 第三件：M6 层级 2 达标，或按冻结纪律缩小并重述承诺（接活时能承诺多少）

- 影响维度：**Agent 可用性与评测可信度 3.5 → 4**。
- 增量：GitHub **+1.25**；Upwork **+1.875**。
- 为什么排第三而不是第一：它只影响一维，且**不阻塞服务页**——
  但它决定服务页上「Evidence-first AI / MCP Integration」这一方向能写多满：
  49/60 = 81.7% 的实测结果不支持「稳定优于基线」这类说法
  （[m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:83、:85）。
- 前置条件：需要真实模型预算授权；或走同文件 :85 给的另一半路——
  修正系统或**缩小并重述服务承诺**后重测（不得删题换通过率）。

> **三件做完之后的两平台分数**：GitHub 85.0 + 5.0 + 7.5 + 1.25 = **98.75**；
> Upwork 81.875 + 6.875 + 6.875 + 1.875 = **97.5**。
> 换句话说：**三件事都做完，两平台都会越过 90%**，而其中没有一件需要改产品代码。

---

## 7. 仍然未达成的（照旧写出来）

| # | 缺口 | 现状与出处 |
|---|---|---|
| 1 | **M6 层级 2 未达验收线** | 三轮合计 **49/60 = 81.7%**（逐轮 15/16/18），未达「每轮 ≥80%、三轮合计 ≥90%」；r1 15/20 = 75.0% 未达每轮线（[m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:83、:85） |
| 2 | **M10 独立验收未发起** | 材料已成稿，邀请函待发起人发出；commit 占位符未填（[m10-invitation-final.md](m10-invitation-final.md):60；[status.md](../status.md):3、:138） |
| 3 | **Upwork 服务页与素材仍是草稿未发布** | [project-brief.md](../outreach/project-brief.md):3「Draft for review — not published」；发布前还有十项人工确认（[publish-review.md](../outreach/publish-review.md):307-340） |
| 4 | **macOS 未验证** | 无 Apple 硬件，如实标注（[m8-install-rehearsal.md](m8-install-rehearsal.md):28） |
| 5 | **三个证据包只覆盖两份分析** | demo 与 api-integration 两个包的 `report.md` / `report.html` 是**同一份分析报告**（字节相同），不能当成两份独立证据报数（[case-studies/README.md](../case-studies/README.md):36-37；[publish-review.md](../outreach/publish-review.md):342-343） |
| 6 | **读者路径未在最终 tag 上复走** | 演练基准 `0104ccb`，tag 现指向 `75976e0`，相距 23 个提交（`src/` 一行未改）（[reader-dry-run.md](reader-dry-run.md):9-13） |
| 7 | **CI 的运行结果没有落盘记录** | 机制在 [ci.yml](../../.github/workflows/ci.yml)，运行结果不在仓库里；读者无法自行复核（而且 tag `v1.0.0` 那次 run 实际是红的，见 §8 第 8 条） |
| 8 | **README 独立首读复核结论未回填** | 上一轮列为待办 #5，至今无落盘结论 |

**这一轮新增的还有两条口径限定**（上一轮没有）：

- 上一轮 §2 引用的测量是 **1,542 测试 / 93.1%**（那是上一轮自己抄进正文的字面值）；
  本文不抄基线树的值，改引用落盘标记：
  **[phase1-execution-report.md](phase1-execution-report.md):76-77** 的
  `<!--fig:tests.total-->` / `tests.fast` / `tests.slow` / `coverage.pct` /
  `coverage.covered` / `coverage.total`（源指纹见同文 :1097 的 `source_fingerprint`）。
  这些数字由 `scripts/refresh-report-figures.py` 写盘，**重测量会整体替换**；
  本文的口径差异结论（「这一轮的测量比上一轮新」）不依赖具体数值。
- 上一轮的复评结论（§6.5，GitHub 81.25% / Upwork 76.9%）本身**没有被重新计算**，
  它是「上一轮的快照」；本文是「这一轮的快照」。两者不可相加。

---

## 8. 必须改的 18 处（只列清单，不代改任何文件）

按「会不会让读者读到一句假话」排序。**本文不代改任何一处**。

| # | 文件:行 | 现状 | 建议改法 |
|---|---|---|---|
| 1 | [README.md](../../README.md):15 | 徽章由脚本写入（其值 = [phase1-execution-report.md](phase1-execution-report.md):76 的 `<!--fig:tests.total-->` 落盘值），正文却手写着「完整环境下的一次测量（**1612** 个测试、0 跳过）」——手写的那一处没跟上落盘值 | 改成指向 `<!--fig:tests.total-->` 的落盘值（**不要抄数字**）；这一步由 `scripts/refresh-report-figures.py` 同步 |
| 2 | [README.md](../../README.md):21 | social preview 的 alt 文本手写着「…93.3% first-party code coverage, **1612** tests…」 | 同上：alt 文本与徽章同源（脚本写），或由脚本一并同步 |
| 3 | [social-preview-howto.md](social-preview-howto.md):53-54 | 「图上的文字」映射表手写着 `1612` 与 `1465 快 + 147 集成`，而执行报告 :76 的落盘值已是别的数 | 按新值改这张表，否则照它重画会把旧数画回图上；新值取 `<!--fig:tests.total-->` / `tests.fast` 的落盘值，不手抄 |
| 4 | [status.md](../status.md):26 | 「CI｜**6 个** workflow job 全绿…故实际并行运行数为 **7**」 | 改为 **9 个 job 定义、tag 推送时展开成 10 次并行运行**（`test` 是 3.12/3.13 两格矩阵，所以 9 个 job → 10 次运行；分母是 `ci.yml` 的 job 定义数，不是「运行数」）（[ci.yml](../../.github/workflows/ci.yml):38、:119、:198、:270、:406、:416、:442、:471、:493） |
| 5 | [status.md](../status.md):50-51 | 「CI 的**六个** workflow job 各自覆盖一种配置…展开后是**七个**并行运行」 | 同上（9 job 定义 / 10 次运行） |
| 6 | [v1.0.0-release-checklist.md](v1.0.0-release-checklist.md):40 | 「最终 commit 上 CI **七个**并行运行全绿」 | 改为 10 次（tag 推送时） |
| 7 | [v1.0.0-release-checklist.md](v1.0.0-release-checklist.md):112、:423-427 | 「CI 只在 push 到 `main` 或 PR 到 `main` 时触发…**推 tag 也不产生** run」「21 项门禁里 CI 实际跑 14 项，6 道只存在于本地」 | 已被 [ci.yml](../../.github/workflows/ci.yml):18 与三个新 job 推翻；按新状态重写或加注记 |
| 8 | [ci-gate-coverage.md](ci-gate-coverage.md):13、:35、:49 | 摘要与 §1/§3 说 tag 推送不触发 workflow、CI 是「6 个 job、7 次并行运行」 | 同上：改为 tag 会触发、9 个 job / 10 次运行。§7.1（:340-386）只记了另两个盲区，这条没记 |
| 9 | [ci-gate-coverage.md](ci-gate-coverage.md):139-140、:414、:446 | 「`v1.0.0^{commit}` = `8f9ddca`」「tag 不可变，本轮没有动它」 | 现在是 `75976e0`；tag 已被重打**五次**（6 个 tag 状态：success → success → success → failure → cancelled → in_progress，见 [release-process-dry-run.md](release-process-dry-run.md) §4.3），按当前指向改 |
| 10 | [next-engagements.md](next-engagements.md):3 | 「调研基准：本 worktree 的 `0104ccb`（= tag `v1.0.0` 指向的 commit）」 | tag 现指向 `75976e0`；改基准句或注明「本文写于 tag 重打之前」 |
| 11 | [m10-invitation-final.md](m10-invitation-final.md):60 | commit 占位符「【待填：v1.0.0 发版 commit 的完整 hash】」仍是空的 | 按该文件自述的写法让读者用 `git rev-parse v1.0.0^{commit}` 自取比对（**别写死一个 hash**：tag 被重打是这条路径的常态，写死的 hash 第二天就会过期） |
| 12 | [docs/reports/README.md](README.md) | 索引漏收两份报告：**reader-dry-run.md**（该文件 §7 自己承认「本文件尚未被收录」）与 **next-engagements.md** | 补进索引表；另 :87 那条把要填的 hash 写成 `0104ccb…`，而 tag 现指向 `75976e0` |
| 13 | [m10-reader-walkthrough-2nd.md](m10-reader-walkthrough-2nd.md)（N1）与 [索引](README.md):127 | 记「N1（重打 `v1.0.0` tag、把远端推进到最终 commit）**未处理**」 | 已处理（tag 已重打并推到 `75976e0`）；回填结论，否则读者会以为发版仍卡着 |
| 14 | [m10-number-traceability.md](m10-number-traceability.md)（索引 [README.md](README.md):120 亦引） | 记录的权威值是「1,588 个测试、一方代码覆盖率 93.3%（7,117/7,631 行）、源指纹 `sha256:975afa8e…`」 | **三项都要按落盘值回填**（**不抄数字**）：套件数与覆盖率取 [phase1-execution-report.md](phase1-execution-report.md):76-77 的 `<!--fig:tests.total-->` / `tests.fast` / `tests.slow` / `coverage.pct` / `coverage.covered` / `coverage.total`；源指纹取同文 :1097 的 `source_fingerprint`。**覆盖率的那两行行数会随套件一起变**（分子分母同时动），所以「百分比没变」不等于「行数没变」。回填并注明「发版后重测已刷新」 |
| 15 | [portfolio-readiness-2026-11-15-recheck.md](portfolio-readiness-2026-11-15-recheck.md):127-130 | §4 收敛清单的 GitHub 增量列（+10.0 / +2.5）与其自述口径算不平（按权重应为 +7.5 / +11.25） | 加一行注记说明该列的口径，或按权重改算；本文 §6 已改用可直接复算的算式 |
| 16 | [status.md](../status.md):71-77 | 「已发布版本」表只列到 `v0.2.0`（`v1.0.0` 只出现在 §1 快照） | 表里补 `v1.0.0` 一行 |
| 17 | 仓库内无落盘记录 | CI 的运行结果只有机制（[ci.yml](../../.github/workflows/ci.yml)）没有结果——tag `v1.0.0` 那次 run 实际以 `failure` 结束、4 个 job 红 | 落盘一份运行记录（run 链接、时间、覆盖的 job、对应的 commit、结论），放进 [docs/reports/](README.md) 并进索引 —— 否则读者无从判断「这个发布版本的 CI 结论是什么」 |
| 18 | [reader-dry-run.md](reader-dry-run.md):12-13、:41、:63 | 文中多处把 `0104ccb` 当作「tag 所指提交」 | 加一句「本文写于 tag 重打之前，当前 tag 指向 `75976e0`」，与 §7 已有的说明一致 |

---

## 附录：核验方法、门禁记录与局限

**本轮做了这些（全部只读）**：

- 读了**基线树**（`75976e0`）上的评分基线两篇、准备包、契约表、状态页、案例与附件、
  五份对外素材、三份读者走查报告、五份审计报告、演练报告与本轮新增的两份报告，
  逐条核到 `file:line`。
- `git` 只读查询：`rev-parse`、`rev-list --count`、`log`、`diff --stat`、`merge-base --is-ancestor`、
  `for-each-ref`、`cat-file`。
- 三道只读门禁（见下）。

**本轮没有做（因此不据此加分）**：

- 未运行 `pytest --cov`、任何 `coverage` 命令、`uv sync`、
  `scripts/refresh-report-figures.py`；未重新测量覆盖率与套件数，
  采用仓库里已落盘的最终测量（[phase1-execution-report.md](phase1-execution-report.md):76-77、:1097）。
- 未联网。因此**「GitHub Release 在线」「GitHub 已把仓库识别为 Apache-2.0」这两条本轮无法复核**，
  本文只引用仓库里可查的部分（tag 指向、CI 工作流定义、LICENSE 全文），其余按作者在平台上的
  观察陈述，并在 §8 第 17 条列为待落盘项。
  **第三条「CI 10 次并行运行全绿」已从本清单删去**：它不再只是「本轮无法复核」，
  而是**已被证伪**——tag `v1.0.0` 那次 run 以 `failure` 结束、**4 个 job 红**（见文首更正与 §4.1）。
- 未邀请任何独立读者，未发起 M10 独立验收，未发布任何内容。
- 未修改仓库任何文件（除新增本报告），未写入共享树 `E:\Dexatlas`。

**门禁记录（2026-11-18，基准 `75976e0`，本 worktree 内执行）**：

| 门禁 | 结果 |
|---|---|
| `pytest tests/test_docs.py -q`（不带 `--cov`） | **64 passed**，0 skipped |
| `python scripts/check-doc-citations.py` | exit 0 —— `citations: 285`（`naming a symbol: 166`、`pointing only at a location: 119`）、`unresolved paths: 0`、`drifted: 0`；按树分列：v1.0.0 树 1 份文档 / 63 处，工作副本 11 份 / 222 处 |
| `python scripts/check-version-claims.py --base auto` | exit 0 —— `tags: …, v1.0.0`；`package version: 1.0.0`；`newest release: v1.0.0`；`documents read: 123`；`findings: 2`（两条均为 v0.2.0 / CHANGELOG 的历史发版记录，base `410aebb1` 已含） |

**这份自评的局限**：

1. 评分者是作者本人，与被评对象同源。分值只应被当作**独立验收的对照基线**，
   最终分数必须由 M10 独立验收按[重评模板](m10-review-record-template.md)产生。
2. 门禁只覆盖文档与声明的一致性，**不覆盖产品行为**；本文对「工程」与「复现」两维的
   信心来自别人写的报告与作者自己的演练，不是来自本轮的独立复现。
3. 本文的证据引用大量依赖仓库内的自述文档；当这些文档本身有过期内容时
   （§8 第 4–10 条与第 13–16 条正是这类），本文的引用也会随之过期。
   本文已把这类点单列在 §8，便于读者按图索骥地自己核。
