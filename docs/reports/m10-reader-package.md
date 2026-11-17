# M10 读者验收包 —— 外部独立验收一站式入口

> **状态：验收包已就绪，等待读者执行。独立验收尚未开始；M10 未完成。**
>
> 本文件把 [M10 独立验收准备包](m10-acceptance-pack.md)整理成可直接交给一位
> **未参与实现**的读者的完整执行包：从这里出发，不需要再向作者要任何步骤。
> 验收记录填写[验收记录模板](m10-review-record-template.md)。
>
> 编写日期：2026-11-16（2026-11-17 定稿）· 验收 commit：**随邀请函给出**
> ——即 v1.0.0 发版 commit，完整 hash 写在[邀请函成稿 §2](m10-invitation-final.md)
> 的占位符里（由发起人填好）；不要使用移动的 `main` 分支
> · 评分基线：[作品集准备度评估](portfolio-readiness-2026-11-15.md)
> （GitHub 约 75% / Upwork 约 65%）与[复评](portfolio-readiness-2026-11-15-recheck.md)
> （GitHub 77.5% / Upwork 68.75%，均为作者自评，不是验收结论）。
> 两套数字用的是**同一组维度与权重**，复评是同一维度上的自评更新；
> 你的重评请与 **75% / 65%** 这一档对齐，并在记录里写明依据。
>
> **第一次来？** 先看一页版[读者执行摘要](m10-executive-summary.md)；
> 邀请与独立性要求见[邀请函成稿](m10-invitation-final.md)（发给您的就是这一份；
> [邀请函模板](m10-invitation-template.md)只供发起人填空用）。

## 0. 这份包是什么、不是什么

**是什么**

- 一条从 clone 到完成逐项打分的完整路径，每步给出可复制命令与预期输出要点。
- 一份独立性守则：你的判定只依据你自己执行命令得到的输出。
- 一份高风险声明清单：这些地方最值得怀疑，请优先核查。
- 一份评分与提交说明：怎么打分、怎么记录、交回什么。

**不是什么**

- 不是验收结论，也不是评分。所有数字都是作者自述或脚本生成，**在你亲自复现之前一律视为未验证**。
- 不替代[验收准备包](m10-acceptance-pack.md)的 40 项判定标准；本包只负责把路走通，判定以准备包为准。
- 不是安全审计：DexAtlas 是静态分析工具，不做动态分析、不定性恶意软件、不判断可利用性。

## 1. 读者须知（独立性要求）

1. **不采信作者自述。** README、案例、报告里的每一个数字，都要么由你重跑命令复现，
   要么记「未验证」。作者的解释可以听，但只能作为线索，不能作为证据。
2. **逐项按检查表判定。** 40 个验收项见[准备包 §2](m10-acceptance-pack.md)，
   三态判定（通过 / 不通过 / 未验证），没有「大概可以」。判定标准写在每个验收项里，
   按标准判，不按印象判。
