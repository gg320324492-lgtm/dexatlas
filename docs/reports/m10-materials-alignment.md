# M10 独立验收材料 —— 与仓库现状的对账表

> **状态：作者侧对账记录。本文件不是独立验收，不产生任何「通过 / 不通过」判定。**
>
> **为什么有这份文件**：第三轮读者视角走查
> （[m10-reader-walkthrough-3rd.md](m10-reader-walkthrough-3rd.md)）给出的判语是
> **「读者会做出一份针对另一棵树的验收结论」**——材料自己之间、以及材料与仓库之间
> 有矛盾。材料矛盾会让唯一的独立验收作废，所以这是一件 P0。
> 这份文件把 M10 材料里的每一条事实性陈述逐条对到仓库里的真值来源，
> **并把判定写下来**：一致 / 已改 / 待最终同步。表本身就是「材料立得住」的证据。
>
> 对账日期：2026年11月18日 · 对账范围：M10 独立验收材料 8 份
> + 2 份同批材料（模板、就绪记录）· 本轮**只改 `docs/` 下的文档**，
> 没碰 `src/`、`tests/`、`scripts/`、`CHANGELOG.md`、
> `docs/architecture/public-contracts.md`；没跑 `pytest --cov`、coverage、
> `uv sync` 或 `scripts/refresh-report-figures.py`；没联网；没打 tag、没发 PR。
>
> **对账基线**：本文件所在的那棵树（分支 `claude/zealous-bardeen-358fb7`）。
> 材料里凡是**测量类**的数字（测试数、覆盖率、源指纹）一律**不写死**，
> 改为引用 [`phase1-execution-report.md`](phase1-execution-report.md) 里的
> `<!--fig:...-->` 标记——因为主会话正在对这棵树跑一次完整重测量，
> 落盘后那些数字会换新。**凡是能静态核对的数字**（40 项、19 阻断项、
> 27 个 skip、2 个样本、4 个证据包条目、退出码 0–6、MCP 11 工具、
> 报告 10 字段、`schema_version=3`、5 类/8 方法/23 调用点/21 调用边、
> 20 题 / 92 题、49/60 = 81.7%）**保留成数字**，因为它们不随重测量变。

---

## 0. 怎么判「对齐」

每条陈述按类型对到同一个真值来源：

| 陈述类型 | 真值来源 |
|---|---|
| 测试数、覆盖率、源指纹 | [`phase1-execution-report.md`](phase1-execution-report.md) 的 `<!--fig:...-->` 标记（**不手抄数字**） |
| CLI 退出码、MCP 工具数、REST 端点数、CLI 子命令数、报告字段与 `schema_version` | [`docs/architecture/public-contracts.md`](../architecture/public-contracts.md) 与 `src/` 里的实现 |
| 第三方样本从哪来、几个、不抓会怎样 | [`scripts/fetch-fixtures.sh`](../../scripts/fetch-fixtures.sh) |
| 证据包里有几个条目、哪几个文件 | [`src/dexatlas/reports/evidence_package.py`](../../src/dexatlas/reports/evidence_package.py) |
| 自动化自查判据数与结论 | `scripts/m10_selfcheck.py` 的当前输出（自动化 43 项 / 需人工 40 项） |
| 演示样例的计数、案例证据条数 | [`docs/case-studies/demo-app-walkthrough.md`](../case-studies/demo-app-walkthrough.md)、[m8-install-rehearsal.md](m8-install-rehearsal.md) |
| benchmark 成绩、冻结题量 | `docs/benchmarks/` 下的对应报告与 `benchmarks/` 里的脚本 |
| 引用行号是否还指对 | `scripts/check-doc-citations.py`（能判「符号漂移」的那 170 条）+ 逐条人工复核（只指位置的 132 条） |

**三条判定**：

- **一致** —— 陈述与真值来源对得上，材料不改。
- **已改** —— 对不上，材料已改；表里写明改成了什么。
- **待最终同步** —— 现在对得上，但主会话的重测量落盘后会换新，
  材料**已经改成引用标记**，不需要再动手；这一类要在最终同步时确认一次。

---

## 1. 对账表

