# C17：把散文里剩下的手写测量数全部收进「数字随测量走」

**日期：** 2026年11月20日 · **性质：** 机制补边 + 守卫对齐 + 残留审计 · **分支：** `claude/gifted-moore-40c95f`
**动的：** `scripts/refresh-report-figures.py` ✓、`scripts/make-social-preview.py` ✓、
两页 `docs/how-to-verify*` ✓、`tests/test_how_to_verify.py` ✓、`tests/test_figures_auto_write.py` ✓、
`tests/test_social_preview.py` ✓、`tests/test_docs.py` ✓、`.github/social-preview.json` ✓、本文件 ✓。

---

## 0. 一句话

C17 登记时点名**三个同形状的闭环**——「数字变了 → 门禁先红 → 门禁挡住更新数字的那件事」。
散文那一环（`tests.trio`、skip 表三数）已由 `prose-to-markers.md` 那扇闭合；本窗口把
**剩下的三处手写测量数**收进机制，并给不能改成标记的地方配上**守性质**的门禁：

| 闭环 | 本窗口的处置 | 状态 |
|---|---|---|
| ① 两页 §2.3 的 `pytest --collect-only` 期望输出（围栏里的整句） | 新增 `tests.collect.fast` / `tests.collect.slow` 两个 figure kind，**围栏写入通道**；两页换成标记；守卫改读标记并挪进**自检段** | ✅ 机制 + 页面 + 守卫 |
| ② 报告的测试文件表（行是手写的） | 审计进**测量记录**（`table.missing_rows` / `table.stale_rows`），拒绝路径也写；4 条红→绿测试 | ✅ 记录化 + 测试 |
| ③ 社交预览卡片 sidecar 的 suite 口径 | sidecar 增加 **`suite` 块**（按测量脚本的 `SUITE_NAMES` 全量记录）；`--check` 对账 sidecar 与测量记录；2 条红→绿测试 | ✅ 对齐 + 门禁 |
| ④ 两页 §2.5 的 `documents read: N` | 新增 `documents.count` figure kind（复用 `check-version-claims.py` 的统计口径），两页换成标记 | ✅ 机制 + 页面 |

**测量脚本本窗口没有跑**（按分工留给主会话统一重测）——本窗口改了 `scripts/` 与 `tests/`，
源指纹已变；本窗口还**新增了 9 个测试函数**（收集数 1775 → 1785），两页的数已过期，
`tests/test_how_to_verify.py` 的 6 条检查现在是**红的**——这正是 C17 要破的闭环的样子，
重测后由机制自动转绿（见 §4）。

---

## 1. 闭环 ①：collect 期望输出改标记

**残留形状**（`prose-to-markers.md` §4 留下的）：

```bash
uv run --no-sync pytest --collect-only -q -m "not slow"   # → 1626/1775 tests collected (149 deselected)
uv run --no-sync pytest --collect-only -q -m "slow"         # → 149/1775 tests collected (1626 deselected)
```

这两句是**命令该打印的东西**，写在围栏里；`live_figures()` 不把围栏里的标记当数，
所以之前的机制写不了它们——每加一个测试，这两句要人手改，否则守卫红、测量拒绝写。

**机制改法**（`scripts/refresh-report-figures.py`）：

1. `render_figures()` 新增两个键，值为**整句**（跟 `tests.trio` 同一思路：一个标记装一句，
   守卫的正则在标记里照样匹配）：
   - `tests.collect.fast` → `1626/1775 tests collected (149 deselected)`（数字来自测量）；
   - `tests.collect.slow` → `149/1775 tests collected (1626 deselected)`。
2. 新增 `FENCED_KEYS`：这三类（collect 两句 + `documents.count`）是**唯一**允许写入围栏的标记。
   写入围栏走独立的第二遍（`apply_figures(..., collect=True)`），普通遍仍然不碰围栏——
   「围栏是引文」的规则对其它一切标记照旧成立。
3. **唯一的例外有唯一的理由**：这几句的文本**就是测量本身**（命令的输出、文档的计数），
   不是插图。页面上它们仍以 `<!--fig:…-->` 标记包裹，渲染出来只有数字与句子本身。

