# C6 判据 (a)：镜像构建时间的新口径（CI 实测）

> 测量日期：2026年11月18日。对象：候选清单 [C6](v1.1.0-candidates.md#L697) 判据 (a) 要求的
> 「把新的构建时间写回引用旧口径的地方」。
> 复核工作树：`E:\Dexatlas\.claude\worktrees\recursing-gauss-bfce6d`（分支 `claude/recursing-gauss-bfce6d`）。
>
> **本文是那个新口径的唯一落点。** 别处只引用它，不另抄一份数——
> 这正是判据 (a) 的「构建时间的新口径在材料里只有一处」。

## 0. 结论先说

**CI 上 `docker build` 这一步实测 46 秒**（最近一次跑过 `docker` job 的 run），
整个 `docker` job 66 秒；tag `v1.0.0` 那次发版验收的 run 里，构建步骤 35 秒、job 51 秒。

| 测的是哪一段 | 数 | 出处 |
|---|---|---|
| CI runner 上的 `docker build` 步骤（**新口径**） | **46 秒**（tag 那次 35 秒） | 本文 §1 |
| CI runner 上的整个 `docker` job（构建 + 验后端 + 镜像内分析样本） | **66 秒**（tag 那次 51 秒） | 本文 §1 |
| 读者本机冷缓存、走代理下载后端的整段构建（**旧口径**） | 1099 秒 ≈ 18 分 19 秒 | [读者实走演练](reader-dry-run.md#L117) |

**两个数都成立，因为它们测的不是同一段。** 旧的那一个是**读者本机**的实测，
测的是「无层缓存 + 走代理下载 JADX / Apktool」这一段；新的这一个测的是
**GitHub 托管 runner 上的一步 `docker build`**。谁要写给读者看，**先说清测的是哪一段**。

## 1. 证据：这是从哪条 run 的哪个 job 抄来的

### 1.1 最近一次跑过 `docker` job 的 run（主口径）

| 项 | 值 |
|---|---|
| 仓库 | `gg320324492-lgtm/dexatlas` |
| **run id** | **44334171465** |
| 触发 | `push` → `main`，head sha `7a416bdbf2193cbc6a948f9084ebe7634926bbfd` |
| 起止 | 2026-11-18T15:18:48Z 起，**6m44s**，结论 **success** |
| **job** | **`Docker image builds and analyses a bundled sample`**（job id `134906231107`） |
| job 起止 | `2026-11-18T15:18:51Z` → `2026-11-18T15:19:57Z` = **66 秒** |
| **step** | **`Build image`**（`docker build -t dexatlas:ci .`） |
| step 起止 | `2026-11-18T15:18:54Z` → `2026-11-18T15:19:40Z` = **46 秒** |
| 同 job 的另两步 | `Verify the backends in the image actually run` 4 秒；`Analyse the bundled sample inside the image` 11 秒 |

命令（`gh` 只读，不需要写权限）：

```bash
gh api repos/gg320324492-lgtm/dexatlas/actions/runs/44334171465/jobs \
  --jq '.jobs[]|select(.name|test("Docker"))|{started_at,completed_at,steps:[.steps[]|{name,started_at,completed_at,conclusion}]}'

gh api repos/gg320324492-lgtm/dexatlas/actions/jobs/134906231107/logs --allow-escape-sequences
```

日志里能直接读到的两行（buildkit 的收尾）：

```text
2026-11-18T15:19:34.2645753Z #24 naming to docker.io/library/dexatlas:ci done
2026-11-18T15:19:40.5053180Z #24 DONE 19.6s
```

### 1.2 交叉核对：tag `v1.0.0` 那次发版验收的 run

| 项 | 值 |
|---|---|
| **run id** | **44324097977**（`push` → tag `v1.0.0`，head sha `2715aef`） |
| 结论 | **success**（整条 run 9m19s） |
| job | `Docker image builds and analyses a bundled sample`（job id `134870583050`） |
| job 起止 | `2026-11-18T14:25:42Z` → `2026-11-18T14:26:33Z` = **51 秒** |
| step `Build image` 起止 | `2026-11-18T14:25:44Z` → `2026-11-18T14:26:19Z` = **35 秒** |

两次跑的是**同一份 `Dockerfile`**（C6 方案 A 之后的那一份，带 `COPY examples/ examples/`），
数落在 35–46 秒之间——**这就是这个口径的量级**，不是单次侥幸。

### 1.3 「没有层缓存」这件事是查过的，不是假设

buildkit 的构建日志里 **`CACHED` 一次都没有出现**，27 个构建步骤全部实做
（`#1 DONE 0.1s` … `#24 DONE 19.6s`）。两次跑都查过：run `44334171465` 的日志与
run `44324097977` 的日志，`CACHED` 的计数都是 **0**。

这说明「CI 上几十秒」与「读者本机一千多秒」的差别**不在有没有缓存**——
两次构建都是从零拉的——而在 runner 的网络与机器，以及读者那台机器走的是代理。

## 2. 这次测量**没有**覆盖什么

- **没有在本机构建镜像**：本轮不联网构建，所以本机上没有 `dexatlas:ci` 镜像。
  上面两个数全部来自 CI 的 run 日志。
- **没有测读者本机**：1099 秒那一段是 [读者实走演练](reader-dry-run.md#L117) 的记录，
  本轮**没有重测**它——那要一台冷缓存、走代理的机器。它仍然按它自己的口径成立。
- **没有把两个数合并成一个区间**：它们测的是两段不同的东西，
  合并成一个「2–46 分钟」那样的数会把「测的是哪一段」这句话弄丢——
  那正是 C6 判据里「两份材料里的构建时间口径标明测的是哪一段」要防的事。

## 3. 引用旧口径的地方，现在各指向哪里

| 位置 | 旧口径 | 现在 |
|---|---|---|
| [v1.1.0-candidates.md](v1.1.0-candidates.md#L697)（C6 一行） | 「按演练实测 Docker 构建无层缓存 1099 秒」 | 改成「已完成」+ 新口径的出处（本文） |
| [docker-examples-gap.md](docker-examples-gap.md)（§0 结论 3 与 §2 方案 A 的代价表） | 「冷缓存口径约 18–20 分钟机时」「加 COPY 后的构建时间：未构建镜像」 | 标明那是**当时的待办**，并指向本文 |
| [docker-image-samples.md](docker-image-samples.md)（§6 第 6 条「C6 的另一条判据没有做」） | 「本轮没有重建镜像，构建时间口径还是旧的那份」 | 改成「已做」，数字取自本文 §1 |
| m10-reader-package.md（§3.2 路线 B） | 「约 2–20 分钟（2 分 16 秒 / 1099 秒）」 | 加一句标明**测的是读者本机**，并给出 CI 的那一段 |
| m10-acceptance-pack.md（§3.3） | 同上 | 同上 |
| m10-materials-alignment.md（G5 行） | 「两个口径 2 分 16 秒 / 1099 秒」 | 补上第三段（CI 的 46 秒）与本文的出处 |

**没有改的**（它们是**测量记录**，不是口径）：[m8-install-rehearsal.md](m8-install-rehearsal.md)、
[reader-dry-run.md](reader-dry-run.md)、m10-reader-walkthrough-4th.md。
这三份记的是**当时某台机器上发生过什么**，把里面的数换成 CI 的数就是篡改记录，
而不是「把口径写回去」。

## 4. 这一轮的范围：哪些是本窗口做的、哪些留给主会话

**本窗口做的**（分支 `claude/recursing-gauss-bfce6d`；**纯文档**，一个 `.py` 都没改，
所以**源码指纹不变**，报告里的数字保持有效）：

1. **CI 的 job 计数收口**——`.github/workflows/ci.yml` 里是 **13 个 job 定义**
   （`test` 是 3.12/3.13 矩阵），**tag 上 14 次并行运行**；push 与 PR 上 13 次，
   因为「只在推 tag 时跑」的测量比对那个 job 会跳过。
   核过两遍：把 workflow YAML 解析出来数 job 定义（13），再对着两次 run 的 job 列表
   数（tag run `44324097977` 与 main push run `44334171465` 都是 14 条，
   其中测量比对那条在 push 上是 `skipped`）。
   同一个说法的五处副本都改了：[docs/portfolio.md](../portfolio.md)、
   [docs/status.md](../status.md)（汇总行与 §1 的表两处）、
   [CLAUDE.md](../../CLAUDE.md) 与 [AGENTS.md](../../AGENTS.md)（同一个文件，有测试盯着它俩相等）、
   [docs/HANDOVER.md](../HANDOVER.md)。
2. **两页 how-to-verify 补上 `suite.xfailed`**——权威值取自
   [phase1-execution-report.md](phase1-execution-report.md) 的 `<!--fig:suite.xfailed-->` 标记
   （**0**），不是手抄的。两页各补一条 xfailed 的读法，汇总行那一行补上 `0 xfailed`；
   `scripts/check-release-numbers.py` 现在会把这两个数与执行报告比（退出码 0）。
3. **C6 判据 (a) 的构建时间写回**——本文是那个新口径的**唯一落点**，§3 那张表列了
   每个引用旧口径的地方现在指向哪里。
4. **引用重锚**——本轮动了几个被引用的文件，引用检查器报的 6 处漂移已改；
   三份**活着的**文档（[docs/glossary.md](../glossary.md)、
   m10-reader-kit.md、
   [figures-coverage-design.md](figures-coverage-design.md)）里指向它们的 18 处引用也改了。
   `scripts/check-doc-citations.py`：**drifted: 0**。

**留给主会话的**：

1. **登记本文**：`docs/reports/c6-build-time-from-ci.md` 还没进 `docs/reports/README.md`
   的索引，也没进 `scripts/check-doc-citations.py` 的 `DOCS` 清单（本窗口按分工不登记）。
   登记之后，本文里的 `file:line` 引用才会被引用检查器扫到。
2. **[outward-number-parity.md](outward-number-parity.md) §7 第 4、5 条**：
   第 4 条（两页 how-to-verify 写不写 xfailed）**已经定了并做完了**；
   第 5 条（`docs/portfolio.md:67`–`:68` 归不归那个门禁）**还是主会话的决定**——
   它的测试数 `1,695` 是发版测量钉住的对外数字，要等重测之后一起同步，本轮没动它。
   顺带一处更正：那份报告的第 6 条写「job 定义从 13 个变成 14 个」——
   实测**前后都是 13 个定义**（`test` 展开成两条才是 14 次运行），
   陈旧的是那一行的 **12**（少一个数），不是别的。
3. **M10 读者材料里还有一句假话**：两份材料仍写着「**镜像里没有 `examples/`** → 要挂两个卷」，
   而镜像现在自带样本（[docker-image-samples.md](docker-image-samples.md) 已落地）。
   那是**命令**那一条判据，不在本轮（构建时间）的范围里。
4. **十几份点时间报告里的行号刻意没动**：读者走查、复核、审计这一类报告各自声明了
   它的行号属于哪棵树（例如 [handover-tails-audit.md](handover-tails-audit.md)
   写着「本报告的 `file:line` 只在 `0a8e02e` 上成立」）。
   本轮改了几个被它们引用的文件，那些行号会跟着移——**但它们是关于那些树的**，
   跟着移过去等于把记录改成今天的样子。要不要重锚，是主会话按每份报告的声明逐份定的。

