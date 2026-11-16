# M6 层级 2 —— 三轮完整复测失败模式分析（零成本，只读已落盘 trace）

**状态：本文只分析 [m6-level2-retest3-traces-r1.json](m6-level2-retest3-traces-r1.json)、[m6-level2-retest3-traces-r2.json](m6-level2-retest3-traces-r2.json)、[m6-level2-retest3-traces-r3.json](m6-level2-retest3-traces-r3.json) 三份已落盘 trace 中 DexAtlas 配置的 11 条未通过记录，不调用任何模型 API，不消耗预算。结论服务于下一步决策：哪些失败可修复、哪些是模型方差、修复的预期收益是多少。判分口径与 [m6-level2-retest3.md](m6-level2-retest3.md) 一致。**

三轮结果：DexAtlas 逐轮 17/20、15/20、17/20，合计 49/60 = 81.7%，未达验收线（每轮 ≥80% 且三轮合计 ≥90%）。

## 1. 失败分类总览

把 11 条未通过记录按「判分时答案里有什么」分成三类：

| 类别 | 记录 | 轮次 |
|---|---|---|
| **A. 降级空响应**（模型返回空消息：`completion_tokens=0`、`answer_text` 空、`error` 空） | `partial.no-apktool-there-is-no-manifest`、`strings.api-key.demo` | r1 / r2 |
| **B. 单题预算耗尽**（24,000 闸触发，`error` 写明 token 花费） | `resources.app-name.demo`（24,639）、`multidex.dex-file-count`（26,438） | r2 / r3 |
| **C. 答了但判分不过**（有实质回答，未满足判分要求） | `overloads.method-identity.descriptor-distinguishes`、`strings.api-key.demo`、`manifest.permission.count-obfuscated`、`partial.no-apktool-there-is-no-manifest` | r1–r3 |

三类各占 2、2、7 条。**C 类是主体，且集中在 4 道题上**；A、B 两类是执行层故障，不是解题失败。

## 2. C 类逐题分析（可修复性核心）

### 2.1 `overloads.method-identity.descriptor-distinguishes`（r1、r2 失败，r3 通过）

- **判分要求**：答案必须同时含三个完整方法引用——`digestOf`、`obfuscate`、`sign`（`must_contain` 三个全文）。
- **失败形态**：agent 只比较了 `digestOf` 与 `obfuscate`（二者描述符确实相同），得出「yes, identical」，**从未提到 `sign`**——而 `sign` 的双参描述符才是这道题要的「区分者」。
- **r3 通过形态**：逐个列出三个方法的描述符，并明确说 `sign` 不与另两者共享。
- **根因**：题面问「Do digestOf and obfuscate have the same descriptor?」，模型按字面回答了「是」，但判分器要求覆盖全部三个方法——这是**回答宽度不足**，不是检索失败。agent 两轮都正确检索到了 `Crypto.smali`。
- **可修复性**：中。可以在 agent 的作答指引（系统提示的 wrap-up 段）中加一条「涉及方法身份/重载的题，枚举同类全部方法而不是只回答被点名的两个」；但这是提示词层面的软修复，不保证每轮触发。

### 2.2 `strings.api-key.demo`（r1 答错、r2 空响应、r3 通过）

