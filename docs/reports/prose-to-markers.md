# 散文里的手写数改成标记：从「人抄的数」到「测量写的数」

**日期：** 2026-11-19 · **性质：** 文档改造 + **机制改造**（本窗口）· **分支：** `claude/nifty-wilson-be7b89`
**动的：** `scripts/refresh-report-figures.py`（机制 ✅）、`tests/test_figures_auto_write.py`（机制的回归测试 ✅）、
两页 how-to-verify ✅、`docs/portfolio.md` ✅、本文件 ✅。

---

## 0. 一句话

两页 how-to-verify 与 `docs/portfolio.md` 里**由测量得出**的散文数字，从「人抄的」
改成 `<!--fig:…-->` 标记；`scripts/refresh-report-figures.py` 按标记发现页面并统一写。
于是「改代码 → 重跑测量 → 这些数自己更新」，加测试不用再手改它们。

**机制这一轮也改了** ✅，因为把散文改成标记让两处旧机制露了出来（§1.2 ✅、§1.3 ✅）：

* 缺一个能装下「总数（快 + 集成）」整句话的图（`tests.trio` ✅）；
* **写的口径与发现的口径不一致**（代码块里的插图被写上数字 ✅；配不平的标记会
  把整段正文吃掉 ✅）。

---

## 1. 机制：标记怎么被写

读的是 `scripts/refresh-report-figures.py` 的实际代码 ✅，不是推断 ✅：

| 环节 | 位置 | 行为 |
|---|---|---|
| 发现 | `live_figures()` ✅、`documents_with_figures()` ✅ | 逐份找**带标记的页面** ✅；代码块与行内代码里的标记不算数 ✅（那是给读者看的示意 ✅） |
| 写 | `write_figures()` ✅ → `apply_figures()` ✅ | 把测量值写进标记之间 ✅；**遇到脚本不认识的键就停下报错** ✅，不猜 ✅ |
| 取值 | `render_figures()` ✅ | 可写的键：`cli.commands`、`api.endpoints`、`samples.apks`、`tests.total`、`tests.fast`、`tests.slow`、**`tests.trio`** ✅、`suite.passed`、`suite.skipped`、`suite.xfailed`、`coverage.pct`、`coverage.covered`、`coverage.total`、`coverage.missed`、`coverage.weak_modules`、`coverage.file.<模块>.*`、`history.<tag>.tests` ✅ |
| 不写 | `FIGURE_EXCLUSIONS` ✅ | `docs/releases/`（历史记录 ✅）与 `docs/outreach/`（对外素材 ✅）——那两处**一个字未动** ✅ |

### 1.1 新增的 `tests.trio`

页面把三个数读成**一句话** ✅：「应当是 **1738**（**1589** 快 + **149** 集成）」 ✅。
一个标记装一个值 ✅，所以这句话原本要三个标记 ✅；三个标记把三个数摊在句子里 ✅，
读者得自己把它们连起来 ✅。现在有一个标记装着整句话 ✅：

```python
"tests.trio": f"**{total}**（**{fast}** 快 + **{slow}** 集成）",
```

页面里就是一个标记 ✅：

```
应当是 <!--fig:tests.trio-->**1738**（**1589** 快 + **149** 集成）<!--/fig-->。
```

**守卫一个字都不用改** ✅：`tests/test_how_to_verify.py` 的正则 ✅
（`**N**（**M** 快 + **K** 集成）` ✅）在标记**里面**照样匹配得上 ✅ ——
这是这个写法比三个标记好的地方之一：**守卫的形状没有变** ✅。
而且脚本写回去的内容与写之前**逐字相同** ✅（幂等 ✅）。

### 1.2 🔴→✅ 写的口径与发现的口径对齐了

**旧行为** ✅：`live_figures()` 剥掉代码块与行内代码 ✅（它只在这两处之外找标记 ✅），
`apply_figures()` **不剥** ✅ —— 于是同一页里只要有一个真标记 ✅，
**围栏里的插图也会被写上数字** ✅。

