# 本地门禁与 CI 门禁的差异核对（方法）

> 复核日期：2026年11月19日 · 复核方式：**写方法**（本轮改了 `scripts/` 与 `tests/`） ·
> 复核树：`claude/modest-ishizaka-8318ba` @ `415f522`（本文的 `file:line` 锚在这一棵树上，
> 但正文里尽量只写**函数名与文件名**——清单里的行号是会烂的）
>
> **本文只新增报告与配套的清单、脚本、测试**；改了一处既有文档（执行报告的测试文件表加了
> 一行，因为有一条测试要求那张表列全每个测试文件），其余既有文件一行未动。
> 登记与重测留给主会话，见 §7。

## 摘要

- **C15 的缺口是「个案已修，方法未建」**。已修的那个个案是提交 `ec52527`：一条目标写着
  三个点的相对链接，在 Windows 上 `Path(...).resolve()` 把它规范化成「上一级目录」→ 判绿，
  在 Linux 上 `...` 是个普通目录名 → 判红。**本地那道门禁比它代表的那道 CI 门禁更宽松**，
  而这个差只在推上去以后才显形。
- **这一轮又撞了两回同一形状的**：
  1. `tests/test_platform_independent_gates.py` 里那条「每个跑 uv 的 job 都重定向临时目录」
     的测试**把 job 数写死**（9/11 → 10/12，提交 `be76e0f` 改的）——**每加一个 CI job 或改一次
     安装方式，那条测试就红**，而它红的原因与它要守的性质无关；
  2. POSIX launcher 的那条测试**在 Windows 上按设计跳过**——这一类差异是**合法的**，但要有人
     知道它是合法的。
- **本文建的是方法，不是又修一个个案。** 三件东西：
  1. **清单**：[`scripts/platform-gates.json`](../../scripts/platform-gates.json)——
     14 个 CI job、4 条平台相关的测试、3 处平台敏感的脚本行、两组「只在一处跑」的门禁，
     每一条写明**为什么会有差异**、**这个差异是合法还是缺陷**；
  2. **机制**：[`scripts/check-platform-gates.py`](../../scripts/check-platform-gates.py)——
     从树上把事实**推出来**（读 workflow 文本、用 `ast` 读测试套件），与清单逐条对账，
     对不上就退出 1。**它不数任何东西**；
  3. **记录**：本文。
- **方法一上来就查出一处真缺陷**（§3.1）：`contracts-without-jadx` 这个 job 跑的是**活检**
  （`scripts/check-contract-records.py` 自己会跑 `scripts/verify-public-contracts.py`），
  而活检的工作区落在 `tempfile.gettempdir()` 里——**这个 job 没有把临时目录重定向到工作区**，
  它的兄弟 job `contracts` 有。**写死个数的那条测试看不见这件事**：两边的总数对得上，
  检查就是绿的。
- **红→绿已证**（§5）：把旧实现放回去，`tests/test_platform_gate_inventory.py` 的 **10 条
  全红**；放回来就全绿。

---

## 0. 这套方法是什么

### 0.1 三件东西

| | 是什么 | 在哪 | 谁跑它 |
|---|---|---|---|
| **清单** | 每个平台差异是什么、为什么、合法还是缺陷 | `scripts/platform-gates.json` | 人写、机器核 |
| **机制** | 从树上把事实推出来，与清单对账 | `scripts/check-platform-gates.py` | **测试套件**（不是一条要人记得的命令） |
| **记录** | 方法怎么用、现在这个仓库是什么样、还剩什么没说完 | 本文 | 人读 |

三者的分工是：**清单说「差异是合法的」，机制说「你说的和树上的不一样」，记录说「所以呢」**。
只有清单没有机制，它会烂；只有机制没有清单，它只会说「有东西不一样」而不说是什么。

### 0.2 机制守的是性质，不是个数

这一节是整套方法里最要紧的一条，也是这一轮踩得最疼的一条。

旧的那条规则长这样（`tests/test_platform_independent_gates.py`，本轮改之前）：

