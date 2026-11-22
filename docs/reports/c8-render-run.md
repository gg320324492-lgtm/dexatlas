# CLI 增加「渲染某一次运行」—— C8 的落地记录

日期：2026年11月20日 · 分支 `claude/interesting-bose-ebdef6`
worktree `.claude/worktrees/confident-wiles-618c95`（本会话）· 基线树 `2920f8b`

> **一句话**：候选 **C8** 已完成——CLI 增加「渲染某一次运行」的能力：
> `dexatlas runs` 列出某项目的全部运行、`--run` 原样取回某次运行的记录；
> `dexatlas render` 把某次**已完成且仍是已发布**的运行渲染成可复核目录
> （三格式报告 + 证据包 zip + `run.json`）。这是**公共契约的向后兼容新增**
> （规则 5）：CLI 活检 15→18、静态总数 49→52，契约表、CHANGELOG、两页
> how-to-verify、发版材料、M10 读者包同步改齐；15 条集成测试覆盖输出结构、
> 退出码与「未发布/已被替换的 run 拒绝渲染」。**本窗口没有跑**
> `scripts/refresh-report-figures.py`，**报告数字与 tag 留给主会话合入后
> 统一重测**。

---

## 0. 这一层补的是什么

读者实走演练 §4 第 9 条（M10 演练 #9）：后端缺失的错误确实落库
（`analysis_runs.errors`），但 **CLI 没有「渲染某一次运行」的命令**，重跑一次
分析后 stdout 上的证据就没了。C8 的候选节还点名了另两条缺口：公共契约的
CLI 子命令表里没有这条命令；演练 §4 第 9 条「当场记下」的建议要随工具能力更新。

C8 补的是**同一个事实的两条通道**：

1. **记录通道**（`dexatlas runs <project_id> --run <run_id>`）——把某次运行
   自己的记录（工具版本、起止、错误记录）原样读回。库里的记录一直在，现在
   有一条命令能取到它；
2. **渲染通道**（`dexatlas render <project_id> <run_id> --output <dir>`）——
   把某次已发布运行的报告与证据包按可复核结构落到一个目录。写进去的包就是
   `dexatlas export` 写的那个包（同一选择、同一守卫），并且**写入后当场过
   `verify_package` / `verify_citations`**——渲染命令自己先验证，不把校验
   留给读者。

## 1. 设计决定（与候选判据逐条对账）

候选 C8 的「怎么算做完」有四条判据，逐条对账：

| 判据 | 落地 |
|---|---|
| 「有 published run」与「没有」两种情况下都有明确退出码，复用既有退出码集合 | `render`：run 不存在 / 未发布 / 快照已被替换 / 输出目录非空 / 项目不存在 → **2**（`EXIT_BAD_REQUEST`）；渲染自身失败 → **3**（`EXIT_FAILED`）。`runs`：项目不存在 → **2**；项目没有运行 → **1**（`EXIT_EMPTY`）；未知 run id → **2**。没有新造任何退出码语义 |
| 契约表与快照测试同步 | 契约表 §1.1 新增两行、§7 改齐；`tests/test_public_contracts.py` 的 `CONTRACT_CHECK_SECTIONS`/`CONTRACT_CHECK_TOTAL` 与 `scripts/verify-public-contracts.py` 的 `check()` 调用点同步（见 §3） |
| 有一个在旧实现下失败的回归测试（规则 1） | `tests/test_run_render.py` 的 15 条测试在旧实现（无这两个命令）下全部失败——命令不存在本身就是红；其中「渲染只读工作区」「拒绝渲染已被替换的 run」两条在**没有 render 命令**与**有命令但不去重**的两种旧实现下都会红 |
| 后端缺失的那次运行，错误能被这条命令原样取回 | `test_runs_shows_one_runs_record_with_its_errors`：种子运行带 `not_installed` 错误，`runs --run` 输出里出现该错误码与记录 |

**关键设计决定：只渲染「已完成且仍是已发布」的运行。** 候选文本设想的验收
场景是「后端缺失的那次运行，错误能被原样取回」——这条由 `runs --run` 兑现；
而 `render` 渲染的是**快照**，快照只有一份（发布的那份）。被新分析换下的旧
run：记录还在（`runs --run` 能读），但它的符号行已不在项目表里，渲染它只能
得到「穿着旧 run 名字的新快照」——那是贴错标签的证据，C8 拒绝这样做，退出码 2
并在错误信息里点名已发布的 run。这不是缩水：`export` 走的也是 published run，
`render` 与它同界，多出来的能力在 `runs --run` 的记录回看上。

