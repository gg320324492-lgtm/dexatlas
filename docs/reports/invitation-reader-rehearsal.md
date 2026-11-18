# M10 邀请函 —— 读者视角预演记录（只读）

> **本文件的性质：** 这是一次**只读预演**：照着邀请函与读者包给的命令，从 clone
> 走到打分的模板前，把每一步实际跑了一遍，记录「命令 / 实际输出 / 与材料是否对得上 /
> 耗时」，并标出会让读者卡住、被误读或觉得多余的地方。
>
> **它不是验收结论。** 预演由作者侧执行（拿得到仓库、能读源码），因此**不具备
> 独立性**；它的价值只有一处——**在把邀请发出去之前，先用一双眼睛把材料走一遍**。
> 40 个验收项在这里一条也没有被判「通过」，也没有被改过。
>
> **本文件不改任何既有文件**，只新增这一份。未触碰 `.github/`、README 徽章、
> `docs/status.md`，未跑 `scripts/refresh-report-figures.py`。

---

## 0. 预演基线与环境

| 项 | 值 |
|---|---|
| 预演日期 | 2026-11-18 |
| 验收对象 | `v1.0.0` 这个 tag 所指的提交 |
| `git rev-parse "v1.0.0^{commit}"` | `3e943b5b7870112f9df8994268482b30255d2e16` |
| `git rev-parse v1.0.0`（tag 对象） | `21f06eba7dd6669ebf041a0e4beea3479dd8c369` |
| `git cat-file -t v1.0.0` | `tag`（**附注 tag**） |
| 副本来源 | 本地克隆 `E:/Dexatlas` → `.scratch/reader-rehearsal/dexatlas`（**离线**；GitHub URL 未走网络，见 §8） |
| OS | Windows 11 Pro 10.0.26300 |
| Python / uv / JDK | 3.12.10 / 0.11.21 / 21.0.11（OpenJDK） |
| 后端 | jadx 1.5.2、apktool 2.11.1（`E:\Dexatlas\.scratch\backends`，经 `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` 指向）、androguard 4.1.4 |
| 其它 | gh 2.97.0、ffmpeg 4.2.11 |
| 走过的步数 | **34 步**（材料要求的 33 步 + 1 步用等价静态检查代替「双击打开 HTML」）；**跳过 1 步**（`fetch-fixtures.sh`，无网络）；**没做 1 步**（Docker 路线） |
| 计算耗时合计 | 材料路径上的命令约 45 秒；其余是阅读材料的时间 |

**副本与 tag 的纪律**：克隆后 `git tag -l` 拿到全部 8 个 tag，`git checkout v1.0.0`
进入 detached HEAD，`git status` 干净（`--porcelain` 无输出），`git rev-parse HEAD`
与邀请函 §2 应当填写的那一串逐字相同——这一条链路是通的。

---

## 1. 结论摘要

| | 数量 | 最要紧的一条 |
|---|---:|---|
| **卡住**（材料让你做的事做不到，或缺材料没给的东西） | **2** | F1 要实测退出码 1，但材料没给任何能产生退出码 1 的命令 |
| **误读**（材料可以有两种理解，而读者会读错那一种） | **7** | G3（★）：准备包与读者包对同一条命令的预期**互相矛盾**，本机还满足不了准备包那一版 |
| **多余**（不必要的动作，或同一件事说了两遍而两遍不一致） | **3** | G3 的预期在两份材料里各写一遍，且两遍打架 |
| 合计 | **12** | |

**40 项验收项的三类归属**：

| 归属 | 项数 | 是哪些 |
|---|---:|---|
| **能自己判** | **39** | A1–A7、B1–B6、C1–C6、D1–D5、E1–E5、F2–F6、G1、G2、G4、G5 |
| **必须问作者** | **1** | **G3**（★）——两份权威材料的预期不一致，且准备包那一版在本机不可满足 |
| **材料没给判据** | **0** | 40 项的判定标准都写到了「读者能照着判」的程度；问题出在**命令**与**预期值**，不在判据 |

> 两点必须一起读：① 39 项「能自己判」里有 **F1、F2、F3、F4** 四项虽然有判据，
> 却**没有可照抄的命令**（见 S-1、S-2）——读者若不去 README 里自己找，这四项只能
> 记「未验证」，而 F1 与 F5 是 ★ 阻断项。② 「必须问作者」的 G3 一项，其可问的内容
> 不是「工具对不对」，而是「**两份材料哪一份说了算**」。

---

## 2. 我实际走了多少步

每一步都记了命令、退出码、关键输出与耗时。下表是**材料路径**（读者包 §3.1–§3.8 +
§9.1）上的执行记录。

### 2.1 §3.1 取得固定副本（验收项 A1）—— 4 步

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料是否对得上 |
|---|---|---:|---|---:|---|
| 1 | `git clone <url>` | 0 | `Cloning into 'dexatlas'... done.`（本地源，0.47 s） | 0.5 s | ✓ |
| 2 | `git checkout v1.0.0` | 0 | `HEAD is now at 3e943b5 发布文本里的 passed 数改成落定值 1694` | <0.1 s | ✓ 附注 tag 可直接 checkout |
| 3 | `git status` | 0 | `HEAD detached at v1.0.0` / `nothing to commit, working tree clean` | <0.1 s | ✓ 干净 |
| 4 | `git rev-parse HEAD` | 0 | `3e943b5b7870112f9df8994268482b30255d2e16` | <0.1 s | ✓ 与 §2 占位符应填的那一串同形 |

