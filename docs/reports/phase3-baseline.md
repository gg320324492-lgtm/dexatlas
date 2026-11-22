# Phase 3 M5 — 基线校准与对外陈述收口

日期：2026-11-15。基准：`6b08684`（main）+ 本分支改动。
这是 [Phase 3 计划](../roadmap/phase3-plan.md) §4（M5）的产物：先让承诺与代码、trace、演示一致。
本文回答三个问题：**对外声明有什么证据、三份 benchmark 是否可从原始 trace 重算、还剩哪些问题**。

---

## 1. 核查命令与输出摘要

以下命令全部在本仓库根目录、本分支工作树上执行（2026-11-15）。

### 1.1 三份 benchmark 的指标重算

```bash
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-traces.json --metrics
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-real-traces.json --metrics
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-stronger-traces.json --metrics
```

三份的八项指标输出与各自报告逐格一致（scripted：16.3/16.3/5.4 等；
real：30.4/22.8/19.6 等；stronger：28.3/16.3/22.8 等）。
`benchmarks/comparison/run.py` 的 `--input … --metrics` 是唯一再生入口，
CI 的 `m3-comparison` job 用同一命令兜底。

### 1.2 三份报告的逐字再生

```bash
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-traces.json --report docs/benchmarks/comparison.md
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-real-traces.json --report docs/benchmarks/comparison-real.md
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-stronger-traces.json \
  --compare-to docs/benchmarks/comparison-real-traces.json \
  --report docs/benchmarks/comparison-stronger.md
```

再生输出与仓库内三份 `.md` **逐字节一致**（`diff` 为空）。
注意 stronger 报告的再生必须带 `--compare-to docs/benchmarks/comparison-real-traces.json`，
否则再生出的报告会缺「Comparison with the previous run」段——报告尾部的
Regenerating 段现在写的就是这两条正确命令。

### 1.3 trace 的逐配置预算核对

从三份 trace 的 `max_tokens` 字段逐条读取：

| trace 文件 | A | B | DexAtlas | 模型 | provider |
|---|---:|---:|---:|---|---|
| `comparison-traces.json` | 2048 | 2048 | 2048 | （无，scripted） | scripted |
| `comparison-real-traces.json` | 4096 | 4096 | 4096 | MiniMax-M3.1-Flash | openai-compatible |
| `comparison-stronger-traces.json` | **4096** | **4096** | **16384** | MiniMax-M3.1-Flash | openai-compatible |

**发现并已修正的不一致**：`comparison-stronger.md` 曾写
「Budget: 16384 `max_tokens` per request, identical for all three configurations」，
而 trace 里 A/B 每请求实际是 4096，只有 DexAtlas 放宽到 16384。
「更强模型」的说法同样不成立：三轮都是同一个 MiniMax-M3.1-Flash，
变化的是预算与执行条件（agent 步数 12→40、循环轮数 8→24、每请求 token 4096→16384、
敏感读数批准门放行上限 8 次；A/B 每请求保持 4096）。
两轮的差值是**这对运行的差值**，不能归因为模型变化。

修正方式：改 `benchmarks/comparison/run.py` 的报告生成器（不手改报告数字），
报告头部按 trace 实际情况二选一——预算一致时写「identical for all three」，
不一致时逐配置列出并说明「agent 的回答信封加宽而 A/B 未加宽，配置在执行条件上
不等价」；指标表新增每配置 Max tokens 列；与上一轮的对比段改为逐配置预算陈述；
末条固定披露同样按预算是否一致分别生成。三份报告随后由脚本再生。

### 1.4 文档与版本检查

| 检查 | 结果 |
|---|---|
| `uv run --no-sync pytest -q tests/test_docs.py` | **59 passed, 1 skipped**（skip 需 demo extra 的 Pillow 深检） |
| `uv run --no-sync python scripts/check-doc-citations.py` | 94 处引用校验 93 处通过；1 处 location-only（待人工决定）；drifted 0 |
| `uv run --no-sync python scripts/check-version-claims.py --base auto` | 2 条 findings，均为**已知且有意保留**的历史记录（v0.2.0 发版说明写 91.0%、当时实测 91.6%；v0.1.3 手抄 93.9%）——检查器结论「Every version claim matches the repository」 |
| `scripts/refresh-report-figures.py --check` | 报告与新鲜测量一致（1370 个测试收集自当前树；完整测量见 §4） |
| `uv run --no-sync ruff check .` / `ruff format --check .` | 通过（本分支改动文件） |
| `uv run --no-sync pytest -q tests/test_comparison_metrics.py tests/test_comparison_providers.py` | **27 passed** |

