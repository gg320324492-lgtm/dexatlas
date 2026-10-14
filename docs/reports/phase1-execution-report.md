# Phase 1 执行报告 — DexAtlas v0.1.0

**日期：** 2026-10-14
**版本：** `v0.1.0`（tag `efa86d5`）
**仓库：** https://github.com/gg320324492-lgtm/dexatlas
**Release：** https://github.com/gg320324492-lgtm/dexatlas/releases/tag/v0.1.0

本报告供你审核。按路线图约定的评审机制，**Phase 1 已交付但评审尚未进行**，
Phase 2 的任务清单应在你的评审结论之后再写，而不是照搬原计划。

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
| 测试数 | 208（164 快 + 44 集成） | — |
| 一方代码覆盖率 | **87.8%**（1484/1691 行） | ≥80% |
| mypy | strict 通过 | strict |
| ruff | 通过 | 通过 |
| CI | 5 job 全绿（3.12 / 3.13 / Docker / 依赖审计 / lint） | 全绿 |
| Python 代码量 | 6975 行 / 42 文件 | — |
| 提交数 | 10 | — |

### 1.3 覆盖率分布（诚实披露薄弱处）

```
 70.7%  cli/main.py              46/157 未覆盖
 76.8%  tools/jadx/adapter.py    48/207 未覆盖
 82.4%  cli/console.py            6/34  未覆盖
 82.7%  tools/apktool/adapter.py 24/139 未覆盖
 85.7%  api/app.py              21/147 未覆盖
 88.5%  tools/androguard/adapter 20/174 未覆盖
```

**未覆盖的是什么：** 主要是错误分支（后端超时/非零退出后的恢复路径）和一些
CLI 参数组合。**不是**核心分析逻辑——`core/` 下的主要模块都在 90% 以上。

---

## 2. 测试是怎么设计的

这部分值得你重点审核，因为它决定了 87.8% 这个数字意味着什么。

### 2.1 分层策略

按 pytest 标记划分（这个数字可以用 `--collect-only -m` 直接核实）：

| 层 | 数量 | 特点 |
|----|------|------|
| 快速套件（`-m "not slow"`） | 164 | **不需要任何外部工具**，秒级完成 |
| 集成套件（`-m slow`） | 44 | 需要 JADX / Apktool / Androguard / 演示 APK |
| 合计 | 208 | |

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
| `test_backend_discovery.py` | 后端发现、平台差异 |
| `test_cli.py` | CLI 命令真实执行 |
| `test_api.py` | REST 端点 |
| `test_androguard_integration.py` | 真实 DEX 解析 |
| `test_demo_app.py` | 端到端演示流程 |
| `test_docs.py` | 文档与资产完整性 |

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

### 3.7 CI 反复失败暴露的问题

CI 一共红了 **3 次**，每次都是真问题：

| 次数 | 失败 job | 真实原因 |
|------|----------|----------|
| 1 | 5/6 | `uv sync --frozen` 缺 lock 文件；jadx 解压目录名假设错误；依赖审计 action 不存在；缺 `unzip` |
| 2 | 4/6 | 覆盖率门禁偷偷用了 `-m "not slow"`，把该测的代码排除掉了，报告 70% 而非 82% |
| 3 | 2/6 | 测试无条件 import Pillow，而 Pillow 在 CI 没装的 `demo` extra 里 |

第 2 次尤其值得注意：**门禁本身是坏的**。它报告的 70% 和真实的 82% 都不是问题，
问题是它测的东西和它声称测的东西不一样。

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
所以 `examples/demo-app/` 是手写 smali 构建的真实应用，源码和重建脚本都在仓库里。

**代价：** 演示样本很小（3KB、5 个类），展示不出大型 APK 的表现。
**收益：** 完全自有、可重建、无第三方许可问题；陌生人克隆后立刻能跑。

### 4.4 我没有实现计划书里的部分内容

计划书 Phase 1 提到「测试 APK 从上传到阅读 AI 分析报告的闭环」——
**Phase 1 没有 AI**，这是计划书本身的设计（AI 在 Phase 2）。

但我确认：**关闭所有大模型 API 后，底层分析完全正常**——这是路线图的第一原则，已达成。

### 4.5 未做的部分（如实列出）

- **Phase 1 计划里的 5 个测试 APK**：只有 1 个自建 + 3 个外部拉取的样本，
  且外部样本不在仓库里（靠 `scripts/fetch-fixtures.sh`）
- **Web 工作台 / MCP / Agent**：Phase 2，尚未开始
- **多 DEX 真实压力测试**：多 DEX 支持有单元测试，但没有用真实的多 DEX 大型 APK 验证
- **混淆代码的对抗性测试**：有 XXE 和畸形输入测试，但没有真正的混淆 APK 样本

---

## 5. 安全边界执行情况

本项目的硬边界，逐条核对：

| 边界 | 执行情况 | 验证方式 |
|------|----------|----------|
| 仓库不含第三方 APK | ✅ | `git ls-files` 实际校验，不只信 .gitignore |
| 唯一的 .apk 是自建演示样本 | ✅ | 有 smali 源码 + 重建脚本，测试强制 |
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
git checkout v0.1.0

uv sync --extra dev --extra analysis
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=dexatlas --cov-report=term

# 安装后端后跑完整套件
bash scripts/install-backends.sh
uv run pytest          # 应为 208 passed
```

CI 记录：https://github.com/gg320324492-lgtm/dexatlas/actions

---

## 7. 建议的下一步

按路线图的评审协议，**在你审阅之前不应该开始 Phase 2**。如果你认可当前状态，我建议：

1. **Phase 2 的 Issue 从评审结论写起**，而不是从原计划写。原计划里对 Agent 架构的
   设想是基于「代码不存在」时的假设，现在有真实代码了。
2. **优先补 Phase 1 的已知薄弱处**（如果评审认为必要）：
   - `cli/main.py` 覆盖率 70.7%，缺参数组合测试
   - 多 DEX / 混淆样本的对抗性测试
3. **补充一份分析覆盖度文档**（尚未存在）：调研中发现 Androguard 用「哪些结论由哪个
   后端的哪个版本产出」作为可信度凭证，这比任何自述都有说服力。

---

## 附：10 次提交

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
```

注意提交历史里 **6 次是修 bug**。这个比例偏高，但每个都在提交信息里写清了
「为什么写错了」和「为什么测试没抓到」——这比一次性的完美提交更有信息量。
