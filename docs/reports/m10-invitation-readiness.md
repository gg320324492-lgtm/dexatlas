# M10 独立验收邀请 —— 发出前就绪记录

> **状态：作者侧准备就绪（材料已定稿、核对清单已可执行）。独立验收尚未执行；
> M10 未完成。**
>
> **本轮没有发送任何东西。** 没有发邮件、没有调用任何平台或 API、没有联网、
> 没有推送、没有打 tag、没有改动 `src/`、`tests/`、`scripts/` 与 `CHANGELOG.md`。
> 本轮改的全部是 `docs/` 下的文档文件，发信是发起人的动作，由人来做。
>
> 本文件回答三个问题：**发出前必须做哪几步**、**还差什么**、**谁来做**。
> 逐步的执行细节在[发起人发送前清单](m10-invitation-sender-checklist.md)；
> 读者侧的材料在[读者验收包](m10-reader-package.md)。

## 0. 本轮做了什么、没做什么

| | 内容 |
|---|---|
| **定稿** | [邀请函成稿](m10-invitation-final.md)：正文全部写实（读者是谁、要做什么、大概多久、要交回什么、交回后会发生什么、作者的边界），只留一处**内容占位**——第二节的验收 commit hash |
| **改写** | [发送前清单](m10-invitation-sender-checklist.md)：改成「查什么 → 怎么查（命令）→ 查过是什么样 → 不通过怎么办」的可执行版，并补上 N1 要求的「钉死一棵树」一组 |
| **补一处** | [验收记录模板](m10-review-record-template.md) §1 的「commit hash」栏：注明照抄邀请函 §2 钉定的那一串完整 hash（N1 的一环） |
| **新增** | 本文件 |
| **没有做** | 没有发送、没有外发、没有打 tag、没有推送、没有联网、没有跑测量脚本（`scripts/refresh-report-figures.py`）、没有改四个由测量脚本写的文件（`docs/reports/phase1-execution-report.md`、`README.md`、`README.zh-CN.md`、`docs/status.md`） |

**材料一词的边界：** 「就绪」说的是**邀请函与发送清单可以发出**，
不是说 M10 可以关闭。M10 的判定仍然只来自一位未参与实现的读者交回的那份记录。

## 1. 发出前必须做的 10 步

按顺序做；**第 2 步不做，第 3 步做的也是废工**。

| # | 步骤 | 查什么 / 怎么查 | 完成判据 | 谁做 |
|---|---|---|---|---|
| 1 | 材料定稿 | 邀请函、验收包、读者包、工具包、记录模板、发送清单均已定稿 | 本轮已完成 | 作者（已完成） |
| 2 | **重打 `v1.0.0` tag** | `git tag -f -a v1.0.0 <材料定稿的提交> -m "v1.0.0 — 材料定稿"` 后 `git push origin v1.0.0 --force` | 读者 `git checkout v1.0.0` 拿到的是**定稿材料**，不是旧稿 | 发起人 |
| 3 | **取 hash 并填进函里** | `git rev-parse "v1.0.0^{commit}"`；贴进[邀请函 §2](m10-invitation-final.md)，整串 40 位一字不差 | `grep -n "commit 【待填" docs/reports/m10-invitation-final.md` 无命中 | 发起人 |
| 4 | 补完抬头与落款 | `grep -n "［.*——发出时填写］" docs/reports/m10-invitation-final.md` | 无命中（称呼、发件人、日期、签名） | 发起人 |
| 5 | 确认远端拿得到 | `git ls-remote origin 'refs/tags/v1.0.0^{}'` | 返回的提交与第 3 步那一串相同 | 发起人 |
| 6 | 跑自查与两条门禁 | `uv run --no-sync python scripts/m10_selfcheck.py`（退出码 0）；`scripts/check-doc-citations.py`；`scripts/check-version-claims.py --base auto` | 三个退出码都是 0 | 发起人 |
| 7 | 确认本机三后端 | `source .scratch/env.sh && uv run --no-sync dexatlas backends` | 三个后端 available，版本抄进留档 | 发起人 |
| 8 | 落实交回口径 | 函 §6 的交回渠道与时限写实；补一句「不得转发给第三方」 | 读者知道往哪交、交到什么时候 | 发起人 |
| 9 | 附件与凭据扫描 | `git ls-tree -r --name-only "<验收 commit>" docs/case-studies/`；凭据形状扫描；`git status --porcelain` 无输出 | 13 个案例文件在验收树上；凭据命中仅两处已知占位符；工作区干净 | 发起人 |
| 10 | 填留档 → 发出 | 留档表：发出日期、收件人、未参与实现的确认、验收 hash、交回渠道、时限、后端版本、自查结果 | 留档表无空格 | 发起人 |

第 2–3 步是第三轮读者走查的 **N1**：「重打 tag 之前不能发邀请函」——
材料改了而 tag 没跟上，读者会做出一份**针对另一棵树**的验收结论。
第 4–10 步的逐条命令、实测输出与「不通过怎么办」见
[发送前清单](m10-invitation-sender-checklist.md)。

