# 发布前最终一致性复核（v1.0.0）

**复核日期：** 2026-11-17 · **复核对象：** v1.0.0 发版前的七份对外文本 · **性质：** 只读复核

本文回答一个问题：**这七份对外文本放在一起读，会不会互相打架？**
七份文本是：

| # | 文本 | 位置 |
|---|---|---|
| 1 | `CHANGELOG.md` 的 `## [1.0.0] — 2026-11-17` 段 | `CHANGELOG.md:8`–`:519` |
| 2 | 仓库内发版说明 | `docs/releases/v1.0.0.md` |
| 3 | GitHub Release 正文草稿（含中文摘要；附录明确标注「Not part of the release body」） | `docs/reports/v1.0.0-github-release-body.md` |
| 4 | 当前状态页 | `docs/status.md` |
| 5 | 作品集描述 | `docs/portfolio.md` |
| 6 | 双语入口 | `README.md` / `README.zh-CN.md` |
| 7 | 公共契约表 | `docs/architecture/public-contracts.md` |

---

## 0. 方法与边界

**做了什么。** 把七份文本逐行读完，把每个数字与每条状态措辞追到仓库里的落盘出处
（benchmark 报告、契约活检脚本、测试文件、案例附件、git 对象），再把七份互相对一遍。
结论表里每一行都给出「七份文本里的写法（文件:行）」与「基准出处」，可直接复核。

**没做什么（硬边界）。**

- 未运行 `pytest --cov`、任何 `coverage` 命令、`uv sync`、`scripts/refresh-report-figures.py`；
  因此**覆盖率 93.3%、测试数 1,644 一律按已归档的测量值引用，不重测**。
- 未修改任何被核文本；本次只新增本文件。
- 只读门禁已跑通：`scripts/check-doc-citations.py`（220 条引用，0 漂移、0 悬空路径）、
  `scripts/check-version-claims.py --base auto`（2 条发现，均为 `8f9ddcaf` 已记录的既有项）。
- 契约活检脚本 `scripts/verify-public-contracts.py` **本次未执行**（它要起 uvicorn 并跑全量后端）；
  凡涉及它的地方，结论来自静态读码，文中标注「推断（静态）」。

**关于「推断」的用法。** 凡结论不是从文件直接读出的（主要是脚本行为、git 对象），
一律标注「推断」并给出依据所在行。依据不足的不写入清单。

---

## 1. 数字逐条核对

> **附件集在 2026-11-18 换过一轮**（3 包 / 9 文件 → 4 包 / 16 文件，
> 覆盖 2 次分析 → 4 次分析）。本节这一行按 v1.0.0 发版树记录；
> 现状见 [case-studies-third-package.md](case-studies-third-package.md)。

