# M4 源码评审与验收报告

**日期：** 2026-11-14
**评审对象：** M4 web workbench，基准提交 `71c8d8c`（main 最新；worktree 分支
`claude/jolly-mayer-639bc1` 从同一提交切出，评审在 worktree 内进行）。
**M4 退出标准出处：** [docs/roadmap/phase2-plan.md §6](../roadmap/phase2-plan.md)（`M4 exit criteria`，6 条，[phase2-plan.md:414-423](../roadmap/phase2-plan.md)）。
**前置材料：** [验收演练报告](m4-acceptance.md)（2026-11-13，基准 `ba770f6`）·
[端到端实测报告](m4-e2e-run.md)（2026-11-14，基准 `a322e09`）。

**结论先行：M4 验收判定为「有条件通过」。** 六屏全部建成且源码评审未发现违反
只读边界、上传策略分叉或密钥泄露的问题；六条退出标准中 5 条满足、1 条（端到端）
满足但带一条已知缺口——真实模型在默认预算内走不完「工具 → 结论」的循环，链路的
每一环都各自可用且已实测，但「问一句就得到一句带引用的结论」对当前模型配置
不可复现。该缺口已在 [m4-e2e-run.md §3-P1](m4-e2e-run.md)、
[docs/status.md](../status.md) 与 [v0.2.0 发布说明](../releases/v0.2.0.md) 如实披露，
不构成对退出标准字面的违反，但在它收敛之前，M4 的「portfolio」目标只算部分达成。

**范围边界：** 本报告是评审与验收，不修改产品代码。源码评审发现的全部问题按
严重度列在 §4；其中 P2-1 与 P2-2 是文档与实现的一致性问题，修复属于文档任务，
不阻塞验收判定。

---

## 1. 评审范围与方法

### 1.1 源码评审覆盖

| 文件 | 行数 | 内容 |
|---|---|---|
| [src/dexatlas/workbench/app.py](../../src/dexatlas/workbench/app.py) | 524 | 全部 19 个路由（17 个 API + 静态兜底）、错误映射、上传端点、导出端点 |
| [src/dexatlas/workbench/agent_tasks.py](../../src/dexatlas/workbench/agent_tasks.py) | 542 | agent 后台任务、模型配置读取、预算、任务视图、报告复用 |
| [src/dexatlas/workbench/benchmarks.py](../../src/dexatlas/workbench/benchmarks.py) | 194 | M3 基准视图的 trace 重算与披露 |
| [src/dexatlas/workbench/\_\_main\_\_.py](../../src/dexatlas/workbench/__main__.py) | 118 | 启动、首次构建前端、npm 环境隔离 |
| [src/dexatlas/workbench/web/src/](../../src/dexatlas/workbench/web/src/) | ~2500 | App.tsx（1853，六屏 UI + 路由）、api.ts（494，契约镜像）、main.tsx、styles.css |
| [src/dexatlas/api/uploads.py](../../src/dexatlas/api/uploads.py) | 392 | 两个 transport 共用的上传策略（评审重点：是否真的共用） |
| [tests/test_workbench.py](../../tests/test_workbench.py) 等 5 个测试文件 | — | 47 + 16 + 6 + 17 + 4 = 90 个 workbench 相关测试，全部实跑通过 |

六屏对应关系（[workbench.md](../architecture/workbench.md) 的屏幕表）逐屏核对了
后端端点与前端路由：屏 1（`#/` 列表 + `/api/projects`）、屏 2（上传面板 +
`POST /api/analyze` + 轮询）、屏 3/4/7（`#/projects/{id}/search` 一屏串起
符号 → 源码 → 证据 → locator）、屏 5（`#/projects/{id}/calls` 调用关系）、
屏 6（`#/projects/{id}/agent`）、屏 8（项目页导出面板 + `#/benchmarks`）。

### 1.2 评审方法

- **边界破坏式核对**：对「只读」「无 shell」「无写端点」逐条找反例——列出全部
  路由逐一分类，检索 `subprocess`/`os.system`/`Popen`/`shell=True`，核对每个
  响应是否为 MCP 工具自己的 pydantic 模型。
