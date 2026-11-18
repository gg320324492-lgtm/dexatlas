# 测量数字自动覆盖设计：让「数字随测量走」管住所有手写位置

**日期：** 2026-11-18 · **性质：** 只读调研报告（本文件是新增的唯一产物，未改任何既有文件）
**回答的问题：** 怎样让测量数字自动覆盖所有手写位置，不再靠人记得同步。

---

## 0. 背景与问题

这一轮 v1.0.0 发版反复出事的根源之一：源指纹只覆盖 `src/`、`tests/`、
`pyproject.toml` 与测量脚本本身（`scripts/refresh-report-figures.py:114` 的
`FINGERPRINT_FILES`，经 `fingerprint_files()` 于 `:721` 收集），`docs/`、
`README.md` 正文、`.github/workflows/ci.yml` 都不在内。于是每次改文档都要人工
同步 10+ 处数字，漏一处就红一次 CI 或发一份带旧数的 Release。发版清单 §8.2 的
B7 条目（`docs/reports/v1.0.0-release-checklist.md:645`）已记录
「README 首屏手写数字没人管」。

本项目已有的三类机制，本报告全部沿用、不另起炉灶：

| 机制 | 代表 | 模式 |
|---|---|---|
| 生成时写盘 | `scripts/refresh-report-figures.py` 的 `<!--fig:...-->` 标记（`FIGURE` 于 `:231`）+ `apply_figures()`（`:1022`）+ `apply_badges()`（`:1046`）+ `render_status()`（`:1079`） | **自动写**：测量完整才写，写报告、`docs/status.md`、两份 README 徽章 |
| 旁证 + 检查 | `scripts/make-social-preview.py` 写 `.github/social-preview.json`（`ASIDE` 于 `:87`），`check()`（`:659`）在 CI `social-preview` job 核数 | **自动核对**：图不能 diff，核的是数 |
| 声明锚树 | `scripts/check-doc-citations.py` 的 `DOCS` 清单（`:116`）+ `TREE_DOCUMENTS`（`:154`，按文档声明的 ref 解析行号） | **自动核对**：`file:line` 引用锚到它声称的那棵树 |
| 事实核对 | `scripts/check-version-claims.py`：release 规则用 `measured_figures()`（`:963`，`git show tag:` 读 **tag 树**报告）核对发版文档；outward 规则用 **当前树** 报告的 fig 值（`main()` 于 `:1678` 读 working tree）核对 `docs/outreach/` 等对外素材 | **自动核对**：数字与测量对不上就红 |

一个能说明「双轨制为什么对」的实测：本报告撰写时工作树处于测量中间态
（报告落盘 `tests.total = 1649`，而对外素材仍写着上一轮的 `1,690`），
`check-version-claims.py` 当场抓出 5 处 `outward-tests` 不一致——机制在正确工作。
同一次检查也暴露了盲区：`docs/portfolio.md:67-68` 手写的 `1,690 tests at 93.3%`
**没有**被抓（它不在 `OUTWARD_DIRECTORIES` 里，见 §2.6）；三处文档里的 CI job
数互相矛盾也没有任何检查报红（见 §2.7）。

---

## 1. 逐位置盘点与结论（问题 1）

结论分三档：**A = 已有自动写，维持**；**B = 纳入自动写（加 fig 标记或脚本渲染）**；
**C = 只纳入自动核对（不改写，防篡改语义/历史）**；**D = 两者都不合适**。

### 1.1 A 类：已有自动写，维持现状

| 位置 | 现状 | 守护 |
|---|---|---|
| `docs/reports/phase1-execution-report.md` 全部 fig 标记（如 `:76`-`:77`） | refresh 脚本写 | `tests/test_docs.py:672` `test_execution_report_numbers_match_the_code`、`:718` `states_every_generated_figure`、`:725` `coverage_figures_describe_the_current_code`（指纹比对）、`:765` `suite_figures_add_up_to_the_tests_that_exist` |
| `docs/status.md:23`-`:24` 快照表 fig 标记 | `render_status()` 写 | `tests/test_status_figures.py:59`/`:66`/`:87` |
| 两份 README 徽章（`README.md:12`-`:13`、`README.zh-CN.md:12`-`:13`） | `apply_badges()` 写（徽章是 URL，放不了 HTML 注释，所以用 URL 模式匹配回写） | `tests/test_docs.py:1377`、`:1397`；`tests/test_version_claims.py:700` `test_a_badge_that_is_one_test_off_is_a_finding` |
| `.github/social-preview*.png` 两张卡片 | `make-social-preview.py` 画图 + 写旁证 JSON | 同脚本 `--check`（CI `social-preview` job，`ci.yml:651`）；`tests/test_social_preview.py:114`/`:228` |

