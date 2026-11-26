# DexAtlas 当前状态

**最后更新：** 2026-11-26 · **对应版本：** v1.1.0（2026-11-25 发布；v1.0.2 于 2026-11-24 发布；v1.0.1 于 2026-11-21 发布、tag 现指 `3489ddc`；v1.0.0 于 2026-11-17 发布、tag 现指 `6e90317`；M4 评审详见[评审报告](reports/m4-review.md)）· **当前阶段：** Phase 4 收尾完成，Q2 桌面应用阶段完成（2026-11-24）；**Phase 5 工程交付与验收均完成（2026-11-26）：W1 侧车进程、W2 阶段级进度契约、W3/W4 备料已合入 main；打包 exe 安装形态全链路与 W2 后复测均已通过**（见[Phase 5 验收报告](reports/phase5-acceptance.md)）；Portfolio Freeze 部分解冻（B）——仅允许修桌面应用的缺陷、性能与可用性问题，新功能重新评审；M10 独立验收**已通过**（2026-11-20，外部验收人执行：40 项 39 通过 / 0 不通过，重评 97.5% / 96.3%，均 ≥90%；验收记录随 2026-11-21 的去平台化清理移除；逐里程碑状态见 §4.0）

这份文档回答两个问题：**现在在哪**，**还剩什么**。

- 「交付了什么」和「怎么交付的」在[执行报告](reports/phase1-execution-report.md)里
- 「每条结论由谁支撑、怎么自己核对」在[分析覆盖度与证据来源](analysis-provenance.md)里
- **换一台机器继续做**看[交接说明](HANDOVER.md)——现状、重建步骤、以及接下来做什么
- 「这个项目现在成熟到什么程度」在[成熟度评估](reports/phase1-maturity-assessment.md)里
- 「评审挖出来、还没修的」在[Phase 2 issue 清单](reports/phase2-issue-list.md)里
- 「三阶段的计划」在[路线图](roadmap/ROADMAP.md)里
- [Phase 3 计划](roadmap/phase3-plan.md)的实施进度与证据见 §4.0，M10 独立验收已通过（2026-11-20，重评 97.5% / 96.3%）
- [Phase 4 执行单](roadmap/phase4-plan.md)（最终决策 A + D + G）定义作品集收尾、软件设计与 Workbench UI 的范围；完成后默认进入 Portfolio Freeze
- [Phase 4 Q2 补充单](roadmap/phase4-q2-supplement.md)（2026-11-24 批准）**解除桌面应用范围的冻结**：在同一仓库立项原创桌面应用（Tauri + React），按四步 UI 方法设计与迭代；收尾条件见 [Q2 收尾单](roadmap/phase4-q2-closure.md)。设计规范（信息架构、视觉 token、组件清单、状态矩阵、接线边界）见[桌面应用设计规范](architecture/desktop-app.md)。其余 Freeze 规则继续生效
- **Q2 已完成（2026-11-24）：** 桌面应用 DexAtlas Studio 交付——组件库 + 画廊（Q2-M1）、核心工作流接入真实数据（Q2-M2：首页拖拽上传 → 分析三区 → 详情三栏与证据抽屉 → 报告导出）、四态与可访问性打磨（Q2-M3-T2）、Windows Tauri 真窗口原型与四步标准截图（Q2-M3-T1/T3）。验收按补充单 §6 八维度逐项通过（验收当时记录的三项限制：后端无 `/api/backends`、`/runs`、`/cancel` 端点；分析页阶段推进为前端模拟；未做安装包分发——**前两项已被 Phase 5 关闭**：三个端点现在都在，分析页的阶段推进也已换成真实阶段事件；「未做安装包分发」仍然成立），结论与证据见[Q2 验收报告](reports/phase4-q2-acceptance.md)；收尾单交付物与退出条件已逐项回填。**Q2 之后定界：部分解冻（B）**——仅允许修桌面应用的缺陷、性能与可用性问题，新功能重新评审；其余 Freeze 规则继续生效。
- **Phase 5 工程交付完成、验收完成（2026-11-26）：** [执行单](roadmap/phase5-plan.md)的 W1 侧车进程真接入（PR #13，`3625862`）、W2 阶段级进度契约（PR #14，`9614cb0`；`GET /api/projects/{id}/runs/{run_id}/stages`，独立只读端点）与 W3 C12 备料 / W4 发版后运营清单已合入 main。**验收动作也已做完**：打包 exe 的安装形态全链路经二次真机验收（判据 a–d 全通过，全程 8618 无监听，前端请求打在侧车自己的端口上），W2 合入后已按端到端走查同口径复测。首轮验收与两次复测各自暴露的缺陷已分别由 PR #18（契约文档与实现相反）、#19（完成态「证据」格停在「待处理」）、#20（侧车装不起来 + 前端锁死 8618 回退）、#21（三处陈旧文案）修好；走查的 P1/P3/P4 由 PR #15/#17 修好。逐项判据、证据与**仍然开放**的项见[Phase 5 验收报告](reports/phase5-acceptance.md)。**收尾批次（2026-11-26）又关闭了七项**：打包 exe 在 jadx + apktool + androguard 齐全时跑出 12 条证据、`complete: true`；MSI 装得上（`msiexec /i … /passive` 退出码 0）；强杀宿主不再留孤儿后端（Windows 作业对象，且 `cargo test --lib` 进了 CI 门禁）；failed / cancelled 时间线真机走通；「打开来源」内联展示源码；角标不再夸大；run 进终态即停止轮询。另修掉走查带出的一个后端缺陷：分析失败的状态此前从不落库，界面会永远停在「分析中」。**仍然开放四项**（验收报告 §7.3）：macOS/Linux 明确不纳入、非 MSIX 容器下的启动、MCP 面是否暴露阶段工具的取舍记录、W4 清单的一处账号口径——**均不挡住 Phase 5**。**此后所有任务都算作 Phase 5 的任务**（作者指示 2026-11-26）；未完成目标的完整盘点见[Phase 5 尚未完成的目标清单](reports/phase5-remaining-goals.md)。其中「前端模拟代码删除」已于 2026-11-26 收尾完成：无 run 数据如实显示状态未知，runs 不可用显示错误与重试入口）。
- M15 作品集材料在 [portfolio/](portfolio/)：[通用外部渠道案例页](portfolio/case-page.md)（不点名平台、不虚构联系方式）与 [Portfolio Freeze 声明](portfolio/freeze.md)（四类解冻信号与冻结期四类维护，与执行单 §8 一致）
- 每次发布的具体内容在 [releases/](releases/) 里

---

## 1. 快照

| | |
|---|---|
| 已发布版本 | v0.1.0 · v0.1.1 · v0.1.2 · v0.1.3 · v0.2.0（2026-11-14 已发布，见[发版说明](releases/v0.2.0.md)） · v1.0.0（2026-11-17 已发布，见[发版说明](releases/v1.0.0.md)） · v1.0.1（2026-11-21 已发布，[GitHub Release](https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v1.0.1)） · v1.0.2（2026-11-24 已发布） · **v1.1.0**（2026-11-25 已发布，Q2 桌面应用 + 稳定性批次，见[发版说明](releases/v1.1.0.md)） |
| 测试 | <!--fig:tests.total-->1880<!--/fig--> 个（<!--fig:tests.fast-->1731<!--/fig--> 快 + <!--fig:tests.slow-->149<!--/fig--> 集成） |
| 一方代码覆盖率 | <!--fig:coverage.pct-->93.4%<!--/fig--> |
| 类型检查 / lint | `mypy` strict、`ruff` lint + format，均通过 |
| CI | **15 个 workflow job、tag 上 16 次并行运行**（`test` 是 3.12/3.13 矩阵；「只在 tag 上跑的测量比对」在 push 与 PR 上跳过，所以那边是 15 次）：Lint / Python 3.12 / 3.13 / 部分后端 / 桌面前端单测 / 桌面端 Rust 单测（仅 Windows）/ M3 对比重跑 / Docker / 依赖审计 / 公共契约活检（带 Java 后端与不带两种）/ M10 自查 / 门禁覆盖自查 / 社交预览卡片核对 / 对外文本发布数字核对 / 只在 tag 上跑的测量比对。每次 push 到 `main`、PR 到 `main`、推 `v*` tag 都会跑一遍；**每一次 run 的逐 job 结论见 [CI run 记录](reports/v1.0.0-ci-run-record.md)** |
| 成熟度评估 | 修复前的基线 **5.50 / 10**（六个加权维度，见[评估报告](reports/phase1-maturity-assessment.md)）；今天的分数要重跑才有 |

