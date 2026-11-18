# 测量数字自动覆盖：机制落地报告

**日期：** 2026-11-18 · **性质：** 实现报告（本轮新增这一个文件；另改了测量脚本与一个新测试文件，并按仓库自身的规矩补了报告的测试文件表一行、重新推导了两份文档里位移的行号）

**回答的问题：** 把 [《测量数字自动覆盖设计》](figures-coverage-design.md) 的结论落成哪一层、怎么落的、还剩什么。

---

## 0. 落在哪一层，为什么先落这层

调研的结论有三条对本轮有约束力：

- **不扩指纹**（调研 §2.2）：`src/`、`tests/`、`pyproject.toml` 与测量脚本之外的 `docs/`
  数字不能靠指纹管住——指纹只说明「代码变了」，不说明「某页上的数过期了」。
- **B 类纳入自动写、C 类只核对、D 类两者都不合适**（调研 §1.2–§1.4）：自动写只适合
  「这个数由一次测量决定」的位置；发版说明与 Release 正文是历史记录，自动改写就是篡改。
- **实施顺序是前三步**（调研 §3.7）：三步都是**核对**，第五步（`fig:ci.*`）标为可选。

本轮的边界是「**不迁移文档**」：改写 `docs/` 下那些引着数字的页面是后面的活。在这条边界内
能落、且落下来之后迁移才变便宜的，是**机制层**——两样东西：

| | 是什么 | 为什么是它 |
|---|---|---|
| **机制一** | **硬保险**：pytest 的汇总行读不出来时中止，并说清这一轮量到了什么、没量到什么 | 上一轮 tag 的测量 job 就是这么红的（把一轮 13 项、挂了 1 条的自检读成 **0 项**）。那一类「读不出来就当 0」不修，下一次解析失误会同样地静默 |
| **机制二** | **写入口**：脚本按标记发现**所有**带生成数字的文档并统一写；写不出的标记中止；历史/对外文档不写但要被点名 | 迁移的前提。在没有写入口之前，每迁移一页就要改一次脚本；有了它，迁移 = 加一个标记，脚本自己找到并写。手写数字「靠人记得同步」这个病根，只有在这一层立住之后才谈得上「自动」 |

**为什么先落机制层、而不是调研 §3.7 的前三步核对**：那三步都要先改文档才可能绿——
§3.1 要把三处 CI job 数改成实况，§3.2（把 `docs/portfolio.md` 纳入 outward 核对）会当场抓住
`docs/portfolio.md:67` 的 **1,695**（当前记录是 **1,712**，本来就过期），§3.3 要改
how-to-verify 的表格行。改文档这一轮不让做，所以它们做出来只能是红的。机制层不需要改任何
文档就能立住，且立住之后上面的核对与迁移才有地方落脚。

---

## 1. 机制一：读不出汇总行就中止

### 1.1 旧行为

`outcome_counts()` 在找不到 pytest 的汇总行时**退回整段输出**去数：

```python
summary = summaries[-1] if summaries else output  # 旧实现
```

于是一段没有汇总行的输出会被读成：

```
{'passed': 0, 'failed': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0, 'error': 0, 'deselected': 0}
```

0 是一个**测量**——「套件一项都没跑」——而读不出汇总行的这一轮并不是这项测量，它什么也没测。
把它当成 0 写进报告，就是发布一个描述着「不存在的套件」的数字。上一轮 tag 的测量 job 就是
这么红的：一轮 13 项、挂了 1 条的自检被读成 0 项 → 账目对不上树 → job 变红，而它给出的原因
（账目对不上）是错的。

### 1.2 新行为

- `outcome_counts()` 找不到汇总行 → 抛 `SummaryUnreadable`（**不再退回整段输出**）。
- `measure_tests()` 把异常原样传上去；`measure_code_tests()`、`measure_report_checks()`、
  `measure_status_checks()` 各自说明自己测的是哪一轮（「the suite」/「the report's
  self-checks」/「the status page's self-checks」）。
- `main()` 接住它，打印一份**账目**，然后以退出码 1 结束，**一个字都不写**。

账目长这样（`Ledger` 是这一轮新加的小结构：先 `expect()` 声明这一轮要建立哪些事实，走到哪一步
就 `note()` 记下哪一条）：

```
pytest's summary line could not be read out of the suite.
A count read as zero would say that no test ran at all, which is not what happened.

What this run measured:
  - the fingerprint of the tree: sha256:18f3ab15…
  - the tests the suite collects: 1721 (1572 fast, 149 integration)

What this run did not measure:
  - how many tests passed, failed, skipped or xfailed
  - which tests skipped or xfailed
  - the coverage of the tree

The last lines of the output:
  …

Nothing was written. The report still carries the figures of the previous measurement.
```