### 2.2 §3.2 环境准备（验收项 A2、A3）—— 2 步（+1 步跳过）

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料是否对得上 |
|---|---|---:|---|---:|---|
| 5 | `uv sync --extra dev --extra analysis --extra mcp --extra demo`（本预演加 `--offline`，暖缓存） | 0 | 43 个包解析完成，`+ pytest==9.1.1` … | 3.3 s | ✓ 退出码 0；**冷缓存的 4 分 24 秒未复现**（无网络） |
| 6 | `uv run dexatlas backends`（未设环境变量） | 0 | 表：jadx `not installed` / apktool `not installed` / androguard `available 4.1.4` + `2 backend(s) unavailable…` | 1.6 s | ✓ 与「每个后端是 available 或 not installed」一致 |
| — | `bash scripts/fetch-fixtures.sh` | **未跑** | — | — | **跳过**：本预演不联网。原因与影响见 §8 |

按 install.md 设 `DEXATLAS_JADX_PATH`（指向 `bin\jadx.bat`）与 `DEXATLAS_APKTOOL_JAR`
之后，`uv run dexatlas backends` 输出三个后端全 `available`（jadx 1.5.2 / apktool
2.11.1 / androguard 4.1.4）——**install.md 对 Windows 的 `.bat` 提示是必要的，且写对了**。

### 2.3 §3.3–§3.4 首次分析与检索（验收项 A4、B2–B5）—— 6 步

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料是否对得上 |
|---|---|---:|---|---:|---|
| 7 | `uv run dexatlas analyze examples/demo-app/demo.apk` | 0 | `✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (4.0s)` | 5.0 s | ✓ **与预期逐字一致**（id、五个计数全对） |
| 8 | `uv run dexatlas manifest apk_80a8fe0e81204c9f` | 0 | `com.example.demo` / `version 1.0 (1)` / `sdk min 24 / target 34` / `permissions 1` / `components 3` + MainActivity、SyncService 均 `no permission guard` | 1.3 s | ✓ |
| 9 | `uv run dexatlas search … "Crypto"` | 0 | 7 行：`class` 1 + `method` 4 + `string` 2（`Crypto.java`、`Lcom/example/demo/Crypto;`） | 1.3 s | ✓ |
| 10 | `uv run dexatlas search … "sk_live"` | 0 | `string │ sk_live_2f8a91c4e7b3 │ sk_live_2f8a91c4e7b3` | 1.3 s | ✓ `Kind=string` 的解释够用 |
| 11 | `uv run dexatlas source … com.example.demo.MainActivity` | 0 | `source kind: java` + `jadx:sources/com/example/demo/MainActivity.java` | 1.3 s | ✓ |
| 12 | `uv run dexatlas xrefs … "…MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;"` | 0 | `1 call site(s), 1 call edge(s)` / `classes.dex@34` | 1.3 s | ✓ |

### 2.4 §3.5–§3.6 报告、证据包与校验（验收项 A5、C5–C6、D1–D5、G5）—— 8 步

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料是否对得上 |
|---|---|---:|---|---:|---|
| 13 | `uv run dexatlas analyze … -o report.md --json report.json --html report.html` | 0 | 三行 `Markdown report → report.md` / `JSON report → report.json` / `HTML report → report.html` | 5.0 s | ✓ |
| 14 | `uv run dexatlas export apk_80a8fe0e81204c9f -o evidence.zip` | 0 | `✓ evidence package → evidence.zip (4 files: 3 reports + 1 manifest, apk 80a8fe0e81204c9f)` | 1.4 s | ✓ 「4 files」的口径解释准确 |
| 15 | `verify_package` + `verify_citations` | 0 | `{'citations_total': 14, 'citations_resolved': True, 'citations_unresolved': [], 'apk_sha256': '80a8fe0e…'}` | 1.0 s | ✓ `citations_resolved=True`、`unresolved` 空 |
| 16 | `python -m zipfile -e evidence.zip evidence` | 0 | 4 个条目：`manifest.json` + `reports/{report.md,report.json,report.html}` | 0.3 s | ✓ 与 §3.6 的「4 个条目」一致 |
| 17 | 打开 `evidence/manifest.json` | — | `not_included` 三条（APK / full_sources / unrelated_strings）+ 3 个文件的 sha256 与字节数 | — | ✓ |
| 18 | `certutil -hashfile` 抽查 2 个文件 | 0 | `report.md` = `21ab945c…`、`report.json` = `02185b48…`，与清单一致 | 0.2 s | ✓ |
| 19 | `grep` 核对 `report.html` 的外部引用 | — | 无 `<script>`、无 `<link`、无 `src=`/`href=`/`http(s)://`/字体/`@import` | 0.1 s | ✓（**代替「断网双击打开」**这一动作，判据等价） |
| 20 | 三格式抽查 3 个数字 | — | `classes=5`、`methods=8`、`call_edges=21`、`call_sites=23`、`resource_strings=1` 在 md / json / html 三处一致；project id 一致 | 0.2 s | ✓ |

### 2.5 §3.8 契约、回归集与故障恢复（验收项 E、F、G 组）—— 13 步

