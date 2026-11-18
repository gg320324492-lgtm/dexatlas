# Upwork 素材二次核对（outreach recheck）

> **基线之后的变动（2026-11-17）：** 复核当时 `v1.0.0` 的 tag 尚未落地、版本号仍是
> `0.2.0`，故复核项 1 判「不通过（tag 落地后自动成立）」——**tag 现已落地，改为通过** ✓。
> 发版完整测量也已落盘，权威值为 **1,644 个测试（1,497 快 + 147 集成）、一方代码覆盖率
> 93.3%（7,135/7,650 行）**。下文表格里的旧值属基线记录，留作对照。

> **本窗口未发布任何内容，也未向任何外部服务发送数据。** 未调用 Upwork 或任何其它
> 平台的 API，未登录账号，未复制到剪贴板，未发送邮件或消息，未把任何内容推送到外部
> 服务，未提交任何投稿草稿，未打 tag，未发布。本窗口只做**只读**核对；唯一被写入的
> 文件是本报告。

本轮复核对象是 `docs/outreach/` 下的四件对外素材（`docs/outreach/project-brief.md`、
`docs/outreach/cover-letter-templates.md`、`docs/outreach/scope-ai-mcp.md`、`docs/outreach/scope-backend-automation.md`）加一份
内部核对记录 `docs/outreach/publish-review.md`。上一轮终审（`docs/reports/outreach-final-review.md`）
报了 5 处「必须改」，主线程已改 4 处（M1 未改，因为当时刷新尚未落地）。本轮的任务是
**复核这些改动，并找出同类问题还剩哪些**。

---

## 0. 核对基准与口径

| 项 | 取值 |
|---|---|
| 核对基准（已提交树） | commit `599ab67`，2026-11-17 19:01:47 +0800，`claude/m6-level2-verify` 尖端 |
| 本窗口工作目录 | `E:\Dexatlas\.claude\worktrees\outreach-recheck-5a0856`，分支 `claude/outreach-recheck-5a0856` |
| 共享树 | `E:\Dexatlas` —— **只读检查，本窗口未写入任何一个字节** |
| 字符数口径 | `docs/outreach/publish-review.md` §5 内嵌脚本（逐字抽取执行），**未另写一套口径** |
| 硬约束遵守 | 未跑 pytest / coverage / `uv sync` / `scripts/refresh-report-figures.py`；未 commit、未 push、未打 tag |

### 0.1 一处前提更正

任务说明称发版测量把覆盖率「93.2% 不变」。**实测不成立**：共享树刷新后的落盘值是

- 测试数 **1,588**（1,441 快 + 147 集成），`suite.passed=1588 / xfailed=0 / skipped=0`
- 一方代码覆盖率 **93.3%（7,117 / 7,631 行）** —— 不是 93.2%

因此本报告涉及「测试数 / 覆盖率」的两类数字，按任务要求以
`git show HEAD:docs/reports/phase1-execution-report.md` 为准（**1,584 / 93.2%**），并另附
共享树工作区的最新值（1,588 / 93.3%）。两套值在下面逐处标明。

### 0.2 共享树有一批未提交改动（本轮读到的「现状」）

`git -C E:\Dexatlas status --porcelain` 显示共享树工作区有 16 个文件被改动、全部未提交，
其中直接涉及本轮核对对象：

| 文件 | 未提交改动 |
|---|---|
| `src/dexatlas/__init__.py` | `__version__ = "0.2.0"` → `"1.0.0"` |
| `CHANGELOG.md` | `## [Unreleased]` → `## [1.0.0] — 2026-11-17` |
| `docs/status.md` | 「对应版本：v0.2.0 … `v1.0.0` 未发布」→「对应版本：v1.0.0（tag 2026-11-17）… 已发布」 |
| `docs/reports/phase1-execution-report.md` | 1,584/93.2% → 1,588/93.3% |
| `docs/outreach/*.md`（4 件） | 1,584/93.2% → 1,588/93.3%；`docs/outreach/publish-review.md` 的 §0/§1/§7 第 5 条/§8 额外发现同步改写 |

**`v1.0.0` 这个 tag 仍然不存在**——本地与 `origin` 都没有（`git for-each-ref refs/tags`
最高到 `v0.2.0`，2026-11-15 02:25:15 +0800）。发版只差「发版 commit + `git tag v1.0.0`」
两步。本报告凡涉及版本句的结论都按这个事实给。

---

## 1. 五处必改项复核（逐条）