> M6 层级 2 的执行层修复（判分链路、预算分类、重试、检索兜底）已在本分支
> 落地并通过代码级测试；6 题 × 3 轮窄验证显示 4/6 题转化、确定性子集 4/5，
> 但该轮运行不完整（53/54 条 trace，预算超支至 410,256 tokens）。针对首轮
> 窄验证暴露失败面的四项修复（协议泄漏纠偏重试、partial 措辞对齐、api-key
> 常量池检索引导、descriptor 连写模板）之后，窄验证二轮（6 题 × 3 轮 × 3
> 配置，54 条 trace 完整，
> [m6-level2-narrow-verify2.md](benchmarks/m6-level2-narrow-verify2.md)）**未达
> 窄验证判据**：DexAtlas 转通过 2/6、确定性修复题 2/5（门槛 ≥4/6、≥3/5）。
> 修复后三轮完整重测（[m6-level2-retest4.md](benchmarks/m6-level2-retest4.md)）
> DexAtlas 49/60 = 81.7%，仍未达 B1 验收线，B1 保持未关闭；按验收方案停止
> 投入，转方案 3（现状披露）。在此之上落地的预算效率四项修复（resources
> 收口、notice 折叠、string excerpt 截断、空转软提示）与行裁剪机制之后，
> 窄验证三轮（6 题 × 3 轮 × 3 配置，54 条 trace 完整，
> [m6-level2-narrow-verify3.md](benchmarks/m6-level2-narrow-verify3.md)）仍**未达
> 窄验证判据**：DexAtlas 转通过 3/6、确定性修复题 3/5（门槛 ≥4/6、≥3/5）；
> 实测 380,881 tokens，在 450,000 授权之内。窄验证二、三两轮连续未达后
> （第一轮运行不完整、不计为判定），按
> [m6-verify3-plan.md](benchmarks/m6-verify3-plan.md) §7 停止，**方案 3
> （现状披露）为最终定稿路径**，不再追加修复轮或模型调用。本页其余测量数字
> 仍对应修复前代码（`main` `fbca3d5` 及更早）。

**CI 的十五个 workflow job 各自覆盖一种配置**，不是重复（`test` 是 3.12/3.13
矩阵，展开后是**十六次并行运行**；下表逐行列出这十六次运行）：

