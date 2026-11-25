# Upwork 素材发布前核对（publish review）

> **本文件是一次校对记录，不是发布动作。** 本轮没有向 Upwork 或任何其它
> 平台提交、发布、复制或发送任何内容；没有调用任何模型 API。四份素材仍然是
> 草稿，状态是「Draft for review — not published」。
>
> **内部核对记录——不对外、不作附件、不随提案发送。** 本文件只留在仓库里：
> 它记着核对基准、提交号与本机路径，那些是给自己看的；对外发出去的只有同
> 目录下的四份素材本身。
>
> **核对基准：** `v1.0.0` 发版树（tag `v1.0.0`，2026-11-17），commit `8f9ddca`
> ——四份素材与本文件的最后一次改动都在这个发版 commit 里。更早一轮的核对以
> `claude/upwork-check` @ `8868e30` 为基准，那一轮的历史值在下文各自标了出处。

---

## 0. 核对基准与数据来源

| 要核对的量 | 取值 | 来源（仓库内可复核） |
|---|---|---|
| 测试总数 | 1,866（1,717 快 + 149 集成） | `docs/reports/phase1-execution-report.md` 的 `<!--fig:tests.total-->` / `tests.fast` / `tests.slow` |
| 一方代码覆盖率 | 93.3%（7,467 / 8,001 行） | 同上的 `<!--fig:coverage.pct-->` / `coverage.covered` / `coverage.total`；`docs/status.md` 同值 |
| MCP 只读工具数 | 11 | `src/dexatlas/mcp/server.py` 实际注册的 `@server.list_tools()`；`README.md` 与 `docs/architecture/workbench.md` 均写 “eleven” |
| case study 数 | 3 | `docs/case-studies/README.md`：「Three complete walkthroughs」，三篇正文标题即 *Case study 1/2/3* |
| M6 层级 2 实测 | 49/60 = 81.7%（逐轮 15/16/18），未达验收线 | `docs/benchmarks/m6-level2-retest4.md` |
| M6 窄验证二轮 | 转通过 2/6（门槛 ≥4），未达标 | `docs/benchmarks/m6-level2-narrow-verify2.md` |
| M6 窄验证三轮 | 转通过 3/6（门槛 ≥4），未达标 | `docs/benchmarks/m6-level2-narrow-verify3.md` |
| 最新已发布版本 | `v1.0.0`（tag 2026-11-17；`src/dexatlas/__init__.py` 的 `__version__` 是 `1.0.0`） | `git tag` / `src/dexatlas/__init__.py` |

报告里的数字由 `scripts/refresh-report-figures.py` 从真实测量生成，**本轮没有手改任何
`<!--fig:...-->` 标记**，只按它们已落盘的值改写对外文案。

> **一处事实错误的更正（本轮改）。** 上一版把 M6 窄验证的结果记成「**二轮**
> 转通过 **3/6**」——**3/6 是三轮的结果**（`docs/benchmarks/m6-level2-narrow-verify3.md`
> 第 59–61 行：转通过 3/6，门槛 ≥4，未达判据）；**二轮是 2/6**
> （`docs/benchmarks/m6-level2-narrow-verify2.md` 第 59–61 行：转通过 2/6，同样
> 未达判据）。两轮都未通过，结论不变，但数字各归各轮，现已按轮次分列。

---

## 1. 对外数字核对：4 处不一致，已全部改正

四处都是**文案比仓库落盘值旧**（写的是更早一次测量的数字），不是夸大。改正后
数字与 `docs/reports/phase1-execution-report.md` 逐字一致。

| # | 文件 | 修正前 | 修正后 | 落盘真值 |
|---|---|---|---|---|
| 1 | `project-brief.md` §Short description | `~1,540 automated tests, 93.1% coverage` | `1,829 automated tests, 91.1% coverage` | 1,612 / 93.3% |
| 2 | `project-brief.md` §Deliverables | `~1,540 tests, coverage and dead-code gates` | `1,829 tests, coverage and dead-code gates` | 1,612 |
| 3 | `scope-backend-automation.md` §What I offer | `~1,540 tests at 93.1% coverage` | `1,612 tests at 93.3% coverage` | 1,612 / 93.3% |
| 4 | `cover-letter-templates.md` Template 1 | `~1,540 automated tests at 93.1% coverage` | `1,612 automated tests at 93.3% coverage` | 1,612 / 93.3% |

