# M6 层级 2 失败模式分析（DexAtlas 配置）

**状态：已完成。本文是对 [m6-level2-traces.json](m6-level2-traces.json) 全部 183 条 trace 的纯本地重算与逐题归因，未调用任何模型，未改动代码与题集。所有数字可按 §10 的方式复算；根因假设均标注「假设，需 X 验证」。**

本文回答一个问题：层级 2 真实模型批次（见 [m6-level2-real.md](m6-level2-real.md)）里，DexAtlas 配置三轮合计 24/60（40.0%），距离 80% 验收线（48/60）还差 24 题次——这些失败具体败在哪一步，哪些能靠改 agent 修复，哪些是测量或题目本身的结构问题。

## 1. 结论先导

DexAtlas 的 36 个失败题次中，**没有一次是「编造了被禁止的事实」**：183 条 trace 里三配置的 `must_not_contain` 违例均为 0。失败集中在四种可命名的模式：

| 排名 | 失败模式 | 题次 | 一句话根因 |
|---|---|---:|---|
| 1 | 否定/缺席题的回答形态 | 9 | `check()` 对 `expect_empty` 题见任何 finding 即判负；agent 把「没有 receiver / 没有 caller」写成了结论 |
| 2 | 计数题的判分形状 | 7 | `expect_count` 数的是 findings 条数，不是题面问的数量；agent 的汇总式回答与过程注记都算进 findings |
| 3 | 作答枚举不完整 | 6 | 问「是否同描述符/返回什么」时只答了问到的两个方法，没有枚举判分要求的第三个方法或矛盾两侧 |
| 4 | 检索词不命中 | 5 | 字符串常量题按语义词（api、URL、http）检索，常量本身不含这些子串，检索层返回空 |

建议方向：**先改 agent 的回答契约（否定题空结论、计数题逐项成条、过程注记移出结论、方法身份必须带完整 JVM 描述符），再补一个「资源 → 声明文件」查询工具**。这五项都是 prompt/工具层修复，不动题集与判分。按 §8 的逐项账目，全部落地理论上限 53/60（88.3%）；保守口径（不计最不确定的枚举粒度项）47/60（78.3%）。**但 `partial.*` 两题（6 题次）在当前 comparison harness 下无法被如实回答通过（§5.6、§9），需要主会话决策：修订 harness/判分说明，或在验收口径中说明这两题的测量无效。**

## 2. 数据与判定口径

- 数据：[m6-level2-traces.json](m6-level2-traces.json)，183 条 = 三配置 ×（20 题 × 3 轮 + 1 条冒烟）。冒烟（q001 第 4 条记录）三轮统计之外，本文所有「题次」均指 60 个三轮题次。
- 判定：`benchmarks/model.py` 的 `check()`（`benchmarks/model.py:430`）。与本文相关的三条规则：
  - `expect_empty` 题：answer.findings 非空即判负（`benchmarks/model.py:464-465` `anchor: if task.expect_empty:`）；
  - `must_contain`：每项都要出现在某条 finding 或 answer 全文里，子串大小写不敏感（`benchmarks/model.py:485-488` `anchor: for wanted in task.must_contain:`）；
  - `expect_count`：**findings 的条数**必须等于期望值（`benchmarks/model.py:525` `anchor: if task.expect_count is not None and len(answer.findings) != task.expect_count:`）。
- 判分输入：`answer_from_result` 把被测系统的 conclusions 变成 findings（`benchmarks/comparison/adapters.py:26`）。A/B 的断言一律 `grounded=False`（`benchmarks/comparison/systems.py:244`）；DexAtlas 的断言来自证据记录，只有 BEHAVIOUR 类记录进入结论（`benchmarks/comparison/systems.py:543-545` `anchor: EvidenceKind.BEHAVIOUR`）。
- 总成绩复核：A 24/60、B 18/60、DexAtlas 24/60，与 [m6-level2-real.md](m6-level2-real.md) §2 一致；失败题次 A 36、B 42、DexAtlas 36。

## 3. DexAtlas 36 题次失败的判负原因分解

按 `check()` 的判负分支机械归类（同一失败只落一类）：

