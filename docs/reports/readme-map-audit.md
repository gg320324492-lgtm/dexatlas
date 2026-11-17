# README 文档地图完整性复核

日期：2026-11-17。基线：`claude/readme-map-audit-b68ec2` @ `062c4b5`（工作树
`E:\Dexatlas\.claude\worktrees\readme-map-audit-b68ec2`）。**只读复核**：除本页外未改动任何文件。

复核对象：英文 `README.md` 的 `## Documentation` 段（`README.md:375`–`README.md:504`）与中文
`README.zh-CN.md` 的 `## 文档` 段（`README.zh-CN.md:317`–`README.zh-CN.md:385`）——这两段就是本项目
对外的「文档地图」。README 其余部分（顶部状态段、Roadmap status 表、Quick start）里指向
`docs/` 的链接一并核了，但不算地图条目。

对照基准：工作树里实际存在的 `docs/**/*.md` 共 104 份（本页落地后 105 份），加 6 份根级文档。

---

## 0. 结论摘要

| 类别 | 条数 | 说明 |
|---|---|---|
| 缺失（仓库里有、地图里没有） | 15 | 其中 12 条是面向访客的入口类文档，3 条是分组计数（见 §3） |
| 描述已过期 | 2 | 数字/摘要与文件现在的内容不符 |
| 中英不对称（英文有、中文没有） | 4 | 全部集中在「怎么自己复核」和「两份窄验证记录」上 |
| **合计** | **21** | |

所有地图里已存在的条目，路径**全部存在**（66 条链接 0 条失效），描述与文件现在的内容
**逐条核对后基本相符**（唯一例外见 §4）。问题不在「写错了」，在「没写」和「没同步」。

**三步结论：访客从 README 出发能走完「了解」，走不完「复核」（中文 README 卡住），
走不完「找报告」（两份 README 都没有报告目录索引）。**

---

## 1. 英文 `README.md` 文档地图逐行核对

段落范围：`README.md:375`–`README.md:504`。

