# 证据包清单的第四个键 —— C16 的落地记录

日期：2026年11月20日 · 分支 `claude/zen-gauss-58179a`
worktree `E:\Dexatlas\.claude\worktrees\intelligent-jemison-7cbe0f` · 基线树 `469dbf3`

> **一句话**：候选 **C16** 已完成——证据包清单的 `not_included` 加了第四个键
> **`outside_analysis`**，`schema_version` 从 1 升到 **2**；三处钉死与两份 M10 材料
> 同步改齐；仓库里**四个已入库的旧包**（schema 1）已用新代码**重新分析并导出**，
> 案例研究里的 sha256 与 run id 同步更新；红→绿已证。
> **本窗口没有跑** `scripts/refresh-report-figures.py`，**报告数字与 tag 留给主会话
> 合入后统一重测**。

---

## 0. 这一层补的是什么

C10 那一轮把「包里只有本次分析」写在了**能被执行的地方**：打包时的守卫
（`src/dexatlas/reports/evidence_package.py` 的 `_why_not_an_analysis_file`）
挡住反编译树之外的文件与指向树外的链接，5 条红→绿测试守着它。但**清单本身
没有声明这件事**——读者打开 `manifest.json`，看到的是三个「少带了什么」的键，
没有一条说「包里只装本次分析自己的文件」。

C16 把这条边界**声明**出来。读者现在打开清单就能看到：

```json
"not_included": {
  "apk": "the analysed APK is not packaged; identify it by its SHA-256",
  "full_sources": "only the source fragments the evidence cites are packaged",
  "unrelated_strings": "string constants that no evidence record cites are not packaged",
  "outside_analysis": "the package holds only the files of this analysis: a file from outside the decompiler's output trees, or reached through a link out of them, is not packaged"
}
```

键名 `outside_analysis` 与现有三键同风格（名词短语），文案说的是**正面事实**
（only the files of this analysis）加**两条 otherwise 的进路**（树外文件、树内链接）。

## 1. 改了什么

### 1.1 代码与契约侧（五个文件、九处钉死，照 v1.1.0-candidate-c10-manifest.md §1.2 的表）

| # | 文件 | 改成 |
|---|---|---|
| 1 | `src/dexatlas/reports/evidence_package.py` | `PACKAGE_SCHEMA_VERSION = 2`（注释写明 v2 增加了第四键） |
| 2 | 同上 | `NOT_INCLUDED` 四个键 |
| 3 | `tests/test_public_contracts.py` | `test_the_evidence_package_manifest_is_versioned` 断言 `== 2` 与四键集合 |
| 4 | 同上 | （同一函数内的 `NOT_INCLUDED` 集合断言） |
| 5 | `tests/test_evidence_package.py` | `test_the_clients_apk_and_the_whole_source_tree_stay_out` 的整段字面量加第四键 |
| 6 | `scripts/m10_selfcheck.py` | `check_evidence_boundary_contract` 的 `expected = {"apk", "full_sources", "unrelated_strings", "outside_analysis"}`（**阻塞级**） |
| 7 | 同上 | 检查项名改为「证据包 not_included 声明 apk/full_sources/unrelated_strings/outside_analysis」 |
| 8 | `docs/architecture/public-contracts.md` | §5.3 形状块：`schema_version: 2`、`not_included: {apk, full_sources, unrelated_strings, outside_analysis}` |
| 9 | 同上 | 「清单的形状与 `schema_version = 1` 不变」改为升版说明；「包内只有本次分析」段补一句「清单的第四个键把这条边界声明出来」 |

### 1.2 M10 验收材料（活材料，四处文件）

- `docs/reports/m10-acceptance-pack.md`：D3 与 G5 的判据补上第四键；§3.4 预期改为
  「四个键」；§3.5 第 3 步同改；§7 M7 清单补「只装本次分析自己的文件」。
- `docs/reports/m10-reader-package.md`：§3.6 数据边界的「三个键」改四个键，并补一句
  第四键的含义。
- `docs/reports/m10-reader-kit.md`：Q5 的核对口径补「且只装本次分析自己的文件」。
- `docs/reports/m10-review-record-template.md`：G5 的记录说明改「四键声明」。
- `docs/reports/m10-selfcheck.md`：检查项表与 §4 第 4 条的「三键」改「四键」。

### 1.3 契约版本声明