| # | 命令 | 退出码 | 实际输出（摘要） | 耗时 | 与材料是否对得上 |
|---|---|---:|---|---:|---|
| 21 | 退出码 0 | 0 | `analyze` | — | ✓ |
| 22 | 退出码 2：`uv run dexatlas analyze README.md` | **2** | `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives` | 1.2 s | ✓ 与 §9.1 G1 逐字一致 |
| 23 | 退出码 1（**材料未给命令**，自行试出） | **1** | `uv run dexatlas search apk_80a8fe0e81204c9f zzz_no_such_term_xyz` → `No matches for 'zzz_no_such_term_xyz'.` | 1.3 s | ⚠ 见 **S-1** |
| 24 | `uv run dexatlas projects`（G1 之后的「工作区无半成品」检查） | 0 | `Projects (1)` —— `apk_80a8fe0e81204c9f / demo.apk / completed / 5 / 8` | 1.2 s | ⚠ 与 §9.1 G1 的预期**不一致**，见 **M-5** |
| 25 | `DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR= uv run dexatlas analyze …`（G2 降级） | 0 | `4 classes, 8 methods, 23 call sites, 21 call edges, 0 resource strings` + `! apktool is not installed or not on PATH…` + `! jadx is not installed or not on PATH…` | 3.0 s | ✓ 退出码 0、`not_installed` 两条、计数 4/0 —— 与 §3.2 的「A6 预告」一致 |
| 26 | `DEXATLAS_TOOL_TIMEOUT_SECONDS=1 uv run dexatlas analyze …`（G3 超时） | 0 | `! jadx exceeded its 1s timeout and was terminated`（**只有 jadx 超时**），计数与正常运行相同 | 4.4 s | ⚠ 与准备包 G3 不一致，见 **M-1** |
| 27 | 同一超时命令加 `--json report_timeout.json`，查报告字段 | 0 | `errors[]` 1 条 `code=timeout`；**`index_complete=True`、`index_gaps=[]`**；`evidence` **12** 条 | 4.5 s | ⚠ 三处与材料不一致，见 **M-1 / M-2** |
| 28 | `uv run dexatlas analyze …`（G4 第一次） | 0 | `apk_80a8fe0e81204c9f` | 4.1 s | ✓ |
| 29 | `uv run dexatlas analyze …`（G4 第二次） | 0 | 同一个 project id | 4.1 s | ✓ |
| 30 | `uv run dexatlas projects`（G4 之后） | 0 | `Projects (1)` | 1.2 s | ✓ 幂等 |
| 31 | `uv run --no-sync pytest tests/test_public_contracts.py -q` | 0 | `31 passed in 6.30s` | 8.1 s | ✓ 无 skip、无 fail |
| 32 | `uv run --no-sync python scripts/verify-public-contracts.py` | 0 | `48/48 checks passed` + `the public contracts hold` | 17.8 s | ✓ 逐项 PASS |
| 33 | 读 `service-regression-set.md` / `m6-level1-scripted.md` / `m6-level2-retest4.md`（E 组） | — | 冻结 20 题 + 完整 92 题**同报**；层级 1「预算耗尽 = 替身脚本步数耗尽」「答错 = 断言形态」写明；retest4 逐轮 **15/20、16/20、18/20**，合计 **49/60 = 81.7%**，未达 ≥54/60 | — | ✓ E1–E5 的判据都能在原文里找到 |

### 2.6 §9.1 与 §3.7 补做—— 1 步 + 阅读

| # | 动作 | 结果 |
|---|---|---|
| 34 | 通读 `docs/case-studies/demo-app-walkthrough.md` | 章节结构齐全：Background / Scope / Procedure / Key evidence / **Conclusions** / **Limits and boundaries** / **Recommended next steps** / Exporting —— B6 的「结论、限制、下一步」都有原文可复述 ✓ |

**另做的 12 步交叉核查**（不是材料要求的，是为了把上面几条查实）：
`git cat-file -t` / `for-each-ref` 看 tag 形态与日期；把 tag 改成**轻量**再改回附注，
验证两种形态下 `rev-parse` 的差别；把 `evidence.zip` 复制到别的目录复验（C6 迁移）；
直接从 `.dexatlas/dexatlas.db` 复算 5/8/23/21/1 与 21 条边（C4）；读
`src/dexatlas/core/models.py:94`（`index_gaps` 的定义）与
`src/dexatlas/core/storage.py:1303`（`save_evidence` 先删后插）；
跑 `scripts/m10_selfcheck.py` 两遍（两种环境）；核对材料里的 `file:line` 引用；
跑 `scripts/check-doc-citations.py`（`unresolved: 0`、`drifted: 0`、`Every citation
still says what it says`）。

**没有跑的东西**（按任务约束与现实条件）：完整测试套件（约十几分钟）、
`fetch-fixtures.sh`（无网络）、Docker 路线（构建 2–20 分钟且需网络）、macOS。

---

## 3. 卡住（2 条）

### S-1 【验收项 F1，★ 阻断项】退出码 1 没有一条可照抄的命令

**材料说：** 读者包 §3.8（F1）：「CLI 退出码：0 成功、1 空答案、2 请求错误、3 分析
失败、4 重载歧义、5 截断、6 跑完但没有可用的代码索引……**至少实测 0/1/2 各一次**」。
准备包 §2.6 F1 同样：「至少实测 0/1/2 各一次，并核对文档语义」。

**实际：** 材料只给了 0（`analyze`）和 2（G1 的坏输入）两条现成命令，**退出码 1
（空答案）一条都没有**。我自己试了出来（`search` 一个不存在的词 → 1；`source` 一个
不存在的类 → 1；`xrefs` 一个不存在的方法 → 1），但这正是读者须知第 4 条禁止的
情形：「**不要让作者代劳**……凡是靠作者口头补充才走通的步骤，相关验收项判不通过」。
如果读者按材料的字面要求去找作者问「退出码 1 该怎么造」，F1 只能判不通过——而
F1 是 ★ 阻断项，一项不通过，M10 即不通过。