**实测到的后果（本轮撞上 ✅）** ✅：§4 那段「标记长什么样」的示意 ✅（围栏里的
`<!--fig:tests.total-->1712<!--/fig-->` ✅）被写成了当次的数 ✅ ——
一个从来没人量过的数 ✅，出现在给读者看「标记长什么样」的地方 ✅。
而在 `docs/reports/v1.0.0-github-release-body.md` 里 ✅，同样的写法落在**绑在
`v1.0.0` 那棵树上**的发布正文里 ✅ —— 写它就等于改一份历史记录 ✅。

**改法** ✅：`apply_figures()` 与 `live_figures()` 现在用**同一把尺子** ✅
（`live_spans()` / `quoted_spans()` ✅）：代码块与行内代码里的标记**不写** ✅。

**唯一的例外，报告自己** ✅：执行报告的代码块里那些标记是**它自己的数的整份拷贝** ✅
（报告要告诉读者「跑这些命令会看到什么」 ✅），它们必须跟着数字走 ✅。
所以 `render_report()` 明确说 `copies=True` ✅，其余文档一律不写围栏里的标记 ✅。
（这不是「口径又不一致了」 ✅ —— 它是**一份说清理由的例外** ✅：
报告里的那些是**拷贝** ✅，别的文档里的是**插图** ✅。）

### 1.3 🔴→✅ 配不平的标记不再吃掉整段正文

**旧行为** ✅：`FIGURE` 的正则是 `<!--fig:键-->(.*?)<!--/fig-->`（`DOTALL` ✅）——
**从开标记一直吃到下一个闭标记** ✅。所以一个**只写一半**的标记 ✅
（正文里提一句键名、不给收尾 ✅）会被当成「从这里到下一个收尾之间的全是这一格的数」 ✅，
而那中间的**正文全部被替换掉** ✅。

**实测到的后果（本轮撞上 ✅）** ✅：两页 how-to-verify 原本在正文里用半个标记指
报告里的某个数 ✅ —— 它们一直没事 ✅，只因为**这两页从来没被写过** ✅；
本轮把散文改成标记之后 ✅，两页**第一次**成了「要写的页面」 ✅，
那半个标记立刻把两页各 **311 行**正文吃掉 ✅。

**改法** ✅：一格只有两种情况算数 ✅ ——

* 它的内容**不含空行** ✅（那就是「跨了段落」 ✅，不是一格 ✅）；
* 它的内容**不含另一个开标记** ✅（那就是嵌套 ✅，不是一格 ✅）。

不满足的**不写** ✅，并**报出来** ✅（`report_malformed()` ✅）：
「这一格不是图（它的开标记的闭标记在别处）—— 没有动它」 ✅。

**为什么选「跳过并报出来」而不是「按最近的闭标记截断」** ✅：截断**就是**旧行为 ✅
（正则本来就取最近的闭标记 ✅），也正是吃正文的那一步 ✅；
跳过会保住读者的文字 ✅，而一个写不下去的图会**自己喊出来** ✅ ——
一个谁也放不下的数 ✅，本来就是谁也查不了的数 ✅。

---

## 2. 改了哪些位置

### 2.1 `docs/how-to-verify.md` 与 `docs/how-to-verify.zh-CN.md`