- `CHANGELOG.md` `[Unreleased] → Changed` 新增一条：升版是**破坏性变更**
  （新代码的 `verify_package` 拒绝 schema 1 的旧包），按契约表 §6 的政策显式声明；
  同时把 C10 那一条里「清单的形状与 `not_included` 三键未变（那是公共契约，另议）」
  的「另议」收口为「由下一条落地」。

## 2. 四个已入库的旧包怎么处置的

`docs/case-studies/attachments/` 下的四个包（demo / api-integration / obfuscated /
multidex）都是 `schema_version = 1`，新代码的 `verify_package` 会拒绝它们。
按作者批准的方案**重打**：用新代码对三个一方样本**重新分析并导出**（demo.apk
分析两次——CLI 一次、REST API 一次，四个包对应四次独立分析，`run_id` 两两不同；
REST 那次先 `DELETE /projects/{id}` 再上传，否则 `POST /analyze` 对已完成项目短路，
两个包会拿到同一个 run id）。散装报告从**包内 `reports/` 复制**（案例研究的口径：
散装与包内逐字节一致），不是 `analyze -o` 直出的 CRLF 版本。

| 包 | 新 run_id | 新包 sha256 | 字节 |
|---|---|---|---|
| `demo-evidence-package.zip` | `run_bc38a1ba488449b6` | `a2318a03615e8bc430c01a70d220468f91df7acf9385d66485091b1c2c70b75b` | 6,961 |
| `api-integration-evidence-package.zip` | `run_aafda311d9864a4a` | `3bbf9462abf58b87db72361d6e8b30f1b21142c5b5b1a91a6f57d16b4d093058` | 6,954 |
| `obfuscated-evidence-package.zip` | `run_6646f0a97a0c4401` | `d3a796fe107db25b035451d8fcc09b049d0e90d395fdd27d1641fa5d41cb94d7` | 6,276 |
| `multidex-evidence-package.zip` | `run_d1b4246fe1054c63` | `1a96cf7975b3fb82cdb2f4bc88a77630ddb31b1b4ef9f2184c009d55400b7be3` | 6,369 |

四个包全部通过 `verify_package` 与 `verify_citations`（`citations_resolved: True`，
无 unresolved）；每个包内 `reports/report.{md,json,html}` 与对应散装报告
**逐字节一致**（sha256 已复算）。报告计数与案例研究声称的一致：demo 与
api-integration 5 类 / 8 方法 / 23 call site / 21 call edge / 11 证据；
obfuscated 4 / 11 / 10 / 9 / 8；multidex 4 / 11 / 13 / 10 / 9。

**连带更新的文档**（案例研究正文里的 run id、耗时、sha256；对照报告加历史标注）：

- `docs/case-studies/README.md`：四个 run id、指向本报告；
- `docs/case-studies/demo-app-walkthrough.md`：`run_bc38a1ba…`、3.6 s、
  report.json sha256 `29194a2d…`、schema 2 说明；
- `docs/case-studies/obfuscated-app.md`：`run_6646f0a9…` / `run_d1b4246f…`、
  3.5 s / 3.4 s、report.json sha256 `0c59d1b4…`、schema 2 说明；
- `docs/case-studies/api-integration.md`：`run_aafda311d9864a4a`（三处）、
  report.md sha256 `af3f00d7…`、schema 2 说明；
- `docs/reports/case-studies-third-package.md`、`case-studies-client-read.md`、
  `c5-c6-status-alignment.md`：顶部加历史标注（描述的是上一批 schema 1 包）；
- `docs/reports/next-engagements.md`、`outreach-publish-checklist.md`、
  `v1.1.0-candidates.md`、`docs/reports/README.md`、
  `docs/outreach/publish-review.md`：run id 与哈希的引用同步或加注。

## 3. 红→绿怎么证的

新增 2 条测试（`tests/test_evidence_package_isolation.py`，文件 docstring 一并说明
第四键的存在）：

| 测试 | 断言 |
|---|---|
| `test_the_manifest_declares_the_package_holds_only_the_analysis` | 导出的包里 `manifest.json` 的 `not_included` **有** `outside_analysis` 键，且文案含「only」与「link」——声明正面事实与两条进路 |
| `test_the_declared_boundary_names_everything_the_guard_refuses` | `NOT_INCLUDED` 的键集合**恰为**四键——声明的边界与执行的边界是同一条 |

**红**（改动前，基线 `469dbf3` 上先跑）：

```
FAILED tests/test_evidence_package_isolation.py::test_the_manifest_declares_the_package_holds_only_the_analysis
FAILED tests/test_evidence_package_isolation.py::test_the_declared_boundary_names_everything_the_guard_refuses
2 failed, 5 passed in 1.55s
```

