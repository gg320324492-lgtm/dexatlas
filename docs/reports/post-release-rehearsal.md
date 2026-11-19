# 发布后修正并重打 tag —— 路径演练记录（只读）

**状态：演练记录，不是发版记录。** 本轮**没有**打 tag、**没有**推任何东西、**没有**跑
`scripts/refresh-report-figures.py`、**没有**跑完整套件、**没有**改 CI、**没有**改任何
既有文件 —— 本文件是本轮**唯一新增**的文件。

- **日期**：2026-11-18
- **对象**：[v1.0.0-release-checklist.md](v1.0.0-release-checklist.md) §3 步骤 8
  （`docs/reports/v1.0.0-release-checklist.md:220`）—— 这条路径是这一轮才补上的，
  此前清单里一个字都没有
- **演练树**：`E:\Dexatlas\.claude\worktrees\vibrant-benz-e30712`，分支
  `claude/vibrant-benz-e30712`，HEAD `3e943b5`
- **基线**：GitHub 上 `v1.0.0` 的实际发布状态（已发布；tag 在 Release 发布之后被**重打过
  5 次**，每一次都让上一次的 CI 结论作废），以及 2026-11-17～18 这一轮真实的操作记录
  （[v1.0.0-ci-run-record.md](v1.0.0-ci-run-record.md)、
  [release-process-dry-run.md](release-process-dry-run.md)）
- **本轮的动作**：全部只读。命令的存在性用 `grep` 核，行为用读源码核；没有执行任何会
  产生副作用的命令，没有联网

---

## 0. 结论速览

| | |
|---|---|
| 核的动作 | §3 步骤 8 的**九个动作**（清单里写成 7 条「顺序不可换位」+ 4 条并列判据） |
| 写的演练条目 | **12 条**（§2，编号 R1–R12） |
| 其中「§3 步骤 8 本该拦住但没拦住」 | **8 条**（R1、R2、R3、R4、R5、R7、R10、R11） |
| 半是 | **1 条**（R6：门禁存在，但本地清单没列、路径里也没这一步） |
| 不属此类 | **3 条**（R8 清单已如实标出、R9 纯约定、R12 已核清无需动） |
| 判据含糊的动作 | **3 个**（第 1 个的触发条件、第 4 个的顺序、第 7 个的等待方式） |
| 建议补的判据 | **3 条**（§3） |

**一句话**：这条路径**写清楚了它该做什么，没写清楚它什么时候算做完**。九个动作里，
「改什么、怎么改」都具体；「什么时候必须做」「做到什么程度算做完了」「谁在等」三件事
全部缺判据。本轮踩的十几次坑，绝大多数落在后三件事上。

---

## 1. 九个动作逐条核

| # | 动作 | 清单写清楚了没有 | 判据含糊在哪 | 对应条目 |
|---|---|---|---|---|
| 1 | 改代码 | **半清楚** | 「**数字变了才需要**」重测量 —— 判据用的是「数字」，而项目真正的闸门是「**指纹**」。改 `src/` 一行注释，数字一个不变，指纹变了，报告已经作废 | R1、R2 |
| 2 | `ruff format` | **清楚** | 顺序写在第 1 条里（`改代码 → ruff format → 完整重测量`），与 CLAUDE.md「先格式化再测量」一致 | — |
| 3 | 完整重测量 | **清楚** | 前提条件（后端、fixtures、Pillow、ffmpeg、git tag）与独占要求都在 §3 步骤 3 里写全了 | R1、R2、R6 |
| 4 | 改文档里的数字与引用 | **不清楚** | 「按内容重锚，不按行号推算」是**方法**不是判据。**没写重锚要在重打 tag 之后** —— 引用检查器对 Release 正文读的是**本地 `v1.0.0` ref 指向的树**，tag 还没重打时它核的是旧树 | R3、R7 |
| 5 | 提交 | **清楚** | 「提交信息写清修正了什么」无机器判据（纯人工约定） | R9 |
| 6 | 重打 tag | **半清楚** | 命令写对了（`git tag -f -a` + `git push --force`）。但本地 `git tag -f` 与远端 `git push --force` 之间有窗口，而 §3 步骤 8 判据第 1 条查的是**本地** ref | R4、R5 |
| 7 | 等 CI 变绿 | **清楚但没法执行** | 写了「最新一条 run 的 headSha 必须等于新 commit」——判据是对的，**没写怎么等**：新 run 要几秒才出现在列表里；上一条 run 可能还在**跑**（不打断）或还在**排队**（被顶掉、0 个 job） | R5 |
| 8 | 重跑同源核对 | **半清楚** | §7 N6 说要核**四份**，但第四份（GitHub 上已发布的那一份）**没有任何东西比对**；仓库里的三份里，「测试数」这一批也有三处没人比 | R7、R8 |
| 9 | 必要时重发 Release 正文 | **不清楚** | 「正文变了：`gh release edit`」——「变了」由谁判定没有判据；改完「重新 diff 一遍」也没说 diff 的对象是谁 | R8、R10 |

