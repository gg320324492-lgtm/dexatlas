# 本地门禁与 CI 门禁的差异（只读复核）

> 复核日期：2026年11月18日 · 复核方式：只读 · 复核树：`claude/exciting-shannon-d0f438` @ `9e1aa61`
>
> 本文回答一个问题：**哪些门禁在 Windows（本地）与 Linux（CI）上会给出不同的答案。**
> 每一处给出：差在哪 → 哪个平台判什么 → 门禁因此漏掉了什么（或误报了什么）→ 怎么改。
>
> 本文只新增这一个文件，没有改动任何既有文件。改动由主会话统一做。

## 摘要

- 复核范围：本地 6 道门禁（见 [v1.0.0-release-checklist.md](v1.0.0-release-checklist.md) §8.1）与
  CI 的 10 个 job（[ci.yml](../../.github/workflows/ci.yml)）。
- **查出 30 处平台差异**，其中 **28 处会让两个平台给出不同的答案**（本地绿 / CI 红，或反过来），
  另有 **2 处方向相反**（本地比 CI 更严，见 §2）。
- **最要紧的三条**：
  1. **D1 —— 报告里的测量记录是 Windows 的测量。** CI 的 measurement job 在 Linux 上跑，
     那三条 Windows-only 的测试在那里整条跳过，于是「跳过的身份集合」与记录里的对不上，
     测量被判为不完整；而 `--check` 在不完整时仍然返回 0。
     **结果是：CI 的测量门禁在这棵树上恒为绿，且什么都没验。**（§1 D1）
  2. **D2 —— 测量脚本的子进程输出按平台默认编码解码。** 本机是 cp936，Linux 是 UTF-8。
     父子进程只要有一边进了 UTF-8 模式，字节就按另一边的编码解释。（§1 D2）
  3. **D3 —— 契约活检的时间预算是按「本地那套配置」定的。** CI 装了 JADX 与 Apktool，
     走完整反编译；本地常常没装，只走 androguard 一条路。CI 因此比本地更容易撞上 120 秒的上限。（§1 D3）
- **本文不改任何东西。** 下面所有关于「会判什么」的判断都来自代码路径的推导与 §6 的实验，
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
| Java 后端 | 常常没装在本机 PATH 上 | 每个相关 job 都装，且版本固定 |
| 第三方 fixture | 需手动取 | 每个相关 job 都取 |
| Pillow | 按项目说明装环境时**没有**（见 D25） | measurement job 装了 |
| ffmpeg | 不一定有（本机那一份来自 MATLAB） | runner 镜像自带，**CI 没有显式装**（见 D10） |
| git 历史与标签 | 取决于本地 clone | `fetch-depth: 0`，全量 |
| 依赖版本 | venv 可能与锁文件不同步 | `--frozen`，与锁文件严格一致 |
| 并发 | 一次一个 | 11 个 job 并行 |

### 0.3 判据

- **差异**：同一个输入在两个平台上会给出不同的判定（含「都过，但验的东西不同」）。
- **一致**：两个平台的判定相同，且验的是同一件事。
- 本文只写差异与已处理过的；「查过、一致的」清单在 §4。

---

## 1. 会让两个平台给出不同答案的差异（按后果排序）

