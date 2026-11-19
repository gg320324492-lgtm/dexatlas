# 手写测量数审计：「数字随测量走」还差哪些

**本窗口是只读审计：未修改任何既有文件（除新增本报告），未运行任何项目测量。**
未运行 `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率），未跑 `pytest --cov`，
未 `uv sync`。只读手段：`grep` / `Read` / `git log` / 直接导入门禁脚本的函数做**内存内的漂移实验**
（把某个数改掉再喂给门禁，看它报不报——不改磁盘上的任何文件）。

- **审计基准**：本 worktree `cool-lamport-3cb292`，HEAD `0b98843`，分支 `claude/gracious-bassi-fc0d79`。
- **审计范围**：`docs/` 全部子目录 + 仓库根的 `README.md` / `README.zh-CN.md` / `CHANGELOG.md` /
  `CLAUDE.md` / `AGENTS.md` / `CONTRIBUTING.md` / `SECURITY.md`。
- **与并行会话的重叠**：散文里的手写数（`docs/how-to-verify.md` / `.zh-CN.md`）与社交预览卡片，
  已有另外两扇窗口在收进机制；本报告**不重复给方案**，只在清单里标出它们的位置与现状。

---

## 0. 判据：什么算「测量数」，什么不算

**算**：能被一次运行量出来的数。测试总数、快/集成拆分、通过/跳过/xfail 数、覆盖率（% 与
covered/total 行数）、CLI 子命令数、REST 端点数、MCP 工具数、自建样本数、契约检查项数、
CI job 数、每次分析产出的类/方法/证据条数。

**不算**：`Apache-2.0`、`v1.0.0` 这类常量与版本号（它们归 `scripts/check-version-claims.py` 管，
本报告不重复）；里程碑编号、日期、commit 号、行号；一次运行的**冻结记录**里的数（见 §4 C 类）。

一个数要算「测量数」，得满足两条：**它会随树的变化而变**（加一个测试、加一个端点、加一个
CI job），**而且它是对外的当前声明**（读者会照着它去核对）。只有第一条的是历史记录，
只有第二条的是说明文字。

---

## 1. 机制现状：谁在检什么

先把「门禁」这张表摆清楚，后面每一条清单都指回它。

| 门禁 | 跑在哪 | 它读哪些文档 | 它比哪些数 | 覆盖不到的 |
|---|---|---|---|---|
| `scripts/refresh-report-figures.py` | CI `measurement` job（**只在打 tag 时**跑） | 按 `<!--fig:…-->` 标记**发现**的所有文档（`docs/releases/`、`docs/outreach/` 除外） | 标记里的数 | 没有标记的散文；不带标记的表格行 |
| `scripts/check-release-numbers.py` | CI `release-numbers` job | `docs/how-to-verify.md`、`.zh-CN.md`（对**工作副本**的报告）；`docs/releases/<tag>.md`、`docs/reports/<tag>-github-release-body.md`、GitHub 上已发布的 release body（对**tag 树**的报告） | `tests.total/fast/slow`、`suite.passed/skipped/xfailed`、`coverage.pct`、`coverage.covered/total` | 除上列以外的任何文档 |
| `scripts/check-version-claims.py` | CI `lint` job | 全部 `.md`（版本声明 + 徽章）；`docs/outreach/`、`docs/case-studies/`、`docs/proposals/`（测试数/覆盖率/MCP 工具数/样本数） | 版本声明；`tests-*`/`coverage-*` 徽章 URL；对外素材里的测试数、覆盖率、工具数、样本数 | `docs/portfolio.md`、`docs/status.md`、`docs/HANDOVER.md`、`docs/glossary.md`、`docs/architecture/` |
| `scripts/check-doc-citations.py` | `tests/test_doc_citations.py` | `DOCS` 白名单（16+ 篇） | `文件:行号` 引用指向的符号 | 文档里的**数**；不在白名单的文档 |
| `scripts/make-social-preview.py --check` | CI `social-preview` job | `docs/reports/phase1-execution-report.md` | 卡片上的数与报告的数 | 卡片 PNG 的像素 |
| `scripts/check-contract-records.py` | CI `contracts` / `contracts-without-jadx` job | `docs/architecture/public-contracts.md` §7 | 契约活检的记录条数 | 别处复述这个数的文档 |
| `scripts/check-platform-gates.py` | `tests/` 里有测试跑它 | `scripts/platform-gates.json` | 本地门禁清单与 CI 门禁清单 | 散文里写的 job 数 |
| `scripts/check-gate-coverage.py` | CI `gate-coverage` job | `scripts/` + `.github/workflows/` + `tests/` | 每个门禁脚本有没有被跑 | 门禁**数目**在散文里的写法 |
| `scripts/check-m10-snapshot.py` | `tests/` 里有测试跑它 | M10 快照 | 自查条数、组数 | 状态页上复述的 `43/43` |
| `scripts/refresh-report-figures.py` 的测试文件表检查 | 同上（写之前） | `docs/reports/phase1-execution-report.md` §2.1 | 表里的**行**（文件名集合）与磁盘上的 `tests/test_*.py` | 行右边那句**说明** |

### 1.1 关键事实：标记机制只覆盖「标记过的文档」

`refresh-report-figures.py` 的 `documents_with_figures()` 是**按标记发现**文档的，
`FIGURE_EXCLUSIONS` 排除了 `docs/releases/`（历史）与 `docs/outreach/`（对外素材）。
所以：

- **在 `docs/` 里的任何散文**，只要没有 `<!--fig:…-->`，就完全在这套机制之外；
- **`docs/outreach/` 里的素材**由 `check-version-claims.py` 的 outward 规则管，
  但那套规则只认**几种写法**（见 §3 的 B3）。

---

## 2. 清单 A：有门禁守着的（陈旧了会被抓）

| # | 是什么数 | 在哪 | 谁在检 | 陈旧了会怎样 |
|---|---|---|---|---|
| A1 | 测试总数/快慢拆分/套件通过跳过/coverage | `docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` | `refresh-report-figures.py` 写；`tests/test_docs.py::test_execution_report_numbers_match_the_code` 按源码指纹比对；CI `measurement` job 在 tag 上重算 | **门禁先红**，挡住更新——正是那三个闭环的形状。改数要走脚本 |
| A2 | 同上（状态页） | `docs/status.md:23-24` | 同 A1；同一套标记机制是 `scripts/refresh-report-figures.py` 的 `documents_with_figures()` 按标记发现文档 | 同 A1 |
| A3 | 测试数 / 覆盖率**徽章** | `README.md:12-13`、`README.zh-CN.md:12-13` | `refresh-report-figures.py` 写 URL；`check-version-claims.py::check_badges` 读 URL 里的数与测量比 | 徽章过期 → badge 门禁红 |
| A4 | 测试数/拆分/套件数（散文） | `docs/how-to-verify.md:147,172`、`.zh-CN.md:120,149` | `check-release-numbers.py` 的「工作副本」段；`tests/test_how_to_verify.py::test_the_page_states_the_numbers_the_suite_has` | 门禁先红。**但**：另一扇窗口正在把这两页的散文改成标记（改法见该窗口的交接），改的过程中 `tests/test_how_to_verify.py:36` 的 `STATED_NUMBERS` 形状要求会挡路——**本报告不动这两页** |
| A5 | 测试文件表（§2.1 的文件名集合） | `docs/reports/phase1-execution-report.md:150-…` | `tests/test_docs.py::test_execution_report_lists_every_test_file`（集合相等）；`refresh-report-figures.py` 写之前也比一次 | 加一个测试文件 → 门禁先红 → 必须补一行。表右边那句**说明**没人检（见 B10） |
| A6 | 已发布 release 的数（tests/coverage/套件） | `docs/releases/v1.0.0.md`、`docs/reports/v1.0.0-github-release-body.md`、GitHub 上已发布的 release body | `check-release-numbers.py` 的「已发布 release」段，对 **tag 树**的报告比 | 门禁先红。**这是对的**：release 说的是它自己那棵树测出来的数 |
| A7 | 对外素材的测试数/覆盖率/MCP 工具数/样本数 | `docs/outreach/`、`docs/case-studies/`、`docs/proposals/` | `check-version-claims.py::check_outward_numbers`（`OUTWARD_DIRECTORIES`） | 门禁先红。**但这套规则只认几种写法**——见 B3 |
| A8 | 契约活检的记录条数 | `docs/architecture/public-contracts.md` §7 | `check-contract-records.py`（CI `contracts` job 实跑后对记录） | 门禁先红 |
| A9 | 基准对比报告的数 | `docs/benchmarks/comparison.md` | CI `m3-comparison` job 从提交的 trace **重新生成**并逐行比对 | 重生成结果不同 → 门禁先红 |
| A10 | 报告/文档里的 `文件:行号` 引用 | 16+ 篇在 `check-doc-citations.py` 的 `DOCS` 白名单里 | `tests/test_doc_citations.py` 调 `check-doc-citations.py` 的 `main()` | 门禁先红 |

---

## 3. 清单 B：没人守的（陈旧了静默——这一类才是真风险）

下面每一条都附了「核法」：怎么确认**真的**没人检。核法分两种：

- **核法一（查门禁清单）**：`grep -rn "<文件名>" scripts/*.py tests/*.py .github/workflows/*.yml`
  ——门禁脚本里没有提到这个文件，就是没人读它。
- **核法二（内存漂移实验）**：直接 import 门禁脚本，把它读的文本在**内存里**改掉一个数
  （不改磁盘），看它报不报。这一条是决定性的：它证明的不是「门禁没提到这个文件」，
  而是「门禁就算读到了这个数，也认不出来 / 不去比它」。

### B1 ★★★ `docs/portfolio.md` 的四个数 —— 整页没人守

- **是什么数**：`docs/portfolio.md:67` 的 `1,695 tests at`；`docs/portfolio.md:68` 的 `93.3% coverage`；
  `docs/portfolio.md:68` 的 `thirteen CI jobs (fourteen runs on a tag — the test job is a 3.12/3.13 matrix)`；
  另加 `docs/portfolio.md:48` 的 `Eleven tools over stdio`。
- **谁在检**：**没人**。核法一：`grep -rn "portfolio" scripts/*.py tests/*.py .github/workflows/*.yml`
  → 零命中。`docs/portfolio.md` 不在 `check-release-numbers.py` 的 `VERIFY_DOCUMENTS`，
  不在 `check-version-claims.py` 的 `OUTWARD_DIRECTORIES`，不在 `check-doc-citations.py` 的
  `DOCS`，也不在 `refresh-report-figures.py` 的标记文档里（这页一个 `<!--fig:…-->` 都没有）。
- **核法二（决定性）**：`check-release-numbers.py` 的**抽取器**其实**看得见**这一页的数——
  我在内存里跑 `extract()`，它从 `docs/portfolio.md` 里读出
  `tests.total = 1695 (line 67)` 与 `coverage.pct = 93.3 (line 68)`。
  门禁**看得见，只是没有被指到这一页**：`main()` 的 source 列表只有 `VERIFY_DOCUMENTS`
  两页 + 三份 release 文档。
  漂移实验：把 `1,695` 改成 `1,999`，喂给 `compare()` → 8 条 finding
  （`tests.total mismatch expected 1733 found 1999`）；但门禁**从来没对这一页跑过 compare**。
- **陈旧了会怎样**：**已经陈旧了**。`1,695` 是老树上的数，当前是 `1,733`（`tests.total`）。
  `93.3%` 与 `thirteen CI jobs` 今天还是对的（CI 现在恰好 13 个 job，tag 上 14 个 run），
  但同样没人守。**读者会照着核对**：这一页是「给客户看的作品集描述」，
  读者拿着 `1,695` 去数测试就数不对。
- **该怎么做**：**改成标记 / 加进门禁**。这一页是当前声明，不是历史记录。
  推荐：把 `1,695` 与 `93.3%` 换成 `<!--fig:tests.total-->` / `<!--fig:coverage.pct-->`
  （`refresh-report-figures.py` 会自动发现并写它，`documents_with_figures()` 按标记发现文档，
  不需要改脚本）；`thirteen CI jobs` 与 `Eleven tools` 属于「代码事实」，
  要么也进标记（`cli.commands`、`api.endpoints` 已有先例，`samples.apks` 也有；
  MCP 工具数与 CI job 数**目前没有对应的键**，需要先加键），要么另设门禁。
  **不要**只把 `1,695` 手改成 `1,733`——那只是把一个没人守的数换成另一个没人守的数。

### B2 ★★★ 两页「怎么复核」里**另一个环境**那一行的数

- **是什么数**：`docs/how-to-verify.md:171` 的 `1664 passed, 31 skipped`，
  同行的 `27 个 skip` 与 `（25 条）`/`（2 条）` 的理由拆分；
  `docs/how-to-verify.zh-CN.md:148` 的同两个数（理由只有一种写法）。
- **谁在检**：**没人**——但原因不是「门禁没提到这一页」，而是**门禁主动放过了它**。
  `scripts/check-release-numbers.py` 的 `_OTHER_ENVIRONMENT`（`scripts/check-release-numbers.py:206`）把「**没**取第三方样本」这类
  块整块跳过（`scripts/check-release-numbers.py:403`）：那是另一个环境的测量，不是这次发布声称的那次。
  核法二：我 import 了这个脚本，在内存里把 `1664 passed` 改成 `2999 passed`、
  把 `31 skipped` 改成 `77 skipped`，`extract()` 读出来的族
  **一行都没变**（仍然是 `docs/how-to-verify.md:147` 的 tests.total/fast/slow 与 `docs/how-to-verify.md:172` 的 suite 三项）；
  跑整条门禁（`scripts/check-release-numbers.py`）退出码仍是 0。
- **陈旧了会怎样**：**静默**。套件每加一个测试，这一行的三个数就全错；
  而这一行恰恰是「读者照着跑一遍、对不上数字」时会去看的那一行。
  **差多远**：这一行写 `1664 passed`，而报告记的那次测量是 `1731 passed`，
  这棵树上现在收集到的是 **1744**（1595 快 + 149 集成）——**这一行落后了 80 个测试**，
  而 `docs/how-to-verify.md:172` 那一行（被守着的）只落后 13 个。**同一张表，一行被守着、一行没有。**
  **另一扇窗口正在把这两页的散文改成标记，但改的是 `docs/how-to-verify.md:147` 与
  `docs/how-to-verify.md:172`（有标记键的那几处），
  这一行没有对应的键**——`suite.*` 键记的是「取了样本」那一次的测量，
  「没取样本」那一次是**另一个口径**，现在没有键能记它。
- **附带发现（中优先级）**：英文版把 27 条 skip 拆成**两种理由**（25 + 2），
  中文版说 27 条**全是**一种理由。两页对同一次测量给了两种拆法，都没人检。
- **该怎么做**：**另设门禁 / 加一个键**。要么给 `refresh-report-figures.py` 加一个
  「无第三方样本环境」的测量段（它是另一次运行，成本高、要单独跑），
  要么把这一行降级成「不写具体数」——只说「套件会因为缺样本跳掉一批」，
  让读者自己去数。**不要**照抄现在的数往上加，那正是手抄的下场。

### B3 ★★ `docs/outreach/publish-review.md` 的汇总列 —— 对外门禁认不出的写法

- **是什么数**：`docs/outreach/publish-review.md:50-53` 最右列的 `1,695 / 93.3%`（共 4 处），
  `docs/outreach/publish-review.md:342` 与 `docs/outreach/publish-review.md:406` 的 `1,695 / 93.3%`。
- **谁在检**：**没人**。`docs/outreach/` 确实在 `check-version-claims.py` 的
  `OUTWARD_DIRECTORIES` 里，但 outward 规则**只认带单位的写法**：
  `TESTS_STATED`（`scripts/check-version-claims.py:203`）要 `N tests`；
  中文写法 `N 个测试` 由 `OUTWARD_TESTS_CN`（`scripts/check-version-claims.py:142`）认；
  `COVERAGE_STATED`（`scripts/check-version-claims.py:189`）要附近出现 `coverage` / `覆盖率` 字样。
  `1,695 / 93.3%` 两者都不满足。
  核法二：我 import 了 `check-version-claims.py`，把 `publish-review.md` 内存里的
  `1,695` 全改成 `1,999`，再跑 `check_outward_numbers()` →
  **0 条 finding**（改之前也是 0 条）。
- **陈旧了会怎样**：**已经陈旧**（应为 `1,733`），而且**静默**。
  这份文件是**对外素材的审阅记录**，右边那列写的正是「这一轮应该是什么数」——
  它是给发出去之前核对用的，读者（发稿人）会照着它核。表格里**前两列的旧数是故意的**
  （`~1,540` 是「修正前」；第 3 列是同一栏的「替换后」措辞）——两列都被反引号包着，
  按 outward 规则的**设计**豁免（见 §5.3），**不是缺口**；
  **缺口是最右列**：`1,695 / 93.3%` 没有反引号（不是引文），却因为**写法**没人认。
  `docs/outreach/publish-review.md:342` 与 `docs/outreach/publish-review.md:406` 是同样的两处散文。
  （对照：`docs/outreach/project-brief.md:50` 与 `docs/outreach/project-brief.md:87` 现在写的是 `1,733`，**被 outward 规则守得住**。
  也就是说同一批对外素材里，被守的那两页是对的，没被守的这张审阅表是错的。）
- **该怎么做**：**另设门禁**（扩 outward 规则的写法，让 `N / P%` 这种「数 / 覆盖率」也算），
  或**改写**成能被认出的写法（`1,695 tests, 93.3% coverage`）。
  **不要**手改数字——那正是这一轮三个闭环的成因。
  **也不要**动第 3 列的写法：它被反引号包着是有意为之的区分（引文 vs 声明）。

### B4 ★★ CI job 数：五份文档各写一遍，没有一处有人比

- **是什么数**：`CLAUDE.md:79` 与 `AGENTS.md:79`（孪生文件，逐字相同）的
  `CI runs thirteen jobs (fourteen parallel runs on a tag — the test job is a 3.12/3.13 matrix)`；
  `docs/portfolio.md:68` 的同一句；`docs/status.md:50` 的 `CI 的十三个 workflow job`；
  `docs/HANDOVER.md:148` 的 `thirteen jobs (fourteen parallel runs on a tag push, thirteen on a push or a PR)`。
- **谁在检**：**没人**。核法一：`check-gate-coverage.py` 数的是**门禁脚本**有没有被跑，
  不是 **job** 数；`check-platform-gates.py` 会打印 `PASS 13 CI jobs are declared`，
  但那是它**自己算出来的**，不是拿它跟散文里的 `thirteen` 比；
  `scripts/platform-gates.json` 里明确写着「Nothing here is a count: a job added tomorrow
  is one more entry, not a number to edit」——它按 job 逐个登记，不登记数目。
  `check-version-claims.py` 只管版本号，不管 job 数。
- **陈旧了会怎样**：**静默**。今天 13 个 job（`ci.yml` 里 13 个 job 键，tag 上 `test` 是 3.12/3.13 两格 → 14 个 run），
  五处都写对了；**加一个 job 就全错**，而没有任何一处在等。
  **读者会照着核对**：CI 贡献者会数 `.github/workflows/ci.yml` 的 job 数。
- **该怎么做**：**另设门禁**。`check-platform-gates.py` 已经算得出这个数
  （它打印「13 CI jobs are declared」），让它**比**散文里写的那个数，
  或者让 `platform-gates.json` 记一条 `ci_job_count: 13` 并由它比。
  写成标记不合适——CI job 数不是 `refresh-report-figures.py` 的测量对象，
  硬塞进去会让「测量」这个概念变味。

### B5 ★★ MCP 工具数（11）：对外守住了，项目自己的页没守住

- **是什么数**：`docs/portfolio.md:48` 的 `Eleven tools over stdio`；
  `docs/HANDOVER.md:29` 的 `eleven tools`；`docs/status.md:256` 的 `十一个工具`。
- **谁在检**：**部分**。`check-version-claims.py` 的 `mcp_tool_count()`（`scripts/check-version-claims.py:1337`）
  读 `src/dexatlas/mcp/server.py` 数 `@server.tool`，但它只在 `check_outward_counts()`
  里用，而那个函数**只对 `OUTWARD_DIRECTORIES` 跑**（`docs/outreach/`、`docs/case-studies/`、
  `docs/proposals/`）。`docs/case-studies/api-integration.md` 的第 48、285、295 行
  （`what its eleven tools are` / `The eleven tools:` / `the server offers 11 tools:`）
  因此**有人守**（漂移实验 E5：把 `eleven` 改成 `nine` → 3 条 `outward-mcp-tools`）；
  `docs/portfolio.md`、`docs/HANDOVER.md`、
  `docs/status.md` 的那三处**没人守**。
  核法一：`grep -rn "portfolio\|HANDOVER" scripts/check-version-claims.py` → 不在 `OUTWARD_DIRECTORIES` 里。
  一处小例外：`docs/case-studies/api-integration.md:34` 的 `eleven read-only tools` 也不被认；
  `MCP_TOOLS_STATED`（`scripts/check-version-claims.py:166`）要求数字后面紧跟 `tools`。
  但同一页第 48、285、295 行认得住。
- **陈旧了会怎样**：**静默**。今天 11 个，是对的；给 MCP 加一个只读工具，那三处就错了。
- **该怎么做**：**加键或扩门禁**。`refresh-report-figures.py` 的 `render_figures()`
  （`scripts/refresh-report-figures.py:1108`）已有 `cli.commands` / `api.endpoints` / `samples.apks` 三个「代码事实」键，
  加一个 `mcp.tools` 是同一形状的事；或者把 `check_outward_counts()` 的适用范围
  从 `OUTWARD_DIRECTORIES` 放宽到「任何写了工具数的文档」。

### B6 ★ 契约检查项数（49）：权威处有人守，复述处没人守

- **是什么数**：`docs/architecture/public-contracts.md:365` 的
  `检查项清单共 49 项：28 REST + 6 MCP + 15 CLI`（§7 的记录）；`docs/glossary.md:186` 的
  `静态条数…（49）；实跑条数…（48 或 47，依可用后端而定）`。
- **谁在检**：**§7 有人守**（`check-contract-records.py` 实跑后对记录，
  CI `contracts` / `contracts-without-jadx` 两个 job）。**`docs/glossary.md` 没人守**：
  核法二，`check-version-claims.py` 的 `extract()` 在 `docs/glossary.md` 上读出**零个数**
  （`49` 不属于任何一族）；`check-doc-citations.py` 的 `DOCS` 白名单里也没有 `docs/glossary.md`
  （它只有 `文件:行号` 引用的检查，跟数无关）。
- **陈旧了会怎样**：**静默**。今天是 49，对的；`verify-public-contracts.py` 加一个 `check()`
  调用点，§7 会红而 glossary 不会。
- **该怎么做**：**加键或扩门禁**（让 glossary 引用 §7 的那个数，而不是复述它）。
  `docs/glossary.md` 自己就是「只管词不管数」的页——**这正好是它的设计**，
  所以这里更像是**设计违规**：它在 `docs/glossary.md:199` 明说「手抄会立刻过期；这一页只管词不管数」，
  却在 `docs/glossary.md:186` 手抄了一个数。**最省事的修法是把 `docs/glossary.md:186` 的数字改成指向 §7 的引用。**

### B7 ★ 分析出证条数：跑一次的结果被写进了「当前行为」的文档

- **是什么数**：`docs/analysis-provenance.md:398-402` 那张五个样本的分析表
  （类/方法/交叉引用/证据/字符串/资源/反编译成功）；`docs/analysis-provenance.md:411` 的 `五个样本、40 条证据，三种 kind`；
  `docs/analysis-provenance.md:850` 的 `在这 5 个自建样本上，JADX 一次都没失败`。
- **谁在检**：**没人**。`scripts/check-doc-citations.py` 的 `DOCS` 白名单（`scripts/check-doc-citations.py:164`）
  里有 `docs/analysis-provenance.md`，但它检的是**行号引用**，不检这张表的数；
  `check-version-claims.py` 的 outward 规则不覆盖 `docs/`（只覆盖 `docs/outreach/`、
  `docs/case-studies/`、`docs/proposals/`）。
- **陈旧了会怎样**：**静默**。这些数是**当前代码**在五个样本上的产出——
  证据条数尤其随管线改动而变；读者按这一页的分析结果去核对，就会对不上。
  严格说它们是「一次运行的记录」，但记录的是**今天**的行为，不是某个 tag 的行为，
  所以归在这一类而不是 C 类。
- **该怎么做**：**留着手写，但标明它是一次运行的记录**（写清跑的是哪个 commit / 哪次测量），
  或者给它一个脚本重算的入口（仓库里已有 `examples/` 的五个样本与 `scripts/generate-large-apk.py`，
  跑一遍分析就能得到这张表）。**不要**把它当「当前的数」继续往上加。

### B8 ★ 基准对比（真模型那次）的断言条数

- **是什么数**：`docs/status.md:293` 的
  `DexAtlas 45 条非空断言中 43 条带 grounded + locator；A/B 的 86 条全部不溯源（0/86）；
  agent 的 2 条不带 locator 的断言即 4.4% 的无支撑率`；
  以及 `docs/benchmarks/comparison-real.md`、`docs/benchmarks/comparison-stronger.md` 里的数。
- **谁在检**：**部分**。CI `m3-comparison` job 从 `docs/benchmarks/comparison-traces.json`
  重新生成 `docs/benchmarks/comparison.md` 并逐行比对（`comparison.md` 有人守）。
  但 `comparison-real.md` / `comparison-stronger.md` 用的是**另外的 trace 文件**
  （`comparison-real-traces.json`），CI 不重生成它们 → **没人守**；
  `docs/status.md:293` 复述它们的数 → **也没人守**。
  核法一：`grep -n "comparison-real\|comparison-stronger" .github/workflows/ci.yml` → 只有 `comparison-traces.json`。
- **陈旧了会怎样**：**静默**。这些是一次真实模型运行的记录，理论上不随代码变；
  但它们**由脚本从 trace 重算**（`docs/status.md:141` 自己这么说：
  「全部数字由脚本从 `m6-level2-traces.json` 重算」），
  也就是说**有重算的机制，只是没有人在跑**。
- **该怎么做**：**留着手写 + 另设门禁**（把 `comparison-real` 的重算也接进 `m3-comparison` job，
  就像 `comparison.md` 那样）。`docs/status.md:293` 那一句改成引用报告里的数。

### B9 ★ M10 自查条数（43/43）

- **是什么数**：`docs/status.md:145` 的 `43/43 通过`。
- **谁在检**：**间接**。`check-m10-snapshot.py` 打印
  `PASS the counts agree: 43 passed, 0 failed, 40 left for a human`——
  它比的是**快照与脚本**的条数，不是状态页上写的那个数。核法一：
  `grep -rn "43/43" scripts/ tests/` → 无命中；`grep -n "status.md" scripts/check-m10-snapshot.py` → 不在它的文档清单里。
- **陈旧了会怎样**：**静默**。今天 43/43，对的；自查脚本加一条检查，状态页就错了。
- **该怎么做**：**留着手写，但改成引用**（指向 `docs/reports/m10-selfcheck.md` 的记录，
  或让 `check-m10-snapshot.py` 多比一处）。**优先级低**：自查条数变动不频繁，
  且状态页那一格本身还带着「验收未开始」的定性。

### B10 ★ 测试文件表右边的「说明」

- **是什么数**：不是数，是**描述**——`docs/reports/phase1-execution-report.md:153-…`
  每行右列写「这个测试文件覆盖什么」。
- **谁在检**：**没人**。`test_execution_report_lists_every_test_file` 只比**文件名集合**；
  `refresh-report-figures.py` 的 `test_file_table()` 也只比集合。
- **陈旧了会怎样**：**静默**。某个测试文件改了职责，表里的说明不会跟着改——
  读者照着说明去读测试文件，会读到不一样的东西。这不是数，但它是同一类问题：
  **读者会照着核对，而没有人比**。
- **该怎么做**：**留着**（说明是人的判断，脚本判不了），但这已经是那三个闭环之一的
  边界——那一扇窗口在收进机制，**本报告不重复给方案**。

---

## 4. 清单 C：故意手写的（历史记录 / 对外素材，由别的门禁比或本来就该冻结）

| # | 是什么 | 在哪 | 为什么留着 |
|---|---|---|---|
| C1 | 各次 release 的测试数/覆盖率 | `docs/releases/v0.1.0.md` … `v1.0.0.md`、`CHANGELOG.md` 的各版本段、`docs/reports/v1.0.0-github-release-body.md`、GitHub 上已发布的 release body | **历史记录**：release 说的是它自己那棵树测出来的数。`check-release-numbers.py` 对 **tag 树**的报告比——它验的正是「发出去的那些数有没有被后来的树改掉」 |
| C2 | 已发布 release 的对外素材 | `docs/outreach/publish-review.md` 里**前两列**的「修正前」数（`~1,540 automated tests, 93.1% coverage`） | 故意保留的对照。反引号包着的旧数被 outward 规则豁免（`tests/test_version_claims.py:1081` 记着这个豁免） |
| C3 | 基准运行的记录 | `docs/benchmarks/m6-level2-*.md`、`task-set.md`、`service-regression-set.md`（92 题、20 题、49/60、853,103 tokens …） | **一次运行的冻结记录**：题目冻结在某个 commit 上，成绩是那一次跑出来的。`docs/benchmarks/comparison.md` 另有 CI 重生成守着；`comparison-real.md` 的缺口见 B8 |
| C4 | 审核 / 评估的记录 | `docs/status.md:27,110,111,123`（`5.50 / 10`、44 条发现、十五个缺陷）、`docs/reports/phase1-maturity-assessment.md`、`docs/reports/*` 里的绝大多数数 | 某次审核的结论，不是当前的树的状态。`docs/status.md:27` 自己就写着「今天的分数要重跑才有」——**这句是诚实的** |
| C5 | 里程碑 / 日期 / 版本号 | `docs/roadmap/`、`docs/HANDOVER.md:18,23`、各处 `v0.x.y` | 不是测量数 |
| C6 | 行号引用 | 各文档的 `文件:行号` | 不是测量数；由 `check-doc-citations.py` 管（在白名单里的那 16+ 篇） |

---

## 5. 「真的没人守」的核法

### 5.1 查门禁清单（最省事，先做这一步）

```bash
grep -rn "<文件名>" scripts/*.py tests/*.py .github/workflows/*.yml
```

零命中 → 没人读这个文件。这是 **必要条件**，不是充分条件——
`docs/how-to-verify.md` 在 `check-release-numbers.py` 里，但它**主动豁免**了其中一行（见 B2）。

### 5.2 内存漂移实验（决定性的一步）

门禁读的是磁盘上的文件，但门禁的**判定逻辑**是可以单独调用的。
做法：import 门禁脚本，把它的输入在**内存里**改掉一个数，看它报不报。
**磁盘上一个字都不改**，所以这是只读的。

```python
import importlib.util, sys

spec = importlib.util.spec_from_file_location("crn", "scripts/check-release-numbers.py")
m = importlib.util.module_from_spec(spec)
sys.modules["crn"] = m
spec.loader.exec_module(m)

auth = m.read_authority()  # 当前工作副本报告里的数
name = "docs/portfolio.md"
text = Path(name).read_text(encoding="utf-8")
drifted = text.replace("1,695", "1,999")  # 只在内存里改
src = m.Source(name, drifted)
claims, _ = m.extract(src, auth)  # 抽取器看得见吗？
print({k: [c.value for c in v] for k, v in claims.items()})
print(m.compare(src, claims, auth, "probe"))  # 比对器会不会报？
```

本轮实际跑出来的结果：

| 实验 | 输入 | 结果 |
|---|---|---|
| E1 | `docs/portfolio.md` 的 `1,695` → `1,999` | `extract()` 读出 `tests.total = 1999`；`compare()` 报 **8 条** finding——**但 `main()` 从不对这一页跑 compare**（它不在 `VERIFY_DOCUMENTS` 里）→ **实际 0 条** |
| E2 | `docs/how-to-verify.md` 的 `1664 passed` → `2999 passed` | `extract()` 读出的族**完全没变**（豁免）→ **实际 0 条** |
| E3 | `docs/outreach/publish-review.md` 的 `1,695` → `1,999` | `check_outward_numbers()` → **0 条**（写法 `N / P%` 不被 outward 规则认） |
| E4 | `docs/how-to-verify.md` 的 `**1733**` → `**1999**`（对照组） | `tests.total mismatch expected 1733 found 1999` → **1 条**，证明实验本身有效 |
| E5 | `docs/case-studies/api-integration.md` 的 `eleven` → `nine`（对照组） | `outward-mcp-tools` × 3（第 48、285、295 行）→ **3 条**，证明 outward 规则在它覆盖的文档上是有效的 |

E4 与 E5 是对照组：它们证明这套漂移实验**能**抓到漂移，所以 E1–E3 的「0 条」是真的没人守，
不是实验没搭好。

### 5.3 `docs/outreach/publish-review.md` 那一列为什么没人抓——查清了

我一开始把第三列当疑点（它写着 `` `1,695 automated tests, 93.3% coverage` ``，
按 outward 规则的写法**应该**被认出来），查下来是**两栏各自的道理**：

| 栏 | 内容 | 为什么没被抓 |
|---|---|---|
| 第 2 栏 | `` `~1,540 automated tests, 93.1% coverage` `` | **故意的**：它是「修正前」的旧措辞，按 outward 规则的**设计**豁免（`BACKTICKED`：反引号包着的是「被替换掉的旧措辞」）。这是 C2，不是缺口 |
| 第 3 栏 | `` `1,695 automated tests, 93.3% coverage` `` | **同一类豁免**：它也被反引号包着（我查了 `quoted_spans()`：第 50–53 行的反引号区间覆盖了第 3 栏）。所以**不是规则没认出来，是它被当成引文放过了** |
| **第 4 栏（最右）** | `1,695 / 93.3%`（**没有反引号**） | **这才是缺口**：`TESTS_STATED`（`scripts/check-version-claims.py:203`）要 `1,695 tests` 或 `1,695 个测试`，`COVERAGE_STATED`（`scripts/check-version-claims.py:189`）要附近出现 `coverage`/`覆盖率`——`1,695 / 93.3%` 两者都不满足 |
| `docs/outreach/publish-review.md:342`、`docs/outreach/publish-review.md:406` | `1,695 / 93.3%`（散文，无反引号） | 同上：**写法**不被认 |

**结论**：第 4 栏与 `docs/outreach/publish-review.md:342`/`docs/outreach/publish-review.md:406` 才是真缺口（B3 说的就是这三类）。
第 3 栏虽然也是 `1,695`，但它被反引号豁免是**规则的既定设计**
（`tests/test_version_claims.py:1081` 记着这个豁免）——修 B3 时**不要动第 3 栏的写法**，
动了反而会把「引文」变成「声明」，那是有意为之的区分。

---

## 6. 优先级

按「**静默过期** 且 **读者会照着核对**」排：

| 序 | 项 | 为什么是这个顺序 |
|---|---|---|
| 1 | **B1 `docs/portfolio.md`** | **已经过期**（`1,695` vs `1,733`）＋ 整页零门禁 ＋ 这一页是**给外部读者看**的作品集描述，读者一定照着数。门禁的抽取器已经能读出它的数，只差把这一页指进去——改造成本最低、收益最高 |
| 2 | **B2 两页「怎么复核」的另一个环境那一行** | **已经过期**（`1664/31/27` 是老树上的数）＋ 静默 ＋ 这是「读者照着跑一遍对不上数」时**第一个会去看的表**。它没有对应的标记键，所以另一扇窗口的改法**覆盖不到它**——两扇窗口之间有个洞 |
| 3 | **B3 `docs/outreach/publish-review.md` 的汇总列** | **已经过期** ＋ 静默 ＋ 这是**发出去之前**核对用的那一列。对外素材里有个门禁认不出的写法，是「对外那一层」的漏洞，比内部页更显眼 |
| 4 | **B4 CI job 数（五处）** | 今天还对，但**五处重复**、都静默；加一个 job 就五处一起错。读者（贡献者）会数 job 数。修法现成：`check-platform-gates.py` 已经在算这个数 |
| 5 | **B5 MCP 工具数（三处）** | 今天还对，静默；`docs/case-studies/` 那几处有人守，三处项目自己的页没有。修法与 B4 同形 |
| 6 | **B6 契约检查项数（glossary）** | 今天还对，静默；而且这一页**自己写着「只管词不管数」**却抄了一个数——设计违规，最便宜的修法是改成引用 §7 |
| 7 | **B8 基准对比的断言条数** | 有重算机制只是没人在跑；接进 `m3-comparison` job 即可 |
| 8 | **B7 分析出证条数** | 静默；但它是「一次运行的记录」，改成「标明那次运行」比「让它永远对」更诚实 |
| 9 | **B9 M10 自查条数** | 静默；变动不频繁，优先级最低 |
| 10 | **B10 测试文件表的说明** | 不是数；同一扇窗口的边界，不重复 |

---

## 7. 这一轮做了什么 / 没做什么

**本窗口做的**：

- 一次**只读**的全库审计，产出了本报告（`docs/reports/handwritten-numbers-audit.md`，本窗口唯一的新文件）。
- 核法本身是可复跑的：§5.2 的内存漂移实验（不改磁盘）＋ §5.1 的 grep 清单。
- **本报告自己的引用经得起引用检查器**：把它临时挂进 `check-doc-citations.py` 的 `DOCS`
  名单跑一遍（内存里挂，磁盘不改），`drifted: 0`、`unresolved: 0`。
  做法是**行号与符号分开写**：行号引它所在的那个文件（`scripts/check-version-claims.py:203`），
  符号提到**它所在的文件**（`TESTS_STATED`）；并把每一处裸写行号（`:142`）补成完整路径。
  顺带查出一处**引错了文件**：`_TEST_COUNT` 与 `_COVERAGE_PCT` 属于
  `scripts/check-release-numbers.py`，不属于 `scripts/check-version-claims.py`；
  outward 规则用的是后者里的 `TESTS_STATED` 与 `COVERAGE_STATED`——已改正。
- 门禁跑过并全绿：`ruff check .`、`ruff format --check .`、`mypy`、
  `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80`（退出 0）、
  `scripts/check-doc-citations.py`（`drifted: 0`）、`scripts/check-version-claims.py --base auto`（退出 0）、
  `scripts/check-release-numbers.py`（退出 0）、`scripts/check-platform-gates.py`（退出 0）、
  `scripts/check-m10-snapshot.py`（退出 0）。
- 文档相关的测试跑了（`test_docs` / `test_figures_auto_write` / `test_doc_citations` /
  `test_version_claims` / `test_release_numbers` / `test_status_figures` / `test_how_to_verify`）：
  **197 passed, 10 failed**。那 10 条**与本报告无关**——我把本报告移走再跑一遍，
  **同样这 10 条红**。它们是两件别的事：
  - **9 条是测量过期**：报告里记的是 `1733`（1584 快 + 149 集成），
    而这棵树上现在收集到 **1744**（1595 + 149）——上一次测量之后别的窗口加了 11 个测试。
    这正是 A1 说的那种「门禁先红」：它工作正常，只是还没人去重测。
  - **1 条是相对链接断了**：`docs/reports/m10-material-fixes.md` 等别的窗口的 M10 材料
    指向 `m10-acceptance-pack.md:13` 这类带行号的链接，那些文件不在树里。
  **本报告没有新增测试，也没有改动任何被这些测试读的文件。**

**本窗口没做（留给主会话或别的窗口）**：

- **没改任何既有文件**。B1–B10 全部只记在本报告里。
- **没跑 `scripts/refresh-report-figures.py`**，没跑 `pytest --cov`（并发测量会互相污染覆盖率）。
- **没动两页「怎么复核」**（`docs/how-to-verify.md` / `.zh-CN.md`）——散文改标记是另一扇窗口的事。
  **但请主会话注意 B2**：那一扇改的是 `docs/how-to-verify.md:147` 与 `docs/how-to-verify.md:172`（有标记键的那几处），
  **`docs/how-to-verify.md:171` / `docs/how-to-verify.zh-CN.md:148` 那个「另一个环境」的数没有键可挂**，两扇之间是个洞。
- **没动社交预览卡片**（`scripts/make-social-preview.py` 与 `.github/social-preview.*`）——
  另一扇窗口在收进机制。
- **没动 `docs/reports/README.md`**（报告索引）——主会话统一登记。
- **没动 `scripts/` 与 `tests/`**：本报告没有新增门禁，也没有改门禁。
  §3 与 §6 里的「该怎么做」是**建议**，每一条都注明了理由；要不要做、怎么做，由主会话定。
- **B3 的 §5.3 疑点已经查清**（不是留给主会话的悬念）：`publish-review.md` 表格的第 2、3 栏
  被反引号包着 → 按 outward 规则的**设计**豁免；**缺口只在最右栏与
  `docs/outreach/publish-review.md:342`/`docs/outreach/publish-review.md:406`**，
  因为 `1,695 / 93.3%` 这个**写法**不在规则的认法里。详见 §5.3。
