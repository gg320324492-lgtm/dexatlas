# M10 验收材料 —— 第二轮预演缺口的逐条处置

> **本文件的性质：** 这是对[第二轮读者视角预演](m10-reader-rehearsal-2nd.md)记下的
> **9 处缺口 + 2 处「多余」**的逐条处置记录：预演说的是什么 → 改成了什么 → 依据。
> **它不是验收结论**，也没有替任何验收项打勾——40 项的判定权仍在读者手上。
>
> **本轮是纯文档改动**：没有动任何 `.py`，源码指纹不变，报告里的测量数保持有效；
> **没有跑** `scripts/refresh-report-figures.py`（并发测量会互相污染覆盖率）。
>
> **本文件不改任何既有文件**，只新增这一份。未触碰 `.github/`、README 徽章、
> `docs/status.md`、`docs/reports/README.md`，未登记进
> `scripts/check-doc-citations.py` 的文档清单（那两件按分工留给主会话统一做）。

---

## 0. 基线

| 项 | 值 |
|---|---|
| 处置日期 | 2026-11-19 |
| 依据 | [m10-reader-rehearsal-2nd.md](m10-reader-rehearsal-2nd.md)（第二轮预演，2026-11-18，59 步） |
| 被处置的材料 | `m10-invitation-final.md`（邀请函）、`m10-reader-package.md`（读者包）、`m10-acceptance-pack.md`（准备包）、`m10-review-record-template.md`（记录模板） |
| 实测环境 | Windows 11 Pro 10.0.26300 · Python 3.12.10 · uv 0.11.21 · JDK 21 · jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4（三后端齐备）· Git Bash + PowerShell 7.6.3 + Windows PowerShell 5.1 |
| 改动的文件数 | 4 份材料 + 2 处 `file:line` 重锚（见 §4） |
| 源码改动 | **无**（`src/`、`tests/`、`scripts/` 一行未动） |

**处置原则**（与作者给的两处决定一致）：

1. **判据本身不动，只补可达性。** F2 的判据仍是「抽查 3 个端点」——补的是六类端点
   各一条能跑的命令；F3 的判据仍是「11 个工具、全部只读注解、抽查 2 个工具」——
   补的是能列清单、能调工具的命令。
2. **权威判据只有一处。** 准备包 §2 是 40 项判定标准的权威；凡与它重复的表述，
   改成指向它，而不是再写一遍。
3. **命令必须真的能跑。** 本轮给出的每一条命令都在上面那台机器上**实跑过**，
   输出的原文抄进材料；本机不具备的条件（如三个后端不齐）照材料既有写法标
   「实测 / 未实测」，**没有编造没跑过的输出**。

---

## 1. 三处卡住（S-1 / S-2 / S-3）

### S-1 【F3】要判「MCP 工具清单为 11 个、全部只读注解」，材料给的命令不列清单

**预演说的**：F3 的判据要读者列出工具清单并抽查两个工具的返回形状，但 §3.8 给的
`uv run --no-sync dexatlas-mcp` 只是**把 server 起起来**——它走 stdio，终端里什么
都看不到；预演者自己写了 20 行 MCP 客户端脚本才拿到清单。这与邀请函 §一
「您不需要写代码」直接冲突，读者须知第 4 条（凡靠作者口头补充才走通的步骤判不通过）
会让 F3 只能落进「未验证」。

**改成了什么**（[读者包 §3.8](m10-reader-package.md:396)）：

- **第一步**：明说「`dexatlas-mcp` 是 stdio 传输，**直接起它看不到工具清单**」，
  并给出**协议级**的做法：用 MCP 的 JSON-RPC 问它一次。
- **列工具清单 + 四个只读注解**（bash 一条、PowerShell 一条，照抄即可，读者不写代码）：
  `initialize` → `notifications/initialized` → `tools/list`，管道接一个
  `python -c` 把每个工具的 `readOnlyHint` / `destructiveHint` /
  `idempotentHint` / `openWorldHint` 打出来。**实测输出 11 行 + `tool count: 11`**，
  与契约表 §3.1 的 11 个工具**逐名对上**，四个注解与契约表 §3 开头写的一致。
