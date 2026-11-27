# 公共契约表

本文是 DexAtlas 对外承诺的清单：CLI 退出码、REST 端点、MCP 工具、计数的含义、
报告 schema 与版本政策。每一条都标注了它由哪段代码实现（`file:line`），并有一列
记录它在真实接口上被验证的方式。契约快照测试在 `tests/test_public_contracts.py`，
它把端点清单、工具清单和退出码表固化成断言——契约变了，测试先红。

约定：本表描述的是**当前**契约。历史拼写（如 `reference_count` 的旧名）只在
"兼容别名"一节出现。表中的行号由 `scripts/remap-citations.py` 维护，由
`scripts/check-doc-citations.py` 校验；改动 `src/` 后先重映射再核对。

## 1. CLI

CLI 是 Typer 应用（`src/dexatlas/cli/main.py:75-76` `anchor: app = typer.Typer(`）。全部命令委托
`Analyzer`（`src/dexatlas/core/pipeline.py`），CLI 自身不做分析。全局选项：
`--log-level`、`--verbose/-v`（`src/dexatlas/cli/main.py:274-285` `anchor: _root`）。

### 1.1 子命令

| 命令 | 用途 | 关键选项 | 实现 |
|---|---|---|---|
| `dexatlas version` | 打印版本 | | `src/dexatlas/cli/main.py:295-297` `anchor: version` |
| `dexatlas backends` | 列出后端与版本 | | `src/dexatlas/cli/main.py:295-318` `anchor: backends` |
| `dexatlas analyze <apk>` | 分析 APK 并出报告 | `-o/--output`（Markdown）、`--json`、`--html`、`--workspace` | `src/dexatlas/cli/main.py:322-422` `anchor: analyze` |
| `dexatlas projects` | 列出项目 | | `src/dexatlas/cli/main.py:426-450` `anchor: projects` |
| `dexatlas classes <pid>` | 列出类 | `--prefix`、`--limit`（≥1，无上限）、`--provenance-limit`（≥0）、`--all` | `src/dexatlas/cli/main.py:454-509` `anchor: classes` |
| `dexatlas methods <pid>` | 列出方法 | `--class`、`--limit` | `src/dexatlas/cli/main.py:513-560` `anchor: methods` |
| `dexatlas source <pid> <cls>` | 打印类/方法源码 | `--method`、`--descriptor`、`--format text\|json` | `src/dexatlas/cli/main.py:564-663` `anchor: source` |
| `dexatlas resources <pid>` | 资源字符串 | `--name`、`--limit` | `src/dexatlas/cli/main.py:692-744` `anchor: resources` |
| `dexatlas resrefs <pid>` | 资源引用 | `--type`、`--name`、`--limit` | `src/dexatlas/cli/main.py:748-808` `anchor: resrefs` |
| `dexatlas search <pid> <kw>` | 全文搜索 | `--limit` | `src/dexatlas/cli/main.py:812-851` `anchor: search` |
| `dexatlas export <pid>` | 证据包（.zip） | `-o/--output`（必填） | `src/dexatlas/cli/main.py:855-899` `anchor: export` |
| `dexatlas manifest <pid>` | 解析后的 manifest | | `src/dexatlas/cli/main.py:903-931` `anchor: manifest` |
| `dexatlas xrefs <pid> <mid>` | 方法调用者 | | `src/dexatlas/cli/main.py:935-964` `anchor: xrefs` |
| `dexatlas runs <pid>` | 列出该项目的运行历史；`--run <rid>` 打印某一次运行自己的记录（工具版本、起止、时长、是否已发布、错误记录原样取回） | `--run`、`--limit`（≥1） | `src/dexatlas/cli/main.py:968-1044` `anchor: runs` |
| `dexatlas render <pid> <rid>` | 把某一次**已完成且仍是已发布**的运行渲染成可复核目录：该次快照的三格式报告、`evidence/evidence-package.zip`（与 `export` 同一选择与守卫，写入后当场 `verify_package`/`verify_citations`）、run 记录 `run.json`。只读，不重新分析 | `-o/--output`（必填，目录须为空或不存在） | `src/dexatlas/cli/main.py:1047-1110` `anchor: render` |

`runs` / `render` 的退出码（C8，2026-11-20 新增，向后兼容）：run id 或项目不存在、
run 未发布/已取消/失败（无可渲染快照）、run 的快照已被新分析替换、输出目录非空 →
`2`（`EXIT_BAD_REQUEST`）；项目没有运行历史 → `1`（`EXIT_EMPTY`）；渲染自身失败 →
`3`（`EXIT_FAILED`）。没有新造退出码语义。`render` 的边界与 `export` 同界——都渲染
**published run**；被替换的旧 run 记录仍可经 `runs --run` 读回。

`source` 的文本格式把"这是 Java 还是 Smali、来自哪个文件"打到 stderr
（`src/dexatlas/cli/main.py:564-572`），stdout 只承载源码本身；`--format json`
把同一信息放进文档。方法名命中多个重载时列出候选并要求 `--descriptor`
（`src/dexatlas/cli/main.py:601-602` `anchor: --descriptor`）。

### 1.2 退出码

退出码常量与语义（`src/dexatlas/cli/main.py:93-135` `anchor: EXIT_BAD_REQUEST`，epilog 同步声明于
`src/dexatlas/cli/main.py:72-81` `anchor: epilog=(`）：

| 码 | 常量 | 语义 | 触发点（示例） |
|---|---|---|---|
| 0 | — | 成功完成 | `analyze` 无截断且索引可用（`src/dexatlas/cli/main.py`，`analyze` 成功分支） |
| 1 | `EXIT_EMPTY` | 请求正确但答案为空：无匹配类/方法/调用者/资源/源码；或分析产出零符号（项目 `failed`） | `classes` 无匹配、`analyze` 零符号（`src/dexatlas/cli/main.py`） |
| 2 | `EXIT_BAD_REQUEST` | 请求本身错误：项目不存在、输入不是 APK、描述符不合法、无已发布 run | `_require_project`、`ApkValidationError`、`export` 无发布 run（`src/dexatlas/cli/main.py`） |
| 3 | `EXIT_FAILED` | 分析本身失败（步骤抛错、工作区不可写） | `AnalysisFailed`、`export` 构建失败（`src/dexatlas/cli/main.py`） |
| 4 | `EXIT_AMBIGUOUS` | 请求正确但答案有歧义：方法名命中多个重载 | `AmbiguousMethodError`（`src/dexatlas/cli/main.py`） |
| 5 | `EXIT_TRUNCATED` | 分析跑完，但有步骤被上限截断，报告带缺口 | `_truncated` 判定（`src/dexatlas/cli/main.py`） |
| 6 | `EXIT_NO_INDEX` | 分析跑完，但无可用的代码索引：所有读取 DEX 的后端全部失败，索引为空（manifest 仍可读） | `_no_index` 判定（`src/dexatlas/cli/main.py`） |