### 1.2 B 类：可纳入自动写

| 位置 | 结论与理由 | 改法 |
|---|---|---|
| `docs/status.md:26` 与 `:50` 的 CI job 数（「9 个 workflow job、10 次并行运行」） | 数字来源是 `ci.yml` 的静态结构，可解析、可生成；且当前已与实况脱节（见 §2.7） | 新增 `fig:ci.jobs` / `fig:ci.runs` 由 refresh 脚本写入（解析 `ci.yml` 零成本、不需测量）；同时加独立核对测试（§3.1），双保险 |
| `docs/how-to-verify.md:147` / `how-to-verify.zh-CN.md:120` 的「收集到的测试数……**1690**（**1541** 快 + **149** 集成）」 | 这句已是 `STATED_NUMBERS` 正则（`tests/test_how_to_verify.py:36`）的比对目标，但那是「核对」不是「写」。改成 fig 标记后与报告同源， prose 测试可简化 | 把三个粗体数换成 `<!--fig:tests.total-->` 等标记；`tests/test_how_to_verify.py:115` 的 prose 比对保留作第二道闸 |
| `docs/how-to-verify.md:171`-`:168` / zh `:144`-`:145` skip 对照表（`1659 passed, 31 skipped` / `1690 passed、0 skipped`） | 「取了样本」行的 `1690 passed、0 skipped` 就是 `suite.passed`/`suite.skipped`，可直接标记化；「没取样本」行的 `1659/31` 是某次树状态的历史值，会随树漂移 | 「取了样本」行改用 `<!--fig:suite.passed-->`/`<!--fig:suite.skipped-->`（该行已部分引用这两个 fig 名）；「没取样本」行删去会过期的具体总数，只保留 skip 理由分类（25+2 条），并加核对测试（§3.3） |

**不纳入自动写的 B 类边界**：`docs/how-to-verify.md:153`-`:154`（zh `:126`-`:127`）
的 `pytest --collect-only` 期望输出行**不能**用 fig 标记——它们在代码块里，HTML
注释在代码块内会原样渲染出来。这两行保持手写，由
`tests/test_how_to_verify.py:95`（实跑两条收集命令比对期望输出）自动核对——这
已经是正确的机制。

### 1.3 C 类：只核对、不自动写

| 位置 | 为什么只核对 | 现有/建议守护 |
|---|---|---|
| `docs/releases/v1.0.0.md:94`-`:98`、`:242`（发版说明 Verification 段） | 发版说明是**历史记录**：它陈述「v1.0.0 那棵树测出什么」。自动改写会把历史记录篡改成「今天的树」，直接违反它自己的声明 | 已有：`check-version-claims.py` 的 release 规则（`check_release_numbers()` 于 `:1231`，按 tag 读 `measured_figures()`） |
| `docs/reports/v1.0.0-github-release-body.md:167`-`:176`、`:267`-`:268`、`:297`-`:304`（Release 正文 + 附录出处表） | 同上，且正文开头声明「Line numbers refer to the v1.0.0 release tree」；附录每条数字带 `file:line`，行号锚定 tag 树 | 已有：release 规则 + `check-doc-citations.py` 的 `TREE_DOCUMENTS` 把它锚到 `v1.0.0`（`:155`） |
| `docs/outreach/` 四份素材（`project-brief.md:50`/`:87`、`scope-backend-automation.md:24`、`cover-letter-templates.md:82`、`scope-ai-mcp.md:28` 的 eleven tools）+ `publish-review.md:23`-`:24`、`:50`-`:53` | 对外文案，措辞敏感（约数 `~1,540` vs 精确数 `1,690` 是有意的修辞选择）；`publish-review.md` 的表格还故意保留「修正前」旧数作对照（backtick 引用豁免已处理，见 `tests/test_version_claims.py:1081`） | 已有：outward 规则（`check_outward_numbers()` 于 `:1364`、`check_outward_counts()` 于 `:1401`），实测正抓着 5 处红 |
| `docs/reports/social-preview-howto.md:72`-`:75` 的「图上文字 → 出处」映射表 | 这张表写的是**出处关系**（哪个数来自哪个文件哪一行），不是数字本身；自动改写会掩盖「出处是否还成立」这个需要人判断的问题 | 已有：该文件在 `check-doc-citations.py` 的 `DOCS` 清单里（`:123`），表内 `file:line` 全部被核对 |
| `docs/releases/v1.0.0.md:58`/`:64`、release body `:89`/`:95` 的「nine files / three evidence packages」；release body `:338` 与发版说明 `:235` 的「MCP tools 10 → 11」 | 样本数/附件数/MCP 工具数是**结构事实**不是测量值：来源是目录内容与 `@server.tool` 注册点，变了应该改代码或目录，再让检查器对账 | 已有：outward 规则的 samples/tools 检查（`tests/test_version_claims.py:1060`/`:1071`）；release 文档由 release 规则覆盖 |

