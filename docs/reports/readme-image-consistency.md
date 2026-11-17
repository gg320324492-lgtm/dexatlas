# README 首屏与 social preview 图的一致性复核

> 复核对象：`.github/social-preview.png`、`README.md`、`README.zh-CN.md`
> 复核日期：2026年11月18日
> 复核方式：**只读**。图、README、报告均未改动；本文件是本次复核新增的唯一文件。
> 数字基准：`docs/reports/phase1-execution-report.md` 的 `<!--fig:...-->` 标记与其中的
> 机器可读测量记录块（`<!--report-figures:...-->`）。复核时该记录为
> `tests.total=1632` / `tests.fast=1485` / `tests.slow=147` /
> `coverage=93.3%（7135/7650）` / `suite.passed=1631` / `suite.failed=1`。

## 0. 结论摘要

**图本身是干净的**：1280×640、70,617 字节，无截断、无中英错别字；howto §4 那张出处表
十三行里十行逐字命中，数字全部自洽（1485+147=1632、28+6+15=49）。错的两处在表里，
不在图上：一行指向的字符串仓库里根本不存在，两行的行号指错了七行。

**问题不在图，在图旁边。** 首屏同时摆着**三个**测试数——徽章 `1631 passing`、图上 `1632`、
正文散文 `1612`——其中 `1612` 是上一轮重测量之前的旧值，且已经被两份评审报告列为
「必须改」而至今未改。更要紧的是：**这张图没有任何自动重生成的路径**。绘图脚本按 howto
的说法不入库，CI 里没有一处检查看它，howto 那张出处表本身也不在引用检查器的范围内。
主会话正在跑的重测量一落定，这张图就必须**手工重画**，否则它会静默地停留在上一轮。

发现 **14 条**，按后果排序：严重 3 条、中 6 条、低 5 条。

| # | 后果 | 一句话 |
|---|---|---|
| 1 | 严重 | 首屏并存三个测试数，`1612` 是旧值，正文与 alt 文本各写了一遍 |
| 2 | 严重 | 徽章 `1631 passing` 与图上 `1632` 不一致，根因是测量记录里 `failed=1` 尚未重测 |
| 3 | 严重 | 图零自动化守护：重测量落定后卡片会静默过期，而 howto 承诺的「跟着变」不成立 |
| 4 | 中 | 图上那 49 项检查的分布 `28 REST + 6 MCP + 15 CLI` 是检查项条数，不是接口数，与报告的 23 端点打架 |
| 5 | 中 | `49 公共契约检查项` 没说是静态条数，读者会读成「49 项全过」 |
| 6 | 中 | 英文 README 上的卡片，标签与唯一的定位句全是中文 |
| 7 | 中 | howto §4 那张出处表本身有两处错（中文 tagline 的出处、`49` 的行号） |
| 8 | 中 | 解释徽章口径的那段注释是中文，挂在英文 README 上 |
| 9 | 中 | 中文 README 说自己的徽章要「人工同步」——其实脚本两个都写，这话会招来手抄 |
| 10 | 低 | 中英 tagline 不一致：英文有 `bounded`，中文没有 |
| 11 | 低 | 中文 README 没有这张图 |
| 12 | 低 | 徽章的链接落点不对，首屏的数字无一处一键可达的出处 |
| 13 | 低 | 图面版式：三个大数字同权重、比率与计数并列、页脚混入最强信任信号、无成熟度信号 |
| 14 | 低 | 术语小出入：卡片「可核查」vs 中文 README「可核验」 |

---

## 1. 需要改的（逐条：原文逐字 → 读者会怎么误读 → 建议改法）

### 1.1 【严重】正文与 alt 文本里的 `1612` 是上一轮的旧值

**原文（逐字）**

- `README.md:15`
  > `> 徽章是**完整环境下**的一次测量（1612 个测试、0 跳过）。在没抓第三方样本的机器上，`
- `README.md:21`
  > `README.md:21` 的 img 标签，`src` 指向 `.github/social-preview.png`，`alt` 文本逐字是
  > 「DexAtlas — From APK to Evidence: 93.3% first-party code coverage, 1612 tests, 49 public contract checks」

**读者会怎么误读**

首屏同一屏内，徽章写 `1631 passing`、正文写「1612 个测试」，两个数只差 19 却指同一件事，
没有任何一句话说明为什么。读者会二选一：要么认为徽章是坏的（徽章通常被认为更权威），
要么认为正文过期。两种猜测都会让读者对后面所有数字打折。

更隐蔽的是 alt 文本：屏幕阅读器用户、图片加载失败时的读者、以及 GitHub 把它当纯文本
索引时读到的都是 `1612 tests`——**图上明明写着 1632**。同一个元素自己和自己矛盾。