- **共用代码核对**：对比 workbench `POST /api/analyze`（[app.py:262-287](../../src/dexatlas/workbench/app.py)）
  与 REST `POST /analyze`（[api/app.py:368-403](../../src/dexatlas/api/app.py)）
  的调用链，确认 staging、限额、校验、入库、后台分析是否同一份函数。
- **测试实证**：本 worktree 自建 `.venv`（`uv sync --extra dev --extra analysis
  --extra mcp --extra demo`），实跑 workbench 全部 5 个测试文件（90 passed）、
  `tests/test_docs.py`（60 passed）与四项文档门禁。
- **文档事实核对**：README 双语横幅、CHANGELOG 0.2.0 段、v0.2.0 发布说明、
  status.md、install.md、workbench.md 的每一条 M4 相关陈述与实现/测试比对，
  追溯其在 git 历史中的修改时点。

---

## 2. 源码评审结论

### 2.1 只读边界成立

`src/dexatlas/workbench/` 的全部 17 个 API 路由里，**写端点只有一个**：
`POST /api/analyze`（[app.py:262](../../src/dexatlas/workbench/app.py)），它只把
字节交给与 REST API/CLI 相同的分析管线。`POST /api/projects/{id}/agent/tasks`
（[app.py:395](../../src/dexatlas/workbench/app.py)）不写分析数据——它在工作区的
`agent-tasks/` 目录下写任务状态文件，这是 agent 自身设计的一部分
（[agent.md](../architecture/agent.md)），不是对工作区的写入。其余 15 个路由全部
是 GET，且每个都直接调用 `dexatlas.mcp.tools` 的只读工具函数。

无 shell、无子进程：workbench 包内除 `__main__.py` 的前端构建（`npm install`/
`npm run build`，[​__main__.py:70-81](../../src/dexatlas/workbench/__main__.py)）
外没有任何进程启动；`grep -rn "subprocess|os.system|Popen|shell=True"` 在
workbench 的其余文件里零命中。分析后端的调用只发生在 `run_background_analysis`
复用的既有 pipeline 里，workbench 自己不碰 JADX/Apktool。

浏览器收到的 JSON 就是 MCP 工具的形状：9 个数据端点都带
`response_model=<MCP pydantic 模型>`（[app.py:116-237](../../src/dexatlas/workbench/app.py)），
`tests/test_workbench.py` 对其中关键的几个（projects、symbols、callers、callees、
evidence）直接断言 `response.json() == tool(...).model_dump(mode="json")`
（[test_workbench.py:543-568](../../tests/test_workbench.py)）。前端 `api.ts` 的
interface 是这些模型的镜像，不加字段。唯一不是单个 MCP 工具的端点是
`GET /api/projects/{id}/evidence`（[app.py:209-224](../../src/dexatlas/workbench/app.py)），
它是「对每个 id 调一次 `get_evidence`」的集合，测试断言 `listed == [one]`——
集合里的每一项与 `/evidence/{id}` 逐字节一致（[test_workbench.py:446-458](../../tests/test_workbench.py)）。
错误也继承契约：`RequestError` 按 `unknown_project → 404`、其余 → 400 映射
（[app.py:95-99](../../src/dexatlas/workbench/app.py)），`find_callers/find_callees`
的「没有调用者」保持工具原样的 `0` 计数而不是 404（[test_workbench.py:615-638](../../tests/test_workbench.py)）。

### 2.2 上传策略与 REST API 共用同一份代码

这是 M4 验收演练（[m4-acceptance.md](m4-acceptance.md) P1-1）之后补上的关键一环，
评审确认共用是真实的、不是复制：

- 两个 transport 都调用 [src/dexatlas/api/uploads.py](../../src/dexatlas/api/uploads.py)
  的 `stage_upload`（staging → `stored_name` 安全命名 → `inspect_apk` 档案校验 →
  `uploads/<sha256>/<client-name>` 哈希入库）与 `run_background_analysis`
  （[workbench/app.py:269,280](../../src/dexatlas/workbench/app.py) 与
  [api/app.py:381,397](../../src/dexatlas/api/app.py)）。
