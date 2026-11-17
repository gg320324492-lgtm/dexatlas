# M10 独立验收 —— 读者工具包（评分表 / 回填说明 / 常见问答）

> **状态：工具包已就绪，等待读者执行。独立验收尚未开始；M10 未完成。**
>
> 本文件是[读者验收包](m10-reader-package.md)的配套工具，只装三样东西：**评分表**、
> **回填说明**、**常见问答**。它不含任何验收结论，也不预填任何分数——本文里
> 每一个空格都还是空的，等读者亲手填。
>
> 编写日期：2026-11-17 · 验收 commit：**v1.0.0 发版 commit**——完整 hash 写在
> [邀请函成稿 §2](m10-invitation-final.md)的占位符里，由验收发起人填好后随函给你；
> 本文件与该 commit 同一棵树 · 判定依据：[验收准备包](m10-acceptance-pack.md)
> · 评分基线：[准备度评估](portfolio-readiness-2026-11-15.md)

## 0. 先读这三条

1. **本工具包是工具，不是结论。** 它的作用是让读者少问一次「写到哪里、怎么打分、
   遇到问题找谁」。它不替代[准备包](m10-acceptance-pack.md)的 40 项判定标准，
   也不替代[记录模板](m10-review-record-template.md)。
2. **独立验收尚未开始。** 仓库里没有任何一项验收结论被判定为「通过」
   （`docs/reports/m10-acceptance-pack.md:3`、`docs/status.md:128`）。
3. **M6 未达验收线，如实告知。** 修复后三轮完整重测合计 49/60 = 81.7%，
   低于三轮合计 ≥54/60 的验收线（`docs/benchmarks/m6-level2-retest4.md:83`）；
   窄验证转通过 3/6，未达 ≥4 的判据（`docs/benchmarks/m6-level2-narrow-verify3.md:61`）。
   项目已按既定方案停止追加修复轮，把 Agent 服务定稿为**现状披露**——
   「有界、证据可核查的 agent 演练」，不宣称达到验收线。这是读者应当重点核对的
   高风险声明之一（`docs/reports/m10-reader-package.md:261`）。

## 1. 你的路径

| 步骤 | 做什么 | 读哪份 | 产出 |
|---|---|---|---|
| 1 | 走一遍完整路径 | [读者验收包 §3](m10-reader-package.md) | A/B/D 组命令、退出码、耗时、卡点 |
| 2 | 逐项判定 | [准备包 §2](m10-acceptance-pack.md)（40 项） | 每项「通过 / 不通过 / 未验证」 |
| 3 | 打分并回填 | 本文件 §2 + [记录模板 §6](m10-review-record-template.md) | GitHub / Upwork 两张评分表 + 总评 |

三步可以并行：你既是首次读者，又是客户视角审阅者时，一份记录就够。

## 2. 评分表

> **维度与权重逐字沿用[准备包 §5](m10-acceptance-pack.md)，一字未改。**
> 不因本轮完成了什么而改权重——改了权重，分数就与 75% / 65% 的基线不可比
> （`docs/reports/m10-acceptance-pack.md:453`）。基线权重出处：
> `docs/reports/portfolio-readiness-2026-11-15.md:34`。

### 2.1 评分等级（0–4）

| 分值 | 定义 |
|---:|---|
| 0 | 未见证据 |
| 1 | 初步证据 |
| 2 | 局部可用，仍有实质缺口 |
| 3 | 在声明环境内有完整演示或复现记录 |
| 4 | 在该维度的限定范围内经过评审并有边界验证 |

4 分不表示软件无缺陷。每一分都要在「证据」栏写出文件、命令或验收项编号；
没有证据的分值记 0。

### 2.2 GitHub 空白评分表

来源权重：准备度评估表「GitHub 权重」列。

| 维度 | 权重 | 分值 / 4 | 加权贡献（分值 ÷ 4 × 权重） | 证据（文件 / 命令 / 验收项） | 扣分原因与遗留 |
|---|---:|---:|---:|---|---|
| 核心工程与证据链 | 30% |  |  |  |  |
| 首次试用与复现 | 20% |  |  |  |  |
| Agent 可用性与评测可信度 | 10% |  |  |  |  |
| 客户交付件与服务边界 | 10% |  |  |  |  |
| 对外展示与个人贡献说明 | 25% |  |  |  |  |
| 独立使用验证 | 5% |  |  |  |  |
| **合计** | **100%** |  | **____%** |  |  |

