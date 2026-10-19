# 分析覆盖度与证据来源

**这份文档回答一个问题：一条结论，到底是谁、用哪个版本的工具、在哪份 APK 的哪个位置上得出的。**

它不是架构说明。[`docs/architecture/README.md`](architecture/README.md) 讲的是「代码怎么组织、
为什么这么组织」；这份讲的是「哪些结论可信、依据是什么、哪些情况下不可信」。

文中每一条说法都指向具体的 `文件:行号`，或者下面第 4 节里跑出来的真实输出。
**没有跑过、也没读过代码的地方，这里不写。**

---

## 1. 覆盖度总表：每类结论由谁产出

DexAtlas 目前有 3 个分析后端（`src/dexatlas/tools/registry.py:19-20`）加 1 个不依赖任何后端的
APK 检查步骤。它们的产出范围是**互不重叠**的：

| 结论类型 | 产出后端 | 落在哪里 | 代码位置 |
|---|---|---|---|
| APK 哈希、大小、DEX 文件列表、原生库、是否有签名证书 | 无（纯标准库） | `ApkMetadata` | `core/ingest.py:51-77` |
| manifest（包名、版本、SDK、权限、组件） | **Apktool** | `ManifestInfo` | `tools/apktool/adapter.py:102-196` |
| manifest 的版本号 / SDK（Apktool 把它挪走了，从 `apktool.yml` 补） | **Apktool** | `ManifestInfo` | `tools/apktool/adapter.py:289-320` |
| 类的身份、种类、父类、接口、访问标志 | **Androguard**（主）+ **JADX**（并） | `ClassRef` | `tools/androguard/adapter.py:263-274` |
| 类的**源码表示**（Java 或 Smali） | **JADX** 优先，**Apktool** 回退 | 工作区文件，按需读取 | `core/pipeline.py:251-281` |
| 方法（签名、描述符、访问标志、是否有字节码） | **Androguard**（唯一） | `MethodRef` | `tools/androguard/adapter.py:297-310` |
| 字段 | **Androguard**（唯一） | `FieldRef` | `tools/androguard/adapter.py:276-287` |
| 交叉引用（调用边） | **Androguard**（唯一，遍历字节码得到） | `MethodReference` | `tools/androguard/adapter.py:318-329` |
| 字符串常量 | **Androguard**（唯一，取自 DEX 字符串池） | `StringConstant` | `tools/androguard/adapter.py:354-373` |
| 资源（`res/`、布局、字符串表） | **没有人** | 不在模型里 | 见 5.4 |

几条需要注意的推论：

- **JADX 不产出方法、字段、交叉引用里的任何一条。** JADX 后端只产出 `ClassRef`
  （`tools/jadx/adapter.py:185-192`）。方法表、字段表、交叉引用表 100% 来自 Androguard。
- **Apktool 不产出任何符号。** 它产出 manifest 和 Smali 文件；Smali 是**按需读取**的，
  不进索引、不进证据表（`core/pipeline.py:251-281`）。
- **资源没有覆盖。** Apktool 会把 `res/` 解码到工作区，但 `src/` 里没有任何代码读它
  （`grep -rn "res/values\|resources" src/` 只命中 `ingest.py:15` 的文件名常量
  `resources.arsc`、Apktool/JADX 模块的 docstring，以及 `jadx/adapter.py:358` 的
  `"sources" / "resources" / "log"` ——那是 JADX **自己**的输出目录，不是 APK 的 `res/`）。这一条在 5.4 里展开。

---

## 2. 冲突时谁说了算

只有一类结论有两个来源：**类**。Androguard 从 DEX 定义读到一个类，JADX 从它写出的
`.java` 文件读到同一个类。合并规则写在 `core/pipeline.py:316-339` 的 `_merge_classes` 里，
不是「谁后跑谁覆盖」：

