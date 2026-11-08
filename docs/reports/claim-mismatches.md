# 注释 / docstring 与代码不一致：M1–M24 逐条复核

## 这份文件是什么

`docs/reports/phase2-issue-list.md` 第 8 节列了 25 处「文档/注释/docstring 声称与代码实际不一致」，
编号 M1 到 M24。**那份清单是一张快照**，量于 commit `8df894b`（2026-10-21）。此后落地了五个
大变更 —— P2-001（overload-safe 方法解析）、P2-002（analysis runs 与事务化结果）、
P2-003（call site 与 call edge）、P2-004（证据不变量）、P2-005（运行时隔离）—— 其中一半以上的
条目被这些变更直接改掉了，清单里的行号也指向了一棵不存在的树。

所以这份文件是那份清单的**复核结果**，不是它的实施记录。每一条都回到代码里读，给出三种结论之一：

| 结论 | 含义 |
| --- | --- |
| **已被后续变更修好** | 清单描述的那个缺陷不再成立。写清是哪个变更修的，以及怎么核对的。 |
| **仍为真 —— 改措辞** | 缺陷还在，但代码的行为是对的：该改的是注释，让它说代码实际做的事。 |
| **仍为真 —— 改行为** | 代码本身说的是假话：该改代码，并配一个**去掉修复就变红**的测试。 |

复核基线：本分支的 `HEAD`（`6ecbd27`）加上本分支自己的改动。行号都指这个状态。

## 结论一览

| 结论 | 条数 | 条目 |
| --- | ---: | --- |
| 已被后续变更修好 | 8 | M1 M2 M4 M5 M6 M21 M22 M24 |
| 仍为真 —— 改措辞 | 14 | M3 M7 M8 M10 M11 M12 M14 M15 M16 M17 M18 M19 M20 M23 |
| 仍为真 —— 改行为 | 2 | M9 M13 |
| **合计** | **24** | |

原清单说「4 条改代码」（M1 M2 M9 M13）。复核之后只有 2 条需要改代码：**M1 与 M2 已经被
`a388867` 修掉了**，清单写下的时候它们还成立。

---

## 逐条

### 已被后续变更修好（8 条）

#### M1 —— 报告写了一个从未被测量的时长

**清单说的**：`api/app.py` 的 `_rebuild_result` 重建 `AnalysisResult` 时不设 `duration_seconds`，
而报告无条件打印这一行，于是每个从 REST API 导出的报告都写着「Analysis time \| 0.0s」。

**现在**：已经不成立。`a388867`（*Fail an analysis loudly, and give every reported number one
meaning*）引入了 `analysis_duration()`（`src/dexatlas/core/pipeline.py`），它返回 `None` 而不是 `0.0`
表示「没被计时」；Markdown 渲染器（`src/dexatlas/reports/markdown.py` 的 `_duration_cell`）在那种
情况下写 `unknown`，JSON 渲染器写 `null`。`_rebuild_result` 的 docstring 也明说了为什么：
一份对一次三秒的分析写「0.0s」的报告，说的是这个分析从未产生过的数。

**怎么核对的**：读 `analysis_duration` 的实现、`markdown.py` 的 `_duration_cell`、`json_report.py`
的 `_summary_block`，以及 `api/app.py` 的 `_rebuild_result`，四条路径都走同一个函数。

#### M2 —— 存储层的失败既不记录也不包装

**清单说的**：`pipeline.py` 注释写着「Every later failure is recorded on the project instead of
raised.」，而存储层的 `sqlite3.Error` 直接上抛，项目行留在 `running`。

**现在**：已经不成立，而且是被 `a388867` 与 P2-002 一起修掉的。`Analyzer.analyze` 现在把
`Exception` 交给 `_record_failure()`：失败先被记到 project 上（状态写成 `failed`，原因进
`project.errors`），再以 `AnalysisFailed` 抛给调用方。那句注释本身也不在了 —— `analyze` 的
docstring 现在精确地写着两种失败的分工：后端失败记在 project 上继续跑，分析自身的失败把
project 标成 failed 并抛出去。

