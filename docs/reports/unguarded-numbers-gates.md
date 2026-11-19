# 没人守的手写测量数：逐处处置与那道门禁

**日期**：2026年11月19日 · **性质**：实现报告（本窗口新增两个脚本、一个测试文件与本文件；
另改了三个既有文件，见 §7）

**回答的问题**：[《手写测量数审计》](handwritten-numbers-audit.md) 查出的十处
**没有任何门禁会报**的手写测量数，逐处怎么办。

**一句话**：十处里 **七处配了门禁**（B1、B3、B4、B5、B6 的静态条数、B8、B9），
**两处明确写成「不归自动管」并说清为什么**（B2、B10），
**一处一半归一半不归**（B6 的实跑条数）。
新门禁是 `scripts/check-unguarded-numbers.py`：
它**守性质，不守写死的数**——真值每次从树上算出来，文档里那句话被读出来比。

**门禁现在是红的**：11 条 finding，全部落在审计查出的那几处**真过期**的数上
（`1,695` vs 树上的 `1,733`）。这是它该有的样子，§4 有红→绿的实测。

---

## 0. 判据与做法

审计 §0 已经把「什么算测量数」划清楚了（会随树变 + 是对外的当前声明）。本窗口
只处理「没人守」那一类，处理办法只有两条，任务书里也是这么写的：

1. **配一道门禁**——让它陈旧了会被报出来；
2. **明确写成「不归自动管」**——并说清为什么。

两条路的分界，本窗口用的是这个问句：

> **这个数能不能从树上现算出来？**
>
> 能 → 配门禁（守性质：文档说的与算出来的一致）。
> 不能 → 不归（并说清缺的是哪一次测量、哪一个人的判断，还是哪个后端）。

「不能现算」不等于「不重要」。B2 与 B7 都很重要——它们被写进「不归」不是因为它们
不重要，而是因为**给它们配一道静态门禁，等于把一个手抄的数换成另一个手抄的数**，
那正是审计要治的病。

---

## 1. 逐处 → 处置 → 依据

