# 门禁自己站得住：这一轮改了什么

## 这份报告回答什么

上一轮把「同源门禁」（`scripts/check-release-numbers.py`）写了出来，但那一轮有**两件事没做完**，
还有**一个没被发现的问题**：

1. 那个门禁**没有回归测试**——本轮硬约束是不许动 `tests/`（它在源指纹的覆盖范围内），
   所以测试只能等下一轮；
2. 那个门禁**把工作副本的报告当权威**，于是 v1.1.0 一开工、报告重新测量，它就会拿**新数**
   去比 **v1.0.0 已发布**的正文，直接变红——而已发布的那一份本该与**已发布的树**比；
3. 镜像的**构建上下文**现在带着整个 `.git`。

这一轮把三件都做了，并且每一件都留了一条**红→绿**的证据。

**然后主会话用真实的树跑出了两处不对**——都在这个窗口自己写的代码上，都在**这个门禁自己的
立场上**：一处把「示意」当成了「声明」，一处把冻结的发布文档放进了会变的那一段。
那两处的修法、红→绿，以及**一处需要主会话拍板的取舍**，在 §5。

## 基线

| | |
|---|---|
| 仓库 | `E:\Dexatlas`（工作树 `E:\Dexatlas\.claude\worktrees\keen-dubinsky-ae6eb6`） |
| 分支 | `claude/keen-dubinsky-ae6eb6` |
| 基线提交 | `7a416bd`（第一轮）→ `92d8293`（第二轮，v1.0.0 合入之后） |
| 日期 | 2026年11月18日（第一轮）、2026年11月19日（第二轮） |
| 上一轮的报告 | [`outward-number-parity.md`](outward-number-parity.md) |

**这份报告里的数只有一处需要重测后同步**：§4 说的那几项。其余都是可复现的命令与它的输出。

---

## 1. 同源门禁的权威来源，分成两段

### 1.1 原来的问题

门禁原来只读**一个**权威来源——**工作副本**的 `docs/reports/phase1-execution-report.md`——
然后拿它去比**五份**文本（四份工作副本里的文本，加上 GitHub 上已发布的 Release 正文）。

问题出在第五份上：

- 工作副本的报告**每次发版都会重测**。v1.0.0 发出去时它记的是 1712 tests；
  v1.1.0 一开工、报告重测，它会变成别的数。
- 已发布的 v1.0.0 Release 正文说的是**v1.0.0 发出去时**的数，**不会**跟着下一次测量变。
- 拿新的数去比已发布的正文，门禁变红——**而且红得没有道理**：已发布的那一份没有做错任何事。

门禁一旦因为不认账的理由变红，就会被关掉；被关掉的门禁比没有门禁更糟，因为**它还在那儿**，
看起来还在守着。

### 1.2 现在的两段

改成两段，各比各的（段的数据结构是 `Segment`，见 `scripts/check-release-numbers.py:292`）：

| 段 | 比什么 | 权威来源 |
|---|---|---|
| **the working copy** | 四份文本：`docs/how-to-verify.md`、`docs/how-to-verify.zh-CN.md`、`docs/releases/v1.0.0.md`、`docs/reports/v1.0.0-github-release-body.md` | **工作副本**的报告 |
| **the published release v1.0.0** | GitHub 上 v1.0.0 的 Release 正文 | **v1.0.0 tag 树里**的报告 |

第一段跟原来一模一样。第二段是新的：**已发布的那一份，跟它发出去时的那棵树比。**

两段的结果**分开报**：报哪一段比的、哪一份对不上、差在哪个数、哪一行。摘要是这样：

```text
summary
  segment the working copy: 4 source(s)
    mismatches: 0
    not written: 4
  segment the published release v1.0.0: 1 source(s)
    mismatches: 0
    not written: 0
```

### 1.3 读树的那一段，用的是同一套读法

