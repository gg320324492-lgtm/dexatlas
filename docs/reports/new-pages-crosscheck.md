# 新增两页的交叉校对（只读）

**校对日期：** 2026-11-17 · **性质：** 只读复核
**被校对象：**

| # | 文本 | 位置 | 本轮引入 |
|---|---|---|---|
| 1 | 怎么自己复核 DexAtlas 说的每句话 | `docs/how-to-verify.md`（427 行） | 提交 `7607b83` + `b25068a`，合并于 `e5060af` |
| 2 | `docs/reports/` 索引 | `docs/reports/README.md`（155 行） | 提交 `b3b2a63`，合并于 `d3dee74` |
| 3 | README 的入口指路（三行） | `README.md:462`–`:464` | 合并于 `e5060af` |

**基线：** `e5060af`（本次校对的 worktree 与共享树 HEAD 相同）。
**范围：** 只核这三处；不核它们引用的报告本身的内容质量。

---

## 0. 方法与边界

**做了什么。**

- 把三处的**每一个**相对链接与页内锚点解出来，用标题文字逐个核对锚点（不只是看文件在不在）。
- 把两页出现的**每一个**数字追到落盘出处（脚本源码、契约表、报告的 `<!--fig:…-->` 标记、git 对象）。
- **实跑**了 `how-to-verify.md` 里纯只读的那些命令，逐字比对页面写的输出。
- 把两页的每句话与本轮后续修正（`0403847`、`a3bbd3c`、`c4785ee`、`02e6d9c`）的落盘结果对一遍。

**没做什么（硬边界）。**

- 未运行 `pytest --cov`、任何 `coverage` 命令、`uv sync`、`scripts/refresh-report-figures.py`；
  因此覆盖率 93.3%、测试数 1,588 一律按已归档的测量值引用，不重测。
- 未修改被核的任何一份文件；本次只新增本文件。
- 未向共享树 `E:\Dexatlas` 写入任何内容。

**环境说明（影响可复现性，如实写出）。** 本 worktree 自带的 `.venv` 是空壳（无 pytest / dexatlas），
而 `uv sync` 被禁止，因此实跑改用主树 `E:\Dexatlas\.venv` 的解释器，并用 `PYTHONPATH`
把 `import dexatlas` 指回**本 worktree 的 `src/`**。两个 HEAD 同为 `e5060af`，`src/` 逐文件
一致（仅行尾 CRLF/LF 之差）。契约活检的后端从共享树 `.scratch/backends/` 只读引用，
脚本自身的写盘位置由 `REPOSITORY_ROOT` 推导，落在本 worktree 的 `.scratch/` 里。

---

## 1. 链接与路径

**结论：没有失效链接，没有指错的锚点。**

| 位置 | 问题 | 依据 | 建议改法 |
|---|---|---|---|
| `docs/how-to-verify.md`（41 个相对链接，0 个页内锚点） | 无 | 逐个解相对路径后确认目标存在；页面引用的每个小节（§1.2 / §1.3 / §6 / §4 / §7 / §8 等）按标题文字核对存在 | — |
| `docs/reports/README.md`（65 个相对链接 + 7 个页内锚点） | 无 | 7 个锚点全部按**标题文字**重算 slug 后命中：`#1-执行评审与阶段结论phase-12`、`#2-m4--m8-验收与模型可禁用性`、`#3-里程碑与对外准备度`、`#4-m10-独立验收材料`、`#5-v100-发版材料`、`#6-本轮审计与走查2026-11-17`、`#7-历史记录不要当现状读` | — |
| `README.md:462` | 无 | `docs/how-to-verify.md` 存在 | — |

核对方法与结果留痕：`.scratch/check_links.py`（本 worktree 内，未进仓库）逐行解出全部
markdown 链接（方括号文字 + 圆括号目标），`dest` 含锚点时按 GitHub 的 slug 规则
（转小写、去标点、空格转连字符）重算目标文件的标题集合再比对。**锚点全部命中**，
`docs/reports/README.md` 的 65 条链接（含 7 条页内锚点）全部指向真实存在的位置。

**但「路径」这一半本来就有门禁，「锚点」这一半没有。** 仓库里有一条相对链接门禁
`tests/test_docs.py::test_all_relative_links_resolve`：它遍历仓库里**每一份** Markdown
（含这两页），把每个链接的目标切掉 `#fragment` 之后检查文件是否存在——所以这三处的
**路径**早就有机器保证；它**不检查锚点**，这正是本次手工核对锚点的原因。
（本报告本身也被这条门禁覆盖：写完后跑一次 `pytest tests/test_docs.py` 确认新文件不引入坏链。）

---

## 2. README 那一行指路

新增的三行：

```
- **[How to verify every claim]** — the commands to re-check this
  project's own numbers yourself, what you should see, and which claims are not met
  (Chinese; 怎么自己复核这个项目说的每句话)
```

（原文里 `[How to verify every claim]` 是一个指向 `docs/how-to-verify.md` 的 markdown 链接；
这里把目标写成文字，是因为**本文件位于 `docs/reports/`，从这儿写 `docs/how-to-verify.md`
会被仓库的相对链接门禁判成坏链**——从 `docs/reports/` 出发它应是 `../how-to-verify.md`。）

**优点：** 说清了「有三样东西」——**有哪些命令**、**该看到什么**、**哪些说法没做到**；
并按本仓库既有惯例标注了语言。与其上下几行（`Installation` / `Current status` /
`Analysis coverage & provenance` / `Roadmap`）格式一致，位置也合理（放在「当前状态」之后、
「出处」之前）。

**缺口如下。**

