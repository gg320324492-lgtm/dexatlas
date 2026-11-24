# Phase 4 M15 — 发布冻结与作品集封装规划

> **2026-11-24 状态追记（不改动下文原规划）：** 本文写作时（2026-11-23，`337e7d5`）素材、走查、README 入口尚未落盘，各步骤的「当前是否已具备」自评是当时如实的判断，现已过时。截至 2026-11-24（基线 `e30307e`）：步骤 1（独立 walkthrough）已完成，见 [phase4-walkthrough.md](phase4-walkthrough.md)；步骤 2（演示与讲解录制）已完成，见 [phase4-demo-shots.md](phase4-demo-shots.md) 与 `docs/assets/phase4-demo-80s.mp4`、`docs/assets/phase4-tech-talk-4min.mp4`；步骤 3（README 展示区）与步骤 4（案例页）已完成，见 [case-page.md](../portfolio/case-page.md)；步骤 5（发布前门禁）已本地执行，见 [phase4-release-review.md](phase4-release-review.md)；步骤 6（源码评审并标记完成）评审记录同在 [phase4-release-review.md](phase4-release-review.md)，Phase 4 已标记完成；步骤 7（作品集冻结）已完成，冻结声明落盘为 [portfolio/freeze.md](../portfolio/freeze.md)（Portfolio Freeze 已生效）。步骤 6 之后仅剩 GitHub 侧发布动作（tag/Release/推送），待用户发话后执行。下文原规划正文保留不改写，读者请以本追记与所引落盘文档为准。

**日期：** 2026-11-23 · **阶段：** Phase 4（[执行单](../roadmap/phase4-plan.md)，最终决策 A + D + G）· **里程碑：** M15 — 发布冻结和作品集封装
**性质：** 规划文档。七步中的执行、录制、门禁和发布动作尚未在本轮完成；本文只写清交付物、前置、现状、缺口与建议执行方式，不宣称任何未执行步骤已经通过。
**范围约束：** 通用开源项目。不点名任何外部平台或发布渠道；作者自行选择渠道，渠道页复用同一套演示、截图和案例材料。本轮不改产品代码，不主动触发 CI。

---

## 0. 阅读方式

[执行单 §6](../roadmap/phase4-plan.md) 把 M15 定为 1–2 个工程日的七步收尾；[§8 冻结规则](../roadmap/phase4-plan.md) 定义了什么信号才能解冻。本文逐条对照当前仓库，给出可执行顺序。

文中「已具备」只表示仓库里能指出可复核的文件、记录或已实测的资产；「待执行」表示需要新的运行、录制或人工审阅才能产生证据。任何测试数、覆盖率、门禁结论都不在本文手写：数字归 [执行报告](phase1-execution-report.md) 的 `<!--fig:...-->` 标记，README badge 由 `scripts/refresh-report-figures.py` 写入；CI 尚未跑，本轮不更新数字。

与本文并行推进、但不属于本文产物的窗口：独立用户 walkthrough 记录（`docs/reports/phase4-walkthrough.md`，由 walkthrough 窗口编写）、M14 的未跟踪截图资产 `docs/assets/phase4-m14/`、执行报告数字的刷新。本文引用它们的状态时应以它们落盘后的版本为准，不代替其结论。

---

## 1. M15 七步逐条对照

