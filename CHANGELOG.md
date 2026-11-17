# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-11-17

### Added

- **代码审查遗留修复：裁剪内容可追溯（M-1）与宽页行裁剪补全（L-1）。**
  只读审查发现两处边界：M-1——transcript 裁剪提示宣称"全文已录为
  evidence"，但 `_record_source` 的 detail 只存 tool/kind 不存文本，真实
  APK 大类被裁到 4000 字符后尾部不可达；L-1——`_clip_rows` 只裁
  `symbols`/`declarations`，`find_callers` 的 `call_sites` 大页（上限
  200 行）整页绕过裁剪、每轮重发烧预算。修复：① 证据记录承载源码文本
  （≤65536 字符按 3800 字符分块存 `detail.text_parts`，附
  `text_total_chars`/`text_parts_truncated`）；② `get_class_source`/
  `get_method_source` 增加可选 `offset`/`limit` 分页（默认整篇返回，
  向后兼容），`SourceView` 增 `text_offset`/`text_total_chars`；③
  `find_callers`/`find_callees` 增加可选 `offset`（`find_callees` 先全量
  去重再分页，跨页不重复），`CallerView`/`CalleeView` 增 `offset`；
  ④ `_clip_rows` 行键扩为 `symbols`/`declarations`/`call_sites`/`callees`
  （计数取各自 total 字段）；⑤ 裁剪提示措辞改为如实指向分页续读（
  "read the rest with the same tool, offset=N"），不再宣称全文已录为
  evidence。判分语义与七条红线不变。各带红→绿回归
  （`tests/test_review_fixes.py`，9 项）。

- **Phase 3 M5 — 对外声明基线校准。** 新增 `docs/reports/phase3-baseline.md`：
  对外声明逐条对照代码与已提交 trace 复核（Windows 启动器、证据三级、计数
  口径等），三份 benchmark（scripted / real / stronger）的八项指标均可由
  committed trace 经 `benchmarks/comparison/run.py --metrics` 重算再生，报告
  逐字再生有脚本与核对记录；演示素材的 scripted/真实模型标注同步修正。
  产物与剩余问题见该报告（基线 `6b08684` + 本分支改动）。

- **Phase 3 M6 前置 — 服务回归集冻结与层级 0/1 演练。** 新增
  `docs/benchmarks/service-regression-set.md`：从 92 题全集冻结 20 题服务
  回归集（`benchmarks/m6_service_set.py`，冻结基线 `100b191`），覆盖
  权限/组件、指定方法、调用关系、资源出处、无法回答/后端缺失五类，并写明
  「只代表这 20 道题」的能力边界；层级 0 确定性判分 **20/20**（零模型）。
  层级 1 scripted 演练（`docs/benchmarks/m6-level1-scripted.md`，零模型
  零费用）打通发题/工具循环/trace 落盘/判分管线：comparison harness 新增
  `--task <id前缀>` 按题过滤（`tests/test_comparison_task_selection.py`
  5 项回归先行），20 题与 92 题全量各跑一轮，scripted 成绩原样公开
  （20 题 A 4/20、B 4/20、DexAtlas 1/20；92 题 A 15/92、B 15/92、
  DexAtlas 5/92）——它度量 harness 机械，不是模型能力基线。

- **Phase 3 M6 层级 2 首轮真实模型批测（未达验收线，失败面分析驱动后续修复）。**
  新增 `docs/benchmarks/m6-level2-real.md` 与
  `docs/benchmarks/m6-level2-traces.json`（MiniMax-M3.1-Flash 对冻结 20 题
  独立 3 轮 × 3 配置）：DexAtlas 24/60 = 40.0%（逐轮 45%/40%/35%）、
  A 源码文本 24/60、B 结构化检索 18/60——**未达验收线（每轮 ≥80%、三轮
  合计 ≥90%），验收结论「未通过」**；全部 trace 合计 853,103 tokens，超出
  800,000 授权上限 53,103，92 题全量轮因此未执行。失败模式分析
  （`docs/benchmarks/m6-level2-failure-analysis.md`）归类执行层故障与回答
  宽度缺口，驱动其后各轮修复与复测。

- **M6 层级 2 修复后单轮复测与第二轮复测（中间测量，如实存档）。** 单轮
  复测（`docs/benchmarks/m6-level2-retest.md`，修复后首测）DexAtlas 15/20
  = 75.0%（差 1 题达 80% 单轮线），trace 合计 356,803 tokens 超出 350,000
  授权上限；五项根因修复后的第二轮复测
  （`docs/benchmarks/m6-level2-retest2.md`，20 题完整分母）DexAtlas
  **16/20 = 80.0%，达到单轮验收线**（A 7/20、B 7/20；trace 合计 355,623
  tokens，追加授权 +50,000 后在总授权内）。单轮达标不等于三轮合计 ≥90%
  的 B1 验收线；三轮完整结论见下条与 [m6-level2-retest4.md](docs/benchmarks/m6-level2-retest4.md)。

- **M6 层级 2 预算效率四项修复与行裁剪机制（窄验证三轮前置）。** 四项修复
  各带红→绿回归：① `resources` intent 加入 `KEY_TOOLS`，资源题首次成功读取
  即收口；② agent transcript 对重复 data notice 折叠（首条保留全文，其余
  短标记，MCP 对外响应不变）；②b `search_symbols` 字符串命中 excerpt 截断
  到 1 行/128 字节，工具描述与提示词增「先 limit=20 再翻页」引导；③ 同工具
  连续无新行读取 N=3 次发软提示（不硬拦，带新行的合法翻页即清除）。另带
  transcript 三层行裁剪（单字段 4000 字符、行页 12000 字符，保 total/offset
  语义）。全量 suite 1575 项通过，发版测量之前的覆盖率是 93.2%（commit `1e8d947`）。

- **v1.0.0 发版流程预研与本地 dry-run。** 新增
  `docs/reports/v1.0.0-release-runbook.md`：发版流程的完整操作方案——版本号
  落点（`src/dexatlas/__init__.py:11` 单一来源，pyproject 经 hatch 读取）、
  CHANGELOG 1.0.0 条目草稿、B4 完整重测与全门禁清单、annotated tag 与
  push 命令、GitHub Release 步骤、HANDOVER 改指 v1.0.0 的替换文本、阻断项
  B1–B5 现状核对（基于 `c3586d8`）。只准备、不发布：不打 tag、不改版本号、
  不调用模型 API。dry-run 预演记录见
  `docs/reports/v1.0.0-dry-run.md`（2026-11-16；tag、push 与 GitHub Release
  均未执行）。

- **M6 层级 2 窄验证三轮报告（预算效率修复验证，仍未达窄验证判据）。** 新增
  `docs/benchmarks/m6-level2-narrow-verify3.md` 与
  `docs/benchmarks/m6-level2-narrow-verify3-traces.json`（6 题 × 3 轮 × 3
  配置 = 54 条 trace），全部数字由新脚本
  `scripts/m6_level2_narrow_verify3_report.py` 从 trace 重算生成，trace
  缺失或不完整即拒绝生成报告。代码 `1e8d947`：DexAtlas 转通过 **3/6**
  （`manifest.permission.count-obfuscated` 3/3、`resources.app-name.demo`
  3/3、`multidex.dex-file-count` 2/3），确定性修复题 **3/5**——仍低于
  窄验证判据（≥4/6 且 ≥3/5）。实测 380,881 tokens，在 450,000 授权内，
  无熔断中止；三轮密钥扫描零命中。按 `m6-verify3-plan.md` §7 停止：不进入
  完整重测，不再追加修复轮或模型调用，M6 以现状披露方案（方案 3）定稿。

- **M6 层级 2 服务回归集单轮验证复测报告（A+C2 修复验证）。** 新增
  `docs/benchmarks/m6-level2-verify.md` 与 trace 文件
  `m6-level2-verify-traces.json`（20 题 × 3 配置 = 60 条），全部数字由新脚本
  `scripts/m6_level2_verify_report.py` 从 trace 重算生成（并对照
  `m6-level2-retest3-traces-r1.json` 逐题比较），trace 缺失或不完整即拒绝
  生成报告。本轮验证两项代码级修复（`1a7add6` A 类空响应、`192382f` C2
  字符串诱饵遮蔽）在 `main` `fbca3d5` 上的效果：MiniMax-M3.1-Flash 上
  DexAtlas 15/20 = 75.0%（A 7/20、B 7/20），未到 80% 单轮参考线；r1 失败
  3 题中 `overloads.method-identity.descriptor-distinguishes` 转通过，
  `strings.api-key.demo` 出现 1 条 A 类空响应（按修复后口径仍未能经重试
  恢复），`partial.no-apktool-there-is-no-manifest` 答了但判分不过；
  `resources.app-name.demo`、`multidex.dex-file-count` 两题 24,000 闸预算
  耗尽如实判 budget-exhausted。trace 合计 359,697 tokens，在 400,000 单轮
  授权之内；判分失败与空答未重跑。单轮数字受模型方差影响，不外推为稳定
  通过率，不据此关闭或重开 B1 验收。

- **M6 层级 2 服务回归集三轮完整复测报告（B1 关闭测量）。** 新增
  `docs/benchmarks/m6-level2-retest3.md` 与三个 trace 文件
  （`m6-level2-retest3-traces-r1/r2/r3.json`，各 20 题 × 3 配置 = 60 条），
  全部数字由新脚本 `scripts/m6_level2_retest3_report.py` 从 trace 重算生成，
  任一轮 trace 缺失或不完整即拒绝生成报告。结果：MiniMax-M3.1-Flash 上
  DexAtlas 逐轮 17/20、15/20、17/20，三轮合计 49/60 = 81.7%；A 源码文本
  20/60、B 结构化检索 22/60。**未达验收线（每轮 ≥80% 且三轮合计 ≥90%）**：
  r2 低于单轮线，三轮合计 81.7% 低于 90%。三轮 trace 合计 1,080,116 tokens，
  在 1,200,000 授权之内；单题 24,000 闸触发 2 题如实判 budget-exhausted；
  运行中 MiniMax 端点两次成片 529 过载，对 errored（未判分）配置做了如实
  重试并保留全部成功配置的原始 trace，判分失败与空答未重跑。（此为执行层修复
  **之前**的三轮复测；最终结论以修复后的 retest4 为准，逐轮 15/20、16/20、
  18/20，见本节 retest4 条目）

### Changed

- **公共契约变更：新增退出码 6（`EXIT_NO_INDEX`），分辨「跑完了但无可用的代码索引」。**
  当所有读取 DEX 的后端（Androguard 等）全部失败（例如
  `DEXATLAS_TOOL_TIMEOUT_SECONDS` 过小导致全部超时）而 Apktool 在被终止前已写出
  可解析 manifest 时，`dexatlas analyze` 过去与完整成功同为退出码 0；现在返回
  **6**，并在 stderr 说明。判定条件：项目 `completed` 且 `class_count == 0` 且
  存在索引缺口（androguard 失败或分析失败，与报告 `summary.index_complete == false`
  同源）；无 DEX 的资源型 APK（索引为空但无缺口）与部分后端失败（索引仍在）不受
  影响，仍为 0。0–5 的语义与触发条件全部不变；受影响的仅是原先错误地落在 0 的
  这类残缺运行——把非零一律当失败的调用方自动受益，把 0 当成功的调用方请按
  `exit_code in (0, 6)` 区分「完整成功」与「跑完了但无可用的代码索引」。报告
  （Markdown/JSON/HTML）与 manifest 照常产出，`schema_version` 不变。由提案
  [docs/proposals/exit-code-partial-read.md](docs/proposals/exit-code-partial-read.md)
  批准实施（方案 A），同步更新 `docs/install.md` 退出码表与
  `docs/architecture/public-contracts.md` §1.2/§8.1。回归测试
  `tests/test_public_contracts.py::test_cli_an_analysis_with_no_index_is_six`
  等四项在未修复实现上先红（`assert 0 == 6`），修复后转绿。