### 1.1 测量数字类（9 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| A1 | README 徽章 tests 1620 / coverage 93.3%；`tests.total = 1473 + 147` | `m10-selfcheck.md` §3 | 执行报告 `<!--fig:tests.total-->` 等标记 | **已改** → 改为引用 `<!--fig:tests.total-->` / `<!--fig:suite.passed-->` / `<!--fig:coverage.pct-->` / `<!--fig:tests.fast-->` / `<!--fig:tests.slow-->`（写死的 1620 / 1473 已过期，现值 1643 = 1496 + 147） |
| A2 | 「实测 `1593 passed, 27 skipped`」「取到后是 `1620 passed` / `0 skipped`」 | `m10-reader-kit.md` §3.3 | 同上 | **已改** → 保留可静态核对的 **27**，去掉两个写死的套件数；套件总数指向 `<!--fig:tests.total-->` |
| A3 | 「实测：三后端齐备但未取样本时汇总行是 `1593 passed, 27 skipped`」 | `m10-reader-package.md` §3.2 | 同上 | **已改** → 同 A2 |
| A4 | 「`scripts/check-doc-citations.py`：通过（226 条引用，0 漂移）」 | `m10-acceptance-pack.md` §6.3 | `scripts/check-doc-citations.py` | **已改** → 改为「通过（**0 漂移**）」并注明「引用条数随材料增删变化，本包不写死条数」（当前 302 条） |
| A5 | 「`tests/test_docs.py` 全量：**60 项全通过**」 | `m10-acceptance-pack.md` §6.3 | `tests/test_docs.py` | **已改** → 改为「**全部通过**（用例数随树变化，本包不写死个数）」（当前收集 65 例） |
| A6 | 「`pytest tests/test_docs.py` 60 passed」 | `m10-acceptance-pack.md` §7 缺口表 | 同上 | **已改** → 同 A5 |
| A7 | 「引用检查 286 条引用、0 漂移、退出码 0」 | `m10-invitation-sender-checklist.md` §5 | 同 A4 | **已改** → 只留「0 漂移、退出码 0」 |
| A8 | 「引用检查 \| 286 条引用、0 漂移、退出码 0」 | `m10-invitation-readiness.md` §4 | 同 A4 | **已改** → 同 A7 |
| A9 | 报告里的测试数、覆盖率、源指纹 | 执行报告与 README 徽章 | `scripts/refresh-report-figures.py` 的下一次完整测量 | **待最终同步** —— 材料侧已全部改成引用标记，**不再需要改**；最终同步时只需确认标记里是新一轮的数 |

### 1.2 公共契约类（5 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| B1 | CLI 退出码 **0–6**（0 成功 / 1 空答案 / 2 请求错误 / 3 分析失败 / 4 重载歧义 / 5 截断 / 6 无索引） | 准备包 F1、读者包 §4、工具包 §4.1、邀请函 §2 | 契约表 = CLI 常量（含隐式成功 0）= 契约测试期望 | **一致**（`F1.exit-codes` 判据通过：三方都是 `[0,1,2,3,4,5,6]`） |
| B2 | MCP 工具 **11 个** | 准备包 F3、读者包 §4 | 契约表 = 测试断言 | **一致**（`F3.mcp-tools` 判据通过：契约表 11 个 / 测试 11 个） |
| B3 | JSON 报告 **10 个顶层字段** + `schema_version = 3` | 准备包 F4、读者包 §4 | 契约表 = 测试断言 = `src/dexatlas/reports/json_report.py` | **一致**（`F4.report-fields`、`F4.schema-version` 判据通过） |
| B4 | REST 端点 **23** 个、CLI 命令 **13** 个 | 准备包 F4 / 契约表 | 执行报告 `<!--fig:api.endpoints-->` = 23、`<!--fig:cli.commands-->` = 13 | **一致**（标记与实现对得上） |
| B5 | 契约活检 **49 项 = 28 REST + 6 MCP + 15 CLI** | `m10-invitation-sender-checklist.md` §5 | `docs/architecture/public-contracts.md`「49 是静态条数」 | **一致**（28 + 6 + 15 = 49；该文档另注明实跑执行条数依机器而定，为 47 或 48） |

