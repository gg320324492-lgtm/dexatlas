# M10 邀请函 —— 读者视角预演记录（第三轮，只读）

> **本文件的性质：** 这是一次**只读预演**：照着**定稿后的**邀请函与读者包给的命令，
> 从 clone 走到打分的模板前，把每一步实际跑了一遍，记录「命令 / 实际输出 /
> 与材料是否对得上 / 耗时」，并标出会让读者卡住、被误读或觉得多余的地方。
> 口径与前两轮（[第一轮](invitation-reader-rehearsal.md)、
> [第二轮](m10-reader-rehearsal-2nd.md)）一致：
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
| 预演日期 | 2026-11-19（第三轮） |
| 本轮验收对象 | `v1.0.0` 这个 tag 所指的提交 |
| `git rev-parse "v1.0.0^{commit}"` | `2715aefda06c3cbbc055a9edf795535e71464068` |
| `git rev-parse v1.0.0`（tag 对象） | `b2720eecc2af37ae6a715c4a4b1634ab31dda40b`（**与上一串不相等**） |
| `git cat-file -t v1.0.0` | `tag`（**附注 tag**） |
| 副本来源 | 本地克隆 `E:/Dexatlas` → `.scratch/reader-rehearsal-3rd/dexatlas`（**离线**；未走 GitHub，见 §8） |
| OS | Windows 11 Pro 10.0.26300 |
| Python / uv / JDK | 3.12.10 / 0.11.21 / 21.0.11（OpenJDK） |
| 后端 | jadx 1.5.2、apktool 2.11.1（`E:\Dexatlas\.scratch\backends`，经 `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 指向）、androguard 4.1.4 |
| 其它 | gh 2.97.0（已登录）、Docker 29.9.2（本轮未用 Docker 路线） |
| 走过的步数 | **57 步**（材料路径上的命令）；**跳过 1 步**（Docker 路线）；**1 步用等价静态检查代替**（「双击打开 HTML」） |
| 计算耗时合计 | 材料路径上的命令约 **2 分钟**（不含阅读材料与思考的时间；`uv sync` 另计约 16 s，见 §2.1） |

**副本与 tag 的纪律**：克隆后 `git tag -l` 拿到全部 8 个 tag，`git checkout v1.0.0`
进入 detached HEAD（`HEAD is now at 2715aef`），`git status --porcelain` 除本轮
自己的产物外无输出，`git rev-parse HEAD` = `2715aefda06c3cbbc055a9edf795535e71464068`。
这一条链路是通的。

**这一轮与上一轮最大的不同**：上一轮预演的对象是**同一棵树**（`2715aef`），
但材料在那一轮之后做过一轮修复（9 处缺口 + 2 处「多余」，逐条记在
[材料修复记录](m10-material-fixes.md)）。本轮的核心任务就是逐条核对那 11 条
修复**到底堵住没有**——而核对的方式必须是**实跑**，不是读修复记录本身。

**这一轮最重要的结论（一句话）**：**11 条修复在「随函发出的那一份材料」里
全部成立；但 tag 指向的那棵树上，一条都没有。** 详见 §3 的 S-4。

**另一条给主会话的**（本轮后补）：**重打 tag 这一步本身有一个前置条件** ——
引用检查器把 release body 的 64 条引用绑在 `v1.0.0` 那棵树上，tag 一换就要
重核，否则门禁立刻红。详见 §3 的 S-6 与 §8.1。

---

## 1. 这一轮的做法

前两轮预演都已确立一条纪律：**只有实跑才能发现缺口**。第二轮记下的 G3 自相矛盾、
F3 无命令可用、tag 树里 hash 是占位符，三条都是读材料读不出来的。所以本轮的
做法与前两轮一致，也与任务要求一致：

1. **克隆并 checkout `v1.0.0`** —— 走 §3.1；
2. **照材料给的命令一条条跑** —— 走 §3.2–§3.9、§9.1、§9.2，每条记
   「命令 / 实际输出 / 与材料是否对得上 / 耗时」；
3. **逐条核对上一轮那 11 条** —— 对每一条，先在**修复后的树**上验证修复内容本身
   是否成立，再在 **tag 树**上验证读者实际读到的那一份是否含修复；
4. **给 40 项做三类归属** —— 能自己判 / 必须问作者 / 没判据。

---

## 2. 读者实走：步骤与实测输出

### 2.1 §3.1–§3.2 环境准备（验收项 A1、A2、A3）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 1 | `git clone --no-hardlinks <本地> .scratch/reader-rehearsal-3rd/dexatlas` | 0 | `done.` | **0.5 s**（本地路径克隆，见下方注） | ✓ |
| 2 | `git checkout v1.0.0` | 0 | `HEAD is now at 2715aef run 记录改成当前的事实…` | 1 s | ✓ |
| 3 | `git rev-parse HEAD` | 0 | `2715aefda06c3cbbc055a9edf795535e71464068` | 0.1 s | ✓ 与随函 §2 那一串**逐字相同** |
| 4 | `git status --porcelain` | 0 | 无输出（干净） | 0.1 s | ✓ |
| 5 | `git tag -l` | 0 | 8 个 tag，含 `v1.0.0` | 0.1 s | ✓ |
| 6 | `uv sync --extra dev --extra analysis --extra mcp --extra demo` | **0** | 101 行；`EXIT=0` | **约 16 秒**（uv 缓存已热；另测一次全新克隆 + sync = 3.3 s） | ✓ |
| 7 | `uv run dexatlas backends`（**未设**后端变量） | 0 | `jadx not installed` / `apktool not installed` / `androguard available 4.1.4`；`2 backend(s) unavailable.` | 1.5 s | ✓ 与 §3.2 的预期形状一致 |
| 8 | 同上（**设了** `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR`） | 0 | 三行全 `available`：jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4 | 1.2 s | ✓ |

> **第 1 步与第 6 步的耗时不能与材料的数比**：材料 §3.1 写的是
> `git clone https://github.com/gg320324492-lgtm/dexatlas.git`（**走网络**），
> 本轮按任务的「不联网」约束改成了**从本地克隆**（`--no-hardlinks`），因此
> 0.5 秒；[读者实走演练](reader-dry-run.md:74) 的 46 秒是**网络克隆**的实测。
> 同理，第 6 步的 16 秒是**uv 缓存已热**时的数（冷缓存 + 走网络的那次是
> 218 秒，见同文件 :74）。**本轮不判 A7 的耗时**（它要的是读者自己那台的数）。

### 2.2 §3.3–§3.5 首次分析与三格式报告（验收项 A4、A5、D1、D2）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 9 | `uv run dexatlas analyze examples/demo-app/demo.apk` | **0** | `✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (4.3s)` | 5.2 s | ✓ **A4 基线逐字对上** |
| 10 | `dexatlas manifest apk_80a8fe0e81204c9f` | 0 | `com.example.demo` / `version 1.0 (1)` / `sdk min 24 / target 34` / `permissions 1` / `components 3`；两个 exported 组件均 `no permission guard` | 0.8 s | ✓ B2 逐项对上 |
| 11 | `dexatlas search … "Crypto"` | 0 | 命中 1 class + 3 method + 2 string（`Crypto.java`、`Lcom/example/demo/Crypto;`） | 0.9 s | ✓ |
| 12 | `dexatlas search … "sk_live"` | 0 | 一行：`string │ sk_live_2f8a91c4e7b3` | 0.8 s | ✓ `Kind=string` |
| 13 | `dexatlas source … com.example.demo.MainActivity` | 0 | `source kind: java` / `jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java` | 0.9 s | ✓ B4 对上 |
| 14 | `dexatlas xrefs … MainActivity.describe(…)` | 0 | `1 call site(s), 1 call edge(s)` / `classes.dex@34` | 0.9 s | ✓ B5 对上 |
| 15 | `dexatlas analyze … -o report.md --json report.json --html report.html` | **0** | 三份文件：5 262 B / 11 747 B / 8 606 B | 4.5 s | ✓ A5 |
| 16 | 读 `report.json` 顶层字段 | — | `['errors','evidence','generated_at','latest_attempt_status','manifest','project','run','schema_version','summary','tools']` —— **10 个** | 0.3 s | ✓ F4 |
| 17 | 同上 `schema_version` | — | `3` | 0.1 s | ✓ 契约表 §5.1 说「当前 `3`」 |
| 18 | D2 抽查 5 个计数在 md / json / html 三处一致 | — | classes 5 / methods 8 / call_sites 23 / call_edges 21 / resource_strings 1 —— 三处**全部 True** | 0.3 s | ✓ |
| 19 | D1 离线检查 `report.html` | — | `<script` 0 处、`http://` 0 处、`https://` 0 处、`<link` 0 处、`cdn.` 0 处；含 project id | 0.3 s | ✓ **D1 通过**（无任何外部请求） |
| 20 | D5 转义检查 | — | `onerror=` 0、`onload=` 0、`javascript:` 0 | 0.2 s | ✓ |

