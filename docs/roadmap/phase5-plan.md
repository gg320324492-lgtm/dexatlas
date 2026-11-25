# Phase 5 执行单 — 桌面应用自包含与阶段级可观测

**日期：** 2026-11-25 · **性质：** 新阶段执行单 · **状态：** 待作者批准后实施
**上游：** [phase4-q2-closure.md](phase4-q2-closure.md)（部分解冻 B）、[v1.1.0-candidates.md](../reports/v1.1.0-candidates.md)（C12 等外部条件）
**作者指示（2026-11-25）：** 先不正式运营，完整做完开发工作；批准四项——侧车进程真接入、阶段级进度契约、C12 外发渠道核实、发版后运营。

## 1. 这一轮解决什么

v1.1.0 交付了桌面应用的完整 UI 与真实数据链路，但两处仍是"借来的"：

1. **分析能力不在桌面应用里。** 桌面端靠 vite 代理 / Tauri HTTP 打一个
   **独立启动的** 8618 后端进程；exe 本身不含分析能力，用户拿到安装包
   仍然起不来一次分析。设计规范 §178（`desktop-app.md`）早已写明目标形态：
   **Tauri 侧车进程运行现有 DexAtlas，前端只经侧车的本地通道取数**。
2. **分析页的阶段进度是前端模拟。** 后端 runs 契约只有起止状态
   （pending/running/completed/failed/cancelled），没有阶段级事实；分析页
   五阶段时间线的中间推进是前端按时间近似出来的（页面有角标注明）。
   这一条在 v1.1.0 发布说明里如实声明了，但它是**可消除的**——
   pipeline 的阶段推进点在代码里是明确的。

同时处理两件不阻塞开发的事：C12 外发渠道核实的**仓库内备料**，
与发版后运营的**清单化**（作者明确"先不正式运行"）。

## 2. 范围

### 2.1 必须完成

| # | 工作项 | 交付物 | 验收判据 |
|---|---|---|---|
| W1 | **侧车进程真接入**：Tauri Rust 壳在应用启动时 spawn 现有 DexAtlas HTTP 服务（`python -m dexatlas.workbench` 或 `dexatlas-workbench`），把端口注入前端；进程退出/崩溃时 UI 如实呈现；前端 `defaultBaseUrl()` 优先走侧车实际端口 | Rust `lib.rs` 侧车管理、capability 更新、前端 api 适配；`desktop/README.md` 更新 | 打包后的 exe 在**不预先手动起后端**的情况下能完成 上传 → 分析 → 证据 → 导出 全链路；侧车崩溃时页面显示可读错误而非静默白屏 |
| W2 | **阶段级进度契约**：为分析 run 增加只读的阶段事实来源。pipeline 在既有阶段推进点（inspect → apktool → androguard → jadx → publish）向 run 记录阶段事件；新增只读端点 `GET /api/projects/{id}/runs/{run_id}/stages`（或并入现有 runs 详情）返回阶段列表与时间戳 | `src/dexatlas/core/runs.py`（阶段模型）、`src/dexatlas/core/pipeline.py`（推进点埋点）、`src/dexatlas/api/app.py` + `src/dexatlas/workbench/app.py`（只读端点）、契约文档同步 | 分析一次 demo.apk 后，stages 端点返回 ≥5 个阶段且顺序与 pipeline 一致；桌面分析页用真实 stages 渲染时间线，前端模拟代码删除；REST/MCP 既有契约零改动（纯新增） |
| W3 | **C12 仓库内备料**：`scope-ai-mcp.md` 压缩版（≤5,000 字符，保住验收与排除条款的完整表述）与「整篇附件 + 字段只贴 What I offer」两个方案并排，附核对表模板（字段/实测长度/门限/结论）；真实渠道核实仍等作者提供渠道与账号 | `docs/outreach/` 恢复（从 .scratch 演练副本回收）+ 压缩稿 + 核对表 | 压缩稿 ≤5,000 字符且关键条款完整；两个方案的取舍写明；核对表模板可直接填 |
| W4 | **发版后运营清单**：把"发版后运营"落成一张可执行清单（渠道、动作、负责人、频率），明确本轮**只备料不执行**（作者指示"先不正式运行"） | `docs/ops/post-release-checklist.md`（新） | 清单覆盖 release 页面检查、issue triage 节奏、反馈收集渠道、下一个版本的条件；不含任何需要作者账号的执行步骤 |

### 2.2 明确不纳入

- 不做应用商店分发、自动更新服务、签名证书。
- 不改 REST/MCP/CLI 既有契约、报告 schema、locator、状态码、退出码
  （W2 是**纯新增**只读端点；W1 是客户端行为）。
- 不做 macOS/Linux 验证（第一验收平台仍是 Windows）。
- 不新增分析后端、漏洞规则、认证、多租户。

## 3. 里程碑与并行拆分

### M1 — 侧车接入（W1）与阶段契约（W2）并行

- **窗口 A（W1 侧车）**：`desktop/src-tauri/`（Rust）+ `desktop/src/api/` +
  `desktop/src-tauri/capabilities/`；产出可独立验证的 exe。
- **窗口 B（W2 阶段契约）**：`src/dexatlas/`（runs 模型、pipeline 埋点、
  两个 app 的只读端点）+ 契约文档 + 回归测试；产出可独立验证的端点。
- 文件边界不相交；B 先行合入不影响 A（A 的前端在 W2 合入前继续用轮询 +
  模拟，合入后切换到真实 stages）。
- **汇合点**：桌面分析页删除前端模拟、改读 stages 端点（小窗口 C，依赖
  A+B 均合入）。

### M2 — C12 备料（W3）与运营清单（W4）并行

- 与 M1 无文件交集，可同批并行；均不需要作者账号。

### M3 — 真机验收与文档收口

- 打包 exe（含侧车）真机全链路；`docs/status.md`、`ROADMAP.md`、CHANGELOG
  回填；视结果决定是否发 v1.1.1 / v1.2.0。

## 4. 冻结与风险

- 本单继续"部分解冻 B"：解冻范围 = 桌面应用（`desktop/`）+ 为桌面端服务
  的**新增只读**后端能力 + 文档。核心分析逻辑只加埋点不改行为。
- **风险 1：侧车在 Windows 上拉起 Python 的路径问题。** 打包产物里没有
  Python 解释器；方案是侧车启动**用户机器上已装的** `dexatlas-workbench`
  入口（pipx/venv），找不到时 UI 如实提示"未检测到 DexAtlas 后端，请安装
  或在设置页指定路径"。设置页（W1 一并）提供后端命令路径配置。
- **风险 2：阶段埋点影响分析性能。** 埋点只写 run 记录（内存 + SQLite 单行
  更新），不引入 IO 放大；W2 的回归测试包含"埋点不改变分析结果"的断言。
- **风险 3：stages 契约与既有 runs 契约重复。** stages 作为 run 详情的
  **扩展字段**返回（同一个端点加字段），不新开平行端点，避免契约分叉。

## 5. 完成定义

- 打包 exe（无预置后端）真机完成三步主链路；
- `GET /api/projects/{id}/runs/{run_id}` 返回真实 stages，桌面分析页删除
  前端模拟；
- 既有测试套件全绿 + 新增回归测试（侧车拉起、stages 形状、埋点不改变结果）；
- C12 备料与运营清单落盘；
- 文档四处（status/ROADMAP/CHANGELOG/桌面 README）回填。
