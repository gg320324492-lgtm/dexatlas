# 英文读者视角终检（第二轮，只读复核）

**日期：** 2026-11-18
**范围：** 本轮合并的五份文档（仓库文档正文为中文，本轮按「一个只读得到英文文本与这几份
报告的英语读者」这一人设来核）
**性质：** 只读复核。**未修改任何被核文本**，除本文件外未改动仓库任何文件。

> **本报告的行号锚在哪棵树：** 全部锚在提交 **`2c456e0`**（= 本报告提交前的那棵树，
> `v1.0.0` tag `75976e0` 之后 13 个提交）上。**主会话已在本报告发出后开始按它修这五份
> 文档**，因此那些文档的行号会继续移动——**本报告里的 `file:line` 只在 `2c456e0` 上
> 成立**。这是本仓库自己的规矩：读一份报告之前先看它锚在哪棵树上。
> 处置进度见 §9.4。

| 被核文本 | 行数 | 角色 |
|---|---:|---|
| `docs/reports/release-process-dry-run.md` | 600 | 照发版清单实走一遍的演练报告 |
| `docs/reports/portfolio-readiness-2026-11-18.md` | 465 | 作品集准备度第二轮自评 |
| `docs/reports/v1.1.0-candidates.md` | 695 | 下一轮需求候选清单（C1–C12） |
| `docs/reports/v1.0.0-release-checklist.md` | 726 | 发版清单（已按演练发现修订过一轮） |
| `docs/reports/README.md` | 176 | 报告索引（本轮收录了三份新报告） |

---

## 1. 读者人设与方法

**读者人设：** 一个英语读者——评估这个开源项目的技术负责人，或在 Upwork 上读到它的人。
他不懂本项目历史，也不需要懂。他只读得到仓库里的**英文**文本（README、发版说明、
架构文档、代码注释）与**这几份中文报告的英文摘要与数字**。

**为什么这一轮不一样：** 上一轮同性质的走查（[english-reader-review.md](english-reader-review.md)）
核的是**五份对外英文文本**能不能被顺畅读下去。这一轮的对象换了：核的是**五份中文报告**，
读者画像也换了——他拿到的不是成品文案，而是**别人替他做完核查之后留下的结论与数字**。
所以判据不再是「读起来顺不顺」，而是「**他读完会不会相信一件不成立的事**」。

**只读边界（严格遵守）：**

- 未跑 `pytest --cov`、未跑任何 `coverage` 命令、未 `uv sync`、未跑
  `scripts/refresh-report-figures.py`、未联网、未 `git commit` / `checkout` / `stash`。
- 只跑了两个只读门禁：`scripts/check-doc-citations.py`（285 条引用，0 漂移）、
  `git rev-list` / `git diff` / 一次独立重算 `source_fingerprint()`。
- **未读 `.claude/worktrees/` 下的任何副本**——那不是本树的文档。
- 结论凡属推断均标「推断」并给出依据行号；凡属事实均给出出处行号。
- 本报告不含任何密钥或凭据样式字符串。

**关于「重测量正在跑」：** 主会话正在对这棵树跑一次完整重测量，落盘后测试数 / 覆盖率 /
源指纹会换新。本报告**不把这些数字当成错误**，只做两件事：(1) 指出**哪些数字是脚本生成
的**（重测量会统一替换，文档里不必逐处跟）；(2) 指出**哪些数字是手写的**——那才是重测量
救不了、必须人改的。见 §5.2。

---

## 2. 速览

| 类别 | 条数 |
|---|---:|
| **会让读者做出错误结论**（§3） | 19 |
| 术语：直接用了而没有一句解释（§4） | 16 |
| 数字与分母（§5） | 11 |
| 「这棵树」与「发布的那棵树」没分开（§6） | 8 |
| 自相矛盾（§8） | 10 |

**最要紧的三条：**

1. 准备度报告说「**CI 10 次并行运行全绿**」，演练报告说「**CI 有 2 个 job 是红的，且那个
   run 至今未结束**」。两份文档同一天合并，读者只能信一份，而被写进评分证据的是错的那份。
2. 「**73 项判定**」复算不出来：分项相加是 80，表里实有 75 行，判定相加是 73。三个数，
   一个都对不上。
3. 同一张 §7 表被记成两个数：**16**（不一致）与 **17**（陈旧前提）——第 17 行写的明明是
   「一致」。

---

## 3. 必须改的 18 处（按后果排序）

### 3.1 同一件事，两份报告给了相反的答案，而错的那个进了评分证据

**原文（逐字）**

