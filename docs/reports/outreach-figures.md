# 外发材料里的数：接进「数字是生成的」（outreach-figures）

**状态：机制已接上并跑通；四份材料里的测试数与覆盖率不再手抄。**

- **日期**：2026-11-28
- **对象**：`docs/outreach/` 下的四份材料——`cover-letter-templates.md`、
  `project-brief.md`、`scope-backend-automation.md`（外发）与 `publish-review.md`
  （内部核对记录）。它们在正文里手抄了测试总数与一方覆盖率。
- **基线**：`docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` 标记——它
  是这批数的权威来源，由 `scripts/refresh-report-figures.py` 从一次完整测量写出。
- **本轮的动作**：**新增** `scripts/export-outreach.py`、`tests/test_outreach_figures.py`、
  本文件；**改动** `scripts/refresh-report-figures.py`（把 `docs/outreach/` 从写入
  排除名单里去掉、加 `grouped()` 这个写法、新增四个 `*.grouped` 标记键）、
  `scripts/check-version-claims.py`（加一道「标记里的数与报告对得上」的检查）、
  `scripts/check-gate-coverage.py`、`scripts/platform-gates.json`、
  `.github/workflows/ci.yml`、四份材料本身、`docs/reports/README.md`。
  **没有**改 `src/`、`desktop/`、`pyproject.toml`。**没有**提交、没有推送。

---

## 0. 结论速览

| | |
|---|---|
| 病 | 四份材料手抄测试数与覆盖率；每重测一次就要人改 4 个文件 6 处。2026-11-27 → 11-28 发生过三次（1887 → 1915 → 1931） |
| 选的路 | **A**（让测量脚本写它们）＋ **C 的精神**（导出这一步），**B 不用** |
| 标记语法 | 沿用项目已有的 `<!--fig:…-->`，**不引入第二套占位符** |
| 新脚本 | `scripts/export-outreach.py`：把标记渲染成发出去的纯文本 |
| 门禁 | `check-version-claims.py` 新增 `check_outward_figures`：**标记里的值**与报告比对 |
| CI | 新增一步 `export-outreach.py --check`（在 `release-numbers` job 里） |
| 代价（明说） | 仓库里现在存的是**带标记的源**，不是可直接粘贴的成品；由导出化解，导出件不进版本库 |
| 顺带修掉 | 门禁读不出百分比（`plain_number("93.4%")` 返回 `None`）：两个读不出数的百分比会被当成相等 |

---

## 1. 病：不是「四份文件」，是「一个纪律的例外」

这个项目第一条纪律是「数字是生成的，不是写的」。报告里的数由
`scripts/refresh-report-figures.py` 写入，README 徽章由同一个脚本写入，
社交预览卡上的数由另一个脚本从报告读出。**只有外发材料里的数是手抄的**，
而外发材料恰恰是**发出去就改不了**的那一份。

手抄在 2026-11-27 到 11-28 之间发生过三次：1887 → 1915 → 1931。每一次都是人
记得去改 4 个文件 6 处——**而人记得的那一次，和别人记得的那一次，不是同一个人**。

### 1.1 现有的门禁为什么没逮住

先量过，不是推断：

- `scripts/check-version-claims.py` 对外发材料用 `BADGE_TOLERANCE = 0.5`
  （该脚本里的常量），把 93.3% 与 93.4% 判为一致。**覆盖率的分毫之差现在就在门禁眼皮
  底下过去。**
- `publish-review.md` 里覆盖率的分子分母（当时写的是 7,485 / 8,018）**根本不在
  门禁的正则口径内**，任何漂移都不会被报出来。
- 测试总数能被发现，**只是因为它恰好还对**。等它变成 1,950，门禁会报
  `outward-tests`——但它报的是「总数不对」，而材料描述的是**当下**的项目，
  一个发出去的文案里的数本来就属于上一次测量。

⇒ **门禁现在逮住漂移是偶然的，不是结构的。**

### 1.2 也不能靠「把数全做成标记」就完事

`check_stated_numbers` 在检查前会把标记抹掉：

```python
spoken_lines = [FIGURE.sub(lambda match: " " * len(match.group(0)), line) for line in lines]
```

这是对的——标记里的数不是文本的断言，是**测量的断言**。但后果是：**如果材料
里所有的数都在标记内，这道门禁对外发材料就无事可做了。** 那正是任务警告的
「退步」。实测：把材料里的标记值改成 9,999 / 95.0%，`check-version-claims.py`
报 **0 findings**。

⇒ 所以本轮的机制必须**同时**做到两件事：材料里的数由测量写入；门禁仍然盯着
材料里的数。**门禁的工作方式换了，但没有变少——反而变强了**（标记是精确比较，
手写数有 0.5 容差）。

---

## 2. 三条路的取舍

