# 提案：让退出码能分辨「跑完了，但没读到任何代码」

状态：**提案，未实施**。本文只给方案与版本化路线，不改任何实现。
关联：[公共契约 §8.1](../architecture/public-contracts.md)、[install.md 退出码表](../install.md)、[CHANGELOG](../../CHANGELOG.md)。
日期：2026年11月16日。

## 1. 问题重述

公共契约 §8.1 记录了一个已知缺口：当 JADX、Apktool、Androguard 三个后端
全部失败（例如 `DEXATLAS_TOOL_TIMEOUT_SECONDS` 过小导致三者全部超时），
但 Apktool 在被终止前已写出可解析的 `AndroidManifest.xml` 时——

- 流水线把项目记为 `completed`：只有 `classes` 为空**且** `manifest` 也为空
  才记 `FAILED`（`src/dexatlas/core/pipeline.py:334-336`）；
- `AnalysisResult.succeeded` 因此为真（`src/dexatlas/core/pipeline.py:110-112`）；
- `analyze` 走成功分支，**退出码 0**（`src/dexatlas/cli/main.py:334-352`）。

而 §1.2 与 `docs/install.md` 的退出码表对调用方的承诺是：**只看退出码就能
分辨残缺运行**。截断确实有专属的退出码 5（`src/dexatlas/cli/main.py:123`，
判定函数 `_truncated`，`src/dexatlas/cli/main.py:161-174`，只认
`ToolErrorCode.OUTPUT_TRUNCATED`，`src/dexatlas/core/models.py:42`）；
但「索引为空、所有代码后端都失败」的运行里，后端记录的是 `timeout` /
`exit_nonzero` 等错误码，不触发 5，于是与完整成功同为 0。只读退出码的
调用方会把「什么都没读到」误读为「读完了」。

三个传输通道的现状：

| 通道 | 能否分辨这种残缺 | 依据 |
|---|---|---|
| CLI 退出码 | **不能**（缺口所在） | 成功分支给 0，`src/dexatlas/cli/main.py:334-352` |
| JSON 报告 | 能 | `summary.index_complete == false`、`index_gaps[]`、`errors[]`（`src/dexatlas/reports/summary.py:23-34`、`src/dexatlas/reports/json_report.py:136`、`src/dexatlas/reports/json_report.py:40`） |
| REST | 能 | `ProjectResponse.errors[]`、`RunResponse.completeness == "partial"`（`src/dexatlas/api/app.py:188-220`、`src/dexatlas/api/app.py:229-252`；run 记 completeness 的判定在 `src/dexatlas/core/pipeline.py:349-353`） |

即：机器可读的补救通道已经存在，缺的只是退出码这一条「最廉价的通道」。
M8 按用户决策只记录、不修复；本文补上修复方案，供后续版本决策。

## 2. 目标与非目标

**目标**

1. 调用方只看 `dexatlas analyze` 的退出码，就能把「完整成功」与
   「跑完了但无可用的代码索引」分开。
2. 报告（Markdown/JSON/HTML）与 manifest 照常产出——残缺运行的数据仍然
   可查，退出码只是额外的信号，不收回任何现有输出。
3. 变更按 §6 显式版本化：epilog、两处退出码表、契约快照测试同步更新。

**非目标**

- 不改「部分后端失败但索引非空」的行为（索引仍在，错误与
  `completeness=partial` 已足够）。
- 不改「项目记为 `FAILED`（无 classes 且无 manifest）时 `analyze` 以
  退出码 1 结束」的现有映射（`src/dexatlas/cli/main.py:334-339`）——
  该映射是否合理是另一个独立问题，本文不动它。
- 不改 REST/JSON 的响应形状（除非所选方案本身要求）。
- 不引入自动重试、不放宽超时语义。

## 3. 候选方案

### 方案 A：新增专用退出码 6（`EXIT_NO_INDEX`）——推荐

**语义定义**：`6 = the analysis finished, but no symbol index could be
built`——运行正常结束、报告与 manifest 已写出，但所有读取 DEX 的后端都
失败了，索引为空。触发谓词（在 CLI 侧判定，紧随 `_truncated` 的风格）：

```python
def _no_index(result: AnalysisResult) -> bool:
    return (
        result.succeeded
        and result.project.class_count == 0
        and bool(index_gaps(result.project.errors))
    )
```

