# 「后端未完成」的证据文案：说清没跑完与已产出是两件事

> **状态：已实施。** 一条 `verified` 证据记录的**措辞**被改写；它的**等级没有动**，
> 统计字段一个没动，公共契约一个字没动。
>
> **基线：** 本报告描述的改动落在提交 `90cf64d` 上。本文里的 `file:line` 引用指
> **那一棵树**（即 `src/dexatlas/core/evidence.py` 的 `add_error`）。此后若有人再动
> 这段代码，按 `CLAUDE.md` 第 4 步用 `scripts/remap-citations.py` 重映射即可。
>
> **来源：** M10 读者视角预演（[invitation-reader-rehearsal.md](invitation-reader-rehearsal.md)）
> 的 **M-2** 节。那一节记的是一份**超时运行**的报告里挂着两条互相打架的
> `verified` 证据；本报告处理的是其中一条（`E-0007`）的文案。

---

## 0. 一句话

后端没跑完，和后端交出来的产物，是两件事；旧文案只说了前一件，读起来却像后一件
不成立，于是读者抽到这两条就判「证据链断了」。改的是措辞：**把「这一步的状态」和
「它交出来的东西」分开说**。

---

## 1. 缺口：M-2 记下的那两条记录

预演报告用一个**全新工作区只跑一次**的超时分析复现出这个形状：

```text
evidence count: 12          ← 正常运行是 11 条
evidence_by_level: {'verified': 12}
E-0007 │ jadx did not complete: jadx exceeded its 1s timeout and was terminated │ jadx:error/timeout
E-0008 │ jadx produced real Java for 7 of 8 methods in 5 of 5 classes           │ jadx:sources
```

同一份报告的 `summary.decompilation` 写着 `methods_decompiled: 7 /
methods_total: 8 / methods_jadx_failed: []`，`errors[]` 里只有一条 `timeout`。

**读者为什么读错：** 验收项 C1（★）要求「任选 3 条 evidence 记录，逐条写出工具、
版本、locator 和 level」。读者抽到这两条，拿到的是两条关于同一个后端、字面互相打架
的 `verified` 陈述——一条说 jadx 没有完成，一条说 jadx 为 5 个类产出了 7 个方法的
真实 Java。**这两条都是真的**，但字面放在一起读不出它们各自说的是什么，读者会直接
推向「证据链断了」这个结论。

---

## 2. 这条记录是怎么来的（为什么它会和统计并列）

要改对，得先看清这条记录与统计**各自**是怎么算出来的。两者互不依赖。

**记录这一侧**：`src/dexatlas/core/evidence.py:317` 的 `add_error` 在后端失败时写下
一条记录。它的 `level` 是 `VERIFIED`——「后端失败」这件事本身是工具确立的事实，
locator 指向 `jadx:error/timeout`（失败即事实，见
`src/dexatlas/core/locators.py:56`）。文案原来只有一句：后端没有完成。

**统计那一侧**：`src/dexatlas/core/pipeline.py:1320` 的 `_record_decompilation` 从
jadx **自己的输出树**里读出覆盖度，写成 `summary.decompilation` 的三个字段和那条
「jadx produced real Java for N of M methods in K of K classes」的记录。

**为什么两者会在同一轮里同时成立：** jadx 超时时，被杀之前已经写进 `sources/` 的
`.java` 还在。`src/dexatlas/tools/jadx/adapter.py:279` 的 `extract` 收编这些已经写
出来的文件，同时把运行时的错误原样带回（该函数的 docstring 写得很直白：*"A
non-zero exit still yields classes whenever JADX wrote files before failing."*）。
于是同一轮里既有「jadx 没跑完」，也有「jadx 交出了 7 个方法」。

所以旧文案**不是错的**，它是**只说了一半**：它说了这一步的状态，没说输出的状态。
读者把「没跑完」读成「没产出」，矛盾就是这么来的——矛盾在读者的读法里，不在数据里。

---

## 3. 改前 / 改后

改的是 `src/dexatlas/core/evidence.py:63` 的 `_failure_summary`——它给这条记录拼文案，
由 `src/dexatlas/core/evidence.py:317` 的 `add_error` 调用。按错误码分两支。

### 3.1 后端跑了、但没跑完

`timeout` / `exit_nonzero` / `parse_error` / `output_truncated` 都属于这一类。