| # | 是什么数 | 在哪 | 处置 | 依据（真值从哪来 / 为什么不归） |
|---|---|---|---|---|
| **B1** ★★★ | 测试总数、覆盖率 | `docs/portfolio.md:67`–`:68` | **门禁** | 真值 = 执行报告的 `<!--fig:tests.total-->` / `<!--fig:coverage.pct-->`（报告由测量脚本写、并与源码指纹比对）。门禁语句：`portfolio-tests-total`、`portfolio-coverage`。**现在是红的** |
| **B2** ★★★ | 「另一个环境」那一行的 passed/skipped 与 skip 理由拆分 | `docs/how-to-verify.md:171`、`.zh-CN.md:148` | **不归自动管** | 那一行量的是「**没取第三方样本**」那一次运行。现有测量键里没有它：`suite.*` 记的是「取了样本」那一次。要守它得先有那一次测量（另一次完整运行，成本与理由要单独立项）。**处置：那一行降级成「不写具体数」，只留 skip 的理由分类**——散文改标记那一扇窗口正在做。本窗口不碰那两页 |
| **B3** ★★ | 汇总列的 `1,695 / 93.3%`（6 处） | `docs/outreach/publish-review.md:50`–`:53`、`:342`、`:406` | **门禁** | outward 规则只认带单位的写法（`N tests` / `N 个测试` / 带 `coverage` 字样的百分数），`N / P%` 两种都不满足。门禁语句：`outreach-summary`（最右列与两处正文）、`outreach-quoted-texts`（表格「修正后」列那四个反引号里的数——**反引号让 outward 规则把它当引文放过**，而它是**将要发出去的文案**，所以单列一条）。**现在是红的** |
| **B4** ★★ | CI job 数与并行 run 数（tag 上 / push 上） | `CLAUDE.md:79`、`AGENTS.md:79`、`docs/portfolio.md:68`、`docs/status.md:26`、`:50`、`docs/HANDOVER.md:148` | **门禁** | 真值 = `.github/workflows/ci.yml`：job 键的个数、矩阵展开后的 run 数（tag 上）、以及只在 tag 上跑的 job 减掉之后的 run 数（push/PR 上）。门禁语句：`ci-jobs-*`（6 条）、`ci-tag-runs-*`（5 条）、`ci-push-runs-*`（2 条）。**现在绿的** |
| **B5** ★★ | MCP 工具数（11） | `docs/portfolio.md:48`、`docs/HANDOVER.md:29`、`docs/status.md:256`、`docs/architecture/README.md:288` | **门禁** | 真值 = `src/dexatlas/mcp/server.py` 里 `@server.tool` 的注册数（AST 数，与 `check-version-claims.py` 的 `mcp_tool_count()` 同一个函数）。门禁语句：`mcp-tools-*`（4 条）。**现在是绿的** |
| **B6** ★ | 契约检查项数：静态 49 / 实跑 48 或 47 | `docs/glossary.md:186` | **一半门禁，一半不归** | **静态条数（49）配门禁**：它等于 `docs/architecture/public-contracts.md` §7 记录里的数，而 §7 由 `check-contract-records.py` 实跑守着——守的是「glossary 与权威一致」，权威自己有人守。**实跑条数（「48 或 47，依可用后端而定」）不归**：它依**可用后端**而定，一个静态数守不住它；页面自己已经把这个依赖写明了。门禁语句：`contract-static-checks` |
| **B7** ★ | 分析产出条数（类/方法/交叉引用/证据/字符串/资源） | `docs/analysis-provenance.md:398`–`:402`、`:411`、`:850` | **不归自动管** | 它是**一次管线运行的记录**：五个自建样本上跑一遍分析得到的结果，重算要跑分析与后端，而读者要复核它也得跑一遍。把它写成「当前的数」就会变成下一个手抄的数。**处置：标明它是一次运行的记录（跑的是哪棵树 / 哪次测量），不要当现状读** |
| **B8** ★ | 基准对比（真模型那次）的断言条数 | `docs/status.md:293`、`docs/benchmarks/comparison-real.md`、`comparison-stronger.md` | **门禁** | 真值 = 落盘的 `comparison-real-traces.json` 的 `assertions` 字段（非空断言、带 grounded + locator 的、A/B 的、不带 locator 的、百分比），算法与报告的 metrics 同一个分母。**两份报告另由测试守住**：`comparison-real.md` 与 `comparison-stronger.md` 各自从自己的 trace 重算并**逐字比对**——CI 的 `m3-comparison` job 只重算 `comparison.md`，那两份是「由脚本重算、却没有人跑」的数。门禁语句：`status-trace-assertions`；测试：`test_the_real_model_reports_regenerate_from_their_committed_traces` |
| **B9** ★ | M10 自查条数（43/43） | `docs/status.md:145` | **门禁** | 真值 = `docs/reports/m10-selfcheck.md` 记录的条数，而那份记录由 `check-m10-snapshot.py` 对着真脚本核过（43 通过 / 0 失败 / 40 留人工）。门禁语句：`status-m10-selfcheck` |
| **B10** ★ | 测试文件表右列的「说明」 | `docs/reports/phase1-execution-report.md` 的测试文件表 | **不归自动管** | 那不是数，是一句「这个测试文件覆盖什么」——**脚本判不了**，那是人的判断，而人的判断不该由一个正则来守。表里的**行**已经有人守（`test_execution_report_lists_every_test_file` 比文件名集合，缺一行就红）。本窗口不碰那个文件 |

---

## 2. 新门禁怎么工作

### 2.1 两个文件

| | 是什么 |
|---|---|
| `scripts/check-unguarded-numbers.py` | 门禁本体：从树上把真值算出来，从文档里把那句话读出来，比 |
| `scripts/unguarded-numbers.json` | **清单**：门禁守着的每一处（哪个文件、哪句话、正则、数是什么）。改写一句话就改这里 |

清单里现在是 **25 条语句**。每条语句点名一个文件、一条正则和「这个数是什么」。
正则里的命名组对应事实：`{"number": "ci_jobs"}`。

### 2.2 真值从哪来（**没有一个是抄下来的**）