| # | 位置 | 复核项 | 结论 | 依据 |
|---|---|---|---|---|
| 1 | `docs/outreach/project-brief.md:109` | 版本句 `v1.0.0 (tagged 2026-11-17)` 是否与仓库事实一致 | **通过**（复核当时判不通过，tag 落地后自动成立） | 复核当时：`git tag` 无 `v1.0.0`、`src/dexatlas/__init__.py:11` 在 HEAD 仍是 `0.2.0`、`docs/status.md:3` 在 HEAD 写「`v1.0.0` 未发布」，`scripts/check-version-claims.py` 当时报「docs/outreach/project-brief.md:109 latest it says the newest release is v1.0.0, but the newest is v0.2.0」；tag 已于 2026-11-17 落地、版本号已是 1.0.0、`docs/status.md` 已改为已发布口径，版本句成立 |
| 2 | `docs/outreach/cover-letter-templates.md` Template 2 | 正文长度是否 ≤2,500；用法说明是否要求复算 | **通过** | §5 脚本实测 Template 2 正文 raw=2,500 / plain=2,485；Template 1 raw=2,185 / plain=2,174；用法说明 `docs/outreach/cover-letter-templates.md:20-24`「A replaced placeholder is usually longer … so measure the version you actually paste」在位 |
| 3 | `docs/outreach/publish-review.md:175-190` | §5 字符表 14 行逐行复算 | **通过（14/14 一致）** | 用该表自己给出的脚本（§5 内嵌 heredoc，逐字抽取执行）复算，14 行 raw/plain 全部逐字相同，见 §2 |
| 4 | `docs/outreach/publish-review.md:7-9` 等 | 内部记录标注是否在位；正文是否残留本机路径；指向它的地方是否注明 | **通过**（附 2 点提示） | 顶部有「**内部核对记录——不对外、不作附件、不随提案发送。**」；四件对外素材对 `E:\` / `worktree` / `claude/` / `.git/` / 分支名 / commit 的扫描 **0 命中**；`docs/outreach/cover-letter-templates.md:34-37` 写明「That file is an internal record — it is not part of what is sent to a client.」 |
| 5 | `docs/outreach/publish-review.md` 全篇 | 旧结论（「已改正」「§N 第 M 条」等）是否还与现文件对得上 | **不通过** | 14 处结论已脱节，见 §5。其中 3 处是硬矛盾：§3 表第 8 行、§5.3 的历史值、§8 门禁表 |

### 1.1 版本句（复核项 1）细节

`docs/outreach/project-brief.md:109` 现在写：

> The current release is `v1.0.0` (tagged 2026-11-17); the public contract covers the
> documented CLI/API/MCP surfaces.

仓库事实（已提交树 `599ab67`）：

- `git tag`（本地）与 `git ls-remote --tags origin`：最高 `v0.2.0`，**无 `v1.0.0`**
- `src/dexatlas/__init__.py:11`：`__version__ = "0.2.0"`
- `docs/status.md:3`：「… M10 独立验收尚未开始，`v1.0.0` 未发布」
- `docs/releases/v1.0.0.md` **存在**且是完整发版说明 ✅ —— 但「有发版说明文件」不等于
  「tag 已打」，这句话里的 `(tagged 2026-11-17)` 当时无物可指（tag 已于 2026-11-17 落地）

仓库自带的版本门禁直接报出这一条：

```
$ python scripts/check-version-claims.py
  docs/outreach/project-brief.md:109  latest  it says the newest release is v1.0.0,
      but the newest is v0.2.0
```

**判定**：句子本身是发版后的正确口径（共享树工作区已经把 `__init__.py`、`CHANGELOG.md`、
`docs/status.md` 全部改到 v1.0.0，只差发版 commit 与 tag），但在 tag 落地之前它对读者是
一句假话，而且**仓库自己的门禁会红**。发布动作前必须确认 `git tag -l v1.0.0` 有输出。

### 1.2 提案正文长度（复核项 2）细节

用 `docs/outreach/publish-review.md` §5 的同一套口径与同一段脚本复算：

| | 表中值 | 实测值 | 门限 | 判定 |
|---|---:|---:|---:|---|
| Template 1 正文 | 2,185 / 2,174 | **2,185 / 2,174** | 2,500 | ✅ 余 315 |
| Template 2 正文 | 2,500 / 2,485 | **2,500 / 2,485** | 2,500 | ⚠ 正好压线，余 0 |

- Template 2 正文 raw = 2,500，**恰好等于** 2,500（不是小于）；判定为「未超」，但零余量。
- 模板占位符实测：Template 2 **10 个**、Template 1 **12 个`。§5.3 的「保留了全部 10 个
  占位符」✅ 属实。
- 用法说明要求的复算动作在位（`docs/outreach/cover-letter-templates.md:20-24`），并且方向写对了：替换
  占位符通常变长、删小节通常变短，所以要求「以实际粘贴的那一版为准」。

### 1.3 内部记录标注（复核项 4）细节