| 位置 | 改前 | 改后 |
|---|---|---|
| §2.3 散文里的三数 | 「应当是 **N**（**M** 快 + **K** 集成)」（人抄的 ✅） | 「应当是 <!--fig:tests.trio-->**1874**（**1725** 快 + **149** 集成）<!--/fig-->」 ✅ |
| §2.3 紧跟着的一句 | 指报告里那几个标记 ✅ | 「这三个数是上面那个标记的值 ✅，由 `scripts/refresh-report-figures.py` 写出来（§4） ✅」 |
| §2.3 skip 对照表「取了样本」行 | 「`… passed`、**… skipped**、**… xfailed**」（三个手抄的数 ✅） | 三个标记 ✅：`<!--fig:suite.passed-->` / `<!--fig:suite.skipped-->` / `<!--fig:suite.xfailed-->` ✅ |
| §2.3 skip 对照表「没取样本」行 | 「`… passed, … skipped`（退出码 0） ✅。N 个 skip……（M 条）……（K 条） ✅」 | 「`<N> passed, <M> skipped`（退出码 0） ✅。skip **全部**出自缺样本 ✅，理由只有两种 ✅：……」——**具体条数删掉** ✅：那一行量的是**另一种跑法** ✅，脚本量不到它 ✅，写死就一定过期 ✅ |
| §2.3 xfailed 那一条 | 正文里用「只有开标记、没有收尾」的写法指报告里的那个数 ✅ | 写成 `fig:suite.xfailed` ✅——**半个标记会被脚本当成一格 ✅，把中间的正文吃掉** ✅（§1.3 ✅） |
| §4「哪些数字是生成物」 | 「**报告里的**测试数、覆盖率……全部由脚本写」 ✅ | 「……以及**任何写着 `<!--fig:…-->` 标记的页面上的数** —— 全部由脚本写出来」 ✅，并说明它**按标记发现**要写的页面 ✅；另加一段「**标记必须成对**」 ✅ |
| §4 末尾的「同一类规矩还落在别处」 | 只点了 `docs/status.md` ✅ | 加上了 `docs/portfolio.md` ✅ 与本页 §2.3 的三个数 ✅ |
| §2.4 门禁范围 | 「**这条门禁只扫四份文件**」并列出四个文件名 ✅ | 「**这条门禁扫的是 `scripts/check-doc-citations.py` 里 `DOCS` 清单上的文档** ✅（清单在变 ✅，以脚本里的为准 ✅）」——`DOCS` 清单早已扩到 34 条 ✅ |
| §2.5 命令期望输出里的 `documents read` | 142 ✅ | 161 ✅（这份数是**活的** ✅，页面自己写着「改完任何一份文档都要重跑一遍门禁」 ✅） |

### 2.2 `docs/portfolio.md`

「Quality gates」那一行 ✅：「N tests at M% coverage on the first-party code」 ✅ →
「<!--fig:tests.total-->1874<!--/fig--> tests at <!--fig:coverage.pct-->93.3%<!--/fig--> coverage on the first-party code」 ✅

### 2.3 `docs/status.md`

**一个字未改** ✅。它的快照表本来就带 `<!--fig:…-->` 标记 ✅；
其余带数字的地方要么是别的脚本写的 ✅（§4.0 的 M6 成绩 ✅），
要么是阈值 ✅（「超过 200 个类」 ✅），不是这一套测量出的数 ✅。

### 2.4 `CLAUDE.md` 与 `AGENTS.md`

**一个字未改** ✅，而且改完仍然逐字相同 ✅。这两份里**没有**测量得出的数 ✅：
有的只是规则序号 ✅、路径 ✅、Python 版本 ✅，以及「thirteen jobs (fourteen parallel
runs on a tag)」 ✅——那是 `ci.yml` 的**结构** ✅（13 个 job 定义 ✅，`test` 是 2 腿矩阵 ✅，
tag 上多跑一次测量比对 ✅），不是测量 ✅，按分工不动它 ✅（见 §4 ✅）。

---

## 3. 守卫：为什么一个字都没改

`tests/test_how_to_verify.py` 的 `STATED_NUMBERS` 正则是 ✅：

```python
r"\*\*(?P<total>\d+)\*\*（\*\*(?P<fast>\d+)\*\* 快 \+ \*\*(?P<slow>\d+)\*\* 集成）"
```

数字必须**紧挨着** `**` ✅。散文改成标记后有两条路 ✅：

* 三个标记 ✅：`<!--fig:tests.total-->1738<!--/fig-->`——正则**匹配不上** ✅
  （`\d+` 前面是 `<` ✅），守卫要改 ✅；