| README（英）:行 | 地图里写的 | 实际状态 | 建议改法 |
|---|---|---|---|
| `README.md:379` | `docs/case-studies/demo-app-walkthrough.md` — 全流程走查 | 存在，描述相符 | — |
| `README.md:382` | `docs/case-studies/obfuscated-app.md` — 混淆应用还剩什么 | 存在，描述相符 | — |
| `README.md:385` | `docs/case-studies/api-integration.md` — REST/MCP 线缆契约 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/case-studies/README.md` 案例索引页 | 在 `README.md:377` 段首加一条，指案例索引 |
| `README.md:390` | `docs/architecture/README.md` — 流水线/存储/设计取舍 + glossary | 存在，描述相符（glossary 四项术语都在） | — |
| `README.md:394` | `docs/architecture/workbench.md` — 只读浏览器界面 | 存在，描述相符 | — |
| `README.md:396` | `docs/architecture/mcp-server.md` — 只读工具 | 存在，描述相符 | — |
| `README.md:398` | `docs/architecture/agent.md` — 证据优先的 agent | 存在，描述相符 | — |
| `README.md:400` | `docs/architecture/report-rendering.md` — 三种渲染 | 存在，描述相符 | — |
| `README.md:402` | `docs/architecture/public-contracts.md` — 公共契约表 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/architecture/{analysis-runs,call-sites-and-edges,evidence-invariants,runtime-isolation}.md` 四份 | 在 `README.md:388` 段补或收进一条「架构其余各页」 |
| （地图无对应行） | — | **缺失**：`docs/architecture/diagram.md`（连 `docs/architecture/README.md` 都没链它，全树只有 `docs/portfolio.md` 与 `docs/status.md` 链到） | 同上 |
| `README.md:407` | `docs/benchmarks/comparison.md` — 92 题验证对比机制 | 存在，描述相符 | — |
| `README.md:409` | `docs/benchmarks/comparison-real.md` — 具名模型、完整披露 | 存在，描述相符 | — |
| `README.md:411` | `docs/benchmarks/comparison-stronger.md` — 预算/执行条件变化 | 存在，描述相符 | — |
| `README.md:413` | `docs/benchmarks/large-apk.md` — 20 万方法 APK | 存在，描述相符 | — |
| `README.md:415` | `docs/benchmarks/service-regression-set.md` — 20 道冻结题 + 判定规则 | 存在，描述相符；本行已链 glossary（`README.md:416`） | — |
| `README.md:418` | `docs/benchmarks/m6-level1-scripted.md` — scripted 替身 provider | 存在，描述相符 | — |
| `README.md:421` | `docs/benchmarks/m6-level2-real.md` — 层级 2 真实模型批次 | 存在，描述与文件一致（24/60、853,103 tokens、超授权） | — |
| `README.md:431` | `docs/benchmarks/m6-level2-retest2.md` — 根因修复后复测 | 存在，描述相符 | — |
| `README.md:437` | `docs/benchmarks/m6-level2-retest4.md` — 三轮完整复测 49/60 | 存在，描述相符 | — |
| `README.md:443` | `docs/benchmarks/m6-level2-narrow-verify2.md` — 窄验证二轮 2/6 | 存在，描述相符 | **中文地图缺这条**（见 §5） |
| `README.md:454` | `docs/benchmarks/m6-level2-narrow-verify3.md` — 窄验证三轮 3/6 | 存在，描述相符 | **中文地图缺这条**（见 §5） |
| `README.md:469` | `docs/HANDOVER.md` — 现状/怎么跑/下一步 | 存在，描述逐字相符 | — |
| `README.md:471` | `docs/install.md` — 每条命令都在全新克隆上验证过 | 存在，描述逐字相符 | — |
| `README.md:472` | `docs/status.md` — 项目状态页；§4.0 带 M6 层级 2 判定 | 存在，描述相符（`docs/status.md:125` 确为 §4.0，且写明里程碑未收口） | — |
| `README.md:475` | `docs/service-commitments.md` — 服务承诺范围 | 存在，描述相符（中文文档） | **中文地图缺这条**（见 §5） |
| `README.md:477` | `docs/how-to-verify.md` — 怎么自己复核每句话 | 存在，描述相符（该页 §3 正是「哪些说法未达成」） | **中文地图缺这条**（见 §5，最要紧） |
| `README.md:480` | `docs/analysis-provenance.md` — 哪条结论由哪个后端支撑 | 存在，描述相符（中文文档） | — |
| `README.md:483` | `docs/roadmap/ROADMAP.md` — 三个阶段与当前位置 | 存在，描述相符 | — |
| `README.md:484` | `docs/roadmap/phase2-plan.md` — Phase 2 计划 | 存在，描述相符 | — |
| `README.md:486` | `docs/roadmap/phase3-plan.md` — 作品集计划 | 存在，描述相符 | — |
| `README.md:488` | `docs/reports/phase3-baseline.md` — 声明清单/重算数字/未决问题 | 存在，描述相符 | — |
| `README.md:490` | `docs/assets/demo.mp4` — 85 秒完整会话 | 存在，描述相符 | — |
| `README.md:496` | `docs/releases/phase1-acceptance-2026-10-21.md` — 验收了什么 | 存在，描述相符 | — |
| `README.md:498` | `docs/reports/phase1-review-report.md` — Phase 1 源码评审 | 存在，描述相符 | — |
| `README.md:500` | `docs/reports/phase1-maturity-assessment.md` — 六个加权维度 | 存在，描述相符（含「分数是修复前基线」的免责） | — |
| `README.md:503` | `docs/reports/phase2-issue-list.md` — 推迟的发现 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/reports/README.md` 报告目录索引 | 在 `README.md:467` 段加一条（最要紧，见 §7） |
| （地图无对应行） | — | **缺失**：`docs/releases/v1.0.0.md` v1.0.0 发版说明 | 在 `README.md:467` 段加一条 |
| （地图无对应行） | — | **缺失**：`docs/portfolio.md` | 低优先，可并入「项目记录」 |
| （地图无对应行） | — | **缺失**：`docs/proposals/exit-code-partial-read.md` | 低优先 |
| （地图无对应行） | — | **缺失**：`docs/outreach/{publish-review,cover-letter-templates,scope-ai-mcp,scope-backend-automation}.md` | 低优先；`docs/outreach/project-brief.md` 已在 `README.md:567` 出现，可作同组入口 |
| （地图无对应行） | — | **缺失**：`docs/releases/v0.1.0.md`–`v0.2.0.md` 六份旧发版说明 | 低优先，可收进 `docs/releases/` 一条 |
| （地图无对应行） | — | **缺失**：`docs/benchmarks/task-set.md` | 低优先 |
| （地图无对应行） | — | **缺失**：`docs/case-studies/attachments/{demo-report,obfuscated-report}.md` | 低优先；`docs/case-studies/README.md` 已提及 attachments 目录 |

---

## 2. 中文 `README.zh-CN.md` 文档地图逐行核对

段落范围：`README.zh-CN.md:317`–`README.zh-CN.md:385`。

| README（中）:行 | 地图里写的 | 实际状态 | 建议改法 |
|---|---|---|---|
| `README.zh-CN.md:321` | `docs/case-studies/demo-app-walkthrough.md` — 全流程走查 | 存在，描述相符 | — |
| `README.zh-CN.md:323` | `docs/case-studies/obfuscated-app.md` — 混淆应用还剩什么 | 存在，描述相符 | — |
| `README.zh-CN.md:325` | `docs/case-studies/api-integration.md` — REST/MCP 线缆契约 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/case-studies/README.md` 案例索引页 | 在 `README.zh-CN.md:319` 段首加一条 |
| `README.zh-CN.md:330` | `docs/architecture/README.md` — 流水线/存储模型/设计取舍 | 存在，但**描述比英文少**：英文 `:390` 那行还点了 glossary（agent service promise、frozen discipline、B1、七条评分规则），中文没有 | 补一句 glossary 指引（见 §5 第 4 条） |
| `README.zh-CN.md:331` | `docs/architecture/workbench.md` — 只读浏览器界面 | 存在，描述相符 | — |
| `README.zh-CN.md:332` | `docs/architecture/mcp-server.md` — 只读工具 | 存在，描述相符 | — |
| `README.zh-CN.md:333` | `docs/architecture/agent.md` — 证据优先的 agent | 存在，描述相符 | — |
| `README.zh-CN.md:334` | `docs/architecture/report-rendering.md` — 三种渲染 | 存在，描述相符 | — |
| `README.zh-CN.md:335` | `docs/architecture/public-contracts.md` — 公共契约表 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/architecture/{analysis-runs,call-sites-and-edges,evidence-invariants,runtime-isolation,diagram}.md` 五份 | 在 `README.zh-CN.md:328` 段补或收进一条 |
| `README.zh-CN.md:340` | `docs/benchmarks/comparison.md` — 92 题验证对比机制 | 存在，描述相符 | — |
| `README.zh-CN.md:341` | `docs/benchmarks/comparison-real.md` — 具名模型、完整披露 | 存在，描述相符 | — |
| `README.zh-CN.md:342` | `docs/benchmarks/comparison-stronger.md` — 预算/执行条件变化 | 存在，描述相符 | — |
| `README.zh-CN.md:344` | `docs/benchmarks/large-apk.md` — 20 万方法 APK | 存在，描述相符 | — |
| `README.zh-CN.md:346` | `docs/benchmarks/service-regression-set.md` — 20 道冻结题 + 判定规则 | 存在，描述相符，但**本行没有链 glossary**（英文 `:415` 有） | 补 glossary 链接（见 §5 第 4 条） |
| `README.zh-CN.md:348` | `docs/benchmarks/m6-level1-scripted.md` — scripted 替身 provider | 存在，描述相符 | — |
| `README.zh-CN.md:350` | `docs/benchmarks/m6-level2-real.md` — 层级 2 真实模型批次 | 存在，描述相符（24/60、853,103 tokens） | — |
| `README.zh-CN.md:356` | `docs/benchmarks/m6-level2-retest2.md` — 根因修复后复测 | 存在，描述相符 | — |
| `README.zh-CN.md:360` | `docs/benchmarks/m6-level2-retest4.md` — 三轮完整复测 49/60 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/benchmarks/m6-level2-narrow-verify2.md` | 在 `README.zh-CN.md:360` 之后补一条 |
| （地图无对应行） | — | **缺失**：`docs/benchmarks/m6-level2-narrow-verify3.md` | 在 `README.zh-CN.md:360` 之后补一条 |
| `README.zh-CN.md:367` | `docs/HANDOVER.md` — 现状/怎么跑/下一步 | 存在，描述相符 | — |
| `README.zh-CN.md:368` | `docs/install.md` — 每条命令都在全新克隆上验证过 | 存在，描述相符 | — |
| `README.zh-CN.md:369` | `docs/status.md` — 项目现在在哪，还剩什么 | 存在，描述相符（比英文 `:472` 少一句「§4.0 带 M6 判定」，不算错） | 可选：补 §4.0 |
| （地图无对应行） | — | **缺失**：`docs/service-commitments.md` | 在 `README.zh-CN.md:369` 之后补一条 |
| （地图无对应行） | — | **缺失**：`docs/how-to-verify.md` | 在 `README.zh-CN.md:369` 之后补一条（最要紧，见 §7） |
| `README.zh-CN.md:370` | `docs/analysis-provenance.md` — 哪条结论由哪个后端支撑 | 存在，描述相符 | — |
| `README.zh-CN.md:371` | `docs/roadmap/ROADMAP.md` — 三个阶段与当前位置 | 存在，描述相符 | — |
| `README.zh-CN.md:372` | `docs/roadmap/phase2-plan.md` — Phase 2 计划 | 存在，描述相符 | — |
| `README.zh-CN.md:373` | `docs/roadmap/phase3-plan.md` — 作品集计划 | 存在，描述相符 | — |
| `README.zh-CN.md:375` | `docs/reports/phase3-baseline.md` — 声明清单/重算数字/未决问题 | 存在，描述相符 | — |
| `README.zh-CN.md:377` | `docs/assets/demo.mp4` — 85 秒完整会话 | 存在，描述相符 | — |
| `README.zh-CN.md:381` | `docs/releases/phase1-acceptance-2026-10-21.md` — 验收了什么 | 存在，描述相符 | — |
| `README.zh-CN.md:383` | `docs/reports/phase1-review-report.md` — Phase 1 源码评审 | 存在，描述相符 | — |
| `README.zh-CN.md:384` | `docs/reports/phase1-maturity-assessment.md` — 六个加权维度 | 存在，描述相符（比英文 `:500` 少「修复前基线」免责） | 可选：补「修复前基线」免责 |
| `README.zh-CN.md:385` | `docs/reports/phase2-issue-list.md` — 推迟的发现 | 存在，描述相符 | — |
| （地图无对应行） | — | **缺失**：`docs/reports/README.md` 报告目录索引 | 在 `README.zh-CN.md:365` 段加一条（最要紧，见 §7） |
| （地图无对应行） | — | **缺失**：`docs/releases/v1.0.0.md` v1.0.0 发版说明 | 在 `README.zh-CN.md:365` 段加一条 |
| （地图无对应行） | — | **缺失**：`docs/portfolio.md`、`docs/proposals/exit-code-partial-read.md`、`docs/outreach/` 四份、`docs/releases/v0.1.0`–`v0.2.0` 六份、`docs/benchmarks/task-set.md`、`docs/case-studies/attachments/` 两份 | 低优先，与英文同样处理 |
| （地图无对应行） | — | **待新增**：`docs/how-to-verify.zh-CN.md` | 本树 `git ls-files docs/` 无此文件（另一窗口正在新增）。落地后：中文 README 的复核入口改指该页；若该页最终不落地，则仍指 `docs/how-to-verify.md` |