```text
改前：jadx did not complete: jadx exceeded its 1s timeout and was terminated

改后：jadx did not complete in this run: jadx exceeded its 1s timeout and was
      terminated. It stopped part-way: what it had produced before it stopped
      is recorded separately, not withheld.
```

三处变化：

1. **`in this run`** —— 把范围钉死在这一次运行上。读者不必猜「jadx 是不是从来就没
   成功过」。
2. **`It stopped part-way`** —— 它是**停在中途**，不是「什么都没做」。
3. **`what it had produced before it stopped is recorded separately, not withheld`** ——
   它停止前交出来的东西**另有记录**，没有被扣留。这半句是整条改动的重点：读者读到
   这里就知道 `E-0008` 不是和它打架的另一件事，而是它说的那件事的另一半。

### 3.2 后端压根没跑

`not_installed`（工具没装）与 `unsupported`（分析依赖没装上）属于这一类。

```text
改前：jadx did not complete: jadx is not installed or not on PATH

改后：jadx did not complete in this run: jadx is not installed or not on PATH. It
      never ran, so it produced nothing.
```

这一支说的是相反的话，而且是必须说的：**没有产物，因为没有运行**。若这里也用
「stopped part-way」那套话，读者会去猜「是不是有产物被扣下了」——那正是 3.1 要
消除的疑问，在这里却是假的。两类失败的事实不同，措辞就不能一样。

### 3.3 没有动的部分

| | 状态 |
|---|---|
| `level` | 仍是 `VERIFIED`。**证据等级的语义是公共契约面，本次不动**（用户的决定：只改文案） |
| `kind` | 仍是 `observation` |
| locator | 仍是 `{tool}:error/{code}` |
| `detail` | 仍是 `error` 的完整转储 |
| `summary.decompilation` 的三个字段 | 一个没动（`methods_decompiled` / `methods_total` / `methods_jadx_failed`） |
| `errors[]` 的结构与退出码 | 一个没动 |
| `docs/architecture/public-contracts.md` | **一个字没动** |

---

## 4. 改后怎么读

拿 M-2 那份报告的两条并排看：

```text
E-0007 │ jadx did not complete in this run: jadx exceeded its 1s timeout and was
       │ terminated. It stopped part-way: what it had produced before it stopped
       │ is recorded separately, not withheld.          │ jadx:error/timeout
E-0008 │ jadx produced real Java for 7 of 8 methods in 5 of 5 classes
                                                      │ jadx:sources
```

- 读 `E-0007`：得到「**这一步**没跑完；它交出来的东西**另有记录**」。
- 读 `E-0008`：得到「那些东西是 7/8 个方法、5/5 个类」。

两句合起来是一句话的两半，不是两句互相否定的话。读者再核对 `summary.decompilation`
的 `7 / 8`，看到的是同一个数的两处表述——**一致**。

反过来，如果这轮是「jadx 没装」，读者拿到的 `E-0007` 会直说「它没运行，所以它没有
产出」，而报告里**不会**同时有一条覆盖记录（没有产出就没有覆盖度可写）。两种情况
的措辞不同，读者一眼能分开。

---

## 5. 英文与中文材料的一致性

这条记录的文案是**英文**的（报告与 JSON 报告的 `summary` 字段）。检查了同一件事在
中文材料里的对应说法：

| 材料 | 怎么说 | 要不要改 |
|---|---|---|
| 记录本身（Markdown 报告 / JSON 报告 / 证据包） | 英文，见 §3 | **已改** |
| 读者包 §9.1（G3） | 「超时运行的证据条数与正常运行不同：会**多出一条** `verified` 的『后端未完成』记录」 | **不用改**——新文案仍然是「一条 verified 的后端未完成记录」，条数也没变，只是这句话本身不再会被读成「jadx 什么都没产出」 |
| 公共契约 `docs/architecture/public-contracts.md` | 对证据等级、`errors[]`、退出码、`index_complete` / `index_gaps` 的说明 | **不用改**（一个字都没动；本次只改一条记录的措辞，契约面本来也不该由这次改动来动） |
| 报告渲染层的固定句 | 「These steps did not complete. Results that depend on them are absent, not clean.」 | **不用改**——同一套道理：未完成 ≠ 结果为干净。新文案与它是同向的 |
| `docs/glossary.md` | 没有「后端未完成」这个词条 | 无需动 |

