# Upwork 素材发版前终审（只读复核）

> **本窗口未发布任何内容，也未向任何外部服务发送数据。**
> 没有调用 Upwork 或任何其它平台的 API，没有登录账号，没有复制到剪贴板，没有发送邮件或
> 消息，没有提交任何投稿草稿，没有创建 tag，也没有向 `main` / `claude/m6-level2-verify`
> 推送任何东西。
> 没有运行 `pytest` / `pytest --cov` / `coverage` / `uv sync`，没有写入任何测量产物；
> 核对只用了 `git show` / `git ls-tree` / `Read` / `Grep`，以及一个放在**仓库外**临时目录
> 里的纯标准库字符数脚本。本轮唯一的写入是本文件。

---

## 0. 核对基准与口径

| 项 | 取值 | 说明 |
|---|---|---|
| 审查对象 | `docs/outreach/` 下 4 件对外素材 + 1 份核对记录 `publish-review.md` | 就在本分支工作树里，取自主线 `claude/m6-level2-verify` @ `78102a8`（该提交已合并上一轮校对 `08cb34f`） |
| 本窗口 worktree | `E:\Dexatlas\.claude\worktrees\outreach-final-review-01a419`，分支 `audit/outreach-final-review`，基线 `origin/claude/m6-level2-verify` @ `78102a8` | 素材本体、核对记录、M6 基准报告、`docs/releases/v1.0.0.md` 全部在工作树内；本分支只比基线多一个提交（本文） |
| 报告数字基准 | `docs/reports/phase1-execution-report.md`（基线提交落盘版） | 落盘值：**测试 1584**（1437 快 + 147 集成）、**一方代码覆盖率 93.2%**（7109/7631 行） |
| 共享树工作副本 | **不作为基准** | `E:\Dexatlas\docs\reports\phase1-execution-report.md` 的未提交改动把覆盖率写成 **35.4%（2699/7631）**，测试数仍是 1584；这是并发 `pytest --cov` 互相清 `.coverage` 后的残缺值，不是真值。本报告一律不引用工作树版本 |
| 行号基准 | 本文所有 `素材:行` 指向本分支工作树内的 `docs/outreach/<文件>` | 与基线提交逐字一致（已用 `diff` 比对，四件素材与校对后版本字节相同） |
| 外部信息 | **未联网** | 官方指南链接的可达性与 Upwork 真实字段上限未经联网核实；本轮按任务给定门限（标题 ≤60、简介 ≤5,000）判定，提案正文另按 2,500 的保守口径复核 |

两条线索（`origin/main` 与主线）的落盘数字本身就不一样：`origin/main`（`fbca3d5`）的报告是
1515（1368 快 + 147 集成）/ 93.2%（6938/7445），主线（`78102a8`，比 `fbca3d5` 多 60 个提交）
是 1584（1437 + 147）/ 93.2%（7109/7631）。**素材与主线一致、与 `origin/main` 不一致**，
所以发布必须以主线合并后的树为准（见 §6 M1）。

> 审计轨迹：本轮最初把分支切在 `origin/main`（`fbca3d5`）上，那棵树**不含**校对提交
> `08cb34f`，素材与核对记录都不在里面；第一版复核因此全部经 `git show 78102a8:…` 只读取用，
> 结论逐条可复算。收到基线纠正后，分支已重切到 `origin/claude/m6-level2-verify` @ `78102a8`
> 并把本文移到其上，所有结论已在工作树内重新核对一遍，**数值无变化**。

补充观察（复核期间的仓库动态）：共享树的本地 `claude/m6-level2-verify` 已前进到 `7910195`
（「测量隔离：覆盖率数据文件按次私有 + 同 checkout 互斥锁 + 红→绿回归」），远端仍停在
`78102a8`。该提交只改 `scripts/refresh-report-figures.py` 与新增
`tests/test_refresh_coverage_hygiene.py`，**没有动** `docs/reports/phase1-execution-report.md`、
`docs/outreach/`、`docs/status.md`、`README.md`，所以本文所有落盘数字仍成立；但它新增了一个
测试文件，意味着下一次完整测量写回的测试数与覆盖率**一定**会变——这正是 §6 M1 说的那件事。

