# 模型能力可禁用性验证报告（M4 退出标准）

**日期：** 2026-11-14
**基准提交：** `1f1d883`（main 最新），worktree 分支 `claude/cranky-joliot-c09ed1`
**验证对象：** [phase2-plan.md §6](../roadmap/phase2-plan.md) M4 退出标准第 6 条——
**"Every model-dependent capability can be disabled without breaking the static
analysis core"**（每一个依赖模型的能力都可以被禁用，而不破坏静态分析核心）。
**验证方式：** 在**不设置任何 `DEXATLAS_AGENT_*` 环境变量**的前提下，逐一驱动
CLI、REST API、workbench、MCP server 与分析管线，记录每项的实际输出。每条结论附可复现命令。
**范围边界：** 本报告只做验证并记录结果，不修改产品代码。

---

## 1. 结论

**该退出标准成立。** 不配置任何模型端点时：

- CLI 的全部 11 个子命令正常完成；
- REST API 的 health、分析上传、项目查询正常；
- workbench 的全部静态分析端点（项目、状态、检索、源码、证据、locator、调用关系、上传、报告导出、benchmark）正常；
- MCP server 的 10 个工具全部正常应答；
- 唯一依赖模型的入口——`POST /api/projects/{id}/agent/tasks`——返回**明确的
  `503` + `agent_not_configured`**，而不是崩溃、挂起或静默降级。

模型能力是纯增量：去掉模型配置，静态分析核心（分析管线、索引、证据、报告）毫发无损。

---

## 2. 模型依赖在哪里

代码层面的依赖点只有一处：workbench 的 agent 工作区。

| 依赖点 | 位置 | 行为 |
|---|---|---|
| 模型端点配置 | [agent_tasks.py:56-81](../../src/dexatlas/workbench/agent_tasks.py) | 全部来自 `DEXATLAS_AGENT_BASE_URL` / `DEXATLAS_AGENT_MODEL` / `DEXATLAS_AGENT_API_KEY` / `DEXATLAS_AGENT_PROVIDER` 等环境变量，**没有默认值**——"操作员没有指向的模型不是这台机器该调用的模型" |
| 读取配置 | [agent_tasks.py:127-147](../../src/dexatlas/workbench/agent_tasks.py) `read_agent_model_config()` | URL 或模型名缺一个就返回 `None`，即"未配置" |
| 创建 provider | [agent_tasks.py:169](../../src/dexatlas/workbench/agent_tasks.py) `default_agent_provider_factory()` | 配置为 `None` 时返回 `None` |
| agent 提问端点 | [app.py:395-421](../../src/dexatlas/workbench/app.py) `ask_agent` | provider 为 `None` 时抛 `HTTPException(503, {"code": "agent_not_configured", ...})`，错误信息指出缺哪几个环境变量 |
| agent 状态可见性 | [app.py:361-374](../../src/dexatlas/workbench/app.py) `agent_config` | `GET /api/agent/config` 返回 `{"configured": false}`，屏幕据此显示未配置状态而非报错 |

除此之外，[CLI](../../src/dexatlas/cli/main.py)、[REST API](../../src/dexatlas/api/app.py)、
[MCP server](../../src/dexatlas/mcp/server.py) 与
[分析管线](../../src/dexatlas/core/pipeline.py) 中 `grep -rn "DEXATLAS_AGENT\|agent_provider\|agent_not_configured"`
零命中——它们不 import 任何模型 provider，也没有任何需要模型才初始化的路径。
MCP 的定位本身就是"工具服务器"：[examples/mcp_client.py:8-10](../../examples/mcp_client.py)
写明"It needs **no model provider**"。

---

## 3. 验证矩阵与证据

环境：Windows 11，Python 3.12（worktree 独立 `.venv`），后端 JADX 1.5.2 / Apktool 2.11.1 / androguard 4.1.4。
每条命令执行前均显式 `unset` 全部 `DEXATLAS_AGENT_*` 变量并确认 `env | grep DEXATLAS_AGENT` 为空。
工作区为 `--workspace .scratch/verify-ws`，分析对象为仓库自带 `examples/demo-app/demo.apk`。

