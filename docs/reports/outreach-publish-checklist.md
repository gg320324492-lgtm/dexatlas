# Upwork 素材发布前最后点检清单（outreach publish checklist）

> **这不是发布动作。** 本轮没有向 Upwork 或任何其它平台提交、发布、复制或发送
> 任何内容；没有登录任何账号；没有调用任何模型 API；没有打 tag；没有联网。
> 四件对外素材仍然是草稿，状态是「Draft for review — not published」。
>
> **本文件是内部清单，不是附件。** 它放在 `docs/reports/` 下，**不随提案发送**，
> 也不进任何证据包。对外发出去的只有 `docs/outreach/` 下的四件素材本身。
>
> 编写日期：2026年11月17日。编写基准：分支 `claude/outreach-final-checklist-0eabb0`，
> commit `a4e7af5`（worktree `stale-number-scan-213305`）。
> 对象：[cover-letter-templates.md](../outreach/cover-letter-templates.md)、
> [project-brief.md](../outreach/project-brief.md)、
> [scope-ai-mcp.md](../outreach/scope-ai-mcp.md)、
> [scope-backend-automation.md](../outreach/scope-backend-automation.md)，
> 以及内部核对记录 [publish-review.md](../outreach/publish-review.md)。
>
> 字段长度的口径与脚本一律取自 `publish-review.md` §5，**本清单不另立一套**。
> 清单里的每个数字都来自它指向的落盘文件；仓库之外的数字一个也没有。

---

## 0. 怎么用这份清单

- 每一条 `- [ ]` 是「发布那一刻」的一项检查，格式固定为：**查什么 → 怎么查 →
  查过是什么样**。第三段是 2026年11月17日本分支上的实测结果，作为基线。
- 发布当天把「怎么查」里的命令重跑一遍。数字与基线不同，就以新的落盘处为准，
  并回头改文案；不要凭记忆改。
- 数值型结论一律**从落盘处抄**，不手抄、不凭印象。报告里的数字由
  `scripts/refresh-report-figures.py` 生成，**禁止手改** `<!--fig:...-->` 标记。

---

## 1. 数字一致性

### 1.1 素材里写着的数字（逐个 → 去哪核 → 查过是什么样）

| # | 数字 | 出现在 | 去哪核（落盘处） | 查过是什么样 |
|---|---|---|---|---|
| 1 | **1,588** 个测试（1,441 快 + 147 集成） | `cover-letter-templates.md:79`；`project-brief.md:50`、`:85`；`scope-backend-automation.md:24` | [phase1-execution-report.md](phase1-execution-report.md) 的 `<!--fig:tests.total-->` / `<!--fig:tests.fast-->` / `<!--fig:tests.slow-->`；同值另见 [status.md](../status.md) | `1588（1441 + 147）` ✅ 一致 |
| 2 | **93.3%** 一方代码覆盖率（7,117 / 7,631 行） | 同上三处 | `phase1-execution-report.md` 的 `<!--fig:coverage.pct-->` / `<!--fig:coverage.covered-->` / `<!--fig:coverage.total-->`；`status.md` | `93.3%（7117/7631）` ✅ 一致 |
| 3 | **eleven**（11）个 MCP 只读工具 | `cover-letter-templates.md:135`；`scope-ai-mcp.md:28` | [server.py](../../src/dexatlas/mcp/server.py) 里注册的 11 个 `Tool`；[public-contracts.md](../architecture/public-contracts.md) §1.3 的第 1–11 行；[README.md](../../README.md) 写 “eleven tools” | `11` ✅ 一致 |
| 4 | 三个走查 / 三个一方样本 / **四个包、四次分析** | `cover-letter-templates.md:36-45`；`project-brief.md:127-135` | [case-studies/README.md](../case-studies/README.md) 表格下方那段说明 | 三篇走查覆盖 `demo-app` / `obfuscated-app` / `multidex-app`，四个证据包对应四次分析（run id 两两不同） ✅ 一致（详见 §1.3） |
| 5 | 四个证据包（四个 zip） | `cover-letter-templates.md:32-35`；`project-brief.md:123-126` | [attachments/](../case-studies/attachments/) 下的四个 `.zip`，均已被 git 跟踪 | 四个 zip 都在 ✅ |
| 6 | `v1.0.0`（tagged 2026-11-17） | `project-brief.md:109` | `git for-each-ref refs/tags`；[__init__.py](../../src/dexatlas/__init__.py) 的 `__version__` | tag `v1.0.0`（2026-11-17）、`__version__ = "1.0.0"` ✅ 一致 |
| 7 | 三个分析引擎 / 两套 Python 版本（3.12 / 3.13） | `cover-letter-templates.md:78`、`:80`；`project-brief.md:51`；`scope-backend-automation.md:23-25` | `src/dexatlas/tools/` 下的三个后端；`.github/workflows/` 的 CI 矩阵 | Apktool / JADX / Androguard 三个引擎，CI 覆盖 3.12 与 3.13 ✅ |
| 8 | “773 characters as written” | `scope-ai-mcp.md:14` | 按 `publish-review.md` §5 脚本复算 `scope-ai-mcp.md` 的 §What I offer | plain **773** ✅ 一致（raw 781） |

