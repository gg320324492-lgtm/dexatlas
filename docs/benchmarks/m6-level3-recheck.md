# M6 层级复验 —— M6-③ 修复效果的零成本确定性复核

**状态：已完成（2026-11-15）。全程零模型调用、零费用：层级 0 走
`benchmarks/run.py` 确定性判分，层级 1 走 `scripts/m6_level1_drill.py` 的
scripted provider。本文所有数字由这两条链路直接产出，未手改；trace 与
JSON 原件在 `E:/Dexatlas/.scratch/m6-level3-recheck/`（不入库），本文只
引用其结论。**

本文回答一个问题：main @ `a541073` 上的 M6-③ 两项修复——
`1a1509c`（agent 回答契约与工具调优：否定答案不进 findings、过程注记移出
结论、计数逐项成条、完整 JVM 描述符、新增 `find_resource_declarations`
资源反查工具）与 `b956260`（`partial.*` 两题 `expect_backend_failure`
判定谓词，后端按题面配置真实禁用）——是否消除了
[层级 2 失败分析](m6-level2-failure-analysis.md) 归出的失败模式，以及
是否值得授权真实模型复测（层级 2 重跑）。

**措辞边界（沿用项目纪律）：零成本复验只能证明「判分语义与 harness
机械按修复意图工作、题集在无模型环节下可满足」。它不能外推为真实模型
的通过率，也不能证明模型会稳定遵循新的回答契约。**

## 1. 结论先导

| 层级 | 结果 | 对照基线 |
|---|---|---|
| 层级 0（确定性判分） | 冻结 20 题 **20/20**（full 18 题 + no-jadx/no-apktool 各 1 题分别单跑）；顺带全量 92 题 full 配置 **92/92** | 与 [m6-level1-scripted.md](m6-level1-scripted.md) §4 的层级 0 记录一致 |
| 层级 1（scripted 三配置） | A **3/20**、B **3/20**、DexAtlas **3/20**（基线 A 4、B 4、DexAtlas 1） | DexAtlas +2（正是 partial.* 两题）；A/B −1（同一题从「空答判过」变「判负」，是判定语义修订的预期效果，见 §4） |

- **层级 0 全绿**：题集与判定标准（含新的 `expect_backend_failure`）在
  真实禁用后端的条件下可满足，判分器对诚实失败记录判过、对编造判负。
  这是「修复在判分层与执行层生效」的直接证据。
- **层级 1 上 DexAtlas 从 1/20 → 3/20**，新增通过的两题正是
  `partial.no-apktool-there-is-no-manifest`（q067）与
  `partial.no-jadx-the-failure-is-recorded`（q066）：comparison harness
  现在按题面配置真实 Analyze（空串禁用后端），agent 的回答里带着
  `missing_backends: ["apktool"|"jadx"]` 与 `not installed` 字样，被
  `expect_backend_failure` 如实判过。
- **A/B 从 4/20 → 3/20**：失去的一题也是 q067。旧口径下 A/B 的 scripted
  空答恰好落进 `expect_empty` 的通过区；新口径下空答不再是正确回答的
  形状，判负。这与 [service-regression-set.md](service-regression-set.md)
  附录 B.4 的预告逐字一致，是**判定义务变严**，不是退步。
- **四种失败模式的可复验部分已按修复意图工作**（§5 逐项对照）；但
  scripted 层级 1 的 16 道实证题仍然全败，这是替身脚本「复述观察」形态
  与 `must_contain` 判分的固有错位（M3 基线同形态），**不能用来判定
  修复对真实模型的效果**。

## 2. 运行配置与复现命令

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-15 |
| 基线 commit | main @ `a541073`（含 `1a1509c`、`b956260`） |
| 层级 0 | `benchmarks/run.py --json`，真实后端（`DEXATLAS_JADX_PATH=E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat`、`DEXATLAS_APKTOOL_JAR=E:/Dexatlas/.scratch/backends/apktool.jar`） |
| 层级 1 | `scripts/m6_level1_drill.py --skip-full-set`（scripted，零模型调用） |
| 工作区 | `E:/Dexatlas/.scratch/m6-level3-recheck/`（.scratch 内，不入库） |
| 产物 | `level0-full.json`（92 题）、`level0b`（partial 单跑）、`l1/service-regression-20-traces.json`（60 trace）、`l1/m6-level1-report.md` |

