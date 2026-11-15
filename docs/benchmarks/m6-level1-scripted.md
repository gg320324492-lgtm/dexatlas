# M6 层级 1 —— 服务回归集 scripted 演练记录

**状态：已完成（2026-11-15）。零模型调用、零费用。**
本文件落实 [服务回归集](service-regression-set.md) §6 的**层级 1**：用 scripted
provider 对冻结 20 题与完整 92 题旧题集各跑一次真实演练，证明 comparison 管线
（发题、工具循环、trace 落盘、判分）在冻结题上端到端可用。运行命令与逐题
原始记录见下文；报告数字全部由脚本从 trace 生成，未手改任何数字。

**免责声明（沿用 [comparison.md](comparison.md) 头部）：scripted provider 是
替身模型，不是模型基线。本演练的数字度量的是 harness 机械，不是任何模型的
解题能力；配置之间的差异不构成对模型质量的任何主张。层级 2（真实模型批次）
是另一项需要单独授权的测量。**

## 1. 演练配置

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-15 |
| 基线 commit | 本文件所在 worktree 分支（基于 `bcafc33`） |
| provider | `scripted`（零模型调用） |
| 配置 | A（源码文本检索）/ B（结构化检索）/ DexAtlas（agent），三配置同预算 |
| 每请求预算 | 2048 `max_tokens`，三配置一致 |
| 演练范围 | 冻结 20 题 1 轮 + 完整 92 题 1 轮 |
| 工作区 | `E:/Dexatlas/.scratch/m6-level1/ws`（.scratch 内，不入库） |
| trace | `.scratch/m6-level1/{service-regression-20,legacy-full-92}-traces.json` |

运行入口是 `scripts/m6_level1_drill.py`（新增）：它把冻结题 id 清单
（`benchmarks/m6_service_set.py`）接到 comparison harness 的按题过滤上，跑完
把两组 trace 落盘，并从 trace 生成逐题结果文件 `.scratch/m6-level1/m6-level1-report.md`。
复现命令：

```bash
export PATH="/e/Dexatlas/.scratch/backends/jadx/bin:$PATH"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
uv run --no-sync python scripts/m6_level1_drill.py \
  --workspace E:/Dexatlas/.scratch/m6-level1/ws --output-dir E:/Dexatlas/.scratch/m6-level1
# 仅从已落盘 trace 重新生成报告文件：
uv run --no-sync python scripts/m6_level1_drill.py \
  --workspace E:/Dexatlas/.scratch/m6-level1/ws --output-dir E:/Dexatlas/.scratch/m6-level1 --traces-only
```

为让 20 题子集可跑，comparison harness 增加了 `--task <id前缀>` 过滤
（`benchmarks/comparison/run.py`）：子集只决定"问哪些题"，reference 题号仍取自
全集编号，判分映射不变；该改动带 5 个回归测试（`tests/test_comparison_task_selection.py`，
按红→绿纪律先行编写，曾暴露并修正了"子集题号被重排"与"前缀多匹配"两个问题）。

## 2. 结果总览（数字由脚本从 trace 生成）

| 组 | 配置 | 判分通过 | 正确率 | 预算耗尽 | 答错 |
|---|---|---:|---:|---:|---:|
| 冻结 20 题（60 trace） | A | 4/20 | 0.200 | 15/20 | 1/20 |
| 冻结 20 题 | B | 4/20 | 0.200 | 15/20 | 1/20 |
| 冻结 20 题 | DexAtlas | 1/20 | 0.050 | 0/20 | 19/20 |
| 完整 92 题（276 trace） | A | 15/92 | 0.163 | 77/92 | 0 |
| 完整 92 题 | B | 15/92 | 0.163 | 77/92 | 0 |
| 完整 92 题 | DexAtlas | 5/92 | 0.054 | 0/92 | 87/92 |

八项指标（同一次 trace 计算，逐题表见 `.scratch/m6-level1/m6-level1-report.md`）：

| 指标 | 20 题 A | 20 题 B | 20 题 DexAtlas | 92 题 A | 92 题 B | 92 题 DexAtlas |
|---|---:|---:|---:|---:|---:|---:|
| `correct_answer_rate` | 0.200 | 0.200 | 0.050 | 0.163 | 0.163 | 0.054 |
| `evidence_grounding_rate` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| `unsupported_assertion_rate` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `false_positive_rate` | 0.500 | 0.500 | 0.950 | 0.000 | 0.000 | 0.946 |
| `tool_call_success_rate` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `token_consumption` | 1187 | 581 | 13328 | 1153 | 492 | 61325 |

92 题全量与 M3 已归档的 scripted 基线（[comparison.md](comparison.md)，trace
`docs/benchmarks/comparison-traces.json`）**逐题判分完全一致**（A 15/92、B 15/92、
DexAtlas 5/92），证明本次演练路径与既有基线同源。A/B 的 token 总量与基线
逐题相同；DexAtlas 每题恒定 +42 tokens，来源是 `get_project_status` 观察文本里
的时间戳、耗时、workspace 路径等动态字段的词数差（断言文本按 2000 字符截断，
长度不变），不影响任何判分结果。

## 3. 结果解读（scripted 机理，不是模型能力）

scripted provider 的脚本只有三步（A/B：两次检索 + 一次作答；DexAtlas：
一次工具调用 + 两次作答），它不看题集、不编答案，观察里有什么就答什么。
因此本演练的结果分布完全由脚本形态决定：

- **A/B 的"预算耗尽"不是超时或扣费**，而是替身脚本的应答步数（2 步）被
  检索重试耗尽后抛出 `ProviderError: the script ran out of answers`。
  92 题里 A/B 各 77 题、20 题里各 15 题走到这一步——这些题在 M3 基线里
  也是同样的空答形态，逐题判分与基线一致。
