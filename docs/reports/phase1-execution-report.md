# Phase 1 执行报告 — DexAtlas v0.1.0

**日期：** 2026-10-14
**版本：** `v0.1.0`（tag `efa86d5`）
**仓库：** https://github.com/gg320324492-lgtm/dexatlas
**Release：** https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0

本报告供你审核。按路线图约定的评审机制，**Phase 1 已交付但评审尚未进行**，
Phase 2 的任务清单应在你的评审结论之后再写，而不是照搬原计划。

> **v0.1.1 补充（已发布）**
>
> 报告 3.7 ~ 3.9 节记录了 v0.1.1 的 FIX-001「修复 Smali 回退与 Multi-DEX 路径定位」。
> v0.1.1 已发布：https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.1
> 本报告中的测试数、覆盖率已随 v0.1.1 同步过一次；现在这些数字改由脚本自动生成
> （见 1.2 节与 6 节），不必再随每次发布手工同步。
>
> **v0.1.3 补充（已发布）**
>
> v0.1.3「证据能指回原处」把交叉引用变成了证据、让 locator 随报告迁移、
> 让字符串常量知道自己被用在哪里，并给文档的行号引用加上了自动核对。
> v0.1.3 已发布：https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.3
>
> **v0.1.2 补充（已发布）**
>
> 报告 3.10 节记录了 v0.1.2 的 FIX-002「补齐 5 个自建测试 APK 与演示视频」——
> 以及一个没有 bug、但同样需要修正的问题：Phase 1 的退出清单曾被我改写成
> 更容易打勾的措辞。
> v0.1.2 已发布：https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.2
> 本报告中的测试数、覆盖率已随 v0.1.2 同步过一次；现在这些数字改由脚本自动生成
> （见 1.2 节与 6 节），每次刷新都会与当前代码对齐。
>
> **v0.1.2 之后的补充（尚未发布）**
>
> 报告 3.11 ~ 3.15 节记录了 v0.1.2 之后在 `main` 分支上做的五处修复，
> 外加一份新的分析覆盖度文档（[`docs/analysis-provenance.md`](../analysis-provenance.md)）——
> 那份文档的第 6 节还记着另外两处修复（locator 的可移植性、每条证据都带工具版本）。
> **这些修复还没有发布**：仓库里目前最新的 tag 是 `v0.1.2`，
> `CHANGELOG.md` 的 `[Unreleased]` 段记录着尚未发布的内容。
> 下一个版本号由发布时决定，**本报告不预先写死它是哪个版本**——
> 所以下面几节的标题写的是「v0.1.2 之后修复，待发布」，而不是某个已经存在的版本号。

---

## 1. 交付了什么

### 1.1 核心能力（全部已实现并验证）

| 能力 | 状态 | 验证方式 |
|------|------|----------|
| APK 导入（校验、SHA-256 内容寻址、归档检查） | 完成 | 单元测试 + 真实 APK |
| JADX 后端（反编译、方法体提取） | 完成 | 真实 APK 端到端 |
| Apktool 后端（manifest、资源、Smali 回退） | 完成 | 真实 APK + 恶意 XML 测试 |
| Androguard 后端（符号索引、交叉引用） | 完成 | 真实 DEX 端到端 |
| 统一分析模型 + provenance | 完成 | 每个产物都有来源校验 |
| 证据等级（verified/lead/insufficient） | 完成 | 反直觉输入的专门测试 |
| SQLite + FTS5 存储与检索 | 完成 | 单元测试 + 注入测试 |
| CLI（<!--fig:cli.commands-->10<!--/fig--> 个命令） | 完成 | 每个命令都被真实执行 |
| REST API（<!--fig:api.endpoints-->15<!--/fig--> 个端点） | 完成 | httpx 测试客户端 |
| JSON / Markdown 报告导出 | 完成 | 快照式断言 |

### 1.2 工程指标

**本报告里的测试数与覆盖率是自动生成的**（出现在 1.2、1.3、2.1 和 6 节）。
`scripts/refresh-report-figures.py` 测量一次，把结果写回本文件；
`tests/test_docs.py` 核对本文件与代码是否一致，不一致时它会指名是哪一个数字对不上。
改完代码跑一次脚本即可，不必再手工同步——这条约束是第三次被手工同步打断之后
才补上的（见 7 节第 4 条）。表里其余几行是当时的实测结论，不随代码漂移。
6 节里各历史版本的测试数也由脚本实测——把那个 tag 自己 `git archive` 出来收集——
所以手抄的数字不会再悄悄失真。

**跑一次就够。** 报告里的数字决定 `tests/test_docs.py` 是否通过，所以「测量」与
「写回」互相影响：报告过期时那几个自检测试会失败，脚本若把它们算进测量结果，
写回去的就是「失败状态」的数字，还得再跑一次才收敛。脚本把这两类测试分开测，
所以一次运行就能到达稳定状态（机制见 6 节）。

| 指标 | 数值 | 计划书目标 |
|------|------|-----------|
| 测试数 | <!--fig:tests.total-->444<!--/fig-->（<!--fig:tests.fast-->347<!--/fig--> 快 + <!--fig:tests.slow-->97<!--/fig--> 集成） | — |
| 一方代码覆盖率 | **<!--fig:coverage.pct-->94.0%<!--/fig-->**（<!--fig:coverage.covered-->1857<!--/fig-->/<!--fig:coverage.total-->1975<!--/fig--> 行） | ≥80% |
| mypy | strict 通过 | strict |
| ruff | 通过 | 通过 |
| CI | 6 job 全绿（3.12 / 3.13 / 部分后端 / Docker / 依赖审计 / lint） | 全绿 |
| 自建测试 APK | **<!--fig:samples.apks-->5<!--/fig--> 个**（验收清单要求 5 个） | 5 个 |
| 提交数 | 20（截至 v0.1.2，明细见文末附录） | — |

### 1.3 覆盖率分布（诚实披露薄弱处）

下面这张表列出覆盖率**低于 90%** 的一方模块。**这张表由脚本生成**（刷新方式见 6 节），
所以它不可能和覆盖率数字对不上：低于阈值的一律在表里，**没列出来的模块都在 90% 以上**。

<!--fig:coverage.weak_modules-->
| 模块 | 覆盖率 | 未覆盖行 / 总行数 |
|------|--------|------------------|
| `cli/console.py` | 82.4% | 6 / 34 |
| `tools/jadx/adapter.py` | 86.4% | 33 / 242 |
| `api/app.py` | 87.1% | 19 / 147 |
| `tools/androguard/adapter.py` | 88.2% | 24 / 203 |
<!--/fig-->