| 判负原因 | 题次 | 涉及题目 |
|---|---:|---|
| `must_contain` 缺项 | 20 | q029×3、q041×3、q046×3、q066×3、q083×3、q034×2、q039×2、q022×1 |
| `expect_empty` 但有 findings | 9 | q071×3、q077×3、q067×3 |
| `expect_count=3` 得 4 | 3 | q010×3 |
| `expect_count=2` 得 1 | 3 | q050×3 |
| `expect_count=1` 得 3 | 1 | q025 的 1 轮 |

对照 A/B 的同口径分解：A = must_contain 24 + expect_empty 3 + 计数形状 9；B = must_contain 27 + expect_empty 6 + 计数形状 9。**「计数题形状不符」是三配置共有的系统性现象；「否定题写成 findings」DexAtlas 最重（9 对 A 3、B 6），因为 A/B 的回答契约本来就倾向输出空 conclusions + limitations。**

## 4. 失败模式分类表

| 模式 | 频次 | 典型题 | 根因（事实/假设） |
|---|---:|---|---|
| FM-1 否定/缺席题回答形态 | 9 | q071、q077、q067 | 事实：`expect_empty` 题见 findings 即负（`benchmarks/model.py:464-465`）；agent 的回答契约把直接回答都写成结论。适配层文档写明「"there is none" 应放 limitations」（`benchmarks/comparison/adapters.py:33` `anchor: marker. Saying "there is none" belongs`），agent 配置未遵循这一约定 |
| FM-2 计数题判分形状 | 7 | q010、q050、q025 | 事实：`expect_count` 比 findings 条数（`benchmarks/model.py:525`）。q010 多出的第 4 条是「分析已完成」过程注记；q050 把「2 个 DEX」写成 1 条 |
| FM-3 作答枚举不完整 | 6 | q041、q046 | 假设，需 prompt 调整后重跑验证：模型按问句字面回答（是否相同/返回什么），未枚举判分要求的全部限定名或矛盾两侧 |
| FM-4 检索词不命中 | 5 | q029、q034 | 事实：常量 `sk_live_2f8a91c4e7b3`（examples/demo-app/smali/com/example/demo/MainActivity.smali:21）不含 "api"/"key" 子串；telemetry URL 不含 "http" 以外的语义词。检索按语义词走，返回空 |
| FM-5 harness 未移除后端 | 3 | q066 | 事实：comparison harness 只用 `Configuration.FULL` 分析样本（`benchmarks/comparison/run.py:222`），任务声明的 `NO_JADX`/`NO_APKTOOL` 在这条链路上未生效 |
| FM-6 工具缺口 | 3 | q083 | 事实：agent 的工具集没有「资源 → 声明文件」查询；search_symbols 能给出 app_name 的值，给不出 res/values/strings.xml |
| FM-7 格式不符 | 2 | q039（1 轮）、q022（1 轮） | 事实：回答用了 `java.lang.String` 签名形态或省略了包前缀，判分要求完整 JVM 描述符/全限定名 |
| FM-8 基础设施 | 1 | q039（1 轮） | 事实：`error="the model endpoint did not answer in time"`，184.4 秒超时，按规程计入失败未重试 |

另有两例**模型侧退化输出**（不计入上述根因， because 题目本身也因 FM-2 判负）：q050 的 1 轮拒答（"I'm sorry, but I cannot assist with that request."）和 1 轮把 MiniMax 控制标记泄漏进回答。这是模型生成风险，不是 agent 链路问题。

## 5. 代表题深入分析

每题按「模型实际答了什么 → 期望是什么 → 差在哪一步」记录。

### 5.1 q010 `manifest.permission.count-obfuscated`（三配置全败）

- 实际（DexAtlas）：4 条 findings——①「3 个权限：ACCESS_FINE_LOCATION、READ_PHONE_STATE、SEND_SMS」（1 条列全）；②包名/版本；③组件清单；④「分析已完成、未截断」过程注记。
- 期望：恰好 3 条 findings（`benchmarks/tasks/manifest.py:171` `anchor: expect_count=3`），题面无 `must_contain`。
- 差在哪：**内容全对，形状不对**。3 个权限被写进 1 条，过程注记又占 1 条。A/B 只输出 1 条汇总，同样判负。这是 FM-2 的原型：判分按 findings 计数，模型按自然语言组织回答。

### 5.2 q071 `unanswerable.crypto-digestof-has-no-callers`（A、B 全过，DexAtlas 全败）

