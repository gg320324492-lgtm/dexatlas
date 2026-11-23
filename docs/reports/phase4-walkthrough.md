# Phase 4 M15 独立用户 walkthrough（README 全链路实测）

**日期：** 2026-11-23 · **阶段：** Phase 4（[执行单](../roadmap/phase4-plan.md)）· **里程碑：** M15 第一步 — 独立用户 walkthrough
**基线树：** GitHub `main` @ `22c0621`（干净 clone，不含工作分支 `claude/youthful-clarke-db2263-wt` 上尚未合入的 M14 两个提交）
**执行环境：** Windows 11 Pro，Git Bash；uv 0.11.21；Node v24.16.0 / npm 11.13.0；系统 Python 3.12（仅系统级存在，全程未用于运行 DexAtlas）
**方法：** 模拟零上下文真实用户，严格按 README.md（英文版，主测对象）与 README.zh-CN.md（中文版，一致性核对）的公开步骤，在干净目录 `E:\labcairn-local\tmp\opencode\m15-walkthrough\dexatlas-walk\` 走完整链路。所有命令逐条执行，输出留存于该目录 `walkthrough-out/`（不入库）。发现缺陷只记录，不修复。

---

## 0. 结论

**通过（有 4 项低危发现，均不阻断链路）。**

README 快速开始的每一条命令在干净 clone 上按原文执行成功，无一步卡死；后端可选性、报告三格式、证据包、`runs`/`render`（C8）、REST API、Workbench 八屏、agent 成功流与 `503 agent_not_configured` 拒绝流全部按文档兑现。发现的问题集中在「文档与实现的边角不一致」与「Windows 首次启动体验」，没有一处导致用户走不下去。

---

## 1. 逐步实测记录

以下每步均为实际执行结果；「与文档一致」指与 README.md / README.zh-CN.md / docs/install.md 的说法核对。

### 1.1 clone

- 命令：`git clone https://github.com/gg320324492-lgtm/dexatlas.git dexatlas-walk`
- 结果：成功。HEAD = `22c0621`（`main`），与 README 徽章/状态所指的发布树一致。
- **发现 F1（信息性）：** 工作分支上已合入的 M14 修复（`6dbc9a3` TaskStore Windows 并发写加固、`acb9f0b` 可访问性补齐）尚未在 `main` 上，真实用户 clone 到的是没有这两个修复的树。这不违反任何声明（README 未承诺未发布分支的内容），仅作为 Phase 4 进度事实记录。

### 1.2 安装（README 快速开始第 1 条）

- 命令：`uv sync --extra analysis`
- 结果：成功，生成独立 `.venv`（220 MB）。
- 与文档一致：README 说「the first command works the moment the clone is in place」，属实。

### 1.3 后端发现（README 第 2 条）

- 命令：`uv run dexatlas backends`（未装后端时）
- 结果：jadx/apktool 显示 `not installed`，androguard `available 4.1.4`，退出码 0，并明确提示「2 backend(s) unavailable. Analysis continues...」。
- 与文档一致：README「Backends are optional and independent」「a missing backend is a normal state」属实。

### 1.4 安装后端（docs/install.md 路径）

- 命令：`bash scripts/install-backends.sh`
- 结果：成功下载 JADX 1.5.2 与 Apktool 2.11.1 到 `%TEMP%/dexatlas-backends`（147 MB）。
- **发现 F2（文档可用性，低危）：** install.md 正确警告了「脚本内的 export 不影响你的 shell，需自行设置 `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR`」，但脚本运行结束时的输出只有两行版本号（`jadx 1.5.2` / `apktool 2.11.1`），**没有把需要复制的两行 export 打印出来**——install.md 正文说「Copy the two lines it prints into your own shell」，而脚本实际不打印这两行。用户必须回读文档才能拼出：

  ```bash
  export DEXATLAS_JADX_PATH="$TMPDIR/dexatlas-backends/jadx/bin/jadx.bat"   # Windows: bin\jadx.bat
  export DEXATLAS_APKTOOL_JAR="$TMPDIR/dexatlas-backends/apktool.jar"
  ```

  建议：让 `install-backends.sh` 结束时打印这两行（或打印 install.md 所述内容），使文档与脚本行为一致。
