# 发版后运营清单 — v1.1.0 起

**日期：** 2026-11-25 · **性质：** 运营备料（作者指示"先不正式运行"，本清单只列动作，不含任何需要作者账号的执行步骤）· **适用：** v1.1.0 及之后的每个版本

## 1. 发布当天（每版必做）

| # | 动作 | 位置 | 完成判据 | 账号需求 |
|---|---|---|---|---|
| 1 | 核对 GitHub Release 页面渲染（正文、tag、assets） | https://github.com/gg320324492-lgtm/dexatlas/releases | 正文与 `docs/releases/<tag>.md` 一致；tag 指向发版提交 | 作者（或已登录 CI） |
| 2 | 核对 tag CI 全绿（14 项，含 tag-only 测量门禁） | Actions | 全部 success（tag-only 项按设计 skip） | 无 |
| 3 | `check-release-numbers --tag <tag>` 退出码 0 | 本地 | mismatches 0、published body read | 无 |
| 4 | README 徽章与 status.md 的版本行与发布一致 | 仓库 | 三处同版本号 | 无 |

## 2. 发布后一周（每版）

| # | 动作 | 频率 | 完成判据 |
|---|---|---|---|
| 1 | issue triage：新 issue 按缺陷/功能/文档分桶，缺陷标 `bug`，桌面应用相关标 `desktop` | 每 2 天 | 无未分桶 issue |
| 2 | CI 失败跟进：main 或 tag 上任何红 run 当天定位 | 每次 push | 无超过 24h 的红 run |
| 3 | 反馈收集：记录来自 issue/discussion/私聊的反馈条目（日期/来源/诉求/处置） | 持续 | 反馈台账有新增即更新 |

## 3. 反馈收集渠道（建议，待作者选定）

| 渠道 | 用途 | 现状 |
|---|---|---|
| GitHub Issues | 缺陷与功能请求的主台账 | 已可用（仓库公开） |
| GitHub Discussions | 使用问答与反馈（需作者开启 Discussions） | 未开启 |
| README 徽章下方"反馈"链接 | 把读者引到 Issues | 待加一行链接 |

## 4. 指标（记录，不设目标）

- 每版 release 页面浏览/下载（GitHub Insights，需作者账号查看）
- issue 新增/关闭数（可由 CI 或脚本按周统计，无需账号）
- 桌面安装包构建产物体积与启动时间（已在性能基线报告记录口径）

## 5. 下一版本触发条件（沿用收尾单的解冻信号）

- 同一缺陷被 ≥2 个不同来源提及 → 优先修
- 桌面应用被真实使用并产生 ≥3 条可用反馈 → 评估是否结束"部分解冻 B"
- 出现需要新分析能力/新契约的诉求 → 按 Freeze 规则重新评审