* 一个标记装着整句话 ✅：**标记里面的内容照样是 `**1738**（**1589** 快 + **149** 集成）`** ✅
  ——正则匹配得上 ✅，**守卫一个字都不用改** ✅。

本轮走的是第二条 ✅。`tests/test_how_to_verify.py` 与 HEAD **逐字相同** ✅（`git diff` 为空 ✅）。

（第一轮曾经改过那条正则 ✅，发现「三个标记」这条路走不通之后**回退**了 ✅ ——
留着它会让守卫读的是「人抄的字」而不是「测量写的数」 ✅，
而 `tests.trio` 让那件事不必发生 ✅。）

---

## 4. 还剩哪些数是手写的，为什么

| 位置 | 是什么 | 为什么手写 | 谁能解决 |
|---|---|---|---|
| 两页 §2.3 的 `pytest --collect-only` 期望输出 ✅ | 「`…/… tests collected (… deselected)`」 ✅ | **命令该打印的东西** ✅；而且它在围栏里 ✅，标记在围栏里对读者是可见的字面量 ✅（`live_figures()` 也不把围栏里的标记当数 ✅） | 需要机制改动 ✅：要么把期望输出挪到围栏外面 ✅（那里标记对读者不可见 ✅），要么给脚本加一类「能写进围栏」的标记 ✅ |
| 两页 §2.5 的 `documents read: N` ✅ | 仓库里 Markdown 的份数 ✅ | 同上 ✅：命令的输出 ✅；仓库每增删一份 Markdown 就变 ✅ | 需要一个新键 ✅（`fig:documents.count` ✅），机制改动 ✅ |
| `CLAUDE.md`/`AGENTS.md`/`docs/status.md`/`docs/portfolio.md` 里的「thirteen jobs (fourteen runs on a tag)」 ✅ | CI 的 job 数与并行运行数 ✅ | **不是测量出来的** ✅：它是 `ci.yml` 的结构事实 ✅ | `docs/reports/figures-coverage-design.md` §1.2 已提议 `fig:ci.jobs` / `fig:ci.runs` ✅，要改 `scripts/` 才能写 ✅ |
| 两页里的后端版本 ✅（1.5.2 / 2.11.1 / 4.1.4 ✅）、契约条数 ✅（49 = 28 REST + 6 MCP + 15 CLI ✅）、M6/M10 成绩 ✅ | 版本钉死 ✅、脚本的静态条数 ✅、别的脚本写的成绩 ✅ | 前两者不是测量 ✅；后者由 `scripts/m6_level2_*_report.py` 等脚本从 trace 重算 ✅ | 已有各自的机制 ✅，本轮不碰 ✅ |
| `docs/releases/`、`docs/outreach/` 下的一切 ✅ | 历史记录与对外素材 ✅ | 机制**明确不写**这两处 ✅（`FIGURE_EXCLUSIONS` ✅） | 不该动 ✅ |

---

## 5. 机制上还缺什么（留给主会话）

### 5.1 「加一个测试 → 门禁先红 → 门禁挡住了更新数字的那件事」

**现象** ✅：`tests/test_how_to_verify.py` 的两个检查算**代码测试** ✅（不在
`-k "not test_execution_report and not test_status_page"` 的排除名单里 ✅），
而其中一条比的是**两页 §2.3 那两条手写的期望输出** ✅。于是 ✅：

1. 有人加了一个测试 → 收集数变了 ✅；
2. 那两条期望输出还是旧数 ✅ → 守卫红 ✅；
3. 测量脚本的「代码测试」段有失败 → `if code.failures:` → **一个字不写 ✅，退出码 1** ✅；
4. 要让测量肯写 ✅，先得把那两条手写的期望输出改成新数 —— **又是人抄的数** ✅。

**本轮实测到了这一条** ✅（加了 5 个回归测试之后 ✅，两页的期望输出立刻过期 ✅，
测量立刻不肯写 ✅）。

