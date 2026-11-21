# 三个已合并窗口交接尾巴的只读核对

> 核对日期：2026年11月18日 · 核对方式：只读（未改任何既有文件，本报告是唯一新增）
> 核对树：`claude/compassionate-newton-1953f9` @ `0a8e02e`（= `v1.0.0` tag 当前指向）。
> **本报告的 `file:line` 只在 `0a8e02e` 上成立。**
>
> 方法：逐条列「来源 → 交接里说的事 → 当前树的证据 → 判定」。判定只有三档：
> **已落实 / 未落实 / 进行中（待主会话最终测量落盘，属预期状态，不按缺陷计）**。
> 本轮没有跑 `refresh-report-figures.py`、没有跑完整套件、没有联网。

## 摘要

- **尾巴一（C13，引用检查器覆盖到报告层）：3 项核对全部已落实。** 8 份报告已登记、
  锚树与指纹声明齐全、43 处重锚无遗漏（实跑检查器，报告侧 0 发现）。
- **尾巴二（平台差异 36 处处置）：6 项已落实，1 项未落实——D13（契约活检断言按后端
  配置分叉）在处置提交与回归测试里都没有出现，是本类唯一的漏网条目。**
- **尾巴三（M10 第四轮读者走查）：R6 已落实（tag 已重打到 `0a8e02e`）；R3（G 组无读者
  命令）与 R4（工具包 6 处行号漂移）未落实；R1/R2/R5 的数字错位仍在，但属「待最终
  测量落盘」的进行时——`0a8e02e` 已把对外素材同步到 1690，执行报告的 fig/记录块
  还是 1649/`ffc546bc`，这正是主会话测量流程要收敛的最后一笔。**
- 最要紧的三条未落实项：**D13、R3、R4**（见 §4）。

---

## 1. 尾巴一：C13——引用检查器覆盖到报告层

来源：共享 notes `c13-report-citations-coverage.md`（提交 `04b5c6e` + `53e1e32`）。

| # | 交接里说的事 | 当前树的证据 | 判定 |
|---|---|---|---|
| C13-1 | 8 份 2026-11 复核报告进 `DOCS`，并按声明树登记进 `TREE_DOCUMENTS`（8 个 ref） | `scripts/check-doc-citations.py:129-139`（DOCS 8 条）与 `:154-166`（TREE_DOCUMENTS 8 条）逐条在，ref 与交接记录完全一致（48a56b5 / 3ef6676 / 9e1aa61×3 / ec52527 / d43369b / 2c456e0） | **已落实** |
| C13-2 | 5 份缺树声明的报告补「锚树 + 测量指纹」，denominator 补指纹 | 8 份报告文首均有锚树声明（抽查：outreach-first-read:19-20、local-vs-ci-gates:5-7、english-reader-review-2:8-10、denominator-and-tree-pass:10-12 等）；实跑检查器，8 份报告的 declaration 检查 0 发现（声明与树内记录一致） | **已落实** |
| C13-3 | 43 处报告引用重锚，drifted 应为 0 | 实跑 `check-doc-citations.py`：8 份报告按各自声明树解析，**报告引用 0 漂移**；全仓仅剩 1 条发现，且不是报告引用（见下方备注） | **已落实** |

**备注（唯一的 1 条 drifted）：** `v1.0.0-github-release-body.md` 的指纹声明报
wrong tree——文档引 `sha256:02d98a84`（`0a8e02e` 同步进去的），而 `v1.0.0` tag 树内
测量记录还是 `sha256:ffc546bc`（`docs/reports/phase1-execution-report.md:1101`）。
这不是 C13 重锚的遗漏：C13 交接第 4 节自己预警过「tag 未重打/测量未落盘时，release-body
会是下一条 wrong tree」。它随 §3 的 R1/R2（最终测量落盘 + tag 已重打）一起消除，
**不需要也不应该现在手改**。`tests/test_doc_citations.py` 30 条中因此红 2 条
（`test_every_citation_in_the_documents_still_says_what_it_says`、
`test_the_release_body_is_read_out_of_the_release_tree`），其余 28 条绿。

