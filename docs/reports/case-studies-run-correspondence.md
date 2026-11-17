# 案例证据包与「三次分析」的对应关系——实测核对

日期：2026年11月18日 · 核对基准：本 worktree 的 `d43369b`
（`git rev-parse HEAD`）。

> **本文是什么**：一次**对既有附件的核对**的产物。它把
> [需求候选清单 C4](../reports/v1.1.0-candidates.md)指出的
> 「三个案例包实际只覆盖两次分析」这一条，从**推测**变成**实测结论**，
> 并给出「第三个包补不补」的结论与方案。
> 核对本身没有改动任何附件；核对之后按核对结果改了 `docs/` 下四份走查文档
> 的措辞（§8 列了清单）。
>
> **本文不是什么**：不是验收结论，不是计划书，不是需求文档。
> 它只核对既有附件与既有文档之间的事实是否对得上。
>
> **本轮纪律**：**没有重新生成任何附件**——没有运行 `dexatlas analyze`、
> 没有动 `docs/case-studies/attachments/` 里的任何一个文件；
> 没有运行 `scripts/refresh-report-figures.py`；没有联网；
> 没有改动 `src/`、`tests/`、`scripts/`、`CHANGELOG.md`，
> 也没有改动 `README.md`、`README.zh-CN.md`、`docs/status.md`、
> `docs/reports/phase1-execution-report.md`（这四份由主会话的重测量脚本写）。
> 改动只落在 `docs/` 下：本文、本文在 `docs/reports/README.md` 的索引行、
> 以及 `docs/case-studies/` 下四份走查文档的措辞。
>
> **行号口径**：本文引用的 `file:line` 一律指**基线 `d43369b`**（本轮改动
> 之前的那棵树）。本轮改过 `docs/case-studies/` 下四份文件，改动之后行号会
> 移动；要看基线原文用 `git show d43369b:<path>`。

---

## 0. 结论速览

| 问题 | 结论 | 依据 |
|---|---|---|
| 三个案例包覆盖几次分析？ | **两次**。`demo` 与 `api-integration` 出自同一次运行 `run_e112e71772d34a0e`；`obfuscated` 出自另一次 `run_8d6735d410174df6` | §2、§3、§4 |
| 两个包为什么一模一样？ | 两者的 `report.md`、`report.html` **逐字节相同**（sha256 `1594a0c1…` / `82bcb84c…`）；`report.json` 只差一个 `generated_at` 字段 | §4 |
| 三份走查正文引用了几次运行？ | **至少四次**：正文引用的 run id / 耗时，与附件里的那次**不是同一次**（§6 的四处发现） | §6 |
| 案例索引有没有说错？ | 索引**已经**写对了（「三个走查、两个样本；三个证据包只覆盖两次分析」）——这一句在 `feb4ae1` 就改过 | §5.1 |
| 走查正文有没有说错？ | **有**。第 3 篇声称附件「from the same analysis」，但它引用的 run id 在整个仓库里不存在；第 1、2 篇的耗时与附件报告里的耗时对不上；第 2 篇的 multi-DEX 附录那一跑**没有附件，正文也没说** | §6 |
| 第三个包补不补？ | **补，但不是加一个新包，而是把第 3 篇换成它自己那次分析的包**（现方案）。本轮**不补**，先把文档改对 | §7 |
| **后来补上了吗？** | **补上了（2026-11-18）**：四个包、四次分析全部入库（`run_e8e49384…` / `run_fc8e432d…` / `run_dd897202…` / `run_4fde2fa0…`），见 [第三个案例证据包](case-studies-third-package.md)。**本文的结论仍按基线树 `d43369b` 成立**——它记录的是补包之前的状态 | — |
| 不补的话对外怎么说？ | 「**三个案例走查、三份证据包、两次独立分析**；第 1 篇与第 3 篇共用一次 `demo-app` 分析」——**不能**说「三次分析」或「三份独立证据」 | §7.4 |