| 位置 | 问题 | 依据（file:line 或实跑输出） | 建议改法 |
|---|---|---|---|
| `README.zh-CN.md:368`–`:371` | **中文 README 没有对应的一行。** 英文 README 的文档清单是 5 条（安装指南 / 当前状态 / 怎么复核 / 出处 / 路线图），中文 README 只有 4 条，缺的正是新增那条。中文读者点不到这一页。 | `README.zh-CN.md:368`–`:371` 与 `README.md:459`–`:467` 逐行对照 | 在 `README.zh-CN.md:370` 前后补一行：「**[怎么自己复核这个项目说的每句话]**（链接目标是 `docs/how-to-verify.md`，相对仓库根）—— 自己复核本项目每个数字的命令、应该看到什么、以及哪些说法尚未达成」。本仓库自己的 `final-outward-consistency.md` §3 就有「I 组 —— 中英对等」这一组，说明这条规矩是成立的。 |
| `README.md:462`–`:464` | 没有说**前置条件**。访客读完这一行去跑，第一件事是 `uv sync`，然后就卡在「后端不在 PATH 上、测试全 skip」上，而这一页自己的 §0 第 3 条才是答案。 | `docs/how-to-verify.md:19`–`:23`、`:72`–`:103` | 该行末尾加半句「needs a JDK and the three analysis backends」。 |
| `README.md:462`–`:464` | 「which claims are not met」指向的是页内 §3，但没给锚点；访客不知道要滚到哪一节。 | §3 标题是「3. 哪些说法目前是「未达成 / 未验证」，请据此打折」，锚点为 `#3-哪些说法目前是未达成--未验证请据此打折` | 行尾补一个页内锚点，或把描述改成「…and §3 lists which claims are **not** met」。 |
| `README.md:462`–`:464` | 没有提示这一页**自己也有边界**（§6：「它不保证你的机器上跑出来和这里一模一样」）。 | `docs/how-to-verify.md:419`–`:427` | 可不改；页内 §6 已经写明，属于可接受的重复省略。 |

---

## 3. 数字一致性

### 3.1 逐个核过且**一致**的数字

| 数字 | 页面出处 | 落盘出处 | 判定 |
|---|---|---|---|
| 测试数 1,588 = 1,441 快 + 147 集成 | `how-to-verify.md:113`–`:119` | `docs/reports/phase1-execution-report.md:76`、`:143`–`:145`（`<!--fig:tests.total-->` 等标记）、`README.md:12` 徽章 | ✅ 一致；**且实跑复核过**（见 §4） |
| 覆盖率 93.3%（7,117 / 7,631 行） | `how-to-verify.md` 未复述，索引页 `:109` 复述 | `phase1-execution-report.md:77`、`:1065`、`:1082` | ✅ 一致（7,117 / 7,631 = 93.25% → 93.3%） |
| 源指纹 `sha256:787282…` | `docs/reports/README.md:109` | `phase1-execution-report.md:1082` = `sha256:78728268669a0179765a58ef637ab6acea7ecb92271550107b250ab38d4352fe` | ✅ 前缀一致 |
| MCP 工具 11 个 | `docs/reports/README.md:109` | `scripts/verify-public-contracts.py:327`–`:339` `EXPECTED_TOOLS` 11 个；`tests/test_public_contracts.py` `EXPECTED_MCP_TOOLS` 11 个；`public-contracts.md:423`「恰为 §3.1 的十一个名字」 | ✅ 一致 |
| CLI 13 个子命令 | `phase1-execution-report.md:55` 的 `<!--fig:cli.commands-->` | `refresh-report-figures.py:659` `cli.count("@app.command()")` → **实算 13** | ✅ 一致 |
| REST 23 个端点 | `phase1-execution-report.md:56` 的 `<!--fig:api.endpoints-->` | `refresh-report-figures.py:660` 正则数路由 → **实算 23**；`tests/test_public_contracts.py` `EXPECTED_REST_ROUTES` 46 条（method+path 配对 = 23 个路径） | ✅ 一致 |
| 契约活检 49 项（28 REST + 6 MCP + 15 CLI） | `docs/reports/README.md:109`、`how-to-verify.md:234`–`:237` | `public-contracts.md:348`「检查项清单共 49 项：28 REST + 6 MCP + 15 CLI」；脚本里 `check()` 调用点实数 = 28 + 6 + 15 = 49 | ✅ 一致（**静态条数**） |
| 契约活检实跑 48（27+6+15）/ 47（26+6+15） | `how-to-verify.md:239`–`:242` | `public-contracts.md:361`–`:362` 的验证记录表；**实跑得 48/48，退出码 0**（见 §4） | ✅ 一致 |
| 退出码 0–6 | `docs/reports/README.md:115`；`how-to-verify.md:226`–`:229` 的活检输出 | `public-contracts.md:46`–`:54` 退出码表 7 行；`tests/test_public_contracts.py` `EXPECTED_EXIT_CODES` 7 项；活检实跑逐个打到 0/1/2/3/4/5/6 | ✅ 一致 |
| M6 49/60 = 81.7%、逐轮 15/16/18 | `how-to-verify.md:354` | `docs/benchmarks/m6-level2-retest4.md:82`（逐轮）、`:83`（合计）、`:85`（总结论） | ✅ 数字一致（**行号引用有问题，见 3.2**） |
| 窄验证 2/6、2/5 / 3/6、3/5 | `how-to-verify.md:355` | `m6-level2-narrow-verify2.md:61`、`m6-level2-narrow-verify3.md:61` | ✅ 一致，且**行号精确命中** |
| M10 40 项验收检查表 + 自查 40/40 | `how-to-verify.md:356` | `docs/status.md:138`（§4.0 的 M10 行）、`docs/roadmap/ROADMAP.md:390` | ✅ 一致 |
| 成熟度 5.50 / 10 | `how-to-verify.md:360` | `docs/status.md:27`、`:104` | ✅ 一致 |
| 索引页转述的各报告自报条数：52 / 10 / 5 / 20 / 9 / 12 / 29 / (23+5+1) / 8 | `docs/reports/README.md:109`–`:117` | 逐份回原报告：52（`stale-number-scan.md:70`）、10（`m10-number-traceability.md:198`）、5（`outreach-final-review.md:323`）、N=20（`outreach-recheck.md:283`）、9（`release-notes-consistency.md:276`）、12（`changelog-vs-release-notes.md:41`）、29 / 23+5+1 / 8（`m10-reader-walkthrough.md`、`m10-reader-walkthrough-2nd.md:49`） | ✅ 全部一致 |
| 索引页转述的 23 处分九组 | `docs/reports/README.md:117` | `final-outward-consistency.md` §3 的 A–I 组（6/2/2/1/4/2/2/3/1 = 23），组名逐个对得上 | ✅ 一致 |
| 索引页引用的 31 个 commit hash | `docs/reports/README.md` 全文 | 逐个 `git cat-file -e` 确认存在 | ✅ 全部存在 |
| 索引页 §7 点名的 8 份「历史记录」 | `docs/reports/README.md:130`–`:137` | 8 份都已计在 §1–§6 里（与 `:30` 的声明相符）；各自「以哪一份为准」的指针逐条核对成立 | ✅ 成立（**一处例外，见 5.1**） |