## 2. 尾巴二：平台差异 36 处处置

来源：`docs/reports/local-vs-ci-gates.md`（37 处：35 正向 + D36/D37 反向）与处置提交
`52ab305`（D1 的「完整性判据换掉」由更早的 `81336a5` + `45dd880` 处置）。

| # | 交接/审计里说的事 | 当前树的证据 | 判定 |
|---|---|---|---|
| P-1 | D1 测量门禁空转（含 `--check` 不完整时应返回非 0） | `81336a5` 换掉完整性判据（refresh-report-figures.py +206 行），`45dd880` 修自检轮收敛根因 | **已落实** |
| P-2 | D2/D4/D5/D6/D28/D34、D8–D12/D14/D15/D30、D16/D35/D37、D17–D19、D20/D21/D29、D23、D31/D32/D25/D27/D33/D7、D26、D3、D36、D24 的逐条改法 | `52ab305` 提交信息逐条点名（34 个唯一条目），diff 对应 22 个文件；`tests/test_platform_independent_gates.py` 实跑 **35 passed** | **已落实** |
| P-3 | D13：契约活检断言按「这次装没装后端」分叉，本地绿不代表 CI 绿 | **`52ab305` 提交信息没有 D13**；`verify-public-contracts.py:460-480` 的 MCP 断言仍是同一套固定判据，无「未装后端判需人工」分支；测试文件里也没有 D13 的判据测试 | **未落实** |
| P-4 | D22：版本声明检查依赖 clone 深度 | `CLAUDE.md`「Prerequisites the gates assume」写明全量 clone 与浅 clone 的行为（走报告建议的第一条路）；脚本侧的「浅 clone 明确失败」未做 | **已落实**（文档路线） |
| P-5 | D24：symlink 测试在 Windows 无权限时跳过 | `tests/test_apktool_smali.py:293-300`、`tests/test_jadx_source_paths.py:285-300` 已补 junction 等价物 | **已落实** |
| P-6 | D25：ffmpeg 依赖是白捡的 | `ci.yml:693-694` measurement job 显式装 ffmpeg；`CLAUDE.md` 前置条件清单点名 ffmpeg | **已落实** |
| P-7 | D3/D7：报告写明覆盖率在哪台平台、哪棵树上量 | `phase1-execution-report.md` 口径段（`52ab305` 写入）：「这个数字是在 Windows 上、三个后端都在的那套配置下量出来的…」 | **已落实** |
| P-8 | 审计 §2 相邻建议：新报告进检查器清单、重锚脚本范围对齐、报告索引登记 | 前两件由 C13 完成（DOCS 20 份、remapper 与检查器同源）；`docs/reports/README.md:159-163` 已登记 stale-number-scan-2 / local-vs-ci-gates / round-two-fresh-read | **已落实** |

**「不自动化/不属本轮」的 5 处判定是否成立：** 审计报告与处置提交里都没有以
「不自动化/不属本轮」为由跳过的条目——任务描述里的这个印象与两份材料不符。
逐条核对后，真正的缺口只有一个：**D13**。它既不在 `52ab305` 的 34 条清单里，也没有
对应回归测试；处置提交标题写「36 处处置」，实际有处置证据的是 35 处，差的正是 D13。

## 3. 尾巴三：M10 第四轮读者走查

来源：`docs/reports/m10-reader-walkthrough-4th.md`（提交 `3c1fef4`，合并 `9f3ceec`）。
报告自身声明：前轮 42 条中 41 条关闭或维持关闭，1 条（N11）有残余（即 R4）。