三个条件缺一不可：`succeeded` 把 `FAILED` 项目排除（那条路仍走现有
分支）；`class_count == 0` 表达「无可用电索」；`index_gaps(...)` 非空
（`src/dexatlas/core/models.py:94-113`，即 androguard——`INDEX_TOOL`，
`src/dexatlas/core/models.py:81`——的失败或 `ANALYSIS_FAILED`）把
「APK 本来就没有 DEX」的正常空索引排除，后者仍是 0。退出码判定顺序：
`not succeeded` → 1；`_no_index` → 6；`_truncated` → 5；否则 0
（no-index 先于 truncated：空索引是更强的信号）。

**对三个传输的影响**：

- CLI：新增常量 `EXIT_NO_INDEX = 6`（与 `src/dexatlas/cli/main.py:91-123`
  的五个常量并列）、epilog 追加一句（`src/dexatlas/cli/main.py:71-78`）、
  stderr 打一条与截断分支同风格的黄色警告、退出码 6。报告文件照常写出
  （`src/dexatlas/cli/main.py:354-369` 不变）。
- REST：无变化。REST 本就不经过 CLI 退出码，且 `errors[]` 与
  `completeness` 已能表达残缺。
- JSON：无形状变化。`schema_version` 仍为 3
  （`src/dexatlas/reports/json_report.py:32`）；`summary.index_complete`
  已携带同一事实。可选地在文档里提示调用方把 6 与
  `index_complete == false` 互相印证。

**向后兼容性**：按 §6 的分类，「加退出码」是兼容变更；0–5 的语义与触发
条件全部不变。严格说，0 的外延收窄了（原先落在 0 的这类残缺运行改落 6），
这正是本提案的目的；对「把 0 当成功」的既有调用方，这类运行本来就该按
失败处理，收窄是修正而非破坏。把非零一律当失败的调用方自动正确。

**迁移成本**：低。代码面 ≈ 一个常量 + 一个判定函数 + 一个分支 + epilog
一句话；文档面 = `docs/install.md` 退出码表与契约 §1.2 两张表同步；
测试面 = 快照 `EXPECTED_EXIT_CODES`（`tests/test_public_contracts.py:122-128`）
加一码，外加新回归测试（见 §6）。

### 方案 B：复用 `EXIT_FAILED`（3）

**语义定义**：把「三后端全失败、索引为空」归入「分析本身失败」。实现上
有两条路：让流水线在「无 classes 且有索引错误」时直接记
`ProjectStatus.FAILED` 并抛 `AnalysisFailed`；或保持流水线不动、CLI 在
成功分支里把该情形改判为 3。

**影响与兼容性**：第一条路改动深——项目状态变 `failed` 后，`publish_run`
被跳过（`src/dexatlas/core/pipeline.py:359-364`），REST 里该项目状态显示
`failed`（`src/dexatlas/api/app.py:188-220` 的 `status` 字段），且按
`src/dexatlas/api/app.py:380-390` 的现行逻辑，同 APK 再上传会触发重新分析；
「后端失败是值、运行照常出报告」的设计原则（`src/dexatlas/core/pipeline.py`
的既有注释与 §8.1 的描述）也被打破。第二条路（CLI 改判）不动状态机，但
让 3 的语义从「运行摔倒」扩成「运行摔倒**或**没读到东西」，两种失败原因
不同、处置不同（前者查环境，后者换参数/换 APK），混在一起违背
`src/dexatlas/cli/main.py:7-30` 阐明的「不同的空要分开」的原则。

**迁移成本**：高。状态机、发布语义、REST 消费方、重分析回路都要复核；
测试面覆盖 `ProjectStatus` 三态流转。

### 方案 C：复用 `EXIT_TRUNCATED`（5）

**语义定义**：把「索引为空」视为截断的极端情形，复用 5。

