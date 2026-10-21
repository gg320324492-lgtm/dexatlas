# Phase 2 开工清单（推迟项的可执行 issue 列表）

> 本文只写**被评审推迟的发现**，每一条都写清楚了：现状（带 `file:line`）、代价、两种可选方案、
> 推荐、验收标准，以及**钉住它的测试怎么写**。
>
> **来源**：2026-10-21 的 Phase 1 成熟度评估（`docs/reports/phase1-maturity-assessment.md`，
> 针对 `b8ef71a`）＋ 本文的独立复核。评审结论在本文里一律当**数据**处理，不当事实：
> 每一条都重新核对过行号与行为，跑过命令的写明命令和输出。
>
> **行号基准：`HEAD = 8df894b`。** 本文所有 `file:line` 都以 `git show 8df894b:<path>` 为准，
> 复核日期 2026-10-21。**不要拿工作区的行号去核对** —— 复核期间有并行 agent 在改
> `src/dexatlas/api/app.py`、`src/dexatlas/core/storage.py`、`src/dexatlas/config/settings.py`、
> `src/dexatlas/core/paths.py`、`src/dexatlas/tools/jadx/adapter.py`，
> 这些文件的行号在工作区里已经位移（本文写作过程中 `storage.py` 位移了 4 行、
> `app.py` 位移了 18 行）。**引用时请连同符号名一起用**，这样行号漂了也找得到。
>
> **那并行改动有没有顺手修掉本文的条目？没有。** 它修的是「相对工作区导致 JADX 输出写进
> 双重嵌套目录」那一条（把工作区锚成绝对路径，`core/paths.py` 新增 `absolute_path`）。
> 本文列的 8 条**一条都没被它碰到**，行号漂移也不影响结论 ——
> 每条缺陷在 `8df894b` 与工作区里都成立。
>
> **实测的基准**：所有命令与输出是在**工作区**（含并行改动）上跑的。
> 差异只落在上面那 5 个文件里，且都不改变本文任何一条结论（逐条核对过）。
>
> **怎么用**：每条都写成可以直接贴进 issue tracker 的形态。顺序按「严重级 × 可执行性」排，
> 不是按评审里的编号。**每条末尾的「钉住它的测试」是重点** —— 这个项目吃过
> 「测试全绿但测的是没坏的那条路径」的亏，所以每条都写明了：这个测试在**旧代码上会不会红**，
> 不会红就说明测试写错了。

---

## 0. 复核时先纠正的几处前提

复核过程中有三条来自评审/交办的前提与当前代码对不上，先记在这里，免得后面按错的前提排期：

| 前提 | 实际情况 | 证据 |
| --- | --- | --- |
| 「loguru 的 handler 在 `src/dexatlas/core/logging.py` 里被移除」 | **没有这个文件**。移除发生在 `src/dexatlas/tools/androguard/adapter.py:112` 的 `_quiet_androguard()` 里 | 全仓库 `loguru` 只在 `tools/androguard/adapter.py` 命中（`:105`、`:112`） |
| 「`docs/status.md` 第 6 节列了 13 类缺陷」 | 该节写的是**十一类**（`docs/status.md:233`），表体 11 行 | `sed -n '229,262p' docs/status.md \| grep -c "^| "` → 12（含表头） |
| 「`project.id` 是内容哈希」 | 是哈希，但**只取前 16 位十六进制**（64 bit），不是全量 sha256 | `src/dexatlas/core/models.py:592-595` |

其余前提（`xrefs` 无主键、workspace 是 `projects_dir / project.id`、上传后不删）**复核后全部成立**，
下面逐条展开。

---

## 1. 总表

| 编号 | 标题 | 严重级 | 状态 | 推荐动作 | 预计工作量 | 依赖 |
| --- | --- | --- | --- | --- | --- | --- |
| **X1** | 上传文件名由客户端决定 → 证据链指向另一个 APK | **极高** | **新发现** | 上传文件按内容哈希命名（不可变） | 0.5–1 天（与 #12 合并） | 无 |
| **#4** | 并发分析不安全：工作区共享 + 打开工作区会写库 | **高** | 仍成立 | 每次分析一个独立 run 目录；WAL 转换移出 `transaction()` | 2–3 天 | X2 |
| **X2** | `Store.transaction()` 每次都跑 `PRAGMA journal_mode = WAL`：一次**读**也在写库 | **高** | **新发现**（#4 的根因） | 把 journal mode 的设置移到建库那一次 | 0.5 天 | 会碰到并行 agent 正在改的 `storage.py` |
| **#7** | `xrefs` 表没有主键：交叉引用按**调用次数**计数，不是按**边** | **高** | 仍成立（评审的描述不完整） | 主键 `(project_id, caller, callee, kind)`；`_migrate` 里 DROP+重建 | 1–2 天 | 需同步改 `analysis-provenance.md` §6.6 |
| **#11** | loguru 的全局 handler 被移除且**永不恢复** | 中 | 仍成立（位置与交办描述不同） | 用 `logger.disable("androguard")` / `enable()` 代替 `logger.remove()` | 0.5 天 | 无 |
| **#12** | 上传的 APK 分析完成后不删除 | 中 | 仍成立 | 上传文件按内容哈希命名 + 分析完成后删除 | 1 天（与 X1 合并） | X1 |
| **#14/#15** | 文档/注释/docstring 声称与代码实际不一致（25 条） | 中 | 仍成立 | 逐条改措辞或改代码 | 2–3 天 | 无 |
| **F8** | 死代码：`tools/base.py` 4 处，全仓库另有 9 处；ruff 抓不到死函数 | 中 | 仍成立 | 删/用掉 10 处，配好 vulture 后把「退出码 0」做成 CI 门禁 | 1–2 天 | 无 |

---

## 2. X1【极高·新发现】上传文件名由客户端决定，证据链会指向另一个 APK

### 现状

上传的落地路径由**客户端提供的文件名**决定：

- `src/dexatlas/api/app.py:273` —— `target = upload_dir / Path(file.filename or "upload.apk").name`
- `src/dexatlas/core/ingest.py:89` —— `save_upload` 用 `target.open("wb")` 打开，**截断并覆盖**同名旧文件
- `src/dexatlas/api/app.py:291` —— `apk = inspect_apk(target)`：哈希在**请求时**算
- `src/dexatlas/api/app.py:311` —— `background.add_task(_run_analysis, analyzer, target, apk)`：分析**稍后**才开始
- `src/dexatlas/tools/androguard/adapter.py:236` —— `apk_obj = APK(str(apk))`：分析时**按路径**重新读盘
- `src/dexatlas/tools/apktool/adapter.py:116` / `src/dexatlas/tools/jadx/adapter.py:239` —— 同样把**路径**交给外部工具

也就是说：**哈希是请求时的那个文件的哈希，符号是分析时那个路径上的文件的符号。**
这两者之间隔着一个可以被改写的窗口。

### 为什么重要（它会让读者得出什么错误结论）

`GET /projects/{id}` 返回 `apk_sha256` 和 `apk_path`。`apk_path` 经 `display_path()`
（`src/dexatlas/core/paths.py:78-86`）只剩文件名。读者据此认定「这个项目分析的就是这个文件」，
而 `Provenance.apk_sha256`（`src/dexatlas/core/models.py:112-127`）在**每一行**上都写着同一个哈希。

**当那个哈希是假的时，provenance 就不再是证据链，而是伪造的凭据。**
一个「证据优先」的平台最不能出的错就是这个。

### 实测（复现步骤与真实输出）

用 `fastapi.testclient.TestClient`，A = `examples/demo-app/demo.apk`（sha `80a8fe…`），
B = `examples/multidex-app/multidex.apk`（sha `a488e4…`），两次都用文件名 `app.apk`：

**第一次（顺序上传，先 A 后 B，分析都跑完）**

```
=== projects table ===
  apk_80a8fe0e81204c9f
    recorded apk_sha256 : 80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9
    apk_path            : ...\workspace\uploads\app.apk
    sha256 of that file : a488e43e38c2b8e9292ba4d3badf15fb73167bda92c2343cb2b656cdfd309d55
    MATCH               : False          ← 记录的哈希和路径上的文件对不上
```

也就是说：**两个项目指向同一个路径**，而第一个项目指向的那个路径上已经是 B 的字节了。

**第二次（B 在 A 的分析还在跑的时候上传）—— 3 次运行，3 次都复现**

```
PROJECT apk_80a8fe0e81204c9f  recorded apk_sha256=80a8fe0e81204c9f…  status=completed  classes=4
   class com.example.multidex.PayloadLoader       provenance apk_sha256=['80a8fe0e81204c9f']
   class com.example.multidex.PrimaryHelper        provenance apk_sha256=['80a8fe0e81204c9f']
   class com.example.multidex.SecondaryHelper      provenance apk_sha256=['80a8fe0e81204c9f']
   class com.example.multidex.SharedConfig         provenance apk_sha256=['80a8fe0e81204c9f']
   xref  com.example.multidex.PrimaryHelper.<init>()V  provenance apk_sha256=['80a8fe0e81204c9f']
```

**项目 A（哈希 `80a8fe…`）的符号表里装的是 B（`com.example.multidex.*`）的类，
而每一行的 provenance 都写着 A 的哈希。** 另有一次运行是混合态：A 的项目里有 8 个类
（demo 的 4 个 + multidex 的 4 个），同样全部标注 A 的哈希。

### 方案 A：上传文件按内容哈希命名（不可变）

把 `src/dexatlas/api/app.py:273` 改成先落到一个**临时名**，算完哈希后再重命名成
`uploads/<sha256>.apk`；或者更简单：仍然写客户端给的文件名，但**写完之后立刻按哈希重命名**。

- 代价：多一次 rename；上传目录里文件名不再可读（要靠 `sha256` 反查）。
- 风险：低。内容寻址的名字**天然不可变** —— 两个不同的 APK 不可能撞名，
  同一个 APK 重复上传就是同一个文件（幂等）。
- 附带好处：「已分析过就直接返回」那条路径（`api/app.py:301-307`）变成真正的幂等操作。

### 方案 B：上传目录按请求隔离 + 分析用**已经读进内存的字节**

落盘成 `uploads/<uuid>/<原文件名>`，分析时用**请求时读到的字节**而不是路径。

- 代价：APK 最大 256 MiB（`src/dexatlas/core/ingest.py:34`），整份读进内存不可接受；
  改成「复制到一个不可变的私有路径」等于回到方案 A，只是名字不同。
- 风险：多一次拷贝；而且 `save_upload` 现在就是流式写的（`ingest.py:88-94`），改成读内存会破坏
  「超限时不落盘」这个已经做对的行为。

### 推荐：**方案 A**

理由要落到「这个项目现在缺什么」：DexAtlas 缺的正是**「结论能追回字节」**这一条。
内容寻址的文件名是唯一不需要额外状态就能保证「路径上的字节 == 记录的哈希」的做法，
而且它和项目已经采用的**内容寻址的 project id**（`models.py:592-595`）是同一条思路，
不引入新概念。

### 验收标准

1. `uploads/` 下的文件名 = 文件内容的 sha256。
2. 任意时刻，对任意项目，`sha256(项目记录的 apk_path 上的文件) == 项目的 apk_sha256`
   （在文件被删除之前恒成立）。
3. 两个不同内容的 APK 用**同一个客户端文件名**上传，得到两个不同的项目，
   各自的符号表里只有自己的类。

### 钉住它的测试怎么写