判据：截断 = 项目 errors 里存在 `output_truncated`（`ToolErrorCode.OUTPUT_TRUNCATED`，
`src/dexatlas/core/models.py:42`）；无索引 = 项目 `completed` 且 `class_count == 0`
且存在索引缺口（`index_gaps` 非空，`src/dexatlas/core/models.py:94`，即 androguard
失败或分析失败——与报告 `summary.index_complete == false` 同源）。无 DEX 的资源型
APK（索引为空但无缺口）不触发 6，仍为 0；部分后端失败（索引仍在）不触发 6，仍为 0。
no-index 判定先于截断：空索引是更强的信号。三个"空"彼此不同：请求错（2）、答案空
（1）、运行失败（3），调用方只读退出码也能区分（`src/dexatlas/cli/main.py:7-30` `anchor: EXIT_AMBIGUOUS`）。

退出码 6 由提案 [docs/proposals/exit-code-partial-read.md](../proposals/exit-code-partial-read.md)
批准实施（方案 A），按 §6 作为兼容变更显式版本化：0–5 语义不变，0 的外延收窄——
原先错误地落在 0 的「跑完了但无可用的代码索引」运行改落 6。

## 2. REST API

FastAPI 应用 `app`（`src/dexatlas/api/app.py:155-164`），标题 DexAtlas，携带版本与
Apache-2.0 许可信息。上传体积上限由中间件强制：`UploadSizeLimitMiddleware`，上限
`ingest.MAX_APK_BYTES = 256 MiB`（`src/dexatlas/api/app.py:167` `anchor: UploadSizeLimitMiddleware`、
`src/dexatlas/core/ingest.py:41` `anchor: MAX_APK_BYTES`），超限返回 413
（`src/dexatlas/api/uploads.py:57` `anchor: HTTP_CONTENT_TOO_LARGE`）。

### 2.1 元信息

| 端点 | 方法 | 响应 | 说明 |
|---|---|---|---|
| `/health` | GET | `{"status":"ok","version":str,"backends":{name: version\|null}}` | 存活探针 + 后端可用性；null = 未安装（`src/dexatlas/api/app.py:359-365` `anchor: health`） |
| `/backends` | GET | `{"available":[str],"missing":[str],"versions":{}}` | 部署可用的后端（`src/dexatlas/api/app.py:369-375` `anchor: list_backends`） |

### 2.2 分析

| 端点 | 方法 | 请求 | 响应 | 状态码 |
|---|---|---|---|---|
| `/analyze` | POST | multipart 字段 `file`（APK） | `AnalyzeJobResponse{project_id,status,detail}` | 202；同哈希且非 failed 的项目已存在时直接返回既有项目（`src/dexatlas/api/app.py:365-399` `anchor: analyze`） |
| `/projects/{pid}/cancel` | POST | — | `{"project_id","status":"cancelling"}` | 202；无运行中分析则 404（`src/dexatlas/api/app.py:507-520` `anchor: cancel_analysis`） |

分析是后台任务（`run_background_analysis`，`src/dexatlas/api/uploads.py`）。
`/analyze` 的幂等语义：同字节重复上传返回已有项目，不重复分析；failed 项目
重新上传会重试（`src/dexatlas/api/app.py:399` `anchor: ProjectStatus.FAILED`）。

### 2.3 项目与运行

| 端点 | 方法 | 响应 | 状态码 |
|---|---|---|---|
| `/projects` | GET | `ProjectResponse[]`，最新在前 | 200（`src/dexatlas/api/app.py:422-424` `anchor: list_projects`） |
| `/projects/{pid}` | GET | `ProjectResponse` | 200 / 404（`src/dexatlas/api/app.py:188-194`） |
| `/projects/{pid}/runs` | GET | `{"project_id","total","published_run_id","runs":[RunResponse]}`，最新在前 | 200（`src/dexatlas/api/app.py:437-455` `anchor: list_runs`） |
| `/projects/{pid}/runs/{rid}` | GET | `RunResponse` | 200 / 404（`src/dexatlas/api/app.py:248-270` `anchor: RunResponse`） |
| `/projects/{pid}/runs/{rid}/stages` | GET | `{"project_id","run_id","run_status","stages":[{stage,started_at,finished_at}]}` | 200 / 404（`src/dexatlas/api/app.py:471-499` `anchor: get_run_stages`） |
| `/projects/{pid}` | DELETE | — | 204 / 404（`src/dexatlas/api/app.py:870-874` `anchor: delete_project`） |

`ProjectResponse` 字段见 `src/dexatlas/api/app.py:188-220` `anchor: ProjectResponse`：`id`、`status`、
`apk_sha256`、`apk_path`（文件名，不含目录——目录布局不发布）、`apk_size_bytes`、
`class_count`、`method_count`、`reference_count`（= 调用点数）、`call_site_count`
（同 `reference_count` 的别名，见 §4）、`call_edge_count`、`evidence_count`、
`resource_count`、`tool_versions`、`errors[]`。其中 `tool_versions` 在
`src/dexatlas/api/app.py:219`；`errors[]` 的元素是 `ErrorResponse{tool,code,message,detail}`，
该模型定义于 `src/dexatlas/api/app.py:181-185` `anchor: ErrorResponse`。
行模型见 `ClassRef`
（`src/dexatlas/core/models.py:243`）、`MethodRef`（`src/dexatlas/core/models.py:279`）、
`FieldRef`（`src/dexatlas/core/models.py:318`）、`CallSite`
（`src/dexatlas/core/calls.py:45`）、`StringConstant`（`src/dexatlas/core/models.py:393`）、
`ResourceString`（`src/dexatlas/core/models.py:865`）、`ResourceReference`
（`src/dexatlas/core/models.py:942`）；manifest 文档是 `ManifestInfo`
（`src/dexatlas/core/models.py:472`）。

`RunResponse` 字段（`src/dexatlas/api/app.py:229-251`）：`id`、`project_id`、
`status`、`completeness`（"complete"/"partial"）、`apk_sha256`、`tool_versions`、
`errors[]`、`started_at`、`finished_at`、`duration_seconds`、`published`。

**stages 端点（2026-11-25 新增，纯新增端点）**：`GET /projects/{pid}/runs/{rid}/stages`
回答"这个 run 走到了哪一步"，响应是
`{"project_id","run_id","run_status","stages":[{stage,started_at,finished_at}]}`，
阶段事件按记录顺序排列。每个元素的形状是 `{stage, started_at, finished_at}`
（模型见 `RunStageEventResponse`，`src/dexatlas/api/app.py:229-245`
`anchor: RunStageEventResponse`）。stage 取值 inspect、parse-apktool、
index-androguard、decompile-jadx、publish（与 `Analyzer.analyze` 的实际推进点一致，
`src/dexatlas/core/pipeline.py:152`；阶段枚举见 `src/dexatlas/core/runs.py:75`
`anchor: RunStage`）。`started_at` 与 `finished_at` 是 ISO 8601 时间戳，
`finished_at` 为 null 表示该阶段尚未结束——包括 run 在阶段中途失败或被取消的情况。
同一阶段至多出现一次；旧版本写入的 run 或在首个阶段前就结束的 run，阶段列表是
空数组（读作"无阶段事实"，不是错误）。