tag 树里的报告是用 `git show v1.0.0:docs/reports/phase1-execution-report.md` 读的。
**没有另造一套**：读一个树里的文件这件事，在本仓库里只有**一个**实现——引文检查器里的
`Tree`（`scripts/check-doc-citations.py`），它读文件用 `git show`，并且把「**这棵树没有这个
文件**」和「**文件是空的**」分得清清楚楚。

门禁直接**引用**它，跟 `scripts/remap-citations.py` 引用引文检查器是同一个做法
（`scripts/check-release-numbers.py:515` 的 `citation_checker()`）。读树的那一段在
`scripts/check-release-numbers.py:572` 的 `tagged_report()`。

### 1.4 退出码

| 码 | 意思 |
|---|---|
| 0 | 两段都对得上 |
| 1 | 有对不上的（或 `--strict` 下有没写的） |
| 2 | **第二段读不出来**——已发布的正文取不到，或 tag 树取不到 |

**2 不是「一致」。** 第二段没跑成，就是第四份文本没有被核对过，脚本会**明说**是哪一样取不到：

```text
published release body: NOT READ -- gh is not installed
...
the published release body could not be read: gh is not installed
```

`--offline` 是**故意**跳过第二段，它会明说「not checked (--offline)」，并且**不**把它当成一致。

---

## 2. 回归测试：`tests/test_release_numbers.py`

### 2.1 那个仓库是**造出来**的

测试不碰网络，也不碰 GitHub。`gh` 那一段被换成一个假函数（返回一段假正文），
其余全部在一个**临时造出来的仓库**里跑——那个仓库有**两棵树**：

- tag `v1.0.0`：报告记着 **100** tests / **98** passed / 91.0% 覆盖，四份文本也写这组数；
- 工作副本：报告被**重新测量**过，记着 **200** tests / **198** passed / 92.0% 覆盖，
  四份文本也跟着同步成了这组数；
- GitHub 上**已发布**的那一份：说的是 **100** / **98**——**它没有错**，它说的就是 v1.0.0 发出去时的数。

已发布的正文是**只读的**；重新发布它是发版动作，不是门禁的事。

### 2.2 六条断言（第二轮又加了两条，见 §5.4）

| 测试 | 钉住什么 |
|---|---|
| `test_the_checker_exists` | 脚本在 |
| `test_the_published_body_is_compared_against_the_tree_it_shipped` | **本轮的核心**：已发布的正文跟 **tag 树**比，不是跟工作副本比（`tests/test_release_numbers.py:323`） |
| `test_a_mismatch_names_the_text_the_number_the_report_and_the_line` | `outward-number-parity.md` §5.5 那条判据 C：哪一份、哪个数、权威是多少、那份写的是多少、**哪一行**——五样齐了（`tests/test_release_numbers.py:404`） |
| `test_the_two_comparisons_are_reported_separately` | 两段分开报，且各自的权威来源写清楚 |
| `test_a_published_body_that_cannot_be_read_is_not_an_agreement` | 取不到 → 退出码 2 + **明说**取不到 |
| `test_a_tag_that_is_not_in_the_checkout_is_not_an_agreement` | tag 不在 checkout 里 → 退出码 2 + **明说** |

判据 C 那一条，断言的是**哪棵树**的数：

```text
mismatches
  the published release v1.0.0
    GitHub release v1.0.0 (published body)  suite.passed
      report: 98
      this text: 96  (line 7)
```

`report: 98` 是 **tag 树**的数；`report: 198` 会是工作副本的数——**旧实现报的是后者**。

### 2.3 红→绿怎么证的

把 `scripts/check-release-numbers.py` 换回 `7a416bd` 的那一版，跑同一份测试（**当前的**这份，
第二轮加过两条，见 §5.4）：