## 2. 还差什么

**A. 只能由人做的事（本轮做不了）**

| 缺口 | 为什么本轮做不了 | 谁来补 |
|---|---|---|
| **一位未参与实现的独立读者** | 这是独立验收的前提：没有这样一个人，40 项判定就没人做，M10 就没有依据 | 发起人找读者，并确认对方**没有**写过本项目的代码/文档/做过评审 |
| 读者的姓名或代号 | 称呼栏是唯一的收件人身份 | 发起人 |
| 实际发件人身份与联系方式 | 联系方式失效 = 读者只能停在半路 | 发起人 |
| 发出日期 | 留档与时限都从这一天算 | 发起人（发出当天） |

**B. 可以做但本轮没做的（因为不属于文档工作）**

| 缺口 | 说明 |
|---|---|
| 重打 `v1.0.0` tag 并推送 | 属于改动远端的动作，发起人决定（清单组二给了两种选择） |
| 填 hash | hash 取决于 tag 最终落在哪个提交上，**必须现查现填**，不能提前写死 |
| 跑最终重测量 | 主会话在跑；本轮**没有**跑 `scripts/refresh-report-figures.py`，也没有手抄任何测量数字——套件数、覆盖率、指纹一律以[发版执行报告](phase1-execution-report.md) 里的 `<!--fig:...-->` 标记为准 |

**C. 本轮发现的、记录在案但未改的问题**

| # | 问题 | 为什么不在这轮改 |
|---|---|---|
| 1 | `docs/reports/next-engagements.md:236` 与 `docs/reports/v1.0.0-release-runbook.md:389` 仍写「作者侧自检 40/40」——自助检查的自动化判定早已从 40 提到 **43**（见[自查报告](m10-selfcheck.md)） | 属于另外两份文档的数字同步，不在本轮三份交付物的范围内；改前应先确认它们指的是哪一个 40 |
| 1b | `docs/reports/next-engagements.md:411` 还写着「填 7 处空格」——邀请函重写后是 **5 处**（抬头三项 + 落款签名 + hash 占位） | 同上；清单与邀请函本轮已改成按内容查找，不再依赖这个数字 |
| 2 | `docs/reports/reader-dry-run.md:64` 记的是「通过 40 / 失败 0 / 需人工 40」，那是三条新判据加入**之前**的快照 | 那是**某次演练的历史记录**，改它就改掉了历史 |
| 3 | `docs/reports/m10-number-traceability.md:62`、`:105`、`:131` 等处按行号引用邀请函的旧行号 | 同上：那是某棵基线树上的核对记录；本轮重写了邀请函，行号会漂。**注意**：这些引用**不在** `scripts/check-doc-citations.py` 的受检文档清单里，机器不会报错，但人读时会指错位置 |
| 4 | 第三轮走查报告（`m10-reader-walkthrough-3rd.md`）里的 tag hash 与「落后 85 个提交」是那轮基线上的历史值 | 同上，那是**当时那棵树**上的取证记录 |
| 5 | `docs/status.md:3` 写「v1.0.0（tag 2026-11-17）」，而当前这个 tag 对象是 2026-11-18 重打的 | 发版日期仍是 2026-11-17；tag 对象会在发信前再重打一次。该文件由测量脚本写，本轮不动 |

## 3. 谁来做

| 角色 | 谁 | 做什么 | 边界 |
|---|---|---|---|
| **发起人** | 项目作者 / 负责人 | 走完第 1–10 步、发出邀请、接收记录、按记录排修复与复验 | 不判定验收项，不替读者补步骤，不对分数施加影响 |
| **独立读者** | 一位**未参与实现**的外部读者 | 按[读者验收包](m10-reader-package.md)复现、审阅、逐项判定、打分、交回[记录模板](m10-review-record-template.md) | 只依据自己执行命令得到的输出判定；不用移动的 `main`；全程只验钉定的那一个 commit |
| **作者侧自动化** | `scripts/m10_selfcheck.py` 与两条门禁 | 回答仓库自己能回答的问题（当前：43 条自动化判定 / 40 项留人工） | **不产生任何验收结论**；「需人工」不是失败 |

## 4. 本轮的核查记录

以下是在本轮工作树上实跑出来的结果（只读命令；不联网）：

