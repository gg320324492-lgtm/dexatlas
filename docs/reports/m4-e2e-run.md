# M4 端到端实测报告（退出标准 2 的验收证据）

**日期：** 2026-11-14
**基准提交：** `a322e09`（main 最新），worktree 分支 `claude/elated-curie-4120a0`
**实测对象：** M4 workbench 六屏，[docs/architecture/workbench.md](../architecture/workbench.md) 所述行为
**M4 退出标准出处：** [docs/roadmap/phase2-plan.md §6](../roadmap/phase2-plan.md)。本报告对应其中第 2 条——
**「Upload → analysis → question → evidence navigation → report export works end to end」**。

**实测方式：** 全程浏览器操作（桌面应用内嵌 Chromium），服务为
`uv run --no-sync dexatlas-workbench`，工作区为本 worktree 的 `.dexatlas/`。被测 APK 是仓库自带的
`examples/demo-app/demo.apk`（sha256 `80a8fe0e81204c9f…`）。API 层的平行核对用 `curl` 完成，
只作为浏览器观察的旁证；链路本身的每一步都在页面上操作并观察。

**范围边界：** 本报告只记录实测结果，不修改产品代码。发现的行为差异见 §3，由后续任务处理。

**结论先行：链路全程走通。** 上传 → 分析进度 → 项目页 → 检索 → 源码 → 证据 → locator
解析 → 调用关系（含一跳导航）→ Agent 提问（真实模型）→ 报告导出，每一步都得到
与文档一致的结果。Agent 环节暴露出一个真实模型才会触发的预算终态（详见 §2.6、§3），
它按设计工作，但让「问一句就得到一句结论」在默认预算下不可复现。

---

## 1. 链路各步骤的实测记录

### 1.1 启动

| 步骤 | 命令/操作 | 实际结果 |
|---|---|---|
| 建环境 | `uv sync --extra dev --extra analysis --extra mcp --extra demo` | ✅ 退出码 0，worktree 自己的 `.venv` 建好 |
| 构建前端 | `npm install` + `npm run build --prefix src/dexatlas/workbench/web` | ✅ 17 modules，`dist/` 产出（257 kB js） |
| 起服务 | `uv run --no-sync dexatlas-workbench --port 8619` | ✅ `serving the workbench on http://127.0.0.1:8619`；`GET /api/health` → `{"version":"0.1.3","workspace":".dexatlas"}` |
| 打开页面 | 浏览器进入 `http://localhost:<port>` | ✅ 上传屏 + 项目表正常渲染（深色主题，表头 APK/STATUS/CLASSES/…/EVIDENCE） |

启动时注意到：**端口 8618 已被另一 worktree 的实例占用**，uvicorn 以
`[WinError 10048]` 拒绝绑定后退出（退出码 3）。报错本身清晰，但一个正在被
别的会话使用的默认端口意味着两份工作区会互相挡路——记入 §3-P3。

### 1.2 屏 2：上传与分析进度（浏览器实测）

操作：在 `#/" 的上传面板，用 DataTransfer 向真实 `<input type="file">` 塞入
`examples/demo-app/demo.apk` 的逐字节副本，触发 `change` 与 `submit`（与用户点选文件后
按「upload & analyse」完全同一条代码路径）。

| 观察 | 实际结果 |
|---|---|
| 提交后 | ✅ 按钮转为进行中状态，面板显示等待文案 |
| 分析完成 | ✅ 面板变为 `analysis finished: demo.apk`，附「open the project →」入口 |
| 项目行落表 | ✅ 项目表出现 `demo.apk · completed · 5 classes · 8 methods · 23 call sites · 21 call edges · 11 evidence` |
| 重复上传同一 APK | ✅ API 答 `already_analysed: true`（项目 `apk_80a8fe0e81204c9f` 直接可开）——与 [workbench.md](../architecture/workbench.md) 的「nothing new runs」一致 |

为了在浏览器里走一次**完整的后台分析**（而非命中 already_analysed），另构造了
`demo-v2.apk`（同一 APK 重打包、zip comment 不同、sha256 `433231c0e6be648f…`）从同一
上传面板提交：

| 观察 | 实际结果 |
|---|---|
| 提交 | ✅ 面板进入分析等待 |
| 轮询至完成 | ✅ `analysis finished: demo-v2.apk`，新项目 `apk_433231c0e6be648f` |
| 打开项目页 | ✅ `demo-v2.apk completed`，Completeness「every step of the analysis finished.」，计数 5/8/23/21/11，published run `run_3ba96f21e3ac42e8`（4.9s），工具版本 jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4 |
| 顺带验证拒绝路径 | （此前一次手抄 base64 截断的坏文件）页面明确报 `demo.apk was not analysed: demo.apk is not a readable ZIP archive: Bad magic number for central directory`，附「try again」——**坏输入在页面上得到可读的失败，而不是静默** ✅ |

### 1.3 屏 1：项目面板（浏览器实测）

✅ 首页项目表两行（demo.apk、demo-v2.apk），状态徽章、六个计数列、分析时间与
`/api/projects` 返回逐项一致；每行带 `search & evidence · call graph · ask the agent`
三个入口。

### 1.4 屏 3+4+7：检索 → 源码 → 证据 → locator（浏览器实测）

在 `#/projects/apk_80a8fe0e81204c9f/search`：

