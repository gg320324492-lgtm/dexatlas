# M4 验收演练报告（新用户视角）

**日期：** 2026-11-13
**基准提交：** `ba770f6`（main 最新），worktree 分支 `claude/inspiring-raman-ee8b15`
**演练方式：** 只按仓库文档操作，从 clone 等价状态（本 worktree）出发，逐步执行 README /
[docs/install.md](../install.md) / [docs/architecture/workbench.md](../architecture/workbench.md) /
[CONTRIBUTING.md](../../CONTRIBUTING.md) 中的命令，记录实际结果。每条结论附可复现证据。

**M4 退出标准出处：** [docs/roadmap/phase2-plan.md §6](../roadmap/phase2-plan.md)（`M4 exit criteria`，6 条）。

**范围边界：** 本报告是验收演练，不修改产品代码。发现的文档与实现不符之处记录在
§4「发现的问题」，由后续任务修复。屏 2（APK 上传）与屏 8（报告导出）由其他会话开发中，
本文只记录其当前状态，不替它们背书。

---

## 1. 新用户步骤清单及实际结果

环境：Windows 11，Python 3.12，uv（缓存与临时目录已按仓库惯例重定向到系统盘之外）。
所有命令均在本 worktree 内执行；后端为 JADX 1.5.2、Apktool 2.11.1、androguard 4.1.4。

### 1.1 安装与首次运行

| # | 步骤（出处） | 命令 | 实际结果 |
|---|---|---|---|
| 1 | 创建环境（README「web workbench」段、[install.md](../install.md)） | `uv sync --extra dev --extra analysis --extra mcp --extra demo` | ✅ 成功，退出码 0。约 1 分钟。 |
| 2 | 查看后端（[install.md](../install.md)「Backends」） | `uv run dexatlas backends` | ✅ 输出与文档示例同构：jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4 全部 available。 |
| 3 | 分析内置 APK（[README.md:213](../../README.md)） | `uv run dexatlas analyze examples/demo-app/demo.apk` | ✅ `✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (5.0s)`。demo.apk 确认在仓库内（`examples/demo-app/demo.apk`），无需下载。 |
| 4 | CLI 检索（[README.md:142](../../README.md)） | `uv run dexatlas search apk_80a8fe0e81204c9f "Crypto"` | ✅ 返回 1 class + 3 method + 2 string 命中，表格渲染正常。 |
| 5 | CLI manifest（[README.md:141](../../README.md)） | `uv run dexatlas manifest apk_80a8fe0e81204c9f` | ✅ 输出包名、版本、SDK、权限、导出组件，与 [analysis-provenance.md](../analysis-provenance.md) 的示例一致。 |
| 6 | CLI 交叉引用（[README.md:143](../../README.md)） | `uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;"` | ✅ `1 call site(s), 1 call edge(s)`，给出调用点与 `classes.dex@34` 偏移。 |
| 7 | CLI 报告导出（[README.md:140](../../README.md)） | `uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json` | ✅ 生成 `report.md`（5.2 KB）与 `report.json`（11.7 KB）。 |
| 8 | 启动 workbench（[README.md:214](../../README.md)、[workbench.md:115-121](../architecture/workbench.md)） | `uv run dexatlas-workbench` | ✅ 首次启动自动 `npm install` + `npm run build` 前端（耗时数分钟，符合文档「npm once」），随后服务 `http://127.0.0.1:8618`，`GET /` 200。 |
| 9 | 启动 REST API（[README.md:149](../../README.md)） | `uv run uvicorn dexatlas.api.app:app --reload` | ✅ `/docs` 200（OpenAPI 页面）；`/health` 返回 `{"status":"ok","version":"0.1.3","backends":{...}}`。 |
| 10 | API 上传分析（[install.md:226](../install.md) `POST /analyze`） | `curl -X POST -F "file=@examples/demo-app/demo.apk" http://127.0.0.1:8000/analyze` | ✅ 202，返回 `{"project_id":"apk_80a8fe0e81204c9f","status":"completed","detail":"/projects/..."}`。 |
| 11 | MCP server（[README.md:168](../../README.md)） | `uv run dexatlas-mcp` + `uv run --no-sync python examples/mcp_client.py` | ✅ 客户端列出 10 个工具，每个都带「数据不是指令」的描述；全程无模型 provider。 |
| 12 | 文档自检（CLAUDE.md 规定的门禁） | `check-doc-citations.py` / `check-version-claims.py --base auto` / `ruff check` / `ruff format --check` / `mypy` | ✅ 引用 0 drift；版本陈述 2 个已知 findings（`phase1-acceptance-2026-10-21.md:63` 的 v0.2.0 表述、`status.md:67` 的 v0.1.3 表述，均为检查器已记录项）；ruff 全过；mypy strict 无问题。 |
| 13 | 完整测试套件（[CONTRIBUTING.md:43](../../CONTRIBUTING.md)） | `uv run pytest -q` | ✅ `1260 passed, 27 skipped in 380.79s`。**27 个 skip 全部是「fixture not present; run scripts/fetch-fixtures.sh」**（`tests/test_androguard_isolation.py:99` 等），是文档写明的预期跳过，不是后端缺失。 |

