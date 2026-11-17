# 并发测量污染覆盖率 —— 只读审计报告

> **性质：只读审计。** 这份文件由一次**没有改动任何代码、没有运行任何测量**的审计写成。
> 审计日期：2026年11月17日 · 审计对象：主线 `E:\Dexatlas` · 引用基线：commit `8868e30`
>
> **一句话结论：** `.coverage` 是「一个 checkout 一份」的单例文件，而测量脚本对它
> **整体删除**（`REPO_ROOT.glob(".coverage*")`）、**追加写入**（`pytest --cov-append`）、
> **再整体读取**（`coverage json`）——三个动作之间没有任何互斥，于是并发会话会互相吃掉
> 对方的覆盖率数据，最终把一份「只剩自检阶段导入级数据」的残缺文件当成完整测量写进报告。

---

## 0. 审计基线、方法与合规声明

### 0.1 引用行号对应哪一份代码

本文的 `文件:行` 引用**统一对应主线工作树 `E:\Dexatlas` 的文件**，即 commit `8868e30`
（`git worktree list` 显示主线 `E:\Dexatlas` 处于 `claude/m6-level2-verify`，HEAD = `8868e30`）。
审计时该工作树里 `scripts/refresh-report-figures.py` 与 `tests/test_docs.py` **均无未提交改动**
（`git status --porcelain` 只列出 CHANGELOG、README×2、`docs/HANDOVER.md`、`docs/portfolio.md`、
`docs/reports/m10-*.md`、`docs/reports/phase1-execution-report.md`、`docs/roadmap/*`、
`docs/status.md`、`src/dexatlas/__init__.py`），因此「工作树内容」与「`8868e30` 提交内容」一致。

审计工作副本是 `.claude/worktrees/unruffled-mcclintock-3b238b`，基线为 `fbca3d5`——**比主线旧**：
该副本里的 `scripts/refresh-report-figures.py` 还没有 `COVERAGE_PROCESS_START` / `parallel = true`
（主线在 `de41e3e`「测量脚本的 coverage rc 文件改为按进程命名，避免并发测量互相干扰」、
`fc2a3f6`「测量 rc 文件常驻 .scratch，消除子进程读不到配置的窗口」两次提交里加的）。
附录 B 给出旧副本里同一构造的行号，方便在本副本内复核。

### 0.2 合规声明

| 约束 | 实际做法 |
| --- | --- |
| 只读审计 | 全程只用 `Read` / `Grep` / `git show` / `git diff` / `ls` / `awk` / `sed` 读取；除新增本文件外未写入任何文件 |
| 不跑测量 | 未运行 `pytest`、`scripts/refresh-report-figures.py`、`coverage`；未 `uv sync`；未删除或覆盖任何 `.coverage` |
| 不碰共享树 | 未在 `E:\Dexatlas` 下写入、未执行任何脚本；只读取其文件与 git 对象 |
| 无对外动作 | 未 push、未 tag、未建分支；未写任何 key/secret |
| 未跑 `check-doc-citations.py` | 本副本**没有 `.venv`**（`uv sync` 会写满系统盘、并可能干扰正在进行的重测量），因此无法运行 pytest/ruff/mypy。替代核对方式见 §0.3 |

### 0.3 行号是如何核对的（`check-doc-citations.py` 的替代方案）

`scripts/check-doc-citations.py` 需要 import 本仓库的模块（要在 `.venv` 里跑），本副本不具备条件。
改用的替代核对：把每条引用写成一个 `文件:行` 对，用 `git show 8868e30:<路径> | sed -n '<行>p'`
把那一行原文打印出来，与本文的描述逐条对读。核对结果记录在 §8.4。
本文引用的是 `scripts/` 与 `tests/` 下的文件，而 `check-doc-citations.py` 的检查对象是文档里指向
`src/` 的符号引用（CLAUDE.md 第 4 条：「After changing anything under `src/`」），因此本文不新增
任何指向 `src/` 的 `file:line` 引用，不影响该检查器对本文件的判定。

---

## 1. 结论先行

1. **污染机制（已证实）**：测量脚本把覆盖率数据写进**固定路径 `E:\Dexatlas\.coverage`**，
   路径由 cwd 决定——所有子进程都以 `cwd=REPO_ROOT` 启动（`scripts/refresh-report-figures.py:238`），
   而仓库里**从未设置 `COVERAGE_FILE`**（全仓 grep 只在 coverage 自己的文档里命中，
   `E:\Dexatlas\.venv\Lib\site-packages\coverage\cmdline.py:101`、`:113`、`:125`），
   `tests/conftest.py:30-35` 重定向的是 `TMPDIR`/`TEMP`/`TMP`（临时目录），**不是**覆盖率数据文件。
   因此「同一个 checkout 里的多个会话」= 「同一个 `.coverage` 文件」。

2. **谁删谁的数据**：脚本在测量开始前执行 `discard_stale_coverage()`（`:1107` 调用，
   `:293-311` 定义），它 `REPO_ROOT.glob(".coverage*")` 后 `unlink()`（`:306-310`）——
   **删掉的不只是 `.coverage`，还包括 `parallel = true` 模式下每个进程各自的
   `.coverage.<host>.<pid>.<rand>` 分片**。会话 B 的这一步会直接抹掉会话 A 正在累积的分片，
   也会抹掉 A 已经 `coverage combine` 出来的合并结果。

3. **为什么 `tests.total` 正确而 `coverage.pct` 错误**：测试计数来自**本进程捕获的 pytest stdout**
   （`:290` `read_outcome` → `Outcome(counts=...)`），在内存里，与磁盘上的 `.coverage` 无关；
   覆盖率数字来自**磁盘上的共享文件**（`:316` `coverage json -o -`）。两者数据来源不同，
   所以并发只会污染后者。

4. **为什么现有护栏一个都没拦住**：现有判据全部是**内部自洽型**，对「分子被换掉」免疫——
   指纹只哈希源码与测试（`:509-535`、`:487-506`），不覆盖 `.coverage` 数据本身；
   模块集合检查（`:1115-1122`）因为 coverage 的 `source = dexatlas` 语义（`:126-129`）
   **必然相等**（未执行的文件也进报告）；`tests/test_docs.py:704-709` 只断言「per-file 之和 = 总数」，
   `tests/test_docs.py:780-809` 只断言**分母**与树一致——**没有一个断言检查分子**。