- **抽查 2 个工具的返回形状**：同一条管道换成 `tools/call`（`list_projects` 与
  `get_project_status`），打印返回对象的 `structuredContent`。**实测两行**
  （`id=3` / `id=4`；两行先后顺序不固定——两个调用并发执行，实测两种顺序都出现过，
  已写进材料）。
- [准备包 F3](m10-acceptance-pack.md:154) 的判据**一个字没动**，只在后面补了一句
  指路：两条可照抄的命令在读者包 §3.8。

**依据**：契约表 §3.1（11 个工具清单）、§3（`_read_only` 的四个注解值）；
`scripts/verify-public-contracts.py` 的 `mcp_checks()`（它本来就是用 MCP SDK 在
协议层查这两件事——本轮把同样的检查变成读者能照抄的命令）。

> **为什么不给 `dexatlas-mcp` 加 `--list-tools`**：那要改源码（动指纹、要补回归测试、
> 要重新测量），而本轮是纯文档批次。命令级的做法把同样的证据给到读者，且**证据本身
> 是协议层的**，不是读源码读出来的。

### S-2 【A1 / 邀请函 §2 / 记录模板 §1】tag 指向的树里，hash 还是占位符

**预演说的**：填 hash 的提交 `7a416bd` 在 tag（`2715aef`）**之后**，所以读者
checkout 到的那棵树里，邀请函 §2 与记录模板 §1 都是**占位符**；记录模板却让读者
「照抄那一串」——严格照树做，读者做不到。tag 不能重打（打了又要一个填 hash 的提交）。

**改成了什么**（作者已决定的口径：「以随函发出的那一份为准」）：

| 文件 | 改成 |
|---|---|
| [邀请函 §2](m10-invitation-final.md:93) | 新增一段：**这一串以「随函发出的这一份」为准**；仓库里同名文件在 tag 指向的那棵树上仍是「填入前」的版本（填 hash 发生在打 tag 之后），那是**同一份材料的两个副本，不是两份不同的材料**；核 hash 的方式不变（`git rev-parse v1.0.0^{commit}`） |
| [邀请函 抬头说明](m10-invitation-final.md:7) | 「正文里只留一处内容占位」改为说明：仓库这一份**已填**，填入动作在打 tag 之后，所以树内那份仍是填入前的版本，以随函发出的那一份为准 |
| [记录模板 §1](m10-review-record-template.md:17) | 提示语改成同一口径：照**随函发出的那份邀请函 §2**；树内那份是填入前的版本；核对方式 `git rev-parse v1.0.0^{commit}` |
| [读者包 §1.6](m10-reader-package.md:56) / 抬头 / §3.1 | 三处「hash 在邀请函成稿 §2」的指针改成「**随函发出的那份邀请函**」，并说明树内那份是填 hash 之前的版本 |
| [准备包 §0 抬头](m10-acceptance-pack.md:13) / §3.1 | 同上 |

**依据**：预演的实测（`git show 2715aef:docs/reports/m10-invitation-final.md` 里
§2 仍是「【待填：…】」）+ 邀请函 §2 本来就写着「由验收发起人在发出本函之前填入」
——新口径与它自洽。**hash 的值一个字节没改**（`2715aefd…`，40 位）。

### S-3 【F2】REST 端口 8000 被占时没有退路，而且失败是静默的

**预演说的**：8000 被别的服务占着时，uvicorn 先打印 `Application startup complete.`
（像是成功了）、再打印 bind 失败，然后退出；**`curl` 照样成功**，返回的是**另一个
应用**的响应（`{"status":"healthy"}` / `{"detail":"Not Found"}`）。读者会把它写成
一条 F2 的假卡点。

**改成了什么**（[读者包 §3.8](m10-reader-package.md:331)）：

- **先讲怎么认出成功**：服务真的起来时日志里有这一行——
  `INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`——
  **它是「服务真的起来了」的唯一信号**（`Application startup complete.` 不作数）。
