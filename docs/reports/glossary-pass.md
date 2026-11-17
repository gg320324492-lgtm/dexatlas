# 术语对照表：这一轮做了什么、覆盖了什么、什么故意没做

**日期**：2026-11-18 · **性质**：只读文档工作，产出 `docs/glossary.md` 与几处就地定义。
**没改**：任何 `src/`、`tests/`、`scripts/`、`CHANGELOG.md` 文件；没跑测量脚本；
没抄任何一个测量数字。

---

## 1. 这件事的来路

英文读者视角终检第二轮（[english-reader-review-2.md](english-reader-review-2.md)）§4
列了 **16 条"直接用了而没有一句解释的黑话"**。那一节的判断是对的：这些词**在仓库里大多
是有定义的**——问题不是"没定义过"，而是**用的时候没有指过去**，英语读者手上没有那把尺子。

那份清单只有 16 条，因为它只覆盖了五份当轮合并的文档。本轮要回答的是更大的问题：
**整个 `docs/` 里还有哪些词，是读者读不懂就会猜错的。** 所以做法分三步：

1. **接住那 16 条**——逐条核对它在今天的树上的首次出现处，确认"是否已有就地定义"。
2. **系统扫一遍 `docs/`**——按目录把中文文档过了一遍，列出每个候选词的首次出现行号。
3. **把英文文档排除在外**——`docs/install.md`、`docs/portfolio.md`、`docs/case-studies/`、
   `docs/architecture/` 下多数文件、`docs/roadmap/ROADMAP.md`、`docs/HANDOVER.md`、
   `docs/outreach/`、`docs/releases/` 多数版本说明**本来就是英文**（程序化核对：中文字符数
   为 0）。它们不产生"中文黑话"，只需要在术语表里被**指向**，不被重定义。

第 3 步省掉了大半工作量，也避免了在英文文档旁边再写一份中文解释。

## 2. 覆盖了哪些文档

`docs/` 下 127 份 markdown（`check-version-claims.py` 本轮读到的份数）。其中**含中文**、
因而需要进表的是这些：

| 文档 | 行数 | 本轮在它身上做了什么 |
|---|---:|---|
| `docs/reports/release-process-dry-run.md` | 614 | 补 11 处就地定义；术语表主要来源 |
| `docs/reports/portfolio-readiness-2026-11-18.md` | 484 | 补 6 处；术语表主要来源 |
| `docs/reports/v1.1.0-candidates.md` | 735 | 补 5 处；术语表主要来源 |
| `docs/reports/v1.0.0-release-checklist.md` | 730 | 补 6 处；术语表主要来源 |
| `docs/reports/README.md` | 184 | 加一行术语表索引；**并把索引的份数改对**（见下） |
| `docs/how-to-verify.md` | 480 | 补 7 处；**英语读者的入口页** |
| `docs/how-to-verify.zh-CN.md` | 451 | 补 7 处（与上页一一对应，见 §4） |
| `docs/architecture/public-contracts.md` | 538 | 只被引用，未改（见 §5） |
| `docs/analysis-provenance.md` | 1266 | 只被引用，未改（见 §5） |
| `docs/service-commitments.md` | 151 | 只被引用，未改（见 §5） |
| `docs/roadmap/phase3-plan.md` | 251 | 只被引用，未改（见 §5） |
| `docs/benchmarks/service-regression-set.md` | 327 | 只被引用，未改（见 §5） |
| `docs/proposals/exit-code-partial-read.md` | 267 | 只被引用，未改（见 §5） |
| `docs/reports/m10-selfcheck.md` | — | 只被引用，未改 |
| `docs/reports/ci-gate-coverage.md` | 454 | 只被引用，未改 |
| `docs/reports/coverage-guard-audit.md` | 550 | 只被引用，未改 |
| `docs/reports/m10-acceptance-pack.md` | 727 | 只被引用，未改 |
| `docs/reports/phase2-issue-list.md` | 1633 | 只被引用，未改 |
| `docs/reports/next-engagements.md` | 502 | 只被引用，未改 |
| `docs/reports/final-outward-consistency.md` | — | 只被引用，未改 |
| `docs/reports/m10-reader-package.md` | 487 | 只被引用，未改 |
| `docs/outreach/publish-review.md` | 400 | 只被引用，未改 |
| `docs/benchmarks/m6-verify3-plan.md` | — | 只被引用，未改 |
| `docs/architecture/README.md` | 445 | 只被引用（它自己已有英文 Glossary，见 §5） |