### 2.3 §3.6 证据包导出与校验（验收项 C5、C6、D3、D4、G5）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 21 | `dexatlas export apk_80a8fe0e81204c9f -o evidence.zip` | 0 | `✓ evidence package → evidence.zip (4 files: 3 reports + 1 manifest, apk 80a8fe0e81204c9f)` | 1.1 s | ✓ 「4 files」与 zip 内条目数一致 |
| 22 | `verify_package` + `verify_citations` | 0 | `{'citations_total': 14, 'citations_resolved': True, 'citations_unresolved': [], 'apk_sha256': '80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9'}` | 1.0 s | ✓ C5 / C6 |
| 23 | **迁移复验**：复制到 `/tmp/c6-move` 后再跑一次校验 | 0 | 同一串输出，逐字相同 | 0.9 s | ✓ C6「包内路径不指向生成它的机器」 |
| 24 | 解压后看目录树 | — | `evidence/manifest.json` + `evidence/reports/{report.html,report.json,report.md}` —— **4 个文件**，**没有 `sources/`** | 0.4 s | ✓ D4（裸树 locator → 按构造解析） |
| 25 | 读 `evidence/manifest.json` | — | `not_included` 三条齐全：`apk` / `full_sources` / `unrelated_strings`；`files` 清单 3 条（**不含 manifest 自己**） | 0.3 s | ✓ D3 / G5 |

> **第 24–25 步值得单说**：材料 §3.6 特别提醒「你数 zip 得到 4、CLI 也说 4 —— 一致；
> 若只数 manifest 的清单会得到 3，那是少算了一个」。本轮实测**确认了这个提醒
> 是对的**（`files` 清单 3 条 + manifest 自己 1 条 = 4）。这一处材料**没有错**。

### 2.4 §3.8 契约活检（验收项 F1、F5、F6）

| # | 命令 | 退出码 | 实际输出（要点） | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 26 | `dexatlas analyze examples/demo-app/demo.apk` | **0** | 同第 9 步 | 4.4 s | ✓ F1 的 0 |
| 27 | `dexatlas search apk_80a8fe0e81204c9f __no_such_term__` | **1** | `No matches for '__no_such_term__'.` | 0.8 s | ✓ F1 的 1 |
| 28 | `dexatlas analyze README.md` | **2** | `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives` | 0.7 s | ✓ F1 的 2 |
| 29 | `pytest tests/test_public_contracts.py -q` | **0** | `31 passed in 6.01s` | 7.3 s | ✓ F5 |
| 30 | `python scripts/verify-public-contracts.py` | **0** | `48/48 checks passed` / `the public contracts hold` | 15.8 s | ✓ F6 |
| 31 | `python scripts/check-contract-records.py --expect with-jadx` | **0** | `the live run: 48 checks (27 REST + 6 MCP + 15 CLI), 48 passed, exit 0` / `PASS the table records 6 run(s)` | 16.2 s | ✓ §9.2 的退出码 0 |

### 2.5 §3.8 F2 的六类 REST 端点（验收项 F2）

| # | 命令 | 状态码 | 实际输出（要点） | 对得上吗 |
|---|---|:---:|---|---|
| 32 | `uvicorn dexatlas.api.app:app --port 8000` | — | **失败**：`Application startup complete.` 之后打 `[WinError 10048] error while attempting to bind`；`curl localhost:8000/health` 返回 `{"status":"healthy"}`，`/projects` 返回 `{"detail":"Not Found"}` | **正是 §3.8 描述的场景**——见下 |
| 33 | 同上，`--port 8011` | — | `INFO: Uvicorn running on http://127.0.0.1:8011 (Press CTRL+C to quit)` | ✓ |
| 34 | `curl -s localhost:8011/health` | — | `{"status":"ok","version":"1.0.0","backends":{"jadx":"1.5.2","apktool":"2.11.1","androguard":"4.1.4"}}` | ✓ 身份核对通过 |
| 35 | `POST /analyze`（multipart） | **202** | `{"project_id":"apk_80a8fe0e81204c9f","status":"completed","detail":"/projects/apk_80a8fe0e81204c9f"}` | ✓ 上传 |
| 36 | `GET /projects` | **200** | `[{"id":"apk_80a8fe0e81204c9f","status":"completed","class_count":5,"method_count":8,"reference_count":23,"call_site_count":23,"call_edge_count":21,"evidence_count":11,"resource_count":1,…}]` | ✓ 项目 |
| 37 | `GET /projects/{pid}/runs` | **200** | `{"project_id":…,"total":2,"published_run_id":"run_b6ccbae53ef24111","runs":[…]}` | ⚠ **见 §4 的 M-7** |
| 38 | `GET /projects/{pid}/classes?limit=2` | **200** | `{"project_id":…,"total":5,"classes":[{…"name":"com.example.demo.Crypto","kind":"class",…}]}` | ✓ 符号 |
| 39 | `GET /projects/{pid}/classes/com.example.demo.MainActivity/source`（只取头） | **200** | `x-dexatlas-source-kind: java` / `x-dexatlas-source-tool: jadx` / `x-dexatlas-source-locator: jadx:sources/com/example/demo/MainActivity.java` / `x-dexatlas-source-tool-version: 1.5.2` | ✓ 源码 |
| 40 | `GET /projects/{pid}/report?format=json` | 200 | 10 个顶层字段（与第 16 步同一串） | ✓ 报告 |

> **第 32 步是本轮最值钱的一步**：修复后的材料 §3.8 里那整段「端口被占时的退路
> （这一处会静默失败，请照做）」——本机 8000 端口上**真的**跑着另一个 FastAPI
> 应用（`/health` 返回 `{"status":"healthy"}`）。**照修复后的材料走，读者会先
> 撞上这个坑，然后按材料说的换到 8011、先用 `/health` 确认服务身份，再往下做。**
> 这段修复**在这台机器上被实测复现并验证**了。

### 2.6 §3.8 F3 的 MCP 工具清单（验收项 F3）—— 上一轮最大的卡住点

| # | 命令 | 实际输出 | 耗时 | 对得上吗 |
|---|---|---|---:|---|
| 41 | 修复后 §3.8 的「列 11 个工具与四个只读注解」那条管道 | **11 行**，每行 `name\treadOnly=True\tdestructive=False\tidempotent=True\topenWorld=False`；末行 `tool count: 11`。工具名逐个为 `list_projects` / `get_project_status` / `get_manifest` / `search_symbols` / `get_class_source` / `get_method_source` / `find_callers` / `find_callees` / `get_evidence` / `resolve_locator` / `find_resource_declarations` | 3.2 s | ✓ **与契约表 §3.1 的 11 个逐名对上**；四个注解与契约表 §3 开头一致 |
| 42 | 修复后 §3.8 的「抽查 2 个工具的返回形状」那条管道 | `id=3 -> {"projects": [{"id": "apk_80a8fe0e81204c9f", …, "class_count": 5, "method_count": 8, …}], "total": 1, "offset": 0, …}`；`id=4 -> {"project": {…}, "completeness": {"complete": true, …}, "published_run": {…}}` | 3.3 s | ✓ 与 §3.1 的 `ProjectList{projects,total,offset,limit}` / `ProjectStatus{project,completeness,published_run?,runs[]}` 对上 |

> **这是上一轮 S-1 的正面答复**：上一轮预演者自己写了 20 行 MCP 客户端脚本才拿到
> 清单，而材料只给了「`uv run --no-sync dexatlas-mcp`」一行。**本轮照修复后的
> 两条命令原样跑，两条都直接出结果，读者不需要写任何代码** —— 与邀请函 §一
> 「您不需要写代码」一致。
>
> **两行的先后顺序**：本轮实测 `id=3` 在前、`id=4` 在后。材料说「顺序不固定，
> 按 `id=` 对号入座即可」——这句**与实测一致**（顺序由两个调用的并发完成次序
> 决定，本轮只见到一种顺序，但材料没有声称顺序固定）。

