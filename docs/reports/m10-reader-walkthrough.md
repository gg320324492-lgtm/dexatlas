# M10 读者视角走查报告 —— 第一次看到 DexAtlas 的外部评审者会卡在哪

> **本文件的性质：** 这是一次**只读**的「读者视角走查」。作者以一位**从未参与开发**的
> 真实读者身份，把 M10 独立验收的四份材料（邀请函成稿、读者验收包、验收准备包、
> 读者工具包）与三份被验收对象（`docs/releases/v1.0.0.md`、`docs/HANDOVER.md`、
> `README.md`）通读一遍，逐条记录「一个不知情的人会卡住、看不懂或误判」的地方。
>
> **本文件只列问题，不给建议措辞，也不替主线程改材料。** 改动权在主线。
>
> **走查方法与边界（重要）：**
> - 全部结论用 `Read` / `Grep` / `git show` / `git cat-file` / `git ls-tree` / `git tag`
>   取得，**未运行 pytest、未运行 coverage、未运行 `uv sync`、未运行
>   `scripts/refresh-report-figures.py`**（主线正在共享树里跑 v1.0.0 的完整测量）。
> - 未修改仓库任何文件（本次只新增本报告）。工作副本：
>   `E:\Dexatlas\.claude\worktrees\m10-reader-walkthrough-69187f`；
>   共享树 `E:\Dexatlas` 只读。
> - **行号基准有两个**：材料文件的行号以**当前工作副本 HEAD `599ab67`** 为准；
>   凡涉及「钉定验收提交 `277d0fa` 里是什么样」的，一律用 `git show 277d0fa:<file>`
>   单独取证，并在「涉及的事实」栏注明。
> - 共享树里有**尚未提交**的发版改动（`CHANGELOG.md`、`README.md`、`README.zh-CN.md`、
>   `docs/HANDOVER.md`、`docs/status.md`、`docs/reports/m10-invitation-final.md` 等）。
>   本报告凡引用共享树版本的内容都写明「共享树未提交版」，因为**评审者 clone 到的是
>   已提交的那一份**——两者不是同一件事。
> - 凡属推断而非直接取证，一律标「**推断**」并给出推断依据。

---

## 0. 结论速览

| 类别 | 条数 | 一句话概括 |
|---|---:|---|
| 1 路径/命令失效 | 8 | 钉定提交里的邀请函指向另一个 commit；读者工具包在钉定提交里不存在；两处 `file:line` 引用打不开；一份窄验证报告引用了从未存在的文件 |
| 2 数字矛盾 | 12 | 逐轮分数两套、MCP 工具数 10/11、退出码 0–5/0–6、暖缓存 30 秒/2 分钟、版本 0.2.0/1.0.0、契约检查 46/49、自查记录的徽章数字三套 |
| 3 术语未定义 | 3 | 「B1 验收线」「trace」「预算」「确定性判分」「层级 0/1/2」「M10」 |
| 4 顺序缺失 | 3 | 执行摘要第 1 步就要找作者要 commit；邀请函要人判三级语义却不定义它 |
| 5 重复/自相矛盾 | 5 | M8-4 有三种说法；同一文件里「没有 tag」与「已打 tag」并存；中英文 README 状态相反 |
| 6 过度承诺/含糊 | 4 | 「已发布的 v1.0.0（tag 2026-11-17）」——仓库里没有这个 tag |
| 7 该有而没有 | 5 | 材料冲突时以谁为准；钉定提交上的门禁现状；自查记录属于哪棵树 |
| **合计** | **29 条独立问题**（分类计数含跨类，故分项之和 > 29） | — |

**最危险的三处**（会让评审者做出错误判断，而不是只是卡住）：

1. `docs/reports/m10-invitation-final.md:25`（共享树未提交版）——「已发布的 v1.0.0
   （tag 2026-11-17）」。`git tag -l` 只有 7 个 tag，最高 `v0.2.0`；
   `git describe --tags` = `v0.2.0-170-g599ab67`。评审者第一件事就是核对 tag，
   核不到就会认为整个项目「宣称了不存在的发布」。
2. `docs/reports/m10-acceptance-pack.md:637`（M8-4「未关闭（重要）」）对
   `docs/reports/m10-reader-package.md:297` 与
   `docs/reports/m10-reader-kit.md:273`（M8-4「已在 v1.0.0 关闭」）——
   而 `docs/reports/m10-acceptance-pack.md:157` 的 **G3 是 ★ 阻断项**，
   要评审者自己判断这个缺口「是否接受」。
3. `docs/reports/m10-invitation-final.md:45-46`（已提交版）——把「更早一次重测」的
   逐轮 **17/15/17** 写成了「最终完整重测」的逐轮数，而当前事实
   （`docs/benchmarks/m6-level2-retest4.md:28`–`:30`）是 **15/20、16/20、18/20**。

---

## A 档：会让评审者做出错误判断（12 条）