- **给出退路**：端口被占就换（`--port 8011`），并把命令里的端口一起换；命令块用
  变量 `B=localhost:8011` 承载端口，**换一处即可**。
- **给出身份核对**：`curl -s localhost:8011/health` 必须是
  `{"status":"ok","version":…,"backends":{…}}`；返回 `{"status":"healthy"}` 或
  `{"detail":"Not Found"}` 就说明这个端口上**不是 DexAtlas**，继续换端口。

**依据**：本轮**在同一个机器上复现了预演记的场景**（8000 上跑着另一个 FastAPI
应用，`/health` 返回 `{"status":"healthy"}`、`/projects` 返回 `{"detail":"Not Found"}`；
uvicorn 日志先打 `Application startup complete.` 再打 `[WinError 10048]`），
并在 8011 上把 DexAtlas 起来核对身份——两条输出都抄进了材料，标「实测」。

---

## 2. 六处误读（M-1 … M-6）

### M-1 【G3，★】G3 的预期在三份材料里各写一遍，三遍条数不一样

**预演说的**：准备包 §2.7（权威）写的是泛化表述「**至少一条**」；读者包 §9.1 给了
两个**具体数字**（「实测」三条、「会只有两条」）；M8 演练 §5 又是「三后端各记一条」。
预演机上一条 timeout（只有 jadx），读者若把「两条」当形状预期，会在 ★ 阻断项上
记一条假卡点。

**改成了什么**：

- [读者包 §9.1 G3](m10-reader-package.md:773)：开头改成「**至少一条后端记 `timeout`，
  且报告照常产出**。**权威判据见准备包 §2.7 G3**——那里是这条判据的唯一出处，
  **条数与本机速度有关，不是固定值**」；原来那段三行「实测」输出改标为
  **示例**，并另给**本机实测（一条：androguard 与 apktool 都在 1 秒内跑完，
  只剩 jadx 超时）**；括注从「会只有两条」改成「条数随后端速度变化——本机实测
  只有一条」。
- 顺带把两处**自相矛盾**的表述并成一处：`index_complete` / `index_gaps` 的说明
  原来先说「`index_complete` 是 false、`index_gaps` 里有一条 androguard 的 timeout」，
  后面又说「只在 androguard 自己也超时时才成立」；现在合成一段并写明
  **`index_gaps` 只统计 androguard，jadx 超时不构成 gap**。
- [准备包 G3](m10-acceptance-pack.md:165) 末尾加一句「**本项是 G3 判据的唯一权威
  出处**——读者包 §9.1 给的是可照抄的命令与**示例**输出，以本行为准」。

**依据**：预演的实测（本机 1 秒超时下只有 jadx 超时，`errors[]` 一条、
`index_complete: true`、`index_gaps: []`）；本轮在同一台机器上复跑，**结果一致**
（`!  jadx exceeded its 1s timeout; its launcher had already exited`，退出码 0，
报告照常产出）。

> **M8 演练 §5 的第三处**在 `docs/reports/m8-install-rehearsal.md` ——**那个文件属于
> 另一个窗口**，本窗口没有改（见 §5）。

### M-2 【G3，★】「核对 M8-4 的退出码语义」指向的那一节，写的是修复前的语义

**预演说的**：M8 演练 §6 那一节写的是「退出码仍是 0」「留主会话决策」，是 v1.0.0
之前的状态，而且**那一节里一次都没提过退出码 6**；认真核对的读者会得出「M8-4 的
缺口还在」。

**改成了什么**（两个文件各一处，都在本窗口拥有的文件里）：

- [准备包 G3](m10-acceptance-pack.md:165)：「本项只需核对 M8-4 的退出码语义」改成
  「本项只需**核对退出码 6 的语义**（[公共契约表 §1.2](../architecture/public-contracts.md)；
  **M8-4 是提出该缺口的历史记录，已由退出码 6 关闭**，见读者包 §4.4）」；
  证据记录栏的「M8-4 结论」也改成「退出码 6 的结论」。