### 2.7 §3.4 / §3.6 的证据核查（C 组）

| # | 命令 | 实际输出 | 对得上吗 |
|---|---|---|---|
| 43 | 读 `report.json` 的 `evidence`（11 条） | 顶层字段是 `['detail','id','kind','level','provenance','summary']` —— **tool / tool_version / locator 不在顶层**，在 `provenance[]` 里（1 或 2 条） | ⚠ **见 §4 的 M-8** |
| 44 | MCP `get_evidence`（E-0004） | `{"id":"E-0004","kind":"cross_reference","level":"verified","summary":…,"detail":{…},"provenance":["androguard:classes.dex#…onCreate->…sign","androguard:classes.dex#…Crypto#…sign"]}` | ⚠ 同上：**MCP 侧的 `provenance` 是字符串数组，JSON 报告侧是对象数组** |
| 45 | MCP `resolve_locator` × 3 | `androguard:classes.dex#com.example.demo.Crypto` → `resolved=true, reason="com.example.demo.Crypto is in classes.dex"`；`androguard:AndroidManifest.xml` → `resolved=true, reason="AndroidManifest.xml is a dex file of this analysis"`；`jadx:sources` → `resolved=true, kind="java"`, `reason` 是工作区里的真实绝对路径 | ✓ C2 的三档都验到了 |
| 46 | B4 顺 locator 找文件 | `.dexatlas/projects/apk_80a8fe0e81204c9f/runs/<run>/jadx/sources/com/example/demo/{Crypto,MainActivity,NetworkClient,R,SyncService}.java` **确实存在** | ✓ |

### 2.8 §9.1 G 组故障恢复（验收项 G1–G5）

| # | 命令 | 退出码 | 实际输出 | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 47 | `DEXATLAS_WORKSPACE=./g1-fresh dexatlas analyze README.md` | **2** | `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives` | 0.9 s | ✓ |
| 48 | `DEXATLAS_WORKSPACE=./g1-fresh dexatlas projects` | 0 | `No projects yet. Run \`dexatlas analyze <apk>\`.` | 1.0 s | ✓ **空工作区里列表为空** |
| 49 | 主工作区 `dexatlas projects` | 0 | 1 条 `apk_80a8fe0e81204c9f`（5 classes / 8 methods） | 0.9 s | ✓ 与 §9.1 新增的那句一致 |
| 50 | `DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR= dexatlas analyze …` | **0** | `✓ apk_80a8fe0e81204c9f — 4 classes, 8 methods, 23 call sites, 21 call edges, 0 resource strings` + 两条 `!`：`apktool is not installed or not on PATH: …` / `jadx is not installed or not on PATH: …` | 1.7 s | ✓ G2；计数 4 classes / 0 resource strings 与材料一致 |
| 51 | 读降级那次的 `errors[]` / `tools` | — | `errors: [('apktool','not_installed'),('jadx','not_installed')]`；`tools: {"jadx":null,"apktool":null,"androguard":"4.1.4"}` | 0.2 s | ✓ |
| 52 | `DEXATLAS_TOOL_TIMEOUT_SECONDS=1 dexatlas analyze …` | **0** | 一条 `!  jadx exceeded its 1s timeout; its launcher had already exited`（**只有一条**） | 4.4 s | ✓ G3 的新判据「至少一条」 |
| 53 | 读超时那次的 `errors[]` / `index_*` | — | `errors: [{'tool':'jadx','code':'timeout',…}]`；`index_complete=True`；`index_gaps=[]`；`evidence_by_level: {'verified': 12}`（正常运行 11 条） | 0.2 s | ✓ 修复后 §9.1 的括注逐句对上 |
| 54 | `dexatlas analyze …` ×2 + `dexatlas projects` | 0 / 0 / 0 | 两次同一个 project id、同样计数；`projects` 只列 **1** 条 | 7.6 s | ✓ G4 |

### 2.9 §7 自查脚本（与 §五 对照）

| # | 命令 | 退出码 | 实际输出 | 耗时 | 对得上吗 |
|---|---|:---:|---|---:|---|
| 55 | `uv run python scripts/m10_selfcheck.py` | **0** | `自动化判定：通过 43，失败 0，需人工 40；已判定项通过率 100.0%` | 0.8 s | ✓ 43 / 40 与修复后邀请函 §五 一致 |
| 56 | 抽自查脚本「需人工」的编号 | — | `A1…G5` 共 40 个，**与 40 个验收项编号一一相同** | 0.2 s | ✓ 修复后 §五 的说法成立 |
| 57 | 抽自查脚本「通过」清单里带验收项编号的条目 | — | `F5 F6 F1 F3 F4 F4 F2 D3 D1 D5 E1 E5 A4 F6 A6` —— **13 项（A4、A6、D1、D3、D5、E1、E5、F1、F2、F3、F4、F5、F6）确实同时出现在两份清单里** | 0.2 s | ✓ 修复后 §五 说的「13 项」逐个对得上 |

---

## 3. 卡住（3 条）

### S-4 【**全部 11 条修复**】tag 指向的树上，一条修复都没有 —— 读者读到的是修复前的材料

**这是本轮最重要的发现，也是前两轮都没发现的一条。**

**材料怎么说**：修复记录 [m10-material-fixes.md](m10-material-fixes.md) 逐条处置了
上一轮的 9 处缺口 + 2 处「多余」，处置原则第 3 条写着「**命令必须真的能跑。
本轮给出的每一条命令都在上面那台机器上实跑过**」。§5「改完后还剩什么」的第 4 条
写着「tag 所指的那棵树上的材料仍是填 hash 之前的版本 | 不需要人做 | 形状不变是
作者的决定（tag 不重打）」——**这一条只提了「填 hash」这一件事**。

**实测**：修复的那一个提交是 `12141b5`，而 tag 指向的 `2715aef` 是它的**祖先**
（`git merge-base --is-ancestor 2715aef 12141b5` → 0，中间隔 **18** 个提交；
从 tag 到 HEAD 隔 **22** 个提交）。也就是说：

> **读者 `git checkout v1.0.0` 拿到的那棵树，是修复前的树。**
> **读者包 §3.8 的 F3 两条协议级命令、§9.1 的 G1 空工作区写法、§3.8 的端口退路、
> 准备包的 G3 唯一权威出处、邀请函 §五 的「就是同一组」、邀请函 §四 的 locator
> 判法 —— 全部都不在那棵树里。**

逐条实测（在 tag 树里 grep 同一组关键词）：

| 修复 | 关键词 | tag 树命中 | 修复后树命中 |
|---|---|:---:|:---:|
| S-1 F3 协议级命令 | `notifications/initialized` | **0** | 3 |
| S-2 hash 口径 | `随函发出的那一份` | **0**（四份材料全是 0） | 邀请函 0 / 读者包 1 / 准备包 3 / 模板 0 |
| S-3 端口退路 | `8011` | **0** | 5 |
| S-3 端口退路 | `Uvicorn running on` | **0** | 1 |
| M-1 G3 单点化 | `本项是 G3 判据的唯一权威出处` | **0** | 1 |
| M-1 G3 单点化 | `权威判据见` | **0** | 1 |
| M-3 G1 空工作区 | `g1-fresh` | **0** | 3 |
| M-4 邀函 §五 | `不是另一组东西` | **0** | 1 |
| M-5 六类端点 | `六类关键端点` | **0** | 1 |
| M-6 locator 判法 | `按构造解析` | **0** | 1 |

**并把上一轮那几条在 tag 树里原样复现了一遍**：

- **tag 树读者包 §3.8 的 F3 命令**（`v1.0.0^{commit}:docs/reports/m10-reader-package.md`
  的**第 314 行**）仍然只是
  `uv run --no-sync dexatlas-mcp  # 起 MCP server（列工具清单）`。本轮照它原样跑：
  **stdin 立刻 EOF，输出为空 —— 看不到工具清单**。上一轮的 S-1 **原样重现**。