结论：**没有哪份中文材料与新文案冲突**。中文材料里唯一提到这条记录的地方（读者包
§9.1）说的是「多出一条记录」，这件事改文案前后一样。

---

## 6. 怎么复现

**看新样子**（本机有 jadx 时）：把 jadx 的超时设得足够小，跑一次分析，在报告的
证据表里找 `did not complete in this run` 那一行。仓库里的一组替身后端
（`tests/test_failure_wording.py`）不依赖任何外部工具，随时能跑：

```bash
uv run --no-sync pytest tests/test_failure_wording.py -q
```

**看旧样子**：把 `src/dexatlas/core/evidence.py:317` 的 `add_error` 拼文案的那一行换回
旧的一行（`f"{error.tool} did not complete: {error.message}"`），再跑上面那条命令——
**5 条会红**：

```text
FAILED tests/test_failure_wording.py::test_a_stopped_backend_says_it_stopped_part_way
FAILED tests/test_failure_wording.py::test_a_stopped_backend_says_what_it_left_behind
FAILED tests/test_failure_wording.py::test_a_backend_that_never_ran_says_it_produced_nothing
FAILED tests/test_failure_wording.py::test_the_failure_record_and_the_coverage_record_are_not_a_contradiction
FAILED tests/test_failure_wording.py::test_the_report_and_the_json_report_carry_the_wording
```

另有 4 条在旧实现下**照旧是绿的**——它们守的是**不该变**的东西：等级仍是
`verified`、统计仍是 `7 of 8 methods in 5 of 5 classes`、失败记录里不得出现
「produced nothing」。**「只改文案」这件事本身要有测试守着**，否则下一次顺手改动的
人不会知道自己顺手改了什么。

---

## 7. 本窗口做了什么 / 留给主会话

### 7.1 本窗口（分支 `claude/quizzical-dubinsky-df2ff1`）

| 文件 | 改了什么 |
|---|---|
| `src/dexatlas/core/evidence.py` | 新增 `_failure_summary`（`src/dexatlas/core/evidence.py:63`）与 `NEVER_RAN_CODES`（`:60`）；`add_error`（`:317`）改用它。**等级、kind、locator、detail 一个没动** |
| `src/dexatlas/core/pipeline.py` | `_record_decompilation` 的 docstring（`src/dexatlas/core/pipeline.py:1320`）补一句：失败记录说的是**这一步**，不是它的产出 |
| `tests/test_failure_wording.py` | **新文件，9 条**。复现 M-2 的完整场景（替身后端：jadx 写出部分 Java 后被终止 + 8 个方法 5 个类的索引），断言两条记录并存时不再打架、等级仍是 `verified`、统计数字没动、Markdown 与 JSON 报告都带着新文案 |
| `tests/test_first_party_samples.py` | 一条精确相等断言跟随新文案（`not_installed` 那一支） |
| `docs/analysis-provenance.md` | 文档里的 JSON 样例的 `summary` 换成新文案；**5 处** `core/evidence.py` 引用行号因插行而漂移（2 处由 `scripts/remap-citations.py` 重映射，3 处手改到新行号） |
| `docs/reports/evidence-package-isolation.md` | 1 处引用行号被重映射（同样是插行造成的漂移） |
| `docs/reports/post-release-rehearsal.md` | 2 处**既存**漂移：它指向 `v1.0.0-release-checklist.md` 的 §7 N6，那一节被前面的一次改动挤走了（原引用指的那一行现在只剩一个空行），已改指到 §7 N6 现在所在的位置。修它是因为门禁要求 `drifted: 0` |
| `docs/how-to-verify.md`、`docs/how-to-verify.zh-CN.md` | 两处**手写**的 `collect` 预期输出更新为本窗口实测值（1561/1710）。这两处不由 `scripts/refresh-report-figures.py` 维护，只能人手改；本窗口动手**之前**它们就已经落后 6 个测试 |
| `docs/reports/phase1-execution-report.md` | **只加了测试文件表里的一行**（`test_failure_wording.py`）。这行**必须**加：`scripts/refresh-report-figures.py` 在测量**之前**先比对那张表与实际套件，对不上就打印「Nothing was written」并退出 1——不加这一行，主会话合入后的重测会被脚本直接挡住。表里的**数字一个没动**（`<!--fig:tests.*-->` 留给刷新脚本） |
| `docs/reports/evidence-incomplete-backend-wording.md` | 本文件 |
| `docs/reports/README.md` | 索引登记（§6），份数与合计同步 |
| `scripts/check-doc-citations.py` | `DOCS` 列表登记本文件 |