- 实际（DexAtlas）：如实且完整——「索引中无任何 call site 指向 Crypto.digestOf，call_site_count=0、call_edge_count=0；项目状态 complete、无截断；另有一条未证实的线索：存在独立字符串常量 'digestOf'，可能与反射调用有关（未确认）」。
- 期望：**零 findings**；提到 MainActivity/NetworkClient/SyncService/Crypto.sign/Crypto.obfuscate 任一即判负（`benchmarks/tasks/partial.py:175` `anchor: expect_empty=True`）。
- 差在哪：DexAtlas 的回答里没有违禁名字，事实也全部有据，但 4 条 findings 触发 `expect_empty` 判负。A/B 通过的方式是 conclusions 留空、把「未发现调用者」写进 limitations。**这是 agent 回答契约与判分语义的冲突，不是分析错误。**

### 5.3 q077 `unanswerable.demo-declares-no-receiver`（三配置全败）

- 实际：三配置都答「没有声明 receiver」（A/B/DexAtlas 的措辞均如此）。
- 期望：零 findings（`benchmarks/tasks/partial.py:238`，无 `must_not_contain`）。
- 差在哪：三配置都把否定回答写成了 findings。A/B 在其余否定题（q071）上会留空 conclusions，这道题却没留——说明「否定 → 空 conclusions」的行为不稳定，靠 prompt 固化才有意义。

### 5.4 q029 `strings.api-key.demo`（三配置全败）与 q034 `strings.telemetry-url.obfuscated`（DexAtlas 1/3）

- 实际：DexAtlas 三轮都检索 "api"/"key"，只命中 `api_key` 标签与 `https://api.example.com/v1`，未见到密钥常量，于是回答「未发现凭证样式的值」；q034 败轮检索 "http"/"URL" 返回空，答「无法确定端点」。
- 期望：回答包含完整常量 `sk_live_2f8a91c4e7b3` / 完整 URL `https://telemetry.example.net/collect?d=`。
- 差在哪：**检索词与目标常量无子串交集**。常量在 MainActivity.smali:21，检索层按行做子串匹配，"api" 匹配不到第 21 行。q034 的通过轮走了 `search_symbols → get_class_source`，读到类源码后拿到了完整 URL——这直接支持「先读类源码/按字面前缀检索」的修复方向（假设，需重跑验证）。

### 5.5 q041 `overloads.method-identity.descriptor-distinguishes`（三配置全败）与 q046 `ambiguity.declared-type-contradicts-body`（三配置全败）

- 实际（DexAtlas，q041）：三轮都答「是，digestOf 与 obfuscate 的描述符相同，均为 (Ljava/lang/String;)Ljava/lang/String;」——就问句字面而言是对的；但三轮都未提及 sign。q046：答「onBind 返回字符串字面量 "com.example.demo.provider"」（部分轮补了一句 declared return type is IBinder）。
- 期望：q041 需同时含三个方法的完整 JVM 描述符限定名（`benchmarks/tasks/methods.py:72` `anchor: must_contain=(`）；q046 需同时含 `Landroid/os/IBinder;` 与 `com.example.demo.provider`（`benchmarks/tasks/methods.py:159`）。
- 差在哪：**找到了、推理也对，但枚举粒度不满足判分**。q041 差「第三个方法」，q046 差「描述符的 JVM 形式」（说了 IBinder 没说 `Landroid/os/IBinder;`）。A 在 q041 上因源码形态是 `String sign(String, String)` 永远给不出 JVM 描述符；B 能给全限定名但枚举不稳。这类题三配置全败，属于「问句邀请短回答、判分要求全枚举」的粒度错位。

### 5.6 q066 `partial.no-jadx-the-failure-is-recorded`（三配置全败）与 q067 `partial.no-apktool-there-is-no-manifest`（A 3/3，B、DexAtlas 全败）

