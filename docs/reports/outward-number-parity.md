# 对外文本里的同一批数字：一个机器比对（outward-number-parity）

**状态：门禁已接上并跑通；本轮没有改那四份文本里的任何一个数字。**

- **日期**：2026-11-18
- **对象**：上游审计报告
  [`docs/reports/post-release-rehearsal.md`](post-release-rehearsal.md) 的**判据 C**
  （`:364`）——「把『同一批数字相等』写成一份写下来的清单，并让每一份副本都有东西在比」。
  该判据核出的现状是：测试数与覆盖率有东西在比，**passed / skipped 这一批**在四份对外
  文本里**一个都没在比**。
- **基线**：本树 `docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` 标记
  （`:76`、`:77`、`:143`–`:145`、`:881`）——它是这批数字的权威来源，由
  `scripts/refresh-report-figures.py` 从一次完整测量写出；以及 GitHub 上**已发布**的
  `v1.0.0` Release 正文（`gh release view v1.0.0 --json body`，取于 2026-11-18）。
- **本轮的动作**：**新增** `scripts/check-release-numbers.py`、一处 CI job、本文件；
  **改动** `scripts/check-gate-coverage.py`（把新门禁登记进 GATES 名单）、
  `scripts/check-doc-citations.py`（把本文件登记进 DOCS 名单）、
  `docs/reports/README.md`（索引与份数）。**没有**改 `src/`、`tests/`、`pyproject.toml`、
  `scripts/refresh-report-figures.py`；**没有**跑 `scripts/refresh-report-figures.py`
  （主会话正在跑完整测量，并发会互相污染覆盖率）；**没有**改那四份文本里的任何数字。

---

## 0. 结论速览

| | |
|---|---|
| 比对的数字 | **9 个**：测试总数、快测、集成、passed、skipped、xfailed、一方覆盖率，以及覆盖率背后的两个行数（7136 / 7650） |
| 权威来源 | 执行报告的 `<!--fig:…-->` 标记，**脚本从报告里读**，不抄 |
| 被比的文本 | **4 份**：两份 how-to-verify、发版说明、**GitHub 上已发布的那一份 Release 正文** |
| 外加一份 | 仓库里的 Release 正文源文件 `docs/reports/v1.0.0-github-release-body.md`（发布正文的出处），拿来跟已发布的那一份对 |
| 仓库内的三份 | **彼此一致，也与权威来源一致** |
| **已发布的那一份** | **不一致**：15 处。它写的是**旧树**上的数（1620），tag `v1.0.0` 指向的树上是 1695 |
| 「没写」 | **4 处**：两份 how-to-verify 都没写 xfailed，都没写覆盖率 |
| CI | 新 job `release-numbers`（`.github/workflows/ci.yml` 末尾），阻塞式 |
| 退出码 | 0 一致 / 1 有数对不上 / 2 已发布的正文取不到 |

**一句话**：这批数字**机器一个都没在比**这件事，现在有一个门禁在比了；**门禁第一次跑
就报出了真东西**——GitHub 上已发布的那一份 Release 正文，写的是发版之前那棵树上的数。

---

## 1. 查了什么

### 1.1 这批数字是哪几个

上游判据 C 把「同一批数字」留给这一轮写下来（`:370`：「『四份对外文本的同一批数字
集合相等』这句话里的『同一批数字』，**要写下来**」）。本轮写下来的清单是：

