# 对外素材首读终审（只读复核）

> **状态：作者侧首读复核，不是发布动作。** 本轮没有向 Upwork 或任何其它
> 平台提交、发布、复制或发送任何内容；没有登录账号，没有调用任何模型 API，
> 没有创建 tag，也没有向任何远端推送。本轮**没有联网**，素材里引用的官方
> 指南链接仍未对现网核实。
>
> **本文件是只读产物。** 唯一写入就是本文件。素材本体一个字都没改；下面所有
> 建议句子供主会话在测量落盘后统一采用。
>
> **复核对象**：`docs/outreach/` 下三份对外素材
> （`cover-letter-templates.md`、`project-brief.md`、
> `scope-backend-automation.md`）、第三份服务页
> `scope-ai-mcp.md`、内部核对记录 `publish-review.md`，
> 外加对外展示页 `docs/portfolio.md` 与对外边界文档
> `docs/service-commitments.md`。
>
> **基准树**：本 worktree `HEAD` = `48a56b5`（`v1.0.0` tag 指向 `b71bf30`，
> 二者相差 1 个提交）。测量数字一律取自
> `docs/reports/phase1-execution-report.md` 的 `<!--fig:...-->` 标记，
> 报告里的 `<!--report-figures:{...}-->` 记录块同理；本报告不手抄任何数字，
> 凡引用均给出可复算的来源。

---

## 0. 一句话结论

**素材的数字换得干净，没有留下半截旧数，也没有同一份素材里两个数打架。**
测试数（1,632）、快/集成拆分（1,485 + 147）、覆盖率（93.3%）在四份素材里
逐字一致，也与报告的 `<!--fig:...-->` 落盘值一致。

**但「新数字」之外有三处会让真客户理解错的东西，其中一处是硬错**：
`project-brief.md` 列了**两个不存在的 CLI 命令**；四份素材把
「一方代码覆盖率」写成了**没有限定词的 93.3% coverage**；而仓库里落盘的
测量记录是 **1,631 passed / 1 failed**，不是 1,632 全绿。另外
`docs/service-commitments.md` 还在用**更早一轮**的 M6 数字，并把它写成
「达到验收线」。

共 **11 条发现**（3 条高 / 5 条中 / 3 条低），外加一节「确认过且没问题的部分」。

---

## 1. 高后果发现（会让客户理解错，或把没交付的说成交付了）

### F-1｜`project-brief.md` 列了两个不存在的 CLI 命令

**原文（`docs/outreach/project-brief.md:68-70`，逐字）：**

> - **Two transports over one core.** A CLI (`dexatlas analyze / manifest /
>   search / source / xref / evidence / report`) and a REST API (FastAPI) over
>   the same analyzer.

**仓库实况（`src/dexatlas/cli/main.py`）：** 全文只注册了 13 个 `@app.command()`，
没有子命令组（`grep` 确认无 `add_typer`）。命令名逐个是：

```
version   backends   analyze   projects   classes   methods   source
resources  resrefs   search   export   manifest   xrefs
```

对照素材列出的七个：

| 素材写的 | 真实命令 | 结论 |
|---|---|---|
| `analyze` | `analyze` | ✅ |
| `manifest` | `manifest` | ✅ |
| `search` | `search` | ✅ |
| `source` | `source` | ✅ |
| `xref` | **`xrefs`** | ❌ 少一个 s |
| `evidence` | **不存在** | ❌ |
| `report` | **不存在** | ❌ |

`evidence` 与 `report` 都不是 CLI 命令：证据包是 `dexatlas export`，报告是
`dexatlas analyze -o report.md --json report.json` 的产物；`evidence` 与 `report`
是 REST 端点与 MCP 工具的名字。仓库自己的 `README.md:202-207` 展示的也是
`backends / analyze / manifest / search / xrefs / export`。

**读者会怎么误读：** 客户照着敲 `dexatlas evidence` 或 `dexatlas report`，
得到 `No such command`。这是首读里最容易撞上的一条——数字写错客户可能不查，
命令敲错他一定当场敲。而且这份素材的主题正是「把二进制输入变成可审计输出」，
客户很可能就是要照着这几个命令跑一遍。

**建议改法（可直接用）：**

