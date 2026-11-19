# M10 读者验收包 —— 外部独立验收一站式入口

> **状态：验收包已就绪，等待读者执行。独立验收尚未开始；M10 未完成。**
>
> 本文件把 [M10 独立验收准备包](m10-acceptance-pack.md)整理成可直接交给一位
> **未参与实现**的读者的完整执行包：从这里出发，不需要再向作者要任何步骤。
> 验收记录填写[验收记录模板](m10-review-record-template.md)。
>
> 编写日期：2026-11-16（2026-11-17 定稿）· 验收对象：**`v1.0.0` 这个 tag 所指的提交**
> ——发出前由发起人把 tag 重打到材料定稿的那棵树上，完整 hash 写在**随函发出的
> 那份邀请函**的 §2 里（仓库里同名文件是**填 hash 之前**的版本，见 §1.6）；
> **不要使用移动的 `main` 分支**
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
   v1.0.0 发版 commit，完整 hash 见**随函发出的那份邀请函**的 §2）——
   不需要你另行索取，全程只验这一个 commit，所有记录写明 hash。
   > **仓库里那份同名文件是「填 hash 之前」的版本**：填 hash 这一步发生在打
   > tag **之后**（tag 指的那棵树上，`docs/reports/m10-invitation-final.md` 的
   > §2 仍是占位符），所以**以随函发出的那一份为准**。你自己核的方式是
   > `git rev-parse v1.0.0^{commit}`——它的输出应当与随函那一串**逐字相同**。
   > 不要用移动的 `main` 分支做验收。
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
| 时间 | 冷缓存（含 clone、依赖、后端下载）首次 10–20 分钟；暖缓存（JDK/uv 已装）到第一份报告**按 1.5–2 分钟预留**；完整验收建议预留半天 | **1.5–2 分钟是预算档位，不是实测值**——两处实测锚点的口径不同、都比它快：[M8 演练](m8-install-rehearsal.md)「空目录 → 第一份报告，暖缓存」**约 30 秒**（同一次**首次分析本身 6.8 秒**）；[读者实走演练](reader-dry-run.md)实测冷缓存 **10 分 28 秒**、clone + `uv sync` **4 分 24 秒**、「重建 `.venv` → 第一份报告」**8 秒**（分析本身 3.8 秒）。**做快于 30 秒不是卡点**；口径说明见 §5.4 |

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
应与**随函发出的那份邀请函** §2 钉定的那一串相同——仓库里那份同名文件是填 hash
之前的版本，见 §1.6）、clone 来源 URL、日期。

### 3.2 第 2 步：环境准备（验收项 A2、A3）

**路线 A（推荐，可完成 CLI、案例、测试和契约检查）：**

```bash
uv sync --extra dev --extra analysis --extra mcp --extra demo
uv run dexatlas backends
```

预期：`uv sync` 退出码 0；`backends` 打印一张表，每个后端是 `available` 或
`not installed`。四个 extras 的分工见 [install.md](../install.md)。

**再抓两个第三方集成样本（跑测试套件要用）：**

```bash
bash scripts/fetch-fixtures.sh
```

> **为什么这一步不能跳**：集成测试要读两个 APK，而它们**不在仓库里**——随仓库分发
> 二进制，读者就无法从树里核对来源与许可 ✓，所以脚本把每一个是从哪儿来、什么许可
> 都写在了脚本里 ✓。**前置条件**：一台能上网的机器 + 一个**已登录的 GitHub CLI**
> （脚本用 `gh api` 取文件 ✓，`gh auth status` 能看到已登录即可 ✓）。
> **不抓的后果**：案例分析照常能做 ✓，但测试套件里 **27 个集成用例会 skip**
> （这 27 个是 3 个样本门控测试文件里依赖第三方 APK 的用例，静态可数；
> 三后端齐备但未取样本时，那 27 个 skip 的原因全部是
> `fixture not present; run scripts/fetch-fixtures.sh` ✓；取到之后套件**零 skip**
> ✓ ——**那才是报告里记录的那次完整测量** ✓）。
> **退出码 0 只说明没有失败，不说明该跑的都跑了** ✓。
> 套件总数与「快 / 集成」的拆分以
> [执行报告](phase1-execution-report.md) 的 `<!--fig:tests.total-->`、
> `<!--fig:tests.fast-->`、`<!--fig:tests.slow-->` 为准（重测一次换一次新，
> 材料不写死数字）——你只需核对**自己的汇总行里 `skipped` 是不是 0**。

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

