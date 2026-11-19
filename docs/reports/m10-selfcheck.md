# M10 验收自查（作者侧自动化预检）

> **状态：作者自测记录。本文件不是独立验收，不产生任何「通过/不通过」判定。**
>
> 本文件配套 [M10 独立验收准备包](m10-acceptance-pack.md)与
> [读者验收包](m10-reader-package.md)：把验收包 40 项中**可自动化**的检查写成
> `scripts/m10_selfcheck.py`，在提交验收材料前先发现文档、徽章、契约清单层面的
> 明显缺口，降低外部读者的执行负担。独立验收仍以读者亲手执行[验收记录模板](m10-review-record-template.md)
> 的结果为准。
>
> 执行日期：2026年11月17日 · 运行树：`v1.0.0` 这个 tag 所指的提交（发出前由发起人
> 把 tag 重打到材料定稿的那棵树上，**这里不写死某一串 hash**——本文里的
> `file:line` 引用只对本文所在的那棵树成立；读者在自己的验收 commit 上复跑时
> 以自己的实际输出为准）

## 1. 脚本用法

```bash
uv run --no-sync python scripts/m10_selfcheck.py           # 逐项结果 + 汇总
uv run --no-sync python scripts/m10_selfcheck.py --json    # 机器可读输出
```

- 无第三方依赖，只读仓库文件，**不写入**任何报告、徽章或数字。
- 退出码：`0` = 无失败项（「需人工」不算失败）；`1` = 至少一项失败。
- 判定三态与验收包一致：`通过` / `失败` / `需人工`。阻断项（★）单独标注。

## 2. 83 项分类结果（自动化 43 + 留人工 40）

### 2.1 本脚本自动化判定的 43 项检查

以下检查由脚本直接从仓库内容判定（对照物均为仓库内的代码、测试与文档，
不引入第二份手写真值）：

| 脚本检查 | 对应验收项/依据 | 判定依据 |
|---|---|---|
| `PACK.40-items` | §2/附录 A | 验收包表格恰 40 行、编号无重复 |
| `PACK.19-blocking` | §2.8/附录 A | 标 ★ 行 19 行，与声明清单一致 |
| `PACK.reader-links` | §1 | 读者包链接验收包与记录模板 |
| `DOC.pack-links` / `DOC.reader-links` / `DOC.contracts-links` | 文档完整性 | 三份文档的相对链接全部可解析 |
| `DOC.case-study` / `DOC.service-set` | B 组/E 组入口 | 案例文档与回归集文档存在 |
| `DOC.changelog-newest-section` | 变更记录纪律 | 最新一节含 Added/Changed |
| `DOC.changelog-version` | 版本一致性 | `__init__.py` 版本 = CHANGELOG 最新发布版 |
| `FIG.consistent` | 报告数字纪律 | `<!--fig:-->` 同键不出现两个值 |
| `FIG.suite-adds-up` | 报告数字纪律 | `tests.total = tests.fast + tests.slow` |
| `FIG.badge-tests` / `FIG.badge-coverage` | M9 纪律 | README 徽章数字 = 报告 `suite.passed`/`coverage.pct` |
| `F5.entry` / `F6.entry` | F5/F6 | 契约测试文件与契约实测脚本存在 |
| `F1.exit-codes` | F1 | 退出码 0–6：契约表 = CLI 常量（含隐式成功 0）= 契约测试 `EXPECTED_EXIT_CODES` |
| `F3.mcp-tools` | F3 | MCP 工具清单：契约表 = 测试断言（11 个） |
| `F4.report-fields` / `F4.schema-version` | F4 | JSON 报告顶层 10 字段与 `schema_version=3`：契约表 = 测试断言 |
| `F2.route-test` | F2 | 契约快照测试覆盖 REST/CLI/MCP 三表 |
| `D3.not-included` | D3/G5 | 证据包 `not_included` 声明 apk/full_sources/unrelated_strings/outside_analysis |
| `D1.no-external` | D1 | HTML 渲染器无脚本标签/外部资源 |
| `D5.escape` | D5 | HTML 渲染器使用 `html.escape` |
| `E1.frozen-20` | E1 | 冻结回归集恰 20 题（`benchmarks/m6_service_set.py`） |
| `E5.both-reported` | E5 | 冻结 20 题与完整 92 题报告入口同时存在 |
| `A4.demo-present` | A4 入口 | `demo.apk` 与构建脚本在仓库中 |
| `G.ruff` … `G.check-version-claims` | §6.3 门禁 | 7 个门禁命令可执行（只查存在性，不跑全量） |
| `F6.script` 等 `GATE.*` | §6.3/§6.4 | 验收包点名的 5 个脚本有可运行入口 |
| `M8-1.regression` | §6.2 M8-1 | `verify_citations` 回归测试存在 |
| `FIXTURE.precondition` | 读者实走演练 §3.2 | 装环境那一步必须抓第三方样本：不抓则 27 个集成用例 skip（退出码 0 不说明该跑的都跑了），样本数与 skip 数在读者包/工具包/摘要三处一致 |
| `A6.on-the-spot` | 读者实走演练 §3.3 | A6 的降级证据要当场记下：CLI 没有按 run 选运行的命令、新分析替换已发布运行，材料因此要求当场抄下并说明原因 |
| `PACKAGE.entry-count` | 读者实走演练 §3.6 | 证据包条目数：材料说的数目 = 报告数 + `manifest.json`；CLI 打印的是**归档自己的文件数**（含 `manifest.json`），不是清单里的报告数 |