### 2.3 Upwork 空白评分表

来源权重：准备度评估表「Upwork 权重」列。

| 维度 | 权重 | 分值 / 4 | 加权贡献（分值 ÷ 4 × 权重） | 证据（文件 / 命令 / 验收项） | 扣分原因与遗留 |
|---|---:|---:|---:|---|---|
| 核心工程与证据链 | 20% |  |  |  |  |
| 首次试用与复现 | 15% |  |  |  |  |
| Agent 可用性与评测可信度 | 15% |  |  |  |  |
| 客户交付件与服务边界 | 25% |  |  |  |  |
| 对外展示与个人贡献说明 | 15% |  |  |  |  |
| 独立使用验证 | 10% |  |  |  |  |
| **合计** | **100%** |  | **____%** |  |  |

### 2.4 计算与判定

- 每项贡献 = 分值 ÷ 4 × 该平台权重；六项求和即该平台总分。
- 两个平台**分别**达到至少 90% 才算达到 M10 的评分目标；两平台平均分不能替代。
- 基线是 GitHub 约 75%、Upwork 约 65%（[准备度评估](portfolio-readiness-2026-11-15.md)，
  人工基线）；[复评](portfolio-readiness-2026-11-15-recheck.md)的 77.5% / 68.75%
  是同一组维度与权重下的作者自评更新，不是新的权重基准——重评请与 75% / 65%
  这一档对齐，并在记录里写明依据；目标 90% 是门槛，不是预测。
- 只保留一位小数；不四舍五入到 90% 以上来「达标」。
- **分数通过不能抵消阻断缺陷。** 以下任一项存在，即使总分 ≥90%，也判 M10 不通过：
  1. 证据链断裂（结论无法追到字节，或引用不可解析）；
  2. 数据隔离失败（证据包含 APK/全量源码/未引用字符串，或上传越界）；
  3. 真实模型披露不实（把 scripted 当模型能力，或隐去失败）；
  4. 首次安装有阻断缺陷（独立读者无法按文档完成）。
- 权重与维度必须与基线一致。确需调整时，写清原因、日期，并重新计算基线；
  调整后的分数标注「与 2026-11-15 基线不可直接比较」。
- 100% 只表示六个维度在约定范围内都有充分证据，不表示接单能力、客户评价或
  SaaS 运营能力。

（以上 2.1–2.4 为[准备包 §5](m10-acceptance-pack.md)的原文，权重与定义以该处为准。）

### 2.5 填写指引：每个维度去看什么

下面只说「去哪里取证」，**不改动维度与权重**。「基线已读证据」一列摘自
[准备度评估](portfolio-readiness-2026-11-15.md)的原表，可作为你抽样的起点。

| 维度（原文） | GitHub / Upwork 权重 | 去看什么 | 基线已读证据（2026-11-15） |
|---|---|---|---|
| 核心工程与证据链 | 30% / 20% | C1–C6 与 F 组：报告里的结论能否追到字节；引用能否解析；证据包结构与哈希是否成立；公共契约表与实现是否一致 | Phase 2 计划、M4 源码评审、`tests/test_evidence_invariants.py`、`tests/test_upload_isolation.py`；范围限于已验收能力 |
| 首次试用与复现 | 20% / 15% | A1–A7：从 clone 到第一份报告你自己走通了哪几步、耗时多少、卡在哪 | 安装说明、M4 端到端实测、Docker 和 CI 已有；**未见独立首次用户完成安装的验收记录** |
| Agent 可用性与评测可信度 | 10% / 15% | E1–E5：三轮重测与窄验证的数字、trace、判分口径；脚本级成绩有没有被当成模型能力 | 强预算报告、M4 复验；有真实模型完成案例，但默认预算与开放问题仍有缺口，不能据此声称广泛优于基线 |
| 客户交付件与服务边界 | 10% / 25% | B1–B6、D 组：案例结论、限制、下一步是否可复述；交付件是否自带边界说明 | 案例、报告导出与 portfolio 文案已有；尚缺面向客户的范围、验收、离线证据包完整样例 |
| 对外展示与个人贡献说明 | 25% / 15% | README 与案例里的数字是否可复现；披露是否前后一致 | 双语 README、视频、架构图与案例已存在；当时仍存「视频的 Agent 使用 scripted provider」等未统一项 |
| 独立使用验证 | 5% / 10% | **就是您这一份记录**：有没有未参与实现的读者复现并留痕 | 可见记录主要是项目自身演练与评审，未见独立读者复现及客户式验收记录；不推断项目没有外部用户 |