| 字段 | 规则 | 实际效果 |
|---|---|---|
| `kind`（class/interface/enum/annotation） | 除非新值是 `class`，否则保留先到的 | **Androguard 说了算**（它先跑，`pipeline.py:128-136` 早于 `138-142`） |
| `superclass` | `existing.superclass or cls.superclass` | **Androguard 说了算** |
| `interfaces` | 两个集合的并集 | 两边都保留 |
| `access_flags` | 两个集合的并集 | 两边都保留 |
| `method_count` / `field_count` | `max()` | 取**较大**的那个，不做取舍 |
| `provenance` | 拼接 | **两条都留**，谁也不覆盖谁 |

Androguard 先跑不是因为它更重要，是因为它是**结构**的正确来源（`docs/architecture/README.md`
里说的「a decompiler's text output is the wrong source for structure」）。但代码里的实际
依据就是执行顺序加上 `or` 短路——换成任何保留 `kind`/`superclass` 的实现结果都一样。

实测（`apk_a488e43e38c2b8e9`，`SharedConfig` 同时存在于两个 DEX）：

```json
"provenance": [
    {"tool": "androguard", "tool_version": "androguard 4.1.4",
     "locator": "androguard:classes.dex#com.example.multidex.SharedConfig"},
    {"tool": "androguard", "tool_version": "androguard 4.1.4",
     "locator": "androguard:classes2.dex#com.example.multidex.SharedConfig"},
    {"tool": "jadx", "tool_version": "1.5.2",
     "locator": "jadx:.../jadx/sources/com/example/multidex/SharedConfig.java"}
]
```

三个来源，一条都不丢。**没有「优先后端」这个概念——只有「每一类结论归谁」。**

---

## 3. provenance 具体记录了什么

### 3.1 字段

`Provenance` 定义在 `src/dexatlas/core/models.py:57-76`，只有四个字段：

| 字段 | 类型 | 含义 | 谁填的 |
|---|---|---|---|
| `tool` | `str` | 后端名（`jadx` / `apktool` / `androguard`） | `tools/base.py:205` |
| `tool_version` | `str \| None` | 后端版本字符串 | `tools/base.py:206` → `Backend.version()` |
| `apk_sha256` | `str` | 被分析 APK 的完整 SHA-256 | 调用方传入 |
| `locator` | `str` | **后端原生的**指回源头的指针 | 各 adapter 自己拼 |

`Sourced`（`models.py:79-87`）是混入类，给所有可追溯的产物加上 `provenance: list[Provenance]`。
注意是**列表**：一个产物可以有多个来源（见第 2 节）。

还有一个项目级的版本表 `Project.tool_versions: dict[str, str | None]`
（`models.py:285`），记录这次分析实际用到的三个后端版本，存进 `projects.tool_versions`
（`core/storage.py:52`）。它和 `provenance.tool_version` 是**两份独立的数据**——
下面 6.5 会说明它们会不一致。

### 3.2 locator 的实际格式

locator 的格式**每个后端都不一样**，因为 `Backend.provenance()`（`tools/base.py:202-209`）
只负责填 `tool` / `tool_version` / `apk_sha256`，`locator` 由各 adapter 自己拼：

| 后端 | 格式 | 真实样例（demo-app） |
|---|---|---|
| Apktool（manifest 证据） | `AndroidManifest.xml` | `AndroidManifest.xml` |
| Apktool（导出组件证据） | `AndroidManifest.xml#/application` | `AndroidManifest.xml#/application` |
| JADX | `jadx:<绝对路径>.java` | `jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81204c9f/jadx/sources/com/example/demo/Crypto.java` |
| Androguard（类） | `androguard:<dex 名>#<类全名>` | `androguard:classes.dex#com.example.demo.Crypto` |
| Androguard（方法） | `androguard:<dex 名>#<类全名>#<方法全名><描述符>` | `androguard:classes.dex#com.example.demo.Crypto#com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;` |
| Androguard（字段） | `androguard:<dex 名>#<类全名>#<字段名>` | `androguard:classes.dex#com.example.demo.MainActivity#TAG` |
| Androguard（交叉引用） | `androguard:<dex 名>#<调用方>-><被调方>` | `androguard:classes.dex#com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V->com.example.demo.Crypto.sign(...)Ljava/lang/String;` |
| Androguard（字符串） | `androguard:<dex 名>#str/<字符串前 64 字符>` | `androguard:classes.dex#str/api_key` |
| 任何后端的失败 | `error/<错误码>` | `error/not_installed` |

