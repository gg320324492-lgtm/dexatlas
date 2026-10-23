# DexAtlas 当前状态

**最后更新：** 2026-10-21 · **对应版本：** v0.1.3 之后的开发状态（尚未发布）

这份文档回答两个问题：**现在在哪**，**还剩什么**。

- 「交付了什么」和「怎么交付的」在[执行报告](reports/phase1-execution-report.md)里
- 「每条结论由谁支撑、怎么自己核对」在[分析覆盖度与证据来源](analysis-provenance.md)里
- 「这个项目现在成熟到什么程度」在[成熟度评估](reports/phase1-maturity-assessment.md)里
- 「评审挖出来、还没修的」在[Phase 2 issue 清单](reports/phase2-issue-list.md)里
- 「三阶段的计划」在[路线图](roadmap/ROADMAP.md)里
- 每次发布的具体内容在 [releases/](releases/) 里

---

## 1. 快照

| | |
|---|---|
| 已发布版本 | v0.1.0 · v0.1.1 · v0.1.2 · **v0.1.3** |
| 测试 | <!--fig:tests.total-->972<!--/fig--> 个（<!--fig:tests.fast-->849<!--/fig--> 快 + <!--fig:tests.slow-->123<!--/fig--> 集成） |
| 一方代码覆盖率 | <!--fig:coverage.pct-->94.1%<!--/fig--> |
| 类型检查 / lint | `mypy` strict、`ruff` lint + format，均通过 |
| CI | 6 个 job 全绿：Python 3.12 / 3.13 / 部分后端 / Docker / 依赖审计 / Lint |
| 成熟度评估 | 修复前的基线 **5.50 / 10**（六个加权维度，见[评估报告](reports/phase1-maturity-assessment.md)）；今天的分数要重跑才有 |

**CI 的六个 job 各自覆盖一种配置**，不是重复：

| Job | 覆盖什么 |
|---|---|
| Tests (Python 3.12) | 全部后端 |
| Tests (Python 3.13) | **两个外部后端都不在**——JADX 和 Apktool 需要 Java，Androguard 是 Python 包，还在 |
| Tests (Apktool only, no JADX) | **Apktool 在、JADX 不在**——Smali 回退存在的理由 |
| Docker image builds | 镜像里三个后端真的能跑 |
| Dependency audit | 锁文件的已知漏洞 |
| Lint and format | ruff、mypy、**actionlint**（workflow 文件本身）、**版本状态陈述检查** |

第三个 job 存在的原因值得记一句：它曾经**从未在 CI 上跑过**，
于是两个假定 JADX 已安装的测试一直是绿的，而 Smali 回退——那个「JADX 不可用时
仍能读出代码」的机制——实际上没被测过。

---

## 2. 已发布

| Tag | 日期 | 主题 |
|---|---|---|
| `v0.1.0` | 2026-10-14 | Functional Foundation — 可用的静态分析流水线 |
| `v0.1.1` | 2026-10-19 | Foundation Hardening — 修了从未生效的 Smali 回退 |
| `v0.1.2` | 2026-10-20 | The Acceptance Checklist, Actually Met — 5 个自建样本 + 演示视频 |
| `v0.1.3` | 2026-10-20 | Evidence That Points Back — 交叉引用成为证据、locator 可移植、文档自校验 |

v0.1.1 到 v0.1.3 修的是同一类问题的三个实例：**一个看起来像成功的缺陷**。
详见执行报告第 3 节。

---

## 3. 阶段验收的状态

**原计划书 1.4 节的 8 项验收清单已全部达成。**
[路线图的 1.4 退出清单](roadmap/ROADMAP.md)用的是原计划书的原话，
每一项后面都能指到实际交付物。

**Phase 1 已于 2026-10-21 验收通过**，基准是固定的提交
`a1e81ce8ae262b84fa06bc5a3afb995fd0238660`（milestone tag `phase1-acceptance-2026-10-21`）。
**那不是 v0.1.3**——它比 v0.1.3 领先 76 个提交，评审做出的东西**一个都还没发布**。

按路线图约定的评审机制，Phase 1 的源码审核是 Phase 2 的准入条件，
**Phase 2 的任务清单在审核结论之后写**，而不是照搬原计划
（原计划的 Agent 架构设想建立在「代码不存在」的假设上）。

评审协议的五步，全部走完：

