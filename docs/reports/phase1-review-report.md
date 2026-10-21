# Phase 1 源码评审报告 — DexAtlas

**评审对象：** v0.1.3 之后的开发状态（提交 `8df894b` 及后续修复）
**评审协议：** [`docs/roadmap/ROADMAP.md`](../roadmap/ROADMAP.md) 末尾的「Review protocol」
**配套材料：** [成熟度评估](phase1-maturity-assessment.md) · [执行报告](phase1-execution-report.md) · [Phase 2 issue 清单](phase2-issue-list.md)

---

## 1. 评审怎么做的

路线图把评审分成五步。这份报告是第 4 步的产物；第 3 步的成熟度评估在
[配套材料](phase1-maturity-assessment.md)里，第 5 步的下一阶段计划在
[Phase 2 issue 清单](phase2-issue-list.md)里。

第 2 步（架构与代码审核）**分三个方向并行**，各自独立工作：

| 方向 | 范围 | 发现 |
|---|---|---|
| 核心实现与调用路径 | 管道、存储、三个后端 | 15 条 |
| 接口一致性与安全边界 | CLI ↔ API ↔ 存储的契约、路径穿越、不可信输入、权限边界 | 14 条 |
| 测试覆盖与可靠性 | 覆盖率数字本身、测试实际证明了什么、CI 真的跑了吗 | 15 条 |

**共 44 条。**

### 1.1 评审用的方法

三个审核 agent 被要求做同一件事：**去破坏实现，看测试会不会红**。

这不是比喻。审核 agent 的做法是把一段代码删掉或改坏，然后跑测试看结果。
「测试全绿」在这个项目里出现过太多次，所以「这段代码删了会怎样」是唯一
能回答「测试到底证明了什么」的问题。

结果：**44 条里有相当一部分是「删掉这段代码，测试全绿」**——也就是说，
这些缺陷不是被测试发现的，是被「测试没发现」这件事本身暴露的。

### 1.2 复核

每一条发现都在**新基线上逐条复核过**，复核用的是探针而不是转述：

| 复核方式 | 用在哪 |
|---|---|
| 造一个具体的坏输入，跑一遍，看输出 | 路径穿越、上传覆盖、默认配置下的 JADX |
| 删掉实现的一行，看测试红不红 | 每一条修复都必须通过这一关 |
| 在源码包里跑检查器 | 检查器能不能被读者运行 |
| 在 WSL 的真 Linux 上跑一遍 | 平台差异（已经栽过两次） |

**复核否掉了一些审核结论**，也纠正了评审记录里的错误位置——
比如「loguru 的 handler 在 `core/logging.py`」——那个文件根本不存在。

### 1.3 这份报告里的每一条，都标了「怎么验的」

不复述审核 agent 的话。每条发现要么给出复现的命令，要么给出实测的输出。
**没有复现过的不写进来。**

---

## 2. 结论

| | |
|---|---|
| 阻断级 | 6 条，**全部已修** |
| 重要级 | 16 条，**全部已修或在修** |
| 可选级 | 12 条 |
| 推迟到 Phase 2 | 9 条，每条带两个方案和推荐 |

**成熟度总分 5.50 / 10**（六个加权维度，见[成熟度评估](phase1-maturity-assessment.md)）。

分数不高，但**它的用处不在分数上**。这个项目在这一轮里证明了一件事：
**它现在能自动发现自己的一部分问题**——版本声明检查器、引用检查器、
报告数字的重新测量，都从「靠人记得」变成了「靠工具」。

评审挖出来的 21 类「宣称完成了、实际没有完成」（见
[状态页第 6 节](../status.md)）是这个项目最诚实的一份资产：
它记录的不是这个项目做对了什么，是**它曾经怎样骗过自己**。

---

## 3. 阻断级：6 条，全部已修

### B1 · 上传的文件名由客户端决定 → 一个项目的符号表装上另一个 APK 的类

**它声称**：每个项目只装它自己的 APK 的符号。
**实际**：目标文件名是 `Path(file.filename).name`——**客户端说了算**。
两个不同的 APK 用同一个文件名上传，第二个覆盖第一个；而分析是**后台任务**，
它读的是那个路径，不是上传时的字节。

**复现**（构造时序：后台分析在跑 → 同名文件被覆盖）：

```
A 的哈希: 80a8fe0e8120   ← A 的元数据，说的是 demo.apk
存进去的类: com.example.strings.Constants   ← 这是 strings.apk 的类
项目记录的哈希: 80a8fe0e8120
```

**为什么这比「哈希对不上」更糟**：读者核对哈希会**通过**——哈希确实是 A 的，
元数据也确实是在 A 的字节上算的。**但那个类根本不属于这个 APK。**
证据链的每一环都自洽，指向的却是错的东西。

**这是整个评审里最严重的一条**：它破坏的正是这个项目立身之本。