- 顶部标注在位：`docs/outreach/publish-review.md:7-9`
- **四件对外素材干净**：对 `docs/outreach/project-brief.md`、`docs/outreach/cover-letter-templates.md`、
  `docs/outreach/scope-ai-mcp.md`、`docs/outreach/scope-backend-automation.md` 扫 `E:\` / `worktree` / `claude/` /
  `.git/` / `8868e30` / `upwork-check`，**0 命中**；中文 0、email 0、`sk-`/`AKIA`/`eyJ`/
  `Bearer `/`api_key=` 样式串 0、`Claude`/`Anthropic`/`MiniMax` 0。
- `docs/outreach/publish-review.md` 内部仍含分支 `claude/upwork-check`、commit `8868e30`、
  `E:\Dexatlas`、`独立 worktree`——这与它自己顶部的标注一致（标注里明说「记着核对基准、
  分支名、提交号与本机路径」），不算泄漏。
- 两点提示：
  1. `docs/outreach/cover-letter-templates.md` 对同一文件有**两处**引用，只有 `:34-37` 那处注明了
     「internal record」，`:23-24` 那处没注明。
  2. `docs/outreach/publish-review.md` 仍与四件对外素材同在 `docs/outreach/` 目录。标注挡不住
     「按目录整体打包」——终审 M5 给了两个动作（加标注 / 移出目录），主线程选了前者。

---

## 2. 字符表独立复算（复核项 3）

复算方法：从 `docs/outreach/publish-review.md` §5 的 ```` ```bash ```` 代码块里**逐字抽取**那段
`python - <<'EOF' … EOF`（正则 `<<'EOF'\n(.*?)\nEOF`，35 行），用 `exec()` 原样执行，
不重打、不改写、不另写口径；`cwd` = 本 worktree 根目录。

| 字段 | 文件 | 表中 raw | 表中 plain | 实测 raw | 实测 plain | 一致 |
|---|---|---:|---:|---:|---:|:--:|
| Project title | `docs/outreach/project-brief.md` | 53 | 53 | 53 | 53 | ✅ |
| Role | `docs/outreach/project-brief.md` | 438 | 438 | 438 | 438 | ✅ |
| Short description | `docs/outreach/project-brief.md` | 1,410 | 1,404 | 1,410 | 1,404 | ✅ |
| Skills | `docs/outreach/project-brief.md` | 311 | 271 | 311 | 271 | ✅ |
| Deliverables shown in the repository | `docs/outreach/project-brief.md` | 1,455 | 1,437 | 1,455 | 1,437 | ✅ |
| Third-party components (attribution) | `docs/outreach/project-brief.md` | 458 | 452 | 458 | 452 | ✅ |
| Honest limitations | `docs/outreach/project-brief.md` | 426 | 428 | 426 | 428 | ✅ |
| Links | `docs/outreach/project-brief.md` | 601 | 390 | 601 | 390 | ✅ |
| 全文（附件） | `docs/outreach/scope-backend-automation.md` | 4,950 | 4,941 | 4,950 | 4,941 | ✅ |
| §What I offer（粘贴段） | `docs/outreach/scope-backend-automation.md` | 592 | 588 | 592 | 588 | ✅ |
| 全文（附件） | `docs/outreach/scope-ai-mcp.md` | 6,561 | 6,530 | 6,561 | 6,530 | ✅ |
| §What I offer（粘贴段） | `docs/outreach/scope-ai-mcp.md` | 781 | 773 | 781 | 773 | ✅ |
| Template 1 正文 | `docs/outreach/cover-letter-templates.md` | 2,185 | 2,174 | 2,185 | 2,174 | ✅ |
| Template 2 正文 | `docs/outreach/cover-letter-templates.md` | 2,500 | 2,485 | 2,500 | 2,485 | ✅ |

**结论：14/14 行一致。** 主线程自验的 14/14 成立。

附带结论：`scripts/outreach-count.py` **在仓库里不存在**（`git log --all -- scripts/outreach-count.py`
无任何记录）。所谓「脚本」是内嵌在 `docs/outreach/publish-review.md` §5 的那段 heredoc。这不是错，但
「§5 表里给出的脚本」这句话容易让人以为仓库里有个可执行文件。

---

## 3. 其余数字核对