---

## 3. 缺失项明细（仓库里有，两份地图都没有）

按访客价值排序。

| # | 文档 | 在树里的位置与作用 | 从 README 可达？ | 建议 |
|---|---|---|---|---|
| 1 | `docs/reports/README.md` | 报告目录索引：每份报告回答什么问题、什么时候该看它、哪些是历史记录不该当现状读（自述 37 份，实际只覆盖 42 份里的 37 份） | **不可达**。全树入链只有 `docs/releases/v1.0.0.md` 与本页，两份 README 都够不着；两份 README 只能到达 5 份报告（`m4-e2e-run`、`phase3-baseline`、`phase1-review-report`、`phase1-maturity-assessment`、`phase2-issue-list`），其余 37 份不可达 | 两份 README 的「项目记录」段各加一条 |
| 2 | `docs/releases/v1.0.0.md` | v1.0.0 发版说明：Phase 3 交付了什么、边界在哪 | 不可达（全树 21 条入链，0 条来自 README）。`README.zh-CN.md:31` 明写「见发版说明」却**没有链接**——悬空指路 | 两份 README 各加一条；中文 `:31` 那半句补链接或删掉 |
| 3 | `docs/case-studies/README.md` | 案例索引页，明写「阅读这些案例不需要安装 DexAtlas，只需要愿意核一个定位符」 | 不可达 | 两份 README 的案例段各加一条 |
| 4 | `docs/architecture/{analysis-runs,call-sites-and-edges,evidence-invariants,runtime-isolation}.md` | 架构目录 13 份里的 4 份 | 两跳可达（`docs/architecture/README.md` 链到其中 3 份） | 可用一条「架构其余各页」概括 |
| 5 | `docs/architecture/diagram.md` | 架构图说明 | 两跳不可达——`docs/architecture/README.md` 也没链它 | 同上，或在 `docs/architecture/README.md` 里补链 |
| 6 | `docs/portfolio.md` | 作品集/对外定位页 | 不可达（全树 18 条入链，0 条来自 README） | 低优先 |
| 7 | `docs/proposals/exit-code-partial-read.md` | 退出码 6（`EXIT_NO_INDEX`）的提案 | 不可达（全树 10 条入链，0 条来自 README） | 低优先 |
| 8 | `docs/outreach/{publish-review,cover-letter-templates,scope-ai-mcp,scope-backend-automation}.md` | 对外投稿与范围材料 | 不可达；同目录的 `project-brief.md` 已在 `README.md:567` | 低优先 |
| 9 | `docs/releases/v0.1.0.md`–`v0.2.0.md`（六份） | 历史发版说明 | 不可达 | 低优先，可收进 `docs/releases/` 一条 |
| 10 | `docs/benchmarks/task-set.md` | 冻结题集原始定义 | 不可达 | 低优先 |
| 11 | `docs/case-studies/attachments/{demo-report,obfuscated-report}.md` | 案例的报告与证据包附件 | 不可达；`docs/case-studies/README.md` 已提 attachments 目录 | 低优先 |
| 12 | `docs/how-to-verify.zh-CN.md` | 中文版「怎么自己复核」页 | **本树不存在**，另一窗口正在新增 | 落地后中文 README 改指该页 |
| 13–15 | `docs/architecture/README.md` 之外的 5 份架构页 / `docs/outreach/` 四份 / `docs/releases/` 六份旧发版说明 | （分组计数，详见上表 4–11 行） | — | 见上 |