| # | 走查说的事 | 当前树的证据 | 判定 |
|---|---|---|---|
| R1（高） | fig 写 1643/1496，当前树实测更多；准备包 §6.3 声称「全部通过」已失真 | fig 现为 1649/1502/147、记录块 `passed=1646`、指纹 `ffc546bc`；而 `0a8e02e` 已把对外素材同步到 **1690（1541 快 + 149 集成）、指纹 `02d98a84`**——fig 与对外素材现在差着一次未落盘的测量。准备包 `:641-642` 的「全部通过」「测试数/文件表/指纹与当前树一致」两行文字未按建议改 | **进行中**（数字收敛待主会话测量落盘；§6.3 两行文字的改写仍未做） |
| R2（高) | `check-version-claims --base auto` 退出码 1，与清单「退出码 0」不符 | 实跑确认**仍退出码 1、6 findings**，全部是 outreach 素材写 1690 vs fig 记录 1649（同 R1 根因）。清单 `:417-419`「版本声明检查退出码 0」与准备包 `:640`「通过（0 新增）」未按建议补「以最终测量为准」的限定 | **进行中**（同 R1 批次） |
| R3（中） | G 组（含 ★ 阻断项 G3）在读者执行路径无可照抄命令；`DEXATLAS_TOOL_TIMEOUT_SECONDS` 在读者材料从未出现 | `m10-reader-package.md:301` 仍只有一句概括；读者包内 `DEXATLAS_TOOL_TIMEOUT_SECONDS` 出现 **0 次**；`3c1fef4` 之后没有任何提交触碰读者包 | **未落实** |
| R4（中） | 工具包 6 处 `file:line` 漂移（第三轮 N11 残余） | 6 处逐一实核全部仍在：`m10-reader-kit.md:167`→invitation-final:146（实际是「三态判定…」，目标在 :184-185）、`:175`→:153（目标在 :183）、`:250`→:54（目标在 :91）、`:239`→reader-package:44（目标在 :45）、`:337`→pack:501（目标在 :502）、`:22`→status.md:128（目标在 :130-133） | **未落实** |
| R5（低） | 对账表 A1 的「现值 1643 = 1496 + 147」已过期 | `m10-materials-alignment.md:59` 仍写「现值 1643 = 1496 + 147」——如今 fig 是 1649、对外素材是 1690，「现值」双过期；与 R1 同批收敛 | **进行中**（同 R1 批次） |
| R6（提醒） | `v1.0.0` tag 落后材料定稿树，发出前必须重打 | `v1.0.0` 现为 annotated tag（对象 `cd9d87f`），指向 **`0a8e02e` = 当前 HEAD**——重打已完成 | **已落实** |

**前轮 42 条**：走查 §1 的逐条复核表与「41 关闭 + N11 残余」的小结，经抽查
（N1、N9、N10、N11、N12、N15、57 条对账）与当前材料一致；N11 的残余就是 R4 的
6 处，全部未修。**没有发现「既没关闭也没记录去向」的 R 项**——R1–R6 在报告 §2 都有
处置建议，本节给出的是它们在主树的落实状态。

## 4. 判定汇总与最要紧的未落实项

**判定分布**（13 个核对点）：

| 判定 | 条目 |
|---|---|
| 已落实 | C13-1、C13-2、C13-3、P-1、P-2、P-4、P-5、P-6、P-7、P-8、R6（11 条） |
| 未落实 | **P-3（D13）、R3、R4**（3 条） |
| 进行中（待主会话最终测量落盘） | R1、R2、R5（3 条；随测量落盘与 §6.3 文字改写收敛） |

**最要紧的三条未落实项：**

1. **P-3 / D13（平台差异审计的漏网条目）**——契约活检的断言仍按「这次装没装后端」
   分叉：本地（常无 JADX/Apktool）验的是空答案契约，CI 验的是真答案契约，本地绿
   不代表 CI 绿。审计明说这是「本地那台机器从来没跑过带 JADX 的那几条断言」。
   **该由谁、改哪里**：主会话（或下一个处置窗口）在 `scripts/verify-public-contracts.py`
   把「源码后端未配置」从「换一套断言」改成「判需人工/明确跳过并记录」，并在
   `tests/test_platform_independent_gates.py` 补一条判据测试（该文件现在 35 条，正好补齐
   提交信息声称的 36 条）。