- [读者包 §4.4](m10-reader-package.md:559)：M8-4 那一条后面加一段提示——
  **[M8 演练 §6] 记的是「当时（修复前）的实况」**，是提出缺口的历史记录，
  那份记录里没有前向指针，**以本条与契约表 §8.1 为准**。

**依据**：契约表 §1.2（退出码 6 = `EXIT_NO_INDEX` 的语义）、§8.1；
[docs/proposals/exit-code-partial-read.md](../proposals/exit-code-partial-read.md)（提案）。
预演给的修法有两条，本轮取的是**第二条**（改判据），因为 M8 演练文件不在本窗口的
文件清单里；第一条（在该文件里加一行前向指针）留给拥有它的窗口（见 §5）。

### M-3 【G1】`projects` 预期为空，与材料规定的执行顺序冲突

**预演说的**：§9.1 是附录，排在 §3.3 之后，而 §3.3 已经把 demo.apk 分析进主工作区；
在主工作区跑 `projects` **列着 A4 的项目**，不是空的——照 §9.1 走的读者会记一条
假卡点。（这一条与上一轮的 M-5 是同一个问题，两轮未改。）

**改成了什么**（[读者包 §9.1 G1](m10-reader-package.md:709)）：

- 开头加一段说明：**这条要在「一个空工作区」里跑**，并解释为什么（§9.1 排在
  §3.3 之后，主工作区里已有 A4 的项目）。
- 命令改成带一个**新工作区**：
  `DEXATLAS_WORKSPACE=./g1-fresh uv run dexatlas analyze README.md` 与
  `DEXATLAS_WORKSPACE=./g1-fresh uv run dexatlas projects`（另给 PowerShell 写法）。
- 预期改为：**这个工作区**里列表是空的；并补一句——**在主工作区里再跑一次
  `projects` 也没问题**，它列着 A4 的项目、计数与 §3.3 一致、**没有多出半个坏输入
  项目**，这一条同样算 G1 通过。

**依据**：本轮实跑（`DEXATLAS_WORKSPACE=./g1-fresh` 下退出码 **2**、错误信息一行、
`projects` 输出 `No projects yet. Run \`dexatlas analyze <apk>\`.`，工作区目录被自动
建出来但没有项目记录）✓。

### M-4 【邀请函 §五】「40 项留人工……与您要判的 40 项不是同一组东西」——这句是错的

**预演说的**：脚本标「需人工」的 40 条，**编号就是 A1–G5 那 40 个验收项本身**；
而且其中 **13 个同时出现在脚本的「通过」清单里**。所以「另一个分母」「不是同一组
东西」是反的——邀请函是发给读者的那一份正文，读者照它读自查脚本的输出，会看到
一堆和自己清单一模一样的编号，却被告知「不是同一组」。

**改成了什么**（[邀请函 §五](m10-invitation-final.md:190)）：

> **那 40 项就是您要判的这 40 项**——编号 A1–G5 与本函第五节那份清单**一一对应**，
> 不是另一组东西；其中 13 项（A4、A6、D1、D3、D5、E1、E5、F1、F2、F3、F4、F5、
> F6）脚本能静态自检，其余留给您实做。**但脚本判的「通过」不是验收判定**——它不能
> 替您判定任何一项，M10 的判定只来自您亲手执行的记录。

**依据**：本轮实跑 `scripts/m10_selfcheck.py`：退出码 0，末行
「自动化判定：通过 43，失败 0，需人工 40；已判定项通过率 100.0%」；
「需人工」编号提取出来是 `A1 A2 … G5` **正好 40 个**，与验收项编号一一对应；
其中落在「通过」清单里的交集是 **13 个**（A4 A6 D1 D3 D5 E1 E5 F1 F2 F3 F4 F5 F6），
与预演记的一致。**「43 / 40」这两个数字一个都没改**——改的是它们**是什么**。

### M-5 【F2】「抽查 3 个端点」，材料给的命令只覆盖 6 个关键端点里的 2 个