| 事实 | 怎么算 | 用到哪 |
|---|---|---|
| `ci_jobs` / `ci_tag_runs` / `ci_push_runs` | 读 `.github/workflows/ci.yml`：job 键的个数、矩阵展开后的 run 数、只在 tag 上跑的 job 减掉之后的 run 数 | B4 |
| `mcp_tools` | `src/dexatlas/mcp/server.py` 的 AST：`@server.tool` 的注册数（复用 `check-version-claims.py` 的 `mcp_tool_count()`） | B5 |
| `report_tests_total` / `report_coverage_pct` | 执行报告的 `<!--fig:…-->`（复用 `check-release-numbers.py` 的 `read_authority()`） | B1、B3 |
| `m10_automated_passed` / `m10_automated_total` | `docs/reports/m10-selfcheck.md` 的记录（复用 `check-m10-snapshot.py` 的 `recorded_summary()`） | B9 |
| `trace_*`（5 个） | `docs/benchmarks/comparison-real-traces.json` 的 `assertions` 字段 | B8 |
| `contract_static_checks` | `docs/architecture/public-contracts.md` §7 记录里的数 | B6 |

**复用而不是重写**：这四个真值都借用了别的门禁已有的函数。一个数有两种算法，
迟早会给出两个答案；这里只有一个。

### 2.3 守的是性质

门禁**从不**说「CI job 数是 13」。它说的是：

> 「这句话说的是 CI job 数，而 workflow 里有这些个 job。」

真值每次从树上算。加一个 job、换一个工具、加一个测试——门禁自己就红了，
**没有人需要手改一个数**。这一点有实测（§5.2）。

### 2.4 一句话改版了，门禁会说出来

清单里的每一条语句，正则都必须在文档里匹配上、而且那一处要读得出数。匹配不上时
门禁报「这句话不在文档里了」，而不是安静地不再守它——**一句被守着的句子消失了，
本身就是一件要有人决定的事**（是句子被删了，还是清单该改名）。

同理，一个匹配上但读不出数的地方（「the tools,」而不是「eleven tools,」）不算一句
数的话，会被跳过；一句都跳不过去时，报「不在了」。

---

## 3. 逐处的门禁语句

| 事实 | 语句（清单里的 id） | 文档 |
|---|---|---|
| `ci_jobs` | `ci-jobs-claude` / `-agents` / `-portfolio` / `-status-table` / `-status-prose` / `-handover` | `CLAUDE.md`、`AGENTS.md`、`docs/portfolio.md`、`docs/status.md`（两处）、`docs/HANDOVER.md` |
| `ci_tag_runs` | `ci-tag-runs-claude` / `-agents` / `-portfolio` / `-status` / `-handover` | 同上五处 |
| `ci_push_runs` | `ci-push-runs-handover` / `-status` | `docs/HANDOVER.md`、`docs/status.md` |
| `mcp_tools` | `mcp-tools-portfolio` / `-handover` / `-status` / `-architecture` | `docs/portfolio.md`、`docs/HANDOVER.md`、`docs/status.md`、`docs/architecture/README.md` |
| `report_tests_total` / `report_coverage_pct` | `portfolio-tests-total` / `portfolio-coverage` | `docs/portfolio.md` |
| `report_tests_total` / `report_coverage_pct` | `outreach-summary` | `docs/outreach/publish-review.md`（6 处） |
| `report_tests_total` | `outreach-quoted-texts` | `docs/outreach/publish-review.md`（表格「修正后」列 4 处） |
| `report_tests_total` | `outreach-truth-column` | `docs/outreach/publish-review.md`（表格最右「落盘真值」列那一个不带百分数的格子，`:51`） |
| `m10_automated_passed` / `m10_automated_total` | `status-m10-selfcheck` | `docs/status.md:145` |
| `trace_*`（5 个） | `status-trace-assertions` | `docs/status.md:293` |
| `contract_static_checks` | `contract-static-checks` | `docs/glossary.md:186` |

---

## 4. 红→绿（实测，不是声称）

### 4.1 红：门禁在**这棵树**上抓到了审计说的那处真过期

```
$ uv run --no-sync python scripts/check-unguarded-numbers.py
FAIL docs/portfolio.md:67  [portfolio-tests-total]  it says 1695, and the report_tests_total is 1733
FAIL docs/outreach/publish-review.md:50  [outreach-summary]  it says 1695, and the report_tests_total is 1733
…（共 11 条，全部是 1,695 vs 1,733）
11 finding(s) in 25 watched statements.
$ echo $?
1
```