| # | 门禁（出处） | 差在哪 | Windows 判 | Linux 判 | 后果 | 建议 |
|---|---|---|---|---|---|---|
| D1 | 测量门禁<br>`scripts/refresh-report-figures.py:1315-1321`、`:1469-1478`、`:1512` | 记录的「跳过的测试身份」是 Windows 那一份：Linux 上那三条 Windows-only 的测试会整条跳过，身份集合对不上，测量被判不完整；而 `--check` 在不完整时保留了旧记录并仍然返回 0 | 测量完整，数字被真正核对一遍 | 测量被判不完整，数字一个都不核对，**门禁变成空转但仍然是绿的** | CI 的 measurement job 在这棵树上恒绿且无实际作用；「报告里的数字属于这棵树」这件事**只有本地的 Windows 在守** | 让两边跑同一套测试（见 D29）；**另外，不完整时 `--check` 必须返回非 0**（现在返回 0） |
| D2 | 测量门禁<br>`scripts/refresh-report-figures.py:261-263`、`:355-364` | 子进程输出用文本模式解码但没写编码，落回平台默认编码；父进程的环境也没固定 `PYTHONUTF8` | cp936 | UTF-8 | 父子两边只要有一边进了 UTF-8 模式，字节就按另一边的编码解释。更糟的是解码失败时**子进程不抛异常**，只是把输出变成空值，于是下游报的是一个与编码无关的类型错误 → 本地崩、CI 好，且是按内容触发的间歇故障 | `run()` 加 `encoding="utf-8", errors="replace"`；环境里加 `PYTHONUTF8=1`，把父子两边的契约钉死；所有用到子进程输出的地方加一层空值兜底 |
| D3 | 契约活检<br>`scripts/verify-public-contracts.py:128-135` | 分析完成的等待预算是写死的 240 次 × 0.5 秒 = 120 秒；CI 装了 JADX 与 Apktool（走完整反编译），本地常常没装（只走 androguard） | 没装后端时秒级完成，预算绰绰有余 | 装了后端且 runner 负载高时可能超过 120 秒 | **CI 红、本地绿**；tag 那一轮已经踩过（runner 负载高时挂在这一项） | 预算按配置给足（装了后端就至少给 600 秒），或把超时判成一条明确的信息而不是硬失败；本地门禁清单里也要写明「装后端」，否则本地根本不是在测同一件事 |
| D4 | 契约活检<br>`scripts/verify-public-contracts.py:38`、`:68`、`:162-163` | 工作区放在 `.scratch` 下且**每次运行前不清空**；项目 id 由 APK 的哈希决定，所以上一次跑出来的项目行还在 | 上一次的残留项目行可以顶替本次的结果，让「项目列表里至少有一行」这条判据通过 | 每次都是干净的工作区，判据是诚实的 | **CI 更严**：本地绿可能来自上一次运行的残留，CI 会红 | 每次运行前删掉工作区；或把项目 id 里的哈希换成本次运行唯一的 |
| D5 | 契约活检<br>`scripts/verify-public-contracts.py:73-83` | 结束时用 `terminate()` 停 uvicorn：POSIX 上是 SIGTERM（优雅关闭），Windows 上是 TerminateProcess（硬杀） | 硬杀，工作区里的 sqlite 可能没关干净 | 优雅关闭 | 本地下一次运行可能读到上一次留下的半开状态 → **本地红、CI 绿**，而且与代码无关 | 结束前先请求优雅退出再兜底强杀；至少在下次运行前删掉工作区（与 D4 一起改） |
| D6 | 覆盖率与弱模块表<br>`src/dexatlas/tools/base.py:346`、`src/dexatlas/tools/jadx/adapter.py:209-211`、`src/dexatlas/tools/androguard/worker.py:180-184` | 这三处是平台分支：Windows 走 taskkill 与 `.bat` 启动器，Linux 走进程组与 POSIX 限额。**被覆盖的行因此不同** | 报告里的 93.3% 与弱模块表是 Windows 那一份 | 同一棵树会得到另一个百分比与另一张弱模块表 | 即使 D1 修好，CI 量出来的覆盖率也会与报告里的对不上 → CI 红；今天的报告在 Linux 上是**错的**，只是没人比对 | 在报告里注明覆盖率是在哪个平台上量的；或把平台分支挪到不参与覆盖统计的位置；或让测量在两个平台上各跑一次并记录两份 |
| D7 | M10 自查<br>`scripts/m10_selfcheck.py:254-262` | 相对链接检查用 `Path(...).resolve()` 判断目标是否存在；而 **Windows 把三个点规范化成上一级目录**，Linux 上三个点是一个普通目录名 | 占位链接判绿 | 占位链接判红 | 与本轮已经修好的那处（§3）是同一个 bug 类，**同样的写法还留在 M10 自查里**；今天那三份被检查的文档里还没有占位链接，所以是潜伏的 | 复用 `tests/test_docs.py` 里已经写好的逐段按名查找的写法（§3），不要用 `resolve()` |
| D8 | mypy<br>`pyproject.toml:212-217` | mypy 的 platform 缺省取**宿主平台**，而不可达告警是开着的 | `sys.platform` 等于 linux 的分支被判不可达并报错 | 等于 win32 的分支被判不可达并报错 | 同一份源码在两个平台上得到不同的 mypy 结论（已实测，见 §6）。今天的 `src/dexatlas` 用的是 `os.name`（mypy 不对它做平台收窄），所以暂时两边一致；**任何人在 `src/dexatlas` 里写一行 `sys.platform` 就会踩到** | 在 mypy 配置里显式写 `platform = "linux"`（与 CI 对齐）或 `platform = "any"` |
| D9 | 符号链接测试<br>`tests/test_apktool_smali.py:293-295`、`tests/test_jadx_source_paths.py:285-287` | 建符号链接失败就跳过。Windows 上建链接要开发者模式或管理员，Linux 上默认可建 | 没有权限时整条测试跳过 | 一定跑 | **本地更宽松**：本地可能红也可能绿，CI 一定跑这条。安全相关的「链接不能被跟随」这条断言，本地可能根本没验 | 本地门禁清单里写明「开开发者模式」；或把这两条测试改成在 Windows 上用 junction、不依赖真实链接的等价物 |
| D10 | ffmpeg<br>`tests/test_docs.py:519-521` | 没装 ffmpeg 就跳过。CI 的 runner 镜像自带 ffmpeg，但 **CI 的 measurement job 并没有显式安装它** | 本机那一份来自 MATLAB 的目录，不是一个声明过的依赖；换一台机器就没有 | 现在恰好不跳；**runner 镜像一换就多一个跳过** | 本地与 CI 的「跳过集合」不同（与 D1 是同一根因的另一处表现）；本机的「0 跳过」这个前提建立在一个偶然的安装上，而 CI 的「完整」也是白捡的 | 把 ffmpeg 列进本地门禁的前置条件清单；CI 的 measurement job 里显式装它；并在报告里点名「本次跳过了哪些测试」 |
| D11 | 第三方 fixture 与后端的查找<br>`scripts/fetch-fixtures.sh:39`、`.github/workflows/ci.yml:144-148`、`tests/test_androguard_integration.py:48`、`scripts/refresh-report-figures.py:1057-1060` | fixture 不在就跳过：CI 每个相关 job 都用 `GH_TOKEN` 取，本地没取就静默跳过。另外后端的查找在 Windows 上会经由 PATHEXT 命中 `.bat`，在 Linux 上只命中可执行脚本，于是「后端不在就跳过」的那些测试在两个平台上的跳过身份可能不同 | 没取 fixture 就跳过 | 一定在 | **本地更宽松**：本地绿是因为没跑，CI 红是因为跑了；且本机「0 跳过」这个前提只在取过 fixture 的机器上成立 | 把取 fixture 列为本地门禁的前置；或让 fixture 缺失成为一条明确的失败而不是跳过；把「因可选工具而跳过」的那几条从 D1 的身份比较里单列 |
| D12 | 版本声明检查<br>`scripts/check-version-claims.py:1587-1601`、`tests/test_console_output.py:106-108` | 基线的选取依赖 `origin/main` 与标签列表；CI 显式取全量历史，本地取决于 clone 的深度 | 浅 clone 时标签相关的检查整条跳过 | 全量历史，一定有标签 | **本地更宽松**：本地的版本声明检查可能根本没跑，而 CI 一直在跑 | 本地门禁清单里加一句「确认 clone 是全量的」；或让浅 clone 变成一条明确的失败 |
| D13 | 全部本地门禁<br>`.github/workflows/ci.yml:53`、`:142`、`scripts/prove-red.sh:58` | 本地按惯例用 `uv run --no-sync`，用的是 venv 里**当时装着的**版本；CI 用 `uv sync --frozen`，严格等于锁文件。`prove-red.sh` 里的 `uv sync` 连 `--frozen` 都没有 | 工具版本可能比锁文件旧 | 严格等于锁文件 | 同一份代码，两个平台可能用不同的 ruff / mypy / pytest 得到不同的结论；`prove-red.sh` 还可能顺手把锁文件改了 | 本地门禁清单的第一步改成 `uv sync --frozen --all-extras`；`prove-red.sh` 加上 `--frozen` |
| D14 | 后端版本<br>`scripts/install-backends.sh:20-21`、`scripts/fetch-jadx.py:24`、`docs/analysis-provenance.md:273` | 版本固定只写在 CI 用的安装脚本里；本机装的是哪一版没有任何东西核对，而文档却声明「所有输出都是在固定的那三版下产生的」 | 本机版本不同 → 报告里记的来源与文档的声明不符 | 每次装固定版本，永远相符 | 本地量出来的 provenance 可能与文档的声明对不上，**而没有任何门禁会发现** | 测量脚本在开跑前核对三个后端的版本，与文档里的声明不符就拒绝写入 |
| D15 | 测量门禁<br>`scripts/refresh-report-figures.py:604-611` | 指纹要枚举的文件集合用 `rglob("*.py")`。**Windows 上这个匹配不区分大小写，Linux 上区分**（已实测，见 §6） | 多算进大写扩展名的文件 | 不算 | 树里只要出现一个 `.PY` 文件，指纹就与 CI 不同 → CI 判「树变了」→ 红；本地无感 | 改成显式比较后缀（`path.suffix == ".py"`），或改用 `git ls-files`（与 `check-version-claims` 的写法一致） |
| D16 | 契约活检<br>`scripts/verify-public-contracts.py:40`、`:73-78` | 端口写死 8977，且 uvicorn 的输出都丢进 DEVNULL | 端口被占时，报出来的是「60 秒后 uvicorn 没回答健康检查」 | runner 上端口不会冲突 | **本地红、CI 绿**，但报的是一条误导性的信息：真正的原因是端口被占 | 启动前先探测端口并给出明确的信息；把 uvicorn 的输出接过来（失败时打印） |
| D17 | M10 自查<br>`scripts/m10_selfcheck.py:1101-1119` | `--json` 那条路把结果 `print` 出去，`ensure_ascii=False` 保留原文；输出被重定向到文件时走的是平台默认编码 | 写出来的是 GBK + CRLF（已实测：15953 字节，589 个 CRLF，按 UTF-8 解不开） | UTF-8 + LF | M10 那份机读产物**在两个平台上不是同一种文件**；任何按 UTF-8 读它的消费者在 Windows 上直接失败 | 改用 `Path.write_text(payload, encoding="utf-8", newline="\n")` 写文件，不经过 `print` |
| D18 | M10 自查<br>`scripts/m10_selfcheck.py:650-669` | 「门禁命令可执行」这条判据先看 PATH，再看 venv 里的两种目录布局 | 机器上装了全局工具时，PATH 那一支就会命中 | runner 上 PATH 里只有 venv 的 bin，靠 venv 那一支命中 | 结论跟着**环境里的 PATH** 走，而不是跟着树走；一个刚建、还没同步过 venv 的工作区会在本地判红、在 CI 判绿 | 判据只看 venv 的两种布局；「没装」判成「需人工」而不是「失败」 |
| D19 | 测量门禁<br>`scripts/refresh-report-figures.py:331-336` | 清旧覆盖率数据时直接 `path.unlink()`，没有兜住失败 | 别的进程正开着这个文件 → 抛 PermissionError → 测量脚本带着 traceback 崩掉，一个数都不写 | 允许删除已打开的文件 → 删除成功，**把另一次运行的覆盖率数据静默毁掉** | 同一行代码，两个平台两种坏法：Windows 是崩，Linux 是静默出错。后者更坏 | 删不掉就报出来并退出（而不是崩），并提示「有另一次测量在跑」；两个平台用同一条路径 |
| D20 | 版本声明检查<br>`scripts/check-version-claims.py:1569` | `sorted()` 作用在 Path 对象上时，比较用的是**规范化之后**的字符串，而 Windows 的规范化会转小写 | 同一个集合，顺序按小写排（已实测：`A.md`、`b.md`、`C.md`、`d.md`） | 同一个集合，顺序按码点排（`A.md`、`C.md`、`b.md`、`d.md`） | 判定的**集合**相同，但**报出的顺序**不同；树里有 README、AGENTS、CHANGELOG 这类大写名，顺序就会差 | 一律用 `as_posix()` 做排序键（本仓库测量脚本已经这么写） |
| D21 | CI 的覆盖率门禁<br>`.github/workflows/ci.yml:150-153`、`docs/reports/phase1-execution-report.md:77` | CI 用同一道 `--fail-under=80` 门禁量三棵不同的树（全后端 / 无 Java / 只有 Apktool），而报告里那个 93.3% 属于第四棵——Windows、本机、三个后端都在 | 报告里的 93.3% 是本机量出来的 | 三道 job 各自量各自的树，没有一道量的是报告描述的那棵 | 那道 80% 的门禁守的是**阈值**，不是**发布出去的那个数**；CI 里的注释还写着「从 82% 掉到 70%」，与 93.3% 已经差了十一个点 | 在报告里写明 93.3% 是在哪棵树上量的；加一道与报告同配置的覆盖率 job；顺手改掉那条陈旧的注释 |
| D22 | CI 的临时目录<br>`.github/workflows/ci.yml:291-299` | 「把生成物留在 .scratch」这一步**只在六个 job 里的一个**里 | 临时目录由测试自己重定向到项目里，但 `uv sync` 与 `uv run` 发生在重定向之前，仍落在系统盘 | runner 的临时目录就是项目目录 | 本机系统盘已经 97% 满，`uv sync` 有可能因为没空间而失败，而 CI 不会 | 把这一步做成复合动作，给其余五个 job 都加上 |
| D23 | 项目说明与代码<br>`tests/conftest.py:30-35` | 项目说明里写的是「所有产物都在 `G:\dexatlas\.scratch`」，而代码算出来的是「仓库目录下的 .scratch」 | 主 checkout 上两者恰好是同一个目录 | 在工作区里两者是**两个不同的目录** | 说明里那条「系统盘快满了」的告诫是照着一个代码并不使用的路径写的；工作区会在项目盘上长出自己的 .scratch，而那条告诫不适用 | 把说明改成「仓库目录下的 .scratch；在主 checkout 上它是那一个路径」 |
| D24 | 社交预览图<br>`scripts/make-social-preview.py:419-423` | 字体查找目录写死成 Windows 的字体目录；Linux 上没有这个目录 | 能画（用的是本机的微软雅黑） | **画不了**——只有 `--check` 那条路能在 Linux 上跑 | 预览图**只有 Windows 能重画**；而且卡片字节取决于画图那台机器上的字体版本，而 side-car 只记图片的哈希、不记字体的哈希 → 换字体这件事在 `--check` 里完全看不见 | 把字体当资产入库并把它的哈希写进 side-car；或在字体目录里补上 Linux 常见目录并做字体族映射 |
| D25 | 本地环境安装<br>`CLAUDE.md:47` | 项目说明里给的那条安装命令**没有 demo extra**，而 Pillow 在 demo extra 里；CI 的 measurement job 装了 | 按说明装的环境**没有 Pillow** → 画图那条测试被跳过 → 命中 D1 → 刷新变成静默空操作，还打印「报告已经是最新」并退出 0 | measurement job 装了 Pillow | 按项目自己的说明书装环境，就会得到一次「绿色但没测」的刷新，且没有任何提示 | 把安装命令改成带上 demo 与 mcp 两个 extra；并在「缺什么」的提示里**明确点名**「缺 Pillow ⇒ 本次测量只能是部分的」 |
| D26 | 临时候选与 side-car 的换行<br>`scripts/refresh-report-figures.py:518`、`:550`、`:571-572`、`scripts/make-social-preview.py:856` | 这四处用文本模式写文件而没写换行参数，Windows 上会把 LF 翻译成 CRLF | 写出来是 CRLF | 写出来是 LF | 候选报告、候选状态页与 side-car 的**字节**在两个平台上不同；今天无害（读方一律按文本模式读，通用换行会归一），但一旦有检查比对字节或哈希就分叉 | 这四处统一加 `newline="\n"`，让候选字节 = 写盘字节 = Linux 字节 |
| D27 | 覆盖率读回<br>`scripts/refresh-report-figures.py:415-437` | 靠字符串前缀判断某个文件是不是本项目的模块；而相对化路径在**跨盘符**时会失败并退回绝对路径，那样的文件会被静默丢掉 | 多盘符的机器上更容易踩 | 单一盘符，不会踩 | 覆盖率数字静默少一块，而那条「跑出来的模块与树对不上」的提示只打印、不失败 | 改成按解析后的路径判断归属；并把那条提示升级为硬失败 |
| D28 | 测量脚本的前置条件提示<br>`scripts/refresh-report-figures.py:1057-1060` | 判「JADX 在不在」用的是 PATH 查找；而 CI 是用环境变量把后端指给代码的，并没有把它的 bin 目录加进 PATH | 本机装了就在 PATH 里，提示正常 | **CI 上会误报「JADX 缺失」** | 只影响提示不影响判据，但读 CI 日志的人会被误导 | 让这段提示改用与后端本身相同的解析逻辑，而不是 PATH 查找 |

