# M10 邀请函 —— 读者视角预演记录（第四轮，只读）

> **本文件的性质：** 这是一次**只读预演**：照着**定稿后的**邀请函、读者包、准备包与
> 记录模板给的命令，从 clone 走到打分的模板前，把每一步实际跑了一遍，记录
> 「命令 / 实际输出 / 与材料是否对得上 / 耗时」，并标出会让读者卡住、被误读或
> 觉得多余的地方。
> 口径与前三轮（[第一轮](invitation-reader-rehearsal.md)、
> [第二轮](m10-reader-rehearsal-2nd.md)、
> [第三轮](m10-reader-rehearsal-3rd.md)）一致：
> **卡住** = 材料让你做不到的事，或缺材料没给的东西；**误读** = 材料可以有两种
> 理解，而你会读错那一种；**多余** = 不必要的动作，或同一件事说了两遍而两遍不一致。
>
> **它不是验收结论。** 预演由作者侧执行（拿得到仓库、能读源码），因此**不具备
> 独立性**；40 个验收项在这里一条也没有被判「通过」，也没有被改过。
>
> **本文件不改任何既有文件**，只新增这一份。未触碰 `.github/`、README 徽章、
> `docs/status.md`、`docs/reports/README.md`，未跑
> `scripts/refresh-report-figures.py`，未登记进 `scripts/check-doc-citations.py`
> 的文档清单（那两件按分工留给主会话统一做；本文件因此**不在引用检查器的
> 覆盖范围内**，里面的 `file:line` 引用是逐条手工核过的）。

---

## 0. 预演基线与环境

| 项 | 值 |
|---|---|
| 预演日期 | 2026-11-19（第四轮） |
| **修复后的树**（本轮真正验证修复内容的那棵） | `main` = `be593fac93f57d6e9ed458dc64844d89409da48c`（**预演时**的 `main`；预演结束后本分支已把 `main` 的新 tip `a785d01` 合进来，见 §8.2 的门禁对照） |
| **tag 树**（读者照材料走会读到的那棵） | `v1.0.0` → `2715aefda06c3cbbc055a9edf795535e71464068`（**未重打**） |
| 副本来源 | 本地克隆 `E:/Dexatlas` → `.scratch/reader-rehearsal-4th/dexatlas`（**离线**；见 §8） |
| OS | Windows 11 Pro 10.0.26300 |
| Python / uv / JDK | 3.12.10 / 0.11.21 / 21.0.11（OpenJDK） |
| 后端 | jadx 1.5.2、apktool 2.11.1（`E:\Dexatlas\.scratch\backends`，经 `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 指向）、androguard 4.1.4 |
| 走过的步数 | **62 步**（材料路径上的命令）；**跳过 1 步**（Docker 路线）；**1 步用等价静态检查代替**（「双击打开 HTML」） |
| 计算耗时合计 | 材料路径上的命令约 **4 分钟**（不含阅读材料与思考的时间；`uv sync` 另计 5.6 s） |

**这一轮与上一轮最大的不同**：上一轮预演完那 11 条之后，材料又改了一轮
（5 条：S-5 / M-8 / M-9 / G5 / F2，逐条记在
[第三轮缺口的逐条处置记录](m10-round3-fixes.md)）。本轮要回答的是两个问题：
**那 5 条真堵住了吗**（§6），**照定稿后的材料再走一遍，还剩什么**（§3–§5）。

**本轮的结论（一句话）**：**5 条修复内容本身全部成立**——实测逐条对上了；
**但它们一条都没进 tag**（§3 的 S-4 延续），读者照材料 §3.1 走
（`git checkout v1.0.0`）读到的仍是修复前的稿。
**这一轮新挖出 2 条卡住、2 条误读、1 条多余**，其中 **S-7 与 M-10 都是上一轮那批
修复自己带进来的**——它们不是「材料没改」，是「改得不够」。

---

## 1. 这一轮的做法

前三轮预演都已确立一条纪律：**只有实跑才能发现缺口**。第二轮记下的 G3 自相矛盾、
F3 无命令可用、tag 树里 hash 是占位符，第三轮记下的 G3 条数矛盾、F3 无命令可用、
tag 树里一条修复都没有，三条都是读材料读不出来的。所以本轮的做法与前几轮一致，
也与任务要求一致：

1. **克隆一份副本**（§3.1）——**分别**在 **tag 树**（`v1.0.0`）与**修复后的树**
   （`main`）上各看一遍；
2. **照材料给的命令一条条跑**（§3.2–§3.9、§9.1、§9.2），每条记
   「命令 / 实际输出 / 与材料是否对得上 / 耗时」；
3. **逐条核对上一轮那 5 条**——对每一条，先在**修复后的树**上验证修复内容本身
   是否成立，再在 **tag 树**上验证读者实际读到的那一份是否含修复（§6）；
4. **给 40 项做三类归属**——能自己判 / 必须问作者 / 没判据（§7）。

**这一轮的额外动作**：对上一轮新给的那条 locator 解析命令做了**启动时序测量**
（§2.7），因为它第一次跑就返回了空输出——**前三轮都没有做过这一步**，
而这一轮的 3 条新缺口里有 2 条是从那次「空输出」里长出来的。

---

## 2. 读者实走：步骤与实测输出

### 2.1 §3.1–§3.2 环境准备（验收项 A1、A2、A3）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 1 | `git clone --no-hardlinks <本地> .scratch/reader-rehearsal-4th/dexatlas` | 0 | `done.` | **0.75 s**（本地路径克隆，见下方注） | ✓ |
| 2 | `git checkout v1.0.0` | 0 | `HEAD is now at 2715aef run 记录改成当前的事实…` | 1 s | ✓ |
| 3 | `git rev-parse "v1.0.0^{commit}"` | 0 | `2715aefda06c3cbbc055a9edf795535e71464068` | 0.1 s | ✓ 与**main 树**邀请函 §2 那一串**逐字相同** |
| 4 | `git status --porcelain` | 0 | 无输出（干净） | 0.1 s | ✓ |
| 5 | `git tag -l` | 0 | 8 个 tag，含 `v1.0.0` | 0.1 s | ✓ |
| 6 | `bash scripts/fetch-fixtures.sh` | — | **未跑**（本轮不联网）；改为从主检出**复制**已取好的两个 fixture 到 `fixtures/apk/` | — | ⚠ 见 §8 |
| 7 | `uv sync --extra dev --extra analysis --extra mcp --extra demo` | **0** | 装出 101 个包 | **5.6 s**（uv 缓存已热） | ✓ |
| 8 | `uv run dexatlas backends`（**未设**后端变量） | 0 | `jadx not installed` / `apktool not installed` / `androguard available 4.1.4`；`2 backend(s) unavailable.` | 4.0 s | ✓ |
| 9 | 同上（**设了** `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR`） | 0 | 三行全 `available`：jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4 | 2.2 s | ✓ |

> **第 1 步与第 7 步的耗时不能与材料的数比**：材料 §3.1 写的是
> `git clone https://github.com/gg320324492-lgtm/dexatlas.git`（**走网络**），
> 本轮按任务的「不联网」约束改成了**从本地克隆**（`--no-hardlinks`），因此
> 0.75 秒；第 7 步的 5.6 秒是 **uv 缓存已热**时的数。
> **本轮不判 A7 的耗时**（它要的是读者自己那台的数）。