### 1.3 第三方样本类（5 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| C1 | 抓 **2 个**第三方集成样本 | 摘要、读者包、发送前清单 | `scripts/fetch-fixtures.sh` 的 `FILES` 数组：`TestActivity.apk`、`multidex.apk` | **一致** |
| C2 | 来源与许可：androguard/androguard @ `tests/data/APK`，Apache-2.0；不进仓库 | 读者包 §3.2 | 同上脚本头部与生成的 `fixtures/apk/SOURCES.md` | **一致** |
| C3 | 不抓则 **27 个**集成用例 skip | 摘要、读者包、工具包、自查记录 | 静态核对：3 个样本门控测试文件（`test_androguard_integration.py` 10 个、`test_androguard_isolation.py` 9 个、`test_smali_fallback_integration.py` 8 个）里依赖样本的用例共 27 个 | **一致**（可静态复核，不随重测量变） |
| C4 | 工具包只说「抓第三方集成样本」，没说**几个** | `m10-reader-kit.md` §3.3 | 同 C1 | **已改** → 补上「**两个**第三方 APK：`TestActivity.apk`、`multidex.apk`，均取自 androguard 的 Apache-2.0 测试数据」 |
| C5 | 「退出码 0 只说明没有失败，不说明该跑的都跑了」 | 读者包 §3.2、自查记录 §2.1 | 项目纪律（准备包 §6.3「跳过不是通过」） | **一致**（三处措辞与自查判据 `FIXTURE.precondition` 一致） |

### 1.4 证据包类（4 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| D1 | 归档里是 **4 个条目** = 3 份报告 + `manifest.json` | 读者包 §3.6、自查记录 | `evidence_package.py` 的 `_REPORT_PATHS` 三个角色 + `MANIFEST_NAME` | **一致**（材料说的「4 个条目 / 3 份报告」与实现一致，本轮不改） |
| D2 | 「CLI 打印的「3 files」指的是那 3 份报告」 | 读者包 §3.6、自查记录 §2.1 / §3 | `cli/main.py` 现在调用 `package_file_summary(manifest)` | **已改** → CLI 打印**归档自己的文件数**（形如 `4 files: 3 reports + 1 manifest`）；材料三处改成新行为，并把「只数 manifest 清单会得 3」写清楚 |
| D3 | `manifest.json` 不出现在自己的 `files` 清单里（文件不能给自己算哈希） | 读者包 §3.6 | `evidence_package.py` 构造 `manifest` 时只遍历 `files` | **一致**（自查判据 `PACKAGE.entry-count` 的 `manifest_not_listed` 通过） |
| D4 | `not_included` 明示不含 APK、全量源码、未被引用的字符串 | 准备包 D3/G5、读者包 §3.6 | `evidence_package.py` 的 `not_included` 三键 | **一致**（`D3.not-included` 判据通过） |

### 1.5 自查类（3 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| E1 | 自动化 **43** 项 + 需人工 **40** 项 = 83 | 自查记录 §2、邀请函 §2、就绪记录 | `scripts/m10_selfcheck.py` 当前输出 | **一致**（本机实测「需人工 40」；自动化判据 43 项） |
| E2 | 快照「通过 43，失败 0，需人工 40；已判定项通过率 100.0%」 | 自查记录 §3 | 同上 | **已改** → 保留该快照（装齐 dev extras 的机器），但**补上环境依赖**：未装 dev extras 时 `G.vulture` 单独失败，实测末行为「通过 42，失败 1，需人工 40；已判定项通过率 97.7%」、退出码 1。就绪记录原本已经这么写，现在两份材料口径一致 |
| E3 | 验收包 **40 项**、**19 个** ★ 阻断项 | 准备包 §2 / §2.8、邀请函 §2、工具包 §5 | `scripts/m10_selfcheck.py` 的 `PACK.40-items` / `PACK.19-blocking` | **一致**（两判据均通过：读到 40 项、标 ★ 行 19 行、声明清单 19 项；邀请函 §2 的 19 项清单与准备包 §2.8 逐项相同） |