| 键 | 是什么 | 权威来源（执行报告里的标记） |
|---|---|---|
| `tests.total` | 测试总数 | `<!--fig:tests.total-->`（`:76`、`:145`） |
| `tests.fast` | 快测数（`-m "not slow"`） | `<!--fig:tests.fast-->`（`:76`、`:143`） |
| `tests.slow` | 集成数（`-m slow`） | `<!--fig:tests.slow-->`（`:76`、`:144`） |
| `suite.passed` | 完整环境下的 passed | `<!--fig:suite.passed-->`（`:881`） |
| `suite.skipped` | 完整环境下的 skipped | `<!--fig:suite.skipped-->`（`:881`） |
| `suite.xfailed` | 完整环境下的 xfailed | `<!--fig:suite.xfailed-->`（`:881`） |
| `coverage.pct` | 一方代码覆盖率 | `<!--fig:coverage.pct-->`（`:77`） |
| `coverage.covered` | 覆盖行数 | `<!--fig:coverage.covered-->`（`:77`） |
| `coverage.total` | 总行数 | `<!--fig:coverage.total-->`（`:77`） |

**权威来源的读法**：脚本按 `<!--fig:键-->值<!--/fig-->` 从
`docs/reports/phase1-execution-report.md` 里**读**这九个值。脚本里没有一份写死的期望值
列表——那样写就是把这批数字再抄一份，抄错的地方还是抄错。

### 1.2 被比的四份文本

| # | 文本 | 怎么取 |
|---|---|---|
| 1 | `docs/how-to-verify.md` | 仓库里的文件 |
| 2 | `docs/how-to-verify.zh-CN.md` | 仓库里的文件 |
| 3 | `docs/releases/v1.0.0.md` | 仓库里的文件（发版说明） |
| 4 | GitHub 上 `v1.0.0` 的 **Release 正文** | `gh release view v1.0.0 --json body` |

第 4 份在仓库里**没有对应物**：它的出处是
`docs/reports/v1.0.0-github-release-body.md`，**发布正文 = 该文件去掉 `## Appendix` 一节**。
所以脚本额外做两件事：

- 把仓库里那份源文件的正文段（去掉附录）也跟权威来源比一遍；
- 把**已发布的那一份**跟**仓库里那份**逐个数对一遍——这一对才是「发布出去的和仓库里的是不是
  同一份」。

### 1.3 此前有没有东西在比

没有。判据 C 的表（`:379`）写着 `passed / skipped` 这一批「**无**」，「已发布的那一份」
「**无**（人工 `gh release view` + diff）」。

有**两样**东西沾着这批数字，但都不是「四份之间相等」：

- `tests/test_how_to_verify.py` 比的是**那一页**说的三个数（总数 / 快 / 集成）与**套件实际
  收集到的数**——是「页面对套件」，不是「四份文本互相」。
- `scripts/check-version-claims.py` 的对外规则只覆盖 `docs/outreach/`、`docs/case-studies/`、
  `docs/proposals/`（`OUTWARD_DIRECTORIES`）——**够不到**本轮这四份里的任何一份。

---

## 2. 这批数字实际写在哪些行

这是本轮核出来的事实（2026-11-18 的树）。**行号是事实，不是承诺**：主会话重测之后这些行
会变。

### 2.1 仓库内的三份 + 发布正文的源文件

| 数字 | `docs/how-to-verify.md` | `docs/how-to-verify.zh-CN.md` | `docs/releases/v1.0.0.md` | `docs/reports/v1.0.0-github-release-body.md` |
|---|---|---|---|---|
| 测试总数 | `:147`、`:456` | `:120`、`:428` | `:94`、`:242` | `:167`、`:267` |
| 快测 | `:147` | `:120` | `:94` | `:167`、`:267` |
| 集成 | `:147` | `:120` | `:94` | `:167`、`:267` |
| passed | `:168` | `:145` | `:95` | `:168`、`:175`、`:267` |
| skipped | `:168` | `:145` | `:95` | `:168`、`:268` |
| xfailed | **没写** | **没写** | `:95` | `:168`、`:267` |
| 覆盖率 | **没写** | **没写** | `:98` | `:170`、`:176`、`:268` |
| 覆盖行数 | **没写** | **没写** | `:98` | `:170`、`:268` |

三处需要说明的：

- **`:456` / `:428`**：那是代码围栏里**示例**的一段
  `<!--fig:tests.total-->1695<!--/fig-->`，用来展示「生成物长什么样」。它是一份**手抄的
  副本**，本门禁**要**它跟权威来源一致（见 §6.1）。