5. **污染态的现场（主线工作树，当前仍是污染态）**：`docs/reports/phase1-execution-report.md:77`
   现为 `35.4%（2699/7631）`，同文件 `:76` 的 `tests.total=1584` 是对的；
   弱模块表从 HEAD 的 10 行膨胀到 **52 行**；`tools/androguard/worker.py` 变成 **0.0%（112/112）**。
   同一个数字还污染了 `docs/status.md:24` 与 `README.md:13` 的覆盖率徽章
   （徽章值由同一次测量算出并写回：`scripts/refresh-report-figures.py:1261-1271`、`:1305-1309`；
   `README.zh-CN.md` **没有**覆盖率徽章——`apply_badges()` 只替换已存在的徽章，`:801-833`——
   所以它未被污染）。

6. **防呆方案优先级**（详见 §5）：
   **P0 每次运行独占 `COVERAGE_FILE`**（数据文件从 checkout 级降到运行级）→
   **P1 checkout 级互斥锁**（并发直接拒绝）→
   **P2 覆盖率相对阈值的写入闸门 + 指纹/计数/覆盖率签名绑定**（防「残缺数据被当成完整」）
   → **P3 独立的 `--check` 只读校验模式** →
   **P4 不改代码的操作规程**（§6，今天就能用）。
   **P0/P1/P3/P4 都不改变测量语义**；**P2 的闸门只增加一个「拒绝写入」的条件**，
   不会让「部分运行」被写成完整运行（见 §5.4 的逐条判定）。

---

## 2. 污染机制：脚本如何产生与消费覆盖率

### 2.1 数据文件路径由谁决定

| 环节 | 事实 | 出处 |
| --- | --- | --- |
| 工作目录 | 所有子命令以 `cwd=REPO_ROOT` 启动 | `scripts/refresh-report-figures.py:238` |
| `REPO_ROOT` | 脚本所在目录的父目录 = checkout 根 | `scripts/refresh-report-figures.py:86` |
| `COVERAGE_FILE` | **项目内从未设置**（全仓 grep 无命中） | 仓库全局；coverage 自身读取点 `E:\Dexatlas\.venv\Lib\site-packages\coverage\config.py:708` |
| 默认数据文件 | coverage 7.16.2 的默认值是 cwd 下的 `.coverage` | `E:\Dexatlas\.venv\Lib\site-packages\coverage\config.py:708`（`env_data_file = os.getenv("COVERAGE_FILE")`，未设即默认） |
| `tests/conftest.py` 的重定向 | 改的是 `TMPDIR`/`TEMP`/`TMP` → `<repo>/.scratch/tmp`，**与数据文件无关** | `tests/conftest.py:30-35` |
| coverage 版本 | 7.16.2 | `E:\Dexatlas\.venv\Lib\site-packages\coverage\version.py`（`version_info = (7, 16, 2, "final", 0)`） |

**结论**：`.coverage` 的实际路径 = **cwd = checkout 根**，同一 checkout 的所有会话指向同一个文件。

### 2.2 三个测量阶段（谁写、怎么写）

| 阶段 | 函数 | 命令 | 对 `.coverage` 的动作 |
| --- | --- | --- | --- |
| ① 代码测试 | `measure_code_tests()` `:387-433` | `coverage run --rcfile=<.scratch/coveragerc-measure.ini> -m pytest -k "not test_execution_report and not test_status_page"` `:416-430`，随后 `coverage combine --rcfile=<同一 rc>` `:431` | rc 里 `parallel = true`（`:126-129`）→ **每个进程各写一个 `.coverage.<host>.<pid>.<rand>` 分片**；`combine` 把分片合并成 `.coverage` 并删除分片 |
| ② 报告自检 | `measure_report_checks()` `:435-451` | `pytest --cov=dexatlas --cov-append -k test_execution_report` `:449` | **pytest-cov**，`--cov-append` → **向 cwd 的 `.coverage` 追加**；pytest-cov 用的是默认 coverage 配置，**不读** ① 的 rc 文件 |
| ③ 状态页自检 | `measure_status_checks()` `:454-474` | `pytest --cov=dexatlas --cov-append -k test_status_page` `:472` | 同上，追加 |
| 读取 | `read_coverage()` `:314-334` | `coverage json -o -` `:316` | **整体读取** cwd 的 `.coverage`；不带 `--rcfile`、不带 `--data-file` |
| 预先清场 | `discard_stale_coverage()` `:293-311` | `REPO_ROOT.glob(".coverage*")` → `unlink()` `:306-310` | **删除 `.coverage` 与全部分片**，在测量开始前执行（`:1107`） |

补充事实：
- `COVERAGE_PROCESS_START` **只在阶段 ① 的 `env` 里设置**（`:414-415`，指向
  `.scratch/coveragerc-measure.ini`），阶段 ②③ 与 `coverage json` 都没有这个环境变量。
- 阶段 ②③ 的 pytest-cov **不受 `parallel = true` 影响**：仓库里没有 `.coveragerc`、
  没有 `setup.cfg` / `tox.ini`，`pyproject.toml` 也没有 `[tool.coverage.*]` 段，
  所以 coverage 走的是「默认值」这一支（`E:\Dexatlas\.venv\Lib\site-packages\coverage\config.py:700-712`
  的查找顺序），rc 文件根本没被读到。
  但 **`--cov=dexatlas` 仍然把 `source` 设成了 `dexatlas`**（`:449`、`:472`），
  于是「未执行的模块也进报告、计入分母」这条性质在阶段 ②③ 里同样成立——
  这正是污染态里分母（7631）正确、分子（2699）错误的原因。
- 仓库里**没有** `coverage erase`（全仓 grep 无命中），删除是靠 Python 的 `unlink()` 完成的；
  仓库里**有** `coverage combine`（`:431`），**没有** `--parallel` 命令行模式的使用。

### 2.3 完整性的判据在哪几行（以及它为什么拦不住这次污染）

脚本有两道「拒绝写入」的闸门：