### 1.5 本次文档修订清单

| 文件 | 修订 |
|---|---|
| `benchmarks/comparison/run.py` | 报告生成器按 trace 逐配置陈述预算；「更强模型」归因纠正；Regenerating 段指向各报告自己的 trace；`_REAL_PROVIDER_SECTION` 尾句不再声称 checked-in 报告「保持 scripted 基线」 |
| `docs/benchmarks/comparison.md`、`comparison-real.md`、`comparison-stronger.md` | 由脚本再生（数字不变，措辞如实） |
| `README.md` / `README.zh-CN.md` | 演示录像的 Agent 屏 scripted provider 披露移到首屏可见位置；路线图表 Phase 2 版本号 `v0.5.0`→`v0.2.0`（与 ROADMAP、实际发布一致） |
| `docs/status.md` | 「换更强模型」段加修订注记：同一模型的预算/执行条件变化，差值不归因模型变化 |
| `docs/HANDOVER.md` | M3 行措辞改为 same-model wider-budget rerun |
| `docs/reports/phase3-baseline.md` | 本文件（新建） |

未改动任何 `<!--fig:...-->` 生成数字；未改动 `src/` 生产代码
（`benchmarks/comparison/run.py` 是仓库工具，不是 `src/dexatlas` 生产代码；
其行为变化只影响报告措辞，指标计算逻辑未动，`compare()` 原样）。

---

## 2. 对外声明清单

每项标注：**已验证**（有可运行测试、基准或手工核验记录）、
**受限**（在声明范围内成立，边界另列）、**未验证**（无证据，不得对外声明）。

### 2.1 功能

| # | 声明 | 状态 | 证据与核验方法 |
|---|---|---|---|
| F1 | APK 摄取：哈希、校验、二进制 manifest 解码（包名、版本、SDK、权限、导出组件） | 已验证 | `tests/test_docs.py` 报告数字核对；`docs/install.md` 实测输出（340 classes / 2,600 methods / 6,033 xrefs）；案例 1 逐条 locator |
| F2 | 三后端符号索引：Androguard 权威符号与调用点、JADX 反编译、Apktool manifest + Smali 回退 | 已验证 | CI 三种后端配置矩阵；`tests/test_smali_fallback_integration.py`（JADX 缺席时 Smali 回退真跑通）；后端缺失时记录 `ToolError` 而非异常 |
| F3 | 交叉引用：调用点带 DEX 文件与指令偏移，调用边可从 CLI/API/浏览器/agent 查询 | 已验证 | `docs/status.md` M0 段；P2-003 回归测试（方向断言）；案例 1 的一跳导航 |
| F4 | 证据模型三级：`verified`（工具确定性建立+可解析引用）/ `lead` / `insufficient`；模型输出写不成 `verified` | 已验证 | `tests/test_evidence_invariants.py`（23 tests）；`tests/test_model_claims.py`（11 tests）；去掉不变量测试即红 |
| F5 | 只读 MCP server：十工具、stdio、有界响应、不写不跑 shell、**不需要模型 provider** | 已验证 | `tests/test_mcp_tools.py`（25 tests）；`docs/architecture/mcp-server.md`；`uv run dexatlas-mcp` |
| F6 | 证据优先 agent：单循环、预算、串行工具、结论三段式；APK 内指令是数据不是命令 | 受限 | 库形态，无 `dexatlas agent "..."` CLI 入口（`docs/architecture/agent.md` §338）；`tests/test_agent_untrusted_input.py` 等四个文件 39 个测试；真实模型行为见 F7 |
| F7 | agent 在真实模型下可完成带引用的结论 | 受限 | 仅在放宽配置下验证：MiniMax-M3.1-Flash、120k tokens、40 步、8 迭代时，2/3 类测试问题稳定 `completed` 且引用可解析（`m4-e2e-run.md` §5）；**默认预算下 5/5 `budget_exhausted`**；枚举型问题放宽后仍不收敛。不声称对所有问题可靠 |
| F8 | 死代码由 CI vulture 门禁拦截 | 已验证 | `.github/workflows/ci.yml` lint job 内 `uv run vulture … --min-confidence 80`；Phase 3 计划明确不再重复排期 |
| F9 | Web workbench 八屏（面板/上传/检索证据/调用关系/agent 工作区/报告导出/基准视图） | 已验证 | M4 源码评审通过（`m4-review.md`）；端点与路由逐屏核对 |
| F10 | 基准视图数字与报告逐字一致 | 已验证 | `GET /api/benchmarks/m3` 用 harness 自己的 `_run_from_document`+`compare` 实时重算（`src/dexatlas/workbench/benchmarks.py`）；trace 缺失时答空列表+披露 |
| F11 | 大型 APK（合成 200k 方法）分析、三缺陷修复 | 受限 | `docs/benchmarks/large-apk.md`：合成样本、真实机器测量；真实大 APK、JADX/Apktool 规模表现、native、内存**未测** |
| F12 | 报告 Markdown/JSON 与 workbench 导出逐字节一致 | 已验证 | M4 端到端实测（`m4-e2e-run.md`）；同一渲染器同一快照 |