**分组计数说明**：上表 1–12 为 12 条独立条目；13–15 是三组同质文件的计数别名
（架构其余 5 份、`docs/outreach/` 4 份、`docs/releases/` 旧发版说明 6 份），已在 4/5/8/9 行逐份列出，
不重复计入。

---

## 4. 描述已过期

| # | 位置 | 地图/文档现在写的 | 文件现在的实际状态 | 建议改法 |
|---|---|---|---|---|
| 1 | `docs/reports/README.md:3` 与 `docs/reports/README.md:28` | 「三十七份报告」；分组表合计 `37` | `docs/reports/` 下实际有 **42** 份报告（另加 1 份索引；本页落地前是 41 份），索引自己没链到的 4 份：`english-reader-review.md`、`m10-invitation-sender-checklist.md`、`new-pages-crosscheck.md`、`outreach-publish-checklist.md` | 改实数并补这 4 份。**注意**：本页 `docs/reports/readme-map-audit.md` 落地后数字已是 42，改索引的人要把这份也算进去 |
| 2 | `README.zh-CN.md:31` | 「退出标准未全部达成（**M6 未收口、M10 未开始**）」 | 英文 `README.md:41` 同位置写的是「(M6, M8 and **M10** are still open)」；而中文自己的 Roadmap status 表里 M8 行写的是「**部分完成**」 | 中文摘要补 M8，或改成与英文一致的表述 |