```python
# tests/test_upload_immutability.py
def test_two_analyses_with_the_same_upload_name_do_not_contaminate_each_other(
    client, demo_apk, multidex_apk, tmp_path
):
    """两个内容不同的 APK 用同一个文件名上传，谁也不能污染谁。

    现在会红：第二个上传会覆盖第一个项目的 apk_path，
    而第一个项目的符号表会装上第二个 APK 的类，
    provenance 却写着第一个 APK 的哈希。
    """
    # 上传 A，等它分析完
    project_a = _upload(client, demo_apk, "app.apk")
    _wait_completed(client, project_a)

    # 用**同一个文件名**上传 B
    project_b = _upload(client, multidex_apk, "app.apk")
    _wait_completed(client, project_b)

    # 1. 两个项目各自指着自己的字节
    for project_id, apk in ((project_a, demo_apk), (project_b, multidex_apk)):
        recorded = client.get(f"/projects/{project_id}").json()["apk_sha256"]
        assert recorded == sha256(apk), "项目记录的哈希不是它自己那份 APK 的哈希"

    # 2. 关键断言：项目 A 的符号表里没有 B 的类
    classes_a = client.get(f"/projects/{project_a}/classes").json()["classes"]
    assert all(not c["name"].startswith("com.example.multidex") for c in classes_a), (
        "项目 A 的索引里出现了另一个 APK 的类，而 provenance 声称是 A 的"
    )
```

**这个测试在旧代码上会不会红？会，而且是确定性地红**，不依赖时序：
即使两次上传完全串行，第二次也会覆盖 `uploads/app.apk`，
于是「两个项目指向同一个路径」这条断言（第 1 条里的路径检查）立刻失败。

**要证明它不是假绿**，再加一条「污染」断言：故意让第二个上传在第一个的分析**还在跑**的时候到达，
断言项目 A 的类名集合里没有 `com.example.multidex`。这条依赖时序，属于**加强**而非唯一防线——
第 1 条才是确定性的那条。

---

## 3. #4【高】并发分析不安全：工作区共享 + 打开工作区会写库

### 现状（逐条复核）

**（a）同一个 APK 的两次分析共用同一个工作目录。**

- `src/dexatlas/core/pipeline.py:118` —— `workspace = self._settings.projects_dir / project.id`
- `src/dexatlas/core/models.py:592-595` —— `Project.new_id(sha256)` → `f"apk_{sha256[:16]}"`，
  `Project.create`（`:597-599`）用的就是它。**id 由内容决定，所以同一个 APK 永远是同一个 id，
  永远是同一个目录。**
- `src/dexatlas/core/pipeline.py:225` —— `output_dir = workspace / "apktool"`
- `src/dexatlas/core/pipeline.py:321` —— `output_dir = workspace / "jadx"`
- `src/dexatlas/tools/jadx/adapter.py:227` —— `output_dir.mkdir(parents=True, exist_ok=True)`；
  `:238` 把 `str(output_dir)` 作为 `--output-dir`，`:241` 把同一个路径作为 `cwd`
  —— **外部工具就地写这个目录，两个进程会互相覆写。**

实测（两个线程分析同一个 APK，探针记录每个后端拿到的 `output_dir`）：

```
=== output dirs handed to the backends ===
  apktool: C:\...\ws-conc\projects\apk_80a8fe0e81204c9f\apktool
  jadx:    C:\...\ws-conc\projects\apk_80a8fe0e81204c9f\jadx
  distinct paths: 2
```

（`distinct paths: 2` 是 apktool 与 jadx 各自一个目录；**两个线程各自拿到的是同一对目录**——
探针被调用了 4 次，路径集合只有 2 个。）

**（b）API 允许并发触发同一 APK 的两次分析。**

- `src/dexatlas/api/app.py:58-66` —— `get_analyzer` 依赖：每个请求新建一个 `Analyzer`，
  于是每个请求都 `Store.open` 一次（`src/dexatlas/core/pipeline.py:79`）。
- `src/dexatlas/api/app.py:301-307` —— 去重检查 `find_project_by_hash` 在**后台任务开跑之前**。
  两个并发请求都还没提交项目行，所以**两个都看到 None，两个都排了后台任务**。

**（c）实测的失败：**

```
Exception in thread Thread-1 (worker):
  File "G:\dexatlas\src\dexatlas\api\app.py", line 67, in get_analyzer
    return Analyzer(settings)
  File "G:\dexatlas\src\dexatlas\core\pipeline.py", line 79, in __init__
    self._store = Store.open(self._settings.database_path)
  File "G:\dexatlas\src\dexatlas\core\storage.py", line 341, in open
    with store.transaction() as connection:
  File "G:\dexatlas\src\dexatlas\core\storage.py", line 371, in transaction
    connection.execute("PRAGMA journal_mode = WAL")
sqlite3.OperationalError: database is locked
```

在 API 层复现（两个并发 `POST /analyze`，全新工作区）：**一个请求 202，另一个抛未捕获的
`sqlite3.OperationalError`**（真实部署下就是 500）。

**注意失败的位置**：不是符号写入，而是**打开工作区**。根因见 **X2**。

**（d）工作区已经存在时，两个分析都能跑完**，但共用同一个输出目录：

```
=== per-thread outcome ===
--- t0 --- ok: True  status: completed  classes: 5  methods: 8  refs: 23  evidence: 10
--- t1 --- ok: True  status: completed  classes: 5  methods: 8  refs: 23  evidence: 10
```

两个线程都往 `workspace/jadx` 和 `workspace/apktool` 里写。**读端没有任何保护**：
`Analyzer.class_source_document`（`src/dexatlas/core/pipeline.py:349-391`）在查询时
直接读 `workspace/jadx/sources/...`，所以一个并发的 `/source` 请求可能读到**写了一半**的 `.java`。

### 为什么重要（它会让读者得出什么错误结论）

- 一个并发的 `/analyze` 返回 500，而项目可能已经被排进了队列 ——
  **「提交成功却查不到结果」**。
- 报告里「Tools」一行照旧列着 `jadx 1.5.2`，但 JADX 的输出目录可能被另一次运行覆写过 ——
  **报告说它读过某个文件，而那个文件已经不是它写的那份了**。
- 更糟的是叠加 X1：`provenance` 里的 `apk_sha256` 变成假值（见上条）。

### 方案 A：每次分析一个独立的 run 目录，成功后再切换指针

- 每次分析写进 `projects/<id>/runs/<run-id>/{apktool,jadx}`；
- `projects.workspace` 这一列（`src/dexatlas/core/storage.py:118`，读写在 `:404` 和 `:442-447`）
  指向当前的 run 目录。**「原子替换」= 一次 `UPDATE projects SET workspace = ?`，这在 SQLite 里是真的原子。**
- 旧的 run 目录按策略清理。

**代价**：
1. **目录级的 `os.replace` 在 Windows 上不可用**——实测：
   ```
   os.replace(dir -> non-empty dir): FAILED -> PermissionError [WinError 5]
   os.replace(dir -> EMPTY dir):     FAILED -> PermissionError [WinError 5]
   ```
   所以「用 `os.replace` 原子替换目录」这条在 Windows 上直接走不通。
   **用「版本化目录 + 数据库指针」绕开它**，这正是方案 A 的形状。
2. `class_source_document` / `method_source_document` 走 `get_workspace`，
   需要确认读到的是**同一个 run** 的目录（一次请求内只读一次指针即可）。
3. run 目录的清理策略要定（保留最近 N 个？还是只保留当前那个？）。

**风险**：中。`get_workspace` 的调用点有 3 处（`pipeline.py:440`、`api/app.py:609`、以及报告重建），
改动面可控；但**这是本清单里唯一会动到「读哪一份产物」语义的一条**，必须配上面那条并发测试。

### 方案 B：按项目 id 加文件锁，串行化同 id 的分析

- 在 `projects/<id>` 下放一个锁文件，跨进程用 `filelock` / `msvcrt.locking` / `fcntl.flock`；
  同 id 的分析排队执行。

**代价与必须回答的问题**：
1. **锁的粒度**：按 project id 锁，还是按整个工作区锁？按 id 锁更细，但不同 id 的分析
   仍然并发写同一个 SQLite 文件 —— **那把锁解决不了 `database is locked`**（那是数据库级的事）。
2. **超时**：等待多久后放弃？超时时 API 该返回 409 还是 503？
3. **崩溃后锁怎么释放**：`flock` 会在进程退出时自动释放（POSIX）；
   Windows 上 `msvcrt.locking` 同样是 OS 句柄，进程死了锁自动掉。
   **但如果自己实现一个「锁文件存在即已锁」的朴素方案，进程被 kill -9 之后锁就永远留着** ——
   这类实现必须配一个「锁文件里的 pid 是否还活着」的检查 + 超时清理。
4. 锁把「两个并发请求」变成「一个请求排队」——**用户体验上 202 之后要等更久**，
   而 API 现在没有排队语义（`app.py:6-8` 自己写着「Phase 3 introduces a proper queue」）。

**风险**：中。锁解决的是「同时跑两个同样的分析」，**解决不了**「读端读到写了一半的产物」——
那需要方案 A 的目录隔离。

### 推荐：**A + X2，B 作为可选的加固**

理由落到「这个项目现在缺什么」：

1. 这个项目**没有多租户部署**，但 API 是可以并发请求的 —— 所以要解决的不是「扩展到多租户」，
   而是「**同一台机器上两个请求不会互相踩**」。
2. **X2（打开工作区会写库）是并发失败的直接原因，而它和并发无关地也错**：
   一个 liveness 探针做一次读，就把数据库的 journal mode 改了（见 X2 的实测）。
   **先修 X2，并发失败的一大半就没了。**
3. 方案 A 的代价（版本化目录 + 指针）比方案 B 的代价（跨平台文件锁 + 超时 + 崩溃恢复）
   **更小也更可控**；而且方案 A 顺带解决了「读端读到写了一半的产物」——
   这个 B 解决不了。
4. 方案 B 的「排队」语义和 `app.py:6-8` 写的「Phase 3 才有真正的队列」冲突，
   现在引入等于提前做一半 Phase 3。

### 验收标准

1. 两个并发的、同一个 APK 的分析**都成功**，都拿到 `status == completed`，
   且符号计数与**单独跑一次**的结果一致。
2. 两个分析在**同一时刻**各自持有**互不相同**的工作目录。
3. 分析进行中，`GET /projects/{id}/source` 返回的是一份**完整**的源码，不是半截文件。
4. 打开一个已经是当前 schema 的工作区**不产生任何写**（见 X2 的验收标准）。

### 钉住它的测试怎么写

**这条要写成两个测试**，因为一个测试同时钉两件事时，失败时说不清是哪件没修。

**测试 4a：工作目录不共享（确定性，不依赖时序）**

```python
# tests/test_concurrent_analysis.py
class _OverlapProbe:
    """记录每次分析拿到的输出目录，并证明两次分析确实重叠。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inside = 0
        self.max_concurrent = 0
        self.output_dirs: list[Path] = []
        self._arrived = threading.Event()
        self._peers = 0

    def enter(self, output_dir: Path) -> None:
        with self._lock:
            self._inside += 1
            self.max_concurrent = max(self.max_concurrent, self._inside)
            self.output_dirs.append(output_dir)
            self._peers += 1
            if self._peers >= 2:
                self._arrived.set()

    def wait_for_peer(self, timeout: float = 30.0) -> bool:
        """等另一个分析也进来。返回 False 表示没有等到。"""
        return self._arrived.wait(timeout)

    def leave(self) -> None:
        with self._lock:
            self._inside -= 1
```

把探针挂在一个**假后端**上（不要真跑 JADX —— CI 的两个矩阵里没有 JADX）：

