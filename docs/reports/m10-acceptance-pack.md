# Phase 3 M10 — 独立验收准备包

> **状态：准备材料。独立验收尚未执行；M10 未完成。**
>
> 本文件是 [Phase 3 计划](../roadmap/phase3-plan.md) §9（M10）的验收准备材料，不是验收记录，
> 也不是 GitHub / Upwork 得分证据。文中的验收项当前全部为「未验证」；只有未参与实现的读者
> 按本包执行、并把结果填入[验收记录模板](m10-review-record-template.md)后，才产生可引用的
> 验收证据。
>
> 编写日期：2026-11-15 · 编写基准：`ff5c4cc`（本文件在独立分支提交）·
> 评分基线：[作品集准备度评估](portfolio-readiness-2026-11-15.md)
> （GitHub 约 75% / Upwork 约 65%，人工基线，不是接单概率）

## 0. 这份文件是什么、不是什么

**是什么**

- M10 的独立验收清单：40 个验收项，分 7 组，每项有判定标准、阻断标记、三态和证据栏。
- 首次读者操作指引：从 clone 到完成一个完整案例的最短路径，不依赖作者补充步骤。
- 客户视角审阅指引：如何判断「输入与结论是否清楚」「引用能否核查」「事实与线索能否区分」。
- 重评模板：沿用[准备度评估](portfolio-readiness-2026-11-15.md)的原维度与原权重，
  含 0–4 分定义和空白评分表。
- M5–M9 源码评审清单：每个里程碑的证据入口和核对动作。

**不是什么**

- **不是独立验收。** 目前没有外部读者参与，没有任何一项被判定为「通过」。
- **不是分数。** 不预填重评分值；不把计划目标（各平台 ≥90%）当成成绩。
- **不是真实模型批次。** M6 层级 2 尚未授权、尚未执行；scripted 结果不能替代模型能力。
- **不是安全审计或渗透测试。** 不覆盖 native / 动态分析、恶意软件定性、加固还原。
- **不替代原始证据。** 与[公共契约表](../architecture/public-contracts.md)、
  [服务回归集](../benchmarks/service-regression-set.md)、
  [M8 安装演练](m8-install-rehearsal.md)等冲突时，以原始证据和代码为准。

**硬规则**

1. 作者自测必须标注「自测」，不能代替独立验收。
2. 任何判定都要有命令、退出码、关键输出、耗时和路径；没有记录的一律记「未验证」。
3. 阻断项（表中标 ★）只要有一项「不通过」，M10 即不通过；其他项的高分不能抵消。
4. 验收针对一个固定 commit；作者修复阻断项后，必须取新 commit 并复验受影响项。
5. 第三方 APK、DEX、`so`、秘密、含个人路径的日志不入仓库；记录中的个人信息要脱敏。

## 1. 角色、独立性与产出

| 角色 | 做什么 | 独立性要求 | 产出 |
|---|---|---|---|
| 首次读者 | 按 §3 从 clone 到完成一个案例 | 未参与实现；作者不补步骤、不远程操作其机器 | 环境、耗时、逐条命令与输出、卡点 |
| 客户视角审阅者 | 按 §4 审阅案例、HTML、证据包 | 无需安装 DexAtlas；可以是首次读者本人 | 三问结论 + 红旗清单 + 备忘 |
| 源码评审者 | 按 §6 核对 M5–M9 证据与代码 | 必须具备阅读 Python、测试和契约的能力；可兼任前两项之一 | 里程碑结论、遗留项、阻断项 |
| 作者 | 准备材料、解释意图、修复缺陷 | 不填写「通过/不通过」；自测必须标注 | 修复 commit、复验范围 |

**作者可以做什么、不可以做什么**

- 可以：回答「这个词是什么意思」「这条命令的预期是什么」这类澄清问题。
- 不可以：替读者补一条文档里没有的命令，或直接登录读者机器代为操作。
- 文档里缺步骤，本身就是一项文档缺陷：读者应记录为卡点并按 §3.7 上报，
  作者修复后再复验；不能把口头补充当作通过。

**记录放在哪里**

每个角色填写一份[验收记录模板](m10-review-record-template.md)。模板可以复制多份；
原始日志、截图和证据包留在验收人自己的机器上，仓库只接收脱敏后的记录。
验收完成后，由验收发起人把记录状态汇总回本文件的 §8。

## 2. 验收项（40 项）

状态图例：`☐ 通过` / `☐ 不通过` / `☐ 未验证`。**本文件不预勾选任何状态。**
「证据记录」栏至少写：命令、退出码、关键输出、耗时、文件或路径。
标 ★ 的项是阻断项；19 个阻断项的清单见 §2.8。