| 文件:行 | 读者的疑问或卡点（评审者口气） | 类别 | 涉及的事实是什么 | 可核实的依据 |
|---|---|---|---|---|
| `docs/reports/m10-invitation-final.md:25`（共享树未提交版）；`docs/status.md:3`、`:128`；`docs/HANDOVER.md:11-12`；`README.md:127`；`README.zh-CN.md:22`；`docs/reports/m10-acceptance-pack.md:688` | 「说 v1.0.0 已经打了 tag，可我 `git tag -l` 根本没看到 —— 是不是这份材料自己在编？」 | 6 过度承诺/含糊 + 2 数字矛盾 | 材料一致宣称「v1.0.0（tag 2026-11-17）已发布」：`status.md:3`「对应版本：v1.0.0（tag 2026-11-17）」、`status.md:128`「`v1.0.0`（tag 2026-11-17）已发布」、`HANDOVER.md:11`「The state itself is the tag **`v1.0.0`** (2026-11-17)」、`README.zh-CN.md:22`「当前状态：v1.0.0（tag 2026-11-17…）」、`acceptance-pack.md:688`「v1.0.0 已于 2026-11-17 打 tag」。仓库里没有这个 tag。 | `git tag -l` → `handover-2026-11-10 / phase1-acceptance-2026-10-21 / v0.1.0 / v0.1.1 / v0.1.2 / v0.1.3 / v0.2.0`（7 个，无 v1.0.0）；`git describe --tags` → `v0.2.0-170-g599ab67`；`git cat-file -e v1.0.0` 不存在。**推断（依据：tag 由发版动作产生，本次走查全程只读、未打 tag）**：主线很可能正处在「打 tag 之前写材料」的窗口，材料先写了 tag 事实。 |
| `docs/reports/m10-acceptance-pack.md:637`（另见 `:567`）；`docs/reports/m10-reader-package.md:297`；`docs/reports/m10-reader-kit.md:273-275` | 「M8-4 到底修没修？准备包说『未关闭』，读者包和工具包说『已关闭』——我按 ★ 项 G3 到底该判通过还是不通过？」 | 5 重复/自相矛盾 | M8-4 = 「三后端全部失败时 CLI 仍退 0」。准备包 §7 写「未关闭（重要）」、`acceptance-pack.md:567` 写「M8-2 / M8-3 / M8-4 仍未关闭」；读者包 §4.4 写「**M8-4（已在 v1.0.0 关闭）**」；工具包 FAQ Q6 写「已在 v1.0.0 由新退出码 6（`EXIT_NO_INDEX`）关闭」。而 `acceptance-pack.md:157` 的 **G3 是 ★ 阻断项**，要求评审者「核对 M8-4 的退出码缺口…记录是否接受及其边界」。事实层面退出码 6 已落地（见下一行）。 | `git show 277d0fa:src/dexatlas/cli/main.py` → `:135 EXIT_NO_INDEX = 6`、`:387-389` 已在用；`docs/architecture/public-contracts.md:64` 与 `docs/install.md:226`（退出码表第 6 行）都已写 6；`docs/status.md:135` 写「M8-4…已按 `docs/proposals/exit-code-partial-read.md` 提案修复…（1f6ef05）」。**同时**：准备包 §2.8 与 `reader-kit.md:328` 规定「两者冲突时以准备包为准」，于是「以准备包为准」的答案（未关闭）与代码事实（已修）正好相反。 |
| `docs/reports/m10-invitation-final.md:45-46`（已提交版 `599ab67`） | 「邀请函说最终重测逐轮 17/15/17，可 retest4 报告写的是 15/16/18 —— 邀请函这一句是拿旧数据冒充当前事实吧？」 | 2 数字矛盾 | 邀请函写「最终完整重测 DexAtlas 49/60 = 81.7%，逐轮 **17/15/17**」。当前事实是 retest4 逐轮 15/20、16/20、18/20；17/15/17 是**更早一次**重测（retest3）的逐轮数。同一批材料的其他两份都写对了：准备包 `:544`、`:639` 写「逐轮 15/16/18」，工具包 `:232-233`、`:313-316` 写「15/20、16/20、18/20」并把 17/15/17 明确标为「更早一次重测」。共享树未提交版已改对（`invitation-final.md:45-47`），但**未提交 = 评审者 clone 到的分支上没有**。 | `git show 277d0fa:docs/benchmarks/m6-level2-retest4.md` `:28-30` → `r1 15/20 / r2 16/20 / r3 18/20`；`:82` 逐轮判定；`:38` → `DexAtlas 49/60 81.7%`。`git show 277d0fa:docs/benchmarks/m6-level2-retest3.md` `:29-31` → `r1 17/20 / r2 15/20 / r3 17/20`；`:85` 逐轮判定。`grep -rn "17/15/17" --include="*.md"` 全仓库只在 `docs/status.md`（未提交版）出现，**已提交的 README 与发版说明里都没有这个数** —— 评审者核对时会在别处找不到出处。 |
| `docs/reports/m10-reader-package.md:9-10`、`:74`；`docs/reports/m10-acceptance-pack.md:188-189`、`:196` | 「让我执行 `git checkout <验收发起人钉定的 commit>` —— 这个尖括号是要我自己去问发起人吗？可材料说不要向作者要任何步骤。」 | 1 路径/命令失效 + 2 数字矛盾 | 两份主材料仍写占位符：读者包 `:9-10`「验收 commit：**由验收发起人钉定并告知**（待项目里程碑定稿后确定…）」、`:74` 命令块 `git checkout <验收发起人钉定的 commit>`；准备包 `:188-189`「（待项目里程碑定稿后确定并告知 hash）」、`:196` 同一占位符命令。而邀请函 `:57`、`:92`、`:163` 与工具包 `:9`、`:163`、`:203` 已经钉死 `277d0fa`。**更麻烦的是**：`git show 277d0fa:docs/reports/m10-invitation-final.md:57` 写的是 **`commit e4f3011`**（`e4f3011` 是 `277d0fa` 的祖先，落后 4 个提交）—— 也就是说评审者若按钉定提交里那份邀请函做，会 checkout 另一个提交。 | `git show 277d0fa:docs/reports/m10-invitation-final.md` → `:57` `commit e4f3011`、`:62` `git checkout e4f3011`；`git merge-base --is-ancestor e4f3011 277d0fa` → 真，`git rev-list --count e4f3011..277d0fa` → 4。工作副本 HEAD `599ab67` 的邀请函 `:57` 已是 `277d0fa`；共享树未提交版也是 `277d0fa`。 |
| `docs/reports/m10-reader-kit.md:9-10`（整份文件） | 「邀请函让我只验 `277d0fa`，可我 checkout 完发现根本没有『读者工具包』这个文件 —— 评分表、FAQ、回填说明去哪了？」 | 1 路径/命令失效 | 读者工具包自称「只装三样东西：评分表、回填说明、常见问答」（`reader-kit.md:5-7`），并在 `:9` 自称「验收 commit：**277d0fa**」，但这份文件本身是在 `277d0fa` **之后**才加进来的。钉定提交里的读者包也没有指向它。 | `git cat-file -e 277d0fa:docs/reports/m10-reader-kit.md` → 不存在（`fatal: path … exists on disk, but not in '277d0fa'`）。`git show 277d0fa:docs/reports/m10-reader-package.md` 全文无 `reader-kit` 字样；`grep -n "reader-kit" docs/reports/m10-reader-package.md` 只在**当前**版本的 `:411` 出现。另：`git ls-tree --name-only main -- docs/reports/` 只有 `m10-reader-package.md`，**没有** `m10-invitation-final.md`、没有 `m10-reader-kit.md` —— 评审者 clone 默认分支看不到邀请函成稿与工具包。 |
| `docs/reports/m10-acceptance-pack.md:144`（`277d0fa` 版） | 「F1 说 CLI 只有 0–5 六个退出码，可我真的跑出了 6 —— 是代码错了还是判据错了？」 | 2 数字矛盾 + 4 顺序缺失 | 钉定提交里的 F1 判据：「CLI 退出码：0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、5 截断」；读者包 `:225` 同。退出码 6 是 v1.0.0 新增（`EXIT_NO_INDEX`）。代码与其它两份文档在钉定提交上**已经**是 6。 | `git show 277d0fa:src/dexatlas/cli/main.py:135` → `EXIT_NO_INDEX = 6`；`git show 277d0fa:docs/install.md` 退出码表 `:226` 有 `\| 6 \| The analysis finished, but no symbol index could be built…`；`git show 277d0fa:docs/architecture/public-contracts.md:54` 退出码表有第 6 行。当前 HEAD `:144` 已补上「6 跑完但无可用的代码索引（`EXIT_NO_INDEX`，v1.0.0 新增）」。 |
| `docs/reports/m10-acceptance-pack.md:146`（`277d0fa` 版） | 「F3 说 MCP 工具是契约表的 10 个，可我数出来是 11 个 —— 这是契约漂移吗？」 | 2 数字矛盾 | 钉定提交里的 F3 判据：「MCP：工具清单为契约表的 **10 个**，全部只读注解」；实际代码注册了 11 个工具，公共契约表 §3.1 也列 11 个。当前 HEAD 的 `:146` 已改为 11。 | `git show 277d0fa:src/dexatlas/mcp/server.py \| grep -c "@server.tool"` → **11**；`git show 277d0fa:docs/architecture/public-contracts.md` §3.1 工具表 `:205`–`:220` 列 11 行；`git show 277d0fa:docs/architecture/public-contracts.md:385` 写「恰为 §3.1 的十一个名字」。 |
| `README.md:32` 与 `README.zh-CN.md:22`（均为共享树未提交版） | 「英文 README 说自己还是『早期开发、v0.2.0 已发布』，中文 README 说自己已经是 v1.0.0 —— 到底哪个是真的？」 | 2 数字矛盾 | 被验收对象之一的两份 README 在**同一次发版改动里**状态相反：英文 `:32`「Status: early development (v0.2.0 released; Phase 3 in progress)…」；中文 `:22`「当前状态：v1.0.0（tag 2026-11-17，见发版说明）」。钉定提交上两者是一致的（「早期开发 / early development」，`README.md:32` 与 `README.zh-CN.md:22`），是这轮未提交的发版改动把中文版单独推到了 v1.0.0。 | `git status --short`（共享树）→ `M README.md`、`M README.zh-CN.md`；`sed -n '32p' README.md` → `> **Status: early development (v0.2.0 released; Phase 3 in progress).**`；`sed -n '22p' README.zh-CN.md` → `> **当前状态：v1.0.0（tag 2026-11-17，见发版说明）。**` |
| `docs/reports/m10-invitation-final.md:25` 与 `docs/reports/m10-acceptance-pack.md:625`、`:657`、`:659` | 「按准备包自己的退出门槛表，M10 现在一定不通过（『未关闭（M8-2/3/4 等）』『未推进：无 tag』）—— 那这轮验收请我来做什么？」 | 6 过度承诺/含糊 + 7 该有而没有 | 准备包 §8 退出门槛对照表自己写着未达成：`:653`「所有阻断项关闭；重要遗留项有边界与接受理由 → 未关闭（M8-2/3/4 等）」、`:657`「完成源码评审和验收后才推进阶段/准备 tag → 未推进：无 tag」、`:659`「独立验收尚未执行，M10 未完成」。而邀请函 `:25`（共享树版）说的是「已发布的 v1.0.0 … 做独立验收」、`:40` 把 40 项检查表当作待办清单。材料没有一句话解释「这轮验收就是用来关闭这些遗留的」还是「这些遗留已经被接受」。 | `sed -n '653p;657p;659p' docs/reports/m10-acceptance-pack.md`；`sed -n '25p' docs/reports/m10-invitation-final.md`（共享树）；`sed -n '40p;44-49p' docs/reports/m10-invitation-final.md`。 |
| `docs/reports/m10-reader-kit.md:328` 对 `docs/reports/m10-acceptance-pack.md:38-40` | 「两份材料打架的时候到底听谁的？规则自己就有两条，而且指向不同答案。」 | 7 该有而没有 | 工具包 §5 末：「两者冲突时以准备包为准」（指工具包 vs 准备包）；准备包 §0「不是什么」：「与[公共契约表]、[服务回归集]、[M8 安装演练]等冲突时，**以原始证据和代码为准**」。当**准备包本身**与代码冲突时（退出码 6、MCP 工具数、M8-4），这两条规则给出相反答案，而材料没有第三条规定。 | `sed -n '328p' docs/reports/m10-reader-kit.md`；`sed -n '38,40p' docs/reports/m10-acceptance-pack.md`。 |
| `docs/reports/m10-acceptance-pack.md:544`、`:639`；`docs/reports/m10-reader-package.md:268` | 「『B1 验收线未达』『B1 未关闭』—— B1 是什么？它跟表里那个 B1 验收项是一回事吗？」 | 3 术语未定义 | 「B1」在验收材料里有**两个互不相干的含义**：(a) 验收项编号 B1 = 「按案例从 analyze 走到 xrefs 全程完成」（★ 阻断项，`acceptance-pack.md:97`、`:166`）；(b) M6 的「B1 验收线 / B1 未关闭」，指真实模型批次的验收线。而材料把被验收对象指向的 `docs/roadmap/phase3-plan.md` 里**没有** B1 这个标签，M6 的判据实际写在 `service-regression-set.md §5` 与 `phase3-plan.md §5 M6`（每轮 ≥16/20、三轮合计 ≥54/60）。 | `grep -n "B1\|B2\|B3" docs/roadmap/phase3-plan.md` → 无匹配；`grep -rn "B1 验收" docs/` → 只有 `acceptance-pack.md:544`、`:639` 与 `docs/benchmarks/m6-level2-retest4.md:3`（「B1 验收测量」）；`docs/benchmarks/m6-level2-retest4.md:3` 自己写「验收线来自 [service-regression-set.md] §5 与 [phase3-plan.md] §5 M6（每轮 ≥16/20，三轮合计 ≥54/60）」——与「B1」这个标签无关。 |
| `docs/reports/m10-invitation-final.md:1`、`:29`、`:36`、`:102`；`docs/reports/m10-acceptance-pack.md:527-529`；`docs/reports/m10-reader-package.md:290`、`:293` | 「邀请函要我核对 evidence 的 `level` 字段是不是三级语义，可这三个词整份邀请函里一次都没出现过。」 | 4 顺序缺失 + 3 术语未定义 | 邀请函从头到尾没有 `verified`/`lead`/`insufficient` 这三个词（`grep` 无匹配），但它要求评审者判断「事实与线索能否区分」（`:36`）、并「任选 3 条 evidence 记录核对工具、版本、locator、level 四字段」（`:102`），而 C3 是 ★ 阻断项（`acceptance-pack.md:110`）。另外三个术语同样没有就地解释：`trace`（准备包 `:527-529`「指标能否从 trace 重算」，而 §4 明说客户视角审阅者「不需要读 Python」）、`预算`（读者包 `:293`「确认预算差异已被披露而不是隐去」，指 token 预算/题预算）、「确定性判分」（读者包 `:290`、准备包 `:128`「层级 0 确定性判分 20/20」）。 | `grep -n "verified\|lead\|insufficient" docs/reports/m10-invitation-final.md` → 无匹配；`grep -n "verified\|lead\|insufficient" docs/reports/m10-reader-kit.md` → **无匹配**（工具包是「评分/回填/FAQ」三件套，但一个 `verified` 都没有）；定义实际在 `docs/reports/m10-reader-package.md:170-172`、`docs/reports/m10-acceptance-pack.md:384-388`、`docs/architecture/public-contracts.md:259`。 |