---

## 1. 数字与表述逐行核对

| 素材文件:行 | 原文数字/表述 | 仓库出处 | 判定 |
|---|---|---|---|
| `cover-letter-templates.md:68` | `1,584 automated tests at 93.2% coverage` | `docs/reports/phase1-execution-report.md:76-77`（`tests.total`=1584、`coverage.pct`=93.2%）；同 `docs/status.md:23-24`、`README.md:12-13` | 一致（但见 §6 M1） |
| `project-brief.md:50` | `1,584 automated tests, 93.2% coverage` | 同上 | 一致（但见 §6 M1） |
| `project-brief.md:85` | `1,584 tests` | 同上 | 一致（但见 §6 M1） |
| `scope-backend-automation.md:24` | `1,584 tests at 93.2% coverage` | 同上 | 一致（但见 §6 M1） |
| `cover-letter-templates.md:132` | `eleven tools over stdio` | `src/dexatlas/mcp/server.py` 注册 11 个 `@server.tool`：list_projects / get_project_status / get_manifest / search_symbols / get_class_source / get_method_source / find_callers / find_callees / get_evidence / resolve_locator / find_resource_declarations | 一致 |
| `project-brief.md:71` | `Eleven tools over stdio` | 同上 | 一致 |
| `scope-ai-mcp.md:28` | `eleven tools over stdio` | 同上 | 一致 |
| `project-brief.md:52-53` | `three complete case studies on first-party sample APKs` | `docs/case-studies/README.md`「Three complete walkthroughs」；三篇正文 `demo-app-walkthrough.md` / `obfuscated-app.md` / `api-integration.md` | 一致（措辞提示见 §5.2） |
| `project-brief.md:109` | `` `v0.2.0` is the newest release `` | `git tag`：v0.1.0 / v0.1.1 / v0.1.2 / v0.1.3 / **v0.2.0**，v0.2.0 是最新；v1.0.0 尚未打 tag | 一致（**v1.0.0 发版后即成假话**，见 §6 M2） |
| `project-brief.md:69`、`scope-backend-automation.md:25` | `CI across Python 3.12/3.13` | `.github/workflows/ci.yml:96` → `python-version: ["3.12", "3.13"]` | 一致 |
| `project-brief.md:114` | `https://github.com/gg320324492-lgtm/dexatlas` | `README.md:9-15` 徽章同域；`git remote -v` 同 | 一致 |
| `scope-ai-mcp.md:14-15` | `What I offer`（`773 characters as written`） | 本轮实测 raw 781 / plain **773** | 一致（见 §3） |
| `cover-letter-templates.md:39`、`:92` | 两行 `**Subject: {{job title}} — …**` | 模板占位符，不是字段值 | 需人工确认（替换后长度） |
| `cover-letter-templates.md` 全文 | `{{...}}` 占位符 12 处 | 只在封面信模板里；另三份是可直接粘贴的成稿 | 需人工确认（逐个替换，见 §7） |
| 四份素材均**未出现** | M6 层级 2 的 40.0% / 81.7%、逐轮 17-15-17 与 15-16-18、tokens、26 REST + 6 MCP + 14 CLI、退出码 6 | 仓库落盘：`docs/benchmarks/m6-level2-retest3.md`、`docs/benchmarks/m6-level2-retest4.md`、`docs/releases/v1.0.0.md:57,62` | 一致（不提即不宣称；M6 未达验收线，不引用是对的） |
| `publish-review.md:20` | `49/60 = 81.7%（逐轮 15/16/18）` → `docs/benchmarks/m6-level2-retest4.md` | retest4 §逐轮结果总览：r1 15/20、r2 16/20、r3 18/20 | 一致（归属正确，见 §2） |
| `publish-review.md:21` | 窄验证二轮 `转通过 3/6（门槛 ≥4）` → `m6-level2-narrow-verify2.md` | 该文件 §逐轮结论 | 一致 |
| `publish-review.md:22` | 最新已发布版本 `v0.2.0` | `git tag` 同 §1 | 一致 |

