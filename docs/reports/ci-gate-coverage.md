# CI 门禁覆盖度复核（v1.0.0 发版）

> 复核日期：2026年11月17日 · 复核方式：只读 · 复核树：`claude/ci-gate-coverage-840415` @ `062c4b5`
>
> 本文回答四个问题：**CI 到底跑了什么**、**这一版发版依赖的门禁哪些在 CI 里**、
> **CI 在什么时候才验到发版树**、**哪些东西改了不会被任何自动化发现**。
> 最后一条是本文最有价值的部分。

## 摘要

- CI 只在 `main` 上触发（`.github/workflows/ci.yml:3-7`），**推发版分支没有 CI 兜底**。
- 本报告 §2 的 **21 项门禁/检查**里，**CI 实际跑 14 项**（其中 1 项是间接的：`tests/test_doc_citations.py:49` 调 `check-doc-citations.py` 的 `main()`）。**只存在于本地的是 6 道**：完整测量、契约活检、M10 自查、对外素材点检、Release 附录行号重锚、`docs/how-to-verify.md` 的示例输出核对。
- **重打 tag 这一动作本身不会被任何 CI job 验到**：tag 推送不触发 workflow（`on.push` 只收 `main` 分支，`ci.yml:4-5`）。
- 源指纹只覆盖 `src/dexatlas/`、`tests/`、`pyproject.toml`、`scripts/refresh-report-figures.py`（`scripts/refresh-report-figures.py:111`、`:583-602`）。**改 `scripts/` 下其它脚本、改 `docs/`、改 README，都不会让报告的数字变陈旧** —— 本轮 74 个 commit 里改了 5 个脚本，指纹未变，`tests/test_docs.py` 仍然全绿。

---

## 1. CI 到底跑了什么

### 1.1 触发条件

`.github/workflows/ci.yml:3-7`：

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

两条触发都只认 `main`。由此得到三个事实：

1. **推 `main` 之外的任何分支都不跑 CI** —— 包括发版分支、包括本复核所在的 `claude/*` 分支。
2. **推 tag 不跑 CI** —— `on.push.branches` 是分支过滤器，tag 推送既不匹配 `branches` 也不匹配 `pull_request`。这一条对「重打 tag」的影响见 §3.3。
3. `concurrency: cancel-in-progress: true`（`ci.yml:9-11`）—— 连续两次推 `main`，**后一次会取消前一次的 run**。第一次 run 的结论就此丢失，且没有留下任何记录。

### 1.2 Job 清单

| # | Job（`ci.yml` 行号） | 名称 | 跑什么 | checkout 深度 |
|---|---|---|---|---|
| 1 | `lint`（`:17`） | Lint and format | `ruff check .`（`:34`）、`ruff format --check .`（`:36`）、`mypy`（`:38`）、`vulture --min-confidence 80`（`:45`）、`actionlint`（`:50-51`）、`check-version-claims.py`（`:64-83`） | **`fetch-depth: 0`**（`:25-27`） |
| 2 | `test`（`:87`） | Tests (Python 3.12 / 3.13) | `uv sync --extra dev --extra analysis --extra mcp --frozen`（`:110`）、`fetch-fixtures.sh`（`:112-116`）、setup-java（仅 3.12，`:125-128`）、**`pytest --cov=dexatlas`**（`:136`）、`coverage report --fail-under=80`（`:138-139`）、默认配置端到端反编译（`:155-164`） | **`fetch-depth: 0`**（`:98-104`） |
| 3 | `test-partial-backends`（`:166`） | Tests (Apktool only, no JADX) | `pytest --cov=dexatlas`（`:228`） | 默认（浅） |
| 4 | `m3-comparison`（`:238`） | M3 comparison stays reproducible | M3 复现性脚本 + pytest（`:336`） | 默认（浅） |
| 5 | `docker`（`:374`） | Docker image builds | 镜像构建 | 默认（浅） |
| 6 | `security`（`:384`） | Dependency audit | 依赖审计 | 默认（浅） |

CI 一共 6 个 job、7 次并行运行（`test` 是 3.12 / 3.13 两份）。

### 1.3 checkout 深度与 tag 的可见性

`fetch-depth: 0` 出现在 `lint`（`:25-27`）与 `test`（`:98-104`）两个 job，注释写明了原因：**版本声明检查要读 tag 列表**。这一点是成立的：