| Job | 覆盖什么 |
|---|---|
| Tests (Python 3.12) | 全部后端 |
| Tests (Python 3.13) | **两个外部后端都不在**——JADX 和 Apktool 需要 Java，Androguard 是 Python 包，还在 |
| Tests (Apktool only, no JADX) | **Apktool 在、JADX 不在**——Smali 回退存在的理由 |
| M3 comparison stays reproducible | 从已提交的 92 题对比 trace 重算八项指标，**报告与数据保持可复现** |
| Docker image builds and analyses a bundled sample | 镜像里三个后端真的能跑；镜像自带的样本在镜像内分析得通（退出码 0，类/方法/调用点/调用边的计数非空） |
| Dependency audit | 锁文件的已知漏洞 |
| Lint and format | ruff、mypy、**actionlint**（workflow 文件本身）、**版本状态陈述检查** |
| Public contracts (live) | 公共契约活检实跑：三个后端齐备时跑 `scripts/verify-public-contracts.py`，退出码要判 |
| Public contracts (live, no Java backends) | 同一份契约再活检一遍，但机器上**没有 JADX 与 Apktool**（`DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 置空，不走 PATH 查找）——契约不能只在后端齐备时才成立 |
| M10 acceptance self-check | 跑 `scripts/m10_selfcheck.py`（只读、零成本），M10 验收材料的自动化判据 |
| Every gate is run by something | 跑 `scripts/check-gate-coverage.py`：**每一条门禁都得有东西跑它**，不能只写在文档里 |
| Social preview card | 仓库首页那张卡片上的数要与报告里的数一致——图片没法被人 diff，所以这一步由机器做 |
| The outward texts agree on the release numbers | 对外文本里手抄的发布数字要与执行报告一致（`scripts/check-release-numbers.py`） |
| Desktop unit tests | 桌面前端的单元测试（`npm run test`，vitest）：阶段映射、locator 落点分类、侧车端口解析——桌面端此前零测试，这些回归只有真单测能守 |
| Desktop Rust unit tests | 桌面端 Rust 侧的单元测试（`cargo test --lib`，**只在 Windows 上跑**）：作业对象兜底、侧车生命周期——被测代码（Job Object）只存在于 Windows，别处跑等于什么都没测 |
| The report's figures describe the tagged tree | **只在推 tag 时跑**：用 `refresh-report-figures.py --check` 重测一遍并比对，报告里的数字必须描述被 tag 的那棵树 |

第三个 job 存在的原因值得记一句：它曾经**从未在 CI 上跑过**，
于是两个假定 JADX 已安装的测试一直是绿的，而 Smali 回退——那个「JADX 不可用时
仍能读出代码」的机制——实际上没被测过。

---

## 2. 已发布

| Tag | 日期 | 主题 |
|---|---|---|
| `v0.1.0` | 2026-10-14 | Functional Foundation — 可用的静态分析流水线 |
| `v0.1.1` | 2026-10-19 | Foundation Hardening — 修了从未生效的 Smali 回退 |
| `v0.1.2` | 2026-10-20 | The Acceptance Checklist, Actually Met — 5 个自建样本 + 演示视频 |
| `v0.1.3` | 2026-10-20 | Evidence That Points Back — 交叉引用成为证据、locator 可移植、文档自校验 |
| `v0.2.0` | 2026-11-14 | The Agent Layer, Open to a Caller — M0~M3 全套 + workbench 六屏；发版说明见 [releases/v0.2.0.md](releases/v0.2.0.md) |

v0.1.1 到 v0.1.3 修的是同一类问题的三个实例：**一个看起来像成功的缺陷**。
详见执行报告第 3 节。

---

## 3. 阶段验收的状态

**原计划书 1.4 节的 8 项验收清单已全部达成。**
[路线图的 1.4 退出清单](roadmap/ROADMAP.md)用的是原计划书的原话，
每一项后面都能指到实际交付物。

**Phase 1 已于 2026-10-21 验收通过**，基准是固定的提交
`a1e81ce8ae262b84fa06bc5a3afb995fd0238660`（milestone tag `phase1-acceptance-2026-10-21`）。
**那不是 v0.1.3**——它比 v0.1.3 领先 76 个提交。评审做出的东西「在 Phase 1 验收时（2026-10-21）一个都尚未发布」；那之后 v0.1.3 才于 2026-10-20 打上 tag（见第 2 节），评审成果的发布状态以 [releases/](releases/) 与 CHANGELOG 为准。

按路线图约定的评审机制，Phase 1 的源码审核是 Phase 2 的准入条件，
**Phase 2 的任务清单在审核结论之后写**，而不是照搬原计划
（原计划的 Agent 架构设想建立在「代码不存在」的假设上）。

评审协议的五步，全部走完：

| 步骤 | 状态 |
|---|---|
| 1. 版本提交 | 完成：五个 tag（v0.1.0 ~ v0.2.0）、仓库链接、可复现命令 |
| 2. 架构与代码审核 | 完成：三个并行审核（核心实现 / 接口与安全边界 / 测试可靠性），共 44 条发现，**每一条都在新基线上逐条复核过** |
| 3. 成熟度评估 | 完成：[成熟度评估](reports/phase1-maturity-assessment.md)，六个加权维度。**5.50 / 10 是修复前的基线**，不是这棵树的当前分数 |
| 4. 评审报告 | 完成：[评审报告](reports/phase1-review-report.md) |
| 5. 重新规划下一阶段 | 完成：[Phase 2 计划](roadmap/phase2-plan.md)（M0 ~ M4）+ [Phase 2 issue 清单](reports/phase2-issue-list.md) |

**验收记录**在[这里](releases/phase1-acceptance-2026-10-21.md)——
它同时说了验收**没有**声称什么。

审核用了一个方法值得记下来：**每个审核 agent 都被要求去破坏实现，看测试会不会红**。
44 条发现里有相当一部分是「删掉这段代码，测试全绿」——也就是说，
**这些缺陷不是被测试发现的，是被「测试没发现」这件事本身暴露的**。

两轮审核一共挖出 **21 类**「宣称完成了、实际没有完成」（见第 6 节）。
审核时建议先看执行报告的**第 3 节**：那里记录了十五个开发过程中发现并修复的
真实缺陷（3.1 ~ 3.15），其中九类属于同一个模式，以及它们各自是怎么被发现的。

---

## 4. 还剩什么

这一版关掉了原来五项里的四项。先说还开着的，再说这一轮新发现的。

### 4.0 Phase 3 进度（截至 2026-11-22，B1 已关闭、Phase 3 退出标准已达成）

Phase 3 按[作品集计划](roadmap/phase3-plan.md)的 M5–M10 推进。下表只列**已合入
本分支**的产物，并写明每项还差什么；没有证据的一律标未开始或未验证。**M10
独立验收已通过（2026-11-20，外部验收人执行：40 项 39 通过 / 0 不通过 / 0 未验证，19 项阻断项全过；按原权重重评 97.5% / 96.3%，均 ≥90% 达成）。Phase 3 的退出标准中，M6 层级 2 的 B1 验收线仍未达成——修复后三轮完整重测 49/60 = 81.7%（逐轮 15/16/18），低于 90% 合计线，按验收方案定稿走「方案 3：现状披露」，不再追加修复轮；B1 已于 2026-11-22 达成并关闭（见下）。**2026-11-21 追加独立测量**（作者决定，换模型不换题集；预算同步放开至 96k 任务预算 / 80 步）：GLM-5.3-Flash 经本地网关对同一冻结 20 题跑 3 轮 × 3 配置，DexAtlas 逐轮 17/18/18，三轮合计 **53/60 = 88.3%——仍低于 ≥54/60（≥90%）的 B1 合计线**（差 1 题），单轮线（≥16/20）三轮全部达成；A 30.0%、B 30.0%；trace 与报告见 [m6-level2-glm.md](benchmarks/m6-level2-glm.md)（traces：[r1](benchmarks/m6-level2-glm-traces-r1.json)/[r2](benchmarks/m6-level2-glm-traces-r2.json)/[r3](benchmarks/m6-level2-glm-traces-r3.json)）。B1 合计线在 DeepSeek-V4.1-Flash 上达成（56/60 = 93.3%，逐轮 18/20/18），B1 于 2026-11-22 关闭；GLM（53/60 = 88.3%）与 MiniMax（49/60 = 81.7%）两套基线留档，三模型成绩分开陈述不混排。`v1.0.0`（tag 2026-11-17，现指向 `6e90317`）已发布，发版说明见 [docs/releases/v1.0.0.md](releases/v1.0.0.md)；v1.0.1（2026-11-21）是文档/测量/门禁侧的后续修正版，其 tag 树的 `src/` 相对 v1.0.0 有 7 个文件的 agent 指令与证据目录支持改动；生产分析流程未变，但「源码完全相同」的说法不准确。**（文中的 B1 验收线，英文说明见 [Architecture → Glossary](architecture/README.md#glossary)。）

| 里程碑 | 状态 | 证据 / 还差什么 |
|---|---|---|
| M5 基线校准 | **已完成** | [phase3-baseline.md](reports/phase3-baseline.md)：声明清单、三份 benchmark 由已提交 trace 重算、演示素材的 scripted/真实模型标注 |
| M6 服务回归集 | **已完成（B1 验收线达成）** | 20 题已冻结在 `100b191`（[service-regression-set.md](benchmarks/service-regression-set.md)）；层级 0 确定性判分 **20/20**（零模型）；层级 1 scripted 演练完成（[m6-level1-scripted.md](benchmarks/m6-level1-scripted.md)）——scripted 是替身模型，成绩原样公开，只证明发题/trace/判分管线端到端可用，不是模型能力基线；层级 2 真实模型批次已完成（[m6-level2-real.md](benchmarks/m6-level2-real.md)，全部数字由脚本从 [m6-level2-traces.json](benchmarks/m6-level2-traces.json) 重算）：MiniMax-M3.1-Flash 对冻结 20 题独立跑 3 轮，DexAtlas 24/60（40.0%，逐轮 45%/40%/35%）、A 源码文本 24/60（40.0%）、B 结构化检索 18/60（30.0%）——**未达验收线（每轮 ≥80%、三轮合计 ≥90%），验收结论「未通过」**；全部 trace 合计 853,103 tokens，超出本次授权的 800,000 上限 53,103，92 题全量轮因此未执行。诚实边界：agent 当前默认配置在该冻结集上未达验收线，服务承诺范围待失败模式分析后重定。失败模式分析已完成（[m6-level2-failure-analysis.md](benchmarks/m6-level2-failure-analysis.md)），修复后第一轮复测 DexAtlas 15/20（[m6-level2-retest.md](benchmarks/m6-level2-retest.md)）；五项根因修复后的第二轮复测（20 题完整分母，首轮 18 题 + 追加授权补跑 2 题，token 355,623）**DexAtlas 16/20 = 80.0%，达到验收线**（[m6-level2-retest2.md](benchmarks/m6-level2-retest2.md)，A 7/20、B 7/20；层级 1 复验确认修复未破坏 scripted 路径，见 [m6-level1-recheck-after-fixes.md](benchmarks/m6-level1-recheck-after-fixes.md)）；三轮完整复测（[m6-level2-retest3.md](benchmarks/m6-level2-retest3.md)，全部数字由 `scripts/m6_level2_retest3_report.py` 从 [m6-level2-retest3-traces-r1/r2/r3.json](benchmarks/m6-level2-retest3-traces-r1.json) 重算，token 1,080,116 在 1,200,000 授权内）：DexAtlas 逐轮 17/15/17（合计 49/60 = 81.7%）——**未达验收线（每轮 ≥80% 且三轮合计 ≥90%）：r2 75.0% 低于单轮线，三轮合计 81.7% 低于 90% 线，验收结论「未达标」**，按冻结纪律只能修正系统或缩小并重述服务承诺后重测，不得删题换通过率。；执行层修复成套落地（limitations 纳入判分、预算耗尽单列 outcome、端点故障重试启用、XML 泄漏容错、C2 并集放宽到单词查询）后先做 6 题 × 3 轮窄验证（[m6-level2-narrow-verify-incomplete.md](benchmarks/m6-level2-narrow-verify-incomplete.md)，由 `scripts/m6_level2_narrow_verify_audit.py` 从 53 条已捕获 trace 生成，**运行不完整**：原授权 400,000 tokens，追加至 406,000 后仍超支，实际 410,256 tokens，第 54 条 trace 未跑）：6 题中 4 题转化（每题 ≥2 轮正确），确定性修复子集 4/5。窄闸门在已捕获轮次上达标，但**这不是 54-trace 判定**；修复后的完整结论以三轮完整重测为准（[m6-level2-retest4.md](benchmarks/m6-level2-retest4.md)，全部数字由 `scripts/m6_level2_retest4_report.py` 从 [m6-level2-retest4-traces-r1/r2/r3.json](benchmarks/m6-level2-retest4-traces-r1.json) 重算生成）：DexAtlas 逐轮 15/20、16/20、18/20，三轮合计 49/60 = 81.7%，**仍未达 B1 验收线（每轮 ≥16/20 且三轮合计 ≥54/60）**——r1 低于单轮线，合计低于 90% 线；三轮 trace 合计 1,182,356 tokens，在 1,200,000 授权之内，无熔断中止、无 not-run。与修复前复测合计分相同（49/60），失败构成已从执行层故障转为判分不过与个别题预算耗尽/errored。B1 保持未关闭。针对首轮窄验证暴露失败面的四项修复（协议泄漏纠偏重试、partial 措辞对齐、api-key 常量池检索引导、descriptor 连写模板）之后的窄验证二轮（[m6-level2-narrow-verify2.md](benchmarks/m6-level2-narrow-verify2.md)，由 `scripts/m6_level2_narrow_verify2_report.py` 从 [m6-level2-narrow-verify2-traces.json](benchmarks/m6-level2-narrow-verify2-traces.json) 重算，6 题 × 3 轮 × 3 配置 = 54 条 trace 完整，代码 `9b25835`）：DexAtlas 转通过 2/6、确定性修复题 2/5，**未达窄验证判据（≥4/6 且 ≥3/5）**；实测 420,826 tokens 超授权上限 410,000 达 10,826，超出如实记录。按验收方案 §2.2 停止投入，**转方案 3（现状披露）**。预算效率四项修复（resources 收口、notice 折叠、string excerpt 截断、空转软提示）与行裁剪机制落地后的窄验证三轮（[m6-level2-narrow-verify3.md](benchmarks/m6-level2-narrow-verify3.md)，由 `scripts/m6_level2_narrow_verify3_report.py` 从 [m6-level2-narrow-verify3-traces.json](benchmarks/m6-level2-narrow-verify3-traces.json) 重算，54 条 trace 完整，代码 `9f0dae3`）：DexAtlas 转通过 3/6、确定性修复题 3/5，**仍未达窄验证判据**；实测 380,881 tokens，在 450,000 授权内，无熔断中止；按 [m6-verify3-plan.md](benchmarks/m6-verify3-plan.md) §7 停止，不再追加修复轮或模型调用，**方案 3 为最终定稿路径**。**2026-11-22 B1 达成并关闭**：预算放开（96k 任务预算 / 80 步 / 32 迭代）与三项产品修复（DEX 枚举证据、evidence_catalog、指令三轮强化）后，DeepSeek-V4.1-Flash 对同一冻结 20 题跑 3 轮 × 3 配置，DexAtlas 逐轮 18/20、20/20、18/20，三轮合计 **56/60 = 93.3%**——每轮 ≥80% 与三轮合计 ≥90% 两条验收线均达成（[m6-level2-deepseek.md](benchmarks/m6-level2-deepseek.md)，traces：[r1](benchmarks/m6-level2-deepseek-traces-r1.json)/[r2](benchmarks/m6-level2-deepseek-traces-r2.json)/[r3](benchmarks/m6-level2-deepseek-traces-r3.json)，由 `scripts/m6_level2_deepseek_report.py` 重算）。同口径对照：GLM-5.3-Flash 53/60 = 88.3%（[m6-level2-glm.md](benchmarks/m6-level2-glm.md)）、MiniMax 基线 49/60 = 81.7%——三模型成绩分开陈述不混排，修复在三个模型上全部有效。 |
| M7 客户交付包 | **交付项完成** | 三个案例按「问题/范围/操作/证据/结论/限制/下一步」重写（[case-studies/](case-studies/README.md)）；离线 HTML 与最小证据包（`analyze --html`、`export`）、迁移后引用校验与反向测试见[报告渲染说明](architecture/report-rendering.md)。逐例可下载报告/证据包附件已落盘（[attachments/](case-studies/attachments/)，2026-11-16 由文档内命令生成、`verify_package` 校验通过）；案例与代码逐项核对完成（2026-11-16）：三案例声称的命令、样例哈希、计数与证据记录均实跑核对一致，MCP 工具数等过期表述已纠正，API 报告丢失 APK 档案事实与重复分析 `created_at` 漂移两处真实缺陷已带红→绿回归修复 |
| M8 安装与契约 | **交付完成（macOS 未验证）** | 干净安装、Docker、故障恢复演练完成，macOS 未验证——已知限制，不属于已完成的验收项（[m8-install-rehearsal.md](reports/m8-install-rehearsal.md)）；公共契约表完成（[public-contracts.md](architecture/public-contracts.md)）；M8-2（查询命令缺 `--workspace`）与 M8-3（install.md 的 extras 组合不一致）**已修复并合入**（d90baff，全命令 `--workspace/-w`、install.md 修正）；M8-4（三后端全失败但 manifest 可解析仍退出 0）已按[提案](proposals/exit-code-partial-read.md)修复：新增退出码 6（EXIT_NO_INDEX），0–5 语义不变（1f6ef05） |
| M9 展示与素材 | **展示入口已完成；素材已移除** | 双语 README 首屏、文档地图、第三方归属表与路线图状态已合入；对外英文素材已随 2026-11-21 的去平台化清理移除 |
| M10 独立验收 | **已通过（2026-11-20）** | 外部独立验收人（未参与实现）在 `2edaed9`（当时的 `v1.0.0`）上从 clone 走完推荐安装路线 + 完整案例，40 项判定 **39 通过 / 0 不通过 / 0 未验证**，19 项阻断项全过，无需作者补步；客户视角三问（输入与结论、引用可核查、事实与线索区分）均成立，红旗十条全未命中；按原权重重评 **97.5% / 96.3%**，均 ≥90%。**tag 漂移已处置（2026-11-21）**：验收之后 tag 因测量记账门禁修复重打过三次（现指 `6e90317`）；作者决定**追认现有 tag**，验收结论覆盖到 `6e90317`，不重跑。验收材料与记录随项目去平台化清理移除（2026-11-21）。 |

4.1 起是此前记录、仍未关闭的缺口。

### 4.1 真实加固 APK

`obfuscated-app` 覆盖了短类名和短方法名，但它是**手写的**混淆，
不是有控制流混淆的真实加固产物。真实的加固 APK 需要外部样本。

### 4.2 布局里硬编码的文本（已覆盖）

资源表读了：`res/values*/` 里的文本声明（`<string>`、
`<string-array>` 的每一项、`<plurals>` 的每一项）进了索引，
`dexatlas search` 搜得到 `DexAtlas Demo`，每一条都指回声明它的那个文件。

布局 XML 里 `android:text="..."` 这种**硬编码**的文本现在也进了索引：
`res/layout*`、`res/menu`、`res/xml` 里 `android:text`、`android:hint`、
`android:contentDescription`、`android:title`、`android:summary`、
`android:label` 的字面量按 `layout_text` 入 `resources` 表和全文索引，
locator 指回布局文件与元素起始行
（详见[分析覆盖度与证据来源](analysis-provenance.md) §5.4）。

`@string/app_name` 这种**资源引用**也进了索引：解码树里全部
`res/**/*.xml` 的属性值与 `<item>` 文本凡形如 `@type/name`
（含 `@android:string/ok` 这样的平台前缀）都记成一条引用边，
进 `resource_references` 表——引用方（文件 + 元素 + 属性 + 行号）
指向被引资源（type + name）。`dexatlas resrefs <project> --type string --name app_name`
和 `GET /projects/{id}/resource-references` 都能反查「这个 string 被谁引用」，
每条边带 `apktool:<file>#line=N;<Tag>` 的 locator。
仍然不在索引里的是**资源 ID 的数值映射**（`R.string.app_name` 是哪个 int）——
那要读 `resources.arsc` 的 ID 表，是下一件事。

