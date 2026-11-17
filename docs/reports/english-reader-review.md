# 英文读者视角终检（只读复核）

**日期：** 2026-11-17
**范围：** 五份对外英文文本
**性质：** 只读复核。**未修改任何被核文本**，除本文件外未改动仓库任何文件。

| 被核文本 | 行数 | 角色 |
|---|---|---|
| `docs/releases/v1.0.0.md` | 166 | 发版说明（正式） |
| `docs/reports/v1.0.0-github-release-body.md` | 330 | GitHub Release 正文草稿（含中文摘要与数字出处附录） |
| `README.md` | 546 | 项目门面 |
| `docs/portfolio.md` | 120 | 客户简报 |
| `docs/architecture/README.md` | 415 | 架构说明 |

---

## 1. 读者人设与方法

**读者人设：** 第一次看到 DexAtlas 的英文读者——评估这个开源项目的技术负责人，或在 Upwork 上读到它的人。不懂本项目历史，也不需要懂。只读得到上面这五份英文文本。

**为什么这一轮不一样：** 前几轮核的是「数字对不对」「说法一致不一致」。这一轮核的是另外一类问题：**文本能不能被一个没有背景的人顺畅地读下去**，以及**读完之后他会形成什么印象、其中哪些是文本造成的错觉**。因此本报告的判据不是「与源码是否一致」（那一轮已经做过），而是「读者会怎么读、会怎么想」。

**只读边界（严格遵守）：**

- 未跑 `pytest --cov`、未跑任何 `coverage` 命令、未 `uv sync`、未跑 `scripts/refresh-report-figures.py`。
- 只跑了两个只读门禁：`scripts/check-doc-citations.py`（220 条引用，0 漂移）、`scripts/check-version-claims.py --base auto`（2 条既有项，无新增）。
- **`pytest tests/test_docs.py` 在本 worktree 跑不起来**：`.venv` 未安装本项目（`ModuleNotFoundError: No module named 'dexatlas'`），而任务禁止 `uv sync`。改为**按 `tests/test_docs.py` 的正则逐条复刻**其中两个全仓库扫描断言——`test_all_relative_links_resolve`（相对链接）与 `test_every_embedded_image_resolves`（内嵌图片）——覆盖全仓 120 个 markdown：**0 断链、0 缺图**（含本报告自身）。
- 结论凡属推断均标「推断」并给出依据行号；凡属事实均给出出处行号。
- 本报告不含任何密钥或凭据样式字符串。

**辅助核查（只读）：** 五份文本共 115 条相对链接，逐条解析目标是否存在——**0 条断链**；本报告自身的链接也按同一规则校验通过。因此下文「指路」一类的发现**不是断链**，而是**链接文字与落点内容对不上**，或**读者点进去之后拿不到需要的东西**。

---

## 2. 速览

| 类别 | 条数 |
|---|---|
| 门槛（读者需要已有背景才读得懂） | 19 |
| 术语（同一概念不同处不同词） | 9 |
| 吹过头／读起来像在许诺 | 10 |
| 拼写与大小写 | 5 |
| 指路（链接措辞／落点） | 5 |
| 中英不等价 | 1 |
| **合计** | **49** |

**必须改的 16 处**见第 5 节，按「会让读者误判」排序。

### 最容易让英文读者误判的三处

