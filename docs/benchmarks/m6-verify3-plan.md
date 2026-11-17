# M6 层级 2 —— 窄验证三轮 + 完整重测执行方案（verify3）

**状态：方案定稿，待执行。本文是执行约束与判据，不含任何测量结果；在真实模型调用发生前，本文不产生任何 trace 与数字。判分七条红线不放宽。**

## 1. 背景与授权边界

窄验证二轮（[m6-level2-narrow-verify2.md](m6-level2-narrow-verify2.md)）未达判据：DexAtlas 转通过 2/6、确定性修复题 1/5（门槛 ≥4/6、≥3/5），总用量 420,826 tokens（授权 410,000，超支如实披露）。此后第三轮修复已在 `claude/budget-impl` 落地：行裁剪机制、resources 收口、string excerpt 截断、空转提示、提示词条款（均带红→绿回归）。

本方案为修复后的第三轮窄验证，以及窄验证达标后的完整三轮重测，给出一次性授权的执行约束：

- 窄验证三轮总额 ≤ **450,000** tokens；完整重测总额 ≤ **1,250,000** tokens（仅窄验证过闸后启动）。
- 不达标即停：按验收方案三选一定稿服务承诺范围，**不再追加修复轮**。
- 全程不放宽测量口径：单题 24,000 闸、16 迭代、40 步、600 秒、temperature 0、判分语义零改动（`_FAILURE_MARKERS` closed set、budget-exhausted 判负、expect_count、expect_empty、must_contain 原样）。

## 2. 题集与轮次

### 2.1 窄验证三轮

6 题 × 3 轮 × 3 配置（A 源码文本检索 / B 结构化检索 / DexAtlas）= **54 条 trace**，DexAtlas 18 条为判定主体。题集与二轮一致，覆盖全部已知失败面：

| # | task | 失败面 |
|---|---|---|
| 1 | `partial.no-apktool-there-is-no-manifest` | 判分通道（limitations） |
| 2 | `strings.api-key.demo` | C2 触发条件（常量池检索） |
| 3 | `overloads.method-identity.descriptor-distinguishes` | C1 方法身份宽度 |
| 4 | `manifest.permission.count-obfuscated` | C3 findings 纪律 |
| 5 | `resources.app-name.demo` | 单题预算越线 |
| 6 | `multidex.dex-file-count` | 单题预算越线（近闸值） |

### 2.2 完整重测

冻结 20 题（[m6_service_set.py](../../benchmarks/m6_service_set.py)，与 [service-regression-set.md](service-regression-set.md) 冻结纪律一致）× 3 轮 × 3 配置 = **180 条 trace**。题集不增删、不重排；不因通过率删题。

## 3. 运行配置

与既有轮次完全一致（[m6-level2-retest4.md](m6-level2-retest4.md) 复现命令），一项不放松：

| 项 | 值 |
|---|---|
| 模型 | MiniMax-M3.1-Flash（`https://api.minimaxi.com/v1`，openai-compatible） |
| provider | `openai-compat`（key 经 `MINIMAX_API_KEY` 环境变量注入） |
| 每请求 max_tokens | A/B 16,384；DexAtlas 120,000 |
| 每任务 token 闸 | DexAtlas 24,000（`--total-tokens 24000`，单题熔断，harness 内建） |
| 迭代 / 步数 / 时限 / 请求超时 | 16 / 40 / 600 秒 / 300 秒 |
| 采样 | temperature 0（provider 默认） |
| 代码状态 | `claude/budget-impl` 上含第三轮修复的提交（执行前冻结并记录 hash，全程不改代码） |

## 4. token 预算与总额熔断

### 4.1 预算

| 阶段 | 规模 | 预期（依据） | 授权上限（硬） |
|---|---|---|---|
| 窄验证三轮 | 54 trace | ≈410,000（二轮实际 420,826；本轮修复均指向降耗） | **450,000** |
| 完整重测 | 180 trace | ≈1,180,000（retest4 实际 1,182,356，三轮 395,740 / 395,542 / 391,074） | **1,250,000** |

