# 分析覆盖度与证据来源

**这份文档回答一个问题：一条结论，到底是谁、用哪个版本的工具、在哪份 APK 的哪个位置上得出的。**

它不是架构说明。[`docs/architecture/README.md`](architecture/README.md) 讲的是「代码怎么组织、
为什么这么组织」；这份讲的是「哪些结论可信、依据是什么、哪些情况下不可信」。

文中每一条说法都指向具体的 `文件:行号`，或者下面第 4 节里跑出来的真实输出。
**没有跑过、也没读过代码的地方，这里不写。**

---

## 1. 覆盖度总表：每类结论由谁产出

DexAtlas 目前有 3 个分析后端（`src/dexatlas/tools/registry.py:19-20`）加 1 个不依赖任何后端的
APK 检查步骤。它们的产出范围**基本互不重叠**——唯一的交叉是**类**：
Androguard 和 JADX 会为同一个类各产出一条 `ClassRef`（第 2 节讲两条怎么合并）。
方法表里的 `decompiled` 标志是另一回事：那是 JADX 给 Androguard 产出的方法补的一个
**状态**，不是第二份方法。下面会说清楚：

| 结论类型 | 产出后端 | 落在哪里 | 代码位置 |
|---|---|---|---|
| APK 哈希、大小、DEX 文件列表、原生库、是否有签名证书 | 无（纯标准库） | `ApkMetadata` | `core/ingest.py:51-77` |
| manifest（包名、版本、SDK、权限、组件） | **Apktool** | `ManifestInfo` | `tools/apktool/adapter.py:102-196` |
| manifest 的版本号 / SDK（Apktool 把它挪走了，从 `apktool.yml` 补） | **Apktool** | `ManifestInfo` | `tools/apktool/adapter.py:289-320` |
| 类的身份、种类、父类、接口、访问标志 | **Androguard** 与 **JADX** 各产出一条，合并规则见第 2 节 | `ClassRef` | `tools/androguard/adapter.py:263-274` |
| 类的**源码表示**（Java 或 Smali） | **JADX** 优先，**Apktool** 回退 | 工作区文件，按需读取 | `core/pipeline.py:291-321` |
| 方法（签名、描述符、访问标志） | **Androguard**（唯一） | `MethodRef` | `tools/androguard/adapter.py:336-350` |
| 方法**是否被反编译成 Java** | **JADX**（唯一） | `MethodRef.decompiled` | `tools/jadx/adapter.py:320-373` |
| 字段 | **Androguard**（唯一） | `FieldRef` | `tools/androguard/adapter.py:276-287` |
| 交叉引用（调用边） | **Androguard**（唯一，遍历字节码得到） | `MethodReference` | `tools/androguard/adapter.py:362-372` |
| 字符串常量 | **Androguard**（唯一，取自 DEX 字符串池） | `StringConstant` | `tools/androguard/adapter.py:432-458` |
| 字符串常量**出现在哪** | **Androguard**（遍历字节码时记录 `const-string` 的引用点） | `StringConstant.class_name` / `method_name` | `tools/androguard/adapter.py:432-458` |
| 资源（`res/`、布局、字符串表） | **没有人** | 不在模型里 | 见 5.4 |

几条需要注意的推论：

- **JADX 不产出方法、字段、交叉引用里的任何一条。** JADX 后端只产出 `ClassRef`
  （`tools/jadx/adapter.py:269-276`）。方法表、字段表、交叉引用表 100% 来自 Androguard。
  **JADX 在方法上的唯一贡献是 `decompiled` 这个标志**：它是 JADX 对「这个方法我反编译出来了」的
  回答，被记在 Androguard 产出的那一条方法上（`core/pipeline.py:442-459`）。
  它是**状态**，不是结构——方法的签名、描述符、访问标志仍然全部来自 Androguard。
- **Apktool 不产出任何符号。** 它产出 manifest 和 Smali 文件；Smali 是**按需读取**的，
  不进索引、不进证据表（`core/pipeline.py:291-321`）。
- **资源没有覆盖。** Apktool 会把 `res/` 解码到工作区，但 `src/` 里没有任何代码读它
  （`grep -rn "res/values\|resources" src/` 只命中 `ingest.py:15` 的文件名常量
  `resources.arsc` 和它的错误消息（`ingest.py:44`），以及 Apktool
  模块自己提到 resources 的 docstring——**没有一处是读 `res/`**）。
  这一条在 5.4 里展开。

---

## 2. 冲突时谁说了算

只有一类结论有两个后端都看得到：**类**。Androguard 从 DEX 定义读到一个类，JADX 从它写出的
`.java` 文件读到同一个类。合并规则写在 `core/pipeline.py:356-380` 的 `_merge_classes` 里，
不是「谁后跑谁覆盖」：

| 字段 | 规则 | 实际效果 |
|---|---|---|
| `kind`（class/interface/enum/annotation） | 新值是 `class`（最笼统的一种）时保留先到的；新值更具体时取新值 | **更具体的那个赢**。实际是 **JADX 说了算**（它后跑）——只有 JADX 说 `class` 时才轮到 Androguard |
| `superclass` | `existing.superclass or cls.superclass` | **Androguard 说了算**（它先跑） |
| `interfaces` | 两个集合的并集 | 两边都保留 |
| `access_flags` | 两个集合的并集 | 两边都保留 |
| `method_count` / `field_count` | `max()`（**只是视图**） | 合并阶段取较大值；**落库时按 `methods` / `fields` 表的实际行数重算**，所以表里的数永远等于查询返回的行数 |
| `provenance` | 拼接 | **两条都留**，谁也不覆盖谁 |

合并的**顺序**就是执行顺序：Apktool → Androguard → JADX
（`core/pipeline.py:132-141`、`core/pipeline.py:143-151`、`core/pipeline.py:153-169`）。Apktool 不产出 `ClassRef`，
所以真正参与合并的只有 Androguard（先）和 JADX（后）。

Androguard 先跑不是因为它更重要，是因为它是**结构**的正确来源（`docs/architecture/README.md`
里说的「a decompiler's text output is the wrong source for structure」）。但代码里的实际
依据分两种：`superclass` 靠 `or` 短路——先到的非空值就赢；`kind` 靠一条**专门的规则**
——`existing.kind if cls.kind.value == "class" else cls.kind`，
即**更具体的那个赢**，`class` 只是兜底。
**所以「谁后跑谁说了算」对 `superclass` 成立，对 `kind` 不成立**：
JADX 报 `interface` 时结果是 `interface`，哪怕 Androguard 报的是 `class`；
反过来 JADX 报 `class` 而 Androguard 报 `interface` 时，结果是 `interface`。
仓库自己的测试就锁住了这条：`test_merge_prefers_the_more_specific_kind`
（`tests/test_evidence.py:439-449`）。

实测（`apk_a488e43e38c2b8e9`，`SharedConfig` 同时存在于两个 DEX）：

```json
"provenance": [
    {"tool": "androguard", "tool_version": "4.1.4",
     "locator": "androguard:classes.dex#com.example.multidex.SharedConfig"},
    {"tool": "androguard", "tool_version": "4.1.4",
     "locator": "androguard:classes2.dex#com.example.multidex.SharedConfig"},
    {"tool": "jadx", "tool_version": "1.5.2",
     "locator": "jadx:sources/com/example/multidex/SharedConfig.java"}
]
```

三个来源，一条都不丢。**没有「优先后端」这个概念——只有「每一类结论归谁」。**