| 步骤 | 交付物 | 前置条件 | 当前是否已具备 | 缺口 | 建议执行方式 |
|---|---|---|---|---|---|
| 1. 从 README 开始完成一次独立用户 walkthrough | 独立走查记录（建议落在 `docs/reports/phase4-walkthrough.md`）：执行人、环境、每一步的实际结果、卡点与退出条件对照 | README 双语文案可读；可启动 Workbench；有获授权的分析样本与可用后端 | **部分具备**。README 双语与真实样本链路已有记录；[M11 基线报告](phase4-baseline.md) §1 给出真实可运行流程；独立走查文档正在另一窗口编写，尚未落到本文可以引用的提交 | 尚无「独立执行人按公开文档、无口头解释完成核心路径」的终态记录；M11 报告明确说明 agent 成功流当时未配模型、未截图 | 等 walkthrough 窗口落盘后审阅其证据，按[执行单 §7 验收矩阵](../roadmap/phase4-plan.md)核对九项；若出现阻塞，按冻结规则中的「实际使用记录表明核心流程存在阻塞」处理，而非顺手加功能 |
| 2. 录制 60–90 秒真实演示和 3–5 分钟技术讲解 | 新录制的短视频、讲解视频及两者的文字稿/镜头表，放在 `docs/assets/` 与 `docs/reports/`；产出后替换现有演示入口 | 真实项目 `apk_80a8fe0e81204c9f` 仍在本地工作区可复现；agent 成功流可复现；录制脚本/环境就绪 | **未具备**。现有 `docs/assets/demo.mp4`（约 85 秒）、`demo.gif`、`demo-quick.gif` 是真实运行剪辑，但 README 已明确披露其中 agent 画面由脚本化 provider 驱动、不是真实模型调用；M13 的真实 agent 成功流有 22 张截图（`docs/assets/phase4-agent/`），但不是视频 | 缺真实模型调用的 agent 视频段；缺 3–5 分钟讲解视频；旧演示的 agent 披露口径必须与新素材一起更新，不能新旧混引 | 按本文 §2 的脚本提纲录制；素材必须是真实运行的一镜一段，讲解只引用截图中可见事实；录制后由作者核对画面与解说是否一致 |
| 3. 更新 GitHub README 的截图、入口和演示说明 | `README.md` 与 `README.zh-CN.md` 的截图、视频链接、入口段落同步更新 | 步骤 2 的素材已落盘；步骤 1 的走查无阻断；截图来源可追溯到真实运行 | **部分具备**。双语 README 现有演示段落与素材链接完整，已有 Phase 4 截图资产（见本文 §3）；但截图尚未进入 README | 现有 README 仍指向旧 85 秒演示与其「脚本化 agent」披露；新 Workbench 六页、状态矩阵、agent 成功流截图没有展示入口；README 索引对 Phase 4 材料的入口尚需补齐 | 按本文 §3 的替换清单同时改两份 README；只用已落盘的真实资产路径；数字 badge 不手写，仍由脚本刷新；改完跑链接与文档检查 |
| 4. 准备外部渠道案例页、交付边界、技术栈和验收方式 | 通用案例页骨架（模板 + 已验证事实清单），不发布、不点名平台 | 案例事实可复核；交付边界与限制有现成文档 | **部分具备**。已有[作品集描述](../portfolio.md)、[案例研究目录](../case-studies/)、[安装说明](../install.md)、[公共契约表](../architecture/public-contracts.md)、[验收记录](phase1-execution-report.md)与 [M4 端到端记录](m4-e2e-run.md)；M7 对外素材在 2026-11-21 去平台化清理中移除 | 没有一份「通用渠道可用」的案例页骨架，也没有把交付边界、技术栈、验收方式收敛到同一页；对外渠道由作者自行选择，本仓库不替平台做适配 | 按本文 §4 模板骨架落一份通用页；每格只填可由仓库内文档支撑的陈述；平台选择、发布与文案投放由作者自行操作 |
| 5. 执行测试、lint、format、mypy、vulture、文档引用、版本声明和 `git diff --check` | 一次完整的门禁运行记录；数字只在完整测量后由脚本写入 | 按 [CLAUDE.md](../../CLAUDE.md) 的前置条件备齐：完整 clone、第三方 fixtures、后端、ffmpeg、tags；每个 worktree 自己的 `.venv` | **未具备（本轮不执行）**。脚本与 CI job 齐备（`scripts/check-doc-citations.py`、`check-version-claims.py`、`check-release-numbers.py`、`check-gate-coverage.py`、`refresh-report-figures.py` 等）；用户已明确 CI 不主动跑 | 本轮没有门禁运行结果；测试数/覆盖率以执行报告的标记为准，不能从旧报告抄数；测量必须在 `ruff format` 之后做，否则报告记录的是不存在的文件树 | 用户发话后按本文 §6 清单执行；先看 skip 数而非只看退出码；测量不完整时不让脚本写覆盖率和套件数 |
| 6. 完成源代码评审，并把 Phase 4 标记为完成 | 源码评审记录；`docs/status.md`、路线图、README 双语文案、HANDOVER 中 Phase 4 状态一致标记为完成 | 步骤 1–5 全部有证据；[执行单 §7 验收矩阵](../roadmap/phase4-plan.md)九项全部有证据 | **未具备**。M11–M14 的实现与资产已陆续提交，[状态页](../status.md)目前仍把 Phase 4 写成进行中的执行单，未标记完成 | 缺一次覆盖 Phase 4 全部改动的源码评审；缺状态页/路线图/README/HANDOVER 的一致更新；验收矩阵尚未逐项打勾 | 评审范围以 Phase 4 提交序列为准；评审通过后一次性更新状态文案，避免多处各写一种完成度；里程碑推进遵循「源码评审与验收后才推进」的规则 |
| 7. 写明没有真实用户信号时不启动下一阶段功能开发 | Portfolio Freeze 声明草稿，最终并入状态页/路线图/README | 步骤 6 完成，Phase 4 正式收口 | **部分具备**。[执行单 §8](../roadmap/phase4-plan.md)已定义四类解冻信号与冻结期维护范围；[状态页](../status.md)已写「完成后默认 Portfolio Freeze」 | 缺一份面向读者的冻结声明，说明「何时冻结、冻结期允许哪四类维护」；本轮先产出草稿，正式发布时机随步骤 6 | 用本文 §7 草稿；不把「没有用户反馈」写成「项目停止维护」，只写范围决策 |

