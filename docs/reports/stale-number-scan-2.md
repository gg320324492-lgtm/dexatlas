# 全库过期数字扫描（第二轮，只读）

**本窗口为只读扫描：未修改任何既有文件（除新增本报告），未运行任何项目测量。**
未运行 `pytest` / `pytest --cov` / `coverage`，未运行 `uv sync`，未运行
`scripts/refresh-report-figures.py`；未向 `E:\Dexatlas` 共享树写入任何内容
（只读取）。`git status` 在本 worktree 内除本文件外无变化。

核对行号用的是 `Read` / `Grep` / `git show` / `git ls-files` / `git ls-tree`。
另外调用了三样**只读**的东西复算数字，均不写文件：

- `scripts/check-version-claims.py --base auto`（版本声明核对，只读；
  用来复核 `docs/how-to-verify.md` 里那段样例输出的真值），
- `scripts/m10_selfcheck.py`（M10 自查；**只读**，它不写仓库），
- `scripts/check-doc-citations.py`（引用核对；含本报告在内 rc=0、
  `unresolved paths: 0` / `drifted: 0`）。

- **扫描基准**：本 worktree `E:\Dexatlas\.claude\worktrees\competent-dewdney-0895d1`，
  HEAD `9e1aa61`（"最终测量落定：1643 passed / 0 failed / 0 skipped，指纹
  d0e85b61，两张图重画"），工作区 clean，tag `v1.0.0` 已存在。
- **扫描范围**：`docs/` 全部子目录（`reports/` 62 份 + `architecture/` + `roadmap/` +
  `releases/` + `outreach/` + `proposals/` + `benchmarks/` + `case-studies/` +
  `assets/` + `docs/` 根下 11 份）、`README.md`、`README.zh-CN.md`、`CHANGELOG.md`、
  `CLAUDE.md`、`AGENTS.md`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、
  `.github/workflows/ci.yml`。
- **与上一轮的关系**：上一轮（`docs/reports/stale-number-scan.md`）在 `8f9ddca`
  上扫过，挖出 52 处。**本轮不重复列已修好的**；只列「现在仍然存在」的问题，
  以及这一轮新合并的三份报告带来的新问题。
- **与并行会话的重叠**：另一并行会话的 `docs/reports/changelog-vs-release-notes.md`
  已在上一轮记过 `CHANGELOG.md` 的两处（十个只读工具、退出码 6 前后矛盾）——
  **这两处本轮已核实修好**（`CHANGELOG.md:372` 写「MCP 工具从十个增至十一个」，
  `:345-350` 写「本版已按方案 A 实施」），不再列出。

> **处置状态（2026-11-18，扫描之后）**：本报告 §2 的 **67 处**已处置完——
> A 组 6 处在扫描之后已被提交 `d4874b8` 先行修好（`1642 passed` → `1644 passed`）；
> **其余 57 处**按本报告的「应改为」逐条改掉；**剩下 4 处在 `docs/status.md`**
> （B 组 3 处 + D 组 1 处），那个文件由 `scripts/refresh-report-figures.py` 写，
> 留给主会话在最终重测量落盘时一并改。
>
> **「现在写的」那一栏记录的是扫描当时（基准树 `9e1aa61`）的文本。** 它引用的
> `file:line` 今天不再指向同一句话——**那是处置的结果，不是新的漂移**。本报告是只读
> 扫描的产物，不随处置改写。

> **扫描期间仓库的变动**：本扫描期间，**完整重测量正在跑**，落盘后测试数、覆盖率、
> 源指纹会全部换新。因此本报告**不判**这些数字的当前对错，只指出**哪些地方是手写的、
> 脚本管不到**——那才是会长期腐烂的地方（见 §5）。

---

## 0. 权威基线（先核到出处，再用来判文档）

| 事实 | 值 | 出处 |
|---|---|---|
| MCP 只读工具数 | **11** | `src/dexatlas/mcp/server.py` 11 个 `@server.tool` |
| CLI 子命令数 | **13** | `src/dexatlas/cli/main.py` 13 个 `@app.command()` |
| REST 端点数 | **23** | `src/dexatlas/api/app.py` 23 条路由 |
| 公共契约活检（**静态条数**） | **49 = 28 REST + 6 MCP + 15 CLI** | `scripts/verify-public-contracts.py` 49 个 `check()`（分段计数：REST 28 / MCP 6 / CLI 15）；`tests/test_public_contracts.py:759`/`:762` 把这个数**钉住** |
| 契约活检（**实跑条数**） | 三后端齐备 **48**；仅 androguard **47** | `docs/architecture/public-contracts.md:366-369`（带分支与 commit 的实跑记录） |
| JSON 报告顶层键 / `schema_version` | **10** / **3** | `src/dexatlas/reports/json_report.py:32` |
| 工作区 schema | **7** | `src/dexatlas/core/storage.py:44` |
| CLI 退出码 | **0–6**（0 成功 / 1 空 / 2 请求错 / 3 失败 / 4 歧义 / 5 截断 / 6 无索引） | `src/dexatlas/cli/main.py:94-135` |
| CI workflow **job 定义数** | **10**（`lint`、`test`、`test-partial-backends`、`m3-comparison`、`docker`、`security`、`contracts`、`m10-selfcheck`、**`social-preview`**、`measurement`） | `.github/workflows/ci.yml:38,119,198,270,406,416,442,471,500,519` |
| CI **并行运行数** | push/PR **10** 次；推 tag **11** 次（`test` 是 3.12/3.13 两格矩阵；`measurement` 只在 tag 上跑） | 同上；`ci.yml:522` 的 `if: startsWith(github.ref, 'refs/tags/')` |
| CI 触发条件 | `push` 收 `branches: [main, 'release/**']` + `tags: ['v*']`；`pull_request` 收 `main` | `ci.yml:4-22` |
| `.github/workflows/ci.yml` 行数 | **551** | `wc -l .github/workflows/ci.yml` |
| M10 自查 | **43** 条自动化判定 + **40** 项留人工 | `scripts/m10_selfcheck.py`（`CHECKS` 43 项）；`docs/reports/m10-selfcheck.md:25` |
| 仓库里 `docs/reports/` 报告份数 | **61**（不含 `docs/reports/README.md` 本身） | `git ls-files "docs/reports/*.md"` = 62，减索引页 1 |
| 版本 | **1.0.0**（tag `v1.0.0`，2026-11-17） | `src/dexatlas/__init__.py:11`；`git tag` |
| 自建测试 APK / 案例 / 证据包 | **5** / **3** / **4** | `examples/*/*.apk` 5 个；`docs/case-studies/*.md` 3 篇走查；`docs/case-studies/attachments/*.zip` 4 个 |
| `check-version-claims.py` 读到的文档份数 | **140**（本报告入库后重跑脚本确认） | 该脚本实跑输出（`git ls-files "*.md"` = 150，减 `.github/issues/` 10） |

**最近一次测量（本报告不判其对错，只用作"当前落盘值"）**：1643 passed / 0 failed /
0 skipped；1496 快 + 147 集成；一方代码覆盖率 93.3%（7135/7650 行）；源指纹
`sha256:d0e85b61…`。出处：`docs/reports/phase1-execution-report.md:76-77`、`:879`、
`:1098-1106`（记录块）。

---

## 1. 已跳过（正在被最终重测量重写）

按任务要求，**测试总数、快测数、集成数、覆盖率、覆盖行数、源指纹一律不判对错**，
理由：**正在刷新**。本轮重测量落盘后它们会再换一次。

- `docs/reports/phase1-execution-report.md`（`<!--fig:-->` 标记内）、
  `docs/status.md` §1 快照表（标记内）、`README.md` / `README.zh-CN.md` 顶部两个徽章
  （URL 数字）——这三个文件由 `scripts/refresh-report-figures.py` 写
  （`scripts/refresh-report-figures.py:88,95,101`），**本报告一律不作为发现列出**。
- 下列各处虽然也会被重测量改写，但**它们不在脚本的管理范围内**，所以要单独改：
  见 §2 C 组。

---

## 2. 必须改的 67 处

严重度：**高** = 对外承诺与仓库事实直接冲突；**中** = 读者按它会得到错误结论；
**低** = 不影响结论但与仓库不符。

### A 组 —— 对外发版材料的 `1642 passed` 与报告的 `1643 passed` 直接冲突（6 处）