覆盖率的措辞保持「一方代码覆盖率」的口径，没有写成「总覆盖率」——报告里
`coverage.pct` 量的就是一方代码。

## 2. 事实性错误：3 处，已全部改正

| # | 文件 | 修正前 | 修正后 | 依据 |
|---|---|---|---|---|
| 5 | `project-brief.md` §Deliverables | `Read-only MCP server. Ten tools over stdio` | `Eleven tools over stdio` | server.py 注册 11 个工具；`README.md` 与 `docs/architecture/workbench.md` 写 “eleven” |
| 6 | `scope-ai-mcp.md` §What I offer | `a read-only MCP server (ten tools over stdio)` | `(eleven tools over stdio)` | 同上 |
| 7 | `project-brief.md` §Short description | `two end-to-end case studies` | `three complete case studies` | `docs/case-studies/` 下是三篇（demo / obfuscated / api-integration）；`end-to-end` 只适用于第 1 篇，改用仓库自己的说法 “complete” |

`cover-letter-templates.md` Template 2 里原本就写的 `eleven tools over stdio` 是对的，
未改动——这也说明同一批素材里的工具数曾经自相矛盾（10 / 10 / 11）。

## 3. 版本措辞：1 处，已收紧（并随发版改过一次）

| # | 文件 | 修正前 | 修正后（现文件里的版本句） |
|---|---|---|---|
| 8 | `project-brief.md` §Honest limitations | `in early development (v0.2.x)` | `The current release is v1.1.0 (tagged 2026-11-25)` |

`v0.2.x` 不是一个 tag，也不是一个可核对的版本号，所以第一轮把它收紧成了当时
真实存在的 `v0.2.0`（那一版的意思是「当前最新版本就是 v0.2.0」）。这种句子要靠
`scripts/check-version-claims.py` 验证。**但它说的是「当前最新版本」，所以每发
一个版就会过期，必须随发版一起改**，见 §7 第 1 条。

**发版已落地，这一句已经按 §7 第 1 条改过一遍。** `v1.0.0` 于 2026-11-17 打上
tag（`git for-each-ref refs/tags/v1.0.0`），`src/dexatlas/__init__.py` 的
`__version__` 是 `1.0.0`，`project-brief.md` §Honest limitations 现在写
`The current release is v1.1.0 (tagged 2026-11-25)`，后半句是
`; the public contract covers the documented CLI/API/MCP surfaces.`。
**下次发版仍要按 §7 第 1 条回来改这一句。**

---

## 4. 证据包与链接核对

### 4.1 引用到的文件是否真实存在

四份素材里现在一共 **12** 条相对链接，**逐条打开确认存在**。条数按
`tests/test_docs.py::test_all_relative_links_resolve` 自己的正则口径数
（`\[[^\]]*\]\((?!https?://|#|mailto:)([^)\s]+)`）——上一版记的 11 条漏了下面
「用法说明 / 字段长度」那一条：

| 引用位置 | 链接目标 | 存在 |
|---|---|---|
| `project-brief.md` §Links | `../case-studies/README.md` | ✅ |
| `project-brief.md` §Links | `../case-studies/attachments/demo-evidence-package.zip` | ✅ |
| `project-brief.md` §Links | `../case-studies/attachments/obfuscated-evidence-package.zip` | ✅ |
| `project-brief.md` §Links | `../case-studies/attachments/api-integration-evidence-package.zip` | ✅ |
| `cover-letter-templates.md` 头部 | `scope-backend-automation.md` | ✅ |
| `cover-letter-templates.md` 头部 | `scope-ai-mcp.md` | ✅ |
| `cover-letter-templates.md` 头部 | `project-brief.md` | ✅ |
| `cover-letter-templates.md` 用法说明 | `publish-review.md`（本文件，字符计数口径那一条） | ✅ |
| `cover-letter-templates.md` 用法说明 | `../case-studies/attachments/demo-evidence-package.zip` | ✅ |
| `cover-letter-templates.md` 用法说明 | `../case-studies/attachments/obfuscated-evidence-package.zip` | ✅ |
| `cover-letter-templates.md` 用法说明 | `../case-studies/attachments/api-integration-evidence-package.zip` | ✅ |
| `cover-letter-templates.md` 用法说明 | `publish-review.md`（本文件，字段长度那一条） | ✅ |

