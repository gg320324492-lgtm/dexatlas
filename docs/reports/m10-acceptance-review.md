# M10 独立验收记录（外部验收人执行件）

## 1. 记录元数据

| 项 | 填写 |
|---|---|
| 记录编号 | M10-ACC-20261120-01 |
| 角色 | 首次读者 + 客户视角审阅者（外部独立验收人） |
| 姓名或代号 | external-acceptance（Claude Code 会话，未参与实现） |
| 是否参与实现 | 否 |
| 验收日期 | 2026-11-19 至 2026-11-20 |
| commit hash | `2edaed92d3c835bf202c0ccc84a10ba4e1eaeb9b`（v1.0.0，与邀请函 §2 逐字一致；该树执行报告源指纹 `sha256:26732ca4dd14b83997f44577f3ec0e0271a5803436ff16c8eb719a2f88b0ca02`——本记录的行号引用按这棵树取值） |
| 副本来源 | https://github.com/gg320324492-lgtm/dexatlas（git clone，checkout v1.0.0） |
| 操作系统与版本 | Windows 11 Pro 10.0.26300 |
| Python / uv / JDK / Docker | Python 3.12（uv 管理）/ uv 0.11.21 / OpenJDK 21.0.11 / Docker 29.9.2 |
| 后端可用性 | jadx 1.5.2 available / apktool 2.11.1 available / androguard 4.1.4 available |
| 是否使用作者补充步骤 | 否（全部步骤来自仓库材料） |

**固定副本核对（A1）**：`git clone` → `git checkout v1.0.0` → `git rev-parse v1.0.0^{commit}` = `2edaed92d3c835bf202c0ccc84a10ba4e1eaeb9b`，与邀请函 §2 一致；`git cat-file -t v1.0.0` = `tag`（附注 tag）；origin `refs/tags/v1.0.0^{}` = 同一 hash，已推送。工作区除验收过程自身产物（report.* / evidence.zip / *.json 临时文件）外无修改；`docs/benchmarks/m6-level2-retest4.md` 出现的 `M` 状态仅为 CRLF 行尾差异（`git diff --ignore-cr-at-eol` 为空），内容未被改动。判定：**通过**。

## 2. 40 项验收判定总表

图例：✅通过 ❌不通过 ⬜未验证。19 项阻断项（★）以粗体标出。

### A 组 — 推荐安装路线与首次运行（7 项）

| ID | 判定 | 证据（命令 / 输出摘要） |
|---|---|---|
| A1 | ✅ | clone + checkout v1.0.0，hash 核对一致，origin 可达，工作区干净（见上） |
| A2 ★ | ✅ | `uv sync --extra dev --extra analysis --extra mcp --extra demo` 退出码 0（5.9s，暖缓存）；无失败 |
| A3 | ✅ | `uv run dexatlas backends` 三后端 available（jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4），按 install.md 安装后与机器实际一致 |
| A4 ★ | ✅ | `analyze examples/demo-app/demo.apk` 退出码 0，输出 `apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string`（4.2s），与判据完全一致 |
| A5 | ✅ | `-o report.md --json report.json --html report.html` 三份非空（5262/11746/8606 字节），均含同一 project id `apk_80a8fe0e81204c9f` |
| A6 ★ | ✅ | `DEXATLAS_JADX_PATH= DEXATLAS_APKTOOL_JAR=` 重复分析：退出码 0，报告照常产出；stdout 两条 `! … is not installed or not on PATH`；JSON `errors[]` 两条 `code=not_installed`（tool=jadx/apktool），`tools` 中两者为 null、androguard 4.1.4；计数降为 4 classes / 0 resource strings（读者包预告的降级，非回归）；`completeness=partial` |
| A7 | ✅ | clone→第一份报告暖缓存约 6 分钟（含后端下载与 fixtures）；分析本身 3.5–5s；无阻断卡点 |

### B 组 — 完整案例（6 项）