2. **R3（M10 验收的阻断项风险）**——G3 是 ★ 阻断项，但读者执行路径里没有可照抄的
   命令；按准备包自己的硬规则「凡是靠作者口头补充才走通的步骤，相关验收项判不通过」，
   读者极可能卡死在 G3。**该由谁、改哪里**：主会话在
   `docs/reports/m10-reader-package.md` §3.8 末尾增补「G 组怎么做」小节——G1
   （`uv run dexatlas analyze README.md`，预期退出码 2、无半成品）、G2（清空
   `DEXATLAS_JADX_PATH`/`DEXATLAS_APKTOOL_JAR` 后重析）、G3
   （`DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze examples/demo-app/demo.apk`，
   预期三后端 `timeout`、退出码 6、`summary.index_complete=false`）、G4（同 APK 连析
   两次比对 project id），变量名引 `docs/install.md` 的环境变量表。
3. **R4（工具包 6 处行号漂移）**——第三轮 N11 的残余全数仍在，而工具包自己要求读者
   「逐字核行号」；读者翻到 `invitation-final.md:146` 想看「交回渠道」、看到的却是
   「三态判定」，会直接得出「材料自相矛盾」的结论。**该由谁、改哪里**：主会话按走查
   R4 表格逐处改 `docs/reports/m10-reader-kit.md` 的 6 个行号，或把这些引用改成节引用
   （「邀请函 §六」等），一次免疫后续漂移。

**给主会话的一条流程提醒**：R1/R2/R5 与 §1 备注那条 release-body wrong tree 是同一笔
账——1690 那次完整测量的数字已写进对外素材（`0a8e02e`），但执行报告的 fig/记录块
（1649/`ffc546bc`）还没刷新。等主会话的测量落盘后，这 4 处会一起收敛；在那之前
不要手改其中任何一处数字。

**这三条未落实项已在本窗口处置——处置结果见 §5。** §1–§4 描述的仍是 `0a8e02e`
那棵树的只读核对结论。

---

## 5. 处置结果（本窗口，2026年11月18日）

> §1–§4 是对 `0a8e02e` 的只读核对；本节记录**这三条未落实项在本窗口怎么处置的**。
> 改动只落在 `docs/` 下（`scripts/` 与 `tests/` 一行未动，**源指纹不变**，主会话正在
> 跑的测量不受影响）。每条按「先核实 → 做了什么 → 为什么 → 证据」写。

### 5.1 D13——契约活检：本地绿不代表 CI 绿

**先核实（三问的答案）**

1. **断言是否真的分叉？** 分叉，但分叉的判据**不是「机器装没装后端」**，而是
   「这次分析里哪个后端参与了」与「端点有没有回答」：REST 的
   `X-DexAtlas-Source-* headers` 只在源码端点返回 200 时才记
   （`scripts/verify-public-contracts.py:342`），CLI 的 `source` / `resources` 两个
   调用点按 `project.tool_versions` 走两条不同的期望（同文件 `:558-568`）。所以一次
   实跑的**执行条数**依机器而定：三后端齐备 48 条、缺 JADX/Apktool 47 条——与契约表
   §7 记的两行一致。
2. **CI 两个 job 的期望是否不同？** **本来就不同**：`contracts` 用
   `--expect with-jadx`（`.github/workflows/ci.yml:529`），`contracts-without-jadx`
   用 `--expect without-jadx`（同文件 `:559`），后者把两个 Java 后端用**空值**关掉。
