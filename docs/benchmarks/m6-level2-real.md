# M6 层级 2 —— 服务回归集真实模型批次（运行记录）

**状态：已完成授权范围内的执行并按授权停止。本文所有数字由`scripts/m6_level2_report.py` 从 [m6-level2-traces.json](m6-level2-traces.json) 重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。**

本文落实 [服务回归集](service-regression-set.md) §6 的**层级 2**：真实模型（MiniMax-M3.1-Flash，openai-compatible 端点）对冻结 20 题独立跑 3 轮，三配置（A 源码文本 / B 结构化检索 / DexAtlas agent）同题同模型。92 题完整旧题集全量轮**未执行**（原因见 §3 停止条件）。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-15 |
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与 service-regression-set.md §3 一致） |
| 轮次 | 冻结 20 题 × 3 轮 + 1 题冒烟；92 题全量未跑 |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（M6-② 新默认预算） |
| 每任务 token 预算 | DexAtlas 120000（A/B 检索式，无任务级循环预算） |
| 迭代 / 步数 / 时限 | 16 迭代 / 40 步 / 600 秒 |
| 采样 | temperature 0（provider 默认） |

预算对齐说明：DexAtlas 的 120000/16/40 是 M6-② 定稿的 agent 新默认预算；A/B 保持与 [comparison-stronger.md](comparison-stronger.md) 相同的 16384 每请求预算。逐配置预算不同，因此配置间差异同时反映执行条件与可见信息，不构成对模型质量的比较。

## 2. 结果总览