- **tag 树读者包 §9.1 的 G1 命令**仍然只有 `uv run dexatlas analyze README.md`
  （**没有 `DEXATLAS_WORKSPACE`**，也没有「空工作区」那段提醒）。本轮照它原样跑：
  退出码 2 ✓，但**紧接着的 `dexatlas projects` 列着 1 条项目**——上一轮的
  M-3 / G1 冲突**原样重现**。
- **tag 树读者包 §9.1 的 G3 预期**仍然是「超时的后端**各记一条 `timeout`**」
  并列出三条 `!` 样例——本轮实测**只有一条**（只有 jadx 超时）。上一轮的
  M-1 / G3 矛盾**原样重现**。
- **tag 树邀请函 §五**仍然写着「那是**另一个分母**……与您要判的 40 项
  **不是同一组东西**」。上一轮的 M-4 **原样重现**。
- **tag 树邀请函 §四**没有「按构造解析」那句，locator 判法仍是旧的那套。
  上一轮的 M-6 **原样重现**。
- **tag 树读者包 §3.8** 的 F2 段没有端口退路（`8011` 命中 0）。上一轮的 S-3
  **原样重现**——本机 8000 端口**真的**被别的服务占着。

**为什么算卡住**：读者的路径是「clone → `git checkout v1.0.0` → **读树里的
材料** → 照着做」。修复后的那 11 条内容只在**树外**（`main` 分支 /
`12141b5` 及其后继），树内读到的是旧稿。读者手上唯一的「随函发出的那一份」
是**邀请函**（一封信），而**读者包、准备包、记录模板这三份读者必然去树里读的
文件**不在信里 —— 邀请函 §四 明确说「完整分步命令、每步预期输出与记录格式，
以[读者验收包 §3]为准」。

**这不是读者能靠「按邀请函 §2 的指引核 hash」绕过去的**：邀请函 §2 的口径是
「**这一串以随函发出的这一份为准**」（这一句本身在修复后的树里），它解决的是
**hash 那一串从哪儿取**，不是「读者包 §3.8 里的 F3 命令在哪一版」。读者核完
hash 会得到 `2715aef` —— 与随函那一串**逐字相同**（这一条是通的），但他读到的
**命令**仍然是旧版。

**给主会话的修法（三选一，按代价排序）**：

1. **重打 tag**（材料自己写好的那一步）：`git tag -f -a v1.0.0 <修复后的提交>
   -m "v1.0.0 — 材料定稿" && git push origin v1.0.0 --force`，然后**重新取
   hash 并重填**邀请函 §2、记录模板 §1，准备包 §3.1、读者包 §1.6/§3.1 的指针
   随之更新。**[就绪记录](m10-invitation-readiness.md) 第 2 步与
   [发送清单](m10-invitation-sender-checklist.md) 的 N1 写的就是这一步**
   —— 它只是**还没被执行**。代价：tag 已在 origin 上，移动它是公开可见的改动。
2. **接受现状并把话写进随函**：在随函发出的那一份里明说「树里的读者包是
   **修复前**的版本；F3 的两条协议级命令、G1 的空工作区写法、§3.8 的端口退路
   请以随函附件的这三份材料为准」，并把**三份材料作为附件发出**。代价：读者要
   在两套材料之间对照，容易再读错。
3. **什么都不做**：那这一轮预演的全部结论就是「11 条修复一条都没到读者眼前」，
   上一轮的 11 条缺口原样保留 —— **不建议**。

**附带的一条**：发送清单里那条「查 tag 指向的那棵树**含本轮全部材料修正**」
的检查（`git diff --name-only "v1.0.0^{commit}"..HEAD -- docs/reports/m10-*.md`）
**本轮实跑的结果是 11 个文件**，而清单里写的是「**只应列出「填 hash 这一步」
动过的文件**」（它举的例子是 4 个：邀请函 §2、记录模板 §1、发送清单、准备清单）。
**这条检查现在会以「不通过」告终**，而且它给出的正是正确的诊断——只是它被写成
「填 hash 这一步」而实际上多了 7 份材料。**清单的命令是对的，判语需要跟着
这一轮的事实改。**

> **注意这不影响「随函发出的那一份」自身的正确性**：本轮 §2 的全部 57 步都是照
> **修复后**的材料跑的，它们**全部与材料对得上**（材料路径上只有两处不符，见 §4 的
> M-7 / M-8；§3 的 S-5 与 S-6 是材料没给命令、门禁要重核，不在命令路径上）。
> **修复的内容是对的，只是它没进 tag。**

### S-5 【验收项 C2 ★】locator 解析没有可照抄的命令，判据却要求「在分析工作区内解析到真实文件」

**材料怎么说**：准备包 C2（★ 阻断项）的判据是「locator 解析：文件级 locator
在分析工作区内解析到真实文件；DEX 成员 locator 与裸树 locator（如
`jadx:sources`）按构造解析（`path=None` 是设计，不是失败）；无法解析的 locator
要单独列出」。邀请函 §四 第 4 步（修复后）也把 locator 判法指向 C2。

**实测**：C2 要的是**解析结果**，但**三份材料里没有任何一条解析 locator 的
命令**。可用的只有 MCP 的 `resolve_locator` 工具 —— 它在契约表 §3.1 的 11 个
工具里，但**读者包 §3.8 的 F3 命令只抽查了 `list_projects` 与
`get_project_status` 两个**，没有覆盖它；而 REST 侧**根本没有 locator 解析
端点**（契约表 §2 的路由表里没有；`/projects/{pid}/evidence` 只是列出证据记录）。

本轮自己写了管道去调 `resolve_locator`（第 45 步），三档都验到了：

```text
androguard:classes.dex#com.example.demo.Crypto → resolved=true, reason="com.example.demo.Crypto is in classes.dex"
androguard:AndroidManifest.xml                 → resolved=true, reason="AndroidManifest.xml is a dex file of this analysis"
jadx:sources                                    → resolved=true, kind="java", reason=<工作区里的真实绝对路径>
```

**为什么算卡住**：C2 是 **★ 阻断项**，判据要求读者给出「解析结果」这一栏
（证据记录栏写的是「locator：；解析结果：」）。**照材料走，读者只能自己写
MCP 客户端**——那正是上一轮 S-1（F3）被记为卡住的**同一种情形**：材料要求一个
需要写代码才能得到的结论，却没有给命令。

**给主会话的修法**：在读者包 §3.8 的 F3 段之后（或 C2 的说明里）补**一条**可照抄
的 `resolve_locator` 命令（同 §3.8 F3-b 那条管道的写法，把 `tools/call` 的
`name` 换成 `resolve_locator`、`arguments` 换成
`{"project_id":"…","locator":"…"}`），并把契约表 §2 那张路由表里「REST 没有
locator 解析端点」这件事写明（读者不必去找）。

### S-6 【重打 tag 这一步本身】新 tag 树会让 release body 的 64 条引用漂移

**背景**：`scripts/check-doc-citations.py` 把 **release body** 的引用绑在
**`v1.0.0` 那棵树上**，行号是 `git show v1.0.0:<file>` 读出来的。**tag 一换，
那棵树就换了，引用要重核。**

**实测**：用一个临时 tag 指向 HEAD 跑一遍（跑完已删除该 tag、脚本已还原、
工作区已确认干净），得到 **drifted: 2**：

1. **指纹声明**：release body 写「release tree: source fingerprint
   `sha256:18f3ab15…`, suite 1710 passed / 0 failed」（`:175`、`:290`、`:304`）
   —— 那是**旧 tag 树**的指纹与测试数；新树里是 `sha256:beddd7c9…` / `1733`；
2. **一条引用指空**：`docs/reports/phase1-execution-report.md:879` 在旧树里是
   「1694 passed + 0 xfailed + 1 skipped」那一行，新树里那一行挪了位。

**为什么算卡住**：这一条**卡住的不是读者，是发版那一步** —— 主会话已经决定
重打 tag，若「同步对外文本」发生在「重测」之前，tag 一打，门禁立刻红。
**release body 里的指纹与测试数本身就是重测的产物**，所以同步必须排在重测之后。

**完整的分析与建议顺序见 §8.1。**

---

## 4. 误读（3 条）

### M-7 【验收项 F2】`/projects/{pid}/runs` 的 `total` 是 2，材料给的是 1

**材料怎么说**：修复后读者包 §3.8 的「运行（§2.3）」那条命令下面写着实测输出：

