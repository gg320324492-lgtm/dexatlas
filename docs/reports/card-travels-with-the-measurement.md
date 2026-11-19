# 卡片随测量走：把「重画卡片」从人的顺序变成测量的一步

**日期：** 2026-11-19 · **性质：** 实现报告（新增产物 + 两个改动文件：
`scripts/refresh-report-figures.py`、`tests/test_figures_auto_write.py`）
**回答的问题：** 首页卡片（`.github/social-preview.png`）上的数字怎么跟着测量走；
为什么原来「测量 → 卡片」要靠人记得做，做错了为什么会把测量锁死。

---

## 0. 结论

- 卡片是报告的一张**渲染图**：它上面的每个数都来自报告里的 `<!--fig:…-->` 标记
  （`scripts/make-social-preview.py:213` 的 `collect_facts()`），
  画完把画了什么记在旁边的 `.github/social-preview.json`（`ASIDE` 于 `:87`）里。
- 原来的做法是**两件事靠顺序连起来**：先重画卡片，再测量，测完再重画一遍。
  谁忘了中间那步，测量就会把整个仓库锁死（§1）。
- 现在测量自己会画：**报告落盘之后，测量顺手把卡片按新数重画**
  （`scripts/refresh-report-figures.py:2090-2092` 的 `draw_social_preview` 调用，
  函数在 `:2152`）。于是「测量 → 卡片」不再是一段要人记得的顺序，
  而是一次测量里的一个步骤。
- 时序只有一条规矩：**卡片画的是落盘后的报告**，不是收敛循环手里那份还没落盘的候选（§3）。
- 画不出来，这一次测量就失败——因为「画不出来的卡片」正是那个会把下一次测量锁死的状态（§2.3）。

---

## 1. 改之前：死锁长什么样

卡片和报告本来是一份事实的两个副本，谁都不是自动跟着谁走的。于是形成了这个环：

1. 某次测量把新数写进了 `docs/reports/phase1-execution-report.md`；
2. 卡片还是上一次画的那张，**它和报告在盘上的内容对不上了**；
3. 下一轮测量先跑**代码轮**（整条套件，`scripts/refresh-report-figures.py` 的
   `measure_code_tests()`），套件里有一项是
   `tests/test_social_preview.py:114` 的 `test_the_cards_are_current`——
   它拿卡片旁边的记录和报告里的数比，对不上就红；
4. 代码轮红 → 这一轮测量**拒绝落盘**（代码轮有失败时直接停，报告一个字都不动）；
5. 卡片于是永远更新不了：唯一能更新卡片的动作（跑测量）被卡片自己挡住了。

绕法是**顺序**：先重画卡片（让第 3 步能过），再测量，测完再重画一遍（让第 3 步下次还能过）。
人只要漏掉其中一次，就落进上面的环里。而且这条顺序要求人知道「卡片要重画两遍」这件事本身。

门禁其实早就发现了这件事：卡片脚本自己的核对模式（`scripts/make-social-preview.py:664-673`
的 `check`）会在 CI 里核对卡片与报告的数（44 项），`tests/test_social_preview.py:228` 的
`test_the_side_car_file_holds_the_figures_the_cards_draw` 再核一次记录本身。
**能发现不等于能修复**——门禁只会说「卡片旧了」，修卡片这件事仍然在人身上。

---

## 2. 改了什么

### 2.1 机制：从「两段顺序」变成「一个步骤」

测量脚本在写盘分支里多了一步：在报告、状态页、README 徽章和其它带标记的文档
都写完之后，重画卡片（`scripts/refresh-report-figures.py:2090-2092`）。

```python
        card_drawn = True
        if report_path == REPORT_PATH:
            card_drawn = draw_social_preview(REPO_ROOT)
```

画不出来时 `card_drawn` 为假，这一轮运行以失败收场（`:2108` 的 `matched = card_drawn`），
并把画图脚本自己说的话原样带出来。理由是：一张没画出来的卡片**就是**那个会把下一次
测量锁死的状态；这一轮把它说出来，比让下一轮撞上去才说好。

### 2.2 怎么调它：子进程，不是 import

