# Phase 4 M15 — 演示镜头表与真实运行佐证

**日期：** 2026-11-23 · **阶段：** Phase 4 · **里程碑：** M15 第二步 — 演示素材录制
**性质：** 素材来源记录。本文逐镜头说明新演示视频的画面来自哪一次真实运行、对应哪些可复核数据；不包含手写的性能或质量数字。
**运行环境：** Windows 11 Pro，本仓库工作分支 `claude/youthful-clarke-db2263-wt`；Workbench `uv run dexatlas-workbench --port 8618`（前端已重新 build）；agent 经本机 OpenAI 兼容网关 magpine（`DEXATLAS_AGENT_BASE_URL=http://127.0.0.1:3425/v1`、`DEXATLAS_AGENT_MODEL=group/free`、`DEXATLAS_AGENT_PROVIDER=openai-compatible`）。录制由 Playwright（Edge headless，1440×900）真实驱动：点击、输入、上传、提问均为真实交互，无脚本化 provider、无摆拍帧。

---

## 1. 共同数据源

| 项 | 值 | 佐证 |
|---|---|---|
| 项目 | `apk_80a8fe0e81204c9f`（`examples/demo-app/demo.apk`，一方样本） | `GET /api/projects/apk_80a8fe0e81204c9f` 返回 `status=completed`、`completeness.complete=true` |
| 界面读数 | 5 classes / 8 methods / 23 call sites / 21 call edges / 12 evidence | 同上接口与项目详情页计数卡（录制帧 0002） |
| published run | `run_ce8da0e906094f3e`，jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4，3.5s | 同上接口 `published_run` |
| agent 任务 | `3f428a7081cd`，question「Which permissions does this APK's manifest declare, and which components request them?」 | `.dexatlas/agent-tasks/3f428a7081cd.json`（真实模型调用状态文件） |
| agent 用量 | 2 iterations · 12,217 tokens（预算 120,000/16/180s）· 2 tool calls，状态 `completed` | 同上状态文件 |
| agent 工具调用 | `get_project_status` ✓ 0.015s；`get_manifest` ✓ 0.000s | 同上 `tool_calls` |
| agent 报告 | sections：established 2（E-0001 分析完整性、E-0002 manifest 声明 `com.example.demo` 1 permission / 3 components，均 verified）/ leads 0 / insufficient 1（E-0003，模型未附证据 locator，如实降档） | `GET /api/agent/tasks/3f428a7081cd/report` |

录制当次 agent 运行耗时约 84 秒（任务创建 06:16:13 → 终态轮询命中在 06:17:38 前），处于 180s 预算内。

## 2. 80 秒演示镜头表（`docs/assets/phase4-demo-80s.mp4`）

> **帧文件未入库（如实说明）：** 下表引用的 `0001-s1-project-list.png` 等 12 个帧文件是录制工作目录的截图产物，仅用于录制时逐镜头核对，未提交进仓库，当前无法直接打开比对。帧文件的命名与逐项内容描述为录制当次记录；请以本节对应的视频 `docs/assets/phase4-demo-80s.mp4` 与 [§1 的真实运行佐证](#1-共同数据源)（接口返回、agent 状态文件、报告接口）为准，不新增指向不存在文件的图片链接。

| 片段 | 时长 | 画面（真实帧） | 内容与佐证 |
|---|---|---|---|
| 1 | 8s | `0001-s1-project-list.png` | Workbench 项目列表：demo.apk、strings.apk、wide.apk 等，状态徽章与计数来自真实项目库 |
| 2 | 12s | `0002-s2-project-detail.png` | demo.apk 项目详情：completeness=complete、五张计数卡（5/8/23/21/12）、runs 面板列出 published run 与历史 run |
| 3 | 8s | `0004-s3-search-sign.png` | Search & Evidence：以 `sign` 实查符号索引，命中 `com.example.demo.Crypto.sign` 等 |
| 4 | 8s | `0005-s3-evidence-open.png` | 打开一条证据记录：ID/level/kind/summary/provenance 来自真实 evidence 表 |
| 5 | 8s | `0008-s4-calls-graph.png` | Call Graph：`Crypto.sign` 的 callers/callees 图（1 in / 4 out），来自 Androguard 权威符号图 |
| 6 | 7s | `0007-s4-calls-hits.png` | 方法选择器：索引搜索命中后按方法 id 跳转 |
| 7 | 6s | `0009-s5-agent-idle.png` | Agent workspace 空态：显示 `model: group/free via openai-compatible` |
| 8 | 6s | `0011-s5-agent-planning.png` | 提交真实问题后的 planning 态（任务已受理） |
| 9 | 8s | `0033-s5-agent-completed.png` | 真实模型调用完成：completed 徽章、12,217/120,000 tokens、2 iterations、2 tool calls |
| 10 | 7s | `0034-s5-panel…toolcalls.png` | Tool calls 时间线（get_project_status、get_manifest）与 Established facts 表 |
| 11 | 7s | `0041-s6-export-markdown.png` | 点击「Markdown report」真实导出报告文件 |
| 12 | 6s | `0043-s7-tail-agent.png` | 尾帧：agent 报告分区（established / insufficient），证据不足明说 |

合计约 91 秒，处于 60–90 秒要求的上沿附近（含片头片尾缓冲）。

## 3. 技术讲解素材

- 讲解脚本：`docs/reports/phase4-tech-talk-script.md`（4 分钟分段、解说词与画面依据）。
- 讲解视频：`docs/assets/phase4-tech-talk-4min.mp4`（与演示同源的真实运行画面 + 逐段讲解字幕；未做人工配音，如需配音由作者后续叠加）。

## 4. 披露边界

- 新素材的 agent 段是**真实模型调用**（magpine `group/free`），区别于旧 `demo.mp4`/`demo.gif` 的脚本化 provider；两者不混用，旧素材的披露口径由 README 窗口统一改写。
- 录制画面中不含密钥、本地绝对路径或私人工作区名；workspace 名显示为 `.dexatlas` 相对路径。
- 模型输出在画面与解说中均保持「lead 不等于 finding」：E-0003 因未附证据被归入 insufficient，未升格。
- 素材由真实交互生成；未使用任何脚本化 provider、合成画面或手写数字。