```text
# 200
# {"project_id":"apk_80a8fe0e81204c9f","total":1,"published_run_id":"run_…","runs":[{…,"status":"completed","completeness":"complete",…}]}
```

**实测**：`total` 是 **2**，`runs` 里有两条（`run_b6ccbae53ef24111` 与
`run_072c3be7a5e2400d`），两条都是 `completed`。

**为什么是 2**：读者按 §3 的顺序走，到 §3.8 之前已经分析过**三次**同一个 APK
（§3.3 一次、§3.5 三格式报告一次、§3.8 的上传端点自己还会再触发一次），
每一次都**更新同一个项目**（G4 的幂等），但**每次留下一个 run 记录**。所以
`total` 记的是**历史运行次数**，不是项目数。

**为什么算误读**：材料把 `total:1` 写成「**实测输出**」的一部分，读者会把它
当成**形状预期**（`total` 应该是 1）来核对。实测值与材料给的字面输出不一样，
而**判据本身**（契约表 §2.3 那一行的响应形状）并没有规定 `total` 该是几 ——
**判据是行为（形状对、状态码对），不是数字**。这一点材料在别处（§9.1 的
「**判据是行为，不是数字**」）说得很清楚，**但 §3.8 这段把具体数字写成了
「实测输出」，读者会直接拿去比**。

**给主会话的修法**：把那一行的 `"total":1` 改成 `"total":N`（或直接写
`"total":<历史运行次数>`），并在旁边加一句「`total` 是该项目的**历史运行次数**，
§3.3–§3.8 每分析一次就 +1；判据是形状与状态码，不是这个数」。**代价一行。**

### M-8 【验收项 C1 ★ / C3 ★】evidence 的「工具、版本、locator」三个字段不在 JSON 的顶层，材料没说它们在哪

**材料怎么说**：邀请函 §四 第 4 步（修复后）：

> 任选 3 条 evidence 记录核对工具、版本、locator、level 四字段：
> - `tool` 与 `version` 抄这条 evidence 记录自己写的值，不用另行查证；

准备包 C1（★）：

> 任选 3 条 evidence 记录，逐条写出工具、版本、locator 和 level；**字段不得为空
> 或臆造。**

读者包 §3.4（修复后）：

> 打开 JSON 报告或证据包，任选 3 条 evidence 记录，逐条核对工具、版本、locator、
> level 四个字段

**实测**：JSON 报告里一条 evidence 记录的顶层键是
`['detail','id','kind','level','provenance','summary']` —— **`tool`、`tool_version`、
`locator` 三个字段在顶层都取不到**（读到 `None`）。它们在 **`provenance[]`
数组**里，每个元素是 `{tool, tool_version, apk_sha256, locator}`：

```text
E-0001  provenance n=1  [('androguard','4.1.4','androguard:AndroidManifest.xml')]
E-0004  provenance n=2  [('androguard','4.1.4','androguard:classes.dex#…onCreate->…sign'),
                         ('androguard','4.1.4','androguard:classes.dex#…Crypto#…sign')]
```

**而且两个传输的形状不一样**：MCP 的 `get_evidence` 返回的 `provenance` 是
**字符串数组**（只有 locator，没有 tool / version）：

```text
"provenance": ["androguard:classes.dex#…onCreate->…sign",
               "androguard:classes.dex#…Crypto#…sign"]
```

**为什么算误读**：C1 是 **★ 阻断项**，判据写着「**字段不得为空**」。一个读者
照「逐条写出工具、版本、locator 和 level」去做，打开 JSON 报告先看到三个
`None` —— **极可能记成「C1 不通过：字段为空」**，或写下一堆臆造的字段值。
而实际上字段是有的，只是在 `provenance[]` 里、且**一条记录可能有 2 条**
（E-0004–E-0006 都是 2 条），材料对此**一个字都没说**。

三份材料里只有**契约表 §3.1** 提过 `provenance[]` 这个词（`get_evidence` 的
返回形状 `EvidenceView{id,kind,level,summary,detail,provenance[]}`），
但那是 MCP 契约、且没说 `provenance` 里装的是什么；**JSON 报告侧的
`evidence[]` 形状（`src/dexatlas/core/models.py` 的 `Evidence`）在契约表
§5.1 里只写了 `evidence` \| `Evidence[]` 一行，没有展开**。

**给主会话的修法**：在准备包 C1 的判据或读者包 §3.4 里加一句（**两句即可**）：
「工具 / 版本 / locator 在 `provenance[]` 里（JSON 报告侧是对象数组，元素含
`tool` / `tool_version` / `apk_sha256` / `locator`；MCP 侧 `get_evidence` 返回的是
locator 字符串数组）；**一条记录可能有不止一条 provenance**，逐条列出即可」。
再在契约表 §5.1 的 `evidence` 那一行把 `Evidence` 的六个键写全。

### M-9 【验收项 C2 ★】「`path=None` 是设计，不是失败」——判据用的词与 API 实际返回的字段对不上

**材料怎么说**：准备包 C2 与修复后邀请函 §四 都说：DEX 成员 locator 与裸树
locator（如 `jadx:sources`）是**按构造解析**的，**`path=None` 是设计，不是失败**。

**实测**：`resolve_locator` 的返回里**根本没有 `path` 这个键**。本轮实测到的
三个返回，键是 `resolved` / `reason` / `kind` / `text` / `provenance`：

```text
androguard:classes.dex#…Crypto → {"resolved": true, "reason": "com.example.demo.Crypto is in classes.dex", "kind": null, "text": {…}, "provenance": ["androguard:classes.dex#…"]}
jadx:sources                    → {"resolved": true, "reason": "E:\\…\\.dexatlas\\projects\\…\\jadx\\sources", "kind": "java", "text": {…}, "provenance": ["jadx:sources"]}
```

`path=None` 是**内部 Python API**（`LocatorResolver.resolve(...)`）的说法 ——
它出现在 [M8 演练](m8-install-rehearsal.md:48) 的实测表里（`path=None`，那一行写的是
「`LocatorResolver.resolve(...)`（Python API）」），那里说的
确实是 Python API。

**为什么算误读**：C2 是 **★ 阻断项**，判据里点名了一个**在读者能调用的任何
接口上都不存在的字段**。读者读到「`path=None`」，然后在 `resolve_locator` 的
返回里找 `path` —— **找不到**，会去源码里找、或者以为解析失败了。**「
`resolved=true`」这个真正的判据（材料其实也写了「按构造解析」）反而被这句
`path=None` 盖住了。**

**给主会话的修法**：把 C2 与邀请函 §四 那句改成 **「`resolved=true` 但没有可读的
文件内容，是按构造解析，不是失败」**（用 API 里真实存在的字段说话），并在
括号里保留一句「内部 Python API 里那个字段叫 `path`」——**一句话的改动，
但它在一颗 ★ 上**。

---

## 5. 多余（1 条）

### X-3 【发送前清单】那条「tag 树含本轮全部材料修正」的检查，判语已经与事实不符

**材料怎么说**：[发送前清单](m10-invitation-sender-checklist.md:146) 那条勾选项写着：

> **查过是什么样：** 第一条**只应列出「填 hash 这一步」动过的文件**——邀请函 §2、
> 验收记录模板 §1 的 commit hash 栏，以及随之改判据的发送清单与准备清单；
> **M10 材料在 tag 指向的树里与你手上的其余部分仍是同一份，读者读到的是定稿**。
> ……第三条告诉你 tag 落后几个提交（**填完 hash 后是 1**）。

**实测**（照它自己给的命令跑）：

```text
$ git diff --name-only "v1.0.0^{commit}"..HEAD -- docs/reports/m10-*.md
docs/reports/m10-acceptance-pack.md
docs/reports/m10-invitation-final.md
docs/reports/m10-invitation-readiness.md
docs/reports/m10-invitation-sender-checklist.md
docs/reports/m10-material-fixes.md
docs/reports/m10-materials-alignment.md
docs/reports/m10-reader-kit.md
docs/reports/m10-reader-package.md
docs/reports/m10-reader-rehearsal-2nd.md
docs/reports/m10-reader-walkthrough-4th.md
docs/reports/m10-review-record-template.md

$ git diff --name-only "v1.0.0^{commit}"..HEAD -- src/ tests/
tests/test_docker_image_samples.py
tests/test_figures_auto_write.py
tests/test_release_numbers.py

$ git log --oneline "v1.0.0^{commit}"..HEAD | wc -l
22
```

