# 怎么自己复核 DexAtlas 说的每句话（中文版）

> 这一页是 [`docs/how-to-verify.md`](how-to-verify.md) 的中文版，与主文档一一对应：
> 同样五类对外说法、同样每类落在哪里、同样该跑哪条命令、该看到什么数字。

这是一页给 GitHub 上的访客和潜在评审者的**门径**：这个项目对外说了哪些话，
每类话落在哪个文件里，你该跑哪条命令、该看到什么数字才能确认它是真的。

这页本身不重复结论，只讲**去哪里核**。凡是本页出现的数字，都标了它落在哪个文件、
哪一行——那是它唯一的来源；本页不手抄仓库里没有的数字。

复核要用的绝大多数材料都已经随仓库提交，所以**你不需要写一行代码**，
也不需要向作者要任何东西。

---

## 0. 三条使用说明

1. **这一页是中文版。** 主文档 [`docs/how-to-verify.md`](how-to-verify.md) 与本页
   内容一一对应（同样五类说法、同样落盘处、同样命令与预期输出）。仓库的文档目前
   中英混排（`docs/status.md`、`docs/analysis-provenance.md`、本文是中文；
   `docs/architecture/` 下的多数是英文），本页跟随它主要指向的那几份中文文档。
   README 的对应入口行上也注明了这一点。
2. **命令是按 Unix shell / Git Bash 写的。** Windows 上 PowerShell 的写法不同，
   但每条命令本身在两种 shell 里都能跑（`source` 是 bash 的）。
3. **skip 不等于通过。** 外部分析后端（JADX / Apktool）找不到时，相关测试会
   **skip** 而不是 fail；两个第三方集成样本没拉时同理。skip 的数量写在 pytest 的
   汇总行里——**请读那一行，不要只看退出码**（这条规则同样写在
   [项目自己的开发约定](../CLAUDE.md)里）。§2.3 给了两种环境下这一栏各是多少。

---

## 1. 这个项目对外有哪几类说法，各自去哪核

| # | 说法类别 | 落在哪里 | 怎么核 |
|---|---|---|---|
| 1 | **测试数与覆盖率** | [`docs/reports/phase1-execution-report.md`](reports/phase1-execution-report.md) 1.2 / 1.3 / 6 节，数字夹在 `<!--fig:…-->` 标记之间 | 跑 `scripts/refresh-report-figures.py` 重测（见 §2.8）；或跑 `tests/test_docs.py`，它拿报告里记录的那次测量的源码指纹和当前树比对 |
| 2 | **公共契约**（CLI 子命令、退出码、REST 端点、MCP 工具、报告 schema、版本政策） | [`docs/architecture/public-contracts.md`](architecture/public-contracts.md)，验证记录在同文件 §7 | 跑 `scripts/verify-public-contracts.py`（见 §2.6）；契约快照在 `tests/test_public_contracts.py` |
| 3 | **M6 层级 2 的得分**（层级 2 = 用真实模型跑冻结题集的那一层评测） | [`docs/benchmarks/m6-level2-real.md`](benchmarks/m6-level2-real.md)、[`docs/benchmarks/m6-level2-retest4.md`](benchmarks/m6-level2-retest4.md) 及窄验证各轮（窄验证 = 只在六道已知失败面上重跑的缩小复测，6 题 × 3 轮） | 跑对应的 `scripts/m6_level2_*_report.py` 从已提交的 trace 重算（见 §2.7）；缺 trace 时脚本不出报告 |
| 4 | **退出码语义** | [`docs/architecture/public-contracts.md`](architecture/public-contracts.md) §1.2 | 同第 2 条：契约活检脚本会真的触发每一个退出码 |
| 5 | **证据链与出处模型**（每条结论由哪个工具、哪个版本、从哪个字节位置读出来） | [`docs/analysis-provenance.md`](analysis-provenance.md) | 该文件 §4「读者如何自己验证一条结论」、§7「复现本文档的全部数字」给了逐步命令；§8 是一页速查表 |

第 5 类是这套材料的地基：**其余四类说的都是它的一个特例**。想判断一条结论有多硬，
先看 `provenance` 数组和 `Evidence.level`，而不是先看措辞。

---

## 2. 怎么自己跑一遍