### 3.1 分析管线与 CLI

| # | 验证项 | 命令 | 实际结果 |
|---|---|---|---|
| 1 | 分析管线 | `uv run dexatlas analyze examples/demo-app/demo.apk --workspace .scratch/verify-ws` | ✅ exit 0：`✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (5.3s)` |
| 2 | `dexatlas version` | 同上环境 | ✅ `dexatlas 0.2.0`，exit 0 |
| 3 | `dexatlas backends` | 同上 | ✅ 三个后端全部 available，表格正常，exit 0 |
| 4 | `dexatlas projects` | 同上 | ✅ 列出 1 个 completed 项目，exit 0 |
| 5 | `dexatlas classes <id> --limit 3` | 同上 | ✅ 列出 3 个类及 androguard/jadx 双来源 locator，exit 0 |
| 6 | `dexatlas methods <id> --limit 3` | 同上 | ✅ 方法表（Flags/Decompiled 列）正常，exit 0 |
| 7 | `dexatlas source <id> com.example.demo.Crypto` | 同上 | ✅ 输出反编译 Java 源码，exit 0 |
| 8 | `dexatlas source … --method sign --descriptor … --format json` | 同上 | ✅ JSON 文档带完整 provenance（`jadx 1.5.2 -> jadx:sources/...#sign(...)`），exit 0 |
| 9 | `dexatlas resources <id>` | 同上 | ✅ 资源表 1 条（app_name），exit 0 |
| 10 | `dexatlas search <id> sign` | 同上 | ✅ 命中 method + string，exit 0 |
| 11 | `dexatlas manifest <id>` | 同上 | ✅ 包名/版本/SDK/权限/组件齐全，exit 0 |
| 12 | `dexatlas xrefs <id> <method_id>` | 同上 | ✅ 列出 1 个调用点及 dex 偏移，exit 0 |

### 3.2 REST API（`uvicorn dexatlas.api.app:app`，端口 8633）

| # | 验证项 | 请求 | 实际结果 |
|---|---|---|---|
| 13 | health | `GET /health` | ✅ 200：`{"status":"ok","version":"0.2.0","backends":{...三个版本齐全}}` |
| 14 | 分析上传 | `POST /analyze`（multipart `file=@demo.apk`） | ✅ 202：`{"project_id":"apk_80a8fe0e81204c9f","status":"completed","detail":"/projects/..."}` |
| 15 | 项目列表 | `GET /projects` | ✅ 200：1 个项目，计数完整（5 classes / 8 methods / 23 call sites / 21 call edges / 11 evidence） |
| 16 | 项目详情 | `GET /projects/apk_80a8fe0e81204c9f` | ✅ 200：状态、tool_versions、errors=[] 齐全 |

REST API 源码中无任何 agent/model 引用（grep 零命中），不提供 agent 端点——模型能力只存在于 workbench。

### 3.3 Workbench（`dexatlas-workbench --port 8631`）

