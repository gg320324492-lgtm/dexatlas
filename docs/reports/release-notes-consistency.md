# v1.0.0 发布文本一致性复核

> 本次为只读复核，未创建 tag、未发布任何内容。除新增本文件
> （`docs/reports/release-notes-consistency.md`）外，未改动仓库内任何文件。

## 0. 复核范围与基线

| 项 | 值 |
|---|---|
| 复核对象 A | `docs/releases/v1.0.0.md` —— 随 tag 发布的仓库内发版说明（已定稿） |
| 复核对象 B | `docs/reports/v1.0.0-github-release-body.md` —— GitHub Release 正文草稿（本轮新出） |
| A 的基线 commit | `78102a8`（`claude/m6-level2-verify`，= 共享树 `E:\Dexatlas` 的 HEAD） |
| B 的基线 commit | `23ec6fa`（`claude/release-body`），已合入 `78102a8`；`git diff 23ec6fa 78102a8 -- docs/reports/v1.0.0-github-release-body.md` 为空，两处内容逐字相同 |
| 复核手段 | Read / Grep / `git show` / `git diff`。**未**运行 pytest、`pytest --cov`、coverage 或 `uv sync`；**未**打 tag、push tag、创建 GitHub Release |
| 工作位置 | 本复核在独立 worktree `E:\Dexatlas\.claude\worktrees\release-notes-consistency-1c6965` 内完成（分支 `audit/release-notes-consistency`，基线已切到 `origin/claude/m6-level2-verify` = `78102a8`），未触碰共享树 `E:\Dexatlas` |

### 0.1 共享工作树覆盖率污染说明（重要）

共享树 `E:\Dexatlas` 的**工作副本**里，`docs/reports/phase1-execution-report.md` 已被并发
`pytest --cov` 污染，一方覆盖率被写成 **35.4%（2699/7631）**，`tools/androguard/worker.py`
一行被写成 `0.0%`（实测 `git -C E:\Dexatlas diff -- docs/reports/phase1-execution-report.md`
确认）。**该工作副本不可引用。**

本报告一律以 `git show HEAD:docs/reports/phase1-execution-report.md`（即 `78102a8`）为准，其
正确值为：

- 一方代码覆盖率 **93.2%（7109/7631 行）** —— `docs/reports/phase1-execution-report.md:77`
- 测试数 **1584（1437 快 + 147 集成）** —— 同文件 `:76`、`:877`

发布正文（B）与附录引用的 93.2% / 1584 与仓库 HEAD **一致**，无需改动；被污染的只有共享树
工作副本，不是任何一份发布文本。

### 0.2 一处测量批次说明

B 的「Verification」节声明这组数字测自 commit `277d0fa`，指纹 `sha256:ccea379b…`，并说后续的
纯文档提交 `8868e30` 不影响该指纹。已逐条核实：

- `277d0fa` 与 `8868e30` 均为 `78102a8` 的祖先；
- `git diff --name-only 277d0fa 8868e30` 只含 `docs/` 下的文件，**不含** `src/`、`tests/`、
  `pyproject.toml`、`scripts/refresh-report-figures.py`；
- 指纹的覆盖范围见 `scripts/refresh-report-figures.py:110`（`FINGERPRINT_FILES`）与
  `:487-506`（`fingerprint_files()` 收集 `src/`、`tests/` 下的 `*.py` 加上那两个固定文件）；
- 「测试套件会重算指纹、报告过期即失败」的说法成立：`tests/test_docs.py:687`；
- `git log -1 --format=%B 277d0fa` 的正文确实写着「完整测量在最终树刷新：指纹 ccea379b…，
  suite 1584 passed / 0 failed，覆盖率 93.2%」，与 B 附录 `:269` 的引述逐字相符。

⇒ B:164-171 的测量声明**属实**，无需修改。

---

## 1. 逐节对照

