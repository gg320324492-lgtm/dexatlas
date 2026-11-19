# 让「只指位置」的引用自己声明它声称的内容

**这一批做了什么**：`scripts/check-doc-citations.py` 的两类引用里，有一类一直是盲区
——「只指位置」的引用只被问「被引的那行是不是空行」。这一批让**文档自己声明**
「我指的是哪一段」，机器拿声明去比被引的那一段；并在公共契约表上逐条试点。

**它没有做什么**：声明不是行号的替代品。行号仍然会漂，声明做的是让漂移**看得见**。

---

## 1. 声明的形式

一条引用可以带一条声明。声明是一个反引号跨度，内容以 `anchor:` 开头：

```markdown
| `dexatlas version` | 打印版本 | | `src/dexatlas/cli/main.py:289-291` `anchor: version` |
```

### 1.1 为什么是「一段源码」而不是别的

作者给的两条路：「`fig:suite.passed` 那一处」、「`source_fingerprint` 那一行」、
某个小节标题。三条都是**稳定的名字**，不是位置、不是数字。本批沿用这条思路：
声明写的是**被引的那段里有什么**，而且写的是一个**在源码里找得到的名字或片段**。

### 1.2 为什么它不随行号漂

声明里没有行号。它写的是 `version`、`def version(`、`epilog=(`、
`@app.get("/projects"`、`[tool.hatch.version]` 这类东西 —— 它们在源码里由**内容**
定位，不由位置定位。代码往上挪十行，声明一个字都不用改；只有行号要改，而行号正是
机器能验的东西。

这与 `TREE_DOCUMENTS` 是同一套思路的再往前一步：那份注册表让文档声明「我说的是
哪棵树」，声明让文档声明「我说的是哪一段」。两处都是**文档自报**，机器去比。

### 1.3 为什么它不随数值漂

声明里没有数字。这是硬约束：**测量重写数字后，声明不会过期**。

代价是：一条指向「某行有个 91.6%」的引用，声明不能写那个百分比。它得写那个数字
**所挂的名字**——比如 `<!--fig:tests.total-->` 这个标记名、或者
`CONTRACT_CHECK_SECTIONS` 这个常量名。标记与常量名不随重测改变。

这一条是迁移其余文档时最容易踩的坑，§5 单独说。

### 1.4 两种锚点，两种查法

| 锚点 | 例子 | 怎么查 |
|---|---|---|
| 裸名字 | `version`、`EXIT_BAD_REQUEST` | 与「名了符号」的引用同一套查法：文件要在被引范围里**定义**它，或范围要在它打开的函数体里 |
| 源码片段 | `def version(`、`epilog=(` | 片段要在被引范围里**逐字出现**（空白归一化后） |

裸名字走结构化查法（强），片段走字面查法（覆盖非标识符的东西：路由、装饰器、
JSON 键、docstring 里的一句话）。规则落在 `DECLARATION`
（`scripts/check-doc-citations.py:426`）、`ANCHOR_NAME`（`:432`）、
`check_anchor_name`（`:1904`）、`check_anchor_fragment`（`:1936`）。

> **一个词的三个意思。** 本报告说的「锚点」是**引用声明的内容**；仓库里还有两个
> 同名的旧东西：Markdown 的**标题锚点**（`#fragment` 链接，`scripts/` 之外的
> 链接检查器管它），以及 `TREE_DOCUMENTS` 登记的**锚树**（一份文档描述哪棵
> commit）。三处不在一个层面：本批的「锚点」是**源码里的一段内容**，锚树是**一棵
> 树**，标题锚点是**一个标题**。本批不碰后两者。

### 1.5 代价：行变长了

一条引用从「`` `file.py:12-34` ``」变成「`` `file.py:12-34` `anchor: xxx` ``」，
宽度大约翻倍。契约表里最长的几行已经要换行才排得下，表格单元格里尤其明显。

这是本机制的真实成本，不是可以忽略的细节。三条缓解办法，按本批的实践排序：

1. **锚点尽量短。** 能用裸名字（`version`）就不用片段（`def version(`）—— 名字短，
   而且查法更强。
