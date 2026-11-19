# C13 落地记录：引用检查器覆盖到报告层

> **性质**：v1.1.0 候选 **C13** 的收口报告（2026-11-20）。
> 回答三个问题：报告层是怎么被结构性纳入检查的；「新报告带坏引用、不改名单、检查器报错」
> 的红→绿是怎么证的；哪些历史报告被显式排除、每份的原因是什么。
> **本窗口只动了检查器、它的测试与文档**；测量脚本与各门禁脚本一字未改。

---

## 1. 改了什么

### 1.1 结构性收集：`collect_documents()`

`scripts/check-doc-citations.py` 的检查对象不再是一份手工维护的 `DOCS` 名单，而是：

- `collect_documents()`：固定核心文档（`docs/analysis-provenance.md`、
  `docs/architecture/public-contracts.md`、`docs/benchmarks/large-apk.md`）
  **＋ `docs/reports/*.md` 全部报告**（除 `REPORT_EXCLUSIONS`）
  **＋ `docs/releases/*.md`**，去重后返回。`DOCS = collect_documents()` 保持模块级兼容。
- `REPORT_EXCLUSIONS: dict[str, str]`：**显式排除清单**，键是报告文件名，值是排除原因。
  现有 **40 份**历史报告在列，每份的原因写明「行号按哪棵树取值、为什么当前不能核、
  何时可移出」。排除是决定，不是 omission——这条性质有测试守着
  （`test_an_excluded_report_is_left_out_and_its_reason_is_stated`）。

**为什么不是「全量纳入后逐份修到绿」**：实测（逐份独立跑 `check_documents`）
58 份未被覆盖的报告里，18 份当前零 findings，40 份带 **720 条** findings——绝大多数是
「行号按写作当时的树取值」的历史快照（`phase2-issue-list.md` 声明基线 `8df894b`、
`phase1-maturity-assessment.md` 声明 `b8ef71a`、`ci-gate-coverage.md` 声明 `062c4b5` 等）。
按当前树硬核会全数误报，而正确收口（登记 `TREE_DOCUMENTS` + 文档补指纹声明）需要逐份
回到各自基线树重锚，不属于本窗口「只动检查器、测试与文档」的分工。所以本窗口的做法是：
**结构上全收，例外显式列出并写明原因**——新报告从此没有「漏登记」的可能，
历史报告的去向全部可查。

### 1.2 名单重构引发的自身引用位移：16 处修正

`DOCS` 从 :164 的手工名单变成 :271 的 `collect_documents()`，检查器自己及若干报告里
引用检查器行号的 `file:line` 全部位移。逐处核对符号的真实新行号后修正 16 处：

| 文件 | 修正内容 |
|---|---|
| `citation-anchor-declarations.md` | `DECLARATION`/`ANCHOR_NAME`/`check_anchor_name`/`check_anchor_fragment`/`_resolve`/`check_anchor`/`document_orphan_declarations`/`DECLARING_DOCUMENTS`/`check_declaration_of_content` 共 7 处行号 |
| `declarations-outward.md` | 6 处（含 2 处 `DOCS` 引用改指 `collect_documents()` 新行号并更新 `anchor:` 声明） |
| `handwritten-numbers-audit.md` | `DOCS` 白名单行号 1 处 |
| `post-release-rehearsal.md` | `TREE_DOCUMENTS` 行号 1 处 |
| `local-vs-ci-gates.md` | `os.walk` 顺序核对行 1 处 |
| `m4-acceptance.md` | 「2 个已知 findings」的出处改指真实在案的 `docs/releases/v0.2.0.md:326` 与 `CHANGELOG.md:1117`（原文引的 `status.md:67` 不承载该表述） |

`pyproject.toml` 给 `scripts/check-doc-citations.py` 加了 `RUF001` 豁免
（排除清单的原因说明是中文，全角标点在字符串字面量里会误触该规则），并清理了因此
失效的 5 处 `# noqa: RUF001`。

### 1.3 文档与登记