- **`:153`–`:154` / `:126`–`:127`**：两段代码围栏里的
  `# → 1546/1695 tests collected (149 deselected)`。也是手抄的副本，但**不**参与比对
  （见 §6.1）。这一条是本门禁**够不到**的地方，§6.2 里记着。
- **`:242`**（发版说明）：「release measurement says 1695 tests at 93.3%」——叙述旧发现时
  引用的数，和上面那些是同一个数。

### 2.2 已发布的那一份（`gh release view v1.0.0 --json body`）

| 数字 | 发布正文里的行 | 值 |
|---|---|---|
| 测试总数 | `:164`、`:264` | **1620** |
| 快测 | `:164`、`:264` | **1473** |
| 集成 | `:164`、`:264` | **147** |
| passed | `:165`、`:172`、`:264` | **1620** |
| skipped | `:165`、`:265` | **0** |
| xfailed | `:165`、`:264` | 0（与报告一致） |
| 覆盖率 | `:167`、`:173`、`:265` | 93.3%（与报告一致） |
| 覆盖行数 | `:167`、`:265` | **7117 / 7631** |

（行号是**已发布正文**里的行号，与仓库里那份源文件的行号不同——两份不是逐字节相同。）

---

## 3. 四份各自的值

权威来源（执行报告）写的：

| | |
|---|---|
| 测试总数 | 1695 |
| 快测 + 集成 | 1546 + 149 |
| 完整环境下的汇总 | 1694 passed + 0 xfailed + 1 skipped |
| 一方覆盖率 | 93.3%（7136 / 7650 行） |

四份各自的：

| | how-to-verify | how-to-verify.zh-CN | 发版说明 | **已发布的正文** | 仓库里的正文源文件 |
|---|---|---|---|---|---|
| 测试总数 | 1695 | 1695 | 1695 | **1620** | 1695 |
| 快测 | 1546 | 1546 | 1546 | **1473** | 1546 |
| 集成 | 149 | 149 | 149 | **147** | 149 |
| passed | 1694 | 1694 | 1694 | **1620** | 1694 |
| skipped | 1 | 1 | 1 | **0** | 1 |
| xfailed | 没写 | 没写 | 0 | 0 | 0 |
| 覆盖率 | 没写 | 没写 | 93.3% | 93.3% | 93.3% |
| 覆盖行数 | 没写 | 没写 | 7136 / 7650 | **7117 / 7631** | 7136 / 7650 |

**仓库内的三份彼此一致，也与权威来源一致。已发布的那一份不一致。**

---

## 4. 目前对不上的

### 4.1 已发布的那一份 Release 正文（15 处）

`gh release view v1.0.0 --json body` 取回的正文，与权威来源差在这些数上：

| 数 | 权威来源 | 已发布的正文 | 正文里的行 |
|---|---|---|---|
| 测试总数 | 1695 | 1620 | `:164`、`:264` |
| 快测 | 1546 | 1473 | `:164`、`:264` |
| 集成 | 149 | 147 | `:164`、`:264` |
| passed | 1694 | 1620 | `:165`、`:172`、`:264` |
| skipped | 1 | 0 | `:165`、`:265` |
| 覆盖行数 | 7136 | 7117 | `:167`、`:265` |
| 总行数 | 7650 | 7631 | `:167`、`:265` |

**证据链**（只读核过）：

1. 已发布的正文，与仓库里 `docs/reports/v1.0.0-github-release-body.md` 在提交
   **`75976e0c`**（2026-11-18 00:32:21 +0800）时的正文段**逐字节相同**。
2. `75976e0c` 在 tag `v1.0.0`（`3e943b5`，2026-11-18 20:33:34 +0800）**之前 109 个提交**。
3. tag `v1.0.0` 指向的树里，那份正文源文件写的已经是 1695 / 1694 / 1 skipped / 7136 /
   7650，指纹 `sha256:f688245e…`；已发布的那一份写的还是 1620 一族，指纹
   `sha256:975afa8e…`。