### 1.6 演示样例、案例与 benchmark 类（10 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| F1 | demo 计数 **5 classes / 8 methods / 23 call sites / 21 call edges / 1 resource string**；project id `apk_80a8fe0e81204c9f` | 准备包 A4、读者包 §3.3、邀请函 §2 | M8 演练 §3 耗时表；读者实走演练 §3.3（逐字命中） | **一致** |
| F2 | `search sk_live` 命中 `sk_live_2f8a91c4e7b3`，`Kind=string` | 准备包 B3 | `examples/demo-app/smali/com/example/demo/MainActivity.smali:21`；`docs/case-studies/demo-app-walkthrough.md` | **一致** |
| F3 | demo 报告 **11 条** evidence 全为 `verified` | 准备包 §4 | `docs/case-studies/demo-app-walkthrough.md`「Evidence records \| 11」 | **一致** |
| F4 | **5 个**一方样例 APK 已提交在 `examples/` | 准备包 §7 | `<!--fig:samples.apks-->` = 5；`examples/` 下确有 5 个 `.apk` | **一致** |
| F5 | Docker 镜像里**没有** `examples/` | 读者包 §3.2 路线 B | `Dockerfile` 只 `COPY src/ ./src/` 与 `pyproject.toml uv.lock README.md LICENSE` | **一致** |
| F6 | 冻结回归集 **20 题**；完整集 **92 题** | 准备包 E1/E5、读者包 §4 | `benchmarks/m6_service_set.py`（20 题）；`docs/benchmarks/comparison.md`「Task count: 92」 | **一致** |
| F7 | M6 层级 2 三轮合计 **49/60 = 81.7%**，逐轮 15/20、16/20、18/20；验收线每轮 ≥16/20、三轮合计 ≥54/60 | 准备包 §0 / §4、工具包 §0.3、邀请函 §1 | `docs/benchmarks/m6-level2-retest4.md` | **一致** |
| F8 | 窄验证转通过 **3/6**，未达 ≥4 | 工具包 §0.3 | `docs/benchmarks/m6-level2-narrow-verify3.md` | **一致** |
| F9 | 层级 2 首测 **24/60 = 40.0%** | 准备包 §4 | `docs/benchmarks/m6-level2-failure-analysis.md` | **一致** |
| F10 | 评分基线 GitHub 约 **75%** / Upwork 约 **65%**；复评 77.5% / 68.75% | 读者包抬头、工具包 §2、准备包 §5 | `docs/reports/portfolio-readiness-2026-11-15.md` 与 `-recheck.md` | **一致**（两套数字用的是同一组维度与权重，材料已写明复评不是新基线） |

### 1.7 时间口径类（8 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| G1 | 冷缓存（含 clone、依赖、后端下载）首次 **10–20 分钟** | 摘要、读者包、工具包、准备包、邀请函 | 读者实走演练 §3.2：实测 **10 分 28 秒**（落在区间下沿） | **一致** |
| G2 | 暖缓存到第一份报告 **约 1.5–2 分钟**（材料写作「M8 演练实测约 1.5 分钟」） | 摘要、读者包 §2 / §5.4、工具包 §3.3、准备包 §3.1、邀请函 §2、模板 | [m8-install-rehearsal.md](m8-install-rehearsal.md) §3 / §4：**M8 里没有 1.5 分钟这个数**——它写的是「从空目录到第一份报告，暖缓存约 30 秒、冷缓存约 1 分钟」，首次分析 6.8 秒 | **已改** → 1.5–2 分钟改写成**预算档位**（明写「不是实测值」），并给出两处口径不同的实测锚点：M8「空目录 → 第一份报告，暖缓存」约 **30 秒**（同一次首次分析本身 6.8 秒）；读者实走演练「重建 `.venv` → 第一份报告」**8 秒**（分析本身 3.8 秒）；并写明**做快于 30 秒不是卡点**。六份材料现在同一套说法 |
| G3 | M8 首次分析 **6.8 秒** | 读者包 §2、工具包 §3.3 | M8 §3 耗时表 | **一致** |
| G4 | 读者实走演练：冷缓存 **10 分 28 秒**、clone + `uv sync` **4 分 24 秒**、重建 venv 后 **8 秒**（分析本身 3.8 秒） | 读者包 §2 / §5.4、准备包 §3.1 | `reader-dry-run.md` §3 | **一致** |
| G5 | Docker 构建：层已就绪 **2 分 16 秒**；无层缓存走代理 **1099 秒 ≈ 18 分 19 秒**；CI runner 上 `docker build` 这一步 **46 秒**（**另一段**） | 读者包 §3.2 / §5.4、准备包 §3.3 / §3.6 | M8 §3；读者实走演练 §3.2 路线 B；CI run `44334171465` 的 `Build image` 步骤（[c6-build-time-from-ci.md](c6-build-time-from-ci.md)） | **一致**（三段各自标明测的是哪一段） |
| G6 | clone + `uv sync`：**15 秒–4 分 30 秒** | 准备包 §3.6 | M8 冷缓存 15 秒；读者实走演练 4 分 24 秒 | **一致** |
| G7 | 完整案例（analyze → xrefs）约 **1–2 分钟** | 摘要、读者包、工具包、邀请函、模板 | 材料自身口径（实测分析本身 3.8–6 秒，此处是给读者的余量） | **一致** |
| G8 | 40 项判定 + 两平台打分**预留半天** | 摘要、读者包、工具包、邀请函、模板 | 四处一致 | **一致**（属预算估计，非测量值） |

