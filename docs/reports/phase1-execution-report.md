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
> 本报告中的测试数、覆盖率、提交数已同步到 v0.1.1 的状态。

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
| CLI（10 个命令） | 完成 | 每个命令都被真实执行 |
| REST API（15 个端点） | 完成 | httpx 测试客户端 |
| JSON / Markdown 报告导出 | 完成 | 快照式断言 |

### 1.2 工程指标

| 指标 | 数值 | 计划书目标 |
|------|------|-----------|
| 测试数 | 275（196 快 + 79 集成） | — |
| 一方代码覆盖率 | **89.2%**（1525/1709 行） | ≥80% |
| mypy | strict 通过 | strict |
| ruff | 通过 | 通过 |
| CI | 5 job 全绿（3.12 / 3.13 / Docker / 依赖审计 / lint） | 全绿 |
| 自建测试 APK | **5 个**（验收清单要求 5 个） | 5 个 |
| 提交数 | 18 | — |

### 1.3 覆盖率分布（诚实披露薄弱处）

```
 70.1%  cli/main.py              47/157 未覆盖
 76.8%  tools/jadx/adapter.py    48/207 未覆盖
 82.4%  cli/console.py            6/34  未覆盖
 85.7%  api/app.py              21/147 未覆盖
 88.5%  tools/androguard/adapter 20/174 未覆盖
 89.4%  reports/markdown.py       5/47  未覆盖
```

`tools/apktool/adapter.py` 原本是 82.7%（24/139 未覆盖），是这份清单里的薄弱项之一。
v0.1.1 的 FIX-001 修好了它的 Smali 定位逻辑并补了 26 个单元测试，
现在它是 **94%（5/159 未覆盖）**，已经离开这份清单。

**未覆盖的是什么：** 主要是错误分支（后端超时/非零退出后的恢复路径）和一些
CLI 参数组合。**不是**核心分析逻辑——`core/` 下的主要模块都在 90% 以上。

---

## 2. 测试是怎么设计的

这部分值得你重点审核，因为它决定了 89.1% 这个数字意味着什么。

### 2.1 分层策略

按 pytest 标记划分（这个数字可以用 `--collect-only -m` 直接核实）：

| 层 | 数量 | 特点 |
|----|------|------|
| 快速套件（`-m "not slow"`） | 196 | **不需要任何外部工具**，秒级完成 |
| 集成套件（`-m slow`） | 79 | 需要 JADX / Apktool / Androguard / 演示 APK |
| 合计 | 275 | |

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
| `test_backend_discovery.py` | 后端发现、平台差异、一个已知缺陷的 xfail 记录 |
| `test_cli.py` | CLI 命令真实执行 |
| `test_api.py` | REST 端点 |
| `test_androguard_integration.py` | 真实 DEX 解析 |
| `test_demo_app.py` | 端到端演示流程 |
| `test_docs.py` | 文档与资产完整性 |
| `test_apktool_smali.py` | Smali 路径定位与多 DEX 目录（v0.1.1 新增） |
| `test_smali_fallback_integration.py` | 无 JADX 时回退到 Smali 的端到端验证（v0.1.1 新增） |
| `test_first_party_samples.py` | 5 个自建样本的导入、索引、搜索与交叉引用（FIX-002 新增） |

### 2.2 几类值得注意的测试

**证据等级的不可提升性** —— 这是本项目最核心的安全属性，单独测：

```python
def test_model_supplied_claims_are_leads_not_verified():
    evidence = builder.add(
        EvidenceKind.BEHAVIOUR,
        EvidenceLevel.LEAD,
        "CONFIRMED VULNERABILITY: hardcoded credential",
        [],
    )
    assert evidence.level == EvidenceLevel.LEAD
```

一条措辞笃定的记录，被显式提交为 `lead` 时必须仍是 `lead`。

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

**根因：** Androguard 为了人类可读，把调用目标渲染成

```
Lcom/example/demo/Crypto;->sign(Ljava/lang/String; Ljava/lang/String;)
```

每个分号后有空格。而方法表里 `get_descriptor()` 返回的是规范形式

```
Lcom/example/demo/Crypto;->sign(Ljava/lang/String;Ljava/lang/String;)
```

我直接把前者当作 callee id 存储，**两者永远不可能相等**。

**为什么严重：** 这正是本项目「无法点回原处的结论不算结论」原则要防的失败模式，
而它伪装成了成功。

**修复：** 规范化解析（`_parse_dalvik_reference`）。

**新增测试：** 断言「任何 call target 不得含空白」+「必须有 target 能在符号索引中解析到」
+ 端到端通过公开 API 查一次调用者。

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

CI 一共红了 **4 次**，每次都是真问题：

| 次数 | 失败 job | 真实原因 |
|------|----------|----------|
| 1 | 5/6 | `uv sync --frozen` 缺 lock 文件；jadx 解压目录名假设错误；依赖审计 action 不存在；缺 `unzip` |
| 2 | 4/6 | 覆盖率门禁偷偷用了 `-m "not slow"`，把该测的代码排除掉了，报告 70% 而非 82% |
| 3 | 2/6 | 测试无条件 import Pillow，而 Pillow 在 CI 没装的 `demo` extra 里 |
| 4 | 1/5 | Smali 回退的集成测试依赖「JADX 不可用」，而我是用「把 `jadx_path` 指向不存在的目录」实现的 |

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

我没有修它（超出本次 Issue 范围），但也没有让它继续藏在注释里：
已加一个 `strict=True` 的 `xfail` 测试记录这个行为。**strict 意味着**
如果哪天它被修好了，这个测试会**失败**，强制有人回来摘掉标记——
这样它既不会被遗忘，也不会把一个 bug 固化成期望行为。

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