- `scripts/check-version-claims.py` 的 facts 来自 `git tag`（`:386-403` 的 `git()`、`:480-505` 的 `read_facts()`）。
- **浅克隆（没有 tag）时，检查器不会「什么都没查所以通过」**：它退回到从 CHANGELOG 推导已发布版本（`:485-504`），并把 tag 标为未知；`:499-503` 的注释写明了这个降级路径。
- 触发条件上 `push` 用 `github.event.before` 作为 base、`pull_request` 用 merge-base（`ci.yml:64-83`）：PR 用 merge-base 是为了让「分支上任何一次推送引入的声明」都算作本次新增。

**推论（推断，依据 `ci.yml:4-5` + `:25-27`）**：只有 `lint` 与 `test` 两个 job 能看到完整 tag 列表；`test-partial-backends`、`m3-comparison`、`docker`、`security` 是浅克隆，它们跑的任何 git 相关逻辑都看不到 tag。这三个 job 不读 tag，所以现在无害 —— 但**任何将来放进这三个 job 的版本相关检查都会拿到一个没有 tag 的世界**。

---

## 2. 发版依赖的门禁逐条对照

「本地」列指这一版发版实际依赖过、或本次复核实跑过的。

| 门禁 / 检查 | 本地 | CI（job + 触发条件） | 漏掉会怎样 | 建议 |
|---|---|---|---|---|
| `scripts/check-version-claims.py --base auto` | ✅ 发版时跑；本次复核实跑 exit 0 | ✅ `lint` job（`:64-83`），push 到 `main` / PR 到 `main` | 文档里「v1.0.0 已发布」「最新 tag 是 X」与实际 tag 矛盾时无人发现 | 保持。补一条 tag 触发的运行（见 §6-1） |
| `scripts/check-doc-citations.py` | ✅ 实跑 exit 0，221 处引用、0 漂移 | ⚠️ **间接**：`tests/test_doc_citations.py:49-59` 调 `checker.main()`，随 `test` / `test-partial-backends` job 跑 | **只覆盖 4 个文档**（`scripts/check-doc-citations.py:57-61`：`analysis-provenance.md`、`architecture/public-contracts.md`、`reports/phase1-execution-report.md`、`benchmarks/large-apk.md`）。Release 正文、对外素材、how-to-verify 的行号引用全部失明 | 把 `docs/releases/*.md` 与 `docs/reports/v1.0.0-github-release-body.md` 加进 `DOCS`（见 §6-4） |
| `tests/test_docs.py`（含源指纹断言） | ✅ 实跑 **60 passed** | ✅ `test` job（pytest 全量） | 报告数字与当前代码树脱节、文档链接断裂、必需文档缺失时无人发现。**这是全套门禁里唯一能自动发现「文档说的 ≠ 代码做的」的** | 保持。注意它的边界（见下） |
| `ruff check .` | ✅ | ✅ `lint`（`:34`） | 未用导入、明显错误进主干 | 保持 |
| `ruff format --check .` | ✅ | ✅ `lint`（`:36`） | 格式漂移（Windows 上还兼作 CRLF/LF 混合的告警者） | 保持 |
| `mypy`（strict） | ✅ | ✅ `lint`（`:38`） | 类型错误进主干 | 保持 |
| `vulture --min-confidence 80` | ✅ | ✅ `lint`（`:45`） | 死代码累积 | 保持 |
| `actionlint` | ✅ | ✅ `lint`（`:50-51`） | 工作流文件本身写错 → GitHub 拒绝调度任何 job，表现为「一次没有输出的失败」 | 保持 |
| `scripts/refresh-report-figures.py` **完整测量** | ✅ 发版时跑（写回报告数字、README badge） | ❌ **不跑** | 报告里的覆盖率 / 测试数 / 源指纹永远停在最后一次本地测量 | 至少在 tag 触发时跑 `--check`（见 §6-7） |
| `pytest --cov` 覆盖率门槛 | ➖ 发版门禁是完整测量，不是 80% 门槛 | ✅ `test` / `test-partial-backends` job，`coverage report --fail-under=80`（`:138-139`） | 覆盖率跌破 80% 时无人发现 | 保持。**注意 CI 卡 80%，报告写 93.3% —— 两者之间没有自动比对** |
| `tests/test_public_contracts.py`（契约**快照**） | ✅ | ✅ `test` job | 契约的**行为**变了（退出码、端点、工具、形状）时快照先红 | 保持 |
| `scripts/verify-public-contracts.py`（契约**活检**） | ✅ 实跑（三后端齐备 48/48，退出码 0） | ❌ **不跑** | 活检判定逻辑改坏、脚本自身有 bug 时无人发现；**契约表 §7 的实跑记录会一直是旧的** | 加 job（见 §6-5） |
| `scripts/m10_selfcheck.py`（M10 自查） | ✅ 实跑 | ❌ **不跑**（`tests/test_m10_selfcheck.py` 只有 2 个测试，都不调它的 `main()`） | `docs/reports/m10-selfcheck.md` 这份**手写快照**会与脚本当前行为脱节，无人发现 | 加 job（见 §6-6） |
| `scripts/remap-citations.py`（引用重锚工具） | ✅ 用过 | ❌ 不跑（它是工具不是检查） | —— | 无需进 CI |
| `scripts/fetch-fixtures.sh` | ✅ | ✅ `test` job（`:112-116`） | 集成测试拿不到第三方样本 → **skip 而不是 fail**（CLAUDE.md 已记此坑） | 保持 |
| M3 复现性 | ✅ | ✅ `m3-comparison` job | 基准不可复现 | 保持 |
| Docker 镜像 | ✅ | ✅ `docker` job | 镜像构建失败无人知道 | 保持 |
| 依赖审计 | ✅ | ✅ `security` job | 已知漏洞进依赖 | 保持 |
| **对外素材点检**（`docs/reports/outreach-publish-checklist.md`） | ✅ 人工逐条打勾 | ❌ 不跑 | Upwork 素材里的数字与本仓库脱节 | 见 §4.1 |
| **Release 附录行号重锚** | ✅ 人工核对（本轮 `062c4b5` 改了 8 处） | ❌ 不跑 | 附录指向的行不再写它声称的内容 | 见 §4.2 |
| **`docs/how-to-verify.md` 的命令与示例输出** | ✅ 人工 | ❌ 不跑 | 文档里的命令跑不通、示例输出过期 | 见 §4.3 |