### 2.2 明确留人工的 40 项（脚本标「需人工」）

验收包 40 个验收项（A1–G5）中的绝大多数需要读者在真实机器上执行命令、
观察输出并记录证据，脚本只做静态核对，不代替判定。逐项留人工的理由：

| 验收项 | 留人工理由 |
|---|---|
| A1–A3 | 需要读者 clone 指定 commit、真实安装依赖、抓第三方样本（不抓则集成用例 skip，每一条 skip 都要能说出是哪一类）、核对本机后端 |
| A4–A7 | 需要真实运行分析并记录计数/耗时/卡点（脚本只验证入口存在） |
| B1–B6 | 需要亲手走完整案例并复述输出 |
| C1–C6 | 需要打开真实分析工作区与证据包逐条核对 |
| D1–D5 | 浏览器/离线行为与真实证据包内容（代码侧已静态核对渲染器约束） |
| E1–E5 | 读者理解与引用方式检查（20 题清单与两套报告入口已静态核对） |
| F1–F6 | 需要真实运行 CLI/REST/MCP 与两个契约入口（清单与语义已静态核对） |
| G1–G5 | 需要注入故障、卸载后端、重复分析等真实运行（`not_included` 已静态核对） |

**留人工的原则：凡是要「跑起来看输出」「打开包核对」「复述理解」的判定，
脚本一律不代替；它只把仓库自身能回答的问题先答掉。**

## 3. 本次自查运行结果快照

> 以下为 2026年11月18日、在这棵含「读者实走演练三条新判据」的树上的运行记录
> （非机器生成数字；可随时用 §1 的命令复现核对）。

- 运行命令：`uv run --no-sync python scripts/m10_selfcheck.py`
- 退出码：`0`
- 汇总：**通过 43，失败 0，需人工 40；已判定项通过率 100.0%**
- 脚本输出末行原文：
  `自动化判定：通过 43，失败 0，需人工 40；已判定项通过率 100.0%`

**判据数 43 / 40 是稳定的，「通过 / 失败」的拆分不是**：脚本里有 1 项判据
（`G.vulture`）要 `vulture` 这个可执行文件，装齐 dev extras 的环境里通过；
在没装 dev extras 的工作树上，**只有这一项失败**，其余 42 项照过
（末行变成「通过 42，失败 1，需人工 40；已判定项通过率 97.7%」，退出码 `1`）。
上面这个快照来自装齐 dev extras 的机器。

