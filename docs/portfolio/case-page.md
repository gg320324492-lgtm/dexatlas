# DexAtlas — 案例页（通用外部渠道骨架）

> **性质：** M15 步骤 4 的通用案例页骨架，按[发布规划 §4](../reports/phase4-release-plan.md) 的模板填写。
> **范围约束：** 本页不点名任何外部平台或发布渠道；平台选择、发布与投放由作者自行决定。每格陈述都有仓库内依据；不可复核的营销形容不写。联系字段留空，不虚构联系方式。

---

## 一句话价值

DexAtlas 把一个 APK 变成一份**可核验**的分析：三个后端（Androguard / JADX / Apktool）产出清单、符号索引与调用图，每条结论带证据等级，并且回溯到它被读出的那个字节位置。
（依据：[portfolio.md](../portfolio.md)「Short description」；[分析来源说明](../analysis-provenance.md)。）

## 它解决什么问题

- **输入：** 一个获得授权分析的 APK。样本边界见 [README「Intended use」](../../README.md#intended-use)——教育、授权软件分析、移动应用安全评估与防御性研究；签名伪造、许可绕过、保护规避与未授权数据提取明确不在范围内。
- **输出：** 解码后的 manifest（包名、版本、SDK、权限、导出组件）、类/方法/字段/字符串符号索引、调用点与调用边、带出处的反编译源码、逐条证据记录，以及由同一渲染器生成的 Markdown / JSON 报告（Workbench 导出与渲染器逐字节一致）。
  （依据：[案例研究目录](../case-studies/README.md)；[portfolio.md](../portfolio.md)「What it does」。）
- **边界：** DexAtlas 不是安全判定器——可疑形状只作为形状报告，不判恶意、不评分、不断言可利用性；模型输出只能是 `lead`，永远不会被记录为 `verified`；后端失败是结果值（`ToolOutcome`），报告写明哪些步骤没有运行。
  （依据：[案例研究目录](../case-studies/README.md)「What these studies are not」；[portfolio.md](../portfolio.md)「An evidence model with levels」；[执行单](../roadmap/phase4-plan.md)。）

## 交付物

- **五种使用方式：** CLI、REST API、只读 MCP server（11 个工具、无写路径、无 shell、无模型依赖）、单循环证据约束 agent、本地 Web Workbench（React + Vite + TypeScript）。
  （依据：[portfolio.md](../portfolio.md)；[安装说明](../install.md)；[MCP server 说明](../architecture/mcp-server.md)。）
- **报告：** 生成式 Markdown / JSON / HTML，附证据引用与 locator；`dexatlas runs` / `dexatlas render` 可原样回放某一次已发布运行。
  （依据：[报告渲染说明](../architecture/report-rendering.md)；[公共契约](../architecture/public-contracts.md) §1.1。）
- **文档入口：** README（[英文](../../README.md) / [中文](../../README.zh-CN.md)）、[安装](../install.md)、[架构](../architecture/README.md)、[执行报告](../reports/phase1-execution-report.md)、[当前状态](../status.md)。

## 技术栈与来源

- Python / uv；React + Vite + TypeScript Workbench；SQLite 工作区。
  （依据：[架构图](../architecture/diagram.md)；[执行单 §3.2](../roadmap/phase4-plan.md)。）
- 三个第三方引擎**独立进程调用，不在仓库内捆绑、不再分发**：[JADX](https://github.com/skylot/jadx)、[Apktool](https://github.com/iBotPeaches/Apktool)、[Androguard](https://github.com/androguard/androguard)，均为 Apache-2.0。
  （依据：[README「Authorship and third-party engines」](../../README.md#authorship-and-third-party-engines)。）
- **作者自述：** 个人开源项目，无客户或雇主；AI 编码助手参与了部分实现，但每项设计决策与每行交付代码由作者评审并负责。贡献边界与第三方引擎的分工见上述 README 段落。

## 真实演示

> 以下素材全部来自真实运行，路径均已在仓库内。逐镜头证据来源见[演示镜头表](../reports/phase4-demo-shots.md)；讲解分段与解说词见 [phase4-tech-talk-script.md](../reports/phase4-tech-talk-script.md)。

- **80 秒演示视频（M15 新录）：** [docs/assets/phase4-demo-80s.mp4](../assets/phase4-demo-80s.mp4) —— 上传 demo.apk → 分析 → 搜索与证据 → 调用关系 → agent 真实提问 → 导出报告。由 Playwright（Edge headless）真实交互驱动，**无脚本化 provider、无摆拍帧**；agent 段为真实模型调用（`group/free`，2 iterations / 12,217 tokens，任务 `3f428a7081cd`）。
  （依据：[phase4-demo-shots.md](../reports/phase4-demo-shots.md)；agent 报告接口 `GET /api/agent/tasks/3f428a7081cd/report`。）
- **4 分钟技术讲解视频（233 秒，无配音）：** [docs/assets/phase4-tech-talk-4min.mp4](../assets/phase4-tech-talk-4min.mp4) —— 问题与边界 → 三后端与证据模型 → Workbench 信息架构 → 核心路径演示 → agent 与证据链 → 验收与限制；画面与 80 秒版同源（真实运行），配音可按讲稿另行录制。
  （依据：[phase4-tech-talk-script.md](../reports/phase4-tech-talk-script.md)；时长与「无配音」披露同 [docs/reports/ 索引](../reports/README.md)该文件条目。）
- **完整会话演示（84.8 秒，`ffprobe` 实测）：** [docs/assets/demo.mp4](../assets/demo.mp4) —— 早期端到端录屏：空工作区 → 上传 → 分析 → 检索 → 证据 locator → 调用图 → agent 提问 → 报告导出。**披露：** 该视频的 agent 画面由项目自带的脚本化演示 provider 驱动（无密钥、无真实模型调用），其余为真实分析产物；`demo.gif` / `demo-quick.gif` 为同源剪辑。
  （依据：[状态页 §4.6](../status.md) demo 行的 ffprobe 实测记录。）
- **真实模型 agent 成功流截图（M13，2026-11-23）：** [docs/assets/phase4-agent/](../assets/phase4-agent/) 22 张——UI 提问 → planning / running → 工具调用 → completed，工具调用与答案分区可见，报告带 limitations。
- **Workbench 六页 × 四宽度基线截图（M11）：** [docs/assets/phase4-baseline/](../assets/phase4-baseline/) 24 张（375 / 768 / 1024 / 1440），覆盖项目列表、项目详情、Search & Evidence、Call Graph、Agent、Benchmarks。

| 环节 | 真实截图 |
|---|---|
| 项目列表 / 上传 | ![project list](../assets/phase4-baseline/01-project-list-1440.png) |
| 项目详情（completeness 与计数） | ![project detail](../assets/phase4-baseline/02-project-detail-1440.png) |
| 搜索与证据 | ![search and evidence](../assets/phase4-baseline/03-search-evidence-1440.png) |
| 调用关系 | ![call graph](../assets/phase4-baseline/04-calls-1440.png) |
| agent 真实成功流 | ![agent final](../assets/phase4-agent/agent-03-final.png) |

## 如何验收

1. **按公开文档在干净环境启动：** `git clone` 后 `uv sync --extra analysis`，再按 [install.md](../install.md) 安装后端。独立用户 walkthrough（[phase4-walkthrough.md](../reports/phase4-walkthrough.md)，2026-11-23）已在干净 clone（`main@22c0621`）上按 README 原文走完全链路，结论**通过**（4 项低危发现，无阻断）。
2. **用一方示例 APK 走核心路径：** `examples/demo-app/demo.apk`（源码在旁），`uv run dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json --html report.html`，然后逐项核对[执行单 §7 验收矩阵](../roadmap/phase4-plan.md)。
3. **打开证据引用，确认能回到来源：** 每条证据带工具名与版本、APK sha256、文件与位置 locator；完整方法见[怎么复核](../how-to-verify.md)。
4. **核对公共契约与边界：** CLI 退出码 0–6、REST 端点、MCP 工具清单见[公共契约](../architecture/public-contracts.md)；复核时**读 skip 数**，并记录 macOS 尚未验证。

## 已知限制

- **macOS 未验证**（M8 对外统一口径：「交付完成，macOS 未验证」）。（依据：[phase4-baseline.md](../reports/phase4-baseline.md)。）
- **后端安装状态影响完整性：** JADX / Apktool 缺失时分析照常完成，但依赖它们的步骤缺失，报告会写明——数字是下界，不是完整值。（依据：[分析来源说明](../analysis-provenance.md)。）
- **模型输出只能是 lead；** agent 在默认预算（20000 tokens / 8 迭代）下部分提问会 `budget_exhausted`，需要放宽预算。（依据：[状态页 §4.6](../status.md)。）
- **agent 基准成绩如实披露：** 冻结 20 题三轮合计 GLM-5.3-Flash 53/60 = 88.3%、MiniMax-M3.1-Flash 49/60 = 81.7%，均低于项目自设的 ≥90% 验收线，按「现状披露」处理，不宣称达标。（依据：[portfolio.md](../portfolio.md)；[状态页 §4.0](../status.md)。）
- **没有真实用户信号时不启动下一阶段功能开发**：项目在 Phase 4 收口后进入 Portfolio Freeze，规则见 [freeze.md](freeze.md)。

## 联系与发布说明

（由作者自行填写。本模板不预设平台、账号或外链；联系方式、发布渠道与投放文案均由作者决定。）
