# 证据包的隔离边界 —— 核过什么，改了什么

> **性质：核对 + 实施。** 这份报告核对了「`dexatlas export` 打的证据包里到底会被
> 打进什么」，把「哪些路径永远不该进包」写死，并**实施了**一道打包时的守卫和它的
> 红→绿回归测试。
> 核对日期：2026年11月18日 · 引用基线：commit `3e943b5` ·
> 工作树：`.claude/worktrees/elastic-mirzakhani-800d7d`（分支 `claude/elastic-mirzakhani-800d7d`）
>
> **一句话结论：** 候选 C10 说的那条通路**今天不成立**——包里的源码片段只可能来自
> 被分析 APK 的反编译树，`docs/outreach/publish-review.md` 这类内部核对记录**进不去**；
> 但这条性质**只靠实现细节成立**，代码里没有任何一处写明它、检查它、或者在清单里
> 声明它。已经补上：打包时多一道守卫（反编译树之外的文件、指向树外的链接都不进包），
> 加上契约文档里的明文与 5 条红→绿回归测试。

---

## 0. 这次要回答的问题

候选 C10 的原话是：**内部核对记录不得随证据包外发**。要落地这句话，得先回答三件事：

1. 证据包**实际**会被打进什么？（不是「应该」打什么）
2. 「内部核对记录」在路径上长什么样，**哪些路径永远不该进包**？
3. 怎么把这条从「靠实现细节」变成**可执行的断言**？

本文按这个顺序回答。先核事实，再下判断，最后才是改法。

## 1. 核到的事实

### 1.1 包里到底有什么

`dexatlas export` 的实现只有一条路：`src/dexatlas/cli/main.py:855` 的 `export`
命令 → `src/dexatlas/cli/main.py:890` 调 `build_evidence_package`。
没有第二条路：全仓只有这一处调用它（`grep build_evidence_package src/` 只命中
`cli/main.py:64` 的 import 和 `cli/main.py:890` 的调用）。

`build_evidence_package`（`src/dexatlas/reports/evidence_package.py:102-152`）写进
归档的是：

| 条目 | 来源 | 位置 |
|---|---|---|
| `reports/report.json` | `build_json_report(result)` | `evidence_package.py:117-119` |
| `reports/report.md` | `render_markdown(result)` | `evidence_package.py:120` |
| `reports/report.html` | `render_html(result)` | `evidence_package.py:121` |
| `sources/<相对路径>` | `_cited_sources(...)` | `evidence_package.py:122-123` |
| `manifest.json` | 清单本身（不列进自己的文件数组） | `MANIFEST_NAME`（`evidence_package.py:73`）、清单写入 `evidence_package.py:144-150` |

### 1.2 谁决定收不收

**决定权在 `_cited_sources`**（`src/dexatlas/reports/evidence_package.py:196-252`），
规则只有三条：

1. 只有 **`jadx:` 前缀**的定位符才可能被收（`evidence_package.py:215`）；
2. 定位符的相对位置必须是一条**安全相对路径**（`evidence_package.py:218` →
   `_is_a_safe_relative_path`，`evidence_package.py:436-450`）；
3. 文件从 **`<workspace>/jadx/<相对位置>`** 读出来（`evidence_package.py:232`），
   复制成 `sources/<去掉 sources/ 或 resources/ 前缀后的路径>`（`evidence_package.py:250`）。

`workspace` 是这次分析自己的目录：`src/dexatlas/core/pipeline.py:186`
（`settings.projects_dir / project.id / "runs" / run.id`），
JADX 的输出树是它下面的 `jadx/`（`pipeline.py:279`、`pipeline.py:682`、`pipeline.py:743`）。
分析的**输入**是 APK（`src/dexatlas/cli/main.py:322-344`，`analyze` 的参数是 APK 路径）。

**所以：打包器唯一的输入根目录是 `<workspace>/jadx/`，而那棵树上只有被分析 APK 的
反编译产物。**

### 1.3 用真实产物核一遍

不是读代码推的，是把包打开数条目：

**仓库里现成的四个证据包**（`docs/case-studies/attachments/*.zip`）——
逐个 `zipfile.namelist()`：

| 包 | 条目数 | `sources/` 条目 |
|---|---|---|
| `api-integration-evidence-package.zip` | 4 | **0** |
| `demo-evidence-package.zip` | 4 | **0** |
| `multidex-evidence-package.zip` | 4 | **0** |
| `obfuscated-evidence-package.zip` | 4 | **0** |