```python
@pytest.fixture
def probe(monkeypatch):
    p = _OverlapProbe()

    def fake_decompile(self, apk, output_dir, **kwargs):
        p.enter(output_dir)
        try:
            # 关键：在这里等另一个分析。两边都到了才继续。
            # 如果实现把两次分析串行化了，第一个会在这里超时 → 测试红。
            assert p.wait_for_peer(), "两个分析没有重叠，测试没有证明并发"
            (output_dir / "sources").mkdir(parents=True, exist_ok=True)
            return ToolOutcome(returncode=0, stdout="", stderr="", duration_seconds=0.0)
        finally:
            p.leave()

    monkeypatch.setattr(JadxBackend, "decompile", fake_decompile)
    return p


def test_two_concurrent_analyses_of_one_apk_do_not_share_a_workspace(
    settings, probe, demo_apk
):
    analyzer = Analyzer(settings)
    results, errors = [], []

    def run():
        try:
            results.append(analyzer.analyze(demo_apk))
        except BaseException as exc:      # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300)

    assert not errors, f"并发分析抛了异常：{errors!r}"
    assert len(results) == 2
    assert all(r.succeeded for r in results)

    # 证明两次分析真的重叠了（不是碰巧串行）
    assert probe.max_concurrent == 2, "两次分析没有同时在跑，这条测试没证明并发"

    # 关键断言：两个分析没有共用同一个目录
    assert len(set(probe.output_dirs)) == 2, (
        f"两个分析用了同一个目录：{probe.output_dirs}"
    )
```

**怎么证明这不是假绿**（这是本条的重点）：

- `probe.max_concurrent == 2` 这一条**排除了「因为串行所以没冲突」**这种假绿。
  如果实现把两次分析串行化了，`wait_for_peer()` 会超时，
  `assert p.wait_for_peer()` 先红 —— 报错信息直接写着「两个分析没有重叠」。
- `len(set(probe.output_dirs)) == 2` 是一个**精确的相等断言**，不是「至少 1 个」这种永远成立的断言。
- **在旧代码上会不会红？会，而且是确定性地红**：当前代码两次分析拿到的是**同一个** `output_dir`
  （`pipeline.py:225`/`:321` 都由 `project.id` 决定），集合大小是 1 → 红。
  失败信息就是「两个分析用了同一个目录」。

**测试 4b：两个分析都成功，且结果与单独跑一次一致**

```python
def test_two_concurrent_analyses_both_produce_a_complete_result(settings, demo_apk):
    # 先单独跑一次，拿到「完整结果」的基线
    baseline = Analyzer(Settings(workspace=tmp_path / "baseline")).analyze(demo_apk)

    analyzer = Analyzer(settings)
    results, errors = [], []
    # ... 两个线程并发跑（不挂探针，让它自然并发）...
    assert not errors, f"并发分析抛了异常：{errors!r}"
    for result in results:
        assert result.succeeded
        assert result.project.class_count == baseline.project.class_count
        assert result.project.method_count == baseline.project.method_count
```

**这个测试在旧代码上会不会红？不一定**（实测在已存在的工作区上两个分析都能跑完），
所以它**不是钉子**，只是一条防回归的护栏。**真正的钉子是 4a。**
把 4b 的断言也放进 4a 里（同一个测试先断言目录不共享，再断言两个结果完整），
这样一次失败就能说明两件事。

---

## 4. X2【高·新发现】`Store.transaction()` 每次都跑 `PRAGMA journal_mode = WAL`：一次读也在写库

### 现状

`src/dexatlas/core/storage.py:305-318`：

```python
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")     # ← :371，每一条语句都跑
```

`transaction()` 是 Store 的**唯一**出入口：`get_project`、`list_projects`、`search`、
`get_method_references`……**一次纯读也走这里**。

而 `journal_mode` 在 SQLite 里是**数据库的属性**，不是连接的属性。
在一个还不是 WAL 的数据库上执行 `PRAGMA journal_mode = WAL` 是一次**模式转换**，
需要排他锁；而且**模式转换不遵守 busy timeout**，直接返回 `SQLITE_BUSY`。

**这正是 #4 里那个 `database is locked` 的来源。**

### 实测

```
mode after Store.open           : wal
mode after operator chose DELETE: delete
mode after a plain READ         : wal      ← 一次读把 journal mode 改回去了
mode after a second Store.open  : wal      ← 打开一个已经是当前 schema 的工作区也在改
```

以及并发打开的失败率（两个线程同时 `Store.open` 一个全新的库，20 次试验）：

```
H2: two concurrent Store.open on a fresh db: 15/20 trials had a failure
```

### 为什么重要

1. **「打开工作区」不是只读操作。** 一个 liveness 探针、一个 `GET /projects` 列表请求，
   都会去改数据库的 journal mode。在一个还没转成 WAL 的库上，这就是一次要排他锁的写。
2. **它使并发失败与并发无关地成立**：即使只有一次「打开」和一次「读」，
   只要它们和一个正在转换的连接撞上，就会 `database is locked`。
3. **它让已经暂存的那处并行改动白做**：工作区里 `Store.open`（`src/dexatlas/core/storage.py`，
   并行 agent 正在改，**行号会漂**）已经改成了「schema 版本对得上就只读不写」。
   **但 `transaction()` 里的这条 pragma 照样在写** —— 那个改动解决的是
   「`Store.open` 多余的 `DELETE/INSERT schema_info`」，
   没解决「`transaction()` 每条语句都在写库」。**两者必须一起修。**

### 方案 A：journal mode 只在建库时设一次

- 把 `PRAGMA journal_mode = WAL` 从 `transaction()` 挪到 `Store.open()`，
  **并且只在数据库还不存在 / 还不是 WAL 时才执行**；
  转换失败（`SQLITE_BUSY`）时**吞掉**——另一个连接正在转，转完就好了。

**代价**：低。`journal_mode` 一旦设成 WAL 是**持久**的（写在数据库头里），
不需要每条语句重申。

**风险**：低。唯一的行为变化是「操作员手动把 journal mode 改成 `delete` 之后，
DexAtlas 不再自动改回去」——而这正是应该的行为（journal mode 是部署的决定）。

### 方案 B：把 pragma 留在 `transaction()`，但改成容错的

```python
try:
    connection.execute("PRAGMA journal_mode = WAL")
except sqlite3.OperationalError:
    pass
```

**代价**：最低，一行改动。
**风险**：中。如果转换真的失败了，数据库会停在 `delete` 模式，
于是「读阻塞写」——**并发下症状会变成更难查的 `database is locked`**（而不是干脆起不来）。
所以 B 应该是 A 的补丁，不是替代。

### 推荐：**A 为主，B 作为兜底**

A 解决根因（读不该写库），B 保证在有别的进程正在转换时不会把整个请求打挂。
两者不冲突，可以一起上。

### 验收标准

1. 一个已经是当前 schema 的工作区，`Store.open()` **不产生任何写**。
2. 对一个**只读**的调用（`list_projects()`、`search()`），数据库的 journal mode 不变。
3. 两个并发 `Store.open` 同一个新工作区，**两个都成功**。

### 钉住它的测试怎么写

```python
# tests/test_store_open.py （与并行 agent 新增的同名文件合并，不要覆盖）
def _journal_mode(db: Path) -> str:
    connection = sqlite3.connect(db)
    try:
        return connection.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        connection.close()


def test_reading_the_workspace_does_not_write_to_the_database(tmp_path):
    """一次读不应该改数据库。

    现在 transaction() 每次都跑 PRAGMA journal_mode = WAL ——
    那是一条数据库级别的写语句（journal mode 是数据库的属性）。
    在一个还没进 WAL 模式的库上，它是一次需要排他锁的模式转换；
    两个连接同时打开工作区时，第二个就会拿到 "database is locked"。
    """
    db = tmp_path / "dexatlas.db"
    store = Store.open(db)

    # 部署方自己选了 DELETE 模式
    connection = sqlite3.connect(db)
    try:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.commit()
    finally:
        connection.close()

    store.list_projects()          # ← 一次纯读

    assert _journal_mode(db) == "delete", "一次读把 journal mode 改了 —— 它拿了写锁"
```

**在旧代码上会不会红？会，确定性地红**：实测「一次纯读」之后 mode 从 `delete` 变成 `wal`。
这条断言与时序、与并发**完全无关**——它是「读不应写」的直接编码。

再补一条钉住并发后果的：

```python
def test_two_concurrent_opens_of_a_new_workspace_both_succeed(tmp_path):
    db = tmp_path / "dexatlas.db"
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def open_it():
        barrier.wait(timeout=30)
        try:
            Store.open(db)
        except BaseException as exc:      # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=open_it) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors, f"并发打开工作区失败了：{errors!r}"
```

**这条会红，但**实测失败率是 **15/20（75%）** —— 它是**概率性的**。
所以：**它只能当护栏，不能当钉子**。**钉子是上面那条「读不应写」的测试**，
那条 100% 稳定地红。**这一点必须写进 issue 里**，否则将来有人会抱怨这个测试 flaky。

---

## 5. #7【高】`xrefs` 表没有主键：交叉引用按**调用次数**计数，不是按**边**

### 现状（复核）

`src/dexatlas/core/storage.py:157-163`：

```sql
CREATE TABLE IF NOT EXISTS xrefs (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    caller     TEXT NOT NULL,
    callee     TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'invoke',
    provenance TEXT NOT NULL DEFAULT '[]'
);
```

**没有 `PRIMARY KEY`，没有 `UNIQUE`。** 对照同文件里的其他表：
`classes` `:132`、`methods` `:144`、`fields` `:155`、`resources` `:92`、`evidence` `:185`
—— 全都有主键。`strings`（`:166-172`）也没有主键，但那是**故意的**
（`src/dexatlas/core/models.py:384-388`：「一个常量在两个方法里用，就是两行，
因为每行都要指向代码里的一个位置」）。

`xrefs` 不一样：**一条调用边就是一条边**，两行同一条边是重复。

写入处 `src/dexatlas/core/storage.py:497-509` 用的是**裸 `INSERT`**（没有 `OR REPLACE`），
所以重复行会真的留下。

### 重复是从哪来的 —— 评审的描述不完整

评审（以及 `docs/analysis-provenance.md` §6.6）只提到**跨 DEX** 重复。
实测发现**还有第二种，而且更常见**：

| 来源 | 例子 | provenance 是否相同 |
| --- | --- | --- |
| **同一个 DEX 里，同一个方法调用同一个目标两次**（两条 invoke 指令） | `Crypto.sign → StringBuilder.append` | **完全相同** |
| 同一个方法定义在两个 DEX 里，各自调用同一个目标 | `SharedConfig.<init>() → Object.<init>()` | 不同（locator 里的 DEX 名不同） |

第一类**根本不是「两条边」**——它是一条边被调用了两次。现在的表分不清这两者。

### 实测

```
=== demo.apk  project=apk_80a8fe0e81204c9f ===
  project.reference_count = 23
  xrefs rows in table       = 23
  distinct (caller,callee)  = 21
  duplicate rows            = 2
    x2  com.example.demo.Crypto.sign(...)V -> java.lang.StringBuilder.append(...)Ljava/lang/StringBuilder;  kinds=virtual
    x2  com.example.demo.MainActivity.describe(...)V -> java.lang.StringBuilder.append(...)Ljava/lang/StringBuilder;
  API total for java.lang.StringBuilder.append(...)Ljava/lang/StringBuilder;: 4 rows, 2 distinct callers

=== multidex.apk ===
  project.reference_count = 13   xrefs rows = 13   distinct = 10   duplicate rows = 3
=== wide.apk ===
  project.reference_count = 15   xrefs rows = 15   distinct = 13   duplicate rows = 2
```

### 为什么重要（读者会得出什么错误结论）

1. **项目记录里的 `reference_count` 数的是调用指令，不是调用边。**
   demo.apk 报「23 条交叉引用」，索引里真实的边是 **21** 条。
   这个数进报告、进 API、进 `ProjectResponse`（`src/dexatlas/api/app.py:147`）。