2. **锚点放在句子的括号里，不放在表格单元格里**（表格有列宽，挤不下）。
3. **接受它。** 一行 80 列变成 160 列，换来的是这一行在代码挪动之后会被门禁逮住。
   本批的判断是这笔交易划算 —— §3.2 那 13 条本来就指错的引用是这笔交易的收益。


---

## 2. 检查器怎么用它

### 2.1 声明绑在哪条引用上

声明**绑定到它前面最近的那条引用**，且两者之间不能隔着一个块边界 —— 与裸行号
``:143`` 的绑定规则完全一样（表格的一行是一个块，一个段落是一个块）。
实现见 `_resolve`（`scripts/check-doc-citations.py:1074`）。

这样写的好处是：声明与引用**分成两个跨度**，声明在文档里读起来是「这里，以及这里
说的是什么」，而不是一串挤在一起的代码。

### 2.2 查不上时怎么报

报的是「声明说的是 X，被引那段的 Y 不是 X」，并给出**它其实在哪**：

```
public-contracts.md:22  src/dexatlas/cli/main.py:289-291  anchor missing:
    the anchor `version` is at line 289  |  | `dexatlas version` | 打印版本 | ...
```

裸名字的报法与既有的「符号漂移」一致（`` `X` is at line N ``）；片段的报法是
`` the anchor `X` is at line N ``，找不到就说「不在范围里」。
见 `check_anchor`（`scripts/check-doc-citations.py:1877`）。

### 2.3 三条防呆

1. **孤立的声明要报。** 声明绑定不到任何引用（写在了引用前面、或者隔了一个块），
   它就什么也没说。报出来，不当它不存在。见 `document_orphan_declarations`
   （`scripts/check-doc-citations.py:1978`）。
2. **声明跨度不参与「名了符号」的推断。** 契约表里 `src/dexatlas/cli/main.py:289-291`
   `anchor: version` 这一条：声明里写的那个名字不是句子里被提到的名字，它是对源码的
   声明 —— 两条通道分开，不互相污染。
3. **在「声明型文档」里，不声明就报错。** `DECLARING_DOCUMENTS`
   （`scripts/check-doc-citations.py:441` 的 `DECLARING_DOCUMENTS`）列出的文档里，任何「既没有名了符号、又
   没有声明」的引用都报成 `declares nothing`。契约表在名单里，所以它的沉默是
   决定，不是疏忽。见 `check_declaration_of_content`（`:1952`）。

### 2.4 摘要多了一行

```
citations: 1375
  naming a symbol: 314
  pointing only at a location: 1061
  declaring what they point at: 60
```

最后一行是本批新增的：它让「有多少条引用带着声明」成为可数的，而不是猜的。

---

## 3. 试点：公共契约表改了什么

试点选 `docs/architecture/public-contracts.md`。它没有 release body 那种「行号绑在
`v1.0.0` 那棵树上」的特殊性（它在 `WORKING_COPY`），所以行号以当前工作副本为准。

### 3.1 逐条改了什么

- **59 条「只指位置」的引用全部带上了声明**，一条不剩。
  （58 个不同的引用字符串；`src/dexatlas/api/app.py:188-220` 在文中出现两次，
  两处都带上了声明。）
- 顺带发现并修正了 **13 条旧引用本来就指错了地方**：
  - **12 条指着隔壁命令的代码**。契约表的 CLI 一栏 13 行里，指错的那些**偏了 83 到
    110 行**：`version` 指着上一条命令的收尾（206，实为 289），`export` 指着 `search`
    的函数体（751，实为 855），`xrefs` 指着 `search` 的 docstring（825，实为 935）；
    API 那边 `src/dexatlas/api/app.py` 的 729–735 行指着 descriptor 的 400 校验（claim 说的是 409 的候选），
    MCP 那边 `src/dexatlas/mcp/server.py` 的 295–301 行指着 `get_evidence` 工具（claim 说的是 stdio 传输）。
  - **1 条差一行**：`src/dexatlas/cli/main.py` 的第 70 行指在 `name="dexatlas",` 上，而 Typer 应用的开头
    在 69。
- 每一处的行号都重新取自当前源码，**用的是定义/片段本身定位，不是手抄**。