## 3. 术语表本身

[`docs/glossary.md`](../glossary.md)：**89 行术语**，分十节：

| 节 | 行数 | 收的是什么 |
|---|---:|---|
| 一、测量、指纹与基线 | 10 | 源指纹、完整测量、独占测量、基线/基准、口径、分母/分子、一方代码覆盖率、落盘、分片、弱模块表 |
| 二、门禁、CI 与判定 | 8 | 门禁、契约活检、M10 自查、红/绿、判定、只读演练、两棵树、重打 tag |
| 三、引用完整性 | 5 | 漂移、悬空路径、重锚、裸树 locator、探针 |
| 四、套件与测试口径 | 13 | 快/集成、去掉的测试、集成样本、层级、验收线、未达成/未验证、参考线、冻结纪律、窄验证、转通过、确定性修复题、题次、缺席事实 |
| 五、证据、结论与交付物 | 14 | 结论/事实/线索、证据链、公共契约、证据包、报告三件套、交付包、工作区、交叉引用、脱敏、阻断项、收口、停止点、反向测试、已验证/受限/未验证 |
| 六、契约表与分析溯源 | 21 | 退出码、后端、三后端齐备、索引、索引缺口、已发布 run、截断、调用点/调用边、计数含义、出处、**引用**、引用点、说了算、覆盖度、可复现、符号图、线索、grounding 率、如实降级、缩小并重述等 |
| 七、退出码与契约面 | 5 | 残缺、截断、外延、破坏面、契约快照 |
| 八、M10 验收 | 5 | 准备包、独立验收、留人工、三态、卡点 |
| 九、回归测试的三种说法 | 3 | 钉子/钉住、护栏、假绿 |
| 十、四种"检查" | 5 | 复核、走查、演练、审计、首读 |

每行五列：术语、英文、一句话定义、出现位置（`file:line`）、首次出现处是否给了定义。

**最要紧的三条**——不是词难，是**字面翻译会把读者带到错的结论上**：

1. **基线 / 基准 = baseline，不是 criterion。** 它指"一条判断所依据的那棵树或那个提交"。
   英语读者会把"基准"读成"标准/准则"，于是"修订基准 `75976e0`"读起来像"修订后的准则"，
   而它其实说的是"这些判断是在哪棵树上做的"。这个误解会直接导致把一份快照当成现状。
2. **引用 ≠ citation。** `docs/architecture/public-contracts.md`、
   `docs/analysis-provenance.md`、`docs/service-commitments.md` 这三份中文文档里，
   `引用` 一律指**两项之间的边**（资源引用、交叉引用、引用边）；真正对应英文 *citation*
   的词是 `出处`。把"引用"译成 citation 会把读者带到一个完全不同的概念上。
3. **残缺 ≠ 损坏。** `docs/proposals/exit-code-partial-read.md` 整篇在讲这件事：
   残缺 = 运行结束了但结果不完整；截断 = 某一步撞上上限被截掉。字面读成 "corrupted /
   damaged" 会把两者颠倒——而这正是该文档要纠正的误解。

**另两条"同词不同义"的，术语表里都标了 ⚠**：`判定`（清单行的核对结论 vs 题目的机器判分）、
`工作区`（`--workspace` 指的磁盘目录）vs `工作树`（git working tree）。

**还有一条本轮新发现的、本项目最核心的规矩那一族**——见第九节：**钉子**（拿掉修复就变红的
测试）、**护栏**（防回归但在旧代码上不一定变红）、**假绿**（测试过了却没走到出错的那条路）。
英语里这三个词只能各用一个（nail / guardrail / false green），不并列就分不清，而它们
正是 `CLAUDE.md` 规矩第 1 条的三个说法。

## 4. 补了哪些就地定义

在**首次出现处**补了一句话定义，共 **45 处**（覆盖 31 个词），分布：