**建议改法**

- `README.md:15` 的数字与徽章同源：徽章写的是「通过数」，正文就写「1631 个测试通过、0 跳过」
  （或改成「1632 个测试收集、0 跳过」，并说清是哪个口径），不要出现第三个数。
- `README.md:21` 的 alt 文本改成与图一致的 `1632 tests`，并把口径写进去
  （`1632 tests collected`）。

**依据**

这不是新发现。`docs/reports/english-reader-review-2.md:855` 与
`docs/reports/portfolio-readiness-2026-11-18.md:429-431` 已经把这两行列为「必须改」，
写明「改成 1620，与 phase1-execution-report.md:76 同源」；此后测量又从 1620 走到 1632，
但这两行**仍停在 1612**。两次评审都提了，两次都没改——本次复核按重复发现记为严重。

---

### 1.2 【严重】徽章 `1631 passing` 与图上 `1632` 不是同一个数

**原文（逐字）**

- `README.md:12` → 本窗口基准树上的徽章是
  徽章上的测试数是 **1631**（本窗口基准树的值；主会话随后把它改成了 **1632**——
  徽章 URL 里那个数同理，这里不照抄，免得把旧值当成现状）
- 图上第三栏大数字 → `1632`，其下小字 → `1485 快 + 147 集成`

**读者会怎么误读**

读者在图和徽章之间来回看两次，会得出「图上多算了 1 个测试」或者「徽章少算了 1 个」。
两种读法都会让人怀疑其中一个数是手抄错的。实际上两个数都没抄错，只是**口径不同**：
徽章取的是 `suite.passed`（通过数），图取的是 `tests.total`（收集数）——而这两个数当前
不相等，因为测量记录里 **`"failed": 1`**（`docs/reports/phase1-execution-report.md:1099`）
而 `"passed": 1631`（同文件 `:1100`），`1631 + 1 = 1632`。

**这不是笔误，是一次没做完的重测量。** `git show 00309bb` 的提交说明里写着
「之后要再跑一次测量，让报告的 record block 里是『1632 passed / 0 failed』」——
那次重测量没有发生，于是记录块停在 `1631 passed / 1 failed`，而所有对外材料按
「1632 全过」在写。

**连带（发布材料里的矛盾，比首屏更严重）**

- `docs/releases/v1.0.0.md:90-91`：「The full environment run reports **1632 passed +
  0 xfailed + 0 skipped**」——与记录块 `:1099-1100` 直接矛盾。
- `docs/how-to-verify.md:168`：「`1632 passed`、**0 skipped**——这就是报告里记录的那次完整
  测量」——同样与它所引用的记录块矛盾。
- `docs/status.md:23` 用的是 `tests.total`（1632），与徽章口径不同但数值一致。

**建议改法**

1. 先把那次重测量做完（主会话正在做）。若结果是 `1632 passed / 0 failed`，徽章自动变
   `1632 passing`，与图上的 `1632` 天然对上，本条自动消解。
2. 但**别指望它自动消解**：图是手工产物（见 1.3），重测量后必须重画一次图，
   并核对徽章与图一致。
3. 无论重测量结果如何，把「收集数 / 通过数」的口径在首屏写清楚一次
   （徽章 = 通过数；图 = 收集数），避免下次再冒出第三个口径。

---

### 1.3 【严重】这张图没有自动重生成的路径，重测量后会静默过期

**原文（逐字）**

- `docs/reports/social-preview-howto.md:61-62`：
  > `图上的数字不是手抄的：生成脚本直接解析上面这些文件（§5）。报告里的数字变了`
  > `（`scripts/refresh-report-figures.py` 写回），下一次生成的图就跟着变。`
- `docs/reports/social-preview-howto.md:66-67`：
  > `脚本不入库——画一张图不需要给仓库增加依赖，Pillow 是 demo extra 已经带来的。把它放在`
  > `**项目根目录下**临时用（不要提交，用完删掉或加进 `.gitignore`），例如`

**读者会怎么误读**

这半句承诺正是读者判断「图上的数可不可信」的依据。它今天不成立：

- 全仓 `grep -rn "social.preview|social_preview" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.cfg"`
  **零命中**——CI 的六个 job 里没有任何一个看这张图。
- `scripts/check-doc-citations.py` 的 `DOCS` 列表（`:87-96`）只有
  `docs/analysis-provenance.md`、`docs/architecture/public-contracts.md`、
  `docs/reports/phase1-execution-report.md`、`docs/benchmarks/large-apk.md`、
  `docs/releases/*.md`、`docs/reports/*-github-release-body.md`——
  **`docs/reports/social-preview-howto.md` 不在其中**，所以 howto §4 那张表里的
  `file:line` 引用也没有机器守着（这正是 1.7 那两处错能活下来的原因）。