---

## 2. retest3 / retest4 归属核对（两次重测合计相同、逐轮不同）

| 文档 | r1 | r2 | r3 | 三轮合计 | 落盘出处 |
|---|---|---|---|---|---|
| `docs/benchmarks/m6-level2-retest3.md` | 17/20 | 15/20 | 17/20 | **49/60 = 81.7%** | 该文件 §逐轮结果总览（token 367581 / 356309 / 356226） |
| `docs/benchmarks/m6-level2-retest4.md` | 15/20 | 16/20 | 18/20 | **49/60 = 81.7%** | 该文件 §逐轮结果总览（token 395740 / 395542 / 391074） |

- `publish-review.md:20` 把 **15/16/18** 挂在 `m6-level2-retest4.md` 上 —— **挂对了**，
  与 retest4 的逐轮表一致。
- 两份文档合计都是 49/60 = 81.7%，若只看合计无法区分；**逐轮数必须随文档一起引用**。
- 四份对外素材里没有任何一处引用 M6 数字，也没有逐轮数，因此素材侧不存在 retest3/retest4
  混淆的风险。

---

## 3. 字段字符数实测

**口径（本轮重新定义并落盘在 §8）**：raw = 该 `## ` 小节正文的 Markdown 源码字符数
（不含小节标题行，首尾空行不计）；plain = 去掉 Markdown 语法（`**粗体**`、`` `代码` ``、
列表符号、`>` 引用、链接语法只留链接文字）后的字符数，即粘进表单框的内容。判定取两者
**较大者**，口径保守。

| 字段（引小节标题行） | 文件:行 | raw | plain | 门限 | 判定 | 余量（按较大者） |
|---|---|---:|---:|---:|---|---:|
| Project title | `project-brief.md:17` | **53** | 53 | 60 | ✅ | **7** |
| Role | `project-brief.md:21` | 438 | 438 | 5,000 | ✅ | 4,562 |
| Short description | `project-brief.md:30` | 1,410 | 1,396 | 5,000 | ✅ | 3,590 |
| Skills | `project-brief.md:55` | 311 | 271 | 5,000 | ✅ | 4,689 |
| Deliverables shown in the repository | `project-brief.md:63` | 1,455 | 1,407 | 5,000 | ✅ | 3,545 |
| Third-party components (attribution) | `project-brief.md:89` | 458 | 440 | 5,000 | ✅ | 4,542 |
| Honest limitations | `project-brief.md:102` | 443 | 433 | 5,000 | ✅ | 4,557 |
| Links | `project-brief.md:112` | 707 | 478 | 5,000 | ✅ | 4,293 |
| §What I offer（粘贴段，标题 :19，正文 21-32） | `scope-ai-mcp.md:19` | 781 | **773** | 5,000 | ✅ | **4,227** |
| §What I offer（粘贴段，标题 :15，正文 17-25） | `scope-backend-automation.md:15` | 592 | 588 | 5,000 | ✅ | 4,408 |
| 全文（附件） | `scope-backend-automation.md` | 4,951 | 4,837 | 5,000 | ✅（贴附件不占字段） | 49 |
| 全文（附件） | `scope-ai-mcp.md` | **6,562** | **6,418** | 5,000 | ❌ **超 1,562**（若整篇粘贴） | — |
| Template 1 正文（标题 :37，正文 39-86） | `cover-letter-templates.md:37` | 2,190 | 2,155 | 2,500（提案正文常规值） | ✅ | **345** |
| Template 2 正文（标题 :90，正文 92-151） | `cover-letter-templates.md:90` | 3,152 | **3,111** | 2,500（提案正文常规值） | ❌ **超 611** | — |

说明：

1. **唯一超出 5,000 的是 `scope-ai-mcp.md` 整篇（6,562）**。该文件头部
   `scope-ai-mcp.md:13-15` 已写明处理路径：作为附件上传，若目标是简介框就只贴
   §What I offer（773 字符）。按这条路径走即不超限；若决定整篇粘贴，则必须再压约
   1,500 字符（删排除条款 / 验收条款 / 模型预算边界属于编辑判断，本轮不替人做）。