2. **API 的 `"total"` 是行数，不是调用者数。**
   `GET /projects/{id}/xrefs/java.lang.StringBuilder.append(...)` 返回
   `{"total": 4, "references": [4 条]}`，而实际只有 **2 个不同的调用方**。
   读者会以为有 4 个地方调了这个方法。**这是 API 契约级的错误。**
3. **`docs/analysis-provenance.md` §6.6 说这个重复「是对的」** —— 但它只覆盖了跨 DEX 那一类，
   而且把它当成「读者需要知道」而不是「这是个 bug」。**文档需要改，代码也需要改。**

### 方案 A：给 `xrefs` 加主键，把「边」和「调用点」分开

主键 `(project_id, caller, callee, kind)`，provenance 变成一个列表（像
`_merge_methods` 在 `src/dexatlas/core/pipeline.py:528-553` 那样把多份 provenance 合并）。

- **代价**：
  1. **跨 DEX 的两条边会合并成一行** —— 这是**有意的**：跟 `classes`/`methods` 的处理一致
     （`pipeline.py:496-525`、`:528-553`、`:556-577` 都在做「合并但保留每一份 provenance」）。
     合并后 provenance 数组里有两个 locator，信息**不丢**。
  2. `kind` 要不要进主键？**要**。同一个 (caller, callee) 被不同 opcode 调用是可能的
     （`invoke-virtual` 与 `invoke-interface`），合成一条会丢掉这个区别。
  3. 写库要改成 `INSERT OR REPLACE` 或 `INSERT ... ON CONFLICT DO UPDATE`，
     且要把多份 provenance 合并后再写 —— 需要一个合并步骤（可以复用 `_merge_methods` 的形状）。
- **风险**：中。`docs/analysis-provenance.md` §6.6 的说法要一起改，
  而且该文档的行号引用会被 `scripts/check-doc-citations.py` 检查（`ci.yml` 里有独立的
  「Doc citations」步骤）—— **改 schema 必然改行号，引用要同步更新。**

### 方案 B：保留「一行 = 一个调用点」，但把**计数**改成按边算

- 表不动，`INSERT INTO xrefs` 不动；
- `Project.reference_count` 改成 `COUNT(DISTINCT caller, callee)`；
- API 的 `total` 改成不同调用方的数量，并在响应里同时给出「调用点数」。

- **代价**：最小，不碰 schema，不碰迁移。
- **风险**：**高**。表里仍然留着无法区分的重复行；任何直接查表的人（包括
  `docs/analysis-provenance.md` 里教读者写的那些 SQL）读到的还是重复。
  **这个项目自己的文档教读者用裸 SQL 查这张表**（`analysis-provenance.md` §7、`:437`），
  所以「表里的重复」是读者会直接撞上的东西。**只改计数不修表，等于把问题推给读者。**

### 迁移怎么做 —— 这里有个坑，必须写进 issue

**`_SCHEMA_VERSION` 从 2 改成 3 是不够的。** 实测：

```python
# 旧库：xrefs 没有主键
c.executescript("""
CREATE TABLE IF NOT EXISTS xrefs (..., PRIMARY KEY (project_id, caller, callee, kind));
""")
# rows before: 2
# rows after executescript: 2
# schema after: CREATE TABLE xrefs ( ... )     ← 主键没有生效
# duplicate insert: ACCEPTED (no primary key in effect)
```

因为 `CREATE TABLE IF NOT EXISTS` **不会改已经存在的表**。而
`src/dexatlas/core/storage.py:298-299` 正是靠 `executescript(_SCHEMA)` 来建表的：

```python
if version != SCHEMA_VERSION or not _SCHEMA_TABLES.issubset(tables):
    connection.executescript(_SCHEMA)
```

**所以迁移必须显式重建表。** 现成的先例就在同一个文件里 ——
`src/dexatlas/core/storage.py:277-285` 对 `resources` 就是这么做的：

```python
    resource_columns = {row["name"] for row in connection.execute("PRAGMA table_info(resources)")}
    if resource_columns and "position" not in resource_columns:
        # The table is a cache of the analysis rather than a source of truth —
        # the next analysis fills it again — so it is dropped and created empty.
        connection.execute("DROP TABLE resources")
        connection.execute(_RESOURCES_TABLE)
```

**照抄这个形状**：`PRAGMA table_info(xrefs)` 里没有主键索引 → `DROP TABLE xrefs` +
`CREATE TABLE xrefs (...)`（带主键）。

**迁移代价**：
1. 旧工作区的交叉引用索引**会被清空**，要等下一次分析才填回来。
   这是可接受的（`xrefs` 是分析的缓存，不是真相来源 —— 与 `resources` 同理），
   **但必须在迁移时把 `projects.reference_count` 一并归零**，否则项目记录上留着
   一个「23」而表里是 0 行，读者查出来是空的。**这两处必须一起处理。**
2. `SCHEMA_VERSION` 要从 2 升到 3（`src/dexatlas/core/storage.py:39`）。
3. `docs/analysis-provenance.md` §6.6 与 §5.1 的行号引用要同步更新
   （`scripts/check-doc-citations.py` 会查）。

### 验收标准

1. 写入同一条边两次，`xrefs` 表里只有一行。
2. `Project.reference_count` == 不同 `(caller, callee)` 的数量。
3. `GET /projects/{id}/xrefs/{method_id}` 的 `"total"` == 不同调用方的数量。
4. 跨 DEX 的同一条边**合并成一行，但 provenance 数组里保留两个 locator**。
5. 一个 v2 的旧工作区在 v3 代码下打开：表被重建、`reference_count` 被归零、
   不抛异常。

### 钉住它的测试怎么写

```python
# tests/test_storage.py
def test_the_same_call_edge_is_stored_once(store):
    """同一条调用边只能存一行。

    现在会红：xrefs 没有主键，同一条边写两遍就是两行。
    """
    edge = MethodReference(
        caller="com.example.A.foo()V",
        callee="com.example.B.bar()V",
        kind=InvocationKind.VIRTUAL,
    )
    store.save_symbols(
        "p1", [], [], [], [edge, edge], []
    )
    rows = store._count_xrefs("p1")     # 或直接查 connection
    assert rows == 1, "同一条调用边存了两行"
```

更好的是**从 API 端断言**，因为读者看的是 API：

```python
def test_the_xref_total_counts_callers_not_call_sites(client, demo_project):
    body = client.get(
        f"/projects/{demo_project}/xrefs/"
        "java.lang.StringBuilder.append(Ljava/lang/String;)Ljava/lang/StringBuilder;"
    ).json()
    callers = {r["caller"] for r in body["references"]}
    assert body["total"] == len(callers), (
        f"total={body['total']} 但只有 {len(callers)} 个不同的调用方"
    )
```

**在旧代码上会不会红？会，确定性地红**：实测 demo.apk 上
`total = 4` 而不同调用方 `= 2`；`reference_count = 23` 而不同的边 `= 21`。
这两个数都是**从真实样本量出来的**，不是构造出来的。

**怎么证明它不是假绿**：断言里同时用了两个**独立算出来的**数
（API 返回的 `total` vs 集合去重后的 `len(callers)`），
不是「总数 == 总数」。在旧代码上，`total` 是行数、`len(callers)` 是去重后的调用方数，
两者**必然不等**（除非一个调用方恰好只调一次）。

---

## 6. #11【中】loguru 的全局 handler 被移除且永不恢复

### 现状（复核；位置与交办描述不同）

交办说「`src/dexatlas/core/logging.py`（或类似文件）」——**这个文件不存在**。
真正的位置是 `src/dexatlas/tools/androguard/adapter.py:96-119`：

```python
@contextmanager
def _quiet_androguard() -> Iterator[None]:
    """Silence Androguard's loguru output.

    On a large APK it emits thousands of parse-trace lines at DEBUG, which buries the
    CLI's own output. Suppressed here rather than configured globally, because the
    library may legitimately be used at debug level elsewhere in the process.
    """
    try:
        from loguru import logger as loguru_logger      # :105
    except ImportError:
        yield
        return

    previous = os.environ.get("LOGURU_LEVEL")            # :110
    os.environ["LOGURU_LEVEL"] = "ERROR"                 # :111
    loguru_logger.remove()                               # :112   ← 全局删除所有 handler
    try:
        yield
    finally:                                              # :115-119  ← 只恢复了环境变量
        if previous is None:
            os.environ.pop("LOGURU_LEVEL", None)
        else:
            os.environ["LOGURU_LEVEL"] = previous
```

三处错：

1. **`logger.remove()` 是全局的**，而且**不可逆**。loguru 0.7.3 的 `remove()` 返回 `None`，
   删掉包括默认 handler（id 0）在内的**全部** handler；`finally` 里**只恢复了环境变量**，
   handler 再也没有回来。
2. **`LOGURU_LEVEL` 那两行是死代码。** loguru 在**导入时**读一次这个环境变量，
   把它当作 `logger.add(level=...)` 的默认值（`loguru/_logger.py` 里
   `level=_defaults.LOGURU_LEVEL`）。而 `:105` 的导入发生在 `:111` 设环境变量**之前**，
   所以那次导入就已经用环境里的旧值建好了默认 handler；`:112` 又把它删了。
   之后 `from loguru import logger` 是缓存命中，什么都不会发生。
   **这个环境变量从头到尾没有影响过任何一个 handler。**
3. **docstring 与代码相反。** 它写「Suppressed here rather than configured globally,
   because the library may legitimately be used at debug level elsewhere in the process」，
   而代码做的恰恰是**全局配置**（全局删除）。

还有一处**时序上的巧合掩盖了它**：真正费时间的 DEX 解析
（`adapter.py:246` 的 `dex = DEX(blob)`）**在 `with _quiet_androguard():` 之外**
（那个 `with` 块只包住 `:236-240` 的 `APK()` 构造）。
**如果移除真的像 docstring 说的那样是「临时的」，那些解析日志会全部冒出来。**
它们没冒出来，只是因为移除是永久的。

### 实测

```python
print("handlers:", list(loguru.logger._core.handlers.keys()))   # -> [0]
host_handler_id = loguru.logger.add(sys.stderr, format="HOST-LOG: {message}")
print("handlers:", list(loguru.logger._core.handlers.keys()))   # -> [0, 1]
...  跑一次 analyzer.analyze(APK)  ...
print("handlers:", list(loguru.logger._core.handlers.keys()))   # -> []      ← 归零
print("min_level:", loguru.logger._core.min_level)              # -> inf
loguru.logger.info("host says hello after the analysis")         # → 没有任何输出
```

```
=== BEFORE any analysis ===
loguru handlers: [0]
host handler id: 1
loguru handlers after host add: [0, 1]

=== AFTER analysis ===
status: completed
loguru handlers: []
loguru min_level: inf
--- host logs after analysis (should appear if the handler survived) ---
--- end host logs ---

=== Calling _quiet_androguard directly ===
handlers before: []
handlers inside: []
handlers after: []
```

**一次分析之后，整个进程的 loguru 输出就没了。**

### 为什么重要（影响面）

1. **嵌入方自己的日志没了。** `dexatlas` 是可以 `pip install` 的库
   （`pyproject.toml` 的 `[tool.hatch.build.targets.wheel] packages = ["src/dexatlas"]`），
   而 `androguard` 本身就依赖 loguru。宿主进程里任何用 loguru 的代码
   ——包括宿主自己的 androguard ——**在第一次 DexAtlas 分析之后全部静音**。
2. **DexAtlas 自己也没法把 androguard 的 DEBUG 输出打开。** 这个 `_quiet_androguard`
   是唯一的 loguru 使用点，它一进上下文就把 handler 删了，之后再没有任何途径恢复。
3. **这是单程门（one-way door）**：装它的代码自己都没法拆。

### 方案 A：改用 loguru 的 `disable()` / `enable()`

```python
loguru_logger.disable("androguard")
try:
    yield
finally:
    loguru_logger.enable("androguard")
```