这 11 条落在三处：`docs/portfolio.md:67`（B1）、`docs/outreach/publish-review.md`
的最右「落盘真值」列与「修正后」列（B3）。**这正是审计 §2 B1/B3 说的
「已经陈旧且静默」**——现在它不静默了。逐行清单在 §9。

### 4.2 绿：同一个门禁、同棵树，数字改对之后

把上面两处的 `1,695` 改成 `1,733`（**只在本窗口的工作树里临时改，随后
`git checkout --` 还原，两文件最终没有进入提交**），门禁：

```
$ uv run --no-sync python scripts/check-unguarded-numbers.py
PASS 25 watched statements agree with the tree.
$ echo $?
0
```

**红→绿只差那个数**。门禁没有改过一个字。

### 4.3 「在旧实现下是红的」

这一条按两种读法都成立：

- **读法一（树）**：门禁跑在**旧树**（`be593fa`，本窗口动手之前）上是红的——
  那棵树里 `docs/portfolio.md` 写的就是 `1,695`。上面 4.1 就是那棵树。
- **读法二（实现）**：把门禁从树上拿掉（恢复「没人守」），那两处过期就**回到静默**：
  `scripts/check-version-claims.py` 对 `docs/portfolio.md` 一条 finding 都不报
  （审计 §2 B1 的核法二），`check-release-numbers.py` 也不看这一页。
  **「没人守」不是一个状态，是一个缺口**——缺口补上时它红，是补对了的证据。

### 4.4 单测层面的红→绿

`tests/test_unguarded_numbers.py` 里也有一对：

- `test_a_watched_sentence_with_the_wrong_number_is_reported` —— 同一句话里的数
  换成 `1,999`，门禁报出「文档说 1,999 / 树说 1,733」；
- `test_the_same_sentence_with_the_right_number_is_silent` —— 换成树上的那个数，
  没有 finding。

---

## 5. 它抓得住「以后」的漂移吗

### 5.1 门禁算的是树，不是抄下来的数

`tests/test_unguarded_numbers.py::test_the_truths_come_from_the_tree_and_not_from_a_number_written_down`
扫门禁脚本的源码，确认里面没有 `== 13`、`== 11`、`== 1733`、`== 93.3` 这类写死的数。

### 5.2 加一个 CI job 会怎样（实测）

在 `.github/workflows/ci.yml` 末尾临时加一个 job，门禁立刻在**六处**散文上抓到：

```
FAIL CLAUDE.md:79            [ci-jobs-claude]    it says 13, and the ci_jobs is 14
FAIL AGENTS.md:79            [ci-jobs-agents]    it says 13, and the ci_jobs is 14
FAIL docs/portfolio.md:68    [ci-jobs-portfolio] it says 13, and the ci_jobs is 14
FAIL docs/status.md:26       [ci-jobs-status-table]  it says 13, and the ci_jobs is 14
FAIL docs/status.md:50       [ci-jobs-status-prose]  it says 13, and the ci_jobs is 14
FAIL docs/HANDOVER.md:148    [ci-jobs-handover]  it says 13, and the ci_jobs is 14
```

（加完 job 之后 `ci.yml` 已还原。）这正是审计 B4 说的那句：「**加一个 job 就全错，
而没有任何一处在等**」。现在有在等的了。

### 5.3 门禁在 CI 里跑

`check-gate-coverage.py` 的清单里登了它，CI 的 `release-numbers` job 里跑它。

**为什么不是 `lint` job**：`lint` job 在 `ci.yml` 的**上面**，在那儿加一个步骤会
把下面每一行都挪一位——而好几份报告引着那些行（`post-release-rehearsal.md`、
`docker-image-samples.md`、`ci-temp-redirect-fix.md`）。`ci-temp-redirect-fix.md`
那张表记的是**上一次**重映射把行号从哪儿挪到哪儿；把它的数字改成适配一棵它不
描述的树，那不是重映射，是改记录。**所以这道门禁放在文件里最后一个 job
（`release-numbers`）的末尾：它一行都不挪。**

---

## 6. **仍然没人守的**（这一栏不空）