四个包里都只有三份报告 + `manifest.json`。`manifest.json` 的形状（读
`demo-evidence-package.zip` 的清单）：

```json
{
  "schema_version": 1,
  "project_id": "apk_80a8fe0e81204c9f",
  "apk_sha256": "80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9",
  "run_id": "run_e8e49384ab5246ab",
  "package_generated_at": "2026-11-17T18:31:11.628317+00:00",
  "tool_versions": {"jadx": "1.5.2", "apktool": "2.11.1", "androguard": "4.1.4"},
  "files": [ … 三份报告，每份带 path/sha256/bytes/role … ],
  "not_included": {
    "apk": "the analysed APK is not packaged; identify it by its SHA-256",
    "full_sources": "only the source fragments the evidence cites are packaged",
    "unrelated_strings": "string constants that no evidence record cites are not packaged"
  }
}
```

**本轮现跑的一个包**（第一方样本 `examples/demo-app/demo.apk`，JADX 1.5.2 +
Apktool 2.11.1，`DEXATLAS_WORKSPACE` 指向本工作树的 `.scratch/workspace`）：

```
$ uv run --no-sync dexatlas analyze examples/demo-app/demo.apk
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string
$ uv run --no-sync dexatlas export apk_80a8fe0e81204c9f -o .scratch/out/demo-package.zip
✓ evidence package → .scratch\out\demo-package.zip (4 files: 3 reports + 1 manifest, …)
```

包里同样**没有任何 `sources/` 条目**。

**为什么没有？** 查了该次分析的全部证据记录的定位符，工具分布是
`androguard: 11`、`apktool: 2`、`jadx: 1`，而那唯一一条 `jadx:` 是
`jadx:sources`——**整棵树的裸定位符**（覆盖率观察记录，
`src/dexatlas/core/pipeline.py:1398`），它背后没有一个文件，所以
`_cited_sources` 什么也复制不到。

文件级的 `jadx:` 定位符确实存在，但只出现在**源码文档**（API 的
`/source` 响应）上，不在证据记录上：`src/dexatlas/core/pipeline.py:751`
与 `src/dexatlas/core/pipeline.py:836`。因此：

> **`sources/` 这条通路在当前的流水线里是休眠的**——没有任何一条真实分析产生的
> 证据记录会点名一个 `jadx:` 的具体文件。

### 1.4 已经有的防线

- `_is_a_safe_relative_path`（`evidence_package.py:436-450`）拒绝 `..`、绝对路径、
  Windows 盘符、反斜杠、NUL。所以 `jadx:../../docs/outreach/publish-review.md`
  这种定位符在到达读取之前就被挡住了。
- `_check_names`（`evidence_package.py:374` 起）拒绝归档里带路径穿越的条目名，
  并逐文件核对 sha256。

### 1.5 没有的防线

两处，都是同一种毛病——**没有确认这个文件确实是分析的产物，就把它复制出去了**：

1. **链接不解析。** `evidence_package.py:233` 的 `source.is_file()` 与
   `evidence_package.py:250` 的 `read_bytes()` 都跟随符号链接。反编译树里一个指向
   树外的链接，会被当成「分析的一个源文件」原样复制进包。
2. **目录本身不是边界。** 只要定位符点名了 `<workspace>/jadx/` 下的任何**文件**，
   它就会进包——包括反编译器根本没写过的文件（JADX 只写 `sources/` 与 `resources/`
   两棵树；实测本轮那棵树上确实只有这两个目录）。

值得对照的是：**这个项目在别处都做了这道检查。**
`is_inside`（`src/dexatlas/core/paths.py:140-152`，「链接已解析」）用在
`src/dexatlas/tools/jadx/adapter.py:337`、`src/dexatlas/tools/apktool/adapter.py:640`、
`src/dexatlas/mcp/security.py:75`（那里自称「同一扇门上的第二把锁」）。
**打包器是唯一一个把文件从分析目录复制出去、却没检查这个文件是否在分析目录之内的读点**——
而它恰好是唯一一个复制给**客户**的那个。

## 2. 判断

### 2.1 候选 C10 说的那条通路，今天不成立