## 2. 改了什么

### 2.1 代码侧

| 文件 | 改动 |
|---|---|
| `src/dexatlas/reports/run_render.py` | **新模块**。`render_run()`：校验 run 存在、属于该项目、已完成、仍是已发布 → 写 `run.json`（schema_version 1：run 的身份、工具版本、起止、时长、published 标记、脱敏后的错误列表）→ 经 `package_contents()`/`package_manifest()` 生成证据包 → zip 写入 `.building` 临时名后原子替换 → 当场 `verify_package` + `verify_citations`，失败则清掉整个输出目录并报错。`render_run_summary_lines()`：CLI 汇总行（报告数、包内列出的文件数、源码片段数、未解析引用数——数从清单与引用报告来，不从目录重数） |
| `src/dexatlas/reports/evidence_package.py` | **重构**：`build_evidence_package()` 拆出 `package_contents()`（选择哪些文件进包）与 `package_manifest()`（为给定文件集生成清单，绑定到当时那次分析）。zip 导出与目录渲染共用同一选择与守卫；`build_evidence_package()` 行为不变（既有 32 条证据包测试全绿） |
| `src/dexatlas/cli/main.py` | 新增 `runs` 与 `render` 两个子命令（现 15 个命令）。`runs`：默认表格列出运行（run id、状态、完整性、开始时间、时长、是否已发布，`--limit` 有界）；`--run <id>` 打印单条记录，错误走 stderr。`render`：`--output/-o` 必填，目录非空拒绝（2）；成功打印汇总行与一句「如何复核」的提示。退出码映射集中在命令层，`RunRenderError` → 2，其余异常 → 3 |

### 2.2 契约与门禁侧（数字全部同源改动）

| 位置 | 改动 |
|---|---|
| `scripts/verify-public-contracts.py` | `cli_checks()` 增加 3 个 `check()` 调用点：runs 列出已发布运行、未知 run id → 2、render 已发布运行落盘（目录含 `evidence/evidence-package.zip` 与 `run.json`）。**15 → 18，静态总数 49 → 52** |
| `tests/test_public_contracts.py` | `CONTRACT_CHECK_SECTIONS = {"_rest_requests": 28, "mcp_checks": 6, "cli_checks": 18}`、`CONTRACT_CHECK_TOTAL = 52`、`STATED_NUMBER` 正则 49 → 52 |
| `docs/architecture/public-contracts.md` | §1.1 子命令表新增 `runs`、`render` 两行；§7 开头的静态条数（49→52）与两次实跑行数（47/48→50/51）改齐，并留一段 2026-11-20 的更新说明（旧实跑数字保留为历史记录）；§7.3 尾部的静态数说明同步 |
| `CHANGELOG.md` | `[Unreleased]` §Added 新增第一条：`dexatlas render` 的契约变更说明（向后兼容新增、退出码映射、活检计数变化、对演练 #9 的缓解与边界） |
| `docs/how-to-verify.md` / `docs/how-to-verify.zh-CN.md` | §契约活检的「为什么实跑是 51 项，不是 52」与两张实跑表改齐（48/47 → 51/50，15 CLI → 18 CLI） |
| `docs/releases/v1.0.0.md` / `docs/reports/v1.0.0-github-release-body.md` | 四处 49/28+6+15 的历史数字**保留**（它们描述 v1.0.0 tag 那棵树），各加一句「2026-11-20 C8 后长到 52 = 28 REST + 6 MCP + 18 CLI」的限定语——发版正文不改写历史数，只加边界 |
| `scripts/m10_selfcheck.py` | 两处：① `check_package_entry_count` 的文本探测适配重构后的打包器（清单是否自列的判据改为读 `package_manifest` 函数体）；② **`check_a6_onsite_record` 判据升级**——CLI 现在能按 run 选运行（`runs --run` / `render`），判据从「材料必须说工具不能回看」改为「材料必须写明 runs/render 能力 + 保留『只有已发布那次能渲染』的边界 + 保留当场记录的要求」 |
| `docs/reports/m10-reader-package.md` | A6 的两段「当场记下证据」改写：能力表述更新（runs/render 能回看），边界保留（重跑换掉已发布运行，旧 run 快照不在工作区，当场记录的建议仍然成立） |
| `tests/test_m10_selfcheck.py` | 两条 A6 红测试的破坏方式随判据升级重写（改为抹掉边界/能力表述后必须判红）；11 条全绿 |