层级 0 逐题命令（20 题前缀见 `benchmarks/m6_service_set.py`；~~`run.py`
的 `--configuration no-*` 过滤当前会把其它配置的题也选进判分集、但只
Analyze 被选配置的样本，从而在 `_run_tasks` 处 KeyError——见 §6，因此
no-jadx / no-apktool 配置的题用 `--task <id>` 单跑~~ **已修复
（2026-11-16）：`--configuration no-*` 现在按题面声明过滤任务集并只建对应
工作区，no-jadx / no-apktool 的题可直接按配置跑；回归测试见
`tests/test_comparison_configuration_routing.py`。当时记录：**）：

```bash
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
uv run --no-sync python benchmarks/run.py --workspace E:/Dexatlas/.scratch/m6-level3-recheck/level0 --json   # full 92 题
uv run --no-sync python benchmarks/run.py --task partial.no-jadx-the-failure-is-recorded --workspace E:/Dexatlas/.scratch/m6-level3-recheck/level0b --json
uv run --no-sync python benchmarks/run.py --task partial.no-apktool-there-is-no-manifest --workspace E:/Dexatlas/.scratch/m6-level3-recheck/level0b --json
```

层级 1：

```bash
export PATH="/e/Dexatlas/.scratch/backends/jadx/bin:$PATH"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
uv run --no-sync python scripts/m6_level1_drill.py \
  --workspace E:/Dexatlas/.scratch/m6-level3-recheck/l1-ws \
  --output-dir E:/Dexatlas/.scratch/m6-level3-recheck/l1 --skip-full-set
```

## 3. 层级 0 逐题结果（确定性判分）

full 配置 18 题全部通过；partial 两题在各自配置下单独验证通过。逐题：

| # | task id | 配置 | 判定 | 结果 |
|---|---|---|---|---|
| 1 | `manifest.package.demo` | full | must_contain `com.example.demo` | PASS |
| 2 | `manifest.permission.name-strings` | full | must_contain `android.permission.INTERNET` | PASS |
| 3 | `manifest.permission.count-obfuscated` | full | expect_count=3 | PASS |
| 4 | `components.exported.demo` | full | must_contain `com.example.demo.MainActivity` | PASS |
| 5 | `components.exported.obfuscated` | full | must_contain `a.a.a.a` | PASS |
| 6 | `overloads.method-identity.crypto-sign` | full | 完整 JVM 描述符 | PASS |
| 7 | `overloads.method-identity.descriptor-distinguishes` | full | 三方法完整描述符 | PASS |
| 8 | `ambiguity.declared-type-contradicts-body` | full | `Landroid/os/IBinder;` + `com.example.demo.provider` | PASS |
| 9 | `xrefs.crypto-sign-callers` | full | must_contain 调用者 | PASS |
| 10 | `xrefs.handler-handle-callers` | full | must_contain 调用者 | PASS |
| 11 | `xrefs.crypto-sign-call-site-count` | full | expect_count=3 | PASS |
| 12 | `strings.api-key.demo` | full | `sk_live_2f8a91c4e7b3` | PASS |
| 13 | `strings.telemetry-url.obfuscated` | full | 完整 URL | PASS |
| 14 | `resources.app-name.demo` | full | `app_name` + `DexAtlas Demo` | PASS |
| 15 | `wheresource.app-name-resource-file.demo` | full | `res/values/strings.xml`，不含 manifest | PASS |
| 16 | `unanswerable.crypto-digestof-has-no-callers` | full | expect_empty | PASS |
| 17 | `unanswerable.demo-declares-no-receiver` | full | expect_empty | PASS |
| 18 | `partial.no-apktool-there-is-no-manifest` | no-apktool | `expect_backend_failure("apktool")`，不得含包名 | PASS |
| 19 | `partial.no-jadx-the-failure-is-recorded` | no-jadx | `expect_backend_failure("jadx")` | PASS |
| 20 | `multidex.dex-file-count` | full | expect_count=2 | PASS |