### 4.3 压测没有覆盖的部分

[大型 APK 基准](benchmarks/large-apk.md) 记了它测了什么，也记了**没测什么**：
真实的 APK（不是合成的）、JADX 与 Apktool 在规模下的表现、
native 库、内存。这些要等下一个手里有真实样本的人。

### 4.4 被截断的运行，退出码曾经是 0（已修复）

索引触到上限时，项目状态仍是 `completed`——部分成功不是失败——
错误记在 `project.errors` 里，报告有「Backend errors」段，CLI 也会把它
当警告打出来。

**CLI 现在返回退出码 5**（`EXIT_TRUNCATED`）：分析跑完了、报告照常写出，
但只要有一步被上限截短（`output_truncated`），退出码就是 5——只看退出码
的调用方能分出「被截断的运行」「完整的运行」「失败的运行」。
公共契约变更：0/1/2/3/4 的含义不变，5 是新增，无破坏。

### 4.5 阶段验收挖出来的、这一轮修掉的

评审（协议第 2 步，三份审核共 44 条发现）挖出来的产品缺陷，
按严重程度排：

| 缺陷 | 严重级 | 状态 |
|---|---|---|
| 上传的文件名由客户端决定 → 一个项目的符号表装上另一个 APK 的类 | **阻断** | 已修 |
| 默认配置下 JADX 的 Java 反编译完全失效，报告照旧写着 jadx 的版本 | **阻断** | 已修 |
| `PRAGMA journal_mode = WAL` 在每次事务里——一次纯读也在写库，并发分析直接 500 | 重要 | 已修 |
| `analyze()` 没有 try/except：异常穿出去，项目停在 `running`、`errors=[]`，再传同一个 APK 永不重跑 | 重要 | 已修 |
| `GET /health` 每个请求都开数据库写锁——探活的服务把自己搞挂 | 重要 | 已修 |
| 证据的每环都自洽却指向错的东西（上传覆盖那一类） | 重要 | 已修 |
| `cross_references_with_evidence` 数的是被调方法数，而 `cross_references` 数的是边数 | 重要 | 已修 |
| 超过 200 个类时，反编译覆盖率那条证据被挤出报告的证据表 | 重要 | 已修 |
| API 导出的报告写「Analysis time 0.0s」，与 CLI 导出的同一份不一致 | 中 | 已修 |
| `xrefs` 表没有主键，同一条调用边可以写进多行 | 重要 | 已修（P2-003，见 4.6） |
| workspace 并发不安全：同一个 APK 的两次分析共用一个目录 | 重要 | 已修（P2-002：每次分析写进自己的目录，发布前不可见） |
| `EvidenceKind.CODE_LOCATED` / `BEHAVIOUR`、`EvidenceLevel.LEAD` / `INSUFFICIENT` 没有任何生产者 | 中 | 已修（P2-004：`BEHAVIOUR` / `LEAD` / `INSUFFICIENT` 由 `add_claim` 产出；M2：agent 读到带出处的源码时产出 `CODE_LOCATED`） |

