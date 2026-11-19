# 本地门禁与 CI 门禁的差异（只读复核）

> 复核日期：2026年11月18日 · 复核方式：只读 · 复核树：`claude/exciting-shannon-d0f438` @ `9e1aa61`
>
> **本报告的行号锚在哪棵树：** 全部锚在提交 **`9e1aa61`** 上，那棵树的测量指纹是
> `sha256:d0e85b61…`；**本报告里的 `file:line` 只在 `9e1aa61` 上成立**。这是本仓库
> 自己的规矩：读一份报告之前先看它锚在哪棵树上。
>
> 本文回答一个问题：**哪些门禁在 Windows（本地）与 Linux（CI）上会给出不同的答案。**
> 每一处给出：差在哪 → 哪个平台判什么 → 门禁因此漏掉了什么（或误报了什么）→ 怎么改。
>
> 本文只新增这一个文件，没有改动任何既有文件。改动由主会话统一做。

## 摘要

- 复核范围：本地 6 道门禁（见 [v1.0.0-release-checklist.md](v1.0.0-release-checklist.md) §8.1）与
  CI 的 10 个 job（[ci.yml](../../.github/workflows/ci.yml)）。
- **查出 37 处平台差异**：**35 处**会让两个平台给出不同的答案（本地绿 / CI 红，或反过来），
  另有 **2 处方向相反**（本地比 CI 更严，见 §3）。
- **最要紧的三条**：
  1. **D1 —— 报告里的测量记录是 Windows 的测量。** CI 的 measurement job 在 Linux 上跑，
     那三条 Windows-only 的测试在那里整条跳过，于是「跳过的身份集合」与记录里的对不上，
     测量被判为不完整；而 `--check` 在不完整时仍然返回 0。
     **结果是：CI 的测量门禁在这棵树上恒为绿，且什么都没验。**（§1.1 D1）
  2. **D2 —— 测量脚本的子进程输出按平台默认编码解码。** 本机是 cp936，Linux 是 UTF-8。
     父子进程只要有一边进了 UTF-8 模式，字节就按另一边的编码解释。（§1.1 D2）
  3. **D10 —— 契约活检的时间预算是按「本地那套配置」定的。** CI 装了 JADX 与 Apktool，
     走完整反编译；本地常常没装，只走 androguard 一条路。CI 因此比本地更容易撞上 120 秒的上限。（§1.2 D10）
- **本文不改任何东西。** 下面所有关于「会判什么」的判断都来自代码路径的推导与 §7 的实验，
  其中 D1 另有仓库里已落盘的 CI 实跑记录佐证。

---

## 0. 两边的门禁与环境

### 0.1 门禁清单

| 来源 | 门禁 | 本地判据 | CI 判据 |
|---|---|---|---|
| 本地 + CI | ruff lint / ruff format | 同一份命令 | 同一份命令 |
| 本地 + CI | mypy（strict） | 同一份命令 | 同一份命令 |
| 本地 + CI | vulture（死代码） | 同一份命令 | 同一份命令 |
| 本地 + CI | pytest 全套 | `uv run --no-sync` | `uv sync --frozen` 之后 `uv run pytest` |
| 本地 + CI | check-doc-citations | 同一份命令 | 同一份命令（间接：被 `tests/test_doc_citations.py` 调用） |
| 本地 + CI | check-version-claims | `--base auto` | PR 用 `--base auto`，push 用 `$BEFORE`，tag 用 `HEAD^` |
| 本地 + CI | verify-public-contracts | 同一份命令 | contracts job |
| 本地 + CI | m10_selfcheck | 同一份命令 | m10-selfcheck job |
| 本地 + CI | make-social-preview | 写盘 | `--check`，只比数字 |
| 本地 + CI | refresh-report-figures | **写盘** | `--check`，**仅 tag 触发** |
| 仅 CI | actionlint / 依赖审计 / Docker 镜像 | — | lint / security / docker 三个 job |
| 仅 CI | 3.13 无后端、仅 Apktool 两套配置 | — | test job 矩阵 + test-partial-backends |
| 仅本地 | 后端版本固定 | 无 | install-backends 脚本 |

### 0.2 环境对照

| | 本地 | CI |
|---|---|---|
| 操作系统 | Windows 11 | ubuntu-latest |
| Python | 3.12（本机 venv） | 3.12 / 3.13 矩阵 |
| 默认文本编码 | cp936（GBK） | UTF-8 |
| 文件系统大小写 | 不敏感 | 敏感 |
| 符号链接 | 需开发者模式或管理员 | 默认可建 |
| 路径长度上限 | 260 字符 | 4096 |
| git 是否在系统 PATH 上 | 不一定（常只有 Git Bash 里有） | 一定有 |
| Java 后端 | 常常没装在本机 PATH 上 | 每个相关 job 都装，且版本固定 |
| 第三方 fixture | 需手动取 | 每个相关 job 都取 |
| Pillow / mcp | 按项目说明装环境时**都没有**（见 D31） | 相关 job 都装 |
| ffmpeg | 不一定有（本机那一份来自 MATLAB） | runner 镜像自带，**CI 没有显式装**（见 D25） |
| git 历史与标签 | 取决于本地 clone | `fetch-depth: 0`，全量 |
| 依赖版本 | venv 可能与锁文件不同步 | `--frozen`，与锁文件严格一致 |
| 并发 | 一次一个 | 11 个 job 并行 |

### 0.3 判据