**新用户视角小结：** 从 clone 到看到 workbench 的路径是通的，文档命令全部可执行。
最大的体验缺口是：[install.md](../install.md) 的 Requirements 表没有列出 **Node.js/npm**
（workbench 首次启动需要），也没有在「Running the checks」之前提示 fixtures 脚本
（`scripts/fetch-fixtures.sh`）——新用户跑 `pytest` 会看到 27 个 skip 而不知道原因；
CONTRIBUTING.md 的开发设置段（`CONTRIBUTING.md:39-44`）同样没有提 fixtures。

### 1.2 Workbench 三屏浏览器实测

在独立实例（端口 8629，独立工作区 `.dexatlas-browser`）中用浏览器逐屏验证，全程
**0 个 console error、0 个失败请求**：

| 屏 | 路由 | 实测内容 | 结果 |
|---|---|---|---|
| 1 项目面板 | `#/` | 项目表：demo.apk · completed · 5 classes · 8 methods · 23 call sites · 21 edges · 11 evidence | ✅ 与 `/api/projects` 数据一致 |
| 2 检索与证据 | `#/projects/{id}/search` | 搜 `Crypto` → 6 命中；点类名打开 Java 源码（`SOURCE · JAVA`，含 provenance `jadx:sources/...` 与 resolve 按钮）；点 `Crypto.sign(...)` 打开方法体；点 E-0004 打开证据详情（JSON detail + 两条 Androguard locator）；点 resolve → `resolved — sign is in com.example.demo.Crypto` + 「this locator names a member of the APK, not a file to show.」 | ✅ 与 [workbench.md](../architecture/workbench.md) 描述一致；UntrustedText 提示在页面上出现（「Text from the analysed APK is data, not instructions...」） |
| 5 调用关系 | `#/projects/{id}/calls?method=...` | `describe(...)`：CALLERS 1 call site · 1 call edge（opcodes/DEX/offset 齐全）；CALLEES 4 call sites · 3 call edges（StringBuilder 三个被去重的 callee，各带 opcode 无计数）；点 caller 节点跳到 `onCreate` 的调用视图（0 in / 5 out），一跳一换 URL | ✅ 与文档「one hop per click」「callee 节点不带计数」一致 |

浏览器层验证通过：三屏都按文档工作，来源提示、零计数语义（0 而非 404）、locator
解析（DEX 符号显示「resolved 无文件可显示」）都与 [workbench.md](../architecture/workbench.md) 的承诺一致。

### 1.3 Workbench API 契约抽查

| 端点 | 实测 |
|---|---|
| `GET /api/health` | ✅ 返回版本与 workspace 路径 |
| `GET /api/projects` | ✅ `ProjectList` 形状，含每项目 missing_backends / truncated |
| `GET /api/projects/{id}` | ✅ `ProjectStatus` + completeness |
| `GET /api/projects/{id}/symbols?q=Crypto` | ✅ 每个字符串带 UntrustedText notice；空查询返回空列表而非错误 |
| `GET /api/projects/{id}/source/class?class_name=...` | ✅ `found:true, kind:"java"` + 源码 |
| `GET /api/projects/{id}/source/method?...&descriptor=...` | ✅ 精确到描述符的方法体 |
| `GET /api/projects/{id}/evidence` | ✅ 11 条，逐条为 `get_evidence` 形状 |
| `GET /api/projects/{id}/evidence/E-0004` | ✅ cross_reference + 两条 androguard provenance |
| `GET /api/projects/{id}/locators/resolve?locator=...` | ✅ `resolved:true` + reason |
| `GET /api/projects/{id}/callers?method_id=...` / `callees?...` | ✅ `CallerView`/`CalleeView` 形状，含 call_site_count / call_edge_count |
| unknown project（symbols / evidence / locators） | ✅ 一律 404（契约的 `unknown_project`） |