```python
assert tmp_steps == 10, f"{tmp_steps} jobs redirect their temporary directory"
assert sync_steps == 12, f"{sync_steps} steps install dependencies"
```

**它守的不是它写的那件事。** 它想问的是「每个跑 uv 的 job 都重定向了临时目录」，
问出来的却是「现在有 10 个这样的 job、12 处 uv sync」——**后者是一个要跟着改动一起改的数**。
于是：加一个**做对了**的 CI job → 两个数各 +1 → 测试红 → 修法是改数字。
提交 `be76e0f` 干的就是这件事（9/11 改成 10/12）。

新规则问的是同一个问题，答案是一个**性质**：

- 每个跑 `uv sync` 的 job，要么把临时目录重定向到工作区（claim = `yes`），
- 要么在清单里写明**它为什么不需要**（claim = `exempt`，必须给理由），
- 要么在清单里写明**它需要而没有**（claim = `defect`，必须给修法）。

**加一个正确的 CI job 的代价是清单里多一行**，不是某个文件里的某个数被改一下。
这条性质由 `tests/test_platform_gate_inventory.py::test_adding_a_correct_job_does_not_turn_the_check_red`
钉住（§5）。

### 0.3 机制怎么从树上把事实推出来

不靠数，靠**读**：

| 事实 | 从哪读出来 | 怎么读 |
|---|---|---|
| CI 有哪些 job、跑在哪、装不装依赖、重不重定向临时目录 | `.github/workflows/ci.yml` | **按缩进读文本**（不要 PyYAML：多一个依赖就多一个能坏的东西） |
| 哪些测试的**执行**随平台变 | `tests/**/*.py` | `ast`：找 `pytest.mark.skipif` 里读 `os.name` / `sys.platform` 的条件 |
| 哪些测试的**判据**随平台变 | `tests/**/*.py` | `ast`：函数体里读 `os.name` / `sys.platform` / `platform.system()` |
| 哪些测试把两个平台都断言了 | `tests/**/*.py` | `ast`：`parametrize` 的值里有 `nt` / `posix` / `win32` |
| 哪些**脚本行**随平台变 | `scripts/*.py` | `ast`：模块级与函数级找 `os.name` / `sys.platform` / `tempfile.gettempdir` 等构造 |
| 哪些脚本只在一处跑 | `scripts/`、`.github/workflows/`、`tests/` | 按名字比对 |

**关键在于清单的键不是行号。** 清单里写的是 `scripts/refresh-report-figures.py::try_measurement_slot`
这样的「文件::函数」，不是 `scripts/refresh-report-figures.py:624`——
**清单里的行号是下一次改动就会烂掉的东西**，而烂掉的行号会让检查器报一个假的差异。

---

## 1. 怎么用

### 1.1 加了一个 CI job

1. 在 `.github/workflows/ci.yml` 里加 job；
2. 如果它跑 `uv sync`，给它加上那一步 `Keep generated files in .scratch`；
3. 在 `scripts/platform-gates.json` 的 `ci_jobs` 里加一条：`runs_on`、`gate_scripts`、
   `temp_redirect`（`yes` / `exempt` + 理由 / `defect` + 修法）；
4. 跑 `uv run --no-sync python scripts/check-platform-gates.py`——它会说「这个 job 不在清单里」，
   直到你回答了上面那三个问题。

**它不会**因为你加了一个 job 而说「数不对了」。

### 1.2 加了一个平台相关的测试

1. 测试里出现 `skipif(os.name == "nt")` 之类的条件，**或者**函数体里读了 `os.name`；
2. 在清单的 `platform_tests` 里加一条：节点 id（`tests/xxx.py::test_yyy`）、`kind`
   （`skipped-on` / `branching` / `parameterised`）、`platforms`、`reason`、`verdict`；
3. 检查器会核 `kind` 与 `platforms` 对不对——条件写得能静态推出来时，它推出来的必须和你写的一致。

### 1.3 加了一处平台敏感的行