- **差异**：同一个输入在两个平台上会给出不同的判定（含「都过，但验的东西不同」）。
- **一致**：两个平台的判定相同，且验的是同一件事。
- 本文只写差异与已处理过的；「查过、一致的」清单在 §5。

---

## 1. 会让两个平台给出不同答案的差异

按后果排序，分四组。

### 1.1 测量与报告

| # | 门禁（出处） | 差在哪 | Windows 判 | Linux 判 | 后果 | 建议 |
|---|---|---|---|---|---|---|
| D1 | 测量门禁<br>`scripts/refresh-report-figures.py:1315-1321`、`:1469-1478`、`:1512` | 记录的「跳过的测试身份」是 Windows 那一份：Linux 上那三条 Windows-only 的测试会整条跳过，身份集合对不上，测量被判不完整；而 `--check` 在不完整时保留了旧记录并仍然返回 0 | 测量完整，数字被真正核对一遍 | 测量被判不完整，数字一个都不核对，**门禁变成空转但仍然是绿的** | CI 的 measurement job 在这棵树上恒绿且无实际作用；「报告里的数字属于这棵树」这件事**只有本地的 Windows 在守** | 让两边跑同一套测试（见 D36）；**另外，不完整时 `--check` 必须返回非 0**（现在返回 0） |
| D2 | 测量门禁<br>`scripts/refresh-report-figures.py:261-263`、`:355-364` | 子进程输出用文本模式解码但没写编码，落回平台默认编码；父进程的环境也没固定 `PYTHONUTF8` | cp936 | UTF-8 | 父子两边只要有一边进了 UTF-8 模式，字节就按另一边的编码解释。更糟的是解码失败时**子进程不抛异常**，只是把输出变成空值，于是下游报的是一个与编码无关的类型错误 → 本地崩、CI 好，且是按内容触发的间歇故障 | `run()` 加 `encoding="utf-8", errors="replace"`；环境里加 `PYTHONUTF8=1`，把父子两边的契约钉死；所有用到子进程输出的地方加一层空值兜底 |
| D3 | 覆盖率与弱模块表<br>`src/dexatlas/tools/base.py:346`、`src/dexatlas/tools/jadx/adapter.py:209-211`、`src/dexatlas/tools/androguard/worker.py:180-184` | 这三处是平台分支：Windows 走 taskkill 与 `.bat` 启动器，Linux 走进程组与 POSIX 限额。**被覆盖的行因此不同** | 报告里的 93.3% 与弱模块表是 Windows 那一份 | 同一棵树会得到另一个百分比与另一张弱模块表 | 即使 D1 修好，CI 量出来的覆盖率也会与报告里的对不上 → CI 红；今天的报告在 Linux 上是**错的**，只是没人比对 | 在报告里注明覆盖率是在哪个平台上量的；或把平台分支挪到不参与覆盖统计的位置；或让测量在两个平台上各跑一次并记录两份 |
| D4 | 测量门禁<br>`scripts/refresh-report-figures.py:331-336` | 清旧覆盖率数据时直接 `path.unlink()`，没有兜住失败 | 别的进程正开着这个文件 → 抛 PermissionError → 测量脚本带着 traceback 崩掉，一个数都不写 | 允许删除已打开的文件 → 删除成功，**把另一次运行的覆盖率数据静默毁掉** | 同一行代码，两个平台两种坏法：Windows 是崩，Linux 是静默出错。后者更坏 | 删不掉就报出来并退出（而不是崩），并提示「有另一次测量在跑」；两个平台用同一条路径 |
| D5 | 测量门禁<br>`scripts/refresh-report-figures.py:604-611` | 指纹要枚举的文件集合用 `rglob("*.py")`。**Windows 上这个匹配不区分大小写，Linux 上区分**（已实测，见 §7） | 多算进大写扩展名的文件 | 不算 | 树里只要出现一个 `.PY` 文件，指纹就与 CI 不同 → CI 判「树变了」→ 红；本地无感 | 改成显式比较后缀（`path.suffix == ".py"`），或改用 `git ls-files`（与 `check-version-claims` 的写法一致） |
| D6 | 测量门禁与引用检查<br>`scripts/refresh-report-figures.py:518`、`:550`、`:571-572`、`scripts/remap-citations.py:196`、`scripts/check-doc-citations.py:1084` | 前四处用文本模式写文件而没写换行参数，Windows 上把 LF 翻译成 CRLF；引用检查算摘要的那一处是整个脚本里**唯一按字节读**的，对行尾敏感 | 写出来是 CRLF，摘要按 CRLF 算 | 写出来是 LF，摘要按 LF 算 | 重锚引用的脚本在 Windows 上会把整个文档转成 CRLF，而 `.gitattributes` 会在提交时归一化 → **`git diff` 什么都看不见，开发者收不到任何信号**；引用检查印出的「本次针对的是哪个 subject」在两个平台上是两个值 | 那四处加 `newline="\n"`；摘要改成按归一化后的文本算，或先做 CRLF 归一 |
| D7 | CI 的覆盖率门禁<br>`.github/workflows/ci.yml:150-153`、`docs/reports/phase1-execution-report.md:77` | CI 用同一道 `--fail-under=80` 门禁量三棵不同的树（全后端 / 无 Java / 只有 Apktool），而报告里那个 93.3% 属于第四棵——Windows、本机、三个后端都在 | 报告里的 93.3% 是本机量出来的 | 三道 job 各自量各自的树，没有一道量的是报告描述的那棵 | 那道 80% 的门禁守的是**阈值**，不是**发布出去的那个数**；CI 里的注释还写着「从 82% 掉到 70%」，与 93.3% 已经差了十一个点 | 在报告里写明 93.3% 是在哪棵树上量的；加一道与报告同配置的覆盖率 job；顺手改掉那条陈旧的注释 |

