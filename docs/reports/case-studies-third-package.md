# 第三个案例证据包——独立分析的实测与交接清单

日期：2026年11月18日 · 基准：本 worktree 的 `48a56b5`
（`git rev-parse HEAD`）。

> **本文是什么**：一次**新分析**的产物。它为[需求候选清单 C4](../reports/v1.1.0-candidates.md)
> 指出的「三个案例包实际只覆盖两次分析」这一条，**补出了真实的第三次分析**，
> 并给出「哪些文件放进 `docs/case-studies/attachments/`、放进去之后哪些文档
> 的说法要跟着改」的完整清单。
>
> **本文不是什么**：不是验收结论，不是发版材料。产物**全部在 `.scratch/` 里**，
> 一个字节都没有写进 `docs/case-studies/attachments/`——那一步由主会话在发版
> 测量落定后做。
>
> **本轮纪律**：**没有动 `docs/case-studies/attachments/` 里的任何一个文件**
> （9 个文件一个没碰）；**没有改任何既有文档**；本轮只新增本文一个文件。
> 没有改 `src/`、`tests/`、`scripts/`、`CHANGELOG.md`、`README.md`、
> `README.zh-CN.md`、`docs/status.md`、`docs/reports/phase1-execution-report.md`
> （这四份由主会话的重测量脚本写）。没有运行
> `scripts/refresh-report-figures.py`；没有联网；没有往 C 盘装任何东西。
>
> **行号口径**：本文引用的 `file:line` 一律指**基线 `48a56b5`**（本轮只新增
> 本文，未动任何既有文件，行号不移动）。
>
> **产物位置**：`E:\Dexatlas\.scratch\case3\final\`（**在主 checkout 的 `.scratch`
> 下，不在本 worktree**——worktree 随时可能被清理，产物必须活得比它久）。
> 全部文件都是 `.scratch/`，被 `.gitignore` 忽略，不入库。

---

## 0. 结论速览

| 问题 | 结论 | 依据 |
|---|---|---|
| 第三次独立分析做出来了吗？ | **做出来了**。第 3 篇（api-integration）现在有自己的一次分析：`run_fc8e432d4d094350` | §2 |
| 新的 run 跟旧的是不是同一次？ | **不是**。run id、run 的起止时间、`project.created_at`、耗时四项全部不同；工作区是全新的空目录，DB 是新文件 | §1.3 |
| 计数会不会因为重跑而变？ | **不会，也确实没变**。196 个 JSON 叶子值里，除 run id/时间戳/耗时外的全部相同——5 类 / 8 方法 / 23 call site / 21 call edge / 11 evidence / 1 resource 一字不差 | §3.3 |
| `project_id` 变了吗？ | **没变，也不该变**。它是 APK sha256 的函数（`src/dexatlas/core/models.py:806-809`），同一份 APK 永远是同一个 id。「三次分析」的证据在 **run id**，不在 project id | §1.4 |
| 新包自校验过吗？ | **过**。四个包全部 `verify_package` 通过、`verify_citations` 全部可解析（14 / 14 / 8 / 9 条引用） | §2.3 |
| 放进去要改哪些文档？ | **9 处**，其中 4 处是对外文案（`docs/outreach/` 与两份对外报告）——不改就是对外继续说「只有两次分析」 | §4.3 |
| 顺带补了什么？ | multi-DEX 附录（第 2 篇末尾那一跑）此前**没有任何附件**、正文也没说；本轮补出了它的包与报告 | §2、§4.2 |

---

## 1. 这一轮做了什么

### 1.1 环境

| | |
|---|---|
| 代码树 | 本 worktree 的 `src/`，与主 checkout 的 `src/` 在 `48a56b5` 上**逐字节一致**（`git diff main..HEAD -- src/` 为空，主 checkout 的 `src/` 也无未提交改动） |
| 解释器 | 复用主 checkout 的 `.venv`（Python 3.12.10）——**故意不跑 `uv sync`**：本 worktree 没有自己的 `.venv`，`uv sync` 会与主会话正在跑的重测量抢 uv cache |
| 后端 | `DEXATLAS_JADX_PATH=.scratch/backends/jadx/bin/jadx.bat`、`DEXATLAS_APKTOOL_JAR=.scratch/backends/apktool.jar` |
| 后端版本 | jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4 —— **与旧附件 manifest 里记的完全一致** |
| 临时文件 | 全部在 `.scratch/case3/tmp/`；工作区、产物、日志在 `.scratch/case3/` |

### 1.2 做了什么

四次分析，**四次都是全新的空工作区**（每个工作区一个独立的 `dexatlas.db` 文件）：

| # | 用途 | APK | 入口 | 工作区 |
|---|---|---|---|---|
| 1 | **第 3 篇（api-integration）——本轮的主目标** | `examples/demo-app/demo.apk` | **REST API**：`POST /analyze` → 轮询 → `GET /projects/{id}/report` | `.scratch/case3/ws` |
| 2 | 可选替换第 1 篇 | `examples/demo-app/demo.apk` | CLI `dexatlas analyze` + `dexatlas export` | `.scratch/case3/ws-demo` |
| 3 | 可选替换第 2 篇 | `examples/obfuscated-app/obfuscated.apk` | CLI | `.scratch/case3/ws-obfuscated` |
| 4 | 可选新增：第 2 篇的 multi-DEX 附录 | `examples/multidex-app/multidex.apk` | CLI | `.scratch/case3/ws-multidex` |

**第 1 次为什么走 API 而不是 CLI**：第 3 篇讲的正是 REST API 这条面，
「附件是从 API 那条面导出来的」这句话只有在产物真的经过那条面时才成立。
本次是 uvicorn 起服务 → HTTP 上传 → 后台分析 → 轮询 → HTTP 取报告。

**API 路径有一处必须知道的坑**（`src/dexatlas/api/app.py:380-386`）：
`POST /analyze` 撞上**同一工作区里已分析过的同一 APK**，会**直接返回既有项目、
不新建 run**。所以「独立的新一次分析」必须用**一个空工作区**——这正是
[对应关系报告](case-studies-run-correspondence.md) §6.1 记的那个坑，
本轮绕开了它。

### 1.3 为什么它是一次新的 run（不是复制）

四条独立证据：

1. **run id 不同**：`run_fc8e432d4d094350` ≠ 旧的 `run_e112e71772d34a0e`。
   run id 是 `uuid4().hex[:16]`，随机、与 APK 无关
   （`src/dexatlas/core/runs.py:42-49`——源码里明确写着「两次分析同一份字节
   就是两次 run，id 若是字节的派生就会给它们同一个名字，而这正是这套机制
   要消除的那种同一性」）。
2. **时间戳不同**：`run.started_at` / `run.finished_at` 是本轮的真实时刻；
   `project.created_at` 是本轮新工作区里新建的项目记录的时刻。
3. **工作区是新的**：`.scratch/case3/ws/` 是一个**空目录**，`dexatlas.db`
   是新文件，旧工作区的任何记录都不在里面。
4. **字节确实变了**：`report.md` 与 `report.html` 相对旧包**逐字节不同**
   （§3.2），`report.json` 有 7 个叶子字段不同（§3.3）。旧包与新包的
   `report.md` 若真是同一次渲染，不可能有这些差异。

### 1.4 一条必须说清的边界：`project_id` 不会变，也不该变

新包的 `project_id` **仍然是 `apk_80a8fe0e81204c9f`**，和旧包一样。
这不是复用旧项目，是**内容寻址**的结果：

```python
@classmethod
def new_id(cls, sha256: str) -> str:
    """Project ids are content-addressed, so re-analysing an APK is idempotent."""
    return f"apk_{sha256[:16]}"