### 3.2 为什么这些漂移此前是看不见的

旧的检查对「只指位置」的引用只问「被引的范围是不是空行」。上面 12 条偏了 83–110
行的引用，被引的那一行**都非空** —— 每一问都过。检查器报的是 `drifted: 0`。

这正是本批要补的洞：不是「检查器没看见有东西」，是「它没有可问的问题」。声明给了
它一个问题。

### 3.3 试点之后这份文档的性质

契约表现在**没有一条沉默的引用**了：每条引用要么名了符号（机器验名字在不在），
要么带了声明（机器验那段是不是还装着它声称的东西）。这条性质由
`tests/test_doc_citations.py:947` 守着 —— 它遍历这份文档的每一条引用，任何一条
既没有名了符号又没有声明，测试就红。

---

## 4. 红 → 绿怎么证的

新增 6 条测试（`tests/test_doc_citations.py:860` 起）。**在旧实现下**（把
`scripts/check-doc-citations.py` 换回 `HEAD` 的版本）：

```
FAILED test_a_citation_that_declares_what_it_points_at_is_checked
FAILED test_a_declared_name_is_checked_where_it_is_defined
FAILED test_a_citation_that_declares_nothing_in_a_declaring_document_fails
FAILED test_the_contract_table_declares_every_citation_that_points_only_at_a_location
FAILED test_a_declaration_that_names_no_citation_is_reported
5 failed, 6 passed
```

（`6 passed` 里有 5 条是既有测试被 `-k` 选中，与本批无关。）

五条红全是**断言失败**，不是属性错误：测试写成读 `getattr(citation, "anchors", ())`、
用 `raising=False` 挂 `DECLARING_DOCUMENTS`，就是为了让「红」红在**行为**上，
而不是红在「旧实现没有这个字段」上。

第六条（`test_a_declaration_that_still_holds_is_accepted`）在旧实现下是**绿的** ——
它守的是另一头：一条**成立**的声明不能被报成漂移。没有它，一个把一切都报红的检查器
也能过那五条。

换回新实现后，五条转绿；第四条要等契约表改完才转绿 —— 这就是试点本身的
红→绿。

---

## 5. 其余文档怎么改：难度清单

全仓 1375 条引用里，1061 条「只指位置」。按文档列：

| 文档 | 只指位置 | 适合改成声明吗 | 难度 |
|---|---|---|---|
| `docs/reports/stale-number-scan-2.md` | 277 | 部分 | **高**（量最大；且绑在固定树上） |
| `docs/reports/local-vs-ci-gates.md` | 96 | 部分 | 高（量大、绑固定树） |
| `docs/reports/readme-image-consistency.md` | 92 | 部分 | 高（量大、绑固定树） |
| `docs/reports/round-two-fresh-read.md` | 86 | 部分 | 高（量大、绑固定树） |
| `docs/reports/case-studies-client-read.md` | 68 | 部分 | 高（量大、绑固定树） |
| `docs/reports/v1.1.0-candidate-c10-manifest.md` | 61 | 是 | 中（工作副本；多引裸文件名） |
| `docs/reports/v1.0.0-github-release-body.md` | 60 | 部分 | 高（**主会话正在按语义重锚它，本批不碰**） |
| `docs/reports/outreach-first-read.md` | 39 | 部分 | 中（量大、绑固定树） |
| `docs/reports/post-release-rehearsal.md` | 37 | 部分 | 中（量大、绑固定树） |
| `docs/reports/english-reader-review-2.md` | 34 | 部分 | 中（量大、绑固定树） |
| `docs/reports/evidence-package-isolation.md` | 28 | 是 | **低**（工作副本；引的是代码） |
| `docs/reports/figures-auto-write-landing.md` | 19 | 部分 | 中（§5.1 的坑） |
| `docs/reports/ci-temp-redirect-fix.md` | 13 | 是 | 低 |
| `docs/reports/m8-4-note-and-c17.md` | 13 | 是 | 低 |
| `docs/reports/m10-reader-rehearsal-2nd.md` | 13 | 是 | 低 |
| `docs/reports/social-preview-howto.md` | 12 | 是 | 低 |
| `docs/reports/outward-number-parity.md` | 11 | 是 | 低 |
| `docs/reports/gate-self-checks.md` | 9 | 是 | 低 |
| `docs/reports/platform-gate-inventory.md` | 8 | 是 | 低 |
| `docs/reports/m10-material-fixes.md` | 8 | 是 | 低 |
| `docs/reports/m10-reader-rehearsal-3rd.md` | 6 | 是 | 低 |
| `docs/reports/denominator-and-tree-pass.md` | 5 | 部分 | 中（绑固定树） |
| `docs/reports/docker-image-samples.md` | 2 | 是 | 低 |
| `docs/analysis-provenance.md` | 1 | 是 | 低（90 条里只有 1 条沉默） |
| 其余 8 份 | 各 1 | 是 | 低 |

