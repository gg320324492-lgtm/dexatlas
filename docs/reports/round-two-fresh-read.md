# 本轮全部产出：第二遍通读（只读复核）

**日期**：2026-11-18 · **复核基准**：`ec52527`（`git rev-parse HEAD`；本 worktree 的
工作副本干净，与该提交一致）· **性质**：只读复核。

> **本文件是只读产物。** 本文只列发现与建议改法，**一个字都没改**——所有改动由主会话
> 统一做。本轮复核期间**没有改** `src/`、`tests/`、`scripts/`、`CHANGELOG.md`、
> `README.md`、`README.zh-CN.md`、`docs/status.md`、
> `docs/reports/phase1-execution-report.md`，**没有联网**，**没有跑**
> `scripts/refresh-report-figures.py`。
>
> **复核对象**：本轮合并进来的全部产出——
> `docs/reports/outreach-first-read.md`、`docs/reports/m10-invitation-readiness.md`、
> `docs/reports/m10-invitation-sender-checklist.md`、`docs/reports/m10-invitation-final.md`、
> `docs/reports/m10-review-record-template.md`、`docs/reports/case-studies-third-package.md`、
> `docs/reports/readme-image-consistency.md`、`docs/reports/v1.0.0-release-checklist.md`、
> `docs/glossary.md`、`docs/reports/glossary-pass.md`、`docs/reports/README.md`，
> 以及按首读终审改过的 `docs/outreach/` 四份素材、`docs/portfolio.md`、
> `docs/service-commitments.md`。
>
> **一句话结论**：**测量数字这一层大体是干净的**——落盘记录、徽章、两份 README、对外
> 素材、发版说明，彼此逐字一致，旧数没有漏网。**唯一的例外是本轮最后一个提交**
> （见第 0 条）。**其余问题全在「树」和「状态」两层**：
>
> 0. **本轮最后一个提交 `ec52527` 加了一个测试，于是刚落盘的测量又过期了**——
>    套件数差 1、源指纹从 `80bf8b0a` 变成 `7de84ff1`，而 `v1.0.0` tag 正指着那个提交
>    （严重）；
> 1. 有一份对外素材**已经超过平台门限**，而照着走就会把它发出去（严重）；
> 2. 术语对照表**166 处行号指针里有 46 处已经不再指向它声称的词**，而术语表自己写着
>    「改动多的时候整表重算一遍」，这条规则在它落盘后的 10 个提交里没有执行（严重）；
> 3. `v1.0.0` tag 又被重打了一次，于是**九处「tag 现在指向 X」的现在时句子当场变假**，
>    其中一处（CI 结论）会直接误导读者判断这个发布版本的 CI 是红是绿（严重）；
> 4. 四份新报告里，**首读终审的 13 条发现已经全部落地、README 核对的 2 条严重发现已经
>    修好**，但两份报告的正文仍把它们写成「现在还错着」——「各自都对」之后，
>    **报告本身成了唯一还在说旧话的东西**（严重）。
>
> 共 **21 条发现**（严重 8 / 中 11 / 低 4），另有一节「查过且没问题的部分」。

---

## 0. 怎么复核的（都可复算）

| 复核项 | 办法 | 结果 |
|---|---|---|
| 测量数字 | `docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` 与 `<!--report-figures:…-->` 记录块 | 1632 / 1485+147 / 7135÷7650 = 93.3% / passed 1632, failed 0 / 指纹 `sha256:80bf8b0a…` / 13 命令 / 23 端点 / 5 样例。**但树里实测是 1633 / 1486 / 指纹 `7de84ff1…`——见 S-1** |
| 旧数 | 全仓扫 `1620 1473 1425 1436 7117 7631 1611 1612 1631 93.2 1588 1441` 与全部 `sha256:` 指纹串 | 命中 153 处，逐处判「历史陈述」还是「现在时陈述」；现在时陈述的清单见 §1 |
| 树指代 | `git for-each-ref refs/tags/v1.0.0` / `git rev-parse "v1.0.0^{commit}"` 与逐句比对 | tag → `ec52527`（tag 对象 `a079a87`，taggerdate 2026-11-18 03:07:11 +0800） |
| 源指纹 | 按 `scripts/refresh-report-figures.py` 的配方，对 `00309bb / 28c34d6 / 0f1400b / ec52527` 四个提交重算 | 前三个是 `sha256:80bf8b0a…`，`ec52527` 变成 **`sha256:7de84ff1…`**（见 S-1） |
| 术语表行号 | 按 `docs/reports/glossary-pass.md:197` 自己声明的口径（词出现在所引行的**上下两行内**）逐条重算 | 166 处指针里 **46 处**不再命中（另 5 处是表内已注明「措辞不同」的有意指向） |
| 相对链接 | 15 份相关文档里 266 个相对链接逐个解析（另 244 个 token 的扫描见 §4.5） | **0 断链**、0 占位目标 |
| 门禁 | `check-doc-citations.py`、`check-version-claims.py --base auto`、`pytest tests/test_public_contracts.py` | 见 §4.7 与 §2 各条 |
| 字符门限 | 重跑 `docs/outreach/publish-review.md` §5 里那段**逐字**的脚本 | 9/14 行复现，1 行已越限 |

> **并发提示**：本轮复核期间，同一仓库有别的会话在并行推进（首屏与图收口、第三个案例证据包
> 入库、证据包刷新落盘）。本文的结论对应 **`ec52527`** 这一棵树；主会话合并时若那些会话已
> 落地，本文里与它们相关的条目可能已经自行消失——**合并前请先重核一遍本文 §1 的每一条**。

---

## 1. 严重（8 条）：会让客户理解错，或把没交付的说成交付了

### S-1｜本轮最后一个提交加了一个测试，于是刚落盘的测量又过期了——而 tag 正指着它

**仓库实况**（`ec52527`，本轮最后一个提交）：

```
$ git show ec52527 -- tests/test_docs.py | grep '^+def test_'
+def test_the_link_check_does_not_accept_a_placeholder(tmp_path: Path) -> None:

$ .venv/Scripts/python.exe -m pytest tests/ -m "not slow" --collect-only -q
1486/1633 tests collected (147 deselected)
```

而 `docs/reports/phase1-execution-report.md` 的记录块里写的仍是
`tests.total = 1632` / `tests.fast = 1485`。

**指纹也跟着变了**。按 `scripts/refresh-report-figures.py` 自己那段配方（覆盖 `src/`、
`tests/`、`pyproject.toml` 与测量脚本），对四个提交重算：

| 提交 | 源指纹 |
|---|---|
| `00309bb`（数字同步那一次） | `sha256:80bf8b0a…` ← **记录块里写的** |
| `28c34d6`（最终测量通过） | `sha256:80bf8b0a…` |
| `0f1400b`（按首读终审改对外材料） | `sha256:80bf8b0a…` |
| `ec52527`（修 CI 红的根因） | **`sha256:7de84ff1f5bfbe8c4507d48cf0015ca1e95737365ca3f3f30851411593efa394`** |

`tests/` 在指纹覆盖范围内，而脚本自己的注释写着：

> `The suite is part of what is hashed. The pass/skip split the report states is a`
> `property of the tree, so adding a test makes those numbers stale as surely as`
> `changing a line of the code does.`

**三条判据现在就是红的**（`.venv/Scripts/python.exe -m pytest tests/test_docs.py`）：

- `tests.total: the report says ['1632'], the code has 1633`；`tests.fast: … ['1485'] … 1486`
- `the coverage figures were measured on a different source tree`
  `（sha256:80bf8b0a… -> sha256:7de84ff1…）`
- `the report says 1632 passed … which is 1632 of the 1633 tests in the tree`