「量到了什么 / 没量到什么」是这个要求的字面兑现：**没量到的事实不会被写成 0**。

---

## 2. 机制二：数字随测量走

### 2.1 写入口：按标记发现文档

旧实现里脚本写死的只有两份文档：执行报告（`--report` 指过去的那份）与状态页（`render_status`）。
徽章另走一条 URL 正则的路。新实现加了一条**通用通道**：

- `live_figures(text)`：一份文档真正带着的图标记。**代码块里的标记是插图**（教读者看
  `<!--fig:…-->` 长什么样的那一段），**行内代码里的标记是句子**，两者都不是数字，不该被改写。
- `documents_with_figures(root)`：把仓库里的 markdown 找一遍，列出带图标记的那些。
- `write_figures(path, values)`：把测量值写进去；**写不出的标记中止**（沿用报告与状态页已有的
  那条规矩：「猜一个数比停下来更糟」）。
- `main()`：报告与状态页写完之后，其余带标记的文档也用同一批测量值写一遍；`--check` 也核对它们。

**这一层带来的直接后果**：迁移一页文档从此只是「加一个标记」的事，不需要再改脚本。调研 §1.2
里 B 类那几页（how-to-verify 的三个粗体数、status 的 CI 行）下一轮要做的就是这个。

### 2.2 不写、但要点名的地方

`FIGURE_EXCLUSIONS` 明确列出**不写**的两处，并写清为什么：

- `docs/releases/`：发版说明陈述「v1.0.0 那棵树测出什么」，是历史记录（调研 §1.3）。
- `docs/outreach/`：对外素材整段贴去别的平台，数字由 `check-version-claims.py` 对账
  （调研 §1.3），不由脚本改写。

历史记录里出现生成标记是**错误**，不是策略——所以有一条仓库级的闸门盯着它：

```python
def test_every_generated_number_in_the_repository_is_written_by_the_measurement():
```

它遍历仓库里的每一份 markdown，凡是带真标记的，就不许落在脚本不写的那两类目录里。
换句话说：**一个手写数字想躲在标记后面，唯一的办法是躲进一份历史记录，而那会被判红。**

### 2.3 边界：这一轮没有改任何 `docs/` 页面上的数字

机制立住了，**页面上的数字一个没动**。这正是本轮要的：机制先立住，迁移是后面的活。

---

## 3. 红 → 绿是怎么证的

新增 `tests/test_figures_auto_write.py`（9 个测试）。证法是**把旧实现放回去跑一遍**：

```bash
cp scripts/refresh-report-figures.py .scratch/refresh-new.py
git show HEAD:scripts/refresh-report-figures.py > scripts/refresh-report-figures.py
uv run --no-sync pytest tests/test_figures_auto_write.py -q
cp .scratch/refresh-new.py scripts/refresh-report-figures.py
uv run --no-sync pytest tests/test_figures_auto_write.py -q
```

旧实现下：

```
8 failed, 1 passed in 0.26s
```

——8 个红，1 个绿。那个绿的是 `test_a_run_that_prints_its_summary_line_is_still_counted`：
它是**反向的护栏**（新保险不许把能数的运行也拦下来），旧实现本来就数得对，所以它不红是应该的。

旧实现下那条最关键的保险测试为什么红，看得见：

```
E   AttributeError: module 'dexatlas_figures_auto_write' has no attribute 'SummaryUnreadable'
```

而旧实现对同一段输出的读数（当场打印）：

```
outcome_counts -> {'passed': 0, 'failed': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0,
                    'error': 0, 'deselected': 0}
```

——这就是「读不出来就当 0」的那个类别本身。

新实现下：

```
9 passed in 0.22s
```

八个测试逐条对应的性质：

| 测试 | 性质 |
|---|---|
| `test_a_run_whose_summary_line_cannot_be_read_is_not_read_as_zero` | 硬保险：不读成 0 |
| `test_a_run_that_prints_its_summary_line_is_still_counted` | 反向护栏：能数的照数 |
| `test_the_error_reaches_the_run_and_not_only_the_reader_of_the_output` | 异常一路传到测量，不只是解析器 |
| `test_the_run_says_what_it_measured_and_what_it_did_not` | 账目：量到了什么 / 没量到什么 |
| `test_a_figure_inside_a_code_block_is_an_illustration_and_not_a_figure` | 代码块/行内代码里的标记是插图 |
| `test_a_document_that_carries_a_figure_is_written_from_the_measurement` | 写入口：加标记即可，不用改脚本 |
| `test_a_figure_the_measurement_cannot_fill_stops_the_refresh` | 写不出的标记要中止 |
| `test_every_generated_number_in_the_repository_is_written_by_the_measurement` | 仓库级闸门：没有数字躲在标记后面 |
| `test_the_documents_the_measurement_writes_are_the_ones_that_carry_figures` | 报告与状态页确实走这条通道 |