**还有一处不是「冲突」，是分工：** `MethodRef.decompiled`（这个方法有没有被反编译成
Java）只有 JADX 知道，Androguard 读 DEX 根本答不了这个问题。所以这条标志是
**JADX 写、Androguard 的那条方法上记**（`core/pipeline.py:442-459`）。
它不是结构，合并规则对它不适用：方法表里没有第二个来源跟它抢。

---

## 3. provenance 具体记录了什么

### 3.1 字段

`Provenance` 定义在 `src/dexatlas/core/models.py:89-121`，只有四个字段：

| 字段 | 类型 | 含义 | 谁填的 |
|---|---|---|---|
| `tool` | `str` | 后端名（`jadx` / `apktool` / `androguard`） | `tools/base.py:205` |
| `tool_version` | `str \| None` | 后端版本字符串 | `tools/base.py:206` → `Backend.version()` |
| `apk_sha256` | `str` | 被分析 APK 的完整 SHA-256 | 调用方传入 |
| `locator` | `str` | 指回源头的指针，形状是 `<后端名>:<相对路径>`（见 3.2） | 各 adapter 自己拼 |

`Sourced`（`models.py:123-135`）是混入类，给所有可追溯的产物加上 `provenance: list[Provenance]`。
注意是**列表**：一个产物可以有多个来源（见第 2 节）。

还有一个项目级的版本表 `Project.tool_versions: dict[str, str | None]`
（`models.py:416`），记录这次分析实际用到的三个后端版本，存进 `projects.tool_versions`
（`core/storage.py:73`）。它和 `provenance.tool_version` 是**两份独立的数据**——
管道把同一份版本表交给证据构造器（`core/pipeline.py:118-124`），
所以两份数据现在说的是同一件事。

### 3.1.1 交叉引用自己带的信息：调用方式

`MethodReference` 除了 `caller` 和 `callee`，还有一个 `kind` 字段，**说的是这条调用
边是怎么发起的**：`virtual`（虚调用）、`super`（父类调用）、`direct`（直接调用）、
`static`（静态调用）、`interface`（接口调用），以及 `invoke`——opcode 认不出来时
的兜底。

Dalvik 有好几种调用方式，它们在字节码里是**不同的指令**，而指令是唯一能说出
「这是静态调用还是虚调用」的东西。以前这个字段的文档写着五种取值，实际产出的却
只有 `invoke` 一种——名字和值对不上。现在它从指令名读出来，所以文档和实现是一回事。

`dynamic` 不在其中：能承载它的 `invoke-custom` / `invoke-polymorphic` 指向的是
call site 或 method handle，不是方法，没有 callee 可填。

### 3.2 locator 的实际格式

locator 的格式**每个后端都一样**。`Backend.provenance()`（`tools/base.py:202-209`）
只负责填 `tool` / `tool_version` / `apk_sha256`，`locator` 由各 adapter 自己拼，
但拼出来的形状是同一个：

> **`<后端名>:<相对路径>`**——前缀是产出这条证据的后端，路径是**相对于那份产物**的
> 相对路径。

「那份产物」是哪一个，由后端决定，但规则只有一条，读者不需要为某个后端学一套别的规矩：

- **Androguard** 读的是 APK 本身，所以路径是 **APK 里的成员名**（`classes.dex`），
  `#` 后面是 DEX 里的符号。
- **JADX** 和 **Apktool** 产出自己的输出目录，所以路径是**输出目录里的文件**。
  DexAtlas 把这两个目录放在 `<workspace>/projects/<project id>/jadx/` 和
  `<workspace>/projects/<project id>/apktool/` 下面；读者自己用同一个版本的工具
  跑一遍同一个 APK，也会得到同样的目录结构。

**路径里没有绝对路径，这是硬规则。** 一个 locator 说的是「哪份产物里的哪个位置」，
不是「某台机器上的哪个文件」：带绝对路径的 locator 在别的机器上一文不值，
读报告的人没法顺着它找到代码。同一份记录里的 `apk_sha256` 负责把「哪份产物」钉死，
工具版本负责把「哪个工具」钉死，剩下的相对路径负责把「哪个位置」钉死。

| 后端 | 格式 | 真实样例（demo-app） |
|---|---|---|
| Apktool（manifest 证据） | `apktool:AndroidManifest.xml` | `apktool:AndroidManifest.xml` |
| Apktool（导出组件证据） | `apktool:AndroidManifest.xml#/application` | `apktool:AndroidManifest.xml#/application` |
| JADX | `jadx:<输出目录里的路径>.java` | `jadx:sources/com/example/demo/Crypto.java` |
| JADX（反编译覆盖度） | `jadx:<输出目录里的路径>` | `jadx:sources` |
| Androguard（类） | `androguard:<dex 名>#<类全名>` | `androguard:classes.dex#com.example.demo.Crypto` |
| Androguard（方法） | `androguard:<dex 名>#<类全名>#<方法全名><描述符>` | `androguard:classes.dex#com.example.demo.Crypto#com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;` |
| Androguard（字段） | `androguard:<dex 名>#<类全名>#<字段名>` | `androguard:classes.dex#com.example.demo.MainActivity#TAG` |
| Androguard（交叉引用） | `androguard:<dex 名>#<调用方>-><被调方>` | `androguard:classes.dex#com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V->com.example.demo.Crypto.sign(...)Ljava/lang/String;` |
| Androguard（字符串） | `androguard:<dex 名>#str/<字符串前 64 字符>` | `androguard:classes.dex#str/api_key` |
| 任何后端的失败 | `<后端名>:error/<错误码>` | `jadx:error/not_installed` |

**这些 locator 里没有行号。** 这不是偷懒，是一个可以追溯的因果链：

- JADX 被以 `--no-debug-info` 调用（`tools/jadx/adapter.py:232`），反编译结果里没有行号表，
  所以 locator 只能指到**文件**，不能指到**行**。方法级别只能靠方法名区分。
- Androguard 的 locator 指的是 DEX 里的**符号**，不是字节码偏移量。

**只有一个 locator 指的不是文件而是目录：** JADX 的「反编译覆盖度」记录
（`core/pipeline.py:461-526`）说的是「JADX 写出来的这一整个 `sources/` 目录里，
有多少方法是真反编译出来的」——它的证据就是这个目录本身。

**旧数据库里的 JADX locator 是带绝对路径的。** 那是 6.7 记的那处缺陷。
`Provenance` 在读出来的时候会把那种老格式改写成现在的相对格式
（`core/models.py:68-86` 的 `normalize_locator()`），
所以旧工作区不需要重建，报告里的 locator 也是可复现的。

### 3.3 provenance 没有记录什么

诚实起见，下面这些**当前不在** provenance 里：

- **行号。** 原因见上。
- **字符串池里没有被任何指令加载的条目。** `StringConstant` 的 `class_name` /
  `method_name` 现在**会填**（`models.py:293-294`）：遍历字节码时顺带记下每条
  `const-string` 指令引用了哪个池项，于是「这个 URL 出现在哪个方法里」可以回答。
  但 DEX 字符串池里还有类型描述符（`Landroid/app/Activity;`）、成员名（`onCreate`）
  这类**没有指令直接加载**的条目——demo-app 的 63 条池项里只有 8 条是真正的字面量，
  剩下 55 条没有位置。**池里有，不等于代码用了它。**