### 2.1 A — 推荐安装路线与首次运行（7 项）

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| A1 | 取得固定副本：从验收发起人指定的 commit 取得干净副本，`git status` 干净；记录 commit hash、来源 URL、日期。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；commit：；日期： |
| A2 | 依赖安装：按 §3.2 或 §3.3 的推荐路线安装完成，退出码 0；记录 OS、Python、uv、JDK、extras、耗时；不得有未解释的编译/下载失败。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码：；耗时：；版本： |
| A3 | 后端检查：`uv run dexatlas backends` 的输出与机器实际安装一致；缺失后端要写明缺失原因，不得把缺失记成通过。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；输出： |
| A4 | 首次分析：`examples/demo-app/demo.apk` 分析退出码 0；project id 为 `apk_80a8fe0e81204c9f`；计数为 5 classes / 8 methods / 23 call sites / 21 call edges / 1 resource string。若不同，先核对后端配置，再判定。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码：；计数：；耗时： |
| A5 | 三格式报告：同一次分析用 `-o report.md --json report.json --html report.html` 生成三份非空文件，且描述同一 project。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 文件大小：；project id： |
| A6 | 后端缺失降级：Androguard 可用、至少一个外部后端不可用时，分析仍以 0 退出并产出报告；错误记录写明哪个后端 `not_installed`；不得崩溃或静默省略。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码：；错误记录： |
| A7 | 耗时与卡点：记录从 clone 到第一份报告的总耗时、各阶段耗时、所有卡点原文；卡点按 §3.7 格式提交。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 总耗时：；卡点数： |

### 2.2 B — 完整案例（6 项）

案例入口：[demo-app-walkthrough](../case-studies/demo-app-walkthrough.md)。
判定时只使用该文档公开的命令；需要作者补充步骤即记 B1 不通过。

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| B1 | 按案例从 analyze 走到 xrefs 全程完成，不需要作者补命令；每一步退出码与案例预期一致。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 步骤数：；卡点： |
| B2 | manifest：包名 `com.example.demo`、版本 1.0 (1)、min 24 / target 34、1 个权限、3 个组件、两个 exported 组件无权限保护，均可从输出复述。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；输出： |
| B3 | search：`Crypto` 命中相关类/方法；`sk_live` 命中字符串 `sk_live_2f8a91c4e7b3`；读者能说出命中来自哪个索引。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；命中： |
| B4 | source：输出标注来源（java 或 smali）、后端与 locator；读者能顺着 locator 找到对应文件。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；locator： |
| B5 | xrefs：区分 call site 与 call edge；本例为 1 call site、1 call edge、`classes.dex@34`；读者能解释两个计数为何不同。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；输出： |
| B6 | 结论与限制：读者能复述案例的结论、限制和下一步，并指出哪些是事实、哪些是推断、哪些没有覆盖。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 复述要点： |

### 2.3 C — 证据核查（6 项）

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| C1 | 任选 3 条 evidence 记录，逐条写出工具、版本、locator 和 level；字段不得为空或臆造。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 记录编号：；字段： |
| C2 | locator 解析：文件级 locator 在分析工作区内解析到真实文件；DEX 成员 locator 与裸树 locator（如 `jadx:sources`）按构造解析（`path=None` 是设计，不是失败）；无法解析的 locator 要单独列出。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | locator：；解析结果： |
| C3 | 三级语义：`verified` 必须是确定性工具产出且 citation 可解析；模型文本不得为 `verified`；`lead` 是线索不是结论；`insufficient` 表示证据不足。读者能各举一例。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 例子： |
| C4 | 计数一致：报告中的计数与证据记录/索引一致，没有无法追溯来源的数字；抽查 2 个计数复算。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 抽查：；复算： |
| C5 | 证据包结构：`verify_package` 通过（schema、路径穿越、SHA-256、项目/APK 绑定）；失败时记录异常原文。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；结果： |
| C6 | 引用迁移：`verify_citations` 返回 `citations_resolved=true`；把包复制到另一个目录后复验仍通过；包内路径不指向生成它的机器。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；复制路径：；结果： |

### 2.4 D — 离线阅读（5 项）

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| D1 | HTML 离线：断网或复制到另一台机器后直接打开 `report.html`；页面可读，无 `<script>`、无外部 CSS/JS/字体请求、无网络依赖。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 打开方式：；网络请求： |
| D2 | 三格式一致：同一分析的 Markdown / JSON / HTML 中，计数与关键结论一致；抽查 3 个数字。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 抽查：；三处值： |
| D3 | 包内声明：`manifest.json` 的 `not_included` 明示不含 APK、全量源码、未被证据引用的字符串；实际包内容与该声明一致。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 声明：；实际内容： |
| D4 | 包内引用：若证据含 file-level `jadx:sources/...` locator，包内对应片段位于同名相对路径，读者不安装 DexAtlas 也能按路径打开；若只有裸树/DEX locator，包内不出现 `sources/`，读者能说明这是按构造解析而非缺失。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | locator 类型：；包内路径： |
| D5 | 文本转义：样本中的字符串/类名不能写入 HTML 结构（无未转义标签、无事件属性）；异常文本只作为文本显示。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 样本：；页面表现： |

### 2.5 E — 服务回归集结果解释（5 项）

证据入口：[服务回归集](../benchmarks/service-regression-set.md)、
[M6 层级 1 演练](../benchmarks/m6-level1-scripted.md)。

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| E1 | 范围：能说出冻结集是 20 题、覆盖权限/组件、指定方法、调用关系、资源出处、无法回答/后端缺失五类，并明确「只代表这 20 题，不外推到任意 APK」。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 复述： |
| E2 | 层级：能区分层级 0（确定性判分，20/20）、层级 1（scripted 管线演练）、层级 2（真实模型，尚未授权/执行）各自证明什么、不证明什么。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 复述： |
| E3 | 不冒充模型能力：不把 scripted 的 4/20、1/20 等数字当作模型通过率或能力结论；引用时保留 scripted 免责声明。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 引用原文： |
| E4 | 失败解释：能解释层级 1 的「预算耗尽」是替身脚本步数耗尽，不是真实超时/扣费；能解释 DexAtlas 配置的判错来自断言形态。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 解释： |
| E5 | 完整集同报：同时看到完整 92 题与冻结 20 题的结果，不只报成功子集；改动冻结集有版本化记录。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 报告位置： |