- 两个应用都挂同一个 `UploadSizeLimitMiddleware`，limit 都取
  `ingest.MAX_APK_BYTES`（[workbench/app.py:93](../../src/dexatlas/workbench/app.py)、
  [api/app.py:167](../../src/dexatlas/api/app.py)），声明长度超限在路由前以 413 拒绝。
- 测试锁住了「同样的拒绝」：workbench 的 413 措辞与 API 一致
  （[test_workbench.py:1014-1033](../../tests/test_workbench.py)），非 APK 422
  （[test_workbench.py:1003-1013](../../tests/test_workbench.py)），重复上传答
  `already_analysed: true`（[test_workbench.py:1034-1073](../../tests/test_workbench.py)）。
  422 的 detail 会把校验器消息里的 staging 绝对路径替换成客户端文件名
  （[uploads.py:333-340](../../src/dexatlas/api/uploads.py)），不向调用方泄露
  服务器目录布局。
- 保留期清扫 `expire_uploads` 跳过运行中分析正在读的文件
  （[uploads.py:234-237](../../src/dexatlas/api/uploads.py)），并有专门测试
  （[test_upload_lifecycle.py:162](../../tests/test_upload_lifecycle.py)）。

两处刻意保留的差异也核对无误：REST 答 `AnalyzeJobResponse`（含 `detail` 链接），
workbench 答 `UploadAccepted`（含 `already_analysed`），各自形状独立定义，符合
uploads.py 模块声明「响应形状不在这里定义」的边界。

### 2.3 错误处理与路径脱敏

- **路径脱敏**：`/api/health` 只答工作区目录名，不答路径
  （[app.py:101-114](../../src/dexatlas/workbench/app.py)），
  `test_health_does_not_leak_the_workspace_path` 断言回答里没有任何路径分隔符
  （[test_workbench.py:291-306](../../tests/test_workbench.py)）——这正是验收演练
  P3-4 的修复，测试写法（「goes red against the old response」）满足铁律 1。
  上传 422 的脱敏见上节。项目列表/状态走 MCP 工具，其回答本就不含绝对路径。
- **后台任务不消失**：agent 循环外层有兜底 except，任务意外死亡时写 `failed`
  状态与原因（[agent_tasks.py:314-328](../../src/dexatlas/workbench/agent_tasks.py)），
  测试覆盖「模型端点宕机 → 任务 failed 且报告带错误」
  （[test_workbench_agent.py:457-485](../../tests/test_workbench_agent.py)）。
  上传的分析失败由 pipeline 记录在项目上并打日志
  （[uploads.py:377-384](../../src/dexatlas/api/uploads.py)），与 e2e 实测中
  「坏文件在页面上得到可读失败」一致。
- **输入校验**：分页 limit/offset 走 MCP 同款 `Query(ge=1, le=MAX_LIMIT)` 约束
  （越界 422 有测试）；问题长度 `max_length=2000`（[agent_tasks.py:84,345-349](../../src/dexatlas/workbench/agent_tasks.py)）；
  agent 任务 id 由服务端 `uuid4().hex[:12]` 生成，轮询端点用 `TaskStore.load`
  按文件名查找、查不到答契约错误（[app.py:384-393](../../src/dexatlas/workbench/app.py)），
  不存在把用户输入拼进路径的写操作，无路径穿越面。
- **`PinnedTaskStore`**（[agent_tasks.py:212-228](../../src/dexatlas/workbench/agent_tasks.py)）
  把 orchestrator 自铸的任务 id 钉在 202 应答的 id 上，两个测试分别从 store 层和
  真 orchestrator 层锁住这个契约
  （[test_workbench_agent.py:433-456,509-555](../../tests/test_workbench_agent.py)）。

### 2.4 Agent 屏的模型边界与密钥处理

- **模型是配置，不是默认**：`read_agent_model_config` 只从
  `DEXATLAS_AGENT_BASE_URL`/`DEXATLAS_AGENT_MODEL`/`DEXATLAS_AGENT_PROVIDER`/
  `DEXATLAS_AGENT_API_KEY` 读取（[agent_tasks.py:121-141](../../src/dexatlas/workbench/agent_tasks.py)）；
  未配置时 `POST …/agent/tasks` 答 503 `agent_not_configured`
  （[app.py:408-421](../../src/dexatlas/workbench/app.py)），测试断言不配置就拒绝、
  报错信息点名环境变量（[test_workbench_agent.py:163-181](../../tests/test_workbench_agent.py)）。
  未知 provider kind 是配置错误而非静默回退
  （[test_workbench_agent.py:400-410](../../tests/test_workbench_agent.py)）。