- **资源。** 见 5.4。
- **Smali 内容的来源。** Smali 回退路径（`core/pipeline.py:302-303`、`317-321`）返回的是
  裸字符串，**不附带任何 provenance**。也就是说：当 `class_source` 返回 Smali 而不是 Java 时，
  调用方从返回值里**无法判断**这是 Apktool 的输出。只能靠「工作区里有没有 jadx 目录」间接推断。
- **同一产物的多个来源之间没有主次标记。** `provenance` 是一个扁平的列表，
  顺序即合并顺序（Androguard 在前，JADX 在后），但这个顺序**不表达可信度**。
- **方法的 provenance 里没有 JADX 那一半。** 一个方法的 provenance 仍然只有 Androguard
  那一半（它在 DEX 里的位置）——JADX 的贡献是 `decompiled` 这个标志，
  **不是**一条 provenance 记录。理由是 JADX 不产出方法（见 1 节）：
  它只回答「这个方法我反编译出来了吗」。所以「这个方法的 Java 在哪」这个问题，
  provenance 答不了——得看 `decompiled` 标志，然后去工作区的 `jadx/sources` 里找。

---

## 4. 读者如何自己验证一条结论

### 4.1 环境

Windows / Git Bash。三个后端的位置：

```bash
export DEXATLAS_APKTOOL_JAR="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/apktool.jar"
export DEXATLAS_JADX_PATH="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin/jadx.bat"
export PATH="/c/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin:$PATH"
export DEXATLAS_WORKSPACE="C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws"
```

`DEXATLAS_WORKSPACE` 决定工作区和数据库的位置。**不设它会写进仓库根目录的 `.dexatlas/`**，
所以本文档的复现步骤都显式设成一个临时目录。

```bash
uv sync --extra dev --extra analysis
```

`analysis` 这个 extra 装的是 Androguard（`pyproject.toml:49-52`）。**只装 `uv sync` 的话
Androguard 不可用**，分析会照常完成但没有符号索引。

先确认三个后端都在：

```console
$ uv run dexatlas backends
              Analysis backends              
┌────────────┬───────────┬──────────────────┐
│ Backend    │    Status │ Version          │
├────────────┼───────────┼──────────────────┤
│ jadx       │ available │ 1.5.2            │
│ apktool    │ available │ 2.11.1           │
│ androguard │ available │ 4.1.4 │
└────────────┴───────────┴──────────────────┘
```

> 下文所有输出都是在 **jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4**、
> OpenJDK 21.0.12.1、Python 3.12.13 这套版本上跑出来的。
> 版本不同，输出里的数字（类数、方法数、交叉引用数）可能不同；本文档引用的每一处都标了出处。

### 4.2 跑一遍 `demo-app`

```console
$ uv run dexatlas analyze examples/demo-app/demo.apk --json demo.json
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 cross-references (2.8s)
JSON report → C:\Users\admin\AppData\Local\Temp\dexatlas-prov-demo.json
```

`apk_80a8fe0e81204c9f` 不是写死的：**项目 id 是内容寻址的**，
`Project.new_id()` 取 SHA-256 的前 16 位（`models.py:424-427`）。
所以任何人都能自己算出这个 id：

```console
$ python -c "import hashlib,pathlib; print('apk_'+hashlib.sha256(pathlib.Path('examples/demo-app/demo.apk').read_bytes()).hexdigest()[:16])"
apk_80a8fe0e81204c9f
```

`demo.apk` 的完整 SHA-256 是
`80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9`，
它同时出现在每一条 provenance 的 `apk_sha256` 字段里。

JSON 报告的 `project` 段和 `tools` 段（节选自真实输出）：

```json
{
  "project": {
    "id": "apk_80a8fe0e81204c9f",
    "apk": {
      "sha256": "80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9",
      "size_bytes": 2951,
      "dex_files": ["classes.dex"],
      "native_libraries": [],
      "has_signed_certificate": false
    },
    "status": "completed",
    "class_count": 5,
    "method_count": 8,
    "reference_count": 23,
    "evidence_count": 10
  },
  "tools": {
    "jadx": "1.5.2",
    "apktool": "2.11.1",
    "androguard": "4.1.4"
  },
  "errors": []
}
```

`errors` 是空的——**三个后端都跑完了，没有任何一步降级**。

### 4.3 跑一遍 `multidex-app`

```console
$ uv run dexatlas analyze examples/multidex-app/multidex.apk --json multidex.json
✓ apk_a488e43e38c2b8e9 — 4 classes, 11 methods, 13 cross-references (2.7s)
JSON report → C:\Users\admin\AppData\Local\Temp\dexatlas-prov-multidex.json
```

```json
{
  "project": {
    "id": "apk_a488e43e38c2b8e9",
    "apk": {
      "sha256": "a488e43e38c2b8e9292ba4d3badf15fb73167bda92c2343cb2b656cdfd309d55",
      "size_bytes": 2350,
      "dex_files": ["classes.dex", "classes2.dex"],
      "native_libraries": [],
      "has_signed_certificate": false
    },
    "status": "completed",
    "class_count": 4,
    "method_count": 11,
    "reference_count": 13,
    "evidence_count": 8
  },
  "tools": {
    "jadx": "1.5.2",
    "apktool": "2.11.1",
    "androguard": "4.1.4"
  },
  "errors": []
}
```

**`method_count` 报 11，`methods` 表里也是 11 行。** 这一点不是自动成立的：
Androguard 把两个 DEX 里的 `SharedConfig` 各索引一遍，会得到 14 个方法；
`methods` 表的主键是 `(project_id, class_name, name, descriptor)`（`core/storage.py:105`），
重复的被 `INSERT OR REPLACE` 折叠掉了，而计数一度取的是**折叠前**的列表长度。
现在计数由表自己量（`core/pipeline.py:181-185`），折叠掉的那三个方法没有丢——
它们合并成了一条带两份 provenance 的方法。详见 6.2。

### 4.4 五个自建样本的实际结果

全部在 4.1 的环境里跑出来，数字原样：

| 项目 id | APK | 大小 | 类 | 方法 | 交叉引用 | 证据 | 字符串 | 反编译成功 | 状态 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `apk_80a8fe0e81204c9f` | demo.apk | 2951 B | 5 | 8 | 23 | 10 | 63 | 7 / 8 | completed |
| `apk_a488e43e38c2b8e9` | multidex.apk | 2350 B | 4 | 11 | 13 | 8 | 44 | 7 / 11 | completed |
| `apk_d342e11b7931077d` | wide.apk | 1440 B | 4 | 11 | 15 | 9 | 29 | 6 / 11 | completed |
| `apk_2f8d476fb9e71ac4` | obfuscated.apk | 1892 B | 4 | 11 | 10 | 7 | 33 | 7 / 11 | completed |
| `apk_17c6da79f2d5467b` | strings.apk | 1547 B | 1 | 10 | 6 | 4 | 33 | 9 / 10 | completed |

「反编译成功」是 `MethodRef.decompiled` 为真的方法数——**JADX 真的把方法还原成了 Java**。
没成功的那些全是构造器（`<init>`）或接口里的抽象方法：JADX 不给平凡构造器写代码，
接口方法本来就没有方法体。详见 5.2。

`strings-app` 只有 1 个类——它本来就是「一个类塞满字符串」的样本。

**五个样本、38 条证据，三种 `kind`，全部是 `verified`：**

```console
$ python -c "import sqlite3; c=sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db'); print(c.execute('SELECT kind, level, COUNT(*) FROM evidence GROUP BY kind, level').fetchall())"
[('cross_reference', 'verified', 7), ('declaration', 'verified', 26), ('observation', 'verified', 5)]
```