**还有一条清单没写、但这一轮真的发生过的**：第 4 步之后回头改了 `src/`，第 3 步的测量当场
作废（见 R11）。清单没有「第 4 步之后不许再改 `src/`/`tests/`；要改就退回第 1 步重来」
这条回退规则。

---

## 2. 演练记录

每条六栏：**触发条件 → 现象 → 该在哪一步被拦住 → 现在的判据 → §3 步骤 8 本该拦住但没拦住？
→ 漏过的后果**。

---

### R1. 改了 `tests/` 之后源指纹变了，报告的数字作废

- **触发条件**：修正里含 `tests/` 下**任何** `.py` 的改动 —— 加一条回归测试也算。
- **现象**：报告里 `<!--fig:tests.total-->`、`<!--fig:suite.passed-->`、`<!--fig:suite.skipped-->`
  与两份 README 的徽章仍写着旧值；`docs/reports/phase1-execution-report.md` 的测量记录块里
  的 `source_fingerprint` 与当前树对不上。
- **该在哪一步被拦住**：**第 1 步之后、第 3 步之前**。
- **现在的判据**：`scripts/refresh-report-figures.py` 的 `fingerprint_files()`
  （`scripts/refresh-report-figures.py:908-931`）把 `src/` 与 `tests/` 下**全部 `.py`**，
  连同 `pyproject.toml` 与测量脚本一起哈希；`source_fingerprint()`
  （`scripts/refresh-report-figures.py:934-961`）算它。核对靠
  `tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code`
  （`tests/test_docs.py:725`）；「测试树进指纹」这条不变式由
  `tests/test_docs.py::test_the_fingerprint_covers_the_code_and_the_suite`
  （`tests/test_docs.py:857-888`）守着。
- **§3 步骤 8 本该拦住但没拦住？** **是**。第 1 条的触发条件写的是「**数字变了才需要**」
  重测量，而这里**数字确实变了**（多一条测试 = 多一个 passed）—— 真正含糊的是它的**兄弟
  条目 R2**。
- **漏过的后果**：报告与徽章描述的树不存在（CLAUDE.md 规则 3 的反面）。CI 的 `measurement`
  job（`.github/workflows/ci.yml:724`，**仅 tag 触发**，跑
  `refresh-report-figures.py --check`，`.github/workflows/ci.yml:771`）会红 —— 但那已经在
  重打 tag 的半路上了。

---

### R2. 改了 `src/` 但一个数字都没变，指纹照样变了

- **触发条件**：只改 `src/` 里的注释、docstring 或格式，测试数与覆盖率都没动。
- **现象**：数字**看起来全对**（测试数对、覆盖率对），但报告记录的指纹对不上当前树。
  报告里那一行 `source_fingerprint` 描述的是一棵已经不存在的树。