**预演说的**：§3.8 给的三条 curl 命中的是 `/health`（元信息，**不在** F2 点名的六个
关键端点里）、`/projects`（项目）、`/report`（报告）——六个里只覆盖了两个；读者记
「F2 通过（抽查 3 个端点）」，而实际抽查的 3 个里有 1 个不在 F2 的关键端点表上。

**改成了什么**（作者已决定：**补齐六类端点的命令，判据本身不动**）：

- [读者包 §3.8](m10-reader-package.md:351) 给出**六类关键端点各一条命令**：
  上传（`POST /analyze`）、项目（`/projects`）、运行（`/projects/{pid}/runs`）、
  符号（`/projects/{pid}/classes`）、源码（`/projects/{pid}/classes/{cls}/source`）、
  报告（`/projects/{pid}/report?format=json`）。每条带 `-w "\n[%{http_code}]\n"`
  ——**状态码是 F2 判据的一部分**。
- 端口用变量 `B=localhost:8011` 承载（被占时换一处即可）；`P` 承载 project id。
- [准备包 F2](m10-acceptance-pack.md:153) 的判据**一个字没动**（「抽查 3 个端点」），
  只在后面补一句：六类端点各有一条可照抄的命令（见读者包 §3.8），**判据仍是
  「抽查 3 个」——自选其中 3 个记录即可**。

**依据**：契约表 §2.2–§2.6（路径、方法、状态码、响应形状）。本轮**逐条实跑**
（在一个**全新的工作区**上，先 analyze 一次，再起服务）：

| 类 | 命令 | 状态码 | 实测响应（摘要） |
|---|---|:--:|---|
| 上传 | `POST /analyze` | **202** | `{"project_id":"apk_80a8fe0e81204c9f","status":"completed","detail":"/projects/apk_80a8fe0e81204c9f"}`（幂等：同字节再传返回同一项目） |
| 项目 | `GET /projects` | **200** | `[{"id":"apk_80a8fe0e81204c9f","status":"completed",…,"class_count":5,"method_count":8,…}]` |
| 运行 | `GET /projects/{pid}/runs` | **200** | `{"project_id":…,"total":1,"published_run_id":"run_…","runs":[{…,"status":"completed","completeness":"complete",…}]}` |
| 符号 | `GET /projects/{pid}/classes?limit=2` | **200** | `{"project_id":…,"total":5,"classes":[{…,"name":"com.example.demo.Crypto","kind":"class",…}]}` |
| 源码 | `GET /projects/{pid}/classes/com.example.demo.MainActivity/source` | **200** | 头：`x-dexatlas-source-kind: java`、`x-dexatlas-source-tool: jadx`、`x-dexatlas-source-locator: jadx:sources/com/example/demo/MainActivity.java`、`x-dexatlas-source-tool-version: 1.5.2` |
| 报告 | `GET /projects/{pid}/report?format=json` | **200** | 顶层 10 个字段：`['errors','evidence','generated_at','latest_attempt_status','manifest','project','run','schema_version','summary','tools']` |

（材料里每一块都标了「实测（2026年11月19日 …）」；`…` 表示省略的中间字段。）

### M-6 【C2 / C3，★】邀请函说的 locator 判法，与准备包说的不是一件事

**预演说的**：邀请函 §四 第 4 步写「`locator` 要能在你导出的证据包里解析到对应
字节」；demo 项目的 11 条 evidence **没有一条**在证据包里解析到字节——包里只有
3 份报告 + 1 份 manifest，没有 `sources/` 目录，也没有 DEX。那是
`verify_citations` 说的「**按构造解析**（`path=None` 是设计，不是失败）」。
照邀请函的字面判，**★ 阻断项 C3 会被判成不通过**。

**改成了什么**（[邀请函 §四 第 4 步](m10-invitation-final.md:149)）：

> **`locator` 按[准备包 §2.3 C2](m10-acceptance-pack.md)的规则核**：**文件级**
> locator 要在分析工作区里解析到真实文件；**DEX 成员 locator 与裸树 locator**
> （如 `jadx:sources`）是**按构造解析**的——`path=None` 是设计，不是失败
> （证据包不含整棵源码树，所以包里没有 `sources/` 目录）；解析不了的
> locator 要单独列出来；