`scope-ai-mcp.md` 与 `scope-backend-automation.md` 里没有相对链接（对外只给仓库
网址与平台指南链接）。

这些链接是**相对 markdown 链接**，所以 `tests/test_docs.py::test_all_relative_links_resolve`
每次跑都会强制它们存在——链接指向不存在的路径，测试就会红。修正前这些位置用的是
纯文本（`docs/case-studies/README.md`），检查器管不到；现在是能自动验证的。

### 4.2 证据包与 case study 的对应关系

`docs/case-studies/attachments/` 下共 9 个文件，三个证据包与三篇 case study
一一对应，没有多余也没有缺失（对应的是**附件集合**，不是说每篇带的报告都不同
——见下面的字节比对）：

| case study | 引用的附件（4 个） | 证据包 zip 内容 |
|---|---|---|
| `demo-app-walkthrough.md` | `demo-report.md` / `.json` / `.html` + `demo-evidence-package.zip` | `reports/report.html`、`reports/report.json`、`reports/report.md`、`manifest.json` |
| `obfuscated-app.md` | `obfuscated-report.md` / `.json` / `.html` + `obfuscated-evidence-package.zip` | 同上 4 项 |
| `api-integration.md` | `demo-report.md` / `.json` / `.html` + `api-integration-evidence-package.zip` | 同上 4 项 |

三个 zip 都已解压核对，内含报告三件套与一份 `manifest.json`（哈希清单），不是空壳。
素材里对外的描述（「a zip holding the report and a manifest of hashes」）与内容一致。

**一处必须说明的事实：demo 与 api-integration 两个证据包里的报告是同一份。** 把两个
zip 解开逐文件比对，`reports/report.md` 与 `reports/report.html` **字节完全相同**
（sha256 前 16 位同为 `1594a0c19aa6c165` / `82bcb84c37db4f64`），只有
`reports/report.json` 与 `manifest.json` 不同。两边的 `manifest.json` 也写明是同一次
分析：APK sha256 同为 `80a8fe0e…`，`run_id` 同为 `run_e112e717…`。原因是 case
study 1 与 case study 3 分析的是**同一个**一方样本 `examples/demo-app/demo.apk`
——case study 3 走的是 REST API / MCP 入口，不是另一个样本。

**样本数与分析数不是一回事。** 三篇走查涉及**三个**一方样本：`demo.apk`
（case study 1 与 3）、`obfuscated.apk`（case study 2）、`multidex.apk`（case study 2
的 multi-DEX 附录）。但**三个证据包只覆盖两份分析**——demo 包与 api-integration 包是
同一次分析（所以报告字节相同），obfuscated 包是另一次分析（`run_id`
`run_8d6735d4…`）；`multidex.apk` 没有单独的证据包。对外不要读成三份独立分析，
更不要读成三个客户案例。素材侧已各加了一句澄清（`project-brief.md` §Links、
`cover-letter-templates.md` 用法说明）。

### 4.3 素材里没有指错的东西

- `project-brief.md` §Links 原来只指到 `docs/case-studies/README.md`，读者拿不到
  可以直接打开的证据包；现在补齐了三个 zip 的确切路径。
- 三个 case study 的附件引用在 `docs/case-studies/` 内原本就是对的，本轮未改动。

---

## 5. 字段长度核对（实测字符数）

口径：**raw** = Markdown 源码字符数（人从文件里复制的内容）；**plain** = 去掉
Markdown 语法（`**粗体**`、列表符号、`>` 引用）后的正文字符数（粘进表单框的
内容）。取两者较大者判定，所以口径是保守的。门限：**标题 ≤60、简介 ≤5,000**
（Upwork 作品集指南，见素材顶部的链接）；**提案正文 ≤2,500**（本轮按较严的
常用值取，模板按此留余量）。