3. **文档与实际不符，如实记录。** 预期输出和实际输出不一致时，以实际输出为准，
   把差异写成[卡点](#52-卡点记录格式)。文档缺步骤本身就是缺陷，不要替项目圆场。
4. **不要让作者代劳。** 作者可以澄清「这个词是什么意思」，不可以替你补命令、
   改环境或远程操作。凡是靠作者口头补充才走通的步骤，相关验收项判不通过。
5. **阻断项一票否决。** 19 个标 ★ 的验收项（清单见[准备包 §2.8](m10-acceptance-pack.md)）
   任何一个不通过，M10 即不通过，高分不能抵消。
6. **固定 commit。** 验收 commit 由验收发起人钉定，**随邀请函给出**（本轮是
   v1.0.0 发版 commit，完整 hash 在[邀请函成稿 §2](m10-invitation-final.md)）——
   不需要你另行索取，全程只验这一个 commit，所有记录写明 hash。不要用移动的
   `main` 分支做验收。
7. ** secrets 与第三方样本不入记录。** 记录中的个人路径、密钥、日志用 `<redacted>` 脱敏；
   不要把第三方 APK 或 `so` 文件传给任何人。

## 2. 开始之前：你需要什么

| 项目 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows 11 或 Linux | 两者有实测记录；**macOS 未验证**，使用 macOS 请如实记录 |
| Python | 3.12 或 3.13 | CI 在两个版本上运行 |
| [uv](https://docs.astral.sh/uv/) | 最新版 | 包与环境管理 |
| JDK | 21+ | 仅 JADX / Apktool 后端需要；没有 Java 也能用 Androguard 完成基础分析 |
| Docker | 可选 | 不想装 Python/JDK 时走 [Docker 路线](#32-路线-bdocker隔离环境自带后端) |
| `gh` CLI | 仅 fixtures 需要 | `scripts/fetch-fixtures.sh` 经 GitHub API 拉取 androguard 测试数据 |
| 网络 | 首次需要 | clone、依赖、后端下载；装好后分析本身可离线 |
| 磁盘 | 预留数 GB | 记录实际占用；不要写系统盘根目录 |
| 时间 | 冷缓存（含 clone、依赖、后端下载）首次 10–20 分钟；暖缓存（JDK/uv 已装）到第一份报告约 1.5–2 分钟；完整验收建议预留半天 | 暖缓存彩排实测约 1.5 分钟（Windows 11，[M8 演练](m8-install-rehearsal.md)另测 6.8 秒纯分析） |

## 3. 分步执行路径

每一步都记录：命令原文、退出码、关键输出、耗时。这是后面 A/B/D 组验收项的证据。

### 3.1 第 1 步：取得固定副本（验收项 A1）

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
git checkout v1.0.0
git status
```

预期：`git status` 干净；记录 commit hash（`git rev-parse HEAD` 的输出，
应与[邀请函成稿 §2](m10-invitation-final.md)钉定的那一串相同）、clone 来源 URL、日期。

### 3.2 第 2 步：环境准备（验收项 A2、A3）

**路线 A（推荐，可完成 CLI、案例、测试和契约检查）：**

```bash
uv sync --extra dev --extra analysis --extra mcp --extra demo
uv run dexatlas backends
```

预期：`uv sync` 退出码 0；`backends` 打印一张表，每个后端是 `available` 或
`not installed`。四个 extras 的分工见 [install.md](../install.md)。

> **M8-3（历史问题，已修复并合入）：** [install.md](../install.md) 的安装节过去
> 把最小安装（`uv venv` + `uv pip install -e ".[analysis]"`，不含 `mcp` 与
> `demo` extras）写在前面，容易被读成推荐路线；现在 install.md **先**给四
> extras 的 `uv sync`，最小路线明确标注为「只用 CLI 与 REST API 时够用」。
> 验收推荐上面的四 extras 路线；无论用哪条，记录实际命令。
> 若 install.md 现在的写法仍影响你的操作，记录为卡点。

后端不在 `PATH` 时按 [install.md](../install.md) 设置：

```bash
export DEXATLAS_JADX_PATH=/path/to/jadx/bin/jadx
export DEXATLAS_APKTOOL_JAR=/path/to/apktool.jar
```

Windows 下 `DEXATLAS_JADX_PATH` 指向 `bin\jadx.bat`。**没有后端不要停**：
继续往下走，这正好是验收项 A6 / G2 要核实的降级行为。

> **工作区位置（路线 A）**：连续执行 `analyze` / `manifest` / `search` 等命令时，
> 工作区是**当前目录下的 `.dexatlas/`**。请在克隆目录根目录内执行全部命令；
> 若换目录执行查询命令，需设置 `DEXATLAS_WORKSPACE` 指回原工作区，否则会得到
> 「No such project」（退出码 2）。

> **缺后端时的计数差异（A6 预告）**：在 jadx 或 apktool 不可用时重复分析，
> `classes` 与 `resource strings` 计数会低于 A4 的 5 classes / 1 resource string
> 基线（例如缺 jadx 时 5→4、1→0）——这是降级不是回归，记录实际值即可。

**路线 B（Docker，隔离环境，自带后端）：**

```bash
docker build -t dexatlas .
docker run --rm dexatlas dexatlas backends
```

预期：构建约 2 分钟（[M8 演练](m8-install-rehearsal.md)实测 2 分 16 秒）；
镜像内 JADX / Apktool 可用。容器内多个命令共享 workspace 时，用
`DEXATLAS_WORKSPACE=/workspace/ws` 统一（M8-2 已修复并合入：所有命令都带
`--workspace`/`-w`，这一项不再是已知限制；容器里仍建议用环境变量统一）。

### 3.3 第 3 步：首次分析 demo.apk（验收项 A4）

```bash
uv run dexatlas analyze examples/demo-app/demo.apk
```

预期（读者记录实际值；计数不同先核对后端是否齐全，再判定）：

```text
apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string
```

样本 sha256：`80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9`。

**后端缺失降级（验收项 A6）**：在 Androguard 可用、至少一个外部后端不可用的
情况下重复分析，预期仍以退出码 0 完成并产出报告，错误记录写明哪个后端
`not_installed`；不得崩溃或静默省略。

### 3.4 第 4 步：检索、证据与 locator 解析（验收项 B2–B5、C1–C3）

以下命令全部来自 [demo-app 案例](../case-studies/demo-app-walkthrough.md)：

```bash
uv run dexatlas manifest apk_80a8fe0e81204c9f
uv run dexatlas search apk_80a8fe0e81204c9f "Crypto"
uv run dexatlas search apk_80a8fe0e81204c9f "sk_live"
uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.MainActivity
uv run dexatlas xrefs apk_80a8fe0e81204c9f \
  "com.example.demo.MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;"
```

预期要点：

| 步骤 | 预期 |
|---|---|
| manifest | 包名 `com.example.demo`；version 1.0 (1)；sdk min 24 / target 34；1 个权限；3 个组件；MainActivity 与 SyncService 均为 exported 且无权限保护 |
| search `Crypto` | 命中 `com.example.demo.Crypto` 相关类与方法 |
| search `sk_live` | 一条字符串命中 `sk_live_2f8a91c4e7b3`；`Kind=string` 即表明命中来自字符串常量索引（search 输出无单独索引列，Kind 列就是索引条目类型：`class` / `method` / `field` / `string` / `resource`） |
| source | 第一行标明 `source kind: java`（或 smali 回退）与 locator，例如 `jadx:sources/com/example/demo/MainActivity.java` |
| xrefs | `1 call site(s), 1 call edge(s)`，调用点为 `classes.dex@34` |

**证据核查（C 组核心）**：打开 JSON 报告或证据包，任选 3 条 evidence 记录，
逐条核对工具、版本、locator、level 四个字段；理解三级语义——`verified` 是
确定性工具产出且 citation 可解析，`lead` 是线索不是结论，`insufficient` 是
证据不足；模型生成的文本永远不能是 `verified`。三级定义的出处是
[公共契约表 §证据三级](../architecture/public-contracts.md)；静态分析管线只
产生 `verified`，demo 报告 11 条 evidence 全为 `verified`、`lead 0` 是设计而非
缺失，`lead`/`insufficient` 由模型 claim 与人工复核产生。locator 解析规则见
[准备包 §2.3 C2](m10-acceptance-pack.md)。

### 3.5 第 5 步：三格式报告导出（验收项 A5、D1–D2）

```bash
uv run dexatlas analyze examples/demo-app/demo.apk \
  -o report.md --json report.json --html report.html
```

预期：三份非空文件，描述同一 project id。抽查 3 个数字（如 classes、methods、
call edges），确认 Markdown / JSON / HTML 三处一致。

**离线阅读（验收项 D1）**：把 `report.html` 复制到另一个目录，断网后双击打开；
页面应完整可读，无 `<script>`、无外部 CSS/JS/字体请求。

### 3.6 第 6 步：证据包导出与校验（验收项 C5–C6、D3–D5、G5）

```bash
uv run dexatlas export apk_80a8fe0e81204c9f -o evidence.zip
uv run --no-sync python -c \
  "from pathlib import Path; from dexatlas.reports.evidence_package import verify_package, verify_citations; p=Path('evidence.zip'); m=verify_package(p); print(verify_citations(p, m))"
```

预期：`verify_package` 通过（schema、路径穿越、SHA-256、项目/APK 绑定）；
`citations_resolved` 为 `True`，`citations_unresolved` 为空。

**迁移复验（C6）**：把 `evidence.zip` 复制到另一个目录（或另一台机器）再跑一次
校验，仍应通过；包内路径不得指向生成它的机器。

**数据边界（D3、G5）**：解压 `python -m zipfile -e evidence.zip evidence`，
打开 `evidence/manifest.json`，对照 `not_included` 声明检查包内实际文件——
证据包**不含** APK、全量源码、未被证据引用的字符串。包内只有裸树/DEX locator
时没有 `sources/` 目录，这是按构造解析，不是缺失（详见[准备包 §3.5](m10-acceptance-pack.md)）。

### 3.7 第 7 步：至少一个完整案例核对（验收项 B1–B6）

以读者身份通读 [demo-app 案例](../case-studies/demo-app-walkthrough.md)，
核对三件事：

1. 案例里的每条命令你能否照跑且结果一致（B1）；
2. 案例的结论、限制、下一步是否都能从你自己的输出复述出来（B6）；
3. 哪些是工具读到的事实、哪些是作者推断、哪些明确没覆盖（C3、B6）。

有余力再抽查 [obfuscated-app 案例](../case-studies/obfuscated-app.md)
（名称混淆下还能读到什么）与 [api-integration 案例](../case-studies/api-integration.md)
（REST/MCP 集成）。

### 3.8 第 8 步：契约与回归集抽查（验收项 E、F 组，可选但建议）

- **CLI 退出码（F1）**：0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、
  5 截断、6 跑完但没有可用的代码索引（`EXIT_NO_INDEX`，v1.0.0 新增；自动化脚本
  请用 `exit_code in (0, 6)` 或 `summary.index_complete` 区分）；至少实测
  0/1/2 各一次。语义见[公共契约表](../architecture/public-contracts.md)。
- **契约实测（F5–F6）**：

  ```bash
  uv run --no-sync pytest tests/test_public_contracts.py -q
  uv run --no-sync python scripts/verify-public-contracts.py
  ```

- **服务回归集（E1–E5）**：读[服务回归集](../benchmarks/service-regression-set.md)
  与[层级 1 scripted 演练](../benchmarks/m6-level1-scripted.md)，确认你能区分
  层级 0（确定性判分 20/20）、层级 1（scripted 替身演练）、层级 2（真实模型，
  已执行三轮完整重测，当前结果 49/60 = 81.7% 未达验收线，见
  [高风险声明清单](#4-需要重点核查的高风险声明)）各自证明什么、不证明什么。
- **故障恢复（G1–G4）**：坏输入（非 ZIP 当 APK）应退出码 2 且不留半成品；
  清空后端环境变量后分析仍完成并写明 `not_installed`；同一 APK 分析两次
  project id 相同。

### 3.9 第 9 步：按检查表逐项打分

打开[验收记录模板](m10-review-record-template.md)复制一份，按
[准备包 §2](m10-acceptance-pack.md) 的 40 项逐项填写三态与证据记录，
按[准备包 §5](m10-acceptance-pack.md) 的空白评分表给两平台打分。
填写说明见[本包 §5](#5-评分表填写说明与提交格式)。

## 4. 需要重点核查的高风险声明

以下是作者自述中**最值得怀疑、对结论影响最大**的声明。逐条给出核查方法；
核查结果直接写进对应验收项与卡点记录。

### 4.1 Agent 层级 2 未达验收线（对应 E2、E3，★）

作者自述：层级 2 真实模型批次（MiniMax-M3.1-Flash，冻结 20 题 × 3 轮）的时间线是
**首测 24/60（40.0%）→ 执行层修复 → 三轮完整重测 49/60（81.7%，逐轮 15/16/18），
仍未达验收线（每轮 ≥80%、三轮合计 ≥90%）**。当前事实以执行层修复后的完整重测
[m6-level2-retest4.md](../benchmarks/m6-level2-retest4.md) 为准（数字由
`scripts/m6_level2_retest4_report.py` 从三个 committed trace 重算——本文的
「trace」指**一次模型运行落盘的可复查记录**，定义见本节末的术语块）；首测
[m6-level2-real.md](../benchmarks/m6-level2-real.md)（24/60 = 40.0%，逐轮
45% / 40% / 35%，trace 合计 853,103 tokens 超出当次 800,000 授权）与中间复测
（[retest](../benchmarks/m6-level2-retest.md)、[retest2](../benchmarks/m6-level2-retest2.md)、
[retest3](../benchmarks/m6-level2-retest3.md)）是过渡数字，引用时不得替代 retest4。
无论引用哪一轮，验收结论都是「未通过、**B1 验收线**未关闭」。

> **术语（就地定义）：** 本文的「**B1 验收线**」= v1.0.0 发版阻断项 B1
> 「M6 层级 2 未达验收线」（每轮 ≥80%、三轮合计 ≥90%），定义见
> [v1.0.0 发版演练](v1.0.0-dry-run.md)。它与[验收准备包](m10-acceptance-pack.md)
> §2 判定表里的**验收项 B1**（B 组「完整案例」，★ 阻断项）是两回事：
> 本节讲的是前者，判定表里那一项讲的是「案例能否从头走到尾」。
>
> **术语（就地定义）：** 本文的「**trace**」= **一次模型运行落盘的可复查记录**，
> 即 `*-traces.json` 里的一条，含该次运行的输入、输出与 token 消耗。它既是上面
> 那些百分比与 token 数的**原始数据**（可由 `scripts/m6_level2_retest4_report.py`
> 重算复现），也是 E2 / E3 的核查对象。本节及其余各处的 trace 都是这个意思。

**核查方法**：确认 retest4 的数字由 committed trace 重算得出（可用
`scripts/m6_level2_retest4_report.py` 复现）；确认文档没有把 81.7% 说成达标，
没有只报成功子集；确认早期 40.0% 等过渡数字没有被当作当前能力引用；确认服务
承诺范围收窄且对外表述一致。

### 4.2 演示视频是 scripted provider，不是真实模型（对应 E3，★）

作者自述：README 中的演示 GIF/视频由仓库内置的 scripted demo provider 驱动
——无 API key、无真实模型。出处：[README.md](../../README.md) 演示一节。

**核查方法**：确认 README 与相关文档在展示演示处保留了 scripted 标注；
确认没有任何材料把 scripted 演示表述为模型能力。

### 4.3 benchmark 配置不等价，配置间对比不是模型质量结论（对应 E2、E3，★）

作者自述：层级 2 中三配置预算不同（DexAtlas 120000 tokens/任务，A/B 检索式
16384/请求），配置间差异同时反映执行条件与可见信息，**不构成对模型质量的
比较**；层级 1 scripted 成绩（冻结 20 题 A 4/20、B 4/20、DexAtlas 1/20）
度量的是 harness 机械，不是任何模型的解题能力。出处：
[m6-level2-real.md](../benchmarks/m6-level2-real.md)、
[m6-level1-scripted.md](../benchmarks/m6-level1-scripted.md)。

**核查方法**：抽查报告是否保留了免责声明；确认没有把 scripted 数字当作
通过率引用；确认预算差异已被披露而不是隐去。

### 4.4 已知限制与历史遗留（对应 G2、G3、A2，★）

- **M8-4（已在 v1.0.0 关闭）**：三个后端全部超时（或全部失败）时，分析状态曾为
  `completed`、退出码曾为 0。v1.0.0 用新退出码 **6（`EXIT_NO_INDEX`）**关闭了它
  ——这类运行现在返回 6，并在 `errors[]`、`summary.index_complete == false` 与
  `run.completeness = "partial"` 里同时说明；契约见
  [公共契约表 §8.1](../architecture/public-contracts.md)，引入它的提案见
  [exit-code-partial-read.md](../proposals/exit-code-partial-read.md)。复现与
  理由见 [M8 演练 §6](m8-install-rehearsal.md)。请核对：读到 6 时你是否仍会把它
  误读为「分析成功」。
- **M8-2（已修复并合入）**：容器内查询类命令缺 `--workspace` 选项的历史问题已修
  ——现在所有命令都带 `--workspace`/`-w`；容器里仍建议用 `DEXATLAS_WORKSPACE`
  统一工作区。
- **M8-3（已修复并合入）**：[install.md](../install.md) 的安装节现在**先**给验收
  推荐的四 extras 路线，最小安装被明确标为「只用 CLI 与 REST API 时够用」
  （见[本包 §3.2](#32-第-2-步环境准备验收项-a2a3)）。
- **macOS 未验证**：环境表只对 Windows 11 与 Linux 有实测记录。

**核查方法**：这些限制是否在对应文档中原样可见（而不是只藏在验收包里）；
降级行为（A6/G2）是否真的「记录为值」——错误写进报告而不是抛异常。

### 4.5 其他诚实性边界

- 案例与回归集全部使用 first-party 样本（`examples/`）；可疑形状的常量是
  无害占位符。工具不做恶意软件定性、不判断可利用性——案例里若出现越界结论，
  直接判不通过。
- `lead 0` 表示「分析没有在这一级落结论」，**不表示样本安全**。
- 测试与覆盖率数字来自 v1.0.0 发版的完整重测量；你验收的 commit 若与它不同，
  以你本机 `uv run --no-sync pytest -q` 的实际结果为准。

## 5. 评分表填写说明与提交格式

### 5.1 打分规则

- 六个维度、两套权重（GitHub / Upwork）与 0–4 分定义沿用
  [基线评估](portfolio-readiness-2026-11-15.md)；空白表在
  [准备包 §5.2–5.3](m10-acceptance-pack.md)。
- 基线是 GitHub 约 75%、Upwork 约 65%；[复评](portfolio-readiness-2026-11-15-recheck.md)
  的 77.5% / 68.75% 是同一组维度与权重下的作者自评更新，不是新的权重基准——
  你的重评请与 75% / 65% 这一档对齐，并在记录里写明依据。
- 等级含义：0＝未见证据；1＝初步证据；2＝局部可用、仍有实质缺口；
  3＝在声明环境内有完整演示或复现记录；4＝在限定范围内经过评审并有边界验证。
  4 不表示软件无缺陷。
- 每项贡献 = 分值 ÷ 4 × 平台权重；六项求和即平台总分，保留一位小数。
- **两个平台分别 ≥90% 才算达到 M10 评分目标**；平均分不能替代。
- **分数不能抵消阻断缺陷**：证据链断裂、数据隔离失败、真实模型披露不实、
  首次安装有阻断缺陷——任一存在即判 M10 不通过（见[准备包 §5.4](m10-acceptance-pack.md)）。
- 打分只依据你自己的验收记录；引用作者报告的数字时注明「作者自述，未独立复现」
  或附上你的复现命令。

### 5.2 卡点记录格式

每个卡点一条，格式与[准备包 §3.7](m10-acceptance-pack.md) 一致：

```text
卡点编号：
发生步骤（§3.x / 验收项 ID）：
环境（OS / Python / uv / JDK / Docker / commit）：
执行的命令：
退出码：
实际输出（完整原文，脱敏后）：
预期（引用文档哪一节、哪一句）：
是否可以重试：
是否阻断后续步骤：
附件路径（不入仓库）：
作者修复 commit：
复验结果（通过 / 不通过 / 未验证）：
```

### 5.3 提交格式

向验收发起人交回**一份**[验收记录模板](m10-review-record-template.md)的填写件，
包含：

1. **记录元数据**（模板 §1）：角色、commit hash、OS、Python/uv/JDK/Docker 版本、
   后端可用性、是否使用了作者补充步骤。
2. **首次读者会话记录**（模板 §2）：A/B/D 组逐项的命令、退出码、关键输出、耗时、
   卡点编号，以及总结栏（两段总耗时、需要作者补充的步骤、最影响理解/信任的一处、
   建议优先修复的三项）。
3. **卡点记录**（模板 §3）：每卡点一条，按 §5.2 格式。
4. **客户视角审阅备忘**（模板 §4）：三问结论、抽查的 3 条引用、红旗清单。
5. **源码评审记录**（模板 §5，仅当你是源码评审者）：逐里程碑结论与最终门禁。
6. **重评记录**（模板 §6）：GitHub / Upwork 两张评分表填满，附每项扣分原因。

原始日志、截图和证据包留在你自己的机器上，**不要**上传；仓库与提交记录只接收
脱敏后的文字。若验收发起人要求归档，按其指定渠道提交，不要自行 push 到仓库。

### 5.4 时间参考

- 到第一份报告：首次 10–20 分钟（含下载），暖缓存约 1.5–2 分钟。
  （[M8 演练](m8-install-rehearsal.md)在已就绪的会话工作树上实测约 30 秒，
  同一环境差异下两者都成立；以你自己的实测为准，明显超出预期按 §5.2 记卡点。）
- Docker 镜像构建：约 2 分钟。
- 完整案例（analyze 到 xrefs）：约 1–2 分钟。
- 40 项逐项判定 + 两平台打分：视抽查深度，建议预留半天。

## 6. 常见问题

**Q：某一步的预期输出和我的实际输出不一致，先改环境还是先记录？**
先记录。差异本身就是验收发现；只有确认是自己的环境问题（如后端没装、
PATH 没配）才修复后重试，并把两次输出都留下。

**Q：某个后端装不上怎么办？**
不要停。这正是 A6 / G2 的验收场景：确认分析仍完成、报告写明该后端
`not_installed`、没有崩溃或静默省略，然后把装不上的原因写成卡点。

**Q：我可以用作者提供的脚本一键跑通全部步骤吗？**
不可以。本包的每条命令都要你亲手执行；作者未在文档中公开的任何步骤，用了
就使相关验收项不能判通过。

**Q：遇到文档没写的报错？**
按 §5.2 记录卡点：完整命令、退出码、原始输出、你期望的依据（文档哪一节）。
然后问验收发起人，不要自行猜测项目的意图。

## 7. 自查脚本

作者侧提供 [m10-selfcheck.md](m10-selfcheck.md)：把验收包 40 项中可自动化的
检查写成脚本（`scripts/m10_selfcheck.py`）并留有自查记录。它可以帮你在
正式验收前发现文档、徽章、契约清单层面的明显缺口，但**不替代**你的任何
一项判定——需人工的项仍要你亲手执行并记录。
**注意自查记录描述的是哪棵树：** 该记录自带执行日期与它自己写明的 commit，
是**那一次自查的快照**，不是验收 commit 的现状；它里面的数字与你在验收
commit 上跑出来的不同，**以你的实测为准**，不要据此判「作者的数字造假」——
按 §5.2 记成卡点即可。

## 8. 配套工具：读者工具包

打分、回填与常见问答另有[读者工具包](m10-reader-kit.md)：空白评分表（维度与权重
逐字沿用[准备包 §5](m10-acceptance-pack.md)）、回填说明（写到哪、怎么交、耗时预期、
遇到问题找谁）与 FAQ。工具包同样不含任何验收结论，也不预填任何分数。
