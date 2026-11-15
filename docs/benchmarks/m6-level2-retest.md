# M6 层级 2 —— 服务回归集真实模型复测（单轮，M6-③ 修复后）

**状态：已完成授权范围内的执行并按授权停止（单轮，预算上限 350000 tokens）。本文所有数字由 `scripts/m6_level2_retest_report.py` 从 [m6-level2-retest-traces.json](m6-level2-retest-traces.json) 重算生成，未手改任何数字；重跑脚本应得到逐字节相同的文件。对照基线为 [m6-level2-real.md](m6-level2-real.md)（首测三轮，其 trace 文件未改动）。**

本文回答一个问题：M6-③ 五项修复（`1a1509c` 回答契约与工具调优、`b956260` partial.* 判定谓词，见 [m6-level3-recheck.md](m6-level3-recheck.md)）之后，冻结 20 题服务回归集在真实模型（MiniMax-M3.1-Flash）单轮上的表现，相比首测是否改善；以及是否达到验收线。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-16 |
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 冻结集 | `benchmarks/m6_service_set.py` 的 20 题（与首测同一题集、同一顺序） |
| 轮次 | 冻结 20 题 × 1 轮 × 3 配置（无冒烟：首测已验证端点与记账） |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与首测一致） |
| 每任务 token 预算 | DexAtlas 120000（A/B 检索式，无任务级循环预算） |
| 迭代 / 步数 / 时限 | 16 迭代 / 40 步 / 600 秒（与首测一致） |
| 代码状态 | main 合并树，M6-③ 修复已入库（`1a1509c`、`b956260`） |
| 采样 | temperature 0（provider 默认） |

与首测的执行条件差异：首测在修复前的代码上跑（合并 `1a1509c` 之前），本轮在 M6-③ 修复后的代码上跑。A/B 的提示词与检索策略未改，其差异应视为同一测量下的模型波动；DexAtlas 的差异才是修复效果的测量。

## 2. 结果总览

| 配置 | 复测正确 | 首测 r1 正确 | 三轮首测合计 | 复测 token | 复测耗时(s) |
|---|---:|---:|---:|---:|---:|
| A | 7/20 | 8/20 | 8/60 | 31574 | 123.9 |
| B | 6/20 | 6/20 | 6/60 | 14980 | 46.3 |
| DexAtlas | 15/20 | 9/20 | 9/60 | 310249 | 270.8 |

- 全部 trace 合计 token：**356803**（API `usage` 字段逐 trace 加总）。
- 结果构成：budget-exhausted 1, correct 28, empty 18, no-answer 2, wrong 11。

### DexAtlas 失败题明细

- `strings.api-key.demo`：回答为空。
- `strings.telemetry-url.obfuscated`：判分不通过（回答内容与判定要求有差距）。
- `overloads.method-identity.descriptor-distinguishes`：判分不通过（回答内容与判定要求有差距）。
- `partial.no-jadx-the-failure-is-recorded`：回答为空。
- `partial.no-apktool-there-is-no-manifest`：任务级预算/迭代耗尽，未作答。

- A/B 的 empty 是检索式配置对 evidence-only 判分题的固有形态（与首测一致）；其 wrong 多为 `must_contain` 部分命中或计数不符。

## 八指标（由 trace 经 `benchmarks.comparison.metrics.compare` 重算）

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 35.0% | 30.0% | 75.0% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 100.0% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 0.0% |
| `false_positive_rate` | 33.3% | 54.5% | 7.7% |
| `tool_call_success_rate` | 100.0% | 100.0% | 99.3% |
| `recovery_rate` | n/a | n/a | 0.0% |
| `token_consumption` | 31574 | 14980 | 310249 |
| `execution_duration` | 123.922 | 46.281 | 270.828 |

## 逐题结果（20 题冻结集，单轮 × 三配置，附首测 round-1 对照）

correct = 判分通过；wrong = 判分不通过；empty/errored/budget-exhausted 含义与层级 2 报告一致。每格为 `复测/首测r1`。

- `manifest.package.demo`（demo-app，manifest）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `manifest.permission.name-strings`（strings-app，manifest）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `manifest.permission.count-obfuscated`（obfuscated-app，manifest）：A: wrong/wrong；B: wrong/wrong；DexAtlas: correct/wrong
- `components.exported.demo`（demo-app，components）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `components.exported.obfuscated`（obfuscated-app，components）：A: correct/correct；B: correct/correct；DexAtlas: correct/correct
- `overloads.method-identity.crypto-sign`（demo-app，overloads）：A: empty/empty；B: correct/correct；DexAtlas: correct/wrong
- `overloads.method-identity.descriptor-distinguishes`（demo-app，overloads）：A: empty/empty；B: empty/empty；DexAtlas: wrong/wrong
- `ambiguity.declared-type-contradicts-body`（demo-app，ambiguity）：A: empty/empty；B: wrong/wrong；DexAtlas: correct/wrong
- `xrefs.crypto-sign-callers`（demo-app，xrefs）：A: empty/empty；B: empty/empty；DexAtlas: correct/correct
- `xrefs.handler-handle-callers`（wide-app，xrefs）：A: empty/empty；B: empty/empty；DexAtlas: correct/correct
- `xrefs.crypto-sign-call-site-count`（demo-app，xrefs）：A: empty/empty；B: empty/empty；DexAtlas: correct/correct
- `strings.api-key.demo`（demo-app，strings）：A: empty/wrong；B: wrong/empty；DexAtlas: no-answer/wrong
- `strings.telemetry-url.obfuscated`（obfuscated-app，strings）：A: empty/empty；B: empty/empty；DexAtlas: wrong/correct
- `resources.app-name.demo`（demo-app，strings）：A: correct/correct；B: wrong/wrong；DexAtlas: correct/correct
- `wheresource.app-name-resource-file.demo`（demo-app，where-source）：A: correct/correct；B: empty/empty；DexAtlas: correct/wrong
- `unanswerable.crypto-digestof-has-no-callers`（demo-app，unanswerable）：A: correct/correct；B: correct/correct；DexAtlas: correct/wrong
- `unanswerable.demo-declares-no-receiver`（demo-app，unanswerable）：A: wrong/wrong；B: wrong/wrong；DexAtlas: correct/wrong
- `partial.no-apktool-there-is-no-manifest`（demo-app，partial）：A: empty/correct；B: empty/wrong；DexAtlas: budget-exhausted/wrong
- `partial.no-jadx-the-failure-is-recorded`（demo-app，partial）：A: empty/empty；B: empty/empty；DexAtlas: no-answer/wrong
- `multidex.dex-file-count`（multidex-app，multidex）：A: wrong/wrong；B: wrong/wrong；DexAtlas: correct/wrong