> 权重一列按准备包原表抄写：GitHub 30/20/10/10/25/5
> （`docs/reports/m10-acceptance-pack.md:468`）、Upwork 20/15/15/25/15/10
> （`docs/reports/m10-acceptance-pack.md:482`）。

### 2.6 总评与一句话结论

打分只依据**您自己的验收记录**。引用作者报告的数字时，注明「作者自述，未独立复现」，
或附上您复现的命令与退出码（`docs/reports/m10-reader-package.md:358`）。

```text
GitHub 总分：____%    Upwork 总分：____%    （各保留一位小数）

总评（对照 40 项判定的整体结论）：

阻断项结论：____ 项通过 / ____ 项不通过 / ____ 项未验证
  （19 个 ★ 阻断项清单见 docs/reports/m10-acceptance-pack.md:173；
    任一 ★ 不通过，M10 即不通过，分数不能抵消）

一句话结论（读者的一句话判断）：

```

## 3. 回填说明

### 3.1 写到哪

一份记录就够：[验收记录模板](m10-review-record-template.md)复制一份，逐段填。
下表是「填哪段、用什么填」的对照。

| 模板段落 | 你填什么 | 材料来源 |
|---|---|---|
| §1 记录元数据（`docs/reports/m10-review-record-template.md:8`） | 角色、是否参与实现、日期、**commit hash（填邀请函成稿 §2 钉定的那一串完整 hash）**、副本来源、OS 与 Python/uv/JDK/Docker 版本、三个后端各自 available / not installed、是否用了作者补充步骤 | 你的机器；后端可用性来自 `uv run dexatlas backends` |
| §2 首次读者会话记录（`docs/reports/m10-review-record-template.md:24`） | A1–A7、B1–B6、D1–D5 每步一行：命令、退出码、关键输出摘要、耗时、卡点编号 | [读者验收包 §3](m10-reader-package.md) 的命令原文 |
| §3 卡点记录（`docs/reports/m10-review-record-template.md:60`） | 每个卡点一条：完整命令、退出码、原始输出（脱敏）、你期望的依据（文档哪一节）、是否阻断后续 | 你自己的日志 |
| §4 客户视角审阅备忘（`docs/reports/m10-review-record-template.md:77`） | 三问结论（输入与结论是否清楚 / 引用能否核查 / 事实与线索能否区分）+ 抽查的 3 条引用 + 红旗清单命中项 | 案例、HTML 报告、证据包 |
| §5 源码评审记录（`docs/reports/m10-review-record-template.md:110`） | 承担源码评审者角色时填：里程碑结论（C/E/F/G 组逐项）、最终门禁（`docs/reports/m10-review-record-template.md:149`）各命令退出码与跳过数 | `uv run --no-sync pytest -q`、契约脚本 |
| §6 重评记录（`docs/reports/m10-review-record-template.md:162`） | 两张评分表：**可直接把本文件 §2.2 / §2.3 的表抄进去**，或按 §2.4 重新计算后填 | 本文件 §2 |
| §7 签署（`docs/reports/m10-review-record-template.md:208`） | 姓名或代号、日期、是否同意致谢 | — |

### 3.2 提交形式

- **提交物**：一份填写完成的[验收记录模板](m10-review-record-template.md)（Markdown 文件），
  含元数据、会话记录、卡点、客户视角备忘、（如承担）源码评审记录与两张评分表。
- **回传方式**：按邀请函第六节指定的渠道交给验收发起人（邀请函发出时填写的
  收件渠道，`docs/reports/m10-invitation-final.md:146`）。**不要自行 push 到仓库**；
  如发起人要求归档，按其指定渠道提交。
- **附 commit**：记录里必须写明所验的 commit hash（邀请函成稿 §2 钉定的那一串
  完整 hash，模板 §1「commit hash」栏），
  以及每条命令是在哪个 commit 上跑的。全程只验这一个 commit，不要切换分支、不要
  拉取新提交。
- **原始材料留本机**：日志、截图、证据包、`.dexatlas/` 工作区都留在你自己的机器上；
  仓库只接收脱敏后的记录——个人路径、密钥、账号一律写 `<redacted>`
  （`docs/reports/m10-invitation-final.md:153`）。
