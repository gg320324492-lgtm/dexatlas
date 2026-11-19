# 引用检查器能验「句中含值」的引用了

**日期：** 2026-11-19
**性质：** 改 `scripts/check-doc-citations.py`（逻辑）+ `tests/test_doc_citations.py`（新增测试），
外加 `docs/reports/post-release-rehearsal.md` 的 4 处行号重锚（**我的改动让
`scripts/check-doc-citations.py` 的行号整体下移**，那 4 处引用跟着走；用仓库自己的
`scripts/remap-citations.py` 重锚，其中 `TREE_DOCUMENTS` 那一处 remapper 判不出来
——它的规则是「只移动 checker 说符号已经离开被引范围的那些引用」，而这个符号是一张
字典、出现的位置太分散——按 remapper 自己的说法「一个数字不值得猜」，由人改）。
**没有动** `src/`、**没有动** `scripts/refresh-report-figures.py`、**没有动**
`docs/` 下别的文件。
**没跑** `scripts/refresh-report-figures.py`（主会话在跑）——**本窗口改了
`scripts/`，源码指纹变了，合入后必须重测一轮**。

**本报告里的行号**一律指 `v1.0.0` 那棵树（`git show v1.0.0:<file>`），因为本轮
说的每一处引用漂移都在那棵树上。

---

## 0. 结论速览

| | |
|---|---|
| 治的病 | 引用检查器只验「名了符号」的引用；「只指位置」的那一类**只验被引范围不是空行**，不验那行说的是不是那句话 |
| 这一批加的检查 | 引用句里**含具体值**时，拿那个值跟被引行的**实际值**比 |
| 现在比得上的值 | 带量词的计数（`1694 passed`）、百分数（`93.3%`）、指纹（`sha256:18f3ab15…`） |
| 比不上的（归「无法比对」） | 裸数字、限值（`≥16/20`）、版本号、章节号、引用块里的数、表格序号 |
| 真发现 | **13 处**，全在 `docs/reports/v1.0.0-github-release-body.md` 的附录表里；其中 **3 处正是本轮要抓的那三条错位** |
| 门禁 | `drifted: 0` / `unresolved paths: 0` / 退出码 **0**；值的不符**单列一档**（`values not matching: 13`），**先不参与退出码**（理由见 §5） |

---

## 1. 病在哪：门禁守的是它能守的，不是它该守的

`scripts/check-doc-citations.py` 把引用分两类：

| 类别 | 判定 | 验什么 | 盲区 |
|---|---|---|---|
| **名了符号** | `is_symbolic(name)` 或被引的行里出现了这个名字 | 名字**在不在** | 无 |
| **只指位置** | 两条都不成立 | **只验「被引的范围不是空行」** | 那行**说的是不是那句话** |

实测的后果（`v1.0.0` 树）：release body 对 `docs/reports/phase1-execution-report.md`
的 10 处引用里，检查器认出的 `names` 全空、`is_compared` 全 False —— **全部落在
验不了的那一类**。其中三处**在 `v1.0.0` 树里就已经各偏了 2 行**：

| release body 写的 | 被引行实际是 | 该值实际在 |
|---|---|---|
| `:848`（`Two third-party integration fixtures…`） | `uv sync --extra dev --extra analysis --extra demo` | **850** 行 |
| `:879`（`1694 passed + 0 xfailed + 1 skipped`） | `uv run pytest --cov=dexatlas --cov-report=term` | **881** 行 |
| `:1098`（`Source fingerprint `sha256:18f3ab15…``） | `  },` | **1100** 行 |

旧检查器一条都报不出来（那三行都**不是空行**）。

## 2. 判据怎么定的

### 2.1 什么算「值」

只有三种：

1. **带量词的计数**：`1694 passed`、`7136 / 7650 lines`、`Two third-party integration fixtures`。
   量词是「这是个数」的证据：`| 1 |` 是表格行号，`200 / 404` 是状态码，
   `120 s` 里的 `s` 只有一个字母——都不是量词。
2. **百分数**：`93.3%`。
3. **指纹**：`sha256:18f3ab15…`（≥8 位十六进制、至少含一个数字）。

