# M10 读者视角走查报告（第二轮）—— 上一轮 29 条是否真的关闭，修正本身有没有引入新问题

> **本文件的性质：** 这是第二轮**只读**的「读者视角走查」。基线是**当前工作树**
> `02e6d9c`（合并 M10 读者材料修正与验收 commit 重钉），不是第一轮报告所钉的
> `599ab67`。作者以一位**从未参与开发**的外部评审者的身份，把 M10 独立验收的
> 四份材料（邀请函成稿、读者验收包、验收准备包、读者工具包）与**它们指向的
> 一页版执行摘要**重读一遍，逐条判定第一轮的 29 条是否关闭，并检查修正本身
> 有没有留下新问题。
>
> **本文件只列问题与判定，不替主线程改材料。** 改动权在主线。
>
> **走查方法与边界：**
> - 全部结论用 `Read` / `Grep` / `git show` / `git ls-tree` / `git tag` /
>   `git for-each-ref` / `git rev-parse` 取得，**外加两条只读门禁**：
>   `scripts/check-doc-citations.py`（220 条引用，0 漂移）与
>   `scripts/check-version-claims.py --base auto`（退出码 0），以及
>   `pytest tests/test_docs.py`（60 passed，不带 `--cov`）。
> - **未运行** pytest `--cov`、coverage 任何命令、`uv sync`、
>   `scripts/refresh-report-figures.py`；未修改仓库任何文件（本次只新增本报告）；
>   未写入共享树 `E:\Dexatlas`；未打 tag、未发 PR、未联网。
> - **工作副本**：`E:\Dexatlas\.claude\worktrees\outreach-cleanup-20-084399`
>   （分支 `claude/sad-golick-351f9a`，自 `8f9ddca` 快进到 `02e6d9c`）。
> - **行号基准**：一律以当前树 `02e6d9c` 为准。第一轮报告的行号钉在旧基线，
>   本表用**内容**定位后重新取当前行号。
> - 凡属推断而非直接取证，一律标「**推断**」并给出推断依据。
> - 本文件不转录任何密钥样式字符串；demo 样本里的 `sk_live_…` 字符串常量
>   只以模式出现。

---

## 0. 结论速览

### 0.1 第一轮 29 条的判定分布

| 判定 | 条数 | 条目 |
|---|---:|---|
| **已关闭** | **23** | A1、A2、A3、A4、A5、A6、A7、A8、A9、A10、A11、B4、B5、B6、B7、B8、B9、B10、C1、C2、C3、C4、C6 |
| **未关闭** | **5** | A12（6 个术语里剩 1 个）、B1、B2、B3、C7 |
| **判定有误** | **1** | C5 |
| **合计** | **29** | — |

> **口径说明（对第一轮报告本身的一处观察）：** 第一轮报告的小标题写的是
> 「A 档 12 条 / B 档 8 条 / C 档 6 条」（合计 26），但三张表的**实际行数**是
> 12 / 10 / 7 = 29（`docs/reports/m10-reader-walkthrough.md:58`、`:75`、`:90`
> 三处小标题 vs 表格行）。第一轮的「结论速览」表（`:30-39`）里的「29 条独立
> 问题（分类计数含跨类，故分项之和 > 29）」说的是七分类计数，不是 A/B/C 档。
> 本轮按**表格实际行数**编为 A1–A12 / B1–B10 / C1–C7，映射见 §2。

### 0.2 第二轮新发现：8 条

| 编号 | 一句话 | 类别 |
|---|---|---|
| **N1** | `v1.0.0` tag 落后 25 个提交，材料却断言「checkout tag 即得含本轮全部修正的版本」 | **会让评审者做出错误判断** |
| N2 | 一页版执行摘要仍写「暖缓存约 30 秒」（其余四份：1.5–2 分钟） | 会让评审者卡住（数字矛盾） |
| N3 | 一页版执行摘要仍要读者「向发起人索取 commit hash」 | 会让评审者卡住（顺序缺失） |
| N4 | 一页版执行摘要仍指向邀请函**模板** | 会让评审者卡住（路径失效） |
| N5 | 一页版执行摘要完全没写验收 commit / `git checkout v1.0.0` | 会让评审者走错起点 |
| N6 | 准备包两条路线给两个不同的 checkout 目标（`:204` vs `:235`） | 口径不一致 |
| N7 | 准备包 §7 末两行停在旧树（install.md 措辞、文档门禁状态） | 口径不一致（状态过期，会让评审者以为发布不合规） |
| N8 | 准备包 `:688`「已发布 v1.0.0」与 `:693`「不得据此发布 v1.0.0」并存 | 自相矛盾 |

详见 §3。

### 0.3 一句话结论

**还不能。** 四份材料本身已经接近可用——40 项、19 项阻断项、退出码 0–6、
契约 49 项、全部 `file:line` 引用都自洽了；但**评审者 `git checkout v1.0.0`
现在拿到的不是这批材料**，而且材料正在向他断言「拿到的是」（见 N1 与 §5）。

---

## 1. 基线事实（本轮取证）

这几条是后面所有判定的公共前提，先列出来。