| 主题 | 七份文本里的写法（文件:行） | 基准出处 | 判定 |
|---|---|---|---|
| 测试总数 **1,644**（1,497 快 + 147 集成） | `docs/releases/v1.0.0.md:90`；`docs/reports/v1.0.0-github-release-body.md:164`；`docs/status.md:22`（脚本写，当前 1,643）；`docs/portfolio.md:67`（写作 1,644）；`README.md:12`（徽章，脚本写，当前 `tests-1643`）；`README.zh-CN.md` 无 | `docs/reports/phase1-execution-report.md:76` | 一致（5 处）——**手写的三处现值已是 1,644**；`docs/status.md:22` 与 `README.md:12` 那两处由 `scripts/refresh-report-figures.py` 写，当前仍是 1,643，最终重测量落盘即跟上。README.zh-CN 无徽章 → 见 §4.3 |
| 完整环境 **1,644 passed + 0 xfailed + 0 skipped** | `docs/reports/v1.0.0-github-release-body.md:165` | `docs/reports/phase1-execution-report.md:879` | 仅一处有（无冲突） |
| 一方覆盖率 **93.3%**（7,135 / 7,650 行） | `docs/releases/v1.0.0.md:94`；`docs/reports/v1.0.0-github-release-body.md:167`；`docs/status.md:23`；`docs/portfolio.md:68`；`README.md:13`（徽章）；`CHANGELOG.md` 1.0.0 段无；`README.zh-CN.md` 无 | `docs/reports/phase1-execution-report.md:77` | 一致（5 处） |
| MCP 只读工具 **11** | `CHANGELOG.md:333`（十个增至十一个）、`:354`；`docs/releases/v1.0.0.md:146`；`docs/reports/v1.0.0-github-release-body.md:198`；`docs/status.md:248`、`:358`；`docs/portfolio.md:47`；`README.md:254`；`README.zh-CN.md:191`、`:239`、`:316`；`docs/architecture/public-contracts.md` §3.1（11 行）、`:404` | `docs/architecture/public-contracts.md` §3.1 | 一致（12 处） |
| CLI **13** 个子命令 | `CHANGELOG.md:351`；`docs/architecture/public-contracts.md` §1.1 表 **13 行**（未写总数） | `src/dexatlas/cli/main.py`；契约表 §1.1 | 仅一处有总数（另一处可数，无冲突） |
| REST **23** 个端点 | `CHANGELOG.md:353`；`docs/architecture/public-contracts.md` §2 各表合计 **23 行**（未写总数） | `src/dexatlas/api/app.py`（23 条路由） | 仅一处有总数（另一处可数，无冲突） |
| 契约活检 **49 项**（28 REST + 6 MCP + 15 CLI） | `docs/releases/v1.0.0.md:65`；`docs/reports/v1.0.0-github-release-body.md:103`–`:104`、`:185`、`:274`–`:275`、`:338`；`docs/architecture/public-contracts.md:348`；`CHANGELOG.md:360`–`:361`（另记 M8 当时 46 项）；`docs/status.md` 未出现该数 | `scripts/verify-public-contracts.py` 的 `check()` 调用点计数 | 一致（6 处）；status.md 无 |
| 活检**实测条数** | `docs/architecture/public-contracts.md:359`–`:362`「仅 androguard 47/47、三后端齐备 48/48，退出码均为 0」；`docs/reports/v1.0.0-github-release-body.md:106`「executes 48 and passes all 48 with exit 0」、`:276`「三后端齐备那次实跑 48 项、48 项通过、脚本退出码 0」 | `scripts/verify-public-contracts.py:99`（服务起不来时才记的那一项）、`:466`–`:527`（按后端参与的分支）、`:653`–`:658`（条数合计与退出码） | **已一致** —— §3 第 9–10 条记的是修复前的不一致；`8483db2` 改了判定逻辑、`40ad42d` 改了契约表 §7 之后已消除 |
| 退出码 **0–6**（6 = `EXIT_NO_INDEX`） | `CHANGELOG.md:131`、`:138`、`:352`；`docs/releases/v1.0.0.md:74`、`:139`–`:146`；`docs/reports/v1.0.0-github-release-body.md:108`–`:110`、`:199`–`:201`；`docs/status.md:136`；`docs/architecture/public-contracts.md:43`–`:54` | `src/dexatlas/cli/main.py` | 一致 |
| 退出码 5 属 **v0.2.0**、6 是 **v1.0.0 新增** | `docs/releases/v1.0.0.md:138`；`docs/reports/v1.0.0-github-release-body.md:191`；`CHANGELOG.md:775`（位于 `[0.2.0]` 段内，段起于 `:520`）；`docs/status.md:135` | `docs/releases/v0.2.0.md` | 一致 |
| 一方示例 APK **5** 个 | `docs/releases/v1.0.0.md:76`；`docs/reports/v1.0.0-github-release-body.md:74`、`:180`；`docs/status.md:443`；`README.zh-CN.md:96`；`examples/` 下 5 个目录 | `docs/reports/phase1-execution-report.md:81` | 一致 |
| 案例附件 **9 个文件** / **3 个证据包** / 覆盖 **2 份分析** | `CHANGELOG.md:262`–`:266`（9 个文件、三个证据包、两个 project id）；`docs/releases/v1.0.0.md:57`–`:61`（nine files、两个 project id）；`docs/reports/v1.0.0-github-release-body.md:92`–`:94`（nine files，**未提覆盖几份分析**）、`:235`；`docs/portfolio.md:108`–`:110`（「the same analysis」）；`docs/status.md:134`（未给数） | `docs/case-studies/README.md`（三案例、三样本、三包、两份分析）；`docs/case-studies/attachments/` 实为 9 个文件、3 个 zip | 数字一致（**按 v1.0.0 发版树**；附件集已于 2026-11-18 换过一轮，见本节上方）；**「三包只覆盖两分析」仅 `docs/case-studies/README.md` 披露** → 见 §3 第 20 条 |
| 案例研究 **3 篇** / 一方样本 **3** 个 | `docs/portfolio.md:108`–`:110`；`docs/status.md:134`；`docs/releases/v1.0.0.md:55`；`docs/reports/v1.0.0-github-release-body.md:92`；`CHANGELOG.md:261`；**`docs/status.md:368` 写「≥2 个完整案例研究」** | `docs/case-studies/`（3 篇） | **不一致**（status.md 两处）→ 见 §3 第 21 条 |
| CI **6 job / 7 并行** | `docs/status.md:26`、`:49`；`docs/portfolio.md:67`（six CI jobs） | `.github/workflows/ci.yml` | 一致 |
| 契约快照测试项数 | `CHANGELOG.md:362`「`tests/test_public_contracts.py`（**22 项**）」 | `git show v1.0.0:tests/test_public_contracts.py` → **26** 个 `def test_`；退出码 6 的提交 `1f6ef05` 增 4 项 | **不一致** → 见 §3 第 11 条 |
| 第三方 fixture **2 个**、不入库 | `docs/reports/v1.0.0-github-release-body.md:181`–`:182`；`docs/releases/v1.0.0.md:77`–`:78` | `scripts/fetch-fixtures.sh` | 一致 |