- **key 只进请求头**：`OpenAICompatibleProvider` 是 frozen dataclass，key 仅在
  `headers()` 里出现（[openai_compat.py:117-122](../../src/dexatlas/agent/providers/openai_compat.py)）；
  `TaskState` 的序列化字段不含 provider/key；测试三重验证——`/api/agent/config`
  的 JSON 不含 key、任务状态/JSON 报告/Markdown 报告三个文档都不含 key
  （[test_workbench_agent.py:331-379](../../tests/test_workbench_agent.py)）。
- **权限不放大**：workbench 的审批门只对「计划允许的敏感读」免暂停
  （[agent_tasks.py:231-244](../../src/dexatlas/workbench/agent_tasks.py)），
  工具白名单仍由 `Planner` 的 plan 决定并在 `ToolExecutor._refuse` 强制
  （[tool_executor.py:469-476](../../src/dexatlas/agent/tool_executor.py)），
  跨项目读取被 `project_id` 绑定拒绝（[tool_executor.py:477-485](../../src/dexatlas/agent/tool_executor.py)）。
  agent 的记录走项目自己的 `EvidenceBuilder`（builder 由分析本身构造，
  [agent_tasks.py:252-283](../../src/dexatlas/workbench/agent_tasks.py)），模型输出
  到不了 `verified`——这条链路在测试里有专门断言
  （[test_workbench_agent.py:486-508](../../tests/test_workbench_agent.py)）。

### 2.5 前端与基准屏

- **无 HTML 注入面**：`grep dangerouslySetInnerHTML|innerHTML` 在 `web/src/` 零命中；
  APK 来的文本全部以 React 文本节点渲染，并保留 MCP `UntrustedText` 的 notice
  （[api.ts:58-63](../../src/dexatlas/workbench/web/src/api.ts)）。前端错误处理统一
  走 `errorText`，非 JSON 响应降级到状态码文案（[api.ts:146-164](../../src/dexatlas/workbench/web/src/api.ts)）。
- **不画不存在的数字**：上传屏不画进度百分比（服务端没有进度量，
  [App.tsx:117-123](../../src/dexatlas/workbench/web/src/App.tsx)）；调用关系屏
  callee 节点不画计数（工具已去重、无 per-callee 计数）；agent 屏轮询显示 plan/
  工具时间线/预算而非虚构进度条（[App.tsx:483-487](../../src/dexatlas/workbench/web/src/App.tsx)）。
  轮询有上限（上传 ~15 分钟、agent ~10 分钟），超时说等待而非空转。
- **基准屏零重述**：`GET /api/benchmarks/m3` 每次请求用对比 harness 自己的
  `_run_from_document` + `format_value` 从仓库内 trace 重算
  （[benchmarks.py:140-175](../../src/dexatlas/workbench/benchmarks.py)），
  测试断言两连请求各读一次 trace 文件（无缓存，
  [test_workbench.py:1158-1180](../../tests/test_workbench.py)）、指标与 harness
  重算逐格相等（[test_workbench.py:1074-1119](../../tests/test_workbench.py)）、
  三条披露随行（[test_workbench.py:1120-1136](../../tests/test_workbench.py)）、
  trace 缺失答空列表加披露而非报错
  （[test_workbench.py:1137-1157](../../tests/test_workbench.py)）。

### 2.6 测试平台证据

本 worktree 实跑（fixtures 未拉取，集成测试按设计 skip）：

- workbench 全部 5 个测试文件：**90 passed**（47 transport + 16 agent 屏 +
  6 上传限额 + 17 生命周期 + 4 隔离），67.6s。
- `tests/test_docs.py`：**60 passed**（含 README overclaim 防线、链接解析、
  执行报告数字与树一致性）。