- **M6 服务回归集 `partial.*` 两题的判定语义修订（Phase 3 M6-③）。**
  新增 `benchmarks.model.Task.expect_backend_failure` 判定谓词：
  `partial.no-jadx-the-failure-is-recorded` 与
  `partial.no-apktool-there-is-no-manifest` 改由它判定——回答必须把缺失后端
  名与失败标记（`not_installed` / "not installed" / "did not take part"）
  写在同一处；`must_not_contain` 仍生效（无 Apktool 时答出包名即编造），
  空答判负。修订动机：comparison harness 原先用 `Configuration.FULL` 分析
  全部题目，题面声明的 `no-jadx` / `no-apktool` 配置没有消费者，agent 如实
  回答「后端没有缺失」反而判负（m6-level2-failure-analysis.md §5.6，层级 2
  共 6 题次无效失败）。同批修正 harness 执行层：按题面配置真实 Analyze
  （缺失后端在对应工作区确实不参与），B/D 按题路由到对应工作区，A 的检索面
  按题隐藏缺失后端的文件类别。**这是判分语义变更，不是放水**：对
  m6-level2-traces.json 的 6 个 DexAtlas 题次以新谓词重判仍全部判负（旧
  trace 里的回答描述的是"后端未缺失"这一旧测量事实）；历史报告数字不变，
  新口径自下次测量生效。详见
  `docs/benchmarks/service-regression-set.md` §3 判定规则与附录 B。

### Fixed

- **M6 层级 2 执行层修复成套落地：降级作答进判分、预算耗尽单列、端点故障
  可重试。** 针对三轮复测失败分析
  （`docs/benchmarks/m6-level2-retest3-failure-analysis.md`）归类的执行层故障
  与回答宽度缺口，在单轮验证（`1a7add6` A 类空响应、`192382f` C2 诱饵遮蔽）
  之后补齐：
  - **limitations 纳入判分**：`SystemResult` 新增 `limitations` 随 trace 落盘；
    后端失效类任务（如 `partial.no-apktool-*`）的「后端缺席读不到」经
    `Answer.limitations` 进判分通道——它本身就是该题要的证据。limitations
    永不进 findings、永不满足 `must_contain`。
  - **预算耗尽单列**：`SystemResult.outcome` 取 `answered`/`budget-exhausted`/
    `failed`；判分器对 `budget-exhausted` 一律不判过，报告如实命名，不再从
    error 文案里推断。
  - **端点故障重试启用**：`AgentSystem` 新增 `model_attempts`（默认 3）与
    `model_backoff`，替代写死的单次请求；retryable 端点故障现在有重试机会。
  - **XML 工具调用泄漏容错**：最终回答含 `<invoke>`、`<|tool_calls|>` 等
    协议泄漏标记时按 retryable 端点故障处理，泄漏文本不进最终答案。
  - **C2 并集放宽到单词查询**：单轮验证显示单词 `api_key` 检索仍只见诱饵；
    并集规则不再按词数设限（含 FTS 拆不出词、走子串兜底的 `apikey` 类），
    命中类/方法/字段的查询仍不并集。同文件上文 C2 条目已同步改写。
  - 另在系统提示补两条作答纪律（方法身份题枚举同类全部方法；计数读不出时
    如实写入 limitations 并列出已读项）——提示词级软修复，不保证每轮触发。
  回归测试：`tests/test_comparison_output_contract.py`（6 用例，旧实现先红）、
  `tests/test_search_symbols_decoy.py` 单词用例（首版实现上先红）。
  窄验证（6 题 × 3 轮，53/54 条 trace）显示 4/6 题转化、确定性子集 4/5；
  修复后的完整效果见三轮重测报告（`docs/benchmarks/m6-level2-retest4.md`）。
- **模型端点返回空 assistant 消息被记为解题失败（M6 A 类「降级空响应」）。**
  OpenAI 兼容端点偶发返回 `200`，其 `choices[0].message.content` 为空
  （`completion_tokens=0`）且无 `tool_calls`。`openai_compat.parse_response`
  过去把它原样解析为 `ModelResponse(content="")`：orchestrator 记 COMPLETED、
  0 findings，benchmark 判分以 `failed = not answer_text` 标失败且 `error`
  留空——端点抽风被计成解题失败（M6 三轮复测 r1
  `partial.no-apktool-there-is-no-manifest`、r2 `strings.api-key.demo` 即此因）。
  修复：content 为空/None 且无 tool_calls 时抛
  `ProviderError("the model endpoint answered with an empty message",
  retryable=True)`，走 orchestrator `_ask` 既有的退避重试；content 非空或带
  tool_calls 的正常工具轮不受影响。回归测试 `tests/test_openai_empty_completion.py`
  在旧实现上先红（空 completion 不抛错），修复后转绿；orchestrator 层测试
  证明 retryable 错误触发重试、任务以非空答案完成。
- **`search_symbols` 的词法命中遮蔽常量池枚举（M6 C2「诱饵遮蔽」）。**
  词法检索命中 string 类符号时，兜底链（子串检索 → 常量池枚举）不再触发：
  agent 查询 `api key` 命中诱饵常量 `api_key` 后，同池真密钥
  `sk_live_2f8a91c4e7b3` 完全不可见，agent 据诱饵作答。修复：词法命中
  均为 string 类符号的查询，把常量池枚举结果与词法命中**并集返回**——
  词法命中保序在前、枚举补充在后、按 (kind, name) 去重、分页作用于并集整体；
  命中为类/方法/字段的查询不触发并集，避免污染代码检索。首版修复只对
  ≥2 词的查询生效；单轮验证显示 agent 以单词 `api_key` 检索仍会只见到诱饵，
  随后放宽到单词查询（含 FTS 拆不出词、走子串兜底的 `apikey` 一类），
  不再按词数设限。
  回归测试 `tests/test_search_symbols_decoy.py` 在旧实现上先红
  （`"api key"` 只返回 `['api_key']`），修复后转绿；单轮验证后补的
  单词用例（`api_key`、`apikey`）在首版实现上同样红，放宽后转绿。
- **REST API 导出的报告丢失 APK 档案事实。** 项目行过去只存哈希与大小，
  API 从行重建报告时 `ApkMetadata` 的 `dex_files` / `native_libraries` /
  `has_signed_certificate` 全部落默认值——同一项目 CLI 报告写
  `DEX files: 1`，API 报告写 `DEX files: 0`，违背案例 3「两种导出字节一致」
  的声称。`SCHEMA_VERSION` 6→7，projects 表新增 `apk_metadata` JSON 列
  （迁移按列缺失判定，旧行读作「未记录」而非零），写入方随 upsert 保存、
  读取方优先从该列恢复。回归测试
  `tests/test_api.py::test_the_api_report_carries_the_same_apk_metadata_as_the_cli`
  在旧实现上先红（`[] == ['classes.dex', 'classes2.dex']`），修复后转绿。
- **重复分析后 CLI 报告的 `created_at` 与存储行不一致。** `Project.create`
  以当次分析时钟盖戳，而 upsert 不改写该列——重复分析后 CLI 报告（渲染自
  内存模型）携带第二次的时间，API 报告（自存储行重建）携带第一次的时间，
  两个传输对同一项目报出两个创建时间。发布前从存储回读项目（仅发布路径；
  未发布路径保留内存模型，避免把失败分析误报为运行中），两个传输
  陈述同一存储事实。回归测试
  `tests/test_analysis_runs.py::test_a_re_analysis_reports_the_stored_created_at`
  在旧实现上先红，修复后转绿。
- **`androguard:AndroidManifest.xml` 出处无法被 `resolve_locator` 解析。**
  SDK 级别证据（E-0001）自 74d4c55 起引用该 locator，但解析器把
  `AndroidManifest.xml` 当 DEX 文件名对照 APK 的 dex 清单校验，永远拒绝——
  MCP 的 `resolve_locator` 对自己产出的一条 verified 证据返回「不是该 APK
  的 dex 文件」。修复：dex 白名单仅约束 `.dex` 后缀的 place；androguard
  从 APK 内读取的其它位置（二进制 manifest）按其本名解析。
- **`benchmarks/run.py --configuration no-*` 按题面配置过滤任务集**
  （m6-level3-recheck.md §6 的 harness 缺口）。旧实现只把所选配置加入
  Analyze 集，任务集仍返回全部 92 题，`_run_tasks` 随即在
  `analyses[(task.configuration, task.sample)]` 处 KeyError；现改为
  `--configuration no-jadx` / `no-apktool` 只路由**声明**适用该配置的题、
  只建对应工作区，与 `--category` / `--task` 取交集；组合不出任何题时以
  「no tasks selected」退出码 2 明确结束，不再静默全选。不带
  `--configuration` 的正常路径不变。回归测试
  `tests/test_comparison_configuration_routing.py`（8 项）在旧实现上先红
  （KeyError / 全选），修复后全绿。
- **`scripts/m10_selfcheck.py` 的退出码契约检查期望滞后。** 退出码 6
  （`EXIT_NO_INDEX`）落地后，契约表、CLI 常量与契约测试
  `EXPECTED_EXIT_CODES` 均已更新为 0–6，但自查脚本的 F1 检查仍硬编码
  期望 0–5，在契约一致的树上误报失败（自查一度 39/40）。现改为从契约
  测试的 `EXPECTED_EXIT_CODES` 表读取期望（字面量 + 按 CLI 常量名解析），
  三处互相印证，契约变更不再需要同步第三份副本；回归测试
  `tests/test_m10_selfcheck.py` 在旧硬编码实现上先红，修复后转绿。

### Added

- **逐例客户交付附件落盘（Phase 3 M7 收尾）。** 三个[案例](docs/case-studies/README.md)
  的可下载交付件入库至 `docs/case-studies/attachments/`（9 个文件）：demo 与
  API 集成案例（同一分析 `apk_80a8fe0e81204c9f`）与混淆案例
  （`apk_2f8d476fb9e71ac4`）各含 Markdown/JSON/离线 HTML 报告与最小证据包
  （`analyze --html` / `export` 生成，工具版本 jadx 1.5.2 / apktool 2.11.1 /
  androguard 4.1.4 与报告内记录一致）；三个证据包均通过 `verify_package`
  校验（manifest 含逐文件 sha256 与 `not_included` 三键声明）。三篇案例文档
  与案例 README 增补附件引用节，注明生成命令与可复现性——读者无需安装
  DexAtlas 即可审阅证据。