---

## 2. M6 口径逐条核对

这是本次复核的重点：**M6 的每一个数字在七份文本里有几个写法**。

| 主题 | 七份文本里的写法（文件:行） | 基准出处 | 判定 |
|---|---|---|---|
| 首测 **24/60 = 40.0%**（逐轮 45/40/35） | `CHANGELOG.md:52`；`docs/releases/v1.0.0.md:23`；`docs/reports/v1.0.0-github-release-body.md:112`；`docs/status.md:133`；`README.md:410`；`README.zh-CN.md` 未写逐轮 | `docs/benchmarks/m6-level2-real.md:126` | 一致 |
| 首测**验收线** | `CHANGELOG.md:53`–`:54`「每轮 ≥80%、三轮合计 ≥90%」；`docs/reports/v1.0.0-github-release-body.md:110`–`:111`「≥16/20 per round and ≥54/60 (≥90%)」、`:235`（中文摘要同）；**`docs/releases/v1.0.0.md:24`「against the ≥90% acceptance bar」**；**`README.md:47`、`:539`「against ≥80%」**；**`README.zh-CN.md:31`、`:99`、`:422`「每轮 ≥80%」** | `docs/benchmarks/m6-level2-real.md:126`「每轮 ≥80%，三轮合计 ≥90%」 | **不一致（三种写法）** → 见 §3 第 1–6 条 |
| retest3 逐轮 **17/15/17** = 49/60（1,080,116 tokens） | `docs/status.md:133`；`CHANGELOG.md:120`–`:129`；`docs/benchmarks/m6-level2-retest3.md:28`–`:30`、`:41` | 同左 | 一致；**七份文本中无一处把 17/15/17 当成 retest4 的逐轮数** ✓（`CHANGELOG.md:126`–`:129` 还专门写了「此为执行层修复**之前**的三轮复测；最终结论以修复后的 retest4 为准」） |
| retest4 逐轮 **15/16/18** = 49/60（1,182,356 tokens） | `docs/releases/v1.0.0.md:28`–`:31`；`docs/reports/v1.0.0-github-release-body.md:113`–`:116`；`docs/status.md:133`；`README.md:48`、`:425`、`:539`；`README.zh-CN.md:33`、`:422` | `docs/benchmarks/m6-level2-retest4.md:28`–`:30`、`:38`、`:101` | 一致（9 处） |
| **B1 线**：每轮 ≥16/20 且三轮 ≥54/60 | `docs/reports/v1.0.0-github-release-body.md:110`、`:288`；`CHANGELOG.md:66`；`docs/status.md:133`（「每轮 ≥80% 且三轮合计 ≥90%」/「每轮 ≥16/20 且三轮合计 ≥54/60」两种等价写法） | `docs/benchmarks/m6-level2-retest4.md:3`、`:82`–`:83` | 一致（两种等价写法） |
| 窄验证 **4/6 → 2/6 → 3/6** | `docs/reports/v1.0.0-github-release-body.md:117`–`:122`、`:236`–`:237`；`docs/status.md:30`、`:36`、`:43` | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:31`–`:33`；`…-narrow-verify2.md:59`–`:61`；`…-narrow-verify3.md:59`–`:61` | 一致；第一轮 4/6 被如实标注为「运行不完整，不计为判定」 ✓ |
| 窄验证**两套门槛** ≥4/6 与 ≥3/5 | `docs/reports/v1.0.0-github-release-body.md:119`、`:237`；`docs/status.md:36`、`:43`；`README.md:53` | `docs/benchmarks/m6-verify3-plan.md:206`、`:230` | 一致；**两套门槛未被混用** ✓ |
| 停机口径：「连续**三**轮未达」 | `docs/status.md:44`；`docs/reports/v1.0.0-github-release-body.md:241`（中文摘要） | `docs/benchmarks/m6-verify3-plan.md:206`「**连续两轮未达后**，方案 3 为默认候选」；`docs/reports/v1.0.0-github-release-body.md:117` 英文正文自己写「The **two** narrow verification rounds」 | **不一致（3 vs 2）** → 见 §3 第 7–8 条 |
| 方案 3（现状披露） | `CHANGELOG.md:97`、`:459`、`:477`–`:478`；`docs/releases/v1.0.0.md:48`–`:49`；`docs/reports/v1.0.0-github-release-body.md:124`、`:241`、`:304`；`docs/status.md:38`–`:39`、`:45`–`:46` | `docs/benchmarks/m6-verify3-plan.md:206` | 一致 |
| **B1 未关闭** | `CHANGELOG.md:478`；`docs/releases/v1.0.0.md:48`–`:49`；`docs/status.md:38`；`README.md:539` | `docs/benchmarks/m6-verify3-plan.md:90` | 一致 |
| **M6 未收口** | `CHANGELOG.md:49`；`docs/status.md:133`；`README.md:539`；`README.zh-CN.md:422`；`docs/releases/v1.0.0.md:20`–`:25` | `docs/benchmarks/service-regression-set.md` §5 | 一致 |
| **M10 独立验收尚未开始** | `CHANGELOG.md:294`–`:295`；`docs/status.md:3`、`:13`、`:128`、`:137`；`docs/reports/v1.0.0-github-release-body.md:151`–`:153`、`:242`；`README.md:33`、`:61`；`docs/releases/v1.0.0.md`（经 `:49` 与 status 口径） | `docs/reports/m10-acceptance-pack.md` | 一致（**七份文本里口径最一致的一条**） |
| retest4 的**成因** | `docs/releases/v1.0.0.md:26`–`:27`「execution-layer fixes (four) and the C2 single-word fallback」；`README.md:424`「after the execution-layer fixes」；**`README.md:539`、`README.zh-CN.md:422`「after failure-mode analysis and five root-cause fixes」** | `docs/benchmarks/m6-level2-retest4.md:3`（执行层修复后的 B1 验收测量）；`docs/benchmarks/m6-level2-retest2.md:5`（五项根因修复 → 16/20 = 80.0%） | **不一致（两语种 README）** → 见 §3 第 3、6 条 |
| 首测 token **853,103**（超 800,000 上限 53,103） | `CHANGELOG.md:54`–`:55`；`docs/status.md:133`；`README.md:411`–`:412` | `docs/benchmarks/m6-level2-real.md:112` | 一致 |

---

## 3. 状态措辞与中英一致

### 3.1 状态措辞

| 主题 | 七份文本里的写法（文件:行） | 基准出处 | 判定 |
|---|---|---|---|
| Phase 3 的状态 | `README.md:32`–`:34`「Phase 3 **is delivered**」；`README.zh-CN.md:22`–`:23`「Phase 3 **已交付**」；**`README.md:41`–`:42`「Phase 3 **is under way**」**；**`README.zh-CN.md:28`–`:29`「Phase 3 正按…推进」**；`docs/status.md:128`「Phase 3 的退出标准未全部达成」 | `docs/status.md:128` | **不一致（同一横幅内自相矛盾）** → 第 12–15 条 |
| `v1.0.0` 的发布门槛 | `README.md:32`、`README.zh-CN.md:22`、`docs/status.md:22`、`:128`「v1.0.0 已发布（tag 2026-11-17）」；**`README.md:545`–`:546`、`README.zh-CN.md:428`「只有本计划的退出标准全部通过，才会考虑 `v1.0.0`」** | tag `v1.0.0` 确实存在（`git rev-list -n1 v1.0.0` → `8f9ddca`，tag 日期 2026-11-17），但 `docs/status.md:128` 明写退出标准未全达成 | **不一致** → 第 16–17 条 |
| 「早期开发 / early development」 | `README.md:32`；`README.zh-CN.md:22` | — | **中英一致 ✓**；`docs/portfolio.md:117` 另用「Actively developed」→ 第 22 条 |
| macOS | `docs/releases/v1.0.0.md:107`；`docs/reports/v1.0.0-github-release-body.md:148`–`:149`；`docs/status.md:135`；`README.md:541`、`README.zh-CN.md:424` | `docs/reports/m8-install-rehearsal.md` | 一致（都写「未验证，Windows/Linux 是被测平台」）✓ |
| 退出码 6 的**定位** | **「已决策并记录为已知限制」**：`README.md:541`、`README.zh-CN.md:424`；**「已按提案修复：新增退出码 6」**：`docs/status.md:135`；**正式对外契约**：`docs/architecture/public-contracts.md:54`、`:458`–`:483` | `docs/proposals/exit-code-partial-read.md`；`CHANGELOG.md:131` | **不一致** → 第 18–19 条 |
| 第三方署名 | `README.md:481`–`:499`（JADX / Apktool / Androguard，均 Apache-2.0）；`README.zh-CN.md:371`–`:386`（同） | — | **中英一致 ✓** |
| 覆盖率口径（`plain pytest --cov` 看不到 `tools/androguard/worker.py`） | 仅 `docs/reports/v1.0.0-github-release-body.md:164`–`:166` | — | 仅一处有（不冲突） |

### 3.2 中英等价性（README 两份 + release body 中英摘要）

| 主题 | 英文 | 中文 | 判定 |
|---|---|---|---|
| 状态横幅骨架 | `README.md:32`–`:58` | `README.zh-CN.md:22`–`:38` | 骨架一致；但**中文横幅完全没有窄验证 2/6、3/6 与 ≥4/6 / ≥3/5 两套门槛**（英文 `:51`–`:57` 有）→ 第 14 条 |
| Phase 3 路线图表 | `README.md:131`（含窄验证 2/6→3/6、≥4/6 门槛、moved to state-of-record disclosure） | `README.zh-CN.md:99`（**全缺**） | **不等价** → 第 5 条 |
| M6 路线图表 | `README.md:539`（含窄验证与停止结论） | `README.zh-CN.md:422`（**全缺**） | **不等价** → 第 6 条 |
| 第三方署名表 | `README.md:481`–`:499` | `README.zh-CN.md:371`–`:386` | 等价 ✓ |
| 状态横幅措辞 | 「early development」 | 「早期开发」 | 等价 ✓ |
| release body 中英摘要 | `:105`–`:153` | `:235`–`:255` | **等价 ✓**（两处都写全了首测验收线；唯一分叉是「连续三轮」，见 §2） |
| 测试/覆盖率徽章 | `README.md:12`–`:13`（tests-1644、coverage-93.3%） | `README.zh-CN.md:1`–`:9` **无徽章** | 不对等 → 第 23 条 |

---

## 4. 必须统一的 23 处

> **只列清单，不改任何被核文本。** 每条给出文件、行号、现状、建议改法、依据。
> 优先级：**高** = 会被读者直接误判结论；**中** = 口径残缺或互相矛盾；**低** = 对等性/措辞。

### A 组 — M6 首测验收线（6 处，优先级：高）

**1. `docs/releases/v1.0.0.md:24`**
- 现状：`scored **24/60 = 40.0% (45%/40%/35% per round) against the ≥90% acceptance bar — not passed**`
- 建议：改为「against the acceptance bar of ≥16/20 per round and ≥54/60 (≥90%) over three rounds — not passed」
- 依据：`docs/benchmarks/m6-level2-real.md:126`「每轮 ≥80%，三轮合计 ≥90%」；`docs/benchmarks/m6-level2-retest4.md:3`；本仓库七份文本中另有六处写的是「每轮 ≥80%」或两门槛并列，只有此处写「≥90%」。

**2. `README.md:47`**
- 现状：`did **not** meet the acceptance line (DexAtlas 40.0% over three rounds against ≥80%; …)`
- 建议：拆开两个口径——「per-round 45%/40%/35% are all below the ≥16/20 (≥80%) line, and the three-round total 40.0% is below the ≥90% line」；不要拿三轮合计去比每轮线。
- 依据：`docs/benchmarks/m6-level2-real.md:126`。

**3. `README.md:539`**
- 现状：`after failure-mode analysis and five root-cause fixes, the full three-round [retest]（链接指向 …/m6-level2-retest4.md）scored DexAtlas 49/60 …`；同格另有「against the ≥80% acceptance line」
- 建议：成因改为「after the execution-layer fixes」（本文件 `:424` 已经这么写）；验收线改为两门槛并列。
- 依据：`docs/benchmarks/m6-level2-retest4.md:3`（retest4 是执行层修复后的 B1 验收测量）；`docs/benchmarks/m6-level2-retest2.md:5`（五项根因修复 → 16/20 = 80.0%，是 retest2 不是 retest4）；`docs/releases/v1.0.0.md:26`–`:27`。

**4. `README.zh-CN.md:31`**
- 现状：`（DexAtlas 三轮合计 40.0%，验收线为每轮 ≥80%；见 …）`
- 建议：同第 2 条，改为逐轮与三轮合计各自对应的两条门槛。
- 依据：`docs/benchmarks/m6-level2-real.md:126`。

**5. `README.zh-CN.md:99`**
- 现状：`未通过：首批 40.0%，低于 80% 验收线；…`
- 建议：改为「首批 40.0%（逐轮 45%/40%/35%），未达每轮 ≥16/20 且三轮合计 ≥54/60 的门槛」；并补上英文同格已有的窄验证 2/6→3/6 与 ≥4/6 门槛（见 §3.2）。
- 依据：`README.md:131`；`docs/benchmarks/m6-level2-real.md:126`。

**6. `README.zh-CN.md:422`**
- 现状：`（DexAtlas 三轮合计 24/60 = 40.0%，验收线为每轮 ≥80%）；失败模式分析与五项根因修复后，三轮完整[复测]（链接指向 …/retest4.md）…`
- 建议：① 验收线两门槛并列；② 成因改为「执行层修复后」（与 `README.md:539` 同步改）；③ 补英文格已有的窄验证 2/6、3/6、≥4/6/≥3/5 与「转方案 3 现状披露」。
- 依据：`docs/benchmarks/m6-level2-retest4.md:3`；`docs/benchmarks/m6-level2-narrow-verify2.md:61`、`…-narrow-verify3.md:61`；`docs/benchmarks/m6-verify3-plan.md:206`。

### B 组 — 停机轮次（2 处，优先级：高）

**7. `docs/status.md:44`**
- 现状：`连续三轮未达后，按 [m6-verify3-plan.md] §7 停止，**方案 3（现状披露）为最终定稿路径**`
- 建议：改为「窄验证二、三两轮连续未达后（第一轮运行不完整、不计为判定）」。
- 依据：`docs/benchmarks/m6-verify3-plan.md:206`「**连续两轮未达后**，方案 3「现状披露」为默认候选」；本页 `:30`–`:31` 自己已写明第一轮不完整。

**8. `docs/reports/v1.0.0-github-release-body.md:241`**
- 现状：`连续三轮未达后（其中第一轮运行不完整、**不计为判定**），按验收方案的**方案 3（现状披露）**停止追加投入`
- 建议：改为「连续两轮未达后（窄验证二、三；第一轮运行不完整、不计为判定）」；括注保留。
- 依据：同第 7 条；本文件英文正文 `:117` 自己写的是「The **two** narrow verification rounds」——**同一文件的中英两版已经互相矛盾**。

### C 组 — 契约活检条数（2 处，优先级：中）

**9. `docs/architecture/public-contracts.md:355`**
- 现状：`2026年11月17日实测为 47/47 通过；三个后端齐备时是 49/49。`
- 建议：改为「47/47 通过（缺 JADX，源码头检查不触发）；三个后端齐备时为 **48/48** —— `server comes up` 这一项只在服务起不来时才记录，通过的运行不会触发它。」
- 依据（推断，静态）：`scripts/verify-public-contracts.py:92`–`:100` 是一个 `for … else`：重试全部失败才走 `else` 分支记录 `check("server comes up", False, …)` 并 `return`；`:264` 的源码头检查只在 HTTP 200 时触发。REST 共 28 个调用点，其中仅 1 个会随后端齐备而多触发 → 27 + 6 + 15 = **48 为上限**。同结论在 `docs/reports/m10-reader-walkthrough.md:88` 已经用「REST 里有 2 个条件调用点，无源码后端的机器上是 26，合计 47」的说法写对过一遍。

**10. `docs/reports/v1.0.0-github-release-body.md:312`**
- 现状：`…the 2026-11-17 re-run passed 47/47 on that machine, because two checks are conditional (the source-endpoint header check needs the endpoint to answer, and **the server check needs the service up**) — with the full backend set it is 49/49`
- 建议：改为 `… because two checks are conditional (the source-endpoint header check needs the endpoint to answer; the server check is only recorded when the service fails to come up) — with the full backend set it is 48/48`。
- 依据：同第 9 条。**括注把语义写反了**：脚本记录的是服务**没**起来，不是起来了。

### D 组 — CHANGELOG 内的过期数字（1 处，优先级：中）

**11. `CHANGELOG.md:362`**
- 现状：`新增契约快照测试 \`tests/test_public_contracts.py\`（**22 项**）`
- 建议：改为 **26 项**。
- 依据：`git show v1.0.0:tests/test_public_contracts.py` 现有 **26** 个 `def test_`；退出码 6 的提交 `1f6ef05` 新增 4 项（22 → 26）。同一段 `:360`–`:361` 已经写明「v1.0.0 的契约表为 49 项（…含新增的退出码 6 活检）」，却没同步测试项数。