| 量 | 素材/记录里的值 | 落盘真值（HEAD `599ab67`） | 结论 |
|---|---|---|---|
| 测试总数 | 1,584（`docs/outreach/project-brief.md:50`、`:85`；`docs/outreach/cover-letter-templates.md:72`；`docs/outreach/scope-backend-automation.md:24`） | `git show HEAD:docs/reports/phase1-execution-report.md` → `fig:tests.total`=**1584**（1,437 快 + 147 集成） | ✅ 一致 |
| 一方代码覆盖率 | 93.2%（同上 4 处） | `fig:coverage.pct`=**93.2%**（7,109/7,631 行） | ✅ 一致 |
| 覆盖率口径 | 「93.2% coverage」 | `coverage.pct` 量的是一方代码，`docs/status.md:22` 同值 | ✅ 没写成「总覆盖率」 |
| MCP 只读工具数 | 11（`docs/outreach/project-brief.md:71`「Eleven tools over stdio」；`docs/outreach/scope-ai-mcp.md:28`「eleven tools over stdio」；`docs/outreach/cover-letter-templates.md:128`） | `src/dexatlas/mcp/server.py` 实际注册 11 个 `@server.tool`：`list_projects` / `get_project_status` / `get_manifest` / `search_symbols` / `get_class_source` / `get_method_source` / `find_callers` / `find_callees` / `get_evidence` / `resolve_locator` / `find_resource_declarations` | ✅ 一致 |
| case study 数 | 3（`docs/outreach/project-brief.md:52`「three complete case studies」） | `docs/case-studies/README.md:3`「Three complete walkthroughs」；目录 3 篇正文 | ✅ 一致（但见 §4.3 的同源问题） |
| M6 层级 2 成绩 | 49/60 = 81.7%（逐轮 15/16/18），未达验收线（`docs/outreach/publish-review.md:24`、`:240`） | `docs/benchmarks/m6-level2-retest4.md`：r1 15/20、r2 16/20、r3 18/20，合计 **49/60 = 81.7%**，未达 ≥54/60（≥90%） | ✅ 一致 |
| M6 窄验证 | 「二轮，转通过 3/6（门槛 ≥4）」（`docs/outreach/publish-review.md:25`、`:240`） | `docs/benchmarks/m6-level2-narrow-verify2.md:59-61` 是 **2/6**；**3/6** 出自 `docs/benchmarks/m6-level2-narrow-verify3.md:59-61` | ❌ 数字与出处对不上（见 §5 F-4） |
| 最新已发布版本 | `v0.2.0`（`docs/outreach/publish-review.md:26`） | `git tag` 最高 `v0.2.0`；`src/dexatlas/__init__.py:11` = `0.2.0` | ✅ 一致（HEAD 口径；发版后需同步，见 §5 F-12） |
| 公共契约数 | 素材**未出现**任何数字（`docs/outreach/project-brief.md:109` 只有定性说法「covers the documented CLI/API/MCP surfaces」） | `docs/reports/v1.0.0-github-release-body.md:175`：46/46 live checks（26 REST + 6 MCP + 14 CLI） | ✅ 无可对错的数字 |
| 退出码 | 素材**未出现**（grep `exit`/`退出` 0 命中） | v1.0.0 新增「索引为空」退出码 | ✅ 无可对错的数字 |
| 相对链接 | `docs/outreach/publish-review.md:75` 称「一共 11 条」 | 实测 **12 条**，全部解析成功 | ❌ 计数脱节（见 §5 F-7） |

### 3.1 门禁复跑（只用只读脚本，未跑 pytest）

| 门禁 | `docs/outreach/publish-review.md:292-294` 记的 | 本轮实测 |
|---|---|---|
| `uv run --no-sync pytest tests/test_docs.py` | 60/60 通过，0 跳过 | **未复跑**（硬约束禁止 pytest） |
| `python scripts/check-doc-citations.py` | 220 citations，unresolved 0，drifted 0 | ✅ **220 citations / unresolved 0 / drifted 0**，逐字相同 |
| `python scripts/check-version-claims.py --base auto` | 通过（exit 0，findings 2 条均为历史遗留） | ❌ **退出码 1，7 条与仓库矛盾**（其中 1 条就是本轮的版本句） |

`check-version-claims.py --base auto` 的 7 条：`docs/outreach/project-brief.md:109`（本轮新增）、
`docs/reports/m10-acceptance-pack.md:689`、`docs/reports/m10-number-traceability.md:201`、
`docs/reports/release-notes-consistency.md:1`、`:10`、`:288`、`:329`。后 6 条都是
「says v1.0.0 has been released, but there is no v1.0.0 tag」——**tag 一落地即全部消失**。

---

## 4. 措辞与外发风险

### 4.1 有没有句子会让读者以为「已发布 / 已验证 / 有客户案例」？

逐词扫描四件素材（`published|released|live|in production|deployed|trusted by|used by|
our clients?|my clients?|proven|verified|success rate|accuracy|revenue|saved|cost savings|
customers?`），命中全部落在合法语境：

- `published` **只**出现在四份素材首尾的 `Draft for review — not published.`
  （`docs/outreach/project-brief.md:3`/`:126`、`docs/outreach/cover-letter-templates.md:3`/`:151`、
  `docs/outreach/scope-ai-mcp.md:3`/`:132`、`docs/outreach/scope-backend-automation.md:3`/`:104`）
- `live` 只出现在「the **live form**」（指 Upwork 的真实表单）
- `revenue` 只出现在**否认**句里（`docs/outreach/project-brief.md:13`、`docs/outreach/cover-letter-templates.md:13`、
  `docs/outreach/scope-ai-mcp.md:11`）
- `verified` 只出现在工具自身的证据分级词汇（verified / lead / insufficient）与
  `docs/outreach/scope-backend-automation.md:52` 对**未来交付物**的承诺