> **任务清单里的「三个证据包、三个一方样本」在这两页里并不存在。** 全文检索只有
> 「三个后端」「三个数」等表述；`examples/` 下的一方样本实际是 **5 个** APK
> （`phase1-execution-report.md:81` 的 `<!--fig:samples.apks-->5<!--/fig-->`，
> `refresh-report-figures.py:661` 实算亦为 5）。此项无对应说法可核。

### 3.2 数字/引用**有问题**的地方

| 位置 | 问题 | 依据（file:line 或实跑输出） | 建议改法 |
|---|---|---|---|
| `docs/how-to-verify.md:168` | **`documents read: 110` 与当前树不符。** 该块被标注为「下面是这棵树上的实测输出」，但当前树实测是 **114**。差的 4 份正是本轮新增的文档：`docs/reports/README.md`、`english-reader-review.md`、`m10-invitation-sender-checklist.md`、`outreach-publish-checklist.md`。 | 实跑 `python scripts/check-version-claims.py --base auto` → `documents read: 114`。核对：`git ls-files "*.md"` = 124，减 `HISTORY = (".github/issues/",)` 的 10 份 = 114；在 `b25068a` 上是 120 − 10 = 110，即该输出是写这一页时的真值。**（本报告签入后该数会变成 115——正好印证这一行「每增删一份文档，这个数就变」。）** | 重新贴一次输出（把 `110` 改成 `114`）；或在块外补一句「此块采于 `b25068a`，其后本仓库新增了 4 份文档，该数现在会是 114」。注意页面正文已经写明「仓库每增删一份文档，这个数就变」，但**标注为实测输出的块必须与当前树一致**，否则访客会以为门禁坏了。 |
| `docs/how-to-verify.md:172`–`:174` | findings 块**不是逐字输出**：真实输出在每条 finding 下面还有一行被引文（`First-party coverage is **91.0%** …` / `- **The v0.1.3 release notes quoted…`），页面把它们删了，却仍把整块标为「实测输出」。 | 实跑输出见 §4 的第 2 条记录。 | 把那两行引文补回去，或把块首的「实测输出」改成「节选」。 |
| `docs/how-to-verify.md:354` | 行号引用**漏了关键一行**：「逐轮 15/16/18」与「每轮 ≥16/20」写在 `m6-level2-retest4.md:82`，页面引的是「第 83、85 行」——83 是三轮合计，85 是总结论，**两者都不含逐轮数**。访客按页面的行号跳过去，找不到「15/16/18」。 | `m6-level2-retest4.md:82` = 逐轮判定；`:83` = 三轮合计；`:85` = 总结论。 | 改成「第 82、83、85 行」。 |
| `docs/reports/README.md:3`、`:28` | **「三十七份报告」与目录实际文件数不符**：实际是 **40** 份（`docs/reports/` 下 41 个 `.md`，减去索引页自己）。 | `ls docs/reports/*.md` = 41；减 `README.md` = 40。索引页的分组表 7+5+2+8+5+10 = 37 是**自洽的**，但不等于目录实况。 | 改成「四十份」，并同步分组表（见 §6）。 |
| `docs/reports/README.md:114` | 指向了**不存在的小节号**：括号里说「该报告 §3 逐条给了理由」，但 `docs/reports/stale-number-scan.md` **没有 §3**（章节是 §0 / §1 / §2 / §4 / §5）。那两段（历史陈述 30 处、计划待办 21 处）是 §2 末尾两段**无编号小节**，分别在 `:177` 与 `:207`。 | `grep -n "^## " docs/reports/stale-number-scan.md` → `0.`/`1.`/`2.`/`4.`/`5.`，无 `3.` | 改成「该报告 §2 末尾两段（历史陈述 30 处、计划待办 21 处）逐条给了理由」，或给出行号 `:177` / `:207`。 |
| `docs/reports/README.md:109` | 「**契约活检项数统一为 49**（提交 `27a8d67`）」写在 §6 的「结论被并进了哪些改动」列里，脱离上下文看会被读成**实跑条数是 49**——而这正是 `final-outward-consistency.md` §3 C 组（第 9、10 条）判过、后来由 `a3bbd3c` 改成 48/47 的那个误解。同一页 `:117` 提到了 `a3bbd3c`，但没有把两者扣上。 | `public-contracts.md:348`「49 项」= 静态调用点；`:353`「49 是静态条数，任何一次实跑都跑不满它」；实跑上限 48。 | 把该句改成「**契约表项数**统一为 49（静态条数）；实跑 48/47 由 `a3bbd3c` 定稿」，与 `how-to-verify.md:234`–`:242` 的口径对齐。 |
| `docs/how-to-verify.md:91`–`:98` | §2.2 的 `dexatlas backends` 表格**列宽与真实输出不符**（Version 列文档写 18 宽、实际输出 9 宽），且漏了标题行的居中缩进。内容（三行 / jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4）本身**正确**。 | 实跑输出见 §4 第 6 条。 | 把表格换成实跑的原文；或把这一块降级为「示意」并注明「列宽随终端宽度变化」。 |
| `docs/how-to-verify.md:283` | 「**逐字节**应当和仓库里的一样」在 Windows 上不严格成立：脚本用 `Path.write_text` 写出的是 **CRLF**，而仓库里签入的是 **LF**。内容（除行尾外）逐字节相同。 | 隔离副本实跑 `m6_level2_retest4_report.py` → `cmp` 报 `differ: char 103, line 1`；`diff --strip-trailing-cr` → **无差异**。 | 改成「**内容**逐字节相同（Windows 上脚本写出 CRLF、仓库签入 LF，行尾不同）」；或补一句「在 LF 检出上逐字节相同」。 |

