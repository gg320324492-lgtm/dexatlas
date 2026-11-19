# M10 验收材料 —— 第三轮缺口的逐条处置记录

> **本文件的性质：** 逐条记录第三轮[读者视角预演](m10-reader-rehearsal-3rd.md)查出的
> 缺口，这一批把哪些改了、怎么改的、依据是什么，以及**还剩什么没解决**。
>
> **它不是验收结论。** 40 个验收项在这里一条也没有被判「通过」——判定只能来自
> 未参与实现的读者亲手执行。
>
> **纯文档改动。** 本批只改 `docs/reports/` 下的四份 M10 材料，没有动任何 `.py`，
> 因此**源码指纹不变**，报告里的测量数字保持有效；没有跑
> `scripts/refresh-report-figures.py`。
>
> **本文件未登记进 `scripts/check-doc-citations.py` 的文档清单**（按分工留给主会话
> 统一登记），因此它不在引用检查器的覆盖范围内，里面的 `file:line` 引用是逐条
> 手工核过的。

---

## 0. 这一批的基线

| 项 | 值 |
|---|---|
| 处置日期 | 2026年11月19日 |
| 依据 | [第三轮预演](m10-reader-rehearsal-3rd.md)（§3 卡住 1 条、§4 误读 3 条、§6 四项判据缺口、§7 一项没判据） |
| 改动的文件 | `m10-acceptance-pack.md`、`m10-reader-package.md`、`m10-invitation-final.md`、`m10-review-record-template.md`；另有一处**等行数**的重锚：`m10-reader-rehearsal-2nd.md` 的一条引用（见 §3.3，原因是本批改读者包把它的行号带偏） |
| 未动的文件 | `docs/architecture/public-contracts.md`（契约表是对的）、`v1.1.0-candidates.md`、`platform-gate-inventory.md`、`c5-c6-status-alignment.md`、`docs/reports/README.md`、`scripts/`、`tests/` |
| 实跑环境 | Windows 11 Pro 10.0.26300 · Python 3.12.10 · uv 0.11.21 · JDK 21.0.11 · jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4（三个后端齐备）· 工作区 `.scratch/ws` · REST 起在 8123 |

**实跑清单**（这一批给出的每条命令都跑过，输出抄进材料）：

| # | 跑了什么 | 结果 |
|---|---|---|
| 1 | `dexatlas analyze examples/demo-app/demo.apk -o/--json/--html` | `✓ apk_80a8fe0e81204c9f — 5 classes, 8 methods, 23 call sites, 21 call edges, 1 resource string (6.6s)` |
| 2 | 读 `report.json` 的 `evidence[]` | 顶层键 `detail/id/kind/level/provenance/summary`；`provenance[]` 元素含 `tool/tool_version/apk_sha256/locator`；E-0004–E-0006 各两条 provenance |
| 3 | MCP `resolve_locator` × 5 类 locator（bash） | 五行 `resolved=True/False` 全部拿到（见 §1.2 的表） |
| 4 | 同上（PowerShell 5.1） | 输出逐行相同 |
| 5 | MCP `get_evidence`（E-0004） | `provenance` 是**只含 locator 的字符串数组** |
| 6 | REST `GET /projects/{pid}/evidence` | 与 JSON 报告同形状（`provenance` 是对象数组） |
| 7 | REST 六类端点各一条命令 | 状态码与形状全部与材料相符；只有 `/runs` 的 `total` 需要改（§3.2） |
| 8 | `dexatlas export … -o evidence.zip` + 读 `manifest.json` | 4 个条目；`not_included` 三键 `apk` / `full_sources` / `unrelated_strings`；`files` 三条 |

**未实测的：** Docker 路线（本批不涉及）；`v1.0.0` tag 树上的材料（tag 尚未重打，
见 §5）。

---

## 1. 三条新缺口

### 1.1 M-8 【★ C1】evidence 的「工具、版本、locator」不在 JSON 顶层

**预演说的是什么**（§4 M-8）：JSON 报告里一条 evidence 记录的顶层键是
`['detail','id','kind','level','provenance','summary']`——`tool`、`tool_version`、
`locator` 在顶层**取不到**（读到 `None`）；它们在 `provenance[]` 数组里。而且
**两个传输的形状不一样**：MCP 的 `get_evidence` 返回的 `provenance` 是**字符串
数组**（只有 locator，没有工具与版本）。预演的判断是「极可能记成『C1 不通过：
字段为空』」——C1 是 ★ 阻断项，判据写着「字段不得为空」。

