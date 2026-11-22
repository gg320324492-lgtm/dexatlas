# DexAtlas 服务承诺范围（Service Commitments）

**状态：对外表述边界文档。本文只陈述已有实测证据支持的能力与明确不做的事；所有数字来自已提交的评测报告，由脚本从 trace 重算生成，未手改、未外推。最新实测基准：[m6-level2-deepseek.md](benchmarks/m6-level2-deepseek.md)（2026-11-22，DeepSeek-V4.1-Flash 三轮 56/60 = 93.3%，逐轮 18/20/18——**B1 验收线达成**）；同口径对照：[m6-level2-glm.md](benchmarks/m6-level2-glm.md)（GLM-5.3-Flash 53/60 = 88.3%）、历史 MiniMax 基线 [m6-level2-retest4.md](benchmarks/m6-level2-retest4.md)（49/60 = 81.7%）均留档；**本文 §2 与 §3.3 引的单轮数字来自 [m6-level2-retest2.md](benchmarks/m6-level2-retest2.md)（2026-11-16）那一次**，不是最新一轮。**

本文面向潜在客户与雇主，回答一个问题：**把一个 APK 分析任务交给 DexAtlas，当前可以期待什么、不可以期待什么。** 它不是营销页，每一句能力声明都挂在可点开的证据上。