1. `scripts/` 下的脚本里出现了 `os.name` / `sys.platform` / `tempfile.gettempdir` 之类的构造；
2. 在清单的 `platform_sensitive_code` 里加一条：键是「文件::函数」，值是 `constructs`、
   `reason`、`verdict`；
3. 检查器会核「你写的构造和树上的一样」。

### 1.4 什么时候会红

- 清单与树对不上（多了一个 job、漏了一条测试、一条声明指向了不存在的东西）；
- 一条差异**没有理由**；
- 一条差异被判为**缺陷**却**没有修法**（缺陷没有计划只是气味，不是发现）；
- 一条「只在 CI 跑」的声明**没有 workflow 认领**（这句话会骗人）；
- 一条「只在本地跑」的声明**其实有 workflow 或测试认领**（这句话也会骗人）。

---

## 2. 这个仓库的平台相关门禁（清单）

### 2.1 平台条件的测试（4 条）

`ast` 在 `tests/` 里扫出来的全部结果——**只有 4 条**，两个平台的差就在这里：

| 节点 id | kind | 跑在 | 为什么会有差异 | 判定 |
|---|---|---|---|---|
| `tests/test_backend_timeout.py::test_a_windows_launcher_is_stopped_with_its_work` | skipped-on | Windows | 批处理文件是 Windows 的启动器：超时必须杀掉的那棵进程树（`cmd.exe` + 它的子进程）只有那边有这个形状 | **合法** |
| `tests/test_backend_timeout.py::test_a_posix_launcher_that_spawns_work_is_stopped_with_its_work` | skipped-on | POSIX | 上面那条的 POSIX 等价物（`.sh` 脚本），让「杀掉整棵树」这件事两边都被验到 | **合法** |
| `tests/test_backend_discovery.py::test_the_launcher_choice_is_a_rule_about_the_platform` | parameterised | 两个平台都跑 | 启动器的规则是关于**它说的那个平台**，不是关于它跑在哪：两个平台名在两个平台上都被断言 | **合法**（这一条是**收口**的形状，不是**描述**差别的形状） |
| `tests/test_backend_discovery.py::test_jadx_prefers_the_launcher_this_platform_executes` | branching | 两个平台都跑，但各断言各的 | 「本平台执行的那个启动器才是它偏好的」——**别的平台那一支由上面那条参数化的测试盖住** | **合法**（但两个平台并不互相验对方那一支；上面那条才是补上的） |

**这就是两个平台通过数不一样的那一处**：一条只在本机跑、一条只在 CI 跑。
**它是合法的**，而且现在是**写在清单里的**——下一个人看到两个数不一样时，答案在
`scripts/platform-gates.json` 里，不用去猜。

### 2.2 平台敏感的脚本行（3 处）

| 键 | 读的是什么 | 差在哪 | 判定 |
|---|---|---|---|
| `scripts/refresh-report-figures.py::try_measurement_slot` | `os.name` | 测量的锁在 Windows 上是 `msvcrt`、在别处是 `fcntl`；两边都是**非阻塞**的：拿不到就说拿不到，而不是排队 | 合法 |
| `scripts/verify-public-contracts.py::<module>` | `tempfile.gettempdir()` | 活检的工作区落在**平台的临时目录**里——所以跑它的 CI job 必须重定向 `TMPDIR`（§3.1 就出在这里） | 合法 |
| `scripts/render-demo.py::_posix` | `sys.platform` | Git for Windows 附带的 MSYS bash 认的是 `/g/x` 而不是 `G:\x`，路径只为那个 shell 改写 | 合法（不是门禁，是录 demo 的脚本；列在这里是因为它是 `scripts/` 下唯一**故意**长成 Windows 形状的一个） |

### 2.3 CI 的 job 矩阵（14 个）

`.github/workflows/ci.yml` 里的 job，一共 14 个（`on:` 下面那两个不是 job）：