### 2.6 F — 公共契约核对（6 项）

契约入口：[公共契约表](../architecture/public-contracts.md)。

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| F1 | CLI 退出码：0 成功、1 空答案、2 请求错误、3 分析失败、4 重载歧义、5 截断；至少实测 0/1/2 各一次，并核对文档语义。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码： |
| F2 | REST：关键端点（上传/项目/运行/符号/源码/报告）的响应形状与状态码与契约表一致；抽查 3 个端点。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 端点：；响应： |
| F3 | MCP：工具清单为契约表的 10 个，全部只读注解；抽查 2 个工具的返回形状。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 工具：；注解： |
| F4 | 报告 schema：JSON 报告 `schema_version` 与顶层字段（10 个）与契约表一致；兼容别名不混用。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | schema：；字段： |
| F5 | 契约快照测试：`tests/test_public_contracts.py` 全部通过；失败项要记录，不得跳过。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；通过/失败： |
| F6 | 契约实测脚本：`scripts/verify-public-contracts.py` 退出码 0，逐项 PASS；失败项记录原文。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码： |

### 2.7 G — 故障恢复与数据边界（5 项）

| ID | 验收项与判定标准 | 阻断 | 状态 | 证据记录 |
|---|---|:---:|---|---|
| G1 | 坏输入：非 ZIP 文件当 APK 分析，退出码 2，错误信息可理解，workspace 不留下半成品项目。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码：；workspace： |
| G2 | 后端缺失：清空后端环境变量后分析继续，错误记录 `not_installed`，报告照常产出；不得把失败当异常抛出。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码：；errors： |
| G3 | 超时：设置极短超时后三后端记录 `timeout`，报告仍产出；同时核对 M8-4 的退出码缺口（全部后端失败仍为 0），记录是否接受及其边界。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 命令：；退出码：；M8-4 结论： |
| G4 | 幂等：同一 APK 连续分析两次，project id 相同，`projects` 只有一条，计数一致。 |  | ☐ 通过　☐ 不通过　☐ 未验证 | 两次 id：；项目数： |
| G5 | 数据隔离：证据包不含 APK、全量源码、未引用字符串；记录 SHA-256 绑定但没有把 APK 打进包。 | ★ | ☐ 通过　☐ 不通过　☐ 未验证 | 包内容：；not_included： |

### 2.8 判定规则与阻断项

- **通过**：有可复现命令、输出与文件，判定标准全部满足。
- **不通过**：任一条判定标准不满足，或结果无法复现。
- **未验证**：没有执行、没有记录，或证据不足以判断。三者之外没有「大概可以」。
- **阻断项（★）共 19 项**：A2、A4、A6、B1、C1、C2、C3、C5、C6、D1、D2、D3、E2、E3、F1、F5、G2、G3、G5。
- 任一项 ★ 不通过，M10 不通过；分数通过不能抵消阻断缺陷。
- 非阻断项不通过时，必须写清影响范围、是否有替代证据、是否接受遗留。

## 3. 首次读者操作指引（交给外部读者）

本节可以原样交给读者。它不假设读者读过项目其他文档，也不依赖作者补充步骤。
如果某一步在本节找不到，按 §3.7 记录为卡点；作者的补充不算文档已具备该步骤。

### 3.1 先确认环境

| 项目 | 要求 | 说明 |
|---|---|---|
| 操作系统 | Windows 11 或 Linux | 两者有实测记录；macOS 未验证，读者使用 macOS 时如实记录 |
| Python | 3.12 或 3.13 | CI 在两个版本上都跑 |
| uv | 最新版 | 包与虚拟环境管理 |
| JDK | 21+ | 只有 JADX / Apktool 后端需要；没有 Java 也能用 Androguard 完成基础分析 |
| Docker | 可选 | 不想装 Python/JDK 时走 Docker 路线；镜像自带 JADX 与 Apktool |
| 网络 | 首次需要 | clone、uv 依赖、后端下载；装好后分析本身可离线 |
| 磁盘 | 预留数 GB | 记录实际占用；不要写到系统盘根目录 |
| 时间 | 首次 10–20 分钟 | 含下载；暖缓存到第一份报告约 30 秒（M8 实测，见 [M8 演练](m8-install-rehearsal.md)） |

**固定版本。** 验收针对验收发起人指定的 commit。不要用移动的 `main` 分支做验收；
所有记录都写清 commit hash。

### 3.2 路线 A：uv（推荐，可完成 CLI、案例、测试和契约检查）

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
git checkout <验收发起人指定的 commit>
uv sync --extra dev --extra analysis --extra mcp --extra demo
uv run dexatlas backends
```

预期：`uv sync` 退出码 0；`backends` 打印一张表，每个后端是 `available` 或
`not installed`。`analysis` 提供 Androguard（进程内 DEX 解析）；JDK 21 加
JADX / Apktool 才提供 Java 源码和 Smali 回退。

> **已知文档不一致（M8-3）：** [install.md](../install.md) 的安装节写的是
> `uv venv` + `uv pip install -e ".[analysis]"`，这是最小安装，不含 `mcp` 和
> `demo` extras。验收推荐上面的四 extras `uv sync`；无论用哪条，记录实际命令。

如果后端不在 `PATH`，按 [install.md](../install.md) 设置：

```bash
export DEXATLAS_JADX_PATH=/path/to/jadx/bin/jadx
export DEXATLAS_APKTOOL_JAR=/path/to/apktool.jar
```

Windows 下 `DEXATLAS_JADX_PATH` 指向 `bin\jadx.bat`。没有后端时不要停：
继续做 A6，确认分析仍完成、报告写明哪些步骤没运行。

### 3.3 路线 B：Docker（隔离环境，自带后端）

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
git checkout <验收发起人指定的 commit>
docker build -t dexatlas .
docker run --rm dexatlas dexatlas backends
```