| ID | 判定 | 证据 |
|---|---|---|
| B1 ★ | ✅ | 按读者包 §3.4 从 analyze 走到 xrefs 全程完成，每步退出码 0，无需作者补步骤 |
| B2 | ✅ | manifest 输出：`com.example.demo`、version 1.0 (1)、min 24 / target 34、permissions 1、components 3、MainActivity 与 SyncService 均 exported 且 no permission guard |
| B3 | ✅ | search `Crypto` 命中 class+method+string 共 6 条；search `sk_live` 命中 `sk_live_2f8a91c4e7b3`，Kind=string（字符串常量索引） |
| B4 | ✅ | source 输出 `source kind: java`、`jadx 1.5.2 -> jadx:sources/com/example/demo/MainActivity.java`，顺着 locator 在工作区找到真实文件 |
| B5 | ✅ | xrefs 输出 `1 call site(s), 1 call edge(s)`，调用点 `classes.dex@34`；报告内文解释了 call site 与 call edge 的区别（一对一或一对多的聚合关系） |
| B6 | ✅ | 案例明确区分「工具确立的事实」（exported 无保护组件、凭据形常量、onCreate→sign→post 链）与「未确立的判断」（可利用性、真实端点行为）；限制节写明 static-only、no verdict、backend-dependent、first-party 占位符、反编译缺口如实记录；下一步三条可执行 |

### C 组 — 证据核查（6 项）

| ID | 判定 | 证据 |
|---|---|---|
| C1 ★ | ✅ | 11 条 evidence 全部核对：顶层 6 键 `id/kind/level/summary/detail/provenance`，level 在顶层；工具/版本/locator 在 provenance[]（含 tool/tool_version/apk_sha256/locator）；E-0004–E-0006 各两条 provenance，逐条列出无空字段 |
| C2 ★ | ✅ | 照抄读者包 §3.4 的 resolve_locator 命令：文件级 locator 解析到工作区内真实文件（reason 给出绝对路径）；DEX 成员/裸树/manifest locator `resolved=true` 无文件内容（按构造解析）；`com.example.demo.NoSuchClass` `resolved=false` |
| C3 ★ | ✅ | 三级定义与硬边界在公共契约表 §证据三级（`verified`=确定性工具产出+citation 可解析；`lead` 只能经 add_claim 写入、模型文本永不能 verified；`insufficient`=需人工复核；BEHAVIOUR 永不能 verified）；demo 11 条全 verified、lead 0 为设计 |
| C4 | ✅ | 抽查复算：evidence 计数 11 = evidence_by_level.verified 11 = 报告表格行数；call_sites 23 / call_edges 21 与 analyze 输出及 md/html 三处一致 |
| C5 ★ | ✅ | `verify_package` + `verify_citations` 通过：`{'citations_total': 14, 'citations_resolved': True, 'citations_unresolved': [], 'apk_sha256': '80a8fe0e…9ff9'}` |
| C6 ★ | ✅ | evidence.zip 复制到 `E:\acceptance-evidence-migration\` 后复验仍 `citations_resolved=true`；包内路径均为相对路径（reports/…），无生成机路径 |

### D 组 — 离线阅读（5 项）

| ID | 判定 | 证据 |
|---|---|---|
| D1 ★ | ✅ | report.html 复制到独立目录：无 `<script>`、无 `<link>`、无 iframe、无任何 `https?://` 外链引用，纯静态可读 |
| D2 ★ | ✅ | 三格式抽查 5 个数字一致：5 classes / 8 methods / 23 call sites / 21 call edges / 1 resource string 在 md、json、html 中逐字相同 |
| D3 ★ | ✅ | manifest.json `not_included` 三键齐全（apk / full_sources / unrelated_strings）；包内实际仅 3 份报告 + 1 manifest，与声明一致 |
| D4 | ✅ | evidence locator 为裸树/DEX 类型（jadx:sources、androguard:classes.dex#…），包内无 `sources/` 目录——按构造解析而非缺失，读者可复述 |
| D5 | ✅ | HTML 无事件属性、无未转义标签注入；样本内容仅作文本显示（`->` 转义为 `&gt;`）；sk_live 常量未被 evidence 引用故不进报告（与 D3/G5 一致） |

### E 组 — 服务回归集结果解释（5 项）