### 2.3 测试与文档侧

| 位置 | 改动 |
|---|---|
| `tests/test_run_render.py` | **新文件，15 条测试**：runs 列表/单条记录（含错误取回）/空项目→1/未知项目→2/未知 run→2；render 的输出结构（run.json 字段、包内三报告 + manifest）、报告 JSON/MD 里点名该 run、包过 `verify_package`、未发布 run 拒绝且不留残留、失败 run 拒绝、非空输出目录拒绝、未知项目/run→2、**渲染只读工作区**（数据库 mtime 不变） |
| `README.md` | Quick start 命令清单加 `runs`、`render` 两行 |
| `docs/install.md` | 新增「Runs — one analysis attempt, kept readable」一节：runs/render 的用法、能回看什么、渲染的边界（只有已发布那次） |
| `docs/reports/phase1-execution-report.md` | §2.1 测试文件表补 `test_run_render.py` 一行（行集合核对要求每个测试文件都有行） |
| `docs/reports/README.md` | 索引份数 96 → 97（§6 84 → 85），新增本报告的索引行 |

## 3. 数字对账（本报告自己的数，可复算）

| 数 | 值 | 怎么复核 |
|---|---|---|
| CLI 子命令数 | 13 → **15** | `python -c "from dexatlas.cli.main import app; print(len(app.registered_commands))"` |
| 契约活检静态条数 | 49 → **52**（28 REST + 6 MCP + 18 CLI） | 对 `scripts/verify-public-contracts.py` 数 `check()` 调用点（AST）；契约测试 `test_the_live_contract_script_has_the_number_of_checks_the_materials_state` 自动核对 |
| 两页 how-to-verify 的实跑执行条数 | 48/47 → **51/50** | 52 静态 − 1（server comes up 分支不记）− 1（无 JADX 时 header 检查不记） |
| 新增集成测试 | **15** 条 | `uv run --no-sync pytest tests/test_run_render.py -q` |
| 证据包既有测试 | 32 条全绿 | `uv run --no-sync pytest tests/test_evidence_package.py tests/test_evidence_package_isolation.py -q` |
| 报告索引份数 | 96 → **97** | `ls docs/reports/*.md \| wc -l` 减本页 |

## 4. 本窗口做的 / 留给主会话的

**本窗口做的**：上面 §2 的全部代码、契约、测试与文档改动；门禁自测
（`ruff check`、`ruff format --check`、`mypy`、相关测试模块、
`check-doc-citations.py` drift=0、`check-version-claims.py --base auto`、
`check-unguarded-numbers.py`、`m10_selfcheck.py`、`check-m10-snapshot.py`、
`check-release-numbers.py --offline`）在提交前逐项跑过。

**留给主会话的（合入后统一做）**：

1. **完整重测**（`scripts/refresh-report-figures.py`）——本窗口改了 `src/`、
   `tests/`、`scripts/`，源指纹已变；执行报告的 suite/coverage 数字、README
   徽章、两页 how-to-verify 的 collect 数都描述旧树，4 条
   `tests/test_docs.py` 的测量守卫按设计变红（这与 C17 报告记录的
   「红是闭环本身的样子」相同），重测后由机制自动转绿；
2. **重打 tag**（如需）——版本政策 §6 的流程不变；
3. `docs/status.md` 若引用 CLI 命令数或活检数，合入后按 §3 的表同步。

## 5. 边界与不走之处

- `render` 不重新分析、不启动任何后端：它读工作区、写输出目录，仅此而已
  （有测试盯着工作区数据库的 mtime）。
- 「某一次运行」的**记录**永远可回看（`runs --run`，包括失败/取消的运行）；
  能**渲染**的只有「已完成且仍是已发布」的运行。这个边界写进了命令的
  docstring、错误信息、契约表和 M10 读者包——四处说的是同一件事。
- 公共契约变更是**向后兼容的新增**（规则 5）：没有改任何既有命令、端点、
  退出码的语义；CHANGELOG `[Unreleased]` 显式声明。