4. GitHub 上这次 Release 的发布时间是 **2026-11-17T14:45:39Z**，**早于** tag 被打到
   `3e943b5` 的时间。

也就是说：**已发布的那一份正文描述的是 tag 现在不指向的那棵树**。发版说明
（`docs/releases/v1.0.0.md`）和仓库里的正文源文件都是新的，只有发布出去的那一份没有跟着
更新。

这不是本轮造成的。本轮只是**第一次让机器说出这件事**。

### 4.2 「没写」的四处

| 文本 | 没写的数 |
|---|---|
| `docs/how-to-verify.md` | `suite.xfailed`、`coverage.pct`（连同它的两个行数） |
| `docs/how-to-verify.zh-CN.md` | 同上 |

这两页是**指路**页（「这页本身不重复结论，只讲**去哪里核**」），它们把数字交给执行报告，
所以覆盖率不写是对的。**xfailed 没写**是一件值得主会话决定的事：这两页写明了 passed 与
skipped，却没写 xfailed——一旦完整测量里出现 xfailed，这两页不会自己发现。

**这四条不使门禁变红**（脚本默认只在「写了但写错」时失败；`--strict` 会连「没写」一起算
失败）。理由写在脚本的 `--strict` 帮助里，也写在这里：一份**没写**某个数的文档和一份
**写错**某个数的文档不是一回事，把两者混成同一个退出码，这个门禁第一次跑就会因为两份
指路页而永远红着。

### 4.3 本门禁够不到、但仍是手抄副本的地方

| 位置 | 抄的是什么 | 现状 |
|---|---|---|
| `docs/how-to-verify.md:153`–`:154`、`docs/how-to-verify.zh-CN.md:126`–`:127` | `# → 1546/1695 tests collected (149 deselected)` | 围栏块内的命令输出样例，本门禁按「引用」处理，不比 |
| `docs/portfolio.md:67`–`:68` | `1,695 tests at 93.3% coverage` | **第五份副本**，既不在本门禁的四份里，也不在 `check-version-claims.py` 的对外目录里 |
| `docs/outreach/*`、`docs/case-studies/*`、`docs/proposals/*` | 测试数与覆盖率 | 已有 `check-version-claims.py` 的对外规则在比 |
| `docs/status.md`、两份 README 的徽章 | 测试数与覆盖率 | 由 `scripts/refresh-report-figures.py` 写出，**不是手抄** |

---

## 5. 脚本与门禁

### 5.1 怎么跑

```bash
uv run --no-sync python scripts/check-release-numbers.py            # 比四份 + 仓库里的源文件
uv run --no-sync python scripts/check-release-numbers.py --strict   # 连「没写」也算失败
uv run --no-sync python scripts/check-release-numbers.py --offline  # 明确跳过已发布的那一份
uv run --no-sync python scripts/check-release-numbers.py --repo owner/name
```

只用标准库（`argparse`/`json`/`re`/`shutil`/`subprocess`/`decimal`），不碰 `src/`。

### 5.2 退出码

| 码 | 意思 |
|---|---|
| 0 | 写出来的数都跟权威来源一致 |
| 1 | 有数对不上，或同一份文本对同一个数说了两种话 |
| 2 | **已发布的那一份取不到**（没有 `gh`、`gh` 失败、正文为空）——这一轮的比对**不完整**，不等于「一致」 |

`--offline` 时脚本会**明说**「published release body: not checked (--offline)」，并且**不**
把它当成一致。

### 5.3 CI

`.github/workflows/ci.yml` **末尾**新增一个 job（没有动 `docker` job）：

