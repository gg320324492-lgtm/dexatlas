# M10 邀请函 —— 读者视角预演记录（第二轮，只读）

> **本文件的性质：** 这是一次**只读预演**：照着定稿后的邀请函与读者包给的命令，
> 从 clone 走到打分的模板前，把每一步实际跑了一遍，记录「命令 / 实际输出 /
> 与材料是否对得上 / 耗时」，并标出会让读者卡住、被误读或觉得多余的地方。
> 口径与上一轮（[第一轮预演](invitation-reader-rehearsal.md)）一致：
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
| 预演日期 | 2026-11-18（第二轮） |
| 上一轮预演针对的树 | `3e943b5b7870112f9df8994268482b30255d2e16` |
| 本轮验收对象 | `v1.0.0` 这个 tag 所指的提交 |
| `git rev-parse "v1.0.0^{commit}"` | `2715aefda06c3cbbc055a9edf795535e71464068` |
| `git rev-parse v1.0.0`（tag 对象） | `b2720eecc2af37ae6a715c4a4b1634ab31dda40b`（**与上一串不相等**） |
| `git cat-file -t v1.0.0` | `tag`（**附注 tag**） |
| 副本来源 | 本地克隆 `E:/Dexatlas` → `.scratch/reader-rehearsal-2nd/dexatlas`（**离线**；未走 GitHub，见 §8） |
| OS | Windows 11 Pro 10.0.26300 |
| Python / uv / JDK | 3.12.10 / 0.11.21 / 21.0.11（OpenJDK） |
| 后端 | jadx 1.5.2、apktool 2.11.1（`E:\Dexatlas\.scratch\backends`，经 `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 指向）、androguard 4.1.4 |
| 其它 | gh 2.97.0（已登录）、Docker 29.9.2（无本地 dexatlas 镜像） |
| 走过的步数 | **59 步**（材料路径上的命令）；**跳过 2 步**（`fetch-fixtures.sh`、Docker 路线）；**1 步用等价静态检查代替**（「双击打开 HTML」） |
| 计算耗时合计 | 材料路径上的命令约 **2–3 分钟**（不含阅读材料与思考的时间） |

**副本与 tag 的纪律**：克隆后 `git tag -l` 拿到全部 8 个 tag，`git checkout v1.0.0`
进入 detached HEAD（`HEAD is now at 2715aef`），`git status --porcelain` 无输出，
`git rev-parse HEAD` = `2715aefda06c3cbbc055a9edf795535e71464068`。这一条链路是通的。

**这一轮与上一轮最大的不同**：tag 已经从 `3e943b5` 移到了 `2715aef`，而
`2715aef` 之后又有一个提交 `7a416bd`（把邀请函里的 hash 填上）。**填 hash
这个动作本身不在 tag 所指的树里**——这件事是本轮最重要的发现，见 S-2。

---

## 1. 结论摘要

| | 数量 | 最要紧的一条 |
|---|---:|---|
| **卡住**（材料让你做的事做不到，或缺材料没给的东西） | **3** | F3 要判「MCP 工具清单为契约表的 11 个」，但材料给的那条命令**不列清单**，读者得自己写一个 MCP 客户端 |
| **误读**（材料可以有两种理解，而读者会读错那一种） | **6** | 邀请函 §四 说 locator「要能在你导出的证据包里解析到对应字节」——demo 包里**没有一条 locator 解析到字节**，照字面判会把 ★ 阻断项 C3 判成不通过 |
| **多余**（不必要的动作，或同一件事说了两遍而两遍不一致） | **2** | G3 的预期在三份材料里各写一遍，三遍的条数不一样、且没有一处互相指向 |
| 合计 | **11** | |

**40 项验收项的三类归属**：

| 归属 | 项数 | 是哪些 |
|---|---:|---|
| **能自己判** | **39** | A1–A7、B1–B6、C1–C6、D1–D5、E1–E5、F1、F2、F4–F6、G1–G5 |
| **必须问作者** | **1** | **F3**（★ 无关，但无命令可用） |
| **没判据** | **0** | |

**与上一轮比**：上一轮是「2 卡住 / 7 误读 / 3 多余」，**39 项能自己判、1 项
（G3）必须问作者**。这一轮 **G3 解开了**（判据改成「至少一条 + 报告照常产出」，
命令也齐了），**F1/F2/F3/F4 的命令补齐了**；但 **F3 换了一个新的理由必须问作者**
（命令补了，但那条命令不产出要判的东西），并且**冒出一条新的 ★ 级误读**
（邀请函 §四 的 locator 判法）。

---

## 2. 我实际走了多少步

### 2.1 §3.1 取得固定副本（验收项 A1）—— 8 步

| # | 命令 | 退出码 | 实际输出 | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 1 | `git clone E:/Dexatlas <dest>`（**本地源，替代 GitHub URL**） | 0 | `Cloning into '...dexatlas'...` | 2.6 s | ⚠ 替代，见 §8 |
| 2 | `git tag -l` | 0 | 8 个 tag，含 `v1.0.0` | <0.1 s | ✓ |
| 3 | `git checkout v1.0.0` | 0 | `HEAD is now at 2715aef run 记录改成当前的事实：…` | <0.1 s | ✓ 附注 tag 可直接 checkout |
| 4 | `git status --porcelain` | 0 | （空输出） | <0.1 s | ✓ 干净 |
| 5 | `git rev-parse HEAD` | 0 | `2715aefda06c3cbbc055a9edf795535e71464068` | <0.1 s | ✓ **与邀请函 §2 那一串逐字相同** |
| 6 | `git rev-parse v1.0.0` | 0 | `b2720eecc2af37ae6a715c4a4b1634ab31dda40b` | <0.1 s | ✓ **与上一串不相等**（附注 tag） |
| 7 | `git cat-file -t v1.0.0` | 0 | `tag` | <0.1 s | ✓ |
| 8 | `git diff --stat 2715aef HEAD -- docs/`（自加，非材料步骤） | 0 | 5 个文件有差异 | 0.4 s | **← S-2 的起点** |

### 2.2 §3.2 环境准备（验收项 A2、A3）—— 2 步

| # | 命令 | 退出码 | 实际输出 | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 9 | `uv sync --extra dev --extra analysis --extra mcp --extra demo` | 0 | 依赖装齐 | **12.7 s** | ✓（暖 uv 缓存） |
| 10 | `uv run dexatlas backends` | 0 | `jadx available 1.5.2` / `apktool available 2.11.1` / `androguard available 4.1.4` | 1.8 s | ✓ 与 §3.2 的预期一致 |

> 附带核了一条材料没写的：`uvicorn 0.54.0` 与 `fastapi 0.143.0` 是**核心依赖**，
> 不是某个 extra 带来的——所以 §3.8 那条 `uv run --no-sync uvicorn …` 在只装了
> 四个 extras 的环境里能跑通 ✓（这条不是问题，是给主会话的一个确认）。

### 2.3 §3.3–§3.4 首次分析与检索（验收项 A4、B2–B5）—— 7 步

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 11 | `uv run dexatlas analyze examples/demo-app/demo.apk` | 0 | `apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (4.0s)` | 4.7 s | ✓ **逐字命中** |
| 12 | `dexatlas manifest apk_80a8fe0e81204c9f` | 0 | `com.example.demo` / `version 1.0 (1)` / `sdk min 24 / target 34` / `permissions 1` / `components 3` / MainActivity + SyncService 均 `no permission guard` | 1.0 s | ✓ B2 |
| 13 | `dexatlas search … "Crypto"` | 0 | 1 class + 3 method + 3 string 命中 | 1.0 s | ✓ B3 |
| 14 | `dexatlas search … "sk_live"` | 0 | `Kind=string` 命中 `sk_live_2f8a91c4e7b3` | 1.0 s | ✓ B3 |
| 15 | `dexatlas source … com.example.demo.MainActivity` | 0 | `source kind: java` / `jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java` | 1.1 s | ✓ B4 |
| 16 | `dexatlas xrefs … describe(...)` | 0 | `1 call site(s), 1 call edge(s)`，调用点 `classes.dex@34` | 1.0 s | ✓ B5 |
| 17 | `dexatlas classes` / `dexatlas methods`（复算计数，C4） | 0 | 5 个类（Crypto / MainActivity / NetworkClient / **R** / SyncService）、8 个方法 | 1.2 s | ✓ 与 A4 的计数逐项对上 |

### 2.4 §3.5–§3.6 报告、证据包与校验（验收项 A5、C1–C6、D1–D5、G5）—— 14 步

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 18 | `dexatlas analyze … -o report.md --json report.json --html report.html` | 0 | 三份文件：`report.md` 5262 / `report.json` 11746 / `report.html` 8606 字节，同一个 `apk_80a8fe0e81204c9f` | 4.3 s | ✓ A5 |
| 19 | 读三份报告的计数 | — | md / html / json **三处都是** 5 / 8 / 23 / 21 / 1 | 0.2 s | ✓ D2 |
| 20 | `dexatlas export … -o evidence.zip` | 0 | `4 files: 3 reports + 1 manifest` | 1.2 s | ✓ 与 §3.6 的括注一致 |
| 21 | `python -m zipfile -l evidence.zip` | 0 | 4 个条目：`reports/report.{html,json,md}` + `manifest.json` | 0.2 s | ✓ |
| 22 | `verify_package` + `verify_citations` | 0 | `{'citations_total': 14, 'citations_resolved': True, 'citations_unresolved': [], …}` | 1.0 s | ✓ C5 / C6 |
| 23 | 解包读 `manifest.json` | — | `not_included` 三条（apk / full_sources / unrelated_strings）；`files` 清单 3 项；**包内无 APK** | 0.2 s | ✓ D3 / G5 |
| 24 | 逐条列 11 条 evidence 的 provenance | — | 工具 / 版本 / locator / level 四字段齐全，无空值 | 0.2 s | ✓ C1 |
| 25 | 把 `evidence.zip` 复制到 `/tmp/dex-migration-test` 后复验 | 0 | 仍然 `citations_resolved=True` | 1.1 s | ✓ C6 迁移 |
| 26 | 在包里搜机器绝对路径 | — | `machine-absolute path hits: none` | 0.3 s | ✓ C6 |
| 27 | `certutil -hashfile evidence/reports/report.md SHA256` | 0 | `9c2cd5f7…` = manifest 里那一串 | 0.4 s | ✓ §3.5 第 5 步 |
| 28 | 同上，抽查 `report.json` | 0 | `c99bc142…` = manifest 里那一串 | 0.4 s | ✓ |
| 29 | HTML 结构静态检查（`<script>` / `<link>` / `src=` / `href=` / `http` / `on*=`） | — | 全为 0 | 0.3 s | ✓ D1（替代「双击打开」） |
| 30 | HTML 严格解析（标签配对、`&lt;` 计数） | — | 未闭合 0、错配 0；`<!DOCTYPE html>` 之外无杂散 `<` | 0.3 s | ✓ D5 |

> **附带核了一条 ★ 相关的事实（D2 / B6）**：案例 §8 说「打包的 `report.json` 与散落的
> `report.json` **逐字节相同**（sha256 `921d3d3e…`）」。实测**散落的那两份是
> `analyze` 写出来的，带本机 CRLF**（`report.json` 11746 字节 / 364 个 CRLF；
> `report.md` 5262 字节 / 91 个 CRLF），与包里的（11382 / 5171 字节，0 个 CRLF）
> **不是逐字节相同**。但案例 §8 的原文已经**把这层区别写清楚了**——它说的是
> 「**散落的报告文件是从包里拷出来的那几份**」，并明说「`analyze` 写出来的那几份
> 带本平台的 CRLF 行尾，哈希只在产出它们的机器上才相同」。逐字核了附件本身：
> `docs/case-studies/attachments/demo-report.json` 的 sha256 **正是**
> `921d3d3e3c8b6b08f5c3d23488e333d610bfeadf41cbb67ed8c471ea5a67f63e`，CRLF 计数 0 ✓。
> **上一轮的 M-4 已修 ✓**，本轮不再是问题。

### 2.5 §3.7 完整案例核对（验收项 B1、B6）—— 1 步 + 阅读

| # | 动作 | 结果 |
|---|---|---|
| 31 | 把 `docs/case-studies/demo-app-walkthrough.md` §4 的证据表与自己的 11 条记录逐行对照 | **11 行全部对上**（ID / level / kind / 工具 / 版本 / locator / summary），案例里「eleven evidence records」与实测的 11 一致 ✓ |

### 2.6 §3.8 契约与回归集抽查（验收项 E、F 组）—— 12 步

| # | 命令 | 退出码 | 实际输出 | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 32 | `dexatlas analyze …`（F1 第 1 条） | **0** | `✓ apk_80a8fe0e81204c9f — 5 classes, …` | 3.6 s | ✓ |
| 33 | `dexatlas search … __no_such_term__`（F1 第 2 条） | **1** | `No matches for '__no_such_term__'.` | 1.0 s | ✓ |
| 34 | `dexatlas analyze README.md`（F1 第 3 条） | **2** | `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives` | 0.9 s | ✓ |
| 35 | `uvicorn dexatlas.api.app:app --port 8000` | **1** | `ERROR: [Errno 10048] … 端口被占` | 9 s | ✗ **← S-3** |
| 36 | `uvicorn … --port 8011`（改端口） | 0 | `Uvicorn running on http://127.0.0.1:8011` | 9 s | ✓ 换端口后正常 |
| 37 | `curl -s localhost:8011/health` | 0 | `{"status":"ok","version":"1.0.0","backends":{…}}` | 0.2 s | ✓ F2 |
| 38 | `curl -s localhost:8011/projects` | 0 | `[{…class_count:5, method_count:8, …}]` | 0.2 s | ✓ F2 |
| 39 | `curl -s localhost:8011/projects/{pid}` | 0 | 与契约 §2.3 的 `ProjectResponse` 字段一致 | 0.2 s | ✓ F2 |
| 40 | `curl -s …/runs` | 0 | `{"project_id","total":3,"published_run_id","runs":[…]}` | 0.2 s | ✓ F2 |
| 41 | `curl -s …/search?q=Crypto` | 0 | `{"project_id","query","results":[…]}` | 0.2 s | ✓ F2 |
| 42 | `curl -s …/manifest` | 0 | 8 个字段（`components/min_sdk/package/…`） | 0.2 s | ✓ F2 |
| 43 | `curl -s …/classes/…/source` 的响应头 | 0 | `x-dexatlas-source-kind/tool/locator/tool-version` | 0.2 s | ✓ F2 |