### 2.1 源指纹的边界（最容易被误解的一条）

`scripts/refresh-report-figures.py:111`：

```python
FINGERPRINT_FILES = ("pyproject.toml", "scripts/refresh-report-figures.py")
```

配合 `:583-602` 的 `fingerprint_files()`，指纹覆盖的集合是：`src/dexatlas/**/*.py` + `tests/**/*.py` + `pyproject.toml` + `scripts/refresh-report-figures.py`。

**不覆盖**：`scripts/` 下其它脚本、`docs/` 全部、`README.md` / `README.zh-CN.md`、`examples/`。

这直接决定了 §3.3 的结论，也解释了本轮的一个真实情形：tag 树到当前 HEAD 之间改了 5 个 `scripts/` 下的脚本（其中 `scripts/verify-public-contracts.py` 改了 82 行），**指纹一动不动**，`tests/test_docs.py` 仍然 60 passed。

---

## 3. 触发条件的含义：CI 什么时候才验到发版树

### 3.1 顺序推演

这一版的发版顺序是「发版 commit → 打 tag → 推 main → CI 重跑」。逐步推：

| 步骤 | CI 看得到吗 | 说明 |
|---|---|---|
| 发版 commit 推到发版分支 | ❌ | 分支不是 `main`（`ci.yml:4-5`）。**这一步完全没有 CI 兜底**，只有本地门禁。 |
| 打 tag（本地 / 远端） | ❌ | tag 推送不匹配 `on.push.branches`，**不产生任何 run**。 |
| 推 `main` | ✅ | 此刻 CI 才第一次看见这棵发版树。`lint` 与 `test` 两个 job 拿到的是**这次 push 的 commit**，并带完整 tag 列表（`fetch-depth: 0`）。 |
| CI 重跑 | — | `lint` 的 version-claims 用 `github.event.before` 作为 base（`ci.yml:68`、`:82`），所以「这次 push 新增的声明」全部被当作待查项；`test` 的 pytest 全量在发版树上跑。 |

**结论：CI 验到发版树是在「推 main」之后，不是在「打 tag」之后。** 主线是唯一的第二道防线，而这道防线只在最后一步存在。

### 3.2 tag 在 CI 判定里的作用

`scripts/check-version-claims.py` 的判定完全依赖 `git tag` 的结果：

- 「v1.0.0 已发布」但仓库里没有 `v1.0.0` 这个 tag → finding（`:804-816`），CI 红灯。
- 反向断言：「未发布」类措辞用在**实际已有 tag** 的那个版本上 → finding（`:818-844`），CI 红灯。
- 「最新 tag 是 X」类断言与实际 newest tag 不符 → finding（`:823-840`）。

所以：

