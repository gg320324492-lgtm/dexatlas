# M10 独立验收 —— 读者流程实跑报告（reader dry run）

> **状态：作者侧自测记录。本文件不是独立验收，不产生任何「通过/不通过」判定。**
>
> 目的：前三轮读者视角走查都是**读**材料找问题，从没有人**真按材料走一遍**。
> 本轮在一个干净目录里从远端 clone、检出固定 tag、按材料逐条执行命令，
> 把「材料说的」与「机器上真发生的」逐行对上，暴露文档与真实机器之间的卡点。
>
> 执行日期：2026年11月17日 · 验收对象：`v1.0.0` tag 所指提交
> `0104ccb7c058fab5197320c83723ba01a662b334`（tag 对象 `dbb2c8154b2a8d06af40f96e7cbf28f86447c852`）· **该 tag 此后已被重打**（重打记录见 [v1.0.0-ci-run-record.md](v1.0.0-ci-run-record.md)），上面这两个 hash 是**当时**那个 tag 对象，不是今天的
> · 演练目录：`E:/Dexatlas/.scratch/reader-dry-run/`（仓库只读，除本文件外未改动任何文件）
> · 本文件所有 `file:line` 引用均针对 **v1.0.0 那棵树**；`origin/main` 已在其后继续前进，
> 差异在 §7 单独说明。
>
> **这是一份历史记录，不是现状。** 它记的是 2026年11月17日 23:50 那一刻、
> 在 `0104ccb7…` 那棵树上的实走结果：§2「材料说的」栏、§4 差距清单、§5 改法清单、
> §6 的判据条数与那串数字，**都只对那棵树成立**。此后材料按 §5 清单改过若干轮，
> **每一条卡点的现状见 §9**——先看 §9，再决定这份报告对你还有没有用。
> 本文件里的旧数字（`1593` / `1620` / `1585` / `1612`、`13 个文件`、`286 条引用`、
> 两串 hash）都是**那一次**的快照，不回改。

---

## 1. 这次演练做了什么

| 项 | 内容 |
|---|---|
| 机器状态 | Windows 11 / PowerShell 侧的 Git Bash；系统 Python 3.10.11，另有 CPython 3.12.10；uv 0.11.21；OpenJDK 21.0.11；Docker 29.9.2；gh 2.97.0 |
| 隔离 | 演练目录在 `E:/Dexatlas/.scratch/reader-dry-run/`；uv 缓存、uv 托管 Python、临时目录、后端安装目录全部指向该目录；**未向系统盘根目录写入任何东西** |
| 网络 | 本机需代理：`HTTPS_PROXY=http://127.0.0.1:7897`（`http_proxy` 一并设上）；clone、依赖下载、后端下载均经代理 |
| 起点 | `git clone https://github.com/gg320324492-lgtm/dexatlas.git`（远端真实克隆，不是本地拷贝） |
| 后端 | 按 `docs/install.md` 的路线装 jadx 1.5.2 / apktool 2.11.1（`scripts/install-backends.sh`，install.md Troubleshooting 指向它） |

**为什么这样算是「干净的机器」**：uv 缓存是空的（首轮 `uv sync` 实测下载 97 个包），
后端是现装的（首轮实测下载 jadx+apktool 用时 359 秒），克隆目录与本仓库工作区完全无关。
「暖缓存」一节则复用同一缓存与已装后端，模拟第二次使用。

---

## 2. 逐步骤对照表

「材料说的」栏是材料的**逐字原文**（v1.0.0 树）；「实际发生的」栏是本机实测输出与耗时。