一次容器内完成分析、三格式报告与证据包导出：

```bash
mkdir -p out
docker run --rm \
  -v "$PWD/examples/demo-app:/in:ro" \
  -v "$PWD/out:/out" \
  dexatlas sh -c 'dexatlas analyze /in/demo.apk -o /out/report.md --json /out/report.json --html /out/report.html && dexatlas export apk_80a8fe0e81204c9f -o /out/evidence.zip'
```

预期：构建约 2 分钟（M8 实测 2 分 16 秒）；镜像内 JADX / Apktool 可用；
分析加导出约 10 秒；`out/` 下出现四份文件。

> **已知限制（M8-2）：** 容器内多个命令共享 workspace 时，查询类命令没有
> `--workspace` 选项；用 `DEXATLAS_WORKSPACE=/workspace/ws` 统一。遇到此问题
> 记录为卡点，不要改用作者未公开的步骤。

Docker 路线下校验证据包：

```bash
docker run --rm -v "$PWD/out:/out" dexatlas python -c \
  "from pathlib import Path; from dexatlas.reports.evidence_package import verify_package, verify_citations; p=Path('/out/evidence.zip'); m=verify_package(p); print(verify_citations(p, m))"
```

### 3.4 完整案例最短路径（路线 A，约 1–2 分钟）

以下命令全部来自 [demo-app 案例](../case-studies/demo-app-walkthrough.md)，
按顺序执行即可。不要先读源码；先以读者身份看输出是否自解释。

```bash
uv run dexatlas analyze examples/demo-app/demo.apk
uv run dexatlas manifest apk_80a8fe0e81204c9f
uv run dexatlas search apk_80a8fe0e81204c9f "Crypto"
uv run dexatlas search apk_80a8fe0e81204c9f "sk_live"
uv run dexatlas source apk_80a8fe0e81204c9f com.example.demo.MainActivity
uv run dexatlas xrefs apk_80a8fe0e81204c9f \
  "com.example.demo.MainActivity.describe(Ljava/lang/String;)Ljava/lang/String;"
```

预期输出（读者记录实际值；若计数不同，先核对后端是否齐全）：

| 步骤 | 预期 |
|---|---|
| analyze | `apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string` |
| manifest | `com.example.demo`；version 1.0 (1)；sdk min 24 / target 34；permissions 1；components 3；MainActivity 与 SyncService 均为 exported 且无权限保护 |
| search `Crypto` | 命中 `com.example.demo.Crypto` 相关类与方法 |
| search `sk_live` | 一条字符串命中 `sk_live_2f8a91c4e7b3`，并显示它来自字符串索引 |
| source | 第一行标明 `source kind: java`（或 smali 回退）与 locator，例如 `jadx:sources/com/example/demo/MainActivity.java` |
| xrefs | `1 call site(s), 1 call edge(s)`，调用点为 `classes.dex@34` |

然后生成三格式报告和证据包：

```bash
uv run dexatlas analyze examples/demo-app/demo.apk \
  -o report.md --json report.json --html report.html
uv run dexatlas export apk_80a8fe0e81204c9f -o evidence.zip
```

校验证据包（不安装额外工具）：

```bash
uv run --no-sync python -c \
  "from pathlib import Path; from dexatlas.reports.evidence_package import verify_package, verify_citations; p=Path('evidence.zip'); m=verify_package(p); print(verify_citations(p, m))"
```

预期：`citations_resolved` 为 `True`，`citations_unresolved` 为空；
`manifest.json` 的 `not_included` 明示 APK、全量源码、未被证据引用的字符串不在包内。

### 3.5 离线阅读（不安装 DexAtlas 的读者）

1. 把 `report.html` 复制到另一个目录，断网后双击打开；页面应完整可读。
2. 把 `evidence.zip` 解压到一个新目录（任意 Python 3，或系统解压工具）：

   ```bash
   python -m zipfile -e evidence.zip evidence
   ```

3. 打开 `evidence/reports/report.html`，再打开 `evidence/manifest.json`；
   对照 `not_included` 检查包内实际文件。
4. 打开 `evidence/reports/report.json`，看 evidence 记录的 locator 类型：
   - 若是 file-level `jadx:sources/...`，在 `evidence/` 下按同名相对路径找到源码片段；
   - 若只有 DEX 成员 locator 或裸树 `jadx:sources`（demo 示例包就是这种），
     包内没有 `sources/` 是正确的——它们按构造解析，`verify_citations` 会说明。
     读者应能说出这两种情况的区别，而不是把「没有 sources/」当成包损坏。
5. 用 `sha256sum`（Linux）或 `certutil -hashfile <file> SHA256`（Windows）
   抽查 manifest 中至少两个文件的哈希。

### 3.6 时间预期