### B2 · 默认配置下 JADX 的 Java 反编译完全失效，报告照旧写着 jadx 的版本

**它声称**：JADX 把 APK 反编译成 Java，索引读它的输出。
**实际**：`settings.py` 的默认工作区是**相对路径** `.dexatlas`，而
`jadx/adapter.py` 同时传了相对的 `--output-dir` 和 `cwd=output_dir`——
**同一个路径被解析两次**，JADX 把源码写进双重嵌套目录：

```
.dexatlas/projects/apk_XXX/jadx/.dexatlas/projects/apk_XXX/jadx/sources/...
```

而索引找的是 `.dexatlas/projects/apk_XXX/jadx/sources/...`——**找不到**。

| | 相对工作区（**默认**） | 绝对工作区 |
|---|---|---|
| 索引到的类数 | 4 | 5 |
| `dexatlas source` | `source kind: smali`（回退到 Apktool） | `source kind: java` |
| 证据条数 | 9 | 10 |

**为什么测试抓不到**：`tests/conftest.py` 的工作区永远是绝对路径。
**默认部署路径从来没被测过。**

### B3 · 版本声明检查器放过「本次提交造成的失真」

**它声称**：`--base` 模式只报本次提交新增的失真。
**实际**：「已知失真」集合是用 **HEAD 的事实**去重跑 base 的文档算出来的。
于是一个提交打了 `v0.1.4` 的 tag、而文档仍写「v0.1.3 之后」——
在 base 上用同样的新 facts 重跑会产生同样的 finding → key 相同 → 划进 known → **不算失败**。

**这是「唯一一道自动防线，在它要防的那个场景下失效」。**

**复现**：克隆 → 提交 → 打 tag → `--base HEAD~1` → 修复前 exit 0，修复后 exit 1。

### B4 · 文档的引用检查器只查 18/94，而且 `main()` 永远 return 0

**它声称**：`check-doc-citations.py` 校验文档里每一处 `文件:行号` 引用。
**实际**：94 处引用里只有 18 处被真正校验；而且 `main()` **永远 return 0**，
测试也没复用它——**而是把逻辑重写了一遍**（连容差都不一样：脚本 `slack=0`，测试 `slack=2`）。

审核 agent 把脚本整段范围检查删掉，**测试照样绿**。

**现在**：94 处引用、93 处带符号校验、0 漂移。

### B5 · JADX 后端没有任何路径守卫

Apktool 侧有完整的守卫（逐段拒绝 `..`、绝对路径、盘符、控制字符、通配符，
还有 8 个恶意用例守着）。**JADX 侧一个字符都没检查**：

```python
candidate = sources / Path(class_name.replace(".", "/") + ".java")
```

`Path("C:/...")` 是绝对路径，pathlib 里 `sources / 绝对路径` **等于那个绝对路径本身**。
审核 agent 用探针替换 `read_text`，证明**工作区外的文件真的被打开并读进了内存**。

HTTP 面：`GET /projects/{id}/classes/C:/Users/admin/.../secret/loot/source` → **500 + 纯文本**
（不是 API 的 `{"detail":...}`），CLI 面打出带服务器绝对路径的完整回溯。

### B6 · Androguard 一个 dex 解析失败 → 已索引部分的证据一条不生成

符号照样进数据库，报告的指标行写「有证据的交叉引用: 0」，
读者会读成「这个 APK 没有内部调用」。

**这是错的结论，不只是少了证据**：解析失败的是另一个 dex，
成功那个 dex 的类确实存在、那些调用边确实在字节码里。

**为什么能藏着**：现有测试用的都是好样本，这条路径要让一个 dex 真的坏掉才会走到。

---

## 4. 重要级：16 条

按严重程度排列。每条都标了**怎么验的**——不复述审核 agent 的话。

### I1 · `analyze()` 没有 try/except：异常穿出去，项目停在 `running`

**它声称**（docstring 第 110 行）：「Every later failure is recorded on the project
instead of raised.」
**实际**：整个 `analyze()` 里**一处 `try/except` 都没有**。

**复现**（让后端在分析中途抛异常，然后查数据库）：

```
项目行: status='running'  classes=0  methods=0  evidence=0  errors='[]'
```

**没有任何地方说这次分析失败过。** 再传同一个 APK，API 命中已有哈希
（`project.id` 是内容哈希）→ **直接返回，永不重跑**。

这条有两个后果，第二条更狠：第一，报告和 API 都说「项目在跑」；
第二，那个 APK 从此再也不会被分析。

### I2 · `/health` 每个请求都开数据库写锁

**它声称**：这是一个 liveness 探针。
**实际**：`Depends(get_analyzer)` → 每个请求 `Analyzer(settings)` → `Store.open()`
→ 每次跑一遍 `executescript(_SCHEMA)` + `DELETE/INSERT schema_info`。