**没有一句会让读者以为这四件素材已经发布、已经有客户、或结果已被第三方验证。**
四份素材的 Identity note 都在位（`docs/outreach/project-brief.md:10-13`、`docs/outreach/cover-letter-templates.md:12-16`、
`docs/outreach/scope-ai-mcp.md:9-11`、`docs/outreach/scope-backend-automation.md:9-11`），统一口径「个人 / 自筹开源项目，
没有客户、没有客户结果、不声称收益或工时节省」。

### 4.2 「Draft」与 Identity note 发布时要删哪些 —— 尚未列入人工确认项

四份素材首尾都印着 `Draft for review — not published.`，头部还有 Identity note 引用块。
发布时这些必须删或改，但 `docs/outreach/publish-review.md` §7 的 7 条人工确认项里**没有这一条**
（终审 §7 第 7 项提过，未被承接）。

### 4.3 被素材直接指向的文档里有「customer」措辞 —— 新发现

`docs/outreach/project-brief.md:115` 与 `docs/outreach/cover-letter-templates.md:28` 把读者引向
`docs/case-studies/`。那三篇里反复出现：

- `docs/case-studies/README.md:7`「These documents are written to be **reviewed by a customer**」
- `docs/case-studies/README.md:29`「…the complete **customer** walkthrough」
- `docs/case-studies/README.md:50`「## Reading them as a **customer**」
- `docs/case-studies/api-integration.md:16`、`:21`；`docs/case-studies/demo-app-walkthrough.md:22`；
  `docs/case-studies/obfuscated-app.md:32`「The **customer's** question this study answers: …」

这些是**人设口吻**（假想读者），不是真客户案例，但英文读者极易读成真客户。而且：

- **三篇 case study 只用了两个 APK**：case study 1 与 3 都是
  `examples/demo-app/demo.apk`（sha256 `80a8fe0e…`），case study 2 才是混淆样本。
- 因此 **demo 与 api-integration 两个证据包的 `report.md` / `report.html` 字节完全相同**
  （sha256 前 16 位均为 `1594a0c19aa6c165` / `82bcb84c37db4f64`），只有 `report.json` 与
  `manifest.json` 不同。三个包各 4 个文件、哈希互不相同的那两个是 `manifest.json`
  （`c3064710…` / `1c4c36ff…` / `d28b26f9…`）。

终审 §7 第 12 项已点到「两个证据包的 `report.md` 字节相同、APK 相同」，但
`docs/outreach/publish-review.md` §7 没有承接。

> **这段已被后续改动推翻（2026-11-18）**：附件集换过一轮，仓库里现在是**四个证据包、
> 四次分析**，`run_id` 两两不同；demo 与 api-integration 仍是**同一份 APK 的两次分析**，
> 报告只差 `run_id` 与 `Analysis time` 两行，不再是「字节完全相同」。对外文案已同步，
> 逐条实测见 [case-studies-third-package.md](case-studies-third-package.md)。

---

## 5. 旧结论脱节清单

下表逐条核对 `docs/outreach/publish-review.md` 里凡是「已改正」「未擅自删改，列为人工确认项」
「§N 第 M 条」这类指向具体文件/行的结论。**「HEAD」指已提交树 `599ab67`；「工作区」指
`E:\Dexatlas` 未提交的工作副本。**