**run 对象本身不带 stages**：`RunResponse` 仍是上表的 11 个字段，阶段事实另取
stages 端点——这样既有 run 对象的字段集一个也不变。workbench 的
`GET /api/projects/{pid}/runs/{rid}/stages` 与 REST 同形状
（`src/dexatlas/workbench/app.py:603-616` `anchor: get_run_stages`）；MCP 面的形状经
`src/dexatlas/mcp/tools/projects.py:74-92` `anchor: def run_stages` 与
`src/dexatlas/mcp/schemas.py:155-170` 的 `RunStages` 定义。端点与字段
只增不改：既有端点的响应形状、状态码与退出码零变化。

### 2.4 符号与检索

| 端点 | 方法 | 查询参数 | 响应 | 状态码 |
|---|---|---|---|---|
| `/projects/{pid}/manifest` | GET | — | manifest 文档（`ManifestInfo.model_dump`） | 200 / 404（无 manifest，如 Apktool 未装；`src/dexatlas/api/app.py:596-604` `anchor: get_manifest`） |
| `/projects/{pid}/classes` | GET | `prefix`、`limit`(1..1000,默认200) | `{"project_id","total","classes":[ClassRef]}` | 200（`src/dexatlas/api/app.py:609-623`） |
| `/projects/{pid}/methods` | GET | `class`、`limit`(1..1000,默认200) | `{"project_id","total","methods":[MethodRef]}` | 200（`src/dexatlas/api/app.py:625-639`） |
| `/projects/{pid}/resources` | GET | `name`、`limit`(1..1000,默认200) | `{"project_id","total","resources":[ResourceString]}` | 200（`src/dexatlas/api/app.py:641-658`） |
| `/projects/{pid}/resource-references` | GET | `res_type`、`res_name`、`limit` | `{"project_id","total","references":[ResourceReference]}` | 200（`src/dexatlas/api/app.py:609-634`） |
| `/projects/{pid}/xrefs/{method_id:path}` | GET | — | `{"project_id","method_id","call_sites","call_edges","total","total_unit":"call_sites","references":[CallSite]}` | 200（`src/dexatlas/api/app.py:808-831` `anchor: get_references`） |
| `/projects/{pid}/search` | GET | `q`(必填)、`limit`(1..200,默认50) | `{"project_id","query","results":[…]}` | 200（`src/dexatlas/api/app.py:837-846`） |
| `/projects/{pid}/evidence` | GET | — | `{"project_id","total","evidence":[Evidence]}` | 200（`src/dexatlas/api/app.py:846-853` `anchor: list_evidence`） |

`xrefs` 的 `method_id` 回显规范化拼写（`canonical_method_id`）；`total` 的单位是
调用点，由 `total_unit: "call_sites"` 明示，`call_edges` 单独给出
（`src/dexatlas/api/app.py:823-839`）。

### 2.5 源码

| 端点 | 方法 | 参数 | 响应 | 状态码 |
|---|---|---|---|---|
| `/projects/{pid}/classes/{class_name:path}/source` | GET | `format=text\|json`（默认 text） | text：源码正文 + `X-DexAtlas-Source-*` 头；json：含 provenance 的文档 | 200 / 404（`src/dexatlas/api/app.py:692-711` `anchor: get_class_source`） |
| `/projects/{pid}/methods/{class_name:path}/{method_name}` | GET | `format`、`descriptor` | 同上 | 200 / 404 / 409（重载歧义，返回候选；`src/dexatlas/api/app.py:754-804` `anchor: get_method_source`）/ 400（descriptor 不合法，`src/dexatlas/api/app.py:774-777` `anchor: A name that matches more than one overload is answered with`） |

溯源响应头（`_SOURCE_HEADERS`，`src/dexatlas/api/app.py:288-306`）：

| 头 | 含义 |
|---|---|
| `X-DexAtlas-Source-Kind` | `java` 或 `smali` |
| `X-DexAtlas-Source-Tool` | 产生源码的后端 |
| `X-DexAtlas-Source-Locator` | 源码在该后端输出树中的位置 |
| `X-DexAtlas-Source-Tool-Version` | 该后端的版本 |

JSON 形状（`_SOURCE_JSON_SCHEMA`，`src/dexatlas/api/app.py:308-332`）：
`{project_id, class_name, method?, descriptor?, kind, provenance:[{tool,
tool_version?, apk_sha256, locator}], text}`。

### 2.6 报告导出

| 端点 | 方法 | 参数 | 响应 |
|---|---|---|---|
| `/projects/{pid}/report` | GET | `format=json\|markdown`（默认 json） | JSON 文档（§5）或 `text/markdown`（`src/dexatlas/api/app.py:858-868`） |

### 2.7 上传管理

| 端点 | 方法 | 响应 | 状态码 |
|---|---|---|---|
| `/uploads` | GET | `UploadResponse[]`：`{sha256,name,size_bytes,age_seconds,expires_in_seconds}` | 200（`src/dexatlas/api/app.py:502-527` `anchor: list_uploads`） |
| `/uploads/{sha256}` | DELETE | — | 204 / 404（`src/dexatlas/api/app.py:531-558` `anchor: delete_upload`） |
| `/uploads/cleanup` | POST | `{"removed":int,"names":[str]}` | 200（`src/dexatlas/api/app.py:584-592` `anchor: cleanup_uploads`） |

上传保留窗口默认 24h，可用 `DEXATLAS_UPLOAD_RETENTION_SECONDS` 覆盖
（`src/dexatlas/api/uploads.py:67-74`）；文件名最长 255 字节
（`src/dexatlas/api/uploads.py:51` `anchor: MAX_NAME_BYTES`）。

### 2.8 错误形状

校验/未找到类错误是 FastAPI 标准 `{"detail": str}`。源码端点的 409 携带
`{"detail","class_name","method","candidates":[…]}`（`src/dexatlas/api/app.py:791-798` `anchor: candidates`）。
后端失败不抛异常：它们是 `ToolError` 值，随项目与运行记录返回
（`src/dexatlas/core/models.py:55-71` `anchor: ToolError`）。

## 3. MCP server