**为什么这件事最要紧**：`v1.0.0` tag 现在指向的正是 **`ec52527`**——就是那个改了指纹的
提交。而 `measurement` job（只在 tag 上跑）执行 `refresh-report-figures.py --check`，
问的正是「报告里的数字还描述这棵树吗」。**tag 上的那道门禁会红**，而 `ec52527` 的提交
说明写的恰恰是「修 CI 红的根因」。

（**覆盖率的分母不受影响**：7,650 行是 `src/dexatlas/` 自己的语句数，改 `tests/` 不动它。
红的是**测试数**与**指纹**这两项。）

**还有三处对外的陈述因此变成了假的**——它们把 `80bf8b0a` 说成**当前 / 发布树**的指纹：

- `docs/reports/v1.0.0-github-release-body.md:172`（发布正文逐字：
  `release tree: source fingerprint \`sha256:80bf8b0a…\`, suite 1632 passed /`）
- 同一文件的 `:266` / `:288` / `:298` / `:301`
- `docs/outreach/publish-review.md:335`（逐字：「测量落盘的报告（源指纹
  `sha256:80bf8b0a…`）——完整测量已重跑」）

**建议改法**：

1. **重跑一次完整测量**（`uv run --no-sync python scripts/refresh-report-figures.py`），
   让 `tests.total` 变 1633、`tests.fast` 变 1486、指纹变 `7de84ff1…`，四个由脚本写的
   文件一起落盘。**主会话本来就在跑最终重测量**——这一条它会顺带解决，但要确认它测的
   那棵树**包含 `ec52527`**（`ec52527` 之后 `tests/` 没有再被改）。
2. 落盘后把 `v1.0.0-github-release-body.md` 与 `publish-review.md` 里那几处指纹与套件数
   一起刷新。**GitHub Release 正文已经发布**：正文里的数要改，得改 GitHub 上那一份
   （本轮不联网，改不了）——或者在正文里注明它描述的是哪一次测量。
3. 如果 Release 正文来不及改，就按**发版清单 §3 步骤 8**（本轮刚补上的一条）把
   `v1.0.0` tag 再重打到重测量之后的那棵树上——**这一轮正好撞上那条路径存在的理由**。

---

### S-2｜`scope-backend-automation.md` 已经越过 5,000 字符门限，而核对表仍记着 ✅

**原文（`docs/outreach/publish-review.md:227`，逐字）：**

> `| 全文（附件） | \`scope-backend-automation.md\` | 4,950 | 4,941 | 5,000 | ✅ |`

**仓库实况**（重跑 `publish-review.md` §5 自己那段脚本，口径不变）：

```
### docs/outreach/scope-backend-automation.md 全文 raw=5022 plain=5013
```

门限是 5,000，口径是**取 raw 与 plain 的较大者判定**——两���都超了。

**为什么现在不对**：这一轮（`0f1400b`）按首读终审 F-1 把这段素材的命令列表改了
（`xref` → `xrefs`，并补了 `export` 写证据包、`analyze` 写报告的说明），字数涨过了门限；
`publish-review.md` 的字符表没有跟着重算，于是它**在素材已经超限之后仍说「✅」**。

**读者会怎么误读**：这张表是发信前的自检依据，也是「这份素材能直接发」的判据。照它走，
就是带着一份超长的简介去投 Upwork。

**建议改法**：

- 把 `:227` 改成 `5,022 | 5,013 | 5,000 | ❌ 超`，并按 `publish-review.md` §5.2 对
  `scope-ai-mcp.md` 的现成做法处理（给出可粘贴段，或压回 5,000 以内）；
- 把 `:365` 的「**14/14 一致**」改成实数（见 S-3）；
- 更要紧的一步：**这类素材的字数门限没有任何自动化**。`publish-review.md` §5 已经把口径
  写成了可执行脚本，却没有任何一道门禁跑它——建议把那段脚本挪成
  `scripts/` 下的一个检查，接进 `outward` 规则（`check-version-claims.py` 已经管着
  素材里的测试数与覆盖率，把字数一起管掉最省事）。

---

### S-3｜`publish-review.md` 的「§5 字符表复算 … 14/14 一致」现在是 9/14

**原文（`docs/outreach/publish-review.md:365`，逐字）：**

> `| §5 字符表复算（§5 的脚本，逐字抽取执行） | **14/14 一致** |`

**仓库实况**（逐字重跑 §5 的脚本）：

| 行 | 表里写的 | 现在的实数 |
|---|---|---|
| `:221` Short description | 1,410 / 1,404 | **1,484 / 1,478** |
| `:223` Deliverables shown in the repository | 1,455 / 1,437 | **1,534 / 1,512** |
| `:226` Links | 1,178 / 947 | **1,291 / 1,058** |
| `:227` 全文（附件）`scope-backend-automation.md` | 4,950 / 4,941 | **5,022 / 5,013** |
| `:228` §What I offer `scope-backend-automation.md` | 592 / 588 | **664 / 660** |
| `:231` Template 1 正文 | 2,185 / 2,174 | **2,257 / 2,246** |

其余 8 行仍复现。同一批数字还在 `:265`（Template 1 正文）与 `:320`（两封信 2,500 再核）
各出现一次，也要一起改。

**为什么现在不对**：`0f1400b` 改了 `project-brief.md`、`cover-letter-templates.md`、
`scope-backend-automation.md` 三份素材的字，字符表是**改素材之前**测的。

**读者会怎么误读**：这张表的用途是「把上面每个数字都能用它复算」。当 14 行里 6 行复算不
出来，这句话就成了空话——读者要么信表（信错），要么不信表（那这张表还有什么用）。

**建议改法**：整表重算，把 `:365` 改成 `9/14 一致，其余 6 行见上表`——或者更好：改完素材
就把 §5 的脚本跑一遍，让表始终是实数。

---

### S-4｜术语对照表 166 处行号指针里有 46 处已经不再指向它声称的词

**原文（`docs/glossary.md`「维护」一节，`:204-205`，逐字）：**

> `- **行号会漂**：本表的 `file:line` 指向改动后的当前树。`docs/` 下的文档一改，行号就动；`
> `  改动多的时候整表重算一遍，不要手改数字。`

**仓库实况**：`docs/glossary.md` 落在 `d711b83`（11-18 02:05）之后**一次都没改过**；
而它引用的 27 个文件里，有 **11 个在本轮又被改过**。按 `glossary-pass.md:197` 自己声明的
容差（词出现在所引行的上下两行内）重算：

| | 数 |
|---|---|
| 「出现位置」列里的 `file:line` 指针 | 166 |
| 已不再命中（词的真正位置在别处） | **46** |
| 表内已注明「措辞不同」的有意指向（不算缺陷） | 5 |
| 仍然命中 | 115 |

**为什么会这样**：这就是 `denominator-and-tree-pass.md:19-21` 自己在治的病——
「树动了，句子没跟着动」。只不过这一次的句子在术语表里。

**为什么这条最要紧**：这张表是全仓「读者读不懂就会猜错」的兜底，而它**逐条声明自己的行号
指向当前树**；一个读者按 `docs/glossary.md:38` 去 `docs/reports/release-process-dry-run.md:62`
找「源指纹」，会落在「## 1. 演练环境、边界与代价」这一行标题上。而
`scripts/check-doc-citations.py` 的 `DOCS` 名单里**没有 `docs/glossary.md`**——
`glossary-pass.md:198` 自己承认「这张表不在检查器的 `DOCS` 名单里……改动多时得自己重算——
这是这张表已知的软肋」。这条软肋在它落盘后的 10 个提交里被踩实了。

**三个可复算的例子**：