- 实际（DexAtlas，q066）：「分析未记录反编译器缺失：missing_backends 为空，JADX 1.5.2 在工具版本列表中，Java 源码带 JADX 溯源成功取得」。q067：get_manifest 成功，答出完整 manifest 内容（包名、权限、组件）。
- 期望：q066 的回答需含 "jadx" 与 "not_installed"（`benchmarks/tasks/partial.py:102` `anchor: expect_backend_failure=("jadx",)`）；q067 期望零 findings（`benchmarks/tasks/partial.py:117` `anchor: expect_backend_failure=("apktool",)`）。
- 差在哪：**harness 没有真的移除后端**。comparison 链路只用 `Configuration.FULL` 建分析（`benchmarks/comparison/run.py:222`），任务声明的配置只作为字段随题下发，没有任何消费者据此禁用后端。于是 q066 的真实答案是「没有缺失」，q067 里 manifest 真实存在——DexAtlas 的回答在事实层全对，判分层全错。A 通过 q067 的方式是「检索没找到所以什么都没说」，同样不是题目想要的「知道阅读器缺失」。**这两题 ×3 轮 = 6 题次在当前测量下不构成对 agent 能力的有效测量。**

### 5.7 q083 `wheresource.app-name-resource-file.demo`（A 3/3，B、DexAtlas 全败）

- 实际（DexAtlas）：三轮都找到 `app_name = DexAtlas Demo`（E-0003 有据），但明确说「现有证据不能给出声明它的资源文件」。
- 期望：回答含 `res/values/strings.xml`（`benchmarks/tasks/wheresource.py:67` `anchor: must_contain=("app_name", "res/values/strings.xml")`），且不得提 AndroidManifest.xml（`benchmarks/tasks/wheresource.py:68` `anchor: must_not_contain=("AndroidManifest.xml",)`）。
- 差在哪：**工具缺口**。符号索引里有资源的名字与值，没有「声明文件」字段；agent 也没有可调用的资源文件定位查询。A 靠直接读样例文件树命中。DexAtlas 的回答诚实且无违例，是能力边界而非幻觉。

### 5.8 q022 `xrefs.handler-handle-callers`（DexAtlas 2/3，A、B 全败）与 q039 `overloads.method-identity.crypto-sign`（B 3/3，DexAtlas 1/3，A 全败）

- 实际：q022 败轮答「`HandlerFactory.dispatch(Handler, String)` 通过 `handler.handle(str)` 调用 handle」——调用链找对了，但没写全限定名 `com.example.wide.HandlerFactory.dispatch`（`benchmarks/tasks/xrefs.py:88`）。q039 的 1 个败轮用 `java.lang.String` 签名形态作答，另 1 轮是端点超时（FM-8）。
- 期望：完整限定名/完整 JVM 描述符（`benchmarks/tasks/methods.py:41` `anchor: must_contain=(`）。
- 差在哪：**格式纪律**。检索与推理都对，输出形态不满足判分的子串匹配。B 在 q039 全过的原因正是结构化符号索引天然带 JVM 描述符形态。

## 6. agent 独有失败 vs 三配置共有失败

逐题通过数（每格 = 3 轮中通过数，A/B/D）：

| 任务 | A | B | D | 判读 |
|---|---:|---:|---:|---|
| ambiguity.declared-type-contradicts-body | 0 | 0 | 0 | 共有：枚举粒度 |
| manifest.permission.count-obfuscated | 0 | 0 | 0 | 共有：判分形状 |
| multidex.dex-file-count | 0 | 0 | 0 | 共有：判分形状 |
| overloads.method-identity.descriptor-distinguishes | 0 | 0 | 0 | 共有：枚举粒度 |
| partial.no-jadx-the-failure-is-recorded | 0 | 0 | 0 | 共有：harness 未移除后端 |
| strings.api-key.demo | 0 | 0 | 0 | 共有：检索不命中 |
| unanswerable.demo-declares-no-receiver | 0 | 0 | 0 | 共有：否定题形态 |
| **partial.no-apktool-there-is-no-manifest** | 3 | 0 | 0 | **DexAtlas 独有败**（A 靠空答过） |
| **unanswerable.crypto-digestof-has-no-callers** | 3 | 3 | 0 | **DexAtlas 独有败**（回答太完整反而触发 expect_empty） |
| **wheresource.app-name-resource-file.demo** | 3 | 0 | 0 | **DexAtlas 独有败**（工具缺口；A 靠文件树直读） |
| overloads.method-identity.crypto-sign | 0 | 3 | 1 | DexAtlas 落后 B：A 的源码形态给不出描述符，B 的符号索引天然带 |
| strings.telemetry-url.obfuscated | 0 | 0 | 1 | DexAtlas 更好（1 轮走通 get_class_source） |
| xrefs.crypto-sign-callers | 0 | 0 | 3 | DexAtlas 更好：find_callers 直答 |
| xrefs.crypto-sign-call-site-count | 0 | 0 | 2 | DexAtlas 更好 |
| xrefs.handler-handle-callers | 0 | 0 | 2 | DexAtlas 更好 |
| 其余 5 题（package/name-strings/exported×2/resources.app-name） | 3 | 3 | 3 | 三配置全过 |