**逐条自查：**

- [ ] **1,588 / 1,441 / 147 仍与落盘一致。**
  怎么查：`grep -n "fig:tests\." docs/reports/phase1-execution-report.md`
  查过是什么样：三个标记分别落盘为 `1588`、`1441`、`147`；素材里写的是 `1,588`。
- [ ] **93.3%（7,117 / 7,631）仍与落盘一致，且口径仍是「一方代码覆盖率」。**
  怎么查：`grep -n "fig:coverage\.\(pct\|covered\|total\)" docs/reports/phase1-execution-report.md`
  查过是什么样：`93.3%`、`7117`、`7631`。**不要写成「总覆盖率」**——那会把没测到的第三方代码算进分母。
- [ ] **MCP 工具数仍是 11，措辞仍是 “eleven tools over stdio”。**
  怎么查：`grep -cE "^\s+name=\"" src/dexatlas/mcp/server.py`（结果减 1 个服务器名 `dexatlas` = 工具数）
  查过是什么样：`12 - 1 = 11`。
  ⚠️ **别从 [v1.0.0-release-checklist.md](v1.0.0-release-checklist.md) 抄工具数**：那份写在
  第 11 个工具 `find_resource_declarations` 加入之前，行 63 写的是「10 个只读工具」——
  当时正确，现在是旧的。素材里的 11 才是当前值。
- [ ] **版本句 `v1.0.0 (tagged 2026-11-17)` 仍然成立。**
  怎么查：`git for-each-ref refs/tags/v1.0.0 --format='%(refname:short) %(creatordate:short)'`
  查过是什么样：`v1.0.0 2026-11-17`。**再发一个 tag，这句就过期了**，
  `scripts/check-version-claims.py` 会报出来；届时回 `project-brief.md` 改这一句。
- [ ] **「三个样本 / 四个包 / 四次分析」的口径没被改回去。**
  怎么查：`grep -n "only two analyses\|只有两份分析\|three first-party samples\|four separate analyses\|四个证据包" docs/outreach/*.md`
  查过是什么样：`cover-letter-templates.md:36` 与 `project-brief.md:127` 各有一处说明
  「四个证据包对应四次分析」，紧跟着说明「demo 与 api-integration 两个包是同一份样本的
  两次分析」。**旧的「only two analyses / 只有两份分析」一句已经删掉**——附件集换过
  一轮之后它不再成立；grep 命中的是新口径。

### 1.2 素材里**没有**写、但发布时可能被临时加上的数字

以下五个数**当前不在四件素材里**（本轮逐文件 grep 过：`13` 只出现在 `Python 3.12/3.13`、
`23` / `49` / 退出码 / 5 个 APK 都没有）。发布时若想在作品集或提案里补一句，
必须先按下面这一列核，**不能凭印象写**。