| 步骤 | 状态 |
|---|---|
| 1. 版本提交 | 完成：四个 tag（v0.1.0 ~ v0.1.3）、仓库链接、可复现命令 |
| 2. 架构与代码审核 | 完成：三个并行审核（核心实现 / 接口与安全边界 / 测试可靠性），共 44 条发现，**每一条都在新基线上逐条复核过** |
| 3. 成熟度评估 | 完成：[成熟度评估](reports/phase1-maturity-assessment.md)，六个加权维度。**5.50 / 10 是修复前的基线**，不是这棵树的当前分数 |
| 4. 评审报告 | 完成：[评审报告](reports/phase1-review-report.md) |
| 5. 重新规划下一阶段 | 完成：[Phase 2 计划](roadmap/phase2-plan.md)（M0 ~ M4）+ [Phase 2 issue 清单](reports/phase2-issue-list.md) |

**验收记录**在[这里](releases/phase1-acceptance-2026-10-21.md)——
它同时说了验收**没有**声称什么。

审核用了一个方法值得记下来：**每个审核 agent 都被要求去破坏实现，看测试会不会红**。
44 条发现里有相当一部分是「删掉这段代码，测试全绿」——也就是说，
**这些缺陷不是被测试发现的，是被「测试没发现」这件事本身暴露的**。

两轮审核一共挖出 **21 类**「宣称完成了、实际没有完成」（见第 6 节）。
审核时建议先看执行报告的**第 3 节**：那里记录了十五个开发过程中发现并修复的
真实缺陷（3.1 ~ 3.15），其中九类属于同一个模式，以及它们各自是怎么被发现的。

---

## 4. 还剩什么

这一版关掉了原来五项里的四项。先说还开着的，再说这一轮新发现的。

### 4.1 真实加固 APK

`obfuscated-app` 覆盖了短类名和短方法名，但它是**手写的**混淆，
不是有控制流混淆的真实加固产物。真实的加固 APK 需要外部样本。

### 4.2 布局里硬编码的文本仍然搜不到

资源表现在读了：`res/values*/` 里的文本声明（`<string>`、
`<string-array>` 的每一项、`<plurals>` 的每一项）进了索引，
`dexatlas search` 搜得到 `DexAtlas Demo`，每一条都指回声明它的那个文件。

但布局 XML 里 `android:text="..."` 这种**硬编码**的文本仍然进不了索引。
这是这一轮明确留下的缺口，不是遗漏。`@string/app_name` 这种**引用**
也不在索引里——资源 ID 的图是另一个问题。

### 4.3 压测没有覆盖的部分

[大型 APK 基准](benchmarks/large-apk.md) 记了它测了什么，也记了**没测什么**：
真实的 APK（不是合成的）、JADX 与 Apktool 在规模下的表现、
native 库、内存。这些要等下一个手里有真实样本的人。

### 4.4 被截断的运行，退出码仍然是 0

索引触到上限时，项目状态仍是 `completed`——部分成功不是失败——
错误记在 `project.errors` 里，报告有「Backend errors」段，CLI 也会把它
当警告打出来。**但 CLI 的退出码是 0**：只看退出码的调用方分不出
「被截断的运行」和「完整的运行」。要看项目记录才知道。

### 4.5 阶段验收挖出来的、这一轮修掉的

评审（协议第 2 步，三份审核共 44 条发现）挖出来的产品缺陷，
按严重程度排：

| 缺陷 | 严重级 | 状态 |
|---|---|---|
| 上传的文件名由客户端决定 → 一个项目的符号表装上另一个 APK 的类 | **阻断** | 已修 |
| 默认配置下 JADX 的 Java 反编译完全失效，报告照旧写着 jadx 的版本 | **阻断** | 已修 |
| `PRAGMA journal_mode = WAL` 在每次事务里——一次纯读也在写库，并发分析直接 500 | 重要 | 已修 |
| `analyze()` 没有 try/except：异常穿出去，项目停在 `running`、`errors=[]`，再传同一个 APK 永不重跑 | 重要 | 已修 |
| `GET /health` 每个请求都开数据库写锁——探活的服务把自己搞挂 | 重要 | 已修 |
| 证据的每环都自洽却指向错的东西（上传覆盖那一类） | 重要 | 已修 |
| `cross_references_with_evidence` 数的是被调方法数，而 `cross_references` 数的是边数 | 重要 | 已修 |
| 超过 200 个类时，反编译覆盖率那条证据被挤出报告的证据表 | 重要 | 已修 |
| API 导出的报告写「Analysis time 0.0s」，与 CLI 导出的同一份不一致 | 中 | 已修 |
| `xrefs` 表没有主键，同一条调用边可以写进多行 | 重要 | 见 [Phase 2 issue 清单](reports/phase2-issue-list.md) |
| workspace 并发不安全：同一个 APK 的两次分析共用一个目录 | 重要 | 见 Phase 2 清单 |
| `EvidenceKind.CODE_LOCATED` / `BEHAVIOUR`、`EvidenceLevel.LEAD` / `INSUFFICIENT` 没有任何生产者 | 中 | 见 Phase 2 清单 |