| # | 验证项 | 请求 | 实际结果 |
|---|---|---|---|
| 17 | 健康与版本 | `GET /api/health` | ✅ 200：`{"version":"0.2.0","workspace":"verify-ws"}` |
| 18 | 项目列表 | `GET /api/projects` | ✅ 200，1 个项目，字段完整 |
| 19 | 项目状态 | `GET /api/projects/{id}` | ✅ 200：completeness.complete=true，runs/tool_versions 齐全 |
| 20 | 符号检索 | `GET /api/projects/{id}/symbols?q=demo` | ✅ 200：3 个命中（Crypto/MainActivity/NetworkClient） |
| 21 | 类源码 | `GET /api/projects/{id}/source/class?class_name=com.example.demo.MainActivity` | ✅ 200：Java 源码 + provenance `jadx:sources/...` |
| 22 | 证据列表 | `GET /api/projects/{id}/evidence` | ✅ 200：11 条证据（E-0001…），含 kind/level/provenance |
| 23 | 单条证据 | `GET /api/projects/{id}/evidence/E-0004` | ✅ 200：cross_reference/verified 及双 Androguard locator |
| 24 | locator 解析 | `GET /api/projects/{id}/locators/resolve?locator=androguard:classes.dex#com.example.demo.Crypto` | ✅ 200：`{"resolved":true,"reason":"com.example.demo.Crypto is in classes.dex"}` |
| 25 | 调用方 | `GET /api/projects/{id}/callers?method_id=com.example.demo.Crypto.sign(...)` | ✅ 200：1 call site / 1 call edge，含指令偏移 |
| 26 | 被调方 | `GET /api/projects/{id}/callees?method_id=com.example.demo.MainActivity.onCreate(...)` | ✅ 200：5 call sites / 5 edges |
| 27 | 上传分析 | `POST /api/analyze`（multipart `file=@demo.apk`） | ✅ 202：`{"project_id":"apk_80a8fe0e81204c9f","status":"completed","already_analysed":true}` |
| 28 | 报告导出（JSON） | `GET /api/projects/{id}/report?format=json` | ✅ 200：schema_version/project/manifest/evidence/tools 等 10 个键齐全 |
| 29 | 报告导出（Markdown） | `GET /api/projects/{id}/report?format=markdown` | ✅ 200：Markdown 报告正文正常 |
| 30 | benchmark 视图 | `GET /api/benchmarks/m3` | ✅ 200（response_model=BenchmarkSet） |
| 31 | 前端页面 | `GET /` | ✅ 200：构建后的单页应用正常返回 |
| 32 | agent 配置视图 | `GET /api/agent/config` | ✅ 200：`{"configured":false}`——屏幕据此显示"未配置"，而非报错 |
| 33 | **agent 提问（核心项）** | `POST /api/projects/{id}/agent/tasks` `{"question":"What permissions does this app use?"}` | ✅ **503**：`{"detail":{"code":"agent_not_configured","message":"no model endpoint is configured; set DEXATLAS_AGENT_BASE_URL and DEXATLAS_AGENT_MODEL (and, when the endpoint needs one, DEXATLAS_AGENT_API_KEY) to ask the agent a question"}}` |

第 33 项是这条退出标准的正面测试：模型能力被禁用（未配置）时，agent 端点**明确拒绝**，
错误码、人话解释和补救指引（设置哪几个环境变量）一应俱全，服务本身继续正常服务其余 16 个端点。

### 3.4 MCP server（`python -m dexatlas.mcp.server`，stdio）

以 [examples/mcp_client.py](../../examples/mcp_client.py) 同构的 stdio 客户端逐个调用全部工具：

| # | 工具 | 调用参数 | 实际结果 |
|---|---|---|---|
| 34 | `list_tools` | — | ✅ 10 个工具全部注册 |
| 35 | `list_projects` | limit=5 | ✅ 1 个项目 |
| 36 | `get_project_status` | demo 项目 | ✅ status=completed, complete=True |
| 37 | `get_manifest` | demo 项目 | ✅ package=com.example.demo, permissions=1 |
| 38 | `search_symbols` | query=demo | ✅ 3 个命中 |
| 39 | `get_class_source` | MainActivity | ✅ found=True, kind=java |
| 40 | `get_method_source` | onCreate + descriptor | ✅ found=True |
| 41 | `find_callers` | Crypto.sign | ✅ 1 call site / 1 edge |
| 42 | `find_callees` | MainActivity.onCreate | ✅ 5 call sites / 5 edges |
| 43 | `get_evidence` | E-0004 | ✅ level=verified |
| 44 | `resolve_locator` | androguard:classes.dex#com.example.demo.Crypto | ✅ resolved=True |

11 项检查全部通过（脚本输出 `MCP_ALL_TOOLS_OK (11 checks)`）。MCP server 与模型零耦合。

---

## 4. 与退出标准的对照

