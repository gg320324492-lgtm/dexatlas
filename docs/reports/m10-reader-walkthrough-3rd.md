# M10 读者视角走查报告（第三轮）—— 前两轮说「已关闭」的，是不是真关闭了

> **本文件的性质：** 这是第三轮**只读**的「读者视角走查」。基线是**当前树**
> `c6bf3f7`（共享工作树 `E:\Dexatlas` 的 `claude/m6-level2-verify` 分支），不是前两轮
> 各自钉的 `599ab67` / `02e6d9c`。作者以一位**从未参与开发**的外部评审者的身份，
> 把 M10 独立验收的五份材料（邀请函成稿、读者验收包、验收准备包、读者工具包、
> 一页版执行摘要）从头重读一遍，逐条判定前两轮共 42 条是否关闭，并检查这些修正
> 本身有没有留下新问题。
>
> **本文件只列问题与判定，不替主线程改材料。** 改动权在主线。
>
> **走查方法与边界：**
> - 全部结论用 `Read` / `Grep` / `git show` / `git ls-tree` / `git cat-file` /
>   `git rev-parse` / `git for-each-ref` / `git diff` 取得，另加三条**只读门禁**：
>   `scripts/check-doc-citations.py`（221 条引用，0 漂移，退出码 0）、
>   `scripts/check-version-claims.py --base auto`（退出码 0，2 条 finding 已在基线内）、
>   `pytest tests/test_docs.py`（**60 passed**，不带 `--cov`）。
> - **未运行** pytest `--cov`、coverage 任何命令、`uv sync`、
>   `scripts/refresh-report-figures.py`；未修改仓库任何文件（本次只新增本报告）；
>   未写入共享树 `E:\Dexatlas`；未打 tag、未发 PR、未联网、未代作者发送邀请。
> - **工作副本**：`E:\Dexatlas\.claude\worktrees\stale-number-scan-213305`
>   （分支 `claude/m10-reader-walkthrough-3rd`，自 `c6bf3f7` 起）。
> - **行号基准**：一律以当前树 `c6bf3f7` 为准。前两轮报告的行号钉在旧基线，
>   本表按**内容**定位后重新取当前行号。
> - **本 worktree 没有自己的 `.venv`**（`uv sync` 被禁止），故 `pytest` 借用共享树的
>   解释器，并以 `PYTHONPATH` 指向本 worktree 的 `src/`——实测
>   `dexatlas.__file__` = `E:\Dexatlas\.claude\worktrees\stale-number-scan-213305\src\dexatlas\__init__.py`，
>   即测的是本轮基线，不是共享树那一份。
> - 凡属推断而非直接取证，一律标「**推断**」并给出推断依据。
> - 本文件不转录任何密钥样式字符串；demo 样本里的 `sk_live_…` 字符串常量只以模式出现。

---

## 0. 结论速览

### 0.1 42 条判定分布

| 来源 | 条数 | 已关闭 | 未关闭 | 判定有误 |
|---|---:|---:|---:|---:|
| 第一轮 29 条 | 29 | **26** | **2**（B4、B8） | **1**（C5） |
| 第二轮 13 条 | 13 | **12** | **1**（N1） | 0 |
| **合计** | **42** | **38** | **3** | **1** |

### 0.2 本轮新发现：7 条

| 编号 | 一句话 | 类别 | 严重度 |
|---|---|---|:---:|
| **N9** | 执行摘要让读者用 `git rev-parse v1.0.0` 核对 commit hash——附注 tag 返回的是 **tag 对象 SHA**，与邀请函里的 commit hash **永不相等** | 1 路径/命令失效 | **高** |
| **N10** | 准备包 §3.3（Docker 路线）仍写 M8-2「查询类命令没有 `--workspace` 选项」，与 §7、`docs/status.md`、读者包、**源码**四处矛盾 | 5 重复/自相矛盾 | **高** |
| **N11** | 读者工具包 **9 处** `file:line` 引用错位，其中 **4 处指向空行** | 1 路径/命令失效 | 中 |
| **N12** | 暖缓存 30 秒的「环境差异」在三份材料里说法互相矛盾 | 2 数字矛盾 | 中 |
| **N13** | 读者工具包两处断言「本文件与该 commit 同一棵树」「行号指向…v1.0.0 发版 commit」——在 tag 树上不成立 | 6 过度承诺 | 中 |
| **N14** | `m10-selfcheck.md:11` 写「运行树：v1.0.0 发版 commit（**含本轮 M10 读者材料修正**）」——同一句假断言的第三处，且被三份材料直接链接 | 6 过度承诺 | 中 |
| **N15** | 读者工具包全篇**没有** `verified` / `lead` / `insufficient` 的定义，而这批「术语定义补齐」的修正只覆盖了准备包与读者包 | 3 术语未定义 | 低 |

### 0.3 最严重的三处

1. **N9 —— 读者在第 1 步就会拿到一个假警报。** 执行摘要 `:27` 写「想核对时用
   `git rev-parse v1.0.0` 核出 hash，与邀请函成稿 §2 占位符里填的那串逐字比对」。
   `v1.0.0` 是**附注 tag**，`git rev-parse v1.0.0` 返回 tag 对象 SHA
   `e937ca12c688b12be3de71195c412f844e6d50bd`，而邀请函 §2 填的「commit 的完整 hash」
   是 `8f9ddcaf7804841d77270c1fdb548110faecc598`。两者**永远不相等**。邀请函
   `:67` 又写「不一致就停下，联系发起人」——读者会照做，然后卡死在第 1 步，
   并得出「项目自己的材料对不上」的结论。其余三份材料都写对了（都用
   `git rev-parse HEAD`）。
2. **N10 —— 准备包自己跟自己打架，而且打在一份读者会照做的路线上。**
   `m10-acceptance-pack.md:253-255`（Docker 路线）仍把 M8-2 写成「已知限制：
   查询类命令没有 `--workspace` 选项」，而同一份文件的 `:668`（§7）写「已修 CLI
   （所有命令都有 `--workspace`/`-w`）并合入（`d90baff`）」，`docs/status.md:136`
   同样写「已修复并合入」，读者包 `:133-135` 已改对，源码
   `src/dexatlas/cli/main.py:159` 也确有 `--workspace`/`-w`。**四处说已修，一处说没修。**
