# 案例材料的客户视角复核（只读）

日期：2026年11月18日 · 复核基准：本 worktree 的 `9e1aa61`
（`git rev-parse HEAD`）。

> **⚠️ 2026年11月20日起，本文核对过的四个证据包（schema 1）已被重新分析并导出**
> （清单的第四个键，`schema_version = 2`），包哈希与 run id 已全部更换；
> 当前附件的实测见 [c16-manifest-fourth-key.md](c16-manifest-fourth-key.md)。
> 本文的核对记录保留的是**上一批包**的状态，供对照——正文里引用的
> `run_e8e49384…` / `run_dd897202…` / `run_4fde2fa0…` / `run_fc8e432d…`
> 与各处耗时都是**当时**的实测，不是当前附件的。

> **本文是什么**：一次**只读**复核的产物。它站在「一个客户 / 一个要评估这个项目的人」
> 的位置上，把 `docs/case-studies/` 的三篇走查、案例索引、四个证据包，以及
> `docs/reports/case-studies-run-correspondence.md`、
> `docs/reports/case-studies-third-package.md`、`docs/outreach/` 五份素材
> （其中 `publish-review.md` 是内部核对记录，不外发）、
> `docs/portfolio.md`、`docs/service-commitments.md` 放在一起读一遍，
> 回答一个问题：**读完这些材料，客户会不会数错、会不会被误导？**
>
> **本文不是什么**：不是验收结论，不是改稿。**复核轮**一个既有文件都没有改，
> 只新增了本文一个文件。所有改动留给主会话统一做。
> **处置轮（2026-11-18）**的结果记在 [§7](#7-处置2026-11-18处置轮追加)——
> §1–§6 是复核轮的原样产出，结论与行号未动。
>
> **本轮纪律**：没有运行 `dexatlas analyze`、没有重新生成任何附件、
> 没有运行 `scripts/refresh-report-figures.py`、没有跑 `pytest`、没有联网、
> 没有 `git stash`。只做了只读操作：`Read` / `Grep` / `sha256sum` /
> `unzip` 到 `.scratch/` / `git show` / 纯标准库的 DEX 头解析。
> 没有动 `src/`、`tests/`、`scripts/`、`CHANGELOG.md`、`README.md`、
> `README.zh-CN.md`、`docs/status.md`、
> `docs/reports/phase1-execution-report.md`。
>
> **行号口径**：本文引用的 `file:line` 一律指**基线 `9e1aa61`**（本轮只新增本文，
> 未动任何既有文件，行号不移动）。**本报告的行号锚在哪棵树：** 全部锚在提交
> **`9e1aa61`** 上，那棵树的测量指纹是 `sha256:d0e85b61…`；**本报告里的 `file:line`
> 只在 `9e1aa61` 上成立**。这是本仓库自己的规矩：读一份报告之前先看它锚在哪棵树上。
>
> **临时文件**：`.scratch/client-read/`（解包出来的四个包），已被 `.gitignore` 忽略。

---

## 0. 结论速览

| 问题 | 结论 | 依据 |
|---|---|---|
| 四处材料的「数」是不是同一个数？ | **客户材料内是的**（四个包 / 四次分析 / 三个一方样本 / 三篇走查）；**仓库里有三处仍以现在时写旧数**（CHANGELOG、发版说明、已发布的 Release 正文） | §2.3、§2.6、§3 |
| 「demo 与 api-integration 共用一次运行」这件事说清了吗？ | **说清了，而且能被字节级证明**。四处材料都写明是两个 run id、两次分析；实测两个包的 `report.md` / `report.html` 各只差 2 行（run id 与 Analysis time） | §3.4 |
| 包里的东西与文档说的对得上吗？ | **对得上**：12 个 manifest 条目的 sha256 与字节数全部核对通过；散装报告与包内 `reports/` 逐字节相同；包内 `apk_sha256` 与仓库里三个 APK 的实际 sha256 一致 | §3.1–§3.3 |
| 有过度承诺吗？ | **没有**。三篇走查都写了「不能证明什么」，证据边界清楚 | §3.9 |
| 英文读者会不会读错？ | **会，有 4 处**（与 `english-reader-review-2.md` 同一把尺子：「他读完会不会相信一件不成立的事」） | §4 |
| 发现条数 | **11 条**：严重 2 / 中 4 / 低 5 | §2、§3 |

**最要紧的三条：**

1. **`demo-app-walkthrough.md` 自己的类数是 4 / 5 / 6 三个数**——§3.1 的输出与附件报告
   都写 5，§4 的证据表只列了 4 个类，§5 的结论句字面读是 6；而
   `examples/demo-app/demo.apk` 的 DEX 头实测 `class_defs_size = 4`。
   客户按任何一处去数，都能数出一个跟别处不一样的数。（§2.1）
2. **同一篇走查里 §3 的会话有两个耗时**：抬头写 `4.9 s`，§3.1 引用的输出写 `(5.0s)`。
   `4.9 s` 是**旧**附件报告里的 `Analysis time`（git 历史可证），补包时换了后半句、
   忘了前半句。（§2.2）
3. **CHANGELOG 的 v1.0.0 段仍以现在时写「三个证据包 / 9 个文件」**，
   而 `## [Unreleased]` 段没有记这一轮附件集更换。CHANGELOG 是这批材料里最像
   「对外文案」的一份，客户打开 `attachments/` 数到的是 16 个文件、4 个 zip。（§2.3）

---

## 1. 方法与边界

**怎么当客户。** 本轮读了：`docs/case-studies/README.md`、三篇走查、
`attachments/` 下 16 个文件（4 个 zip 全部解压）、两份实测报告
（`case-studies-run-correspondence.md`、`case-studies-third-package.md`）、
`docs/outreach/` 五份素材、`docs/portfolio.md`、`docs/service-commitments.md`，
以及 CHANGELOG、`docs/releases/v1.0.0.md`、
`docs/reports/v1.0.0-github-release-body.md`、`docs/reports/final-outward-consistency.md`、
`docs/reports/outreach-final-review.md`、`docs/reports/next-engagements.md`、
`docs/status.md` 里提到案例材料的段落。

**做了哪些实测。**

- 16 个附件逐个 `sha256sum`；
- 4 个 zip 解压到 `.scratch/client-read/x-*/`，逐个文件重算 sha256 与字节数，
  与 `manifest.json` 的 `files[]` 对账，并与散装同名文件对账；
- 4 个 `manifest.json` 的 `project_id` / `run_id` / `apk_sha256` 抄出来互相比对；
- 4 个 `report.json` 的 `schema_version`、`run.*`、`summary.*` 抄出来与走查正文对账；
- 用纯标准库解析三个 `examples/*.apk` 的 DEX 头（`class_defs_size`）与
  `class_def` 表，取出实际定义的类名清单；
- `git log -p --follow` 追两处耗时的来源；
- `src/dexatlas/` 里核对 MCP 工具注册数、`POST /analyze` 的状态码、
  `AnalyzeJobResponse` 的字段、`readOnlyHint` 注解、类索引的合并口径。

**没做什么。** 没跑分析、没重生成附件、没跑测量脚本、没跑测试、没联网、没改任何既有文件。
因此本文**不**评价报告里那些由脚本生成的数字（测试数、覆盖率、源指纹），
也**不**评价主会话正在重测量的那四份文件。

**判据。** 与 `english-reader-review-2.md` 同一把尺子：**他读完会不会相信一件不成立的事**。
每条发现给三样东西：原文（逐字）→ 客户会怎么数 / 怎么误读 → 建议改法。
按后果排序。

---

## 2. 必须改的（按后果排序）

### 2.1 【严重】demo 走查的类数在同一篇文档里有 4 / 5 / 6 三个数，且都不是 APK 的类数

**原文（逐字）**

`docs/case-studies/demo-app-walkthrough.md:60-61`（§3.1 引用的 CLI 输出）：

```
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges,
  1 resource string (5.0s)
```

`docs/case-studies/demo-app-walkthrough.md:210`（§4 的证据表最后一行）：

```
| E-0008…11 | verified | declaration | Class declarations: Crypto, MainActivity, NetworkClient, SyncService | `androguard 4.1.4 → classes.dex#…` |
```

`docs/case-studies/demo-app-walkthrough.md:224-225`（§5 结论）：

```
the whole surface is four classes plus one activity, one service.
```

附件 `docs/case-studies/attachments/demo-report.md:17`：

```
| Classes indexed | 5 |
```

附件 `docs/case-studies/attachments/demo-report.json`（E-0007 的 detail）：

```json
"decompilation": {"methods_decompiled": 7, "methods_total": 8,
                  "classes_with_source": 5, "classes_total": 5, ...}
```

**实测**

`examples/demo-app/demo.apk` 里只有一个 `classes.dex`。解析它的 DEX 头，
`class_defs_size = 4`，`class_def` 表里的四个类名是：

```
Lcom/example/demo/Crypto;
Lcom/example/demo/MainActivity;
Lcom/example/demo/NetworkClient;
Lcom/example/demo/SyncService;
```

`examples/demo-app/smali/` 下也只有这 4 个 `.smali` 文件。
**APK 实际定义的类数是 4。**

**客户会怎么数 / 怎么误读**

- 按 §3.1 数 → **5**；
- 按 §4 的证据表数（E-0008…E-0011）→ **4**；
- 按 §5 那句话字面读（four classes **plus** one activity, one service）→ **6**；
- 打开 APK 数 → **4**。

四处给出四个不同的数，而这一篇走查的卖点恰恰是「每条结论都能回溯到字节」。
更要紧的是：**没有一个数是 4**，所以客户无论按哪一处数，都数不到 APK 的真实类数。

**为什么会这样（推断，供工具侧判断）**

`src/dexatlas/core/pipeline.py:290` 把 androguard 的 `dex_classes` 写进证据表，
`pipeline.py:300` 又用 `_merge_classes(classes)` 把 androguard 的 DEX 类视图与
JADX 的反编译类视图**合并去重**，`pipeline.py:311` 之后 `save_symbols` 落库，
`src/dexatlas/core/storage.py:1065` 的 `class_count` 取的是 `classes` 表的行数。
所以 `Classes indexed` 是**两个后端类视图的并集**，不是 APK 定义的类数。
旁证：obfuscated 样本（DEX 4 类 / jadx 4 类 → 报告 4 ✓）与 multidex 样本
（DEX 5 个类定义、`SharedConfig` 在两个 DEX 各定义一次 → 去重后 4，报告 4 ✓）
都对得上，**只有 demo 出现了 4 → 5 的差**。

**建议改法**

1. **走查侧（必改）**：§5 那句改成不含加法歧义的写法，并写明 §3.1 那个「5」的口径，例如：

   > the whole surface is the four classes the evidence table names —
   > `Crypto`, `MainActivity`, `NetworkClient`, `SyncService` — one of them the
   > exported activity, one the exported service.

   并在 §3.1 的输出下面加一句口径说明：
   > `Classes indexed` counts the merged class index — the DEX definitions read by
   > androguard together with the classes JADX decompiled — so it can exceed the
   > number of classes the DEX defines; the four `class_def` entries in
   > `classes.dex` are the four the evidence table names.

2. **工具侧（另开一条，不属于本轮）**：`Classes indexed` 与 APK 实际定义的类数不等时，
   报告应说明多出来的那条来自哪个后端、叫什么。否则「5 个类」在报告里读起来就是
   「这个 APK 有 5 个类」，而它没有。

---

### 2.2 【严重】同一篇走查里，§3 那次会话有两个耗时

**原文（逐字）**

`docs/case-studies/demo-app-walkthrough.md:5-6`（抬头）：

```
**Run:** one `dexatlas analyze` — the session quoted in §3 took 4.9 s; the
attached package is a later run of the same APK (`run_e8e49384ab5246ab`, 4.5 s)
```

| | 抬头引文完 |
|---|---|

§3.1 引用的输出是下面这段（`docs/case-studies/demo-app-walkthrough.md:60-61`）：

```
✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges,
  1 resource string (5.0s)
```

（上行号仍指 `docs/case-studies/demo-app-walkthrough.md:60-61`。）

**实测（git 历史可证）**

- `git log -p --follow -- docs/case-studies/demo-app-walkthrough.md` 里，
  `1 resource string (5.0s)` 这行**只被加过一次，从未被改过**（它随文件一起进来，
  见 `d76972a`）；
- 而 `| Analysis time | 4.9 s |` 曾经是**旧附件报告**里的一行，后来被替换掉了
  （同一份 diff 里只有一次 `-`、一次 `+`）；
- 也就是说：抬头的 `4.9 s` 是**旧包**的耗时，补包那一轮把后半句改成了
  `run_e8e49384ab5246ab, 4.5 s`，前半句的 `4.9 s` 忘了改；
- 巧合的是，`4.9 s` 恰好是 **api-integration 那一次**运行的耗时
  （`api-integration-report.md` 的 `| Analysis time | 4.9s |`）——像是串了行。

**客户会怎么数 / 怎么误读**

抬头说 4.9 s，§3 引用的输出说 5.0 s，同一次会话。客户只有两种读法：
「文档抄错了」，或者「§3.1 那段输出不是真的那次会话」。两种都会削弱
「outputs quoted are the actual outputs of those commands」（`:50-51`）这句承诺。

**建议改法**：抬头改成 `the session quoted in §3 took 5.0 s`（与 §3.1 的输出一致）；
或者干脆不写这个数，只写 `the session quoted in §3; the attached package is a later
run of the same APK (run_e8e49384ab5246ab, 4.5 s)`。前者更好——5.0 s 就在下面一行。

---

### 2.3 【中】CHANGELOG 仍以现在时写「三个证据包 / 9 个文件」，Unreleased 段没有记这一轮

**原文（逐字）**

`CHANGELOG.md:300-306`（`## [1.0.0] — 2026-11-17` 段内）：

> - **逐例客户交付附件落盘（Phase 3 M7 收尾）。** 三个[案例](../case-studies/README.md)
>   的可下载交付件入库至 `docs/case-studies/attachments/`（9 个文件）：demo 与
>   API 集成案例（同一分析 `apk_80a8fe0e81204c9f`）与混淆案例
>   （`apk_2f8d476fb9e71ac4`）各含 Markdown/JSON/离线 HTML 报告与最小证据包
>   （`analyze --html` / `export` 生成，工具版本 jadx 1.5.2 / apktool 2.11.1 /
>   androguard 4.1.4 与报告内记录一致）；三个证据包均通过 `verify_package`
>   校验（manifest 含逐文件 sha256 与 `not_included` 三键声明）。

> （引文里的链接目标改成了从本文件位置能解析的等价路径，**可见文字逐字未改**——
> 否则仓库的相对链接门禁 `tests/test_docs.py::test_all_relative_links_resolve`
> 会因为「引文里的链接」而红。）

`CHANGELOG.md:8-45`（`## [Unreleased]` 段）：共 38 行，**没有一句提到附件集、
证据包或案例**。

**客户会怎么数 / 怎么误读**

CHANGELOG 是这批材料里最像「对外文案」的一份。客户读到「三个案例 / 9 个文件 /
三个证据包」，然后打开 `docs/case-studies/attachments/` 数到 **16 个文件、4 个 zip**。
这一条还比别的更糟：它不是历史段落里的旧数，而是**以现在时**写在「已入库至」后面的，
并且 `docs/case-studies/README.md` 的链接就挂在「三个」这个词上。

**建议改法**（CHANGELOG 本轮不由我改，留给主会话）

1. `## [Unreleased]` 的 `### Added` 下加一条，例如：

   > - **案例证据包扩到四个、覆盖四次独立分析。** 第 3 篇走查改用它自己那一次
   >   REST API 分析的包（`run_fc8e432d4d094350`），第 2 篇的 multi-DEX 附录
   >   补上自己的包与报告；`docs/case-studies/attachments/` 由 9 个文件变为
   >   16 个（4 个证据包 + 12 份散装报告），四个包的 `run_id` 两两不同。
   >   四个包的 `verify_package` 与 `verify_citations` 均通过。

2. v1.0.0 那条末尾加一句限定语（与 `english-reader-review-2.md` §6 的「两棵树」尺子一致）：

   > （本条记录的是 v1.0.0 发版时的附件集：9 个文件、3 个证据包。2026-11-18 起
   > 附件集已换过一轮，见 [Unreleased]。）

---

### 2.4 【中】`api-integration.md` §3.5 的最后一句与上一句互相否定

**原文（逐字）**

`docs/case-studies/api-integration.md:262-265`：

```
The upload here answers `completed` rather than `pending` because it hits the
same API, and that workspace already holds the project from §3.2 — the
short-circuit described above. The run it reports is the one that upload
started.
```

而 §3.2 讲的是相反的事（`docs/case-studies/api-integration.md:99-103`）：

```
`POST /analyze` takes a multipart upload, returns **202** with a job-shaped
body, and analyses in the background. The project id is the APK's sha256
prefix, so uploading the same bytes twice lands on the same project instead
of analysing it twice — the second response is the finished project, not a
new job. The `detail` field is where to poll.
```

**客户会怎么数 / 怎么误读**

§3.5 说这次上传短路了（没有新分析），紧接着又说「报出来的 run 是**这次上传**启动的」。
客户会得出结论：§3.5 那次 `client.analyze(...)` 启动了 `run_fc8e432d4d094350`。
但事实是——§3.2 的上传启动的才是那个 run，§3.5 的上传短路了；包里的
`manifest.json` 与 `api-integration-report.md:7` 记的也正是 §3.2 那一次。
这直接影响客户对「这次集成会产生几次分析」的理解。

**建议改法**：最后一句改成

```
The run it reports is the one §3.2's upload started.
```

---

### 2.5 【中】`case-studies-third-package.md` 说「examples/ 里四个 APK」，实际是三个

**原文（逐字）**

`docs/reports/case-studies-third-package.md:126-127`：

```
四个包的 `apk_sha256` 分别是 `80a8fe0e…` / `80a8fe0e…` / `2f8d476f…` /
`a488e43e…`，与 `examples/` 里四个 APK 的实际 sha256 一致（已核）。
```

**实测**

- `examples/` 下实际有 **5 个** APK：`demo-app/demo.apk`、`multidex-app/multidex.apk`、
  `obfuscated-app/obfuscated.apk`、`strings-app/strings.apk`、`wide-app/wide.apk`；
- 四个包只覆盖 **3 个不同的 APK**（`demo.apk` 出现两次：demo 包与 api-integration 包）；
- 那串 sha256 前缀本身是对的（`80a8fe0e…` / `80a8fe0e…` / `2f8d476f…` / `a488e43e…`），
  错的是「四个 APK」这个说法——它把「四个包」当成了「四个 APK」。

**客户会怎么数 / 怎么误读**

这句话是客户查哈希时的落点：`docs/case-studies/README.md:48-49` 与
`docs/case-studies/api-integration.md:233-234` 都把客户指向这份报告，
作为「四个 run id 与实测哈希」的出处。客户照着这句话去 `examples/` 里找
「四个 APK」，会找到五个文件，而且其中两个 hash 前缀是一样的。

**建议改法**

```
四个包的 `apk_sha256` 分别是 `80a8fe0e…` / `80a8fe0e…` / `2f8d476f…` /
`a488e43e…`——**三个**不同的 APK，其中 `demo.apk` 出现两次（demo 包与
api-integration 包是同一份字节的两次分析）。`examples/` 下另有
`strings-app/strings.apk` 与 `wide-app/wide.apk` 两个样本，未进入案例材料。
```

---

### 2.6 【中】已发布的 GitHub Release 正文与仓库里的发版说明，仍说 nine files / three packages / two analyses

**原文（逐字）**

`docs/reports/v1.0.0-github-release-body.md:88-94`：

```
  rewritten case studies with their attachments committed under
  `docs/case-studies/attachments/` — nine files (six reports and three evidence
  packages), each generated by the command printed in its study; the three
  evidence packages were checked with `verify_package`, and they cover two
  analyses — the demo and api-integration packages come from one run. A reader
  can open the HTML offline or unzip a package and check its manifest hashes
  without installing DexAtlas.
```

`docs/releases/v1.0.0.md:55-62`：

```
- **M7 — client-ready deliverables.** Offline single-file HTML reports
  (`analyze --html`), minimal evidence packages (`dexatlas export`), and three
  rewritten case studies. The per-case deliverables are committed under
  [case-studies/attachments/](../case-studies/attachments/) — nine files:
  report Markdown/JSON/HTML plus a minimal evidence package for the demo/API
  case (`apk_80a8fe0e81204c9f`) and the obfuscated case
  (`apk_2f8d476fb9e71ac4`), each generated by the commands printed in its
  study and checked with `verify_package`.
```

**客户会怎么数 / 怎么误读**

这一段在 GitHub 上**已经发布**了（v1.0.0 的 Release 正文）。客户点开 Release 看到的
就是「nine files（six reports and three evidence packages）」和「they cover two
analyses」——两句话今天都不成立，而且「two analyses」在仓库里是**被明文推翻过**的结论。
仓库里的 `docs/releases/v1.0.0.md` 是同一句话的中文对照。

按 `english-reader-review-2.md` §6 的「两棵树」尺子，这些文档记录的是**发版树**的状态，
它们需要的是一句限定语，而不是改数——改了数就和已发布的 tag 对不上了。

**建议改法**

- `docs/releases/v1.0.0.md` 与 `docs/reports/v1.0.0-github-release-body.md` 各加一句：

  > (As of the `v1.0.0` tag: nine files, three evidence packages, covering two
  > analyses. The attachment set was replaced on 2026-11-18 — four packages,
  > sixteen files, four analyses; see
  > `docs/case-studies/README.md`.)

- GitHub 上已发布的那一份改不了：要么在 v1.0.0 Release 上补一条 comment，
  要么等下一个 release 的正文里说清。**这一条需要人决定**，本轮只报出来。

---

### 2.7 【中低】`final-outward-consistency.md` 的「数字一致」结论与它引用的句子都已过期

**原文（逐字）**

`docs/reports/final-outward-consistency.md:56`：

```
| 案例附件 **9 个文件** / **3 个证据包** / 覆盖 **2 份分析** | `CHANGELOG.md:262`–`:266`（9 个文件、三个证据包、两个 project id）；`docs/releases/v1.0.0.md:57`–`:61`（nine files、两个 project id）；`docs/reports/v1.0.0-github-release-body.md:92`–`:94`（nine files，**未提覆盖几份分析**）、`:235`；`docs/portfolio.md:108`–`:110`（「the same analysis」）；`docs/status.md:134`（未给数） | `docs/case-studies/README.md`（三案例、三样本、三包、两份分析）；`docs/case-studies/attachments/` 实为 9 个文件、3 个 zip | 数字一致；**「三包只覆盖两分析」仅 `docs/case-studies/README.md` 披露** → 见 §3 第 20 条 |
```

**客户会怎么数 / 怎么误读**

这一行的结论字是「**数字一致**」——今天不成立了：附件集已经是 16 个文件 / 4 个包 /
4 次分析。而且它引用的 `docs/portfolio.md:108`–`:110`（「the same analysis」）
也已经不是 `portfolio.md` 现在的写法了：现在写的是
`docs/portfolio.md:115-118` 的「a second, **independent** analysis of the same demo app」。
一份「发布前最终一致性复核」如果还留着「数字一致」这个结论，客户会以为发布前的那次
复核覆盖到了今天。

**建议改法**：在该表上方（或本报告抬头）加一句限定语，例如：

```
> **附件集在 2026-11-18 换过一轮**（3 包 / 9 文件 → 4 包 / 16 文件，
> 覆盖 2 次分析 → 4 次分析）。本文这一行按 v1.0.0 发版树记录；
> 现状见 [case-studies-third-package.md](case-studies-third-package.md)。
```

---

### 2.8 【低】「四次分析」这个数没有一处说明它是「有包的那四次」——三篇走查里能数出 7 次运行

**客户会怎么数 / 怎么误读**

客户读完三篇走查，会数出 **7 次**分析：

| 走查 | §3 引用的会话 | 附件那一跑 | 小计 |
|---|---|---|---|
| 1（demo） | 1 次 CLI `analyze`（§3.1） | `run_e8e49384ab5246ab` | 2 |
| 2（obfuscated） | 2 次（obfuscated 5.1 s、multidex 4.8 s） | `run_dd897202eba74e28`、`run_4fde2fa0b5254ccb` | 4 |
| 3（api-integration） | 1 次（`run_fc8e432d4d094350`，§3.5 的上传短路，不新增） | 同一次 | 1 |

而索引与对外文案统一说的是「四个包 / 四次分析 / one package per analysis」。
两句话都对，但**没有一个地方把它们接上**：客户要么以为「只有四次分析，
那另外三次是什么」，要么以为「分析了七次，为什么说四次」。

**建议改法**：`docs/case-studies/README.md` 的附件段（`:20-27`）加一句：

```
The three walkthroughs quote seven runs in total; four of them are the ones the
evidence packages were made from — one package per analysis.
```

---

### 2.9 【低】索引说「four packages, twelve report files」，没写 `attachments/` 里共 16 个文件

**原文（逐字）**

`docs/case-studies/README.md:20-22`：

> **Attachments:** [`attachments/`](../case-studies/attachments/) holds four evidence packages
> and the loose report files the walkthroughs link to — **four packages, twelve
> report files**.

**客户会怎么数 / 怎么误读**

客户打开 `attachments/` 数到 16 个文件，而索引给的是「四个包 + 十二份报告」——
要把两个数加起来才知道 16。内部文档 `docs/outreach/publish-review.md:125`
写了「共 16 个文件」，但那是内部记录、客户看不到。

**建议改法**：改成 `— **four packages, twelve report files, sixteen files in all**`。

---

### 2.10 【低】`demo-app-walkthrough.md` 的 "on screen 8" 指向不明

**原文（逐字）**

`docs/case-studies/demo-app-walkthrough.md:214-215`：

```
position inside it. Opening the report on screen 8, or via
`analyze -o report.md`, prints the same table — the workbench renders the
renderer's output byte for byte (measured in the
```

**实测**：`src/dexatlas/workbench/app.py` 里的界面是 upload / index→source→evidence /
calls / report export / benchmark 五块（`:239`、`:289`、`:466`），**没有编号为 8 的屏**。
这句自 `d76972a` 起就在，原样未改。

**客户会怎么数 / 怎么误读**：英文读者读到 "on screen 8" 会以为 workbench 里有一块
编号 8 的界面，找不到；也可能以为漏了一个上下文（比如「第 8 号屏幕」是别的文档里的编号）。
对一个主张「每条结论都能回溯」的走查来说，这是一个指不到东西的指针。

**建议改法**：改成 `Opening the report in the workbench's report screen, or via
`analyze -o report.md`, prints the same table`。

---

### 2.11 【低】multi-DEX 附录说索引「keeps both」，但摘要行是 4 classes，没把「5 个定义 → 4 个类」讲清

**原文（逐字）**

`docs/case-studies/obfuscated-app.md:306-312`：

```
jadx keeps one copy and warns about the dropped one; androguard's symbol index
keeps **both**, each with a locator naming the DEX file it was read from. The
call-site rows carry a `dex_name` column (`classes.dex` / `classes2.dex`), so
every call site says which container it was read from — the raw material an
analyst needs to reason about what a class-loader would actually resolve.

The summary for this run: 4 classes, 11 methods, 13 call sites, 10 call edges,
evidence records E-0001…E-0009, jadx 7 of 11 methods decompiled, 4.8 s.
```

**实测**：`multidex.apk` 有两个 DEX，`class_defs_size` 合计 **5**
（`classes.dex` 2 个、`classes2.dex` 3 个），其中 `SharedConfig` 在两个 DEX 里各定义一次；
报告的 `Classes indexed` 是 **4**（去重后）。

**客户会怎么数 / 怎么误读**：客户读完「androguard 的索引 keeps **both**」，
再看下一段的「4 classes」，会以为报告少算了一个类，或者以为「both」是指两条证据记录。
这一篇附录的主题**恰好**就是去重，所以这里是读者最会停下来的地方。

**建议改法**：在摘要句前补一句，把口径讲明：

```
`Classes indexed` counts distinct classes, so the five class definitions in the
two DEX files are four classes — `SharedConfig` is defined twice and counted
once. Both definitions stay in the symbol index, each with its own locator.
```

---

## 3. 查过且没问题的部分

以下都实测过，可以放心。

### 3.1 四个包 = 四次分析，`run_id` 两两不同 ✓

| 包 | `project_id` | `run_id` | 包 sha256（实测） | 字节 |
|---|---|---|---|---:|
| `demo-evidence-package.zip` | `apk_80a8fe0e81204c9f` | `run_e8e49384ab5246ab` | `7bd4b000ade2c2d0a95475757e8eb94f01253b341d0dc71ff042ae5cccaea4e6` | 6,873 |
| `obfuscated-evidence-package.zip` | `apk_2f8d476fb9e71ac4` | `run_dd897202eba74e28` | `5b129b2d5b99fa64304d1484f50b2d3f1281f13c5405d0e7f79543758410113b` | 6,200 |
| `multidex-evidence-package.zip` | `apk_a488e43e38c2b8e9` | `run_4fde2fa0b5254ccb` | `a8c03be8fb001e67b41bae34413977d040d76ac5707b6f48572352bfb01af950` | 6,279 |
| `api-integration-evidence-package.zip` | `apk_80a8fe0e81204c9f` | `run_fc8e432d4d094350` | `139c33915b62bd4a4452fada579ba4842a3f0754f2bd945ddf6dff5d7d9d5bb4` | 6,867 |

四个 `run_id` 两两不同 ✓；前三个与 `docs/reports/case-studies-third-package.md:119-124`
表里记的**完全一致**（含包 sha256 与字节数）。

### 3.2 12 个 manifest 条目的 sha256 与字节数全部核对通过 ✓

对 4 个包各 3 个文件（共 12 条）重算 sha256 与字节数，**12/12 与 `manifest.json`
的 `files[]` 一致**；包内的 `reports/report.*` 与 `attachments/` 下的散装同名文件
**逐字节相同**（12/12）。

### 3.3 包内 `apk_sha256` 与仓库里的样本一致 ✓

`demo.apk` = `80a8fe0e…7969ff9`、`obfuscated.apk` = `2f8d476f…c299540`、
`multidex.apk` = `a488e43e…d309d55`——三个 APK 在**当前仓库里**重算的 sha256
与四份报告/manifest 记的完全一致（demo 被两个包引用）。客户按走查给出的哈希
能下载到同一份字节。

### 3.4 「demo 与 api-integration 是同一份样本的两次不同分析」——说得明白，且可证 ✓

- `docs/case-studies/README.md:35-45`：明写「三篇走查覆盖三个一方样本……
  case study 1 与 3 分析的是同一个 demo-app APK」「四个证据包来自四次不同的分析」，
  并把四个 run id 逐个列出；
- `docs/case-studies/api-integration.md:230-234`：明写「same bytes, same counts,
  different run id and different timing」；
- `docs/outreach/project-brief.md:127-135`：明写「四个证据包是四次不同的分析……
  demo 与 api-integration 两个包分析的是同一份 APK 的两次运行」，
  并补了「不是客户案例」的边界；
- `docs/outreach/publish-review.md:139-155`：把字节级比对写了出来；
- **实测**：`demo-report.md` 与 `api-integration-report.md` 的 diff 只有 2 行
  （`**Run:**` 一行、`| Analysis time |` 一行），`.html` 同样 2 行；
  `.json` 的差异是 run id、时间戳与 `duration_seconds`。

这是本次复核里**最扎实**的一处：说法、证据与客户能自己做的核对动作三样齐备。

### 3.5 走查引用的 run id 与包内 manifest 四对四全对 ✓

`demo-app-walkthrough.md:6,293` → `run_e8e49384ab5246ab` ✓；
`obfuscated-app.md:8,257` → `run_dd897202eba74e28` ✓；
`obfuscated-app.md:9,270` → `run_4fde2fa0b5254ccb` ✓；
`api-integration.md:5,222` → `run_fc8e432d4d094350` ✓。
（旧 run id `run_e112e717…` / `run_8d6735d4…` 只出现在
`case-studies-run-correspondence.md` 的历史记录里 ✓，那份报告在 `§0` 速览里
自己就标了「**后来补上了吗？——补上了（2026-11-18）**」并注明「本文的结论仍按基线树
`d43369b` 成立」✓。）

### 3.6 走查引用的计数与包内报告逐项一致 ✓

| 走查 | 声称 | 包内 `report.md` 摘要 | |
|---|---|---|---|
| 1（demo） | 5 类 / 8 方法 / 23 call site / 21 call edge / 11 证据 | 5 / 8 / 23 / 21 / 11 | ✓ |
| 2（obfuscated） | 4 类 / 11 方法 / 10 call site / 9 call edge / 8 证据 | 4 / 11 / 10 / 9 / 8 | ✓ |
| 2 附录（multidex） | 4 类 / 11 方法 / 13 call site / 10 call edge / 9 证据 | 4 / 11 / 13 / 10 / 9 | ✓ |
| 3（api） | 5 类 / 8 方法 / 23 call site / 21 call edge / 11 证据 | 5 / 8 / 23 / 21 / 11 | ✓ |

耗时也对得上：`report.json` 的 `run.duration_seconds` 分别是 4.516 / 4.985 / 4.703 /
4.937，报告里的 `Analysis time` 是 4.5s / 5.0s / 4.7s / 4.9s ✓（唯一对不上的是
`demo-app-walkthrough.md:5` 那个 `4.9 s`，见 §2.2）。

### 3.7 索引 README 的对应关系说明准确 ✓

`docs/case-studies/README.md:20-27` 说「study 1 links `demo-report.*`，study 2 links
`obfuscated-report.*` and `multidex-report.*`，study 3 links `api-integration-report.*`」——
与三个走查正文里的附件链接**逐个对得上** ✓，没有多余也没有缺失。

### 3.8 证据记录的出处齐全 ✓

`report.json` 里每条 evidence 都带 `provenance[]`，含 `tool` / `tool_version` /
`apk_sha256` / `locator`（抽查 E-0001 与 E-0007）——与
`demo-app-walkthrough.md:212-214` 的「Every record carries the full provenance」相符 ✓。

### 3.9 没有过度承诺 ✓

三篇走查都各有一节写「不能证明什么」：

- `demo-app-walkthrough.md:227-231`（**Not established here**：是否可利用、真实端点会做什么、
  是否像某个生产应用；并明说样本是一方的、常量是占位符）；
- `obfuscated-app.md:200-215`（**Not established here**：不判定这是恶意软件，
  「看起来像」不等于结论；并说明手写混淆的边界：没有控制流混淆、字符串加密、运行时加壳、JNI）；
- `api-integration.md:55-66`（**Out of scope**：认证、多租户、限流、横向扩展、写接口）。

索引 `docs/case-studies/README.md:13-18` 也统一声明「不是渗透测试，不对任何样本作恶意软件
分类，不主张任何东西可利用」。这一层是这批材料里做得最好的部分。

### 3.10 走查里引用的 API / MCP 契约与代码一致 ✓

- `api-integration.md:280-283` 列的 11 个 MCP 工具名，与
  `src/dexatlas/mcp/server.py:106-329` 注册的 11 个**逐个同名** ✓；「eleven read-only tools」
  与 `server.py:76-85` 的 `ToolAnnotations(read_only_hint=True)` 相符 ✓；
- `api-integration.md:342` 的「`POST /analyze` returns 202 with a job body」与
  `src/dexatlas/api/app.py:359-362`（`status_code=status.HTTP_202_ACCEPTED`）、
  `src/dexatlas/api/app.py:223-226`（`AnalyzeJobResponse` 的 `project_id` / `status` / `detail`）相符 ✓；
- `api-integration.md:259` 的「schema 3」与四份 `report.json` 的
  `"schema_version": 3` 相符 ✓。

### 3.11 `docs/service-commitments.md` 没有提到案例材料 ✓

全文检索没有一处提案例 / 走查 / 证据包，所以那里**不存在**会被数错的数。
（它提到「三个后端」的是 `analysis-provenance.md` 的口径，与案例材料无关 ✓。）

### 3.12 对外文案的「四包四跑」口径彼此一致 ✓

`docs/outreach/project-brief.md:120-135`、`docs/outreach/cover-letter-templates.md:29-36`、
`docs/outreach/publish-review.md:125-155`、`:351-355` 说的是同一件事：
**四个包、四次分析、三个一方样本、demo 与 api-integration 是同一份样本的两次运行、
不是客户案例**。四处没有互相打架 ✓。

### 3.13 `docs/portfolio.md` 的表述 ✓

`docs/portfolio.md:115-118`：「Three complete worked analyses — a walkthrough of the demo
app from upload to evidence chain, an obfuscated-sample study, and an integration study
that drives a second, **independent** analysis of the same demo app over the REST API
and the MCP server」——三篇走查 ✓，「第二次独立的分析」与两次不同的 run 一致 ✓。

---

## 4. 英文读者专项（与 `english-reader-review-2.md` 同一把尺子）

那把尺子是：**「他读完会不会相信一件不成立的事」**，外加「直接用了而没有一句解释的黑话」。

| # | 原文（逐字） | 英文读者会相信什么 | 实际 | 严重度 |
|---|---|---|---|---|
| E1 | `the session quoted in §3 took 4.9 s`（`demo-app-walkthrough.md:5`） | 那次会话跑了 4.9 秒 | §3.1 引用的输出写 `(5.0s)` | 高（§2.2） |
| E2 | `5 classes` / `four classes plus one activity, one service`（`:60`、`:225`） | 这个 APK 有 5 个类（或者 6 个） | DEX 里定义 4 个类 | 高（§2.1） |
| E3 | `The run it reports is the one that upload started.`（`api-integration.md:265`） | §3.5 的上传启动了一次新分析 | 这次上传短路了，run 是 §3.2 启动的 | 中（§2.4） |
| E4 | `Opening the report on screen 8`（`demo-app-walkthrough.md:214`） | workbench 里有编号 8 的界面 | 没有编号的界面 | 低（§2.10） |

**黑话（本轮新增的两条，标低）**

- **`call site` / `call edge`**：`demo-app-walkthrough.md:181-182` 解释得很清楚
  （「one method that calls the same target twice is two call sites and one call edge」）✓，
  但 `obfuscated-app.md:71-75` 与 `api-integration.md:343` 直接用这两个词，没有一句解释，
  而两处的两个数都不一样（10/9、23/21）。建议在这两篇首次出现处各加一句。
- **`smali`**：`demo-app-walkthrough.md:81` 用了 `smali representation`，没解释；
  `obfuscated-app.md` 里解释得较好（`:118-120` 说清 apktool 回退路径）。
  建议 demo 那篇加半句。

**一处值得表扬的英文写法**：`docs/case-studies/README.md:66-69`
「Analysis times are reported per run and will differ on other machines; the symbol and
evidence counts are deterministic for a given sample and backend set.」——一句就把
「哪些数会变、哪些不会」说清了，正是英文读者最需要的那句限定语。

---

## 5. 附：本轮实测到的事实（可复算）

**附件集（16 个文件）**

```
docs/case-studies/attachments/
├── api-integration-evidence-package.zip   139c339…5bb4   6,867 B
├── api-integration-report.html            1dafa26…f6768
├── api-integration-report.json            2491c02…bcf0b
├── api-integration-report.md              dd5e2a3…ec601
├── demo-evidence-package.zip              7bd4b00…aa4e6   6,873 B
├── demo-report.html                       5fe3485…0db82
├── demo-report.json                       921d3d3…67f63e
├── demo-report.md                         08140e8…8fd51
├── multidex-evidence-package.zip          a8c03be…af950   6,279 B
├── multidex-report.html                   5dbe419…18347
├── multidex-report.json                   0f9940c…5790b
├── multidex-report.md                     9d7ca4b…1d12f
├── obfuscated-evidence-package.zip        5b129b2…0113b   6,200 B
├── obfuscated-report.html                 6f311c3…05617
├── obfuscated-report.json                 0d5d2fa…f0f6
└── obfuscated-report.md                   5b0cd9f…61db5
```

**三个样本 APK 的 DEX 类定义数（实测）**

| APK | DEX 文件 | `class_defs_size` 合计 | 报告的 `Classes indexed` |
|---|---|---:|---:|
| `demo.apk` | `classes.dex` | 4 | **5**（见 §2.1） |
| `obfuscated.apk` | `classes.dex` | 4 | 4 ✓ |
| `multidex.apk` | `classes.dex` + `classes2.dex` | 5（去重后 4） | 4 ✓ |

**四次分析的时长**

| run | `duration_seconds` | 报告里的 `Analysis time` |
|---|---:|---|
| `run_e8e49384ab5246ab` | 4.516 | 4.5s ✓ |
| `run_dd897202eba74e28` | 4.985 | 5.0s ✓ |
| `run_4fde2fa0b5254ccb` | 4.703 | 4.7s ✓ |
| `run_fc8e432d4d094350` | 4.937 | 4.9s ✓ |

---

## 6. 本轮做了什么、没做什么

**做了什么**

- 只读复核 `docs/case-studies/` 全部材料 + `docs/reports/` 两份案例实测报告 +
  `docs/outreach/` 五份素材 + `docs/portfolio.md` + `docs/service-commitments.md` +
  CHANGELOG / 发版说明 / 已发布 Release 正文草稿 / 三份内部一致性报告 / `docs/status.md`
  里提到案例的段落；
- 解压 4 个证据包，对 12 个 manifest 条目逐个重算 sha256 与字节数（12/12 通过）；
- 解析 3 个样本 APK 的 DEX 头与 `class_def` 表，取出实际类清单；
- 用 `git log -p --follow` 追两处耗时的来源；
- 在 `src/dexatlas/` 核对 MCP 工具数、`POST /analyze` 状态码、`AnalyzeJobResponse`、
  `readOnlyHint`、类索引的合并口径。

**没做什么**

- **没有改任何既有文件**；本轮唯一的新增是本文。
- 没有运行 `dexatlas analyze`，没有重新生成任何附件，没有跑
  `scripts/refresh-report-figures.py`，没有跑 `pytest`，没有联网，没有 `git stash`，
  没有动 `src/`、`tests/`、`scripts/`、`CHANGELOG.md`、`README.md`、`README.zh-CN.md`、
  `docs/status.md`、`docs/reports/phase1-execution-report.md`。
- **没有评价报告里由脚本生成的数字**（测试数、覆盖率、源指纹）——那归主会话的重测量。
- **没有评价 GitHub 上已发布的 Release 正文**该怎么改（改不了），只报出来让人决定。

**结论依赖读者自己实跑的部分**

- §2.1 的「DEX 里 4 个类」：本轮用纯标准库解析 DEX 头得到，可复算；但
  「`Classes indexed` 为什么会是 5」是**推断**（依据 `pipeline.py:290/300/311` 与
  `storage.py:1065`），要坐实需要跑一次分析看索引里那第 5 条是什么。
- §2.2 的「4.9 s 来自旧附件报告」：git 历史可证（`git log -p --follow`），可复算。
- §2.5 的「examples/ 里五个 APK」：目录列举可复算。

**两处引文的机械改动（读者须知）**

- §2.3 与 §2.9 的引文里各有一个相对链接。为了不让
  `tests/test_docs.py::test_all_relative_links_resolve` 因为**引文里的链接**而红，
  这两个链接的目标改成了从本文件位置能解析的等价路径
  （`docs/case-studies/README.md` → `../case-studies/README.md`；
  `attachments/` → `../case-studies/attachments/`），**可见文字逐字未改**。
- 本文**不在** `scripts/check-doc-citations.py` 的受检文档清单里（那是一份固定清单，
  改它要动 `scripts/`，本轮不动）。本文的 `file:line` 引用是逐条手工核过的
  （§2 每一处引用都对着文件数过行号），不是门禁自动核的。

**本轮跑过的两个只读门禁**

```bash
uv run --no-sync python scripts/check-doc-citations.py   # 302 条引用，0 漂移，0 未解析
uv run --no-sync python .scratch/linkcheck.py             # broken: 0（含本文）
```

第二个脚本是本轮临时写在 `.scratch/` 里的（已被 `.gitignore` 忽略，不入库），
它复刻 `tests/test_docs.py::test_all_relative_links_resolve` 的判定逻辑。

---

## 7. 处置（2026-11-18，处置轮追加）

本文的 11 条发现已逐条处置。改动只落在 `docs/` 与 `CHANGELOG.md`：**没有重新生成
任何附件**、没有跑 `dexatlas analyze`、没有跑 `scripts/refresh-report-figures.py`、
没有动 `src/`、`tests/`、`scripts/`。

| 条 | 发现 | 处置 | 落在哪 |
|---|---|---|---|
| §2.1 | demo 走查的类数在同一篇里有 4 / 5 / 6 三个数 | §5 的结论句改为点名四个类；§3.1 的输出下面补一段口径（`Classes indexed` 是两个后端类视图的**合并索引**，可以大于 DEX 定义的类数，DEX 里是 `class_defs_size = 4`）；§1 的「five-class application」改为 four-class；§3.1 末尾的「5 of 5 classes」改为「5 of 5 **indexed** classes」。§3.1 引用的输出与 §4 的证据表是原件，不动 | [demo-app-walkthrough.md](../case-studies/demo-app-walkthrough.md) |
| §2.2 | 同一篇抬头与 §3.1 两个耗时 | 抬头的 `4.9 s` 改为 `5.0 s`，与 §3.1 引用的输出对齐 | 同上 |
| §2.3 | CHANGELOG 以现在时写「三个证据包 / 9 个文件」 | `## [Unreleased]` 的 `### Added` 加一条（附件集扩到四个包、16 个文件、四次分析）；v1.0.0 那条末尾加限定语，指向 [Unreleased] | `CHANGELOG.md` |
| §2.4 | api 走查 §3.5 末句与上一句互相否定 | 末句改为「The run it reports is the one §3.2's upload started; this upload added no analysis of its own.」 | [api-integration.md](../case-studies/api-integration.md) |
| §2.5 | 第三个案例包报告把「四个包」写成了「`examples/` 里四个 APK」 | 改为「三个不同的 APK，`demo.apk` 出现两次」，并点名 `examples/` 下另有两个未进案例材料的样本 | [case-studies-third-package.md](case-studies-third-package.md) |
| §2.6 | 发版说明与 Release 正文仍说 nine files / three packages / two analyses | 两处各加一句限定语：v1.0.0 tag 时是那个样子，2026-11-18 附件集换过一轮 | [v1.0.0.md](../releases/v1.0.0.md)、[v1.0.0-github-release-body.md](v1.0.0-github-release-body.md) |
| §2.7 | `final-outward-consistency.md` 的「数字一致」结论与它引用的句子都已过期 | §1 的表上方加限定语；那一行的判定注明「按 v1.0.0 发版树」；§5.2 第 6 条补上当前状态 | [final-outward-consistency.md](final-outward-consistency.md) |
| §2.8 | 「四次分析」没有一处说明它是「有包的那四次」 | 案例索引补一句：三篇走查引用 7 次运行，四次是出包的那几次 | [README.md](../case-studies/README.md) |
| §2.9 | 索引只写「四个包 + 十二份报告」 | 改为「four packages, twelve report files, sixteen files in all」 | 同上 |
| §2.10 | 「on screen 8」指向不明 | 改为「in the workbench's report screen」 | [demo-app-walkthrough.md](../case-studies/demo-app-walkthrough.md) |
| §2.11 | multi-DEX 附录说索引 keeps both，摘要行却是 4 classes | 摘要句前补一句去重口径：5 个类定义去重后是 4 个类，两份定义各自带 locator | [obfuscated-app.md](../case-studies/obfuscated-app.md) |

§4 标低的两处黑话也一并处置了：`call site` / `call edge` 在 obfuscated 与 api 两篇
首次出现处各加一句解释，demo 走查里的 `smali` 加了半句。

**处置后复算的结果**（读包、算哈希，没有重新生成任何东西）：

- 四个包的 `project_id` / `run_id` / `apk_sha256` / 包 sha256 / 字节数与 §5 的表逐项
  相同；四个 `run_id` 两两不同，覆盖三个不同的 APK（`demo.apk` 两次）；
- 附件目录仍是 16 个文件 = 4 个 zip + 12 份散装报告；四个包的 `manifest.json` 的
  `files[]` 逐文件 sha256 与包内字节一致；散装报告与包内 `reports/` 逐字节相同；
- `examples/demo-app/demo.apk` 的 `classes.dex` 仍是 `class_defs_size = 4`，四个类名
  与 §4 证据表所列一致。

**处置之后仍然需要人判断的两处**：

1. **`Classes indexed` 多出来的那一条来自哪个后端、叫什么。** 报告不列类清单，
   本轮没有跑分析，所以走查只写明「合并索引可能大于 DEX 定义的类数」，没有点名
   那一条——这是工具侧的事（§2.1 的建议 ②），不在这一轮文档处置的范围里。
2. **GitHub 上已发布的 v1.0.0 Release 正文改不了。** 仓库里两份文本已加限定语，
   但已经贴出去的正文要靠一条 Release comment 或下一个 release 的正文说清——
   这一条要人决定（§2.6 末段）。

> 本节由处置轮追加；§1–§6 是复核轮的原样产出，结论与行号未动。