### 1.4 D 类：两者都不合适（保持手写，靠评审）

- **Release 正文的英文叙述句**（如 `:167` 的「The full environment run reports
  …; a skip is not a pass, so the zero is part of the claim」）：数字嵌在论证里，
  脚本替换会破坏句子；且这是 tag 树的历史记录。核对已覆盖。
- **CHANGELOG 的历史测量描述**（如「全量 suite 1575 项通过」是 `1e8d947` 时期
  的中间值）：它陈述的是**当时**的事实，永远不该被刷新。`check-version-claims`
  对历史版本只核对测试数与该 tag 报告的一致性，不多不少。
- **约数与修辞**（`~1,540 automated tests`）：自动改写会消灭有意的约数修辞；
  核对规则已把「约数 vs 落盘值不符」当作 finding 提示人工决断，而不是自动改。

### 1.5 README 首屏（B7 的两处）——已经处置完毕，加防回潮闸

B7 记录的两处（首屏「一次测量（N 个测试、0 跳过）」句、social preview 的 alt
文本数字）在 `5c097fe` 一轮已按**删除数字**方案修掉：当前 `README.md:25` 的 alt
是 `DexAtlas — From APK to Evidence`，无数字；首屏无测量句；
`docs/reports/social-preview-howto.md:59` 已立规「alt 文本里不写数字」。
**残余风险是回潮**——将来有人再把数字写回去，没有任何检查拦。方案见 §3.4：
加一条「README 首屏 img alt 不含数字」的核对测试，把 howto §3 的规定变成门禁。

---

## 2. 三个专项判断

### 2.1 CI job 数：当前三处文档互相矛盾，且零守护（本报告实测）

- `.github/workflows/ci.yml` 实际有 **12 个 job 定义**（`lint` `:38`、`test`
  `:128`、`test-partial-backends` `:218`、`m3-comparison` `:300`、`docker`
  `:436`、`security` `:446`、`contracts` `:481`、`contracts-without-jadx`
  `:541`、`m10-selfcheck` `:565`、`gate-coverage` `:605`、`social-preview`
  `:630`、`measurement` `:658`；`runs-on` 恰出现 12 次），其中 `test` 是
  3.12/3.13 两格矩阵（`:136`-`:137`）→ 一次 tag 推送展开 **13 次并行运行**
  （`measurement` 只在 tag 上跑，`if:` 于 `:661`）。
- `docs/status.md:26` 写「9 个 workflow job、10 次并行运行」（`:50` 同口径）；
  `CLAUDE.md:79`（`AGENTS.md:79` 镜像）写「ten jobs (eleven parallel runs)」；
  `docs/portfolio.md:68` 写「ten CI jobs (eleven runs)」。三处口径互不相同，
  且都与 ci.yml 实况不符——因为 job 数会随门禁增加而变，而没有任何检查把它
  锚住。

这正是「手写数字没人管」的活标本，也是新检查收益最大的地方。

### 2.2 指纹要不要扩到 docs/README/workflows？——**不扩**（问题 2）

**不扩的理由：**