- **tag 必须在推 `main` 之前打好**，否则 CI 那次 run 看到的是旧 tag 列表，「v1.0.0 已发布」会判红。补救办法是再推一次 `main`（哪怕只改一行），让 CI 以新 tag 重跑。
- **CI 不会因为 tag 变了而自己重跑** —— 没有任何 workflow 监听 tag 事件。

### 3.3 重打 tag 前后的差异（实测）

本轮的事实（在本 worktree 实测）：

- `v1.0.0` 是 **annotated tag**：tag 对象 `e937ca1`，指向 commit **`8f9ddca`**（`v1.0.0^{commit}`）。
- `8f9ddca` 正是 **`main` 的 HEAD**（`git rev-parse main` 同值，`git rev-list --count v1.0.0^{commit}..main` = 0）。
- 当前复核树 HEAD `062c4b5` 在 `main` 之上 **74 个 commit**：`git log --oneline main..HEAD`。
- 这 74 个 commit 里：**49 个改 `docs/`**，5 个改 `scripts/`（`m10_selfcheck.py`、`m6_level2_narrow_verify2_report.py`、`m6_level2_narrow_verify_audit.py`、`m6_level2_retest_report.py`、`verify-public-contracts.py`，共 +130 / −22 行），另加 `CHANGELOG.md`、`README.md`、`README.zh-CN.md`。
- **`src/` 与 `tests/` 一行未改** —— `git diff --stat 8f9ddca HEAD -- src/ tests/` 为空。

由此得到三个结论：

1. **重打 tag 本身不会让任何 CI job 变红。** 触发条件是分支不是 tag，tag 推送根本不产生 run；即使产生了，version-claims 看的是「哪些版本已发布」，tag 从 commit A 挪到 commit B 不改变「v1.0.0 已发布」这个事实。
2. **报告的数字在当前树仍然「新鲜」。** 指纹只覆盖 `src/` + `tests/` + `pyproject.toml` + 测量脚本（§2.1），这 74 个 commit 一个都没碰 → 指纹不变 → 实测 `pytest tests/test_docs.py` **60 passed**、实测 `pytest --collect-only` **1588 collected**，与文档写的 1588 一致。
3. **但「v1.0.0 release tree」这棵树与当前树在脚本层面已经不同。** 契约活检的判定逻辑在 tag 之后被改过（`scripts/verify-public-contracts.py:453-510`：从「这台机器装没装后端」改成「这次运行有没有后端参与」），实跑结果从 46/48、退出码 1 变成 48/48、退出码 0（记录见 `docs/architecture/public-contracts.md:359-362`）。**这次改动既不改指纹、也不被任何 CI job 跑到。** 它之所以被发��材料知道，是因为有人手工实跑并手工改了文档。

> **推断（依据 `ci.yml:4-5`、`:25-27`、`:98-104` 与 §2.1）**：如果这 74 个 commit 现在合进 `main`，CI 会重跑。`lint` 的 version-claims 会以 `--base 8f9ddca` 复查这 74 个 commit 新增的声明；`test` 的 pytest 全量会在新树上跑，`tests/test_docs.py` 仍绿（指纹未变），`tests/test_doc_citations.py:49` 会在**扩大的**文档集合上复查引用 —— 但 `docs/reports/v1.0.0-github-release-body.md` 与 `docs/releases/*.md` 仍不在检查范围内（`scripts/check-doc-citations.py:57-61`）。**这次合并会得到一次「全绿」，而绿的部分不覆盖这次改动里最要紧的那一半（对外材料与契约活检）。**

---

## 4. 哪些东西改了不会被任何自动化发现

这一节是本次复核的产出重点。判定标准：**这个仓库里没有任何脚本、测试或 workflow 会因为它变红**。

### 4.1 对外素材里的数字（Upwork / 案例 / 提案）

- **位置**：`docs/outreach/*.md`（5 份）、`docs/case-studies/*.md`（4 份）、`docs/proposals/exit-code-partial-read.md`、`docs/portfolio.md`、`docs/service-commitments.md`。
- **为什么没人发现**：`scripts/check-version-claims.py` 有三组检查 —— `check_release_numbers` 只作用于 `docs/releases/{tag}.md` 与 CHANGELOG 的发版段（`:116`、`:892-921` 的 `release_documents()`、`:1128`）；`check_badges` 只匹配 shields.io 形式的 badge 行里的数字（`:1181-1200`，由 `:1339-1341` 调用）；`check_text` 只查**版本声明**（最新 tag 是谁、某版本是否已发布，`:737-890`）。**素材里的覆盖率、测试数、样本数、MCP 工具数一律不查。**
- **现在靠什么**：`docs/reports/outreach-publish-checklist.md` —— 一份**纯人工勾选清单**（§1.1 的 1,588 / 1,441 / 147 / 93.3% / MCP 11 / 三个样本两份分析，§2 的字段长度，§3 的占位符，§4 的三个 zip，§5 的「不外发的东西」，§7 的发布后留痕）。CI 不跑它，也没有任何测试读它。
- **风险**：素材改了数字、或代码变了导致数字陈旧，**没有任何东西会响**。