- `ruff check .` + `ruff format --check .`：全过（219 files already formatted）。
- `mypy`：Success, no issues found in 63 source files。
- `check-version-claims.py --base auto`：**findings: 0**。
- `check-doc-citations.py`：94 引用，**drifted: 0**。

当前树报告记录的测试总数是 1325（快 1182 + 集成 143，
[phase1-execution-report.md:76](phase1-execution-report.md)），指纹与树一致——
M3 审计曾发现的「报告描述不存在的树」问题（3 红）已由完整重测修复，本次
`test_docs.py` 全绿交叉确认了这一点。

---

## 3. M4 退出标准逐条核对

出处：[docs/roadmap/phase2-plan.md:414-423](../roadmap/phase2-plan.md)。

| # | 退出标准 | 判定 | 证据 |
|---|---|---|---|
| 1 | A new user can install and run the documented system. | ✅ **满足** | [install.md](../install.md) Requirements 已含 Python 3.12+/uv/JDK 21+/Node.js 18+（Node 仅构建 workbench 前端，P2-2 修复后）；`uv sync --extra dev --extra analysis --extra mcp --extra demo` 在本 worktree 一次成功；`dexatlas-workbench` 首启自动 npm build（[​__main__.py:61-83](../../src/dexatlas/workbench/__main__.py)），未装 npm 时报错信息带完整构建指引；CONTRIBUTING 已含 `scripts/fetch-fixtures.sh` 步骤并写明「skip 不是 pass」。README Quick Start 的命令与实现一致（`test_docs.py` 60 过含全部 quick-start 断言）。安装类文档缺口已在演练后的修复中闭环。 |
| 2 | Upload → analysis → question → evidence navigation → report export works end to end. | ✅ **满足，附一条已知缺口** | 逐屏浏览器实测见 [m4-e2e-run.md](m4-e2e-run.md)：上传 demo.apk → 后台分析 → 项目页 → 检索 → 源码 → 证据 E-0004 → locator 解析 → 调用关系一跳跳转 → 报告导出（与渲染器输出逐字节一致）全程走通；上传与导出两屏在演练时缺席、现已建成并有 21 个专项测试。**缺口**：Agent 提问环节的屏、API、轮询、报告、预算披露全部按设计工作，但真实模型（MiniMax-M3.1-Flash）在默认预算（12 步 / 20000 tokens）内 5/5 任务 `budget_exhausted`，「问题 → 带引用的结论」最后一跳对当前模型不可复现（[m4-e2e-run.md §2/§3-P1](m4-e2e-run.md)）。按退出标准字面（各环节可用）判满足；缺口作为已知限制披露于 [status.md](../status.md)、[v0.2.0.md](../releases/v0.2.0.md)。 |
| 3 | Tests pass on the supported platforms and backend configurations. | ✅ **满足（本机证据 + CI 配置在位）** | 本 worktree：workbench 系列 90 passed；test_docs 60 passed；ruff/mypy/doc-citations/version-claims 全绿。CI 六 job 配置核对无误（lint / test 3.12+3.13 矩阵 / test-partial-backends / m3-comparison / docker / security，[.github/workflows/ci.yml](../../.github/workflows/ci.yml)）。本报告未在 CI 上复核，与验收演练同一口径：本机全绿 + CI 配置存在。 |
| 4 | Known security and reliability limitations are **disclosed**. | ✅ **满足** | [v0.2.0.md Known limitations](../releases/v0.2.0.md) 逐条列明：workbench 六/八屏、真模型运行不可复现、agent 正确率主要是模型行为、样本小、截断 run 退出码 0、API 无鉴权（单用户设计、默认绑 127.0.0.1、反代是安全边界——install.md 有专节）。workbench 特有限制也已在位：上传保留期 24h 可配（`DEXATLAS_UPLOAD_RETENTION_SECONDS`）、agent 预算耗尽如实写 `budget_exhausted` + did not finish（[agent.md:118-121](../architecture/agent.md)）、key 只进请求头。 |
| 5 | **No unverified feature appears as a completed feature in the README.** | ✅ **满足** | 双语 README 横幅准确：八屏建成六屏，逐屏列出，明确「已进仓库但尚未发布」「agent-workspace 屏未建成」（[README.md:24-30](../../README.md)、[README.zh-CN.md:14-19](../../README.zh-CN.md)）。git 历史核对：横幅随每屏合入同步更新（1ea5139 修低报、27211fe 随 benchmark 屏把五屏改六屏）；唯一遗留不符是 agent 屏合入（3202ad7）本身未同步更新横幅，由后续 benchmark 屏提交顺带改准——期间窗口约 6.5 小时、均已闭合。`test_readme_does_not_overclaim` 及配套断言把「建成的必须点名、未建成的不得进 Quick Start」锁进测试。README 的 workbench 段与 workbench.md、CHANGELOG、v0.2.0 发布说明四者口径一致。 |
| 6 | Every model-dependent capability can be disabled without breaking the static analysis core. | ✅ **满足** | 模型能力只有 agent 提问一处：不配 `DEXATLAS_AGENT_*` 时仅 `POST …/agent/tasks` 答 503，其余 16 个端点与六屏其余部分照常工作（agent 测试用 `del client.app.state.agent_provider_factory` 精确模拟该状态）。模型调用走标准库 urllib 的自写 transport（[transport.py](../../src/dexatlas/agent/providers/transport.py)），不引入任何模型 SDK 依赖；pyproject 的核心 dependencies 无任何模型/网络 SDK，mcp 仅是可选 extra。静态分析核心（CLI/API/workbench 十个只读工具、上传、报告、基准重算）在零模型配置下完整可用——e2e 实测的其余全部环节即在此状态下走通。 |