```text
FAILED tests/test_release_numbers.py::test_the_published_body_is_compared_against_the_tree_it_shipped
FAILED tests/test_release_numbers.py::test_a_number_illustrated_in_a_code_block_is_not_a_claim
FAILED tests/test_release_numbers.py::test_the_release_documents_are_compared_against_the_tag_tree
FAILED tests/test_release_numbers.py::test_a_mismatch_names_the_text_the_number_the_report_and_the_line
FAILED tests/test_release_numbers.py::test_the_two_comparisons_are_reported_separately
FAILED tests/test_release_numbers.py::test_a_tag_that_is_not_in_the_checkout_is_not_an_agreement
6 failed, 2 passed
```

（第一轮量的时候是 4 红 2 绿——那时还没有第二轮加的两条。）

第一条失败的现场，正是旧实现说错话的地方：

```text
=== GitHub release v1.0.0 (published body) ===
  suite.passed     98         7            MISMATCH (report: 198)
...
  mismatches: 6
```

已发布的正文说的是 98——**它没做错任何事**——旧实现拿工作副本重新测量出来的 198 去比它，
于是门禁红了。换成新实现：

```text
8 passed
```

**红的几条是行为上的红**（断言失败），不是 setup 里的 `AttributeError`：fixture 里那句
`getattr(module, "citation_checker", None)` 是故意的，好让「把修复拿走」表现为**答案错了**，
而不是表现为「少了一个属性」。

---

## 3. Docker 那条门禁

### 3.1 两条只读文件的快测试

`tests/test_docker_image_samples.py`，**不跑 Docker**，只读两个文件：

| 测试 | 钉住什么 |
|---|---|
| `test_the_samples_are_copied_after_the_dependencies_are_installed` | `COPY examples/ examples/` 在**最后一次 `uv sync` 之后**——否则改一个样本就会让依赖层失效，上头那两层（下载 JADX 和 Apktool）要重跑好几分钟（`tests/test_docker_image_samples.py:138`） |
| `test_the_docker_job_analyses_the_bundled_sample_by_a_relative_path` | CI 的 docker job 里那条命令用的是**相对路径**——相对路径在**容器里**解析，不受宿主把 Windows 路径改写成什么的影响（`tests/test_docker_image_samples.py:163`） |
| `test_the_docker_job_checks_the_counts_the_run_produced` | 那个 job **核了计数**：读回 JSON 报告，对着 floors 断言 classes / methods / call_sites / call_edges——没有这条，一个什么都没分析出来的镜像也能让 job 变绿（`tests/test_docker_image_samples.py:182`） |

那条相对路径的命令在 `.github/workflows/ci.yml:541`。

（第三条是顺带加的：任务里点名的是两条，但它和第二条是同一件事的两半——**用相对路径**跑，
**并且**核了跑出来的数。）

### 3.2 `.dockerignore`

新增一份 `.dockerignore`。镜像的构建上下文现在带着**整个 `.git`**（主 checkout 里 21 MB）、
`docs/`（19 MB）、`tests/` 和本机的工作目录。

**只写这一份文件**，`Dockerfile` 的 `COPY` 一行没动。

写法上有一处是刻意的：目录写成 `name/*` 而不是 `name`。Docker 的忽略名单里，
**不带斜杠**的模式在**任意深度**匹配（`*.apk` 会把 `examples/demo-app/demo.apk` 一起带走）；
带斜杠的才只对**从上下文根算起**的路径生效。所以 `docs/*` 只排掉根上那个 `docs/`，
`src/dexatlas/**/docs/` 这样的目录不受影响——镜像里的东西不会因为一条忽略规则悄悄少掉。

`*.apk` **没有**被排除：样本是镜像被检查的对象，少了它，镜像就没有样本可分析了。

### 3.3 三次变异，每一次都被抓住

| 变异 | 结果 |
|---|---|
| 把 `COPY examples/ examples/` 挪到 `uv sync` 之前 | `test_the_samples_are_copied_after_the_dependencies_are_installed` **红** |
| 把 CI 里的路径改成 `$GITHUB_WORKSPACE/examples/demo-app/demo.apk` | `test_the_docker_job_analyses_the_bundled_sample_by_a_relative_path` **红** |
| 在 `.dockerignore` 里加一行 `*.apk` | `test_the_ignore_list_keeps_everything_the_image_copies` **红**（报的是 `examples/demo-app/demo.apk would not reach the image`） |

