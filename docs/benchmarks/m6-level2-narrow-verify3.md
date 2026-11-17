# M6 层级 2 —— 修复后窄验证三轮（6 题 × 3 轮）

**状态：本 run 验证二轮窄验证（`m6-level2-narrow-verify2.md`）之后的预算效率修复（resources 收口、notice 折叠、string excerpt 截断、空转软提示、行裁剪机制）。代码状态 `claude/m6-level2-verify 1e8d947`。本文所有数字由 `scripts/m6_level2_narrow_verify3_report.py` 从 [m6-level2-narrow-verify3-traces.json](m6-level2-narrow-verify3-traces.json) 重算生成，未手改任何数字；trace 缺失或不完整时本脚本拒绝生成报告。**

本文回答 m6-verify3-plan（§5.1）的两个问题：

1. 六道覆盖已知失败面的题，DexAtlas 三轮合计是否 ≥4 题转通过（≥2/3 轮判过/题）；
2. 确定性修复直接相关的五题（除 descriptor 外）是否 ≥3 题转通过。

## 1. 运行配置

| 项 | 值 |
|---|---|
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入，不入 trace、不入报告） |
| 题集 | 6 题（m6-verify3-plan §2.1，覆盖全部已知失败面） |
| 轮次 | 6 题 × 3 轮 × 3 配置 = 54 条 trace |
| 每请求 max_tokens | A/B 16384；DexAtlas 120000（与三轮复测一致） |
| 每任务 token 预算 | DexAtlas 24,000（单题闸） |
| 迭代 / 步数 / 时限 / 请求超时 | 16 迭代 / 40 步 / 600 秒 / 300 秒 |
| 总额熔断 | 累计 450,000 tokens（逐题批间核对累计 usage） |
| 代码状态 | `claude/m6-level2-verify 1e8d947`（含预算效率修复：resources 收口 / notice 折叠 / string excerpt 截断 / 空转软提示 / 行裁剪机制） |
| 采样 | temperature 0（provider 默认） |

## 八指标（54 条 trace 经 `benchmarks.comparison.metrics.compare` 重算）

| metric | A | B | DexAtlas |
|---|---:|---:|---:|
| `correct_answer_rate` | 16.7% | 5.6% | 55.6% |
| `evidence_grounding_rate` | 0.0% | 0.0% | 100.0% |
| `unsupported_assertion_rate` | 100.0% | 100.0% | 0.0% |
| `false_positive_rate` | 70.0% | 100.0% | 17.4% |
| `tool_call_success_rate` | 100.0% | 100.0% | 97.0% |
| `recovery_rate` | n/a | n/a | 100.0% |
| `token_consumption` | 24,077 | 50,546 | 306,258 |
| `execution_duration` | 87.3 | 129.5 | 576.9 |

## 逐题结果（DexAtlas；每轮一格：通过数（判定））

| task | 失败面 | r1 判定 | r2 判定 | r3 判定 | 3 轮合计 |
|---|---|---|---|---|---|
| `partial.no-apktool-there-is-no-manifest` | 判分通道（limitations） | 0/1（empty） | 0/1（empty） | 1/1（correct） | **1/3** |
| `strings.api-key.demo` | C2 触发条件（常量池检索） | 0/1（empty） | 0/1（empty） | 0/1（empty） | **0/3** |
| `overloads.method-identity.descriptor-distinguishes` | C1 方法身份宽度 | 0/1（wrong） | 1/1（correct） | 0/1（wrong） | **1/3** |
| `manifest.permission.count-obfuscated` | C3 findings 纪律 | 1/1（correct） | 1/1（correct） | 1/1（correct） | **3/3** |
| `resources.app-name.demo` | 单题预算越线 | 1/1（correct） | 1/1（correct） | 1/1（correct） | **3/3** |
| `multidex.dex-file-count` | 单题预算越线（近闸值） | 1/1（correct） | 0/1（empty） | 1/1（correct） | **2/3** |

## 判定分布（3 轮合计，每配置 18 条）

| 配置 | correct | wrong | empty | no-answer | budget-exhausted | errored |
|---|---:|---:|---:|---:|---:|---:|
| A | 3 | 7 | 8 | 0 | 0 | 0 |
| B | 1 | 11 | 6 | 0 | 0 | 0 |
| DexAtlas | 10 | 2 | 6 | 0 | 0 | 0 |

## 窄验证判定（m6-verify3-plan §5.1 的闸）

- 转通过题（DexAtlas，3 轮中 ≥2 轮判过）：**3/6**（`manifest.permission.count-obfuscated`、`resources.app-name.demo`、`multidex.dex-file-count`）
- 确定性修复相关题转通过（partial、api-key、count、两道预算题）：**3/5**（`manifest.permission.count-obfuscated`、`resources.app-name.demo`、`multidex.dex-file-count`）
- 判定：**未达到窄验证通过判据**（转通过 3/6，门槛 ≥4；确定性修复相关题 3/5，门槛 ≥3）。按 m6-verify3-plan §7 停止：不进入完整重测，按验收方案三选一定稿服务承诺范围，本授权内不再追加修复轮。

## 修复验证关注点

- 单题 24,000 闸触发（DexAtlas）：**0 题**，均如实判 budget-exhausted 计失败。
- XML 工具调用协议泄漏（retryable 处理）：**0 条**。
- 判分失败与空答未重跑；errored 的基础设施性失败按 service-regression-set §6 处置。

## 成本与停止条件（照实陈述）

- 本 run 实测 token 合计 **380,881**（API `usage` 字段逐 trace 加总），授权上限 450,000（未触发）。
- 逐题分批执行，批间核对累计 usage；单题 24,000 闸由 `--total-tokens 24000` 落实。

## 已知局限

- **窄题集**：6 题覆盖已知失败面，但通过率不能外推到 20 题完整服务回归集；
  进入完整三轮（B1 关闭测量）以 m6-verify3-plan §5.1 的闸为准。
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
# 逐题执行（m6-verify3-plan §6.3），每题每轮一次调用，批间核对累计 token：
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat --api-key-env MINIMAX_API_KEY \
  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \
  --budget 16384 --agent-budget 120000 --total-tokens 24000 \
  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \
  --output .scratch/m6-verify3/narrow/r1/<task-id> --task <task-id>
# 报告再生：
uv run --no-sync python scripts/m6_level2_narrow_verify3_report.py
```