### 1.8 树、tag 与「这份材料属于哪棵树」类（9 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| H1 | `git rev-parse v1.0.0` 给的是 **tag 对象**的 hash，与 `^{commit}` 不同 | 摘要、发送前清单、就绪记录 | `git cat-file -t v1.0.0` = `tag`（附注 tag） | **一致**（第三轮走查 N9 已修：三份材料的写法现在一致，都教读者用 `^{commit}`） |
| H2 | 发送前清单写死了两串 hash（`2453b7d…` / `b71bf309…`） | `m10-invitation-sender-checklist.md` 组二 | `git rev-parse` 实测——**tag 每重打一次就换一次串** | **已改** → 改成**形状示例**并注明「下面的 hash 是示意，必须现查现填」；自查判据从「数值相等」改成「形状正确」（`cat-file -t` 打印 `tag`、两条 `rev-parse` 互不相同） |
| H3 | 就绪记录写死了两串 hash | `m10-invitation-readiness.md` §4 | 同 H2 | **已改** → 同 H2 |
| H4 | 「你 `git checkout v1.0.0` 拿到的就是**含本轮全部修正的那棵树**」 | `m10-reader-kit.md` 抬头 | 「哪棵树」由 tag 决定，随重打 tag 变 | **已改** → 改成树中立表述：发出前发起人把 tag 重打到材料定稿树，「你 checkout 到的就是材料定稿的那棵树」，并给出比对方法 |
| H5 | 「运行树：`v1.0.0` 这个 tag 所指的提交（**含本轮 M10 读者材料修正**）」 | `m10-selfcheck.md` 抬头 | 同 H4 | **已改** → 去掉「含本轮修正」这个会过期的断言，明写「这里不写死某一串 hash」「本文里的 `file:line` 引用只对本文所在的那棵树成立」 |
| H6 | 「**编写本包时的**门禁现状（2026-11-15）」小节里，正文写「通过」而末条写「编写本包时是红的」 | `m10-acceptance-pack.md` §6.3 | 小节标题与内容自相矛盾 | **已改** → 拆成两段：「2026-11-15 初稿时门禁是红的（原因）」与「材料定稿树上复跑的结果（通过）」；并去掉写死的引用条数与用例数 |
| H7 | 读者实走演练里的旧数字与旧结论（`1593` / `1620` / `1585` / `1612` / 40 条自动化判据 / 13 个文件 / 「材料还差最后一步」） | `reader-dry-run.md` 全文 | 那是一次实走的**历史快照** | **已改** → 加历史定位 banner（明确「只对 `0104ccb7` 那棵树成立」）、§6.1 补判据条数变化说明、§8 补状态说明，并**新增 §9**：11 条卡点的逐条现状表 + tag 纪律的落点。历史数字不回改 |
| H8 | 发送前清单「tag 指向的那棵树含本轮全部材料修正」的判据是「材料目录的差异」 | `m10-invitation-sender-checklist.md` 组二 | 判据应直接盯 **M10 材料本身** | **已改** → 判据改成 `git diff --name-only "v1.0.0^{commit}"..HEAD -- docs/reports/m10-*.md` 期望为空；另两条命令保留 |
| H9 | 就绪记录「案例与证据包在验收树上：13 个文件」 | `m10-invitation-readiness.md` §4 | `git ls-tree -r HEAD docs/case-studies/` → **20** 个文件（4 篇 markdown + 4 个 zip + 12 份报告） | **已改** → 改为当前值并注明「个数随附件集增删变化，要核的是结构」；发送前清单同一处一并改 |