3. **N1（延续）—— 评审者 `git checkout v1.0.0` 拿到的不是这批材料。**
   见 §5。tag 落后当前树 **85 个提交**，材料却断言「即含本轮全部材料修正的版本」。

### 0.4 一句话结论

**还不能。** 材料的**内容**这一轮基本修好了（38/42 已关闭，三条门禁全绿，40 项/
19 项/退出码 0–6/契约 49 项自洽）；但材料**指向的那棵树**还没跟上（tag 落后 85 个
提交），而且这一轮修正**新引入**了 7 处问题，其中 N9 与 N10 会直接把评审者拦在
开始之前或第一次判断上。

---

## 1. 基线事实（本轮取证）

| 事实 | 取证 |
|---|---|
| 当前树 = `c6bf3f7`（`claude/m6-level2-verify`，共享工作树 `E:\Dexatlas`） | `git log --oneline -1` |
| `v1.0.0` 是**附注 tag**：tag 对象 `e937ca12c688b12be3de71195c412f844e6d50bd`，指向 commit `8f9ddcaf7804841d77270c1fdb548110faecc598` | `git cat-file -t v1.0.0` → `tag`；`git rev-parse v1.0.0` → `e937ca1…`；`git rev-parse v1.0.0^{commit}` → `8f9ddca…` |
| `main` = `8f9ddca`——**与 tag 同一点** | `git rev-parse main` / `git rev-parse origin/main` → `8f9ddcaf…` |
| 当前树比 tag **领先 85 个提交** | `git rev-list --count 8f9ddca..c6bf3f7` → `85`；`git describe --tags c6bf3f7` → `v1.0.0-85-gc6bf3f7` |
| tag → 当前树的差异规模 | `git diff --shortstat 8f9ddca c6bf3f7` → `62 files changed, 6443 insertions(+), 496 deletions(-)` |
| 五份材料在两棵树里**全部不同** | `git diff --stat 8f9ddca c6bf3f7 -- docs/reports/m10-*.md` → 5 files changed, 229 insertions, 128 deletions |
| 当前树**已推送到 origin**（在 `origin/claude/m6-level2-verify` 上，不在 `origin/main`） | `git branch -r --contains c6bf3f7` → `remotes/origin/claude/m6-level2-verify`；`git rev-parse origin/main` → `8f9ddcaf…` |
| 本轮基线上三条只读门禁全绿 | `check-doc-citations.py` → 221 条引用 / 0 漂移 / 退出码 0；`check-version-claims.py --base auto` → 退出码 0（2 条 finding 均在 `8f9ddcaf` 基线内）；`pytest tests/test_docs.py` → **60 passed** |

---

## 2. 第一轮 29 条复核（基线：当前树 `c6bf3f7`）

> 编号沿用第二轮报告 §2 的映射（A1–A12 / B1–B10 / C1–C7）。