| 步骤 | 材料说的 | 实际发生的 | 一致 / 不一致 / 卡住 | 卡点的细节 |
|---|---|---|---|---|
| §3.1 `git clone` | 「`git clone https://github.com/gg320324492-lgtm/dexatlas.git`」 | 退出码 0，**46 秒**，37 MB | 一致 | — |
| §3.1 `git checkout v1.0.0` + `git status` | 「预期：`git status` 干净」 | 退出码 0；`HEAD detached at v1.0.0`；`nothing to commit, working tree clean` | 一致 | — |
| §3.1 核对 commit | 「记录 commit hash（`git rev-parse HEAD` 的输出，**应与邀请函成稿 §2 钉定的那一串相同**）」 | `git rev-parse HEAD` = `0104ccb7…`，`git rev-parse v1.0.0^{commit}` = 同值 | **卡住（发出前必须填）** | 邀请函成稿 `docs/reports/m10-invitation-final.md:60` 的占位符在仓库里仍是「commit 【待填：v1.0.0 发版 commit 的完整 hash】」。**这一栏本就该由发起人发出前填好，评审者收到的是填好的版本——不是材料缺陷**；但从「只读仓库」的角度现在读到的就是空的，而读者包 §3.1、工具包 §3.5 的自查项都要求「与那串相同」 |
| §3.2 `uv sync --extra dev --extra analysis --extra mcp --extra demo` | 「预期：`uv sync` 退出码 0」 | 退出码 0，**218 秒**；复用本机已有 CPython 3.12.10，解析 97 个包并装齐 | 一致 | 若机器上没有 3.12/3.13，uv 还要额外下载一个 Python，本轮未覆盖该情形 |
| §3.2 `uv run dexatlas backends` | 「`backends` 打印一张表，每个后端是 `available` 或 `not installed`」 | 退出码 0，1 秒。首轮（干净机器）：jadx `not installed`、apktool `not installed`、androguard `available 4.1.4`；装完后：三项全 `available`（jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4） | 一致 | — |
| §3.2 装后端 | install.md:109-119 给 `curl -LO … jadx-1.5.2.zip` + `unzip -q … -d /opt/jadx`；Troubleshooting:381 指向 `scripts/install-backends.sh` | `bash scripts/install-backends.sh` 退出码 0，**359 秒**（下载 jadx 24 MB + apktool 24 MB） | **不一致（路径）** | install.md 只给了 Linux 的 `/opt/jadx` 与 `$PWD`；Windows 读者必须自己换落盘位置。脚本内部 `export DEXATLAS_JADX_PATH=…/bin/jadx`（`scripts/install-backends.sh:76-77,92`）**不跨进程生效**，脚本退出即失效，读者还要自己再 export 一次——而 Windows 要指向 `bin\jadx.bat`（install.md:128 只在手动路线里提了一句） |
| §3.3 首次分析（**无外部后端**） | 「**后端缺失降级（A6）**：预期仍以退出码 0 完成并产出报告，错误记录写明哪个后端 `not_installed`；不得崩溃或静默省略」 | 退出码 0，3 秒：`4 classes, 8 methods, 23 call sites, 21 call edges, 0 resource strings`；stdout 两条 `! apktool is not installed…` / `! jadx is not installed…`；DB 里 `analysis_runs.errors` 记 `code=not_installed`、`completeness=partial` | 一致 | 与 §3.2 的「A6 预告」（缺 jadx 时 5→4、1→0）吻合 |
| §3.3 首次分析（**三后端齐全**） | 「`apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string`」 | 退出码 0，5 秒（分析本身 3.8 秒），**逐字命中** | 一致 | — |
| §3.4 `manifest` | 「包名 `com.example.demo`；version 1.0 (1)；sdk min 24 / target 34；1 个权限；3 个组件；MainActivity 与 SyncService 均为 exported 且无权限保护」 | 退出码 0，输出逐字相符 | 一致 | — |
| §3.4 `search "Crypto"` | 「命中 `com.example.demo.Crypto` 相关类与方法」 | 退出码 0：`class` 1 条 + `method` 3 条 + `string` 2 条 | 一致 | — |
| §3.4 `search "sk_live"` | 「一条字符串命中 `sk_live_2f8a…`；`Kind=string` 即表明命中来自字符串常量索引」 | 退出码 0：`Kind=string` 1 条（完整串见材料与报告产物，本文不复写） | 一致 | — |
| §3.4 `source` | 「第一行标明 `source kind: java` … 例如 `jadx:sources/com/example/demo/MainActivity.java`」 | 退出码 0：`source kind: java` / `jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java` | 一致 | — |
| §3.4 `xrefs` | 「`1 call site(s), 1 call edge(s)`，调用点为 `classes.dex@34`」 | 退出码 0，逐字相符 | 一致 | — |
| §3.5 三格式导出 | 「三份非空文件，描述同一 project id」 | 退出码 0：`report.md` 5 262 B、`report.json` 11 746 B、`report.html` 8 606 B，同一 project id | 一致 | — |
| §3.5 离线阅读（D1） | 「页面应完整可读，无 `<script>`、无外部 CSS/JS/字体请求」 | `grep -c "<script"` = **0**；`src=`/`href=` 外链 **0**；`http(s)://` 引用 **0** | 一致 | — |
| §3.6 `export -o evidence.zip` | 「`verify_package` 通过（schema、路径穿越、SHA-256、项目/APK 绑定）」 | 退出码 0，1 秒：`✓ evidence package → evidence.zip (3 files, apk 80a8fe0e81204c9f)` | 一致 | 包内实为 **4 个条目**（3 份报告 + `manifest.json`）；「3 files」指报告数，容易被读成「包里只有 3 个文件」 |
| §3.6 引用校验 | 「`citations_resolved` 为 `True`，`citations_unresolved` 为空」 | 退出码 0：`{'citations_total': 14, 'citations_resolved': True, 'citations_unresolved': [], 'apk_sha256': '80a8fe0e…'}` | 一致 | — |
| §3.6 迁移复验（C6） | 「把 `evidence.zip` 复制到另一个目录（或另一台机器）再跑一次」 | 复制到 `../moved-evidence/` 后复跑，输出与原处完全相同（`citations_resolved: True`） | 一致 | — |
| §3.6 包内声明（D3） | 「`manifest.json` 的 `not_included` 明示不含 APK、全量源码、未被证据引用的字符串；实际包内容与该声明一致」 | `not_included` 三项齐（apk / full_sources / unrelated_strings）；包内确无 APK、无 `sources/` 目录 | 一致 | demo 的证据 locator 全是裸树/DEX 成员型，包内不出现 `sources/`——与 D4 的说明自洽 |
| §3.7 案例核对（B1） | 「案例里的每条命令你能否照跑且结果一致」 | 案例 `docs/case-studies/demo-app-walkthrough.md` 的 analyze → manifest → search → source → xrefs → export 全部照跑，一致；**未向作者补任何一条命令** | 一致 | — |
| §3.8 契约实测（F5–F6） | 「`uv run --no-sync pytest tests/test_public_contracts.py -q`」「`uv run --no-sync python scripts/verify-public-contracts.py`」 | 前者 `29 passed in 6.66s`；后者 **48/48 checks passed**，退出码 0 | 一致 | — |
| §3.8 退出码 0/1/2 | 「至少实测 0/1/2 各一次」 | 0：analyze 成功；1：查一个项目里不存在的类（契约脚本实测 `source … a class the project does not hold answers 1`）；2：非 ZIP 当 APK → `Not a usable APK: … is not a ZIP archive; APKs are ZIP archives`，退出码 2 | 一致 | — |
| §3.8 故障恢复 G1/G2/G3/G4 | 「坏输入应退出码 2 且不留半成品」「清空后端环境变量后分析仍完成并写明 `not_installed`」「同一 APK 分析两次 project id 相同」「极短超时后三后端记录 `timeout`，报告仍产出」 | G1：退出码 2，`projects` 仍只有 1 条；G2：见上（`not_installed` + `completeness=partial`）；G4：连续两次 analyze 同 id `apk_80a8fe0e81204c9f`，`projects` 只有 1 条、计数一致；G3：`DEXATLAS_TOOL_TIMEOUT_SECONDS=1` → `! jadx exceeded its 1s timeout and was terminated`，分析仍退出 0 并出报告 | 一致 | G3 的**退出码 6** 分支本轮未能实测：androguard 进程内解析，无法用超时变量打掉，三后端无法同时失败（`index_complete` 恒为真）。该分支只由契约脚本 `an analysis with no index exits 6` 覆盖 |
| §6.3 门禁七条 | 「`ruff check` / `ruff format --check` / `mypy` / `vulture` / `pytest -q` / `check-doc-citations.py` / `check-version-claims.py --base auto`」 | **七条全部退出码 0**：ruff 1 s、format 0 s、mypy 4 s、vulture 1 s、pytest 461 s、citations 1 s、version-claims 6 s | 一致 | — |
| §6.3「跳过不是通过」 | 「读 summary 的 skip 数；后端缺失导致的 skip 要单独说明」 | `pytest -q` → **1585 passed, 27 skipped in 457.54s**。27 个 skip **全部**是 `fixture not present; run scripts/fetch-fixtures.sh`，与后端无关 | **卡住（材料缺一步）** | 读者路径里**没有任何一步**让读者先跑 `scripts/fetch-fixtures.sh`：环境表（`docs/reports/m10-reader-package.md:66`）只说「`gh` CLI 仅 fixtures 需要」，没说是 pytest 的前置条件。读者按材料走 → 27 个 skip → 与 README 徽章「tests-1612 passing」对不上。补跑该脚本（5 秒）后重跑那 3 个测试文件 → **43 passed, 0 skipped**，1612 与报告数字吻合。**已在 `origin/main` 的 `a6d81f7` 修好（见 §7）** |
| §7 自查脚本 | 「`uv run --no-sync python scripts/m10_selfcheck.py`」，退出码 0 = 无失败项 | 退出码 **0**：**通过 40 / 失败 0 / 需人工 40** | 一致 | — |
| 路线 B：Docker | 「预期：构建约 2 分钟（[M8 演练](m8-install-rehearsal.md)实测 2 分 16 秒）；镜像内 JADX / Apktool 可用」 | 构建退出码 0，**1099 秒 ≈ 18 分 19 秒**（镜像 1.3 GB）；`docker run --rm dexatlas dexatlas backends` 3 秒，三后端全 `available`（jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4）；容器内分析退出码 0、8 秒，计数同为 5/8/23/21/1 | **不一致（时间）**；后端与计数一致 | 构建时间超材料预期约 **8.5 倍**（本机走代理下载，本地无该项目层缓存）。**另有一处材料缺了一步**：镜像里**没有 `examples/`**（`docker run --rm dexatlas ls /app` 只有 `src/ pyproject.toml uv.lock README.md LICENSE`），材料 §3.2 路线 B 只给到 `backends` 检查，**没告诉读者怎么在容器里分析 APK**——读者得自己想出 `-v <仓库>/examples:/app/examples:ro` 与 `-v <工作区>:/workspace` 两个挂载才能跑出案例 |
| 暖缓存计时 | 「暖缓存（JDK/uv 已装）到第一份报告约 1.5–2 分钟」（`docs/reports/m10-reader-package.md:69`、`:405`；`docs/reports/m10-acceptance-pack.md:193`） | **口径 A（uv 缓存已热）**：删掉 `.venv` 与工作区后重建并出报告——`uv sync` **2 秒** + 分析与三格式导出 **6 秒** = **8 秒**，三份产物与首轮逐字同尺寸 | **不一致（口径混用）** | 材料那 1.5–2 分钟来自 [M8 演练](m8-install-rehearsal.md)的**已就绪会话工作树**（分析现场、`.venv`、报告都已在手），本轮的 8 秒是**从重建 `.venv` 到第一份报告**——两件事不是同一件。读者若拿 8 秒去对「1.5–2 分钟」，会以为自己测错了。**口径本身没有矛盾，是材料把两档写在同一句话里。**（另：二次远程 clone 的完整路径复测因本机代理拥塞未完成，本行数字由 `uv sync` 与分析两段分别实测合成） |
| 冷缓存计时 | 「冷缓存（含 clone、依赖、后端下载）首次 10–20 分钟」 | **628 秒 ≈ 10 分 28 秒**（clone 46 s + `uv sync` 218 s + 后端 359 s + 分析 5 s） | 一致（落在区间下沿） | — |
| 准备包 §3.6 时间表 | 「\| clone + `uv sync` \| 15 秒–2 分钟 \| 冷缓存与网络差异大；M8 冷缓存实测 15 秒 \|」（`docs/reports/m10-acceptance-pack.md:331`） | 实测 **264 秒（4 分 24 秒）** | **不一致** | 同一份准备包的 §3.1 时间表（:193）写的是「冷缓存……首次 10–20 分钟」，读者包 :69/:405 也写 10–20 分钟。同一个包三处口径互相打架，读者不知道该信哪个 |
| 执行摘要 5 步 | 「1 锁定验收对象 → 2 clone 并装环境 → 3 跑一个完整案例 → 4 逐项判定并打分 → 5 交回记录」 | 步骤 1–3 可独立走通；步骤 4–5 依赖人工判定与人工填写（非自动化可跑） | 一致（步骤 1–3）；4–5 见 §6 | 步骤 1 说「**不必再向发起人索取 commit hash**」——执行摘要用 `git rev-parse v1.0.0^{commit}` 自取，而 §3.1 要与邀请函 §2 比对；两者只要 §2 填好就不冲突（**填好即消解**，见 §5 第 2 条） |

