# Phase 1 成熟度评估

> 评估对象：DexAtlas @ `b8ef71a`
> 评估日期：2026-10-21
> 评估人：Claude Code（只读审查 + 实测）
> 本文只记录**能跑出来、能指到行号的**证据。README、`docs/status.md`、
> `docs/reports/phase1-execution-report.md` 里的自述一律当作**待验证的主张**，
> 不当作事实。凡是文档与代码不一致的，以代码和实测为准，不一致本身单列在第 5 节。

---

## 1. 方法

### 1.1 打分刻度

自定 0–10 刻度：

| 分 | 含义 |
| -- | ---- |
| 0 | 不存在 |
| 1–2 | 只有骨架/占位，无法运行 |
| 3–4 | 主体缺失，但存在的部分是真东西 |
| 5 | 能跑，但有已知缺口或未披露的降级 |
| 6–7 | 主体完整且可靠，缺陷集中在边缘或特定配置 |
| 8–9 | 完整、有证据支撑、边缘也处理妥当 |
| 10 | 完整 + 有外部可核验的证据 + 无已知缺口 |

「能跑」的定义：我在本机实际执行过，看到过输出。**README 说有但我没跑出来的，一律不算通过。**

### 1.2 证据要求

每个分数必须能追到以下之一，否则该条不计分：

- **file:line** —— 引用的行号全部按 `b8ef71a` 的内容核对过（见 1.4）。
- **命令输出** —— 我实际跑过的命令及其真实输出（命令写全，便于复核）。
- **实测对照** —— 我构造的最小复现（例如把工作区改成相对路径 / 绝对路径，各跑一次）。

### 1.3 我实际跑过的命令

```bash
git rev-parse --short HEAD                       # b8ef71a
uv run --no-sync dexatlas --help
uv run --no-sync dexatlas backends
uv run --no-sync dexatlas analyze examples/demo-app/demo.apk -o /tmp/da-demo.md
uv run --no-sync dexatlas analyze <2050 类合成 APK> -o /tmp/da-big/report.md --json ...
uv run --no-sync dexatlas source <id> "com.example.demo.Crypto" [--format json]
uv run --no-sync dexatlas xrefs <id> "<method-id>"
uv run --no-sync uvicorn dexatlas.api.app:app --port 8137   # 起 API，curl 全部端点
uv run --no-sync pytest --cov=dexatlas --cov-report=term-missing     # 773 项，6 分钟
uv run --no-sync pytest --collect-only -q [-m slow|-m "not slow"]
uv run --no-sync python scripts/refresh-report-figures.py --check
uv run --no-sync python scripts/check-doc-citations.py
uv run --no-sync python scripts/check-version-claims.py --base auto
uv run --no-sync python scripts/generate-large-apk.py --scale large --output-dir /tmp/da-big
uv sync --extra analysis                        # 全新克隆，按 README 走
```

后端环境（三个都装上了）：

```bash
export DEXATLAS_APKTOOL_JAR="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/apktool.jar"
export DEXATLAS_JADX_PATH="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin/jadx.bat"
export PATH="/c/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin:$PATH"
```

实测后端版本：jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4。

### 1.4 关于工作区的一个重要说明

评估期间（2026-10-21 约 03:26）**有另一个会话在并行修改 `src/dexatlas/api/app.py`
和 `src/dexatlas/core/storage.py`**（`git status` 可见两处 `M`）。这不影响本次结论，
但影响两件事，我做了隔离：

- 所有**行号引用**一律以 `git archive b8ef71a` 抽出的干净副本为准，
  而不是当前工作区（并行改动会让行号整体位移）。
- 文档一致性检查（`check-doc-citations.py`）在**当前工作区**报 2 处引用漂移
  （`analysis-provenance.md:123`、`analysis-provenance.md:1027`），
  在 **HEAD `b8ef71a` 上报 0 处漂移、退出码 0**。也就是说那 2 处漂移是并行改动引起的，
  **不是 `b8ef71a` 的缺陷**，不计入第 5 节。
- 同样地，执行报告数字过期导致的测试失败，我在 `b8ef71a` 的干净副本上复现过（见 3.4(1)），
  确认是 HEAD 本身的缺陷。

**本次评估的全部结论都针对 `b8ef71a`。**

### 1.5 我用的外部工具

无。整个评估只用了本仓库自带的脚本、`pytest`、`curl` 和标准库。

---

## 2. 总表

| 维度 | 分数 | 权重 | 加权分 | 一句话结论 |
| ---- | ---- | ---- | ------ | -------- |
| 核心功能与完整性 | **6** / 10 | 25% | 1.50 | 功能清单基本都在、都能跑，但**默认配置下 JADX 的 Java 反编译完全失效且报告不吭声**，另有两个静默截断上限 |
| 软件架构与代码质量 | **6** / 10 | 20% | 1.20 | 无循环依赖、mypy strict 全过、docstring 质量罕见地高；但抽象层是装饰性的，且存在数处「文档说 A、代码做 B」 |
| Agent / MCP 工程 | **4** / 10 | 20% | 0.80 | **MCP 完全不存在**（无 server / client / SDK 依赖），无 agent 编排；证据模型与 provenance 纪律是真东西，locator 是只写不读 |
| 测试、可靠性与安全 | **6** / 10 | 15% | 0.90 | 安全边界扎实、变异测试证明测试是行为级的、基准文档诚实；但**套件在 HEAD 上是红的**，且项目最在意的「静默截断」恰好没有测试 |
| 文档与开发者体验 | **6** / 10 | 10% | 0.60 | 文档有自检工具链、provenance 文档是招牌；但旗舰报告自己的数字过期（并因此让套件变红），README 徽章过期 |
| GitHub / Upwork 展示价值 | **5** / 10 | 10% | 0.50 | 门面材料齐全（中英 README、演示视频、自建样本、三档 CI），但**买家最先看的两样——CI 徽章与测试数徽章——此刻都是错的** |
| **加权总分** | | **100%** | **5.50 / 10** | |

---

## 3. 六个维度

### 3.1 核心功能与完整性 —— 6 / 10（权重 25%，加权 1.50）

#### 支撑证据

**（1）功能清单逐条核对 —— 清单本身基本成立。** 逐条实测结果：

| 清单项 | 状态 | 证据 |
| ------ | ---- | ---- |
| manifest 解析 | ✅ | `E-0001 declaration / Package com.example.demo (versionName=1.0, minSdk=24, targetSdk=34)` |
| DEX 索引（类/方法/字段/字符串/资源） | ✅ | 报告 `Classes indexed 5 / Methods indexed 8 / Resource strings indexed 1` |
| 交叉引用 | ✅ | 报告 `Cross-references indexed 23`；`dexatlas xrefs` 正确返回 `MainActivity.onCreate(...)V → Crypto.sign(...)` |
| 三后端分工与回退 | ⚠️ | `dexatlas backends` 三个都 `available`；但 JADX 的回退逻辑在默认配置下**恒定触发**（见 (2)） |
| 证据记录 | ✅ | `GET /projects/{id}/evidence` 返回 9 条，每条带 `provenance`（tool / tool_version / apk_sha256 / locator） |
| 报告 Markdown / JSON | ✅ | 两份都实测生成 |
| CLI | ✅ | `dexatlas --help` 列出 11 个命令，全部试过 |
| REST API | ✅ | `/openapi.json` 列出 16 个端点，逐一 curl 过 |
| 存储与检索（FTS5） | ✅ | `core/storage.py:200` `CREATE VIRTUAL TABLE ... USING fts5`；`search_index MATCH ?`（`storage.py:630`）、`snippet(search_index, 3, …)`（`storage.py:628`） |

**（2）默认配置下 JADX 的输出被写进双重嵌套目录，代码找不到它 —— 高severity。**

`src/dexatlas/config/settings.py:26`：

```python
workspace: Path = Field(default=Path(".dexatlas"))
```

默认值是**相对路径**。`src/dexatlas/core/pipeline.py:118` 用它拼出工作目录，
**没有 `.resolve()`**。然后 `src/dexatlas/tools/jadx/adapter.py:237-241`：

```python
                    "--output-dir",
                    str(output_dir),      # ← 相对路径
                    str(apk),
                ],
                cwd=output_dir,          # ← 子进程的工作目录也是它
```

JADX 把 `--output-dir` 相对**自己**的工作目录解析，于是写到了
`<output_dir>/<output_dir>/sources/...`。实测（相对工作区，默认配置）：

```
.dexatlas/projects/apk_80a8fe0e81204c9f/jadx/.dexatlas/projects/apk_80a8fe0e81204c9f/jadx/sources/com/example/demo/Crypto.java
```

同一份 APK，只把工作区改成**绝对路径**，输出路径就正确了：

