# Docker 镜像里到底能不能跑仓库自带的案例（C6 调研）

> 调研日期：2026年11月18日。对象：候选清单 [C6](v1.1.0-candidates.md#L679)。
> 本轮**只做调研与建议，没有改动任何既有文件**：`Dockerfile`、CI 配置、`examples/` 一律未动。
> 复核工作树：`E:\Dexatlas\.claude\worktrees\gracious-perlman-8560f2`（分支 `claude/gracious-perlman-8560f2`）。
>
> **后续（2026年11月18日，本文写完当天）**：本文的**方案 A 已经落地**——
> `Dockerfile` 末尾加了 `COPY examples/ examples/`，CI 的 `docker` job 什么都不挂就在镜像里
> 实跑了一次分析（过程与边界见 [docker-image-samples.md](docker-image-samples.md)）。
> **构建时间的新口径也已经测出来**：CI runner 上 `docker build` 这一步实测 **46 秒**
> （run `44334171465` 的 `Build image` 步骤），**唯一落点**是
> [c6-build-time-from-ci.md](c6-build-time-from-ci.md)。
> 本文下面出现的「18–20 分钟机时」「1099 秒」是**调研当时的成本估计**与
> **读者本机冷缓存、走代理下载时**的实测——它们测的是**读者本机那一段**，仍然成立，
> 但**不再是最新的口径**：新口径测的是 CI runner，别处一律指向
> [c6-build-time-from-ci.md](c6-build-time-from-ci.md)。

## 0. 结论先说

1. **事实成立**：镜像里确实没有 `examples/`——`Dockerfile` 只 COPY 了四样文件加 `src/`
   （[Dockerfile:32-37](../../Dockerfile#L32)）。今天在镜像里跑仓库自带案例**只能挂卷**，
   唯一一条被验证跑通的命令写在 [m10-reader-package.md:164-166](m10-reader-package.md#L164)。
2. **但 C6 的前提只对了一半**：本项目**没有发布预构建镜像**——`.github/workflows/` 下只有
   `ci.yml` 一个文件，其 docker 段只有 build 与 run 两步（[ci.yml:436-444](../../.github/workflows/ci.yml#L436)）；
   README 给的也是 `docker build`（[README.md:362](../../README.md#L362)）。所以今天"客户拉了镜像"
   = 客户 clone 仓库后本地构建，**客户手上本来就有 `examples/`**。真正缺的不是样本本身，
   而是**一条不用挂卷的命令**，以及**一个能证明"镜像里能跑案例"的验证**。
3. **建议：值得现在就做**——`Dockerfile` 加一行 `COPY examples/ examples/`（实测约 44 KB），
   CI 的 docker job 加一步在镜像内跑通 demo 案例（相对路径，不受 Git Bash 路径改写影响），
   `docs/install.md` 的 Docker 段补上这条命令。唯一昂贵项是**复测构建时间**
   （调研当时按冷缓存口径估约 18–20 分钟机时），且要把新口径写回 7 处引用。
   若本轮不安排镜像重建，则退一步先做"写进说明"的最小版。
   **（这一条后来做了——新口径见开头的「后续」与 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)）**

## 1. 核到的事实

### 1.1 镜像里装了什么、没装什么

**装了**

| 内容 | 出处 |
|---|---|
| `python:3.12-slim` 基础镜像 | [Dockerfile:3](../../Dockerfile#L3) |
| `ca-certificates` / `curl` / `unzip` / `openjdk-21-jre-headless` | [Dockerfile:14-20](../../Dockerfile#L14) |
| `uv` | [Dockerfile:22](../../Dockerfile#L22) |
| 项目：`pyproject.toml uv.lock README.md LICENSE` + `src/`（分两层 COPY） | [Dockerfile:32-37](../../Dockerfile#L32) |
| JADX 1.5.2（构建期解包并 `test -x` 验证） | [Dockerfile:46](../../Dockerfile#L46)、[Dockerfile:51-57](../../Dockerfile#L51) |
| Apktool 2.11.1（构建期 `java -jar … --version` 验证） | [Dockerfile:47](../../Dockerfile#L47)、[Dockerfile:59-61](../../Dockerfile#L59) |
| `DEXATLAS_JADX_PATH` / `DEXATLAS_APKTOOL_JAR` / `PATH` | [Dockerfile:39-41](../../Dockerfile#L39) |
| `DEXATLAS_WORKSPACE=/workspace` | [Dockerfile:10](../../Dockerfile#L10) |
| `WORKDIR /app`、`VOLUME /workspace`、`EXPOSE 8000`、`CMD uvicorn …` | [Dockerfile:24](../../Dockerfile#L24)、[Dockerfile:63](../../Dockerfile#L63)、[Dockerfile:65](../../Dockerfile#L65)、[Dockerfile:70](../../Dockerfile#L70) |

`Dockerfile` 里**没有 `ENTRYPOINT`**（全文 grep 无此指令）→ `docker run <image> <cmd>` 直接替换 `CMD`，
所以 `docker run --rm dexatlas dexatlas analyze …` 这种写法成立。

**没装**

- `examples/`——第一方样本（smali 源码 + 已构建 APK）**不在镜像里**。
- `fixtures/`——本来就不在仓库里：仓库只带说明（[fixtures/apk/SOURCES.md:1-4](../../fixtures/apk/SOURCES.md#L1)），
  第三方样本由 `scripts/fetch-fixtures.sh` 按需拉取。
- `scripts/`、`tests/`、`docs/`。
- 仓库**没有 `.dockerignore`** → 构建上下文是整个工作树（含 `.git`）。

**补充一个容易读错的点**：README 说"A demo application is bundled, so there is nothing to download"
（[README.md:365](../../README.md#L365)），指的是**仓库自带**（clone 下来就有），
不是**安装产物自带**。wheel 只装 `src/dexatlas`（[pyproject.toml:149-150](../../pyproject.toml#L149)），
`src/` 下没有任何 `.apk`（实测 find 为空）→ 镜像里同样没有样本。

### 1.2 镜像实际能跑什么

> **核实边界（务必先读）**：本机 `docker images` 里**没有** `dexatlas:*` 镜像；构建镜像必须联网从 GitHub
> 下载 JADX 与 Apktool（[Dockerfile:51-61](../../Dockerfile#L51)），而本轮既不联网也不构建镜像。
> **因此镜像内部没有实跑。** 下面"镜像里会怎样"是由 `Dockerfile` + **同版本 CLI 的实测行为**推导的。
> CLI 实测用主检出的 venv（`E:\Dexatlas\.venv`），但用 `PYTHONPATH` 把源码指向本工作树的 `src/`
> （`git diff main -- src/` 为空，两边源码相同），工作区指向本工作树的 `.scratch/`。

**CLI 能力面（实测 `dexatlas --help`）**：13 个子命令——`analyze` `backends` `classes` `export`
`manifest` `methods` `projects` `resources` `resrefs` `search` `source` `version` `xrefs`。
镜像与宿主是同一套 CLI，差别只在后端（镜像里三个后端都在）。

**在当前镜像里跑案例会发生什么**：`analyze` 的 APK 参数声明为 `exists=True`
（[src/dexatlas/cli/main.py:323](../../src/dexatlas/cli/main.py#L323)），路径不存在时 Typer 报用法错误：

```text
Usage: dexatlas analyze [OPTIONS] {apk}
Try 'dexatlas analyze --help' for help.
┌─ Error ─────────────────────────────────────────────────────────────────────┐
│ Invalid value for 'apk': Path '…/app/examples/demo-app/demo.apk' does not exist. │
└─ Error ─────────────────────────────────────────────────────────────────────┘
退出码 2
```

退出码 2 在本项目语义里是 `EXIT_BAD_REQUEST`（[src/dexatlas/cli/main.py:94](../../src/dexatlas/cli/main.py#L94)）：
"请求本身错了：没有这个项目，或输入不是 APK"（[public-contracts.md:41-46](../../docs/architecture/public-contracts.md#L41)）。
**读者不会看到"样本不在镜像里"这句话，只看到一个用法错误。**

**样本可达时，案例全流程是通的**（宿主实测，androguard 单后端降级）：

| 命令 | 结果 |
|---|---|
| `dexatlas analyze examples/demo-app/demo.apk -o report.md --json report.json` | 退出码 0，2.6 s，**4 classes / 8 methods / 23 call sites / 21 call edges / 0 resource strings**，Markdown + JSON 报告落盘 |
| `dexatlas projects` | 列出 `apk_80a8fe0e81204c9f`（`completed`，4 classes / 8 methods） |
| `dexatlas export apk_80a8fe0e81204c9f -o evidence.zip` | 退出码 0，**4 files: 3 reports + 1 manifest** |

降级说明：本机 `dexatlas backends` 实测为 jadx `not installed`、apktool `not installed`、
androguard 4.1.4 `available`，所以 classes 5→4、resource strings 1→0——与材料里的 A6 预告一致
（[m10-reader-package.md:143-145](m10-reader-package.md#L143)）。镜像里三个后端都在
（实走演练记录：jadx 1.5.2 / apktool 2.11.1 / androguard 4.1.4，[reader-dry-run.md:72](reader-dry-run.md#L72)），
计数应为 5/8/23/21/1。

**Git Bash 的路径改写（用现成的 `alpine:latest` 实测，与本项目无关，只测 shell 行为）**：

| 传给容器的参数 | 容器里实际收到 |
|---|---|
| `/app/examples/demo-app/demo.apk` | `C:/Program Files/Git/app/examples/demo-app/demo.apk`（**被改写**） |
| `examples/demo-app/demo.apk` | **原样** |
| `MSYS_NO_PATHCONV=1` + 绝对路径 | 原样 |

这条对两个方案都关键：**绝对路径 + Git Bash 会把容器路径改写成 Windows 路径**（准备包已经踩过并写进了
[m10-reader-package.md:169-171](m10-reader-package.md#L169)）；而**相对路径不受影响**。
镜像 `WORKDIR` 是 `/app`（[Dockerfile:24](../../Dockerfile#L24)），所以样本若在镜像内的 `/app/examples`，
`analyze examples/demo-app/demo.apk` 这条**相对路径**命令在 Git Bash / PowerShell / CMD 上都干净。

### 1.3 `examples/` 的构成与构建依赖

- **五个**第一方样本，不是三个：`demo-app` / `multidex-app` / `obfuscated-app` / `strings-app` / `wide-app`
  （安装文档同样列五个，[install.md:161-163](../../docs/install.md#L161)）。三个案例研究跑在其中三个上
  （`demo-app`、`obfuscated-app`、`multidex-app`，[install.md:164-167](../../docs/install.md#L164)）。
- 每个样本目录里都有 **smali 源码 + 已构建好的 APK**；APK 是 git 追踪的
  （`git ls-files examples` 列出 `demo.apk`/`multidex.apk`/`obfuscated.apk`/`strings.apk`/`wide.apk`），
  `.gitignore` 为它们专门开了第一方例外（[.gitignore:52-63](../../.gitignore#L52)）。
- 体积（实测字节）：`demo.apk` 2951 B、`multidex.apk` 2350 B、`obfuscated.apk` 1892 B、
  `strings.apk` 1547 B、`wide.apk` 1440 B；整个 `examples/` = **43,995 B ≈ 44 KB**（含两个 Python 客户端示例）。
- APK 内容（实测 zip 结构）：都含 `AndroidManifest.xml` + `classes.dex`；`multidex.apk` 额外含
  `classes2.dex`（两个 dex）——正是多 DEX 那条路径需要的输入。
- 构建脚本：`scripts/build-demo-apk.sh`（只构建 demo，转交给下面那个）与 `scripts/build-test-apks.sh`
  （构建全部五个）。两者都**只要求 Apktool + JDK 21+**
  （[scripts/build-demo-apk.sh:8](../../scripts/build-demo-apk.sh#L8)、[scripts/build-test-apks.sh:10](../../scripts/build-test-apks.sh#L10)），
  **不需要 Android SDK / aapt2 / Gradle**。也就是说：镜像里理论上也能重建（它有 java 与 apktool.jar），
  但**没必要**——APK 已经提交在仓库里，直接 COPY 即可。

### 1.4 CI 的 docker job 现在验什么

[ci.yml:436-444](../../.github/workflows/ci.yml#L436)：

```yaml
docker:
  name: Docker image builds
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Build image
      run: docker build -t dexatlas:ci .
    - name: Verify the backends in the image actually run
      run: docker run --rm dexatlas:ci dexatlas backends
```

**只验后端在镜像里能跑**，不验"镜像里能跑案例"，也没有任何针对 `examples/` 是否进镜像的断言。

### 1.5 材料现状（谁已经写了、谁没写）

| 位置 | 现状 |
|---|---|
| [m10-reader-package.md:160-171](m10-reader-package.md#L160) | 已明确写"镜像里没有 `examples/`"，给出两卷挂载命令 + Git Bash 坑 |
| [m10-acceptance-pack.md:250-251](m10-acceptance-pack.md#L250) | 只有构建时间口径，**没有**容器内分析命令 |
| [docs/install.md:50-82](../../docs/install.md#L50) | Docker 段只有 build / backends / 起 API 三条命令，**没有**容器内分析命令 |
| [docs/install.md:159-172](../../docs/install.md#L159) | 五个样本 + `uv run` 用法（宿主路线），不是容器路线 |
| [reader-dry-run.md:72](reader-dry-run.md#L72) | 已记录："镜像里**没有 `examples/`**……材料 §3.2 路线 B 只给到 `backends` 检查，**没告诉读者怎么在容器里分析 APK**——读者得自己想出两个挂载才能跑出案例" |
| [reader-dry-run.md:143](reader-dry-run.md#L143) | 已给出补法（把实测过的挂载命令补进材料） |

→ **C6 判据 (b) 要求的"准备包与安装文档两处逐字一致"今天不成立**：准备包有命令，install.md 根本没有。
这正是"照材料走会卡住"的那一处。

## 2. 三个候选改法

### 方案 A：把 `examples/` 装进镜像

**要改什么**

1. `Dockerfile` 加一行 `COPY examples/ examples/`。**位置很重要**：放在**最后一次 `uv sync` 之后**
   （[Dockerfile:37](../../Dockerfile#L37) 之后），否则会作废依赖层缓存，把构建从"层已就绪 2 分 16 秒"
   打回冷缓存口径。COPY 的相对路径以 `WORKDIR`（`/app`）为基准 → 落在 `/app/examples`。
2. CI 的 docker job 加一步：在镜像里跑通一个案例并断言退出码 0
   （`docker run --rm dexatlas:ci dexatlas analyze examples/demo-app/demo.apk`，相对路径）。
   这才是 C6 判据 (a) 的落地——**让"镜像里能跑案例"成为被 CI 验证过的事实**。
3. `docs/install.md` 的 Docker 段补一条命令。
4. 复测构建时间（新口径），并把新数字写回所有引用旧口径的地方：
   [m8-install-rehearsal.md:15](m8-install-rehearsal.md#L15)、[reader-dry-run.md:72](reader-dry-run.md#L72)、
   [reader-dry-run.md:117](reader-dry-run.md#L117)、[m10-reader-package.md:154-155](m10-reader-package.md#L154)、
   [m10-acceptance-pack.md:250-251](m10-acceptance-pack.md#L250)、[m10-acceptance-pack.md:336](m10-acceptance-pack.md#L336)、
   [m10-materials-alignment.md:129](m10-materials-alignment.md#L129)（G5）与 [m10-materials-alignment.md:268](m10-materials-alignment.md#L268)、
   [m10-reader-walkthrough-4th.md:259-260](m10-reader-walkthrough-4th.md#L259)。
   **（已做。新口径在 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)；写回时**只改口径陈述**——
   [m8-install-rehearsal.md](m8-install-rehearsal.md)、[reader-dry-run.md](reader-dry-run.md)、
   [m10-reader-walkthrough-4th.md](m10-reader-walkthrough-4th.md) 这三份是**测量记录**，
   记的是当时某台机器上发生过什么，把数换掉就是篡改记录，不改。）**

**代价**

- 镜像 +44 KB（相对"约 1.3 GB"可忽略）；构建多一个 COPY 层。
- 复测构建时间：调研当时估的是冷缓存口径一次约 18 分 19 秒（1099 秒，[reader-dry-run.md:117](reader-dry-run.md#L117)）
  + 层缓存口径一次约 2 分 16 秒（[m8-install-rehearsal.md:15](m8-install-rehearsal.md#L15)），外加写回 7 处。
  **实际没有付这 20 分钟机时**：新口径改由 CI 实测（**CI runner 上 `docker build` 这一步 46 秒**，
  见 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)）。
- CI 每个 docker job 多一次容器内分析（秒级；实走演练记录容器内分析约 8 秒）。

**风险**

- 读者若仍按老材料挂 `-v $(pwd)/examples:/app/examples:ro`，会**遮蔽**镜像里的副本——同内容，无害，
  但材料里要写清"不用挂了"。
- 样本改动后必须重建镜像才能看到新样本；材料里要说明这一点（否则读者会以为镜像里的样本总是最新的）。
- 分发二进制：镜像是本地构建产物，不是发布物；这五个 APK 是第一方、单个 3 KB 以内，与 CLAUDE.md 规则 7
  和 `.gitignore:52-63` 的口径一致。即便将来发布预构建镜像，随镜像分发仍在许可范围内。
- **最大的风险是"只改 Dockerfile、不加 CI 断言"**——那只是把一条没人验证的承诺换成了另一条没人验证的承诺。

### 方案 B：只改说明（"镜像不含样本，必须挂两个卷"）

**要改什么**：把容器内分析的命令写进安装文档，并让准备包与 install.md **逐字一致**（C6 判据 (b)）。

- 现状下 install.md 的 Docker 段（[install.md:50-82](../../docs/install.md#L50)）**完全没有**容器内分析命令。
- 需要补的就是 [m10-reader-package.md:164-166](m10-reader-package.md#L164) 那三行命令，加
  [m10-reader-package.md:169-171](m10-reader-package.md#L169) 的 MSYS 说明，逐字搬进 install.md。

**代价**：零构建改动、零复测、零镜像风险；半天内可完成。

**风险**

- **读者仍要理解两个卷、一个宿主工作区目录、一个 Git Bash 陷阱**——这是这个方案保留的全部摩擦。
- 口径分散：同一段命令出现在准备包与安装文档两处，改一处忘一处就又漂了。C6 判据说"可以 diff"，
  但**没有门禁强制**；若把这段命令收敛到一个脚本、让两份文档都引用它，摩擦才真正归零。
- 只在"读者手上有仓库 clone"的前提下成立——今天成立（没有发布镜像）；将来若发布预构建镜像，
  这段说明会立刻过期。

### 方案 C：只把 5 个已构建 APK 装进镜像（不带 smali 源码）

**要改什么**：`COPY examples/*/*.apk /app/examples/`（约 10 KB），不带 smali 源码。

**代价**：镜像增量最小。

**风险**

- 镜像里只剩二进制，"每个类都有对应 smali"的可核对性没了——而这正是本项目把样本放进仓库的理由
  （`scripts/build-test-apks.sh` 开头自述：样本是"not a mystery binary"）。
- 它是方案 A 的真子集，单独用没有好处。
- **结论：不单独采用**；若走 A，就整个 `examples/` 一起进镜像。

## 3. 结论与建议

**结论**

1. C6 的事实前提成立：当前镜像跑仓库自带案例必须挂两个卷，唯一一条被验证跑通的命令见
   [m10-reader-package.md:164-166](m10-reader-package.md#L164)。
2. 但"客户拉了镜像也跑不了案例"的说法要修正：本项目不发布预构建镜像，"拉镜像"= clone 后本地 build，
   客户手上本来就有样本。缺的是**不用挂卷的命令**与**对"镜像里能跑案例"的验证**。
3. 三个案例研究跑的三个样本（`demo-app` / `obfuscated-app` / `multidex-app`）都在 `examples/` 里，
   体积合计不到 7 KB——把它们放进镜像没有实质成本。
4. 成本最高的从来不是"把样本放进镜像"，而是**改完之后要复测构建时间并把新口径写回 7 处引用**。

**建议（一句话）**

> **值得现在就做**：在 `Dockerfile` 最后一次 `uv sync` 之后加一行 `COPY examples/ examples/`，
> 在 CI 的 docker job 里加一步用相对路径在镜像内跑通 `analyze examples/demo-app/demo.apk`，
> 并在 install.md 的 Docker 段补上这条命令——让"镜像里能跑案例"成为**被 CI 验证过的事实**，
> 而不是文档里的一句承诺。

**若本轮不安排镜像重建**（复测构建时间需要一次冷缓存构建 ≈ 18–20 分钟机时），则退一步做方案 B 的最小版：
（**后续没有走这条路**：新口径改由 CI 实测，见 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)）
把 [m10-reader-package.md:164-171](m10-reader-package.md#L164) 那段逐字抄进 install.md 的 Docker 段，
并把两处命令收敛到同一个脚本引用上。C6 因此从"读者卡住"降级为"读者要多绕一步"，方案 A 留到能复测构建时间的那一轮再做。

**为什么 A 优于 B**：本项目的纪律是"证据先于断言"。镜像能跑案例这条承诺，应该由 CI 里的一条命令来守，
而不是由文档来守；B 只是把承诺写得更详细。

## 4. 哪些还没核实、为什么

| 没核实的 | 为什么 |
|---|---|
| 镜像内部的实跑行为 | 本机无 `dexatlas:*` 镜像；构建需联网下载 JADX/Apktool（[Dockerfile:51-61](../../Dockerfile#L51)），本轮不联网、不构建镜像。镜像内的结论由 `Dockerfile` + 同版本 CLI 实测推导 |
| 加 COPY 后的构建时间 | 本轮（调研时）未构建镜像；文中引用的是既有实测口径（1099 秒 / 2 分 16 秒）。**后续已补**：新镜像在 CI 上实测，`docker build` 这一步 **46 秒**（唯一落点 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)） |
| 镜像体积变化 | 未构建镜像；按 `examples/` 实测 43,995 B 估算，相对"约 1.3 GB"可忽略 |
| PowerShell / CMD 下的路径行为 | 本轮只实测了 Git Bash（MSYS）；Windows 上另两种 shell 未测（相对路径在三种 shell 上都不会被改写，但未实测） |
| 预构建镜像场景 | 目前不存在发布镜像的流水线，无从核实；方案 B 的有效期依赖这一前提 |
| 三个案例研究在容器里的完整复现 | 本轮只跑了 demo 样本，没逐个跑 `docs/case-studies/` |

## 5. 复核用的命令（本轮实际跑过，可重跑）

```bash
# 1) 镜像里没有 examples/（静态）
grep -n "^COPY" Dockerfile

# 2) CLI 能力面
PYTHONPATH="<worktree>/src" "E:/Dexatlas/.venv/Scripts/dexatlas.exe" --help

# 3) 路径不存在时的行为（= 当前镜像里 analyze 案例的结果）
PYTHONPATH="<worktree>/src" "E:/Dexatlas/.venv/Scripts/dexatlas.exe" analyze /app/examples/demo-app/demo.apk; echo "exit=$?"

# 4) 样本可达时的完整案例（工作区落在本工作树 .scratch/）
export DEXATLAS_WORKSPACE="<worktree>/.scratch/docker-gap/ws"
PYTHONPATH="<worktree>/src" "E:/Dexatlas/.venv/Scripts/dexatlas.exe" analyze examples/demo-app/demo.apk \
    -o .scratch/docker-gap/demo-report.md --json .scratch/docker-gap/demo.json
PYTHONPATH="<worktree>/src" "E:/Dexatlas/.venv/Scripts/dexatlas.exe" projects
PYTHONPATH="<worktree>/src" "E:/Dexatlas/.venv/Scripts/dexatlas.exe" export apk_80a8fe0e81204c9f \
    -o .scratch/docker-gap/evidence.zip

# 5) 样本体积与 zip 结构
du -sb examples && python -c "import zipfile,pathlib;[print(p,zipfile.ZipFile(p).namelist()) for p in sorted(pathlib.Path('examples').rglob('*.apk'))]"

# 6) Git Bash 的路径改写（用现成 alpine，不构建本项目镜像）
docker run --rm alpine:latest echo /app/examples/demo-app/demo.apk
docker run --rm alpine:latest echo examples/demo-app/demo.apk
MSYS_NO_PATHCONV=1 docker run --rm alpine:latest echo /app/examples/demo-app/demo.apk
```

**注意**：第 2–4 步借用了主检出的 venv（`E:\Dexatlas\.venv`）。它指向主检出的 `src/`，
因此必须用 `PYTHONPATH` 指向本工作树的 `src/` 才是在测本工作树的代码（两边 `src/` 内容相同），
并且用 `DEXATLAS_WORKSPACE` 把工作区指向本工作树的 `.scratch/`，避免写到主检出的工作区。