```
（`src/dexatlas/core/models.py:806-809`）

同一份 APK 分析多少次，project id 都是这一个字符串。
**「三个包对应三次独立分析」的证据是三个不同的 `run_id`，不是三个不同的
`project_id`**——任何文档里都不应该出现「三个不同的 project id」这种说法，
因为那既做不到也不该做。旧的两份报告里没写错这一点，本文把口径钉死。

---

## 2. 四个新包的实测结果

### 2.1 证据包

| 包 | `project_id` | `run_id` | 包 sha256 | 字节 |
|---|---|---|---|---|
| `api-integration-evidence-package.zip` | `apk_80a8fe0e81204c9f` | **`run_fc8e432d4d094350`** | `139c33915b62bd4a4452fada579ba4842a3f0754f2bd945ddf6dff5d7d9d5bb4` | 6867 |
| `demo-evidence-package.zip`（可选） | `apk_80a8fe0e81204c9f` | `run_e8e49384ab5246ab` | `7bd4b000ade2c2d0a95475757e8eb94f01253b341d0dc71ff042ae5cccaea4e6` | 6873 |
| `obfuscated-evidence-package.zip`（可选） | `apk_2f8d476fb9e71ac4` | `run_dd897202eba74e28` | `5b129b2d5b99fa64304d1484f50b2d3f1281f13c5405d0e7f79543758410113b` | 6200 |
| `multidex-evidence-package.zip`（可选） | `apk_a488e43e38c2b8e9` | `run_4fde2fa0b5254ccb` | `a8c03be8fb001e67b41bae34413977d040d76ac5707b6f48572352bfb01af950` | 6279 |

四个包的 `apk_sha256` 分别是 `80a8fe0e…` / `80a8fe0e…` / `2f8d476f…` /
`a488e43e…`——**三个**不同的 APK，其中 `demo.apk` 出现两次（demo 包与
api-integration 包是同一份字节的两次分析）。`examples/` 下另有
`strings-app/strings.apk` 与 `wide-app/wide.apk` 两个样本，未进入案例材料。

### 2.2 包内三份报告

| 包 | `reports/report.md` | `reports/report.json` | `reports/report.html` |
|---|---|---|---|
| api-integration | `dd5e2a35d1c739f3b48687a5350d0c9bf693635a3bec588766e2f44b6f0ec601`（5171 B） | `2491c02c5898e6011630a660efa17d90237dfc5cf58d8569e58bb0829acbcf0b`（11382 B） | `1dafa26c5c1acee38c2251f85ebf257113eba716ab2ba4d1922886b5fc6f6768`（8549 B） |
| demo | `08140e8d2f26cb761c102b5d0b72e153d8063d5fe27e6a955784f2f12598fd51`（5171 B） | `921d3d3e3c8b6b08f5c3d23488e333d610bfeadf41cbb67ed8c471ea5a67f63e`（11382 B） | `5fe348551df3844eda8cd03356f5d1c821a2fd1f20f7826060759cee27d0db82`（8549 B） |
| obfuscated | `5b0cd9fb84ca7747802cce2a5ec16ec263516231c69b23593b1f82a62d861db5`（3505 B） | `0d5d2fa00b4ba379c0e0011bf4d1899187453534315b8e5f069ea6c9e06ef0f6`（7944 B） | `6f311c336d39b9e1ddc4b57611c427d7f053c9d90631bc0d9bf8fb4d9a705617`（6716 B） |
| multidex | `9d7ca4b8ddae8ab3b11551a68487056e03c7de20f40b2a6b787cc01f6331d12f`（3895 B） | `0f9940c1a6b80f2223430f00a2a4ac403cd01f74d65d9b2776f80bf91f95790b`（8447 B） | `5dbe419f9ddba214e53eed76a0a5f8a31fd173543c171ab36115b42f21318347`（7115 B） |

### 2.3 自校验

用工具自己的校验函数（`dexatlas.reports.evidence_package.verify_package` /
`verify_citations`）跑过四个包：

| 包 | manifest 哈希核对 | 引用可解析 |
|---|---|---|
| api-integration | ✅ | 14 / 14 |
| demo | ✅ | 14 / 14 |
| obfuscated | ✅ | 8 / 8 |
| multidex | ✅ | 9 / 9 |

逐条结果在 `.scratch/case3/final/verification.json`
（sha256 `c3334df753e14fa4ab28f8128abbe298d3bf0a6cd8b1d69045e5a7a8373009b0`）。

### 2.4 散装报告（**从包里取**，理由见 §3.5）

| 文件 | sha256 | 字节 |
|---|---|---|
| `api-integration-report.md` | `dd5e2a35d1c739f3b48687a5350d0c9bf693635a3bec588766e2f44b6f0ec601` | 5171 |
| `api-integration-report.json` | `2491c02c5898e6011630a660efa17d90237dfc5cf58d8569e58bb0829acbcf0b` | 11382 |
| `api-integration-report.html` | `1dafa26c5c1acee38c2251f85ebf257113eba716ab2ba4d1922886b5fc6f6768` | 8549 |
| `demo-report.md` | `08140e8d2f26cb761c102b5d0b72e153d8063d5fe27e6a955784f2f12598fd51` | 5171 |
| `demo-report.json` | `921d3d3e3c8b6b08f5c3d23488e333d610bfeadf41cbb67ed8c471ea5a67f63e` | 11382 |
| `demo-report.html` | `5fe348551df3844eda8cd03356f5d1c821a2fd1f20f7826060759cee27d0db82` | 8549 |
| `obfuscated-report.md` | `5b0cd9fb84ca7747802cce2a5ec16ec263516231c69b23593b1f82a62d861db5` | 3505 |
| `obfuscated-report.json` | `0d5d2fa00b4ba379c0e0011bf4d1899187453534315b8e5f069ea6c9e06ef0f6` | 7944 |
| `obfuscated-report.html` | `6f311c336d39b9e1ddc4b57611c427d7f053c9d90631bc0d9bf8fb4d9a705617` | 6716 |
| `multidex-report.md` | `9d7ca4b8ddae8ab3b11551a68487056e03c7de20f40b2a6b787cc01f6331d12f` | 3895 |
| `multidex-report.json` | `0f9940c1a6b80f2223430f00a2a4ac403cd01f74d65d9b2776f80bf91f95790b` | 8447 |
| `multidex-report.html` | `5dbe419f9ddba214e53eed76a0a5f8a31fd173543c171ab36115b42f21318347` | 7115 |

---

## 3. 与已入库附件的逐字节对比

### 3.1 包 sha256 对照

| 包 | 旧（已入库） | 新（本轮） | 是否同一份 |
|---|---|---|---|
| demo | `399f5bbec0ebe6b6fd379a94394123a76ae6408224d6574e23a9f736298fa22c` | `7bd4b000ade2c2d0a95475757e8eb94f01253b341d0dc71ff042ae5cccaea4e6` | **否** |
| api-integration | `6187665613d58eb33d67a0bc24240a5322194ec119d5f4ea6ab1af1e656cd548` | `139c33915b62bd4a4452fada579ba4842a3f0754f2bd945ddf6dff5d7d9d5bb4` | **否** |
| obfuscated | `3ab1935eb1ad673f519e4b0884d44a8e67741aafbad13d82c987780cd1aa1954` | `5b129b2d5b99fa64304d1484f50b2d3f1281f13c5405d0e7f79543758410113b` | **否** |

### 3.2 `report.md` 的差异只有两行

旧 demo 包 vs 新 demo 包（api-integration 同理，因为它也是 demo.apk）：

```diff
-**Run:** `run_e112e71772d34a0e` (completed, complete)
+**Run:** `run_e8e49384ab5246ab` (completed, complete)
-| Analysis time | 6.6s |
+| Analysis time | 4.5s |
```

`report.html` 同样只有两行变（`<dl class="meta">` 里的 run id 一行、
summary 表里的 Analysis time 一行）。**其余每一个数字都相同**——
同一份 APK 重跑，计数必然一致，耗时必然不同。

### 3.3 `report.json` 的差异只有 7 个叶子字段

旧 demo 包 → 新 demo 包（196 个叶子值里）：

| 字段 | 旧 | 新 |
|---|---|---|
| `run.id` | `run_e112e71772d34a0e` | `run_e8e49384ab5246ab` |
| `run.started_at` | `2026-11-15T20:46:03.503656+00:00` | `2026-11-17T18:31:05.006900+00:00` |
| `run.finished_at` | `2026-11-15T20:46:10.121741+00:00` | `2026-11-17T18:31:09.521876+00:00` |
| `run.duration_seconds` | `6.61` | `4.516` |
| `summary.duration_seconds` | `6.61` | `4.52` |
| `project.created_at` | `2026-11-14T12:14:19.325275+00:00` | `2026-11-17T18:31:05.006900+00:00` |
| `generated_at` | `2026-11-15T20:46:14.728759+00:00` | `2026-11-17T18:31:11.627790+00:00` |

**其余 196 个叶子值逐字节相同**——包括 5 类 / 8 方法 / 7 of 8 反编译 /
23 call site / 21 call edge / 11 evidence / 1 resource 的每一个数。
obfuscated 包同理（158 个叶子值里只有这 7 个不同）。

`project.created_at` 这一格是**新工作区**的直接证据：旧包里它是 2026-11-14
那一次工作区的项目记录，本轮它是 2026-11-17 新建的另一条项目记录——
虽然两条记录的 id 字符串相同。

### 3.4 HTTP 面与包的关系（第 3 篇的引文可以逐字用）

| 比较 | 结果 |
|---|---|
| `GET /projects/{id}/report?format=markdown`（HTTP 正文）vs 包内 `reports/report.md` | **逐字节相同**（`dd5e2a35…`） |
| `GET /projects/{id}/report?format=json`（HTTP 正文）vs 包内 `reports/report.json` | 203 个叶子值里**只有 1 个不同**：`generated_at`（渲染时刻，HTTP 是 `18:30:19.600970`，包里是 `18:30:23.635063`） |

两条都对得上源码：HTTP 与包都调同一个 `render_markdown(result)`
（HTTP：`src/dexatlas/api/app.py:807-816`；包：
`src/dexatlas/reports/evidence_package.py:102`），包里的报告是从工作区里
已发布的那次 run 重建出来的（`src/dexatlas/cli/main.py:882`）。

**这意味着**：`docs/case-studies/api-integration.md` §3.4 引的那段
`# DexAtlas analysis report …` 输出，现在可以**直接照抄附件里的
`api-integration-report.md`**，不需要再说「正文引的那次和附件不是同一次」。