### E 组 — Phase 3 状态措辞（4 处，优先级：中）

**12. `README.md:32`–`:34`** ／ **13. `README.md:41`–`:42`** ／ **14. `README.zh-CN.md:22`–`:23`** ／ **15. `README.zh-CN.md:28`–`:29`**
- 现状：第 12/14 条写「Phase 3 is delivered / Phase 3 已交付」；第 13/15 条写「Phase 3 is under way / Phase 3 正按…推进」。两条在同一份文件的同一段横幅里。
- 建议：统一为「Phase 3 的交付物已发布，但退出标准未全部达成（M6 未收口、M10 未开始）」，并把「is under way / 正按…推进」改成不与前句冲突的表述（如「Phase 3 按作品集计划推进」改为「Phase 3 的各里程碑状态见下」）。
- 依据：`docs/status.md:128`「M10 独立验收尚未开始，Phase 3 的退出标准未全部达成」；`docs/status.md:133`（M6 未收口）。

### F 组 — v1.0.0 发布门槛措辞（2 处，优先级：高）

**16. `README.md:545`–`:546`** ／ **17. `README.zh-CN.md:428`**
- 现状：`Only after this plan's exit criteria all pass will \`v1.0.0\` be considered — phases advance on evidence, not on a calendar.`（中：`只有本计划的退出标准全部通过，才会考虑 \`v1.0.0\``）
- 建议：改成历史口径，如「本计划原本以退出标准全部通过为准；`v1.0.0` 已于 2026-11-17 按现状披露口径发布，M6 与 M10 的验收仍未关闭（见 `docs/status.md`）」。
- 依据：tag `v1.0.0` 存在（`8f9ddca`，2026-11-17），`README.md:32`、`README.zh-CN.md:22`、`docs/status.md:22`、`:128` 均写「已发布」；`docs/status.md:128` 同时写「退出标准未全部达成」。**现状是「已发布」与「未达门槛」并存**，读者照字面读会得出「发版违反了本项目自己的门槛」。