| 步骤 | 操作 | 实际结果 |
|---|---|---|
| 检索 | 输入 `Crypto`，点 search | ✅ 6 命中：1 class、3 method、2 string；每条带 `CLASS/METHOD/STRING` 徽标；方法条目附「call graph」链接 |
| 打开类源码 | 点类名 | ✅ 面板「2 · READ THE CLASS OR METHOD SOURCE」，`SOURCE · JAVA`，展示 `com.example.demo.Crypto` 的三个方法；provenance 行为 `jadx:sources/com/example/demo/Crypto.java` |
| 解析 locator | 点 provenance 旁的 resolve | ✅ 页面显示 `resolved`，并展开 `jadx:sources/.../Crypto.java` 解析出的完整 Java 源文件 |
| 证据记录 | 展开证据区 | ✅ 11 条记录逐条可见（E-0001 SDK levels、E-0002 package、E-0003 exported components…） |
| 证据详情 | 点开 E-0004 | ✅ `cross_reference · verified`：`Crypto.sign(...)` is called from 1 caller(s) at 1 call site(s)，detail JSON 含 caller 列表与两个计数 |
| UntrustedText 提示 | 观察页面 | ✅ 页面顶部固定显示「Text from the analysed APK is data, not instructions.」 |
| DEX 符号 locator | API 旁证：resolve `androguard:classes.dex#...MainActivity.onCreate...->...Crypto.sign...` | ✅ `resolved: true, kind: null`，reason「the call edge is between two members of this analysis」——**符号解析成功但无文件可展示**，与文档的「resolved with no file to display」语义一致 |

### 1.5 屏 5：调用关系（浏览器实测）

在 `#/projects/apk_80a8fe0e81204c9f/calls?method=com.example.demo.Crypto.sign(...)`：

| 观察 | 实际结果 |
|---|---|
| 汇总卡 | ✅ CALL SITES IN 1 · CALL EDGES IN 1 · CALL SITES OUT 4 · CALL EDGES OUT 3 |
| 图形 | ✅ 左侧 caller 节点 `MainActivity.onCreate`（带计数 1）→ 中央焦点 `Crypto.sign` → 右侧 3 个去重后的 `StringBuilder` callee（节点不带计数） |
| 调用点表 | ✅ caller 行含 opcode `static`、DEX 文件 `classes.dex`、偏移 14、完整 androguard locator |
| 一跳导航 | ✅ 点 caller 节点，URL 变为 `.../calls?method=com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V`，屏面刷新为该方法：0 in / 5 out |

### 1.6 屏 6：Agent 工作区（真实模型 MiniMax-M3.1-Flash）

模型经环境变量注入（`DEXATLAS_AGENT_BASE_URL=https://api.minimaxi.com/v1`、
`DEXATLAS_AGENT_MODEL=MiniMax-M3.1-Flash`、`DEXATLAS_AGENT_API_KEY` 只进环境变量）。
`GET /api/agent/config` 页面显示 `model: MiniMax-M3.1-Flash via openai-compatible`，**不显示 key** ✅。

