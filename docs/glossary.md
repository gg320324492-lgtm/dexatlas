# 术语对照表（中文 ↔ English）

**为什么有这一页。** DexAtlas 的文档是中文，代码与注释是英文。中文里"不言自明"的词，
英文里没有对应物——读者读不懂就只能猜，猜错就会得出错的结论。这一页把仓库自己用过的
词逐条摊开：**每条一句话，读完这一句就能继续往下读，不用跳转。**

**怎么用。** 正文里第一次出现某个词、而那里没有就地解释时，先查这一页。正文里就地
定义过的，以正文为准——最后一栏会把这件事标出来。

**这一页不收什么。** 工具名、库名、Python 与 Git 概念（`pytest`、`ruff`、`mypy`、
`venv`、CI job、worktree、commit）不收：它们在正文里就是英文原样出现的，读者查官方
文档即可。只收**读者读不懂就会猜错**的词。

**最后一栏的读法。** 它写的是每个词**在各个文件里的首次出现处**有没有就地定义，
格式是 `文件:行号 是 / 否`。标「已补」的是本轮补上去的；标「否」又没标「已补」的，
那一处靠这一页兜底。行号指向本轮改动后的当前树。

**数字不在这一页。** 测试数、覆盖率、指纹这些数字由
`scripts/refresh-report-figures.py` 生成，写在
[`docs/reports/phase1-execution-report.md`](reports/phase1-execution-report.md) 的
`<!--fig:…-->` 标记之间；这一页只管词，不管数。