### 1.2 契约活检

| # | 门禁（出处） | 差在哪 | Windows 判 | Linux 判 | 后果 | 建议 |
|---|---|---|---|---|---|---|
| D8 | 契约活检<br>`scripts/verify-public-contracts.py:129-135`、`src/dexatlas/api/app.py:411-413` | 轮询把「项目还不存在」当成终态：分析是后台任务，POST 立刻返回 202，项目行稍后才写入；这时 GET 返回 404，脚本读到的状态是空串，不在等待集合里 → **第一轮就跳出** | 工作区是复用的，行早就存在，撞不上 | 干净的工作区上第一轮就可能撞上 | 报出来的是「分析完成，status=」——既不说明原因也不说明修法；间歇性失败，负载越高越容易撞上 | 把 404 当成「还没建好」继续等，而不是终态 |
| D9 | 契约活检<br>`scripts/verify-public-contracts.py:38`、`:68`、`src/dexatlas/api/app.py:379-385`、`src/dexatlas/config/settings.py:66-67` | 工作区放在 `.scratch` 下且**每次运行前不清空**；数据库也在这棵工作区里，所以上一次跑出来的项目行还在 | 上传时按哈希查到了既有项目 → **直接返回旧项目，分析根本没重跑**；后面所有断言读的是上一次的快照 | 每次都是干净的工作区，会真的跑一遍分析 | **本地可能在没跑分析的情况下判绿**，而 CI 会重跑并可能失败；本地绿不代表 CI 绿 | 每次运行前删掉工作区；或把项目 id 里的哈希换成本次运行唯一的 |
| D10 | 契约活检<br>`scripts/verify-public-contracts.py:128-135` | 分析完成的等待预算是写死的 240 次 × 0.5 秒 = 120 秒；CI 装了 JADX 与 Apktool（走完整反编译），本地常常没装（只走 androguard） | 没装后端时秒级完成，预算绰绰有余 | 装了后端且 runner 负载高时可能超过 120 秒 | **CI 红、本地绿**；tag 那一轮已经踩过（runner 负载高时挂在这一项） | 预算按配置给足（装了后端就至少给 600 秒），或把超时判成一条明确的信息而不是硬失败；本地门禁清单里也要写明「装后端」，否则本地根本不是在测同一件事 |
| D11 | 契约活检<br>`scripts/verify-public-contracts.py:73-83` | 结束时用 `terminate()` 停 uvicorn：POSIX 上是 SIGTERM（优雅关闭），Windows 上是 TerminateProcess（硬杀） | 硬杀，工作区里的 sqlite 可能没关干净 | 优雅关闭 | 本地下一次运行可能读到上一次留下的半开状态 → **本地红、CI 绿**，而且与代码无关 | 结束前先请求优雅退出再兜底强杀；至少在下次运行前删掉工作区（与 D9 一起改） |
| D12 | 契约活检<br>`scripts/verify-public-contracts.py:40`、`:73-78` | 端口写死 8977，且 uvicorn 的输出都丢进 DEVNULL | 端口被占时报出来的是「60 秒后 uvicorn 没回答健康检查」；**上一次跑剩下的 uvicorn 还活着的话，它会直接把检查答掉** | runner 上端口不会冲突 | **本地红、CI 绿**，但报的是一条误导性的信息；更糟的是本地可能答的是另一个工作区的旧服务 | 启动前动态挑一个空闲端口；把 uvicorn 的输出接到 `.scratch` 下的文件（失败时打印） |
| D13 | 契约活检<br>`scripts/verify-public-contracts.py:466-476` | 断言按「这次有没有装后端」分支：没有源码后端时验的是**空答案契约**，有源码后端时验的是**真答案契约** | 本机常常两个后端都没有 → 验的是空答案那一半 | 装了 JADX 与 Apktool → 验的是真答案那一半 | **本地绿不代表 CI 绿**：本地那台机器从来没有跑过带 JADX 的那几条断言。契约表自己记着这个分叉（47 条与 48 条） | 本地也装后端；或把「没装后端」判成一条明确的「需人工」而不是换一个断言 |
| D14 | 契约活检<br>`scripts/verify-public-contracts.py:34`、`pyproject.toml:60-65` | 那个 extra 的 SDK 在**模块顶层**导入；而项目说明里给的那条安装命令没有装它 | 按说明装的环境 → 导入处就抛 ModuleNotFoundError，**一条检查都没跑** | 相关 job 装了 | 本地红、CI 绿，而且报的是一个与代码无关的导入错误 | 把那行导入挪进用到它的那个函数里，让「没装」变成一条被报告出来的失败；并把安装命令补齐（见 D31） |
| D15 | 契约活检<br>`scripts/verify-public-contracts.py:47-54` | 没有 UTF-8 输出守卫，而同类的版本声明检查有 | 控制台是 cp936 时，一条失败的检查带着非 ASCII 的细节 → UnicodeEncodeError → 脚本死在中途 | UTF-8，没问题 | **本地红、CI 绿**，而且退出码 1 与「有一条检查没过」没法区分 | 把版本声明检查里那段重配输出流的写法搬过来 |

### 1.3 文档与引用检查