**这些 locator 里没有行号。** 这不是偷懒，是一个可以追溯的因果链：

- JADX 被以 `--no-debug-info` 调用（`tools/jadx/adapter.py:148`），反编译结果里没有行号表，
  所以 locator 只能指到**文件**，不能指到**行**。方法级别只能靠方法名区分。
- Androguard 的 locator 指的是 DEX 里的**符号**，不是字节码偏移量。

**JADX 的 locator 含绝对路径。** 它指向本次分析的工作区，换一台机器、换一个工作区目录，
同一个 locator 字符串就指向不同的东西。读一份别人的报告时，JADX 那一半的 locator
**不可直接复现**；能复现的是 Androguard 那一半（只依赖 DEX 名和符号名）。

### 3.3 provenance 没有记录什么

诚实起见，下面这些**当前不在** provenance 里：

- **行号。** 原因见上。
- **字符串常量出自哪个类、哪个方法。** `StringConstant` 有 `class_name` / `method_name`
  两个字段（`models.py:169-170`），但唯一的生产者 `AndroguardBackend._index_strings`
  从不填它们（`tools/androguard/adapter.py:362-367`）。实测全部为 `null`。
  一条字符串常量**只能定位到「哪个 DEX 里有这个字符串」，定位不到「哪段代码用了它」**。
- **资源。** 见 5.4。
- **Smali 内容的来源。** Smali 回退路径（`core/pipeline.py:262-264`、`279-281`）返回的是
  裸字符串，**不附带任何 provenance**。也就是说：当 `class_source` 返回 Smali 而不是 Java 时，
  调用方从返回值里**无法判断**这是 Apktool 的输出。只能靠「工作区里有没有 jadx 目录」间接推断。