**这是本轮最要紧的一处。** 它不是「数字旧了」，是**同一份对外材料自相矛盾**，
而且矛盾就发生在"最终测量落定"那一次提交里。

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/releases/v1.0.0.md:91` | `environment run reports **1642 passed + 0 xfailed + 0 skipped**` | **1643 passed** | `**1643 passed + 0 xfailed + 0 skipped**` | `phase1-execution-report.md:879` `<!--fig:suite.passed-->1643<!--/fig-->`；`:1100-1103` 记录块 `"passed": 1643, "failed": 0, "skipped": 0, "xfailed": 0` |
| `docs/reports/v1.0.0-github-release-body.md:165` | 同上 | 1643 passed | 同上 | 同上 |
| `docs/reports/v1.0.0-github-release-body.md:264` | `完整环境下 1642 passed、0 xfailed、0 skipped` | 1643 passed | 1643 passed | 同上 |
| `docs/reports/v1.0.0-github-release-body.md:296` | `\| 1642 passed + 0 xfailed + 0 skipped \|`（该行的「落盘出处」列写的是 `phase1-execution-report.md:879`，而那一行写的是 **1643**） | 1643 passed | 1643 passed | 同上；**这一行是指着自己的出处打自己的脸** |
| `docs/reports/v1.0.0-github-release-body.md:172` | `suite 1642 passed / 0 failed` | 1643 passed | `suite 1643 passed / 0 failed` | 同上 |
| `docs/reports/v1.0.0-github-release-body.md:301` | `suite 1642 passed / 0 failed, coverage 93.3%` | 1643 passed | 1643 passed | 同上 |

**成因（已用 git 复现）**：这不是一处老早就错的手误。`c8fa1e9` 把
`docs/releases/v1.0.0.md:90-91` 从「1632 tests（1485 fast + 147 integration）／
**1632 passed**」改成「1643 tests（1496 fast + 147 integration）／**1642 passed**」，
**那时是对的**——那一棵树的报告记录块当时就是 `"passed": 1642`。
真正的回归在 **`9e1aa61`（最终测量落定）**：该提交把发版正文里的源指纹从
`sha256:171a70b8…` 手工改成 `sha256:d0e85b61…`（**改对了**），却把**紧挨着的
那句 `suite 1642 passed` 留在原地**
（`git show 9e1aa61 -- docs/reports/v1.0.0-github-release-body.md` 可见：
指纹行变了、`1642 passed` 行没变）。而它引用的报告记录块在同一个提交里
已经变成 `"passed": 1643`。

> `docs/releases/v1.0.0.md` **完全没被 `9e1aa61` 碰过**，于是 `:91` 的
> `1642 passed` 在 `9e1aa61` 那一刻变旧；而 `:90` 的总数（1643 / 1496）
> 是 `c8fa1e9` 改的，**两行分别来自两次提交**。
> **一颗 bullet 里两个数差 1：1643 个测试、1642 passed、0 xfailed、0 skipped**——
> 差的那 1 条测试，在报告里既没失败也没跳过。

**为什么没人发现**：`scripts/check-doc-citations.py` 核的是**行号**（那一行还在），
不核**值**；`scripts/check-version-claims.py` 的 `release_documents()` 只收
`docs/releases/{tag}.md` 与 CHANGELOG 的发版段，**不收 Release 正文**；
`tests/test_public_contracts.py:771` 只收这个文件里的 `49` 与 `28 REST + 6 MCP + 15 CLI`。
**这个数谁都不管。**

### B 组 —— CI 的 job 数与触发条件：漏了 `social-preview`（6 处）

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/status.md:26` | `**9 个 workflow job、10 次并行运行**`，job 列表里没有 `Social preview card` | **10 个 job 定义 / 推 tag 时 11 次并行运行** | `**10 个 workflow job、推 tag 时 11 次并行运行**`（push/PR 是 10 次），并在列表里补 `social preview 图检查` | `ci.yml:500` `social-preview:`（`name: Social preview card`） |
| `docs/status.md:50-51` | `**CI 的九个 workflow job** 各自覆盖一种配置……展开后是**十次并行运行**` | 十个 / 十一次 | `**CI 的十个 workflow job**……展开后是**十一次并行运行**` | 同上 |
| `docs/status.md:55-64` | CI 表 10 行，**缺 `Social preview card` 一行** | 11 行 | 补一行（覆盖面：该 job 跑 `scripts/make-social-preview.py --check`，核对卡片上的数与报告一致） | `ci.yml:500-513` |
| `docs/reports/v1.0.0-release-checklist.md:60` | `最终 commit 上 CI **9 个 job / 10 次并行运行**全绿` | 10 / 11 | `**10 个 job / 11 次并行运行**` | 同上 |
| `docs/reports/v1.0.0-release-checklist.md:136-139` | `当前 CI 共 **9 个 job / 10 次并行运行**（lint、test 矩阵两个 Python 版本、test-partial-backends、m3-comparison、docker、security、contracts、m10-selfcheck、measurement）` | 同上；**列表里少了 `social-preview`** | 补进列表并改数 | 同上 |
| `docs/HANDOVER.md:148-151` | `CI runs six jobs (seven parallel runs): lint/format/mypy, tests on Python 3.12 (every backend), tests on Python 3.13 (no external backends), tests with Apktool only, the Docker image, and the dependency audit.` | **ten jobs (eleven runs on a tag)**；列表里少 **5 项**（M3 对比重跑、公共契约活检、M10 自查、social preview 图检查、tag 上跑的测量比对） | 整段改成现行 10 项 | `ci.yml:38-519`；同文件 `:54` 起的 M10 行已按 43 条自查写，是对的 |

**三个独立来源互相印证**，说明 `status.md`、发版清单与 `HANDOVER.md` 是**没跟上**的三处：

- `docs/portfolio.md:68`：`ten CI jobs (eleven runs on a tag — the test job is a 3.12/3.13 matrix)`
- `CLAUDE.md:66` / `AGENTS.md:66`：`the social-preview … job`，`ten jobs (eleven parallel runs on a tag)`
- `docs/portfolio.md:73` 还逐个列出了 `a job that checks the social preview card's numbers against the report`

> **一个必须小心的陷阱**：`docs/reports/v1.0.0-ci-run-record.md:50` 写的「**10 个 job**
> 里 4 个红」也是**同一个数、另一个分母**——它数的是 **v1.0.0 tag 那次 run 的 10 行
> 逐 job 结论**（`test` 矩阵展开成 3.12/3.13 两行）。那一棵树（`75976e0`）上
> workflow 只有 **9** 个 job 定义。这条**不用改**，但它是"`10 个 job`"这句话
> 被读成"10 个 job 定义"的来源。

### C 组 —— 手写测量数字：下一轮重测量会再烂一次（16 处）