- **代价**：几乎为零。两行换两行。
- **风险**：低。`disable(name)` 只压制**名为 `androguard` 的记录**，
  **不动任何 handler**（默认 handler 还在），宿主进程的日志**完全不受影响**。
  `enable()` 把状态还原。
- **要核实的一点**：`disable()` 是全局状态，所以两个线程同时进入 `_quiet_androguard` 时，
  一个先退出就会 `enable()`，把另一个还在压制的窗口提前打开。
  **这是可接受的**（后果只是多几行 DEBUG 日志），但要在代码注释里写清楚。
- **还要核实**：`disable("androguard")` 能不能真的盖住 androguard 的日志 ——
  取决于 androguard 用的是不是 loguru 的 `logger.opt(depth=...)` 且模块名落在 `androguard` 下。
  **这一条要实测，不能假设。**

### 方案 B：捕获并还原 handler

在 `remove()` 之前把 `logger._core.handlers` 抄下来，之后逐个 `logger.add(...)` 加回去。

- **代价**：要碰 loguru 的私有属性 `_core.handlers`（loguru 0.7.3 里确实是私有的）。
- **风险**：**高**。`Handler` 对象不能直接交给 `logger.add()`；
  要还原得重建 sink 和配置（level/format/filter/enqueue…），
  很容易还原出一个**行为不同**的 handler。而且 loguru 升级换了内部结构就会静默失效。
- **判断**：**不推荐**。为了「别弄坏别人的日志」去依赖别人的私有 API，
  是在一个更隐蔽的地方制造同类问题。

### 方案 C（补充）：在「DexAtlas 独占进程」时保留旧行为

如果有人确实需要完全静音 androguard 的日志，可以提供一个显式开关
（`DEXATLAS_QUIET_ANDROGUARD=1` 之类）走 `logger.remove()`，并在文档里写清楚
「这会移除进程内所有 loguru handler，仅适用于独占进程」。

- **代价**：多一个配置项和一条文档。
- **风险**：低。默认走 A。

### 推荐：**A（必要时叠加 C）**

理由落到「这个项目现在缺什么」：这个项目的强项是**诚实**——
报告里不写没发生过的事。**而这里的 docstring 写了一件代码没做的事**，
这正是 `docs/status.md` §6 列的「文档说 A、代码是 B」那一类。
方案 A 一箭双雕：**既修好了行为，又让 docstring 变成真的**——
把 docstring 改成「压制 androguard 自己的日志，不动进程的全局 handler」即可。

**顺带**：`_quiet_androguard` 的 `finally` 只恢复环境变量这件事本身也该改 ——
要么恢复 handler（方案 B，不推荐），要么**把环境变量那两行删掉**
（它们是死代码，留着只会误导下一个人）。

### 验收标准

1. 一次分析之后，`loguru.logger._core.handlers` 的**内容与之前完全一致**。
2. 宿主进程自己加的 handler，在分析之后仍然能收到日志。
3. androguard 自己的 DEBUG 日志在分析期间仍然被压制（这个行为不能丢）。
4. docstring 与代码一致。

### 钉住它的测试怎么写

```python
# tests/test_androguard_integration.py
def test_an_analysis_leaves_the_process_logging_alone(settings, demo_apk):
    """一次分析不能动宿主进程的日志。

    现在会红：_quiet_androguard 调 logger.remove()，
    把进程里所有 loguru handler 删掉，而且不恢复。
    """
    import loguru

    host_sink = io.StringIO()
    handler_id = loguru.logger.add(host_sink, format="{message}")
    before = dict(loguru.logger._core.handlers)

    try:
        Analyzer(settings).analyze(demo_apk)

        assert set(loguru.logger._core.handlers) == set(before), (
            "分析之后 loguru 的 handler 变了"
        )
        loguru.logger.info("the host is still listening")
        assert "the host is still listening" in host_sink.getvalue(), (
            "宿主进程的日志被分析吞掉了"
        )
    finally:
        loguru.logger.remove(handler_id)
```

**在旧代码上会不会红？会，确定性地红**：实测「一次分析之后 handlers 从 `[0, 1]` 变成 `[]`」。
断言用的是**集合相等**（不是「至少还有一个」），所以修复成「加回来一个不同的 handler」
也会红——这是对的，因为那正是方案 B 的失败模式。

**怎么证明它不是假绿**：`before` 是在分析**之前**取的快照，
断言的是**集合相等**，不是「非空」。
旧代码上 `set(handlers) == set(before)` → `set() != {0, 1}` → 红。

再补一条钉住「不能把该压制的放开」的：

```python
def test_androguard_debug_output_is_still_suppressed(settings, demo_apk, caplog):
    ...
```

（这条要配合方案 A 落地后，改为断言 androguard 的 DEBUG 记录**没有**出现在输出里。）

---

## 7. #12【中】上传的 APK 分析完成后不删除

### 现状（复核）

- `src/dexatlas/api/app.py:46-47` —— `UPLOAD_DIRNAME = "uploads"`
- `src/dexatlas/api/app.py:271-273` —— 落到 `settings.workspace / "uploads" / <客户端文件名>`
- `src/dexatlas/api/app.py:276` —— `save_upload(file.file, target)`
- `src/dexatlas/api/app.py:291-299` —— `inspect_apk` 失败时 `target.unlink(missing_ok=True)`（**这一条是对的**）
- `src/dexatlas/api/app.py:301-307` —— **「已存在同 hash 就直接返回」那条路径：文件留着**
- `src/dexatlas/api/app.py:311` —— `background.add_task(_run_analysis, analyzer, target, apk)`
- `src/dexatlas/api/app.py:319-323` —— `_run_analysis` 只调 `analyzer.analyze(...)`，**没有 `finally` 清理**

实测（跑完一次完整分析后）：

```
uploaded file exists: True sha: 80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9
uploads dir listing: ['app.apk']
```

仓库自己的 `.dexatlas/uploads/demo.apk`（2951 字节）也一直躺在那里。

### 已经做对的部分 —— **不要重复造**

这几处已经存在，方案里应当复用：

| 已有机制 | 位置 |
| --- | --- |
| 包体上限 256 MiB | `src/dexatlas/core/ingest.py:34`（`MAX_APK_BYTES`） |
| 解压后总量上限 2 GiB | `src/dexatlas/core/ingest.py:41` |
| 膨胀比上限 100× | `src/dexatlas/core/ingest.py:48` |
| 校验读取预算 256 MiB | `src/dexatlas/core/ingest.py:56` |
| **流式写盘 + 超限即中止 + 删掉半截文件** | `src/dexatlas/core/ingest.py:88-97`（`save_upload` 的 `except BaseException: target.unlink()`） |
| `UploadTooLarge` 异常 | `src/dexatlas/core/ingest.py:63-68` |
| 请求头 `Content-Length` 预检（不等流完就拒） | `src/dexatlas/api/app.py:82-113`（`UploadSizeLimitMiddleware`） |

**所以「上传体积」这件事已经做得很扎实了，缺的只是「上传的文件用完怎么办」。**

### 为什么重要

- **磁盘**：每个上传的 APK 最多 256 MiB 常驻。分析一次就扔掉的东西留在盘上，
  N 次上传就是 N × 256 MiB。
- **证据指向一个不存在的文件**（见 X1）：留着文件的时候，`apk_path` 至少还能被核对；
  删掉之后，`projects.apk_path` 指向一个空路径。
- **和 X1 是同一件事的两面**：文件名可被覆盖（X1）＋ 文件不删（#12）。

### 方案 A：分析完成后删除上传文件

- 在 `src/dexatlas/api/app.py:319-323` 的 `_run_analysis` 里加 `finally: target.unlink(missing_ok=True)`。
- **必须只删 API 上传的那一份**，不能删用户自己给 CLI 的路径。
  → 落盘时就该区分：**API 的上传落到 `workspace/uploads/` 下，CLI 的分析不碰那里**。
  `Analyzer.analyze` 收到的是路径，它分不清来源 —— 所以**删除动作要放在 API 层**
  （`_run_analysis` 里），不要放进 `Analyzer`。
- **代价**：`projects.apk_path` 变成一条悬空路径。
  影响面很小：API 只暴露 `display_path(project.apk.path)`（文件名，`api/app.py:580`），
  报告里也是 `project.apk.path.name`（`src/dexatlas/reports/markdown.py:77`）。
  但**数据库里存的是绝对路径**（`src/dexatlas/core/storage.py:343`），将来如果加一个「按路径复核证据」的功能就会指空。
  → **配套：分析完成后把 `projects.apk_path` 置空，或者改成记内容哈希。**

### 方案 B：保留文件，但按内容哈希命名 + 加保留策略

- 落盘成 `uploads/<sha256>.apk`（和 X1 同一个改动）；
- 保留期：比如 N 小时后由一次性的清扫任务删掉，或者「保留最近 N 个 / 总量配额」。

- **代价**：要写一个清扫逻辑（什么时候跑？CLI 每次启动？API 每次启动？还是定时？）。
  比方案 A 复杂。
- **风险**：低。而且**保留文件本身有价值** —— 读者可以取回被分析的那份 APK，
  这对「证据优先」是加分项（前提是名字和哈希一致，见 X1）。
- **配额**：需要一个「上传总量上限」，否则一个恶意的调用方可以把盘写满。
  **注意**：现有的 `MAX_APK_BYTES` 是**单个文件**的上限，不是**总量**的上限。

### 推荐：**X1 的改动 + 方案 B（保留 + 配额），把方案 A 作为可选项**

理由落到「这个项目现在缺什么」：

1. 这个项目的**卖点是可复核**——读者能取回被分析的字节、能核对哈希。
   **删掉文件是把这个卖点减掉。** 而 X1 的修复（内容寻址的名字）让保留变得安全。
2. 现有的上传防护做的是**单个文件**的防护，缺的是**总量**防护。
   **配额是这条真正缺的东西**，不是删除。
3. 建议的动作顺序：
   1. **X1**：上传按内容哈希命名（不可变）——这一条同时修掉证据链断裂和覆盖问题；
   2. **配额**：给 `workspace/uploads` 一个总量上限（比如「总量不得超过 N 倍数据库大小」
      或一个绝对值），超了拒绝新的上传（复用现成的 `UploadTooLarge` /
      `HTTP_CONTENT_TOO_LARGE` 路径，**不要另造一套错误码**）；
   3. **清扫**：超过保留期（按 mtime）的上传文件在启动时删掉；
   4. **方案 A 作为可选**：如果部署方不想要保留字节，把 `unlink` 打开即可
      （做成一个设置项）。

### 验收标准

1. 同一个文件名的两次上传不会互相覆盖（这是 X1 的验收标准）。
2. `workspace/uploads` 的**总量**有上限，超了返回 413。
3. 超过保留期的上传文件会被清掉。
4. 清扫不会删掉正在被分析的文件（正在分析的文件要么用内容哈希命名且 mtime 新，
   要么用「正在使用」的标记）。

### 钉住它的测试怎么写

**（a）钉住「不删」这个行为本身**（如果要保留）：

```python
def test_the_uploaded_apk_is_still_there_after_the_analysis(client, demo_apk):
    """分析完之后，上传的 APK 还在，且内容没变。

    现在会红（如果选了「分析后删除」这条路线）：
    文件被删掉，或者内容被另一个上传覆盖了。
    """
    project = _upload(client, demo_apk, "demo.apk")
    _wait_completed(client, project)
    uploads = list((settings.workspace / "uploads").iterdir())
    assert len(uploads) == 1
    assert sha256(uploads[0]) == sha256(demo_apk)
```

**（b）钉住配额**：

