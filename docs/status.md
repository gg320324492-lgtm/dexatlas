# DexAtlas 当前状态

**最后更新：** 2026-10-20 · **对应提交：** `622a8c6`（v0.1.3）

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
| 测试 | <!--fig:tests.total-->497<!--/fig--> 个（<!--fig:tests.fast-->400<!--/fig--> 快 + <!--fig:tests.slow-->97<!--/fig--> 集成） |
| 一方代码覆盖率 | <!--fig:coverage.pct-->94.0%<!--/fig--> |
| 类型检查 / lint | `mypy` strict、`ruff` lint + format，均通过 |
| CI | 6 个 job 全绿：Python 3.12 / 3.13 / 部分后端 / Docker / 依赖审计 / Lint |

**CI 的六个 job 各自覆盖一种配置**，不是重复：

| Job | 覆盖什么 |
|---|---|
| Tests (Python 3.12) | 全部后端 |
| Tests (Python 3.13) | **一个后端都不装** |
| Tests (Apktool only, no JADX) | **Apktool 在、JADX 不在**——Smali 回退存在的理由 |
| Docker image builds | 镜像里三个后端真的能跑 |
| Dependency audit | 锁文件的已知漏洞 |
| Lint and format | ruff、mypy、**actionlint**（workflow 文件本身） |

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
而不是照搬原计划（���计划的 Agent 架构设想建立在「代码不存在」的假设上）。

审核时建议先看执行报告的**第 3 节**：那里记录了十五个开发过程中发现并修复的
真实缺陷（3.1 ~ 3.15），其中九类属于同一个模式——「宣称完成了、实际没有完成」，
以及它们各自是怎么被发现的。

---

## 4. 还剩什么

### 4.1 文档与 issue 的发布状态（进行中）

v0.1.3 发布后，仓库里还有大约六处陈述停留在发布之前：
报告开头和 3.11~3.15 节的标题写着「待发布」「在 v0.1.2 之后」，
[分析覆盖度文档](analysis-provenance.md)第 6 节开头说「已修的那些都还没有发布」。

GitHub issue #1 的清单更旧：它写着「`v0.1.0` release: Not started」「88%」，
而它早已关闭。**关闭的历史不该改写**，处理方式是留一条评论说明现状。

这一类没有自动检查。`scripts/check-doc-citations.py` 校验文档里的 `文件:行号`
引用是否仍指向它说的东西，但**校验不了版本状态陈述**——那不是行号。

### 4.2 资源完全没有覆盖

Apktool 会把 `res/` 解码到工作区，`src/` 里却没有任何代码读它。
可以直接看到后果：demo-app 的资源字符串 `'DexAtlas Demo'`
（来自 `res/values/strings.xml`）**不在字符串索引里**。

这是三个后端共同的盲区，也是「证据能指回原处」目前最大的缺口。

### 4.3 Smali 回退不附带 provenance

`class_source` 返回 Smali 而不是 Java 时，调用方**无法从返回值判断**
这是 Apktool 的输出——只能靠「工作区里有没有 jadx 目录」间接推断。

与 v0.1.3 刚建立的「证据能指回原处」直接相关：现在方法、字符串、
交叉引用都能指回原处，唯独 Smali 这条路径不能。

### 4.4 大型 APK 的性能压测

现有样本最大不到 3 KB。索引性能和 `MAX_INSTRUCTION_LIMIT`
**从未被真实压过**——大 APK 上会发生什么，目前只有推测。

### 4.5 真实加固 APK

`obfuscated-app` 覆盖了短类名和短方法名，但它是**手写的**混淆，
不是有控制流混淆的真实加固产物。真实的加固 APK 需要外部样本。

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

`scripts/check-doc-citations.py` 校验文档里 82 处 `文件:行号` 引用
是否仍指向它说的东西。改了 `src/` 之后跑一次：

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

本地要复现「部分后端」那一种：

```bash
env -u DEXATLAS_JADX_PATH uv run pytest
```

**这三个配置都要跑。** 只跑默认那一种，正是两个假定 JADX 已安装的测试
长期未被发现的��因。

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

DexAtlas 出现过九类「宣称完成了、实际没有完成」：

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

共同点有两个：

1. **它们都不让测试变红。** 绿色的测试套件证明不了「这个功能能用」，
   只证明「被断言的那些行为成立」。
2. **它们都藏在真实流程之外。** 手写的理想输入、被跳过的 fixture、
   没被拉取的样本、改写过的清单——只要不去跑一遍真实的东西，就看不见。

所以这个项目对自己的要求是：**不是「测试通过」，是「跑过一遍并且对得上」**。
新加一条测试时值得问一句——它用的是**真实流程里的输入**，还是我手写的那个？