| 数字 | 去哪核（落盘处） | 怎么查 | 查过是什么样 |
|---|---|---|---|
| CLI **13** 个子命令 | `src/dexatlas/cli/main.py`；`phase1-execution-report.md` 的 `<!--fig:cli.commands-->` | `grep -c "@app.command()" src/dexatlas/cli/main.py` | `13` |
| REST **23** 个端点 | `src/dexatlas/api/app.py`；`<!--fig:api.endpoints-->` | `grep -oE "@app\.(get\|post\|delete\|put)\(" src/dexatlas/api/app.py \| wc -l` | `23` |
| 契约活检 **49** 项（28 REST + 6 MCP + 15 CLI） | [public-contracts.md](../architecture/public-contracts.md) §7；[verify-public-contracts.py](../../scripts/verify-public-contracts.py) 的 `check()` 调用点 | 读 §7 那句「检查项清单共 49 项」 | `49 = 28 + 6 + 15`（**静态条数**，见 §1.3 第一个坑） |
| 退出码 **0–6**（7 个） | `src/dexatlas/cli/main.py` 的 `EXIT_*` 常量；`public-contracts.md` §1.2（0 = 成功完成） | `grep -nE "^EXIT_[A-Z_]+ = [0-9]" src/dexatlas/cli/main.py` | `EXIT_EMPTY=1`、`EXIT_BAD_REQUEST=2`、`EXIT_FAILED=3`、`EXIT_AMBIGUOUS=4`、`EXIT_TRUNCATED=5`、`EXIT_NO_INDEX=6`，加 0（成功）= **0–6** |
| 一方示例 APK **5** 个 | `examples/`；`<!--fig:samples.apks-->` | `find examples -name "*.apk"` | `demo-app` / `multidex-app` / `obfuscated-app` / `strings-app` / `wide-app` = **5** |

- [ ] **若发布时补写了上表任何一行，复核时按表里那列命令重跑，并写下复算到的值。**
  查过是什么样：本轮五个数全部复算通过（13 / 23 / 49 / 0–6 / 5）。
- [ ] **注意 `cover-letter-templates.md:145` 的 “5–10 questions” 不是仓库数字**——
  那是给客户的提问（问对方要评估哪几类问题），不要拿它当项目指标改写。

### 1.3 三个最容易说错的口径

- [ ] **契约活检的「49」是静态条数，不是实跑条数。**
  怎么查：读 `public-contracts.md` §7 那句「**49 是静态条数，任何一次实跑都跑不满它**」
  及其下的两次实跑对照表。
  查过是什么样：静态 49 = 28 REST + 6 MCP + 15 CLI；实跑依机器而定——
  仅 androguard 时 **47（26 REST + 6 MCP + 15 CLI）**，三后端齐备时 **48（27 REST + 6 MCP + 15 CLI）**。
  ⚠️ 写「49/49 全部通过」是**不成立**的结论，旧稿里的这句已被删。
- [ ] **三个样本 ≠ 四个包 ≠ 客户案例。**
  怎么查：读 `docs/case-studies/README.md` 表格下方那段话。
  查过是什么样：三篇走查涉及**三个**一方 APK（`demo-app`、`obfuscated-app`、
  `multidex-app`——后者是第 2 篇的 multi-DEX 附录），**四个证据包对应四次分析**，
  每包一次，`run_id` 两两不同。别写成「四个客户案例」。
- [ ] **demo 与 api-integration 两个包是同一份样本的两次分析，别当成两个样本，也别因为「看起来重复」去删一个。**
  怎么查：解开两个 zip 读 `manifest.json`。
  查过是什么样：两者的 `project_id` 都是 `apk_80a8fe0e81204c9f`（project id 是
  APK sha256 的前缀，同一份样本必然同一个），但 `run_id` 不同
  （`run_e8e49384ab5246ab` 与 `run_fc8e432d4d094350`）；`report.md` 与
  `report.html` **各只有 `run_id` 与 `Analysis time` 两行不同**，其余数字相同。
  `obfuscated` 包（`run_dd897202eba74e28`）与 `multidex` 包
  （`run_4fde2fa0b5254ccb`）是另外两次分析，独立。

---

## 2. 字段长度（口径与脚本一律取自 `publish-review.md` §5）

口径：**raw** = Markdown 源码字符数；**plain** = 去掉 Markdown 语法后的正文字符数；
判定取**两者较大者**（保守）。门限：标题 ≤60、简介 ≤5,000、提案正文 ≤2,500。