| 阶段 | 预期 | 备注 |
|---|---|---|
| clone + `uv sync` | 15 秒–2 分钟 | 冷缓存与网络差异大；M8 冷缓存实测 15 秒 |
| 后端安装/配置 | 0–10 分钟 | 已有二进制时接近 0；下载 JADX/Apktool 时更长 |
| 首次分析 demo.apk | 5–10 秒 | M8 实测 6.8 秒；本包编写时复测 8.0 秒 |
| 完整案例（§3.4） | 1–2 分钟 | 含重复分析与检索 |
| Docker 构建 + 分析 | 约 3 分钟 | 构建 2 分 16 秒 + 分析约 10 秒 |
| 证据包校验 | < 1 分钟 | 小样本 |

这些是参考值，不是验收标准；读者记录自己的实际耗时。若明显超出，
记录环境与卡点，不修改预期来迁就结果。

### 3.7 卡点上报格式

每个卡点一条，原文粘贴，不要转述：

```text
卡点编号：
发生步骤（§3.x / 验收项 ID）：
环境（OS / Python / uv / JDK / Docker / commit）：
执行的命令：
退出码：
实际输出（完整原文，脱敏后）：
预期（引用文档哪一节、哪一句）：
是否可以重试：
是否阻断后续步骤：
附件路径（日志/截图，不入仓库）：
```

要求：不贴秘密、不贴第三方 APK、不贴含个人路径的完整日志；用 `<redacted>` 替换。
一个卡点只描述一个现象；不要把多个失败合并成一条。

### 3.8 读者完成标准

- §3.2 或 §3.3 至少一条路线走通，A1–A7 有记录。
- §3.4 的完整案例走完，B1–B6 有记录。
- §3.5 的离线阅读完成，D1–D4 有记录。
- 所有卡点按 §3.7 提交；作者修复后，读者只复验受影响项，不复验全部。

## 4. 客户视角审阅指引

审阅者不需要安装 DexAtlas，也不需要读 Python。只需要愿意抽查引用，并对
「这句话有没有证据」保持怀疑。建议先读[案例索引](../case-studies/README.md)，
再选一个案例逐条核对。

### 4.1 三个问题

**问题一：输入与结论是否清楚？**

- 案例是否写明：分析的样本是什么、问题是什么、范围到哪里、哪些不在范围内？
- 结论是否区分「工具读到的事实」和「作者的判断」？
- 读者能否用一句话复述「这个案例回答了什么、没有回答什么」？
- 通过信号：结论前有样本与范围；结论后有边界；「下一步」不是结论的替代品。
- 不通过信号：读完不知道样本是什么；结论里混入未验证的推断；把「没有发现」
  写成「不存在」。

**问题二：引用能否核查？**

- 任选 3 条结论，逐条找到它引用的 evidence 记录或 locator。
- 打开证据包，按 locator 的相对路径找到源码片段或报告位置；不安装 DexAtlas。
- 检查哈希：`manifest.json` 中的 SHA-256 与包内文件一致。
- 通过信号：3 条都能在 5 分钟内定位；locator 指向真实文件或按构造解析。
- 不通过信号：引用指向包外、指向不存在的路径、只有「见源码」而没有位置。

**问题三：事实与线索能否区分？**

- `verified`：确定性工具产出，citation 能在分析内解析。
- `lead`：模型或启发式给出的怀疑指示，不是确认。
- `insufficient`：证据不足，需人工复核。
- 硬边界：模型生成的文本永远不能是 `verified`；`BEHAVIOUR` 类记录永远不能是
  `verified`；报告里 `lead 0` 只表示「分析没有在这一级落结论」，不表示样本安全。
- 通过信号：读者能各举一个 `verified` / `lead` / `insufficient` 的例子，并说出
  为什么。
- 不通过信号：把 `lead` 读成「已确认」；把 `lead 0` 读成「无风险」；把模型回答
  当成事实记录。

### 4.2 三个案例怎么读

| 案例 | 输入 | 重点核查 | 明确边界 |
|---|---|---|---|
| [从上传到证据链](../case-studies/demo-app-walkthrough.md) | `examples/demo-app/demo.apk` | 全链路：manifest、检索、源码、交叉引用、11 条 evidence 逐条可定位 | 样本是一方样本；结论只描述字节中的事实 |
| [阅读混淆应用](../case-studies/obfuscated-app.md) | `examples/obfuscated-app/obfuscated.apk`，附 multidex 附录 | 名称混淆后仍能读到什么；字符串索引与资源出处；多 DEX 的类定义 | 不做去混淆承诺、不还原加固、不判断恶意 |
| [从 Python 集成](../case-studies/api-integration.md) | `examples/demo-app/demo.apk`，REST 与 MCP | 上传→分析→轮询→查询→报告的线上契约；错误形状；只读 MCP | 本地单机、无认证；不是多租户 SaaS |

### 4.3 红旗清单

出现任一条，审阅结论至少记「需澄清」；涉及阻断项的记「不通过」：

1. 结论没有 evidence 记录或 locator，或 locator 指向包外/不存在的位置。
2. 把 `lead` 写成 finding，或把「没有发现」写成「不存在/安全」。
3. 数字没有生成脚本或 trace 来源；Markdown / JSON / HTML 三处不一致。
4. 只报成功子集，不报完整 92 题；失败和预算耗尽被隐去。
5. 把 scripted 结果写成模型能力或模型通过率。
6. 安装/案例步骤依赖作者口头补充，文档本身走不通。
7. 证据包含 APK、全量源码或未被证据引用的字符串。
8. REST API 无认证却绑定 `0.0.0.0` 或对外网开放。
9. 声称「完整」但未说明后端缺失时哪些步骤没运行。
10. 服务说明缺少输入、交付、验收、排除项、数据处理的任一项。