- **同一产物的多个来源之间没有主次标记。** `provenance` 是一个扁平的列表，
  顺序即合并顺序（Androguard 在前，JADX 在后），但这个顺序**不表达可信度**。

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
│ androguard │ available │ androguard 4.1.4 │
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
`Project.new_id()` 取 SHA-256 的前 16 位（`models.py:292-295`）。
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
    "evidence_count": 6
  },
  "tools": {
    "jadx": "1.5.2",
    "apktool": "2.11.1",
    "androguard": "androguard 4.1.4"
  },
  "errors": []
}
```

`errors` 是空的——**三个后端都跑完了，没有任何一步降级**。

### 4.3 跑一遍 `multidex-app`

```console
$ uv run dexatlas analyze examples/multidex-app/multidex.apk --json multidex.json
✓ apk_a488e43e38c2b8e9 — 4 classes, 14 methods, 13 cross-references (2.7s)
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
    "method_count": 14,
    "reference_count": 13,
    "evidence_count": 7
  },
  "tools": {
    "jadx": "1.5.2",
    "apktool": "2.11.1",
    "androguard": "androguard 4.1.4"
  },
  "errors": []
}
```

**`method_count` 报 14，但数据库里只有 11 行。** 原因：Androguard 把两个 DEX 里的
`SharedConfig` 各索引一遍，得到 14 个方法；`methods` 表的主键是
`(project_id, class_name, name, descriptor)`（`core/storage.py:84`），重复的被
`INSERT OR REPLACE` 折叠掉了。`project.method_count = len(methods)` 取的是**折叠前**的列表长度
（`core/pipeline.py:154`）。详见 6.2。

### 4.4 五个自建样本的实际结果

全部在 4.1 的环境里跑出来，数字原样：

| 项目 id | APK | 大小 | 类 | 方法 | 交叉引用 | 证据 | 字符串 | 状态 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `apk_80a8fe0e81204c9f` | demo.apk | 2951 B | 5 | 8 | 23 | 6 | 63 | completed |
| `apk_a488e43e38c2b8e9` | multidex.apk | 2350 B | 4 | 14 | 13 | 7 | 44 | completed |
| `apk_d342e11b7931077d` | wide.apk | 1440 B | 4 | 11 | 15 | 5 | 29 | completed |
| `apk_2f8d476fb9e71ac4` | obfuscated.apk | 1892 B | 4 | 11 | 10 | 6 | 33 | completed |
| `apk_17c6da79f2d5467b` | strings.apk | 1547 B | 1 | 10 | 6 | 2 | 33 | completed |

`multidex.apk` 那一行的「方法」是 14（CLI 打印的 `method_count`），
`methods` 表实际 11 行。详见 6.2。

`strings-app` 只有 1 个类——它本来就是「一个类塞满字符串」的样本。

**五个样本、26 条证据，全部是 `declaration` / `verified`：**

```console
$ python -c "import sqlite3; c=sqlite3.connect(r'C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/dexatlas.db'); print(c.execute('SELECT kind, level, COUNT(*) FROM evidence GROUP BY kind, level').fetchall())"
[('declaration', 'verified', 26)]
```

**注意 `kind` 只有 `declaration` 一种。** `EvidenceKind` 定义了 5 种
（`models.py:229-234`），但管道里只产出两种：`declaration` 和 `observation`（后端失败时）。
`cross_reference`、`behaviour`、`code_located` **一次都不会出现**——
`EvidenceBuilder.add_method_references`（`core/evidence.py:131-146`）这个方法
**在 `src/` 里没有任何调用点**。交叉引用确实被索引了（`xrefs` 表），但它**从不变成证据行**。
详见 6.4。

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
    [{'tool': 'androguard', 'tool_version': 'androguard 4.1.4', 'apk_sha256': '80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9', 'locator': 'androguard:classes.dex#com.example.demo.MainActivity.onCreate(Landroid/os/Bundle;)V->com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;'}]
```

**第三步**：打开工作区里 Androguard 说的那个 DEX，对照 Apktool 解出的 Smali：

```console
$ cat "C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81204c9f/apktool/smali/com/example/demo/MainActivity.smali"
```

对应仓库里提交的同一份源码 `examples/demo-app/smali/com/example/demo/MainActivity.smali`：

```smali
    invoke-static {v0, v1}, Lcom/example/demo/Crypto;->sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;
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
│ androguard │     available │ androguard 4.1.4 │
└────────────┴───────────────┴──────────────────┘

$ uv run dexatlas analyze examples/demo-app/demo.apk
✓ apk_80a8fe0e81204c9f — 4 classes, 8 methods, 23 cross-references (1.2s)
```

两处变化，都值得注意：

1. **类数从 5 掉到 4。** 少掉的那个是 `com.example.demo.R`——它**只存在于 JADX 的输出里**，
   DEX 里没有这个类（见 5.2）。
2. **缺后端会变成一条证据**（`core/evidence.py:76-91`）：

```json
{
  "id": "E-0006",
  "kind": "observation",
  "level": "verified",
  "summary": "jadx did not complete: jadx is not installed or not on PATH",
  "provenance": [
    {"tool": "jadx", "tool_version": null,
     "apk_sha256": "80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9",
     "locator": "error/not_installed"}
  ]
}
```