### 3.5 散装报告为什么从包里取，而不是取 `analyze` 写出来的那份

实测：Windows 上 `dexatlas analyze -o` 写出的 Markdown 是 **CRLF**
（5262 B，91 行全是 `\r\n`），而包里的同一份报告是 **LF**（5171 B）。
已入库的 6 份散装报告**全部是 LF**，且旧的 `demo-report.md` 与旧包内的
`reports/report.md` **逐字节相同**（都是 `1594a0c1…`）。

所以散装文件取自包内 `reports/`，理由有两条：
一是与既有附件的换行符一致（LF），二是**散装文件与包内文件逐字节相同**，
读者拿 manifest 里的哈希就能直接核对散装文件。
旧附件里 `demo-report.json` 与包内 `report.json` **不一致**（差两个时间戳），
所以 `docs/case-studies/demo-app-walkthrough.md:293-297` 那段「核对哈希时
注意」的说明，在换上本轮这批文件后**不再成立**，需要改（§4.3 第 6 条）。

---

## 4. 放进去要改哪几处

产物在 `E:\Dexatlas\.scratch\case3\final\`。下面两张表是**清单**，
主会话按表复制即可。

### 4.1 必做：把「三次分析」变成真的（4 个文件）

| 源文件（`.scratch/case3/final/`） | 目标路径（仓库内） | sha256 |
|---|---|---|
| `api-integration-evidence-package.zip` | `docs/case-studies/attachments/api-integration-evidence-package.zip` | `139c33915b62bd4a4452fada579ba4842a3f0754f2bd945ddf6dff5d7d9d5bb4` |
| `api-integration-report.md` | `docs/case-studies/attachments/api-integration-report.md` | `dd5e2a35d1c739f3b48687a5350d0c9bf693635a3bec588766e2f44b6f0ec601` |
| `api-integration-report.json` | `docs/case-studies/attachments/api-integration-report.json` | `2491c02c5898e6011630a660efa17d90237dfc5cf58d8569e58bb0829acbcf0b` |
| `api-integration-report.html` | `docs/case-studies/attachments/api-integration-report.html` | `1dafa26c5c1acee38c2251f85ebf257113eba716ab2ba4d1922886b5fc6f6768` |

做完后，三个证据包对应**三个互不相同的 run**：

| 包 | run_id |
|---|---|
| `demo-evidence-package.zip` | `run_e112e71772d34a0e`（旧的，不动） |
| `api-integration-evidence-package.zip` | `run_fc8e432d4d094350`（**新的**） |
| `obfuscated-evidence-package.zip` | `run_8d6735d410174df6`（旧的，不动） |

三个包的 `report.md` 也随之**互不相同**（旧 demo 包的 `report.md` 与旧
api 包相同；新 api 包与旧 demo 包差一个 run id 和一个耗时）。

**但注意**：只做这 4 个文件，第 1 篇和第 3 篇仍然是**同一份 APK 的两次
分析**，两篇正文引的**各自那次**分析仍然与附件不是同一次（§6.2、§6.1）。
要一次做彻底，走 4.2。

### 4.2 可选：一次做彻底（另外 10 个文件）

| 源文件 | 目标路径 | sha256 | 作用 |
|---|---|---|---|
| `demo-evidence-package.zip` | `docs/case-studies/attachments/demo-evidence-package.zip` | `7bd4b000ade2c2d0a95475757e8eb94f01253b341d0dc71ff042ae5cccaea4e6` | 换掉旧包 |
| `demo-report.md` | `docs/case-studies/attachments/demo-report.md` | `08140e8d2f26cb761c102b5d0b72e153d8063d5fe27e6a955784f2f12598fd51` | 换掉旧散装 |
| `demo-report.json` | `docs/case-studies/attachments/demo-report.json` | `921d3d3e3c8b6b08f5c3d23488e333d610bfeadf41cbb67ed8c471ea5a67f63e` | 换掉旧散装 |
| `demo-report.html` | `docs/case-studies/attachments/demo-report.html` | `5fe348551df3844eda8cd03356f5d1c821a2fd1f20f7826060759cee27d0db82` | 换掉旧散装 |
| `obfuscated-evidence-package.zip` | `docs/case-studies/attachments/obfuscated-evidence-package.zip` | `5b129b2d5b99fa64304d1484f50b2d3f1281f13c5405d0e7f79543758410113b` | 换掉旧包 |
| `obfuscated-report.md` | `docs/case-studies/attachments/obfuscated-report.md` | `5b0cd9fb84ca7747802cce2a5ec16ec263516231c69b23593b1f82a62d861db5` | 换掉旧散装 |
| `obfuscated-report.json` | `docs/case-studies/attachments/obfuscated-report.json` | `0d5d2fa00b4ba379c0e0011bf4d1899187453534315b8e5f069ea6c9e06ef0f6` | 换掉旧散装 |
| `obfuscated-report.html` | `docs/case-studies/attachments/obfuscated-report.html` | `6f311c336d39b9e1ddc4b57611c427d7f053c9d90631bc0d9bf8fb4d9a705617` | 换掉旧散装 |
| `multidex-evidence-package.zip` | `docs/case-studies/attachments/multidex-evidence-package.zip` | `a8c03be8fb001e67b41bae34413977d040d76ac5707b6f48572352bfb01af950` | **新增**：第 2 篇附录的包 |
| `multidex-report.{md,json,html}` | `docs/case-studies/attachments/multidex-report.{md,json,html}` | 见 §2.4 | **新增**：第 2 篇附录的报告 |

走完 4.1 + 4.2 的效果：

- 三个证据包 ↔ **三次互不相同的分析**（`run_e8e49384…` / `run_fc8e432d…` / `run_dd897202…`），
  全部来自本轮，同一套后端版本；
- 每篇走查的**附件**与**正文引的那次分析**之间的差距只剩「run id 与耗时」，
  正文可以把耗时改成与附件一致（见 §4.3）；
- 第 2 篇的 multi-DEX 附录**第一次有附件**，正文里那句「附录那一跑没有附件」
  也要跟着改（§4.3 第 8 条）。

⚠️ **一条容易踩的坑**：换包之后，第 1 篇正文引的 `4.9 s` 与新 demo 包里的
`4.5 s` 不一致；而新 api 包里的耗时**恰好也是 `4.9 s`**。两篇引的时长会
「看起来一样」但各指不同的运行。改的时候要按包对号入座，别让读者以为
两篇引的是同一次。

### 4.3 文档里要跟着改的说法（9 处）

> 行号指基线 `48a56b5`。本轮**一处都没改**，留给主会话在放完附件后统一动。

| # | 文件:行 | 现在的说法 | 要改成 |
|---|---|---|---|
| 1 | `docs/case-studies/README.md:20-26` | 「three packages, six report files」，且「case study 3 links case study 1's `demo-report.*` files」 | 附件变成 **三包 + 九份散装报告**；第 3 篇链接**它自己**的 `api-integration-report.*`，不再借用第 1 篇的文件 |
| 2 | `docs/case-studies/README.md:36-38` | 「the three evidence packages cover only two analyses … the demo and api-integration packages come from one run (`run_e112e717…`) and their `report.md` and `report.html` are byte-identical」 | 改成三个包对应三次分析（列出三个 run id），并说明「同一份 APK 的两次分析，报告除 run id 与耗时外逐字节相同」 |
| 3 | `docs/case-studies/api-integration.md:5-6` | 「the session quoted below is `run_6506002de5d8486a`; the attached package carries a different run of the same APK, `run_e112e71772d34a0e`」 | 附件现在是 `run_fc8e432d4d094350`；正文引的那次应**改成附件这一次**（§3.4 已证明 HTTP 输出与包内 `report.md` 逐字节相同，可以直接照抄） |
| 4 | `docs/case-studies/api-integration.md:203` 与 `:252` | 正文引的 `run_6506002de5d8486a` | 同上 |
| 5 | `docs/case-studies/api-integration.md:212` 与 `:217-222` | 「Ready-made attachments」指向 `attachments/demo-report.*`；以及「Which analysis they come from」整段（说散装文件是第 1 篇的、包里是 `run_e112e717…`、并解释 `run_6506002de5d8486a` 不在任何附件里） | 附件链接改成 `attachments/api-integration-report.*`；「Which analysis they come from」整段可以删掉或改写成「正文引的就是附件这一次」 |
| 6 | `docs/case-studies/demo-app-walkthrough.md:5-6`、`:234`、`:286-297` | 引 `4.9 s`、附件 `run_e112e717…` / `6.6 s`；末尾那段「包内 `report.json` 是 `56251060…`，散装的是 `6cd7fa0b…`，差两个时间戳字段」 | 若走 4.2：run id 与耗时改成新包的（`run_e8e49384ab5246ab` / `4.5 s`）；**末尾那段哈希说明要删或改写**——新散装文件与包内文件逐字节相同，哈希都是 `921d3d3e…` |
| 7 | `docs/case-studies/obfuscated-app.md:7-8`、`:250-256` | 「the attached report is a later run of `obfuscated.apk` (`run_8d6735d410174df6`, 6.0 s)」「a different run from the session quoted in §3 … the counts match and the timings do not」 | 若走 4.2：改成新包（`run_dd897202eba74e28`，5.0 s），并把「the counts match and the timings do not」按新耗时改 |
| 8 | `docs/case-studies/obfuscated-app.md` 附录末尾 | 附录那一跑**没有附件**，正文也没说 | 若走 4.2：补上 `multidex-report.*` 与 `multidex-evidence-package.zip` 的链接与说明 |
| 9 | **对外文案**：`docs/outreach/cover-letter-templates.md:35-40`、`docs/outreach/project-brief.md:123-128`、`docs/outreach/publish-review.md:341`、`docs/reports/outreach-publish-checklist.md:43`、`:68-69`、`:102-104`、`docs/reports/m10-invitation-sender-checklist.md:272`、`docs/reports/next-engagements.md:280-289` 与 `:442` | 「the three evidence packages hold **only two analyses**」「三个证据包只覆盖两次分析」「Do not present them as three independent analyses or three client cases」 | 换成「三个证据包对应三次独立分析」。**这是本轮最要紧的一处**：不改，对外仍然在说一个已经不成立的事实 |

还有两处**本轮不必改、但主会话应知道**：

- `docs/reports/case-studies-run-correspondence.md` 的 §0 结论行与 §7.2
  （它写的是「本轮**不补**第三个包，先把文档改对」）——现在包已经补出来了，
  那份报告的结论行需要加一句指向本文，否则两份报告会互相矛盾。
- `docs/reports/README.md` 的索引表要加本文一行（本文按要求**没有**自己加）。

---

## 5. 复现命令

```bash
cd E:/Dexatlas
export DEXATLAS_JADX_PATH="$PWD/.scratch/backends/jadx/bin/jadx.bat"
export DEXATLAS_APKTOOL_JAR="$PWD/.scratch/backends/apktool.jar"