任务给出 A / B / C 三条路。逐条评估，**并说明为什么这么选**。

### 2.1 B（从别处派生：指向 `docs/status.md`）——不用

**代价是致命的**：材料是**直接粘进表单**的成品。「见 docs/status.md」对一个
Upwork 读者没有意义——他不会 clone 仓库。而材料存在的全部理由就是被读。

唯一能活下来的 B 形态是「正文不写数，改写成一句不含数的说法」（「覆盖率高、
门禁齐全」）。这会损失材料的具体性，而具体性正是它作为作品集样例的价值。

**不用。**

### 2.2 A（让测量脚本写它们）——用

好处很直接：数与报告里的数是**同一份测量**，不是两次计算；报告刷新时材料一起
刷新，「重复劳动」从「人记得改 4 个文件 6 处」变成零。

难点是任务点出的那个：**这些文件会被发出去**，而 HTML 注释粘进表单是可见的乱码。
两条子路：

1. **导出时剥掉标记**——加一步导出。
2. **换一种不显眼的占位符**（比如 `{{tests.total}}`）——但这与项目既有的
   `{{...}}` 语义**冲突**：材料里已有的 `{{one sentence tying it to the job}}`
   是「发送前必须替换」的占位符，而 `{{tests.total}}` 是「永不替换、由脚本写入」
   的。两种语义同形会让使用说明自相矛盾，而**使用说明本身也要被发出去**。

⇒ **用 A，且沿用项目已有的 `<!--fig:…-->` 语法。** 这是本决定最重要的一点：
**不引入第二套占位符语法**，写入器（`refresh-report-figures.py`）、读取器
（`check-version-claims.py`、`check-release-numbers.py`）全部复用，不新增机制。

### 2.3 C（加一道生成步骤）——用它的精神，不用它的形式

C 的模板 + 生成有两处代价：

- 仓库里多一份「生成物」，发布流程变成「改模板 → 重新生成 → 提交生成物」，
  比 A 多一步；
- 更要紧的是：素材是要**人工编辑**的成品（替换 `{{...}}`、删去不适用小节、
  逐句润色）。**模板化和「人工编辑成品」这件事打架。**

⇒ **不用模板文件。** 但 C 的一个洞察值得留下：**仓库里存的应该是「源」，发出的
应该是「渲染」。** 导出这一步就是那个渲染。

### 2.4 决定：A ＋ 一道导出

关键洞察：**「材料」与「发出去的东西」本来就不是同一个东西。** 现在的四份文件
里，`publish-review.md` 自己就声明了「本文件只留在仓库里：不对外、不作附件、
不随提案发送」，而另外三份是要发出去的。**仓库里已经有「内部件」与「外发件」
的区分了**，只是外发件现在同时承担了「可编辑的源」和「要粘出去的成品」两个角色。

于是：

1. **四份材料改为带标记的源**（A），标记用 `<!--fig:…-->`；
2. **新增 `scripts/export-outreach.py`**，把外发件里的标记渲染成纯文本（剥掉标记，
   留下数），写到 `.scratch/outreach-export/` 下。**发出去的是导出的文件**，
   不是仓库里的源；
3. **`publish-review.md` 是内部件，不导出**——它本来就只留在仓库里。但它的数
   **同样改为标记**，因为它也在讲当下的项目，它的数同样会过期。

---

## 3. 机制是怎么搭的

### 3.1 测量脚本写材料

`scripts/refresh-report-figures.py` 原来把 `docs/outreach` 列在
`FIGURE_EXCLUSIONS` 里，理由是「外发材料的数由 `check-version-claims.py` 核对，
不由本脚本填」。现在这个排除去掉了，理由改写成：**排除没有解决标记可见的问题，
只是让那些数变成手抄的**，而手抄的数是这个项目最容易烂掉的东西。

新增一个写法：

```python
def grouped(number: int | str) -> str:
    """A count as a person writes it: ``1,938``."""
```

报告在表格单元格里写 `1938`（窄），材料是散文，人在句子里写 `1,938`。两个写法
是同一个数，但散文那个是**第二种要保持对的格式**——所以它也是生成的：
`tests.total.grouped` / `tests.fast.grouped` / `tests.slow.grouped` /
`coverage.covered.grouped` / `coverage.total.grouped`。

### 3.2 导出脚本

`scripts/export-outreach.py` 干三件事：

- 把标记渲染成值（值从**报告**里读，报告是权威）；
- `--check` 模式：**导出件里不得残留 `<!--fig:`**，且每个标记都必须是一个
  报告承载的图；
- 把渲染结果写到 `.scratch/outreach-export/`（已 gitignore）。

导出的结果**不进版本库**：它的内容由当前测量决定，而测量每次都不同；把它存进
仓库就是**再存一份数的副本**，正是本机制要结束的那件事。