第三条一开始**没被抓住**：那时只检查了 `COPY` 的**源**（`examples` 这个目录名），
没检查目录**里面**的文件。现在检查的是 Dockerfile 真正复制进去的每一个文件。

---

## 4. 哪些数字需要重测后同步

**这一轮动了 `tests/`，`tests/` 在源指纹的覆盖范围内**（源指纹把 `src/`、`tests/`、
`pyproject.toml` 和测量脚本一起哈希）。所以报告里的数**过期了**，主会话要在合入后
重跑 `scripts/refresh-report-figures.py`，然后把数同步到四份对外文本里。

### 4.0 先做这一步，否则测量**跑不起来**

`docs/reports/phase1-execution-report.md` 的 §2.1 有一张「按测试文件分布」的表。
**那张表的行是手写的**（生成器只写数字，不写行），而 `scripts/refresh-report-figures.py`
在**测量之前**会比对那张表和磁盘上的 `tests/test_*.py`：

```text
The report's test-file table does not describe the suite:
  the suite has test_docker_image_samples.py; the table does not list it
  the suite has test_release_numbers.py; the table does not list it

Nothing was written. The table's rows are written by hand: add the row that
is missing, or take out the row that is stale.
```

**它会直接返回 1，一个数也不写。** 所以顺序是：**先往 §2.1 的表里加两行**
（`test_docker_image_samples.py`、`test_release_numbers.py`），**再**跑测量。

这是**加两行**，不是改数——所以它属于「谁加都行」的那一类，但本窗口**没有加**：
`docs/` 下的一切是别的窗口在动的，而测量脚本自己会把缺哪两行**点名**说出来。

### 4.1 哪些数会变

需要重测后同步的是 `docs/reports/phase1-execution-report.md` 里 `<!--report-figures:...-->`
记录块中的这些项：

| 记录块里的键 | 现在是多少 | 会变吗 |
|---|---|---|
| `source_fingerprint` | `sha256:18f3ab15…` | **会变**（`tests/` 变了） |
| `tests.total` | 1712 | **会变**：本窗口新增 10 条测试 |
| `tests.fast` | 1563 | **会变**：新增的 10 条都没有 `slow` 标记 |
| `tests.slow` | 149 | 不会变 |
| `suite.passed` | 1710 | **会变** |
| `suite.skipped` / `suite.xfailed` / `suite.failed` | 1 / 0 / 1 | 以脚本量出来的为准 |
| `coverage.pct` / `coverage.covered` / `coverage.total` | 93.3% / 7157 / 7671 | 本窗口没动 `src/`，**应当不变**——但以脚本量出来的为准 |

记录块里的数一变，下面这些地方抄的数就跟着要改（`check-release-numbers.py` 会把它们一条一条
指出来，包括**哪一行**）：

- `docs/how-to-verify.md`
- `docs/how-to-verify.zh-CN.md`
- `docs/releases/v1.0.0.md`
- `docs/reports/v1.0.0-github-release-body.md`

这四份文本里还有**源指纹**的缩写（`sha256:18f3ab15…`），也要一起换。

**在主会话重测之前，main 的 CI 会因为数字过期而红——这是预期的。**

本地把整套测试跑了一遍（第二轮，7 分 48 秒）：**11 failed, 1721 passed, 1 skipped**。
11 条**全部**归因到「报告过期」这一件事上，本窗口**没有留下一条自己造的失败**
（第一轮量的时候是 11 failed / 1710 passed，失败的是同样这 11 条）：