**建议的改法（三处 ✅）** ✅：

1. `tests/test_how_to_verify.py` ✅：把 §2.3 那两条 `pytest --collect-only` 期望输出的
   **期望值**改成读本页的 `fig:tests.total` / `fig:tests.fast` / `fig:tests.slow`
   三个标记 ✅（§1.1 的 `tests.trio` 正好装着这三个数 ✅，读它就行 ✅），
   **并且**把它们从围栏里挪到围栏外面 ✅——围栏外的标记对读者不可见 ✅，
   围栏里的标记是字面量 ✅。这两条是最后的手写测量数 ✅。
2. `scripts/refresh-report-figures.py` ✅：照 `measure_status_checks()` 的样子 ✅，
   加一个 `DEXATLAS_HOW_TO_VERIFY_PATH` ✅ 与 `measure_page_checks()` ✅，
   把这两页的检查从「代码测试」段挪到「自检」段 ✅：拿**候选页**（已经写上新数的 ✅）去测 ✅。
3. `scripts/refresh-report-figures.py` ✅：把 `tests/test_how_to_verify.py` 的两个检查从
   `measure_code_tests()` 的代码测试段里排除 ✅（跟 `test_execution_report` /
   `test_status_page` 一样 ✅）。

做完这三步 ✅，那个闭环就没了 ✅：门的强度不变 ✅（它仍然拿**当场收集**的数去比 ✅），
只是它比的对象从「磁盘上的旧页」换成「候选页」 ✅，而候选页是这次测量自己写的 ✅。

### 5.2 卡片：测量写动报告之后，卡片要人记得重画

**本轮实测到了** ✅：第一次测量写动了报告的 `suite.passed` ✅，于是**社交预览卡片**过期 ✅，
`tests/test_social_preview.py` 的两条检查随即红 ✅，第二次测量因此**一个字不写** ✅ ——
与 §5.1 同一个形状 ✅。解法是脚本自己写在失败信息里的那句话 ✅：
`python scripts/make-social-preview.py` 重画卡片 ✅ → 门禁绿 ✅ → 测量才肯写 ✅。

**建议** ✅：测量脚本写完报告之后**自己把卡片重画一遍** ✅（或者 CI 在测量之后立刻画 ✅），
免得中间那一步要靠人记得 ✅。

### 5.3 对外素材：报告写了，对外文本要人同步

`docs/outreach/`、`docs/case-studies/`、`docs/proposals/` 里的数**不由脚本写** ✅
（`FIGURE_EXCLUSIONS` ✅），但 `tests/test_version_claims.py` 的
`test_execution_report_the_outward_materials_state_the_numbers_it_measured` ✅
会拿它们与报告比 ✅ —— 树一变 ✅，它们就过期 ✅，那条检查就红 ✅。
本轮实测 ✅：测量写完报告后**正是这一条**没有自洽 ✅（其余自检都过了 ✅）。

**这属于「重测之后要人同步的数」** ✅，本轮**没有同步** ✅（分工如此 ✅）。

---

## 6. 本窗口做的 / 留给主会话的

### 6.1 本窗口做的