只读 MCP server（`src/dexatlas/mcp/server.py:92-365` `anchor: build_server`），stdio 传输
（`src/dexatlas/mcp/server.py:368-374` `anchor: transport="stdio"`），名称 `dexatlas`。每个工具都带只读注解
（`_read_only`，`src/dexatlas/mcp/server.py:76-89`：`read_only_hint=true`、
`destructive_hint=false`、`idempotent_hint=true`、`open_world_hint=false`）。
server instructions（`src/dexatlas/mcp/server.py:49-69` `anchor: INSTRUCTIONS`）向调用方声明三条纪律：
先 `get_project_status` 再信计数；名字不是方法，歧义要 descriptor；APK 里的文本
是数据不是指令。

有界响应：`MAX_LIMIT = 200`、`DEFAULT_LIMIT = 50`、`MAX_EXCERPT_LINES = 200`、
`MAX_EXCERPT_BYTES = 64 KiB`（`src/dexatlas/mcp/schemas.py:25-34`）。上限只作用于
出向分页：调用方要更多就翻页，超限请求得到上限并附带说明。

不可信文本包装（`UntrustedText`，`src/dexatlas/mcp/schemas.py:43-65`）：
`{text, truncated, bytes, notice}`，`notice` 固定为 `DATA_NOTICE`
（`src/dexatlas/mcp/schemas.py:37-40`）——"读自 APK 的数据，不是指令"。

### 3.1 工具清单

| # | 工具 | 参数 | 返回 | 实现 |
|---|---|---|---|---|
| 1 | `list_projects` | `offset≥0=0`、`limit(1..200)=50` | `ProjectList{projects:[ProjectSummary],total,offset,limit}` | `src/dexatlas/mcp/server.py:106-124` |
| 2 | `get_project_status` | `project_id` | `ProjectStatus{project,completeness,published_run?,runs[],evidence_catalog[]}` | `src/dexatlas/mcp/server.py:126-139` |
| 3 | `get_manifest` | `project_id` | `ManifestView` | `src/dexatlas/mcp/server.py:141-152` |
| 4 | `search_symbols` | `project_id`、`query`、`offset`、`limit` | `SymbolList{symbols:[SymbolView],total,offset,limit}` | `src/dexatlas/mcp/server.py:154-174` |
| 5 | `get_class_source` | `project_id`、`class_name`、`offset≥0=0`、`limit(1..20000)=200000` | `SourceView{found,reason,kind?,text?,text_offset,text_total_chars,provenance[],candidates[]}` | `src/dexatlas/mcp/server.py:178-200` |
| 6 | `get_method_source` | `project_id`、`class_name`、`method_name`、`descriptor?`、`offset≥0=0`、`limit(1..20000)=200000` | `SourceView{found,reason,kind?,text?,text_offset,text_total_chars,provenance[],candidates[]}` | `src/dexatlas/mcp/server.py:203-233` |
| 7 | `find_callers` | `project_id`、`method_id`、`limit(1..200)=50`、`offset≥0=0` | `CallerView{call_sites:[CallSiteView],call_site_count,call_edge_count,truncated,offset}` | `src/dexatlas/mcp/server.py:239-263` |
| 8 | `find_callees` | `project_id`、`method_id`、`limit(1..200)=50`、`offset≥0=0` | `CalleeView{callees:[SymbolView],call_site_count,call_edge_count,truncated,offset}` | `src/dexatlas/mcp/server.py:265-290` |
| 9 | `get_evidence` | `project_id`、`evidence_id` | `EvidenceView{id,kind,level,summary,detail,provenance[]}` | `src/dexatlas/mcp/server.py:302-312` |
| 10 | `resolve_locator` | `project_id`、`locator` | `LocatorResolution{resolved,reason,kind?,text?,provenance[]}` | `src/dexatlas/mcp/server.py:315-330` |
| 11 | `find_resource_declarations` | `project_id`、`name?`、`value?`、`offset`、`limit` | `ResourceDeclarationList{declarations:[ResourceDeclarationView],total,offset,limit}` | `src/dexatlas/mcp/server.py:322-357` |

**阶段工具为什么不在 MCP 面上（作者决定，2026-11-27）：** Phase 5 W2 加了阶段级
进度契约——`GET /projects/{pid}/runs/{rid}/stages` 返回 run 的五个推进点与它们的
时间戳。它**没有**被注册成 MCP 工具，工具清单仍是上面 11 个。

这是**有意的取舍，不是遗漏**。理由：MCP 面是给 agent 用的，agent 要的是「这个
APK 里有什么」；阶段进度是**这一次分析进行到哪了**——一个正在跑的 run 的阶段，
对 agent 查证据没有帮助，而 run 一旦结束，阶段事实就是「全部完成」，agent 从
`get_project_status` 的 `runs[]` 里已经能看到结论。阶段事实的用处在于**给人看**
（桌面应用的分析页），那两个传输面已经给了。

所以阶段事实走 REST 与 workbench 两处，MCP 面不暴露。这条取舍写在这里，
是为了下次有人问「为什么 MCP 没有阶段工具」时有答案可查，而不是只能看到
一个「没有」。

> 注：5/6 两个工具的 `limit` 默认值（200000）大于其校验上界（20000）是**现有实现的事实**，
> 不是文档笔误——pydantic 不校验 default，所以省略 `limit` 时按 200000 生效；显式传
> 20001–200000 会被拒（`src/dexatlas/mcp/server.py:198-201, 236-239`，上界来自
> `MAX_LIMIT * 100`，`src/dexatlas/mcp/schemas.py:25` 的 `MAX_LIMIT`）。本表按实现如实记录；
> 让默认值与上界自洽属于冻结期之外的行为变更，这里不改代码。

### 3.2 响应形状与"有界、说清"语义

`SourceView`（`src/dexatlas/mcp/schemas.py:327-360`）用 `found: bool` 区分"分析
查过但没有"（`found=false` + `reason`）与"分析没跑过"；歧义名在 `candidates`
里列 descriptor。`text_offset`/`text_total_chars` 说明本页在整篇源码中的位置
（`offset=0`、`limit=200000` 时整篇返回）；agent transcript 对超过 4000 字符
的文本字段裁剪，裁剪提示指向分页（同工具 `offset=` 续读），不再宣称全文
已录为 evidence。`Completeness`（`src/dexatlas/mcp/schemas.py:68-90`）携带
`complete`、`missing_backends[]`、`truncated`、`errors[]`——"没找到"与"没查"
分开。错误以 `RequestError` 抛出，形状 `{code,message,detail}`
（`src/dexatlas/mcp/errors.py:14-31` `anchor: RequestError`），已知码：`unknown_project`
（`src/dexatlas/mcp/errors.py:32-38`）、`unknown_method`
（`src/dexatlas/mcp/errors.py:41-47`）、`no_manifest`
（`src/dexatlas/mcp/errors.py:50` 起）。

## 4. 计数含义

`SymbolCounts`（`src/dexatlas/core/storage.py:81-124`）与 `Project`
（`src/dexatlas/core/models.py:755-798`）：

