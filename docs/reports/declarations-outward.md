# 把「引用带声明」推到对外文本

**这一批做了什么**：`scripts/check-doc-citations.py` 的「只指位置」的引用，在
**对外文本**里现在全都自带声明——一条引用后跟一个 `anchor:` 跨度，装着一个
稳定的名字或源码片段，机器拿它去比被引的那一段。

**它没有做什么**：没有改任何测量数；没有动 `src/`、`tests/`、`scripts/`；
没有碰 `docs/reports/v1.0.0-github-release-body.md`（主会话正在按语义重锚它）。

---

## 0. 结论速览

| | |
|---|---|
| 改了的文档 | **7 份**（对外文本） |
| 加的声明 | **208 处**，覆盖这 7 份里**全部**「只指位置」的引用 |
| 重锚（把引用移到它该指的地方） | **80 处**：术语表 59 · 基准报告 13 · 提案 7 · 层级 3 复测 1 |
| 实测出「原本就指错」的地方 | **11 处**名了符号却指着别处（8 个位置）＋ **8 处**术语已从目标文件里消失 |
| 给定的候选名单 | **七份文件里一条 `file:line` 引用都没有** —— 实际改的是另一批（§2） |
| 门禁 | ruff / ruff format / mypy / vulture / 版本声明 **全绿**；`check-doc-citations.py` 的 16 处漂移是**本批之前就在的**，本批一条没加、也没减（§7） |

**一句话**：对外文本里现在**没有一条沉默的引用**了——每条引用要么名了符号
（机器验名字在不在），要么带了声明（机器验那段是不是还装着它声称的东西）。

---

## 1. 声明的形状

一条引用带一条声明：

`` `src/dexatlas/cli/main.py:289-291` `anchor: version` ``

声明是一个反引号跨度，内容以 `anchor:` 开头（`scripts/check-doc-citations.py:526`
`anchor: DECLARATION = re.compile`）。裸名字走结构化查法
（`scripts/check-doc-citations.py:2004` `anchor: def check_anchor_name`），
其余走字面查法（`scripts/check-doc-citations.py:2036`
`anchor: def check_anchor_fragment`）。

试点在契约表（`docs/architecture/public-contracts.md:22`
`anchor: dexatlas version`），形式与判据见
`docs/reports/citation-anchor-declarations.md:1`
`anchor: # 让「只指位置」的引用自己声明它声称的内容`。本批沿用同一形式。

---

## 2. 给定的候选名单与仓库现状

作者给的候选是七份文件：**发版说明、邀请函、读者包、准备包、记录模板、
两份 how-to-verify、`docs/outreach/` 下那几份**。逐份核过一遍，
**这七份文件里一条 `file:line` 引用都没有**：

| 候选 | `file:line` 引用数 |
|---|---|
| `docs/releases/v1.0.0.md` | 0 |
| `docs/reports/m10-invitation-final.md` | 0 |
| `docs/reports/m10-reader-package.md` | 0 |
| `docs/reports/m10-acceptance-pack.md` | 0 |
| `docs/reports/m10-review-record-template.md` | 0 |
| `docs/how-to-verify.md` | 0 |
| `docs/how-to-verify.zh-CN.md` | 0 |
| `docs/outreach/` 下 5 份 | 0 |

它们用的是**普通 Markdown 链接**（`[公共契约 §8.1](../architecture/public-contracts.md)`），
不是带行号的引用。链接检查器管得了它们，行号声明管不着——**没有东西可改**。

按「读者会照着它核对」这条判据，仓库里真正有「只指位置」引用的**对外文本**
是另外 7 份，本批改的就是它们。

---

## 3. 改了什么

| 文档 | 声明 | 重锚 | 说明 |
|---|---|---|---|
| `docs/glossary.md` | 172 | 59 | 术语表：读者查词的第一站 |
| `docs/proposals/exit-code-partial-read.md` | 15 | 7 | 退出码提案（已实施，保留为原文） |
| `docs/benchmarks/m6-level2-failure-analysis.md` | 13 | 13 | M6 层级 2 失败分析 |
| `docs/architecture/evidence-invariants.md` | 5 | 0 | 证据不变量 |
| `docs/analysis-provenance.md` | 1 | 0 | 出处模型 |
| `docs/benchmarks/m6-level3-recheck.md` | 1 | 1 | M6 层级 3 复测 |
| `CHANGELOG.md` | 1 | 0 | 版本号落点 |
| **合计** | **208** | **80** | |

