# CI 的临时目录重定向：补上一个 job，退役一条数个数的规则

> 复核日期：2026年11月19日 · 复核方式：**修 + 核**（本轮改了 `.github/workflows/ci.yml`、
> `scripts/platform-gates.json`、`tests/` 与三份报告里的引文行号）
> 复核树：`claude/vigorous-hamilton-94ee65` @ `5f30e5d`（父树是 C15 落地后的 `5f30e5d`）
>
> 本文只说这一轮的两件事。**登记与重测留给主会话**，见 §7。
> 正文尽量只写**函数名与文件名**——行号是会烂的。

## 摘要

- **交办时的前提有一条已经过时。** 交办说「`test_every_ci_job_redirects_its_temporary_directory`
  现在把个数写死（`tmp_steps == 10` / `sync_steps == 12`）」。**这条规则在 C15 那一轮就已经退役了**
  ——提交 `d471b6d` 把它改成了守性质。所以本轮第二件事不是「退役」，而是**核**：核实它确实已经
  不数个数了，并且**把那个性质真正变成强制**（§3）。
- **真缺陷已修**：CI 的 `contracts-without-jadx` job 跑 `uv sync`、跑活检，却**没有**把临时目录
  重定向到工作区。它现在有了 `Keep generated files in .scratch` 那一步（§2）。
- **修之前，性质其实并没有被守住。** 这是本轮查到的最要紧的一件事：C15 的机制允许清单写
  `"defect"`，而这个 job 在清单里正是 `"defect"`。于是**缺陷在，机制是绿的**——它被
  「写下来了」，没有被守住。把清单改成 `"yes"` 之后，性质才成为性质：谁把那一步删掉，机制就红（§3.2）。
- **红→绿已证**（§4），有四组，其中第三组是本轮新加的回归测试**单独**抓住的。
- **顺带修了六处引文行号**（§5）：本轮往 `ci.yml` 里插了 16 行，所有指向 `ci.yml` 第 601 行
  之后的引文都跟着移位；其中两处**在写下的那天是对的、后来漂了**，本轮按它们**指着的那个东西**
  重新推导，而不是按 `+16` 平移。
- **数字过期**：本轮改了 `tests/` 与 `scripts/`，源码指纹变了 → 报告里的数要等主会话统一重测。
  **没有跑 `scripts/refresh-report-figures.py`，没有手改任何数。** 见 §6。

---

## 0. 这一轮改了什么

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `.github/workflows/ci.yml` | `contracts-without-jadx` job 加上 `Keep generated files in .scratch` 一步 | §2 的缺陷 |
| `scripts/platform-gates.json` | 该 job 的 `temp_redirect`：`"defect"` → `"yes"`；`gate_scripts` 补上 `scripts/verify-public-contracts.py`；`reason` + `fix` 换成一个记着来龙去脉的 `note` | §3.2 |
| `scripts/platform-gates.json` | `platform_sensitive_code` 里那条 note 的措辞（「missing redirect」）改成事实 | 该 job 已经不缺了 |
| `tests/test_platform_independent_gates.py` | 新增 `test_the_contract_jobs_redirect_their_temporary_directory` | §3.3 的回归测试 |
| `docs/reports/post-release-rehearsal.md`、`docs/reports/docker-image-samples.md`、`docs/reports/gate-self-checks.md` | 六处 `ci.yml` 引文行号 | §5 |
| `docs/reports/ci-temp-redirect-fix.md` | 本文件 | — |

**没动的**：`.github/workflows/ci.yml` 里其余 12 个 job 一行未动；`scripts/check-platform-gates.py`
一行未动（C15 的机制本身没有问题——§3.2 说的是**清单**怎么写，不是机制怎么判）。

---

## 1. 交办前提的核对：数个数的规则已经退役了

交办说那条测试现在写死了个数。**实际情况不是这样**，这里把证据摆出来，免得后面的人按交办的前提
去「修」一个已经修好的东西。

C15 那一轮（提交 `d471b6d`，分支 `claude/modest-ishizaka-8318ba`）把它改了：

```
git show d471b6d^:tests/test_platform_independent_gates.py
    822:    tmp_steps = text.count("Keep generated files in .scratch")
    823:    sync_steps = text.count("uv sync")
    824:    assert tmp_steps == 10, f"{tmp_steps} jobs redirect their temporary directory"
    825:    assert sync_steps == 12, f"{sync_steps} steps install dependencies"
```