---

## 4. 这一轮整套套件的状态

带着第三方 fixture（`bash scripts/fetch-fixtures.sh`）跑完整套：

```
9 failed, 1624 passed, 88 skipped in 306.02s (0:05:06)
```

**9 条红全部是预期的「数字过期」**，没有一条是本轮改动造成的回归：

| 红在哪 | 为什么红 |
|---|---|
| `tests/test_docs.py::test_execution_report_numbers_match_the_code` | `tests.total: the report says ['1712'], the code has 1721` |
| `tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code` | 覆盖率是另一棵树测的（`sha256:18f3ab15…` → `sha256:fbe76910…`） |
| `tests/test_docs.py::test_execution_report_suite_figures_add_up_to_the_tests_that_exist` | 报告说 1712，树里有 1721 |
| `tests/test_how_to_verify.py`（6 条） | 页面散文里的 1712/1563/149 与当场收集的 1721/1572/149 不一致 |

这 9 条要等合入后那一轮重测 + 页面同步（§6）才会消失——**在合入之前它们就该是红的**：
`scripts/` 与 `tests/` 都在指纹里，代码一变，报告里的数就过期。

**88 条 skip 要读清楚**：这个 worktree 里没装 Apktool 与 JADX（可选后端），跳过的正是那些要真调
后端的用例。按 CLAUDE.md 的规矩，skip 不是 pass——这一轮的数字属于「没装后端」的配置，
完整配置下的数字由合入后那一轮重测给出。

---

## 5. 这一轮改了哪些文件

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `scripts/refresh-report-figures.py` | 硬保险（`SummaryUnreadable`、`Ledger`、`abort`）+ 写入口（`live_figures`、`documents_with_figures`、`write_figures`、`FIGURE_EXCLUSIONS`）+ `figure_changes()` 改收 values | 本轮的主体 |
| `tests/test_figures_auto_write.py` | 新增，9 个测试 | 红→绿的证据 |
| `docs/reports/phase1-execution-report.md` | **只加了测试文件表的一行**（`| \`test_figures_auto_write.py\` | …`），行里没有数字 | 仓库自身的规矩：表与套件不一致时，测量脚本拒绝写报告（`test_file_table()` 与 `tests/test_docs.py::test_execution_report_lists_every_test_file`）。**不加这一行，主会话合入后就写不出报告了** |
| `docs/reports/post-release-rehearsal.md`、`docs/reports/docker-image-samples.md` | 7 处 `file:line` 引用由 `scripts/remap-citations.py` 重新推导（脚本行号位移） | CLAUDE.md 第 4 条；`check-doc-citations.py` 要求 `drifted: 0` |

**没有动**：`docs/` 下引着数字的那些页面（机制先立住，迁移是后面的活）、`docs/reports/README.md`
与 `scripts/check-doc-citations.py`（主会话统一登记）、`scripts/check-release-numbers.py` 与
`tests/test_release_numbers.py`、`tests/test_docker_image_samples.py`（另一个窗口在改）。

---

## 6. 哪些数字需要重测后同步

**本轮没有跑 `scripts/refresh-report-figures.py`**（并发测量会互相污染覆盖率），也**没有手改任何
数字**。以下清单是合入后那一轮重测要处理的：

### 6.1 脚本会自己写的（重测后自动同步）

| 位置 | 现在的值 |
|---|---|
| `docs/reports/phase1-execution-report.md` 的全部 fig 标记与 `<!--report-figures:{…}-->` 记录 | 1712 / 1710 passed / 1 skipped / 93.3% |
| `docs/status.md:23-24` 的快照表 | 同上 |
| 两份 README 的徽章（`README.md:12-13`、`README.zh-CN.md:12-13`） | tests-1710 passing / coverage-93.3% |

这一轮新增的测试文件让**收集数变了**：现在 `pytest --collect-only` 报
**1572/1721 tests collected (149 deselected)**（改之前是 1563/1712）。所以上面三处一定会动。

### 6.2 要人手同步的（脚本不碰，因为它们是散文里的数字）

