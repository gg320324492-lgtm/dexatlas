# M6 层级 2 —— 服务回归集真实模型复测第二轮（单轮，根因修复后）

**状态：按 [m6-level2-retest-plan.md](m6-level2-retest-plan.md) 执行；首轮 18 题后触发 300,000 总额熔断；经用户追加授权（+50,000）补跑剩余 2 题（+46,983 tokens；最终累计越过原授权线 350,000 达 5,623，在追加后的总授权内）。本文所有数字由 `scripts/m6_level2_retest2_report.py` 从 [m6-level2-retest2-traces.json](m6-level2-retest2-traces.json) 重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。对照基线为 [m6-level2-retest.md](m6-level2-retest.md)（上轮复测，修复前树，15/20），其 trace 文件未改动。**

本文回答一个问题：五项根因修复（`294853a`..`c770285`，检索兜底、整字面量契约、枚举完整性、partial 豁免、no_manifest 闭合）之后，冻结 20 题服务回归集在真实模型（MiniMax-M3.1-Flash）单轮上的表现，相比上轮复测是否改善；以及是否达到验收线。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-16 |
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测、上轮同一题集、同一顺序） |
| 轮次 | 冻结 20 题 × 1 轮 × 3 配置；20 题全部发起（首轮 18 题 + 追加授权补跑 2 题） |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与上轮一致） |
| 每任务 token 预算 | DexAtlas 24000（本轮新增单题闸，方案 §2.1） |
| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |
| 总额熔断 | 累计 300,000 tokens；逐题批间核对（方案 §3） |
| 代码状态 | `claude/m6-level2-rootcause-fixes` 合并 main（`02d4b43`），五项根因修复已入库 |
| 采样 | temperature 0（provider 默认） |

与上轮的执行条件差异：上轮在 M6-③ 修复后的代码上跑；本轮在五项根因修复之后的代码上跑，并新增了单题 24,000 预算闸与 300,000 总额熔断（上轮仅有隐式 1,200,000 任务上限，等于无闸）。A/B 的提示词与检索策略未改。

## 2. 结果总览

| 配置 | 本轮正确 | 上轮正确 | 本轮 token | 本轮耗时(s) |
|---|---:|---:|---:|---:|
| A | 7/20 | 7/20 | 33683 | 79.3 |
| B | 7/20 | 6/20 | 19555 | 44.8 |
| DexAtlas | 16/20 | 15/20 | 302385 | 217.6 |

- 全部 trace 合计 token：**355623**（API `usage` 字段逐 trace 加总）。首轮 18 题累计 308,640 触发 300,000 控制线熔断；经用户追加授权（+50,000，总授权 400000）补跑最后 2 题（+46,983）。最终累计越过原授权线 350000 达 5623 tokens，在追加后的总授权 400000 之内（余 44377）；如实记录。
- 结果构成（20 题 × 3 配置 = 60 条 trace）：correct 30, empty 16, wrong 14。20 题完整分母，无 not-run。

### DexAtlas 失败题明细（20 题完整范围内）

- `manifest.permission.count-obfuscated`：判分不通过（回答内容与判定要求有差距）。
- `overloads.method-identity.descriptor-distinguishes`：判分不通过（回答内容与判定要求有差距）。
- `unanswerable.demo-declares-no-receiver`：判分不通过（回答内容与判定要求有差距）。
- `partial.no-apktool-there-is-no-manifest`：判分不通过（回答内容与判定要求有差距）。

上轮五个失败题中，`strings.api-key.demo` 与 `strings.telemetry-url.obfuscated` 本轮通过；`overloads.method-identity.descriptor-distinguishes`、`unanswerable.demo-declares-no-receiver`、`partial.no-apktool-there-is-no-manifest` 本轮仍未通过（形态见上）；`partial.no-jadx-the-failure-is-recorded` 补跑通过。

## 八指标（由 trace 经 `benchmarks.comparison.metrics.compare` 重算）

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 35.0% | 35.0% | 80.0% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 97.7% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 2.3% |
| `false_positive_rate` | 40.0% | 50.0% | 32.6% |
| `tool_call_success_rate` | 100.0% | 100.0% | 99.4% |
| `recovery_rate` | n/a | n/a | 100.0% |
| `token_consumption` | 33683 | 19555 | 302385 |
| `execution_duration` | 79.296 | 44.846 | 217.561 |

## 逐题结果（冻结集，单轮 × 三配置，附上轮复测对照）

correct = 判分通过；wrong = 判分不通过；empty/errored/budget-exhausted 含义与层级 2 报告一致；not-run = 总额熔断未发起。每格为 `本轮/上轮`。