**建议（很小）：** 在读者包 §9.1 或 §3.8 补一条现成命令，例如
`uv run dexatlas search apk_80a8fe0e81204c9f __no_such_term__` → 退出码 1、
`No matches for '__no_such_term__'.`。

### S-2 【验收项 F2 / F3 / F4】没有可照抄的命令，读者得自己去 README 找

**材料说：** 读者包 §3.8 标题是「契约与回归集抽查（验收项 E、F 组，**可选但建议**）」，
其中只给了 F5、F6 两条命令；F2（REST 抽查 3 个端点）、F3（MCP 工具清单 11 个与
只读注解）、F4（报告 schema 的 10 个顶层字段）**没有任何命令**。§9.2 也只覆盖
契约活检脚本。

**实际：** 这三项的判据都在 `docs/architecture/public-contracts.md` 里，读者自己能
查；但「怎么把 REST 服务与 MCP server 跑起来」在 M10 材料里一句都没有。答案在
README 里（`uv run uvicorn dexatlas.api.app:app --reload` 与 `uv run dexatlas-mcp`），
而**读者包没有指这条路**。按读者须知「作者不补步骤」的口径，读者若在 M10 材料里
找不到命令、也没人去问，就会把 F2–F4 记成「未验证」——这不是作者的错，但会白白
损失三项。

**建议：** 读者包 §3.8 或 §9.2 补三行：起 REST（附端口与一个可直接 curl 的端点）、
起 MCP（stdio）、跑一次 `dexatlas analyze --json` 查报告顶层字段。

---

## 4. 误读（7 条）

### M-1 【G3，★ 阻断项】三份材料对同一条命令的预期互相矛盾，而准备包那一版在本机满足不了

**材料说（三处）：**

| 出处 | 原文要点 |
|---|---|
| 准备包 §2.7 **G3**（**判据权威**——读者包 §0 明写「判定以准备包为准」） | 「设置极短超时后**三后端记录 `timeout`**，报告仍产出；同时核对 M8-4 的退出码语义——三个后端全部失败时退出码应为 **6**……记录实际退出码。」★ |
| 读者包 §9.1 G3 | 「报告 JSON 里 `errors[]` 每条的 `code` 是 `timeout`；`summary.index_complete` 是 **false**，`summary.index_gaps` 里有一条 `androguard` 的 `timeout`。」 |
| 读者包 §9.1 G3 末段 | 「**若 androguard 在你的机器上 1 秒内就跑完了**，`errors[]` 会只有两条、`index_complete` 是 `true`——**这同样是正确行为**……」 |

**实际（本机：Windows 11 / jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4）：**
`DEXATLAS_TOOL_TIMEOUT_SECONDS=1` 下**只有 jadx 超时**（1 条 `timeout`），androguard
与 apktool 都在 1 秒内完成；退出码 0；计数与正常运行完全相同。报告 JSON 里：

```text
errors:          [{"tool": "jadx", "code": "timeout", …}]     ← 1 条，不是 3 条
index_complete:  true                                          ← 材料写 false
index_gaps:      []                                            ← 材料写「一条 androguard 的 timeout」
```

**为什么读者会读错：** 准备包的 G3 是判据权威，它要求「**三后端**记录 timeout」。
本机只有 1 条。读者照准备包判 → **G3 不通过**（★ 阻断项）→ M10 直接不通过；
读者照读者包判 → 通过。两份材料给出相反结论，而材料自己规定了「以准备包为准」。
读者手上唯一能做的正确动作是**问作者哪一份说了算**——这就是本报告里唯一一项
「必须问作者」。

**顺带厘清一个事实**（供修材料时用）：`index_gaps` 只统计**索引后端**（androguard）
或分析级失败（`src/dexatlas/core/models.py:94`）。jadx 超时不构成 gap，所以
「index_complete=false、index_gaps 里有 androguard」**只在 androguard 自己超时时
才成立**；读者包为 `errors[]` 的条数写了免责，却没为 `index_complete` / `index_gaps`
写。准备包 G3 里「三个后端全部失败 → 退出码 6」这一条，用超时变量在 demo APK 上
**根本触发不了**（androguard 总是先交出类表）——读者包 §9.1 已经说清楚了，但准备包
的判定标准里没有这个说明，读者只能把它当成本轮必须实测的判据。

**建议：** ① 准备包 §2.7 G3 的标准改成「**至少一条后端记 `timeout` 且报告照常产出**
（条数与本机速度相关）」；② 把「退出码 6」标注为「**不由超时变量触发**，由
`scripts/verify-public-contracts.py` 的 `an analysis with no index exits 6` 一条覆盖，
本轮读者只需核对语义」；③ 读者包 §9.1 末段补一句「`index_complete=false` 仅当
androguard 超时」。

### M-2 【G3 / C1，均为 ★】超时运行的报告里同时挂着两条互斥的 `verified` 证据

**实际（一次干净的复核：全新工作区、只跑一次超时分析）：**

```text
evidence count: 12          ← 正常运行是 11 条
evidence_by_level: {'verified': 12}
E-0007 │ jadx did not complete: jadx exceeded its 1s timeout and was terminated │ jadx:error/timeout
E-0008 │ jadx produced real Java for 7 of 8 methods in 5 of 5 classes           │ jadx:sources
```