### 2.7 §9.1 与 §9.2 补做（验收项 F3、F4、F5、F6、G 组）—— 7 步

| # | 命令 | 退出码 | 实际输出 | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 44 | `curl -s …/report?format=json` | 0 | `['errors','evidence','generated_at','latest_attempt_status','manifest','project','run','schema_version','summary','tools']` —— **正好 10 个** | 0.3 s | ✓ F4 |
| 45 | `uv run --no-sync dexatlas-mcp`（F3 材料给的命令） | 0 | **没有任何输出** | 0.3 s | ✗ **← S-1** |
| 46 | 自写 MCP 客户端（`mcp` SDK 的 `stdio_client`）→ `tools/list` | 0 | **11 个工具**，全部 `read_only_hint=True / destructive_hint=False / idempotent_hint=True / open_world_hint=False`；再 `call_tool("get_project_status")` 返回正常 | 12 s | ✓ F3 的**判据**成立，但**不是照材料命令拿到的** |
| 47 | `pytest tests/test_public_contracts.py -q` | 0 | `31 passed in 3.83s` | 3.8 s | ✓ F5 |
| 48 | `python scripts/verify-public-contracts.py` | 0 | `48/48 checks passed`，含 `PASS an analysis with no index exits 6` | 14.6 s | ✓ F6 + G3 的交叉引用 |
| 49 | `python scripts/check-contract-records.py --expect with-jadx` | 0 | 「这台机器就是 CI 那台配置」 | 16 s | ✓ §9.2 表 |
| 50 | `python scripts/check-contract-records.py --expect without-jadx`（本机装了后端） | **2** | 「契约成立，但这台机器不是那个配置」 | 16 s | ✓ §9.2 表 |