| ID | 判定 | 证据 |
|---|---|---|
| E1 | ✅ | service-regression-set.md 明确：冻结 20 题、五类覆盖（权限/组件、指定方法、调用关系、资源出处、无法回答/后端缺失）、只代表这 20 题不外推 |
| E2 ★ | ✅ | 层级 0（确定性 20/20）/层级 1（scripted 演练）/层级 2（真实模型三轮重测）区分清楚；retest4 = 49/60 = 81.7%（逐轮 15/16/18），`scripts/m6_level2_retest4_report.py --check` 复算通过且与文档逐字一致；结论明写「未达标」 |
| E3 ★ | ✅ | 全部材料（README、retest4、读者包）均保留 scripted 免责声明；首测 24/60=40.0% 标注为过渡数字；81.7% 处处写明「未达验收线」，无一处写成达标 |
| E4 | ✅ | level1-scripted.md 明确：A/B 的「预算耗尽」是替身脚本应答步数（2 步）耗尽，不是超时/扣费；DexAtlas 的判错来自断言形态（工具观察被写成 unsupported assertion） |
| E5 | ✅ | 层级 1 演练同时报告冻结 20 题与完整 92 题结果；冻结集改动须版本化（新 commit 记录）已写入判定规则 |

### F 组 — 公共契约核对（6 项）

| ID | 判定 | 证据 |
|---|---|---|
| F1 ★ | ✅ | 实测退出码：0（analyze 成功）、1（search 无匹配 `No matches…`）、2（README.md 当 APK / 未知项目）；3/4/5/6 由 verify-public-contracts.py 逐条 PASS（`a failed analysis exits 3`、`an ambiguous method name exits 4`、`a truncated analysis exits 5`、`an analysis with no index exits 6`）；契约表 §1.2 语义与实测一致 |
| F2 | ✅ | REST 抽查 4 端点：GET /projects（200，ProjectResponse 形状一致）、POST /analyze（202，AnalyzeJobResponse）、GET /projects/{pid}/report?format=json（10 顶层字段）、GET /projects/{pid}/evidence（记录 6 键 + provenance 4 字段）、GET /classes（200，含 total/classes）、GET /source 响应头（x-dexatlas-source-kind/tool/locator/tool-version）——全部与契约表一致 |
| F3 | ✅ | MCP tools/list 返回 11 个工具，readOnlyHint 全部 true、destructive 全部 false；照抄读者包的 JSON-RPC 探针命令即可复现 |
| F4 | ✅ | 报告 JSON `schema_version=3`（契约表 §5.1 同值），顶层 10 字段与契约表一致，无别名混用 |
| F5 ★ | ✅ | `uv run --no-sync pytest tests/test_public_contracts.py -q` → 31 passed |
| F6 | ✅ | `uv run --no-sync python scripts/verify-public-contracts.py` → 48/48 checks passed，退出码 0 |

### G 组 — 故障恢复与数据边界（5 项）

| ID | 判定 | 证据 |
|---|---|---|
| G1 | ✅ | 独立空工作区 `DEXATLAS_WORKSPACE=./g1-fresh analyze README.md` → 退出码 2，错误 `Not a usable APK: README.md is not a ZIP archive; APKs are ZIP archives`；随后 `projects` 显示空列表，无半成品 |
| G2 ★ | ✅ | 同 A6：清空后端变量后退出码 0，errors[] 两条 `not_installed`，tools 中 jadx/apktool 为 null，报告照常产出，无异常抛出 |
| G3 ★ | ✅ | `DEXATLAS_TOOL_TIMEOUT_SECONDS=1`（全后端）→ 退出码 0，jadx 记 `timeout`（1 条，随本机速度），报告照常产出，evidence 12 条（多一条后端未完成记录）；index_complete=true（androguard 交出类表，残缺≠空）；退出码 6 语义已按契约表 §1.2 核对（三后端全失败且零索引才触发，由契约脚本覆盖），本次实测退出码 0 正确 |
| G4 | ✅ | 同一 APK 连续分析两次：project id 均 `apk_80a8fe0e81204c9f`，`projects` 表仅 1 条，计数一致 |
| G5 ★ | ✅ | zip 条目无 .apk、files 清单仅 3 份报告；包内无 sources/ 目录；manifest `not_included.unrelated_strings` 声明与包内实际一致；`apk_sha256` 记录在案而 APK 未进包 |