```
/tmp/da-abs-ws/projects/apk_80a8fe0e81204c9f/jadx/sources/com/example/demo/Crypto.java
```

两者的报告差异是实测出来的，不是推断：

| 指标 | 相对工作区（默认） | 绝对工作区 |
| ---- | ------------------ | ---------- |
| Classes indexed | **4** | **5** |
| Methods decompiled by JADX | **该行不存在** | `7 of 8` |
| decompilation 证据记录 | **没有** | `E-0010 … jadx produced real Java for 7 of 8 methods in 5 of 5 classes` |
| `dexatlas source` 输出 | **smali** | java |
| Tool versions 行 | `… jadx 1.5.2` | `… jadx 1.5.2` |

最后一行是关键：**报告照旧列着 `jadx 1.5.2`，但整份报告里没有一句说 JADX 什么也没产出。**
我按 README 的 Quick start 在一个全新目录里原样跑了一遍，得到的就是左列。

为什么测试抓不到：`tests/conftest.py:117` 是 `Settings(workspace=tmp_path / "workspace")`，
`tmp_path` 是**绝对路径**；`tests/test_jadx_parsing.py:50-55` 的 JADX 测试是**手写 .java 文件**，
从来不真的跑 JADX 再看它写到哪。全仓库没有一个测试用过相对工作区（grep 验证）。

Apktool 没中招，因为 `tools/apktool/adapter.py` 不设 `cwd=`。

**（3）两个静默截断上限，报告不披露 —— 高 severity。**

`core/pipeline.py:53` `MAX_EVIDENCE_CLASSES = 500`，`:301` 处
`builder.add_classes(classes[:MAX_EVIDENCE_CLASSES])`；超限时只有一行
`logger.info`（`:302-306`），**没有 ToolError、没有证据行、没有报告行**。
`core/evidence.py:33` `MAX_EVIDENCE_CALLED_METHODS = 100`，`:211` 处
`called[:MAX_EVIDENCE_CALLED_METHODS]`，同样静默。

用 2050 类的合成 APK 实测，报告长这样：

```
| Classes indexed | 2,002 |
| Cross-references indexed | 200,000 |
| Cross-references with evidence | 1 |
| Evidence records | 504 |
```

证据只覆盖了 500 个类（报告里 504 条记录），而报告对这 500 这个数字**一个字都没说**。
更糟的是 `reports/markdown.py:31-35` 的 `_XREF_NOTE` 只把「交叉引用没有证据」归因于
「调用 JDK 方法不算证据」——读者据此会算出错误的漏报数字，看不到还有第二个原因（100 条上限）。

对比：**索引层的截断披露得非常好。** 同一份报告里：

```
| Index completeness | incomplete: string limit 50000 reached: … 1449 entries … were not indexed …
> **This index is incomplete.** The counts above cover the parts of the APK that
> could be read, not the whole of it.
```

这说明项目**知道**怎么披露截断——只是漏了这两个上限。这两个恰好落在
「证据优先」这条主线上。

**（4）API 导出的报告写着一句假话 —— 高 severity。**

`api/app.py:600-610` 的 `_rebuild_result` 重建 `AnalysisResult` 时**没有设
`duration_seconds`**，于是默认 0.0。`reports/markdown.py` 与
`reports/json_report.py` 无条件打印这个数。实测：

```
$ curl -s "…/projects/apk_80a8fe0e81204c9f/report?format=markdown" | grep "Analysis time"
| Analysis time | 0.0s |

$ grep "Analysis time" /tmp/da-demo.md          # 同一份分析的 CLI 导出
| Analysis time | 2.9s |
```

**每一个从 REST API 导出的报告，都写着一个分析从未产生过的数字。**
在一条「证据优先」的产品线上，这属于最不能犯的一类错。

**（5）Androguard 有两处宽泛捕获会静默缩小索引 —— 中 severity。**

`tools/androguard/adapter.py:523-524`（单个方法的字节码解码失败）与 `:612-613`
（字符串池提取失败）都是 `except Exception` + `logger.debug`，**不记录任何错误**。
前者让方法「看起来就是没有调用边」，后者让报告继续说索引是完整的。
讽刺的是 `tools/base.py:3` 声称「Backends are subprocess wrappers, never links」，
而 `tools/androguard/adapter.py:11-14` 自己写着
「Androguard runs in-process rather than as a subprocess — That is the one exception
to the subprocess rule」——**唯一无法被进程边界隔离的后端，正是会静默丢数据的后端**。

**（6）能跑的证据 —— 上限触顶时 CLI 与报告确实会说。**

```
$ uv run --no-sync dexatlas analyze /tmp/da-big/large.apk -o report.md
WARNING androguard: string limit 50000 reached; index is truncated
WARNING androguard: method limit 200000 reached on classes4.dex; index is truncated
!  string limit 50000 reached: the index is incomplete — 1449 entries of this DEX file's
   string pool were not indexed, and no DEX file after it contributed any string; …
```

**（7）后端缺席时优雅降级 —— 实测。**

全新克隆只装 `analysis` extra（JADX / Apktool 都不在）：

```
$ uv run --no-sync dexatlas backends
│ jadx       │ not installed │ —       │
│ apktool    │ not installed │ —       │
│ androguard │     available │ 4.1.4   │
2 backend(s) unavailable. Analysis continues with what is installed, and records the gap as evidence.
```

分析照常完成，错误进 `project.errors`，报告有「Backend errors」段。这一条是真的做到了。

#### 要拿更高分需要做什么

1. **修 JADX 输出路径**（最高优先）。二选一：`settings.py:26` 的默认改成绝对路径
   （`Path(".dexatlas").resolve()` 或在 `ensure_workspace()` 里 `resolve()`），
   或者 `jadx/adapter.py:241` 的 `cwd=output_dir` 改成绝对路径 / 去掉 `cwd`。
   **并补一个用相对工作区跑真实 JADX 的集成测试**——现在这条路径一次都没被测过。
2. **给 `MAX_EVIDENCE_CLASSES` 和 `MAX_EVIDENCE_CALLED_METHODS` 加披露**：
   在报告里写一行「证据覆盖了前 500 个类 / 前 100 个被调用方法」，
   并在 `Evidence.detail` 里带 `truncated` 标记（`evidence.py:178` 已有这个模式，照抄即可）。
   同时把 `_XREF_NOTE` 的归因补上第二个原因。
3. **修 `_rebuild_result` 的 `duration_seconds`**：要么从 `projects.created_at` 算出来，
   要么在导出的报告里这一行直接不出现。**不能让报告打印一个 0.0。**
4. **把 Androguard 的两处 `logger.debug` 变成 `ToolError`**，
   让「解码失败」和「没有调用边」在报告上可区分。
5. **JADX 什么也没产出时，报告必须说**。`core/pipeline.py:622` 的 `if not status: return`
   应改成记一条「jadx 未产出任何类」的事实，而不是让报告保持沉默。

---

### 3.2 软件架构与代码质量 —— 6 / 10（权重 20%，加权 1.20）

#### 支撑证据

**（1）架构底子比一般项目好。**

- **无循环依赖**：28 个模块逐个在新进程里单独 import，全部成功。
- **分层清晰**：`core/` 从不 import `api/` 或 `cli/`；`api/` 与 `cli/` 都是 `core`+`reports` 之上的叶子。
- **类型严格度高于典型**：`pyproject.toml` 设 `mypy strict = true` +
  `warn_unreachable` + `disallow_any_generics`；实测 `mypy` 0 error，`ruff check` 全过。
- **规模**：`src/` 7,035 行，`tests/` 13,304 行，`docs/` 4,616 行。测试代码是源码的两倍。

**（2）但抽象层是装饰性的。**

- `tools/base.py:90` 的 `Backend` ABC 说「Subclasses declare how to locate and probe their
  tool, then implement extraction」——**基类里根本没有 `extract` 抽象方法**，
  三个子类的 `extract` 签名还各不相同
  （`jadx` 是 `(apk_sha256, output_dir, outcome)`，`androguard` 是 6 元组）。
- `core/pipeline.py` 在模块层直接 import 三个具体适配器
  （`pipeline.py:43-47`），`BackendRegistry` 只被用来做 `versions()`/`available()`——
  **注册表在真正的干活路径上被绕过了**。
- 版本缓存实现了两遍：`tools/base.py:264-274` 一遍，三个适配器各一遍。
- `androguard/adapter.py:141-142` 的 `resolve()` 返回的是**包文件路径**
  （`androguard/__init__.py`），而基类契约是「Locate the backend executable」。

**（3）「文档说 A、代码做 B」这一类缺陷确实还剩。**（行号按 `b8ef71a` 核对）