### 2.8 G 组故障恢复（验收项 G1–G5）—— 9 步

| # | 命令 | 退出码 | 实际输出 | 耗时 | 与材料对得上 |
|---|---|:--:|---|---:|---|
| 51 | `dexatlas projects`（**在 A4 用过的同一个工作区**） | 0 | 列出 1 条 `apk_80a8fe0e81204c9f` | 1.0 s | ✗ 与 §9.1 G1「列表是空的」不符 **← M-3** |
| 52 | `DEXATLAS_WORKSPACE=/tmp/g1-fresh dexatlas analyze README.md` | **2** | `Not a usable APK: README.md is not a ZIP archive; …` | 0.9 s | ✓ G1 |
| 53 | `DEXATLAS_WORKSPACE=/tmp/g1-fresh dexatlas projects` | 0 | `No projects yet. Run \`dexatlas analyze <apk>\`.` | 1.0 s | ✓ G1（**空工作区**才成立） |
| 54 | `DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR= dexatlas analyze …` | 0 | 两条 `not_installed`；`4 classes, …, 0 resource strings` | 0.7 s | ✓ G2 / A6 |
| 55 | 读降级那次的 `errors[]` / `tools` | — | `[('apktool','not_installed'),('jadx','not_installed')]`；`{"jadx":null,"apktool":null,"androguard":"4.1.4"}` | 0.2 s | ✓ G2，**与 §9.1 的每一句都对上** |
| 56 | `DEXATLAS_TOOL_TIMEOUT_SECONDS=1 dexatlas analyze …`（G3） | **0** | 一条 `! jadx exceeded its 1s timeout; its launcher had already exited` | 4.3 s | ✓ G3（**条数只有一条**，见 M-1） |
| 57 | 读超时那次的 `errors[]` / `index_*` | — | `[('jadx','timeout')]`；`index_complete=True`；`index_gaps=[]`；`evidence_count` 12（正常运行 11） | 0.2 s | ✓ G3，与 §9.1 的第二段括注一致 |
| 58 | `dexatlas analyze …` ×2 + `dexatlas projects`（G4） | 0 / 0 / 0 | 两次同一个 project id、同样的计数；`projects` 只列 **1** 条 | 7.6 s | ✓ G4 |
| 59 | `uv run --no-sync python scripts/m10_selfcheck.py`（自查脚本） | 0 | `通过 43，失败 0，需人工 40` | 2.0 s | ✓ 数字与邀请函 §五 一致；**但「需人工 40」就是那 40 个验收项**，见 M-4 |

> 另附三条与判据无关、但我顺手核过的边界：`DEXATLAS_TOOL_TIMEOUT_SECONDS=0`
> → 退出码 1 + 一段 pydantic 校验回溯（材料只说「取值不得小于 1」，没说会这样）；
> `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` **不写**与**写成空值**在本机
> 表现相同（都是 `not installed`），因为本机的 jadx / apktool 不在 PATH 上——
> §9.1 说的「空值与不写是两件事」在本机观察不到差别。

---

## 3. 卡住（3 条）

### S-1 【验收项 F3】MCP 工具清单：材料给的那条命令不列清单

**材料怎么说**：读者包 §3.8 把它写成一行命令，注释写着「列工具清单」——
`uv run --no-sync dexatlas-mcp                               # 起 MCP server（列工具清单）`
（这行命令在 `v1.0.0` 那棵树的读者包第 314 行；材料后来换成了协议级的两条，现行材料在 `docs/reports/m10-reader-package.md:491`）。

**实际发生**：这条命令**不产生任何输出**。空 stdin 跑一遍，stdout 一个字节都没有，
退出码 0：

```text
$ echo -n "" | timeout 10 uv run --no-sync dexatlas-mcp
EXIT=0
```

它是一个 **stdio 传输的 JSON-RPC server**（`dexatlas-mcp` = `dexatlas.mcp.server:main`，
`main()` 只做 `build_server(Analyzer()).run(transport="stdio")`）。工具清单要走
协议层的 `tools/list` 才拿得到，**没有 CLI 开关**（`grep -n "argparse\|sys.argv\|add_argument\|list_tools" src/dexatlas/mcp/server.py` 无命中）。

**为什么算卡住**：F3 的判据是「MCP：工具清单为契约表的 11 个，全部只读注解；
**抽查 2 个工具的返回形状**」（`docs/reports/m10-acceptance-pack.md:153`）。要判
「全部只读注解」与「返回形状」，读者得先把工具清单列出来、还得真调两个工具。
材料给的命令两件事都做不到。我最后是自己写了 **20 行** 的 MCP 客户端脚本
（`mcp` SDK 的 `stdio_client` + `ClientSession.list_tools()`）才拿到：

```text
server name: dexatlas
tool count: 11
  list_projects              {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  get_project_status         {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  get_manifest               {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  search_symbols             {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  get_class_source           {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  get_method_source          {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  find_callers               {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  find_callees               {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  get_evidence               {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  resolve_locator            {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
  find_resource_declarations {'read_only_hint': True, 'destructive_hint': False, 'idempotent_hint': True, 'open_world_hint': False}
```

**判据本身是真的**（11 个工具、全部只读注解、与契约表 §3.1 的清单逐名对上）——
但**按材料走不到那里**。而且邀请函 §一 明确写着「**您不需要写代码**，只需要执行
命令、观察输出、按写在检查表里的标准判定」，与「要判 F3 就得自己写个 MCP 客户端」
直接冲突。读者须知第 4 条又规定「凡是需要作者口头补充才走通的步骤，相关验收项判
不通过」——照材料严格走，F3 只能落进「未验证」。

**给主会话的三个修法（挑一个即可）**：
1. 给 `dexatlas-mcp` 加一个 `--list-tools`（或 `--dump-tools`），打印工具名与注解——
   一行命令就能照抄；
2. 或在读者包 §9.1 里直接给一段可照抄的 10 行 Python（用已装的 `mcp` extra），
   并在 F3 的判据里写明「用这段脚本枚举」；
3. 或把 F3 的判据降级为「对照契约表 §3.1 逐行核对源码里的 `@server.tool` 装饰器」，
   明确**不要求协议实测**（这样就不必让读者写代码，但要把「未做协议实测」写进记录）。

### S-2 【验收项 A1 / 邀请函 §2 / 记录模板 §1】tag 所指的树里，hash 还是占位符

**这是本轮最重要的一条。**

邀请函 §2 里那一串 hash 已经填好了（工作区里是
`docs/reports/m10-invitation-final.md:81`：
`commit 2715aefda06c3cbbc055a9edf795535e71464068`）。但**填 hash 的那个提交
`7a416bd` 在 tag 之后**——`v1.0.0` 指的是 `2715aef`，而 `2715aef` 的树里：

```text
$ git show 2715aef:docs/reports/m10-invitation-final.md | sed -n '79p'
commit 【待填：v1.0.0 发版 commit 的完整 hash】

$ git show 2715aef:docs/reports/m10-review-record-template.md | sed -n '17p'
| commit hash | 照抄[邀请函成稿 §2](m10-invitation-final.md)钉定的那一串完整 hash（40 位） |
```

**读者会同时面对三个指向空处的指针**：

| 指针 | 指向 | 读者在 tag 树里看到的是 |
|---|---|---|
| 记录模板 §1 的「commit hash」栏 | 邀请函成稿 §2 | 一句「照抄……那一串」，**而那一处是占位符** |
| 读者包 §1.6「完整 hash 在[邀请函成稿 §2]」 | 邀请函成稿 §2 | 同上，**占位符** |
| 邀请函成稿 §2 自己的正文（tag 树版本） | 「上面填入的那一串」 | **占位符** |

也就是说，**记录模板让读者「照抄」的那一串，在读者被要求 checkout 的那棵树里
不存在**。读者能拿到它的唯一途径是：邀请函的**信件正文**（发起人手上那份），
或者自己跑 `git rev-parse v1.0.0^{commit}`（邀请函 §2 确实给了这个核对方式）。

**为什么算卡住**：记录模板 §1 明确要求「照抄……钉定的那一串完整 hash（40 位）」；
严格照树做，读者做不到这件事，只能凭空写、或者去问作者。这符合「材料让你做不到的
事，或缺材料没给的东西」。