| job | 装依赖 | 重定向临时目录 | 跑什么 |
|---|---|---|---|
| `lint` | 是 | 是 | ruff / ruff format / mypy / vulture / 版本声明 |
| `test` | 是 | 是 | 全套 pytest + fixture + 后端 |
| `test-partial-backends` | 是 | 是 | 同一套，`DEXATLAS_JADX_PATH` 清空（**少跑的那些是 JADX 依赖的，不是失败**） |
| `desktop` | 否（npm，不是 uv） | 不适用 | 桌面前端的 vitest 单测 + `tsc --noEmit`（`npm run test` / `npm run build`） |
| `m3-comparison` | 是 | 是 | 基准比对 |
| `docker` | 否 | 不适用 | 镜像构建与实跑 |
| `security` | 是 | 是 | `uv export` + `pip-audit` |
| `contracts` | 是 | 是 | 契约活检 + 记录比对 |
| `contracts-without-jadx` | 是 | **否 → 缺陷**（§3.1） | 契约记录比对（**它自己会跑活检**） |
| `m10-selfcheck` | 是 | 是 | M10 自查 + 快照比对 |
| `gate-coverage` | 是 | 豁免（只读脚本，没有临时文件可搬） | 每道门禁都被某处跑着 |
| `social-preview` | 是 | 是 | 卡片上的数字（`--check`，只比数不比字节——两个平台字体不同，图像本来就不同） |
| `measurement` | 是 | 是 | 重测一遍并比对（**只在 tag 上跑**） |
| `release-numbers` | 是 | 是 | 对外文本的发布数字 |

### 2.4 只在一处跑的门禁（覆盖差）

**CI 跑、本地门禁清单里没有的（7 个）**：
`scripts/check-contract-records.py`、`scripts/check-gate-coverage.py`、`scripts/check-m10-snapshot.py`、
`scripts/check-release-numbers.py`、`scripts/fetch-fixtures.sh`、`scripts/install-backends.sh`、
`scripts/make-social-preview.py`。

其中真正要紧的是：**依赖审计与 Docker 镜像这两道门禁在本地没有任何东西代替**
（`security` 与 `docker` 两个 job 跑的是 `pip-audit` 与 `docker build`，不是 `scripts/` 下的脚本）——
本地绿灯不代表它们过。

**两边都不跑、只有人跑的（7 个）**：`scripts/linux-check.sh`、`scripts/prove-red.sh`、
`scripts/remap-citations.py`、`scripts/capture-demo.sh`、`scripts/create-milestone-issues.sh`、
`scripts/fetch-jadx.py`、`scripts/accept-chip.sh`。

**最要紧的一个是 `scripts/linux-check.sh`**：它的开头写着「连续两个缺陷通过了每一个本地测试，
却在 Linux runner 上失败」——**它就是为了这一类问题存在的**，但它是**手工的**、要在 WSL 里跑、
**CI 不调用它**、而且它跑的是**测试套件**而不是每一道门禁脚本。
**换句话说：Linux 那一侧的门禁核对，到今天为止仍然靠一个人记得手动跑它。**（§4.1）

---

## 3. 这一轮查出来的

### 3.1 缺陷：`contracts-without-jadx` 没有重定向临时目录

**这是方法建起来之后才查出来的，不是这一轮读代码读出来的。**

- `contracts-without-jadx` 这个 job 跑的是
  `uv run --no-sync python scripts/check-contract-records.py --expect without-jadx`；
- `scripts/check-contract-records.py` **自己会跑活检**（它的 `run_live_check()` 调起
  `scripts/verify-public-contracts.py`）；
- 活检的工作区在 `scripts/verify-public-contracts.py` 里是
  `Path(tempfile.gettempdir()) / "dexatlas-verify-contracts"`——**平台的临时目录**；
- 它的兄弟 job `contracts` 跑同一个活检，**有**那一步 `Keep generated files in .scratch`；
  这个 job **没有**。

**写死个数的那条测试看不见它**：两个总数（10 / 12）对得上，检查就是绿的。
**性质规则看得见**：这个 job 跑 `uv sync` 却没有重定向临时目录，清单里就得有它的说法——
写清单的时候它就露出来了。