---

## 3. 读者能在哪一步放弃

按**最可能的放弃顺序**排列。前三条都会真的发生，后两条是「材料自己绊自己」。

1. **第 2 步装环境（约 9 分 40 秒，占冷缓存耗时的 92%）。**
   `uv sync` 218 秒、后端下载 359 秒，且要 JDK、要网络代理。后端这一步最容易卡住：
   install.md 给的是 Linux 路径，`scripts/install-backends.sh` 装完**不把环境变量交出来**，
   Windows 读者还得自己知道要指向 `bin\jadx.bat`。如果读者同时在等 10–20 分钟的上限，
   装到第 8 分钟就会怀疑「是不是卡死了」。**这是第一放弃点。**

2. **第 3 步第一次分析的输出对不上。**
   干净机器上第一次 analyze 必然是 `4 classes … 0 resource strings`，与材料的
   `5 classes … 1 resource string` 不同。§3.2 的「A6 预告」确实写了 5→4、1→0，
   但它埋在一个引用块里；没读到 §3.2 的读者会认为工具坏了，**当场就走了**。

3. **门禁那一步的 27 个 skip。**
   pytest 要跑 7 分 37 秒，跑完给 27 个 skip。材料同时写着「跳过不是通过」，
   读者此刻只能理解成「我的环境有问题」，而材料没告诉他缺的是 fixtures。
   愿意深究的读者要自己去 `grep` 跳过原因才能发现那行 `run scripts/fetch-fixtures.sh`。