- **该在哪一步被拦住**：**第 1 步之后、第 3 步之前** —— 与 R1 同一处。
- **现在的判据**：与 R1 相同。指纹比对**不看数字**，它看内容哈希，所以这一类照样抓得到。
- **§3 步骤 8 本该拦住但没拦住？** **是**，而且这是 §3 步骤 8 第 1 条**措辞上最大的含糊**：
  「数字变了才需要」把这一整类放过了。项目真正的闸门是**指纹**，不是数字 ——
  `source_fingerprint()` 的 docstring 自己写着「**指纹让这件事不用重测量就看得见**」。
- **漏过的后果**：同 R1。更隐蔽的是：本地看起来毫无异样，因为**没有一个数是错的**。

---

### R3. tag 还没重打时，引用检查器按旧树核正文

- **触发条件**：第 4 步（改文档里的数字与引用）之后、第 6 步（重打 tag）之前跑
  `scripts/check-doc-citations.py`。
- **现象**：检查器的结论**与将要发布的那棵树无关**。
  `scripts/check-doc-citations.py:278-278` 的 `TREE_DOCUMENTS` 把
  `docs/reports/v1.0.0-github-release-body.md` 映射到 ref `v1.0.0`；`tree_of()`
  （`scripts/check-doc-citations.py:2150-2153`）按这个 ref 取树；本地 tag 还没动 →
  读的是**旧树**。于是：为新树写的行号被判「漂移」，或者旧的行号被判「对」。
  `check_declaration()`（`scripts/check-doc-citations.py:2173-2222`）还会把正文里引的测量
  指纹与**那棵树**的测量记录比对 —— 旧树的指纹，于是也判「不符」。
- **该在哪一步被拦住**：**第 4 步与第 6 步之间**。清单第 4 条只说了「按内容重锚」，没说
  重锚的**基准是本地 tag 还是远端 tag**，也没说重锚完要**在 tag 移过之后再核一次**。
- **现在的判据**：机制是齐的 —— `TREE_DOCUMENTS` + `Tree` + `tree_fingerprint()`
  （`scripts/check-doc-citations.py:2156-2159`）+ `check_declaration()`；
  `tests/test_doc_citations.py::test_the_release_body_is_read_out_of_the_release_tree`
  （`tests/test_doc_citations.py:687-701`）守住「Release 正文必须是从 release 树里读出来的」。
  **缺的只是清单里的顺序要求**。
- **§3 步骤 8 本该拦住但没拦住？** **是**。
- **漏过的后果**：Release 正文里的行号与指纹全部指向一棵不存在的树。这一轮真的发生过 ——
  CI run `44126427363` 红的原因之一就是
  「`v1.0.0-github-release-body.md` 引用了 `sha256:4e72ac49`，而树的是
  `sha256:975afa8e…`」（[v1.0.0-ci-run-record.md](v1.0.0-ci-run-record.md)）。

---

### R4. 本地 tag 已重打，远端 tag 还没推

- **触发条件**：`git tag -f -a v1.0.0 <新 commit>` 执行之后、`git push --force origin v1.0.0`
  之前。
- **现象**：本地 `git rev-parse v1.0.0^{commit}` 已经是新 commit，§3 步骤 8 判据第 1 条
  （`docs/reports/v1.0.0-release-checklist.md:239`）「`git rev-parse v1.0.0^{commit}` ==
  `origin/main`」**成立**。但 GitHub 上已发布的 tag 仍指向旧 commit，Release 页上显示的
  正文仍是旧的。判据在这个窗口里给出「已发布的内容已经是新的」的**假象**。
- **该在哪一步被拦住**：**第 6 步内部** —— `git tag -f` 与 `git push --force` 之间。
- **现在的判据**：§3 步骤 8 判据第 1 条**只查本地 ref**。已发布的那一份是**远端**的 tag，
  查法是 `git ls-remote origin 'refs/tags/v1.0.0^{}'`（annotated tag 要用 `^{}` 剥到
  commit —— §3 步骤 4 写明 tag 是 annotated 的）。这一条**现在仓库里没有**。
- **§3 步骤 8 本该拦住但没拦住？** **是**。
- **漏过的后果**：第 8 步的四份同源核对里，**第四份**（GitHub 上已发布的那一份）核的是旧
  正文，而这一份恰恰是读者唯一能直接看到的。

---