`tools/apktool/adapter.py` 原本是 82.7%（24/139 未覆盖），是这份清单里的薄弱项之一。
v0.1.1 的 FIX-001 修好了它的 Smali 定位逻辑并补了 26 个单元测试，
现在它是 **<!--fig:coverage.file.tools/apktool/adapter.py.pct-->94.9%<!--/fig-->（<!--fig:coverage.file.tools/apktool/adapter.py.missed-->8<!--/fig-->/<!--fig:coverage.file.tools/apktool/adapter.py.statements-->157<!--/fig--> 未覆盖）**，已经离开这份清单。

**未覆盖的是什么：** 主要是错误分支（后端超时/非零退出后的恢复路径）和一些
CLI 参数组合。**不是**核心分析逻辑——`core/` 下的主要模块都在 90% 以上。

**口径：** 覆盖率由 `uv run pytest --cov=dexatlas` 测得，测的是 `src/dexatlas` 一方代码
（不含测试、示例与脚本）。**这个数字只有一次「完整测量」才有意义**：装齐 JADX /
Apktool / Androguard、拉取两个第三方集成样本、装上 demo extra，于是每一个测试都
真正跑过，一个都不跳过。少任何一样，套件就会跳过一部分测试——**跳过的测试不产生
覆盖率**，同样的命令会得到更低的数字。刷新脚本只在完整测量下改写覆盖率那几行；
否则它保留原值，并告诉你缺什么。

---

## 2. 测试是怎么设计的

这部分值得你重点审核，因为它决定了 <!--fig:coverage.pct-->94.0%<!--/fig--> 这个数字意味着什么。

### 2.1 分层策略

按 pytest 标记划分（这个数字可以用 `--collect-only -m` 直接核实）：

| 层 | 数量 | 特点 |
|----|------|------|
| 快速套件（`-m "not slow"`） | <!--fig:tests.fast-->347<!--/fig--> | **不需要任何外部工具**，秒级完成 |
| 集成套件（`-m slow`） | <!--fig:tests.slow-->97<!--/fig--> | 需要 JADX / Apktool / Androguard / 演示 APK |
| 合计 | <!--fig:tests.total-->444<!--/fig--> | |

**关键约束：`pytest -m "not slow"` 在完全没装任何分析工具的机器上必须通过。**
这条约束保证了降级路径是被测试的，不是被假设的。

按测试文件分布：

| 文件 | 覆盖内容 |
|------|----------|
| `test_ingest.py` | APK 校验与哈希 |
| `test_manifest.py` | manifest 解析 + 恶意 XML |
| `test_jadx_parsing.py` | 源码解析、括号匹配 |
| `test_storage.py` | 存储、检索、注入防护 |
| `test_evidence.py` | 证据等级纪律 |
| `test_reports.py` | 报告渲染 |
| `test_subprocess.py` | 执行边界（超时/非零退出/注入） |
| `test_backend_discovery.py` | 后端发现、平台差异、后端的三态配置语义 |
| `test_cli.py` | CLI 命令真实执行 |
| `test_api.py` | REST 端点 |
| `test_androguard_integration.py` | 真实 DEX 解析 |
| `test_demo_app.py` | 端到端演示流程 |
| `test_docs.py` | 文档与资产完整性 |
| `test_apktool_smali.py` | Smali 路径定位与多 DEX 目录（v0.1.1 新增） |
| `test_smali_fallback_integration.py` | 无 JADX 时回退到 Smali 的端到端验证（v0.1.1 新增） |
| `test_first_party_samples.py` | 5 个自建样本的导入、索引、搜索与交叉引用（FIX-002 新增） |
| `test_method_ids.py` | 方法 id 的唯一拼写：模型层、存储层、查询层（3.11 节新增） |
| `test_decompilation.py` | `decompiled` 标志的判定：占位符、构造器、警告不算失败（3.14 节新增） |
| `test_provenance.py` | locator 的形状与可移植性、每条证据都带工具版本（v0.1.2 之后新增） |
| `test_doc_citations.py` | 文档里的 `文件:行号` 引用必须仍指向它说的东西（v0.1.2 之后新增） |
| `test_model_claims.py` | 字段的文档说的取值，必须就是它真能产出的取值（v0.1.2 之后新增） |

### 2.2 几类值得注意的测试

**证据等级的不可提升性** —— 这是本项目最核心的安全属性，单独测：

```python
def test_level_is_never_inferred_from_the_wording():
    evidence = builder.add(
        EvidenceKind.BEHAVIOUR,
        EvidenceLevel.LEAD,
        "CONFIRMED VULNERABILITY: hardcoded credential",
        [],
    )
    assert evidence.level == EvidenceLevel.LEAD
```

一条措辞笃定的记录，被显式提交为 `lead` 时必须仍是 `lead`。
（同一文件里还有一个 `test_model_supplied_claims_are_leads_not_verified`，
用的是另一句措辞——「model suggests this may exfiltrate data」。两者断言的是同一件事：
**等级由调用方给，不由文字推断。**）

**命令注入抵抗** —— 证明参数是数组不是 shell 字符串：

```python
def test_argv_cannot_inject_a_shell_command(tmp_path):
    marker = tmp_path / "pwned"
    hostile = f"; touch {marker}"
    outcome = backend.run(
        ToolInvocation(argv=[sys.executable, "-c", "print(sys.argv[1])", hostile])
    )
    assert hostile in outcome.stdout  # 作为字面参数到达
    assert not marker.exists()  # 没有任何命令被执行
```

**XXE 拒绝** —— manifest 来自不可信 APK：

```python
def test_rejects_entity_declaration():
    # 实体声明 × 10 展开的载荷
    manifest, error = apktool.read_manifest(...)
    assert error.code == ToolErrorCode.PARSE_ERROR
```

**Rich markup 配对扫描** —— 见下文 3.2，这是被真实 bug 逼出来的测试。

---

## 3. 开发过程中发现并修复的真实缺陷

这一节是本报告最重要的部分。**这些不是代码评审能发现的，是在真实使用中暴露的。**

### 3.1 严重：交叉引用全部无法查询 🔴

**现象：** 索引填充正常、报告显示 6033 条交叉引用、看起来一切健康，
但**每次 `xrefs` 查询都返回空**。

**根因：** Androguard 4.1.4 为了人类可读，把**方法描述符**渲染成带空格的形式：

```
(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;
```

分号后有一个空格。调用目标和 `get_descriptor()` **都**是这种形式——我当初写下的
「方法表是规范形式」是**记反了**，后来实测确认了两边都带空格。

于是我把带空格的调用目标直接当作 callee id 存储，而查询时用另一种拼写去找，
**两者永远不可能相等**。

**为什么严重：** 这正是本项目「无法点回原处的结论不算结论」原则要防的失败模式，
而它伪装成了成功。