---

## 2. 演示素材方案（脚本提纲，不录制）

**共同数据源：** `examples/demo-app/demo.apk`（一方样本，源码在 `examples/demo-app/` 旁），项目 id `apk_80a8fe0e81204c9f`，M11 基线实测为 5 classes / 8 methods / 23 call sites / 21 call edges / 12 evidence、`completeness=complete`。这些数字是 M11 那次运行的记录，录制时以当次界面实际读数为准，不在口播中硬背。

**两条硬约束：**（1）新演示的 agent 段必须来自真实模型调用，沿用 M13 实测配置思路（UI 提问 → planning/running → completed，工具调用 `get_project_status` → `get_manifest`），不再复用旧视频里脚本化 provider 的画面；（2）短视频与讲解视频都只用真实运行画面，旁白只说可见事实，不把 lead 说成 finding。

### 2.1 60–90 秒真实演示（建议 80 秒）

| 时间 | 画面 | 口播要点 | 证据/素材来源 |
|---|---|---|---|
| 0–8 s | README 顶部 → 启动 Workbench，项目列表 | 「这是从 README 开始的核心路径：本地启动、上传授权 APK。」 | `docs/assets/phase4-baseline/01-project-list-1440.png`；M11 报告 §1 |
| 8–20 s | 上传并分析 demo.apk，进入项目详情 | 展示 completeness、计数卡；「后端实际跑了什么，报告里逐项写明。」 | `docs/assets/phase4-baseline/02-project-detail-1440.png` |
| 20–35 s | Search & Evidence：查符号，打开证据记录 | 「每条结论能跳回来源；找不到就标 insufficient。」 | `docs/assets/phase4-baseline/03-search-evidence-1440.png`、`docs/assets/phase4-agent/kb-03-evidence.png` |
| 35–50 s | Call Graph：选方法，看 callers/callees 与源码片段 | 「调用关系来自 DEX 符号图，不是前端推断。」 | `docs/assets/phase4-baseline/04-calls-1440.png`、`docs/assets/phase4-agent/r6-calls-method-1440.png` |
| 50–68 s | Agent Workspace：真实提问，显示 planning/running 至 completed | 「这是真实模型调用，工具调用和答案分区可见；答案带引用。」 | `docs/assets/phase4-agent/agent-00-idle.png` → `agent-02b-running-tools.png` → `agent-03-final.png` |
| 68–78 s | 导出 Markdown/JSON 报告，打开链接 | 「报告是生成物，数字不是手写。」 | `docs/assets/phase4-agent/agent-04-report.png`、`docs/assets/phase4-agent/kb-04-export.png` |
| 78–80 s | 尾帧：报告 + 边界说明 | 「证据不足处会明说，后端失败也是结果。」 | 旧演示的披露口径须同步改写 |

### 2.2 3–5 分钟技术讲解（建议 4 分钟）