**「已修」的每一条都配一个在旧代码上会红的测试**——不是「测试通过」，
是「把修复撤掉，测试必须红」。这一轮共验证了 21 处破坏实验。

三条阻断级里最值得记的是第一条：项目声称的哈希、标识符、每条 provenance
**全都是它自己的**，而符号表里装的是**另一个 APK 的类**。
**证据链的每一环都自洽，指向的却是错的东西**——读者核对哈希会通过，
因为哈希确实是它的。

### 4.6 Phase 2 交付了什么（M0–M4，已验收）

Phase 2 已于 2026-11-14 通过 M4 源码评审与验收（[评审报告](reports/m4-review.md)）。
以下是交付内容与退出标准核对，作为 Phase 3 的输入保留。

M0 有五条，每条带验收标准，都在
[Phase 2 计划](roadmap/phase2-plan.md)里。

**P2-001：让方法解析对重载安全 —— 已交付。**

原来一个方法**只按名字**解析：两个重载 `sign(String)` 和 `sign(String, String)`，
请求 `sign` 拿到哪一个取决于源码里的顺序，**不是签名**。

**为什么它是第一件事**：MCP 工具会把这个结果直接返回给 agent，
而 agent 会把它当证据引用——**一个被引用错了的方法，比没有方法更糟**。
所以它排在 MCP 之前。

**索引里其实存着能区分重载的信息**（`methods.descriptor`），
只是查询时没用；而 JADX 适配器的正则**已经抓了参数类型**，
只是解析结果里把它丢掉了。

修法：按完整 DEX descriptor 解析；**歧义要明说，不能猜**——
名字对应多个重载而调用方没指明时，明确报告有哪些候选、需要什么才能确定地选一个。
命令行用**自己的退出码**（4），API 用 **409**，
「没有源码」「请求不对」「分析失败」这几个码仍然各说各的。

**M0 的五条全部落地**：P2-001 重载安全的方法解析、P2-002 `AnalysisRun` 与事务化结果、
P2-003 CallSite / CallEdge 语义、P2-004 已验证证据的不变量、P2-005 运行时隔离。
每一条都配了**在旧实现上会红**的回归测试。

P2-003 关掉了上表里 `xrefs` 那条缺陷：索引里现在存的是**调用点**
（带着它是从哪个 DEX 文件、哪条指令读出来的），**调用边**由调用点派生。
两个数在报告里分开写，并且各自说清是哪个。

**M1 也落地了**：只读的 MCP 服务器。十一个工具，读而不写、不跑 shell、
不需要模型 provider；每一份从 APK 里读出来的文字都带着「这是数据」的标记。
设计与边界在[架构文档](architecture/mcp-server.md)里。

**M2 也落地了**：单一的 evidence-first agent。一个循环、一份计划、一份预算、
一份状态、一份报告；结论走项目自己的 `EvidenceBuilder`，所以模型的说法写不成
`verified`；**APK 里的指令指挥不了 agent**（去掉这条性质，测试就红）。
设计在[架构文档](architecture/agent.md)里。

**M3 的任务集与对比机械都落地了**：92 个带独立可核对答案的任务
（[任务集说明](benchmarks/task-set.md)，含 11 个问「答案在哪里找到」的
where-source 任务），三配置 harness、八项指标和脚本生成的报告都在仓库里。
被测系统只看 `--emit-questions` 的四个字段，判分器独占 marking scheme；
每个报告数字都能用 `--input <traces.json> --metrics` 从落盘 trace 重算。

**真模型对照也跑过了**：用 MiniMax-M3.1-Flash（OpenAI 兼容端点）跑完 92 题
× 3 配置，结果在[真模型报告](benchmarks/comparison-real.md)，证据是
`comparison-real-traces.json`；scripted 的那组在
[对比报告](benchmarks/comparison.md)，两份**分开陈述、不并表**。
本次正确率 A 30.4% / B 22.8% / DexAtlas agent 19.6%，无支撑断言率
100% / 100% / 4.4%，工具调用成功率 100% / 100% / 98.9%。