3. **装了后端的机器会不会把「没装后端」的结果也判过？** **不会。**
   `check-contract-records.py` 按「执行条数 + 分段 + 通过数 + 退出码」的**形状**去
   匹配记录行（`scripts/check-contract-records.py:312`），47 与 48 是两行、形状不同，
   所以落在哪一行就说明这次活检是哪种配置；期望与实到不符时它返回 **2**
   （同文件 `:332-345`，打印「the live run landed in the other configuration … The
   machine is not the one the record was written on.」）。把这段判据对契约表 §7 的
   记录**重放**一遍（只读：解析记录行 → 代入两次实跑的形状 → 走 `main()` 的同一段
   分支），四种组合的结论是：装齐的机器配 `--expect without-jadx` → **2**；没装的
   机器配 `--expect with-jadx` → **2**；对上时 → 0。

**判定：§2 的 P-3「未落实」部分成立。**

- **成立的部分**：活检脚本自己**不区分配置**——两种配置下都退出 0、都说「契约成立」。
   文档里写的「本地跑这一条」因此会给出一盏不代表 CI 的绿灯。D13 的危害陈述成立。
- **不成立的部分（审计的证据不全）**：「需人工」的判定**早就存在**——退出码 2 就是
   「这台机器不是记录里那台」；CI 侧也已分成两道门、期望不同。D13 缺的不是判据，
   是**接线**：读者与维护者的路径上只有 `verify-public-contracts.py`，没人问那句
   「你这台机器是不是 CI 那台」。

**做了什么**（纯文档接线）

- `docs/how-to-verify.md` §2.6 末尾与 `docs/how-to-verify.zh-CN.md` §2.6 末尾各加
  一段：写明活检在装没装后端两种配置下都退出 0（47 vs 48），给出
  `uv run --no-sync python scripts/check-contract-records.py --expect with-jadx`，
  并把三个退出码写成表——**0 = 契约成立且这台机器就是 CI 那台；2 = 契约成立但这台
  机器不是那个配置（需人工）；1 = 契约破了或记录过时**。末尾一句把它钉死：「2 不是
  失败，是『还没验』——把『没验到』报成『验过了』比报错更糟」。
- `docs/reports/m10-reader-package.md` 新增 **§9.2 契约活检与本机配置**：读者路径上
  的同一段（§3.8 的「契约实测」条目改为指向它）。

**为什么不改脚本**：判据已经在 `check-contract-records.py` 里；改
`verify-public-contracts.py` 的退出码会改掉契约表 §7 记录的那两个 0——那是**公共契约
的破坏性变更**，也会让 CI 的 `contracts-without-jadx` job 失配；补回归测试又必须动
`tests/`，而 `tests/` 在测量指纹的枚举范围内，会与主会话正在跑的测量冲突。**本轮只
改 `docs/`**，这是约束下唯一不欠账的路径。

**证据**：`uv run --no-sync python scripts/check-doc-citations.py` → `drifted: 0`；
`uv run --no-sync pytest tests/test_docs.py -q` → 65 passed。

### 5.2 R3——G 组（含 ★ 阻断项 G3）在读者执行路径没有可照抄的命令

**先核实**：走查说得对——读者包 §3.8 当时只有一句概括；`DEXATLAS_TOOL_TIMEOUT_SECONDS`
在读者材料里出现 **0 次**，只在 `docs/install.md:151` 的变量表与源码
`src/dexatlas/config/settings.py:36`（`tool_timeout_seconds: int = Field(default=900,
ge=1)`，`env_prefix="DEXATLAS_"` 拼出变量名）里。

**但走查给的 G3 预期与事实不符**：走查 §R3 建议写「预期三后端 `timeout`、报告仍产出、
**退出码 6**、`summary.index_complete=false`」。实测（2026年11月18日，Windows 11 +
JDK 21 + 三后端齐备）**退出码是 0**：1 秒超时下三个后端各记一条 `timeout`，但
androguard 已经把类表交出来了（`5 classes`），索引是**残缺**而不是**空**；退出码 6
（`EXIT_NO_INDEX`）说的是「跑完了，但**一个符号都没索引到**」
（`src/dexatlas/cli/main.py:377-389`、`src/dexatlas/core/models.py:94-113`），那个
分支用超时变量在 demo APK 上测不出来（androguard 总是先交出类表），它由契约活检脚本
用一个没有索引的分析触发。**读者按准备包 G3 的「记录实际退出码」记 0 即可**，并且要
一并记下 `index_complete=false`——这两件事合起来才是完整的读数。