---

## 2. M4 退出标准逐条核对

出处：[docs/roadmap/phase2-plan.md:414-423](../roadmap/phase2-plan.md)。

| # | 退出标准 | 状态 | 证据 |
|---|---|---|---|
| 1 | **A new user can install and run the documented system.** | ✅ 满足（含一处文档缺口） | §1.1 的 13 步全部按文档跑通；缺口：[install.md](../install.md) 未列 Node.js/npm 前置要求，fixtures 脚本未在面向新用户的安装/贡献文档中前置说明（见 §4 P2）。 |
| 2 | **Upload → analysis → question → evidence navigation → report export works end to end.** | ❌ **未满足**（三段已通，两段未建成） | 已通：REST `POST /analyze` 上传→后台分析（§1.1 步骤 10）；CLI/API/MCP 的提问与证据导航（workbench 屏 2/5，§1.2/§1.3）；CLI 报告导出 `analyze -o report.md --json report.json` 与 REST `GET /projects/{id}/report?format=json\|markdown`（[app.py:952](../../src/dexatlas/api/app.py)）。**未建成：workbench 屏 2（APK 上传与分析进度）与屏 8（report export）**——[workbench.md:25,31](../architecture/workbench.md) 自身标注「not started」，workbench 应用无任何上传/导出端点（`src/dexatlas/workbench/app.py` 仅有 11 个只读 GET）。如实记录：**端到端链路在 workbench 内尚不成立**。 |
| 3 | **Tests pass on the supported platforms and backend configurations.** | ✅ 满足（本机证据） | 本 worktree：`1260 passed, 27 skipped`（skip 均为缺 fixtures，非平台差异）；ruff check/format、mypy strict、doc-citations、version-claims、`refresh-report-figures.py --check`（「The report matches a fresh measurement.」）全过。CI 的 3.12/3.13/部分后端/Docker 矩阵见 [.github/workflows/ci.yml](../../.github/workflows/ci.yml)（`test` job 为 3.12+3.13 矩阵、`test-partial-backends`、`docker`、`security`、`m3-comparison`、`lint`）。本报告未在 CI 上复核，标注为「本机全绿 + CI 配置存在」。 |
| 4 | **Known security and reliability limitations are disclosed.** | 🟡 **部分满足** | 已披露：无鉴权 API 只绑 127.0.0.1（[install.md:179-183](../install.md)）、反代是唯一安全边界（[install.md:198-208](../install.md)）、上传限额 256 MiB（[install.md:250](../install.md)，`MAX_APK_BYTES = 256*1024*1024`）、分析是同步 CPU 密集、`/analyze` 是后台任务（[app.py:14-16](../../src/dexatlas/api/app.py) 模块 docstring）、APK 内容一律视为不可信数据（[mcp-server.md:61-70](../architecture/mcp-server.md)、[workbench.md:59-63](../architecture/workbench.md)、[SECURITY.md:45-56](../../SECURITY.md)）、Docker 端口只发布到宿主回环（[install.md:42-55](../install.md)）。**缺口**：README 面向新用户的 Quick start 与「Intended use」段没有汇总这些限制的入口链接；SECURITY.md 只在 Contributing/README 尾部被顺带提及（见 §4 P3）。 |
| 5 | **No unverified feature appears as a completed feature in the README.** | 🟡 **基本满足，两处不准确** | 三屏描述与实测一致（[README.md:193-229](../../README.md)、[README.zh-CN.md:156-176](../../README.zh-CN.md)），且明写「not released」；agent 段明写「It is a library rather than a command」（[README.md:235](../../README.md)）。**不符两处**：① [README.md:26-27](../../README.md) / [README.zh-CN.md:16-17](../../README.zh-CN.md) 状态横幅仍说 MCP 与 web workbench「*planned*, not shipped」「尚未实现」，而 MCP server 与三屏 workbench 已在本分支实现且 CHANGELOG 已记录——横幅过时（方向是「写得保守」，不是夸大，但不准确）；② [workbench.md:138](../architecture/workbench.md) 说 evidence `E-0003` 带两条 Androguard locator，实测 E-0003 是**一条 apktool locator**（`apktool:AndroidManifest.xml#/application`），带两条 Androguard locator 的是 E-0004/5/6。 |
| 6 | **Every model-dependent capability can be disabled without breaking the static analysis core.** | ✅ 满足（按架构与依赖核实） | 静态分析核心（CLI/API/报告）不依赖任何模型：`dependencies` 里无模型 SDK（[pyproject.toml:36-50](../../pyproject.toml)）；MCP server「runs without any model provider」（[mcp-server.md:15-18](../architecture/mcp-server.md)，实测 §1.1 步骤 11）；agent 是独立包 `src/dexatlas/agent/`，模型通过 `providers/`（openai_compat/local/scripted）注入，README 明说「library rather than a command」。**注意**：没有「开关」式的运行时 flag——隔离是靠「模型能力在独立包 + 独立 extra + 独立入口」实现的；就 M4 的 workbench 而言，workbench 完全不碰 agent 包，标准满足。 |