**这些数字里有一半是模型行为，不是工具能力**：agent 正确率低的主因是模型
反复请求工具直到预算耗尽（15 题），以及回答写成散文而非 JSON
（`parse_answer` 已能提取内嵌文档，见下）。unanswerable 那一类反而是 agent
最好（11/13，A 10/13、B 8/13）。报告的「Why the failed tasks failed」表把这些
成因逐条列出——率不带成因就是没有解释。

**§5 退出标准逐条核对**（2026-11-14，逐条证据见
[Phase 2 计划 §5](roadmap/phase2-plan.md)原文）：

| 退出标准 | 结论 | 证据 |
|---|---|---|
| ≥30 道带可审计答案的任务 | **满足**——92 题（≥30 的三倍），答案取自样例自己的源码，可独立核对 | [任务集说明](benchmarks/task-set.md)、`benchmarks/tasks/` |
| 每个报告指标可由仓库脚本再生 | **满足**——`--input <traces> --metrics` 重算八项指标，与两份报告逐格一致；`--report` 逐字再生报告，CI 门禁兜底 | [对比报告](benchmarks/comparison.md)、[真模型报告](benchmarks/comparison-real.md) |
| 至少两种 model/provider 配置实测 | **满足**——scripted 与 MiniMax-M3.1-Flash（openai-compatible）各跑完 92 题 × 3 配置 = 276 条 trace，两份分开陈述 | `comparison-traces.json`、`comparison-real-traces.json` |
| 工具执行成功率达 95% 或披露缺口 | **满足**——scripted 100%/100%/100%，真模型 100%/100%/98.9%（≥95%）；缺口不在工具调用而在任务完成，报告如实披露 | 两份报告的 The eight metrics 与 Disclosures 段 |
| 对外代码结论可溯源或标未验证 | **部分满足**——DexAtlas 45 条非空断言中 43 条带 grounded + locator；A/B 的 86 条全部不溯源（0/86），由 `unsupported_assertion_rate` 100% 披露；agent 的 2 条不带 locator 的断言即 4.4% 的无支撑率 | 真模型 `comparison-real-traces.json` 的 assertions 字段 |
| 对比不声称测量不支持的改进 | **满足**——两份报告均明文「never claims an improvement the measurements do not support」；scripted 报告另声明「not a model baseline」 | 两份报告的 Disclosures 段 |

**「换更强模型」这一问也跑完了**（2026-11-15；修订 2026-11-15：该问的准确
说法是**同一模型的预算与执行条件变化**——模型没有换，不能把两轮差值归因为
模型变化）：仍是 MiniMax-M3.1-Flash、
同端点同题集，但把三处预算约束放开（agent 工具调用步数 12→40、循环轮数
8→24、每请求 token 4096→16384；A/B 每请求仍 4096），并修掉一处测量口径
问题——敏感工具第二次调用会暂停等人工批准，而基准跑批无人可问，69 题
因此空答；现在计划内的敏感读数由批准门放行（上限 8 次，见
[架构文档](architecture/agent.md)与 `benchmarks/comparison/systems.py`）。
结果在[强预算报告](benchmarks/comparison-stronger.md)，证据是
`comparison-stronger-traces.json`，与上一轮**分开陈述、不并表**。
agent 正确率 19.6% → 22.8%（+3.3 个百分点，21/92），A 30.4% → 28.3%，
B 22.8% → 16.3%；agent 无支撑断言率 4.4% → 9.2%。结论：**agent 与 A 的
差距主要是任务的步数预算与回答格式咬合的问题，不是换模型能消的**
——同一模型下，光把预算放开、把敏感门拿掉，agent 也只追回 3.3 个百分点，
且 61 题仍撞在 24 轮的循环上限上（模型一轮只请求一个工具、又倾向反复取证）。
A/B 在长上下文下反而更不稳定（B 退步 6.5 个百分点）。两轮的差值表在报告的
「Comparison with the previous run」段；报告不把任何差值说成改进。

**M4 的 workbench 已建六屏**（随 v0.2.0 发布）：项目面板、APK 上传与分析进度（上传策略与
REST API 共用同一份代码，后台分析，前端轮询项目状态）、检索与证据追溯（符号 →
类/方法源码 → 证据记录 → locator 解析）、单个方法的调用关系视图（谁调用它、它调用
谁，按调用点画出，点了节点就能跳到下一个方法）、Agent 工作区（问题由生产
Orchestrator 在后台任务里回答，屏上轮询计划、工具时间线与三段式报告）、报告导出
（CLI 与 REST API 同一份渲染器，无第二种格式）。六屏都坐在同一套只读 MCP
工具上，浏览器拿到的 JSON 就是工具自己的形状，测试逐个端点比对
`model_dump()`；没有调用者的方法答 0 而不是 404——把「分析没读到调用」
说成「这个方法不存在」，正是这个项目要避免的混淆。
**未建成**：基准视图（其导出一半已建成）与既有屏幕的细化仍在进行；调用关系屏
一次只答一个方法，不是全工作区调用图。
设计与取舍在[workbench 架构文档](architecture/workbench.md)里。

**Benchmark 视图也已落地**（屏 8 的另一半，随 v0.2.0 发布）：`#/benchmarks` 呈现 M3
对比的两份测量——scripted 与 MiniMax-M3.1-Flash——各自的八项指标、失败成因表，
以及「scripted 不是模型基线」「真模型运行不可复现」「不声称哪个配置更优」三条
披露。`GET /api/benchmarks/m3` 用对比 harness 自己的 `_run_from_document` +
`compare` 从仓库内 `docs/benchmarks/` 的 trace 实时重算、用 `format_value` 出
报告同款文本——屏幕不加一个数字、不落盘、不缓存；trace 文件缺失时答空列表加
披露，不报错。浏览器上的每格数字与两份报告逐字一致。

**M4 端到端链路已实测**（2026-11-14，逐屏证据见
[端到端实测报告](reports/m4-e2e-run.md)）：上传 `demo.apk` → 后台分析 →
检索 `Crypto` → 打开源码与证据 E-0004 → 解析 locator → 调用关系一跳跳转 →
报告导出，全程浏览器操作走通，导出文件与 `render_markdown` /
`build_json_report` 的输出逐字节一致。Agent 环节接了真实模型
（MiniMax-M3.1-Flash，key 只进环境变量）：屏、任务轮询与预算披露按设计工作，
但当前模型习惯每轮并行请求多个工具，默认预算（12 步 / 20000 tokens）内
5 个问题全部 `budget_exhausted`，没走到「写出带引用的结论」那一步——报告如实
标注 did not finish。缺口、复现与候选修法记录在实测报告 §3；该缺口随后已按
候选修法收敛（见下一条复验记录），不再遗留。

**M4 源码评审与验收已完成，判定升级为「通过」**（评审 2026-11-14，基准
`71c8d8c`，见[评审报告](reports/m4-review.md)；核验同日）：六屏源码全覆盖，
只读边界、上传策略共用、密钥处理与响应契约逐项核实无违例；六条退出标准
5 条满足、1 条（端到端）满足。评审当时判定「有条件通过」，附两个关闭条件；
两个条件均已核验满足（见下两条记录与[评审报告 §5.2](reports/m4-review.md)），
M4 验收正式升级为**已通过**。