## 修复针对的失败模式（M6-③ 分析归因）复测对照

| 失败模式 | 配置 | 首测 r1 | 复测 | 变化 |
|---|---|---:|---:|---:|
| 否定/缺席题（expect_empty + partial 后端缺失） | A | 2/4 | 1/4 | -1 |
| 否定/缺席题（expect_empty + partial 后端缺失） | B | 1/4 | 1/4 | 0 |
| 否定/缺席题（expect_empty + partial 后端缺失） | DexAtlas | 0/4 | 2/4 | +2 |
| 计数题（expect_count） | A | 0/3 | 0/3 | 0 |
| 计数题（expect_count） | B | 0/3 | 0/3 | 0 |
| 计数题（expect_count） | DexAtlas | 1/3 | 3/3 | +2 |
| 方法身份/枚举完整性（must_contain 描述符） | A | 0/3 | 0/3 | 0 |
| 方法身份/枚举完整性（must_contain 描述符） | B | 1/3 | 1/3 | 0 |
| 方法身份/枚举完整性（must_contain 描述符） | DexAtlas | 0/3 | 2/3 | +2 |
| 资源出处（资源 → 声明文件反查） | A | 2/4 | 2/4 | 0 |
| 资源出处（资源 → 声明文件反查） | B | 0/4 | 0/4 | 0 |
| 资源出处（资源 → 声明文件反查） | DexAtlas | 2/4 | 2/4 | 0 |

失败模式对照的读法：修复针对的四类模式里，**计数题、方法身份枚举、否定题在 DexAtlas 上改善**，与 M6-③ 各项修复一一对应（计数逐项成条、完整 JVM 描述符、否定答案移入 limitations、partial 判定谓词与真实禁用 Analyze）；资源出处类持平（`wheresource` 题已通过，`strings`两题的检索词命中问题不在本批修复范围）。A/B 三类不变符合预期：其提示词与检索策略本批未改。

## 3. 成本与停止条件

- 本轮实测 token 合计 **356803**（含三配置），授权上限 350000，超出 6803（约 2%）。超限发生在运行结束后的核账环节发现：运行本身是单轮 20 题 × 3 配置的完整授权范围，未因追加轮次或题目超出授权；超出部分主要来自 DexAtlas 配置的长尾任务。按约定如实记录。
- 单轮设计本身即授权边界：未追加任何轮次或题目。

## 4. 验收结论（照实陈述）

服务回归集验收线（service-regression-set.md §5）：每轮 ≥80%（20 题即 ≥16 题）。本轮实测：DexAtlas 15/20（75.0%）、A 7/20、B 6/20。**未达到验收线，需继续修正或缩小服务承诺后重测。**本报告不声称优于任何基线；A/B 与 DexAtlas 预算不同，配置间数字差异反映可见信息与执行条件不同。

## 5. 已知局限

- 单轮单模型，温度 0 下同一模型两次运行仍可能不同；本轮数字不外推为该配置的稳定通过率。
- 样本全部为 first-party 小型 APK（examples/ 五样本），不外推到真实规模或加固样本。
- token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。
- 对照的首测 r1 是修复前代码的测量；除代码状态外，两轮执行条件一致。
- 与首测三轮制不同，本轮为单轮：首测报告的「三轮合计」列（x/60）与本轮单轮数字（x/20）不可直接比较，逐题对照均以首测 round-1 为基线。

## 复现命令

```bash
# key 经环境变量注入，不写入任何文件
export MINIMAX_API_KEY="<key>"
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat \
  --base-url https://api.minimaxi.com/v1 \
  --model MiniMax-M3.1-Flash \
  --api-key-env MINIMAX_API_KEY \
  --budget 16384 --agent-budget 120000 --total-tokens 120000 \
  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \
  --output E:/Dexatlas/.scratch/m6-level2-retest/full \
  --task manifest.package.demo --task manifest.permission.name-strings \
  --task manifest.permission.count-obfuscated --task components.exported.demo \
  --task components.exported.obfuscated --task overloads.method-identity.crypto-sign \
  --task overloads.method-identity.descriptor-distinguishes \
  --task ambiguity.declared-type-contradicts-body --task xrefs.crypto-sign-callers \
  --task xrefs.handler-handle-callers --task xrefs.crypto-sign-call-site-count \
  --task strings.api-key.demo --task strings.telemetry-url.obfuscated \
  --task resources.app-name.demo --task wheresource.app-name-resource-file.demo \
  --task unanswerable.crypto-digestof-has-no-callers \
  --task unanswerable.demo-declares-no-receiver \
  --task partial.no-apktool-there-is-no-manifest \
  --task partial.no-jadx-the-failure-is-recorded --task multidex.dex-file-count

# 报告由 trace 重算生成
uv run --no-sync python scripts/m6_level2_retest_report.py
```