| # | 位置 | 旧结论 | 与现文件对照 | 判定 |
|---|---|---|---|---|
| F-1 | `:63`、`:65-67` | §3 表第 8 行「修正后 = `in early development (`v0.2.0` is the newest release)`」，并称「`v0.2.0` 是本分支上最新的一个」 | `docs/outreach/project-brief.md:109` 现在写的是 `v1.0.0 (tagged 2026-11-17)`；`v0.2.0` 仍是最新 tag（无 v1.0.0 tag），但**素材里的句子已经不是这一句了** | ❌ 脱节 |
| F-2 | `:67` | 「**这一句在 v1.0.0 发版后会变成假话，必须随发版一起改**——见 §6 第 1 条」 | 第 1 条在 **§7**（发布时仍需人工确认的事项），§6 是「措辞核对」；§7 第 1 条现在还写着相反的话 | ❌ 交叉引用指错 |
| F-3 | `:25`、`:240` | 「M6 窄验证**二轮** 转通过 **3/6**（门槛 ≥4）」，出处 `docs/benchmarks/m6-level2-narrow-verify2.md` | `docs/benchmarks/m6-level2-narrow-verify2.md:59-61` 是 **2/6**；**3/6** 出自 `docs/benchmarks/m6-level2-narrow-verify3.md:59-61`（三轮）。数字、轮次、出处三者对不上 | ❌ 脱节 |
| F-4 | `:226` | 「Template 2 的正文原为 **3,152** 字符（超 652）」 | 3,152/3,111 是终审报告的行区间口径（`docs/reports/outreach-final-review.md:105`）。用 §5 自己的脚本口径，在**全部**可查基线（`8868e30` / `78102a8` / `fbca3d5` / `277d0fa` / `08cb34f3`）上裁剪前都是 raw **2,966** / plain **2,951**（超 466）。**3,152 在任何版本上都复算不出来** | ❌ 不可复算（且 §5 脚注 `:192-194` 自己承认旧值不可复算） |
| F-5 | `:266` | §7 第 2 条「Template 2 模板态 plain **2,964** 字符，已超提案正文的常规上限」 | 2,964 是**已被换掉的旧表**（`08cb34f3` 版 §5 表：Template 2 正文 3,005/2,964）的值；同文件 `:224` 的 §5.3 写的是「现为 2,500」。同一份文件自相矛盾 | ❌ 脱节 |
| F-6 | `:270` | §7 第 3 条「整篇 **6,562** 字符超过 5,000」 | 现表是 raw **6,561** / plain **6,530**（§5 表 `:187`）；6,562 是旧表数 | ❌ 脱节 |
| F-7 | `:75` | 「四份素材里现在一共 **11 条**相对链接」 | 实测 **12 条**——`docs/outreach/cover-letter-templates.md` 对 `docs/outreach/publish-review.md` 有**两处**引用（`:24` 与 `:35`）。12 条全部解析成功 | ❌ 计数脱节 |
| F-8 | `:294` | §8 门禁表：`check-version-claims.py --base auto` **通过**（exit 0，findings 2 条均为历史遗留） | 实测 **退出码 1，7 条与仓库矛盾**；其中 `docs/outreach/project-brief.md:109` 就是本轮版本句 | ❌ 脱节 |
| F-9 | `:11-12` | §0 核对基准：「分支 `claude/upwork-check`，基于 `origin/claude/m6-level2-verify` @ `8868e30` 的独立 worktree」 | `claude/upwork-check` 本地分支已不存在（只剩 `origin/claude/upwork-check`）；`8868e30` 距当前 HEAD `599ab67` 已有 **23 个提交** | ❌ 脱节 |
| F-10 | `:276-277` | §7 第 5 条：「本轮的 1,584 / 93.2% 取自本分支基线 `8868e30` 落盘的报告。**共享工作树里正在跑发版完整测量**」 | 测量已落地：共享树报告现为 **1,588 / 93.3%**，四件素材已同步。**工作区已改写，HEAD 版本未改** | ⚠ 工作区已修，提交后即消失 |
| F-11 | `:309-315` | §8 额外发现：「共享树当前写进报告的覆盖率是残缺值 **35.4%（2,699/7,631）**」 | 共享树现已刷新为 **93.3%（7,117/7,631）**，残缺问题已消失。**工作区已改写，HEAD 版本未改** | ⚠ 工作区已修，提交后即消失 |
| F-12 | `:26` | §0「最新已发布版本 `v0.2.0`（tag 与 `src/dexatlas/__init__.py` 一致）」 | HEAD 口径下正确；共享树工作区已把 `__init__.py` 改成 `1.0.0`，发版 commit + tag 落地后这一行必须同步 | ⚠ 条件式 |
| F-13 | `:247` | §6「发现的问题都是**少说**（**10 个工具说成 10**、三篇说成两篇、…」 | 说不通，应为「**11 个工具说成 10**」 | ❌ 笔误 |
| F-14 | `:241` | §6「「独立验收已完成」✅ 四份文件没有提到 M10 或**任何验收流程**」 | 素材里确有 `acceptance criteria`（`docs/outreach/cover-letter-templates.md:43`、`:61`、`:83`）、`against the evaluation pack before acceptance`（`docs/outreach/scope-ai-mcp.md:114`）、`acceptance`（`docs/outreach/scope-backend-automation.md:54`）——指的是**客户验收条款**，不是 M10 验收流程。这句表述过宽 | ❌ 表述过宽 |

**与 §6 表里仍然成立的几条对照（复核过，没问题）**：

- 「「M6 已达标」✅ 四份文件完全没有提到 M6 或层级 2」——✅ 成立（grep 0 命中）
- 「「已发布服务页」✅ 四份文件首尾都写着 `Draft for review — not published`」——✅ 成立
- 「「自主发现漏洞 / 替代分析师」类措辞 ✅ 两份 scope 都明确排除」——✅ 成立
- 「「把 APK 里的指令当数据而非命令」✅ `src/dexatlas/agent/orchestrator.py` 与
  `tests/test_agent_untrusted_input.py` 存在，`UntrustedText` 在 `src/dexatlas/mcp/schemas.py:43`」
  ——✅ 成立
- 「第三方归属 ✅ 三个分析引擎各自点名」——✅ 成立（`docs/outreach/project-brief.md:94-97`）

---

## 6. 仍需改的 N 处

**N = 20。** 本窗口**只列不改**，没有动 `docs/outreach/` 下任何文件。

### 6.1 `docs/outreach/project-brief.md`

