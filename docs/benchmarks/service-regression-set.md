# 服务回归集（Phase 3 M6 第一步：调优前冻结）

**状态：已冻结。冻结基线：commit `100b191`（main，2026-11-15）。**
本文件落实 [Phase 3 计划](../roadmap/phase3-plan.md) §5（M6）的第一条工作：
从现有题集选定并在调优前冻结一个服务回归集，覆盖权限/组件、指定方法、调用关系、
资源出处、无法回答/后端缺失五类；同时保留完整旧题集评测，防止只报成功子集。

本文件只冻结题集与判定标准，不报告任何一次运行的成绩。所有实测数字仍由
`benchmarks/run.py`、`benchmarks/comparison/run.py` 与其 committed traces 生成；
本文件不手写、不改写任何测量结果。

---

## 1. 这个集合承诺什么、不承诺什么

服务回归集是对**有限服务能力**的回归测试：在冻结的 20 道题上，DexAtlas 的
agent 配置应当能以可核查的证据完成回答，失败时给出可理解的原因。它**只代表
这 20 道题**，不外推到任意 APK、任意问题或开放式分析任务。

对外表述必须同时说明边界：

- 承诺对象是 first-party 样本上的**封闭问题集**（清单见 §3）；
- 不承诺恶意软件定性、漏洞发现、加固还原、native/动态分析；
- 模型输出仍是线索，事实性断言必须落到可解析的证据与出处；
- 完整能力边界以 [Phase 3 计划](../roadmap/phase3-plan.md) §1.1 的服务定位为准。

## 2. 选题标准

从 M3 的 92 题全集（`benchmarks/tasks/`，见 [task-set.md](task-set.md)）中选取，
每题必须满足：

1. **期望答案独立于被测工具**：答案来自样本自带的 manifest / Smali /
   `strings.xml`，第二人不开工具即可核对（全集本身已满足，此处重申）；
2. **判定客观**：`must_contain` / `expect_count` / `expect_empty` 机器可判，
   不依赖措辞或人工打分；
3. **first-party 样本**：全部落在 `examples/` 的五个样本内，无第三方 APK；
4. **答案已经过独立核对**：优先选 M3/M4 评测中判分机制已覆盖、trace 留存过的题；
5. **五类覆盖**：权限/组件、指定方法、调用关系、资源出处、无法回答/后端缺失。

在满足以上条件的前提下，同一能力点只保留代表性题量，控制真实模型批次的成本。

## 3. 冻结题集（20 题）

判定规则（对全部题目统一适用，见 `benchmarks/model.py` 的 `check()`）：
`must_contain` 为大小写不敏感的子串匹配，多条须全部命中；`expect_count` 为精确
计数；`expect_empty` 题先判「无证据」，答案带出任何证据即失败，再检查
`must_not_contain`。配置一列中 `full` 为三后端齐全，`no-apktool` / `no-jadx`
为对应后端被显式禁用的配置。

### 3.1 权限 / 组件清单（5 题）

| id | 样本 | 配置 | 问题 | 期望答案 | 判定 |
|---|---|---|---|---|---|
| `manifest.package.demo` | demo-app | full | 声明的包名？ | `com.example.demo` | must_contain；且不得出现 `com.example.multidex` |
| `manifest.permission.name-strings` | strings-app | full | 声明了哪个权限？ | `android.permission.INTERNET` | must_contain；不得含 `READ_EXTERNAL_STORAGE`/`SEND_SMS` |
| `manifest.permission.count-obfuscated` | obfuscated-app | full | 声明了几个权限？ | 3（`ACCESS_FINE_LOCATION`、`READ_PHONE_STATE`、`SEND_SMS`） | expect_count=3 |
| `components.exported.demo` | demo-app | full | 哪些组件 exported？ | `com.example.demo.MainActivity`、`com.example.demo.SyncService` | must_contain；不得含 `receiver` |
| `components.exported.obfuscated` | obfuscated-app | full | 哪些组件 exported？ | `a.a.a.a`、`a.a.b.a` | must_contain；不得含 `service a.b.a`（该 service 不导出） |

