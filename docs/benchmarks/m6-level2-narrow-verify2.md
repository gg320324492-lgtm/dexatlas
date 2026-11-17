# M6 层级 2 —— 修复后窄验证二轮（6 题 × 3 轮）

**状态：本 run 验证首轮窄验证（`m6-level2-narrow-verify-incomplete.md`）之后的四项修复（协议泄漏纠偏重试、partial 后端缺失措辞对齐、api-key 常量池检索引导、descriptor 连写模板）。代码状态 `claude/m6-level2-verify 9b25835`。本文所有数字由 `scripts/m6_level2_narrow_verify2_report.py` 从 [m6-level2-narrow-verify2-traces.json](m6-level2-narrow-verify2-traces.json) 重算生成，未手改任何数字；trace 缺失或不完整时本脚本拒绝生成报告。**

本文回答验收方案（§2.2）的两个问题：

1. 六道覆盖已知失败面的题，DexAtlas 三轮合计是否 ≥4 题转通过（≥12/18）；
2. 确定性修复直接相关的五题（除 descriptor 外）是否 ≥3 题转通过。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 题集 | 6 题（验收方案 §2.2，覆盖全部已知失败面） |
| 轮次 | 6 题 × 3 轮 × 3 配置 = 54 条 trace |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与三轮复测一致） |
| 每任务 token 预算 | DexAtlas 24,000（单题闸） |
| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |
| 总额熔断 | 累计 410,000 tokens（逐题批间核对累计 usage） |
| 代码状态 | `claude/m6-level2-verify 9b25835`（含四项修复：泄漏纠偏重试 / partial 措辞 / api-key 常量检索 / descriptor 连写） |
| 采样 | temperature 0（provider 默认） |

## 八指标（54 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 16.7% | 11.1% | 38.9% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 100.0% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 0.0% |
| `false_positive_rate` | 66.7% | 100.0% | 31.6% |
| `tool_call_success_rate` | 100.0% | 100.0% | 97.0% |
| `recovery_rate` | n/a | n/a | 33.3% |
| `token_consumption` | 24,215 | 46,654 | 349,957 |
| `execution_duration` | 105.1 | 114.5 | 327.7 |

## 逐题结果（DexAtlas；每轮一格：通过数（判定））

| task | 失败面 | r1 判定 | r2 判定 | r3 判定 | 3 轮合计 |
|---|---|---|---|---|---|
| `partial.no-apktool-there-is-no-manifest` | 判分通道（limitations） | 0/1（empty） | 1/1（correct） | 0/1（empty） | **1/3** |
| `strings.api-key.demo` | C2 触发条件（单词并集） | 0/1（budget-exhausted） | 0/1（budget-exhausted） | 0/1（budget-exhausted） | **0/3** |
| `overloads.method-identity.descriptor-distinguishes` | C1 回答宽度 | 0/1（wrong） | 0/1（wrong） | 0/1（wrong） | **0/3** |
| `manifest.permission.count-obfuscated` | C3 findings 纪律 | 1/1（correct） | 1/1（correct） | 1/1（correct） | **3/3** |
| `resources.app-name.demo` | B 单题预算 | 0/1（budget-exhausted） | 1/1（correct） | 1/1（correct） | **2/3** |
| `multidex.dex-file-count` | B 单题预算（近闸值） | 0/1（budget-exhausted） | 0/1（budget-exhausted） | 1/1（correct） | **1/3** |

## 判定分布（3 轮合计，每配置 18 条）

| 配置 | correct | wrong | empty | no-answer | budget-exhausted | errored |
|---|---:|---:|---:|---:|---:|---:|
| A | 3 | 6 | 9 | 0 | 0 | 0 |
| B | 2 | 11 | 5 | 0 | 0 | 0 |
| DexAtlas | 7 | 3 | 2 | 0 | 6 | 0 |

## 窄验证判定（验收方案 §2.2 的闸）

- 转通过题（DexAtlas，3 轮中 ≥2 轮判过）：**2/6**（`manifest.permission.count-obfuscated`、`resources.app-name.demo`）
- 确定性修复相关题转通过（partial、api-key、count、两道预算题）：**2/5**（`manifest.permission.count-obfuscated`、`resources.app-name.demo`）
- 判定：**未达到窄验证通过判据**（转通过 2/6，门槛 ≥4；确定性修复相关题 2/5，门槛 ≥3）。若转通过 ≤2/6，按验收方案停止投入，转方案 3（现状披露）；否则按失败模式再分析后决定。

## 修复验证关注点

- 单题 24,000 闸触发（DexAtlas）：**3 题**（`multidex.dex-file-count`、`resources.app-name.demo`、`strings.api-key.demo`），均如实判 budget-exhausted 计失败。
- XML 工具调用协议泄漏（retryable 处理）：**0 条**。
- 判分失败与空答未重跑；errored 的基础设施性失败按 service-regression-set §6 处置。

## 成本与停止条件（照实陈述）

- 本 run 实测 token 合计 **420,826**（API `usage` 字段逐 trace 加总），授权上限 410,000（已触发熔断，超出部分如实记录）。
- 逐题分批执行，批间核对累计 usage；单题 24,000 闸由 `--total-tokens 24000` 落实。

## 已知局限

- **窄题集**：6 题覆盖已知失败面，但通过率不能外推到 20 题完整服务回归集；
  进入完整三轮（B1 关闭测量）需另按验收方案 §3 的触发条件申请。
- **单模型**：全部测量来自 MiniMax-M3.1-Flash 一个模型，不外推到其他模型。
- **温度 0**：采样温度为 0，但同一模型多次运行仍可能不同。
- **first-party 小样本**：样本全部为 first-party 小型 APK（examples/），不外推到真实规模或加固样本。
- **预算不对等**：A/B 与 DexAtlas 的每请求 max_tokens 与任务预算不同，配置间数字差异不构成优劣结论。
- **token 口径**：token 数字来自端点 `usage` 回报，未用本地 tokenizer 复核。

## 复现命令

```bash
# key 经环境变量注入，不写入任何文件
export MINIMAX_API_KEY="<key>"
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
# 逐题执行（验收方案 §2.2），每题每轮一次调用，批间核对累计 token：
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat --api-key-env MINIMAX_API_KEY \
  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \
  --budget 16384 --agent-budget 120000 --total-tokens 24000 \
  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \
  --output .scratch/m6-narrow-verify2/<task-id> --task <task-id>
# 报告再生：
uv run --no-sync python scripts/m6_level2_narrow_verify2_report.py
```