[portfolio-readiness-2026-11-18.md:314](portfolio-readiness-2026-11-18.md#L314)：

> 作者记录下的 CI 10 次并行运行全绿（tag 推送时：9 个 job 定义，`test` 是 3.12/3.13 矩阵）——
> **该结果本轮未联网复核，仓库里也没有落盘记录**（见 §7 第 7 条、§8 第 17 条）。

[release-process-dry-run.md:26](release-process-dry-run.md#L26)：

> | **本次演练中发现的最高等级事实** | **已发布的 `v1.0.0` tag 指向的提交，CI 有 2 个 job 是红的，且那个 run 至今未结束**（§4.1） |

演练报告 §4.1 给了细节：run `44126968629` 至今 `in_progress`，`Tests (Python 3.13)` 与
`Tests (Apktool only, no JADX)` 两个 job `failure`，`measurement` job 17 小时后仍在跑。

**英文读者会怎么误读**

准备度报告 §8 第 8 条是「有一个可引用的发布版本了」这条**新增硬证据**的正文，它同时
支撑着「核心工程与证据链 4/4」和「对外展示 3/3」两个维度的满分。读者会得出：
**「v1.0.0 这个已发布的版本，CI 全绿，发布质量是被自动化验过的。」**
而同一轮合并的演练报告说恰恰相反。读者手上没有 GitHub 凭据，也没有第二份报告，
他只能相信「全绿」那句——**因为带「全绿」两个字的那句没有标「未复核」以外的任何限定，
而标了「未联网复核」的恰恰是它的证据强度说明，不是它的结论**。

**建议改法**

把 portfolio:314 整条换成：

> The v1.0.0 tag's CI run is **not** green. Two jobs failed
> (`Tests (Python 3.13)` and `Tests (Apktool only, no JADX)`) and the run had
> not finished when it was last checked; see
> [release-process-dry-run.md](release-process-dry-run.md) §4.1. This review did
> not re-check it against GitHub. The release therefore cannot be described as
> "CI-verified"; the repository contains the mechanism (`ci.yml`) but not the
> result.

并把 §1 表格里「核心工程与证据链」的得分理由中「CI 新增 tag 触发与只在 tag 上跑的测量 job」
与「契约活检进 CI」这两条**保留**，但把由「全绿」推出来的任何表述去掉；§7 第 7 条与
§8 第 17 条的措辞也要一并改（现在它们把「全绿」当成既成事实在讨论「没有落盘记录」）。

**处置状态（2026-11-18，主会话）：已修。** 主会话在报告发出后于
`portfolio-readiness-2026-11-18.md` 开头加了一段「更正」：把「CI 10 次并行运行全绿」
改成「**那句是错的**」，并写明 tag `v1.0.0` 的那次 run（`44126968629`）**以 `failure`
结束、4 个 job 红**（`Tests (Python 3.12)`、`Tests (Python 3.13)`、
`Tests (Apktool only, no JADX)`、`The report's figures describe the tagged tree`），
根因是同一条契约判据，并声明**分数不变**（4/4 的依据是 `ci.yml` 里的机制，不是那次
运行的结果）。同时 `release-process-dry-run.md` 的 §0 与 §4.1 也改成了
「CI 是红的」。

**比本报告更准的两点，值得记下来：** 演练报告写的是「2 个 job 已红、run 还没跑完」，
主会话拿到的是**跑完之后的最终结论**——4 个 job 红、run 结束为 `failure`。
本报告采信的是演练报告当时的状态，**以主会话这一版为准**。
这也说明一件事：**「CI 状态」这类数字必须带一个「截至何时」**，
否则读者读到的是一份永远在变的快照。

---

### 3.2 「73 项判定」复算不出来

**原文（逐字）** [release-process-dry-run.md:20](release-process-dry-run.md#L20)：

> | 走过的清单条目 | **73 项判定**（§1 前置 8 / §2 契约 8 / §3 步骤 1–7 与 §7 八条 43 / §5 阻断与披露 9 / §8.1 六道 6 / §8.2 六类 6；另 §8.4 的 11 条候选按「落地状态」列，不做对错判定） |

**英文读者会怎么误读**

读者会去核这个 73：把分项相加 → 8+8+43+9+6+6 = **80**，与 73 对不上。再数报告里的表格
行：§2 前置 8 行、§3.1 契约 8 行、§3.2–§3.7 共 4+9+6+2+6+11 = **38** 行、§3.8 六道 6 行、
§3.9 六类 6 行、§3.10 阻断与披露 9 行，合计 **75 行**——也不是 73，也不是 80。
最后落到 §0 的四个判定数：49 一致 + 16 不一致 + 6 无法验证 + 2 缺失 = 73 ✓。
**三个数、三个都对不上**。一个英语读者到此只能得出一个结论：这些数字是凑的，
后面 16 / 2 / 17 那一串也都不可信。

**建议改法**

给出可复算的写法，例如：

> | Judgements made | **75** (§2 prerequisites 8 / §3.1 contract surface 8 / §3.2–§3.7 steps 1–7 and the eight §7 traps 38 / §5 blockers and disclosures 9 / §8.1 six gates 6 / §8.2 six change classes 6). §8.4's 11 candidates are listed with their status only and are not judged. |
> | of which "consistent" | 46 rows carry an explicit 一致 verdict; 2 rows carry a conditional 一致（有脚注 / 一致但…）; the remaining rows are described in the table text rather than by a verdict cell |

或者干脆把「73」改成**能加出来的那个数**，并把四个判定数改成表里能逐行点出来的口径。
**分项与总数必须能互相对上**，这是本仓库「数字可复算」这条规矩对**报告本身**的要求。

**一条跟着来的提醒：** 逐表重数之后还会剩一个尾巴——`release-process-dry-run.md:80`
那一行的判定格写的是「**不一致 + 无法验证**」。**它同时属于两个桶。**
如果四个判定数要加成一个总数（而不是两个总数），这一行需要一条明确规则
（要么只算一次、要么那一行只判一格、要么总数写成「判定格数」，并注明
「有 1 行同时带两个判定」）。否则读者把 4 个数加起来会得到 75，而表里只有 74 行
被分到桶里。

**处置状态（2026-11-18，主会话）**：主会话已按逐表重数把这一格改成
**75 项判定 / 50 一致 / 17 不一致 / 6 无法验证 / 2 不完整**，并加了一段「复核更正」
说明原数字来自手工汇总。上面那条「双判定格」的尾巴**在那一版里仍然存在**
（17 与 6 都把 :80 算了进去），建议一并定规则。

---

### 3.3 同一张 §7 表被记成 16 与 17 两个数

**原文（逐字）** [release-process-dry-run.md:22](release-process-dry-run.md#L22) 与
[:25](release-process-dry-run.md#L25)：

> | 「不一致」 | **16 项**（其中 6 项会直接把作者引到错误结论） |
> | 清单里的陈旧数字/前提 | **17 处**（见 §7） |

§7 的表只有 17 行，第 17 行写的是：

> | 17 | §1.1 / §1.2 引用的全部 14 份证据文件、9 个逐例附件 | 全部存在 ✅ | 一致 | |

也就是说 **16 行是不一致，第 17 行是「一致」**——它不是一条陈旧前提。
「17 处陈旧数字/前提」把一个**核对通过**的条目也算进了「陈旧」。

同一个 17 又出现在另外两处：
[checklist:493-494](v1.0.0-release-checklist.md#L493)（「§7 指出的那 **17 处**陈旧前提之一」）、
[README.md:104](README.md#L104)（「73 项判定里 16 项与仓库现状不符、2 项缺失，**17 处**前提过期」）。
而 [checklist:7](v1.0.0-release-checklist.md#L7) 写的又是「修正 **16 处**与仓库现状不符的前提」。

**英文读者会怎么误读**

读者拿不到 §7 的原表（至少拿不到「哪一行是一致」这个信息），只能看到 16 与 17 在同一篇
里指同一张表。他会认为报告自己没算清，或者更糟——认为其中一个数是夸大的。

**建议改法**

§0 的两行改成：

> | "Inconsistent with the repository" | **16** (§7 rows 1–16) |
> | of which would lead the author to the wrong conclusion | 6 (§5.2) |
> | Stale figures or premises in the checklist | **16** — the same 16 rows of the §7 table. The table's 17th row is a check that *passed*; it is not a stale premise. |

同步改 `v1.0.0-release-checklist.md:493-494` 与 `README.md:104` 的「17 处」。

---

### 3.4 源指纹有三个值，读者无从知道哪个是「现在这棵树」

**原文（逐字）** [release-process-dry-run.md:130](release-process-dry-run.md#L130)：

> 直接调用脚本自己的 `source_fingerprint()` 重算当前克隆树的指纹 → `sha256:975afa8e…`，
> 与 `docs/reports/phase1-execution-report.md:1097` 记录的值**逐字一致** ✅

以及 [:196](release-process-dry-run.md#L196)：

> | **B4** | 执行报告的 `source_fingerprint` 与当前代码树不一致 | **一致** —— 重算指纹 = `sha256:975afa8e…` = 记录值 ✅ |

**实测（本轮独立重算，只读）**

| 指纹 | 出处 | 是哪棵树 |
|---|---|---|
| `sha256:975afa8e…` | `75976e0`（= `v1.0.0` tag）上的 `phase1-execution-report.md:1097` | 发布的那棵树 |
| `sha256:1bcf620d…` | **今天** `docs/reports/phase1-execution-report.md:1097` 的值 | 提交 `44902a6` 重测量时那棵树 |
| `sha256:a92ace15…` | **提交 `4fd86af`（本 worktree 的 HEAD）** 的真实指纹 | 提交态 |
| `sha256:80bf8b0a…` | **本轮核稿期间的工作区**（含同树其他会话尚未提交的 `src/`、`tests/` 改动） | 工作区，**随时会变** |

本轮用 `git show <rev>:<path>` 对 `4fd86af` 与 `75976e0` 各重算了一遍（174 个文件，
与 `source_fingerprint()` 的算法逐字一致）：`4fd86af` = `a92ace15…`、
`75976e0` = `975afa8e…`。**这独立确认了演练报告对发布树的那句「逐字一致 ✅」是对的**——
问题只在于它没有说「这是**那一棵树**的」。

`727` → `a92ace15` 的原因是 `72caa25` 改了 `tests/test_m10_selfcheck.py` 与
`tests/test_public_contracts.py`——两者都在指纹覆盖范围内（`src/**/*.py` + `tests/**/*.py`
+ `pyproject.toml` + 测量脚本本身）。

**第四个值值得单独说一句：** 本轮核稿期间，这棵 worktree 上有别的会话在改
`src/dexatlas/cli/main.py`、`src/dexatlas/reports/evidence_package.py`、
`tests/test_evidence_package.py` 等**未提交**的改动——它们在指纹覆盖范围内，于是工作区的
指纹从 `a92ace15…` 变成了 `80bf8b0a…`。**指纹不是「这棵 checkout 的属性」，是「这一刻
这批文件内容的属性」。**

**英文读者会怎么误读**

演练报告说「指纹逐字一致 ✅」，读者据此认为「报告里的数字描述的就是现在这棵树」；
而准备度报告 §0 引用同一批数字（1,620 / 93.3% / 7,117-7,631）时也只给了行号，没说
这批数字属于哪棵树。读者会把 2026-11-17 那次测量的结果当成当前状态。
**更硬的一条**：[v1.0.0-release-checklist.md:303](v1.0.0-release-checklist.md#L303) 写
B4「**已关闭（2026-11-18 复核）**：在最终发布 commit 上完整重测量后指纹一致，
`tests/test_docs.py` 全绿」——而守这条的测试
`tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code`
断言 `record["source_fingerprint"] == script.source_fingerprint()`，**在今天这棵树上是红的**
（`1bcf620d…` ≠ `a92ace15…`）。

**建议改法**

演练报告与清单里的指纹断言一律加上树限定，并把「一致」的措辞改成对哪棵树一致：

> The fingerprint recorded in `docs/reports/phase1-execution-report.md:1097` matched
> the clone's fingerprint **on the tag tree `75976e0`** (`sha256:975afa8e…`). The
> working copy has since moved on: its own fingerprint is now
> `sha256:a92ace15…`, so the recorded measurement no longer describes the working
> copy. A re-measurement is required before those figures may be quoted as
> current.

清单 §5 B4 的「已关闭」改成「**在发布树 `75976e0` 上已关闭**；本树（`4fd86af`）已因
`72caa25` 改动 `tests/` 而重新变红，待重测量」。

---

### 3.5 「`git rev-list --count v1.0.0..HEAD` = 0」今天不成立

**原文（逐字）** [v1.1.0-candidates.md:3-4](v1.1.0-candidates.md#L3)：

> 日期：2026年11月18日 · 调研基准：本 worktree 的 `75976e0`
> （= tag `v1.0.0` 指向的提交，`git rev-parse v1.0.0^{commit}`；`git rev-list --count v1.0.0..HEAD` = 0）。

**实测** 今天 `git rev-list --count v1.0.0..HEAD` = **13**。

**英文读者会怎么误读**

「= 0」是全文最容易被当成现况的一句：它说的是「我核的就是发布的那棵树，一行没动」。
读者会以为**候选清单里的每一条现状复核都发生在发布的那棵树上**，因而「读这份清单 = 读
发布版」。而实际上这 13 个提交里有 `scripts/m10_selfcheck.py` 与三份 `tests/` 的改动，
清单里若干条现状复核因此**已经不成立**（见 §3.7）。

**建议改法**

> …`git rev-list --count v1.0.0..HEAD` was **0 when this document was written**
> (2026-11-18). The working copy has since gained 13 commits; the re-checks in
> §3 were made against the tree as of `75976e0`. Anything that depends on
> `scripts/` or `tests/` must be re-checked before it is acted on.

---

### 3.6 演练报告说清单里「一个字都没有」的那条路径，今天已经补上了

**原文（逐字）** [release-process-dry-run.md:391](release-process-dry-run.md#L391) 与
[:396](release-process-dry-run.md#L396)：

> **没有。** 全清单 631 行里：
> …
> - 「发布后如何修正并重打 tag」这条路径，在发版清单里**一个字都没有**。

同文 [:8](release-process-dry-run.md#L8)：

> - **对象**：`docs/reports/v1.0.0-release-checklist.md`（631 行）

**实测** 今天该清单是 **726 行**，§3 里多出「### 步骤 8：发布后修正并重打 tag（发布之后才发现错时的路径）」
（[checklist:196](v1.0.0-release-checklist.md#L196)），正是这条路径。

**英文读者会怎么误读**

英文读者手上若只有演练报告（它自称是「清单哪里对不上现实」的权威读法），会得出
**「发版清单没有『发布后修正并重打 tag』这条路径」**——而清单里现在写着这条路径的完整
七步与四条判据。索引 [README.md:104](README.md#L104) 有一句「清单已按它的发现修过一轮」
可以救，但那句话在索引的一行表格单元格里，读者多半不会读到。

**建议改法**

演练报告开头加一行状态声明，并把 §8.2 的结论改成有语境的写法：

> **Status of this report:** every finding below was acted on — the checklist now
> has 726 lines and §3 step 8 ("publish, then correct and re-tag") exists. The
> findings are kept as written because they describe the checklist **as of
> `75976e0`**; re-read them as history, not as the checklist's current state.

### 3.7 「M10 自查 40/40」少了 3 条判据，现在是 43

**原文（逐字）**

[portfolio-readiness-2026-11-18.md:137](portfolio-readiness-2026-11-18.md#L137)：

> …M10 自查 40 通过 / 0 失败

[portfolio-readiness-2026-11-18.md:281](portfolio-readiness-2026-11-18.md#L281)：

> 检出 tag、九步路径、七道门禁退出码全 0、契约 48/48、M10 自查 40/40；

[v1.1.0-candidates.md:165](v1.1.0-candidates.md#L165)：

> - `scripts/m10_selfcheck.py` 仍 40/40 通过，且新增的跨文件口径检查**在旧材料上会失败**

**实测** [m10-selfcheck.md:25](m10-selfcheck.md#L25) 写「## 2. 83 项分类结果（自动化 43 + 留人工 40）」，
[:88](m10-selfcheck.md#L88) 写「**通过 43，失败 0，需人工 40**」。提交 `72caa25`
（"M10 自查：加三条判据"）把自动化判定从 40 提到 43。

**英文读者会怎么误读**

两个「40」指的是**两个不同的分母**：验收包一共 40 项（其中大部分留人工），自动化判定是
43 条。读者会把「自查 40/40 通过」读成「**验收包那 40 项全部通过**」——那是一个比实际
情况强得多的断言（那 40 项按定义就还没人执行，全是「留人工」）。而
v1.1.0 候选清单把「仍 40/40 通过」写成 C1 的**做完判据**，读者照着去核对会得到一个
对不上的数。

**建议改法**

三处统一改成：

> the M10 self-check reports **43 automated checks passed, 0 failed, 40 items left
> for a human reader** — the 40 and the 43 are different denominators (see
> [m10-selfcheck.md](m10-selfcheck.md) §2)

**同一处还有一处更细的引用错**：[release-process-dry-run.md:173](release-process-dry-run.md#L173)
写「快照 `docs/reports/m10-selfcheck.md:85` 记的是「通过 40，失败 0，需人工 40」」——
`:85` 现在是**空行**，摘要在 `:88`；而它引的那句「通过 40」是 `44902a6` 之前的值，
现在的快照写的是「通过 **43**，失败 0，需人工 40」。两处都要改。

### 3.8 索引页自己的份数有三个，§3 / §5 的分组份数没跟上

**原文（逐字）**

[README.md:3](README.md#L3)：

> 这个目录里是 DexAtlas 从 Phase 1 到 v1.0.0 发版收尾之间的四十五份报告
> （**这是 2026-11-17 的快照**）。

[README.md:25](README.md#L25)、[:27](README.md#L27)、[:29](README.md#L29)（原文逐字）：

> | §3 里程碑与对外准备度 | 2 | 这个项目作为对外作品集是什么成色 |
> | §5 v1.0.0 发版材料 | 5 | 发版要发什么、凭什么、怎么发 |
> | 合计 | 41 | |

**实测（本轮逐节数行）**

| | 页里写的份数 | 表里实有几行 | 目录里实际有几个文件 |
|---|---:|---:|---:|
| §1 | 7 | 7 | |
| §2 | 5 | 5 | |
| §3 | **2** | **4** | |
| §4 | 9 | 9 | |
| §5 | **5** | **6** | |
| §6 | 17 | 17 | |
| 合计 | **41**（而分项相加是 45，与首页的「四十五份」又不同） | **48** | **51**（`docs/reports/*.md` 减本页自己） |

**英文读者会怎么误读**

索引页第一句就告诉读者「这一层有 45 份报告」，表格说 41，而数文件是 51。
**读者无法判断哪一份报告是最新的现状。** 而索引页自己的使命恰恰是回答这个。
另外「**这是 2026-11-17 的快照**」与本轮**新增了三行**（§3 加了 2 行、§5 加了 1 行）
自相矛盾：快照不会自己长出新的行。

**建议改法**

- 首页改成「**51 份**报告（截至 2026-11-18；`ls docs/reports/*.md | wc -l` 减本页），
  **份数是快照，每落进一份就变一次**」。
- §3 的 2 改 4、§5 的 5 改 6、合计 41 改 48。
- 或者更省事：**把首页那个总数删掉**，只保留「份数是快照，不是常数」+ 数文件的命令。
  本轮新增的三份报告是**这个数字第一次被本轮自己打破**的场合。

### 3.9 三份被反复引用的文件没有进索引

**实测** 把 `docs/reports/` 下 52 个 `.md` 与索引里点名过的文件逐一比对，**未被索引点名**
的有三份（除索引自己）：

| 文件 | 谁在引它 |
|---|---|
| `reader-dry-run.md` | 准备度报告 :43、:320；演练报告 §1.1 前提 |
| `next-engagements.md` | v1.1.0 候选清单 :7、:31、:73、:590、:596 |
| `social-preview-howto.md` | 演练报告 §6 S8（：「本次**它就是闯祸的那个**」） |

**英文读者会怎么误读**

索引是这一层的入口。读者从索引走到 v1.1.0 候选清单，再顺着它找到它的源头
《下一轮可接什么活》——点不动，因为索引里没有这一份。他要么认为链接断了，要么认为
这份候选清单是凭空冒出来的。演练报告把 `social-preview-howto.md` 点名为「闯祸的那个」
文件，一个认真复核的读者会去读它——索引里也没有。

**建议改法**

索引 §6（或新开一小节）补三行，并在首页把份数一并改对。

### 3.10 引用类缺陷：六处指到空行，一处漂移——出处查不到

**(a) 指到空行的六处（准备度报告，分布在六行）**

**原文（逐字）** [portfolio-readiness-2026-11-18.md:25](portfolio-readiness-2026-11-18.md#L25)：

> 见 [m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:83、:86。

**实测** `docs/benchmarks/m6-level2-retest4.md` 里：`:38` 是 `| DexAtlas | 49/60 | 81.7% |`，
`:83` 是「三轮合计判定：DexAtlas 49/60 = 81.7%，未达 ≥54/60（≥90%）」，
而 **`:86` 与 `:88` 都是空行**。该文件自提交 `2c727f8` 起**没有再改过**——这些引用从写下
那天起就指错了。真正想指的是 `:82`（逐轮判定 r1 15/20 = 75.0%…）与 `:85`
（**总结论：未达标。**）。

六处的确切位置（逐行核过）：

| 行 | 引的 | 该行是什么 |
|---:|---|---|
| [:25](portfolio-readiness-2026-11-18.md#L25) | `:38、:83、:86` | `:86` 空行 |
| [:172](portfolio-readiness-2026-11-18.md#L172) | `:38、:83、:86` | `:86` 空行 |
| [:174](portfolio-readiness-2026-11-18.md#L174) | 「同文件 :88」 | `:88` 空行 |
| [:367](portfolio-readiness-2026-11-18.md#L367) | `:38、:83、:88` | `:88` 空行 |
| [:368](portfolio-readiness-2026-11-18.md#L368) | 「同文件 :88」 | `:88` 空行 |
| [:381](portfolio-readiness-2026-11-18.md#L381) | `:38、:83、:86` | `:86` 空行 |

**英文读者会怎么误读**

这些是「M6 层级 2 未达验收线」这条**全报告最硬的负面事实**的出处。读者点 `:86` 得到
一个空行——他不会认为「行号错了」，他会认为「这条结论没有落盘的支持」，或者更糟，
认为**这一段是编的**。一个以「证据优先」为卖点的项目，在自己的负面结论上指不到证据，
代价是双倍的。

**(b) 漂移的一处**

**原文（逐字）** [portfolio-readiness-2026-11-18.md:215-216](portfolio-readiness-2026-11-18.md#L215)：

> 两轮读者视角走查共 37 条（第一轮 29 条 + 第二轮新发现 8 条，见
> [索引](README.md):126-127、[m10-reader-walkthrough-2nd.md](m10-reader-walkthrough-2nd.md)），

同一处引用在 [:297](portfolio-readiness-2026-11-18.md#L297) 重复一次。

**实测** 写这份报告时（提交 `5d5e8a6`）`README.md:126-127` 确实正是那两行走查的表格行；
本轮索引新增三行后它们移到了 **:129-130**。今天点 `README.md:126-127` 落到的是
`release-notes-consistency.md` 与 `changelog-vs-release-notes.md` 两行。

**英文读者会怎么误读**

读者顺着这个引用去看「29 条 + 8 条」在哪，点开的是两份别的报告——他要么以为这 37 条
的出处被删了，要么以为编号记错了。

**建议改法**

- (a) 六处一律改成 `[m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md):38、:82、:83、:85`。
- (b) 两处改成 `[索引](README.md):129-130`，并按仓库规矩跑一遍
  `uv run --no-sync python scripts/remap-citations.py` 再
  `uv run --no-sync python scripts/check-doc-citations.py`。
- **并且**：这两类错（指到空行、漂移到别的行）**引用检查器查不出来**——
  `check-doc-citations.py` 对「只指位置、不指符号」的 119 条引用只验「行还在不在」。
  §7.1 建议加一条新的检查规则：**被引用的行不得为空白**。这条规则能一次性抓住 (a) 的
  四处。

### 3.11 清单 §8 的修订只做了一半

清单开头 [checklist:8-9](v1.0.0-release-checklist.md#L8) 承诺：

> 并把 §8 的「CI 不跑」改成「CI 现状（2026-11-18）」逐道标注。

**实测**：§8.1 / §8.2 的**子标题**改了（§8.1 已是「六道需要单独盯的门禁（CI 现状：2026-11-18）」），
但 §8 的**大标题**没改，且两栏「为什么」还是旧的：

| 位置 | 原文（逐字） | 事实 |
|---|---|---|
| [checklist:476](v1.0.0-release-checklist.md#L476) | `## 8. 自动化覆盖与盲区 —— CI 不跑的那些门禁` | 6 道门禁里 L1/L2/L3/L4 现在都有 CI job |
| [checklist:697](v1.0.0-release-checklist.md#L697) | C1 … \| **已落地** \| 重打 tag 现在不产生任何 run，tag 指向错了永远没人知道 | C1 已落地 = tag 触发**已经加上了** |
| [checklist:698](v1.0.0-release-checklist.md#L698) | C2 … \| **部分落地** \| 推发版分支现在完全没有 CI 兜底 | `release/**` 已进 `on.push.branches`，发版分支**有** CI |
| [checklist:687](v1.0.0-release-checklist.md#L687) | 复核报告给了 11 条建议。**本节只列清单，不代改**；`.github/workflows/` 这次**没有动**。 | 同一节下方的状态列写着 C1/C5/C6/C7 **已落地**（都是 `ci.yml`） |

**英文读者会怎么误读**

读者从索引点到清单，先看到大标题「CI 不跑的那些门禁」，再看到 C1 的理由「重打 tag
现在不产生任何 run」——**这是演练报告 §7 第 1 行点名的同一条陈旧前提，修在了 §8 的
背景段，却留在了 §8.4 的表格里**。读者据此以为「重打 tag 不会产生 run、没人会发现
tag 指向错了」——恰恰是这一版发版最后变红的原因。

**建议改法**

- 大标题改成 `## 8. 自动化覆盖与盲区 —— 哪些门禁 CI 跑、哪些跑不了`。
- C1/C2 的「为什么」列加前缀「**当初的理由（已过时）**：」，理由句后面接一句现状。
- §8.4 正文那句「`.github/workflows/` 这次**没有动**」改成「本节初稿时没有动；
  2026-11-18 复核后 C1/C5/C6/C7 已落地」。

### 3.12 v1.1.0 候选清单把「收录进索引」列为待办，但索引已经收录了它

**原文（逐字）** [v1.1.0-candidates.md:597](v1.1.0-candidates.md#L597)：

> | **把本报告收录进 `docs/reports/README.md` 索引** | 本轮硬约束：除新增本文件外不得修改任何文件 | 下一个文档改动窗口；索引自己声明「**份数是快照，不是常数**」，所以它晚一步不构成事实错误，但确实留了一处待办 |

**实测** 索引 [README.md:76](README.md#L76) 已经有这一行：

> | [v1.1.0-candidates.md](v1.1.0-candidates.md) | 下一轮（v1.1.0）的**需求候选清单**：12 项候选… |

**英文读者会怎么误读**

读者以为这份候选清单**没有被收进项目**，是一份游离线的东西；或者反过来，以为自己漏看了
一份文档。这条待办是同一轮合并里被同一轮合并掉的。

**建议改法**

把这行从 §4「现在还不能做的」删掉，或改成：

> — **Done:** this report is listed in `docs/reports/README.md` §3.

### 3.13 索引页内部对「§6 有几份报告」说了两个数

**原文（逐字）** [README.md:115](README.md#L115) 与 [README.md:162](README.md#L162)、[:164](README.md#L164)：

> 这十七份报告全部是**只读审计**产出：

> - **凡带基线声明的报告，数字只在该基线上成立。** §6 的十三份审计报告各自锚在自己的基线上，
> - **「只读审计」不等于「结论已落地」。** §6 的十三份报告只记录发现，改动由主线执行；

而 [:28](README.md#L28) 的分组表写「§6 … | 17 |」。

**英文读者会怎么误读**

「十七份」与「十三份」指同一组报告。读者不知道 §6 到底是 13 份还是 17 份，也就不知道
该按哪一组去核对「基线声明」的规则。

**建议改法**

把 §7 那两处的「十三份」改成「十七份」，或者在 §7 说明「§6 的前 13 份是逐份审计，
后 4 份（`ci-gate-coverage.md`、`readme-map-audit.md`、`m10-reader-walkthrough-3rd.md`、
`github-repo-metadata-proposal.md`）是同批的复核与提案」。

---

### 3.14 tag 被重打了 5 次还是 2 次？两份新报告给了两个数

**原文（逐字）**

[release-process-dry-run.md:11](release-process-dry-run.md#L11)：

> - **基线**：GitHub 上 `v1.0.0` 的**实际发布状态**（已发布、tag 被重打过 5 次、CI 有红）

同文 [:381](release-process-dry-run.md#L381)：

> `v1.0.0` 在 GitHub Release 发布（2026-11-17T14:45:39Z）之后，**tag 被重新推送了 5 次**

[portfolio-readiness-2026-11-18.md:413](portfolio-readiness-2026-11-18.md#L413)：

> | 9 | [ci-gate-coverage.md](ci-gate-coverage.md):139-140、:414、:446 | 「`v1.0.0^{commit}` = `8f9ddca`」「tag 不可变，本轮没有动它」 | 现在是 `75976e0`；tag 已被重打两次，按当前指向改 |

**英文读者会怎么误读**

「重打了 5 次」是演练报告列为**最高等级事实**的那一节的支点（§4.1、§8.1：每一次重打
都作废上一次的 CI 结论）；「重打了两次」是准备度报告 §8 的第 9 条。读者会挑一个信，
而挑哪个会改变他对「v1.0.0 这条发版流程到底有多不可靠」的判断。

**实测** 演练报告 §4.3 的表列了 6 个 tag 状态
（`09b6078` → `a575eea` → `0104ccb` → `774d4fb` → `410aebb` → `75976e0`，
结论依次 success/success/success/failure/cancelled/in_progress），也就是 6 个状态 ⇒
**5 次重打**。这 6 个 commit 在本仓库里都存在。**演练报告的 5 是对的**，
准备度报告的 2 应该是它写的时候只数到了前两次。

**建议改法**

准备度报告 §8 第 9 条改成：

> tag 已被重打**五次**（6 个 tag 状态：success → success → success → failure →
> cancelled → in_progress），最后一次指向 `75976e0`；见
> [release-process-dry-run.md](release-process-dry-run.md) §4.3。

### 3.15 「上一轮」的分数有两个互不相认的版本

**原文（逐字）**

[portfolio-readiness-2026-11-18.md:6-7](portfolio-readiness-2026-11-18.md#L6)：

> 「上一轮得分」取 [2026-11-15 复评](portfolio-readiness-2026-11-15-recheck.md) §6.5 的最终值
> （GitHub 81.25% / Upwork 76.9%）

[v1.0.0-release-checklist.md:42-43](v1.0.0-release-checklist.md#L42)：

> - [ ] 按原权重重评 GitHub / Upwork，**各 ≥90%**。最新作者自评为 GitHub **85.0%**、
>   Upwork **81.9%**（[第二轮复评](portfolio-readiness-2026-11-18.md)；上一轮为
>   77.5% / 68.75%，见[首轮复评](portfolio-readiness-2026-11-15-recheck.md)），均未达标。

**英文读者会怎么误读**

两个文档都指向同一份 `portfolio-readiness-2026-11-15-recheck.md`，却对「它的最终值是多少」
给出两个答案（81.25 / 76.9 与 77.5 / 68.75）。读者点进去核对会发现：
**77.5 / 68.75 是那份复评 §2 的旧口径，81.25 / 76.9 才是它 §6.5 的最终值**——
而准备度报告 §3（[:78-82](portfolio-readiness-2026-11-18.md#L78)）恰恰是指出这件事的人。
清单在这里踩了自己人。

**建议改法**

清单那一句改成：

> 上一轮为 **81.25% / 76.9%**（见[首轮复评](portfolio-readiness-2026-11-15-recheck.md) §6.5；
> 该报告 §2 的 77.5% / 68.75% 是它的旧口径），均未达标。

### 3.16 「其中 6 项会直接把作者引到错误结论」在报告里没有名单

**原文（逐字）** [release-process-dry-run.md:22](release-process-dry-run.md#L22)：

> | 「不一致」 | **16 项**（其中 6 项会直接把作者引到错误结论） |

**实测** 报告里最接近这份名单的是 §12 A「会让人照做出错动作的（优先）」——那张表只有
**A1–A5 五行**（[:521-527](release-process-dry-run.md#L521)）。此外 §7 表里有 4 行带
「照做会…」的措辞（:363、:365、:368、:369），§2/§3 表里还有若干「照清单做会向读者报一个
偏大的差距」式的措辞。**「6」这个数在任何地方都没有被列出来。**

**英文读者会怎么误读**

读者会去找那 6 条——因为「会直接把作者引到错误结论」是全文最该被逐条读的东西。
找不到，他会认为这 6 条是「报告心里有数但没写」，于是**跳过 10 条不重要的**——
而其中哪 6 条要命，只有作者知道。

**建议改法**

要么在 §0 这一行后面直接列出是哪 6 行（例如 `§7 rows 7, 9, 12, 13 + §3.6 的正文文件
+ §3.10 B3`），要么把「6」改成 §12 那张表的真实行数并在句子里点明：

> | "Inconsistent with the repository" | **16** (§7 rows 1–16) |
> | of which would make the author act wrongly | **5** — listed as A1–A5 in §12 A; the other 11 are stale premises, not wrong actions |

### 3.17 演练报告说检查器查 11 份文档，实际 12 份；清单里两行「没有人」已经过时

**原文（逐字）** [release-process-dry-run.md:162](release-process-dry-run.md#L162)：

> | **N5** 改动后统一重锚 `file:line` | `check-doc-citations.py` drifted 0 ✅；但它现在**只查 11 份文档**（含 `docs/releases/*.md` 与 `*-github-release-body.md`） | 一致 |

同一说法还在 [:370](release-process-dry-run.md#L370) 与 [:541](release-process-dry-run.md#L541)。

**实测** `scripts/check-doc-citations.py` 的 `DOCS` 列表解析出 **12** 份
（4 份固定 + `docs/releases/*.md` 的 7 份 + `docs/reports/*-github-release-body.md` 的 1 份）；
检查器本轮自己的输出也是 `the v1.0.0 tree: 1 document(s)` + `the working copy: 11 document(s)`
= 12。清单已经改对了（[checklist:416](v1.0.0-release-checklist.md#L416) 写「那 **12** 份文档」）。

**另一处更值得注意：** 演练报告 §7 第 4 行说

> | 4 | §8.2 B2「Release 附录里的 `文件:行` → **没有人**」 | `check-doc-citations.py` 现在查它（按 `v1.0.0` 那棵树解析） | 让人以为还要手工重锚 |

而清单 [checklist:611](v1.0.0-release-checklist.md#L611) **今天仍然写着**：

> | B2 | Release 附录里的 `文件:行` | `docs/reports/v1.0.0-github-release-body.md` | **没有人**（靠 L5 的手工重锚） |

`docs/reports/v1.0.0-github-release-body.md` **确实在检查器的 `DOCS` 里**，所以 B2 已经有
人管。同理 [checklist:613](v1.0.0-release-checklist.md#L613) 的 B5 仍写「没有人」，
而 §7 第 6 行说它已有 CI job（虽然确实没人拿它跟那份手写快照比对——**那半句是对的**）。

**英文读者会怎么误读**

清单说「Release 附录里的 `文件:行` 没有人核对」——一个准备发版的读者据此判断附录会漂，
于是**手工重锚一遍**（多余的劳动），或者干脆不锚。而这恰恰是演练报告点名要收口的盲区。

**建议改法**

- 演练报告三处「11 份」改成「**12** 份」。
- 清单 §8.2 的 B2 改成「**有**（`check-doc-citations.py` 的 `DOCS` 含
  `*-github-release-body.md`，按该文档声明的 `v1.0.0` 那棵树解析；2026-11-18 复核）」。
- 清单 §8.2 的 B5 改成「**部分有**（`m10-selfcheck` job 跑脚本，但没人拿它跟那份手写
  快照比对；靠 L3 的重跑重写）」。

### 3.18 候选清单的 7 + 4 ≠ 12

**原文（逐字）** [v1.1.0-candidates.md:25-29](v1.1.0-candidates.md#L25)：

> | 下一轮有多少候选？ | **12 项**（C1–C12），按「对能不能接活、能不能被信任」排 |
> | 现在就能做的有几项？ | **7 项**（C1、C3–C8）全部在仓库内、不需要外部读者；C2 的作者侧准备可做，验收本身需要外部读者 |
> | 现在还不能做的？ | **4 项**（M10 的执行部分、README 首读复核、平台表单复核、M6 再开一轮），各有触发条件 |

**实测** 候选确为 12 项（`#### C1` 到 `#### C12`，[:120](v1.1.0-candidates.md#L120) 至
[:554](v1.1.0-candidates.md#L554)）。但 7 + 4 = **11**：

- **C9**（对外联系方式、时区、可用性）与 **C10**（外发隔离）**两边都没有**——它们在
  §2 排序表里被标为 P2 /「要写真值」，但没有进任何两个汇总桶。
- **C7 与 C8 两边都有**：C7、C8 在「7 项现在就能做」里，也在 §4「现在还不能做」的表里
  （[:594-595](v1.1.0-candidates.md#L594)：C8 的执行要等 M10 验收完成、C7 的执行要另开
  一个测量窗口）。§4 那张表**实有 8 行**（6 行是候选范围，2 行不是：Upwork 服务页发布、
  收录进索引）。

**英文读者会怎么误读**

读者会以为漏了一项，或者以为「12 − 7 − 4 = 1」那一项是 C9/C10 里的某一个——
**他没有办法判断到底是哪一项没归类**。这是「按能不能接活排优先级」这份清单最要紧的
一张摘要表。

**建议改法**

§0 的两行改成能对上的口径，例如：

> | How many can be started now? | **7** (C1, C3–C8) — all inside this repository, no external reader needed. C2's *preparation* can be started; its *acceptance* cannot. |
> | Which are blocked? | **5** — C2's execution, C9, C10, C11, C12's execution. Each has a stated trigger condition in §4. (C7's and C8's *execution* are also blocked; see §4.) |

并把 §4 那张表的标题改成「**现在还不能做的：8 项（含 2 项非候选动作）**」，让 8 这个
数在原地可数。

### 3.19 四处引用指向 `ci.yml` 里不存在的行，另有四处悬空

**(a) 引用范围越过文件末尾（四处）**

**原文（逐字）** [portfolio-readiness-2026-11-18.md:42](portfolio-readiness-2026-11-18.md#L42)：

> 已到等级上限；证据变厚但未跨档：CI 新增 tag 触发与只在 tag 上跑的测量 job（[ci.yml](../../.github/workflows/ci.yml):18、:493-537），契约活检进 CI（`:442`）…

同一处 `:493-537` 还出现在 [:95](portfolio-readiness-2026-11-18.md#L95)、
[:258](portfolio-readiness-2026-11-18.md#L258)（带链接形式与裸引用形式各一次）、
[:264](portfolio-readiness-2026-11-18.md#L264)。

**实测** `.github/workflows/ci.yml` **一共 525 行**（发布树 `75976e0` 与当前树都是 525 行）。
`measurement` 这个 job 从 `:493` 开始，**到文件末尾 `:525` 结束**——所以 `:493-537`
这个范围**末尾 12 行根本不存在**。起点 `:493` 是对的（`  measurement:`），
`:18`（`    tags: ['v*']`）、`:442`（`  contracts:`）、`:471`（`  m10-selfcheck:`）
也都对。**只有范围的尾巴越界。**

**英文读者会怎么误读**

读者点 `:537`——**文件没有这一行**。浏览器显示的是文件末尾或一个 404。一个正在评估
「这个项目的 CI 门禁够不够硬」的读者，会把「引用越界」读成「**这个 CI job 还在写、
还没写完**」或者「引用的行号是编的」。而这条引用撑着的正是 §4.1「本轮新增的硬证据有
四条」里的第 1 条。

**(b) 四处悬空的裸引用**

**原文（逐字）** [portfolio-readiness-2026-11-18.md:264-265](portfolio-readiness-2026-11-18.md#L264)：

> 证据：契约活检（`:442`）、M10 自查（`:471`）、测量比对（`:493-537`）三个 job；
> tag 推送也产生 run（`:18`）。

这两行里的 `:442`、`:471`、`:493-537`、`:18` 是**裸行号**——它们所属的文件
`ci.yml` 是在**上一段**（`:258`）命名的，而 `:262` 是一行空行。按本仓库自己的约定
（「裸 `:143` 指本块之前命名的那个文件」），这四处**在自己的块里无解**。
语义上它们显然指的是 `ci.yml`，而且确实指对了，但形式上读者无从判断。

**建议改法**

- (a) 四处 `:493-537` 一律改成 `:493-525`（或 `:493-` 到 EOF）。
- (b) 四处裸行号各自带上文件名：`:ci.yml:442` → `ci.yml:442`。
- 两者都改完后跑 `uv run --no-sync python scripts/remap-citations.py` 再
  `uv run --no-sync python scripts/check-doc-citations.py`。
- **并把 §7.1 说的那条新规则加上**：被引用的行不得为空白、范围不得越过文件末尾。
  这两条规则能一次性抓住本节的 (a)(b) 与 §3.10 的 (a)——**而现有的检查器一条都抓不到**，
  因为这五份文档**没有一份在它的 `DOCS` 列表里**（§7.1）。

---

## 4. 术语：直接用了而没有一句解释的黑话（16 条）

下面这些词在五份文档里被当作已知概念使用。**它们在仓库里大多是有定义的**——问题不是
「没定义过」，而是**这几份文档用的时候没有指过去**，英语读者手上没有那把尺子。

| # | 术语 | 出现在 | 仓库里有定义的地方 | 建议 |
|---|---|---|---|---|
| 1 | **源指纹 / source fingerprint** | dry-run:130、196、253；portfolio:29 | `docs/reports/phase1-execution-report.md:985` 有一句解释 | 首次出现处加一句英文：`the source fingerprint — a hash of src/, tests/, pyproject.toml and the measurement script; it answers "is this the same code?", not "is this still green?"` |
| 2 | **契约活检** | dry-run:185、195；portfolio:45、99 | `docs/how-to-verify.md:240`（§2.6「门禁三：公共契约活检」） | 首次出现处补 `contract live-check — a script that actually exercises the public contract surface and exits non-zero if a check fails` |
| 3 | **留人工** | portfolio:237；m10-selfcheck.md:62 | `docs/reports/m10-selfcheck.md:62` | 改为 `left for a human reader (「留人工」)` |
| 4 | **红→绿 / 绿** | dry-run:26、117、409；checklist:8 | 无统一说法 | 首次出现处说明：`a run is "green" when every CI job concludes success` |
| 5 | **独占测量** | dry-run:128；checklist N1 | `docs/reports/coverage-guard-audit.md`、`docs/status.md` | `exclusive measurement — one measurement process at a time per checkout` |
| 6 | **两棵树** | dry-run:250-259、:130；ci-gate-coverage.md:225 | `docs/reports/ci-gate-coverage.md` §4.11、§7 | `the release tree (the immutable tag) and the working copy` |
| 7 | **三后端齐备** | portfolio:45、111；dry-run:51 | `docs/architecture/public-contracts.md:371` | `all three backends present (Apktool, JADX, androguard)` —— **第一次出现就要写全名** |
| 8 | **fast / slow 套件** | dry-run:582-583；portfolio:27 | `scripts/refresh-report-figures.py` 的 `tests.fast` / `tests.slow` 标记 | `the fast suite (everything not marked slow) and the slow suite (the integration tests marked slow)` |
| 9 | **证据包 / 三件套** | v1.1.0-candidates C4；portfolio:45 | `docs/architecture/public-contracts.md` | 首次出现处给一句：`an evidence package — the report, its JSON form, and the manifest of files it cites` |
| 10 | **工程日刻度** | v1.1.0-candidates:53-57 | `docs/roadmap/phase3-plan.md:72` | `engineering-day ruler — the Phase 3 schedule's unit of effort` |
| 11 | **只读演练 / 只读复核** | 五份都有 | 无 | `read-only dry run — nothing was written outside this report` |
| 12 | **判定 / 走过的清单条目** | dry-run:20 | 无 | `judgement — one checklist row marked consistent / inconsistent / unverifiable` |
| 13 | **重打 tag** | dry-run:381；checklist:196 | `docs/reports/m10-invitation-sender-checklist.md:123-127` | `re-tagging — force-moving an existing annotated tag onto a new commit` |
| 14 | **弱模块表** | README:123；dry-run 未用 | `docs/reports/coverage-guard-audit.md` | `the low-coverage module table` |
| 15 | **门禁 / 六道门禁** | dry-run §3.8；checklist §8.1 | `docs/reports/ci-gate-coverage.md` | `gate — a check whose exit code decides pass or fail` |
| 16 | **M10 准备包 / 独立验收** | portfolio:4；v1.1.0-candidates:99 | `docs/reports/m10-acceptance-pack.md` | 首次出现处补一句：`the M10 acceptance pack — 40 checks handed to a reader who did not write the code` |

**一条通用建议**：这五份文档里最值得加的不是逐条术语表，而是**每份开头一个五行
"Glossary" 小节**，只收本份用到的词。这比全仓统一术语表便宜得多，也正是英语读者唯一
会回头找的东西。

---

## 5. 数字与分母

### 5.1 逐个核

| 数字 | 出现在 | 分母是什么 | 复核结论 |
|---|---|---|---|
| **73 项判定** | dry-run:20；README:104 | 声称是走过的清单条目数 | **复算不出来**：分项相加 80，表内实有 75 行，四判定相加 73。§3.2 |
| **49 一致 / 16 不一致 / 6 无法验证 / 2 缺失** | dry-run:21-24 | 73 项判定 | 四个相加 = 73 ✓，但与表内逐行的判定格对不上：**每一个「问题桶」都少算 1**（表内判为「不一致」的格子实有 16 或 17 个，取决于 dry-run:80 那个「不一致 + 无法验证」的双判定格算几遍；判为「无法验证」的实有 7 个；「不完整」（:163）与「缺失」（:149）各 1 个）。§3.2 |
| **6 项会直接把作者引到错误结论** | dry-run:22 | 声称是 16 项里的一个子集 | **报告里没有名单**——最接近的 §12 A 表只有 A1–A5 五行。§3.16 |
| **16 项不一致** | dry-run:22；README:104；checklist:7 | §7 表的第 1–16 行 | ✓ 可核（第 17 行是「一致」） |
| **17 处陈旧前提** | dry-run:25；checklist:493；README:104 | 声称是 §7 表 | **多算了 1 行**（第 17 行是核对通过的）。§3.3 |
| **6 项会直接把作者引到错误结论** | dry-run:22 | 声称是 16 项里的一个子集 | 报告 §5.2 确实列了六条，但**没写它是从 16 项里挑哪 6 项挑出来的**——读者无法核对 |
| **2 项缺失** | dry-run:24；README:104 | 声称是清单里根本没有的步骤 | ✓ 可核：§3.6 的「Release 正文与仓库正文没有比对检查」+ §8 的「重打 tag 路径」 |
| **85.0% / 81.9%** | portfolio:49、62、70-71 | 六个维度加权，权重和 = 100，分值满分 4 | **算式对得上**：GitHub `4×30+3.5×20+3.5×10+3.5×10+3×25+1×5 = 340`，`340/400 = 85.0%` ✓；Upwork `327.5/400 = 81.875%` → 报 81.9% ✓（**四舍五入，读者用 81.9 反推得 327.6 对不上 327.5**，建议脚注一句 `81.875%`） |
| **+3.75 / +5.0 个百分点** | portfolio:74 | 相对上一轮（81.25% / 76.9%） | ✓ `81.25+3.75 = 85.0`、`76.9+5.0 = 81.9` ✓。但上一轮的 81.25 / 76.9 **在本仓库里查不到出处**——portfolio:78-82 反而指出上一轮的算式按其自述口径算不平 |
| **12 项候选 / 7 项现在就能做 / 4 项现在还不能做** | v1.1.0-candidates:25-29 | C1–C12 | 候选确为 12 项（C1–C12 各有一节）；**7+4 = 11 ≠ 12** —— **C9、C10 两边都没有**，C7、C8 **两边都有**，§4 那张表实有 8 行。§3.18 |
| **1,620 / 1,473 / 147 / 93.3% / 7,117-7,631** | portfolio:27-29；dry-run:155、363 | 一次完整测量的套件与覆盖率 | **由脚本生成**（`<!--fig:tests.total-->` 等标记，见 `phase1-execution-report.md:76-77`）→ 重测量会统一替换，**不算错** |
| **sha256:975afa8e…** | dry-run:130、196、587 | 发布树 `75976e0` 的源指纹 | 事实正确，但**不适用于今天这棵树**。§3.4 |
| **49 / 60 = 81.7%** | portfolio:24、44 | M6 层级 2 三轮各 20 题 | ✓ 出处 `docs/benchmarks/m6-level2-retest4.md`:38、:83、:86 |
| **11 个 MCP 只读工具** | dry-run:364 | `server.py` 注册的工具数 | ✓（dry-run 的结论：清单 §2 写 10、§8.1 L4 写 11，**清单内部打架**） |
| **9 个 job / 10 次并行运行** | dry-run:120、366；portfolio:408 | `.github/workflows/ci.yml` 的 job 数 + 矩阵展开 | ✓ 可核（portfolio 列了 9 个 job 的行号） |
| **5 次重打 tag** | dry-run:381 | GitHub 上 `headBranch == v1.0.0` 的 run 数 | 事实来源在 GitHub，**仓库里没有落盘记录**——dry-run §4.3 的表就是唯一落点。**且准备度报告:413 写的是「两次」**，两份新报告打架。§3.14 |
| **11 份文档（被引用检查器覆盖的）** | dry-run:162、:370、:541 | `check-doc-citations.py` 的 `DOCS` | 实际是 **12** 份（检查器自己的输出：1 + 11 = 12）。清单已改对，演练报告三处未改。§3.17 |
| **上一轮 81.25% / 76.9%** | portfolio:6-7 | 相对 `portfolio-readiness-2026-11-15-recheck.md` §6.5 | ✓ 该复评 §6.5 的算式确实是 `325 → 81.25%` / `307.5 → 76.9%`。**但清单:42-43 把同一份文档的「上一轮」写成 77.5% / 68.75%**。§3.15 |
| **39 通过 / 失败 1 / 需人工 40** | dry-run:173、:579 | `m10_selfcheck.py` 在**一个没装 dev extras 的干净克隆**里的实跑 | 与仓库落盘的快照（`通过 43，失败 0，需人工 40`）**不是一回事**——失败项是 `G.vulture`。**这不是错**（两个不同环境），但报告没写清「这是本窗口的环境结果，不是仓库快照」，读者会以为仓库里跑出来是红的 |
| **40 / 43** | portfolio:137、281；candidates:165 | 两个不同的分母 | 混用了。§3.7 |

### 5.2 哪些数字是脚本生成的，哪些是手写的

这一节直接回应「重测量会换新数字」这件事。

**脚本生成（重测量落盘后统一替换，文档不必逐处跟，但**引用它们的句子**要跟着改**）：**

- 套件数与覆盖率：`docs/reports/phase1-execution-report.md:76-77` 的
  `<!--fig:tests.total-->` / `tests.fast` / `tests.slow` / `coverage.pct` /
  `coverage.covered` / `coverage.total`；`docs/status.md:22-24` 同源。
- 源指纹：`phase1-execution-report.md:1097` 的 `"source_fingerprint"`。
- README 徽章：`tests-1620 passing` / `coverage-93.3%`。

**手写（重测量救不了，必须人改）：**

| # | 位置 | 手写的什么 | 为什么重测量救不了 |
|---|---|---|---|
| 1 | `README.md:15` | 「完整环境下**的一次测量（1612 个测试、0 跳过）**」 | 正文里的散文数字，徽章是脚本写的、正文是手写的，两者已经不一致 |
| 2 | `README.md:21` | social preview 的 alt 文本「…**1612** tests」 | 同上 |
| 3 | `docs/status.md:26` | 「CI \| **6 个** workflow job 全绿…故实际并行运行数为 **7**」 | job 数与结论都是手写的；且「全绿」本身已被证伪（§3.1） |
| 4 | `portfolio-readiness-2026-11-18.md:27-29` | 「1,620 项测试…93.3%（7,117/7,631 行）」 | 报告里**抄**了生成数字的值。重测量后这里的值会变，而这份报告的其它结论（评分）建立在旧值上 |
| 5 | `release-process-dry-run.md:155、363、582-583、587` | 「1620 = 1473 快 + 147 集成」「`1473/1620 tests collected`」「`sha256:975afa8e…`」 | 同上：手抄的生成值 |
| 6 | `v1.0.0-release-checklist.md:303` | B4「**已关闭（2026-11-18 复核）**」 | 手写的状态判定。重测量不会把「已关闭」这四个字改回去 |
| 7 | `docs/reports/README.md:3、25、27、29` | 索引的份数 | 纯手写 |
| 8 | `release-process-dry-run.md:20-25`、`README.md:104` | 73 / 49 / 16 / 2 / 17 | 纯手写 |
| 9 | `portfolio-readiness-2026-11-18.md:49、62、70-74` | 85.0% / 81.9% / +3.75 / +5.0 | 纯手写，且**分母（6 个维度、权重和 100、满分 4）只写在正文里**，读者得自己重建 |

**一条建议：** 第 4、5 两类（报告里抄生成值）在下一轮重测量后必然失配。与其让每份报告
各自追一次，不如在报告开头写一句**「本报告引用的数字锚在 X 树的一次测量上；树变了，
这些数字就只描述那棵树」**——这既是 §6 的限定语，也是这一节要的东西。

---

## 6. 「这棵树」与「发布的那棵树」——需要一句限定语的地方（8 处）

这五份文档大量引用 commit / 指纹 / 基线。读者最容易犯的错，是把**某一棵树上的事实**
当成**现状**。逐处标出：

| # | 位置 | 现在的写法 | 缺什么 |
|---|---|---|---|
| 1 | portfolio:3 | 「评估基准：`75976e0`（= `git rev-parse v1.0.0^{commit}`，与 `origin/main` 同指）」 | `origin/main` 今天**仍然**是 `75976e0` ✓，但本 worktree 的 HEAD 已是 `4fd86af`（领先 13 个提交）。**只写「与 `origin/main` 同指」会让读者以为它等于当前 checkout。** 建议加：`The working copy has since moved 13 commits ahead of this baseline.` |
| 2 | portfolio:7 | 「分值是作者按同一评分表对**当前树**的保守判断」 | 「当前树」是相对哪棵树？读者会读成今天这棵。加 `the tree at 75976e0`。 |
| 3 | portfolio:314-317 | 「这一轮评的是「一个发布出去的版本」」 | 这句话本身是对的（评的是 `75976e0`），但紧邻的「CI 全绿」已经被演练报告证伪（§3.1）。两句放在一起，读者会把「评的是发布版」理解成「发布版没问题」。 |
| 4 | portfolio:316 | 「上一轮评的是「一个工作分支上的树」；这一轮评的是「一个发布出去的版本」」 | 「一个发布出去的版本」= tag `75976e0` 这一棵树，**不是**「任何读者现在拿到的代码」。建议：`the released tag, not the current working copy`。 |
| 5 | v1.1.0-candidates:4 | 「`git rev-list --count v1.0.0..HEAD` = 0」 | §3.5。 |
| 6 | dry-run:8-10 | 「**演练树**：`E:\Dexatlas\.scratch\release-dry-run\dexatlas`（从 GitHub 克隆的干净副本，`main` @ `75976e0`）」 | 这一处**做对了**——它明说演练发生在克隆上。但 §3.4–§3.10 的结论行（"一致"）说的是「仓库现状」，读者会把克隆的结论套到本树。 |
| 7 | dry-run:391 | 「全清单 **631 行**里……」 | §3.6。清单今天 726 行。 |
| 8 | v1.0.0-release-checklist:3 | 「编写日期：2026-11-15；编写基准：`53358c5`（worktree 分支 `claude/angry-mcclintock-1f9b4e`…）」 | 清单在 2026-11-18 按演练发现改过一轮（:6-9），**改的却是 `75976e0` 那棵树的事实**，而**声明的基准仍然是 `53358c5`**（该提交确实存在、确实是 HEAD 的祖先）。读者按声明的基准去核，会拿到一份 2026-11-15 的清单。建议加一行：**「本文 2026-11-18 的修订是按 `75976e0` 那棵树做的」**。 |

**通用建议：** 这五份文档的**每一节**的表头都可以加一列
「**结论属于哪棵树**」：`发布树 75976e0` / `本 worktree 4fd86af` / `未声明`。
这一列本身就把上面 8 处的误读堵掉大半，而且**是读者唯一能自己核的东西**。

---

## 7. 相对链接与 `file:line` 引用

### 7.1 本轮自己跑的门禁

```
$ .venv/Scripts/python.exe scripts/check-doc-citations.py
citations: 285
  naming a symbol: 166
  pointing only at a location: 119
trees:
  the v1.0.0 tree: 1 document(s), 63 citation(s)
  the working copy: 11 document(s), 222 citation(s)
unresolved paths: 0
drifted: 0
Every citation still says what it says.
```

**0 断链、0 漂移**。但注意 `119` 条是「只指位置、不指符号」——**这一类只验「行还在不在」，
验不了「那行写的是不是它声称的东西」**（`ci-gate-coverage.md` §4.11 已记录这条盲区）。
§3.10 的 `README.md:126-127` 就落在这一类里，门禁查不出来。

**更要紧的一条：这个门禁根本没有覆盖本轮被核的五份文档。**
`scripts/check-doc-citations.py:87-95` 的 `DOCS` 列表解析出来是 12 份：

```
docs/analysis-provenance.md
docs/architecture/public-contracts.md
docs/reports/phase1-execution-report.md
docs/benchmarks/large-apk.md
docs/releases/*.md              （7 份）
docs/reports/*-github-release-body.md（1 份）
```

`release-process-dry-run.md`、`portfolio-readiness-2026-11-18.md`、
`v1.1.0-candidates.md`、`v1.0.0-release-checklist.md`、`docs/reports/README.md`
——**一份都不在里面**。这就是为什么 §3.10 的六处空行引用、§3.19 的四处越界引用
在 CI 里全是绿的：**没进名单的文档，它的引用谁也不必保持为真**。
清单 §8.4 的 C4 说「扩 `DOCS` 列表」已落地（现共 12 份），但扩的是**发版**那几份，
不是这五份。

**建议给这个门禁加三条规则**（每一条都能抓一处本轮查出的真错）：

1. **被引用的行不得为空白** → 抓 §3.10(a) 的六处。
2. **引用范围不得越过文件末尾** → 抓 §3.19(a) 的四处 `:493-537`。
3. **裸 `:NN` 必须在同一块内能解析到所属文件** → 抓 §3.19(b) 的四处。

再加一条覆盖面：**把这五份文档加进 `DOCS`**（它们各有 100+ 条 `file:line` 出处，
是最需要被守着的一批）。

### 7.2 「两棵树」在检查器里的样子

`the v1.0.0 tree: 1 document(s), 63 citation(s)` —— 仓库里有一份文档**明确声明**它写的是
`v1.0.0` 那棵树（`docs/reports/v1.0.0-github-release-body.md`），它的 63 条出处按 tag
解析；其余 11 份按**当前树**解析。**这个机制是这批文档里最值得英语读者知道的一件事**，
而这五份新报告里**只有 portfolio:29 间接提到**「按文档声明的树解析」。

**建议：** 在五份新报告的开头各加一行：

> Citations in this document are resolved against the **working copy**, not against
> the `v1.0.0` tag. See `scripts/check-doc-citations.py` §"trees".

### 7.3 相对链接

五份文档的 **381 条渲染链接**（另 3 条在 ` ```markdown ` 代码块里，不是链接）与
**8 条锚点链接**本轮逐条解析过：**0 条断链、0 条锚点失配**。
`v1.1.0-candidates.md` 里另有 **114 条带 `#L<行号>` 的链接**，逐条打开核对过：
全部指向存在的文件、范围内的非空行，且那一行的内容与句子的说法对得上。
因此本节的发现**不是断链**，而是**链接文字与落点内容对不上**，与上一轮同。

| # | 位置 | 链接文字 | 落点 | 问题 |
|---|---|---|---|---|
| 1 | portfolio:215-216、:297 | 「见 [索引](README.md):126-127」 | `README.md` 的**两行走查表格** | 行号漂移到 :129-130。§3.10 |
| 2 | portfolio:421 | 「放进 [docs/reports/](README.md) 并进索引」 | `docs/reports/README.md` | 这是一个**目录**链接指到索引页。文字说的是「放进这个目录并进索引」，落点是索引页本身，读者点进去得不到目录列表。建议改成两个链接。 |
| 3 | dry-run:349 | 「`docs/reports/social-preview-howto.md` 这类」 | 纯文本，不是链接 | 这份文件**没进索引**（§3.9），且它正是「闯祸的那个」文件——读者拿不到。 |
| 4 | candidates:73 | 「[next-engagements.md](next-engagements.md)」 | 存在 ✓ | 但**没进索引**（§3.9） |

### 7.4 指向「本仓库里没有的东西」的引用

| # | 位置 | 引用 | 读者点进去会发现 |
|---|---|---|---|
| 1 | dry-run:50 | 「`pytest -q` → 1619 passed / 1 failed」 | 仓库里没有这次运行的记录（`E:\Dexatlas\.scratch\release-dry-run\` 不在仓库内，`.scratch` 被忽略）。读者**无法复核这个最要命的数字**。建议把克隆的 commit 与 run 命令写进报告，并说明「结果未落盘」。 |
| 2 | dry-run:138 | 「查远端 tag 对象：…tagger date = 2026-11-18 00:32:33 +0800」 | 同上，只能靠联网复核（而报告自己说本轮未联网）。 |
| 3 | portfolio:314-315 | 「CI 10 次并行运行全绿…**该结果本轮未联网复核，仓库里也没有落盘记录**」 | 报告**自己承认**了。这正是 §3.1 要处理的地方。 |

**三处查过之后判定「不是缺陷」的，列出来免得读者再查一遍：**

| # | 位置 | 引用 | 判定 |
|---|---|---|---|
| 4 | dry-run:104 | `pyproject.toml:145-146` | **是引用清单自己的错**，演练报告在正文里明说了「清单给的范围 145-146 恰好不含真正写着 `path` 的那一行」。清单已改成 `:146-147` ✓。`:145` 确实是空行，但这处引用是**被批判的对象**，不是错误。 |
| 5 | dry-run:100、checklist:79 | `evidence_package.py:37` | `PACKAGE_SCHEMA_VERSION = 1` 在发布树、HEAD 与本轮核稿时的工作区都在 `:37` ✓。但核稿期间同树另一个会话正在改这个文件，**那一行的位置在编辑过程中短暂地移到了 `:38`**——这说明**检查器读的是工作区**，一个正在被编辑的工作区会报出并不存在的漂移。这条不是缺陷，是**机制的一个提醒**。 |
| 6 | candidates 全文 | 114 条 `#L<行号>` 链接 | 逐条打开核对过：全部落在范围内的非空行上，且那行的内容与句子的说法一致 ✓。 |

---

## 8. 自相矛盾清单（10 处）

| # | 甲方 | 乙方 | 性质 |
|---|---|---|---|
| 1 | portfolio:314「CI 10 次并行运行**全绿**」 | dry-run:26「CI 有 **2 个 job 是红的**，且那个 run 至今未结束」 | **直接打架**，见 §3.1 |
| 2 | dry-run:20「**73** 项判定」 | 同行的分项 8+8+43+9+6+6 = **80**；表内实有 **75** 行 | 内部打架，§3.2 |
| 3 | dry-run:22「**16** 项不一致」 vs :25「**17** 处陈旧」 | §7 表第 17 行写「一致」 | 内部打架，§3.3 |
| 4 | README:28「§6 … **17**」 | README:162、:164「§6 的**十三份**」 | 内部打架，§3.13 |
| 5 | checklist:303「B4 **已关闭**…`tests/test_docs.py` 全绿」 | 守这条的测试在今天这棵树上是红的（`1bcf620d…` ≠ `a92ace15…`） | 与仓库现状打架，§3.4 |
| 6 | checklist:687「`.github/workflows/` 这次**没有动**」 | 同节 :697-703 的状态列写着 C1/C5/C6/C7 **已落地**（都在 `ci.yml`） | 同一节内部打架，§3.11 |
| 7 | dry-run:11、:381「tag 被重打**5** 次」 | portfolio:413「tag 已被重打**两次**」 | **两份新报告打架**，§3.14 |
| 8 | portfolio:6-7「上一轮 = **81.25% / 76.9%**」 | checklist:42-43「上一轮为 **77.5% / 68.75%**」（指向同一份复评报告） | **两份新报告打架**，§3.15 |
| 9 | dry-run:162、:370、:541「检查器查 **11** 份文档」 | `check-doc-citations.py` 的 `DOCS` 实为 **12** 份（检查器自己的输出：1 + 11） | 与仓库现状打架，§3.17 |
| 10 | dry-run:362（§7 第 4 行）「B2 现在有人查了」 | checklist:611 仍写「**没有人**」 | 与清单打架，§3.17 |

**两处不是矛盾、但看起来像矛盾的（值得写明，省得读者以为有错）：**

- portfolio:228-230 说「README 徽章写 1620，README 正文与 social preview 的说明文字仍写
  1612（见 §8 第 1–3 条）」。本轮实测 `README.md:15` 与 `README.md:21` **确实还是 1612**，
  这条**至今成立**——它不是过期项，只是还没改。
- dry-run:173 的「实跑：通过 39、失败 1、需人工 40」与仓库快照「通过 43、失败 0、需人工 40」
  **不是同一个东西**——前者是**本窗口那个没装 dev extras 的干净克隆**里的实跑
  （失败项是 `G.vulture`），后者是仓库里落盘的快照。两个数都对，但报告没写清这个区别，
  读者会以为仓库里跑出来是红的。

---

## 9. 本轮做了什么、没做什么、哪些结论依赖读者自己实跑

### 9.1 做了什么

- 通读了五份文档（2,662 行）与上一轮的 [english-reader-review.md](english-reader-review.md)（220 行），
  按它的体例写成本报告。
- **只读**跑了 `scripts/check-doc-citations.py`（285 条引用、0 漂移）。
- 逐行数了演练报告 §2–§3 的 11 张判定表（75 行）与 §7 的 17 行表，复算「73 / 16 / 2 / 17」。
- 逐节数了索引页六组的表格行（48 行）与目录里的实际文件（51 份）。
- 独立重算了源指纹（按 `source_fingerprint()` 的算法，174 个文件），得到提交态
  `4fd86af` = `sha256:a92ace15…`、tag 态 `75976e0` = `sha256:975afa8e…`，
  与仓库里记录的 `sha256:1bcf620d…` 三者分开；工作区因同树其他会话的未提交改动，
  指纹在核稿期间已变成第四个值 `sha256:80bf8b0a…`。
- 用 `git rev-list` / `git diff` 核了「工作树领先 tag 13 个提交」与「哪几个提交动了指纹
  覆盖范围内的文件」。
- 核了 `tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code`
  的断言逻辑（**读代码，没有跑测试**），据此判断该测试在今天这棵树上为红。
- 核了 `85.0%` / `81.9%` 的加权算式、两个平台的权重和（= 100）与满分（= 400），
  以及上一轮 81.25% / 76.9% 在 `portfolio-readiness-2026-11-15-recheck.md` §6.5 的出处。
- 核了 `scripts/check-doc-citations.py` 的 `DOCS` 列表**实际解析出 12 份文档**，
  并与检查器自己的输出（1 + 11）对上。
- 核了 `src/dexatlas/mcp/server.py` 的 `@server.tool` 装饰器个数 = **11**。
- 核了 `.github/workflows/ci.yml` 的 **9 个 job** 与 `test` 的 3.12/3.13 矩阵展开。
- 核了演练报告 §4.3 表里的 6 个 tag 状态 commit 在本仓库**都存在**。
- 核了 `docs/benchmarks/m6-level2-retest4.md` 自 `2c727f8` 起**未再改动**，因而
  portfolio 那三处 `:86` / `:88` 的引用从写下那天起就指着空行。
- 核了 `m10-selfcheck.md` 的 `:84-90`，确认 `:85` 是空行、摘要在 `:88`。
- 核了候选清单 `#### C1`–`#### C12` 共 12 个小节，以及 C9 / C10 未进任何汇总桶。
- **跑了第二遍引用审计**（逐条解析五份文档里 376 个 `file:line` / `#L<行号>` / 裸
  `:NN` 引用，**每条都对着发布树 `75976e0` 与当前树各核一次**）。查出本报告
  §3.10(a) 与 §3.19 的问题，并**修正了本报告自己的一处数**：§3.10(a) 原本写「三处」，
  实际是**六处**（分布在 :25、:172、:174、:367、:368、:381 六行）。
- **未读 `.claude/worktrees/` 下的任何副本。**

### 9.2 没做什么

- **没有联网**：`gh run list` / `gh release view` / `git ls-remote` 全部没跑。因此
  「CI 有 2 个 job 是红的」「tag 被重打 5 次」「Release 正文 18,560 字节」这些事实，
  本报告**采信演练报告的记录**，没有独立复核。
- **没有跑 `pytest`**（哪怕单条）。§3.4 中「守指纹的那条测试今天是红的」是**读断言得出
  的推断**，不是实跑结果。
- **没有跑 `refresh-report-figures.py`**，没有重测量，没有改任何既有文件。
- **没有逐条复核演练报告 §3.6 步骤 6 提到的那 87 条 Release 附录出处**（演练报告说
  27 条待人工确认后都是假阳性；本轮没有重做这个近似比对）。
- **没有核对 GitHub 上已发布的 Release 正文**与仓库里的正文是否仍然一致。
- **没有评审这几份报告的判断本身是否「对」**——只核了「读者会不会被误导」。
- **没有核这棵 worktree 上同树其他会话的未提交改动**（核稿期间 `CHANGELOG.md`、
  `docs/architecture/public-contracts.md`、`scripts/m10_selfcheck.py`、
  `src/dexatlas/cli/main.py`、`src/dexatlas/reports/evidence_package.py` 与两份
  `tests/` 文件是 modified 状态）。本报告**没有碰它们**，本轮的提交**只包含新增的
  这一份报告**；但读者若在别的提交上复核本报告的数字，**源指纹会不同**（§3.4 的第四个值）。

### 9.3 哪些结论依赖读者自己实跑

| 结论 | 依赖 |
|---|---|
| §3.1 CI 是否真的红 | 读者必须联网查 GitHub 的 run `44126968629`；仓库里**没有落盘记录** |
| §3.4 今天这棵树的指纹是 `a92ace15…` | 读者必须在自己的 checkout 上跑 `source_fingerprint()`；本报告的算法复刻见 §1 |
| §3.4 守指纹的那条测试今天是红的 | 读者必须跑那一条测试（本报告只读了断言） |
| §3.2 / §3.3 的 73 / 16 / 17 | 读者必须自己数演练报告的表格行——本报告数的是 **75 行**；判为「不一致」的格子 **17 个**（含 :80 那个双判定格）或 16 个（不含），判为「陈旧前提」的是 **16** 行 |
| §3.8 索引的份数 | 读者必须 `ls docs/reports/*.md \| wc -l`；今天是 52（减本页 = 51） |
| §3.14 tag 被重打 5 次 | 读者必须联网查 GitHub 的 tag 与 run 记录；仓库里**没有落盘记录**，只有 §4.3 的表 |
| 演练报告 §1.1 的全部实测耗时（2 分 19 秒克隆、9 分 21 秒全量测试…） | 只能在**同样的环境**下复现；本报告未复现 |

**给读者的最短路径**：想复核这五份文档的结论，只读这三份就够——
`docs/reports/README.md`（索引）、`docs/reports/release-process-dry-run.md`（哪棵树上、
哪些数字是实测的）、`docs/reports/portfolio-readiness-2026-11-18.md`（分数怎么来的）。
**但要先看本报告 §3.1 与 §3.4**：这两条决定了上面三份里哪些句子还能照单全收。

### 9.4 本报告发出之后，主会话已经改了什么

报告发出后（2026-11-18），主会话开始按它修这五份文档。**截至本报告这次修订，
在同一棵 worktree 的工作区里能看到的改动**（这些改动**尚未提交**，因此本报告不能把
它们算作「已发布的事实」）：

| 本报告的发现 | 工作区里看到的处置 |
|---|---|
| §3.1 CI「全绿」与演练报告打架 | `portfolio-readiness-2026-11-18.md` 开头加了「更正（2026-11-18，主会话）」段：明写「**那句话是错的**」，run `44126968629` 以 `failure` 结束、**4 个 job 红**，并声明**分数不变**（4/4 的依据是 `ci.yml` 的机制，不是那次运行的结果）。`release-process-dry-run.md` §0/§4.1 同步改成「CI 是红的」。**比本报告更准**（本报告采信的是演练报告当时「2 个 job 已红、run 未结束」的状态）。 |
| §3.2 / §3.3 73 / 16 / 17 | `release-process-dry-run.md` §0 改成 **75 项判定 / 50 一致 / 17 不一致 / 6 无法验证 / 2**，分组改成 `8+8+38+9+6+6`，并加了「复核更正」段说明原数字来自手工汇总。「陈旧数字/前提」改成 **16 处**（并注明 §7 表 17 行、第 17 行判的是「一致」）。`README.md:104` 的「73 项判定里 16 项…17 处」同步改。 |
| §3.11 清单 §8 只改了一半 | `v1.0.0-release-checklist.md` 的 §8 大标题、§8.2 的 B2（「没有人」→「有」）、C4 的「12 份」都已改。 |
| §3.4 清单 §5 B4「已关闭」 | 改成「**已关闭过一次**」——正是本报告说的「B4 曾经关闭过，但那一版是针对别的树的」。 |
| §3.19 `ci.yml:493-537` 越界 | **尚未见处置。** |
| §3.10 六处空行引用 | **尚未见处置。** |
| §3.9 三份文件没进索引 | **尚未见处置。** |
| §3.8 索引份数 45 / 41 / 51 | **尚未见处置。** |

**两点提醒：**

1. **§3.2 的尾巴还在**：主会话改成的「50 / 17 / 6 / 2」把
   `release-process-dry-run.md:80` 那一行（「不一致 + 无法验证」）同时算进了 17 与 6。
   四个数加起来是 75，但被分到桶里的只有 74 行。要么给这一行定一条规则，
   要么总数写成「判定格数」并注明有一行带两个判定。
2. **本报告的行号会漂**：这些文档正在被改，本报告里的 `file:line` 只在 `2c456e0`
   上成立（见文首的限定语）。**改完之后应当跑一遍
   `uv run --no-sync python scripts/remap-citations.py` 与
   `uv run --no-sync python scripts/check-doc-citations.py`**——
   而按 §7.1 的发现，**这两条命令查不出本报告 §3.10 / §3.19 那两类错**
   （因为这五份文档不在检查器的 `DOCS` 名单里）。**要先把名单扩了，
   再修那两处。**

---

## 附录 A：核查方法（可重跑）

```bash
# 1) 引用门禁（只读）
.venv/Scripts/python.exe scripts/check-doc-citations.py

# 2) 索引份数
ls docs/reports/*.md | wc -l            # 52（含索引自己）

# 3) 工作树与发布树的距离
git rev-list --count v1.0.0..HEAD      # 13
git diff --stat v1.0.0 HEAD -- src tests pyproject.toml scripts/

# 4) 今天这棵树的源指纹（按 scripts/refresh-report-figures.py 的算法复刻）
#    注意：工作区里有别的会话的未提交改动，所以这个值随时间变。
#    要一个稳定的数，用提交态重算：
git show 4fd86af:docs/reports/phase1-execution-report.md | grep source_fingerprint
#    → sha256:a92ace15…（提交态）；tag 75976e0 是 sha256:975afa8e…
```

---

## 附录 B：上一轮（[english-reader-review.md](english-reader-review.md)）的处理状态

上一轮核的是**五份对外英文文本**，留下 **49 条发现、其中 16 处必须改**。本轮核的是
**五份中文报告**，与此不重叠。本轮顺带核到上一轮的处置状态：

- 上一轮 16 处必须改 —— 索引 [README.md:132](README.md#L132) 记为「16 处修正进提交
  `7ba97c9`」。本轮未复核其内容（不在本轮范围内）。
- 上一轮报告体例被本报告沿用：读者人设 → 速览 → 逐条「原文引用 → 英文读者会怎么误读 →
  建议改法（给出可直接用的英文句子）」→ 只读边界 → 结尾交代做了什么、没做什么。
- 上一轮报告自己的一条纪律，本轮仍然适用并被本报告再次执行：
  **「凡出现数字的地方，都是从它指向的那份报告里抄来的，并在原地标了出处」**——
  本轮 §5.1 逐个数字标了出处与分母，其中 4 个（73、16、17、81.9 的四舍五入）
  **不符合**这条纪律。
