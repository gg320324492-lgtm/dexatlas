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
| 口径 | measurement basis | 这个数是在哪个分母、哪套题、哪条判分规则下算出来的。 | `docs/roadmap/phase3-plan.md:58` `anchor: 口径`、`docs/reports/v1.1.0-candidates.md:31` `anchor: 口径` | phase3-plan:58 否 · candidates:31 否 |
| 一方代码覆盖率 / 一方 | first-party coverage | 本仓 `src/dexatlas` 自身代码的覆盖率，不含第三方库。 | `docs/reports/coverage-guard-audit.md:414` `anchor: 一方代码覆盖率` | 否 |
| 落盘 | persisted to disk | 由工具写进磁盘、并成为后续读数来源的那一步。 | `docs/reports/coverage-guard-audit.md:167` `anchor: 落盘` | 否 |
| 分片 | coverage data shard | coverage 并行模式下每个进程各写各的独立数据文件；进程之间会互相抹掉。 | `docs/reports/coverage-guard-audit.md:63` `anchor: 分片` | 否 |
| 弱模块表 | low-coverage module table | 覆盖率明显偏低的模块清单，由测量脚本生成；数字变陈旧时它先变陈旧。 | `docs/reports/coverage-guard-audit.md:79` `anchor: 弱模块表`、`docs/reports/phase1-execution-report.md:89` `anchor: <!--fig:coverage.weak_modules-->` | coverage-guard-audit:79 否 · phase1-execution-report:89 是（`<!--fig:coverage.weak_modules-->` 标记内） |

### 二、门禁、CI 与判定

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|

### 三、引用完整性（这个项目的承诺就落在这几个词上）

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 探针 | probe | 插进代码里记录调用参数的测试挂钩，不是产品功能。 | `docs/reports/phase2-issue-list.md:218` `anchor: 探针` | 否 |

### 四、套件与测试口径

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 去掉的测试 | deselected tests | 被 pytest 的 `-m` 过滤掉的用例；pytest 把它记作 deselected，不是 removed。 | `docs/how-to-verify.md:134` `anchor: 去掉的测试` | 否（已补于 :135） |
| 集成样本 | third-party integration fixture | 不随仓库分发、由 `scripts/fetch-fixtures.sh` 拉取的第三方测试 APK；不取它，相关测试会 skip。 | `docs/how-to-verify.md:24` `anchor: 集成样本` | 否（§2.0 解释了怎么取，但词本身没定义） |
| 验收线 | acceptance threshold | 认定某个里程碑通过所需的最低分数门槛。 | `docs/how-to-verify.md:438` `anchor: 验收线`、`docs/benchmarks/service-regression-set.md:159` `anchor: 验收线` | how-to-verify:438 是（已补）· service-regression-set:159 是 |
| 未达成 / 未验证 | not met / not verified | **未达成** = 量过但没过线；**未验证** = 从未测过。两者对读者的意义不同：前者是坏消息，后者是不知道。 | `docs/how-to-verify.md:429` `anchor: 未达成` | 否（已补于 :410） |
| 参考线 | reference threshold | 预先写下、只作对照比较的分数线；**不等于**验收线，对照参考线的报告不算验收成绩。 | `docs/how-to-verify.md:354` `anchor: 参考线` | 否（已补于 :334） |
| 冻结纪律 | freeze discipline | 调优前冻结题集与门槛，不许靠删掉做对的题来提高通过率。 | `docs/how-to-verify.md:438` `anchor: 冻结纪律`、`docs/benchmarks/service-regression-set.md:155` `anchor: 冻结纪律`、`docs/architecture/README.md:204` `anchor: The frozen discipline.** The rule the acceptance plan` | how-to-verify:438 是（已补）· service-regression-set:155 是（§5，并链到 architecture/README.md）· architecture/README:204 是（英文定义） |
| 窄验证 | narrow verification | 只在六道已知失败面上重跑的缩小复测：6 题 × 3 轮。 | `docs/how-to-verify.md:37` `anchor: 窄验证` | 否（已补） |
| 转通过 | flipped to pass | 原先判失败、这一轮改成通过的题。 | `docs/how-to-verify.md:439` `anchor: 转通过` | 是（已补） |
| 确定性修复题 | deterministic-fix task | 预期修法确定、可判对错的题（窄验证六题中的五题）。 | `docs/how-to-verify.md:439` `anchor: 确定性修复题` | 是（已补） |
| 题次 | question instance | 一道题在一轮里的一次计分。 | `docs/benchmarks/service-regression-set.md:264` `anchor: 题次` | 否 |
| 缺席事实 | the fact of absence | "某样东西不存在"这件事本身，必须按与失败记录相同的形状记下来。 | `docs/benchmarks/service-regression-set.md:276` `anchor: 缺席事实` | 否 |