| 事实 | 取证 |
|---|---|
| 当前树 = `02e6d9c`「合并 M10 读者材料修正与验收 commit 重钉（144d5a9）」 | `git log --oneline -1` |
| `v1.0.0` 是**附注 tag**，指向 commit `8f9ddca` | `git rev-parse v1.0.0` → `e937ca1`（tag 对象）；`git rev-parse v1.0.0^{commit}` → `8f9ddcaf7804841d77270c1fdb548110faecc598` |
| `8f9ddca` 比当前树**落后 25 个提交** | `git describe --tags` → `v1.0.0-25-g02e6d9c` |
| `origin/main` = `8f9ddca`（与 tag 同一点） | `git rev-parse origin/main` → `8f9ddcaf…`（本地 fetch 快照时间 2026-11-17 19:47） |
| 本轮修正只落在 `origin/claude/m10-reader-materials-f60bbe` 与 `origin/claude/architecture-contract-docs-37f29a` 上，**没有** `origin/main` 含 `02e6d9c` | `git branch -r --contains 02e6d9c` → 空；`git branch -r --contains c4785ee` → `origin/claude/m10-reader-materials-f60bbe` |
| `277d0fa` 是**真实存在**的 commit，但里面**没有** `docs/reports/m10-reader-kit.md` | `git cat-file -t 277d0fa` → commit；`git ls-tree --name-only 277d0fa docs/reports/ \| grep -c m10-reader-kit` → `0` |
| `277d0fa` 里的准备包仍写 F1 = 退出码 0–5、F3 = 10 个 MCP 工具 | `git show 277d0fa:docs/reports/m10-acceptance-pack.md \| grep -n "^| F1 \|^| F3 "` |
| `e4f3011` 也是**真实存在**的 commit | `git cat-file -t e4f3011` → commit |
| 当前树的只读门禁全绿 | `check-doc-citations.py` → 220 条 / 0 漂移；`check-version-claims.py --base auto` → 退出码 0（2 项既有声明与 `8f9ddcaf` 相同，非新增）；`pytest tests/test_docs.py` → **60 passed** |
| 40 项、19 项 ★、分组 7/6/6/5/5/6/5 与材料声明一致 | `grep -c "| ★ |"` → 19；`grep -cE "^\| (A\|B\|C\|D\|E\|F\|G)[0-9]+ \|"` → 40；清单在 `m10-acceptance-pack.md:173`、`m10-invitation-final.md:136-137`、`m10-reader-kit.md:136` 三处逐字相同 |
| demo 样例的计数与材料一致 | `docs/case-studies/attachments/demo-report.json` → `classes 5 / methods 8 / call_sites 23 / call_edges 21 / resource_strings 1`，`evidence_by_level {"verified": 11}` |
| demo.apk 的 sha256 与材料一致 | `sha256sum examples/demo-app/demo.apk` = `docs/reports/m10-reader-package.md:149` 所写 |

---

## 2. 表一：第一轮 29 条逐条复核

「第一轮编号」是本轮为便于引用而新编的；「首轮定位」给出第一轮报告里的
原始 `文件:行`（旧基线 `599ab67`），便于对照。

### 2.1 A 档（会让评审者做出错误判断）—— 12 条