### R5. 推 tag 与 CI checkout 的竞态

- **触发条件**：`git push --force origin v1.0.0` 之后**立刻**查 CI。
- **现象**：两种都真实发生过 ——
  （a）**新 run 还没出现在列表里**：`gh run list --branch v1.0.0 --limit 1` 返回的还是上一条
  （旧 `headSha`、结论 `success`）。只看结论会**误判通过**。
  （b）**上一条 run 还在排队**：被新 run 顶掉，conclusion 是 `cancelled`、**0 个 job**，
  看起来像失败，其实它连门禁都没跑。
  另外（c）上一条 run **已经在跑**：不会被���断（见下），它会继续跑完，结论是关于**旧树**的
  —— 列表里于是有两条 run 指向同一个 `v1.0.0`。
- **该在哪一步被拦住**：**第 7 步**。
- **现在的判据**：`.github/workflows/ci.yml:23-32` 的 concurrency 组是
  `${{ github.workflow }}-${{ github.ref }}`，`cancel-in-progress: false` ——
  **已开始的 run 不被打断**，只排队的被新 run 替换。清单判据第 2 条
  （`docs/reports/v1.0.0-release-checklist.md:240`）要求
  「最新一条 run 的 conclusion == success **且** headSha == 上述 commit」——
  `headSha` 这半条**正是防住 (a) 的那半条**，判据本身是对的；**缺的只是怎么等到那条 run
  出现**，以及「`cancelled` 不算结论、`pending` 不算结论」。
- **§3 步骤 8 本该拦住但没拦住？** **是**（判据对，但不可执行）。
- **漏过的后果**：把上一条 run 的 `success` 当成本次的结论 → 发布一棵没验过的树。
  这一轮 CI run 记录里的第 4 次重打（run `44126696597`）就是 **0 个 job 的 `cancelled`**。

---

### R6. 测量脚本不重画卡片，数字改了卡片就静默过期

- **触发条件**：第 3 步（完整重测量）之后，数字变了。
- **现象**：`.github/social-preview.png` 与 `.github/social-preview-zh.png` 两张卡片上的数
  （覆盖率、测试数、公共契约检查项数）还是旧的，而报告与徽章已经是新的。卡片是 PNG，
  `git diff` 看不出它过期。
- **该在哪一步被拦住**：**第 3 步之后、第 9 步之前**。§3 步骤 8 的九个动作里**从头到尾
  没有「重画卡片」这一步**。
- **现在的判据**：`tests/test_social_preview.py::test_the_cards_are_current`
  （`tests/test_social_preview.py:114-120`）与 CI 的 `social-preview` job
  （`.github/workflows/ci.yml:696`，跑 `scripts/make-social-preview.py --check`，
  `.github/workflows/ci.yml:717`）**能抓住**。但：
  （i）`scripts/refresh-report-figures.py` 里 `preview` 一词 **0 命中** —— 测量脚本
  **不画卡**，画卡是 `scripts/make-social-preview.py` 的活；
  （ii）§3 步骤 2 的**本地**门禁清单里**没有** `make-social-preview.py --check`。
- **§3 步骤 8 本该拦住但没拦住？** **半是**。门禁是有的（pytest + CI job），
  但**本地清单没列、重打 tag 的路径里也没有这一步**。
- **漏过的后果**：本地全绿、卡片过期；要等推 tag 之后 CI 的 `social-preview` job 才发现 ——
  那时已经走了半个重打 tag 的流程，又要多一轮。

---

### R7. 同一批数字散落在多处手抄的位置，漏改

- **触发条件**：数字变了。
- **现象**：同一个「1694 passed / 1 skipped」在仓库里**手抄**了 4 处，其中**3 处没有任何
  门禁在比**。