## 4. 需要你重点审核的判断

以下是我的主观决策，你可能有不同看法。

### 4.1 「后端失败是值，不是异常」

整个架构建立在这一条上：JADX/Apktool 对混淆代码失败是**常态**，
所以失败必须是一等公民（`ToolError`），挂在受影响的结果上，而不是中断整个分析。

**代价：** 错误处理代码明显增多，`Analyzer` 里有大量「记一笔然后继续」。
**收益：** 一个 APK 即使完全骗过 JADX，仍然产出 manifest、符号索引和报告。

**审核点：** 这个复杂度的取舍你认可吗？

### 4.2 交叉引用靠遍历字节码，而非用库的 xref 缓存

Androguard 4.x **移除了** xref 缓存（3.x 有）。所以调用边是从指令里扫出来的。

**代价：** 这是最贵的操作（真实 APK 上占大部分时间），所以有 instruction limit。
**收益：** 不依赖特定版本行为，跨版本稳定。

**审核点：** 接受自己实现 xref，还是引入 Ghidra 等工具做符号解析？

### 4.3 演示样本是自建的，不是抓来的第三方 APK

本机没有 Android SDK，但我发现 **Apktool 自带 aapt2，可以从 smali 直接构建 APK**。
所以 `examples/` 下的样本全是手写 smali 构建的真实应用，源码和重建脚本都在仓库里。
FIX-002 之后是 5 个：`demo-app`（通用）、`multidex-app`（两个 dex）、
`obfuscated-app`（单字母类名）、`strings-app`（字符串密集）、
`wide-app`（接口与实现层次）。

**代价：** 样本都很小（最大的不到 3 KB、5 个类），展示不出大型 APK 的表现。
**收益：** 完全自有、可重建、无第三方许可问题；陌生人克隆后立刻能跑。

### 4.4 我没有实现计划书里的部分内容

计划书 Phase 1 提到「测试 APK 从上传到阅读 AI 分析报告的闭环」——
**Phase 1 没有 AI**，这是计划书本身的设计（AI 在 Phase 2）。

但我确认：**关闭所有大模型 API 后，底层分析完全正常**——这是路线图的第一原则，已达成。

### 4.5 未做的部分（如实列出）

- **Web 工作台 / MCP / Agent**：Phase 2，尚未开始
- **大型 APK 压力测试**：5 个自建样本 + 2 个第三方样本覆盖了多 DEX、混淆、
  字符串密集、接口继承等布局，但都**很小**——最大的自建样本不到 3 KB。
  没有 10 万类以上的大型 APK 数据点，所以索引性能和指令上限从未被真实压测过
- **混淆代码的对抗性测试**：`obfuscated-app` 覆盖了短类名和短方法名，
  但它是**手写的**混淆，不是有控制流混淆的真实加固 APK
- **第三方的混淆/加固样本**：仓库不含此类文件（安全边界），需要时靠
  `scripts/fetch-fixtures.sh` 拉取

Phase 1 计划里的 5 个自建测试 APK 已由 FIX-002 补齐（见 3.10 节）。

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

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas

# v0.1.0（已发布）
git checkout v0.1.0
uv sync --extra dev --extra analysis
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=dexatlas --cov-report=term

# 安装后端后跑完整套件
bash scripts/install-backends.sh
uv run pytest          # v0.1.0 时为 208 passed

# v0.1.1（含 FIX-001）
git checkout v0.1.1
uv run pytest          # 244：243 passed + 1 xfailed

# main（含 FIX-002：5 个自建样本 + 演示视频）
git checkout main
uv run pytest          # 275：274 passed + 1 xfailed
```

集成测试依赖的第三方样本不入库，先拉下来：

```bash
bash scripts/fetch-fixtures.sh   # 拉 TestActivity.apk 和 multidex.apk
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
2. **把「空路径不能禁用后端」立为独立 Issue**（见 3.8 节末）。它是一个真实的、
   已被记录的缺陷，`strict` 的 xfail 会在它被修好时强制有人清理标记。
3. **优先补 Phase 1 的已知薄弱处**（如果评审认为必要）：
   - `cli/main.py` 覆盖率 70.1%，缺参数组合测试
   - 混淆样本的对抗性测试
4. **补充一份分析覆盖度文档**（尚未存在）：调研中发现 Androguard 用「哪些结论由哪个
   后端的哪个版本产出」作为可信度凭证，这比任何自述都有说服力。
5. **考虑把报告里的测试数字改成自动生成**。目前报告写死数字，每次新增测试都要手工
   同步——本次修复中这个测试失败了两次，都是它在正确地报警，但摩擦是真实的。
   （本条属于报告工具化，不在 FIX-001 范围内。）

---

## 附：提交历史

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
```

注意提交历史里 **9 次是修 bug**。这个比例偏高，但每个都在提交信息里写清了
「为什么写错了」和「为什么测试没抓到」——这比一次性的完美提交更有信息量。

其中 3.8 节记录的第 4 次 CI 失败，值得单独说一句：那个 bug 是**我自己的新测试**
在**我的机器上通过、在 CI 上失败**才暴露的。它不在原来的 208 个测试的覆盖范围内，
是这次改动引入的。**新写的测试自己也会有 bug**，这一点在这次修复里比任何文档都更有说服力。

而 3.10 节是这份历史里唯一一次**没有 bug、但仍然是错的**提交：
宣布完成的时候，验收清单已经被我改写过了。