| 位置 | 声称 | 实际 |
| ---- | ---- | ---- |
| `tools/base.py:3` | "Backends are subprocess wrappers, never links" | Androguard 是进程内库；`androguard/adapter.py:11-14` 自己承认是 "the one exception" |
| `core/storage.py:268` | "Additive only." | 同一函数 `:284` 就 `DROP TABLE resources`（注释说 resources 表是缓存，不是真相来源） |
| `core/ingest.py:6-7` | "inspected through its *central directory* … rather than by decompressing it" | `_verify_entries`（`:155-173`）实际解压最多 256 MiB 去校验 checksum |
| `core/pipeline.py:497` | "Apktool knows the manifest declaration, Androguard the DEX definition. Both are kept" | Apktool **从不产出 ClassRef**（`pipeline.py:230` `classes: list[ClassRef] = []` 恒空；`tools/apktool/adapter.py` 里 `ClassRef` 零命中） |
| `core/storage.py:427` | "symbol tables key on the symbol" | 对 `classes`/`methods`/`fields` 成立，对 `xrefs`（`:157-163`）与 `strings`（`:165-171`）**不成立——这两张表没有主键** |
| `core/evidence.py:31-32` | "The report's evidence table shows 200 rows, so this leaves room for the class declarations in the same table" | 100 条 xref + 最多 500 条 class = 600 条 vs 200 行表；实测 class 行溢出，表尾写 `_400 further evidence records omitted._` |
| `core/evidence.py:192-193` | 只把「调用 JDK 方法」当作 xref 无证据的原因 | 还有第二个原因：100 条上限。读者据此算错漏报 |
| `core/paths.py:34-35` | "rejects a name with any empty segment **before it splits into components**" | 代码 `:69` 先 `split(".")` 再判空 |
| `core/paths.py:20-21` | "Windows caps it at the same number"（255 字节） | NTFS 限的是 255 个 **UTF-16 码元**，不是字节；一个 200 字的中文类名能过字节检查却超字符限制 |
| `tools/base.py:29-30` | "#: Output that exceeds this is treated as a runaway backend rather than a result." | `_DEFAULT_MAX_OUTPUT` **全仓库零引用**，是死常量；活着的是 `settings.tool_max_output_bytes` |
| `tools/base.py:246-252` | `_decode` 里 `if len(raw) > limit: logger.warning("output truncated…")` | 该分支**不可达**：`_read_capped`（`:403-413`）先 `truncate(limit)` 再读，`len(raw) <= limit` 恒成立。**后端 stdout 被裁剪时永远不会被告知** |
| `api/app.py:3-4` | "No analysis behaviour is defined here, so the two interfaces cannot diverge" | API 对已分析过的 APK **去重**（`:301-307`），CLI **不去重**（`cli/main.py:187` 每次重跑） |
| `core/models.py:77-79` | EvidenceLevel 的 LEAD / INSUFFICIENT 是给模型输出用的闸门 | `src/` 里**没有任何一处产生这两个等级**，报告的等级表恒为 `lead 0 / insufficient 0` |
| `tools/androguard/adapter.py:579,592` | locator 格式 `<tool>:<place>` | 字符串值被截到 64 字符，两个同前缀的长串**得到同一个 locator**——指针不再指向唯一位置，文档未记载 |

**（4）死代码不是偶然的，是被放弃的设计决策。**（每个都做过全仓库引用计数）

| 位置 | 符号 | 说明 |
| ---- | ---- | ---- |
| `api/app.py:160-163` | `SubmitResponse` | 带 `already_analysed` 字段，为「已分析过」这个契约准备的；`/analyze` 返回的是另一个模型 |
| `tools/base.py:447` | `java_available()` | docstring 说「Apktool 和 JADX 都需要 JRE」——但 `apktool/adapter.py:93` **无条件**拼 `["java","-jar",…]`，没人做这个预检 |
| `tools/base.py:461` | `coerce()` | 「Best-effort conversion of a tool's loosely typed JSON field」——**没有后端解析任何工具的 JSON** |
| `tools/base.py:30` | `_DEFAULT_MAX_OUTPUT` | 被放弃的输出上限声明 |
| `config/settings.py:32-33` | `rizin_path` / `ghidra_path` | 不会有 rizin / ghidra 后端 |
| `config/settings.py:55-56` | `cache_dir` | **每次运行都创建、从不写入**——没有缓存 |
| `core/models.py:254-255` | `ClassRef.simple_name` | 零引用 |
| `tools/androguard/adapter.py:80` | `INVOKE_OPCODES` | 定义 + `__all__`，从不使用 |

**（5）异常处理。** 10 处 `except Exception`。5 处吞掉失败且**不记录错误**，
其中 2 处（`androguard/adapter.py:523`、`:612`）在主分析路径上，会让索引静默变小而报告称完整。
`api/app.py:322` 的后台分析失败会让 project 永远停在 `running` 状态
（`pipeline.py:204` 的最终 `save_project` 不会执行）——轮询 `/projects/{id}` 的客户端会无限等待。

**（6）干净的地方（不是所有地方都有问题）。** `src/` 里 **零个 TODO / FIXME / XXX / HACK**。
所有 `:meth:`/`:func:`/`:class:` 交叉引用都能解析到真实符号。CLI 的 `--limit 0` / `-1`
拒绝是真的被 Typer 的 `min=1` 强制的。

#### 要拿更高分需要做什么

1. **让抽象层名副其实**：把 `extract` 提到 `Backend` 基类，或者明确改掉 `base.py:90` 的措辞；
   `BackendRegistry` 要么真正管住分发，要么就别叫 registry。
2. **清死代码**：至少把 `SubmitResponse`、`java_available`、`coerce`、
   `_DEFAULT_MAX_OUTPUT`、`rizin_path`/`ghidra_path` 删掉或用起来。
   `java_available()` 尤其该用——现在 Apktool 在没有 JRE 的机器上是**运行期**失败而不是预检失败。
3. **修 5 处「文档说 A、代码做 B」**：`base.py:3`、`storage.py:268`、`ingest.py:6`、
   `pipeline.py:497`、`storage.py:427`（xrefs/strings 加主键或改措辞）。
4. **`_decode` 的截断分支改成真能触发**（把 `_read_capped` 的截断信息传出来），
   否则 256 MiB 的 stdout 上限是纯静默的。
5. **让 API 与 CLI 的行为真的对齐**（`api/app.py:3-4` 的那句声称），
   并修 `api/app.py:322` 的 `running` 悬挂。

---

### 3.3 Agent / MCP 工程 —— 4 / 10（权重 20%，加权 0.80）

> **这一项是全项目权重第二高、而目前做得最少的。** 下面把
> **（A）已经有且做得好**、**（B）有但没做完**、**（C）完全没有**三类严格分开。

#### 先把 MCP 这件事查清楚

**（C）MCP 完全不存在。** 不是「没做好」，是**一行都没有**：

```bash
$ grep -rn -i "mcp" src/dexatlas/          # 0 命中
$ ls src/dexatlas/mcp/                      # No such file or directory
$ grep -c 'name = "mcp"' uv.lock            # 0
```

没有 server、没有 client、没有 `mcp`/`fastmcp` SDK 依赖、没有 tool/resource/prompt 定义。

`src/` 里全部 "mcp" 命中都在 `tests/` 与 `docs/`，而且**全部是防止项目夸大**的守卫：

- `tests/test_docs.py:111` —— `for unbuilt in ("mcp", "agent", "workbench"): assert unbuilt not in quick_start.lower()`
- `tests/test_docs.py:656` —— `assert "MCP server is shipped" not in report.lower()`

承诺的位置：`docs/roadmap/ROADMAP.md:252-256` 的 §2.2，版本 **v0.5.0（Phase 2）**；
`README.md:86` 同。当前版本 `0.1.3`。

**这个诚实度要记在项目账上**：README 明说「Agent orchestration, MCP and the web workbench
are *planned*, not shipped」，`docs/releases/v0.1.0.md:78` 说「This release has no AI in it」，
而且有测试强制它继续诚实。**但对本维度而言，「交付物不存在」就是不存在。**

#### （A）已经有且做得好

**证据模型（`core/models.py` + `core/evidence.py`）——这是本项目最像「为 agent 而建」的部分。**

- `EvidenceKind`（`models.py:454-459`）5 个成员、`EvidenceLevel`（`:462-476`）3 个成员，
  都是 `StrEnum`，字符串值，JSON 友好。
- `Provenance`（`:112-143`）是 **frozen** pydantic model，只有 4 个字段：
  `tool` / `tool_version` / `apk_sha256` / `locator`。
- `EvidenceLevel` 的设计意图写在 docstring 里（`:462-476`）：
  「Model output is never promoted past :attr:`LEAD` without grounding. This is the mechanism
  behind "an LLM thinking code looks risky is not a finding"」——**这是正确的设计**，
  机制上模型无法自我提级。