后果是：重测量一旦把 `tests.total` 或覆盖率改成别的值，**图会安静地停留在上一轮**，
而它看上去和徽章一样是自动同步的。读者不会怀疑一张图上的数字——这正是它被画出来的理由。

**建议改法**（二选一，优先前者）

1. 把绘图脚本入库（放 `scripts/`），并加一个检查：脚本解析出的每个数字必须等于
   报告里的 `<!--fig:...-->` 值；再在 CI 里跑一次「生成 → 与仓库里的 PNG 比对字节」。
   顺带解决 1.7 的「手写字符串无处可查」。
2. 若坚持不入库：把 howto §4 结尾那半句改成实话——「报告的数字变了之后，这张图**必须
   手工重画**；仓库里没有任何检查会发现它过期」——并把「重画」写进发版清单。

---

### 1.4 【中】`28 REST + 6 MCP + 15 CLI` 会被读成接口数量

**图上文字（逐字）**

> `49`
> `公共契约检查项`
> `28 REST + 6 MCP + 15 CLI`

**读者会怎么误读**

三段并排的「N + N + N」是全卡最像「接口清单」的一行，读者会直接读成
「28 个 REST 接口、6 个 MCP 工具、15 个 CLI 命令」。但这三个数不是接口数：

| 卡片上的 | 读者会以为 | 实际是 | 报告/文档里的对应真值 |
|---|---|---|---|
| `28 REST` | 28 个 REST 端点 | `_rest_requests()` 的 **28 个 `check()` 调用点** | REST 端点 **23** 个（`phase1-execution-report.md:56`；`public-contracts.md` 里 23 行路径） |
| `6 MCP` | 6 个 MCP 工具 | `mcp_checks()` 的 **6 个检查点** | MCP 只读工具 **11** 个（`public-contracts.md:203-217`） |
| `15 CLI` | 15 个 CLI 命令 | `cli_checks()` 的 **15 个检查点** | CLI 命令 **13** 个（`phase1-execution-report.md:55`） |

三个数会和读者已知的三组真值全部对不上。更糟的是**卡内自相矛盾**：页脚写着
「MCP 只读工具 11 个」，中栏写着「6 MCP」——读者在同一张图上看到 MCP 既是 6 又是 11，
只能自行决定相信哪个。

真值出处：`docs/architecture/public-contracts.md:355-358`：「**检查项清单共 49 项：
28 REST + 6 MCP + 15 CLI**——即 `scripts/verify-public-contracts.py` 里 `check()` 调用点的
条数」。

**建议改法**

- 卡上把这一格改成「49 项契约检查」并把分项挪走或降级成「按传输面：REST 28 / MCP 6 / CLI 15」，
  让「检查项」和「接口」在视觉上分开；
- 或者把页脚的「MCP 只读工具 11 个」与中栏的「6 MCP」拆到不同视觉层级（见 1.13），
  并在图注里点明 6 ≠ 11 是「检查点 vs 工具」。

---

### 1.5 【中】`49 公共契约检查项` 没说这是静态条数

**图上文字（逐字）**

> `49`
> `公共契约检查项`

**读者会怎么误读**

「49 公共契约检查项」在读者眼里是**通过了 49 项检查**——尤其和其它三个「已达成」的
数字（93.3%、1632、11 个只读工具）并排时。但 `public-contracts.md:360` 明写：

> `**49 是静态条数，任何一次实跑都跑不满它。**`

也就是说，49 是清单的条数，不是任何一次运行的通过数。卡片给的是成就语气，
事实是清单长度。

**建议改法**

把标签从「公共契约检查项」改成能表达「清单」的措辞，例如「公共契约清单 49 项」，
或者在图注里加半句「静态清单条数，一次实跑未必跑满」。

---

### 1.6 【中】英文 README 上的卡片，标签与唯一的定位句全是中文

**图上文字（逐字）**

> `DexAtlas`
> `From APK to Evidence`
> `从 APK 到可核查的证据`
> `开源、证据优先的 Android 逆向工程与移动应用分析平台。`
> `93.3%` / `一方代码覆盖率` / `7135/7650 行`
> `1632` / `测试数` / `1485 快 + 147 集成`
> `49` / `公共契约检查项` / `28 REST + 6 MCP + 15 CLI`
> `MCP 只读工具 11 个 · Apache-2.0 · v1.0.0`

**读者会怎么误读**

卡片挂在**英文** `README.md:21` 上。英文读者打开仓库，第一眼看到的是：

- 标题行是英文 ✓
- 第二、三行是中文：「从 APK 到可核查的证据」+「开源、证据优先的 Android 逆向工程与
  移动应用分析平台。」