### G 组 — 退出码 6 的定位（2 处，优先级：中）

**18. `README.md:541`** ／ **19. `README.zh-CN.md:424`**
- 现状：`the all-backends-time-out exit-code question is decided and recorded as a known limitation`（中：`三后端全超时的退出码问题已决策并记录为已知限制`）
- 建议：改为「已实现为退出码 6（`EXIT_NO_INDEX`），并写入公共契约表」——它不是限制，是已发布的契约。
- 依据：`docs/status.md:135`「M8-4…已按[提案]修复：新增退出码 6（EXIT_NO_INDEX），0–5 语义不变」；`docs/architecture/public-contracts.md:54`（退出码表列 6）、`:458`–`:483`（「与承诺的缺口（已补）」一节把它作为契约写明）；`CHANGELOG.md:131`。

### H 组 — 案例附件的表述（3 处，优先级：中）

**20. `docs/reports/v1.0.0-github-release-body.md:92`–`:94`**
- 现状：`three rewritten case studies with their attachments committed under \`docs/case-studies/attachments/\` — **nine files, each generated by the command printed in its study and checked with \`verify_package\`**`
- 建议：① 改为「nine files …; the three evidence packages were checked with `verify_package`」（9 个文件里只有 3 个是证据包，6 个是报告 md/json/html，`verify_package` 只校验证据包）；② 补一句「the three evidence packages cover two analyses — the demo and api-integration packages come from one run」。
- 依据：`docs/case-studies/attachments/` 实为 9 个文件、3 个 zip；`docs/case-studies/README.md`（三案例用三个样本、三个证据包只覆盖两份分析、demo 与 api-integration 同源于 `run_e112e717…`）；`CHANGELOG.md:265`–`:266`（三个证据包均通过 `verify_package`）。
  > **建议 ② 已作废（2026-11-18）**：附件集换过一轮，仓库里现在是 **16 个文件、4 个
  > zip、4 次分析**，`run_id` 两两不同；建议 ① 里的「nine files」也要跟着改。见
  > [case-studies-third-package.md](case-studies-third-package.md)。