| 文件 | 处数 | 补了哪些词 |
|---|---:|---|
| `docs/reports/release-process-dry-run.md` | 12 | 判定、红/绿、三后端、源指纹、证据包、门禁、独占测量、契约活检、两棵树、重打 tag、快/集成、准备包 |
| `docs/reports/portfolio-readiness-2026-11-18.md` | 6 | 准备包/独立验收、全绿、快/集成、契约活检、三后端齐备、留人工 |
| `docs/reports/v1.0.0-release-checklist.md` | 6 | 基准、准备包、重打 tag、门禁、证据包、独立验收、全绿 |
| `docs/reports/v1.1.0-candidates.md` | 5 | 基准、独立验收、证据包、源指纹、留人工 |
| `docs/how-to-verify.md` | 8 | 层级/窄验证、去掉的测试、快/集成、参考线、未达成/未验证、验收线/冻结纪律、转通过/确定性修复题、三后端齐备 |
| `docs/how-to-verify.zh-CN.md` | 8 | 同上八处（逐处对应，见下） |
| `docs/reports/README.md` | 1 | 术语表索引行 |

**`how-to-verify` 两页是对孪生**：正文自称"与本页内容一一对应"。只在其中一页补定义会让
两份说法不一致，所以**同一定义在两页都补了**，位置按内容对应而非行号对应（两页行数
不同：480 / 451）。

**定义的长度**：一句话，读者不跳转就能继续读。已经在正文就地定义过的词，**一个字都没动**
——包括 `docs/reports/v1.1.0-candidates.md:53` 的工程日刻度（那里本来就写着
"Phase 3 计划里作者自己建仓库的投入估计"）、`docs/reports/m10-selfcheck.md:62` 的
留人工、`docs/architecture/README.md:190` 的英文 Glossary 四条。

## 5. 哪些术语**故意**留给读者自己查

术语表里有一节叫「故意不收的词」，逐条写明理由。归纳成五类：

1. **工具与库名**（Apktool、JADX、androguard、uv、pytest、ruff、mypy、SQLite、MCP）——
   正文里就是英文原样出现的，读者查官方文档即可。给它们写定义只会占版面。
2. **Python 与 Git 概念**（venv、worktree、commit、annotated tag、marker）——同上。
   例外是 `重打 tag`：它在本仓库有特定含义（不是"再打一次"，是"把标签强行移到另一个
   提交上"），所以收进了表，也补进了正文。
3. **普通中文词**（文件、读取、测试、命令、失败、通过）——任何中文读者都懂。
4. **数字**——测试数、覆盖率、指纹值由 `scripts/refresh-report-figures.py` 生成，写在
   `docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` 标记之间。**这一页只管词，
   不管数**：手抄一个数就会立刻过期，而过期的数字比没有数字更糟。
5. **已有英文定义、只需指向的**——`docs/architecture/README.md:190` 已经用英文写清了
   agent service promise、frozen discipline、B1 验收线、判分七条红线。术语表**指向**它，
   不重复定义。

**另外一类"故意不动"是整个文件不动**：`docs/architecture/public-contracts.md`、
`docs/analysis-provenance.md`、`docs/service-commitments.md`、`docs/roadmap/phase3-plan.md`、
`docs/benchmarks/service-regression-set.md`、`docs/proposals/exit-code-partial-read.md`、
`docs/reports/phase2-issue-list.md`、`docs/reports/next-engagements.md`、
`docs/reports/final-outward-consistency.md`、`docs/reports/m10-reader-package.md`、
`docs/reports/ci-gate-coverage.md`、`docs/reports/coverage-guard-audit.md`、
`docs/reports/m10-acceptance-pack.md`、`docs/outreach/publish-review.md`、
`docs/benchmarks/m6-verify3-plan.md` 这十五份**中文文档里的词也进了术语表，但一个字都没
在它们身上补**。理由：

- 它们各自有专门的归属文档（`public-contracts.md` 是契约表的正主、
  `architecture/README.md` 有英文 Glossary、`call-sites-and-edges.md` 整篇讲调用点与调用边），
  在术语表里指向它们，比在正文里插一句话更不打断阅读；
- 这几份都是长文档（151–1633 行），逐处插定义会把它们改成另一份文档；
- 这一轮的目的是**让读者有个地方可以查**，不是让每个文件都自带词典。

代价要写清楚：**在这些文件里，读者第一次遇到某个词时仍然要跳到术语表。** 这是取舍，
不是遗漏。哪一天发现某个词在这些文件里读不懂的反馈变多，再往里补。