`draw_social_preview()`（`:2152`）用**跑测量的那个解释器**起一个子进程：

```
python scripts/make-social-preview.py --repo-root <仓库根>
```

选它而不是 import 的理由有四条：

1. **只有一份「怎么画」的定义。** 字体、排版、两张卡片的文案、以及「画了什么」的那份记录
   都归 `scripts/make-social-preview.py` 管；把它当程序调，就不用在测量脚本里再抄一遍。
2. **文件名带连字符**，正常 import 不进来；用 `importlib` 按路径加载是取巧，
   而取巧的代价是测量脚本从此背着画图代码和它的异常。
3. **画图失败是一个可以被报告的值，不该是测量进程里的一个异常。** 字体缺失、
   排版溢出都由画图脚本自己分类（退出码 1/2），测量脚本把它翻译成「这次运行失败」。
4. **卡片不依赖 PATH 上恰好是哪个 python**——用的是跑测量的同一个解释器。

代价是：画卡片需要 Pillow 和字体。这不是新的要求——完整测量本来就需要 Pillow
（`docs/status.md:428`「完整测量需要 Pillow」），CI 上跑测量时也带了 `--extra demo`
（`.github/workflows/ci.yml:738`）。CI 上测量只跑 `--check`（`:755`），不写盘，
所以那一步在 CI 上根本不会走到（Linux runner 也没有 Windows 字体）。

### 2.3 边界：卡片属于仓库，不属于任何一份报告的副本

闸门是 `report_path == REPORT_PATH`：**只有被刷新的那份报告就是仓库自己的报告时，才画卡片。**

理由和这个脚本里其它几处闸门一样：测试套件跑的是**报告的副本**，配的是**编造的数**
（`tests/test_figures_auto_write.py` 里的 `_install_fake_measurements()`）。
给一份副本画卡片，卡片上会是仓库里那份真报告的数字——卡片和报告就成了两棵树的两个事实，
正是这一步要防的那种错位。这条边界由
`tests/test_figures_auto_write.py:411` 的
`test_a_run_against_a_copy_of_the_report_leaves_the_card_alone` 守着。

---

## 3. 时序：候选 vs 落盘（这一步最容易做错）

测量脚本的收敛循环（`converge()`）手里一直拿着**候选报告**：它是在磁盘上的报告还没写
之前，先把新数填进去、拿自检去量、来回改到自检和报告不再互相 disagreement 为止。
**候选不是磁盘上的文件。**

所以卡片必须在**落盘之后**画：画图脚本是从磁盘上读报告的
（`scripts/make-social-preview.py:213` 的 `collect_facts()` 读
`docs/reports/phase1-execution-report.md`），它画的时候看到什么，取决于那一刻盘上是什么。

- 若在落盘前画：卡片画的是候选，报告在盘上还是旧的 → 卡片上的数和报告里的数不是一回事，
  `.github/social-preview.json` 里记的也是候选的数
  （`tests/test_social_preview.py:228` 核的就是它）→ 错位。
- 若在落盘后画：卡片画的就是刚写下去的那份报告 → 卡片、记录、报告三者一致。

落盘的顺序是：**报告 → 状态页 → README 徽章 → 其它带 `<!--fig:-->` 标记的文档 → 卡片**。
卡片在最后，是因为徽章在 README 里，而徽章上写的正是卡片要核的那两个数
（`suite.passed` 和 `coverage.pct`）——徽章先写，卡片才和它对得上。

这条时序由 `tests/test_figures_auto_write.py:376` 的
`test_the_measurement_draws_the_card_from_the_report_it_wrote` 守着：它把画图脚本换成一个
只会记下「你要我画哪份报告」的桩，然后断言桩记下的内容**逐字等于**落盘后的报告。

---

## 4. 红 → 绿

**旧实现下怎么证明是红的**（把 `scripts/refresh-report-figures.py` 恢复到改动前的版本，
其余不动）：