- **该在哪一步被拦住**：**第 4 步**（改文档里的数字与引用）。
- **现在的判据**（逐处核过）：

  | 位置 | 有没有东西在比 | 比的是什么 |
  |---|---|---|
  | `docs/reports/phase1-execution-report.md` | **有** | `<!--fig:...-->` 标记，由测量脚本写 |
  | `README.md:12` / `README.zh-CN.md:12` 徽章 URL | **有** | 徽章由测量脚本写；`tests/test_docs.py::test_the_readme_badge_states_the_measured_numbers`（`tests/test_docs.py:1382`） |
  | `.github/social-preview*.png` 两张卡片 | **有** | `scripts/make-social-preview.py --check`（CI job + pytest） |
  | `docs/status.md:24` 覆盖率 | **有** | `<!--fig:coverage.pct-->` 标记 |
  | `docs/how-to-verify.md:172`、`docs/how-to-verify.zh-CN.md:149` | **无** | `tests/test_how_to_verify.py` 比的是该页的 **collect 汇总数**（总数/快测/集成，见 `tests/test_how_to_verify.py:114-132`），**不比对这一行的 passed/skipped** |
  | `docs/releases/v1.0.0.md:95` | **无** | `scripts/check-version-claims.py` 的 `release_documents()`（`scripts/check-version-claims.py:976-996`）把发版说明纳入检查，但 `expected["tests.total"]` 取自 `history.<tag>.tests`（`scripts/check-version-claims.py:1275`），而 `HISTORY_TAGS`（`scripts/refresh-report-figures.py:229`）只有 `v0.1.0`–`v0.1.3`，**不含 v1.0.0** → 这个数**没有可比的测量**，规则跳过 |
  | `docs/reports/v1.0.0-github-release-body.md:168`、`:175`、`:267`、`:299`、`:304` | **部分** | 测量**指纹**被 `check-declaration` 比对；**测试数没有** |
  | GitHub 上已发布的那一份正文 | **无** | 不在仓库里 |

- **§3 步骤 8 本该拦住但没拦住？** **是**。§7 N6
  （`docs/reports/v1.0.0-release-checklist.md:463`）要求人工核四份，但**没指出哪几份其实
  一个数都没有机器在比** —— 于是人工核对成了唯一的兜底，而人工会漏。
- **漏过的后果**：读者直接读到错的数。这一轮**最后一次**修正就是这一类：commit `3e943b5`
  「发布文本里的 passed 数改成落定值 1694」—— 正文里同时有「1695 个测试」（收集总数）和
  「1694 passed」（通过数），改正文时把总数当成了通过数。

---

### R8. 第四份对外文本（GitHub 上已发布的那一份）没有任何东西比对

- **触发条件**：第 9 步重发 Release 正文之后（或没重发）。
- **现象**：仓库里的三份改了，GitHub 页面上那一份没改，或改错了，**没有任何告警**。
- **该在哪一步被拦住**：**第 8 步**（重跑同源核对）。
- **现在的判据**：`gh release view v1.0.0` 取页面正文，与仓库里的正文文件 `diff` 一遍
  —— **纯人工**。§7 N6 已经**如实标出**「第四份不在仓库里，没有任何东西比对它」。
- **§3 步骤 8 本该拦住但没拦住？** **否** —— 清单已经如实标出这是人工项。**但** §3 步骤 8
  的判据第 4 条（`docs/reports/v1.0.0-release-checklist.md:242`）把它写成了一条与其它三条
  并列的「判据」，读起来像同性质 —— 它其实是「一条要人去执行的检查」。
- **漏过的后果**：已发布的正文与仓库不一致 —— 而那一份是读者唯一能直接看到的。

---

### R9. 「提交信息写清修正了什么」没有判据

- **触发条件**：第 5 步（提交）。
- **现象**：无法机器判定。commit message 里写没写「修正了什么」，只有人读得出来。
- **现在的判据**：无 —— 纯约定。
- **§3 步骤 8 本该拦住但没拦住？** **不属此类**（这一条本来就不可能有机器判据）。
- **漏过的后果**：读者/后续维护者看不出「这棵树为什么和 tag 指向的那棵不一样」。属于
  可读性损失，不属于正确性损失。

---

### R10. 「必要时重发 Release 正文」的「变了」没有判据