```yaml
  release-numbers:
    name: The outward texts agree on the release numbers
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync --extra dev --frozen
      - name: The outward texts agree on the release numbers
        env:
          GH_TOKEN: ${{ github.token }}
        run: >-
          uv run --no-sync python scripts/check-release-numbers.py
          --repo "${{ github.repository }}"
```

`GH_TOKEN` 是读已发布 Release 正文要的（`contents: read` 就够，工作流顶层的权限已经是它）。

**这个 job 现在是红的，而且应该红**：已发布的那一份写的还是旧树上的数（§4.1）。它会一直红
到有人重新发布那份正文为止——那正是它该做的事。

### 5.4 门禁名单

`scripts/check-gate-coverage.py` 的 `GATES` 里加了

```python
"scripts/check-release-numbers.py": "the release numbers the outward texts state",
```

`scripts/check-gate-coverage.py` 现在认得它，并报出「runs in ci.yml」：

```text
  PASS scripts/check-release-numbers.py runs in ci.yml -- the release numbers the outward texts state
All 10 gates are run by something.
```

（这个脚本会盯两件事：新门禁必须在名单里；名单里的门禁必须被某个 workflow 或某个测试
跑。两头都过了。）

### 5.5 红→绿

判据 C 要求新检查「必须报出『哪一份文本的哪一行还是旧数』，而不是只说『不一致』」
（`:388`）。核过：

1. 把执行报告里 `<!--fig:suite.passed-->` 的值从 1694 改成 1690，跑脚本 →
   退出码 1，并且报的是：

   ```text
   mismatches
     docs/how-to-verify.md  suite.passed
       report: 1690
       this text: 1694  (line 168)
   ```

   ——是哪一份、哪个数、仓库里是多少、那份写的是多少、外加**哪一行**，五样齐了。
2. 改回去，脚本不再报这一条（余下的只有 §4.1 那 15 条真差异）。
3. 执行报告已按原样还原（`git diff` 为空）。

**这个门禁在数被改动时会红，在数没被改动时绿。**

---

## 6. 这个门禁的比对边界

门禁能抓什么、够不到什么，写在这里，免得它被当成比它实际更大的东西。

### 6.1 围栏块按「引用」处理

代码围栏里的内容是**引用**（命令的输出样例、某个检查器打印的东西），不是对当前树的断言
——这跟 `scripts/check-version-claims.py` 对「引号里的版本号不算断言」的处理是同一个约定。
所以：

- `docs/how-to-verify.md:153`–`:154` 里的 `1546/1695 tests collected` **不**比对；
- `docs/how-to-verify.md:221`–`:224` 里那份检查器输出样例（含 `91.0%`、`91.6%` 这些**历史**
  版本的覆盖率）**不**比对。

**例外**：`<!--fig:键-->值<!--/fig-->` 这样的**闭合标记**，即使在围栏里，也要比对。它是
生成物的**整份拷贝**，会跟着测量一起漂（v1.0.2 那轮它落在 `docs/how-to-verify.md`
§4.7 的示例围栏里，v1.1.0 重测后该示例更新为 147，引用随之重锚到当前树）。

### 6.2 「另一套环境」的汇总不算数

`docs/how-to-verify.md:167` 与 `docs/how-to-verify.zh-CN.md:144` 那一行写的是 `1664 passed, 31 skipped`
——**没取第三方样本**的那次运行。它是真的数、另一个环境的数，不是发版声称的那一次。脚本按
行内的措辞（`**没**取第三方样本` / `**取了**第三方样本` / `完整环境` / `full environment`）
把它认出来，**列出来但不比对**。

### 6.3 附录不比对

发布正文源文件的 `## Appendix` 一节是**出处表**，不贴进 GitHub Release。脚本只比它之前
的正文段。附录里那些「`1620 passed`」之类的行因此不会被当成断言。

### 6.4 读不出来就算「没写」，不猜

一个数在一份文本里读不出来时，脚本报「not written」，**不**去猜它写在了别处、也**不**拿别的
环境下的同名数来顶。

---