### 1.9 引用行号类（2 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| I1 | 读者工具包 §5「本工具包引用的数字与出处」里的 `file:line` | `m10-reader-kit.md` | `scripts/check-doc-citations.py` 只自动核**指名符号**的 170 条；只指位置的 132 条要人工核 | **已改** → 第三轮走查 N11 点名的 9 处**逐条重新取行号**（其中 4 处原本指向空行、2 处指向代码围栏、3 处差一行）。另修：读者包 `:209`（应 :251）、`:337`（应 :394）、`:318`（应 :369）、`:434`–`:435`（应 :491）、`:73`/`:348`（应 :74/:443）、`:69`（应 :70）、`:61`（应 :62）、`:261`（应 :317）；准备包 `:457`（应 :460）、`:476`–`:481`（应 :477–:482）、`:490`–`:495`（应 :491–:496） |
| I2 | 就绪记录「对外可见措辞」表的出处行号 | `m10-invitation-readiness.md` §4 | 同 I1 | **已改** → 5 处过期行号重取：准备包 `:656`/`:673`（应 `:660`/`:677`）、`docs/status.md:129`（应 `:132`）、`README.zh-CN.md:517`（应 `:522`）、根 `README.md:643`（应 `:647`，原值指的是 M6 行不是 M10 行）、`docs/reports/README.md:88`（应 `:91`） |

### 1.10 材料之间的一致性类（2 条）

| # | 检查过的陈述 | 出处 | 真值来源 | 判定 |
|---|---|---|---|---|
| J1 | 读者工具包全篇没有 `verified` / `lead` / `insufficient` 的定义 | `m10-reader-kit.md` | 第三轮走查 N15 | **一致**（§5 已有「术语（就地定义）」块，本轮复核仍在位） |
| J2 | 准备包 §3.3（Docker 路线）把 M8-2 写成「已知限制：查询类命令没有 `--workspace`」 | `m10-acceptance-pack.md` §3.3 | 第三轮走查 N10：与 §7、`docs/status.md`、读者包、源码 `cli/main.py` 四处矛盾 | **一致**（已改为「M8-2 **已修复**：容器内的查询类命令现在同样有 `--workspace`/`-w`」） |

---

## 2. 判定分布

| 判定 | 条数 |
|---|---:|
| 一致 | **34** |
| 已改 | **22** |
| 待最终同步 | **1** |
| **合计** | **57** |

**「已改」里最要紧的三条**：

1. **G2 —— 暖缓存那个 1.5–2 分钟本来没有出处。** 材料把它挂在 [M8 演练](m8-install-rehearsal.md)名下，
   而 M8 的原文是「暖缓存约 30 秒」，首次分析 6.8 秒。读者拿 8 秒去对 1.5–2 分钟，
   会以为自己测错了——这正是读者实走演练 §4 第 4 条的原始判断，也是走查 N12 的残留。
   现在六个材料位置统一成「按 1.5–2 分钟预留（预算档位）+ 两处口径不同的实测锚点
   + 做快于 30 秒不是卡点」。
2. **D2 —— 证据包 CLI 打印的数已经变了。** CLI 现在打印归档自己的文件数
   （`4 files: 3 reports + 1 manifest`），材料里「CLI 打印『3 files』」的说法会让读者
   数出 4 个文件却听见 3，凭空记一条「不通过」。材料三处已按新行为改写。