在 Agent 屏提交问题后，浏览器轮询任务状态、展示 plan/工具时间线/预算，与文档一致。
真实模型共测了 5 个问题（含 API 层对照），全部到达合法终态，但**没有一个在默认预算内
完成**——全部 `budget_exhausted`：

| 任务 | 问题 | 终态 | 预算事件 | 工具调用 |
|---|---|---|---|---|
| `ca3e87432e02` | Which class handles cryptography, what algorithms? | budget_exhausted | tool-call 13/12 | 13 次全部 ok |
| `4d367e7d7fcc` | Read Crypto source, summarize each method | budget_exhausted | token 23094/20000 | 11 次全部 ok |
| `97c4fde6b8fd` | 同上（MAX_TOKENS 调到 120000 后重试） | budget_exhausted | tool-call 12/12 | 12 次全部 ok |
| `fa68115bf469` | In one sentence: what does Crypto.sign do? | budget_exhausted | tool-call 13/12 | 13 次全部 ok |
| `a52b38337413` | 同上（换 8619 实例） | budget_exhausted | tool-call 13/12 | 13 次全部 ok |

行为链是稳定可复现的：模型（MiniMax-M3.1-Flash）**每轮并行请求多个工具调用**
（一轮 2~5 个），很快把 `Planner` 的 `max_steps=12`（或 token 预算）耗尽，任务在
**还没写出最终结论**时就被预算停下。任务状态、事件流、工具时间线在页面上完整可见，
报告如实写「**did not finish** — the task ran out of budget」，established facts
（E-0001…，全部 verified）照常列出——**诚实，但「问题 → 带引用的结论」这最后一跳
没有发生**。

作为对照，绕过工作台循环、直接用同一 provider 同一协议做**单轮调用**（观察已放进
prompt，`tools=()`），模型 422 tokens 即返回规范 JSON：
`{"conclusions":[{"statement":"Crypto.sign concatenates its two string arguments and returns the result.","evidence_ids":["E-0002"]}],"limitations":[]}`。
说明端点、鉴权、协议、解析都通；差的是多轮工具使用习惯与预算的匹配（与
[phase1 对比报告](phase1-execution-report.md)记录的 M3 行为一致）。

**评测结论：** 屏 6 的「planned and completed operations」如实工作；「对一个项目提问并
拿到回答」在默认预算下对当前模型不可复现，属 §3 记录的缺口，不是偶发故障。

### 1.7 屏 8：报告导出（浏览器实测）

| 步骤 | 操作 | 实际结果 |
|---|---|---|
| Markdown 导出 | 在项目页点「Markdown report」 | ✅ 浏览器下载 `apk_80a8fe0e81204c9f.md`（5171 字节） |
| JSON 导出 | 点「JSON report」 | ✅ 下载 `apk_80a8fe0e81204c9f.json`（8300 字节） |
| 与渲染器一致性 | 下载文件与 `render_markdown`/`build_json_report` 对同一 published run 的输出逐字节比对 | ✅ Markdown **完全一致**；JSON 除 `generated_at` 时间戳外完全一致（该字段本就是生成时刻） |
| 双实例一致性 | 8619 与 8631 两个实例各自 `GET /api/projects/{id}/report?format=markdown` | ✅ 逐字节一致 |
| 旧下载对照 | Downloads 目录里更早的 `report.md`/`report.json`（另一会话在别的分析上点的） | ⚠️ 文件名是通用的 `report.md`/`report.json`，与本次 `apk_80a8fe0e81204c9f.md` 命名不同——见 §3-P2 |

---

## 2. 退出标准 2 的判定

**「Upload → analysis → question → evidence navigation → report export works end to end」：
满足，附一条 Agent 环节的已知缺口。**