1. **失败闸门**：`:1124-1130` —— `code.failures` 非空则直接 `return 1`，报告一个字节都不动。
2. **完整性闸门**：`:1138-1146` —— 判据是**「这次跳过的测试身份集合」是否等于上次记录的集合**
   （`complete = set(code.skipped) == set(recorded_tests)`；旧记录没有身份时退化为比较跳过数 `:1140-1144`）。
   不完整时走 `:1210-1229`：**保留上一次的 `coverage` / `suite` / `source_fingerprint`**，
   只更新其余部分并打印 `warn_partial()`（`:1340-1352`）。

**为什么这次没拦住**：跳过集合来自阶段 ① 的 pytest 输出（内存），阶段 ① 本身**确实完整跑完了**，
跳过集合与上次一致 → `complete = True` → 脚本进入 `converge()` 并写入。
**完整性判据检查的是「测试有没有跑」，不是「覆盖率数据是否完整」**——
而覆盖率的分子来自一个**别的进程可能已经改过的文件**。

### 2.4 收敛循环如何「采纳」被污染的数据（关键）

`converge()` `:940-1020` 的循环是本次事故的放大器：

```
972  record = build_record(coverage, ...)      # coverage = 第一次读取（:1109）
973  candidate = render_or_fail(text, record)   # 先用「第一次读到的覆盖率」渲染候选
979  checks       = measure_report_checks(...)  # 阶段 ②：pytest --cov-append → 追加写 .coverage
981  status_checks= measure_status_checks(...)  # 阶段 ③：追加写 .coverage
984  new_coverage = read_coverage()             # 第二次读取 .coverage
988-993 if new_suite == suite and new_coverage == coverage and ...: → 判定收敛并返回
1003 suite, coverage = new_suite, new_coverage  # ★ 不相等 → 采纳「新的」覆盖率
1005-1009 record = build_record(coverage, ...)  # 用新覆盖率重建记录
1008 candidate = render_or_fail(text, record)   # 用新覆盖率重新渲染候选
```

`:1003` 的语义是「测量结果变了 → 更新数字」。在并发场景里，「变了」既可能是**代码真的变了**，
也可能是**别人的进程换了数据文件**——脚本把两者当成同一件事，于是**主动把被污染的覆盖率
写进了候选报告**，并在下一轮自我检查中确认「这份报告与这份数据自洽」，最终落盘。

### 2.5 污染时序（推断，附依据）

> **推断**：事故的具体时序是——会话 B 的 `discard_stale_coverage()`（`:1107` → `:306-310`）
> 落在会话 A 的阶段 ① 完成（`coverage combine` 已写出 `.coverage`）之后、A 的阶段 ②③ 之前；
> 于是 A 的阶段 ②（`pytest --cov-append`，`:449`）面对的是一个**已不存在的** `.coverage`，
> pytest-cov 新建了一个**只含自检阶段数据**的 `.coverage`；A 在 `:984` 第二次读取时读到的
> 就是这份残缺数据，`:1003` 采纳它，`:1008` 把它渲染进候选报告。

**推断依据**（都能在只读范围内复核）：

- 污染态的**弱模块表有 52 行**（HEAD 只有 10 行），且几乎所有模块都落在 **0%–35%** 区间，
  而不是「某些模块缺失」——这正是「模块被 import 但函数没被调用」的形态
  （pytest **收集**阶段会 import 全部测试模块，测试模块再 import `dexatlas` 的模块）。
- `tools/apktool/adapter.py` 在污染态是 `18.3%（259/317 未覆盖）`，即**恰好 58 行被执行**；
  而 `tests/conftest.py:16-17` 正好 `from dexatlas.tools.apktool.adapter import ApktoolBackend`
  ——**只 import、不调用**该模块，正是 58 行模块级语句的形态。
- `tools/androguard/worker.py` 污染态 `0.0%（112/112）`：该模块是**子进程**跑的
  （`scripts/refresh-report-figures.py:117-125` 的说明），只有阶段 ① 的
  `COVERAGE_PROCESS_START` + `parallel = true` 才会记录它；阶段 ②③ 不会起 worker。
- `coverage.total = 7631` 与 HEAD 完全一致：coverage 的 `source`（阶段 ① 来自 rc 的 `:128`，
  阶段 ②③ 来自 `--cov=dexatlas`，`:449`、`:472`）让**未被执行的模块也进报告**
  （计入分母、分子为 0），所以「分母对、分子错」是必然的。
- `tests.total = 1584` 正确：它来自阶段 ① 的内存输出（`:290`），不经过 `.coverage`。

**待核项**：上述「58 行 = 模块级语句数」需要用 coverage 自己的 parser 复核，
本审计按硬约束未运行 `coverage` 命令。复核方式见 §8.3 的 T-1。

---

## 3. 共享面：哪些入口会让两个进程写到同一个 `.coverage`

| # | 共享入口 | 共享的东西 | 并发时的后果 |
| --- | --- | --- | --- |
| S1 | **同一个 checkout 的同一 cwd** | `REPO_ROOT`（`:86`）+ `cwd=REPO_ROOT`（`:238`） | 所有会话写同一个 `E:\Dexatlas\.coverage` |
| S2 | **同一个 `COVERAGE_FILE`** | 项目从未设置 → 恒等于 cwd 默认值 | 同上；一旦有人设了它，全局再共享一次 |
| S3 | **`discard_stale_coverage()` 的 glob**（`:306`） | `.coverage` + **全部分片** `.coverage.*` | B 删掉 A 的合并结果；B 删掉 A 正在累积的分片 → A 的 `combine`（`:431`）静默丢数据 |
| S4 | **`pytest --cov-append`**（`:449`、`:472`） | 追加写同一个 `.coverage` | 追加语义是**合并**，但前提是文件里已有数据；文件若被 S3 删掉，就变成**新建一份只含自检数据**的文件 |
| S5 | **`coverage combine`**（`:431`） | 写 `.coverage`，删分片 | combine 会**捡起目录里所有** `.coverage.*` 分片并删除它们 → 可能吃掉别的会话的分片 |
| S6 | **同一个 venv** | `E:\Dexatlas\.venv`（`uv sync` 是 checkout 级） | 只影响「用哪个解释器」，不额外制造数据文件；但同一 venv 也意味着同一套 coverage 版本，行为一致 |
| S7 | **`tests/conftest.py` 的临时目录重定向**（`:30-35`） | `TMPDIR`/`TEMP`/`TMP` → `<repo>/.scratch/tmp` | **不是** `.coverage` 的共享面；它把临时文件也收进 checkout 内（`.scratch/` 已被 `.gitignore:89` 忽略） |
| S8 | **`.scratch/coveragerc-measure.ini`**（`:411-413`） | **固定的 rc 文件路径** | 两个会话会**互相覆盖同一份 rc 文件**（内容相同则无害，内容不同则子进程读到的配置取决于时序）——这是 S8 之外唯一被写坏的共享文件 |
| S9 | **报告 / status / README 徽章**（`:1305-1309`） | `docs/reports/phase1-execution-report.md`、`docs/status.md`、`README.md` | 并发会话会互相覆盖文档；数字取自各自读到的 `.coverage`，谁最后写谁赢（`README.zh-CN.md` 无覆盖率徽章，不在其列，见 §1.5） |
| S10 | **不同 worktree** | 各自的 `REPO_ROOT` | **天然隔离**：worktree 有自己的 checkout 根 → 自己的 `.coverage`、自己的 `.scratch`。风险只存在于「同一 checkout 的多会话」 |