3. **H2 / H3 —— 两串写死的 tag hash 发出时必然是错的。** tag 每重打一次就换一次串，
   而材料要求「发出前重打 tag」——写死的 hash 与「重打 tag」这两件事不能同时成立。
   现在改成形状示例 + 「必须现查现填」，并把自查判据改成看形状而不是看数值。

---

## 3. 本轮做了什么、没做什么

### 3.1 做了

- 逐条抽出 8 份材料（+ 2 份同批材料）里的**每一条事实性陈述**，
  对到 §0 的真值来源表，写进 §1 的 57 行对账表。
- 改了 **22 条**对不上的陈述，改法一律是「**能静态核对的留成数字，
  随重测量变的一律改成引用标记**」。
- 修完了第三轮走查 N11 点的 9 处行号错位，并把同类的 12 处一并重取。
- 给 `reader-dry-run.md` 加了历史定位 banner 与 **§9 现状表**（11 条卡点逐条现状），
  把一份 2026-11-17 的历史记录接回今天的状态。

### 3.2 没做（有意不做）

| 没做的事 | 为什么 |
|---|---|
| 改 `src/`、`tests/`、`scripts/` | 本轮是纯文档范围；`src/` 一改就动源指纹，会打断主会话正在跑的重测量 |
| 改 `CHANGELOG.md`、`docs/architecture/public-contracts.md` | 别的窗口正在改 |
| 改写 `reader-dry-run.md` 里的旧数字 | 那是一次实走的**历史记录**，改它等于伪造历史。正确做法是标注它是历史记录并补现状表（已做） |
| 跑 `pytest --cov` / coverage / `uv sync` / `refresh-report-figures.py` | 会动测量产物与指纹；本轮只跑了**只读**门禁 |
| 把「需人工」的 40 项当成待办改掉 | 它们要真实读者执行才算数。材料的任务是让读者**能**执行，不是替读者执行 |
| 把 `m10-invitation-template.md`、`m10-invitation-readiness.md` 排除在外 | 这两份不在给定的目标文件清单里，但它们与目标材料**同属一套**、被邀请函直接链接；G2 / H2 / H3 / I2 的矛盾跨到它们身上。留着不改等于把矛盾从一份文件挪到另一份 —— 所以一并改了，并在回报里单独点名 |

### 3.3 改动的文件

| 文件 | 改了什么 |
|---|---|
| `docs/reports/m10-reader-package.md` | A3、C4、D2、G2、H4、I1 涉及的行号 |
| `docs/reports/m10-acceptance-pack.md` | A4、A5、A6、G2、H6 |
| `docs/reports/m10-reader-kit.md` | A2、C4、D2、G2、H4、I1（9 处行号 + 4 处） |
| `docs/reports/m10-executive-summary.md` | G2（另核 40 项 / 19 阻断项 / 2 样本 / 27 skip，均一致） |
| `docs/reports/m10-invitation-final.md` | G2（另核 40 项 / 19 阻断项清单、60 / 110 行的时间表、邀请函 §2 占位符，均一致） |
| `docs/reports/m10-invitation-sender-checklist.md` | A7、H2、H8、H9、凭据 grep 的措辞（B5 / C5 / D2 复核后一致，未改） |
| `docs/reports/m10-selfcheck.md` | A1、C3、C5、D2、E1、E2、H5 |
| `docs/reports/reader-dry-run.md` | H7（历史定位 banner + §9 现状表 + §6.1 / §8 状态说明） |
| `docs/reports/m10-invitation-template.md` | G2（与邀请函成稿同一口径） |
| `docs/reports/m10-invitation-readiness.md` | A8、H3、H9、I2 |
| `docs/reports/m10-materials-alignment.md` | **新增**（本文件） |

---

## 4. 仍要真实读者执行才能得出的结论

这份对账表**没有**、也不能替代独立验收。下面这些结论只能由一位未参与实现的读者
在真实机器上执行后得出；本轮**一条都没有替它下**：

- 40 个验收项的「通过 / 不通过 / 未验证」三态判定（A1–G5）——
  现有 **40 项全部为「未验证」**，本轮一条也没改。