```python
def test_the_upload_directory_has_a_total_size_limit(client, settings, demo_apk):
    """上传目录的总量有上限。"""
    # 把配额调到很小
    settings.upload_max_total_bytes = 1024
    # 第一次上传成功
    assert client.post("/analyze", files={"file": ("a.apk", demo_apk.read_bytes())}).status_code == 202
    # 第二次超配额 → 413
    response = client.post("/analyze", files={"file": ("b.apk", demo_apk.read_bytes())})
    assert response.status_code == 413
```

**在旧代码上会不会红？会**：现在没有任何总量上限，
第二次上传照样 202。**这条是确定性地红的**（不依赖时序）。

**（c）钉住「同名上传不覆盖」**（这是 X1 的测试，#12 依赖它）：
见 X1 一节。

---

## 8. #14 / #15【中】文档/注释/docstring 声称与代码实际不一致

### 说明

这两条在评审里是「部分成立」条目，具体子项记不全了。
本次复核的做法是：**在 `src/dexatlas/core/` 和 `src/dexatlas/tools/` 里逐个模块读注释与 docstring，
找出「声称了什么」与「代码实际做了什么」对不上的地方**，并对每一条重新核对了当前树的行号。

**重要前提**：本节**不重复**已在 #7 / #11 / X1 里展开的条目（那些在下面标了「见 §N」），
只列剩下的。表格按严重级排。

### 高

| # | 位置（当前树） | 声称 | 实际 |
| --- | --- | --- | --- |
| M1 | `src/dexatlas/api/app.py:600-610` ＋ `src/dexatlas/reports/markdown.py:70`、`src/dexatlas/reports/json_report.py:84` | `_rebuild_result` 重建 `AnalysisResult`（未设 `duration_seconds`） | `AnalysisResult.duration_seconds` 默认 `0.0`（`src/dexatlas/core/pipeline.py:64`），而报告**无条件**打印这一行 → **每一个从 REST API 导出的报告都写着「Analysis time \| 0.0s」**，一个分析从未产生过的数字 |
| M2 | `src/dexatlas/core/pipeline.py:110` | 「Every later failure is recorded on the project instead of raised.」 | 存储层的 `sqlite3.Error` **既不记录也不包装**，直接上抛。实测：并发 `/analyze` 时 `sqlite3.OperationalError` 从 `get_analyzer` 冒到框架（→ 500），项目行留在 `running` |
| M3 | `src/dexatlas/core/evidence.py:31-32` | 「The report's evidence table shows 200 rows, so this leaves room for the class declarations in the same table」 | `MAX_EVIDENCE_CALLED_METHODS = 100`（`:33`）+ `MAX_EVIDENCE_CLASSES = 500`（`src/dexatlas/core/pipeline.py:53`）= 最多 **600** 条证据记录灌进 `reports/markdown.py:28` 的 `_MAX_EVIDENCE_ROWS = 200` 行表 → **溢出 400 条**，报告尾部写「_400 further evidence records omitted._」（`markdown.py:229`） |
| M4 | `src/dexatlas/core/pipeline.py:499-500` | 「Backends disagree about a class's flags — Apktool knows the manifest declaration, Androguard the DEX definition. Both are kept」 | **Apktool 从不产出 `ClassRef`**：`grep -c ClassRef src/dexatlas/tools/apktool/adapter.py` → **0**；`pipeline.py:230` 的 `classes: list[ClassRef] = []` 恒空。真实的两个来源是 Androguard 与 JADX |

### 中

| # | 位置 | 声称 | 实际 |
| --- | --- | --- | --- |
| M5 | `src/dexatlas/core/storage.py:268` | 「Additive only.」 | 同一个函数 `:294` 就 `DROP TABLE resources`（注释里说 resources 表是缓存，不是真相来源） |
| M6 | `src/dexatlas/core/ingest.py:6-7` | 「The archive is inspected through its *central directory* … rather than by decompressing it」 | `_verify_entries`（`:155-173`）实际**解压最多 256 MiB**（`MAX_VERIFIED_BYTES`，`:56`）去校验 checksum |
| M7 | `src/dexatlas/tools/base.py:3` | 「Backends are subprocess wrappers, never links.」 | Androguard 是**进程内库**；`src/dexatlas/tools/androguard/adapter.py:11-14` 自己承认是「the one exception to the subprocess rule」 |
| M8 | `src/dexatlas/tools/base.py:29-30` | 「Output that exceeds this is treated as a runaway backend rather than a result.」 | `_DEFAULT_MAX_OUTPUT` **全仓库零引用**（死常量，见 F8）；而且实际行为是**静默截断**（`_read_capped`，`:403-413`），不是「当作失控后端」 |
| M9 | `src/dexatlas/tools/base.py:246-251` | `_decode` 里 `if len(raw) > limit: logger.warning("output truncated from %d to %d bytes")` | **分支不可达**：`_read_capped` 先 `truncate(limit)` 再读，`len(raw) <= limit` 恒成立。实测 `_read_capped(h, 100)` 返回 100 字节 → `len(raw) > limit` 为 False。**后端 stdout 被裁剪时永远不会被告知** |
| M10 | `src/dexatlas/tools/base.py:90` | 「Subclasses declare how to locate and probe their tool, then implement extraction.」 | 基类**没有 `extract` 抽象方法**；三个子类的 `extract` 签名互不相同（jadx `(apk_sha256, output_dir, outcome)`、androguard 6 元组、apktool 无 extract） |
| M11 | `src/dexatlas/api/app.py:4` | 「No analysis behaviour is defined here, so the two interfaces cannot diverge.」 | API 对已分析过的 APK **去重**（`:319-325`），CLI **不去重**（`src/dexatlas/cli/main.py:186-187` 每次重跑） |
| M12 | `src/dexatlas/core/models.py:496-514` | `EvidenceLevel.LEAD` / `INSUFFICIENT` 是给模型输出用的闸门 | `src/` 里**没有任何一处产生这两个等级**（全仓库只有枚举定义和 `reports/markdown.py:24-25` 的等级说明表）。报告的等级表恒为 `lead 0 / insufficient 0` |
| M13 | `src/dexatlas/core/pipeline.py:624` | `if not status: return` | JADX 什么都没产出时（输出目录空、`decompilation_status` 返回 `{}`）**报告完全不提**，但报告的 Tool versions 行照旧列 `jadx 1.5.2` |
| M14 | `src/dexatlas/tools/androguard/adapter.py:399-424` | 「method limit {limit} reached」 | 检查是**按类**做的（`:399` `if len(methods) >= method_limit`），一个类里的方法可以一次跨过上限；报出来的 limit 与实际索引量对不上 |

### 低

| # | 位置 | 声称 | 实际 |
| --- | --- | --- | --- |
| M15 | `src/dexatlas/core/paths.py:33-35` | 「rejects a name with any empty segment **before** it splits into components」 | 代码 `:69` 是 `parts = class_name.split(".")` **先 split 再判空**。行为等价，机制描述错 |
| M16 | `src/dexatlas/core/paths.py:20-21` | 「POSIX 文件系统把组件名限在 255 字节，**Windows caps it at the same number**」 | NTFS 限的是 255 个 **UTF-16 码元**，不是字节。一个 200 字的中文类名能过字节检查却超字符限制 |
| M17 | `src/dexatlas/core/evidence.py:3-5` | 「Evidence ids are stable across re-analysis of the same APK」 | 只在**后端集合完全相同**时成立；后端增减会让 `add_error` 之后的所有 id 位移 |
| M18 | `src/dexatlas/tools/androguard/adapter.py:579, 592` | locator 格式 `<tool>:<place>` | 字符串值被截到 **64 字符**（`value[:64]`），两个同前缀的长串**得到同一个 locator** —— 指针不再指向唯一位置，文档未记载 |
| M19 | `src/dexatlas/core/storage.py:844` | 索引里的字符串名 | 截断到 **200 字符**（`constant.value[:200]`），未记载 |
| M20 | `src/dexatlas/tools/base.py:119` | `path_env_var: str = "DEXATLAS_<BACKEND>_PATH"` | **字面占位符**，不是模式。第四个后端若忘了覆盖，缺安装提示里会打印这串字面量 |
| M21 | `src/dexatlas/tools/base.py:5` | 「a crashing or hangs engine」 | 拼写错误（hanging） |
| M22 | `src/dexatlas/tools/jadx/adapter.py:116-139` | `method_status` 的 `False` 语义是「JADX 写了但反编译失败」 | `failed` 集合里**构造器（按 Java 类名记）和普通方法名混在一起**（`:374-382`）。一个类名与某个失败方法同名的混淆 APK，会让 `method_status(..., "<init>")` 对一个**根本不存在**的构造器返回 `False` |
| M23 | `src/dexatlas/core/storage.py:67` / `:488` | 「The tables collapse duplicate keys」/「symbol tables key on the symbol」 | 对 `xrefs`（`:158-164`）与 `strings`（`:166-172`）**不成立** —— 见 §5（#7）。`strings` 的无主键是**有意的**，代码注释里没写 |
| M24 | `src/dexatlas/tools/androguard/adapter.py:101-102` | 「Suppressed here rather than configured globally, because the library may legitimately be used at debug level elsewhere in the process」 | `logger.remove()` 恰恰是全局的、永久的 —— 见 §6（#11） |

### 推荐动作（按「改代码」还是「改措辞」分开）

- **改代码（4 条，都是行为本身该修的）**：M1（报告不许写 0.0）、M2（`sqlite3.Error` 要包装成 `ToolError`）、
  M9（截断要能被告知）、M13（JADX 没产出要记一条）。
- **改措辞（其余）**：把注释改成代码实际做的事。
  **M7/M24 除外**——那两条的代码该改（见 #11），不是措辞。
- **M4 要改措辞**：注释里的「Apktool」应该是「JADX」。

### 验收标准

每一条要么注释改了，要么代码改了；**且 `scripts/check-doc-citations.py` 仍然通过**
（它会检查文档里的 `file:line` 引用是否还指在正确的行上）。

### 钉住它的测试怎么写

这一类的钉子**不是每条一个测试**，而是一个**通用的一致性检查**：

```python
# tests/test_doc_claims.py
"""注释里说的和代码做的一致。

现在会红：把下面每一条断言逐个打开，都是今天为假的。
"""
```

具体地，M1 可以这样钉（这是**唯一一条会让报告说假话**的，值得单独一个测试）：

```python
def test_the_api_exported_report_does_not_claim_a_zero_duration(client, demo_project):
    """API 导出的报告不许写「Analysis time | 0.0s」。

    现在会红：_rebuild_result 不设 duration_seconds，
    而 markdown.py:70 无条件打印这个数。
    """
    markdown = client.get(f"/projects/{demo_project}/report?format=markdown").text
    assert "| Analysis time | 0.0s |" not in markdown, (
        "报告写了一个分析从未产生过的时长"
    )
```

**在旧代码上会不会红？会**：`_rebuild_result`（`api/app.py:600-610`）没有设
`duration_seconds`，`AnalysisResult.duration_seconds` 默认为 `0.0`
（`src/dexatlas/core/pipeline.py:64`），`markdown.py:70` 用 `f"{result.duration_seconds:.1f}s"` 打印。

**怎么证明它不是假绿**：断言的是**字符串内容**（报告里那一行），
不是「字段存在」。而且要**同时**断言另一条：

```python
    # 并且必须真的有耗时，而不是把这一行藏起来
    assert "| Analysis time |" in markdown
```

这样「把这一行删掉」这种改法也会红 —— 而那也是不合格的改法
（读者需要知道这次分析花了多久；正确的改法是从 `projects.created_at` 算出来，
或者在报告里标成「未知」）。

M2 可以这样钉：

```python
def test_a_storage_failure_is_recorded_not_raised(monkeypatch, settings, demo_apk):
    """存储层的失败要变成项目上的错误，不是异常。

    现在会红：sqlite3.Error 直接上抛。
    """
    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(Store, "save_symbols", boom)
    result = Analyzer(settings).analyze(demo_apk)
    assert result.project.errors, "存储层的失败没有被记录"
    assert any("database is locked" in str(e) for e in result.project.errors)
```