**切分规则**：`## ` 标题开一节；一节到下一个 `## ` 标题、或到单独一行的
`---` 分隔线为止；节正文不含标题行本身，首尾空行不计。**plain 的清洗规则**
（逐行）：`` `代码` `` → 内容、`**粗体**`/`*斜体*` → 内容、列表符号
（`- ` / `1. `）→ 4 空格缩进、`> ` 引用符 → 去掉、Markdown 链接
（方括号包文字、圆括号包地址）→ 只留文字、`#` 标题符 → 去掉、行尾空白去掉，
首尾空行不计。

下面这段脚本就是口径本身，**表里的每个数字都能用它复算**（纯标准库，不写
任何测量产物）：

```bash
python - <<'EOF'
import pathlib, re
def sections(path):
    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    out, name, cur = [], None, []
    for l in lines:
        if l.startswith("## "):
            if name is not None: out.append((name, cur))
            name, cur = l[3:].strip(), []
        elif l.strip() == "---":
            if name is not None: out.append((name, cur)); name, cur = None, []
        elif name is not None:
            cur.append(l)
    if name is not None: out.append((name, cur))
    return out
def strip_md(text):
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    out = []
    for l in text.splitlines():
        l = re.sub(r"^\s*(-|\d+\.)\s+", "    ", l)
        l = re.sub(r"^>\s?", "", l)
        l = re.sub(r"^#+\s*", "", l)
        out.append(l.rstrip())
    while out and not out[0].strip(): out.pop(0)
    while out and not out[-1].strip(): out.pop()
    return "\n".join(out)
for path in ["docs/outreach/cover-letter-templates.md", "docs/outreach/project-brief.md",
             "docs/outreach/scope-ai-mcp.md", "docs/outreach/scope-backend-automation.md"]:
    raw = len(pathlib.Path(path).read_text(encoding="utf-8").strip("\n"))
    print(f"### {path} 全文 raw={raw} plain={len(strip_md(pathlib.Path(path).read_text(encoding='utf-8')))}")
    for name, body in sections(path):
        text = "\n".join(body).strip("\n")
        print(f"    {name:<50} raw={len(text):>6} plain={len(strip_md(text)):>6}")
EOF
```

| 字段 | 文件 | raw | plain | 门限 | 判定 |
|---|---|---:|---:|---:|---|
| **Project title** | `project-brief.md` | **53** | 53 | 60 | ✅ |
| Role | `project-brief.md` | 438 | 438 | 5,000 | ✅ |
| **Short description** | `project-brief.md` | 1,410 | 1,404 | 5,000 | ✅ |
| Skills | `project-brief.md` | 311 | 271 | 5,000 | ✅ |
| Deliverables shown in the repository | `project-brief.md` | 1,455 | 1,437 | 5,000 | ✅ |
| Third-party components (attribution) | `project-brief.md` | 458 | 452 | 5,000 | ✅ |
| Honest limitations | `project-brief.md` | 426 | 428 | 5,000 | ✅ |
| Links | `project-brief.md` | 1,178 | 947 | 5,000 | ✅ |
| 全文（附件） | `scope-backend-automation.md` | 4,950 | 4,941 | 5,000 | ✅ |
| §What I offer（粘贴段） | `scope-backend-automation.md` | 592 | 588 | 5,000 | ✅ |
| 全文（附件） | `scope-ai-mcp.md` | **6,561** | **6,530** | 5,000 | ❌ 超（见 §5.2） |
| §What I offer（粘贴段） | `scope-ai-mcp.md` | 781 | 773 | 5,000 | ✅ |
| Template 1 正文 | `cover-letter-templates.md` | 2,185 | 2,174 | 2,500 | ✅ |
| Template 2 正文 | `cover-letter-templates.md` | **2,500** | 2,485 | 2,500 | ⚠ 压线（见 §5.3） |

> 本轮重出整表：`Template 1` / `Template 2` / `scope-backend §What I offer`
> 三行的旧值（2,216 / 3,005 / 621）在文件上**无法复算**，原因是旧表用的是
> 另一套清洗口径且值已过期；现在表、口径、脚本三者同源，数字逐字可复算。

### 5.1 标题：唯一超出平台字段门限的字段，已改正

| | 修正前 | 修正后 |
|---|---|---|
| 标题 | `DexAtlas — Evidence-First Android APK Analysis Platform (Python, REST API, MCP, AI Agent)` | `DexAtlas — Evidence-First Android APK Analysis` |
| 字符数 | **89**（超 ≤60 门限 29） | **53** |