- 三个数字栏的**标签**全是中文：「一方代码覆盖率」「测试数」「公共契约检查项」
- 页脚除了 `Apache-2.0` 与 `v1.0.0`，全是中文：「MCP 只读工具 11 个」

**结果是：这张图上每一个数字的含义，都只对中文读者可读。** 英文读者能读到
`93.3%`、`1632`、`49`，但读不到它们**是什么**——只能猜「49 是接口数还是别的」，
正是 1.4 那个误读。

而英文定位句是有的：`README.md:7` 写着
`An open-source, evidence-first Android reverse engineering and mobile application analysis platform.`
——卡片没画它，改画了中文那行。

**建议改法**

- 英文版卡片把 `README.md:7` 的英文定位句放在第三行，中文定位句只留给中文版卡片；
- 或者出两版图（`.github/social-preview.png` 与 `.github/social-preview.zh-CN.png`），
  英文 README 挂英文版、中文 README 挂中文版——这一并解决 1.11。

---

### 1.7 【中】howto §4 那张出处表本身有两处错

**原文（逐字）**

- `docs/reports/social-preview-howto.md:49`
  > `| `从 APK 到可核查的证据` | `README.md:5` | 同一句 tagline 的中文表述 |`
- `docs/reports/social-preview-howto.md:55-56`
  > `| `49` / `公共契约检查项` | `docs/architecture/public-contracts.md:348` | 检查项清单的静态条数 |`
  > `| `28 REST + 6 MCP + 15 CLI`（合计 49 项） | `docs/architecture/public-contracts.md:348` | 同一行的分项 |`

**读者会怎么误读**

这张表的表头是全文档的承诺：「图上每一个字、每一个数是从哪个文件的哪一行读出来的」
（`social-preview-howto.md:3-4`）。两行兑不了现：

1. **`README.md:5` 并不含「从 APK 到可核查的证据」。** `README.md:5` 是英文行
   `**From APK to Evidence — Powered by a bounded AI agent.**`；`README.zh-CN.md:5`
   同样是英文（见 1.10）。全仓 grep「从 APK 到可核查的证据」只有两处命中：
   howto 自己的 `:49` 和 `:82`——**这句话只存在于那个不入库的绘图脚本里**。
   howto §5（`:81-82`）其实已经承认了（「图里唯一手写的字符串是中文定位句」），
   与 §4 的表头自相矛盾。
2. **`public-contracts.md:348` 是空行。** 那句
   `**检查项清单共 49 项：28 REST + 6 MCP + 15 CLI**` 在 **`:355`**。
   两行都指向 348。

这不是文风问题。howto 是这张图唯一的「出处地图」——读者想核实图上的字时只会看它；
它指错了地方，读者要么找不到出处，要么找到另一处而误以为图错了。

（顺带说明：上一轮 CI 契约判据红的就是这张表——`tests/test_public_contracts.py:766`
的 `MATERIALS_THAT_STATE_THE_COUNT` 要求任何写出分项的材料同时写出总数 49。
现在表里写了「（合计 49 项）」，这一条已经绿了。红的原因在别处，见 1.3：
**这张表不在 `check-doc-citations.py` 的 `DOCS` 列表里**，所以它的行号无人核对。）

**建议改法**

- 把 `:49` 那一行改成如实标注：「手写（绘图脚本内，全仓无此串）」，或者先给中文
  README 补一句中文 tagline（见 1.10），让这句话真有出处；
- 把 `:55-56` 的 `348` 改成 `355`；
- 把 howto 加入 `scripts/check-doc-citations.py` 的 `DOCS` 列表，或另立一条检查把
  §4 表里的每个数字与 `<!--fig:...-->`、与 `public-contracts.md` 对齐。

---

### 1.8 【中】解释徽章口径的那段注释是中文的，却挂在英文 README 上

**原文（逐字）**

- `README.md:15-17`
  > `> 徽章是**完整环境下**的一次测量（1612 个测试、0 跳过）。在没抓第三方样本的机器上，`
  > `> `pytest` 会显示 27 个 skip —— 那是缺 `scripts/fetch-fixtures.sh` 抓的两个样本，`
  > `> 不是失败。`

**读者会怎么误读**

这段注释是徽章的**限定语**：它告诉读者「这个数字来自完整环境，在没抓样本的机器上会
看到 27 个 skip，那不是失败」——这正是防误读的那句话。它是中文的，于是英文读者拿到的
徽章是**没有限定语的裸数字**。

同时，这段中文注释在版面上还把两行徽章隔开了：第一行 5 枚徽章 → 3 行中文注释 →
第二行 2 枚徽章（ruff / mypy）。读者看到的是三段而不是一组。

**建议改法**

