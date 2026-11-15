# M6 层级 2 真实模型复测 —— 下一轮预算与判分方案

**状态：方案已定稿，待 [claude/m6-level2-rootcause-fixes](https://github.com/gg320324492-lgtm/dexatlas/branches) 的根因修复合入后执行。本文只定义预算、停止条件、执行顺序与判分流程，不含任何测量数字。**

上一轮复测（[m6-level2-retest.md](m6-level2-retest.md)）DexAtlas 15/20（75.0%），未达 80% 验收线；全部 trace 合计 356,803 tokens，**超出 35 万授权上限 6,803**。失败模式分析见 [m6-level2-failure-analysis.md](m6-level2-failure-analysis.md)，五个失败题的根因修复在分支 `claude/m6-level2-rootcause-fixes` 推进。本文为修复合入后的下一轮复测制定可复现的执行方案，总预算控制在授权额度之内。

## 1. 为什么上一轮会超预算

上一轮逐题 token（API `usage` 字段，prompt + completion，从 [m6-level2-retest-traces.json](m6-level2-retest-traces.json) 加总）：

| 配置 | 合计 | 单题最大 | 单题中位 | 超出 15,000 的题数 |
|---|---:|---:|---:|---:|
| A（源码文本检索） | 31,574 | 6,223 | ≈1,823 | 0 |
| B（结构化检索） | 14,980 | 1,289 | ≈690 | 0 |
| DexAtlas | 310,249 | 71,718 | ≈13,258 | 6 |

三个事实决定本轮方案：

1. **超支全部来自 DexAtlas 的长尾题。** `partial.no-apktool-there-is-no-manifest` 单题 71,718 tokens——任务级预算/迭代耗尽仍未作答。A/B 是检索式，单请求出答案，天然有界。
2. **DexAtlas 的通过题同样消耗可观。** 通过的 15 题合计 168,930 tokens，单题最大 22,776（`multidex.dex-file-count`，通过），另有 3 道通过题落在 14,243–16,364。**单题上限若压到这个区间以下，会把已验证的正确行为切成预算失败——测的就是预算，不是修复效果。**
3. **5 个失败题合计 141,319 tokens**，其中 4 题超过 15,000。根因修复（空转迭代、重复检索）若奏效，这些题应落回正常作答区间（通过题中位 ≈11,000）。

A/B 无任务级累计消耗（一问一答），DexAtlas 的任务级预算由 `benchmarks/comparison/run.py --total-tokens` 传入 `dexatlas.agent.state.Budget.max_tokens`，超支抛 `BudgetExceeded`、该题记 `budget-exhausted`——**单题熔断机制已存在，本轮直接启用并调低上限**，不需要改代码。

## 2. 预算拆分（20 题，1 轮，3 配置）

### 2.1 逐题上限

| 配置 | 每请求 `max_tokens` | 每题任务预算（`--total-tokens`） | 20 题预算合计 |
|---|---:|---:|---:|
| A | 16,384（不变） | 不适用（检索式，无任务级循环） | ≈31,574（实测）¹ |
| B | 16,384（不变） | 不适用 | ≈14,980（实测）¹ |
| DexAtlas | 120,000（不变，单请求上限） | **24,000** | **≤240,000** |

¹ A/B 检索式单请求出答案，上轮实测 31,574 / 14,980；预算按实测值计，不另设放宽。

**总预算上限：300,000 tokens**（A/B 实测 ≈46,554 + DexAtlas 20 × 24,000 = 480,000 的熔断上界之下的**实际控制线**；若 DexAtlas 全部题都打满 24,000，总额闸会先于单题闸把余下的题熔断——这是设计行为，见 §3）。

### 2.2 与授权额度的关系

| 项 | 值 |
|---|---:|
| 本轮总预算上限 | 300,000 |
| 授权上限 | 350,000 |
| 缓冲 | 50,000（≈14.3%） |

缓冲的用途：单题熔断在**检查点之后**才生效，一题的实际消耗可能略超 24,000（最后一次请求的 completion 计入后才检查）；缓冲覆盖这种尾差与 A/B 的轻微波动。**300,000 是硬数字：总闸对齐它，单题熔断对齐 24,000。**

### 2.3 单题上限 24,000 的依据

- **上界取自通过题的实测最大值。** 上轮通过题里最大消耗 22,776（`multidex.dex-file-count`，正确作答）；上限必须高于它，否则正确的解题路径会被预算拦腰截断。24,000 ≈ 通过题最大值 × 1.05，再留一点修复后波动余地。
- **对失败题足够收紧。** 5 个失败题中位 ≈19,787，若根因修复不奏效，这些题会贴着熔断线运行并在超线时被截停、记 `budget-exhausted`——这是测量结果，如实报告，不是故障。
- **总额闸是真正的保险。** 24,000 × 20 = 480,000 只是名义上界；总额 300,000 意味着平均每题只有 15,000 可用。修复生效时（失败题落回 ≈11,000 中位），预计总消耗 ≈47,000（A/B）+ ≈220,000–240,000（DexAtlas）≈ 270,000–290,000，在控制线内收尾；修复不奏效时，总额闸把超支拦在 300,000，授权线 350,000 永远不会被越过。

## 3. 停止条件

单题与总额两级熔断，先到先停：

| 级别 | 条件 | 动作 | 判定 |
|---|---|---|---|
| 单题 | 该题累计 token > 24,000（`BudgetExceeded("token", …)`） | 终止该题，继续下一题 | 该题记 **budget-exhausted，判负** |
| 单题辅助线 | 16 迭代 / 40 步 / 600 秒先到 | 同上 | 同上（与首测、上轮一致） |
| 总额 | 已完成题的累计 token > 300,000，或剩余题无法在余量内完成 | **熔断：剩余题全部不再发起** | 未跑题记 not-run，判负；报告如实记录熔断点 |
| 授权 | 任何时点累计 token > 350,000 | 立即停止一切请求 | 同上，并在报告标注越线 |

**两级熔断的机器实现不同，必须分开执行：**

- **单题熔断是 harness 内建的**：`--total-tokens 24000` 传入 `Budget.max_tokens`，`check_budget` 在每个请求完成后检查，超限抛 `BudgetExceeded`、该题记 `budget-exhausted`。运行中无需人工干预。
- **总额熔断 harness 没有**：`run.py` 一次调用跑完选定的全部题，中途不核对累计值。因此**必须逐题分批执行**（§4.3）：每题一次 `run.py` 调用（`--task` 只带该题），跑完立即读 trace 累计 token，超过 300,000（或余量不足以再跑一题）就停止发起后续题。批间检查由执行者按 §4.3 的检查命令逐题执行，这不是可选步骤——跳过它，授权线就只剩单题闸在守。

修复生效时预计总消耗 ≈270,000–290,000，总额闸不触发；它是防发散的保险，不是计划内的省钱手段。若它真的触发，说明修复未达预期或出现异常长尾，报告必须如实呈现，不得为凑预算砍题。

## 4. 执行顺序与运行命令

### 4.1 执行顺序

冻结集 20 题按 [benchmarks/m6_service_set.py](../../benchmarks/m6_service_set.py) 的既有顺序执行（与首测、上轮同一顺序，不重排）。三个配置按 A → B → DexAtlas 依次整批跑完再进入下一题组**不必要**——harness 本身逐题跑三配置；顺序不变即可。**先跑 A/B 再跑 DexAtlas** 的唯一好处是 A/B 的 4–6 万消耗先落袋，DexAtlas 剩余额度心中有数；harness 的默认顺序已满足，无需特判。

### 4.2 前置检查（跑之前，零成本）

```bash
# 1. 修复分支已合入，工作区干净
git status
git log --oneline -5

# 2. 三个后端可用（backend 不可用会让测试静默 skip，不是 pass）
uv run --no-sync python -c "from dexatlas.config.settings import Settings; from dexatlas.tools.registry import BackendRegistry; r = BackendRegistry(Settings()); print('available:', [b.name for b in r.available()]); print('missing:', [b.name for b in r.missing()])"

# 3. 环境变量就位（key 不入 trace、不入报告、不入本仓库）
python -c "import os; assert os.environ.get('MINIMAX_API_KEY'), 'MINIMAX_API_KEY 未设置'"

# 4. 预算校验脚本与方案一致
uv run --no-sync python scripts/m6_retest_budget.py --check-plan
```

后端检查的期望输出：`available` 含 `jadx`、`apktool`、`androguard` 三个，`missing` 为空。缺任何一个，先修环境再跑——带缺失后端跑出的不是这道题的测量。

### 4.3 运行命令（逐题分批，与上轮同参，仅新增 `--total-tokens`）

单题配置参数与上轮一致，仅新增 `--total-tokens 24000`（上轮未显式设置，落入默认 `max_tokens × 10 = 1,200,000`，等于没有单题闸门——这正是上轮单题跑到 71,718 的原因）。**总额熔断靠逐题分批实现**（§3）：20 题逐题调用，每题调用间核对累计 token。

对题 `<task-id>` 的单次调用：

```bash
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat --base-url https://api.minimaxi.com/v1 \
  --model MiniMax-M3.1-Flash \
  --budget 16384 --agent-budget 120000 \
  --total-tokens 24000 \
  --max-steps 40 --max-seconds 600 --max-iterations 16 \
  --output .scratch/m6-retest-r2/<task-id> \
  --task <task-id>
```

题集顺序（[benchmarks/m6_service_set.py](../../benchmarks/m6_service_set.py) 的既有顺序，与首测、上轮一致，不重排）：

`manifest.package.demo` → `manifest.permission.name-strings` → `manifest.permission.count-obfuscated` → `components.exported.demo` → `components.exported.obfuscated` → `overloads.method-identity.crypto-sign` → `overloads.method-identity.descriptor-distinguishes` → `ambiguity.declared-type-contradicts-body` → `xrefs.crypto-sign-callers` → `xrefs.handler-handle-callers` → `xrefs.crypto-sign-call-site-count` → `strings.api-key.demo` → `strings.telemetry-url.obfuscated` → `resources.app-name.demo` → `wheresource.app-name-resource-file.demo` → `unanswerable.crypto-digestof-has-no-callers` → `unanswerable.demo-declares-no-receiver` → `partial.no-apktool-there-is-no-manifest` → `partial.no-jadx-the-failure-is-recorded` → `multidex.dex-file-count`

**每题跑完后的批间检查（必做，不是可选）：**

```bash
uv run --no-sync python scripts/m6_retest_budget.py .scratch/m6-retest-r2/*/traces.json
```

退出码 0 且剩余题的预算上界（24,000 × 剩余题数）不超过余量 → 继续下一题；累计超 300,000，或余量不足以再跑一题 → **停止发起后续题**，按 §3 总额熔断处理。20 题各自落盘在 `.scratch/m6-retest-r2/<task-id>/traces.json`，跑完后合并为一份 `docs/benchmarks/m6-level2-retest-r2-traces.json`（`{"traces": [...]}`，与现有 trace 文件同形状），再走 §5 的报告流程。

### 4.4 失败处理

| 情形 | 处理 |
|---|---|
| 单题 `budget-exhausted` | 如实记录，判负；**不重跑该题**（重跑是选择性测量，破坏冻结纪律） |
| 网络错误 / 5xx | 该题记 `errored`；若是端点瞬时故障，允许对**该题**重试一次并记录重试事实；连续 3 题 errored 则中止本轮，排查环境 |
| trace 缺题（少于 60 条） | 报告不得生成；先查 harness 日志，补跑缺失题，trace 齐后才可再生报告 |
| 总额熔断触发 | 停止一切请求；报告如实记录熔断点与已完成题；本轮视为「预算内未完成」，不得拼凑成绩 |
| 超出授权 350,000 | 立即停止；在报告显著位置写明越线事实与原因 |

## 5. 判分与报告生成

1. **判分零改动。** 沿用 `benchmarks/comparison/run.py` 的既有判分（`benchmarks.model.check` + M6-③ 的 `expect_backend_failure` 谓词，见 [service-regression-set.md](service-regression-set.md) §3 与附录 B）。判分语义与上轮完全一致，成绩差异只能来自修复。
2. **trace 落盘。** harness 把 trace 写到 `--output` 目录（`traces.json` + `comparison.json`）。复核无误后，把 trace 提交为 `docs/benchmarks/m6-level2-retest-r2-traces.json`（命名沿用现有 `-traces.json` 惯例，与上轮文件并列，**不覆盖**上轮 trace——历史测量是不可再生的记录）。
3. **报告由脚本生成，数字不许手写。** 复用 [scripts/m6_level2_retest_report.py](../../scripts/m6_level2_retest_report.py) 的口径（或在其旁新增一个读取 r2 trace 的薄封装），从 r2 trace 重算：三配置正确数、逐题结果、token 合计与逐题分布、与上轮（基线）对比。报告落为 `docs/benchmarks/m6-level2-retest-r2.md`。**对照基线是上轮的 [m6-level2-retest-traces.json](m6-level2-retest-traces.json)，不是首测**——首测三轮的对照上轮已做过。
4. **判分口径检查。** 报告必须区分 `correct / wrong / empty / no-answer / errored / budget-exhausted`，且 `budget-exhausted` 题数单独列出——这是本轮新增闸门的直接观测，验收分析需要知道哪些失败是预算造成的、哪些是能力造成的。
5. **验收线不变。** DexAtlas 单轮 ≥ 80%（≥16/20）为通过；A/B 仅作对照，不设验收线。
6. **报告完成后跑校验。**

```bash
uv run --no-sync python scripts/m6_retest_budget.py docs/benchmarks/m6-level2-retest-r2-traces.json
uv run --no-sync python scripts/m6_level2_retest_report.py   # 上轮报告须仍可逐字节再生
```

## 6. 预算校验脚本

[scripts/m6_retest_budget.py](../../scripts/m6_retest_budget.py) 是本轮预算的机器可执行形式，判分与报告生成前必须先过它：

- 逐题核对 DexAtlas trace 的 `prompt_tokens + completion_tokens` 是否超 24,000，超支即非零退出并列出超支题；
- 全部 trace 合计超 300,000 即非零退出，超 350,000 单独标注为越授权线；
- A/B 逐题超 16,384 × 2 时告警（检索式理论上单请求有界，超界说明异常）；
- `--check-plan` 模式只校验本方案文件存在且包含预算关键数字，供运行前自检；
- 无 trace 数据时打印「无 trace 数据，仅校验方案文件存在且格式正确」并退出 0。

## 7. 与既有文档的关系

| 文档 | 关系 |
|---|---|
| [m6-level2-real.md](m6-level2-real.md) | 首测（修复前，三轮）。历史记录，不再对照 |
| [m6-level2-retest.md](m6-level2-retest.md) | 上轮复测（M6-③ 修复后，单轮，15/20，超预算）。本轮的对照基线 |
| [m6-level2-failure-analysis.md](m6-level2-failure-analysis.md) | 五个失败题的根因分析；本轮验证其修复效果 |
| [service-regression-set.md](service-regression-set.md) | 冻结 20 题与判定规则。本轮题集、判分均以其为准，不改动 |
| [m6-level3-recheck.md](m6-level3-recheck.md) | M6-③ 修复的确定性回归。本轮通过后它继续作为层级 0 基线 |

冻结纪律重申：题集不因结果增删；判分规则不因结果修改；预算参数**先于运行**固定在本文（§2），运行中不得下调上限来「省预算」，也不得上调来「救题」。任何偏离必须在报告的「偏离记录」一节写明。