# —— 第 3 篇：走 REST API ——
mkdir -p .scratch/case3/ws
DEXATLAS_WORKSPACE="$PWD/.scratch/case3/ws" .venv/Scripts/uvicorn.exe \
    dexatlas.api.app:app --host 127.0.0.1 --port 8931 &
#   POST /analyze → 轮询 GET /projects/{id} → GET /projects/{id}/report?format=markdown
.venv/Scripts/dexatlas.exe export apk_80a8fe0e81204c9f \
    -o .scratch/case3/out/api-integration-evidence-package.zip \
    --workspace "$PWD/.scratch/case3/ws"

# —— 其余三个：走 CLI ——
for n in demo obfuscated multidex; do
  .venv/Scripts/dexatlas.exe analyze "examples/$n-app/$n.apk" \
      --workspace "$PWD/.scratch/case3/ws-$n"
  .venv/Scripts/dexatlas.exe export "apk_$(sha256sum "examples/$n-app/$n.apk" | cut -c1-16)" \
      -o ".scratch/case3/out/$n-evidence-package.zip" --workspace "$PWD/.scratch/case3/ws-$n"
done
```

驱动的 HTTP 脚本在 `.scratch/case3/`（`drive_api.py` 走 API、`verify_packages.py`
做自校验），校验脚本的输出即 `.scratch/case3/final/verification.json`。

---

## 6. 这一轮没有做的事

- **没有**往 `docs/case-studies/attachments/` 写任何东西（9 个既有文件一个没碰）；
- **没有**改任何既有文档（本轮只新增本文）；
- **没有**动 `src/`、`tests/`、`scripts/`；
- **没有**动 `docs/reports/phase1-execution-report.md`、`README.md`、
  `README.zh-CN.md`、`docs/status.md`；
- **没有**运行 `scripts/refresh-report-figures.py`；
- **没有**联网，**没有**往 C 盘装任何东西；
- **没有**在本文里宣称「三个案例包已经对应三次分析」——那要等主会话把附件
  放进去之后才成立。本文说的是「产物已经做好、清单在此、还差复制与改文档」。