### 5.1 三种难度，和它们各自的原因

**低 —— 锚点是一个名字。** 引用指向一个函数、类或常量，锚点直接写那个名字，
机器用结构化查法验。例：`evidence_package.py:445` → `anchor: _is_a_safe_relative_path`。
这是绝大多数情况，也是契约表 59 条里的绝大多数。

**中 —— 锚点是一段源码。** 引用指向一条路由、一个 JSON 键、一个装饰器、或 docstring
里的一句话。锚点得挑一段**有辨识度**的字面量。例：`src/dexatlas/api/app.py:402-405`
`anchor: @app.get("/projects"` —— 锚点就是那条路由的装饰器。这类的难点是**挑**：
挑得太短会误匹配，挑得太长会被一次措辞调整打断。

**高 —— 锚点会是一个测量重写的数字。** 这是唯一真正难的一类，也是本批明确**不**
推荐硬扛的一类。例：

- `docs/portfolio.md:67` 指着一行「1,695 tests at」——数字本身每次重测都变，
  声明**不能**写它。
- `README.md:12-13` 的 badge URL 里嵌着 `1731%20passing`——同上。

这类引用的正确锚点是**数字旁边的稳定邻居**，不是数字本身：

- `docs/status.md:23-24` 指着 `<!--fig:tests.total-->1733<!--/fig-->` →
  锚点写 `<!--fig:tests.total-->`。**标记名不随重测改变**，数字在标记里面变。
- `tests/test_public_contracts.py:759` 指着
  `CONTRACT_CHECK_SECTIONS = {"_rest_requests": 28, ...}` → 锚点写
  `CONTRACT_CHECK_SECTIONS`。**常量名不随重测改变**，值在它右边变。

所以迁移这类文档时，判断标准是：**这段范围里有没有一个不随重测改变的名字可锚**。
有就容易；没有（例如散文里一个孤零零的数字），那这条引用就**不适合**这种形式 ——
它只能靠「范围非空」这一问，而这一问本来就弱。

### 5.2 绑在固定树上的文档，优先级应当更低

`TREE_DOCUMENTS` 里的 9 份文档的引用描述的是一棵**不动的**树。那棵树不动，引用
就不会漂，所以声明带来的边际收益比工作副本上的小：它能抓住的是「这份文档**从来
就没对过**」，而不是「它漂了」。

这不意味着不该改 —— 契约表的 13 条错误引用就是绑在工作副本上的，所以这类错误在
固定树上同样可能存在（只是抓不到「漂了」而已）。但按收益排，**工作副本上的文档
先改**：`docs/reports/v1.1.0-candidate-c10-manifest.md`（61）、
`evidence-package-isolation.md`（28）、`figures-auto-write-landing.md`（19）、
`ci-temp-redirect-fix.md`、`m8-4-note-and-c17.md`、`m10-reader-rehearsal-2nd.md`、
`social-preview-howto.md`、`outward-number-parity.md`、`gate-self-checks.md`、
`platform-gate-inventory.md`、`m10-material-fixes.md`、`m10-reader-rehearsal-3rd.md`。

### 5.3 另一种沉默，本次没有碰