**一次纯读的探活，在拿 SQLite 唯一的写锁。**

**修法**：`/health` 和 `/backends` 改用 `BackendRegistry`——后端可用性是关于机器的
事实，不是关于数据库的。`Store.open()` 也改成「版本对得上就不写」。

**实测**：`Store.open()` 从 **9.3ms → 1.1ms**，而且不再拿写锁。

**探针怎么证明有牙齿**：另开一个连接 `BEGIN IMMEDIATE` 占住写锁，再 `Store.open()`。
SQLite 单写者，WAL 下读者不被挡——**只要 open 写就会失败**。未修复的代码在这里抛
`database is locked`（耗时 5.48s）。

### I3 · `PRAGMA journal_mode = WAL` 在每次事务里——一次纯读也在写库

**它声称**：读就是读。
**实际**：`storage.py:375`，而 `transaction()` 是**每一次读写**都走的。
而设 WAL 是**写操作**（它改数据库的文件格式）。

**复现**（两个并发上传请求）：

```
sqlite3.OperationalError: database is locked
  File "src/dexatlas/core/storage.py", line 375, in transaction
    connection.execute("PRAGMA journal_mode = WAL")
```

**栈顶就是这一行。** 这是 I2 的根因，也是「workspace 并发不安全」的根因——
并发打开失败率实测 15/20。

**这条的好处是它可以确定性地测**：不需要时序，「一次纯读不写库」用文件修改时间
或者 pragma 的执行计数就能断言。

### I4 · `cross_references_with_evidence` 数的是被调方法数，`cross_references` 数的是边数

**它声称**：「How many of those cross-references are backed by an evidence record.」
**实际**：`add_cross_references` 按 `by_callee` 分组——**一个被调方法一条记录**，
而 `xrefs` 表**一行一条边**。

fan-in=3 时（一个方法被三处调用），报告说「1 条交叉引用有证据」，实际有 **3 条边**。
两个数字放在一起，读者会以为「3 条边里只有 1 条有证据」。

### I5 · 超过 200 个类时，反编译覆盖率那条证据被挤出报告的证据表

**它声称**：报告的每一行都能核对。
**实际**：`markdown.py` 的证据表只保留前 200 条。而证据的顺序是
「manifest 结论 → 交叉引用 → 类 → 反编译覆盖率」——**反编译覆盖率排在最后**。

**复现**（构造 251 条证据：250 个类 + 1 条反编译）：

```
evidence records: 251   report cap: 200
decompilation record present in the report table? False
report says: '_51 further evidence records omitted._'
```

**指标行还在，支撑它的那条证据没了。**

### I6 · `xrefs` 表没有主键

**它声称**（`storage.py:427`）：「symbol tables key on the symbol」。
**实际**：`xrefs` 表没有 `PRIMARY KEY`、没有 `UNIQUE`，而 `classes`/`methods`/`fields` 都有。

**重复有两个来源**（评审只提到一个）：跨 DEX，以及**同一个 DEX 里调用同一目标两次**
——后者连 provenance 都完全相同。

### I7 · workspace 并发不安全：同一个 APK 的两次分析共用一个目录

**机制**：`workspace = projects_dir / project.id`，而 `project.id` 是内容哈希——
**同一个 APK 永远是同一个 id**，所以两次分析写进同一个目录。

**复现**：同 workspace 并发分析 → `OperationalError: database is locked`（根因是 I3）。

**这一条要设计取舍**（临时目录 + 原子替换 vs 文件锁串行化），所以进 Phase 2 清单。

### I8 · API 导出的报告写「Analysis time 0.0s」，CLI 导出的同一份是真实耗时

**它声称**：两个接口共享同一个分析内核。
**实际**：`_rebuild_result` 从存储重建结果时**不设 `duration_seconds`**，
而 `projects` 表**也没有这一列**。所以 API 导出的报告永远写 0.0s。

**实测**：`| Analysis time | 0.0s |`

### I9 · 「证据等级不可提升」在 docstring 里被写成机制，实际是约定

**它声称**（`evidence.py` 的 docstring）：「The level field is **the mechanism**
that stops an unverified claim from being reported as a finding」。

**实际**：`Evidence` 类没有 validator。探针：

```
Evidence(kind=BEHAVIOUR, level=VERIFIED)  ->  level = verified
builder.add(kind=BEHAVIOUR, level=VERIFIED) ->  level = verified
```

而报告会把它渲染成 **"Deterministically established by an analysis tool."**——
一句假话，因为产生它的可能是个模型。

**而且比这更糟**：`LEAD` 和 `INSUFFICIENT` 在 `src/` 里**一个生产者都没有**
（只在报告的文案表里出现）。所以现有测试是手工造一个 LEAD 再断言它还是 LEAD——
**测的是恒等函数**，而真正会提升等级的那条路没有任何测试。