2. **Template 2 在模板态超过提案正文的 2,500 常规上限 611 字符**。删掉 12 处
   `{{...}}` 占位符后会回落，但回落多少取决于占位符替换后的实际文本，必须人工重算。
   （Template 1 只剩 345 字符余量，替换占位符时同样容易顶出去。）
3. **门限来源**：标题 ≤60、简介 ≤5,000 是任务给定口径；2,500 是提案正文的保守常规值，
   **两者都未联网核实**，Upwork 会调整字段限制，发布前须在真实表单上逐字段复核。
4. **与上一轮核对记录的差异**：`publish-review.md:120-135` 的字符表有 3 个数字在当前
   文件上**不可复算**（详见 §6 M4）；其余 22 个数字与本轮实测逐字一致。

---

## 4. 发布约束表述与外发风险

### 4.1 个人项目身份（✅ 守住）

四份素材都带 Identity note：`cover-letter-templates.md:12-16`、
`project-brief.md:10-13`、`scope-ai-mcp.md:9-11`、`scope-backend-automation.md:9-11`，
统一口径是「个人 / 自筹开源项目，没有客户、没有客户结果、不声称收益或工时节省」。
正文里没有任何虚构客户、虚构结果或虚构数字；`scope-ai-mcp.md:86-95`
（§Model costs and budget boundaries，`:88`「You own the model account and the API keys」）
讲的是**客户自备模型账号、费用直付、不加价、每次调用写进交接记录**，属通用商务条款。

### 4.2 联系方式（⚠️ 素材里一个都没有）

对四份素材做正则扫描，`@域名` 形式的邮箱、`mailto:`、GitHub 个人主页、报价、
时区、可用时间、响应时限**全部零命中**。素材是模板 + 成稿，联系方式与可用性要靠人补
（见 §7）。

### 4.3 时区 / 可用性（⚠️ 同上，尚未落笔）

四份素材没有任何时区、工作日/周末、每日可投入时间的表述。这不是错误，是**尚未写**；
按 Upwork 的个人资料要求，这类信息通常要在个人资料和首封回信里出现，素材里没有，
需要人工决定补在哪里。

### 4.4 示例附件引用（✅ 存在，见 §5）

### 4.5 不应外发的内容扫描（✅ 素材侧干净）

对四份素材的扫描结果：