| 退出标准要求 | 本报告的证据 | 判定 |
|---|---|---|
| 模型能力**可以**被禁用 | 全部模型能力由 `DEXATLAS_AGENT_*` 环境变量开关，unset 即禁用（§2） | ✅ |
| 禁用后**静态分析核心不破坏** | CLI 12 项、REST 4 项、workbench 16 项、MCP 11 项全部正常（§3.1–3.4） | ✅ |
| 禁用后 agent 能力**明确拒绝**而非崩溃 | `POST …/agent/tasks` → 503 + `agent_not_configured` + 补救指引（§3.3 #33） | ✅ |
| 禁用状态对用户**可见** | `GET /api/agent/config` → `{"configured":false}`（§3.3 #32） | ✅ |

## 5. 验证的边界

- 本报告验证的是**未配置模型**这一种禁用方式（这也是设计上唯一的禁用开关：
  [app.py:354-359](../../src/dexatlas/workbench/app.py) 注明"The model endpoint is
  configuration, not convention"）。没有验证"配置了模型再动态拔掉"的运行中禁用——
  设计上模型配置只在每次请求时读取（factory per request），重启进程即可生效。
- agent 任务在**已配置模型**下的行为（任务排队、轮询、报告生成）不在本报告范围，
  由 M4 验收演练报告与后续 agent 专项验证覆盖。
- 验证均在单机、单项目（demo.apk）规模下进行，不代表性能结论。

## 6. 复现命令

```bash
# 共同前提（本仓库惯例）：后端路径与缓存重定向；并确保没有任何模型配置
unset DEXATLAS_AGENT_BASE_URL DEXATLAS_AGENT_MODEL DEXATLAS_AGENT_API_KEY \
      DEXATLAS_AGENT_PROVIDER DEXATLAS_AGENT_MAX_TOKENS DEXATLAS_AGENT_MAX_ITERATIONS \
      DEXATLAS_AGENT_MAX_SECONDS DEXATLAS_AGENT_MAX_STEPS
env | grep DEXATLAS_AGENT   # 应为空

# §3.1 CLI 与分析管线
uv run --no-sync dexatlas analyze examples/demo-app/demo.apk --workspace .scratch/verify-ws
uv run --no-sync dexatlas version
uv run --no-sync dexatlas backends
uv run --no-sync dexatlas projects
uv run --no-sync dexatlas classes apk_80a8fe0e81204c9f --limit 3
uv run --no-sync dexatlas methods apk_80a8fe0e81204c9f --limit 3
uv run --no-sync dexatlas source apk_80a8fe0e81204c9f com.example.demo.Crypto
uv run --no-sync dexatlas source apk_80a8fe0e81204c9f com.example.demo.Crypto \
  --method sign --descriptor '(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;' --format json
uv run --no-sync dexatlas resources apk_80a8fe0e81204c9f
uv run --no-sync dexatlas search apk_80a8fe0e81204c9f sign
uv run --no-sync dexatlas manifest apk_80a8fe0e81204c9f
uv run --no-sync dexatlas xrefs apk_80a8fe0e81204c9f \
  'com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;'

# §3.2 REST API
uv run --no-sync uvicorn dexatlas.api.app:app --port 8633 &
curl -s http://127.0.0.1:8633/health
curl -s -X POST -F "file=@examples/demo-app/demo.apk" http://127.0.0.1:8633/analyze
curl -s http://127.0.0.1:8633/projects

# §3.3 Workbench
uv run --no-sync dexatlas-workbench --port 8631 &
curl -s http://127.0.0.1:8631/api/health
curl -s http://127.0.0.1:8631/api/projects
curl -s "http://127.0.0.1:8631/api/projects/apk_80a8fe0e81204c9f/symbols?q=demo"
curl -s "http://127.0.0.1:8631/api/projects/apk_80a8fe0e81204c9f/evidence/E-0004"
curl -s "http://127.0.0.1:8631/api/benchmarks/m3"
curl -s http://127.0.0.1:8631/api/agent/config          # {"configured":false}
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"question":"What permissions does this app use?"}' \
  http://127.0.0.1:8631/api/projects/apk_80a8fe0e81204c9f/agent/tasks   # 503 agent_not_configured

# §3.4 MCP
DEXATLAS_WORKSPACE=$PWD/.scratch/verify-ws uv run --no-sync python examples/mcp_client.py
```