- **别带进来**：第三方 APK、DEX、`so`、含个人路径的日志、任何密钥。

### 3.3 耗时预期

| 事项 | 预期 | 说明 |
|---|---|---|
| 首次复现（冷缓存：clone + 依赖 + 后端下载） | **10–20 分钟** | 首次需要网络；装好后分析本身可离线 |
| 暖缓存到第一份报告 | 约 1.5–2 分钟 | M8 演练另测 6.8 秒纯分析；同一环境下 30 秒的那次实测见 [M8 演练](m8-install-rehearsal.md) |
| 一个完整案例 | 1–2 分钟 | Docker 路线另加约 2 分钟 |
| 完整验收（含 40 项判定与评分） | 建议预留半天 | 时间口径见 `docs/reports/m10-reader-package.md:69` |

慢不一定是卡点：后端下载、JDK 首次安装、首次依赖安装都是一次性开销。把**每一步**
的耗时记下来，读者包要求的是分步耗时，不只是总耗时（验收项 A7）。

### 3.4 遇到问题找谁

| 情况 | 找谁 | 怎么说 |
|---|---|---|
| 不确定某条命令的**预期**是什么 | 验收发起人 | 问「文档哪一节说会输出什么」，这是澄清，不是让对方补命令 |
| 命令报错了、文档缺步骤 | 验收发起人 | 附完整命令、退出码、原始输出、你期望的依据 → 走 §3 卡点 |
| 判定有争议 | 验收发起人 | 把两种判法和各自依据都写进记录，不要口头结论了事 |
| 确认是产品缺陷 | 验收发起人 → 作者 | 缺陷由作者修复；**修复后取新 commit 并复验受影响项** |
| 只在 macOS 上、或环境实在装不上 | 验收发起人 | macOS 未验证，如实记录即可（`docs/reports/m10-reader-package.md:61`） |

**边界**：发起人可以解释名词和意图，不能替您补一条文档里没有的命令、改您的环境或
远程操作您的机器。凡是靠口头补充才走通的步骤，相关验收项判不通过
（`docs/reports/m10-acceptance-pack.md:68`）。

### 3.5 交回前自查

- [ ] 每一条命令都有退出码和关键输出；没执行的项记「未验证」，不是「通过」。
- [ ] 19 个 ★ 阻断项都有明确的三态判定（`docs/reports/m10-acceptance-pack.md:173`）。
- [ ] 两张评分表都填完，每一分都有证据；没有证据的分值记 0。
- [ ] 总分保留一位小数，没有为了「达标」四舍五入。
- [ ] 记录里的 commit hash 与邀请函成稿 §2 钉定的那一串完整 hash 相同。
- [ ] 个人路径、密钥已脱敏；没有第三方样本、日志附件。
- [ ] §7 已签署；致谢意愿已表明。

## 4. 常见问答

**Q1：环境缺失怎么办？**

不要停，把缺失本身当证据记下来。缺后端是**降级**而不是失败：分析仍以 0 退出、
报告写明该后端 `not_installed`，这正是验收项 A6 / G2 要核实的
（`docs/reports/m10-acceptance-pack.md:94`）。没有 Java 也能用 Androguard 完成基础分析
（`docs/reports/m10-reader-package.md:64`）。真装不上时在 §1 元数据里写明
jadx / apktool / androguard 各自「not installed」及原因，并把缺失造成的计数差异
（如 classes 5→4）记进证据栏。缺后端导致的测试 **skip 不是 pass**，跳过数要写进 §5.3。

**Q2：某题判不过算不算失败？**

分两种。**非阻断项**不通过：要写清影响范围、是否有替代证据、是否接受遗留
（`docs/reports/m10-acceptance-pack.md:175`），不影响 M10 的判定，但必须在扣分原因里
留下。**阻断项（★，共 19 项）**不通过：M10 直接判不通过，其他项再高的分也抵消不了
（`docs/reports/m10-acceptance-pack.md:173`）。**未验证**不算失败，但也不能算通过——
没有执行的项一律记「未验证」，不得留空当默认通过。

**Q3：复现结果与文档不一致怎么处理？**