- `EvidenceBuilder` 的 `tool_versions` 是**构造参数**不是事后记忆的字段
  （`evidence.py:41-49`：「an evidence record cannot be written without them」），
  `None` 表示「这个工具根本没跑」，是事实不是缺口。
- 后端失败本身是一条 `VERIFIED` 证据（`evidence.py:101-116`）。

**REST API（`api/app.py`）——真实可用，不是摆设。** 16 个端点，自动 OpenAPI 3.1。
实测 `curl` 全部走过：

```
$ curl -s .../health
{"status":"ok","version":"0.1.3","backends":{"jadx":"1.5.2","apktool":"2.11.1","androguard":"4.1.4"}}
$ curl -s .../classes
{"project_id":"apk_80a8...","total":4,"classes":[{"provenance":[{"tool":"androguard","tool_version":"4.1.4","apk_sha256":"80a8fe...","locator":"androguard:classes.dex#com.example.demo.Crypto"}],"name":"com.example.demo.Crypto",…}]}
$ curl -s .../evidence
{"project_id":"apk_80a8...","total":9,"evidence":[{"provenance":[…],"id":"E-0001","kind":"declaration","level":"verified","summary":"Package com.example.demo (versionName=1.0, minSdk=24, targetSdk=34)",…}]}
```

`source` 端点的响应头 `X-DexAtlas-Source-Kind` / `-Tool` / `-Locator` / `-Tool-Version`
（`api/app.py:169-186`）让调用方知道拿到的到底是 Java 还是 Smali——这是 agent 需要的区分。

**CLI 退出码契约（`cli/main.py:60,64`）——对 agent 友好，且实测有效：**

```
空答案(xrefs) → 1     空答案(search) → 1     项目不存在 → 2     版本 → 0
```

「答案为空」与「请求错了」分开，这是很多项目都没做的。

#### （B）有，但没做完

**locator 格式：构造了 12+ 处，解析了 0 处。**

格式在 `models.py:120-127` 的 docstring 里定义（`<tool>:<place>`），
但那是一段**散文，不是可执行规格**：

| | |
| - | - |
| 构造点 | `jadx/adapter.py:151-162`、`apktool/adapter.py:55-65`、`androguard/adapter.py:244,359,365,394,473,484,579,592`、`core/pipeline.py:410,428,654`、`core/evidence.py:112,146` |
| 解析点 | **零。** 唯一的 `normalize_locator()`（`models.py:94-109`）是旧 JADX 绝对路径格式的**迁移垫片**，不是语法校验器 |

**后果：locator 是只写指针。** 仓库里**没有任何函数**能把一个 locator 还原成文件、方法或符号。
`docs/analysis-provenance.md` §4.5 教读者怎么复核一条结论，第 3 步「按 locator 找到那个文件」
**只能靠读者手工重建工作区路径**。这是给 agent 的最有价值的一个缺失原语。

另外：locator 里**没有任何行号**（只有符号名）；`#str/<前 64 字符>` 会让同前缀字符串碰撞；
`#<method_name>` 分不清重载。

**REST API 的形状 —— 有骨架，缺工程化。**

- **9 / 16 个端点是 untyped**：生成的 OpenAPI 里 `/backends`、`/manifest`、`/classes`、
  `/methods`、`/resources`、`/xrefs`、`/search`、`/evidence`、`/report` 的 schema 是
  `{"type":"object","additionalProperties":true}`——**对 schema 驱动的客户端是黑盒**。
- **没有分页**：只有 `limit`，没有 offset/cursor。大结果集无法翻页。
- **`/evidence` 无 limit、无过滤**：只能拉全部再在客户端过滤（不能按 kind/level/tool 过滤）。
- **错误体的 `detail` 是多态的**：`HTTPException` 给字符串，`RequestValidationError` 给对象数组。

**CLI —— 是人用的，不是 agent 用的。** 11 个命令里**只有 `source --format json` 输出 stdout JSON**；
`analyze --json` 是写文件；`classes`/`methods`/`search`/`xrefs`/`manifest` 全是 Rich 表格，
agent 只能去解析制表符画出来的框线。

**（C）完全没有**

- 无 agent 编排：无规划器、无 agent loop、无 LLM 客户端、无 prompt 模板、无 provider 集成。
- 无可恢复任务：无 checkpoint、无任务状态机。`Analyzer.analyze` 每次重跑整条流水线；
  `Store.save_evidence` 会**删掉旧证据重建**（`storage.py:646`，删除语句在 `:664`）。
- 无证据校验器：没有任何函数接受一条 `Evidence` 并检查它的 locator 能解析、结论站得住。
- 无工具描述符：仓库里**没有** `name`/`description`/`input_schema` 这类可交给模型的工具定义。
- **无 `dexatlas evidence` 子命令**：证据只能从 API（无过滤）、报告或裸 SQL 拿。

**`docs/analysis-provenance.md` 是这个仓库最好的资产，但它的验证流程只有 2/4 有工具支撑。**

§4.5「逐条核对一条结论」的四步里：第 1 步（`dexatlas xrefs`）有、第 4 步（`dexatlas source`）有、
第 3 步（按 locator 找到文件）**没有**、第 2 步（读原始 provenance）**只有裸 SQL**。
文档自己的速查表（`:1220`）就是绕开这个缺口的：「想看完整 provenance 列表 → `dexatlas classes --all`」。

#### 要拿更高分需要做什么

按性价比排序：

1. **写一个 locator → 路径的解析器**（`locator_to_path(project, locator) -> Path`）。
   这是给 agent 的最高价值缺失原语，工作量小（格式已经在 12 个构造点定死了），
   而且能直接兑现 `analysis-provenance.md` §4.5 的第 3 步。
2. **加 `dexatlas evidence` 子命令**，带 `--kind`/`--level`/`--tool` 过滤和 `--json`。
   现在 agent 要拿证据只能拉全表或写 SQL。
3. **让 CLI 的查询命令支持 `--json`**（`classes`/`methods`/`search`/`xrefs`/`manifest`），
   退出码契约已经有了，补上机器可读输出即可。
4. **给 REST API 的 9 个 untyped 端点补 pydantic response model**，并加 offset/cursor 分页。
   OpenAPI 是 agent 的契约，不该是黑盒。
5. **让 `EvidenceKind` / `EvidenceLevel` 的未使用成员有生产者**——
   要么现在就让模型输出能落成 `LEAD`/`INSUFFICIENT`（哪怕只是接一个可选的 LLM 钩子），
   要么把暂时不用的成员从公开枚举里挪走，别让 agent 按枚举名推断能力。
6. **MCP server 本身**（v0.5.0 的正题）。在 1–4 做完之前它没有意义——
   把一个只写不读的 locator 暴露成 MCP tool，只会把问题放大。

---

### 3.4 测试、可靠性与安全 —— 6 / 10（权重 15%，加权 0.90）

#### 支撑证据

**（1）测试套件在 HEAD 上是红的 —— 这是必须先说的事实。**

```
$ uv run --no-sync pytest --cov=dexatlas --cov-report=term-missing
FAILED tests/test_docs.py::test_execution_report_numbers_match_the_code
E   AssertionError: the execution report disagrees with the code:
E     tests.total: the report says ['738'], the code has 773
E     tests.fast:  the report says ['618'], the code has 653
1 failed, 772 passed, 1 warning in 351.01s (0:05:51)
```

实测数量（**不是抄 README 徽章**）：**收集 773 项 = 653 fast + 120 slow；
772 通过，1 失败，0 跳过**（三个后端齐全时）。

失败原因：`docs/reports/phase1-execution-report.md` 的数字是 738/618，实际是 773/653。
我在 `b8ef71a` 的干净副本上复现了同样的失败（`1 failed, 38 passed, 3 skipped`），
确认是 HEAD 自身的缺陷，不是并行改动造成的。

**CI 因此是红的**：`ci.yml` 的 `test` 作业跑的是不带 `-m` 过滤的全套件，
而这个失败没有任何 skip 条件（`tests/test_docs.py:487` 起）。
`docs/roadmap/ROADMAP.md:171` 的退出清单里 `[x] GitHub Actions green on Python 3.12 and 3.13`
**与 HEAD 的事实不符**。

**（2）覆盖率：94%，但缺口不在错误分支上。**

```
TOTAL   2511 stmts   155 miss   94%
```

最低的几个模块：