- [ ] **标题仍 ≤60。**
  怎么查：`project-brief.md` 的 §Project title。
  查过是什么样：raw **53** / plain **53** ✅（余 7）。
- [ ] **简介仍 ≤5,000。**
  怎么查：`project-brief.md` 的 §Short description。
  查过是什么样：raw **1,410** / plain **1,404** ✅（余约 3,596）。
- [ ] **两封信的正文仍 ≤2,500。**
  怎么查：`cover-letter-templates.md` 的两节（模板态，含占位符）。
  查过是什么样：Template 1 raw **2,185** / plain **2,174** ✅；
  Template 2 raw **2,500** / plain **2,485** —— ⚠️ **正好压线，余 0**。
- [ ] **两份 scope 的 §What I offer 仍 ≤5,000。**
  怎么查：`scope-backend-automation.md` 与 `scope-ai-mcp.md` 的 §What I offer。
  查过是什么样：backend raw **592** / plain **588**；ai-mcp raw **781** / plain **773** ✅。
- [ ] **附件形态确认：`scope-ai-mcp.md` 整篇当附件，不当平台字段。**
  怎么查：读 §5.2 与 `scope-ai-mcp.md` 顶部的「Where this goes」。
  查过是什么样：整篇 raw **6,561** / plain **6,530**，**超过 5,000**，
  所以它是附件；粘贴到项目描述栏的只有 §What I offer（plain 773）。
  `scope-backend-automation.md` 整篇 4,950 / 4,941 ✅ 可以整篇贴。
- [ ] **发布当天对「实际粘贴的那一版」重算长度（不是对模板态）。**
  怎么查：把粘贴进表单框的文本存成临时文件，用 `publish-review.md` §5 的脚本跑一遍
  （脚本就是口径本身，纯标准库，不写任何产物）。
  查过是什么样：模板态的数如上；**替换占位符后的那一版必须重新测**——
  替换通常变长，而用法说明又要求删去不适用的小节，两个方向相反。

---

## 3. 占位符

- [ ] **模板里每一个 `{{...}}` 都被替换掉了。**
  怎么查：对**实际粘贴的那份文本**跑 `grep -c "{{"` —— 结果必须是 **0**。
  查过是什么样：模板文件里共 **26** 个 `{{` 记号 =
  **25 个待替换槽位**（Template 1 有 14 个、Template 2 有 11 个，其中 4 个嵌在示例句里：
  `{{input format}}`、`{{output format}}`、`{{items}}`、`{{systems}}`）
  + **1 个用法说明里的字面 `{{...}}`**（`cover-letter-templates.md:20`，那是给人看的，
  不用替换）。
  另三件素材（`project-brief.md`、两份 scope）**没有占位符**（`grep -c "{{"` = 0）✅。
- [ ] **替换后的长度没有超限。**
  怎么查：§2 的脚本，对替换后的那一版重算。
  查过是什么样：模板态 Template 2 已经**压线 2,500（余 0）**，
  替换后只要变长就**一定超**。Template 1 模板态余 315。
- [ ] **替换后语义完整**：占位符的例子文本（`e.g. "..."`）要连同示例一起处理，
  不要留下半句示例残留在信里。
  怎么查：通读粘贴后的正文，确认没有残留的 `e.g.`、示例引号或不完整的括号。
  查过是什么样：本轮以模板态核对，替换后由发布人自行确认。

---

## 4. 附件（证据包）

- [ ] **四个 zip 都在，且能被打开。**
  怎么查：`ls -la docs/case-studies/attachments/*.zip`
  查过是什么样：`api-integration-evidence-package.zip`、`demo-evidence-package.zip`、
  `multidex-evidence-package.zip`、`obfuscated-evidence-package.zip` 四个都在，
  都已被 git 跟踪。
- [ ] **每个包的内容完整。**
  怎么查：`python -c "import zipfile;print(zipfile.ZipFile(p).namelist())"`
  查过是什么样：每个包 4 项 —— `reports/report.md`、`reports/report.json`、
  `reports/report.html`、`manifest.json`。