**依据**：准备包 §2.3 C2（**权威判据，未改**）；
`src/dexatlas/reports/evidence_package.py` 的 `verify_citations`（DEX locator 与
裸树 locator 走 `resolved += 1; continue`，不查包内文件）——即预演说的
「按构造解析」。邀请函与准备包现在说的是**同一件事**。

---

## 3. 两条「多余」

### X-1 G3 的预期被写三遍（= M-1）

已随 M-1 一并处置：三份材料里，**准备包 §2.7 G3 是唯一权威**；读者包 §9.1 改成
「权威判据见准备包 §2.7 G3」+ 示例 + 本机实测；M8 演练 §5 那第三处在别的窗口的
文件里（见 §5）。

### X-2 「首次读者路径」在准备包 §3 与读者包 §3 各写一遍，两遍的步骤清单不一致

**预演说的**：准备包 §3 开头写着「本节**可以原样交给读者**」，但它的「你需要什么」
表里**没有 `gh` CLI** 这一行，整个 §3 里**没有** `scripts/fetch-fixtures.sh` 这一步
（只在 §7 的遗留表里被顺带提了一次）；读者包两样都有。读者拿到哪一份，决定了他知
不知道 `fetch-fixtures.sh` 这件事。

**改成了什么**（两边都补，**以读者包为准**）：

- [准备包 §3 开头](m10-acceptance-pack.md:183) 加一段：**这一段路径在读者包 §3 里
  还有一份发给读者的完整版**；两份讲的是同一条路径，**执行时以读者包 §3 为准**
  （它是随函发出的那一份），本节保留准备侧的说明与判据；两者若有出入，以读者包为准，
  并在记录里写下差异。
- [准备包 §3.1 环境表](m10-acceptance-pack.md:197) 补上 **`gh` CLI** 一行
  （仅第三方 fixtures 需要）。
- [准备包 §3.2](m10-acceptance-pack.md:221) 补上 **`bash scripts/fetch-fixtures.sh`**
  这一步，并写明「为什么这一步不能跳」（集成用例要读两个不在仓库里的 APK）、
  前置条件（能上网 + 已登录的 GitHub CLI）、不抓的后果（**27 个集成用例 skip**，
  退出码 0 只说明没有失败）与详细口径的去处。

**依据**：预演的 `grep -n "gh CLI\|fetch-fixtures\|gh api" docs/reports/m10-acceptance-pack.md`
在 §3 里零命中；本轮复核同样零命中（唯一命中在 §7 遗留表），
`docs/reports/m10-reader-package.md:71` 与 `:108` 两处则都有 ✓。

---

## 4. 顺手改掉的一处指针错误（预演没记）

[读者包 §3.8](m10-reader-package.md:480) 原来写「报告 JSON 的 `schema_version` 与
顶层字段在契约表 **§4**」——契约表 §4 是「计数含义」，报告 schema 在 **§5**
（§5.1「JSON 报告顶层字段」）。已改正为 §5.1。

**依据**：`docs/architecture/public-contracts.md` 的章节表（§4 计数含义 /
§5 报告 schema / §5.1 JSON 报告顶层字段）。

---

## 5. 改完后还剩什么

| # | 剩下的 | 归谁 | 为什么没在本窗口做 |
|---|---|---|---|
| 1 | ~~**M8 演练 §6 的 M8-4 标题下加一行前向指针**~~ —— **已由另一个窗口做掉**：分支 `claude/cool-lamport-3cb292`、提交 `d593470`（M8-4 标题下加了五行「此后已如何解决」的引用块，正文一字未改；M8-4 标题仍在 `:138`，那些旧引用没失效）。**两个修法现已互补闭环**：那边做「修法一」（历史记录上加前向指针），本窗口做「修法二」（改 G3 判据措辞） | 已闭环 | 该文件不在本窗口的文件清单里；**读者侧的歧义本窗口已消掉**（准备包 G3 改了判据、读者包 §4.4 加了提示） |
| 2 | **M8 演练 §5 的「三后端各记一条 timeout」** 也要改成「示例 + 指向准备包 §2.7」——预演 X-1 的第三处 | 拥有 `docs/reports/m8-install-rehearsal.md` 的窗口 | 同上；那个窗口这一轮只动了 §6 的 M8-4 段与 C17 候选，**没有动 §5** |
| 3 | **`docs/reports/README.md` 的登记** 与 **`scripts/check-doc-citations.py` 的文档清单**（含本文件） | **主会话**（按分工） | 本窗口明确不登记；登记后本文件的 `file:line` 引用才会进入引用检查器的覆盖范围（里面的行号是本轮手工核过的） |
| 4 | **tag 所指的那棵树上的材料仍是填 hash 之前的版本** | 不需要人做 | 形状不变是作者的决定（tag 不重打）；新口径已把「以随函发出的那一份为准」写进四处 |