1. **0:00–0:30 问题与边界。** 给一个授权 APK，产出可回溯的分析结果；不是安全判定器，lead 不等于 finding。
2. **0:30–1:15 三后端与证据模型。** Androguard（权威 DEX 符号图）、JADX（Java 反编译）、Apktool（manifest/Smali）；后端失败作为 `ToolOutcome` 返回，报告标明哪些步骤没跑；证据分 `verified` / `lead` / `insufficient`。依据：[分析来源说明](../analysis-provenance.md)。
3. **1:15–2:00 Workbench 信息架构。** 六个路由、共享 token 与状态组件、六态矩阵（loading/empty/success/partial/error/unavailable）。依据：[Workbench UI 设计](../architecture/workbench-ui.md)、[M11 基线](phase4-baseline.md)。
4. **2:00–2:45 核心路径演示剪辑。** 直接放 §2.1 的 80 秒片段或其中 45 秒精华，画面与短视频同源。
5. **2:45–3:30 agent 与证据链。** M13 真实成功流：进行中反馈、工具调用、答案分区、报告链接；明确披露模型来源与数据边界，不把模型输出升格为结论。依据：M13 实测笔记与 agent 截图。
6. **3:30–4:00 验收与边界。** 公共契约、响应式四宽度、可访问性检查、macOS 未验证；给出文档入口，口播不念测试数。依据：[状态页](../status.md)、[执行报告](phase1-execution-report.md)。

**录制前检查清单：** 本地工作区有 `apk_80a8fe0e81204c9f`；agent 环境变量已配置且 `/api/agent/config` 显示 configured；前端已重新 build；录屏不出现密钥/本地绝对路径/私人工作区名；口播与旧 README 的「脚本化 agent」披露不冲突；素材文件只提交真实剪辑，不提交临时脚本与 token。

---

## 3. README 截图更新清单

两份 README 必须同步：**`README.md` 第 100–130 行附近**（`demo-quick.gif`、完整演示 `<details>` 段）与 **`README.zh-CN.md` 对应段落**。数字 badge 只由 `scripts/refresh-report-figures.py` 写，不手工编辑。

| 用途 | 建议采用资产 | 来源基线 | 替换/新增位置 |
|---|---|---|---|
| 顶部快速预览（分析摘要 + 证据层级） | `docs/assets/demo-quick.gif`（保留，直到新短视频产出） | 旧演示，真实分析画面 | 两份 README 现有 `<img src=docs/assets/demo-quick.gif>`；步骤 2 完成后替换成新 60–90 s 剪辑的短 GIF |
| 完整会话（搜索、交叉引用、报告） | `docs/assets/demo.gif` + `docs/assets/demo.mp4`（保留但更新披露） | 旧 85 秒录制，真实分析画面 + **脚本化 agent** | 两份 README 完整演示段与 Demo video 入口；与 §2 新素材一起发布，旧披露不可删改一半 |
| Workbench 项目列表 / 上传 | `docs/assets/phase4-baseline/01-project-list-1440.png`（或 M14 更新帧） | M11 基线，24 张四宽度截图 | 两份 README 新增「Workbench」小节；375/768/1024/1440 的对照另列入架构文档，不必全塞 README |
| 项目详情 / 导出 | `docs/assets/phase4-baseline/02-project-detail-1440.png` | M11 基线 | Workbench 小节 |
| 搜索与证据 | `docs/assets/phase4-baseline/03-search-evidence-1440.png` | M11 基线 | Workbench 小节 |
| 调用关系 | `docs/assets/phase4-baseline/04-calls-1440.png`、`docs/assets/phase4-agent/r6-calls-method-1440.png` | M11 基线 + M13 真实方法 id 重拍 | Workbench 小节 |
| Agent 成功流 | `docs/assets/phase4-agent/agent-03-final.png`、`agent-04-report.png` | M13 真实模型成功流（22 张） | 两份 README 的 agent 段落，须注明模型来源与数据边界 |
| 状态覆盖（可选，一张拼图） | `docs/assets/phase4-states/` 中六态代表帧 | M13/M14 六态核验 | 架构文档优先；README 仅用一张概览 |
| 键盘/焦点/减少动画（可选） | `docs/assets/phase4-agent/kb-*.png`、M14 的 `docs/assets/phase4-m14/focus-*.png`（后者由 M14 a11y 窗口落盘，未提交） | M13 + M14 | 无障碍说明段落；引用 M14 资产前先确认其已入版本控制 |

**替换原则：** 路径必须指向已提交的真实资产；README 只放少量关键帧，四宽度全套留在 `docs/architecture/workbench-ui.md` 与报告索引；截图不承载数字声明；两份 README 的镜头顺序和文字披露保持一致。