**结论**：同一 checkout 内**没有任何互斥**。S3 是破坏性最大的一个（删除范围过大），
S4+S5 是「静默合并/静默新建」，S9 是最终落盘。三者叠加即产生事故。

**为什么 `tests.total` 对而 `coverage.pct` 错**（再次确认，见 §1.3）：数据来源分离——
测试计数在内存（`:290`），覆盖率在磁盘（`:316`）。磁盘那份是共享的，内存那份不是。

---

## 4. 判别性证据：完整性判据与指纹到底是什么

### 4.1 「完整性判据」= 跳过测试的身份集合

- 出处：`scripts/refresh-report-figures.py:1138-1146`（`recorded_tests` / `skipped` / `complete`）。
- 语义：一次测量「完整」= **这次没跑的测试，与上次记录里没跑的测试，是同一批**（`:1146`）。
- 配套：**失败即拒绝写入**（`:1124-1130`）；不完整则**保留旧覆盖率**（`:1223-1228`）。
- **它管不到的事**：覆盖率数据文件本身的完整性。判据与被污染的量在不同的数据通道上。

### 4.2 「指纹」= 源码树的哈希

- 出处：`source_fingerprint()` `:509-535`；参与哈希的文件集合见 `fingerprint_files()` `:487-506`：
  - `src/dexatlas/**/*.py`（`:499-501`，`SOURCE_ROOT` 定义于 `:101`）
  - `tests/**/*.py`（`:499-501`，`TESTS_ROOT` 定义于 `:104`）
  - `FINGERPRINT_FILES = ("pyproject.toml", "scripts/refresh-report-figures.py")`（`:110`，`:502-505`）
  - 换行归一化后再哈希（`:532`，`replace(b"\r\n", b"\n")`）——理由写在 `:522-526`。
- 指纹写进报告的机器可读记录（`build_record()` `:653-691`，`"source_fingerprint": source_fingerprint()` `:673`），
  由 `tests/test_docs.py:696-701` 断言与当前树一致。

### 4.3 为什么指纹能发现「代码变了」，却发现不了「数据被并发破坏」

1. **指纹的对象是源码，不是数据**：`:487-506` 收集的文件里**没有** `.coverage`，
   也没有任何测量产物的哈希（`.scratch/` 被 `.gitignore:89` 忽略，本来也不该进指纹）。
   两次在**同一棵源码**上跑出的指纹**完全相同**，无论覆盖率数据是 93.2% 还是 35.4%。
2. **指纹在测量开始时计算**（`:1079` 与 `:673`），与 `.coverage` 的读取（`:1109`、`:984`）之间没有因果关系。
3. **`tests/test_docs.py` 的四道覆盖率断言都绕开了分子**：
   - `tests/test_docs.py:696-701`：指纹相等（源码维度）；
   - `tests/test_docs.py:704-709`：per-file 之和 = 总数（**内部自洽**，污染数据同样自洽）；
   - `tests/test_docs.py:780-809`：记录的**分母** = 用 coverage 自己的 parser 重算的树内语句数
     （**分母正确**，污染只改分子）；
   - `tests/test_docs.py:848-874`：报告里的弱模块表 == 用记录里的数据重算的弱模块表
     （**自洽**：污染数据的弱模块表就是从污染数据生成的）。
   → **四道断言对「分子被换掉」全部免疫**，这就是污染能一路走到落盘的原因。

### 4.4 「已提交的覆盖率是错的」的可验证判据

按判别力从强到弱（都可只读复核）：

| 判据 | 污染态应满足 | 干净态 | 怎么复核 |
| --- | --- | --- | --- |
| **D1 弱模块表规模** | 52 行（几乎整个包） | 10 行 | 数 `<!--fig:coverage.weak_modules-->` 块里 `^| \`` 的行数 |
| **D2 模块覆盖率的分布形态** | 绝大多数模块落在 0–35% | 弱模块集中在 58%–90%，其余 ≥90% | 看表里每行的 pct 列 |
| **D3 分子/分母关系** | 分子 2699 远低于历史水位 | 分子 7109/7631 | 与上一条记录的分子比较 |
| **D4 `worker.py` 归零** | 0.0%（112/112） | 72.3%（31/112 未覆盖） | 该模块只在阶段 ① 的子进程测量里被记录（`:117-125`），归零 = 阶段 ① 的数据丢失 |
| **D5 已知被充分测试的模块** | `core/pipeline.py` 18.2%、`agent/orchestrator.py` 18.3% | 90%+ | 完整测量里核心模块必然高覆盖 |
| **D6 per-file 与弱模块表互相矛盾** | 无矛盾（同一份数据渲染） | 无矛盾 | 这一条**不能**用来判别，见下 |

**重要提醒**：D6 说明「报告内部矛盾」**不是**可用判据——污染态的报告是**内部完全自洽**的
（分母对、per-file 加总对、弱模块表由同一份数据生成）。**只有与「外部参照物」比较才有判别力**：
参照物 = 上一次记录的覆盖率、树内已知被充分测试的模块、阶段 ① 才产生的子进程模块。