4. **找不到「我该验的 commit 到底是哪一串」。**
   邀请函 §2 的占位符在仓库里是空的（这一栏**本就该由发起人发出前填好**，评审者拿到的是填好的版本；
   但从「只读仓库」的角度现在确实读不到），读者包 §3.1 与工具包 §3.5 的自查项都要求和它比对。
   读者要么放弃这一项，要么**回头问作者**——而「不要让作者代劳」恰恰是这份材料自己的第 4 条读者须知。

5. **Docker 路线等不到 2 分钟。**
   本轮实测 **18 分 19 秒**（见 §4），材料说「约 2 分钟」。用 Docker 路线的读者在第 5 分钟时会以为构建坏了。
   而且路线 B 的材料只给到 `backends` 检查——镜像里没有 `examples/`，读者要自己发明挂载才能跑案例。

---

## 4. 材料与现实的差距清单

| # | 材料说的 | 实际是 | 出处 | 状态 |
|---|---|---|---|---|
| 1 | 「\| clone + `uv sync` \| 15 秒–2 分钟 \|」 | 264 秒（4 分 24 秒），冷缓存 | `docs/reports/m10-acceptance-pack.md:331` | 未改 |
| 2 | 同包 §3.1 与读者包写「冷缓存首次 10–20 分钟」 | 三处口径互不一致（15 s–2 min / 10–20 min / M8 的 30 s–1 min） | `m10-acceptance-pack.md:193`、`m10-reader-package.md:69`、`m8-install-rehearsal.md:56` | 未改 |
| 3 | 「构建约 2 分钟（M8 实测 2 分 16 秒）」 | **18 分 19 秒**（1099 秒，本机走代理、无本地层缓存） | `m10-reader-package.md:132`、`m10-acceptance-pack.md:250` | 未改 |
| 4 | 「暖缓存到第一份报告约 1.5–2 分钟」 | 口径 A（重建 `.venv` 到第一份报告）**8 秒**；材料那 1.5–2 分钟是 M8「已就绪会话工作树」的口径 | `m10-reader-package.md:69`、`:405` | 未改（应拆成两档分别写） |
| 5 | pytest 门禁（读者路径里没有 fixtures 这一步） | 27 skip；补跑 `scripts/fetch-fixtures.sh` 后 1612 全过 | `m10-reader-package.md:66` | **已修**（`origin/main` 的 `a6d81f7`） |
| 6 | README 徽章写「tests-1612 passing」 | 实跑 1585 passed + 27 skipped；跳过被算进了「passing」 | `README.md:12` | 未改 |
| 7 | §3.1「记录 commit hash……应与邀请函成稿 §2 钉定的那一串相同」 | 仓库里 §2 的占位符是「【待填：v1.0.0 发版 commit 的完整 hash】」 | `m10-invitation-final.md:60` | **不需改材料**：这是**发出前由发起人填写**的字段，评审者收到的是填好的版本；只是从「读仓库」的角度现在读到的还是空的 |
| 8 | install.md 的后端安装步骤 | 只给 Linux 路径；脚本的 `export` 不跨进程；Windows 的 `bin\jadx.bat` 提示只在手动路线里 | `docs/install.md:109-119`、`:128-130`、`:380-381`；`scripts/install-backends.sh:76-77,92` | 未改 |
| 9 | A6 的判定标准「错误记录写明哪个后端 `not_installed`」 | 错误确实落库（`analysis_runs.errors`），但 CLI 没有「渲染某一次运行」的命令，重跑一次分析后 stdout 上的证据就没了；材料没说该当场记下 | `m10-reader-package.md:151-153` | 未改 |
| 10 | 「`✓ evidence package → evidence.zip (3 files, …)`」 | 包内 4 个条目（3 份报告 + `manifest.json`） | `src/dexatlas/cli/main.py`（export 提示） | 未改 |
| 11 | 路线 B 给出的命令只有 `docker build` + `docker run --rm dexatlas dexatlas backends` | 镜像里没有 `examples/`，容器内跑案例的命令材料没给（读者需自己发明两个 `-v` 挂载） | `m10-reader-package.md:125-135`、`m10-acceptance-pack.md:230-250` | 未改 |