去掉的技术关键词没有丢：`Python` / `REST API` / `MCP` 仍在 §Skills 与
§Short description 里。

### 5.2 `scope-ai-mcp.md` 全文超出 5,000 —— 未擅自删改，列为人工确认项

- 它是**提案附件**，不是平台字段：按 `cover-letter-templates.md` 的用法说明，
  「Attach the matching scope document」。
- 若目标是 5,000 字符的简介框，可粘贴的是 **§What I offer（plain 773 字符）**，
  这一点已经写进该文件的头部（§Where this goes），附件本体不受长度限制。
- 把整篇压到 5,000 以内要删掉约 1,500 字符的承诺性文字（排除条款、验收条款、
  模型预算边界），这是**编辑判断而不是校对**，所以本轮没有替人做这个决定。
- **若确认要整篇粘贴**，按 §7 第 3 条处理。

### 5.3 另按提案正文常规上限复核（需在真实表单上确认）

Upwork 提案正文的常规上限是 2,500 字符，比作品集简介的 5,000 更严。本轮已按
这个更严的口径裁过 Template 2：

| | raw | plain | 对 2,500 |
|---|---:|---:|---|
| Template 1 正文 | 2,185 | 2,174 | ✅ 未超（余 315） |
| Template 2 正文 | 2,500 | 2,485 | ⚠ 正好压线（余 0） |

Template 2 的正文原为 **raw 2,966 / plain 2,951**（超 2,500 门限 466），本轮
裁掉重复表述与三处交付物的冗长示例，保留了全部 10 个占位符与实质内容（受控
工具、可核查引用、模型输出只是线索、成本与上限、范围边界、自建作品示例、三个
提问），现为 raw 2,500 / plain 2,485。

> **口径更正（上一版这里记的是另一个口径下的值）。** 旧记录写的「**3,152** 字符
> （超 652）」是**不按 `---` 分隔线切节**算出来的——那一版把文件级页脚
> （`*Draft for review — not published…*`）并进了最后一节。**按 §5 现在的口径
> 复算同一份裁剪前的文件**（`git show 0dd3b09^:docs/outreach/cover-letter-templates.md`），
> Template 2 是 raw 2,966 / plain 2,951，超门限 466；去掉 `---` 切分规则再算，
> 才是 3,152 / 3,135。**复算方法：** 把裁剪前的文件取到临时副本目录、按 §5 的
> 脚本原样跑一遍（脚本里的路径写死为 `docs/outreach/…`）。

**发送前仍须重算**：占位符替换后通常比示例长，而用法说明要求删去不适用
的小节——两者方向相反，所以以**实际粘贴的那一版**为准，用 §5 的脚本复算。

---

## 6. 措辞核对：不宣称未达成的里程碑

| 检查项 | 结果 |
|---|---|
| 「已发布服务页」 | ✅ 四份文件首尾都写着 `Draft for review — not published`，没有任何「已上线 / 已发布服务」的措辞 |
| 「M6 已达标」 | ✅ 四份文件**完全没有提到 M6 或层级 2**。M6 层级 2 实测 49/60 = 81.7%（未达 ≥90% 验收线），窄验证二轮转通过 2/6、三轮 3/6（门槛 ≥4），三件事都还没关闭 |
| 「独立验收已完成」 | ✅ 四份文件**没有提到 M10**，也没有把 DexAtlas 自身的验收说成已完成；`docs/status.md` 写着 M10 独立验收尚未开始，素材口径与之一致。素材里出现的 acceptance / milestone 全部是**对客户的服务承诺**（开工前写下的验收标准、里程碑复盘），不是对本项目分析工作的验收结论 |
| 「已验证可复现」类措辞 | ✅ 只在有落盘证据处使用：`docs/case-studies/` 的三篇走查、三个证据包、CI 配置 |
| 「自主发现漏洞 / 替代分析师」类措辞 | ✅ 两份 scope 都明确排除，`project-brief.md` §Honest limitations 也写明 agent 不是通用自主漏洞发现器 |
| 「把 APK 里的指令当数据而非命令」 | ✅ 有实现支撑：`src/dexatlas/agent/orchestrator.py` 的系统提示把工具输出定性为不可信数据，MCP 侧有 `UntrustedText` 包装，`tests/test_agent_untrusted_input.py` 是对应的性质测试 |
| 第三方归属 | ✅ 三个分析引擎各自点名，注明不是自有工作 |