要点：

1. **三配置共有失败 7 题 ×3 轮 = 21 题次**，占 DexAtlas 失败的 58%。这些题 A/B/DexAtlas 全败，主要是判分形状、枚举粒度、检索不命中与 harness 缺陷——**换配置救不了，改判分口径、改 prompt/工具或改题集才有效**。
2. **DexAtlas 独有失败 3 题 = 9 题次**，全部属于「agent 的回答契约与判分语义冲突」或「工具缺口」，无一是检索或推理错误。这 9 题次是 agent 侧最直接的改进空间。
3. DexAtlas 在 xrefs 三题上显著优于 A/B（A/B 合计 0/27，DexAtlas 7/9），说明 agent 链路对调用关系类问题是真实增益。
4. A/B 逐轮结果完全一致（8/8/8、6/6/6；温度 0 + 确定性检索），DexAtlas 9/8/7 的波动来自 agent 循环本身的路径差异（工具选择顺序），不是采样温度。
5. 成本：三轮 token A 95,573 / B 45,913 / DexAtlas 711,617（约 7.4×A）；耗时 220.9s / 145.0s / 812.0s。

## 7. false_positive 偏高的来源

聚合重算（含通过题）：A 11/31 = 35.5%，B 19/35 = 54.3%，DexAtlas 75/152 = 49.3%（报告逐轮 47.1%/55.1%/50.0%）。

分解 DexAtlas 的 75 个 FP 断言：

1. **约 64 项是有证据支撑的（grounded=true）**。它们被判为 FP 只因所在题判负——典型如 q071 的「call_site_count=0」（真话）、q077 的「manifest 无 receiver」（真话）、q067 的包名/权限/组件（真话）。**DexAtlas 的 FP 率高，主要不是「说错」，而是「在判负的题上说了太多真话」。**
2. **约 11 项无支撑（ungrounded）**，几乎全部是「分析已完成/未截断/无缺失后端」这类过程注记（q010、q015、q016、q025、q029、q050、q066、q067 均有出现）。这类注记被证据层标注为「不是对分析的观察」，却仍进入结论列表。
3. **`must_not_contain` 违例为 0**：没有任何配置把工具返回里的 APK 内文当成指令、也没有编造被禁止的符号名。工具返回的呈现方式（结构化视图 + untrusted-input 提示）没有诱发错误断言。
4. A/B 的 FP 率不可与 DexAtlas 直接对比：A/B 的断言恒为 `grounded=False`（`benchmarks/comparison/systems.py:244`），其 unsupported_assertion_rate 恒为 100%，FP 分子实际是「判负题上 emitted 的结论条数」。A 在 12 个失败题次中 8 个连结论都没发（0 断言），B 也多为单结论——A/B 的低断言量本身压低了它们的 FP 分母。

**与工具呈现方式的关系**：未发现关联。FP 的来源是 agent 的**回答组装**——把过程注记、上下文补充、对是否题的直接回答都写进 conclusions——而不是工具返回内容的失真。

## 8. 改进方向建议

每条注明改动对象、覆盖题次、预期影响与验证方式。除第 6 条外都不改题集、不改判分。