同一份报告的 `summary.decompilation` 写 `methods_decompiled: 7 / methods_total: 8 /
methods_jadx_failed: []`，`errors[]` 里只有一条 `timeout`。也就是说：**同一份报告
里，E-0007 说 jadx 没有完成，E-0008 说 jadx 为 5 个类产出了 7 个方法的真实 Java，
两条都是 `verified`。**

这不是跨次运行的残留——我用一个**全新工作区只跑一次**复现了同样的 12 条；降级运行
（清空两个后端环境变量）则是 9 条（少了 apktool/androguard 侧的声明类证据）。

**为什么读者会读错：** C1（★）要求「任选 3 条 evidence 记录，逐条写出工具、版本、
locator 和 level；**字段不得为空或臆造**」。读者抽到 E-0007 与 E-0008 时会拿到两条
关于同一个后端、字面互相打架的 `verified` 陈述；C4 要求「报告中的计数与证据记录
一致」——但证据条数会随后端配置变化（干净 11 / 降级 9 / 超时 12），**材料没有给
任何一条基线**，读者无从判断 12 是不是「多了」。这两条都会把读者推向「证据链断了」
的结论。

**建议：** 读者包 §9.1 G3 补一句预期（「超时运行的报告里会多出一条 `verified` 的
「后端未完成」记录，且 `evidence` 条数与正常运行不同，以报告自身为准」）；工具侧
则应考虑让「后端未完成」这条记录不要与 `decompilation` 的统计并列在同一个
`verified` 层级上。

### M-3 【C1–C6，其中 5 项是 ★ 阻断项】C 组被放在「源码评审记录」一节，但材料把它派给首次读者

**材料说：** 邀请函 §四第 4 步要求读者「任选 3 条 evidence 记录核对工具、版本、
locator、level 四字段……这是验收项 **C3**（★ 阻断项）的判定依据」；读者包 §3.4 标题
就是「检索、证据与 locator 解析（验收项 B2–B5、**C1–C3**）」，§3.6 是「证据包导出
与校验（验收项 **C5–C6**、D3–D5、G5）」——**C 组是首次读者路径上的一等公民**。

**但记录模板** `docs/reports/m10-review-record-template.md` 里：C1–C6 的结论表放在
**§5「源码评审记录（C/E/F/G 组）」** 下的 §5.2；§2「首次读者会话记录」的表格只有
A1–A7、B1–B6、D1–D5，**一行 C 都没有**。

**为什么读者会读错：** 一位只承担「首次读者」角色的外部评审者，打开模板会看到
「§5 源码评审记录」，会合理地认为这一节不是自己的活，把 C1–C6 留空——而 C1、C2、
C3、C5、C6 **五个都是 ★ 阻断项**，留空即「未验证」，M10 就此卡住，而且卡得毫无
痕迹：表格里没有一行写着「读者未填」。

**建议（改一处即可）：** 把记录模板 §5 拆成「§5 源码评审记录（M5–M9 里程碑）」与
「§6 验收项结论（C/E/F/G 组）」，或在 §5 标题里加一句「**C 组由首次读者/客户视角
角色填写**」。

### M-4 【D2 / B6】案例里「打包的 report.json 与散落的 report.json 逐字节相同」在 Windows 上不成立

**材料说：** `docs/case-studies/demo-app-walkthrough.md` §8：「the packaged
`report.json` and the loose `report.json` are **byte-for-byte identical**
(sha256 `921d3d3e…`)」，紧接着又解释「散落的那份带本机的 CRLF 行尾，只有在产出它的
机器上哈希才会相同」。

**实际（同一台机器上三份文件）：**

| 文件 | 行尾 | sha256 |
|---|---|---|
| 散落 `report.json`（`analyze --json` 写的） | 364 个 CRLF / 0 个纯 LF | `8c9a8003…` |
| 证据包内 `reports/report.json` | 0 CRLF / 364 纯 LF | `02185b48…` |
| 仓库附件 `docs/case-studies/attachments/demo-report.json` | 0 CRLF / 364 纯 LF | `921d3d3e…` ✓ 与案例所写一致 |

**为什么读者会读错：** 读者读到的两句是互相打架的——「逐字节相同」与「行尾不同」。
读者拿自己这次跑出来的散落 `report.json` 去对案例里的 `921d3d3e…`，必然对不上；
而材料给的那句解释只覆盖了 CRLF 这一半，另一半（**每次运行的 `run_id`、
`generated_at`、`duration_seconds` 本来就不同**，所以两次运行的报告本来就不可能
逐字节相同）没有覆盖。读者会记下一条假卡点，甚至怀疑「材料里的哈希是编的」。

**建议：** 案例 §8 改成「仓库里附的那一份，其哈希与本案例正文引用的数字一致；
**你自己这次运行产出的报告哈希不会与之相同**——运行元数据与行尾都不同，这不是
缺陷」。

### M-5 【G1】`projects` 的预期输出与材料规定的执行顺序冲突

**材料说：** 读者包 §9.1 G1 第二条命令 `uv run dexatlas projects`，预期
「`No projects yet. Run \`dexatlas analyze <apk>\`.`——列表是空的」，用来确认
「工作区里没有留下半成品项目」。

**实际：** 按材料顺序走（§3.3 先 analyze 过 demo.apk），再跑这条命令，输出是
`Projects (1)` 的表格。**那条预期输出不可能出现。** 意图是对的——坏输入确实没有
留下半成品项目（列表里只有 `apk_80a8fe0e81204c9f / demo.apk`，没有 README.md
对应的项目）——但读者按字面核对会得到一次「预期与实际不符」，而读者须知第 3 条
要求「预期输出和实际输出不一致时……把差异写成卡点」。**材料会逼读者报一个假缺陷。**