### 2.2 §3.3–§3.5 首次分析与三格式报告（验收项 A4、A5、C1、D1、D2）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 10 | `uv run dexatlas analyze examples/demo-app/demo.apk` | 0 | `✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (6.0s)` | 7.7 s | ✓ **逐字相符** |
| 11 | `uv run dexatlas manifest apk_80a8fe0e81204c9f` | 0 | `com.example.demo` / `version 1.0 (1)` / `sdk min 24 / target 34` / `permissions 1` / `components 3`；两个 exported 组件 `no permission guard` | 1.6 s | ✓ |
| 12 | `uv run dexatlas search apk_80a8fe0e81204c9f "Crypto"` | 0 | 2 个 class 命中、3 个 method 命中、2 个 string 命中 | 1.7 s | ✓ |
| 13 | `uv run dexatlas search apk_80a8fe0e81204c9f "sk_live"` | 0 | 一行：`string │ sk_live_2f8a91c4e7b3` | 1.4 s | ✓ |
| 14 | `uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.MainActivity` | 0 | `source kind: java` / `jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java` | 1.7 s | ✓ |
| 15 | `uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.MainActivity.describe(…)"` | 0 | `1 call site(s), 1 call edge(s)`；调用点 `classes.dex@34` | 1.7 s | ✓ |
| 16 | **§3.4 的「打印三个字段 + level」命令**（**在 §3.5 导出之前**跑） | **1** | `FileNotFoundError: [Errno 2] No such file or directory: 'report.json'` | 0.4 s | ✗ **见 M-11** |
| 17 | `uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json --html report.html` | 0 | 三行 `Markdown report → report.md` / `JSON report → report.json` / `HTML report → report.html`；8606 / 11746 / 5262 字节 | 7.7 s | ✓ |
| 18 | 同第 16 步（**导出之后**再跑） | 0 | `E-0001 verified [('androguard', '4.1.4', 'androguard:AndroidManifest.xml')]` / `E-0002 verified [('apktool', '2.11.1', 'apktool:AndroidManifest.xml')]` / `E-0003 verified [('apktool', '2.11.1', 'apktool:AndroidManifest.xml#/application')]` | 0.5 s | ✓ **逐字相符**（M-8 修复成立） |

> **第 16 步是本轮「读者实走」的顺序问题**：材料 §3.4 的小节顺序在 §3.5 之前，
> 而这条命令要读的 `report.json` 是 §3.5 才产出的。材料在命令下方写了一句
> 「（`report.json` 由 §3.5 的导出命令生成；还没导出就先跑那一条……）」——
> **「那一条」指哪一条有两种读法**，见 §4 的 M-11。

### 2.3 §3.6 证据包导出与校验（验收项 C5、C6、D3、D4、G5）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 19 | `uv run dexatlas export apk_80a8fe0e81204c9f -o evidence.zip` | 0 | `✓ evidence package → evidence.zip (4 files: 3 reports + 1 manifest, apk 80a8fe0e81204c9f)` | 2.2 s | ✓ |
| 20 | `verify_package` + `verify_citations` | 0 | `{'citations_total': 14, 'citations_resolved': True, 'citations_unresolved': [], 'apk_sha256': '80a8fe0e…'}` | 0.6 s | ✓ |
| 21 | `python -m zipfile -l evidence.zip` | 0 | **4 个条目**：`reports/report.html` / `reports/report.json` / `reports/report.md` / `manifest.json` | 0.3 s | ✓ 与材料的「4 个条目」相符 |
| 22 | 解包读 `evidence/manifest.json` | 0 | 顶层 8 键；`not_included` 三键 `apk` / `full_sources` / `unrelated_strings`；`files` **3** 条（全是 `reports/…`） | 0.4 s | ✓ |
| 23 | 包内查 `.apk` 与 `sources/` 目录 | 0 | `.apk` **0** 个；`sources/` 目录 **0** 个 | 0.3 s | ✓ **G5 修复成立**（两条都能在包里判） |
| 24 | 查 E-0004–E-0006 的 provenance 条数 | 0 | 三条**各 2 条** provenance（工具都是 androguard） | 0.3 s | ✓ 与 M-8 修复里「E-0004–E-0006 各有两条」相符 |
| 25 | **C6 迁移复验**：把 `evidence.zip` 复制到另一个目录再验一遍 | 0 | 同样 `citations_resolved: True`、无未解析引用 | 0.6 s | ✓ |
| 26 | 在解包后的包里搜本机绝对路径 | 0 | **无命中**（`E:\Dexatlas` 一个也没有） | 0.3 s | ✓ |

### 2.4 §3.8 契约活检（验收项 F1、F5、F6）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 27 | `uv run dexatlas analyze examples/demo-app/demo.apk` | **0** | 计数与第 10 步相同 | 7.6 s | ✓ **F1-1** |
| 28 | `uv run dexatlas search apk_80a8fe0e81204c9f __no_such_term__` | **1** | `No matches for '__no_such_term__'.` | 0.4 s | ✓ **F1-2** |
| 29 | `uv run dexatlas analyze README.md` | **2** | `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives` | 0.4 s | ✓ **F1-3** |
| 30 | `uv run pytest tests/test_public_contracts.py -q` | **0** | `31 passed in 9.85s` | 12.5 s | ✓ **F5** |
| 31 | `uv run python scripts/verify-public-contracts.py` | **0** | `48/48 checks passed` + `the public contracts hold`（27 REST + 6 MCP + 15 CLI） | 26.4 s | ✓ **F6** |
| 32 | `uv run python scripts/check-contract-records.py --expect with-jadx` | **0** | `the live run: 48 checks … passed, exit 0` + `PASS the table records 6 run(s)` | 30.4 s | ✓ §9.2 说的三个退出码里的 **0** |

### 2.5 §3.8 F2 的六类 REST 端点（验收项 F2）

**这台机器的端口状态与材料描述的一模一样**——这让 F2 的退路能被真正验到：

| 端口 | 状态 | `/health` 答什么 |
|---|---|---|
| 8000 | 被**别的** FastAPI 应用占着 | `{"status":"healthy"}` ← 不是 DexAtlas |
| 8011 | 被**另一个 DexAtlas** 占着（`version 1.0.0`，后端版本都一样） | `{"status":"ok","version":"1.0.0","backends":{…}}` ← 形状对，但**不是我的** |
| 8012 | 空闲 | — |

| # | 命令 | 实际输出（要点） | 对得上吗 |
|---|---|---|---|
| 33 | `uv run uvicorn dexatlas.api.app:app --port 8000`（读日志） | `Application startup complete.` **之后**才是 `ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] 通常每个套接字地址…`；`/health` 仍答 `{"status":"healthy"}` | ✓ **退路被触发**；✗ **但材料引用的日志字面串对不上**（见 M-10） |
| 34 | 同上，`--port 8011` | 同样先 `Application startup complete.`、再 `ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8011)` | ✓ **两个端口都被材料点名了** |
| 35 | 同上，`--port 8012` | `INFO: Uvicorn running on http://127.0.0.1:8012 (Press CTRL+C to quit)` ← **材料说的「唯一信号」** | ✓ |
| 36 | `curl -s $B/health` | `{"status":"ok","version":"1.0.0","backends":{…}}` | ✓ 与材料预期逐字相符 |
| 37 | `curl -X POST -F "file=@examples/demo-app/demo.apk" $B/analyze` | `202` + `{"project_id":"apk_80a8fe0e81204c9f","status":"completed","detail":"/projects/apk_80a8fe0e81204c9f"}` | ✓ |
| 38 | `curl $B/projects` | `200` + `[{…"class_count":5,"method_count":8,"reference_count":23,"call_site_count":23,"call_edge_count":21,"evidence_count":11,"resource_count":1…}]` | ✓ |
| 39 | `curl $B/projects/$P/runs` | `200` + `{"project_id":…,"total":7,…}` | ✓ **形状**相符（`total` 的数见下） |
| 40 | `curl "$B/projects/$P/classes?limit=2"` | `200` + `{"project_id":…,"total":5,"classes":[{…"provenance":[{tool,tool_version,apk_sha256,locator}…]…}]}` | ✓ |
| 41 | `curl -D - -o /dev/null ".../classes/com.example.demo.MainActivity/source"` | `HTTP/1.1 200 OK` + `x-dexatlas-source-kind: java` / `-tool: jadx` / `-locator: jadx:sources/com/example/demo/MainActivity.java` / `-tool-version: 1.5.2` | ✓ 四个头**逐字相符** |
| 42 | `curl "$B/projects/$P/report?format=json"` 取顶层键 | `['errors','evidence','generated_at','latest_attempt_status','manifest','project','run','schema_version','summary','tools']` | ✓ **10 个**；`schema_version = 3`（F4） |

> **`total` 是 7，不是材料写的 3 —— 而这正是 M-7 修好之后该有的样子。**
> 材料现在写的是「`total` 是这个项目**跑过几次分析**，不是固定值：照
> §3.3 → §3.5 → §3.8（F1 那条 analyze）的顺序走，到这里是 3。判据看**形状**」。
> 本轮在 §3.8 之前**多跑了 G 组四次分析**（G2 一次、G3 一次、G4 两次），
> `3 + 4 = 7` —— **与材料完全自洽**，而上传端点是幂等的（**没有**再加一条 run）。
> 这条判据**照材料走不会产生假卡点**。