## B 档：会让评审者卡住或无法复现（8 条）

| 文件:行 | 读者的疑问或卡点（评审者口气） | 类别 | 涉及的事实是什么 | 可核实的依据 |
|---|---|---|---|---|
| `docs/reports/m10-reader-package.md:379`（另见 `:63`）；`docs/reports/m10-reader-kit.md:176`；`docs/reports/m10-executive-summary.md:41`；`docs/reports/m10-invitation-final.md:80` | 「暖缓存到第一份报告到底是 30 秒、1.5 分钟还是 2 分钟？我按 30 秒做完花了 2 分钟，算不算卡点？」 | 2 数字矛盾 | 同一个量有四种说法：读者包 §5.4「暖缓存约 **30 秒**」、读者包 §2 表「约 **2 分钟**」、工具包「约 **2 分钟**」、执行摘要「暖缓存约 **30 秒**」、邀请函「约 **1.5–2 分钟**」。读者包 §5.4 就在同一文件的 §2 表下面 300 行。 | `sed -n '63p;379p' docs/reports/m10-reader-package.md`；`sed -n '176p' docs/reports/m10-reader-kit.md`；`sed -n '41p' docs/reports/m10-executive-summary.md`；`sed -n '80p' docs/reports/m10-invitation-final.md`。 |
| `docs/reports/m10-reader-package.md:16`；`docs/reports/m10-executive-summary.md:4` | 「『第一次来？先看…』后面那个链接点开是**邀请函模板**，里面还写着『待钉定』—— 我该看哪一份？」 | 1 路径/命令失效 | 读者包首页把读者引到 `m10-invitation-template.md`（模板），不是 `m10-invitation-final.md`（成稿）。模板里保留了「待钉定」表述（`invitation-final.md:3-6` 明说本稿「与邀请函模板不同，本稿钉定了验收 commit，不再保留『待钉定』表述」）。执行摘要 `:4` 同样指向模板。 | `sed -n '16p' docs/reports/m10-reader-package.md` → 「邀请与独立性要求见「验收邀请函」（指向 `m10-invitation-template.md`）」；`sed -n '4p' docs/reports/m10-executive-summary.md` → 同。`git show 277d0fa:docs/reports/m10-invitation-template.md` 存在且为模板态。 |
| `docs/reports/m10-executive-summary.md:25-27` 对 `docs/reports/m10-reader-package.md:6`、`:42-43` | 「执行摘要第 1 步就是『领 commit：向发起人索取固定 commit hash』，可读者包第 0 节说『从这里出发，不需要再向作者要任何步骤』，第 1 节还说靠作者口头补充走通的步骤要判不通过 —— 我卡在第一步了。」 | 4 顺序缺失 + 5 重复/自相矛盾 | 执行摘要 5 步的第 1 步是向发起人索取 hash；而读者包承诺零求助、独立性守则把「靠作者口头补充才走通的步骤」定为相关项不通过。 | `sed -n '25,27p' docs/reports/m10-executive-summary.md`；`sed -n '6p;42,43p' docs/reports/m10-reader-package.md`。 |
| `docs/reports/m10-reader-kit.md:275`（引 `docs/reports/m10-reader-package.md:293`）；`docs/reports/m10-reader-kit.md:168`（引 `docs/reports/m10-invitation-final.md:136`） | 「工具包给的『证据出处』点开对不上 —— 它说退出码 6 的出处是 reader-package:293，可 293 行讲的是预算。」 | 1 路径/命令失效 | 两处 `file:line` 引用错位：`reader-kit.md:275` 把 `reader-package.md:293` 当作 M8-4/退出码 6 的出处，实际内容在 `reader-package.md:297-299`（`:293` 是「通过率引用；确认预算差异已被披露而不是隐去」）；`reader-kit.md:168` 把 `invitation-final.md:136` 当作脱敏条款出处，实际在 `:138`（`:136` 是「回传方式：直接回填模板文件即可」）。评审者被要求核对「每一分都有证据」，引用打不开正好撞在 §5.4 第 1 条阻断项（证据链断裂）上。 | `sed -n '293p' docs/reports/m10-reader-package.md`；`sed -n '297,299p' docs/reports/m10-reader-package.md`；`sed -n '136p;138p' docs/reports/m10-invitation-final.md`。对照：工具包其余引用（`acceptance-pack.md:442`、`:166`、`:61`、`:87`、`:85`、`reader-package.md:55`、`:63`、`:13`、`invitation-final.md:131`、`m6-level2-retest4.md:38`/`:82`、`m6-level2-retest3.md:85`、`m6-level2-narrow-verify3.md:59`）我逐条核对**全部命中**。 |
| `docs/reports/m10-acceptance-pack.md:205-207` 对 `docs/install.md:17-43` | 「准备包说 install.md 的安装节和推荐组合不一致，可我打开 install.md，安装节明明写的就是四 extras 的 `uv sync` —— 是我漏了哪一段？」 | 5 重复/自相矛盾（过期） | 准备包 §3.2 有一条「**已知文档不一致（M8-3）**：install.md 的安装节写的是 `uv venv` + `uv pip install -e ".[analysis]"`」。但 install.md 的 `## Install` 段现在**先**给四 extras 的 `uv sync`（`:25`），再把 `uv venv` + `uv pip install -e ".[analysis]"` 明确降级为「For the CLI and the REST API alone, the smaller route is enough」（`:39-43`）。`docs/status.md:135` 也说 M8-3「**已修复并合入**（d90baff）」。 | `git show 277d0fa:docs/install.md` `:17` `## Install`、`:19` 「The full route — all four extras, installed from the lockfile:」、`:25` `uv sync --extra dev --extra analysis --extra mcp --extra demo`、`:39` 「For the CLI and the REST API alone, the smaller route is enough:」、`:42-43` `uv venv --python 3.12` / `uv pip install -e ".[analysis]"`。`git show 277d0fa:docs/status.md:135` → 「M8-2…与 M8-3…**已修复并合入**（d90baff…）」。 |
| `docs/reports/m10-acceptance-pack.md:567`、`:635`、`:636` 对 `docs/status.md:135` | 「M8-2、M8-3 在准备包 §7 里还是『未关闭』，status.md 却说『已修复并合入』—— 我按哪张表扣分？」 | 5 重复/自相矛盾 | 准备包 §7 表：M8-2「未关闭」、M8-3「未关闭」，`:567`「M8-2 / M8-3 / M8-4 仍未关闭」，`:653` 退出门槛「未关闭（M8-2/3/4 等）」；而 `docs/status.md:135` 写「M8-2（查询命令缺 `--workspace`）与 M8-3（install.md 的 extras 组合不一致）**已修复并合入**（d90baff，全命令 `--workspace/-w`、install.md 修正）」。M8-4 一项则三份材料三种说法（见 A 档第 2 条）。 | `sed -n '567p;635,636p' docs/reports/m10-acceptance-pack.md`；`git show 277d0fa:docs/status.md:135`（截取 M8 那一行）。**推断（依据：`d90baff` 被 status.md 指为修复提交，prepare-pack 自身在该提交之后未更新）**：准备包 §7 是修复合入前写的。 |
| `docs/reports/m10-acceptance-pack.md:602-613` | 「这页门禁现状写着 3 项失败、5 项失败 —— 我在 `277d0fa` 上跑一遍到底该期望通过还是失败？」 | 7 该有而没有 | §6.3「**编写本包时的门禁现状（2026-11-15，基准 `ff5c4cc`）**」：`check-version-claims.py --base auto` **失败**（3 项既有声明与仓库事实不符：README 徽章、v0.2.0 发布说明覆盖率、CHANGELOG 引用）、`tests/test_docs.py` 全量 **5 项失败**。材料同时要求评审者在最终 commit 上跑同一批命令（`:585-592`），但没写「在 `277d0fa` 上现状如何」，也没写「读者看到失败该记不通过还是未验证」。 | `sed -n '602,613p' docs/reports/m10-acceptance-pack.md`。旁证：三个版本的 README 徽章分别是 `main`=tests 1515 / coverage 93.2%、`277d0fa`=tests 1584 / coverage 93.2%、共享树未提交版=tests 1588 / coverage 93.3%（`git show main:README.md:12-13`、`git show 277d0fa:README.md:12-13`、`sed -n '12,13p' README.md`）——徽章确实随树变动，所以「3 项失败」必然是特定某一棵树的账。 |
| `docs/reports/m10-reader-package.md:146`（另见 `:84`、`:128`、`:178`、`:191`） | 「第 4 步标题写着『验收项 A3–A5』，可 A5 是三格式报告（A/D 组），怎么跑在第 4 步里了？」 | 1 路径/命令失效 | 读者包各步与验收项的对应在标题里互相错位：`:146`「### 3.4 第 4 步：检索、证据与 locator 解析（验收项 A3–A5、B3–B4、C1–C3）」——而 A3 落在 `:84` 第 2 步、A4 落在 `:133` 第 3 步、A5 落在 `:181` 第 5 步；`:191` 第 6 步标「C5–C6、D3–D5、G5」，`:210` 第 7 步标「B1–B6」。 | `grep -n "^### 3\." docs/reports/m10-reader-package.md` → `:80`（A2、A3）、`:128`（A4）、`:146`（A3–A5、B3–B4、C1–C3）、`:178`（A5、D1–D2）、`:191`（C5–C6、D3–D5、G5）、`:210`（B1–B6）、`:223`（E、F）。 |
| `docs/reports/m10-selfcheck.md:11`、`:44`、`:92-94`（读者包 `:7` §自查脚本、执行摘要 `:55-59` 都指向它） | 「自查记录说徽章是 tests 1478 / coverage 91.9%、退出码 0–5，可我检出 `277d0fa` 跑出来是 1584 / 93.2%、退出码有 6 —— 这份记录到底说的是哪棵树？我重跑结果和它不一样，算失败吗？」 | 2 数字矛盾 + 7 该有而没有 | 自查记录 `:11` 自报「执行日期：2026年11月16日 · commit：`bb50635`（main）」——那是 `277d0fa` 的**祖先、落后 83 个提交**的树。它记录的数字（`:92` README 徽章 tests 1478 / coverage 91.9%；`:93` `tests.total = 1332 + 146`；`:44`、`:94`「退出码 0–5」）与 `277d0fa`（1584 / 93.2%，退出码 0–6）和共享树（1588 / 93.3%）**都不一致**。而 `docs/status.md:137` 把这份记录当作当前状态引用（「`m10-selfcheck.md`，40/40 通过」），读者包 §7 与执行摘要也都把它当作「你也可以重跑」的对照物。脚本本身没问题（`scripts/m10_selfcheck.py:417-457` 动态读 `EXPECTED_EXIT_CODES`），过时的是文档散文与 `scripts/m10_selfcheck.py:719` 那行「0–5 语义已静态核对」的标签。 | `git log -1 --format='%h %ad %s' bb50635` → `2026-11-16 修复 --configuration no-* 任务集路由缺口`；`git rev-list --count bb50635..277d0fa` → **83**；`git show bb50635:README.md:12-13` → `tests-1478 passing` / `coverage-91.9%`（与 `:92` 完全对上，证明这份记录只对 `bb50635` 那棵树成立）；`git show 277d0fa:README.md:12-13` → `tests-1584` / `coverage-93.2%`；`sed -n '12,13p' README.md`（共享树）→ `tests-1588` / `coverage-93.3%`；`sed -n '11p;44p;92,94p' docs/reports/m10-selfcheck.md`。**材料没有任何一句说「这份自查记录属于 `bb50635`，不是验收提交」。** |
| `docs/releases/v1.0.0.md:61-62`（被验收对象）对 `scripts/verify-public-contracts.py` | 「发版说明说契约实测 46/46（26 REST + 6 MCP + 14 CLI），可 F6 让我跑这个脚本，跑出来的检查项比 46 多 —— 发版说明的数字和脚本对不上。」 | 2 数字矛盾 | 发版说明：「the public contract table frozen with **46/46** live checks (26 REST + 6 MCP + 14 CLI)」。契约表 §7.1/§7.2/§7.3 逐字写「26/26」「6/6」「14/14 通过」，并标注测量日期「2026年11月15日」。但脚本在 2026-11-16 随退出码 6 加了第 15 个 CLI 检查，现在静态可数 **28 REST + 6 MCP + 15 CLI = 49**（REST 里有 2 个条件调用点，无源码后端的机器上是 26，合计 47）。而 `acceptance-pack.md:149` 的 **F6 验收项**要求评审者「`scripts/verify-public-contracts.py` 退出码 0，逐项 PASS」——跑出来的分母与发版说明的数字不符。 | `sed -n '66,341p' scripts/verify-public-contracts.py \| grep -c "check("` → 28；`:342,415` → 6；`:416,$` → 15；`:571` → `check("an analysis with no index exits 6", result.exit_code == 6, …)`。`git show 277d0fa:docs/architecture/public-contracts.md` `:351`、`:381`、`:395` → 「26/26 通过」「6/6 通过」「14/14 通过」，均在「2026年11月15日」标题下。**推断（依据：该检查由退出码 6 的提交 `1f6ef05` 引入，而契约表的测量日期是 11-15）**：46 是 11-15 的快照，脚本已增长；发版说明沿用了旧快照。 |