**还有一个更要紧的后果**：邀请函 §2 的措辞是「`git checkout v1.0.0` 所得到的那个
提交，**即含本轮全部材料修正的版本**」。实测：`git diff --stat 2715aef HEAD -- docs/`
显示有 5 个文件不同，其中两个正是**邀请函本身**与**记录模板本身**。G3 的判据、
F1–F4 的命令、C 组的归属这些修正**都在** tag 树里 ✓，唯独「§2 填 hash」与
「模板填 hash」这两处修正**不在**。

**给主会话的三个修法（挑一个即可，注意这里有个循环）**：
1. **把 tag 重打到包含 `7a416bd` 的树上**，然后**把邀请函 §2 里的 hash 改成新
   tag 的 hash**——但这一次又要一个提交，于是又落在新 tag 之外。**这条路走不通，
   除非材料接受「树里的邀请函永远是占位符」这件事。**
2. **改材料承认这一点**：在记录模板 §1 与读者包 §1.6 都写明「**完整 hash 以你收到的
   邀请函正文为准**；树内的这一份是发出前的草稿（§2 的 hash 由发起人在发信时填入，
   因此不在被验收的树里）——核对方式：`git rev-parse v1.0.0^{commit}`」。这一条
   **与邀请函 §2 自己的说法最自洽**（它本来就写着「由验收发起人在发出本函之前填入」）。
3. **把 hash 从「树里的文件」挪到「树外的一份」**：例如发信时附一份
   `acceptance-commit.txt`，树里只留「见发信附件」。这样树的 hash 与邀请函的 hash
   彻底解耦，读者核对 `git rev-parse v1.0.0^{commit}` 即可。

> 顺带核过：邀请函 §2 那句「`git rev-parse v1.0.0` 与本函这一串**永不相等**」、
> 以及「`git cat-file -t v1.0.0` 打印 `tag`」——**两句都对**（实测
   `b2720eec…` ≠ `2715aef…`，`cat-file -t` 打印 `tag`）✓。所以问题不在 §2 的
   **数值**上，而在**它存在于哪棵树里**。

### S-3 【验收项 F2】REST 端口 8000 被占时，材料没有退路，而且失败是**静默**的

**材料怎么说**：读者包 §3.8 直接写死端口：

```bash
uv run --no-sync uvicorn dexatlas.api.app:app --port 8000   # 起 REST 服务
curl -s localhost:8000/health                               # 抽查一个端点的响应形状
```

**实际发生**：这台机器的 8000 端口**已经被别的服务占了**——一个叫
"MicroBubble Agent" 的 FastAPI 应用（`GET /openapi.json` 的 `info.title` 是
`MicroBubble Agent`）。于是：

```text
$ uv run --no-sync uvicorn dexatlas.api.app:app --port 8000
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048]
INFO:     Application startup complete.     ← 仍然打印了这句
```

**最要命的是接下来**：材料给的 `curl` **照样成功**，返回的是**别的应用**的响应：

```text
$ curl -s localhost:8000/health
{"status":"healthy"}                     ← 不是 DexAtlas 的 {"status":"ok","version":…,"backends":…}

$ curl -s localhost:8000/projects
{"detail":"Not Found"}                   ← FastAPI 的 404；DexAtlas 契约里 /projects 是 200 + 数组
```

一个只照材料走的读者会看到：`uvicorn` 报了端口占用（但**紧接着又打印了
「Application startup complete」**，像是成功了），`/health` 返回 `healthy`，
`/projects` 返回 404。**读者很可能把这写成一条 F2 的卡点**（「项目列表端点不存在，
与契约表 §2.3 不符」），而实际上服务压根没起来。

**为什么算卡住**：材料给了三条 REST 命令，但**没有一句「端口被占怎么办」**；
而失败形态是**静默的**——curl 不报错，返回的是形状完全不同的另一个服务的响应。
这不是「读者粗心」，是材料在这个分支上**没有给任何可执行的下一步**。

**给主会话的修法**：在 §3.8 那三条命令旁加一行「端口被占用时换一个（如
`--port 8011`），并把三条命令里的端口一起改掉」，或者干脆写成
`--port ${DEXATLAS_PORT:-8000}`。

---

## 4. 误读（6 条）

### M-1 【G3，★ 阻断项】超时记录的**条数**：材料给的是具体数字，本机是另一个数

**材料怎么说**（三处）：

| 出处 | 原文 |
|---|---|
| 准备包 §2.7 G3 | 「设置极短超时后**至少一条后端记 `timeout` 且报告照常产出**（条数与本机速度有关：没超时的后端不留记录，不是「一定有三条」）」（`docs/reports/m10-acceptance-pack.md:165`） |
| 读者包 §9.1 G3 | 「超时的后端**各记一条 `timeout`**（实测）」+ 三行实测输出（apktool / androguard / jadx 各一条） |
| 读者包 §9.1 G3 的括注 | 「**若 androguard 在你的机器上 1 秒内就跑完了**，`errors[]` 会**只有两条**、`index_complete` 是 `true`——这同样是正确行为」 |
| M8 演练 §5 | 「三后端各记一条 `timeout` 错误（jadx 被杀进程树、apktool/androguard 的 launcher 已先退出）」 |

**实际发生**：本机 1 秒超时下，**androguard 与 apktool 都在 1 秒内跑完了**，
**只有 jadx 超时**：

```text
$ DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze examples/demo-app/demo.apk
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (3.6s)
!  jadx exceeded its 1s timeout; its launcher had already exited
EXIT=0

errors[] (tool,code): [('jadx', 'timeout')]
index_complete: True
index_gaps    : []
classes=5 methods=8 resource_strings=1
evidence_count: 12        ← 正常运行是 11，超时多一条「后端未完成」
```

**为什么算误读**：准备包那一版（**权威**，按 §0「冲突时以本包的判定标准为准」）
写的是**泛化表述**，本机**满足** ✓——G3 判据成立。但读者包给了两个**具体数字**
（「实测」三条、「会只有两条」），而本机是**一条**。一个读者如果把「只有两条」
当成了形状预期，看到一条就会以为「有后端没记 timeout → 缺陷」，在一条 ★ 阻断项上
记一个假卡点。**判据是对的，示范的数字不是形状。**

**给主会话的修法**：把读者包 §9.1 里「会只有两条」改成「**会少于三条**（本机实测
只有一条：androguard 与 apktool 都在 1 秒内跑完了，只剩 jadx 超时）」，或者把
「实测」那三行改成「**示例**（本机三后端都慢时；条数随后端速度变化）」。

### M-2 【G3，★ 阻断项】「核对 M8-4 的退出码语义」指向的那一节，写的是**修复前**的语义

G3 的判据里有半句是：「本项只需**核对 M8-4 的退出码语义**并记录实际退出码」。
读者包 §4.4 也写着「M8-4（**已在 v1.0.0 关闭**）…复现与理由见 M8 演练 §6」。
准备包 §7 的表格也写「已关闭（v1.0.0 退出码 6）」✓。

**但 M8 演练 §6 那一节本身，没有任何前向指针**：

```text
docs/reports/m8-install-rehearsal.md:138
### M8-4（重要，涉及退出码契约，留主会话决策）全部后端超时后 run 仍 completed、退出码 0
```

这一节的正文写的是「**退出码仍是 0**」「本轮只记录不改」「留主会话决策」——
**是 v1.0.0 之前的状态**。而且：

```text
$ grep -n "EXIT_NO_INDEX\|1\.0\.0\|退出码 6" docs/reports/m8-install-rehearsal.md
（无输出）
```

**这一节里一次都没提过退出码 6**。也就是说，G3 让读者去核对的那一节，说的与
G3 想要的结论**正好相反**，而且没有任何一处提示「这一节是当时的实况」。
闭合只写在 `docs/status.md:135`、准备包 §7、读者包 §4.4 和契约表 §1.2 里——
**没有一个是指向 M8 演练 §6 的**。

一个认真核对 G3 的读者会得出「M8-4 的缺口还在」的结论，并在一条 ★ 阻断项上
记一条假卡点。