---

## 5. 防呆方案（五个方案 + 评估）

### 5.1 方案 P0：每次运行独占 `COVERAGE_FILE`（**推荐第一优先**）

**做法**：脚本启动时生成唯一 `run_id`，把数据文件指到本次运行专属的路径，例如
`<repo>/.scratch/coverage/<run_id>/.coverage`，并通过两处生效：
① 在 rc 文件里写 `data_file = ...`；② 在传给所有子进程的 `env` 里设 `COVERAGE_FILE=<该路径>`
（coverage 读 `COVERAGE_FILE` 的位置：`E:\Dexatlas\.venv\Lib\site-packages\coverage\config.py:708`）。
阶段 ②③ 的 pytest-cov 也会认这个环境变量（`--cov-append` 的目标文件随之改变）。
测量结束后只把**本次运行自己**的分片合并。

**为什么有效**：数据文件从「checkout 级单例」变成「运行级」，S1–S5 的共享面同时消失；
`discard_stale_coverage()` 只需清理**自己 run_id 目录**（或干脆不清理，因为路径唯一）。

**是否改变测量语义**：**否**。同一棵树、同一套测试、同一份 coverage 配置（`parallel = true`、
`source = dexatlas`、`:126-129`），只是数据落到不同文件；合并顺序与结果不变。

**是否会让「部分运行」被写成完整运行**：**否**。完整性判据（`:1138-1146`）与失败闸门
（`:1124-1130`）原样保留；而且本方案**只解决数据文件隔离**，不解决「残缺数据被当成完整」——
需要 P2 配合才能完全闭合（见 §5.5 的组合建议）。

**代价**：需要把 `COVERAGE_FILE` 同时传给阶段 ②③ 与 `coverage json`（当前只在阶段 ① 的 env 里设了
`COVERAGE_PROCESS_START`，`:414-415`）；`coverage json` 与 `coverage combine` 需要显式指向本次的数据文件。

### 5.2 方案 P1：checkout 级互斥锁（**改动最小、语义最清楚**）

**做法**：脚本启动时用 `O_CREAT | O_EXCL` 原子创建 `<repo>/.scratch/measure.lock`，
内容写 pid / 主机名 / 启动时间；创建失败即**拒绝运行**并退出（打印「另一个测量正在进行」）；
结束时删除。锁文件里带 pid，启动时若发现锁存在但 pid 已不存在，视为陈旧锁并接管。

**为什么有效**：把「一个 checkout 一次只允许一次测量」这条约定**变成代码事实**，
直接消灭 S3/S4/S5/S9 的并发。

**是否改变测量语义**：**否**。它不碰任何测量逻辑，只决定「能不能开始测」。

**是否会让「部分运行」被写成完整运行**：**否**。它只减少并发，不放宽任何判据。

**注意**：worktree 之间天然隔离（S10），所以锁放在 `<repo>/.scratch/` 即可——
每个 worktree 一把锁，正好对应「一个 checkout 一次一次测量」。

**代价**：需处理陈旧锁（进程被 `taskkill` 杀掉后锁残留——这正是事故里提到的场景）。

### 5.3 方案 P2：写入闸门 + 签名绑定（**补上「残缺数据被当成完整」这个洞**）

**做法**（三件事，可分别落地）：

1. **相对阈值闸门**：与上一次记录的覆盖率比较，跌幅超过阈值（例如 5 个百分点）时
   **拒绝写入**并要求显式 `--force`。理由：本仓库的覆盖率长期在 93% 附近（见 §7），
   跌到 35% 显然是测量出了问题，而不是代码变差了。阈值写成**相对上一次记录**，
   而不是绝对值，避免随代码演进而漂移。
2. **弱模块表规模闸门**：若本次弱模块表行数超过上一次记录的 N 倍（例如 2 倍），
   拒绝写入并提示「疑似只测了导入路径」。
3. **签名绑定**：把 `coverage.files` / `missing` / `statements` 与 `suite`（passed/skipped/failed）
   与 `source_fingerprint` 一起哈希成一个 `measurement_signature`，写进记录
   （`build_record()` `:653-691`），并由 `tests/test_docs.py` 断言
   「签名 == 由记录中的各项重算出的签名」。这一条**只是防篡改/防半写**，
   **不直接**发现数据被换掉（污染数据同样能算出自洽签名）——真正有判别力的是 1、2。

**是否改变测量语义**：**否**（只增加「拒绝写入」的条件，不改变测什么、怎么算）。
**是否会让「部分运行」被写成完整运行**：**否，而且方向相反**——它专门拦「不完整的数据被写成完整」。

**代价**：阈值需要调；`--force` 必须留，否则真出问题时无法落盘。

### 5.4 方案 P3：独立的只读校验模式（`--check` 的强化）

**现状**：`--check` 已存在（`:1294-1303`），但它**只保证不写报告**——
它**照样会跑完整测量、照样会执行 `discard_stale_coverage()`（`:1107`）、照样会写 `.coverage`**。
也就是说，**在一场并发测量里跑 `--check` 仍然会破坏别人的数据**。

**做法**：给脚本加一个真正的**只读**模式（建议 `--verify` 或 `--selftest`）：
只读取**已存在的** `.coverage`（或指定的数据文件）与报告记录，做一致性核对
（分母 vs 树、per-file 加总、弱模块表、指纹、suite 计数、签名），**不跑 pytest、不删文件、不写文件**，
以退出码表示是否一致。

**是否改变测量语义**：**否**（不测）。
**是否会让「部分运行」被写成完整运行**：**否**（不写）。
**价值**：CI 与「发版前检查」可以用它做一次零副作用的核对；也是 §6 规程第 4 步的自动化形态。

### 5.5 方案 P4：不改代码的操作规程（见 §6）

**是否改变测量语义**：**否**。**是否会让「部分运行」被写成完整运行**：**否**。

### 5.6 组合建议

- **最小可用组合（今天就能上）**：P4（规程）+ P1（锁）。
- **根治组合**：P0（数据文件隔离）+ P2（写入闸门）。
  P0 解决「互相破坏」，P2 解决「破坏了还写进去」；两者都做才闭环。