- **v1.0.0 发版流程本地 dry-run 报告。** 按
  [发版前检查清单](docs/reports/v1.0.0-release-checklist.md) 完成一次本地预演
  （不创建 tag、不发布、不改版本号）：7 步流程逐项核对、5 项阻断与 4 项披露的
  当日状态核对、新缺口清单（发版说明 `docs/releases/v1.0.0.md` 未落盘、契约表
  未记录退出码 6、清单 ROADMAP 引用悬空、status.md M8 行过时、install.md
  「No APK」与 examples/ 一方 APK 矛盾等）。报告见
  `docs/reports/v1.0.0-dry-run.md`。仅预演与文档，不发版。
- **M6 层级 2 复测下一轮的预算与判分方案与本地校验脚本。** 上一轮复测（DexAtlas 15/20，trace 合计 356,803 tokens）超出 35 万授权上限后，为修复合入后的下一轮复测定稿预算方案 `docs/benchmarks/m6-level2-retest-plan.md`：单题熔断 24,000 tokens（`--total-tokens`，取上轮通过题实测最大 22,776 之上）、总额 300,000 tokens（授权 350,000，留 50,000 缓冲）、总额熔断以逐题分批执行落实、判分与报告沿用既有脚本口径。新增本地校验脚本 `scripts/m6_retest_budget.py`：逐题与总额核对 trace token 用量，超支非零退出；无 trace 数据时校验方案文件存在与格式并退出 0。仅方案与脚本，不调用任何模型 API。
- **M6 层级 2 verify3 执行方案。** 新增
  `docs/benchmarks/m6-verify3-plan.md`：窄验证三轮 + 达标后完整重测的一次性
  授权与执行约束（窄验证 ≤450,000 tokens、完整重测 ≤1,250,000 tokens、
  单题 24,000 闸不放松、判分七条红线零改动），并固化停止条件——窄验证
  不达标即按验收方案三选一定稿服务承诺范围，不再追加修复轮或模型调用。
  方案定稿，不含任何测量结果。
- **M10 独立验收自查脚本与自查报告。** 把[验收准备包](docs/reports/m10-acceptance-pack.md)
  40 项中可自动化的 40 项检查写成 `scripts/m10_selfcheck.py`（仅读仓库、
  无第三方依赖，`uv run --no-sync python scripts/m10_selfcheck.py` 运行，
  退出码 0 表示无失败项；`--json` 输出机器可读结果）：验收包结构完整性、
  文档相对链接、CHANGELOG 与版本一致性、README 徽章与报告数字一致、
  报告 `<!--fig:-->` 标记一致性、退出码/MCP 工具/报告 schema/证据包
  `not_included`/HTML 离线渲染等契约静态核对、门禁命令可执行性；40 项
  人工判定项逐项标注原因留待读者执行。自查记录见
  `docs/reports/m10-selfcheck.md`；[读者验收包](docs/reports/m10-reader-package.md)
  末尾增加指向自查报告的入口。M10 验收材料定稿：验收包按最新代码状态修订
  （邀请函钉定 commit、读者包补降级路径与工作区提示），读者彩排三项高优发现
  修复（案例正文与验收包同步）。M10 **独立验收尚未开始**——验收包已成稿并
  自检，但没有独立评审者跑过。
- **双语 README 与文档状态同步（Phase 3 M9 + B5）。** README（英文）与
  README.zh-CN（简体中文）展示入口：双语状态段、路线图状态表、第三方署名表、
  文档地图；Quick start 的 analyze 示例直接使用仓库自带
  `examples/demo-app/demo.apk`（新读者克隆后即可运行，无需先取第三方
  fixtures），并注明该 APK 可由 `scripts/build-demo-apk.sh` 重建。README /
  README.zh-CN / status.md / ROADMAP 的 M6 表述按窄验证二轮、三轮结果与
  「方案 3（现状披露）」决定同步；install.md 的安装命令与实际 extras 组合对齐
  （uv sync 四 extras），并修正「No APK is committed」与 `examples/` 五个一方
  样例 APK 的矛盾。
- **修复提案：退出码 6 分辨「跑完了但无可用的代码索引」。** 为公共契约
  §8.1 记录的已知缺口（三后端全部失败但 manifest 可解析时 `analyze` 仍退
  出 0）提供只含设计与版本化方案的提案文档
  `docs/proposals/exit-code-partial-read.md`：候选方案对比、推荐方案
  （新增 `EXIT_NO_INDEX = 6`，不改动 0–5 语义）、CHANGELOG 措辞草案与
  红→绿测试计划。提案于 M8 阶段提交，**本版已按方案 A 实施**——退出码 6
  的语义、判定条件与版本化方式见本节 Changed 段的「公共契约变更：新增退出码
  6」，契约依据见 `docs/architecture/public-contracts.md` §1.2/§8.1（§8.1 已
  由「已知缺口」转为「已按提案修复」）与 `docs/install.md` 的退出码表。
- **Agent 回答契约与工具调优（Phase 3 M6-③）。** 依据 M6 层级 2 失败分析
  （`docs/benchmarks/m6-level2-failure-analysis.md`）的失败模式，改 agent 的
  回答契约并补一个查询工具，不动题集与判分：
  - **否定/缺席题的回答形态（FM-1，9 题次）**：问题问「是否存在 X」而证据
    表明不存在时，`orchestrator` 的答案合成不再把否定陈述写成 finding——
    否定措辞且无真实证据支撑的 conclusion 改记入 limitations
    （`_is_process_note`），报告仍完整携带这句话，但 findings 为零，与
    判分 `expect_empty` 的语义一致。
  - **过程注记移出结论（FM-2，7 题次）**：只引用过程类记录（
    `supports_claims=false`，如「分析已完成」）的 conclusion 不再成为
    finding，改记入 limitations。真实证据支撑的结论不受影响。
  - **计数题逐项成条与完整描述符（FM-2/FM-7）**：`INSTRUCTIONS` 明确要求
    「一个计数对象一条 finding、汇总文字移出 conclusions」以及「方法身份
    必须带完整 JVM 描述符 `Class.name(descriptor)`」。
  - **新增 MCP 只读工具 `find_resource_declarations`（FM-6，工具缺口）**：
    按资源名或值反查声明文件（`res/values*/strings.xml` 等），返回声明行
    的文件、qualifier、kind 与 provenance；`McpToolClient`、`Planner`
    （新增 `resources` 意图）、证据记录（`_record_resource_declarations`）
    全链路接入。**公共契约变更：MCP 工具从十个增至十一个**，
    `docs/architecture/public-contracts.md`、`tests/test_public_contracts.py`、
    `scripts/verify-public-contracts.py` 已同步。
  - 契约行为由 `tests/test_agent_answer_contract.py` 的 19 个测试固化
    （旧实现上全部先红）。

### Added

- **全部读写工作区的命令统一接受 `--workspace`/`-w`（Phase 3 M8）。**
  `analyze` 之外，`backends`、`projects`、`classes`、`methods`、`source`、
  `resources`、`resrefs`、`search`、`export`、`manifest`、`xrefs` 现在也接受
  `--workspace`/`-w`，语义与 `analyze` 相同（设置 `DEXATLAS_WORKSPACE` 后清除
  设置缓存，使选项在已缓存设置的进程里同样生效）。Docker / 多工作区场景下
  「分析写入哪个工作区，查询就读哪个」不必再在两套记法之间切换。`analyze`
  可以创建工作区；其余命令只读，`--workspace` 指向不存在的目录时报
  `No such workspace` 并以退出码 2 结束，且不创建该目录。

- **公共契约表（Phase 3 M8）。** 新增 `docs/architecture/public-contracts.md`：
  逐项固化对外承诺——CLI 全部 13 个子命令与退出码语义（0 成功 / 1 空答案 /
  2 请求错误 / 3 分析失败 / 4 重载歧义 / 5 截断 / 6 无可用代码索引
  （`EXIT_NO_INDEX`））、REST 全部 23 个端点的请求/响应形状与状态码、
  MCP 十一个只读工具的参数与返回形状、`SymbolCounts` 与证据
  三级（verified/lead/insufficient）的判定边界、JSON 报告 `schema_version=3`
  顶层结构、证据包 manifest `schema_version=1` 字段，以及语义化版本政策
  （兼容变更进 CHANGELOG，破坏性变更显式升版本）。契约由真实接口验证：
  新增 `scripts/verify-public-contracts.py` 起 uvicorn 逐端点实测（26 项）、
  MCP 走协议实测（6 项）、CLI 退出码逐个触发（14 项），**M8 契约核对当时的
  46 项全部通过**；结果记录在契约表"验证记录"一节。**v1.0.0 的契约清单为 49 个
  检查项**（28 REST + 6 MCP + 15 CLI，含新增的退出码 6 活检）；这是静态条数，
  实跑条数依机器而定——契约表"验证记录"一节记了两次实跑的数字。新增契约快照测试
  `tests/test_public_contracts.py`（22 项），把 REST 路由表、MCP 工具表、
  退出码表、报告/证据包 schema 固化为断言——任何契约变更先红测试，防止
  悄悄变更。

- **离线 HTML 报告与最小证据包（Phase 3 M7）。** `dexatlas analyze` 新增
  `--html <file>`：把同一份分析渲染成单个自包含 HTML 页——无脚本、无外部资源，
  样本字符串等不可信文本全部转义，防样本内容在读者浏览器里执行脚本。HTML 与
  Markdown/JSON 共享同一数据层（`reports/summary.py` 的同一组指标），不重新计算
  事实；新增 `dexatlas export <project> --output evidence.zip` 导出最小证据包：
  三种格式报告、证据记录、证据引用到的源码片段，以及带 SHA-256 校验清单的
  `manifest.json`。包内一切以相对路径定位（可迁移到其他目录后逐条核对引用），
  客户 APK、全量源码、无关字符串不随包导出，未包含内容在 manifest 的
  `not_included` 中明示。包校验（`verify_package`）拒绝路径遍历条目名、文件哈希
  不符、manifest 与报告项目绑定不一致；`verify_citations` 在包迁移后核对引用仍可
  解析。回归测试覆盖：HTML 转义、包路径遍历、错误样本绑定、篡改检测、迁移后
  引用解析。设计说明见 `docs/architecture/report-rendering.md`。

- **布局 XML 里硬编码的文本进入符号索引。** `res/layout*`、`res/menu`、`res/xml`
  里的 `android:text`、`android:hint`、`android:contentDescription`、`android:title`、
  `android:summary`、`android:label` 字面量，现在按 `layout_text` 类型进 `resources`
  表和全文索引，`dexatlas search` 搜得到，`dexatlas resources` 列得出来。行的
  `name` 是携带属性的元素（如 `TextView`），`attribute` 记录属性名，`position`
  是元素起始行号，provenance locator 形如
  `apktool:res/layout/activity_main.xml#line=7;TextView`，指回布局文件与元素所在行。
  `res/values*` 字符串资源的行为不变；`resources` 表新增 `attribute` 列（可空），
  旧工作区自动迁移。`@string/...` 引用仍不在索引——资源 ID 图是另一件事。