> 第 2 条严格说不在「文档地图」范围内（它在顶部状态段），但它是本轮复核读 README 时撞见的
> 中英不一致，且会让读者误判 M8 已完成，故一并记下。

---

## 5. 中英不对称（英文有、中文没有）

| # | 英文位置 | 英文写的 | 中文缺什么 | 影响 | 建议改法 |
|---|---|---|---|---|---|
| 1 | `README.md:477` | `docs/how-to-verify.md` —「怎么自己复核这个项目说的每句话」 | 中文「项目记录」段**完全没有这一条** | 中文访客走不了「复核」这一步。该页本身是中文的（`docs/how-to-verify.md:18` 明写「README 的对应入口行上也注明了这一点」），而中文 README 这一行根本不存在 | `README.zh-CN.md` 的项目记录段补一条；若 `docs/how-to-verify.zh-CN.md` 落地则改指该页 |
| 2 | `README.md:475` | `docs/service-commitments.md` — 服务承诺覆盖与明确不做的事 | 中文项目记录段无 | 中文访客看不到「哪些事本工具不做」 | 补一条（低优先：英文那条本身是中文文档） |
| 3 | `README.md:443` 与 `README.md:454` | 两轮窄验证记录（2/6 与 3/6），各带完整数字与「未达门槛」结论 | 中文「基准」段止于 `README.zh-CN.md:360` 的三轮完整复测，没有窄验证两轮 | 中文读者在基准段看不到 M6 收口的最后两步；这两条在中文顶部状态段有链接，但那是状态说明，不是文档地图 | 在 `README.zh-CN.md:360` 之后补两条 |
| 4 | `README.md:390`（glossary）与 `README.md:416`（服务回归集链 glossary） | 架构条目点名 glossary 及其四项术语；服务回归集条目直接链到 `docs/architecture/README.md#glossary` | 中文架构条目（`README.zh-CN.md:330`）只写「流水线、存储模型与设计取舍」，无 glossary；服务回归集条目（`README.zh-CN.md:346`）也没链 | `docs/benchmarks/service-regression-set.md:169` 把中文读者指向 `../architecture/README.md#glossary` 看「判分七条红线」——中文 README 两处都没有这根指路 | 补一句 glossary 指引 + 一处链接 |

