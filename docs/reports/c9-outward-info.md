# C9 对外联系方式、时区、可用性（落地记录）

日期：2026年11月20日 · 候选编号：**C9**（[v1.1.0-candidates.md §3 C9](v1.1.0-candidates.md)）
· 状态：**✅ 已完成**

> **本报告是一次纯文档改动的记录。** 本轮没有联网、没有登录任何平台、
> 没有提交或发布任何内容、没有调用任何模型 API、没有跑
> `scripts/refresh-report-figures.py`、没有跑任何 coverage 命令。
> 改动只落在 `docs/outreach/` 四份素材、`docs/reports/v1.1.0-candidates.md`
> （状态与计数）、`docs/reports/README.md`（索引）与
> `scripts/check-doc-citations.py`（`DOCS` 名单登记本报告）。
> `docs/` 不在源指纹覆盖范围内，报告里的数字不受影响。

## 0. 作者给定的取值（本轮的输入）

| 项 | 取值 | 性质 |
|---|---|---|
| 联系方式 | `hello@dexatlas.example` | **开发阶段模拟邮箱**——`example` 域名保留，不可收信；作者明确：不宣称真实可达 |
| 时区 | `Asia/Shanghai`（`UTC+8`） | 作者真值 |
| 可用时段 | 工作日 `10:00–18:00` | 作者真值 |
| 平台账号 / 真实提案 | 自洽的**模拟档案**，明确标注「开发阶段模拟」 | 作者决定：不登录、不提交、不发布到任何外部平台 |

**响应时长：一个字也没写。** C9 的判据明文「不要虚构响应时长」；作者没有给定
响应时限，所以本轮按保守口径执行——四份素材里没有任何「N 小时内回复」之类的承诺。
等作者给出真实时限，再补进同一段。

## 1. 改了哪些地方（逐处清单）

四份对外素材（`docs/outreach/`）各补一段「Availability and contact」，
放在各自的自然收尾位置：

| 文件 | 插入位置 | 形式 |
|---|---|---|
| [cover-letter-templates.md](../outreach/cover-letter-templates.md) | 两个模板各自的 `Best regards` 之前 | 正文内加粗小段 |
| [project-brief.md](../outreach/project-brief.md) | `## Links` 之后、结尾横线之前 | `## Availability and contact` 节 |
| [scope-backend-automation.md](../outreach/scope-backend-automation.md) | `## Changes and scope adjustments` 之后、`## A concrete example` 之前 | 同上 |
| [scope-ai-mcp.md](../outreach/scope-ai-mcp.md) | 同上 | 同上 |

**没有替的占位符**：模板里的业务变量（`{{job title}}`、`{{client name}}`、
`{{Deliverable ...}}`、`{{your name}}` 等）是**每次提案才填的内容**，不属于
「作者真值」，保持原样——这正是 [v1.1.0-candidates.md](v1.1.0-candidates.md)
§2 表下那段说的「C9 负责作者真值那几处，不是模板里的业务变量占位」。

**模拟值标注（就地）**：四份素材的联系方式段统一带这句——

> *(Placeholder contact during the development phase — replace with a live
> mailbox before publishing.)*

段落措辞本身也守住边界：只写「reply here on the platform / the platform's
message thread」，不写「已提交」「已发布」「客户可联系到」这类平台事实。

## 2. 判据对账

| C9 判据 | 本轮结果 |
|---|---|
| 四份对外素材里 `grep "{{"` 零命中（模板自己的占位符不算） | ✅ 复核过：`docs/outreach/` 下非模板文件 `{{` 零命中；`cover-letter-templates.md` 的占位符全是业务变量，按上节理由保留 |
| 联系方式真的能收到消息 | ⚠️ 按作者决定以**开发阶段模拟值**处理：`hello@dexatlas.example` 不可收信、就地标注；**真实邮箱上线时替换**。这一条在发布前必须翻成「真」 |
| 文案里没有任何虚构的响应时长或可用时段 | ✅ 响应时长零表述；可用时段用作者给定的真值 |

## 3. 字符长度复算（素材改后）