改完之后，这 7 份里「只指位置」的引用**一条不剩**，检查器的全部判据**零
findings**（怎么验的见 §6）。

---

## 4. 锚点的挑法

**一条硬约束**：锚点里没有行号，也没有数字。行号会漂，测量重写数字后数字
也会过期；锚点写的是**被引的那一段里有什么**，由内容定位。

按这个约束，锚点分三类，**从强到弱**：

1. **名字**（11 处）：文件里**定义**它的那个符号。`__version__`、
   `EvidenceBuilder`、`ProjectResponse`、`RunResponse`、
   `index_completeness`、`test_the_cli_exit_code_table_is_the_contract`。
   这是最强的一种——机器拿它跟 AST 对。
2. **术语本身**（术语表的大头）：术语表那一列写的正是「这个词在哪出现过」，
   所以**锚点就是那个词**。`源指纹`、`重测量`、`分层`、`线索`。
   词不随行号漂，也不随数值漂。
3. **源码片段**（其余 197 处）：被引那一行里的一段**逐字**的话。
   `Deterministically established by an analysis tool`、
   `for wanted in task.must_contain:`、`exit_code = 0`、
   `<!--fig:coverage.weak_modules-->`。

**为什么片段也不算漂**：检查器比的是「这段文字**逐字**在不在被引的范围里」
（`scripts/check-doc-citations.py:2036` `anchor: def check_anchor_fragment`）。
代码往上挪十行，片段一个字都不用改；而行号要改——行号正是机器能验的东西。
片段被改写时，机器会报出来。

**不用什么**：行号（会漂）、测量出来的数字（会过期）、只在这份文档里成立的
措辞（换个人读就没了）。

---

## 5. 实测出来的东西

这一批是「只改形状」，但**加了声明就等于给每一处引用装了一台照妖镜**——
原来没人问的问题，现在被问了。问出来的东西里有真发现。

### 5.1 术语表的 139 条引用，在引用约定下指向空处

术语表在 `docs/` 里，所以它写的是「`reports/ci-gate-coverage.md` 加一个行号」
这种**按 `docs/` 相对**的路径——那是**链接**的写法，不是**引用**的写法。
仓库里其余的引用都是**按仓库根相对**的（`src/dexatlas/...`、
`scripts/...`、`docs/reports/...`）。检查器按仓库根解析，于是术语表里
**139 条引用一条都解析不到**——它从来没被机器看过。

本批把**全部 172 条**都**改写成仓库根相对**（路径前面补上 `docs/`）。这是纯粹的
形状改动：一个字没少，读者照着走还是同一处，但机器现在能读它了。

> 这一条对主会话有直接影响：`docs/glossary.md` 现在**可以**被登记进
> `scripts/check-doc-citations.py` 的 `DOCS` 名单（该名单见
> `scripts/check-doc-citations.py:271` `anchor: DOCS`）。
> 登记之前它不在名单里，所以它一条引用都没被检查过。

### 5.2 术语表的 59 条引用，指着的行上已经没有那个词了

那一列声称的是「这个词在这几份文件里的**首次出现处**」。逐条比下来，
**59 条指向的行上今天已经没有那个词了**——词在代码/文档改动中挪了位，
行号没跟着走。距离从 1 行到 453 行不等（58 条在「出现位置」那一列，
1 条在最后一栏）。

本批把这 59 条**重锚**到「离原位最近、且今天确实写着那个词」的行，锚点写
那个词。术语表最后一栏重复的那些行号也跟着一起挪，两列因此还对得上。