| 失败 | 几条 | 归因 | 加了 §4.0 那两行之后 |
|---|---|---|---|
| `test_docs.py::test_execution_report_numbers_match_the_code` | 1 | 报告里的测试数过期 | 要等重测 |
| `test_docs.py::test_execution_report_coverage_figures_describe_the_current_code` | 1 | 覆盖率过期 | 要等重测 |
| `test_docs.py::test_execution_report_suite_figures_add_up_to_the_tests_that_exist` | 1 | suite 合计过期 | 要等重测 |
| `test_docs.py::test_execution_report_lists_every_test_file` | 1 | §2.1 的表少两行 | **立刻绿** |
| `test_how_to_verify.py::test_the_expected_output_of_the_collect_command_is_what_the_suite_prints` | 4 | 两份 how-to 文档里抄的数过期 | 要等重测 + 同步 |
| `test_how_to_verify.py::test_the_page_states_the_numbers_the_suite_has` | 2 | 同上 | 要等重测 + 同步 |
| `test_refresh_coverage_hygiene.py::test_the_slot_guards_the_checkout_report_only` | 1 | **同一个根因**：测量脚本在「表对不上」那一步就返回 1 了，还没走到 slot 的检查，所以它等的那句 `already running in this checkout` 没出现 | **立刻绿** |

**「加了两行就绿」这件事是量过的**：临时往 §2.1 的表里加了两行（占位文字），
`test_execution_report_lists_every_test_file` 与
`test_the_slot_guards_the_checkout_report_only` **两条立刻变绿**；探针随即撤回，
`docs/reports/phase1-execution-report.md` **一个字节都没留下**。

> 另有一条 `tests/test_evidence_package.py::test_the_cli_counts_the_files_the_reader_finds_in_the_zip`
> 在**第一次**整跑里红了。它是**我自己造成的假象**：那一轮我同时在跑别的 pytest，
> 两边共用 `<repo>/.scratch/tmp`。**干净地重跑一遍，它不红了**（16 passed），
> 整跑也回到 11 条。**同一台机器上不要并发跑两遍 pytest**——临时目录是共用的。

---

## 5. 第二轮：主会话用真实数据跑出来的两处不对

v1.0.0 合入之后，主会话用**真实的树**跑这个门禁（那棵树的树被重新测量过，1731 个测试），
跑出两处不对。**两处都在 `scripts/check-release-numbers.py` 里，都是这个窗口自己写的代码**。

### 5.1 第一处：门禁把「示意」当成了「声明」

`docs/how-to-verify.md` 有一节叫「哪些数字是生成物，不许手改」，它在教读者看标记长什么样，
于是里面有一个**代码块**：

```text
<!--fig:tests.total-->1712<!--/fig-->
```

那是一个**示意**——它展示标记的形状，不是这个项目现在的数。门禁却把它读成了声明：

```text
=== docs/how-to-verify.md ===
  tests.total      1712 / 1731 147, 460     MISMATCH (report: 1731)
```

散文里写的确实是 1731（对的）；报出来的是代码块里那个 1712。zh-CN 那页同理（`:432`）。

**为什么**：门禁原来对 `<!--fig:键-->值<!--/fig-->` 有一条**例外**——「即使在围栏里也要比对，
因为它是生成物的整份拷贝，会跟着测量一起漂」。这条例外是 `outward-number-parity.md` §6.1
写的。它当时是个合理的判断，后来被证伪了：那个标记**不是**生成物的拷贝，是**示意**。
而测量脚本自己**不写**围栏里的标记（`live_figures()` 把代码块与行内代码都剔掉，
见 `scripts/refresh-report-figures.py:1505` `anchor: live_figures`），所以门禁跟测量脚本的尺子本来就不一致。

**改法**：用**同一把尺子**——`scripts/refresh-report-figures.py` 的 `CODE_BLOCK` 与
`INLINE_CODE` 两个正则，**直接引用**它（`scripts/check-release-numbers.py:536` 的
`measurement_script()`，读法与 `scripts/remap-citations.py` 引用引文检查器同一个做法），
不另写一套。围栏里的标记从此是示意，不是声明。