### 2.0 前置：一份干净的检出

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
```

**每个 worktree / 每份检出都要自己的虚拟环境。** `uv sync` 建出来的 `.venv` 是一个
editable 安装，指向**建它的那份目录**；复用别人的 venv 会安静地测错代码。

### 2.1 装依赖

```bash
uv sync --extra dev --extra analysis --extra mcp --extra demo
```

四个 extra 的用途（见 [`pyproject.toml`](../pyproject.toml) 的
`[project.optional-dependencies]`）：

| extra | 装什么 | 为什么需要 |
|---|---|---|
| `dev` | pytest、pytest-cov、ruff、mypy、vulture | 跑测试和静态门禁 |
| `analysis` | androguard | 符号索引与交叉引用。**只装 `uv sync` 的话 Androguard 不可用**——分析照常完成，但没有符号索引 |
| `mcp` | Model Context Protocol SDK | MCP server（契约活检会用到） |
| `demo` | pillow | 演示素材的渲染与自检（`tests/test_docs.py` 少了它会 skip） |

**正常会看到什么：** uv 解析依赖并把 `.venv` 建好，退出码 0。

### 2.2 装分析后端（JADX / Apktool）

```bash
bash scripts/install-backends.sh    # 需要 java 在 PATH 上
```

脚本会把 **JADX 1.5.2** 和 **Apktool 2.11.1** 装到 `INSTALL_ROOT`（默认
`/tmp/dexatlas-backends`），并打印装了什么、装在哪。

想确认后端可用：

```bash
uv run dexatlas backends
```

**正常会看到什么：** 三行，`jadx` / `apktool` / `androguard` 的状态都是
`available`：

```text
              Analysis backends
┌────────────┬───────────┬──────────────────┐
│ Backend    │    Status │ Version          │
├────────────┼───────────┼──────────────────┤
│ jadx       │ available │ 1.5.2            │
│ apktool    │ available │ 2.11.1           │
│ androguard │ available │ 4.1.4            │
└────────────┴───────────┴──────────────────┘
```

若某一行不是 `available`，**去掉的测试会变成 skip，而不是 fail**（见 §0 第 3 条）。
（「去掉的测试」= 被 pytest 的 `-m` 过滤掉的用例；pytest 把它记作 deselected，不是 removed。）
这个表格的实物截图与读法见
[`docs/analysis-provenance.md`](analysis-provenance.md) §4.1。

### 2.3 跑测试套件

```bash
uv run --no-sync pytest -q
```

**正常会看到什么：** 一行点号和一行汇总。汇总行里三样东西要一起读：

* **收集到的测试数** —— 当前这棵树上应当是 **1632**（**1485** 快 + **147** 集成；
  「快 / 集成」= fast / slow 两套：fast 是 pytest 没标 `slow` 的用例，slow 是标了
  `@pytest.mark.slow`、要真调外部后端的集成用例）。  这三个数是报告里 `<!--fig:tests.total-->` / `<!--fig:tests.fast-->` /
  `<!--fig:tests.slow-->` 的值，由脚本生成，不由人手抄；你可以这样自己数一遍：

  ```bash
  uv run --no-sync pytest --collect-only -q -m "not slow"   # → 1485/1632 tests collected (147 deselected)
  uv run --no-sync pytest --collect-only -q -m "slow"         # → 147/1632 tests collected (1485 deselected)
  ```

* **passed 的数量** —— 应当等于收集数减去 skip 数，即**没有 failed、没有 error**。
* **skipped 的数量** —— **这一栏要能说清每一个 skip 的原因。skip 不是通过。**

**skip 从哪来。** 两个第三方集成样本（Apache-2.0 许可，随仓库分发二进制会让读者
无法核对来源）不在 clone 里，要自己拉：

```bash
bash scripts/fetch-fixtures.sh
```

不拉也能跑——套件会跳过用到样本的测试。**这两种跑法的差别就是这一栏：**

| 环境 | 汇总行 |
|---|---|
| 三后端齐备（Apktool、JADX、androguard 三个后端都在），**没**拉第三方样本 | `1605 passed, 27 skipped`（退出码 0）。27 个 skip 全是 `fixture not present; run scripts/fetch-fixtures.sh` |
| 三后端齐备，**拉了**第三方样本 | `1632 passed`、**0 skipped**——这就是报告里记录的那次完整测量（`<!--fig:suite.passed-->` / `<!--fig:suite.skipped-->`） |
**看到 `skipped` 非零时，别把它读成通过。** 退出码 0 只说明「没有失败」，
不说明「该跑的都跑了」。

（本机实测：整套约 7.5 分钟。后端版本、机器和后端是否在场都会影响它。）

`--no-sync` 是有意加的：它让 uv 不会顺手重新同步环境、把你刚装好的 `.venv` 换掉。

### 2.4 门禁一：文档里的行号引用还指得对吗

```bash
uv run --no-sync python scripts/check-doc-citations.py
```

**正常会看到什么：**（下面是这棵树上的实测输出）

```text
citations: 221
  naming a symbol: 162
  pointing only at a location: 59