英文 README 的这段注释改英文（内容照抄中文版的意思），中文版保留中文；徽章两行之间
不要插正文块。

---

### 1.9 【中】中文 README 说自己的徽章要「人工同步」——可脚本两份都写

**原文（逐字）**

- `README.zh-CN.md:15-16`
  > `> 徽章数字与[英文版 README](README.md)同源，取自同一份测量记录；英文版的徽章由`
  > `> `scripts/refresh-report-figures.py` 生成，中文版此处需人工同步。`

**读者/维护者会怎么误读**

这句话是过时的：`scripts/refresh-report-figures.py:101` 的
`README_PATHS = (REPO_ROOT / "README.md", REPO_ROOT / "README.zh-CN.md")`，
`:1440` 起对两份文件都跑 `apply_badges`——**中文徽章同样是脚本写的**。

危害不在读者那一侧，在维护者那一侧：它明说中文徽章要「人工同步」。人工同步就是手抄
数字，而本项目的规矩恰恰是「报告数字由 `scripts/refresh-report-figures.py` 生成，
禁止手改」（`docs/architecture/public-contracts.md:347`）。一个维护者照着这句注释
做，就会在下一次重测量后手抄一次中文徽章——那正是这个仓库花了几轮才消灭掉的漂移。

**建议改法**

把 `README.zh-CN.md:15-16` 改成：「徽章数字与英文版 README 同源，同样由
`scripts/refresh-report-figures.py` 生成，不要手改。」

---

### 1.10 【低】中英 tagline 不一致：英文有 `bounded`，中文没有

**原文（逐字）**

- `README.md:5` → `**From APK to Evidence — Powered by a bounded AI agent.**`
- `README.zh-CN.md:5` → `**From APK to Evidence — Powered by AI Agents.**`
- `docs/roadmap/ROADMAP.md:3` → `> **From APK to Evidence — Powered by AI Agents.**`

**读者会怎么误读**

`bounded` 是这个项目里防止读者把 agent 输出当结论的唯一那个词。中文版没有它，还把
单数写成了复数——中文读者读到的承诺比英文读者更强。
`docs/reports/english-reader-review.md:184`（第 12 条：吹过头）与
`docs/reports/github-repo-metadata-proposal.md:235`（§8 第 13 项：改中文那行）
都已经指出过，仍未改。

**建议改法**

`README.zh-CN.md:5` 与 `docs/roadmap/ROADMAP.md:3` 改成与英文版等强度
（如「Powered by a bounded AI agent.」/「由一个有边界的 AI agent 驱动。」）。

（卡片只画了 tagline 的前半句「From APK to Evidence」，所以卡片本身不涉及此条。）

---

### 1.11 【低】中文 README 没有这张图

**原文（逐字）**

- `docs/reports/social-preview-howto.md:40-41`
  > `本次提交把它放在英文 `README.md` 的徽章那一行之后、收尾的 `</div>` 之前。中文`
  > ``README.zh-CN.md` 同样可以加同一段；本次交付范围里只有英文 README，所以没动它。`

**读者会怎么误读**

中文读者的首屏没有这张图——而这张图上恰恰有全仓库唯一一处用中文写的项目定位句
（`README.zh-CN.md:7`，见 1.6）。**借方没借到，欠方反被引用**：卡片的定位句来自中文
README，中文 README 自己却没有卡片。

**建议改法**

中文 README 也挂一张卡（若采纳 1.6 的两版图方案，这里直接挂中文版）。

---

### 1.12 【低】徽章链接落点不对，首屏的数字无一处一键可达的出处

**原文（逐字）**

- `README.md:13` → `[![Coverage](https://img.shields.io/badge/coverage-93.3%25-brightgreen.svg)](pyproject.toml)`
- `README.md:12` → 本窗口基准树上的徽章是
  徽章上的测试数是 **1631**（本窗口基准树的值；主会话随后把它改成了 **1632**——
  徽章 URL 里那个数同理，这里不照抄，免得把旧值当成现状）

**读者会怎么误读**

读到一个数字、想知道它怎么来的，是「能不能信」这条问题的核心动作。而：

- Coverage 徽章点进去是 **`pyproject.toml`**——一个构建配置，不是覆盖率报告；
- Tests 徽章点进去是 **`tests/` 目录**；
- 唯一解释这些数字的报告在 `README.md:493`（「What the coverage figure was measured on」）
  ——距首屏 470 行；
- 卡片本身是 `<img>`，没有链接。

于是**首屏上没有一个数字能一键走到它的出处**。对一个以「结论必须指回字节」为纲的项目，
这是首屏最反直觉的一处。

**建议改法**