（`d471b6d^` 是改之前的版本；这四行就是那条数个数的规则。）

现在的 `tests/test_platform_independent_gates.py::test_every_ci_job_redirects_its_temporary_directory`
问的是**性质**：跑 `uv` 的 job，要么把临时目录搬进工作区，要么在平台门禁清单里说清楚为什么不用搬。
本轮又核了一遍：全仓 `tests/` 与 `scripts/` 里**再没有**任何写死的 job 计数与
`uv sync` 计数（`grep` 过 `tmp_steps` / `sync_steps` / `job_count` / `len(jobs)` 等）。
剩下两处 `count` 是**算出来的、不是写死的**，都不构成一条规则：
`tests/test_platform_gate_inventory.py` 里那句比的是**两个 workflow**（加一个 job 前后），
`scripts/check-platform-gates.py` 里那个 `len(jobs)` 是**打印在 PASS 那行里的**。

**所以「退役」这件事本身已经完成。** 本轮在第二件事上做的是另一件事——把那个性质**从「被记着」
变成「被守着」**。理由见下。

---

## 2. 第一件事：`contracts-without-jadx` 缺临时目录重定向

### 2.1 缺陷是什么

这个 job 跑 `scripts/check-contract-records.py --expect without-jadx`，而**该脚本自己会跑活检**
（`scripts/verify-public-contracts.py`）。活检的工作区落在 `tempfile.gettempdir()` 里。
它的兄弟 job `contracts` 跑同一个活检，**有** `Keep generated files in .scratch` 那一步；它**没有**。

结果是：这两个 job 跑的是同一道门禁，**一个写进工作区，一个写进 runner 的系统临时目录**。

### 2.2 改法

照兄弟 job 的写法，在 `contracts-without-jadx` 的安装步骤**之前**加同一段（`.github/workflows/ci.yml`
里现在有 11 处 `Keep generated files in .scratch`，原先是 10 处）：

```yaml
      - name: Keep generated files in .scratch
        run: |
          set -euo pipefail
          mkdir -p "$GITHUB_WORKSPACE/.scratch/tmp"
          {
            echo "TMPDIR=$GITHUB_WORKSPACE/.scratch/tmp"
            echo "TEMP=$GITHUB_WORKSPACE/.scratch/tmp"
            echo "TMP=$GITHUB_WORKSPACE/.scratch/tmp"
          } >> "$GITHUB_ENV"
```

放在安装步骤之前，是因为 `uv sync` 自己也要写临时目录——放在后面就晚了。

**YAML 能解析**：`yaml.safe_load` 读得动，`jobs` 仍是 13 个，
`contracts-without-jadx` 的步骤依次是 checkout → setup-uv → **Keep generated files in .scratch** →
Install dependencies → The contracts without the Java backends。

---

## 3. 第二件事：性质当时并没有被守住

### 3.1 「写下来」不等于「守住」

C15 的机制（`scripts/check-platform-gates.py` 的 `check_ci_jobs`）对「跑 `uv` 却不重定向」的 job
接受两种说法：`"exempt"`（说明为什么不用搬）与 `"defect"`（说明缺什么、怎么补）。两种都要求填
`reason`，`"defect"` 还要求填 `fix`。

**这不是设计缺陷，这是它的用意**：「一个差异必须被写下来」。但它有一个直接后果——
**一个被登记为 `defect` 的 job，是被机制放行的**。而 C15 查出来的正是这个 job，
清单里写的就是 `"defect"`。

于是**缺陷在，机制是绿的**。本轮实测（把 `ci.yml` 与清单都还原成改之前的版本）：

```
$ python scripts/check-platform-gates.py
  PASS 13 CI jobs are declared, 4 platform-dependent tests are declared, and every difference carries a reason
EXIT=0
```

**机制说 PASS，而 `ci.yml` 里那一步确实不在。** 这就是本轮要补的洞。

### 3.2 改法：清单从「记着它缺」改成「记着它好了」

`scripts/platform-gates.json` 里这个 job 的条目改成：

- `temp_redirect`：`"defect"` → **`"yes"`**；
- `reason` + `fix` → 一个 `note`，记着它曾经缺过、什么时候补的、补的时候为什么坏
  （留着 `fix` 字段会变成一条没有对象的修复计划）；
- `gate_scripts` 补上 **`scripts/verify-public-contracts.py`**。