**管道里产出三种 `kind`：** `declaration`（类、manifest、导出组件）、
`cross_reference`（这个 APK 自己的方法被谁调用）和 `observation`（后端失败，
以及 JADX 的反编译覆盖度）。`EvidenceKind` 定义了 5 种（`models.py:430-436`），
`behaviour` 和 `code_located` **一次都不会出现**——它们是给 Phase 2 的模型输出准备的。

**`cross_reference` 的粒度是「被调用的方法」，不是「调用」**：一个被五十处调用的方法
是**一条**结论，不是五十条。而且只有**这个 APK 自己的方法**才有记录——
一次对 `java.lang.StringBuilder.append` 的调用是关于 JDK 的事实，不是关于这个应用的结论；
调用本身照样能在 `xrefs` 表里查到。详见 6.4。

### 4.5 逐条核对一条结论

以「`Crypto.sign` 被 `MainActivity.onCreate` 调用」这条结论为例，
从索引一路查到字节码：

**第一步**：查调用者。

```console
$ uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
  com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V  → 
com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/St
ring;
```

**第二步**：这条边的 provenance 指向 Androguard 的字节码遍历：

```console
$ python - <<'PY'
import sqlite3, json
c = sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db')
for r in c.execute("SELECT caller, callee, provenance FROM xrefs WHERE project_id='apk_80a8fe0e81204c9f' AND callee LIKE '%Crypto.sign%'"):
    print(r[0], '->', r[1]); print('   ', json.loads(r[2]))
PY
com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V -> com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    [{'tool': 'androguard', 'tool_version': '4.1.4', 'apk_sha256': '80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9', 'locator': 'androguard:classes.dex#com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V->com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;'}]
```

**第三步**：打开工作区里 Androguard 说的那个 DEX，对照 Apktool 解出的 Smali：

```console
$ cat "C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81204c9f/apktool/smali/com/example/demo/MainActivity.smali"
```

对应仓库里提交的同一份源码 `examples/demo-app/smali/com/example/demo/MainActivity.smali`：

```smali
    invoke-static {v0, v1}, Lcom/example/demo/Crypto;->sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
```

**第四步**：JADX 的反编译结果给出可读形态：

```console
$ uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.Crypto
```

```java
package com.example.demo;

import java.security.MessageDigest;

/* loaded from: classes.dex */
public final class Crypto {
    public static String digestOf(String str) {
        return MessageDigest.getInstance("SHA-256").digest(str).toLowerCase();
    }

    public static String obfuscate(String str) {
        try {
            return str.toUpperCase();
        } catch (Exception e) {
            return "obfuscation_failed";
        }
    }

    public static String sign(String str, String str2) {
        return str + str2;
    }
}
```

**四步之后，这条结论是可以被独立复核的**：哈希对得上、工具版本对得上、字节码指令对得上、
反编译语义对得上。

### 4.6 当 JADX 缺席时：Smali 回退

把 `DEXATLAS_JADX_PATH` 去掉、也不把 jadx 放进 `PATH`（本机 jadx 不在系统 `PATH` 上），
用另一个工作区重跑：

```console
$ uv run dexatlas backends
                Analysis backends                
┌────────────┬───────────────┬──────────────────┐
│ Backend    │        Status │ Version          │
├────────────┼───────────────┼──────────────────┤
│ jadx       │ not installed │ —                │
│ apktool    │     available │ 2.11.1           │
│ androguard │     available │ 4.1.4 │
└────────────┴───────────────┴──────────────────┘

$ uv run dexatlas analyze examples/demo-app/demo.apk
✓ apk_80a8fe0e81204c9f — 4 classes, 8 methods, 23 cross-references (1.2s)
```

两处变化，都值得注意：

1. **类数从 5 掉到 4。** 少掉的那个是 `com.example.demo.R`——它**只存在于 JADX 的输出里**，
   DEX 里没有这个类（见 5.2）。
2. **缺后端会变成一条证据**（`core/evidence.py:101-116`）：

```json
{
  "id": "E-0010",
  "kind": "observation",
  "level": "verified",
  "summary": "jadx did not complete: jadx is not installed or not on PATH",
  "provenance": [
    {"tool": "jadx", "tool_version": null,
     "apk_sha256": "80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9",
     "locator": "jadx:error/not_installed"}
  ]
}
```

`tool_version` 是 `null`，而**这是对的**：jadx 没装上，所以它没有版本。
版本为 `null` 现在只表示「这个工具这次没跑」——
「工具在、版本没填」这件事已经修掉了（见 6.5）。

**没有 JADX 就没有「反编译覆盖度」那条记录**，报告里的「Methods decompiled by JADX」
这一行整个不出现——不是 0，是「没有这一说」。
同理，方法表里的 `decompiled` 全部是 `false`：没有反编译器，就没有反编译出来的 Java。

这时候 `class_source` 会落到 Smali（`core/pipeline.py:291-304`）：

```smali
.class public final Lcom/example/demo/Crypto;
.super Ljava/lang/Object;
.source "Crypto.java"


# direct methods
.method public static digestOf(Ljava/lang/String;)Ljava/lang/String;
    .locals 1

    const-string v0, "SHA-256"

    invoke-static {v0}, Ljava/security/MessageDigest;->getInstance(Ljava/lang/String;)Ljava/security/MessageDigest;

    move-result-object v0

    invoke-virtual {v0, p0}, Ljava/security/MessageDigest;->digest(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/String;->toLowerCase()Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method

.method public static obfuscate(Ljava/lang/String;)Ljava/lang/String;
    .locals 2

    :try_start_0
    invoke-virtual {p0}, Ljava/lang/String;->toUpperCase()Ljava/lang/String;

    move-result-object v0
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    return-object v0

    :catch_0
    move-exception v1

    const-string v0, "obfuscation_failed"

    return-object v0
.end method

.method public static sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
    .locals 2

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method
```

**注意 4.2 那次运行和这次运行的项目 id 一样（`apk_80a8fe0e81204c9f`）**——
项目 id 只由 APK 哈希决定，和装了哪些后端无关。同一个 id 在两个工作区里
有**不同的内容**：5 个类和 4 个类。**项目 id 不能代表分析内容，只能代表输入。**
这正是为什么每条 provenance 都单独带 `apk_sha256` 和 `tool_version`。

---

## 5. 每个后端的局限

### 5.1 Androguard

- **交叉引用是「静态调用目标」，不是「实际被调用的那个实现」。**
  DEX 的 `invoke-interface` 编码的是接收者的**编译期类型**。
  `examples/wide-app` 就是为这件事准备的样本：`HandlerFactory.dispatch` 的接收者类型是接口
  `Handler`，字节码里写的是（`examples/wide-app/smali/com/example/wide/HandlerFactory.smali`）：

  ```smali
  invoke-interface {p0, p1}, Lcom/example/wide/Handler;->handle(Ljava/lang/String;)Ljava/lang/String;
  ```

  所以交叉引用指向**接口**。实测：

  ```console
  $ uv run dexatlas xrefs apk_d342e11b7931077d "com.example.wide.JsonHandler.handle(Ljava/lang/String;)Ljava/lang/String;"
  No callers of com.example.wide.JsonHandler.handle(Ljava/lang/String;)Ljava/lang/String;.
  $ echo "exit=$?"
  exit=1

  $ uv run dexatlas xrefs apk_d342e11b7931077d "com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;"
    com.example.wide.HandlerFactory.dispatch(Lcom/example/wide/Handler;Ljava/lang/String;)Ljava/lang/String;  →
  com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;
  $ echo "exit=$?"
  exit=0
  ```

  **`JsonHandler.handle` 和 `XmlHandler.handle` 看起来「没有调用者」**，
  而实际上运行时它们很可能就是被调用的那一个。
  **静态交叉引用在多态处会漏掉实现类。** 想要实现类的调用者，得自己沿
  `ClassRef.interfaces`（`models.py:203`）往下展开——DexAtlas 不做这件事。
  > 补充：DEX 编码的是**声明类型**（这里是接口），不是子类。实现类只有在运行时多态分派时
  > 才知道，所以任何静态工具都拿不到「运行时被调用的实现」。