- **P3 独立于其余三者**，随时可加。

---

## 6. 不改代码的立即操作规程（多窗口并行期）

**适用场景**：主线正在发版测量，或任何「多个会话可能在同一 checkout 里跑测量」的时期。

| 步骤 | 动作 | 判据 |
| --- | --- | --- |
| 1 | **指定唯一测量窗口**：由**一个**会话负责测量，其余会话一律不跑 `scripts/refresh-report-figures.py`（连 `--check` 也不要跑，见下） | 口头/任务清单里写明「测量负责人：<会话名>」 |
| 2 | **测量前查进程**：确认没有别的测量在跑 | `tasklist //FI "IMAGENAME eq python.exe"` 看是否有 pytest/coverage 进程；发现残留按下面的方式清 |
| 3 | **测量前记录基线**：把当前报告里的 `coverage.pct`、`coverage.covered`、`coverage.total`、`tests.total` 抄下来（或 `git show HEAD:docs/reports/phase1-execution-report.md`） | 有了基线，事后才能判断数字是不是「跳变」 |
| 4 | **测量后核对四件事**（不要只看百分比） | ① `coverage.pct` 与基线相差不超过几个百分点；② **弱模块表的行数**与基线同量级（见 §4.4 的 D1）；③ `tools/androguard/worker.py` 不是 0.0%（D4）；④ `tests.total` 与 `tests.fast + tests.slow` 相等且与 `--collect-only` 的结果一致 |
| 5 | **核对 `.coverage` 的 mtime 与大小**：测量刚结束时它应当是刚被写过的 | `ls -la .coverage`（mtime 应当是刚刚；明显早于测量开始时间 = 读到了别人的旧数据） |
| 6 | **数字写入后立刻做一次 git diff 复核**：`git diff -- docs/reports/phase1-execution-report.md docs/status.md README.md`，逐行看被改掉的数字 | 只应有「测试数增加」「覆盖率微调」这类合理变化；出现覆盖率暴跌 = 污染 |
| 7 | **污染了怎么办**：**清场重测**——删掉 `.coverage*`，确保没有别的测量在跑，重跑一次；不要手工把数字改回去 | 手工改的数字既没有指纹也没有记录，`tests/test_docs.py` 会失败 |
| 8 | **停后台任务**：TaskStop 杀不死 uv 的 python 孙进程，必须连树杀 | `taskkill //PID <root-pid> //T //F`，事后确认 `tasklist` 里没有残留的 python.exe |

**补充（比第 1 步更彻底的办法）**：**用不同的 worktree 测量**。
`REPO_ROOT` 随 checkout 走（`:86`），不同 worktree 的 `.coverage`、`.scratch`、venv 都不同（S10），
天然不会互相污染。代价是每个 worktree 需要自己的 `.venv`（CLAUDE.md「Running it」），
且指纹会因 worktree 路径不同而不同——但指纹只哈希**文件内容**（`:530-532`），
不含路径，所以同一 commit 在不同 worktree 的指纹相同。**这一点是可核对的**。

---

## 7. 存量风险核查：已提交的数字自洽吗

### 7.1 三份「已提交/在树」的数字

| 位置 | `coverage.pct` | covered/total | `tests.total` | 弱模块表行数 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 主线 `HEAD`（`8868e30`） | 93.2% | 7109/7631 | 1584（1437+147） | 10 | **自洽** |
| 主线**工作树**（当前，污染态） | **35.4%** | **2699/7631** | 1584（1437+147） | **52** | **污染** |
| 本审计工作副本（`fbca3d5`） | 93.2% | 6938/7445 | 1515（1368+147） | 10 | **自洽** |

### 7.2 逐项自洽核对

**主线 HEAD（干净态）**：
- `7109 / 7631 = 93.16%` → 四舍五入 **93.2%** ✓（`percent()` `:694-696`，一位小数）
- `1437 + 147 = 1584` ✓
- 弱模块表 10 行，每行 `未覆盖 / 总行数` 与 pct 互相吻合，例如
  `tools/androguard/worker.py` 72.3% ← `(112-31)/112 = 72.32%` ✓；
  `tools/apktool/adapter.py` 93.1% ← `(317-22)/317 = 93.06%` ✓
- **判定：自洽。**

**主线工作树（污染态）**：
- `2699 / 7631 = 35.37%` → **35.4%** ✓（**数字之间自洽，但整体是错的**）
- `1437 + 147 = 1584` ✓（测试数正确，与覆盖率来自不同通道，见 §1.3）
- 弱模块表 52 行；每行内部亦自洽（例如 `tools/apktool/adapter.py` 18.3% ← `(317-259)/317 = 18.30%` ✓）
- **D1（52 行 vs 10 行）异常** ✓；**D4（`worker.py` 0.0%，112/112）异常** ✓；
  **D2（绝大多数模块 0–35%）异常** ✓；**D3（分子 2699 vs 7109）异常** ✓
- **判定：污染态。** 且它已扩散到 `docs/status.md:24`（`一方代码覆盖率 | 35.4%`）与
  `README.md:13` 的覆盖率徽章（`coverage-35.4%25-brightgreen.svg`）
  ——这两处由脚本同一次运行写入（`:1256-1269`、`:1305-1309`）。
  `README.zh-CN.md` 没有覆盖率徽章，**未受污染**。

**本审计工作副本（`fbca3d5`）**：
- `6938 / 7445 = 93.19%` → **93.2%** ✓；`1368 + 147 = 1515` ✓；
  弱模块表 10 行，`tools/apktool/adapter.py` 93.1% ← `(317-22)/317` ✓
- **判定：自洽，且与主线 HEAD 的 93.2% 同量级（分母不同是因为树不同：7445 vs 7631）。**

### 7.3 当前状态的一句话结论

> **主线工作树当前处于污染态**：`docs/reports/phase1-execution-report.md:77`、
> `docs/status.md:24`、`README.md:13` 三处的覆盖率都是 `35.4%`；
> **但这些是未提交的改动**（`git diff` 可见），`HEAD`（`8868e30`）里的 93.2% 是干净的。
> 也就是说：**仓库里「已提交」的覆盖率数字没有被污染**；污染只存在于主线的**工作树**中，
> 尚未被提交。本审计按硬约束**没有修复它**，只做核对。