---

## 4. 外部渠道案例页通用模板骨架（不点名平台）

> 以下骨架只定义信息结构。平台名称、发布方式、投放与对外沟通均由作者自行决定；仓库内不写死任何渠道名、链接或账号。

```markdown
# DexAtlas — 案例页（通用模板）

## 一句话价值
[可验证的 APK 静态分析：三后端、证据分级、报告可回溯。只写仓库能证明的内容。]

## 它解决什么问题
- [输入：获得授权分析的 APK。]
- [输出：manifest/权限、符号索引、调用关系、证据记录、Markdown/JSON 报告。]
- [边界：不是安全判定器；lead 不是 finding；后端缺失会明写。]

## 交付物
- [本地运行：CLI / REST API / MCP / 只读 agent / Web Workbench。]
- [报告：生成式 Markdown/JSON，附证据引用。]
- [文档入口：README（双语）、安装、架构、执行报告。]

## 技术栈与来源
- [Python / uv；React + Vite + TypeScript Workbench；SQLite 工作区。]
- [第三方引擎独立进程调用，不在仓库内捆绑：Androguard、JADX、Apktool。]
- [作者自述与第三方贡献边界：见 README「Authorship and third-party engines」。]

## 真实演示
- [60–90 秒短视频：上传 → 分析 → 搜索 → 证据 → 调用关系 → agent → 导出。]
- [3–5 分钟讲解：三后端与证据模型、界面信息架构、验收与限制。]
- [所有画面来自真实运行；agent 段注明模型来源，不复用脚本化 provider 的旧画面。]

## 如何验收
1. [按公开 README 与安装文档在干净环境启动。]
2. [用一方示例 APK 走通核心路径，逐项核对执行单 §7 验收矩阵。]
3. [打开报告中的证据引用，确认能回到来源。]
4. [核对公共契约与退出码；记录 skip 数与未验证平台。]

## 已知限制
- [macOS 未验证；后端安装状态影响完整性；模型输出只能是 lead。]
- [没有真实用户/客户信号时不启动下一阶段功能开发。]

## 联系与发布说明
[由作者自行填写；模板不预设平台、账号或外链。]
```

**填表规则：** 每个方括号都必须换成可点击的仓库内依据或当次真实运行结果；不可复核的营销形容一律删掉；平台适配代码或平台专属文案不进入本仓库。

---

## 5. 发布前核查清单

> 用户已明确 CI 不主动跑；本节是待用户发话后执行的清单，不是已执行记录。

**前置与门禁**

- [ ] 每个 worktree 使用自己的 `.venv`（`uv sync --frozen --all-extras`）；不在主检出与 WSL 之间混用。
- [ ] clone 为完整深度（tags 可读取）；第三方 fixtures 已由 `scripts/fetch-fixtures.sh` 获取；Java 后端已安装；ffmpeg 与 Pillow 就绪。
- [ ] 先 `uv run --no-sync ruff format .`，再测量；顺序颠倒会使报告记录的文件树指纹失效。
- [ ] `uv run --no-sync pytest -q`：**读 skip 数**，后端缺失造成的 skip 不算通过。
- [ ] `uv run --no-sync ruff check . && uv run --no-sync ruff format --check .`
- [ ] `uv run --no-sync mypy`
- [ ] `uv run --no-sync vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80`（退出码 0）
- [ ] `uv run --no-sync python scripts/check-doc-citations.py`；源码改动后先用 `scripts/remap-citations.py` 重映射，再人工核对其输出
- [ ] `uv run --no-sync python scripts/check-version-claims.py --base auto`
- [ ] `uv run --no-sync python scripts/check-release-numbers.py`（含 `--strict` 若发布说明已备）
- [ ] `uv run --no-sync python scripts/check-gate-coverage.py`
- [ ] `git diff --check`
- [ ] 只有在所有测试都执行、无 skip 的情况下运行 `scripts/refresh-report-figures.py`；数字只由脚本写，README badge 同理。

**内容与契约**