| 模块 | 覆盖率 | 未覆盖行（HEAD） |
| ---- | ------ | ---------------- |
| `tools/base.py` | **84%** | 187-192, 227-228, 249-250, 302, 327-335, 356-357, 365, 372-377, 449, 453, 463 |
| `tools/jadx/adapter.py` | **87%** | 192, 219, 266, 269, 321, 355, 358, 370, 378, 398, 408, 411-412, 463-474, 478, 487, 502, 504, 510, 513, 542-543 |
| `tools/androguard/adapter.py` | **91%** | 106-108, 119, 138, 199, 204-205, 292-294, 523-524, 570-573, 612-613, 659, 662, 720-721, 780, 796 |
| `core/ingest.py` | 93% | 111, 129, 165, 171-173 |
| `api/app.py` | 93% | 284-285, 303, 322-323, 350, 377-378, 452, 456, 489-490, 531, 604 |

**未覆盖行的构成，我逐行看过，不是清一色的错误分支**：

- `tools/base.py:187-192`、`:227-228` —— **确实是错误分支**（`Popen` 周围的
  `FileNotFoundError` / `PermissionError` / `OSError`）。
- `tools/base.py:249-250` —— `_decode` 那个**不可达**的截断分支（见 5.2 第 13 条）。
- `tools/base.py:302`、`:327-335` —— **平台分支**：POSIX 的 `start_new_session` 与
  `os.kill(-pid)` 进程组终止，在 Windows 上跑不到；反过来 `:356-357`、`:365` 是
  Windows `taskkill` 的失败分支。**CI 只在 ubuntu 上跑，这半边永远不测。**
- `tools/base.py:372-377` —— `_reap` 的 wait/kill 序列，**未覆盖**。这是「杀掉一个失控后端」
  的代码，属于安全边界。
- `tools/base.py:449`、`:453`、`:463` —— `java_available()` / `parse_error` / `coerce()`
  的函数体，**死代码**，所以永远不覆盖。

而 `tools/jadx/adapter.py:463-474` 是从反编译文本里配对花括号提取方法体的辅助函数
（`_find_matching_brace`），**不是**输出路径那部分——输出路径（`:237-241`）的 argv 构造
本身是**被测到的**。真正没有测试断言的是「JADX 实际把文件写到了哪里」这件事，
因为没有任何测试真的跑 JADX 再检查落点。

**（3）变异测试：测试确实是行为级的。** 我在 `b8ef71a` 的干净副本上做了两次变异：

*变异一：关掉路径穿越守卫*（`core/paths.py` 的分隔符与 `..` 检查改成 `if False`）

```
7 failed, 13 passed      # test_paths.py
FAILED test_a_name_that_is_not_a_class_name_is_refused[unc]
FAILED test_a_name_that_is_not_a_class_name_is_refused[drive-relative]
FAILED test_a_name_that_is_not_a_class_name_is_refused[separator]
FAILED test_a_name_that_is_not_a_class_name_is_refused[backslash]
FAILED test_a_single_component_is_about_being_one_component
```

*变异二：让报告不再声明索引不完整*（`reports/markdown.py` 的 `_index_completeness` 硬返回 `"complete"`）

```
FAILED tests/test_partial_backend_failure.py::test_the_report_says_the_index_is_incomplete
```

**两个变异都被抓住，且抓住的是行为（输出里的那句话），不是内部实现。** 这条要给足分。
但变异也暴露了覆盖的边界：**下面三处没有测试**，改了不会红：

- `MAX_EVIDENCE_CLASSES`（`grep MAX_EVIDENCE_CLASSES tests/` → **0 命中**）
- JADX 的 `--output-dir` + `cwd` 组合（`tests/test_jadx_parsing.py` 是手写 .java 文件，从不真跑 JADX）
- API 导出的报告里的 `duration_seconds`（`tests/test_reports.py:98` 只测渲染器，不测 API 导出路径）

**（4）可靠性：基准文档是本项目的第二个招牌。**

`docs/benchmarks/large-apk.md` 有 §6「What was not measured」，明确列出没测的：
真实 APK、JADX/Apktool 在规模下的表现、native 库、内存、CI 计时、APK 字节可复现性。
**一份报告主动写下自己的测量边界，这正是这个项目的主张。** 我用 `--scale large`
（2050 类 / 205,000 方法 / 4 个 DEX）实测跑了一遍，40.2 秒，产出与文档一致的行为
（字符串上限、方法上限都触顶并如实披露）。

**（5）安全：这是本项目最扎实的一块。**

| SECURITY.md 的承诺 | 代码证据 |
| ------------------- | -------- |
| "No shell. Backend invocations use argument arrays" | `tools/base.py:182` `shell=False`；全仓库无 `shell=True`/`os.system` |
| "Subprocess isolation" | `tools/base.py:197-199` 超时后 `_terminate_tree`；Windows 走 `taskkill /T`（`:338-356`），POSIX 走进程组（`:320`） |
| "Workspace scoping" | `core/paths.py:89-96` `is_inside()` 做链接解析后的包含检查 |
| 上传限制 | `api/app.py:82-113` `UploadSizeLimitMiddleware` 先看 Content-Length，流式计数兜底 chunked |
| 归档炸弹 | `core/ingest.py:34-56` 四个上限：256 MiB 包体、2 GiB 解压后、100× 膨胀比、256 MiB 校验预算 |
| 路径穿越 | `core/paths.py:57-77` `class_to_relative_path`（**变异测试已验证会被抓住**） |

`defusedxml` 用于 manifest 解析（`pyproject.toml` 有注释说明为什么）。
`ci.yml` 有独立的 `pip-audit --strict` 作业。

**（6）安全侧的两个小问题。**

- `SECURITY.md:31` 把「Injection in DexAtlas's own CLI, REST API or **MCP surface**」列为 in-scope——
  **项目没有 MCP**。
- `api/app.py:322`：后台分析失败时 project 永远停在 `running` 状态，客户端轮询会无限等待。

#### 要拿更高分需要做什么

1. **先修执行报告的数字**（`scripts/refresh-report-figures.py` 跑一次 `--write` 即可），
   让套件回到绿。**这是 Phase 2 之前必须做的第一件事**——一个「证据优先」项目的套件是红的，
   这一条几乎抵消了它其余所有的加分项。
2. **补三条测试**：`MAX_EVIDENCE_CLASSES` 的披露、**相对工作区下真跑一次 JADX 并检查输出落点**、
   API 导出报告的 `duration_seconds`。这三条正是本次找到的三个静默失败点。
3. **把 `tools/base.py` 的未覆盖行补上**——重点是 `:372-377`（`_reap` 的 wait/kill 序列）
   与 `:327-335`（POSIX 进程组终止）。杀失控后端是安全边界，不该只有 84%。
   平台分支（`:302` vs `:301`）建议在 CI 上补一个 Windows 作业，否则 Windows 专用的
   `taskkill` 路径永远只在本地跑。
4. **把 `SECURITY.md:31` 的 "MCP surface" 删掉或改成分期表述**。
5. **修 `api/app.py:322` 的 `running` 悬挂**（失败时把 project 置为 `failed`）。

---

### 3.5 文档与开发者体验 —— 6 / 10（权重 10%，加权 0.60）

#### 支撑证据

**（1）我照着 README 走了一遍（全新目录、默认工作区）。**

```bash
$ cd /tmp/da-readme-ws && uv run dexatlas analyze G:/dexatlas/examples/demo-app/demo.apk -o report.md
✓ apk_80a8fe0e81204c9f — 4 classes, 8 methods, 23 cross-references, 1 resource string (3.5s)
```

**新人的每一步都能走通，没有一个「卡住」的点**——这是很多项目做不到的。
全新克隆 `uv sync --extra analysis` 后 `dexatlas backends` 正确报出
jadx/apktool 缺失、androguard 可用，并给出各自的后端下载指引。
`docs/install.md` 有完整的安装、配置、排错章节（`:273` Troubleshooting）。

**但**：新人按 README 走完，拿到的是 **Smali 而不是 Java**，而且报告里**没有任何一句**
解释为什么（见 3.1(2)）。README 自己说「Methods JADX cannot decompile reliably are
flagged as errors and retain a Smali fallback」——在这个默认配置下，JADX **能**反编译
（绝对路径下实测 7/8 方法），只是 DexAtlas 找不到它。

**（2）数字是自动生成的——机制是真的。**

`docs/reports/phase1-execution-report.md` 里 18 处数字都用 `<!--fig:key-->value<!--/fig-->`
标记，另有 `docs/status.md` 3 处。脚本存在且工作：

```bash
$ uv run --no-sync python scripts/refresh-report-figures.py --check
Collecting the test suite...
  773 tests: 653 fast, 120 integration
Running the suite with coverage (this takes a couple of minutes)...
  passed=761 (the report's own self-checks are measured separately)
Measuring the report's self-checks against a candidate report...
  the self-checks agree with the refreshed report (passed=9) after 2 round(s)
tests.total: 738 -> 773
tests.fast: 618 -> 653
The report does not match a fresh measurement.
EXIT CODE = 1
```

**脚本自己发现了报告过期，并且退出码是 1。** 机制是好的；只是没人跑它。
（`coverage.pct` 等数字没被列为漂移，说明覆盖率部分与脚本口径一致。）