- **触发条件**：第 9 步。
- **现象**：第 4 步改了正文文件，第 9 步没重发 → GitHub 页面上还是旧正文；或者重发了，
  但发的不是仓库里那份。
- **现在的判据**：`gh release edit v1.0.0 --notes-file .scratch/release-body.md`，然后
  「重新 diff 一遍」—— diff 的**对象**（仓库文件 vs 页面正文）没写出来，判定也靠人。
- **§3 步骤 8 本该拦住但没拦住？** **是**（措辞含糊）。
- **漏过的后果**：同 R8。

---

### R11. 第 4 步之后回头改了 `src/`，第 3 步的测量当场作废

- **触发条件**：第 4 步（改文档里的数字与引用）过程中发现还要改代码 → 回到第 1 步。
- **现象**：改了 `src/` 或 `tests/` → 指纹变了 → 第 3 步那次测量作废 → 报告与徽章要重写
  → 第 4 步刚改好的数字要再改一遍。
- **该在哪一步被拦住**：**第 4 步与第 5 步之间** —— 需要一条回退规则。
- **现在的判据**：`tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code`
  （`tests/test_docs.py:725`）会红 —— 它抓得住「测量作废」，但**清单里没有说这时该退回
  哪一步**。
- **§3 步骤 8 本该拦住但没拦住？** **是**。
- **漏过的后果**：两轮改数字（这一轮实际就发生过：数字从 1695 改成 1694 之后又发现卡片
  也要重画，见 R6）。

---

### R12. 重打 tag 不改 `history.*.tests` —— 已核清，**不是坑**

- **触发条件**：重打 `v1.0.0`。
- **现象**：报告里的历史数字（`v0.1.0` 204 / `v0.1.1` 244 / `v0.1.2` 275 / `v0.1.3` 444）
  **不随重打变化**。原因是 `HISTORY_TAGS`（`scripts/refresh-report-figures.py:229`）只列了
  `v0.1.0`–`v0.1.3`，**不含 `v1.0.0`**；而 `collected_at_tag()`
  （`scripts/refresh-report-figures.py:1044-1070`）用 `git archive <tag>` 量 tag 自己的树，
  量的是那个 tag 当时的样子。
- **现在的判据**：`HISTORY_TAGS` 本身就是判据；
  `tests/test_docs.py::test_execution_report_history_figures_match_the_released_tags`
  （`tests/test_docs.py:920`）守着这一列。
- **§3 步骤 8 本该拦住但没拦住？** **不属此类**。
- **漏过的后果**：无。**记下来是为了让下一次演练不用再查一遍** —— 这条看起来像个坑，
  因为「重打 tag」和「报告里的历史数字」放在一起很自然会这么想。

---

## 3. 建议补的三条判据

三条都是**这一轮换来的**，每条写清「加在哪、怎么验」。

---

### 判据 A：把「要不要重测量」的触发条件从「数字变了」改成「**指纹变了**」

- **加在哪**：`docs/reports/v1.0.0-release-checklist.md:227`（§3 步骤 8 第 1 条），
  把「（数字变了才需要）」改成下面这句。
- **判据文本**：

  > 要不要重测量，看**指纹**，不看数字。指纹覆盖 `src/` 与 `tests/` 下的全部 `.py`、
  > `pyproject.toml` 和测量脚本本身 —— 收哪些文件由 `fingerprint_files()` 决定
  > （`scripts/refresh-report-figures.py:908-931`）——
  > **改 `tests/` 里的一条测试也算指纹变了**，哪怕测试数与覆盖率一个都没动。
  > 判据的权威定义就是这个函数，**不要另写一份**。

- **怎么验**（两条都能跑，任选其一作为机器判据）：

  ```bash
  git diff --name-only <base>..<new> -- src/ tests/ pyproject.toml scripts/refresh-report-figures.py
  ```

  非空 ⇒ **必须**完整重测量；空 ⇒ 不用。

  或者直接用现成的那道门禁（它红就是指纹对不上）：

  ```bash
  uv run --no-sync pytest tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code
  ```