---

## 1. 核对方法

核对在项目根目录的 `.scratch/csc/` 下做（临时文件，不入库）：

```bash
# 附件逐个取哈希
sha256sum docs/case-studies/attachments/*

# 解包到临时目录
mkdir -p .scratch/csc
for z in demo api-integration obfuscated; do unzip -q -d .scratch/csc/$z docs/case-studies/attachments/$z-evidence-package.zip; done

# 报告里的身份字段
python -c "import json;d=json.load(open('.scratch/csc/demo/reports/report.json'));print(d['project'],d['run']['id'],d['run']['started_at'])"
```

判断口径有两条，一条比一条硬：

1. **字节层**：同一份文件在两处的 sha256 相同，即为同一份产物。
2. **记录层**：报告里的 `project.id` / `run.id` / `run.started_at` /
   `run.finished_at` 指向哪一次分析。这两条独立成立时，
   「几次分析」就不是靠推测，而是被钉死了。

第 2 条之所以更硬，是因为 `run_id` 是**随机**的：

```python
# src/dexatlas/core/runs.py:42-49
def new_run_id() -> str:
    return f"run_{uuid4().hex[:RUN_ID_LENGTH]}"
```

重新分析同一个 APK 会得到**新的** run id，而 `report.md` 的正文里印着这个
run id（`docs/case-studies/attachments/demo-report.md:7`：
`**Run:** \`run_e112e71772d34a0e\``）。所以：**两个包的 `report.md`
逐字节相同，只可能是因为它们导出自同一条 run 记录**——不存在
「碰巧渲染出一样的结果」这种可能。

---

## 2. 附件实测清单

`docs/case-studies/attachments/` 下共 **9 个文件**（6 个散装报告 + 3 个 zip）：

| 文件 | 字节 | sha256 |
|---|---:|---|
| `demo-evidence-package.zip` | 6880 | `399f5bbec0ebe6b6fd379a94394123a76ae6408224d6574e23a9f736298fa22c` |
| `api-integration-evidence-package.zip` | 6880 | `6187665613d58eb33d67a0bc24240a5322194ec119d5f4ea6ab1af1e656cd548` |
| `obfuscated-evidence-package.zip` | 6214 | `3ab1935eb1ad673f519e4b0884d44a8e67741aafbad13d82c987780cd1aa1954` |
| `demo-report.md` | 5171 | `1594a0c19aa6c165ae0d55738eba92921c10f903d67888469c6551765efdc8f9` |
| `demo-report.html` | 8549 | `82bcb84c37db4f6419afef2616e646af5be44e507ebbe91df8dbb6c5e7b4a838` |
| `demo-report.json` | 11381 | `6cd7fa0be79fde26bb3821a2210e954da4f3bdfaca0adbd7014aad93ec88fa67` |
| `obfuscated-report.md` | 3505 | `e82349bff00b4807cced192327d719d350aab2ed5d4f17ac2f105ffb3a2733fd` |
| `obfuscated-report.html` | 6716 | `9b201cd21ab1660e54554ce1d5f927f807dcb1fae38a8cc2423545ae4ad2c0dc` |
| `obfuscated-report.json` | 7945 | `31124280dc4be4828c504ccb8ff48fba8fa9207725b1ed017c4bd3509fc214b2` |

**没有 `api-integration-report.md` / `.json` / `.html`。** 第 3 篇走查
（`docs/case-studies/api-integration.md:212-214`）链的是**第 1 篇的**
`demo-report.*` 三个文件——这是后文所有问题的根。

三个 zip 的内部清单完全同构，各 4 项：

```
manifest.json
reports/report.html
reports/report.json
reports/report.md
```

包内各文件的 sha256（解包后实测）：