**建议：** G1 的第二条改成「在坏输入**前后各跑一次** `projects`，条数不变且没有
为 `README.md` 新增的项目」，或加一句「若此前已按 §3.3 分析过，工作区本来就有
1 个项目」。

### M-6 【邀请函 §一】「v1.0.0 发版于 2026-11-17」与 tag / 提交的日期不一致

**材料说：** 邀请函 §一：「现邀请您对已发布的 v1.0.0 做独立验收：**v1.0.0 发版于
2026-11-17**，`git tag -l` 里就是它——发出本函前，发起人会把 tag 重打到第二节
钉定的那棵树上」。

**实际：** 当前 tag 对象与它指向的提交都是 **2026-11-18 20:33:34 +0800**
（`git for-each-ref refs/tags/v1.0.0` 与 `git log -1 "v1.0.0^{commit}"`）；发信前
还会再重打一次，日期只会更晚。

**为什么读者会读错：** 「发版日期」与「tag 对象日期」是两件事。项目自己知道这一点
——就绪记录 §4 第 5 行已经写了「`docs/status.md:3` 写「v1.0.0（tag 2026-11-17）」，
而当前这个 tag 对象是 2026-11-18 重打的｜**发版日期仍是 2026-11-17**；tag 对象会
在发信前再重打一次」——但这条说明**只在就绪记录里**，邀请函正文没有。读者去核对
「发版于 2026-11-17」时看到的是 2026-11-18。

**建议：** 邀请函 §一改成「**发版日期 2026-11-17**（tag 对象会在发信前重打，其对象
日期与提交日期会晚于此）」。

### M-7 【F1 / F5，★】§3.8 标注「可选但建议」，与「★ 阻断项，缺一即 M10 不通过」冲突

**材料说：** 读者包 §3.8 标题：「第 8 步：契约与回归集抽查（验收项 E、F 组，
**可选但建议**）」；而准备包 §2.8：「**阻断项（★）共 19 项**：A2、A4、A6、B1、C1、
C2、C3、C5、C6、D1、D2、D3、E2、E3、F1、F5、G2、G3、G5」；读者须知第 5 条：
「阻断项一票否决。19 个标 ★ 的验收项任何一个不通过，M10 即不通过」。

**实际：** F1 与 F5 都在那 19 项里。一个按字面读「这一步可选」的读者会跳过 §3.8，
于是 F1、F5 直接是「未验证」——两项都是 ★ 阻断项，M10 就此无法关闭，而读者**没有
留下任何痕迹**（他自己以为这步是可选的）。

**建议：** 把 §3.8 的标题改成「第 8 步：契约与回归集抽查（验收项 E、F 组——**F1 与
F5 是 ★ 阻断项，不可跳过**）」；「可选」二字留给真正可跳的部分（如 Docker 路线）。

---

## 5. 多余（3 条）

### X-1 G3 的预期在两份材料里各写一遍，而且两遍打架

准备包 §2.7 G3 与读者包 §9.1 G3 都在写「同一条命令的预期输出」，两份都用了
「实测」这个词、都给出精确的 JSON 字段值，但结论相反（见 M-1）。读者包 §0 自己
规定了冲突时以准备包为准——所以读者包那一份要么该删，要么该改成不与准备包冲突的
说法。**同一件事说了两遍而两遍不一致**，是本次预演里最容易造成误判的一处。

### X-2 邀请函 §三 与 读者包 §2 各有一份「你需要准备什么」表；独立性守则也各写一遍

邀请函 §三的表（OS / Python / uv / JDK / Docker / gh / 网络 / 磁盘 / 时间）与读者包
§2 的表逐行重复，连「1.5–2 分钟是预算档位，不是实测值」这句解释都复述了两遍；
独立性要求在邀请函 §八与读者包 §1 各有一份，内容重叠。**两次都不一致**，所以不算
缺陷，但对读者是重复劳动——邀请函 §四第 1 步已经声明「完整分步命令以读者验收包 §3
为准」，同理，这两张表和这份守则也可以只保留一份，另一处给链接。

### X-3 作者自查脚本 `scripts/m10_selfcheck.py`：读者不必跑；跑了还可能多一个假卡点

读者包 §7 把它介绍给读者（「它可以帮你在正式验收前发现文档、徽章、契约清单层面
的明显缺口，但**不替代**你的任何一项判定」）。实测：

| 环境 | 结果 | 退出码 |
|---|---|---:|
| 完整 sync 的副本（按 §3.2 走） | 自动化判定：**通过 43，失败 0**，需人工 40 | 0 |
| 没有 dev extras 的环境（我先在另一个工作树里撞到） | 自动化判定：通过 38，**失败 5**（`G.ruff`/`G.ruff-format`/`G.mypy`/`G.vulture`/`G.pytest` —— 「venv 中未找到该入口」），需人工 40 | **1** |

同一棵树、同一个 commit，差别只在环境。走 Docker 路线的读者、或者只 `uv sync`
了部分 extras 的读者，会看到 5 条与材料无关的失败和退出码 1。

**建议：** 读者包 §7 补一句「**在按 §3.2 完整 sync 的环境里跑**；别的环境下它的
5 条门禁检查会因缺工具而失败，那是环境问题，不是材料问题」；或者干脆把它标成
「作者侧自查，读者不需要跑」。

---

## 6. 40 项验收项的三类归属