### 五、证据、结论与交付物

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 结论 / 事实 / 线索 | finding / fact / lead | 结论 = 工具读出且带能解析的出处；事实 = 工具读到的字节；线索 = 模型的说法，只能待核，永远不能升级成结论。 | `docs/how-to-verify.md:438` `anchor: 结论`、`docs/roadmap/phase3-plan.md:39` `anchor: 线索`、`docs/architecture/README.md:151` `anchor: lead` | how-to-verify:438 是（"模型的结论永远不是事实"）· phase3-plan:39 否 · architecture/README:151 是（英文表：`lead` = 静态分析或模型提示的风险指标） |
| 证据链 / 出处模型 | evidence chain / provenance model | 记录每条结论由哪个工具、哪个版本、从哪个字节位置读出来的那条链。 | `docs/how-to-verify.md:39` `anchor: 出处模型`、`docs/analysis-provenance.md:880` `anchor: 证据链` | how-to-verify:39 是（括注一句）· analysis-provenance:880 是（§4 逐步给命令） |
| 公共契约 | public contract | 对外承诺并版本化的行为表面：CLI 子命令、退出码、REST 端点、MCP 工具、报告 schema。 | `docs/architecture/public-contracts.md:1` `anchor: 公共契约`、`docs/roadmap/phase3-plan.md:7` `anchor: 公共契约` | public-contracts:1 是（整份文件就是它）· phase3-plan:7 否 |
| 报告三件套 | the report trio | 同一份分析的 Markdown / JSON / 离线 HTML 三个文件。 | `docs/benchmarks/m6-verify3-plan.md:125` `anchor: 后端路径随执行环境而定（历史值见 m6-level2-retest4.md 复现命令），以后端检查三件套齐全为准` | m6-verify3-plan:125 是（但那里的"三件套"指后端检查三件套，是另一回事） |
| 交付包 | delivery package | 客户可以直接审阅的成品：报告 + 最小证据包 + 案例说明。 | `docs/roadmap/phase3-plan.md:66` `anchor: 交付包` | 否（实义在 :141、:149） |
| 工作区 | workspace | 存项目、报告与证据的磁盘目录，`--workspace` 指的就是它；与 git 的"工作树"是两回事。 | `docs/architecture/public-contracts.md:51` `anchor: 工作区`、`docs/roadmap/phase3-plan.md:56` `anchor: 工作区` | public-contracts:24 是（`--workspace` 出现在命令行表里）· phase3-plan:56 否 |
| 交叉引用 | cross-reference (xref) | 一个符号引用另一个符号的位置；CLI 子命令是 `xrefs`。 | `docs/how-to-verify.md:98` `anchor: 交叉引用` | 否 |
| 脱敏 | redaction | 从导出包里删掉敏感字符串，并记录删了什么。 | `docs/roadmap/phase3-plan.md:152` `anchor: 脱敏` | 否 |
| 阻断项 | blocking item | 验收前必须关闭的问题，不能被高分或重要项抵消。 | `docs/roadmap/phase3-plan.md:219` `anchor: 阻断项` | 否（:101 那行写的是「阻断/重要/可选」三类） |
| 收口 | close out | 把对外陈述与证据对齐之后定稿，不再改动。 | `docs/roadmap/phase3-plan.md:89` `anchor: 收口` | 否 |
| 停止点 | stopping point | 本阶段停止扩功能的界线，之后由真实反馈决定下一步。 | `docs/roadmap/phase3-plan.md:45` `anchor: 停止点` | 否（§1.2 只有标题「达标后的停止点」） |
| 反向测试 | negative test | 断言缺陷确实会发生的测试，与回归护栏相反。 | `docs/roadmap/phase3-plan.md:161` `anchor: 反向测试` | 否 |
| 已验证 / 受限 / 未验证 | verified / limited / unverified | 对外声明清单里每条陈述的三种标记。 | `docs/roadmap/phase3-plan.md:104` `anchor: 已验证` | 否（只列出三值，未解释"受限"） |