依据：各样本随库的 `AndroidManifest.xml` 与 APK 二进制 manifest（两独立读取方一致；
SDK 级别以 APK 字节为准，见 `benchmarks/tasks/manifest.py` 模块说明）。

### 3.2 指定方法定位 / 源码（3 题）

| id | 样本 | 配置 | 问题 | 期望答案 | 判定 |
|---|---|---|---|---|---|
| `overloads.method-identity.crypto-sign` | demo-app | full | Crypto.sign 的完整方法身份？ | `com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;` | must_contain |
| `overloads.method-identity.descriptor-distinguishes` | demo-app | full | digestOf 与 obfuscate 描述符是否相同？ | 三者全限定签名（digestOf、obfuscate 同描述符，sign 不同） | must_contain 三条签名 |
| `ambiguity.declared-type-contradicts-body` | demo-app | full | SyncService.onBind 返回什么？ | 签名为 `Landroid/os/IBinder;`，body 实际返回字符串 `com.example.demo.provider` | must_contain 两条 |

依据：`examples/demo-app/smali/com/example/demo/Crypto.smali`、
`examples/demo-app/smali/com/example/demo/SyncService.smali` 的 `.method` 行与
方法体。方法身份 = 类 + 名 + DEX 描述符。

### 3.3 调用关系（3 题）

| id | 样本 | 配置 | 问题 | 期望答案 | 判定 |
|---|---|---|---|---|---|
| `xrefs.crypto-sign-callers` | demo-app | full | 谁调用 Crypto.sign？ | `com.example.demo.MainActivity.onCreate` | must_contain 调用者与被调者；不得含 `NetworkClient` |
| `xrefs.handler-handle-callers` | wide-app | full | 谁调用 Handler.handle？ | `com.example.wide.HandlerFactory.dispatch`（invoke-interface） | must_contain |
| `xrefs.crypto-sign-call-site-count` | demo-app | full | 调用 Crypto.sign 的位置有几处？ | 1 | expect_count=1（调用点 ≠ 调用者数） |

依据：`examples/demo-app/smali/com/example/demo/MainActivity.smali`、
`examples/wide-app/smali/com/example/wide/HandlerFactory.smali` 中的
`invoke-*` 指令行。

### 3.4 资源出处（4 题）

| id | 样本 | 配置 | 问题 | 期望答案 | 判定 |
|---|---|---|---|---|---|
| `strings.api-key.demo` | demo-app | full | 是否含疑似活体 API key？ | `sk_live_2f8a91c4e7b3` | must_contain 整串 |
| `strings.telemetry-url.obfuscated` | obfuscated-app | full | 向哪个地址上报？ | `https://telemetry.example.net/collect?d=` | must_contain 完整 URL |
| `resources.app-name.demo` | demo-app | full | label 资源是什么？ | `app_name` = `DexAtlas Demo` | must_contain 两条 |
| `wheresource.app-name-resource-file.demo` | demo-app | full | app_name 声明在哪个资源文件？ | `res/values/strings.xml` | must_contain；不得含 `AndroidManifest.xml` |

依据：`examples/demo-app/smali/com/example/demo/MainActivity.smali` 的
`const-string` 行、`examples/obfuscated-app/smali/a/a/a.smali` 的
`const-string` 行、`examples/demo-app/res/values/strings.xml`。资源表与 DEX
字符串池是两个索引，本组覆盖两者。

### 3.5 无法回答 / 后端缺失（4 题）

| id | 样本 | 配置 | 问题 | 期望答案 | 判定 |
|---|---|---|---|---|---|
| `unanswerable.crypto-digestof-has-no-callers` | demo-app | full | 谁调用 Crypto.digestOf？ | 无调用者（空答） | expect_empty；答出任何调用者即失败 |
| `unanswerable.demo-declares-no-receiver` | demo-app | full | 是否声明 broadcast receiver？ | 未声明（空答） | expect_empty |
| `partial.no-apktool-there-is-no-manifest` | demo-app | no-apktool | 无 APK 阅读器时包名是什么？ | 无 manifest（空答） | expect_empty；错值与空串都算失败 |
| `partial.no-jadx-the-failure-is-recorded` | demo-app | no-jadx | 分析是否记录了反编译器缺失？ | 记录 `jadx` / `not_installed` | must_contain 两条 |