- **判分要求**：答案含完整常量 `sk_live_2f8a91c4e7b3`。
- **r1 失败形态**：agent 搜索 `api key`，词法检索命中**诱饵常量 `api_key`**（`MainActivity.smali` 第 20 行的 `const-string v0, "api_key"`），于是回答「包含一个值为 api_key 的常量」——没提真正的密钥（第 21 行 `sk_live_2f8a91c4e7b3`）。
- **本地复现（零成本）**：在当前树上对 demo.apk 直接调 `search_symbols`：查询 `api key` 只返回诱饵 `api_key`（词法匹配把 `api_key` 拆成 api+key 两词命中）；查询 `sk_live`/`live`/`2f8a91` 都能返回真密钥；**完整常量枚举（63 条）里 `sk_live_2f8a91c4e7b3` 在列**，但枚举兜底只在词法检索**完全为空**时才触发（`src/dexatlas/mcp/tools/symbols.py` 的 `if not page` 链）——诱饵命中**遮蔽**了枚举兜底。
- **根因**：**诱饵遮蔽**。修复 2（整字面量契约）让密钥变得可检索，但没有解决「词法检索已有命中时不再枚举常量池」的遮蔽问题。
- **可修复性**：高。候选修复（代码层，非提示词）：当查询像「找密钥/凭证」这类任务时，把常量池枚举与词法命中**并集返回**；或在 string 类命中旁附带「同池其他高熵常量」。r3 通过是模型方差（agent 恰好也搜了别的词），不是代码变好。

### 2.3 `manifest.permission.count-obfuscated`（r2、r3 失败，r1 通过）

- **判分要求**：`expect_count=3`——答案的 **findings 恰好 3 条**（三个 permission），不是「答案里提到 3 个 permission」。
- **失败形态**：agent 三轮都正确数出了 3 个 permission（ACCESS_FINE_LOCATION、READ_PHONE_STATE、SEND_SMS），但 r2/r3 把 package、components 等其他 manifest 事实**也写成了 finding**，共 8 条 → `len(findings) != 3` 判负。
- **r1 通过形态**：findings 恰好只有 3 条 permission。
- **根因**：**findings 纪律**——count 型题的「证据条数」就是答案，agent 把「顺带看到的 manifest 信息」也升级成了结论。这不是检索或理解错误，是输出组织问题。
- **可修复性**：高。候选修复：agent 提示的 wrap-up 段加「count 型问题的回答只保留与计数直接相关的 findings」；或在 `sufficiency.py` 的作答约束里对 count 题单独声明。同样是软修复。

### 2.4 `partial.no-apktool-there-is-no-manifest`（r1/r2 空响应，r3 答错方向）

- **判分要求**：答案必须记录 apktool 后端失败（`expect_backend_failure=("apktool",)`，backend 名 + 失败短语出现在同一 finding 或 prose 里），且**不得出现** `com.example.demo`（`must_not_contain`）。
- **r1/r2 形态**：降级空响应（A 类），agent 调了 `get_manifest`（ok=False）后没有产出任何文字。
- **r3 形态**：agent 从 DEX 索引里推出「code namespace is com.example.demo」——**恰好踩中 `must_not_contain`**，判负。这道题的正确答案是「没有 manifest，包名无从读起；apktool 未安装、失败已记录」。
- **根因**：两层。执行层是 A 类空响应；语义层是模型把「从 DEX 推出的命名空间」当成了「manifest 声明的包名」——正是这道题要防的混淆。
- **可修复性**：中。空响应部分见 §3；语义部分可在提示中强调「partial 题先报告后端失败状态，再回答可见部分，不要用索引推导值替代被问的来源」。

## 3. A/B 类执行层故障

### 3.1 A 类：降级空响应（2 条）

- 形态：`completion_tokens=0`、`answer_text` 空、`error` 空、工具调用都 ok。这是 MiniMax 端点偶发的**空 assistant 消息**（温度 0 下仍会出现）。
- 现有处理链：`orchestrator._finish` 把空回答记为 COMPLETED、0 findings；`systems.py` 以 `failed = not answer_text` 标记失败，`error` 留空。
- **可修复性**：高，且是**执行层修复**——在 provider 解析处（`openai_compat.parse_response`）把「content 为空且无 tool_calls」识别为 `ProviderError(retryable=True)`，走既有的 `_ask` 重试通道。这不改判分、不改题面，只把「端点抽风」从「解题失败」里摘出来。r1/r2 的这两条若被重试救回，三轮合计变 51/60（85.0%），r2 变 16/20（80.0% 达单轮线）——但合计仍低于 90%，**单靠修 A 类不能关闭 B1**。