**修复后真模型复验已完成**（2026-11-14，基准 `817ad1f`，见
[端到端实测报告 §5](reports/m4-e2e-run.md)）：在 `DEXATLAS_AGENT_MAX_STEPS=40`
与 120k tokens 预算下，「权限清单」「谁调用 Crypto.sign」两个问题以真实模型
（MiniMax-M3.1-Flash）稳定 `completed`，报告三段式完整、引用在证据表内可解析
（manifest 与调用边 locator 均 `resolved: true`）——「有条件通过」的两个关闭
条件之一（agent 提问在某明确配置下可复现）**已满足**；另一个（双语 README 的
agent 展示）由提交 `6eee294` 满足。串行单工具与步数放大两项修复均按设计工作；
默认预算（20000 tokens / 8 迭代）下提问仍会 `budget_exhausted`，枚举型问题在放宽
预算后也可能不收敛（模型先读后答的行为未变），预算默认值的调整留待后续。

**「模型能力可禁用」退出标准已系统验证**（2026-11-14，基准 `1f1d883`，见
[模型能力可禁用性验证报告](reports/model-disable-verification.md)）：不配置任何
`DEXATLAS_AGENT_*` 环境变量时，CLI 12 项、REST API 4 项、workbench 16 项、
MCP 11 项全部正常，agent 提问端点按设计返回 503 + `agent_not_configured`——
该条退出标准判定满足。

**M4 的 Public assets 六项已全部落地**（2026-11-14，对照
[Phase 2 计划 §6](roadmap/phase2-plan.md)的 Public assets 清单）：

| Public asset | 状态 | 位置 |
|---|---|---|
| 60–90 秒端到端 demo | **完成（2026-11-14 重录）**——`ffprobe` 实测 demo.mp4 与 demo.gif 均 **84.8 秒**，覆盖空工作区 → 上传 demo.apk → 后台分析 → 符号检索 → 方法源码 → 证据 locator → 调用图一跳导航 → Agent 提问（planning→completed，三段式报告 + limitations）→ Markdown 报告导出（下载文件名带项目 id）的完整端到端链路；真实浏览器操作录屏（Edge app 窗口 + CDP 输入 + gdigrab 逐帧抓屏，无剪辑无合成帧），Agent 屏由项目自带的 scripted 演示 provider 驱动（无任何密钥、无真实模型调用），其余全部是真实分析产物 | `docs/assets/demo.mp4` / `demo.gif` |
| 技术架构图 | **完成**——ASCII 图覆盖 CLI / REST API / MCP server / agent / workbench 五入口与 core / tools / reports 的关系，只画已存在的组件 | [architecture/diagram.md](architecture/diagram.md) |
| ≥2 个完整案例研究 | **完成**——demo-app 从分析到证据链的完整走查；混淆样本走查（含 multi-DEX 附录），全部引用当次真实运行输出与证据 id（M7 之后已扩为 3 篇，含 API 集成走查） | [case-studies/](case-studies/README.md) |
| 公开 benchmark 摘要 | 已有（v0.2.0 前完成） | [benchmarks/comparison.md](benchmarks/comparison.md) · [comparison-real.md](benchmarks/comparison-real.md) |
| 可下载示例分析报告 | 已有（屏 8 导出，实测与渲染器逐字节一致） | workbench 报告导出 · `dexatlas analyze -o` |
| 面向客户的 portfolio 描述 | **完成**——能做什么、技术亮点、适用场景、快速试用，全英文 | [portfolio.md](portfolio.md) |

demo 时长的结论（2026-11-14 更新）：60–90 秒端到端版已重录完成（84.8 秒，见上表），
替代早先 8.8 秒的短素材；Agent 屏使用项目自带的 scripted 演示 provider（无密钥），
上传、分析、检索、调用图与报告导出均为真实操作。

### 4.7 这一轮关掉的

| 原来开着 | 现在 |
|---|---|
| 文档与 issue 的发布状态 | 23 处过期陈述改完；issue #1 留了评论（正文没动）；`scripts/check-version-claims.py` 现在自动查这一类 |
| 「这个方法调用了谁」被答成「谁调用了它」 | `find_callees` 与 `find_callers` 跑的是同一条查询；方向从来没被断言过，所以测试是绿的 |
| 交叉引用的两个数在五处对不上 | 摘要与自己的 detail 打架；agent 用了报告不读的键；迁移重建表时把索引一起删了；JSON 报告的 project 块只有一个数；`schema_version` 没升 |
| 资源完全没有覆盖 | 资源表进索引，`dexatlas resources` 和 `GET /projects/{id}/resources` 都能查；布局硬编码文本按 `layout_text` 入索引；`@string/...` 资源引用入 `resource_references` 边表，`dexatlas resrefs` 和 `GET /projects/{id}/resource-references` 能反查「谁引用了这个资源」 |
| Smali 回退不附带 provenance | `class_source_document` / `method_source_document` 返回带出处的文档，CLI 与 API 都说得出是 Java 还是 Smali |
| 大型 APK 的性能压测 | 基准跑完了；**顺带找出三个真缺陷并修掉** |
| 文档里的引用会漂移没人管 | `scripts/check-doc-citations.py` 现在真的校验 94 处引用里的 93 处（原来只查 18 处） |
| 版本声明检查器在自己的目标场景下失效 | base 提交用它自己的事实重算，判据从「数量」改成「身份」 |
| 报告里的数字从不重新测量 | 数字改成真测：新增收集的测试数 + coverage 自己解析出的语句数；指纹覆盖 `tests/` 和工具配置 |
| 重载同名时解析靠猜 | 按完整 DEX descriptor 解析；名字对上多个重载时**明说歧义**并列出候选，CLI 退出码 4、API 409 |
| 重分析就地覆盖，两个运行的符号和证据混在一起 | 每次分析有**自己的运行身份**，结果先暂存、再一次事务发布；没发布的那次不碰上一个已发布的快照 |
| 证据的等级是约定，不是机制 | `verified` 的代码结论必须带着**能在分析里解析的引用**；模型的说法走另一条路（`add_claim`），写不成 `verified` |
| 后端把宿主的日志整个删掉；不受信的 DEX 在服务进程里解析 | 压制改成**按名字**（不动宿主的 handler）；DEX 解析搬进**单独的 worker 进程**，解析失败被记下来而不是服务崩掉 |

那一轮找出三个真缺陷值得单独记一句，因为它们是**产品**的缺陷，不是文档的：

1. **版本号每个符号查一次。** 每个类、方法、字段、交叉引用都带一条 provenance，
   每条都要问一次后端版本号，而那次查询要扫一遍已安装的发行版。
   实测：12,000 个方法的一次运行里 82 秒有 80 秒花在这上面。
2. **触到上限就静默截断，项目照样报「完成」。** 索引少了几千个方法，
   `project.errors` 是空的，报告里的数字和数据库的行数**完全一致**——
   因为它们忠实地记录了一个被砍短的索引。现在触顶会记 `output_truncated`。
3. **三个上限里有两个是按 DEX 文件算的。** 四个 DEX 的 APK 拿到四倍额度——
   恰好是最需要封顶的那种 APK 反而拿到最多。现在一份预算一个 APK。

三个都不是「测试变红」能发现的：它们都要**真的走到那个边界**才会露出来。

---

## 5. 动手之前要知道的几件事

### 报告里的数字是自动生成的

文档里的测试数、覆盖率、快慢分层数都带 `<!--fig:...-->` 标记，
由 `scripts/refresh-report-figures.py` 测量并写回。

**不要手改那些数字。** 改完代码跑一次脚本即可：

```bash
uv sync --extra demo          # 完整测量需要 Pillow
uv run python scripts/refresh-report-figures.py
uv run python scripts/refresh-report-figures.py --check   # 只比对不写入
```

脚本在一次运行内收敛，并且**能区分「报告过期」和「代码坏了」**——
前者会刷新，后者会点名失败的测试并拒绝写回。

### 文档的行号引用会漂