- `manifest.package.demo`（demo-app，manifest）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `manifest.permission.name-strings`（strings-app，manifest）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `manifest.permission.count-obfuscated`（obfuscated-app，manifest）：A: wrong/wrong；B: wrong/wrong；DexAtlas: wrong/correct
- `components.exported.demo`（demo-app，components）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `components.exported.obfuscated`（obfuscated-app，components）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `overloads.method-identity.crypto-sign`（demo-app，overloads）：A: empty/empty；B: correct/correct；DexAtlas: correct/correct
- `overloads.method-identity.descriptor-distinguishes`（demo-app，overloads）：A: empty/empty；B: empty/empty；DexAtlas: wrong/wrong
- `ambiguity.declared-type-contradicts-body`（demo-app，ambiguity）：A: empty/empty；B: wrong/wrong；DexAtlas: correct/correct
- `xrefs.crypto-sign-callers`（demo-app，xrefs）：A: empty/empty；B: empty/empty；DexAtlas: correct/correct
- `xrefs.handler-handle-callers`（wide-app，xrefs）：A: empty/empty；B: empty/empty；DexAtlas: correct/correct
- `xrefs.crypto-sign-call-site-count`（demo-app，xrefs）：A: empty/empty；B: empty/empty；DexAtlas: correct/correct
- `strings.api-key.demo`（demo-app，strings）：A: wrong/empty；B: wrong/wrong；DexAtlas: correct/no-answer
- `strings.telemetry-url.obfuscated`（obfuscated-app，strings）：A: empty/empty；B: correct/empty；DexAtlas: correct/wrong
- `resources.app-name.demo`（demo-app，strings）：A: correct/correct；B: wrong/wrong；DexAtlas: correct/correct
- `wheresource.app-name-resource-file.demo`（demo-app，where-source）：A: correct/correct；B: empty/empty；DexAtlas: correct/correct
- `unanswerable.crypto-digestof-has-no-callers`（demo-app，unanswerable）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `unanswerable.demo-declares-no-receiver`（demo-app，unanswerable）：A: wrong/wrong；B: wrong/wrong；DexAtlas: wrong/correct
- `partial.no-apktool-there-is-no-manifest`（demo-app，partial）：A: empty/empty；B: empty/empty；DexAtlas: wrong/budget-exhausted
- `partial.no-jadx-the-failure-is-recorded`（demo-app，partial）：A: empty/empty；B: empty/empty；DexAtlas: correct/no-answer
- `multidex.dex-file-count`（multidex-app，multidex）：A: wrong/wrong；B: wrong/wrong；DexAtlas: correct/correct

## 五个修复题逐题变化（本轮 × 3 配置，附上轮对照）

| 题目 | 针对修复 | A | B | DexAtlas |
|---|---|---|---|---|
| `strings.api-key.demo` | 修复2 整字面量引用契约 | wrong/empty | wrong/wrong | correct/no-answer |
| `overloads.method-identity.descriptor-distinguishes` | 修复3 方法身份枚举完整性 | empty/empty | empty/empty | wrong/wrong |
| `partial.no-apktool-there-is-no-manifest` | 修复5 no_manifest 失败闭合读取 | empty/empty | empty/empty | wrong/budget-exhausted |
| `partial.no-jadx-the-failure-is-recorded` | 修复4/5 partial 过程记录豁免与闭合 | empty/empty | empty/empty | correct/no-answer |
| `unanswerable.crypto-digestof-has-no-callers` | 修复1 检索空后常量池枚举兜底 | correct/correct | correct/correct | correct/correct |

每格为 `本轮/上轮`。`not-run` 表示该题因总额熔断未发起（§3 停止条件），不是失败，也不得计为通过或失败。

## 3. 成本与停止条件（照实陈述）

- 本轮实测 token 合计 **355623**：首轮 18 题在累计 308,640 处越过方案总额控制线 300000 触发熔断；剩余 2 题（`partial.no-jadx-the-failure-is-recorded`、`multidex.dex-file-count`）经用户追加授权（+50,000）后补跑完成（+46,983）。最终累计越过原授权线 350000 达 5623 tokens，在追加后的总授权 400000 之内。20 题均为真实测量，无 not-run。
- 单题 24,000 闸本轮未触发任何一题（DexAtlas 单题最大 22489），上轮 71,718 的长尾未复现。上轮超支主因（失败题长尾空转）被单题闸与修复共同压住。

## 4. 验收结论（照实陈述）

服务回归集验收线（service-regression-set.md §5）：每轮 ≥80%（20 题即 ≥16 题）。本轮实测：DexAtlas 16/20（80.0%）、A 7/20、B 7/20。
- **DexAtlas 16/20 = 80.0%**，**达到验收线（≥16/20）**（A 7/20、B 7/20，均为 20 题完整分母）。
- 事实陈述：DexAtlas 20 题通过 16 题。上轮（修复前）DexAtlas 15/20 = 75.0%；本轮 16/20 = 80.0%，逐题对照见上表。A/B 与 DexAtlas 预算不同，配置间数字差异反映可见信息与执行条件不同，不构成优劣结论。

## 5. 已知局限

- **首轮在 18 题后触发总额熔断，最后 2 题由用户追加授权补跑完成**；两段测量在同一代码、同一模型、同一题集上进行，合并后为完整的 20 题单轮测量。
- 单轮单模型，温度 0 下同一模型两次运行仍可能不同；本轮数字不外推为该配置的稳定通过率。
- 样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。
- token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。
- 对照的上轮是修复前代码的测量；除代码状态与预算闸外，两轮执行条件一致。

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
  --output .scratch/m6-retest-r2/<task-id> --task <task-id>
# 报告再生：
uv run --no-sync python scripts/m6_level2_retest2_report.py
```