| 字段 | 含义 | 折叠/去重 |
|---|---|---|
| `classes` / `class_count` | 类表行数 | 同一键去重（两个 dex 定义的同一类是一行） |
| `methods` / `method_count` | 方法表行数 | 同上 |
| `fields` | 字段表行数 | 同上 |
| `call_sites` / `reference_count` | 调用点数：字节码里每一处调用一行 | 不折叠；同一方法两次调用同一目标是两个点 |
| `call_edges` / `call_edge_count` | 调用边数：两个方法之间的关系，按调用点聚合 | 一方法两次调用同一目标 = 2 点 1 边 |
| `evidence_count` | 证据记录数 | |
| `resources` / `resource_count` | 资源表行数（资源字符串） | |
| `resource_references` | 资源引用边数（`@type/name` 的每一处使用） | |

两个传输与三种报告对"点/边"使用同一组数：`call_site_count` 是
`reference_count` 的别名（`src/dexatlas/api/app.py:205-211`、
`src/dexatlas/mcp/tools/projects.py:53`）。`xrefs` 响应用 `total_unit:
"call_sites"` 把单位写死（`src/dexatlas/api/app.py:775-779`）。

证据三级（`EvidenceLevel`，`src/dexatlas/core/models.py:537-571`）：

| 级别 | 判定边界 |
|---|---|
| `verified` | 确定性工具产出，且代码类发现必须带能在分析内解析的 provenance（`EvidenceBuilder` 拒绝引不到的 verified，`src/dexatlas/core/models.py:542-546`） |
| `lead` | 模型/启发式给出的怀疑指示，不是确认；只能经 `add_claim` 写入 |
| `insufficient` | 双方证据都不足，需人工复核 |

硬边界：`BEHAVIOUR` 类记录永不能是 `verified`（`src/dexatlas/core/models.py:583-590`）；
模型生成的 claim 永不能是 `verified`（`src/dexatlas/core/models.py:543-553`）。
分析本身不产生 `lead`/`insufficient`，报告里 `lead 0` 是"分析没在此级落任何结论"，
不是"APK 无可疑"（`src/dexatlas/core/models.py:555-561` `anchor: add_claim`）。

## 5. 报告 schema

### 5.1 JSON 报告顶层字段

`build_json_report`（`src/dexatlas/reports/json_report.py:21-44`）：

| 字段 | 含义 |
|---|---|
| `schema_version` | 当前 `3`（`src/dexatlas/reports/json_report.py:32`） |
| `generated_at` | UTC ISO 时间戳 |
| `project` | 项目块：`id`、`apk{sha256,size_bytes,path,dex_files,native_libraries,has_signed_certificate}`、`status`、`created_at`、六个计数（`src/dexatlas/reports/json_report.py:68-96`） |
| `run` | 本次 run：`id,status,completeness,apk_sha256,tool_versions,started_at,finished_at,duration_seconds`；无 run 记录的旧工作区为 `null`（`src/dexatlas/reports/json_report.py:47-65` 的 `_run_block`） |
| `latest_attempt_status` | 更晚一次尝试的状态或 `null` |
| `tools` | `tool_versions` |
| `errors` | `ToolError[]` |
| `manifest` | manifest 文档或 `null` |
| `evidence` | `Evidence[]` |
| `summary` | 指标块（下表） |

`summary` 块（`src/dexatlas/reports/json_report.py:43-89`）：`classes`、`methods`、
`call_sites`、`call_edges`、`call_sites_with_evidence`、`call_edges_with_evidence`、
`cross_references`（= `call_sites` 的兼容名）、`resource_strings`、
`cross_references_with_evidence`、`cross_reference_records`、`evidence_by_level`
（`{verified,lead,insufficient}` 计数）、`decompilation`、`index_complete`、
`index_gaps[{tool,code,message}]`、`duration_seconds`、`backends_with_errors`。

### 5.2 三格式共享数据层

Markdown、JSON、HTML 由同一组指标渲染：`reports/summary.py` 的
`summary_metrics`（`src/dexatlas/reports/summary.py:47`）是唯一事实来源，任何
格式都不自行计算数字（`src/dexatlas/reports/summary.py:1-8` `anchor: assembled here, once, from the analysis model`）。承诺：三个格式里
同一个名字是同一个数。

### 5.3 证据包 manifest

`build_evidence_package`（`src/dexatlas/reports/evidence_package.py:111-155`），
`schema_version = 2`（`PACKAGE_SCHEMA_VERSION`，
`src/dexatlas/reports/evidence_package.py:54`）。字段（
`not_included` 写入清单的位置
`src/dexatlas/reports/evidence_package.py:187` `anchor: "not_included": NOT_INCLUDED`；
`NOT_INCLUDED` 常量定义在
`src/dexatlas/reports/evidence_package.py:86-96` `anchor: NOT_INCLUDED = {`）：

```text
schema_version: 2
project_id: str
apk_sha256: str
run_id: str | null
package_generated_at: ISO-8601
tool_versions: {name: version | null}
files: [{path, sha256, bytes, role}]        # role ∈ report | evidence_source | evidence
not_included: {apk, full_sources, unrelated_strings, outside_analysis}
```

包内路径固定：`reports/report.{json,md,html}`、`sources/<相对路径>`、
`manifest.json`（`src/dexatlas/reports/evidence_package.py:53-73`）。定位符一律是
`<tool>:<包内相对位置>`，绝无机器绝对路径
（`src/dexatlas/reports/evidence_package.py:22-24` `anchor: Every locator travels as`）。

包内只有本次分析。被引用的源码片段必须**是分析自己的反编译产物**：文件在
反编译树之内（链接已解析），且位于反编译器写的两棵树之一（`sources/` 或
`resources/`）。不满足的文件不进包；引用仍留在证据里，并由
`verify_citations` 记为未解析，而不是被当作已经带在包里。清单的第四个
`not_included` 键（`outside_analysis`）把这条边界**声明**出来——读者打开
清单就能看到「包里只有本次分析的文件」，而不必去读打包器的实现。

`dexatlas export` 的成功消息打印的是**归档里的文件数**，不是清单列出的
数：清单列的是归档里除清单以外的文件，加上清单自己才是归档的全部条目。
消息同时说清这个数由什么组成（`3 reports + 1 manifest`；被证据引用的源码
片段另计 `N source fragments`），读者打开 zip 数一次就能对上包里有多少
文件。清单的形状在 v1.1.0 升为 `schema_version = 2`：新增
`not_included.outside_analysis` 一个键，其余字段不变（变更记录见 CHANGELOG）。

## 6. 版本政策

- 版本号唯一来源是 `src/dexatlas/__init__.py:11` 的 `__version__`
（当前 `1.1.0`，v1.1.0 已发布）；打包经 hatch 从该文件读取（`pyproject.toml:145-146` `anchor: [tool.hatch.version]`）。
- 遵循 Semantic Versioning（`CHANGELOG.md:5-6` `anchor: project adheres to [Semantic Versioning]`）；变更记录在 CHANGELOG 的
  `[Unreleased]` 节，分类 Added/Changed/Fixed（发版时该节并入该版本的段）。