**合计 20/20。** 附带观察：full 配置下 92 题全集 92/92，与 M3 归档基线
一致，说明 `1a1509c`/`b956260` 未扰动确定性链路的既有判定。

`partial.*` 两题的判过内容（层级 0 的 probe 直接读错误记录）与
`b956260` 的语义一致：`apktool: apktool is not installed or not on PATH`
形状的失败记录进入 findings，包名未出现。

## 4. 层级 1 逐题结果（scripted，三配置）与基线对比

60 条 trace（20 题 × A/B/DexAtlas 各 1 轮）。逐题判定（与 M3 committed
基线 `docs/benchmarks/comparison-traces.json` 及层级 1 基线
[m6-level1-scripted.md](m6-level1-scripted.md) 的差异一并列出）：

| ref | task id | A | B | DexAtlas | 相对基线变化 |
|---|---|---|---|---|---|
| q001 | manifest.package.demo | PASS | PASS | fail | 无变化 |
| q010 | manifest.permission.count-obfuscated | fail | fail | fail | 无变化 |
| q011 | manifest.permission.name-strings | fail* | fail* | fail | 无变化 |
| q015 | components.exported.demo | fail* | fail* | fail | 无变化 |
| q016 | components.exported.obfuscated | fail* | fail* | fail | 无变化 |
| q019 | overloads.method-identity.crypto-sign | fail* | fail* | fail | 无变化 |
| q041 | overloads.method-identity.descriptor-distinguishes | fail* | fail* | fail | 无变化 |
| q046 | ambiguity.declared-type-contradicts-body | fail* | fail* | fail | 无变化 |
| q022 | xrefs.crypto-sign-callers | fail* | fail* | fail | 无变化 |
| q027 | xrefs.handler-handle-callers | fail* | fail* | fail | 无变化 |
| q025 | xrefs.crypto-sign-call-site-count | fail* | fail* | PASS | 无变化（DexAtlas 基线即过） |
| q029 | strings.api-key.demo | fail* | fail* | fail | 无变化 |
| q034 | strings.telemetry-url.obfuscated | fail* | fail* | fail | 无变化 |
| q037 | resources.app-name.demo | fail* | fail* | fail | 无变化 |
| q083 | wheresource.app-name-resource-file.demo | fail* | fail* | fail | 无变化 |
| q071 | unanswerable.crypto-digestof-has-no-callers | PASS | PASS | fail | 无变化 |
| q077 | unanswerable.demo-declares-no-receiver | PASS | PASS | fail | 无变化 |
| q067 | partial.no-apktool-there-is-no-manifest | fail | fail | **PASS** | **A/B 由过变负；DexAtlas 由负变过** |
| q066 | partial.no-jadx-the-failure-is-recorded | fail* | fail* | **PASS** | **DexAtlas 由负变过** |
| q050 | multidex.dex-file-count | fail* | fail* | fail | 无变化 |

\* fail 形态为 `ProviderError: the script ran out of answers`（scripted
替身两步应答被检索重试耗尽），与 M3 基线同形态；`budget-exhausted` 计 32
题次，与层级 1 基线 A/B 各 15 的分布一致。

| 配置 | 基线（层级 1） | 本次 | 变化 |
|---|---:|---:|---|
| A | 4/20 | 3/20 | −1（q067 空答不再判过） |
| B | 4/20 | 3/20 | −1（同上） |
| DexAtlas | 1/20 | 3/20 | +2（q066、q067 判过） |

q066/q067 的 DexAtlas 通过内容：agent 拿到的是**真实按 no-jadx /
no-apktool 配置 Analyze 的工作区**（`_analyse_samples` 路由，后端路径置
空禁用），回答携带 `missing_backends: ["jadx"]` /
`errors: ["jadx: jadx is not installed or not on PATH"]`，命中
`expect_backend_failure` 谓词；q067 的回答中无包名（`must_not_contain`
同时生效）。

## 5. 与层级 2 四种失败模式逐项对照