- **交叉引用靠遍历字节码，没有缓存。** Androguard 4.x 移除了 xref 缓存
  （`tools/androguard/adapter.py:7-9`），所以每条边都是扫指令得到的。
  这条遍历有硬上限：`DEFAULT_METHOD_LIMIT = 200_000`、
  `DEFAULT_INSTRUCTION_LIMIT = 5_000_000`、`DEFAULT_STRING_LIMIT = 50_000`
  （`tools/androguard/adapter.py:48-50`）。**触到上限时索引会被截断，而且只在日志里
  留一行 warning，报告里看不出区别。**

- **字符串索引是「DEX 字符串池」，不是「字符串字面量」。** `dex.get_strings()`
  返回的是字符串池里的**全部**条目，包括类型描述符、方法名、以及类型签名碎片。
  demo-app 的 63 条「字符串常量」里有相当一部分是这样的：

  ```console
  $ python - <<'PY'
  import sqlite3
  c = sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db')
  for (v,) in c.execute("SELECT value FROM strings WHERE project_id='apk_80a8fe0e81204c9f' ORDER BY value LIMIT 20"):
      print(repr(v))
  PY
  '<init>'
  'Crypto.java'
  'I'
  'ILL'
  'L'
  'LL'
  'LLL'
  'Landroid/app/Activity;'
  'Landroid/app/Service;'
  'Landroid/content/Intent;'
  'Landroid/os/Bundle;'
  'Landroid/os/IBinder;'
  'Landroid/util/Log;'
  'Lcom/example/demo/Crypto;'
  'Lcom/example/demo/MainActivity;'
  'Lcom/example/demo/NetworkClient;'
  'Lcom/example/demo/SyncService;'
  'Ljava/lang/Exception;'
  'Ljava/lang/Object;'
  'Ljava/lang/String;'
  'Ljava/lang/StringBuilder;'
  ```

  真正的应用字面量是混在里面的那几条（`'api_key'`、`'sk_live_2f8a91c4e7b3'`、
  `'https://api.example.com/v1'`）。**搜索时要注意这个噪声。**
  另外，`StringConstant` 的 locator 是 `androguard:classes.dex#str/<值前 64 字符>`，
  前 64 字符相同的两个字符串会得到**相同的 locator**。

- **它是唯一一个跑在进程内的后端。** JADX 和 Apktool 是子进程（`tools/base.py:129-138`），
  Androguard 是 Python 库，直接 import 进我们的进程（`tools/androguard/adapter.py:160-162`）。
  所以 DEX 解析崩溃会打在**我们**的进程里——代码用 try/except 把它兜成 `ToolError`
  （`tools/androguard/adapter.py:198-206`），但解析器本身的内存安全风险是继承来的。

- **它答不了「这个方法反编译出来了吗」。** Androguard 读 DEX，能回答「这个方法有没有
  字节码」——但那不是同一个问题，而且几乎每个方法都有字节码，所以这个答案没有信息量。
  **「方法表里的 `decompiled`」现在由 JADX 回答**（见 5.2），Androguard 不再碰这个字段。
  「有没有字节码」这个信息没有丢：没有方法体的方法就是 `abstract` 或 `native` 的方法，
  访问标志里写着。

### 5.2 JADX

- **JADX 会产出 DEX 里根本不存在的类。** demo-app 的第 5 个类 `com.example.demo.R`
  只有一条 provenance，是 JADX 的：

  ```console
  $ uv run dexatlas classes apk_80a8fe0e81204c9f
com.example.demo.Crypto class
  4.1.4 -> androguard:classes.dex#com.example.demo.Crypto
  jadx 1.5.2 -> jadx:sources/com/example/demo/Crypto.java
com.example.demo.MainActivity class
  4.1.4 -> androguard:classes.dex#com.example.demo.MainActivity
  jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java
com.example.demo.NetworkClient class
  4.1.4 -> androguard:classes.dex#com.example.demo.NetworkClient
  jadx 1.5.2 -> jadx:sources/com/example/demo/NetworkClient.java
com.example.demo.R class
  jadx 1.5.2 -> jadx:sources/com/example/demo/R.java
com.example.demo.SyncService class
  4.1.4 -> androguard:classes.dex#com.example.demo.SyncService
  jadx 1.5.2 -> jadx:sources/com/example/demo/SyncService.java
  ```

  `R` 是资源 ID 容器类，由 aapt2 在打包时生成资源表，**DEX 里没有它**。
  Androguard 索引不到它，Apktool 也解不出对应的 Smali。
  **JADX 产出的类不一定在字节码里存在**——这是一个类级「多出来的」结论。

  注意两边的 locator 是**同一种东西**：`androguard:` 后面是 APK 里的成员名，
  `jadx:` 后面是 JADX 输出目录里的相对路径，**两个都是相对路径**，
  换一台机器照样指得到（见 3.2）。

- **JADX 的输出可能不是反编译结果，而是占位符。** JADX 对付不了的方法会写一个
  占位方法体：`throw new UnsupportedOperationException("Method not decompiled: ...")`。
  （`/* Method could not be decompiled */` 是更早版本的写法——jadx 1.5.2 的 jar 里
  没有这个字符串，正则里保留它只是为了兼容别的版本。）
  DexAtlas 用正则 `_DECOMPILE_FAILED_RE`（`tools/jadx/adapter.py:42-47`）和
  `JadxBackend.method_decompiled()`（`tools/jadx/adapter.py:315-317`）认它，
  **现在这条检测在生产路径上**：`JadxBackend.decompilation_status()`
  （`tools/jadx/adapter.py:320-373`）逐个类读 JADX 写出的 `.java`，
  把「真反编译出来的方法」和「JADX 写不出来的方法」分开。

  管道把结果记在方法表里：**`MethodRef.decompiled` 现在就是「JADX 反编译成功了」**，
  字段名和它的值是一回事了。`dexatlas methods` 直接把这一列印出来：

  ```console
  $ uv run dexatlas methods apk_80a8fe0e81204c9f
  ┌───────────────────────────────────────────┬────────────────────┬────────────┐
  │ Method                                    │ Flags              │ Decompiled │
  ├───────────────────────────────────────────┼────────────────────┼────────────┤
  │ com.example.demo.Crypto.digestOf(Ljava/l… │ public static      │ yes        │
  │ com.example.demo.Crypto.obfuscate(Ljava/… │ public static      │ yes        │
  │ com.example.demo.Crypto.sign(Ljava/lang/… │ public static      │ yes        │
  │ com.example.demo.MainActivity.<init>()V   │ constructor public │ no         │
  │ com.example.demo.MainActivity.describe(L… │ public static      │ yes        │
  │ com.example.demo.MainActivity.onCreate(L… │ protected          │ yes        │
  │ com.example.demo.NetworkClient.post(Ljav… │ public static      │ yes        │
  │ com.example.demo.SyncService.onBind(Land… │ public             │ yes        │
  └───────────────────────────────────────────┴────────────────────┴────────────┘
  ```

  `MainActivity.<init>` 是 `no`，而且这是对的：JADX 不给平凡构造器写代码，
  所以**没有反编译出来的 Java**，只有字节码。

  同时 DexAtlas 是以 `--show-bad-code` 调 JADX 的（`tools/jadx/adapter.py:233`），
  那个选项的含义就是「尽力输出，不行就输出残缺代码」。

  **这个标志是怎么判定的，边界在哪：** 判定读的是**方法自己**（声明 + 方法体），
  不读它上面的注释——JADX 会在方法上方写 `/* JADX WARN: Type inference failed ... */`，
  那是**类的**注释，不是失败信号（demo-app 的 `NetworkClient.post` 就带着这么一条，
  它的方法体是真代码）。名字对上了不代表是同一个方法：JADX 用**类名**写构造器，
  而混淆后的类可能有一个**和类同名的方法**，所以构造器是按「没有返回类型」认的，
  不是按名字认的。