| 包内路径 | demo 包 | api-integration 包 | obfuscated 包 |
|---|---|---|---|
| `reports/report.md` | `1594a0c1…` | `1594a0c1…` | `e82349bf…` |
| `reports/report.html` | `82bcb84c…` | `82bcb84c…` | `9b201cd2…` |
| `reports/report.json` | `56251060…` | `2a08ab09…` | `d4ad1405…` |
| `manifest.json` | `1c4c36ff…` | `c3064710…` | `d28b26f9…` |

（表中给的是完整 sha256 的前 8 位，`…` 表示其余部分省略。）

---

## 3. 三个包 ↔ 两次分析

三个包自带的 `manifest.json` 里写着 `project_id` / `run_id` / `apk_sha256`，
三份实测如下：

| 包 | `project_id` | `run_id` | `apk_sha256` | `package_generated_at` |
|---|---|---|---|---|
| `demo-evidence-package.zip` | `apk_80a8fe0e81204c9f` | `run_e112e71772d34a0e` | `80a8fe0e…7969ff9` | `2026-11-15T20:46:14.729759+00:00` |
| `api-integration-evidence-package.zip` | `apk_80a8fe0e81204c9f` | `run_e112e71772d34a0e` | `80a8fe0e…7969ff9` | `2026-11-15T20:46:33.931324+00:00` |
| `obfuscated-evidence-package.zip` | `apk_2f8d476fb9e71ac4` | `run_8d6735d410174df6` | `2f8d476f…c299540` | `2026-11-15T20:46:30.124302+00:00` |

**两次分析，就是这两行 run id。**

- **第一次** `run_e112e71772d34a0e`：`demo.apk`
  （`apk_sha256 = 80a8fe0e81204c9fe9a74625806518c101030440a65cae4b27a0e224e7969ff9`），
  `run.started_at = 2026-11-15T20:46:03.503656+00:00`，
  `run.finished_at = 2026-11-15T20:46:10.121741+00:00`，
  报告里写「Analysis time | 6.6s」。
  **`demo` 包与 `api-integration` 包都来自这一次。**
- **第二次** `run_8d6735d410174df6`：`obfuscated.apk`
  （`apk_sha256 = 2f8d476fb9e71ac4490059c1d9849f22732254cc7e538a7eebe86aca6c299540`），
  `run.started_at = 2026-11-15T20:46:17.850246+00:00`，
  `run.finished_at = 2026-11-15T20:46:23.890215+00:00`，
  报告里写「Analysis time | 6.0s」。
  **`obfuscated` 包来自这一次。**

> **为什么 `demo` 与 `api-integration` 必然同源（结构性证据）**
> `dexatlas export` 是**按项目**导出的，取的是该项目**当前发布的那一次 run**
> （`src/dexatlas/cli/main.py:882` 调 `analyzer.store.get_published_run(project_id)`；
> `src/dexatlas/core/storage.py:847-865`）。同一个项目 `apk_80a8fe0e81204c9f`
> 在同一个工作区里只有一条 published run，所以两个包导出的必然是同一条
> run 记录——除非中间又分析过一次并重新发布了。
> 而 run id 是 `uuid4()` 随机生成的，**两次分析不可能撞出同一个 run id**。

---

## 4. 报告文件的字节比较

### 4.1 `report.md` 与 `report.html`：demo 与 api-integration 完全相同

sha256 相同即为逐字节相同，两份都是 `1594a0c1…`（md）与 `82bcb84c…`（html），
字节数也同（5171 / 8549）。

原因可以解释清楚：**这两份报告里不印任何时间戳**。实测
`grep -c 'generated_at\|created_at'` 对 `report.md` 与 `report.html` 均为 **0**
（包里与散装的都是 0）。它们印的是项目 id、APK 哈希、run id、工具版本——
这些在同一份 run 记录里全都一样，所以逐字节相同。

`report.json` 则印时间戳，所以它三者互不相同，但差别极小：