- 设置两个变量后 `uv run dexatlas backends` 显示三后端全部 available，与 README 快速开始示例表格一致（jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4）。

### 1.5 首次分析（README 第 3 条）

- 命令：`uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json --html report.html`
- 结果：5.3s 完成，5 classes / 8 methods / 23 call sites / 21 call edges / 12 evidence records；三种格式报告均生成。
- 与文档一致：报告头部逐字出现 README 承诺的字段（SHA-256、Run id、Tool versions、Evidence levels 三级、backend errors 区块）；「Index completeness: complete」。
- **附带核验（无后端降级路径）：** 清空两个环境变量后对 `strings.apk` 重跑 `analyze`，退出码 0，报告出现「Backend errors」区块并列出 `apktool (not_installed)` / `jadx (not_installed)`，正文「These steps did not complete. Results that depend on them are absent, not clean.」——README「a backend that fails is reported as a value, not a crash」属实。

### 1.6 只读命令（README 第 4–6 条）

- `manifest` / `search` / `xrefs` 全部成功；README 的 xrefs 示例方法 `com.example.demo.MainActivity.describe(...)Ljava/lang/String;` 返回 1 call site / 1 call edge，带 `classes.dex@34` 字节偏移定位。
- `--workspace`/`-w` 选项实测存在且可用（install.md M8-2 修复属实）。
- 中文 README 的 xrefs 示例用的是占位符 `com.example.Foo.bar(...)V`，实测返回「No callers of ...」正常空结果，不报错。属可接受的占位写法，不算缺陷。

### 1.7 C8：`runs` / `render`（README 第 7–8 条）

- `runs apk_...`：列出 run_ed51ded3176c4f66（completed / complete / published）。
- `render apk_... run_ed51ded3176c4f66 -o rendered-run/`：生成 `run.json` + `evidence/evidence-package.zip`（3 reports + manifest.json，4 files）；CLI 输出自带的 `verify_package` 复核通过（VERIFY_OK）。
- 与文档一致：中英两版 README 快速开始均已包含这两条命令（中文版由 c3c5026 补齐），描述与实测一致。

### 1.8 fixtures（README「Larger test fixtures are fetched with scripts/fetch-fixtures.sh」）

- 命令：`bash scripts/fetch-fixtures.sh`
- 结果：成功拉取 TestActivity.apk（174,896 B）与 multidex.apk（1,233 B）到 `fixtures/apk/`，附 SOURCES.md。
- 与文档一致。

### 1.9 REST API（README「The REST API is the same analysis core over HTTP」）

- 命令：`uv run uvicorn dexatlas.api.app:app --port 8616`，`/health` 返回 `{"status":"ok","version":"1.0.1",...}`，`/docs` 200。
- 逐项核验：`GET /projects`、`GET /projects/{id}`、`GET .../search?q=`、`GET .../manifest`、`GET .../report?format=markdown`（与 CLI 报告同内容同字节数级别）、`GET .../evidence`（12 条）全部 200。
- `DELETE /projects/{id}` 返回 204 且列表相应减少——install.md 端点表与实现一致。
- **发现 F3（文档口径，低危）：** install.md 的 API 表写的是**REST API（`dexatlas.api.app`）**的路径（`/projects/{id}/classes`、`/uploads` 系列等），而 Workbench（`dexatlas.workbench.app`）是**另一套以 `/api/` 为前缀的子集**（`/api/projects/{id}/symbols`、`/api/projects/{id}/source/class` 等；OpenAPI 实测两套路径不同）。README 只说 Workbench「sits on the same eleven tools ... called in-process——the JSON the browser receives is the shape the MCP server would have returned」，没有声称两套 HTTP 路径相同，因此**不构成对外承诺冲突**；但一个从 install.md API 表跳到 Workbench 的读者会预期同名路径。建议在 install.md 该表附近加一句「Workbench serves its own `/api/...` subset — see docs/architecture/workbench.md」，指明这是另一张表。

### 1.10 Workbench（README「The web workbench」）