**怎么核对的**：读 `analyze` 的 `try/except` 块与 `_record_failure`，并确认 `sqlite3.Error`
是 `Exception` 的子类、落进那个分支。

#### M4 —— 合并类定义的注释把 Apktool 算成了类定义的来源

**清单说的**：`pipeline.py` 的 `_merge_classes` 注释写「Backends disagree about a class's flags
— Apktool knows the manifest declaration, Androguard the DEX definition」，而 Apktool 从不产出
`ClassRef`。

**现在**：已经不成立。`065301f`（*Say what the backends and the migration actually do*）把
`_merge_classes` 的 docstring 改成：产生类定义的是 Androguard 和 JADX，Apktool 一条都不产出，
而且两个产出者之间**并不**在 flags 上冲突 —— 只有其中一个报 flags。

**怎么核对的**：读改写后的 docstring；`tests/test_docstring_claims.py` 里有一条检查会读
adapter 的源码来数谁构造 `ClassRef`，断言产出者集合是 `{androguard, jadx}`，并要求
`_merge_classes` 的 docstring 提到每一个产出者、且不能把不产出类的那一个算进去。

#### M5 —— 迁移函数写着「Additive only.」，却 DROP 了一张表

**清单说的**：`storage.py` 的 `_migrate` docstring 第一句是「Additive only.」，同一个函数十几行
之后 `DROP TABLE resources`。

**现在**：已经不成立。`065301f` 把它改成「Two kinds of change live here, and only one of them is
additive.」，并分两段讲清楚：列是原地加的（行还在），表是重建的（行不保留，因为资源表是缓存
而不是真相来源）。

**怎么核对的**：读改写后的 docstring 与 `_migrate` 的函数体；`tests/test_docstring_claims.py`
里有一条检查会在源码里出现 `DROP TABLE` 时要求 docstring 不再含「additive only」。

#### M6 —— 文档说归档只读中央目录，不解压

**清单说的**：`ingest.py` 的模块 docstring 说归档是通过*中央目录*检查的，「rather than by
decompressing it」，而 `_verify_entries` 实际会解压最多 256 MiB 去校验 checksum。

**现在**：已经不成立。`065301f` 把它拆成两件事说：目录里的**大小**读中央目录，不解压；**校验和**
必须解压才能验，所以那一步确实读归档，预算 `MAX_VERIFIED_BYTES`（256 MiB），预算之外的条目不解压，
其中的损坏不会被发现。

**怎么核对的**：读改写后的 docstring 与 `_verify_entries`；`tests/test_docstring_claims.py` 里
有一条检查在源码出现 `entry.read(` 时要求 docstring 提到 `MAX_VERIFIED_BYTES` 和 checksum，
并要求那句「rather than by decompressing it」消失。

#### M21 —— 拼写错误「a crashing or hangs engine」

**现在**：已经不成立。`065301f` 重写了 `tools/base.py` 的模块 docstring，那句话不在了。

#### M22 —— `method_status` 把构造器和方法名混在一个集合里

**清单说的**：`jadx/adapter.py` 的 `failed` 集合里构造器（按 Java 类名记）和普通方法名混在一起，
于是一个类名与某个失败方法同名的 APK，会让 `method_status(..., "<init>")` 对一个根本不存在的
构造器返回 `False`。

**现在**：已经不成立。`ab4e861`（*Make the decompiled flag mean what it says, and stop hiding
the CLI's cuts*）给 `ClassDecompilation` 加了独立的 `constructors` 集合，`method_status` 先查
`constructors`、再查 `decompiled`、最后查 `failed`。

**怎么核对的**：读 `ClassDecompilation.method_status` 的三段分支，以及
`tests/test_decompilation.py` 里那条「一个与自己的类同名的方法不是它的构造器」。

#### M24 —— `logger.remove()` 是全局的、永久的

**清单说的**：`androguard/adapter.py` 声称把 Androguard 的日志「在这里抑制，而不是全局配置」，
但 `logger.remove()` 恰恰是全局的、永久的。