| 组 | 项 | 能自己判 | 必须问作者 | 没判据 | 备注 |
|---|---|:-:|:-:|:-:|---|
| A 安装与首次运行 | A1–A7 | 7 | 0 | 0 | A1/A2/A3/A4/A5/A6 实测通过；A7 由读者自己填 |
| B 完整案例 | B1–B6 | 6 | 0 | 0 | §3.4 的每一步都照抄得上、退出码与预期一致 |
| C 证据核查 | C1–C6 | 6 | 0 | 0 | C1 受 M-3 影响（模板位置）；C1/C4 受 M-2 影响 |
| D 离线阅读 | D1–D5 | 5 | 0 | 0 | D5 的样本不足以触发（demo 样本里没有类 HTML 的字符串） |
| E 服务回归集 | E1–E5 | 5 | 0 | 0 | 49/60=81.7%、逐轮 15/16/18、92 题与 20 题同报，材料里都能核到 |
| F 公共契约 | F1–F6 | 6 | 0 | 0 | F1/F2/F3/F4 有判据无命令（S-1/S-2） |
| G 故障恢复 | G1–G5 | 4 | 0 | 0 | **G3 必须问作者**；G1 的 `projects` 预期与顺序冲突（M-5） |
| **合计** | 40 | **39** | **1（G3）** | **0** | ★ 阻断项 19 个全在其中 |

**两点补充：**

1. **「能自己判」不等于「照材料就能判」。** F1、F2、F3、F4 的判据都在，但命令不在
   M10 材料里（要自己去 README 找）；读者须知第 4 条禁止作者补步骤，所以严格按
   材料走的人，这四项会落进「未验证」。这是 **S-1 / S-2** 的实际后果。
2. **D5 是「能自己判但样本不足」。** demo 样本里没有类 HTML 的字符串
   （`wide-app` 有一个 `"<payload>"`，但 M10 材料没有派它），所以 D5 只能判
   「在 demo 样本上平凡成立」。「异常文本只作为文本显示」这半句，读者**无法用材料
   给的样本证伪**。

---

## 7. 验收 commit 的 hash：读者该怎么取、取不到怎么办

### 7.1 填进邀请函 §2 的，是哪一串

```bash
git rev-parse "v1.0.0^{commit}"      # ← 填进 §2 的就是这一串（40 位）
git rev-parse v1.0.0                 # ← 这是 tag 对象自己的 hash，不是它
git cat-file -t v1.0.0               # ← 应该是 tag（附注 tag）
```

邀请函 §2 与读者工具包 §0 都写明了「必须带 `^{commit}`」，读者工具包还给出了逐字
比对的方法。**这一处材料是清楚的，我实测通过。**

### 7.2 发起人什么时候取

**在把 tag 重打并推上 origin 之后、发出邀请函之前**——发送前清单组二已经把这个
顺序排好了：

```bash
git tag -f -a v1.0.0 <材料定稿的提交> -m "v1.0.0 — 材料定稿"
git push origin v1.0.0 --force
git rev-parse "v1.0.0^{commit}"      # 重新取要填的那一串
```

取到的这一串要**同时**写进两处：邀请函 §2 的占位符（`commit 【待填：…】`）与验收
记录模板 §1 的「commit hash」栏。发送前清单已经写了「填完不要再改 tag」。

**一个已经写对、值得保住的地方：** 清单用的是 `git tag -f -a`（**附注** tag）。这
不是随手写的——若用 `git tag -f v1.0.0 <commit>`（轻量 tag），则
`git rev-parse v1.0.0` 会**等于** `^{commit}` 的输出，邀请函里「`git rev-parse
v1.0.0` 返回的是 tag 对象自身的 hash，与本函这一串**永不相等**」这句话就不成立了，
读者反而会以为材料被改过。我把这两种形态都实测了一遍：

```text
附注 tag： git rev-parse v1.0.0         = 21f06eba…
           git rev-parse v1.0.0^{commit}= 3e943b5b…     ← 不相等 ✓
轻量 tag： git rev-parse v1.0.0         = 3e943b5b…
           git rev-parse v1.0.0^{commit}= 3e943b5b…     ← 相等 ✗
```

**建议：** 发送前清单组二补一句「重打后必须再跑一次 `git cat-file -t v1.0.0`，看到
`tag` 才是附注 tag；看到 `commit` 说明打成了轻量 tag，要用 `git tag -f -a` 重来」；
邀请函 §2 给读者加一句诊断语——「若你核出的 `git rev-parse v1.0.0` 与本函那一串
**相等**，那说明这个 tag 是轻量 tag，属于 tag 形态问题，先联系发起人确认，不要
据此认定材料被改过」。