### 2.2 安装前提

| # | 声明 | 状态 | 证据 |
|---|---|---|---|
| I1 | Python 3.12+（3.12/3.13 在 CI 测试） | 已验证 | `pyproject.toml` `requires-python = ">=3.12"`；CI 矩阵 |
| I2 | uv 为包/环境管理器；每个 worktree 需要自己的 `.venv` | 已验证 | `docs/install.md`；CLAUDE.md 陷阱记录 |
| I3 | JDK 21+ 仅为 JADX/Apktool 所需 | 已验证 | `docs/install.md` Requirements 表；Docker 构建失败即暴露 |
| I4 | Node.js 18+ 仅为 workbench 前端构建所需 | 已验证 | `docs/install.md`；CLI/API/agent 不需要 |
| I5 | 三后端可选且互相独立；一个不装仍可分析（哈希、校验、Androguard 索引） | 已验证 | `docs/install.md` 降级输出实测；`dexatlas backends` 命令 |
| I6 | 无 APK 入库：样例一方构建或 Apache-2.0 拉取 | 已验证 | `examples/` + `scripts/fetch-fixtures.sh` + `fixtures/apk/SOURCES.md` |

### 2.3 支持平台

| # | 声明 | 状态 | 证据 |
|---|---|---|---|
| P1 | Linux（CI 全部 7 个并行运行在 ubuntu-latest） | 已验证 | `.github/workflows/ci.yml` |
| P2 | Windows（开发机验证；`jadx.bat` 启动器解析、路径与临时目录处理有专项测试） | 已验证 | `tests/test_backend_discovery.py`（23 tests，含 Windows launcher）；本报告全部命令在 Windows 11 实跑 |
| P3 | macOS | **未验证** | 无 CI job、无手工核验记录。对外不得声称 macOS 支持 |

### 2.4 默认 agent 预算

| # | 声明 | 状态 | 证据 |
|---|---|---|---|
| B1 | agent 默认预算：20,000 tokens / 8 迭代 / 120 秒 / 12 次工具调用 | 已验证 | `src/dexatlas/agent/state.py:117-127`（`Budget`）；`src/dexatlas/agent/planner.py:171`（`DEFAULT_MAX_STEPS = 12`） |
| B2 | 预算可经环境变量覆盖：`DEXATLAS_AGENT_MAX_TOKENS` / `_MAX_ITERATIONS` / `_MAX_SECONDS` / `_MAX_STEPS`；非法值报 `agent_env_invalid` 而非静默忽略 | 已验证 | `src/dexatlas/workbench/agent_tasks.py`（`budget_from_env` / `max_steps_from_env`）；`docs/architecture/agent.md` budgets 段 |
| B3 | comparison harness 的默认每请求预算：scripted 2048、真实模型 4096（三配置同值）；agent 任务总预算默认 10× 请求预算；循环默认 16 轮、600 秒 | 已验证 | `benchmarks/comparison/run.py:934` 与 `--help` 文本；`systems.py` AgentSystem 注释 |
| B4 | 预算耗尽时任务停止并如实标注 *did not finish*，不编造「没找到」 | 已验证 | `docs/architecture/agent.md`；`m4-e2e-run.md` 5/5 `budget_exhausted` 记录 |