---

## 4. 命令可用性（实跑记录）

**实跑了 11 条**（纯只读的那些），逐字记录实际输出。

### 4.1 文档行号引用门禁 —— ✅ 与页面所写**逐字相符**

```
$ python scripts/check-doc-citations.py
citations: 221
  naming a symbol: 162
  pointing only at a location: 59
unresolved paths: 0
drifted: 0

Every citation still says what it says.
EXIT=0
```

与 `how-to-verify.md:136`–`:144` 的代码块**逐字相同**。页面 `:149`–`:152` 关于「这条门禁只扫四份文件、本页不在其中」的说明也**属实**
（`scripts/check-doc-citations.py` 的 `DOCS` 清单就是那四份）。

### 4.2 版本声明门禁 —— ⚠️ 输出与页面所写**不一致**（`documents read`）

```
$ python scripts/check-version-claims.py --base auto
facts:
  tags: handover-2026-11-10, phase1-acceptance-2026-10-21, v0.1.0, v0.1.1, v0.1.2, v0.1.3, v0.2.0, v1.0.0
  package version: 1.0.0
  changelog: 1.0.0, 0.2.0, 0.1.3, 0.1.2, 0.1.1, 0.1.0
  newest release: v1.0.0
documents read: 114          ← 页面写 110
  skipped: v0.1.0: the report of that release has no measured coverage, so only its test count is checked
  skipped: v0.1.1: the report of that release has no measured coverage, so only its test count is checked
  skipped: v0.1.2: the report of that release has no measured coverage, so only its test count is checked
findings: 2 (2 already in 8f9ddcaf)
  docs/releases/v0.2.0.md:326  release-coverage  it says the coverage is 91.0%, the measured coverage is 91.6%
      First-party coverage is **91.0%** (5945/6536 lines). `mypy` strict and `ruff`   ← 页面删掉了这行
  CHANGELOG.md:1033  release-coverage  it says the coverage is 93.9%, the measured coverage is 91.6%
      - **The v0.1.3 release notes quoted a hand-copied coverage figure.** They said 93.9%,   ← 页面删掉了这行

Every version claim matches the repository.
EXIT=0
```

其余各行（tags / package version / changelog / newest release / 三条 skipped / `findings: 2 (2 already in 8f9ddcaf)` / 两条 finding 本身 / 结尾句 / 退出码 0）与页面**完全一致**。只有 `documents read` 那一行和被删掉的两行引文对不上。

### 4.3 公共契约活检 —— ✅ 与页面所写**一致**，且实测条数与页面表格相符

```
$ python scripts/verify-public-contracts.py        # 后端齐备（JADX 1.5.2 / Apktool 2.11.1 / Androguard 4.1.4）
== REST API over uvicorn ==      27 条 PASS
== MCP server over the protocol == 6 条 PASS
== CLI exit codes ==             15 条 PASS
  PASS version exits 0
  PASS backends exits 0
  PASS analyze of the demo APK exits 0
  PASS projects exits 0 and lists the project
  PASS source with jadx answers 0 … answers 1 (empty)
  PASS resources with apktool answer 0 … answers 1 (empty)
  PASS unknown project exits 2
  PASS --limit 0 is refused with 2
  PASS a missing file exits 2
  PASS a file that is not an APK exits 2
  PASS an ambiguous method name exits 4
  PASS the candidates are named
  PASS a failed analysis exits 3
  PASS a truncated analysis exits 5
  PASS an analysis with no index exits 6

48/48 checks
the public contracts hold
EXIT=0
```

- 页面 `:239`–`:242` 的表「三后端齐备 = 48（27 REST + 6 MCP + 15 CLI），48/48，退出码 0」——**逐项对上**。
- 页面 `:212`–`:229` 引用的输出节选——**逐字对上**（含 `PASS tool list is exactly the read-only tools`）。
- 页面 `:297`–`:307` 说的两种拒绝形态——**实测成立**（见 4.7、4.8）。
- 实跑输出共 58 行、48 条 PASS；页面写「完整 48 行」指 PASS 条数，口径可接受。
- 退出码 **4**（`EXIT_AMBIGUOUS`）确实被触发（`PASS an ambiguous method name exits 4`），
  页面节选里没列它——节选已声明是节选，不算错。

### 4.4 收集到的测试数 —— ✅ 与页面所写**逐字相符**

```
$ python -m pytest --collect-only -q -m "not slow"
1441/1588 tests collected (147 deselected) in 2.64s

$ python -m pytest --collect-only -q -m "slow"
147/1588 tests collected (1441 deselected) in 3.94s
```