### 7.3 读者什么时候取、怎么取

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
git checkout v1.0.0
git rev-parse HEAD            # 与邀请函 §2 的 40 位逐字比对
```

读者拿到的副本默认带全部 tag（我实测 8 个 tag 都在）。§2 的那一串是**提交**的
hash，`git rev-parse HEAD` 与 `git rev-parse "v1.0.0^{commit}"` 等价，两条都行。

### 7.4 取不到怎么办（三级，材料只写了两级半）

| 情形 | 读者该做什么 | 材料是否给了 |
|---|---|---|
| clone 后 `git tag -l` 里**没有** v1.0.0 | 先 `git fetch --tags` 再试（浅克隆 `--depth 1` / `--single-branch` 会漏 tag）；仍没有 → 停下，联系发起人，**不要用 `main` 顶替** | **没给**（邀请函 §2 只说「联系发起人」；没提浅克隆这一种最常见的原因） |
| `git checkout v1.0.0` **取不到** | 停下，联系发起人 | ✓ 邀请函 §2 |
| 核出来的 hash 与函里**不一致** | 立刻停止并联系发起人，不要就地开始验收 | ✓ 邀请函 §2（并说明「这说明材料在发信之后被改动过」） |
| 核出来的 hash **一致** | 正常开始，全程只验这一个提交，不切分支、不拉新提交 | ✓ 邀请函 §2 |

**建议：** 在邀请函 §2 或读者包 §3.1 补一行「`git clone --depth 1` 不会带上 tag；
请用不带 `--depth` 的克隆，或在 clone 之后跑一次 `git fetch --tags`」。

---

## 8. 这次预演跳过了什么、为什么

| 跳过的 | 原因 | 后果 |
|---|---|---|
| `bash scripts/fetch-fixtures.sh` | 本预演**不联网** | 集成样本未取；「不抓样本会 skip 27 个集成用例」这条**未复现**（只静态确认了脚本把样本落到 `fixtures/apk/`，而仓库里只跟踪 `fixtures/apk/SOURCES.md`、两个 APK 不在仓库里 ✓ 与项目硬规则 7 一致） |
| 完整测试套件（约十几分钟） | 任务约束 | 只跑了材料点名的 `tests/test_public_contracts.py`（31 passed）与 `scripts/verify-public-contracts.py`（48/48）；**报告里的测试总数、覆盖率、指纹一概没有复现**，也没有碰 `refresh-report-figures.py` |
| Docker 路线（构建 2–20 分钟） | 需网络 | 路线 B 未验证；本预演全部走路线 A |
| macOS | 本机是 Windows | 路线 A 的 Windows 一侧有实测记录 |
| 「断网后双击打开 report.html」 | 无 GUI 浏览器 | 用 `grep` 核对「无 `<script>`、无外部 CSS/JS/字体请求」替代——判据等价 |
| 邀请函抬头三项 / 落款签名 | 只有发起人能填 | 预演时邀请函里那 4 处仍是空的，符合预期 |

**另外两件本次没做、但发出邀请前值得看一眼的事：**
`docs/reports/README.md` 的索引里没有收录本文件（本预演不改既有文件），索引由谁
补请发起人定；`scripts/check-doc-citations.py` 在本预演结束时是
`unresolved: 0 / drifted: 0`，材料里的 `file:line` 引用都还指着它们说的东西。

---

## 9. 发出邀请前必须补的三件事

1. **统一 G3 的判定标准，并把不可复现的那半句标出来。** 准备包 §2.7 G3 是判据
   权威，现在它要求「三后端记录 timeout」，本机做不到；读者包 §9.1 又说「两条也
   是正确行为」——读者无从裁定。请把准备包 G3 改成「至少一条后端记 `timeout` 且
   报告照常产出（条数随本机速度变化）」，把「三个后端全部失败 → 退出码 6」标注
   为「不由超时变量触发，由 `scripts/verify-public-contracts.py` 覆盖」，并把读者包
   §9.1 里「`index_complete` 是 false、`index_gaps` 里有一条 androguard 的 timeout」
   改成「仅当 androguard 自身超时」。
2. **把 C1–C6 从记录模板的「源码评审记录」一节里挪出来，或给那一节加一句
   「C 组由首次读者/客户视角角色填」。** 这 5 项是 ★ 阻断项，留空就是
   「未验证」，M10 关不掉，而表里看不出是漏填。
3. **补三条可照抄的命令**：退出码 1（空答案）、起 REST 服务后的一个端点、起 MCP
   后的工具清单。命令放进读者包 §9.1 或 §9.2；F1/F2/F3 是 ★ 与评分输入项，
   读者须知第 4 条又禁止作者口头补步骤。

## 10. 可以不补的

- 邀请函 §三 与 读者包 §2 两份「准备什么」表、两份独立性守则的重复（两遍一致，
  不影响判定）。
- 作者自查脚本 `scripts/m10_selfcheck.py` 在非标准环境下的 5 条假失败——读者按 §3.2
  走不会遇到；补一句环境说明即可，甚至只把 §7 的定位改成「作者侧自查」。
- 案例 §8 的「逐字节相同」说法——改成「以你自己的实测为准」即可，不影响任何一项
  判定（真正受影响的是读者的印象，不是判定）。
- 邀请函 §一 的「发版于 2026-11-17」与 tag 日期的差异——就绪记录已经承认；正文加
  半句最好，不加也不会让读者判错任何一项。
- §3.8 的「可选但建议」——如果按 M-7 改一句就够；否则它会静悄悄地让读者少做两项
  ★ 阻断项。

---

## 11. 一句话结论

**材料的骨架是能走通的**：从 clone 到三格式报告、证据包、契约活检、故障恢复，34 步
全部跑通，退出码与关键输出几乎逐字对得上预期，40 项的判据也都写到了可判的程度。
**真正挡在读者面前的是三件事**：G3 的两份材料互相矛盾（★）、记录模板把 5 个 ★ 阻断
项放在读者不会去的那一节（★）、以及四处缺命令（F1/F2/F3/F4）。这三条改完，邀请函
就可以发出去了。

---

*预演基线：`v1.0.0^{commit}` = `3e943b5b7870112f9df8994268482b30255d2e16` ·
原始副本与全部命令输出留在 `.scratch/reader-rehearsal/dexatlas`（未入库、未清理）·
本文件是**预演记录，不是验收结论**：40 项在这里一条也没有被判「通过」。*