| 主题 | `docs/releases/v1.0.0.md:行` | `v1.0.0-github-release-body.md:行` | 一致 / 不一致 / 仅一侧有 | 建议以哪一侧为准及理由 |
|---|---|---|---|---|
| 标题 | 1 | 1 | 一致 | 两侧同题「DexAtlas v1.0.0 — The Evidence-First Portfolio Milestone」。无需改 |
| 开篇导语（定位 + 边界一句） | 3-13 | 12-31 | 一致（措辞不同） | 两侧都含「静态、证据优先；agent 的答案只是待核线索」这一句限定。B 的展开更细（结论分级 `verified`/`lead`/`insufficient`、后端失败是值不是崩溃），A 也没有与之冲突的表述。两边都可用 |
| Highlights / What's in this release | 15-70 | 33-105 | 一致（粒度不同） | A 把 M5–M9 与文档修正平铺成 6 条；B 拆成「本轮交付」+「里程碑」两组，事实集合相同。以内容为准，不需对齐结构 |
| 「本轮交付」小节 | — | 35-76 | 仅一侧有 | B 多出 4 条本轮交付（预算效率四项修复 + 行裁剪、M-1/L-1 两处审查遗留、发版草案/runbook/checklist/dry-run、文档同步）。**无冲突**，属 A 未收录的新增信息；不必回填 A |
| M5 claims baseline | 17-19 | 80-82 | 一致 | 两侧都写「每个对外结论对着代码与已落盘 trace 复核、三个基准逐字节可重算」。以 A 为准（多一个 `[phase3-baseline.md]` 链接） |
| M6 冻结 20 题服务回归集 | 20-45 | 83-89 + 109-130 | 一致（数字位置不同） | A 把 M6 数字写进里程碑条目；B 的里程碑条目只作指针（"the measured numbers are in *Known limitations* below"），数字集中在 Known limitations。**内容等价**，不建议改 |
| M7 客户交付包 | 46-54 | 90-94 | 一致 | 两侧都写：离线单文件 HTML（`analyze --html`）+ 最小证据包（`dexatlas export`）+ 三个案例 + `case-studies/attachments/` 下 9 个文件、逐例由案例正文印出的命令生成并经 `verify_package` 校验。A 额外列出两个案例 APK 的标识（`apk_80a8fe0e81204c9f`/`apk_2f8d476fb9e71ac4`），非冲突 |
| M8 安装 / 契约 / 失败恢复 | 55-63 | 95-100 | 一致 | 两侧同写 `--workspace`/`-w` 全命令化、契约表 **46/46**（26 REST + 6 MCP + 14 CLI）、clean-install/Docker/失败恢复演练、退出码 6 `EXIT_NO_INDEX`。数字逐字一致 |
| M9 展示层 | 64-66 | 101-103 | 一致 | 两侧同写：双语 README、文档地图、第三方归属、roadmap 表；「Upwork 物料仍是未发布草稿」 |
| 文档修正（install.md 矛盾等） | 67-70 | 71-76 | 一致 | 两侧同写「install 指南不再声称仓库里没有 APK；`examples/` 下有 5 个一方样例 APK 并带源码；第三方样例仍由 `scripts/fetch-fixtures.sh` 拉取」 |
| **What this release does NOT include** | 72-86 | 143-147（降级为 Known limitations 里的一条） | 语义一致，分节方式不同 | B 把 A 的整节 5 条压成 Known limitations 的第一条。**逐条内容对得上**（见 §3），仅结构不同。不必强行同构 |
| Known limitations | 88-104 | 107-150 | 一致（B 多 5 条） | A 3 条（后端全败仍记 `completed`、层级 2 边界与 A/B 预算说明、混淆样例的覆盖面）；B 8 条，另加「本次发布不含二进制制品」「窄验证停止条件」「M6 承诺范围」「agent 答案是线索」「独立验收尚未开始」。B 更全，**无一条与 A 冲突** |
| **Verification** | — | 152-180 | 仅一侧有 | A 完全没有验证数字。内容属实（见 §2），**是否回填 A 见 §7 U9** |
| Upgrading from v0.2.0 / Upgrade notes | 106-134 | 182-212 | 一致 | 逐条对齐：退出码 6、`--workspace` 全命令化、MCP 工具 10→11、agent 默认预算 120,000 tokens/16 迭代/120 s/40 步、`--html` 与 `export` 新增、install extras。见 §4 |
| 中文摘要 | — | 214-247 | 仅一侧有 | B 独有的中文摘要，**与英文正文有 1 处口径不等价**（§6 / §7 U2） |
| **Licence** | 136-139 | — | 仅一侧有 | A 有整节，B 全篇没有（中文摘要也没有）。见 §7 U4 |
| Appendix（数字出处表） | — | 251-318 | 仅一侧有（草稿专用） | B 的草稿注记（3-8 行）已声明「`## Appendix` 起的内容不得贴进 GitHub Release」。**贴出正文时应同时删掉 3-8 行的草稿注记本身**，实际发布体 = 10-249 行 |

**结论**：**没有一边多写整节、也没有一边漏写整节之外的语义内容**，但有 4 处「一边有、一边无」的整块信息
（Verification、Licence、M10 独立验收、不含二进制制品）—— 见 §7 清单。

---

## 2. 数字逐个对齐

| 主题 | A（`docs/releases/v1.0.0.md`） | B（`v1.0.0-github-release-body.md`） | 一致 / 不一致 / 仅一侧有 | 核查依据 |
|---|---|---|---|---|
| M5 三个基准逐字节可重算 | 17-19 | 80-82 | 一致 | `docs/reports/phase3-baseline.md` |
| M6 层级 0 确定性判分 20/20（零模型） | 21 | 84、290 | 一致 | `docs/benchmarks/service-regression-set.md:173` |
| M6 层级 1 scripted 演练 | 22-23 | 84-87、291 | 一致（B 更严） | B 补「替身模型、成绩原样公开、证明发题/trace/判分管线可用，不是模型能力基线」；`docs/status.md:133` 同口径 |
| M6 层级 2 首测 **24/60 = 40.0%**（逐轮 45%/40%/35%） | **23-24、74-75** | **正文无**（仅附录 289） | **仅一侧有** | `docs/benchmarks/m6-level2-real.md:29`（`DexAtlas \| 9/20 \| 8/20 \| 7/20 \| 24/60 \| 40.0%`） |
| M6 三轮复测合计 **49/60 = 81.7%** | 27、76、99 | 112、229、279、293 | 一致 | `docs/benchmarks/m6-level2-retest4.md:38`、`:83` |
| M6 逐轮 **15/16/18** | 28、76、99 | 112-113（写作「15/20, 16/20, 18/20」） | 一致 | `m6-level2-retest4.md:28-30`、`:82` |
| M6 验收线 每轮 ≥16/20、三轮 ≥54/60（≥90%） | 29、75 | 110-111、114、276 | 一致 | `m6-level2-retest4.md:3`、`:83` |
| M6 复测 token 合计 **1,182,356** | **30** | **正文无**（仅附录 282） | **仅一侧有** | `m6-level2-retest4.md:40`、`:98` |
| M6 对照 A **21/60**、B **21/60** | 29 | **正文无**（仅附录 281） | **仅一侧有** | `m6-level2-retest4.md:36-37` |
| M6 单轮先达线的那次复测（16/20） | 32-33 | 无 | 仅一侧有 | `docs/benchmarks/m6-level2-retest2.md`；A 的指针指向它，B 未提。不冲突 |
| 窄验证第 2 轮 **2/6**（确定性子集 **2/5**） | 36 | 116、231、284-285 | 一致 | `m6-level2-narrow-verify2.md:59-60`（判定 `:61`） |
| 窄验证第 3 轮 **3/6**（确定性子集 **3/5**） | 38 | 117、232、286-287 | 一致 | `m6-level2-narrow-verify3.md:59-60`（判定 `:61`） |
| 窄验证第 1 轮 **4/6** / **410,256 tokens** / 53 of 54 traces | **无**（只写「Two further narrow verification rounds」） | **118-120、288** | **仅一侧有** | `m6-level2-narrow-verify-incomplete.md:17、31-33` |
| 窄验证 token **380,881**（第 3 轮）/ **420,826**（第 2 轮） | 无 | 无 | 两侧均无 | `m6-level2-narrow-verify3.md:71`、`m6-level2-narrow-verify2.md:71`。两侧都没写，**不构成不一致**；如要补，两边同时补 |
| 窄验证闸 **≥4/6** 与 **≥3/5** | 37 | 117 | 一致 | `m6-level2-narrow-verify2.md:61`、`m6-level2-narrow-verify3.md:61` |
| M8 公共契约 **46/46**（**26 REST + 6 MCP + 14 CLI**） | 56-57 | 96-97、172、238 | 一致 | `docs/architecture/public-contracts.md:351`（26/26）、`:381`（6/6）、`:395`（14/14）；`docs/reports/v1.0.0-release-runbook.md:98` 同写 |
| MCP 工具 **10 → 11** | 119-120 | 196-197、303 | 一致 | 两侧同写新增 `find_resource_declarations`、原十个不变 |
| 退出码 **6**（`EXIT_NO_INDEX`） | 63、92、108-115 | 99、137、186-192、301 | 一致 | `docs/architecture/public-contracts.md:54`、`src/dexatlas/cli/main.py:135`（`EXIT_NO_INDEX = 6`） |
| agent 默认预算 **120,000 tokens / 16 迭代 / 120 s / 40 步**（原 20,000 / 8 / 120 s / 12） | 121-125 | 198-202、245、304 | 一致 | 两侧同给旧值与新值 |
| 测试数 **1584**（1437 快 + 147 集成） | **无** | 157-158、236、262-264 | **仅一侧有** | `docs/reports/phase1-execution-report.md:76`、`:877`（HEAD 版本，非共享树污染版） |
| 一方覆盖率 **93.2%**（**7109/7631**） | **无** | 160、237、265 | **仅一侧有** | `docs/reports/phase1-execution-report.md:77` |
| 自建样例 APK **5** 个 | 68-69 | 74-75、178-180 | 一致 | `docs/reports/phase1-execution-report.md:81` |