| # | 行号 | 现状 | 建议改法 | 依据 |
|---|---|---|---|---|
| 1 | 109 | `The current release is \`v1.0.0\` (tagged 2026-11-17)` —— tag 未落地前对读者是假话 | 发布前先确认 `git tag -l v1.0.0` 有输出；若 tag 尚未落地，改成不依赖 tag 的表述（如「the release being cut」），或在 tag 落地后再放行 | `git tag` 无 `v1.0.0`；`src/dexatlas/__init__.py:11`=0.2.0（HEAD）；`docs/status.md:3`（HEAD）说「`v1.0.0` 未发布」；`check-version-claims.py` 报此行 |

### 6.2 `docs/outreach/publish-review.md`

| # | 行号 | 现状 | 建议改法 | 依据 |
|---|---|---|---|---|
| 2 | 63、65-67 | §3 表第 8 行的「修正后」列仍写 `in early development (\`v0.2.0\` is the newest release)` | 改成与现文件一致的表述（`The current release is \`v1.0.0\` (tagged 2026-11-17)`），或注明「本轮第二次收紧：见 §7 第 1 条」 | `docs/outreach/project-brief.md:109` 现文 |
| 3 | 67 | 「必须随发版一起改——见 **§6 第 1 条**」 | 改为「**§7 第 1 条**」 | §6 是「措辞核对」，§7 才是「发布时仍需人工确认的事项」 |
| 4 | 25 | 「M6 窄验证**二轮** 转通过 **3/6** … `docs/benchmarks/m6-level2-narrow-verify2.md`」 | 二选一：改成「窄验证**三轮** 转通过 3/6 … `docs/benchmarks/m6-level2-narrow-verify3.md`」；或保留二轮但改成「转通过 **2/6** … `docs/benchmarks/m6-level2-narrow-verify2.md`」 | `docs/benchmarks/m6-level2-narrow-verify2.md:59-61`=2/6；`docs/benchmarks/m6-level2-narrow-verify3.md:59-61`=3/6 |
| 5 | 240 | §6 表同一句「窄验证二轮转通过 3/6」 | 同第 4 项 | 同上 |
| 6 | 226 | 「Template 2 的正文原为 **3,152** 字符（超 652）」 | 改成 §5 口径下的可复算值：「原为 raw **2,966** / plain **2,951**（超门限 466）」；或直接删掉历史值只留现值 | 该数在任何基线上都复算不出；§5 脚本在 `8868e30`/`78102a8`/`fbca3d5`/`277d0fa`/`08cb34f3` 上均给出 2,966/2,951；§5 脚注 `:192-194` 已声明旧值不可复算 |
| 7 | 266 | §7 第 2 条「Template 2 模板态 plain **2,964** 字符，已超提案正文的常规上限」 | 改成「模板态 plain **2,485** / raw **2,500**，正好压线（余 0）；占位符替换后须重算」 | §5 表 `:190`；本轮独立复算一致 |
| 8 | 270 | §7 第 3 条「整篇 **6,562** 字符超过 5,000」 | 改成「整篇 raw **6,561** / plain **6,530** 超过 5,000」 | §5 表 `:187`；本轮独立复算一致 |
| 9 | 75 | 「四份素材里现在一共 **11 条**相对链接」 | 改成 **12 条**，并在表里补一行（`docs/outreach/cover-letter-templates.md` → `docs/outreach/publish-review.md` 有两处引用：`:24`、`:35`） | 本轮逐条扫描实测 12 条，全部解析成功 |
| 10 | 294 | §8 门禁表「`check-version-claims.py --base auto` **通过**（exit 0，findings 2 条均为历史遗留）」 | 改成实测值（退出码 1，7 条），或改写成「本轮基准下 2 条；随 v1.0.0 版本句变化新增 1 条」 | 本轮 `python scripts/check-version-claims.py --base auto` → exit 1，7 条 |
| 11 | 11-12 | §0 核对基准「分支 `claude/upwork-check`，基于 `origin/claude/m6-level2-verify` @ `8868e30`」 | 改成当前基线（HEAD `599ab67`），并注明 `claude/upwork-check` 只存在于 origin | `git branch -a`：本地无该分支；`git rev-list --count 8868e30..HEAD` = 23 |
| 12 | 276-277 | §7 第 5 条仍以 `8868e30` 为数字来源、仍写「共享工作树里正在跑发版完整测量」 | 提交共享树工作区里已改写的那版（1,588 / 93.3%），或改成「以最后一次完整测量为准」 | 共享树 `docs/reports/phase1-execution-report.md` 现为 1,588 / 93.3% |
| 13 | 309-315 | §8 额外发现仍写共享树覆盖率是残缺值 35.4% | 提交共享树工作区里已改写的那版（残缺问题已消失，真值 93.3%） | 共享树 `fig:coverage.pct`=93.3% |
| 14 | 26 | §0「最新已发布版本 `v0.2.0`（tag 与 `src/dexatlas/__init__.py` 一致）」 | 发版 commit + tag 落地后同步为 `v1.0.0` | `src/dexatlas/__init__.py` 工作区已改 1.0.0；tag 落地后 `git tag` 最高为 v1.0.0 |
| 15 | 247 | 「（**10 个工具说成 10**、三篇说成两篇、…）」 | 改成「**11 个工具说成 10**」 | §2 表第 5、6 行 |
| 16 | 241 | 「四份文件没有提到 M10 或**任何验收流程**」 | 收窄为「没有提到 M10 验收或本项目的验收流程」 | 素材里有客户验收条款：`docs/outreach/cover-letter-templates.md:43,61,83`；`docs/outreach/scope-ai-mcp.md:114`；`docs/outreach/scope-backend-automation.md:54` |
| 17 | 258-282 | §7 的 7 条人工确认项**未承接**终审 §7 的 5 条 | 补进 §7：(a) 官方指南链接 `support.upwork.com/hc/en-us/articles/360016144974` 未联网核实；(b) 四份素材零联系方式；(c) 零时区/可用性表述；(d) 三个 zip 是否都上传、**`docs/outreach/publish-review.md` 绝不可上传**；(e) demo 与 api-integration 两个证据包 `report.md` 字节相同 | 终审 `docs/reports/outreach-final-review.md:253-269`；本轮实测：四份素材 0 联系方式/0 时区；`demo-evidence-package.zip` 与 `api-integration-evidence-package.zip` 的 `report.md` sha256 前 16 位同为 `1594a0c19aa6c165` |