> **留给人的**：重锚只挪了**指针**，没有重判那一栏的「是 / 否 /（已补）」——
> 那是判断，不是位置。34 行受影响的判断需要人重看一眼。
> 另有一处**本来就对不上**：术语表「独占测量」一行的第四栏指着
> `release-process-dry-run.md` 的第 194 行，第五栏却写着「dry-run:167 是
> （已补）」。**两栏在改之前就不一致**，本批没有动它。

### 5.3 8 条引用的目标文件里已经没有那个词了

| 术语 | 引用 | 声明（碎片） |
|---|---|---|
| 独占测量 | `docs/reports/v1.0.0-release-checklist.md:353` `anchor: 2026-11-16 完成一次本地 dry-run（不创建 tag、不发布、不改版本号），逐项预演` | `2026-11-16 完成一次本地 dry-run…` |
| 独占测量 | `docs/reports/coverage-guard-audit.md:86` `anchor: P0 每次运行独占` | `P0 每次运行独占` |
| 弱模块表 | `docs/reports/phase1-execution-report.md:89` `anchor: <!--fig:coverage.weak_modules-->` | `<!--fig:coverage.weak_modules-->` |
| 只读演练 / 只读复核 | `docs/reports/reader-dry-run.md:1` `anchor: M10 独立验收 —— 读者流程实跑报告（reader dry run）` | 同左 |
| 两棵树（发布树 / 当前树） | `docs/reports/release-process-dry-run.md:257` `anchor: 「静态 49 条」加断言` | `「静态 49 条」加断言` |
| 两棵树（发布树 / 当前树） | `docs/reports/v1.0.0-release-checklist.md:102` `anchor: 已知限制 §8.1 表述与代码一致**：仅当` | 同左 |
| 冻结纪律 | `docs/architecture/README.md:204` `anchor: The frozen discipline.** The rule the acceptance plan` | 同左 |
| 报告三件套 | `docs/benchmarks/m6-verify3-plan.md:125` `anchor: 后端路径随执行环境而定（历史值见 m6-level2-retest4.md 复现命令），以后端检查三件套齐全为准` | 同左 |

这 8 处**没有重锚**：那个词在目标文件里**一个字符都不剩**（不是挪了位，是
文件不再用这个词了）。重锚要有一个地方可指；这里没有。给它们的声明是**碎片**
——声明「这一段装着这句话」，不是「这一段装着那个词」。

**这八处需要人决定**：是那一行当初就不该写这个文件（该另指一处），还是
那一行该换成**另一个文件**里的同一概念。机器答不了。

### 5.4 11 处「名了符号」的引用，指着别处

这类引用本来就有名字可对，机器一直在问，只是**这些文档不在检查器的
`DOCS` 名单里**，所以没被问过。逐条重锚（**11 处引用，8 个位置**）：

| 文档 | 原来指着 | 现在指着 | 依据 |
|---|---|---|---|
| `docs/proposals/exit-code-partial-read.md` | main.py 的 91–123 行 | `src/dexatlas/cli/main.py:93-141` `anchor: EXIT_NO_INDEX` | 五个退出码常量现在在 93–135；新常量 `EXIT_NO_INDEX = 6` 在 135 |
| 同上 | main.py 的 161–174 行 | `src/dexatlas/cli/main.py:173-186` `anchor: def _truncated(result: AnalysisResult) -> bool:` | 判定函数 `_truncated` 现在在 173–186 |
| `docs/benchmarks/m6-level2-failure-analysis.md` | model.py 的 345 行（2 处） | `benchmarks/model.py:430` `anchor: check` | `check()` 现在在 430 |
| 同上 | systems.py 的 234 行（2 处） | `benchmarks/comparison/systems.py:244` `anchor: grounded=False` | 断言现在在 244 |
| 同上 | model.py 的 356 行 | `benchmarks/model.py:464-465` `anchor: if task.expect_empty:` | `expect_empty` 的判分现在在 464 |
| 同上 | model.py 的 414 行 | `benchmarks/model.py:525` `anchor: if task.expect_count is not None and len(answer.findings) != task.expect_count:` | `expect_count` 的判分现在在 525 |
| 同上 | run.py 的 211 行（2 处，**空行**） | `benchmarks/comparison/run.py:222` `anchor: Configuration.FULL` | 原来那一行是空的；`Configuration.FULL` 在 222 |
| 同上 | partial.py 的 255 行 | `benchmarks/tasks/partial.py:238` `anchor: must_not_contain` | `must_not_contain` 现在在 238 |