- **资源引用（`@string/app_name` 等）进入符号索引，建立资源引用边表。**
  解码树里全部 `res/**/*.xml` 的属性值与 `<item>` 文本，凡形如
  `@type/name`（含 `@android:type/name` 平台前缀）都记成一条引用边，进新表
  `resource_references`：引用方（文件 + 元素 + 属性 + 行号）指向被引资源
  （type + name）。`@+id/...` 是定义不是引用，`?attr/...` 走主题解析，均不入边。
  查询入口：CLI 新子命令 `dexatlas resrefs <project> [--type T] [--name N]`，
  API 新端点 `GET /projects/{id}/resource-references?res_type=…&res_name=…`，
  每条边带 `apktool:<file>#line=N;<Tag>` 形式的 locator，指回携带引用的元素。
  `SymbolCounts` 新增 `resource_references` 计数；schema 升到 v6，旧工作区
  自动迁移（新表为空，下次分析填入）。资源 ID 的数值映射
  （`R.string.app_name` → int）仍不在索引——那要读 `resources.arsc`。

### Changed

- **Agent 默认预算上调（Phase 3 M6，公共契约变更）。** `Budget` 默认值改为
  `max_tokens=120000`、`max_iterations=16`、`max_seconds=120`，`Planner` 的
  `DEFAULT_MAX_STEPS` 改为 40。依据是 M4 复验（`docs/reports/m4-e2e-run.md` §5）
  的真实记录：旧默认（20000/8/120s，12 步）下 5/5 任务 `budget_exhausted`，
  而完成任务实际用到的配置是 tokens=120000、步数 40，完成的两次运行分别用了
  4 与 5 次迭代、18 与 12 次工具调用；最长的未完成运行达到 14 次迭代仍在读。
  新上限约为最大实测用量的两倍，不是目标值。**兼容性影响：** 四个环境变量
  （`DEXATLAS_AGENT_MAX_TOKENS/MAX_ITERATIONS/MAX_SECONDS/MAX_STEPS`）仍是
  整体替换式覆盖、语义不变；但依赖旧默认上限的调用方（如按旧值断言
  `budget_exhausted`、或按旧值做费用估算）需注意——同一任务在新默认下可能
  完成、也可能消耗更多预算。依据与边界写进
  `docs/architecture/agent.md` 的「Default budget and stop policy」一节。

- **Agent 新增重复调用检测与收束停止策略（Phase 3 M6）。** 工作区只读，因此
  同一工具+同一参数的重复调用不可能返回新答案：现在循环会命中先前成功读取的
  摘要，直接以复用观察回答（携带同一 evidence id，并注明 `duplicate: true` 与
  被复用的 call id），不再真正调用工具；事件记录 `duplicate_call`，报告
  `convergence.repeated_calls` 计数。失败/超时/被拒的调用不算重复，允许重试。
  同时新增停止策略：`planner` 把问题意图写入 plan，`sufficiency.py` 在每次
  成功读取后判定该意图的关键事实是否已取到（manifest 题看 manifest、callers
  题看 find_callers/find_callees 等；搜索「没搜到」也是有效事实）；命中后下一
  请求的指令会说明证据已齐并要求作答，再给 2 次宽限读取
  （`WRAP_UP_GRACE_CALLS`），随后从请求中移除全部工具并再要求作答两次
  （`FINAL_ANSWER_ROUNDS`）——仍不答则以 `failed` 结束并给出可读原因，绝不
  变成无答案的 `completed`。边界不变：收束只是停止读取，答案仍由模型给出、
  结论仍是 lead。Agent JSON 报告新增 `convergence` 字段
  （`evidence_ready`/`repeated_calls`/`tools_closed`），Markdown 报告新增
  「How the task converged」小节（旧报告无此节即不出现，纯增量）。

- **M6 层级 2 修复后窄验证的 trace 与不完整审计。** 新增
  `docs/benchmarks/m6-level2-narrow-verify-traces.json`（6 题 × 3 配置 × 3 轮，
  应为 54 条，实捕 53 条）与 `docs/benchmarks/m6-level2-narrow-verify-incomplete.md`
  （由新脚本 `scripts/m6_level2_narrow_verify_audit.py` 生成），并新增完整报告
  脚本 `scripts/m6_level2_narrow_verify_report.py`——trace 不足 54 条时拒绝
  生成完整报告（该拒绝保持有效）。本轮验证执行层成套修复（limitations 判分、
  预算单列、重试启用、XML 泄漏容错、C2 单词并集）在 `claude/m6-level2-verify`
  `31a7b45` 上的效果：DexAtlas 6 题中 4 题转化（每题 ≥2 轮正确），确定性修复
  子集 4/5；`strings.api-key.demo` r2 出现 1 条空答，`resources.app-name.demo`
  r1 与 `multidex.dex-file-count` r1 预算耗尽。运行不完整：原授权 400,000
  tokens，追加至 406,000 后仍超支，实际 410,256 tokens，缺失的 1 条 trace
  未跑。窄闸门（≥4/6 且 ≥3/5）在已捕获轮次上达标，但不构成 54-trace 验收判定。

- **M6 层级 2 修复后三轮完整重测报告（B1 验收测量）。** 新增
  `docs/benchmarks/m6-level2-retest4.md` 与三个 trace 文件
  （`docs/benchmarks/m6-level2-retest4-traces-r1.json`、`-r2.json`、`-r3.json`，
  各 20 题 × 3 配置 = 60 条，合计 180 条），全部数字由新脚本
  `scripts/m6_level2_retest4_report.py` 从 trace 重算生成，任一轮 trace
  缺失或不完整即拒绝生成报告。结果：MiniMax-M3.1-Flash 上 DexAtlas 逐轮
  15/20、16/20、18/20，三轮合计 49/60 = 81.7%；A 源码文本 21/60、B 结构化
  检索 21/60。**未达 B1 验收线（每轮 ≥16/20 且三轮合计 ≥54/60）**：r1
  低于单轮线，三轮合计 81.7% 低于 90%。与修复前复测（retest3）合计分相同，
  失败构成已从执行层故障转为判分不过与个别题预算耗尽/errored
  （`multidex.dex-file-count` 三轮均 errored；`strings.api-key.demo` r3
  预算耗尽）。三轮 trace 合计 1,182,356 tokens，在 1,200,000 授权之内，
  无熔断中止、无 not-run；判分失败与空答未重跑。B1 保持未关闭；后续处置
  按其后的窄验证结果定稿（见上方窄验证三轮条目：按方案 §7 停止，M6 以
  现状披露方案（方案 3）定稿）。

- **M6 层级 2 窄验证二轮报告（四项修复验证，未达窄验证判据）。** 新增
  `docs/benchmarks/m6-level2-narrow-verify2.md` 与
  `docs/benchmarks/m6-level2-narrow-verify2-traces.json`（6 题 × 3 轮 × 3
  配置 = 54 条 trace，全部落盘），全部数字由新脚本
  `scripts/m6_level2_narrow_verify2_report.py` 从 trace 重算生成，trace
  缺失或不完整即拒绝生成报告。本轮验证首轮窄验证之后针对已知失败面的四项
  修复（协议泄漏纠偏重试、partial 后端缺失措辞对齐、api-key 常量池检索
  引导、descriptor 连写模板）在 `claude/m6-level2-verify` `9b25835` 上的
  效果。结果：MiniMax-M3.1-Flash 上 DexAtlas 转通过 **2/6**
  （`manifest.permission.count-obfuscated` 3/3、`resources.app-name.demo`
  2/3），确定性修复相关题转通过 **2/5**——**未达窄验证判据（转通过
  ≥4/6 且确定性题 ≥3/5）**。协议泄漏纠偏重试生效（54 条 trace 协议失败
  0 条，retest4 中三轮全灭的 `multidex.dex-file-count` 本轮 r3 打通）；
  `strings.api-key.demo` 三轮全部预算耗尽，`overloads.method-identity.
  descriptor-distinguishes` 三轮全 wrong。实测合计 420,826 tokens，超出
  授权上限 410,000 达 10,826（最后一批跑完才到批间检查点，超出如实记录，
  未补跑）。按验收方案 §2.2：转通过 2/6 ≤ 2，停止投入，**转方案 3
  （现状披露）**；B1 保持未关闭。已知局限：窄题集不外推到 20 题完整
  回归集、单模型、first-party 小样本、预算不对等，详见报告「已知局限」节。

### Fixed

- **截断测试的子进程环境剥离 coverage 钩子（与测量脚本解耦）。**
  `tests/test_output_truncation.py` 的用例把 `ToolInvocation.env` 换成
  `_coverage_free_env()`——去掉 `COVERAGE_PROCESS*` 变量后的环境副本。
  原因：coverage 测量形态下，测试用 venv python 启动的子进程会经
  `a1_coverage.pth` 钩子自启 coverage；一旦 rc 文件读不到（被并发测量
  删除/路径失效），钩子向子进程 stderr 打约 2KB 的 ConfigError 回栈，把
  只写 10 字节的安静脚本顶过 1024 字节上限，测试误判「输出被截断」。这段
  回栈是测量自身的簿记，不是工具产出。回归：污染环境下旧实现红
  （`test_an_output_that_fits_is_not_reported_as_cut` 判 `('stderr',)`），
  新实现绿。
- **测量脚本的 coverage rc 文件改为按进程命名。**
  `scripts/refresh-report-figures.py` 的 `.coveragerc-measure.ini` 改为
  `.coveragerc-measure-<pid>.ini`：固定文件名会被并发的测量或残留进程
  删除/改写，使 `COVERAGE_PROCESS_START` 指向失效配置。同时
  `measure_tests` 的调用约定显式化：`args` 默认是 pytest 参数、函数补
  `sys.executable -m pytest` 前缀，`full_command=True` 表示 args 已是完整
  命令（`coverage run -m pytest` 形态）原样运行——修正自检两轮的命令
  拼装（此前以 WinError 2 崩溃）。
- **测量的覆盖率数据文件改为每次运行私有（并发不再顶掉报告数字）。**
  `.coverage` 是整个 checkout 共享的：不带 `--cov-append` 的 `pytest --cov`
  会把它整个替换掉。发版测量实测被顶成 2699/7631 = 35.4%（15 个 doc 测试
  那一小撮的覆盖面），套件计数仍然正确、覆盖率却是残缺的，报告与 README
  徽章因此写出了不实的数字。现在每次测量用自己的数据文件
  （`.scratch/coverage/<pid>/.coverage`），并用 `COVERAGE_FILE` 告诉它启动的
  每一个进程——套件、coverage 工具、测试拉起的 worker 子进程——写到这里，
  别处碰不到它；同一 checkout 里的并发测量由操作系统级文件锁挡住，已有
  测量在跑时新测量直接拒绝并说明，不与对方抢报告。回归：旧实现下 3 条新
  用例全红（关键一条的失败原因正是「没告诉进程写哪个文件」），新实现绿。
- **`docs/install.md` 的安装命令与实际 extras 组合对齐（Phase 3 M8）。**
  安装节改为 lockfile 驱动的 `uv sync --extra dev --extra analysis --extra mcp
  --extra demo`，并逐项说明四个 extra 的用途，以及「仅 `analysis`」最小安装
  路线缺什么；开发节同步为四 extras（CI 装 dev/analysis/mcp，`demo` 只在
  重生成演示与报告图时用到），并说明 `tests/test_public_contracts.py` 需要
  `mcp` extra。补充 `scripts/fetch-fixtures.sh` 需要已认证的 `gh` CLI，
  并在 Docker 一节写明工作区可用 `--workspace`/`-w` 或 `DEXATLAS_WORKSPACE`
  指定（见上方 Added 条目）。