---

## 2. 反向：本地比 CI 更严

这两处的方向与 §1 相反——本地红、CI 绿。同样有害：CI 从来没有验过它们。

### 2.1 D29 三条 Windows-only 的测试在 CI 里整条跳过

- 出处：`tests/test_backend_discovery.py:49`、`tests/test_backend_discovery.py:62`、`tests/test_backend_timeout.py:96`；
  它们守的产品行为在 `src/dexatlas/tools/jadx/adapter.py:209-219`（把 jadx 的启动器换成 Windows 能执行的那一个）。
- **差在哪**：条件是「不是 Windows 就跳过」。Windows 上跑，Linux 上跳过。
- **哪个平台判什么**：本地跑这三条，CI 一条不跑。
- **后果**：CI 从来没有验过「指向 shell 脚本时解析到旁边的 `.bat`」这条行为——而这正是 Windows 用户实际会踩的那条路径。
  这三条也是 D1 里「跳过身份不同」的来源：**修掉它们，D1 的一半就修掉了。**
- **怎么改**：把这三条改成跨平台——测的是「在 Windows 上选 `.bat`、在别处选原文件」这个纯函数，
  于是两个平台都能验同一条规则；或者给 CI 加一个 `windows-latest` 的 job。

### 2.2 D30 M10 自查的输出编码没有钉死