- 公共契约（本文所列）的变更规则：
  - **加字段、加端点、加工具、加退出码**是兼容变更：在 CHANGELOG 里说明即可。
    JSON 报告从 v1→v2→v3 都是纯增量，读旧文档的调用方忽略未知键不受影响
    （`src/dexatlas/reports/json_report.py:29-32` `anchor: Both are additive`）。
  - **改字段含义、删字段、改状态码/退出码语义、改响应形状**是破坏性变更：必须
    升 `schema_version` 或大版本，并在 CHANGELOG 显式声明，不得悄悄变更。
  - 兼容别名（如 `reference_count`/`call_site_count`、`cross_references`/
    `call_sites`）成对保留：数值不变，名称说明含义，二者同时可读
    （`src/dexatlas/api/app.py:202-211` `anchor: call_site_count`、`src/dexatlas/reports/json_report.py:105-113` `anchor: call_sites`）。
- 文档中的版本陈述由 `scripts/check-version-claims.py` 对照 tag、`__version__`
  与 CHANGELOG 校验；报告数字由 `scripts/refresh-report-figures.py` 生成，禁止手改。

## 7. 验证记录

实测环境：Windows 11，Python 3.12.10。2026年11月15日的首次实测在 branch
`claude/agitated-diffie-f2a45f` 上完成，2026年11月17日按本节清单复跑两次。
快照测试 `tests/test_public_contracts.py` 把同样的清单固化为回归门禁。

**检查项清单共 55 项：31 REST + 6 MCP + 18 CLI**——即
`scripts/verify-public-contracts.py` 里 `check()` 调用点的条数（`_rest_requests()`
31 个、`mcp_checks()` 6 个、`cli_checks()` 18 个）。下面三张表每行对应脚本里的一次
`check()`，行数与分项数相等。

**55 是静态条数，任何一次实跑都跑不满它。** REST 段有两个调用点只在其余分支上记：
`server comes up` 只在服务起不来时记（起不来则本段只记这 1 项并中止），
`X-DexAtlas-Source-* headers` 只在源码端点返回 200 时记。CLI 段的 `source` 与
`resources` 各有一个调用点按「这次分析里有没有对应后端参与」分支，两种配置走不同的
那条（见 §7.3）。所以实跑的**执行条数**依机器而定：

| 实跑 | 可用后端 | 执行条数 | 通过 | 退出码 |
|---|---|---|---|---|
| 2026年11月17日，branch `claude/contract-check-premise-197604`（commit `8483db2`） | 仅 androguard 4.1.4，JADX 与 Apktool 都不在环境里 | 50（26 REST + 6 MCP + 18 CLI） | **50/50** | 0 |
| 2026年11月17日，branch `claude/contract-check-premise-197604`（commit `8483db2`） | jadx 1.5.2 + apktool 2.11.1 + androguard 4.1.4 | 51（27 REST + 6 MCP + 18 CLI） | **51/51** | 0 |
| 2026年11月25日，worktree `eager-antonelli-ea7f79`（未提交） | 仅 androguard 4.1.4，JADX 与 Apktool 都不在环境里 | 53（29 REST + 6 MCP + 18 CLI） | **53/53** | 0 |
| 2026年11月25日，worktree `eager-antonelli-ea7f79`（未提交） | jadx 1.5.2 + apktool 2.11.1 + androguard 4.1.4 | 54（30 REST + 6 MCP + 18 CLI） | **54/54** | 0 |

> **2026年11月20日更新**：C8 落地（`dexatlas runs` / `dexatlas render`）后，CLI 段
> 增加 3 个调用点（runs 列表、未知 run id → 2、render 已发布运行落盘），静态总数
> 由 49 升至 **52**。表中 2026年11月17日那两行实跑数字是**旧脚本**的记录（当时
> CLI 段 15 项）；按新脚本，两行相应为 50 / 51。表中保留旧数字以忠实记录当时那
> 两次实跑；当前配置的实跑以 `scripts/check-contract-records.py --expect <配置>`
> 的结果为准。

> **2026年11月25日更新**：Phase 5 W2 的 stages 端点进入活检，REST 段增加 3 个
> 调用点（stages 形状、阶段顺序、无此 run → 404），静态总数由 52 升至 **55**
> （31 REST + 6 MCP + 18 CLI）。当日两种配置各实跑一次，结果记在本节表里。

命令：`uv run --no-sync python scripts/verify-public-contracts.py`。本 worktree 用
自己的 `.venv`（`uv sync --frozen --all-extras`），后端路径经 `DEXATLAS_JADX_PATH` /
`DEXATLAS_APKTOOL_JAR` 指向 `E:\Dexatlas\.scratch\backends`，临时目录指向本
worktree 的 `.scratch\tmp`。

两次的差在一处条件检查上：缺 JADX 时源码端点返回 404，`X-DexAtlas-Source-* headers`
不记，REST 段执行 29 项（2026年11月25日口径；旧脚本是 26 项）；三后端齐备时它触发
并通过，REST 段执行 30 项（旧脚本是 27 项）。CLI 段的 18 项两种配置下都记满——分支
走的是同一个调用点。

### 7.1 REST 实测

以 `uvicorn dexatlas.api.app:app` 起服务，上传 `examples/demo-app/demo.apk` 后逐
端点核对（脚本 `scripts/verify-public-contracts.py` 的 `_rest_requests()`，静态
31 个调用点；服务起得来时本段实跑 30 项——`server comes up` 只在起不来的分支上记）：