「报告里引用的代码片段可能来自内部核对记录」——按 §1.1–1.3 核到的，这条通路今天
**走不通**：源码片段只能来自 `<workspace>/jadx/`，那棵树里只有被分析 APK 的反编译
产物；分析的输入是 APK，不是仓库；仓库里的 `docs/outreach/publish-review.md` 与
分析工作区没有任何路径关系。

**这不是「没有漏洞」，而是「漏洞被别的事实挡住了」**——挡住它的是「JADX 只往那里写
反编译产物」这个实现细节，不是任何一条声明或检查。

### 2.2 真正的缺口：边界只靠实现细节

三条支撑这个判断：

1. **没有写死。** `evidence_package.py` 的模块 docstring 原来只说「包里有什么、
   没有什么」（APK、全量源码、未被引用的字符串），没有一句说「包里只有本次分析」。
2. **没有检查。** 全仓没有任何一处断言「包里的每个文件都来自分析」。
3. **没有声明。** 清单的 `not_included` 三键（`apk` / `full_sources` /
   `unrelated_strings`）没有一条说到内部核对记录、未发布素材或工作材料。

只要有人把打包器的输入根目录放宽一点（为了「顺手把评审记录一起发过去」，
或者为了把 `resources/` 之外的什么一起带上），包里就会开始装进机器上的东西，
而**没有任何一道闸会响**。这就是 C10 值得做的地方。

### 2.3 哪些路径永远不该进包（范围写死）

| 类别 | 例子 | 为什么永远不该进包 | 现在靠什么挡 |
|---|---|---|---|
| 操作者自己的仓库与工作材料 | `docs/**`（含 `docs/outreach/publish-review.md`）、评审记录（`*-review.md`）、核对清单、未发布素材、`.git/**`、`.env`、任何 secret | 这些是**分析之外**的东西；证据包是给客户看的交付物 | **新增规则 1**：文件必须在分析工作区之内（链接已解析） |
| 反编译树里非反编译产物 | `<workspace>/jadx/` 根部或第三层目录下的文件 | 反编译器只写 `sources/` 与 `resources/` 两棵树；别的东西是**被人放进去的** | **新增规则 2**：文件必须在 `sources/` 或 `resources/` 之下 |
| 被分析的 APK 本身 | `demo.apk` | 包按 SHA-256 标识它，不携带它 | 既有：`not_included.apk` |
| 全量源码树 | `jadx/sources/**` 整棵树 | 包只带被引用到的片段 | 既有：`not_included.full_sources` |
| 未被证据引用的字符串常量 | 常量池里的其余字符串 | 与结论无关 | 既有：`not_included.unrelated_strings` |

前两行是这次新增的；后三行是既有声明，**没有改动**。

## 3. 改法（已实施）

### 3.1 打包时的守卫

`src/dexatlas/reports/evidence_package.py` 新增 `_why_not_an_analysis_file`
（`evidence_package.py:254-277`），在 `_cited_sources` 复制之前问两个问题，
两个都得是「是」：

1. **文件在反编译树之内吗？**（`is_inside`，链接已解析）——树里的链接指向树外，
   一律不算分析的产物；
2. **它在反编译器写的两棵树之一之下吗？**（`sources/` 或 `resources/`，
   常量 `_DECOMPILER_TREES`，`evidence_package.py:67`）

不满足就不复制（`evidence_package.py:238-249`），并**说出是哪一条不满足**
（`logger.warning`）。引用仍留在证据里，`verify_citations`
（`evidence_package.py:302`）会把它记成未解析——读者跟着引用找不到文件时，
看到的是「没带」而不是「带了个假的」。

模块 docstring 也补上了这条边界（`evidence_package.py:14-20`）。

### 3.2 契约文档

`docs/architecture/public-contracts.md` §5.3 补了一段明文：包内只有本次分析，
被引用的源码片段必须是分析自己的反编译产物（`docs/architecture/public-contracts.md:319-322`）。
该文件里指向 `evidence_package.py` 的 5 处行号引用随本次源码改动重新推导
（`scripts/remap-citations.py` 对模块级常量无能为力，按其文档说明交由人判断，
人已改；`scripts/check-doc-citations.py` 现在报「Every citation still says what it says」）。

### 3.3 红→绿回归测试

新增 `tests/test_evidence_package_isolation.py`，5 条：