失败模式编号与频次引自
[m6-level2-failure-analysis.md](m6-level2-failure-analysis.md) §4。

| 模式 | 层级 2 题次 | 修复（main） | 本次复验观察 | 结论 |
|---|---:|---|---|---|
| FM-1 否定/缺席题回答形态 | 9（q071、q077、q067） | `1a1509c`：否定结论移入 limitations（`_is_process_note`），expect_empty 题得到零 findings | 层级 0：q071/q077 PASS（零 findings 判过）；q067 改走 `expect_backend_failure` 后 PASS。层级 1：DexAtlas 的 q071/q077 仍 fail，但 fail 链是 scripted 把**工具观察 JSON** 当断言（1 条 findings），不是「否定写成 finding」——scripted 脚本不走 orchestrator 的结论分类 | **判分语义已按修复意图工作（层级 0 可证）；对真实模型是否生效，需层级 2 验证** |
| FM-2 计数题判分形状 | 7（q010、q050、q025） | `1a1509c`：INSTRUCTIONS 要求计数逐项成条；过程注记不进 findings | 层级 0：q010(=3)、q050(=2)、q025(=3) 全 PASS——判分器形状要求可满足。层级 1：q010/q050 DexAtlas 仍 fail（expected N got 1，scripted 单断言形态；q025 PASS 形态不变） | **判分面无误；「模型是否逐项成条」是 prompt 遵循问题，scripted 无法验证，需层级 2** |
| FM-3 枚举不完整 | 6（q041、q046） | `1a1509c`：INSTRUCTIONS 要求完整 JVM 描述符 `Class.name(descriptor)` | 层级 0：q041/q046 PASS（判分要求可满足，`must_contain` 的 JVM 描述符存在）。层级 1：DexAtlas fail（scripted 断言里没有枚举） | **判分要求本身可行；枚举行为属模型作答粒度，需层级 2，且失败分析已标注「不保证可达」** |
| FM-4 检索词不命中 | 5（q029、q034） | 未直接修复（检索层未改）；`find_resource_declarations` 只覆盖资源类 | 层级 0：q029/q034 PASS（真实 API 能取到常量）。层级 1：DexAtlas fail，scripted 检索词策略与真实模型不同 | **本次无法判定修复效果；q029/q034 是层级 2 复测的重点观察题** |
| （附）FM-5 harness 未移除后端 | 3（q066） | `b956260`：按题面配置真实 Analyze | 层级 1：DexAtlas q066 由负转正，工作区确实缺失 jadx | **已消除（harness 层）** |
| （附）FM-6 工具缺口 | 3（q083） | `1a1509c`：新增 `find_resource_declarations`，planner RESOURCES/GENERAL 意图均可调用 | 层级 0：q083 PASS（API 能给出 `res/values/strings.xml`）。层级 1：DexAtlas q083 fail——scripted agent 不调用该工具（脚本只调 `list_projects` 类无参工具），工具对 scripted 不可见 | **工具已接入 agent 工具面（`tool_executor.py:243`）；是否被真实模型使用需层级 2** |
| （附）FM-7 格式不符 | 2（q039、q022 各 1 轮） | `1a1509c`：INSTRUCTIONS 要求完整描述符 | 层级 0：q039/q022 PASS。层级 1：fail（scripted 无格式概念） | **需层级 2 验证 prompt 约束力** |
| （附）FM-8 基础设施超时 | 1（q039 1 轮） | 未改（属运行期风险） | 不适用（零模型） | 留待层级 2 运行记录 |

**总括**：能在「判分语义 + harness + 工具面」层验证的修复（FM-1 的判分
面、FM-2 的判分面、FM-5、FM-6 的工具接入、partial.* 判定）全部按意图
工作；依赖**模型行为**的部分（否定题留空结论的稳定性、计数逐项成条、
枚举粒度、检索纪律、工具选用）在零成本链路里不可验证——scripted
provider 不走 orchestrator 的结论分类，其「复述观察」形态与 M3 基线
逐题一致，这一层的 16 题全败是测量形态的已知属性，不是修复失效。

## 6. 本次发现的一个 harness 缺口（不影响结论，建议另行处理）