**没有发现夸大之处。** 发现的问题都是**少说**（11 个工具说成 10、三篇说成两篇、
旧一轮的测试数与覆盖率），因此这一轮没有需要下调的表述。

### 需要注意的是反向风险

素材里**现在不引用** M6 的 49/60 = 81.7%。这本身不违规（不提即不宣称），但如果
发布时想在服务页上写「agent 实测准确率」，必须同时写明**未达验收线**，否则就是
本项目 CLAUDE.md 第 2 条禁止的「无人能复算的断言」。

---

## 7. 发布时仍需人工确认的事项

按重要性排序。**这一节是发出去之前的最后一关**：下面每一条要么只能在真实表单
上看，要么要人决定，仓库里的门禁替不了。

1. **版本号会过期（`v1.0.0` 已发，下一个版本还要再改）。**
   `project-brief.md` §Honest limitations 现在写
   `The current release is v1.1.0 (tagged 2026-11-25)`——这句是真的
   （`git for-each-ref refs/tags/v1.0.0`），但它说的是「当前最新版本」。
   **再发一个 tag，这句就变成假话**，`scripts/check-version-claims.py` 会直接
   报出来。发版 commit 之后要回来改这一句。
2. **两封信的正文长度按 2,500 再核一次。** Template 1 模板态 raw 2,185 /
   plain 2,174，Template 2 raw 2,500 / plain 2,485（**正好压线，余 0**）。
   占位符替换后通常比示例长，用法说明又要求删去不适用的小节，两者方向相反，
   所以要以**实际粘贴的那一版**复算（§5.3）。
3. **`scope-ai-mcp.md` 到底是「整篇做附件」还是「只贴 §What I offer」。**
   整篇 raw 6,561 / plain 6,530，超过 5,000；本轮按「附件 + 只贴 What I offer
   （plain 773）」处理，并把这条说明写进了文件头部。若要整篇粘贴，需要再压约
   1,500 字符——那是编辑判断，本轮没有替人做这个决定（§5.2）。
4. **平台真实字段限制要在真实表单上复核。** 本轮用的是任务给定的门限（标题
   ≤60、简介 ≤5,000）。Upwork 实际限制会随时间调整，素材头部本来就有
   「Character limits should be re-checked against the live form」的提示——发版前
   请在真实表单上逐个字段确认。**素材顶部引用的官方指南链接也要联网核实**
   （`support.upwork.com/hc/en-us/articles/360016144974`）：本轮**没有联网**，
   那条链接与其中的限制值都还没对过现网。
5. **对外数字要跟最后一次测量同步。** 本轮的 1,612 / 93.3% 取自最近一次完整
   测量落盘的报告（源指纹 `sha256:4e72ac49…`）——完整测量已重跑，这四份素材的
   数字已按新值核过一遍。**以后任何一次测量都会再改这两个数**，发版前请再核
   一次。
6. **`{{...}}` 占位符全部替换后才能发。** 模板里的占位符若漏改会直接发出去。
   Template 1 有 11 处、Template 2 有 10 处；改完逐个搜 `{{` 确认没有残留。
7. **联系方式与可用性要按平台要求补齐。** 四份素材现在是**零联系方式、零时区、
   零可用性表述**（只有仓库网址）——素材刻意不写这些，但平台表单通常要填。
   补的时候只写本人真实可用的联系方式与时区，不要虚构响应时长。
8. **附件要逐个确认真的上传了。** 三个证据包 zip 要分别附上；注意 **demo 与
   api-integration 两个证据包里的 `report.md` / `report.html` 是同一份分析报告**
   （字节相同，只有 `report.json` 与 `manifest.json` 不同）——附的时候不要当成
   两份独立证据报数。§4.2 与素材侧的澄清句就是为了这件事。
9. **打包外发时逐个选文件，不要把内部核对记录一起发出去。**
   `docs/outreach/publish-review.md`（本文件）**只留在仓库里**，不对外、不作
   附件、不随提案发送——它记着核对基准、提交号与本机路径。素材里指向它的两处
   都已经注明「那是内部记录」。