Coverage 徽章指向 `docs/reports/phase1-execution-report.md`（或它的 §1.2 锚点）；
Tests 徽章指向同一份报告的 §2.1（分层策略）；在卡片正上方加一行指向
`docs/reports/social-preview-howto.md` 的链接（「这张图上每个数的出处」）。

---

### 1.13 【低】图面版式：权重、可比性、页脚与成熟度信号

**图上文字（逐字）**

> `93.3%`　`1632`　`49`
> `一方代码覆盖率` / `测试数` / `公共契约检查项`
> `MCP 只读工具 11 个 · Apache-2.0 · v1.0.0`

**读者会怎么误读 / 版式问题**

1. **三个大数字同字号同字重**：`93.3%` 是比率，`1632`/`49` 是计数，三者被排成一行，
   视觉上暗示它们可比。读者会以为覆盖率 93.3% 和「1632 个测试」「49 项检查」是同一类
   指标（都是「越大越好」），而实际上它们量纲不同。
2. **主角不明确**：这个仓库最该被记住的是「93.3% 的一方代码覆盖率」，但它和另外两个
   数字一样大，读者不知道从哪个读起。
3. **页脚把最强的信任信号降级成脚注**：「MCP 只读工具 11 个」是全卡唯一一条
   「能力边界」级别的声明（只读、不写盘），却和 `Apache-2.0`、`v1.0.0` 并排在灰色小字里，
   看起来像版权页信息。
4. **没有成熟度信号**：页脚写着 `v1.0.0`，而 `README.md:46` 明写
   「**Status: early development — v1.0.0 released …; Phase 3's deliverables are released,
   but its exit criteria are not all met (M6, M8 and M10 are still open)**」。
   读者看图会得到「v1.0.0 = 稳定版」的印象，README 里的告警在图上没有任何对应物。

**建议改法**

- 让 `93.3%` 明显大于其它两个数字，或把它单独放左侧、其余两个缩小；
- 把「只读」这一层提到正文层级（例如在 tagline 下方加一行「只读分析：11 个 MCP 只读工具，
  不写盘」）；
- 页脚补一个成熟度词（如 `early development · v1.0.0`），或把 `v1.0.0` 后面加「早期开发中」。

---

### 1.14 【低】术语小出入：卡片「可核查」vs 中文 README「可核验」

**原文（逐字）**

- 图上 → `从 APK 到可核查的证据`
- `README.zh-CN.md:20` → `DexAtlas 把一个 APK 变成一幅完整、可核验的图景`

**读者会怎么误读**

两个近义词在首屏附近并存，读者会以为它们指两件事。`docs/glossary.md` 里两个词都没有
定义，`docs/glossary.md:44` 只定义了「一方代码覆盖率 / first-party coverage / 一方」。

**建议改法**

统一成一个词（建议「可核查」，与项目的核查/证据链语气一致），并在 `docs/glossary.md`
里给它一条定义。

---

## 2. 核对过且一致的清单

以下都逐条查过，**结论是一致**，列出来是为了让人知道查过哪些、依据是什么。

### 2.1 图本身

| 核对项 | 图上/文件里的值 | 依据 | 结论 |
|---|---|---|---|
| 尺寸 | 1280×640 | 读 PNG IHDR（实测） | 与 `social-preview-howto.md:11` 一致 |
| 体积 | 70,617 字节 | 文件字节数（实测） | 与 `social-preview-howto.md:12` 一致 |
| 文字完整性 | 全部 11 处 | 目视渲染图 | 无截断、无溢出、无中英错别字 |
| 版面 | 三栏 + 页脚 | 目视 | 无重叠、无错行 |

### 2.2 图上每一处文字的落盘出处（照 howto §4 逐条核）

| 图上的文字（逐字） | howto §4 登记的出处 | 实测出处 | 结论 |
|---|---|---|---|
| `DexAtlas` | `README.md:3` | `README.md:3` = `# DexAtlas` | ✅ 一致 |
| `From APK to Evidence` | `README.md:5` | `README.md:5` 前半句，逐字 | ✅ 一致 |
| `从 APK 到可核查的证据` | `README.md:5` | **全仓无此串** | ❌ 见 1.7 |
| `开源、证据优先的 Android 逆向工程与移动应用分析平台。` | `README.zh-CN.md:7` | `README.zh-CN.md:7` 逐字 | ✅ 一致 |
| `93.3%` | `phase1-execution-report.md:77` | `:77` `<!--fig:coverage.pct-->93.3%<!--/fig-->` | ✅ 一致 |
| `7135/7650 行` | `phase1-execution-report.md:77` | `:77` `coverage.covered` / `coverage.total` | ✅ 一致 |
| `1632` | `phase1-execution-report.md:76` | `:76` `<!--fig:tests.total-->1632<!--/fig-->` | ✅ 一致 |
| `1485 快 + 147 集成` | `phase1-execution-report.md:76` | `:76` `tests.fast` / `tests.slow` | ✅ 一致 |
| `49` / `公共契约检查项` | `public-contracts.md:348` | 实为 **`:355`** | ❌ 行号错，见 1.7 |
| `28 REST + 6 MCP + 15 CLI`（合计 49 项） | `public-contracts.md:348` | 实为 **`:355`** | ❌ 行号错，见 1.7 |
| `MCP 只读工具 11 个` | `public-contracts.md:207-217` | `:203` §3.1 表头，`:207-217` 恰 11 行工具 | ✅ 一致 |
| `Apache-2.0` | `pyproject.toml:10` | `pyproject.toml:10` = `license = { text = "Apache-2.0" }` | ✅ 一致 |
| `v1.0.0` | `src/dexatlas/__init__.py:11` | `src/dexatlas/__init__.py:11` = `__version__ = "1.0.0"`；`git tag` 有 `v1.0.0` | ✅ 一致 |