### 2.1 retest3 / retest4 混淆专项核查（任务点名项）

仓库里有**两次**三轮完整复测，合计都是 49/60 = 81.7%：

| 批次 | 逐轮 | 合计 | token | 出处 |
|---|---|---|---|---|
| retest3 | **17 / 15 / 17** | 49/60 = 81.7% | **1,080,116** | `docs/benchmarks/m6-level2-retest3.md:29-31、39、41、101` |
| retest4 | **15 / 16 / 18** | 49/60 = 81.7% | **1,182,356** | `docs/benchmarks/m6-level2-retest4.md:28-30、38、83、98` |

**两份发布文本都只引用 retest4，且逐轮数与 token 数都挂对了**：

- A：`docs/releases/v1.0.0.md:27-31` → 49/60 = 81.7%、15/16/18、1,182,356 tokens，指向
  `../benchmarks/m6-level2-retest4.md` ✓
- B：`v1.0.0-github-release-body.md:112-113` → 49/60 = 81.7%、15/20 / 16/20 / 18/20 ✓；
  附录 `:276-282` 的出处全部指向 `m6-level2-retest4.md` ✓
- 中文摘要 `:229-230` → 逐轮 15/20、16/20、18/20，r2、r3 达单轮线，r1 未达 ✓

**⇒ 逐轮数没有挂错。** 但 A 的因果句仍留了一个歧义（详见 §7 U8）：「After the failure-mode
analysis and five root-cause fixes …（15/16/18 per round）」把「五项根因修复」（发生在 retest2 /
retest3 之前）与 retest4 的逐轮分布绑在同一句里，而同为 49/60 的 retest3 逐轮是 17/15/17。

---

## 3. 「不包含什么」逐条对照

| A 的条目（`docs/releases/v1.0.0.md`） | 行 | B 的对应条目（`v1.0.0-github-release-body.md`） | 行 | 覆盖情况 |
|---|---|---|---|---|
| 不宣称 agent 达到服务验收线：首测 40.0%、复测 81.7%（49/60），M6 仍未收口 | 74-77 | Known limitations 第 1 条：「M6 level 2 did not reach the acceptance line … **Verdict: not met.**」 | 109-114 | ⚠️ **B 缺首测 40.0%**（见 §7 U3）；其余覆盖 |
| agent 的回答始终是 **leads**，不是已验证发现 | 78-79 | 「An agent's answer is a lead, never a verified finding.」 | 128-130 | ✓ 覆盖 |
| 不含原生/动态分析（Ghidra / Rizin 仅以环境变量接入） | 80-81 | 「no native or dynamic analysis (Ghidra and Rizin are wired in as environment variables only; `DEXATLAS_GHIDRA_PATH`/`DEXATLAS_RIZIN_PATH` are reserved and unread)」 | 143-144 | ✓ 覆盖（两侧都点名了两个环境变量，逐字等价） |
| 不含插件生态（超出工具注册表） | 82 | 「no plugin ecosystem beyond the tool registry」 | 144-145 | ✓ 覆盖 |
| 未发布 Upwork 服务页 | 83 | 「no published service page」；M9 条另写「The Upwork materials remain unpublished drafts.」 | 145、102 | ✓ 语义覆盖（B 首处省了「Upwork」限定，M9 条补回） |
| 无 macOS 验证（Windows/Linux 为受测平台） | 83 | 「no macOS verification (Windows and Linux are the tested platforms)」 | 145-146 | ✓ 逐字一致 |
| 不是安全审计 / 渗透测试 / 恶意软件判定 / 加壳绕过 | 85-86 | 「not a security audit, a penetration test, a malware verdict or a packer bypass」 | 146-147 | ✓ 覆盖（B 省了「obfuscation」，非冲突） |
| 本次发布不含二进制制品（PyPI / 签名 tag / Release 制品由发布流水线产出） | **无** | 「The release contains no binary. The PyPI publication, the signed tag and the Release artefact are produced by the release pipeline, not by this document.」 | 109-110 | ⚠️ **仅 B 有**（见 §7 U5） |
| M10 独立验收尚未开始 | **无** | 「**Independent acceptance has not started.** The M10 acceptance package is drafted and self-checked, but no independent reviewer has run it. Nothing in this document should be read as a completed acceptance.」 | 148-150 | ⚠️ **仅 B 有**（见 §7 U1，最严重） |
| 后端全败仍可能记 `completed`（Apktool 可能先写下 manifest） | 90-95 | 同义条目 | 135-139 | ✓ 覆盖 |
| 层级 2 边界窄（单模型、温度 0、一方小 APK、封闭题集）；A/B 与 DexAtlas 预算不同，差异不是模型质量结论 | 96-101 | 「The level-2 boundary is narrow by construction … The comparison configurations A and B ran under different budgets, so the difference between them is not a model-quality claim.」 | 131-134 | ✓ 覆盖（B 多保留警告，但 B 正文没给 A/B 的对照数字 → §7 U7） |
| 混淆样例只覆盖短类名/方法名，不是控制流混淆、不是商业加壳器 | 102-104 | 「The samples under `examples/` include a hand-written obfuscated app. It covers short class/method names — not control-flow obfuscation and not commercial packers.」 | 140-142 | ✓ 覆盖 |

