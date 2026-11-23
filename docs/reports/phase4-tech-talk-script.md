# Phase 4 M15 — 技术讲解脚本（4 分钟）

**性质：** 讲解素材脚本与录制记录。分段与画面同 `phase4-release-plan.md` §2.2；所有画面均来自
2026-11-23 的真实运行（Workbench `--port 8618`，项目 `apk_80a8fe0e81204c9f` / `demo.apk`，
agent 段为 magpine `group/free` 真实模型调用），帧号见 `phase4-demo-shots.md` 镜头表。
本文不虚构任何画面或数字；讲解只引用画面可见事实。

| 时间 | 画面（真实运行） | 解说词 | 依据 |
|---|---|---|---|
| 0:00–0:30 | 项目列表 → demo.apk 项目详情（completeness=complete，5 classes / 8 methods / 23 call sites / 21 call edges / 12 evidence，以界面实际读数为准） | 「给一个授权 APK，DexAtlas 产出的是可回溯的分析结果：清单、符号、调用图、证据。它不是安全判定器——模型给出的 lead 不等于 finding，证据不足会明确标注。」 | s1/s2 帧；M11 基线 |
| 0:30–1:15 | runs 面板与工具版本（jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4）；分析来源说明页 | 「三个后端各司其职：Androguard 给权威 DEX 符号图，JADX 反编译 Java，Apktool 解析 manifest 和 Smali。后端失败不是异常，是 `ToolOutcome` 里带着错误的结果值——报告会写明哪些步骤没跑，数字是下界。证据分 verified / lead / insufficient 三档。」 | docs/analysis-provenance.md；s2 帧 runs 面板 |
| 1:15–2:00 | Workbench 六路由走查：项目列表、项目详情、Search & Evidence、Call Graph、Agent、Benchmarks；六态组件 | 「Workbench 有六个路由，共享同一套 token 和状态组件。loading、empty、success、partial、error、unavailable 六种状态都有对应界面——partial 会说明缺了哪个后端，而不是把不完整当完整展示。」 | s1–s4 帧；docs/architecture/workbench-ui.md；M11 基线 |
| 2:00–2:45 | 播放 80 秒演示的核心段（搜索→证据→调用图） | 「现在看核心路径：搜符号、打开证据记录、每个结论跳回来源；调用图来自 DEX 符号图，不是前端推断。」 | s3/s4 帧 |
| 2:45–3:30 | Agent workspace：提问 → planning/running → 工具调用时间线 → completed，答案分区与证据表 | 「这是真实模型调用（model: group/free via openai-compatible）。进行中能看到 budget 与工具调用逐步出现；完成后答案分 established / leads / insufficient，并附 limitations 与报告链接。模型输出永远是 lead，不升格为结论。」 | s5 帧；M13 实测笔记 |
| 3:30–4:00 | README 入口 → docs/status.md → 报告导出按钮 | 「公共契约有实时检查，响应式在四个宽度实测，可访问性做了对比度与键盘路径检查；macOS 尚未验证，这条限制写在状态页里。文档入口在 README，报告数字全部由脚本生成。」 | s6/s7 帧；docs/status.md；phase1-execution-report.md |

## 录制与披露说明

- 视频文件：`docs/assets/phase4-tech-talk-4min.mp4`，实际时长 3 分 53 秒（233 s），已按本表时间轴渲染（真实运行画面 + 逐段讲解字幕，无配音；如需配音由作者后续叠加）。本文件与视频同时提交；若视频缺失则以本表为脚本保留。
- 画面全部来自本机真实运行（帧号与逐段佐证见 `phase4-demo-shots.md` 镜头表）；不出现密钥、本地绝对路径或私人工作区名。
- 口播只陈述画面可见事实；测试数不在口播中念出，指向执行报告的生成数字。
- 与旧 `demo.mp4` / `demo.gif` 的「脚本化 agent」披露不混用：新素材 agent 段为真实模型调用（任务 `3f428a7081cd`，2 iterations / 12,217 tokens / 2 tool calls，状态 completed）。