### 2.3 数字的自洽性

| 核对项 | 算式 | 结论 |
|---|---|---|
| 快 + 集成 = 总数 | 1485 + 147 = 1632 | ✅ 自洽，与 `phase1-execution-report.md:76` 相符 |
| 契约分项 = 总数 | 28 + 6 + 15 = 49 | ✅ 自洽，与 `public-contracts.md:355` 相符 |
| 契约总数有断言 | `tests/test_public_contracts.py:762` `CONTRACT_CHECK_TOTAL = 49`、`:759` `CONTRACT_CHECK_SECTIONS = {"_rest_requests": 28, "mcp_checks": 6, "cli_checks": 15}` | ✅ 有回归门禁 |
| MCP 工具数 | `public-contracts.md:203-217` 共 11 行；`:187-188` 明写「每个工具都带只读注解」 | ✅ 图上「只读」二字有出处 |
| 覆盖率口径 | 「一方代码覆盖率」= `docs/glossary.md:44` 定义的 first-party coverage | ✅ 术语有定义 |

### 2.4 三方数字对照（本次复核时点）

| 数字 | 图 | 徽章 | 正文 | 报告 fig 值 | 判定 |
|---|---|---|---|---|---|
| 测试总数 | `1632` | — | `README.md:15` 写 `1612` | `tests.total=1632` | ❌ 正文旧值（1.1） |
| 通过数 | — | `1631 passing` | — | `suite.passed=1631`（`:1100`） | ⚠️ 与图上的 1632 口径不同（1.2） |
| 失败数 | — | — | — | `suite.failed=1`（`:1099`） | ⚠️ 首屏无人提（1.2） |
| 覆盖率 | `93.3%` | `93.3%` | — | `coverage.pct=93.3%` | ✅ 一致 |
| 覆盖行 | `7135/7650 行` | — | — | `7135` / `7650` | ✅ 一致 |
| 契约检查 | `49` | — | — | `public-contracts.md:355` = 49 | ✅ 一致 |
| MCP 工具 | `11 个` | — | — | `public-contracts.md:203-217` = 11 | ✅ 一致 |
| 版本 | `v1.0.0` | — | `README.md:46` `v1.0.0 released` | `__init__.py:11` = 1.0.0 | ✅ 一致 |
| 许可证 | `Apache-2.0` | `license-Apache--2.0` | `README.md:626` 处的「Apache-2.0」链接指向仓库根的 `LICENSE` | `pyproject.toml:10` | ✅ 一致 |

### 2.5 两份 README 之间

| 核对项 | 结论 |
|---|---|
| 两个徽章的数字（`README.md:12-13` vs `README.zh-CN.md:12-13`） | ✅ 当前相同（`1631` / `93.3%`） |
| 中文 README 声明的徽章同步方式（`README.zh-CN.md:15-16`） | ❌ 它说「中文版此处需人工同步」，但脚本两份都写（`scripts/refresh-report-figures.py:101`、`:1440`）——见 1.9 |
| 中文 README 全文是否还有别的旧值 | ✅ 无 `1612` / `1620` 残留（`README.zh-CN.md:12` 是唯一一处测试数） |

---

## 3. 首屏结构：读者第一眼看到什么

**事实**（`README.md` 行号）：

| 行 | 内容 |
|---|---|
| 3 | `# DexAtlas` |
| 5 | tagline（英文） |
| 7 | 一句英文定位 |
| 9-13 | 5 枚徽章（CI / Python / License / Tests / Coverage） |
| 15-17 | 3 行**中文**注释（徽章的限定语，也是 `1612` 的载体） |
| 19-20 | 2 枚徽章（ruff / mypy） |
| 21 | 卡片（900px 宽） |
| 23-30 | 首段：这工具做什么 |
| 32-36 | 「一条结论必须能指回字节」那段 |
| 38-95 | 一大段 `> [!IMPORTANT]` 里程碑/状态块（约 58 行） |
| 97-108 | 演示 GIF 与披露 |
| 111 | `## Why DexAtlas?`（第一个二级标题） |
| 192 | `## Quick start` |

