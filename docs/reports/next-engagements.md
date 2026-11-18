# 下一轮接活可行性纪要：这个项目现在能接什么活、值多少钱、还缺什么

日期：2026-11-17。调研基准：本 worktree 的 `0104ccb`（= tag `v1.0.0` 指向的 commit，
`git rev-parse v1.0.0^{commit}`）。

> **本文是什么**：一次**只读**调研的纪要。全部结论都能回指仓库里已落盘的文件。
>
> **本文不是什么**：不是接单计划、不是报价单、不是客户材料、不是验收结论。
> 本文新增后没有修改任何既有文件；调研期间没有联网、没有登录任何平台、
> 没有发布任何内容，也没有运行 `pytest --cov`、`coverage`、`uv sync`
> 或 `scripts/refresh-report-figures.py`。
>
> **一句免责**：文中涉及「对外能说什么」的部分，依据的是仓库里已定稿的对外素材
> （[docs/outreach/](../outreach/)）与发版说明；它不是法律意见，也不替代平台规则。

---

## 0. 结论速览

| 问题 | 结论 | 依据 |
|---|---|---|
| 能接几类活？ | **两类**，素材里已写明的服务范围：Python Backend & Automation、Evidence-first AI / MCP Integration | [scope-backend-automation.md:15](../outreach/scope-backend-automation.md#L15)、[scope-ai-mcp.md:19](../outreach/scope-ai-mcp.md#L19) |
| 值多少钱？ | **仓库里没有价格依据**；建议先做 1–2 单低价试点来校准 | [phase3-plan.md:201](../roadmap/phase3-plan.md#L201)（明确「不凭作品集推导小时费率」）、[portfolio-readiness-2026-11-15.md:71](portfolio-readiness-2026-11-15.md#L71)（报价能力需接单后另行建立） |
| 典型工期？ | **素材里没有写工期数字**；两份 scope 写的是「里程碑 + 书面验收标准」，工期由里程碑数逐段约定 | [scope-backend-automation.md:49](../outreach/scope-backend-automation.md#L49)、[scope-backend-automation.md:83](../outreach/scope-backend-automation.md#L83) |
| 最要紧缺什么？ | **M10 独立验收尚未开始**——它是「对外说已完成验收」的门槛 | [status.md:138](../status.md#L138)、[status.md:3](../status.md#L3) |
| 现在能对外说什么？ | 能说「v1.0.0 已发布 + 两类服务范围 + 可复现样例」；**不能说**已有客户、收益、或已完成独立验收 | [publish-review.md:307](../outreach/publish-review.md#L307) §7 |

---

## 1. 能接的两类活

素材里已写明的服务范围只有两份范围说明
（[scope-backend-automation.md](../outreach/scope-backend-automation.md)、
[scope-ai-mcp.md](../outreach/scope-ai-mcp.md)），本节照抄它们的承诺边界，
不新增第三类。

### 1.1 方向 A —— Python Backend & Automation

**一句话**：按约定的流水线交付 Python 后端与自动化任务——CLI / REST API 接入、
数据摄取与归一化、结构化存储、可重复执行的任务，以及机器可读报告；
测试、类型标注与文档是交付物的一部分。

**输入**（客户需要提供，[scope-backend-automation.md:27](../outreach/scope-backend-automation.md#L27)）：

- 要对接的既有工具、服务、数据格式或文件格式；
- 期望的流水线：什么进来、什么出去、什么形状；
- 运行环境（客户机器 / 容器 / CI job）与运行时约束；
- 有权分享的样本数据，以及处理上的合规约束；
- 已有验收标准；没有就先一起定义，再开工。

**交付**（典型清单，[scope-backend-automation.md:38](../outreach/scope-backend-automation.md#L38)）：

- 实现约定流水线的 Python 包或服务；
- CLI 和 / 或 REST API，附文档化的端点与错误语义；
- 结构化输出（JSON / Markdown / SQLite / CSV，按约定），带 schema；
- 覆盖约定行为的自动化测试套件，加 lint 与类型检查配置；
- README / runbook：安装、配置、用例、已知限制；
- 一次简短交接讲解（书面；可按需约一次通话）。

**验收怎么判**（[scope-backend-automation.md:49](../outreach/scope-backend-automation.md#L49)）：

1. 验收标准在实现开始**之前**写下来；
2. 每项交付都由一个**可运行的测试**或一次**有记录的人工核验**证明——
   没人能复算的数字或行为不算声明；
3. 客户拿到测试套件与运行说明，验收在客户那边可复现，而不是靠演示；
4. 按书面标准评审里程碑；变更走约定的变更流程。

**典型工期**：**素材里没有工期数字。** 两份范围说明都没有写天数或周数
（全文检索 `week` / `days` / `deadline` / `turnaround` 无命中），它们写的是
**里程碑制**：变更请求被分成「范围内澄清 / 变更请求（先估算、先达成一致再动手）/
新里程碑」三类（[scope-backend-automation.md:83](../outreach/scope-backend-automation.md#L83)）。
所以对外沟通工期的正确说法是：**先按具体样本与需求估算，按里程碑逐段约定**，
而不是引用一个来自本仓库的固定天数。仓库里唯一与「工期」沾边的数字是
Phase 3 自身 M5–M10 的排期（[phase3-plan.md:72](../roadmap/phase3-plan.md#L72)），
那是**作者自己建仓库**的投入，不是客户项目的工期，不能拿来当报价依据。

**明确排除**（[scope-backend-automation.md:59](../outreach/scope-backend-automation.md#L59)）：
渗透测试与漏洞发现、持续生产运维与 24/7 值守、未指明规模的性能保证、
移动动态分析 / native `so` 逆向 / 恶意软件定性、以及无权分析的内容。

### 1.2 方向 B —— Evidence-first AI / MCP Integration

**一句话**：用 MCP 与工具 API 把 AI 助手接到客户已有的数据与工具上，
按证据优先设计——助手通过受控的、只读或最小权限的工具读客户的真实数据，
它给出的每个答案都能回指到来源记录；模型输出是线索，不是结论。

**输入**（[scope-ai-mcp.md:34](../outreach/scope-ai-mcp.md#L34)）：

- 助手要对接的数据源 / 服务 / 工具，以及它们的访问方式（API、数据库、文件）；
- **有界的问题集**：AI 集成必须处理的具体问题或任务（有界才可测试、成本才可预期）；
- 客户的模型与供应商约束：哪个供应商 / 模型、隐私规则、哪些数据不得离开环境；
- 模型账号与 API key 归谁所有（见费用条款）；
- 验收标准，或愿意在开工前一起定义。

**交付**（典型清单，[scope-ai-mcp.md:47](../outreach/scope-ai-mcp.md#L47)）：

- 一个 MCP server 或工具层，把客户的数据 / 操作暴露给 AI 助手，
  权限显式（默认只读）、响应有界、工具调用有审计；
- 一个在既定预算内规划工具调用的 agent / 工作流设计，
  报告分三层：**已确证（带引用）**、**只是线索**、**无法确证**；
- 一个评测包：一组带预期证据的问题、一个 runner、录制的结果，
  以便任何改动之后能重跑；
- 文档：架构、工具目录、安全边界、证据 / 引用格式；
- 工具层的测试（确定性、不需要模型），以及模型驱动部分的录制评测。

**验收怎么判**（[scope-ai-mcp.md:62](../outreach/scope-ai-mcp.md#L62)）：

1. 验收标准在实现前写定；
2. 工具层由自动化测试验证；模型驱动的行为由约定的评测集验证，
   **通过与失败都要留记录**——失败的评测是信息，不是需要藏起来的尴尬；
3. 最终报告里的说法分级：`verified`（经工具从客户数据确证）/ `lead`（需人工确认的模型建议）/
   `insufficient`，模型文本永不被记成已确证事实；
4. 客户在交接后可以自己重跑评测包。

**典型工期**：**同样没有数字。** 范围说明写的是「先估算再达成一致 / 新里程碑」
（[scope-ai-mcp.md:109](../outreach/scope-ai-mcp.md#L109)）。
本方向的实际排期受一个客户侧变量支配——**评测集的大小**与**模型预算授权**：
问题集越大、评测轮次越多，工期越长，而这两项都要客户先给定
（[scope-ai-mcp.md:36](../outreach/scope-ai-mcp.md#L36)）。

**模型费用归属**（[scope-ai-mcp.md:86](../outreach/scope-ai-mcp.md#L86)）：
**客户自备模型账号与 API key，费用由供应商直接向客户收取，作者不加价**；
每次模型调用的用途写进交接记录，客户可对照自己的账单审计。
开发与测试默认用最便宜且够用的模型，工具层与模型无关。

**明确排除**（[scope-ai-mcp.md:74](../outreach/scope-ai-mcp.md#L74)）：
自主漏洞发现 / 自主安全测试、可修改系统或执行 shell 的 agent、
「找全所有 bug」「取代分析师」「胜过所有模型」这类承诺，以及
在客户数据上训练或微调模型（可另议，不在本服务内）。

### 1.3 不作为独立服务方向的第三项

[phase3-plan.md:36](../roadmap/phase3-plan.md#L36) 的服务定位表里其实有**三行**，
第三行是「有限范围 APK 静态分析」。它**不是**第三个可报价的服务方向：

- 它在对外素材里没有独立的范围说明文件——`docs/outreach/` 只有两份 `scope-*.md`；
- 它的边界被写死为「不等同渗透测试、恶意软件定性、真实加固还原或 native/dynamic 分析」
  （[phase3-plan.md:40](../roadmap/phase3-plan.md#L40)）；
- 在范围说明里它只作为**排除条款中的一次例外引用**出现：
  方向 A 明确写「我能提供的 APK 分析就是 DexAtlas 示例里那份有限静态范围」
  （[scope-backend-automation.md:67](../outreach/scope-backend-automation.md#L67)）。

**因此**：对外的落点是两类服务；APK 静态分析作为**作品样例 / 附加案例**，
用来证明工程深度（[phase3-plan.md:42](../roadmap/phase3-plan.md#L42)），
不单列成一个可报价的品类。

---

## 2. 报价区间

### 2.1 结论：仓库里没有价格依据

我把整条线索查到底了：

| 检索目标 | 范围 | 结果 |
|---|---|---|
| 价格 / 费率 / 报价 / 工时 | `docs/outreach/` 四份素材 + `docs/portfolio.md` | **零命中**（唯一一处「报价」出现在 `publish-review.md:349`，是一条**禁令**：「不要在发布文案里出现收益、工时节省或客户案例」） |
| 数字货币 / 时薪 / rate card | 全仓库 `docs/` | 无对外报价口径 |
| 素材里的可用性承诺 | 四份素材 | 零：邮箱、`mailto:`、时区、可用时间、响应时限**全部零命中**（[publish-review.md:338](../outreach/publish-review.md#L338)） |

三处**明文的否定依据**：

1. **[phase3-plan.md:201](../roadmap/phase3-plan.md#L201)**：M9 的交付约定是
   「先按具体样本与需求估算，**不凭作品集推导小时费率或承诺固定收益**」。
   换句话说，仓库自己就禁止用作品集反推价格。
2. **[portfolio-readiness-2026-11-15.md:71](portfolio-readiness-2026-11-15.md#L71)**：
   「客户评价、**报价能力**、沟通、真实付费交付经历需要在接单后另行建立，
   不能用个人项目替代。」
3. **[portfolio-readiness-2026-11-15.md:4](portfolio-readiness-2026-11-15.md#L4)**：
   整份准备度评估「不是生产成熟度认证、客户调查或**接单概率**」。

所以**本报告不写金额区间**。写一个「市场价」就等于凭空拍价，
恰恰违反本项目 CLAUDE.md 第 2 条（无生产声明缺少可复算依据）。

### 2.2 能说的：有价格**依据**之后怎么说

仓库里没有任何数字可以当价格锚点，因此报价只能来自**一次具体样本的估算**，
而估算的前提是范围先定死。素材已经把这个前提写好了：

- 方向 A：输入清单五项（[scope-backend-automation.md:27](../outreach/scope-backend-automation.md#L27)）
  + 验收标准前置 + 里程碑制；
- 方向 B：输入清单五项（[scope-ai-mcp.md:34](../outreach/scope-ai-mcp.md#L34)）
  + 评测集大小 + 预算边界；
- 两份素材都写了变更流程：估算先于变更，**不做「悄悄吸收」**
  （[scope-backend-automation.md:83](../outreach/scope-backend-automation.md#L83)、
  [scope-ai-mcp.md:109](../outreach/scope-ai-mcp.md#L109)）。

**可用的报价格式**（按素材自己写的口径，不是新发明）：按里程碑固定报价，
每个里程碑先写验收标准再开工，变更请求先估算先达成一致。
「按时计费」在这个项目里没有依据——没有工时记录，也没有可公开的历史费率。

### 2.3 建议：先做 1–2 单低价试点来校准

**仓库里没有价格依据，建议先做 1–2 单低价试点来校准。**

理由来自仓库自身：

1. **停止点条款就是为此设的**：[phase3-plan.md:228](../roadmap/phase3-plan.md#L228)
   「达到停止点后，下一轮投入由**真实提案反馈或付费试点**决定，另建需求与计划」。
   试点是计划里写明的下一步，不是本文发明的动作。
2. **试点是唯一能产生价格依据的动作**：报价能力被明确归入「接单后另行建立」
   （[portfolio-readiness-2026-11-15.md:71](portfolio-readiness-2026-11-15.md#L71)），
   仓库内任何文档工作都替代不了它。
3. **试点是「有边界的真实问题」**：方向 A 的范围说明要求验收标准前置
   （[scope-backend-automation.md:49](../outreach/scope-backend-automation.md#L49)），
   方向 B 要求有界问题集与评测集
   （[scope-ai-mcp.md:36](../outreach/scope-ai-mcp.md#L36)）——两者都适合做小规模试点，
   且都不需要动 M10。

**试点价怎么定**：本文不给数字，只给规则——
**按「一个里程碑的最小可交付范围」定一个低价**，并把这个价当作**校准样本**，
而不是当作市场行情。第一单的作用是产生一个**可复算的记录**：
交付了什么、验收标准是什么、实际投入了多少、结论是什么。
第二单再据此调整。任何一单做完都要把结果回写成仓库里的记录
（像 M6 的评测记录那样，数字由脚本重算），而不是留在记忆里。

### 2.4 禁止出现在报价相关文案里的东西

素材已经写死，且 publish-review 把它列为发布前人工确认项
（[publish-review.md:349](../outreach/publish-review.md#L349)）：

- 不写收益、时薪节省、任何「帮客户省了多少」的数字；
- 不写或暗示已有客户、客户结果（当前没有任何客户）；
- 不引用 M6 的 49/60 = 81.7% 当作「准确率 81.7%」——
  若要写，必须同时写明**未达验收线**（[publish-review.md:301](../outreach/publish-review.md#L301)）。

---

## 3. 为接活还缺什么

按「挡住接活」的程度排序。每条都指回仓库事实。

### 3.1 最要紧：M10 独立验收尚未开始

**[status.md:138](../status.md#L138)**：「M10 独立验收 | **准备包就绪，验收未开始**」。
准备包是齐的——40 项验收检查表、读者一站式入口、作者侧自动化自查（40/40 通过）、
邀请函成稿、发起人发送前清单都已合入；**缺的是「一位未参与实现的读者真的按包跑一遍」**
这个动作（[phase3-plan.md:211](../roadmap/phase3-plan.md#L211)）。

**为什么它挡住接活**：它是「对外说已完成验收」的门槛。
Phase 3 的退出标准要求 M5–M9 全部验收、M10 完成独立复现与重评
（[phase3-plan.md:219](../roadmap/phase3-plan.md#L219)）；M10 未做意味着
**对外最多只能说「自评」，不能说「已验收」**。

**可复核的量**：准备度复评（作者自评）当前是
**GitHub 81.25% / Upwork 76.9%，两平台平均 79.1%**
（[portfolio-readiness-2026-11-15-recheck.md:227](portfolio-readiness-2026-11-15-recheck.md#L227)），
**未达计划要求的各 ≥90%**（[phase3-plan.md:17](../roadmap/phase3-plan.md#L17)）。
准备度评估里给出的最小路径里，**M10 独立验收是单项增量最大的一项**
（GitHub +10.0、Upwork +8.75，[portfolio-readiness-2026-11-15-recheck.md:127](portfolio-readiness-2026-11-15-recheck.md#L127)）。

**这一步需要仓库外的动作**：真实外部读者。仓库内任何文档工作都替代不了它
（[portfolio-readiness-2026-11-15-recheck.md:236](portfolio-readiness-2026-11-15-recheck.md#L236)）。

### 3.2 M6 层级 2 三轮合计未达验收线

修复后三轮完整重测 **49/60 = 81.7%**（逐轮 15/16/18），验收线是
「每轮 ≥80% 且三轮合计 ≥90%」，**未达标**
（[status.md:37](../status.md#L37)、[m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md)）。

**为什么它挡住接活**：它决定**方向 B（AI / MCP）能承诺到多宽**。
素材里不引用这个数字（不提即不宣称，合法），但一旦有客户问「你的 agent 准不准」，
诚实答案只能是「在一套冻结的 20 题服务回归集上，三轮合计 81.7%，未达我们自己的 90% 线」。
按冻结纪律，修法是**修正系统或缩小并重述服务承诺后重测**，不能删题换通过率
（[status.md:134](../status.md#L134)）。

**能不能绕过**：能，但要把服务承诺改窄。范围说明里「不承诺全自动找漏洞」
的排除条款（[scope-ai-mcp.md:76](../outreach/scope-ai-mcp.md#L76)）已经预留了这个位置——
**把方向 B 的卖点放在工具层与证据链（已达标、已验证），而不是放在模型判断力（未达标）**。

### 3.3 Upwork 服务页与对外素材仍是草稿、未发布

四份素材首尾都印着 `Draft for review — not published.`，Identity note 明确
「个人 / 自筹开源项目，没有客户、没有客户结果、不声称收益或工时节省」
（[publish-review.md:173](../outreach/publish-review.md#L173)）。
发版说明里也写着 `Upwork materials remain unpublished drafts.`
（[releases/v1.0.0.md:78](../releases/v1.0.0.md#L78)）。
**素材已备好，但对外没有落点**——这是「能不能接活」与「能不能接活」之间的一步。

### 3.4 三个证据包只覆盖了两次分析（**2026-11-18 已闭合**）

三个 zip（`demo-` / `obfuscated-` / `api-integration-`）里，
**demo 与 api-integration 的 `report.md` / `report.html` 是同一份分析报告**（字节相同），
只有 `report.json` 与 `manifest.json` 不同
（[publish-review.md:341](../outreach/publish-review.md#L341)，
[portfolio-readiness-2026-11-15-recheck.md:211](portfolio-readiness-2026-11-15-recheck.md#L211)：
两次分析分别是 `apk_80a8fe0e81204c9f` 与 `apk_2f8d476fb9e71ac4`）。

**结论**：三篇走查、三个证据包，**实际只有两次独立分析**。附件时不能当成三份独立证据报数。

> **已闭合（2026-11-18）**：附件集换过一轮，现在仓库里是**四个证据包、四次
> 分析**——`run_e8e49384…`（demo）、`run_fc8e432d…`（api-integration）、
> `run_dd897202…`（obfuscated）、`run_4fde2fa0…`（multidex），run id 两两不同，
> 每个包都过了 `verify_package`。demo 与 api-integration 仍然是**同一份 APK 的两次
> 分析**（报告只差 `run_id` 与 `Analysis time` 两行），但那是「一次样本、两次
> 分析」，不是「一次分析、两个包」。测量与逐条哈希见
> [case-studies-third-package.md](case-studies-third-package.md)。

### 3.5 第三个样本（multi-DEX）只有走查附录，没有证据包（**2026-11-18 已闭合**）

走查 2 的附录覆盖了 `examples/multidex-app/multidex.apk`
（[case-studies/README.md:30](../case-studies/README.md#L30)），
但 `docs/case-studies/attachments/` 里**没有** multidex 的报告与证据包
（现有 9 个文件对应 demo / obfuscated 两个样本）。

**要不要补**：值得，但**优先级低于 §3.1 与 §3.4 的核对**。
理由：§3.4 是「对外不能报错数」的风险（已经发生的表述风险），
§3.5 是「对外证据更丰富」的增益。而且从接活角度看，
**它恰好是三篇走查里唯一能证明「多 DEX / 跨 DEX 类定义」这种难度的材料**，
而这正是方向 A 里「数据摄取与归一化」能讲的硬活。

> **已闭合（2026-11-18）**：`multidex-evidence-package.zip` 与
> `multidex-report.{md,json,html}` 已落盘（`run_4fde2fa0b5254ccb`，4.7 s，
> `verify_package` 与 9 条引用全部通过），走查 2 的附录与
> [case-studies/README.md](../case-studies/README.md) 都已补上链接。

### 3.6 联系方式、时区、可用性在素材里一个都没有

四份素材是模板 + 成稿：邮箱、`mailto:`、GitHub 个人主页、报价、时区、
工作日 / 周末、每日可投入时间、响应时限，**全部零命中**
（[publish-review.md:139](../outreach/publish-review.md#L139)、
[publish-review.md:145](../outreach/publish-review.md#L145)）。
这不是错误，是**尚未写**——而平台表单通常要填，且填的是**本人真实可用的**信息，
不要虚构响应时长（[publish-review.md:338](../outreach/publish-review.md#L338)）。

### 3.7 对外数字会过期

`project-brief.md` 的 §Honest limitations 现在写
`The current release is v1.0.0 (tagged 2026-11-17)`——这句是真的，
但它说的是「当前最新版本」。**再发一个 tag，这句就变成假话**，
`scripts/check-version-claims.py` 会直接报出来（[publish-review.md:312](../outreach/publish-review.md#L312)）。
同样，1,612 / 93.3% 这两个数**任何一次完整测量都会改**
（[publish-review.md:332](../outreach/publish-review.md#L332)）。

### 3.8 GitHub 呈现层：元数据与落盘事实有三处漂移

[github-repo-metadata-proposal.md:184](github-repo-metadata-proposal.md#L184) 列了 11 项缺口，
其中三项是「元数据与仓库落盘事实对不上」：

1. **许可证自相矛盾**：右侧栏写 `Other`，README 徽章与 `pyproject.toml` 写 Apache-2.0
   —— **已关闭**：`LICENSE` 原是「Apache-2.0 头部 + Apache-1.1 短版正文」的混本
   （仓库宣称 Apache-2.0，却没授予它），已换成与官方逐字节一致的全文，GitHub 现已
   识别为 `Apache-2.0`；
2. **「已发布」在 Releases 页对不上**：README 与 `docs/status.md` 说 v1.0.0 已发布，
   而「当时 Releases 页列的还是 `v0.2.0`」—— **已关闭**：v1.0.0 的 Release 已发布；
3. **报告索引不可达**：两份 README 都没有 `docs/reports/README.md` 入口。

**三项现在都已关闭**：第 3 项在本 worktree 的 `README.md:528` 与 `README.zh-CN.md:427`
都已有「报告目录索引」入口，索引文件 `docs/reports/README.md` 存在
（commit `a494e13`）；第 1 项由 `LICENSE` 修复；第 2 项由发布 v1.0.0 的 Release 关闭 ✓。

**这一条为什么算「接活还缺」**：访客在仓库页上看到的每一个对不上的地方，
都会被读成「文档没跟上」——对一份以「结论必须能指回来源」为纪律的项目，
这是最不该先露出来的破绽。

### 3.9 README 独立首读复核结论未回填

准备度评估列出的第 5 项待办：「README 独立首读复核结论合入……必要时修正展示文案」
（[portfolio-readiness-2026-11-15-recheck.md:131](portfolio-readiness-2026-11-15-recheck.md#L131)）。
复评里「对外展示与个人贡献说明」维度的扣分理由仍写着「独立首读复核未回填」
（[portfolio-readiness-2026-11-15-recheck.md:224](portfolio-readiness-2026-11-15-recheck.md#L224)）。
**这一项同样需要外部读者**，和 §3.1 可以合并成同一次邀请。

### 3.10 平台字段限制未在真实表单上复核

本轮核对用的是**任务给定的门限**（标题 ≤60、简介 ≤5,000），
Upwork 实际限制会随时间调整；素材头部引用的官方指南链接**本轮没有联网核实**
（[publish-review.md:326](../outreach/publish-review.md#L326)）。
另外 `scope-ai-mcp.md` 全文 plain 6,530 字符 **超过 5,000**——
本轮按「附件 + 只贴 §What I offer（plain 773）」处理，
「要不要整篇粘贴」是一个**编辑判断**，仓库替不了人做
（[publish-review.md:322](../outreach/publish-review.md#L322)）。

### 3.11 内部核对记录绝对不能外发

`docs/outreach/publish-review.md` 是内部记录，含本地路径、分支名、commit
与 M6 评测细节（[publish-review.md:7](../outreach/publish-review.md#L7)）。
它与四份素材**同处一个目录**，外发时按目录整体打包就会带出去
（[publish-review.md:345](../outreach/publish-review.md#L345)）。
素材侧还把读者引向它（「Field lengths are accounted for in publish-review.md」），
所以这个引用在发布前也要一并处理。

### 3.12 小结：缺口的性质

把 §3.1–§3.11 归类，会发现一个规律：

| 性质 | 缺口 | 仓库内能不能做 |
|---|---|---|
| **需要外部读者** | M10 独立验收、README 独立首读复核 | **不能** |
| **需要外部决策 / 动作** | Upwork 服务页发布、联系方式与时区、GitHub 元数据设置、平台表单复核 | **不能** |
| **需要模型预算授权** | M6 层级 2 三轮 ≥90% | **不能**（但可以缩小服务承诺来绕过） |
| **仓库内可做** | 第三个样本的证据包、内部记录的外发隔离、版本句与数字的同步 | **能** |

**结论**：真正挡住接活的缺口**大部分不在仓库里**。
仓库内还能做的，主要是 §3.5 与 §3.11 这两件小事。
这就是为什么「发出去之前该先做什么」这件事，
**必须把「等外部动作」也算进去**（见 §4）。

---

## 4. 发出去之前该先做什么

按顺序。每条注明依据。**这一步不执行任何对外动作**——发不发是作者的决定。

> **顺序的逻辑**：先做「只影响仓库内、不消耗外部资源、不消耗预算」的，
> 再做「需要发一次邀请」的，最后才轮到「需要对外发布」——
> 因为发布一旦发生，素材里的数字、占位符、链接都会立刻变成公开承诺。

| # | 动作 | 依据 | 依赖 |
|---:|---|---|---|
| 1 | **把 M10 独立验收的邀请发出去**（材料已齐：邀请函成稿 + 读者包 + 40 项检查表 + 发起人发送前清单 + 自查脚本 43/43）。先按发送前清单逐条勾，填 7 处空格、钉死验收 commit、确认三个后端、确认附件、约定反馈时限与提交渠道 | [status.md:138](../status.md#L138)（准备包就绪、验收未开始）、[m10-invitation-sender-checklist.md:16](../reports/m10-invitation-sender-checklist.md#L16)（§0 三分钟版）、[phase3-plan.md:211](../roadmap/phase3-plan.md#L211) | 外部读者 |
| 2 | **同一次邀请里一并回填 README 独立首读复核**（§3.9 与 §3.1 可由同一位读者承担，M10 明确允许「同一读者可以承担两项」） | [phase3-plan.md:214](../roadmap/phase3-plan.md#L214)、[portfolio-readiness-2026-11-15-recheck.md:131](portfolio-readiness-2026-11-15-recheck.md#L131) | 依赖 #1 |
| 3 | **决定方向 B 的服务承诺宽度**：要么等 M6 三轮 ≥90% 再对外说 agent 能力，要么**现在就把卖点收窄到工具层与证据链**，并在范围说明里明说 agent 判断力未达内部验收线 | [status.md:37](../status.md#L37)（49/60 = 81.7%，未达标）、[scope-ai-mcp.md:76](../outreach/scope-ai-mcp.md#L76)（排除条款已留位置） | 无（可与 #1 并行） |
| 4 | ~~**补第三个样本（multi-DEX）的证据包**~~ **（2026-11-18 已完成）**：`analyze --html` / `export` + `verify_package`，落盘到 `docs/case-studies/attachments/` | [case-studies-third-package.md](case-studies-third-package.md)（实测与哈希）、[case-studies/README.md:30](../case-studies/README.md#L30)（附录已覆盖该样本） | 无 |
| 5 | **在素材里补上联系方式、时区、可用性**（只写真实可用的；不要虚构响应时长） | [publish-review.md:338](../outreach/publish-review.md#L338)（素材目前零命中） | 无 |
| 6 | **清理外发隔离**：发布前删除素材里的 `Draft for review — not published.` 标记与 Identity note 引用块（按发稿形态决定删哪些）；**不要**把 `docs/outreach/publish-review.md` 当附件；处理素材里指向它的引用 | [publish-review.md:173](../outreach/publish-review.md#L173)（草稿标记与 Identity note 的位置）、[publish-review.md:345](../outreach/publish-review.md#L345)（内部记录不可外发） | 无 |
| 7 | **替换全部 `{{...}}` 占位符**，改完逐个搜 `{{` 确认无残留（Template 1 有 11 处、Template 2 有 10 处） | [publish-review.md:336](../outreach/publish-review.md#L336) | 依赖 #5（联系方式进占位符） |
| 8 | **决定 `scope-ai-mcp.md` 是「整篇做附件」还是「只贴 §What I offer（plain 773）」**；若整篇粘贴，需再压约 1,500 字符——这是编辑判断，得由人做 | [publish-review.md:322](../outreach/publish-review.md#L322)、[publish-review.md:246](../outreach/publish-review.md#L246) | 无 |
| 9 | **按最后一次完整测量再核一次对外数字**（现在落盘的是 1,644 / 93.3%），并确认版本句仍指向当前最新 tag | [publish-review.md:332](../outreach/publish-review.md#L332)、[publish-review.md:312](../outreach/publish-review.md#L312) | 无 |
| 10 | **在真实表单上逐个字段复核长度限制，并联网核实素材头部引用的官方指南链接**（本轮未联网） | [publish-review.md:326](../outreach/publish-review.md#L326) | 无 |
| 11 | **附件逐个确认真的上传了**；注意 demo 与 api-integration 是同一份分析报告，**不要当成两份独立证据报数** | [publish-review.md:341](../outreach/publish-review.md#L341) | 依赖 #4 |
| 12 | **发布**（作品集页 / 提案）。发布前最后确认：文案里没有收益、时时节省、客户案例（[publish-review.md:349](../outreach/publish-review.md#L349)）；`scope-ai-mcp.md` 与 `scope-backend-automation.md` 的附件按第 8 条处理 | [publish-review.md:307](../outreach/publish-review.md#L307)（§7 全文） | 依赖 #1–#11 |

**这条清单的性质**：第 1、2 条要等外部读者，第 12 条是唯一的对外动作，
中间 3–11 条全是仓库内或人工判断。**在 #1 回来之前就发布，等于用「自评」冒充「验收」**——
这是这份清单唯一真正不可让步的一条。

---

## 5. 这一轮不做会怎样

### 5.1 已经成立的事实（可以对外说）

- **v1.0.0 已发布**：tag `v1.0.0`（2026-11-17），指向 commit `0104ccb`。
- **1,644 项测试 / 93.3% 一方代码覆盖率**（`docs/reports/phase1-execution-report.md` 的
  落盘测量值，经 `scripts/refresh-report-figures.py` 生成），mypy strict、ruff、
  CI 覆盖 Python 3.12/3.13 与多种后端配置。
- **四个入口都实现了**：CLI、FastAPI REST API、只读 MCP server（11 个工具）、
  内置的带引用 agent、本地 web workbench。
- **三篇完整走查 + 可下载报告与最小证据包**（16 个文件，均过 `verify_package` 校验），
  样本是一方自带的，可在仓库里复现。
- **两类服务范围、交付、验收、排除项**已经成文（`docs/outreach/`）。
- **身份**：个人、自筹的开源项目，无客户、无客户结果、不声称收益或工时节省。

### 5.2 不能说的话（说了就是本项目禁止的「无人能复算的断言」）

| 不能说 | 为什么 | 依据 |
|---|---|---|
| 「已经通过独立验收」 | M10 独立验收尚未开始 | [status.md:138](../status.md#L138) |
| 「Agent 准确率 81.7%」 | 49/60 = 81.7% **未达**内部验收线（每轮 ≥80%、三轮合计 ≥90%） | [status.md:37](../status.md#L37) |
| 「作品集准备度 90%+ / 达标」 | 作者自评 GitHub 81.25% / Upwork 76.9%，未达各 ≥90% | [portfolio-readiness-2026-11-15-recheck.md:227](portfolio-readiness-2026-11-15-recheck.md#L227) |
| 「有客户 / 有客户案例 / 帮客户省了 X%」 | 没有任何客户；素材明确不宣称 | [publish-review.md:349](../outreach/publish-review.md#L349) |
| 「可以做渗透测试 / 恶意软件定性 / native so 逆向 / 动态分析」 | 两份范围说明都把这些列在排除项里 | [scope-backend-automation.md:59](../outreach/scope-backend-automation.md#L59)、[scope-ai-mcp.md:74](../outreach/scope-ai-mcp.md#L74) |
| 「小时费率 X」或任何固定报价 | 仓库里没有价格依据 | [phase3-plan.md:201](../roadmap/phase3-plan.md#L201) |
| 「三份独立的交付样例」 | 三个证据包只覆盖两次分析（2026-11-18 起：四个包、四次分析，见 §3.4） | [publish-review.md:341](../outreach/publish-review.md#L341) |

### 5.3 两种走法，各自有代价

**走法一：等 M10 回来再发布（推荐）**

- 代价：等外部读者，时间不可控；Phase 3 的停止点条款本来就是
  「下一轮投入由真实提案反馈或付费试点决定」([phase3-plan.md:228](../roadmap/phase3-plan.md#L228))，
  等并不违背计划，但**推迟的收益要够大**才划算。
- 收益：可以把「已验收」写进对外材料，把准备度从 81.25% / 76.9% 推到
  评估里算出的最小路径 **GitHub 92.5% / Upwork 97.5%**
  （[portfolio-readiness-2026-11-15-recheck.md:133](portfolio-readiness-2026-11-15-recheck.md#L133)）；
  而且这一步还能顺带把 §3.9 的 README 首读复核一起关掉。

**走法二：现在就用「自评 + 草稿素材」开始投提案**

- 代价：对外材料只能写「作者自评」，不能写「已验收」；准备度数字对外说出去
  就是 81.25% / 76.9%；§3.1–§3.11 的清单里至少要在发布前把 #3–#11 做完。
- 好处：**这正是 Phase 3 停止点条款想要的样子**——下一轮投入由真实提案反馈决定。
  计划从没要求等 M10 完成才接触市场，它要求的是「真实提案反馈或付费试点」。

**走法三（危险）：先发布、后补 M10，用「准备包就绪」暗示「已验收」**

- 这条路被明确堵死：M10 的规则写着「若由作者先自测，明确标自测，
  不能代替独立验收」（[phase3-plan.md:215](../roadmap/phase3-plan.md#L215)）；
  发版说明里也写着 `No published Upwork service page`
  与「Upwork materials remain unpublished drafts」
  （[releases/v1.0.0.md:78](../releases/v1.0.0.md#L78)、
  [releases/v1.0.0.md:111](../releases/v1.0.0.md#L111)）。
  **发布时的每一句「已验收」都是一个本项目明令禁止的断言。**

### 5.4 本文这一轮做了什么、没做什么

**做了**：只读调研；核对 `docs/outreach/` 四份素材、`docs/roadmap/phase3-plan.md`、
两份准备度评估、三篇走查与证据包（解压核对内容）、`docs/status.md` §4.0、
两份清单（[v1.0.0-release-checklist.md](v1.0.0-release-checklist.md)、
[m10-invitation-sender-checklist.md](m10-invitation-sender-checklist.md)）、
GitHub 元数据复核报告；新增本文。

**没做**：没有修改任何既有文件；没有发布、发送、复制或登录任何平台；
没有联网；没有运行 `pytest --cov` / `coverage` / `uv sync` /
`scripts/refresh-report-figures.py`；没有重测任何数字（本文引用的数字全部来自
仓库里已落盘的报告）。

---

## 附录：事实来源索引

| 主题 | 文件 |
|---|---|
| 两类服务范围（已定稿素材） | [docs/outreach/scope-backend-automation.md](../outreach/scope-backend-automation.md)、[docs/outreach/scope-ai-mcp.md](../outreach/scope-ai-mcp.md) |
| 作品集条目 / 两封提案信 | [docs/outreach/project-brief.md](../outreach/project-brief.md)、[docs/outreach/cover-letter-templates.md](../outreach/cover-letter-templates.md) |
| 素材发布前核对（内部记录，不可外发） | [docs/outreach/publish-review.md](../outreach/publish-review.md) |
| Phase 3 目标、服务定位、停止点条款 | [docs/roadmap/phase3-plan.md](../roadmap/phase3-plan.md) |
| 准备度评估（基线）与复评（作者自评） | [portfolio-readiness-2026-11-15.md](portfolio-readiness-2026-11-15.md)、[portfolio-readiness-2026-11-15-recheck.md](portfolio-readiness-2026-11-15-recheck.md) |
| 里程碑现状与 M10 状态 | [docs/status.md](../status.md) §4.0 |
| 三篇走查与四个证据包 | [docs/case-studies/](../case-studies/) |
| M10 邀请函 / 读者包 / 发送前清单 | [m10-invitation-final.md](m10-invitation-final.md)、[m10-reader-package.md](m10-reader-package.md)、[m10-invitation-sender-checklist.md](m10-invitation-sender-checklist.md) |
| 发版清单与发版说明 | [v1.0.0-release-checklist.md](v1.0.0-release-checklist.md)、[docs/releases/v1.0.0.md](../releases/v1.0.0.md) |
| GitHub 呈现层的缺口 | [github-repo-metadata-proposal.md](github-repo-metadata-proposal.md) |
| M6 层级 2 的实测结果 | [docs/benchmarks/m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md) |