**清单里现在记着它**，记为 `defect`，并写着修法：给这个 job 加上 `contracts` 那一步。
**本窗口没有改 `.github/workflows/ci.yml`**——那个文件不归本窗口（见 §7）。

### 3.2 差异：`lint` job 的 `uv run` 没有 `--no-sync`

CI 的 `lint` job 是 `uv sync --extra dev --extra mcp --frozen` 之后连着几个
`uv run ruff check .` / `uv run mypy` / `uv run vulture ...`，**都没有 `--no-sync`**；
本地门禁清单是 `uv sync --frozen --all-extras` 之后 `uv run --no-sync ...`。

**这曾经被我写成「CI 装的环境里没有 mcp extra」——那是我猜的，实测不是。**
在 `.scratch/` 下造了一个最小工程实测（uv 0.11.21）：`uv sync --extra dev` 之后，
不带 `--no-sync` 的 `uv run` **不会**把那个 extra 的包卸掉。**装出来的集合是一样的。**

真正的差是：**CI 那几个命令每一步都会让 uv 重新解析并同步一次环境**（因而可能重写 lockfile），
本地那几条不会。这条差异记在清单的 `lint` 条目里——**它不是平台差异，是环境差异，
但属于同一张表**（同一道门禁在两个地方不是一模一样地跑）。

### 3.3 个案：写死个数的那条测试本身就是缺陷（已修）

提交 `be76e0f` 给 `tests/test_platform_independent_gates.py` 里的那条测试改了数字
（9/11 → 10/12），因为多了一个 CI job。**那条测试问的问题和它守的性质无关**，
所以它红的每一次都是一次误报，而每一次误报的修法都是「改数字」。

本轮把它改成守性质（§0.2），并把「新增一个正确的 job 不该让检查变红」钉成了一条测试。

### 3.4 已修的个案（C15 原本要记进表的那一条）

提交 `ec52527`：**CI 红了、本地绿的**那个根因。
一条相对链接的目标是三个点（`docs/reports/outreach-first-read.md:199`），
Windows 的 `Path(...).resolve()` 把它规范化成「上一级目录」→ 判绿；
Linux 上 `...` 是个普通目录名 → 判红。
修法是把链接检查改成**按路径分量逐个查名字**，并加了一条判据：
**占位目标在任何一个平台上都必须判红**。

**这一条是「方法要建」的由来**：修好的是这一条链接，没有建的是「同一道门禁在两个平台上
判得不一样」的核对。本文是那个核对。

---

## 4. 还剩哪些差异没人说得清

### 4.1 Linux 那一侧：**未实测**

- 本机是 **Windows**。本报告里所有「Linux 会怎样」的判断，都是**读代码得出的**，
  不是**跑出来的**。
- **Linux 那一侧能拿到的依据**只有两样：`docs/reports/local-vs-ci-gates.md`（2026年11月18日
  的只读复核，逐条给了两个平台各判什么，锚在树 `9e1aa61` 上）与
  `docs/reports/v1.0.0-ci-run-record.md`（v1.0.0 那次 CI 实跑的记录）。
- **拿不到 Linux 输出**：本机没有 Linux 环境，`scripts/linux-check.sh` 要在 WSL 里手工跑，
  本轮没有跑。**所以「Linux 那侧的收集数与跳过数」在本报告里是空缺，不是数字。**
- 清单里与平台有关的 4 条测试，其平台归属是**从条件静态推出来的**（`os.name == "nt"`
  → 只在 POSIX 跑），这一点在两个平台上都成立，不需要实跑。

### 4.2 两个平台的通过数差：能解释一部分，不能解释全部

- **能解释的**：§2.1 那 4 条 —— 一条只在 Windows 跑、一条只在 POSIX 跑，
  所以两个平台**执行的集合**差 2 条，**收集的集合**相同。