### 4.4 审阅备忘格式

```text
审阅人背景（是否参与实现）：
审阅日期与 commit：
审阅对象（案例 / HTML / 证据包路径）：

问题一：输入与结论是否清楚？  结论：清楚 / 需澄清 / 不成立
  例子：
  理由：
问题二：引用能否核查？        结论：可核查 / 部分可核查 / 不可核查
  抽查的 3 条结论与定位结果：
问题三：事实与线索能否区分？  结论：能 / 部分能 / 不能
  例子：
红旗清单命中项（编号 + 原文）：
阻断项判定（通过 / 不通过 / 未验证）：
建议修复项（按影响排序）：
不能接受但可记录的限制：
```

## 5. 重评模板（原维度、原权重）

重评必须沿用[准备度评估](portfolio-readiness-2026-11-15.md)的六个维度与两组权重。
不因本轮完成了什么而改权重；改了权重，分数就与 75% / 65% 的基线不可比。

### 5.1 评分等级（0–4）

| 分值 | 定义 |
|---:|---|
| 0 | 未见证据 |
| 1 | 初步证据 |
| 2 | 局部可用，仍有实质缺口 |
| 3 | 在声明环境内有完整演示或复现记录 |
| 4 | 在该维度的限定范围内经过评审并有边界验证 |

4 分不表示软件无缺陷。每一分都要在「证据」栏写出文件、命令或验收项编号；
没有证据的分值记 0。

### 5.2 GitHub 空白评分表

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

### 5.3 Upwork 空白评分表

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

### 5.4 计算与判定

- 每项贡献 = 分值 ÷ 4 × 该平台权重；六项求和即该平台总分。
- 两个平台**分别**达到至少 90% 才算达到 M10 的评分目标；两平台平均分不能替代。
- 基线是 GitHub 约 75%、Upwork 约 65%；目标 90% 是门槛，不是预测。
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

## 6. 源码评审清单（M5–M9）

源码评审不是「读一遍觉得没问题」。每个里程碑都要落到可执行的核对动作上；
没有执行的动作记「未验证」。评审者必须具备阅读 Python、测试和契约的能力。

### 6.1 里程碑证据入口

| 里程碑 | 证据入口 | 评审者要核对什么 | 结论 | 遗留 |
|---|---|---|---|---|
| M5 基线校准 | [phase3-baseline](phase3-baseline.md)、[claim-mismatches](claim-mismatches.md)、三份 benchmark 报告 | 声明是否有证据；指标能否从 trace 重算；报告能否逐字再生 | ☐ 通过　☐ 不通过　☐ 未验证 |  |
| M6 有限 Agent | [service-regression-set](../benchmarks/service-regression-set.md)、[m6-level1-scripted](../benchmarks/m6-level1-scripted.md)、`benchmarks/model.py`、`benchmarks/m6_service_set.py` | 冻结题是否先于调优；层级 0/1/2 的证据地位；完整 92 题是否同报 | ☐ 通过　☐ 不通过　☐ 未验证 |  |
| M7 交付包 | [案例索引](../case-studies/README.md)、三个案例、[report-rendering](../architecture/report-rendering.md)、`tests/test_html_report.py`、`tests/test_evidence_package.py` | 案例是否客户可读；HTML 是否自包含；证据包是否可迁移、是否隔离数据 | ☐ 通过　☐ 不通过　☐ 未验证 |  |
| M8 安装与契约 | [m8-install-rehearsal](m8-install-rehearsal.md)、[public-contracts](../architecture/public-contracts.md)、`tests/test_public_contracts.py`、`scripts/verify-public-contracts.py` | 安装链是否可走通；故障是否记录为值；契约是否与真实接口一致；M8-1 修复是否有红→绿证据 | ☐ 通过　☐ 不通过　☐ 未验证 |  |
| M9 对外素材 | [README](../../README.md)、[README.zh-CN](../../README.zh-CN.md)、[portfolio](../portfolio.md)、[outreach](../outreach/project-brief.md) | 首次访客能否复述用途与边界；个人贡献是否说清；Upwork 素材是否满足发布约束 | ☐ 通过　☐ 不通过　☐ 未验证 |  |

### 6.2 逐里程碑核对动作

**M5 — 基线校准**

```bash
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-traces.json --metrics
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-real-traces.json --metrics
uv run --no-sync python benchmarks/comparison/run.py \
  --input docs/benchmarks/comparison-stronger-traces.json --metrics
```

- 三份指标与各自报告逐格一致；逐配置的 `max_tokens` 与报告披露一致。
- 报告再生：前两份用 `--report`；stronger 必须带
  `--compare-to docs/benchmarks/comparison-real-traces.json`，否则会缺对比段。
- 再生结果与仓库内 `.md` 逐字节一致；不一致就记不通过，不要手改报告。
- 检查 `claim-mismatches.md` 的未闭合条目；仍为真的「改行为」项属于阻断候选。

**M6 — 服务回归集**

- 确认冻结集是 20 题、五类覆盖、冻结基线 `100b191`，且在任何调优之前。
- 层级 0 命令见服务回归集附录 A；完整执行应 20/20。后端缺失导致的失败先修环境，
  不得把跳过记成通过。