### 7.4 「真正的风险」不在这一次的数字

即使主线这次重测完、把 93.2% 重新写回，**机制没变**：只要同一 checkout 里还有两个会话
会跑测量，下一次还会发生同样的事。而现有护栏（指纹、模块集合检查、`test_docs.py` 的四道断言）
**一个都不会报错**——它们对「分子被换掉」免疫（§4.3）。
**这才是本次审计真正要交付的东西。**

---

## 8. 建议改动清单（本窗口不改代码，仅列建议）

> 按 CLAUDE.md 第 1 条：每个修复都必须配一个**去掉修复就变红**的回归测试。
> 下表的「回归测试」列给出该测试应有的形态（先红后绿）。

| # | 文件 | 拟改动内容 | 预计影响面 | 需要新增回归测试（红→绿） |
| --- | --- | --- | --- | --- |
| C1 | `scripts/refresh-report-figures.py` | 引入每次运行的唯一数据文件：生成 `run_id`，在 rc 里写 `data_file`、在 env 里设 `COVERAGE_FILE`，阶段 ②③ 与 `coverage json`/`combine` 一并指向它；`discard_stale_coverage()` 改为只清理**本次 run_id 目录**，不再 `glob(".coverage*")` | 测量脚本自身；`tests/test_docs.py` 的记录断言不受影响 | **红**：在临时目录里模拟「并发两次测量」，断言两次运行产出的数据文件路径不同、互不覆盖；**绿**：加了唯一数据文件后通过，去掉后第二次运行覆盖第一次的数据文件而变红 |
| C2 | `scripts/refresh-report-figures.py` | 新增 checkout 级互斥锁：原子创建 `.scratch/measure.lock`（含 pid/主机/时间），已存在则拒绝运行；处理陈旧锁 | 测量脚本自身；不影响并发之外的流程 | **红**：在同一 checkout 起第二个实例，断言它以明确信息拒绝运行（退出码非 0、报告不被触碰）；**绿**：加锁后通过，去掉锁后第二个实例正常跑起来而变红 |
| C3 | `scripts/refresh-report-figures.py` | 写入闸门：与上一次记录的覆盖率比较，跌幅超阈值时拒绝写入并提示 `--force`；弱模块表行数相对上一次异常增长时同样拒绝 | 报告写入路径；`--check` 的语义需同步 | **红**：构造一份「覆盖率比上次低 60 个百分点」的记录，断言脚本拒绝写入且报告文件字节不变；**绿**：加闸门后通过 |
| C4 | `scripts/refresh-report-figures.py` | `build_record()`（`:653-691`）增加 `measurement_signature`：对 `coverage` + `suite` + `source_fingerprint` 求哈希，写进记录 | 记录的 schema 会变（当前 `"schema": 4`，`:665`）→ **属于公开契约变更，按 CLAUDE.md 第 5 条必须显式版本化并写进 CHANGELOG** | **红**：篡改记录里的 coverage 或 suite 任意一项，断言签名不匹配而测试失败；**绿**：加签名后通过 |
| C5 | `tests/test_docs.py` | 断言 `measurement_signature` == 由记录各项重算的签名；并新增「弱模块表规模相对上次记录」的合理性断言 | 文档自检套件；`--cov-append` 阶段会跑到这些测试 | **红**：把记录里的覆盖率数字改小而不改签名，断言测试失败；**绿**：加签名断言后通过 |
| C6 | `scripts/refresh-report-figures.py` | 新增真正的只读校验模式（`--verify`）：不跑 pytest、不删 `.coverage`、不写文件，只核对记录与树的一致性，退出码表示结果 | 新增子命令；`--check` 的语义需在帮助文本里区分 | **红**：在有并发测量进行时运行 `--verify`，断言它不修改 `.coverage` 的 mtime/内容、不删任何 `.coverage*`；**绿**：实现后通过 |
| C7 | `docs/status.md` / `docs/roadmap/ROADMAP.md` / `CLAUDE.md` + `AGENTS.md` | 把「一个 checkout 一次只允许一次测量」写成明文约定（CLAUDE.md 与 AGENTS.md 是同一文件，`tests/test_docs.py` 保持二者一致） | 文档；`AGENTS.md` 必须同步（CLAUDE.md 首段） | **红**：`tests/test_docs.py` 里已有 CLAUDE.md/AGENTS.md 一致性检查，去掉其一的内容时变红；**绿**：同步后通过 |
| C8 | `docs/reports/phase1-execution-report.md` §6（测量机制说明） | 补一句：覆盖率数据文件是 checkout 级共享资源，并发测量会互相污染；引用本报告 §2 的机制 | 报告正文；`<!--fig:...-->` 标记不受影响 | 该节是手写内容，不涉及数字，无需新测试；但改动后须跑 `scripts/check-doc-citations.py`（`docs/` 不在指纹内，改文档不需要重测量） |

### 8.1 建议的落地顺序

1. **C7**（规程写进文档）→ 立刻生效，零风险。
2. **C2**（互斥锁）→ 改动最小，直接消灭并发。
3. **C1**（唯一数据文件）→ 根治共享面。
4. **C3 + C4 + C5**（写入闸门 + 签名）→ 补上「残缺数据被当成完整」这个洞。
5. **C6**（只读校验）→ 供 CI 与发版前检查使用。

### 8.2 若只做一件事

**C1 + C2 一起做**（数据文件隔离 + 互斥锁）。前者让并发测量互不干扰，后者让并发测量根本不会同时发生；
两者叠加后，「残缺数据被采纳」还需要 C3 才能完全堵死，但概率与后果都已降到最低。

### 8.3 待核项（本次审计无法从仓库证实，需按此方式复核）