第一条的失败原文就是缺口本身：

```
assert 'outside_analysis' in {'apk': '…', 'full_sources': '…', 'unrelated_strings': '…'}
```

即：**旧清单（三键）下，一个带树外链接/树外文件的包照常打包并通过校验，
清单对「包里只有本次分析」无话可说**——这正是 C16 要补的声明缺口
（注意与 C10 的红不同：C10 证的是「内部材料会被复制进包」，本条证的是
「清单对边界沉默」；C10 的守卫在位，所以包内容是干净的，缺的是声明）。

**绿**（实现后）：同文件 7 条全过；连同 `tests/test_evidence_package.py` 与
`tests/test_public_contracts.py` 共 53 过、1 失败——那 1 条
（`test_the_cli_counts_the_files_the_reader_finds_in_the_zip`）是**既存环境问题**
（Rich 在本 worktree 的长路径下把 CLI 输出折行），已用 stash 验证它在**未改动的
HEAD 上同样红**，与本改动无关（evidence-package-isolation.md §5 有记录）。

`uv run --no-sync python scripts/m10_selfcheck.py`：
`D3.not-included` 判**过**（阻塞级），汇总「通过 43，失败 0，需人工 40」，
退出码 0。

## 4. 门禁与验证

本窗口跑过的：

- `uv run --no-sync pytest tests/test_evidence_package_isolation.py tests/test_evidence_package.py tests/test_public_contracts.py -q` → 53 过 1 失败（既存环境问题，HEAD 上同红）；
- `uv run --no-sync python scripts/m10_selfcheck.py` → 通过 43 / 失败 0 / 需人工 40，退出码 0；
- 四个新包 `verify_package` + `verify_citations` 全过；
- 散装 vs 包内 sha256 逐字节一致（4 包 × 3 格式）。

**留给主会话的**（本窗口按纪律没有做）：

- `scripts/refresh-report-figures.py` 的统一重测——本轮改了 `src/` 与 `tests/`，
  源指纹已变，报告数字、README 徽章与 tag 由主会话合入后处理；
- `ruff format --check` / `mypy` / `vulture` / `check-doc-citations` /
  `check-version-claims` / `check-unguarded-numbers` / `check-m10-snapshot` 的全量门禁
  跑一遍（`check-doc-citations` 会需要把本报告与契约文档的新行号重锚）。

## 5. 没核实什么、为什么

| 没核实的 | 为什么 |
|---|---|
| 重打包的**字节级可复现** | run id 是 `uuid4()`，`generated_at` 是当下时间——两次运行不可能逐字节相同。可复现的是**计数与结构**（已核），不是字节 |
| 旧包在新代码下**确实被拒** | 没有留 schema 1 的旧包做反例（四个都重打了）；拒绝逻辑本身有测试（`tests/test_evidence_package.py` 的版本断言）。下游若有缓存旧包的读者，按 CHANGELOG 的声明升级 |
| M10 材料的**外部读者视角**通读 | 判据措辞改了四处文件，但没有重走一遍读者演练；那是 C2 独立验收的事 |
| `docs/glossary.md` 对候选清单的行号引用 | C13 那一轮的归属（登记轮已记录），本轮未动 |

## 6. 复现方式

```bash
# 重打一个包（以 demo 为例；JADX/Apktool 用 DEXATLAS_JADX_PATH / DEXATLAS_APKTOOL_JAR 指路）
DEXATLAS_WORKSPACE=$PWD/.scratch/c16/workspace \
DEXATLAS_JADX_PATH=E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat \
DEXATLAS_APKTOOL_JAR=E:/Dexatlas/.scratch/backends/apktool.jar \
  uv run --no-sync dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json --html report.html
DEXATLAS_WORKSPACE=$PWD/.scratch/c16/workspace \
DEXATLAS_JADX_PATH=E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat \
DEXATLAS_APKTOOL_JAR=E:/Dexatlas/.scratch/backends/apktool.jar \
  uv run --no-sync dexatlas export apk_80a8fe0e81204c9f -o demo-evidence-package.zip

# 读一个包的清单形状
python -c "import zipfile,json; m=json.loads(zipfile.ZipFile('docs/case-studies/attachments/demo-evidence-package.zip').read('manifest.json')); print(m['schema_version'], sorted(m['not_included']))"
# → 2 ['apk', 'full_sources', 'outside_analysis', 'unrelated_strings']
```