| 词 | 表里指的 | 现在那一行是 | 词的真正位置 |
|---|---|---|---|
| 源指纹 / 源码指纹（`docs/glossary.md:38`） | `docs/reports/release-process-dry-run.md:62` | `## 1. 演练环境、边界与代价` | **:80** |
| 独占测量（`docs/glossary.md:40`） | `docs/reports/v1.0.0-release-checklist.md:353` | 空行 | **:370**（`### N1 测量必须独占`） |
| 两棵树（`docs/glossary.md:59`） | `docs/reports/release-process-dry-run.md:257` | `\| C11 \| 「静态 49 条」加断言 \| …` | **:287** |

**建议改法**：

1. **整表重算**（不要手改数字——这句是术语表自己写的规矩）。逐条把 46 处的行号按词的**首次
   出现处**重新推导；推导不出来的那几条，从「出现位置」列里删掉，并在末栏注明「该词在本树
   上没有落点，靠本页兜底」。
2. 把 `docs/glossary.md` 加进 `scripts/check-doc-citations.py` 的 `DOCS` 名单，或另立一条
   只检查「指针落点是否含该词」的轻判据——**这张表的 166 个指针是手写的，没有门禁就一定
   会再漂一次**。

---

### S-5｜`v1.0.0` tag 又被重打了一次，九处「tag 现在指向 X」当场变假

**仓库实况**（本地 tag 引用，离线可查）：

```
$ git for-each-ref refs/tags/v1.0.0 --format='%(objecttype) %(objectname) %(*objectname) %(taggerdate)'
tag a079a876580e0f237bf1020d07978799eb72c9d8 ec5252773c89b9e9decce08b460ac2290269d6bc Wed Nov 18 03:07:11 2026 +0800
```

即：tag 现在指向 **`ec52527`**（= HEAD），taggerdate **2026-11-18 03:07:11 +0800**。

**现在时地断言 tag 指向、而现在已经不成立的九处**（逐条给原文）：

| # | 位置 | 原文（逐字） | 现在应为 |
|---|---|---|---|
| 1 | `docs/reports/outreach-first-read.md:18` | `> **基准树**：本 worktree \`HEAD\` = \`48a56b5\`（\`v1.0.0\` tag 指向 \`b71bf30\`，`<br>`> 二者相差 1 个提交）。` | HEAD 是 `ec52527`；tag 也指向 `ec52527`，**二者相差 0 个提交** |
| 2 | `docs/reports/outreach-first-read.md:301` | `\| 「tag \`v1.0.0\`」 \| tag 当前指向 \`b71bf30\`，\`0104ccb\` 只是它的祖先 \|` | tag 当前指向 `ec52527` |
| 3 | `docs/reports/outreach-first-read.md:315` | `> > \`v1.0.0\` tag 当前指向 \`b71bf30\`。本文件的核对结论仍锚在 \`0104ccb\`，` | 同上（这行是 F-7 的**建议改法**，已经被 `0f1400b` 写进 `publish-review.md`；建议改成不写死 hash） |
| 4 | `docs/reports/portfolio-readiness-2026-11-18.md:4` | `本文把它称为「基线树」；**该 tag 后来被重打，现在指向 \`b71bf30\`**——本文评的仍是 \`75976e0\`）。` | 「现在指向 `b71bf30`」已不成立 |
| 5 | `docs/reports/portfolio-readiness-2026-11-18.md:191` | `而 \`v1.0.0\` 现在指向 \`75976e0\`，两者相距 **23 个提交（19 个非合并提交）**。` | 与同文件 `:4` / `:355` **自相矛盾**（一个说 `b71bf30`，一个说 `75976e0`）；两条都要改 |
| 6 | `docs/reports/portfolio-readiness-2026-11-18.md:355` | `（**该 tag 后来被重打，现在指向 \`b71bf30\`**；本文评的仍是 \`75976e0\`）` | 同 #4 |
| 7 | `docs/reports/portfolio-readiness-2026-11-18.md:373` | `而 tag 现在指向 \`75976e0\`，相距 **23 个提交（19 个非合并提交）**——` | 同 #5 |
| 8 | `docs/reports/denominator-and-tree-pass.md:22` | `> 现在指向 \`b71bf30\`」的注记（见 §1 的 A29）。` | 同 #4 |
| 9 | `docs/reports/release-process-dry-run.md:12` | `**该 tag 后来被重打，现在指向 \`b71bf30\`**）` | 同 #4 |
| 10 | `docs/reports/v1.1.0-candidates.md:4` | `（= **调研当时** tag \`v1.0.0\` 指向的提交；**该 tag 后来被重打，现在指向 \`b71bf30\`**）。` | 同 #4 |

（另有 `docs/reports/denominator-and-tree-pass.md:100` 的 A29 行里两处同样的「现在指向
`b71bf30`」，与 #8 同源。）

**为什么现在不对**：这十处的写法都是「**写死一个 hash + 「现在指向」**」。而这一轮里 tag
被重打了一次——`denominator-and-tree-pass.md:19-21` 把这叫做「树动了，句子没跟着动」，
**它自己给出的药方（补一条「现在指向 b71bf30」的注记）就是同一种病**：药效只到下一次
重打为止。

**建议改法**（三选一，按代价从低到高）：

1. **不写 hash**：改成「tag 会被重打，要现查：`git rev-parse v1.0.0^{commit}`」——
   `docs/outreach/publish-review.md:11-12` 已经这么做了，**它是全仓唯一做对的地方**，
   其余各处照它抄；
2. 保留 hash 但加**时点**（「写就时 tag = `ec52527`；此后可能被重打」）；
3. 若第 1 条太啰嗦，至少把「现在指向」改成「截至 2026-11-18 03:07 指向」——
   **关键是不要让「现在」跟着一个会变的 hash 走**。

---

### S-6｜`v1.0.0-ci-run-record.md` 说「当前 tag 的 CI 结论是红的」——这个「当前」已经不是那个 tag 了

**原文（`docs/reports/v1.0.0-ci-run-record.md`，逐字）：**

> `:22` `**tag 的当前指向**（\`gh api repos/gg320324492-lgtm/dexatlas/git/ref/tags/v1.0.0\`）：`
> `:47` `> **当前 \`v1.0.0\` tag 指向的 commit \`75976e0c\`，它的 CI 结论是 \`failure\`**——`
> `:57` `\`v1.0.0\` 这个 ref 上一共触发过 **6 次** CI run，全部是 \`push\` 事件、工作流 \`CI\``
> `:58-59` `（\`gh run list --limit 100 --json ... --jq '[.[] | select(.headBranch=="v1.0.0")]'\`，`
> `返回 6 条；\`--limit 100\` 已覆盖该 ref 的全部历史）。`

**为什么现在不对**：这份记录的查询日是 2026-11-18（落盘于 `f9a4909`，01:58），那时 tag
确实指向 `75976e0`。此后 tag 又被重打了两次（`b71bf30`、`ec52527`），因此：

- 「**当前** tag 指向的 commit `75976e0c`」——现在 tag 指向 `ec52527`；
- 「这个 ref 上一共触发过 **6 次**」——现在至少 8 次，「`--limit 100` 已覆盖全部历史」
  这句承诺已经不成立；
- 「第 5 次（最后一次）的 tagger 时间 `2026-11-17T16:32:33Z`」（`:74`）——不再是最后一次。

**读者会怎么误读**：这份记录存在的**全部理由**是回答「这个发布版本的 CI 结论是什么」。
它给出的答案是「红的，4 个 job 红」，并逐 job 列了表。读者会照着这个结论判断 v1.0.0
不能发——而那 4 个红 job 属于 `75976e0` 这一次 run，不是现在这个 tag 的。

**建议改法**：

- 把 `:22` / `:47` 的「当前」改成带时点的写法：「**查询日 2026-11-18 01:58** 时 tag 指向
  `75976e0c`，它的 CI 结论是 `failure`」；