| 编号 | 待核内容 | 复核方式 |
| --- | --- | --- |
| T-1 | 「`tools/apktool/adapter.py` 的 58 行 = 模块级语句数」这一推断 | 在**非并发**的环境里跑一次 `coverage run --include=src/dexatlas/tools/apktool/adapter.py -m pytest --collect-only` 之类的最小复现，或用 coverage 的 parser 直接统计模块级语句数 |
| T-2 | 「阶段 ②③ 的 pytest-cov 不读 rc 文件、不受 `parallel = true` 影响」 | 对照 coverage 7.16.2 的配置查找顺序（`.coveragerc` → `setup.cfg` → `tox.ini` → `pyproject.toml`）；本仓库 `pyproject.toml` 无 `[tool.coverage.*]` 段 → 走默认值 |
| T-3 | 「弱模块表 52 行」这一数字 | 数 `<!--fig:coverage.weak_modules-->` 块内以 `` | ` `` 开头的行数（表头与分隔行不计） |
| T-4 | 「覆盖率长期在 93% 附近」这一经验阈值 | 读历史提交里的记录（`git log -p -- docs/reports/phase1-execution-report.md`），或读每次测量留下的 `<!--report-figures:...-->` 记录 |
| T-5 | 主线工作树的报告在审计后是否已被重测量改写 | 审计期间主线仍在测量（观测到 `.coverage` 文件与多个 `python.exe` 进程），**结论以审计时刻的 `git diff` 为准**；复核命令：`git -C E:\Dexatlas diff -- docs/reports/phase1-execution-report.md` |

### 8.4 行号核对结果

本文所有 `文件:行` 引用已用 `git show 8868e30:<路径> | sed -n '<行>p'` 逐条打印原文复核
（方法见 §0.3）。核对覆盖 **15 条带文件名的引用** + **88 条简写引用**（形如 `:293-311`，
默认指 `scripts/refresh-report-figures.py`；附录 B 表格里的简写指 `fbca3d5` 版本），
全部命中预期构造。核对过程中修正了三处：

| 位置 | 原引用 | 修正为 | 原因 |
| --- | --- | --- | --- |
| §4.3 | `:1100` | `:1079` | 指纹在主流程里的调用点是 `:1079`（`current_fingerprint = source_fingerprint()`），`:1100` 是 `print` 语句 |
| §1.5 / §7.2 | `:1265-1269` | `:1261-1271` | 徽章值的字典在 `:1261-1264`，替换循环在 `:1265-1271` |
| §4.3 | `tests/test_docs.py:856-874` | `:848-874` | 该测试的 `def` 在 `:848`（`test_execution_report_discloses_every_weak_module`），断言在 `:868`、`:871` |

**一处必须读作「工作树」而非「HEAD」的引用**：`docs/status.md:24`、`README.md:13`、
`docs/reports/phase1-execution-report.md:77` 这三行，在 `8868e30` 的提交内容里是 **93.2%**，
在主线工作树里是 **35.4%**——**行号相同、内容不同**。本文 §7 引用的都是**工作树**（污染态），
§7.1 表格里「主线 HEAD」那一列引用的才是提交内容。

> 本文**不使用** `<!--fig:...-->` 标记承载数字（那些标记由 `scripts/refresh-report-figures.py`
> 拥有，写进去会被下一次测量覆盖）。

---

## 附录 A：主线条号对照（本文引用基准，commit `8868e30`）

| 构造 | 行号 |
| --- | --- |
| `REPO_ROOT` | `scripts/refresh-report-figures.py:86` |
| `FINGERPRINT_FILES` | `:110` |
| `COVERAGE_RC`（`parallel = true` / `source = dexatlas`） | `:126-129` |
| `WEAK_MODULE_PERCENT` | `:132` |
| `RECORD` 正则 | `:143` |
| `MAX_ROUNDS` | `:172` |
| `run()`（`cwd=REPO_ROOT`） | `:236-238` |
| `discard_stale_coverage()` | `:293-311`（glob `:306`，unlink `:309-310`） |
| `read_coverage()` | `:314-334`（`coverage json -o -` `:316`） |
| `measure_code_tests()` | `:387-433`（rc 路径 `:411-413`，`COVERAGE_PROCESS_START` `:414-415`，`coverage run` `:416-430`，`coverage combine` `:431`） |
| `measure_report_checks()` | `:435-451`（`pytest --cov-append` `:449`） |
| `measure_status_checks()` | `:454-474`（`pytest --cov-append` `:472`） |
| `fingerprint_files()` | `:487-506` |
| `source_fingerprint()` | `:509-535`（换行归一 `:532`） |
| `build_record()` | `:653-691`（`source_fingerprint` `:673`，`schema` `:665`） |
| `percent()` | `:694-696` |
| `weak_modules()` | `:699` |
| `converge()` | `:940-1020`（第二次读取 `:984`，采纳 `:1003`，重建 `:1005-1009`） |
| 主流程 | `:1107` 清场、`:1108` 阶段①、`:1109` 第一次读取、`:1115-1122` 模块集合检查、`:1124-1130` 失败闸门、`:1138-1146` 完整性判据、`:1210-1229` 部分运行保留旧值 |
| `--check` 分支 | `:1294-1303`；写回 `:1304-1321` |
| `warn_partial()` | `:1340-1352` |

## 附录 B：审计工作副本（`fbca3d5`）的对应行号

该副本的脚本**尚未**引入 `COVERAGE_PROCESS_START` / `parallel = true`，
阶段 ① 用的是 `pytest --cov=dexatlas --cov-report=term`，同样没有 `--cov-append` 之外的隔离手段；
但**同样存在** `discard_stale_coverage()` 的整体删除与 `coverage json` 的整体读取。

| 构造 | `fbca3d5` 行号 | 主线 `8868e30` 行号 |
| --- | --- | --- |
| `discard_stale_coverage()` | `:277-295` | `:293-311` |
| `read_coverage()` | `:298` | `:314` |
| `measure_code_tests()` | `:365` | `:387` |
| `measure_report_checks()` | `:384` | `:435` |
| `measure_status_checks()` | `:403` | `:454` |
| `fingerprint_files()` | `:436` | `:487` |
| `source_fingerprint()` | `:458` | `:509` |
| `build_record()` | `:602` | `:653` |
| `percent()` | `:643` | `:694` |
| `weak_modules()` | `:648` | `:699` |

`tests/conftest.py` 在两个树里**完全一致**（已 diff 验证），行号通用：
`SCRATCH_DIR` `:30`、`os.environ[...]` `:32-33`、`mkdir` `:35`、
adapter 的 import `:16-17`。