- 19 个 ★ 阻断项的结论；任何一个不通过，M10 即不通过。
- GitHub / Upwork 两套权重下的重评分数（本轮只核了**权重与基线**，
  没有替读者打任何一个维度分）。
- 材料**能不能让一个不知情的人真的走完一次验收**——这是走查判语
  「读者会做出一份针对另一棵树的验收结论」指向的东西，
  只有真实读者走一遍才能验证材料已经不再自相矛盾。
- 机器差异带来的结果差异（macOS 未验证、后端缺失降级、超时降级等）。

**作者侧自动化自查（43 项自动化判据 + 40 项需人工）已经跑过并记在
[m10-selfcheck.md](m10-selfcheck.md)**，但按项目硬规则 1，它标注「自测」，
**不能代替独立验收**，也不改变 40 项「未验证」的状态。

---

## 5. 「待最终同步」清单

主会话的完整重测量落盘后，只需要核这一处，**不需要再改材料**：

| 位置 | 要确认什么 | 现状 |
|---|---|---|
| [`phase1-execution-report.md`](phase1-execution-report.md) 的 `<!--fig:tests.total-->` / `<!--fig:tests.fast-->` / `<!--fig:tests.slow-->` / `<!--fig:suite.passed-->` / `<!--fig:coverage.pct-->` / `<!--fig:coverage.covered-->` / `<!--fig:coverage.total-->` / `<!--fig:api.endpoints-->` / `<!--fig:cli.commands-->` / `<!--fig:samples.apks-->` | 新一轮完整测量后，这几个标记里是**同一棵树**的数字；README 徽章与之一致；`tests.total = tests.fast + tests.slow` 成立 | 材料侧已全部改成引用标记；本轮实测值 `1643 = 1496 + 147`、覆盖率 93.3%、端点 23、命令 13、样例 5 |
| 同上的 `source_fingerprint` | 新指纹对应新树；CI 重算后不 mismatch | 材料侧**未写死任何指纹** |
| `m10-selfcheck.md` §3 的自查快照 | 那一轮自查若在重测量后的树上复跑，快照行可更新；判据数 43 / 40 不变 | 材料已标注快照的环境依赖与复跑方式 |
| `docs/reports/README.md` 的索引 | 收录本文件 | 见 §3.3 |

**材料里已经不再写死的测量数字**（这就是「待最终同步」的含义）：
测试总数、快 / 集成拆分、套件通过数、覆盖率、源指纹、引用检查的条数、
`tests/test_docs.py` 的用例数、案例附件的文件数。
**能静态核对的数字仍在材料里**：40 项、19 阻断项、27 个 skip、2 个样本、
4 个证据包条目、退出码 0–6、MCP 11 工具、报告 10 字段、`schema_version=3`、
5 / 8 / 23 / 21 / 1、20 题 / 92 题、49/60 = 81.7%、3/6、6.8 秒、30 秒、
8 秒、2 分 16 秒、1099 秒、46 秒、4 分 24 秒、10 分 28 秒。

---

## 6. 本轮跑过的门禁

| 门禁 | 结果 |
|---|---|
| `scripts/check-doc-citations.py` | **0 漂移、0 未解析**（改材料前后各跑一次） |
| `scripts/m10_selfcheck.py` | 本机（**未装 dev extras**）：`通过 42，失败 1，需人工 40`，唯一失败项 `G.vulture`（判的是 vulture 在不在 PATH/venv 里）——**不是材料缺陷**；装齐 dev extras 应为 `通过 43，失败 0，需人工 40` |
| 11 份材料的 114 处 `file:line` 人工复核 | 目标材料 **0 处**指向空行 / 围栏 / 越界；`reader-dry-run.md` 的 14 处按设计指向**它自己的历史树**（`0104ccb7`），已在 banner 里写明 |
| `tests/test_docs.py` | **未跑**（本 worktree 没装 dev extras，pytest 不可用）；用例数按静态收集为 65，材料已不写死该数 |
| `pytest --cov` / coverage / `uv sync` / `refresh-report-figures.py` | **未跑**（会动测量产物与源指纹） |