最后这一处值得多说一句：**原来只写了 `scripts/check-contract-records.py`**。
清单的 `gate_scripts` 是「这个 job 跑哪些脚本」，而这个 job 跑活检是**通过代理**跑的。
清单里看不见代理关系，读者就看不出「这个 job 为什么需要重定向」——
**缺陷能藏这么久，正是因为清单把它藏起来了**。把它实际跑到的脚本写进去，代理关系才显形。

改了之后，机制对这个 job 的判据从「写下来就算」变成「**树里必须真有**」：
`check_ci_jobs` 看到 job 确实重定向了、清单说 `"yes"`，两边对上；
谁把那一步删掉，机制会报 `runs 'uv sync' without redirecting its temporary directory
and the inventory says 'yes'` 并退出 1。

**机制本身一行未改**——它判得对，错的是清单把差异记成了「还没修」。

### 3.3 本轮加的那条回归测试

`tests/test_platform_independent_gates.py::test_the_contract_jobs_redirect_their_temporary_directory`：
断言 `contracts` 与 `contracts-without-jadx` 两个 job 都跑 `uv`、都重定向了，
**并且清单对这两个 job 的说法是 `"yes"`**。

最后那半句是它存在的理由：C15 的性质测试接受 `{"exempt", "defect"}`——
**那是有意的**（一个还没修的差异应当可以被记下来），但它意味着**这个洞一直开着**。
所以另加一条测试把这个 job 的**具体**处置钉住：这一处差异是**修好了**，不是记下来了。
以后谁想重新打开它，得先跟这条测试吵一架。

按 CLAUDE.md 规则 1，补一条修复就要带一条**在旧实现下是红的**回归测试——§4 第四组就是。

---

## 4. 红→绿（实测，不是声称）

四组。前三组用不同的方式问同一个问题：**这处差异被守住了吗？**

| # | 场景 | 做法 | 结果 |
|---|---|---|---|
| 1 | **改之前**：`ci.yml` 与清单都是旧的 | `git checkout --` 还原两者，跑机制 | **PASS，退出 0**——缺陷在，机制是绿的（§3.1） |
| 2 | **旧 `ci.yml` + 新清单** | 只还原 `ci.yml` | 机制**退出 1**，报 2 条：一条说这个 job 没重定向而清单说 `yes`，一条说脚本清单对不上 |
| 3 | **旧 `ci.yml` + 新清单** | 只还原 `ci.yml`，跑两个平台的测试文件 | **3 条红**：`test_every_ci_job_redirects_its_temporary_directory`、`test_every_difference_the_tree_has_is_accounted_for`、`test_adding_a_correct_job_does_not_turn_the_check_red`；其余 42 条绿 |
| 4 | **旧 `ci.yml` + 清单说 `defect`**（把洞打开） | 只还原 `ci.yml`，把清单的 `temp_redirect` 改成 `"defect"` 并补 `reason` | 性质测试**绿**（它认这个说法），**本轮新加的那条测试红** |

第 4 组是本轮新加测试的价值所在：**它单独抓住了 C15 那个有意的逃生舱。**
按机制的设计，逃生舱该留着——所以缺陷得由一条**具体**的测试来守，而不是指望通用规则。

**绿的那一头**：

- `python scripts/check-platform-gates.py` → `PASS 13 CI jobs are declared, 4 platform-dependent tests
  are declared, and every difference carries a reason`，**退出 0**；
- `pytest tests/test_platform_independent_gates.py tests/test_platform_gate_inventory.py -q`
  → **46 passed**（45 + 本轮新加的 1 条）。

### 4.1 顺带证过的一条：旧的数数规则会惩罚这次修复

交办说「补了那一步 → `tmp_steps` 从 10 变 11 → 那条数个数的测试正好会因此红」。**这条前提是准的**，
实测如下——把旧版测试文件放回来，跑同一条测试：

```
E       AssertionError: 11 jobs redirect their temporary directory
E       assert 11 == 10
```

**旧规则红的原因是「多了一个做对了的 job」，而那个 job 正是本轮修好的那个。**
这就是它该退役的全部理由：一条会因为正确而红的规则，守不住任何东西。

---

## 5. 顺带修的六处引文行号

本轮往 `ci.yml` 里插了 16 行，插在第 601 行之前。所有指向 `ci.yml` **第 601 行之后**的引文
都跟着移了 **+16**；第 601 行之前的（`ci.yml:4-22`、`ci.yml:436-494` 等）没动。