- `:57-59` 改成「查询日时该 ref 触发过 6 次；此后 tag 又被重打，需重新拉取补齐」；
- 若主会话手上还有 `gh` 的只读能力，补上后两次 run 的记录（**本轮不联网，无法代劳**）；
- 顺带把 `docs/reports/v1.0.0-release-checklist.md:248` 的「tag 在 Release 发布之后被重打过
  **5 次**」与实际次数对齐（现在至少 7 次）。

---

### S-7｜首读终审的 13 条发现已经全部落地，但报告正文仍把它们写成「现在还错着」

**原文（`docs/reports/outreach-first-read.md`，逐字）：**

> `:32-35` `**但「新数字」之外有三处会让真客户理解错的东西，其中一处是硬错**：`
> `> \`project-brief.md\` 列了**两个不存在的 CLI 命令**；四份素材把`
> `> 「一方代码覆盖率」写成了**没有限定词的 93.3% coverage**；而仓库里落盘的`
> `> 测量记录是 **1,631 passed / 1 failed**，不是 1,632 全绿。另外`
> `> \`docs/service-commitments.md\` 还在用**更早一轮**的 M6 数字，并把它写成`
> `> 「达到验收线」。`
> `:144-149` `**仓库实况：** \`docs/reports/phase1-execution-report.md\` 的记录块落盘是：`
> `\`\`\`json`
> `"suite": { "failed": 1, "passed": 1631, "skipped": 0, "xfailed": 0, "xpassed": 0 },`
> `"tests": { "fast": 1485, "slow": 147, "total": 1632 }`
> `\`\`\``
> `:573-583` `## 6. 给主会话的处置顺序`
> `1. **先等这轮重测量落盘**，再定 F-3 的措辞（F-3 是唯一一条会被测量改写的）。`
> `2. **F-1 与 F-2 可以立刻改**——它们不依赖测量结果。`
> `3. F-4 / F-5 / F-9 / F-11 / F-12 与测量结果无关，可一并改。`

**仓库实况**：`0f1400b` 已经把这 13 条对应的对外材料**全部改掉**（CLI 命令改成
`analyze / manifest / search / source / xrefs / export`；三处覆盖率补了「一方代码」与分母
说明；`portfolio.md` 的 CI job 数与千分位；`service-commitments.md` 的 49/60 = 81.7% 与
「未达三轮 ≥90%」；`publish-review.md` 的覆盖行数、tag 日期、核对基准、门禁记录），
而且**重测量也已经落盘**（`suite.passed = 1632, failed = 0`）。

**为什么现在不对**：这份报告是**只读产物**，它的写法是「发现 → 建议改法」，**没有状态栏**。
落地之后，报告就成了本轮唯一还在说「素材写错了」的东西。读者（读者是同事，不只是作者）
会照着 §6 的处置顺序去做已经做过的事。

**建议改法**（不改内容，只加状态）：

- 在报告开头加一行状态注：「**本报告的 13 条发现已于 `0f1400b` 全部落地**；下文按当时的
  树（`48a56b5`）记录，『原文（逐字）』引的是**改动前**的文本。」
- 把 F-3 那段 JSON 记录块明确标成「**当时（`48a56b5`）的记录块**」——它现在是
  `failed: 0, passed: 1632`；
- §6 的处置顺序改成「**已完成**」清单（或直接指向 `0f1400b` 的提交说明）。

---

### S-8｜README 首屏核对的 14 条里，严重的两条早已修好，报告却仍把 `1612` / `1631` 当现状

**原文（`docs/reports/readme-image-consistency.md`，逐字）：**

> `:16-19` `**问题不在图，在图旁边。** 首屏同时摆着**三个**测试数——徽章 \`1631 passing\`、图上 \`1632\`、`
> `正文散文 \`1612\`——其中 \`1612\` 是上一轮重测量之前的旧值，且已经被两份评审报告列为`
> `「必须改」而至今未改。`
> `:50-53` `- \`README.md:15\``
> `  > \`> 徽章是**完整环境下**的一次测量（1612 个测试、0 跳过）。在没抓第三方样本的机器上，\``
> `- \`README.md:21\` 的 img 标签，\`src\` 指向 \`.github/social-preview.png\`，\`alt\` 文本逐字是`
> `  > 「DexAtlas — From APK to Evidence: 93.3% first-party code coverage, 1612 tests, 49 public contract checks」`

**仓库实况**：`README.md:12` 徽章 `tests-1632 passing`；`README.md:15` 正文
「（1632 个测试、0 跳过）」；`README.md:21` alt 文本 `… 1632 tests …`；图上 1632。
**四处一致，1612 与 1631 都不在了。**

**为什么现在不对**：同一个提交 `0f1400b` 已经在正文里改了两处（`:82-84` 改成
「主会话随后把它改成了 **1632**」），**但 §0 的结论摘要与 §1.1/§1.2 的「原文（逐字）」没改**。
于是报告出现两副面孔：§0 说首屏有���个测试数，§1.2 说徽章是 1631——**而 §1.2 自己下面
已经写着「主会话随后把它改成了 1632」**。

更要紧的是：**「原文（逐字）」引的那两句在文件里已经不存在了**。读者按 `README.md:15`
去看，看到的是 1632，不是 1612；按 `README.md:21` 去看，alt 文本也是 1632。报告把一段
不存在的原文当证据摆着。

**建议改法**：

- §0 的结论摘要改成现在的样子：「首屏三个数现在一致（1632 / 1632 / 1632）；§1.1、§1.2
  两条严重发现**已由 `0f1400b` 关闭**」；
- §1.1 与 §1.2 的「原文（逐字）」改标为「**修复前的原文**」，并补一行「**修复**：
  `0f1400b` / `28c34d6`」；
- 剩下 12 条（§1.3–§1.14）**仍然开着**——我逐条核过，一条都没被这一轮动过（见 §4.8）。

---

## 2. 中（11 条）

### M-1｜索引的「二十一份」与 §6 的 24 行对不上

**原文（`docs/reports/README.md`，逐字）：**

> `:128` `这二十一份报告全部是**只读审计**产出：审计方不改被核的代码或文案，只记录发现与依据，`
> `:130` `**二十一份报告的数字都锚在各自的基线上**——基线之后的变动写在报告开头的声明里，读的时候`
> `:180` `- **凡带基线声明的报告，数字只在该基线上成立。** §6 的二十一份审计报告各自锚在自己的基线上，`
> `:182` `- **「只读审计」不等于「结论已落地」。** §6 的二十一份报告只记录发现，改动由主线执行；`

**仓库实况**：§1–§6 的行数是 7 + 5 + 6 + 10 + 8 + **24** = 60，摘要表 `:28` 也写着 24。

**为什么现在不对**：`0f1400b` 把摘要表里的「21」改成了「24」（并加了 4 行），**正文这四处
「二十一份」没跟着改**。同一份文件里同一个数说了两个。

**建议改法**：四处「二十一份」全改成「二十四份」。

---

### M-2｜索引 §6 的表格被一行空行截断，三行落到了表格外面

**原文（`docs/reports/README.md`，逐字结构）：**

```
:155  | [glossary-pass.md](glossary-pass.md) | … |
:156  （空行）
:157  | [outreach-first-read.md](outreach-first-read.md) | … |
:158  | [readme-image-consistency.md](readme-image-consistency.md) | … |
:159  | [case-studies-third-package.md](case-studies-third-package.md) | … |
:160  ## 7. 历史记录：不要当现状读
```

**为什么现在不对**：GitHub-flavored Markdown 里，**空行会终止表格**。所以 §6 的表在
`glossary-pass.md` 那一行就结束了，后三行没有表头也没有分隔行，会渲染成**三段带 `|` 的
普通文本**，不是表格；紧接着的 `## 7.` 前面又没有空行。