**改成了什么**

| 位置 | 改动 |
|---|---|
| [准备包 C1](m10-acceptance-pack.md) | 判据里补一段「**这四个字段各在哪**」：顶层只有六个键，**`level` 在顶层**，**工具/版本/locator 在 `provenance[]`**（元素含 `tool`/`tool_version`/`apk_sha256`/`locator`），**一条记录可能有不止一条 provenance**；MCP 侧是只含 locator 的字符串数组 |
| [准备包 C3](m10-acceptance-pack.md) | 补一句「**`level` 字段就在 evidence 记录的顶层**（工具、版本、locator 在 `provenance[]` 里，见 C1）」 |
| [读者包 §3.4](m10-reader-package.md) | 同样的四行说明，并给一条可照抄的打印命令（把 `level` 与三个字段一次打出来）与实测输出 |
| [邀请函 §四](m10-invitation-final.md) 第 4 步 | 同样补上「四个字段各在哪」的第一条 bullet |
| [记录模板 §4 / §5.2](m10-review-record-template.md) | 「四栏各填什么」与「C1 行写什么」都写明抄哪个字段 |

**依据**：本批实跑（§0 第 2、5、6 项）。JSON 报告与 REST `/evidence` 同一形状；
MCP `get_evidence` 的 `provenance` 是字符串数组（`src/dexatlas/mcp/tools/evidence.py`
第 34 行 `provenance=[entry.locator for entry in record.provenance]`）。

**契约表没有改，也不需要改**：`provenance[]` 就是契约规定的形状，材料没说清位置
才是缺口。

### 1.2 M-9 【★ C2】判据用的词「`path=None`」在 API 返回里不存在

**预演说的是什么**（§4 M-9）：`resolve_locator` 的返回里**根本没有 `path` 这个
键**——实测到的键是 `resolved` / `reason` / `kind` / `text` / `provenance`。
`path=None` 是**内部 Python API**（`LocatorResolver.resolve(...)`）的说法。读者照
判据去找 `path`，找不到，会去源码里找、或者以为解析失败了；而真正的判据
「`resolved=true`」反而被盖住了。

**改成了什么**：判据一律改用 API 里真实存在的字段说。

| 位置 | 改前 | 改后 |
|---|---|---|
| 准备包 C2 | 「按构造解析（`path=None` 是设计，不是失败）」 | 「按构造解析（`resolve_locator` 返回 `resolved=true` 而**没有可读的文件内容**——DEX 成员 locator 的 `text` 是 `null`，裸树 locator 的是空文本（`text.text` 为空串、`bytes` 为 0）——这是按构造解析，不是失败；内部 Python API 里对应的是 `path=None`）」 |
| 邀请函 §四 第 4 步 | 「`path=None` 是设计，不是失败」 | 同上（只留 `resolved=true` 与「没有可读的文件内容」的说法） |
| 读者包 §3.4 | 「locator 解析规则见准备包 C2」 | 增加一张三行的判据表（`resolved=true` 有内容 / `resolved=true` 没有内容 / `resolved=false`） |
| 记录模板 §4 | — | 「定位结果」栏抄 `resolved` 与 `reason` |

**依据**：本批实跑（§0 第 3、4 项）。`LocatorResolution` 的字段是
`resolved` / `reason` / `kind` / `text` / `provenance`
（`src/dexatlas/mcp/schemas.py` 第 406 行）；`Resolution.path: Path | None = None`
是内部 Python API 的字段（`src/dexatlas/core/locators.py` 第 161 行）——
括号里保留了它，`docs/glossary.md` 的「裸树 locator」词条引用了这个说法。

**顺带查清的一件事**：预演写的是「`text` 为空」，实测更细——DEX 成员 locator 的
`text` 是 `null`，裸树 locator 的 `text` 是**一个空文本对象**（`text.text` 是空串、
`bytes` 是 0），文件级 locator 的 `text` 才带内容（`bytes > 0`）。材料现在按这
三种情况写，读者能照着区分。

### 1.3 S-5 【★ C2】locator 解析没有可照抄的命令