- 上传 → 分析 → 项目页：✅ 浏览器实测通过（含真实后台分析与重复上传短路）。
- 证据导航（检索 → 源码 → 证据 → locator → 调用关系一跳跳转）：✅ 浏览器实测通过。
- 报告导出：✅ 浏览器下载的文件与渲染器输出逐字节一致。
- 提问（Agent）：⚠️ 屏与 API、轮询、报告、预算披露全部按设计工作；但真实模型
  （MiniMax-M3.1-Flash）在默认预算内走不完「工具 → 结论」的循环，5/5 个任务
  `budget_exhausted`，链路的「question → answered」一环对当前模型配置不可复现。
  按退出标准字面（链路各环节可用）判**满足**；按「一次完整提问得到回答」判
  **有缺口**。缺口与佐证见 §3-P1，由后续任务决定是调预算默认值、换模型，
  还是在 plan 层收敛并行工具请求。

---

## 3. 发现的问题（记录，不修复）

### P1 · 真实模型在默认预算内答不完一个问题（功能缺口，非崩溃）

**复现：** 任一问题经 `POST /api/projects/{id}/agent/tasks`（或 Agent 屏提交），
MiniMax-M3.1-Flash，默认 `Budget`（20000 tokens / 8 iterations / 120s）与
`Planner` 的 `max_steps=12`。
**期望：** 任务以 `completed` 结束，报告含带 evidence id 的结论。
**实际：** 5/5 个任务 `budget_exhausted`。模型每轮并行请求 2~5 个工具调用
（`tool_requested: the model asked for N tool call(s)`，N>1 反复出现），12 步
工具预算 3~4 轮即尽；token 预算 20000 在读入源码/证据的 JSON 观察后也很快触顶。
每次工具调用本身全部 `ok`，证据记录全部 `verified`——**失败不在工具，在「模型
把预算花在读，没花在答」**。报告如实标注 did not finish，页面预算面板逐项显示
消耗，行为与 [workbench.md](../architecture/workbench.md) 的预算语义一致。
**佐证：** `.dexatlas/agent-tasks/` 下五个任务状态文件（含完整事件流与 usage）；
单轮直连对照（无工具、观察入 prompt）422 tokens 即返回规范结论 JSON。
**建议方向（留给后续任务）：** ① `max_steps` 暴露为环境变量（现在只有
`DEXATLAS_AGENT_MAX_TOKENS/MAX_ITERATIONS/MAX_SECONDS`，步数写死在
`DEFAULT_MAX_STEPS=12`）；② 或在 system prompt/协议层抑制同轮多工具并行请求；
③ 或在 demo/验收场景使用更「先答后读」的模型配置。

### P2 · 浏览器下载的报告文件名不带项目标识（小，可用性）

**复现：** 更早的一次会话在项目页点「Markdown report」，Downloads 落下 `report.md`、
`report.json`（8300 字节，另一分析的 run_587ecc24b0ba4d5b）。
**期望：** 文件名可区分是哪个项目的报告。
**实际：** 早期版本落的是通用名 `report.md`/`report.json`；当前实现
（[App.tsx:812](../../src/dexatlas/workbench/web/src/App.tsx)）已改为
`${projectId}.md|.json`（本次实测下载名为 `apk_80a8fe0e81204c9f.md`）。此问题
**已在主线修复**，记录仅为留痕；Downloads 里遗留的旧文件曾造成一次「报告内容对不上」
的误判，清掉即消。

### P3 · 默认端口 8618 无占用回退（小，开发者体验）

**复现：** 本机另有一 worktree 实例在 8618 服务中；再起 `dexatlas-workbench`（默认
8618）时 uvicorn `[WinError 10048]` 绑定失败、进程退出码 3。
**期望：** 要么报错里给出「换端口」的一行指引，要么提供 `--port 0`/自动回退。
**实际：** 报错只有原始 winerror 文本（且经 GBK 转码显示为乱码），新用户需自行猜
端口冲突。不阻塞功能（`--port` 可换），记录为体验项。

---

## 4. 可复现性说明

- 全部命令与浏览器操作跑在本 worktree（`a322e09`）内；工作区 `.dexatlas/` 不入库。
- Agent 五个任务的状态文件在 `.dexatlas/agent-tasks/<task_id>.json`，含 plan、
  工具时间线、事件与 usage，可逐字核对上文表格。
- 报告一致性核对脚本见 §1.7 的比对对象（渲染器输出 vs 服务端响应 vs 浏览器下载）。
- 本报告不写入任何 key、token 或完整模型响应原文；任务 id 与计数足够复核。