**「已修」的每一条都配一个在旧代码上会红的测试**——不是「测试通过」，
是「把修复撤掉，测试必须红」。这一轮共验证了 21 处破坏实验。

三条阻断级里最值得记的是第一条：项目声称的哈希、标识符、每条 provenance
**全都是它自己的**，而符号表里装的是**另一个 APK 的类**。
**证据链的每一环都自洽，指向的却是错的东西**——读者核对哈希会通过，
因为哈希确实是它的。

### 4.6 Phase 2 正在做的事

M0 有五条，每条带验收标准，都在
[Phase 2 计划](roadmap/phase2-plan.md)里。

**P2-001：让方法解析对重载安全 —— 已交付。**

原来一个方法**只按名字**解析：两个重载 `sign(String)` 和 `sign(String, String)`，
请求 `sign` 拿到哪一个取决于源码里的顺序，**不是签名**。

**为什么它是第一件事**：MCP 工具会把这个结果直接返回给 agent，
而 agent 会把它当证据引用——**一个被引用错了的方法，比没有方法更糟**。
所以它排在 MCP 之前。

**索引里其实存着能区分重载的信息**（`methods.descriptor`），
只是查询时没用；而 JADX 适配器的正则**已经抓了参数类型**，
只是解析结果里把它丢掉了。

修法：按完整 DEX descriptor 解析；**歧义要明说，不能猜**——
名字对应多个重载而调用方没指明时，明确报告有哪些候选、需要什么才能确定地选一个。
命令行用**自己的退出码**（4），API 用 **409**，
「没有源码」「请求不对」「分析失败」这几个码仍然各说各的。

**P2-002 / P2-004 / P2-005 在并行做**：分别是 `AnalysisRun` 与事务化结果、
已验证证据的不变量、运行时隔离。三条的文件归属不重叠，各走各的分支，各自带验收标准。

剩下的 **P2-003（CallSite / CallEdge 语义）排在 P2-002 之后**——
它要动同一张 `xrefs` 表，而那张表上还开着一条旧缺陷
（`xrefs` 没有主键，同一条调用边可以写进多行，见上表）。

### 4.7 这一轮关掉的

| 原来开着 | 现在 |
|---|---|
| 文档与 issue 的发布状态 | 23 处过期陈述改完；issue #1 留了评论（正文没动）；`scripts/check-version-claims.py` 现在自动查这一类 |
| 资源完全没有覆盖 | 资源表进索引，`dexatlas resources` 和 `GET /projects/{id}/resources` 都能查 |
| Smali 回退不附带 provenance | `class_source_document` / `method_source_document` 返回带出处的文档，CLI 与 API 都说得出是 Java 还是 Smali |
| 大型 APK 的性能压测 | 基准跑完了；**顺带找出三个真缺陷并修掉** |
| 文档里的引用会漂移没人管 | `scripts/check-doc-citations.py` 现在真的校验 94 处引用里的 93 处（原来只查 18 处） |
| 版本声明检查器在自己的目标场景下失效 | base 提交用它自己的事实重算，判据从「数量」改成「身份」 |
| 报告里的数字从不重新测量 | 数字改成真测：新增收集的测试数 + coverage 自己解析出的语句数；指纹覆盖 `tests/` 和工具配置 |

那一轮找出三个真缺陷值得单独记一句，因为它们是**产品**的缺陷，不是文档的：

1. **版本号每个符号查一次。** 每个类、方法、字段、交叉引用都带一条 provenance，
   每条都要问一次后端版本号，而那次查询要扫一遍已安装的发行版。
   实测：12,000 个方法的一次运行里 82 秒有 80 秒花在这上面。
2. **触到上限就静默截断，项目照样报「完成」。** 索引少了几千个方法，
   `project.errors` 是空的，报告里的数字和数据库的行数**完全一致**——
   因为它们忠实地记录了一个被砍短的索引。现在触顶会记 `output_truncated`。