**现在**：已经不成立。P2-005（`e2a32f4`，*Parse untrusted DEX in a worker, and leave the host's
logging alone*）换成了 `loguru_logger.disable(ANDROGUARD_LOGGER_NAME)` / `enable(...)`，按**模块名**
开关，进程的每一个 handler 都留在原处。注释还写明了这次替换的代价：开关是全局的、不是按线程的。

**怎么核对的**：读 `_suppress_androguard_logging`；`tests/test_androguard_isolation.py` 里有一条
测试读 loguru 自己的 handler 集合，比较分析前后。

### 仍为真 —— 改措辞（14 条）

#### M3 —— 证据表说「给类声明留了位置」，其实留不下

**现在仍然为真**：`core/evidence.py` 的 `MAX_EVIDENCE_CALLED_METHODS` 注释写着「The report's
evidence table shows 200 rows, so this leaves room for the class declarations in the same table」。
而 `MAX_EVIDENCE_CALLED_METHODS = 100` 加 `MAX_EVIDENCE_CLASSES = 500`（`core/pipeline.py`）是
600 条记录，报告的表只有 200 行（`reports/markdown.py` 的 `_MAX_EVIDENCE_ROWS`）。

**这是措辞，不是行为**：报告本身没有说谎 —— 它在表尾写明漏了多少条（`_truncation_note`）。
错的是注释对「留了位置」的承诺。

**改法**：注释改成说出两个上限与表的真实关系：两个上限合起来是 600 条记录对一张 200 行的表，
报告会说明自己漏了多少；这个上限的作用是**不让索引数据淹没结论**，而不是保证结论都放得下。

#### M7 —— 「后端是 subprocess 包装器，从不链接」与后来的「进程内解析」

**清单说的**：`tools/base.py` 写着「Backends are subprocess wrappers, never links.」，而
Androguard 是进程内库 —— adapter 自己承认是「the one exception to the subprocess rule」。

**现在的实际**：**清单这条已经被修好了一半，但又制造了一个方向相反的新说法。**

- `065301f` 把 `tools/base.py` 的 docstring 改成「引擎是被调用的，从不链接。Androguard 是例外
  —— 一个 Python 库，所以它在进程内运行，每一步都包起来」。这在当时是**准确**的。
- P2-005（`e2a32f4`）把 DEX 的解析搬进了 worker 进程：worker 通过 base 的 runner 启动
  （`tools/androguard/isolation.py` 的 `run_worker` 调用 `runner.run(...)`），结果是 JSON 而不是
  对象。`tools/androguard/adapter.py` 的 docstring 已经是新的说法了。
- **但 `tools/base.py` 没跟着改**，它到现在还写着 Androguard「runs in-process」。这已经不成立，
  而且比原来的说法更糟：原来的说法是「普遍断言掩盖了一个例外」，现在的说法是「一个具体的后端
  在一个具体的地方做了一件它不再做的事」。

**改法**：`tools/base.py` 的 docstring 改成：规则对所有后端成立 —— 每个后端都在自己的进程里
解析不可信输入；Androguard 是库而不是程序，所以没有工具可以 shell out，它改为在 worker 进程里
解析，worker 通过本类的 runner 启动，因此同一套超时与整棵树 kill 同样适用；跨过边界回来的是
数据，坏的 DEX 是 ToolError 而不是整次分析的终点。

**顺带**：锁住旧事实的测试也一并改了。`tests/test_docstring_claims.py` 里原来有一条断言
「进程内解析的后端集合 == {androguard}」—— 它锁的正是那个已经过时的结论。现在它问的是还能
问的问题：**有没有后端在服务自己的进程里解析 APK**（答案是没有），以及 Androguard 的工作是不是
交给了 worker（是）。

#### M8 —— 「超出就被当作失控后端」，其实是被静默截断

**现在仍然为真**：`tools/base.py` 的 `_DEFAULT_MAX_OUTPUT` 注释写着「Output that exceeds this is
treated as a runaway backend rather than a result.」，而代码里没有任何地方读这个常量；实际行为
是**静默截断**。