1. **[`README.md:32`](../../README.md#L32) 与 [`README.md:545`](../../README.md#L545)** —— 顶部说「`v1.0.0` released (tag 2026-11-17)」，底部说「`v1.0.0` is considered only after this plan's exit criteria pass」，而同一页的 M6/M8/M10 三行都写着未完成。读者读完整页的结论是「这个版本违反了自己定的门槛」。
2. **[`README.md:47`](../../README.md#L47)／[`README.md:539`](../../README.md#L539) 与 [`docs/releases/v1.0.0.md:24`](../releases/v1.0.0.md#L24)** —— 同一个失败测量，README 说「40.0% over three rounds against ≥80%」，发版说明说「against the ≥90% acceptance bar」。两条线都真实存在，但各说各的，读者会判定「验收线被挪过」。
3. **[`docs/releases/v1.0.0.md:64`](../releases/v1.0.0.md#L64)／[`docs/reports/v1.0.0-github-release-body.md:96`](v1.0.0-github-release-body.md#L96) 与同文件 [`:312`](v1.0.0-github-release-body.md#L312)** —— 正文说「the public contract table frozen with **49** live checks」，附录说「no run executes all of them」（实跑最多 48 项，且那次退出码 1）。读者只会记住正文的 49。

---

## 3. 逐条发现

### 3.1 `README.md`

| 位置 | 原文 | 英文读者会怎么读（读者口气） | 类别 | 建议改法 |
|---|---|---|---|---|
| [`:5`](../../README.md#L5) | 「**From APK to Evidence — Powered by AI Agents.**」 | 「AGENTS 是复数——这项目里好几个 AI agent？」实际上项目只有一个 agent（portfolio 称之为「a single-loop, evidence-checked agent」）。 | 吹过头 | 改为「Powered by a bounded AI agent.」或直接删掉后半句 |
| [`:19`](../../README.md#L19) | 「turns an APK into a complete, verifiable picture」 | 「complete？那遇到解不开的 APK 也全给我？」紧接着 `:28-29` 却说「an APK that defeats the decompiler still yields a manifest, an index and a report that says which steps did not run」——前后打架。 | 吹过头 | 「…into a picture you can verify — as complete as the installed backends allow; the report names what is missing」 |
| [`:32`](../../README.md#L32) | 「**Status: early development — `v1.0.0` released (tag 2026-11-17); Phase 3 is delivered**」 | 「Phase 3 交付了 = 三个里程碑都做完了？」但同页 `:539` M6 partly done、`:541` M8 partly done、`:543` M10 acceptance not run。 | 吹过头 | 「Phase 3's delivery cut is published; M6, M8 and M10 remain partly open (see Roadmap status)」 |
| [`:32`](../../README.md#L32) vs [`:545`](../../README.md#L545) | 「`v1.0.0` released (tag 2026-11-17)」／「`v1.0.0` is considered only after this plan's exit criteria pass」 | 「这项目自己说退出标准全过才发 1.0.0，而退出标准明明没过（`docs/status.md` 也这么写）。这一版是违规发的。」**读者读完整个 README 都会停在这里。** | 吹过头 | `:545` 改为陈述现状，例如「`v1.0.0` is the Phase 3 delivery cut. The phase's exit criteria are not all met — M6, M8 and M10 are listed above with what is still open.」 |
| [`:36`](../../README.md#L36) | 「The MCP server, the evidence-first agent and the web…」 | 「MCP 是什么？」展开全称要到 `:218` 才出现，中间 180 行。 | 门槛 | `:36` 首次出现处加全称「the MCP (Model Context Protocol) server」 |
| [`:37`](../../README.md#L37)、[`:39`](../../README.md#L39) | 「the web workbench's M4 screens」「the M3 benchmark view」 | 「M4？M3？编号哪来的？」五份文本里没有任何一处给出 M 编号的对照表，而 Phase 3 plan 只覆盖 M5–M10，M3/M4 无处可查。 | 门槛 | 加一句图例「M3–M10 are the project's milestone numbers; M5–M10 are Phase 3's, listed in the Phase 3 plan」，并把 M3/M4 改成直述（「the benchmark view」「the eight workbench screens」） |
| [`:33`](../../README.md#L33)、[`:43`](../../README.md#L43)–`:64` | 「the M6 agent acceptance line and the M10 independent acceptance」「M5 (claims baseline) and M7 (client-ready deliverables) are done; M6 …」 | 「从 M5 跳到 M10，中间 M1–M4 呢？这是一份给外人看的状态说明，却整篇用内部代号。」 | 门槛 | 同上：给 M 编号一句图例，或首次出现时写成「M6 (the bounded agent milestone)」 |
| [`:46`](../../README.md#L46)–`:47`、[`:539`](../../README.md#L539) | 「DexAtlas 40.0% over three rounds against ≥80%」 | 「40.0% 是三轮合计，拿它去比 80%？」——≥80% 是**单轮**线（依据 `docs/roadmap/ROADMAP.md:386`：「≥80% per round, ≥90% over three rounds」）。数字不算错，但种类不同，读者会把 80% 记成「三轮门槛」，再去发版说明里看到 90%，于是怀疑门槛被换过。 | 吹过头 | 「DexAtlas 24/60 = 40.0% over three rounds (per round 45%/40%/35%), below the ≥80% per-round line and below the ≥90% three-round bar」 |
| [`:27`](../../README.md#L27) | 「Conclusions are graded `verified` / `lead` / `insufficient`」 | 「lead 到底什么意思？」README 只列名字不给释义；定义实际在 `docs/portfolio.md:33-36` 与 `docs/architecture/README.md:147-158`，README 没有链过去。`:308` 又直接用「what is a lead」。 | 门槛 | 在 `:27` 就地加三个词的半句释义，或链到 `docs/architecture/README.md#evidence-levels` |
| [`:402`](../../README.md#L402)–`:403`、[`:416`](../../README.md#L416)、[`:422`](../../README.md#L422) | 「the 20 frozen questions **the agent service promise** is measured against」「the service-promise scope is to be re-decided」 | 「service promise 是什么？我以为这项目是个 CLI——它承诺做一个 service？服务范围是什么、跟普通功能承诺有什么区别？」五份文本里没有任何一处定义过它；定义在 `docs/service-commitments.md`（中文），而**全仓库没有任何一份文档链接到那份文件**（grep 零命中）。 | 门槛 | 首次出现处就地点明「the service promise — the scope of analysis the agent is committed to deliver on the frozen set」，并链到 `docs/service-commitments.md`（该文件需出英文版） |
| [`:131`](../../README.md#L131) | 路线图表 Phase 3 行的 Scope 单元格 | 「这一格读不下去。」——一个约 90 词、五个分号隔开的从句串，里面还嵌着 40.0%、81.7%、2/6、3/6、≥4/6、≥90% 六个数字，且这些数字 `:46-59` 已经写过一遍。 | 门槛 | Scope 单元格压到 15 词以内，数字全部留在 `:46-59` 与 `:539` |
| [`:411`](../../README.md#L411)–`:412` | 「The 853,103 tokens spent exceeded the authorized 800,000 cap, so the full 92-question sweep did not run.」 | 「所以题集其实是 92 题？我这轮 60 次是因为超预算被砍了？」这句在「M6 level-2 real-model batch（20 questions, 3 rounds）」的小标题下，但 92 题是**更早的旧题集**（依据 `docs/benchmarks/m6-level2-real.md:113`、`:121`）。 | 门槛 | 补一句「the older 92-question set, a different and superseded sweep」，并把 853,103 与该句的关系改成「预算上限之内已用满，因此未再跑旧题集」 |
| [`README.md:458`](../../README.md#L458)–`:459`、[`README.md:460`](../../README.md#L460)–`:461`、[`README.md:477`](../../README.md#L477)–`:479` | 「Current status → `docs/status.md` — …（Chinese; 当前状态）」「Analysis coverage & provenance → `docs/analysis-provenance.md` …（Chinese; 分析覆盖度与证据来源）」 | 「README 是英文的，我以为点进去也是英文——结果五个最可能被点的链接（HANDOVER 之外的状态、覆盖度、三份评审记录）全是中文。」标注是诚实的，但读者读完英文门面就被挡在门外。 | 门槛 | 每个中文文档在链接处补一句英文摘要（它说了什么、我为什么要点它），或提供英文摘要页 |
| [`:472`](../../README.md#L472)–`:473` | 「The source review is done: 44 findings across three reviews, every one of them re-verified against the tree it was found on.」 | 「44 个发现——是 44 个还没修的缺陷，还是 44 件已修的事？严重度呢？」「the tree it was found on」也是行话。 | 门槛 | 就地给出严重度分布并链到已存在的英文文档：`docs/releases/phase1-acceptance-2026-10-21.md:29`–`:36` 已有该表（Blocking 6 / Important 16 均已修，Optional 12 与 Deferred 9 有说明），补一句链接即可，不必另写 |
| [`:21`](../../README.md#L21) vs [`:368`](../../README.md#L368) | 「an evidence trail that records …」／「[From upload to evidence chain]」 | 「trail 和 chain 是两样东西吗？」同一个概念两个词。 | 术语 | 全文统一一个词。建议保留 evidence trail（README、portfolio、Release 正文都用它），把 evidence chain 改成 evidence trail |
| [`:131`](../../README.md#L131)、[`:466`](../../README.md#L466)、[`:532`](../../README.md#L532) | 「Portfolio & Delivery」「the portfolio plan」「Phase 3 … is a portfolio push」 | 「portfolio 是产品组合还是投资组合？」软件语境里 portfolio 通常指产品线集合；这里指的是「面向客户的一套交付物」，但五份文本没有任何一处解释这个词。 | 术语 | 首次出现处就地点明（例如「the portfolio phase — the set of client-facing deliverables」），或换用无歧义的词（client-delivery phase） |
| [`:106`](../../README.md#L106)、[`:516`](../../README.md#L516)–`:522` | 「A conclusion you cannot click back to is not a finding.」「they are not features, not selling points, not demos.」 | 「这个项目敢说自己的边界，不吹。」 | 保留 | 不要在改稿时误伤这两句 |

### 3.2 `docs/releases/v1.0.0.md`（发版说明）

| 位置 | 原文 | 英文读者会怎么读（读者口气） | 类别 | 建议改法 |
|---|---|---|---|---|
| [`:1`](../releases/v1.0.0.md#L1) | 「# DexAtlas v1.0.0 — The Evidence-First Portfolio Milestone」 | 「Portfolio Milestone 是什么意思？portfolio 在软件发布标题里通常指产品组合。」而且 Phase 3 里明明有六个里程碑（M5–M10），这里把整个阶段叫作一个 milestone。 | 术语 | 改成不含未定义词的标题，例如「DexAtlas v1.0.0 — the Phase 3 delivery cut」 |
| [`:3`](../releases/v1.0.0.md#L3)–`:9` | 「Phase 3's portfolio-and-delivery milestone: the claims baseline re-verified against the code (M5), a frozen 20-question service regression set for the agent with honest level-2 results (M6), …」 | 「一整段都是括号里的代号，而且『claims baseline』『service regression set』都没解释过。」 | 门槛 | 代号后就地加一句话说明该项是什么（六项各一句），并删掉对「portfolio」的依赖 |
| [`:24`](../releases/v1.0.0.md#L24) | 「scored **24/60 = 40.0%** (45%/40%/35% per round) against the ≥90% acceptance bar — not passed」 | 「≥90%？README 里同一件事写的是 ≥80%。门槛到底是 80 还是 90？」≥90% 是三轮线，≥80% 是单轮线，两条都真实（依据 `docs/roadmap/ROADMAP.md:386`），但两篇各说一条。 | 吹过头 | 与 README 同步改成两句：「below the ≥80% per-round line and below the ≥90% three-round bar」 |
| [`:49`](../releases/v1.0.0.md#L49) | 「per the acceptance plan's **option 3, status disclosure**（方案 3，现状披露）investment stopped for good」 | 「一份英文发版说明里嵌了一段中文。」带全角括号，在 GitHub 上与周围半角排版不齐。 | 拼写 | 删掉括号里的中文，只留英文；中文版本另出 |
| [`:64`](../releases/v1.0.0.md#L64) | 「the public contract table frozen with **49** live checks (28 REST + 6 MCP + 15 CLI)」 | 「49 项活检——所以 49 项全过？」同一个文件的附录 [`:312`](v1.0.0-github-release-body.md#L312) 写的是「49 is the number of `check()` call sites; **no run executes all of them**」，实跑最多 48 项、那次退出码 1。正文只给 49，读者只会带走 49。 | 吹过头 | 正文补一句：「49 is the number of checks in the table; no single run executes all of them (the all-backends run executes 48 and ends with 46 passing and exit 1)」 |
| [`:113`](../releases/v1.0.0.md#L113) | 「Nothing in these release notes is a completed acceptance.」 | 「所以这些发版说明整体不算验收通过的说明？」这句话本身诚实，但放在正式发版说明末尾，读者会困惑「我到底该不该信这份东西」。 | 门槛 | 改成正向表述：「Independent acceptance has not run; what follows is the project's own record, not an accepted result.」 |
| [`:163`](../releases/v1.0.0.md#L163) | 「## Licence」 | 与 README 的「## License」（`:524`）不一致；同一套文本里英式/美式混用。 | 拼写 | 统一为美式「License」（与 README、徽章一致） |

### 3.3 `docs/reports/v1.0.0-github-release-body.md`（Release 正文草稿）

| 位置 | 原文 | 英文读者会怎么读（读者口气） | 类别 | 建议改法 |
|---|---|---|---|---|
| [`:1`](v1.0.0-github-release-body.md#L1) | 「# DexAtlas v1.0.0 — The Evidence-First Portfolio Milestone」 | 同 3.2 第一条：这是**要贴到 GitHub 上的标题**，英文读者第一眼就撞上未定义词。 | 术语 | 同 3.2 |
| [`:37`](v1.0.0-github-release-body.md#L37)–`:48` | 「Four fixes landed together: ① … ② … ②b … ③」 | 「到底四项还是五项？②b 到底是 ② 的一部分还是第五项？」而且 ①②③ 是中日韩的全角带圈数字，在英文 Release 里排版突兀，GitHub 字体覆盖也不一致。 | 术语 | 改成 (1)(2)(3)(4) 或 a/b/c/d，并把 ②b 明确写成 ② 的子项或独立第四项 |
| [`:50`](v1.0.0-github-release-body.md#L50) | 「**Two review leftovers closed (M-1 / L-1).**」 | 「M-1、L-1 是哪次评审的编号？」编号在正文里没有出处，读者无法定位。中文摘要 `:231-232` 同样只写「M-1 裁剪内容可追溯、L-1 宽页行裁剪补全」。 | 门槛 | 加一句「from the read-only source review of the agent's evidence path」并给出评审记录链接 |
| [`:62`](v1.0.0-github-release-body.md#L62) | 「Scoring semantics and **the seven red lines** are unchanged.」 | 「seven red lines 是什么？」这个**英文措辞**全仓库只此一处；对应的中文说法「判分七条红线」见于 `CHANGELOG.md:27` 与 `docs/benchmarks/m6-verify3-plan.md:3`，其判分语义由代码 `benchmarks/model.py::check` 定义（见 `docs/benchmarks/service-regression-set.md:166` 第 5 条）。英文文本既不解释，也不指向任何出处。 | 门槛 | 就地给出出处与含义，或改成明说的表述（「the seven rules the scorer refuses to relax, defined in `benchmarks/model.py::check`」） |
| [`:125`](v1.0.0-github-release-body.md#L125) | 「**The frozen discipline holds**: the system is fixed or the service promise is narrowed and restated — questions are never deleted to move a rate.」 | 「frozen discipline 是什么？谁定的？」这个**英文措辞**全仓库只此一处；其定义在 `docs/benchmarks/service-regression-set.md:155` 的《5. 冻结纪律》（中文），而 README `:402` 恰好链接到那份文件——读者点进去撞上一整页中文。「the service promise」同理：五份文本从未定义（README `:403`、`:416`、`:422` 也在用）。 | 门槛 | 「the frozen discipline」改成白话（「the rule the acceptance plan sets: …」），「the service promise」首次出现处就地点明它指的是什么（面向客户的服务范围承诺）；两者都补一条指向定义文件的链接（该文件需出英文版） |
| [`:146`](v1.0.0-github-release-body.md#L146)–`:150` | 「**What this release does not include:** no native or dynamic analysis …; no plugin ecosystem …; no published service page; no macOS verification (Windows and Linux are the tested platforms); and it is not a security audit, a penetration test, a malware verdict or a packer bypass.」 | 英文读者读到的是清晰边界。**但中文摘要完全没有这一段**（`:221-260`），中文读者不会知道「不含动态分析」「macOS 未验证」「不是安全审计」。 | 中英不等价 | 中文摘要补一条对应条目（尤其「无 macOS 验证」「不做动态分析」「不是安全审计」），与英文正文逐条对齐 |
| [`:209`](v1.0.0-github-release-body.md#L209)（同 [`docs/releases/v1.0.0.md:158`](../releases/v1.0.0.md#L158)） | 「repeated analyses no longer drift the CLI report's `created_at` **from** the stored row」 | 「drift from the stored row」读起来方向反了——是报告的 `created_at` 与库里的值不一致（drift away from），还是从库里漂走？ | 术语 | 改成「repeated analyses no longer make the CLI report's `created_at` differ from the stored row's」 |
| [`:216`](v1.0.0-github-release-body.md#L216) | 「## Licence」 | 同 3.2 最后一条。 | 拼写 | 改「## License」 |
| [`:304`](v1.0.0-github-release-body.md#L304)–`:305` | 「M6 is still open; **B1** not closed; option 3 (status disclosure) is the final path」「Three-round total 49/60 = 81.7%, still below **the B1 line**」 | 「B1 是什么？」英文文本里 **B1 只出现在这个附录**，没有定义；定义在 `docs/status.md:133`（中文，同一文件 README `:458` 链过去时标注了「Chinese; 当前状态」）。附录虽标注「不属于正文」，但读者会打开它。 | 门槛 | 附录行内加注：「B1 (the M6 level-2 acceptance line: ≥16/20 per round and ≥54/60 over three rounds)」 |
| [`:3`](v1.0.0-github-release-body.md#L3)–`:8` | 「Every figure below is copied verbatim from a file in this repository; the file and line are listed in the appendix.」 | 「这个项目把每个数字的出处都写出来了。」 | 保留 | 不要在改稿时误伤 |

### 3.4 `docs/portfolio.md`（客户简报）

| 位置 | 原文 | 英文读者会怎么读（读者口气） | 类别 | 建议改法 |
|---|---|---|---|---|
| [`:11`](../portfolio.md#L11)–`:13` | 「turns an APK into a complete, verifiable picture」 | 同 3.1 第二条：complete 与「which steps did not run」自相矛盾。 | 吹过头 | 同 3.1 |
| [`:12`](../portfolio.md#L12)／[`:32`](../portfolio.md#L32)／[`:109`](../portfolio.md#L109) | 「an evidence trail that records …」／「**An evidence model with levels.**」／「from upload to evidence **chain**」 | 「trail、model、chain 三个词指同一个东西吗？」 | 术语 | 统一：trail（总称）／model（分级结构）／chain 不要用，或每次出现时说明与前两者的关系 |
| [`:14`](../portfolio.md#L14)–`:16` | 「It runs from the command line, over a REST API, from an MCP server …, through a built-in agent …, or in a local web workbench.」 | 「五种入口？」但 `docs/architecture/README.md:57` 的图注写「one analysis core, **three transports**」（cli / api / mcp），README `:253-254` 说 workbench 是 in-process 调同一批工具、`:312` 说 agent 是库。读者会把 workbench 和 agent 误当成两个独立传输通道。 | 术语 | 加半句说明：「the workbench calls the same tools in-process and the agent is a library, so the core still has three transports」 |
| [`:15`](../portfolio.md#L15) | 「from an **MCP** server your AI assistant can call」 | 「MCP 是什么？」这份简报是给不读 README 的人看的，MCP 在 portfolio 里从未展开。 | 门槛 | 首次出现处写全称「MCP (Model Context Protocol) server」 |
| [`:66`](../portfolio.md#L66)–`:69` | 「1,588 tests at 93.3% coverage on the first-party code, and **six CI jobs** covering different backend configurations (all three backends; none of the Java-based ones; Apktool only) **plus** Docker and dependency audit」 | 「括号里三个配置 + Docker + 依赖审计 = 五项，哪来的第六项？」第六项是 lint/format/mypy，但文中没提。读者数着数不对，会怀疑数字是凑的。 | 吹过头 | 写成「six CI jobs: lint/format/mypy, three test configurations (all backends / no Java backends / Apktool only), the Docker image, and the dependency audit」 |
| [`:66`](../portfolio.md#L66) | 「1,588 tests」 | 与 README 徽章「tests-1588 passing」、Release 正文「1588 tests」的千分位写法不一致。 | 拼写 | 全文统一一种（本套文本建议 1588，徽章也是 1588） |
| [`:101`](../portfolio.md#L101)–`:102` | 「That analyses a bundled first-party sample in a few seconds」 | 数字本身**有实测支撑**：`docs/reports/m8-install-rehearsal.md:43` 记录 `dexatlas analyze examples/demo-app/demo.apk` 为 6.8 s。但那个样例只有 5 个类 / 8 个方法（同一行），而另一端是 200,000 个方法的 APK（`README.md:401`）。读者会推出「分析一个 APK 只要几秒」。 | 吹过头 | 补上样本规模：「…a bundled 5-class sample in a few seconds」 |
| [`:96`](../portfolio.md#L96)（对 `:102`–`:105`） | 「`uv sync --extra analysis`」紧接「The same workspace can then be opened in the web workbench (`uv run dexatlas-workbench`) or served to an AI assistant (`uv run dexatlas-mcp`)」 | **照着做会失败**：MCP SDK 只在 `mcp` extra 里（`pyproject.toml:60-65`），而 `src/dexatlas/mcp/server.py:23` 直接 `from mcp.server.mcpserver import MCPServer`。只装 `--extra analysis` 时 `uv run dexatlas-mcp` 会 ImportError。发版说明与 Release 正文用的都是完整 extras 列表（`docs/releases/v1.0.0.md:160`、`docs/reports/v1.0.0-github-release-body.md:212`）。 | 指路 | portfolio 快速开始改用 `uv sync --extra dev --extra analysis --extra mcp --extra demo`；或把 MCP/工作台那句移到「装完 MCP extra 之后」 |
| [`docs/portfolio.md:113`](../portfolio.md#L113)–`:114` | 「the benchmark methodology and its disclosures are in `docs/benchmarks/`」 | 「链接文字写的是 `docs/benchmarks/` 一个目录，落点却是 `benchmarks/comparison.md` 一个文件（M3 对比实验）。」读者以为会看到全部 benchmark 说明，结果只看到其中一份。 | 指路 | 文字改成「the M3 comparison（`benchmarks/comparison.md`）」，或直接链到目录里最相关的两份（`service-regression-set.md`、`m6-level2-real.md`） |
| [`docs/portfolio.md:108`](../portfolio.md#L108)–`:111` | 「Three complete worked analyses — a walkthrough …, an obfuscated-sample study, and an integration study … — are in `docs/case-studies/`」 | 「三份案例只给一个文件夹链接，我得自己去翻才知道哪份是哪份。」 | 指路 | 三个案例各给一条直链 |
| [`:101`](../portfolio.md#L101) | 「That **analyses** a bundled first-party sample…」 | 英式动词拼写，与全套文本的美式用法混用（README `:23`、`:70` 同为英式，而命令名是 `analyze`、章节名是 License）。 | 拼写 | 统一美式：analyses → analyzes、analysing → analyzing、analysed → analyzed |
| [`:86`](../portfolio.md#L86)–`:89` | 「It is a good fit when you need **traceable** analysis … It is not a malware classifier or a sandbox; it does not score risk or allege intent.」 | 「一个不会替我做判断、只给我可复查证据的工具——这是我要的。」 | 保留 | 不要在改稿时误伤 |

### 3.5 `docs/architecture/README.md`（架构说明）

| 位置 | 原文 | 英文读者会怎么读（读者口气） | 类别 | 建议改法 |
|---|---|---|---|---|
| [`:64`](../architecture/README.md#L64)–`:65` | 「The two stages the diagram puts between the backends and the report are **the ones that were not here before**.」 | 「before 是 before 什么？我才第一次看。」这句话的整个重点（stage → publish 两段式）恰恰要靠「以前没有」来解释。 | 门槛 | 改成正面陈述：「A run **stages** its results in a database of its own … and then **publishes** them … in a single transaction.」删掉「not here before」 |
| [`:160`](../architecture/README.md#L160)–`:162` | 「**It used to be** a label the caller chose: `EvidenceBuilder.add` wrote whatever level it was handed.」 | 「used to be 是什么状态？我只能从后半句猜出「现在不是了」。」 | 门槛 | 改成现在时：「A `verified` record is not a label the caller chooses: `EvidenceBuilder.add` checks it before writing it.」 |
| [`:311`](../architecture/README.md#L311)–`:313` | 「**This is not what the content-addressed id used to mean.** Re-analysing an APK no longer replaces its symbols in place…」 | 「used to mean 什么？新读者根本没有『旧含义』。」 | 门槛 | 改成现在时：「The content-addressed id identifies the **project** (the APK); the symbols belong to a **run**.」 |
| [`:405`](../architecture/README.md#L405) | 「`mcp/`, `agent/` and `workbench/` have landed.」 | 「have landed 是『上线了』的口语，和这篇文档其余部分的克制语气不一致。」 | 术语 | 改成「`mcp/`, `agent/` and `workbench/` are in the tree.」 |
| [`:405`](../architecture/README.md#L405)–`:415` | 「## Where to read next」下一串只有标题的链接 | 「README 的 Project records 每条都写清了『里面有什么、我为什么要点』，这里只有标题。」读者看不出该先读哪一篇。 | 指路 | 每条后补半句用途说明（尤其与 README `:455-477` 对齐） |
| [`:147`](../architecture/README.md#L147)–`:158` | 「## Evidence levels」——三级证据的完整定义在此 | 「README 里 `verified` / `lead` / `insufficient` 只有名字没有解释，而定义在这里。」README 没有链过来。 | 指路 | README `:27` 加链接到本节锚点 |

### 3.6 根因：四个术语的定义都在中文文档里，英文侧没有一条链接指过去

第 6–9 条不是四个独立问题，是同一个根因的四个切面。下表列出这些术语的定义实际落在哪里；**此表为交叉分析，不重复计入第 2 节的条目统计**。

| 英文文本里的词 | 英文出处 | 定义实际在哪 | 那份文档的语言 | 英文文本链过去了吗 |
|---|---|---|---|---|
| the agent service promise | README `:402-403`、`:416`、`:422`；Release 正文 `:125` | `docs/service-commitments.md`（服务承诺范围） | 中文 | **否——全仓库零引用**（对全仓 grep `service-commitments`，除该文件自身外无一处命中） |
| the frozen discipline | Release 正文 `:125` | `docs/benchmarks/service-regression-set.md:155`《5. 冻结纪律》 | 中文 | README `:402` 链到那份文件，但读者点进去是一整页中文 |
| B1 | Release 正文 `:304-305` | `docs/status.md:133`（「B1 验收线」） | 中文 | README `:458` 链到那份文件，并在链接处标注「Chinese; 当前状态」 |
| the seven red lines | Release 正文 `:62` | 判分语义在代码 `benchmarks/model.py::check`；中文表述见 `CHANGELOG.md:27`、`docs/benchmarks/m6-verify3-plan.md:3` | 代码 / 中文 | 否 |

一句话：**英文文本本身没有说错，掉的是「定义—指针」这一层。** 四个词的定义都真实存在，只是全部落在英文读者到不了（或到得了但读不懂）的地方。修法因此也是同一件事：给 `docs/service-commitments.md`、`docs/benchmarks/service-regression-set.md`、`docs/status.md` 这三份中文文档各出一份英文摘要（或在英文文本里就地把这四个词解释掉），并把 `docs/service-commitments.md` 从孤儿文档挂进 README。

---

## 4. 英文读者读完这五份文本后，会形成什么印象

**三句话：**

1. **对的印象：** 这是一个把「结论必须能回溯到字节」当真话执行的工具——后端失败被写成值而不是崩溃（README `:28`、架构 `:11-14`）、模型输出只能是线索而永远不是发现（README `:309`、portfolio `:35-36`）、每个数字都带出处（Release 正文 `:3-8`）、没验证的边界会自己说出来（发版说明 `:96-114`、Release 正文 `:146-150`）；**这批材料里最真实、也最值钱的就是这份诚实度**——它让读者愿意继续往下读英文版本。
2. **文本造成的错觉之一（最严重）：** 这个项目的「门槛被挪过」——同一个失败测量在 README 里对 ≥80%、在发版说明里对 ≥90%（两条线都真实，但各说各的），「49 live checks」与「no run executes all of them」同页并存，而 README 顶部说已发版、底部说退出标准全过才发版；一个谨慎的读者会把这些读成「规则是为了让数字好看而改的」，而真实情况只是**同一批事实在不同文档里各说了各自的一半**。
3. **文本造成的错觉之二：** 「英文只是门面」——README 前 64 行用 M3–M10 六个内部代号讲状态却不给图例；「the seven red lines」「the frozen discipline」「B1」「the agent service promise」四个词的定义**确实存在**，但全部落在中文文档里，其中 `docs/service-commitments.md` **全仓库无人引用**（详见 3.6）；读者最可能点开的四份状态/评审文档全是中文；再加上 `portfolio.md:96` 的快速开始照做会在 MCP 那一步直接 ImportError，读者容易得出「这个项目内部自己用了一套词，没打算让外人看懂」——而实际只是英文文本还没做到「读者第一次接触」这一层。

---

## 5. 必须改的 16 处（按「会让读者误判」排序）

> **只列清单，未改动任何文件。** 每条给出最小改法；括号内是类别。

### 第一梯队：读者会直接得出错误结论（5 条）

1. **`README.md:32` + `README.md:545`** —— 已发版 vs「退出标准全过才考虑发版」。读者会判定项目违反自己的门槛。改 `:545` 为现状陈述。（吹过头）
2. **`README.md:47` + `README.md:539` vs `docs/releases/v1.0.0.md:24`** —— 同一失败测量对两条不同的线（≥80% 单轮 / ≥90% 三轮）。读者会判定验收线被换过。三处统一成「低于 ≥80% 单轮线，且低于 ≥90% 三轮线」。（吹过头）
3. **`docs/releases/v1.0.0.md:64` + `docs/reports/v1.0.0-github-release-body.md:96` vs 同文件 `:312`** —— 「49 live checks」与「没有一次跑完 49 项」同页。正文补一句实跑口径。（吹过头）
4. **`README.md:32` vs `README.md:539/541/543`** —— 「Phase 3 is delivered」与三个未完成里程碑并存。（吹过头）
5. **`docs/reports/v1.0.0-github-release-body.md:146-150`** —— 「What this release does not include」在中文摘要里整段缺失。中文读者会以为含动态分析、macOS 已验证。（中英不等价）

### 第二梯队：读者读到的是内部黑话，无法查证（6 条）

6. **`docs/reports/v1.0.0-github-release-body.md:62`** —— 「the seven red lines」这个英文措辞全仓库只此一处；判分语义在代码 `benchmarks/model.py::check`，中文表述见 `CHANGELOG.md:27`。就地点明并给出出处。（门槛）
7. **`docs/reports/v1.0.0-github-release-body.md:304-305`** —— 「B1」在英文文本中唯一出现且未定义；定义在 `docs/status.md:133`（中文）。附录行内加一句括注即可。（门槛）
8. **`docs/reports/v1.0.0-github-release-body.md:125`** —— 「the frozen discipline」这个英文措辞全仓库只此一处；定义在 `docs/benchmarks/service-regression-set.md:155`《5. 冻结纪律》（中文，README `:402` 链到它）。改成白话并补链接。（门槛）
9. **`README.md:403`（另见 `:416`、`:422`）** —— 「the agent service promise」从未定义；定义在 `docs/service-commitments.md`（中文），而该文件**全仓库零引用**。就地解释 + 补链接 + 把那份孤儿文档挂进 README。（门槛）
10. **`README.md:33-64`（另见 `:37`、`:39`）** —— M3–M10 代号无图例，M3/M4 无处可查。（门槛）
11. **`README.md:458-461` 与 `:477-479`** —— 英文 README 指向状态、覆盖度、三份评审记录四个中文文档，读者读完英文门面就被挡住。（门槛）

### 第三梯队：读起来会夸大或不一致（5 条）

12. **`README.md:5`** —— 「Powered by AI Agents」复数，项目只有一个 agent。（吹过头）
13. **`README.md:19` / `docs/reports/v1.0.0-github-release-body.md:12` / `docs/portfolio.md:11`** —— 「complete, verifiable picture」与「which steps did not run」自相矛盾。（吹过头）
14. **`docs/releases/v1.0.0.md:49`** —— 英文发版说明里残留中文「（方案 3，现状披露）」。（拼写）
15. **`docs/portfolio.md:96`** —— 快速开始只装 `--extra analysis`，却让读者接着跑 `uv run dexatlas-mcp`（MCP SDK 不在安装里，照做必失败）。（指路）
16. **`docs/portfolio.md:66-69`** —— 「six CI jobs」后面只点得出五项；`:66` 千分位写法与徽章、正文不一致。（吹过头）

### 六类分布

| 类别 | 条数 | 编号 |
|---|---|---|
| 吹过头 | 6 | 1, 2, 3, 4, 12, 13 |
| 门槛 | 6 | 6, 7, 8, 9, 10, 11 |
| 中英不等价 | 1 | 5 |
| 指路 | 1 | 15 |
| 拼写 | 1 | 14 |
| 术语 | 1 | 16 |
| **合计** | **16** | |

---

## 6. 改稿时不要误伤的部分

这批文本里有几处是这轮核对后确认**成立且有分量**的写法，改稿时应原样保留：

- **`docs/reports/v1.0.0-github-release-body.md:3-8`** —— 「Every figure below is copied verbatim from a file in this repository; the file and line are listed in the appendix.」数字出处表的存在本身就是这轮最有说服力的一处。
- **`docs/releases/v1.0.0.md:115-131`**（Known limitations）与 **`:96-114`**（What this release does NOT include）—— 失败数字与边界写得很实，是英文读者最信的部分。
- **`README.md:106`**（「A conclusion you cannot click back to is not a finding.」）、**`:516-522`**（intended use：不授权第三方应用，明确点名不做签名伪造/授权绕过）、**`docs/portfolio.md:86-89`**（不是恶意软件分类器、不打分、不下意图判断）。
- **`docs/portfolio.md:101` 的「a few seconds」** —— 有实测支撑（`docs/reports/m8-install-rehearsal.md:43`：6.8 s），只需补样本规模，不必删。
- **`docs/architecture/README.md:5-25`**（The one rule everything follows）—— 全套材料里最好的开篇，独立于项目历史即可读懂。

---

## 7. 本轮没有做的事

- 没有核对数字本身是否与源码一致——那是前几轮的工作；本报告只在**同一事实被两篇文档用两种口径表述**、从而会让读者误判时提出。
- 没有改任何被核文本。
- 没有跑覆盖率、测量或发版脚本。