## C 档：影响材料可信度、但不改变判定（6 条）

| 文件:行 | 读者的疑问或卡点（评审者口气） | 类别 | 涉及的事实是什么 | 可核实的依据 |
|---|---|---|---|---|
| `docs/architecture/public-contracts.md:327` | 「公共契约表自己写着『当前 0.2.0』，可我验的是 v1.0.0 —— 契约表是不是没跟着发版走？」 | 2 数字矛盾 | 契约表 §6 写「（当前 `0.2.0`）；打包经 hatch 从该文件读取（`pyproject.toml:145-146`）」。共享树未提交版 `src/dexatlas/__init__.py:11` 已改成 `__version__ = "1.0.0"`，但契约表没改（`git status` 里 `docs/architecture/` 未被修改）。 | `sed -n '327p' docs/architecture/public-contracts.md`；`sed -n '11p' src/dexatlas/__init__.py`（共享树）→ `__version__ = "1.0.0"`；`git show 277d0fa:src/dexatlas/__init__.py:11` → `__version__ = "0.2.0"`。 |
| `src/dexatlas/__init__.py:11`（`277d0fa` 版）对 `docs/releases/v1.0.0.md:1`（同一提交） | 「我在钉定提交上装出来 `dexatlas --version` 说 0.2.0，可这个提交里的发版说明标题写着 DexAtlas v1.0.0 —— 我到底在验哪个版本？」 | 2 数字矛盾 | 钉定提交 `277d0fa` 同时含：版本号 `0.2.0` 的源码，与标题为「DexAtlas v1.0.0 — The Evidence-First Portfolio Milestone」的发版说明（`:8` 还写着「a new exit code for runs that indexed nothing」）。版本号要到共享树未提交的那次改动才升到 1.0.0。 | `git show 277d0fa:src/dexatlas/__init__.py:11`；`git show 277d0fa:docs/releases/v1.0.0.md:1`、`:8`；`git diff 277d0fa -- src/dexatlas/__init__.py` → `__version__` 由 `0.2.0` 改为 `1.0.0`（共享树未提交）。 |
| `docs/reports/m10-acceptance-pack.md:489` 对 `docs/reports/m10-reader-package.md:11-13`；`docs/reports/m10-reader-kit.md:276-277` | 「基线到底是 75%/65% 还是 77.5%/68.75%？我打完分该跟哪一档比？」 | 2 数字矛盾 | 准备包 §5.4 只说「基线是 GitHub 约 75%、Upwork 约 65%」；读者包首页同时给出两档（准备度评估 75%/65% 与复评 77.5%/68.75%）；工具包 §5 说「准备度评估与复评里的 75%/65% 与 77.5%/68.75%——**作者自评**，是重评的基线，不是成绩」，但没说两档之间是什么关系、以及评分表该跟哪一档对齐。 | `sed -n '489p' docs/reports/m10-acceptance-pack.md`；`sed -n '11,13p' docs/reports/m10-reader-package.md`；`sed -n '276,277p' docs/reports/m10-reader-kit.md`；`sed -n '41p' docs/reports/m10-reader-kit.md`（「改了权重，分数就与 75% / 65% 的基线不可比」）。 |
| `docs/reports/m10-reader-kit.md:180` | 「一个 Python 项目的耗时说明里为什么让我考虑 `npm install`？这份材料是不是没改干净？」 | 6 过度承诺/含糊 | 工具包 §3.3「慢不一定是卡点：后端下载、JDK 首次安装、`npm install` 都是一次性开销」。仓库是 Python 项目，没有 npm 依赖（`pyproject.toml` 只有 uv extras）。 | `sed -n '180p' docs/reports/m10-reader-kit.md`；`grep -n "npm\|node" pyproject.toml` → 无匹配。 |
| `README.md:127` 对 `README.md:538`（共享树未提交版） | 「里程碑表说 `v1.0.0` 已经打了 tag，可同一份 README 末尾又说只有退出标准全过才考虑 v1.0.0 —— 这两条能同时成立吗？」 | 5 重复/自相矛盾 | `README.md:127` 的里程碑表第三行写「**3** / `v1.0.0` (tag 2026-11-17) / Portfolio & Delivery / … / independent acceptance (pack ready, not run)」；`README.md:538` 却写「`v1.0.0` is considered only after this plan's exit criteria pass — phases advance on evidence…」。而 `docs/status.md:128` 同时说「Phase 3 的退出标准未全部达成…`v1.0.0`（tag 2026-11-17）已发布」。钉定提交上 README `:127` 还写的是 `v1.0.0` **(planned)**。 | `sed -n '127p;538p' README.md`（共享树）；`git show 277d0fa:README.md:127` → 「`v1.0.0` (planned)」；`sed -n '128p' docs/status.md`（共享树）。 |
| `docs/reports/m10-reader-kit.md:6-7`、`:9-10`（与 `docs/reports/m10-acceptance-pack.md:10-12`） | 「材料自己写着『编写基准：`ff5c4cc`（本文件在独立分支提交）』—— 那我核对的到底是哪一棵树？每份材料的基准都不一样。」 | 7 该有而没有 | 四份材料的基准各不相同：准备包 `:10-11`「编写基准：`ff5c4cc`（本文件在独立分支提交）」；读者包 `:9-10`「编写日期 2026-11-16（2026-11-17 定稿）」；工具包 `:9`「验收 commit：**277d0fa**」；邀请函 `:57`「commit 277d0fa」。材料没有一份「材料版本 ↔ 仓库 commit」的对照表，评审者只能逐份猜。 | `sed -n '10,11p' docs/reports/m10-acceptance-pack.md`；`sed -n '9,10p' docs/reports/m10-reader-package.md`；`sed -n '9p' docs/reports/m10-reader-kit.md`；`sed -n '57p' docs/reports/m10-invitation-final.md`。 |
| `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:3`；`docs/benchmarks/m6-level2-narrow-verify2.md:3` | 「按窄验证的证据链去找 `m6-level2-narrow-verify.md`，仓库里没有这个文件 —— 第一轮的窄验证报告到底在哪？」 | 1 路径/命令失效 | 两份窄验证报告都引用了一个**从未存在过**的文件名 `m6-level2-narrow-verify.md`：`:3`「It does not replace `m6-level2-narrow-verify.md`；the full report script refuses to write a report for fewer than 54 traces」、`m6-level2-narrow-verify2.md:3`「验证首轮窄验证（`m6-level2-narrow-verify.md`）之后的四项修复」。真实产物是 `m6-level2-narrow-verify-incomplete.md`。两处都是行内 code span 而非 Markdown 链接，所以链接检查器不会报错，但读者按线索去开一定 404。 | `git log --all --oneline -- 'docs/benchmarks/m6-level2-narrow-verify.md'` → 空（任何分支都没有）；`git ls-tree -r --name-only 277d0fa -- docs/benchmarks/ \| grep narrow-verify` → 只有 `-incomplete`、`-2`、`-3`。仓库自己的 `docs/reports/m10-number-traceability.md:69` 已把这条记为「不存在」并给出替代路径——但那份文件在 `277d0fa` 上还没有（`git cat-file -e 277d0fa:docs/reports/m10-number-traceability.md` → 不存在），评审者看不到这份排查。 |