1. **语义不对**。指纹回答「这棵树的测量还有效吗」。测试数、覆盖率、通过数由
   `src/`+`tests/`+`pyproject.toml`+测量脚本决定；改一行 README 不改变任何
   测量语义。把 docs 纳入指纹，等于宣称「改文档会让覆盖率失效」——这是假话。
2. **代价不成比例**。完整测量约 7.5 分钟且要求后端、fixture、Pillow、ffmpeg、
   git tags 齐备；CI 的 measurement job 只在 tag 推送上跑。若 docs 纳入指纹，
   日常改文档后指纹天天对不上，而重测在本地/CI 都不会随手跑——结果是门禁
   长期红，团队学会无视它（狼来了）。
3. **已有更准的兜底**。docs 的正确守护方式不是「树变了就重测」，而是
   「**每个数字都能追溯到它的来源**」：`check-doc-citations` 的声明锚树管
   `file:line`；`check-version-claims` 的双轨制管「这个数是哪次测量的」；
   `make-social-preview --check` 管图上的数；`test_public_contracts` 管契约
   计数六处一致（`CONTRACT_CHECK_TOTAL = 49` 于 `tests/test_public_contracts.py:762`，
   `MATERIALS_THAT_STATE_THE_COUNT` 于 `:765`，六份材料逐一断言）。
   `check-gate-coverage.py`（`GATES` 于 `:48`）另保证每道门禁都有人跑。

**要补的只有一块**：`docs/` 根层与 README 正文里「非引用、非徽章」的手写
数字，目前只有部分被 outward 规则覆盖（`OUTWARD_DIRECTORIES` 只含
`docs/outreach/`、`docs/case-studies/`、`docs/proposals/`，
`check-version-claims.py:127`）。`docs/portfolio.md` 这样的对外门面文档漏在
外面。补法见 §3.2——用**显式文件清单**扩大 outward 核对范围，而不是扩指纹。

### 2.3 「改文档必须重测」的正确形态

不改指纹后，纪律变成：**改了会改变测量语义的东西（src/tests/pyproject/测量
脚本）→ 必须重测**（指纹闸，已有）；**改了陈述数字的文档 → 必须让核对测试
重新对账**（各专项检查，本报告补齐缺口）。两类改动各有一个闸，谁也不需要
为谁重测。

---

## 3. 最小改动方案（问题 3）

按收益/成本排序。全部是**新增测试或小改检查器**，不新增 CI job（测试落在
既有 `test` job；`check-version-claims` 的改动落在既有 lint job 的
Version claims 步骤，`ci.yml:94`）。

### 3.1 第一步（收益最大）：`tests/test_ci_shape.py` —— 把 CI 结构数字锚住

- **改哪个文件**：新增 `tests/test_ci_shape.py`。
- **做什么**：
  1. 解析 `.github/workflows/ci.yml`（按行正则，不引 PyYAML——与
     `tests/test_platform_independent_gates.py:813` 同法）：数出 job 定义键
     （`^  [a-z0-9_-]+:$` 且键名属于 job 集合，排除 `on:`/`env:` 等顶层键）、
     检出 `matrix.python-version` 列表长度、算出并行运行数 = job 数 − 1 + 矩阵格数。
  2. 断言 `docs/status.md:26`、`docs/status.md:50`、`CLAUDE.md:79`、
     `docs/portfolio.md:68` 里写的 job 数/运行数与解析结果一致。
  3. （可选加固）把 job 名单与 `docs/status.md:50` 起的 job 表逐行对照。
- **红→绿测试思路**：先写测试（此刻它应该红——三处文档与 12/13 对不上），
  改文档对齐实况后转绿；反向验证：往 ci.yml 加一个 job 不改文档 → 测试红。
- **CI 落点**：`test` job（3.12 全后端配置）自动携带；无需登记
  `check-gate-coverage`（它管的是 `scripts/` 下的 gate 脚本，测试不走那个清单）。

### 3.2 第二步：把 `docs/portfolio.md` 纳入 outward 核对

