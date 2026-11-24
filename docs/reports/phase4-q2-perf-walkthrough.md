# Phase 4 Q2 后性能走查报告 — Tauri 桌面原型真机测量

**日期：** 2026-11-24 · **性质：** Q2 后性能基线记录 · **测量对象：** Tauri release 原型（`dexatlas-desktop.exe` 13.1 MB）+ 真实 8618 后端
**来源说明：** 本报告由 X2 真机性能走查窗口测量。原测量工作区文件因 worktree 自动清理未能直接入库，本文按该窗口回报的测量数据重建；测量脚本（`perf_*.py`，位于仓库外 `E:\labcairn-local\tmp\`）与三张 1280 宽度实拍截图（`.scratch/q2-perf-shots/`，不入库）为原始证据。

> **诚实声明。** 以下数值是 2026-11-24 单机单次走查的记录，不是持续基准；机器配置、后端数据规模（当时每项目证据 8–12 条、符号 9–19 条）都会影响结果。当前数据规模小，本报告的结论不外推到大项目场景。

## 1. 测量环境

- Tauri release exe 直接运行（WebView2，加载 `desktop/dist` 打包资源），dev server 未启动。
- 后端：DexAtlas workbench 运行于 `127.0.0.1:8618`（JADX/Apktool 环境变量齐备）。
- 真实项目：`examples/demo-app/demo.apk`（`apk_80a8fe0e81204c9f`）、`examples/wide-app/wide.apk`（`apk_d342e11b7931077d`）。
- 测量方法：进程时间戳 / PowerShell `CopyFromScreen` 截图 / 任务管理器采样 / CDP 注入计时（方法细节随各项标注）。

## 2. 测量结果与阈值判定

| # | 项目 | 方法 | 数值 | 阈值（自定） | 判定 |
|---|---|---|---|---|---|
| 1 | 冷启动 → 首屏可交互 | 进程启动到窗口出现可操作（时间戳差） | 892 ms（进程→窗口仅 31 ms） | ≤ 2 s | ✅ |
| 2 | 路由切换（首页/分析/详情/报告/设置） | CDP 注入计时多次取平均 | 最慢 82 ms（详情页），其余 6–24 ms | ≤ 200 ms | ✅ |
| 3 | 证据列表渲染（demo 12 条 / wide 11 条） | CDP 注入计时 + longtask 观察 | 64 ms，0 longtask | ≤ 300 ms | ✅ |
| 4 | 证据点击 → 详情 + locator resolve | CDP 注入计时 | 11 ms | ≤ 100 ms | ✅ |
| 5 | 报告导出（MD/JSON × 报告页/详情页，点击→文件落盘） | 时间戳差 | 56–78 ms | ≤ 1 s | ✅ |
| 6 | 分析页 2s 轮询期 CPU（应用 8 进程树） | 任务管理器采样 | 0.06% 单核（峰值 0.10%） | ≤ 5% | ✅ |
| 7 | 轮询期内存 | 任务管理器采样 | 607 MB 稳定无增长（WebView2 8 进程基线） | ≤ 1 GB | ✅ |
| 8 | 后端被轮询期间 CPU | 任务管理器采样 | 0.02% | — | ✅ |
| 9 | 窗口缩放 1280→1920→1280→1024(min) | 逐档截图检查横向溢出/越界元素 | 0 横向溢出、0 越界 | 无破版 | ✅ |

**总体判定：** 九项测量全部达标；当前数据规模下无性能瓶颈，暂不需要虚拟滚动等优化（见 §3 P8）。

## 3. 问题清单（按严重度，修复状态截至 2026-11-24）

| 级别 | 编号 | 问题 | 修复归属 | 状态 |
|---|---|---|---|---|
| 高·发布阻塞 | P1 | release exe 为裸 cargo build 形态（未开 custom-protocol，运行时加载 devUrl）；Tauri 生产 origin 下原生 fetch 8618 被 CORS 拦（MissingAllowOriginHeader）→ 发布形态所有页面报"无法连接后端" | `desktop/src-tauri/` 配置 + `desktop/src/api/client.ts` 适配层 | ✅ 已修复（PR #9，`deea24e`/`64fec55`/`9e794c8`） |
| 高·数据/UX | P2 | strings.apk 自 11-23 起僵尸 running（>24h），首页显示"进行中"、分析页 2s 轮询永不停、cancel 405 | 后端 /cancel 端点（W1） | ✅ 已修复（PR #5，`f0e2bdb`） |
| 中·正确性 | P3 | 分析页对 running 项目把 JADX/Apktool/Androguard 全显示红色"× 失败·未安装"（实际已安装，只是 running run 的 tool_versions 未回填），违反"不推断"原则 | `desktop/src/pages/Analysis.tsx` deriveBackends | ✅ 已修复（PR #8，`b1c3ea3`） |
| 中·环境 | P4 | devUrl=localhost:5173 有 IPv6/IPv4 解析歧义（5173 被 `[::1]` 绑定占住时 exe 连不上，ERR_CONNECTION_REFUSED） | devUrl / vite host 改 127.0.0.1 | ✅ 已修复（PR #9，`deea24e`） |
| 低 | P5 | 分析页日志面板长 token（URL/项目 id）断行成碎行 | 日志样式 | ⬜ 待修（下一批） |
| 低 | P6 | 1920 宽屏 `.page` 无 max-width，内容全宽铺开 | global 样式 | ⬜ 待修（下一批） |
| 低 | P7 | 报告页"导出 MD" vs 详情页"导出 Markdown"文案不一致 | 按钮文案 | ⬜ 待修（下一批） |
| 信息 | P8 | 当前数据规模小（每项目证据 8–12 条、符号 9–19 条），列表渲染余量大，暂不需要虚拟滚动 | — | 无需行动 |

## 4. 结论

- Q2 桌面原型在真实后端、真实 APK 数据下的响应性、资源占用与布局稳定性全部达标，可以作为"部分解冻 B"阶段的稳定基线。
- P1–P4 四项阻塞/正确性问题已全部修复并经真机复验；P5–P7 三项低优先级遗留转入下一批小修。
- 本报告不声称覆盖大项目（数千类、数千证据）场景；该场景需要重新测量。