- [ ] **两个包的 `report.md` / `report.html` 只差两行是正常的，别误删其中一个。**
  怎么查：解两个 zip 比 `sha256`。
  查过是什么样：`demo` 与 `api-integration` 的 `report.html`（8,549 字节）与
  `report.md`（5,171 字节）**长度相同，但 sha256 不同**——同一样本的两次分析
  （`run_e8e49384ab5246ab` 与 `run_fc8e432d4d094350`），差别只有 `run_id` 一行与
  `Analysis time` 一行。**这不是重复文件错误，不要因为「看起来重复」删掉一个包**，
  那会把「一份样本、两次分析」变成少一份附件。
- [ ] **别把内部文件打进 zip。**
  怎么查：检查包内清单。
  查过是什么样：四个包内只有报告与 `manifest.json`，
  **没有** `publish-review.md`、没有仓库源码、没有本机路径。
- [ ] **素材里给出的四个 zip 相对路径在客户那一侧能打开。**
  怎么查：`project-brief.md` 与 `cover-letter-templates.md` 里写的是仓库内相对路径；
  单独发 zip 时按附件上传，**不要**把仓库路径当成可点链接交给客户。
  查过是什么样：`cover-letter-templates.md:32-35`、`project-brief.md:123-126` 各列出四个 zip。

---

## 5. 不能一起发的东西

- [ ] **`docs/outreach/publish-review.md` 不外发、不作附件、不随提案发送。**
  怎么查：读该文件顶部第 7–9 行的标注。
  查过是什么样：顶部已写明「**内部核对记录——不对外、不作附件、不随提案发送**」✅
  （它记着核对基准、提交号与本机路径，是给自己看的）。
- [ ] **本清单（`docs/reports/outreach-publish-checklist.md`）同样不外发。**
  怎么查：发布时只挑 `docs/outreach/` 下四件素材 + 四个 zip。
  查过是什么样：本文件与其它内部记录都在 `docs/reports/` 下。
- [ ] **工作树是干净的：发布用的素材没有未提交的改动。**
  怎么查：`git status --porcelain`（应为空）；`git log --oneline v1.0.0..HEAD` 看哪些改动还没进任何 tag。
  查过是什么样：本轮开工时 `git status` 干净；`v1.0.0..HEAD` 之间有若干**已提交但未打 tag** 的改动
  （含契约表 §7 与对外文本的修正）。**素材的最新状态在 `c427e93`（在 tag 之后）**，
  所以「素材 = v1.0.0 发版树」这个说法已经不准确了——以工作树实际内容为准，逐条按本清单核。
- [ ] **没有任何 API key / secret / token 样式的内容被带出去。**
  怎么查：打包前对要发的文件跑一次密钥扫描（如 `grep -rniE "api[_-]?key|secret|token|bearer|password" <要发的文件>`）。
  查过是什么样：本轮四件素材与四个 zip 内均无此类字符串。
- [ ] **不把 `.scratch/`、`.env`、本机路径、数据库文件带进附件。**
  怎么查：核对包的清单（见 §4）与素材里出现的路径。
  查过是什么样：素材里只有仓库内相对路径；四个包内没有本机路径。

---

## 6. 身份与表述边界

- [ ] **素材只声称个人开源项目，无客户经验、无收益。**
  怎么查：`grep -niE "client engagement|revenue|paid|no client" docs/outreach/cover-letter-templates.md docs/outreach/project-brief.md docs/outreach/scope-ai-mcp.md docs/outreach/scope-backend-automation.md`
  查过什么样：四件素材共 **11** 处命中（2 + 3 + 3 + 3），全部是**否定式声明**
  （“No client engagement, revenue figure, or security-testing result is claimed”、
  “There is no client behind it and no client work is implied”、
  “no client engagement, client result, or revenue/time-saving figure is claimed or implied”）。
  ✅ 一致，没有出现任何客户名、成交额或收益数字。
- [ ] **case study 的「customer」人设措辞没被改回去。**
  怎么查：`grep -ri customer docs/case-studies/`（应无输出）；
  再看被替换掉的那些地方现在是什么词。
  查过是什么样：`grep` 结果为空 ✅；替换后的词是
  `potential user`（README ×2）、`developer`（api-integration）、`integrator`（api-integration）、
  `reader`（两篇走查各一处）。