依据：`examples/demo-app/smali/` 无任何指令引用 digestOf；demo-app manifest 只有
activity 与 service；后端缺失是值不是异常（`ToolOutcome` 携带 `ToolError`）。
无法回答题是**计分题**：合理编造即失败，不存在「部分正确」。

### 3.6 结构补充（1 题）

| id | 样本 | 配置 | 问题 | 期望答案 | 判定 |
|---|---|---|---|---|---|
| `multidex.dex-file-count` | multidex-app | full | 样本含几个 DEX 文件？ | 2（`classes.dex`、`classes2.dex`） | expect_count=2 |

计划列出的五类是最低覆盖；此题保证 multidex 样本进入冻结集，使五个 first-party
样本全部有代表。其判定客观（计数），不引入后端顺序歧义。

**样本覆盖核对**：demo-app（多数题）、strings-app（2）、obfuscated-app（3）、
wide-app（1）、multidex-app（1）——五个样本全覆盖。

## 4. 落选说明（代表性理由）

全集 92 题中未入选的 72 题仍保留在完整评测里（M6 要求全量旧题集照常运行）。
落选的代表性理由：

- **provenance 全组（6 题）**：断言的是记录自身的 locator/哈希格式，偏工具内部
  契约，不属于对客户的服务能力承诺；完整评测继续覆盖。
- **multidex.shared-config-java/smali-comes-from-*（2 题）**：正确答案取决于
  后端读取顺序（JADX 保留最后读入的定义，Apktool Smali 按目录序取先者），
  作为「服务承诺」存在配置歧义；保留在完整评测以约束后端行为。
- **其余 where-source / ambiguity 的 no-jadx 题**：需要专用配置才有意义，冻结集
  已含 no-jadx 与 no-apktool 各一题代表后端缺失行为。
- **同能力重复题**（如 xrefs 其余 7 题、strings 其余 6 题、overloads 其余 4 题）：
  与入选题考察点重叠，冻结集控制成本；完整评测保留全部。
- **`unanswerable.apk-is-not-signed`**：好题，但其探测依赖 META-INF 证书解析
  路径，与本集其余题的探测面不同；保留在完整评测。

落选不是贬义：完整旧题集（92 题）在 M6 的每次评测中照常运行并完整报告，
服务回归集只是其中被单独承诺、单独按轮考核的子集。

## 5. 冻结纪律

1. **调优前冻结**：本清单在 M6 的任何 agent 调优、预算调整或提示词修改之前
   定稿；基线 commit `100b191`。
2. **不得删题换通过率**：未达验收线（每轮 ≥80%，三轮合计 ≥90%；空答与预算
   耗尽计失败）时，只能修正系统或**缩小并重述**服务承诺；不允许把失败题移出
   冻结集后宣布同一门槛通过。
3. **改动须版本化**：如确需增删题（例如样本失效），必须在新 commit 中记录
   变更原因、日期与影响，并重新声明基线；静默改动视为违反本纪律。
4. **完整集不裁剪**：服务回归集是完整 92 题评测的子集；对外报告必须同时给出
   完整集结果，不得只报成功子集。
5. **判定以 `benchmarks/model.py::check` 为准**：本文档的「期望答案」是其输入的
   摘要；两者冲突时以代码与 `benchmarks/tasks/` 的任务定义为准，并修订本文。

## 6. 无模型基线执行方案（本阶段执行，零模型调用）

真实模型批次未获授权前，先用确定性手段验证题集 machinery 与判定标准。