| 比较 | 差异字段 |
|---|---|
| demo 包 `report.json` ↔ api-integration 包 `report.json` | **仅** `generated_at`（`20:46:14.728759` ↔ `20:46:33.931324`） |
| demo 包 `report.json` ↔ 散装 `demo-report.json` | `generated_at` 与 `project.created_at` |
| obfuscated 包 `report.json` ↔ 散装 `obfuscated-report.json` | `generated_at` 与 `project.created_at` |

也就是说，**同一个包与散装文件之间，JSON 有两个字段不同**。`project.created_at`
的差异是这一条：

| 项目 | 包内 `report.json` 的 `project.created_at` | 散装 `report.json` 的 `project.created_at` | 该次 `run.started_at` |
|---|---|---|---|
| `apk_80a8fe0e81204c9f` | `2026-11-14T12:14:19.325275+00:00` | `2026-11-15T20:46:03.503656+00:00` | `2026-11-15T20:46:03.503656+00:00` |
| `apk_2f8d476fb9e71ac4` | `2026-11-15T19:58:23.792957+00:00` | `2026-11-15T20:46:17.850246+00:00` | `2026-11-15T20:46:17.850246+00:00` |

散装那份的 `project.created_at` 恰好**等于该次 run 的 `started_at`**
（项目记录与这次分析同时建立）；包内那份的项目记录建立得**更早**——
demo 项目早 32.5 小时（2026-11-14T12:14 到 2026-11-15T20:46），
obfuscated 项目早 47 分 54 秒（19:58:23 到 20:46:17）。
两次渲染的 `run.id`、`run.started_at`、`run.finished_at`、APK 哈希、
全部计数**完全一致**——所以是同一次分析，在**两种项目记录状态**下被渲染了两遍。

### 4.2 由此暴露的一处读者路径断点

`docs/case-studies/README.md` 让读者「unzip the package and check its
manifest hashes」。实测这两条路径**对 `report.json` 不通**：

| 文件 | 包 manifest 记录的 sha256 | 散装文件的 sha256 | |
|---|---|---|---|
| `reports/report.md` | `1594a0c1…` | `1594a0c1…` | ✅ 一致 |
| `reports/report.html` | `82bcb84c…` | `82bcb84c…` | ✅ 一致 |
| `reports/report.json` | `56251060…` | `6cd7fa0b…` | ❌ **不一致** |

读者若按索引的指引，把散装 `demo-report.json` 拿去和包 manifest 对哈希，
**会对不上**，而且 manifest 并没有给出任何说明。`obfuscated` 一侧同构：
包内 `d4ad1405…` vs 散装 `31124280…`。

---

## 5. 文档现状核对

### 5.1 案例索引：已经写对了

`docs/case-studies/README.md:33-37` 在基线上是这么写的：

> Three walkthroughs cover three first-party APKs — `demo-app`, `obfuscated-app`
> and `multidex-app` (the multi-DEX appendix) — with case studies 1 and 3 both
> analysing the same `demo-app` APK; the three evidence packages cover only two
> analyses, because the demo and api-integration packages come from one run
> (`run_e112e717…`) and their `report.md` and `report.html` are byte-identical.

这段在 `feb4ae1`（`docs/case-studies`：人设口吻……并点明「三个视角、两个样本」）
里就改好了，**与本次实测一致**：三个走查、三个一方 APK（`demo-app`、
`obfuscated-app`、`multidex-app`）、三个证据包、两次分析、两个包的
`report.md`/`report.html` 字节相同。

`docs/reports/outreach-publish-checklist.md:100-110` 也已把这条列为
发版前的必查项，且写的是对的。

**因此 C4 这条候选里「索引写着三套」的前描述已经过时**——现在的索引没有
这个错。剩下的错在**走查正文**与**索引的附件说明句**（§5.2、§6）。

### 5.2 索引的附件说明句：仍有一处会误导

`docs/case-studies/README.md` 的附件说明句**改前**写的是（引文中的链接已改指向，
否则从本报告所在的 `docs/reports/` 解析不到）：