**结论**：任务点名的 6 项「不包含什么」中，**5 项两侧都在**，**1 项（M10 独立验收尚未开始）只在
B 侧**；另有 1 项（B 侧的「不含二进制制品」）只在 B 侧。两项都属于「一边漏写」。

---

## 4. 升级说明对照（v0.2.0 → v1.0.0）

| 主题 | A：`docs/releases/v1.0.0.md:行` | B：`v1.0.0-github-release-body.md:行` | 一致？ | 与 `docs/install.md` 是否一致 |
|---|---|---|---|---|
| 新增退出码 **6**（`EXIT_NO_INDEX`）：分析跑完但无可用代码索引；0–5 语义未变（5 号 `EXIT_TRUNCATED` v0.2.0 已有）；0 的外延收窄，非零即失败的脚本须显式判 `exit_code == 6`，把 0 当「完全成功」的调用方须改判 `exit_code in (0, 6)` 或 `summary.index_complete`；报告 / manifest / `schema_version` 未变 | 108-115 | 186-192 | ✓ 逐项一致（A 写「0's extension narrows」，B 写「0's meaning narrows」，语义相同） | ✓ `docs/install.md:226`、`:234-240` 同写 |
| `--workspace`/`-w` 到**每个**读/写命令（v0.2.0 只有 `analyze` 接受）；指向不存在目录的查询退出 **2**，不创建空工作区 | 116-118 | 193-195 | ✓ 一致 | ✓ `docs/install.md:67-71` 同写 |
| MCP 工具 **10 → 11**（新增 `find_resource_declarations`），原十个不变 | 119-120 | 196-197 | ✓ 一致 | — |
| agent 默认预算提到 **120,000 tokens / 16 迭代 / 120 s**，计划上限 **40 步**（原 20,000 / 8 / 120 s / 12）；四个 `DEXATLAS_AGENT_*` 覆盖项不变；agent JSON 报告新增 `convergence` 对象、Markdown 报告新增「How the task converged」一节 | 121-125 | 198-202 | ✓ 一致 | — |
| 新增 `analyze --html` 离线单文件报告与 `dexatlas export` 最小证据包；`schema_version=3` / `schema_version=1` 未变 | 126-129 | 203-205 | ✓ 一致 | — |
| 修复：API 服务的报告不再丢 APK 归档事实（hash 与 size）；重复分析不再让 CLI 报告的 `created_at` 漂离存储行；`androguard:AndroidManifest.xml` 的 provenance 重新可解析 | 129-132 | 206-209 | ✓ 一致 | — |
| 安装：**`uv sync --extra dev --extra analysis --extra mcp --extra demo`**（走 lockfile；v0.2.0 文档写的是 `uv pip install -e ".[analysis]"`） | 133-134 | 210-212 | ✓ 一致 | ✓ 完全一致 —— `docs/install.md:25` 就是这一行，且 `:19` 写明「all four extras, installed from the lockfile」；`docs/install.md:28-33` 的 extras 表列的正是 `analysis`/`mcp`/`demo`/`dev` 四项 |
| B 额外加「See docs/install.md」 | — | 211-212 | 仅 B 有 | ✓ 指向的确实是该文档 |

**结论**：升级说明两侧一致，且与 `docs/install.md` 的实际内容一致，无需改动。

---

## 5. 出处可回溯抽查（附录 `v1.0.0-github-release-body.md:251-318`）

抽查方式：按附录给出的 `file:line` 回到源文件，用 `git show <commit>:<file> | sed -n '<line>p'`
逐条读出该行原文，核对它是否真的写着所声称的数字/事实。附录共 40 条出处，全部核过。