| # | 门禁（出处） | 差在哪 | Windows 判 | Linux 判 | 后果 | 建议 |
|---|---|---|---|---|---|---|
| D16 | M10 自查<br>`scripts/m10_selfcheck.py:254-262` | 相对链接检查用 `Path(...).resolve()` 判断目标是否存在；而 **Windows 把三个点规范化成上一级目录**，Linux 上三个点是一个普通目录名 | 占位链接判绿 | 占位链接判红 | 与本轮已经修好的那处（§4）是同一个 bug 类，**同样的写法还留在 M10 自查里**；今天那三份被检查的文档里还没有占位链接，所以是潜伏的 | 复用 `tests/test_docs.py` 里已经写好的逐段按名查找的写法（§4），不要用 `resolve()` |
| D17 | 引用检查<br>`scripts/check-doc-citations.py:445-453` | 路径探测直接问文件系统存不存在；**Windows 的文件系统不区分大小写** | 一条大小写写错的引用**直接命中**真实文件，判绿 | 探测落空 → 退回到按小写折叠的名字索引 → 可能命中另一个文件，或者变成「有歧义」判红 | **本地绿、CI 红** 的典型入口：仓库里已经有 `docs/roadmap/ROADMAP.md` 这种大写文件名，谁把引用里的路径大小写改错，Windows 仍然绿，Linux 立刻红 | 探测改成逐级按名精确比对，不依赖文件系统的大小写语义 |
| D18 | 引用检查<br>`scripts/check-doc-citations.py:322`、`:430-434` | 文件索引走整棵树，只剪了六个目录名；缓存目录、临时目录、取回来的 fixture 目录都被算了进去 | 开发机上残留的缓存文件进了索引 → 裸名引用的候选更多 → 更容易判「有歧义」 | runner 上的残留与本机不同 | 这道门禁的裁决**取决于跑它那台机器上残留了什么**：同一棵提交，两个平台候选集不同，判定可能分叉 | 剪枝集合与忽略文件对齐；或只索引 git 认识的文件 |
| D19 | 引用检查<br>`scripts/check-doc-citations.py:97-98` | 文档清单里的两处按扩展名匹配，**Windows 上不区分大小写** | 一个叫 `v1.0.0.MD` 的文件会被收进清单并检查 | 不会被收进 | **本地比 CI 严**（反过来）：一份用大写扩展名新增的发布说明能在 Linux CI 上完全逃过这道门禁，而在 Windows 上被抓住 | 改成显式按后缀比对，别依赖 glob 的大小写语义 |
| D20 | 版本声明检查<br>`scripts/check-version-claims.py:1565-1572` | 回退分支（树里没有 git 时走的那条）用 `rglob("*.md")` 找文档，同样是 Windows 上不区分大小写 | 会检查 Linux 根本看不到的文档 | 不会 | 两个平台检查的**文档集合**不同，结论可能分叉 | 改成显式按后缀比对；并让走 git 的那条分支与它一致 |
| D21 | 版本声明检查<br>`scripts/check-version-claims.py:462-470` | 调 git 之前没有查 git 在不在；找不到可执行文件时抛的是「文件不存在」而不是「命令没跑通」 | Windows 上 Git for Windows 常常不在系统 PATH 上（只有 Git Bash 里有）→ 直接崩 | runner 上一定有 git | 本地崩、CI 绿，而且退出码与「有一条真实的发现」没法区分；文档里承诺的「没有 git 就退回源码包那条路」根本没走到 | 给三个 git 辅助函数加上存在性守卫，把「找不到 git」变成那条承诺过的退路 |
| D22 | 版本声明检查<br>`scripts/check-version-claims.py:1587-1601`、`tests/test_console_output.py:106-108` | 基线的选取依赖远端主干与标签列表；CI 显式取全量历史，本地取决于 clone 的深度 | 浅 clone 时标签相关的检查整条跳过 | 全量历史，一定有标签 | **本地更宽松**：本地的版本声明检查可能根本没跑，而 CI 一直在跑 | 本地门禁清单里加一句「确认 clone 是全量的」；或让浅 clone 变成一条明确的失败 |

### 1.4 工具、环境与排序

