# M6 层级 2 —— 服务回归集单轮验证复测（A+C2 修复验证）

**状态：这是 M6 层级 2 服务回归集的单轮验证复测，用于验证两项代码级修复的效果：A 类（`1a7add6`，模型端点返回空 assistant 消息被记为解题失败）与 C2（`192382f`，字符串检索诱饵遮蔽常量池枚举兜底），修复依据是 [m6-level2-retest3-failure-analysis.md](m6-level2-retest3-failure-analysis.md) 的失败模式分析。本文所有数字由 `scripts/m6_level2_verify_report.py` 从 [m6-level2-verify-traces.json](m6-level2-verify-traces.json) 与 [m6-level2-retest3-traces-r1.json](m6-level2-retest3-traces-r1.json) 重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。trace 缺失或不完整时本脚本拒绝生成报告。**

本文回答两个问题：r1 失败的三道题（`overloads.method-identity.descriptor-distinguishes`、`strings.api-key.demo`、`partial.no-apktool-there-is-no-manifest`）本轮是否通过；A 类空响应是否还出现。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-16 |
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测、三轮复测同一题集、同一顺序） |
| 轮次 | 冻结 20 题 × 1 轮 × 3 配置 = 60 条 trace |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与三轮复测一致） |
| 每任务 token 预算 | DexAtlas 24,000（方案 §2.1 单题闸） |
| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |
| 总额熔断 | 单轮累计 400,000 tokens（逐题批间核对累计 usage） |
| 代码状态 | `main` `fbca3d5`（含 A 类修复 `1a7add6` 与 C2 修复 `192382f`） |
| 采样 | temperature 0（provider 默认） |

本轮与三轮复测（`main` `c4922dc`）的差异只有两处代码修复（`1a7add6`、`192382f`）；模型、题集、配置、预算全部一致。单轮结果受模型方差影响，不外推为稳定通过率。

## 八指标（本轮 60 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 35.0% | 35.0% | 75.0% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 93.8% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 6.2% |
| `false_positive_rate` | 40.0% | 45.5% | 28.1% |
| `tool_call_success_rate` | 100.0% | 100.0% | 98.7% |
| `recovery_rate` | n/a | n/a | 33.3% |
| `token_consumption` | 30246 | 19035 | 310416 |
| `execution_duration` | 111.483 | 78.86 | 380.344 |

## 逐题结果（冻结集顺序；每题两格：本轮判定 / r1 判定）

correct = 判分通过；wrong = 判分不通过；empty = 空答；errored = 运行错误；budget-exhausted = 任务级预算耗尽。**空答与预算耗尽均计为失败**。20 题完整分母，无 not-run。

- `manifest.package.demo`（demo-app，manifest）：A: correct；B: correct；DexAtlas: correct ｜ r1：A: correct；B: correct；DexAtlas: correct
- `manifest.permission.name-strings`（strings-app，manifest）：A: correct；B: correct；DexAtlas: correct ｜ r1：A: correct；B: correct；DexAtlas: correct
- `manifest.permission.count-obfuscated`（obfuscated-app，manifest）：A: wrong；B: wrong；DexAtlas: wrong ｜ r1：A: wrong；B: wrong；DexAtlas: correct
- `components.exported.demo`（demo-app，components）：A: correct；B: correct；DexAtlas: correct ｜ r1：A: correct；B: correct；DexAtlas: correct
- `components.exported.obfuscated`（obfuscated-app，components）：A: correct；B: correct；DexAtlas: correct ｜ r1：A: correct；B: correct；DexAtlas: correct
- `overloads.method-identity.crypto-sign`（demo-app，overloads）：A: empty；B: correct；DexAtlas: correct ｜ r1：A: empty；B: correct；DexAtlas: correct
- `overloads.method-identity.descriptor-distinguishes`（demo-app，overloads） **← r1 失败题（修复目标）**：A: empty；B: empty；DexAtlas: correct ｜ r1：A: empty；B: empty；DexAtlas: wrong
- `ambiguity.declared-type-contradicts-body`（demo-app，ambiguity）：A: empty；B: wrong；DexAtlas: correct ｜ r1：A: empty；B: wrong；DexAtlas: correct
- `xrefs.crypto-sign-callers`（demo-app，xrefs）：A: empty；B: empty；DexAtlas: correct ｜ r1：A: empty；B: empty；DexAtlas: correct
- `xrefs.handler-handle-callers`（wide-app，xrefs）：A: wrong；B: empty；DexAtlas: correct ｜ r1：A: wrong；B: empty；DexAtlas: correct
- `xrefs.crypto-sign-call-site-count`（demo-app，xrefs）：A: empty；B: empty；DexAtlas: correct ｜ r1：A: empty；B: empty；DexAtlas: correct
- `strings.api-key.demo`（demo-app，strings） **← r1 失败题（修复目标）**：A: empty；B: empty；DexAtlas: no-answer ｜ r1：A: empty；B: wrong；DexAtlas: wrong
- `strings.telemetry-url.obfuscated`（obfuscated-app，strings）：A: empty；B: correct；DexAtlas: correct ｜ r1：A: empty；B: correct；DexAtlas: correct
- `resources.app-name.demo`（demo-app，strings）：A: correct；B: wrong；DexAtlas: budget-exhausted ｜ r1：A: correct；B: wrong；DexAtlas: correct
- `wheresource.app-name-resource-file.demo`（demo-app，where-source）：A: correct；B: empty；DexAtlas: correct ｜ r1：A: correct；B: empty；DexAtlas: correct
- `unanswerable.crypto-digestof-has-no-callers`（demo-app，unanswerable）：A: correct；B: correct；DexAtlas: correct ｜ r1：A: correct；B: correct；DexAtlas: correct
- `unanswerable.demo-declares-no-receiver`（demo-app，unanswerable）：A: wrong；B: wrong；DexAtlas: correct ｜ r1：A: wrong；B: correct；DexAtlas: correct
- `partial.no-apktool-there-is-no-manifest`（demo-app，partial） **← r1 失败题（修复目标）**：A: empty；B: empty；DexAtlas: wrong ｜ r1：A: empty；B: empty；DexAtlas: no-answer
- `partial.no-jadx-the-failure-is-recorded`（demo-app，partial）：A: empty；B: empty；DexAtlas: correct ｜ r1：A: empty；B: empty；DexAtlas: correct
- `multidex.dex-file-count`（multidex-app，multidex）：A: wrong；B: wrong；DexAtlas: budget-exhausted ｜ r1：A: wrong；B: wrong；DexAtlas: correct