**这是措辞**：截断本身是对的（不截断，一个失控的后端就能把磁盘写满），要改的是那句对它的
描述。另外这一行还藏着第二句假话：它说「超出就被当作失控后端」，而代码从来没把谁「当作失控
后端」。

**改法**：注释改成说出实际的事 —— 这个常量**没有任何地方读**；一次运行真正适用的上限是
`Settings.tool_max_output_bytes`；超出时发生的事在 `Backend.run` 的 docstring 里写着；找到这个
数字的人不能把它误当成当下生效的上限，因为设置可以改而它不能。

#### M10 —— 基类说子类「implement extraction」，其实没有 `extract` 这回事

**现在仍然为真**：`Backend` 的 docstring 写着「Subclasses declare how to locate and probe their
tool, then implement extraction.」，而基类没有抽象的 `extract`；三个子类的读取方式各不相同
（jadx 的 `extract(apk_sha256, output_dir, outcome)`、androguard 的六元组、apktool 干脆没有
`extract`）。

**改法**：docstring 改成承认这一点 —— 子类实现 `resolve` 与 `version`，然后实现**读 APK 的那一步**；
没有统一的 `extract` 可实现，因为三个后端读的是 APK 里不同的东西，各写各的签名，强行统一只会
造出一个谁都不合适的形状。

#### M11 —— 「这里没有定义任何分析行为，所以两个接口不可能分叉」

**现在仍然为真**：`api/app.py` 的模块 docstring 写着「No analysis behaviour is defined here, so
the two interfaces cannot diverge.」，而 API 对已分析过的 APK **去重**（`app.py` 的 `/analyze`
里，已有 project 且不是 failed 就直接返回它），CLI **不去重**（每次重跑）。

**这是措辞**：分析本身确实只有一份实现；分叉的是「要不要为同一个 APK 再跑一次」这个**传输层
策略**。

**改法**：docstring 改成承认这个区别，并说清它是关于上传会不会引发工作的策略，不是关于一次
分析产出什么的差别 —— 但它确实是两个接口之间的一个差别，读者不该只能在代码里找到它。

#### M12 —— `LEAD` / `INSUFFICIENT` 是给模型输出用的闸门，可生产代码里没人产生它们

**现在仍然为真，但清单的说法要更新**：清单说 `src/` 里没有任何一处产生这两个等级。准确的说法是：

- `LEAD` 只能由 `EvidenceBuilder.add_claim` 产生（它的默认 level），而 **`src/` 里没有任何一处
  调用 `add_claim`** —— 所以当前树里报告的等级表恒为 `lead 0`；
- `INSUFFICIENT` 在 `src/` 里**完全没有**产生点，只有枚举定义和报告里的等级说明表。

**顺带发现的一处新的不一致**：`core/models.py` 的 `EvidenceLevel` docstring 写着
`add_claim`「does not offer the level in the first place」，而 `add_claim` 的签名里**有**
`level` 这个 keyword-only 参数（默认 `LEAD`），它自己的 docstring 也明说是为了让人能说
「连 lead 都不是」。这句话本身是错的，一并改掉。

**改法**：`EvidenceLevel` 的 docstring 改成：模型产生的记录不能是 `VERIFIED`（`Evidence` 会拒绝，
`add_claim` 也拒绝）；`LEAD` 是模型或启发式怀疑的东西，`INSUFFICIENT` 是两种证据都没有结论的
时候的状态；**分析本身不产生这两个等级中的任何一个** —— 它们是模型通过 `add_claim` 会写的等级，
在有人调用它之前，报告的等级表写的就是 `lead 0` 与 `insufficient 0`，而那说的是这次分析在这两个
等级上没有结论，不是说 APK 里没有可疑之处。

#### M14 —— 「方法上限」是按类检查的，报出来的数与实际索引量对不上

**现在仍然为真**：`tools/androguard/adapter.py` 的 `if len(methods) >= method_limit:` 在**类循环
之内**，所以一个类里的方法可以一次跨过上限；而消息里的「method limit N reached」说的是 N，
实际索引的却是 N 以上的数。