**没有留在后面的**：S-1、S-3、M-1（两份材料内）、M-3、M-4、M-5、M-6、
X-1（两份材料内）、X-2 —— 都已在本轮改掉，且改动的每一处都实跑或实测过。

---

## 6. 门禁记录（2026年11月19日，本分支）

| 门禁 | 结果 |
|---|---|
| `uv run --no-sync ruff check .` | ✅ All checks passed! |
| `uv run --no-sync ruff format --check .` | ✅ 398 files already formatted |
| `uv run --no-sync mypy` | ✅ Success: no issues found in 68 source files |
| `uv run --no-sync vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | ✅ 退出码 0 |
| `uv run --no-sync python scripts/check-doc-citations.py` | ✅ **drifted: 0**（unresolved paths: 0） |
| `uv run --no-sync python scripts/check-version-claims.py --base auto` | ✅ 退出码 0（2 条 findings 均为既有，`2 already in de5060c7`） |

**引用重锚**：本轮改了四份材料，行号移动，连带三处**指向它们**的引用漂移——
`evidence-package-isolation.md:267`（→ `m10-acceptance-pack.md:129`）、
`m10-reader-rehearsal-2nd.md:259`（→ `m10-invitation-final.md:81`）、
`m10-reader-rehearsal-2nd.md:362`（→ `m10-acceptance-pack.md:165`）。
`scripts/remap-citations.py` 对这三处**没有动手**（它们指向的是「位置」而不是
「符号」，按 CLAUDE.md 规则 4 留给人判断），因此由本窗口**手工重锚**，
重锚后 `drifted: 0`。

---

## 7. 本窗口做了什么、留给谁

**本窗口（本分支 `claude/recursing-neumann-fde6ed`）**：

- 改 4 份材料：
  `docs/reports/m10-invitation-final.md`、
  `docs/reports/m10-reader-package.md`、
  `docs/reports/m10-acceptance-pack.md`、
  `docs/reports/m10-review-record-template.md`；
- 手工重锚 3 处 `file:line` 引用（在 `evidence-package-isolation.md` 与
  `m10-reader-rehearsal-2nd.md` 里，**只改行号，不改这两个文件的内容**）；
- 新增本文件 `docs/reports/m10-material-fixes.md`；
- **未改任何 `.py`**（指纹不变，报告里的数字保持有效）；
- **未跑** `scripts/refresh-report-figures.py`；
- **未登记** `docs/reports/README.md` 与 `scripts/check-doc-citations.py`。

**留给主会话 / 别的窗口**：

- `docs/reports/m8-install-rehearsal.md` 的 **§5 的 timeout 条数**——**归拥有那个
  文件的窗口**（§6 的 M8-4 前向指针那个窗口已经做掉了：`claude/cool-lamport-3cb292`
  的 `d593470`，与本窗口的 G3 判据改动互补）；
- `docs/reports/README.md` 与 `scripts/check-doc-citations.py` 的登记——**归主会话**；
- 本文件的 `file:line` 引用在登记进引用检查器之前**不受自动检查**（里面的行号是
  本轮手工核过的；登记后请跑一次 `scripts/check-doc-citations.py` 确认 `drifted: 0`）；
- 本分支**没有推 main、也没有合并到 main**。