契约表里还有一类「引用」根本不是引用：只写文件名、不写行号的跨度，例如退出码表
里那七行 `` `src/dexatlas/cli/main.py` ``。检查器看不见它们（`CITATION` 要求带
`:行号`），所以它们处于**双重失明**：既没有行号，也没有声明。本批没有把它们改成
带行号的引用 —— 那超出了「逐条改成带声明」的范围，且会新增 7 处需要人工定行号的
判断。**留给主会话决定要不要做**，做的话按 §5.1 的「低」难度走（锚点写常量名
`EXIT_EMPTY` 等）。

---

## 6. 这个机制不能做什么

说清楚它做不到的事，比说清楚它做到的事更重要。

1. **它不让行号不漂。** 代码挪了十行，引用还是得改行号。声明做的是让这次改动
   **被门禁逮住**，而不是让改动不必发生。
2. **它只验「这段里有没有它」，不验「这段是不是它想要的那一段的全部」。**
   一条引用声明了 `version`、范围覆盖了 `version` 所在的函数，外加前后 50 行
   无关代码，声明照样过。范围太宽仍然是文档作者的责任。
3. **一条声明只说一件事。** 契约表那条「同字节重复上传返回既有项目；failed 项目
   重新上传会重试」本来是两个断言，本批用了一个锚点（`ProjectStatus.FAILED`）
   覆盖二者。机制支持一条引用挂多个声明（`Resolved.anchors` 是元组），但读起来
   冗长，试点里没用。
4. **锚点挑得不好，等于没有。** 一个两三个字符的片段会误匹配；本批靠「碎片要够
   长」这条人工纪律，没有机器把关。
5. **它不检查散文。** 声明说的是「那段代码里有什么」，不是「那句话说得对不对」。

---

## 7. 这一批做到的，和留给主会话的

### 本窗口做的

- `scripts/check-doc-citations.py`：**逻辑**（未动 `DOCS` 名单）
  - 声明的语法与解析（`DECLARATION`、`ANCHOR_NAME`）
  - 锚点的两种查法与两种报错
  - 声明与引用的绑定、孤立声明的检测
  - `DECLARING_DOCUMENTS`：声明型文档里「不声明就报错」
  - 摘要新增「declaring what they point at」一行
- `docs/architecture/public-contracts.md`：59 条「只指位置」的引用逐条改成带声明，
  顺带修正 13 条本来就指错的引用
- `tests/test_doc_citations.py`：6 条回归测试，旧实现下 5 红
- `docs/reports/post-release-rehearsal.md`：**机械重映射 4 条行号**。这一份不是我改
  的，是**我改 `scripts/check-doc-citations.py` 把它的行号挪了**，按 CLAUDE.md 第 4 条
  必须重映射。其中指向 `TREE_DOCUMENTS` 的那一条，重映射器**没有自动处理**——它认为
  该符号有两处提及（定义与使用）且相距太远，没有任何等长范围能同时罩住，按它自己的
  规则「留给人判断」；人判断的结果是 `scripts/check-doc-citations.py:236-249`
  （注册表本身，14 行，与旧范围同形，旧范围是 200-213）。
  **第二轮合并后这 4 条又按指代物重新推导过一遍**（见下一节）。
- 本报告

### 本批第二轮（合入之后）改了什么

合入后主会话登记了本报告，于是本报告自己的引用**开始被检查**，检查器当场报出 7 条
发现（3 条「孤儿声明」、1 条「引用模糊」、1 条「锚点不在范围」、1 条「行号漂了」、
1 条「范围是空的」）。这一轮把它们逐条改掉：

- **孤儿声明 3 条**：两处改成**真的绑定对**（`src/dexatlas/cli/main.py:289-291`
  `anchor: version` 与 `src/dexatlas/api/app.py:402-405`
  `anchor: @app.get("/projects"`），一处改成散文 —— 一处讲的是「假如范围开得很宽」
  的假设，本来就不该是活引用。
- **引用模糊 1 条**：`app.py` 在仓库里不止一份（`api/app.py` 与 `mcp/server.py`），
  改成全路径。
- **锚点不在范围 1 条**：`evidence_package.py` 的例子原来指着 218 行（那是**调用**处），
  锚点说的是函数名 —— 改成 436 行（**定义**处）。