> **Attachments:** every study's report (Markdown, JSON, offline HTML) and a
> minimal evidence package are committed under
> [`attachments/`](../case-studies/attachments/) —

「every study's report」不成立：**第 3 篇没有自己的报告文件**，它链的是
第 1 篇的 `demo-report.*`。本轮已改（§8 的改动清单）。

---

## 6. 走查正文与附件对不上的地方（本轮新发现）

前三处**不是措辞问题，是正文引用的运行与附件承载的运行不是同一次**；
第四处是「有没有附件」这件事，正文没有交代。

### 6.1 第 3 篇引用的 run id 在整个仓库里不存在

`docs/case-studies/api-integration.md:201`（`GET /report?format=markdown`
的输出）与 `:241`（客户端输出）都写着：

```
**Run:** `run_6506002de5d8486a` (completed, complete)
report:  schema 3, run run_6506002de5d8486a (complete)
```

全仓库检索，`run_6506002de5d8486a` **只出现在这两行正文里**：

```
docs/case-studies/api-integration.md:201
docs/case-studies/api-integration.md:241
```

它**不在任何附件里**——`api-integration-evidence-package.zip` 内的
`report.md`/`report.json`/`report.html` 印的都是 `run_e112e71772d34a0e`
（§2、§3）。而 §3.4 又声称附件是「from the same analysis … exported over
HTTP per §3.4」——**这句话不成立**：附件里的那次分析不是正文里那次。

### 6.2 第 1 篇的耗时与附件对不上

| 出处 | 耗时 |
|---|---|
| `docs/case-studies/demo-app-walkthrough.md:5` | 「**Run:** one `dexatlas analyze`, 4.9 s」 |
| `docs/case-studies/demo-app-walkthrough.md:60` | 正文引用的输出「1 resource string (**5.0s**)」 |
| `docs/case-studies/attachments/demo-report.md` | 「Analysis time \| **6.6s**」 |
| `docs/case-studies/attachments/demo-report.json` | `run.started_at` → `run.finished_at` = **6.618 s** |

### 6.3 第 2 篇同样对不上

| 出处 | 耗时 |
|---|---|
| `docs/case-studies/obfuscated-app.md:7` | 「**Runs:** **5.1 s** and **4.8 s**」 |
| `docs/case-studies/obfuscated-app.md:296-297` | 附录那一跑的汇总行：「… jadx 7 of 11 methods decompiled, **4.8 s**」 |
| `docs/case-studies/attachments/obfuscated-report.md` | 「Analysis time \| **6.0s**」 |

其中 4.8 s 那一半指的是 multi-DEX 附录的 `multidex.apk`
（`apk_a488e43e38c2b8e9`）。**它没有附件，而正文没有说这一点**——
附录跑完就结束了（`docs/case-studies/obfuscated-app.md:296-297` 之后是文末），
既没有 `multidex-report.*`，也没有 `multidex-evidence-package.zip`，
正文也没有一句「本附录没有附件」。读者顺着「附件在本文末」的惯例走，
会以为附录那一跑也有东西可查。**这是本轮查出的第二处缺说明**，与 §6.1
同类：附件的存在与否，正文没有交代。

### 6.4 这三处合起来说明什么

**正文里的会话是一次录制，附件是后来重新渲染的产物，两者不是同一次执行。**
证据是：所有**计数**完全一致（5 类 / 8 方法 / 23 call site / 21 call edge /
11 evidence / 1 resource —— 附件 `report.md` 的 Summary 表与正文逐项相同），
而**耗时**与**run id** 不同。同一份 APK 重跑，计数必然一致，耗时必然不同。

这本身不是错——但正文把两者写成同一次（「from the same analysis」、
「Every step below was run with the commands shown, in one workspace, and the
outputs quoted are the actual outputs of those commands」），读者据此去核
附件就会对不上。**这是 C4 这条候选真正要修的东西**：不是「三个包只覆盖两次
分析」这一句，而是**走查正文与自己的附件指向不同的运行**。

