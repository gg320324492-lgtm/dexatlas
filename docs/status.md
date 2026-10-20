# DexAtlas 当前状态

**最后更新：** 2026-10-20 · **对应版本：** v0.1.3 之后的开发状态（尚未发布）

这份文档回答两个问题：**现在在哪**，**还剩什么**。

- 「交付了什么」和「怎么交付的」在[执行报告](reports/phase1-execution-report.md)里
- 「每条结论由谁支撑、怎么自己核对」在[分析覆盖度与证据来源](analysis-provenance.md)里
- 「三阶段的计划」在[路线图](roadmap/ROADMAP.md)里
- 每次发布的具体内容在 [releases/](releases/) 里

---

## 1. 快照

| | |
|---|---|
| 已发布版本 | v0.1.0 · v0.1.1 · v0.1.2 · **v0.1.3** |
| 测试 | <!--fig:tests.total-->576<!--/fig--> 个（<!--fig:tests.fast-->458<!--/fig--> 快 + <!--fig:tests.slow-->118<!--/fig--> 集成） |
| 一方代码覆盖率 | <!--fig:coverage.pct-->94.5%<!--/fig--> |
| 类型检查 / lint | `mypy` strict、`ruff` lint + format，均通过 |
| CI | 6 个 job 全绿：Python 3.12 / 3.13 / 部分后端 / Docker / 依赖审计 / Lint |

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

**尚未进行的是源码审核。** 按路线图约定的评审机制，Phase 1 的源码审核是
Phase 2 的准入条件——**Phase 2 的任务清单应当在审核结论之后写**，
而不是照搬原计划（原计划的 Agent 架构设想建立在「代码不存在」的假设上）。

审核时建议先看执行报告的**第 3 节**：那里记录了十五个开发过程中发现并修复的
真实缺陷（3.1 ~ 3.15），其中九类属于同一个模式——「宣称完成了、实际没有完成」，
以及它们各自是怎么被发现的。

这一轮又在这个模式上添了两类（见第 6 节），而它们是**产品**的缺陷，不是文档的：
一个是触到上限就静默截断、项目照样报「完成」，一个是后端版本号每个符号查一次。
两个都要**真的走到那个边界**才会露出来——所以这九个提交里最值得看的
不是修了什么，而是怎么发现边界没被走到过。

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

---

### 这一轮关掉的

| 原来开着 | 现在 |
|---|---|
| 文档与 issue 的发布状态 | 23 处过期陈述改完；issue #1 留了评论（正文没动）；`scripts/check-version-claims.py` 现在自动查这一类 |
| 资源完全没有覆盖 | 资源表进索引，`dexatlas resources` 和 `GET /projects/{id}/resources` 都能查 |
| Smali 回退不附带 provenance | `class_source_document` / `method_source_document` 返回带出处的文档，CLI 与 API 都说得出是 Java 还是 Smali |
| 大型 APK 的性能压测 | 基准跑完了；**顺带找出三个真缺陷并修掉** |

那三个缺陷值得单独记一句，因为它们是**产品**的缺陷，不是文档的：

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

仓库里**不含**任何第三方 APK、DEX、so 或 jar。分析样本只有两个来源：

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

# 两个外部后端都不在：去掉路径配置，并让 java 不在 PATH 上
env -u DEXATLAS_JADX_PATH -u DEXATLAS_APKTOOL_JAR uv run pytest

# 只装 Apktool
env -u DEXATLAS_JADX_PATH uv run pytest
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

DexAtlas 出现过十一类「宣称完成了、实际没有完成」：

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

共同点有两个：

1. **它们都不让测试变红。** 绿色的测试套件证明不了「这个功能能用」，
   只证明「被断言的那些行为成立」。
2. **它们都藏在真实流程之外。** 手写的理想输入、被跳过的 fixture、
   没被拉取的样本、改写过的清单——只要不去跑一遍真实的东西，就看不见。

最后两类是 v0.1.3 之后新出现的，而且都指向同一件事：**边界没被走到过**。
上限没被触到，所以「触顶之后会怎样」只能是推测；一个从没被量过的数字只能靠抄，
而抄来的数字迟早和量出来的不一样。

所以这个项目对自己的要求是：**不是「测试通过」，是「跑过一遍并且对得上」**。
新加一条测试时值得问两句——它用的是**真实流程里的输入**，还是我手写的那个？
它有没有真的走到那个边界？