**修法**：给模型加 validator（无论怎么构造都拒绝提升），并让 `LEAD` 有真正的生产者。

### I10 · 报告的数字只跟旁边的记录自比

**它声称**：`<!--fig:suite.passed-->` 是完整环境下的结果。
**实际**：它只与同一文件里嵌的 record 自比。而 `source_fingerprint()` **只哈希 `src/`**——
**加测试不会让覆盖率数字失效**。

**复现**（评审的实验）：把 record 里的 `"passed": 548` 和图里的数字一起改成 999
→ **没有任何新失败**。

**修法**：指纹覆盖 `tests/` 和工具配置；数字改成真测（新收集的测试数 + coverage 自己
的解析器读出的语句数）；记录存**跳过测试的身份**而不是数量。

**我独立复验过**：把报告数字改成 999，**3 个测试立刻红**。

### I11 · 版本号每个符号查一次（已修）

每个类、方法、字段、交叉引用都带一条 provenance，每条都要问一次后端版本号，
而那次查询要扫一遍已安装的发行版。实测：12,000 个方法的一次运行里 **82 秒有 80 秒**
花在这上面。修法是每个后端只问一次。

### I12 · 触到上限就静默截断，项目照样报「完成」（已修）

索引少了几千个方法，`project.errors` 是空的，报告里的数字和数据库的行数**完全一致**
——因为它们忠实地记录了一个被砍短的索引。现在触顶会记 `output_truncated`。

### I13 · 三个上限里有两个是按 DEX 文件算的（已修）

四个 DEX 的 APK 拿到四倍额度——**恰好是最需要封顶的那种 APK 反而拿到最多**。
现在一份预算一个 APK。

### I14 · `evidence` 表从不清空（已修）

重分析后报告说 9 条、数据库实际 10 条，`E-00xx` 编号还会整体漂移。
现在 `save_evidence` 先删后写。

### I15 · 文档里的行号引用漂移没人管（已修）

原来 94 处引用里只有 18 处被真正校验，其余只检查「那个文件还在」。
现在 93 处带符号校验，**0 漂移**。

### I16 · 版本声明检查器在自己的目标场景下失效（已修）

见 B3。

---

**这一组里最值得记的是 I3 和 I9。**

I3 的教训是：**一个「看起来像配置」的东西（journal mode）其实每次都在写**，
而它在 SQLite 上是单写者——所以一次读就能锁住整个部署。

I9 的教训更深：**docstring 里的「机制」和「约定」差一个字，但差的是一整个保证**。
写「mechanism」的人以为有东西在挡着；写测试的人造了一个恒等的情况，
于是「有测试」和「有保证」被混为一谈。

---

## 5. 可选级与推迟的

---

## 6. 这个项目现在能自动发现什么

这一节比任何一条发现都有用——它说明**下一次同类缺陷会不会重演**。

| 现在能自动发现 | 靠什么 |
|---|---|
| 文档里的版本陈述与仓库的事实矛盾 | `scripts/check-version-claims.py`，CI 的 lint job |
| 文档里的行号引用漂了 | `scripts/check-doc-citations.py`，94 处里 93 处带符号校验 |
| 报告里的数字与代码对不上 | `scripts/refresh-report-figures.py --check` |
| 加了测试但报告没重刷 | 指纹现在覆盖 `tests/` 和工具配置 |
| 一次测量跳过了**另一批**测试 | 记录现在存跳过测试的**身份**，不是数量 |
| 证据等级被提升 | `Evidence` 模型上的 validator |
| 类证据上限静默截断 | 证据表里现在有一条记录说它截断了 |
| 上限被删掉而测试不红 | 四条新测试钉住四个上限 |
| README 徽章过期 | 徽章的数字现在由测量写入 |

---

## 7. 这次评审的方法本身，有什么局限

诚实地说出来，因为一份不说自己局限的评审报告不可信：

1. **审核 agent 审的是代码，不是需求。** 「这个功能该不该有」不在评审范围内。
2. **并发只在单进程内用线程验过。** 没有在 uvicorn 多 worker 的真实部署下验过。
3. **全部实测在 Windows 上。** POSIX 的进程组终止靠 WSL 验过一部分，
   但没有在所有平台上跑过完整套件。
4. **变异测试只做了 2 处**，不是全部 773 项测试的完整变异评分。
5. **没有真实商业 APK。** 大型 APK 基准用的是合成样本。
6. **成熟度评估的分数是评估者的判断，不是测量结果。** 六个维度里，
   权重最高的两项（核心功能 25%、Agent/MCP 20%）恰恰是最需要主观判断的。

---

## 8. 给 Phase 2 的输入

见 [Phase 2 issue 清单](phase2-issue-list.md)——每条带现状、两个方案、
推荐、验收标准，以及**钉住它的测试该怎么写**。