`scripts/check-doc-citations.py` 校验文档里每一处 `文件:行号` 引用
是否仍指向它说的东西。它会打印校验了多少处、漂移了几处——**那个数不要手抄到这里**，
抄的数会漂（这份文档上一版写着 82，下一版就是别的数了）。改了 `src/` 之后跑一次：

```bash
uv run python scripts/check-doc-citations.py
```

### 安全边界

仓库里**不含**任何第三方分析产物——APK、DEX、so、jar、zip、obb、vdex 这些后缀
一个都没有。分析样本只有两个来源：

- **自建** —— `examples/` 下的 5 个，每个的 smali 源码就在旁边，
  `scripts/build-test-apks.sh` 能重建
- **拉取** —— `scripts/fetch-fixtures.sh` 取 androguard 的 Apache-2.0 测试数据

这个边界由 `tests/test_docs.py` 里的测试守着：仓库里每个 APK 都必须有源码在旁边。

### 后端在 CI 上的三种配置

CI 里跑的是三种**不同**的组合——JADX 和 Apktool 是外部程序，Androguard 是
Python 包，所以「装没装后端」要分开说：

| 配置 | JADX | Apktool | Androguard | 对应 job |
|---|---|---|---|---|
| 全装 | 有 | 有 | 有 | Tests (Python 3.12) |
| **两个外部后端都不在** | 无（没 Java） | 无（没 Java） | **有** | Tests (Python 3.13) |
| 只装 Apktool | 无 | 有 | 有 | Tests (Apktool only, no JADX) |

**注意第二行**：3.13 那个 job 装的是 `--extra analysis`，而 `analysis` extra
装的就是 Androguard——它是 Python 包，不需要 Java。所以那个 job 不是
「一个后端都不装」，而是「两个外部后端都装不了」。三种配置都要跑。

本地复现：

```bash
# 全装（默认）
uv run pytest

# 两个外部后端都不在
DEXATLAS_JADX_PATH="" DEXATLAS_APKTOOL_JAR="" uv run pytest

# 只装 Apktool
DEXATLAS_JADX_PATH="" uv run pytest
```

**注意是空值，不是 `env -u`。** 后端路径的配置是三态的：
`None`（没设）表示**去 PATH 上找**，空字符串表示**显式禁用**，
一个存在的路径表示**用它**。`env -u DEXATLAS_JADX_PATH` 只是「没设」，
于是它回退到 PATH 查找——而 jadx 的 `bin` 通常就在 PATH 上，
**后端并没有被禁用**。要禁用，得给它空值：

```console
$ DEXATLAS_JADX_PATH="" uv run dexatlas backends
│ jadx       │ not installed │ —       │
│ apktool    │     available │ 2.11.1  │
│ androguard │     available │ 4.1.4   │
```

**这三个配置都要跑。** 只跑默认那一种，正是两个假定 JADX 已安装的测试
长期未被发现的原因。

### 本机环境

```bash
export DEXATLAS_APKTOOL_JAR="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/apktool.jar"
export DEXATLAS_JADX_PATH="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin/jadx.bat"
export PATH="/c/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin:$PATH"
```

GitHub 网络需要代理 `http://127.0.0.1:7897`。

---

## 6. 这个项目反复出现的缺陷类型

写在这里，是因为**它比任何一条具体清单都更有用**。

DexAtlas 出现过二十一类「宣称完成了、实际没有完成」：

| 缺陷 | 它怎么藏起来的 |
|---|---|
| 交叉引用的 id 带空格，查询永远返回空 | 报告显示 6033 条交叉引用，一切健康 |
| 方法表和交叉引用表的 id 拼写不同 | 从 `dexatlas methods` 复制 id 去查 `xrefs` 查不到 |
| Smali 回退从未生效 | 报告「No source」，看起来像 APK 没代码 |
| 集成测试的 fixture 从未被拉取 | 本机全过、CI 全跳过，**两边都绿** |
| 退出清单被改写成更容易打勾的措辞 | 「5 个自建 APK」写成「verified against test APKs」 |
| 报告里的方法数和实际行数不一致 | 报告说 14 个方法，查询只列得出 11 个 |
| 空路径不能禁用后端 | 旧测试**因为错误的原因**而通过 |
| 文档说 A、代码是 B（9 处） | 没有人核对过 |
| workflow 用了 GitHub 不接受的写法 | run 被创建后失败，**0 个 job 被调度** |
| 手写的数字和自动生成的数字对不上（4 处） | 报告的数字是脚本量的，发布说明和徽章的数字是人抄的——两边从没被放在一起看过 |
| 触到上限就静默截断，项目照样报「完成」 | 样本最大不到 3 KB，从没触到过 5,000,000 指令的上限；截断只打了一条 warning |
| 同一个相对路径被解释成两个位置 | 默认工作区是相对的，JADX 的 `--output-dir` 和 `cwd` 都拿到它——源码写进了双重嵌套目录，索引找不到，**报告照旧写着 jadx 的版本** |
| 默认配置从来没被测过 | `tests/conftest.py` 的工作区永远是绝对路径，所以上面那条躲过了整套测试 |
| 上传的文件名由客户端决定 | 两个 APK 用同一个文件名上传，第二个覆盖第一个，而分析在后台读的是那个路径——**一个项目的符号表装上了另一个 APK 的类** |
| 一次纯读也在写数据库 | `PRAGMA journal_mode = WAL` 在每次事务里，SQLite 只允许一个写者——一次 `GET` 就能把并发的分析锁在门外 |
| 异常穿出去，项目停在 `running` | `analyze()` 没有 try/except，数据库里的项目行是 `status='running'`、`errors=[]`——**没有任何地方说这次分析失败过**，再传同一个 APK 命中已有哈希，永远不重跑 |
| 证据的每一环都自洽，却指向错的东西 | 上面那条上传覆盖：哈希对、项目 id 对、provenance 对——**只有类不属于这个 APK**，核对哈希的人看不出来 |
| 从数据库重建结果时丢了字段 | API 导出的报告写「Analysis time 0.0s」，CLI 导出的同一份是真实耗时——`_rebuild_result` 没有重建它 |
| 「机制」其实只是约定 | 证据等级在 docstring 里被写成机制，实际没有 validator——`BEHAVIOUR` 记成 `VERIFIED`，报告就渲染成「由分析工具确定性确立」 |
| 数字只跟旁边的记录自比 | 把记录里的 `passed` 和图里的数字一起改成 999，没有任何新失败——指纹只哈希 `src/`，加测试都不算过期 |
| 同样的数字，不同的集合 | 「跳过 12 个」和「跳过的是这 12 个」不是一回事——一次不完整的测量可以被当成完整的写进报告 |

共同点有三个：

1. **它们都不让测试变红。** 绿色的测试套件证明不了「这个功能能用」，
   只证明「被断言的那些行为成立」。
2. **它们都藏在真实流程之外。** 手写的理想输入、被跳过的 fixture、
   没被拉取的样本、改写过的清单、**没人用过的默认配置**——只要不去跑一遍真实的东西，就看不见。
3. **它们都在「自洽」里藏身。** 最难查的那几条，单独看每一环都对：
   哈希对、id 对、provenance 对、数字对得上记录。**只有把它们放回真实的流程里，
   对照另一个东西看，才会看出它们指错了。**

最后十类是 v0.1.3 之后新出现的，而且都指向同一件事：**边界没被走到过**。
上限没被触到，所以「触顶之后会怎样」只能是推测；一个从没被量过的数字只能靠抄，
而抄来的数字迟早和量出来的不一样；一个从没被用过的默认配置，只能靠猜。

所以这个项目对自己的要求是：**不是「测试通过」，是「跑过一遍并且对得上」**。
新加一条测试时值得问两句——它用的是**真实流程里的输入**，还是我手写的那个？
它有没有真的走到那个边界？