- [ ] **「三个样本 / 两份分析」的口径仍在素材里点明。**
  怎么查：见 §1.1 第 4 条。
  查过是什么样：`cover-letter-templates.md:35-40`、`project-brief.md:123-126` 各有一段说明。
- [ ] **没有把本项目的验收说成已完成，也没有引用未达标的里程碑。**
  怎么查：`grep -niE "M6|M10|level 2|层级 2|accuracy" docs/outreach/*.md`（除 `publish-review.md`）。
  查过是什么样：四件素材里**没有** M6 / 层级 2 / M10 的提法。
  ⚠️ 反向风险：若发布时想写「agent 实测准确率」，**必须同时写明未达验收线**
  （M6 层级 2 实测 49/60 = 81.7%，未达 ≥90% 验收线；窄验证二轮 2/6、三轮 3/6，
  门槛 ≥4，两轮都未达标），否则就是无人能复算的断言。
- [ ] **「Draft for review — not published」标记的处理已决定。**
  怎么查：`grep -n "Draft for review" docs/outreach/*.md`
  查过什么样：四件素材**首尾各一处**（共 8 处）都写着这句话 ✅。
  发布当天要决定：保留（作为「尚未上线」的诚实声明）还是连同上方的说明一起删——
  **两者都可以，但不能只删一半**，留下「首尾标注不一致」更难看。
- [ ] **第三方归属仍在。**
  怎么查：`grep -nE "Apktool|JADX|Androguard" docs/outreach/project-brief.md`
  查过什么样：三个分析引擎各自点名并注明不是自有工作 ✅。

---

## 7. 发布后留痕

发布完成之后，把下面几项写下来（**写进内部位置，不要新增 `docs/outreach/` 下的文件**——
那个目录里的东西可能被一起发给客户）：

- [ ] **职位链接**：Upwork 职位/提案的 URL（含 proposal id）。
- [ ] **发送日期**：`YYYY-MM-DD`（例：2026年11月18日）。
- [ ] **发出的文案副本**：实际粘贴的标题、简介、两封信的正文、scope 段落，
  以及当时的字符数（用 §2 的脚本量出来的那一版）。
- [ ] **发出的附件清单**：四个 zip 的文件名与大小。
- [ ] **素材版本**：发出时对应的 commit 号（便于日后对照素材与仓库）。
- [ ] **若发布后又打了新 tag**：回头改 `project-brief.md` 的版本句
  （现在是 `v1.0.0 (tagged 2026-11-17)`），并重跑
  `uv run --no-sync python scripts/check-version-claims.py --base auto`。
- [ ] **附件发出后的回执**：平台是否接受、对方是否已下载（只记事实）。

---

## 8. 本轮做了什么 / 没做什么

**做了：**

- 新增这一份清单（`docs/reports/outreach-publish-checklist.md`）。
- 独立复算字段长度（沿用 `publish-review.md` §5 的脚本与口径），
  复算第 1、2、3 节的每一个数字，核对四个 zip 的内容与字节一致关系。
- 跑过三个只读门禁（结果见下）。

**没做（明确不做）：**

- **没有向任何平台提交、发布、复制或发送任何内容**，没有登录账号，没有联网，
  没有打 tag，没有调用模型 API。
- **没有修改 `docs/outreach/` 下的任何文件**（素材本体由主线维护）。
- 没有运行 `pytest --cov`、任何 coverage 命令、`uv sync`、
  `scripts/refresh-report-figures.py`（会重写报告数字）。
- 没有改 `src/`、`tests/`、`scripts/` 或其它任何既有文件。

**只读门禁（2026年11月17日，本分支）：**

| 门禁 | 命令 | 结果 |
|---|---|---|
| 文档测试 | `pytest tests/test_docs.py -q` | **60 passed** |
| 文档引用 | `uv run --no-sync python scripts/check-doc-citations.py` | citations 221（naming a symbol 162 / pointing only at a location 59），unresolved **0**，drifted **0** |
| 版本声明 | `uv run --no-sync python scripts/check-version-claims.py --base auto` | findings 2（均在 `8f9ddcaf` 已记录），退出码 **0** |