3. **三个上限里有两个是按 DEX 文件算的。** 四个 DEX 的 APK 拿到四倍额度——
   恰好是最需要封顶的那种 APK 反而拿到最多。现在一份预算一个 APK。

三个都不是「测试变红」能发现的：它们都要**真的走到那个边界**才会露出来。

---

## 5. 动手之前要知道的几件事

### 报告里的数字是自动生成的

文档里的测试数、覆盖率、快慢分层数都带 `<!--fig:...-->` 标记，
由 `scripts/refresh-report-figures.py` 测量并写回。

**不要手改那些数字。** 改完代码跑一次脚本即可：

```bash
uv sync --extra demo          # 完整测量需要 Pillow
uv run python scripts/refresh-report-figures.py
uv run python scripts/refresh-report-figures.py --check   # 只比对不写入
```

脚本在一次运行内收敛，并且**能区分「报告过期」和「代码坏了」**——
前者会刷新，后者会点名失败的测试并拒绝写回。

### 文档的行号引用会漂

`scripts/check-doc-citations.py` 校验文档里每一处 `文件:行号` 引用
是否仍指向它说的东西。它会打印校验了多少处、漂移了几处——**那个数不要手抄到这里**，
抄的数会漂（这份文档上一版写着 82，下一版就是别的数了）。改了 `src/` 之后跑一次：

```bash
uv run python scripts/check-doc-citations.py
```

### 安全边界

仓库里**不含**任何第三方分析产物——APK、DEX、so、jar、zip、obb、vdex 这些后缀
一个都没有。分析样本只有两个来源：

- **自建** —— `examples/` 下的 5 个，每个的 smali 源码就在旁边，
  `scripts/build-test-apks.sh` 能重建
- **拉取** —— `scripts/fetch-fixtures.sh` 取 androguard 的 Apache-2.0 测试数据

这个边界由 `tests/test_docs.py` 里的测试守着：仓库里每个 APK 都必须有源码在旁边。

### 后端在 CI 上的三种配置

CI 里跑的是三种**不同**的组合——JADX 和 Apktool 是外部程序，Androguard 是
Python 包，所以「装没装后端」要分开说：

| 配置 | JADX | Apktool | Androguard | 对应 job |
|---|---|---|---|---|
| 全装 | 有 | 有 | 有 | Tests (Python 3.12) |
| **两个外部后端都不在** | 无（没 Java） | 无（没 Java） | **有** | Tests (Python 3.13) |
| 只装 Apktool | 无 | 有 | 有 | Tests (Apktool only, no JADX) |

**注意第二行**：3.13 那个 job 装的是 `--extra analysis`，而 `analysis` extra
装的就是 Androguard——它是 Python 包，不需要 Java。所以那个 job 不是
「一个后端都不装」，而是「两个外部后端都装不了」。三种配置都要跑。

本地复现：

```bash
# 全装（默认）
uv run pytest

# 两个外部后端都不在
DEXATLAS_JADX_PATH="" DEXATLAS_APKTOOL_JAR="" uv run pytest

# 只装 Apktool
DEXATLAS_JADX_PATH="" uv run pytest
```

**注意是空值，不是 `env -u`。** 后端路径的配置是三态的：
`None`（没设）表示**去 PATH 上找**，空字符串表示**显式禁用**，
一个存在的路径表示**用它**。`env -u DEXATLAS_JADX_PATH` 只是「没设」，
于是它回退到 PATH 查找——而 jadx 的 `bin` 通常就在 PATH 上，
**后端并没有被禁用**。要禁用，得给它空值：

```console
$ DEXATLAS_JADX_PATH="" uv run dexatlas backends
│ jadx       │ not installed │ —       │
│ apktool    │     available │ 2.11.1  │
│ androguard │     available │ 4.1.4   │
```

**这三个配置都要跑。** 只跑默认那一种，正是两个假定 JADX 已安装的测试
长期未被发现的原因。

### 本机环境

```bash
export DEXATLAS_APKTOOL_JAR="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/apktool.jar"
export DEXATLAS_JADX_PATH="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin/jadx.bat"
export PATH="/c/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin:$PATH"
```

GitHub 网络需要代理 `http://127.0.0.1:7897`。

---

## 6. 这个项目反复出现的缺陷类型

写在这里，是因为**它比任何一条具体清单都更有用**。

DexAtlas 出现过二十一类「宣称完成了、实际没有完成」：