> - **Two transports over one core.** A CLI (`dexatlas analyze / manifest /
>   search / source / xrefs / export`) and a REST API (FastAPI) over the same
>   analyzer. `export` writes the evidence package; `analyze` writes the
>   Markdown/HTML/JSON reports.

---

### F-2｜四份素材把「一方代码覆盖率」写成了没有限定词的 `93.3% coverage`

**原文（三处，逐字）：**

`docs/outreach/cover-letter-templates.md:79`

> failure reporting, 1,632 automated tests at 93.3% coverage, and CI across

`docs/outreach/project-brief.md:50-51`

> - 1,632 automated tests, 93.3% coverage, mypy strict, ruff, and a CI pipeline
>   across Python 3.12/3.13 and multiple backend configurations.

`docs/outreach/scope-backend-automation.md:24`

> third-party engines, 1,632 tests at 93.3% coverage, strict mypy typing, and

**仓库实况：** 报告 `<!--fig:coverage.total-->` 的 7,650 行是 `src/dexatlas/`
**自己**的语句数，测试、脚本、文档都不在内——报告里写的就是「**一方代码**覆盖率」。
同一份仓库里的 `docs/portfolio.md:67-68` 反而写对了：

> - **Quality gates.** Strict mypy typing, ruff lint/format, 1632 tests at
>   93.3% coverage on the first-party code, ...

**读者会怎么误读：** 客户读「93.3% coverage」会默认是**整个仓库**的覆盖率，
包括 `tests/`、`scripts/`、`docs/`。而真实数字是 93.3% / 7,650 行的一方代码
覆盖率；把测试和脚本算进去的总覆盖率要低得多。

**而且内部核对记录断言了一件素材里并不存在的事。** `docs/outreach/publish-review.md:53-54` 写：

> 覆盖率的措辞保持「一方代码覆盖率」的口径，没有写成「总覆盖率」——报告里
> `coverage.pct` 量的就是一方代码。

英文素材里**没有**这个限定词。核对记录说「口径守住了」，素材里那个口径其实
已经掉了。这条比素材本身更值得修：核对记录是下一个人改素材的依据，它说
「守住了」，下一个人就不会再去查。

**建议改法（三处统一，可直接用）：**

> 1,632 automated tests and 93.3% line coverage on DexAtlas's own first-party
> code (tests, scripts and docs excluded)

若要更短：`1,632 tests, 93.3% coverage of the project's own code`。

---

### F-3｜落盘的测量记录里有 1 条 failed，素材说的是「1,632 automated tests」

**原文（四处，同一个数）：** `1,632 automated tests`（cover-letter、
project-brief ×1）、`1,632 tests`（project-brief §Deliverables、
scope-backend-automation）。

**仓库实况：** `docs/reports/phase1-execution-report.md` 的记录块落盘是：

```json
"suite": { "failed": 1, "passed": 1631, "skipped": 0, "xfailed": 0, "xpassed": 0 },
"tests": { "fast": 1485, "slow": 147, "total": 1632 }
```

即：**收 1,632 个、通过 1,631 个、失败 1 个**。这不是我的推断——上一版记录
（`44902a6`）还是 `passed: 1620, failed: 0`，`failed: 1` 是 `00309bb` 这一轮
才出现的。而 `00309bb` 的提交说明自己就写着这件事：

> **测量还差一次**：这一轮测量跑出 2 条失败，都是引用检查器——Release 正文的
> 出处是按**它声明的那棵树**（`v1.0.0` tag）解析的，而 tag 还指着旧树。等 tag
> 重打、引用检查转绿之后要再跑一次测量，让报告的 record block 里是
> 「1632 passed / 0 failed」。

tag 后来确实重打了（`b71bf30`，tagger 2026-11-18 02:16:25 +0800），
引用检查我也复跑了——`python scripts/check-doc-citations.py` 现在是
`unresolved paths: 0 / drifted: 0 / Every citation still says what it says.`
**前提已满足，但那次「还差一次」的测量没有再跑。**

**读者会怎么误读：** 客户在仓库里核对，会看到 1,631 passed。「1,632 automated
tests」在英文里几乎必然被读成「1,632 个测试都通过」。这正是本轮要问的
「1,632 tests 与 1,632 passed 会不会被当成两件事」——现在它们**确实是**两件事，
因为仓库自己的记录说差一个。