### 4.2 Release 正文附录的行号出处

- **位置**：`docs/reports/v1.0.0-github-release-body.md:297-347` 的两张出处表，30 余条 `文件:行`（如 `docs/reports/phase1-execution-report.md:76`、`:877`、`:1082`，`scripts/fetch-fixtures.sh:12`、`:45`–`:48`，`scripts/refresh-report-figures.py:111`、`:583`–`:602`）。
- **为什么没人发现**：该文件**不在** `scripts/check-doc-citations.py` 的 `DOCS` 列表（`:57-61`），所以这些行号**从不被核对**。
- **实证（本复核发现）**：`docs/reports/final-outward-consistency.md:51` 记着「契约活检 49 项」在 Release 正文里的出处是 `docs/reports/v1.0.0-github-release-body.md:96`、`:174`、`:248`。**这三个行号现在指向的都不是「49 项」** —— 实际在 `:103-104`、`:185`、`:274-275`、`:338`。两份报告互相引用的行号已经漂移，而**没有任何自动化会发现**。
- **现在靠什么**：人。本轮的 `062c4b5`「Release 正文附录：8 处行号按内容重锚」就是**手工**做的逐条核对（提交说明写明「逐条按内容重新定位并核对，不靠行号推算」）。
- **风险**：任何一次改动 `src/`、`scripts/`、`docs/reports/phase1-execution-report.md` 的行，都会让这张表悄悄过期，而 CI 全绿。

### 4.3 `docs/how-to-verify.md` 的命令与示例输出

- **位置**：文档给出 10 条读者命令（`:47`、`:57`、`:75`、`:84`、`:108`、`:149`、`:175`、`:209`、`:298`、`:334-336`），并写出**期望输出**，例如 `:119` 的 `→ 1441/1588 tests collected (147 deselected)`、`:120` 的 `→ 147/1588 tests collected (1441 deselected)`。
- **为什么没人发现**：`scripts/m10_selfcheck.py` 会查「验收包点名的门禁是不是路径上存在的命令」，但那是**存在性**，不是**输出比对**；而 `m10_selfcheck.py` 本身 CI 也不跑（§2）。文档里的期望输出是**硬编码文本**，没有任何东西比对它与真实输出。
- **实证**：本次复核实跑 `pytest --collect-only -q` → **1588 collected**，与 `:119`/`:121` 的分母一致；但这是**本次人工跑出来的**，不是任何自动化保证的。

### 4.4 契约活检的实跑结果

- **位置**：`docs/architecture/public-contracts.md:342-485` 的 §7「验证记录」，含 `:359-362` 的两次实跑表（47/47 与 48/48）。
- **为什么没人发现**：`tests/test_public_contracts.py` 是**快照**测试（比对契约的**行为**），**不跑活检**；`scripts/verify-public-contracts.py` 在 CI 里零引用（`ci.yml` 全文无此脚本）。
- **实证**：该脚本的判定逻辑在 tag 之后被改过（`scripts/verify-public-contracts.py:450-520`：从「这台机器装没装后端」改成「这次运行有没有后端参与」），实跑从 46/48（退出码 1）变成 48/48（退出码 0）。
- **实证（本复核发现，两份对外材料互相矛盾）**：契约表 `docs/architecture/public-contracts.md:359-362` 记的是修复后的实跑 —— 三后端齐备 **48/48、退出码 0**；而 **Release 正文附录 `docs/reports/v1.0.0-github-release-body.md:339` 仍写着「48 items ran and **46 passed** … the script exits 1」**，即修复前的那次结果。脚本修好了、契约表改对了，**Release 正文没跟上**，而这两份材料都不在任何自动检查的范围内。**读者拿到两份说法相反的记录。**
- **附带**：「静态 49 条 = REST 28 + MCP 6 + CLI 15」这个数被 5 处发布材料复述（`CHANGELOG.md:360-361`、`docs/releases/v1.0.0.md:65`、`docs/reports/final-outward-consistency.md:51`、`docs/reports/v1.0.0-github-release-body.md:103-104`、`:185`、`:274-275`、`:338`）。它是**为了让这 5 处材料不用改而刻意维持**的人工耦合不变量 —— 没有任何断言守着「活检的 `check()` 调用点数 == 49」。