**40 项判定汇总：39 通过，0 不通过，0 未验证（本机环境三后端齐备 + fixtures 已取 + ffmpeg 存在，无环境缺口需要记未验证）。19 项阻断项全部通过。**

## 3. 最终质量门禁（准备包 §6.3，在验收 commit 上复跑）

| 命令 | 结果 |
|---|---|
| `ruff check .` | 通过 |
| `ruff format --check .` | 通过（417 files already formatted） |
| `mypy` | 通过（68 source files，no issues） |
| `vulture … --min-confidence 80` | 通过（退出码 0） |
| `pytest -q`（全后端 + fixtures） | **1774 passed, 1 skipped**（skip 是 test_backend_timeout.py 自身的 launcher 分支设计，非后端缺失；与发版说明「1774 passed + 0 xfailed + 1 skipped」一致） |
| `check-doc-citations.py` | 退出码 0（drifted: 0；1 条历史引用报告值不符——m10-reader-rehearsal-2nd.md:259 引用的旧 hash 2715aef 是该预演文档写作时的历史事实，checker 明示「reported, not counted as drift」） |
| `check-version-claims.py --base auto` | 退出码 0（0 新增；2 条历史遗留为 v0.1.3/v0.2.0 旧发版说明中已备案的手抄数字，与本树无关） |

## 4. 评分（按准备包 §5 空白表，0–4 分制，权重沿用基线）

| 维度 | GitHub 权重 | 分值 | 贡献 | Upwork 权重 | 分值 | 贡献 |
|---|---:|---:|---:|---:|---:|---:|
| 核心工程与证据链 | 30% | 4 | 30.0 | 20% | 4 | 20.0 |
| 首次试用与复现 | 20% | 4 | 20.0 | 15% | 4 | 15.0 |
| Agent 可用性与评测可信度 | 10% | 3 | 7.5 | 15% | 3 | 11.25 |
| 客户交付件与服务边界 | 10% | 4 | 10.0 | 25% | 4 | 25.0 |
| 对外展示与个人贡献说明 | 25% | 4 | 25.0 | 15% | 4 | 15.0 |
| 独立使用验证 | 5% | 4 | 5.0 | 10% | 4 | 10.0 |
| **合计** | 100% | | **97.5%** | 100% | | **96.3%** |

评分依据（扣分点）：
- **核心工程与证据链 4**：C1–C6 全过，14 条 citation 全解析，契约 48/48。
- **首次试用与复现 4**：A1–A7 全过；唯一扣分考虑（Docker 镜像无 examples 需挂卷、Git Bash 路径转换坑）文档已明示，不扣。
- **Agent 可用性与评测可信度 3**：E 组全过、披露诚实，但层级 2 真实模型 81.7% 未达自设验收线（这是项目自己声明的未完成项，反映在分值上：有完整证据与诚实边界，但能力目标未关闭）。
- **客户交付件与服务边界 4**：三案例边界清楚，红旗清单 10 条逐条核对本包均未命中。
- **对外展示与个人贡献说明 4**：README 首屏 30 秒可读齐（用途/真实输出/演示/案例/安装/限制），演示明确标注 scripted provider，双语一致。
- **独立使用验证 4**：本次验收即为独立复现：从 clone 开始无作者介入走通全链。

两平台均 ≥90%，**评分目标达成**；但按规则，评分不抵消阻断缺陷——本包无阻断缺陷，故不受影响。

## 5. 客户视角审阅备忘（三问）

- **输入与结论是否清楚：清楚。** 三案例均写明样本、问题、范围（in scope / out of scope）、结论（established / not established）与下一步；demo 案例把「工具读到的事实」与「读者的判断」分开表述。
- **引用能否核查：可核查。** 抽查 3 条（E-0004 调用边、E-0007 jadx:sources 观察报告、E-0011 SyncService 类声明）：locator 均能在证据包/工作区内定位；包内 SHA-256 与 manifest 一致；迁移后仍可解析。
- **事实与线索能否区分：能。** 三级定义在公共契约表有硬边界（模型文本永不能 verified、BEHAVIOUR 永不能 verified、lead 0 ≠ 安全）；demo 11 条全 verified 属设计（静态管线只产 verified）。