两阶段预算独立核算；只有窄验证过闸才动用完整重测额度。token 口径 = 每条 trace 的 `result.prompt_tokens + result.completion_tokens`（端点 usage 回报，与既有报告一致，未用本地 tokenizer 复核）。

### 4.2 单题闸（既有，不放松）

`--total-tokens 24000` 由 harness 的 `Budget.max_tokens` 强制：每请求完成后检查，超限抛 `BudgetExceeded`、该题记 `budget-exhausted` 判负。运行中无需人工干预。

### 4.3 总额熔断（逐题批间核对）

harness 不核对累计值，**必须逐题分批执行**：每题每轮一次 `run.py` 调用，跑完立即核对累计 usage。这不是可选步骤——跳过它，授权上限就只剩单题闸在守。

- **熔断线（硬）**：累计 > 阶段上限 → 立即停止发起后续题；在跑的题让它跑完，超支如实披露（沿用窄验证二轮对超支 10,826 的处理方式）。
- **预测线（保守）**：累计 + 24,000 > 阶段上限（余量不足再跑一题）→ 不再发起下一题。

核对命令（窄验证；完整重测把路径换成 `.scratch/m6-verify3/full`）：

```bash
uv run --no-sync python -c "import json,pathlib; f=lambda p: sum(t['result']['prompt_tokens']+t['result']['completion_tokens'] for t in json.loads(pathlib.Path(p).read_text(encoding='utf-8'))['traces']); print('cumulative:',sum(f(p) for p in pathlib.Path('.scratch/m6-verify3/narrow').glob('r*/*/traces.json')))"
```

## 5. 判定门槛

### 5.1 窄验证闸（进入完整重测的必要条件）

- DexAtlas 转通过（3 轮中 ≥2 轮判过）**≥4/6**；
- 确定性修复相关 5 题（§2.1 除 descriptor 外：partial、api-key、count、resources、multidex）转通过 **≥3/5**。

两条同时满足才进入完整重测；任一不满足 → 按 §7 停止。

### 5.2 完整重测 B1 线

- 每轮 DexAtlas **≥16/20**；
- 三轮合计 **≥54/60**（90%）。

两条同时满足 → B1 关闭；否则 B1 保持未关闭（§7）。A/B 配置数字照实披露，不设闸。

## 6. 运行手册（runbook）

### 6.1 前置检查（零 token）

```bash
# 1. 代码状态：第三轮修复已提交，工作区干净，记录 commit hash
git status && git log --oneline -3

# 2. 独立 venv（每个 worktree 各自 sync，绝不复用其他 checkout 的 .venv）
uv sync --extra dev --extra analysis

# 3. 三个后端可用（后端缺失会让测试静默 skip，不是 pass）
uv run --no-sync python -c "from dexatlas.config.settings import Settings; from dexatlas.tools.registry import BackendRegistry; r = BackendRegistry(Settings()); print('available:', [b.name for b in r.available()]); print('missing:', [b.name for b in r.missing()])"
```

期望：`available` 含 `jadx`、`apktool`、`androguard` 三个，`missing` 为空。缺任何一个，先修环境再跑。

其余前置（零 token）：

- examples/ 五样本 fixtures 就位、可构建；
- 零模型判分回归通过（确认判分口径与 `benchmarks/model.py::check` 一致、未被本轮改动）；
- 两个报告脚本 + `pyproject.toml` 的 RUF001 豁免条目 + §4.3/§6.6 的核对与合并命令就绪。

### 6.2 环境变量注入（key 绝不落盘）

key 只存在于 `C:/Users/pc/Desktop/vibe coding/新建 文本文档.txt` 首行，仅在 shell 会话内注入环境变量：

```bash
export MINIMAX_API_KEY="$(head -1 'C:/Users/pc/Desktop/vibe coding/新建 文本文档.txt' | tr -d '\r\n')"
python -c "import os; assert os.environ.get('MINIMAX_API_KEY'), 'MINIMAX_API_KEY 未设置'"
```

```bash
# 后端路径随执行环境而定（历史值见 m6-level2-retest4.md 复现命令），以后端检查三件套齐全为准
export DEXATLAS_JADX_PATH="<jadx.bat 绝对路径>"
export DEXATLAS_APKTOOL_JAR="<apktool.jar 绝对路径>"
```