- **改哪个文件**：`scripts/check-version-claims.py`。
- **做什么**：新增模块级常量
  `OUTWARD_FILES = ("docs/portfolio.md",)`，并把 `check_outward_numbers()`
  （`:1364`）里的目录前缀判断
  `if not name.startswith(OUTWARD_DIRECTORIES)` 改为
  「前缀匹配 **或** `name in OUTWARD_FILES`」。一处改动，portfolio 的
  测试数/覆盖率/MCP 工具数/样本数全部自动对账。
- **红→绿测试思路**：仿照 `tests/test_version_claims.py:1039`
  `test_a_wrong_test_count_in_an_outward_material_is_a_finding` 的
  `_outward_findings()` 夹具（`:1011`），加一条
  `("docs/portfolio.md", "1,500 automated tests")` → 断言 `outward-tests`；
  再加「正确数字不报」的反例。
- **CI 落点**：lint job 的 Version claims 步骤（`ci.yml:94`-`:125`），push/PR/tag
  三种事件都以正确的 base 跑。

### 3.3 第三步：补齐 how-to-verify skip 表格行的核对

- **改哪个文件**：`tests/test_how_to_verify.py`。
- **做什么**：现有两个测试盖住 prose 句（`:115`）与 collect 期望行（`:95`），
  但 skip 对照表（`docs/how-to-verify.md:171`-`:168`、zh `:144`-`:145`）没人查。
  新增一个测试：从执行报告的 record block（`<!--report-figures:{...}-->`，
  正则 `RECORD` 在 `scripts/refresh-report-figures.py:234`；测试侧可仿
  `tests/test_status_figures.py` 读 record 的方式）取 `suite.passed` /
  `suite.skipped` / `tests.total`，断言表格「取了样本」行与之逐字一致；
  断言「没取样本」行不再含会过期的绝对通过数（或其数 = 报告记录的
  无样本运行值，若保留则须与 record 的 `skipped_tests` 对账）。
- **红→绿测试思路**：手改表格里的 `1690` → 红；按 fig 落盘值改写该行 → 绿。
- **CI 落点**：`test` job。

### 3.4 第四步：README 首屏防回潮闸

- **改哪个文件**：`tests/test_docs.py`。
- **做什么**：新增测试：取两份 README 首屏区（徽章行到 `</div>` 之间），
  断言 `<img ... alt="...">` 的 alt 属性与 `<sub>` 说明行里**不出现三位以上
  阿拉伯数字**（徽章 URL 里的数字走 `apply_badges` 白名单路径，不在 alt/正文
  判断范围内）。这把 `social-preview-howto.md:59` 的「alt 文本里不写数字」
  从约定变成门禁，也堵住 B7 描述的「首屏复述测量数」回潮。
- **红→绿测试思路**：往 alt 里塞 `1690 tests` → 红；恢复纯文字 alt → 绿。
- **CI 落点**：`test` job。

### 3.5 第五步（可选，做了更顺）：status.md 的 CI 行改由 fig 标记供给

- **改哪个文件**：`scripts/refresh-report-figures.py` + `docs/status.md`。
- **做什么**：`build_record()` 时顺带解析 ci.yml，把 `ci.jobs` / `ci.runs`
  放进 record；`render_figures()`（`:989`）加两个键；`docs/status.md:26`/`:50`
  的两处数字换成 `<!--fig:ci.jobs-->`/`<!--fig:ci.runs-->`。
  这样 job 数随 ci.yml 变化在**下次测量**时自动同步；3.1 的核对测试继续
  兜住「改了 ci.yml 还没重测」的窗口。
- **注意**：ci.yml 不在指纹里，所以这两个 fig 不参与 stale 判定——这正是
  3.1 的独立核对测试存在的理由。两者是互补不是重复。
- **红→绿测试思路**：`tests/test_status_figures.py` 增一条：record 里构造
  `ci.jobs=12`，候选 status 页写 `9 个` → `render_status` 后变成 `12 个`。

### 3.6 明确不做的事

- **不自动改写**发版说明、Release 正文、CHANGELOG、outreach 素材（理由见
  §1.3/§1.4/§4）。
- **不给 outreach 素材加 fig 标记**：素材要整段贴去外部平台，HTML 注释虽不
  渲染但属于仓库内部机制；核对（check-version-claims）+ 人工改已够。
- **不扩指纹**（§2.2）。
- **不新增 CI job**：上述全部落在既有 job；新测试也不是 `check-*.py` gate
  脚本，不需要进 `check-gate-coverage.py` 的 `GATES` 注册表。