**建议改法：** 优先让主会话这轮重测量落盘出一个 `0 failed` 的记录块，那样
素材一个字都不用改。若新记录仍是 `failed: 1`，素材改成：

> 1,632 automated tests (1,631 passing in the reference run)

并且必须让 `docs/reports/phase1-execution-report.md` 的 `suite.passed`
一起对齐——**这条要等测量落盘后再定，不要现在改素材。**

---

## 2. 中后果发现（对不上，但不至于当场翻车）

### F-4｜`docs/portfolio.md` 说「six CI jobs」，括号里列了七项，仓库里其实是十个 job

**原文（`docs/portfolio.md:67-72`，逐字）：**

> - **Quality gates.** Strict mypy typing, ruff lint/format, 1632 tests at
>   93.3% coverage on the first-party code, and six CI jobs: lint, format and
>   typing; the test suite on Python 3.12 with all three backends and on Python 3.13
>   with none of the Java-based ones; the test suite with Apktool only and no JADX;
>   a check that the published M3 comparison still reproduces; the Docker image; and
>   the dependency audit.

**仓库实况：** `.github/workflows/ci.yml` 有 **9 个 job 定义**（`lint`、`test`、
`test-partial-backends`、`m3-comparison`、`docker`、`security`、`contracts`、
`m10-selfcheck`、`measurement`），其中 `test` 是 `["3.12", "3.13"]` 两版本矩阵，
所以 tag 上实际跑的是 **10 个 job**。仓库自己的 CI 记录就是这么写的
（`docs/reports/v1.0.0-ci-run-record.md` §1）：

> run [`44126968629`](...)，10 个 job 里 **4 个红**，6 个绿。

括号里漏掉的三项是：`Public contracts (live)`、`M10 acceptance self-check`、
`The report's figures describe the tagged tree`。而且它自称 six，却列了七项。
`docs/reports/phase1-execution-report.md:80` 的同一行也写着
`| CI | 6 job 全绿（3.12 / 3.13 / 部分后端 / Docker / 依赖审计 / lint） |`——
同一个旧口径出现在两个地方。

**读者会怎么误读：** 客户点开 `ci.yml` 数一遍（10），或者数括号里的七项，
两遍都对不上「six」。它读起来像「没数过」。这也是本轮最容易证伪的一条——
客户只要点一下链接。

**建议改法：**

> - **Quality gates.** Strict mypy typing, ruff lint/format, 1,632 tests at
>   93.3% coverage on the first-party code, and ten CI jobs: lint and format;
>   the test suite on Python 3.12 (all backends) and 3.13 (no Java backends);
>   the suite with Apktool only; the M3 comparison check; the Docker image; the
>   dependency audit; the live public-contract check; the M10 acceptance
>   self-check; and a job that re-measures the report's figures against the
>   tagged tree.

（`phase1-execution-report.md` 那行由测量脚本所在的主会话处理，本轮不动。）

---

### F-5｜`docs/service-commitments.md` 还在用更早一轮的 M6 数字，并写成「达到验收线」

**原文（`docs/service-commitments.md:3` 与 `:41-49`，逐字）：**

> **状态：对外表述边界文档。…最新实测基准：[m6-level2-retest2.md](benchmarks/m6-level2-retest2.md)（2026-11-16）。**

> ## 2. 已验证的服务能力（2026-11-16 实测）
> …
> | 配置 | 正确数（20 题） | 说明 |
> |---|---:|---|
> | DexAtlas | **16/20（80.0%）** | agent 配置，带证据工具链 |

它引用的 `docs/benchmarks/m6-level2-retest2.md:103` 自己写的是：

> - **DexAtlas 16/20 = 80.0%**，**达到验收线（≥16/20）**（A 7/20、B 7/20，均为 20 题完整分母）。

**仓库实况：** 最新一轮是 `docs/benchmarks/m6-level2-retest4.md`，
逐轮 **15/20、16/20、18/20**，三轮合计 **49/60 = 81.7%**，判定是
**未达 ≥54/60（≥90%）**，而且 r1 的 15/20 = 75% 低于「每轮 ≥80%」那一条线
（`docs/benchmarks/m6-level2-retest4.md:38`、`:83`）。`docs/status.md:38` 与 `:129` 也这么写。
`v1.0.0` 的 tag 说明里也是这句：「M6 层级 2 三轮完整复测合计 49/60 = 81.7%，
未达 ≥90% 验收线」。