**（3）文档的行号引用是被机器检查的——这一点很少见。**

```bash
$ uv run --no-sync python scripts/check-doc-citations.py      # 在 b8ef71a 干净副本上
citations: 94
  naming a symbol: 93
  pointing only at a location: 1
unresolved paths: 0
drifted: 0
Every citation still says what it says.
EXIT=0
```

**94 处引用，0 处漂移。** 而且 `tests/test_docs.py` 把它做成了测试。
版本声明也有专门的检查器：

```bash
$ uv run --no-sync python scripts/check-version-claims.py --base auto
facts: tags v0.1.0..v0.1.3 / package version 0.1.3 / changelog 0.1.0..0.1.3
documents read: 20
findings: 0 (0 already in 4dd3ffc1)
Every version claim matches the repository.
```

**（4）`docs/analysis-provenance.md`（1224 行，中文）是这个仓库的招牌。**

它的 §3.3「provenance 没有记录什么」和 §6「读这份文档时会撞上的七处不一致」
（6 处标「已修」，1 处 `xrefs` 重复明确说「这是对的，但读表的人需要知道」）
是**主动交代自己短板的文档**。§7 给出复现文中每一个数字的命令。
在同类项目里几乎没有第二个这样做。

**（5）文档侧的实际问题。**

| 问题 | 位置 | 证据 |
| ---- | ---- | ---- |
| 旗舰报告的数字过期，**并因此让套件变红** | `docs/reports/phase1-execution-report.md` 的 `<!--fig:tests.total-->738<!--/fig-->` | 实测 773；`test_execution_report_numbers_match_the_code` 失败 |
| README 的测试数徽章是 v0.1.3 的历史数 | `README.md:12` `tests-444%20passing` | 实际 773。`check-version-claims.py` 放行是因为徽章允许「指向最后一个发布版」（`scripts/check-version-claims.py:1062-1078`），但读者看到的是 444 |
| README 的 xrefs 示例方法 id **缺返回类型**，照抄查不到 | `README.md:143` `"com.example.Foo.bar(Ljava/lang/String;)V"` | 实测输出「No callers of …」，退出码 1；正确的形式要带返回类型 `…Ljava/lang/String;` |
| CLI 退出码契约只写在 `--help` 里 | `cli/main.py:45-47` | `grep -i "exit code" docs/ README.md` 无结果 |
| 最有价值的两份文档只有中文 | `docs/status.md`、`docs/analysis-provenance.md` | `docs/install.md` 是英文，另两份是中文；README 有 zh-CN 版，但 provenance 文档没有英文版 |
| 退出清单声称 CI 是绿的 | `docs/roadmap/ROADMAP.md:171` | HEAD 上套件是红的 |

#### 要拿更高分需要做什么

1. **跑一次 `scripts/refresh-report-figures.py`（写回模式）**，把执行报告的数字更新到 773/653。
   顺手把 README 徽章从 444 改成实测值，并给徽章检查加一条「树里的数」的口径。
2. **修 `README.md:143` 的 xrefs 示例**，用完整的 JVM 描述符。
3. **把退出码契约写进 `docs/install.md` 和 README**——这是给 agent 用的一条重要契约。
4. **给 `docs/analysis-provenance.md` 出一份英文版**（或至少一份英文摘要），
   这是这个仓库面向 Upwork/外部审核者时最值钱的资产，不该只有中文。
5. **在 README 里加一句「默认工作区是相对路径」或干脆改成绝对路径**——
   新人第一次跑就遇到 Smali 而不是 Java，是最伤的体验。

---

### 3.6 GitHub / Upwork 展示价值 —— 5 / 10（权重 10%，加权 0.50）

> 这一节问的是一个很具体的问题：**现在把这个仓库拿给潜在客户/雇主看，说服力如何？**

#### 支撑证据

**（1）门面材料是齐的，而且比同阶段项目强。**

- **README 第一屏**：居中标题 + 状态横幅 + 6 个徽章 + 演示 GIF + 明确的
  「Nothing on this page claims a feature that does not yet run」。
- **演示资产三个**：`docs/assets/demo-quick.gif`（149 KB，README 首屏）、
  `demo.gif`（672 KB，完整会话）、`demo.mp4`（204 KB，同一批帧编码，声明「the two cannot drift apart」）。
- **中英双语 README**（`README.md` / `README.zh-CN.md`）。
- **许可证**：Apache-2.0，`LICENSE` 完整。
- **发布历史**：4 个 tag（v0.1.0–v0.1.3），`CHANGELOG.md` 遵守 Keep a Changelog 格式，
  每个版本有 `docs/releases/` 下的发布说明。