> **一处需要主会话拍板的地方**：本窗口把「行内代码」这条规则用在了**标记**上，
> **没有**用在散文里的数上。理由是具体的：`docs/how-to-verify.md` 的表格里那句
> `` `1710 passed` `` 写在**行内代码**里，而**那一格正是这两页声明 suite.passed 的地方**
> ——`outward-number-parity.md` §4.2 把 `suite.passed` 列在「写了」的数里，把
> `suite.xfailed` 与 `coverage.pct` 列在「没写」里。把行内代码整个剔掉，
> `suite.passed` 就会变成「没写」，门禁从此**看不见**那一栏漂了，`--strict` 还会永远红。
> 那一格表格里的 `1710 passed`、**1 skipped**、**0 xfailed** 是同一句话：前一半在行内代码里，
> 后一半在粗体里，按同一条规则读才对。
>
> 也就是说：**围栏 = 引用**（散文与标记都是），**行内代码 = 示意**（只对标记）。
> 如果主会话要的是「行内代码里的数也不算数」，那是一行的改动
> （`add()` 里把 `code_blocks` 换成 `quotations`），但它会丢掉上面这一栏——
> 请主会话定。

### 5.2 第二处：发布说明与 Release 正文放错了段

`docs/releases/v1.0.0.md` 与 `docs/reports/v1.0.0-github-release-body.md` 说的是
**v1.0.0 那次发布测到的数**。v1.0.0 已冻结（tag 不再重打），所以它们的数属于
**v1.0.0 tag 树**，不属于之后测出来的任何东西。

第一轮把这两份放进了「工作副本」那一段。于是主会话把工作副本重测一遍（1731 个测试）之后，
这两处就红了——**而这正是这一扇窗口要解决的那个问题**：拿新数去比旧正文。

**改法**：正确的切分是

| 段 | 比什么 | 权威来源 |
|---|---|---|
| the working copy | `docs/how-to-verify.md`、`docs/how-to-verify.zh-CN.md`（描述当前树的两页） | 工作副本的报告 |
| the published release v1.0.0 | `docs/releases/v1.0.0.md`、`docs/reports/v1.0.0-github-release-body.md`、GitHub 上已发布的正文 | **v1.0.0 tag 树里**的报告 |

**这一轮没有动那两份文档里的任何数字**——它们是 v1.0.0 的历史记录。

### 5.3 两处的红→绿，都是拿主会话那棵树量的

把主会话 checkout 里那几份文件（报告 1731、散文 1731、围栏里 1712）原样搬进工作树，
用**改之前**的实现跑：

```text
=== docs/how-to-verify.md ===
  tests.total      1712 / 1731 147, 460     MISMATCH (report: 1731)
=== docs/how-to-verify.zh-CN.md ===
  tests.total      1712 / 1731 120, 432     MISMATCH (report: 1731)
=== docs/releases/v1.0.0.md ===
  tests.total      1712       94, 242      MISMATCH (report: 1731)
=== docs/reports/v1.0.0-github-release-body.md ===
  tests.total      1712       167, 267     MISMATCH (report: 1731)
...
  mismatches: 13
```

用**改之后**的实现跑**同一棵树**：

```text
=== segment: the working copy ===
=== docs/how-to-verify.md ===
  tests.total      1731       147          ok
=== segment: the published release v1.0.0 ===
=== docs/releases/v1.0.0.md ===
  tests.total      1712       94, 242      ok
=== docs/reports/v1.0.0-github-release-body.md ===
  tests.total      1712       167, 267     ok
...
  mismatches: 0
```

**13 处不符 → 0 处不符，退出码 1 → 0。**
复现完就把工作树里那几份文件换回来了，`git status` 干净。

### 5.4 两条新的回归测试

`tests/test_release_numbers.py` 从 6 条变成 8 条：