| # | 仍然没人守的 | 为什么 |
|---|---|---|
| 1 | **B2 的那一次测量**：「没取第三方样本」环境下套件会跑成什么样 | 没有测量键，也没有那一次运行的成本预算。要守它得先有那一次测量。**处置是删掉具体数**，不是加门禁 |
| 2 | **B6 的实跑条数**（48 或 47） | 依**可用后端**而定。静态数守不住一个随环境变的数；页面自己已经把这个依赖写明了 |
| 3 | **B7 的分析产出表** | 一次管线运行的记录。要守它，得每次树变了都跑一遍五个样本的分析，然后让文档跟着变——那不是门禁，是一条每次都要付钱的流水线 |
| 4 | **B10 的说明列** | 一句「这个测试文件覆盖什么」是人的判断。正则守不了判断 |
| 5 | **`docs/outreach/` 里反引号包住的**历史列（「修正前」那一列，`~1,540 …`） | 它是**旧值**，本来就该旧。门禁只守「修正后」那一列 |
| 6 | **所有「数错了也没人看」的地方** | 门禁只守清单里点名的句子。清单是交付物：新增一句带数的句子，要在清单里加一行，否则没人守——**这一条靠人记得，靠 `check-gate-coverage.py` 之外的一道自觉** |
| 7 | **`docs/status.md` / `docs/portfolio.md` 里别的数**（本窗口没点到的） | 审计只列了十处；本窗口逐处读过那十处并配了门禁，但**别的文档里别的数有没有被抄错，不在这次的范围里** |

第 6 与第 7 条是这次工作**没有**解决的：门禁守住的是清单，清单之外的手写数，
仍然要靠人写下来时记得登记。

---

## 7. 本窗口改了什么

| 文件 | 改动 |
|---|---|
| `scripts/check-unguarded-numbers.py` | **新增**：门禁本体 |
| `scripts/unguarded-numbers.json` | **新增**：清单（25 条语句） |
| `tests/test_unguarded_numbers.py` | **新增**：11 条测试（红→绿、清单不烂、真值算得出来、两份真模型报告从 trace 重算） |
| `.github/workflows/ci.yml` | **加一个步骤**（在文件最后一个 job 的末尾）：跑新门禁。**没有加 job**——job 数变了，六处散文会跟着变，而那六处本窗口不碰 |
| `scripts/check-gate-coverage.py` | 清单里登了新门禁（加在字典的最后，`GATES` 那一行仍在第 48 行，引用它的文档不受影响） |
| `scripts/platform-gates.json` | `release-numbers` job 的 `gate_scripts` 加了它；`local_gates` 加了一条 |
| `docs/reports/phase1-execution-report.md` | **只加了一行**：测试文件表里补 `test_unguarded_numbers.py` 那一行。**表里的行是手写的**，而 `refresh-report-figures.py` 在写任何数字之前先比这张表——**不补这一行，主会话的重测会被挡住**（脚本会打印「The table's rows are written by hand」并一个数都不写）。表里的数一个没动 |

**本窗口没有碰**：`docs/how-to-verify.md` 与 `.zh-CN.md`、`docs/portfolio.md`、
`docs/status.md`、`CLAUDE.md`、`AGENTS.md`、`docs/outreach/`、
`docs/releases/v1.0.0.md`、`docs/reports/m10-*.md`、
`docs/reports/README.md`、`scripts/check-doc-citations.py`、
`scripts/refresh-report-figures.py`、`docs/reports/v1.1.0-candidates.md`。

§4.2 里那两处临时改动（`docs/portfolio.md`、`docs/outreach/publish-review.md`）
在提交前已用 `git checkout --` 还原，**不在提交里**。

**没有登记成候选**：`docs/reports/v1.1.0-candidates.md` 的结构是一轮一轮登记的
（每轮都要改 §0 的计数、§2 的分桶、§7 的基线表），而本窗口带出去的「不归自动管」
四项在本文 §6 已经逐条写清了理由与代价。**登记成候选是主会话的动作**：把它并进
C17（散文里的手写数）那一族最合适——C17 治的是「让散文里的数由测量写」，
本窗口治的是「剩下的数由谁守」。

---

## 8. 留给主会话

1. **合入后要重测一轮。** `scripts/` 与 `tests/` 在源码指纹的覆盖范围内，本窗口
   加了一个脚本、一个测试文件、11 条测试，报告里的测试数与指纹都过期了。
   `scripts/refresh-report-figures.py` **本窗口没有跑**（按指示留给主会话）。
   **测试文件表那一行本窗口已经补好了**（§7），所以重测不会被「The table's rows
   are written by hand」挡住——但表里的**数**要等这一轮重测来写。