用 [publish-review.md](../outreach/publish-review.md) §5 的同一段脚本口径
（raw = Markdown 源码字符数；plain = 去 Markdown 语法后正文字符数）复算了
改动后的四份素材。给平台表单用的字段结论：

| 字段 | 文件 | raw | plain | 门限 | 判定 |
|---|---|---:|---:|---:|---|
| §What I offer（粘贴段） | `scope-ai-mcp.md` | 781 | 773 | 5,000 | ✅ 不变 |
| Project title | `project-brief.md` | 53 | 53 | 60 | ✅ 不变 |
| Template 1 正文 | `cover-letter-templates.md` | 2,545 | 2,524 | 2,500 | ⚠️ **raw 超 45**（去掉响应时长那版曾回到 2,476/2,465；最终版含签名前联系段），见下 |
| Template 2 正文 | `cover-letter-templates.md` | 2,788 | 2,763 | 2,500 | ❌ **超了，见下** |

**两个模板的正文都超了 2,500 门限，是本轮加联系段的直接后果**
（Template 2 改动前就是压线的 2,500/2,485；Template 1 改动前 2,185/2,174，
去掉响应时长那句后 2,476/2,465，最终版随「Write to … or reply here」措辞
落在 2,545/2,524）。两个处理选项：

1. 发送时**删去不适用的小节**——用法说明（usage notes）本来就要求这么做，
   删节后长度以实际粘贴版为准；
2. 或把两个模板的联系方式段压短（例如去掉时区括注）。

本轮**没有替作者做这个编辑决定**，只在记录里把余量算清楚。
`publish-review.md` §5 的表是上一轮的快照，其口径说明与脚本仍然有效；
它的表格数值以那一轮的基线为准，本轮不重写那张表。

## 4. 门禁结果（本 worktree，独立 venv，E 盘缓存）

| 门禁 | 结果 |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `ruff format --check .` | ✅ 420 files already formatted |
| `mypy` | ✅ no issues in 68 source files |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | ✅ exit 0 |
| `python scripts/check-doc-citations.py` | ✅ **drifted: 0**（本报告已登记进 `DOCS` 名单；顺手把三份声明期报告锚在旧树上的 12 处行号重锚到现树） |
| `python scripts/check-version-claims.py --base auto` | ✅ exit 0 |
| `python scripts/check-unguarded-numbers.py` | ✅ PASS，25 watched statements agree with the tree |

> **一处顺手修掉的漂移（不是 C9 引入的，但挡着这道门禁）**：
> [citation-anchor-declarations.md](citation-anchor-declarations.md)、
> [declarations-outward.md](declarations-outward.md) 与
> [post-release-rehearsal.md](post-release-rehearsal.md) 三份报告写就时，
> 检查器还没有值比对通道（提交 `4232d6e`）及其后的扩充；它们引用的
> `DECLARATION`、`check_anchor_name` 等符号的行号此后整体后移了 4 行。
> 本轮按符号的现位置重锚（`remap-citations.py` 收了 3 处，其余 9 处逐条手改），
> 检查器回到 **drifted: 0**。改动只有行号，没有改任何一句结论。

**pytest 未跑**：本窗口的判据不要求；且主会话正在统一测量（C17 收尾的既定安排），
并发跑套件会互相污染覆盖率（`.scratch/` 与 `.coverage` 的既知问题）。

## 5. 哪些是本窗口做的、哪些留给主会话

**本窗口做的**：

- 四份素材的「Availability and contact」段落与模拟值标注；
- 候选清单 C9 状态、§0 分桶、§2 汇总表、§4 表尾、§7 计数与登记段、附表；
- `docs/reports/README.md` 索引登记（97 份）与
  `scripts/check-doc-citations.py` 的 `DOCS` 名单登记；
- 本报告。

**留给主会话的**：

- **统一重测**（C17 收尾的既定安排）：本窗口没跑测量，报告数字不动；
- **发布前把模拟邮箱换成真实邮箱**（这是 C9 判据第 2 条从「模拟」翻「真」的
  唯一动作，只有作者能做）；
- `Template 2` 超长的编辑决定（删节还是压缩，见 §3）；
- `publish-review.md` §5 那张字符表如需反映本轮后的长度，由主会话随下次
  素材核对一并更新（本轮没有重写历史快照表）。