**做了什么**

- `docs/reports/m10-reader-package.md` 新增 **§9.1 G 组故障恢复的可照抄命令**：G1
  （`uv run dexatlas analyze README.md`）、G2（`DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR=`
  后重析）、G3（`DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze
  examples/demo-app/demo.apk`）、G4（同 APK 连析两次 + `dexatlas projects`），每条给
  命令、预期退出码与预期输出。§3.8 的「故障恢复」条目改为指向它（等行数改写）。
- **超时变量第一次出现在读者材料里**，并写清三件事：它读在
  `src/dexatlas/config/settings.py` 的 `tool_timeout_seconds` 上、默认 **900**、
  取值不得小于 1；**它是环境变量、不是 CLI 参数**（`dexatlas analyze --help` 里找不到
  它）；以及「怎么验证」——把 `DEXATLAS_TOOL_TIMEOUT_SECONDS=1` 设上再跑一次分析，
  看三个后端是否各记一条 `timeout`。
- 四条命令的预期输出**都是当天实跑的**（临时工作区在 `.scratch/` 下，命令与原文见
  §9.1）：G1 退出码 2 + `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP
  archives` + `dexatlas projects` 列表为空；G2 退出码 0 + 两条 `not_installed`（`tools`
  里 `jadx`/`apktool` 为 `null`、`androguard` 有版本号，计数降到 4 classes / 0
  resource strings）；G3 退出码 0 + 三条 `timeout` + `index_complete=false` +
  `index_gaps` 一条 androguard；G4 两次同 id `apk_80a8fe0e81204c9f`、`projects` 一条。

**为什么追加在末尾（§9）而不是插进 §3.8**：读者包 §1–§8 的行号被四份走查报告按行
引用（`m10-reader-walkthrough*.md`），在 §3.8 插一节会把其后 200 余行的行号整体挪走，
那些**记录当时发现**的引用会指向别的内容——第三轮走查里有一行写的是「
`reader-package:312` 是**空行**」，那是它当时看到的行号，挪走之后这句话就不成立了。
所以新内容**追加在末尾**，§3.8 只改两条**等行数**的指向：**读者包现有行号一个不动**
（§1–§8 仍是 501 行，逐条核对见 §5.3 的证据）。

**留给发起人的一处**：准备包 G3 的措辞把「设置极短超时」与「退出码应为 6」并列，容易
被读成「超时会得到 6」。**本窗口没有改准备包的判据**（改验收判据要发起人点头），
但读者材料现在写清了实际值与理由。

**证据**：`check-doc-citations.py` → `drifted: 0`；`tests/test_docs.py` → 65 passed；
读者包新加的两个锚点（`#91-g-组故障恢复的可照抄命令`、`#92-契约活检与本机配置`）按
GitHub 的 slug 规则核对命中。

### 5.3 R4——工具包 6 处 `file:line` 漂移

**先核实**：把工具包里**全部** `file:line` 引用（不止审计点名的 6 条）逐条拉出来，
看它指到的那一行到底写了什么。审计点名的 6 条**全部仍在漂移**；此外还发现**第 7 处**
——工具包 `:344`（表格里「M10 独立验收尚未开始」那行的出处）引的是同一个
`docs/status.md:128`，审计漏了。

**做了什么：按内容重锚 7 处**（审计的 6 + 多出的 1）。判据是「那一行写了什么」，
不是「行号该往后挪多少」：