> 四条都出现在「项目说清楚了没有」这条轴上：中文 README 在这一轮**落后于**英文，不是领先。

---

## 6. 入口够不够用：三步检查

以「一个第一次打开 GitHub 页面、拿着 README 的外部访客」为准。

| 步骤 | 英文访客 | 中文访客 | 依据 |
|---|---|---|---|
| **了解：这个项目在说什么** | ✅ 通 | ✅ 通 | 顶部状态段 + `docs/status.md` + `docs/roadmap/ROADMAP.md` + `docs/analysis-provenance.md`（中英均在地图内） |
| **复核：怎么自己核** | ✅ 通 | ❌ **断** | 英文 `README.md:477` → `docs/how-to-verify.md`；中文地图无此条 |
| **找报告：报告在哪** | ❌ **断** | ❌ **断** | 两份 README 都只列了 5 份报告，没有 `docs/reports/README.md` 这根指路；`docs/reports/` 下 42 份报告里 37 份从 README 走不到 |

英文访客走完三步要靠两处运气：点到 `docs/how-to-verify.md`，再自己意识到「42 份报告在
`docs/reports/` 里，但没索引」。中文访客第一步就断了。

---

## 7. 必须改的 N 处

只列清单，不代改。

1. **`README.zh-CN.md`（项目记录段，`README.zh-CN.md:365` 起）补一条 `docs/how-to-verify.md`**（若 `docs/how-to-verify.zh-CN.md` 落地则改指该页）——中文访客「复核」这一步目前无入口。
2. **`README.md` 与 `README.zh-CN.md` 的项目记录段各补一条 `docs/reports/README.md`**（报告目录索引）——「找报告」这一步目前无入口，42 份里 37 份不可达。
3. **`README.md` 与 `README.zh-CN.md` 的项目记录段各补一条 `docs/releases/v1.0.0.md`**；同时把 `README.zh-CN.md:31` 的「见发版说明」补成链接或删掉该半句。
4. **`README.zh-CN.md` 的基准段（`README.zh-CN.md:360` 之后）补两条**：`docs/benchmarks/m6-level2-narrow-verify2.md`、`docs/benchmarks/m6-level2-narrow-verify3.md`。
5. **`README.zh-CN.md` 的项目记录段补一条 `docs/service-commitments.md`**。
6. **`README.zh-CN.md:330` 与 `README.zh-CN.md:346` 补 glossary 指引**（`docs/architecture/README.md#glossary`），与英文 `:390`/`:416` 对齐。
7. **`docs/reports/README.md:3` 与 `docs/reports/README.md:28` 的「三十七份」改为实数**，并补链 4 份漏掉的报告（`english-reader-review.md`、`m10-invitation-sender-checklist.md`、`new-pages-crosscheck.md`、`outreach-publish-checklist.md`）；本页 `readme-map-audit.md` 落地后数字再改一次。
8. **`README.zh-CN.md:31` 的退出标准摘要补 M8**（与英文 `README.md:41` 对齐；中文自己的 Roadmap status 表已写 M8「部分完成」）。
9. **`README.md:377` 与 `README.zh-CN.md:319` 的案例段各补一条 `docs/case-studies/README.md`**（案例索引页）。
10. **`README.md:388` 与 `README.zh-CN.md:328` 的架构段收进 `docs/architecture/` 其余各页**（至少 `analysis-runs.md`、`call-sites-and-edges.md`、`evidence-invariants.md`、`runtime-isolation.md`、`diagram.md`）；`diagram.md` 目前连 `docs/architecture/README.md` 都没链。