以**实际输出**为准，把差异写成卡点（模板 §3）：完整命令、退出码、原始输出、
你期望的依据（文档哪一节哪一句）、是否可以重试、是否阻断后续。确认是自己的环境问题
才修复后重试，**两次输出都留下**。文档缺步骤本身就是缺陷，不要替项目圆场
（`docs/reports/m10-reader-package.md:44`）。特别提醒：M6 的数字以仓库落盘报告为准——
修复后三轮完整重测逐轮 15/20、16/20、18/20、合计 49/60 = 81.7%
（`docs/benchmarks/m6-level2-retest4.md:82`），另有一次更早的重测逐轮为 17/15/17
（`docs/benchmarks/m6-level2-retest3.md:85`）；两者合计都是 49/60。看到不同文档里的
逐轮数字不一致时，以[重测报告](../benchmarks/m6-level2-retest4.md)为准，并把差异记成卡点。

**Q4：验收 commit 钉定 v1.0.0 发版 commit 是什么含义？**

含义是：**本次验收只认这一个 commit**。clone 后执行 `git checkout v1.0.0`，
用 `git rev-parse HEAD` 核出的 hash 应与邀请函成稿 §2 填的那一串逐字相同；此后
不要切换分支、不要拉取新提交，所有记录写明该 hash；不要用会移动的 `main` 分支做验收
（`docs/reports/m10-invitation-final.md:54`）。这个 commit 由验收发起人钉定，邀请函里引用的
M6 数字对应的是该 commit 所在树上的落盘报告（`docs/benchmarks/m6-level2-retest4.md`）；
若 clone 后找不到该 hash 或 `git checkout v1.0.0` 取不到，先联系发起人，不要自行换用
其他提交。规则上的原因：验收针对一个
固定 commit，作者修复阻断项后必须取新 commit 并复验受影响项
（`docs/reports/m10-acceptance-pack.md:54`）。

**Q5：证据包怎么验证（verify_package）？**

导出后跑校验（命令见[读者验收包 §3.6](m10-reader-package.md)）：

```bash
uv run dexatlas export apk_80a8fe0e81204c9f -o evidence.zip
uv run --no-sync python -c \
  "from pathlib import Path; from dexatlas.reports.evidence_package import verify_package, verify_citations; p=Path('evidence.zip'); m=verify_package(p); print(verify_citations(p, m))"
```

预期：`verify_package` 通过（schema、路径穿越、SHA-256、项目/APK 绑定），
`citations_resolved` 为 `True`、`citations_unresolved` 为空
（`docs/reports/m10-reader-package.md:209`）。再把包复制到另一个目录或另一台机器复验一次
（验收项 C6），并解压对照 `manifest.json` 的 `not_included` 声明，确认包里没有 APK、
全量源码和未被证据引用的字符串（验收项 D3、G5）。

**Q6：哪些结论是作者自述，不能当验收依据？**

作者自测与作者口径的以下内容，**在你亲自复现之前一律记「未验证」**：

- M6 层级 2 的所有成绩数字（含 49/60 = 81.7% 与窄验证 3/6）——出处是脚本重算的
  benchmark 报告（`docs/benchmarks/m6-level2-retest4.md:83`），是作者测的，不是你测的；
- 层级 1 scripted 成绩——那是替身模型，只证明管线端到端可用，不是模型能力基线
  （`docs/benchmarks/m6-level1-scripted.md`）；
- 测试与覆盖率数字——以你本机 `uv run --no-sync pytest -q` 的实际结果为准
  （`docs/reports/m10-reader-package.md:337`）；
- 已知限制只剩 macOS 未验证（M8-2、M8-3 已修复并合入）；M8-4（三个后端全部失败时
  退出码仍为 0）已在 v1.0.0 由新退出码 6（`EXIT_NO_INDEX`）关闭
  （`docs/reports/m10-reader-package.md:312`）；
- 准备度评估与复评里的 75%/65% 与 77.5%/68.75%——**作者自评**，不是成绩。
  两组数字用的是同一组维度与权重：75%/65% 是[准备度评估](portfolio-readiness-2026-11-15.md)
  的基线，77.5%/68.75% 是同一基线上的自评更新。**你的重评请与 75%/65% 这一档
  对齐**，并在记录里写明依据
  （`docs/reports/m10-reader-package.md:12`）。

作者可以解释名词与意图，不能替你补命令、改环境或远程操作；靠口头补充才走通的步骤，
相关验收项判不通过（`docs/reports/m10-acceptance-pack.md:68`）。

**Q7：我可以用自己的 APK 代替 demo.apk 吗？**

