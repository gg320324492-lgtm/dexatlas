# `docs/reports/` 索引

这个目录里是 DexAtlas 从 Phase 1 到 Phase 5 收口之间的**69 份报告**
（**这是 2026-11-27 的快照**；份数是快照，不是常数——新增报告时把数改过来）。新读者打开这一层，
看到的是一堵墙；不知道哪一份是现状、哪一份是当时的快照、哪一份已经被后面的检查推翻了。

本页只做三件事：

1. 每份（或每一类）报告回答什么问题，**什么时候该看它**；
2. 本轮 v1.0.0 发版审计产生了哪些报告，它们的结论被并进了哪些改动；
3. 哪些是历史记录，**不该再当现状读**，以及该以哪一份为准。

本页不给出项目数字。凡出现数字的地方，都是从它指向的那份报告里抄来的，并在原地标了出处。
**报告里的数字都有基线**：同一件事在不同基线上读出来的数不一样，而报告本身不会替你更新。
所以读任何一份之前，先看它开头的基线声明。

---

## 分组一览

| 分组 | 份数 | 主要回答 |
|---|---|---|
| [§1 执行、评审与阶段结论](#1-执行评审与阶段结论phase-12) | 11 | Phase 1–2 做了什么、评审发现了什么、还剩什么 |
| [§2 M4 / M8 验收与模型可禁用性](#2-m4--m8-验收与模型可禁用性) | 5 | 里程碑的退出标准是怎么验出来的 |
| [§3 里程碑与下一轮候选](#3-里程碑与下一轮候选) | 2 | 下一轮可以做什么、每项做完算不算完 |
| [§4 发版材料](#4-发版材料v100--v110--v120) | 4 | 发版要发什么、凭什么、怎么核 |
| [§5 审计与走查](#5-审计与走查2026-11-17–20) | 48 | 发版前后几轮审计与走查找出来的问题，以及怎么处置的 |
| [§6 历史记录](#6-历史记录不要当现状读) | 1 | 不要当现状读的记录 |
| 合计（点名，去重） | 69 | 另有 0 份不点名；8 份报告被两处或三处点名（见下） |

**每个「份数」就是该节表格的行数**。要核某一节，就数那一节的行。
**份数是快照，不是常数。** 目录里每落进一份新报告，这个数与下面各组的份数就变一次
（C9 轮起的「逐行实测」口径沿用至今；最近新增 [phase5-acceptance.md](phase5-acceptance.md)、[c9-outward-info.md](c9-outward-info.md)、[c8-render-run.md](c8-render-run.md)、[phase5-failure-timeline.md](phase5-failure-timeline.md)、[phase5-machine-verification.md](phase5-machine-verification.md)、[phase5-crash-and-race-paths.md](phase5-crash-and-race-paths.md) 与 [phase5-remaining-goals.md](phase5-remaining-goals.md)）。
要核当前目录里到底有几份，直接数文件：

```bash
ls docs/reports/*.md | wc -l      # 减掉本页自己（README.md）就是报告份数
```

**下面 §1–§6 的每一行都点名了一个文件**，所以「哪几份没被收录」可以直接比出来。
（2026-11-27 复核（逐行实测，C9 轮起沿用该口径）：目录里 69 份报告中 69 份被分组表点名，
无遗漏、无虚指。分组表共 71 行，其中 7 行同时点名多份报告，行内点名 79 次、去重后是 69 份
（8 份报告被两处或三处点名）。
历史快照（2026-11-18 的 95、C9 轮的 98）与实测对不上——
那是只加行不核数累积出来的，且去平台化清理（2026-11-21）移除了 46 份，本页从 C9 轮起以「逐行实测」为准。）

> 分组表里的「份数」是该节表格的行数，不是目录总数；目录总数以 `ls` 实测为准。
M6 的基准报告不在本目录，在 [`docs/benchmarks/`](../benchmarks/)；里程碑计划在
[`docs/roadmap/`](../roadmap/)。本目录只收「一次检查留下的一份记录」。

**读不懂的词查哪张表**：[`docs/glossary.md`](../glossary.md) 是全仓术语对照表（中文 ↔ English），
收的是「读者读不懂就会猜错」的词——源指纹、契约活检、独占测量、两棵树、红/绿、证据包、判定……
表里还标了每个词在哪份文档的首次出现处有没有就地定义。

**对外作品集材料**：M15 起另设 [`docs/portfolio/`](../portfolio/)（不在本目录计数）——
[案例页骨架](../portfolio/case-page.md)（通用外部渠道，按[发布规划 §4](phase4-release-plan.md) 填写）与
[Portfolio Freeze 声明](../portfolio/freeze.md)（解冻信号与冻结期维护范围，与[执行单 §8](../roadmap/phase4-plan.md) 一致）。

---

## 1. 执行、评审与阶段结论（Phase 1–2）

| 报告 | 回答什么 | 什么时候看它 |
|---|---|---|
| [phase1-execution-report.md](phase1-execution-report.md) | Phase 1 执行报告（v0.1.0）：落地了什么、每项能力对应哪些文件。**README 徽章与执行报告里的 `<!--fig:…-->` 数字由 `scripts/refresh-report-figures.py` 填进这份文件的表格**，不是手写的。 | 想知道「报告里某个数字是从哪来的」时看它；想知道 Phase 1 的交付范围时看它。 |
| [phase1-maturity-assessment.md](phase1-maturity-assessment.md) | Phase 1 成熟度评估（评估对象 DexAtlas @ `b8ef71a`，2026-10-21）：只记「能跑出来、能指到行号」的证据，并给出阶段判断。 | 想看「当时为什么认为项目到了某个阶段」时看它。 |
| [phase1-review-report.md](phase1-review-report.md) | Phase 1 源码评审报告（基准 `8df894b`）：评审怎么做的、发现了什么、修了什么、推迟了什么（中文）。 | 要引用「44 条发现全部复验」或 Phase 1 评审结论时看它。 |
| [phase1-findings-ledger.md](phase1-findings-ledger.md) | Phase 1 复现台账（基准 `8df894b`）：每一条评审发现是怎么验出来的、现状指针在哪里。 | 要重跑或核对某条发现的复现步骤时看它。 |
| [phase2-issue-list.md](phase2-issue-list.md) | Phase 2 开工清单（基准 `8df894b`）：评审之后按发现整理的待办 issue，编号、范围与处置状态。 | 想核对「Phase 2 当时打算修什么」时看它。 |
| [phase3-baseline.md](phase3-baseline.md) | Phase 3 M5 基线校准：对外声明有什么证据、三份 benchmark 能否从原始 trace 重算、还剩哪些问题。 | 想确认「对外说的每个数都能重算」时看它。 |
| [phase5-acceptance.md](phase5-acceptance.md) | Phase 5 验收报告（基线 `origin/main` @ `33e4ba9`）：W1 侧车（安装形态二次验收 a–d 全通过）、W2 阶段契约（复测 ①–⑤，⑤ 的文档过时与完成态缺陷已由 PR #18/#19 修好）、W3/W4 备料的逐项判据与证据，含 16 张截图。**明确写出仍然开放的项**（见 §7：macOS/Linux 不纳入、打包 exe 未跑装了 jadx/apktool 的配置、MSI 未验证等；「前端模拟代码删除」已于 2026-11-26 收尾完成）。 | 要引用「Phase 5 做到哪一步」时看它；判据与证据都在里面，未覆盖的项也都在里面。 |
| [phase5-failure-timeline.md](phase5-failure-timeline.md) | Phase 5 失败/取消时间线走查（开发模式 + 浏览器 + 真后端，2026-11-26）：「取消」这条路径确实存在（`POST /cancel` → 管线在下一个检查点停 → run 记 cancelled、项目记 failed），「失败」分叉成三种界面结果（上传被拒 / 分析跑完却读到空 / 后端失败但分析完成）。**走查带出一个后端缺陷**：失败状态此前从不落库，界面会永远停在「分析中」（实测 4 分 44 秒）。含 9 张截图。**边界**：全程开发模式，未在打包 exe 里复验（未覆盖项逐条列在 §7）。 | 要引用「失败与取消在界面上是什么样」时看它；也解释了为什么 Phase 5 会修后端的失败落库。 |
| [phase5-machine-verification.md](phase5-machine-verification.md) | Phase 5 真机补测（2026-11-26）：打包 exe 在 JADX 1.5.2 + Apktool 2.11.1 + Androguard 4.1.4 齐全时跑出 **12 条证据**、`missing_backends: []`、`complete: true`（缺后端那档实测 10 条）；MSI 用 `msiexec /i … /passive` 退出码 **0** 装到 `C:\Program Files\DexAtlas Studio\`，装完能启动能分析。**`/qn` 在未提升的会话里装不上（退出码 1603）——机制限制是静默模式不做凭据提升，不是包的毛病；在已提升的会话里 `/qn` 装得上（2026-11-27 复验）**。升级 / 卸载 / repair 三条路径也各跑通。含 26 张截图。 | 要引用「打包产物在完整后端配置下真的能用」时看它；测量看不到的东西逐条列在 §4。 |
| [phase5-crash-and-race-paths.md](phase5-crash-and-race-paths.md) | Phase 5 管线崩溃形态与并发竞态（2026-11-27，打包 exe 上真实触发）：管线自己抛异常那条 `except Exception` 分支**第一次被真的走到**（故障注入：把一个普通文件放在本该是目录的地方），实测项目行 failed、未发布、**轮次自己的 errors 是空的**、HTTP 层没有错误码；并发下**「同一 APK 重复上传不会重复分析」是假的**（4 个同时上传每轮都跑起来，被发布那一轮的 `tool_versions.jadx` 被并发读成 null，界面于是说「JADX 没装」），`RUNNING` 表按项目号建键导致**正在跑的分析变得不可取消**。含 4 张截图。 | 要引用「管线崩了会是什么样、并发下哪里会打架」时看它；6 个待修缺陷逐条列在报告里。 |
| [phase5-remaining-goals.md](phase5-remaining-goals.md) | Phase 5 尚未完成的目标清单（2026-11-26）：把散在验收报告、走查报告、机器补测报告、状态页与运营清单里的未完成项收成一处，分四类——A 解冻范围内可直接做（4 件）、B 等作者提供账号/渠道/决策（4 件）、C 明确不在范围内不追（3 件）、D 需外部样本或别的机器（4 件）。**只做盘点与归类，不承诺执行**；并指出 Q2 报告里那条「三个端点不存在」的限制已过期。 | 要回答「Phase 5 说自己做完了，还剩什么」时看它。 |

## 2. M4 / M8 验收与模型可禁用性

| 报告 | 回答什么 | 什么时候看它 |
|---|---|---|
| [m4-review.md](m4-review.md) | M4 源码评审与验收：M4 的退出标准逐条是否达成。 | 要引用「M4 已验收」的依据时看它。 |
| [m4-e2e-run.md](m4-e2e-run.md) | M4 端到端实测：退出标准 2 的验收证据，实际跑出来的步骤与结果。 | 要引用端到端跑通的事实时看它。 |
| [m4-acceptance.md](m4-acceptance.md) | M4 验收演练（新用户视角）：只按仓库文档从 clone 等价状态出发，一步步走，看哪里走不通。 | 想知道「陌生人按文档能不能装起来」时看它。 |
| [model-disable-verification.md](model-disable-verification.md) | 模型能力可禁用性验证（M4 退出标准）：模型不可用时工具链是否仍然给出确定结果。 | 要引用「证据优先、不依赖模型」这条主张的依据时看它。 |
| [m8-install-rehearsal.md](m8-install-rehearsal.md) | M8 干净安装与故障恢复演练：装得上、坏掉后能恢复。 | 要引用安装与恢复能力的实测依据时看它。 |

## 3. 里程碑与下一轮候选

| 报告 | 回答什么 | 什么时候看它 |
|---|---|---|
| [v1.1.0-candidates.md](v1.1.0-candidates.md) | **需求候选清单**：**24 项候选**（2026-11-27 的 v1.2.0 登记轮新增 C18–C24），每项写明解决的缺口、可交付物、做完判据、依赖与估时（估时按仓库实测口径，不是拍脑袋）。**调研产出，不是已排期的计划。** | 要看「下一轮可以做什么、每项做完算不算完」时看它。 |
| [c9-outward-info.md](c9-outward-info.md) | **C9 的落地记录**：四份对外素材怎么补上联系方式、时区与可用性（作者给定的三项取值），开发阶段模拟值怎么就地标注，字符长度怎么复算，哪些留给主会话。 | 要发布素材、替换占位邮箱，或核对「对外素材里有没有未经授权的承诺」时看它。 |

## 4. 发版材料（v1.0.0 / v1.1.0 / v1.2.0）

| 报告 | 回答什么 | 什么时候看它 |
|---|---|---|
| [v1.0.0-ci-run-record.md](v1.0.0-ci-run-record.md) | `v1.0.0` 这个 tag 的**每一次 CI run** 落盘记录：run 编号、时间、headSha、逐 job 结论，以及 tag 为何被重打过多次、其中一次以 `failure` 结束（4 个 job 红）。 | 要查「这个发布版本的 CI 结论到底是什么」时看它。 |
| [v1.1.0-github-release-body.md](v1.1.0-github-release-body.md) | `v1.1.0` 的 GitHub Release 正文底稿：发布页面写了什么、数字与仓库材料怎么对应。 | 要核「v1.1.0 发布页正文」时看它。 |
| [v1.2.0-github-release-body.md](v1.2.0-github-release-body.md) | `v1.2.0` 的 GitHub Release 正文底稿：发布页面写了什么、数字与仓库材料怎么对应。 | 要核「v1.2.0 发布页正文」时看它。 |
| [social-preview-howto.md](social-preview-howto.md) | GitHub social preview 图怎么设（图只能手动设，GitHub 没有 API），以及图上每一个字、每一个数是从哪个文件的哪一行读出来的。 | 要换那张图、或要核对图上的数字与报告是否一致时看它。 |

发版本身的结果，以 [`docs/releases/v1.0.0.md`](../releases/v1.0.0.md) 与 git tag 为准，
不在本目录。

---

## 5. 审计与走查（2026-11-17–20）

这一节回答「本轮 v1.0.0 发版审计产生了哪些报告」。

这些报告**以只读审计为主**：审计方不改被核的代码或文案，只记录发现与依据，
改动由主线按清单执行。所以每份报告里既有「必须改的 N 处」，也有「已经改好了」的复核结果。
**报告的数字都锚在各自的基线上**——基线之后的变动写在报告开头的声明里，读的时候
先看那段。

| 报告 | 它回答什么 | 结论被并进了哪些改动 |
|---|---|---|
| [coverage-guard-audit.md](coverage-guard-audit.md) | 并发测量会不会污染覆盖率。结论：`.coverage` 是「一个 checkout 一份」的单例文件，测量脚本对它整体删除、追加写、整体读，三者之间没有互斥；并发会把别的进程的数据当成自己的测量结果写进报告。现有护栏只验分母与内部自洽，**没有一个验分子**，所以污染态的报告是内部完全自洽的、自检全绿。 | 根因修复进测量脚本本身：覆盖率数据文件按次私有 + 同 checkout 互斥锁（提交 `7910195`），以及「测量槽位只保护本 checkout 的报告」（提交 `9d5ea65`），两者都带回归测试 `tests/test_refresh_coverage_hygiene.py`。审计本身由提交 `62b40e8` 收进仓库。 |
| [changelog-vs-release-notes.md](changelog-vs-release-notes.md) | `CHANGELOG.md` 的 `[1.0.0]` 段、发版说明、Release 正文**三方同源核对**。结论：**仍须统一的 12 处**，最严重的是 CHANGELOG 同一节内对「退出码 6 是否已实施」自相矛盾，以及「MCP 十个工具」与同文件「十一个」直接冲突；另给出 retest3 / retest4 / 窄验证三套口径的区分规则。 | CHANGELOG `[1.0.0]` 段的 6 处进提交 `b60ae35`；发版说明与 Release 正文的相关条目进提交 `b9ed1d7`、`2459601`；本报告由提交 `a9f09e8` 收进仓库。 |
| [reader-dry-run.md](reader-dry-run.md) | 读者流程**实走演练**（只读）：真 clone、真装依赖、真跑命令，看一个外部读者按材料走会卡在哪。结论：**11 处材料与现实不符**（不抓第三方样本会 27 个 skip、容器构建时间两个口径、证据包条目数与 CLI 打印对不上等）。 | 要知道「验收材料照着走会不会卡住」时看它；材料已按它的发现修过三轮。 |
| [readme-map-audit.md](readme-map-audit.md) | README 文档地图完整性复核：21 处缺失/过期/中英不对称。 | 两份 README 的地图补齐并对齐（含报告目录索引与「怎么复核」入口）。 |
| [github-repo-metadata-proposal.md](github-repo-metadata-proposal.md) | GitHub 仓库元数据与可发现性复核（只读 + 提案）。 | LICENSE 恢复官方 Apache-2.0 全文；README 首屏接上「怎么复核」；Releases 页与 tag 对齐。 |
| [glossary-pass.md](glossary-pass.md) | 术语对照表这一轮的做法记录：那张表怎么来的、覆盖了哪些文档、补了哪些就地定义、哪些词**故意**不给定义。 | 想知道 [`docs/glossary.md`](../glossary.md) 为什么是现在这个样子、或要往里加词时看它。 |
| [readme-image-consistency.md](readme-image-consistency.md) | README 首屏与 social preview 图的**一致性核对**（只读）：图、两个徽章、首屏文字与它们各自的出处对不对得上，一个新读者十秒内会不会误读。结论：**14 条**（3 严重 / 6 中 / 5 低）。 | 要判断首屏会不会把人带偏时看它。 |
| [local-vs-ci-gates.md](local-vs-ci-gates.md) | 本地门禁与 CI 门禁的**平台差异审计**（只读）：37 处差异——路径语义、排序与 locale、编码与换行、CI 并行负载、工具版本、环境依赖。含一条要紧的：**CI 的测量门禁在 Linux 上恒绿却空转**。 | 要知道「本地判绿、CI 判红」这类问题还有哪些时看它。 |
| [case-studies-client-read.md](case-studies-client-read.md) | 案例材料的**客户视角复核**（只读）：三篇走查 + 四个包 + 案例索引 + 对外文案，数目与对应关系对不对得上。**11 条发现**。 | 客户按其中一处去数会不会数出另一个数时看它。 |
| [phase4-baseline.md](phase4-baseline.md) | **Phase 4 M11 基线**（2026-11-23）：对外状态文案收口（M8 统一为「交付完成，macOS 未验证」）、Workbench 六页现状与真实可运行流程、24 张四宽度基线截图、页面状态矩阵与缺口清单。 | Phase 4 后续里程碑（M12 设计规范、M13 Workbench 实现）从这里接手；loading/error/empty 三类 UI 缺口归 M13。 |
| [case-studies-third-package.md](case-studies-third-package.md) | 第三个案例证据包的**交接报告**：为第三个案例跑出的**新 run**（走 REST API），四个包的自带校验都过；附**入库清单**与 9 处要跟着改的说法。**2026-11-18 起这些包已全部入库**（四个证据包、四次分析），对外文案已按本清单改完。**⚠️ 2026-11-20 起四个包随清单第四键（schema 2）重打，本文的包哈希与 run id 描述的是上一批包。** | 要把第三个包放进仓库时看它；重打包后的现状看 [c16-manifest-fourth-key.md](c16-manifest-fourth-key.md)。 |
| [evidence-package-isolation.md](evidence-package-isolation.md) | 证据包的**隔离边界**核对：包里到底会被打进什么（逐个打开四个已入库的包，再现跑一个包核过），「内部核对记录不得随证据包外发」这条今天成立到什么程度、缺的是哪一道闸。结论：那条通路今天走不通——源码片段只可能来自被分析 APK 的反编译树；但**这条性质只靠实现细节成立**，代码里没写死、没检查、清单里也没声明。 | 打包时的守卫（反编译树之外的文件、指向树外的链接都不进包）、契约文档 §5.3 的明文、5 条红→绿回归测试（`tests/test_evidence_package_isolation.py`）。清单的声明层（第四个 `not_included` 键）已由 [c16-manifest-fourth-key.md](c16-manifest-fourth-key.md) 落地（schema 2）。 |
| [docker-examples-gap.md](docker-examples-gap.md) | **C6**：Docker 镜像里到底能不能跑仓库自带的案例（只读调研）。结论：**不能**——`Dockerfile` 只 COPY 四样文件加 `src/`，镜像里没有 `examples/`，今天只能挂卷；镜像里 13 个 CLI 子命令在样本可达时全流程通。 | 只出调研，未动 `Dockerfile`/CI/`examples/`。建议已由 [docker-image-samples.md](docker-image-samples.md) 落地。 |
| [docker-image-samples.md](docker-image-samples.md) | **C6 方案 A 的落地**：镜像里能不能跑仓库自带的案例。结论：**能，而且由 CI 验证**——`Dockerfile` 末尾多一行 `COPY examples/ examples/`（放在最后一次 `uv sync` 与后端安装之后，改样本不会让依赖层失效）；CI 的 `docker` job 多一步，在刚构建的镜像里用**相对路径**跑通 `analyze examples/demo-app/demo.apk`，核出退出码 0 与 classes / methods / call sites / call edges 四个非空计数；`docs/install.md` 的 Docker 段改成「镜像自带样本」，挂卷只留「用你自己的 APK」。**边界**：镜像内未本地实跑（本地不构建镜像），由 CI 验证。 | 改动进了 `Dockerfile`、`.github/workflows/ci.yml` 的 `docker` job（job 显示名与 `docs/status.md` 的 job 行同步改）、`docs/install.md` 与本索引的份数；本报告已登记进 `scripts/check-doc-citations.py` 的 `DOCS` 清单。`tests/` 的回归测试按本轮约束未加，需求写在报告的「需要主会话接手」一节。 |
| [post-release-rehearsal.md](post-release-rehearsal.md) | 「**发布后修正并重打 tag**」这条路径的端到端演练（只读，演练记录不是发版记录）。结论：12 条（R1–R12）里 **8 条**「§3 步骤 8 本该拦住但没拦住」，另 3 处判据含糊；给出三条该补的判据——按**指纹**而不是数字决定要不要重测量、本地 tag 与远端 tag 分开查且引用检查排在 tag 移过之后、把「同一批数字相等」写成一份让每份副本都有东西在比的清单。 | 只出记录。三条建议尚未落进清单，等主线处置。 |
| [outward-number-parity.md](outward-number-parity.md) | **判据 C 的落地**：对外文本里的同一批数字（测试总数、快/集成、passed、skipped、xfailed、一方覆盖率），机器逐个数比对。结论：仓库内的文本彼此一致、也与执行报告一致；**GitHub 上已发布的那一份 Release 正文不一致**——它写的是旧树上的数（1620 一族），而 tag `v1.0.0` 指向的树上是 1695 一族。 | 新增门禁 `scripts/check-release-numbers.py` + CI job `release-numbers`；**没有**改文本里的任何数字。门禁第一次跑就是红的，等主线重新发布 Release 正文。 |
| [figures-coverage-design.md](figures-coverage-design.md) | **测量数字自动覆盖设计**（只读调研）：怎样让「数字随测量走」管住所有手写位置。结论：源指纹只覆盖 `src/`、`tests/`、`pyproject.toml` 与测量脚本本身，`docs/` 下手写的数字不受它管。 | 只出调研（提交 `d6b8edf`），方案尚未落成改动。 |
| [handover-tails-audit.md](handover-tails-audit.md) | 三个已合并窗口**交接尾巴**的逐条只读核对：每条按「已落实 / 未落实 / 进行中」三档判定，判定只认当前树上的证据。 | 三条未落实项（D13 / R3 / R4）分别进提交 `6842a98` 与 `07129f0`；本报告的 `file:line` 只在它声明的基线树上成立。 |
| [v1.1.0-candidate-c10-manifest.md](v1.1.0-candidate-c10-manifest.md) | 证据包清单的**第四个键**（核对 + 登记，**这一轮不实施**）：清单今天只有三个 `not_included` 键，没有一条说「包里只有本次分析的文件」；补第四个键是**公共契约变更**——升 `schema_version`、改**五个文件里的九处**钉死、同步验收材料、处置**四个已入库的旧包**（都是 `schema_version = 1`，新代码下会验不过）。 | 登记成 v1.1.0 候选 **C16**，按作者的决定**留到 v1.1.0**；C10 改成「主体完成」（守卫 + 契约明文 + 5 条红→绿测试已落地）。本报告的 `file:line` **已进引用检查器的 `DOCS` 名单**，有自动门禁在看。 |
| [c16-manifest-fourth-key.md](c16-manifest-fourth-key.md) | C16 的**落地记录**：第四个 `not_included` 键（`outside_analysis`）+ `schema_version = 2`，九处钉死与验收材料同步，四个已入库包**重新分析并导出**（新 run id 与 sha256 全表），红→绿已证（2 条新测试先红后绿）。 | 要看当前四个包的 run id / sha256、清单 v2 的形状，或「哪些留给主会话重测」时看它。 |
| [evidence-incomplete-backend-wording.md](evidence-incomplete-backend-wording.md) | 「后端未完成」那条 `verified` 证据的**文案**：读者预演 M-2 记的那两条互斥陈述（E-0007 说 jadx 没完成、E-0008 说 jadx 为 5 个类产出了 7 个方法的真实 Java）读起来像「证据链断了」。结论：问题在**措辞** —— 旧文案只说了「没跑完」，读起来却像「没产出」。 | 改的是文案、不是等级：「did not complete」改成「did not complete **in this run**」，并补一句「已经交出来的产物仍在证据里」；统计字段与公共契约一个字没动，9 条新回归测试守着文案与等级。 |
| [c6-build-time-from-ci.md](c6-build-time-from-ci.md) | C6 判据 (a) 要求的**新口径**：镜像构建时间的**唯一落点** —— 取自 CI 那个 `docker` job 的实测（46 秒），别处只引用它、不另抄一份数。 | 只出记录，引用它的地方已按新口径改过。 |
| [gate-self-checks.md](gate-self-checks.md) | 门禁自己站得住：同源门禁**拆成两段比较**（工作副本对工作副本的数；**GitHub 上那份已发布的正文对 v1.0.0 tag 树里的报告** —— 否则下一轮一重测，它就拿新数去比旧正文而变红），配 6 条回归测试并证过红→绿；Docker 那条门禁补了 4 条**只读文件、不跑 Docker**的快测试；另写了一份 `.dockerignore`（镜像的构建上下文此前带着整个 `.git`）。 | 门禁与测试已合入；`tests/` 在指纹覆盖范围内，**合入后要重测一轮**。 |
| [figures-auto-write-landing.md](figures-auto-write-landing.md) | 「**测量数字自动覆盖**」的机制落地：脚本按标记发现所有带生成数字的文档统一写，不再靠人记得同步；另加一条硬保险 —— pytest 的汇总行**读不出来就中止并说清量到了什么、没量到什么**（上一轮 tag 的测量 job 就是把一轮 13 项的自检读成 0 项而红的）。 | 9 条新测试（旧实现下 8 红、新实现 9 绿）；**合入后要重测一轮**并同步各文档里的手写数字。 |
| [m8-4-note-and-c17.md](m8-4-note-and-c17.md) | 两件小事：M8 演练 §6 的 **M8-4** 加一句「此后已如何解决」（退出码 6 早已落地，那一节写的是 v1.0.0 之前的实况 —— 读者核对 G3 会看到相反结论并在 ★ 阻断项上记假卡点 ✓；早年的对账报告就指出该加 ✓，一直没落地 ✓）；以及把「**散文里的手写数也改成标记**」登记成 v1.1.0 候选 **C17** ✓（这一轮撞出的三个闭环里最根治的那个 ✓）。 | 只加前向指针、正文未改 ✓（那一节是历史记录 ✓）；候选清单的计数从 16 改齐到 17 ✓。 |
| [c5-c6-status-alignment.md](c5-c6-status-alignment.md) | 候选 **C5 与 C6 的状态与现实对齐**：C6 走的判据 (a) 已落地（镜像自带样本 ✓、CI 在镜像内实跑并核计数 ✓、构建时间的新口径单点存放 ✓），C5 的 multi-DEX 证据包早已入库 ✓；**「镜像内未本地实跑、由 CI 验证」这一点如实留在状态里** ✓（不写成「已验证跑通」✓）。 | 候选清单里**写着一个数的 13 处口径全部改齐** ✓（已完成 5→7 ✓、仓库内可做 5→3 ✓、总数仍 17 ✓）。 |
| [platform-gate-inventory.md](platform-gate-inventory.md) | 候选 **C15** 的核对方法三件套：**清单**（`scripts/platform-gates.json` ✓）、**机制**（`scripts/check-platform-gates.py` ✓，接进测试套件 ✓）、**记录**（本文件 ✓）—— 哪些门禁是**平台相关**的、差异为什么有、哪些差异是**合法的**（如 POSIX launcher 测试在 Windows 上按设计跳过 ✓）。 | 守的是**性质**而不是个数 ✓（「每个跑 uv 的 job 都重定向了临时目录」✓），因此**每加一个 CI job 不必再改一个写死的数** ✓；方法查出一个**真缺陷**：CI 的 `contracts-without-jadx` job 缺临时目录重定向 ✓。 |
| [citation-value-comparison.md](citation-value-comparison.md) | 让引用检查器能验「**句中含具体值**」的那一类 ✓：引用句里的值与被引那一行的实际值比 ✓ —— 本轮那 3 条错位**全在这一类** ✓，值比对能一次抓住 ✓。认不出的（裸数字 ✓、限值 ✓、版本号 ✓、派生值 ✓……）归「**无法比对**」而不是误报 ✓。 | 判据与边界写在报告里 ✓（表格行按单元格 ✓、散文按距离 ✓、点了符号就不比值 ✓、点名另一棵树就整段不比 ✓）；**13 处真发现**全在 release body 的附录表里 ✓。 |
| [citation-anchor-declarations.md](citation-anchor-declarations.md) | 让「只指位置」的引用**自己声明它声称的内容** ✓：一条引用后跟一个 `anchor:` 跨度 ✓（稳定的名字或源码片段 ✓ —— **不随行号漂** ✓、**也不随数值漂** ✓）→ 机器就能比 ✓。试点在**契约表** ✓（59 处逐条改完 ✓）。 | 过程中**实测出其中 13 处原本就指错的地方** ✓（检查器此前看不见 ✓ —— 它们落在非空行上 ✓）；检查器新增「声明型文档」的强制规则 ✓；另查出检查器 `clauses()` 的一个既有缺陷 ✓（围栏代码块会让后面的引用失去检查 ✓），补丁交给主会话排期 ✓。 |
| [handwritten-numbers-audit.md](handwritten-numbers-audit.md) | 「数字随测量走」还差哪些手写数：**只读审计** ✓ —— `docs/` 与仓库根下每一处**手写的测量数** ✓，逐处说清「是什么数 ✓、谁在检它 ✓、陈旧了会怎样 ✓、该改成标记还是另设门禁 ✓」。 | 查出 **10 处没人守** ✓ 的手写测量数 ✓（**静默过期** ✓ —— 没有任何门禁会报 ✓）；按「静默过期 **且** 读者会照着核对」排了优先级 ✓。 |
| [card-travels-with-the-measurement.md](card-travels-with-the-measurement.md) | 把**社交预览卡片**收进「数字随测量走」✓：测量脚本写完报告之后**自己重画**首页卡片 ✓ —— 那三个闭环里的第三个 ✓（卡片画的是报告里的数 → 测量要写新数 → 候选与卡片不符 → 那条测试失败 → 测量不肯写 → 卡片永远更新不了 ✓）。 | 全量套件的归因也补进了报告 §5.1 ✓（红项逐条归因 ✓，没有一条是本窗口造的 ✓）。 |
| [ci-temp-redirect-fix.md](ci-temp-redirect-fix.md) | C15 的核对方法查出的**真缺陷**与修法：CI 的 `contracts-without-jadx` job 跑 `uv` 却**没把临时目录重定向到工作区** ✓ → 补上 ✓；清单里它的声明从 `defect` 改成 `yes` ✓（性质从「被记着」变成「被守着」✓）；另加一条回归测试**堵住 `defect` 这个逃生舱** ✓。 | 那条「数着 10/12 个 job」的测试**已退役** ✓ —— C15 的机制接管 ✓（守性质而不是守个数 ✓）。 |
| [declarations-outward.md](declarations-outward.md) | 把「引用带声明」**推到对外文本** ✓：**208 处**「只指位置」的引用全部带上声明 ✓、**重锚 80 处** ✓（先改读者会照着核对的那几份 ✓ —— 作者定的范围 ✓）。 | 过程中**实测出 19 处原本就指错的引用** ✓；6 条 pytest 失败与 16 处漂移**还原 HEAD 验过** ✓ —— 都是本批之前就红的 ✓。 |
| [unguarded-numbers-gates.md](unguarded-numbers-gates.md) | 给审计查出的 **10 处无人守** ✓ 的手写测量数配门禁（或明确不归 ✓）：新门禁守的是**性质** ✓（「文档说的与测量出来的一致」✓），**不是写死的数** ✓ —— 这一轮刚栽过两个写死数的跟头 ✓（CI 的 job 数 ✓、引用行号 ✓）；另加回归测试**堵住 `defect` 逃生舱** ✓，并把那条「数着 10/12 个 job」的测试退役 ✓。 | `scripts/check-unguarded-numbers.py` ✓ + `scripts/unguarded-numbers.json` ✓ + `tests/test_unguarded_numbers.py` ✓；**红→绿**证过 ✓；「仍然没人守的」那一栏**不空** ✓ ✓。 |
| [case-studies-run-correspondence.md](case-studies-run-correspondence.md) | 案例证据包与「三次分析」的**实测对应关系**（基准 `d43369b`，sha256 逐个实测）：三个案例包实际只覆盖**两次**分析——`demo` 与 `api-integration` 同出 `run_e112e717…`，两者 `report.md`/`report.html` 逐字节相同；`obfuscated` 出自另一次 `run_8d6735d…`。还查出**走查正文引用的会话与附件承载的运行不是同一次**（耗时与 run id 对不上），以及包内 `report.json` 与散装 `report.json` 差两个时间戳字段。含「第三个包补不补」的结论、方案与代价。**这段结论已被后续补包推翻——见 [case-studies-third-package.md](case-studies-third-package.md)。** | 要对外说清「几个案例、几次分析、几份证据」，或要把第 3 篇换成它自己那次分析的包时看它。 |
| [claim-mismatches.md](claim-mismatches.md) | M1–M24 的复核量于 `8df894b`（2026-10-21），此后落地了五个大变更，文件开头就说明了这一点。 | [phase2-issue-list.md](phase2-issue-list.md) 第 8 节与当前源码。 |
| [prose-to-markers.md](prose-to-markers.md) | 把**散文里的手写测量数**改成标记 ✓：两页 how-to-verify 的「应当是 N 个测试」「N passed」等，现在由测量统一写 ✓ —— **加测试不用再手改任何数字** ✓（三个闭环里最根治的一个 ✓）。**机制这轮真改了三处** ✓：加 `tests.trio` 这个 figure kind ✓（守卫一个字没改 ✓、幂等 ✓）；**写的口径与发现的口径用同一把尺子** ✓（代码块与行内代码里的标记不再被写 ✓ —— 但执行报告代码块里的标记是**它自己那份数的拷贝** ✓，必须跟着数字走 ✓，所以单独 `copies=True` ✓）；**配不平的标记不吃掉整段** ✓（跳过并报出来 ✓ —— 旧行为是按最近闭标记截断 ✓，正是吃正文那一步 ✓）。 | 5 个新回归测试**在旧实现上 5 red** ✓；**「没取样本」那一行的具体条数已删** ✓（它是另一个环境的汇总 ✓、没有键可挂 ✓ —— 只留 skip 的理由分类 ✓，不再长得像当前树的数 ✓）。**留给主会话**：对外素材的数要重测后同步 ✓；机制还差两处（守卫挪进自检段 ✓、collect-only 期望输出改读标记 ✓）。 |
| [c17-markers-everywhere.md](c17-markers-everywhere.md) | **C17 的收尾**：把剩下三处手写测量数收进机制 ✓——两页 §2.3 的 `pytest --collect-only` 期望输出改成 `tests.collect.*` 标记（**围栏写入通道**：这几句的文本就是测量本身，是「围栏是引文」的唯一例外 ✓）；`documents read` 改成 `documents.count` 标记（复用 version-claims 的统计口径 ✓）；测试文件表的行集合核对**写进测量记录**（`table.missing_rows`/`stale_rows`，拒绝路径也写 ✓）；卡片 sidecar 增 `suite` 块并与测量记录的 `SUITE_NAMES` 对账（44 → 50 项检查 ✓）。 | 机制 + 页面 + 守卫 + 11 条新回归测试，红→绿证过 ✓；**测量未跑**（按分工留给主会话统一重测）——两页的数因本窗口新增 9 个测试而过期，守卫 6 red 是闭环本身的样子，重测后由机制自动转绿 ✓。 |
| [c13-report-citations.md](c13-report-citations.md) | **C13 的收口**：引用检查器改为**结构性收集**——`collect_documents()` 自动读取 `docs/reports/` 下全部报告，不再靠手工登记 `DOCS` 名单；每份历史报告要么被检查、要么登记进显式排除清单 `REPORT_EXCLUSIONS`（每份附原因）。**红→绿已证**：一份带坏引用的新报告，不改任何名单，落盘即被检查并让退出码变 1（旧手工名单实现下为 0）；另修好 6 份既有报告因名单重构位移的 16 处引用。 | 40 份历史报告的逐份回锚（登记 `TREE_DOCUMENTS` + 文档补指纹声明）与候选 C13 的三条新规则（空白行 / 越界 / 悬空裸引用）留给后续；报告 `docs/reports/c13-report-citations.md`。 |
| [c8-render-run.md](c8-render-run.md) | **C8 的落地**：CLI 增加「渲染某一次运行」的能力 ✓——`dexatlas runs` 列出某项目的全部运行、`--run` 原样取回某次运行的记录（工具版本、起止、错误）；`dexatlas render` 把某次**已完成且仍是已发布**的运行渲染成可复核目录（三格式报告 + 证据包 zip + `run.json`），包写入后当场过 `verify_package`/`verify_citations` ✓。公共契约向后兼容新增：CLI 活检 15→18、静态总数 49→52，契约表/CHANGELOG/两页 how-to-verify/发版材料同步 ✓；15 条集成测试覆盖输出结构、退出码、「未发布/已被替换的 run 拒绝渲染」与「渲染只读工作区」 ✓。 | `src/dexatlas/cli/main.py`（runs/render 两个子命令）、`src/dexatlas/reports/run_render.py`（新模块）、`src/dexatlas/reports/evidence_package.py`（抽出 `package_contents`/`package_manifest` 共用底层）、`scripts/verify-public-contracts.py`、`scripts/m10_selfcheck.py`（A6 判据升级 + 条目数探测适配）、`tests/test_run_render.py`、`tests/test_public_contracts.py`、`tests/test_m10_selfcheck.py`、`docs/architecture/public-contracts.md`、`CHANGELOG.md`、`docs/install.md`、`README.md`、两页 how-to-verify、M10 读者包 A6 两段、执行报告测试文件表 + 本索引。**测量已由主会话统一补跑**（2026-11-22，`3489ddc`）；M10 演练 #9 的「当场记下」建议更新为「先记 run id，可用 runs/render 回看已发布那次，但重跑会换掉已发布运行」。 |
| [c9-outward-info.md](c9-outward-info.md) | **C9 的收尾**：作者给定三项取值（`hello@dexatlas.example` 模拟邮箱、`Asia/Shanghai`、工作日 10:00–18:00）后，四份对外素材各补一段「Availability and contact」✓，模拟值就地标注 ✓，**不写响应时长** ✓（判据的保守执行）；素材字符长度复算 ✓；候选清单计数改齐（已完成 9 → 10）✓。 | 要替换占位邮箱、核对素材的可用性表述，或看「哪些留给主会话」时看它。 |
| [phase4-release-plan.md](phase4-release-plan.md) | **Phase 4 M15 发布冻结规划**（2026-11-23）：M15 七步逐条对照（现状/缺口/建议执行方式）、80 秒演示与 3–5 分钟讲解的脚本提纲、README 双语截图更新清单、通用渠道案例页模板骨架、发布前核查清单与 Portfolio Freeze 声明草稿。规划文档——执行、录制、门禁与发布动作尚未发生，不宣称任何未执行步骤已通过。 | Phase 4 收口时按它排执行顺序；录演示、改 README、写渠道页前先看它。 |
| [phase4-walkthrough.md](phase4-walkthrough.md) | **Phase 4 M15 独立用户 walkthrough**（2026-11-23）：零上下文用户按 README 在干净 clone（`main` @ `22c0621`）走完整链路（安装 → 后端 → analyze → 只读命令 → runs/render → fixtures → REST API → Workbench → agent 成功流/503 拒绝流 → 证据包）的逐步实测记录。**结论：通过**，4 项低危/信息发现（F1 分支进度、F2 install-backends 不打印 export 行、F3 Workbench `/api` 子集与 REST API 表不同、F4 端口占用自救）只记录未修。 | 判断「陌生人按 README 能不能走通」时看它；修 F2–F4 前先读原始发现。 |
| [phase4-release-review.md](phase4-release-review.md) | **Phase 4 M15 发布前本地评审**（2026-11-23）：全量本地门禁、Phase 4 源码评审（M11–M15）、发布数字一致性、walkthrough 四项低危发现追踪。未跑、未盯 GitHub CI（按用户要求）。 | 发布前判断「本地门禁全绿了吗、还有哪些待办」时看它。 |
| [phase4-demo-shots.md](phase4-demo-shots.md) | **Phase 4 M15 演示镜头表**（2026-11-23）：新 80 秒演示视频（`docs/assets/phase4-demo-80s.mp4`）逐镜说明画面来自哪一次真实运行（Workbench + agent 真实模型调用，Playwright 真实交互驱动）、每个读数在哪份接口/状态文件可复核。 | 核对演示视频每一帧的证据来源，或替换旧 demo 入口前确认素材边界时看它。 |
| [phase4-tech-talk-script.md](phase4-tech-talk-script.md) | **Phase 4 M15 技术讲解脚本**（4 分钟，2026-11-23）：分段与画面同[发布规划 §2.2](phase4-release-plan.md)；所有画面均来自真实运行（Workbench 与 agent 真实模型调用），解说只引用画面可见事实。讲解视频已按本表渲染为 `docs/assets/phase4-tech-talk-4min.mp4`（233 s，无配音）。 | 核对讲解视频解说与画面是否一致，或重录/配音时看它。 |
| [phase4-q2-acceptance.md](phase4-q2-acceptance.md) | **Phase 4 Q2 桌面应用验收报告**（2026-11-24）：按 Q2 补充单 §6 八维度验收矩阵逐项给结论与证据（产品方向/信息架构/视觉语言/组件一致/状态诚实/可访问性/技术边界/冻结解除范围），引用四张 Tauri 真窗口截图（`docs/assets/phase4-q2/`）；记录真实链路验证（demo.apk 三步 8618 实测）与已知限制（后端无 `/api/backends`、`/runs`、`/cancel`；分析页阶段推进为前端模拟；未做安装包分发）。 | 判断「Q2 桌面应用能否收尾、证据在哪」时看它；下一阶段定界（部分解冻）的依据。 |
| [phase4-q2-perf-walkthrough.md](phase4-q2-perf-walkthrough.md) | **Q2 后 Tauri 原型真机性能走查**（2026-11-24）：release exe + 真实 8618 后端，九项测量（冷启动 892ms、路由最慢 82ms、证据渲染 64ms、导出 56–78ms、轮询 CPU 0.06%/内存 607MB、缩放无破版）全部达标；问题清单 P1–P8 逐项标注修复状态（P1–P4 已修，P5–P7 待小修，P8 无需行动）。 | 判断「桌面原型性能基线」或核对 X2 问题清单修复状态时看它。 |

## 6. 历史记录：不要当现状读

下面这些文件**记录的是当时的状态**。直接读它们会得到过期的结论。

注意这一节是**横切视角**，不是新的一组：下面点名的文件都已经计在上面里面了，
这里只是把它们从「按主题分组」的角度再挑出来标一次。

| 文件 | 为什么是历史记录 | 以哪一份为准 |
|---|---|---|
| [phase1-findings-ledger.md](phase1-findings-ledger.md) | 台账记的是**复验当时**的状态（基准 `8df894b`），文件开头指明每条发现的现状在别处。 | [phase1-review-report.md](phase1-review-report.md) 与 [phase2-issue-list.md](phase2-issue-list.md)。 |

另外三条通则，比单份文件更要紧：

- **凡带基线声明的报告，数字只在该基线上成立。** §5 的审计报告各自锚在自己的基线上，
  基线之后的变动写在报告开头；跨报告引用同一个数字前，先确认基线是否一致。
- **「只读审计」不等于「结论已落地」。** §5 的报告只记录发现，改动由主线执行（本轮当场
  实施了改动的是 `evidence-package-isolation.md` 与 `docker-image-samples.md`）；
  判断某条发现是否已修，看对应提交与当前文件，不要只看报告。
- **历史陈述不是过期数字。** 过期数字是「现在仍然这样陈述，但已经不成立」；历史陈述是
  扫描时别把它们混为一谈。

---

## 这份索引也会过期

这份索引本身也是一份手写文档：它记录的是某一刻的目录状态。**新增报告时，请把它加进来**——
放进对应分组，并检查它属于哪一档（现状、审计结论、还是历史记录）。同一次改动里，如果
某份报告被取代了，也顺手把上一节「历史记录」那一行的指向改掉。