| 工具包位置 | 原来指向 | 那行实际写的是 | 改后指向 | 改后那行写的是 |
|---|---|---|---|---|
| `:22` | `docs/status.md:128` | 「### 4.0 Phase 3 进度（截至 2026-11-17）」小节标题 | `docs/status.md:132` | 「独立验收尚未开始，Phase 3 的退出标准未全部达成（……）」 |
| `:167` | `m10-invitation-final.md:146` | 「三态判定；每项写明命令、退出码、关键输出、耗时与路径。」 | `m10-invitation-final.md:184` | 「**交回渠道：直接回复本邀请所在的邮件线程……**（发起人若另指定渠道，会在发出前改写本行。）」 |
| `:175` | `m10-invitation-final.md:153` | 「读者验收包 §5.3 的提交格式交回发起人。」 | `m10-invitation-final.md:183` | 「……记录中涉及的个人路径、密钥等敏感信息请用 `<redacted>` 脱敏。」 |
| `:239` | `m10-reader-package.md:44` | 「按标准判，不按印象判。」 | `m10-reader-package.md:46` | 「把差异写成[卡点](#52-卡点记录格式)。文档缺步骤本身就是缺陷，不要替项目圆场。」 |
| `:250` | `m10-invitation-final.md:54` | 「「输入与结论是否清楚」「引用能否核查」「事实与线索能否区分」（C、D 组）。」 | `m10-invitation-final.md:91` | 「- 不要使用移动的 `main` 分支做验收。」 |
| `:337` | `m10-acceptance-pack.md:501` | 「每项贡献 = 分值 ÷ 4 × 该平台权重；六项求和即该平台总分。」 | `m10-acceptance-pack.md:502` | 「两个平台**分别**达到至少 90% 才算达到 M10 的评分目标；两平台平均分不能替代。」 |
| `:344` | `docs/status.md:128` | 同 `:22` | `docs/status.md:132` | 同 `:22` |

**与审计报告的两处出入**（按内容重锚的结果与审计的建议不完全一致，以内容为准）：

- 审计说 `:239` 的目标在 reader-package `:45`；按内容，那句「文档缺步骤本身就是缺陷，
  不要替项目圆场」在 **`:46`**（`:45` 是该条的标题行）。
- 审计说 `:22` 的目标在 status.md `:130-133`；按内容，「M10 独立验收尚未开始」在
  **`:132`**。

**证据**：工具包**行数不变（356 行）**——只改行内文字，所以引用工具包的其他文档的行号
一个不动；逐条复核引用的落点内容与上表「改后那行写的是」一致。

### 5.4 这一轮改动对仓库其他部分的影响

| 改动 | 影响 |
|---|---|
| `docs/reports/m10-reader-package.md`（§3.8 两条等行数改写 + 末尾新增 §9） | §1–§8 的行号**一个不变**；四份走查报告与工具包对它的引用全部仍然命中 |
| `docs/reports/m10-reader-kit.md`（7 处行内改写） | 行数不变（356 行），对它的引用全部仍然命中 |
| `docs/how-to-verify.md` / `.zh-CN.md`（§2.6 末尾各加一段） | 该文件 §2.6 之后的行号后移 23 行。**工作副本里唯一受影响的是 `docs/reports/new-pages-crosscheck.md` 的三处引用**——但那份报告自己声明了基线是 `e5060af`（「被校对象：`docs/how-to-verify.md`（427 行）」「**基线：** `e5060af`」），它的行号指的是**它校对时那棵树**，因此不改（改了反而会让它去描述一棵它没校对的树）。钉在树上的四份 11 月复核报告（`TREE_DOCUMENTS`）同理不动 |
| `scripts/`、`tests/` | **一行未动** → 测量指纹不变，主会话正在跑的测量与对外素材的测试数（1690）都不受影响 |

**核对**：`uv run --no-sync python scripts/check-doc-citations.py` → `drifted: 0`、
`unresolved paths: 0`；`uv run --no-sync pytest tests/test_docs.py -q` → 65 passed。