> 上述 10 条中，1–4 条是「外部访客会走不通」的直接原因；5–10 条是完整性缺口。
> 低优先但同批可做：`docs/portfolio.md`、`docs/proposals/exit-code-partial-read.md`、
> `docs/outreach/` 四份、`docs/releases/` 旧发版说明六份、`docs/benchmarks/task-set.md`、
> `docs/case-studies/attachments/` 两份。

---

## 8. 三步结论（单独一句）

**访客从 README 出发能走完「了解」，走不完「复核」（中文 README 卡住，`README.zh-CN.md:365`
的项目记录段没有 `docs/how-to-verify.md`），也走不完「找报告」（两份 README 都没有指向
`docs/reports/README.md`，42 份报告里 37 份从 README 不可达）。**

---

## 9. 复核方法与可复现命令

只读复核，未运行任何写入型命令；未使用 `--cov`、未运行 `uv sync`、未运行
`scripts/refresh-report-figures.py`、未联网、未推送、未打 tag。

在 worktree `E:\Dexatlas\.claude\worktrees\readme-map-audit-b68ec2` 内执行：

```bash
git ls-files docs/            # 104 份 docs/**/*.md 的完整清单
python - <<'PY'               # 提取两份 README 的相对链接、比对差集
import re, pathlib
def doclinks(fn):
    res = {}
    for i, l in enumerate(open(fn, encoding='utf-8').read().splitlines(), 1):
        for m in re.finditer(r'\]\((docs/[^)#]+)', l):
            res.setdefault(m.group(1), []).append(i)
    return res
print(sorted(set(doclinks('README.md')) - set(doclinks('README.zh-CN.md'))))
PY
ls docs/reports/*.md | wc -l  # 43（42 份报告 + README.md 索引；本页落地前是 42）
```

只读门禁（用主 checkout 的 venv，`PYTHONPATH` 指向本 worktree 的 `src/`，未改任何文件）：

| 命令 | 结果 |
|---|---|
| `pytest tests/test_docs.py -q` | **60 passed**（无 skip、无 fail） |
| `python scripts/check-doc-citations.py` | `citations: 221`，`unresolved paths: 0`，`drifted: 0`，EXIT=0 |
| `python scripts/check-version-claims.py --base auto` | `findings: 2 (2 already in 8f9ddcaf)`（`docs/releases/v0.2.0.md:326`、`CHANGELOG.md:1033`，均为基线既有豁免），EXIT=0 |

**门禁能查什么、查不到什么**：现有门禁只验「链接不失效」（`tests/test_docs.py` 的
`test_all_relative_links_resolve`）与「行号引用不漂移」，**没有任何一条检查地图的完整性
或中英等价性**——本文列的 21 条问题全部能通过这三道门禁。若要防复发，需要新增一条针对
「文档地图覆盖面」的测试（例如：两份 README 的地图条目集合必须相等，且必须包含
`docs/reports/README.md`）。