### 6.3 `docs/outreach/cover-letter-templates.md`

| # | 行号 | 现状 | 建议改法 | 依据 |
|---|---|---|---|---|
| 18 | 23-24 | 第一处指向 `docs/outreach/publish-review.md` 的引用没有注明那是内部记录 | 加一句「（internal record — not sent to the client）」，与 `:34-37` 口径一致 | 同一文件对同一目标有两处引用，只有 `:34-37` 注明了 |

### 6.4 目录级 / 被指向文档

| # | 位置 | 现状 | 建议改法 | 依据 |
|---|---|---|---|---|
| 19 | `docs/outreach/`（目录） | 5 个文件同目录，其中 `docs/outreach/publish-review.md` 顶部写明「不对外、不作附件」，但仍与四件对外素材同处一地 | 打包时**逐个选**四件素材；或把 `docs/outreach/publish-review.md` 移到 `docs/outreach/` 之外（例如 `docs/reports/`），让「这个目录里的东西都能外发」成立 | 终审 M5 给了两个动作，主线程选了「加标注」；标注挡不住整目录打包 |
| 20 | `docs/case-studies/README.md:7,29,50`；`api-integration.md:16,21`；`docs/case-studies/demo-app-walkthrough.md:22`；`docs/case-studies/obfuscated-app.md:32` | 被素材直接指向的三篇 case study 里反复用 "customer" 作人设口吻，且 case study 1 与 3 用同一个 APK、两个证据包的报告字节相同 | 人工确认是否要在素材里点明「三篇走查 = 三个视角、两个样本；demo 与 api-integration 共享同一份分析报告」，或把 case study 里的 "customer" 改成 "reader"/"integrator" 一类不会读成真客户的词 | `docs/outreach/project-brief.md:115`、`docs/outreach/cover-letter-templates.md:28` 把读者引向该目录；两个包 `report.md`/`report.html` sha256 相同 |

---

## 7. 本轮做了什么 / 没做什么

**做了**：

- 逐条复核 5 处必改项（§1），5 处的结论、依据都在表里
- 用 `docs/outreach/publish-review.md` §5 **自带**的口径与脚本独立复算字符表，**14/14 行一致**（§2）
- 只读复跑了两个只读门禁脚本：`check-doc-citations.py`（220/0/0，与 §8 记录一致）、
  `check-version-claims.py`（exit 1 / 7 条，与 §8 记录不一致）
- 逐条核对了 `docs/outreach/publish-review.md` 里指向具体文件/行的旧结论（§5，14 处）
- 核对了其余数字与其落盘来源（§3），并更正了任务说明里「覆盖率 93.2% 不变」的前提
- 只读检查了共享树 `E:\Dexatlas` 的未提交改动，区分了「已提交树」与「工作区」两种口径

**没做（受硬约束或任务范围限制）**：

- 未跑 pytest / coverage / `uv sync` / `scripts/refresh-report-figures.py`；§8 里的
  `tests/test_docs.py` 一行**未复跑**，无法独立确认「60/60 通过，0 跳过」
- 未修改 `docs/outreach/` 下任何文件，未修改任何其它文件（除新增本报告）
- 未 commit、未 push、未打 tag、未发布、未登录任何平台、未调用任何外部 API、
  未向任何外部服务发送数据
- 未核对 `origin/main`（1515 / 93.2%，与素材不一致）作为发布基准的取舍——那是主线程的判断

---

*本窗口未发布任何内容，也未向任何外部服务发送数据。*