**一份姊妹表。** [`docs/architecture/README.md`](architecture/README.md) 的
[`## Glossary`](architecture/README.md#glossary) 用英文写清了四条**项目自己的规矩**
（agent service promise、frozen discipline、B1 验收线、判分七条红线）。那些是英文文档，
不需要翻译；本页只**指向**它们，不重复定义。

---

## 术语表

按主题排序，不是字母序。同一族的词挨在一起，因为读者常常一次读到好几个。

### 一、测量、指纹与基线

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 源指纹 / 源码指纹 | source fingerprint | 对 `src/`、`tests/`、`pyproject.toml` 和测量脚本求的哈希；它回答「还是不是同一份代码」，不回答「这份代码还绿吗」。 | `reports/release-process-dry-run.md:62`、`reports/v1.1.0-candidates.md:106`、`reports/portfolio-readiness-2026-11-18.md:442`、`reports/v1.0.0-release-checklist.md:529`、`reports/ci-gate-coverage.md:14`、`reports/phase1-execution-report.md:985` | dry-run:62 是（已补）· candidates:106 是（已补）· portfolio:442 否 · checklist:529 否 · ci-gate-coverage:14 否（§2.1 从 :91 起解释边界）· phase1-execution-report:985 是 |
| 完整测量 / 重测量 | full measurement | 跑一遍完整测试套件并测覆盖率，把结果写回报告与 README 徽章；数字由此而来。 | `reports/release-process-dry-run.md:66`、`reports/v1.0.0-release-checklist.md:381`、`reports/ci-gate-coverage.md:12` | dry-run:66 否 · checklist:381 是（§8.1 L1 行给出命令）· ci-gate-coverage:12 否 |
| 独占测量 | exclusive measurement | 同一个 checkout 同一时刻只允许一个测量进程在跑；两个进程会互相污染覆盖率数据。 | `reports/release-process-dry-run.md:167`、`reports/v1.0.0-release-checklist.md:353`、`reports/coverage-guard-audit.md:86` | dry-run:167 是（已补）· checklist:353 是（§7 N1 整节讲机制）· coverage-guard-audit:86 是 |
| 基线 / 基准 | baseline | 一条判断所依据的那棵树或那个提交。同一个数字在不同基线上读出来可能不同。 | `reports/README.md:14`、`reports/release-process-dry-run.md:11`、`reports/portfolio-readiness-2026-11-18.md:7`、`reports/v1.1.0-candidates.md:3`、`reports/v1.0.0-release-checklist.md:3` | README:14 是 · dry-run:11 是（就地写明基线是什么）· portfolio:7 否 · candidates:3 是（已补）· checklist:3 否（已补于 :8） |
| 口径 | measurement basis | 这个数是在哪个分母、哪套题、哪条判分规则下算出来的。 | `roadmap/phase3-plan.md:58`、`reports/v1.1.0-candidates.md:91` | phase3-plan:58 否 · candidates:91 否 |
| 分母 / 分子 | denominator / numerator | 比值的上数与下数：测试总数，或代码总行数。⚠ 本仓库里"分母"有两义——**测试数** 与 **代码总行数**，换个口径就换个意思。 | `reports/release-process-dry-run.md:68`、`reports/v1.1.0-candidates.md:166`、`reports/ci-gate-coverage.md:178`、`reports/coverage-guard-audit.md:75` | dry-run:68 否 · candidates:166 是（并说明"两个分母不是一回事"） |
| 一方代码覆盖率 / 一方 | first-party coverage | 本仓 `src/dexatlas` 自身代码的覆盖率，不含第三方库。 | `reports/coverage-guard-audit.md:414` | 否 |
| 落盘 | persisted to disk | 由工具写进磁盘、并成为后续读数来源的那一步。 | `reports/coverage-guard-audit.md:167` | 否 |
| 分片 | coverage data shard | coverage 并行模式下每个进程各写各的独立数据文件；进程之间会互相抹掉。 | `reports/coverage-guard-audit.md:63` | 否 |
| 弱模块表 | low-coverage module table | 覆盖率明显偏低的模块清单，由测量脚本生成；数字变陈旧时它先变陈旧。 | `reports/coverage-guard-audit.md:79`、`outreach/publish-review.md:387`、`reports/phase1-execution-report.md:89` | coverage-guard-audit:79 否 · publish-review:387 否 · phase1-execution-report:89 是（`<!--fig:coverage.weak_modules-->` 标记内） |

### 二、门禁、CI 与判定

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 门禁 | gate | 一道退出码直接决定通过与否的自动检查。 | `how-to-verify.md:97`、`reports/release-process-dry-run.md:117`、`reports/v1.0.0-release-checklist.md:20`、`reports/ci-gate-coverage.md:1` | how-to-verify:97 是（§2.4–§2.8 逐条给命令）· dry-run:117 是（已补）· checklist:20 是（已补）· ci-gate-coverage:1 是（通篇逐道列出） |
| 契约活检 | contract live-check | 真的把公共契约面跑一遍、失败就非零退出的脚本；它验证行为，不是比对文档。 | `how-to-verify.md:38`、`reports/release-process-dry-run.md:181`、`reports/portfolio-readiness-2026-11-18.md:56`、`reports/v1.0.0-release-checklist.md:508`、`reports/ci-gate-coverage.md:12` | how-to-verify:38 是（§2.6「门禁三」）· dry-run:181 是（已补）· portfolio:56 是（已补）· checklist:508 是（§8.1 L2 行）· ci-gate-coverage:12 否 |
| M10 自查 | M10 self-check | `scripts/m10_selfcheck.py`：把 M10 准备包里的检查跑成自动化判定。 | `reports/ci-gate-coverage.md:12`、`reports/v1.0.0-release-checklist.md:509` | ci-gate-coverage:12 否 · checklist:509 是（§8.1 L3 行） |
| 红 / 绿 / 全绿 | red / green | 一次 CI run 的结论：每个 job 都是 success 才叫绿；有一个不是，就不叫绿。 | `reports/release-process-dry-run.md:11`、`reports/v1.0.0-release-checklist.md:51`、`reports/portfolio-readiness-2026-11-18.md:18` | dry-run:11 否（已补于 :26）· checklist:51 否（已补）· portfolio:18 否（已补于 :19） |
| 判定 | judgement | 一行检查核对完之后留下的结论，取值有限；本仓库里另有一义：**题目的机器判分**（`must_contain` / `expect_count` / `expect_empty` / `expect_backend_failure`）。 | `reports/release-process-dry-run.md:20`、`reports/v1.0.0-release-checklist.md:83`、`benchmarks/service-regression-set.md:8` | dry-run:20 否（已补）· checklist:83 否 · service-regression-set:8 否 |
| 只读演练 / 只读复核 | read-only dry run | 照着清单或材料真走一遍，但除了这份报告什么都没改；它的结论只对走它的那棵树成立。 | `reports/release-process-dry-run.md:1`、`reports/v1.0.0-release-checklist.md:9`、`reports/reader-dry-run.md:1` | dry-run:1 是（标题写明"只读"，§0 写明没改任何东西）· checklist:9 是（括注"照本清单实走一遍的只读演练"）· reader-dry-run:1 是 |
| 两棵树（发布树 / 当前树） | the two trees | 发布树 = tag 指向的那棵不可变的树；当前树 = 现在工作区这棵。数字属于前者，代码可能已经是后者。 | `reports/release-process-dry-run.md:257`、`reports/v1.0.0-release-checklist.md:102`、`reports/ci-gate-coverage.md:225` | dry-run:257 否（已补）· checklist:102 否 · ci-gate-coverage:225 否（§4.11 从 :225 起讨论） |
| 重打 tag | re-tagging | 把已存在的 annotated tag 强行移到另一个提交上，标签本身不变。 | `reports/release-process-dry-run.md:39`、`reports/v1.0.0-release-checklist.md:10`、`reports/m10-invitation-sender-checklist.md:123` | dry-run:39 是（已补）· checklist:10 否（已补于 :11）· invitation-sender:123 是（给出 `git push --force`） |

### 三、引用完整性（这个项目的承诺就落在这几个词上）

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 漂移 | citation drift | 文档里的 `file:line` 已经不再指向它命名的那个符号。 | `reports/ci-gate-coverage.md:70`、`reports/final-outward-consistency.md:31` | 否 |
| 悬空路径 | dangling path | 引用指向的文件或路径已经不存在。 | `reports/final-outward-consistency.md:31` | 否 |
| 重锚 | re-anchor a citation | 把 `file:line` 引用改写到该符号现在所在的新行号。 | `reports/ci-gate-coverage.md:82` | 否（该行给了工具名 `scripts/remap-citations.py`） |
| 裸树 locator | bare-tree locator | 指向整个反编译源码树（而不是单个文件）的定位符；`path=None` 是设计，不是失败。 | `reports/m10-acceptance-pack.md:116` | 否 |
| 探针 | probe | 插进代码里记录调用参数的测试挂钩，不是产品功能。 | `reports/phase2-issue-list.md:218` | 否 |

### 四、套件与测试口径

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 快 / 集成（两套测试） | fast suite / integration suite | fast = pytest 没标 `slow` 的用例；slow = 标了 `@pytest.mark.slow`、要真调外部后端的集成用例。**仓库里没有 `integration` 这个 marker。** | `how-to-verify.md:147`、`reports/release-process-dry-run.md:164`、`reports/portfolio-readiness-2026-11-18.md:39`、`how-to-verify.md:147` | how-to-verify:147 否（已补于 :148）· dry-run:164 是（已补）· portfolio:39 是（已补） |
| 去掉的测试 | deselected tests | 被 pytest 的 `-m` 过滤掉的用例；pytest 把它记作 deselected，不是 removed。 | `how-to-verify.md:134` | 否（已补于 :135） |
| 集成样本 | third-party integration fixture | 不随仓库分发、由 `scripts/fetch-fixtures.sh` 拉取的第三方测试 APK；不取它，相关测试会 skip。 | `how-to-verify.md:24` | 否（§2.0 解释了怎么取，但词本身没定义） |
| 层级 | level / tier | M6 评测任务的分级：0 = 确定性判分，1 = 替身脚本（scripted），2 = 用真实模型跑冻结题集。**scripted 是替身，不是模型能力。** | `how-to-verify.md:37`、`reports/m10-acceptance-pack.md:38`、`benchmarks/service-regression-set.md:175` | how-to-verify:37 否（已补）· acceptance-pack:38 否（层级含义在 :140 才说开）· service-regression-set:175 是（各层标题自解释） |
| 验收线 | acceptance threshold | 认定某个里程碑通过所需的最低分数门槛。 | `how-to-verify.md:413`、`benchmarks/service-regression-set.md:159` | how-to-verify:413 是（已补）· service-regression-set:159 是 |
| 未达成 / 未验证 | not met / not verified | **未达成** = 量过但没过线；**未验证** = 从未测过。两者对读者的意义不同：前者是坏消息，后者是不知道。 | `how-to-verify.md:404` | 否（已补于 :406） |
| 参考线 | reference threshold | 预先写下、只作对照比较的分数线；**不等于**验收线，对照参考线的报告不算验收成绩。 | `how-to-verify.md:329` | 否（已补于 :330） |
| 冻结纪律 | freeze discipline | 调优前冻结题集与门槛，不许靠删掉做对的题来提高通过率。 | `how-to-verify.md:413`、`benchmarks/service-regression-set.md:155`、`architecture/README.md:204` | how-to-verify:413 是（已补）· service-regression-set:155 是（§5，并链到 architecture/README.md）· architecture/README:204 是（英文定义） |
| 窄验证 | narrow verification | 只在六道已知失败面上重跑的缩小复测：6 题 × 3 轮。 | `how-to-verify.md:37` | 否（已补） |
| 转通过 | flipped to pass | 原先判失败、这一轮改成通过的题。 | `how-to-verify.md:414` | 是（已补） |
| 确定性修复题 | deterministic-fix task | 预期修法确定、可判对错的题（窄验证六题中的五题）。 | `how-to-verify.md:414` | 是（已补） |
| 题次 | question instance | 一道题在一轮里的一次计分。 | `benchmarks/service-regression-set.md:264` | 否 |
| 缺席事实 | the fact of absence | "某样东西不存在"这件事本身，必须按与失败记录相同的形状记下来。 | `benchmarks/service-regression-set.md:276` | 否 |

### 五、证据、结论与交付物

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 结论 / 事实 / 线索 | finding / fact / lead | 结论 = 工具读出且带能解析的出处；事实 = 工具读到的字节；线索 = 模型的说法，只能待核，永远不能升级成结论。 | `how-to-verify.md:415`、`roadmap/phase3-plan.md:39`、`architecture/README.md:151` | how-to-verify:415 是（"模型的结论永远不是事实"）· phase3-plan:39 否 · architecture/README:151 是（英文表：`lead` = 静态分析或模型提示的风险指标） |
| 可核查 | verifiable | 读者能自己把一条结论核到它的出处：指出是哪个工具、哪个版本、从哪个字节位置读出来的。本仓库统一写「可核查」，不写「可核验」——两个词说的是一件事，读者以为是两件。 | `../README.zh-CN.md:5`、`../README.zh-CN.md:25`、`reports/m10-acceptance-pack.md:443`、`benchmarks/service-regression-set.md:17` | 否（README.zh-CN.md:5 的 tagline 是定位语，不解释词义） |
| 证据链 / 出处模型 | evidence chain / provenance model | 记录每条结论由哪个工具、哪个版本、从哪个字节位置读出来的那条链。 | `how-to-verify.md:40`、`analysis-provenance.md:880` | how-to-verify:40 是（括注一句）· analysis-provenance:880 是（§4 逐步给命令） |
| 公共契约 | public contract | 对外承诺并版本化的行为表面：CLI 子命令、退出码、REST 端点、MCP 工具、报告 schema。 | `architecture/public-contracts.md:1`、`roadmap/phase3-plan.md:7` | public-contracts:1 是（整份文件就是它）· phase3-plan:7 否 |
| 证据包 | evidence package | `dexatlas export` 导出的 zip：报告本身 + 一份记录所引文件哈希的 `manifest.json`。 | `reports/release-process-dry-run.md:84`、`reports/v1.1.0-candidates.md:28`、`reports/v1.0.0-release-checklist.md:37`、`reports/portfolio-readiness-2026-11-18.md:207`、`architecture/public-contracts.md:32` | dry-run:84 是（已补）· candidates:28 是（已补）· checklist:37 是（已补）· portfolio:207 否 · public-contracts:32 是（§5.3 给出 manifest 字段） |
| 报告三件套 | the report trio | 同一份分析的 Markdown / JSON / 离线 HTML 三个文件。 | `outreach/publish-review.md:130`、`benchmarks/m6-verify3-plan.md:125` | publish-review:130 是（列出三个文件名）· m6-verify3-plan:125 是（但那里的"三件套"指后端检查三件套，是另一回事） |
| 交付包 | delivery package | 客户可以直接审阅的成品：报告 + 最小证据包 + 案例说明。 | `roadmap/phase3-plan.md:66` | 否（实义在 :141、:149） |
| 工作区 | workspace | 存项目、报告与证据的磁盘目录，`--workspace` 指的就是它；与 git 的"工作树"是两回事。 | `architecture/public-contracts.md:24`、`roadmap/phase3-plan.md:56` | public-contracts:24 是（`--workspace` 出现在命令行表里）· phase3-plan:56 否 |
| 交叉引用 | cross-reference (xref) | 一个符号引用另一个符号的位置；CLI 子命令是 `xrefs`。 | `how-to-verify.md:98` | 否 |
| 脱敏 | redaction | 从导出包里删掉敏感字符串，并记录删了什么。 | `roadmap/phase3-plan.md:152` | 否 |
| 阻断项 | blocking item | 验收前必须关闭的问题，不能被高分或重要项抵消。 | `roadmap/phase3-plan.md:219` | 否（:101 那行写的是「阻断/重要/可选」三类） |
| 收口 | close out | 把对外陈述与证据对齐之后定稿，不再改动。 | `roadmap/phase3-plan.md:89` | 否 |
| 停止点 | stopping point | 本阶段停止扩功能的界线，之后由真实反馈决定下一步。 | `roadmap/phase3-plan.md:45` | 否（§1.2 只有标题「达标后的停止点」） |
| 反向测试 | negative test | 断言缺陷确实会发生的测试，与回归护栏相反。 | `roadmap/phase3-plan.md:161` | 否 |
| 已验证 / 受限 / 未验证 | verified / limited / unverified | 对外声明清单里每条陈述的三种标记。 | `roadmap/phase3-plan.md:104` | 否（只列出三值，未解释"受限"） |

### 六、契约表与分析溯源里的词（`docs/architecture/`、`docs/analysis-provenance.md`、`docs/service-commitments.md`）

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 公共契约 | public contract | 对外承诺并版本化的行为表面：CLI 子命令、退出码、REST 端点、MCP 工具、计数的含义、报告 schema；改动要显式升版本。 | `architecture/public-contracts.md:1`、`roadmap/phase3-plan.md:7` | public-contracts:1 是（整份文件就是它）· phase3-plan:7 否 |
| 退出码 | exit code | CLI 退出码。**1 是"答案合法但为空"，不是报错**；2、3 才是错误。 | `architecture/public-contracts.md:3` | 否（§1.2 的表逐条给了含义，但词本身没定义） |
| 后端 | backend | 外部工具（Apktool / JADX / androguard）；它失败被记成一个值，不抛异常。 | `architecture/public-contracts.md:23`、`analysis-provenance.md:15` | public-contracts:23 否 · analysis-provenance:15 否（:15 说清是 3 个分析后端 + 1 个不依赖后端的） |
| 三后端齐备 / 三后端 | all three backends present | Apktool、JADX、androguard **三个都在**；只装两个时相关检查会 skip，skip 不是通过。 | `reports/release-process-dry-run.md:59`、`reports/portfolio-readiness-2026-11-18.md:59`、`reports/v1.0.0-release-checklist.md:326`、`how-to-verify.md:168`、`architecture/public-contracts.md:378`、`reports/ci-gate-coverage.md:80` | dry-run:59 是（已补）· portfolio:59 是（已补）· checklist:326 否 · how-to-verify:168 是（已补）· public-contracts:378 否（§7 只用这个词，不解释它）· ci-gate-coverage:80 否 |
| 索引 | index | 工作区库里从 DEX 抽出的符号表（类、方法、字段、调用点）；Smali 与 Java 不入表。 | `architecture/public-contracts.md:48` | 否 |
| 索引缺口 | index gap | 符号索引短于整个 APK 的那部分；**不等于**"后端没装"那种错误。 | `architecture/public-contracts.md:58` | 是（:56-60 的判据段） |
| 已发布 run | published run | 当前发布在工作区快照里的那一次运行；失败或取消的 run 不发布。 | `architecture/public-contracts.md:50` | 否 |
| 截断 | truncation | 某一步的输出撞上大小上限被截掉；运行仍算完成，报告写明有缺口。 | `architecture/public-contracts.md:48` | 否 |
| 调用点 / 调用边 | call site / call edge | 调用点 = 字节码里每一处调用（索引的一行）；调用边 = 按调用点聚合出来的两个方法之间的关系。⚠ 与 `analysis-provenance.md:143` 讲的 JVM `callsite` 对象同名但不是一回事。 | `architecture/public-contracts.md:106`、`architecture/public-contracts.md:245` | 否（定义在 :245；英文侧另有专门文档 `architecture/call-sites-and-edges.md`） |
| 计数含义 | count semantics | 每个计数字段到底数的是什么；同名不同义会把读者带到错的结论上。 | `architecture/public-contracts.md:234` | 是（§4 整节） |
| 出处 | provenance / source pointer | 一条记录来自哪个工具、哪份产物、哪个位置的指针（`Provenance.locator`）。**本仓库里"出处"才是 citation，"引用"不是——见下一行。** | `architecture/public-contracts.md:472` | 否 |
| 引用 | edge / reference (between two items) | ⚠ **不是 citation。** 这几份中文文档里的"引用"一律指两项之间的边（资源引用、交叉引用、引用边）；对应英文 *citation* 的词是"出处"。 | `analysis-provenance.md:36`、`architecture/public-contracts.md:30` | 否 |
| 引用点 | reference point (`const-string`) | 字符串常量被 `const-string` 指令引用的位置；与"调用点"是两种点。 | `analysis-provenance.md:34` | 否 |
| 说了算 | who wins | 两个后端给出同一字段时按哪条规则取值，不是"谁后跑谁覆盖"。 | `analysis-provenance.md:57` | 是（§2 标题即释义） |
| 覆盖度 | coverage (of the analysis) | 每个后端能产出哪几类结论的覆盖面；**不是**测试覆盖率，也不是"分析完成度"。 | `analysis-provenance.md:1` | 否 |
| 可复现 | reproducible | 换台机器、按同一相对路径仍能定位到同一处字节。 | `analysis-provenance.md:200` | 否 |
| 符号图 | symbol graph | 从 DEX 抽出的权威符号结构：类、方法、字段、调用点。 | `service-commitments.md:13` | 否 |
| 线索 | lead | 证据三级之一：怀疑但未确认，永远不能升为 `verified`。 | `service-commitments.md:13` | 否（正式定义在 `architecture/public-contracts.md:255`） |
| grounding 率 / 无依据断言率 | grounding rate / unsupported-assertion rate | 模型断言里带可解析出处的比例 / 不带的比例。 | `service-commitments.md:53` | 否 |
| 如实降级 | honest degradation | 样本超出已验证范围时如实说降级，不硬答。 | `service-commitments.md:121` | 是 |
| 缩小并重述 | narrow and restate | 题类短期不达标时缩小并重写服务承诺，而不是把失败题移出题集宣布通过。 | `service-commitments.md:134` | 是 |

### 七、退出码与契约面（`docs/proposals/`）

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 残缺 | partial | 运行结束了，但结果不完整；**不是**"损坏"。 | `proposals/exit-code-partial-read.md:21` | 否 |
| 截断 | truncation | 某一步被上限截断（退出码 5）；与"残缺"是两种不同的缺口。 | `proposals/exit-code-partial-read.md:21` | 否 |
| 外延 | denotation | 一个退出码所覆盖的运行集合；"收窄外延"= 某些运行不再返回它。 | `proposals/exit-code-partial-read.md:98` | 否 |
| 破坏面 | blast radius | 一次改动会打破的既有消费方与文档表述的范围。 | `proposals/exit-code-partial-read.md:160` | 否 |
| 契约快照 | contract snapshot | 契约表在仓库里的定稿副本，契约测试拿它比对。 | `architecture/public-contracts.md:353` | 是（"快照测试把同样的清单固化为回归门禁"） |

### 八、M10 验收

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 准备包 / M10 准备包 | M10 acceptance pack | 交给外部读者执行的 M10 验收材料包（清单、记录模板、读者包）。 | `reports/m10-acceptance-pack.md:1`、`reports/portfolio-readiness-2026-11-18.md:4`、`reports/v1.0.0-release-checklist.md:5`、`reports/v1.1.0-candidates.md:130` | acceptance-pack:1 是（标题即定义）· portfolio:4 否（已补于 :5）· checklist:5 是（已补）· candidates:130 否 |
| 独立验收 | independent acceptance | 由一个没参与实现的人执行准备包里的 40 项检查并给出结论。 | `reports/portfolio-readiness-2026-11-18.md:4`、`reports/v1.0.0-release-checklist.md:41`、`reports/v1.1.0-candidates.md:27` | portfolio:4 否（已补于 :5）· checklist:41 是（§1.2 标题括注）· candidates:27 是（已补） |
| 留人工 | left for a human reader | 脚本判不了、要由人读材料下结论的那几项检查。 | `reports/m10-selfcheck.md:25`、`reports/portfolio-readiness-2026-11-18.md:296`、`reports/v1.1.0-candidates.md:166` | m10-selfcheck:25 是（§2.2「明确留人工的 40 项」，从 :62 起）· portfolio:296 是（已补）· candidates:166 是（已补） |
| 三态 | three-state verdict | 一个验收项的三种结论：通过 / 不通过 / 未验证。 | `reports/m10-acceptance-pack.md:27` | 否（三个取值在 :81 才列出） |
| 卡点 | blocker (a logged defect) | 读者记下的一处文档缺陷：文档写的与实际行为不符。 | `reports/m10-acceptance-pack.md:47` | 否（§3.7 给了记法，没给这个词的定义） |

### 九、回归测试的三种说法

这个项目的规矩是"每个修复都要有一条**拿掉修复就变红**的测试"。这条规矩有三个词，
英文里只能各用一个词，容易混。

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 钉子 / 钉住 | nail / pin | 一条回归测试：**把修复拿掉，它就变红**。这是本项目规矩第 1 条要的测试。 | `reports/phase2-issue-list.md:4`、`reports/phase2-issue-list.md:455`、`reports/ci-gate-coverage.md:407` | 否（三处都没有一句定义） |
| 护栏 | guardrail | 防回归的测试，但在旧代码上**不一定**变红——所以它钉不住缺陷。 | `reports/phase2-issue-list.md:455`、`reports/coverage-guard-audit.md:71` | 是（phase2-issue-list:455 与钉子作了对照） |
| 假绿 | false green | 测试通过了，却没走到会出错的那条路径。 | `reports/phase2-issue-list.md:196` | 否（该行只出现一次，且没解释） |

### 十、四种"检查"，四种做法

仓库里有四种都叫"检查"的东西，英文读者容易塌缩成一个 review。

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 复核 | consistency review | 两份文本逐条比对，找不一致；不重新执行任何东西。 | `reports/ci-gate-coverage.md:1`、`reports/english-reader-review-2.md:1` | 否（只有标题） |
| 走查 | walkthrough | 按读者视角从头走一遍流程；与只做文本比对的复核不同。 | `reports/m10-reader-walkthrough-3rd.md:1`、`reports/final-outward-consistency.md:212` | 否（只有标题） |
| 演练 | rehearsal / dry run | 照着清单真做一遍；见第二节「只读演练」。 | `reports/release-process-dry-run.md:1` | 是 |
| 审计 | audit | 一处或一组缺陷的根因追查，结论通常是"要改哪里的机制"。 | `reports/coverage-guard-audit.md:1` | 否（只有标题） |
| 首读 | cold read | 没读过该文档的外部读者从零冷读一遍并给结论。 | `reports/next-engagements.md:343` | 否 |

---

## 故意不收的词

下面这些**不**收进表里，理由逐条写明——省得下一个来的人以为漏了。

| 词 | 为什么不给定义 |
|---|---|
| 工具与库名：Apktool、JADX、androguard、uv、pytest、ruff、mypy、vulture、SQLite、MCP | 正文里就是英文原样出现的，读者查官方文档即可；给它们写定义只会占版面。 |
| Python 与 Git 概念：venv、worktree、commit、annotated tag、`--force`、marker | 同上。`重打 tag` 收进表，是因为它在本仓库里有一个特定含义（不是"再打一次"，是"把标签移到另一个提交"）。 |
| 普通中文词：文件、读取、测试、命令、失败、通过 | 任何中文读者都懂，收进来是噪声。 |
| `结论` / `事实` / `线索` 的通用义 | 表里收的是它们**在本项目里**的三分法（见第五节），不是这三个词的一般含义。 |
| 数字：测试数、覆盖率、指纹值 | 由 `scripts/refresh-report-figures.py` 生成，写在 `docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` 标记之间。手抄会立刻过期；这一页只管词不管数。 |
| 里程碑编号 M5–M10 的具体内容 | 每个里程碑有自己的文档与验收线，术语表代替不了那些链接。 |
| `architecture/README.md` 里已有的四条英文定义 | 那里已经用英文写清了（agent service promise、frozen discipline、B1、the seven scoring rules）。本表只**指向**它们，不重复定义。 |
| `docs/status.md` 的快照与评分 | 那份文档自己声明了它是什么、它的基线是谁，而且它由测量脚本写，本轮不动它。 |
| `审计件`、`生成物`、`采集` | 各自那一段的句子本身就说清了——"一份**审计件**（由 `scripts/m6_level2_narrow_verify_audit.py` 生成）"、"## 4. 哪些数字是生成物，不许手改"、"重新**采集** trace 才是另一件事"。为它们单独立条只会让表变长、读者找不到真正要紧的那几条。 |
| `虚机`、`错误样本绑定`、`门槛` | 出现处都是短句或专名，前后文已经把意思给了：`干净工作树/虚机演练`、`包路径遍历、错误样本绑定、脱敏破坏证据链`、`验收目标（未来门槛，不是当前结果）`。 |

---

## 维护

- **新增一条的时机**：一份新文档第一次用了表里没有的词，而这个词读者会猜错。
- **改一条的时机**：某个词的含义变了（尤其是"同词不同义"的那几条——`判定`、`残缺` /
  `截断`、`工作区` / `工作树`、`快 / 集成`）。
- **行号会漂**：本表的 `file:line` 指向改动后的当前树。`docs/` 下的文档一改，行号就动；
  改动多的时候整表重算一遍，不要手改数字。
- **改了哪份文档，就在那一列标「已补」**——这样下一轮的人一眼知道哪些地方已经就地解释过，
  不用再补一遍。
- 本表不参与源指纹（`src/`、`tests/`、`pyproject.toml`、测量脚本之外的文件都不进指纹），
  所以改它**不需要**重测量。