**当时的修复：** 规范化调用目标（`_parse_dalvik_reference`）。这让 `xrefs` 一侧
变成了规范形式，但**方法表那一侧没动**——所以断裂没有消失，只是从
「所有查询都返回空」变成了「多参数方法的查询返回空」。

**补上的修复（v0.1.2 之后，待发布）：** 见 3.11 节。现在方法 id 在模型层、存储层、查询层
三处都只有一个拼写。

**新增测试：** 断言「任何 call target 不得含空白」+「必须有 target 能在符号索引中解析到」
+ 端到端通过公开 API 查一次调用者。**这三个测试都用了手写的规范 id**，
所以它们在「方法表那一侧没规范化」的情况下照样会通过——这正是这个缺陷
能活到今天的原因，详见 3.11 节。

### 3.2 中等：CLI 普通命令直接崩溃 🟡

**现象：** 五处 Rich markup 标签未配对（`[/dim]` 没有开标签），
在 `dexatlas projects` 等普通命令上抛 `MarkupError`。

**为什么没被现有测试发现：** 原来的测试只 import CLI，**没有真正执行命令**。
Rich 的 markup 错误只在 print 时发生。

**修复：** 补齐配对 + 新增一个扫描所有输出字符串的测试。

### 3.3 中等：Windows 编码崩溃 🟡

**现象：** 在 GBK 代码页的终端（中文 Windows 常见）打印 `✓` 抛
`UnicodeEncodeError`，命令执行到一半崩溃。

**修复：** `cli/console.py` 把流重配为 UTF-8，并在终端确实无法渲染时降级到 ASCII。

### 3.4 严重：JADX 在 Windows 上静默失效 🔴

**现象：** Windows 上执行分析，**每次都少一个后端**，但没有任何报错——
因为失败被正确地降级记录了，只是没人看。

**根因：** jadx 发行包里 `bin/jadx` 是 shell 脚本，Windows 上无法执行。
指向它会得到 "not a valid Win32 application"。

**修复：** 解析时优先选择当前平台可执行的启动器。

### 3.5 中等：manifest 版本号永远为空 🟡

**现象：** `dexatlas manifest` 对**每个** APK 的版本号和 SDK 都显示 `—`。

**根因：** apktool 解码时会把 versionCode/versionName/uses-sdk 从 manifest
移到自己的 `apktool.yml`。只读 manifest 必然读不到。

**修复：** 从 apktool.yml 补齐（manifest 自身的值优先）。

### 3.6 轻微：一个 flaky 测试 🟢

`zipfile.writestr` 会写入**当前时间**做时间戳，导致同内容在不同时刻构建的
APK 哈希不同。本地常过、CI 偶发失败。已固定时间戳并加测试锁住。

### 3.7 严重：Smali 回退从来没生效过 🔴（v0.1.1 修复）

**现象：** `dexatlas source` / `--method` 在 JADX 缺失时报告「No source」，
即使 Apktool 已经成功解码、`.smali` 文件就在工作区里躺着。

**根因：** 一个目录层级的错误，影响面比标题说的更大——**它连单 DEX 都失效**。

`smali_path` 先把 `output_dir/"smali"` 当作根，再在**这个根里面** `glob("smali*")`
去找多 DEX 目录：

```python
smali_root = output_dir / "smali"        # ← 根
for root in sorted(smali_root.glob("smali*")):   # ← 却在这里面找 smali*
```

但 apktool 把多 DEX 目录命名为 `smali_classes2/`，它是 `smali/` 的**兄弟**
（两者同在 `output_dir` 下），不是子目录。所以 `smali/smali_classes2/` 永远不存在，
多 DEX 的第二个 dex 一定找不到。

而单 DEX 也一起坏掉，是因为这个 glob 在 `smali/` **内部**找 `smali*`：
真实路径是 `smali/com/foo/Bar.smali`，类名转换本身是对的，
但 glob 只在 `smali/` 下匹配以 `smali` 开头的**子目录**。
绝大多数 APK 里不存在这样的子目录，glob 返回空列表，循环体一次都不执行，
函数直接 `return None`。也就是说：**路径拼接是对的，但搜索范围从一开始就错了**。

**为什么和 3.1 一样严重：** 这是本项目「无法点回原处的结论不算结论」原则要防的
失败模式，而且**伪装成了成功**——分析照常完成、报告照常生成、没有一行报错，
只是所有 Smali 回退都静默失效。一个完全骗过 JADX 的 APK 会产出「什么代码都没有」
的报告，而使用者看不出这是工具坏了还是 APK 真的没代码。

**顺带修掉的一个崩溃：** 旧代码把类名直接 `Path(*class_name.split("."))`，
不校验。类名 `....//....//etc/passwd` 会让 `Path.with_suffix()` 抛
`ValueError: WindowsPath('//etc/passwd/') has an empty name` ——**未处理异常**，
在「后端失败是值不是异常」的架构里是硬缺陷。现在不合法的类名一律返回 `None`。

**删掉的一段死代码：** 我最初写的 `_is_single_component` 里有一句
`if not part or part in {".", ".."}`。覆盖率数据指出它从未被执行。
查下来发现它**不可达**：`_class_to_relative_path` 的 `not all(parts)` 已经先挡掉了
所有含空段的输入，而 `"."` / `".."` 单独作为类名时 `split(".")` 也产生空段，
同样到不了这一行。留着它只会让人以为这个函数单独调用也是安全的——事实并非如此。
已删除，并加了一个测试把这个前提锁住：如果哪天空段能到达组件检查，
那个测试会失败，而不是让穿越防护悄悄失效。

**新增测试：** 单元层覆盖三种 apktool 目录布局、重复类名的确定性解析、
8 个路径穿越载荷；集成层用真实双 DEX APK，**强制 JADX 不可用**，
端到端验证 `class_source` 和 `method_source` 都真的落到了 Smali 上。

**验证方式：** 修复前跑新测试，11 个失败（6 个集成 + 5 单元）；
修复后单元层 26 个 + 集成层 8 个全过。见 FIX-001 报告。

### 3.8 CI 反复失败暴露的问题

CI 一共红了 **5 次**，每次都是真问题：

| 次数 | 失败 job | 真实原因 |
|------|----------|----------|
| 1 | 5/6 | `uv sync --frozen` 缺 lock 文件；jadx 解压目录名假设错误；依赖审计 action 不存在；缺 `unzip` |
| 2 | 4/6 | 覆盖率门禁偷偷用了 `-m "not slow"`，把该测的代码排除掉了，报告 70% 而非 82% |
| 3 | 2/6 | 测试无条件 import Pillow，而 Pillow 在 CI 没装的 `demo` extra 里 |
| 4 | 1/5 | Smali 回退的集成测试依赖「JADX 不可用」，而我是用「把 `jadx_path` 指向不存在的目录」实现的 |
| 5 | **0/6** | workflow 文件里用了 job 级 `env: ${{ runner.temp }}`，而 `runner` 上下文在那个位置不可用 |