预期：构建**约 2–20 分钟**（两个口径：层已就绪时约 2 分 16 秒 —— [M8 演练](m8-install-rehearsal.md)；
首台机器无层缓存、走代理下载时实测 **1099 秒 ≈ 18 分 19 秒** —— [读者实走演练](reader-dry-run.md)；
镜像约 1.3 GB）；镜像内 JADX / Apktool 可用。**这两个口径测的是你这台机器**——
CI runner 上另测过一段（`docker build` 这一步 **46 秒**），那是另一段，不是你本机的预期，
出处见 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)。容器内多个
命令共享 workspace 时，用 `DEXATLAS_WORKSPACE=/workspace/ws` 统一（M8-2 已修复并合入：
所有命令都带 `--workspace`/`-w`，这一项不再是已知限制；容器里仍建议用环境变量统一）。

**镜像里没有 `examples/`**（只有 `src/ pyproject.toml uv.lock README.md LICENSE`）→
要在容器里跑案例，得自己挂两个卷 ✓：

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$(pwd)/examples:/app/examples:ro" -v "$(pwd)/ws:/workspace" \
  dexatlas dexatlas analyze /app/examples/demo-app/demo.apk --workspace /workspace
```

> **Git Bash 的坑**：不加 `MSYS_NO_PATHCONV=1` 时，MSYS 会把 `-v` 后面的**容器
> 路径**改写成 Windows 路径**（`/app/examples` → `C:/Program Files/Git/app/examples` ✓），
> 挂载就指错地方了 ✓。

（读者实走演练实测：容器内三后端全 `available` ✓、分析退出码 0、约 8 秒 ✓，计数与本机一致 ✓）

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

> **当场记下证据**：CLI 没有「渲染某一次运行」的命令，而重复分析会把该项目的
> 最新一次运行换成新的一次 —— 所以**那一次 stdout 上的降级证据要当场抄下来**
> （后端状态表、`errors[]` 里的 `not_installed`），否则重跑后就找不回来了 ✓。
> 库里的记录仍在（`analysis_runs.errors` ✓），只是没有 CLI 命令把它渲染出来 ✓。

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

**证据核查（C 组核心）**：打开 JSON 报告（`report.json`）或证据包里的
`reports/report.json`，任选 3 条 evidence 记录，逐条核对工具、版本、locator、
level 四个字段。**这四个字段各在哪，是最容易读错的一处**：

- 记录的**顶层**只有六个键：`id` / `kind` / `level` / `summary` / `detail` /
  `provenance` ——**`level` 就在顶层**；
- **工具、版本、locator 在 `provenance[]` 数组里**，每个元素是
  `{"tool": …, "tool_version": …, "apk_sha256": …, "locator": …}`；
- **一条记录可能有不止一条 provenance**（demo 的 E-0004–E-0006 各有两条），
  逐条列出即可；
- REST 的 `GET /projects/{pid}/evidence` 是同一个形状；MCP 的 `get_evidence`
  返回的 `provenance` 是**只含 locator 的字符串数组**（那一侧没有工具与版本），
  工具与版本看 JSON 报告那一侧。

把三个字段连同 `level` 一起打出来，可以照抄这一条（`report.json` 由 §3.5 的导出
命令生成；还没导出就先跑那一条，或者把下面命令里的路径换成证据包里的
`evidence/reports/report.json`）：

```bash
uv run --no-sync python -c "import json;d=json.load(open('report.json',encoding='utf-8'));[print(e['id'], e['level'], [(p['tool'], p['tool_version'], p['locator'][:60]) for p in e['provenance']]) for e in d['evidence'][:3]]"
```

预期（实测，2026年11月19日，三个后端齐备）：

```text
E-0001 verified [('androguard', '4.1.4', 'androguard:AndroidManifest.xml')]
E-0002 verified [('apktool', '2.11.1', 'apktool:AndroidManifest.xml')]
E-0003 verified [('apktool', '2.11.1', 'apktool:AndroidManifest.xml#/application')]
```

再理解三级语义——`verified` 是确定性工具产出且 citation 可解析，`lead` 是线索
不是结论，`insufficient` 是证据不足；模型生成的文本永远不能是 `verified`。
三级定义的出处是[公共契约表 §证据三级](../architecture/public-contracts.md)；
静态分析管线只产生 `verified`，demo 报告 11 条 evidence 全为 `verified`、
`lead 0` 是设计而非缺失，`lead`/`insufficient` 由模型 claim 与人工复核产生。

**locator 解析（C2 ★）：一条可照抄的命令。** 解析 locator 只有一个入口——
MCP 的 `resolve_locator`（**REST 侧没有 locator 解析端点**，不必去找）。
下面这条命令把五类 locator 各解析一次：DEX 成员、manifest、裸树、文件级，
外加一个**解析不出来**的。照抄即可，不需要写代码：

```bash
{ printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"androguard:classes.dex#com.example.demo.Crypto"}}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"androguard:AndroidManifest.xml"}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"jadx:sources"}}}' \
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"jadx:sources/com/example/demo/MainActivity.java"}}}' \
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"androguard:classes.dex#com.example.demo.NoSuchClass"}}}' \
  ; sleep 3; } \
| uv run --no-sync dexatlas-mcp \
| uv run --no-sync python -c "import json,sys;[print('resolved=%s kind=%s locator=%s reason=%s' % (s['resolved'], s['kind'], (s['provenance'][0] if s['provenance'] else '(none)'), s['reason'])) for l in sys.stdin if l.strip() for d in [json.loads(l)] for t in [(d.get('result') or {}).get('content')] if t for s in [json.loads(t[0]['text'])] if 'resolved' in s]"
```

预期（实测，2026年11月19日，三个后端齐备）：

```text
resolved=True kind=java locator=jadx:sources reason=<工作区里 jadx\sources 的绝对路径>
resolved=True kind=java locator=jadx:sources/com/example/demo/MainActivity.java reason=<该文件的绝对路径>
resolved=False kind=None locator=(none) reason=com.example.demo.NoSuchClass is not in this analysis
resolved=True kind=None locator=androguard:AndroidManifest.xml reason=AndroidManifest.xml is a dex file of this analysis
resolved=True kind=None locator=androguard:classes.dex#com.example.demo.Crypto reason=com.example.demo.Crypto is in classes.dex
```

**五行的先后顺序不固定**（几个调用并发执行）——按 `locator=` 对号入座即可。

PowerShell 写法（同一台机器上实测通过，PowerShell 7 与 5.1 都可）：

```powershell
& {
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
  '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"androguard:classes.dex#com.example.demo.Crypto"}}}'
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"androguard:AndroidManifest.xml"}}}'
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"jadx:sources"}}}'
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"jadx:sources/com/example/demo/MainActivity.java"}}}'
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"resolve_locator","arguments":{"project_id":"apk_80a8fe0e81204c9f","locator":"androguard:classes.dex#com.example.demo.NoSuchClass"}}}'
  Start-Sleep -Seconds 3
} | uv run --no-sync dexatlas-mcp | uv run --no-sync python -c "import json,sys;[print('resolved=%s kind=%s locator=%s reason=%s' % (s['resolved'], s['kind'], (s['provenance'][0] if s['provenance'] else '(none)'), s['reason'])) for l in sys.stdin if l.strip() for d in [json.loads(l)] for t in [(d.get('result') or {}).get('content')] if t for s in [json.loads(t[0]['text'])] if 'resolved' in s]"
```

要解析别的 locator，就换 `arguments` 里的 `locator` 值（`project_id` 换成你要查的
那个项目 id）——一条一次。

**C2 的判据怎么用这张表**（判据全文见[准备包 §2.3 C2](m10-acceptance-pack.md)）：

| `resolved` | 是什么 | C2 怎么判 |
|---|---|---|
| `true`，`reason` 是工作区里的一个绝对路径，且 `text` 里**有内容**（`bytes > 0`） | **文件级 locator**：在工作区内解析到了真实文件 | 通过：核对那个文件确实存在（在 `.dexatlas/` 工作区里） |
| `true`，**没有可读的文件内容**（DEX 成员 locator 的 `text` 是 `null`；裸树 locator 的是空文本——`text.text` 为空串、`bytes` 为 0） | **DEX 成员 locator**（如 `androguard:classes.dex#…`）与**裸树 locator**（如 `jadx:sources`）：**按构造解析**——它指的不是某个文件，是这次分析里的一类位置 | 通过：**不是失败**，不要记成「解析不出来」 |
| `false` | 解析不出来（类不在这次分析里、后端没装、文件不在工作区……） | 单独列出来，记进记录 |

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