**三处与清单的判语对不上**：

1. **文件数是 11，不是 4** —— 「只应列出填 hash 这一步动过的文件」这条判语已经不成立；
2. **「tag 落后几个提交（填完 hash 后是 1）」现在是 22**；
3. **「`src/` 与 `tests/` 期望为空」这一条现在不空** —— 多了三个 `tests/` 文件。
   （这三个测试文件是 v1.0.0 **之后**新增的，与材料修正无关；清单那条检查的
   **本意**是「材料修正不该动 `src/` 与 `tests/`」，而它写成了对整个
   `tag..HEAD` 区间的检查 —— **检查的范围比它的本意宽**。）

**为什么算多余**：**同一件事（tag 与材料定稿的关系）在这套材料里被说了三遍，
三遍不一致**：

- **发送清单**说「tag 落后 1 个提交，读者读到的是定稿」；
- **[就绪记录](m10-invitation-readiness.md) 第 2 步**说「重打 tag → 读者
  `git checkout v1.0.0` 拿到的是**定稿材料**，不是旧稿」——**这一句是对的**，
  而且它把「重打 tag」列为发信前的第 2 步；
- **实际状态**是 tag **没有**被重打，仍停在 `2715aef`（材料定稿**之前**）。

**读者该信哪一句？** 三句里两句说「读者读到的是定稿」，一句（就绪记录第 2 步）
说的是一个**待执行的动作**。而事实是**两件事都没发生**：tag 没重打，
所以「读者读到的是定稿」也不成立。**在发信之前**，这三处必须收敛成一处
**当前事实**（要么把 tag 重打，要么把随函写成「树内是旧稿」）。

**给主会话的修法**：把发送清单那一处的判语从「填完 hash 后是 1」改成
「**发信前必须让 tag 指向材料定稿的提交**（[就绪记录](m10-invitation-readiness.md)
第 2 步）；本仓库当前的 tag 落后 **22** 个提交，材料修正涉及 **11** 份
`docs/reports/m10-*.md`」；`src/`/`tests/` 那条检查改成**只看材料修正那个提交**
（`git diff --name-only <tag>..12141b5 -- src/ tests/` 为空），而不是整个区间。

---

## 6. 上一轮 11 条的逐条去向

> 口径：**堵住了** = 读者照材料能拿到结论；**还差什么** = 修复内容本身有欠缺；
> **新的误读** = 修好之后新出现、或因修复才暴露出来的读法问题。
> **「在修复后的树里」**一列说的是**修复内容本身**是否成立；**「在 tag 树里」**
> 一列说的是**读者实际读到的那一份**是否含这条修复。

| 上一轮的 | 内容 | 在修复后的树里 | 在 tag 树里 | 本轮去向 |
|---|---|---|---|---|
| **S-1** | F3 的 MCP 工具清单命令改成协议级 | ✓ **堵住** —— 两条命令原样跑，11 行 + `tool count: 11`，注解四值齐全，抽查 2 个工具两行输出（§2.6） | ✗ **没有**（`notifications/initialized` 命中 0）；照 tag 树的旧命令跑，**stdin EOF、输出为空**，上一轮的卡住**原样重现** | **修复有效，但没进 tag** → 归入 **S-4** |
| **S-2** | hash 的形状按「以随函发出的那一份为准」写清 | ✓ **堵住** —— 邀请函 §2、记录模板 §1、读者包 §1.6/§3.1、准备包 §0/§3.1 四处口径一致；本轮 `git rev-parse v1.0.0^{commit}` 的输出与随函那一串**逐字相同**（§2.1 第 3 步） | ✗ **没有**（四份材料里 `随函发出的那一份` 命中 0）；tag 树的邀请函 §2 仍是「**【待填：v1.0.0 发版 commit 的完整 hash】**」 | **修复有效，但没进 tag** → 归入 **S-4**。**这一条是 S-4 的一个注脚**：它恰好说明了「随函发出的那一份」与「树内那一份」的差别 —— 但读者要读的**命令**在树里 |
| **S-3** | REST 端口被占有退路且失败看得见 | ✓ **堵住** —— 本机 8000 **真的**被另一个 FastAPI 占着（`/health` 返回 `{"status":"healthy"}`），照修复后的材料换到 8011、先用 `/health` 确认身份，全程没有假卡点（§2.5 第 32–34 步） | ✗ **没有**（`8011` 命中 0）；tag 树里没有退路也没有身份核对 | **修复有效，但没进 tag** → 归入 **S-4** |
| **M-1** | G3 的预期单点化 | ✓ **堵住** —— 准备包 §2.7 G3 写着「**本项是 G3 判据的唯一权威出处**」，读者包 §9.1 改成「至少一条后端记 `timeout`」并指向它（§2.8 第 52–53 步实测**只有一条**） | ✗ **没有**；tag 树的 §9.1 仍是「各记一条」+ 三条样例，与本机实测的**一条**矛盾 —— 上一轮的假卡点**原样重现** | **修复有效，但没进 tag** → 归入 **S-4** |
| **M-2** | M8-4 的判据改指新契约 | ✓ **基本堵住** —— 准备包 G3 已写「**M8-4 是提出该缺口的历史记录，已由退出码 6 关闭**」；本轮 `verify-public-contracts.py` 实测打出 `PASS an analysis with no index exits 6`，`check-contract-records.py --expect with-jadx` 退出码 0（§2.4 第 30–31 步） | ⚠ **部分** —— tag 树的准备包 G3 已有「由 `verify-public-contracts.py` 的 `an analysis with no index exits 6` 一条覆盖」，但仍写着「本项只需核对 **M8-4 的退出码语义**」 | **判据已指新契约（tag 树里也已指），只是措辞未同步**。**M8-4 那个「当时（修复前）的实况」注记不在 tag 树里**，但注记在 `m8-install-rehearsal.md`，那份文件不在 M10 材料的 diff 里 → 影响小 |
| **M-3** | G1 的空工作区预期与执行顺序对齐 | ✓ **堵住** —— §9.1 的 G1 现在明写「这条要在**一个空工作区**里跑」，两条命令都带 `DEXATLAS_WORKSPACE=./g1-fresh`，并补了「主工作区里 `projects` 列着 A4 的项目是正常的」（§2.8 第 47–49 步三段全对） | ✗ **没有**（`g1-fresh` 命中 0）；照 tag 树跑，`projects` 列着 1 条 —— 上一轮的假卡点**原样重现** | **修复有效，但没进 tag** → 归入 **S-4** |
| **M-4** | 邀函 §五 那句「不是同一组东西」改掉 | ✓ **堵住** —— 改成「**那 40 项就是您要判的这 40 项**……编号 A1–G5 与本函第五节那份清单**一一对应**，不是另一组东西」；本轮实跑自查脚本，「需人工」的 40 个编号**就是** A1–G5（§2.9 第 55–57 步） | ✗ **没有**；tag 树的 §五 仍写着「那是**另一个分母**……**不是同一组东西**」 | **修复有效，但没进 tag** → 归入 **S-4** |
| **M-5** | F2 按「补齐六类端点的命令」处置 | ✓ **堵住** —— 六类端点（上传 / 项目 / 运行 / 符号 / 源码 / 报告）各一条可照抄命令，**本轮六条全跑**，状态码 202 / 200×5，响应形状与契约表 §2 对上（§2.5 第 35–40 步） | ✗ **没有**；tag 树 §3.8 只有 4 条命令、且没有状态码（`-w` 参数） | **修复有效，但没进 tag** → 归入 **S-4**。**但修复后的版本本身有一处新问题** → 归入 **M-7**（`total:1`） |
| **M-6** | 邀函 §四 的 locator 判法与准备包对齐 | ✓ **基本堵住** —— 邀请函 §四 现在明写「**文件级** locator 要在分析工作区里解析到真实文件；**DEX 成员 locator 与裸树 locator**（如 `jadx:sources`）是**按构造解析**的」 | ✗ **没有**（`按构造解析` 命中 0） | **判据口径已对齐**（归入 S-4）。**但对齐之后暴露了两个新问题**：C2 没有可照抄的**命令**（→ **S-5**），以及 `path=None` 这个词在 API 里**不存在**（→ **M-9**） |
| **X-1** | G3 的预期三处各写一遍 | ✓ **堵住** —— 准备包 G3 自称唯一权威出处，读者包 §9.1 指向它且只给**示例**（明说「条数随后端速度变化」），M8 演练 §5 由**另一个窗口**（`d593470`）另修 | ⚠ **tag 树里三处仍在** | 与 M-1 同一批 → 归入 **S-4** |
| **X-2** | 邀请函 §三 与读者包 §2 各有一份「你需要准备什么」表；两份「读者路径」的步骤清单不一致 | ⚠ **部分堵住** —— 准备包 §3 现在补了「**两者若有出入，以读者包为准**」与夹具步骤（`fetch-fixtures.sh`）那一段；读者包 §2 那张表**更全**（多了时间档位的口径说明与「做快于 30 秒不是卡点」）；但**三张表仍然都在**（邀请函 §3 / 读者包 §2 / 准备包 §3.1），**读者路径的步骤清单仍是两份** | ✗ **没有**（`以读者包为准` 命中 0；准备包 §3.1 在 tag 树里也没有夹具步骤） | **三张表仍在**（这是**多份材料各管一段**的常态，不算错，但读者仍要自己判断以哪份为准）。**本轮不算误读**——三张表的内容**互相不矛盾**，只是详略不同。**记为「未完全收敛，但不构成误读」** |