---

## 7. 第三个包该不该补

### 7.1 结论

**该补，但不是「再加一个包」，而是「把第 3 篇换成它自己那次分析的包」。**
本轮**不补**，只把文档改对；补的方案写在这里，等主会话的重测量落定后
另起一轮执行。

理由：现在真正让读者误判的不是「包少了一个」，而是**第 3 篇没有自己的
证据**——它的附件链接指向第 1 篇的文件，它的正文引用一个仓库里查不到的
run id。再加一个包（哪怕是 multi-DEX 附录的包）并不会修掉这两条，
反而会多出第四个包、第三次分析，让「几个包对应几次分析」更难说清。

### 7.2 补它需要什么

**需要一次新的分析**：`run_id` 是 `uuid4()` 随机生成的
（`src/dexatlas/core/runs.py:42-49`），且 `report.md` 印着它，所以
「一次新的分析」是绕不过去的。而 `dexatlas export` 取的是项目**当前发布的
run**（`src/dexatlas/cli/main.py:882`），因此必须让这次新分析成为该项目的
published run。

**关键约束**：`demo.apk` 的 `project_id` 恒为 `apk_80a8fe0e81204c9f`
（项目 id 是 APK 哈希前缀）。要在**不覆盖**第 1 篇那次运行的前提下得到
第 3 篇自己的包，必须用**独立的工作区**，而且这个工作区必须是**空的**——
`POST /analyze` 撞上一个已经分析过的同一 APK 时，**直接返回既有项目、不新建
run**（`src/dexatlas/api/app.py:379-385`）。这正是第 3 篇正文里那句
「the demo APK was already in this workspace, so this run answered `completed`
immediately」描述的机制，也正是它让正文的 run id 与附件的 run id 分了家。

```bash
# 1) 独立工作区（空的！同一个 APK 已分析过就不会新建 run）
export DEXATLAS_WORKSPACE=.scratch/api-ws

# 2) 起 API
uv run uvicorn dexatlas.api.app:app --port 8000

# 3) 上传并分析 demo.apk（返回 pending，轮询 /projects/{id} 直到 completed）
curl -s -X POST http://127.0.0.1:8000/analyze -F file=@examples/demo-app/demo.apk
curl -s http://127.0.0.1:8000/projects/apk_80a8fe0e81204c9f

# 4) 取一份 HTTP 渲染的 Markdown——正文 §3.4 引的就是它
curl -s "http://127.0.0.1:8000/projects/apk_80a8fe0e81204c9f/report?format=markdown" \
  -o .scratch/api-report.md

# 5) 打包：export 自己渲染三种格式，一次产出 md/json/html
uv run dexatlas export apk_80a8fe0e81204c9f \
  -o docs/case-studies/attachments/api-integration-evidence-package.zip \
  --workspace .scratch/api-ws

# 6) 从包里取出三份报告，作为第 3 篇**自己**的散装文件
mkdir -p .scratch/api-pkg
unzip -oq docs/case-studies/attachments/api-integration-evidence-package.zip \
  -d .scratch/api-pkg
for f in md json html; do
  cp ".scratch/api-pkg/reports/report.$f" \
     "docs/case-studies/attachments/api-integration-report.$f"
done
```

**为什么 HTML 要从包里取，而不是再 curl 一次**：API 的
`GET /projects/{id}/report` **只有 `json` 与 `markdown` 两种格式**
（`src/dexatlas/api/app.py:810` 的 `pattern="^(json|markdown)$"`），
HTML 只有 `dexatlas analyze --html`（`src/dexatlas/cli/main.py:331`）能写；
而 `dexatlas export` 自己就渲染三种格式
（`src/dexatlas/reports/evidence_package.py:100-103`）。从包里取，
散装的三份报告与包里的三份就**保证**是同一次分析的产物。