---

## 5. 必须改的 N 处（只列清单，不代改）

| # | 文件:行 | 建议改法 |
|---|---|---|
| 1 | `docs/reports/m10-acceptance-pack.md:331` | 把「15 秒–2 分钟」改成与同文件 :193 一致的冷/暖两档口径，并附本轮实测（冷 264 秒 / 后端 359 秒）作为参考区间 |
| 2 | `docs/reports/m10-invitation-final.md:60` | **发出前填入完整 hash**（当前 `v1.0.0` = `0104ccb7c058fab5197320c83723ba01a662b334`）——这是填写动作，不是材料缺陷；若 tag 重指，需同步更新此处。另可考虑把 §3.1 的措辞改成「用 `git rev-parse v1.0.0^{commit}` 自取并与 §2 比对」，让占位符即使未填也不卡住读者 |
| 3 | `docs/reports/m10-reader-package.md:132` 与 `docs/reports/m10-acceptance-pack.md:250` | 把「构建约 2 分钟」改成一个**带条件的区间**：建议写成「约 2–20 分钟：层已就绪时约 2 分 16 秒（M8 实测）；首台机器、无本地层缓存、下载走代理时实测 **18 分 19 秒**（本轮，1099 秒）」——只写 2 分钟会让走代理的读者在第 5 分钟以为构建坏了 |
| 4 | `docs/reports/m10-reader-package.md:69` 与 `:405` | 把「暖缓存」拆成**两档**分别写：「① 重建 `.venv` → 第一份报告：实测 **8 秒**（uv sync 2 s + 分析 6 s）；② 已就绪会话工作树：约 1.5–2 分钟（M8 口径）」——并注明本轮 8 秒那一档是在 uv 缓存已热、后端已装的前提下测的 |
| 5 | `docs/install.md:109-119` | 补一条 Windows 安装路径（落盘目录 + `DEXATLAS_JADX_PATH` 指向 `bin\jadx.bat`），或直接指向 `scripts/install-backends.sh` 并说明「脚本内的 export 不跨进程，需自行再设一次」 |
| 6 | `docs/install.md:380-381` | Troubleshooting 里补一句「脚本只在自己进程内 export，退出后需自行 `export DEXATLAS_JADX_PATH=…/bin/jadx.bat`」 |
| 7 | `README.md:12` | 徽章口径二选一：改写为「tests-1612 collected」，或注明「passing 含 fixture 缺失时的 skip」；否则与 `m10-acceptance-pack.md:620`「跳过不是通过」自相矛盾 |
| 8 | `docs/reports/m10-reader-package.md:151-153`（A6 段） | 加一句「A6 的证据要当场记下（或先导出报告再装后端），重跑分析会覆盖同一 project 的最新运行」 |
| 9 | `src/dexatlas/cli/main.py`（export 成功提示） | 「(3 files, …)」改成「(3 reports + manifest, …)」或直接给条目数 4，免得读者以为包里只有 3 个文件 |
| 10 | `docs/reports/m10-reader-package.md:151-153` + §3.2 | 复核 A6 预告的位置：把「缺 jadx 时 5→4、1→0」从引用块提到正文小标题旁——这是读者第一次分析失败时最容易错过的一句 |
| 11 | `docs/reports/m10-reader-package.md:125-135`（路线 B） | 路线 B 只给到 `docker run --rm dexatlas dexatlas backends`；镜像里没有 `examples/`，材料没给容器内分析的命令。补上这段（本轮实测可用，退出码 0、8 秒、计数 5/8/23/21/1）：<br>`docker run --rm -v <仓库>/examples:/app/examples:ro -v <工作区>:/workspace dexatlas dexatlas analyze examples/demo-app/demo.apk`<br>并加一句 Git Bash 注意事项：`-v` 的容器路径会被 MSYS 改写成 `C:/Program Files/Git/app/...`，需 `MSYS_NO_PATHCONV=1` 或写 Windows 风格路径 |