| 测试 | 断言 |
|---|---|
| `test_the_decompiler_output_the_evidence_cites_is_packaged` | 分析自己的文件**照旧进包**（边界不是墙） |
| `test_a_record_planted_in_the_decompiler_directory_is_not_packaged` | 反编译树里被放进来的内部核对记录**不进包** |
| `test_a_link_out_of_the_analysis_is_not_packaged` | 指向树外的链接**不进包**（用真的 `docs/outreach/publish-review.md` 式内容当载荷） |
| `test_a_refused_citation_is_reported_as_unresolved` | 被拒的引用**记为未解析**，不是被假装带上了 |
| `test_every_file_in_the_package_is_the_analysis_and_nothing_else` | 归档里的条目集合**逐条等于**「三份报告 + 清单 + 分析自己的文件」 |

**红→绿证据**（CLAUDE.md 规则 1：旧实现下必须变红）：

```bash
# 把守卫摘掉（reason = None），其余不动：
$ uv run --no-sync pytest tests/test_evidence_package_isolation.py -q
FAILED tests/test_evidence_package_isolation.py::test_a_record_planted_in_the_decompiler_directory_is_not_packaged
FAILED tests/test_evidence_package_isolation.py::test_a_link_out_of_the_analysis_is_not_packaged
FAILED tests/test_evidence_package_isolation.py::test_every_file_in_the_package_is_the_analysis_and_nothing_else
3 failed, 2 passed in 1.22s
```

旧实现的具体表现（红的那两条的断言原文）：

```
AssertionError: assert 'sources/internal-notes.md' not in {'manifest.json', 'reports/report.html',
  'reports/report.json', 'reports/report.md', 'sources/com/example/demo/Crypto.java',
  'sources/internal-notes.md'}
AssertionError: assert {'manifest.js...sh-review.md'} == {'manifest.json', …, 'sources/com/example/demo/Crypto.java'}
  Extra items in the left set: 'sources/publish-review.md'
```

即：**旧实现把操作者的内部核对记录原样复制进了给客户的包**（`sources/publish-review.md`），
以及**把指向树外的链接当成了分析的源文件**（`sources/internal-notes.md`）。
把守卫放回去，5 条全绿。

## 4. 清单里应该声明什么

**现状**：`not_included` 三键被三处钉死——
`tests/test_public_contracts.py:740`（集合相等）、
`scripts/m10_selfcheck.py:591`（**阻塞级**自检）、
`docs/architecture/public-contracts.md:316`（契约文档）。
清单的整体形状也被 `tests/test_public_contracts.py:170-179`
（`EXPECTED_PACKAGE_MANIFEST_FIELDS`）钉死。

因此两条路，代价不同：

| 方案 | 改什么 | 代价 | 我的建议 |
|---|---|---|---|
| **A. 加第四个 `not_included` 键** | 例如 `"internal_records": "操作者自己的评审记录、工作文档与未发布素材一律不进包"` | 清单**形状变了**：`PACKAGE_SCHEMA_VERSION` 需从 1 升到 2（`evidence_package.py:50`），并同步改 `docs/architecture/public-contracts.md:316`、`tests/test_public_contracts.py:740`、`scripts/m10_selfcheck.py:591`，以及 M10 验收材料里「`not_included` 三键」的判据（`docs/reports/m10-acceptance-pack.md:128`） | **不建议在这一轮做**：这是公共契约变更（CLAUDE.md 规则 5），影响面远大于它覆盖的风险，而且**执行侧的守卫不依赖它** |
| **B. 只改 `full_sources` 的措辞** | 例如改成「only the source fragments the evidence cites are packaged, and only from the analysis's own decompiler tree」 | 键集合不变 → M10 自检与契约文档的键列表都还成立；但 `tests/test_evidence_package.py:305` 钉的是整段字面量，要同步改；仓库里四个已入库包的清单带的是旧措辞（历史产物，非破坏） | **可以接受**，但它是「契约文本变更」，仍应进 CHANGELOG |

**这一轮实际做了什么**：**没有动清单**（形状、键集合、措辞一字未改），
把边界写在了**能被执行的地方**（打包时的守卫）、**契约文档**（§5.3 明文）
和**测试**（5 条红→绿）上。