| 配置 | r1 正确 | r2 正确 | r3 正确 | 三轮合计 | 三轮合计正确率 | 三轮 token | 三轮耗时(s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 8/20 | 8/20 | 8/20 | 24/60 | 40.0% | 95573 | 220.9 |
| B | 6/20 | 6/20 | 6/20 | 18/60 | 30.0% | 45913 | 145.0 |
| DexAtlas | 9/20 | 8/20 | 7/20 | 24/60 | 40.0% | 711617 | 812.0 |

- 全部 trace 合计 token：**853103**（冒烟 7,187 + 三轮回归）。
- DexAtlas 证据溯源率（evidence_grounding_rate）三轮为 94.1% / 85.7% / 85.4%；A/B 为 0%（其回答按设计不带证据引用）。
- 空答：0；预算耗尽判分失败：0；基础设施性失败：1（第 3 轮 DexAtlas 1 题，计入该轮失败，未重试——重试会改变已记录的测量）。
- 冒烟验证（1 题 × 3 配置）：全部判分通过，用于确认端点、key 注入与 trace 记账可用。

## 逐轮八指标（由 trace 经 `benchmarks.comparison.metrics.compare` 重算）

### round-1

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 40.0% | 30.0% | 45.0% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 94.1% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 5.9% |
| `false_positive_rate` | 36.4% | 54.5% | 47.1% |
| `tool_call_success_rate` | 100.0% | 100.0% | 100.0% |
| `recovery_rate` | n/a | n/a | n/a |
| `token_consumption` | 32669 | 14688 | 249853 |
| `execution_duration` | 80.704 | 42.031 | 209.859 |

### round-2

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 40.0% | 30.0% | 40.0% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 85.7% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 14.3% |
| `false_positive_rate` | 40.0% | 58.3% | 55.1% |
| `tool_call_success_rate` | 100.0% | 100.0% | 100.0% |
| `recovery_rate` | n/a | n/a | n/a |
| `token_consumption` | 33687 | 15411 | 214194 |
| `execution_duration` | 80.407 | 49.391 | 217.859 |

### round-3

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 40.0% | 30.0% | 35.0% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 85.4% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 14.6% |
| `false_positive_rate` | 33.3% | 54.5% | 50.0% |
| `tool_call_success_rate` | 100.0% | 100.0% | 100.0% |
| `recovery_rate` | n/a | n/a | 0.0% |
| `token_consumption` | 29217 | 15814 | 247570 |
| `execution_duration` | 59.812 | 53.532 | 384.297 |

## 逐题结果（20 题冻结集，三轮 × 三配置）

correct = 判分通过；wrong = 判分不通过；empty/errored/budget-exhausted 含义与层级 1 报告一致。单元格按轮次排列。

- `manifest.package.demo`（demo-app，manifest）：A: correct/correct/correct；B: correct/correct/correct；DexAtlas: correct/correct/correct
- `manifest.permission.name-strings`（strings-app，manifest）：A: correct/correct/correct；B: correct/correct/correct；DexAtlas: correct/correct/correct
- `manifest.permission.count-obfuscated`（obfuscated-app，manifest）：A: wrong/wrong/wrong；B: wrong/wrong/wrong；DexAtlas: wrong/wrong/wrong
- `components.exported.demo`（demo-app，components）：A: correct/correct/correct；B: correct/correct/correct；DexAtlas: correct/correct/correct
- `components.exported.obfuscated`（obfuscated-app，components）：A: correct/correct/correct；B: correct/correct/correct；DexAtlas: correct/correct/correct
- `overloads.method-identity.crypto-sign`（demo-app，overloads）：A: empty/empty/empty；B: correct/correct/correct；DexAtlas: wrong/correct/errored
- `overloads.method-identity.descriptor-distinguishes`（demo-app，overloads）：A: empty/empty/empty；B: empty/empty/empty；DexAtlas: wrong/wrong/wrong
- `ambiguity.declared-type-contradicts-body`（demo-app，ambiguity）：A: empty/empty/empty；B: wrong/wrong/empty；DexAtlas: wrong/wrong/wrong
- `xrefs.crypto-sign-callers`（demo-app，xrefs）：A: empty/empty/empty；B: empty/empty/empty；DexAtlas: correct/correct/correct
- `xrefs.handler-handle-callers`（wide-app，xrefs）：A: empty/empty/empty；B: empty/empty/empty；DexAtlas: correct/correct/wrong
- `xrefs.crypto-sign-call-site-count`（demo-app，xrefs）：A: empty/empty/empty；B: empty/empty/empty；DexAtlas: correct/wrong/correct
- `strings.api-key.demo`（demo-app，strings）：A: wrong/wrong/empty；B: empty/wrong/wrong；DexAtlas: wrong/wrong/wrong
- `strings.telemetry-url.obfuscated`（obfuscated-app，strings）：A: empty/empty/empty；B: empty/empty/empty；DexAtlas: correct/wrong/wrong
- `resources.app-name.demo`（demo-app，strings）：A: correct/correct/correct；B: wrong/wrong/wrong；DexAtlas: correct/correct/correct
- `wheresource.app-name-resource-file.demo`（demo-app，where-source）：A: correct/correct/correct；B: empty/empty/empty；DexAtlas: wrong/wrong/wrong
- `unanswerable.crypto-digestof-has-no-callers`（demo-app，unanswerable）：A: correct/correct/correct；B: correct/correct/correct；DexAtlas: wrong/wrong/wrong
- `unanswerable.demo-declares-no-receiver`（demo-app，unanswerable）：A: wrong/wrong/wrong；B: wrong/wrong/wrong；DexAtlas: wrong/wrong/wrong
- `partial.no-apktool-there-is-no-manifest`（demo-app，partial）：A: correct/correct/correct；B: wrong/wrong/wrong；DexAtlas: wrong/wrong/wrong
- `partial.no-jadx-the-failure-is-recorded`（demo-app，partial）：A: empty/empty/empty；B: empty/empty/empty；DexAtlas: wrong/wrong/wrong
- `multidex.dex-file-count`（multidex-app，multidex）：A: wrong/wrong/wrong；B: wrong/wrong/wrong；DexAtlas: wrong/wrong/wrong

## 失败构成（三轮合并，按配置）

- A：36 个失败 trace（20 题 × 3 轮 − 通过数），构成：empty 25, wrong 11。
- B：42 个失败 trace（20 题 × 3 轮 − 通过数），构成：empty 23, wrong 19。
- DexAtlas：36 个失败 trace（20 题 × 3 轮 − 通过数），构成：errored 1, wrong 35。

DexAtlas 三轮共同的失败题（每轮都错）：`ambiguity.declared-type-contradicts-body`、`manifest.permission.count-obfuscated`、`multidex.dex-file-count`、`overloads.method-identity.crypto-sign`、`overloads.method-identity.descriptor-distinguishes`、`partial.no-apktool-there-is-no-manifest`、`partial.no-jadx-the-failure-is-recorded`、`strings.api-key.demo`、`unanswerable.crypto-digestof-has-no-callers`、`unanswerable.demo-declares-no-receiver`、`wheresource.app-name-resource-file.demo`（11 题）。判定原因由 `benchmarks.model.check` 重算得出，见 trace；模式集中在：expect_count 题返回了多余证据（如权限计数把组件清单一起列出）、expect_empty 题给出了带证据的叙述性回答、must_contain 题的答案没有以要求的精确形式（完整方法签名、资源路径、失败标记）落入 findings。

## 3. 停止条件与成本

- 三轮回归实测 token 合计 **853103**（API `usage` 字段逐 trace 加总），已超过本次授权的 800000 tokens 上限 53103 tokens；其中 DexAtlas 配置 711617 tokens（约 83%）。
- 92 题全量轮未执行：按三轮实测比例外推（92/20 × 每轮约 28.4 万 tokens ≈ 每次全量 130 万+ tokens，DexAtlas 单配置占绝对大头），远超剩余授权额度。该决定由主会话确认（2026-11-15）。
- 单题未出现超过任务预算（120000 tokens）的情况；最大单题消耗见 trace。
- 模型 API 未出现限流或中断，无重试成本。

## 4. 与既有测量的关系

- [层级 0](service-regression-set.md)（无模型确定性判分）：20/20 通过，证明题集 machinery 与判定标准本身可用。
- [层级 1](m6-level1-scripted.md)（scripted 演练）：同一 harness 在冻结集上端到端可用；其数字度量 harness 机械，不是模型能力。
- [M3 真实模型 run](comparison-real.md)（92 题、每请求 4096）：DexAtlas correct_answer_rate 19.6%、token 1,192,451。本批次预算放宽到 120000/16/40 后，冻结 20 题上的正确率高于那次全量数字，但**两者题集不同（20 vs 92）、预算不同，不能当作同一测量的改进**。
- [M3 stronger run](comparison-stronger.md)（92 题、DexAtlas 每请求 16384）：DexAtlas 22.8%、token 15,150,070、61 题迭代耗尽。本批次把任务级预算提高到 120000 并沿用 16 迭代后，迭代耗尽从主要失败模式变为 0，说明更强的预算主要换来的是「把话说完」，不是「说对」。

## 5. 验收结论（照实陈述）

服务回归集验收线（service-regression-set.md §5）：每轮 ≥80%，三轮合计 ≥90%。本次实测：DexAtlas 每轮 45% / 40% / 35%，三轮合计 40%；A 40%，B 30%。**未通过，需继续修正或缩小服务承诺后重测。**本报告不声称优于任何基线；配置间数字差异反映可见信息与执行条件不同。

不可回答题（expect_empty，2 题）与后端缺失题（partial，2 题）的诚实处理：DexAtlas 在这 4 题上三轮全部判分失败——它给出了叙述性回答而非「无证据」判定，按 check() 规则带出任何证据即失败。这 8/8 的失败计入上述通过率，未剔除、未单独放宽。

## 6. 已知局限

- 样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。
- 20 题封闭集上的正确率不代表开放分析能力；三配置预算不同，配置对比是执行条件对比。
- 单模型（MiniMax-M3.1-Flash）、每配置每题 1 次（温度 0）；温度 0 下同一模型两次运行仍可能不同（comparison-real.md 已披露过该不可复现性），三轮DexAtlas 45/40/35% 的波动是同一测量条件下的实际波动。
- token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。