- **「哪些类反编译失败了」现在有答案了。** 分析结束时会记录一条证据：
  `jadx produced real Java for 7 of 8 methods in 5 of 5 classes`，
  它的 `detail` 里带着失败的方法清单和没有源码的类清单
  （`core/pipeline.py:461-526`）。报告的 Summary 里也有一行
  「Methods decompiled by JADX」。

  **这里没有 per-class 的错误日志可读，因为 JADX 根本不写那个文件。**
  旧的 `summarize_jadx_log()` 解析的是 `sources/resources/log/error.log`——
  这个路径跟 JADX 的输出目录结构对不上（JADX 把 `resources/` 放在输出目录的根下，
  不在 `sources/` 里），而且 **jadx 1.5.2 压根不写它**：整个 jar 里没有 `error.log`
  这个字符串，`jadx.core.export.OutDirs` 只有 `srcOutDir` 和 `resOutDir` 两个目录，
  跑一次会失败的 APK 也只留下 `sources/` 和 `resources/` 两个空目录。
  所以这个函数被删了：它对着一个不存在的文件，返回一个永远是空的字典。

- **locator 现在是相对路径**（见 3.2）。它以前是绝对路径，换一台机器就指不到东西
  ——那是 6.7 记的那处缺陷，现在修好了。

- **在这 5 个自建样本上，JADX 一次都没失败。** 五个样本的 `errors` 全空，
  也没有一个方法带占位符——**没成功的那些全是 JADX 根本没写的方法**
  （平凡构造器、接口里的抽象方法），不是失败。
  **所以本节关于 JADX 失败路径的描述来自代码和已知缺陷，不是来自一次真实失败。**
  真正打穿 JADX 的样本不在仓库里——这正是
  [`docs/reports/phase1-execution-report.md`](reports/phase1-execution-report.md) 4.5 节
  列的「未做的部分」。

### 5.3 Apktool

- **Apktool 产出 manifest，不产出符号。** 类、方法的结构一律来自 Androguard。
  Apktool 唯一的符号贡献是 **Smali 文件**，而且是**按需读取**的，不进索引。

- **Smali 是字节码，不是源码。** Smali 回退给的是 Dalvik 汇编。
  它能证明「这个方法调用了谁」，但读起来不是 Java。**回退发生时，结论的可读性下降了，
  可信度没有下降**——它反而更接近原始事实。

- **Smali 不带 provenance。** 走回退路径时，调用方拿到的只是一个字符串，
  不知道它来自 Apktool（见 3.3）。

- **manifest 的版本号和 SDK 版本不在 manifest 里。** Apktool 解码时把它们挪进
  `apktool.yml`（`tools/apktool/adapter.py:156-159`、`289-320`）。
  只读 `AndroidManifest.xml` 会得到空值，所以实现里从 `apktool.yml` 补齐
  （manifest 自身的值优先）。**这意味着 manifest 结论的证据链其实跨了两个文件**，
  而 provenance 只写了 `apktool:AndroidManifest.xml` 一个。

- **manifest 里的 `exported` 属性只有显式写了才为 `true`。**
  `ManifestComponent.exported` 是 `bool | None`（`models.py:314`），
  `_parse_bool` 把没写的当 `None`（`tools/apktool/adapter.py:283-286`）。
  `exported_components` 只挑 `exported is True`（`models.py:332-334`）。
  **一个没有显式 `android:exported` 的组件，在 API 31+ 上默认不导出，
  但在这份报告里它不会出现在「已导出组件」列表里——这是对的；
  但反过来，如果 APK 显式写了 `exported="true"` 而实际有权限保护，
  它照样会出现在列表里。** 这个列表是「声明为导出」，不是「实际可被外部调用」。

### 5.4 三个后端共同的盲区

- **资源完全没有覆盖。** Apktool 会把 `res/` 解码到工作区：

  ```console
  $ find "C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81204c9f/apktool/res" -type f
  .../apktool/res/values/public.xml
  .../apktool/res/values/strings.xml
  ```

  但 `src/` 里没有任何代码读它。后果可以直接看到——demo-app 的资源字符串
  `'DexAtlas Demo'`（来自 `res/values/strings.xml`）**不在字符串索引里**：

  ```console
  $ python - <<'PY'
  import sqlite3
  c = sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db')
  print(c.execute("SELECT COUNT(*) FROM strings WHERE project_id='apk_80a8fe0e81204c9f' AND value='DexAtlas Demo'").fetchone())
  PY
  (0,)
  ```

  **资源里的字符串是搜不到的。** 硬编码密钥如果放在 `strings.xml` 而不是代码里，
  当前的索引看不见它。**这是覆盖度上最大的一块空白。**

- **`lead` 和 `insufficient` 两个证据等级在 Phase 1 一次都不会出现。**
  管道里所有证据都是显式传 `EvidenceLevel.VERIFIED` 的
  （`core/evidence.py:105`、`122`、`139`、`173`，`core/pipeline.py:221`）。
  这两个等级是给 Phase 2 的模型输出准备的。

- **原生库（`.so`）只被统计，不被分析。** `ApkMetadata.native_libraries`
  是从 ZIP 目录里列出来的文件名（`core/ingest.py:59-61`），
  没有 ELF 解析、没有 JNI 关系。Phase 3 才计划接 Ghidra。

- **没有动态分析。** 全部结论都是静态的。

---

## 6. 读这份文档时会撞上的七处不一致

这些不是猜测，是写这份文档时实际跑出来的。**其中六处已经修好了**，
下面每一节都写明了现在的状态；剩下的一处**不是缺陷**——
一份声称讲「证据来源」的文档如果藏起这些，就不值得读。
**已修的那些都还没有发布**：它们在 `main` 分支上、在 v0.1.2 之后，
下一个版本号由发布时决定。

| 节 | 不一致 | 状态 |
|---|---|---|
| 6.1 | 方法 id 有两种写法，`dexatlas xrefs` 只认其中一种 | **已修** |
| 6.2 | `method_count` 报的数比表里的行数多 | **已修** |
| 6.3 | `dexatlas classes` 只显示前两条 provenance | **已修** |
| 6.4 | 交叉引用永远不产生证据行 | **已修** |
| 6.5 | 「已导出组件」这条证据的 `tool_version` 是 `null` | **已修** |
| 6.6 | `xrefs` 表里可能有重复的 caller/callee 对 | 未修，但这是对的（见该节） |
| 6.7 | JADX 的 locator 含绝对路径，换台机器就指不到东西 | **已修** |