- 出处：`scripts/m10_selfcheck.py:1124-1136`（打印）、对照 `scripts/check-version-claims.py:1604-1621`（同样的问题在那边已经解决了）。
- **差在哪**：版本声明检查在开跑前把 stdout 与 stderr 重配成 UTF-8；M10 自查没有。
  控制台上的中文在两个平台上都没问题（Windows 的控制台用 UTF-8 写），
  但**输出被重定向到文件或管道时，Windows 用 cp936，Linux 用 UTF-8**。
- **哪个平台判什么**：一个只含 GBK 字符的标题在两边都打得出来；
  一旦标题里出现 GBK 之外的字符（破折号以外的排版符号、表情），Windows 上抛 UnicodeEncodeError，
  脚本中途死掉 → **本地红、CI 绿**，而且死在哪一行取决于标题的内容。
- **后果**：它返回的退出码里，1 既表示「有一条检查没过」，也表示「脚本崩了」——这两件事被混成了一件事。
- **怎么改**：照 `check-version-claims` 的做法，在 `main()` 开头把两个流重配成 UTF-8。

---

## 3. 已经处理过的

这些是本轮之前就修好的，列在这里是因为它们正是这类差异的样本，改动时不要把它们改回去。

| 事项 | 出处 | 现在的做法 |
|---|---|---|
| 三个点占位链接 | `tests/test_docs.py:112-137`、`:156-175` | 链接检查**按名字逐段查找**，不做路径规范化；因此三个点构成的占位链接在两个平台上都是断链。回归测试就写在旁边 |
| 测量指纹的换行 | `scripts/refresh-report-figures.py:626-638` | 哈希前先把 CRLF 归一成 LF，所以同一份源码在两个平台上是同一个指纹 |
| 报告写回 | `scripts/refresh-report-figures.py:1480-1484` | 用 `write_bytes` 写回，不经过文本模式的换行翻译 → 两个平台写出同样的字节 |
| 工作区的换行 | `.gitattributes:2` | 全部文本按 LF 检出，两个平台的字节一致 |
| 版本声明检查的输出 | `scripts/check-version-claims.py:1604-1621` | 开跑前把 stdout 与 stderr 重配成 UTF-8，字符写不出去时替换而不是抛错 |
| 引用的文件名大小写 | `scripts/check-doc-citations.py:427-434` | 文件名统一折叠成小写后建索引，所以大小写不一致的引用在两个平台上判得一样 |
| 门禁命令的查找 | `scripts/m10_selfcheck.py:650-669` | venv 的两种目录布局都认（Windows 的 `Scripts` 与 POSIX 的 `bin`）——问题在 PATH 那一支，见 D18 |
| 测量的并发锁 | `scripts/refresh-report-figures.py:395-412` | Windows 用 `msvcrt`、POSIX 用 `fcntl`，两边都是非阻塞：拿不到锁就说拿不到，而不是排队 |
| 社交预览图<br>（CI 那一侧） | `.github/workflows/ci.yml:500-512` | CI 跑的是 `--check`，**只比数字，不比 PNG 的字节**——因为两个平台的字体不同，画出来的图本来就不一样（字体目录那一侧见 D24） |
| Docker 镜像 | `.github/workflows/ci.yml:406-414` | 本地门禁清单里没有这一道，它只在 CI 跑；本机装没装 Docker 都不影响本地门禁的结论 |