```
$ uv run --no-sync pytest tests/test_figures_auto_write.py -q -k "draws_the_card"
...
        drawn = root / "card-was-drawn.txt"
>       assert drawn.is_file(), "the measurement wrote the report and left the card alone"
E       AssertionError: the measurement wrote the report and left the card alone
E       assert False
E        +  where False = is_file()
E        +    where is_file = WindowsPath('.../card-was-drawn.txt').is_file

FAILED tests/test_figures_auto_write.py::test_the_measurement_draws_the_card_from_the_report_it_wrote
1 failed, 1 passed, 9 deselected
```

红的理由是机制本身的理由：旧实现里测量写完报告就结束了，卡片根本没人画，
所以「画过卡片」这件事没有发生——不是断言写歪了。

**新实现下**：`11 passed`（`tests/test_figures_auto_write.py` 全绿）。

两个测试分别守着两件事：

| 测试 | 守着什么 |
|---|---|
| `tests/test_figures_auto_write.py:376` `test_the_measurement_draws_the_card_from_the_report_it_wrote` | 测量画了卡片，且画的是**落盘后**的报告 |
| `tests/test_figures_auto_write.py:411` `test_a_run_against_a_copy_of_the_report_leaves_the_card_alone` | 刷副本时不碰卡片（§2.3 的闸门） |

测试用的不是真画图：画图脚本被换成一个只会记下「你要我画哪份报告」的桩
（`tests/test_figures_auto_write.py:240` 的 `CARD_STUB`），测量脚本在**自己的一棵树**里跑
（`_tree()`，`:252`）。这样测试不依赖字体、不依赖 Pillow、在任何机器上都能跑，
而且不会在跑测试的时候把仓库自己的卡片重画一遍。

---

## 5. 门禁

| 门禁 | 结果 |
|---|---|
| `uv run --no-sync ruff check .` | All checks passed! |
| `uv run --no-sync ruff format --check .` | 405 files already formatted |
| `uv run --no-sync mypy` | Success: no issues found in 68 source files |
| `uv run --no-sync vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | 退出码 0（无输出） |
| `uv run --no-sync python scripts/check-doc-citations.py` | `drifted: 0`／`unresolved paths: 0` |
| `uv run --no-sync python scripts/check-version-claims.py --base auto` | 退出码 0（Every version claim matches the repository.） |
| `uv run --no-sync python scripts/make-social-preview.py --check` | All 44 checks passed. |
| `uv run --no-sync python scripts/check-gate-coverage.py` | All 11 gates are run by something. |

`check-doc-citations.py` 之所以还是 `drifted: 0`：新增的代码全部落在
`scripts/refresh-report-figures.py` 第 1670 行**之后**——全仓引用这个脚本的地方最高只到
`:1670`（`test_file_table()` 的调用），把新代码放在它后面，被引用的行号一个都不动。

### 5.1 全量套件的状态

全量 `uv run --no-sync pytest -q`：**1628 passed, 12 failed, 88 skipped, 17 errors**（8m49s）。
红项逐条归因，**没有一条是本窗口的改动造成的**：

| 红项 | 数量 | 归因 | 谁来修 |
|---|---|---|---|
| `tests/test_docs.py` 的「报告里的数」三项 | 3 | 报告的数过期（本轮加了 2 个测试，源指纹也变了） | 主会话合入后跑一轮测量 |
| `tests/test_how_to_verify.py` | 6 | `docs/how-to-verify.md` 里的 `<!--fig:tests.total-->` 还写着 1712 | 同上——那个数由测量写 |
| `tests/test_docs.py::test_all_relative_links_resolve` | 1 | 断链全在别的窗口的 `docs/reports/m10-*.md` 里（锚点对不上）；把本报告移出 `docs/` 再跑**仍然红**，与本改动无关 | 别的窗口 |
| `tests/test_androguard_integration.py`（2 failed + 7 errors）、`tests/test_androguard_isolation.py`（10 errors） | 2 + 17 | 这棵工作树没跑过 `bash scripts/fetch-fixtures.sh`，`fixtures/apk/` 里只有 `SOURCES.md` | 跑一次取夹具（环境问题） |

88 个 skip 是本机没装 apktool / JADX（环境问题）。**本窗口自己的两个文件是绿的**：
`tests/test_figures_auto_write.py` 11 项全过。

---

## 6. 哪些数字需要重测后同步（合入后由主会话做）

本窗口**没有跑** `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率），
也**没有手改任何数字**。下面这些数字在合入后必须由一轮完整测量重新写出来：