### 2.5 演示 provider

| # | 声明 | 状态 | 证据 |
|---|---|---|---|
| D1 | 演示录像（`demo.mp4`/`demo.gif`）中分析、检索、证据、调用关系、报告各屏为真实分析产物 | 已验证 | `docs/status.md` 录制记录（真实浏览器操作录屏，无剪辑无合成帧）；`tests/test_docs.py` 资产存在性与 MP4 头校验 |
| D2 | 录像中 **Agent 屏由仓库自带 scripted 演示 provider 驱动——无密钥、无真实模型调用**；真实模型表现另见 M4 实测 | 已验证（披露已在双语 README 首屏可见位置） | `src/dexatlas/agent/providers/scripted.py`；本次 README 修订；`m4-e2e-run.md` |
| D3 | scripted provider 的 benchmark 数字测量的是 harness，不是模型基线；与真实模型测量分开陈述、永不并表 | 已验证 | `comparison.md` 披露段；`comparison-real.md`「not reproducible to the digit」段；CI 门禁 |
| D4 | workbench 无模型配置时 agent 提问返回 `503 agent_not_configured`，不由替身模型作答 | 已验证 | `tests/test_workbench_agent.py`（20 tests）；`model-disable-verification.md`（CLI 12 / REST 4 / workbench 16 / MCP 11 项全部正常） |

### 2.6 后端缺失行为

| # | 声明 | 状态 | 证据 |
|---|---|---|---|
| E1 | 后端缺失时分析继续：报告如实列出哪些步骤没跑（`! apktool is not installed…`） | 已验证 | `docs/install.md` 实测输出；`tests/test_partial_backend_failure.py` |
| E2 | `dexatlas source` 无 JADX/Apktool 时明确报告，而非返回空结果 | 已验证 | `docs/install.md`「`source` needs JADX or Apktool」段 |
| E3 | 后端缺失时测试 skip，**skip 不算 pass**；读 summary 的 skip 数 | 已验证 | CLAUDE.md；`tests/conftest.py` 临时目录与跳过机制 |
| E4 | 退出码 0–5 语义（含 5 = 截断完成，区别于 3 = 失败） | 已验证 | `docs/install.md` 退出码表；`output_truncated` 回归测试 |
| E5 | 上传限制：256 MiB 流式拒绝（413）、声明解压 2 GiB / 100× 膨胀比 422（ZIP central directory 阶段拒绝） | 已验证 | `src/dexatlas/core/ingest.py:41,65`；`docs/install.md` |

---

## 3. 三份 benchmark 的可比性说明

**配置不等价之处，明确列出：**

1. **scripted vs real**：provider 不同，一个是脚本、一个是 MiniMax-M3.1-Flash。
   两者回答不同问题，分开陈述，永不并表（报告披露 + CI 门禁）。
2. **real vs stronger**：同模型、同题集、同 scorer、同 92 题；不同的是
   **执行条件**——DexAtlas 每请求 4096→16384、步数 12→40、循环 8→24、
   敏感读数批准门从「暂停等人」改为「计划内放行（上限 8 次）」。
   A/B 每请求保持 4096。所以 stronger 表头曾写的
   「Budget: 16384 identical for all three configurations」是错的，已修正；
   两轮差值（agent 19.6%→22.8% 等）是**这对运行的差值**，不是模型间比较，
   更不是「换更强模型」的效果。
3. **A/B vs DexAtlas（同一轮内）**：A/B 最多两轮检索、无工具循环；
   agent 多轮工具循环。token 形状不同是执行形状的成本，不是答案质量的陈述
   （报告披露保留）。

**历史配置**：三轮各自的逐配置预算均以 trace 的 `max_tokens` 字段为准；
trace 未记录的维度（如端点侧限流、当日的网络延迟）标 **unknown**，不倒推、不补造。

---

## 4. 完整测量的说明

`scripts/refresh-report-figures.py --check` 的完整测量（需三后端 + fixtures +
Pillow + git tags 全部就位）已在配置齐全的环境执行，结果与本报告 §1.4 的
部分运行结论一致：报告数字与当前树相符。任何后续 `src/` 或测试改动都必须
按 CLAUDE.md 的顺序重跑：改代码 → `ruff format` → 完整测量 → 刷新报告。