---

## 1. 七类逐类小结（评审者口气）

1. **路径/命令失效（8 条）** —— 最疼的是「钉定提交里的邀请函指向 `e4f3011`」（A 档第 4 条）和
   「读者工具包不在 `277d0fa` 里」（A 档第 5 条）。这两条合起来意味着：**评审者严格照材料
   执行，会在一个错误提交上、用一套不存在的工具包**。另外两处 `file:line` 打不开
   （`reader-kit.md:275`、`:168`）会被评审者直接读成「引用不可解析」；还有一处窄验证报告
   引用了从未存在的 `m6-level2-narrow-verify.md`。
2. **数字矛盾（12 条）** —— 逐轮分数、退出码、MCP 工具数、暖缓存时长、版本号、
   契约表版本、基线分数、tag 存在与否、契约实测 46 vs 49、自查记录的徽章数字三套。
   **共同的形状是「同一件事在已提交版与未提交版不一样」**：`277d0fa` 的材料与 `277d0fa`
   的代码也对不上（退出码 6、MCP 11 个）。评审者拿到哪一份，取决于他 clone 的是哪个分支。
3. **术语未定义（3 条）** —— 「B1 验收线」是撞得最狠的一个：它在准备包和读者包里被当成
   一个已知的判据反复引用，而被指向的 `phase3-plan.md` 里根本没有 B1；同一个文档里 B1
   又是一条 ★ 验收项。`trace`/`预算`/`确定性判分`/`层级 0-1-2`/`M10` 都没有就地解释。