**检查器只报了 2 条**（两处指向 `measurement` job 的行号），因为只有它**认得出** YAML 的 job 名、
能把那行解析成「`measurement` 这个 job」再比它现在在哪。
**`scripts/remap-citations.py` 移了 0 条**——它查的是 Python 符号，YAML 的 job 不是符号。
CLAUDE.md 规则 4 说得很清楚：指着「地方」而不是「符号」的引文，**留给人来判**。

人判的结果——按**它们指着的那个东西**重新推导，不是按 `+16` 平移：

| 文件 | 原 | 新 | 它指着的东西 | 现在在哪 |
|---|---|---|---|---|
| `post-release-rehearsal.md` | `ci.yml:708` | `ci.yml:724` | `measurement` job | 724 |
| `post-release-rehearsal.md` | `ci.yml:705` | `ci.yml:771` | `refresh-report-figures.py --check` 那行 | 771 |
| `post-release-rehearsal.md` | `ci.yml:630` | `ci.yml:696` | `social-preview` job | 696 |
| `post-release-rehearsal.md` | `ci.yml:651` | `ci.yml:717` | `make-social-preview.py --check` 那行 | 717 |
| `docker-image-samples.md` | `ci.yml:708` | `ci.yml:724` | `measurement` job | 724 |
| `docker-image-samples.md` | `:755` | `:771` | `refresh-report-figures.py --check` 那行 | 771 |
| `gate-self-checks.md` | `ci.yml:786` | `ci.yml:802` | `fetch-depth: 0` 那行 | 802 |

**其中两处是本轮顺手发现的旧漂移**，不是本轮造成的，值得说一句：
`ci.yml:705` 与 `ci.yml:630` / `:651` 在**写下它们的那一天（提交 `2dcf677`）是准的**
——那时 `refresh-report-figures.py --check` 正好在 705 行，`social-preview` job 在 630 行、
它的 `--check` 在 651 行。后来 `ci.yml` 长胖了，引文没有跟着走，就漂了。
所以它们是**按指代物**重新推导的（771 / 696 / 717），不是 `+16` 平移。
`docker-image-samples.md` 里那句「引用 `measurement` job 的两处行号」
——那两个行号正好是这两个指代物在**当时**的位置，与上表自洽（今天又移过了 ✓）。

**没有改的**：`handover-tails-audit.md`（明写「本报告的 `file:line` 只在 `0a8e02e` 上成立」——
那是 v1.0.0 树，指的是那棵树）、`english-reader-review-2.md`（锚在 `2c456e0`）、
`ci-gate-coverage.md`（锚在 `062c4b5`）、以及各份快照报告里锚在别棵树的引文。
**锚在哪棵树，就跟着哪棵树走。**

改完：`python scripts/check-doc-citations.py` → **`drifted: 0`**。

---

## 6. 数字：哪些过期了，要重测后同步

本轮改了 `tests/` 与 `scripts/`，**源码指纹变了**。按 CLAUDE.md 的规矩，
报告里的数由 `scripts/refresh-report-figures.py` 生成，**不能手改**。

**本轮没有跑那个脚本，也没有手改任何数字。** 需要主会话在合入后重测一轮的：

| 位置 | 为什么过期 |
|---|---|
| `docs/reports/phase1-execution-report.md` 的 `<!--fig:…-->` 标记 | 源指纹变了（改了 `tests/` 与 `scripts/`）；测试条数与覆盖率都要重测 |
| `README.md` / `README.zh-CN.md` 的徽章 | 同上（徽章由同一个脚本写） |
| `docs/status.md` 的快照表 | 同上 |
| 报告索引里的报告份数 | 目录里现在有 **86** 份（本文之前 85）；索引上写的 82 是 2026-11-18 的快照，那三个差量是别的窗口落的（`platform-gate-inventory.md`、`m10-material-fixes.md`、`m8-4-note-and-c17.md`）。**本轮按交办要求没有登记**，见 §7 |
| 套件计数 | 本轮加了 1 条测试（两个平台的测试文件 45 → 46） |

**门禁现状**（本轮跑完，全绿）：