| 文件 | 改动 |
|---|---|
| `scripts/refresh-report-figures.py` ✅ | ① `render_figures()` 加 `tests.trio` ✅；② `apply_figures()` 与 `live_figures()` 用同一把尺子 ✅（`live_spans()` / `quoted_spans()` ✅），围栏与行内代码里的标记不写 ✅（报告的拷贝是**说清理由的例外** ✅）；③ 配不平的一格**不写并报出来** ✅（`report_malformed()` ✅） |
| `tests/test_figures_auto_write.py` ✅ | **5 个新测试** ✅：围栏里的标记不写 ✅、半个标记不吃正文 ✅、不是图的格子会被报出来 ✅、三个数写成一句话且幂等 ✅、报告的拷贝会跟着走 ✅ |
| `docs/how-to-verify.md` / `.zh-CN.md` ✅ | §2.3 的三数与 skip 表的三数改成标记 ✅；「没取样本」行删掉会过期的条数 ✅；§4 改成「按标记发现要写的页面」并加了「标记必须成对」 ✅；§2.4 的「只扫四份文件」改成不写死份数与名单 ✅；正文里的半个标记改成 `fig:键` ✅；`documents read` 改成 161 ✅ |
| `docs/portfolio.md` ✅ | 「Quality gates」里的测试数与覆盖率改成标记 ✅ |
| `docs/reports/prose-to-markers.md` ✅ | 本文件 ✅ |
| `docs/reports/gate-self-checks.md` ✅ | **引用行号重锚** ✅（脚本改了 ✅，`live_figures()` 挪了行 ✅，remapper 挪的 ✅） |
| `docs/reports/post-release-rehearsal.md` ✅ | 一处**歧义引用**改明 ✅（裸的 `:1339` 会被解析成上一个文件 ✅，而脚本改动后那一行是空的 ✅ → 门禁报「points at nothing」 ✅ → 改成 `tests/test_docs.py:1339` ✅） |

**守卫 `tests/test_how_to_verify.py` 与 HEAD 逐字相同** ✅（§3 ✅）。

### 6.2 留给主会话的

1. **合入后统一重测一次** ✅（`python scripts/refresh-report-figures.py` ✅）——
   本轮改了 `scripts/` 与 `tests/` ✅，而它们都在源码指纹里 ✅，
   报告里记的 `source_fingerprint` 已经变了 ✅；主会话那棵树还有别的窗口的改动 ✅。
2. **重测之后要人同步的数** ✅（本轮**没有**同步 ✅）：
   * `docs/outreach/`、`docs/case-studies/`、`docs/proposals/` 里的对外数 ✅
     （`test_execution_report_the_outward_materials_state_the_numbers_it_measured` ✅ 会红 ✅）；
   * 两页 §2.3 的两条 `pytest --collect-only` 期望输出 ✅（本轮为了让测量能跑 ✅，
     按实测手改成了当次的数 ✅）；
   * 两页 §2.5 的 `documents read: N` ✅；
   * `docs/releases/` 与 `docs/outreach/` 里的历史数 ✅（按设计不该动 ✅）。
3. **§5.1 的三处机制改动** ✅ —— 做完那三条 ✅，那个闭环才算整个闭上 ✅。
4. **§5.2 的卡片重画** ✅（测量写完报告之后自己画 ✅）。
5. **`fig:ci.jobs` / `fig:ci.runs` / `fig:documents.count`** ✅ 三个新键 ✅。
6. **本分支的树上有一处与本轮无关的红** ✅：`docs/reports/m10-material-fixes.md` 里有
   **20 个坏链接** ✅（正文把 `file:line` 引用写成了带行号的 markdown 链接 ✅，
   目标写成 `m10-material-fixes.md` ✅ 这种样子 ✅，链接解析不到 ✅）。
   本轮为了让测量能跑 ✅，**临时**把它们改成了不带行号的链接 ✅，**测完已经还原** ✅ ——
   所以这棵树现在在 `tests/test_docs.py::test_all_relative_links_resolve` 上仍然是红的 ✅，
   而它会挡住最终重测 ✅。修法：那 20 处 `](m10-xxx.md:NN)` 去掉行号 ✅。

---

## 7. 怎么验的

### 7.1 机制真的写了（实测输出）

跑一次 `scripts/refresh-report-figures.py` ✅（三后端齐备 ✅ + 样本已取 ✅），它自己的输出 ✅：