- **A/B 通过的题几乎全是"无法回答"类**：脚本第二次作答把观察原样复述，
  空观察产生空结论，恰好落在 expect_empty 题的判分通过区（13/15）。唯一
  的例外是 `manifest.package.demo` 与 `manifest.version.multidex`：检索把
  manifest 文本整体带回，复述文本里包含了期望子串。这是脚本形态与判分
  规则的巧合，不是检索质量。
- **DexAtlas 的"答错"是断言形态问题**：agent 脚本把工具观察（JSON 状态
  摘要）原样作为断言文本，判分器拿到的是工具状态而不是对问题的回答，所以
  20 题里 19 题判错。唯一通过的是 `xrefs.crypto-sign-call-site-count`
  （expect_count=1，恰好数出一条断言）。这与 M3 基线中 DexAtlas 5/92 的
  形态相同（基线多出的 4 题同样是 expect_count/expect_empty 的形态巧合）。
- **`evidence_grounding_rate` 全为 0**：scripted 结论不带 evidence_ids，
  grounding 判定按"无证据"计。这是替身模型的已知形态，comparison.md 已披露。
- **`false_positive_rate` 的组间差异**（20 题 A/B 0.500、DexAtlas 0.950）：
  分母是"答错的非空断言"。DexAtlas 每题都产出一条非空 JSON 断言且几乎全
  判错，分母大、分子大；A/B 的非空断言只出现在少数题上。这个比值度量的是
  脚本形态，不是模型纪律。

## 4. 与层级 0（确定性判分 20/20）的对照

层级 0（[服务回归集](service-regression-set.md) 附录 A 的
`benchmarks/run.py --task ... --json`，本 worktree 重跑确认 **20/20**）直接问
DexAtlas 自己的分析 API，无模型环节。层级 1 把同样的 20 题放进 comparison
harness，用 scripted provider 走完整的"发题→检索→作答→判分"链路。两组对照：

| 层级 | 回答者 | 20 题通过 | 含义 |
|---|---|---|---|
| 层级 0 | DexAtlas 分析 API 直接判分 | 20/20 | 题集与判定标准本身可满足，machinery 判分正确 |
| 层级 1 | comparison harness + scripted | A 4/20、B 4/20、DexAtlas 1/20 | harness 链路跑通；scripted 答案形态与题集期望不咬合 |

逐题对照（层级 0 全部通过；层级 1 中 A/B 通过 4 题：`manifest.package.demo`、
`partial.no-apktool-there-is-no-manifest`、`unanswerable.crypto-digestof-has-no-callers`、
`unanswerable.demo-declares-no-receiver`；DexAtlas 通过 1 题：
`xrefs.crypto-sign-call-site-count`）。20 题里没有任何一题在层级 0 与层级 1
的三个配置上同时通过——这个差距**全部来自 scripted 脚本形态与题集期望的
不咬合**，与层级 0 已验证的分析能力无关。

## 5. 发现的问题与对层级 2 的建议

以下只影响"scripted 演练能否作为参照系"，不影响层级 0 已验证的题集与
判定标准本身。

### 5.1 题集与判定标准：无需修改

20 题在层级 0 全部通过，`must_contain` / `expect_count` / `expect_empty`
三种判定都按文档 §3 的期望工作，无需澄清或调整。冻结纪律（§5）继续有效。

### 5.2 scripted 脚本形态与题集不咬合（如实记录的缺口）

- A/B 脚本的"复述观察"形态只能命中 expect_empty 题与个别全文包含题；
  16 道实证题（权限名、组件名、方法签名、调用者、字符串、资源出处）无一
  能靠复述观察通过。**这不算 harness 缺陷**：harness 的职责是忠实记录与
  判分，而 scripted 本来就不是为"答对实证题"设计的。
- DexAtlas 配置的 agent 脚本把工具观察原样作为断言，导致 19/20 判错。
  这暴露的是 `scripted_agent_provider` 的回答形态，而不是 agent 管线故障
  （工具调用成功率 100%，trace 完整）。

### 5.3 对层级 2（真实模型批次）的建议（仅建议，未授权执行）

1. **预算形态**：真实模型不会像 scripted 一样"两步耗尽"。92 题全量 + 20 题
   3 轮的批次仍建议按 [服务回归集](service-regression-set.md) §6 层级 2 的
   预算依据执行（以 comparison-real.md 的 token 量级为参考），单题
   `max_tokens` 建议 ≥ 4096（A/B 的 prose 回答在 2048 下已见复述超长截断）。
2. **agent 断言形态**：真实模型的 agent 回答应是结论性语句；建议在层级 2
   之前核对 `scripted_agent_provider` 与真实 provider 的回答进入判分器的
   路径一致（`answer_from_result` 对两者的处理相同），避免替身形态的误差
   被带进真实批次。
3. **判空题的对照价值**：13 道 unanswerable/partial 题在层级 1 里是 A/B
   唯一稳定的通过来源；层级 2 里它们对"模型是否编造"的检验价值不变，
   建议保持在其冻结集合内不动。
4. **成本核对**：本演练全程零模型调用；层级 2 启动前按既有流程另行申请
   授权与预算上限，本文件不构成授权。

## 6. 层级 1 的验收结论

- comparison 管线、判分与 trace 落盘在冻结 20 题与完整 92 题上端到端跑通：
  60 + 276 条 trace 全部落盘，判分、指标计算、报告生成全部由脚本完成。
- 92 题全量与 M3 scripted 基线逐题判分一致，确认演练路径未引入回归。
- scripted 结果不是模型基线；本演练不产生任何层级 2 的通过率预期。
- 层级 2（真实模型批次）继续等待单独授权。