**改法**：消息改成把两个数都说出来 —— 上限是多少、实际索引了多少，并说明为什么这两个数可以
不等（上限是在类之间检查的，不是在类里面）。

#### M15 —— 「在 split 成组件**之前**就拒绝空段」

**现在仍然为真**：`core/paths.py` 的 `is_single_component` docstring 说
`class_to_relative_path` 「rejects a name with any empty segment before it splits into
components」，而代码是 `parts = class_name.split(".")` **先 split 再判空**（`if not parts or not
all(parts)`）。

行为等价，错的是对机制的描述。

**改法**：改成「把名字拆成组件，任何一个为空就拒绝这个名字」。

#### M16 —— 「Windows 也把组件名限在同样的 255」

**现在仍然为真**：`core/paths.py` 的 `MAX_COMPONENT_BYTES` 注释说 POSIX 限 255 字节，
「Windows caps it at the same number」。实际上 NTFS 限的是 **255 个 UTF-16 码元**，不是字节 ——
一个 200 字的中文类名是 600 个 UTF-8 字节，却只有 200 个码元。

**这是措辞，而且代码比注释更安全**：检查按字节做，而字节是两者中更严的一个（UTF-8 用到的
字节数从不少于 UTF-16 的码元数），所以过了这道检查的名字也一定在 Windows 的限制之内。

**改法**：注释改成把两个限制各自的**度量**说清楚，并说明为什么按字节检查是保守的，以及一个
在 Windows 上合法、在 POSIX 上非法的名字为什么仍然被拒（两个平台一条规则，比多放行的名字值钱）。

#### M17 —— 「同一个 APK 重新分析时，证据 id 是稳定的」

**现在仍然为真**：`core/evidence.py` 的模块 docstring 写着证据 id 在同一 APK 重新分析时稳定。
id 是按记录顺序分配的，所以**后端集合相同**时稳定；后端增减会让 `add_error` 之后的所有 id 位移。

**改法**：docstring 改成说清 id 是什么 —— 序列里的一个位置，`E-0007` 解析回数据库里的同一行；
在同一 APK 重新分析、且两次分析走到同一步骤时稳定；id 是一个位置而不是 APK 的属性；比较两次
运行的人要比较两次运行**做了什么**，不能只比较 APK。

#### M18 —— locator 里的字符串被截到 64 字符，两个同前缀的长串得到同一个 locator

**现在仍然为真**：`tools/androguard/adapter.py` 写 locator 时用 `value[:64]`，两个前 64 个字符
相同的字符串会得到同一个 locator，文档没有记载这件事。

**改法**：把截断写成常量 `MAX_LOCATOR_VALUE_CHARS = 64` 并说明它的含义 —— locator 命名的是
**值被找到的地方**，值本身在索引里是完整的，所以 locator 不必带着它的全部；它也不必唯一：
两个共享这 64 个字符的字符串共享一个 locator。

#### M19 —— 搜索索引里的字符串名被截到 200 字符，没有记载

**现在仍然为真**：`core/storage.py` 写搜索索引时用 `constant.value[:200]`。

**改法**：写成常量 `MAX_SEARCH_NAME_CHARS = 200` 并说明 —— 名字是这一行的标签，而行的 body
装的是完整的值，所以名字是搜索首先匹配的东西、body 才是把匹配做完的东西；截短名字是为了不把
一大段 base64 塞进一个每次搜索都要读的索引。

#### M20 —— `DEXATLAS_<BACKEND>_PATH` 是字面占位符，不是模式

**现在仍然为真**：`tools/base.py` 的 `path_env_var` 默认值是字面字符串
`"DEXATLAS_<BACKEND>_PATH"`。三个真实后端都覆盖了它（jadx `DEXATLAS_JADX_PATH`、apktool
`DEXATLAS_APKTOOL_JAR`、androguard 空串），但第四个后端若忘了覆盖，缺安装提示里就会印出这串
字面量。