**预演说的是什么**（§3 S-5）：C2 的判据要求读者给出「解析结果」这一栏，但**三份
材料里没有任何一条解析 locator 的命令**。可用的只有 MCP 的 `resolve_locator`
工具，读者包 §3.8 的 F3 命令只抽查了两个工具，没覆盖它；REST 侧**根本没有**
locator 解析端点。照材料走，读者只能自己写 MCP 客户端——那正是上一轮 S-1 被记
为卡住的同一种情形。

**改成了什么**

- [读者包 §3.4](m10-reader-package.md) 新增一节「**locator 解析（C2 ★）：一条
  可照抄的命令**」：一条 bash 命令（`{ printf … } | dexatlas-mcp | python -c …`）
  把五类 locator 各解析一次——DEX 成员、manifest、裸树、文件级，外加一个**解析
  不出来**的；配一段「预期（实测，2026年11月19日，三个后端齐备）」的五行输出；
  再给一段 PowerShell 写法（实测通过）。
- 同节给出「**C2 的判据怎么用这张表**」的三行表（见 §1.2）。
- [准备包 C2](m10-acceptance-pack.md) 与 [邀请函 §四](m10-invitation-final.md)
  都指到这条命令，并写明「**REST 侧没有 locator 解析端点**」——读者不必去找。

**依据**：本批实跑（§0 第 3、4 项）。实测输出：

```text
resolved=True kind=java locator=jadx:sources reason=<工作区里 jadx\sources 的绝对路径>
resolved=True kind=java locator=jadx:sources/com/example/demo/MainActivity.java reason=<该文件的绝对路径>
resolved=False kind=None locator=(none) reason=com.example.demo.NoSuchClass is not in this analysis
resolved=True kind=None locator=androguard:AndroidManifest.xml reason=AndroidManifest.xml is a dex file of this analysis
resolved=True kind=None locator=androguard:classes.dex#com.example.demo.Crypto reason=com.example.demo.Crypto is in classes.dex
```

REST 侧确实没有这个端点：`src/dexatlas/api/app.py` 的 20 条路由里没有 locator
解析路由，`/projects/{pid}/evidence` 只列出证据记录。

---

## 2. 四项从「能自己判」掉进「必须问作者」

| 验收项 | 预演的结论 | 这一批的处置 | 依据 |
|---|---|---|---|
| **C1** | 字段位置没说 → 读者要么记「字段为空」，要么臆造 | **改材料**（§1.1）：准备包 C1/C3、读者包 §3.4、邀请函 §四、记录模板都写明四个字段各在哪 | 实跑 JSON 报告 / REST / MCP 三处形状 |
| **C2** | 判据用的是 API 里不存在的字段，且没有可照抄的命令 | **改材料**（§1.2 + §1.3）：判据改用 `resolved`/`text`，并补上命令 | 实跑 MCP 五类 locator |
| **F2** | 上一轮补了六类端点的命令，但这一轮仍卡住 | **查清了原因**：命令在**修复后的树里是齐的**（本批实跑六条端点，状态码与形状全部相符），卡住是因为**读者读到的是 tag 树里那一份旧的**（S-4）。材料侧只剩一处实打实的残留——`/runs` 的 `total` 示例写死了 `1`（见 §3.2），已改。**其余随 tag 重打消失。** | 实跑六条端点命令；预演 §4 S-4 |
| **F3** | 命令只在修复后的树里，tag 树里没有 | **不改材料**：这一条会随 tag 重打而自己好（预演 §3 S-4 已写明tag 重打就是材料自己写好的那一步）。本批只把它记在这里 | 预演 §3 S-4 |

**F3 为什么不用改**：F3 的两条协议级命令（列工具清单与注解、调两个工具）在
[读者包 §3.8](m10-reader-package.md) 里已经写好且本轮实测有效；读者之所以读不到，
是因为 `v1.0.0` tag 仍停在材料定稿**之前**的那棵树上。tag 重打之后，读者
`git checkout v1.0.0` 拿到的就是含这两条命令的那一份。

---

## 3. 判据本身要改的两处

### 3.1 G5（★）——「未引用字符串」在包里无法直接判定

**预演说的是什么**（§7）：G5 的判据写的是「证据包不含 APK、全量源码、**未引用
字符串**」，而包里只有 manifest + 三份报告——**读的人看不到包里有什么字符串**，
这一条在包里**无法直接判定**。