**状态更新（2026-11-16）：本缺口已修复。** `_selected_tasks` 现在按
`--configuration` 过滤任务集——只保留题面声明适用该配置的题，只建被选
配置的工作区；与 `--category` / `--task` 叠加时取交集，组合不出任何题时
以「no tasks selected」退出码 2 明确结束。回归测试
`tests/test_comparison_configuration_routing.py`（8 项）覆盖「no-* 配置只
路由适用题」「不适用组合明确报错」「正常全量路径不变」，在旧实现上先红
（复现：`--configuration no-jadx --task manifest.package.demo` 于修复前在
`_run_tasks` 处抛 `KeyError: (<Configuration.FULL: 'full'>,
<Sample.DEMO: 'demo-app'>)`），修复后全绿。CHANGELOG [Unreleased] Fixed
已登记。

以下为原始记录（修复前的现象，保留供追溯）：

`benchmarks/run.py` 的 `--configuration no-jadx`（或 `no-apktool`）只把
被选配置加入 Analyze 集，但 `_selected_tasks` 仍返回**全部 92 题**；
`_run_tasks` 随后在 `analyses[(Configuration.FULL, sample)]` 处 KeyError
（`benchmarks/run.py:115`）。层级 0 的 no-jadx / no-apktool 两题因此改用
`--task <id>` 单跑（结果不受影响）。该缺口不影响本次复验结论，但会让
「按配置跑子集」的直觉用法失败，建议后续单独修复并补回归测试。

## 7. 是否建议授权真实模型复测（层级 2 重跑）

**建议：值得授权，但按「验证修复、非达标冲刺」的口径执行。**

依据：

1. 修复的**机制层验证已闭环**：判分谓词、harness 配置路由、agent 工具
   面在层级 0/1 均按 `b956260`/`1a1509c` 的意图工作，层级 2 不再有
   「如实回答必判负」的测量盲区（q066/q067 已可判过）。
2. 失败分析 §8 的账目（修复全落地理论上限 47/60=78.3%，加超时重试
   48/60=80.0%）**尚未被任何测量证实或证伪**；层级 2 复测是唯一能给出
   真实数字的手段。当前基线 24/60=40%，距 80% 验收线差 24 题次，其中
   21 题次属三配置共有失败（判分形状/枚举/检索），9 题次属 agent 契约
   ——本次修复正对着这 9 题次与 partial 6 题次。
3. **成本约束**：按服务回归集 §6，层级 2 为冻结 20 题 × 3 轮 × 3 配置，
   参考上次批次 853,103 tokens（DexAtlas 711,617）。复测前需按流程单独
   申请授权与费用上限；本文件不构成授权。

复测设计建议（供授权方参考）：

- 同模型同预算（MiniMax-M3.1-Flash，A/B 16384、DexAtlas 120000，16 迭代
  / 40 步 / 600 秒，temperature 0），保证与基线可比；
- 重点观察题：q066/q067（修复直指）、q071/q077（否定题契约稳定性）、
  q010/q050/q025（计数成条）、q041/q046（枚举粒度，允许失败）、
  q029/q034（检索纪律）、q083（`find_resource_declarations` 是否被
  使用）、q039/q022（描述符格式）；
- 判读纪律：零成本结果与 scripted 数字**不得**写入任何对外达标结论；
  层级 2 报告仍由 `scripts/m6_level2_report.py` 从 trace 生成。

## 8. 复算方式

```bash
# 层级 0：附录式全量
uv run --no-sync python benchmarks/run.py --workspace E:/Dexatlas/.scratch/m6-level3-recheck/level0 --json
# 层级 1：重跑 drill（或 --traces-only 重出报告）
uv run --no-sync python scripts/m6_level1_drill.py \
  --workspace E:/Dexatlas/.scratch/m6-level3-recheck/l1-ws \
  --output-dir E:/Dexatlas/.scratch/m6-level3-recheck/l1 --skip-full-set
```

本文不包含需要 `refresh-report-figures.py` 重算的数字（未改动 `src/`，
覆盖率与套件计数不受影响）。