- `docs/reports/v1.1.0-candidates.md`：C13 状态改「✅ 已完成（2026-11-20）」；
  §0 速览、§0.1 分桶表、§2 P0 表、§4 触发条件表（C13 行移除，7 行→6 行）、
  §7.1/§7.2 复核口径全部改齐（已完成 9→10、等外部 5→4、加法 10+1+1+1+4=17）。
- `docs/reports/README.md`：§6 登记本报告，份数 96→97（§6 84→85），快照注记同步。
- 本报告（`c13-report-citations.md`）落盘即被 `collect_documents()` 纳入检查——
  它自己的 `file:line` 引用从此也有门禁看着。

---

## 2. 红→绿证据

**红（旧实现）**：取 `HEAD` 版本的 `check-doc-citations.py`（手工 `DOCS` 名单），
在临时目录 `docs/reports/` 放一份新报告
`a-fresh-report.md`，内容只有一句英文句子，引用了 pyproject.toml 的第 99999 到 100001 行（超出文件末尾）：

- 旧实现无 `collect_documents`；新报告不在 `DOCS` 名单里；
  旧 `main()` 对其视而不见，**退出码 0**。

**绿（新实现）**：同一份新报告、同一个临时目录，`collect_documents()` 把它捡进检查列表，
`check_documents()` 报 **1 条 `out of range`** finding，退出码 **1**。

固定为回归测试（`tests/test_doc_citations.py` 新增 5 条）：

1. `test_the_reports_are_collected_without_a_handwritten_list`——临时仓库里新建报告与
   release 文档，`collect_documents()` 全部收进；
2. `test_an_excluded_report_is_left_out_and_its_reason_is_stated`——排除清单生效且每项有原因；
3. `test_every_report_is_either_checked_or_excluded`——真实仓库里 `docs/reports/*.md`
   要么在 `DOCS`、要么在排除清单，两边都不在即红（这条在旧手工名单实现下直接红：
   58 份无人覆盖）；
4. `test_a_new_report_with_a_bad_citation_fails_the_check_without_touching_a_list`——
   **红→绿的核心**：新报告带坏引用，不改名单，`main()` 退出码 1；
5. `test_a_new_report_that_is_clean_leaves_the_check_green`——干净的新报告不误伤（仍为 0）。

旧实现回放方式：`git show HEAD:scripts/check-doc-citations.py` 单独加载，
跑同一场景——退出码 0（红）；新实现同场景退出码 1（绿）。

---

## 3. 排除清单的构成（40 份，原因摘要）

| 类别 | 报告 | 共同原因 |
|---|---|---|
| Phase 1/2 审计（5 份） | phase1-maturity-assessment、phase2-issue-list、phase1-findings-ledger、phase1-review-report、phase3-baseline | 行号按文首声明的基线树（`b8ef71a`/`8df894b`/`6b08684`）写 |
| M10 验收材料（9 份） | m10-acceptance-pack、m10-number-traceability、m10-materials-alignment、m10-reader-walkthrough 1–4 轮、m10-reader-kit、m10-invitation-readiness、m10-invitation-final、m10-review-record-template | 行号按各自复核/走查树（`ff5c4cc`/`78102a8`/`0104ccb`/`599ab67`/`02e6d9c`/`c6bf3f7`/`81336a5`/`b71bf30`/`2edaed9`）写 |
| 发版周记录（8 份） | release-notes-consistency、changelog-vs-release-notes、v1.0.0-release-checklist/-runbook/-commit-draft、v1.0.0-ci-run-record、reader-dry-run、release-process-dry-run | 行号按其记录的树（`78102a8`/`d2c5f35`/`53358c5`/`277d0fa`/`a4e7af5`/v1.0.0 tag/演练副本）写 |
| 11 月审计轮（8 份） | ci-gate-coverage、coverage-guard-audit、new-pages-crosscheck、readme-map-audit、handover-tails-audit、final-outward-consistency、english-reader-review、stale-number-scan | 行号按各自复核树（`062c4b5`/`8868e30`/`e5060af`/`0a8e02e`/`d43369b`/`48a56b5` 等）或未声明基线 |
| 设计/分析报告（9 份） | figures-coverage-design、case-studies-run-correspondence、case-studies-third-package、m8-install-rehearsal、glossary-pass、portfolio-readiness-2026-11-18、outreach-recheck、outreach-final-review、outreach-publish-checklist、github-repo-metadata-proposal | 行号按写作当时树或其基线树（`9f0dae3`/`c3586d8`/`e4f3011`/`75976e0`/`8f9ddca` 等）写 |
| 候选清单本身（1 份） | v1.1.0-candidates | 引用多处基准文件行号，按写作当时树取值；其 §3 C13 自述了这一缺口 |