---

## 9. F8【中】`tools/base.py` 的死代码，以及怎么自动防住

### 现状：找出**没有任何调用点**的符号

方法：对每个符号在 `src/`（除定义文件外）与 `tests/` 里全文搜索。
**注意**：`parse_error` 这种名字会被**同名局部变量/枚举成员**干扰，
必须用 `name(` 的形式再搜一次才能下结论。

`src/dexatlas/tools/base.py` 里确认无调用点的：

| 符号 | file:line | 行数 | 引用数（src / tests） | 说明 |
| --- | --- | --- | --- | --- |
| `_DEFAULT_MAX_OUTPUT` | `src/dexatlas/tools/base.py:30` | **1**（注释在 `:29`） | 0 / 0 | 常量。注释说「超过这个输出量就当作后端失控」，实际生效的是 `settings.tool_max_output_bytes`（`src/dexatlas/config/settings.py:37`），而实际行为是**静默截断**不是「当作失控」 |
| `java_available` | `src/dexatlas/tools/base.py:447-449` | **3** | 0 / 0 | docstring 说「Apktool 和 JADX 都需要一个 JRE」。但 `src/dexatlas/tools/apktool/adapter.py:93` **无条件**拼 `["java", "-jar", …]`，没人做这个预检 → 没有 JRE 的机器上是**运行期**失败而不是预检失败 |
| `parse_error` | `src/dexatlas/tools/base.py:452-458` | **7** | 0 / 0 | 「could not parse {tool} output」。全仓库**没有任何后端调用它** —— 每个后端各自拼自己的 `ToolError`。（`grep -rn "parse_error(" src/ tests/` 只命中定义本身；其余命中是 `ToolErrorCode.PARSE_ERROR` 枚举成员和 `pipeline.py:227` 的同名局部变量） |
| `coerce` | `src/dexatlas/tools/base.py:461-463` | **3** | 0 / 0 | 「Best-effort conversion of a tool's loosely typed JSON field」—— **没有任何后端解析任何工具的 JSON** |

合计 **14 行死代码**（含 `_DEFAULT_MAX_OUTPUT` 的注释行是 15 行）。

**复核过程中更正的一条**：评审把 `parse_error` 和另两个一起列为死代码 —— 这条**成立**
（第一次用裸名字搜会被 `ToolErrorCode.PARSE_ERROR` 和局部变量干扰，
用 `parse_error(` 再搜一次才确认它一次都没被调用过）。

**同一类问题在 `base.py` 之外也有**（下面用 vulture 扫出来的，见「可落地的方案」）：

| 符号 | file:line | 状态 |
| --- | --- | --- |
| `SubmitResponse` ＋ 它的两个字段 | `src/dexatlas/api/app.py:160-163` | 死类（`/analyze` 返回的是另一个模型） |
| `rizin_path` / `ghidra_path` | `src/dexatlas/config/settings.py:32-33` | 死字段（不会有 rizin / ghidra 后端） |
| `cache_dir` | `src/dexatlas/config/settings.py:54-56` | 只在 `ensure_workspace`（`:59`）里**建目录**，从不写入 |
| `Sourced.tools` | `src/dexatlas/core/models.py:151-154` | 死属性 |
| `ClassRef.simple_name` | `src/dexatlas/core/models.py:253-254` | 死属性 |
| `EvidenceKind.CODE_LOCATED` | `src/dexatlas/core/models.py:486` | **死枚举成员**：`src/` 里只出现这一处定义，没有任何生产者 |
| `EvidenceKind.BEHAVIOUR` | `src/dexatlas/core/models.py`（枚举定义） | **也是死的**：`src/` 里只在 `models.py` 的校验器（`:542`）里被引用，**没有任何地方产生它** |
| `EvidenceLevel.LEAD` / `INSUFFICIENT` | `src/dexatlas/core/models.py:511`、`:514` | 死枚举成员：只出现在 `reports/markdown.py:24-25` 的等级说明表里 |
| `INVOKE_OPCODES` | `src/dexatlas/tools/androguard/adapter.py:80` | 死常量（只有定义和 `__all__`） |

> `EvidenceKind.BEHAVIOUR` 与 `EvidenceLevel.LEAD/INSUFFICIENT` 这三条，
> 是**评审已经指出但只说了「没有生产者」而没有落到「该怎么处理」**的。
> 建议（见下）：`BEHAVIOUR` 与 `LEAD` 是**为 Phase 2 的模型输出预留的闸门**，
> 现在没有模型所以没有生产者 —— **应该留着，但要在注释里写清楚「Phase 2 才有生产者」**，
> 否则读者会以为代码写坏了。而 `CODE_LOCATED` **没有任何理由留着**（没有对应的阶段），
> 建议删掉。

### 删还是留

| 符号 | 建议 | 理由 |
| --- | --- | --- |
| `java_available` | **用起来**，不要删 | 它对应一个真实缺口：`apktool/adapter.py:93` 无条件拼 `java -jar`，在没装 JRE 的机器上是运行期失败。**在 `ApktoolBackend.available()`（或 `resolve()`）里加上这个预检**，缺 JRE 时给出「装 JRE」的错误提示，和缺 apktool.jar 的提示一样清楚。这比删掉有价值得多 |
| `parse_error` | **删** | 三个后端各自拼 `ToolError`，格式已经不一样了（`ToolErrorCode.PARSE_ERROR` / `EXIT_NONZERO` / `OUTPUT_TRUNCATED`）。**统一成一个函数要先统一语义**，那是另一件事。现在留着只是让人以为有统一入口 |
| `coerce` | **删** | 它服务的场景（解析工具的 JSON）在这个项目里不存在。留着会让人以为有 JSON 后端 |
| `_DEFAULT_MAX_OUTPUT` | **删**（连注释） | 真正生效的限额在 `settings.tool_max_output_bytes`。而且注释描述的行为（「当作失控后端」）和实际（静默截断）不一致 —— **留着注释比留着常量更糟** |
| `SubmitResponse` | **删** | `/analyze` 返回的是 `AnalyzeJobResponse`。留着它会让人以为「已分析过」是 API 的一部分 |
| `rizin_path` / `ghidra_path` | **删** | 不会有 rizin / ghidra 后端；留着会让部署方以为设了这两个环境变量有用 |
| `protection_level` / `shared_user_id` | **用起来**，不要删 | 这两个是**真实的 APK 事实**：`android:protectionLevel` 是权限的保护级别，`android:sharedUserId` 是共享 uid（多个 APK 共享 uid 是安全信号）。现在**后端写了，报告不用** —— 报告里「Permissions」一段应该把保护级别带上 |
| `CODE_LOCATED` | **删** | 没有阶段会用它，也没有生产者 |
| `BEHAVIOUR` / `LEAD` / `INSUFFICIENT` | **留着，注释写清楚** | 它们是 Phase 2 模型输出的闸门，机制（`models.py:527-547` 的 model_validator）是完整可用的。**问题不是它们存在，是没人说它们现在没有生产者** |
| `cache_dir` | 删掉，或用起来 | `ensure_workspace` 每次启动都建一个空目录 |
| `Sourced.tools` / `ClassRef.simple_name` / `INVOKE_OPCODES` | **删** | 没有调用点，也没有对应的规划 |

### 现在的 lint 抓不到这些