| 类别 | 结果 |
|---|---|
| 中文字符 | 0（四份素材全是英文，未混入内部中文笔记） |
| API key / secret 样式字符串 | 0（`sk-`、长 base64、`AKIA`、`eyJ`、`Bearer `、`password=`/`api_key=` 均无命中） |
| 内部路径 | 0（无 `E:\`、`G:\`、`.scratch`、worktree 路径） |
| 分支名 / commit / 内部流程词 | 0（无 M6、层级 2、retest、预算、tokens、共享树、HANDOVER） |
| 模型 / 工具厂商名 | 0（无 Claude / Anthropic / ChatGPT 等；DexAtlas 的三个引擎 JADX / Apktool / Androguard 已在 §Third-party components 里按第三方归属正确署名） |
| 他人姓名 | 0（只有 `{{your name}}`、`{{client name}}` 等占位符） |

**但是：`docs/outreach/publish-review.md` 是内部核对记录，绝不可作为附件上传。**
它含有本地路径 `E:\worktrees\upwork-check`（第 8 行、第 224 行）、分支名
`claude/upwork-check`、commit `8868e30`，以及 M6 层级 2 的评测细节。而
`cover-letter-templates.md:31-33` 明确把读者引向它（「Field lengths are accounted for
in publish-review.md」）。素材与内部记录同处一个目录，外发时按目录整体打包就会带出去
（见 §6 M5）。

**另外**：四份素材首尾都印着 `Draft for review — not published.`
（`cover-letter-templates.md:3`、`:155-157`；`project-brief.md:3`、`:126-127`；
`scope-ai-mcp.md:3`、`:132-133`；`scope-backend-automation.md:3`、`:104-105`），
以及头部的 Identity note 引用块。发布前必须决定删哪些（见 §7）。

---

## 5. 证据包与链接核对

### 5.1 相对链接逐条核对（全部存在）

| 引用位置 | 链接目标 | 存在 |
|---|---|---|
| `project-brief.md:115` | `../case-studies/README.md` | ✅ |
| `project-brief.md:120` | `../case-studies/attachments/demo-evidence-package.zip` | ✅ |
| `project-brief.md:121` | `../case-studies/attachments/obfuscated-evidence-package.zip` | ✅ |
| `project-brief.md:122` | `../case-studies/attachments/api-integration-evidence-package.zip` | ✅ |
| `cover-letter-templates.md:28` | `../case-studies/attachments/demo-evidence-package.zip` | ✅ |
| `cover-letter-templates.md:29` | `../case-studies/attachments/obfuscated-evidence-package.zip` | ✅ |
| `cover-letter-templates.md:30` | `../case-studies/attachments/api-integration-evidence-package.zip` | ✅ |
| `cover-letter-templates.md:6` | `scope-backend-automation.md` | ✅ |
| `cover-letter-templates.md:7` | `scope-ai-mcp.md` | ✅ |
| `cover-letter-templates.md:8` | `project-brief.md` | ✅ |
| `cover-letter-templates.md:32` | `publish-review.md` | ✅（但**不可外发**，见 §6 M5） |

`docs/case-studies/attachments/` 下共 9 个文件（3 个 zip + 3×report.md/.json/.html 中
demo、obfuscated 两组共 6 个），与三篇 case study 的引用一致，无多余无缺失。

### 5.2 证据包内容核对（本轮新解压核对）

| zip | 仓库大小 | 内含 | 素材里的描述 |
|---|---:|---|---|
| `demo-evidence-package.zip` | 6,880 B | `reports/report.html` 8,549 B / `reports/report.json` 11,381 B / `reports/report.md` 5,171 B / `manifest.json` 1,167 B | 「a zip holding the report and a manifest of hashes」✅ |
| `obfuscated-evidence-package.zip` | 6,214 B | 同结构（report 三件套 + `manifest.json` 1,166 B） | ✅ |
| `api-integration-evidence-package.zip` | 6,880 B | 同结构 | ✅ |

`manifest.json` 里 `files[]` 每项带 `sha256` + `bytes` + `role`，`not_included` 明确写了
「APK 本体不打包，凭 SHA-256 识别」——素材的描述与内容一致，三个包都不是空壳。

**新发现（需人工确认，不算素材说错）**：`api-integration-evidence-package.zip` 与
`demo-evidence-package.zip` 的 **`reports/report.md` 字节完全相同**，`manifest.json` 的
`apk_sha256` 也相同（`80a8fe0e…9ff9`），因为 **case study 3 复用同一个
`examples/demo-app/demo.apk`**（`docs/case-studies/api-integration.md:3-4` 自己写明了
Sample 就是 demo.apk）。两个包只有 `project_id` / `run_id` / 时间戳 / `report.json` 不同。
素材说的「three complete case studies on first-party sample APKs」与「one per case
study」**都不算假话**，但读者可能理解成三个不同样例；三个包并排上传时尤其明显。
建议人工决定是否在素材里点明「第三篇是同一 demo APK 的 API 视角」。

### 5.3 官方指南链接

四份素材各引用一次同一个链接（`cover-letter-templates.md:10`、`project-brief.md:5`、
`scope-ai-mcp.md:7`、`scope-backend-automation.md:7`）：
`https://support.upwork.com/hc/en-us/articles/360016144974-How-to-enhance-your-freelancer-profile`。
四份写法完全一致，无拼写漂移。**本轮未联网**，因此链接是否仍可达、其描述的字段限制是否
与 §3 的门限一致，**没有核实**（见 §7 人工确认项）。

---

## 6. 必须改的 N 处

**N = 5**。定义：在**发布动作发生之前**必须动一下，否则要么对外发布的数字/版本将与仓库
矛盾，要么核对记录里的数字无法复算，要么会把内部文件发出去。本窗口**只列不改**。