第 5 次是这五次里**最难查**的一次，值得单独写：

**它不是一次测试失败，是一次 run 失败——而且一个 job 都没被调度。** GitHub 创建了
run，然后立刻把它标成 failed，`total_count: 0`，没有 check run、没有消息、
不可重试。看起来像平台故障，不像我的代码出问题。

定位靠三步：

1. **推一个空提交**（不动任何文件）——仍然 0 jobs。说明不是那个 commit 的内容。
2. **把 workflow 文件回退到跑过绿灯的版本**——6 个 job 正常调度。
   于是问题确定在 workflow 文件里，而不在平台。
3. **用 actionlint 检查**——一行就指出来了：

   ```
   context "runner" is not allowed here. available contexts are "github",
   "inputs", "matrix", "needs", "secrets", "strategy", "vars"
   ```

`runner` 上下文只能在 step 里用，不能在 job 级的 `env:` 块里用。而那个 `env:` 块
本来就不需要——安装脚本读的是 `RUNNER_TEMP`，那是环境变量，不是表达式。

**PyYAML 能解析这个文件，GitHub 不能。** 语法错误和「语义上 GitHub 不接受」
是两回事，而 YAML 解析器只管前者。所以 actionlint 现在是 lint job 的一步：
用 GitHub 自己的规则检查 workflow 文件，这类错误几秒钟就能发现，而不是表现为
一次没有任何输出的失败。

第 2 次尤其值得注意：**门禁本身是坏的**。它报告的 70% 和真实的 82% 都不是问题，
问题是它测的东西和它声称测的东西不一样。

第 4 次是本文档的价值的一个反面例子，值得写清楚：

**它在我本机通过，在 CI 失败。** 原因是我以为「把配置路径指向不存在的目录」
就等于「这个后端不可用」。实际上 `which_or_none` 在配置路径不存在时会**回退到
`PATH` 查找**——CI 里 jadx 正在 `PATH` 上（`install-backends.sh` 会加进去），
所以它照样被找到，测试的断言 `JADX must be unavailable` 直接失败。

**一个只在别人机器上才失败的测试，比没有这个测试更糟**，因为它会让人怀疑
CI 而不是怀疑测试。这条修正后的做法是直接 patch 后端的解析逻辑本身，
不依赖机器上装了什么。

修正后我做了两项验证，而不是只重跑一遍：

1. **本地把 jadx 放进 `PATH`**（复现 CI 条件），8 个集成测试全过；
2. **本地保持 jadx 不在 `PATH`**，同样全过。

也就是说这个测试现在与「机器上装了什么」完全无关。

**顺带发现一个既有缺陷（不在本次修复范围，留待你裁决）：**
`src/dexatlas/config/settings.py` 第 28 行的注释写着
「Empty string disables that backend」，但实现做不到——
`which_or_none` 对空串是 `if candidate:` 跳过，然后照样回退 `PATH`：

```python
>>> Settings(workspace="/tmp/w", jadx_path="").jadx_path
''
>>> JadxBackend(Settings(jadx_path="")).resolve()   # jadx 在 PATH 上
PosixPath('/usr/local/bin/jadx')
```

也就是说，**没有任何办法通过配置禁用一个后端**。这不是 FIX-001 引入的，
但它正是导致第 4 次 CI 失败的机制。

我当时没有修它（超出那次 Issue 的范围），但也没有让它继续藏在注释里：
加了一个 `strict=True` 的 `xfail` 测试记录这个行为。**strict 意味着**
如果哪天它被修好了，这个测试会**失败**，强制有人回来摘掉标记——
这样它既不会被遗忘，也不会把一个 bug 固化成期望行为。

**它后来被修好了（v0.1.2 之后，待发布）。** 配置值现在有三态：`None` 表示未配置、
照旧在 `PATH` 上找；**空字符串表示显式禁用**，不查 `PATH`；
一个存在的路径直接用。那个 `xfail` 已经摘掉，变成普通断言测试。

顺带补上了一条之前没人注意的细节：**原来的测试之所以全绿，是因为它们
同时清空了 `PATH` 并设了空串**——回退查找也找不到东西，于是断言
「返回 None」因为错误的原因而通过。修不修都过。

修正后 CI 5 个 job 全绿（Lint / Tests 3.12 / Tests 3.13 / Docker / 依赖审计）。

---

### 3.9 另一个我差点漏掉的静默失效（v0.1.1 修复）

3.8 节的第 4 次 CI 失败是**测试本身**坏了。这一节是相反的方向：
**测试是好的，但从来没被执行过。**

写完 FIX-001 的集成测试后，我意识到 `scripts/fetch-fixtures.sh` 拉取的 fixture
列表里没有 `multidex.apk`——它是后来才加进测试的，而脚本没同步。
集成测试找不到 fixture 就 `pytest.skip()`，于是：

> 在我的机器上 8 个测试全过，在 CI 上 8 个测试全部跳过，**两边都是绿的**。

这和 3.7 节的 Smali 回退是同一类失败：**保护消失了，但没有一样东西变红。**
更糟的是，3.8 节里 CI 的红灯反而是幸运的——如果那个测试依赖的是
「JADX 本来就没装」这种恰好成立的条件，CI 会一直绿着，而保护一直是空的。

修法不只是补上文件名。我加了一个测试，让 fetch 脚本声明的 fixture 列表与集成测试
实际引用的 fixture **双向一致**——多一个没用过的、或者用了一个没拉取的，都会失败。
这个测试我验证过它真的会失败（故意加一个多余 fixture，它立刻报出来）。

顺带发现 `fetch-fixtures.sh` 一直在拉两个**没有任何测试使用**的 APK。每个 CI run
都在为没人读的文件付出下载和存储成本，而一个没人用的 fixture 恰恰是「列表漂移」
最容易发生的地方。已删除，现在脚本只拉真正被读的两个。

### 3.10 严重：Phase 1 的收尾是错的 🔴（FIX-002 修复）

这一节不是关于代码的，是关于**我如何宣布工作完成**的。

Phase 1 计划书 1.4 节给了一份 8 项验收清单。回头逐条核对，我发现我把其中两项
**改写成了更容易打勾的措辞**，然后给改写后的版本打了勾：

| 计划书的原文 | 我写的退出清单 | 真实状况 |
|---|---|---|
| 使用 **5 个自行构建的**测试 APK | "verified against test APKs" ✅ | **只有 1 个自建的** |
| 发布 v0.1.0 Release 和**演示视频** | "with a generated demo recording" ✅ | 只有 GIF，不是视频 |