### 4.5 M10 自查快照

- **位置**：`docs/reports/m10-selfcheck.md`（手写快照，记录 40 项的通过 / 失败 / 需人工分布与执行日期）。
- **为什么没人发现**：`scripts/m10_selfcheck.py` 的判据改过（`8524503`「自查脚本的变更记录判据改为版本无关」），改完要人重跑重写快照；`tests/test_m10_selfcheck.py` 只有 2 个测试（`:69`、`:76`），都不调 `main()`；CI 不跑该脚本。
- **风险**：快照里的「通过 40 / 失败 0 / 需人工 40」随时可能不再是脚本的当前输出。

### 4.6 源指纹覆盖不到的改动

- **位置**：`scripts/refresh-report-figures.py:111`、`:583-602`。
- **为什么没人发现**：改 `scripts/` 下除测量脚本外的任何文件（`verify-public-contracts.py`、`m10_selfcheck.py`、6 个 `m6_*.py`）、改 `docs/`、改 README，**指纹都不动**，于是 `tests/test_docs.py:696-699` 的指纹断言照样绿、报告里的 93.3% 照样「新鲜」。
- **实证**：本轮 74 个 commit 改了 5 个脚本（+130 / −22 行），指纹未变，`tests/test_docs.py` 实跑 60 passed。**这正是「改了不会被任何自动化发现」的教科书案例。**

### 4.7 验收包里 40 项「需人工」的判定

- **位置**：`docs/reports/m10-acceptance-pack.md`（40 项）、`docs/reports/m10-invitation-sender-checklist.md:201-215`（通过 40 / 失败 0 / 需人工 40）。
- **为什么没人发现**：这些**本来就该**由一位读者在真实机器上执行并填入 `docs/reports/m10-review-record-template.md`。`scripts/m10_selfcheck.py:738-740` 明确把它们标成 `manual`，且 `manual` 不算失败。
- **如实说明**：这一项**不是缺陷**，是设计的边界。列在这里是为了不让「40 项全部自动化了」这种误读成立。

### 4.8 素材里需要人判断的占位

- **位置**：`docs/outreach/cover-letter-templates.md:20-21` 的 `{{...}}` 占位符；`docs/reports/m10-invitation-sender-checklist.md:14`、`:63`、`:133` 的「由你决定」。
- **为什么没人发现**：占位符**应该**由人在发送前替换。自动化检查「占位符是否被替换」在原则上就与「发布前最后点检」冲突（模板态是合法的仓库态）。
- **如实说明**：同样不是缺陷，是「机器不该替人做的判断」。

### 4.9 本节小结

| # | 改动什么 | 会被谁发现 |
|---|---|---|
| 4.1 | 对外素材里的测量数字 | **没有人**（人工清单） |
| 4.2 | Release 附录里的 `文件:行` | **没有人**（人工重锚） |
| 4.3 | how-to-verify 的示例输出 | **没有人**（人工实跑） |
| 4.4 | 契约活检的实跑结果 / 静态 49 条 | **没有人**（人工实跑 + 人工改文档） |
| 4.5 | M10 自查快照 | **没有人**（人工重跑重写） |
| 4.6 | `scripts/` 下非测量脚本、`docs/`、README | **没有人**（指纹不覆盖） |
| 4.7 | 40 项人工验收判定 | **按设计就该没人** |
| 4.8 | 发送前的占位符与人工判断 | **按设计就该没人** |

**六个「不该没人却没人」的（4.1–4.6），全部集中在对外材料与本地脚本上。** 它们恰好是 v1.0.0 这一版发版质量里最要紧、也最没有自动化兜底的部分。

---

## 5. 结论：发布线上有几道防线

按执行顺序，三道：

### 第一道：本地全门禁（人跑）

发版检查清单的步骤 1–7（`docs/reports/v1.0.0-release-checklist.md:90-170`：版本号定稿 `:90`、全门禁 `:99`、完整重测量 `:114`、提交与 annotated tag `:133`、推送 `:143`、GitHub Release `:152`、README / 文档状态同步 `:163`）。实际内容是：ruff / format / mypy / vulture、`check-version-claims.py`、`check-doc-citations.py`、`pytest` 全量、`refresh-report-figures.py` 完整测量（写回报告数字与 README badge）、`verify-public-contracts.py` 活检、`m10_selfcheck.py` 自查、对外素材点检、Release 附录重锚。