与 `how-to-verify.md:118`–`:119` 写的两条**逐字相同**（页面把耗时省略了）。

### 4.5 文档门禁测试 —— ✅ 无 skip

```
$ python -m pytest tests/test_docs.py -q
60 passed in 21.37s
```

**0 skipped**。这同时验证了页面 §2.1 的说法：`demo` extra 装上 Pillow 后 `tests/test_docs.py`
不再 skip。页面 `:122`–`:124` 说「skipped 那一栏必须是 0」——在 `test_docs.py` 上成立。

### 4.6 后端状态表 —— ✅ 内容对，列宽差

```
$ python -m dexatlas.cli.main backends
         Analysis backends
┌────────────┬───────────┬─────────┐
│ Backend    │    Status │ Version │
├────────────┼───────────┼─────────┤
│ jadx       │ available │ 1.5.2   │
│ apktool    │ available │ 2.11.1  │
│ androguard │ available │ 4.1.4   │
└────────────┴───────────┴─────────┘
EXIT=0
```

### 4.7 M6 报告重算 —— ✅ 内容一致，行尾有差（见 §3.2 末行）

隔离副本（把 `scripts/`、`benchmarks/`、三份 trace 复制到临时树）实跑
`m6_level2_retest4_report.py`：`diff --strip-trailing-cr` **无差异**；`cmp` 因 CRLF/LF 报不同。

### 4.8 缺 trace 时的拒绝 —— ✅ 两种形态都被页面说对了

| 脚本 | 实测行为 | 与页面 |
|---|---|---|
| `m6_level2_narrow_verify2_report.py` | `trace file is missing: …/m6-level2-narrow-verify2-traces.json` / `the run is not complete; refusing to write a partial report`，**EXIT=1**，**未写出报告** | ✅ 与 `how-to-verify.md:289`–`:294` **逐字相同** |
| `m6_level2_retest4_report.py` | `round1 trace file is missing: …` / `the three-round rerun is not complete; refusing to write a partial acceptance report`，**EXIT=1**，未写出 | ✅ 属页面列的「指名拒绝」一类 |
| `m6_level2_report.py` | 抛**未捕获的 `FileNotFoundError`** 回溯，**EXIT=1**，未写出 | ✅ 与页面 `:303` 说的「未捕获异常」形态一致 |

页面 `:300`–`:303` 列的 10 个脚本全部存在；「指名拒绝」一列的 7 个脚本确实用 `SystemExit`，
「未捕获异常」一列的 3 个脚本确实直接 `TRACE_PATH.read_text()` 不先查存在性——**这张表是对的**。

### 4.9 顺带核到的东西（不在命令表里，但页面引用了）