| 附录条目 | 附录行 | 引用 | 核对结果 |
|---|---|---|---|
| 1584 tests | 262 | `phase1-execution-report.md:76` | ✅ |
| 1437 fast + 147 integration | 263 | 同 `:76`（另 `:144`–`:146`） | ✅ |
| 1584 passed + 0 xfailed + 0 skipped | 264 | `:878` | ✅ |
| Coverage 93.2%（7109 / 7631 lines） | 265 | `:77`（另 `:877`） | ✅ |
| Source fingerprint `sha256:ccea379b…` | 266 | `:1083` | ✅ |
| Five first-party sample APKs | 267 | `:81` | ✅ |
| 两个第三方集成样例：由 `scripts/fetch-fixtures.sh` 拉取、不入库 | 268 | `:847`；`fetch-fixtures.sh:12`, `:45`–`:48` | ✅ |
| 测量 commit `277d0fa`（引述其提交信息正文） | 269 | `git log 277d0fa` | ✅ 提交正文确写「完整测量在最终树刷新：指纹 ccea379b…，suite 1584 passed / 0 failed，覆盖率 93.2%」 |
| 指纹覆盖 src + tests + `pyproject.toml` + 测量脚本，不含文档 | 270 | `refresh-report-figures.py:110`, `:487`–`:506` | ✅ |
| 验收线：每轮 ≥16/20、三轮 ≥54/60（≥90%） | 276 | `m6-level2-retest4.md:3` | ✅ 该行写明「每轮 ≥16/20，三轮合计 ≥54/60」 |
| r1 15/20, r2 16/20, r3 18/20 | 277 | `retest4.md:28`, `:29`, `:30` | ✅ |
| 逐轮判定（r1 未达；r2、r3 达） | 278 | `retest4.md:82` | ✅ `r1 15/20 = 75.0%（未达 ≥16/20）；r2 16/20 = 80.0%（达到）；r3 18/20 = 90.0%（达到）` |
| 三轮合计 49/60 = 81.7% | 279 | `retest4.md:38`（判定 `:83`） | ✅ `:38` = `\| DexAtlas \| 49/60 \| 81.7% \|`；`:83` = `未达 ≥54/60（≥90%）` |
| 判定「未达标」 | 280 | `retest4.md:85` | ✅ `**总结论：未达标。**` |
| 对照配置 A 21/60、B 21/60 | 281 | `retest4.md:36`, `:37` | ✅ `:36` = `\| A \| 21/60 \| 35.0% \|`；`:37` = `\| B \| 21/60 \| 35.0% \|` |
| 1,182,356 tokens | 282 | `retest4.md:40`（另 `:98`） | ✅ `:40` = `三轮全部 trace 合计 token：**1182356**`；`:98` 同数 |
| 测量代码状态 `f9d9fd8` | 283 | `retest4.md:20` | ✅ |
| 窄验证第 2 轮 2/6、确定性子集 2/5 | 284 | `narrow-verify2.md:59`, `:60` | ✅ |
| 窄验证第 2 轮判定 | 285 | `narrow-verify2.md:61` | ✅ |
| 窄验证第 3 轮 3/6、确定性子集 3/5 | 286 | `narrow-verify3.md:59`, `:60` | ✅ |
| 窄验证第 3 轮判定 | 287 | `narrow-verify3.md:61` | ✅ |
| 窄验证第 1 轮 4/6、410,256 tokens、53 of 54 | 288 | `narrow-verify-incomplete.md:17`, `:31`–`:33`；`status.md:30`–`:31` | ✅ 四行分别写 410,256 tokens、4/6、4/5、`MET on the captured rounds … not a 54-trace verdict` |
| 首测 24/60 = 40.0% | 289 | `m6-level2-real.md:29`（另 `releases/v1.0.0.md:23`–`:24`） | ✅ `\| DexAtlas \| 9/20 \| 8/20 \| 7/20 \| 24/60 \| 40.0% \|` |
| 层级 0 确定性判分 20/20 | 290 | `service-regression-set.md:173` | ✅ |
| 层级 1 是替身模型、不是能力基线 | 291 | `status.md:133` | ✅ |
| M6 未收口、B1 未关闭、转方案 3（现状披露） | 292 | `status.md:37`–`:44`, `:133` | ✅ |
| 三轮合计 49/60 = 81.7%，仍未达 B1 验收线 | 293 | `status.md:37`–`:38` | ✅ |
| 46/46 | 299 | `releases/v1.0.0.md:56`–`:58`；`runbook:98` | ✅ |
| REST / MCP / CLI | 300 | `public-contracts.md:351`, `:381`, `:395` | ✅ 三行分别写「26/26 通过」「6/6 通过」「14/14 通过」 |
| 退出码 6 `EXIT_NO_INDEX` | 301 | `releases:108`–`:115`；`public-contracts.md:54` | ✅ |
| `--workspace` 全命令 | 302 | `releases:116`–`:118` | ✅ |
| MCP 10 → 11 | 303 | `releases:119`–`:120` | ✅ |
| agent 默认预算 | 304 | `releases:121`–`:122` | ✅ |
| `--html` 与 `export` | 305 | `releases:126`–`:128` | ✅ |
| 安装 extras | 306 | `releases:133`–`:134` | ✅ |
| 案例附件 9 个文件 | 307 | `CHANGELOG.md:264`–`:272` | ✅ |
| 5 个一方样例 APK | 308 | `CHANGELOG.md:299`–`:307` | ✅ |
| 预算效率四项修复 + 行裁剪 | 314 | `CHANGELOG.md:73`–`:79` | ✅ 逐行读过，四项修复与三层行裁剪都在 |
| M-1/L-1 两处审查遗留 + 9 项红→绿回归 | 315 | `CHANGELOG.md:17`–`:33` | ✅ `:33` = 「（`tests/test_review_fixes.py`，9 项）」 |
| 发版草案 / runbook / checklist / dry-run | 316 | `CHANGELOG.md:273`–`:279` | ✅ |
| 文档同步（README/status/roadmap/install） | 317 | `CHANGELOG.md:299`–`:307` | ✅ |
| M10 验收包 | 318 | `CHANGELOG.md:287`–`:298`；`status.md:3`, `:13` | ✅ |

**结论**：附录 40 条出处**逐条核对，全部命中**，未发现一处「引用的行不写着那个数字」，
也未发现 off-by-one。

---

## 6. 中英文口径等价性