### 2.6 §3.8 F3 的 MCP 工具清单（验收项 F3）

| # | 命令 | 实际输出 | 对得上吗 |
|---|---|---|---|
| 43 | §3.8「列出 11 个工具与四个只读注解」那条命令 | **11 行**工具名 + 四注解齐全（`readOnly=True destructive=False idempotent=True openWorld=False`）+ `tool count: 11` | ✓ **逐字相符**（跑了 3 次，3 次都对） |
| 44 | §3.8「抽查 2 个工具的返回形状」那条命令 | `id=4 -> {"project": {…},"completeness": {…},…}` / `id=3 -> {"projects": [{…}],"total":1,"offset":0,"limit":50}` | ✓ 顺序确实是乱的，材料也说了「按 `id=` 对号入座」 |

### 2.7 §3.4 的 locator 解析命令（验收项 C2 ★）—— 上一轮 S-5 补的那一条

**这是本轮唯一一条「第一次跑就返回空输出」的命令。**

| # | 命令 | 实际输出 | 耗时 | 对得上吗 |
|---|---|---|---:|---|
| 45 | 照抄 §3.4 那条（bash 写法） | **5 行**，与材料的预期**逐行相符**（顺序不同，材料也说了「顺序不固定」） | 3.8 s | ✓ |
| 46 | 同一条，**再跑 5 次** | 5 / 5 / 5 / 5 / 5 行 | — | ✓ |
| 47 | 同一条，**把 `sleep 3` 改成 `sleep 2`** | **0 行**；退出码 **0**；stderr **空** | 2.7 s | ✗ |
| 48 | 同一条，`sleep 1` | **0 行** | 1.7 s | ✗ |
| 49 | 同一条，`sleep 0` | **0 行** | 0.7 s | ✗ |
| 50 | 同一条，`sleep 4` / `sleep 6` | 5 行 / 5 行 | — | ✓ |
| 51 | **测 MCP server 从进程启动到首个应答的延迟**（3 次） | **2.91 s / 2.27 s / 2.17 s** | — | — |

> **第 47–51 步是本轮的关键测量**：材料那条命令的末尾是 `sleep 3`，
> 而 MCP server 在这台机器上要 **2.17–2.91 秒**才能应答。**余量只有 0.1–0.8 秒。**
> `sleep 2` 时 stdin 先闭合，server 起来后**不回话**，管道里一行都没有，
> **退出码 0、stderr 什么都没有**。见 §3 的 S-7。

### 2.8 §9.1 G 组故障恢复（验收项 G1–G5）

| # | 命令 | 退出码 | 实际输出（要点） | 对得上吗 |
|---|---|:---:|---|---|
| 52 | `DEXATLAS_WORKSPACE=./g1-fresh uv run dexatlas analyze README.md` | **2** | `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives` | ✓ |
| 53 | `DEXATLAS_WORKSPACE=./g1-fresh uv run dexatlas projects` | 0 | `No projects yet. Run \`dexatlas analyze <apk>\`.` | ✓ |
| 54 | `uv run dexatlas projects`（主工作区） | 0 | `Projects (1)` 一行，`apk_80a8fe0e81204c9f` / `demo.apk` / `completed` / 5 / 8 | ✓ |
| 55 | `DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR= uv run dexatlas analyze examples/demo-app/demo.apk` | **0** | `✓ … — 4 classes, 8 methods, 23 call sites, 21 call edges, 0 resource strings (1.5s)` + **两条** `!  apktool is not installed or not on PATH: …` / `!  jadx is not installed or not on PATH: …` | ✓ **逐条相符**（4 classes / 0 resource strings 也对上了） |
| 56 | `DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze examples/demo-app/demo.apk` | **0** | `✓ … — 5 classes, 0 methods, 0 call sites, 0 call edges, 1 resource string (7.2s)` + **三条** `!  apktool exceeded its 1s timeout; its launcher had already exited` / `!  androguard exceeded its 1s timeout; its launcher had already exited` / `!  jadx exceeded its 1s timeout; its launcher had already exited` | ✓ 判据是「至少一条记 timeout」→ 满足；条数是 3（材料说了「可能是两条或三条」） |
| 57 | `uv run dexatlas analyze examples/demo-app/demo.apk` ×2 | 0 / 0 | 两次 id 相同、计数相同 | ✓ **G4** |
| 58 | `uv run dexatlas projects` | 0 | `Projects (1)` | ✓ **G4** |

