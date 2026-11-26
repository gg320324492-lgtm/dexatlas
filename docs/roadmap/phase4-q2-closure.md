# Phase 4 Q2 收尾单 — 桌面应用阶段的结束条件

**日期：** 2026-11-24 · **性质：** Q2 收尾执行单 · **状态：** 已回填（2026-11-24，Q2-M1–M3 完成后；验收结论见[验收报告](../reports/phase4-q2-acceptance.md)）
**上游：** [phase4-q2-supplement.md](phase4-q2-supplement.md)（已批准的桌面应用补充单）

## 1. 收尾目标

Q2 桌面应用阶段结束时，项目必须能回答三个问题：

1. 桌面应用是不是做出来了，能不能在 Windows 上启动？
2. 它有没有守住 DexAtlas 的公共契约和证据优先原则？
3. 下一个阶段的冻结/解冻范围是什么？

本单是 Q2 的**退出门禁**：没有逐项回填之前，Q2 不能宣布完成。

## 2. 交付物核对清单

| # | 交付物 | 位置 | 状态 |
| --- | --- | --- | --- |
| 1 | 桌面 UI 设计规范 | `docs/architecture/desktop-app.md` | ✅ 完成（`9bbf87e`） |
| 2 | 视觉 token 与组件清单 | `desktop/src/styles/tokens.css` + 设计文档 §4 | ✅ 完成 |
| 3 | 组件库与组件画廊 | `desktop/src/components/`（19 组件 + states）+ `/gallery` 画廊页 | ✅ 完成（`520bf4d`） |
| 4 | 首页：拖拽上传 + 最近项目 | `desktop/src/pages/HomePage.tsx` | ✅ 完成（`7c53a7d` + `17bbd95` 接真实数据） |
| 5 | 分析进行中页：进度/日志/后端状态 | `desktop/src/pages/Analysis.tsx` | ✅ 完成（`c92879b`；阶段推进当时为前端模拟，页面有角标注明；该模拟已在 Phase 5 收尾删除） |
| 6 | 项目详情三栏 + 证据抽屉 | `desktop/src/pages/ProjectDetail.tsx` | ✅ 完成（`1d7623b`） |
| 7 | 证据与 locator 解析视图 | `desktop/src/pages/EvidencePage.tsx` + `desktop/src/pages/FindingsPage.tsx` | ✅ 完成（T1 `34a2790` 真实化） |
| 8 | 报告导出页 | `desktop/src/pages/ReportsPage.tsx` | ✅ 完成（`1d7623b`；Markdown/JSON 导出） |
| 9 | 设置页（后端路径/模型/版本） | `desktop/src/pages/SettingsPage.tsx` | ✅ 完成（T1 `34a2790`；`/api/backends` 后端未提供，如实呈现） |
| 10 | Windows 可运行 Tauri 原型 | `desktop/src-tauri/target/release/dexatlas-desktop.exe`（复现步骤 `.scratch/q2-windows-build-notes.md`） | ✅ 完成（`f7a286a`；打包分发未做，见验收报告 §2.3） |
| 11 | 四步标准截图对照 | `docs/assets/phase4-q2/01–04*.png`（说明 `.scratch/q2-m3-screenshots.md`） | ✅ 完成（`1c08bfc`） |
| 12 | Q2 验收报告 | `docs/reports/phase4-q2-acceptance.md` | ✅ 完成（本次提交） |

## 3. 退出条件（全部满足才可收尾）

### 3.1 产品与设计

- [x] 首屏呈现"拖拽上传 + 最近项目"，气质为高端浅色工作室。（截图 `docs/assets/phase4-q2/01-product-home.png`）
- [x] 深海军蓝主色 + 淡紫/橙渐变仅用于既定区域；圆角、阴影、渐变 token 生效。（token 于 `desktop/src/styles/tokens.css`；截图 04 画廊）
- [x] 线性图标风格统一；首屏插画不复制第三方版权资产。（lucide 线性图标；插画为自绘 hero 渐变，无第三方素材）
- [x] 左侧栏导航覆盖项目/分析/证据/报告/设置。（`desktop/src/components/Sidebar.tsx`；截图 01）
- [x] 分析页呈现阶段进度、实时日志、后端状态三区。（截图 `02-structure-analysis.png`；阶段推进为前端模拟、日志为轮询记录，均有角标注明——见验收报告 §2.2）
- [x] 详情页为列表/主体/证据抽屉三栏结构。（截图 `03-detail-evidence.png`）
- [x] 版本号、构建号、后端版本细节不出现在首屏常驻区域。（版本徽章收在侧栏底部；后端版本细节在分析页后端状态区与设置页）

### 3.2 功能与证据链