- **不能解释的**：任务里提到的那两个数（本机 1689 / CI 1694，差 5）**在这棵树上复现不出来**——
  本机实测收集到 **1733** 条（改本轮之前；改之后 1743 条），而「1689 / 1694」这两个数
  **在仓库的文档里找不到**（`docs/reports/` 里出现的 1694 是**测量**的 passed 数，
  指的是另一件事）。
- **诚实的说法**：一个平台的通过数比另一个少，少掉的那几条里，
  **平台条件的只有 2 条**（可静态判定）；**其余的差来自环境**——后端装没装、fixture 取没取到、
  `install-backends.sh` 在两个平台装出来的东西不一样。**这一类差不是「平台差异」，
  但它同样会让两个平台给出不同的答案**，同样没人系统地核过。
  **这是本方法下一步该覆盖的地方**（§4.3）。

### 4.3 环境差异不是平台差异，但它同样会让两个平台判得不一样

本轮把这一类**明确划到了范围外**：平台差异指「同一个输入，两个平台给出不同的**判据**」。
而「这台机器上少装了一个后端，所以少了 92 条测试」是**配置差异**——
`test-partial-backends` 这个 job 就是为它存在的（**它跑同一套测试，只是把 JADX 清空**）。

**划到范围外不等于它不重要**：CI 的 `test` 与 `test-partial-backends` 两个 job 之间的差，
就是「环境差异」的一个可测样本。清单里记了这一条。

### 4.4 `scripts/linux-check.sh` 仍然只在本地、仍然靠人记得

它跑的是**测试套件**，不是**每一道门禁脚本**；CI 不调用它。
**本方法补上的正是它没补的那一半**：门禁**脚本**在两个平台上的判据差异，现在有清单和机制了；
**测试套件**在两个平台上的差异，仍然靠那一条手工脚本。

---

## 5. 红→绿

**规则 1 的要求**：修 bug 要带一条**在旧实现下会红**的回归测试。

**这次的「修」是什么**：把「同一道门禁在两个平台上判得不一样」这一类问题，从
「一个个案地修」变成「一套方法」；被替换掉的旧实现是
`tests/test_platform_independent_gates.py` 里那条**写死个数**的规则，
加上**不存在**的清单与核对脚本。

**做法**（与 `scripts/prove-red.sh` 同形：把修复前的树放回去，看着新测试变红）：

1. 把 `scripts/check-platform-gates.py`、`scripts/platform-gates.json`、
   `tests/test_platform_gate_inventory.py` 移走；
2. 把 `tests/test_platform_independent_gates.py` 恢复成写死个数的旧版本
   （`git checkout --`）；
3. 跑新测试；
4. 放回来，再跑一次。

**红的那一次**：

```
$ uv run --no-sync pytest tests/test_platform_gate_inventory.py -q
FAILED tests/test_platform_gate_inventory.py::test_the_platform_gate_checker_exists
FAILED tests/test_platform_gate_inventory.py::test_every_difference_the_tree_has_is_accounted_for
FAILED tests/test_platform_gate_inventory.py::test_the_known_platform_differences_are_listed_as_they_are
FAILED tests/test_platform_gate_inventory.py::test_a_declared_difference_without_a_reason_is_found
FAILED tests/test_platform_gate_inventory.py::test_a_defect_without_a_plan_is_found
FAILED tests/test_platform_gate_inventory.py::test_a_job_that_installs_without_the_redirect_is_found
FAILED tests/test_platform_gate_inventory.py::test_adding_a_correct_job_does_not_turn_the_check_red
FAILED tests/test_platform_gate_inventory.py::test_a_platform_conditional_test_that_is_not_declared_is_found
FAILED tests/test_platform_gate_inventory.py::test_a_declared_test_that_is_gone_is_found
FAILED tests/test_platform_gate_inventory.py::test_a_claim_about_a_script_that_no_workflow_runs_is_found
10 failed in 0.16s
```

**绿的那一次**：`45 passed`（新文件 10 条 + 改写后的 `test_platform_independent_gates.py` 35 条）。