**小结：6 条标准，5 满足、1 满足带已知缺口（标准 2 的 agent 环节），0 未满足。**

---

## 4. 发现的问题（按严重度）

评审遵循「指出真实问题，文件:行号，不臆测」。以下问题均已在源码/文档中定位核实；
按本任务边界**不修产品代码**，逐条给出建议去处。

### P1-1 真实模型在默认预算内答不完一个问题（功能缺口，非缺陷）

- **位置：** [src/dexatlas/agent/planner.py:171](../../src/dexatlas/agent/planner.py)（`DEFAULT_MAX_STEPS = 12` 写死，无环境变量覆盖）与 [Budget](../../src/dexatlas/agent/state.py) 默认值（20000 tokens / 8 iterations / 120s）的组合。
- **现象：** MiniMax-M3.1-Flash 每轮并行请求 2~5 个工具调用，12 步工具预算 3~4 轮即尽，token 随源码/证据读入很快触顶；5/5 个实测任务 `budget_exhausted`，全部工具调用 `ok`、证据全部 `verified`，但没走到「写出带引用的结论」。单轮直连对照（观察入 prompt、无工具循环）422 tokens 即返回规范结论 JSON——端点、鉴权、协议、解析都通，差的是多轮工具使用习惯与预算的匹配。
- **为何不阻塞验收：** 链路每一环各自可用且已实测；任务以诚实终态收场（`budget_exhausted` + did not finish），页面与报告如实披露消耗，不存在静默失败或虚构结果；缺口已记录在 [m4-e2e-run.md §3-P1](m4-e2e-run.md)、[status.md](../status.md)、[v0.2.0.md](../releases/v0.2.0.md)。
- **建议去处：** 独立任务，按 e2e 报告 §3-P1 的三个候选方向收敛——① 把 `max_steps` 暴露为环境变量（与既有 `DEXATLAS_AGENT_MAX_TOKENS/MAX_ITERATIONS/MAX_SECONDS` 对齐）；② 在 system prompt/协议层抑制同轮多工具并行请求；③ demo/验收场景换更「先答后读」的模型。修法落定后重跑 e2e 的 agent 段留证。

### P2-1 README 双语的 workbench 段未列 Agent 工作区入口，中文版缺 agent/MCP 专节