10. **不要在发布文案里出现收益、工时节省或客户案例。** 四份素材目前都守住了
    「个人开源项目、无客户」的边界，改写时不要破坏它。

---

## 8. 门禁结果

在 `v1.0.0` 发版树（改动所在的 worktree，独立 venv）执行：

| 门禁 | 结果 |
|---|---|
| `uv run --no-sync pytest tests/test_docs.py` | **60/60 通过，0 跳过** |
| `uv run --no-sync python scripts/check-doc-citations.py` | 220 citations，unresolved 0，**drifted 0** |
| `uv run --no-sync python scripts/check-version-claims.py --base auto` | **exit 1**，findings 3 条：2 条历史遗留（`docs/releases/v0.2.0.md`、`CHANGELOG.md` 里的旧版本覆盖率）+ 1 条 `docs/reports/outreach-recheck.md` 自己的过期事实。**本轮改动没有新增任何 finding**：改动前先跑一遍、再改动后跑一遍，两次输出逐字相同（都是 exit 1、同 3 条） |
| §5 字符表复算（§5 的脚本，逐字抽取执行） | **14/14 一致** |

`check-doc-citations.py` 与 `check-version-claims.py` 都只读文档与 git，不写报告
数字；本轮**没有跑** `scripts/refresh-report-figures.py`，也没有跑任何 coverage
命令，因此没有触碰任何测量产物。

> **那第 3 条 finding 不在素材里，但它让这道门禁现在就是红的。** 它落在
> `docs/reports/outreach-recheck.md` 第 60 行——二次核对报告把**当时**的检查器
> 输出整段引了进去，那段引文里有「the newest is v0.2.0」；`v1.0.0` 打上 tag
> 之后，这句引文本身成了过期事实，检查器于是把它当成本树的新 finding，退出码 1。
> 素材侧与本文件侧都没有这个问题（§3 的版本句已按 §7 第 1 条改成 `v1.0.0`）。
> **要清掉它得改 `docs/reports/` 里的那份报告，不在本轮范围内**——本轮只动
> `docs/outreach/`。

> **复现这条门禁时的一个坑：** `uv sync` 只装 `--extra dev` 时，
> `tests/test_mcp_tools.py` 与 `tests/test_public_contracts.py` 会因为缺 `mcp`
> 包而**收集失败**（这两个文件共 51 个测试），`test_docs.py` 于是报「报告说
> 1,588，树上只有 1,537」。要复现报告里的套件口径，需要装齐全部 extra：
> `uv sync --extra dev --extra analysis --extra mcp --extra demo`（装齐后收集到
> 1,612，与报告一致，`test_docs.py` 才 62/62）。

### 额外发现：并发测量会污染覆盖率（发版那一轮已重跑并落盘）

在 `E:\Dexatlas`（共享树，本轮**未改动**）里，`docs/reports/phase1-execution-report.md`
的未提交改动**一度**把覆盖率写成了 **35.4%（2,699/7,631）**，弱模块表里
`core/pipeline.py` 18.2%、`cli/main.py` 23.0%、`tools/androguard/worker.py` 0.0%——
这是多会话并发测量互相清掉 `.coverage` 之后的残缺结果，不是当时的真值（v1.1.0
发版时是 93.3%：7,117/7,631；Phase 5 W2 的测量轮已随代码变化更新，见下）。按项目已有的经验（并发测量会污染覆盖率），**共享树的发版测量需要
重跑并核对弱模块表**才能落盘。**发版那一轮已照此重跑并落盘**：弱模块表复原
（`tools/androguard/worker.py` 72.3%、`tools/apktool/adapter.py` 93.1%），
测量脚本也已改成每次用私有数据文件 + 同 checkout 互斥槽位，不会再被并发顶掉。
**当前 `docs/reports/phase1-execution-report.md` 落盘的是最近一轮完整测量的值**
（1,866 tests / 93.3%，7,467/8,001 行；Phase 5 W2 与 P1 修复后的测量轮）。

---

*本文件是校对记录，不是发布记录。素材仍然是草稿：没有提交、发布、复制或发送
到任何平台。*
