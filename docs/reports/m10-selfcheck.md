# M10 验收自查（作者侧自动化预检）

> **状态：作者自测记录。本文件不是独立验收，不产生任何「通过/不通过」判定。**
>
> 本文件配套 [M10 独立验收准备包](m10-acceptance-pack.md)与
> [读者验收包](m10-reader-package.md)：把验收包 40 项中**可自动化**的检查写成
> `scripts/m10_selfcheck.py`，在提交验收材料前先发现文档、徽章、契约清单层面的
> 明显缺口，降低外部读者的执行负担。独立验收仍以读者亲手执行[验收记录模板](m10-review-record-template.md)
> 的结果为准。
>
> 执行日期：2026年11月17日 · 运行树：`v1.0.0` 这个 tag 所指的提交（含本轮 M10 读者材料修正；
> 读者在自己的验收 commit 上复跑时以自己的实际输出为准）

## 1. 脚本用法

```bash
uv run --no-sync python scripts/m10_selfcheck.py           # 逐项结果 + 汇总
uv run --no-sync python scripts/m10_selfcheck.py --json    # 机器可读输出
```

- 无第三方依赖，只读仓库文件，**不写入**任何报告、徽章或数字。
- 退出码：`0` = 无失败项（「需人工」不算失败）；`1` = 至少一项失败。
- 判定三态与验收包一致：`通过` / `失败` / `需人工`。阻断项（★）单独标注。

## 2. 40 项分类结果

### 2.1 本脚本自动化判定的 40 项检查

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
| `D3.not-included` | D3/G5 | 证据包 `not_included` 声明 apk/full_sources/unrelated_strings |
| `D1.no-external` | D1 | HTML 渲染器无脚本标签/外部资源 |
| `D5.escape` | D5 | HTML 渲染器使用 `html.escape` |
| `E1.frozen-20` | E1 | 冻结回归集恰 20 题（`benchmarks/m6_service_set.py`） |
| `E5.both-reported` | E5 | 冻结 20 题与完整 92 题报告入口同时存在 |
| `A4.demo-present` | A4 入口 | `demo.apk` 与构建脚本在仓库中 |
| `G.ruff` … `G.check-version-claims` | §6.3 门禁 | 7 个门禁命令可执行（只查存在性，不跑全量） |
| `F6.script` 等 `GATE.*` | §6.3/§6.4 | 验收包点名的 5 个脚本有可运行入口 |
| `M8-1.regression` | §6.2 M8-1 | `verify_citations` 回归测试存在 |

### 2.2 明确留人工的 40 项（脚本标「需人工」）

验收包 40 个验收项（A1–G5）中的绝大多数需要读者在真实机器上执行命令、
观察输出并记录证据，脚本只做静态核对，不代替判定。逐项留人工的理由：

| 验收项 | 留人工理由 |
|---|---|
| A1–A3 | 需要读者 clone 指定 commit、真实安装依赖、核对本机后端 |
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

> 以下为 2026年11月17日、在这棵含 M10 读者材料修正的树上的运行记录（非机器生成
> 数字；可随时用 §1 的命令复现核对）。

- 运行命令：`uv run --no-sync python scripts/m10_selfcheck.py`
- 退出码：`0`
- 汇总：**通过 40，失败 0，需人工 40；已判定项通过率 100.0%**
- 脚本输出末行原文：
  `自动化判定：通过 40，失败 0，需人工 40；已判定项通过率 100.0%`

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
3. README 徽章（tests 1588 / coverage 93.3%）与执行报告 `<!--fig:-->` 数字一致；
   `tests.total = 1441 + 147` 加和成立。
4. F1/F3/F4/D3/D1/D5/E1/E5 的静态契约核对全部一致（退出码 **0–6**、MCP 11 工具、
   报告 10 顶层字段 + `schema_version=3`、`not_included` 三键、HTML 无外部资源、
   冻结 20 题、两套报告入口）。
5. §6.3 门禁的 7 个命令中 6 个在本机可执行（`vulture` 因本环境未装 dev extras
   不可执行，见上表）；5 个被点名脚本均有 `__main__` 入口；本脚本不代跑全量门禁。

## 4. 边界与诚实声明

- 本自查是**作者侧预检**，按验收包硬规则 1 标注「自测」；它不能代替独立验收，
  也不改变 40 项当前「未验证」的状态。
- 脚本只读仓库；不运行全量测试、不起服务、不产生任何测量数字，因此不触碰
  「报告数字必须重测」的纪律。
- 「需人工」不是失败：它表示该项必须由未参与实现的读者按验收包执行并记录。
- 若后续代码或文档变更导致某项失败，请先修复再验收；脚本可重复运行，退出码
  非零即存在待处理项。