- **红→绿演示**（按 CLAUDE.md 规则 1，判据也得能证伪）：改 `tests/` 下任意一个 `.py` 的
  一个字符（哪怕是注释），上面那条 `git diff` 必须非空；改 `docs/` 下的文件，它必须为空。
  这一条能同时证伪「数字变了才需要」那个旧措辞 —— 因为改注释时数字不变。

---

### 判据 B：把「本地 tag」和「已发布的 tag」分成两个查法，并要求引用检查**在 tag 移过之后**再跑

- **加在哪**：`docs/reports/v1.0.0-release-checklist.md:228`（§3 步骤 8 第 2 条）与
  `:239-240`（判据第 1、2 条）。
- **判据文本**：

  > **第 2 步与第 6 步之间有一个顺序要求**：引用检查器对
  > `docs/reports/v1.0.0-github-release-body.md` 读的是**本地 `v1.0.0` ref 指向的树**
  > （`scripts/check-doc-citations.py:273-273`、`:1387-1390`）。所以顺序是
  > **先重打本地 tag → 再跑 `check-doc-citations.py` → 若漂了则改正文 → 再提交 →
  > 再重打一次 tag → 再跑一次检查器**。在 tag 移过之前跑的那一次结论，与将发布的树无关。
  >
  > **本地与远端分开查**：`git rev-parse v1.0.0^{commit}` 查的是本地；
  > **已发布的那一份**是远端的 tag，用
  > `git ls-remote origin 'refs/tags/v1.0.0^{}'`（annotated tag 要用 `^{}` 剥到 commit）。
  > 两者不等 ⇒ 已发布的还是旧的。

- **怎么验**：

  ```bash
  git rev-parse v1.0.0^{commit}
  git ls-remote origin 'refs/tags/v1.0.0^{}'
  ```

  两个 commit 必须相等才算「tag 已经重打到位」。这一对命令是**纯读**的，可以在不推任何
  东西的情况下先跑一遍，确认本地与远端当前是否一致。

  引用检查的时机则按上面那段顺序走：**tag 移过之后**跑
  `uv run --no-sync python scripts/check-doc-citations.py`，读它的输出（drifted 与
  unresolved 都必须是 0）。

---

### 判据 C：把「同一批数字相等」写成**一份写下来的清单**，并让每一份副本都有东西在比

- **加在哪**：`docs/reports/v1.0.0-release-checklist.md:241`（§3 步骤 8 判据第 3 条），
  配合 §7 N6（`:463`）。
- **判据文本**：

  > 「四份对外文本的同一批数字集合相等」这句话里的「同一批数字」，**要写下来**，
  > 而且**每一份副本都要有东西在比**。本轮核完的现状是：
  >
  > | 数字 | 仓库内的副本 | 有没有东西在比 |
  > |---|---|---|
  > | 测试总数 / 快测 / 集成 | 报告（`<!--fig:-->`）、徽章 URL | 有（测量脚本 + pytest） |
  > | 覆盖率 | 报告、徽章、`docs/status.md` | 有 |
  > | 契约检查项数 | 六份材料 | 有（`tests/test_public_contracts.py`） |
  > | 卡片上的数 | 两张 PNG | 有（`make-social-preview.py --check`），但**本地门禁清单里没列** |
  > | **passed / skipped** | `docs/how-to-verify.md`、`.zh-CN.md`、`docs/releases/v1.0.0.md`、Release 正文 | **无** |
  > | **已发布的那一份正文** | 不在仓库里 | **无**（人工 `gh release view` + diff） |
  >
  > 补法：把 passed/skipped 这一批纳入某个只读检查（`scripts/check-version-claims.py`
  > 的 `OUTWARD_DIRECTORIES` 规则已经会查对外素材的测试数，扩到这几份发版文本即可），
  > 并把「已发布的那一份」的 diff 写成**一条命令**放进 §3 步骤 8 第 8 步。