**总评：** 6 条中 3 条满足、1 条部分满足、1 条基本满足（两处文档不准确）、1 条未满足
（端到端链路缺 workbench 上传与导出两屏——这正是其他会话正在开发的部分）。
M4 目前**不应**被宣布达成；达成前必须补上屏 2/屏 8 并让端到端链路在 workbench 里跑通。

---

## 3. 安全与可靠性限制披露清单

逐项核对「已知限制是否被写下来」：

| 限制 | 披露位置 | 状态 |
|---|---|---|
| REST API 无鉴权，只应绑 127.0.0.1；跨机需反代+鉴权 | [install.md:179-208](../install.md)、[install.md:42-55](../install.md)（Docker 段） | ✅ |
| 上传大小限制 256 MiB（413 拒绝），但不限请求数——暴露的 API 可被刷盘 | [install.md:203-208, 250, 254](../install.md)；实现 [app.py:221-252](../../src/dexatlas/api/app.py)、[ingest.py:41](../../src/dexatlas/core/ingest.py) | ✅ |
| 分析是同步 CPU 密集操作，`/analyze` 用后台任务而非并发模型 | [app.py:14-16](../../src/dexatlas/api/app.py) 模块 docstring | ✅（但只在源码注释里，用户文档未提） |
| APK/DEX/反编译文本是不可信输入；文本按 data 而非指令渲染 | [SECURITY.md:45-56](../../SECURITY.md)、[mcp-server.md:61-70](../architecture/mcp-server.md)、[workbench.md:59-63](../architecture/workbench.md)、MCP/Workbench 每个响应的 UntrustedText notice（实测可见） | ✅ |
| 后端子进程隔离、无 shell、工作区限定、本地优先 | [SECURITY.md:45-56](../../SECURITY.md) | ✅ |
| 缺后端是事实记录而非失败；计数依赖后端完整性 | [install.md:76-78](../install.md)、[mcp-server.md:45-49](../architecture/mcp-server.md)、`get_project_status` 返回 missing_backends（实测） | ✅ |
| MCP server 只读、有界、无模型 | [mcp-server.md:81-99](../architecture/mcp-server.md) | ✅ |
| workbench 只读：不写、不分析、不跑 shell | [workbench.md:3-5](../architecture/workbench.md)、[README.md:195](../../README.md)、[README.zh-CN.md:158-159](../../README.zh-CN.md) | ✅（实测 11 个端点全为 GET，无 POST） |
| 大型 APK 的未测量范围（真实样本、JADX/Apktool 规模表现、native、内存） | [status.md §4.3](../status.md)、[benchmarks/large-apk.md](../benchmarks/large-apk.md) | ✅ |
| **README 的限制入口** | Quick start / Intended use 段没有一处汇总「使用前必读的限制」链接（SECURITY.md 只在 Contributing 段被提一句，[README.md:292](../../README.md)） | ⚠️ 缺口 |
| **同步分析的用户可见说明** | install.md / README 均未告诉用户大 APK 会阻塞多久、`DEXATLAS_TOOL_TIMEOUT_SECONDS=900` 的含义 | ⚠️ 缺口（信息存在于配置表 [install.md:113](../install.md) 与源码注释，但未作为「可靠性限制」陈述） |

---

## 4. 发现的问题（按严重度排序）

严重度定义：**P1** = 阻塞 M4 退出标准或误导使用者对能力的判断；**P2** = 新用户按文档操作会卡住或得到意外结果；**P3** = 文档质量/一致性问题。

### P1-1 端到端链路在 workbench 内不成立（退出标准 2 的主体缺口）

**不是缺陷，是事实陈述：** 屏 2（APK 上传与分析进度）与屏 8（benchmark/report export）
尚未建成（[workbench.md:25,31](../architecture/workbench.md) 自标「not started」；
`src/dexatlas/workbench/app.py` 无上传/导出端点）。M4 退出标准 2 要求的
「Upload → analysis → question → evidence navigation → report export」目前只能在
「REST API 上传 + workbench 浏览 + CLI/API 导出」的组合下拼出来，workbench 自身不构成
端到端产品。**M4 不能在两屏落地前宣布达成。**（该工作正在其他会话进行，本报告不重复实现。）