unresolved paths: 0
drifted: 0

Every citation still says what it says.
```

**退出码 0。** 意思是：文档里 `file:line` 形式的引用，指的还是它说的那个符号。
`drifted: 0` 是关键那一行——非零就说明有引用漂了。

**这条门禁只扫四份文件**（`scripts/check-doc-citations.py` 里的 `DOCS` 清单）：
`docs/analysis-provenance.md`、`docs/architecture/public-contracts.md`、
`docs/reports/phase1-execution-report.md`、`docs/benchmarks/large-apk.md`。
**这两页都不在其中**——`docs/` 下其它文档的行号引用没有自动门禁，评审时值得自己抽查。

### 2.5 门禁二：对外的版本声明与仓库对得上吗

```bash
uv run --no-sync python scripts/check-version-claims.py --base auto
```

**正常会看到什么：**（下面是这棵树上的实测输出）

```text
facts:
  tags: handover-2026-11-10, phase1-acceptance-2026-10-21, v0.1.0, v0.1.1, v0.1.2, v0.1.3, v0.2.0, v1.0.0
  package version: 1.0.0
  changelog: 1.0.0, 0.2.0, 0.1.3, 0.1.2, 0.1.1, 0.1.0
  newest release: v1.0.0
documents read: 110
  skipped: v0.1.0: the report of that release has no measured coverage, so only its test count is checked
  skipped: v0.1.1: the report of that release has no measured coverage, so only its test count is checked
  skipped: v0.1.2: the report of that release has no measured coverage, so only its test count is checked
findings: 2 (2 already in 8f9ddcaf)
  docs/releases/v0.2.0.md:326  release-coverage  it says the coverage is 91.0%, the measured coverage is 91.6%
  CHANGELOG.md:1033  release-coverage  it says the coverage is 93.9%, the measured coverage is 91.6%

Every version claim matches the repository.
```

**退出码 0。** 它把仓库里**每一份 Markdown**（`documents read` 那行给出份数；仓库每
增删一份文档，这个数就变）里出现的版本号、发布日期、覆盖率和 tag 跟 git 事实
（tag 列表、`pyproject.toml` 的版本、CHANGELOG）逐条比对。

`findings: 2` 里那两条是**历史遗留、且已被登记在案**的（`2 already in 8f9ddcaf`）：
两份文档在描述**已发布的历史版本**时引用了当时的覆盖率，而门禁用当前树的覆盖率
作参照，所以差一个百分点。门禁知道它们是历史事实，不判失败——但它**把这两条摆在你
面前**，而不是藏起来。这是这个项目的习惯：**已知偏差要写出来，不要静音**。

### 2.6 门禁三：公共契约活检（需要三个后端）

```bash
uv run --no-sync python scripts/verify-public-contracts.py
```

这条脚本会**真的起一个 uvicorn 服务**、上传 `examples/demo-app/demo.apk`、
逐端点核对响应形状，再用 MCP 协议调一遍只读工具，最后把每个 CLI 退出码都触发一遍。
**它需要 JADX、Apktool、Androguard 三个后端都在**（§2.2）。

若后端不在 PATH 上，按本机情况把它们指出来：

```bash
export DEXATLAS_JADX_PATH="<jadx 启动器的路径>"
export DEXATLAS_APKTOOL_JAR="<apktool.jar 的路径>"
```

本项目的开发机上把两样装在项目内的 `.scratch/backends/` 下，用一份
`.scratch/env.sh` 一次引好（它还把临时目录也指到项目内）。**但 `.scratch/` 被
`.gitignore` 忽略、不随仓库分发**，所以访客要自己写上面那两行 export。

**正常会看到什么：**（下面是三后端齐备时的实测输出，节选；完整 48 行见脚本输出）

```text
== REST API over uvicorn ==
  PASS /health shape
  PASS /backends shape
  PASS POST /analyze -> 202 job
  ...
  PASS X-DexAtlas-Source-* headers
  ...