- **位置：** [README.md:195-240](../../README.md)（workbench 段列了六屏但其中没有 agent workspace 屏的条目；项目页入口 `ask the agent` 只在 e2e 报告与 status.md 出现）；[README.zh-CN.md](../../README.zh-CN.md) 整体无 `### The agent`/`### The MCP server` 专节，文档索引（180-198 行）未链接 [docs/architecture/agent.md](../architecture/agent.md) 与 [docs/architecture/mcp-server.md](../architecture/mcp-server.md)。
- **性质：** 不属「把未验证功能写成已完成」——横幅对屏状态的陈述是准确的；这是**已建成能力的欠展示**：英文 README 用专门小节介绍了 agent 库与 MCP server，中文版仅在横幅与路线图表里带过。双语信息量不对等，中文读者无从发现 agent 屏入口与两份架构文档。
- **建议去处：** 文档任务。中文 README 补 MCP server / agent 两小节（可缩译英文版）并在文档索引补两条链接；英文 workbench 段的六屏清单补一行 agent workspace（指向 `#/projects/{id}/agent`）。

### P2-2 `max_steps` 是 agent 预算中唯一不可经环境变量调整的维度

- **位置：** [src/dexatlas/agent/planner.py:171,182](../../src/dexatlas/agent/planner.py)（`DEFAULT_MAX_STEPS = 12` 为类字段默认，`Planner()` 无参数注入路径）；对照 [agent_tasks.py:72-75,175-182](../../src/dexatlas/workbench/agent_tasks.py)——tokens/iterations/seconds 三者都有 `DEXATLAS_AGENT_*` 覆盖，唯独步数没有。
- **性质：** 与 P1-1 同根：当前模型并行请求工具，12 步上限是最先触顶的预算，而运营者没有不改代码的调节手段。e2e 报告的候选修法①即是它。
- **建议去处：** 与 P1-1 同一任务处理；若采纳方向①，补一个「env 缺省时用 `DEFAULT_MAX_STEPS`」的回归测试（红→绿可证）。

### P3-1 workbench 默认端口 8618 无占用回退与指引

- **位置：** [src/dexatlas/workbench/__main__.py:23,97-103,114-118](../../src/dexatlas/workbench/__main__.py)。
- **现象：** 端口被占时 uvicorn 以 `[WinError 10048]` 退出（经 GBK 控制台转码显示为乱码），报错无「换端口」指引；多 worktree 并行开发时互相挡路（e2e 实测 §3-P3 已记录）。
- **建议去处：** 小改进任务：捕获绑定失败时打印一行「port N is in use; pass --port <other>」；或支持 `--port 0` 并在启动横幅里打印实际端口。

### P3-2 `benchmarks.py` 的 `sys.path.insert` 是进程级全局副作用

- **位置：** [src/dexatlas/workbench/benchmarks.py:148-150](../../src/dexatlas/workbench/benchmarks.py)。
- **性质：** 为了 import 仓库工具 `benchmarks.comparison.*`，把仓库根插进 `sys.path`。它是幂等的（先判 `not in sys.path`）、只读用途、且有注释说明取舍，风险低；但严格说这是进程级全局状态修改，若仓库根下存在与第三方包同名的顶层模块会被意外优先。当前仓库根无此类冲突（`benchmarks/`、`examples/`、`scripts/` 均非可撞名包）。
- **建议去处：** 不阻塞。若日后重构，可把 comparison harness 收进包内或改用 importlib 的显式路径加载；当下保持现状是合理取舍。

### P3-3 agent 提问端点对「项目存在但分析未发布」的语义未单独测试

- **位置：** [src/dexatlas/workbench/app.py:406-407](../../src/dexatlas/workbench/app.py) 只检查 `get_project(project_id) is None`；一个状态为 `pending`/`failed` 的项目行也能受理提问，随后 agent 工具读到的是不完整分析。
- **性质：** 这不算错误——agent 的 plan 第一步就是 `get_project_status`，completeness/missing_backends 会把不完整如实带进任务与报告（[test_workbench_agent.py:227-256](../../tests/test_workbench_agent.py) 验证了 plan 与工具时间线）；但「对 failed 项目提问」这一路径没有专门测试锁定其行为（报告应能成立，且 limitations 应提及分析未完成）。
- **建议去处：** 测试补强任务：加一个「对 failed/pending 项目提问，任务可完成且报告披露分析不完整」的断言，防止未来把「项目存在」误改成「项目已完成」时无测试报警。

---

## 5. 验收判定

**判定：有条件通过（conditional pass）。**

**理由：**