### 3.2 B 类：单题预算耗尽（2 条）

- `resources.app-name.demo` r2（24,639/24,000）与 `multidex.dex-file-count` r3（26,438/24,000）：同一题在其他轮通过时 prompt 分别为 20,943–22,384 与 26,438–31,376——**multidex 在通过的轮次里 prompt 本来就接近或超过 24k**，说明这道题的检索路径天然接近闸值。
- **可修复性**：低-中。multidex 的 prompt 体量来自多次 `list_dex_files`/大响应，压 prompt 需要动检索策略；放宽单题闸则与预算方案（24k 取「上轮通过题实测最大 22,776 之上」）冲突。B 类两条分属不同题、不同轮，是方差性越线，不是系统性超支。

## 4. 修复收益测算（零成本推算，不外推为承诺）

| 修复 | 可挽回记录 | 三轮合计变化 | 是否足以关闭 B1 |
|---|---|---|---|
| A 类空响应重试（执行层） | r1 partial、r2 api-key | 49→51（85.0%），r2 达单轮线 | **否**（合计仍 <90%） |
| C2 诱饵遮蔽修复（api-key） | r1 api-key | 51→52（86.7%） | 否 |
| C3 count findings 纪律 | r2/r3 count-obfuscated | 52→54（90.0%） | **恰好到线**（若每轮也 ≥80%：r2 16/20=80%、r1/r3 17/20=85%） |
| C1 descriptor 宽度提示 | r1/r2 descriptor | 54→56（93.3%） | 是（余量 +2） |

**结论**：四项修复全部生效的理想情况下 56/60 = 93.3%，每轮 17/20、18/20、18/20 量级，可达线；但 C1/C3 是提示词级软修复，不保证触发，**修复后的重测仍有不达线风险**。A 类重试与 C2 是代码级确定性修复，建议先做这两项，再决定是否值得为 C1/C3 花一轮 35 万 tokens 的验证。

## 5. 与上轮（两轮复测）的对照

- 上轮 five-fix 后单轮 16/20=80%；本轮三轮中 r1/r3 均为 17/20，高于上轮，r2 15/20 低于上轮——**轮间方差 ±1 题量级**，与「温度 0 仍有方差」的既有局限一致。
- 上轮失败题 `unanswerable.demo-declares-no-receiver` 本轮三轮全过（修复 1 生效稳定）；`descriptor-distinguishes` 本轮 1/3——五项修复没有覆盖到的新失败面主要就是本文 §2 的四类。

## 6. 建议的下一步（供决策）

1. **先做代码级修复**（红→绿回归）：A 类空响应重试（`openai_compat.parse_response` 识别空 completion）+ C2 诱饵遮蔽（`symbols.py` 枚举兜底条件从「词法为空」改为「词法为空或查询含密钥类意图时并集返回」——需谨慎设计避免误报）。
2. **再做提示词级修复**：C1（重载题枚举全部同类方法）、C3（count 题 findings 纪律）、C4（partial 题先报后端状态）。
3. **重测**：一轮单轮复测（约 35 万 tokens）验证修复方向；若单轮 ≥18/20，再跑完整三轮（约 110 万 tokens）正式关 B1。
4. 若用户不想再投入预算：按现状把「三轮 81.7% 未达标」写入 v1.0.0 已知限制，B1 保持未关闭，发版与否另行决策。

## 局限

- 本文的「收益测算」是从既有 trace 推算的假设，不是测量；修复后重测才产生新证据。
- r3 通过的 `descriptor-distinguishes` 与 r1 通过的 `count-obfuscated` 证明这些题在当前代码上**可解**，失败是方差与输出组织问题，不是能力上限。
- A 类空响应的成因（端点侧）只能从 trace 侧面推断（completion_tokens=0、error 空），无法从本地复现端点行为。