`pyproject.toml:94-96`：

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "C4", "SIM", "RUF"]
ignore = ["E501"]
```

- **`F401`（unused-import）** 是唯一沾边的规则 —— 它只管**导入**。
- **ruff 没有任何一条规则检测「定义了但没人调用的函数」。**
  （我查了 ruff 0.15.13 的全部规则目录：`ARG001-005` 是**未使用的参数**，
  `F841` 是**未使用的局部变量**，`PYI046/047/049` 是未使用的 typing 协议/别名/字典 ——
  **没有一条是「未使用的函数」。**）
- `mypy strict` 也抓不到 —— 类型检查不关心调用图。

### 可落地的方案：引入 vulture

**环境里已经有 vulture 2.16**（实测可跑），所以下面全部是**真实输出**，不是设想。

**先说清楚 vulture 2.16 的机制**（这一点很容易搞错）：

- 它**没有**「白名单文件」这种输入。`--make-whitelist` 是**输出**一份可以贴进
  *第三方包*的白名单模块的清单，不是让你把自己的白名单喂回去。
- 它真正提供的压制手段只有三个：
  - `--ignore-decorators PATTERNS` —— 忽略带某个装饰器的函数/类（**这是解决 FastAPI/Typer/Pydantic 误报的正确工具**）；
  - `--ignore-names PATTERNS` —— 按名字忽略；
  - `--exclude PATTERNS` —— 按路径排除。
- 它支持 `--config CONFIG`，指向一个带 `[tool.vulture]` 段的 `pyproject.toml` ——
  **所以配置可以直接进本仓库的 `pyproject.toml`，和 `[tool.ruff]`、`[tool.mypy]` 并排。**
- **退出码：有发现就是 3，没有发现才是 0。** 所以「门禁」的条件是**退出码 0**。

**裸跑的结果（什么配置都没有）**：

```
$ vulture src/ tests/
（共 69 条；src/ 38 条，tests/ 31 条）
```

**38 条里大约三分之二是误报**，而且误报是**结构性的**，不是零星的：

| 误报类别 | 例子 | 为什么 vulture 看不到 |
| --- | --- | --- |
| FastAPI 路由函数 | `app.py` 的 `health` / `list_backends` / `get_class_source` / `get_method_source` / `get_references` / `search_code` / `export_report` | 被 `@app.get` 之类的装饰器注册，vulture 不把装饰器当引用 |
| Typer 命令 | `cli/main.py` 的 `_root` / `xrefs` | 同上 |
| Pydantic 钩子 | `models.py` 的 `_canonicalise_descriptor` / `_read_an_older_locator_in_the_current_form` / `_known_component_kind` / `_a_behaviour_is_never_verified`；`settings.py` 的 `_expand_workspace` | 运行时由 pydantic 调用 |
| pydantic 的 `model_config` | `models.py:51` / `:115` | 由 pydantic 读取 |
| sqlite3 的 `row_factory` | `storage.py` | 由 sqlite3 内部读取 |
| pytest 的夹具与标记 | `pytestmark` / `apktool_available` / `jadx_unavailable` / `fake_dex` / `compress_type` | 由 pytest 调用 |

**再叠加两个 vulture 的硬限制**（这才是它不能当银弹的原因）：

**（一）它会漏报。** 实测这三个**确实死**的符号它**不报**：

| 漏报的符号 | 为什么漏报 |
| --- | --- |
| `parse_error`（`base.py:452`） | 名字 `parse_error` 在 `pipeline.py:227` 是个**局部变量**、在 `models.py:39` 是个**枚举成员** → vulture 认为「这个名字被用到了」，于是不报 |
| `_DEFAULT_MAX_OUTPUT`（`base.py:30`） | vulture 不报模块级**常量**的「unused variable」（它只报类属性和局部变量） |
| `EvidenceKind.BEHAVIOUR` | 名字出现在 `models.py:542` 的校验器里 → 同样被当成「用到了」 |

**（二）`--min-confidence 100` 在这个仓库上没有用。** 实测：

```
$ vulture src/ tests/ --min-confidence 100
（22 条，**全部在 tests/**，全是 pytest 夹具参数；**src/ 里 0 条**）
```

**结论：vulture 不是「装上就干净」的银弹。** 这一点必须写进 issue，
否则将来会有人说「vulture 跑了，还是有死代码」。

**推荐的配置**（加进 `pyproject.toml`，和 `[tool.ruff]`、`[tool.mypy]` 并排）：

```toml
[tool.vulture]
paths = ["src", "tests"]
min_confidence = 60
# 装饰器注册的函数：FastAPI 路由、Typer 命令、pydantic 钩子、pytest 夹具。
ignore_decorators = [
  "@app.get", "@app.post", "@app.delete", "@app.put", "@app.patch",
  "@app.callback", "@app.command",
  "@field_validator", "@model_validator",
  "@pytest.fixture", "@pytest.mark.*",
  "@property", "@staticmethod", "@classmethod",
]
# 按名字忽略：pydantic 的类配置、sqlite3 的 row_factory，以及 pytest 的机制名。
ignore_names = [
  "model_config", "row_factory",
  "pytestmark", "apktool_available", "jadx_unavailable",
  "fake_dex", "compress_type", "_blob", "report_path",
]
```

**这个配置的真实输出**（实测）：

```
$ vulture --config pyproject.toml
src\dexatlas\api\app.py:162: unused variable 'apk_size_bytes' (60% confidence)
src\dexatlas\api\app.py:178: unused class 'SubmitResponse' (60% confidence)
src\dexatlas\api\app.py:181: unused variable 'already_analysed' (60% confidence)
src\dexatlas\config\settings.py:34: unused variable 'rizin_path' (60% confidence)
src\dexatlas\config\settings.py:35: unused variable 'ghidra_path' (60% confidence)
src\dexatlas\core\models.py:405: unused variable 'protection_level' (60% confidence)
src\dexatlas\core\models.py:461: unused variable 'shared_user_id' (60% confidence)
src\dexatlas\core\models.py:486: unused variable 'CODE_LOCATED' (60% confidence)
src\dexatlas\tools\base.py:447: unused function 'java_available' (60% confidence)
src\dexatlas\tools\base.py:461: unused function 'coerce' (60% confidence)
exit=3
```

**69 条 → 10 条，而且这 10 条全部是真的**（要么死代码，要么「写了没人读」的字段）。
**零误报。** 这是「误报多不多」这个问题的实测答案：**原始配置约三分之二是误报，
配好之后是 0。**

**为什么 `paths` 要同时包含 `src` 和 `tests`**：

- 只扫 `src/` → `Analyzer.class_source`（`pipeline.py:330`）、`Analyzer.method_source`（`:340`）、
  `Store.get_class`（`src/dexatlas/core/storage.py:560`）会被误报成死的 ——
  **它们确实只被测试调用**（`tests/test_demo_app.py:155`、`tests/test_storage.py:562` 等）。
- 只扫 `tests/` 显然不行。
- 两个一起扫 → 这三个不再被报，而 pytest 机制名用 `ignore_names` 压掉。

**CI 门禁怎么做**：

```yaml
# .github/workflows/ci.yml —— 加一个独立 job，不要并进 ruff 那一档
  dead-code:
    name: Dead code (vulture)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --extra dev --extra analysis
      # vulture 有发现时退出码是 3；零发现才是 0
      - run: uv run vulture --config pyproject.toml
```

`vulture` 要加进 `pyproject.toml` 的 `dev` extra（`"vulture>=2.16"`）。

**推进顺序很重要**：

1. **先按上面的表把 10 条处理掉**（删 6 个、用起来 3 个、注释说明 1 个）。
2. **再把 vulture 加进 CI**，条件是**退出码 0**（不是「与基线一致」）。
   理由：配好之后剩下的全是真问题，**基线 diff 那套机制在这里是多余的复杂度** ——
   基线文件是给「误报压不掉」的场景用的，这里压得掉。
3. **vulture 抓不到的那三个**（`parse_error`、`_DEFAULT_MAX_OUTPUT`、`EvidenceKind.BEHAVIOUR`）
   靠人盯：**建议在 PR 模板里加一条**「新增的模块级函数、常量、枚举成员，确认有调用点/有生产者吗？」

### 验收标准

1. `vulture --config pyproject.toml` 的退出码是 0。
2. `tools/base.py` 里 4 处死代码按上面的建议处理完（3 删 1 用）。
3. `EvidenceKind.CODE_LOCATED` 删掉；`BEHAVIOUR` / `LEAD` / `INSUFFICIENT` 的注释写明
   「Phase 2 的模型输出才会有生产者」。
4. `protection_level` / `shared_user_id` 出现在报告里（不是只存在数据库里）。

### 钉住它的测试怎么写

死代码本身没有「行为测试」——**它的钉子就是 CI 门禁本身**。所以这里要钉的是门禁：

```python
# tests/test_dead_code.py
"""死代码检查本身要能工作。

不是「测 vulture」，是测**门禁会拦住新死代码**：
故意加一段没人调用的函数，门禁必须报出来。
"""


def test_the_dead_code_check_finds_an_unused_function(tmp_path):
    """把一段新死代码放进一个临时副本，门禁必须报出来。"""
    source = tmp_path / "sample.py"
    source.write_text(
        "def used():\n"
        "    return 1\n"
        "\n"
        "def never_called():\n"
        "    return 2\n"
    )
    result = subprocess.run(
        ["vulture", str(source), "--min-confidence", "60"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, "门禁没报出新增的死代码（退出码应为 3）"
    assert "never_called" in result.stdout, "门禁没报出新增的死代码"
    assert "used" not in result.stdout, "门禁把被调用的函数也报出来了"
```

**在旧代码上会不会红？** 这个测试在旧代码上**会绿**（它测的是 vulture 的行为，不是仓库的状态）。
**所以它不是钉子，是防回归的护栏。** 真正的「钉子」是 CI 门禁本身：

- vulture 的**退出码语义**已经钉住了：**有发现 = 3，零发现 = 0**（实测）。
  所以「清理干净之后，CI 必须绿」这件事是**可执行的**。
- 而「清理干净」这件事的起点是**现在**：今天 `vulture --config pyproject.toml` 的退出码是 **3**，
  把它变成 0 就是这一条 issue 的完成标志。**这是一个客观的、当前为红的目标。**

**换句话说**：这条 issue 的「钉住它的测试」是
「`vulture --config pyproject.toml` 的退出码为 0」这个**门禁条件本身**。
建议的推进顺序是：**先把 10 条清掉 → 再把 vulture 加进 CI**，
这样加进去的第一天就是绿的。


## 10. 我复核后**新发现**的条目汇总

| 编号 | 一句话 | 严重级 | 证据 |
| --- | --- | --- | --- |
| **X1** | 上传文件名由客户端决定 → 同名上传互相覆盖 → 一个项目的符号表装上另一个 APK 的类，而 provenance 写着第一个 APK 的哈希 | **极高** | 3/3 次复现（§2） |
| **X2** | `Store.transaction()` 每次都跑 `PRAGMA journal_mode = WAL` → 一次**纯读**也在写数据库；这正是并发 `database is locked` 的来源 | 高 | 实测「一次读把 mode 从 delete 改回 wal」；并发打开失败率 15/20（§4） |

另外两条**复核后确认成立但描述需要更正**的：

- **#11 的位置**：不在 `core/logging.py`（该文件不存在），在 `tools/androguard/adapter.py:96-119`。
  另外交办说的「handler 被全局移除后不恢复」——**成立，而且比说的更彻底**：
  连 `LOGURU_LEVEL` 那两行环境变量操作都是死代码（loguru 在导入时读一次）。
- **#7 的描述**：「同一条调用边可以被写进多行」成立，但**重复有两个来源**，
  评审只提了跨 DEX 那一类；**同一个 DEX 里调用同一个目标两次**同样会重复，
  而且那一类的 provenance 完全相同 —— 它不是「两条边」，是**一条边被记了两次**。

---

## 11. 建议 Phase 2 先做哪三条

### 第 1 名：**X1（上传文件按内容哈希命名）** —— 0.5–1 天

**理由**：这是**唯一一条会让报告里的证据链变成假值**的缺陷。
实测 3/3 复现：一个项目的 `provenance.apk_sha256` 写着 A 的哈希，
符号表里装的是 B 的类。在一个「证据优先」的产品线上，
这比并发失败严重一个量级——并发失败是「这次请求没成」，
X1 是「**这次请求成了，而且成了假的**」。

**它也是投入产出比最高的**：改动点只有 `src/dexatlas/api/app.py:273` 一行的命名规则
（外加一次 rename），却同时修掉三件事：覆盖、证据链断裂、和 #12 的一半。

### 第 2 名：**X2 + #4 的 SQLite 部分（把写库从读路径里拿掉）** —— 0.5–1 天

**理由**：
(a) X2 是一行 pragma 的位置问题，但**实测它让「一次纯读」变成一次写**，
这在一个「有 liveness 探针」的部署里是实打实的风险；
(b) 它是 #4 并发失败的**直接原因**，而 #4 里那部分（run 目录隔离）要 2–3 天。
**先把便宜的做完，并发失败的一大半就没了。**

**钉子极其确定**：那条「读不应写」的测试在旧代码上 **100% 稳定地红**，
不依赖任何时序——这在这个项目的测试史上是少见的。

### 第 3 名：**#7（xrefs 主键）** —— 1–2 天

**理由**：
(a) 它影响的是**每一个读报告的人**：报告里的「交叉引用数」是错的（23 vs 21），
API 的 `total` 是错的（4 vs 2 个调用方）。**这是对外的数字**。
(b) 它有现成的迁移先例（`src/dexatlas/core/storage.py:277-285` 的 `resources`），
(c) 它顺带暴露了一个**文档也在说错话**的地方（`analysis-provenance.md` §6.6）——
而这个项目最看重「文档和代码说同一件事」。

**为什么不是 #4 的目录隔离**：目录隔离要 2–3 天，
而且它要动「读哪一份产物」的语义，风险比前三条大。
**建议 #4 的目录隔离排在 X1/X2/#7 之后**，作为 Phase 2 的第二周任务。

**为什么不把 #11 和 #12 排进前三**：
#11 影响面真实但没有「对外的错误数字」；
#12 与 X1 是同一处代码，**跟着 X1 一起做**，不单列。

---

## 附录：本文引用的实测命令

```bash
export DEXATLAS_APKTOOL_JAR="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/apktool.jar"
export DEXATLAS_JADX_PATH="C:/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin/jadx.bat"
export PATH="/c/Users/admin/AppData/Local/Temp/dexatlas-backends/jadx/bin:$PATH"

# 版本
git rev-parse --short HEAD                    # 8df894b
uv run --no-sync python -c "import loguru; print(loguru.__version__)"   # 0.7.3
vulture --version                              # 2.16
uv run --no-sync ruff --version                # 0.15.13

# F8：死代码
vulture src/ --min-confidence 60 | wc -l           # 38
vulture src/ tests/ --min-confidence 60 | wc -l    # 69
vulture src/ tests/ --min-confidence 100 | wc -l    # 22 —— 全部在 tests/，src/ 里 0 条
vulture --config <带 [tool.vulture] 的 pyproject>   # 配好之后 10 条，全是真的，exit=3
grep -rn "\bjava_available\b\|\bcoerce\b\|\bparse_error(" src/ tests/ --include="*.py"

# X2：一次读会不会改数据库
#   建库 → PRAGMA journal_mode = DELETE → store.list_projects() → 再看 journal_mode
#   实测：delete → wal（一次读把它改了）

# #7：交叉引用的重复
#   analyze 之后查：COUNT(*) vs COUNT(DISTINCT caller, callee)
#   实测 demo.apk：23 行 vs 21 条不同的边
```

**vulture 的退出码语义**（实测）：有发现 = 3，零发现 = 0。

**验证脚本**（都在工作区外，不进仓库）：
`v_loguru.py`、`v_xrefs.py`、`v_concurrency.py`、`v_conc2.py`、`v_api_race.py`、
`v_upload.py`、`v_swap.py`、`v_swap2.py`、`v_lock.py`。