| 第一轮编号 | 文件:行（当前树） | 状态 | 证据（file:line 或文件内容） |
|---|---|---|---|
| **A1** v1.0.0 tag 不存在 | `docs/reports/m10-invitation-final.md:27`；`docs/status.md:3`、`:128`；`docs/HANDOVER.md:11-12`；`README.md:32`、`:129`；`README.zh-CN.md:22`；`docs/reports/m10-acceptance-pack.md:719-720` | **已关闭** | `git tag -l` → `v1.0.0` 存在（附注 tag，对象 `e937ca1`，创建日 2026-11-17）；六处宣称现在都与事实相符：「已发布的 v1.0.0（tag 2026-11-17，可用 `git tag -l` 核对）」（邀请函 `:27`）、「`v1.0.0`（tag 2026-11-17）已发布」（status.md `:128`）、「The state itself is the tag **`v1.0.0`** (2026-11-17)」（HANDOVER `:11-12`）、「v1.0.0 released (tag 2026-11-17)」（README `:32`）、「v1.0.0 已发布（tag 2026-11-17，见发版说明）」（README.zh-CN `:22`）。**但见 N1**：tag 指向的不是这批材料。 |
| **A2** M8-4 有三种说法 | `docs/reports/m10-acceptance-pack.md:164`、`:587`、`:668`；`docs/reports/m10-reader-package.md:312`；`docs/reports/m10-reader-kit.md:280-283` | **已关闭** | 三处现在同口径：「已关闭（v1.0.0 退出码 6）」（准备包 `:668`）、「已在 v1.0.0 关闭」（读者包 `:312`）、「已知限制只剩 macOS 未验证（M8-2、M8-3 已修复并合入）；M8-4 … 已在 v1.0.0 由新退出码 6 关闭」（工具包 `:280-283`）。★ 项 G3（准备包 `:164`）已从「核对 M8-4 的退出码缺口（全部后端失败仍为 0）」改成「三个后端全部失败时退出码应为 **6**（`EXIT_NO_INDEX`，v1.0.0 新增），不是 0；记录实际退出码」——评审者按此判不会得到相反答案。 |
| **A3** 邀请函拿 17/15/17 冒充最终重测 | `docs/reports/m10-invitation-final.md:47-50` | **已关闭** | 现文：「最终完整重测 DexAtlas 49/60 = 81.7%，逐轮 15/20、16/20、18/20，见 retest4 报告；**更早一次重测**逐轮为 17/15/17、合计同为 49/60」。两个数字都标了归属，不再有冒充。核对：`docs/benchmarks/m6-level2-retest4.md:82` = r1 15/20、r2 16/20、r3 18/20；`docs/benchmarks/m6-level2-retest3.md:85` = 17/20、15/20、17/20。 |
| **A4** 占位符 commit 与 `e4f3011` | `docs/reports/m10-invitation-final.md:54-72`（占位符在 `:60`）；`docs/reports/m10-reader-package.md:9-11`、`:50-53`；`docs/reports/m10-reader-kit.md:9-11`；`docs/reports/m10-acceptance-pack.md:11-12` | **已关闭**（材料层） | 邀请函 `:60` 占位符现为「commit 【待填：v1.0.0 发版 commit 的完整 hash】」，`:61-63` 说明「也就是读者执行 `git checkout v1.0.0` 所得到的那个提交，即含本轮全部材料修正的版本」；`:66-69` 要求用 `git rev-parse HEAD` 核对；`:71-72` 给出「取不到就联系发起人」的兜底。四份材料的基线表述已统一为「v1.0.0 发版 commit」。**但这句「即含本轮全部材料修正的版本」目前不成立，见 N1。** |
| **A5** 读者工具包不在钉定提交里 | `docs/reports/m10-reader-kit.md`（整份） | **已关闭** | 钉定提交已从 `277d0fa` 改为 `v1.0.0` tag；tag 树（`8f9ddca`）里 `docs/reports/m10-reader-kit.md` 存在（`git ls-tree --name-only 8f9ddca docs/reports/ \| grep m10-reader-kit` → 命中）。`277d0fa` 里确实仍无该文件（计数 0），但它已不是钉定提交。 |
| **A6** F1 只写退出码 0–5 | `docs/reports/m10-acceptance-pack.md:151` | **已关闭** | 现文：「CLI 退出码：0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、5 截断、**6 跑完但无可用的代码索引（`EXIT_NO_INDEX`，v1.0.0 新增）**」。tag 树 `8f9ddca` 的同一行也是 0–6。 |
| **A7** F3 写 10 个 MCP 工具 | `docs/reports/m10-acceptance-pack.md:153` | **已关闭** | 现文：「MCP：工具清单为契约表的 **11 个**，全部只读注解」。`docs/architecture/public-contracts.md:348` 亦为 49 项（28 REST + 6 MCP + 15 CLI），`docs/releases/v1.0.0.md:61-62` 同为 49。 |
| **A8** 中英文 README 状态相反 | `README.md:32`；`README.zh-CN.md:22` | **已关闭** | 英文：「Status: early development — v1.0.0 released (tag 2026-11-17); Phase 3 is delivered, but the M6 agent acceptance line and the M10 independent acceptance are still open.」；中文：「当前状态：早期开发——v1.0.0 已发布（tag 2026-11-17，见发版说明）；Phase 3 已交付，但 M6 验收线与 M10 独立验收仍未完成。」语义与标点均对齐。 |
| **A9** §8 退出门槛表自相矛盾 | `docs/reports/m10-acceptance-pack.md:654-656`、`:688` | **已关闭** | `:654-655` 现写「**实际状态：v1.0.0 的 tag 于 2026-11-17 打好，而独立验收尚未执行**——这次发版不含任何验收结论；M10 仍是「未完成」，本包 40 项仍全部「未验证」」；`:656` 加了时间限定「**本包编写时（2026-11-15）没有 tag、没有发布候选、没有验收结论。**」；§8 表 `:688` 行写「已发布：v1.0.0（tag 2026-11-17）——但独立验收在其后仍未执行，本次发版不含验收结论」。**残余张力见 N7。** |
| **A10** 冲突以谁为准，两条规则打架 | `docs/reports/m10-acceptance-pack.md:42-47`；`docs/reports/m10-reader-kit.md:340-344` | **已关闭** | 准备包改成三层规则：「本包、[读者验收包]与[读者工具包]三份材料之间冲突时，以**本包的判定标准**为准；本包与被验收对象（公共契约表、服务回归集、M8 安装演练、源码、README）冲突时，**以原始证据和代码为准**，并把差异按 §3.7 记成卡点」。工具包 `:342` 用同一口径。 |
| **A11** 「B1」到底指什么 | `docs/reports/m10-acceptance-pack.md:561-565`；`docs/reports/m10-reader-package.md:279-283` | **已关闭** | 准备包 §6 就地定义「**B1 验收线** = v1.0.0 发版阻断项 B1「M6 层级 2 未达验收线」（每轮 ≥80%、三轮合计 ≥90%）」，并指向 `docs/reports/v1.0.0-dry-run.md`；读者包 `:279-283` 另给「术语（就地定义）」块，并明说它与判定表里的**验收项 B1**「是两回事」。 |
| **A12** 六个术语未定义 | `docs/reports/m10-invitation-final.md:113-114`；`docs/reports/m10-reader-package.md:179-184`、`:247`、`:272`、`:300` | **未关闭**（6 项里关掉 5 项） | 已定义：`verified`/`lead`/`insufficient` 三级语义（邀请函 `:113-114`；读者包 `:179-184`，并指明出处「公共契约表 §证据三级」）；「确定性判分」以「层级 0（确定性判分 20/20）」标注（读者包 `:247`）；「预算」给出具体数「DexAtlas 120000 tokens/任务」（读者包 `:300`）。**仍无定义**：`trace` —— 读者包 `:272`、`:274`、`:285` 三次使用「committed trace」「trace 合计 853,103 tokens」，全篇未说 trace 是什么（模型的一次运行记录？判分输入？），而它正是 E2/E3 的核查对象。 |

### 2.2 B 档（会让评审者卡住或无法复现）—— 10 条