**旁证**：`docs/reports/m10-number-traceability.md:247` 早就指出过这件事要改——
「原 M8 演练记录（`m8-install-rehearsal.md:138`–`:145`）是当时的实况，
**需加一句「已在 1.0.0 解决」或改指新契约**」——**这一条没有落地**。

**给主会话的修法**（二选一，都是一行）：
1. 在 M8 演练 §6 的 M8-4 标题下加一行「**已在 v1.0.0 关闭**：新增退出码 6
   （`EXIT_NO_INDEX`），见契约表 §1.2 与[提案]」；
2. 或在 G3 的判据里把「核对 M8-4 的退出码语义」改成「**核对退出码 6 的语义**
   （契约表 §1.2；M8-4 是提出该缺口的历史记录，已由退出码 6 关闭）」。

### M-3 【G1】`projects` 预期为空，与材料规定的执行顺序冲突（上一轮 M-5，未改）

读者包 §9.1 G1 写：「再确认**工作区里没有留下半成品项目**」，命令是
`uv run dexatlas projects`，预期「`No projects yet. …`——**列表是空的**」
（`docs/reports/m10-reader-package.md:561`）。

但 §9.1 是**附录**，排在 §3.3–§3.6 之后，而 §3.3 已经分析过 demo.apk 了。
在**同一个工作区**里跑：

```text
$ uv run dexatlas projects
Projects (1)
┌──────────────────────┬──────────┬───────────┬─────────┬─────────┐
│ apk_80a8fe0e81204c9f │ demo.apk │ completed │       5 │       8 │
└──────────────────────┴──────────┴───────────┴─────────┴─────────┘
```

**列表不是空的**——那条是 A4 的项目，不是「半成品」。只有**空工作区**里才是
那个预期：

```text
$ DEXATLAS_WORKSPACE=/tmp/g1-fresh dexatlas analyze README.md   # → 退出码 2
$ DEXATLAS_WORKSPACE=/tmp/g1-fresh dexatlas projects
No projects yet. Run `dexatlas analyze <apk>`.
```

§9.1 开头说「这四条命令**互相独立**，各跑各的」，但没说「**要在空工作区里跑**」。
一个按 §9.1 顺序走的读者（先走完主路径，再补附录）会看到非空的列表，并在 G1 上
记一条假卡点。**这条与上一轮的 M-5 是同一个问题，本轮未改。**

**给主会话的修法**：把 G1 的预期改成「**在一个空工作区**里（`DEXATLAS_WORKSPACE=<新目录>`）
跑 `analyze README.md` 后 `projects` 应为空；主工作区里它列着 A4 的项目，是正常的」。

### M-4 【邀请函 §五】「40 项留人工……与您要判的 40 项**不是同一组东西**」——这句是错的

邀请函 §五 写：

> 作者另有一套自动化自查脚本（`scripts/m10_selfcheck.py`），当前快照是
> 「43 条自动化判定通过、40 项留人工」……那是**另一个分母**：43 是脚本自己能回答的
> 检查条数，40 是留给读者实做的那一组，与您要判的 40 项**不是同一组东西**。

（`docs/reports/m10-invitation-final.md:175` 与 `:177`）

**实测**：脚本标「需人工」的 40 条，**编号就是 A1–G5 那 40 个验收项本身**：

```text
$ uv run --no-sync python scripts/m10_selfcheck.py | grep -oE "^\[需人工\] [A-G][0-9]+" | awk '{print $2}'
A1 A2 A3 A4 A5 A6 A7 B1 B2 B3 B4 B5 B6 C1 C2 C3 C4 C5 C6
D1 D2 D3 D4 D5 E1 E2 E3 E4 E5 F1 F2 F3 F4 F5 F6 G1 G2 G3 G4 G5
count: 40
```

而且自查文档自己写对了：「### 2.2 明确留人工的 40 项（脚本标「需人工」）——
验收包 40 个验收项（A1–G5）中的绝大多数需要读者在真实机器上执行命令」
（`docs/reports/m10-selfcheck.md:64`）。

**所以「不是同一组东西」是反的**：它们**就是同一组**，连编号都一样。而且还有第二层
混乱——这 40 个编号里有 **13 个同时出现在脚本的「通过」清单里**
（A4、A6、D1、D3、D5、E1、E5、F1、F2、F3、F4、F5、F6），所以「43 / 40」这两个
数字在 ID 上是**重叠**的，「另一个分母」这个说法还会让读者以为自己的 40 项是
**第三**组东西。

**为什么算误读**：邀请函是**发给读者的那一份正文**。读者照它去读自查脚本的输出，
会看到一堆和自己清单**一模一样的编号**，却被告知「不是同一组」——读者要么困惑，
要么（更可能）从此不再把自查脚本的逐项输出当成自己清单的对照。

**给主会话的修法**：把那句改成「**那 40 项就是您要判的这 40 项**（按编号 A1–G5
一一对应）——自查脚本对其中 13 项能静态自检，但**它不能替您判定**；M10 的判定
只来自您亲手执行的记录」。

### M-5 【F2】「抽查 3 个端点」，材料给的命令只覆盖 6 个关键端点里的 2 个

F2 的判据是：「REST：关键端点（**上传 / 项目 / 运行 / 符号 / 源码 / 报告**）的
响应形状与状态码与契约表一致；**抽查 3 个端点**」
（`docs/reports/m10-acceptance-pack.md:152`）。

而 §3.8 给的「抽查用的命令」是：

```bash
uv run --no-sync uvicorn dexatlas.api.app:app --port 8000
curl -s localhost:8000/health
curl -s localhost:8000/projects | head -c 400
curl -s "localhost:8000/projects/apk_80a8fe0e81204c9f/report?format=json" | …
```

这三条 curl 命中的是 **`/health`（元信息）、`/projects`（项目）、`/report`（报告）**。
按契约表 §2 的分组，`/health` 属于 **§2.1 元信息**，**不在** F2 点名的那 6 个
关键端点里；6 个里只覆盖了「项目」与「报告」两个。**上传、运行、符号、源码
四个端点的路径，材料一个都没给。**

读者照 §3.8 抄完，会记「F2 通过（抽查 3 个端点）」，而实际抽查的 3 个里有 1 个
不在 F2 的关键端点表上。补救路径是存在的（契约表 §2.3–§2.6 有全部路径，材料也
说了「判据都在公共契约表里」），但**材料自己给的「抽查用的命令」没兑现 F2 自己的
判据**。

**给主会话的修法**：§3.8 的 REST 命令块里补两条，把 6 个关键端点各覆盖一个：

```bash
curl -s "localhost:8000/projects/apk_80a8fe0e81204c9f/runs" | head -c 400   # 运行
curl -s -D - -o /dev/null \
  "localhost:8000/projects/apk_80a8fe0e81204c9f/classes/com.example.demo.MainActivity/source"  # 源码
```

（这两条本轮实测都通，形状与契约表 §2.3–§2.5 一致，见 §2.6 的第 40–43 行。）

### M-6 【验收项 C2 / C3，★ 阻断项】邀请函说的 locator 判法，与准备包说的**不是一件事**

邀请函 §四 第 4 步（读者要照做的执行路径）写：

> 任选 3 条 evidence 记录核对工具、版本、locator、level 四字段：
> - `tool` 与 `version` 抄这条 evidence 记录自己写的值，不用另行查证；
> - **`locator` 要能在你导出的证据包里解析到对应字节**；
> - …
> - 四字段里只要有一项与你抽到的证据对不上……就写进客户视角审阅备忘——
>   这是验收项 **C3（★ 阻断项）** 的判定依据。

（`docs/reports/m10-invitation-final.md:139`）

**实际发生**：demo 项目的 11 条 evidence，**locator 全部**是
`androguard:AndroidManifest.xml`、`apktool:AndroidManifest.xml#/application`、
`androguard:classes.dex#…`、`jadx:sources`（裸树）这一类。证据包里**没有一条**
解析到字节——包里只有 3 份报告 + 1 份 manifest，没有 `sources/` 目录，也没有 DEX。
这正是 `verify_citations` 所说的「**按构造解析**（resolved by construction, not by
a file here）」——代码里 `src/dexatlas/reports/evidence_package.py:302` 的
`verify_citations` 对 DEX locator 与裸树 locator 都走 `resolved += 1; continue`，
不查包内文件。