| 来源 | 编号 | 文件:行 | 状态 | 证据（file:line 或命令输出） |
|---|---|---|---|---|
| 第一轮 | A1 | `m10-invitation-final.md:27`；`docs/status.md:3`、`:22`、`:129` | 已关闭 | `git tag -l` → 含 `v1.0.0`；`git cat-file -t v1.0.0` → `tag`。**但由此派生 N1 未关闭** |
| 第一轮 | A2 | `m10-acceptance-pack.md:670`、`:164`、`:589-592`；`m10-reader-package.md:318`；`m10-reader-kit.md:280-282` | 已关闭 | 四处口径统一为「M8-4 已由退出码 6（`EXIT_NO_INDEX`）关闭」；G3（`:164`）改为「核对退出码应为 6，不是 0」 |
| 第一轮 | A3 | `m10-invitation-final.md:48-50` | 已关闭 | 「最终完整重测 DexAtlas 49/60 = 81.7%，逐轮 15/20、16/20、18/20…更早一次重测逐轮为 17/15/17」——两个数各归其位 |
| 第一轮 | A4 | `m10-invitation-final.md:54-72`；`m10-acceptance-pack.md:204`、`:235` | 已关闭（形式） | 占位符改为「【待填：v1.0.0 发版 commit 的完整 hash】」（`:60`）；全库 `git checkout` 目标已统一为 `v1.0.0`（grep 命中 11 处，无 `<…钉定的 commit>`）。**形式关闭，被 N1 掏空** |
| 第一轮 | A5 | `docs/reports/m10-reader-kit.md` | 已关闭 | `git ls-tree --name-only v1.0.0 docs/reports/` → 含 `m10-reader-kit.md`（tag 树里存在） |
| 第一轮 | A6 | `m10-acceptance-pack.md:151` | 已关闭 | F1 现列 `0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、5 截断、6 跑完但无可用的代码索引` |
| 第一轮 | A7 | `m10-acceptance-pack.md:153` | 已关闭 | F3 现写「MCP：工具清单为契约表的 **11 个**」；`docs/architecture/public-contracts.md:348` 同为 49 项（28+6+15） |
| 第一轮 | A8 | `README.md:41`；`README.zh-CN.md:31` | 已关闭 | 两份首屏均为「v1.0.0 已发布（tag 2026-11-17）」，状态不再相反 |
| 第一轮 | A9 | `m10-acceptance-pack.md:677-690` | 已关闭 | §8 逐行「未验证 / 未执行 / 未关闭」，末行结论 `:692-696` 明写「本文件是准备材料…M10 未完成」 |
| 第一轮 | A10 | `m10-acceptance-pack.md:42-47`；`m10-reader-kit.md:341-342` | 已关闭 | 单条规则：材料之间冲突以准备包判定标准为准；材料与被验收对象冲突以原始证据和代码为准。工具包不再另立规则 |
| 第一轮 | A11 | `m10-invitation-final.md:139-140`；`m10-acceptance-pack.md:563-567` | 已关闭 | 「这些编号是判定表里的**验收项编号**（如 B1 = 「按案例从 analyze 走到 xrefs 全程完成」），与「M6 的 B1 验收线」（发版阻断项）不是一回事」 |
| 第一轮 | A12 | `m10-acceptance-pack.md:117`、`:421`；`m10-reader-package.md:178-183` | 已关闭 | 准备包 C3 内联定义 `verified`/`lead`/`insufficient`；读者包复述并给出出处（公共契约表 §证据三级）。`trace` 在 `:421` 内联定义。**工具包侧仍缺 → 见 N15** |
| 第一轮 | B1 | `m10-reader-package.md:69`、`:405-407`；`m10-reader-kit.md:181`；`m10-executive-summary.md:44-46`；`m10-invitation-final.md:86` | 已关闭（残留口径见 N12） | 主数字已统一为「暖缓存 1.5–2 分钟」（五份材料一致），M8 的 30 秒各处都给出并指向同一来源 `docs/reports/m8-install-rehearsal.md:56` |
| 第一轮 | B2 | `m10-reader-package.md:19-20`；`m10-executive-summary.md:4` | 已关闭 | 两处均指向 `m10-invitation-final.md`（成稿），并注明「邀请函模板只供发起人填空用」 |
| 第一轮 | B3 | `m10-executive-summary.md:25-29` | 已关闭 | 第 1 步改为「你执行 `git checkout v1.0.0` 就能拿到它，**不必再向发起人索取 commit hash**」 |
| 第一轮 | B4 | `m10-reader-kit.md:282` → `m10-reader-package.md:312` | **未关闭** | `reader-package:312` 是**空行**；M8-4 的实际位置是 `:318`。**另新增同类错位 8 处 → 见 N11** |
| 第一轮 | B5 | `m10-acceptance-pack.md:588-592`；`m10-reader-package.md:99-104` | 已关闭 | 两处均写「M8-3（历史问题，已修复并合入）」，并说明 install.md 现写法与验收推荐路线 |
| 第一轮 | B6 | `m10-acceptance-pack.md:668`、`:674`、`:686`；`docs/status.md:136` | 已关闭 | §7 与 §8、status.md 一致：「M8-2/M8-3 已修复并合入、M8-4 已由退出码 6 关闭」。**但 §3.3 未同步 → 见 N10** |
| 第一轮 | B7 | `m10-acceptance-pack.md:627-644` | 已关闭 | 该段标题即「**历史账，不是验收 commit 的现状**（2026-11-15，基准 `ff5c4cc`）」，3 项/5 项失败被明确定性为历史账；§7 `:675` 另给当前树三项复跑结果（已复核为真） |
| 第一轮 | B8 | `m10-reader-package.md:155` | **未完全关闭** | §3.4 标题写「（验收项 **B3–B4、C1–C3**）」，但该节 `:160` 的 `manifest` 命令对应 **B2**（准备包 `:105`）、`:164` 的 `xrefs` 对应 **B5**（准备包 `:108`），两者的预期输出都在该节 `:172`、`:176` 的表里。编号仍对不上内容 |
| 第一轮 | B9 | `m10-reader-package.md:436-439`；`m10-reader-kit.md:309-310` | 已关闭 | 「该记录自带执行日期与它自己写明的 commit，是**那一次自查的快照**，不是验收 commit 的现状」 |
| 第一轮 | B10 | `docs/architecture/public-contracts.md:348`；`docs/releases/v1.0.0.md:65-66` | 已关闭 | 两处同为 49 项（28 REST + 6 MCP + 15 CLI），`28+6+15=49` |
| 第一轮 | C1 | `docs/architecture/public-contracts.md:326-327` | 已关闭 | §6 版本政策现写「版本号唯一来源是 `src/dexatlas/__init__.py:11` 的 `__version__`（**当前 `1.0.0`**）；打包经 hatch 从该文件读取」 |
| 第一轮 | C2 | `src/dexatlas/__init__.py:11` | 已关闭 | `__version__ = "1.0.0"`；`pyproject.toml` 经 hatch 读取（契约表 `:327` 一致） |
| 第一轮 | C3 | `m10-reader-package.md:12-16`；`m10-acceptance-pack.md:13-16`；`m10-reader-kit.md:90-93` | 已关闭 | 三处口径一致：「复评的 77.5% / 68.75% 是同一组维度与权重上的作者自评更新，**不是新基线**；重评请与 **75% / 65%** 这一档对齐」 |
| 第一轮 | C4 | `docs/reports/m10-reader-kit.md` | 已关闭 | `grep -n "npm" docs/reports/m10-reader-kit.md` → 零命中 |
| 第一轮 | C5 | `README.md:127` vs `README.md:539` | **判定有误（维持）** | 当前 `README.md:127` 是「## Principles」，`:539` 是「Please do not open a pull request that includes an APK…」；两处都不承载第一轮所指的那个 v1.0.0 表述。第一轮自己的表内就写「两处并不矛盾」 |
| 第一轮 | C6 | `m10-acceptance-pack.md:10-12`；`docs/reports/m10-number-traceability.md:29` | 已关闭 | 准备包头部同时给出「初稿基准 `ff5c4cc`」与「**当前版本对应 v1.0.0 发版 commit**」，不再让读者猜基准 |
| 第一轮 | C7 | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:3` | 已关闭 | 现指向 `m6-level2-narrow-verify2.md` 与 `m6-level2-narrow-verify3.md`，两份在 `docs/benchmarks/` 中真实存在 |

**第一轮小结：26 已关闭 / 2 未关闭（B4、B8）/ 1 判定有误（C5）。**

---

## 3. 第二轮 13 条复核（基线：当前树 `c6bf3f7`）

> 第二轮的 13 条 = 第一轮遗留未关闭的 5 条（A12、B1、B2、B3、C7）+ 第二轮新发现的
> 8 条（N1–N8）。

| 来源 | 编号 | 文件:行 | 状态 | 证据（file:line 或命令输出） |
|---|---|---|---|---|
| 第二轮 | N1 | `m10-invitation-final.md:61-63` | **未关闭** | 断言「即含本轮全部材料修正的版本」；实测 tag → `8f9ddca`，落后当前树 85 个提交。详见 §5 |
| 第二轮 | N2 | `m10-executive-summary.md:44-46` | 已关闭 | 现写「暖缓存约 **1.5–2 分钟**（同一环境差异下 M8 演练另测过约 30 秒…口径说明见读者验收包 §5.4）」，30 秒不再是唯一口径 |
| 第二轮 | N3 | `m10-executive-summary.md:26` | 已关闭 | 「**不必再向发起人索取 commit hash**」 |
| 第二轮 | N4 | `m10-executive-summary.md:4` | 已关闭 | 指向 `m10-invitation-final.md`（成稿） |
| 第二轮 | N5 | `m10-executive-summary.md:25-30` | 已关闭 | 第 1 步「锁定验收对象」写明 `git checkout v1.0.0` + `git rev-parse v1.0.0` 核对。**但核对命令本身有问题 → 见 N9** |
| 第二轮 | N6 | `m10-acceptance-pack.md:204` vs `:235` | 已关闭 | 两条路线（§3.2 uv / §3.3 Docker）的 checkout 目标已统一为 `git checkout v1.0.0` |
| 第二轮 | N7 | `m10-acceptance-pack.md:674-675` | 已关闭 | §7 末两行已改：`install.md` 行写「已修正：install.md 现写明五个一方样例 APK 已提交于 `examples/`」；文档门禁行写「已在当前树复跑三项只读门禁…`pytest tests/test_docs.py` 60 passed…**已关闭**」。**本轮实测复核为真** |
| 第二轮 | N8 | `m10-acceptance-pack.md:690`、`:695-696` | 已关闭 | §8 末行写「已发布：v1.0.0（tag 2026-11-17）——但独立验收在其后仍未执行，本次发版不含验收结论」；`:695-696` 写「v1.0.0 已于 2026-11-17 打 tag…本次验收既不构成重发或改发 v1.0.0 的理由」。两处不再打架 |
| 第二轮 | A12 | `m10-acceptance-pack.md:117`、`:421`；`m10-reader-package.md:178-183` | 已关闭 | 同 §2 |
| 第二轮 | B1 | 五份材料的时间口径 | 已关闭 | 同 §2（B1） |
| 第二轮 | B2 | `m10-reader-package.md:19-20`；`m10-executive-summary.md:4` | 已关闭 | 同 §2（B2） |
| 第二轮 | B3 | `m10-executive-summary.md:25-29` | 已关闭 | 同 §2（B3） |
| 第二轮 | C7 | `docs/benchmarks/m6-level2-narrow-verify-incomplete.md:5` | 已关闭 | 同 §2（C7） |

**第二轮小结：12 已关闭 / 1 未关闭（N1）。**

---

## 4. 本轮新发现：7 条

### N9【高】执行摘要让读者用 `git rev-parse v1.0.0` 核对 commit hash——这个核对永远不会通过

- **位置：** `docs/reports/m10-executive-summary.md:25-29`

  ```
  1. **锁定验收对象**：验收对象是 `v1.0.0` 这个 tag 所指的提交——你执行
     `git checkout v1.0.0` 就能拿到它，**不必再向发起人索取 commit hash**；
     想核对时用 `git rev-parse v1.0.0` 核出 hash，与
     [邀请函成稿 §2](m10-invitation-final.md) 占位符里填的那串逐字比对。
  ```

- **事实：** `v1.0.0` 是**附注 tag**（`git cat-file -t v1.0.0` → `tag`）。对附注 tag，
  `git rev-parse v1.0.0` 返回的是**tag 对象**的 SHA，不是它指向的 commit 的 SHA：

  | 命令 | 实测输出 |
  |---|---|
  | `git rev-parse v1.0.0` | `e937ca12c688b12be3de71195c412f844e6d50bd`（tag 对象） |
  | `git rev-parse v1.0.0^{commit}` | `8f9ddcaf7804841d77270c1fdb548110faecc598`（commit） |

  邀请函 `:60-63` 的占位符说明是「此处填 v1.0.0 发版 **commit** 的完整 hash」，
  填进去的必然是 `8f9ddca…`。执行摘要让读者拿 `e937ca1…` 去和 `8f9ddca…`
  「逐字比对」，**必然不一致**。

- **读者后果：** 邀请函 `:66-68` 紧接着写「不一致就停下，联系发起人，不要自行换用
  其他提交」。一个认真的评审者会在**第 1 步**停下，把「材料自相矛盾」记成第一条卡点。
  这是「材料自己制造的假警报」——比缺一个步骤更坏。

- **对照：** 其余三份材料都写对了——`m10-invitation-final.md:66`、
  `m10-reader-package.md:84`、`m10-reader-kit.md:245` 一律用 `git rev-parse HEAD`
  （在 `git checkout v1.0.0` 之后它给出的正是 commit SHA）。**四处写对、一处写错**，
  而写错的那一处是读者最先读到、且被指定为「第一次来」的首读页
  （`m10-reader-package.md:18`）。
- **推断（依据：材料自称来自 v1.0.0 附件的整理稿）：** 这一行大概率是第二轮改写
  执行摘要时新加的——改写前执行摘要没有「核出 hash」这一步（N5 修的就是它）。

### N10【高】准备包 §3.3（Docker 路线）仍把 M8-2 写成「已知限制」，与四处「已修复」矛盾

- **位置：** `docs/reports/m10-acceptance-pack.md:253-255`

  ```
  > **已知限制（M8-2）：** 容器内多个命令共享 workspace 时，查询类命令没有
  > `--workspace` 选项；用 `DEXATLAS_WORKSPACE=/workspace/ws` 统一。遇到此问题
  > 记录为卡点，不要改用作者未公开的步骤。
  ```

- **四处说「已修」：**

  | 位置 | 原文 |
  |---|---|
  | `m10-acceptance-pack.md:668`（§7） | 「已修 CLI（所有命令都有 `--workspace`/`-w`）并合入（`d90baff`）；复验 A6/G2 时确认 \| **已修复并合入**」 |
  | `m10-acceptance-pack.md:686`（§8） | 「§7 遗留项中 M8-2/M8-3 已修复并合入」 |
  | `docs/status.md:136` | 「M8-2（查询命令缺 `--workspace`）…**已修复并合入**（d90baff，全命令 `--workspace/-w`）」 |
  | `m10-reader-package.md:133-135` | 「（M8-2 已修复并合入：所有命令都带 `--workspace`/`-w`，**这一项不再是已知限制**）」 |

- **源码为准：** `src/dexatlas/cli/main.py:159`
  `typer.Option("--workspace", "-w", help="Override the analysis workspace root.")`——
  `--workspace` 确实存在。

- **读者后果：** 这条正落在**读者会照做的 Docker 路线**里，并直接牵动 A6/G2/F2
  三项判定。读者按 §3.3 的说法，会把「查询命令必须用环境变量绕」当成既定限制，
  并把「容器里用 `--workspace`」记成一个卡点；按 §7 的说法这不该是问题。
  **同一份准备包给出两个相反的答案。**
- **推断（依据：`:213-218` 的 M8-3 段已被改写成「历史问题，已修复并合入」，
  而 `:253-255` 的 M8-2 段仍是原句式）：** 第二轮修 M8-2/M8-3 时改了 §3.2 的
  M8-3 段、§7 的两行与读者包，**漏了 §3.3 的 M8-2 段**。

### N11【中】读者工具包 9 处 `file:line` 引用错位，其中 4 处指向空行

读者工具包 §5「本工具包引用的数字与出处」（`:317-334`）是评审者核对数字的主索引，
§2.5、§3.1、§4 的多处行号也靠它定位。逐条实测（脚本把每个 `path:line` 展开成被
指行的原文）：

| 工具包行 | 声称 | 被指行实际内容 | 应指 |
|---|---|---|---|
| `:42` | 「改了权重，分数就与 75% / 65% 的基线不可比」 | `m10-acceptance-pack.md:453` = **空行** | `:455` |
| `:122` | GitHub 权重 30/20/10/10/25/5 | `m10-acceptance-pack.md:468` = 「没有证据的分值记 0。」 | `:476-481` |
| `:123` | Upwork 权重 20/15/15/25/15/10 | `m10-acceptance-pack.md:482` = GitHub 表的「**合计** \| 100%」行 | `:490-495` |
| `:128` | 「附上您复现的命令与退出码」 | `m10-reader-package.md:358` = 「4 不表示软件无缺陷。」 | `:73` / `:348` |
| `:282` | M8-4 已在 v1.0.0 关闭 | `m10-reader-package.md:312` = **空行** | `:318` |
| `:308` | 「不替代你的任何一项判定」 | `m10-reader-package.md:418` = 「**Q：某个后端装不上怎么办？**」 | `:434-435` |
| `:322` | GitHub 权重（§5 出处表） | 同 `:122` | `:476-481` |
| `:323` | Upwork 权重（§5 出处表） | 同 `:123` | `:490-495` |
| `:325` | 目标 90%（两平台分别） | `m10-acceptance-pack.md:499` = **空行** | `:501` |
- **读者后果：** 工具包明说「所有数字均抄自仓库落盘文件，未手改」（`:314`）。评审者
  按这张表逐条核对时，**4 条落在空行、5 条落在不相干的行**——共 9 条无法核。
  落在空行的 4 条（`:42`、`:282`、`:325`）尤其可疑：读者点过去看到一片空白，
  会怀疑工具包整张表是编的。
- **为什么自动门禁没抓到：** `scripts/check-doc-citations.py` 只覆盖
  `docs/analysis-provenance.md`、`docs/architecture/*.md`、
  `docs/reports/phase1-execution-report.md`、`docs/benchmarks/large-apk.md`
  四份（`scripts/check-doc-citations.py:58-61` 的 `DOCS` 清单），**M10 五份材料不在其内**。本轮实测该门禁
  对当前树报 221 条引用 / 0 漂移 / 退出码 0——**这个绿灯不覆盖 M10 材料**。
  这正是 B4 类问题反复出现的原因。

### N12【中】暖缓存 30 秒的「环境差异」在三份材料里说法互相矛盾

| 位置 | 原文 |
|---|---|
| `m10-reader-kit.md:181` | 「M8 演练另测 6.8 秒纯分析；**同一环境下** 30 秒的那次实测见 [M8 演练]」 |
| `m10-reader-package.md:405-407` | 「暖缓存约 1.5–2 分钟。（[M8 演练]在**已就绪的会话工作树**上实测约 30 秒，**同一环境差异下**两者都成立；以你自己的实测为准…）」 |
| `m10-executive-summary.md:45` | 「暖缓存约 1.5–2 分钟（**同一环境差异下** [M8 演练]另测过约 30 秒…）」 |

- **矛盾点：** 工具包说 30 秒是「**同一环境**下」测的；读者包说 30 秒来自
  「已就绪的会话工作树」、因此存在「环境差异」。**同一批数字，一个说同环境，
  一个说不同环境。**
- **原始事实：** `docs/reports/m8-install-rehearsal.md:56-57` 写的是
  「**从空目录到第一份报告**，暖缓存约 30 秒、冷缓存约 1 分钟（不含 Docker）」，
  `docs/reports/m8-install-rehearsal.md:46` 另给「首次分析 6.8 s」。也就是说 M8 的 30 秒与材料的「暖缓存（JDK/uv 已装）
  到第一份报告约 1.5–2 分钟」**是同一场景的两个环境**，但材料从未说清差异是什么
  （没写差在 venv 已 sync、uv 缓存已热、还是别的）。
- **读者后果：** 读者包 §5.4 让读者「明显超出预期按 §5.2 记卡点」——那么 30 秒到
  1.5 分钟之间的任何耗时都可能被记成卡点，而材料自己给不出判据。
- **备注：** 这不改变 B1 的判定（主数字已统一为 1.5–2 分钟，五处一致）；残留的是
  **解释**没统一，不是数字没统一。

### N13【中】读者工具包两处断言「本文件与该 commit 同一棵树」「行号指向 v1.0.0 发版 commit」

- `docs/reports/m10-reader-kit.md:9-11`：「编写日期：2026-11-17 · 验收 commit：
  **v1.0.0 发版 commit**…**本文件与该 commit 同一棵树**」
- `docs/reports/m10-reader-kit.md:314-315`：「所有数字均抄自仓库落盘文件，未手改；
  **行号指向引用时所在的 commit——即本轮 v1.0.0 发版 commit**」

  事实：工具包这些行号指向的是**当前树**（`c6bf3f7`）的内容，而 `v1.0.0` tag 指向
  `8f9ddca`。tag 树里的同名文件在 §5 出处表的 13 条引用上**至少有 5 条内容不同**
  （`m10-acceptance-pack.md:27`、`:173`、`:457`、`:468`、`:482` 均已移动）。
  读者 checkout tag 后按工具包的「出处表」逐条核对，**每一条都会落到别的内容上**。
- 与 N1 同源，但这是**另一份文件里的另两句断言**，后果独立：读者核对数字的
  唯一索引表，恰好是失效最严重的那一张。

### N14【中】`m10-selfcheck.md:11` 同源假断言，且被三份材料直接链接

```
docs/reports/m10-selfcheck.md:11
> 执行日期：2026年11月17日 · 运行树：v1.0.0 发版 commit（含本轮 M10 读者材料修正；
```

「含本轮 M10 读者材料修正」——tag 树 `8f9ddca` 里**不含**任何一轮的读者材料修正
（tag 树的 `m10-reader-kit.md:180` 仍有 `npm install`，`m10-executive-summary.md:25-27`
仍写「领 commit：向发起人索取固定 commit hash」）。该文件被
`m10-executive-summary.md:62`、`m10-reader-package.md:432`、`m10-reader-kit.md:306`
三处直接链接，读者被引到它就会读到这句假断言。
- 读者包 `:436-439` 已经教读者「自查记录是它自己那一次执行时的快照，不是验收 commit
  的现状」——但快照自报的树也是错的，读者无从判断。

### N15【低】读者工具包全篇没有 `verified` / `lead` / `insufficient` 的定义

- `grep -n "verified\|lead\|insufficient\|三级" docs/reports/m10-reader-kit.md` → **零命中**。
- 而工具包多处让读者做需要这三级的判断：`:96`「引用不可解析」、
  `:114`「报告里的结论能否追到字节；引用能否解析」、
  `:155`「三问结论（…事实与线索能否区分）」。
- 准备包 `:117`（C3 验收项）与读者包 `:178-183` 都有完整定义与出处
  （公共契约表 §证据三级）。**「术语定义补齐」这一批修正只覆盖了准备包与读者包，
  没覆盖工具包。**

---

## 5. N1 取证专章：「`git checkout v1.0.0` 真的拿到含全部修正的版本吗」

### 5.1 结论

**不成立。** 这是本轮最严重的一条，且**预期之内**（任务书已说明 tag 尚未重打）。

### 5.2 三个数字

| 项 | 值 | 取证 |
|---|---|---|
| `v1.0.0` 是 | **附注 tag** | `git cat-file -t v1.0.0` → `tag` |
| tag 对象 SHA | `e937ca12c688b12be3de71195c412f844e6d50bd` | `git rev-parse v1.0.0` |
| tag **指向的 commit** | `8f9ddcaf7804841d77270c1fdb548110faecc598` | `git rev-parse v1.0.0^{commit}` |
| `main` / `origin/main` | `8f9ddcaf…`（**与 tag 同一点**） | `git rev-parse main` / `origin/main` |
| 当前树 | `c6bf3f7f14a43f07931f9ef12ce440a983941b4e`（`claude/m6-level2-verify`） | `git log --oneline -1` |
| 当前树领先 tag | **85 个提交** | `git rev-list --count 8f9ddca..c6bf3f7` → `85`；`git describe --tags c6bf3f7` → `v1.0.0-85-gc6bf3f7` |
| 差异规模 | 62 个文件、+6443 / −496 | `git diff --shortstat 8f9ddca c6bf3f7` |
| 五份材料在两棵树的差异 | 5 files changed, 229 insertions(+), 128 deletions(-) | `git diff --stat 8f9ddca c6bf3f7 -- docs/reports/m10-*.md` |

### 5.3 材料的断言

`docs/reports/m10-invitation-final.md:60-63`：

```
commit 【待填：v1.0.0 发版 commit 的完整 hash】
（填写说明：此处填 v1.0.0 发版 commit 的完整 hash——也就是读者执行
 `git checkout v1.0.0` 所得到的那个提交，即含本轮全部材料修正的版本；
 由验收发起人在发出本函之前填入）
```

**这句在今天不成立。** 同一句话的变体还出现在
`m10-reader-kit.md:9-11`（N13）与 `m10-selfcheck.md:11`（N14）。

### 5.4 评审者 checkout tag 后会看到什么（逐条实测）

在 tag 树（`8f9ddca`）里实测，前两轮判定为「已关闭」的问题**大面积原样复现**：

| 位置（**均在 tag 树 `v1.0.0` = `8f9ddca` 内**，行号为该树行号，与 §2/§3 的当前树行号不同） | 内容 | 对应前两轮条目 |
|---|---|---|
| `m10-invitation-final.md:57` | `commit 277d0fa` + `git checkout 277d0fa` | A4 复现（钉的根本不是 v1.0.0） |
| `m10-acceptance-pack.md:196`、`:224` | `git checkout <验收发起人钉定的 commit>` | A4 复现（占位符回到旧写法） |
| `m10-acceptance-pack.md:157` | G3「核对 M8-4 的退出码缺口（全部后端失败仍为 0）」 | A2 复现 |
| `m10-acceptance-pack.md:567` | 「M8-2 / M8-3 / M8-4 仍未关闭」 | A2 / B6 复现 |
| `m10-acceptance-pack.md:635-637` | M8-2 / M8-3 / M8-4 = 「未关闭」 | A2 / B6 复现 |
| `m10-acceptance-pack.md:205` | 「已知文档不一致（M8-3）」 | B5 复现 |
| `m10-acceptance-pack.md:641-642` | §7 末两行停在旧树（install.md 措辞、文档门禁「未关闭（阻断文档门禁）」） | N7 复现 |
| `m10-acceptance-pack.md:688` vs §7 | 「v1.0.0 已于 2026-11-17 打 tag」与「不能据此发布 v1.0.0」并存 | N8 复现 |
| `m10-reader-package.md:16` | 「邀请与独立性要求见[验收邀请函](m10-invitation-template.md)」 | B2 复现 |
| `m10-reader-package.md:63` / `:379` | 「暖缓存…约 2 分钟」/「暖缓存约 30 秒」 | B1 复现 |
| `m10-reader-kit.md:180` | 「`npm install` 都是一次性开销」 | C4 复现 |
| `m10-executive-summary.md:25-27` | 「**领 commit**：向发起人索取固定 commit hash」+ `git checkout <commit>` | B3 / A4 复现 |

（tag 树里 `F1` 已含退出码 6、`F3` 已写 11 个 MCP 工具——发版提交 `8f9ddca` 顺手修掉
了这两处，所以 A6/A7 在 tag 树里不复现。上表只列实测复现的。）

### 5.5 最坏的一种组合

评审者的核对流程是：

1. 邀请函 `:66-68` 要求「`git checkout v1.0.0`，用 `git rev-parse HEAD` 核出完整
   hash，与上面填入的那一串**逐字相同**再开始验收」。
2. 发起人填进占位符的必然是 `8f9ddcaf…`（那是 `git checkout v1.0.0` 之后的 HEAD）。
3. 评审者 checkout `v1.0.0` → HEAD 正是 `8f9ddcaf…` → **hash 核对通过**。
4. 然后评审者打开**同一棵树里**的 `docs/reports/m10-acceptance-pack.md`——
   那是**旧版**：M8-4 未关闭、§7 末两行停在旧树、checkout 目标写的是占位符。
5. 而他收到的**邮件里**的验收包是**新版**：M8-4 已关闭、40 项、19 项 ★、退出码 0–6。

**hash 核对给绿灯，内容核对给红灯，两者不可能同时通过。** 材料自己设计的那道
「防伪造」关卡（核对 hash）恰好把评审者送到一棵树，那棵树里的材料与随函材料
不是同一份——而材料里没有任何一处告诉评审者「随函的这份以哪个 commit 为准」。

### 5.6 处置建议（只列，不代改）

1. **重打 `v1.0.0` tag** 指向最终验收 commit，并把当前树推到 `origin/main`——
   两件都要做；只做前者，评审者 `git clone` 后 `git tag -l` 可能根本看不到这个 tag。
2. 把 `m10-invitation-final.md:61-63`、`m10-reader-kit.md:9-11`、`:314-315`、
   `m10-selfcheck.md:11` 四处「即含本轮全部材料修正的版本 / 同一棵树 / 运行树」
   的措辞改成**不假设「当前 tag 指向何处」**的写法（例如写成「本函与随附材料
   同属 tag `v1.0.0` 所指的那棵树；材料本身的版本以随函这一份为准」）。
   不改这一句，下次重打 tag 前会**再犯一次**。
3. 邀请函 §2 增一句：**评审者应以随函材料为准，仓库里的同名文件若与之不同，
   记为卡点并联系发起人**——这条现在缺。

---

## 6. 材料里的命令、路径、文件名核对

### 6.1 路径与文件（全部真实存在）

逐个 `test -e` 实测，材料点名的仓库内文件**全部存在**：

`examples/demo-app/demo.apk`、`scripts/m10_selfcheck.py`、`scripts/fetch-fixtures.sh`、
`scripts/verify-public-contracts.py`、`scripts/check-doc-citations.py`、
`scripts/check-version-claims.py`、`scripts/refresh-report-figures.py`、
`scripts/m6_level2_narrow_verify_report.py`、`docs/how-to-verify.md`、
`docs/how-to-verify.zh-CN.md`、`Dockerfile`、`pyproject.toml`、`uv.lock`、
`docs/architecture/public-contracts.md`、`docs/benchmarks/service-regression-set.md`、
`docs/benchmarks/m6-level2-retest{3,4}.md`、`docs/benchmarks/m6-level2-narrow-verify3.md`、
`docs/benchmarks/comparison-{traces,real-traces,stronger-traces}.json`、
`docs/reports/portfolio-readiness-2026-11-15{,-recheck}.md`、
`docs/reports/m8-install-rehearsal.md`、`docs/reports/phase3-baseline.md`、
`docs/reports/claim-mismatches.md`、`docs/reports/v1.0.0-github-release-body.md`、
`docs/proposals/exit-code-partial-read.md`、`docs/releases/v1.0.0.md`、
`docs/roadmap/phase3-plan.md`。

### 6.2 命令

| 命令 | 出处 | 核对结果 |
|---|---|---|
| `git checkout v1.0.0` | 五份材料共 11 处 | 目标统一 ✓（N1 使其取到的树不对） |
| `git rev-parse HEAD` | invitation `:66`、reader-package `:84`、reader-kit `:245` | ✓ 正确 |
| `git rev-parse v1.0.0` | **executive-summary `:27`** | ✗ **返回 tag 对象 SHA → 见 N9** |
| `uv sync --extra dev --extra analysis --extra mcp --extra demo` | invitation `:100`、reader-package `:92`、acceptance-pack `:205`、exec-summary `:31` | 四处逐字一致 ✓ |
| `uv run dexatlas backends` | invitation `:101`、reader-package `:93`、acceptance-pack `:206` | 三处一致 ✓ |
| `uv run dexatlas analyze examples/demo-app/demo.apk` | acceptance-pack `:270`、reader-package `:140` | 一致 ✓ |
| `uv run dexatlas export … -o evidence.zip` + `verify_package` / `verify_citations` | reader-package `:203-209`、acceptance-pack `:295`、`:301` | 一致 ✓ |
| `pytest tests/test_docs.py` | acceptance-pack `:675` 声称 60 passed | ✓ **本轮实测 60 passed** |
| `scripts/check-doc-citations.py` | acceptance-pack `:675` 声称 0 漂移 | ✓ 实测 221 条 / 0 漂移 |
| `scripts/check-version-claims.py --base auto` | acceptance-pack `:675` 声称 0 新增 finding | ✓ 实测退出码 0，2 条 finding 均在基线内 |
| `docker build -t dexatlas .` | reader-package `:128`、acceptance-pack `:236` | 一致 ✓；`Dockerfile` 存在 ✓ |

### 6.3 数量口径

`40 项` / `19 项 ★` / `退出码 0–6` / `契约 49 项（28+6+15）` / `MCP 11 个` /
`逐轮 15/20、16/20、18/20` / `合计 49/60 = 81.7%` / `窄验证 3/6（门槛 ≥4）` /
`基线 75% / 65%` —— 在五份材料内**全部自洽**，且与
`docs/architecture/public-contracts.md`、`docs/benchmarks/m6-level2-retest4.md`、
`docs/benchmarks/m6-level2-narrow-verify3.md` 一致。

### 6.4 唯一未被自动门禁覆盖的一层

`scripts/check-doc-citations.py` 的 `DOCS` 清单（`:58-61`）只含四份文档，
**M10 五份材料不在其中**；因此本报告 §4/N11 的 9 处错位不会被任何现有门禁抓到。
这与 `tests/test_docs.py` 的 60 passed 并存——两个绿灯都覆盖不到读者材料。

---

## 7. 仍未关闭的清单（不在本轮改动，只列）

| # | 条目 | 位置 | 性质 | 严重度 |
|---|---|---|---|:---:|
| 1 | **N1** —— `v1.0.0` tag 落后当前树 85 个提交；材料断言「checkout tag 即得含全部修正的版本」不成立 | `m10-invitation-final.md:61-63` | 阻塞发邀请函 | **高** |
| 2 | **N9** —— 执行摘要让读者用 `git rev-parse v1.0.0` 核对 commit hash（附注 tag 返回 tag 对象 SHA，永不相等） | `m10-executive-summary.md:27` | 读者第 1 步的假警报 | **高** |
| 3 | **N10** —— 准备包 §3.3 仍写 M8-2 是「已知限制：查询类命令没有 `--workspace`」，与 §7 / status.md / 读者包 / 源码四处矛盾 | `m10-acceptance-pack.md:253-255` | 自相矛盾（读者会照做的路线上） | **高** |
| 4 | **B4 / N11** —— 读者工具包 9 处 `file:line` 错位（4 处指向空行） | `m10-reader-kit.md:42`、`:122`、`:123`、`:128`、`:282`、`:308`、`:322`、`:323`、`:325` | 引用失效 | 中 |
| 5 | **B8** —— 读者包 §3.4 标题漏 B2、B5 | `m10-reader-package.md:155` | 编号错位 | 中 |
| 6 | **N12** —— 暖缓存 30 秒的「环境差异」三处说法互相矛盾 | `m10-reader-kit.md:181` / `m10-reader-package.md:405-407` / `m10-executive-summary.md:45` | 口径不一致 | 中 |
| 7 | **N13** —— 工具包断言「本文件与该 commit 同一棵树」「行号指向 v1.0.0 发版 commit」 | `m10-reader-kit.md:9-11`、`:314-315` | 过度承诺 | 中 |
| 8 | **N14** —— 自查记录写「运行树：v1.0.0 发版 commit（含本轮 M10 读者材料修正）」 | `m10-selfcheck.md:11` | 过度承诺 | 中 |
| 9 | **N15** —— 读者工具包无 `verified`/`lead`/`insufficient` 定义 | `m10-reader-kit.md`（全篇） | 术语未定义 | 低 |

**共 9 处。** 其中 1–3 项在发出邀请函之前必须解决；4–9 项可以在邀请函发出后
作为随函勘误，但第 4 项（引用失效）会直接削弱「工具包是权威出处表」的定位。

---

## 8. 结论

**这批材料现在还不能让一个不知情的人真的完成一次独立验收。**

最关键的缺口有两个，缺一不可：

1. **指向的那棵树没跟上（N1）。** 评审者 `git checkout v1.0.0` 拿到的是
   `8f9ddca`，落后当前树 **85 个提交**、62 个文件；那棵树里的准备包把 M8-4 写成
   未关闭、§7 末两行停在旧树、读者包指向邀请函**模板**、工具包还留着 `npm install`。
   而随函发出的材料写的是修好之后的版本。**hash 核对会通过，内容核对会失败，
   两者不可能同时通过**，材料也没有任何一处告诉评审者以哪一份为准。
   —— 这不是「读者会卡住」，是「读者会做出一份针对另一棵树的验收结论」。

2. **第 1 步就有一道自己造的假警报（N9）。** 执行摘要让读者拿
   `git rev-parse v1.0.0`（附注 tag → tag 对象 SHA `e937ca1…`）去和邀请函里
   填的 commit hash（`8f9ddca…`）「逐字比对」，并配套一句「不一致就停下，
   联系发起人」。即使 tag 被重打，这一句仍会让每一位评审者在第 1 步停下。
   三处引用的 `git rev-parse HEAD` 写法说明正确的写法就在旁边——只是没被统一。

在这两条修掉之前，其余 38 条「已关闭」的修复（40 项 / 19 项 ★ 自洽、退出码 0–6、
契约 49 项、M8-4 三处口径统一、术语定义补齐、三条只读门禁全绿）都只证明了
**这份材料本身是自洽的**——它还没有证明「评审者按材料走时，看到的是这份材料」。