| 缺陷 | 它怎么藏起来的 |
|---|---|
| 交叉引用的 id 带空格，查询永远返回空 | 报告显示 6033 条交叉引用，一切健康 |
| 方法表和交叉引用表的 id 拼写不同 | 从 `dexatlas methods` 复制 id 去查 `xrefs` 查不到 |
| Smali 回退从未生效 | 报告「No source」，看起来像 APK 没代码 |
| 集成测试的 fixture 从未被拉取 | 本机全过、CI 全跳过，**两边都绿** |
| 退出清单被改写成更容易打勾的措辞 | 「5 个自建 APK」写成「verified against test APKs」 |
| 报告里的方法数和实际行数不一致 | 报告说 14 个方法，查询只列得出 11 个 |
| 空路径不能禁用后端 | 旧测试**因为错误的原因**而通过 |
| 文档说 A、代码是 B（9 处） | 没有人核对过 |
| workflow 用了 GitHub 不接受的写法 | run 被创建后失败，**0 个 job 被调度** |
| 手写的数字和自动生成的数字对不上（4 处） | 报告的数字是脚本量的，发布说明和徽章的数字是人抄的——两边从没被放在一起看过 |
| 触到上限就静默截断，项目照样报「完成」 | 样本最大不到 3 KB，从没触到过 5,000,000 指令的上限；截断只打了一条 warning |
| 同一个相对路径被解释成两个位置 | 默认工作区是相对的，JADX 的 `--output-dir` 和 `cwd` 都拿到它——源码写进了双重嵌套目录，索引找不到，**报告照旧写着 jadx 的版本** |
| 默认配置从来没被测过 | `tests/conftest.py` 的工作区永远是绝对路径，所以上面那条躲过了整套测试 |
| 上传的文件名由客户端决定 | 两个 APK 用同一个文件名上传，第二个覆盖第一个，而分析在后台读的是那个路径——**一个项目的符号表装上了另一个 APK 的类** |
| 一次纯读也在写数据库 | `PRAGMA journal_mode = WAL` 在每次事务里，SQLite 只允许一个写者——一次 `GET` 就能把并发的分析锁在门外 |
| 异常穿出去，项目停在 `running` | `analyze()` 没有 try/except，数据库里的项目行是 `status='running'`、`errors=[]`——**没有任何地方说这次分析失败过**，再传同一个 APK 命中已有哈希，永远不重跑 |
| 证据的每一环都自洽，却指向错的东西 | 上面那条上传覆盖：哈希对、项目 id 对、provenance 对——**只有类不属于这个 APK**，核对哈希的人看不出来 |
| 从数据库重建结果时丢了字段 | API 导出的报告写「Analysis time 0.0s」，CLI 导出的同一份是真实耗时——`_rebuild_result` 没有重建它 |
| 「机制」其实只是约定 | 证据等级在 docstring 里被写成机制，实际没有 validator——`BEHAVIOUR` 记成 `VERIFIED`，报告就渲染成「由分析工具确定性确立」 |
| 数字只跟旁边的记录自比 | 把记录里的 `passed` 和图里的数字一起改成 999，没有任何新失败——指纹只哈希 `src/`，加测试都不算过期 |
| 同样的数字，不同的集合 | 「跳过 12 个」和「跳过的是这 12 个」不是一回事——一次不完整的测量可以被当成完整的写进报告 |

共同点有三个：

1. **它们都不让测试变红。** 绿色的测试套件证明不了「这个功能能用」，
   只证明「被断言的那些行为成立」。
2. **它们都藏在真实流程之外。** 手写的理想输入、被跳过的 fixture、
   没被拉取的样本、改写过的清单、**没人用过的默认配置**——只要不去跑一遍真实的东西，就看不见。
3. **它们都在「自洽」里藏身。** 最难查的那几条，单独看每一环都对：
   哈希对、id 对、provenance 对、数字对得上记录。**只有把它们放回真实的流程里，
   对照另一个东西看，才会看出它们指错了。**

最后十类是 v0.1.3 之后新出现的，而且都指向同一件事：**边界没被走到过**。
上限没被触到，所以「触顶之后会怎样」只能是推测；一个从没被量过的数字只能靠抄，
而抄来的数字迟早和量出来的不一样；一个从没被用过的默认配置，只能靠猜。

所以这个项目对自己的要求是：**不是「测试通过」，是「跑过一遍并且对得上」**。
新加一条测试时值得问两句——它用的是**真实流程里的输入**，还是我手写的那个？
它有没有真的走到那个边界？