**读者会怎么误读**：页面上 §6 只显示 **21** 行，而摘要表写着 **24**——两处对不上，而且
看不出为什么。（这也正是 M-1 那个「二十一份」的来处：写摘要表的人数的是**渲染出来**的行。）

**建议改法**：删掉 `:156` 的空行，在 `:160` 的 `## 7.` 之前补一个空行。

---

### M-3｜首读终审自己写的发现条数与正文对不上：说 11 条，正文有 13 条

**原文（`docs/reports/outreach-first-read.md:39`，逐字）：**

> `共 **11 条发现**（3 条高 / 5 条中 / 3 条低），外加一节「确认过且没问题的部分」。`

**仓库实况**：正文有 **13** 条 —— §1 高后果 **3** 条（F-1…F-3）、§2 中后果 **7** 条
（F-4…F-10）、§3 低后果 **3** 条（F-11…F-13）。

**为什么现在不对**：11 = 3+5+3 算术自洽，但**正文的中后果是 7 条不是 5 条**。这个数从
落盘起就是错的（`2954644` 的原版就写「11 条」），而 `0f1400b` 的提交说明写的是
「按首读终审的 **13 条**发现把对外材料改对」——**提交说明数对了，报告没改**。

`docs/reports/README.md:157` 抄了同一句：「结论：**11 条**（3 高 / 5 中 / 3 低）」。

**建议改法**：报告 `:39` 与索引 `:157` 都改成「**13 条（3 高 / 7 中 / 3 低）**」。

---

### M-4｜索引说「三个不存在的 CLI 命令」，报告自己说「两个」

**原文：**

> `docs/reports/outreach-first-read.md:33` `> \`project-brief.md\` 列了**两个不存在的 CLI 命令**；四份素材把`
> `docs/reports/outreach-first-read.md:45` `### F-1｜\`project-brief.md\` 列了两个不存在的 CLI 命令`
> `docs/reports/README.md:157` `…其中包括素材列了三个**不存在的 CLI 命令**、覆盖率丢了「一方代码」这个限定词。`

**仓库实况**：F-1 的表里三个 ❌ —— `xref` → **`xrefs`**（少一个 s）、`evidence` **不存在**、
`report` **不存在**。报告把它读成「两个不存在 + 一个拼错」；索引与 `0f1400b` 的提交说明
读成「三个」。

**为什么现在不对**：两个数说的是同一件事，读者去数就是三个错。严格讲报告的读法更精确
（`xref` 改成 `xrefs` 就是 `xrefs`），但**两份文件写着不同的数**，这是本轮「合起来」才
出现的问题——索引那一句是 `0f1400b` 新写的。

**建议改法**：统一成一句不含歧义的话：「素材列的七个命令里有**三个对不上**：`xref` 少一个
s（真名 `xrefs`），`evidence` 与 `report` **根本不是命令**（证据包是 `export`，报告是
`analyze` 的产物）」。

---

### M-5｜演练报告说「这条断言现在是红的」——它现在是绿的

**原文（`docs/reports/release-process-dry-run.md:257`，逐字）：**

> `| C11 | 「静态 49 条」加断言 | ✅ **已落地**，且**这条断言现在是红的** |`

**仓库实况**：

```
$ .venv/Scripts/python.exe -m pytest tests/test_public_contracts.py -q
30 passed in 6.36s
```

**为什么现在不对**（时间线可查）：

| 时刻 | 事件 | 断言状态 |
|---|---|---|
| 11-17 22:03 | `fad19cd` 加入「静态 49 条」断言 | 红 |
| 11-18 00:48 | `079e8b0` 写下演练报告这一行 | 红（当时**确实**是红的） |
| 11-18 00:53 | `61c8046`「修 CI 红点：分项旁补总数」 | **绿** |
| 11-18 之后 | 演练报告再没改过这一行 | 绿 |

**建议改法**：改成「✅ **已落地**（断言绿；它曾经红过，`61c8046` 修的）」。

---

### M-6｜`publish-review.md` 记的两道门禁结果已经过期

**原文（`docs/outreach/publish-review.md`，逐字）：**

> `:362` `| \`uv run --no-sync pytest tests/test_docs.py\` | **64/64 通过，0 跳过**（2026-11-18 复核；原文一处写 60、一处脚注写 62，两数自相矛盾，现按实测） |`
> `:364` `| \`uv run --no-sync python scripts/check-version-claims.py --base auto\` | **exit 1**，findings 3 条：2 条历史遗留（\`docs/releases/v0.2.0.md\`、\`CHANGELOG.md\` 里的旧版本覆盖率）+ 1 条 \`docs/reports/outreach-recheck.md\` 自己的过期事实。**本轮改动没有新增任何 finding**：改动前先跑一遍、再改动后跑一遍，两次输出逐字相同（都是 exit 1、同 3 条） |`

**仓库实况**：

```
$ .venv/Scripts/python.exe scripts/check-version-claims.py --base auto   → exit 0
findings: 2 (2 already in 0f1400bc)
  docs/releases/v0.2.0.md:326  release-coverage …
  CHANGELOG.md:1072  release-coverage …
Every version claim matches the repository.

$ .venv/Scripts/python.exe -m pytest tests/test_docs.py -q
3 failed, 62 passed in 35.61s      ← 收集 65 个用例
```

**为什么现在不对**：第 3 条 finding（`outreach-recheck.md`）已经不存在了；`exit 1` 变成
`exit 0`。`:369-385` 的脚注还在解释「那第 3 条 finding …… 它让这道门禁现在就是红的」——
**解释的是一件已经不存在的事**。而 `:362` 的 64 也变成了 65。

（`pytest tests/test_docs.py` 现在 **3 failed** 是因为主会话正在跑最终重测量、四个由测量
脚本写的文件还没落定——**这不是本轮产出的缺陷**，但 `:362` 那句「0 跳过」在发信前要重测。）

**建议改法**：`:364` 改成「**exit 0**，findings 2 条（均为历史遗留：`docs/releases/v0.2.0.md`、
`CHANGELOG.md` 里的旧版本覆盖率）」；删掉或改写 `:369-385` 那段脚注；`:362` 的用例数在
发信前重测一次再填。

---

### M-7｜`glossary-pass.md` 自己的数字已经过期

**原文（`docs/reports/glossary-pass.md`，逐字）：**

> `:29` `\`docs/\` 下 127 份 markdown（\`check-version-claims.py\` 本轮读到的份数）。其中**含中文**、`
> `:181` `改完**可复算**：§1–§6 点名的 53 个文件与目录里的 53 个 \`.md\` 一一对应，无重复、无遗漏`
> `:197` `| 术语表自检 | 表里 **143 处 \`file:line\` 引用逐条解析**：文件存在、行号在范围内，0 处失效；另有一次术语邻近核对，确认每个词确实出现在所引的那一行或其上下两行内（少数"对不上"的是英文原文、复合词与 \`<!--fig:…-->\` 标记，人工逐条看过） |`

**仓库实况**：

| 报告写的 | 现在 |
|---|---|
| 127 份 markdown | 125 份（`check-version-claims.py` 现在报 `documents read: 136`） |
| 53 个文件 ↔ 53 个 `.md` | **60 ↔ 60**（索引已改到 60，这份没跟上） |
| 143 处 `file:line`，0 处失效 | **166 处**，**46 处已不再命中**（见 S-4） |
| §2 表里 8 行的行数 | 全部过期（`release-process-dry-run.md` 614→**666**、`portfolio-readiness-2026-11-18.md` 484→**525**、`v1.1.0-candidates.md` 735→**754**、`v1.0.0-release-checklist.md` 730→**759**、`docs/reports/README.md` 184→**194**、`how-to-verify.md` 480→**485**、`how-to-verify.zh-CN.md` 451→**456**、`m10-selfcheck.md` 「—」→**136**） |