**两份材料说的不是一回事**：

| 出处 | 判法 |
|---|---|
| 邀请函 §四 第 4 步 | locator 必须「在证据包里**解析到对应字节**」 |
| 准备包 §2.3 C2（★，权威） | 「DEX 成员 locator 与裸树 locator（如 `jadx:sources`）**按构造解析**（`path=None` 是设计，不是失败）」 |
| 准备包 §3.5 第 4 步 | 「包内没有 `sources/` 是**正确的**——它们按构造解析」 |
| 读者包 §3.4 | 「locator 解析规则见[准备包 §2.3 C2]」✓（指向了权威版） |

**为什么算误读**：邀请函是**发出去的那一份**，它给的是**更严的那条**，而且明说
「对不上 → 写进审阅备忘 → 这是 **C3（★ 阻断项）** 的判定依据」。一个读者照
邀请函字面执行，随手抽 3 条（**11 条里随便抽 3 条都会全中**），会发现三条 locator
都「解析不到字节」，于是**在两条 ★ 阻断项上各记一条假卡点**——而这是**设计**。

**给主会话的修法**：把邀请函 §四 第 4 步那一条改成
「`locator` 要能在你导出的证据包里解析到对应字节；**DEX 成员 locator 与裸树
locator 按构造解析（`path=None` 是设计，不是失败）——解析规则见
[准备包 §2.3 C2](m10-acceptance-pack.md)」。

---

## 5. 多余（2 条）

### X-1 G3 的预期在三份材料里各写一遍，三遍的条数不一样，也没有一处互相指向

同一条命令（`DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze …`）的预期
写在三处，三处的**条数**与**语义**各不相同：

| 出处 | 写的是什么 | 与本机实测 |
|---|---|---|
| 准备包 §2.7 G3（**权威**） | 「**至少一条**后端记 `timeout` 且报告照常产出（条数与本机速度有关……不是「一定有三条」）」 | ✓ 相符 |
| 读者包 §9.1 G3 | 「超时的后端各记一条（**实测：三条**）」+ 括注「会**只有两条**」 | ✗ 本机是**一条** |
| M8 演练 §5 / §6 | 「**三后端各记一条** timeout 错误」+ 修复前的「退出码 0」 | ✗ 条数与语义都不符 |

三处**没有一处写「详见准备包 §2.7」**（读者包 §0 只笼统说「判定以准备包为准」，
读者要在正文中找）。读者很可能只读到其中一处就下判断。**判据本身是对的
（准备包那一版本机满足），但同一个事实被写了三遍、三遍不一致。**

**给主会话的修法**：读者包 §9.1 与 M8 演练那两处都加一句「**权威判据见
[准备包 §2.7 G3](m10-acceptance-pack.md)**」，并把具体的条数改成「**示例**」。

### X-2 「首次读者路径」在准备包 §3 与读者包 §3 各写一遍，两遍的**步骤清单**不一致

准备包 §3 开头写着「本节**可以原样交给读者**。它不假设读者读过项目其他文档，
也不依赖作者补充步骤」；读者包 §0 写着「本文件把 [M10 独立验收准备包] 整理成
可直接交给一位外部读者的完整执行包」。**两份都是给同一批读者的同一段路径**，
但：

| | 准备包 §3.1 / §3.2 | 读者包 §2 / §3.2 |
|---|---|---|
| `gh CLI` 出现在「你需要什么」表里 | **没有这一行** | 有：「`gh` CLI｜仅 fixtures 需要」 |
| `scripts/fetch-fixtures.sh` 这一步 | **整个 §3 里没有**（只在 §7 的遗留表里被顺带提了一次） | 有，且带「**为什么这一步不能跳**」的解释与「不抓的后果：27 个集成用例会 skip」 |

实测：`grep -n "gh CLI\|fetch-fixtures\|gh api" docs/reports/m10-acceptance-pack.md`
在 §3 里**零命中**（唯一命中在 `:678`，是 §7 遗留问题表的一行）。

所以：一份声称「可以原样交给读者」的路径里**少了两个前置条件**（`gh` CLI、
第三方夹具），而另一份把它们讲清楚了。读者拿到哪一份，决定了他知不知道
`fetch-fixtures.sh` 这件事。

**给主会话的修法**：两份材料的「你需要什么」表与步骤清单**以一份为准**
（建议读者包，因为它是发给读者的那一份），另一份改为指向它；若保留两份，
就把 `gh CLI` 行与夹具步骤补进准备包 §3。

---

## 6. 40 个验收项的三类归属

| 组 | 项 | 能自己判 | 必须问作者 | 没判据 | 备注 |
|---|---|:-:|:-:|:-:|---|
| A 安装与首次运行 | A1–A7 | 7 | 0 | 0 | A1 的 hash 抄写受 **S-2** 影响；A2–A7 实测全通过 |
| B 完整案例 | B1–B6 | 6 | 0 | 0 | 案例 §4 证据表 11 行与实测逐行对上 |
| C 证据核查 | C1–C6 | 6 | 0 | 0 | C2 / C3 受 **M-6** 影响（照邀请函字面会误判） |
| D 离线阅读 | D1–D5 | 5 | 0 | 0 | D5 仍是「样本不足」——demo 样本里没有类 HTML 的字符串（`&lt;` 计数为 0） |
| E 服务回归集 | E1–E5 | 5 | 0 | 0 | 20 题 / 五类 / 92 题同报 / 49/60 = 81.7%（逐轮 15/16/18）都能在材料里核到 |
| F 公共契约 | F1–F6 | 5 | **1（F3）** | 0 | F1 三条命令全对；F2 受 **M-5** 影响；F4 顶层字段正好 10 个 ✓；F3 受 **S-1** 影响 |
| G 故障恢复 | G1–G5 | 5 | 0 | 0 | G1 受 **M-3**；G3 受 **M-1 / M-2 / X-1**；G2 每一句都对得上 |
| **合计** | 40 | **39** | **1（F3）** | **0** | ★ 阻断项 19 个全在「能自己判」里 |

**两点补充：**

1. **「能自己判」不等于「照材料就能判」。** F3 的判据是真的（本机实测 11 个工具、
   全部只读注解），但**按材料走拿不到**——要写一个 MCP 客户端脚本，而邀请函
   明说读者「不需要写代码」。严格按材料走，F3 落进「未验证」。这是 **S-1** 的
   实际后果，也是这一轮**唯一**一项必须问作者的。
2. **D5 仍是「能自己判但样本不足」。** 与上一轮相同：demo 样本里没有类 HTML 的
   字符串（报告 HTML 的 `&lt;` 计数为 **0**），所以「异常文本只作为文本显示」
   这半句，读者**无法用材料给的样本证伪**。D5 在 demo 上是**平凡成立**。
   （`wide-app` 有一个 `"<payload>"`，但 M10 材料没有派它。）

---

## 7. 三件特别要验的事

### 7.1 那个 hash：读者 clone 之后拿到的那一串

| 核什么 | 实际输出 | 结论 |
|---|---|---|
| `git rev-parse "v1.0.0^{commit}"` | `2715aefda06c3cbbc055a9edf795535e71464068` | ✓ |
| 邀请函 §2 那一串 | `2715aefda06c3cbbc055a9edf795535e71464068` | ✓ **逐字相同**（40 位） |
| `git rev-parse HEAD`（checkout 之后） | `2715aefda06c3cbbc055a9edf795535e71464068` | ✓ **逐字相同** |
| `git rev-parse v1.0.0` | `b2720eecc2af37ae6a715c4a4b1634ab31dda40b` | ✓ **不相等**（附注 tag） |
| `git cat-file -t v1.0.0` | `tag` | ✓ |

**结论：数值链路全通 ✓。** 邀请函 §2 的两句提醒（「必须带 `^{commit}`」、
「`git rev-parse v1.0.0` 与本函这一串**永不相等**」）实测都对。

**但树的内容有一处不对**——见 **S-2**：tag 所指的树里，邀请函 §2 与记录模板 §1 的
hash **仍是占位符**（填 hash 的提交 `7a416bd` 在 tag 之后）。**结论：hash 的
「值」是对的；hash 的「所在位置」不对。**