| 检查 | 结果 |
|---|---|
| 服务起来（起不来则记 `server comes up` 并中止本节；起得来时这一项不计入本段条数） | ✅ |
| `GET /health` → `{status,version,backends}`，`status=="ok"` | ✅ |
| `GET /backends` → `{available,missing,versions}`，两集合不相交 | ✅ |
| `POST /analyze` → 202 `{project_id,status,detail}` | ✅ |
| `POST /analyze` 的 `project_id` = `apk_<sha256[:16]>` | ✅ |
| 分析跑到 `completed` | ✅ |
| `GET /projects/{pid}` → §2.3 全部 14 字段 | ✅ |
| `GET /projects/{pid}` 的 `call_site_count == reference_count` | ✅ |
| `GET /projects` → `ProjectResponse[]` | ✅ |
| `GET /projects/{pid}/runs` → `{project_id,total,published_run_id,runs[]}`，RunResponse 11 字段 | ✅ |
| `GET /projects/{pid}/runs/{rid}` → `published==True` | ✅ |
| `GET /projects/{pid}/runs/{rid}/stages` → `{project_id,run_id,run_status,stages[]}`，`project_id`/`run_id` 对得上，`run_status` 与 run 详情一致 | ✅ |
| 上一行的每个阶段元素 → `{stage,started_at,finished_at}`，stage ∈ 五个阶段名，时间戳按阶段顺序不减 | ✅ 本次分析的 run 由当前代码写入，阶段事实非空 |
| `GET /projects/{pid}/runs/{rid}/stages`（无此 run） → 404 带 detail | ✅ |
| `GET /projects/{pid}/manifest` → 200（三后端齐备时 200；本机 Apktool 缺失时 404 带 reason） | ✅ |
| `GET /projects/{pid}/classes?limit=5` → `{project_id,total,classes}`，`len(classes) ≤ 5`，`total ≥ len(classes)` | ✅ |
| `GET /projects/{pid}/methods?limit=5` → `{project_id,total,methods}`，`total ≥ 1` | ✅ |
| `GET /projects/{pid}/resources` → `{project_id,total,resources}` | ✅ |
| `GET /projects/{pid}/resource-references` → `{project_id,total,references}` | ✅ |
| `GET /projects/{pid}/xrefs/{mid}` → `total_unit=="call_sites"`，`total==call_sites`，`call_edges ≤ call_sites` | ✅ |
| `GET /projects/{pid}/search?q=demo` → `{project_id,query,results}`，`query=="demo"` | ✅ |
| `GET /projects/{pid}/evidence` → `{project_id,total,evidence}`，`level ∈ {verified,lead,insufficient}` | ✅ |
| `GET /projects/{pid}/classes/{cls}/source` → 200 或 404 | ✅ |
| 上一行返回 200 时，四个 `X-DexAtlas-Source-*` 头齐全 | ✅ 三后端齐备时触发 |
| `GET /projects/{pid}/report?format=json` → `schema_version==3`，10 个顶层键 | ✅ |
| `GET /projects/{pid}/report?format=markdown` → `text/markdown` | ✅ |
| `GET /projects/{pid}/report?format=bogus` → 422 | ✅ |
| `GET /projects/apk_deadbeefdeadbeef` → 404 `{"detail":…}` | ✅ |
| `POST /uploads/cleanup` → `{"removed","names"}` | ✅ |
| `DELETE /uploads/{sha}` → 204 | ✅ |
| `DELETE /projects/{pid}` → 204 | ✅ |

REST 段有两项是条件检查：`server comes up` 只在服务起不来时记（起不来则本段中止，
只记这 1 项，REST 段合计 1 项）；`X-DexAtlas-Source-* headers` 只在源码端点返回
200 时记。缺 JADX 的实跑里后者不触发（端点返回 404），REST 段执行 29 项；三后端
齐备的实跑里它触发并通过（源码端点答 200，四个头齐全），REST 段执行 30 项。

**这一段只覆盖 REST 面。** 阶段事实在 MCP 面上没有对应工具——§3.1 的十一个工具里
没有它，MCP 调用方要阶段事实只能走 REST 或 workbench 的这个端点。这是一处**不对
称**，不是一处缺口：契约没有承诺 MCP 面有它。

### 7.2 MCP 实测

以 in-process `Client(build_server(analyzer))` 走 MCP 协议调用（同
`tests/test_mcp_tools.py` 的方式，脚本 `mcp_checks()`，6 项检查）：

| 检查 | 结果 |
|---|---|
| `list_tools()` 恰为 §3.1 的十一个名字 | ✅ |
| 每个工具都带 `read_only_hint=True` | ✅ |
| `list_projects` → `{projects,total,offset,limit}` | ✅ |
| `get_project_status` → `{project,completeness,published_run,runs,evidence_catalog}`，completeness 四键齐全 | ✅ |
| `search_symbols` → `{symbols,total,offset,limit}` | ✅ |
| `get_class_source` → `found/reason/kind/text/provenance/candidates` 六键 | ✅ |

响应都是有界的：`limit` 请求被上限收敛，摘录按行数和字节数截断（快照测试
`tests/test_mcp_tools.py` 的 `test_an_excerpt_is_bounded` 与
`test_list_projects_pages` 固化了这条）。

### 7.3 CLI 退出码实测

`CliRunner` 逐个触发（脚本 `scripts/verify-public-contracts.py` 的 `cli_checks()`，
静态 18 个调用点）：

| 场景 | 期望 | 实测（仅 androguard / 三后端齐备） |
|---|---|---|
| `version` | 0 | ✅ / ✅ |
| `backends` | 0 | ✅ / ✅ |
| `analyze examples/demo-app/demo.apk` | 0 | ✅ / ✅ |
| `projects` | 0，列出项目 | ✅ / ✅ |
| `source <pid> com.example.demo.MainActivity`（demo 的类）与 `source <pid> com.example.demo.Missing`（项目没有的类） | 无源码后端：1（空），并点名缺源码的类；有源码后端：0，stdout 打出该类源码，stderr 点名后端。项目没有的类：1（空） | ✅ / ✅ |
| `resources <pid>`（全部资源）与 `resources <pid> --name dexatlas_no_such_resource`（APK 没有的名字） | 无资源后端：1（空），并说明没有匹配；有资源后端：0，列出 `app_name` = `DexAtlas Demo`，点名 `apktool:`。APK 没有的名字：1（空） | ✅ / ✅ |
| `classes apk_nope` | 2 | ✅ / ✅ |
| `classes <pid> --limit 0`（Typer `min=1`） | 2 | ✅ / ✅ |
| `analyze 缺失文件` | 2 | ✅ / ✅ |
| `analyze 非APK文件` | 2 | ✅ / ✅ |
| `source` 歧义方法名（合成双重载项目） | 4 | ✅ / ✅ |
| 歧义方法的候选被列出（两个重载都在输出里） | 候选被列出 | ✅ / ✅ |
| `analyze` 桩抛 `AnalysisFailed` | 3 | ✅ / ✅ |
| `analyze` 项目带 `output_truncated` 错误 | 5，stderr 提到 exit code 5 | ✅ / ✅ |
| `analyze` 无可用代码索引（三后端全失败，manifest 仍可解析） | 6 | ✅ / ✅ |

`source` 与 `resources` 那两个调用点按「这次分析里有没有对应后端参与」分支。前提从项目
自己记下的 `tool_versions` 读——那是 `src/dexatlas/core/pipeline.py:1081-1096` 的
`_took_part` 用的同一份记录，问的是「这次运行有没有这个后端」，不是「这台机器上装没装」：

- 无源码后端（JADX、Apktool 都不在环境里）时：`source` 答 1（空），并在 stderr 点名缺
  源码的类；有源码后端时：答 0，stdout 打出该类自己的源码，stderr 点名产出它的后端
  （`jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java`）。
- 无资源后端时：`resources` 答 1（空），并说明没有匹配；有资源后端时：答 0，列出 demo
  自己的 `app_name` = `DexAtlas Demo`（出处
  `apktool 2.11.1 -> apktool:res/values/strings.xml`），并点名读它的后端。