---

## 5. 问题清单（M5 复核后）

### 阻断

无。三份 benchmark 可从原 trace 重算并逐字再生；文档与版本检查通过；
对外声明与证据一致。

### 重要

| # | 问题 | 证据/源码 | 核验方法 | 归属 |
|---|---|---|---|---|
| I-1 | 默认 agent 预算下，真实模型对开放问题 5/5 `budget_exhausted`，不产出带引用结论 | `src/dexatlas/agent/state.py:120`；`m4-e2e-run.md` §3、§5.3 | 配 MiniMax 端点 + 默认预算跑 demo 提问，观察终态 | M6（预算默认值收敛） |
| I-2 | 枚举型问题（如「列出全部加密算法」）在放宽预算后仍不收敛：模型反复 `search_symbols` 先读后答 | `m4-e2e-run.md` §5.3.2（14 迭代中 9 次 search_symbols） | 同配置重跑 Q1，检查迭代构成 | M6（停止策略/答案合成） |
| I-3 | stronger 与 real 两轮执行条件不等价（预算+批准门），差值只能按「对运行」陈述 | 本报告 §1.3、§3；`comparison-stronger-traces.json` 的 `max_tokens` 字段 | 重读本报告 §1.3 的核对命令 | 已收口（报告已如实披露） |
| I-4 | workbench 基准视图只加载 scripted + real 两份 trace，stronger 未入屏 | `src/dexatlas/workbench/benchmarks.py:39-40`（`SCRIPTED_TRACES`/`REAL_TRACES`） | `GET /api/benchmarks/m3` 返回的 measurements 长度 | 可选（M7 交付包时一并考虑） |
| I-5 | `projects.apk_path` 在数据库存绝对路径，影响未来「按路径复核证据」与证据包可移植性 | `src/dexatlas/core/storage.py:343`；`phase2-issue-list.md` 方案 A/B 段 | 读 schema 与写入点 | M7（证据包设计时定夺） |
| I-6 | macOS 无 CI 覆盖、无手工验证记录；平台声明只能是「Linux（CI）/ Windows（开发验证）/ macOS 未验证」 | `.github/workflows/ci.yml`（全部 ubuntu-latest） | 本报告 §2.3 | 对外文案已按此措辞；如需 macOS 支持需补验证 |

### 可选

| # | 问题 | 证据 | 核验方法 |
|---|---|---|---|
| O-1 | 大型 APK 基准未覆盖：真实 APK 样本、JADX/Apktool 规模表现、native 库、内存 | `docs/benchmarks/large-apk.md`；`docs/status.md` §4.3 | 需真实样本，等有样本时补测 |
| O-2 | 资源 ID 数值映射（`R.string.app_name` → int）未入索引 | `docs/status.md` §4.2 末段 | 读 `resources.arsc` ID 表，下一件事 |
| O-3 | Windows 长任务中 `TaskStore.save` 原子写偶发 `WinError 5`（疑杀毒/索引进程瞬时锁文件），已记录未复现 | `m4-e2e-run.md` §5.3.4 | 环境稳定性观察项 |
| O-4 | F8（死代码）已由 CI vulture 门禁覆盖，不再列为未完成工作 | `.github/workflows/ci.yml:45` | CI lint job |

---

## 6. 结论

M5 的目标达成：**对外承诺、代码、trace、演示四者一致**。
三份 benchmark 的每个数字都能从仓库内 trace 重算，三份报告都能用仓库内脚本
逐字再生；「更强模型」的误述已从报告、状态文档与交接文档中纠正为
「同一模型的预算与执行条件变化」；演示录像的 scripted provider 披露已放到
双语 README 首屏可见位置；README 路线图表的 Phase 2 版本号与实际发布一致。
声明清单 34 项中：已验证 30 项、受限 3 项（F6、F7、F11，边界均已写明）、
未验证 1 项（P3 macOS）。遗留问题全部入册（§5），无阻断项。

---

> **本报告的行号锚在哪棵树：** 全部锚在提交 **`100b191`**（本报告入库的那一次提交）上；
> 那棵树的测量指纹是 `sha256:f0336537…`。**本报告里的 `file:line` 只在 `100b191` 上
> 成立**，按当前树核会误报。