**21. `docs/status.md:368`**
- 现状：`≥2 个完整案例研究 | **完成**——demo-app 从分析到证据链的完整走查；混淆样本走查（含 multi-DEX 附录）`
- 建议：加一句「（M7 之后已扩为 3 篇，含 API 集成走查）」。
- 依据：`docs/case-studies/` 下 3 篇（`demo-app-walkthrough.md`、`obfuscated-app.md`、`api-integration.md`）；同页 `:134`（M7 行）已写「三个案例…重写」。该行是 M4 历史记录（2026-11-14），但读者会当成现状。

**22. `docs/portfolio.md:117`**
- 现状：`Actively developed; the current release is v1.0.0`
- 建议：与 README 的成熟度口径对齐，改成「early development」/「早期开发」并保留「actively developed on the v1.0.0 line」之类的补充说明，避免单独读这一页的读者得到比 README 更高的成熟度印象。
- 依据：`README.md:32`、`README.zh-CN.md:22`。**注意**：portfolio.md 是面向客户的文本，「Actively developed」在这里是**对外承诺**，与「early development」并列出现会让客户高估成熟度。

### I 组 — 中英对等（1 处，优先级：低）

**23. `README.zh-CN.md:1`–`:9`**
- 现状：整个文件没有 CI / Python / License / **Tests / Coverage** 徽章，而 `README.md:9`–`:15` 有 6 枚徽章（含 `tests-1644`、`coverage-93.3%`）。
- 建议：至少补 `tests-1644` 与 `coverage-93.3%` 两枚。
- 依据：`README.md:12`–`:13`；`docs/reports/phase1-execution-report.md:76`–`:77`。**取舍**：README.md 徽章是 `refresh-report-figures.py` 生成的，中文版无法自动同步，需人工维护——这一条要么补，要么在中文版写明「以英文版徽章为准」。