## 修复验证（本轮要回答的两个问题）

### 1. r1 失败的三道题本轮是否通过（DexAtlas）

| task | r1 判定 | r1 结果摘要 | 本轮判定 | 本轮结果摘要 |
|---|---|---|---|---|
| `overloads.method-identity.descriptor-distinguishes` | wrong | answer did not meet the rubric | correct | passed |
| `strings.api-key.demo` | wrong | answer did not meet the rubric | no-answer | answer did not meet the rubric |
| `partial.no-apktool-there-is-no-manifest` | no-answer | answer did not meet the rubric | wrong | answer did not meet the rubric |

三道 r1 失败题本轮通过 **1/3**。

### 2. A 类空响应（模型端点返回空 assistant 消息）是否还出现

本轮 DexAtlas 出现 **1** 条 A 类空响应 trace（答案型题 failed 且无 error 且判分无 findings，即修复前的执行层空响应形态）：`strings.api-key.demo`。

判定口径：A 类空响应 = 该题正确答案不是「空」（`expects_absence` 为假）且 `result.failed` 为真且 `result.error` 为空且 `answer_is_empty` 为真（判分无 findings）——即修复前被记为解题失败的执行层空响应形态。四项均由 trace 字段直接读出，不经人工判断。`expects_absence` 的题（unanswerable 两题）空答即正确答案，其 failed+empty 形态是判分器对「答无所指」的记法，不是端点空响应，故排除；r1 同题同形态，非本轮新增。注意 MiniMax 端点对全部成功请求都回报 `completion_tokens=0`，该字段不区分空响应，不作判定依据。

## 结果判定（对照参考线，非验收）

本 run 是单轮验证，不是 B1 的验收测量；验收线（每轮 ≥16/20 且三轮合计 ≥54/60）属于三轮完整复测。这里只把本轮数字放在同一条参考线旁读：DexAtlas 本轮 15/20 = 75.0%（参考线 ≥16/20，本轮未到线）。

| 配置 | 本轮正确 | 正确率 | 本轮 token |
|---|---:|---:|---:|
| A | 7/20 | 35.0% | 30246 |
| B | 7/20 | 35.0% | 19035 |
| DexAtlas | 15/20 | 75.0% | 310416 |

本轮全部 trace 合计 token：**359697**（API `usage` 字段逐 trace 加总）。

A/B 与 DexAtlas 的预算不同（每请求 max_tokens 16384 对 120000、任务预算仅 DexAtlas 24,000），配置间数字差异反映可见信息与执行条件不同，不构成优劣结论。

## 成本与停止条件（照实陈述）

- 本轮实测 token 合计 **359697**，在单轮授权 400,000 之内（余 40303）。
- 单题 24,000 闸共触发 2 题（DexAtlas），均如实判 budget-exhausted 计失败；判分失败与空答未重跑。

## 已知局限

- **单轮**：单轮数字受模型方差影响大（三轮复测同题集同配置逐轮在 15–17/20 间波动），本轮数字不外推为稳定通过率，也不据此关闭或重开任何验收。
- **单模型**：全部测量来自 MiniMax-M3.1-Flash 一个模型，不外推到其他模型。
- **温度 0**：采样温度为 0，但同一模型多次运行仍可能不同。
- **first-party 小样本**：样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。
- **预算不对等**：A/B 与 DexAtlas 的每请求 max_tokens 与任务预算不同，配置间数字差异不构成优劣结论。
- **token 口径**：token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。

## 复现命令

```bash
# key 经环境变量注入，不写入任何文件
export MINIMAX_API_KEY="<key>"
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
# 逐题执行（方案 §4.3），每题一次调用，批间核对累计 token：
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat --api-key-env MINIMAX_API_KEY \
  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \
  --budget 16384 --agent-budget 120000 --total-tokens 24000 \
  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \
  --output .scratch/m6-retest-verify/<task-id> --task <task-id>
# 报告再生：
uv run --no-sync python scripts/m6_level2_verify_report.py
```