- [ ] 执行单 [§7 验收矩阵](../roadmap/phase4-plan.md)九项逐项有证据（状态真实、核心路径、契约稳定、组件一致、响应式、可访问性、证据可读、作品集完整、独立验收）。
- [ ] README 双语、status、路线图、HANDOVER 对 Phase 4 完成度只有一种解释；macOS 未验证继续写作限制。
- [ ] 公共契约（API、MCP、CLI、报告、退出码）无静默改变；有变化必须显式版本化并写变更记录。
- [ ] 新演示与 README 的 agent 披露一致；所有截图路径可解析，所有引用指向真实运行。
- [ ] 第三方 APK、DEX、`so`、密钥不在仓库内；样本仅一方或脚本获取。

**源码评审与冻结**

- [ ] 对 Phase 4 提交序列完成源码评审，记录结论与遗留问题；里程碑推进在评审与验收之后。
- [ ] 把 Phase 4 标记为完成，并把状态页/路线图/README/HANDOVER 同步。
- [ ] 发布 tag 与 Release 说明由作者确认；**本规划不主动执行 tag、Release、推送或 CI**。
- [ ] 在状态页/路线图并入 §7 冻结声明。

---

## 6. 执行顺序建议

1. 审阅并合入独立 walkthrough 记录（步骤 1）；若有阻断先按冻结规则判定。
2. 按 §2 录制真实演示与讲解，产出文字稿（步骤 2）。
3. 按 §3 同步双语 README 截图、入口和演示说明（步骤 3）；按 §4 填通用案例页骨架（步骤 4）。
4. 用户发话后按 §5 跑全部门禁并刷新数字（步骤 5）。
5. 源码评审通过后一次性更新状态文案、标记 Phase 4 完成（步骤 6）。
6. 并入 §7 冻结声明；由作者自行决定 tag/Release 与外部渠道发布（步骤 7）。

---

## 7. Portfolio Freeze 声明草稿

> 正式并入状态页/路线图的时机：步骤 6 源码评审通过、Phase 4 标记完成之后。**（2026-11-24 追记：该时机已达成——源码评审已通过并记录于 [phase4-release-review.md](phase4-release-review.md)，Phase 4 已标记完成；冻结声明已落盘为 [../portfolio/freeze.md](../portfolio/freeze.md)，Portfolio Freeze 生效。本节保留为起草过程记录。）**

**Portfolio Freeze（草案）**

自 Phase 4 源码评审通过并标记为完成之日起，项目默认进入 Portfolio Freeze。没有真实用户信号时，不启动下一阶段的功能开发，也不新增后端、分析规则、页面、平台或展示性功能。

重新规划新阶段的唯一依据是出现以下真实信号之一：

1. 有真实用户按公开文档完成安装，并留下可复核反馈；
2. 有真实客户提出与证据链能力直接相关的需求；
3. 有外部贡献者提交 issue、PR 或复现报告；
4. 有实际使用记录表明核心流程存在阻塞问题。

冻结期允许且只允许四类维护：

1. **安装与发布阻塞** —— 影响安装、启动、发布或核心路径可用的问题；
2. **安全问题** —— 依赖漏洞、数据处理或对外暴露的安全缺陷；
3. **依赖兼容性** —— 上游 breaking change、Python/Node 版本兼容等；
4. **文档事实错误与链接错误** —— 与外部实际状态不符的陈述、失效引用、错误数字。

每类维护仍需有回归测试、可复核记录或明确的手工验证；数字由测量脚本生成，状态文案同步更新。没有上述信号，也没有这四类问题，就保持现状——这不是停止维护，而是把范围锁定在已经验证过的交付物上。

---

## 8. 本轮未做的事

> **2026-11-24 追记：** 下列「未做」均为本文写作时（2026-11-23）的状态，现已陆续完成或另有归属——视频已录制落盘（`docs/assets/phase4-demo-80s.mp4`、`phase4-tech-talk-4min.mp4`）、README 展示区已更新、案例页与冻结声明已落盘（[case-page.md](../portfolio/case-page.md)、[../portfolio/freeze.md](../portfolio/freeze.md)）、门禁与源码评审已本地执行（[phase4-release-review.md](phase4-release-review.md)）。仍然成立的只有：未主动触发 CI、未打 tag、未创建 Release、未推送（待用户发话）；未修改产品代码，未改执行报告的测量数字。

- 未录制视频、未替换 README 截图、未发布案例页；
- 未跑测试、lint、format、mypy、vulture、文档引用、版本声明与 `git diff --check`；
- 未主动触发 CI、未打 tag、未创建 Release、未推送；
- 未修改产品代码，未改执行报告的测量数字，未触碰并行窗口的文件。