| # | 门禁（出处） | 差在哪 | Windows 判 | Linux 判 | 后果 | 建议 |
|---|---|---|---|---|---|---|
| D23 | mypy<br>`pyproject.toml:212-217` | mypy 的 platform 缺省取**宿主平台**，而不可达告警是开着的 | `sys.platform` 等于 linux 的分支被判不可达并报错 | 等于 win32 的分支被判不可达并报错 | 同一份源码在两个平台上得到不同的 mypy 结论（已实测，见 §7）。今天的 `src/dexatlas` 用的是 `os.name`（mypy 不对它做平台收窄），所以暂时两边一致；**任何人在 `src/dexatlas` 里写一行 `sys.platform` 就会踩到** | 在 mypy 配置里显式写 `platform = "linux"`（与 CI 对齐）或 `platform = "any"` |
| D24 | 符号链接测试<br>`tests/test_apktool_smali.py:293-295`、`tests/test_jadx_source_paths.py:285-287` | 建符号链接失败就跳过。Windows 上建链接要开发者模式或管理员，Linux 上默认可建 | 没有权限时整条测试跳过 | 一定跑 | **本地更宽松**：本地可能红也可能绿，CI 一定跑这条。安全相关的「链接不能被跟随」这条断言，本地可能根本没验 | 本地门禁清单里写明「开开发者模式」；或把这两条测试改成在 Windows 上用 junction、不依赖真实链接的等价物 |
| D25 | ffmpeg<br>`tests/test_docs.py:519-521` | 没装 ffmpeg 就跳过。CI 的 runner 镜像自带 ffmpeg，但 **CI 的 measurement job 并没有显式安装它** | 本机那一份来自 MATLAB 的目录，不是一个声明过的依赖；换一台机器就没有 | 现在恰好不跳；**runner 镜像一换就多一个跳过** | 本地与 CI 的「跳过集合」不同（与 D1 是同一根因的另一处表现）；本机的「0 跳过」这个前提建立在一个偶然的安装上，而 CI 的「完整」也是白捡的 | 把 ffmpeg 列进本地门禁的前置条件清单；CI 的 measurement job 里显式装它；并在报告里点名「本次跳过了哪些测试」 |
| D26 | 第三方 fixture 与后端的查找<br>`scripts/fetch-fixtures.sh:39`、`.github/workflows/ci.yml:144-148`、`tests/test_androguard_integration.py:48`、`scripts/refresh-report-figures.py:1057-1060` | fixture 不在就跳过：CI 每个相关 job 都用令牌取，本地没取就静默跳过。另外后端的查找在 Windows 上会经由 PATHEXT 命中批处理文件，在 Linux 上只命中可执行脚本，于是「后端不在就跳过」的那些测试在两个平台上的跳过身份可能不同 | 没取 fixture 就跳过 | 一定在 | **本地更宽松**：本地绿是因为没跑，CI 红是因为跑了；且本机「0 跳过」这个前提只在取过 fixture 的机器上成立 | 把取 fixture 列为本地门禁的前置；或让 fixture 缺失成为一条明确的失败而不是跳过；把「因可选工具而跳过」的那几条从 D1 的身份比较里单列 |
| D27 | 全部本地门禁<br>`.github/workflows/ci.yml:53`、`:142`、`scripts/prove-red.sh:58` | 本地按惯例用 `uv run --no-sync`，用的是 venv 里**当时装着的**版本；CI 用 `uv sync --frozen`，严格等于锁文件。证明脚本里的 `uv sync` 连 `--frozen` 都没有 | 工具版本可能比锁文件旧 | 严格等于锁文件 | 同一份代码，两个平台可能用不同的 ruff / mypy / pytest 得到不同的结论；那个证明脚本还可能顺手把锁文件改了 | 本地门禁清单的第一步改成 `uv sync --frozen --all-extras`；证明脚本加上 `--frozen` |
| D28 | 后端版本<br>`scripts/install-backends.sh:20-21`、`scripts/fetch-jadx.py:24`、`docs/analysis-provenance.md:273` | 版本固定只写在 CI 用的安装脚本里；本机装的是哪一版没有任何东西核对，而文档却声明「所有输出都是在固定的那三版下产生的」 | 本机版本不同 → 报告里记的来源与文档的声明不符 | 每次装固定版本，永远相符 | 本地量出来的来源说明可能与文档的声明对不上，**而没有任何门禁会发现** | 测量脚本在开跑前核对三个后端的版本，与文档里的声明不符就拒绝写入 |
| D29 | 版本声明检查<br>`scripts/check-version-claims.py:1569` | `sorted()` 作用在 Path 对象上时，比较用的是**规范化之后**的字符串，而 Windows 的规范化会转小写 | 同一个集合，顺序按小写排（已实测：`A.md`、`b.md`、`C.md`、`d.md`） | 同一个集合，顺序按码点排（`A.md`、`C.md`、`b.md`、`d.md`） | 判定的**集合**相同，但**报出的顺序**不同；树里有 README、AGENTS、CHANGELOG 这类大写名，顺序就会差 | 一律用 `as_posix()` 做排序键（本仓库测量脚本已经这么写） |
| D30 | Windows 的路径长度上限<br>`scripts/verify-public-contracts.py:38` | Windows 的路径上限是 260 字符（这台机器上长路径支持是关的），POSIX 是 4096 | 本工作区下最深的路径是 209 字符，余量 51；换个更深的 checkout 根目录就过线 | 同样的路径结构离上限还有一千多字符 | 越线时是 `OSError`，**只有 Windows 会犯**；而本项目已经踩过一次「路径比文件名能装下的长」的坑 | 把契约活检的工作区放在一个短的根目录下，而不是仓库里 |
| D31 | 项目说明里的安装命令<br>`CLAUDE.md:47` | 那条命令**没有 demo 与 mcp 两个 extra**，而 Pillow 在 demo 里、那个 SDK 在 mcp 里；CI 的相关 job 都装了 | 按说明装的环境 → 画图那条测试被跳过 → 命中 D1 → 刷新变成静默空操作，还打印「报告已经是最新」并退出 0；契约活检则在导入处就死 | 相关 job 都装了 | 按项目自己的说明书装环境，就会得到一次「绿色但没测」的刷新，和一条与代码无关的导入错误 | 把安装命令补齐这两个 extra；并在「缺什么」的提示里**明确点名**「缺 Pillow ⇒ 本次测量只能是部分的」 |
| D32 | 项目说明与代码<br>`tests/conftest.py:30-35` | 项目说明里写的是「所有产物都在一个固定的盘符路径下」，而代码算出来的是「仓库目录下的 .scratch」 | 主 checkout 上两者恰好是同一个目录 | 在工作区里两者是**两个不同的目录** | 说明里那条「系统盘快满了」的告诫是照着一个代码并不使用的路径写的；工作区会在项目盘上长出自己的 .scratch，而那条告诫不适用 | 把说明改成「仓库目录下的 .scratch；在主 checkout 上它是那一个路径」 |
| D33 | CI 的临时目录<br>`.github/workflows/ci.yml:291-299` | 「把生成物留在 .scratch」这一步**只在六个 job 里的一个**里 | 临时目录由测试自己重定向到项目里，但 `uv sync` 与 `uv run` 发生在重定向之前，仍落在系统盘 | runner 的临时目录就是项目目录 | 本机系统盘已经 97% 满，`uv sync` 有可能因为没空间而失败，而 CI 不会 | 把这一步做成复合动作，给其余五个 job 都加上 |
| D34 | 测量脚本的前置条件提示<br>`scripts/refresh-report-figures.py:1057-1060` | 判「JADX 在不在」用的是 PATH 查找；而 CI 是用环境变量把后端指给代码的，并没有把它的 bin 目录加进 PATH | 本机装了就在 PATH 里，提示正常 | **CI 上会误报「JADX 缺失」** | 只影响提示不影响判据，但读 CI 日志的人会被误导 | 让这段提示改用与后端本身相同的解析逻辑，而不是 PATH 查找 |
| D35 | M10 自查<br>`scripts/m10_selfcheck.py:650-669` | 「门禁命令可执行」这条判据先看 PATH，再看 venv 里的两种目录布局 | 机器上装了全局工具时，PATH 那一支就会命中 | runner 上 PATH 里只有 venv，靠 venv 那一支命中 | 结论跟着**环境里的 PATH** 走，而不是跟着树走；一个刚建、还没同步过 venv 的工作区会在本地判红、在 CI 判绿 | 判据只看 venv 的两种布局；「没装」判成「需人工」而不是「失败」 |