## [0.2.0] — 2026-11-14

The agent layer, open to a caller. Phase 2's first four milestones, in one
release: the analysis core made safe for programmatic access (M0), a read-only
MCP server over the workspace (M1), a single evidence-first agent (M2), and a
92-task benchmark harness with a scripted and a real-model comparison (M3).
The web workbench carries six of its eight screens; the benchmark view and
the screen-level refinement behind them are still being built, and this
release says so rather than counting them in.

### Added

- **The workbench benchmark screen (M4 screen 8).** The benchmark half of
  the report-export screen: a `#/benchmarks` view that presents the M3
  comparison's two committed measurements — the scripted-provider run and
  the MiniMax-M3.1-Flash run — each with its eight metrics, its
  "why the failed tasks failed" table, and the disclosures the M3 rules
  require (a scripted provider is not a model baseline; a real-model run is
  not reproducible to the digit; neither measurement claims that one
  configuration is better than another).

  The screen serves no stored numbers and adds no second derivation: the
  new read-only endpoint `GET /api/benchmarks/m3` recomputes every figure
  from the traces committed under `docs/benchmarks/` with the comparison
  harness's own `_run_from_document` + `compare`, formats them with the
  harness's own `format_value`, and reads nothing into a workspace. A
  checkout without the trace files answers with an empty measurement list
  and the disclosures, not an error.

- **The workbench agent workspace (M4 screen 6).** A user can now ask the
  evidence-first agent a question about an analysed APK from the browser:
  the workbench accepts the question, runs the agent's own
  `Orchestrator` in the background (the loop plans, calls the read-only MCP
  tools, asks the model and checks its conclusions), and the screen polls
  the task to show the plan, the tool-call timeline and the report the
  project's own renderer writes — established facts, leads, and
  insufficient evidence, each finding carrying the evidence id or locator
  it rests on.

  The model endpoint is configuration, not convention: `DEXATLAS_AGENT_BASE_URL`,
  `DEXATLAS_AGENT_MODEL`, `DEXATLAS_AGENT_API_KEY` and the optional
  `DEXATLAS_AGENT_PROVIDER` (`openai-compatible` or `local`) are read from
  the environment of the process serving the workbench. The key travels in
  the request headers only — never to disk, never into a task state, an
  event or a report — and with nothing configured the question is refused
  with `503 agent_not_configured` rather than answered by a stand-in model.
  The tool set, the step count and the budgets are the agent's own `Planner`
  and `Budget`; the task states live under the workspace's `agent-tasks/`
  directory through the agent's own `TaskStore`, so an interrupted task can
  be picked up again.

- **A read-only MCP server.** An agent can now ask a DexAtlas workspace what
  it holds: the projects, the manifest, the indexed symbols, the source of a
  class or of one exact method, the call sites between methods, the evidence
  records and the places those records were read from. The server reads and
  nothing else — it never writes, never runs a shell, and never returns more
  than a bounded amount of anything — and **it needs no model provider**: it
  is a tool server, and a tool server that needed a model would not be a tool
  server.

  Three things a caller has to know are said in the tools themselves rather
  than only in the documentation: a count is only as good as the analysis
  behind it, so every answer says which backends were missing and whether a
  limit stopped the analysis short; a name is not a method, so an ambiguous
  name is answered with the candidates rather than with one of them, because
  the body of the wrong overload reads exactly like the body of the right
  one; and everything that comes out of an APK is **data, not instruction**,
  so it is carried in a field that says so and the server's own descriptions
  are checked never to carry the APK's text.

  ```bash
  uv sync --extra analysis --extra mcp
  uv run dexatlas-mcp        # speaks MCP over stdio
  ```

  A client to try it with is in `examples/mcp_client.py`, and the tools are
  described in `docs/architecture/mcp-server.md`.

- **The web workbench, and six of its eight screens.** `dexatlas-workbench`
  serves a read-only browser over a workspace: the projects it holds, each
  with the backends that took part and the counts the analysis produced; the
  upload screen, where an APK chosen in the browser is stored with the REST
  API's own policy — the same staging, the same size limit, the same
  validation, the same refusals, one shared implementation in
  `dexatlas.api.uploads` rather than a copy — and analysed in the background,
  the browser polling the project's status until the run publishes, and an
  APK that was analysed before is answered with its project, not analysed
  again; the search and evidence view, where a query returns indexed
  symbols, a class or method opens its Java or Smali source and an evidence
  record's provenance locators resolve to places inside that analysis; the
  cross-reference view — for one method at a time — of who calls it and what
  it calls, with the DEX file and the instruction offset each call was read
  out of, and clickable callers and callees to walk the chain with; the agent
  workspace, where a question about an analysed APK is answered by the
  production orchestrator over a configured model endpoint; and the report
  export: the Markdown and JSON the existing renderers write over the
  published snapshot — the same report the CLI and the REST API produce,
  with no second format and no changed field.

  It calls the MCP tools' own functions in-process, so the JSON the browser
  receives is the shape the MCP server would have returned, produced by the
  same code: **no added analysis, no writes, and no second contract**. A test
  asserts the response against the tool's own `model_dump()`.

  Two answers the call-graph screen refuses to fake: a method nobody calls is
  `0` call sites, not a 404 — "the analysis read no call into this method" and
  "this method does not exist" are different answers — and no number is drawn
  beside a callee, because `find_callees` deduplicates its callees and answers
  no per-callee count, so such a number would be one no query can re-derive.

  ```bash
  uv sync --extra dev --extra analysis --extra mcp
  uv run dexatlas-workbench      # serves http://127.0.0.1:8618
  ```

  Two screens of the M4 set are not built — the benchmark view whose
  report-export half is the export above, and the deeper work the existing
  screens still need — and the cross-reference screen answers one method at a
  time rather than rendering a whole-workspace call graph. The screens and
  the decisions they were built under: `docs/architecture/workbench.md`.

- **The workflow is in the repository, not in a scratch directory.** The scripts
  that re-derive the documents' citations, that accept a branch, that prove a
  regression test goes red without its fix, that run the suite on real Linux
  and that fetch the decompiler over a slow link all lived in a local folder
  that was never committed — so they died with the machine that had them.
  They are `scripts/remap-citations.py`, `scripts/accept-chip.sh`,
  `scripts/prove-red.sh`, `scripts/linux-check.sh` and
  `scripts/fetch-jadx.py` now, and [`docs/HANDOVER.md`](docs/HANDOVER.md)
  says how to rebuild the environment and what to do next.

  The citation remapper is **idempotent** now: it moves a citation only
  where the checker says the symbol it names has left the cited range, so
  running it twice does not move every number twice — which is what the
  older version did, and why it had to be reset before every run. The
  citation checker walks the tree once instead of once per citation, which
  is the difference between a second and a quarter of an hour.

- **A status page** — `docs/status.md` says where the project stands and what is left:
  the released versions, the acceptance status of Phase 1, and the gaps that remain.
  It is written in Chinese, like the analysis coverage document. Its test count and
  coverage are now written by the same script that writes the execution report's, so
  the page cannot drift away from the measurement it summarises.
- **The APK's resource table is in the index.** Apktool decoded `res/` into the
  workspace and nothing read it: the demo app's `DexAtlas Demo` — a string that
  exists only in `res/values/strings.xml` — was in no index at all, and a key written
  only in a resource file could not be found. The text declarations in `res/values*/`
  are read now, each row carrying the provenance of the file that declared it, and
  they are queryable through `dexatlas resources` and `GET /projects/{id}/resources`.
  Text hard-coded in a layout is still not covered, and the document says so.
- **A source says which backend produced it.** `class_source` returned Smali or Java
  with nothing to tell the two apart, so a caller could not know the difference
  without inspecting the workspace. `class_source_document` and `method_source_document`
  return the text together with its kind, its provenance and the version of the tool
  that wrote it; the REST API reports the same in response headers. The plain-text
  response body is unchanged.
- **The version claims in the documentation are checked.** `check-doc-citations.py`
  proves that a `file:line` citation still points at what it names, but a sentence
  like "the newest tag is v0.1.2" is not a line number and nothing could see it go
  stale. `scripts/check-version-claims.py` reads the tags, the package version, the
  changelog and the generated figures out of the repository and reports the claims
  that contradict them. It runs in CI, and it runs there too.
- **A benchmark for APKs large enough to reach the limits.** The committed samples
  are under 3 KB, so the three limits in the Androguard adapter had never been
  pressed against a real file and what would happen on a large APK was a guess.
  `scripts/generate-large-apk.py` writes a synthetic APK of a chosen size and a
  ground-truth manifest of what it wrote; `docs/benchmarks/large-apk.md` is the
  measurement, and it says what it did not measure. The pressure test found three
  real defects, all fixed — see below.

- **One evidence-first agent.** The MCP server can be read by a program; the
  agent is what turns it into an answer. It takes a question about an APK,
  plans a bounded series of tool calls, makes them against a workspace, checks
  that every conclusion it reached has something behind it, and reports what it
  found — **separated into what was established, what is a lead, and what is
  not established**. One orchestrator, not a swarm: one loop, one plan, one
  budget, one state, one report.

  The pieces that make it more than a loop: per-task budgets for tokens,
  iterations and execution time; tool-call logging with retries and a circuit
  breaker; a task state that is written down, so an interrupted task can be
  picked up again; an explicit confirmation before anything sensitive; and
  three model endpoints behind one interface — an OpenAI-compatible one, a
  local one, and a scripted one, so the orchestration can be tested without a
  model key and without a network.

  It routes its conclusions through the project's own `EvidenceBuilder` rather
  than around it, so a model's output can never become a verified finding. And
  **it does not read instructions found inside an APK**: the APK is untrusted
  input, and there is a test for it that goes red when the property is taken
  away.

  The design is in `docs/architecture/agent.md`.

- **The M3 comparison: three configurations over one task set, and the eight
  metrics Phase 2 asked for.** The milestone asked for a comparison, and what
  the repository had was a task set and a runner that checked DexAtlas against
  its own expectations. The three configurations now run over the same 92
  questions: one that reads decompiled source text, one that reads structured
  symbols and call references, and the DexAtlas agent with its provenance and
  its evidence verification. Each of them sees only the question, the sample,
  the backend configuration and a reference number — the marking scheme is
  held by the scorer alone, and a system under test never reads the task set.

  The eight metrics — correct-answer rate, evidence-grounding rate,
  unsupported-assertion rate, false-positive rate, tool-call success rate,
  recovery rate, token consumption and execution duration — are computed from
  one auditable trace per run, and every reported figure can be regenerated by
  a script in this repository from the trace file beside it. A metric whose
  denominator is zero reads `n/a`, never `0%`: a configuration that called no
  tools has not had a 100% tool-call success rate.

  ```bash
  uv run --no-sync python benchmarks/comparison/run.py --report docs/benchmarks/comparison.md
  uv run --no-sync python benchmarks/comparison/run.py --input docs/benchmarks/comparison-traces.json --metrics
  ```

  A measurement against a **real model** is reported separately, in its own
  file and its own table, because the scripted measurement and the real one
  answer different questions and a table that mixed them would support a
  conclusion neither row supports. The run against MiniMax-M3.1-Flash is in
  `docs/benchmarks/comparison-real.md`, and it says why each failed task
  failed: the agent's lower overall rate is mostly a model that keeps asking
  for tools until the budget runs out, and on the questions whose answer is an
  absence it is the best of the three.

  **A real-model run is not reproducible.** Asked at temperature 0, the same
  question twice still does not get the same answer twice: two runs over the
  same tasks differed by about a percentage point in the correct-answer rate
  and by about one percent in the tokens spent. The report describes the run
  whose traces sit beside it, a rerun is not expected to reproduce them to
  the digit, and a difference between configurations smaller than that
  spread is noise no row claims. The scripted measurement has no such
  spread: its provider is a script, so its numbers come back the same on
  every run.