- 两个调用点各自还核对一条与后端无关的「答案为空」：项目没有的类、APK 没有的名字——
  两种配置下都得是 1（空），所以「答案为空即 1」这条契约在两种配置下都被核对。

改动前，脚本把「没有源码/资源后端」写进了那两条断言的前提。后端齐备时前提不成立，
脚本把一棵正确的树判成不合格——失败的是断言的前提，不是产品行为。本次把判定逻辑改成
按后端可用性分支，红→绿如下（命令、环境与后端版本见本节开头的表）：

| 脚本版本 | 可用后端 | 执行条数 | 通过 | 退出码 |
|---|---|---|---|---|
| 改动前 | jadx 1.5.2 + apktool 2.11.1 + androguard 4.1.4 | 48（27 REST + 6 MCP + 15 CLI） | **46/48** | 1 |
| 改动前 | 仅 androguard 4.1.4 | 47（26 REST + 6 MCP + 15 CLI） | **47/47** | 0 |
| 改动后 | jadx 1.5.2 + apktool 2.11.1 + androguard 4.1.4 | 48（27 REST + 6 MCP + 15 CLI） | **48/48** | 0 |
| 改动后 | 仅 androguard 4.1.4 | 47（26 REST + 6 MCP + 15 CLI） | **47/47** | 0 |

改动前那 2 条未通过，正是 `source`（JADX 在场、答案非空 → 0）与 `resources`
（Apktool 在场、资源表有 `app_name` → 0）两条：脚本断言的是「无后端时的 1」，而
§1.2 承诺的是「答案为空即 1」。改动后静态条数不变（当时仍是 49 = 28 REST + 6 MCP +
15 CLI；2026年11月20日 C8 落地后升为 52 = 28 REST + 6 MCP + 18 CLI，2026年11月25日
stages 端点进活检后升为 55 = 31 REST + 6 MCP + 18 CLI，见本节开头），
那次实跑的条数也不变（47 / 48），变的只是那两条断言的判定依据。

## 8. 已知限制

本节记录契约的已知缺口与它的结局：一条缺口在修复前是什么、修复后是什么、调用方
怎么印证。它不是对承诺的描述，而是对"承诺与实现之间曾经差什么、现在差多少"的说明。
修复任何一条都属于公共契约变更，按 §6 的规则显式版本化，不得悄悄改。

本节当前没有未修复的条目：§8.1 唯一的一条已按提案修复，下面记的是那次变更的完整
记录。

### 8.1 三后端全部失败时 run 仍可能记 `completed`、CLI 退出码为 0

**状态：已按提案修复（新增退出码 6，方案 A），本条由「已知缺口」转为「已修复的
契约变更记录」。** 修复以兼容变更显式版本化（§6、CHANGELOG `[1.0.0]`）：
0–5 语义不变，0 的外延收窄。

- **原现象**：`DEXATLAS_TOOL_TIMEOUT_SECONDS` 过小等情况下，JADX、Apktool、
  Androguard 三个后端全部超时，报告带三条 `timeout` 错误、`classes`/`methods` 计数
  为 0——但只要 Apktool 在超时前写出了可解析的 `AndroidManifest.xml`，
  `project.status` 仍是 `completed`：只有 `classes` 为空**且** `manifest` 也为空时
  才记 `ProjectStatus.FAILED`，`analyze` 因此走成功分支，退出码 0。
- **与承诺的缺口（已补）**：§1.2 与 `docs/install.md` 的退出码表承诺"只看退出码能
  分辨残缺运行"——截断（`output_truncated`）以 5 表达，但"索引为空、所有代码后端
  都失败"的运行过去与完整成功的运行同为 0。现在这类运行以 **6（`EXIT_NO_INDEX`）**
  表达：判定为项目 `completed` 且 `class_count == 0` 且 `index_gaps` 非空
  （`_no_index`，`src/dexatlas/cli/main.py`），no-index 先于截断判定。部分后端失败
  （索引仍在）与无 DEX 的资源型 APK 不触发 6，仍为 0。
- **何时会发生**：代码/资源后端全部失败（超时或崩溃），同时 manifest 仍可解析——
  例如 Apktool 在被超时终止前已经写出 manifest。若 manifest 也没有，项目记为
  `failed`，`analyze` 以退出码 1 结束，不在此列。
- **调用方如何印证**（退出码之外的多重通道，均早已存在）：
  - CLI 的 JSON 报告：`errors[]` 非空，或 `summary.index_complete == false`、
    `summary.index_gaps[]` 非空、`summary.backends_with_errors` 非空（§5.1；判定函数
    `index_completeness`，`src/dexatlas/reports/summary.py:23-34` `anchor: index_completeness`）。
  - REST：`GET /projects/{pid}` 的 `errors[]`（`src/dexatlas/api/app.py:188-220` `anchor: ProjectResponse`）；
    `GET /projects/{pid}/runs` 的 `completeness == "partial"`
    （`src/dexatlas/api/app.py:229-252` `anchor: RunResponse`）。
  - 运行记录本身：存在任何错误时 `run.completeness` 为 `partial`，即"这次运行没有
    读完它要读的东西"。
  - 截断与"全失败"是两回事：前者由 `output_truncated` 错误判定并给出退出码 5；
    后者由 `index_gaps` 判定并给出退出码 6。
- **修复记录**：由提案
  [docs/proposals/exit-code-partial-read.md](../proposals/exit-code-partial-read.md)
  批准实施（方案 A：新增退出码 6，候选方案对比、版本化措辞与红→绿测试计划见该文）。
  回归测试：`tests/test_public_contracts.py` 的
  `test_cli_an_analysis_with_no_index_is_six`（先红 `assert 0 == 6`，后绿）及
  partial-index / resource-only / no-index-over-truncation 三项护栏。
- **「什么都没读到」的失败也要落库（2026-11-26 修复）**：上面「何时会发生」里说的
  「若 manifest 也没有，项目记为 `failed`」，过去只有内存里的模型记着：管线算出了
  `failed`，却没有把它写进数据库，项目行与 run 行仍停在 `running`。桌面端读的是
  持久化的状态，于是分析早就结束、界面却一直停在「分析中」；只有后端重启时那次
  孤儿轮次对账会把它改成 `failed`，而它给的理由是「服务端进程在分析结束前就结束
  了」——对这次「分析其实跑完了、只是失败状态没写」的情形恰好说反。现在这条路径把
  失败写进数据库：项目行记 `failed`、run 行记 `failed`，并带一条说得清原因的错误
  （`dexatlas: the analysis finished but read nothing: ...`）。空的结果**不**发布，
  已发布的快照保持原样；取消路径与异常路径不变
  （`src/dexatlas/core/pipeline.py:519-565` `anchor: _record_empty_result`）。
  回归测试：`tests/test_empty_result.py`（拿掉修复即红：项目行与 run 行都停在
  `running`）。