4. **顺序缺失（3 条）** —— 执行摘要第 1 步就要向作者要 commit（与「不需要再向作者要任何
   步骤」直接冲突）；邀请函要人判三级语义却一次都没写过这三个词；工具包（专门解释
   术语的 FAQ）里 `verified`/`lead`/`insufficient` 出现 0 次。
5. **重复/自相矛盾（5 条）** —— M8-4 三种说法；准备包一份文件内「没有 tag」（`:625`、`:657`）
   与「已打 tag」（`:688`）并存；中英文 README 状态相反；M8-3 的「已知不一致」已不存在。
6. **过度承诺/含糊（4 条）** —— 头号是「已发布的 v1.0.0（tag 2026-11-17）」而 tag 不存在；
   其次是准备包 §8 自己写着退出门槛未达成；再次是 `npm install` 这类没改干净的模板残留。
7. **该有而没有（5 条）** —— 最缺的一条：**材料冲突时以谁为准，有两条互相冲突的规则**
   （`reader-kit.md:328` vs `acceptance-pack.md:38-40`），且没说材料与**被验收对象**
   （README / 发版说明 / status.md）冲突时怎么办。其余是：钉定提交上的门禁现状、
   材料各自的基准 commit、自查记录属于哪一棵树、失败后怎么办（只有「问发起人」，
   没有「判不通过」的收尾路径）。