### 六、契约表与分析溯源里的词（`docs/architecture/`、`docs/analysis-provenance.md`、`docs/service-commitments.md`）

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 公共契约 | public contract | 对外承诺并版本化的行为表面：CLI 子命令、退出码、REST 端点、MCP 工具、计数的含义、报告 schema；改动要显式升版本。 | `docs/architecture/public-contracts.md:1` `anchor: 公共契约`、`docs/roadmap/phase3-plan.md:7` `anchor: 公共契约` | public-contracts:1 是（整份文件就是它）· phase3-plan:7 否 |
| 退出码 | exit code | CLI 退出码。**1 是"答案合法但为空"，不是报错**；2、3 才是错误。 | `docs/architecture/public-contracts.md:3` `anchor: 退出码` | 否（§1.2 的表逐条给了含义，但词本身没定义） |
| 后端 | backend | 外部工具（Apktool / JADX / androguard）；它失败被记成一个值，不抛异常。 | `docs/architecture/public-contracts.md:23` `anchor: 后端`、`docs/analysis-provenance.md:15` `anchor: 后端` | public-contracts:23 否 · analysis-provenance:15 否（:15 说清是 3 个分析后端 + 1 个不依赖后端的） |
| 索引 | index | 工作区库里从 DEX 抽出的符号表（类、方法、字段、调用点）；Smali 与 Java 不入表。 | `docs/architecture/public-contracts.md:48` `anchor: 索引` | 否 |
| 索引缺口 | index gap | 符号索引短于整个 APK 的那部分；**不等于**"后端没装"那种错误。 | `docs/architecture/public-contracts.md:58` `anchor: 索引缺口` | 是（:56-60 的判据段） |
| 已发布 run | published run | 当前发布在工作区快照里的那一次运行；失败或取消的 run 不发布。 | `docs/architecture/public-contracts.md:50` `anchor: 已发布 run` | 否 |
| 截断 | truncation | 某一步的输出撞上大小上限被截掉；运行仍算完成，报告写明有缺口。 | `docs/architecture/public-contracts.md:48` `anchor: 截断` | 否 |
| 调用点 / 调用边 | call site / call edge | 调用点 = 字节码里每一处调用（索引的一行）；调用边 = 按调用点聚合出来的两个方法之间的关系。⚠ 与 `docs/analysis-provenance.md:143` `anchor: call site` 讲的 JVM `callsite` 对象同名但不是一回事。 | `docs/architecture/public-contracts.md:106` `anchor: 调用点`、`docs/architecture/public-contracts.md:245` `anchor: 调用点` | 否（定义在 :245；英文侧另有专门文档 `architecture/call-sites-and-edges.md`） |
| 计数含义 | count semantics | 每个计数字段到底数的是什么；同名不同义会把读者带到错的结论上。 | `docs/architecture/public-contracts.md:234` `anchor: 计数含义` | 是（§4 整节） |
| 出处 | provenance / source pointer | 一条记录来自哪个工具、哪份产物、哪个位置的指针（`Provenance.locator`）。**本仓库里"出处"才是 citation，"引用"不是——见下一行。** | `docs/architecture/public-contracts.md:477` `anchor: 出处` | 否 |
| 引用 | edge / reference (between two items) | ⚠ **不是 citation。** 这几份中文文档里的"引用"一律指两项之间的边（资源引用、交叉引用、引用边）；对应英文 *citation* 的词是"出处"。 | `docs/analysis-provenance.md:36` `anchor: 引用`、`docs/architecture/public-contracts.md:30` `anchor: 引用` | 否 |
| 引用点 | reference point (`const-string`) | 字符串常量被 `const-string` 指令引用的位置；与"调用点"是两种点。 | `docs/analysis-provenance.md:34` `anchor: 引用点` | 否 |
| 说了算 | who wins | 两个后端给出同一字段时按哪条规则取值，不是"谁后跑谁覆盖"。 | `docs/analysis-provenance.md:57` `anchor: 说了算` | 是（§2 标题即释义） |
| 覆盖度 | coverage (of the analysis) | 每个后端能产出哪几类结论的覆盖面；**不是**测试覆盖率，也不是"分析完成度"。 | `docs/analysis-provenance.md:1` `anchor: 覆盖度` | 否 |
| 可复现 | reproducible | 换台机器、按同一相对路径仍能定位到同一处字节。 | `docs/analysis-provenance.md:200` `anchor: 可复现` | 否 |
| 符号图 | symbol graph | 从 DEX 抽出的权威符号结构：类、方法、字段、调用点。 | `docs/service-commitments.md:13` `anchor: 符号图` | 否 |
| 线索 | lead | 证据三级之一：怀疑但未确认，永远不能升为 `verified`。 | `docs/service-commitments.md:13` `anchor: 线索` | 否（正式定义在 `docs/architecture/public-contracts.md:260` `anchor: lead`） |
| grounding 率 / 无依据断言率 | grounding rate / unsupported-assertion rate | 模型断言里带可解析出处的比例 / 不带的比例。 | `docs/service-commitments.md:53` `anchor: grounding 率` | 否 |
| 如实降级 | honest degradation | 样本超出已验证范围时如实说降级，不硬答。 | `docs/service-commitments.md:121` `anchor: 如实降级` | 是 |
| 缩小并重述 | narrow and restate | 题类短期不达标时缩小并重写服务承诺，而不是把失败题移出题集宣布通过。 | `docs/service-commitments.md:134` `anchor: 缩小并重述` | 是 |