**另有一项需发起人决定（不是文字问题）**：`v1.0.0` tag 目前仍指向 `0104ccb…`，
而补 fixtures 那一步的修正（`a6d81f7`）在 `origin/main`（现为 `e637438`）上。
**读者按材料 `git checkout v1.0.0` 拿到的是没有这一步的那棵树**，仍会撞上 27 个 skip。
两条路：重打 tag 到含 `a6d81f7` 的提交，或在读者包 §3.1 明说「先切到 `origin/main` 再验收」。

---

## 6. 40 项自动化判据的实跑结果

### 6.1 脚本口径（`scripts/m10_selfcheck.py`）

> **本节是那一轮的口径**：当时脚本有 40 条自动化判据。演练本身又暴露出三条
> 自查没查的事，随后各配一条判据与一条红→绿回归测试——**现在是 43 条自动化 +
> 40 条需人工**，见[材料自查记录](m10-selfcheck.md)与 §9。

| 判定 | 条数 |
|---|---:|
| 通过 | **40** |
| 失败 | **0** |
| 需人工 | **40** |

脚本退出码 **0**（无失败项；「需人工」不算失败）。这 40 个「需人工」正是验收准备包 §2 的 40 个验收项。

### 6.2 我在本轮实跑中人工补上的部分

脚本判「需人工」的 40 项里，我按材料实跑并记录了证据的有 **34 项**（A 组 7/7、B 组 6/6、C 组 6/6、
D 组 5/5、F 组 6/6、G 组的 G1/G2/G4/G5），未发现与材料预期不符者。
其中 D2 的「三格式抽查 3 个数字」已逐项对过：`classes 5 / methods 8 / call_sites 23 / call_edges 21 /
resource_strings 1` 在 Markdown、JSON、HTML 三处取值一致。