| 测试 | 钉住什么 |
|---|---|
| `test_a_number_illustrated_in_a_code_block_is_not_a_claim`（`tests/test_release_numbers.py:465`） | 代码块里与行内代码里的**示意**不是声明 |
| `test_the_release_documents_are_compared_against_the_tag_tree`（`tests/test_release_numbers.py:495`） | 发布说明与 Release 正文跟 **tag 树**的报告比，不跟工作副本的比 |

**红→绿**：换回改之前的实现 → **3 红 5 绿**，红的是**行为上的红**：

```text
  tests.total      100 / 200  3, 16, 19    MISMATCH (report: 200)   ← 示意被读成了声明
  tests.total      100        3            MISMATCH (report: 200)   ← 发布说明被拿工作副本的数比
```

换成改之后的实现 → 8 passed。

---

## 6. 留给主会话的事

| # | 事情 | 为什么是主会话的 |
|---|---|---|
| 1 | **拍板「行内代码里的数算不算声明」**（§5.1 末尾那个方框） | 本窗口把它用在了标记上，没有用在散文里的数上——理由写在 §5.1，但**这是主会话的判断**：改了会丢掉两页的 `suite.passed` 那一栏，改法是一行 |
| 2 | **先往执行报告 §2.1 的测试文件表里加两行**（`test_docker_image_samples.py`、`test_release_numbers.py`）——**然后**才跑测量（§4.0） | 那张表的行是手写的，测量脚本不会替人写；不加，测量会**一个数也不写**就返回 1。`docs/` 下的一切是别的窗口在动的 |
| 3 | **重测并同步四份文本里的数**（§4.1） | 测量是独占的，并发跑会互相污染覆盖率 |
| 4 | **登记这份报告**：`docs/reports/README.md` 的索引（分组一览的份数 + 那一行）与 `scripts/check-doc-citations.py` 的 `DOCS` 名单 | 那两处由主会话统一登记。本窗口只写了报告本身 |
| 5 | **把这份报告的 `file:line` 引文核一遍** | 登记进 `DOCS` 之后，引文检查器就会开始核它。本窗口写完后自查过，但别的窗口改动 `src/` 会让行号移动——那之后要跑 `uv run --no-sync python scripts/remap-citations.py` 再跑检查器 |

**本窗口自己做的**（不在你给的文件名单里，但**必须**做，否则这一轮的改动在 CI 上不成立）：

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `.github/workflows/ci.yml` | `release-numbers` job 的 checkout 加了 `fetch-depth: 0`（`.github/workflows/ci.yml:876`） | 第二段要读 **tag 树**里的报告，而那个 job 原来的 checkout 是**浅克隆**，里面没有 `v1.0.0` 这个 tag。同一份文件里另外四个需要 tag 的 job 早就是 `fetch-depth: 0` 了，这里是照着它们的样子加的 |

如果这一行不加，CI 上那个 job 会以退出码 2 结束，并报
`the v1.0.0 tree could not be read: the v1.0.0 tag is not in this checkout`——
**取不到就说取不到**，但那是一个假的红灯：CI 的 checkout 不是浅的就好了。

---

## 7. 这一轮动了哪些文件

| 文件 | 性质 |
|---|---|
| `scripts/check-release-numbers.py` | 改：分成两段；围栏与行内代码里的**标记**是示意；发布说明与 Release 正文归到已发布那一段 |
| `tests/test_release_numbers.py` | 新：8 条 |
| `tests/test_docker_image_samples.py` | 新：4 条 |
| `.dockerignore` | 新 |
| `.github/workflows/ci.yml` | 改：见 §6 |
| `docs/reports/gate-self-checks.md` | 新：本报告 |

**没有动**：`scripts/refresh-report-figures.py`（只**引用**它）、`docs/` 下的一切（除新增本报告）、
`docs/reports/README.md`、`scripts/check-doc-citations.py`、`Dockerfile`、
`docs/releases/v1.0.0.md`、`docs/reports/v1.0.0-github-release-body.md`、
`docs/how-to-verify.md`、`docs/how-to-verify.zh-CN.md`。