### 七、退出码与契约面（`docs/proposals/`）

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 残缺 | partial | 运行结束了，但结果不完整；**不是**"损坏"。 | `docs/proposals/exit-code-partial-read.md:21` `anchor: 残缺` | 否 |
| 截断 | truncation | 某一步被上限截断（退出码 5）；与"残缺"是两种不同的缺口。 | `docs/proposals/exit-code-partial-read.md:21` `anchor: 截断` | 否 |
| 外延 | denotation | 一个退出码所覆盖的运行集合；"收窄外延"= 某些运行不再返回它。 | `docs/proposals/exit-code-partial-read.md:98` `anchor: 外延` | 否 |
| 破坏面 | blast radius | 一次改动会打破的既有消费方与文档表述的范围。 | `docs/proposals/exit-code-partial-read.md:160` `anchor: 破坏面` | 否 |
| 契约快照 | contract snapshot | 契约表在仓库里的定稿副本，契约测试拿它比对。 | `docs/architecture/public-contracts.md:5` `anchor: 契约快照` | 是（"快照测试把同样的清单固化为回归门禁"） |

### 八、回归测试的三种说法

这个项目的规矩是"每个修复都要有一条**拿掉修复就变红**的测试"。这条规矩有三个词，
英文里只能各用一个词，容易混。

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 护栏 | guardrail | 防回归的测试，但在旧代码上**不一定**变红——所以它钉不住缺陷。 | `docs/reports/phase2-issue-list.md:455` `anchor: 护栏`、`docs/reports/coverage-guard-audit.md:71` `anchor: 护栏` | 是（phase2-issue-list:455 与钉子作了对照） |
| 假绿 | false green | 测试通过了，却没走到会出错的那条路径。 | `docs/reports/phase2-issue-list.md:196` `anchor: 假绿` | 否（该行只出现一次，且没解释） |

### 九、四种"检查"，四种做法

仓库里有四种都叫"检查"的东西，英文读者容易塌缩成一个 review。

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| 审计 | audit | 一处或一组缺陷的根因追查，结论通常是"要改哪里的机制"。 | `docs/reports/coverage-guard-audit.md:1` `anchor: 审计` | 否（只有标题） |

---

### 这一轮新引入的两个说法

| 术语 | English | 一句话定义 | 出现位置（`file:line`） | 首次出现处是否给了定义 |
|---|---|---|---|---|
| **静态条数 / 实跑条数** | static count / live count | 契约的**静态条数**是脚本里 `check()` 调用点的数目（55）；**实跑条数**是那次真跑出来的条数（53 或 54，依可用后端而定）。两者不是一回事。 | `docs/architecture/public-contracts.md` §7 | 是 |


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