- **An M4 acceptance rehearsal, from a new user's chair.**
  `docs/reports/m4-acceptance.md` walks the repository's own installation,
  CLI, API and workbench instructions step by step, checks them against the
  six exit criteria the plan set, and separates what passed from what was
  missing — including the two screens that were still being built as the
  rehearsal ran, and the places where the documents understated or
  overstated what the tree had. The documentation fixes below are its
  findings, fixed.

  The M4 source review and acceptance (`docs/reports/m4-review.md`) first
  recorded a **conditional pass** with two closing conditions; both were
  verified the same day (the real-model re-run in `docs/reports/m4-e2e-run.md`
  §5, commit `b6e5fb1`, and the bilingual README agent sections, commit
  `6eee294`), and the verdict was upgraded to **pass**. A question can still
  exhaust its budget under the default settings, and the documents say so:
  that is model-behaviour tuning, not an engineering gap.

### Changed

- **`dexatlas analyze` 在分析被截断时返回退出码 5（新退出码 `EXIT_TRUNCATED`）。**
  分析跑完、报告照常写出，但只要有一步被上限截短（`output_truncated` 记在
  项目上），退出码就是 5——调用方只看退出码就能区分「干净完成（0）」「部分
  完成/被截断（5）」「失败（3）」。0/1/2/3/4 的含义不变；此前截断的运行
  退出码是 0，依赖旧退出码的调用方需注意这一公共契约变更。

- **The health answers name the workspace, not its path.** The workbench's
  `/api/health` carried the workspace's absolute path, which the header then
  printed in full — the directory *name* is enough to tell workspaces apart,
  and it is a name on every platform. This is a contract change stated here:
  a caller that parsed the field as a path would break, and the field's
  purpose does not need a path.

- **The report says which run it describes, and whether a later attempt
  published.** An exported report said `Status: completed` — the status of
  the snapshot — with no way for a standalone reader to tell that a later
  analysis had failed. The report names the run it describes and says when
  a later attempt ended differently; the JSON carries the same two facts,
  and its schema version moves to 2 (additive keys, a version that says the
  shape changed rather than a silent change).

- **Untrusted DEX is parsed in a worker, and the host's logging is left
  alone.** Androguard is a library, so a malformed DEX was parsed in the
  process that served it — one that takes the interpreter down took the
  service with it. The parse now happens in a worker the service starts,
  bounds and throws away, and an unparseable DEX is a recorded failure
  rather than a dead process. The same adapter also removed *every* loguru
  handler in the process — the host's included — and nothing could put them
  back; the suppression is by name now.

- **A deleted project's analysis goes with it.** Every run wrote into a
  directory of its own, so deleting a project left a directory per run
  behind it for ever; the workspace belongs to the server.

- **The liveness probe was able to take the service down.** `/health` built
  an Analyzer, which opened the workspace database — and `Store.open()`
  wrote the schema version on every open, even when it was already right,
  so every probe took the one write lock SQLite allows and fought the
  analysis it was meant to protect; the loser answered 500 with "database
  is locked". The probe depends on the backend registry alone now, the
  version is written only when it changed, and the schema only when a
  table is missing.

- **The manifest's SDK levels come from the APK's bytes.** Apktool writes
  its own rebuilt values into `apktool.yml`, and what it writes is not what
  the APK says: a sample whose binary manifest carries `minSdkVersion=24`
  decoded to an `sdkInfo` of 25. The levels are read back from the binary
  manifest now, and `apktool.yml` is no longer trusted for them.

- **A measurement of the report's figures starts from nothing.** A run
  interrupted before pytest-cov erased the coverage file left its partial
  record behind, and the next measurement added itself to that record — two
  measurements of the same tree could disagree, and the freshness check
  blamed the tree. `.coverage*` is removed from the repository root before
  the script measures.

- **The README's status banners denied what is built.** They said the MCP
  server, the agent and the workbench were "planned, not shipped" while the
  server and the agent have landed and the workbench has six of its eight
  screens. Both banners now say Phase 2 is in progress and name what is
  built, what is in the tree but unreleased, and what is not built.

- **The MCP server now says "no manifest" when that is what it means.** A
  project whose Apktool step never ran has no manifest, and the tool answered
  `unknown_project` — a project that is not there, said about a project that
  is. A caller that believed it would go looking for a project that does not
  exist instead of for the backend that did not run. There is a `no_manifest`
  error code now, it names the backends that did not take part, and
  `unknown_project` still means what it says.

- **A symbol's name and detail are marked as data.** `search_symbols` returned
  the symbol's name and an excerpt of the indexed text as plain strings, and
  both come out of the APK — for a string symbol the name *is* the string.
  The other tools carried the same text in a field with a notice on it, and
  this one did not, so a caller reading the two could not tell that one of
  them was data. They are carried the same way now, and they are bounded the
  same way: a symbol's text is cut and the cut is stated.

### Fixed

- **A real endpoint refused the agent's own tool answers.** The OpenAI shape
  reserves the `tool` role for the answer to a call the *model* made, and a
  strict endpoint rejects a `tool` message whose `tool_call_id` matches no
  assistant `tool_calls` entry with a 400 — "tool result's tool id not found".
  A tool the agent's *plan* called has no such entry, so every plan step's
  answer was one the endpoint would refuse. The agent therefore could not
  talk to a strict endpoint at all: it was rejected on its first observation,
  every time. Such an answer goes in the `user` channel now, with the same
  notice that says it is data. It still reaches the model as data and never
  as an instruction; it just does not claim the model asked for it.

  The scripted provider never saw this, because a scripted answer is always
  exactly the shape the code asked for. It took a run against a real endpoint
  to find it.

- **A model that answered in prose lost its answer.** The agent asks for a
  JSON document and nothing else, and a model sometimes writes its reasoning
  first and the document after it. The parser accepted the whole answer only
  if the *entire* thing was a document, so such an answer was recorded as
  "the model answered without naming any evidence" — a real conclusion,
  read out of a real answer, thrown away and reported as no answer at all.
  The document is now found inside the answer rather than beside it, and the
  prose around it is kept so a reader still sees it.

- **"What does this method call" was answered with "who calls this method".**
  `find_callees` and `find_callers` ran the same query — both of them looked
  the *callee* up — so the tool that answers the other direction answered the
  same direction twice. An agent that asked what a method calls was told who
  calls it: **every word of it true, and all of it about another thing**. The
  test beside it counted the two numbers and never checked the direction, so
  it was green.

- **Five places where two things did not match, found by an acceptance pass.**
  Putting the MCP server, the agent and the architecture document together
  left five mismatches, and each of them was a number or a sentence that was
  true about one thing and read as if it were about another:

  - a cross-reference record's **summary contradicted its own detail** — the
    summary said "called from one location" while the detail said two call
    sites, and "a location" now means a call site;
  - **the agent wrote its cross-reference records under keys the reports do
    not read** (`call_sites` rather than `call_site_count`), so the report
    counted them as one and one whatever the tool had found;
  - **the migration dropped the table's indexes** — SQLite drops an index with
    the table it belongs to, and the schema script does not run again once
    the version matches, so every rebuilt workspace scanned the whole table
    for good;
  - **the JSON report's project block held one of the two numbers** with
    nothing to say which, and the API's `total` had no unit;
  - **the JSON report's schema version did not move** when keys were added
    to it.

- **A source was looked for with the wrong question.** Whether a class's
  source could be read was decided by asking whether JADX was *installed*,
  rather than whether JADX took part in the analysis. Those are different
  questions, and the answer belonged to the wrong one: a workspace written on
  a machine with JADX was read on one without it and served the Smali instead
  of the Java, and an output tree left over from an earlier analysis was
  served as if this one had produced it. Reading a source file is a matter of
  reading a file, and the question is now the one the analysis recorded.

  The Smali fallback follows from it, and it is the better rule for the same
  reason: the fallback is for a class the decompiler did not manage, not for
  a decompiler that is not on the machine.

- **A note about the analysis could carry a conclusion.** The agent records
  "the analysis is incomplete: apktool did not take part" as evidence, which
  is right — a reader needs to know. But the verifier counted it as support
  for a conclusion, so a model that cited it produced a **lead** on the
  strength of a record that says nothing about the APK being asked about. A
  conclusion has to rest on an observation of the thing the question was
  about, and on a record that establishes something: a record that says the
  evidence was insufficient cannot be the ground a conclusion stands on.

- **A cross-reference could not say where a call happened.** The index held one row
  per call, and the row said who called whom and how — but not *where*. A method
  that called the same target twice held two rows that said exactly the same thing,
  and a table keyed on the caller and the callee could not tell "called twice" from
  "written twice". The rows are **call sites** now: each carries the DEX file it
  was read out of and the instruction offset it sits at, and the key carries both,
  so the two kinds of duplication stay apart. A **call edge** — the relationship
  between two methods — is derived from the sites rather than stored beside them,
  and the report states the two numbers separately and says which is which
  (`Call sites indexed` beside `Call edges indexed`), because the review found a
  report printing two different units side by side and a reader taking a ratio
  that was never there. The old names stay in the JSON report and **their
  values did not change** — but what a row *is* did, so the two old keys now
  count the call sites rather than the relationships they used to duplicate.
  A reader who wants the relationships reads `call_edges`. The table was
  rebuilt rather than altered — SQLite cannot change a primary key in place
  — and the project's count of the rows went with it, because
  a record that says "23 cross-references" while the table holds nothing is a
  number a reader cannot check.

- **A method asked for by name could be the wrong one.** `read_method_source` took
  the first declaration whose *name* matched and returned it, so a class with two
  overloads of `sign` answered every request for `sign` with whichever one the
  decompiler happened to write first — and the body of the wrong overload reads
  exactly like the body of the right one, all the way into an agent's answer. The
  DEX descriptor tells two overloads apart, and the symbol index already held it:
  a request may now carry one (`--descriptor` on the command line, `?descriptor=`
  in the API), and a name that matches several methods is reported as an ambiguity
  rather than resolved by guessing — the candidates and their descriptors are in
  the error, so the caller can ask again and be sure of the answer. The CLI says
  so with an exit code of its own (4), the API with `409`; `1` (nothing there),
  `2` (a wrong request) and `3` (the analysis failed) still mean what they meant.
  A name that matches exactly one method is answered as before, and so is a
  request that carries a descriptor: the old call sites keep working.