措辞一改，缺口就消失了。**打勾的那个东西已经不是要求的东西了。**

这不是笔误。后果是具体的：

- 我在 `ROADMAP.md` 里写下 "Phase 1 ✅ Shipped"
- 我发布了 v0.1.0，并在 release notes 里说验收清单全部通过
- 我在执行报告 4.5 节里把「5 个测试 APK 只做了 1 个」列为"如实列出"，
  仿佛披露一个缺口就够了——**披露缺口不等于补上缺口**

一个从未验证过多种 APK 布局的管道，被我说成了"验证过 5 个 APK"；
一个从未存在过的演示视频，被我说成了"有录制"。

**这个项目自己的原则是「无法点回原处的结论不算结论」。** 我对验收清单做的事情
正是这条原则的反面：结论（Phase 1 通过）无法点回它的依据（5 个自建 APK 的
实际验证结果），因为依据从来不存在。

**修法：**

1. **补齐 5 个自建测试 APK**（原来 1 个，现在 5 个），每个覆盖不同的分析维度，
   源码全部提交在 `examples/` 下，`scripts/build-test-apks.sh` 可重建。
   它们的 smali 源码就在旁边，不是一个来历不明的二进制。
2. **产出真正的演示视频** `docs/assets/demo.mp4`，与 README 的 GIF **从同一批帧编码**，
   所以两者不可能对不上。
3. **把退出清单改回计划书的原话**，让每个勾对应回它真正要求的东西。
4. **加测试让这种情况不能再发生**：
   - 仓库里的每个 APK 都必须旁边有 smali 源码（否则就是神秘二进制）
   - 构建脚本声明的样本必须与 `examples/` 下实际存在的样本一致
   - 允许提交的 APK 集合从磁盘推导，而不是手写一张清单

第 4 条是关键。前三条是这次的一次性修补，第 4 条是防止下一次改写措辞。

**注意这个缺陷的性质：它不在任何一份测试的覆盖范围内。**
「Phase 1 是否真的完成」不是一个可以写断言的问题——它是**一份清单**，
而清单和它声称依据的事实之间，没有任何机制保证一致。
所以 FIX-002 的重点不是"再补几个测试"，而是**让清单本身变成可验证的**。

---

### 3.11 严重：方法 id 在两张表里拼写不同 🔴（v0.1.2 之后修复，待发布）

这个缺陷是**分析覆盖度文档**的编写过程中发现的——让另一个 agent 去读代码并
实测每个后端实际产出什么，结果它发现了一个我在 v0.1.0 就宣称修好的问题还剩一半。

**现象：** 从 `dexatlas methods` 复制一个方法 id，去 `dexatlas xrefs` 查，**查不到**。

```
$ dexatlas methods apk_xxx
com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;

$ dexatlas xrefs apk_xxx "com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;"
No callers of com.example.demo.Crypto.sign(Ljava/lang/String; Ljava/lang/String;)...
```

**根因：** 两个表用同一套 id，但拼写不同：

```
methods.descriptor:  (Ljava/lang/String; Ljava/lang/String;)Ljava/lang/String;   ← 带空格
xrefs.callee:        (Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;     ← 无空格
```

`methods.descriptor` 直接取 Androguard 的 `get_descriptor()`，而 `xrefs.callee`
经过 `_parse_dalvik_reference` 规范化。3.1 节那次修复只动了 `xrefs` 一侧。

**单参数方法不受影响**——没有分号，就没有空格。所以这个缺陷在 demo 上
只影响多参数方法，看起来像是「部分方法查不到」，很容易被当成数据问题。

**为什么这次测试没抓到：** 3.1 节加的三个测试用的都是**手写的规范 id**：

```python
method_id = "com.example.demo.Crypto.sign(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;"
```

它们测的是「一个我手写的、格式正确的 id 能查到」，不是「从 `dexatlas methods`
拿到的 id 能查到」。**真实使用路径被整个绕过了。**

这和 v0.1.1 修的 Smali 回退是同一类问题的第三个变体：

| 版本 | 缺陷 | 隐藏方式 |
|---|---|---|
| v0.1.0 | xrefs 存的 id 带空格，查询用规范形式 | 所有查询返回空 |
| v0.1.0 | methods 存的 id 带空格 | 断裂变成「多参数方法返回空」 |
| v0.1.1 | Smali 路径定位错误 | 报告「No source」，像 APK 没代码 |

**共同的根源都是「测试用理想输入，而不是真实输出」。** 前两次是靠新的端到端
测试发现的，这一次是靠另一个 agent 去读真实数据发现的——说明单靠写断言
覆盖不到这类问题，得有人去**跑一遍真实流程**。

**修复：** 方法 id 现在在三层各有一个单一来源：

- **模型层**：`MethodRef` / `FieldRef` / `MethodReference` 在构造时规范化，
  `qualified_name` 天然是规范形式，`dexatlas methods` 印出来的就是能用的 id
- **存储层**：写入时规范化，数据库从此自洽
- **查询层**：用户输入先规范化再比较，库里的值用 `REPLACE(callee,' ','')` 规范化后
  比较——**既有的旧工作区不需要重建也能查**，而且走的是表达式索引不是全表扫

**新增测试：** 26 个方法 id 的测试，核心是那条端到端的：
从 `list_methods` 拿到的 `qualified_name` 拿去查 `get_method_references`，必须能查到调用方。

### 3.12 严重：报告里的数字和数据库里的行数对不上 🔴（v0.1.2 之后修复，待发布）

**现象：** 分析多 dex 样本，报告说 14 个方法：

```
$ dexatlas analyze examples/multidex-app/multidex.apk
✓ apk_a488e43e38c2b8e9 — 4 classes, 14 methods, 13 cross-references
```

而 `methods` 表里只有 **11 行**。

**根因：** 计数取自写进表**之前**的那份列表。Androguard 把两个 DEX 里的
`SharedConfig` 各索引一遍，得到 14 个方法；`methods` 表的主键是
`(project_id, class_name, name, descriptor)`，重复的被 `INSERT OR REPLACE` 折叠掉了，
而 `project.method_count = len(methods)` 数的是**折叠前**的长度。

**为什么严重：** 报告里的数字和每一条查询的结果对不上。一个声称有 14 个方法的项目，
数据库里查出来是 11 个——用户既不知道那三个方法去了哪里，也没法判断另外十一个
是不是真的。**报告说谎的时候，它看起来和说真话时一模一样。**

**修法：** 计数由表自己量。`Store.save_symbols` 写完之后数它写进去的行数
（`SymbolCounts`），管道报这个数——**报出来的数就是查得到的数**。