- 层级 1：核对 20 题 A 4/20、B 4/20、DexAtlas 1/20；完整 92 题 A 15/92、B 15/92、
  DexAtlas 5/92；trace 与报告一致。
- 层级 2 未授权、未执行。评审结论不得写成「真实模型已验证」。
- 判分口径以 `benchmarks/model.py` 的 `check()` 为准；文档与代码冲突时以代码为准。

**M7 — 案例、HTML、证据包**

- 三个案例都具备：问题、范围、可复现命令、逐条证据、结论、限制、下一步。
- `--html` 生成单文件；无 `<script>`、无外部资源；样本文本被转义。
- `dexatlas export` 后：`verify_package` 通过 schema、路径、哈希、绑定检查；
  `verify_citations` 通过；包搬到另一目录后仍通过。
- 包内不含 APK、全量源码、未被证据引用的字符串；`not_included` 与实际一致。
- 相关测试必须真实覆盖管线写出的记录，而不是只构造理想 evidence 记录；
  M8-1 的回归测试就是反例教训。

**M8 — 安装、故障恢复、契约**

- 复核 [M8 演练](m8-install-rehearsal.md)的平台矩阵：Windows 实测、Linux CI 全绿、
  macOS 未验证；不得把 CI 的 Linux 结果外推为 macOS。
- 六个故障场景逐项核对退出码与记录：坏输入 2、后端缺失继续、超时继续、
  截断 5、重复分析幂等、证据隔离。
- M8-1（`verify_citations` 裸树 locator）已修复：核对回归测试在旧实现上会红；
  只看到「测试通过」不算。
- M8-2 / M8-3 / M8-4 仍未关闭，按 §7 决定「阻断」还是「有边界接受」。
- 契约核对：`pytest -q tests/test_public_contracts.py` 全过；
  `python scripts/verify-public-contracts.py` 退出码 0；逐项 PASS。

**M9 — 对外素材**

- 以首次访客身份读 README 首屏：能否在 30 秒内说出用途、真实输出、演示入口、
  案例入口、安装入口、个人贡献与限制。
- 双语 README 的事实一致；不出现未构建功能的「已交付」表述。
- Upwork 素材：个人项目身份、联系方式、字符限制、服务范围、验收、排除项、
  数据处理、模型费用归属；不得替用户发布或联系客户。
- 对外文稿中的测试数/覆盖率以 `scripts/refresh-report-figures.py` 与指纹为准；
  发现手写数字或与快照不一致，记文档缺陷，不手改数字。

### 6.3 最终质量门禁

在最终 commit 上按顺序执行；后端配置是分开的配置，不是一次运行：

```bash
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
uv run --no-sync vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80
uv run --no-sync pytest -q
uv run --no-sync python scripts/check-doc-citations.py
uv run --no-sync python scripts/check-version-claims.py --base auto
```

- **跳过不是通过。** 读 summary 的 skip 数；后端缺失导致的 skip 要单独说明。
- 有源码变更时，先 `ruff format`，再 `remap-citations.py`，再 citation checker。
- 报告数字必须与最终树一致：先改代码、格式化，再测量；指纹不匹配就是红。
- `refresh-report-figures.py` 只在测量完整（全部测试运行、无 skip）时写数字；
  部分运行保留旧覆盖率和旧套件数，等于描述一棵不存在的树。
- 三种后端配置（全后端 / 无外部后端 / 仅 Apktool）都要有结果或明确记录未跑。

**编写本包时的门禁现状（2026-11-15，基准 `ff5c4cc`）**

- `ruff check .` 与 `ruff format --check .`：通过。
- `scripts/check-doc-citations.py`：通过（226 条引用，0 漂移）。
- `tests/test_docs.py::test_all_relative_links_resolve` 与
  `tests/test_doc_citations.py`：通过（16 项）。
- `scripts/check-version-claims.py --base auto`：**失败**，3 项既有声明与仓库
  事实不符（README 徽章、v0.2.0 发布说明覆盖率、CHANGELOG 引用）。
- `tests/test_docs.py` 全量：**5 项失败**，全部是 `phase1-execution-report.md`
  的测试数/文件表/指纹与当前树不一致；不涉及本包新增文件。
- 这些失败是既有文档数字未随源码树更新，不是本包引入。按项目规则不得手改数字；
  最终 commit 上必须完整重测量后复跑至全绿。详见 §7。



### 6.4 最终 commit 与发布候选

- 验收针对一个固定 commit；评审记录写 commit hash 与日期。
- CI 七个并行运行全绿；Docker 镜像可构建；依赖审计通过。
- 发布说明列出：交付文件、使用说明、兼容/破坏性变更、已知限制、不支持的
  native / dynamic 能力；`v1.0.0` 的稳定承诺只覆盖契约表明确列入的范围。
- 实验性 Agent 行为另行标注；不得把默认预算下的有限能力写成通用自主分析。
- 完成源码评审和验收后才准备 tag；提交、推送和发布状态按实际记录书写。
- **本包编写时没有 tag、没有发布候选、没有验收结论。**

## 7. 已知遗留问题（进入验收前必须处理或明确接受）

来源：[M8 安装演练](m8-install-rehearsal.md) §6、Phase 3 计划 §9。
下表不是「已接受」清单；每一项都要由验收发起人在记录中写明处理方式。