| 核查 | 命令 | 实测 |
|---|---|---|
| tag 是附注 tag | `git cat-file -t v1.0.0` | `tag` |
| tag 对象 | `git rev-parse v1.0.0` | 40 位 hash，**每次重打 tag 都变**——现查现填，本表不写死 |
| tag 指向的提交 | `git rev-parse "v1.0.0^{commit}"` | 另一串 40 位 hash，**同上**；它才是填进邀请函 §2 的那一串 |
| tag 指向的树与本轮树的关系 | `git diff --name-only "v1.0.0^{commit}"..HEAD -- src/ tests/` | 空（代码与测量数字不受材料修正影响） |
| M10 材料的差异 | `git diff --name-only "v1.0.0^{commit}"..HEAD -- docs/reports/m10-*.md` | tag 重打到材料定稿提交后应为**空**；不为空就是「读者读到旧稿」 |
| 案例与证据包在验收树上 | `git ls-tree -r --name-only "v1.0.0^{commit}" docs/case-studies/` | 材料定稿时是 20 个文件（4 篇 markdown + 4 个证据包 zip + 12 份报告）；**个数随附件集增删变化**，要核的是结构 |
| 凭据形状扫描 | `git grep -nEI "(api[_-]?key\|secret\|access[_-]?token\|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}"` | 命中 2 处，都是仓库内一方测试里的占位常量（`tests/test_search_substring_fallback.py`、`tests/test_workbench_agent.py`），不是真凭据 |
| 作者侧自查 | `python scripts/m10_selfcheck.py`（本机**未装** dev extras） | `通过 42，失败 1，需人工 40`，唯一失败项 `G.vulture`（判的是 vulture 在不在 PATH/venv 里）；装齐依赖后应为 `通过 43，失败 0，需人工 40` |
| 引用检查 | `python scripts/check-doc-citations.py` | **0 漂移**、退出码 0（引用条数随材料增删变化，本表不写死条数） |
| 版本声明检查 | `python scripts/check-version-claims.py --base auto` | 退出码 0，2 条 finding 已在基线内 |

**两处未实测：** 远端 tag 状态（`git ls-remote`，本轮不联网）与本机三个后端的
available 状态（本 worktree 没有 `.scratch/env.sh`）。这两项在清单里都写着，
请发起人在自己机器上跑。

## 5. 两个容易搞错的地方

### 5.1 「40 项验收」与「43 条自动化判定」不是一回事

| | 是什么 | 分母 |
|---|---|---|
| **40 项验收** | 验收包 §2 的检查表（A–G 七组），读者逐项判「通过 / 不通过 / 未验证」 | 40（其中 19 项是 ★ 阻断项） |
| **43 条自动化判定** | 作者侧自查脚本自己能回答的检查条数 | 43 |
| **40 项留人工** | 上面那 40 项验收，脚本不代替读者判 | 40 |

83 = 40 + 43，两组是**不同的集合**：脚本的 43 条里有几条对应到某个验收项
（如 `F1.exit-codes` → F1），但它们不是同一组东西。
**「自查 43/43 通过」不表示 40 项验收里有任何一项被判通过**——M10 的判定
只来自读者。[邀请函 §5](m10-invitation-final.md)现在就把这句话写在了正文里。

### 5.2 「独立验收未执行」在各处的表述

本轮核对了对外可见的 **10 个文件、22 处**状态表述，**语义一致**：没有任何一处
声称独立验收已完成。措辞有六种变体，指的是同一件事：

| 措辞 | 出处（示例） |
|---|---|
| 独立验收尚未执行 | `docs/reports/m10-acceptance-pack.md:3`、`:660`、`:677`；`docs/reports/README.md:91` |
| 独立验收尚未开始 | `docs/reports/m10-reader-package.md:3`；`docs/reports/m10-reader-kit.md:3`；`docs/status.md:13`、`:132`；`CHANGELOG.md:334`；`docs/reports/v1.0.0-github-release-body.md:247` |
| 验收未执行 | `README.zh-CN.md:522` |
| acceptance not run | `README.md:647` |
| Independent acceptance has not started | `docs/reports/v1.0.0-github-release-body.md:155`；`docs/releases/v1.0.0.md:265` |
| 尚未发起 | `docs/status.md:3` |

统计方法（可复跑）：

```bash
grep -cE "独立验收尚未执行|独立验收尚未开始|独立验收未执行|验收未执行|尚未发起|acceptance not run|acceptance has not started|no independent reviewer" \
  README.md README.zh-CN.md CHANGELOG.md docs/status.md docs/releases/v1.0.0.md \
  docs/reports/v1.0.0-github-release-body.md docs/reports/m10-acceptance-pack.md \
  docs/reports/m10-reader-package.md docs/reports/m10-reader-kit.md docs/reports/README.md
```

计数命令的命中数会随材料改动而变（新增一句就多一处），但**要核的是语义一致，
不是数字相等**。

本轮**没有改动**这些文件：四个由测量脚本写的文件（`README.md`、
`README.zh-CN.md`、`docs/status.md`、`docs/reports/phase1-execution-report.md`）
与 `CHANGELOG.md` 都不在允许改动范围内；其余各处本就一致。

## 6. 声明：本轮没有发送任何东西

- 没有调用任何邮件、平台或 API；没有 `git push`；没有打 tag；没有联网。
- 本轮唯一的写操作是修改 `docs/` 下的 4 个文件（含本文件）。
- `v1.0.0` 这个 tag 在本轮**未被移动**（仍是 `b71bf309b870d92c805629b53900a4a8f9ae98db`）。
- 邀请函尚未发出，因此**没有任何验收记录、没有验收判定、没有评分**；
  M10 的状态仍是「未完成」。