- **社区基建**：`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、
  `.github/ISSUE_TEMPLATE/`（bug + feature + config）、`PR_TEMPLATE.md`。
- **CI 矩阵是真的三档**，不是一档：
  - Python 3.12 + JADX + Apktool + Androguard（全量）
  - Python 3.13 **无 JADX**（3.13 环境无 Java）——专门测 Smali 回退
  - **只有 Apktool、没有 JADX** ——并在这个作业里显式断言
    `DEXATLAS_JADX_PATH=""` 且 `jadx` 不在 PATH 上，「这个作业否则会测错配置」

  `ci.yml` 里的注释写着：「how two tests that assumed JADX was installed stayed green in CI
  for as long as they did」——**这个仓库记得自己踩过什么坑**。
- **自建样本**：5 个 APK（demo / multidex / obfuscated / strings / wide），
  **smali 源文件一并提交**，`scripts/build-test-apks.sh` 可重建。
  README 明说「built from the smali sources committed beside it — not a staged recording」。

**（2）但买家最先看的两样东西，此刻都是错的。**

| 买家会看什么 | 此刻的状态 |
| ------------ | ---------- |
| CI 徽章 | **会是红的**（HEAD 上套件 1 失败，CI 跑全套件） |
| 测试数徽章 | `444 passing`，实际 773。点进仓库的人会数到 773 个测试 |
| 覆盖率徽章 | `94.0%` —— 实测 94%，**这个是对的** |
| README Quick start | 跑出来是 **Smali**，不是 Java；报告不解释原因 |
| 演示 GIF / 视频 | 录于 2026-10-20，此后代码有约 10 次提交。**我无法验证视频内容与当前代码一致** |

**（3）定位与交付物不匹配。**

`docs/roadmap/ROADMAP.md` 的 Portfolio strategy 明说：
「Lead with Agent engineering and Python backend; they map onto the broadest set of
OpenAI-compatible agent jobs」，并把 **「AI Agent Engineer」**列为第一个定位，
展示物是「Agent workflow recording + **MCP architecture diagram**」。

**而 Agent 编排与 MCP 是本项目做得最少的一块**（见 3.3：MCP 一行都没有，
agent 编排一行都没有）。现在这个仓库**没有任何东西**能展示成
「AI Agent Engineer」——展示物本身还不存在。README 自己诚实地写着
「Agent-ready architecture — the contract an AI agent will consume in Phase 2,
designed for it from the start」。

**诚实地说**：这个定位**不是谎言**（它说的是「为 Phase 2 而设计」），
但它也不能作为今天的展示物。一份写给 Upwork 雇主的介绍如果主打 Agent 工程，
对方点进来会发现 `src/dexatlas/mcp/` 不存在。

**（4）现在能不能拿去接活？**

**能接的活**（诚实的说法）：

- Android APK 静态分析相关的**脚本化/自动化**工作：能装、能跑、有 REST API、能出带出处的报告。
- 把 DexAtlas 当**一个可编程的分析内核**嵌进客户自己的流水线（这正是 README 的
  「the same analysis core is reachable from a CLI and a REST API」）。
- 有证据链的**初筛报告**产出（前提是客户接受「报告里有上限和截断」这件事被如实标注）。

**现在还接不了的活**：

- 任何需要 **MCP / agent 编排**的活（交付物不存在）。
- 任何需要 **Java 反编译作为主输出**的活（默认配置下它不工作）。
- 任何承诺**长期维护/生产 SLA**的活（`Development Status :: 3 - Alpha`，Phase 2 才进 `v0.5.0`）。
- 任何以**报告完整覆盖整个 APK** 为前提的活（两个静默截断上限）。

#### 要拿更高分需要做什么

1. **让 CI 变绿、让徽章写真值**——这是投入产出比最高的一件事。
   徽章是唯一每个潜在客户都会看的「自动生成的摘要」。
2. **修默认工作区的 JADX 路径**，并把演示视频用修复后的代码重录一遍。
   演示视频是 GitHub 上传播最广的资产，它必须是真的。
3. **把定位往后挪一格**：现在主打的是 **「Python 后端 & 自动化 + 移动应用安全」**，
   Agent 工程作为**路线图**讲，不作为**展示物**讲。
   `docs/roadmap/ROADMAP.md` 的 Portfolio strategy 表需要按这个原则重写。
4. **补一份「已知限制」的一页英文说明**，直接放在 README 折叠区：
   现在哪些上限会触发、触发时报告怎么说、哪些东西没被覆盖。
   这一页比再多一句「evidence-first」都更能说服技术面试官。
5. **把 5 个自建样本的重建脚本跑通并录进 README**——
   「clone → rebuild samples → analyze」全链路可复现，是这个仓库相对同类项目最强的差异点。

---

## 4. 加权总分（算给你看）

| 维度 | 分数 | × 权重 | = 加权分 |
| ---- | ---- | ------- | -------- |
| 核心功能与完整性 | 6 | × 0.25 | **1.500** |
| 软件架构与代码质量 | 6 | × 0.20 | **1.200** |
| Agent / MCP 工程 | 4 | × 0.20 | **0.800** |
| 测试、可靠性与安全 | 6 | × 0.15 | **0.900** |
| 文档与开发者体验 | 6 | × 0.10 | **0.600** |
| GitHub / Upwork 展示价值 | 5 | × 0.10 | **0.500** |
| | | **1.00** | **5.50 / 10** |

### 一句话结论

**5.50 / 10。**

这是一个**工程质量明显高于其完成度**的项目：安全边界扎实、测试是行为级的、
文档有自检工具链、provenance 文档是同类项目里少见的诚实。
但它现在处在「**功能清单齐全、默认路径有静默失效、权重第二高的交付物（Agent/MCP）
还不存在**」的状态。作为 Phase 1 的收官评估，这个分数说得很直白：
**Phase 1 的「地基本」是真的，但 Phase 1 的「验收」还没做完。**

### 分数分布的一个观察

加权总分 5.50 低于六个维度的**中位数 6**，因为**权重第二高的那一项（20%）拿了 4 分**——
而那一项的交付物（MCP server）根本不存在。
这说明**权重的分配和实际完成度是错配的**：项目把 20% 的评分权重放在一个
「Phase 2 才做」的交付物上，等于在 Phase 1 的评估里预扣了 1.2 分。
这不是项目的错——是这份路线图自己的评分协议在 Phase 1 的语境下需要修订
（要么把 Agent/MCP 那一维拆成「本阶段」与「下一阶段」两栏，要么把权重按阶段重分配）。

---

## 5. 「文档与代码不一致」清单

> 全部按 `b8ef71a` 核对。行号以 `git archive b8ef71a` 抽出的干净副本为准。
> 已在第 3 节展开的，此处只列条目与严重度。

### 5.1 高

| # | 位置 | 不一致 |
| - | ---- | ------ |
| 1 | `src/dexatlas/core/pipeline.py:497` | 声称「Apktool knows the manifest declaration, Androguard the DEX definition. Both are kept」——**Apktool 从不产出 `ClassRef`**（`pipeline.py:230` 恒空；`tools/apktool/adapter.py` 中 `ClassRef` 零命中）。真实的两个来源是 Androguard 与 JADX |
| 2 | `src/dexatlas/tools/base.py:3` | 「Backends are subprocess wrappers, never links」——**Androguard 是进程内库**，`tools/androguard/adapter.py:11-14` 自己承认是 "the one exception to the subprocess rule" |
| 3 | `src/dexatlas/core/storage.py:268` | 「Additive only.」——同一函数 `:284` 就 `DROP TABLE resources` |
| 4 | `src/dexatlas/core/ingest.py:6-7` | 「inspected through its *central directory* … rather than by decompressing it」——`_verify_entries`（`:155-173`）实际解压最多 256 MiB |
| 5 | `src/dexatlas/api/app.py:600-610` | `_rebuild_result` 不设 `duration_seconds` → **API 导出的报告写「Analysis time \| 0.0s」**（实测） |
| 6 | `docs/reports/phase1-execution-report.md` | `<!--fig:tests.total-->738<!--/fig-->` / `<!--fig:tests.fast-->618<!--/fig-->` vs 实测 773 / 653 → **使测试套件在 HEAD 上变红** |
| 7 | `src/dexatlas/config/settings.py:26` + `tools/jadx/adapter.py:237-241` | 默认工作区是相对路径 + `--output-dir` 与 `cwd` 同为相对路径 → JADX 输出写进双重嵌套目录，**报告与 CLI 均无察觉** |
| 8 | `README.md:143` | xrefs 示例的方法 id 缺返回类型，照抄**静默查不到** |
| 9 | `docs/roadmap/ROADMAP.md:171` | 退出清单 `[x] GitHub Actions green on Python 3.12 and 3.13`——HEAD 上套件是红的 |
| 10 | `src/dexatlas/core/storage.py:427` | 「symbol tables key on the symbol」——对 `xrefs`（`:157-163`）与 `strings`（`:165-171`）**不成立**（这两张表无主键；`analysis-provenance.md` §6.6 对此有说明，但代码注释没有） |

### 5.2 中

| # | 位置 | 不一致 |
| - | ---- | ------ |
| 11 | `src/dexatlas/core/evidence.py:31-32` | 「The report's evidence table shows 200 rows, so this leaves room for the class declarations in the same table」——实测 100 xref + 500 class = 600 条 vs 200 行表，class 行**溢出** |
| 12 | `src/dexatlas/core/evidence.py:192-193` | 把 xref 无证据**只**归因于「调用 JDK 方法」——漏了 100 条上限这个第二原因，`reports/markdown.py:31-35` 同样只给了一个解释 |
| 13 | `src/dexatlas/tools/base.py:246-252` | `_decode` 的截断告警分支**不可达**（`_read_capped` 已先截断）→ 后端 stdout 被裁剪时永远静默 |
| 14 | `src/dexatlas/tools/base.py:29-30` | 「Output that exceeds this is treated as a runaway backend rather than a result」——该常量 `_DEFAULT_MAX_OUTPUT` **零引用**，且实际行为是**静默截断**而非「当作失控后端」 |
| 15 | `src/dexatlas/tools/base.py:90` | 「Subclasses declare how to locate and probe their tool, then implement extraction」——基类**没有** `extract` 抽象方法，三子类签名互不相同 |
| 16 | `src/dexatlas/api/app.py:3-4` | 「No analysis behaviour is defined here, so the two interfaces cannot diverge」——API 对已分析 APK **去重**，CLI **不去重** |
| 17 | `src/dexatlas/core/models.py:462-476` | EvidenceLevel 的 LEAD / INSUFFICIENT 是模型输出的闸门——`src/` 中**无任何生产者**，报告恒为 0 |
| 18 | `src/dexatlas/tools/androguard/adapter.py:579,592` | locator 的字符串值截断到 64 字符，**同前缀长串碰撞**，文档未记载 |
| 19 | `src/dexatlas/core/storage.py:844` | 索引里的字符串名截断到 200 字符，未记载 |
| 20 | `src/dexatlas/tools/androguard/adapter.py:399-424` | 「method limit {limit} reached」——检查是**按类**做的，实际索引量可能超出一个类的量 |
| 21 | `src/dexatlas/core/paths.py:34-35` | 「rejects … **before** it splits into components」——代码 `:69` 先 split 后判空（行为等价，机制描述错） |
| 22 | `src/dexatlas/core/paths.py:20-21` | 「Windows caps it at the same number」（255 字节）——NTFS 限的是 255 个 **UTF-16 码元** |
| 23 | `src/dexatlas/core/pipeline.py:622` | `if not status: return`——JADX 什么都没产出时**报告完全不提**，但 Tool versions 行照旧列 `jadx 1.5.2` |
| 24 | `src/dexatlas/core/evidence.py:3-5` | 「Evidence ids are stable across re-analysis of the same APK」——仅在**后端集合完全相同**时成立；后端增减会让 `add_error` 之后的所有 id 位移 |
| 25 | `README.md:12` | 徽章 `tests-444 passing` vs 实测 773（该数字是 v0.1.3 的历史数） |
| 26 | `SECURITY.md:31` | 把「MCP surface」列为 in-scope——**项目没有 MCP** |
| 27 | `src/dexatlas/tools/jadx/adapter.py:116-127` | `method_status` 的 `False` 语义（「JADX 写了但反编译失败」）——失败的**构造器**与失败的**普通方法**混在同一张表里，`method_status("<init>")` 可能对不存在的构造器返回 `False` |

### 5.3 低

| # | 位置 | 不一致 |
| - | ---- | ------ |
| 28 | `src/dexatlas/tools/base.py:4` | 「a crashing or hangs engine」——拼写错误（hanging） |
| 29 | `src/dexatlas/tools/base.py:119` | `path_env_var: str = "DEXATLAS_<BACKEND>_PATH"`——字面占位符，不是模式；第四个后端若忘了覆盖就会打印这串字面量 |
| 30 | `src/dexatlas/cli/main.py:390-391` | 「JADX and Apktool must both be installed, and the APK re-analysed.」——**类根本不存在时**也打印同一句话 |
| 31 | `src/dexatlas/core/pipeline.py:107-110` | 「Every later failure is recorded on the project instead of raised.」——存储层的 `sqlite3.Error` **既不记录也不包装**，直接向上抛 |
| 32 | `docs/analysis-provenance.md`（中文） | 最有价值的一份资产**没有英文版**；`docs/status.md` 同 |

### 5.4 关于「文档里的数字是自动生成还是手写」

| 位置 | 自动生成？ |
| ---- | ---------- |
| `docs/reports/phase1-execution-report.md`（18 处数字） | ✅ `<!--fig:key-->value<!--/fig-->` 标记，由 `scripts/refresh-report-figures.py` 写入 |
| `docs/status.md`（3 处数字） | ✅ 同上 |
| `README.md:12` 的测试数徽章 | ❌ 手写，且已过期（444 vs 773） |
| `README.md:13` 的覆盖率徽章 | ❌ 手写，但**目前是对的**（94.0% = 实测 94%） |
| `docs/benchmarks/large-apk.md` 的数字 | ❌ 手写，但每条都附了生成它的命令（§7 有完整复现步骤）——这是合理的例外 |

---

## 6. 我没能验证的

> **凡是没有亲手验证的，一律在上面的评估里降权或标注。此节不许空。**

### 6.1 需要网络（完全没碰）

| 项 | 为什么没验 | 对分数的影响 |
| -- | ---------- | ------------ |
| **GitHub Actions 的真实运行状态与 CI 徽章** | 无 `github.com` 访问。**我只能推断**：HEAD 上套件 1 失败、`ci.yml` 跑全套件且该失败无 skip 条件 → CI 应为红。**但我无法确认最近一次 CI 实际运行的时间与结果** | 3.6 的「CI 徽章会红」标注为**推断**，未实测 |
| **仓库的 star / fork / issue / PR 数、可见性、release 页面** | 需要网络 | 3.6 未计入社区指标 |
| **`pip-audit` 的实际结果**（`ci.yml` 的 `security` 作业） | 需要 advisory 数据库 | 4 未引用依赖漏洞结论 |
| **`scripts/fetch-fixtures.sh`** 拉取的 `fixtures/apk/*.apk`（`Test-debug.apk`、`TestActivity.apk`、`AndroidManifest_ShortName.apk`） | 需要 `gh` API + token | 4 未用这些样本做验证 |
| **`docker build` + `docker run dexatlas backends`** | 需要拉基础镜像 + Java + JADX/Apktool | 3.6 的 Docker 一项**未实测** |

### 6.2 需要真实样本（没有）

| 项 | 为什么没验 | 对分数的影响 |
| -- | ---------- | ------------ |
| **真实商业 APK**（加固、含 native 库、大量资源） | 仓库里只有 5 个自建样本（都是手写 smali）与合成的大 APK。**没有真实 APK 可分析** | 3.1 的 4 分可信度受限；3.4 的「可靠性」分只覆盖合成样本 |
| **`docs/benchmarks/large-apk.md` 声称「the counts would be different; the behaviour of the limits would not」** | 无真实 APK 佐证。**这是文档的声称，不是我的验证** | 3.4 的基准分只在合成样本范围内成立 |
| **JADX 在 205,000 方法规模下的表现** | 基准文档明确说没测（`JADX_METHOD_CEILING`），我也没测——需要长时间 + 大量内存 | 3.4 未给该项加分 |

### 6.3 需要更多时间或资源

| 项 | 为什么没验 |
| -- | ---------- |
| **示例 APK 与提交的 smali 源是否逐字节一致** | 我没有跑 `scripts/build-test-apks.sh` 重建后逐个比对 |
| **演示 GIF / MP4 是否是当前代码跑出来的** | 视频录于 2026-10-20，此后代码有约 10 次提交。我**无法逐帧验证**。我只能验证：文件存在、`README.md:37-38` 声称 MP4 与 GIF 同帧所以不会漂移 |
| **`tools/androguard/adapter.py:523`/`:612` 两处静默捕获能否被真实 DEX 触发** | 机制确凿（代码路径可读），但我**没有构造出触发输入**。这两条降权处理：未计入「已证实缺陷」，只作为风险提示 |
| **并发行为**（多进程同时写同一工作区、SQLite 锁竞争） | 未测。`api/app.py:322` 的 `running` 悬挂与 `core/storage.py` 的写入路径都与并发相关，但本次是单进程实测 |
| **REST API 的鉴权与限流** | **不存在**，无法测（`docs/install.md:180` 明确说明用反向代理解决） |
| **Python 3.13 下的行为** | 本机只有 3.12。CI 有 3.13 作业，但那是「无 JADX」的配置，且我看不到它的运行结果 |
| **Linux / macOS 下的行为** | **本次全部实测在 Windows 11 上。** `tools/base.py:315` 按 `os.name` 在 `_taskkill_tree`（Windows，`taskkill /T`）与 `_kill_process_group`（POSIX，`:320`）之间分派，**POSIX 分支未实测** |
| **`examples/` 下 5 个 APK 的深度反编译质量** | 只跑了 `demo.apk` 的完整流水线；其余 4 个（multidex / obfuscated / strings / wide）只在测试套件里被间接覆盖 |

### 6.4 方法本身的局限

- **行号引用基于 `git archive b8ef71a` 的干净副本**，而**当前工作区已被并行会话改动**
  （`src/dexatlas/api/app.py`、`src/dexatlas/core/storage.py` 两个文件 `M`）。
  如果这些改动被提交，本文的行号会位移。
- 我在 `check-doc-citations.py` 上观察到的「2 处漂移」**属于并行改动，不是 HEAD 缺陷**，
  已在 1.4 说明，未计入第 5 节。
- **变异测试只做了 2 处**（路径守卫、索引完整性披露）。全部 773 个测试的完整变异评分
  **未做**——那需要数小时。
- 我的「文档与代码不一致」清单覆盖了 `src/dexatlas/` 的全部 19 个模块与 `docs/` 的全部 5 份文档，
  但**没有**逐字复核 `CHANGELOG.md`、`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、
  `docker-compose.yml`、`Dockerfile` 的每一条声称。

---

## 7. 给 Phase 2 的输入（浓缩版）

按「能不能被外部审核者直接看见」排序。前四项做完，套件变绿，README 可信度立刻上一个台阶。

| 优先级 | 事项 | 出处 |
| ------ | ---- | ---- |
| P0 | 跑 `scripts/refresh-report-figures.py` 写回，把执行报告的数字更新到 773/653；同步 README 徽章 | 3.4(1)、3.5 |
| P0 | 修 JADX 的 `--output-dir` / `cwd` 相对路径问题（把默认工作区改绝对路径，或让 adapter 用绝对路径），并补一个**用相对工作区跑真实 JADX** 的集成测试 | 3.1(2) |
| P0 | 给 `MAX_EVIDENCE_CLASSES`（500）与 `MAX_EVIDENCE_CALLED_METHODS`（100）加披露；补 `_XREF_NOTE` 的第二个归因 | 3.1(3) |
| P0 | 修 `_rebuild_result` 的 `duration_seconds`——导出的报告不能写 0.0 | 3.1(4) |
| P1 | 实现 locator → 路径的解析器；加 `dexatlas evidence` 子命令（带过滤与 `--json`） | 3.3 |
| P1 | 修 5 处「文档说 A、代码做 B」（`base.py:3`、`storage.py:268`、`ingest.py:6`、`pipeline.py:497`、`storage.py:427`） | 3.2(3) |
| P1 | 清死代码（`SubmitResponse`、`java_available`、`coerce`、`_DEFAULT_MAX_OUTPUT`、`rizin_path`/`ghidra_path`、`cache_dir`） | 3.2(4) |
| P1 | Androguard 的两处 `logger.debug` 改成 `ToolError` | 3.1(5) |
| P2 | REST API 的 9 个 untyped 端点补 response model + 分页 | 3.3 |
| P2 | 退出码契约写进 README 与 `docs/install.md`；修 README 的 xrefs 示例；出 `analysis-provenance.md` 英文版 | 3.5 |
| P2 | 修 `api/app.py:322` 的 `running` 悬挂；`SECURITY.md:31` 去掉不存在的 MCP surface | 3.4(6) |
| P2 | 按「现在真的有的东西」重写 Roadmap 的 Portfolio strategy 一节 | 3.6 |
| P3 | 把 Roadmap 评分协议按阶段拆分（见 4 的观察） | 4 |