**要改哪些地方**（全部在 `docs/`）：

1. `docs/case-studies/api-integration.md` —— §3.2/§3.4 的 run id 换成新值；
   附件链接从 `demo-report.*` 换成 `api-integration-report.*`；
   「from the same analysis」那句删掉或改写。
2. `docs/case-studies/README.md` —— 附件说明句改成「每篇走查各有自己的报告
   与证据包」；对应关系段改成「三次分析、三个包」。
3. `docs/outreach/publish-review.md:128` 与
   `docs/outreach/cover-letter-templates.md:32-34` —— 附件清单。
4. `docs/reports/outreach-publish-checklist.md:99-110,178` —— 两条勾选项
   现在写着「两个包同源」，补完第三个包后要改成「三个包三个 run」。
5. 复核 `docs/case-studies/` 四份文档里所有引用的 sha256/耗时。

### 7.3 代价

| 项 | 代价 |
|---|---|
| 分析本身 | 秒级。附件里那次 `demo.apk` 分析是 **6.6 s**（`run_e112e71772d34a0e` 的 `started_at`→`finished_at` 实测 6.618 s）；`obfuscated.apk` 那次是 **6.0 s** |
| 导出 | 秒级 |
| 起 API | 一次 `uvicorn` 进程；`examples/api_client.py` 现成可用 |
| **真正的成本** | **文档**，不是算力：5 处文档要改、要复核哈希、跑 `scripts/check-doc-citations.py` 与 `pytest tests/test_docs.py -q` |
| 工程时间 | **约 1–2 小时**（其中分析+打包 < 5 分钟） |

**为什么不在本轮做**：主会话正在跑最终重测量。现在重生成附件会**新增**
`api-integration-report.*` 三个文件（`docs/case-studies/attachments/` 从 9 个
变 12 个），并**改动** `api-integration-evidence-package.zip` 的哈希
（第 1 篇的 `demo-report.*` 与 `demo-evidence-package.zip` 不动）；
哈希一变，与重测量的核对就打架。**等重测量落定后另起一轮**是最干净的顺序。

**顺带的次要缺口**（本轮不补）：multi-DEX 附录（`multidex.apk`，
`apk_a488e43e38c2b8e9`）在第 2 篇里被完整走查过，但**没有自己的报告与
证据包**。若要补，它是**第四个包、第四次分析**，成本与上同量级。

### 7.4 不补的话，对外该怎么写

**不能说**：
- 「三个独立分析」「三份独立证据」「三个案例各对应一次分析」——
  前两句与实测冲突，第三句会被读者用 §3 的 run id 当场推翻。
- 「三个客户案例」——`docs/outreach/cover-letter-templates.md:40` 已经明令
  不要这么写。

**该这么写**（推荐）：

> **三个案例走查、三份证据包、两次独立分析。**
> 第 1 篇（CLI 全链路）与第 3 篇（REST/MCP 集成）分析的是同一个
> `demo-app` 样本，因此共用一次分析 `run_e112e71772d34a0e`；
> 第 2 篇（混淆代码）来自另一次 `run_8d6735d410174df6`。

一句话版本（放在项目简介里）：

> Three walkthroughs, three evidence packages, **two** underlying analyses.

> ⚠️ **这段口径已经作废（2026-11-18）**：附件集换过一轮，现在是**四个证据包、
> 四次分析**，`run_id` 两两不同，对外改说「四个包、四次分析」。上面这段保留
> 在文里是为了说明「补包之前该怎么写」，**不要照抄**。现行口径见
> [case-studies-third-package.md](case-studies-third-package.md) 与
> [case-studies/README.md](../case-studies/README.md)。

---

## 8. 本轮改了什么