| 位置 | 现在写的 | 该是多少 | 谁来改 |
|---|---|---|---|
| `docs/how-to-verify.md:147` 的散文三数（**1712** / **1563** / **149**）与 `:153-154` 的两条 collect 期望输出 | 1712 / 1563 / 149 | 1721 / 1572 / 149 | 主会话（合入后） |
| `docs/how-to-verify.zh-CN.md:120` 同上、`:126-127` 两条期望输出 | 同上 | 同上 | 主会话 |
| `docs/portfolio.md:67` | `1,695 tests at 93.3% coverage` | 记录里是 1712 —— **这一条在本轮之前就已经过期**（调研 §0 实测抓到的盲区：portfolio 不在 `OUTWARD_DIRECTORIES` 里） | 主会话（连同调研 §3.2 把 portfolio 纳入 outward 核对） |
| `docs/status.md:26` / `:50`、`CLAUDE.md:79` / `AGENTS.md:79`、`docs/portfolio.md:68` 的 CI job 数 | 9 个 job / 10 次并行（status）、twelve jobs（CLAUDE.md、portfolio） | `ci.yml` 现在是 **13 个 job**（tag 上 14 次并行） | 主会话（调研 §3.1 + §3.5） |

`docs/how-to-verify.md` 那两页的散文数字由 `tests/test_how_to_verify.py` 盯着，它拿**当场收集**
的数与页面比对，所以新增测试文件之后它会红——这是预期的，直到页面被重新同步。

---

## 7. 剩下什么留给主会话

按调研 §3.7 的顺序，本轮没落的：

1. **§3.1 `tests/test_ci_shape.py`**：把 CI job 数锚住。纯新增测试，但要绿就得先改三处文档的
   数字（`docs/status.md:26`/`:50`、`CLAUDE.md:79`、`docs/portfolio.md:68`），本轮不动文档。
2. **§3.2 把 `docs/portfolio.md` 纳入 outward 核对**：改 `scripts/check-version-claims.py` 一处
   判断即可，但 `docs/portfolio.md:67` 现在写的是 1,695、记录里是 1712 → 加进去当场红 → 必须先
   同步页面（见 §6.2）。
3. **§3.3 how-to-verify 的 skip 表格核对**：要改那两页的表格行。
4. **§3.5 `fig:ci.jobs` / `fig:ci.runs`**：`docs/status.md` 的 CI 行改由标记供给。机制已经就位
   （脚本会写任何带标记的文档），剩下的是把那两个数字变成标记 + 在 `build_record()` 里解析
   `ci.yml`。
5. **本轮新增报告的登记**：`docs/reports/README.md` 的索引与 `scripts/check-doc-citations.py`
   的 `DOCS` 清单由主会话统一登记（文件名：`docs/reports/figures-auto-write-landing.md`）。
6. **合入后重测一轮**：见 §6。测量脚本与 `tests/` 都在指纹里，所以**合入前 main 的 CI 会因为
   数字过期而红**，这是预期的。

---

## 8. 本窗口做的 / 留给主会话

**本窗口（`claude/exciting-gauss-35fa92`）做的：**

- 硬保险：pytest 汇总行读不出来 → 中止 + 说清量到了什么、没量到什么（`SummaryUnreadable`、
  `Ledger`、`abort`），并把「读不出来就当 0」这个类别从根上关掉。
- 写入口：脚本按标记发现所有带生成数字的文档并统一写；写不出的标记中止；代码块与行内代码里
  的标记不当数字；历史与对外文档不写、但被仓库级闸门盯着。
- 红→绿：新增 9 个测试，旧实现下 8 红 1 绿（新保险不许误伤能数的运行），新实现下 9 绿；并当场
  打印了旧实现把读不出汇总行的输出读成全 0 的实况。
- 报告的测试文件表加一行（不含数字，仓库自身的门禁要求）；两份文档的引用行号按规矩重新推导。
- 整套套件带 fixture 跑完：**9 红 1624 绿 88 跳过**，9 条红全是预期的数字过期（§4），没有一条
  是本轮改动造成的回归；门禁（ruff / format / mypy / vulture / 引用 drifted: 0 / 版本 claims
  退出 0）全绿。

**留给主会话：**

- 合入后**重测一轮**（`scripts/refresh-report-figures.py`），让报告、状态页与两份 README 徽章
  重新落数——**这是本窗口唯一没做的事，也是合入前必须做的事**（`scripts/` 与 `tests/` 都在指纹里，
  合入前 main 的 CI 会因为数字过期而红，这是预期的）。
- 同步 §6.2 里那三处人手数字：how-to-verify 两页的散文三数与 collect 期望输出、portfolio 的
  1,695、status 与 CLAUDE.md 的 CI job 数。
- 调研 §3.1–§3.3、§3.5 四步核对，以及本报告在 `docs/reports/README.md` 与
  `scripts/check-doc-citations.py` 里的登记。