- **怎么验**（红→绿，这是三条里唯一需要写新代码的）：
  1. 把 `docs/reports/phase1-execution-report.md` 里 `<!--fig:suite.passed-->` 的值改成
     一个别的数，跑新检查 —— 它必须**报出「哪一份文本的哪一行还是旧数」**，而不是只说
     「不一致」。
  2. 改回去，新检查必须绿。
  3. 第四份用一条命令核：
     `gh release view v1.0.0 --json body` 取回正文，与
     `docs/reports/v1.0.0-github-release-body.md` 的正文段（末尾「## Appendix」之前）
     `diff`。**这条要联网，本轮没有跑** —— 它是给发版者在有网时用的。

---

## 4. 本轮已核清、**不需要**动的地方

记下来是为了让下一次演练不用重查。

| # | 结论 | 依据 |
|---|---|---|
| 1 | 重打 `v1.0.0` **不会**让报告里的 `history.*.tests` 作废 | `HISTORY_TAGS` 不含 `v1.0.0`（`scripts/refresh-report-figures.py:229`）；`collected_at_tag()` 从 `git archive <tag>` 量（`:1044-1070`）—— R12 |
| 2 | 改 `docs/` 下的文件**不进**指纹，所以改文档本身不需要重测量 | `fingerprint_files()`（`scripts/refresh-report-figures.py:908-931`）只收 `src/`、`tests/`、`pyproject.toml` 与测量脚本 —— R1 |
| 3 | 已开始的 CI run **不会**被后来的 tag push 打断 | `.github/workflows/ci.yml:23-32`，`cancel-in-progress: false` —— R5 |
| 4 | 第四份对外文本（GitHub 上已发布的那一份）确实**没有**自动比对，清单已如实标出 | §7 N6（`docs/reports/v1.0.0-release-checklist.md:448-464`）—— R8 |
| 5 | 测量指纹的**跨平台**归一（CRLF/LF）已在脚本里做了，两个平台算出的指纹相同 | `source_fingerprint()` 对换行做归一（`scripts/refresh-report-figures.py:934-961`）；`tests/test_docs.py::test_the_source_fingerprint_ignores_line_endings`（`tests/test_docs.py:1339`）—— 这条**不是**重打 tag 路径的坑 |

---

## 5. 一句话总结

§3 步骤 8 现在是一张**动作清单**，还不是一条**判据链**：它说清了九个动作，却没有说清
「什么时候必须做」「做到什么程度算做完」「谁在等」。这一轮踩的坑，几乎全部落在后三件事
上 —— **指纹变了却按「数字没变」跳过了重测量**（R1、R2）、**在 tag 移过之前就核了引用**
（R3）、**把本地的 tag 当成了已发布的 tag**（R4）、**把上一条 run 的结论当成了这一条的**
（R5）、**以为测量脚本会重画卡片**（R6）、**以为四份文本都有机器在比**（R7、R8）。

三条判据就是补这三处：**指纹代替数字**（A）、**本地与远端分开查、引用检查排在 tag 之后**
（B）、**把「同一批数字」写下来并让每份副本都有人比**（C）。

---

## 6. 本轮的核法（可复现）

只读，全部可重跑：

```bash
# 判据 A 的机器判据（只读）
git diff --name-only <base>..<new> -- src/ tests/ pyproject.toml scripts/refresh-report-figures.py

# 判据 B 的机器判据（只读；后者要联网）
git rev-parse v1.0.0^{commit}
git ls-remote origin 'refs/tags/v1.0.0^{}'

# 本记录里各条引用的位置（只读）
grep -n "fingerprint_files\|HISTORY_TAGS\|def collected_at_tag" scripts/refresh-report-figures.py
grep -n "TREE_DOCUMENTS\|def tree_of\|def tree_fingerprint\|def check_declaration" scripts/check-doc-citations.py
grep -n "OUTWARD_DIRECTORIES\|def release_documents\|def check_outward_counts" scripts/check-version-claims.py
grep -n "^  social-preview:\|^  measurement:\|cancel-in-progress\|group:" .github/workflows/ci.yml
grep -rn "1694" --include=*.md .
```

**没有跑的**：`scripts/refresh-report-figures.py`（任何模式）、完整测试套件、
`git tag` / `git push`、任何联网操作、任何对既有文件的修改。