| 事实 | 中文摘要（`:214-247`） | 英文正文 | 等价？ |
|---|---|---|---|
| M6 承诺范围 | 「有界、证据可核查的 **agent 演练**」 | 「a **bounded, evidence-checkable agent walkthrough** over the frozen set」 | ✅ 限定词（bounded / evidence-checkable）在两语种里都保住了，没有被写成「agent 通过了 X%」 |
| agent 答案的性质 | 「**agent 的答案始终是待核线索，不是已验证发现**」 | 「An agent's answer is a **lead, never a verified finding**」 | ✅ |
| M6 验收线 | 「每轮 ≥16/20、三轮合计 ≥54/60（≥90%）」 | 「≥16/20 per round and ≥54/60 (≥90%) over three rounds」 | ✅ |
| 三轮复测结果 | 「49/60 = 81.7%（逐轮 15/20、16/20、18/20），r2、r3 达到单轮线，r1 未达，合计未达 ≥90% 线——判定是「未达标」」 | 「49/60 = 81.7% (15/20, 16/20, 18/20 per round): r2 and r3 met the per-round line, r1 did not … **Verdict: not met.**」 | ✅ |
| 窄验证结果 | 「两轮窄验证同样未达闸：二轮转通过 2/6（确定性子集 2/5），三轮转通过 3/6（确定性子集 3/5），门槛是 ≥4/6 与 ≥3/5」 | 「The **two** narrow verification rounds … round 2 converted 2/6 … round 3 converted 3/6 … against gates of ≥4/6 and ≥3/5」 | ✅ 数字一致 |
| 停止决策 | 「**连续三轮未达后按方案 3（现状披露）停止追加投入**」 | 「When the narrow verification missed its gate, the plan's stop condition applied and investment stopped for good.」+ 上一句「An earlier narrow round … **is not a verdict and is not counted as one.**」 | ❌ **不等价**，见 §7 U2：中文说「连续三轮」（把不完整的第一轮算进去），英文说「两轮」且明说第一轮「不计为判定」；中文点名「方案 3（现状披露）」，英文全篇没有对应的具名选项 |
| 独立验收 | 「M10 独立验收尚未开始」 | 「Independent acceptance has not started. The M10 acceptance package is drafted and self-checked, but no independent reviewer has run it.」 | ✅（但 A 侧完全没有，见 §7 U1） |
| 验证口径 | 「1584 个测试（1437 快 + 147 集成），完整环境下 1584 passed、0 xfailed、0 skipped；一方代码覆盖率 93.2%（7109/7631 行）」 | 同（`:157-160`） | ✅ |
| 测量批次 | 「这两个数字测自 commit `277d0fa`（源指纹 `sha256:ccea379b…`），后续只改文档的 `8868e30` 不影响指纹」 | 同（`:164-171`） | ✅ |
| 公共契约 | 「公共契约表 46/46（26 REST + 6 MCP + 14 CLI）」 | 同（`:172-173`） | ✅ |
| 升级：退出码 6 | 「新增退出码 6（`EXIT_NO_INDEX`，跑完但无可用代码索引；0–5 的含义不变，但 0 的外延收窄，自动化脚本请用 `exit_code in (0, 6)` 或 `summary.index_complete` 区分）」 | 同（`:186-192`） | ✅ |
| 升级：agent 预算 | 「agent 默认预算提到 120,000 tokens / 16 迭代 / 120 s / 40 步」 | 同（`:198-199`） | ✅ |
| 本轮交付：M-1/L-1 | 「代码审查遗留的两处边界修复（M-1 裁剪内容可追溯、L-1 宽页行裁剪补全，**带 9 项红→绿回归**）」 | 「Two review leftovers closed (M-1 / L-1) … **Nine red→green regression tests came with it.**」 | ✅（英文的「9」写成 Nine，数字一致；`CHANGELOG.md:33` 佐证） |
| 本轮交付：发版材料 | 「发版草案、runbook、检查表与本地 dry-run 报告」 | 「a written change list, a step-by-step runbook, a pre-flight checklist and a local dry-run report」 | ✅ |
| 本轮交付：文档同步 | 「README（英/中）、status、roadmap、install 的文档同步」 | 「The bilingual READMEs (English and 简体中文), the status page, the roadmap and the install guide」 | ✅ |
| 本轮交付：预算效率 | 「预算效率四项修复与行裁剪机制」 | 「Budget efficiency: four fixes plus a row-clipping mechanism」 | ✅ |

**结论**：16 组事实里 **15 组等价**；**唯一不等价的是「停止决策」那一行**（U2），且它同时缺一个英文具名项。

---

## 7. 必须统一的 N 处清单（N = 9）

> **本窗口只读，不替主线程改。** 下列每条给出：文件、行号、现状、建议改法、依据。
> 排序按「读者会得出不同结论」的风险从高到低。

### U1 ★最严重 —— 「M10 独立验收尚未开始」：B 有，A 完全没有

| | |
|---|---|
| 文件 / 行 | `docs/reports/v1.0.0-github-release-body.md:148-150`（英文）、`:234`（中文摘要） ↔ `docs/releases/v1.0.0.md` **全文无对应** |
| 现状 | B 写：「**Independent acceptance has not started.** The M10 acceptance package is drafted and self-checked, but no independent reviewer has run it. Nothing in this document should be read as a completed acceptance.」中文摘要写「M10 独立验收尚未开始」。A 的「What's in this release」只列 M5–M9（`:17-70`），全文不含「M10」，也不含「独立验收」四字；`accept` 一词仅出现在「≥90% acceptance bar」这一验收线语境（`:24`、`:44`） |
| 风险 | 随 tag 发布的那份发版说明把 v1.0.0 写成「Phase 3's portfolio-and-delivery milestone」（`:3`），逐条列 M5–M9，读者**看不到**「独立验收还没开始」这条最关键的边界 —— 两份同时面向读者的文本，一份说了、一份没说 |
| 建议改法 | **以 B 为准**，在 A 的 `## What this release does NOT include`（`:72-86`）末尾或 `## Known limitations`（`:88-104`）补一条：`M10 independent acceptance has not started — the acceptance package is drafted and self-checked, but no independent reviewer has run it. Nothing here is a completed acceptance.` |
| 依据 | `docs/status.md:3`、`:13`（「M10 独立验收尚未开始，`v1.0.0` 未发布」）；`docs/reports/m10-acceptance-pack.md`；B 附录 `:318` |

### U2 —— 中文摘要「连续三轮未达」与英文正文「两轮 + 第一轮不计为判定」不等价；「方案 3（现状披露）」无英文对应