### P1-2 README 状态横幅与 CHANGELOG/实现相矛盾

[README.md:24-28](../../README.md)（及中文版 [README.zh-CN.md:14-18](../../README.zh-CN.md)）写：
「Agent orchestration, MCP and the web workbench are *planned*, not shipped」/「属于规划中的
能力，尚未实现」。但 MCP server 已实现（M1 done，[HANDOVER.md:27](../HANDOVER.md)）、
agent 已实现（M2 done）、workbench 三屏已实现（[CHANGELOG.md:39](../../CHANGELOG.md) 的
Unreleased 段记录了它们）。横幅的方向是保守（没把没有的说成有），但**它把已有的说成了没有**，
同样违反「README 不与事实矛盾」的验收精神；而且横幅自称「Phase 1 — Foundation」，
与 Roadmap 表里 Phase 2 已推进到 M3/M4 的现状不一致。
**修法：** 横幅改为「Phase 2 in progress: MCP server and the agent are built; the workbench
has three of its eight screens; upload and export are not built yet」一类的准确陈述。

### P2-1 workbench.md 的 E-0003 示例与实际数据不符

[workbench.md:137-139](../architecture/workbench.md)：「searching `Crypto` finds the class and
its `sign` method, and evidence `E-0003` carries two Androguard locators that resolve into that
analysis.」实测（对 demo.apk 标准工作区查 `evidence` 表）：E-0003 是
`declaration · apktool:AndroidManifest.xml#/application`（一条 apktool locator）；带两条
Androguard locator 的是 **E-0004**（`Crypto.sign` 的 cross_reference）。按文档指引点开
E-0003 的用户会看到与文档不同的内容。第二屏的会话笔记也把实测对象记成了 E-0003，
说明这一偏差已经存在了一段时间。
**修法：** 把示例改成 E-0004，或改为「a cross-reference record such as E-0004」。

### P2-2 新用户文档缺少 Node.js/npm 前置要求与 fixtures 步骤

- [install.md](../install.md) 的 Requirements 表（Python 3.12+ / uv / JDK 21+）没有 Node.js/npm。
  只读用户按 README workbench 段走到 `uv run dexatlas-workbench` 时，若机器没有 npm，
  会得到 `sys.exit` 的报错（[__main__.py:67](../../src/dexatlas/workbench/__main__.py)）——
  报错信息本身清楚（含 `npm install --prefix ...` 提示），但前置要求应写进 Requirements。
- [install.md:126](../install.md) 在「Analyse an APK」段才提 `scripts/fetch-fixtures.sh`，
  [CONTRIBUTING.md:39-44](../../CONTRIBUTING.md) 的开发设置完全没有提。新贡献者跑
  `uv run pytest` 会看到 `1260 passed, 27 skipped`，不知道 27 个 skip 是「没跑 fixtures」
  而非「平台不支持」——CLAUDE.md 明确告诫「skip 不是 pass」。
**修法：** install.md Requirements 加一行 Node.js（含用途：仅构建 workbench 前端）；
CONTRIBUTING 的 Development setup 加 `bash scripts/fetch-fixtures.sh` 一步。

### P3-1 `docs/status.md` 与 `docs/HANDOVER.md` 的 M4 状态不同步

[HANDOVER.md:30](../HANDOVER.md) 说 M4「**not started**」；[status.md:220](../status.md)
与 CHANGELOG 已记录三屏建成。两份「现在在哪」的文档互相矛盾（HANDOVER 自称锚定
`handover-2026-11-10` tag，彼时为真，但现在读者无法分辨）。
**修法：** HANDOVER 加一行「M4: three of eight screens built since this tag; see status.md」。

### P3-2 CI job 数表述（6 个）与 workflow 实际结构需对齐说明

[status.md:25](../status.md) 说「CI 6 个 job」，[.github/workflows/ci.yml](../../.github/workflows/ci.yml)
的顶层 job 是 `lint / test(3.12,3.13 矩阵) / test-partial-backends / m3-comparison / docker /
security`——按「命名 job」数是 6 个，但 `test` 是双 Python 矩阵，实际并行运行数更多。
表述不算错，但「六个 job 全绿」的口径容易让读者数不上。**修法（可选）：** 在 status.md
标注「test 为 3.12/3.13 矩阵」。