## 7. 需要主会话接手的事

按「谁的活」分：

| # | 事情 | 为什么是主会话的 |
|---|---|---|
| 1 | **重新发布 v1.0.0 的 Release 正文**，让已发布的那一份与 tag 指向的树一致 | 发版动作；本轮只读，没有动 GitHub 上的任何东西。命令在 `docs/reports/post-release-rehearsal.md` 的判据 B 一节（`:433`） |
| 2 | **重测之后同步四份文本里的数** | 本轮按约束**没有**改那四份文本里的任何数字，也没有跑测量脚本 |
| 3 | **给这个脚本配一条 `tests/` 里的回归测试** | 本轮的硬约束是**不碰 `tests/`**（它是源码指纹的覆盖范围）。建议照 `tests/test_docs.py` 的样子：把 §5.5 那条「红→绿」写成断言 |
| 4 | **决定 `suite.xfailed` 在两份 how-to-verify 里写不写** | §4.2：那两页写了 passed 与 skipped，没写 xfailed。要么补上，要么在门禁里显式承认「这两页不写这个数」 |
| 5 | **决定 `docs/portfolio.md:67`–`:68` 归不归这个门禁** | §4.3：它是第五份副本，两边都没有东西在比它 |
| 6 | **`docs/portfolio.md:68` 的 CI job 数** | 本轮新增一个 CI job（`release-numbers`），工作流里的 job 定义从 **13** 个变成 **14** 个；那一行写的是「twelve CI jobs」——**在 HEAD 上就已经是 13 个对 12 个**，不是本轮造成的，但本轮把它推得更远了 |
| 7 | **CI 里这个 job 的状态** | 它现在是红的（§5.3）。如果主会话打算在重新发布正文之前先合这个门禁，要么先重新发布，要么把 job 临时标成不阻塞——**但那要写下来**，不能让一个红 job 变成一个说不清的绿 |

---

## 8. 本窗口做了什么、留给主会话什么

**本窗口（本批次）做了：**

- 新增 `scripts/check-release-numbers.py`（只用标准库；读权威来源、读四份文本、读已发布的
  正文；逐个数比对；退出码 0/1/2 有意义）。
- 在 `.github/workflows/ci.yml` **末尾**新增 job `release-numbers`（没有动 `docker` job）。
- 在 `scripts/check-gate-coverage.py` 的 `GATES` 里登记新门禁。
- 写本文件；在 `docs/reports/README.md` 的 §6 登记并把份数改对；在
  `scripts/check-doc-citations.py` 的 `DOCS` 里登记本文件。
- 核出并写明：已发布的那一份 Release 正文写的是旧树上的数（§4.1，附证据链）。
- **顺带修了引用门禁**：往 `scripts/check-doc-citations.py` 的 `DOCS` 里加一行会让
  `post-release-rehearsal.md` 里引 `tree_of()` 的两处行号移位——用
  `scripts/remap-citations.py` 重锚了；另外那一份报告里有两处 §7 N6 的引用指向
  `docs/reports/v1.0.0-release-checklist.md` 的第 448 行，而那在 HEAD 上就是**空行**
  （§7 N6 现在在那一份清单的第 463 行）——这是**上一个窗口**留下的，不是本轮造成的，
  但门禁要求 `drifted: 0`，所以一并重锚了。

**留给主会话：**

- 重新发布 Release 正文（§7 第 1 条）。
- 重测之后同步四份文本（以及 `docs/portfolio.md`）里的数字（§7 第 2 条）。
- 补 `tests/` 里的回归测试（§7 第 3 条）。
- 决定 xfailed 与 portfolio.md 两件事（§7 第 4、5 条）。
- 本窗口**没有**跑 `scripts/refresh-report-figures.py`，**没有**改 `src/`、`tests/`、
  `pyproject.toml`、`scripts/refresh-report-figures.py`——这四样是源码指纹的覆盖范围，
  改了报告里的数就过期。