| | |
|---|---|
| 文件 / 行 | `v1.0.0-github-release-body.md:232`（中文） ↔ `:115-121`（英文） |
| 现状 | 中文：「连续三轮未达后按**方案 3（现状披露）**停止追加投入」。英文：「The **two** narrow verification rounds … stayed below their gate as well」「An earlier narrow round had converted 4/6 … **it is not a verdict and is not counted as one.**」「When the narrow verification missed its gate, the plan's stop condition applied and investment stopped for good.」—— 英文既把判定轮数说成 2，又明说第一轮「不计为判定」，还从未出现「方案 3 / 现状披露」这个具名终局选项（英文只说「the system is fixed or the service promise is narrowed and restated」，`:122-124`） |
| 风险 | 同一篇文档的中文摘要与英文正文给出两种轮次印象（3 vs 2）；中文读者会以为「方案 3」是英文正文里也写明的既定选项，但英文正文里查无此项 |
| 建议改法 | 中文改为「连续三轮未达（其中第一轮运行不完整、**不计为判定**）后，按验收方案的**「现状披露」路径**（option 3）停止追加投入」；并在英文正文 `:121-124` 处补上具名项：把 `the plan's stop condition applied` 改成 `the plan's stop condition applied — the acceptance plan's option 3, status disclosure` |
| 依据 | `docs/status.md:38`、`:44`（「按验收方案停止投入，转方案 3（现状披露）」「连续三轮未达后…」）；`docs/benchmarks/m6-level2-narrow-verify-incomplete.md:33`；`docs/benchmarks/m6-level2-narrow-verify3.md:61`（"按 m6-verify3-plan §7 停止…按验收方案三选一定稿服务承诺范围"） |

### U3 —— 首测 24/60 = 40.0%（逐轮 45%/40%/35%）在 B 的可发布正文里完全缺失

| | |
|---|---|
| 文件 / 行 | `docs/releases/v1.0.0.md:23-24`、`:74-75` ↔ B 正文 **无**（只在附录 `:289`，而附录不贴进 Release） |
| 现状 | A 两处写明「scored **24/60 = 40.0% (45%/40%/35% per round)** against the ≥90% acceptance bar — not passed」与「the first three-round batch measured 40.0% against the ≥90% bar」。B 的 Known limitations（`:109-124`）与中文摘要（`:228-234`）都只写修复后的 49/60 = 81.7% |
| 风险 | GitHub Release 的读者只看到 81.7%，看不到起点 40.0%，「修复带来多少提升」这条线断了；两份文本给出的「不包含什么」因此不等价（A 说「首测 40.0%」，B 没说） |
| 建议改法 | **以 A 为准**，在 B 的 Known limitations 第 1 条（`:111` 之后）补一句：`The first batch scored 24/60 = 40.0% (45%/40%/35% per round) against the ≥90% bar; after the root-cause fixes the full three-round retest scored 49/60 = 81.7%.` 并在中文摘要 `:229` 前同样补出「首测 24/60 = 40.0%（逐轮 45%/40%/35%）」 |
| 依据 | `docs/benchmarks/m6-level2-real.md:29`；`docs/status.md:133` |

### U4 —— Licence 整节：A 有，B 全篇没有

| | |
|---|---|
| 文件 / 行 | `docs/releases/v1.0.0.md:136-139` ↔ B **无**（中文摘要 `:214-247` 亦无） |
| 现状 | A：「Apache-2.0. JADX, Apktool and Androguard are invoked as separate processes or libraries and are not redistributed as part of this project.」B 全文不含 `Apache`、`Licence`、`License` |
| 风险 | GitHub Release 正文是许可声明最常见的位置；缺这一节，读者在 License 页之外拿不到「第三方后端不随项目分发」这句 |
| 建议改法 | **以 A 为准**，在 B 的 `## Upgrade notes`（`:182-212`）之后加一节 `## Licence`：`Apache-2.0. JADX, Apktool and Androguard are invoked as separate processes or libraries and are not redistributed as part of this project.`；中文摘要末尾同步一句许可与第三方后端说明 |
| 依据 | `docs/releases/v1.0.0.md:136-139`；`docs/install.md:28-33`（extras 表说明后端为外部进程） |

### U5 —— 「本次发布不含二进制制品」：B 有，A 没有

| | |
|---|---|
| 文件 / 行 | `v1.0.0-github-release-body.md:109-110` ↔ `docs/releases/v1.0.0.md` **无** |
| 现状 | B：「The release contains no binary. The PyPI publication, the signed tag and the Release artefact are produced by the release pipeline, not by this document.」A 全文无此意 |
| 建议改法 | **以 B 为准**，在 A 的 `## What this release does NOT include`（`:72-86`）补一条：`No binary ships in this release — the PyPI publication, the signed tag and the Release artefact are produced by the release pipeline.` |
| 依据 | `docs/reports/v1.0.0-release-runbook.md`（发布动作由流水线执行，不在文档内） |

### U6 —— 窄验证第 1 轮 4/6 / 410,256 tokens / 53-of-54「不计为判定」：B 有，A 没有