**读者会怎么误读：** 这份文档的自我定位就是「回答把 APK 分析任务交给 DexAtlas
能期待什么」。客户读到的结论是「agent 准确率 80.0%，**达到验收线**」——
而当前口径是**未达标**。这比「多说了」严重：它把一个**未达标**的能力写成了
**已达标**。

**说明：** 四份对外素材本身**没有**引用 M6 数字（这是对的，见 §4），所以这条
只影响 `service-commitments.md` 这条对外边界文档。

**建议改法：**

> 状态：对外表述边界文档。…最新实测基准：[m6-level2-retest4.md](benchmarks/m6-level2-retest4.md)（三轮完整复测）。

> ## 2. 已实测的服务能力（未达验收线，按现状披露）

> | 配置 | 三轮正确合计（20 题 × 3 轮） | 说明 |
> |---|---:|---|
> | DexAtlas | **49/60（81.7%）** | agent 配置，带证据工具链；逐轮 15 / 16 / 18 |

并补一句：**未达 ≥90% 的合计验收线**（每轮 ≥80% 的判据中，r1 的 15/20 = 75%
未达）。

---

### F-6｜`publish-review.md` §0 的覆盖行数还是旧值

**原文（`docs/outreach/publish-review.md:22`，逐字）：**

> | 一方代码覆盖率 | 93.3%（7,117 / 7,631 行） | 同上的 `<!--fig:coverage.pct-->` / `coverage.covered` / `coverage.total`；`docs/status.md` 同值 |

**仓库实况：** 报告落盘是 **93.3%（7,135 / 7,650 行）**
（`<!--fig:coverage.covered-->7135<!--/fig-->` / `<!--fig:coverage.total-->7650<!--/fig-->`）。
所以这一行里「当前值」列的两个数都停在上一轮。

同一文件 `:389-390` 的引用块里也还写着 `真值是 93.3%：7,117/7,631`——那一处
是在**引用一段历史记录**（「并发测量污染覆盖率」那次），属于历史，可以不动；
但 §0 表是「当前值」，必须改。

**建议改法：** §0 表改成 `93.3%（7,135 / 7,650 行）`。

---

### F-7｜`publish-review.md` 的核对基准已经指错了树

**原文（`docs/outreach/publish-review.md:11-13`，逐字）：**

> > **核对基准：** `v1.0.0` 发版树（tag `v1.0.0`，2026-11-17），commit `0104ccb`
> > ——四份素材与本文件的最后一次改动都在这个发版 commit 里。

**仓库实况：**

| 说法 | 实况 |
|---|---|
| 「四份素材与本文件的最后一次改动都在 `0104ccb`」 | 三份素材与本文件的最后一次改动是 `00309bb`（2026-11-18 02:15:33 +0800）；`scope-ai-mcp.md` 是 `08cb34f` |
| 「tag `v1.0.0`」 | tag 当前指向 `b71bf30`，`0104ccb` 只是它的祖先 |
| 「tag `v1.0.0`，2026-11-17」 | tag 对象 taggerdate = `2026-11-18 02:16:25 +0800`（= UTC `2026-11-17 18:16:25`） |

`git log -1 -- docs/outreach/publish-review.md` → `00309bb`。
`git for-each-ref refs/tags/v1.0.0` → `object b71bf309b87…`，taggerdate
`2026-11-18 02:16:25 +0800`。

**读者会怎么误读（内部为主，但会传染到素材）：** 照着 `0104ccb` 去核对素材，
看到的不是当前素材；「已核对过」这个结论因此对不上任何一棵树。这条也是
F-8 的成因。

**建议改法：**

> > **核对基准：** 素材最后一次改动是 `00309bb`（2026-11-18 02:15:33 +0800）；
> > `v1.0.0` tag 当前指向 `b71bf30`。本文件的核对结论仍锚在 `0104ccb`，
> > 数字列已按最新一次完整测量同步。

---

### F-8｜tag 日期在作者自己的时区是 2026-11-18，素材写的是 2026-11-17

**原文：**

`docs/outreach/project-brief.md:109-110`

> - The current release is `v1.0.0` (tagged 2026-11-17); the public contract
>   covers the documented CLI/API/MCP surfaces.