**需人工判断、本轮未能定论的 5 项（E1–E5）**：它们要求读者能复述服务回归集的层级语义
（层级 0 确定性判分 20/20、层级 1 scripted 替身、层级 2 真实模型 49/60 = 81.7% 未达验收线）。
本轮核对了落盘报告与文档口径一致，但这五项本质是**理解与解释能力**，不是命令能判的。

**部分实测的 1 项（G3）**：超时分支已验（`DEXATLAS_TOOL_TIMEOUT_SECONDS=1` → jadx 超时被杀、
分析仍退出 0 并出报告）；但**「三后端全败 → 退出码 6」这一分支本轮无法在正常机器上复现**——
androguard 是进程内解析，超时变量打不掉它，三后端无法同时失败。该分支只有契约脚本
（`an analysis with no index exits 6`）覆盖，材料未给读者在正常机器上复现它的办法。

---

## 7. 材料树与主线的差异（2026年11月17日 23:50 核对）

- `origin/main` = `e637438`，比 `v1.0.0`（`0104ccb…`）**领先 5 个提交**。
- `a6d81f7`「读者材料：把「抓第三方集成样本」这一步补进安装流程」在主线上，
  **不在 tag 那棵树上**；§4 的第 5 条据此记为「已修」。
- 本轮实测的所有材料行号都指向 tag 树；主线上的行号会前移，**改材料时请以主线为准重新取行号**。
- 父线程转述的「tag 已重打、`origin/main` 与它同指 `0104ccb`」与实测不符：
  远端 `refs/tags/v1.0.0` 仍是 tag 对象 `dbb2c815…` → 提交 `0104ccb…`，
  而 `origin/main` 已在 `e637438`。本报告按实测写。
- `docs/reports/README.md:87` 那条「`v1.0.0` tag 仍停在 `8f9ddca`，`origin/main` 同样是 `8f9ddca`，
  两者都落后当前树……tag 重打、远端推进到最终 commit 之前，成稿第二节那串 hash 填不出来」
  ——**按 23:50 的实测已经过期**：tag 在 `0104ccb…`、远端在 `e637438`，
  两者都动了，**成稿第二节那串 hash 现在是填得出来的**（就是本报告开头那串）。
  这条索引文字本身需要跟着更新，否则读者读到的是一份「还不能发」的判断。
- 本目录索引（`docs/reports/README.md`）按其自述要收全 `docs/reports/` 下的每一份报告，
  **本文件尚未被收录**（本次演练只新增这一份报告，未改动索引页——超出「只新增一份报告」的边界）。

---

## 8. 结论

> **这段结论是 2026年11月17日 23:50 的状态。** 它末段点名的三处材料内部矛盾
> （准备包 §3.6 与 §3.1 的冷缓存口径、暖缓存两个口径混写、读者路径里缺
> fixtures 那一步）此后都已按 §9 逐条处理；**现在的状态看 §9**。

**能，但只有走 uv 路线、走完全部九步才成；这份材料目前还差最后一步才能发给外部评审者。**

工具本身没有在任何一个环节挡住读者：40 项自动化判据全过，七道门禁全绿，
九步路径的输出与材料逐字相符，证据包 14 条引用全部可解析，迁移后复验仍成立，
冷缓存 10.5 分钟落在材料的 10–20 分钟区间内。

真正挡住读者的是**材料自身的两处内部不一致**与**一处前置条件缺失**：
准备包 §3.6 的「15 秒–2 分钟」与同文 :193 的「10–20 分钟」互相打架（读者不知道该信哪个），
暖缓存那一句把「已就绪工作树」与「重建 venv」两个口径混写（读者拿 8 秒去对 1.5–2 分钟会以为自己测错了），
以及 pytest 的 fixtures 前置条件在 v1.0.0 那棵树上没有写进读者路径（读者会看到 27 个 skip 并以为自己坏了机器）。
邀请函 §2 的 commit 占位符属于**发出前填写**，不是材料缺陷——但发出前必须填上。