**页面改法**：两页 §2.3 的两条命令行注释里，期望输出换成
`<!--fig:tests.collect.fast-->1703/1852 tests collected (149 deselected)<!--/fig-->` / `<!--fig:tests.collect.slow-->149/1852 tests collected (1703 deselected)<!--/fig-->`；
§4 的清单补一句「collect 期望输出也是这套标记写的」。

**守卫改法**（`tests/test_how_to_verify.py`）：

- `_the_expected_output()` 改为读页面的 `tests.collect.*` **标记**（含一条：标记的键要与
  命令的 `-m` 过滤对应，键与过滤器错位也是 finding），不再从裸文本抓数字；
- 页面路径改经 `DEXATLAS_HOW_TO_VERIFY_PATH` 环境变量（与报告、状态页同一套重定向约定）；
- 测量脚本新增 `measure_page_checks()`（照 `measure_status_checks()` 的样子），把这两页的
  检查从**代码测试段**（`--ignore` 掉 `tests/test_how_to_verify.py`）挪进**自检段**：
  自检拿**候选页**（本次测量自己写好的）去测。至此「加测试 → 旧数红 → 测量不肯写」的
  死锁消失：门仍在（当场收集的数照比），只是它比的对象换成了候选页。

**红→绿**：5 条新机制测试（`tests/test_figures_auto_write.py`）在 HEAD 旧实现上 **5 red**
（`test_a_collect_sentence_inside_a_fence_is_written` 等），新实现全绿。
守卫对照：裸文本页面 + 旧守卫能匹配（证明旧守卫读的是字面量）；标记页面 + 新守卫读标记。

---

## 2. 闭环 ②：测试文件表的行集合核对进记录

`1fe7c30` 已让刷新脚本在**测之前**比对「表里列出的文件集合」与 `tests/test_*.py` 实际集合，
不等就拒绝写。本窗口补的是**记录化**：

- `build_record()` 新增 `table` 键：`{"missing_rows": [...], "stale_rows": [...]}`——
  **空列表也写**（一个只在出错时才出现的键，读者没法核对它的缺席）。
- 拒绝路径也把审计写进记录块再退出：报告被拒之后，读者打开报告就能从记录里看到
  **为什么被拒**，不用重跑那个两秒的比对。数字与表格照旧一个字不写。
- 4 条测试（`tests/test_docs.py`）：缺行 → 记录 `missing_rows=["test_docs.py"]` ✓；
  全对 → 记录两个空列表 ✓；记录的审计与当场比对一致 ✓；拒绝路径的**图形不变**（只多审计）✓。
  在 HEAD 旧实现上 4 条 **red**（记录里没有 `table` 键），新实现全绿。

---

## 3. 闭环 ③：卡片 sidecar 的 suite 口径

`b16c0ad` 把卡片检查的「测量完整」判据改成按 `SUITE_NAMES`（含 `deselected`）核账，
但 **sidecar JSON 本身**只记 `figures`（`suite.passed`、`suite.failed` 两个）——
测量记录里的 suite 块后来又添了别的键时，sidecar 没有跟上，检查者无从对账。

**改法**（`scripts/make-social-preview.py`）：

- `build_aside()` 增加 **`suite` 块**：按 `SUITE_NAMES` 全量记录（值读自测量记录，不是手抄）；
- `check()` 新增一组断言：sidecar 的 `suite` 块对每个 `SUITE_NAMES` 键都有记录——
  **名单读自测量脚本，不另抄一份**（两份名单迟早给出两个答案）。
- 44 项检查 → **50 项**（6 条 suite 键断言），当前树全绿。

**红→绿**：2 条新测试（`tests/test_social_preview.py`）在 HEAD 旧卡片脚本上 **red**
（`test_the_gate_refuses_a_sidecar_that_misses_a_suite_outcome`：旧门禁放行了一个丢了
outcome 的 sidecar——`assert 0 != 0` 失败，即旧门禁对该缺陷沉默），新实现拒绝并点名缺的键。

---

## 4. 闭环 ④：`documents read` 改标记