**为什么现在不对**：这份记录是**术语表那一份的做法记录**，它的数字描述的是
`d711b83` 那一刻的树。它没有基准声明（不像别的报告写「本文引用的行号指基线 X」），
所以读者只能把它当现状读——而它已经不是了。

**建议改法**：给这份报告加一句基准声明（「本文记录的是 `d711b83` 那一刻的树」），并把
`:197` 那行的自检结果改成 S-4 的实测数；或者按 S-4 重算完术语表之后，把这一行改成新的
自检数。

---

### M-8｜项目自己的指令文件还写着「six jobs (seven parallel runs)」

**原文（三处逐字相同）：**

> `CLAUDE.md:62` `CI runs six jobs (seven parallel runs): lint/format/mypy, tests on Python 3.12 (every backend),`
> `AGENTS.md:62` `CI runs six jobs (seven parallel runs): lint/format/mypy, tests on Python 3.12 (every backend),`
> `docs/HANDOVER.md:148` `CI runs six jobs (seven parallel runs): lint/format/mypy, tests on Python 3.12 (every backend),`

**仓库实况**（`.github/workflows/ci.yml`）：**9 个 job 定义** —— `lint`(:38)、
`test`(:119，矩阵 3.12 / 3.13)、`test-partial-backends`(:198)、`m3-comparison`(:270)、
`docker`(:406)、`security`(:416)、`contracts`(:442)、`m10-selfcheck`(:471)、
`measurement`(:493，只在 tag 上跑)。tag 推送时 **10 次并行运行**；push / PR 时 **8 次**
（`m10-selfcheck` 没有 tag 门禁，只有 `measurement` 有）。

**为什么现在不对**：这一轮把 `docs/portfolio.md` 与四份对外素材的 CI 说法改对了，
**却漏了项目自己的指令文件与交接文档**——而 `CLAUDE.md` / `AGENTS.md` 是每个 agent 会
读的那一份。漏掉的三项正是 `contracts`、`m10-selfcheck`、`measurement`。

**建议改法**：三处改成

> `CI runs nine jobs (ten parallel runs on a tag push, eight on a push or PR): lint/format/mypy, tests on Python 3.12 (every backend),`

并把 `contracts`、`m10-selfcheck`、`measurement` 列进括号里的清单。
**注意 `CLAUDE.md` 与 `AGENTS.md` 必须逐字相同**（`tests/test_docs.py` 有一道判据守着
「这两个文件是同一个文件」），改一处就要改另一处。

---

### M-9｜`portfolio.md` 把「10 次并行运行」说成了「ten CI jobs」

**原文（`docs/portfolio.md:68`，逐字）：**

> `  93.3% coverage on the first-party code, and ten CI jobs: lint and format;`

**仓库实况**：`docs/status.md:26` 写的是「**9 个 workflow job、10 次并行运行**（`test` 是
3.12/3.13 矩阵）」；`docs/reports/v1.0.0-release-checklist.md:60` 写的是「最终 commit 上 CI
**9 个 job / 10 次并行运行**」。**三份文件，两个说法。**

**为什么现在不对**：`0f1400b` 把 portfolio 的「six CI jobs」改成了「ten CI jobs」，
把**运行次数**写成了**job 数**。清单里列的那十项里，`test` 出现两次（3.12 与 3.13），
所以是 9 个 job、10 次运行。

**建议改法**：改成「nine CI jobs — ten parallel runs on a tag push (the `test` job runs
twice, on 3.12 and 3.13)」，与 `docs/status.md` 与发版清单同口径。

---

### M-10｜这一轮新引入的两个说法没进术语表：「判定格」与「静态条数 / 实跑条数」

**为什么现在不对**：本轮引入了两对同名不同义的数，而 `docs/glossary.md` 的
「分母」条目（`:43`）只记了「两义」：

1. **判定表的「行」与「格」**。`docs/reports/denominator-and-tree-pass.md` 的 A1 / A2 与
   `docs/reports/english-reader-review-2.md` §3.2 这一轮引入第三种分母：一行判定表里
   有一行带两个判定，所以是 **75 行 / 76 格**；两套分桶（50+16+1+6+2 = 75 行；
   50+17+7+2 = 76 格）。术语表 `docs/glossary.md:43` 写的是
   「⚠ 本仓库里"分母"有两义——**测试数** 与 **代码总行数**」——**漏了这第三种**。
2. **契约的「静态条数」与「实跑条数」**。静态是 **49 = 28 REST + 6 MCP + 15 CLI**，
   实跑是 47 / 48（看后端在不在）。这一轮反复强调这对区别：
   `docs/reports/v1.0.0-release-checklist.md` 的 B4、§8.1 L2，
   `docs/reports/readme-image-consistency.md` 的 §1.4 / §1.5
   （「`28 REST + 6 MCP + 15 CLI` 会被读成接口数量」「`49 公共契约检查项` 没说这是静态条数」）。
   术语表的 `契约活检`（`:54`）只解释了脚本是什么，**没有分开这两个数**。

**建议改法**：

- `docs/glossary.md:43` 的「分母」条目补上第三义：「判定表的**行**与**格**（75 行 vs 76 格）」，
  或单列一条「判定格」；
- 单列一条「静态条数 / 实跑条数」，指向 `docs/architecture/public-contracts.md:355`（静态 49）
  与 `:368-369`（实跑 47 / 48），并写明「引用静态数时必须连分项一起写」。

---

### M-11｜索引 §7 说「点名的文件都已经计在 §1–§5 里面了」，但有一份在 §6

**原文（`docs/reports/README.md:164`，逐字）：**

> `注意这一节是**横切视角**，不是新的一组：下面点名的文件都已经计在 §1–§5 里面了，`

**仓库实况**：§7 点名的 8 份里，`m10-reader-walkthrough.md` 在 **§6**（索引 `:142`），
不在 §1–§5。

**建议改法**：把「§1–§5」改成「§1–§6」。

---

## 3. 低（4 条）

### L-1｜`docs/status.md:129` 是空行，两处引用指向它

`docs/reports/m10-invitation-readiness.md:131` 与 `docs/reports/outreach-first-read.md:330`
都引 `docs/status.md:129` 去取「`v1.0.0`（tag 2026-11-17）已发布／独立验收尚未开始」那一句，
而那一行现在是**空行**，正文在 **`:132`**。

**建议改法**：两处改指 `:132`。**注意 `docs/status.md` 由测量脚本写**，主会话重测量落盘后
行号可能再动一次——改前重查。

---

### L-2｜首读终审里若干「原文（逐字）」的行号已挪，且引的是改动前的文本

`docs/reports/outreach-first-read.md` 声明了基准树 `48a56b5`（`:18`），行号漂移是设计内的。
但这些引用引的是**被本轮改掉的**文本，读者按行号去会找不到原句：

| 引用 | 说的内容 | 现在在 |
|---|---|---|
| `:47` `docs/outreach/project-brief.md:68-70` | 「Two transports over one core…」 | **:69-72**，措辞已改 |
| `:324` `docs/outreach/project-brief.md:109-110` | 「证据包里是 the report + a manifest」 | **:111-112** |
| `:409` `docs/outreach/cover-letter-templates.md:77` | 「1,632 automated tests at 93.3% coverage」 | **:79-80** |
| `:393` `docs/outreach/publish-review.md:360` / `:362` | 两道门禁的行 | **:360** 现在是表头、`:362` 是 test_docs 那一行 |