### 2.2 什么不算（归「无法比对」，不报「不符」）

| 排除 | 例子 | 为什么 |
|---|---|---|
| 裸数字 | `| 1 |`、状态码 `404` | 标签，不是测量值 |
| 限值 | `≥16/20` | 这是验收线，跟那次跑出来的数无关 |
| 章节号 | `§3`、`第 3 节` | 指的是别的东西 |
| 版本号 | `2.11.1`、`v1.0.0` | 版本不是测量值 |
| 派生值 | `= 75%` | 句子自己算出来的 |
| 连字符复合词 | `Level-1`、`level-2` | `1` 属于 `Level-1` |
| 反引号里的数 | `1632 tests at 93.3% coverage` | 那是**引文**，不是本文的主张 |
| 直角引号/引号里的数 | `「1632 tests…��` | 同上 |
| 围栏代码块里的数 | 门禁自己的输出 | 那是样例输出 |
| 标题里的数 | `### 5.1 JSON 报告顶层字段` | 那是章节号 |

### 2.3 值归哪条引用

* **表格行**按**单元格**读：一个单元格里写的数是**它旁边那个格子**里的引用的主张
  （出处表说「这个数是从那儿来的」）；数跟引用**同一个格子**，就是这条引用自己的主张；
  跟引用**隔着一个以上格子**，就谁都不属于。
* **散文**按**距离**：数归离它最近的那条引用。
* 一条引用**已经有名了符号的检查**（句子点了 `check()`、`_rest_requests()`）时，
  **不再拿值去比**：那时的数是**数这个符号装了多少东西**
  （「`_rest_requests()` 里的 28 个检查」），不是那行该写的数。
* 句子点名了**另一棵树**（`75976e0`、某个 tag）时，整段不比：它说的是那棵树，
  不是本文锚定的那棵树。

### 2.4 比的时候怎么判「不符」

按这个顺序，三档：

1. **被引行带着这个数**（数词和量词都对得上）→ 主张成立，不报。
2. **被引行带着同一个词、另一个数**（`"failed": 1` vs 句子的 `0 failed`）→
   **矛盾**，报，并把两个数都写出来：`the sentence says `0 failed`, the cited line says `1 failed``。
3. **被引行根本没带这个数** → **引用指错了地方**，报，并尽量指出这个数**现在在哪一行**。

第 3 档的「现在在哪一行」只指**按句子的写法带着这个数**的行（`1710 passed`
带 `passed`，`两个` 带量词 `个`）；只带着数字的行不算——一个出现在五处的数字，
指哪一处都不算指。它取的是**离被引行最近**的那一处，所以一个在很多地方出现过的
数，它可能指到另一处：`:343` 那条的提示是 `:340`（那里有「5 项阻断」），
而样例 APK 那句在 `:372` 附近。**提示是指路的，不是证明**——改之前先读那一行。

### 2.5 跨树

跟符号检查一样：**值从文档声明的那棵树里读**。release body 绑的是 `v1.0.0`，
它的值就拿 `v1.0.0` 那棵树比，不是工作区（`tests/test_doc_citations.py`
里的 `test_the_value_is_read_out_of_the_tree_the_document_declares` 守这条）。

---

## 3. 真发现：release body 的附录表有 13 处对不上

**这 13 处全在 `docs/reports/v1.0.0-github-release-body.md` 的附录表里**
（`docs/reports/v1.0.0-github-release-body.md:297` 起）。成因查得出来：
`47b9572`（最终测量落定）把**正文**的数从 1695 一族同步成了 1712 一族，
**附录表没跟**——`scripts/check-release-numbers.py` 也不管附录
（发布时用 `sed '/^## Appendix/,$d'` 把附录裁掉），所以没有人看见。