`docs/outreach/publish-review.md:11`、`:28`、`:71`、`:78`、`:81`、`:314`；以及
`docs/status.md:129`（`v1.0.0`（tag 2026-11-17）已发布）。

**仓库实况：** tag 是附注 tag，taggerdate = **`2026-11-18 02:16:25 +0800`**，
换算成 UTC 是 `2026-11-17 18:16:25`。也就是说「2026-11-17」只在 UTC 成立，
在作者本地时区（以及任何 UTC+8 以上的读者机器上）`git for-each-ref
refs/tags/v1.0.0` 显示的就是 **2026-11-18**。

**读者会怎么误读：** 客户在自己机器上查 tag，看到 2026-11-18，与素材里
「tagged 2026-11-17」不一致。日期差一天本身不严重，但**这正好是「数字写错」
这类问题最容易被当场抓住的一类**——一条 `git` 命令就能验证。

**建议改法（去掉时区歧义，最省事）：**

> - The current release is `v1.0.0` (the `v1.0.0` tag in the repository); the
>   public contract covers the documented CLI/API/MCP surfaces.

若一定要留日期：`tagged 2026-11-17 UTC (2026-11-18 in UTC+8)`。

---

### F-9｜`project-brief.md` 说证据包里是「the report + a manifest」，实际是 4 个条目

**原文（`docs/outreach/project-brief.md:118-119`，逐字）：**

> - Evidence packages, one per case study, each a zip holding the report and a
>   manifest of hashes:

**仓库实况：** 三个 zip 的内容逐字相同（4 个条目）：

```
reports/report.html
reports/report.json
reports/report.md
manifest.json
```

`manifest.json` 的 `files` 列表里 3 条，role 都是 `report`——manifest **只**哈希
这 3 份报告。所以包里是 **3 份报告 + 1 份 manifest**，不是 2 个东西。

`src/dexatlas/reports/evidence_package.py:136-161` 的 `package_file_summary`
就是按这个口径写的，CLI 打印的是：

> `4 files: 3 reports + 1 manifest`

（这条是本轮刚修的：提交 `f22f5e1`「修 `dexatlas export` 的文件数：打印归档
自己的条目数，不再是清单里的报告数」——之前它打印的是「3」。）

**读者会怎么误读：** 客户打开 zip 看到 4 个文件、3 份报告，和「the report and
a manifest」对不上；也可能以为包里只有一份报告、另外两份是重复的。

**建议改法：**

> - Evidence packages, one per case study, each a zip holding the three report
>   formats (Markdown, HTML, JSON) and a manifest that hashes them:

再补一句（可选，能防住「当成三份独立证据」）：

>   The CLI prints `4 files: 3 reports + 1 manifest` for each package.

---

### F-10｜`publish-review.md` §8 的门禁记录已经过期，且同一份文件里两个数打架

**原文（`docs/outreach/publish-review.md:360` 与 `:362`，以及 `:382` 的脚注）：**

> | `uv run --no-sync pytest tests/test_docs.py` | **60/60 通过，0 跳过** |
> | `uv run --no-sync python scripts/check-version-claims.py --base auto` | **exit 1**，findings 3 条：2 条历史遗留（`docs/releases/v0.2.0.md`、`CHANGELOG.md` 里的旧版本覆盖率）+ 1 条 `docs/reports/outreach-recheck.md` 自己的过期事实。… |

脚注 `:382` 却写：

> 装齐后收集到 1,620，与报告一致，test_docs.py 才 62/62

**实况（本轮复跑，只读）：**

| 门禁 | `publish-review.md` 记的 | 本轮实测 |
|---|---|---|
| `check-version-claims.py --base auto` | exit 1，findings 3 条 | **exit 0，findings 2 条**（两条都是历史遗留：`docs/releases/v0.2.0.md:326`、`CHANGELOG.md:1072`；第 3 条 `docs/reports/outreach-recheck.md` 那条已经不存在了） |
| `check-doc-citations.py` | 220 citations，unresolved 0，drifted 0 | **222 citations（工作副本）+ 64（v1.0.0 树），unresolved 0，drifted 0** |
| `tests/test_docs.py` | 表格写 60/60，脚注写 62/62 | **未跑**（本轮无 venv，且主会话正在跑重测量，不去抢）。但同一份文件里的 60 与 62 本身就矛盾 |