两页 §2.5 的 `documents read: 161` 是版本声明门禁实跑输出的摘录，仓库每增删一份
Markdown 它就变——此前要人手跟。`prose-to-markers.md` §4 留的方案是加一个
`fig:documents.count` 键。

**改法**：

- `code_facts()` 新增 `documents` 计数，**复用** `scripts/check-version-claims.py` 的
  `_markdown_files()` 与 `HISTORY` 口径（同一份清单，不是第二种数法）；测量跑在**副本树**上
  （测试套件的常规做法）而没有那份脚本时返回 `None`，该图形**不写**（与徽章的空值规则一致：
  空数比错数好，什么都不说比说错强）。
- `render_figures()` 暴露 `documents.count`；它进 `FENCED_KEYS`（那两页把它写在围栏里）。
- 两页换成 `documents read: <!--fig:documents.count-->157<!--/fig-->`，说明段改为
  「由测量脚本按 §4 写出，仓库增删文档后下次测量自动变」。

当前实跑：`documents read: 173`（`git ls-files '*.md'` 减 `.github/issues/`）。
**页面上的 161 要等主会话重测后由机制写成 173**——本窗口不手改测量数。

---

## 5. 残留手写测量数审计（收尾清单）

| 位置 | 是什么 | 处置 |
|---|---|---|
| 两页 §2.3 collect 期望输出（围栏） | 命令输出 | ✅ 本轮改标记（`tests.collect.*`），机制写 |
| 两页 §2.5 `documents read` | 文档计数 | ✅ 本轮改标记（`documents.count`），机制写 |
| 报告测试文件表的**行** | 手写行 | ✅ 本轮审计进记录 + 4 条测试 |
| 卡片 sidecar 的 suite 口径 | 记录块 | ✅ 本轮 sidecar 增 `suite` 块 + 门禁对账 |
| `CLAUDE.md`/`AGENTS.md`/`portfolio`/`status`/`HANDOVER` 的 CI job 数 | 结构事实 | 已有门禁（`check-unguarded-numbers.py` 的 `ci-jobs-*`），真值从 `ci.yml` 现算——**维持** |
| 两页后端版本、契约条数 49、M6/M10 成绩 | 钉死/别的脚本 | 不是本机制的对象——**维持**（各有各的门禁） |
| `docs/releases/`、`docs/outreach/` 的一切 | 历史记录 / 对外素材 | 机制**明确不写**（`FIGURE_EXCLUSIONS`）——**按设计保留** |
| 报告里的历史 `documents read`（`ci-gate-coverage.md:443` 的 115、`new-pages-crosscheck.md` 的 114/110） | 当时实跑的记录 | **历史快照**，页面正文已写明「份数是快照」——**不改判定**；活的那两处已改标记 |

**结论**：仓库里会随树漂移、且读者会照着核对的测量数，现在要么由机制写（标记），
要么有门禁守性质，要么明确登记为「不归自动管」并写明理由。C17 的三个闭环全部闭合。

---

## 6. 红→绿汇总（全部实测）

| 测试 | 旧实现上 | 新实现上 |
|---|---|---|
| `test_a_collect_sentence_inside_a_fence_is_written` 等 5 条 collect 机制测试 | **5 red** | green |
| `test_the_record_names_the_rows_the_table_is_missing` 等 4 条 table 审计测试 | **4 red** | green |
| `test_the_gate_refuses_a_sidecar_that_misses_a_suite_outcome` 等 2 条 sidecar 测试 | **red**（旧门禁放行缺 outcome 的 sidecar） | green |
| `tests/test_how_to_verify.py` 6 条守卫 | 旧守卫读裸文本（对照：裸文本页可匹配） | 新守卫读标记；页面数过期时 **6 red**（等重测转绿——这正是闭环本身） |

**关于 6 条红**：本窗口新增 9 个测试函数（figures_auto_write +5、social_preview +2、
test_docs 的 table 审计 +2 个函数/4 个用例、how_to_verify 守卫改造），树上收集数
**1775 → 1785**（快 1626 → 1636），两页的 `1775/1626` 与记录块的 suite 数随之过期。
按分工**本窗口不跑测量**：`scripts/refresh-report-figures.py` 由主会话统一跑，
它会写两页的 `tests.trio`、`suite.*`、`tests.collect.*`、`documents.count`（161 → 173）、
报告、状态页、徽章，并重画卡片——**一个数都不用手改**，这正是本轮机制改造的验收方式。