**这组是本轮真正要交给主会话长期看管的**：这些数**不在**
`scripts/refresh-report-figures.py` 的管理范围内（该脚本只写
`phase1-execution-report.md`、`docs/status.md`、两份 README 的徽章），
所以每次重测量都要**人手改一遍**。

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/portfolio.md:67` | `1,632 tests at 93.3% coverage` | **1,643** | `1,643 tests` | `phase1-execution-report.md:76`；同文件 `:68` 的 CI 数**已经**是对的（ten/eleven），只有测试数没跟上 |
| `docs/reports/social-preview-howto.md:74` | `\| 1632 \|`（落盘出处写的是 `phase1-execution-report.md:76`） | **1643** | `\| 1643 \|` | 同上（`:76` 现在是 1643）；`.github/social-preview.json` 的 `tests.total` 已是 1643 |
| `docs/reports/social-preview-howto.md:75` | `\| 1485 快 + 147 集成 \|` | **1496 快 + 147 集成** | `\| 1496 快 + 147 集成 \|` | 同上 |
| `docs/reports/m10-reader-package.md:110` | `实测：三后端齐备但未取样本时汇总行是 1593 passed, 27 skipped` | **1616 passed, 27 skipped**（1643 − 27） | `1616 passed, 27 skipped` | `docs/how-to-verify.md:167` 写的是同一场景的 `1616 passed, 27 skipped`（正确）；本文件落后两轮 |
| `docs/reports/m10-reader-package.md:111` | `取到之后是 1620 passed、0 skipped ——**这才是报告里记录的那次完整测量**` | **1643 passed、0 skipped** | `1643 passed`、`0 skipped` | `phase1-execution-report.md:879` |
| `docs/reports/m10-reader-kit.md:181` | `不抓则 27 个集成用例 skip（实测 1593 passed, 27 skipped），取到后是 1620 passed / 0 skipped` | **1616 passed, 27 skipped** / **1643 passed** | 同上两处 | 同上 |
| `docs/reports/m10-number-traceability.md:4` | `权威值随之变为 **1,588 个测试（1,441 快 + 147 集成）**` | **1,643 个测试（1,496 快 + 147 集成）** | 整句替换 | `phase1-execution-report.md:76` |
| `docs/reports/m10-number-traceability.md:5` | `一方代码覆盖率 93.3%（7,117/7,631 行），源指纹 sha256:787282…` | **93.3%（7,135/7,650 行）** / **`sha256:d0e85b61…`** | 整句替换 | `phase1-execution-report.md:77`、`:1098` |
| `docs/reports/outreach-final-review.md:3-4` | `权威值变为 **1,588 个测试（1,473 快 + 147 集成）、一方代码覆盖率 93.3%（7,117/7,631 行）**` | **1,643 个测试（1,496 快 + 147 集成）/ 93.3%（7,135/7,650 行）** | 整段替换 | 同上；**另：1,473 + 147 = 1,620 ≠ 1,588，同一批另两份写的是 1,441——这一份自己的数就加不平** |
| `docs/reports/outreach-recheck.md:5-6` | `权威值为 **1,588 个测试（1,441 快 + 147 集成）、一方代码覆盖率 93.3%（7,117/7,631 行）**` | **1,643（1,496 快 + 147 集成）/ 93.3%（7,135/7,650 行）** | 整句替换 | 同上 |
| `docs/reports/outreach-publish-checklist.md:40-41` | `**1,588** 个测试（1,441 快 + 147 集成）` / `**93.3%**（7,117 / 7,631 行）`，核过栏写 `✅ 一致` | **1,643（1,496 快 + 147 集成）/ 93.3%（7,135 / 7,650 行）** | 三处一起改 | `phase1-execution-report.md:76-77` |
| `docs/reports/outreach-publish-checklist.md:51-53` | `三个标记分别落盘为 1588、1441、147；素材里写的是 1,588` | 落盘现为 **1643、1496、147** | 整行改 | 同上 |
| `docs/reports/new-pages-crosscheck.md:29`、`:100`、`:463` | `1,588（1,441 快 + 147 集成）` / `1,561 + 27 = 1,588` | **1,643（1,496 快 + 147 集成）** | 三处一起改 | `phase1-execution-report.md:76` |
| `docs/reports/next-engagements.md:419` | `按最后一次完整测量再核一次对外数字（**现在落盘的是 1,612 / 93.3%**）` | **1,643 / 93.3%** | 改数 | 同上 |
| `docs/how-to-verify.md:216` | 样例输出 `documents read: 115` | **140** | `documents read: 140` | `scripts/check-version-claims.py --base auto` 实跑输出 |
| `docs/how-to-verify.zh-CN.md:193` | 样例输出 `documents read: 110` | **140** | `documents read: 140` | 同上 |

**`docs/reports/m10-reader-package.md` / `m10-reader-kit.md` 这四处要单独说**：
那两份是**要交给一位未参与实现的外部读者**的一站式执行包（M10 独立验收尚未开始），
它们告诉读者「报告里记录的那次完整测量是 `1620 passed`」——**那是两轮之前的数**。
读者照它跑一遍会得到 1643，然后无从判断是文档错还是自己错。
**同一句旁边那个 `1593 passed, 27 skipped` 也同样过期**（27 这个 skip 数本身是对的，
`scripts/m10_selfcheck.py` 跨三份材料钉着它；**总数没有任何东西钉**）。

**`docs/how-to-verify.md` 那两处更典型**：该页 `:233` 自己写着
「**`documents read` 那行是活的。** 它数的是当前这棵树里 Markdown 的份数——
本文件也是被数的之一，所以改完任何一份文档都要重跑一遍门禁」，
**然后页面里摆着一个落后 25 份的数字**（140 − 115；中文页落后 30 份）；
**英文页与中文页还各写一个（115 / 110）**，**同一个脚本、同一棵树，两个数**。
同一段样例里的 `findings: 2 (2 already in 8f9ddcaf)` 也要一起改：
**`documents read` 那一行现在该是 `140`**（本报告入库后重跑脚本确认），
而 `already in <hash>` 那一段跟的是 HEAD，**每提交一次就变一次**——
所以这一行只能重抄，不要手写（本次扫描时脚本输出的是 `2 (2 already in 9e1aa616)`）。

**另有两处「结构上就会静默腐烂」的**：

- `docs/how-to-verify.md:433` 与 `docs/how-to-verify.zh-CN.md:405` 有一行
  `<!--fig:tests.total-->1643<!--/fig-->`。这个 `fig:` 标记**在脚本的管理范围之外**
  ——`refresh-report-figures.py` 只写 `phase1-execution-report.md`、`docs/status.md`
  和两份 README。**这一行永远不会被脚本更新**，它看起来像生成物，实际是手抄的。
  当前值 1643 恰好是对的，但下一次重测量它就会悄悄变成一个假的"生成数字"。
- `docs/reports/README.md:85` 说 `v1.1.0-candidates.md` 有「**12 项候选**」，
  真值是 **15**（`v1.1.0-candidates.md` §3 的 C1–C15；其 §4 表自己写
  `合计 15`，并给了 `3 + 1 + 4 + 2 + 5 = 15 ✓`）。索引页落后在那份清单扩充之前。

### D 组 —— 索引与清单的份数、漏行（6 处）

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/reports/README.md:3` | `这个目录里是 …… **61 份报告**` | **61**（= 实际文件数，**当前是对的**） | 本轮新增本报告后变 **62** | `git ls-files "docs/reports/*.md"` = 62，减索引页 = 61 |
| `docs/reports/README.md:42` | `（2026-11-18 复核：目录里 61 个 .md **全部被点名，无遗漏**。）` | **假**：`round-two-fresh-read.md` **全篇未被点名**（`grep 'round-two-fresh-read' docs/reports/README.md` 无命中） | 补进 §6 并把 `无遗漏` 改成真话 | `git ls-files "docs/reports/*.md"` 含该文件；`:190-195` 自己也写着「**新增报告时，请把它加进来**」 |
| `docs/reports/README.md:42` | `§1–§6 加起来是 68 行而不是 61——其中 8 份在两节里各列了一次……**去重后 §1–§6 点名 60 份，第 61 份在 §7**` | §1–§6 自己的表行合计是 **60**（7+5+6+10+8+**24**）；跨小节重复点名的是 **15** 份（不是 8）；**§7 那张表点名的 8 份全部已在 §1–§6 里出现过，它一份新的都没加** | 整句重写 | 逐节数表行：§1 `:59-65` 7 行、§2 5、§3 6、§4 10、§5 8、§6 `:135-158` **24** |
| `docs/reports/README.md:28`、`:29`、`:31-32` | 表里 §6 写 **32**、合计写 **68**；同页 `:31-32` 又说「§7「历史记录」是横切视角，点名的文件都已计在上面的分组里，**不另计份数**」 | §6 那 32 = §6 自己的表（24 行）+ §7 那张表的 8 行（`:165-174`）。**§7 没有 `## 7.` 标题**，它的表仍在 §6 的标题之下（`:124` 是 §6，`:160` 起是 §7 的内容），所以「§6 的份数」按页首那句「每个『份数』就是该节表格的行数」算，就等于把 §7 又数了一遍 | 两条路选一条：① 给 §7 加 `## 7.` 标题，让 §6 = 24、合计 = 60；② 保留现状但在 `:31-32` 改成「§6 的 32 含 §7 那张表」 | `:19-32` 分组一览表；`:124`、`:160`、`:165` 的实际结构 |
| `docs/reports/README.md:3` vs `:29` | 页首 **61**（文件数）与表里 **68**（行数）**用同一个词「份」** | 两个分母 | 页首改成「61 份报告文件」，表里合计列注明「68 行（61 份文件）」 | 同上 |
| `docs/status.md:74-80` | §2「已发布」表的最后一行是 `v0.2.0`（2026-11-14），**没有 `v1.0.0` 一行** | 同一份文档 §1 的快照 `:22` 已经写着「**v1.0.0**（2026-11-17 已发布，见[发版说明](../releases/v1.0.0.md)）」 | 表里补一行 `v1.0.0` | `docs/status.md:22`；`docs/releases/v1.0.0.md` 已存在；`git tag` 有 `v1.0.0` |