**建议改法：**

- `:360` 与 `:362` 两行按上表改（exit 0 / findings 2；citations 222）。
- 60/60 与 62/62 二选一，并把另一处改掉——这是本文件里唯一的**自相矛盾**。

---

## 3. 低后果发现（措辞与一致性）

### F-11｜`README.md` 社交预览的 alt 文字里测试数是旧的（1612）

**原文（`README.md:21`，逐字）：**

> <img src=".github/social-preview.png" alt="DexAtlas — From APK to Evidence: 93.3% first-party code coverage, 1612 tests, 49 public contract checks" width="900">

当前测量是 **1632**。这个 alt 文字是**手写的**：`scripts/refresh-report-figures.py`
只改两个 badge（`BADGE_TESTS` / `BADGE_COVERAGE`，见脚本 `:900-903`），
不碰 alt 文字；`00309bb` 的说明里提到「social preview 图重画」——那是重画**图**，
图上的数字已经是 1632 / 1485，但 alt 文字留在了 1612。

**注意：** `README.md` 是主会话测量脚本会写的文件，而脚本**不会**改这一行，
所以重测量不会顺手把它修好，需要单独改。

**建议改法：** `1612 tests` → `1632 tests`。
（`49 public contract checks` ✅ 正确，不用动。）

### F-12｜`portfolio.md` 的 `1632` 没有千分位，四份素材都是 `1,632`

`docs/portfolio.md:67` 写 `1632 tests at 93.3% coverage`，四份素材统一写
`1,632`。客户并排看两份材料时，会以为这是两个数。

**建议改法：** 统一成 `1,632`。

### F-13｜素材里 `93.3%` 与 `1,632` 之间的**相对**关系没被否定

这一条是 F-2 / F-3 的读者侧后果，单独列出是因为它最容易被忽略：素材把
`1,632 automated tests, 93.3% coverage` 并列成一句，读起来像「1,632 个测试
覆盖了 93.3% 的代码」——而覆盖率的分母是**代码行**（7,650 行），不是测试数。

**建议改法：** 在首次出现覆盖率的地方加一个分母，例如
`93.3% of 7,650 lines of the project's own code`。

---

## 4. 确认过且没问题的部分

这一节是为了让人知道**查过哪些**，以及**哪些不需要再改**。

### 4.1 数字：换得干净

| 项 | 素材里的值 | 报告落盘值 | 结论 |
|---|---|---|---|
| 测试总数 | 1,632（四处） | `<!--fig:tests.total-->1632<!--/fig-->` | ✅ |
| 快测 / 集成 | 素材**未写**拆分 | `<!--fig:tests.fast-->1485<!--/fig-->` / `<!--fig:tests.slow-->147<!--/fig-->` | ✅ 没有可被误读成「两套测试」的表述 |
| 覆盖率 | 93.3% | `<!--fig:coverage.pct-->93.3%<!--/fig-->` | ✅ 数值一致（**限定词**另见 F-2） |
| 覆盖行数 | 素材**未写** | `<!--fig:coverage.covered-->7135<!--/fig-->` / `<!--fig:coverage.total-->7650<!--/fig-->` | ✅ 素材没提，所以没有对不上的行 |
| CLI 命令数 | 素材未写总数，只列了 7 个（其中 3 个有错） | `<!--fig:cli.commands-->13<!--/fig-->` | ⚠ 见 F-1 |
| API 端点数 | 素材未写 | `<!--fig:api.endpoints-->23<!--/fig-->` | ✅（数 `src/dexatlas/api/app.py` 的 `@app.<verb>` 装饰器：23 个，与落盘一致） |

- **没有半截旧数。** 四份素材里搜不到 `1,620` / `1,588` / `1,584` / `1,540` /
  `7,117` / `7,631` / `93.1%` / `93.2%`。
- **同一份素材里没有两个数打架。** 素材之间也没有：四处都是 1,632 / 93.3%。

### 4.2 事实：逐条核过，都对得上