== MCP server over the protocol ==
  PASS tool list is exactly the read-only tools
  ...
== CLI exit codes ==
  PASS version exits 0
  PASS source with jadx answers 0 with the source it found, and a class the project does not hold answers 1 (empty)
  PASS resources with apktool answer 0 with the resources it found, and a name the APK does not declare answers 1 (empty)
  PASS unknown project exits 2
  PASS a failed analysis exits 3
  PASS a truncated analysis exits 5
  PASS an analysis with no index exits 6
```

**退出码 0。**

**为什么实跑是 48 项，不是 49？** 契约表 §7 写得很清楚：**49 是脚本里 `check()` 调用点
的静态条数**（28 REST + 6 MCP + 15 CLI），任何一次实跑都跑不满它——
`server comes up` 只在服务起不来时记，`X-DexAtlas-Source-* headers` 只在源码端点
返回 200 时记。所以：

| 可用后端 | 实跑执行条数 | 通过 | 退出码 |
|---|---|---|---|
| jadx 1.5.2 + apktool 2.11.1 + androguard 4.1.4 | 48（27 REST + 6 MCP + 15 CLI） | 48/48 | 0 |
| 仅 androguard 4.1.4 | 47（26 REST + 6 MCP + 15 CLI） | 47/47 | 0 |

**CLI 段的 `source` 与 `resources` 各有一个调用点按「这次分析里有没有对应后端参与」
分支**：有 JADX 就断言它真的打出了源码（退出 0），没有就断言它按契约降级（退出 1、
答案为空）。两种配置都过，才算门禁绿。

### 2.7 从 trace 重算 M6 层级 2 的报告

M6 层级 2 的每一个数字都由脚本从**已提交的 trace 文件**重算，报告里不手抄数字。
对应关系（每一行的「脚本」都以仓库根目录为工作目录运行）：

| 报告 | trace | 脚本 |
|---|---|---|
| [`benchmarks/m6-level2-real.md`](benchmarks/m6-level2-real.md) | `m6-level2-traces.json` | `scripts/m6_level2_report.py` |
| [`benchmarks/m6-level2-verify.md`](benchmarks/m6-level2-verify.md) | `m6-level2-verify-traces.json` + `m6-level2-retest3-traces-r1.json` | `scripts/m6_level2_verify_report.py` |
| [`benchmarks/m6-level2-narrow-verify-incomplete.md`](benchmarks/m6-level2-narrow-verify-incomplete.md) | `m6-level2-narrow-verify-traces.json` | `scripts/m6_level2_narrow_verify_audit.py` |
| [`benchmarks/m6-level2-narrow-verify2.md`](benchmarks/m6-level2-narrow-verify2.md) | `m6-level2-narrow-verify2-traces.json` | `scripts/m6_level2_narrow_verify2_report.py` |
| [`benchmarks/m6-level2-narrow-verify3.md`](benchmarks/m6-level2-narrow-verify3.md) | `m6-level2-narrow-verify3-traces.json` | `scripts/m6_level2_narrow_verify3_report.py` |
| [`benchmarks/m6-level2-retest.md`](benchmarks/m6-level2-retest.md) | `m6-level2-retest-traces.json` | `scripts/m6_level2_retest_report.py` |
| [`benchmarks/m6-level2-retest2.md`](benchmarks/m6-level2-retest2.md) | `m6-level2-retest2-traces.json` | `scripts/m6_level2_retest2_report.py` |
| [`benchmarks/m6-level2-retest3.md`](benchmarks/m6-level2-retest3.md) | `m6-level2-retest3-traces-r1/r2/r3.json` | `scripts/m6_level2_retest3_report.py` |
| [`benchmarks/m6-level2-retest4.md`](benchmarks/m6-level2-retest4.md) | `m6-level2-retest4-traces-r1/r2/r3.json` | `scripts/m6_level2_retest4_report.py` |

**第一轮窄验证为什么是「-incomplete」。** 那一轮的 trace 少了 1 条（53/54），所以
**完整报告脚本拒绝出报告**——这是被**刻意保留**的行为，不是缺陷。仓库里留的是
一份**审计件**（由 `scripts/m6_level2_narrow_verify_audit.py` 生成），它自己就写着
「本文件不是完整的窄验证报告；完整报告脚本对少于 54 条 trace 拒绝写报告，这个拒绝
被保留不动」（[`benchmarks/m6-level2-narrow-verify-incomplete.md`](benchmarks/m6-level2-narrow-verify-incomplete.md)
开头）。后续两轮是完整的，报告在 `narrow-verify2` / `narrow-verify3`。

**还有一份不是验收测量。**
[`benchmarks/m6-level2-verify.md`](benchmarks/m6-level2-verify.md) 是**单轮**验证，
它自己的标题就写着「结果判定（对照参考线，**非验收**）」——别把它当成 B1 的成绩单。
（「参考线」= 预先写下、只作对照比较的分数线，不等于「验收线」。）
**B1 的验收测量是 `m6-level2-retest4.md`**（三轮完整重测）。

例如重算三轮完整重测：

```bash
uv run --no-sync python scripts/m6_level2_retest4_report.py
```

**正常会看到什么：** 脚本重新生成那份 Markdown，**逐字节应当和仓库里的一样**；
文件没有变化。

**缺 trace 时脚本不出报告。** 这是这套材料的底线：**一次没跑完的测量不许变成一份
看起来完整的报告。** 把 trace 拿掉再跑，你会看到（下面是实测输出）：

```text
trace file is missing: .../docs/benchmarks/m6-level2-narrow-verify2-traces.json
the run is not complete; refusing to write a partial report
```

**退出码 1，且不写出任何文件。** trace 存在但条数不对、某个 (system, task) 配对的
trace 数不是 3、少了某个任务——同样拒绝，各有各的指名信息。

**一处需要如实说明的差别：**「拒绝出报告」这件事**在所有脚本上都成立**（都不写文件），
但**报错的形态分两种**：

| 脚本 | 缺 trace 时 |
|---|---|
| `m6_level2_narrow_verify_report.py`、`m6_level2_narrow_verify2_report.py`、`m6_level2_narrow_verify3_report.py`、`m6_level2_narrow_verify_audit.py`、`m6_level2_narrow_verify2_audit.py`、`m6_level2_verify_report.py`、`m6_level2_retest3_report.py`、`m6_level2_retest4_report.py` | **指名拒绝**：`SystemExit` + 一句说清哪个文件缺、为什么拒绝。退出码 1 |
| `m6_level2_report.py`、`m6_level2_retest_report.py`、`m6_level2_retest2_report.py` | **未捕获异常**：直接抛 `FileNotFoundError` 回溯。退出码 1，仍然不写文件 |

两种都**没有写出报告**，区别只在错误信息好不好读。前一种更符合脚本 docstring 里
那句话（「缺 trace 是指名问题的 `SystemExit`，不是回溯」），后一种没有做到——
评审时这是一个可以提的改进点，不是会写错数字的问题。

**重算不需要模型、不需要 API key、不需要联网**：trace 已经随仓库提交，脚本只读它。
（重新**采集** trace 才需要 `MINIMAX_API_KEY` 和三个后端；那是另一件事，见
[`benchmarks/m6-level2-retest4.md`](benchmarks/m6-level2-retest4.md) 自己的复现小节。）

### 2.8 重算报告里的数字（生成物）

```bash
uv run --no-sync python scripts/refresh-report-figures.py            # 测量并写回
uv run --no-sync python scripts/refresh-report-figures.py --check    # 只比较、不写入
```

**正常会看到什么：** 脚本跑一遍完整套件，把结果写回
[`docs/reports/phase1-execution-report.md`](reports/phase1-execution-report.md) 里
`<!--fig:…-->` 标记之间的数字，以及两份 README 顶部的徽章。
`--check` 走同一套测量，只比较、不写入，有出入就以非零码退出。

**测量的两个前提，缺一不可：**

* **测量必须是完整的。** 缺后端、缺样本的机器上量出来的覆盖率更低；脚本**不会**把
  那种残缺数字写进报告——它会告诉你缺了什么，然后保留原来的覆盖率。
* **同一份检出里，一次只跑一个测量。** 两个测量会互相覆盖报告，**后写完的那个会把
  前一个量出来的数字写进去**。脚本对此有硬保护：同一个 checkout 里已经有测量在跑，
  第二个会**直接不开始**：

  ```text
  Another measurement is already running in this checkout. Two of them would
  fight over the report, so this one did not start.
  ```

  **退出码 1。** 这次没有测量发生，报告也没有被改。

  这条保护只覆盖**同一份检出**。不同的 worktree / 不同的检出各有各的
  `.coverage` 与 `.scratch`，**天然隔离**，可以并行。

* **改完代码先 `ruff format`，再测量。** 报告记录的是**源码树的指纹**；格式化会移动
  行，测量早于格式化就描述了一棵已经不存在的树。

---

## 3. 哪些说法目前是「未达成 / 未验证」，请据此打折

（「未达成」= 量过但没过线；「未验证」= 从未测过。两者对读者的意义不同：前者是坏消息，
后者是不知道。）

这一节是本页最该被读到的部分。**下面每一条都是仓库自己写的**，链接指向原文。

| 说法 | 现在的状态 | 依据 |
|---|---|---|
| **M6 层级 2 的得分达标** | **未达。** 修复后三轮完整重测 DexAtlas **49/60 = 81.7%**（逐轮 15/16/18），**低于三轮合计 ≥90%（≥54/60）的验收线**（验收线 = 认定该里程碑通过所需的最低分数门槛）；r1 未达每轮 ≥80%（≥16/20）。结论：**未达标** | [`benchmarks/m6-level2-retest4.md`](benchmarks/m6-level2-retest4.md) 第 83、85 行；验收线（每轮 ≥80%、三轮合计 ≥90%）见 [`benchmarks/service-regression-set.md`](benchmarks/service-regression-set.md) §5「冻结纪律」（冻结纪律 = 调优前冻结题集与门槛，不许靠删掉做对的题来提高通过率）第 2 条与 [`roadmap/phase3-plan.md`](roadmap/phase3-plan.md) §5 M6 |
| **窄验证（六个已知失败面）达标** | **未达。** 窄验证二轮 DexAtlas 转通过 **2/6**、确定性修复题 **2/5**（转通过 = 原先判失败、这一轮改成通过；确定性修复题 = 预期修法确定、可判对错的题）；三轮（预算效率修复后）转通过 **3/6**、确定性修复题 **3/5**——门槛都是 ≥4/6、≥3/5，**两轮都未达** | [`benchmarks/m6-level2-narrow-verify2.md`](benchmarks/m6-level2-narrow-verify2.md) 第 61 行；[`benchmarks/m6-level2-narrow-verify3.md`](benchmarks/m6-level2-narrow-verify3.md) 第 61 行 |
| **M10 独立验收已完成** | **尚未开始。** 准备包就绪（40 项验收检查表 + 读者一站式入口 + 作者侧自查 43/43 通过），但**独立复现、准备度重评与 release candidate 仍未开始**，需要一位真实的独立读者来跑 | [`docs/status.md`](status.md) §4.0 的 M10 行；[`roadmap/ROADMAP.md`](roadmap/ROADMAP.md) 的 M10 行 |
| **Phase 3 的退出标准已全部达成** | **未全部达成。** M6 层级 2 未达标、M10 验收未开始 | [`docs/status.md`](status.md) §4.0 开头；[`roadmap/ROADMAP.md`](roadmap/ROADMAP.md) 开头段 |
| **agent 的回答是事实** | **不是。** 「模型的结论永远不是事实」——工具读出来的东西才是事实，且带能解析的引用；模型的结论只能是**待核的线索（lead）** | [`architecture/agent.md`](architecture/agent.md) §「The boundary between a lead and a finding」；[`architecture/evidence-invariants.md`](architecture/evidence-invariants.md) |
| **支持 macOS** | **未验证。** **Windows 11 与 Linux（CI）是实测平台**，**macOS 无 CI 覆盖、无手工验证记录**；不得把 CI 的 Linux 结果外推为 macOS | [`reports/m8-install-rehearsal.md`](reports/m8-install-rehearsal.md) §2 环境矩阵；[`reports/phase3-baseline.md`](reports/phase3-baseline.md) 的 I-6 条 |
| **成熟度评分 5.50/10 说的是今天这棵树** | **不。** 5.50 / 10 是**修复前**的基线，六个加权维度；今天的分数**要重跑才有** | [`docs/status.md`](status.md) §1 快照表 |

**怎么读这张表。** 这个项目对外说的每一句话，在它自己的文档里都带着一条边界声明。
上面这些**就是**那些边界——它们不是缺陷清单，是这个项目承诺的「说出测量看不到的东西」
的具体实例。评审时如果发现某句话**没有**对应的边界声明，那才是真正的问题。

---

## 4. 哪些数字是生成物，不许手改

**报告里的测试数、覆盖率、命令数、端点数、样本数，以及两份 README 顶部的徽章，
全部由 `scripts/refresh-report-figures.py` 写出来。**

它们在源文件里长这样——标记是 HTML 注释，渲染出来只有一个数字：

```text
<!--fig:tests.total-->1632<!--/fig-->
```

**改了会怎样？**

* **改了标记里的数字** —— `tests/test_docs.py` 会红。报告里同时存着**上一次测量的
  机器可读记录**（`<!--report-figures:{…}-->` 注释），其中有 `source_fingerprint`：
  那次测量所针对的源码树的指纹。指纹对不上当前树，
  `test_execution_report_coverage_figures_describe_the_current_code` 就会失败，并告诉你
  「覆盖率数字是在另一棵源码树上量出来的，去跑 refresh-report-figures.py」。
* **改了徽章里的数字** —— 徽章是 URL，写不了标记，所以它的数字是脚本从 URL 模式里
  匹配出来再写回去的。它同样是测量结果。

**正确的做法是改代码，然后重跑脚本**——不是改数字。跑完之后报告自检自然就绿了
（脚本把「报告自检」和「代码测试」分开测，所以**跑一次就够**）。

**同一类规矩还落在别处：**

* `docs/status.md` 的快照表里也有同样的 `<!--fig:…-->` 标记，同样由这个脚本写。
* M6 层级 2 各份报告的数字由 `scripts/m6_level2_*_report.py` 从 trace 重算（§2.7），
  同样不许手改；缺 trace 时脚本拒绝出报告。
* 各历史版本（v0.1.0 ~ v0.1.3）的测试数由脚本把那个 tag `git archive` 出来、
  用 `pytest --collect-only` 实测，**不随其它数字刷新**——因为它们描述的是历史状态。

---

## 5. 一条最短的复核路径

如果你只想走一遍最短路径，按这个顺序：

1. 读 [`docs/status.md`](status.md) §1 快照和 §4「还剩什么」——**先看边界，再看成绩**。
2. 跑 §2.4 的行号引用门禁和 §2.5 的版本声明门禁（两条都是只读的）。
3. 跑 §2.6 的契约活检（三后端齐备时），看它是不是 48/48。
4. 跑 §2.7 的 `m6_level2_retest4_report.py`，确认那份报告**逐字节可复现**。
5. 读 [`docs/architecture/public-contracts.md`](architecture/public-contracts.md) §7
   （验证记录）和 §8（已知限制）——**§8 是这个项目自己承认的破口**。

再往下，是 [`docs/analysis-provenance.md`](analysis-provenance.md) §4——
那份文档教你**怎么逐条核对一条结论**，包括「这个结论是谁用哪个版本的工具、从哪个
字节位置读出来的」。

---

## 6. 这页没有覆盖什么

* **它不保证你的机器上跑出来和这里一模一样。** 后端版本、JDK 版本、Python 版本
  不同，输出里的类数、方法数、交叉引用数会不同。`docs/analysis-provenance.md` §4.1
  写明了它自己那套数字是在哪套版本上量出来的。
* **它没有复核 API key、第三方样本的来源与许可**，那件事在
  [`CONTRIBUTING.md`](../CONTRIBUTING.md) 和 [`docs/install.md`](install.md) 里。
* **它没有替你读代码。** 契约表和报告里的 `file:line` 引用是给「愿意顺着点进去看」的
  评审者的导航，不是替他们看的结论。