**为什么这条要算高**：`docs/reports/README.md` 是这一层唯一的入口，页面自己说
「不知道哪一份是现状、哪一份是当时的快照」。**入口页上三个"份数"互相打架**，
恰好在它要回答的那个问题上失效。而且 `docs/reports/english-reader-review-2.md:874`
那行写着「索引的份数 …… **已改**：分组份数按实际行数改齐，合计与总数对齐」——
**这句话是假的**（见 G 组）。

### E 组 —— 审计记录里的旧测量值，且行内断言「一致」（10 处）

这些都在 `docs/reports/` 下的审计报告里。它们**有基线声明**（那一层属历史陈述），
但**行内的那句断言是现在时**——「这两个数一致 ✓」——而今天它们**不再一致**。
判为过期数字。

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/reports/m10-selfcheck.md:114` | `README 徽章（tests 1620 / coverage 93.3%）与执行报告 <!--fig:--> 数字一致；tests.total = 1473 + 147 加和成立` | 徽章是 **1643**；加和是 **1496 + 147** | 改成 1643 / 1496 + 147 | `README.md:12` 徽章 `tests-1643`；`phase1-execution-report.md:76` |
| `docs/reports/round-two-fresh-read.md:730` | `README.md:12-13（徽章 1632 passing / 93.3%）、README.md:15（正文 1632）、README.md:21（alt 1632）` | 徽章 **1643**；`:15` 的正文与 `:21` 的 alt **已不再有数字**（alt 文本已按 `social-preview-howto.md:59-60` 的规定去掉数字） | 整行按当前树重写 | `README.md:12`、`:15`、`:21` |
| `docs/reports/readme-image-consistency.md:503` | `\| 1632 \| phase1-execution-report.md:76 \| ✅ 一致 \|` | **1643** | 1643 | `:76` 现在是 1643 |
| `docs/reports/readme-image-consistency.md:504` | `\| 1485 快 + 147 集成 \|` | **1496 快 + 147 集成** | 同上 | 同上 |
| `docs/reports/outreach-first-read.md:463` | `\| 测试总数 \| 1,632（四处） \|` | **1,643** | 1,643 | `phase1-execution-report.md:76` |
| `docs/reports/outreach-first-read.md:464` | `\| 快测 / 集成 \| 素材未写拆分 \| <!--fig:tests.fast-->1485<!--/fig--> \|` | **1496** | 1496 | 同上 |
| `docs/reports/final-outward-consistency.md:45` | `\| 测试总数 **1,588**（1,441 快 + 147 集成） \| …… \| 一致（5 处） \|` | **1,643**（1,496 快 + 147 集成）；且那 5 处现在**已经彼此不一致** | 整行改，并说明"现在哪几处不一致" | `phase1-execution-report.md:76` |
| `docs/reports/github-repo-metadata-proposal.md:78` | `徽章：Tests \| README.md:12 → tests-1588 passing …… \| 数字与落盘报告一致 ✓` | 徽章现在是 **tests-1643** | 数字不动那句改成"数字由脚本写入，脚本会跟着重测量更新" | `README.md:12` |
| `docs/reports/github-repo-metadata-proposal.md:80` | `徽章数值与落盘报告是否一致 \| **一致 ✓**：……1588 与……的 1588（1441 快 + 147 集成）相符` | 徽章 **1643**、报告 **1643（1496 快 + 147 集成）** | 整行改 | `README.md:12`；`phase1-execution-report.md:76` |
| `docs/reports/outreach-first-read.md:182` vs `:193` | `:182` 的小节标题写「仓库里其实是**十个 job**」，`:193` 的正文写「`.github/workflows/ci.yml` 有 **9 个 job 定义**（列 9 个名字，漏了 `social-preview`）」 | **10** | `:193` 改成 10 并把 `social-preview` 补进去 | `ci.yml:38-519`；同文件 `:602` 已经写「已改：十个 job（tag 上十一次并行运行）」——**同一份文件里三处两种说法** |

### F 组 —— 流程数字与"最新/现状"声明（5 处）

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/reports/ci-gate-coverage.md:7-8`、`:49` | 摘要用**现在时**写：「CI 只在 `main` 上触发（`.github/workflows/ci.yml:3-7`）」「**tag 推送不触发 workflow**（`on.push` 只收 `main` 分支，`ci.yml:4-5`）」；§1 写「CI 一共 6 个 job、7 次并行运行」 | 现在 `on.push` 是 `branches: [main, 'release/**']` + `tags: ['v*']`（**tag 推送会触发**）；现行 workflow **10** 个 job 定义 | 三处都改成现行事实，或在摘要里加一句「以下结论属于 `062c4b5` 那棵树」 | `ci.yml:4-22`、`:38-519`；该报告的复核树是 `062c4b5`（`:2`） |
| `docs/reports/v1.0.0-release-checklist.md:645` | `（2026-11-18 实测：徽章已是 1632，那两处还写着 1612）` | 徽章现在是 **1643** | 改成 1643（并确认那两处现在是什么状态） | `README.md:12` |
| `docs/service-commitments.md:3` | `最新实测基准：[m6-level2-retest2.md]（2026-11-16）` | retest2 **不是**最新——`m6-level2-retest4.md`（三轮 15/16/18 = 49/60 = 81.7%）更晚 | 改指 retest4，或把"最新"改成"本文 §2 引用的是 retest2 那一次" | `docs/benchmarks/m6-level2-retest4.md`；`docs/status.md:137` 引用的是 retest4 |
| `docs/reports/next-engagements.md:411` | `材料已齐：…… + 40 项检查表 + 发起人发送前清单 + **自查脚本 40/40**` | 自查是 **43 条**自动化判定 | `自查脚本 43/43` | `scripts/m10_selfcheck.py`；`docs/reports/m10-selfcheck.md:25`、`:88` |
| `docs/reports/next-engagements.md:435` | `**1,612 项测试 / 93.3% 一方代码覆盖率**`（§5.1「已经成立的事实」） | **1,643 / 93.3%** | 改数 | `phase1-execution-report.md:76-77` |

### G 组 —— 审计报告里的**处方**照做会写错（7 处）