---

## 2. 顺带核实：材料里提到的东西是不是真的存在

**真实存在（已逐一取证）：** `examples/demo-app/demo.apk`；`docs/case-studies/` 三个案例
及其 9 个附件（`demo-report.md/json/html`、`demo-evidence-package.zip`、
`obfuscated-report.md/json/html`、`obfuscated-evidence-package.zip`、
`api-integration-evidence-package.zip`）；`docs/assets/demo.mp4`、`demo.gif`、
`demo-quick.gif`；`docs/architecture/public-contracts.md`、`docs/install.md`、
`docs/proposals/exit-code-partial-read.md`；`docs/benchmarks/` 下的
`m6-level2-retest3.md`、`m6-level2-retest4.md`、`m6-level2-narrow-verify3.md`、
`m6-level2-real.md`、`m6-level1-scripted.md`、`service-regression-set.md`；
`scripts/verify-public-contracts.py`、`scripts/m10_selfcheck.py`、
`scripts/check-doc-citations.py`、`scripts/check-version-claims.py`；
`tests/test_public_contracts.py`、`tests/test_docs.py`、`tests/test_html_report.py`、
`tests/test_evidence_package.py`；`docs/reports/m10-selfcheck.md`、
`m10-review-record-template.md`、`portfolio-readiness-2026-11-15.md` 与其 `-recheck.md`。