**这一道最厚** —— 它包含后面两道都没有的东西：完整测量、活检、自查、素材点检、附录重锚。**但它完全依赖人记得跑、并且跑对。**

### 第二道：CI（推 `main` 之后）

6 个 job。真正与「发版质量」直接相关的是两个：`lint`（静态门禁 + 版本声明）和 `test`（pytest 全量 → 内含 `tests/test_docs.py` 的指纹断言与 `tests/test_doc_citations.py:49` 的真实文档引用复查 + 契约快照 + 覆盖率 80% 门槛 + 默认配置端到端反编译）。

### 第三道：分发（GitHub Release / 页面）

无自动化。Release 正文与附录一旦贴上去，改了不会有人知道。

### 5.1 哪一道最强

**CI 的 `test` job 最强**，因为它是**唯一**一道能在无人参与的情况下发现「文档说的 ≠ 代码做的」的防线：`tests/test_docs.py:696-699` 的源指纹断言让「代码变了、报告没重测」当场变红；`tests/test_doc_citations.py:49-59` 让「行号漂了」当场变红；`tests/test_public_contracts.py` 让「契约行为变了」当场变红。

**但它最强的一环恰好是有边界的**：指纹不覆盖 `scripts/` 下其它脚本、不覆盖 `docs/`、不覆盖 README（§2.1）。本轮 74 个 commit 里改了 5 个脚本、49 份文档，指纹一动不动（§3.3）。**所以 CI 最强的地方，恰好是这一版发版改动最少的地方。**

**本次复核就在这道防线的盲区里找到了一处实质矛盾**：Release 正文附录仍记着契约活检「48 项执行、46 通过、脚本退出码 1」（`docs/reports/v1.0.0-github-release-body.md:339`），而契约表 §7 已记「48/48、退出码 0」（`docs/architecture/public-contracts.md:359-362`）。**两份都是对外材料，CI 全绿，没有任何自动化会响**（§4.4）。

### 5.2 哪一道其实只在本地存在

**六道**：

1. **完整测量**（`refresh-report-figures.py`）—— CI 只有 80% 覆盖率门槛，报告里的 93.3% 与 1588 全靠本地测量写回。
2. **契约活检**（`verify-public-contracts.py`）—— CI 零引用。
3. **M10 自查**（`m10_selfcheck.py`）—— CI 零引用，连测试都不调它的 `main()`。
4. **对外素材点检**（`outreach-publish-checklist.md`）—— 纯人工清单。
5. **Release 附录行号重锚** —— 纯人工核对。
6. **`docs/how-to-verify.md` 的示例输出核对** —— 纯人工实跑。

其中第 1 条还带来一个结构性后果：**报告里的数字描述的是「最后一次本地测量时的树」，CI 只能证明那棵树还能过 80%，不能证明它还是当前树** —— 而这个「还是不是」恰好由 `tests/test_docs.py` 的指纹断言承担了。它是有效的，但它只对 `src/` + `tests/` + 两个文件有效。

### 5.3 一句话

> **主线是唯一的第二道防线，而这道防线在发版分支上不存在；它能守住的那部分，恰好是这一版改动最少的那部分。**

---

## 6. 必须改的 N 处

只列清单，不代改。全部是 CI 配置或检查清单的建议。