| 文件 | 改了什么 |
|---|---|
| `docs/case-studies/README.md` | 附件说明句改为「哪些文件属于哪篇走查」；对应关系段补上 run id 与「散装 JSON 与包内 JSON 的差异」提示，并指向本文 |
| `docs/case-studies/demo-app-walkthrough.md` | 抬头补 run id，写清「正文的 4.9 s 是录制那次、附件报告里的 6.6 s 是附件那次」；结论里「under five seconds」改为与附件一致 |
| `docs/case-studies/api-integration.md` | §3.4 附件说明改为如实陈述：附件来自 `run_e112e71772d34a0e`，正文引用的是 `run_6506002de5d8486a`，两者不是同一次；散装报告文件是第 1 篇的 |
| `docs/case-studies/obfuscated-app.md` | 抬头补 run id 与 5.1 s / 6.0 s 的出处；附件段点名 run id、补 JSON 哈希差异说明；**明说 multi-DEX 附录那一跑没有附件** |
| `docs/reports/case-studies-run-correspondence.md` | 本文（新增） |
| `docs/reports/README.md` | 索引行 |

**没有改**：三个 zip、六个散装报告文件，以及 `src/`、`tests/`、`scripts/`、
`CHANGELOG.md`、`README.md`、`README.zh-CN.md`、`docs/status.md`、
`docs/reports/phase1-execution-report.md`。

---

## 9. 本轮不能断言的事

诚实起见，以下几条**没有**被证明，不应当成结论用：

1. **`run_6506002de5d8486a` 到底是什么。** 它只存在于第 3 篇正文的两行里，
   仓库里没有任何附件、报告或数据库记录能佐证它。它很可能是当年录制
   HTTP 会话时那次真实分析的 run id（正文的 §3.2 说「the demo APK was
   already in this workspace, so this run answered `completed` immediately」，
   读起来就是「工作区里已有一条跑完的 run，API 直接返回它」），
   但**本轮无法验证**，所以本文只说「查不到」，不说「不存在」。
2. **两次渲染的 `project.created_at` 为什么不同。** 只能确认「同一次 run、
   两个工作区状态」（run id 与起止时间完全一致），至于两个工作区各自是怎么
   来的，本文不推断。
3. **正文的会话与附件的运行之间的时间关系。** 附件那次是
   `2026-11-15T20:46`；正文那次没有时间戳（只有耗时），所以只能说
   「不是同一次」，不能说「早一次」或「晚一次」。
4. **`docs/outreach/` 下的三份文档**（`publish-review.md`、
   `cover-letter-templates.md`、`project-brief.md`）本轮只做了检索，
   没有改。其中 `cover-letter-templates.md:40` 已经写着「don't present them
   as three independent analyses or three client cases」，方向正确；
   `publish-review.md:128` 把第 3 篇的附件写成 `demo-report.*` +
   `api-integration-evidence-package.zip`，与实测一致（那正是「借用第 1 篇
   文件」的现状），补包之后要一起改。

---

## 10. 复算

本文每个数字都能从仓库里复算，不依赖本文：

```bash
# 附件清单与哈希
sha256sum docs/case-studies/attachments/*

# 解包后逐文件哈希
for z in demo api-integration obfuscated; do
  unzip -qo -d .scratch/csc/$z docs/case-studies/attachments/$z-evidence-package.zip
done
find .scratch/csc -type f | sort | xargs sha256sum

# 报告里的身份字段
python - <<'PY'
import json
for d in ("demo", "api-integration", "obfuscated"):
    r = json.load(open(f".scratch/csc/{d}/reports/report.json"))
    print(d, r["project"]["id"], r["run"]["id"], r["run"]["started_at"], r["run"]["finished_at"])
PY

# run id 是随机的（所以同源只能来自同一条 run 记录）
grep -n "uuid4" src/dexatlas/core/runs.py

# export 取的是项目已发布的 run
grep -n "get_published_run" src/dexatlas/cli/main.py src/dexatlas/core/storage.py
```

临时目录 `.scratch/` 在 `.gitignore` 内，不入库。