可以，但验收项 A4 的计数（5 classes / 8 methods / 23 call sites / 21 call edges /
1 resource string）与 project id `apk_80a8fe0e81204c9f`是 demo-app 的预期值
（`docs/reports/m10-acceptance-pack.md:92`）。用你自己的样本时，这一条的判定标准要改为
「与你自己对样本的预期是否一致」，并在证据栏写清样本来源；demo.apk 那一组请照原样跑一遍。

**Q8：我发现了一个 bug，可以直接改吗？**

不要改仓库。按卡点（模板 §3）记录：复现命令、实际输出、预期行为、影响范围。
修复由作者完成，之后会取新 commit，你再复验受影响的项。

**Q9：作者侧的自查脚本能代替我跑吗？**

不能。[作者自查记录](m10-selfcheck.md) 覆盖的是文档、徽章、契约清单这类自动化项，
**不替代你的任何一项判定**，需人工的项仍要你亲手执行并记录
（`docs/reports/m10-reader-package.md:418`）。
注意：那份自查记录是**它自己那一次执行时的快照**（记录里写明了当时的日期与
commit），不是验收 commit 的现状；数字对不上时以你的实测为准，按 §3 记卡点。

## 5. 本工具包引用的数字与出处

所有数字均抄自仓库落盘文件，未手改；行号指向引用时所在的 commit——即本轮
v1.0.0 发版 commit（见[邀请函成稿 §2](m10-invitation-final.md)）。

| 数字 | 出处 | 说明 |
|---|---|---|
| 40 个验收项、7 组 | `docs/reports/m10-acceptance-pack.md:27` | A–G 七组 |
| 19 个 ★ 阻断项 | `docs/reports/m10-acceptance-pack.md:173` | 清单同处 |
| 0–4 分定义 | `docs/reports/m10-acceptance-pack.md:457` | §5.1 原文表 |
| GitHub 权重 30/20/10/10/25/5 | `docs/reports/m10-acceptance-pack.md:468` | §5.2 原文表 |
| Upwork 权重 20/15/15/25/15/10 | `docs/reports/m10-acceptance-pack.md:482` | §5.3 原文表 |
| 基线 GitHub 约 75% / Upwork 约 65% | `docs/reports/portfolio-readiness-2026-11-15.md:28` | 人工基线，不是接单概率 |
| 目标 90%（两平台分别） | `docs/reports/m10-acceptance-pack.md:499` | 门槛，不是预测 |
| M6 三轮合计 49/60 = 81.7% | `docs/benchmarks/m6-level2-retest4.md:38` | 脚本重算生成 |
| M6 逐轮 15/20、16/20、18/20 | `docs/benchmarks/m6-level2-retest4.md:82` | 未达每轮 ≥16/20 的轮次存在 |
| 验收线 每轮 ≥16/20、合计 ≥54/60 | `docs/benchmarks/m6-level2-retest4.md:83` | 未达 |
| 更早一轮重测逐轮 17/15/17 | `docs/benchmarks/m6-level2-retest3.md:85` | 合计同为 49/60 |
| 窄验证转通过 3/6（门槛 ≥4） | `docs/benchmarks/m6-level2-narrow-verify3.md:59` | 未达判据 |
| 窄验证确定性修复相关题 3/5 | `docs/benchmarks/m6-level2-narrow-verify3.md:60` | — |
| M10 独立验收尚未开始 | `docs/status.md:128`、`docs/reports/m10-acceptance-pack.md:3` | 如实状态 |
| 冷缓存首次 10–20 分钟 | `docs/reports/m10-reader-package.md:69` | 时间口径 |
| 验收 commit（v1.0.0 发版 commit） | `docs/reports/m10-invitation-final.md:60` | 由验收发起人钉定；完整 hash 填在邀请函成稿 §2 的占位符里 |

## 6. 这份工具包不是什么

- 不是验收结论，不是分数，也不代表任何一项验收项已通过。
- 不是 M10 的完成证明——M10 的关闭依据是读者填写并回传的记录
  （`docs/reports/m10-invitation-final.md:160`）。
- 不替代[准备包](m10-acceptance-pack.md)的 40 项判定标准；本包与准备包、读者包之间
  冲突时以准备包的判定标准为准。
- 不是安全审计或渗透测试：DexAtlas 是静态分析工具，不做动态分析、不定性恶意软件、
  不判断可利用性（`docs/reports/m10-acceptance-pack.md:41`）。