### 5.5 另 10 处「只指位置」的引用，也指着别处

| 文档 | 原来指着 | 现在指着 | 依据 |
|---|---|---|---|
| `docs/proposals/exit-code-partial-read.md` | main.py 的 334–352 行（2 处） | `src/dexatlas/cli/main.py:401-408` `anchor: exit_code = 0` | 「成功分支给 0」就是 `exit_code = 0`，现在在 408 |
| 同上 | main.py 的 354–369 行 | `src/dexatlas/cli/main.py:404-420` `anchor: output.write_text(render_markdown(result), encoding="utf-8")` | 报告写出的那几行现在在 404–420 |
| 同上 | main.py 的 71–78 行 | `src/dexatlas/cli/main.py:72-81` `anchor: epilog=(` | epilog 现在到 81 行 |
| 同上 | install.md 的 206–223 行 | `docs/install.md:254-266` `anchor: ### Exit codes` | 原来指着取 fixture 的脚本，不是退出码表 |
| `docs/benchmarks/m6-level2-failure-analysis.md` | model.py 的 377 行 | `benchmarks/model.py:485-488` `anchor: for wanted in task.must_contain:` | `must_contain` 的判分现在在 485 |
| 同上 | systems.py 的 475 行（**空行**） | `benchmarks/comparison/systems.py:543-545` `anchor: EvidenceKind.BEHAVIOUR` | 只有 BEHAVIOUR 类记录进入结论，现在在 543–545 |
| `docs/benchmarks/m6-level3-recheck.md` | tool_executor.py 的 243 行 | `src/dexatlas/agent/tool_executor.py:251-253` `anchor: find_resource_declarations` | 工具注册表现在在 251–253 |

其中一处**改了措辞**：提案里那句「（与 main.py 93–135 行的五个常量并列）」
改成「（与 main.py 93–135 行**中的其余**五个常量并列）」——新范围里是**六个**
常量（五个旧的加新加的那个），不写「其余」这句话就不成立。这是本批唯一
一处改句子。

**一处要提醒读者**：提案与基准报告是**那几轮当时的记录**。今天代码变了，
所以这几处指针指向的是**今天的代码**；读者看到的是「这条后来被修了」，而
不是「这条当时就是这样」。这是「指针指向当下」这一选择的代价，写在这里
以免被当成「报告当时就长这样」。

---

## 6. 怎么验的

**这台机器上没有第二个检查器**：`scripts/check-doc-citations.py` 的 `DOCS`
名单由 `collect_documents()` 自动收集（`scripts/check-doc-citations.py:227`
`anchor: def collect_documents`），本批**不能动那个文件**。
所以本批借了检查器自己的机器，写了一个只读脚本（放在 `.scratch/`，
不进仓库）：它 `import` 检查器、用**同一套判据**跑这 7 份文档。

```
docs/glossary.md: 91 clauses, named=0 declared=172 loc-only=0   no findings
docs/proposals/exit-code-partial-read.md: 27 clauses, named=23 declared=15 loc-only=0   no findings
docs/benchmarks/m6-level2-failure-analysis.md: 25 clauses, named=12 declared=13 loc-only=0   no findings
docs/architecture/evidence-invariants.md: 3 clauses, named=0 declared=5 loc-only=0   no findings
docs/analysis-provenance.md: 81 clauses, named=89 declared=1 loc-only=0   no findings
docs/benchmarks/m6-level3-recheck.md: 2 clauses, named=1 declared=1 loc-only=0   no findings
CHANGELOG.md: 1 clauses, named=0 declared=1 loc-only=0   no findings

TOTAL findings: 0
```

**这 7 份文档现在可以被登记进 `DOCS`**——登记之后，检查器对它们说的就是
上面这同一段话。