**门禁状态**（本窗口实测）：`ruff check` / `ruff format --check` / `mypy` /
`vulture --min-confidence 80`（退出 0）/ `check-doc-citations.py`（`drifted: 0`）/
`check-version-claims.py --base auto`（退出 0，2 条既存 finding，未新增）全绿。

本机全量测试里**没有通过**的那些，逐条归因如下（都不是本改动的责任，但主会话重测
时会再遇到）：

| 未通过的测试 | 为什么 |
|---|---|
| `tests/test_androguard_integration.py`、`tests/test_androguard_isolation.py`（9 errors + 2 failed） | 需要 `scripts/fetch-fixtures.sh` 抓的第三方 fixture，本机无网。CLAUDE.md 写了：fixture 缺失时集成套件**失败**而不是跳过 |
| `tests/test_docs.py` 5 条 | 执行报告里的数字（测试数、覆盖率指纹、语句计数）与树不符 → 正是留给主会话重测的那件事 |
| `tests/test_platform_independent_gates.py::test_every_ci_job_redirects_its_temporary_directory` | CI job 数 10 ≠ 期望 9（别的会话往 CI 里加了本地门禁 job，没同步这个期望值）。与本改动无关 |
| `tests/test_evidence_package.py::test_the_cli_counts_the_files_the_reader_finds_in_the_zip` | 本机控制台宽度把输出折了行（期望串 `1 source fragment` 被拆成 `1 source \nfragment`）。与本改动无关 |
| `tests/test_how_to_verify.py` 6 条 | 文档里手写的 `collect` 预期输出过期 → **本窗口已更新**，见 §7.1 |

### 7.2 留给主会话

1. **合入后要重测一轮。** 本窗口改了 `src/` 与 `tests/`——而源码指纹的覆盖范围正是
   `src/**/*.py`、`tests/**/*.py`、`pyproject.toml`、
   `scripts/refresh-report-figures.py`，所以指纹一定变。**本窗口按要求没有跑
   `scripts/refresh-report-figures.py`**（并发测量会互相污染覆盖率）。
2. **重测会一并修好当前树里已经过期的报告数字**，不必当成新问题追：
   - `tests.total`：报告写 1695，树里是 1710；
   - `tests.fast`：报告写 1546，树里是 1561；
   - 覆盖率指纹、套件通过/跳过数、语句计数（`core/evidence.py` 107 → 113 是本窗口
     造成的，**`reports/evidence_package.py` 172 → 187 不是**——那一处在本窗口动手
     之前就已经与树不符）；
   - 执行报告的测试文件清单——**那一行本窗口已经补上了**（见 §7.1），剩下的是数字。
3. **本窗口新增 9 个测试**，套件计数因此 +9（not slow 1552 → 1561，total 1701 →
   1710）。`docs/how-to-verify.md` 与 `docs/how-to-verify.zh-CN.md` 里**手写**的
   `collect` 预期输出**已按本窗口实测更新**（1561/1710）——那份文档**不由**
   `scripts/refresh-report-figures.py` 维护（脚本只写执行报告、`docs/status.md` 与
   README 徽章），只能人手改。顺带说明：它在本窗口动手**之前**就已经落后 6 个测试
   （它写 1546/1695，树里是 1552/1701），不是本窗口引入的；**合入后若树再变，
   这两处要再核一次**。
4. **M-2 的材料侧那一半没有动**：验收项 C4（「报告中的计数与证据记录一致」）怎么
   给基线，是材料侧的决定；本窗口只处理了工具侧那条记录的文案。读者包 §9.1 已经
   说明了「条数随后端配置变化，判据是以报告自身为准」，因此 C4 在改文案之后仍然
   成立。
5. **本窗口没有动任何公共契约**：`docs/architecture/public-contracts.md`、
   `src/dexatlas/core/models.py` 的等级定义、`errors[]` 的结构、退出码、
   `index_complete` / `index_gaps` 的语义，全部原样。

---

## 8. 一句话留给下一个人

**「后端没跑完」不是「后端没产出」。** 证据记录说一件事，就说那一件事；把同一轮里
已经成立的事实（它交出来的产物）留在别处，是索引，不是矛盾。