### 汇总

**两个维度是独立的**：「修复内容本身成不成立」与「读者读到的那一版有没有它」
是两件事，因此分成两张表。

**维度一：修复内容本身（这一轮实跑验证的）**

| 类别 | 条数 | 编号 |
|---|:---:|---|
| **堵住** | **8** | S-1、S-2、S-3、M-1、M-3、M-4、M-5、X-1 |
| **基本堵住**（判据已改对，措辞/命令有欠缺） | **2** | M-2、M-6 |
| **部分堵住**（收敛了一半，仍有多处/多份） | **1** | X-2 |

**维度二：读者读到的那一版（tag 树 `2715aef`）有没有这条修复**

| 类别 | 条数 | 编号 |
|---|:---:|---|
| **不在 tag 树里**（读者读到旧稿） | **10** | S-1、S-2、S-3、M-1、M-3、M-4、M-5、M-6、X-1（+ X-2 同批） |
| **部分在**（判据已指对，措辞未同步） | **1** | M-2 |

**一句话**：**11 条修复的内容，一条不假，全部有效；但 10 条对读者不可见 ——
读者 `git checkout v1.0.0` 读到的是修复前的树。**

> **另外三条新问题（S-5、M-8、M-9）跟 tag 无关** —— **tag 重打了它们也还在**，
> 因为它们出在判据与 API 的对不上，不在材料版本上。

---

## 7. 40 个验收项的三类归属

> 口径照前两轮：**能自己判** = 读者照材料能给出「通过 / 不通过 / 未验证」；
> **必须问作者** = 判据或材料有缺口，读者只能靠问；
> **没判据** = 判据本身不足以判定。
> 上一轮：能自己判 **39**、必须问作者 **1**（F3）、没判据 **0**。

| 分类 | 项数 | 编号 |
|---|:---:|---|
| **能自己判** | **35** | A1、A2、A3、A4、A5、A6、A7、B1、B2、B3、B4、B5、B6、C3、C4、C5、C6、D1、D2、D3、D4、D5、E1、E2、E3、E4、E5、F1、F4、F5、F6、G1、G2、G3、G4 |
| **必须问作者** | **4** | **F3**（★F3 的命令只在修复后的树里；tag 树里**没有** → 读者只能问）、**C2**（★ 判据要求解析 locator，**材料没给命令** → **S-5**）、**F2**（★ 六类端点命令同样只在修复后的树里 → 同 F3）、**C1**（★ 四字段的位置（`provenance[]`）与两传输的形状差异没写 → **M-8**） |
| **没判据** | **1** | **G5**（★「证据包不含 APK、全量源码、未引用字符串」——「未引用字符串」在包里**无法直接判定**：包内只有 manifest + 3 份报告，没有全量字符串集可比对；读者只能核对 `not_included` 声明与 APK 本身。**判据能核的是「不含 APK」与「不含全量源码」两项**） |

> **与上一轮的对照**：上一轮是 39 / 1 / 0（只有 F3 要问作者）。本轮把
> **C1、C2、F2 从「能自己判」挪进「必须问作者」，把 G5 从「能自己判」挪进
> 「没判据」**（三条的理由见下）。**上一轮那 39 项里有 4 项本轮不再算数** ——
> 上一轮的预演者**读了源码**才把 `provenance[]`、`path=None` 的来历与
> REST 端点的覆盖面搞清楚，**材料本身并没有给到读者**。
>
> **F3 是唯一一条「上一轮也要问作者、本轮在材料里已解决、但读者仍拿不到」的项**
> —— 因为命令只在 tag 树之外。

### 与前两轮的差别

| | 第一轮 | 第二轮 | **第三轮** |
|---|---|---|---|
| 能自己判 | 33 | **39** | **35** |
| 必须问作者 | 5 | **1**（F3） | **4**（F3、C2、F2、C1） |
| 没判据 | 2 | **0** | **1**（G5） |
| 走过的步数 | 41 | 59 | **57** |

**为什么「能自己判」反而从 39 掉到 35** —— 这是本轮与前两轮最重要的差别，
值得说清楚：

1. **F3 从「能自己判」退回「必须问作者」**：上一轮 F3 之所以能自己判，是因为
   **上一轮的预演者自己写了 MCP 客户端脚本**（报告里写了这件事），
   **材料本身并没有给命令**。本轮的材料**给了**命令 —— 但**只在 tag 树之外**。
   **一个真读者 checkout `v1.0.0` 拿到的仍是旧稿**，于是 F3 又回到「必须问
   作者」。**这一条不是修复失败，是修复没送到。**
2. **C1、C2 从「能自己判」退回「必须问作者」**：这两项在上一轮被判为「能自己判」，
   但上一轮预演者**读了源码**才把 `provenance[]` 与 `path=None` 的来历搞清楚。
   **C1 的判据（「逐条写出工具、版本、locator 和 level」）照字面做会读到三个
   `None`**（M-8）；**C2 的判据（「在分析工作区内解析到真实文件」）照材料做
   没有任何命令可用**（S-5）。**这两条是本轮新发现的**，与 tag 无关 ——
   **即使 tag 重打了，这两条也仍然要问作者。**
3. **F2 从「受 M-5 影响」回到「必须问作者」**：上一轮 F2 因 M-5（六类端点只给了
   两条命令）而受影响；修复后六类端点齐了（本轮六条全跑、状态码全对），
   **但在 tag 树里那份仍是旧的**。
4. **G5 新出现「没判据」**：上一轮判 G5「能自己判」，本轮发现「未引用字符串」
   这一半**在包里没有可比对的基准** —— 包内只有 manifest + 3 份报告，
   **没有全量字符串集**，读者无从判断「未被引用的字符串」是不是真的没被打进去。
   前两轮都没盯这一条。**这一条与 tag 无关，tag 重打了它也还在。**

**净效果**：**5 条修复让材料本身变好了（那 7 条「堵住了」），但 tag 让读者读不到；
另外 4 条是本轮实跑新发现的、与 tag 无关的判据/材料缺口。** 上一轮的 11 条
缺口里，**真正被读者消除的是 0 条**。

---

## 8. 什么没验、什么留给了谁

### 本窗口**没有**验的

- **Docker 路线（读者包 §3.2 路线 B）**：本轮跳过（机器上无本地 dexatlas 镜像，
  构建需 15–20 分钟）。**上一轮也跳过。**
- **`scripts/fetch-fixtures.sh`**：本轮**没有**跑它（网络受限），而是**从主检出
  复制**了两个 fixture（`TestActivity.apk` 174 896 B、`multidex.apk` 1 233 B，
  sha256 与主检出逐字相同）。**这不影响本轮结论** —— 本轮没有跑测试套件的
  集成部分，只跑了 `tests/test_public_contracts.py`（31 passed）。
- **完整测试套件**：没跑（本轮不判任何需要套件全绿的项）。
- **GitHub 上已发布的 Release 正文**：本轮**没有**取（任务允许，但本轮的
  结论全部来自本地树与本地实跑，不需要它）。