- **行号漂了 2 条**：`DECLARATION` 与 `DECLARING_DOCUMENTS` 的位置因为另一扇窗口往
  `DOCS` 名单里加了两份报告而各移了 5 行，**按符号重新推导**，不是按行号差平移。

另外 `docs/reports/post-release-rehearsal.md` 的 4 条引用也按指代物重新推导了一遍
（`TREE_DOCUMENTS` 的注册表、`tree_of`、`check_declaration`、`tree_fingerprint`）——
那次合并把检查器挪了位置，机械重映射够不着它们（那些引用**名了符号**但范围仍然罩住了
符号的定义，所以检查器与重映射器都认为它们没漂）。

### 留给主会话的

1. **合入后要重测一轮。** `scripts/` 与 `tests/` 在源码指纹的覆盖范围内，本批的改动
   让报告里的数字过期了；`scripts/refresh-report-figures.py` **本批没有跑**，按
   指示由主会话在合入后统一重测。
2. **本报告已被登记进 `DOCS`。** 主会话已把本报告加进 `scripts/check-doc-citations.py`
   的 `DOCS` 名单（`docs/reports/README.md` 的报告数也一并登记）。因此本报告自己的
   引用**现在是被检查的** —— 本次修改就是它变成红的那些发现的来由。
3. **release body 不在本批范围。** `docs/reports/v1.0.0-github-release-body.md` 的 60 条
   「只指位置」引用由主会话按语义重锚；本批没有碰它一个字。
4. **§5.3 的「文件级引用」要不要改成带行号的引用**，由主会话决定。
5. **其余文档的迁移**（§5.2 的优先级清单）不在本批范围内。
6. **贡献者文档里要不要写这个语法。** `CLAUDE.md` 与 `AGENTS.md`（两份必须一样，
   `tests/test_docs.py` 守着）现在只说「改完 `src/` 要重映射引用」，没提声明这种
   写法。这两份不是本批的文件（且改它们要同步改两份），所以留给出文档的人决定。

### 一个查出来的缺陷，请主会话排期：**围栏代码块会让后面的引用失去检查**

这一批在核对本报告自己的引用时，查出检查器的一个既有缺陷。它与声明机制无关，
但它正是「引用不被检查」这一类问题，所以记在这里。

**现象。** `clauses()` 收集「要跳过的反引号跨度」与「围栏代码块」放进同一个队列，
逐个跳过。围栏代码块里常常**含有**反引号跨度（代码样例里再写代码）。跳过一个围栏
之后，队列里剩下的那些**被围栏包住的**跨度起点落在游标之前，于是
「`index == spans[0][0]`」这个判断再也不成立 —— **队列从此堵住**，后面每一个跨度
都不再被跳过。

**后果。** 跨度不再被跳过，意味着子句的边界可以落在跨度**内部**：引用
`core/models.py:296` 里的那个冒号是子句的终止符，于是边界切在冒号后面，
**这条引用所在子句里只剩半截**，它「名了符号」这件事就丢了 —— 检查器不再拿那个
符号去比。

**实测。** 把 `clauses()` 的一行改对之后，全仓「带符号声明」的引用数从 333 变成 343
—— **10 条引用此前被静默地降级成「只指位置」**（只查「在不在」，不查「是不是」）。
受影响的文档 4 份：`docs/reports/case-studies-client-read.md`（12 个围栏块）、
`docs/reports/m10-reader-rehearsal-2nd.md`、`docs/reports/m10-reader-rehearsal-3rd.md`，
以及**本报告自己**（2 个围栏块）。

**补丁**（`scripts/check-doc-citations.py` 的 `clauses()`）：

```python
        if spans and index == spans[0][0]:
            index = spans[0][1]
            spans.pop(0)
            continue
```

改成

```python
        if spans and spans[0][0] <= index:
            # A span that starts before the index has been overtaken by a
            # fenced region that contains it: skip it too, or every span
            # after it loses the protection and a clause boundary can fall
            # inside a citation.
            index = max(index, spans[0][1])
            spans.pop(0)
            continue
```