**影响与兼容性**：5 的现有契约是「运行跑完，但有步骤被上限**截短**」，
判定只认 `output_truncated`（`src/dexatlas/cli/main.py:161-174`）。超时
不是 `output_truncated`，要让它命中 5 必须扩宽判定谓词——这等于**更改
既有退出码的语义**，是 §6 明文的破坏性变更：今天收到 5 的调用方读到的是
「索引被截短但仍可观」，明天同一个 5 可能意味着「索引整个是空的」。把
「部分残缺」与「全空」合并进一个码，恰恰复刻了本提案要修的过度信任问题。
超时虽然也是「上限」（时间上限），但「被时间上限停在半路、还有部分产出」
与「所有产出通道全灭」是两种运行，不该共享一个码。

**迁移成本**：中。代码改动小，但契约损害大，且需同步改写 5 的全部文档
表述。

### 方案 D：JSON 报告新增顶层字段，退出码不变

**语义定义**：在 JSON 报告加顶层字段（如 `"index_usable": false`），
退出码维持 0。

**影响与兼容性**：加字段是纯兼容变更，成本最低。但 §8.1 指出的正是
「只看退出码」的调用方——JSON 报告里 `summary.index_complete`、
`index_gaps[]`、`errors[]` 已经完整携带这一事实（`src/dexatlas/reports/json_report.py:136`、`src/dexatlas/reports/json_report.py:40`），再加
一个同义字段是第三个名字说同一件事，缺口分毫未补。只适合作为方案 A 的
附带说明（文档里提示两通道互证），不值得单独立项。

### 方案 E：`ProjectStatus` 新增 `partial`

**语义定义**：在 `ProjectStatus`（`src/dexatlas/core/models.py:748-752`，
现为 `pending/running/completed/failed`）里加 `partial`，该情形记
`partial`，CLI 对 `partial` 给非零退出码。

**影响与兼容性**：破坏面最大。`status` 出现在 REST `ProjectResponse`
（`src/dexatlas/api/app.py:188-220`）、JSON 报告 project 块
（`src/dexatlas/reports/json_report.py:82`）与数据库中，所有做
`status == "completed"` 判断的消费方都要适配；且 run 级已有
`completeness == "partial"`（`src/dexatlas/api/app.py:229-252`），同名
不同物，词汇表会更混乱。方案 A 用退出码表达同一判断，不需要动状态机。

### 比较

| | 语义清晰 | 向后兼容 | 迁移成本 | 破坏面 |
|---|---|---|---|---|
| **A 新增 6** | 高：一种运行一个码 | 兼容（纯增量） | 低 | 仅 0 的外延收窄（即修复目标本身） |
| B 复用 3 | 低：两种失败混同 | 破坏（状态/发布语义变） | 高 | 状态机、REST、重分析 |
| C 复用 5 | 低：部分残缺与全空混同 | 破坏（改既有码语义） | 中 | 全体 5 的消费方 |
| D 仅加 JSON 字段 | 不解决缺口 | 兼容 | 最低 | 无，但也无收益 |
| E 状态加 `partial` | 中 | 破坏（状态枚举变更） | 高 | 全部 status 消费方 |

## 4. 推荐方案与理由

**推荐方案 A**：新增 `EXIT_NO_INDEX = 6`。

1. **对症**：缺口是「退出码通道分不出这种残缺」；A 是唯一让该通道本身
   变得可分辨、且不改动任何既有码含义的方案。
2. **有先例**：退出码 5 当年就是以同样的方式加入的——加常量、写 epilog、
   同步 `docs/install.md` 表、进契约快照测试（`docs/install.md:206-223`、
   `tests/test_public_contracts.py:450-462`）。A 完全复用这条已被验证的
   路径。
3. **兼容**：0–5 一个不动；把非零当失败的调用方立即受益；把 0 当成功的
   调用方中，受影响的恰是本应把这类运行当失败的那部分——收窄即修正。
4. **克制**：不碰状态机、发布语义与 REST/JSON 形状；B、E 的破坏面与
   本缺口的收益不成比例，C 则以破坏既有码语义为代价，均劣于 A。

## 5. 版本化与 CHANGELOG 措辞草案

按 §6，**加退出码是兼容变更**，在 CHANGELOG 说明即可，不需升
`schema_version` 或大版本；但因 0 的外延收窄，措辞要把「哪类运行不再
返回 0」写明。实施版本定为下一个次版本（语义化版本的 MINOR），实施时
将以下条目落入当时 CHANGELOG 的 `[Unreleased]`：