2. **把那 11 条 finding 改对。** 门禁现在是红的，红的地方就是审计说的那几处真过期：
   `docs/portfolio.md:67` 的 `1,695`，以及 `docs/outreach/publish-review.md` 的
   最右列与「修正后」列。改的是**数**，不是门禁。改完之后门禁会绿（§4.2 实测过）。
   **逐行清单（文件、行、现在写的、应改成、依据）在 §9。**
3. **把这份报告登记进索引。** `docs/reports/README.md` 的分组与份数，
   以及 `scripts/check-doc-citations.py` 的 `DOCS` 白名单（登记之后本文的
   `file:line` 引用才会被检查）——这两处归主会话统一登记。
4. **两条主会话自己树上的红（本窗口没碰，也不该由本窗口碰）：**
   - `scripts/check-doc-citations.py` 报 **12 条** value drift，全在
     `docs/reports/v1.0.0-github-release-body.md`。**这是主会话自己合入
     「引用能验句中含值」那一扇之后新出现的**：本窗口在 `main`（`a785d01`）上
     单独跑过，同一个脚本、同一个 12 条——不是本窗口造成的。
   - `ruff format --check .` 说 `scripts/check-doc-citations.py` 与
     `tests/test_doc_citations.py` **两个文件要重排**。同样在 `main` 上单独
     跑过，一样——不是本窗口造成的。本窗口的文件 `ruff format --check` 全绿。
5. **全套 pytest 的状态：本分支没有新增任何一条红。**

   | | 本分支 | `main`（`a785d01`）单独跑 |
   |---|---|---|
   | 全套 | **14 failed / 1649 passed / 88 skipped / 17 errors** | — |
   | `test_how_to_verify.py` | 6 failed | **6 failed**（同一批） |
   | `test_evidence_package.py` | 1 failed | **1 failed**（同一条） |
   | `test_docs.py` | 3 failed | **3 failed**（同一批） |
   | `test_doc_citations.py` | 2 failed | **2 failed**（同一批） |
   | `test_androguard_integration.py` / `test_androguard_isolation.py` | 2 failed / 17 errors | 同上：fixture APK 没取回（`bash scripts/fetch-fixtures.sh` 没跑），CLAUDE.md 明写这种情况**失败而不是跳过** |

   `test_how_to_verify.py` 那 6 条值得单独说一句：**它在 `main` 上就已经红**——
   两页写的测试数是 1733，而 `main` 的树已经收集到 1757（本分支加了 11 条测试，
   收集到 1768）。这正是审计 §2 记着的那个闭环：「加一个测试 → 页面的数过期 →
   测试红 → 测量脚本拒绝写数」。**本窗口的 11 条测试没有引入它，也没有解开它**；
   解开它的是把那些数变成 `<!--fig:…-->`（散文改标记那一扇在做的），或者主会话
   在重测时一并处理。

---

## 9. 逐行同步清单（给最终那次统一同步用）

**这一节是给「把数字改对」这件事的输入**：每一处写清「文件、行、现在写的、
应改成、依据是哪次测量或哪个标记」。**依据是标记与命令，不是本文的断言**——
主会话同步时逐条核，不要照抄。

### 9.0 两个符号

| 符号 | 是什么 | 现在是多少（占位） | 当场怎么核 |
|---|---|---|---|
| `N` | 测试总数 | 报告 `<!--fig:tests.total-->` 现在记 **1733**（上一轮测量的落盘值）。本分支此刻 `pytest --collect-only -q` 收集到 **1768** | 重测后：`grep -o '<!--fig:tests.total-->[^<]*' docs/reports/phase1-execution-report.md`；或 `uv run --no-sync pytest --collect-only -q` 的最后一行 |
| `P` | 一方代码覆盖率 | 报告 `<!--fig:coverage.pct-->` 现在记 **93.3%** | 重测后：`grep -o '<!--fig:coverage.pct-->[^<]*' docs/reports/phase1-execution-report.md` |

**两个都是占位**：最终以主会话那一轮重测写进报告的值为准。**重测之前不要按
本文的数去改**——本文记的是「现在写的」和「依据在哪」，不是「最终是多少」。

### 9.1 表 A：现在就是错的（门禁报出来的 11 条，必须改）