把这三处补上、把 tag 指到含 `a6d81f7` 的提交，材料就能让一个不知情的人**真的**走完一次独立验收。

---

## 9. 这份报告之后：11 条卡点的现状

> 核对日期：2026年11月18日 · 核对方式：逐条读**当前树**里的材料原文，
> 不看本文件的旧行号。「已改」= 材料现在就是这么写的；「已修」= 代码或别处
> 的文档已修；「不需改」= 那一条本来就不是缺陷。
> 逐条陈述的真值来源见[材料对齐表](m10-materials-alignment.md)。

| §5 # | 卡点 | 现状 | 现在在哪 / 怎么核 |
|---|---|---|---|
| 1 | 准备包 §3.6「clone + `uv sync` 15 秒–2 分钟」与同文件 §3.1 的「10–20 分钟」打架 | **已改** | 准备包 §3.6 写成「15 秒–4 分 30 秒」，两个数各带出处（M8 冷缓存 15 秒、实走演练 4 分 24 秒） |
| 2 | 邀请函 §2 的 commit 占位符 | **不需改**（是**发出前填写**的字段） | 占位符仍在；读者拿到的是填好的版本。核对方式见[发送前清单](m10-invitation-sender-checklist.md)组二 |
| 3 | Docker「构建约 2 分钟」与实测 18 分 19 秒 | **已改** | 读者包 §3.2 路线 B 与准备包 §3.3 都写成「约 2–20 分钟（两个口径）」，各带出处 |
| 4 | 暖缓存把「已就绪工作树」与「重建 venv」两个口径混写 | **已改** | 两处实测锚点各自标了口径：M8「空目录 → 第一份报告，暖缓存」约 30 秒、实走演练「重建 `.venv` → 第一份报告」8 秒；并写明「**做快于 30 秒不是卡点**」。材料给读者的是**1.5–2 分钟的预算档位**，并注明那是预算、不是实测 |
| 5 | install.md 的后端安装只有 Linux 路径 | **已修** | install.md 补了 Windows 段（`DEXATLAS_JADX_PATH` 指向 `bin\jadx.bat`；走 `scripts/install-backends.sh`） |
| 6 | install.md Troubleshooting 没提「脚本内的 export 不跨进程」 | **已修** | 同上，Troubleshooting 里已写明退出后需自行再设一次 |
| 7 | README 徽章把 skip 算进「passing」 | **已修** | 徽章数字由测量脚本从 `suite.passed` 写入；完整测量下 `skipped=0`，徽章与执行报告同源。徽章上的数会随重测量换新——**以徽章当前显示的为准**，材料不写死它 |
| 8 | A6 的降级证据当场记下就找不回来 | **已改** | 读者包 §3.3 要求读者当场抄下并说明原因（CLI 没有按 run 选运行的命令，重跑会换掉最新一次运行） |
| 9 | CLI 打印「3 files」而包内 4 个条目 | **已改** | CLI 现在打印**归档自己的文件数**：`4 files: 3 reports + 1 manifest`；读者包 §3.6 按新行为写清了「数 zip 得 4、CLI 也说 4，只数 manifest 清单会得 3」 |
| 10 | A6 预告埋在引用块里 | **已改** | 已提到正文小标题旁（读者第一次分析失败时最容易错过的一句） |
| 11 | 路线 B 只给到 `docker run … backends`，镜像里没有 `examples/` | **已改** | 读者包 §3.2 路线 B 与准备包 §3.3 给出 `-v` 挂载与容器内 analyze / export 命令 |

**另外两条与 tag 有关的事**（当时是「未完成」，现在有明确做法）：

- 「重打 tag 之前不能发邀请函」这条纪律**保留**，并被写成可执行的检查：
  [发送前清单](m10-invitation-sender-checklist.md)组二给了「取 hash / 核远端 /
  核 tag 指向的树含本轮材料修正 / 重打 tag」四步，每步都带命令与判据。
- 清单与就绪记录里原先**写死的两串 hash** 已改成**形状示例**并注明「必须现查现填」——
  tag 每重打一次就换一次串，写死的串发出时一定是错的。

**这份报告里的旧数字不回改**：`1593 passed` / `1620 passed` / `1585 passed` /
`1612` / `13 个文件` / `286 条引用` / 两串 hash，都是**那一次**的快照。
材料现在一律不写死它们——测量类的数引用
[执行报告](phase1-execution-report.md) 的 `<!--fig:...-->` 标记，其余写明
「随树变化，以你 checkout 出来的那一份为准」。