### 7.2 G3：准备包与读者包的预期现在一致了吗？本机跑出来是什么？

**一致了 ✓。** 准备包 §2.7（权威）写「**至少一条**后端记 `timeout` 且报告照常产出
（条数与本机速度有关：没超时的后端不留记录，不是「一定有三条」）」；读者包 §9.1 的
括注写「判据是『后端失败时记 `timeout`、不抛异常、报告照常产出』，**不是「一定有
三条 `timeout`」**」，并且补了一句「只有 jadx 超时时，`index_complete` 是 `true`、
`index_gaps` 是 `[]`——同样正确」。**两处的口径一致，而且本机跑出来正好落在这个
被明确写下来的分支上。**

本机实测：

```text
$ DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze examples/demo-app/demo.apk
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (3.6s)
!  jadx exceeded its 1s timeout; its launcher had already exited
EXIT=0

errors[] (tool,code): [('jadx', 'timeout')]
index_complete: True
index_gaps    : []
evidence_count: 12
```

| G3 判据的每一句 | 本机 | 结论 |
|---|---|---|
| 至少一条后端记 `timeout` | 一条（jadx） | ✓ |
| 报告照常产出 | `report.json` 正常写出 | ✓ |
| 不抛异常 | 退出码 **0**，无异常 | ✓ |
| 退出码 6 不由超时变量触发 | 本次退出码是 **0**；6 由契约活检覆盖（`PASS an analysis with no index exits 6`） | ✓ |
| 「核对 M8-4 的退出码语义」 | 那一节写的还是修复前的语义 | ✗ **M-2** |
| 示范里的条数（3 / 2） | 本机是 **1** | ⚠ **M-1**（判据不影响） |

**结论：G3 现在是一个「判据明确、本机满足、退出码可记」的验收项 ✓**——这是上一轮
**解开了**的那一项（上一轮它必须问作者）。留下的只有两条与判据无关但会误导记录的
问题（M-1 / M-2）。

### 7.3 F1 / F2 / F3 / F4：材料里新给的那几条命令，照抄能不能跑出预期？

| 项 | 材料给的命令 | 照抄结果 | 结论 |
|---|---|---|---|
| **F1** | `analyze` → 0；`search … __no_such_term__` → 1；`analyze README.md` → 2 | **0 / 1 / 2**，输出与材料逐字一致（`No matches for '__no_such_term__'.` / `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives`） | ✓ **三条全中** |
| **F2** | `uvicorn … --port 8000` + 3 条 curl | 端口被占 → uvicorn 绑定失败，但 **curl 静默命中了另一个服务**；换端口后 `/health`、`/projects`、`/projects/{pid}`、`/runs`、`/search`、`/manifest`、`/source` 全部与契约表一致 | ⚠ **M-5** + **S-3** |
| **F3** | `uv run --no-sync dexatlas-mcp` | **没有任何输出**；工具清单要自己写 MCP 客户端才拿得到（拿到后：11 个工具、全部只读注解 ✓） | ✗ **S-1** |
| **F4** | `curl …/report?format=json` \| `python -c "…print(sorted(json.load(sys.stdin)))"` | `['errors','evidence','generated_at','latest_attempt_status','manifest','project','run','schema_version','summary','tools']`—— **正好 10 个**，与材料列的 10 个字段**逐字相同** | ✓ **完全符合** |

**结论：F1 与 F4 这两条新命令是「照抄就能跑出预期」的 ✓✓；F2 的命令能跑，但缺
端口退路、且抽查覆盖不到位（S-3 / M-5）；F3 的命令补上了，但**补错了东西**——
它能启动 server，不能列清单（S-1）。**

---

## 8. 这次预演跳过了什么、为什么

| 跳过的 | 理由 | 影响 |
|---|---|---|
| `git clone https://github.com/gg320324492-lgtm/dexatlas.git` | 本轮约束是不联网（只允许取已发布的 Release 正文）。改用**本地克隆** `E:/Dexatlas`，并确认 tag / commit 与 GitHub 上的 `v1.0.0` 一致（`git tag -l` 拿到 8 个 tag，`v1.0.0` → `2715aef`） | clone 来源 URL 这一栏的记录是本地路径，不是 GitHub URL；**A1 的「来源 URL」需按材料 §3.7 记一条脱敏说明** |
| `bash scripts/fetch-fixtures.sh` | 同上（本机 `gh` **已登录**，但网络在本轮范围外） | 测试套件里依赖第三方夹具的集成用例会 skip。**本轮跑的两个测试目标都不依赖它**（`tests/test_public_contracts.py` 31 passed、`verify-public-contracts.py` 48/48） |
| Docker 路线（准备包 §3.3 / 读者包 §3.2 路线 B） | 构建要拉基础镜像（网络）；本机 `docker images` 里**没有** dexatlas 镜像 | 路线 B 未走通。**路线 A 全通**，A2 的判据由路线 A 满足 |
| 「双击打开 `report.html`」（D1） | 无头环境 | 用**等价静态检查**代替：`<script>` 0、`<link>` 0、`<img>` 0、`src=`/`href=` 0、`http(s)://` 0、`url()` 0；复制到 `/tmp/d1-copy` 后重新扫描结果相同；HTML 解析器验证标签配对无未闭合、无错配 |
| 完整 pytest 全量套件 | 需要第三方夹具（同上） | 本轮只跑了材料点名的两个测试目标 |
| GitHub Release 正文 | **已取**（`releases/tags/v1.0.0`） | 正文 16225 字符、285 个真换行、**0 个字面 `\n`**、无格式损坏；含 `EXIT_NO_INDEX`；**不含** commit hash（合理——hash 由邀请函带） |

---

## 9. 与上一轮（针对 `3e943b5` 那一棵树）比：哪些修了，哪些没修

| 上一轮的问题 | 这一轮 | 说明 |
|---|---|---|
| **S-1** F1 没有产生退出码 1 的命令 | **已修 ✓** | §3.8 现在给了 0/1/2 三条命令，本机三条全中 |
| **S-2** F2/F3/F4 没有命令 | **半修** | F2/F4 的命令可用 ✓；**F3 的命令不产出要判的东西** → 本轮 S-1 |
| **M-1** G3 两份材料的预期互相矛盾，且本机满足不了准备包那一版 | **已修 ✓** | 准备包改成「至少一条 + 报告照常产出」，本机满足；见 §7.2 |
| **M-2** 超时运行的报告里同时挂着两条互斥的 `verified` 证据 | **材料已补说明，事实未变** | 本轮 G3 的 12 条里，E-0007 仍是 `verified` 的「jadx did not complete in this run…」（locator `jadx:error/timeout`），E-0008 仍是 `verified` 的「jadx produced real Java for 7 of 8 methods」（locator `jadx:sources`）——**两条 `verified` 并存**。读者包 §9.1 现在明说「会**多出一条** `verified` 的『后端未完成』记录」，读者不会再被条数吓到；但两条 `verified` 的张力本身没有被消解，也没有材料说它为什么可以并存 |
| **M-3** C 组被放在「源码评审记录」一节 | **已修 ✓** | 记录模板 §5 已写明「C 组（C1–C6）也是首次读者填的」，且这句**在 tag 树里**（`2715aef` 的模板第 113 行） |
| **M-4** 案例里「打包的 report.json 与散落的 report.json 逐字节相同」在 Windows 上不成立 | **已修 ✓** | 案例 §8 已改写成「散落的报告文件是**从包里拷出来**的那几份」，并明说 `analyze` 写的那几份带 CRLF、哈希只在产出机器上相同；附件自身的 sha256 与文中所写逐字相符（见 §2.4 的附注） |
| **M-5** G1 的 `projects` 预期与执行顺序冲突 | **未改 ✗** | 本轮 M-3，同一个问题 |
| **M-6** 邀请函 §二「v1.0.0 发版于 2026-11-17」与 tag 日期不一致 | **未核** | 本轮未核这条（tag 已重打，日期语义可能已变） |
| **M-7** §3.8 标注「可选但建议」与 ★ 阻断项冲突 | **未改 ✗** | 读者包 §3.8 标题仍是「契约与回归集抽查（验收项 E、F 组，**可选但建议**）」，而 F1、F5 是 ★ 阻断项 |
| **X-1** G3 的预期在两份材料里各写一遍 | **变本加厉** | 现在是**三处**（多了 M8 演练 §5），且三处不一致 → 本轮 X-1 |
| **X-2** 邀请函 §三与读者包 §2 各有一份「你需要准备什么」表；独立性守则也各写一遍 | **仍在** | 三张表仍在（邀请函 §三 / 读者包 §2 / 准备包 §3.1）；**本轮 X-2 记的是更尖的一处**：两份「读者路径」本身（准备包 §3 与读者包 §3）的**步骤清单**就不一致 |
| **X-3** 自查脚本读者不必跑 | **仍在，且多一处事实错误** | 邀请函 §五 那段现在还有一处**事实错误** → 本轮 M-4 |
| —— | **新增 ★ 级误读** | 邀请函 §四 的 locator 判法 → 本轮 M-6 |
| —— | **新增卡住** | tag 树里的 hash 占位符 → 本轮 S-2 |