> **第 56 步那三条 `!` 行的措辞与材料 §9.1 给的「三条示例」不完全一样**——
> 材料的三条示例里 jadx 那条写的是 `and was terminated`，本机是
> `its launcher had already exited`。这三种措辞在源码里是**三种不同的运行结果**
> （[`src/dexatlas/tools/base.py:331`](../../src/dexatlas/tools/base.py#L331) `anchor: and was terminated`、
> [`src/dexatlas/tools/base.py:333`](../../src/dexatlas/tools/base.py#L333) `anchor: its launcher had already exited`、
> [`src/dexatlas/tools/base.py:334`](../../src/dexatlas/tools/base.py#L334) `anchor: could not be terminated`）。判据是行为不是措辞，
> **不影响判定**，但见 §5 的 X-4。

### 2.9 其余各组（验收项 D1、D2、C3、C4、E、F4）

| # | 命令 | 实际输出 | 对得上吗 |
|---|---|---|---|
| 59 | `grep -c "<script" report.html`（复制到另一目录后查） | **0**；`src=` / `href=` 引用 **0** 条；`http(s)://` 引用 **0** 条 | ✓ **D1** |
| 60 | 三格式计数对照（JSON `summary` / JSON `project` / MD 文本 / HTML 文本） | JSON `summary`：`classes 5, methods 8, call_sites 23, call_edges 21, resource_strings 1`；`project` 同；MD 与 HTML 里 5 / 8 / 23 / 21 都在 | ✓ **D2**（抽查 3 个数字的做法可用） |
| 61 | `evidence_by_level` | `{"verified": 11}` —— `lead` 0、`insufficient` 0 | ✓ **C3**「demo 报告 11 条 evidence 全为 verified、lead 0 是设计而非缺失」 |
| 62 | `uv run python scripts/m10_selfcheck.py` | `自动化判定：通过 43，失败 0，需人工 40；已判定项通过率 100.0%` | ✓ §7 |

---

## 3. 卡住（2 条）

### S-4 【**全部 5 条修复**】tag 指向的树上，**一条修复都没有** —— 读者读到的是修复前的材料

**上一轮就有这一条，本轮原样重现。**

**实测**：本轮的 tag 与上一轮**同一个**——`git rev-parse "v1.0.0^{commit}"` =
`2715aefda06c3cbbc055a9edf795535e71464068`，`git cat-file -t v1.0.0` = `tag`（附注 tag），
`git tag -l` 仍是 8 个 tag。**`main` 已经跑到 `be593fa`，中间隔了 60 个提交。**

**逐条比对「5 条修复的特征串」在两棵树里的命中**（`git grep -F -c`，
范围是四份 M10 材料）：

| 特征串 | `v1.0.0`（tag 树） | `main`（修复后的树） | 对应上一轮的哪一条 |
|---|:---:|:---:|---|
| `没有可读的文件内容` | **0** | **4** | M-9 |
| `REST 侧没有 locator 解析端点` | **0** | **1** | S-5 |
| `一条可照抄的命令` | **0** | **2** | S-5 |
| `包里能直接判的是两条` | **0** | **1** | G5 |
| `Uvicorn running on` | **0** | **1** | F2 |

**另外两处也在 tag 树里是修复前的**：

- tag 树的邀请函 §2 仍是 `commit 【待填：v1.0.0 发版 commit 的完整 hash】`；
  `main` 树里已经是 `commit 2715aefda06c3cbbc055a9edf795535e71464068`。
- tag 树的 `docs/architecture/public-contracts.md` 与 `main` 的一致（这一处**没变**）。

**为什么算卡住**：读者照材料 §3.1 走（`git clone` → `git checkout v1.0.0`），
拿到的是**修复前的稿**——§3.4 里**没有** locator 解析命令、C2 判据还在说
「`path=None` 是设计」、C1 判据还在让人去顶层找三个字段、G5 判据还在要求
「与全量字符串表比对」、§3.8 里**没有**六类端点命令与端口退路。
**上一轮那 5 条修复，对读者而言一条都不生效。**

**这一轮把它记成「延续」而不是「新发现」**：上一轮已经说过「tag 尚未重打」，
这一轮**只是把它复核了一遍，并给出了上面那张逐条命中的表**——因为这次可以
说得更准：**不是「一条修复都没进 tag」，而是「5 条里 5 条都没进 tag」**。

**它卡住的是发版那一步，不是读者**——与上一轮的 S-6 是同一件事的两面：
重打 tag 之前，release body 的引用要按新树重新锚（上一轮 §8.1），
重测也要排在同步之后。

---

### S-7 【验收项 C2 ★】上一轮新给的那条解析命令是**启动竞态** —— 输不出来时，退出码是 0，日志是空的

**材料怎么说**：上一轮的 S-5 补了「**一条可照抄的解析命令**」（读者包 §3.4，
[`docs/reports/m10-reader-package.md:264`](m10-reader-package.md) `anchor: 一条可照抄的命令`），命令末尾是

```bash
  ; sleep 3; } \
| uv run --no-sync dexatlas-mcp \
```

**实测**：

| 变体 | 结果 |
|---|---|
| 照抄（`sleep 3`） | **5 行**，与材料的预期逐行相符 |
| 同一条，跑 5 次 | 5 / 5 / 5 / 5 / 5 行 |
| `sleep 2` | **0 行**，退出码 **0**，stderr **空** |
| `sleep 1` / `sleep 0` | **0 行** |
| `sleep 4` / `sleep 6` | 5 行 / 5 行 |
| **MCP server 从进程启动到首个应答**（3 次实测） | **2.91 s / 2.27 s / 2.17 s** |

**机制**：那是一条 **stdio 的 JSON-RPC 管道**。`{ printf … ; sleep 3; }` 这一头
写完 6 行请求后**关闭 stdin**；MCP server 一读到 EOF 就退出，**还没回的请求丢掉**——
材料在 §3.8 写这句的时候其实已经知道这个机制（「末尾的 `sleep 3` 是让 server 有
时间回话（stdin 一闭合，它会把还没回的请求丢掉）」，
[`docs/reports/m10-reader-package.md:500`](m10-reader-package.md) `anchor: sleep 3`）。
**问题在于那个 `3` 是一个没有保证的常数**：它必须**大于** server 的启动时间，
而 server 的启动时间 = uv 解析工程 + 装 Python 进程 + 导入 MCP 栈，**随机器、
随 uv 缓存冷热、随机器上别的进程有多少而变**。这台机器上它是 **2.17–2.91 秒**，
**余量只剩 0.1–0.8 秒**。

**为什么算卡住**：失败的形态是**最坏的一种**——

- **退出码 0**（管道两段都「成功」）；
- **stderr 一行都没有**（没有 traceback、没有报错）；
- **stdout 一行都没有**（不是「少一行」，是**全空**）。

一个读者在慢机器上（冷 uv 缓存、装了一堆东西的笔记本、CI runner、或**同时**在
跑别的 `uv` 命令抢工程锁）跑这条命令，拿到的是**一片空白**。
他手上没有「重试」的手段（材料没说「没输出就把 `sleep` 调大」），
而 C2 是 **★ 阻断项**、判据要求「在分析工作区内解析到真实文件」——
**最可能的读法就是把它记成「C2 不通过」**，再按 §5.2 记一条卡点。
**这一条命令是上一轮为了堵 C2 的卡住而加的，现在它自己成了卡住。**

**修法（任选其一，一行以内）**：

1. 把 `sleep 3` 换成 `sleep 10` —— 能把余量从 0.8 秒拉到 7 秒，但**仍不是保证**；
2. 更好：让命令**等够行数再走**，例如把 `sleep 3` 换成一个「等到收到 5 条
   `resolved=` 就退出」的循环；
3. 至少要在材料里加一句退路：「**若输出为空，把 `sleep` 改成 10 重跑一次**」——
   这句本身就能把这一条从「卡住」降级成「可重试」。

> 顺带说明：这条竞态**同样影响 §3.8 的两条 F3 命令**（它们也用 `sleep 3`），
> 本轮跑 3 次都拿到了完整的 11 行，但那是这台机器**当时空闲**的结果。
> F3 的判据是「工具清单与注解齐全」，拿到 0 行的读者同样会记成 F2/F3 不通过。

---

## 4. 误读（2 条）

### M-10 【验收项 F2 ★】退路的判据引用了一个**真实日志里没有的字面串** —— 读者按它 grep 会得到 0 命中

**材料怎么说**：上一轮修的 F2（端口被占的退路）把「服务到底起来没有」的
**判断依据定成 uvicorn 的日志**，并两次引用了同一串字面量：

> 「uvicorn 会**先**打印 `Application startup complete.`（这句不作数）**再**打印
> `[WinError 10048] error while attempting to bind`，然后自己退出」
> —— [`docs/reports/m10-reader-package.md:425`](m10-reader-package.md) `anchor: error while attempting to bind`

> 「**判断依据是 uvicorn 的日志**：里面有 `[WinError 10048] error while attempting to bind`
> 就是**你的服务没起来**」
> —— [`docs/reports/m10-reader-package.md:446`](m10-reader-package.md) `anchor: error while attempting to bind`

**实测**：本机 8000 与 8011 都被占着（§2.5），照材料走，uvicorn 的日志**原文**是：

```text
INFO:     Started server process [59820]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
```

**材料引用的那一串，日志里没有**：

| 检索 | 命中 |
|---|:---:|
| `grep -c "WinError 10048] error while attempting to bind"` | **0** |
| `grep -c "WinError"` | **0** |
| `grep -c "winerror"`（小写） | 1 |
| `grep -c "error while attempting to bind"` | **1** |

uvicorn 打印的是 **`[Errno 10048]`**，不是 `[WinError 10048]`；`winerror` 只以
**小写**出现在后半句的系统错误文本里。**那一串是材料手写的，不是抄的。**

**为什么算误读**：读者拿到的是一条**明确写着「判断依据是这一串」**的指令。
他 `grep` 那一串 → **0 命中** → 合理地推出「日志里没有绑定错误 → **我的服务起来了**」
→ 回头去 `curl $B/health` → 拿到的是**别人的** `{"status":"healthy"}`（8000 上）
或**另一个 DexAtlas** 的 `{"status":"ok",…}`（8011 上）→ **记成一条 F2 的假卡点**
（「端点与契约表不符」）。**这正是上一轮那条 S-3 想消灭的失败模式**——
上一轮把判据从「敲 `/health`」换成了「读日志」，**方向对了，但换过去的那个
字面串是错的**。

**修法（一行）**：把两处 `[WinError 10048] error while attempting to bind` 换成
**稳定的子串** `error while attempting to bind`（这一串两种形态里都有），
或者**照抄本机真实日志的一行**（像 §3.4 那五行 locator 预期那样，把真实输出贴上去）。
**顺带把「`Application startup complete.` 不作数」这句留着**——它是对的。

---

### M-11 【验收项 C1 ★，影响小】「还没导出就先跑那一条」——「那一条」有两种读法

**材料怎么说**：读者包 §3.4 给了那条「把三个字段连同 `level` 一起打出来」的
命令（这正是 M-8 修复带来的、**本轮实测逐字对得上**的那条），命令下面写：

> 「（`report.json` 由 §3.5 的导出命令生成；还没导出就先跑那一条，或者把下面命令里的
> 路径换成证据包里的 `evidence/reports/report.json`）」
> —— [`docs/reports/m10-reader-package.md:243`](m10-reader-package.md) `anchor: 还没导出就先跑那一条`

**实测**：§3.4 的小节顺序在 §3.5 **之前**。一个照小节顺序走的读者**先跑这条**：

```text
FileNotFoundError: [Errno 2] No such file or directory: 'report.json'
```

**「那一条」指哪一条有两种读法**：指「§3.5 的导出命令那一条」（材料想说的），
还是指「这条打印命令」（字面上更近的那个）。第二种读法下，读者**先跑一条必然
失败的命令**，看到 `FileNotFoundError`，然后**要么自己猜（去 §3.5 找导出命令）、
要么记成一条卡点**。

**为什么算误读（而不是卡住）**：材料其实**给了出路**——同一句括号里的后半句
「或者把下面命令里的路径换成证据包里的 `evidence/reports/report.json`」
**只有在已经导出过证据包的前提下才成立**，所以这条括号实际上**假设读者已经
走过 §3.5**，而 §3.5 在 §3.6 里、也在 §3.4 之后。**读者要做的只是「往后翻一节
先把导出跑了」**——材料不是没有答案，是答案写在后面一节，且那句话有歧义。

**修法（一句话）**：把那半句改成无歧义的写法，例如
「**先跑 §3.5 的导出命令拿到 `report.json`，再跑这条**」，
或者直接把这条命令挪到 §3.5 之后。

---

## 5. 多余（1 条）

### X-4 【G3，验收项 ★】同一节里给了**两段**「实测」示例输出，两段的措辞来自**两种不同的运行结果**

读者包 §9.1 的 G3 下面给了两段标着「实测」的示例：

```text
（单条示例，[`docs/reports/m10-reader-package.md:881`](m10-reader-package.md) `anchor: its launcher had already exited`）
!  jadx exceeded its 1s timeout; its launcher had already exited

（三条示例，[`docs/reports/m10-reader-package.md:887-889`](m10-reader-package.md) `anchor: and was terminated`）
!  apktool exceeded its 1s timeout; its launcher had already exited
!  androguard exceeded its 1s timeout; its launcher had already exited
!  jadx exceeded its 1s timeout and was terminated
```

**这两段里的 jadx 那行说的是两件不同的事**，而源码里这三种措辞对应**三种不同的
运行结局**：

| 措辞 | 源码 | 含义 |
|---|---|---|
| `and was terminated` | [`src/dexatlas/tools/base.py:331`](../../src/dexatlas/tools/base.py#L331) `anchor: and was terminated` | 进程树被**杀掉**了 |
| `its launcher had already exited` | [`src/dexatlas/tools/base.py:333`](../../src/dexatlas/tools/base.py#L333) `anchor: its launcher had already exited` | launcher **自己先退了** |
| `and could not be terminated` | [`src/dexatlas/tools/base.py:334`](../../src/dexatlas/tools/base.py#L334) `anchor: could not be terminated` | 杀不掉，**可能还在跑** |

**本机这一次的实测**（§2.8 第 56 步）三条全是 `its launcher had already exited`，
**连 jadx 也是**——也就是说，材料的三条示例里那一条 `and was terminated`，
**在这台机器上这次没有复现**（它可能在别的运行里出现过，两段示例可能来自两次
不同的运行）。

**为什么算多余**：**同一件事（超时那行长什么样）在同一节里说了两遍，而两遍
不一致**——读者会以为「同一台机器、同一次运行，一会儿这样一会儿那样」，
于是对**哪一条才是「正常」输出**产生怀疑；更糟的是第三种措辞
（`could not be terminated`，那个「**可能还在跑**」的结局）**材料里根本没提**，
而它恰恰是读者最该知道不能忽略的一种。

**判据本身没受影响**（G3 的判据是「**至少一条后端记 `timeout`、不抛异常、
报告照常产出**」，条数与措辞都随后端速度变化，材料在 §9.1 里已经写明了
「判据是行为，不是数字」）。**但示例该统一。**

**修法（一处）**：把三行示例合成一段，并注明措辞会变；或者直接引源码里那三种
结局（那是**更**有教育意义的版本——「杀不掉」是一种真实可能）。

---

## 6. 上一轮那 5 条的逐条去向

> 口径照前一轮：**堵住了** = 读者照材料能拿到结论；**还差什么** = 修复内容本身
> 有欠缺；**新的误读** = 修好之后新出现、或因修复才暴露出来的读法问题。
> **「在修复后的树里」**一列说的是**修复内容本身**是否成立；**「在 tag 树里」**
> 一列说的是**读者实际读到的那一份**是否含这条修复。

| 上一轮的 | 内容 | 在修复后的树（`main` = `be593fa`）里 | 在 tag 树（`v1.0.0` = `2715aef`）里 | 本轮去向 |
|---|---|---|---|---|
| **S-5** ★ | C2 的判据要求「在分析工作区内解析到真实文件」，材料没给可照抄的命令 | ⚠ **基本堵住** —— §3.4 新增的那条命令**照抄能跑**，5 行输出与材料预期**逐行相符**（§2.7 第 45 步），还给了 PowerShell 写法；**但它自己带来两条新缺口**：**S-7**（`sleep 3` 是启动竞态，输不出来时退出码 0、stderr 空）与 **S-8**（判据用的 `text`/`bytes` 字段**这条命令不打印**，见下） | ✗ **没有**（特征串 `一条可照抄的命令` 命中 **0**、`REST 侧没有 locator 解析端点` 命中 **0**） | **修复有效，但没进 tag** → 归入 **S-4**；并新引出 **S-7**、**S-8** |
| **M-8** ★ | evidence 的「工具、版本、locator」三个字段**不在 JSON 顶层** | ✓ **堵住** —— 四份材料口径一致（顶层六键、`level` 在顶层、工具/版本/locator 在 `provenance[]`、一条记录可能不止一条 provenance、MCP 侧是只含 locator 的字符串数组）；**那条打印命令实跑逐字相符**（§2.2 第 18 步）；E-0004–E-0006 各 2 条 provenance 已核；MCP `get_evidence` 实测 `provenance` 确为**字符串数组**（[`src/dexatlas/mcp/tools/evidence.py:34`](../../src/dexatlas/mcp/tools/evidence.py#L34) `anchor: entry.locator for entry in record.provenance`） | ✗ **没有**（`没有可读的文件内容` 命中 **0**；M-8 的四段说明在 tag 树里一段也没有） | **修复有效，但没进 tag** → 归入 **S-4** |
| **M-9** ★ | C2 判据用的词「`path=None` 是设计」与 API 实际返回的字段对不上 | ✓ **堵住** —— 判据一律改用 API 里真实存在的字段（`resolved` / `reason` / `kind` / `text` / `provenance`，[`src/dexatlas/mcp/schemas.py:228`](../../src/dexatlas/mcp/schemas.py#L406) `anchor: class LocatorResolution`）；内部 Python API 的 `path` 保留在括号里（[`src/dexatlas/core/locators.py:161`](../../src/dexatlas/core/locators.py#L161) `anchor: path: Path | None = None`），三份材料口径一致 | ✗ **没有** | **修复有效，但没进 tag** → 归入 **S-4** |
| **G5** ★ | 「证据包不含未引用字符串」在包里**无法判定** | ✓ **堵住** —— 判据改成包里能判的两条 + `manifest.json` 的声明核对（[`docs/reports/m10-acceptance-pack.md:167`](m10-acceptance-pack.md) `anchor: 包里能直接判的两条`）；**实跑逐条核过**：包内 `.apk` **0** 个、`sources/` 目录 **0** 个、`not_included` 三键齐全、`files` 三条全是报告 | ✗ **没有**（`包里能直接判的是两条` 命中 **0**） | **修复有效，但没进 tag** → 归入 **S-4** |
| **F2** ★ | REST 端口 8000 被占时材料**没有退路**，而且那判据会**假通过** | ⚠ **基本堵住** —— 退路（换端口）与「用 uvicorn 日志判断身份」都写进去了，**本机 8000 与 8011 恰好都被占着**（8000 是别的 FastAPI、8011 是另一个 DexAtlas），**两次都按材料走**，全程没有假卡点，§2.5 第 33–42 步全部对上；**但退路的判据引用的日志字面串是错的**（`[WinError 10048] …` → 真日志是 `[Errno 10048] …`） | ✗ **没有**（`Uvicorn running on` 命中 **0**） | **修复有效，但没进 tag** → 归入 **S-4**；并新引出 **M-10** |

### 汇总

- **5 条修复内容本身：3 条完全堵住**（M-8、M-9、G5），**2 条带保留堵住**
  （S-5、F2 —— 方向对、命令能用，但各带一条新缺口：S-7/S-8 与 M-10）。
- **5 条进 tag 的：0 条。** 读者照 §3.1 走，读到的仍是修复前的稿。
- **本轮新挖出 5 条缺口**（卡住 2 / 误读 2 / 多余 1），其中 **S-7、S-8、M-10、X-4
  这 4 条直接来自上一轮那批修复**——**它们不是「材料没改」，是「改得不够」**；
  只有 M-11（§3.4 与 §3.5 的顺序措辞）是新长出来的。

---

## 7. 40 个验收项的三类归属

> 口径照前几轮：**能自己判** = 读者照材料能给出「通过 / 不通过 / 未验证」；
> **必须问作者** = 判据或材料有缺口，读者只能靠问；
> **没判据** = 判据本身不足以判定。
>
> **本轮给两列**，因为这轮的读者面对的是**两棵不同的树**：
> **修复后的树**（`main`）是材料定稿后的样子，**tag 树**（`v1.0.0`）是读者
> 照 §3.1 真会拿到的东西。

| 分类 | 修复后的树（`main`） | tag 树（`v1.0.0`） | 编号 |
|---|:---:|:---:|---|
| **能自己判** | **39** | **35** | 修复后的树：A1–A7、B1–B6、C1、C3–C6、D1–D5、E1–E5、F1–F6、G1–G5（**除 C2**）<br>tag 树：同上，但**去掉 C1、C2、F2、F3**（这四项的判据或命令只在修复后的树里） |
| **必须问作者** | **1** | **4** | 修复后的树：**C2**（★）<br>tag 树：**C1**（★）、**C2**（★）、**F2**（★）、**F3**（★） |
| **没判据** | **0** | **1** | tag 树：**G5**（★「证据包不含 APK、全量源码、未引用字符串」——「未引用字符串」在包里无法直接判定） |

### C2 为什么还留在「必须问作者」——以及它离关闭有多近

**第三轮的 C2 是「没有命令」；这一轮的 C2 是「命令有了，判据要的两个字段没被打印出来」。**

C2 的判据要区分三件事（[`docs/reports/m10-acceptance-pack.md:117`](m10-acceptance-pack.md) `anchor: 按构造解析`）：

| `resolved` | 是什么 | C2 怎么判 |
|---|---|---|
| `true`，`reason` 是绝对路径，**且 `text` 里有内容（`bytes > 0`）** | 文件级 locator | 通过：核对那个文件确实存在 |
| `true`，**没有可读的文件内容**（DEX 成员的 `text` 是 `null`；裸树的是空文本——`text.text` 为空串、`bytes` 为 0） | DEX 成员 locator 与裸树 locator | 通过：**不是失败** |
| `false` | 解析不出来 | 单独列出来 |

**而 §3.4 给的那条命令只打印 `resolved` / `kind` / `locator` / `reason`
（[`docs/reports/m10-reader-package.md:280`](m10-reader-package.md) `anchor: resolved=%s kind=%s locator=%s reason=%s`）。**`text` 与 `bytes`
**一个都没打印**。本轮把整条响应打出来看过，差别是**实在的**：

| locator | 命令打印出来的 | 命令**没**打印但真实存在的 |
|---|---|---|
| `androguard:classes.dex#com.example.demo.Crypto` | `resolved=True kind=None reason=com.example.demo.Crypto is in classes.dex` | `text` = **`null`** |
| `jadx:sources`（裸树） | `resolved=True kind=java reason=E:\…\jadx\sources` | `text` = `{"text":"", "bytes":0, …}` |
| `jadx:sources/com/example/demo/MainActivity.java`（文件级） | `resolved=True kind=java reason=E:\…\MainActivity.java` | `text` = `{"text":"package com.example.demo;…", "bytes":675, …}` |

**从打印出来的那几列看，裸树与文件级两行长得几乎一样**：`resolved=True` +
一个绝对路径。读者要分清它们，只能靠**判据表里那个没被打印的 `bytes`**，
或者自己 `ls` 一下那个路径是不是目录——**材料没有授权后者**
（§6 明确写「作者未在文档中公开的任何步骤，用了就使相关验收项不能判通过」）。

**所以这一轮的记法是**：**C2 仍是「必须问作者」，但比上一轮小一个数量级**——
上一轮是「一条命令都没有」，这一轮是「命令有了，差的只是让那条命令多打印两个字段」。
**关掉它只需要在 §3.4 那条命令的 python 过滤器里加一个 `text` 的摘要**
（例如把 `s['text']` 打成 `None` 或 `bytes=N`），
**或者把判据表的判别式换成命令里已有的字段**（例如「`reason` 是绝对路径**且那个路径是文件**」）。

> **本轮也给出另一种读法**：若作者认为「读者能自己 `ls` 一下那个路径」就算
> 「能自己判」，那么 C2 可以归入**能自己判 40 / 必须问作者 0**。
> **本报告取保守的一边**（39 / 1 / 0），因为材料自己的判据表用的就是 `bytes`。

### 与前三轮的差别

| | 第一轮 | 第二轮 | 第三轮 | **第四轮** |
|---|---|---|---|---|
| 能自己判（修复后的树） | 39 | 39 | 35 | **39** |
| 能自己判（tag 树） | 39 | 39 | 35 | **35** |
| 必须问作者（修复后的树） | 1 | 1 | 4 | **1** |
| 必须问作者（tag 树） | 1 | 1 | 4 | **4** |
| 没判据（修复后的树） | 0 | 0 | 1 | **0** |
| 没判据（tag 树） | 0 | 0 | 1 | **1** |
| 走过的步数 | 34 | 59 | 57 | **62** |
| 卡住 | 2 | 3 | 3 | **2** |
| 误读 | 7 | 6 | 3 | **2** |
| 多余 | 3 | 2 | 1 | **1** |

> **这张表里的第一轮数字，本轮是逐条查过原始报告的**，不是抄第三轮那张对照表：
> [第一轮](invitation-reader-rehearsal.md) 的 §6 合计行写着
> 「**39** / **1（G3）** / **0**」，§0 写着「走过的步数 **34** 步」。
> **第三轮那张「与前两轮的差别」表把第一轮记成了「33 / 5 / 2、41 步」——
> 四个数都与第一轮的原表不符**（33 那个数是第一轮 §0 里「**材料要求的 33 步**」，
> 不是走过的步数；41 那个数在第一轮的报告里**根本没有出现过**）。
> 这一轮不修第三轮的报告（那是别的窗口的记录），**只把正确的数记在这里**。

**三件要说清楚的事**：

1. **「能自己判」回到了 39**——这是四轮以来的最高，且**第一次两棵树都给出数**。
   上一轮的 35 是因为 4 项的判据/命令只在修复后的树里；这一轮这些都在了
   （C1、M-8 的四段说明、C2 的解析命令、F2 的六端点与退路、F3 的两条协议命令、
   G5 的可判判据）。**但读者拿到的是 tag 树上的 35。**
2. **卡住从 3 降到 2、误读从 3 降到 2、多余从 1 降到 1**——
   **这个「降」要小心读**：它**不是**材料变好了，而是**上一轮的 11 条缺口被
   上一轮那批修复关掉了**，同时**这批修复自己带进来 4 条新缺口**
   （S-7、S-8、M-10、X-4）。**缺口总数从 7 变成 5，净减 2**，
   但**如果只数「这一轮新挖出几条」，那是 5 条——比上一轮的 3 条多**。
3. **「必须问作者」从 4 降到 1**（修复后的树），**「没判据」从 1 降到 0**——
   G5 这一条**真的关掉了**：包内不含 APK、不含全量源码两条都能在包里判，
   「未引用字符串」改由 manifest 的声明核对，**判据与包里的东西对得上**。

---

## 8. 什么没验、什么留给了谁

### 本窗口**没有**验的

- **Docker 路线**（读者包 §3.2 路线 B）——本轮未跑。上一轮也未跑。
  材料给的数（「首台机器无层缓存、走代理下载时实测 1099 秒 ≈ 18 分 19 秒」）
  本轮**无法复核**。
- **`scripts/fetch-fixtures.sh`**——本轮**不联网**，改为从主检出**复制**已取好的
  两个 fixture（`TestActivity.apk` / `multidex.apk` + `SOURCES.md`）。
  **这意味着本轮没有验证脚本本身**（它能不能跑、gh 未登录时怎么报错），
  也**没有验证「取到之后套件零 skip」**这个说法——本轮**没有跑完整套件**。
- **完整测试套件与覆盖率**——按任务要求**没有跑**
  `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率），
  也**没有跑 `pytest -m slow` 的完整套件**。
- **案例的第二、第三份**（obfuscated-app、第三方包）——读者包 §3.7 说「有余力再抽查」，
  本轮只核了 demo-app 那份的**全部 8 条命令**（逐条对上）。
- **§4 的高风险声明清单**（Agent 层级 2 的 49/60 = 81.7% 等）——
  本轮只核了**它们在文档里能不能找到**（E5 的 92 题与 20 题两份报告都能找到），
  **没有复核那 49/60 的数字本身**（那是 `scripts/m6_level2_retest4_report.py`
  从 committed trace 重算的事，不在本轮范围）。
- **`git push` / GitHub Release 正文**——本轮**没有联网**，没有取 Release 正文，
  没有核「对外文本里的数字与报告一致」。

### 留主会话的（本窗口**没有手改任何既有文件**——只把 `main` 的新 tip 合了进来，见 §10）

| # | 事项 | 本窗口的证据 | 性质 |
|---|---|---|---|
| 1 | **重打 `v1.0.0` tag** —— 这是把 5 条修复送到读者手里的**唯一**途径 | §3 的 S-4：tag 仍指 `2715aef`，`main` 已到 `be593fa`，中间 60 个提交；5 条修复的特征串在 tag 树里**命中全为 0** | **发版那一步**（不是读者那一步） |
| 2 | **重打 tag 之前要重锚 release body** —— 上一轮 §8.1 已经给过完整分析 | 本轮补两条**新事实**：<br>（a）`v1.0.0..main` 之间 **`src/` 一行未改**，但 **`scripts/` 与 `tests/` 变了**（`check-doc-citations.py` **+1055 行**、`check-platform-gates.py` 新增、`refresh-report-figures.py` +332 行，等 12 个文件）；而文档里**确实有**指向这些文件的行号引用（如 `docs/reports/ci-gate-coverage.md` 里的 [`scripts/refresh-report-figures.py:111`](../../scripts/refresh-report-figures.py#L111) `anchor: The files that decide how the measurement comes out`、[`scripts/verify-public-contracts.py:453`](../../scripts/verify-public-contracts.py#L453) `anchor: get_project_status`）——**tag 一换，这些引用要按新树重锚**。<br>（b）**基线提交 `a785d01` 上的引用检查器就已经是红的**：本窗口在基线上跑了一次作对照，`12 citation(s) no longer say what they say`、退出码 **1**——**9 条在 release body（它绑在 `v1.0.0` 那棵树上）、3 条在刚被 `check-doc-citations.py` 涨了 1055 行挪了位的文档里**。**这一条不是本窗口造成的**（见 §8.2） | **重打 tag 的前置条件** |
| 3 | **`docs/reports/m10-reader-rehearsal-4th.md` 登记进 `scripts/check-doc-citations.py` 的文档清单** | 本文件里 **40 处** `file:line` 引用（正文 16 处、§8 交接表 3 处、§9.3 核法表 21 处），**逐条手工核过**（§9.3 列了核法），并且**每一处都带了 `anchor:` 声明**——本窗口用检查器自己的 `resolve_citations` + `check_anchor` 跑了一遍：**40/40 通过、0 条孤立声明**（核法见 §9.3）。但文件**不在**检查器的文档清单里，所以那些引用**目前不被机器检查** | 按分工留给主会话统一登记 |
| 4 | **五条新缺口的修**（S-7 / S-8 / M-10 / M-11 / X-4） | §3、§4、§5 各自给了**具体的改法**（都是一行以内的改动） | 材料侧 |
| 5 | **F2 那两个「占着 8000 / 8011 的服务」** | §2.5 的端口表 | 机器环境，与材料无关；读者换机器会遇到别的端口 |
| 6 | **基线上那 12 条漂移的引用**（§8.2） | §8.2 的对照实验 | 引用工作那一扇的范围 |

### 8.1 【S-7】把上一轮那条命令改成「等够行数再走」—— 顺便把 F3 那两条一起改

上一轮 §9 给了「给下一轮的方法」。这一轮补一条**具体的**：

**S-7 的最小修法**（三处命令共用同一个 `sleep 3`）：把
`{ printf … ; sleep 3; }` 改成
`{ printf … ; sleep 3; sleep 10; }`（多等一次，代价是几秒），
或者更好——在 python 过滤器里**等收满 N 条再打印**。
**三处都要改**：§3.4 的 locator 解析命令、§3.8 的两条 F3 命令。

**为什么建议三处一起改**：这三条命令**共用同一个失败形态**——
**输出为空、退出码 0、无 stderr**。本轮只实测了 §3.4 那条（失败率肉眼可见），
§3.8 那两条本轮 3 次都成功，**但那是机器空闲时的结果**。

### 8.2 【门禁】本窗口的门禁状态：**除引用检查器外全绿，引用检查器在基线上就已经是红的**

| 门禁 | 结果 |
|---|---|
| `ruff check .` | ✅ `All checks passed!` |
| `ruff format --check .` | ⚠️ **2 个文件要重排**：`scripts/check-doc-citations.py` 与 `tests/test_doc_citations.py`（各差一个空行）。**这两个文件是本窗口合并进来的 `a785d01` 带来的**——**在基线 `a785d01` 上跑，同样是这 2 个文件**（对照实验）。**本窗口没有改 `scripts/` 与 `tests/`**（那是任务里的硬约束），所以没跑 `ruff format`；**修法是 `ruff format scripts/check-doc-citations.py tests/test_doc_citations.py`**，一条命令，交给那两扇窗口的属主 |
| `mypy` | ✅ `Success: no issues found in 68 source files` |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | ✅ 退出码 **0**，无输出 |
| `scripts/remap-citations.py` | ✅ 跑过，**0 条移动**（本窗口没让任何引用漂走） |
| `scripts/check-doc-citations.py` | ❌ **退出码 1，12 条漂移** —— **但这 12 条在基线提交 `a785d01` 上就已经存在**（对照实验：在 `.scratch/` 的副本里 checkout `a785d01` 跑同一个检查器，**同样是 12 条、退出码 1**）。**本窗口的文件一条都没在里面**（它不在检查器的文档清单里，而它自己的 **40 条引用逐条核过、全部带 `anchor:` 声明、40/40 通过**） |
| `scripts/check-version-claims.py --base auto` | ✅ 退出码 0 |

**那 12 条是谁的**：

- **9 条在 `docs/reports/v1.0.0-github-release-body.md`** —— 那份 release body
  **绑在 `v1.0.0` 那棵树上**（`TREE_DOCUMENTS`），它里面的数字
  （`1694 passed` / `sha256:18f3ab15…` / `49 live` / `28 REST` …）是**那棵树
  当时的测量**，而工作区已经往前走了。**这正是上一轮 S-6 说的那件事**：
  **重打 tag 之前要重锚 release body，重锚要排在重测之后**——
  本轮把它量化了：**这 9 条现在就是红的**。
- **3 条在别的文档**（`post-release-rehearsal.md`、`citation-anchor-declarations.md`、
  `handwritten-numbers-audit.md`）—— 它们引用的 `scripts/check-doc-citations.py`
  的行号，因为那个脚本在提交 `61a2700` 里**长了 1055 行**而挪了位
  （检查器报「`TREE_DOCUMENTS` is at line 261」这类）。
  **`scripts/remap-citations.py` 对这三份文档移动了 0 条**——
  按 CLAUDE.md 的说法，「只指位置」的引用留给检查器报、给人判；
  **这三条是别人的文件，本窗口没有改**。

**本窗口没有动别人的文件**（§10）。**引用检查器的红不在本窗口的责任范围里，
但它会挡住整条门禁**——这一点留给主会话统一处理。

---

## 9. 复验这一轮的方法（给下一轮）

### 9.1 怎么验「上一轮那 5 条」

**不要只读材料。** 这一轮最关键的三个发现（S-7、M-10、S-8）**读材料全都读不出来**：

- **S-7** 只有在**把 `sleep` 改小**、看到输出归零时才现形；
- **M-10** 只有在**真的把 uvicorn 起在 8000 上、把日志整行抄下来、拿材料引用的
  那一串去 grep** 时才现形（`grep -c` = 0）；
- **S-8** 只有在**把 MCP 的整条响应打出来**（而不是材料给的那四个字段）时才现形。

**下一轮的起点建议**：先跑
`git rev-parse "v1.0.0^{commit}"`——如果它还等于 `2715aef`，**S-4 一字未动**，
§6 那张表也不用重做；如果它变了，**先确认 tag 树里那 5 条修复的特征串是否命中**，
再重跑 §6 的「在 tag 树里」一列。

### 9.2 本轮新增的、值得下一轮复用的三个测量

| 测量 | 怎么做 | 为什么值得复用 |
|---|---|---|
| **MCP server 启动延迟** | 写一个 20 行的 Python：spawn `uv run --no-sync dexatlas-mcp`、写一行 `initialize`、量到第一行响应 | 这是**所有 `sleep N` 式命令的余量**；下一轮在别的机器上量一次就知道那条命令稳不稳 |
| **端口占用体检** | `curl -s -m 3 http://127.0.0.1:<port>/health` + `netstat -ano \| grep ":<port>"` | F2 的退路只有在**端口真的被占**时才能验；这台机器 8000 与 8011 **同时**被占，正好是材料说的最难的情形 |
| **把 MCP 响应整条打出来** | 把 `structuredContent` 整个 `json.dumps` 出来，而不是挑字段 | 材料给的命令**挑了字段**，被挑掉的字段正是判据要用的（`text`/`bytes`）——**这一招把 S-8 挖出来了** |

### 9.3 本报告里 `file:line` 引用的核法

本文件**不在** `scripts/check-doc-citations.py` 的文档清单里（按分工留给主会话
统一登记），所以下面的引用是**逐条手工核**的：

| 引用 | 核法 |
|---|---|
| [`src/dexatlas/tools/base.py:331`](../../src/dexatlas/tools/base.py#L331) `anchor: and was terminated` / [`:333`](../../src/dexatlas/tools/base.py#L333) `anchor: its launcher had already exited` / [`:334`](../../src/dexatlas/tools/base.py#L334) `anchor: could not be terminated` | `sed -n '325,336p'` 逐行看，三行分别就是那三句 |
| [`src/dexatlas/mcp/tools/evidence.py:34`](../../src/dexatlas/mcp/tools/evidence.py#L34) `anchor: entry.locator for entry in record.provenance` | `sed -n '30,38p'`，第 5 行是 `provenance=[entry.locator for entry in record.provenance],` |
| [`src/dexatlas/mcp/schemas.py:228`](../../src/dexatlas/mcp/schemas.py#L406) `anchor: class LocatorResolution` | `sed -n '400,412p'`，第 7 行是 `class LocatorResolution(BaseModel):` |
| [`src/dexatlas/core/locators.py:161`](../../src/dexatlas/core/locators.py#L161) `anchor: path: Path | None = None` | `sed -n '155,165p'`，第 7 行是 `path: Path | None = None` |
| [`docs/reports/m10-reader-package.md:243`](m10-reader-package.md) `anchor: 还没导出就先跑那一条` / [`:264`](m10-reader-package.md) `anchor: 一条可照抄的命令` / [`:280`](m10-reader-package.md) `anchor: resolved=%s kind=%s locator=%s reason=%s` / [`:318`](m10-reader-package.md) `anchor: text.text` / [`:425`](m10-reader-package.md) `anchor: error while attempting to bind` / [`:446`](m10-reader-package.md) `anchor: error while attempting to bind` / [`:500`](m10-reader-package.md) `anchor: sleep 3` / [`:881`](m10-reader-package.md) `anchor: its launcher had already exited` / [`:887-889`](m10-reader-package.md) `anchor: and was terminated` | `grep -n` 逐条取行号，再 `sed -n` 看该行原文与材料里引用的一致 |
| [`docs/reports/m10-acceptance-pack.md:117`](m10-acceptance-pack.md) `anchor: 按构造解析` / [`:167`](m10-acceptance-pack.md) `anchor: 包里能直接判的两条` | `sed -n '112,168p'` 看 C2 与 G5 两行 |
| [`scripts/refresh-report-figures.py:111`](../../scripts/refresh-report-figures.py#L111) `anchor: The files that decide how the measurement comes out` / [`scripts/verify-public-contracts.py:453`](../../scripts/verify-public-contracts.py#L453) `anchor: get_project_status` | §8 交接表第 2 行里的两处示例引用；`sed -n` 核该行原文 |

**机器核过**：本窗口把检查器自己的两个函数调起来，对**本文件**跑了一遍
（`resolve_citations` + `check_anchor`）——**识别到 40 条引用、40 条全部带声明、
40/40 锚点命中、0 条孤立声明**。这段脚本在
`.scratch/reader-rehearsal-4th/verify-my-citations.py`（**不入库**），
它只**读** `scripts/check-doc-citations.py`，**没有改**。

---

## 10. 本窗口做的 / 留给主会话的

**本窗口做的**：

- 写了这**一份**文件：`docs/reports/m10-reader-rehearsal-4th.md`。
- **没有改任何既有文件**——四份 M10 材料、契约表、README、`docs/status.md`、
  `docs/reports/README.md`、`scripts/`、`tests/` 一行未动。
- **没有跑** `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率）。
- 预演的产物全在 `.scratch/reader-rehearsal-4th/`（副本、脚本、日志），
  **不在仓库里**；`fixtures/apk/` 里的两个第三方 fixture 是从主检出复制进去的，
  **没有提交**（它们本来就不在版本控制里）。
- **把 `main` 的新 tip（`a785d01`）合进了本分支**——因为预演结束时基线已经往前
  走了，而门禁要在这棵树上跑。**这一个合并提交带进来的是别人的东西**
  （`docs/reports/` 下四份文件与 `scripts/check-doc-citations.py`、
  `tests/test_doc_citations.py` 的改动，见 §8.2），**本窗口没有改它们**。
- 本文件里的 **40 处 `file:line` 引用**全部带 `anchor:` 声明，
  并用检查器自己的函数核过：**40/40 命中、0 条孤立声明**（§9.3）。
- 提交在**本窗口自己的分支**上，**没有推 main、没有合并到 main**。

**留给主会话的**：

1. **重打 `v1.0.0` tag**（§8 表第 1 行），以及**重打之前**的 release body 重锚
   （§8 表第 2 行）——这两件是「读者能不能看到那 5 条修复」的**唯一**通路。
2. **把本文件登记进** `scripts/check-doc-citations.py` 的文档清单（§8 表第 3 行）。
3. **五条新缺口的修**（§8 表第 4 行）：S-7（三处 `sleep 3`）、S-8（多打印两个字段）、
   M-10（换那串日志字面量）、M-11（改半句措辞）、X-4（统一 G3 的示例）。
4. **重测与对外文本同步**——按 CLAUDE.md 的顺序：先改代码 → `ruff format` → 再测；
   本轮**没有碰源码**，所以**没有动过任何测量数字**。
5. **基线上那 12 条漂移的引用**（§8.2）——**9 条在 release body**（它绑在旧 tag 树上，
   **要等重测之后随重打 tag 一起重锚**），**3 条在别的文档**（`check-doc-citations.py`
   涨了 1055 行把行号带偏了，`remap-citations.py` 对它们移动 0 条，要人判）。
   **本窗口一条都没碰**——但它们**让整条引用门禁是红的**。

---

## 11. 一句话结论

**上一轮那 5 条修复，内容本身全部成立**（实测逐条对上了，3 条完全堵住、2 条带保留）；
**但它们一条都没进 tag**（`v1.0.0` 仍指 `2715aef`，`main` 已到 `be593fa`）——
**读者照材料 §3.1 走，读到的仍是修复前的稿**（S-4 延续）。
**这一轮新挖出 5 条缺口**（卡住 2 / 误读 2 / 多余 1），
其中 **4 条直接来自上一轮那批修复**——S-7（那条 locator 解析命令是启动竞态，
输不出来时退出码 0、stderr 空）、S-8（C2 判据要的 `text`/`bytes` 那条命令不打印）、
M-10（F2 退路判据引用的日志字面串在真实日志里**不存在**）、X-4（G3 的两段示例互相不一致）。
**材料已经从「不能判」走到「基本能判」，但还没到「照抄就一定跑得出来」。**