> **包里有几个文件**：zip 内是 **4 个条目** —— 3 份报告（`report.md` /
> `report.json` / `report.html`）加一份 `manifest.json`。CLI 打印的「4 files」指的是
> **归档自己的文件数** —— 完整输出形如 `4 files: 3 reports + 1 manifest` ✓，
> 说的是 zip 里打开能看到的数，**不是** `manifest.json` 里 `files` 清单的长度
> （清单里没有 `manifest.json` 自己：文件不能给自己算哈希 ✓）。
> 所以你数 zip 得到 4、CLI 也说 4 —— 一致 ✓；若只数 manifest 的清单会得到 3，
> 那是少算了一个 ✓。

**迁移复验（C6）**：把 `evidence.zip` 复制到另一个目录（或另一台机器）再跑一次
校验，仍应通过；包内路径不得指向生成它的机器。

**数据边界（D3、G5）**：解压 `python -m zipfile -e evidence.zip evidence`，
打开 `evidence/manifest.json`，对照 `not_included` 的三个键
（`apk` / `full_sources` / `unrelated_strings`）检查包内实际文件。
**包里能直接判的是两条**：**不含 APK**（zip 的条目里没有 `.apk`，
`manifest.json` 的 `files` 清单里也没有）、**不含全量源码**（包内没有
`sources/` 目录，`files` 清单里只有报告）。
**「未引用字符串」核的是 manifest 的声明**——`not_included.unrelated_strings`
写着「未被证据引用的字符串常量不进包」；包里**没有** APK 的完整字符串表可供
比对，读者核的是**这条声明与包内实际内容一致**（判据全文见
[准备包 §2.7 G5](m10-acceptance-pack.md)）。
包内只有裸树/DEX locator 时没有 `sources/` 目录，这是按构造解析，不是缺失
（详见[准备包 §3.5](m10-acceptance-pack.md)）。

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
  **0 / 1 / 2 三条现成命令**（照抄即可，退出码在后面）：

  ```bash
  uv run --no-sync dexatlas analyze examples/demo-app/demo.apk          # 0 成功
  uv run --no-sync dexatlas search apk_80a8fe0e81204c9f __no_such_term__ # 1 空答案
  uv run --no-sync dexatlas analyze README.md                          # 2 请求错误（非 APK）
  ```

  第 1 条要**先跑完 analyze**（第 2 条里的 project id 是它给的：`apk_80a8fe0e81204c9f`）；
  第 2 条输出 `No matches for '__no_such_term__'.`；第 3 条输出
  `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives`。