| 事实 | 依据 |
|---|---|
| `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 是代码真正读的变量名 | `src/dexatlas/tools/jadx/adapter.py:183`、`src/dexatlas/tools/apktool/adapter.py:106` |
| `install-backends.sh` 装的正是 JADX 1.5.2 / Apktool 2.11.1，`INSTALL_ROOT` 默认 `/tmp/dexatlas-backends` | `scripts/install-backends.sh:20`–`:22` |
| 并发测量的保护文案与页面 `:333`–`:336` 逐字相同 | `scripts/refresh-report-figures.py:1211` |
| `--check` 选项存在（§2.8 的第二条命令） | `scripts/refresh-report-figures.py:1154`–`:1155` |
| 指纹比对测试确实存在，页面 §4 点名的那条测试名对得上 | `tests/test_docs.py:682` `test_execution_report_coverage_figures_describe_the_current_code` |
| `docs/status.md` 确实有 3 个 `<!--fig:…-->` 标记（§4 的说法） | `grep -c "fig:" docs/status.md` = 3 |
| 历史版本测试数确实由脚本 `git archive` + `--collect-only` 量出 | `scripts/refresh-report-figures.py:681`–`:682`、`:706` |
| `analysis-provenance.md` 的 §4 / §7 / §8 标题与页面 §1 第 5 行的说法一致 | `docs/analysis-provenance.md:236`、`:1220`、`:1250` |
| `docs/architecture/` 下「多数是英文」属实 | 11 份里 9 份英文为主（`public-contracts.md` 为中文、`diagram.md` 中英混排） |

### 4.10 完整套件实跑 —— ⚠️ 汇总行的 skip 数是 **27**，不是页面说的「0」

```
$ python -m pytest -q
1561 passed, 27 skipped in 415.61s (0:06:55)
EXIT=0
```

- 收集数与页面一致：1,561 + 27 = **1,588** ✓，0 failed、0 error ✓。
- **27 个 skip 全部是同一个原因**，逐条核过：

  | 条数 | skip 原因 |
  |---|---|
  | 25 | `fixture not present; run scripts/fetch-fixtures.sh` |
  | 2 | `fixture TestActivity.apk not present; run scripts/fetch-fixtures.sh` |

  涉及 `tests/test_androguard_integration.py`、`tests/test_androguard_isolation.py`、
  `tests/test_smali_fallback_integration.py`。原因是**第三方 fixture 没抓**
  （`scripts/fetch-fixtures.sh` 要联网，本次禁止联网，故未执行）——**与后端无关**，
  三个后端全程在场（活检那一条已证）。
- 页面 `how-to-verify.md:123` 说「**skipped 的数量** —— **这一栏必须是 0**（或你能说清每一个 skip 的原因）」。
  括号里的免责成立（pytest 自己把原因打在 skip 行上），但**页面从头到尾没有提
  `scripts/fetch-fixtures.sh` 这一步**：§2.0「一份干净的检出」→ §2.1 装依赖 → §2.2 装后端，
  走完之后汇总行仍然是 27 skip。访客既不知道该去抓 fixture，也拿不到「0」。
  这与 §4.1 那条是同一类毛病：**页面给的预期输出与访客真跑出来的对不上**。
  本仓库的规则 7 明确写着「Samples are either first-party (`examples/`) or fetched by
  `scripts/fetch-fixtures.sh` from Apache-2.0 licensed data」，一页讲「怎么自己复核」的文档
  却没有这一步，是缺口。

---

## 5. 与本轮其它改动的冲突

### 5.1 必须改的一处：**验收 commit 的钉定方式**，索引页说反了

| 位置 | 问题 | 依据 | 建议改法 |
|---|---|---|---|
| `docs/reports/README.md:78` 与 `:135` | 两处都说邀请函**模板**的「验收 commit 还是空白」。**这已经过期了**：模板现在的文首明写「**验收 commit 已钉定为 v1.0.0 发版 commit**（本轮读者 `git checkout v1.0.0` 得到的那个提交）……该 commit 的完整 hash 写在成稿第二节的占位符里，由发起人在发出前填入（模板本身不预设具体 hash）」。空白的是 **hash**，不是 **commit**。 | `docs/reports/m10-invitation-template.md:14`–`:17`（文首）、`:72`–`:73`（正文「本轮为 v1.0.0 发版 commit」）；`:8`「模板本身不预设具体 hash」 | `:78` 改成「邀请函**模板**：正文用通用措辞，**验收 commit 已钉定为 v1.0.0 发版 commit**，只有完整 hash 不在模板里预设（见成稿第二节的占位符）」；`:135` 同步改。 |
| `docs/reports/README.md:77` | 索引页把邀请函成稿描述成「**只差**发起人把完整 hash 填进占位符」，读起来像「随时可发」。但**现在还不能发**：walkthrough-2nd 的 N1 指出「重打 tag 之前邀请函不能发」，而 tag **至今没有重打**——`v1.0.0` 仍指向 `8f9ddca`，落后当前树 **61 个提交**；`origin/main` 也还是 `8f9ddca`。tag 里的那版邀请函第二节写的是 `commit 277d0fa`，准备包 F1 还写退出码 0–5、F3 还写 10 个 MCP 工具。 | `git rev-list -n1 v1.0.0` → `8f9ddca`；`git rev-list --count v1.0.0..HEAD` → 61；`git log origin/main -1` → `8f9ddca`；`git show v1.0.0:docs/reports/m10-invitation-final.md` 第 57 行 → `commit 277d0fa`；`docs/reports/m10-reader-walkthrough-2nd.md:296` 的 N1 建议原文 | `:77` 补上条件：「……**但 `v1.0.0` tag 仍停在 `8f9ddca`（落后当前树 61 个提交），N1 的『重打 tag 之前不能发』仍然成立；tag 重打前不要发出这封信。**」§6 的 `m10-reader-walkthrough-2nd.md` 行（`:116`）也建议补一句「N1 尚未关闭：tag 未重打」。 |

### 5.2 核过、**没有**冲突的三项

| 主题 | 落盘现状 | 两页的说法 | 判定 |
|---|---|---|---|
| **契约活检的实跑条数** | `public-contracts.md:348`「49 项：28 REST + 6 MCP + 15 CLI」= **静态**调用点数；`:353` 明确「49 是静态条数，任何一次实跑都跑不满它」；`:361`–`:362` 记录 47 / 48 两次实跑；`a3bbd3c` 已把实跑数字改成 48/48、47/47 | `how-to-verify.md:234`–`:246` **完整**讲清了「49 是静态条数、实跑 48 或 47、两条 CLI 调用点按后端分支」；实测 48/48 与之相符 | ✅ **一致**。索引页 `:109` 的措辞另见 §3.2 |
| **M6 的停机轮次口径** | `docs/status.md:44`「窄验证二、三两轮连续未达后」、`docs/reports/v1.0.0-github-release-body.md:244`「连续两轮未达后」——都是**两轮**（`0403847` B 组已改） | 两页都没有复述停机轮次口径 | ✅ **无冲突**（也没有把三轮写回来） |
| **退出码 6 的归属** | `README.md:546`「the all-backends-timeout exit code is **implemented as exit code 6** (`EXIT_NO_INDEX`) and written into the public contract table」；`public-contracts.md:54` 退出码表列 6；`CHANGELOG.md:131` | `how-to-verify.md:226`–`:229` 的活检输出含 `PASS an analysis with no index exits 6`；索引页 `:115` 写「M10 自查口径改成 0–6」 | ✅ **一致**，两页都没有把它说成「已知限制」 |

---

## 6. 索引页的收录完整性

| 项 | 数量 | 说明 |
|---|---|---|
| 目录里实际的报告文件（`docs/reports/*.md`，不含索引页自己） | **40** | `ls docs/reports/*.md` = 41，减 `README.md` |
| 索引页声称的份数 | **37** | `:3`「三十七份报告」；`:28` 分组表合计 37 |
| **漏收** | **3** | `english-reader-review.md`、`m10-invitation-sender-checklist.md`、`outreach-publish-checklist.md` |
| **多收** | **0** | 索引页点名的 37 个文件全部存在，没有指向不存在的文件 |

**为什么漏：** 索引页写于提交 `b3b2a63`，那棵树上正好 37 份；这三份是**之后**落盘的，
且都在 2026-11-17 这一天：

| 漏收文件 | 引入提交 | 性质 | 建议归入 |
|---|---|---|---|
| `english-reader-review.md` | `cc1e8e6` | 只读复核（五份对外英文文本的可读性与印象） | **§6 本轮审计与走查** → 该组 10 → **11** |
| `m10-invitation-sender-checklist.md` | `f0dcc7a` | 发起人发出 M10 邀请前要做的每一步 | **§4 M10 独立验收材料** → 8 → **9** |
| `outreach-publish-checklist.md` | `fed3a37` | Upwork 素材发布前的最后点检清单（内部件，四件素材仍是草稿、未发布） | §6 偏「发布动作清单」而非审计；可放 §6（则 §6 → 12），或新开一组「对外素材发布前点检」 |

**「历史记录」判断是否成立：成立，但有一处例外。**

§7 点名的 8 份文件**都已在 §1–§6 里计过份数**（与 `:30` 的声明相符），逐条核对如下：

| 文件 | §7 的理由 | 核对结果 |
|---|---|---|
| `v1.0.0-dry-run.md` | 预演，非发版执行记录 | ✅ 成立（标题与开头都这么写） |
| `v1.0.0-release-runbook.md` | 预研文档，基准 `c3586d8` | ✅ 成立（`c3586d8` 存在） |
| `v1.0.0-release-commit-draft.md` | 草案，实际发版提交已存在 | ✅ 成立（tag `v1.0.0` 在） |
| `portfolio-readiness-2026-11-15.md` | 基线评估，基准 `752d10a`，当日被复评取代 | ✅ 成立（`752d10a` 存在，复评件在目录里） |
| `m10-reader-walkthrough.md` | 第一轮问题清单，已被第二轮逐条复核 | ✅ 成立（23 关闭 / 5 未关闭 / 1 判定有误） |
| `m10-invitation-template.md` | 「验收 commit 还是空白」 | ❌ **不成立**（见 §5.1） |
| `claim-mismatches.md` | 量于 `8df894b`，快照 | ✅ 成立（`8df894b` 存在，文件开头自述快照） |
| `phase1-findings-ledger.md` | 记的是复验当时的状态 | ✅ 成立 |

§7 的三条通则（`:141`–`:147`）也都与落盘一致：§6 报告各自锚基线、只读审计 ≠ 结论已落地、
历史陈述 ≠ 过期数字（`stale-number-scan.md:177` / `:207` 确实分列这两类）。

---

## 7. 必须改的 N 处

> **只列清单，不代改。** 下面 9 条按「改了才算数」排序；其余为建议项，见 §3.2 表格。

1. **`docs/how-to-verify.md:168`** —— `documents read: 110` 与当前树（**114**）不符，而该块被标为「这棵树上的实测输出」。重新贴一次输出，或标明采于 `b25068a`。
2. **`docs/reports/README.md:3` 与 `:28`** —— 「三十七份报告」/ 合计 37 → **40**；分组表同步（§4 8→9、§6 10→11，另有 1 份待定归组，见 §6）。
3. **`docs/reports/README.md`** —— **补收三份漏掉的报告**：`english-reader-review.md`、`m10-invitation-sender-checklist.md`、`outreach-publish-checklist.md`，并各写一行「回答什么 / 什么时候看它」。
4. **`docs/reports/README.md:114`** —— 「该报告 §3」→ `stale-number-scan.md` **没有 §3**；改成「§2 末尾两段（`:177` / `:207`）」。
5. **`docs/reports/README.md:78` 与 `:135`** —— 邀请函模板的描述已过期：commit 已钉定为 v1.0.0 发版 commit，**只有完整 hash 未填**，且 hash 在成稿的占位符里。
6. **`docs/reports/README.md:77`（建议 `:116` 同步）** —— 邀请函成稿「只差填 hash」的说法掩盖了 **N1 仍未关闭**：`v1.0.0` tag 仍停在 `8f9ddca`（落后当前树 61 个提交），`origin/main` 同样是 `8f9ddca`，**tag 重打前这封信不能发**。
7. **`docs/how-to-verify.md:354`** —— 行号引用补上 `m6-level2-retest4.md` 的 **第 82 行**（逐轮 15/16/18 与「每轮 ≥16/20」在那儿，83 与 85 都不含）。
8. **`README.zh-CN.md:368`–`:371`** —— 补上与 `README.md:462`–`:464` 对应的一行（中文读者的指路入口）；这一条属于本仓库自己 `final-outward-consistency.md` §3 的「I 组 —— 中英对等」。
9. **`docs/how-to-verify.md:123` 与 §2.0–§2.2** —— 补上 **抓 fixture 的一步**（`bash scripts/fetch-fixtures.sh`，Apache-2.0 数据）。实测：按页面现在的三步走完，汇总行是 **27 skipped**，而页面写着「这一栏必须是 0」；这 27 个 skip 全部是「fixture not present; run scripts/fetch-fixtures.sh」。要么把这一步写进 §2.0，要么把 §2.3 的判据改成「skip 只允许来自未抓取的第三方 fixture，且每一条都要能说出是哪一类」。

**建议项（不阻塞发布，但会被下一个访客撞上）：**

- `docs/how-to-verify.md:172`–`:174`：findings 块补回被删的两行引文，或把「实测输出」改成「节选」。
- `docs/how-to-verify.md:91`–`:98`：`dexatlas backends` 表格换成实跑原文（Version 列宽）。
- `docs/how-to-verify.md:283`：「逐字节相同」→「内容逐字节相同（行尾 CRLF/LF 有差）」。
- `docs/how-to-verify.md:78`–`:79`：`INSTALL_ROOT` 的默认值写的是 `/tmp/dexatlas-backends`，脚本实为 `${RUNNER_TEMP:-/tmp}/dexatlas-backends`（在 GitHub runner 上是 `$RUNNER_TEMP/dexatlas-backends`）。
- `docs/reports/README.md:109`：「契约活检项数统一为 49」补成「契约表**静态**项数 49；实跑 48/47」，与 `how-to-verify.md:234`–`:242` 对齐。
- `README.md:462`–`:464`：补前置条件（JDK + 三个后端）与 §3 的页内锚点。

---

## 8. 这两页能不能真的带一个访客走完一遍复核？

**结论：能走通大半，但有三处会被访客撞上的绊脚石，一个硬缺口。**

### 8.1 走得通的部分

- 路径设计是对的：§1「五类说法 → 落在哪里 → 怎么核」给了一张可导航的地图，
  §2 给了逐条命令与**该看到什么**，§5 给了「最短复核路径」的五步。这套结构对一个
  只读过 README 的访客是够用的——他不必读代码就能知道每个数字该去哪里核。
- **命令是真的。** 11 条命令实跑过：引用门禁、版本门禁、契约活检、测试收集数、完整套件、
  `test_docs.py`、后端状态、M6 报告重算、缺 trace 的两种拒绝形态，全部与页面描述相符
  （只有 `documents read`、skip 数与两处格式细节对不上，见 §7 第 1 条与第 9 条）。
- **最要紧的诚实性做到了**：§3「哪些说法目前是未达成 / 未验证」直接列出 M6 未达标
  （49/60 = 81.7% < 90%）、窄验证两轮未达、M10 验收未开始、macOS 未验证、
  成熟度 5.50 是修复前的基线。这一页没有替项目遮丑，这正是它作为访客入口的价值。

### 8.2 三处会被访客撞上的绊脚石

1. **§2.5 的输出块与真机不符（`documents read: 110` vs 114）。**
   访客跑完门禁会看到 114，而页面上写 110 —— 他会以为自己装错了版本，或者（更糟）
   以为这个门禁本来就不准。**这是本页最容易被撞上的一处**，因为 §2.5 是「最短路径」
   的第 2 步，几乎每个访客都会走到。
2. **§2.3 的汇总行：页面说「skipped 那一栏必须是 0」，真跑是 27。**
   实跑完整套件：1,561 passed + **27 skipped**（全部是「fixture not present; run
   scripts/fetch-fixtures.sh」）。页面从 §2.0 到 §2.2 讲完了装环境的三步，**唯独没有
   抓 fixture 这一步**（见 §7 第 9 条）。访客若照页面走完，汇总行里那 27 个 skip 无从解释。
3. **§2.2 的后端表格列宽与真机不符。** 影响小，但同样会让人怀疑「这页是不是手抄的」。

### 8.3 一个硬缺口：**「数出个数」这件事，访客没法自己完成**

页面 §1 第 2 行把「公共契约（CLI 子命令、退出码、REST 端点、MCP 工具、报告 schema、版本政策）」
整体交给 `scripts/verify-public-contracts.py`。但那个脚本核的是**响应形状**，
不是**数量**——它只打自己用到的那些端点，不会告诉你「一共 23 个而不是 24 个」：

| 要核的数 | 活检脚本核得了吗 | 真正的核法 |
|---|---|---|
| MCP 工具 11 个 | ✅ 核得到（`PASS tool list is exactly the read-only tools`） | 活检即可 |
| REST 端点 23 个 | ❌ 核不到（只打用到的那几个） | `tests/test_public_contracts.py` 的 `EXPECTED_REST_ROUTES`（46 条 = 23 个路径 × method），断言 `served - FRAMEWORK_ROUTES == EXPECTED_REST_ROUTES`，**多一个端点就红** |
| CLI 子命令 13 个 | ❌ 核不到（只调 4 个命令） | `refresh-report-figures.py:659` 的 `cli.count("@app.command()")`；实算 13 |
| 退出码 0–6 | ✅ 核得到（逐个触发） | 活检即可 |

页面 §1 第 2 行提到了「契约快照在 `tests/test_public_contracts.py`」，但**没给命令**。
一个认真的访客核到「REST 23 个端点」时会卡在这里：他打开契约表看到 23 行，
但没法确认这就是全部——**除非他知道要跑那条快照测试**。
建议在 §1 第 2 行补一句可执行的话，例如
`uv run --no-sync pytest tests/test_public_contracts.py`（核端点集合、MCP 工具集合、退出码集合），
并补上 `cli.commands` 的数法。

### 8.4 其余缺口（次要，但都影响「能不能走完」）

- **§2.6 契约活检起 uvicorn，占用 8977 端口**，会写 `.scratch/`。页面没有说端口与副作用。
- **§2.2 要联网下载后端**（JADX / Apktool 二进制），页面没有说来源、体积，也没说这三个后端
  **不随仓库分发**（`CLAUDE.md` 规则 7）。一个不打算装后端的访客读到这里会以为项目「开箱即用」。
- **§2.3 说「skipped 那一栏必须是 0」**，但没给出「skip 会从哪来」的具体对照——§0 第 3 条讲了
  「缺后端会 skip」这个原则，§2.3 没有把它和「0」这个判据接起来，也没说 fixture 那 27 条
  （见 §7 第 9 条）。
- **§6「这页没有覆盖什么」写得好，但排在最后。** 访客是顺序读的，读到 §6 时已经跑完一遍命令。
  「哪些数字是这台机器量出来的、哪些是仓库归档的」这类边界应该提前到 §0。

### 8.5 一句话结论

**这两页已经足够带一个访客走完一遍复核——前提是先把 §7 的第 1 条（`documents read`）与第 9 条
（抓 fixture 的一步）补上，再把 §8.3 的那条命令补进 §1 第 2 行。** 改完之后，一个访客可以在
**不向作者要任何东西**的前提下，自己确认「1,588 个测试」「93.3% 覆盖率」「11 个 MCP 工具」
「23 个 REST 端点」「13 个 CLI 子命令」「退出码 0–6」「契约活检 48/48」「M6 未达标」这八件事——
这是这个项目第一次把「怎么复核」写成一篇访客能自己走完的路。