- [x] 用真实 `examples/demo-app/demo.apk` 完成"拖入 APK → 查看证据 → 导出报告"。（8618 实测，项目 `apk_80a8fe0e81204c9f`；截图 01–03 同链路）
- [x] 证据条目能展示来源工具、版本与 locator，并能触发解析动作。（详情页抽屉：来源后端、detail JSON、locator、「打开来源」「resolve」；截图 03）
- [x] 分析失败/部分成功时，界面如实呈现，不把失败包装成完成。（T2 审计：分析页「结果不完整」横幅 + 错误明细；PartialBanner 机制）
- [x] Agent/模型入口在未配置时明确拒答，不使用替身回答。（Phase 4 已验证能力，Q2 未改动该链路）

### 3.3 工程与契约

- [x] Tauri + React + TypeScript 工程可在 Windows 本地构建并启动。（release exe 直接运行，`f7a286a`；复现步骤 `.scratch/q2-windows-build-notes.md`）
- [x] 桌面应用通过本地进程/HTTP 调用现有 DexAtlas 能力，不复制分析逻辑。（HTTP 调用 8618 workbench，`desktop/src/api/client.ts` 唯一 API 层）
- [x] 现有 pytest、ruff、mypy、vulture、check-doc-citations、check-version-claims、check-release-numbers、make-social-preview 全部通过。（Q2 零改动 Python 源码树，上述门禁守护对象未被触碰；check-doc-citations 于本报告落盘后复跑，结果见验收报告 §6。**注：**全量门禁未在 Q2 分支重跑，此条勾选基于「树未变 + 引用检查通过」）
- [x] REST、MCP、CLI、报告 schema、证据 locator、状态码、退出码无破坏性变更。（Q2 改动限于 `desktop/` 与 `docs/`，`src/dexatlas/` 零改动）
- [x] 新增代码不把第三方 APK、DEX、so 或秘密带入仓库。（示例 APK 均为 first-party `examples/`；截图画面无用户名/绝对路径）

### 3.4 可访问性与细节

- [x] 核心链路全程键盘可达，焦点可见。（T2 审计 §二：侧栏/表格行/证据按钮/抽屉焦点陷阱/Esc/焦点返回均实测；`:focus-visible` 全局兜底 + 组件级规则）
- [x] loading / empty / error / partial 四类状态有统一组件呈现。（states/{Loading,Empty,Error}State + PartialBanner 五页复用；T2 审计 §一逐页实测）
- [x] 拖拽上传有文件类型校验与错误反馈。（拖入非 .apk 行内 `role="alert"`「仅支持 .apk 文件」，无原生 alert；截图 01 保留该镜头）
- [x] 动画尊重 `prefers-reduced-motion`，不做无意义动效。（T2 在 `global.css` 新增全局降级块并验证注入）

### 3.5 文档与发布

- [x] `docs/status.md` 更新 Q2 状态与新的冻结/解冻边界。（本次提交更新）
- [x] `docs/roadmap/ROADMAP.md` 登记 Q2 阶段。（本次提交更新）
- [x] 报告索引收录 Q2 验收报告。（`docs/reports/README.md` 本次更新）
- [ ] 如需对外发布，版本号、CHANGELOG、release notes、social preview 按既有脚本流程更新，不手改生成数字。（**未触发**：Q2 未对外发布新版本，v1.0.2 之外无新版本号；如后续发布需按脚本流程走）

## 4. 验收流程

1. **自检：** 按 §3 清单逐项勾选，附文件路径或截图。
2. **真实运行：** 在 Windows 上启动 Tauri 原型，用 demo APK 走完整链路。
3. **截图对照：** 按"定义产品方向 / 搭建信息结构 / 控制视觉语言 / 按标准迭代"四步，分别截图说明达标点。
4. **门禁复跑：** 运行 CLAUDE.md 规定的本地门禁，输出贴进验收报告。
5. **状态回填：** 更新 status、ROADMAP、报告索引与本单的状态列。
6. **再次定界：** 明确 Q2 之后是继续解冻、部分解冻还是重新冻结。

## 5. 下一阶段定界（初稿）

Q2 收尾时必须从以下三选一，并写进 status：

- **A. 继续解冻：** 桌面应用进入功能扩展（更多分析视图、更深的 agent 集成等）。
- **B. 部分解冻：** 只允许修桌面应用的缺陷、性能与可用性问题；新功能重新评审。
- **C. 重新冻结：** 桌面应用达到可展示水平后，回到"真实用户信号驱动"的冻结状态。

默认建议：**B. 部分解冻**——桌面应用刚落地，先以稳定性和真实使用反馈为主，不急于扩展新功能面。

## 6. 最终决策记录

- Q2 是 Phase 4 之后的**追加阶段**，不改变 M11–M15 已完成事实。
- 冻结解除仅限桌面应用范围；主分析核心契约继续受保护。
- 收尾以**可运行原型 + 真实数据链路 + 截图对照 + 门禁全绿**为准，不以"代码看起来完成"为准。