| 第一轮编号 | 文件:行（当前树） | 状态 | 证据（file:line 或文件内容） |
|---|---|---|---|
| **B1** 暖缓存 30 秒 / 1.5–2 分 / 2 分 | `docs/reports/m10-reader-package.md:69`、`:399-401`；`docs/reports/m10-reader-kit.md:181`；`docs/reports/m10-acceptance-pack.md:193`；`docs/reports/m10-invitation-final.md:86`；**`docs/reports/m10-executive-summary.md:41`** | **未关闭** | 四份材料已统一为 1.5–2 分钟（读者包 `:69`、`:399`；工具包 `:181`；准备包 `:193`；邀请函 `:86`），并在读者包 `:400-401` 补了口径说明「M8 演练在已就绪的会话工作树上实测约 30 秒，同一环境差异下两者都成立」。**但一页版执行摘要 `:41` 仍是「暖缓存约 30 秒」**——而读者包 `:18` 恰恰让读者「**第一次来？** 先看一页版[读者执行摘要]」。 |
| **B2** 读者包首页指向邀请函**模板** | `docs/reports/m10-reader-package.md:19-20`；**`docs/reports/m10-executive-summary.md:4`** | **未关闭** | 读者包已改：「邀请与独立性要求见[邀请函成稿](m10-invitation-final.md)（发给您的就是这一份；[邀请函模板](m10-invitation-template.md)只供发起人填空用）」。**但执行摘要 `:4` 仍写「细节见[读者验收包](m10-reader-package.md)与[验收邀请函](m10-invitation-template.md)」**，仍把读者指向模板。 |
| **B3** 执行摘要第 1 步要 commit | **`docs/reports/m10-executive-summary.md:25`**、`:27`；`docs/reports/m10-reader-package.md:6`、`:50-53` | **未关闭** | 读者包已改：`:50-53`「验收 commit 由验收发起人钉定，**随邀请函给出**（本轮是 v1.0.0 发版 commit，完整 hash 在[邀请函成稿 §2]）——**不需要你另行索取**，全程只验这一个 commit」。**但执行摘要 `:25` 仍是「1. **领 commit**：向发起人索取固定 commit hash」**，`:27` 仍是 `git checkout <commit>`。读者按摘要走，仍会在第 1 步卡住并去问作者——而读者包 `:46-47` 规定「靠作者口头补充才走通的步骤，相关验收项判不通过」。 |
| **B4** 工具包两处 `file:line` 引用错位 | `docs/reports/m10-reader-kit.md:282`、`:165`、`:173`（全文 61 处引用、去重 47 条，全部核对） | **已关闭** | 原问题位：`:275` 把 `reader-package.md:293` 当作「退出码 6 的出处」，而 293 行讲的是预算。现 `:282` 引 `reader-package.md:312` =「**M8-4（已在 v1.0.0 关闭）**」段，命中。`:165` 引 `invitation-final.md:146` =「### 六、结果回传方式」，命中；`:173` 引 `invitation-final.md:153` = 脱敏条款，命中。工具包内 47 条去重引用逐条 `sed -n Np` 核对，**全部命中目标内容且行号在文件范围内**（含 `:20`、`:22`、`:23`、`:26`、`:42-43`、`:122-123`、`:128`、`:136`、`:152-158`、`:183`、`:196`、`:200`、`:205`、`:218-219`、`:226`、`:228`、`:236`、`:238-239`、`:247`、`:252`、`:266`、`:274-279`、`:282`、`:287`、`:296`、`:308`、`:319-334`、`:340`、`:344`）。 |
| **B5** M8-3 与 install.md 不一致已过期 | `docs/reports/m10-acceptance-pack.md:667`；`docs/install.md:19-25` | **已关闭** | 准备包 `:667` 状态列「已修复并合入」；`docs/install.md:19-25` 现在先给四 extras 路线（`uv sync --extra dev --extra analysis --extra mcp --extra demo`），最小路线另标注。读者包 `:99-104` 另有一段说明历史与现状。 |
| **B6** M8-2/M8-3 在两处状态相反 | `docs/reports/m10-acceptance-pack.md:666-667`；`docs/status.md:135` | **已关闭** | 准备包 `:666`（M8-2）与 `:667`（M8-3）状态列均为「已修复并合入」（`d90baff`），与 `docs/status.md:135`「M8-2…与 M8-3…**已修复并合入**（d90baff…）」一致。 |
| **B7** 门禁现状没说属于哪棵树 | `docs/reports/m10-acceptance-pack.md:625`、`:638-642` | **已关闭** | `:625` 加了标题「**编写本包时的门禁现状（2026-11-15，基准 `ff5c4cc`）——历史账，不是验收 commit 的现状**」；`:638-642` 加了「读者怎么用这张表」：上面 7 条命令应全部以退出码 0 结束，非 0 就按 §3.7 记卡点，「不要拿本表的历史数字去判通过或不通过」。**但同一节末两行（§7 表尾）在 §7 里没有这句限定，见 N6。** |
| **B8** 读者包步骤与验收项错位 | `docs/reports/m10-reader-package.md:87`、`:137`、`:155`、`:187`、`:200`、`:219`、`:232`、`:254` | **已关闭**（残留一处，见右栏） | 每个步骤标题现在都带验收项编号：「### 3.1 第 1 步：取得固定副本（验收项 A1）」「### 3.3 第 3 步：首次分析 demo.apk（验收项 A4）」「### 3.4 第 4 步：检索、证据与 locator 解析（验收项 B3–B4、C1–C3）」「### 3.5 第 5 步：三格式报告导出（验收项 A5、D1–D2）」「### 3.6 第 6 步：证据包导出与校验（验收项 C5–C6、D3–D5、G5）」「### 3.7 第 7 步：至少一个完整案例核对（验收项 B1–B6）」「### 3.8 第 8 步：契约与回归集抽查（验收项 E、F 组，可选但建议）」。**残留**：逐项统计读者包里出现过的验收项编号，只有 A1–A6、B1/B3/B4/B6、C1–C2/C3/C5–C6、D1–D3/D5、E1–E3/E5、F1/F5/F6、G1–G3/G5 出现过；**A7（耗时与卡点）与 C4（计数一致）两个编号在读者包全文里一次都没出现**（内容其实都做了——A7 在 §5.2 卡点记录与 §5.4 时间参考，C4 在 §3.5「抽查 3 个数字…确认 Markdown / JSON / HTML 三处一致」——但评审者按编号查表时会找不到对应行）。 |
| **B9** 自查记录属于哪棵树 | `docs/reports/m10-selfcheck.md:11-12`、`:88-99`；`docs/reports/m10-reader-package.md:430-433` | **已关闭** | 自查文档头部现在写「执行日期：2026年11月17日 · 运行树：v1.0.0 发版 commit（含本轮 M10 读者材料修正；读者在自己的验收 commit 上复跑时以自己的实际输出为准）」，并附两项失败项的成因表与「以你的实际输出为准」的收尾。读者包 `:430-433` 另有一段提醒读者这是快照。**但「运行树：v1.0.0 发版 commit（含本轮 M10 读者材料修正）」这句在 tag 未重打前同样不成立，见 N1。** |
| **B10** 契约实测 46 vs 49 | `docs/architecture/public-contracts.md:348`；`docs/releases/v1.0.0.md:61-62` | **已关闭** | 契约表：「**检查项清单共 49 项：28 REST + 6 MCP + 15 CLI**」；发版说明：「the public contract table frozen with **49** live checks (28 REST + 6 MCP + 15 CLI)」。两处一致；`28 + 6 + 15 = 49` 自洽。 |