1. **`.github/workflows/ci.yml` 增加 tag 触发**：在 `on.push` 下加 `tags: ['v*']`，并让 `lint` 在该事件下跑 `check-version-claims.py`。理由：重打 tag 现在不产生任何 run（`ci.yml:4-5`），tag 指向错了永远没人知道。
2. **`.github/workflows/ci.yml` 放宽 `on.push.branches`**：去掉 `[main]` 过滤，或至少加 `claude/**` 与发版分支。理由：推发版分支现在完全没有 CI 兜底（§3.1）。
3. **`.github/workflows/ci.yml` 调整 `concurrency.cancel-in-progress`**：对 `main` 设为 `false`，或在取消时保留前一次的结论。理由：连续两次推 `main` 时，前一次（含发版 commit）的验证结果被静默丢弃（`ci.yml:9-11`）。
4. **`scripts/check-doc-citations.py:57-61` 的 `DOCS` 列表**：加入 `docs/releases/v1.0.0.md`、`docs/reports/v1.0.0-github-release-body.md`（以及后续每个发版正文）。理由：Release 附录的 20 余条行号出处现在从不被核对（§4.2）。
5. **新增 CI job 跑 `scripts/verify-public-contracts.py`**：需要三后端，可挂在已有 setup-java + apktool 的 `test` job（3.12）里。理由：契约活检的实跑结果没有任何自动化守护（§4.4）。
6. **新增 CI job 跑 `scripts/m10_selfcheck.py`**：只读、退出码可判，零成本。理由：自查快照会与脚本脱节（§4.5）。
7. **新增 CI job 跑 `scripts/refresh-report-figures.py --check`**（只比较不写入），至少挂在 tag 触发上。理由：完整测量目前纯本地（§5.2-1）。
8. **把 `scripts/verify-public-contracts.py` 与 `scripts/m10_selfcheck.py` 纳入源指纹**，或在 `docs/reports/phase1-execution-report.md` 与 README 里显式写明「指纹不覆盖这两个脚本」。理由：改它们不影响指纹（`scripts/refresh-report-figures.py:111`、`:583-602`、§4.6）。
9. **扩展 `scripts/check-version-claims.py` 的 measured-numbers 规则到对外素材**（`docs/outreach/`、`docs/case-studies/`、`docs/proposals/`），覆盖覆盖率、测试数、样本数。理由：素材数字现在零自动化（§4.1）。
10. **给 `docs/how-to-verify.md` 的示例输出建立核对**（至少 `pytest --collect-only` 的分母与两段分类数）。理由：文档给读者的期望输出没有任何东西比对（§4.3）。
11. **为「静态 49 条」加断言**：在 `tests/test_public_contracts.py` 或活检脚本里断言 `check()` 调用点数与文档复述的数一致。理由：这是为少改 5 处材料而维持的人工耦合不变量（§4.4）。

> 第 11 条不计入前 10 条的话，「必须改的 N 处」= **11 处**。全部都是 CI 配置或检查清单层面的建议，没有一条要求改动 `src/` 的行为。

---

## 附 A：本次复核跑过的只读命令与结果

全部在本 worktree 内执行；未写 `E:\Dexatlas` 共享树；未跑 `pytest --cov`、未跑 `coverage`、未 `uv sync`、未跑 `refresh-report-figures.py`。

| 命令 | 结果 |
|---|---|
| `python scripts/check-doc-citations.py` | exit 0 —— `citations: 221`（`naming a symbol: 162`、`pointing only at a location: 59`）、`unresolved paths: 0`、`drifted: 0` |
| `python scripts/check-version-claims.py --base auto` | exit 0 —— `tags: handover-2026-11-10, phase1-acceptance-2026-10-21, v0.1.0, v0.1.1, v0.1.2, v0.1.3, v0.2.0, v1.0.0`；`package version: 1.0.0`；`newest release: v1.0.0`；`documents read: 115`；`findings: 2 (2 already in 8f9ddcaf)`（两条均为 v0.2.0 / CHANGELOG 的历史覆盖率 drift，base 已含） |
| `pytest tests/test_docs.py -q`（不带 `--cov`） | **60 passed**，0 skipped —— 含源指纹断言（`tests/test_docs.py:696-699`） |
| `pytest --collect-only -q`（不带 `--cov`） | **1588 tests collected** |
| `git cat-file -t v1.0.0` / `git rev-parse v1.0.0^{commit}` | `tag`（annotated）/ `8f9ddcaf7804841d77270c1fdb548110faecc598` = `main` HEAD |
| `git diff --stat 8f9ddca HEAD -- src/ tests/` | 空（源码树未变） |
| `git diff --stat 8f9ddca HEAD -- scripts/` | 5 个文件，+130 / −22 |

## 附 B：本复核未能核实的

- **CI 的实际运行结果**：本复核未联网、未触发 CI，因此「CI 现在是绿还是红」未核实。报告里关于 CI 的陈述均来自 `.github/workflows/ci.yml` 的静态阅读。
- **当前树在 CI 下的覆盖率**：受「禁止 `pytest --cov` / coverage」约束，未实测。报告中的 93.3% 是文档里的既有记载，本复核只验证了它未被任何机制判为陈旧（指纹未变）。
- **`v1.0.0` 重打前的旧 tag 指向**：本 worktree 只保留当前 tag 对象，未能取到重打前的旧指向（未联网、未查远端 reflog）。§3.3 关于「重打」的分析基于当前 tag 指向 `main` HEAD 这一事实与 CI 的触发条件，不依赖旧指向的具体值。