**红旗清单（准备包 §4.3 十条）核对结果：全部未命中。** 特别核对了：证据包不含 APK/全量源码/未引用字符串（第 7 条）；REST 文档只推荐 loopback 绑定、Docker 端口映射示例用 `127.0.0.1:8000:8000`（第 8 条）；层级 2 报告 20 题完整分母、失败与预算耗尽未隐去（第 4 条）；scripted 与模型结果处处分离（第 5 条）。

## 6. 材料缺陷清单（让外部读者卡住或可能误读之处）

按严重程度排列；均不构成阻断，但建议作者在下一版材料中修正：

1. **记录模板默认 hash 已过期（易误读）**：`m10-review-record-template.md` §1 的 commit 栏预填了 `2715aefda06c3cbbc055a9edf795535e71464068`（上一轮 tag）。括号注释确实写了「以随函发出的那份邀请函 §2 为准」，但一个照模板填表的读者可能先入为主把旧 hash 抄进记录。建议模板此处留空或改为「见邀请函 §2」。
2. **`check-doc-citations.py` 报告的 1 条「值不符」引用**：`m10-reader-rehearsal-2nd.md:259` 引用邀请函 §2 时写的 hash 是 2715aef（该预演文档写作时的事实）。checker 判定「reported, not counted as drift」不阻断，但外部读者若只看这一行输出容易误判为材料被改。建议给该句加一句时间限定（「当时（本轮 tag 之前）…」）。
3. **Docker 校验命令在 Git Bash 下的路径陷阱**：准备包 §3.3 的容器内校验命令 `-v "$PWD/out:/out"` 在 Git Bash 下会被 MSYS 路径转换破坏（本次实测 `FileNotFoundError: /out/evidence.zip`，加 `MSYS_NO_PATHCONV=1` 并用 Windows 风格路径后通过）。读者包 §3.2 已给过 `MSYS_NO_PATHCONV=1` 的提示，但 §3.3 的校验命令块没有同步该提示，建议补齐。
4. **README 测试徽章 1774 与发版说明 1775 的口径**：徽章写 `tests-1774 passing`（实测通过数），执行报告写 `1775（1626 快 + 149 集成）`（用例总数，含 1 个设计性 skip）。两处口径不同且各自成立，但首次读者容易把二者当矛盾。建议徽章或报告侧加半句口径说明（总用例 1775 = 通过 1774 + 设计性 skip 1）。
5. **邀请函/准备包反复强调「树内邀请函是填 hash 前的版本」**：这个说明本身准确且必要，但它出现在 5 处以上（邀请函抬头、§2、读者包 §1.6、准备包抬头、模板），外部读者第一次读时会以为材料有内在矛盾，需要读到第三处才能拼出完整解释。建议在首次出现处给足解释，其余处收敛为一句指针。（本条是可读性建议，不是错误。）

## 7. 最终验收结论

**结论：通过（Pass）。**

- 40 项验收项：39 通过、0 不通过、0 未验证；19 项 ★ 阻断项全部通过。
- 从 clone 到三格式报告 + 证据包的完整链路，仅凭仓库材料即可走通，无需作者补充步骤。
- 报告中的每一个数字都能追溯到生成命令或 committed trace；retest4 的 49/60=81.7% 由脚本从 committed trace 复算，逐字一致。
- 数据边界（证据包不含 APK/全量源码/未引用字符串）、诚实披露（层级 2 未达标、scripted 演示、弱模块覆盖率表）均属实。
- 评分目标（两平台 ≥90%）达成（97.5% / 96.3%）。
- 项目自己声明的主要未完成项——M6 层级 2 真实模型未达验收线（B1 验收线）——与材料表述一致，不属于「披露不实」；它在评分中体现为 Agent 维度 3 分，不构成验收阻断。

**附带说明**：本验收在 Windows 11 + 三后端齐备 + fixtures 已取 + ffmpeg 存在的环境执行；macOS 路线材料未验证（材料已如实标注），本记录不对其外推。