这时候 `class_source` 会落到 Smali（`core/pipeline.py:257-264`）：

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
    com.example.wide.HandlerFactory.dispatch(Lcom/example/wide/Handler; Ljava/lang/String;)Ljava/lang/String;  →
  com.example.wide.Handler.handle(Ljava/lang/String;)Ljava/lang/String;
  $ echo "exit=$?"
  exit=0
  ```

  **`JsonHandler.handle` 和 `XmlHandler.handle` 看起来「没有调用者」**，
  而实际上运行时它们很可能就是被调用的那一个。
  **静态交叉引用在多态处会漏掉实现类。** 想要实现类的调用者，得自己沿
  `ClassRef.interfaces`（`models.py:110`）往下展开——DexAtlas 不做这件事。
  > 补充：DEX 编码的是**声明类型**（这里是接口），不是子类。实现类只有在运行时多态分派时
  > 才知道，所以任何静态工具都拿不到「运行时被调用的实现」。

- **交叉引用靠遍历字节码，没有缓存。** Androguard 4.x 移除了 xref 缓存
  （`tools/androguard/adapter.py:7-9`），所以每条边都是扫指令得到的。
  这条遍历有硬上限：`DEFAULT_METHOD_LIMIT = 200_000`、
  `DEFAULT_INSTRUCTION_LIMIT = 5_000_000`、`DEFAULT_STRING_LIMIT = 50_000`
  （`tools/androguard/adapter.py:47-49`）。**触到上限时索引会被截断，而且只在日志里
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

### 5.2 JADX

- **JADX 会产出 DEX 里根本不存在的类。** demo-app 的第 5 个类 `com.example.demo.R`
  只有一条 provenance，是 JADX 的：

  ```console
  $ uv run dexatlas classes apk_80a8fe0e81204c9f
com.example.demo.Crypto class
  androguard androguard 4.1.4 -> androguard:classes.dex#com.example.demo.Crypto
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81
204c9f/jadx/sources/com/example/demo/Crypto.java
com.example.demo.MainActivity class
  androguard androguard 4.1.4 -> 
androguard:classes.dex#com.example.demo.MainActivity
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81
204c9f/jadx/sources/com/example/demo/MainActivity.java
com.example.demo.NetworkClient class
  androguard androguard 4.1.4 -> 
androguard:classes.dex#com.example.demo.NetworkClient
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81
204c9f/jadx/sources/com/example/demo/NetworkClient.java
com.example.demo.R class
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81
204c9f/jadx/sources/com/example/demo/R.java
com.example.demo.SyncService class
  androguard androguard 4.1.4 -> 