| ID | 问题 | 影响 | 验收处理 | 状态 |
|---|---|---|---|---|
| M8-1 | `verify_citations` 把覆盖率观察的裸树 locator 判为未解析 | M7 的「包搬走后引用仍可解析」对真实分析不成立 | 已修复并带红→绿回归测试；复验 C6 | 已修复，待复验 |
| M8-2 | 容器内查询命令缺 `--workspace`，只能靠 `DEXATLAS_WORKSPACE` | 首次 Docker 用户必踩；两条路径不一致 | 修 CLI 或在 install.md 明示；验收记录是否阻断 | 未关闭 |
| M8-3 | install.md 的安装命令与推荐四 extras 不一致 | 按 install.md 装会缺 MCP/demo 依赖 | 增补推荐组合与各 extra 用途；验收记录实际路线 | 未关闭 |
| M8-4 | 三后端全部超时后 run 仍 completed、退出码 0 | 只看退出码会把空索引运行误判为成功；涉及公共契约 | 明确接受边界，或修退出码并版本化契约；G3 记录 | 未关闭（重要） |
| — | macOS 未验证 | 平台矩阵不完整 | 如读者使用 macOS，单独记录；不得外推 | 未验证 |
| — | M6 层级 2（真实模型批次）未授权/未执行 | 不能声称真实模型在冻结集上的通过率 | 保持未验证；scripted 不得替代 | 未执行 |
| — | 独立验收尚未执行 | M10 未完成 | 本包就是为此准备；执行后回填 §8 | 未执行 |
| — | `install.md` 写「No APK is committed」，但 `examples/` 有一方 APK | 首次读者可能误以为必须 fetch fixtures | 记录为文档措辞问题；完整案例直接用 `examples/`；不阻断 | 文档缺陷（低） |
| — | 文档门禁在编写时未全绿：`check-version-claims.py` 3 项、`tests/test_docs.py` 5 项失败 | 既有报告数字/指纹/测试文件表与当前树不一致；不能据此发布 | 最终 commit 上完整重测量后复跑；不得手改数字，不得用部分测量刷新 | 未关闭（阻断文档门禁） |

## 8. M10 退出门槛对照（当前全部未验证）

| Phase 3 计划 §9 的要求 | 本包对应 | 当前状态 |
|---|---|---|
| 至少一位未参与实现的读者完成推荐安装路线和一个完整案例 | §2 A/B、§3 | 未验证：尚无外部读者 |
| 记录测试者背景、环境、耗时、命令、输出、卡点及修复后复验 | §1、§3.7、记录模板 | 未验证 |
| 客户视角审阅交付样例：输入/结论、引用、事实/线索 | §4 | 未验证 |
| 源码评审具备审查对应代码的能力 | §1、§6 | 未验证 |
| M5–M9 每项均有证据与评审结论 | §6 | 未验证 |
| 所有阻断项关闭；重要遗留项有边界与接受理由 | §2.8、§7 | 未关闭（M8-2/3/4 等） |
| 最终 commit 源码审查与完整质量检查；数字属于同一棵树 | §6.3、§6.4 | 未验证 |
| 按原权重重评 GitHub / Upwork，各至少 90% | §5 | 未执行：无分数 |
| 列出交付文件、使用说明、兼容/破坏性变更、已知限制 | §6.4、§7 | 材料存在，未评审 |
| 完成源码评审和验收后才推进阶段/准备 tag | §6.4 | 未推进：无 tag |

**结论：本文件是准备材料；独立验收尚未执行，M10 未完成。**
在至少一位独立读者完成 §3、一位审阅者完成 §4、一位有代码能力的评审者完成 §6，
并把结果填入记录模板之前，不得把本包中的任何条目当作「通过」，也不得据此发布
v1.0.0 或对外宣称已达 90%。

## 附录 A：验收项统计与追溯

| 组 | 验收项 | 数量 | 阻断项 |
|---|---|---:|---|
| A 推荐安装路线与首次运行 | A1–A7 | 7 | A2、A4、A6 |
| B 完整案例 | B1–B6 | 6 | B1 |
| C 证据核查 | C1–C6 | 6 | C1、C2、C3、C5、C6 |
| D 离线阅读 | D1–D5 | 5 | D1、D2、D3 |
| E 服务回归集结果解释 | E1–E5 | 5 | E2、E3 |
| F 公共契约核对 | F1–F6 | 6 | F1、F5 |
| G 故障恢复与数据边界 | G1–G5 | 5 | G2、G3、G5 |
| **合计** |  | **40** | **19** |

当前状态计数：通过 0 / 不通过 0 / 未验证 40。
阻断项清单：A2、A4、A6、B1、C1、C2、C3、C5、C6、D1、D2、D3、E2、E3、F1、F5、
G2、G3、G5。

## 附录 B：不在本包范围内

- 不执行独立验收，不邀请或代表外部读者。
- 不执行 M6 层级 2 真实模型批次，不申请预算。
- 不修改 `src/`、`tests/`、`README`、`CHANGELOG`、`docs/status.md`、
  `docs/architecture/` 下的文件；发现的问题记录在本包 §7，由对应负责人处理。
- 不做安全审计、渗透测试、恶意软件定性、native / 动态分析。
- 不上传 Upwork 资料、不联系客户、不创建 tag；v1.0.0 是本阶段的目标版本，tag 还未创建。
- 不预填重评分值，不把计划目标当作成绩。