---

## 4. 查过、两个平台一致的

| 事项 | 出处 | 为什么一致 |
|---|---|---|
| 字符串排序 | 全仓库 | `sorted()` 作用在字符串上时按 Unicode 码点排，与 locale 无关；**全仓库没有 `locale` / `strcoll` / `setlocale`**。中英混排的顺序在两个平台上相同（Path 对象上的排序是另一回事，见 D20） |
| 集合与字典的迭代顺序 | 全仓库 | Python 3.7 起的插入序，两个平台一致 |
| 目录遍历的顺序 | `tests/test_docs.py:100`、`tests/test_public_contracts.py:837`、`scripts/check-doc-citations.py:430` | `os.walk` 的产出顺序取决于文件系统（NTFS 与 ext4 不同），但这三处要么把结果排序，要么只当集合用 |
| 文件读取的编码 | 全部门禁脚本与测试 | 读文件一律显式写 `encoding="utf-8"`，不落回平台默认 |
| 链接的路径写法 | `scripts/refresh-report-figures.py:600-611` | 路径一律转成 POSIX 形式再比较，路径分隔符不影响指纹 |
| 测试的收集数 | `docs/how-to-verify.md:147` | 树里没有模块级跳过，也没有自定义的收集规则，所以「收集到多少个测试」与平台无关；变的只是它们跑过还是跳过 |
| mypy 对平台分支的收窄 | `src/dexatlas/tools/base.py:346` | mypy 不对 `os.name` 做平台收窄，所以这几个分支在两个平台上都被当作可达（这条与 D8 是两回事） |
| 同一测试在两边的不同机制 | `tests/test_backend_timeout_exit.py:69`、`:164`、`:209` | 这几处按平台走不同的桩，但两边都验到了同一件事：杀不掉时如实说杀不掉 |
| 路径安全判断 | `src/dexatlas/core/paths.py:140-148` | 三个点在两个平台上判得不同（Windows 更严），但**两边都拒绝**，结论一致 |
| 社交预览图的判定<br>（CI 那一侧） | `scripts/make-social-preview.py:434-472` | 字体可用性**有检查**：逐角色查文件在不在，缺了就报错并说清缺什么、去哪找、怎么指定；没有静默回退到默认位图字体。CI 只跑 `--check`、不重画，所以结论必然相同 |
| 版本声明的基线选取 | `scripts/check-version-claims.py:1587-1601` | 选取规则本身与平台无关；差别在**输入**（本地有没有全量历史、origin/main 在不在），那是 D12 说的环境差异，不是逻辑差异 |
| 安装脚本的临时目录 | `scripts/install-backends.sh:22` | `RUNNER_TEMP` 只在 CI 有，本地退回 `/tmp`；两个平台都能建目录，差别只是落在哪 |
| 证明脚本的临时目录 | `scripts/prove-red.sh:26` | 用 `TMPDIR`，Windows 一般没有，于是退回 `/tmp`；Git Bash 下 `/tmp` 会被映射到一个真实目录，能用 |
| 退出码与超时 | `scripts/verify-public-contracts.py:83`、`:91-100` | 超时值与退出码的语义在两个平台相同（差异在**预算够不够**，那是 D3） |
| 契约活检的端口冲突 | `scripts/verify-public-contracts.py:40` | 8977 只被一个进程绑定；CI 的各 job 是各自独立的 runner，m10-selfcheck 那个 job 根本不起服务 → CI 上不可能撞车，撞车只发生在本地同时跑两样东西的时候 |
| 产物里有没有本机路径 | `src/dexatlas/core/paths.py:110-118` | 对外只给文件名，报告与 JSON 里不出现绝对路径，所以临时目录落在哪不影响产物 |
| 浮点与百分比 | `scripts/refresh-report-figures.py:799-801` | 覆盖率是一个除法再按固定格式格式化，两平台逐位一致 |