---

## 2. 一处相邻但不属于平台差异的发现

**引用检查器只查一份写死的清单。** `scripts/check-doc-citations.py:87-99` 的文档清单是**写死的 13 个文件**；
`tests/test_doc_citations.py` 的那几条测试也用同一份清单。
于是**任何新写的报告里的 `file:line` 出处，不会被任何自动检查覆盖**——
本文自己的 86 条出处就是例子（它们是逐条手工核对的，不是门禁核对的）。
重锚引用的脚本也只列了 4 份文档（`scripts/remap-citations.py:50-55`），
所以清单外的文档一旦漂了，那道门禁既查不出来也修不了。

**建议**（改动由主会话做）：把新报告加进那份清单，并把重锚脚本的文档范围与检查器对齐。

---

## 3. 反向：本地比 CI 更严

这两处的方向与 §1 相反——本地红、CI 绿。同样有害：CI 从来没有验过它们。

### 3.1 D36 三条 Windows-only 的测试在 CI 里整条跳过

- 出处：`tests/test_backend_discovery.py:49`、`tests/test_backend_discovery.py:62`、`tests/test_backend_timeout.py:96`；
  它们守的产品行为在 `src/dexatlas/tools/jadx/adapter.py:209-219`（把 jadx 的启动器换成 Windows 能执行的那一个）。
- **差在哪**：条件是「不是 Windows 就跳过」。Windows 上跑，Linux 上跳过。
- **哪个平台判什么**：本地跑这三条，CI 一条不跑。
- **后果**：CI 从来没有验过「指向 shell 脚本时解析到旁边的批处理文件」这条行为——而这正是 Windows 用户实际会踩的那条路径。
  这三条也是 D1 里「跳过身份不同」的来源：**修掉它们，D1 的一半就修掉了。**
- **怎么改**：把这三条改成跨平台——测的是「在 Windows 上选批处理文件、在别处选原文件」这个纯函数，
  于是两个平台都能验同一条规则；或者给 CI 加一个 Windows runner 的 job。

### 3.2 D37 两个脚本的输出编码没有钉死

- 出处：`scripts/m10_selfcheck.py:1124-1136`、`scripts/verify-public-contracts.py:47-54`；
  对照 `scripts/check-version-claims.py:1604-1621`（同样的问题在那边已经解决了）。
- **差在哪**：版本声明检查在开跑前把 stdout 与 stderr 重配成 UTF-8；这两个脚本没有。
  控制台上的中文在两个平台上都没问题（Windows 的控制台用 UTF-8 写），
  但**输出被重定向到文件或管道时，Windows 用 cp936，Linux 用 UTF-8**。
- **哪个平台判什么**：一个只含 GBK 字符的内容在两边都打得出来；
  一旦内容里出现 GBK 之外的字符（破折号以外的排版符号、表情），Windows 上抛 UnicodeEncodeError，
  脚本中途死掉 → **本地红、CI 绿**，而且死在哪一行取决于内容。
- **后果**：退出码 1 既表示「有一条检查没过」，也表示「脚本崩了」——这两件事被混成了一件事。
- **怎么改**：照版本声明检查的做法，在 `main()` 开头把两个流重配成 UTF-8。

---

## 4. 已经处理过的

这些是本轮之前就修好的，列在这里是因为它们正是这类差异的样本，改动时不要把它们改回去。