### 2.3 C 档（影响材料可信度、不改变判定）—— 7 条

| 第一轮编号 | 文件:行（当前树） | 状态 | 证据（file:line 或文件内容） |
|---|---|---|---|
| **C1** 契约表写「当前 0.2.0」 | `docs/architecture/public-contracts.md:327` | **已关闭** | 现文：「（当前 `1.0.0`）；打包经 hatch 从该文件读取（`pyproject.toml:145-146`）」。 |
| **C2** `__init__.py` 版本 0.2.0 vs 发版说明 v1.0.0 | `src/dexatlas/__init__.py`；`CHANGELOG.md` 顶部 | **已关闭** | `scripts/check-version-claims.py --base auto` 输出「package version: 1.0.0」「changelog: 1.0.0, 0.2.0, …」「newest release: v1.0.0」，退出码 0。 |
| **C3** 基线 75/65 与 77.5/68.75 两套数 | `docs/reports/m10-acceptance-pack.md:14-16`、`:500-502`；`docs/reports/m10-reader-package.md:13-16`、`:347-349`；`docs/reports/m10-reader-kit.md:90-92`、`:283-285` | **已关闭** | 三份材料同一口径：「75% / 65% 是人工基线（[准备度评估]），[复评]的 77.5% / 68.75% 是同一组维度与权重下的作者自评更新，**不是新的权重基准**——重评请与 75% / 65% 这一档对齐」。邀请函 `:40-41` 也只说「按既有的六维度、双平台权重（GitHub / Upwork）重新打分」，未引复评数。 |
| **C4** 工具包里的 `npm install` | `docs/reports/m10-reader-kit.md`（全篇） | **已关闭** | `grep -n "npm"` 在工具包中零命中；工具包现在的安装命令是 `uv sync --extra dev --extra analysis --extra mcp --extra demo` 与 `uv run --no-sync python -c "…"`。 |
| **C5** README 里程碑表 vs 退出标准表 | `README.md:129`；`README.md:538` | **判定有误** | 两处现在一致，且**本来就不矛盾**：`:129` 里程碑表写 `independent acceptance (pack ready, not run)`；`:538` 退出标准表写 M10 = `independent acceptance, re-scoring, release candidate` / 「**preparation ready; acceptance not run**」。首轮报告自己在「涉及的事实是什么」栏里也写了「两处并不矛盾」，把它列为问题的唯一理由是「里程碑表把 M10 整体列为 v1.0.0 交付内容，退出标准表却把 M10 列为未完成的 Phase 3 退出项」——这是**排版语义**而非事实冲突：第一轮报告已用「并不矛盾」自我否定。故判为判定有误。 |
| **C6** 四份材料各写各的基线 | `docs/reports/m10-acceptance-pack.md:11-12`；`docs/reports/m10-reader-package.md:9-11`；`docs/reports/m10-reader-kit.md:9-11`；`docs/reports/m10-invitation-final.md:5-6` | **已关闭** | 四处现在都写「v1.0.0 发版 commit」，且都指向邀请函成稿 §2 的占位符。**但一页版执行摘要完全没写基线，见 N5。** |
| **C7** 两份窄验证报告引用从未存在的文件 | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:3`；`docs/benchmarks/m6-level2-narrow-verify2.md:3` | **未关闭** | 两处行内 code span 至今仍写 `m6-level2-narrow-verify.md`；该文件在任何分支都不存在（`git log --all --oneline -- 'docs/benchmarks/m6-level2-narrow-verify.md'` → 空）。真实产物是 `m6-level2-narrow-verify-incomplete.md`。仓库自己的 `docs/reports/m10-number-traceability.md:72` 已把这件事记为「不存在」并给出替代路径——**但那份文件没有任何读者材料链接它**（`grep -rn "m10-number-traceability" docs/ README*.md` 只命中 `docs/reports/` 内部的三份复核报告），评审者看不到这份排查，仍会 404。 |

---

## 3. 表二：第二轮新发现的问题

按「修正本身引入的」与「修正时漏改的」两类，都属于第一轮没提过的新条目。

| 编号 | 文件:行 | 评审者的疑问或卡点 | 类别 |
|---|---|---|---|
| **N1** | **`docs/reports/m10-invitation-final.md:60-63`（配合 `docs/reports/m10-reader-package.md:80`、`docs/reports/m10-acceptance-pack.md:204`、`docs/reports/m10-reader-kit.md:9-10`）** | **「邀请函说 `git checkout v1.0.0` 得到的就是『含本轮全部材料修正的版本』——我照做了，拿到的是 `8f9ddca`，里面邀请函第二节写的是 `commit 277d0fa`、让我 `git checkout 277d0fa`。那棵树里根本没有读者工具包，准备包的 F1 还写退出码 0–5、F3 还写 10 个 MCP 工具。我到底该信哪一份？」** | **数字/事实矛盾（会让评审者做出错误判断）** |
| **N2** | `docs/reports/m10-executive-summary.md:41` | 「一页版说暖缓存约 30 秒，读者包、工具包、准备包、邀请函都写 1.5–2 分钟。我按 30 秒做完花了 2 分钟，算不算卡点？」（读者包 `:18` 让读者「第一次来」先看这一页） | 数字矛盾（修正漏改） |
| **N3** | `docs/reports/m10-executive-summary.md:25`、`:27` | 「第 1 步是『领 commit：向发起人索取固定 commit hash』，可读者包说 commit 随邀请函给出、不需要另行索取，还说靠作者口头补充才走通的步骤要判不通过。我是不是第 1 步就被判不通过？」 | 顺序缺失 + 自相矛盾（修正漏改） |
| **N4** | `docs/reports/m10-executive-summary.md:4` | 「『细节见…[验收邀请函]』点开是模板不是成稿——我该读哪一份？」 | 路径失效（修正漏改） |
| **N5** | `docs/reports/m10-executive-summary.md`（全篇） | 「这一页从头到尾没说要验哪个 commit、没有 `git checkout v1.0.0`、没提醒不要用 `main`。我读完它就直接 `git clone` 走 `main` 了。」 | 该有而没有（修正漏改） |
| **N6** | `docs/reports/m10-acceptance-pack.md:235` | 「路线 A（`:204`）写 `git checkout v1.0.0`，路线 B Docker（`:235`）写 `git checkout <验收发起人钉定的 commit>`——同一个包里的两条路线给两个不同的 checkout 目标。」 | 口径不一致 |
| **N7** | `docs/reports/m10-acceptance-pack.md:672`、`:673` | 「§7 遗留问题表里说 install.md 还写着『No APK is committed』——我打开 install.md 看到的是『Five first-party sample APKs are committed』；又说文档门禁『未关闭（阻断文档门禁）』——可我在验收 commit 上跑 `tests/test_docs.py` 是 60 passed，引用检查 0 漂移，version-claims 退出码 0。这两条到底还成立吗？」（同一张表的 M8-1～M8-4 行都已更新为「已修复并合入」「已关闭」，唯独这两行停在旧树，且 §7 没有 §6.3 那句「历史账」的限定） | 数字/状态过期（修正漏改） |
| **N8** | `docs/reports/m10-acceptance-pack.md:688` vs `:693` | 「§8 退出门槛表最后一行写『已发布：v1.0.0（tag 2026-11-17）』，可本节结尾又写『不得据此发布 v1.0.0』。那这个 tag 到底算不算合规发布？评审者要不要把它记成一条卡点？」 | 自相矛盾（修正留的） |

### 3.1 N1 的完整取证（这是本轮最严重的一条）

**材料怎么说（当前树 `02e6d9c`）：**

- `docs/reports/m10-invitation-final.md:60-63`：
  > `commit 【待填：v1.0.0 发版 commit 的完整 hash】`
  > （填写说明：此处填 v1.0.0 发版 commit 的完整 hash——也就是读者执行
  > `git checkout v1.0.0` 所得到的那个提交，**即含本轮全部材料修正的版本**；
  > 由验收发起人在发出本函之前填入）
- `docs/reports/m10-invitation-final.md:66-69`：要求 `git checkout v1.0.0` 后用
  `git rev-parse HEAD` 与占位符里的 hash **逐字相同**再开始验收，不一致就停下。
- `docs/reports/m10-reader-package.md:80`、`docs/reports/m10-acceptance-pack.md:204`、
  `docs/reports/m10-reader-kit.md:9-10`：都给 `git checkout v1.0.0`。

**仓库里实际是什么：**

| 取证 | 结果 |
|---|---|
| `git rev-parse v1.0.0^{commit}` | `8f9ddcaf7804841d77270c1fdb548110faecc598` |
| `git describe --tags` | `v1.0.0-25-g02e6d9c`（tag 比当前树落后 25 个提交） |
| `git rev-parse origin/main` | `8f9ddcaf…`（**与 tag 同一点**；本地 fetch 快照 2026-11-17 19:47） |
| `git branch -r --contains 02e6d9c` | 空（当前树未出现在任何远端跟踪分支上） |
| `git branch -r --contains c4785ee`（M10 读者材料修正） | 只有 `origin/claude/m10-reader-materials-f60bbe` |
| `git show 8f9ddca:docs/reports/m10-invitation-final.md` 的 `:57`、`:59`、`:62`、`:92`、`:163` | 分别写 `commit 277d0fa`、`git checkout 277d0fa` 检出该提交、`git checkout 277d0fa`、执行 `git clone` 与 `git checkout 277d0fa`、全程只验 `277d0fa` 这一个提交 |
| `git show 8f9ddca:docs/reports/m10-reader-package.md:16` | 「邀请与独立性要求见[验收邀请函](m10-invitation-template.md)」（仍是模板） |
| `git show 8f9ddca:docs/reports/m10-reader-package.md:63` / `:379` | 暖缓存「约 **2 分钟**」/「暖缓存约 **30 秒**」（两种说法并存） |
| `git show 8f9ddca:docs/reports/m10-acceptance-pack.md:567` / `:637` / `:157` | 「M8-2 / M8-3 / M8-4 仍未关闭」/「未关闭（重要）」/ G3「核对 M8-4 的退出码缺口（全部后端失败仍为 0）」 |
| `git show 277d0fa:docs/reports/m10-acceptance-pack.md:144` / `:146` | F1 = 退出码 0–5（无 6）；F3 = **10 个** MCP 工具 |
| `git ls-tree --name-only 277d0fa docs/reports/ \| grep -c m10-reader-kit` | `0`——**读者工具包不在 `277d0fa` 里** |

**评审者照做的路径：**

```
git clone … && cd dexatlas && git checkout v1.0.0      # → 8f9ddca
$ cat docs/reports/m10-invitation-final.md | sed -n '57p'
commit 277d0fa                                        # ← 邀请函叫他再 checkout 一次
$ git checkout 277d0fa
# → 277d0fa 里没有 docs/reports/m10-reader-kit.md
# → 准备包 F1 写退出码 0–5、F3 写 10 个 MCP 工具
# → 准备包 :567/:637 写 M8-4「未关闭（重要）」，而工具包说已关闭
```

也就是说：**第一轮的 A2、A4、A5、A6、A7、B1、B2 在 tag 树里原样复现。**

**结论（对任务第 3 问的明确回答）：**

> **否——评审者 `git checkout v1.0.0` 现在拿到的不是当前这批材料。**
>
> `v1.0.0` 指向 `8f9ddca`，落后当前树 25 个提交；`origin/main` 也是 `8f9ddca`。
> 本轮修正（c4785ee 读者材料、144d5a9 自查、1917a23/2459601 架构与契约数字、
> ad61bf4、27a8d67、02e6d9c）**都还没进 tag，也还没进 `origin/main`**。
>
> 材料里那句「即含本轮全部材料修正的版本」（`m10-invitation-final.md:62`）
> 目前是**不成立的**。任务说明里「tag 会被重打一次指向最终 commit」是对这件事的
> 处置承诺，但**在重打之前，这句话是假的**，而邀请函正拿着它去要求评审者签字。
>
> **推断（依据：以上全部为直接取证，唯一推断是「评审者的 clone 只会拿到
> `origin` 上的内容」）**：`git checkout v1.0.0` 与 `git clone` 默认分支两条路
> 现在都会落到同一棵**修正前**的树。**除非先重打 tag 并把当前树推到 `origin`，
> 否则邀请函不能发。**

**（附注）** 我实测 `origin/main` 是 `8f9ddca`，依据的是本地 fetch 快照
（`FETCH_HEAD` 时间 2026-11-17 19:47）。主树此后可能已推送，本轮禁止联网，
未做 `ls-remote` 复核——**推断**：即使主树此后推送了 `main`，只要 `v1.0.0` tag
没有跟着重打，评审者 `git checkout v1.0.0` 仍会拿到 `8f9ddca`。这两件事
（重打 tag、推 main）必须都做。

---

## 4. 顺带核：命令、路径、文件名、引用

### 4.1 材料让读者执行的命令

| 检查 | 结果 |
|---|---|
| `uv run dexatlas backends / analyze / manifest / search / source / xrefs / export` | 全部存在于 `src/dexatlas/cli/main.py`（`def` 在 `:289` version、`:295` backends、`:322` analyze、`:564` source、`:812` search、`:855` export、`:903` manifest、`:935` xrefs） |
| `analyze -o / --json / --html` | 存在：`src/dexatlas/cli/main.py:326`（`--output`/`-o`）、`:329`（`--json`）、`:334`（`--html`） |
| `export <id> -o evidence.zip` | 存在：`src/dexatlas/cli/main.py:855-862` |
| `verify_package` / `verify_citations` 导入路径 | 存在：`src/dexatlas/reports/evidence_package.py`（读者包 `:202-206` 所用） |
| `scripts/m10_selfcheck.py`、`scripts/verify-public-contracts.py`、`scripts/check-doc-citations.py`、`scripts/check-version-claims.py`、`scripts/remap-citations.py`、`scripts/refresh-report-figures.py`、`scripts/fetch-fixtures.sh`、`scripts/m6_level2_retest4_report.py` | **全部存在** |
| `tests/test_public_contracts.py`、`tests/test_html_report.py`、`tests/test_evidence_package.py`、`tests/test_docs.py`、`tests/test_doc_citations.py` | **全部存在** |
| `benchmarks/model.py`、`benchmarks/m6_service_set.py` | **全部存在** |
| `examples/demo-app/demo.apk` | 存在；sha256 与 `m10-reader-package.md:149` 一致 |
| `docs/proposals/exit-code-partial-read.md`（准备包 `:668` 引用） | **存在** |
| `docs/benchmarks/m6-level2-retest4.md` / `retest3.md` / `narrow-verify3.md` / `m6-level1-scripted.md` / `service-regression-set.md` | **全部存在** |
| `docs/architecture/public-contracts.md`、`docs/install.md`、`docs/status.md`、`docs/HANDOVER.md`、`docs/releases/v1.0.0.md`、`README.md`、`README.zh-CN.md`、`CHANGELOG.md` | **全部存在** |
| `docs/reports/portfolio-readiness-2026-11-15.md` / `-recheck.md`、`docs/reports/v1.0.0-dry-run.md`、`docs/reports/m10-review-record-template.md` | **全部存在** |

### 4.2 读者材料里的 `file:line` 引用

四份材料 + 一页版执行摘要里的 `file:line` 引用**逐条** `sed -n Np` 取证核对，
**全部命中目标内容**，无一处错位（第一轮 B4 的两类错位已消失）。另跑
`scripts/check-doc-citations.py` → **220 条引用、0 漂移、0 未解析路径**。

> **顺带说明一条门禁盲区（推断，依据在括号里）：** `scripts/check-doc-citations.py`
> 只扫描一份显式白名单里的 4 个文件（`scripts/check-doc-citations.py:58-61`：
> `docs/analysis-provenance.md`、`docs/architecture/public-contracts.md`、
> `docs/reports/phase1-execution-report.md`、`docs/benchmarks/large-apk.md`），
> **不包含任何 M10 读者材料**。所以第一轮 B4 那种「引用指错行」的缺陷不会被
> citation checker 拦下——它本轮也拦不到本报告新增的任何一处（我的引用是手工
> 逐条核的）。这不是缺陷，只是说明：M10 材料的行号一致性目前**没有自动门禁**，
> 靠人读。**推断**（依据：白名单是硬编码的四个路径，且 `check-doc-citations.py`
> 输出的 220 条在新增本报告前后不变）。

### 4.3 数量与口径

| 检查 | 结果 |
|---|---|
| 40 项检查表 | 准备包实际 40 项；邀请函 `:43`、读者包 `:34`、`:41`、`:257`，执行摘要 `:18`，工具包 `:17`、`:33`——六处一致 |
| 19 项 ★ 阻断项 | 实际 `grep -c "\| ★ \|"` = 19；清单在准备包 `:173`、邀请函 `:136-137`、工具包 `:136`、准备包附录 A `:706`/`:709-710` 五处逐字相同 |
| 分组 7/6/6/5/5/6/5 | 与准备包附录 A `:699-706` 一致 |
| demo 计数 5 classes / 8 methods / 23 call sites / 21 call edges / 1 resource string | 与 `docs/case-studies/attachments/demo-report.json` 的 `summary` 一致 |
| demo 报告 11 条 evidence 全为 `verified` | `summary.evidence_by_level = {"verified": 11}` 一致 |
| 契约 49 项（28 REST + 6 MCP + 15 CLI） | `docs/architecture/public-contracts.md:348` 与 `docs/releases/v1.0.0.md:61-62` 一致，且 28+6+15=49 |
| M6 数字 49/60 = 81.7%、逐轮 15/20、16/20、18/20 | `docs/benchmarks/m6-level2-retest4.md:38`、`:82`、`:83` 一致 |
| 窄验证 3/6、3/5 | `docs/benchmarks/m6-level2-narrow-verify3.md:59`、`:60`、`:61` 一致 |

---

## 5. 仍未关闭的清单（不代改）

第一轮遗留 **5 处**（A12、B1、B2、B3、C7），本轮新增 **1 处**（N1），合计 6 处。

### 5.1 第一轮遗留 5 处

| 编号 | 位置 | 事实 | 建议处置（供主线参考，本轮未执行） |
|---|---|---|---|
| **A12** | `docs/reports/m10-reader-package.md:272`、`:274`、`:285` | 「trace」在读者路径上出现三次且从未定义 | 在读者包 §4.1 就地加一句定义（一次模型运行落盘的记录），或指向 `docs/benchmarks/service-regression-set.md` 的对应段落 |
| **B1** | `docs/reports/m10-executive-summary.md:41` | 仍写「暖缓存约 30 秒」，与另外四份的 1.5–2 分钟矛盾 | 改成 1.5–2 分钟，或直接复用读者包 `:69` 的措辞 |
| **B2** | `docs/reports/m10-executive-summary.md:4` | 仍把读者指向 `m10-invitation-template.md` | 改指 `m10-invitation-final.md`，并照读者包 `:19-20` 补「模板只供发起人填空用」 |
| **B3** | `docs/reports/m10-executive-summary.md:25`、`:27` | 仍要求「向发起人索取固定 commit hash」，与读者包 `:50-53` 矛盾 | 改成「commit 随邀请函给出（在邀请函 §2），全程只验这一个」；`:27` 的 `git checkout <commit>` 改成 `git checkout v1.0.0` |
| **C7** | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:3`；`docs/benchmarks/m6-level2-narrow-verify2.md:3` | 仍引用从未存在的 `m6-level2-narrow-verify.md` | 改成 `-incomplete` 的真实文件名；或在读者材料里链接 `docs/reports/m10-number-traceability.md`（该文件 `:72` 已备案，但目前无人链接它） |