### 6.1 方法 id 的两种写法，`dexatlas xrefs` 只认其中一种（已修）

**当时的现象：** `dexatlas methods` 打印的方法 id 来自 Androguard 的 `get_descriptor()`，
**参数之间有空格**；而 `dexatlas xrefs` 要的是**没有空格**的写法。把前者原样复制过去，
一次都查不到。

**根因：** Androguard 4.1.4 的 `get_descriptor()` 返回
`'(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;'`（带空格），
而 `_parse_dalvik_reference`（`tools/androguard/adapter.py:384-411`）在解析调用目标时
**去掉了空格**。于是 `methods` 表里存的是带空格的 id，`xrefs` 表里存的是不带空格的 id，
**两张表按字符串精确相等是连不上的**：

```console
$ python - <<'PY'
import sqlite3
c = sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db')
for pid in ('apk_80a8fe0e81204c9f','apk_a488e43e38c2b8e9','apk_d342e11b7931077d'):
    total = c.execute('SELECT COUNT(*) FROM xrefs WHERE project_id=?', (pid,)).fetchone()[0]
    exact = c.execute(
        "SELECT COUNT(*) FROM xrefs x JOIN methods m"
        " ON m.project_id=x.project_id"
        " AND m.class_name || '.' || m.name || m.descriptor = x.callee"
        " WHERE x.project_id=?", (pid,)).fetchone()[0]
    print(pid, 'xrefs=%d  exactly-joinable-to-methods=%d' % (total, exact))
PY
apk_80a8fe0e81204c9f xrefs=23  exactly-joinable-to-methods=3
apk_a488e43e38c2b8e9 xrefs=13  exactly-joinable-to-methods=0
apk_d342e11b7931077d xrefs=15  exactly-joinable-to-methods=3
```

（剩下的边指向 `java.lang.StringBuilder.append` 之类**不在这个 APK 里**的库方法，
本来就 join 不上，那是正常的。）

**现在的行为：** 方法 id 在模型层、存储层、查询层三处都只有**一个**拼写——
规范的 JVM 描述符，参数类型紧挨着（`models.py:139-186`）。`dexatlas methods` 印出来的
就是能用的 id，`dexatlas xrefs` 也认两种写法（查询时两边都规范化）：

```console
$ uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
  com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V  →
com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/St
ring;
```

**既有的旧工作区不需要重建也能查**：查询比较的是规范化之后的 id，
索引也建在规范化形式上。详见
[`docs/reports/phase1-execution-report.md`](reports/phase1-execution-report.md) 3.11 节。

### 6.2 `method_count` 报的数比表里的行数多（已修）

**当时的现象：** multidex-app 报 14，`methods` 表 11 行。
`project.method_count` 数的是折叠前的列表——那版写法已经不在了，
现在是表自己量的（`core/pipeline.py:181-185`）——
而 `methods` 表的主键会折叠重复（`core/storage.py:105`）。
**类在多个 DEX 里重复定义时就会不一致。**

**现在的行为：** 计数由表自己量——`Store.save_symbols` 数的是它写进去的行数
（`core/storage.py:429-434`），管道报的是这个数。**报出来的数就是查得到的数。**
折叠掉的那三个方法也没有丢：它们合并成了一条带两份 provenance 的方法
（`core/pipeline.py:382-407`），就像一个类被两个后端看到时那样。

### 6.3 `dexatlas classes` 只显示前两条 provenance（已修）

**当时的现象：** `cli/main.py` 里是 `for source in cls.provenance[:2]:`。
multidex-app 的 `SharedConfig` 有**三条**来源（两个 DEX + JADX），CLI 只显示前两条，
而且**不说是截断的**：

```console
$ uv run dexatlas classes apk_a488e43e38c2b8e9
...
com.example.multidex.SharedConfig class
  4.1.4 ->
androguard:classes.dex#com.example.multidex.SharedConfig
  4.1.4 ->
androguard:classes2.dex#com.example.multidex.SharedConfig
```

第三条（JADX）被截掉了，而 REST API（`api/app.py:228-241` 返回完整的
`model_dump`）返回的是**全部三条**——**CLI 看到的比 API 看到的少**。

**现在的行为：** 默认仍然只显示前两条（一个类可能有几十条来源，全倒出来没法看），
但**明确写出折叠了多少**，并给出看全部的办法：

```console
$ uv run dexatlas classes apk_a488e43e38c2b8e9
...
com.example.multidex.SharedConfig class
  4.1.4 ->
androguard:classes.dex#com.example.multidex.SharedConfig
  4.1.4 ->
androguard:classes2.dex#com.example.multidex.SharedConfig
  … 1 more source not shown (use --all to see all 3)
```

`--all` 显示全部来源，`--provenance-limit N` 指定要显示几条。
类列表本身被 `--limit` 截断时也一样会说明截断了多少。

**`dexatlas methods` 没有这个问题**：它根本不显示 provenance，
所以不是「显示了一部分」，是「一条都没显示」——方法和字段的来源只能从 REST API 拿。

### 6.4 交叉引用永远不产生证据行（已修）

**当时的现象：** `EvidenceKind.CROSS_REFERENCE` 存在，
`EvidenceBuilder.add_method_references` 也存在，
**但 `src/` 里没有任何地方调用它**——所以交叉引用只是索引数据，不是证据。
报告里看不到「谁调用了什么」这一层，只能在索引里查。

**现在的行为：** 管道会为**这个 APK 自己的、被调用过的方法**各记一条证据
（`core/pipeline.py:263` 调用 `core/evidence.py:183-212` 的
`add_cross_references`）。粒度是**被调用的方法**，不是「调用」：
一个被五十处调用的方法是**一条**结论。调用库代码（`java.lang.StringBuilder.append`）
**不产生记录**——那是关于 JDK 的事实，不是关于这个应用的结论；
调用本身照样在 `xrefs` 表里查得到。

所以报告里现在有两个数：**索引里的交叉引用条数**，和**有证据记录的条数**
（`reports/markdown.py:50-51`）。两个数不一样是**故意**的：
一个所有调用都进了库的应用，不能被误读成一个交叉引用坏掉的应用。

`EvidenceKind.CODE_LOCATED` 和 `EvidenceKind.BEHAVIOUR` 仍然没有生产者——
它们是给 Phase 2 准备的。

### 6.5 「已导出组件」这条证据的 `tool_version` 是 `null`（已修）

**当时的现象：** `core/evidence.py:128-154` 的 `add_exported_components` 硬编码了
`tool_version=None`，**即使 apktool 的版本是已知的**。对比同一份报告里 manifest 那条证据：

```console
$ uv run dexatlas analyze examples/demo-app/demo.apk -o report.md
```

| 证据 | 来源 |
|---|---|
| `E-0001` Package com.example.demo (...) | `apktool 2.11.1 -> AndroidManifest.xml` |
| `E-0002` 2 component(s) are explicitly exported | `apktool -> AndroidManifest.xml#/application` |

**同一条工具链的两条证据，一条带版本一条不带。** 报告里的
`Tool versions: 4.1.4, apktool 2.11.1, jadx 1.5.2` 那行
（`reports/markdown.py:70`、`reports/markdown.py:123-129`）是从 `Project.tool_versions` 来的，
和 per-evidence 的 `tool_version` 是两份数据（见 3.1）。