**判断**

- **「这是什么」有了**（`:7` 的英文定位 + `:23-30` 的首段 + 卡片的三行标题）。
- **「怎么用」离得很远**：`Quick start` 在第 192 行——首屏之外，且被那 58 行的里程碑
  说明块挡在前面。卡片本身是纯证据罗列，不含任何用法信息（一行安装命令都没有）。
  对第一次打开仓库的人，前十秒拿不到「怎么跑起来」。
- **「能不能信」有数字，但没有入口**：徽章与卡片给了 5 个数字，但首屏没有任何一处链接
  能把它们指回测量（见 1.12）；唯一的「测量在哪儿」在第 493 行。
- **被徽章与图挤掉的关键信息**：第 38-95 行的状态块（早期开发、Phase 3 退出标准未达成）
  排在一张满是「已完成数字」的卡片之后，读者容易在读到它之前就形成「这项目已经稳了」
  的印象（呼应 1.13 第 4 点）。

**建议**

不改动徽章与图的前提下，把 `:38-95` 的大块状态说明**上提或压缩**（比如把
「early development」那一句提到 `:38` 之前），并把「Quick start」的第一条命令提到卡片
附近，让首屏同时回答「是什么 / 怎么用 / 能不能信」。

---

## 4. 范围外、但相邻的发现（供主会话一并处理）

以下超出本次复核范围（README 首屏 + 卡片），但同属「对外数字」这一类问题，且都能在
本次核对中看见：

| # | 位置 | 事实 | 说明 |
|---|---|---|---|
| A | `docs/outreach/publish-review.md:22` | 「一方代码覆盖率 \| 93.3%（**7,117 / 7,631** 行）」 | 覆盖行数是上一轮的（现为 7135/7650）；该文件是「对外素材核对基准」表 |
| B | `docs/releases/v1.0.0.md:90-91`、`docs/how-to-verify.md:168` | 写「1632 passed + 0 xfailed + 0 skipped」 | 与记录块 `:1099-1100`（failed=1 / passed=1631）矛盾，见 1.2 |
| C | `docs/roadmap/ROADMAP.md:3` | tagline 仍是「Powered by AI Agents.」 | 见 1.10 |
| D | `docs/reports/social-preview-howto.md:66` | 绘图脚本不入库 | 见 1.3；建议随 1.3 的方案一并入库 |

---

## 5. 本次复核怎么做的（可重跑）

只读；未运行 `refresh-report-figures.py`、未联网、未重画图、未改动任何既有文件。

```bash
# 1. 图的尺寸与体积（PNG IHDR + 文件字节数）
python -c "
import struct
d=open('.github/social-preview.png','rb').read()
print(len(d), struct.unpack('>II', d[16:24]))
"

# 2. 图上每个数字在报告里的 fig 值
grep -n 'fig:' docs/reports/phase1-execution-report.md

# 3. 测量记录里的 suite 口径（passed / failed）
grep -n '"failed"\|"passed"\|"skipped"\|"xfailed"' docs/reports/phase1-execution-report.md

# 4. 首屏三个数的出处
grep -n '1612\|1631\|1632\|93\.3' README.md README.zh-CN.md

# 5. 图有没有自动化守护（应为空）
grep -rn 'social.preview\|social_preview' --include='*.py' --include='*.yml' \
  --include='*.yaml' --include='*.toml' --include='*.cfg' .

# 6. 引用检查器覆盖哪些文档（social-preview-howto.md 不在其中）
sed -n '85,100p' scripts/check-doc-citations.py

# 7. 契约条数的回归门禁
sed -n '755,790p' tests/test_public_contracts.py
```

图上文字的「逐字」核对是按 `docs/reports/social-preview-howto.md` §4 的表逐行做的：
把表里每行的落盘出处打开，看该行是否真的含有图上的那串字。13 行里 10 行命中，
2 行行号错（`public-contracts.md:348` → 实为 `:355`，两行受影响），1 行的字符串
在仓库里根本不存在（中文 tagline）。

---

## 6. 给主会话的一句话

图可以留，问题全在它旁边：**重测量一落定，卡片必须手工重画**（没有任何自动化会做这件事），
而重画之前得先把 `README.md:15`、`:21` 的 `1612`、howto §4 的两处错、`49` 的分项口径
这四件事定下来——否则重画出来的图仍然是上一轮的世界。