| | |
|---|---|
| 文件 / 行 | `v1.0.0-github-release-body.md:118-120`（+ 附录 `:288`）↔ `docs/releases/v1.0.0.md:33-40`（只写「Two further narrow verification rounds」） |
| 现状 | A 用「Two further」指向一个**从未出现过**的第一轮，读者无从知道曾经有一轮在捕获到的轮次上达到 4/6（接近门槛 ≥4/6），也没有 token 与「不完整」的披露。B 把这一轮完整披露并明确「不是判定、不计入」 |
| 风险 | A 的「Two further」在读者眼里是一个悬空指代；B 的这处披露恰恰是本发布最诚实的一段，A 反而看不到 |
| 建议改法 | **以 B 为准**，在 A 的 M6 条目 `:33-40` 补一句（与 2/6、3/6 并列）：`An earlier narrow round had converted 4/6 on the rounds it captured, but its run stopped at 53 of 54 traces (410,256 tokens), so it is not a verdict and is not counted as one.` |
| 依据 | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:17`、`:31-33` |

### U7 —— M6 复测的 token 合计 1,182,356 与 A/B 对照 21/60：A 的正文有，B 的正文没有（只在不贴出的附录）

| | |
|---|---|
| 文件 / 行 | `docs/releases/v1.0.0.md:29-30` ↔ B 正文 **无**（附录 `:281-282`） |
| 现状 | A 写「(A 21/60, B 21/60; traces 1,182,356 tokens)」。B 的 Known limitations 保留了「A/B 与 DexAtlas 预算不同，差异不是模型质量结论」的警告（`:131-134`），**却不给 A/B 的对照数字**，读者拿不到可对照的量 |
| 建议改法 | **以 A 为准**，在 B 的 Known limitations 第 1 条补出量级：`… still below the three-round ≥90% bar (A 21/60, B 21/60; traces 1,182,356 tokens).`（若不想加 token，至少补 A/B 21/60，否则那条预算警告是悬空的） |
| 依据 | `docs/benchmarks/m6-level2-retest4.md:36-38`、`:98` |

### U8 —— 「五项根因修复 → 15/16/18」的因果句把两次同为 49/60 的三轮复测混在一句里

| | |
|---|---|
| 文件 / 行 | `docs/releases/v1.0.0.md:26-28` |
| 现状 | A：「After the failure-mode analysis and **five root-cause fixes**, the full three-round retest on the complete 20-question denominator scored **49/60 = 81.7% (15/16/18 per round)**」。事实是：五项根因修复（检索兜底、整字面量契约、枚举完整性、partial 豁免、no_manifest 闭合）发生在 retest2（单轮 16/20）之前；此后有**两次**三轮复测 —— retest3 = **17/15/17** = 49/60 = 81.7%（1,080,116 tokens）与 retest4 = **15/16/18** = 49/60 = 81.7%（1,182,356 tokens）。A 引的是 retest4，逐轮数与 token **没有挂错**，但这句因果把两次 49/60 挤进一句，读者容易把 17/15/17 读成 A 的数 |
| 风险 | 逐轮数本身正确；但这一句正是任务点名的 retest3/retest4 混淆点，距离「挂错」只差一次改写 |
| 建议改法 | 把因果句改为指向真正的前置修复，例如：`After the execution-layer fixes (four) and the C2 single-word fallback, the full three-round retest on the complete 20-question denominator scored 49/60 = 81.7% (15/16/18 per round …)`；若要保留「五项根因修复」，应把它挂在 retest2/retest3 上并写明那次是 17/15/17 |
| 依据 | `docs/benchmarks/m6-level2-retest4.md:5`、`:85`；`docs/benchmarks/m6-level2-retest3.md:29-31`、`:39`、`:41`、`:101`；`docs/benchmarks/m6-level2-retest2.md:5`；`docs/status.md:37-38`、`:133`；`docs/reports/v1.0.0-release-runbook.md:79-82`（同句式，建议一并改） |

### U9 —— 验证数字只在一侧；且需与主线重跑的完整测量同批次刷新

| | |
|---|---|
| 文件 / 行 | B `:157-160`、`:236-237`、`:262-269` ↔ A **无** |
| 现状 | B 给出 1584（1437 快 + 147 集成）、一方覆盖率 93.2%（7109/7631），并声明测自 commit `277d0fa`、指纹 `sha256:ccea379b…`（该声明已核实为真，见 §0.2）。A 全文没有任何验证数字 |
| 风险 | 两份面向读者的文本，一份承诺了可验证的测试与覆盖率口径，另一份没有 —— 读者若交叉比对会看到两个口径。**另外**：主线正在重跑完整测量，若新测得值与 1584 / 93.2% 不同，B 的这组数字与 `docs/reports/phase1-execution-report.md` 必须同批次刷新（由 `scripts/refresh-report-figures.py` 生成，不得手改） |
| 建议改法 | 三步：(1) 等主线测量定稿后，确认 `phase1-execution-report.md` 的 `<!--fig:-->` 标记已由脚本刷新；(2) 若数字有变，同步改 B 的 `:157-160`、`:236-237`、附录 `:262-269`；(3) 视版面决定是否在 A 增加一个简短的验证小节（至少 1584 = 1437 + 147、93.2% = 7109/7631，并注明测自哪个 commit 与指纹）—— 若要加，**必须与主线同批次**，不能照抄当前值 |
| 依据 | `docs/reports/phase1-execution-report.md:76-77`、`:877`（HEAD 版本）；`scripts/refresh-report-figures.py:110`、`:487-506`；`tests/test_docs.py:687` |

---

## 8. 已核对且无问题的项（供主线程直接采信，不必再查）

1. **retest3 / retest4 未混淆**：两份文本的逐轮数与 token 都挂在 retest4 上且正确（详见 §2.1）。逐轮数 **没有** 挂错。
2. **附录 40 条出处逐条命中**，无一处「引用的行不写着那个数字」，也无 off-by-one（§5）。
3. **升级说明与 `docs/install.md` 完全一致**：四个 extras、`--workspace`/`-w`、退出码 6 与「0–5 语义不变」都对得上（§4）。
4. **共享工作树的 35.4% 是污染值，不是发布文本的值**：以 `git show HEAD:docs/reports/phase1-execution-report.md` 为准是 93.2%（7109/7631），与 B 一致（§0.1）。
5. **B 的测量声明属实**：`277d0fa` 与 `8868e30` 均为 `78102a8` 祖先，`8868e30` 只改 `docs/`，不动指纹覆盖的 `src/`、`tests/`、`pyproject.toml`、测量脚本；`277d0fa` 的提交正文确实逐字写着 B 引述的那段（§0.2）。
6. **16 组中英事实里 15 组等价**，唯一不等价是 U2 的停止决策那一行（§6）。
7. **没有一边多写、也没有一边漏写一整节**（除 Verification / Licence / 中文摘要 / Appendix 这几处归属差异外）：A 的 5 条「不包含什么」在 B 里逐条有对应，B 多出的 5 条 Known limitations 也都与 A 不冲突。

---

## 9. 贴出 GitHub Release 时的操作提醒（非一致性问题）

- B 的草稿注记（`:3-8`）与整个 `## Appendix`（`:251-318`）**都不贴进 Release**；实际发布体是
  `:10-249`（导语 + Highlights + Known limitations + Verification + Upgrade notes + 中文摘要）。
- 草稿注记 `:7-8` 已写明「不声称独立验收已发生 —— 它尚未开始」；贴出前若按 U1 改了 A，B 侧此句保持不变即可。
- `:174-177` 声明 M6 层级 2 数字「由脚本从已落盘 trace 重算」，`:164-171` 声明测量批次 —— 贴出前应确认这两段在主线重测后仍然成立。