| release body | 它写的 | `v1.0.0` 树上的真值 | 该改成 |
|---|---|---|---|
| `:297` | `1695 tests` | `:76` 写的是 **1712** | 数改成 1712（行号 `:76` 不用动） |
| `:298` | `1546 fast + 149 integration` | `:76` 写的是 **1563** / 149 | 数改成 1563 |
| `:299` | `1694 passed + 0 xfailed + 1 skipped` | **这行在 `:881`**，写的是 1710 / 0 / 1 | 行号改成 `:881`，数改成 1710 |
| `:300` | `Coverage 93.3% (7136 / 7650 lines)` | `:77` 写的是 **7157 / 7671** | 数改成 7157 / 7671 |
| `:301` | `Source fingerprint `sha256:18f3ab15…`` | **指纹在 `:1100`** | 行号改成 `:1100` |
| `:303` | `Two third-party integration fixtures…` | **「两个第三方集成样本」在 `:850`** | 行号改成 `:850` |
| `:304` | `suite 1710 passed / 0 failed` | 记录块 `:1102` 写的是 **`"failed": 1`** | 见 §3.1 |
| `:334` | `49 live contract checks (28 REST + 6 MCP + 15 CLI)` | **在 `:69`–`:70`** | 行号改成 `:69`–`:70` |
| `:342` | `Nine committed case-study attachment files` | **在 `:327`**（`（9 个文件）`） | 行号改成 `:327` |
| `:343` | `Five first-party sample APKs…` | 「五个一方样例 APK」在 **`:372`** 附近 | 行号改成 `:372` 附近 |

### 3.1 顺带查出来的一件事：那次测量有 **1 个失败**，两处文字都写成了 0

`v1.0.0` 树的记录块（`:1101`–`:1104`）写的是：

```
"failed": 1, "passed": 1710, "skipped": 1, "xfailed": 0
```

而 `1712 = 1710 + 1 + 1` —— **有一个测试是失败的**。可是：

* 报告自己的散文行（`:881`）写的是「1710 passed + 0 xfailed，1 skipped」，**没提那次失败**；
* release body 的附录（`:304`）写的是「suite 1710 passed / **0 failed**」——**明确写了 0**。

值比对抓到的正是这一条：`the sentence says `0 failed`, the cited line says `1 failed``。
**这一条比行号漂移更要紧**：它不是「数旧了」，是**两份对外材料都说了假话**。
工作区的记录块到现在还是 `"failed": 1`（`:1106`），说明这不是 `v1.0.0` 独有的。

**这是主会话的事**（`docs/` 不在本窗口的范围内）。本窗口只负责把它指出来。

---

## 4. 红 → 绿怎么证的

新测试在 `tests/test_doc_citations.py` 里，用一个**合成的仓库**（跟仓库里
`_repository_with_two_trees` 同一个路子）复刻本轮那三条真实错位：报告文件里
「套件结果在第 8 行、指纹在第 12 行、fixture 数在第 3 行」，而文档去引
`:6`、`:10`、`:1`。

| 测试 | 守什么 |
|---|---|
| `test_a_value_the_sentence_states_is_compared_with_the_line_it_cites` | 三条错位都被抓住，且指出值现在在哪一行 |
| `test_a_value_the_cited_line_holds_is_not_reported` | 同样三行、**指对了**，就不报（不是见什么报什么） |
| `test_a_claim_that_states_no_value_is_not_compared` | 「只说在哪」的引用不比（无法比对） |
| `test_a_number_that_is_not_a_measurement_is_not_compared` | 序号、状态码、限值、版本、引用块里的数，一律不比 |
| `test_a_citation_that_names_a_symbol_is_not_compared_with_a_value` | 句子里点了符号时，数不比 |
| `test_the_value_is_read_out_of_the_tree_the_document_declares` | 值跟着文档声明的树走（工作区动了也不报） |
| `test_the_value_findings_are_reported_and_do_not_fail_the_check` | 值的不符单列一档，且不进退出码 |

**红怎么证的**：把 `scripts/check-doc-citations.py` 换回 `HEAD` 的版本（旧的实现
根本没有值比对），跑
`uv run --no-sync pytest tests/test_doc_citations.py -k "value"`：