**建议改法**：把这些引用改成「**改动前**：`docs/outreach/project-brief.md:69-72`（现）」这种双向写法，
或者统一改成「见 `project-brief.md` 的 §Honest limitations」（按内容定位，不按行号）——
后者正是发版清单 B2 的规矩。

---

### L-3｜索引里那个页内锚点对不上标题

**原文（`docs/reports/README.md:28`，逐字）：**

> `| [§6 本轮审计与走查](#6-本轮审计与走查2026-11-17–18) | 24 | 发版前最后一轮找出来的问题，以及怎么处置的 |`

**标题（`:124`）：** `## 6. 本轮审计与走查（2026-11-17–18）`

GitHub 的 slugger 会**删掉**标题里的全角括号与 en dash（en dash 被删，不会变成连字符），
所以标题的 slug 是 `6-本轮审计与走查2026-11-1718`；而链接里留着 en dash，**点不动**。

**为什么现在不对**：这一行是 `0f1400b` 改写的（21 → 24），锚点被原样带了过来；旧行的锚点
`#6-本轮审计与走查2026-11-17` 同样对不上。**仓库里没有任何一道门禁检查页内锚点**
（`check-doc-citations.py` 与 `tests/test_docs.py` 都只检查文件路径）。

**建议改法**：锚点改成 `#6-本轮审计与走查2026-11-1718`；顺带把 §1 的锚点也核一遍
（`#1-执行评审与阶段结论phase-12` 与标题 `## 1. 执行、评审与阶段结论（Phase 1–2）` 同样
要去掉全角括号与 en dash）。

---

### L-4｜本文件进 `docs/reports/` 之后，索引的份数从 60 变 61

`docs/reports/README.md` 三处写着 60：`:3`（「**六十份报告**」）、`:29`（「| 合计 | 60 |」）、
`:42`（「§1–§6 点名的 60 个文件与目录里的 60 个 `.md` 一一对应，无重复、无遗漏。」）。

本文件加进来之后，目录里就是 **61** 份，索引必须跟着改：**`:3` / `:29` / `:42` 的 60 改成
61**，并在 §6 的表里补一行指向本文。

（**本次复核没有做这件事**——本文是只读产物，任务书要求「只新增这一个文件，不改任何既有
文件」。索引的更新留给主会话。）

---

## 4. 查过且没问题的部分

### 4.1 测量数字：全部是当前值，旧数没有漏网

`docs/reports/phase1-execution-report.md` 的落盘记录块（`<!--report-figures:…-->`）：

| 字段 | 值 |
|---|---|
| `tests` | `total 1632 / fast 1485 / slow 147`（1485+147 = 1632 ✓） |
| `suite` | `passed 1632 / failed 0 / skipped 0 / xfailed 0 / xpassed 0` |
| `coverage` | `covered 7135 / total 7650` → 93.3% ✓（7135+515 = 7650） |
| `source_fingerprint` | `sha256:80bf8b0af31312d996cd271c80bcfdc0fb4f51724844e39fc4b6cd301df7e227` |
| `code` | `api_endpoints 23 / cli_commands 13 / sample_apks 5` |

`<!--fig:…-->` 标记全部与记录块一致；`README.md:12-13`（徽章 `1632 passing` / `93.3%`）、
`README.md:15`（正文 1632）、`README.md:21`（alt 1632）、`README.zh-CN.md:12-13`、
`docs/status.md:23-24`、`docs/releases/v1.0.0.md:90-94`、
`docs/reports/v1.0.0-github-release-body.md`、`docs/outreach/` 四份素材、
`docs/portfolio.md:67-68` —— 全部对得上。

> ⚠️ **一处例外**：`ec52527` 往 `tests/` 里加了一个测试，于是记录块里的 **`tests.total`
> （1632 → 树里是 1633）、`tests.fast`（1485 → 1486）与 `source_fingerprint`
> （`80bf8b0a` → `7de84ff1`）** 三项已经过期。见 **S-1**。覆盖率的分母不受影响
> （7,650 行是 `src/dexatlas/` 自己的语句数）。

**旧数只剩在两类地方**，都不该报：① 带基线 / 带日期的历史陈述（`CHANGELOG.md:114`、
`docs/reports/coverage-guard-audit.md`、`docs/reports/m10-number-traceability.md` 的对照列、
`docs/reports/release-process-dry-run.md:212` 等）；② 报告里作为**发现对象**引用的原文
（`docs/reports/outreach-first-read.md:147`、`docs/reports/readme-image-consistency.md:53` 等）——
这些属于「记录了当时」，见 S-7 / S-8。

### 4.2 四份新报告之间的结论没有互相矛盾

逐条对过：`outreach-first-read.md`（11 条 / 13 条）、`m10-invitation-readiness.md`、
`case-studies-third-package.md`、`readme-image-consistency.md` 对**同一件事**的判断彼此一致：

- 「三次分析」：`case-studies-third-package.md` 补出第三次分析，
  `case-studies-run-correspondence.md` 记的是「三个包只覆盖两次分析」——**是同一件事的
  前后两步**，不是矛盾（前者 §4.3 的九处待改清单正是后者的下一步）；
- 「两个不存在的 CLI 命令」：只有 M-4 那处数法分歧；
- 「首屏三个数」：只有 S-8 那处已作废。

`case-studies-third-package.md` 的 §4.1（只换第 3 篇）与 §4.2（连 demo / obfuscated 一起换）
在 run id 与文件数上也自洽；§4.1 的「三个包 ↔ 三个互不相同的 run」与紧跟着的「但第 1 篇和
第 3 篇仍是同一份 APK 的两次分析」不冲突——**那是两个不同的量**（run 数 vs APK 数）。

### 4.3 `case-studies-third-package.md` 的 `file:line` 引用逐条对得上它声明的基准

它明确声明「本文引用的 `file:line` 一律指**基线 `48a56b5`**」（`:22-23`）。核过：
`src/dexatlas/core/models.py:806-809`（`apk_{sha256[:16]}` ✓）、
`src/dexatlas/core/runs.py:42-49`（run id 与字节无关 ✓）、
`src/dexatlas/api/app.py:380-386`、`src/dexatlas/reports/evidence_package.py:102`、
`src/dexatlas/cli/main.py:882`、`docs/case-studies/demo-app-walkthrough.md:293-297`
——**全部命中**。这是本轮四份报告里出处纪律最好的一份。

### 4.4 M10 材料内部自洽

- `m10-invitation-final.md`：正文只留**一处**内容占位（`:79` 的「commit 【待填…】」），
  抬头三项与落款签名是「发出时填写」，与 `m10-invitation-readiness.md` §1 第 4 步的
  grep 判据（`［.*——发出时填写］` 无命中）一一对应；
- `m10-invitation-sender-checklist.md` 的示例输出**明确标了「本清单编写时（2026年11月18日）」**
  （`:97`）与「本清单编写环境不联网，这一组**未实测**」（`:123`）——**没有把示例冒充现状**，
  这是本轮文档纪律最好的一处（与 S-5 里那些「现在指向」形成鲜明对照）；
- `scripts/m10_selfcheck.py` 实跑：**通过 43，失败 0，需人工 40**（exit 0），与
  `docs/reports/m10-selfcheck.md:25` 的「83 项分类结果（自动化 43 + 留人工 40）」对得上；
- `m10-invitation-readiness.md` §2 C 表列的三条「记录在案但未改」我逐条核过：
  `docs/reports/next-engagements.md:398` 仍写「自查脚本 40/40」与「填 7 处空格」，
  `docs/reports/v1.0.0-release-runbook.md:389` 仍写「作者侧自检 40/40（`bb50635`）」——
  **C-1 与 C-1b 的陈述仍然成立，仍未改**（这是诚实的「还开着」，不是过期陈述）。

### 4.5 相对链接：266 个逐个解析，0 断链