## 6. 这一轮没做的事

- **没动四个文件**：`docs/reports/phase1-execution-report.md`、`README.md`、
  `README.zh-CN.md`、`docs/status.md`——主会话正在跑最终重测量，这四个由测量脚本写。
- **没跑 `scripts/refresh-report-figures.py`**：同上；跑它会和主会话抢测量槽位。
- **没抄任何测量数字**：术语表里一个覆盖率、测试数、指纹值都没有。
- **没改 `src/`、`tests/`、`scripts/`、`CHANGELOG.md`**。
- **没加 `<!--fig:…-->` 标记**：那个标记只由测量脚本写进它自己认的那四份文件；
  写进新文件会留下一个永远填不上的空标记。

### 顺带修对的一处：`docs/reports/README.md` 的份数

新增本报告让 `docs/reports/` 多了一份文件，于是索引的份数必须跟着动。动的过程里发现
索引的份数**本来就是错的**（英文读者终检第二轮 §3.8 记的那条）：

| 位置 | 改前 | 改后 | 依据 |
|---|---:|---:|---|
| 开头「**五十二份**报告」 | 52 | 53 | 目录里除本页外有 53 个 `.md` |
| §3 里程碑与对外准备度 | 2 | 5 | 该组点名 5 个文件 |
| §5 v1.0.0 发版材料 | 5 | 7 | 该组点名 7 个文件 |
| §6 本轮审计与走查 | 17 | 20 | 该组点名 20 个文件（加本报告一行） |
| 合计 | 41 | 53 | 7+5+5+9+7+20 |

改完**可复算**：§1–§6 点名的 53 个文件与目录里的 53 个 `.md` 一一对应，无重复、无遗漏
（脚本逐行核对过）。这正是索引自己第 38 行那句话的意思——「下面 §1–§6 的每一行都点名的
一个文件」，所以「哪几份没被收录」现在可以直接比出来。

顺带把「本页的份数停在 2026-11-17 那天树上」改成 2026-11-18。

**没有动 §7「历史记录」**，也没有把别的会话正在改的 §3.9（补三份没进索引的文件）一起做——
那是另一条编号的发现，混进来会让这一轮的改动说不清。

## 7. 怎么验的

| 门禁 | 结果 |
|---|---|
| `scripts/check-doc-citations.py` | `drifted: 0`、`unresolved paths: 0` |
| `scripts/check-version-claims.py --base auto` | `Every version claim matches the repository.`（2 条 finding 均为 base `75976e0c` 里已有的历史项） |
| `pytest tests/test_docs.py -q` | 60 passed / **4 failed**——4 条失败在**未改动的 HEAD 上同样失败**（用 `git archive HEAD` 解出的干净副本复跑确认过）：它们比的是 `docs/reports/phase1-execution-report.md` 里那次测量的记录与**当前源码树**，记录已经过期（`reports/evidence_package.py`：记录 153 行、树里 172 行）。这正是主会话那轮最终重测量要修的，与本轮改动无关 |
| 术语表自检 | 表里 **143 处 `file:line` 引用逐条解析**：文件存在、行号在范围内，0 处失效；另有一次术语邻近核对，确认每个词确实出现在所引的那一行或其上下两行内（少数"对不上"的是英文原文、复合词与 `<!--fig:…-->` 标记，人工逐条看过） |

术语表的行号指向**本轮改动后的当前树**。`docs/` 一改，行号就动；改动多的时候整表
重算一遍，不要手改数字。

## 8. 留给下一轮的事

- `docs/reports/english-reader-review-2.md` §4 的通用建议是"每份开头一个五行 Glossary
  小节"。本轮做的是**全仓一张表**（本任务的要求），没有做那件事。两种做法不冲突：
  若某一轮要精读某一份报告，在它开头加一个只收本份用词的小节仍然更省事。
- 术语表不在 `scripts/check-doc-citations.py` 的 `DOCS` 名单里（那份名单只查 12 份文件），
  所以**它的行号没有自动门禁**。改动多时得自己重算——这是这张表已知的软肋。
- `docs/status.md` 的快照与评分、`docs/releases/` 里的版本说明，本轮都只被引用、未改。