（合计 40 份；完整原因逐份写在 `scripts/check-doc-citations.py` 的 `REPORT_EXCLUSIONS`。）

**移出条件**（写进检查器注释）：把该报告的基线树登记进 `TREE_DOCUMENTS`，
并在文档里补上那棵树的测量指纹声明，使检查器能按其声称的树解析引用。

---

## 4. 门禁结果（本窗口实测）

| 门禁 | 结果 |
|---|---|
| `python scripts/check-doc-citations.py` | **drifted: 0，values not matching: 0**（检查对象 56 份工作副本文档 + 8 个按树解析文档，1620 条引用） |
| `ruff check .` / `ruff format --check .` | 通过（419 files formatted） |
| `mypy`（strict） | 通过（68 files） |
| `vulture --min-confidence 80` | 通过（exit 0） |
| `check-unguarded-numbers.py` | PASS（25 watched statements） |
| `check-version-claims.py --base auto` | 通过（2 findings 均为基线内历史项） |
| `pytest tests/test_doc_citations.py` | **50 passed**（44 旧 + 6 新，其中 5 条为本窗口新增的结构性/红绿测试） |

**没有跑** `scripts/refresh-report-figures.py`，没有同步任何测量数字（按分工留给主会话）；
`tests/` 的改动在源指纹覆盖范围内，**合入后需要重测量**（与历次「改 tests/」的口径一致）。

---

## 5. 本窗口做的 / 留给主会话的

**本窗口做的**

- `collect_documents()` 结构性收集 + `REPORT_EXCLUSIONS` 显式排除清单（40 份、逐份原因）；
- 5 条新回归测试（含红→绿核心测试），旧实现回放验证（退出码 0 → 1）；
- 修正 6 份报告里因名单重构位移的 16 处 `file:line`（含 2 处 `anchor:` 声明更新）；
- `pyproject.toml` 的 `RUF001` per-file 豁免与 5 处失效 `noqa` 清理；
- C13 状态、候选清单计数口径（§0/§2/§4/§7）、README 索引（97 份）登记；
- 本报告。

**留给主会话 / 后续**

1. **40 份历史报告的逐份回锚**：登记 `TREE_DOCUMENTS`、文档补指纹声明，从排除清单移出；
   优先级建议：`figures-coverage-design.md`（36 条，设计报告、常被引用）→
   `m10-number-traceability.md`（41 条）→ 其余按引用频度。
2. **候选 C13 原文的三条新规则**：被引行不得空白、引用不得越界（`out of range`
   已有，作为检查器既有能力可先覆盖一半）、悬空裸 `:NN` 必须同块可解析——
   各配红→绿回归测试。
3. **「文档之间互引」检查**：现行检查器只查「文档 → 代码」；报告层纳入后，
   报告引用报告的行号（如 m10-reader-walkthrough.md 第 47 行引 m10-acceptance-pack.md 第 637 行）
   已经能被 `out of range`/`points at nothing` 抓住一部分，但「被引方行号变化触发引用方
   漂移」的完整闭环仍待补测试。
4. **重测量**：本窗口改了 `tests/`（+5 测试），源指纹会变；按项目规则由主会话统一重测、
   同步报告数字（本窗口未动任何 `<!--fig:-->` 数字）。