| 素材里的说法 | 实况 | 结论 |
|---|---|---|
| 「Eleven tools over stdio」（三处） | `src/dexatlas/mcp/server.py` 的 `@server.list_tools()` 注册 **11** 个（`list_projects`、`get_project_status`、`get_manifest`、`search_symbols`、`get_class_source`、`get_method_source`、`find_callers`、`find_callees`、`get_evidence`、`resolve_locator`、`find_resource_declarations`） | ✅ |
| 「no write path, no shell, no model dependency in the tool layer」 | `mcp/server.py` 的模块与函数 docstring 明写 never writes / never runs a shell / never calls a model | ✅ |
| 「three integrated third-party engines」（Androguard / JADX / Apktool） | 三个后端都在 `src/dexatlas/tools/` 下，归属在素材里逐个点名并声明不是自有工作 | ✅ |
| 「three complete case studies」 | `docs/case-studies/` 三篇（`demo-app-walkthrough.md`、`obfuscated-app.md`、`api-integration.md`），README 首句「Three complete walkthroughs」 | ✅ |
| 「three first-party samples (demo, obfuscated, and a multi-DEX appendix)」 | `examples/demo-app/demo.apk`、`examples/obfuscated-app/obfuscated.apk`、`examples/multidex-app/multidex.apk`；仓库另有 `strings-app`、`wide-app`（共 5 个一方 APK） | ✅ |
| 「the three evidence packages hold **only two analyses**」 | 我逐字节核过：`demo` 与 `api-integration` 的 `reports/report.md` sha256 同为 `1594a0c1…`、`reports/report.html` 同为 `82bcb84c…`；`report.json`（`56251060…` vs `2a08ab09…`）与 `manifest.json` 不同 | ✅ 素材说得完全准确 |
| 「mypy strict / ruff / CI across Python 3.12/3.13」 | `ci.yml` 的 `lint` job + `test` 矩阵 `["3.12","3.13"]` | ✅ |
| 「the web workbench covering project dashboard, upload and analysis progress, search and evidence, cross-references, the agent workspace, and report export」 | `src/dexatlas/workbench/app.py` 19 条路由，逐项对得上（`/api/projects`、`/api/uploads`、`/api/agent/*`、`/api/projects/{id}/report`、`/api/projects/{id}/callers|callees`） | ✅ |
| 「Benchmark harness. Scripted and real-model comparison runs with committed traces; scripted and real-model results are reported separately and never mixed」 | `docs/benchmarks/` 下 `comparison-traces.json`、`comparison-real-traces.json`、`comparison-stronger-traces.json` 等 | ✅ |
| 「12 条相对链接逐条存在」（`publish-review.md` §4.1） | 我用同一条正则逐条复跑：**12 条，全部存在** | ✅ |
| 第三方归属、三个引擎各自的产出 | `docs/analysis-provenance.md` 与素材口径一致 | ✅ |

### 4.3 过度承诺：没发现把草稿说成交付

- 四份素材首尾都有 `Draft for review — not published.`，**没有**「已上线 /
  已发布服务」这类措辞。
- **M6 的 49/60 = 81.7% 在四份素材里一次都没出现**（我逐份搜过）。这正是
  `publish-review.md` §6 说的「不提即不宣称」——这一条守住了。
  `publish-review.md` §6 末尾的**反向风险**提醒仍然成立：发布时若要写
  「agent 实测准确率」，必须同时写明**未达 ≥90% 验收线**。
- **M10 没有被说成已完成**：四份素材一次都没提 M10；`docs/status.md` 写着
  独立验收尚未开始，口径一致。
- 素材里的 acceptance / milestone 全部是**对客户的服务承诺**（开工前写下的
  验收标准、里程碑复盘），没有把 DexAtlas 自身的验收说成已完成。
- 没有客户案例、收益、工时节省、安全测试结果的宣称；identity note 四份齐全。
- 「把 APK 里的指令当数据而非命令」有实现支撑：
  `src/dexatlas/agent/orchestrator.py` 的系统提示 + MCP 侧的 `UntrustedText` 包装。
- 反向风险提示：F-2（覆盖率口径）与 F-3（failed=1）是这一轮**唯一**两处
  「守住了口径却漏在别处」的地方——两处都在**改动落盘后没同步**的缝里。

### 4.4 字符数：§5 的表 14 行全部可复算

我逐字抽出 `publish-review.md` §5 的脚本执行，结果与表里**逐行相同**：