---

## 5. 对外承诺清单

从这七份文本读出去的承诺，读者/客户**可以合理相信**什么、**不能相信**什么。

### 5.1 可以相信（有落盘出处，且七份一致）

1. **测试 1,588、一方覆盖率 93.3%（7,117/7,631）** 是 v1.0.0 发版树上的实测值，可由 `docs/reports/phase1-execution-report.md` 重算；文档改动不影响该指纹。
2. **公共契约是冻结的**：CLI 13 个子命令、REST 23 个端点、MCP 11 个只读工具、退出码 0–6（6 = `EXIT_NO_INDEX`），并有契约快照测试守着。
3. **退出码 6 是 v1.0.0 新增**，0–5 的语义一字未改；退出码 5 早在 v0.2.0 就有。
4. **M6 层级 2 未达验收线**（首测 40.0%，修复后三轮 49/60 = 81.7%）；**B1 未关闭**；**M10 独立验收尚未开始**；最终按**方案 3（现状披露）**定稿，不再追加修复轮。七份里口径最一致的一条。
5. **分析是静态、证据优先的**：结论分 verified / lead / insufficient，每条事实带 provenance；后端失败被报告成一个值而不是崩溃；**agent 的回答是待核的线索，永远不是已验证的发现**。
6. **平台支持范围**：Windows / Linux 是被测平台，**macOS 未验证**；原生/动态分析、插件生态、已发布的 Upwork 服务页都不在本次范围内；它不是渗透测试、不是恶意软件判定、不是脱壳器。
7. **五个一方示例 APK 与其源码同在仓库里**，第三方 fixture 由 `scripts/fetch-fixtures.sh` 拉取、不入库；不需要安装即可审阅证据。
8. **三篇案例研究基于真实运行**，每条结论都带证据定位或 id；证据包有 manifest 的逐文件 sha256 与 `not_included` 声明。