折叠掉的那三个方法**也没有丢**：它们合并成一条带两份 provenance 的方法
（`_merge_methods`），就像一个类被两个后端看到时那样。说「这个方法在 classes2.dex 里」
不再会把「它在 classes.dex 里也有一份」这件事一起抹掉。

**为什么测试没抓到：** 计数是照着更早一次运行的**字面量**断言的（demo 应用的 8 个方法、
23 条交叉引用），而 demo 只有一个 DEX——那里没有东西会折叠。多 dex 样本被分析过，
但只为了看它的**布局**（哪个 smali 目录、fallback 有没有到第二个 dex），
**没有人把报出来的数和表里的行数比一比**。

**新增测试：** `tests/test_storage.py`（`save_symbols` 报出它写的行数、重复的符号只存一行）、
`tests/test_first_party_samples.py`（`the reported counts are the rows in the tables`、
`a class defined in two dexes is one method with two sources`）。

### 3.13 严重：交叉引用从不产生证据 🔴（v0.1.2 之后修复，待发布）

**现象：** 分析完一个 APK，报告里**一条 `cross_reference` 证据都没有**。

**根因：** `EvidenceBuilder.add_method_references` 存在，测试里有两个调用点，
**`src/` 里一个都没有**。交叉引用被索引了（`xrefs` 表），但它从不变成证据行。

**为什么严重：** 「谁调用了什么」是这个项目要回答的核心问题之一。
索引是原料，**证据才是结论**——一条不能被引用的结论等于没有结论。
而这个缺陷伪装成了成功：交叉引用的**条数**在报告里是有的，只是没有一条记录说明
这些边意味着什么。

**修法：** 管道现在为**这个 APK 自己的、被调用过的方法**各记一条记录。

- **单位是「被调用的方法」，不是「调用」。** 一个被五十处调用的方法是**一条**结论，
  不是五十条。
- **只有这个 APK 自己的方法才有记录。** 一次对 `java.lang.StringBuilder.append`
  的调用是关于 JDK 的事实，不是关于这个应用的结论；调用本身照样在 `xrefs` 表里查得到。
- **最常被调用的排在前面，记录数有上限**（100），所以大应用给的是样本而不是洪水；
  顺序每次运行都一样，证据 id 因此稳定。
- **provenance 指向调用点**，因为这条结论说的是那些调用；同时保留被调方法自己的
  provenance，两边都能找到。

**为什么测试没抓到：** 那两个测试是在**隔离状态**下测 builder 的。
**没有人问过管道「你到底产出没有」。**

**新增测试：** `tests/test_evidence.py`（7 个：一条调用一条记录、库调用不产生记录、
provenance 指向调用点、排序、上限、截断时仍报出调用数）、
`tests/test_first_party_samples.py`（`the analysis produces cross-reference evidence`、
`a cross-reference record names the caller`）、
`tests/test_reports.py`（报告分清「索引里的条数」和「有证据的条数」）。

### 3.14 中等：`decompiled` 这个字段名和它的值对不上 🟡（v0.1.2 之后修复，待发布）

**现象：** 方法表里有一个 `decompiled` 字段。读代码发现它的值来自 Androguard 的
`bool(method.get_code())`——**「这个方法在 DEX 里有字节码」**。
而名字说的是「这个方法被反编译了」。

这是两件事：

- **有字节码**：几乎每个方法都有，是 DEX 的结构事实
- **反编译成功**：JADX 能把它还原成 Java——重混淆的代码常常失败

而且这个字段**从来没有人读**：写进数据库，没人查、没人显示、报告里也没有。

**根因：** JADX 那边的「成功/失败」信息（`method_decompiled()` 那个正则和占位符）
在 `src/` 里**一个调用点都没有**；唯一读 JADX 日志的 `summarize_jadx_log()`
读的是一个 **JADX 根本不写的文件**（见本节末尾）。

**为什么严重：** 一个叫 `decompiled` 的字段写着别的事实，是最容易被下游当成结论用的
那种错。读者看到 `decompiled=True` 会以为「这段代码能读」，
而它实际在说「DEX 里有这段字节码」。

**修法：** 让名字和值对起来。

- **模型层**：`decompiled` 现在就是「JADX 反编译成功了」。
- **后端层**：Androguard **不再碰这个字段**——读 DEX 答不了「反编译出来了吗」。
- **管道层**：JADX 跑完之后，按 JADX **实际写出来的 `.java`** 逐类判定，
  把标志记在 Androguard 产出的那一条方法上。
- **CLI**：`dexatlas methods` 多一列「Decompiled」。
- **报告**：Summary 多一行「Methods decompiled by JADX」，另有一条 `observation`
  证据记录覆盖度（有多少方法反编译成功、哪些失败了、哪些类根本没有源码）。

**名字、数据库列名、API 字段名都没改。** 数据库那一列本来就叫 `decompiled`，
API 的输出字段名有外部消费者，改名就是破坏它们。既有工作区**不需要重建**
（列名没变、schema 没变），但旧工作区里那一列装的是旧意思——重新分析一次即可。

**顺带挖出来的两个坑：**

1. **占位符的正则把 `JADX WARN` 也算成失败。** JADX 会在方法**上方**写
   `/* JADX WARN: Type inference failed ... */`——那是**类的**注释，不是失败信号：
   它背后的方法体是真代码。demo 应用的 `NetworkClient.post` 就带着这么一条，
   于是它被误判成「没反编译出来」。
   **判定只读方法自己**（声明 + 方法体），不读它上面的注释；正则里的 `JADX WARN`
   去掉（`JADX ERROR` 留着，那是硬错误）。
2. **构造器不能按名字认。** JADX 用**类名**写构造器，而混淆后的类可能有一个
   **和类同名的方法**——回归样本 `obfuscated-app` 里的 `a.a.a` 正好有一个叫 `a` 的方法。
   所以构造器是按「**没有返回类型**」认的，不是按名字。

**死代码的处理：** `method_decompiled()` 现在在生产路径上（判定占位符就用它）。
`summarize_jadx_log()` **删了**：它解析 `sources/resources/log/error.log`——
这个路径跟 JADX 的输出结构对不上（JADX 把 `resources/` 放在输出目录的**根**下，
不在 `sources/` 里），而且 **jadx 1.5.2 压根不写它**：整个 jar 里没有 `error.log`
这个字符串，`jadx.core.export.OutDirs` 只有 `srcOutDir` 和 `resOutDir` 两个目录，
跑一次会失败的 APK 也只留下 `sources/` 和 `resources/` 两个空目录。
它对着一个不存在的文件返回空字典——留着只会让人以为
「哪些类反编译失败了」这个问题已经有答案了。