**这一条我改了行为，不只改措辞**，理由是那句提示是一个**读者无法照做的假承诺**：
`DEXATLAS_<BACKEND>_PATH` 不是一个可设置的变量名，是一个模式的样子。留着它，就是把一个假
的环境变量名印给一个正在排查「后端为什么找不到」的人。

**改法**：`path_env_var` 的默认值改为空串，含义是「这个后端没有可指向的环境变量」，缺安装提示
因此保持沉默；有变量的后端覆盖成自己的名字（没有可填的模板 —— 让人去设置
`DEXATLAS_<BACKEND>_PATH` 等于什么都没告诉他）。注释把这个约定写出来。

**这是本次改动里唯一一处改变了公开输出的地方**：`Backend.missing_error()` 对**基类**实例的
detail 不再含环境变量名。三个真实后端各自覆盖了 `path_env_var`，它们的消息**一个字都没变**。
`tests/test_subprocess.py` 里原来断言基类的提示里含 `DEXATLAS_` 的那条测试随之改写：它现在
断言基类**不**提一个变量（提了就是提了一个不存在的），并新增一条断言覆盖了变量的后端**确实**
提到了它。

#### M23 —— 「这些表会折叠重复键」对 xrefs 与 strings 不成立

**现在仍然为真**：`core/storage.py` 的 `SymbolCounts` docstring 说「The tables collapse duplicate
keys」，`save_symbols` 的 docstring 说「the symbol tables key on the symbol」。

- `classes` / `methods` / `fields` 的主键确实是符号，重复的键会被折叠；
- `call_sites` 的主键带 `instruction_offset`，所以同一个 caller→callee 的两次调用是**两行**；
- `strings` **根本没有主键**，同一个字符串在两个方法里被用到就是两行。

**改法**：两处 docstring 都改成点名哪几张表折叠、哪几张不折叠，并说出不折叠的理由（call site
是**地方**，string constant 是**用处**），以及为什么键要这么设计 —— `call_sites` 的表注释本来
就写着这件事，strings 表没有，而这一条正是 issue list 点名的「无主键是有意的，但代码注释里
没写」。

### 仍为真 —— 改行为（2 条）

这两条各配一个回归测试，**去掉修复就变红**。证明见下一节。

#### M9 —— 后端的 stdout 被裁掉时，永远没有人被告知

**清单说的**：`tools/base.py` 的 `_decode` 里有
`if len(raw) > limit: logger.warning("output truncated from %d to %d bytes")`，但这个分支
**不可达**：`_read_capped` 先 `truncate(limit)` 再读，`len(raw) <= limit` 恒成立。

**现在的实际**：仍然为真，而且我确认了清单的判断是对的 —— `_read_capped` 确实先截断再读，
`_decode` 里的比较永远为假。

**这不只是措辞**：后端 stdout 被裁掉时，没有任何地方说过这件事。报告里的一切都像是完整的。

**改法**：

1. `_read_capped` 现在返回 `(读到的字节, 文件原本的大小)` —— 只有还知道原大小的地方才知道
   自己截掉了东西。
2. `Backend.run` 用它算出被截断的流，写进 `ToolOutcome` 的新字段 `truncated`，并打一条
   `logger.warning`。
3. `_decode` 里那个不可达分支删掉 —— 它现在的 docstring 说清了为什么截断不在那里做。
4. 新增 `truncation_error(tool, streams, limit)`，把截断变成一个 `ToolError`
   （`OUTPUT_TRUNCATED`），**并把上限的值写进消息与 detail**，因为一个读者无法核实的上限
   只是一句声称。
5. `pipeline.py` 的 `_run_apktool` 与 `_run_jadx` 把它记到 project 上，于是报告的
   「Backend errors」一节会说：某后端的输出被截了，截了多少，被留下的只是头一段。

#### M13 —— 反编译器什么都没产出时，报告完全不提

**清单说的**：`pipeline.py` 的 `_record_decompilation` 里 `if not status: return`，所以 JADX 什么都没
产出时报告一个字都不说，而报告的 Tool versions 行照旧列着 `jadx 1.5.2`。

**现在的实际**：仍然为真。