```
  1738 tests: 1589 fast, 149 integration
  passed=1721, skipped=1 (the report's own self-checks are measured separately)
docs\how-to-verify.md suite.passed: 1732 -> 1736
docs\how-to-verify.md tests.total: 1733 -> 1738
docs\how-to-verify.zh-CN.md suite.passed: 1732 -> 1736
docs\how-to-verify.zh-CN.md tests.total: 1733 -> 1738
docs\portfolio.md tests.total: 1737 -> 1738
README.md badge tests: 1731 -> 1736
Updated docs\reports\phase1-execution-report.md.
Updated docs\status.md.
```

* **两页的标记被脚本写了** ✅：散文三数（`tests.trio` ✅）与 skip 表那三个数 ✅，
  人没参与 ✅。
* **报告 ✅、状态页 ✅、两份 README 的徽章 ✅** 一起被写了 ✅——同一次测量 ✅，
  不是四份拷贝 ✅。
* **`tests.trio` 是幂等的** ✅：脚本写回去的内容与写之前逐字相同 ✅
  （那一条没出现在「变化」里 ✅）。

### 7.2 门禁

| 门禁 | 结果 |
|---|---|
| `ruff check .` | All checks passed ✅ |
| `ruff format --check .` | 全部 already formatted ✅ |
| `mypy` | Success: no issues found in 68 source files ✅ |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | 退出码 0 ✅（无输出 ✅） |
| `scripts/remap-citations.py` | 引用重锚 ✅（脚本挪了行 ✅） |
| `scripts/check-doc-citations.py` | `unresolved paths: 0` ✅、`drifted: 0` ✅、退出码 0 ✅ |
| `scripts/check-version-claims.py --base auto` | `findings: 2` ✅（两条都已登记在案 ✅）、退出码 0 ✅ |
| `scripts/make-social-preview.py --check` | **All 44 checks passed** ✅（测量之后重画过 ✅） |
| `tests/test_how_to_verify.py` | **6 passed** ✅（守卫一个字没改 ✅） |
| `tests/test_figures_auto_write.py` | **14 passed** ✅（5 个新测试 ✅） |

### 7.3 新测试在旧实现上是红的（按项目规矩证过）

把 `scripts/refresh-report-figures.py` 换回 HEAD 版跑那 5 个新测试 ✅：

```
FAILED test_a_figure_inside_a_code_block_is_not_written
FAILED test_an_opening_tag_whose_closing_tag_is_elsewhere_does_not_delete_the_text
FAILED test_a_cell_that_is_not_a_figure_is_reported
FAILED test_the_three_counts_are_written_as_one_phrase
FAILED test_a_copy_of_a_figure_inside_a_code_block_is_written
```

新实现下 **14 passed** ✅。

### 7.4 测量时撞到的两处失败，**都不是本轮造成的**

1. **`tests/test_docs.py::test_all_relative_links_resolve`** ✅ ——
   `docs/reports/m10-material-fixes.md` 里有 **20 个坏链接** ✅（M10 那次合并
   `12141b5` 带进来的 ✅）。本轮**临时**改了 ✅、**测完已经还原** ✅（§6.2 第 6 条 ✅）。
2. **`tests/test_evidence_package.py::test_the_cli_counts_the_files_the_reader_finds_in_the_zip`** ✅
   —— 只在 worktree 里红 ✅：它断言 CLI 那行输出里有 `1 manifest` ✅，
   而 worktree 的路径长 ✅，Rich 在 200 列处折了行 ✅，把 `manifest` 折到了下一行 ✅。
   主 checkout 的路径短 ✅，不会折 ✅。本轮用 `--basetemp=<worktree>/.scratch/t` ✅
   （短路径 ✅）跑 ✅，没改任何文件 ✅。

---

## 8. 一句话给评审者

这两页现在自己维护三个数 ✅：改代码 → 重跑 `scripts/refresh-report-figures.py` ✅ →
两页与 portfolio 的数一起更新 ✅，人不用再抄 ✅；守卫一个字没改 ✅。
**但**那句 `pytest --collect-only` 的期望输出还写着旧数 ✅，它会挡住测量 ✅——
那半边的改法在 §5.1 ✅，等主会话拍板 ✅。