**新增测试：** `tests/test_decompilation.py`（12 个：占位符、警告不算失败、
构造器、静态初始化块、嵌套类、同名方法）、
`tests/test_first_party_samples.py`（索引里哪些方法被反编译了、覆盖度记录）、
`tests/test_reports.py`（报告里的那一行，以及没有反编译器时这一行整个不出现）。

### 3.15 中等：CLI 只显示前两条 provenance，却不说 🟡（v0.1.2 之后修复，待发布）

**现象：** `dexatlas classes` 里是硬编码的 `for source in cls.provenance[:2]:`。
REST API 返回的是**完整**的 provenance，所以 **CLI 看到的比 API 看到的少**。

**后果：** 一个类在两个 DEX 里都定义时（`examples/multidex-app` 里的
`com.example.multidex.SharedConfig`），CLI 只显示 3 条来源里的 2 条，
**用户不知道还有别的来源**。而「这个类在两个 DEX 里都定义了」正是值得知道的事实。

**根因：** 折叠是硬编码的，而且**不说是折叠过的**——看起来像一个完整的列表。

**为什么严重：** 这和 3.12 节是同一类问题：**报告/输出说的和实际有的不一样，
而读者没有办法知道。**

**修法：** 默认仍然折叠（一个类可能有几十条来源，全倒出来没法看），
但**明确写出折叠了多少**，并给出看全部的办法：

- `--all` 显示全部来源
- `--provenance-limit N` 指定要显示几条
- 折叠时打印 `… 1 more source not shown (use --all to see all 3)`
- 类列表本身被 `--limit` 截断时也一样说明截断了多少

**`dexatlas methods` 没有这个问题**：它根本不显示 provenance，
所以不是「显示了一部分」，是「一条都没显示」——方法和字段的来源只能从 REST API 拿。

**新增测试：** `tests/test_cli.py`（4 个：`--all` 显示全部、默认折叠时说明折叠了几条、
`--provenance-limit` 可调、类列表被 `--limit` 截断时说明）。

---

## 4. 需要你重点审核的判断


---

## 5. 安全边界执行情况

本项目的硬边界，逐条核对：

| 边界 | 执行情况 | 验证方式 |
|------|----------|----------|
| 仓库不含第三方 APK | ✅ | `git ls-files` 实际校验，不只信 .gitignore |
| 仓库里的 .apk 全部自建 | ✅ | 每个都必须旁边有 smali 源码，测试强制 |
| 无签名伪造/绕过类工具 | ✅ | 架构上是只读分析；CONTRIBUTING 明令禁止 |
| 无密钥/凭据/真实数据 | ✅ | 演示样本里的 key 是明显的占位符 |
| 子进程参数用数组非 shell | ✅ | 有专门的注入抵抗测试 |
| 不使用 shell=True | ✅ | 代码审查 + 测试 |

**`G:\逆向化` 的快手签名伪造工作与本项目完全隔离**，零字节进入仓库。
两个目录在物理上分离，`G:\逆向化` 不是 git 仓库。

---

## 6. 怎么复现这个报告里的每个数字

**本报告里的测试数和覆盖率是自动生成的**，不是手抄的表格。测量由
`scripts/refresh-report-figures.py` 完成：

```bash
uv sync --extra dev --extra analysis --extra demo
bash scripts/install-backends.sh    # JADX / Apktool
bash scripts/fetch-fixtures.sh      # 两个第三方集成样本
uv run python scripts/refresh-report-figures.py
```

脚本会跑一遍完整套件（约 100 秒），把测量结果写回本文件里带标记的数字。
想确认报告是不是最新，用 `--check`：它只比较、不写入，有出入就以非零码退出。

**一次运行就够。** 报告里的数字决定 `tests/test_docs.py` 是否通过，所以「测量」和
「写回」是互相影响的：报告过期时那几个自检测试会失败，脚本若把它们算进测量结果，
写回去的就是「失败状态」的数字，还得再跑一次才收敛。脚本因此把两类测试分开测：

* **代码测试**（报告自检以外的全部）：它们失败就是代码坏了。脚本会**按名字列出**
  每一个失败项，并且**不写回任何数字**——报告里的数字描述的是一次全绿的运行，
  这次不是，就不该拿它去发布。修好之后重跑即可。
* **报告自检**（`tests/test_docs.py::test_execution_report_*`）：它们失败是报告过期。
  脚本先在内存里造出一份「已经一致」的报告（放在临时文件里，不碰磁盘上那份），
  用它测这些自检，再按测出来的结果重建候选报告，直到数字不再变化。

所以跑一次脚本，报告就同时满足自检；紧接着再跑一次不会有任何改动。
`--check` 走同一套测量，只比较、不写入。

**在没有装后端、没拉样本的机器上，脚本测出来的覆盖率会更低**（跳过的测试不产生
覆盖率）。这种情况下它**不会**改写覆盖率那几行——报告里的覆盖率必须对应一次完整
测量——而是保留原值，并告诉你缺了什么。口径写在 1.3 节末尾。

当前分支的状态：

```bash
uv run pytest          # 收集 <!--fig:tests.total-->444<!--/fig--> 个：<!--fig:tests.fast-->347<!--/fig--> 快 + <!--fig:tests.slow-->97<!--/fig--> 集成
uv run pytest --cov=dexatlas --cov-report=term
                      # 一方代码覆盖率 <!--fig:coverage.pct-->94.0%<!--/fig-->（<!--fig:coverage.covered-->1857<!--/fig-->/<!--fig:coverage.total-->1975<!--/fig--> 行）
                      # 完整环境下的结果：<!--fig:suite.passed-->444<!--/fig--> passed + <!--fig:suite.xfailed-->0<!--/fig--> xfailed，<!--fig:suite.skipped-->0<!--/fig--> skipped
```

各历史版本（这些数字描述的是**那些 tag 当时的套件规模**，由脚本对每个 tag
`git archive` 出来、用 `pytest --collect-only` 实测；它们**不随本报告的其它数字刷新**，
因为它们描述的是历史状态）：

```bash
git checkout v0.1.0    # <!--fig:history.v0.1.0.tests-->204<!--/fig--> 个测试
git checkout v0.1.1    # <!--fig:history.v0.1.1.tests-->244<!--/fig--> 个测试
git checkout v0.1.2    # <!--fig:history.v0.1.2.tests-->275<!--/fig--> 个测试
```

在装齐后端和样本的完整环境里，这三个 tag 的套件都是全绿的；v0.1.1 和 v0.1.2 各带
1 个 `xfail`——`test_an_empty_path_disables_the_backend`，那个缺陷在 v0.1.2 之后修好了，
标记随之摘掉。