- 命令：`uv sync --extra dev --extra analysis --extra mcp --extra demo` → `uv run dexatlas-workbench --port 8619`
- 首次启动自动 `npm install` + `vite build`（约 40s），随后 `serving the workbench on http://127.0.0.1:8619`，与 README「The first start builds the front end (npm once)」一致。
- **发现 F4（Windows 首启体验，低危）：** 本机 8618 端口被另一个 DexAtlas 实例（主 checkout 侧的常驻 Workbench）占用，干净 clone 首启得到清晰报错「port 8618 ... already in use; pass --port <other> ...」，换 `--port 8619` 一次成功。README 只写了默认端口 8618，没有写「被占用时用 `--port` 换端口」；报错信息本身已足够自救，故仅记录为已知体验点，不算文档缺陷。另：两个 Workbench 进程若指向同一工作区会共享项目列表（实测 8618 旧进程能看到干净 clone 写入的 `strings.apk` 项目，因为两者 DEXATLAS_WORKSPACE 都解析到各自 cwd 的 `.dexatlas` 之外的同名相对路径场景不存在——实测共享是因旧进程的工作区恰为新 clone 目录的父级链上同名目录；换 8619 后项目列表完全隔离，仅含本 clone 的 demo.apk，符合「workspace 是启动目录相对路径」的预期）。
- UI 实测（浏览器逐屏）：
  - 项目列表：UPLOAD AN APK 表单 + 项目表（状态/类/方法/调用点/调用边/证据计数）正常。
  - **上传分析流：** `POST /api/analyze`（multipart 字段名 `file`）上传 `strings.apk` → 202 pending → 轮询至 completed（1 class / 10 methods / 6 evidence），前端项目表同步更新。README「upload an APK from the project list and the analysis runs with the same pipeline」属实。
  - **search & evidence：** 搜 `crypto` 返回 6 条（1 class + 3 methods + 2 strings），点开 `Crypto` 类显示 JADX 反编译 Java 源码，provenance locator `jadx:sources/...` 点 resolve 展开为工作区内真实文件路径与源码——证据可回溯到字节级位置，README 核心承诺兑现。
  - **call graph：** 选择 `Crypto.sign` 后显示 1 caller / 3 callees、call sites in/out、call edges in/out，CALLERS 表逐行给 opcode/DEX/offset/locator，CALLEES 按直接/虚拟调用分类——与 README「who calls this method, and what it calls ... each row is a place in the bytecode」一致。
  - **agent workspace（未配置态）：** 页面明示「NO MODEL ENDPOINT IS CONFIGURED」及所需三个环境变量；`POST /api/projects/{id}/agent/tasks` 返回 `503 {"code":"agent_not_configured"}`——README 的 503 拒绝承诺逐字兑现。
  - **agent workspace（成功流）：** 设置 `DEXATLAS_AGENT_BASE_URL=http://127.0.0.1:3425/v1`、`DEXATLAS_AGENT_MODEL=group/free`、`DEXATLAS_AGENT_PROVIDER=openai-compatible` 后重启 Workbench（8622），`/api/agent/config` 返回 configured；提交问题「What does this APK do? Name its main components.」→ pending → running → completed（约 12s，2 iterations，18 tool calls，8,437 tokens，预算 120,000/16/120s 内）。报告 JSON 含 `sections: established/leads/insufficient`、7 findings（2 verified + 5 lead）、4 limitations、逐条 provenance（apktool:AndroidManifest.xml 等）。README「separated into what was established, what is a lead, and what is not established」与「a model's output is a lead and can never be promoted to a finding」兑现（本次 lead 未被提升，limitations 如实列出「manifest 没有应用名」「MainActivity/SyncService 具体行为未确证」等）。
  - **报告导出：** CLI `export` 对上传的 strings.apk 生成 4 文件证据包；`runs` 显示该 run published。

### 1.11 中文 README 一致性核对

- 快速开始九条命令与英文版逐条对应（含 runs/render）；Workbench/Agent 章节与英文版同构；M5/M6/M8/M9/M10 状态行与英文版口径一致（M6「已完成（B1 验收线已于 2026-11-22 达成）」、M8「交付完成（macOS 未验证）」、M10「已通过（2026-11-20）」）。
- 徽章、安装捷径（uv/Docker/pipx）、fixtures 说明、agent 环境变量三件套说明均一致。