| 事项 | 出处 | 现在的做法 |
|---|---|---|
| 三个点占位链接 | `tests/test_docs.py:112-137`、`:156-175` | 链接检查**按名字逐段查找**，不做路径规范化；因此三个点构成的占位链接在两个平台上都是断链。回归测试就写在旁边 |
| 测量指纹的换行 | `scripts/refresh-report-figures.py:626-638` | 哈希前先把 CRLF 归一成 LF，所以同一份源码在两个平台上是同一个指纹 |
| 报告写回 | `scripts/refresh-report-figures.py:1480-1484` | 用 `write_bytes` 写回，不经过文本模式的换行翻译 → 两个平台写出同样的字节 |
| 工作区的换行 | `.gitattributes:2` | 全部文本按 LF 检出，两个平台的字节一致 |
| 版本声明检查的输出 | `scripts/check-version-claims.py:1604-1621` | 开跑前把 stdout 与 stderr 重配成 UTF-8，字符写不出去时替换而不是抛错 |
| 引用的文件名大小写 | `scripts/check-doc-citations.py:427-434` | 文件名统一折叠成小写后建索引，所以大小写不一致的**裸名**引用在两个平台上判得一样 |
| 门禁命令的查找 | `scripts/m10_selfcheck.py:650-669` | venv 的两种目录布局都认（Windows 的与 POSIX 的）——问题在 PATH 那一支，见 §1.4 的 D35 |
| 测量的并发锁 | `scripts/refresh-report-figures.py:395-412` | Windows 用一种锁、POSIX 用另一种，两边都是非阻塞：拿不到锁就说拿不到，而不是排队 |
| 社交预览图<br>（CI 那一侧） | `.github/workflows/ci.yml:500-512` | CI 跑的是 `--check`，**只比数字，不比 PNG 的字节**——因为两个平台的字体不同，画出来的图本来就不一样（字体目录那一侧见 §1.4） |
| Docker 镜像 | `.github/workflows/ci.yml:406-414` | 本地门禁清单里没有这一道，它只在 CI 跑；本机装没装 Docker 都不影响本地门禁的结论 |

---

## 5. 查过、两个平台一致的

| 事项 | 出处 | 为什么一致 |
|---|---|---|
| 字符串排序 | 全仓库 | `sorted()` 作用在字符串上时按 Unicode 码点排，与 locale 无关；**全仓库没有 `locale` / `strcoll` / `setlocale`**。中英混排的顺序在两个平台上相同（Path 对象上的排序是另一回事，见 D29） |
| 集合与字典的迭代顺序 | 全仓库 | Python 3.7 起的插入序，两个平台一致 |
| 目录遍历的顺序 | `tests/test_docs.py:100`、`tests/test_public_contracts.py:837`、`scripts/check-doc-citations.py:432` | `os.walk` 的产出顺序取决于文件系统（NTFS 与 ext4 不同），但这三处要么把结果排序，要么只当集合用 |
| 文件读取的编码 | 全部门禁脚本与测试 | 读文件一律显式写 `encoding="utf-8"`，不落回平台默认 |
| 子进程输出的编码<br>（引用与版本声明两处） | `scripts/check-doc-citations.py:462-470`、`scripts/check-version-claims.py:462-470` | 这两处显式写了 `encoding="utf-8", errors="replace"`；只有测量脚本那一处漏了（见 D2） |
| 换行的归一 | `scripts/check-doc-citations.py:461`、`:793` | 文本模式读入会把 CRLF 归一成 LF，行号与内容在两个平台上相同 |
| 链接的路径写法 | `scripts/refresh-report-figures.py:600-611` | 路径一律转成 POSIX 形式再比较，路径分隔符不影响指纹 |
| 测试的收集数 | `docs/how-to-verify.md:147` | 树里没有模块级跳过，也没有自定义的收集规则，所以「收集到多少个测试」与平台无关；变的只是它们跑过还是跳过 |
| mypy 对平台分支的收窄 | `src/dexatlas/tools/base.py:346` | mypy 不对 `os.name` 做平台收窄，所以这几个分支在两个平台上都被当作可达（这条与 D23 是两回事） |
| 同一测试在两边的不同机制 | `tests/test_backend_timeout_exit.py:69`、`:164`、`:209` | 这几处按平台走不同的桩，但两边都验到了同一件事：杀不掉时如实说杀不掉 |
| 路径安全判断 | `src/dexatlas/core/paths.py:140-148` | 三个点在两个平台上判得不同（Windows 更严），但**两边都拒绝**，结论一致 |
| 引用检查里的三个点 | `scripts/check-doc-citations.py:445-453` | 探测走的是 `is_file()` 而不是路径规范化，而 `is_file()` 对不在末尾的三个点分量不折叠 → 两个平台一致（那个 bug 在 §1.3 的第一条里，不在这两个脚本里） |
| 社交预览图的判定<br>（CI 那一侧） | `scripts/make-social-preview.py:434-472` | 字体可用性**有检查**：逐角色查文件在不在，缺了就报错并说清缺什么、去哪找、怎么指定；没有静默回退到默认位图字体。CI 只跑 `--check`、不重画，所以结论必然相同 |
| 版本声明的基线选取 | `scripts/check-version-claims.py:1587-1601` | 选取规则本身与平台无关；差别在**输入**（本地有没有全量历史、远端主干在不在），那是 D22 说的环境差异，不是逻辑差异 |
| 安装脚本的临时目录 | `scripts/install-backends.sh:22` | 那个只在 CI 有的变量没有时退回 `/tmp`；两个平台都能建目录，差别只是落在哪 |
| 证明脚本的临时目录 | `scripts/prove-red.sh:26` | 用 `TMPDIR`，Windows 一般没有，于是退回 `/tmp`；Git Bash 下 `/tmp` 会被映射到一个真实目录，能用 |
| 退出码与超时 | `scripts/verify-public-contracts.py:83`、`:91-100` | 超时值与退出码的语义在两个平台相同（差异在**预算够不够**，那是 D10） |
| 契约活检的端口冲突 | `scripts/verify-public-contracts.py:40` | 8977 只被一个进程绑定；CI 的各 job 是各自独立的 runner，M10 那个 job 根本不起服务 → CI 上不可能撞车，撞车只发生在本地同时跑两样东西的时候 |
| 产物里有没有本机路径 | `src/dexatlas/core/paths.py:110-118` | 对外只给文件名，报告与 JSON 里不出现绝对路径，所以临时目录落在哪不影响产物 |
| 浮点与百分比 | `scripts/refresh-report-figures.py:799-801` | 覆盖率是一个除法再按固定格式格式化，两个平台逐位一致 |
| git 的调用形状 | `scripts/check-version-claims.py:462-470` | 用列表形式、不开 shell；Windows 靠 CreateProcess 补 `.exe` 并查 PATH，POSIX 靠 execvp 查 PATH；没有写死的 POSIX 路径，参数也不需要 shell 转义 |