本轮新增的三条判据来自[读者实走演练](reader-dry-run.md)：演练真的按材料走了一遍，
暴露出三条自查没查的事——装环境那一步不抓第三方样本就 27 个集成用例 skip
（退出码仍是 0）；A6 要的降级证据当场记下就找不回来（CLI 没有按 run 选运行的命令，
重跑会换掉最新一次运行）；证据包归档里是 4 个文件（3 份报告 + `manifest.json`），
而 CLI 当时只打印清单里的报告数（**现已改为打印归档自己的文件数**）。
三条判据各配一条红→绿回归测试（`tests/test_m10_selfcheck.py`）：把材料改成缺口的样子，
判据必须判红。

上一版本文件记的是「通过 38，失败 2」：两项失败都不是材料缺陷，而是两处环境与
判据的问题，现已分别消解——

| 原失败项 | 成因 | 现在 |
|---|---|---|
| `DOC.changelog-unreleased` | 判据写死了「CHANGELOG 顶部要有 `[Unreleased]` 一节」；v1.0.0 于 2026-11-17 发布后那一节被清空（Keep a Changelog 的正常形态），于是一棵正确的树被判红 | **判据已改为版本无关**：`scripts/m10_selfcheck.py` 现在检查 CHANGELOG 的**最新一节**（发版前是 `[Unreleased]`，发版后是刚打 tag 的那一节）是否含 Added/Changed，条目 id 随之改为 `DOC.changelog-newest-section` |
| `G.vulture` | 本次运行环境里 `PATH` 与 `.venv` 都没有 vulture（该工作树未装 dev extras） | 装齐 dev extras 的环境里通过 ✓ |

差异按[读者验收包 §7](m10-reader-package.md)的同一原则处理：读者在自己树上跑出的
输出可能与此不同，**以你的实际输出为准**。

要点：

1. 验收包结构（40 项、19 阻断项、读者包链接）完整。
2. 三份核心文档的相对链接全部可解析；CHANGELOG 版本与代码版本一致。
3. README 徽章与执行报告 `<!--fig:-->` 数字一致（徽章上的 tests 数 = 报告的
   `suite.passed`，徽章上的覆盖率 = 报告的 `coverage.pct`），
   `tests.total = tests.fast + tests.slow` 加和成立。**这些数字不在本文写死**：
   以 [`phase1-execution-report.md`](phase1-execution-report.md) 里的
   `<!--fig:tests.total-->`、`<!--fig:suite.passed-->`、`<!--fig:coverage.pct-->`、
   `<!--fig:tests.fast-->`、`<!--fig:tests.slow-->` 为准——重测一次它们就换新，
   材料跟着换，读者以自己 checkout 出来的那一份为准。
4. F1/F3/F4/D3/D1/D5/E1/E5 的静态契约核对全部一致（退出码 **0–6**、MCP 11 工具、
   报告 10 顶层字段 + `schema_version=3`、`not_included` 四键、HTML 无外部资源、
   冻结 20 题、两套报告入口）。
5. §6.3 门禁的 7 个命令中 6 个在本机可执行（`vulture` 因本环境未装 dev extras
   不可执行，见上表）；5 个被点名脚本均有 `__main__` 入口；本脚本不代跑全量门禁。
6. 读者实走演练的三条缺口已收口：样本前置条件（不抓则 27 个集成用例 skip，退出码 0
   不说明该跑的都跑了，三处材料的 skip 数一致）、A6 降级证据当场记下（材料的要求与
   CLI 能否回看历史运行一致）、证据包条目数与材料一致（4 = 3 份报告 + `manifest.json`）。
7. `FIXTURE.precondition` 判的是**材料**是否说清，不判本机有没有样本：本机未抓
   第三方样本时它仍判通过，detail 里写出「本机样本 0/2」；样本在不在、每一条 skip
   归因到哪一类，由读者按 A2 记录。

## 4. 边界与诚实声明

- 本自查是**作者侧预检**，按验收包硬规则 1 标注「自测」；它不能代替独立验收，
  也不改变 40 项当前「未验证」的状态。
- 脚本只读仓库；不运行全量测试、不起服务、不产生任何测量数字，因此不触碰
  「报告数字必须重测」的纪律。
- 「需人工」不是失败：它表示该项必须由未参与实现的读者按验收包执行并记录。
- 若后续代码或文档变更导致某项失败，请先修复再验收；脚本可重复运行，退出码
  非零即存在待处理项。