纪律：

- 绝不 echo key、绝不写入代码/提交/报告/trace；`MINIMAX_API_KEY` 只以变量名出现在文档中；
- 注入时进程内剥离 CRLF（`tr -d '\r\n'`）；
- 命令本身不含 key 值，shell 历史不落 key。

### 6.3 逐题执行

每题每轮一次调用（A/B/DexAtlas 三配置同批），输出落 `.scratch`（不提交）：

```bash
uv run --no-sync python benchmarks/comparison/run.py \
  --provider openai-compat --api-key-env MINIMAX_API_KEY \
  --base-url https://api.minimaxi.com/v1 --model MiniMax-M3.1-Flash \
  --budget 16384 --agent-budget 120000 --total-tokens 24000 \
  --max-iterations 16 --max-steps 40 --max-seconds 600 --request-timeout 300 \
  --output .scratch/m6-verify3/narrow/r1/<task-id> --task <task-id>
```

- 窄验证输出根：`.scratch/m6-verify3/narrow/r{1,2,3}/<task-id>/`；
- 完整重测输出根：`.scratch/m6-verify3/full/r{1,2,3}/<task-id>/`；
- 顺序：逐轮推进，轮内按冻结集顺序逐题；每题跑完立即做 §4.3 核对与 §6.4 进程检查。

### 6.4 批间进程检查

每批（每题）之间与每轮结束后，确认无残留/并发进程（既有教训：TaskStop 杀不死 uv 孙进程、并发测量互相污染 coverage）：

```bash
powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -match 'python|uv' } | Select-Object Id,ProcessName,StartTime"
```

只允许当前批次的进程存在；发现孤儿进程先 `taskkill /PID <pid> /F` 清理再继续。

### 6.5 每轮后 sk- 扫描

每轮 trace 落盘后立即扫描（`.scratch` 未合并目录与合并后的 `docs/benchmarks/` 文件各扫一次）：

```bash
grep -rnoE "sk-[A-Za-z0-9_]+" .scratch/m6-verify3/narrow/r1/ | sort -u
```

- 唯一允许命中：`sk_live_2f8a91c4e7b3`（first-party demo 夹具常量，examples/demo-app）；
- 出现任何其他 `sk-` 命中 → 立即停止一切请求，隔离相关文件，按泄漏事故处置；
- 附加加固：确认 key 值本身未出现在任何 trace/报告——`grep -rqF -- "$MINIMAX_API_KEY" <目录>` 应无命中（命令不回显 key）。

### 6.6 trace 合并落盘

轮内全部题完成后合并为仓库内 trace 文件（`docs/benchmarks/`；`.scratch` 原始目录不提交）：

```bash
# 窄验证：三轮合一（54 条）
uv run --no-sync python -c "import json,pathlib; ts=[t for p in sorted(pathlib.Path('.scratch/m6-verify3/narrow').glob('r*/*/traces.json')) for t in json.loads(p.read_text(encoding='utf-8'))['traces']]; pathlib.Path('docs/benchmarks/m6-level2-narrow-verify3-traces.json').write_text(json.dumps({'traces':ts},ensure_ascii=False,indent=2),encoding='utf-8'); print('traces:',len(ts))"
```

```bash
# 完整重测：每轮一份（各 60 条，共 180 条）；r2/r3 同式换目录与文件名
uv run --no-sync python -c "import json,pathlib; ts=[t for p in sorted(pathlib.Path('.scratch/m6-verify3/full/r1').glob('*/traces.json')) for t in json.loads(p.read_text(encoding='utf-8'))['traces']]; pathlib.Path('docs/benchmarks/m6-level2-retest5-traces-r1.json').write_text(json.dumps({'traces':ts},ensure_ascii=False,indent=2),encoding='utf-8'); print('traces:',len(ts))"
```

期望条数：窄验证 54；完整重测每轮 60。条数不符 → 按 §6.8 补跑缺失题，不得带缺口生成报告。

### 6.7 报告生成（脚本化，数字不手写）