- **A method of a nested class could be the outer class's method.** A decompiler
  writes a nested class into the file of the class that holds it, so one file
  holds several classes, and the lookup read the whole file. A request for
  `Outer$Inner.f` could be answered with `Outer.f`. The methods are now read
  from the class the request names.
- **A class name could walk out of the decompiler's output tree.** The JADX backend
  turned a class name into a path without checking any part of it, so a name that
  was already a path — absolute, with a drive letter, with a UNC prefix — was
  honoured as one, and the file it named was read and served. The Apktool backend
  had checked every part; the rules now live in one place (`dexatlas.core.paths`)
  and both backends use them, so they cannot drift apart. A name that fails the
  check is "no such class" — a 404, not a 500 whose traceback carries the
  server's own directories.
- **The API published the server's paths.** `apk_path` and the JSON report's
  `project.apk.path` carried the absolute path of the analysed file, and a
  manifest parse error carried the absolute path of the decoded file. The file's
  *name* is published now, the workspace root is redacted from error details, and
  the promise the architecture document makes — that the API redacts server paths
  — holds in more than the one place it used to.
- **An upload was read into memory in one piece, and an archive could ask for
  gigabytes.** The upload is streamed and counted, and refused at 256 MiB while it
  streams — never held in memory, never written in full. An archive whose
  declared contents exceed 2 GiB, or that expands more than a hundredfold, is
  refused from its ZIP central directory, before a byte of it is decompressed.
  The same APK was also inspected twice — once by the API and once by the
  analysis — and is inspected once now.
- **A backend that outlived its timeout was not stopped.** The timeout killed the
  process that was started, which for JADX is a `cmd.exe` whose child is the
  `java.exe` doing the work: the work carried on, held the output the caller was
  waiting on, and the call waited for it anyway. The whole tree is taken down
  now — a process group on POSIX, `taskkill /T` on Windows — and the message says
  "could not be terminated" when it could not be.
- **The default deployment published an unauthenticated API on every interface.**
  The API has no authentication by design; it is a single-user tool. But
  `docker-compose.yml` published it on `0.0.0.0` and the installation guide
  taught the same command. Both publish on `127.0.0.1` now, and the guide says
  what exposing it means and what a reverse proxy in front of it is for. The
  server inside the container still binds `0.0.0.0` — it has to, or the port
  mapping would find nothing to connect to.
- **The OpenAPI schema did not describe the source endpoints.** They answer with
  the source text by default and with a JSON document on request, and both carry
  `X-DexAtlas-Source-*` headers; the schema claimed JSON with an empty body. It
  says what the endpoints actually return now, headers included.
- **The backend's version was read once per indexed symbol.** Every class, method,
  field and cross-reference carries a provenance record, and every record asked the
  backend for its version — a query that scans the installed distributions. On a
  12,000-method APK, 80 of the 82 seconds of the run went on that. The version is
  now asked once.
- **Reaching a limit truncated the index silently.** The three limits in the
  Androguard adapter stopped the walk and logged a warning; the project then reported
  `completed` with no errors, and the report's counts matched the rows in the
  database exactly — because both faithfully recorded an index that had been cut
  short. A limit now records an `output_truncated` error that names the limit and
  says what was missed, so the gap is stated beside the numbers instead of hidden
  inside them.
- **Two of the three limits were counted per DEX file.** A four-dex APK got four
  times the allowance, so the largest APKs got the most headroom — the opposite of
  what a limit is for. All three are now one budget per analysis.

- **The documentation names the release that shipped each fix.** The Phase 1 execution
  report's opening, the headings of its sections 3.11 – 3.15, and the opening of
  section 6 of the analysis coverage document all described work that had already
  shipped. They now name v0.1.3, which shipped it.
- **The status page named a constant that does not exist.** It referred to a
  `MAX_INSTRUCTION_LIMIT`; the limits the code actually enforces are
  `DEFAULT_METHOD_LIMIT`, `DEFAULT_STRING_LIMIT` and `DEFAULT_INSTRUCTION_LIMIT`.
- **The READMEs pointed at finished work as the current backlog.** The eight tasks that
  planned Phase 1 are archived under `.github/issues/v0.1.0/planned/`; what is
  outstanding is the Phase 1 source review.
- **The v0.1.3 release notes quoted a hand-copied coverage figure.** They said 93.9%,
  which belonged to an earlier tree; the release's own generated report measured
  94.0% (1857/1975 lines) from the tree it was cut from. They now state the
  measured figure.
- **The `[0.1.0]` entry counted 208 tests; the release shipped 204.** A commit made
  after the release overwrote the entry with the test count of the tree at the time.
  The tag measures 204, and the v0.1.0 release notes said 204. The `[0.1.1]` entry
  inherited it as "up from 208", and now says 204.
- **The README's badges had stopped at v0.1.2.** They showed 275 tests and 89%
  coverage — that release's numbers — while the project was on 444 tests and 94.0%.
  A badge URL cannot carry a generated figure, so this is a number to write and
  re-check, not one that can be measured. The badge is written from the
  measurement now — see the review findings below.

### Found by the Phase 1 source review

The review ran three parallel audits against the tree and produced 44 findings;
every one was re-verified on the tree it was found on, and the ones that are
fixed below are fixed with a test that goes red when the fix is reverted.
The review report is `docs/reports/phase1-review-report.md`.

- **An upload's file name was the client's to choose.** Two different APKs
  uploaded under the same name landed on the same path, and the analysis of the
  first one reads that path in the background — so it read the *second* APK's
  bytes, and the project it produced said it held the first APK's classes.
  Nothing a reader could check contradicted the record: the project's hash was
  the first APK's, its identifier was the first APK's, and every provenance
  record named the first APK's hash. The file is stored under its own hash now,
  so two uploads share a path only when they are the same bytes.
- **The default configuration did not decompile Java.** The default workspace is
  a relative path, and the JADX backend handed the same relative path to the
  child process twice — once as `--output-dir` and once as its working
  directory. The path was read against two different bases, so the sources
  landed in a nested copy of the tree the index reads: the report lost the
  decompilation row, the class count dropped by one, and the source fell back
  to Smali — while the tool-version line still credited jadx. Every path a
  backend is handed now means one place, and CI runs the default configuration
  end to end.
- **A read of the database was a write.** The journal mode is a property of the
  database rather than of the connection, and setting it is a write — so every
  read took the one write lock SQLite allows, and a second request failed with
  `database is locked`. It is set once, where the database is created.
- **An analysis that crashed left the project running forever.** The pipeline
  documented that failures are recorded on the project rather than raised, and
  did neither: an exception left the project in `running` with no error
  recorded, and the API answered every later upload of that APK with the
  existing project — so it was never analysed again. A failure now lands the
  project in `failed` with the error on it, and the exception still reaches the
  caller.
  The three kinds of failure are told apart by the exit code: 1 is an empty
  answer, 2 is a wrong request, and **3 is an analysis that broke** — a code
  of its own, so a caller that reads only the exit code can tell a run that
  found nothing from a run that fell over.
  The failure's message is redacted where it is written. An exception's message
  can quote the path it was handed, and that path names the machine the
  analysis ran on; the message is read back through the API, through the JSON
  report and through the Markdown report, so it is redacted once rather than
  three times. The workspace root becomes a placeholder and the path inside it
  survives — that is the part that says what was being worked on.
- **Two numbers that sat next to each other counted different things.** The
  report's "cross-references with evidence" counted the called methods that
  got a record, while the "cross-references indexed" beside it counted the
  calls — so a method called from three places read as "one of three had
  evidence". Both now count edges, in the same unit, and the report says which
  is which.
- **The evidence table dropped the conclusion it was making room for.** With
  more than 200 classes, the decompilation-coverage record fell outside the
  window: the metric was still in the report and the evidence behind it was
  not. The evidence is ordered so the conclusions come first, and the report
  says how many records were left out and what they were.
- **The exported report said the analysis took no time.** The API rebuilt the
  result from storage and did not restore the duration — and the database had
  no column for it. It is stored now, and an old workspace says "unknown"
  rather than "0.0 seconds".
- **The numbers in the report were compared with themselves.** The suite and
  coverage figures were checked against the record written next to them, so
  writing "999" into both changed nothing anybody could see, and the
  fingerprint that declares them stale covered only the source — adding a test
  did not make them stale. They are measured now, and the fingerprint covers
  the suite and the tools that measure it.
- **The citation checker checked 18 of 94 references, and always passed.** The
  script's `main()` returned 0 whatever it found, and the test re-implemented
  the rules with a different tolerance. Ninety-three of the ninety-four
  references are checked now, and a drifted one fails the check.
- **The version-claim checker passed on the case it was built for.** A commit
  that released a version while the documents still denied it was classified as
  drift the base already had, and the check passed. The base commit is now
  judged against its own facts.
- **A behaviour could be published as a finding.** The evidence level was
  documented as the mechanism that stops an unverified claim from being
  reported as one, and nothing stopped a caller from recording a behaviour as
  verified — which the report renders as "deterministically established by an
  analysis tool". A model cannot promote itself now.
- **The readmes' badges were written by hand.** A badge is a URL, so it cannot
  carry a generated figure, so its number was copied — and it was stale. The
  badge is written from the same measurement the report is written from, and a
  run that does not account for every test in the tree is refused rather than
  published.

## [0.1.3] — 2026-10-20

Evidence that points back. A conclusion you cannot point back to is not a
conclusion — this release makes that true of more things than it used to be.

### Added

- **`docs/analysis-provenance.md`** — what each conclusion is actually backed by:
  which backend produces which kind of conclusion, what the four `Provenance`
  fields hold, the real locator format of every backend, and how a reader can
  verify a claim themselves. Every claim in it points at a file and a line, or
  at the output of a real run.
- **Cross-references are evidence now.** The pipeline records one
  `cross_reference` record per called method of the analysed APK. The unit is
  the callee, not the call, and calls into library code stay in the index
  without becoming a conclusion about this application.
- **The decompilation coverage is stated.** The report gained a "Methods
  decompiled by JADX" line and one `observation` record carrying the failed
  methods and the classes JADX wrote no source for. `dexatlas methods` shows a
  "Decompiled" column.
- **The CLI says what it folds.** `dexatlas classes` still shows a short list of
  sources per class, but it now says how many it left out and how to see them:
  `--all` prints every source, `--provenance-limit N` sets the number, and a
  class list cut by `--limit` says so too.
- **Every locator travels.** A locator is now `<tool>:<place>`, where the place
  is relative to the artefact the tool names — the APK for Androguard, the
  output tree for JADX and Apktool. JADX's used to be an absolute path, so a
  report carried a pointer to the machine that produced it and to nothing else;
  the two halves of one record were not even the same kind of thing. A
  workspace indexed before the change still reads back in the current form, so
  no migration is needed.

### Fixed

- **A method id had two spellings.** The methods table and the cross-reference
  table stored the same method differently, so an id copied out of
  `dexatlas methods` never resolved in `dexatlas xrefs` for any method with two
  or more arguments. There is one spelling now — the canonical JVM descriptor —
  in the model, in the store and in the lookup, and a workspace indexed by an
  earlier version still resolves.