**作者已经决定怎么改**（本批遵此执行）：判据改成**包里能判的那几条**——「不含
APK」「不含全量源码」保留；**「未引用字符串」交给 manifest 的声明**（包里带
manifest，它声明了什么不在包里 → 读者核 manifest 的声明）。

**改成了什么**

- [准备包 G5](m10-acceptance-pack.md)：判据改成「**包里能直接判的两条**」——
  **不含 APK**（zip 的条目里没有 `.apk`，`manifest.json` 的 `files` 清单里也没有）、
  **不含全量源码**（包内没有 `sources/` 目录，`files` 清单里只有报告）；
  **「未引用字符串」按 manifest 的声明核对**——`not_included.unrelated_strings`
  声明「未被证据引用的字符串常量不进包」，包里**没有** APK 的完整字符串表可供
  比对，读者核的是**这条声明与包内实际内容一致**（这是本项的判据，不是「与全量
  字符串表比对」）。证据记录栏也改成「包内容：；manifest.not_included：」。
- [准备包 §3.4 / §3.5](m10-acceptance-pack.md)：把 `not_included` 的三个键
  （`apk` / `full_sources` / `unrelated_strings`）点名，并写明「判据是『声明与
  包内实际内容是否一致』」。
- [读者包 §3.6](m10-reader-package.md) 的「数据边界（D3、G5）」段：同样点名三个
  键，写明包里能直接判的是哪两条、「未引用字符串」核的是声明。
- [记录模板 §5.2](m10-review-record-template.md)：G5 行写什么，写明「未引用
  字符串」核的是这条声明。

**依据**：本批实跑（§0 第 8 项）。`manifest.json` 的 `not_included` 是三个键的
字典，每个键一句话；`files` 三条（报告），不含 manifest 自己。

**D3 没有改**：它的判据本来就是「`not_included` 明示 …；实际包内容与该声明
一致」——包里能判，不动。

### 3.2 M-7（F2）——`/runs` 的 `total` 写死成 1

**预演说的是什么**（§4 M-7）：材料给的是 `"total":1`，实测是 **2**。原因是
`total` 是**这个项目跑过几次分析**，读者照 §3.3 → §3.5 → §3.8 的路径走下来会
跑好几次。

**改成了什么**：[读者包 §3.8](m10-reader-package.md) 的运行那条命令旁，把写死
的 `"total":1` 改成形状说明——「`total` 是这个项目**跑过几次分析**，不是固定
值：照 §3.3 → §3.5 → §3.8（F1 那条 analyze）的顺序走，到这里是 3。判据看**形状**：
`runs` 的条数 == `total`，其中**恰有一条** `published=true`，那一条的 id 就是
`published_run_id`（上面那条上传命令是幂等的，不会再加一次）」。

**依据**：本批实跑（§0 第 7 项）。CLI 分析三次后 `total` = 3；再跑一遍 REST 的
`POST /analyze`（同样的字节）**没有**增加运行数——上传按 SHA 幂等，返回同一个
project id。**这不是改测量数**：改的是材料里一个写死的示例输出，改成了形状 + 它
随什么变。

### 3.3 顺带重锚的一条引用（本批改读者包引起的）

读者包 §3.4 加了内容，它下面的行号全部后移，于是
[第二轮预演](m10-reader-rehearsal-2nd.md) 里指向读者包第 314 行（那条
`uv run --no-sync dexatlas-mcp   # 起 MCP server（列工具清单）`）的引用就指空了
——`check-doc-citations.py` 报 `drifted: 1`。那条一行命令在上一轮材料修复时就已经
被换成协议级的两条，它在 `v1.0.0` 那棵树上才在第 314 行。

按 CLAUDE.md 规则 4（「指向位置而不是符号的引用留给检查器报告、由人来定」），本批
把那条引用**改成指现行材料里陈述同一件事的那一行**
（`docs/reports/m10-reader-package.md:491`：`dexatlas-mcp` 是 stdio 传输的 MCP
server，**直接起它看不到工具清单**），并在引用旁边写明「这行命令在 `v1.0.0` 那棵
树的读者包第 314 行」。**改动是等行数的（1 行换 1 行）**——否则它自己下面的行号
会跟着移，又把别处的引用带偏（改一次就报一次 `drifted: 1`，第二轮就是这么发现的）。
**更彻底的做法**是把第二轮预演登记成「讲的是 `v1.0.0` 那棵树」的文档
（`scripts/check-doc-citations.py` 的 `TREE_DOCUMENTS`）——**那是 `scripts/` 的改动，
不在本批范围内**，留给主会话。