| 字段 | 表里 | 实算 |
|---|---|---|
| Template 1 正文 | raw 2,185 / plain 2,174 | 2185 / 2174 ✅ |
| Template 2 正文 | raw 2,500 / plain 2,485 | 2500 / 2485 ✅ |
| `scope-ai-mcp.md` §What I offer | raw 781 / plain 773 | 781 / 773 ✅ |
| `scope-backend-automation.md` §What I offer | raw 592 / plain 588 | 592 / 588 ✅ |
| `scope-ai-mcp.md` 全文（附件） | raw 6,561 / plain 6,530 | 6561 / 6530 ✅ |
| `scope-backend-automation.md` 全文（附件） | raw 4,950 / plain 4,941 | 4950 / 4941 ✅ |
| `project-brief.md` 七节 | 53 / 438 / 1410 / 311 / 1455 / 458 / 426（raw） | 全部一致 ✅ |

`scope-ai-mcp.md` 文件头写的「773 characters as written」也与实测一致。

**但 `publish-review.md` §7 第 2 条因此需要复核：** 它写「Template 2 raw
2,500 / plain 2,485（**正好压线，余 0**）」。按 §5 的口径（取 raw 与 plain
的**较大者**判定），Template 2 的 raw **正好等于** 2,500——余量确实是 0，
但这条是**卡在边界上**：占位符一旦替换后变长（用法说明里写明「通常更长」），
就会超。§7 第 2 条已经提醒要按实际粘贴的那一版复算，这里只是把它标成
「压线」而不是「超」，二者并不矛盾——但发布前必须重算。

### 4.5 M6 与其它基准：素材没引用，所以不必改

| 量 | 值 | 来源 |
|---|---|---|
| M6 层级 2 实测 | 49/60 = 81.7%（逐轮 15/16/18），**未达** ≥54/60（≥90%） | `docs/benchmarks/m6-level2-retest4.md:38`、`:83` |
| M6 窄验证二轮 | 转通过 **2/6**（门槛 ≥4），未达标 | `docs/benchmarks/m6-level2-narrow-verify2.md:59-61` |
| M6 窄验证三轮 | 转通过 **3/6**（门槛 ≥4），未达标 | `docs/benchmarks/m6-level2-narrow-verify3.md:59-61` |
| `publish-review.md` §0 的这三行 | 与上面逐字一致 | ✅ |

`publish-review.md` §0 那张「核对基准」表里，**除覆盖率的两行数（F-6）外全部正确**。

---

## 5. 复核方法（都可复算）

```bash
# 素材里的数字出处
grep -n "fig:" docs/reports/phase1-execution-report.md

# CLI 的 13 个命令
grep -n "@app.command" src/dexatlas/cli/main.py

# MCP 的 11 个工具
grep -n 'name="' src/dexatlas/mcp/server.py

# API 的 23 个端点
grep -rn "@app\.\(get\|post\|put\|delete\)(" src/dexatlas/api/app.py

# 三个证据包的条目与字节
python -c "import zipfile;z=zipfile.ZipFile('docs/case-studies/attachments/demo-evidence-package.zip');print(z.namelist())"

# 两个只读门禁（本轮实跑：exit 0 / unresolved 0 / drifted 0）
python scripts/check-doc-citations.py
python scripts/check-version-claims.py --base auto
```

**本轮没有跑：** `pytest`（无本 worktree 的 venv，且主会话正在跑重测量，
不去抢 `.coverage`）、`scripts/refresh-report-figures.py`（会写测量产物）、
任何联网命令、任何发布接口。

---

## 6. 给主会话的处置顺序

1. **先等这轮重测量落盘**，再定 F-3 的措辞（F-3 是唯一一条会被测量改写的）。
2. **F-1 与 F-2 可以立刻改**——它们不依赖测量结果。
3. F-4 / F-5 / F-9 / F-11 / F-12 与测量结果无关，可一并改。
4. F-6 / F-7 / F-8 / F-10 是 `publish-review.md`（内部记录）的自洽性问题，
   改素材时顺手改掉即可。
5. **注意顺序副作用**：本轮主会话一旦重测量，`tests.total` / `coverage.*` /
   `suite.*` / 源指纹**都可能再变一次**，四份素材里的数字要跟着再同步一遍。
   建议等测量彻底落盘、连跑两次数字不再变之后，再一次性改完本报告里的全部
   建议句。