这一组最危险：**它们不是数字，是"该怎么改"的指令**。照着做会把已经改对的地方改回错的。

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/reports/round-two-fresh-read.md:585` | `CI runs nine jobs (ten parallel runs on a tag push, **eight on a push or PR**): lint/format/mypy, …` | **ten jobs (eleven parallel runs on a tag push, ten on a push or PR)** | 整句替换 | `ci.yml:38-519`；`CLAUDE.md:62` / `AGENTS.md:62` 已经写成 "ten jobs (eleven parallel runs on a tag)"——**照这条处方改会把改对的地方改回错的** |
| `docs/reports/round-two-fresh-read.md:607` | `建议改法：改成「nine CI jobs — ten parallel runs on a tag push (the test job runs …` | 同上 | 同上 | 同上 |
| `docs/reports/denominator-and-tree-pass.md:154`（S3 行） | 处方：把 `docs/status.md:26` 改成「**9 个 job 定义 / 10 次并行运行**」 | **10 个 job 定义 / push-PR 10 次 / tag 11 次** | 照这条改会写成错的；`social-preview` job 由 `5c097fe` 加入 | `ci.yml:500` |
| `docs/reports/denominator-and-tree-pass.md:156` | `social-preview-howto.md:53-55 \| 映射表已由最终重测量刷新为 1632 / 1485 快 + 147 集成 / 7135/7650 \| **已同步** ✅` | 「已同步」现在是假的（落后一轮：1643 / 1496 快 + 147 集成） | 状态改成「已再过期一轮」 | `social-preview-howto.md:74-75` |
| `docs/reports/english-reader-review-2.md:874` | `docs/reports/README.md:3、25、27、29 \| 索引的份数 \| 纯手写 \| **已改**：分组份数按实际行数改齐，合计与总数对齐` | **实际没改齐**（§6 = 24 行、§1–§6 合计 60，页首 61 与表里 68 两个分母） | 状态改成「**未改齐**」并指向 D 组 | 同文件 `:383` 已经指出「索引页自己的份数有三个，§3 / §5 的分组份数没跟上」 |
| `docs/reports/english-reader-review-2.md:869` | `README.md:21 \| social preview 的 alt 文本「…**1612** tests」 \| **待最终同步**` | alt 文本**已经没有数字了** | 状态改成「**已删除**」 | `README.md:21` |
| `docs/reports/readme-image-consistency.md:641` | `而重画之前得先把 README.md:15、:21 的 1612、howto §4 的两处错、49 的分项口径这四件事定下来` | README 那两处**已删除**，只剩 howto §4 的两处错与 `49` 的分母口径 | 改成两件事 | `README.md:15`、`:21`；`social-preview-howto.md:74-75` |

### H 组 —— 三份新合并报告里已经过期的状态数（9 处）

这三份是本轮新合并的。**它们的分母写得比别的报告清楚**（见 §2.5），
但**状态桶**是在自己的基准树之后落地的那几项落地之前写的——
**文件自己打勾了，却没回头改自己的摘要**。

| 文件:行 | 现在写的 | 真值 | 应改为 | 依据 |
|---|---|---|---|---|
| `docs/reports/v1.1.0-candidates.md:44` | `**3 项已做完**（C1、C3、C7）、**1 项主体做完剩最后一段**（C4）、**11 项未开始**` | **5 项已做完**（C1、C3、C4、C7、C14）、**0 项主体完成**、**10 项未开始** | 3/1/11 → **5/0/10** | C4 已闭合（`:380`「已闭合（2026-11-18）」）；C14 的 `scripts/make-social-preview.py`、`tests/test_social_preview.py`、`ci.yml:500 social-preview` 三件都在树里（`92053b0`/`cb24417`/`5c097fe`/`a5c3365`） |
| `docs/reports/v1.1.0-candidates.md:45` | `现在就能做的有几项？ **4 项**（C5、C6、C14、C15）` | **3 项**（C5、C6、C15） | 去掉 C14 | 同上 |
| `docs/reports/v1.1.0-candidates.md:49` | `**候选总数怎么对得上** **15 = 3（已完成）+ 1（主体完成）+ 4（未开始·仓库内可做）+ 2（未开始·要作者的真值）+ 5（未开始·等外部条件）**` | **15 = 5 + 0 + 3 + 2 + 5** | 换桶 | 同上；**`:55` 自称「这张表是 §0 各项数字的唯一出处」，所以 §0 全表、§2 排序、§4 触发表全部跟着歪** |
| `docs/reports/v1.1.0-candidates.md:57` | 桶表 `🟡 **主体完成，剩最后一段** \| 1 \| C4 \| 文档侧已收口；**第三个包的附件还在入库**` | C4 **已闭合**，四个包已入库 | 该行删掉（C4 移到已完成桶） | `docs/case-studies/attachments/` 现在 16 个文件（4 zip + 12 散装）；`git show cb24417 --stat` |
| `docs/reports/v1.1.0-candidates.md:61` | 桶表 `⬜ **未开始·仓库内可做** \| 4 \| C5、C6、C14、C15` | **3**（C5、C6、C15） | 去掉 C14 | 同上 |
| `docs/reports/v1.1.0-candidates.md:146` | `**P0** \| C4 证据包与分析的对应关系 \| **文档侧已完成，附件待入库**` | **已闭合** | 状态改成「已闭合」 | 同 `:380` |
| `docs/reports/v1.1.0-candidates.md:148`、`:518`、`:526` | `**P1** \| C14 social preview 图的自动化守护 \| **未开始（新增）**`；`:518` `**状态**：⬜ **未开始**。`；`:526` 的缺口段仍写「**绘图脚本不入库**、CI 零命中」，并带着 `测试数 1632（1485 快 + 147 集成）` | C14 **已落地**；测试数现值 **1643（1496 快 + 147 集成）** | 三处都改成现状 | `scripts/make-social-preview.py`、`tests/test_social_preview.py`、`ci.yml:500`；`phase1-execution-report.md:76` |
| `docs/reports/release-process-dry-run.md:541` | `§8.4 C1–C11 \| 作者 \| **6 条已落地、5 条未落地**` | 同一份文件的 `:243`、`:410`、`:517`、`:596` 四处都写「**7 条已落地 + 1 条部分落地（C2）+ 3 条未落地**」 | `:541` 改成「7 + 1 + 3」 | `:243`「**分母 = §8.4 的 11 条候选（C1–C11）**：已落地 **7** 条、**部分落地 1** 条、未落地 **3** 条」 |
| `docs/reports/release-process-dry-run.md:111` | `docs/case-studies/attachments/ 下 9 个文件齐（**3 套 × HTML/JSON/MD + 3 个 zip**）` | 9 个文件对（对基线 `75976e0`），但**括号里的分解算出来是 12**：那一棵树上是 **2 套三件套（demo、obfuscated）+ 3 个 zip**（api-integration 只有 zip，没有 html/json/md） | 分解改成「2 套 × HTML/JSON/MD + 3 个 zip」 | `git ls-tree 75976e0 docs/case-studies/attachments/` |
| `docs/reports/portfolio-readiness-2026-11-18.md:441` | §7 行 7：`**CI 的运行结果没有落盘记录** \| 机制在 ci.yml，运行结果不在仓库里；读者无法自行复核` | **已经落盘**：`docs/reports/v1.0.0-ci-run-record.md` 已入库 | 改成「已由 v1.0.0-ci-run-record.md 落盘」 | 同文件 §8 #17 已标「已做」；该报告入库于 `cb24417` 之后 |
| `docs/reports/reader-dry-run.md:9-10` | `验收对象：v1.0.0 tag 所指提交 0104ccb7c058fab5197320c83723ba01a662b334（tag 对象 dbb2c815…）` | tag 已被重打过多次；`git rev-parse v1.0.0^{commit}` 现在是 **`9e1aa61`** | 改成当前 tag 对象，或写明「tag 已重打，见 ci-run-record」 | `git rev-parse v1.0.0^{commit}`；`docs/reports/v1.0.0-ci-run-record.md:3-4` |

---

## 2.5 三份新合并报告的数字复核（分母是什么、能不能复核）

任务点名的三份报告，逐份核了里面的数。**分母都交代得清楚；过期的是状态，不是口径。**

### `docs/reports/release-process-dry-run.md` —— 73 / 16 / 2 / 17：**已收口 ✓**

原文的三个数（总数 73、「不一致」16、「陈旧数字/前提」17）**都已被主会话改正**，
该文件 `:42-52` 有一段「**复核更正（2026-11-18，主会话）**」把口径换成可复算的：

- **分母是 75 行判定表**（`8 + 8 + 38 + 9 + 6 + 6`）；
- 行分桶：一致 50 + 仅不一致 16 + 不一致且无法验证 1 + 仅无法验证 6 + 缺失/不完整 2 = **75 行**；
- 换成判定格：一致 50 + 不一致 17 + 无法验证 7 + 缺失/不完整 2 = **76 格**
  （多出的 1 格是那行双判定的第二个判定）；
- **本表按「行」记，不按「格」记**。

算式自洽（8+8+38+9+6+6 = 75；50+16+1+6+2 = 75；50+17+7+2 = 76），
分母写在文件里。**不用改。** 需要注意的是：`:35` 现在的「17 行（分母：75 行判定表）、
其中 5 条会直接把作者引到错误结论」与 `:39` 的「16 处（分母：§7 那张表的 17 行）」，
两处的分母不同（75 vs 17），引用时必须连分母一起引——文件自己也是这么要求的。

### `docs/reports/portfolio-readiness-2026-11-18.md` —— 85.0 / 81.9：**可复核 ✓**

- `:72`：`GitHub 加权：4×30 + 3.5×20 + 3.5×10 + 3.5×10 + 3×25 + 1×5 = 120 + 70 + 35 + 35 + 75 + 5 = 340 → 85.0%`，
  `:76` `GitHub 340 / 400 = 85.0%`。**算式在文里，分母是 400（每维满分 4 分、权重和 100%）**。
- `:89`：`Upwork 加权：4×20 + 3.5×15 + 3.5×15 + 3.5×25 + 3×15 + 1×10 = 80 + 52.5 + 52.5 + 87.5 + 45 + 10 = 327.5 → 81.9%`，
  `:92-94` 主动写明「327.5 / 400 = **81.875%**，本文四舍五入报 **81.9%**」
  以及「读者若用 81.9 反推会得到 327.6，与 327.5 差 0.1 —— 那是四舍五入，不是算错」。
- **两个平台的权重表不同**（GitHub 30/20/10/10/25/5，Upwork 20/15/15/25/15/10），
  满分都是 400，**六维的分数档位相同**。这是本仓库里**分母交代得最清楚**的一份。

  **但有一处限定语要跟着走**：`:104-105` 的对照表写着「GitHub … **85.0%**」「Upwork … **81.9%**」，
  而 `docs/reports/v1.0.0-release-checklist.md:54-58` 明确提醒
  「**那份复评评的是 `75976e0` 那棵树**，不是读者今天 checkout 到的树」。
  **这两份材料引这组分数时必须带这句限定语**，否则会把一棵旧树的自评当成今天的。

### `docs/reports/v1.1.0-candidates.md` —— 12 项候选：**总数与分母是对的，状态桶与索引页错了 ✗**

- 真值是 **15 项候选**（C1–C15，`v1.1.0-candidates.md` §3 的 15 个 `#### C*` 小节）。
- 文件自己的**分母口径**交代得很清楚：`:44` 的 `3 + 1 + 11 = 15`、§4 表的
  `3 + 1 + 4 + 2 + 5 = 15 ✓`、`:67-68` 还专门写了一句「**两个分母不要混**：
  『§4 表里的行数』是 **7**（含 2 行非候选动作），『候选项数』是 **15**」——
  **这一份的分母是做对了的**。
- **但那两个桶的内容已经过期**：C4（附件已入库）与 C14（脚本、测试、CI job 都落地了）
  在这份文件的基准树之后完成，§3 的 C4 节自己已经打了「**已闭合（2026-11-18）**」，
  **§0 的摘要桶却没跟着改**。`:55` 自称「这张表是 §0 各项数字的唯一出处」，
  所以 §0 全表、§2 排序、§4 触发表全部跟着歪。**共 9 处，见 H 组。**
- **另外 `docs/reports/README.md:85` 写「12 项候选」** —— 落后在那份清单扩充之前
  （`dcfd82d`「更新下一轮需求候选清单：15 项候选，两条新缺口」）。
  **这是三份新报告里唯一一处落在「对外索引页」上的活错数**，已列在 C 组。

---

## 3. 历史陈述（**不要**改）

这些是「当时就是这样，现在仍然正确，只是描述的是过去」。逐条核过，列出以便
主会话知道哪些不用动。

| 位置 | 现在的说法 | 为什么是历史陈述 |
|---|---|---|
| `docs/architecture/public-contracts.md:366-369` | 三后端齐备 48/48、仅 androguard 47/47 | 带分支名、commit、日期的**实跑记录**；且 `:355` 写明「**49 是静态条数**，任何一次实跑都跑不满它」——分母已经交代清楚 |
| `docs/releases/phase1-acceptance-2026-10-21.md:42-44` | 890 / 885 passed, 5 skipped 等 | Phase 1 验收当时的运行记录 |
| `docs/releases/v0.1.1.md:93-95`、`v0.1.2.md:72-74`、`v0.1.3.md:137-139` | 各版本当时的 passed/skipped 表 | 历史发版记录 |
| `docs/benchmarks/m6-level2-retest3.md`（17/15/17 = 49/60，1,080,116 tokens）与 `m6-level2-retest4.md`（15/16/18 = 49/60，1,182,356 tokens） | 两轮不同的运行 | 两者**分母相同、分子不同**，是两次真跑的各自记录，不是同一轮的两种写法；全库未发现把 17/15/17 与 15/16/18 挂反的地方 |
| `docs/benchmarks/m6-level2-narrow-verify*.md` | 410,256（不完整）/ 420,826（超 410,000 闸）/ 380,881（在 450,000 内） | 三轮窄验证各自有闸位与授权；`docs/status.md:31,43` 与 `docs/releases/v1.0.0.md:46` 引用无误 |
| `docs/reports/release-process-dry-run.md`（含「9 个 job、10 次并行运行」） | 演练克隆 `75976e0` 那棵树上的事实 | 页首有明确基线声明：「**本文的结论属于哪棵树（重要）**……说的都是演练克隆里的那一棵树 —— `75976e0`」；且 `:42-48` 已有一段「复核更正（2026-11-18，主会话）」把 73→75/76、16→17、17→16 全部改正并给了算式——**那组数已经收口了** |
| `docs/reports/portfolio-readiness-2026-11-18.md:72`、`:89`、`:92-94` | GitHub 340/400 = **85.0%**；Upwork 327.5/400 = **81.9%** | 加权算式在文中（`4×30 + 3.5×20 + … = 340`），且 `:92-94` 主动说明了 81.875 → 81.9 的四舍五入与"反推会得到 327.6"的 0.1 差——**分母与算法都在** |
| `docs/reports/v1.1.0-candidates.md:48-49`、`:67-68`、§4 表 | 「3 项已做完 + 1 项主体做完 + 11 项未开始」；「§4 表里的行数是 **7**」「候选项数是 **15**」「§4 的 5 项候选」 | **分母全部写明**，§4 表给了 `3 + 1 + 4 + 2 + 5 = 15 ✓` 的算式；`§4 的 5 项` 与 `候选项 15` 也在 `:67-68` 明确说了「两个分母不要混」——**这一份是做对了的** |
| `docs/reports/next-engagements.md:332` | `同样，1,612 / 93.3% 这两个数**任何一次完整测量都会改**` | 这一句**自己就说明它是随测量变的一次快照**，被用作「对外数字会过期」的例证；例证里的数旧了不影响论点（真值仍是 1,643 / 93.3%） |
| `docs/reports/case-studies-run-correspondence.md:87` | 「共 9 个文件（6 个散装报告 + 3 个 zip）」 | 现为 16 个文件（4 zip + 12 散装），但 `:41` 明写「**本文的结论仍按基线树 `d43369b` 成立**——它记录的是补包之前的状态」 |
| `docs/reports/changelog-vs-release-notes.md`、`denominator-and-tree-pass.md`、`english-reader-review-2.md`、`ci-gate-coverage.md`、`new-pages-crosscheck.md` 等审计报告里的 1,588 / 1,584 / 1,620 等 | 各自基线上的测量值 | 报告开头都写明了基线；**例外**是 E 组与 G 组里那些行内断言"一致 ✓"、标着「已改」或给出**处方**的条目——它们宣称的是现在，或会让人照着做错事 |
| `docs/reports/portfolio-readiness-2026-11-15.md` 与 `portfolio-readiness-2026-11-15-recheck.md`（GitHub 77.5% / Upwork 68.75%） | 11-15 那次评估的分数 | 是评分表的历史快照；`docs/reports/m10-reader-package.md:16`、`:394-395` 已经写明「你的重评请与 **75% / 65%** 这一档对齐」并点明「**同一份报告 §2 里的 77.5% / 68.75% 是它的旧口径，别混用**」——分母已经交代清楚 |

**同时确认两处"写法不同是对的"**（不要去统一它们）：

- `1,643`（散文，带千分位）与 `1643`（徽章 URL / pytest 汇总行）——**徽章是 URL，
  装不下逗号**；`pytest` 的汇总行本来就不带千分位。
- `1593 passed, 27 skipped` 与 `1616 passed, 27 skipped` —— 是**两棵树**上的两个数
  （1620 与 1643 减去同样的 27 个 skip），不是同一棵树的两种写法。

**但有一类写法不一致是真的问题**（审计报告里同一个测量值的千分位写法不统一）：
`1,588`（`m10-number-traceability.md:4`、`outreach-final-review.md:3`、
`outreach-recheck.md:5`、`new-pages-crosscheck.md:29/100/463`、
`final-outward-consistency.md:45`）与 `1588`（`ci-gate-coverage.md:148`、
`changelog-vs-release-notes.md:18/19/37/53`、`github-repo-metadata-proposal.md:78/80`）；
`7,117 / 7,631` 与 `7117 / 7631` 同理；CI job 数则有「十个 job」「9 个 job 定义」
「6 job / 7 并行」三种写法并存。**这些都在审计报告里**，改起来是机械活，
但**同一批报告自己就是"数字同源"的锚**，锚里写法不统一，下一轮还会继续漂。

---

## 4. 系统性问题

上一轮挖出 52 处，本轮挖出 **67 处**（A 6 + B 6 + C 16 + D 6 + E 10 + F 5 + G 7 + H 11）。
**数量没少**，但**性质变了**：上一轮的多是"改了脚本、忘了改文档"；本轮的多是
**"改了脚本，也改了脚本管得到的地方，但漏掉了脚本管不到的地方"**。

有五个系统性问题：

### 4.1 脚本的写集是四个文件，仓库里有二十八处抄它的数

`scripts/refresh-report-figures.py` 只写
`docs/reports/phase1-execution-report.md`、`docs/status.md`、
`README.md`、`README.zh-CN.md`（徽章 URL）。**其余每一处提到测试数/覆盖率/
指纹/徽章的地方都是手写的**——C 组 16 处、E 组 10 处、A 组 6 处全是。

**这不是某个人忘了，是缺一道机制**：现在只有**契约检查项数 49** 被
`tests/test_public_contracts.py:759` 钉住（`:765` 的清单把 6 份材料一起钉），
**测量数字一个都没有守卫**。

> 值得注意的一个反例：`docs/how-to-verify.md` 的 1643 / 1496 / 147
> **是被 `tests/test_how_to_verify.py` 钉住的**——它拿 `pytest --collect-only`
> 的真实汇总行比对，数字错则 CI 红。
> **同一个仓库里已经有"把活数字钉住"的先例**，只是没有推广到测量数字上。

**还有一个更细的缺口**：`docs/reports/social-preview-howto.md` **在**
`scripts/check-doc-citations.py:96` 的受检文档名单里（注释写得很清楚：
"a citation nobody checks is a citation nobody has to keep true"）。
但那个门禁只核**"被引用的那一行还是不是它说的那样"**，**不核"表格第一列抄的那个数
是不是那行里的数"**——所以 `social-preview-howto.md:74` 的 `1632` 与它引用的
`phase1-execution-report.md:76` 里的 `1643` 可以同时通过门禁。
**引用有效，值已过期**：这正是 C 组那两处的形状。

### 4.2 一次重测量要人手动改十几处，于是漏了

`9e1aa61` 这一次最终测量改了 6 个文件（`README.md`、`README.zh-CN.md`、
`docs/outreach/publish-review.md`、`phase1-execution-report.md`、
`v1.0.0-github-release-body.md`、`.github/social-preview.json`）。
**它把发版正文里的指纹改对了，把紧挨着的 `1642 passed` 漏了**——
指纹和通过数都在同一行（`:172`），手改一次、漏一次。

**同一批材料里还有两类漏网**：`docs/releases/v1.0.0.md`（完全没被碰）、
`docs/portfolio.md`（1,632 没跟上）。

### 4.3 一个数字有两三个分母，而文档把它们用同一个词写

- **CI 的 job 数**：`job 定义数`（10）vs `并行运行数`（11 on tag）——
  `docs/status.md`、发版清单、`docs/HANDOVER.md` 把它合写成「9 个 job / 10 次并行运行」
  或「six jobs (seven parallel runs)」，而 `portfolio.md` / `CLAUDE.md` 的
  「ten CI jobs (eleven runs on a tag)」是对的。
- **契约检查数**：`静态条数 49` vs `实跑条数 48`——
  `public-contracts.md:355` 与 `v1.0.0-github-release-body.md:267-269`
  **都**交代了分母，做得对；`portfolio-readiness-2026-11-18.md:148-149` 也交代了。
- **报告份数**：`文件数 61` vs `表格行数 68` vs `§1–§6 表行合计 60`——
  `docs/reports/README.md:3`、`:29`、`:42` **在同一页上**用了同一个词「份」。
- **M10 自查**：`自动化判定 43` vs `留人工 40` vs `验收包 40 项`——
  `v1.1.0-candidates.md:219`、`m10-selfcheck.md:25` 都已交代清楚，做得对；
  但 `next-engagements.md:411` 的「自查脚本 40/40」把前两个分母混成了一个。

### 4.4 审计报告的"行内断言"与"处方"会过期，而"基线声明"不会

`docs/reports/` 里的审计报告普遍带基线声明，**基线声明本身是对的**；
但表格里那些**行内断言**（`✅ 一致`、`数字与落盘报告一致 ✓`）说的是**现在**，
基线一走就失效——E 组 10 处全是这一类。

**更危险的是"处方"**（G 组 7 处）：审计报告里写着"该怎么改"的段落，
基线一变，处方本身就错了。`round-two-fresh-read.md:585` 的处方会把
`CLAUDE.md` 已经改对的 CI job 数**改回错的**；`denominator-and-tree-pass.md:154`
的处方会让人把 `docs/status.md` 写成 9 个 job——而真相是 10 个。
**处方比数字更该定期复核**：数字错了读者能发现，照着错的处方改则不会。

### 4.5 审计报告里的"已改 / 已同步 ✅"标签，本身也是需要复核的

`english-reader-review-2.md:874` 写「**已改**：分组份数按实际行数改齐，合计与总数对齐」——
实际没改齐（D 组）；`denominator-and-tree-pass.md:156` 写「**已同步** ✅」——
实际落后一轮（C 组）。**这两处"打勾"比它们检查的数字更危险**：
打勾意味着"这里不用再看了"。

---

## 5. 手写测量数字的位置清单（会随最终重测量自动变化 / 需要人改）

**脚本管得到的四个文件（本轮不列）**：
`docs/reports/phase1-execution-report.md`、`docs/status.md`（§1 快照表）、
`README.md`、`README.zh-CN.md`（顶部两个徽章的 URL 数字）。

**脚本管不到、必须人改的**（= C 组 + A 组 + E 组的实测值）：

| 文件:行 | 当前值 | 类型 | 有守卫测试吗 |
|---|---|---|---|
| `docs/releases/v1.0.0.md:90-91` | 1643 / **1642 passed** | 手写 | ❌ 无（`test_public_contracts.py` 只钉契约数 49） |
| `docs/releases/v1.0.0.md:94` | 93.3%（7135 / 7650 行） | 手写 | ❌ |
| `docs/reports/v1.0.0-github-release-body.md:164-167`、`:172`、`:264-266`、`:296`、`:301` | 1643 / **1642 passed** / 93.3% / 7,135·7,650 / `d0e85b61` | 手写 | ❌ |
| `docs/portfolio.md:67` | **1,632** tests | 手写 | ❌ |
| `docs/reports/social-preview-howto.md:73-75` | 7,135·7,650 / **1632** / **1485 快** | 手写 | ❌（`tests/test_social_preview.py` 只管图片与 `.json`） |
| `docs/reports/m10-reader-package.md:110-111` | **1593 passed, 27 skipped** / **1620 passed** | 手写 | ❌（27 这个 skip 数被 `m10_selfcheck.py` 钉着，**总数无钉**） |
| `docs/reports/m10-reader-kit.md:181` | **1593 passed, 27 skipped** / **1620 passed** | 手写 | ❌ 同上 |
| `docs/reports/m10-number-traceability.md:4-5` | **1,588 / 1,441 / 7,117·7,631 / `787282`** | 手写 | ❌ |
| `docs/reports/outreach-final-review.md:3-4` | **1,588（1,473 快）/ 7,117·7,631** | 手写 | ❌ |
| `docs/reports/outreach-recheck.md:5-6` | **1,588（1,441 快）/ 7,117·7,631** | 手写 | ❌ |
| `docs/reports/outreach-publish-checklist.md:40-41`、`:51-53` | **1,588 / 1,441 / 7,117·7,631** | 手写 | ❌ |
| `docs/reports/new-pages-crosscheck.md:29`、`:100`、`:463` | **1,588 / 1,441 / 1,561+27** | 手写 | ❌ |
| `docs/reports/next-engagements.md:419` | **1,612 / 93.3%** | 手写 | ❌ |
| `docs/reports/final-outward-consistency.md:45` | **1,588 / 1,441** | 手写 | ❌ |
| `docs/reports/github-repo-metadata-proposal.md:78`、`:80` | **tests-1588** | 手写 | ❌ |
| `docs/reports/m10-selfcheck.md:114` | **tests 1620** | 手写 | ❌ |
| `docs/reports/round-two-fresh-read.md:730` | **1632** | 手写 | ❌ |
| `docs/reports/readme-image-consistency.md:503-504` | **1632 / 1485** | 手写 | ❌ |
| `docs/reports/outreach-first-read.md:463-464` | **1,632 / 1485** | 手写 | ❌ |
| `docs/outreach/project-brief.md:50`、`:87` | 1,643 / 93.3% | 手写 | ❌ |
| `docs/outreach/cover-letter-templates.md:82` | 1,643 / 93.3% | 手写 | ❌ |
| `docs/outreach/publish-review.md:23-24` | 1,643 / 93.3%（7,135/7,650） | 手写 | ❌ |
| `docs/how-to-verify.md:147`、`:153-154` | 1643 / 1496 / 147 | 手写 | ✅ `tests/test_how_to_verify.py` 拿 `pytest --collect-only` 比对 |
| `docs/how-to-verify.zh-CN.md:120`、`:126-127` | 同上 | 手写 | ✅ 同上 |
| `docs/how-to-verify.md:167` / `.zh-CN.md:144` | 1616 passed, 27 skipped | 手写 | ❌ **不在**上面那个测试的覆盖范围内（它只查收集数，不查 passed/skipped） |
| `docs/how-to-verify.md:168` / `.zh-CN.md:145` | 1643 passed、0 skipped | 手写 | ❌ |
| `docs/how-to-verify.md:216` / `.zh-CN.md:193` | **documents read: 115 / 110**（真值 140） | 手写 | ❌ |
| `docs/how-to-verify.md:433` / `.zh-CN.md:405` | `<!--fig:tests.total-->1643<!--/fig-->` | 手写（**装饰性标记**） | ❌ |

**另有三个数不是测量值、但同样手写**（不受重测量影响、但会随代码长）：
CI 的 job 定义数与并行运行数（B 组 6 处）、
`docs/reports/README.md` 的三个"份数"（D 组 5 处）、
`docs/reports/ci-gate-coverage.md:49` 的 job 数（F 组）。

---

## 6. 本轮扫了什么、没扫什么

### 扫了

- `docs/` **全部**子目录（`reports/` 62 份 + `architecture/` + `roadmap/` +
  `releases/` + `outreach/` + `proposals/` + `benchmarks/` + `case-studies/` +
  `assets/` + `docs/` 根下 11 份）。
- `README.md`、`README.zh-CN.md`、`CHANGELOG.md`、`CLAUDE.md`、`AGENTS.md`、
  `CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`。
- `.github/workflows/ci.yml` 的 job 定义与触发条件（作为 CI 数字的真值）。
- `src/` 里的契约真值（工具数、命令数、端点数、退出码、报告 schema）。
- 三个**只读**复算：`check-version-claims.py --base auto`、`m10_selfcheck.py`、
  `check-doc-citations.py`；以及 `git ls-files "*.md"`。

### 没扫

- **没有跑 `pytest` / `coverage` / `refresh-report-figures.py`**——本报告不产生
  任何测量数字，测试数、覆盖率、指纹一律不判对错（§1）。
- **没有读 `.claude/worktrees/` 下的任何东西**（别的 checkout 的副本）。
- **没有联网**——CI 的实际运行结论（`gh run view`）无法复核，本报告只核
  **workflow 文件里定义的 job 数**，不核 GitHub 上跑出来的结论。
- **没有核 `docs/benchmarks/*.json` 里的 trace 原始数据**——`docs/benchmarks/*.md`
  的数字是脚本从 trace 重算生成的产物，报告里没有发现与 trace 矛盾的陈述；
  要核 trace 本身需要重跑那些脚本，不在本轮范围。
- **没有逐字复核 `docs/case-studies/attachments/*.json` 的字段**（上一轮已核过
  顶层 10 键；本轮只核了份数：4 个证据包 / 12 份报告文件，与
  `docs/case-studies/README.md:20-22` 一致）。
- **没有核 `scripts/` 内部逻辑**（只把它们当真值来源读）。
- **没有核 GitHub 上 `v1.0.0` 那次 run 的逐 job 结论**（只核了 workflow 的定义）。

### 哪些数字会随最终重测量自动变化、哪些不会

| | 会自动变 | 不会自动变（要人改） |
|---|---|---|
| **测量数字**（测试数 / 覆盖率 / 指纹 / 徽章） | `phase1-execution-report.md` 全部 `<!--fig:-->` 标记；`docs/status.md` §1 快照表；两份 README 的徽章 | **上表 §5 的 28 行里除 `how-to-verify` 三行以外的 25 行** |
| **契约数字**（11 工具 / 13 命令 / 23 端点 / 0–6 退出码 / 49 活检 / 10 报告顶层键 / schema 3） | 不会自动变 | 但 `scripts/verify-public-contracts.py` 一改，`tests/test_public_contracts.py:765` 的 6 份材料清单之外的地方仍会漏（上一轮漏过 4 处 MCP 工具数） |
| **CI 数字**（10 job / 11 runs） | 不会自动变 | **B 组 6 处** |
| **流程数字**（61 份报告 / 各项清单条目数） | 不会自动变 | **D 组 6 处** + F 组 4 处 + C 组 2 处（候选数 15、自查 43/43） |
| **样例输出里的活数**（`documents read`） | 不会自动变，**每加一份文档就变** | `how-to-verify.md:216` / `.zh-CN.md:193` |
| **审计报告里的"已改 / 已同步 / 处方"** | 不会自动变 | **G 组 7 处**——这类最容易被漏，因为它们看起来是"已完成的结论" |
| **新合并报告的"状态桶"** | 不会自动变 | **H 组 11 处**——文件在自己的 §3 里打了"已闭合"，摘要桶却没跟上 |

**一句话**：**测量数字里有 25 处是脚本管不到的手抄**——下一轮重测量会让它们
全部再旧一次；**CI 数字、流程数字与审计报告里的"处方/已改"标签都没有守卫**，
脚本长大或文件增减时它们静默腐烂。

---

## 7. 最要紧的三条

1. **`docs/releases/v1.0.0.md:91` 与 `docs/reports/v1.0.0-github-release-body.md`
   的 5 处写 `1642 passed`，而它们引用的报告记录块写 `1643 passed`。**
   同一颗 bullet 里「1643 个测试 / 1642 passed / 0 xfailed / 0 skipped」自相矛盾。
   回归发生在"最终测量落定"那一次提交 `9e1aa61`：指纹被手工改对了，
   紧挨着的通过数没改。**这是唯一一处会让对外承诺与仓库事实直接冲突的发现，
   而且它落在即将发布的两份材料上；三个门禁（引用核对、版本声明核对、契约计数）
   都不核这个数。**
2. **`docs/status.md:26`、`:50-51`、`:55-64`、`docs/reports/v1.0.0-release-checklist.md:60`、`:136-139`
   与 `docs/HANDOVER.md:148-151` 的 CI job 数少了 `social-preview`**
   （前两处说 9 个 job / 10 次并行运行，`HANDOVER.md` 说 six jobs / seven parallel runs；
   真值 10 个 / tag 11 次）。`docs/portfolio.md:68` 与 `CLAUDE.md:66` 已经是
   「ten CI jobs (eleven runs on a tag)」——**三处独立来源互相印证，
   `status.md`、发版清单与交接文档是唯一没跟上的三处**。
   发版清单是发版前要逐条打勾的东西，勾错一个数，勾出来的是假的；
   `HANDOVER.md` 是下一位接手的人要照着跑的东西，它现在只列了 6 个 job。
3. **`docs/reports/m10-reader-package.md:110-111` 与 `docs/reports/m10-reader-kit.md:181`
   告诉一位外部独立读者「报告里记录的那次完整测量是 `1620 passed`」**——那是两轮
   之前的数（现值 1643），同一句里的 `1593 passed, 27 skipped` 也同样过期。
   M10 独立验收**尚未开始**，这两份正是要交出去的那份。
   同一批里还有 `docs/how-to-verify.md:216` 与 `.zh-CN.md:193` 的
   `documents read: 115` / `110`（真值 **140**）——而该页自己写着
   「**`documents read` 那行是活的**」。

**此外两条不在前三、但同样要处理**：

- **G 组（7 处）：审计报告里的"处方"照做会写错。**
  `docs/reports/round-two-fresh-read.md:585`/`:607` 的处方会把 `CLAUDE.md`
  已经改对的 CI job 数**改回错的**；`denominator-and-tree-pass.md:154` 的处方
  会让人把 `docs/status.md` 写成 9 个 job。**数字错了读者能发现，照着错的处方改则不会。**
- **H 组（11 处）：三份新合并报告的"状态桶"已经过期。**
  `docs/reports/v1.1.0-candidates.md` 在自己的 §3 里给 C4 打了「**已闭合（2026-11-18）**」、
  C14 的脚本/测试/CI job 都已落地，**§0 的摘要桶却还写着「3 项已做完 / 1 项主体完成 /
  11 项未开始」**；而 `:55` 自称「这张表是 §0 各项数字的唯一出处」——
  **一份报告的状态与它自己的摘要对不上，读者第一眼看到的恰好是摘要。**