**改法**：`status` 为空时记一条 evidence —— 「jadx produced no Java for any class」，kind 是
`OBSERVATION`，level 是 `VERIFIED`（空的输出树是一个确定的事实），citation 指向 JADX 自己的
输出目录。反编译器**失败**时不重复记：失败已经由 `add_error` 记成了一条失败，读者被告知
「jadx 没完成」就不需要再被告知「它也没产出」。

---

## 两处行为改动的「去掉修复就变红」证明

### M9

新增 `tests/test_output_truncation.py`。证明分两步做的。

**第一步，把行为改回去（保留接口），只让检测消失**：

```python
# tools/base.py, 旧行为
truncated = ()
```

```bash
uv run --no-sync pytest tests/test_output_truncation.py tests/test_decompiler_absence.py -q
# FAILED tests/test_output_truncation.py::test_a_backend_that_writes_too_much_says_that_it_did
# 4 failed, 7 passed
```

**第二步，把整个 `src/` 还原到 `HEAD`（本分支的改动之前）**：

```bash
git checkout -- src/
uv run --no-sync pytest tests/test_output_truncation.py tests/test_decompiler_absence.py -q
# FAILED tests/test_output_truncation.py::test_a_backend_that_writes_too_much_says_that_it_did
# FAILED tests/test_output_truncation.py::test_an_output_that_fits_is_not_reported_as_cut
# FAILED tests/test_output_truncation.py::test_a_truncated_output_is_recorded_on_the_project
# FAILED tests/test_output_truncation.py::test_the_cap_is_named_with_its_value
# FAILED tests/test_decompiler_absence.py::test_a_decompiler_that_produced_nothing_is_recorded
# FAILED tests/test_decompiler_absence.py::test_the_report_says_the_decompiler_produced_nothing
# FAILED tests/test_decompiler_absence.py::test_the_json_report_carries_the_fact
# 7 failed, 4 passed
```

**第三步，把改动放回去**：

```bash
uv run --no-sync pytest tests/test_output_truncation.py tests/test_decompiler_absence.py -q
# 11 passed
```

### M13

同一个文件 `tests/test_decompiler_absence.py` 里的六个测试，覆盖：记录进了证据、报告里说了、
工具版本仍然照列、JSON 报告里也有、反编译器**失败**时不重复记、反编译器**产出了东西**时不误报。

同样用上面两步还原与恢复，红 → 绿。

---

## 留在集成者那里的事

本分支只动 `src/dexatlas/`、`tests/` 与这份新文件，**没有动任何已有文档**。因此下面几件事
是合并后一次性该做的，本分支不做：

1. **文档里的 `file:line` 引用漂移。** 本分支改了 `src/` 下八个文件的行数，
   `scripts/check-doc-citations.py` 会报出漂移（本次实测 26 处）。这些引用在
   `docs/analysis-provenance.md`、`docs/reports/phase1-execution-report.md`、
   `docs/benchmarks/large-apk.md` 三份文档里，由重推脚本一次性重新推导。
   **不要手改** —— 手改会让重推脚本把已经推过的数字再推一遍。
2. **执行报告里的数字。** 本分支新增了 2 个测试文件、11 个测试，也改了 `src/` 的行数，
   所以 `docs/reports/phase1-execution-report.md` 里的测试数、覆盖率与测试文件清单都过期了。
   这些数字由 `scripts/refresh-report-figures.py` 生成，合并后重跑一次即可。
   注意：**这个分支的基线上就已经有 1 个失败** ——
   `tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code`
   在本分支动手之前就是红的（该报告的数字没有随 P2-002 一起刷新）。
3. **`CHANGELOG.md`** 留给集成者写。

## 本分支留下的已知残留

- **`_DEFAULT_MAX_OUTPUT` 仍然是零引用的死常量。** M8 只让它的注释说实话了；把常量本身删掉
  是 issue list 第 9 节（F8）那条的范围，不在本次窗口内。**没有动它。**
- **`_record_decompilation` 新增的 `decompiler_failed` 参数是 keyword-only 且有默认值**，
  现有调用方不需要改。