---

## 2. 与 README 状态声明的一致性核验

| README 声明 | 实测 | 判定 |
|---|---|---|
| Quick start 每条命令开箱即跑 | 1.2–1.7 全部成功 | 一致 |
| Backends optional；缺后端仍出报告并记录缺口 | 1.3、1.5 降级路径 | 一致 |
| `runs` / `render`（C8）在快速开始中且可用 | 1.7 | 一致 |
| REST API = same analysis core；/docs 可用 | 1.9 | 一致 |
| Workbench 首启 npm 一次；默认 8618 | 1.10（换端口成功） | 一致（F4 记录） |
| agent 未配置 → 503 agent_not_configured，不由替身模型回答 | 1.10 | 一致 |
| agent 报告三分区 + lead 不提升 + limitations 披露 | 1.10 成功流 | 一致 |
| 证据 locator 可解析到分析内真实位置 | 1.10 search & evidence | 一致 |
| M8 = delivered (macOS unverified)，属已知限制 | README 三处 + status.md + ROADMAP 口径统一 | 一致 |
| M6 = done（B1 于 2026-11-22 达成；DeepSeek 56/60=93.3%），历史未达标轮次如实保留 | README 状态表与基准列表逐项核对 | 一致 |
| M10 = passed（2026-11-20），验收材料已移除 | README M10 行 | 一致 |
| MCP server = eleven read-only tools | `src/dexatlas/mcp/server.py` 实数 11 个 Tool 注册 | 一致 |
| README「server is read-only: never writes, never runs a shell」 | MCP server.py 无写/执行工具注册 | 一致 |

---

## 3. 发现清单（按严重度）

| # | 严重度 | 位置 | 现象 | 建议 |
|---|---|---|---|---|
| F1 | 信息 | 仓库分支状态 | `main`@`22c0621` 尚未包含工作分支的 M14 两提交（TaskStore Windows 并发加固、a11y 补齐） | 随 M14 收口合入，无需单独动作 |
| F2 | 低（文档可用性） | `scripts/install-backends.sh` ↔ `docs/install.md` | install.md 称脚本「prints the two lines」export，脚本实际只打印两行版本号，未打印需复制的 `DEXATLAS_JADX_PATH`/`DEXATLAS_APKTOOL_JAR` export | 脚本结束时打印这两行，或改 install.md 措辞 |
| F3 | 低（文档口径） | `docs/install.md` API 表 ↔ Workbench | install.md 表是 REST API 路径；Workbench 另有一套 `/api/...` 子集，两套路径名不同（实现各自自洽，README 未承诺相同） | install.md 表旁加一句指向 workbench.md 的区分说明 |
| F4 | 低（体验） | `dexatlas-workbench` | 默认端口被占时报错清晰、可换 `--port` 自救；README 未提换端口 | 可选：README/workbench.md 加一行「port busy → --port 0」 |

无高危发现；未发现对外契约被违反；未发现 README 声称了不存在的能力。

---

## 4. 边界与未尽事项

- 本 walkthrough 覆盖 README 公开步骤；未运行测试套件、未重测基准数字、未验证 Docker 镜像与 pipx 路径（属 M8/M10 已有验收范围）。
- agent 成功流使用本机 OpenAI 兼容网关（group/free）实测一次；模型质量波动不代表验收结论，M6 验收线以既有基准记录为准。
- 截图取证未纳入本报告（M13 已有 22 张 UI 截图覆盖同一批屏幕）；本报告以命令输出与 API 响应为证据。
- macOS 未验证是既有已披露限制，本窗口无 macOS 环境，维持该披露不变。

---

## 5. 给后续里程碑的输入

1. F2 的脚本输出修复是一行级改动，适合并入任一后续清理提交（需按纪律配回归测试）。
2. F3 的区分说明是纯文档改动，可与 F2 同批处理。
3. M15 后续步骤（若按执行单推进）可直接复用本目录的命令序列与 `walkthrough-out/` 产物结构。