| # | 改什么 | 覆盖题次 | 预期影响 | 验证方式 |
|---|---|---|---|---|
| 1 | **改 prompt（否定题契约）**：判断为「不存在/没有」时输出空 conclusions，否定句只进 limitations/正文 | q071×3、q077×3 = 6 | 24→30（40.0%→50.0%） | 只改 agent 指令，重跑冻结 20 题 |
| 2 | **改 prompt（计数题契约）**：问「多少」时每个被数对象单独成一条 finding；过程注记一律不进 conclusions | q010×3、q050×3、q025×1 = 7 | 30→37（→61.7%） | 同上，重点观察 q010/q050/q025 |
| 3 | **改 prompt + 停止策略（检索纪律）**：字符串/URL/凭证类题先按字面前缀（sk_、https://、api）检索并 `get_class_source` 读类源码，再下「不存在」结论 | q029×3、q034×2 = 5 | 37→42（→70.0%） | 重跑 q029/q034；q034 已有 1 轮走通该路径，可作对照 |
| 4 | **改工具（资源出处）**：新增「资源名 → 声明文件」查询，或让 search_symbols 对资源符号附声明文件字段 | q083×3 = 3 | 42→45（→75.0%） | 加工具后重跑 q083；确认不误报 AndroidManifest.xml（must_not_contain） |
| 5 | **改 prompt（格式纪律）**：方法身份/调用者回答必须用完整 JVM 描述符与全限定名 | q039×1、q022×1 = 2 | 45→47（→78.3%） | 重跑 q039/q022 |
| 6 | **改基础设施（超时重试）**：端点超时按预算允许一次重试，或调大时限 | q039×1 = 1 | 47→48（→80.0%） | 仅影响基础设施失败计数，需在报告口径中注明 |
| 7 | **改 prompt（枚举粒度，不保证）**：比较/矛盾类问题要求枚举类内全部相关方法、并陈「声明类型 vs 实际返回」 | q041×3、q046×3 = 6 | 48→54（→90.0%，上限） | 重跑并人工核对是否真的枚举；三配置全败说明这是模型作答粒度问题，不保证可达 |
| 8 | **改 harness/题集（需主会话决策）**：让 `task.configuration` 真正生效，或在题集文档注明 partial.* 在 comparison 链路的测量无效 | q066×3、q067×3 = 6 | 视口径而定 | 修订后重跑 partial.*；按冻结纪律版本化并说明理由 |

**账目小结**：1–5 全部落地 = 47/60（78.3%），仍差 1 题次到 80% 线；加上第 6 条（重试）恰好 48/60 = 80.0%；第 7 条若见效可到 54/60，但三配置全败的历史使它最不确定。第 8 条不改，partial.* 的 6 题次始终是测量的盲区。

## 9. 当前架构下可能无法达标的诚实清单

- **q066、q067（6 题次）**：harness 未移除后端，agent 如实回答必判负，如实回答是正确行为。不改 harness/题集，这两题不该计入 agent 的达标分母。
- **q041、q046（6 题次）**：三配置全败，问句粒度与判分粒度错位。prompt 或可缓解（第 7 条），但「模型是否稳定输出全枚举」未经证实。
- **q050（3 题次）**：期望 2 条 findings，而「2 个 DEX 文件」最自然的回答是 1 条。第 2 条契约（逐项成条）能否稳定触发，需重跑验证；若不能，需要判分口径说明。
- **q077（3 题次）**：第 1 条契约能修，但 A/B 在这题上也没留空 conclusions——「否定 → 空结论」对模型不是默认行为，需验证其稳定性。
- **模型侧风险**：q050 出现过 1 轮拒答与 1 轮控制标记泄漏（MiniMax-M3.1-Flash）。换模型代次可能改变全部数字，任何「达标」结论都绑定在本批次模型上。

## 10. 复算方式

本文所有计数来自对 trace 的机械重算，可用等价脚本复核：

```bash
uv run --no-sync python - <<'PY'
import json
traces = json.load(open("docs/benchmarks/m6-level2-traces.json", encoding="utf-8"))["traces"]
for system in ("A", "B", "DexAtlas"):
    rows = [t for t in traces if t["system"] == system]
    print(system, "pass", sum(t["passed"] for t in rows), "/", len(rows))
    print("  fails by task:", sorted(t["task_id"] for t in rows if not t["passed"]))
    asserts = [a for t in rows for a in (t["result"].get("assertions") or [])]
    fp = [a for t in rows if not t["passed"] for a in (t["result"].get("assertions") or [])]
    print("  assertions", len(asserts), "grounded", sum(a["grounded"] for a in asserts),
          "FP", len(fp))
PY
```

逐题的「实际回答 / 期望 / 差异」均摘自 trace 的 `result.findings`、`result.answer_text`、`result.assertions` 与 `result.tool_calls` 字段原文；判定条件摘自 `benchmarks/tasks/` 各题定义与 `benchmarks/model.py:430` 的 `check()`。