### 5.2 不能据此相信（读起来像承诺，实际没保证）

1. **「agent 已达标」** —— 七份里没有一份说达标，但两处 README 的验收线只写了一半（只写 ≥80%），会让人以为门槛低得多；实测是**每轮 ≥16/20 且三轮合计 ≥54/60**，两条都没过。
2. **「Phase 3 已交付 / 已完成」** —— 退出标准未全部达成（M6 未收口、B1 未关闭、M10 未开始）。
3. **「v1.0.0 是按本计划退出标准通过后才发布的」** —— README 末尾仍写着这句话，而 tag 已经打了、文档写着「已发布」。按字面读，读者会认为发版违反了项目自己的门槛。
4. **「49 项契约活检全部通过」** —— 清单里是 49 项，但通过的一轮最多跑到 48 项；2026-11-17 实测是 **47/47**。
5. **「三个案例 = 三份互相独立的分析证据」** —— 三篇走查用了三个一方样本（demo / obfuscated / multidex），但**三个证据包只覆盖两份分析**（demo 与 api-integration 同源于一次运行）；multidex 样本没有证据包。
   > **已闭合（2026-11-18）**：附件集换过一轮，仓库里现在是**四个证据包、四次分析**
   > （`run_id` 两两不同，multidex 附录也有了自己的包），对外文案已同步。
   > 见 [case-studies-third-package.md](case-studies-third-package.md)。
6. **「九个附件都经过 `verify_package` 校验」** —— 只有 3 个证据包经过该校验，6 个是报告文件。
   > **按 v1.0.0 发版树**：附件集换过一轮后是 **4 个证据包经过该校验、
   > 12 个是报告文件**（共 16 个文件）。
7. **「退出码问题只是被记为已知限制」** —— 退出码 6 已经实施并写进公共契约表。
8. **「GitHub Release 页面已经发布」** —— 仓库内 tag `v1.0.0` 确实存在（2026-11-17），但 Release 正文仍是**草稿**，其抬头明确写着「本稿不打 tag、不建 Release」。README 说「已发布」指的是版本与 tag，不是 GitHub 上的 Release 页面。
9. **「有客户案例 / 客户成果」** —— 仓库里没有已发布的客户案例或服务页；`docs/portfolio.md` 是**能力描述**，不是交付履历（它自己写了「not a malware classifier」这类边界）。
10. **「93.3% 覆盖了全部一方代码」** —— `plain pytest --cov` 看不到 `tools/androguard/worker.py`（该模块在子进程里跑），这一点只有 release body `:164`–`:166` 写了。

### 5.3 一句话结论

**这七份文本对「工具做了什么」承诺得可信且有出处，对「工具做成了什么」则口径不齐**——问题全部集中在三处：M6 的验收线被写成三种、停机轮次写成三轮而方案是两轮、契约活检的上限被写成 49/49 而实际最多 48；再加上 README 里「已发布 / 才会被考虑」与「已交付 / 正在推进」两对自相矛盾的措辞，读者**不能**从这七份文本推断出「v1.0.0 满足了项目自己定的门槛」——恰恰相反，文本自己承认 M6 未收口、B1 未关闭、M10 未开始。

---

## 6. 本次复核的局限

- 覆盖率与测试数**未重测**（硬约束），一律按发版树归档值引用。
- `scripts/verify-public-contracts.py` **未执行**（要起 uvicorn 跑全量后端）；第 9–10 条关于「最多 48 项」的结论来自静态读码，已标注「推断（静态）」并给出 `scripts/verify-public-contracts.py:92`–`:100`、`:264` 两处依据。
- GitHub Release 页面是否已存在**无法在离线环境核实**；本报告只核实了仓库内的 tag。
- 本报告只核七份对外文本之间的横向一致性，以及它们与落盘出处的纵向一致性；**没有**逐条复核各 benchmark 报告自身的数值正确性（那是 `docs/reports/stale-number-scan.md` 与各 benchmark 报告的责任范围）。
- 全文不含任何 API key / secret 样式字符串；引用 `docs/benchmarks/m6-verify3-plan.md:172` 一带时只复述了「出现 `sk-` 命中即停」这一规则本身，未复现任何凭据。
