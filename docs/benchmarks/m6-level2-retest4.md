# M6 层级 2 —— 服务回归集真实模型三轮完整重测（执行层修复后验收测量）

**状态：这是执行层修复成套落地后的三轮完整重测（B1 验收测量），按 [m6-level2-retest-plan.md](m6-level2-retest-plan.md) 的预算纪律执行；验收线来自 [service-regression-set.md](service-regression-set.md) §5 与 [phase3-plan.md](../roadmap/phase3-plan.md) §5 M6（每轮 ≥16/20，三轮合计 ≥54/60）。本文所有数字由 `scripts/m6_level2_retest4_report.py` 从 [m6-level2-retest4-traces-r1.json](m6-level2-retest4-traces-r1.json)、[m6-level2-retest4-traces-r2.json](m6-level2-retest4-traces-r2.json)、[m6-level2-retest4-traces-r3.json](m6-level2-retest4-traces-r3.json) 三个 trace 文件重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。任一轮 trace 缺失或不完整时本脚本拒绝生成报告。**

本文回答一个问题：执行层修复（limitations 判分、预算耗尽单列 outcome、端点故障重试、XML 泄漏容错）与 C2 单词并集兜底落地后，冻结 20 题服务回归集在真实模型（MiniMax-M3.1-Flash）上完整跑满三轮，DexAtlas 是否同时满足每轮 ≥80% 与三轮合计 ≥90% 的验收线。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-17 |
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测、前三轮复测同一题集、同一顺序） |
| 轮次 | 冻结 20 题 × 3 轮 × 3 配置 = 180 条 trace；三轮均为完整 20 题 |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与前几轮一致） |
| 每任务 token 预算 | DexAtlas 24,000（方案 §2.1 单题闸） |
| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |
| 总额熔断 | 三轮总授权 1,200,000 tokens |
| 代码状态 | `claude/m6-level2-verify` `f9d9fd8` |

三轮在同一代码（`claude/m6-level2-verify` `f9d9fd8`，含执行层修复成套与 C2 单词并集兜底）、同一模型、同一题集、同一配置下完成。

## 逐轮结果总览

| 轮次 | A | B | DexAtlas | 该轮 token 合计 |
|---|---:|---:|---:|---:|
| r1 | 7/20 | 7/20 | 15/20 | 395740 |
| r2 | 7/20 | 7/20 | 16/20 | 395542 |
| r3 | 7/20 | 7/20 | 18/20 | 391074 |

## 三轮合计

| 配置 | 三轮正确合计 | 正确率 |
|---|---:|---:|
| A | 21/60 | 35.0% |
| B | 21/60 | 35.0% |
| DexAtlas | 49/60 | 81.7% |

三轮全部 trace 合计 token：**1182356**（API `usage` 字段逐 trace 加总）。

## 八指标（三轮合并，由 180 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| correct_answer_rate | 35.0% | 35.0% | 81.7% |
| evidence_grounding_rate | 0.0% | 0.0% | 96.6% |
| unsupported_assertion_rate | 100.0% | 100.0% | 3.4% |
| false_positive_rate | 35.7% | 50.0% | 12.5% |
| tool_call_success_rate | 100.0% | 100.0% | 98.7% |
| recovery_rate | n/a | 0.0% | 55.6% |
| token_consumption | 91829 | 92422 | 998105 |
| execution_duration | 305.05 | 267.096 | 959.043 |

## 逐轮 × 逐题结果（冻结集顺序；每格为该配置三轮的判定，`r1/r2/r3`）

correct = 判分通过；wrong = 判分不通过；empty = 空答；errored = 运行错误；budget-exhausted = 任务级预算耗尽。**空答与预算耗尽均计为失败**（`passed` 判定与 `_outcome` 语义已保证这一点）。20 题完整分母，无 not-run。