规则只有一份：分组写法问**测量脚本**（`refresh-report-figures.py` 的
`grouped()`），不重写一遍。两份同一条规则就是同一个问题的两个答案，而第二个
答案是会烂掉的那个。

### 3.3 门禁：标记里的数仍然有人看

`scripts/check-version-claims.py` 新增 `check_outward_figures`：

- 外发材料里的每个标记，值必须与报告里对应图的值**相等**（精确，无容差）；
- 报告里没有的图键 → `outward-figure-unknown`：**门禁比不出答案的数，是没人
  能信的数**；
- 报告本身没有承载的图 → 不检查（那里什么都没断言）。

**顺带修掉一个真盲点**：`plain_number("93.4%")` 返回 `None`，所以两个百分比
会**都读成「没有数」并被判为相等**。新增 `figure_number()` 读小数，两个百分
比于是能被正确比较。实测：把材料里的标记改成 9,999 / 95.0%，门禁从 **0
findings** 变成 **2 findings**（`outward-figure` ×2）。

门禁对材料里**没被标记**的数仍然照查（`check_stated_numbers` 与
`check_outward_counts` 原样保留）——「标记内的数由测量保证，标记外的数由门禁
保证」这条分工是写进代码注释的。

### 3.4 门禁的平台清单与 CI

- `scripts/check-gate-coverage.py`：`export-outreach.py` 登记进 `GATES`
  （CI 跑一个脚本，它就是门禁；未登记会被这道检查报出来）。
- `scripts/platform-gates.json`：`release-numbers` job 的 `gate_scripts` 与
  `local_counterpart` 同步（**加一个正确的 CI step 不需要改任何数字**，
  但清单必须说清差异是否合法）。
- `.github/workflows/ci.yml`：在 `release-numbers` job 里加一步
  `uv run --no-sync python scripts/export-outreach.py --check`。

**CI 会跑导出这一步**，所以「源里的标记与当前测量一致」这件事由 CI 保证，
而不是由人记得跑导出保证。人只在**真的要发出去**的时候才跑导出，而那一步本来
就要人参与（替换 `{{...}}`、逐句检查）。

---

## 4. 代价（明说）

**仓库里现在存的是「带标记的源」，不是「可直接粘贴的成品」。**

这是本决定唯一真正的代价。任何打开 `docs/outreach/cover-letter-templates.md`
的人看到的是一圈 HTML 注释里的数字（`fig:` 标记），不是光秃秃的一个数。

化解它的东西是导出脚本，但它有两个诚实的限制：

1. **导出是另一个文件，不是另一个按钮。** 人要记得在发出去之前跑一次导出。
   CI 跑的是 `--check`（源与导出一致），不是「替人导出」——导出件不进版本库，
   所以它每次都要重新生成。
2. **字符数要按导出件算，不是按源算。** 标记让源多出几十个字符，而
   `publish-review.md` §5 的字符预算**贴线**（Template 2 是 plain 2,485 / 上限
   2,500，余 0；`scope-backend-automation.md` 全文 plain 4,941 / 上限 5,000）。
   §5 的表因此改为**按导出件复算**——见下一节。

另一处代价：**外发材料从此不能直接粘贴**。这在「仓库里存的是可粘贴成品」这个
旧习惯下是反直觉的。但那个习惯正是手抄数字的来源。

### 4.1 一处实测抓到的回归：说明段不能放进外发件

本轮第一版在三份外发材料的头部各加了一段「这是源，发出去前先导出」的使用说明。
**那是个回归**，而且只有实测能抓到：

| | 加说明前 | 加说明后 |
|---|---:|---:|
| `scope-backend-automation.md` 全文 plain | 4,941 | **5,381**（超 5,000 门限 **381**） |

那份材料的 5,000 字符门限**只剩 59 字符余量**，一段说明就把它顶过去了。

更根本的是：**那段说明本来就不该在文件里。** 外发件是要发给客户的，
「先跑 `uv run --no-sync python scripts/export-outreach.py`」这种仓库内的操作
说明不该出现在客户面前。

⇒ 说明全部集中在 `docs/outreach/README.md`（那一页本身是内部页，不外发），
**外发件里一句都不加**。这也意味着：**给外发件加任何东西之前，先量一下**——
门限贴线的材料经不起任何追加。

---

## 5. `publish-review.md` §5 的字符数表

字符数是**平台门限**，不是测量数字：它由「这段文案有多长」决定，与测量的数无关。
但 §5 的表**列了**材料里的数（那几行的计数），所以它跟着材料一起变。

改动前的口径：**按仓库里的源算**。改动后：**按导出的件算**——因为发出去的是
导出件，量它的长度才是量的真东西。`publish-review.md` §5 的脚本因此改为先
导出、再量。