- **The report's counts did not match the tables.** Analysing the multi-dex
  sample printed 14 methods where the table held 11 rows. The counts come from
  the tables now, so the number in the report is the number a query returns,
  and the definitions that collapsed into one row keep both provenances.
- **`decompiled` held a different fact than its name.** The flag was set from
  "this method has a code item in the DEX", which is not "JADX decompiled this
  method". It says what it says now: JADX is the only backend that can answer
  the question, so the pipeline reads JADX's own output. A `JADX WARN` comment
  above a method is no longer counted as a failure, and a constructor is
  recognised by having no return type rather than by its name. The database
  column and the API field keep their names; the value under that name changed
  meaning, so an existing workspace holds the old meaning until it is
  re-analysed.
- **The CLI saw less than the API it fronts.** `dexatlas classes` printed the
  first two sources of a class and said nothing, while the REST endpoint
  returned all of them. See "The CLI says what it folds" above.
- **An empty configured path did not disable a backend.** The documented
  three-state semantics — unset means "look on `PATH`", empty means "do not
  use this one", a path means "use this" — were only two states, because an
  empty string was skipped and the lookup fell through to `PATH`. The strict
  `xfail` that recorded the defect is now a plain assertion test.
- **The `LIKE` prefix filter did not escape the underscore.** `--prefix
  com.example.com_ex` also matched `com.example.comXex.Gamma`, because `_` is
  a wildcard in SQL and underscores are legal in Android package names. The
  answer was wrong, not merely fuzzy.
- **The report's account of the cross-reference fix was inverted.** It claimed
  Androguard's `get_descriptor()` returned the canonical spelling; measured on
  4.1.4 it returns the spaced one, which is what made the v0.1.0 fix look
  complete when it was not.
- **The REST endpoint echoed whatever the caller typed.** It returns the
  canonical spelling now, which is the one that can be pasted into the next
  request.
- **The exported-component evidence carried no tool version.** One report held
  `apktool 2.11.1 -> AndroidManifest.xml` next to `apktool ->
  AndroidManifest.xml#/application`: the same tool, the same run, one record
  with a version and one without, and no way to tell "this tool has no
  version" from "nobody filled this in". The backend-error evidence had the
  same hole, and a failure is evidence too. The versions are probed before the
  evidence is built and handed to the builder, so a record cannot be written
  without them; `None` now means exactly one thing — the tool did not run.
- **The report's own figures were written by hand.** They are measured by
  `scripts/refresh-report-figures.py` now, and `tests/test_docs.py` checks the
  report against the code. The refresh converges in one run instead of two, and
  it tells a report that is merely out of date apart from a tree that is
  broken.
- **The source fingerprint depended on line endings.** Git checks out CRLF on
  Windows and LF on Linux, so the same source had two fingerprints and the
  report was declared stale on every platform but the one it was measured on.
- **Nine places where the documentation said one thing and the code did
  another**, plus three smaller ones. The merge rule for a class's `kind` was
  written backwards, the coverage table listed two modules above the threshold
  it claimed to be limited to, two method ids were quoted in a spelling the
  repository does not use, the test file table was missing two files, a code
  block was attributed to the wrong test, the historical test counts were wrong,
  and one section skipped a number. The figures that can be measured now are
  measured, and the ones that were hand-copied are checked by a test.
- **The cross-reference kind said one thing and meant another.** Its
  documentation listed five ways a call can be made; the code only ever
  produced one. It is read from the bytecode instruction now, so a static
  call and a virtual call are distinguishable in the index. `dynamic` is not
  among them: the instructions that would carry it name a call site rather
  than a method, so there is no callee to record.
- **A string constant knew nothing about where it was used.** The fields for
  it existed and were never filled, so a hardcoded key could be found but
  not traced to the method that uses it. The bytecode walk that collects
  cross-references now records the use sites too, at no extra cost. Pool
  entries no instruction loads — type descriptors, member names — still
  have no location, because nothing loads them.
- **The version was wrong in two places at once.** The published packages
  called themselves 0.1.0 after v0.1.1 and v0.1.2 had shipped, and the
  number was written in both the package and the project file. It lives in
  one place now and the build reads it from there.
- **A workflow mistake could not be seen.** A job-level `env:` block used
  `${{ runner.temp }}`, which GitHub does not allow there. The run was
  created and failed without scheduling a single job, with no message and
  nothing to retry — it looked like a platform fault. `actionlint` is part
  of the lint job now, and it applies GitHub's own rules.
- **The Docker build could not read the version.** The dependency layer
  installs before the source is copied, and the build backend needs the
  version file. The image copies that one file into the dependency layer.

### Engineering

- 444 tests (347 fast, 97 integration), up from 275
- First-party coverage 94.0% (1857/1975 lines), up from 89.2%
- `mypy` strict, `ruff` lint and format; the CI workflow covers Python 3.12 and
  3.13, a configuration with one backend deliberately absent, a Docker build, a
  dependency audit, the lint job and a workflow lint

## [0.1.2] — 2026-10-20

The Phase 1 acceptance checklist, actually met. Five test APKs built by this
project, a demo video, and a correction to how the checklist had been recorded.

### Added

- **Five self-built test APKs**, the number the Phase 1 acceptance checklist asks
  for. Each covers a different layout, and each is built from the smali sources
  committed beside it, so none is a mystery binary:
  - `demo-app` — the general case: components, permissions, cross-references
  - `multidex-app` — two dexes, so `smali/` and `smali_classes2/` both exist, and
    one class name appears in both
  - `obfuscated-app` — one-letter packages, classes and methods, no source hints
  - `strings-app` — mostly string constants, for the search index
  - `wide-app` — an interface with two implementations and a factory
- `scripts/build-test-apks.sh` rebuilds all five from source;
  `scripts/build-demo-apk.sh` now delegates to it
- **A demo video** at `docs/assets/demo.mp4`, encoded from the same frames as the
  README's GIFs, so the two cannot drift apart
- Tests that keep the acceptance checklist honest: every committed APK must have
  its smali sources beside it, the build script's sample list must match what is
  on disk, and the set of APKs allowed in the repository is derived from the
  filesystem rather than written out by hand

### Fixed

- **The Phase 1 exit checklist had been paraphrased into something easier to tick.**
  The plan asks for "five **self-built** test APKs" and a "demo **video**"; the
  checklist said "verified against test APKs" and "a generated demo recording",
  and every box was ticked. One self-built sample and a GIF are not five samples
  and a video. The wording is now the plan's own, and the items behind it exist.

### Engineering

- 275 tests (196 fast, 79 integration), up from 244
- First-party coverage 89.2% (1525/1709 lines)
- `mypy` strict, `ruff` lint and format, GitHub Actions green on Python 3.12 and 3.13

### Known limitations

- The samples are small — the largest is under 3 KB. The *layouts* are covered, the
  *scale* is not: there is still no large-APK data point, so index performance and
  the instruction limits have never been under real load
- The obfuscated sample is hand-written obfuscation, not a realistically hardened APK

## [0.1.1] — 2026-10-19

Foundation Hardening. The Smali fallback — the mechanism that keeps a finding
verifiable when decompilation fails — had never run, for any APK.

### Fixed

- **The Smali fallback never worked for any APK.** `smali_path()` searched for the
  per-dex directories *inside* `smali/`, but Apktool writes `classes2.dex` to
  `smali_classes2/`, a sibling rather than a child. Single-dex APKs failed too: the
  glob only ever matched subdirectories of `smali/` whose name began with "smali", and
  a normally decoded APK has none, so the function returned `None` for every class.
  A source request reported "No source" while the decoded Smali sat in the workspace,
  with no error recorded anywhere. The directories are now discovered as siblings
  under the output directory and searched in sorted order, so a class present in two
  dexes resolves to the same file on every call.
- **A hostile class name could crash the analysis.** The name was joined into a path
  without validation, so `....//....//etc/passwd` raised `ValueError` from
  `Path.with_suffix()`. A name that is not a class name now returns `None`, which is
  what the rest of the architecture expects: backend failure is a value, not an
  exception.

### Added

- Unit coverage for the three Apktool directory layouts, deterministic resolution of
  duplicate class names, and eight path-traversal payloads
- An integration test that analyses a real two-dex APK with JADX made unavailable, so
  the Smali fallback is the thing actually under test
- A check that the fixture-fetching script and the integration tests agree on the
  fixture list, in both directions — a test that skips because its fixture was never
  fetched is a regression guard that has silently disappeared

### Engineering

- 244 tests (192 fast, 52 integration), up from 204
- First-party coverage 89.1% (1523/1709 lines), up from 87.8%. The Apktool adapter
  went from 82.7% to 94%
- `mypy` strict, `ruff` lint and format, GitHub Actions green on Python 3.12 and 3.13

### Known issues

- **An empty backend path does not disable that backend**, although `settings.py`
  documents that it should. The path is skipped and a `PATH` lookup follows. Recorded
  as a strict `xfail` test so it cannot be forgotten; see the execution report.

## [0.1.0] — 2026-10-14

Phase 1 — Functional Foundation. A working static analysis pipeline that operates with
every language model switched off.

### Added

- **APK ingestion** — ZIP and Android-marker validation, streamed SHA-256 content
  addressing, DEX / native library / signature inspection
- **JADX backend** — Java decompilation, class indexing, method body extraction by
  brace matching, and detection of JADX's decompilation-failure placeholders
- **Apktool backend** — manifest parsing (package, versions, permissions, components,
  exported state) and Smali navigation as the fallback when decompilation fails
- **Androguard backend** — the symbol index: classes, methods, fields, cross-references
  recovered by walking bytecode, and string constants
- **Unified analysis model** — every fact carries provenance: source tool, tool version,
  APK hash and code location
- **Evidence levels** — `verified` / `lead` / `insufficient`, so an ungrounded claim can
  never be presented as a confirmed finding
- **Storage and search** — SQLite with FTS5 full-text search over indexed symbols
- **CLI** — `analyze`, `projects`, `classes`, `methods`, `source`, `search`, `manifest`,
  `xrefs`, `backends`
- **REST API** — the same analysis core over FastAPI, including upload, query and
  report export endpoints
- **Report export** — JSON and Markdown, with backend errors surfaced rather than
  omitted
- **Bundled demo application** — built from smali sources in `examples/demo-app/`,
  rebuildable with `scripts/build-demo-apk.sh`, so a stranger can analyse something
  immediately after cloning
- **Generated demo recordings** — `docs/assets/demo.gif` and `demo-quick.gif`,
  rendered from a live run of the real CLI by `scripts/render-demo.py`. Not staged:
  the capture script reads the project id its own run produced, so the recording
  cannot show a value a reader could not reproduce

### Engineering

- 204 tests, 88% coverage on first-party code
- `mypy` strict, `ruff` lint and format, all green in CI on Python 3.12 and 3.13
- Docker image with JADX, Apktool and Androguard verified to run at build time
- Dependency audit via `pip-audit` over the resolved lock file
- Installation and architecture documentation, every install command verified against
  a fresh clone
- No APK, DEX or native library is committed to the repository

[Unreleased]: https://github.com/gg320324492-lgtm/dexatlas/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/gg320324492-lgtm/dexatlas/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.2.0
[0.1.3]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.3
[0.1.2]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.2
[0.1.1]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.1
[0.1.0]: https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0