### P3-3 `version-claims` 的两个既有 findings 未闭环

`check-version-claims.py --base auto` 报告两处（检查器自己标注「already in b5000103」）：
`docs/releases/phase1-acceptance-2026-10-21.md:63`（提及尚未存在的 v0.2.0 tag）与
`docs/status.md:67`（说「v0.1.3 未发布」，而 tag 已存在）。M4 退出标准虽只约束 README，
但「版本陈述与仓库一致」是本项目自己的门禁。**修法：** 归入 Phase 2 收尾的文档修订。

### P3-4 WORKSPACE 快照路径泄露为绝对路径（低危信息暴露）

`GET /api/health` 返回 `"workspace":"E:\\Dexatlas\\...\\.dexatlas"`，浏览器面板页眉也显示
完整绝对路径。单机工具场景可接受，但 [install.md:205-206](../install.md) 说 API「redacts the
server's own directories from its error messages」——健康检查与页眉与该承诺不一致。
**修法（可选）：** health 只返回 workspace 的目录名或相对标记。

---

## 5. 建议的最小修复清单

按「让 M4 退出标准可被诚实宣布」排序；均为文档或少量代码改动，不含屏 2/屏 8 的功能开发
（那是其他会话的任务）。

1. **（随屏 2/屏 8 落地）** 在 workbench 三屏描述后更新 [README.md](../../README.md) /
   [README.zh-CN.md](../../README.zh-CN.md) / [workbench.md](../architecture/workbench.md) 的屏幕状态表，
   并用一次真实「上传 → 分析 → 检索 → 证据 → 导出」浏览器演练替换本报告 §1.2 的位置。
2. **改 README 状态横幅**（P1-2）：中英双语，把「MCP / workbench 未实现」改成准确的
   Phase 2 进度陈述。改动点：[README.md:24-28](../../README.md)、[README.zh-CN.md:14-18](../../README.zh-CN.md)。
3. **改 workbench.md 的 E-0003 示例**（P2-1）：[workbench.md:138](../architecture/workbench.md)。
4. **补 Node.js/npm 到 install.md Requirements**（P2-2a）：[install.md:6-14](../install.md)。
5. **CONTRIBUTING 开发设置补 fixtures 步骤**（P2-2b）：[CONTRIBUTING.md:34-49](../../CONTRIBUTING.md)。
6. **同步 HANDOVER 的 M4 状态**（P3-1）：[HANDOVER.md:30](../HANDOVER.md)。
7. **（可选）** status.md CI 口径注记（P3-2）；health/页眉去绝对路径（P3-4）；闭环两条
   version-claims findings（P3-3）。

---

## 6. 复现命令汇总

```bash
# 环境（worktree 内）
uv sync --extra dev --extra analysis --extra mcp --extra demo
export DEXATLAS_JADX_PATH="<jadx>/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="<path>/apktool.jar"

# §1.1 CLI 链路
uv run dexatlas backends
uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas search apk_80a8fe0e81204c9f "Crypto"
uv run dexatlas manifest apk_80a8fe0e81204c9f
uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;"
uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json

# §1.1 workbench / API / MCP
uv run dexatlas-workbench            # http://127.0.0.1:8618，首启自动 npm build
uv run uvicorn dexatlas.api.app:app --port 8801
curl -s -X POST -F "file=@examples/demo-app/demo.apk" http://127.0.0.1:8000/analyze
uv run --no-sync python examples/mcp_client.py

# §1.3 / §2 证据
curl -s "http://127.0.0.1:8618/api/projects/apk_80a8fe0e81204c9f/evidence/E-0004"
python - <<'PY'
import sqlite3, json
c = sqlite3.connect('.dexatlas/dexatlas.db')
for r in c.execute("SELECT id, kind, provenance FROM evidence WHERE project_id='apk_80a8fe0e81204c9f'"):
    print(r[0], r[1], [p['tool'] for p in json.loads(r[2])])
PY

# 门禁
uv run --no-sync pytest -q                 # 1260 passed, 27 skipped (fixtures)
uv run --no-sync ruff check . && uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync python scripts/check-doc-citations.py
uv run --no-sync python scripts/check-version-claims.py --base auto
uv run --no-sync python scripts/refresh-report-figures.py --check
```

浏览器实测路由（三屏）：
`#/`、`#/projects/apk_80a8fe0e81204c9f/search`、
`#/projects/apk_80a8fe0e81204c9f/calls?method=<URL-encoded method id>`。