**另外一层红→绿**（性质对数字）：旧规则在同一棵树上问的是两个总数。
加一个**完全正确**的新 job（装了依赖、重定向了临时目录）：

```
旧规则：tmp_steps = 11（期望 10）、sync_steps = 13（期望 12） → 红，而新 job 什么也没做错
新规则：清单里多写一条 → 绿
```

这条对比被 `tests/test_platform_gate_inventory.py::test_adding_a_correct_job_does_not_turn_the_check_red`
钉着。

---

## 6. 哪些数字需要重测后同步

**本轮改了 `tests/` 与 `scripts/`，而这两处在源码指纹的覆盖范围内** →
**报告里的数字全部过期**。按规矩**没有跑** `scripts/refresh-report-figures.py`
（那是主会话合入后统一做的事；并发跑会互相污染覆盖率），也**没有手改任何数**。

### 6.1 本轮改动导致过期、且只有重测能修的

| 数 | 现在写的是什么 | 改完之后应当是 | 谁改 |
|---|---|---|---|
| 测试总数 | **1733**（`docs/how-to-verify.md:147`、`:153`、`:154`；`docs/how-to-verify.zh-CN.md:120`、`:126`、`:127`；`docs/reports/phase1-execution-report.md` §2.1 的 `<!--fig:tests.total-->`） | **1743**（本轮新增 10 条测试；本机 `pytest --collect-only` 实测：1743 条，其中慢测 149 条） | **主会话重测时由脚本写** |
| 快测条数 | **1584**（同上两页的散文里） | **1594**（新增的 10 条都是快测） | 同上 |
| 集成条数 | 149 | 149（不变） | 同上 |
| 覆盖率 | 执行报告与 README 徽章里的那一族 | 随上面一起变 | 同上 |
| 源码指纹 | 报告里记的那一串 `sha256:` | `tests/`、`scripts/` 变了 → 指纹变了 | 同上 |

**本机实测（未取 fixture、未装后端）**：`pytest --collect-only -q` → **1743**；
`-m "not slow"` → **1594**；`-m slow` → **149**。

### 6.2 因此变红的测试（**要等重测，不是缺陷**）

| 测试 | 为什么红 |
|---|---|
| `tests/test_docs.py::test_execution_report_numbers_match_the_code` | 执行报告里的测试数是 1733，现在是 1743 |
| `tests/test_docs.py::test_execution_report_suite_figures_add_up_to_the_tests_that_exist` | 同上 |
| `tests/test_how_to_verify.py`（6 条） | 两页「怎么复核」里写着的收集数是 1584/1733 |

**这 8 条在重测之后会自己变绿**——它们守的正是「文档里的数与套件真打出来的一样」，
而数还没重测。

### 6.3 本轮**之前**就在红的（**不是本轮造成的**）

把本轮的新测试文件移走、其余改动保留，重跑得到：

| 测试 | 为什么红 | 归谁 |
|---|---|---|
| `tests/test_docs.py::test_all_relative_links_resolve` | `docs/reports/m10-material-fixes.md` 里的相对链接指向的行号在别的文件里对不上（该文件是**另一扇窗口**在动的） | 另一扇窗口 / 主会话 |
| `tests/test_docs.py::test_execution_report_coverage_figures_describe_the_current_code` | 覆盖率那一族数在这棵树上已经过期（**与本轮无关**：移走本轮的新测试文件后它照样红） | 主会话重测 |

**本轮自己造成的只有 §6.2 那 8 条**，且它们的成因是**数字过期**，不是判据错了。

### 6.4 本轮自己同步的

**一个数都没有**。

**执行报告 §2.1 的测试文件表加了一行**（`test_platform_gate_inventory.py`）——
那不是数字，是一张表，有一条测试（`tests/test_docs.py`）要求它列全每个测试文件；
`scripts/check-doc-citations.py` 跑下来 `drifted: 0`。

---

## 7. 本窗口做的 / 留给主会话的

### 7.1 本窗口做的