- **契约实测（F5–F6）**（可照抄的命令与三个退出码的含义见 [§9.2](#92-契约活检与本机配置)）：

  ```bash
  uv run --no-sync pytest tests/test_public_contracts.py -q
  uv run --no-sync python scripts/verify-public-contracts.py
  ```

- **REST / MCP / 报告 schema（F2–F4）**：这三项的判据都在
  [公共契约表](../architecture/public-contracts.md) 里。下面按 F2 点名的**六类关键
  端点各给一条命令**（上传 / 项目 / 运行 / 符号 / 源码 / 报告）；F2 的判据是
  「**抽查 3 个端点**」——你自选其中 3 个记录即可，不必六条全跑。

  **第一步：起 REST 服务。**

  ```bash
  uv run --no-sync uvicorn dexatlas.api.app:app --port 8000
  ```

  成功时日志里出现这一行，**它是「服务真的起来了」的唯一信号**：

  ```text
  INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
  ```

  > **端口被占用时的退路（这一处会静默失败，请照做）**：8000 被别的服务占着时，
  > uvicorn 会**先**打印 `Application startup complete.`（这句不作数）**再**打印
  > `[WinError 10048] error while attempting to bind`，然后自己退出；此时
  > `curl localhost:8000/health` **不报错**，返回的是**别人的**响应——本机实测
  > 8000 上跑着另一个 FastAPI 应用，`/health` 返回 `{"status":"healthy"}`、
  > `/projects` 返回 `{"detail":"Not Found"}`。照材料走的读者很容易把它写成一条
  > F2 的假卡点（「端点与契约表不符」），而实际上服务压根没起来。
  > **退路是换端口**：把上面那条命令的 `--port 8000` 改成 `--port 8011`；
  > 下面第二步的命令块用 `B=localhost:8011` 承载端口（**实测输出就是在 8011 上
  > 跑出来的**——本机的 8000 被别的服务占了），你把 `B` 改成自己的端口即可，
  > 响应形状与状态码一样。起好之后先确认服务身份：
  >
  > ```bash
  > curl -s localhost:8011/health
  > ```
  >
  > 期望（实测）：`{"status":"ok","version":"1.0.0","backends":{…}}`——**必须是
  > `"status":"ok"` 且带 `version` 与 `backends`**；返回 `{"status":"healthy"}`
  > 或 `{"detail":"Not Found"}` 就说明这个端口上**不是 DexAtlas**，继续换端口。

  **第二步：六类关键端点各一条命令**（`P` 是 §3.3 分析出来的 project id；`B` 是
  端口——按上面第一步的结果填 `8000` 或 `8011`，两处一起改）：

  ```bash
  P=apk_80a8fe0e81204c9f
  B=localhost:8011

  # 上传（契约表 §2.2）——幂等：同样的字节再传一次返回同一个 project
  curl -s -w "\n[%{http_code}]\n" -X POST -F "file=@examples/demo-app/demo.apk" $B/analyze
  # 202
  # {"project_id":"apk_80a8fe0e81204c9f","status":"completed","detail":"/projects/apk_80a8fe0e81204c9f"}

  # 项目（§2.3）
  curl -s -w "\n[%{http_code}]\n" $B/projects
  # 200
  # [{"id":"apk_80a8fe0e81204c9f","status":"completed",…,"class_count":5,"method_count":8,…}]

  # 运行（§2.3）——`total` 是这个项目**跑过几次分析**，不是固定值：
  # 照 §3.3 → §3.5 → §3.8（F1 那条 analyze）的顺序走，到这里是 3。
  # 判据看**形状**：`runs` 的条数 == `total`，其中**恰有一条** `published=true`，
  # 那一条的 id 就是 `published_run_id`（上面那条上传命令是幂等的，不会再加一次）
  curl -s -w "\n[%{http_code}]\n" $B/projects/$P/runs
  # 200
  # {"project_id":"apk_80a8fe0e81204c9f","total":3,"published_run_id":"run_…","runs":[{…,"status":"completed","completeness":"complete","published":true,…},…]}

  # 符号（§2.4）
  curl -s -w "\n[%{http_code}]\n" "$B/projects/$P/classes?limit=2"
  # 200
  # {"project_id":"apk_80a8fe0e81204c9f","total":5,"classes":[{…,"name":"com.example.demo.Crypto","kind":"class",…}]}

  # 源码（§2.5）——只取响应头：正文是 Java 源码，头里才是契约里的那几项
  curl -s -D - -o /dev/null "$B/projects/$P/classes/com.example.demo.MainActivity/source"
  # HTTP/1.1 200 OK
  # x-dexatlas-source-kind: java
  # x-dexatlas-source-tool: jadx
  # x-dexatlas-source-locator: jadx:sources/com/example/demo/MainActivity.java
  # x-dexatlas-source-tool-version: 1.5.2

  # 报告（§2.6）——10 个顶层字段
  curl -s "$B/projects/$P/report?format=json" \
    | uv run --no-sync python -c "import json,sys; print(sorted(json.load(sys.stdin)))"
  # ['errors', 'evidence', 'generated_at', 'latest_attempt_status', 'manifest', 'project', 'run', 'schema_version', 'summary', 'tools']
  ```

  上面每个 `#` 开头的行是**实测输出**（2026年11月19日，Windows 11 + JDK 21 + 三个
  后端齐备、同一棵工作树；`…` 表示省略的中间字段）。**状态码是 F2 判据的一部分**，
  所以命令里带了 `-w "\n[%{http_code}]\n"`。

  **第三步（F3）：MCP 工具清单与只读注解。** `dexatlas-mcp` 是 stdio 传输的 MCP
  server，**直接起它看不到工具清单**——要用 MCP 的 JSON-RPC 协议问它一次。下面
  两条命令**照抄即可，不需要你写代码**；末尾的 `sleep 3` 是让 server 有时间回话
  （stdin 一闭合，它会把还没回的请求丢掉），不是别的意思。

  ```bash
  # 列出 11 个工具与四个只读注解
  { printf '%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' \
    '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'; sleep 3; } \
  | uv run --no-sync dexatlas-mcp \
  | uv run --no-sync python -c "import json,sys;ts=[t for l in sys.stdin if l.strip() for d in [json.loads(l)] for t in d.get('result',{}).get('tools',[])];print('\n'.join('{}\treadOnly={}\tdestructive={}\tidempotent={}\topenWorld={}'.format(t['name'],*(a.get(k) for k in ('readOnlyHint','destructiveHint','idempotentHint','openWorldHint'))) for t in ts for a in [t.get('annotations',{})]));print('tool count:',len(ts))"
  ```

  预期（实测，11 行 + 一行计数）：

  ```text
  list_projects	readOnly=True	destructive=False	idempotent=True	openWorld=False
  get_project_status	readOnly=True	destructive=False	idempotent=True	openWorld=False
  get_manifest	readOnly=True	destructive=False	idempotent=True	openWorld=False
  search_symbols	readOnly=True	destructive=False	idempotent=True	openWorld=False
  get_class_source	readOnly=True	destructive=False	idempotent=True	openWorld=False
  get_method_source	readOnly=True	destructive=False	idempotent=True	openWorld=False
  find_callers	readOnly=True	destructive=False	idempotent=True	openWorld=False
  find_callees	readOnly=True	destructive=False	idempotent=True	openWorld=False
  get_evidence	readOnly=True	destructive=False	idempotent=True	openWorld=False
  resolve_locator	readOnly=True	destructive=False	idempotent=True	openWorld=False
  find_resource_declarations	readOnly=True	destructive=False	idempotent=True	openWorld=False
  tool count: 11
  ```

  逐条与[契约表 §3.1](../architecture/public-contracts.md) 的 11 个工具**逐名
  对上**，四个注解与[契约表 §3](../architecture/public-contracts.md) 开头写的
  一致（`read_only_hint=true`、`destructive_hint=false`、
  `idempotent_hint=true`、`open_world_hint=false`）。

  **再抽查 2 个工具的返回形状**（F3 判据的后半句）：

  ```bash
  { printf '%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' \
    '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
    '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_projects","arguments":{}}}' \
    '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_project_status","arguments":{"project_id":"apk_80a8fe0e81204c9f"}}}'; sleep 3; } \
  | uv run --no-sync dexatlas-mcp \
  | uv run --no-sync python -c "import json,sys;[print('id={} -> {}'.format(d.get('id'),json.dumps(d.get('result',{}).get('structuredContent'),ensure_ascii=False)[:400])) for l in sys.stdin if l.strip() for d in [json.loads(l)] if d.get('id') in (3,4)]"
  ```

  预期（实测，两行；`structuredContent` 是工具返回的对象本身）：

  ```text
  id=3 -> {"projects": [{"id": "apk_80a8fe0e81204c9f", "apk_name": "demo.apk", …, "class_count": 5, "method_count": 8, …}], "total": 1, "offset": 0, "limit": 50}
  id=4 -> {"project": {"id": "apk_80a8fe0e81204c9f", …}, "completeness": {"complete": true, …}, "published_run": {…}}
  ```

  **两行的先后顺序不固定**（两个调用是并发执行的，实测两种顺序都出现过）——按
  `id=` 对号入座即可：`id=3` 是 `list_projects`，`id=4` 是 `get_project_status`。

  把返回对象的形状与[契约表 §3.1](../architecture/public-contracts.md) 那一行的
  「返回」列对一下（`ProjectList{projects,total,offset,limit}`、
  `ProjectStatus{project,completeness,published_run?,runs[]}`）即可。

  PowerShell 写法（同一台机器上实测通过，PowerShell 7 与 5.1 都可）：

  ```powershell
  & {
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
    '{"jsonrpc":"2.0","method":"notifications/initialized"}'
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
    Start-Sleep -Seconds 3
  } | uv run --no-sync dexatlas-mcp | uv run --no-sync python -c "import json,sys;ts=[t for l in sys.stdin if l.strip() for d in [json.loads(l)] for t in d.get('result',{}).get('tools',[])];print('\n'.join('{}\treadOnly={}\tdestructive={}\tidempotent={}\topenWorld={}'.format(t['name'],*(a.get(k) for k in ('readOnlyHint','destructiveHint','idempotentHint','openWorldHint'))) for t in ts for a in [t.get('annotations',{})]));print('tool count:',len(ts))"
  ```

  抽查两个工具的那一条，把第 3、4 行换成：

  ```powershell
    '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_projects","arguments":{}}}'
    '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_project_status","arguments":{"project_id":"apk_80a8fe0e81204c9f"}}}'
  ```

  想把原始 JSON-RPC 记录留作证据，就在管道中间加一个落盘步骤：bash 用
  `> mcp-tools.jsonl`，PowerShell 用 `| Out-File -Encoding utf8 mcp-tools.jsonl`。

  **报告 schema（F4）**：报告 JSON 的顶层字段是 `errors`、`evidence`、
  `generated_at`、`latest_attempt_status`、`manifest`、`project`、`run`、
  `schema_version`、`summary`、`tools` —— 10 个（上面「报告」那条命令已打印）。
  MCP 工具清单与只读注解在契约表 §3；REST 路由表在契约表 §2；报告 JSON 的
  `schema_version` 与顶层字段在契约表 §5.1。

- **服务回归集（E1–E5）**：读[服务回归集](../benchmarks/service-regression-set.md)
  与[层级 1 scripted 演练](../benchmarks/m6-level1-scripted.md)，确认你能区分
  层级 0（确定性判分 20/20）、层级 1（scripted 替身演练）、层级 2（真实模型，
  已执行三轮完整重测，当前结果 49/60 = 81.7% 未达验收线，见
  [高风险声明清单](#4-需要重点核查的高风险声明)）各自证明什么、不证明什么。
- **故障恢复（G1–G4）**：坏输入（非 ZIP 当 APK）应退出码 2 且不留半成品；
  清空后端环境变量后分析仍完成并写明 `not_installed`；同一 APK 分析两次
  project id 相同。四条可照抄的命令与预期输出见 [§9.1](#91-g-组故障恢复的可照抄命令)。

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
  [exit-code-partial-read.md](../proposals/exit-code-partial-read.md)。
  > **注意 [M8 演练 §6](m8-install-rehearsal.md) 记的是「当时（修复前）的实况」**
  > ——那一节写的是退出码仍为 0，是**提出这个缺口的历史记录**，不是现在的语义；
  > 那份记录里没有前向指针，所以**以本条与契约表 §8.1 为准**。
  > 请核对：读到 6 时你是否仍会把它误读为「分析成功」。
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

- 到第一份报告：首次 10–20 分钟（含下载）；暖缓存**按 1.5–2 分钟预留**——
  **这是预算档位，不是实测值**。
  两处实测锚点的口径不同、都比它快：[M8 演练](m8-install-rehearsal.md)「空目录 →
  第一份报告，暖缓存」**约 30 秒**（同一次**首次分析本身 6.8 秒**）；
  [读者实走演练](reader-dry-run.md)「重建 `.venv` → 第一份报告」**8 秒**
  （分析本身 3.8 秒）——**做快于 30 秒不是卡点**，以你自己的实测为准；
  明显超出预期按 §5.2 记卡点。
- clone + uv sync：约 4 分 30 秒（[读者实走演练](reader-dry-run.md)实测 4 分 24 秒）。
- Docker 镜像构建：首次约 15–20 分钟（无本地层缓存时的实测；见 §3.2 路线 B 的两个数）。
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

## 9. 附录：两条要照抄的补充路径

§3 的路径里有两步只给了一句概括，读者最容易卡在这两处：**故障恢复（G 组）**与
**契约活检**。本节把两处的可照抄命令、预期输出与「这个数字为什么是这样」写全。

### 9.1 G 组故障恢复的可照抄命令

这四条命令互相独立，各跑各的；每条跑完把**退出码**与**关键输出**抄进记录。
下面标「实测」的输出是 2026年11月18日在 Windows 11 + JDK 21 + 三个后端齐备的机器
上跑出来的（同一棵工作树）。换一台机器，耗时与「1 秒内能不能跑完」会不同——
**判据是行为，不是数字**。

**G1 坏输入（拿非 ZIP 当 APK 分析）**

> **这条要在「一个空工作区」里跑。** §9.1 是附录，排在 §3.3–§3.6 之后，而 §3.3
> 已经把 demo.apk 分析进主工作区了——在主工作区里 `projects` **列着 A4 的那个
> 项目是正常的**，不是半成品。所以下面两条命令都带一个**新的**工作区目录：
> 坏输入不该在主工作区里留下任何东西，主工作区里已有的项目也不该因此消失。

```bash
DEXATLAS_WORKSPACE=./g1-fresh uv run dexatlas analyze README.md
```

预期退出码 **2**，一行能读懂的错误（实测）：

```text
Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives
```

再确认**这个工作区里没有留下半成品项目**（实测）：

```bash
DEXATLAS_WORKSPACE=./g1-fresh uv run dexatlas projects
```

预期：`No projects yet. Run \`dexatlas analyze <apk>\`.`——列表是空的。

> PowerShell 写法：`$env:DEXATLAS_WORKSPACE="./g1-fresh"; uv run dexatlas analyze README.md`。
>
> **在主工作区里再跑一次 `uv run dexatlas projects` 也没问题**：它列着 A4 的项目，
> 计数与 §3.3 记录的一致，就是没有多出半个坏输入项目——这一条同样算 G1 通过。

**G2 后端缺失（降级，不抛异常）**

```bash
DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR= uv run dexatlas analyze examples/demo-app/demo.apk
```

预期退出码 **0**，报告照常产出，两条 `not_installed` 记进 `errors[]`（实测）：

```text
!  apktool is not installed or not on PATH: ...
!  jadx is not installed or not on PATH: ...
```

PowerShell 写法：`$env:DEXATLAS_JADX_PATH=""; $env:DEXATLAS_APKTOOL_JAR=""; uv run dexatlas analyze examples/demo-app/demo.apk`。

**空值与不写是两件事**：写成空值是「关掉这个后端」，不写这两个变量是「按默认路径
去找它」（变量表见 [install.md](../install.md)）。报告 JSON 里 `errors[]` 的两条
`code` 是 `not_installed`，`tools` 里 `jadx` 与 `apktool` 为 `null`、`androguard`
有版本号；计数低于 A4 基线（5 classes / 1 resource string → 实测 4 classes /
0 resource strings）是**降级不是回归**。

> **当场抄下这一次的 stdout**：重复分析会把该项目的**最新一次运行**换成新的一次
> （见 §3.3 的提醒），重跑之后就找不回这次的 `not_installed` 证据了。

**G3 后端超时**

超时的可配置点是环境变量 **`DEXATLAS_TOOL_TIMEOUT_SECONDS`**：**每个后端各自的
超时秒数**，默认 **900**（变量表见 [install.md](../install.md)）。它读在
`src/dexatlas/config/settings.py` 的 `tool_timeout_seconds` 上，变量名由
`env_prefix="DEXATLAS_"` 加字段名拼出，取值不得小于 1。**它是环境变量，不是 CLI
参数**——`dexatlas analyze --help` 里找不到它。

```bash
DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze examples/demo-app/demo.apk
```

预期：**至少一条后端记 `timeout`，且报告照常产出**。**权威判据见
[准备包 §2.7 G3](m10-acceptance-pack.md)**——那里是这条判据的唯一出处，
**条数与本机速度有关，不是固定值**。下面是**示例**（本机 2026年11月19日实测：
androguard 与 apktool 都在 1 秒内跑完了，**只有 jadx 超时**，所以只有一条）：

```text
!  jadx exceeded its 1s timeout; its launcher had already exited
```

三后端都慢的机器上会看到三条（每条一个 `!` 行）：

```text
!  apktool exceeded its 1s timeout; its launcher had already exited
!  androguard exceeded its 1s timeout; its launcher had already exited
!  jadx exceeded its 1s timeout and was terminated
```

**条数随后端速度变化**——本机实测只有一条，你的机器上可能是两条或三条；
**判据是「后端失败时记 `timeout`、不抛异常、报告照常产出」，不是「一定有三条
`timeout`」**。

报告 JSON 里 `errors[]` 每条的 `code` 是 `timeout`。`summary.index_complete` 与
`summary.index_gaps` **只跟索引后端有关**：`index_gaps` 只统计 **androguard**
（索引后端）或分析级失败，**jadx 超时不构成 gap**——所以只有 jadx 超时时，
`index_complete` 是 `true`、`index_gaps` 是 `[]`（本机实测如此）；**只有 androguard
自己也超时**时，才是 `index_complete=false` 且 `index_gaps` 里有一条
`androguard` 的 `timeout`。

> **退出码是 0，不是 6——这是对的。** 退出码 6（`EXIT_NO_INDEX`）说的是「跑完了，
> 但**一个符号都没索引到**」；1 秒超时下 androguard 已经把类表交出来了
> （`5 classes`），索引是**残缺**而不是**空**——残缺由 `index_complete=false` 与
> `index_gaps` 说明，退出码仍是 0。退出码 6 的语义见
> [公共契约表 §1.2](../architecture/public-contracts.md)；要拿到 6，需要「三个后端
> 全失败**且**一个类都没索引到」，而这个分支用超时变量在 demo APK 上测不出来
> （androguard 总是先交出类表）；它由契约活检脚本用一个没有索引的分析触发
> （`scripts/verify-public-contracts.py` 里的 `an analysis with no index exits 6`）。
> **把实际退出码记进记录**——准备包 G3 的判据就是「记录实际退出码」。
>
> **超时运行的证据条数与正常运行不同**：会**多出一条** `verified` 的「后端未完成」
> 记录（`errors[]` 里每个超时后端一条），所以证据条数随后端配置变化
> （干净 / 降级 / 超时各不相同；本机实测：正常运行 11 条，jadx 超时那次 12 条）。
> **判据是「以报告自身为准」**：报告里写了几条就是几条，不要拿别次运行的条数来比。

**G4 幂等（同一个 APK 连着分析两次）**

```bash
uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas projects
```

预期（实测）：两次的 project id 相同（`apk_80a8fe0e81204c9f`）、退出码都是 0；
`projects` 只列 **1** 条，计数两次一致——project id 由 APK 的 sha256 决定，重跑是
**更新同一个项目**，不是新建一个。

### 9.2 契约活检与本机配置

§3.8 的活检脚本 `scripts/verify-public-contracts.py` 在**装没装后端两种配置下都
退出 0**：没装 JADX / Apktool 时它跑 47 条断言（少一条源码端点的 header 断言），
三个后端齐备时跑 48 条——退出码一样是 0。所以**「本地绿」不等于「CI 绿」**：本地
那台机器可能根本没跑过带 JADX 的那几条断言，而 CI 里有一道 job 是**刻意不装后端**
的。

契约表 §7 自己记着这个分叉（47 与 48 两行），下面这条命令会替你问「这台机器是不是
CI 那台」：

```bash
uv run --no-sync python scripts/check-contract-records.py --expect with-jadx
```

它自己会把活检跑一遍，再拿这一次的结果跟契约表 §7 的记录比。三个退出码各有一句
话，**不要把它们混为一谈**：

| 退出码 | 意思 | 你该做什么 |
|---|---|---|
| 0 | 契约成立，**而且这台机器就是 CI 那台配置**（三个后端都在） | 记 0 |
| 2 | 契约成立，但**这台机器不是那个配置**（没装 JADX / Apktool，或活检没跑到记录里描述的路径） | **需人工**：装上后端再跑一遍（`bash scripts/install-backends.sh`），或如实记录「本机未验证带 JADX 的那半边」 |
| 1 | 契约破了，或契约表的记录已经过时 | 记 1，这是缺陷 |

CI 上是**两道门**：装了后端的那道用 `--expect with-jadx`，**刻意不装后端**的那道用
`--expect without-jadx`。两道题的期望不同——**别拿一道的绿当另一道的答案**。