**在钉定提交里不存在：** `docs/reports/m10-reader-kit.md`（A 档第 5 条）；
`docs/benchmarks/m6-level2-narrow-verify.md`（**任何分支都没有**，C 档最后一条）。

**在 `main` 上不存在（评审者 clone 默认分支会看不到）：** `docs/reports/m10-invitation-final.md`、
`docs/reports/m10-reader-kit.md`。`main` 上有 `m10-reader-package.md`、
`m10-acceptance-pack.md`、`m10-executive-summary.md`、`m10-invitation-template.md`、
`m10-review-record-template.md`、`m10-selfcheck.md`。

**数字核对通过（未发现问题）：** 40 个验收项 = 40 行（`grep -cE '^\| (A|B|C|D|E|F|G)[0-9]+ \|'`），
★ 阻断项 = 19 个（`:166` 的清单与表格逐行一致）；两份评分表（准备包 §5.2/§5.3 与工具包
§2.2/§2.3）逐字一致，权重与「准备度评估表」一致；`docs/status.md:137` 说的
「`m10-selfcheck.md`，40/40 通过」在 `m10-selfcheck.md:84-86` 有对应记录（「通过 40，失败 0，
需人工 40」）—— 但那份记录属于 `bb50635` 那棵树（见 B 档倒数第二行）；
demo 报告 `docs/case-studies/attachments/demo-report.md` 的证据统计确为 **verified 11 / lead 0**
（`:42-43` 的口径表 + `:75`–`:85` 的证据行），与 `reader-package.md:174`、
`acceptance-pack.md:110`、`:391` 一致；`docs/install.md:218-226` 的退出码表与
`public-contracts.md:41-64` 的退出码表一致，**都已含 6**；工具包引用的 benchmark 行号
（`m6-level2-retest4.md:38`/`:82`、`m6-level2-retest3.md:85`、
`m6-level2-narrow-verify3.md:59`/`:61`）**逐条命中**。

**其余路径与命令全部对得上（逐条取证）：** 四个 `uv` extras（`analysis`/`demo`/`mcp`/`dev`）
在 `pyproject.toml` 里齐全；`src/dexatlas/cli/main.py` 的 13 个 `@app.command()` 覆盖材料
用到的 `backends`/`analyze`/`projects`/`classes`/`methods`/`source`/`resources`/`resrefs`/
`search`/`export`/`manifest`/`xrefs`，与契约表 §1.1 的 13 行一致；
`benchmarks/comparison/run.py` 的 `--input`/`--metrics`/`--report`/`--compare-to` 四个选项
真实存在；`Dockerfile` 无 `ENTRYPOINT`、只有 `CMD ["uvicorn", …]`，所以材料里的
`docker run --rm dexatlas dexatlas backends`（参数替换 CMD）成立，CI 用的是同一形式；
`scripts/m10_selfcheck.py` 的 `--json` 选项与「退出码 0 = 无失败项」的说法与
`docs/reports/m10-selfcheck.md:16-21` 一致。

**项目 id 完全对得上（可复算）：** `src/dexatlas/core/models.py:808-809`
`new_id()` 返回 `f"apk_{sha256[:16]}"`，即内容寻址。实测
`sha256sum examples/demo-app/demo.apk` → `80a8fe0e81204c9f…`、
`examples/obfuscated-app/obfuscated.apk` → `2f8d476fb9e71ac4…`，
与材料里的 `apk_80a8fe0e81204c9f`、`apk_2f8d476fb9e71ac4` 完全一致。

**公共契约的自洽性：** 契约表 §7.1/§7.2/§7.3 的「26/26」「6/6」「14/14」与发版说明的
「46/46 live checks (26 REST + 6 MCP + 14 CLI)」相加一致；MCP 工具 11 个、REST 端点
23 个、CLI 退出码 7 个（0–6）与代码一致。**但 46 是 2026-11-15 的快照**，脚本已增长到
49（见 B 档最后一行）。

**「固定验收 commit `277d0fa` 是否与材料自称的被验收对象一致」——不一致，两处：**
（1）`277d0fa` 里那份邀请函（`:57`、`:62`）钉的是 `e4f3011`，不是 `277d0fa`；
（2）`277d0fa` 里的材料对同一件事的说法与当前已提交版不同（退出码 6 缺席、MCP 写 10 个、
   邀请函逐轮写 17/15/17）。**结论：`277d0fa` 是「代码」的合适锚点，但不是「材料」的合适锚点。**

---

## 3. 评审者视角的一句话结论

**不能。** 这四份材料目前不足以让一个不知情的人真的完成一次验收：最关键的一个缺口是
**「被验收对象与验收材料互相矛盾，而材料没有一条可执行的优先级规则」**——`v1.0.0` 的 tag
在仓库里不存在（`git tag -l` 只有 `v0.2.0`）、退出码 6 与 M8-4 有三种说法、逐轮分数有两套、
发版说明的「46/46 契约实测」已是过期快照（脚本现在 49 项）、被读者包与执行摘要当作
「你也可以重跑」的自查记录描述的是 `main` @ `bb50635`（落后验收提交 83 个提交、徽章数字
第三套）、钉定提交里的邀请函还指向另一个 commit `e4f3011`、读者工具包压根不在 `277d0fa` 里；
评审者每做一次核对都会撞上材料自身的矛盾，而 `reader-kit.md:328`（「以准备包为准」）与
`acceptance-pack.md:38-40`（「以原始证据和代码为准」）这两条规则在**准备包自己与代码冲突时**
给出的答案正好相反。**次关键的一个缺口是「钉定提交 ≠ 材料」：`277d0fa` 里的材料缺退出码 6、
把 MCP 工具写成 10 个、且不含读者工具包**——即使评审者完美执行了邀请函，他验的也不是作者
手上那套材料。

---

*本报告由独立会话以只读方式产出；未修改仓库任何文件（本次只新增本报告），未运行
pytest / coverage / `uv sync` / `refresh-report-figures.py`，未联网，未打 tag，未推送。*