**本批为什么没改。** 这一行改动会改变全仓的判定：它让 10 条引用重新带上符号声明，
因而**会多出 3 条发现**，**全部落在 `docs/reports/case-studies-client-read.md`**
（另一扇窗口的文件，本批不碰）。那 3 条里有一条看着是真的（`storage.py` 的第 1065 行
与 `class_count` 差一行），另两条像检查器的「符号归属」启发式在更长的子句上抓错了符号，
**需要人判断**。改共享门禁的行为、并让别的窗口的文档变红，**不是本批该单方面做的
事** —— 所以补丁放在这里，由主会话排期。

**本报告自身已经按「两种检查器都绿」整理过**：本报告里所有「历史引用」（讲的是旧
引用当时指着哪里）都改成了散文形式，不再是活引用；所有「当前引用」都按**指代物**
重新推导过（用符号在源码里的定义行与函数体推导，不是按行号差平移）。因此无论那个
缺陷修不修，本报告的引用都是**真的**。

### 本批跑过的门禁

任务指定的六道门禁，全绿：

```
ruff check .                                    通过
ruff format --check .                           通过
mypy                                            通过（68 个源文件）
vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80   退出 0
scripts/check-version-claims.py --base auto     退出 0
scripts/check-doc-citations.py                  本批的文件 0 发现
```

`scripts/check-doc-citations.py` 这一行要读上下文：**全仓报 drifted: 10，全部来自另一扇
窗口的 `docs/reports/handwritten-numbers-audit.md`**（主会话已把那份交回给那扇窗口）。
本批的三个文件 —— 本报告、`docs/architecture/public-contracts.md`、
`docs/reports/post-release-rehearsal.md` —— **各 0 发现**。

而且它们在**两种检查器**下都是 0：当前这版，以及 §7.1 那个修好围栏块缺陷之后的版本。
这一点是特意做的：本报告里凡是「历史引用」（讲的是旧引用当时指着哪里）都改成了散文
形式，不再是活引用；凡是「当前引用」都按**指代物**重新推导过 —— 用符号在源码里的定义
行与函数体推导，不是按行号差平移。

### 全套 pytest 的结果（不是本批指定的门禁，但跑了）

```
15 failed, 1630 passed, 88 skipped, 17 errors
```

五类失败，**没有一类是本批的改动造成的**，逐条查过：

1. **19 条 androguard 集成/隔离测试（17 errors + 2 failed）—— 环境缺料。**
   `fixtures/apk/` 里只有 `SOURCES.md`，两个 fixture APK（`TestActivity.apk`、
   `multidex.apk`）没有取回。CLAUDE.md 明写：没有取料，集成套件**失败而不是跳过**。
   需要 `bash scripts/fetch-fixtures.sh`。
2. **2 条 `tests/test_doc_citations.py` —— 另一扇窗口的报告。** 这两条断言的是
   `assert not report.findings`，覆盖**全部** DOCS；另一扇窗口的
   `docs/reports/handwritten-numbers-audit.md` 有 10 条发现，于是两条一起红。
   **本批的三个文件各 0 发现**，红的是那一份。
3. **1 条 `test_docs.py::test_all_relative_links_resolve` —— 别的窗口的坏链接。**
   断链全在 `docs/reports/m10-material-fixes.md` 与
   `docs/reports/m10-reader-rehearsal-3rd.md` 里，`HEAD` 版本就有（前者 10 处），
   本批没碰这两个文件。
4. **1 条 `test_backend_timeout.py::test_a_windows_launcher_is_stopped_with_its_work`
   —— 偶发。** 单独跑是绿的（Windows 上停一个进程的时序测试）。
5. **9 条数字过期（`test_execution_report_*` 3 条 + `test_how_to_verify.py` 6 条）
   —— 预期的。** `scripts/` 与 `tests/` **在源码指纹的覆盖范围内**，本批第一轮往
   `tests/` 里加了 6 条测试，于是执行报告里的测试数与指纹都过期了。树里现在 1750 条
   测试，文档写着 1733 —— 差的 **17 条**里，**11 条是本批之前就缺的**（本批第一轮
   加了 6 条），也就是说这批失败**在本批之前就已经存在**。这正是「改 src/tests 后
   最终重测量要重跑」的正常结果：**重测留给主会话**（§7）。