- 窄验证：新开 `scripts/m6_level2_narrow_verify3_report.py`，从合并 trace 重算生成 `docs/benchmarks/m6-level2-narrow-verify3.md`；trace 少于 54 条时拒绝生成。
- 完整重测：新开 `scripts/m6_level2_retest5_report.py`，从 r1/r2/r3 三份 trace 重算生成 `docs/benchmarks/m6-level2-retest5.md`；任一轮缺失或不足 60 条拒绝生成。
- 两个脚本在 `pyproject.toml` 的 `[tool.ruff.lint.per-file-ignores]` 沿用 `RUF001` 豁免（中文报告字符串字面量的既有处理）。
- 报告必含：代码状态 commit、模型与配置、逐题逐轮判定、八指标、token 合计与熔断核对记录、复现命令、已知局限（单模型、温度 0、first-party 小样本、预算不对等、token 口径依赖端点 usage）。

### 6.8 中断恢复

- 每题独立落盘，中断只损失在跑的一题；
- 恢复步骤：① §6.4 确认无孤儿进程；② §4.3 以已落盘 trace 重算累计；③ 从第一个缺失的 `<轮>/<题>` 继续，已完成的题不重跑（消耗已计入）；④ 某 trace 文件损坏/不完整时，移入 `.scratch/m6-verify3/quarantine/` 并重跑该题，报告注明；
- 端点 529/超时成片出现 → 按既有重试参数处理；仍成片失败按 §7 停止条件终止并如实记录，不带病硬跑。

## 7. 失败处置

- **窄验证不达标**（转通过 <4/6 或确定性题 <3/5）：立即停止，不进入完整重测；已消耗 token 与已落盘 trace 如实披露；按验收方案三选一定稿服务承诺范围（连续两轮未达后，方案 3「现状披露」为默认候选，见 [status.md](../status.md) 的披露口径），**本方案授权内不再追加任何修复轮或模型调用**。
- **完整重测不达标**（任一轮 <16/20 或三轮合计 <54/60）：B1 保持未关闭；结果如实落盘与披露；同样按验收方案三选一定稿承诺范围（含「缩小并重述服务承诺」），不再追加修复轮。
- 全程纪律：不删题、不重跑判分失败题换通过率、不放松 24,000 单题闸与各执行参数、判分语义零改动；errored 的如实重试与原始 trace 保留沿用既有做法。

## 8. 执行清单

前置（零 token）：

- [ ] `claude/budget-impl` 第三轮修复已提交推送，记录执行 commit hash
- [ ] 本 worktree 独立 `uv sync --extra dev --extra analysis`
- [ ] 后端三件套 available/missing 检查通过
- [ ] examples/ 五样本 fixtures 就位
- [ ] 零模型判分回归通过（判分口径未变）
- [ ] 两个报告脚本 + pyproject RUF001 豁免 + 预算核对/trace 合并命令就绪
- [ ] `MINIMAX_API_KEY` 注入并断言存在（不回显、不落盘）

窄验证三轮（≤450,000 tokens）：

- [ ] r1：6 题逐题执行，每题批间核对累计 usage 与进程
- [ ] r1 后：sk- 扫描通过，trace 落盘
- [ ] r2：同上
- [ ] r3：同上
- [ ] 54 条 trace 完整性核对通过
- [ ] `m6-level2-narrow-verify3.md` 由脚本生成
- [ ] 闸判定：转通过 ≥4/6 且确定性题 ≥3/5？（不达标 → §7 停止）

完整重测（仅过闸后；≤1,250,000 tokens）：

- [ ] r1：20 题逐题执行，每题批间核对
- [ ] r1 后：sk- 扫描 + 60 条 trace 合并落盘
- [ ] r2：同上
- [ ] r3：同上
- [ ] 180 条 trace 完整性核对通过
- [ ] `m6-level2-retest5.md` 由脚本生成
- [ ] B1 判定：每轮 ≥16/20 且三轮 ≥54/60？

收尾：

- [ ] status.md / CHANGELOG 按结果更新（数字全部由脚本生成）
- [ ] `remap-citations.py` + `check-doc-citations.py` 通过
- [ ] 若代码有变：`ruff format` 后完整测量刷新