- **`src/` 与 `tests/` 的代码审查**：本轮只读不改。

### 留主会话的（本窗口**没有改任何既有文件**）

| # | 事项 | 类型 | 影响 | 代价 |
|---|---|---|---|---|
| 0 | **S-6** —— **重打 tag 之前**先处理「release body 的引用与新 tag 树对不上」这一条（详见 §8.1） | 卡住 | **重打 tag 这一步本身** | 见 §8.1 |
| 1 | **S-4** —— 重打 tag 到材料定稿的提交（[就绪记录](m10-invitation-readiness.md) 第 2 步 / 发送清单 N1），或改口径说「树内是旧稿」并把三份材料随函发出 | 卡住 | **F2、F3（★）、C1、C2（★）、G1、G3（★）… 全部修复项** | 1 条命令 + 重填 hash（**但 tag 是公开可见的改动**） |
| 2 | **S-5** —— 给 C2（★）补一条可照抄的 `resolve_locator` 命令 | 卡住 | C2（★） | 1 段管道 |
| 3 | **M-8** —— 在 C1 判据或读者包 §3.4 里点明工具/版本/locator 在 `provenance[]` 里、且一条记录可能有多条；并在契约表 §5.1 展开 `Evidence` 的键 | 误读 | C1（★）、C3（★） | 2–3 句 |
| 4 | **M-9** —— 把 C2 与邀函 §四 的 `path=None` 改成 API 里真实存在的 `resolved=true` | 误读 | C2（★） | 1 句 |
| 5 | **M-7** —— §3.8 那一行的 `"total":1` 改成 N，并说明它是历史运行次数 | 误读 | F2 | 1 行 |
| 6 | **X-3** —— 发送清单那条「tag 含本轮全部材料修正」的判语改成当前事实；`src/`/`tests/` 那条检查只看材料修正那个提交 | 多余 | 发信前的把关 | 1 段 |
| 7 | **G5 的「未引用字符串」** —— 要么在判据里删掉这一半（改成「不含 APK 与全量源码」+ `not_included` 声明核对），要么在准备包里给出比对方法 | 没判据 | G5（★） | 1 句 |
| 8 | **登记** —— 本文件进 `docs/reports/README.md` 与 `scripts/check-doc-citations.py` 的文档清单 | 登记 | 本文件自身的 `file:line` 才进检查器覆盖 | 主会话统一做 |

### 8.1 【S-6】重打 tag 会让 `check-doc-citations.py` 立刻红 —— 这是重打那一步的前置条件

**背景**：`scripts/check-doc-citations.py` 的 `TREE_DOCUMENTS` 表把 **release body**
的引用绑在 **`v1.0.0` 这棵树上**
（`"docs/reports/v1.0.0-github-release-body.md": "v1.0.0"`）：那 64 条引用的行号
是**按 tag 树读的**（`git show v1.0.0:<file>`），不是按工作区读的。
**tag 一换，那棵树就换了，引用要重核。**

**本轮实测**（用一个临时 tag `v1.0.0-sim` 指向 HEAD 跑出来的；**跑完已删除
该 tag、脚本已还原、工作区已确认干净**）：

```text
the v1.0.0-sim tree: 1 document(s), 64 citation(s)
drifted: 2
  v1.0.0-github-release-body.md  declaration  wrong tree:
    the document quotes sha256:18f3ab15 but the v1.0.0-sim tree's fingerprint is
    sha256:beddd7c924b51d8667afea5911fc967a572f1529c4f6696330782f98d4f42d3e
  v1.0.0-github-release-body.md:299  docs/reports/phase1-execution-report.md:879-879
    points at nothing: the range holds nothing
    |  | 1694 passed + 0 xfailed + 1 skipped | `docs/reports/phase1-execution-report.md:879` |
```

**两条各是什么**：

| # | 漂移 | 原因 | 怎么解 |
|---|---|---|---|
| a | **指纹声明** | release body 声明「release tree: source fingerprint `sha256:18f3ab15…`, suite 1710 passed / 0 failed」（`:175`、`:290`、`:304`）—— 那是**旧 tag 树**的指纹与测试数；新 tag 树（HEAD）的报告里是 `sha256:beddd7c9…` / `1733` 个测试 | **重测之后**（指纹与测试数都会变），release body 的这几处要跟着改成新树的指纹与测试数 |
| b | **一条引用指空** | `docs/reports/phase1-execution-report.md:879` 在旧 tag 树里是「1694 passed + 0 xfailed + 1 skipped」那一行；新树里那一行挪了位，879 落在别处 | 手工重锚这一行（`scripts/remap-citations.py` 对「指向位置而非符号」的引用**按规则不动**，要人来锚） |

**为什么这一条值得单列**：主会话已经决定重打 tag，顺序里也有「同步对外文本」
与「重发 Release 正文」。**但「同步对外文本」必须发生在「重测」之后** ——
release body 里写的**指纹与测试数本身就是重测的产物**。若在重测**前**同步，
tag 一打，检查器立刻红；而红的原因（指纹与测试数）恰恰要等重测才有新值。

**建议的顺序（只动这一段的次序，其余不变）**：

```text
合并 → 登记新报告 → 完整重测（指纹与测试数更新）→ 用新值同步 release body
     → 重锚 release body 里那条指空的引用 → 重打 tag → 更新邀请函 §2 的 hash
     → 重发 Release 正文 → 验 tag 的 CI
```

**验它绿了的命令**：

```bash
uv run --no-sync python scripts/check-doc-citations.py   # 期望 drifted: 0
```

> **本轮没有替主会话做这一步** —— 改 release body、跑重测、重打 tag 都是发版
> 动作，且 tag 是公开可见的改动；本窗口是只读预演。

### 本窗口**做的**

- 只读预演：克隆到 `.scratch/reader-rehearsal-3rd/dexatlas`、`git checkout v1.0.0`、
  照材料跑了 **57 步**（§2），另跑了 tag 树与修复后树的**逐条对照**（§3 S-4、
  §6）；
- **一次模拟验证**（§3 S-6 / §8.1）：用一个**临时 tag** `v1.0.0-sim` 指向 HEAD，
  跑 `scripts/check-doc-citations.py` 看重打 tag 后会发生什么，**得到 drifted: 2**；
  **跑完已删除该 tag、已还原脚本、已确认工作区干净**（`git status --porcelain`
  除本文件外无输出，`git rev-parse "v1.0.0^{commit}"` 仍是 `2715aef…`）；
- 新增**一份**文件：`docs/reports/m10-reader-rehearsal-3rd.md`（本文件）；
- 门禁：`ruff check` / `ruff format --check` / `mypy` / `vulture` /
  `check-doc-citations.py`（drifted: 0）/ `check-version-claims.py --base auto`；
- **没有**跑 `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率）；
- **没有**改任何既有文件 —— `docs/reports/m10-*.md` 里除本文件外的一切、
  `docs/reports/README.md`、`scripts/`、`tests/` **一字未动**
  （模拟时临时改过 `scripts/check-doc-citations.py` 的映射表，**已还原并核对**）；
- 改动提交到**本窗口的分支** `claude/sleepy-mendeleev-530a1b`，**未推 main、
  未合并**。

---

## 9. 复验这一轮的方法（给下一轮）

下一轮预演要验的**不是**「材料说了什么」，而是「读者照着做会得到什么」。本轮
的三条经验值得留下：

1. **凡是写「实测输出」的地方，都要把那个数当形状预期来核** —— 本轮的 M-7
   就是材料里一个「实测」的数字（`total:1`）在另一条顺序下变成了 2。
2. **凡是判据里点名了一个字段/词，就去读者能调用的接口上找那个字段** ——
   本轮的 M-8（`tool` 不在顶层）与 M-9（`path` 根本不存在）都是这么找出来的。
   **`path=None` 这类词来自内部 Python API，不是公共契约。**
3. **验收材料本身也是「被验收对象」的一部分** —— 读者 checkout 的是 tag，
   读的是树里的文件。**修复没进 tag，就等于没修。** 这条本轮才发现，
   前两轮都只核「材料内容对不对」，没核「读者读到的是哪一版」。

---

*本文件由第三轮读者视角预演窗口写成。它不是验收结论 —— 40 个验收项一条也没有
被判「通过」，判定权仍在未参与实现的读者手上。*