---

## 5. 建议的落地顺序

按「先堵住会让人以为验过、其实没验的洞」排：

1. **D1 + D29** 一起做：把那三条 Windows-only 的测试改成跨平台，两边的跳过集合就对齐了；
   同时把 `--check` 在不完整时的返回码从 0 改成非 0。**这是唯一一条会让门禁「假装自己验过」的洞。**
2. **D2**：几行改动，把父子进程的编码契约钉死。
3. **D25**：把安装命令补齐 extra —— 否则按项目自己的说明书装环境就会得到一次「绿色但没测」的刷新。
4. **D3 + D4 + D5**：契约活检的三件事——预算、干净的工作区、优雅退出。
5. **D8**：mypy 显式写 platform。
6. **D6 + D21**：在报告里写明覆盖率是在哪个平台上、哪棵树上量的（不必重做测量）。
7. **D9、D10、D11、D12、D13、D14、D22、D23**：本地门禁清单的前置条件与工具版本对齐。
8. **D15、D16、D17、D18、D19、D20、D24、D26、D27、D28、D30**：低成本的写法修正。

---

## 6. 复核方法与可复现的实验

以下实验在 Windows 11 + Python 3.12 上实跑过，脚本写在工作区的 `.scratch/gate-audit/` 下（该目录不入库）。