---

## 6. 建议的落地顺序

按「先堵住会让人以为验过、其实没验的洞」排：

1. **D1 + D36** 一起做：把那三条 Windows-only 的测试改成跨平台，两边的跳过集合就对齐了；
   同时把 `--check` 在不完整时的返回码从 0 改成非 0。**这是唯一一条会让门禁「假装自己验过」的洞。**
2. **D2**：几行改动，把父子进程的编码契约钉死。
3. **D31**：把安装命令补齐 extra —— 否则按项目自己的说明书装环境就会得到一次「绿色但没测」的刷新。
4. **D8 + D9 + D10 + D11 + D12**：契约活检的五件事——404 不是终态、干净的工作区、预算、优雅退出、动态端口。
5. **D23**：mypy 显式写 platform。
6. **D3 + D7**：在报告里写明覆盖率是在哪个平台上、哪棵树上量的（不必重做测量）。
7. **D13、D15、D16、D17、D18、D19、D20、D21、D22、D24、D25、D26、D27、D28、D30、D32、D33、D34、D35、D37**：逐条改；
   其中 **D17**（大小写写错的引用本地绿 CI 红）是这一组里最容易在下一个版本踩到的。

---

## 7. 复核方法与可复现的实验

以下实验在 Windows 11 + Python 3.12 上实跑过，脚本写在工作区的 `.scratch/gate-audit/` 下（该目录不入库，用完已删）。

**实验一：Windows 把三个点规范化成上一级目录**

```python
>>> pathlib.Path("docs/reports/...").resolve()
WindowsPath('E:/Dexatlas/docs/reports')      # 存在 -> 判绿
```

同一个表达式在 Linux 上得到 `docs/reports/...`（不存在 -> 判红）。
注意 `os.path.normpath` 两边都保留三个点——**是 `resolve()` 背后的 Win32 路径规范化把它吃掉的**，
所以只有走 `resolve()` 的代码受影响（`is_file()` 不受影响）。

**实验二：mypy 的 platform 取宿主平台**

用同一个探针文件（一个 linux 分支和一个 win32 分支）：

| mypy 的 platform | 报出的不可达行 |
|---|---|
| 缺省（Windows 主机） | win32 分支 |
| 缺省（Linux 主机） | linux 分支 |
| 显式 linux | linux 分支 |

**实验三：`rglob` 的大小写敏感性**

在 Windows 上，一个同时含有 `A.PY`、`C.PY`、`b.py` 的目录里，`rglob("*.py")` 返回**三个**文件；
Linux 上只返回 `b.py`。

**实验四：`sorted()` 作用在 Path 上时按小写排**

| | 顺序 |
|---|---|
| `sorted(Path)`（Windows） | `A.md`、`b.md`、`C.md`、`d.md` |
| `sorted(str)`（两个平台） | `A.md`、`C.md`、`b.md`、`d.md` |

**实验五：编码与换行**

本机 `locale.getpreferredencoding()` 是 cp936、`sys.stdout.encoding` 是 gbk；
M10 的 `--json` 重定向到文件后产出 15953 字节、589 个 CRLF，且按 UTF-8 解不开。

**实验六：CI 与本地的跳过数**

`docs/reports/v1.0.0-ci-run-record.md:192-196` 记着 tag 那一轮 Linux 上的实跑：
Python 3.12 是 `1612 passed, 5 skipped`，measurement job 是 `passed=1597, skipped=4`；
而本仓库报告里嵌的记录是 `passed=1643, skipped=0`。**同一棵树，两个平台，跳过的身份集合不同。**

**实验七：路径深度余量**

本工作区下契约活检最深的那条路径是 209 字符，Windows 的上限是 260，而这台机器的长路径支持是关的
（注册表里是 0）——余量只有 51 个字符；主 checkout 是 167 字符；POSIX 那侧的上限是 4096。

---

## 8. 本文没有回答的

- **CI 上 11 个 job 并行时的资源竞争**（上一轮 tag run 踩过）不是平台差异，本文只把它记在 D10 里。
- **本机与 runner 的绝对速度**会随负载变化，无法在一次复核里给出稳定的结论；D10 给的是结构性的那一条。
- 本文**没有重跑任何测量**，也没有改动任何既有文件。