理由：清单是给读者看的**声明**，而读者拿到包时，包里已经是对的了——
声明的作用是让读者知道边界在哪，而不是让边界成立。把边界写进执行侧，
既不花契约变更的代价，也不会因为「文档写了、代码没做」而变成一句空话。
方案 A 留作一次独立的契约变更，由主会话决定（它会牵动 M10 验收材料）。

## 5. 还有什么没核实、为什么

| 未核实的 | 为什么 |
|---|---|
| **四个已入库包的来源** | 只读了它们的条目与清单，没有重跑一遍来复现字节一致。它们的 `package_generated_at` 是 2026-11-17，仓库里没有生成它们的脚本（案例入库记录说是手工跑的），字节级复现不在本次范围内 |
| **本次改动的完整套件与重新测量** | 按任务约束**没有跑** `scripts/refresh-report-figures.py`（主会话正在测量），也**没有跑完整套件**。因此本工作树里 `docs/reports/phase1-execution-report.md` 的数字（测试数 1695→1700、快慢两段划分、源指纹、`reports/evidence_package.py` 的语句数 172→187）**当前是过期的**，`tests/test_docs.py` 的 5 条测量类断言现在是红的，**要等主会话重新测量才会恢复**。已按 `refresh-report-figures.py` 的要求补了**手写的那一行测试文件表**（`docs/reports/phase1-execution-report.md:243`，脚本本身不写表头行，缺这一行它会拒绝写任何数字） |
| **`tests/test_evidence_package.py::test_the_cli_counts_the_files_the_reader_finds_in_the_zip`** | 这条在**未改动的 HEAD 上也红**（已用 `git show HEAD:…` 换回原文件验证过）：本工作树路径太长，Rich 把 CLI 输出的「1 source fragment」折行了，断言找的是不换行的字符串。与本次改动无关，未修 |
| **符号链接测试在无链接权限的机器上** | Windows 上创建符号链接需要开发者模式或相应权限。本机（已开开发者模式）与 CI（`ubuntu-latest`，全部 `runs-on`）都能建；建不了时**只有这一条**会 skip，而可移植的那条（树内非产物文件）不依赖链接，红→绿证明不靠它 |
| **API 的导出路径** | `/projects/{id}/report`（`src/dexatlas/api/app.py:806-817`）只渲染 JSON/Markdown 报告，不产包；全仓也只有 `cli/main.py:890` 一处建包（MCP 服务不建包）。因此没有第二条打包路径需要同样的守卫 |
| **未来会不会有别的通路把内部材料带进包** | 本次只能核到**当前**的代码。若以后增加「把评审记录一起发给客户」这类功能，需要在那个功能里复用这条边界，而不是另起一套——本报告 §2.3 的范围表就是那条边界的书面形式 |

## 6. 复现方式

```bash
# 看一个真包里有什么
python -c "import zipfile;print('\n'.join(zipfile.ZipFile('docs/case-studies/attachments/demo-evidence-package.zip').namelist()))"

# 跑一次真的分析 + 导出（JADX/Apktool 需在 PATH 或用 DEXATLAS_JADX_PATH / DEXATLAS_APKTOOL_JAR 指路）
DEXATLAS_WORKSPACE=$PWD/.scratch/workspace \
  uv run --no-sync dexatlas analyze examples/demo-app/demo.apk
DEXATLAS_WORKSPACE=$PWD/.scratch/workspace \
  uv run --no-sync dexatlas export apk_80a8fe0e81204c9f -o .scratch/out/demo-package.zip

# 跑这道检查
uv run --no-sync pytest tests/test_evidence_package_isolation.py -q
```

## 7. 这对「证据包是给客户看的」意味着什么

一句话：**证据包是交到客户手里的东西，所以它必须是「分析」，不能是「分析 + 这台机器上
我们自己的东西」。**

今天它已经是前者的——但那是**碰巧**的：靠的是「JADX 只往那棵树上写反编译产物」
这个实现细节，没有任何一处代码、文档或清单声明过它。现在它**被声明了、被检查了**：
打包器在复制之前会问「这是不是分析自己的文件」，不是就不带，并且说明是哪一条不满足；
契约文档 §5.3 写着这条边界；5 条测试钉住它，其中 3 条在旧实现下会红。

对读者的实际含义：拿到包的人可以放心——**包里没有我们的评审记录、没有未发布的素材、
没有本机路径**，如果他跟着某条引用找不到文件，那是因为分析里没有那个文件，而不是
因为包里混进了别的东西。