---

## 7. 门禁

| 门禁 | 结果 |
|---|---|
| `ruff check .` | All checks passed ✓ |
| `ruff format --check .` | 417 files already formatted ✓ |
| `mypy` | Success: no issues found in 68 source files ✓ |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | 退出码 0 ✓ |
| `scripts/remap-citations.py` + `scripts/check-doc-citations.py` | 重锚后 **Every citation still says what it says** ✓ |
| `scripts/check-version-claims.py --base auto` | exit 0（`documents read: 173`、findings 2 已登记）✓ |
| `scripts/check-release-numbers.py` | exit 0 ✓ |
| `scripts/check-unguarded-numbers.py` | PASS 25 watched statements ✓ |
| `scripts/make-social-preview.py --check` | **All 50 checks passed** ✓（sidecar 已按新格式重建） |
| `tests/test_figures_auto_write.py` | 21 passed ✓ |
| `tests/test_social_preview.py` | 12 passed ✓ |
| `tests/test_docs.py` | 除 3 条「报告数过期」红外全绿（那 3 条等重测）✓ |

---

## 8. 本窗口做的 / 留给主会话的

### 8.1 本窗口做的

| 文件 | 改动 |
|---|---|
| `scripts/refresh-report-figures.py` | ① `render_figures()` 加 `tests.collect.fast/slow`、`documents.count`；② `FENCED_KEYS` + collect 写入通道（围栏里只写这几类，其余照旧不碰）；③ `build_record()` 加 `table` 审计，拒绝路径也写；④ `measure_page_checks()` + `DEXATLAS_HOW_TO_VERIFY_PATH`：两页守卫挪进自检段，代码测试段 `--ignore` 该文件；⑤ `document_count()` 复用 version-claims 的统计口径，副本树上优雅降级 |
| `scripts/make-social-preview.py` | sidecar 加 `suite` 块（按 `SUITE_NAMES` 全量）；`--check` 增 6 条 suite 键断言（44 → 50 项） |
| `docs/how-to-verify.md` / `.zh-CN.md` | §2.3 collect 行、§2.5 documents read 行改标记；§4 清单补 collect 一句；§2.5 说明段更新 |
| `tests/test_how_to_verify.py` | 守卫读 `tests.collect.*` 标记（键与 `-m` 过滤对应）；页面路径走环境变量 |
| `tests/test_figures_auto_write.py` | +5 条 collect 机制测试 |
| `tests/test_docs.py` | +4 条 table 审计测试；2 条既有拒绝测试的断言按新语义更新（图形不变、记录多审计） |
| `tests/test_social_preview.py` | +2 条 sidecar suite 测试 |
| `.github/social-preview.json` | 按新格式重建（suite 块，值读自测量记录；PNG 未动） |
| 8 份既有报告 | 本窗口改动引起的行号漂移重锚（remapper + 手工核对） |

### 8.2 留给主会话的

1. **统一重测一轮** `scripts/refresh-report-figures.py`（本窗口与并行窗口都改了 `scripts/`、
   `tests/`，源指纹已变；树上新增 9 个测试函数，收集数 1785）。重测会自动写：
   报告与记录块（含新 `table` 审计与新 `documents` 计数）、状态页、两份 README 徽章、
   两页 how-to-verify 的 `tests.trio` / `suite.*` / `tests.collect.*` / `documents.count`
   （161 → 173）、并按新数重画卡片（PNG + sidecar 一起提交）。
2. 重测后 `tests/test_how_to_verify.py` 的 6 条、`tests/test_docs.py` 的 3 条「报告数过期」
   红应全部转绿——这是本轮机制改造的最终验收。
3. 本报告与索引、`DOCS` 名单的登记（本窗口已一并做完，见 §8.1；若主会话另有登记口径，以此为准）。