英文版对这几条的说明（agent service promise）见 [Architecture → Glossary](architecture/README.md#glossary)。

## 1. 本工具做什么 / 不做什么

### 1.1 做什么

DexAtlas 是 evidence-first 的 Android 静态分析工具：输入一个 APK，用三个后端做静态分析——Apktool（manifest 与 Smali）、JADX（反编译 Java）、Androguard（权威 DEX 符号图）——把结果存入 SQLite 工作区，并渲染成带证据出处的 Markdown/JSON 报告。**一个结论必须能沿引用追溯回它来自的字节**；模型输出只是线索，事实性断言必须落到可解析的证据与出处。

在**有限问题集**上，DexAtlas 的 agent 服务可以交付：

- **权限与组件清单**：manifest 声明的包名、权限、exported 组件；
- **指定方法与重载**：按名字/描述符定位方法，报告重载签名；
- **调用关系与交叉引用**：谁调用了某方法、某字符串被谁引用；
- **字符串常量**：API key 形态的字符串、遥测 URL 等常量的定位与出处；
- **资源出处**：资源 ID 到声明文件/值的追溯；
- **multidex 信息**：DEX 文件计数与分布；
- **不可回答判定**：当问题所问的东西在样本中不存在时（例如「某个没有 receiver 的组件被谁接收」），给出「无证据」的明确结论，而不是编造一个答案；
- **部分失败闭合**：当某个后端缺失或失败时，报告如实写明哪个后端没有参与分析、为什么，而不是沉默或补造数据。

### 1.2 不做什么（明确边界）

- **不替代动态分析**：不做运行时行为验证、脱壳、frida/hook、流量分析；
- **不做渗透测试或漏洞发现的承诺**：能定位符号与引用，不保证发现可利用漏洞；
- **不做恶意软件定性**；
- **不承诺加固/加壳样本的通用还原**：混淆样本上的能力仅指 first-party 测试样本中已实测的具体题类，不外推到商业加固方案；
- **不做反混淆的通用承诺**：对混淆代码的可读性改进是后端与 agent 检索能力的自然结果，不是服务承诺；
- **模型输出是线索**：任何 AI 参与的结论都以证据记录为准，无证据的断言在报告中不成立。

### 1 节证据

- [roadmap/phase3-plan.md](roadmap/phase3-plan.md) §1.1 —— 服务定位与三类交付方向；
- [analysis-provenance.md](analysis-provenance.md) —— 三个后端各产出什么、来自哪里；
- [../README.md](../README.md) —— 工具总览与快速上手。

## 2. 已验证的服务能力（2026-11-16 实测；2026-11-21 以 GLM-5.3-Flash 复测同一题集）

以下能力在**冻结的 20 题服务回归集**上用真实模型单轮实测验证。题集、判定标准与冻结纪律见 [service-regression-set.md](benchmarks/service-regression-set.md)；完整实测报告见 [m6-level2-retest2.md](benchmarks/m6-level2-retest2.md)（MiniMax-M3.1-Flash）与 [m6-level2-glm.md](benchmarks/m6-level2-glm.md)（GLM-5.3-Flash 三轮，2026-11-21）。

### 2.1 总体结果

| 配置 | MiniMax 单轮（2026-11-16） | GLM 三轮合计（2026-11-21） | 说明 |
|---|---:|---:|---|
| DexAtlas | **16/20（80.0%）** | **51/60（85.0%；逐轮均 17/20）** | agent 配置，带证据工具链 |
| 对照 A | 7/20 | 9/20（30.0%） | 纯模型 + 基础工具 |
| 对照 B | 7/20 | 7/20（35.0%） | 纯模型 + 检索工具 |

- MiniMax 单轮：证据 grounding 率 **97.7%**，无依据断言率 **2.3%**，工具调用成功率 **99.4%**，trace 合计 **355,623 tokens**（完整表见 [m6-level2-retest2.md](benchmarks/m6-level2-retest2.md)）。
- GLM 三轮：证据 grounding 率 **90.9%→97.5%**（逐轮），无依据断言率 **9.1%→2.5%**，工具调用成功率 **≥98.2%**，trace 合计 **949,093 tokens**（完整表见 [m6-level2-glm.md](benchmarks/m6-level2-glm.md)）。
- 判分客观可复算：`must_contain` / `expect_count` / `expect_empty` / `expect_backend_failure` 全部机器判定，trace 已提交，报告可逐字节重算。

### 2.2 按题类的能力现状

**已由本轮实测通过（可列入服务范围）：**

- manifest 包名与权限名串（demo / strings 样本）；
- exported 组件清单（demo / obfuscated 样本）；
- 指定方法定位与重载签名（crypto-sign）；
- 调用关系（caller）判定；
- 字符串常量：API key 形态字符串与混淆样本中的遥测 URL（本轮经检索兜底修复后转正）；
- 资源出处追溯；
- multidex DEX 文件计数；
- 后端缺失闭合：`no-jadx` 配置下如实报告 JADX 未参与（补跑通过）；
- 无证据判定：demo 样本「声明即全部」类问题。

**仍未通过、暂不列入承诺范围（上轮失败清单遗留）：**

- **descriptor 区分**（`overloads.method-identity.descriptor-distinguishes`）：同名方法按完整 JVM 描述符枚举区分，本轮回答与判定要求仍有差距；
- **no-receiver 判定**（`unanswerable.demo-declares-no-receiver`）：对「不存在 receiver」的否定性结论的作答形态未达判定标准；
- **no-apktool 闭合**（`partial.no-apktool-there-is-no-manifest`）：Apktool 缺失时对「无 manifest」的闭合表述未达判定标准；
- **混淆权限计数**（`manifest.permission.count-obfuscated`）：上轮通过、本轮未过，属单轮波动还是回归待复测确认（见 [m6-level2-retest2.md](benchmarks/m6-level2-retest2.md) 逐题对照）。

### 2.3 一项重要的行为指标

对层级 2 全部 183 条 trace 的失败模式分析（[m6-level2-failure-analysis.md](benchmarks/m6-level2-failure-analysis.md)）显示：三配置 `must_not_contain` 违例均为 **0**——即在被明确禁止编造的题目上，没有任何一次编造被禁事实。失败集中表现为「答不出/答不满」，而非「答错还自信」。这是 evidence-first 纪律在实测中的直接体现。

### 2 节证据

- [benchmarks/m6-level2-retest2.md](benchmarks/m6-level2-retest2.md) —— 本轮全部数字与逐题对照；
- [benchmarks/m6-level2-retest2-traces.json](benchmarks/m6-level2-retest2-traces.json) —— 60 条原始 trace；
- [benchmarks/service-regression-set.md](benchmarks/service-regression-set.md) —— 冻结题集与判定标准；
- [benchmarks/m6-level2-failure-analysis.md](benchmarks/m6-level2-failure-analysis.md) —— 183 条 trace 的失败归因。

## 3. 验收与质量纪律

### 3.1 验收线

服务回归集的验收线（[service-regression-set.md](benchmarks/service-regression-set.md) §5）：**每轮 ≥80%，三轮合计 ≥90%**（空答与预算耗尽计失败；不得删题换通过率）。当前状态：**三套三轮完整测量均已跑完**——历史 MiniMax 基线 49/60 = 81.7%（逐轮 15/16/18），GLM-5.3-Flash 53/60 = 88.3%（逐轮 17/18/18），2026-11-22 的 DeepSeek-V4.1-Flash **56/60 = 93.3%（逐轮 18/20/18）——单轮线（≥80%）与三轮合计线（≥90%）均达成，B1 验收线关闭**。同一套产品修复在三个模型上成绩递增（81.7% → 88.3% → 93.3%），修复有效性得到跨模型验证；三模型成绩分开陈述，不并表、不混排。

### 3.2 质量纪律（对客户可核查）

- **红→绿回归纪律**：每个 bug 修复必须携带一个在旧实现上会失败的回归测试；修复被拿掉时测试必须变红。仓库规则见 [../CLAUDE.md](../CLAUDE.md)。
- **报告数字脚本生成**：评测报告的每一个数字都由脚本从提交的 trace 重算（如 `scripts/m6_level2_retest2_report.py`），重跑应得到逐字节相同的结果；任何人不得手改数字。
- **判定客观**：通过/失败由 `benchmarks/model.py::check` 机器判定，不依赖人工打分。
- **证据可追溯**：报告中的事实断言附 `file:line` 级出处，`scripts/check-doc-citations.py` 在 CI 中核验这些引用未随代码漂移。

### 3.3 已知局限（照实声明，口径同 [m6-level2-retest2.md](benchmarks/m6-level2-retest2.md) §5）

- **单轮单模型**：本轮为 temperature 0 下 MiniMax-M3.1-Flash 的单轮结果；同一模型两次运行仍可能不同，本轮数字不外推为该配置的稳定通过率；
- **first-party 小样本**：20 题全部落在 `examples/` 的五个 first-party 小型 APK 上，不外推到真实规模或加固样本；
- **token 来自端点回报**：token 数字取自 API `usage` 字段，未用本地 tokenizer 复核；
- **熔断与补跑**：首轮 18 题后触发 300,000 token 总额熔断，最后 2 题经追加授权补跑完成；两段测量在同一代码、同一模型、同一题集上进行，合并后为完整的 20 题单轮测量，过程在报告中照实记录；
- **A/B 与 DexAtlas 预算不同**：配置间数字差异反映可见信息与执行条件不同，不构成优劣结论。

### 3 节证据

- [benchmarks/service-regression-set.md](benchmarks/service-regression-set.md) §5 —— 验收线与冻结纪律；
- [benchmarks/m6-level2-retest2.md](benchmarks/m6-level2-retest2.md) §4–§5 —— 验收结论与已知局限原文；
- [../CLAUDE.md](../CLAUDE.md) —— 回归测试与报告数字纪律；
- [status.md](status.md) —— 里程碑当前状态。

## 4. 服务边界与升级路径

### 4.1 遇到超范围样本时会发生什么

当样本超出已验证范围（加固样本、真实规模应用、问题落在失败清单题类）时，DexAtlas 的行为是**如实降级，不是硬答**：

- 后端失败或缺失时，报告写明该后端 `failed` / `partial` 及原因，已完成的步骤照常交付——一个 APK 即使彻底击败 JADX，仍会得到 manifest、索引与报告，报告说明哪些步骤没有运行；
- 问题无法从证据回答时，结论是「无证据/不可回答」，而不是一个看似合理的编造；
- **不编造结论**是判分与设计的双重红线：183 条 trace 中被禁事实的编造违例为 0（见 §2.3）。

### 4.2 失败的处理流程（分析 → 修复 → 复测）

失败不是被掩盖的噪声，而是被归因和修复的对象。已跑通的流程：

1. **失败模式分析**：对全部 trace 做逐题归因，把失败归入可命名的模式（[m6-level2-failure-analysis.md](benchmarks/m6-level2-failure-analysis.md) 归纳出四类：否定题作答形态、计数题判分形状、枚举不完整、检索词不命中）；
2. **根因修复**：按模式做 prompt/工具层修复，每项修复带回归测试（五项根因修复 `294853a`..`c770285`：检索兜底、整字面量契约、枚举完整性、partial 豁免、no_manifest 闭合）；
3. **复测验证**：修复后在同一冻结集上复测，逐题对照修复效果（[m6-level2-retest2.md](benchmarks/m6-level2-retest2.md)：字符串两题转正、partial.no-jadx 补跑通过）；
4. **范围重述**：若某题类短期无法达标，按冻结纪律**缩小并重述**服务承诺，而不是把失败题移出题集宣布通过（[service-regression-set.md](benchmarks/service-regression-set.md) §5）。

### 4.3 对客户的含义

- 交付物自带「哪里测过、哪里没测」的边界说明，不会把未验证能力包装成已验证；
- 超范围需求会先被识别并明确告知，双方在重述后的范围内验收；
- 每一轮实测的 trace、判分与报告都可提交核查，客户可以自己重跑判定。

### 4 节证据

- [benchmarks/m6-level2-failure-analysis.md](benchmarks/m6-level2-failure-analysis.md) —— 失败模式归因方法与结论；
- [benchmarks/m6-level2-retest2.md](benchmarks/m6-level2-retest2.md) —— 修复后复测的逐题对照；
- [benchmarks/service-regression-set.md](benchmarks/service-regression-set.md) §5 —— 冻结纪律与「缩小并重述」规则；
- [roadmap/phase3-plan.md](roadmap/phase3-plan.md) —— 服务定位与验收纪律总纲。

---

*本文由仓库维护者依据已提交的实测报告编写；数字如有更新，以最新提交的评测报告为准。*