| # | 严重度 | 位置 | 问题 | 建议动作（由主线程执行） |
|---|---|---|---|---|
| **M1** | **高** | `cover-letter-templates.md:68`、`project-brief.md:50`、`project-brief.md:85`、`scope-backend-automation.md:24`（4 处） | `1,584` / `93.2%` **当前**与主线落盘报告一致，但主线正在跑 v1.0.0 发版完整测量，`<!--fig:tests.total-->` / `<!--fig:coverage.pct-->` 会被重写；同一批素材已经因测量刷新过期过两次（`~1,540` → `1,584`） | 测量落盘后按新值重核这 4 处；同时确认以主线合并树为准（`origin/main` 是 1515 / 93.2%（6938/7445），与素材不一致） |
| **M2** | **高** | `project-brief.md:109` | `` `v0.2.0` is the newest release `` 在 v1.0.0 打 tag 后**必然**变成假话；`scripts/check-version-claims.py` 会直接报出来 | 随发版 commit 一起改这句（上一轮核对记录 §6 第 1 条已预告，仍未关闭） |
| **M3** | 中 | `cover-letter-templates.md:90-151`（Template 2 正文） | 模板态 plain **3,111** 字符，超提案正文 2,500 常规上限 611；Template 1（`:37-86`）也只剩 345 余量 | 删减到限内，或在用法说明里写明「分两次发送 / 只发节选」；替换 12 处占位符后重算 |
| **M4** | 中 | `publish-review.md:120-135`（字符数表 3 个格子） | 表中 `Template 1 正文 2,216/2,179`、`Template 2 正文 3,005/2,964`、`scope-backend §What I offer raw 621` 在当前文件上**不可复算**；本轮实测为 `2,190/2,155`、`3,152/3,111`、`592/588`。我把该文件在仓库里的**全部历史版本**（`e59929d` 初稿、`ed9b600` 修正）加上校对提交
   `08cb34f` 与主线 `78102a8`、以及 `fbca3d5` / `277d0fa` / `8868e30` 三个引用点全部量了一遍，
   没有任何一个版本能产生 2,216 或 3,005。其余 22 个数字逐字可复算 | 用 §8 的口径重出这张表（或订正这 3 个格子）。素材本身不受影响——余量结论两种口径都成立——但核对记录里的数字不能是复算不出来的（CLAUDE.md 第 2 条） |
| **M5** | 中 | `publish-review.md`（整份）＋ `cover-letter-templates.md:31-33` | 内部核对记录含本地路径 `E:\worktrees\upwork-check`（第 8、224 行）、分支名、commit `8868e30`、M6 评测细节；素材又把它指给读者 | 在该文件顶部加一行「内部核对记录，不对外、不作附件」；或把它移出 `docs/outreach/`，让「这个目录里的东西都能外发」成立 |

> 未列入「必须改」但值得知道的一项：`scope-ai-mcp.md` 整篇 6,562 字符超 5,000——该文件
> 头部已写明处理路径（只贴 §What I offer），按此路径不构成缺陷，因此归入 §7 人工确认项。

---

## 7. 发布前人工确认清单

1. **测量落地后重核数字**：v1.0.0 发版完整测量写回 `docs/reports/phase1-execution-report.md`
   后，按新值重核 §6 M1 的 4 处；并确认发布基准是主线合并树。
2. **版本句**：`v0.2.0` 那句随发版一起改（§6 M2）。
3. **字段长度在真实表单复核**：标题 ≤60、简介 ≤5,000、提案正文 2,500 这三个门限本轮
   **未经联网核实**；Upwork 会调整限制，逐字段在真实表单上确认，并量一次实际输入长度。
4. **官方指南链接**：四份素材引用的 `support.upwork.com/hc/en-us/articles/360016144974`
   本轮未联网，打开确认仍可达、字段描述未变。
5. **联系方式**：四份素材**没有任何**联系方式。用哪个（个人邮箱 / GitHub 个人主页 /
   Upwork 资料），由谁提供，写在哪里。