§7 第 2 条与第 5 条（「发送前仍须重算」）**继续有效**，而且现在多了一条：算出
来的数是导出件的数，不是源的数。

---

## 6. 「去掉它就会红」

每条机制改动都有测试，见 `tests/test_outreach_figures.py`（26 个）。逐条对应：

| 机制 | 测试 | 去掉它会怎样 |
|---|---|---|
| 材料带标记 | `test_the_materials_carry_generated_figures` | 材料回到手抄数 → 测试红 |
| 材料里没有手写测试数 | `test_a_material_states_no_hand_written_test_count` | 手抄数回来 → 测试红 |
| 材料的键都是测量写得出的 | `test_the_materials_carry_only_keys_the_measurement_writes` | 出现测量写不出的键 → 测试红 |
| 导出件无标记残留 | `test_the_exported_text_carries_no_marker` | 导出不再剥标记 → 测试红 |
| 导出件带着测量数 | `test_the_exported_text_states_the_measured_number` | 导出取错数 → 测试红 |
| 内部件不导出 | `test_the_internal_record_is_not_exported` | 内部记录被导出 → 测试红 |
| 导出不进版本库 | `test_the_export_is_written_outside_the_repository` | 导出件进了仓库 → 测试红 |
| 门禁看得见漂移 | `test_the_gate_reports_a_figure_that_drifted_from_the_report` | `check_outward_figures` 被删 → 测试红（AttributeError） |
| 门禁不误报 | `test_the_gate_does_not_report_a_figure_that_agrees_with_the_report` | 门禁变成永远红 → 测试红 |
| 门禁报告比不出的图 | `test_the_gate_reports_a_figure_it_cannot_compare` | 未知图键被放过 → 测试红 |
| 百分比按百分比比 | `test_a_percentage_is_compared_as_a_percentage` | `figure_number` 没了 → 测试红 |
| 门禁没丢掉旧检查 | `test_the_gate_still_checks_the_numbers_written_by_hand` | `check_outward_counts` 被删 → 测试红 |
| 测量脚本写材料 | `test_the_measurement_writes_the_outward_materials` | `docs/outreach` 回到排除名单 → 测试红 |
| 分组写法是生成的 | `test_the_measurement_writes_the_grouped_spelling_of_a_count` | `grouped()` 没了 → 测试红 |
| 材料里不写字面标记示例 | `test_no_material_writes_a_literal_marker_as_an_example` | 材料里出现测量写不出的键 → 测试红 |
| 导出件仍塞得进字段 | `test_the_exported_material_still_fits_the_platform_limits` | 材料长到超过字段门限 → 测试红 |
| 导出件整篇仍塞得进附件 | `test_the_exported_material_still_fits_as_an_attachment` | 头部加了一段说明 → 测试红（§4.1 那个回归） |

---

## 7. 没有做的事，和为什么

- **没有**把 `scope-ai-mcp.md` / `scope-ai-mcp-compact.md` 改成带标记：它们**不
  写测试数与覆盖率**，没有要治的病。
- **没有**把 `c12-field-check-template.md` 改成带标记：它是渠道字段核对表，写的
  是字符数与门限，不是测量数。
- **没有**改 `src/`、`desktop/`、`pyproject.toml`。
- **没有**提交、没有推送：改动留在工作树里，由主会话取。
- **新增**了 `docs/outreach/README.md`：那一页说清哪一份发出去、哪一份不发、
  发之前跑哪一步。它是给自己看的（内部页），不是附件。

## 7.1 一处已知缺口，本轮没有治

`publish-review.md` §1 的**历史对照表**（那一轮的 1,612 / 93.3%）仍然写着旧数。
本轮的处理是**把它标成「历史轮次的记录」**，并写明「变的是 §0 的那张表」。

它没有被改成标记，理由是：**一张要跟着测量走的表就不再是历史了。** 要治它得
另设机制（把「历史值」也做成标记，并让门禁知道哪些标记是历史的），那是另一个
闭环。本轮只把**当下**的那些数接进了机制。

另有一处**同类**的转述被删掉了：`publish-review.md` §7 末尾原来写着「当前
落盘的是……（1,938 tests / 93.4%，7,485/8,018 行）」——那是「当前值」的转述，
而转述出来的数会过期。现在它指向报告，不转述数字。**一个数只写一次。**

## 8. 一件仍然要人做的事

**导出件要重新生成。** 它不进版本库（§3.2），所以每次发出去之前：

```bash
uv run --no-sync python scripts/export-outreach.py
```

然后粘 `.scratch/outreach-export/` 里的文件。**不要粘仓库里的源**——那里面有
标记。

CI 会保证「源里的标记与当前测量一致」，但它不会替人把导出件准备好：导出件的
内容由测量决定，而测量什么时候跑、跑在哪台机器上，是人的决定。