> ### Added
> - **退出码 6（`EXIT_NO_INDEX`）：分析跑完但无可用的代码索引。** 当三个
>   后端全部失败（如全部超时）而 manifest 仍可解析时，`dexatlas analyze`
>   过去返回 0；现在返回 6，并在 stderr 说明。报告与 manifest 照常写出，
>   JSON 报告的 `summary.index_complete == false` 与 `errors[]` 不变，可与
>   退出码互相印证。仅读退出码的调用方从此能把这类残缺运行与完整成功分开
>   （公共契约 §8.1 记录的缺口就此关闭）。
>
> ### Changed
> - `dexatlas analyze` 对「索引为空且所有 DEX 后端失败」的运行不再返回 0，
>   改返回 6。0–5 的语义不变。详见 `docs/proposals/exit-code-partial-read.md`。

同步义务清单（实施时一次做完）：

- epilog（`src/dexatlas/cli/main.py:71-78`）；
- `docs/install.md` 退出码表；
- 契约表 §1.2 的退出码表与 §8.1（缺口关闭后改写为「已于某版修复」或删除）；
- 契约快照 `EXPECTED_EXIT_CODES`（`tests/test_public_contracts.py:122-128`）；
- CHANGELOG 上述两条。

## 6. 测试计划（红 → 绿）

方案 A 的最小回归集（全部落在 `tests/test_public_contracts.py` 的既有
风格里，用 stub `Analyzer` 注入结果，参照
`tests/test_public_contracts.py:495-519` 与
`tests/test_public_contracts.py:522-550` 的写法）：

1. **红**：构造 `AnalysisResult`——`status=COMPLETED`、`class_count == 0`、
   `errors` 含 androguard 的 `timeout`、`manifest` 非空。`analyze` 应返回
   6。现行实现返回 0，测试先红；实现 A 后转绿。
2. **回归护栏（保持绿）**：
   - 同上但 `class_count > 0`（部分后端失败）→ 仍 0；
   - `class_count == 0` 且 `errors` 为空（无 DEX 的资源型 APK）→ 仍 0；
   - `status=FAILED`（无 classes 且无 manifest）→ 仍 1
     （`tests/test_public_contracts.py` 现有语义不回退）；
   - `output_truncated` → 仍 5（现有
     `test_cli_a_truncated_analysis_is_five` 不回退）；
   - 空索引与截断并存（`class_count == 0`、androguard `timeout` 且某后端
     `output_truncated`）→ 取 6（no-index 优先）。
3. **快照红**：`test_the_cli_exit_code_table_is_the_contract` 的
   `EXPECTED_EXIT_CODES` 加入 `6: "no symbol index could be built"`——
   epilog 未更新时先红，epilog 补齐后转绿。
4. **文档门禁**：`scripts/check-doc-citations.py` 对更新后的 §1.2/§8.1
   与 `docs/install.md` 保持 0 drift。

若最终选 B：红测试相同（期望 3），另需覆盖「项目状态转 `failed`、run 不
发布、REST `status == "failed"`、同 APK 重传触发重分析」四点；若选 C：需
先写「5 的语义变更」的显式破坏性变更公告再动码，测试面同上并额外覆盖
「部分截断仍为 5 但空索引也是 5」的新契约。

## 7. 风险与不做的事

**风险**

- 既有脚本若对这类残缺运行依赖「退出 0」，升级后会开始看到 6。缓解：
  CHANGELOG 的 Changed 条目写明触发条件与迁移方式（改判 `exit_code == 0`
  为 `in (0,)` 需求收缩，或补 `== 6` 分支）。
- 谓词边界：未来若出现「androguard 失败但 jadx 产出了部分类」的中间态，
  `class_count == 0` 不会触发 6——这正确：索引非空时残缺已由
  `completeness=partial` 与错误列表表达，无需退出码介入。
- 退出码表继续增长的成本：0–6 尚在「一张表能说清」的规模；若未来再加码，
  应连同 epilog 一起重新审视表述方式。

**不做的事**

- 不改 `FAILED` 项目退出 1 的现行映射（§2 非目标）。
- 不动 REST/JSON 形状与 `schema_version`。
- 不在本提案内实施任何代码改动；实施须另起变更，按 §5 的清单与 §6 的
  测试计划执行，并按 §6 规则落 CHANGELOG。