1. **六屏全部建成且质量达标。** 源码评审覆盖 workbench 全部后端与前端源码：
   只读边界成立（17 路由仅 1 个写端点且交给共享管线，无 shell、无路径穿越面），
   上传策略与 REST API 确认共用 `dexatlas.api.uploads` 同一份实现，响应与错误
   均为 MCP 工具自己的形状（关键端点有 `model_dump()` 逐字节断言），路径脱敏
   与密钥处理有专门测试锁住，前端不画不存在的数字、无 HTML 注入面，基准屏
   零重算缓存零数字重述。
2. **六条退出标准：5 满足、1 满足带已知缺口、0 未满足。** 标准 2 的链路已由
   [m4-e2e-run.md](m4-e2e-run.md) 逐屏浏览器实测走通并有逐字节一致性证据；
   agent 提问环节的缺口（P1-1）按设计诚实工作且已多文档披露，不构成对标准
   字面的违反，但使「一次完整提问得到回答」尚不可复现——这正是「有条件」的
   条件所在。
3. **门禁与测试平台全绿。** workbench 系列 90 测试、test_docs 60 测试实跑通过；
   ruff check/format、mypy strict、check-doc-citations（94 引用 0 漂移）、
   check-version-claims（0 findings）全部通过；报告记录的 1325 测试与指纹和
   当前树一致（M3 审计发现的过期报告问题已闭环）。
4. **README 不夸大。** 双语横幅与 CHANGELOG、v0.2.0 发布说明、status.md 四处
   口径一致：六/八屏、逐屏列名、未建成屏明示、agent 预算缺口披露。历史窗口
   内的短暂不同步已由后续提交闭合，且 overclaim 防线已进 `test_docs.py`。

**通过条件（后续任务，不阻塞本判定）：**

- 收敛 P1-1/P2-2：让「问题 → 带引用结论」在某个明确配置下可复现，并在
  e2e 报告补一段复验记录；
- 补齐 P2-1 的双语 README 展示缺口；
- 顺手处理 P3-1/P3-3 两个小项。

上述条件全部属于「让 M4 的 portfolio 目标完整成立」，而非本判定所依据的
退出标准本身的缺口；在它们完成前，M4 的验收状态以本报告为准记录为
**有条件通过**。

---

## 6. 复现命令汇总

```bash
# 环境（worktree 内，先做）
export DEXATLAS_JADX_PATH="<jadx>/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="<path>/apktool.jar"
export UV_CACHE_DIR="<scratch>/uv-cache"
mkdir -p .scratch/tmp && export TMPDIR="$PWD/.scratch/tmp" TEMP="$PWD/.scratch/tmp" TMP="$PWD/.scratch/tmp"
uv sync --extra dev --extra analysis --extra mcp --extra demo

# workbench 全部相关测试（90 个）
uv run --no-sync pytest -q tests/test_workbench.py tests/test_workbench_agent.py \
  tests/test_upload_limits.py tests/test_upload_lifecycle.py tests/test_upload_isolation.py

# 文档防线与四项门禁
uv run --no-sync pytest -q tests/test_docs.py
uv run --no-sync ruff check . && uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync python scripts/check-version-claims.py --base auto
uv run --no-sync python scripts/check-doc-citations.py

# 起服务走链路（e2e 报告的复现基线）
uv run --no-sync dexatlas-workbench --port 8620
```

源码评审核对点速查：路由清单 [app.py:101-489](../../src/dexatlas/workbench/app.py)；
上传共用 [uploads.py:282-354](../../src/dexatlas/api/uploads.py)（`stage_upload`）与
[uploads.py:356-392](../../src/dexatlas/api/uploads.py)（`run_background_analysis`）；
agent 边界 [agent_tasks.py:121-182](../../src/dexatlas/workbench/agent_tasks.py)（配置）、
[agent_tasks.py:231-244](../../src/dexatlas/workbench/agent_tasks.py)（审批门）、
[agent_tasks.py:286-328](../../src/dexatlas/workbench/agent_tasks.py)（兜底）；
工具白名单强制 [tool_executor.py:469-487](../../src/dexatlas/agent/tool_executor.py)；
基准重算 [benchmarks.py:140-194](../../src/dexatlas/workbench/benchmarks.py)。