**根因：** `EvidenceBuilder` 根本拿不到工具版本。它只有 `project_id` 和 `apk_sha256`，
而版本在管道里是有的——只是**晚了一步**：`project.tool_versions` 是在 builder 建好之后
才赋值的，于是 builder 手里永远是一份空字典。

**现在的行为：** 管道先探测版本，再把**同一份**版本表交给证据构造器
（`core/pipeline.py:118-124`），`EvidenceBuilder` 把它当成构造参数
（`core/evidence.py:37-56`）——不是「记得填」，是「不给就写不出证据」。
`tool_version` 为 `None` 现在只有一种含义：**这个工具这次没跑**
（比如它压根没装，见 4.6）。

实测（`examples/demo-app`）：

| 证据 | 来源 |
|---|---|
| `E-0001` Package com.example.demo (...) | `apktool 2.11.1 -> apktool:AndroidManifest.xml` |
| `E-0002` 2 component(s) are explicitly exported | `apktool 2.11.1 -> apktool:AndroidManifest.xml#/application` |

**后端失败那条证据也一样**（`core/evidence.py:101-116`）：它以前也硬编码
`tool_version=None`，现在写的是**失败的那个工具**的版本——
「jadx 1.5.2 超时」比「jadx 超时」有用得多。

顺带一提 `Provenance.ref()`（`models.py:112-120`）的输出是
`f"{tool} {tool_version} -> {locator}"`，所以 Androguard 那条会显示成
`4.1.4 -> ...`——「androguard」出现两次。不是 bug，是拼接的结果。

### 6.6 `xrefs` 表里可能有重复的 caller/callee 对

`Project.reference_count` 数的是 Androguard 遍历出来的边数，
`xrefs` 表没有主键（`core/storage.py:119-125`），重复的 caller/callee 对会**各自保留**
（因为 provenance 不同：哪个 DEX 里扫到的）。multidex-app 的
`SharedConfig.<init>()V -> java.lang.Object.<init>()V` 就有两条，
分别来自 `classes.dex` 和 `classes2.dex`：

```console
$ python - <<'PY'
import sqlite3, json
c = sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db')
for r in c.execute("SELECT caller, callee, provenance FROM xrefs WHERE project_id='apk_a488e43e38c2b8e9' AND caller='com.example.multidex.SharedConfig.<init>()V'"):
    print(r[0], '->', r[1], '|', json.loads(r[2])[0]['locator'])
PY
com.example.multidex.SharedConfig.<init>()V -> java.lang.Object.<init>()V | androguard:classes.dex#com.example.multidex.SharedConfig.<init>()V->java.lang.Object.<init>()V
com.example.multidex.SharedConfig.<init>()V -> java.lang.Object.<init>()V | androguard:classes2.dex#com.example.multidex.SharedConfig.<init>()V->java.lang.Object.<init>()V
```

这个是对的（两条边确实来自两个 DEX），但读表的人需要知道 `xrefs` 表
**可能有重复的 caller/callee 对**。

### 6.7 JADX 的 locator 含绝对路径，换台机器就指不到东西（已修）

**当时的现象：** 报告里 JADX 的来源长这样：

```
jadx 1.5.2 -> jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81204c9f/jadx/sources/com/example/demo/Crypto.java
```

那个绝对路径**换一台机器就无效**：读者拿到报告，无法定位到文件，
报告里的证据位置因此不可复现。Androguard 那一半不受影响
（`androguard:classes.dex#com.example.demo.Crypto` 只依赖 APK 内部的路径和符号名），
所以**同一行里两半 locator 的可复现性是不一样的**。

**根因：** 两处拼接都用了**绝对**路径——`tools/jadx/adapter.py:273`（每个类一条）
和 `core/pipeline.py:461-526`（反编译覆盖度那条）。绝对路径是**那台机器的属性**，
不是分析的属性。

**现在的行为：** locator 里的路径一律**相对于该后端的输出目录**
（规则见 3.2），所以两个后端看起来是同一种东西：

```
jadx 1.5.2 -> jadx:sources/com/example/demo/Crypto.java
4.1.4 -> androguard:classes.dex#com.example.demo.Crypto
```

要定位文件，读者需要知道两件事，两件都是可推导的：
**产物是哪一个**（同一行里的 `apk_sha256`）和**基准目录在哪里**
（DexAtlas 把它放在 `<workspace>/projects/<project id>/jadx/`；
自己跑一遍 jadx 也会得到同样的目录结构）。

**旧数据库怎么办：** 旧格式的 locator 是绝对路径，改格式就意味着旧行不可复现。
`Provenance` 在读出来的时候会把那种老格式改写成现在的相对格式
（`core/models.py:68-86` 的 `normalize_locator()`，
靠 `projects/apk_<16 位哈希>/jadx/` 这一段认出旧路径），
所以**旧工作区不需要重建，旧报告也是可复现的**。
认不出来的 locator 原样保留——不认识的东西不猜。


---

## 7. 复现本文档的全部数字

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
uv sync --extra dev --extra analysis

export DEXATLAS_APKTOOL_JAR="<apktool.jar 的路径>"
export DEXATLAS_JADX_PATH="<jadx 启动器的路径>"
export DEXATLAS_WORKSPACE="$(mktemp -d)"

uv run dexatlas backends
uv run dexatlas analyze examples/demo-app/demo.apk        --json "$DEXATLAS_WORKSPACE/demo.json"
uv run dexatlas analyze examples/multidex-app/multidex.apk --json "$DEXATLAS_WORKSPACE/multidex.json"
uv run dexatlas analyze examples/wide-app/wide.apk
uv run dexatlas analyze examples/obfuscated-app/obfuscated.apk
uv run dexatlas analyze examples/strings-app/strings.apk
```

`$DEXATLAS_WORKSPACE/dexatlas.db` 就是本文档所有 SQL 查询的来源。
本文档引用的每一条 SQL 都可以直接对它跑。

**清理：**

```bash
rm -rf "$DEXATLAS_WORKSPACE"
```

---

## 8. 一页速查

| 想确认的事 | 看哪里 |
|---|---|
| 一条结论是谁产出的 | 它的 `provenance` 数组（每个元素一个 `tool`） |
| 用的哪个版本的工具 | `provenance[].tool_version`；项目级看 `Project.tool_versions` |
| 分析的是哪个 APK | `provenance[].apk_sha256`；项目 id 只是它的前 16 位 |
| 代码在哪儿 | `provenance[].locator`（`<后端名>:<相对路径>`，格式见 3.2，**没有行号**） |
| 这个结论有多硬 | `Evidence.level`（Phase 1 全部是 `verified`） |
| 后端有没有降级 | `Project.errors` / 报告的「Backend errors」段 / `kind=observation` 的证据 |
| 这个方法反编译出来了吗 | `MethodRef.decompiled` / `dexatlas methods` 的「Decompiled」列 / 报告的「Methods decompiled by JADX」 |
| 有多少代码读不出来 | 报告的「Methods decompiled by JADX」和那条 `observation` 证据的 `detail` |
| 想看完整 provenance 列表 | `dexatlas classes --all`，或者 REST API 的 `/classes`（6.3） |
| 想查调用者 | `dexatlas xrefs`，方法 id 两种拼写都认（6.1） |
| 想知道字符串在不在资源里 | **查不到**，看 5.4 |