### 3.7 实施顺序（前三步）

1. **`tests/test_ci_shape.py`**（§3.1）：纯新增、零依赖、立刻把「9/10 vs
   10/11 vs 12/13」这类反复出错的数字锚住；顺手把三处文档改到与 ci.yml 一致。
2. **`check-version-claims.py` 纳入 `docs/portfolio.md`**（§3.2）：一行判断
   的改动，把最后一个漏网的对外门面文档盖进既有 outward 核对。
3. **how-to-verify skip 表格核对 + README 防回潮闸**（§3.3 + §3.4）：两个小
   测试补掉 B7 与 how-to-verify 的最后缺口。

第五步（fig:ci.*）与后续扩展在前三步落地后再评估。

---

## 4. 风险与规避（问题 4）

**自动改 Release 正文/发版说明的风险：**

1. **篡改历史**。发版文档陈述「那次测量测出什么」；若脚本把 `1690` 自动刷成
   下次的 `1720`，「测自 v1.0.0 发版树」的声明就变成假话。→ 规避：发版文档
   **永不自动写**，只由 check-version-claims 按 tag 树核对。
2. **误替换**。同一文档里 `49/60`（M6 得分）、`49`（契约条数）、`444`（v0.1.3
   测试数）长得都像「该刷新的数」；裸数字替换必然误伤。→ 规避：脚本只碰
   `<!--fig:key-->...<!--/fig-->` 标记内的内容（`apply_figures` 的既有行为，
   `scripts/refresh-report-figures.py:1022`），**一个裸数字都不碰**；想被自动
   刷新的数字必须先由人把它标记化，标记化这个动作本身就是一次「这个数由
   测量供给」的声明。
3. **与人工措辞冲突**。约数（`~1,540`）、限定语（「完整环境下」）、对照结构
   （publish-review 的修正前/修正后表格）都是措辞的一部分。→ 规避：核对而非
   改写；`quoted_spans()`（`scripts/check-version-claims.py:1300`）已把反引号
   引用的「别人的话」豁免；发现不一致时检查器给 finding、人决定怎么改。
4. **多文档同句漂移**。同一数字出现在 6+ 份材料（如契约 49 条）时，逐个改
   容易漏。→ 已有解法照抄：`tests/test_public_contracts.py:765` 的
   `MATERIALS_THAT_STATE_THE_COUNT` 模式——把「哪些文档复述了这个数」列成
   清单，逐一断言。新增需要多处复述的数字时照此登记。

**新增核对测试自身的风险：**

5. **核对测试写成硬编码**（把 1690 写进测试）会变成第二个需要人同步的地方。
   → 规避：核对测试的期望值一律**现算**——或实跑（`test_how_to_verify` 的
   collect 方式），或从 record block / ci.yml / AST 现解析，不抄数。
6. **核对过严导致狼来了**。比如要求所有约数都精确相等。→ 规避：沿用
   check-version-claims 的既有哲学——只拦「与测量矛盾且无豁免标注」的陈述，
   约数、历史值、引用他人文字都有明确豁免通道。

---

## 5. 一页结论

- **已有自动写（维持）**：报告 fig、status fig、README 徽章、social preview 卡。
- **补自动写**：status 的 CI job 数（fig:ci.jobs/ci.runs，可选）；how-to-verify
  prose 句与 skip 表格行标记化（「取了样本」行）。
- **只核对（大部分位置的正确归宿）**：发版说明、Release 正文、CHANGELOG、
  outreach、social-preview-howto 映射表、结构事实（样本数/MCP 工具数）。
  核对网补三个洞：`test_ci_shape`（CI 结构数）、portfolio 纳入 outward、
  how-to-verify skip 表格行 + README 首屏防回潮。
- **指纹不扩**：docs/README/workflows 的改动不改变测量语义；扩指纹会让门禁
  长期假红。数字的正确性靠「声明锚树 + 双轨核对 + 旁证 JSON + 材料清单断言」，
  本报告补齐了最后三个没人查的洞。
- **实施前三步**：`test_ci_shape.py` → portfolio 纳入 outward 核对 →
  how-to-verify 表格核对 + README 防回潮闸。