| # | 文件 | 行 | 现在写的 | 应改成 | 依据 |
|---|---|---|---|---|---|
| A1 | `docs/portfolio.md` | 67 | `1,695 tests at` | `N tests at` | `<!--fig:tests.total-->` |
| A2 | `docs/outreach/publish-review.md` | 50 | 最右「落盘真值」列 `1,695 / 93.3%` | `N / P%` | `<!--fig:tests.total-->` + `<!--fig:coverage.pct-->` |
| A3 | `docs/outreach/publish-review.md` | 51 | 最右列 `1,695`（这一格没有百分数） | `N` | `<!--fig:tests.total-->` |
| A4 | `docs/outreach/publish-review.md` | 52 | 最右列 `1,695 / 93.3%` | `N / P%` | 同 A2 |
| A5 | `docs/outreach/publish-review.md` | 53 | 最右列 `1,695 / 93.3%` | `N / P%` | 同 A2 |
| A6 | `docs/outreach/publish-review.md` | 342 | `本轮的 1,695 / 93.3%` | `本轮的 N / P%` | 同 A2 |
| A7 | `docs/outreach/publish-review.md` | 406 | `（1,695 / 93.3%）` | `（N / P%）` | 同 A2 |
| A8 | `docs/outreach/publish-review.md` | 50 | 「修正后」列 `1,695 automated tests, 93.3% coverage` | `N automated tests, P% coverage` | 同 A2 |
| A9 | `docs/outreach/publish-review.md` | 51 | 「修正后」列 `1,695 tests, coverage and dead-code gates` | `N tests, coverage and dead-code gates` | `<!--fig:tests.total-->` |
| A10 | `docs/outreach/publish-review.md` | 52 | 「修正后」列 `1,695 tests at 93.3% coverage` | `N tests at P% coverage` | 同 A2 |
| A11 | `docs/outreach/publish-review.md` | 53 | 「修正后」列 `1,695 automated tests at 93.3% coverage` | `N automated tests at P% coverage` | 同 A2 |

**A8–A11 要注意**：那四格抄的是**素材里的话**。素材现在写的是 `1,733`
（`docs/outreach/project-brief.md:50`、`docs/outreach/cover-letter-templates.md:82`、
`docs/outreach/scope-backend-automation.md:24`）——**素材与这份校对记录已经对不上了，
门禁抓的就是这件事**。所以那四格要抄**素材改完之后真正写的那句话**，
不是在这里自己拼一个 `N`。

### 9.2 表 B：现在是对的，但重测后必须跟着核对

| 位置 | 现在写的 | 重测后 | 谁会报 |
|---|---|---|---|
| `docs/portfolio.md:68` | `93.3% coverage` | `P%` | 新门禁 `portfolio-coverage` |
| `docs/outreach/project-brief.md:50` | `1,733 automated tests, 93.3% coverage` | `N … P%` | `check-version-claims.py` 的 outward 规则 |
| `docs/outreach/cover-letter-templates.md:82` | `1,733 automated tests at 93.3% coverage` | `N … P%` | 同上 |
| `docs/outreach/scope-backend-automation.md:24` | `1,733 tests at 93.3% coverage` | `N … P%` | 同上 |
| `CLAUDE.md:79`、`AGENTS.md:79`、`docs/portfolio.md:68`、`docs/status.md:26`、`:50`、`docs/HANDOVER.md:148` | `thirteen` / `13` / `十三个` | 仍以 `ci.yml` 现算为准（**只有加了 job 才变**） | 新门禁 `ci-jobs-*` |
| `docs/portfolio.md:48`、`docs/HANDOVER.md:29`、`docs/status.md:256`、`docs/architecture/README.md:288` | `Eleven` / `eleven` / `十一个` | 仍以 `server.py` 现算为准（**只有加了 MCP 工具才变**） | 新门禁 `mcp-tools-*` |

### 9.3 改完怎么验

```bash
uv run --no-sync python scripts/check-unguarded-numbers.py
#   应输出：PASS 25 watched statements agree with the tree.
uv run --no-sync python scripts/check-version-claims.py --base auto
#   应输出：Every version claim matches the repository.
```

第一条是本窗口新加的门禁（红→绿实测过，§4.2）；第二条是主会话既有的对外文本门禁。