| 数字 | 为什么过期 | 谁来写 |
|---|---|---|
| `tests.total` / `tests.fast` / `tests.slow` | 本次给套件加了 2 个测试（`tests/test_figures_auto_write.py`） | 测量 |
| `suite.passed` / `suite.skipped` / `suite.xfailed` | 同上（套件规模变了） | 测量 |
| `source_fingerprint` | `tests/` 与 `scripts/refresh-report-figures.py` 都在源指纹覆盖范围内（`scripts/refresh-report-figures.py:114` 的 `FINGERPRINT_FILES`） | 测量 |
| README 徽章（两个语言） | 徽章里的数由测量写（`apply_badges()`） | 测量 |
| `docs/status.md` 里的数 | 同上 | 测量 |
| 首页卡片（两张 PNG）与 `.github/social-preview.json` | 卡片上的数来自报告的标记 | **测量**（新机制：落盘后自动重画） |

**症状先知道**：合入后、重新测量之前，`tests/test_docs.py:672`
（`test_execution_report_numbers_match_the_code`）会红：报告里写的测试总数比树里
现在有的少 2。这是预期内的：**报告里的数只能由测量写**。同理，下一轮测量在写盘
之前跑代码轮时，也会因为这个红而拒绝落盘——所以顺序是**先测量、再提交**，不是反过来。

卡片这次会跟着一起变：它是一张 PNG，字节会随上面的数变，属于预期内的二进制变更，
要跟报告、徽章一起提交。

---

## 7. 这个窗口做了什么，主会话要做什么

**这个窗口（本次）**

- 改 `scripts/refresh-report-figures.py`：落盘之后多画卡片这一步（`:2090-2092`、`:2152`），
  外加「画不出来就失败」（`:2108`）。**没有动**这个脚本里的其它任何地方——
  汇总行的正则、「读不出汇总行就中止」那条硬保险都没碰。
- 改 `tests/test_figures_auto_write.py`：加两个测试（`:376`、`:411`）和它们用到的桩。
- 新增本报告。
- 跑了 §5 的门禁，全绿；证明了旧实现下测试是红的（§4）。
- **没有**跑测量，**没有**手改任何数字。

**主会话（合入之后）**

1. 把本报告登记进 `docs/reports/README.md`（那份索引是主会话注册的，
   新增一份报告要改里面的份数），并把本文件加进
   `scripts/check-doc-citations.py` 的 `DOCS` 清单——本报告的 21 处 `file:line`
   引用是按「一个引用没人检查，就没人有义务让它一直对」这条规矩**手工核过**的
   （核法：把本文件单独喂给那个检查器，结果 `drifted: 0`、`unresolved: 0`），
   登记进清单之后就不必再手工核了。
2. **跑一轮完整测量**（`uv run --no-sync python scripts/refresh-report-figures.py`）：
   它会写报告、写状态页、写两份 README 徽章，**并且按新数重画卡片**（新机制）。
3. 把测量带出来的变更（报告、状态页、徽章、两张卡片 PNG、`.github/social-preview.json`）
   一起提交——这些是同一次测量的产物，分开提交就等于把一次测量拆成了两棵树。
4. 测量需要 Pillow 与字体；Windows 自带字体，缺了画图脚本会自己说要怎么解决。

**仍然没被解决的两件事**（本轮不在范围内，留给下一轮）

- 卡片**不是**数字的唯一副本：`docs/portfolio.md` 等对外素材里手写的数不在这个机制里
  （见 `docs/reports/figures-coverage-design.md` §2.6 的盘点）。
- 如果测量在「报告已落盘、卡片还没画」的一瞬间被杀，盘上就会留下一个旧卡片，
  下一轮测量会在代码轮红掉。这一轮把它修到了「正常跑完就一定一致」，
  但没有去处理「中途被杀」这种半截状态——那需要的是事务性的写盘，不是再画一次。