**层级 0 —— 确定性判分（零费用，本 worktree 已跑通：20/20）**
直接用 DexAtlas 的分析管线（无模型）对冻结题逐题判分。`benchmarks/run.py`
的 `--task <id>` 参数按题 id 精确过滤，支持重复传入。完整命令见附录 A；
核心形式：

```bash
export PATH="/e/Dexatlas/.scratch/backends/jadx/bin:$PATH"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
uv run --no-sync python benchmarks/run.py --task <题 id> --workspace E:/Dexatlas/.scratch/m6-freeze
```

通过标准：20/20。任一失败先查是题集 machinery 问题还是分析问题，修复须带
回归测试（项目规则 1）。该层级不产生任何模型调用与费用。

**层级 1 —— scripted provider 对照（machinery 演练，零费用）**
`benchmarks/comparison/run.py --provider scripted` 跑通三配置（A/B/DexAtlas），
证明 comparison 管线、判分与 trace 落盘可用。scripted 结果不是模型基线，
报告中必须保持其现有免责声明（见 [comparison.md](comparison.md) 头部）。

**层级 2 —— 真实模型批次（仅草案，待授权后执行）**

- 题集：完整 92 题全量 1 轮（保留完整旧题集评测）+ 冻结 20 题独立 3 轮
  （对应验收线「每轮 ≥80%、三轮合计 ≥90%」）。
- 配置：沿用既有 A/B/DexAtlas 三配置与同一模型、同一 `max_tokens` 预算；
  逐配置预算差异须在报告中显式披露（参照
  [comparison-stronger.md](comparison-stronger.md) 的披露格式）。
- 预算依据：以 [comparison-real.md](comparison-real.md) 已记录的
  `token_consumption`（DexAtlas 1,192,451；A 165,772；B 74,918 tokens / 92 题）
  为量级参考；全量 1 轮 + 冻结 3 轮（每轮约为全量的 20/92）估算总量在同一
  数量级。执行前按当时模型价格折算费用上限，写入运行记录。
- 停止条件（任一触发即停）：单题 token 超过任务预算；累计费用达到批准上限；
  同一题连续 3 次基础设施性失败（非判分失败）；API 不可用。
- 保存：全部 trace（成功、错误、空答、重试、暂停、预算耗尽）与成本估算依据；
  报告由脚本从 trace 重新生成，不手改数字。

## 7. 与既有文档的关系

- 题目定义与独立核对方式：[task-set.md](task-set.md)、`benchmarks/tasks/`；
- 完整评测的历史数字：[comparison.md](comparison.md)（scripted）、
  [comparison-real.md](comparison-real.md)、[comparison-stronger.md](comparison-stronger.md)；
- 服务定位与边界：[Phase 3 计划](../roadmap/phase3-plan.md) §1.1、§5；
- 本文件不替代任何测量报告；M6 的评测结果将另立报告文件并由脚本生成。

## 附录 A：层级 0 完整命令

```bash
export PATH="/e/Dexatlas/.scratch/backends/jadx/bin:$PATH"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
uv run --no-sync python benchmarks/run.py \
  --task manifest.package.demo \
  --task manifest.permission.name-strings \
  --task manifest.permission.count-obfuscated \
  --task components.exported.demo \
  --task components.exported.obfuscated \
  --task overloads.method-identity.crypto-sign \
  --task overloads.method-identity.descriptor-distinguishes \
  --task ambiguity.declared-type-contradicts-body \
  --task xrefs.crypto-sign-callers \
  --task xrefs.handler-handle-callers \
  --task xrefs.crypto-sign-call-site-count \
  --task strings.api-key.demo \
  --task strings.telemetry-url.obfuscated \
  --task resources.app-name.demo \
  --task wheresource.app-name-resource-file.demo \
  --task unanswerable.crypto-digestof-has-no-callers \
  --task unanswerable.demo-declares-no-receiver \
  --task partial.no-apktool-there-is-no-manifest \
  --task partial.no-jadx-the-failure-is-recorded \
  --task multidex.dex-file-count \
  --workspace E:/Dexatlas/.scratch/m6-freeze
```