### 3.4 顺带查出的一个假通过：端口退路可能答在别人的服务上

实跑 F2 的六类端点时发现的：本机 **8000 与 8011 同时被占**——8000 上是另一个
FastAPI（`/health` 返回 `{"status":"healthy"}`），**8011 上跑的是另一个 DexAtlas**
（`/health` 返回 `{"status":"ok","version":"1.0.0",…}`，与读者自己起的服务**应答
一模一样**）。

[读者包 §3.8](m10-reader-package.md) 的退路只写了「8000 被占就换 8011」，并让读者
用 `/health` 确认服务身份。**在 8011 也被占的机器上，这一步会静默通过**：读者自己的
uvicorn 绑不上端口（日志里是 `[WinError 10048] error while attempting to bind`），
而 `/health` 答的是**别人的 DexAtlas**——形状与状态码都对，读者会拿一个**别的
工作区**的响应当自己的。

材料补了一句：**判断依据是 uvicorn 的日志，不是 `/health`**——日志里有
`[WinError 10048]` 就是自己的服务没起来，换一个还没被占的端口（`B` 跟着改）。
这是本批实跑时发现的，**不在第三轮预演的清单里**。

---

## 4. 改完之后的自检

| 门禁 | 结果 |
|---|---|
| `ruff check .` | ✅ |
| `ruff format --check .` | ✅ |
| `mypy` | ✅ |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | ✅ 退出 0 |
| `python scripts/check-doc-citations.py` | ✅ `drifted: 0` |
| `python scripts/check-version-claims.py --base auto` | ✅ |
| `python scripts/m10_selfcheck.py` | ✅ 43 / 0 / 40 |

**没有跑 `scripts/refresh-report-figures.py`**（并发测量会互相污染覆盖率），**没有
改任何 `.py`**（源码指纹不变，报告里的数字保持有效）。

---

## 5. 还剩什么

1. **tag 没有重打，读者读到的仍是旧稿。** 这是预演 §3 的 S-4，也是 F2、F3 两条
   判据缺口**真正**的成因：修复后的材料在 `main`（`12141b5` 及其后继）上，
   `v1.0.0` tag 仍停在 `2715aef`。**本批改的四处也是同样的处境**——它们在
   `main` 上，tag 树里没有。tag 重打之后，S-5、M-8、M-9、M-7 与 G5 的新判据
   才会到读者眼前。**重打 tag 之后要重新取 hash 并重填**邀请函 §2 与记录模板
   §1（这一步按分工由发起人执行，见[发送前清单](m10-invitation-sender-checklist.md)
   的 N1 与[就绪记录](m10-invitation-readiness.md)第 2 步）。
2. **`docs/glossary.md` 的「裸树 locator」词条**引的是
   准备包 §2.7 的 **C1 那一行**（第 116 行），而「裸树 locator」实际在**下一行**（C2
   那一行）——**这一行号在本批之前就已经差了一行**（上一轮改 C1/C2 的判据时移动
   的），本批没有再移动它（表格行数未变）。该文件不在本批拥有范围内，也没有
   进引用检查器的清单，**留给主会话统一处理**。本批保留了 `path=None` 这个词
   （写在括号里），所以词条的定义文字仍然成立。
3. **本文件没有登记进** `scripts/check-doc-citations.py` 的文档清单，
   `docs/reports/README.md` 也没有登记——按分工留给主会话。
4. **验收材料之外的缺口**（预演 §5 的 X-3：发送前清单那句「tag 树含本轮全部材料
   修正」的判语已经与事实不符）不在本批拥有范围内，未改。
5. **本批没有判定任何验收项。** 40 项仍然全部是「未验证」——判定只能来自一位
   未参与实现的读者亲手执行 [m10-reader-package.md](m10-reader-package.md)。

---

## 6. 一句话

**三条新缺口（S-5 / M-8 / M-9）都在材料里堵上了，四项判据缺口里 C1、C2 随之
堵上、F2 查清了成因并修掉唯一残留的示例错误、F3 不用改（随 tag 重打自己好），
G5 的判据改成了包里能判的样子；剩下的不是材料的问题，是 tag 还没重打。**