androguard:classes.dex#com.example.demo.SyncService
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_80a8fe0e81
204c9f/jadx/sources/com/example/demo/SyncService.java
  ```

  `R` 是资源 ID 容器类，由 aapt2 在打包时生成资源表，**DEX 里没有它**。
  Androguard 索引不到它，Apktool 也解不出对应的 Smali。
  **JADX 产出的类不一定在字节码里存在**——这是一个类级「多出来的」结论。

- **JADX 的输出可能不是反编译结果，而是占位符。** JADX 对付不了的方法会写一段
  `/* Method could not be decompiled */`。DexAtlas 有检测它的正则
  （`_DECOMPILE_FAILED_RE`，`tools/jadx/adapter.py:34-39`）和
  `JadxBackend.method_decompiled()`（`tools/jadx/adapter.py:232-234`），
  **但这个方法在 `src/` 里没有任何调用点**，只有测试在用：

  ```console
  $ grep -rn "method_decompiled" --include=*.py src tests | sort
  src/dexatlas/tools/jadx/adapter.py:232:    def method_decompiled(source: str) -> bool:
  tests/test_jadx_parsing.py:165:    assert JadxBackend.method_decompiled('void f() { Log.d("a"); }') is True
  tests/test_jadx_parsing.py:167:        JadxBackend.method_decompiled(
  tests/test_jadx_parsing.py:172:    assert JadxBackend.method_decompiled("// JADX ERROR: Method code generation failed") is False
  tests/test_jadx_parsing.py:173:    assert JadxBackend.method_decompiled("/* Method could not be decompiled */") is False
  ```

  同时 DexAtlas 是以 `--show-bad-code` 调 JADX 的（`tools/jadx/adapter.py:148`），
  那个选项的含义就是「尽力输出，不行就输出残缺代码」。
  **结论：管道无法告诉你某个方法是真反编译还是占位符。** 方法表里的
  `decompiled` 字段也帮不上忙——它来自 Androguard 的 `bool(method.get_code())`
  （`tools/androguard/adapter.py:307`），含义是「这个方法有字节码」，
  **不是「JADX 反编译成功了」**。字段名有误导性。

- **JADX 的 per-class 错误日志没有被采集。** `summarize_jadx_log()`
  （`tools/jadx/adapter.py:356-374`）能解析 `sources/resources/log/error.log`，
  同样**在 `src/` 里没有调用点**：

  ```console
  $ grep -rn "summarize_jadx_log" --include=*.py src tests | sort
  src/dexatlas/tools/jadx/adapter.py:356:def summarize_jadx_log(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
  src/dexatlas/tools/jadx/adapter.py:377:__all__ = ["JadxBackend", "read_text", "summarize_jadx_log"]
  ```

  所以「哪些类反编译失败了」这个信息**不在索引里、不在证据里、也不在报告里**。

- **locator 含绝对路径**，不可跨机器复现（见 3.2）。

- **在这 5 个自建样本上，JADX 一次都没失败。** 五个样本的
  `jadx/sources/resources/log/error.log` 都不存在，`errors` 全空。
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
  而 provenance 只写了 `AndroidManifest.xml` 一个。

- **manifest 里的 `exported` 属性只有显式写了才为 `true`。**
  `ManifestComponent.exported` 是 `bool | None`（`models.py:190`），
  `_parse_bool` 把没写的当 `None`（`tools/apktool/adapter.py:283-286`）。
  `exported_components` 只挑 `exported is True`（`models.py:208-209`）。
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
  （`core/evidence.py:80`、`97`、`114`、`139`，`core/pipeline.py:193`）。
  这两个等级是给 Phase 2 的模型输出准备的。

- **原生库（`.so`）只被统计，不被分析。** `ApkMetadata.native_libraries`
  是从 ZIP 目录里列出来的文件名（`core/ingest.py:59-61`），
  没有 ELF 解析、没有 JNI 关系。Phase 3 才计划接 Ghidra。

- **没有动态分析。** 全部结论都是静态的。

---

## 6. 读这份文档时会撞上的六处不一致

这些不是猜测，是这次为了写这份文档而实际跑出来的。它们**没有被修**——
修它们要动 `src/`，超出本文档的范围。列在这里，是因为一份声称讲「证据来源」的文档
如果藏起这些，就不值得读。

### 6.1 方法 id 的两种写法，`dexatlas xrefs` 只认其中一种

`dexatlas methods` 打印的方法 id 来自 Androguard 的 `get_descriptor()`，
**参数之间有空格**：

```console
$ uv run dexatlas methods apk_80a8fe0e81204c9f
┌────────────────────────────────────────────────────────┬────────────────────┐
│ Method                                                 │ Flags              │
├────────────────────────────────────────────────────────┼────────────────────┤
│ com.example.demo.Crypto.digestOf(Ljava/lang/String;)L… │ public static      │
│ com.example.demo.Crypto.obfuscate(Ljava/lang/String;)… │ public static      │
│ com.example.demo.Crypto.sign(Ljava/lang/String;        │ public static      │
│ Ljava/lang/String;)Ljava/lang/String;                  │                    │
│ com.example.demo.MainActivity.<init>()V                │ constructor public │
│ com.example.demo.MainActivity.describe(Ljava/lang/Str… │ public static      │
│ com.example.demo.MainActivity.onCreate(Landroid/os/Bu… │ protected          │
│ com.example.demo.NetworkClient.post(Ljava/lang/String; │ public static      │
│ Ljava/lang/String;)Ljava/lang/String;                  │                    │
│ com.example.demo.SyncService.onBind(Landroid/content/… │ public             │
└────────────────────────────────────────────────────────┴────────────────────┘
```

而 `dexatlas xrefs` 要的是**没有空格**的写法。把前者原样复制过去：

```console
$ uv run dexatlas xrefs apk_80a8fe0e81204c9f "com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
No callers of com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;.
$ echo "exit=$?"
exit=1
```

去掉空格就有结果（见 4.5 第一步）。

根因：Androguard 4.1.4 的 `get_descriptor()` 返回
`'(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;'`（带空格），
而 `_parse_dalvik_reference`（`tools/androguard/adapter.py:403`）在解析调用目标时
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
apk_80a8fe0e81204c9f xrefs=23  exactly-joinable-to-methods=1
apk_a488e43e38c2b8e9 xrefs=13  exactly-joinable-to-methods=0
apk_d342e11b7931077d xrefs=15  exactly-joinable-to-methods=3
```

（剩下的边指向 `java.lang.StringBuilder.append` 之类**不在这个 APK 里**的库方法，
本来就 join 不上，那是正常的。demo-app 唯一 join 上的那一条是 `MainActivity.describe`，
它的描述符只有一个参数，所以两边都没有空格。）

**规律：描述符里有 2 个及以上参数时，`get_descriptor()` 才在分号后插入空格；
1 个参数时没有空格。** 所以这个方法 id 分歧只影响多参数方法。

> 注意：`docs/reports/phase1-execution-report.md` 3.1 节说
> 「方法表里 `get_descriptor()` 返回的是规范形式」（无空格）。
> **在 androguard 4.1.4 上实测不是这样**——它返回带空格的。
> 那次修复解决的是「调用目标」这一侧，没解决「方法表」这一侧。

### 6.2 `method_count` 报的数比表里的行数多

见 4.3。multidex-app 报 14，`methods` 表 11 行。
`project.method_count` 数的是折叠前的列表（`core/pipeline.py:154`），
`methods` 表的主键会折叠重复（`core/storage.py:84`）。
**类在多个 DEX 里重复定义时就会不一致。**

### 6.3 `dexatlas classes` 只显示前两条 provenance

`cli/main.py:189` 是 `for source in cls.provenance[:2]:`。
multidex-app 的 `SharedConfig` 有**三条**来源（两个 DEX + JADX），CLI 只显示前两条：

```console
$ uv run dexatlas classes apk_a488e43e38c2b8e9
com.example.multidex.PayloadLoader class
  androguard androguard 4.1.4 -> 
androguard:classes2.dex#com.example.multidex.PayloadLoader
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_a488e43e38
c2b8e9/jadx/sources/com/example/multidex/PayloadLoader.java
com.example.multidex.PrimaryHelper class
  androguard androguard 4.1.4 -> 
androguard:classes.dex#com.example.multidex.PrimaryHelper
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_a488e43e38
c2b8e9/jadx/sources/com/example/multidex/PrimaryHelper.java
com.example.multidex.SecondaryHelper class
  androguard androguard 4.1.4 -> 
androguard:classes2.dex#com.example.multidex.SecondaryHelper
  jadx 1.5.2 -> 
jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_a488e43e38
c2b8e9/jadx/sources/com/example/multidex/SecondaryHelper.java
com.example.multidex.SharedConfig class
  androguard androguard 4.1.4 -> 
androguard:classes.dex#com.example.multidex.SharedConfig
  androguard androguard 4.1.4 -> 
androguard:classes2.dex#com.example.multidex.SharedConfig
```

第三条（JADX）被截掉了。要拿完整列表，用 REST API（`api/app.py:236-239` 返回完整的
`model_dump`）：

```console
$ curl -s "http://127.0.0.1:8137/projects/apk_a488e43e38c2b8e9/classes?prefix=com.example.multidex.SharedConfig" | python -m json.tool
```

```json
{
    "project_id": "apk_a488e43e38c2b8e9",
    "total": 1,
    "classes": [
        {
            "provenance": [
                {
                    "tool": "androguard",
                    "tool_version": "androguard 4.1.4",
                    "apk_sha256": "a488e43e38c2b8e9292ba4d3badf15fb73167bda92c2343cb2b656cdfd309d55",
                    "locator": "androguard:classes.dex#com.example.multidex.SharedConfig"
                },
                {
                    "tool": "androguard",
                    "tool_version": "androguard 4.1.4",
                    "apk_sha256": "a488e43e38c2b8e9292ba4d3badf15fb73167bda92c2343cb2b656cdfd309d55",
                    "locator": "androguard:classes2.dex#com.example.multidex.SharedConfig"
                },
                {
                    "tool": "jadx",
                    "tool_version": "1.5.2",
                    "apk_sha256": "a488e43e38c2b8e9292ba4d3badf15fb73167bda92c2343cb2b656cdfd309d55",
                    "locator": "jadx:C:/Users/admin/AppData/Local/Temp/dexatlas-prov-ws/projects/apk_a488e43e38c2b8e9/jadx/sources/com/example/multidex/SharedConfig.java"
                }
            ],
            "name": "com.example.multidex.SharedConfig",
            "kind": "class",
            "superclass": "java.lang.Object",
            "interfaces": [],
            "access_flags": [
                "public"
            ],
            "method_count": 3,
            "field_count": 0
        }
    ]
}
```

### 6.4 交叉引用永远不产生证据行

`EvidenceKind.CROSS_REFERENCE` 存在（`models.py:231`），
`EvidenceBuilder.add_method_references` 也存在（`core/evidence.py:131-146`），
**但 `src/` 里没有任何地方调用它**：

```console
$ grep -rn "add_method_references" --include=*.py src tests | sort
src/dexatlas/core/evidence.py:131:    def add_method_references(
tests/test_evidence.py:146:    builder.add_method_references(method, references)
tests/test_evidence.py:156:    builder.add_method_references(
```

**所以交叉引用只是索引数据，不是证据。** 报告里看不到「谁调用了什么」这一层，
只能在索引里查。`EvidenceKind.CODE_LOCATED` 和 `EvidenceKind.BEHAVIOUR` 同理，
在 `src/` 里都没有生产者。

### 6.5 「已导出组件」这条证据的 `tool_version` 是 `null`

`core/evidence.py:103-129` 的 `add_exported_components` 硬编码了 `tool_version=None`，
**即使 apktool 的版本是已知的**。对比同一份报告里 manifest 那条证据：

```console
$ uv run dexatlas analyze examples/demo-app/demo.apk -o report.md
```

| 证据 | 来源 |
|---|---|
| `E-0001` Package com.example.demo (...) | `apktool 2.11.1 -> AndroidManifest.xml` |
| `E-0006` 2 component(s) are explicitly exported | `apktool -> AndroidManifest.xml#/application` |

**同一条工具链的两条证据，一条带版本一条不带。** 报告里的
`Tool versions: androguard androguard 4.1.4, apktool 2.11.1, jadx 1.5.2` 那行
（`reports/markdown.py:90-96`）是从 `Project.tool_versions` 来的，
和 per-evidence 的 `tool_version` 是两份数据（见 3.1）。

顺带一提 `Provenance.ref()`（`models.py:68-76`）的输出是
`f"{tool} {tool_version} -> {locator}"`，所以 Androguard 那条会显示成
`androguard androguard 4.1.4 -> ...`——「androguard」出现两次。不是 bug，是拼接的结果。

### 6.6 `xrefs` 表里可能有重复的 caller/callee 对

`Project.reference_count` 数的是 Androguard 遍历出来的边数，
`xrefs` 表没有主键（`core/storage.py:98-104`），重复的 caller/callee 对会**各自保留**
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
| 代码在哪儿 | `provenance[].locator`（格式见 3.2，**没有行号**） |
| 这个结论有多硬 | `Evidence.level`（Phase 1 全部是 `verified`） |
| 后端有没有降级 | `Project.errors` / 报告的「Backend errors」段 / `kind=observation` 的证据 |
| 想看完整 provenance 列表 | 用 REST API 的 `/classes`，别用 CLI（6.3） |
| 想查调用者 | `dexatlas xrefs`，**方法 id 不能带空格**（6.1） |
| 想知道 JADX 有没有反编译失败 | **查不到**，看 5.2 |
| 想知道字符串在不在资源里 | **查不到**，看 5.4 |