| manifest.package.demo | correct/correct/correct | correct/correct/correct | correct/correct/correct |
| manifest.permission.name-strings | correct/correct/correct | correct/correct/correct | correct/correct/correct |
| manifest.permission.count-obfuscated | wrong/wrong/wrong | wrong/wrong/wrong | correct/correct/correct |
| components.exported.demo | correct/correct/correct | correct/correct/correct | correct/correct/correct |
| components.exported.obfuscated | correct/correct/correct | correct/correct/correct | correct/correct/correct |
| overloads.method-identity.crypto-sign | empty/empty/empty | correct/correct/correct | correct/correct/correct |
| overloads.method-identity.descriptor-distinguishes | empty/empty/empty | empty/empty/empty | wrong/wrong/correct |
| ambiguity.declared-type-contradicts-body | empty/empty/empty | wrong/wrong/wrong | correct/correct/correct |
| xrefs.crypto-sign-callers | empty/empty/empty | empty/empty/empty | correct/correct/correct |
| xrefs.handler-handle-callers | wrong/empty/empty | empty/empty/empty | correct/correct/correct |
| xrefs.crypto-sign-call-site-count | empty/empty/empty | empty/empty/empty | correct/correct/correct |
| strings.api-key.demo | empty/empty/empty | wrong/wrong/wrong | empty/empty/budget-exhausted |
| strings.telemetry-url.obfuscated | empty/empty/empty | correct/correct/correct | correct/correct/correct |
| resources.app-name.demo | correct/correct/correct | wrong/wrong/wrong | correct/correct/correct |
| wheresource.app-name-resource-file.demo | correct/correct/correct | empty/empty/empty | correct/correct/correct |
| unanswerable.crypto-digestof-has-no-callers | correct/correct/correct | correct/correct/correct | correct/correct/correct |
| unanswerable.demo-declares-no-receiver | wrong/wrong/wrong | wrong/wrong/wrong | wrong/correct/correct |
| partial.no-apktool-there-is-no-manifest | empty/empty/empty | empty/empty/empty | wrong/wrong/correct |
| partial.no-jadx-the-failure-is-recorded | empty/empty/empty | empty/empty/empty | correct/correct/correct |
| multidex.dex-file-count | wrong/wrong/wrong | wrong/wrong/wrong | errored/errored/errored |

## 验收判定（对照 service-regression-set.md §5 与 phase3-plan.md §5 M6）

- 逐轮判定（DexAtlas）：r1 15/20 = 75.0%（未达 ≥16/20）；r2 16/20 = 80.0%（达到 ≥16/20）；r3 18/20 = 90.0%（达到 ≥16/20）。
- 三轮合计判定：DexAtlas 49/60 = 81.7%，未达 ≥54/60（≥90%）。

**总结论：未达标。** 存在未达 ≥16/20 的轮次； 三轮合计未达 ≥54/60；按冻结纪律（service-regression-set.md §5）只能修正系统或缩小并重述服务承诺后重测，不得删题换通过率。

对照参考（同轮 A/B，不构成优劣结论）：

| 配置 | r1 | r2 | r3 | 三轮合计 |
|---|---:|---:|---:|---:|
| A | 7/20 | 7/20 | 7/20 | 21/60 |
| B | 7/20 | 7/20 | 7/20 | 21/60 |

A/B 与 DexAtlas 的预算不同（每请求 max_tokens 16384 对 120000、任务预算仅 DexAtlas 24,000），配置间数字差异反映可见信息与执行条件不同，不构成优劣结论。

## 3. 成本与停止条件（照实陈述）

- 三轮实测 token 合计 **1182356**（三轮分别为 r1 395740、r2 395542、r3 391074），在三轮总授权 1,200,000 之内（余 17644）。
- 每任务 token 闸 24,000（`--total-tokens 24000`）按方案启用；判分失败与空答不重跑，预算耗尽如实按 `budget-exhausted` 计。
- 三轮均跑满 20 题，无熔断中止、无 not-run 题目。

## 已知局限

- **单模型**：全部测量来自 MiniMax-M3.1-Flash 一个模型，不外推到其他模型。
- **温度 0**：采样温度为 0，但同一模型多次运行仍可能不同；三轮合计数字不外推为该配置的稳定通过率。
- **first-party 小样本**：样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。
- **预算不对等**：A/B 与 DexAtlas 的每请求 max_tokens 与任务预算不同，配置间数字差异不构成优劣结论。
- **token 口径**：token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。

## 复现命令

```bash
# key 经环境变量注入，不写入任何文件
export MINIMAX_API_KEY="<key>"
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
# 逐题执行，每题一次调用，批间核对累计 token：
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat --api-key-env MINIMAX_API_KEY \
  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \
  --budget 16384 --agent-budget 120000 --total-tokens 24000 \
  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \
  --output .scratch/m6-retest-verify/full-rerun/r1/<task-id> --task <task-id>
# round2、round3 同式，仅 --output 目录不同：
#   .scratch/m6-retest-verify/full-rerun/r2/<task-id>
#   .scratch/m6-retest-verify/full-rerun/r3/<task-id>
# 报告再生：
uv run --no-sync python scripts/m6_level2_retest4_report.py
```