**实验一：Windows 把三个点规范化成上一级目录**

```python
>>> pathlib.Path("docs/reports/...").resolve()
WindowsPath('E:/Dexatlas/docs/reports')      # 存在 -> 判绿
```

同一个表达式在 Linux 上得到 `docs/reports/...`（不存在 -> 判红）。
注意 `os.path.normpath` 两边都保留三个点——**是 `resolve()` 背后的 Win32 路径规范化把它吃掉的**，
所以只有走 `resolve()` 的代码受影响。

**实验二：mypy 的 platform 取宿主平台**

用同一个探针文件（一个 `sys.platform == "linux"` 分支和一个 `sys.platform == "win32"` 分支）：

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
`m10_selfcheck.py --json` 重定向到文件后产出 15953 字节、589 个 CRLF，且按 UTF-8 解不开。

**实验六：CI 与本地的跳过数**

`docs/reports/v1.0.0-ci-run-record.md:192-196` 记着 tag 那一轮 Linux 上的实跑：
Python 3.12 是 `1612 passed, 5 skipped`，measurement job 是 `passed=1597, skipped=4`；
而本仓库报告里嵌的记录是 `passed=1643, skipped=0`。**同一棵树，两个平台，跳过的身份集合不同。**

---

## 7. 顺带发现：引用检查器只查一份写死的清单

这不属于平台差异，但与本文的主题相邻，所以记在这里。

`scripts/check-doc-citations.py:87-99` 的文档清单是**写死的 13 个文件**；
`tests/test_doc_citations.py` 的那几条测试也用同一份清单。
于是**任何新写的报告里的 `file:line` 出处，不会被任何自动检查覆盖**——
本文自己的 85 条出处就是例子（它们是逐条手工核对的，不是门禁核对的）。
2026-10 那次复核已经踩过同一个坑：一份文档不在清单上，它的出处错了很久没人发现。

**建议**（改动由主会话做）：把新报告加进那份清单。本文被加进清单之前，它的出处只有人能保证。

---

## 8. 本文没有回答的

- **CI 上 11 个 job 并行时的资源竞争**（上一轮 tag run 踩过）不是平台差异，本文只把它记在 D3 里。
- **本机与 runner 的绝对速度**会随负载变化，无法在一次复核里给出稳定的结论；D3 给的是结构性的那一条。
- 本文**没有重跑任何测量**，也没有改动任何既有文件。