| 门禁 | 结果 |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 405 files already formatted |
| `mypy` | Success: no issues found in 68 source files |
| `vulture … --min-confidence 80` | 退出 0 |
| `python scripts/check-doc-citations.py` | **drifted: 0** |
| `python scripts/check-version-claims.py --base auto` | 退出 0（那 2 条 finding 是 `e19de950` 里就有的，与本轮无关） |
| `python scripts/check-platform-gates.py` | PASS，退出 0 |

### 6.1 整套件跑下来是什么样：没有一条红是本轮造成的

完整套件：**13 failed, 1626 passed, 88 skipped, 17 errors**。逐条分完，三类：

| 类 | 条数 | 是什么 | 是本轮造成的吗 |
|---|---|---|---|
| **A** | 11 | `tests/test_docs.py` 的 4 条（`test_all_relative_links_resolve`、`test_execution_report_numbers_match_the_code`、`test_execution_report_coverage_figures_describe_the_current_code`、`test_execution_report_suite_figures_add_up_to_the_tests_that_exist`）、`tests/test_how_to_verify.py` 的 6 条、`tests/test_evidence_package.py` 的 1 条 | **不是**——把本轮改的 6 个文件还原成父树 `5f30e5d` 再跑，**这 11 条照样红**（实测 `11 failed, 80 passed`）。相对链接那一条断的全是 `m10-material-fixes.md` 与 `m10-reader-rehearsal-3rd.md`（别的窗口的文件）；数字那几条是源指纹与套件计数过期——**正是 §6 那张表要主会话重测的东西** |
| **B** | 2 + 17 | `tests/test_androguard_integration.py` 与 `tests/test_androguard_isolation.py` | **不是**——本工作树**没有** `bash scripts/fetch-fixtures.sh`，报错就是它自己写的那句：`fixtures/apk/TestActivity.apk is missing; fetch the integration fixtures with bash scripts/fetch-fixtures.sh before running this suite`。按 CLAUDE.md，缺 fixture 的集成套件是**失败而不是跳过**（跳过会读成「验过了」） |
| **C** | 0 | 本轮改动引起的 | **0 条** |

所以：**本轮让套件里多了一条通过的测试，没有让任何一条从绿变红。**

---

## 7. 本窗口做的 / 留给主会话的

### 本窗口做的

1. **修**了 CI 的 `contracts-without-jadx` job（加临时目录重定向）。
2. **把清单的说法从「记着它缺」改成「记着它好了」**——这一步才让那个性质真的成为性质。
3. **加**了一条回归测试，把这个 job 的**具体**处置钉住，并单独堵住 C15 那个有意的逃生舱。
4. **核**了交办里「数个数的规则」那条前提：**它已经退役了**，并且**实测了**退役前后两种状态。
5. **修**了本轮造成的引文漂移（六处），顺带发现并修了两处**更早的**漂移。
6. **写**了本文。

### 留给主会话的

1. **重测一轮**：合入后跑 `scripts/refresh-report-figures.py`，把 §6 那张表的数同步掉
   （本轮**没有**跑，**没有**手改任何数）。
2. **登记**：本文的索引登记（`docs/reports/README.md` 的份数与 §6 的行）、
   `scripts/check-doc-citations.py` 的 `DOCS` 名单、以及 C15 候选表里这一条的状态
   ——按交办要求，这三处本轮**一律没有自己登记**。
3. **合入顺序**：本文与 C15 那三件东西（`scripts/platform-gates.json`、
   `scripts/check-platform-gates.py`、`docs/reports/platform-gate-inventory.md`）是一套，
   清单里的 `"defect"` → `"yes"` 这一改只有在那套东西在场时才有意义。
   `docs/reports/platform-gate-inventory.md` 里 §3.1 那段**记着这个 job 当时是缺陷**——
   那份报告本轮**没有动**（不归本窗口），主会话可以在合入时补一句它已被修复。

### 一处留给别人的观察，不在本轮范围

`scripts/platform-gates.json` 的 `platform_sensitive_code` 里那条 note 写的是
「the contracts-without-jadx job's **missing** redirect」——本轮改了措辞，因为它已经不缺了。
同一份清单里，**别的** job 若将来也出现同类缺陷，`"defect"` 这个说法会继续是「被放行」的。
**本轮没有动机制对 `defect` 的处理**：那是有意的设计（一个还没修的差异应当可以被记下来），
改它要连着改 C15 那套东西的语义，超出本轮交办的范围。
本轮的做法是给这一个具体的 job 加一条具体的测试——**要用多少条这样的测试，取决于还想守多少处。**