本轮 15 份相关文档（`docs/reports/` 下的八份 + `docs/glossary.md` + `docs/outreach/` 五份 +
`docs/portfolio.md` + `docs/service-commitments.md`）里的 **266 个相对链接**全部解析成功，
没有断链、没有空目标、没有 `...` / TODO / example.com 之类的占位。
M10 那三份（`m10-invitation-final.md`、`m10-invitation-sender-checklist.md`、
`m10-review-record-template.md`）另跑了一遍 244 个链接 token 的扫描，同样 0 断链。

（`0f1400b` 修掉的那个占位链接——原来 run `44126968629` 后面跟的是一串三个点——已经换成
真链接，`docs/reports/outreach-first-read.md:199` 现在是
`https://github.com/gg320324492-lgtm/dexatlas/actions/runs/44126968629` ✓。）

### 4.6 对外素材这一轮改到位了

- **CLI 命令**：`docs/outreach/project-brief.md:69-72` 现在写
  `dexatlas analyze / manifest / search / source / xrefs / export`。逐个对
  `src/dexatlas/cli/main.py` 的 13 个 `@app.command()`（`version backends analyze projects
  classes methods source resources resrefs search export manifest xrefs`）——**七个全对**，
  `evidence` 与 `report` 确实不是命令 ✓；
- **覆盖率限定词**：三处都补了「93.3% coverage of the project's own code (the denominator
  is lines of code, not tests)」，堵住了「1,632 个测试覆盖了 93.3%」这个相对读法 ✓；
- **`portfolio.md`**：CI 从「six」改成十项并补上千分位 ✓（但见 M-9 的措辞）；
- **`service-commitments.md`**：现在写「三轮完整复测已跑完，合计 49/60 = 81.7%（逐轮
  15/16/18）……三轮合计线（≥90%）**没过**；……**方案 3「现状披露」是最终定稿路径**」，
  且明写「不声称「达到三轮验收线」」✓——与 `docs/benchmarks/` 的实测一致；
- **`publish-review.md`** 的核对基准改成「**要现查：`git rev-parse v1.0.0^{commit}`，别抄本
  文件里的旧值**」✓——**这是全仓唯一做对 tag 指代的地方**。

### 4.7 门禁的状态与它们的盲区

| 门禁 | 实跑结果 | 说明 |
|---|---|---|
| `scripts/check-doc-citations.py` | exit 0；`citations: 286` / `unresolved 0` / `drifted 0` | **它的 `DOCS` 名单只有 12 份文档**（`analysis-provenance.md`、`architecture/public-contracts.md`、`phase1-execution-report.md`、`benchmarks/large-apk.md`、`docs/releases/*.md`、`docs/reports/*-github-release-body.md`）。**本轮这批（`docs/glossary.md` 与四份新报告）一份都不在名单里**——它的 286/0/0 对这批文档不构成任何证据 |
| `scripts/check-version-claims.py --base auto` | exit 0；findings 2（均为历史遗留） | 见 M-6 |
| `pytest tests/test_public_contracts.py` | 30 passed | 见 M-5 |
| `pytest tests/test_docs.py` | **3 failed** / 62 passed | 三个失败**都是 `ec52527` 造成的**（套件数差 1 + 指纹变了），不是「重测量在跑」的临时状态——见 **S-1**。失败的是 `test_execution_report_numbers_match_the_code`、`test_execution_report_coverage_figures_describe_the_current_code`、`test_execution_report_suite_figures_add_up_to_the_tests_that_exist` |
| `tests/test_docs.py::test_the_link_check_does_not_accept_a_placeholder` | 通过 | `ec52527` 新加的回归判据（占位目标在任何平台都判红）有效 ✓——**但它把指纹作废了**（S-1） |

### 4.8 social preview 图：与落盘数字完全一致

读图核对过：93.3% / 7135-7650 / 1632（1485 快 + 147 集成）/ 49（28 REST + 6 MCP + 15 CLI）
/ MCP 只读工具 11 个 / Apache-2.0 / v1.0.0——**与记录块逐项对得上**，图面无截断、无中英错别字，
三个大数字的算术自洽。`readme-image-consistency.md` 的 §2.2 / §2.3 逐行核过，**结论正确**。

`readme-image-consistency.md` 的 14 条里，**§1.3–§1.14 这 12 条仍然开着**（我逐条核过，
这一轮一条都没动）：图零自动重生成路径、`28+6+15` 会被读成接口数、`49` 没说是静态条数、
英文 README 上挂中文标签与中文注释、`howto §4` 那张出处表的两处错（`README.md:5` 不是中文
tagline 的出处；`docs/architecture/public-contracts.md:348` 是空行，正文在 **:355**）、中文 README 说自己的
徽章要「人工同步」（脚本 `README_PATHS` **两个 README 都写**，`scripts/refresh-report-figures.py:101`）、
中英 tagline 不一致、中文 README 没有这张图、徽章链接落点不对、版式与「可核查 / 可核验」。

### 4.9 其它逐条核过、确认没问题的

- `docs/reports/README.md` 的索引本身：§1–§6 点名的 **60** 个文件与目录里的 **60** 份
  `.md` **一一对应，无重复、无遗漏**，四份新报告与 `glossary-pass.md` 都在表里
  （M-1/M-2/M-11/L-4 是这个索引里的另外四个问题）；
- `docs/glossary.md` 的 **89 条术语、分十节**与 `docs/reports/glossary-pass.md:61` 声明的
  逐节条数（10/8/5/13/14/21/5/5/3/5）**完全一致**；
- `docs/reports/v1.0.0-release-checklist.md` §3 步骤 8「发布后修正并重打 tag」、
  §8 改成「CI 现状」、§8.2 的 B7 —— 三处的**内容**都对（B7 说「2026-11-18 实测：徽章已是
  1632，那两处还写着 1612」是带日期的历史陈述，且那两处现在已经是 1632，B7 的判断
  「测量脚本只写徽章那一个数字，这两处是手写的」**仍然成立**）；
- `docs/reports/outreach-first-read.md` §4「确认过且没问题的部分」（§4.1 数字换得干净、
  §4.2 事实逐条对得上、§4.3 没发现过度承诺、§4.4 字符数 14 行可复算、§4.5 M6 未被引用）
  —— 逐条核过，**§4.4 那一条现在不成立**（见 S-3）；其余仍成立。

---

## 5. 给主会话的处置顺序

1. **先处理 S-2 / S-3**：那是「照着走就会把超限的素材发出去」——一件能直接害到交付的事。
2. **再处理 S-5 / S-6**：把「tag 现在指向 X」全部改成**不写死 hash**的写法（照
   `docs/outreach/publish-review.md:11-12`），CI 结论那条补上时点。
3. **S-4**：术语表整表重算，并把 `docs/glossary.md` 加进引用检查器的名单。
4. **S-7 / S-8**：给两份报告加状态注（「发现已落地 / 严重发现已关闭」），把「原文（逐字）」
   标成「修复前的原文」。**不要重写正文**——它们是记录，改了就把历史改了。
5. **M-1 / M-2 / M-3 / M-4 / M-11 / L-1 / L-3**：索引与几处计数的小修，一起做。
   （**S-1 是重测量落盘的事**，不在这份清单里——它由主会话正在跑的那次重测量解决。）
6. **M-5 / M-6 / M-7 / M-8 / M-9 / M-10**：分头改；`M-8` 记得 `CLAUDE.md` 与 `AGENTS.md`
   必须逐字相同。
7. **L-4**：把本文加进 `docs/reports/README.md` §6，并把三处「60」改成「61」。

**有一件事本文做不到**：`v1.0.0-ci-run-record.md` 缺的那两次 CI run（S-6），需要联网的
`gh` 只读查询，本轮不联网，查不了。