6. **时区与可用性**：素材里没有时区/可用时间表述；是否补、补在哪（首封回信 / 个人资料）。
7. **个人项目身份声明是否保留**：`project-brief.md:10-13` 的 Identity note 与四份素材首尾的
   `Draft for review — not published.` 标记，发布时删哪些、留哪些。
8. **附件是否真的上传**：三个 zip（`demo-` / `obfuscated-` / `api-integration-`）是否都作为
   附件上传；`publish-review.md` **不得**上传；两个 zip 是否有大小/格式限制。
9. **占位符全部替换**：封面信 12 处 `{{...}}`，漏改会直接发出去；替换后重算正文长度（M3）。
10. **`scope-ai-mcp.md` 的用法**：整篇做附件，还是只贴 §What I offer（773 字符）。整篇粘贴
    则需再压约 1,500 字符。
11. **是否引用 M6 数字**：M6 层级 2 实测 49/60 = 81.7%，**未达 ≥54/60（≥90%）**的验收线。
    当前四份素材完全不引用（正确）。若要提，只能引用 `docs/benchmarks/m6-level2-retest4.md`
    的原值，且必须同时说明「未达验收线」。
12. **case study 3 与 demo 同源**：两个证据包的 `report.md` 字节相同、APK 相同；是否在素材里
    点明（§5.2）。

---

## 8. 复算方法

本轮全部数字可按下述方法重算：

```bash
# 素材正文（校对后的版本，本分支工作树即该版本）
cat docs/outreach/cover-letter-templates.md
cat docs/outreach/project-brief.md
cat docs/outreach/scope-ai-mcp.md
cat docs/outreach/scope-backend-automation.md

# 报告落盘数字（不要用共享树 E:\Dexatlas 的工作副本，那份覆盖率是 35.4% 的残缺值）
git show 78102a8:docs/reports/phase1-execution-report.md | grep -n "fig:tests\.\|fig:coverage\."

# MCP 工具数
grep -c "@server.tool" src/dexatlas/mcp/server.py

# 证据包内容
unzip -l docs/case-studies/attachments/demo-evidence-package.zip
```

字符数脚本口径（纯标准库，跑在仓库外的临时目录，不写任何测量产物）：

- 切分：按 `^## ` 标题把小节切开；小节正文 = 标题行之后到下一个标题行之前的行，
  首尾空行不计。
- raw：`len(小节正文)`，即 Markdown 源码字符数。
- plain：逐行去掉 `` `代码` `` → 内容、`**粗体**`/`*斜体*` → 内容、列表符号
  （`- ` / `1. `）→ 缩进、`> ` 引用符 → 空、Markdown 链接语法（方括号包文字、圆括号包地址）
  → 只保留文字、`#` 标题符 → 空，
  行尾空白去掉，再去掉首尾空行后取 `len`。
- 判定取 raw 与 plain 的较大者。
- 本轮该脚本测得的整文件值（raw / plain）：`cover-letter-templates.md` 7,264 / 6,855；
  `project-brief.md` 6,233 / 5,814；`scope-ai-mcp.md` 6,562 / 6,418；
  `scope-backend-automation.md` 4,951 / 4,837。

---

## 9. 结论

- 四份素材的**对外数字与主线当前落盘的报告数字一致**（1584 / 93.2% / eleven tools /
  three case studies / v0.2.0），M6 与契约类数字**没有被引用**，retest3 / retest4 的逐轮数
  归属正确，没有混淆。
- **字段长度**：项目标题 53（门限 60，余量 7）；简介 1,410（门限 5,000，余量 3,590）；
  scope-ai-mcp 的 §What I offer 773（余量 4,227）；超限项两处——`scope-ai-mcp.md` 整篇
  6,562（超 5,000，已有处理路径）、封面信 Template 2 正文 3,111（超提案正文 2,500 常规值 611）。
- **必须改 5 处**（§6），最严重的是 **M1：`1,584` / `93.2%` 四处对外数字会与主线正在跑的
  发版完整测量脱节**——这批素材已经因为同样的原因过期过两次。
- **发布前人工确认 12 项**（§7）。
- 本窗口**未发布任何内容，未向任何外部服务发送数据**，未改动除本文件外的任何文件。