---

## 10. 留给主会话的清单（按「影响 × 改动代价」排序）

> 以下每一项都**只记录**，本窗口**没有改任何既有文件**。

| # | 事项 | 类型 | 影响 | 代价 |
|---|---|---|---|---|
| 1 | **S-2** — 让记录模板 §1 / 读者包 §1.6 的 hash 指针在 tag 树里有着落（推荐改材料承认「树内是草稿，以邀请函正文为准 + `git rev-parse v1.0.0^{commit}` 核对」） | 卡住 | A1（★ 否，但 40 项的锚） | 2–4 行 |
| 2 | **M-6** — 邀请函 §四 第 4 步的 locator 判法改成准备包 C2 的口径 | 误读 | **C2 + C3（两条 ★）** | 1–2 行 |
| 3 | **M-2** — 给 M8 演练 §6 的 M8-4 加一句「已在 v1.0.0 由退出码 6 关闭」，或把 G3 的措辞改指契约表 §1.2 | 误读 | **G3（★）** | 1 行 |
| 4 | **S-1** — 给 F3 一条能照抄的命令（`dexatlas-mcp --list-tools`，或读者包里给 10 行 Python，或改判据） | 卡住 | F3（40 项里唯一必须问作者的一项） | 中（改代码）或小（改材料） |
| 5 | **M-1 / X-1** — 把读者包 §9.1 与 M8 演练 §5 的具体条数改成「示例」，并注明权威判据在准备包 §2.7 | 误读 + 多余 | G3（★）的记录准确性 | 3 行 |
| 6 | **M-4** — 邀请函 §五「与您要判的 40 项不是同一组东西」改成「**就是**您要判的这 40 项」 | 误读 | 读者对自查脚本的理解 | 1 行 |
| 7 | **M-3** — G1 的 `projects` 预期补上「在空工作区里」 | 误读 | G1 的假卡点 | 1 行 |
| 8 | **S-3** — §3.8 的 REST 命令补一句端口被占怎么办 | 卡住 | F2 的假卡点 | 1 行 |
| 9 | **M-5** — §3.8 的 REST 命令再补「运行」「源码」两个端点，覆盖 F2 点名的 6 个关键端点 | 误读 | F2 的抽查覆盖面 | 2 行 |
| 10 | **X-2** — 准备包 §3 与读者包 §3 的「你需要什么」与步骤清单对齐（`gh` CLI 行 + 夹具步骤） | 多余 | 读者拿到哪一份 | 中 |
| 11 | **M-7（上一轮未改）** — 读者包 §3.8 的「可选但建议」与 ★ 阻断项的口径统一 | 误读 | F1 / F5（★） | 1 行 |
| 12 | **上一轮 M-2 的遗留** — 超时运行的报告里两条 `verified`（E-0007「jadx did not complete」/ E-0008「jadx produced real Java」）并存；材料已说明条数会多一条，但没解释两条 `verified` 为何可以并存 | 遗留 | G3（★）的记录可信度 | 中（要动证据层的措辞或判据） |
| 13 | **新登记** — 把本文件登记进 `docs/reports/README.md` 与 `scripts/check-doc-citations.py` 的 `DOCS` 清单 | 分工 | 按分工留给主会话 | — |

---

## 11. 一句话结论

**上一轮那 12 条里，改掉了 4 条（S-1 / M-1 / M-3 / M-4）、补上了 1 条说明
（M-2）、仍有 4 条没动（M-5 / M-6 / M-7 / X-2 / X-3），这一轮又冒出 4 条**——
**最要紧的两条不是新发现的缺陷，而是「改了一半」的痕迹**：hash 填进了邀请函，
却没填进读者要 checkout 的那棵树（S-2）；G3 的判据改成了泛化表述，读者包里的
**示例数字**却没跟着改（M-1）。**F1 与 F4 这两条新命令是干净的**（照抄即中，
退出码 0/1/2 与 10 个顶层字段逐字命中），**F3 的新命令补错了东西**——它启动
server，不列清单（S-1）。**这一轮唯一一处会让人在 ★ 阻断项上误判的口径**，是
邀请函 §四 那句 locator「要能在证据包里解析到对应字节」（M-6）：demo 包里**没有
一条** locator 解析到字节，而那是**设计**。

---

## 附：这一轮跑过的全部命令（供复现）

```text
# §3.1 固定副本
git clone E:/Dexatlas <dest>            # 离线，替代 GitHub URL
git tag -l ; git checkout v1.0.0 ; git status --porcelain
git rev-parse HEAD ; git rev-parse v1.0.0 ; git cat-file -t v1.0.0
git rev-parse "v1.0.0^{commit}" ; git diff --stat 2715aef HEAD -- docs/

# §3.2 环境
uv sync --extra dev --extra analysis --extra mcp --extra demo
uv run dexatlas backends

# §3.3–§3.4 首次分析与检索
uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas manifest|search|source|classes|methods apk_80a8fe0e81204c9f …
uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.MainActivity.describe(…)Ljava/lang/String;"

# §3.5–§3.6 报告与证据包
uv run dexatlas analyze … -o report.md --json report.json --html report.html
uv run dexatlas export apk_80a8fe0e81204c9f -o evidence.zip
python -m zipfile -l evidence.zip ; python -m zipfile -e evidence.zip evidence
uv run --no-sync python -c "from pathlib import Path; from dexatlas.reports.evidence_package import verify_package, verify_citations; …"
certutil -hashfile evidence/reports/report.md SHA256   # 与 report.json 各一次

# §3.8 契约
uv run --no-sync pytest tests/test_public_contracts.py -q
uv run --no-sync python scripts/verify-public-contracts.py
uv run --no-sync python scripts/check-contract-records.py --expect with-jadx     # → 0
uv run --no-sync python scripts/check-contract-records.py --expect without-jadx  # → 2
uv run --no-sync uvicorn dexatlas.api.app:app --port 8000   # → 端口被占
uv run --no-sync uvicorn dexatlas.api.app:app --port 8011   # 改端口
curl -s localhost:8011/{health,projects} ; curl -s "…/projects/{pid}" ;
curl -s "…/projects/{pid}/runs" ; curl -s "…/projects/{pid}/search?q=Crypto" ;
curl -s "…/projects/{pid}/manifest" ; curl -s -D - -o /dev/null "…/source"
curl -s "…/projects/{pid}/report?format=json" | python -c "import json,sys; print(sorted(json.load(sys.stdin)))"
uv run --no-sync dexatlas-mcp            # 无输出

# §9.1 G 组
DEXATLAS_WORKSPACE=/tmp/g1-fresh uv run dexatlas analyze README.md   # → 2
DEXATLAS_WORKSPACE=/tmp/g1-fresh uv run dexatlas projects            # → 空
DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR= uv run dexatlas analyze examples/demo-app/demo.apk
DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas analyze examples/demo-app/demo.apk   # ×2（G4）
uv run dexatlas projects

# §7 自查脚本与 Release
uv run --no-sync python scripts/m10_selfcheck.py
curl -s https://api.github.com/repos/gg320324492-lgtm/dexatlas/releases/tags/v1.0.0
```