### 5.2 本轮新增 1 处（严重）

| 编号 | 位置 | 事实 | 建议处置（供主线参考，本轮未执行） |
|---|---|---|---|
| **N1** | `docs/reports/m10-invitation-final.md:60-63`；`v1.0.0` tag | tag 指向 `8f9ddca`（落后 25 个提交），材料却断言「即含本轮全部材料修正的版本」 | **重打 `v1.0.0` tag 指向最终 commit，并把当前树推到 `origin/main`**；在此之前邀请函不能发。同时建议邀请函 `:61-63` 的措辞改成对「当前 tag 指向何处」不假设的写法（例如由发起人填 hash 时同步更新该句），避免下次重打前再次出现同样的断言 |

### 5.3 另有一处残留（B8 的尾巴，不单列）

`docs/reports/m10-reader-package.md` 里 **A7** 与 **C4** 两个验收项编号全文未出现
（内容已覆盖，但评审者按编号查表时找不到对应行）。见 §2.2 B8 行。

---

## 6. 评审者视角的结论

**这四份材料现在还不能让一个不知情的人真的完成一次独立验收。**

原因不是材料的内在质量——**内在质量这一轮明显过关了**：40 项、19 项阻断项、
退出码 0–6、契约 49 项、38 处 `file:line` 引用、demo 计数与 sha256、
40 个 CLI 命令与参数、仓库里每一个被点名的路径，**我逐条核过，全部对得上**；
第一轮 29 条里 23 条已关闭，剩下 5 条中有 3 条集中在同一份**一页版执行摘要**
里（它被读者包 `:18` 指定为「第一次来」的首读页，却整体停在了第一轮之前）。

**最关键的缺口只有一个：评审者按材料执行 `git checkout v1.0.0`，拿到的不是这批
材料。** tag 仍指向 `8f9ddca`，落后 25 个提交，而那棵树的邀请函还在叫他
`git checkout 277d0fa`——第一轮最要命的几条（A4 钉错提交、A5 工具包不存在、
A6 退出码 0–5、A7 十个 MCP 工具、A2 M8-4 三种说法、B1/B2 三套耗时与模板指向）
在那里原样复现。材料此刻正拿一句**不成立的断言**（「即含本轮全部材料修正的
版本」）要求评审者核对 hash 并签字。

**这个缺口是可以在一次发版动作里关掉的**（重打 tag + 推 main + 改执行摘要的
4 处 + 修两份窄验证报告的 1 处文件名），但它必须在**邀请函发出之前**关掉；
发出去之后再改，评审者手上的材料与仓库里的材料就不是同一份了。

---

*本报告为只读走查产物，除新增本文件外未修改仓库任何文件；未运行
`pytest --cov` / coverage 任何命令 / `uv sync` / `scripts/refresh-report-figures.py`；
未写入共享树；未打 tag、未发 PR、未联网。*