| 文件 | 是什么 | 新增/改动 |
|---|---|---|
| `scripts/platform-gates.json` | 清单：14 个 CI job、4 条平台相关的测试、3 处平台敏感的行、两组覆盖差、8 条本地门禁 | **新增** |
| `scripts/check-platform-gates.py` | 机制：从树上把事实推出来，与清单对账 | **新增** |
| `tests/test_platform_gate_inventory.py` | 回归测试：10 条，含红→绿的那条 | **新增** |
| `tests/test_platform_independent_gates.py` | 那条写死个数的规则改成守性质 | **改**（只改那一条测试 + 三个常量） |
| `scripts/check-gate-coverage.py` | 门禁登记表里加一行（新脚本是一道门禁，不登记 `gate-coverage` 这个 job 会红） | **改**（一行） |
| `docs/reports/phase1-execution-report.md` | §2.1 的测试文件表加一行 | **改**（一行） |
| `docs/reports/platform-gate-inventory.md` | 本文 | **新增** |

**没有动**：`.github/workflows/ci.yml`、`docs/reports/v1.1.0-candidates.md`、
`docs/reports/m10-*.md`、`docs/reports/README.md`、`scripts/check-doc-citations.py`、
`scripts/refresh-report-figures.py`。

### 7.2 留给主会话的

1. **登记**（按本仓库的规矩，本窗口不自己登记）：
   - `docs/reports/README.md` 的索引与份数（新增一行 + 份数重算）；
   - `scripts/check-doc-citations.py` 的 `DOCS` 名单（新增
     `docs/reports/platform-gate-inventory.md`——**一份没人检查的引用就是一份没人有义务保持为真的引用**）；
   - `docs/reports/v1.1.0-candidates.md` 里 **C15 的状态**（本窗口**没有改**那个文件：
     它是另一扇窗口在动的；本窗口只把方法建起来了，状态怎么写由主会话定）。
2. **修 §3.1 那个缺陷**：给 `.github/workflows/ci.yml` 的 `contracts-without-jadx` job
   加上 `contracts` 那一步 `Keep generated files in .scratch`。**那个文件本窗口没有动。**
   清单里那条 `defect` 记着修法；修完把清单里的 `temp_redirect` 改成 `yes`、
   `verdict` 改成合法。
3. **重测一轮**：§6 那张表。`tests/` 与 `scripts/` 都变了 → 指纹变了 →
   报告里的数字全部要重测后同步。**本窗口没有跑 `refresh-report-figures.py`。**
4. **发版清单 §8.2 的盲区表多一行**：「本地门禁与 CI 门禁的判据差异」。
   C15 的原始交付物里有这一条，但 `docs/reports/v1.0.0-release-checklist.md`
   **不归本窗口**，所以没动。
5. **要不要把核对脚本也接进 CI**：本窗口把它接进了**测试套件**
   （`tests/test_platform_gate_inventory.py` 会跑它），所以它跟着 `test` job 跑。
   如果要一个独立的 job，那是 `ci.yml` 的事——**本窗口没加**（加了 job 就要改
   §2.3 那张表，而那张表在 `.github/workflows/ci.yml` 那边）。

### 7.3 留给下一轮的三件事（不在本轮的范围里）

1. **把门禁脚本的判据也接进 `linux-check.sh`**：它现在跑的是**测试套件**，
   不是**每一道门禁脚本**。本方法补的是「清单 + 机制」，缺的是「Linux 那一侧也跑一遍机制」。
2. **把「环境差异」也纳进来**：§4.2 里那一类——两个平台通过数差的那几条，
   差的不是平台而是**装了什么**。机制已经有了（`test-partial-backends` 那个 job 就是样本），
   但**没有清单**。
3. **Linux 那一侧的实测**（§4.1）：本报告里所有关于 Linux 的判断都是读代码得来的。
   哪一天 `linux-check.sh` 在 CI 里被调起来（或者有人手工跑一遍并把结果贴进清单），
   这一节就能从「未实测」变成「实测」。