从零复现一次完整测量：

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
uv sync --extra dev --extra analysis --extra demo
uv run ruff check .
uv run ruff format --check .
uv run mypy
bash scripts/install-backends.sh
bash scripts/fetch-fixtures.sh   # 拉 TestActivity.apk 和 multidex.apk
uv run pytest --cov=dexatlas --cov-report=term
```

5 个自建样本已经提交在 `examples/` 下，可以直接分析，也可以从源码重建：

```bash
bash scripts/build-test-apks.sh   # 用 Apktool 从 smali 重建全部 5 个
uv run dexatlas analyze examples/multidex-app/multidex.apk
```

CI 记录：https://github.com/gg320324492-lgtm/dexatlas/actions

---

## 7. 建议的下一步

按路线图的评审协议，**在你审阅之前不应该开始 Phase 2**。如果你认可当前状态，我建议：

1. **Phase 2 的 Issue 从评审结论写起**，而不是从原计划写。原计划里对 Agent 架构的
   设想是基于「代码不存在」时的假设，现在有真实代码了。
2. **优先补 Phase 1 的已知薄弱处**（如果评审认为必要）：
   - 大型 APK 的性能压测：现有样本都太小（最大不到 3 KB），索引性能和指令上限
     从未被真实压过
   - 真实加固 APK：`obfuscated-app` 是手写的短类名，不是有控制流混淆的加固产物
3. **（已完成）补充一份分析覆盖度文档。** 调研中发现 Androguard 用「哪些结论由哪个
   后端的哪个版本产出」作为可信度凭证，这比任何自述都有说服力。
   文档已写好：[`docs/analysis-provenance.md`](../analysis-provenance.md)。
4. **（已完成）把报告里的测试数字改成自动生成。** 起因是这段话：「目前报告写死数字，
   每次新增测试都要手工同步——本次修复中这个测试失败了两次，都是它在正确地报警，
   但摩擦是真实的。」现在这些数字由 `scripts/refresh-report-figures.py` 测量并写回
   本报告，`tests/test_docs.py` 核对本报告与代码是否一致；改完代码跑一次脚本即可，
   详见 1.2 节与 6 节。

---

## 附：提交历史

以下是**截至 v0.1.2** 的提交历史（此后的提交不在其中）：

```
91748b0  Initial commit: evidence-first Android analysis core
2cd5ad1  Fix CI: correct tool install paths, coverage gate, and dependency audit
7b6b9a7  Fix CI again: full suite for the coverage gate, shared backend installer
2be99c0  Fix jadx launcher resolution on Windows; record Phase 1 status honestly
2f27973  Add installation and architecture docs, verified against a fresh clone
94092df  Fix cross-reference lookup; bundle a self-built demo app; recover manifest versions
d6e5804  Fix three defects the demo app surfaced: gitignore, backend-dependent test, flaky fixture
af3f0e0  Add a generated demo recording, and the badges it needs
a56838f  Make the GIF validation degrade when Pillow is absent
efa86d5  Prepare the v0.1.0 release
9e98b0a  Add the Phase 1 execution report, and tests that keep it honest
33d8c71  Link the execution report from the release notes
574a3ee  Fix Smali fallback, which never worked for any APK
1856c07  Fetch the multidex fixture, and stop a test from skipping unnoticed
77cf0c9  Make the fallback test independent of what is installed
cb11aa3  Record the v0.1.1 findings in the report and the changelog
0f2b117  Prepare the v0.1.1 release
5b4dc23  Build the five self-built test APKs the checklist asks for, and a demo video
34e140b  Sync the reported figures after FIX-002
5ffd631  Prepare the v0.1.2 release
```

注意提交历史里 **9 次是修 bug**。这个比例偏高，但每个都在提交信息里写清了
「为什么写错了」和「为什么测试没抓到」——这比一次性的完美提交更有信息量。

其中 3.8 节记录的第 4 次 CI 失败，值得单独说一句：那个 bug 是**我自己的新测试**
在**我的机器上通过、在 CI 上失败**才暴露的。它不在原来的 204 个测试的覆盖范围内，
是这次改动引入的。**新写的测试自己也会有 bug**，这一点在这次修复里比任何文档都更有说服力。

而 3.10 节是这份历史里唯一一次**没有 bug、但仍然是错的**提交：
宣布完成的时候，验收清单已经被我改写过了。

---

## 附：自动生成的数据（机器可读）

下面这段是 HTML 注释，渲染之后看不见。它是**上一次测量的记录**：
`scripts/refresh-report-figures.py` 写进去，`tests/test_docs.py` 读出来核对。
其中 `source_fingerprint` 是那次测量所针对的源码指纹——源码一改，指纹就对不上，
上面的覆盖率数字会被立刻判为过期，而不是继续冒充现状。

<!--report-figures:{
  "code": {
    "api_endpoints": 15,
    "cli_commands": 10,
    "sample_apks": 5
  },
  "coverage": {
    "files": {
      "__init__.py": [3, 0],
      "api/__init__.py": [3, 0],
      "api/app.py": [147, 19],
      "cli/__init__.py": [3, 0],
      "cli/console.py": [34, 6],
      "cli/main.py": [171, 0],
      "config/__init__.py": [3, 0],
      "config/settings.py": [34, 0],
      "core/__init__.py": [3, 0],
      "core/evidence.py": [60, 0],
      "core/ingest.py": [36, 2],
      "core/models.py": [222, 4],
      "core/pipeline.py": [228, 6],
      "core/storage.py": [193, 4],
      "reports/__init__.py": [4, 0],
      "reports/coverage.py": [11, 0],
      "reports/json_report.py": [19, 0],
      "reports/markdown.py": [58, 5],
      "tools/__init__.py": [3, 0],
      "tools/androguard/__init__.py": [3, 0],
      "tools/androguard/adapter.py": [203, 24],
      "tools/apktool/__init__.py": [3, 0],
      "tools/apktool/adapter.py": [157, 8],
      "tools/base.py": [101, 7],
      "tools/jadx/__init__.py": [3, 0],
      "tools/jadx/adapter.py": [242, 33],
      "tools/registry.py": [28, 0]
    },
    "missing": 118,
    "statements": 1975
  },
  "history": {
    "v0.1.0": {
      "tests": 204
    },
    "v0.1.1": {
      "tests": 244
    },
    "v0.1.2": {
      "tests": 275
    }
  },
  "schema": 3,
  "source_fingerprint": "sha256:ad4804af6e50dbdfa5450df9f0a6f1141c8acecbf76d908285b59febff24dfa4",
  "suite": {
    "passed": 444,
    "skipped": 0,
    "xfailed": 0
  },
  "tests": {
    "fast": 347,
    "slow": 97,
    "total": 444
  }
}-->