| 测试 | 旧实现下 |
|---|---|
| `test_a_value_the_sentence_states_is_compared_with_the_line_it_cites` | **红** —— `assert findings` 拿到空列表：旧实现一条都报不出来 |
| `test_the_value_is_read_out_of_the_tree_the_document_declares` | **红** —— 旧实现没有值这一档，工作区那份数没人比 |
| `test_the_value_findings_are_reported_and_do_not_fail_the_check` | **红** —— 旧实现的输出里没有 `values not matching:` |
| 其余四条 | **绿** —— 它们断言的是「**不该报的时候不报**」，旧实现什么都不报，自然过 |

也就是说：**三条证明新检查抓得住，两条证明它抓的是值、不是碰巧**（工作区那份数
在新实现下**会**被报出来），四条证明它不误报。

换成新实现，同一组测试 **9 passed**。

（这次复现是在一棵临时的树上做的：把 `HEAD` 的旧脚本与新的测试文件放在一起跑，
免得动工作区里的实现 —— 旧实现下 3 failed / 4 passed，与上表一致。）

---

## 5. 为什么值的不符先不参与退出码

值的不符**报出来**了，但**不**让 `check-doc-citations.py` 退出非零。理由：

* **文档里的数是一次测量的快照，测量每跑一次就写新数。** 对外文本（README、
  发版说明、release 正文）是**人工**在测量之后同步的——那是发版那一步的活。
  把值比对做成阻塞门禁，等于每次重测都先把仓库卡住，直到人工把每一份对外文本
  的数都改一遍。
* **所以这一档是「刷新清单」，不是「门禁」。** 它把两��数并排写出来
  （`the sentence says `0 failed`, the cited line says `1 failed``），
  还要尽量指出这个数**现在在哪一行**——人工照着改，改的就是那一行。
* 判据本身**没有放宽**：13 条发现一条都没有为了绿而收回去。

**主会话要把它变成阻塞门禁，只需要把 `scripts/check-doc-citations.py` 里
`Report.value_findings` 的处理改成也进退出码**（现在是 `main()` 里
`if report.drifted or report.unresolved:`）。建议的次序是：先把 §3 那 13 处
修掉（尤其 §3.1 那条「0 failed」），再把门禁打开。

---

## 6. 这一窗口做了 / 留给主会话

### 本窗口做的

* `scripts/check-doc-citations.py`：加了「句中含值」的比对（§2）、值的一档
  报告（`values not matching: N`）、跨树读值、表格行按单元格归属、
  数字词/中文数字/百分数/指纹/测量标记（`<!--fig:…-->`）的识别。
* `tests/test_doc_citations.py`：新增 7 条测试（§4）。
* `docs/reports/post-release-rehearsal.md`：4 处引用行号重锚（我让
  `scripts/check-doc-citations.py` 的行号整体下移了）。

### 留给主会话的

1. **改 release body 的附录表**（§3 的 10 行）：行号 4 处、数 5 处。
2. **§3.1 那件事**：`v1.0.0` 那次测量有 **1 个失败**，报告散文和 release body
   都写成 0 failed。要不要重发 release、要不要改报告的散文，是发版那一步的决定。
3. **合入后重测一轮**：本窗口改了 `scripts/`，**源码指纹变了**，
   `docs/reports/phase1-execution-report.md` 里的数（`tests.total`、`suite.passed`、
   覆盖率、指纹）全部过期。`scripts/refresh-report-figures.py` 要重跑，
   然后按仓库的规矩把新数同步到对外文本。
4. **本报告的登记**：`docs/reports/README.md` 的 §6 名单要加这一份
   （`docs/reports/citation-value-comparison.md`），份数 73 → 74。
   `scripts/check-doc-citations.py` 的 `DOCS` 名单**没有**加本报告
   （名单是主会话统一登记的；本报告里的 `file:line` 都在 `v1.0.0` 树上）。

---

## 7. 一句话

**门禁守的是它能守的，不是它该守的** —— 这一批把「句中含值」的那一类引用也纳进来了：
现在 release body 附录里那 13 处对不上的数与行号，机器会**逐条指出来**，
其中三处正是本轮挖出来的那三条 2 行错位，还有一条更要紧的：
**那次测量有一个失败，两份对外材料都写成了零**。