**门禁**（`uv run --no-sync`）：

| 门禁 | 结果 |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 409 files already formatted |
| `mypy` | Success: no issues found in 68 source files |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | 退出 0 |
| `scripts/check-version-claims.py --base auto` | Every version claim matches the repository |
| `scripts/check-doc-citations.py` | **16 处漂移，本批之前就在**（§7） |
| `scripts/remap-citations.py` | 0 citation(s) moved（本批改的文档不在 `DOCS` 名单里，remapper 不碰它们） |
| `pytest tests/test_docs.py tests/test_doc_citations.py` | 6 failed / 100 passed —— **那 6 条在本批之前就红** |

**那 6 条失败是本批之前就在的**：把工作区还原成 `HEAD`（本批的 8 个文件全部
拿掉）再跑一遍，**同样的 6 条**红、同样 100 条过——它们分别是执行报告的数字
过期（3 条，主会话要重测）、`check-doc-citations.py` 的 16 处漂移（1 条）、
release body 的树（1 条）、以及一条本来就断的相对链接（1 条，`docs/reports/`
下别的窗口的报告里）。本批没有让任何一条变红，也没有让任何一条转绿。

**没有跑** `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率）。
本批**没改任何 `.py`**，源码指纹不变，所以不需要重测。

---

## 7. 剩下的没改的，以及为什么

| 没改的 | 有多少 | 为什么 |
|---|---|---|
| 给定的候选名单那 7 份 | 全部 | 它们一条 `file:line` 引用都没有（§2） |
| `docs/reports/` 下的报告 | 1000+ | **历史记录**——「一次检查留下的一份记录」。它们的引用描述的是当时那棵树，不会漂 |
| `docs/reports/v1.0.0-github-release-body.md` | 60 | **主会话正在按语义重锚它**，会撞 |
| 术语表里 8 处词已消失的引用 | 8 | 目标文件里没有那个词可指了；要人决定（§5.3） |
| 术语表 34 行受影响的「是 / 否」判断 | 34 | 那是判断不是位置，机器不该替人重判（§5.2） |
| `docs/status.md`、`docs/portfolio.md` | — | **另一扇窗口在改** |
| 检查器现有的 16 处漂移 | 16 | 见下 |

### 那 16 处漂移

`scripts/check-doc-citations.py` 在本批**开始之前**就已经报 16 处漂移，
本批**一条没加、也没减**（同一批条目，同一个数量）。它们全在两份**别的窗口
的报告**里：

- `docs/reports/citation-anchor-declarations.md`：6 处（3 处声明成了孤儿、
  1 处指着空行、1 处 `DECLARING_DOCUMENTS` 挪了位、1 处锚点不在范围内）；
- `docs/reports/handwritten-numbers-audit.md`：10 处（其中 4 处**指错了文件**
  ——声称的是 `scripts/check-release-numbers.py` 里的符号，却指着
  `docs/how-to-verify.zh-CN.md`、`docs/outreach/publish-review.md`、
  `docs/status.md`；另有 2 处行号超出文件长度）。

这两份报告不是本批的文件（brief 说只提交自己的文件），而且
`citation-anchor-declarations.md` 那一扇窗口**还在跑**。**主会话合并时需要
先把这 16 处处理掉**，否则 `check-doc-citations.py` 一直是红的。

---

## 8. 主会话要知道的

1. **`docs/glossary.md` 可以登记进 `DOCS`**——它的 172 条引用现在都能解析、
   都能被验。登记前请先读 §5.1：它的 139 条引用此前**从来没有被检查过**。
2. **`docs/reports/README.md` 的份数要从 89 改成 90**（本批新增一份报告）。
   那个文件归主会话，本批没动。
3. **那 16 处漂移要先清掉**，否则 `check-doc-citations.py` 一直红（§7）。
4. **本批没改任何 `.py`**，源码指纹不变，不需要重测
   `scripts/refresh-report-figures.py`。
5. **术语表那 8 处与 34 行需要人过一遍**（§5.2、§5.3）：机器能把指针摆正，
   判断是人做的。
