# 镜像里能跑仓库自带的案例（C6 方案 A 的落地）

> **基线**：本报告的每一个数字都来自 **2026年11月18日** 在分支
> `claude/fervent-rhodes-e1a6a4`（复核工作树
> `E:\Dexatlas\.claude\worktrees\fervent-rhodes-e1a6a4`，基线 commit `3245fb4`
> 加上本轮改动）上的实跑。
> **镜像内部没有本地实跑**——本地不构建镜像，理由与边界写在 §5。
> 前一份调研报告是 [docker-examples-gap.md](docker-examples-gap.md)：它是「之前」的快照
> （那时镜像里确实没有样本），本报告是它建议的方案 A 的落地。

## 0. 结论

1. **镜像现在自带样本**：`Dockerfile` 末尾多了一行 `COPY examples/ examples/`，
   样本落在镜像的 `/app/examples/` 下（`WORKDIR` 是 `/app`）。
2. **CI 会验它**：`.github/workflows/ci.yml` 的 `docker` job 多了一步，在**刚构建出来的
   镜像里**用**相对路径**跑通 `analyze examples/demo-app/demo.apk`——第一遍什么卷都
   不挂（这就是 C6 判据 (a) 的字面要求），核出退出码为 0；第二遍把报告写出来，核出
   报告里的四个计数（classes / methods / call sites / call edges）都不为空。
3. **说明跟着改**：`docs/install.md` 的 Docker 段从「镜像带代码不带样本」改成
   「镜像带样本」，挂卷只留「用你自己的 APK」这一种用法。
4. **边界**：镜像内部的一切**只由 CI 验证**，本报告没有本地镜像内的输出；本报告里的
   数字是**宿主**上用同一套源码跑同一条分析得到的（口径见 §3、§5）。

## 1. 改了什么

### 1.1 `Dockerfile`：一行 COPY，放在最后

```dockerfile
COPY examples/ examples/
```

放在文件**末尾**（`CMD` 之后），有两个理由，两个都是「不破坏别的东西」：

- **在最后一次 `uv sync --no-dev --extra analysis --frozen` 之后**（也在后端安装之后）。
  依赖层与后端层是镜像里最贵的两层（构建期要从 GitHub 下载 JADX 与 Apktool），
  把样本放在它们之后，改一个样本就不会让这些层失效。
- **在文档引用的每一行之后**。`docs/` 里有若干处按 `file:line` 引用 `Dockerfile`
  （例如 [docker-examples-gap.md](docker-examples-gap.md) 里的第 24、32–37、39–41 行），
  插在中间会让这些行号全部往后挪。放在末尾则一个行号都不动。

镜像里的路径：`/app/examples/demo-app/demo.apk`（`examples/` 目录的内容被复制到
`/app/examples/` 下；`COPY` 复制的是目录**内容**，目录本身不复制）。
样本共 37 个文件、5 个 APK、43,995 字节——相对镜像的体积可以忽略。

### 1.2 CI 的 `docker` job：多了一步，名字也跟着改

`.github/workflows/ci.yml:436-494` 的 `docker` job：

| | 改前 | 改后 |
|---|---|---|
| job 显示名 | `Docker image builds` | `Docker image builds and analyses a bundled sample` |
| 步骤 | 构建镜像 + 跑 `dexatlas backends` | 同上 + **在镜像内分析仓库自带样本** |

**为什么改名字**：这个 job 现在多做了一件事，CI 界面上显示的名字是读者判断
「这个 job 证明了什么」的第一入口。名字里只有「builds」而它其实也证明了「能分析」，
记录就少了一半。

**为什么没有改门禁清单**：读过 `scripts/check-gate-coverage.py` 之后，结论是**不用改**。
那份脚本登记的是**门禁脚本**（`scripts/check-*.py`、`verify-*.py`、`*_selfcheck.py`）
与「谁在跑它」，检查的方向有两个：门禁脚本必须有人跑、进了 CI 的脚本必须登记在册。
`docker` job 不跑任何门禁脚本，它跑的是 `dexatlas` 这个 CLI，所以它不在那份清单的
管辖范围内（清单见 `scripts/check-gate-coverage.py:48-58`）。

**要跟着改的是另一处记录**：`docs/status.md` 的 CI job 表里那一行 job 名与
「覆盖什么」的说明，已同步改成新名字与新说明。

**job 的 key 没有动**（仍然是 `docker:`），所以别的 job 对它的 `needs:` 引用不受影响。

### 1.3 `docs/install.md`：Docker 段

改前写的是「镜像带代码、不带样本，分析要自己挂一个 APK 进去」，给的命令是
挂载 `$PWD/examples`。改后：

- 分析命令直接用**镜像自带的样本**，路径是相对路径：

  ```bash
  docker run --rm -v dexatlas-workspace:/workspace dexatlas \
    dexatlas analyze examples/demo-app/demo.apk
  ```

- 挂卷只留「用你自己的 APK」这一种用法：

  ```bash
  docker run --rm -v "$PWD/my-apks:/samples:ro" -v dexatlas-workspace:/workspace dexatlas \
    dexatlas analyze /samples/app.apk
  ```

### 1.4 登记

- `docs/reports/README.md`：本报告进 §6，该节份数 35 → 36、合计 72 → 73，
  页首「目录里 N 个 `.md` 全部被点名」同步改对。
- `scripts/check-doc-citations.py` 的 `DOCS`：本报告在册，所以本报告里的
  `file:line` 引用会被逐条核对，不是一次性的写法。

## 2. 镜像里现在有什么

| 内容 | 出处 |
|---|---|
| `python:3.12-slim` 基础镜像 | [Dockerfile:3](../../Dockerfile#L3) |
| JADX 1.5.2、Apktool 2.11.1（构建期验证过） | [Dockerfile:46](../../Dockerfile#L46)、[Dockerfile:51-61](../../Dockerfile#L51) |
| 项目代码（`src/`）与依赖（`uv sync --no-dev --extra analysis --frozen`） | [Dockerfile:32-37](../../Dockerfile#L32) |
| `WORKDIR /app`、`VOLUME /workspace`、`EXPOSE 8000`、`CMD uvicorn …` | [Dockerfile:24](../../Dockerfile#L24)、[Dockerfile:63](../../Dockerfile#L63)、[Dockerfile:65](../../Dockerfile#L65)、[Dockerfile:70](../../Dockerfile#L70) |
| **仓库自带的第一方样本**（`/app/examples/`） | `Dockerfile` 末尾的 `COPY examples/ examples/` |

镜像里**仍然没有**的东西：`fixtures/`（第三方样本由 `scripts/fetch-fixtures.sh` 按需拉取）、
`scripts/`、`tests/`、`docs/`。

## 3. 镜像内那条命令与它的预期输出

镜像里的样本就在代码旁边，所以**一条命令、什么卷都不用挂**：

```bash
docker run --rm dexatlas dexatlas analyze examples/demo-app/demo.apk
```

要留着分析结果，就挂一个工作区卷（分析写进 `DEXATLAS_WORKSPACE`，即 `/workspace`）：

```bash
docker run --rm -v dexatlas-workspace:/workspace dexatlas \
  dexatlas analyze examples/demo-app/demo.apk
```

预期 stdout 的形状（**宿主**上同一套源码、同一份样本的实测输出；
`project.class_count` 等四个计数打印在 `src/dexatlas/cli/main.py:359-366`）：

```text
✓ apk_80a8fe0e81204c9f — 4 classes, 8 methods, 23 call sites, 21 call edges, 0 resource strings (1.0s)
```

退出码 **0**。

**镜像里的预期值是 5 / 8 / 23 / 21 / 1**（类 / 方法 / 调用点 / 调用边 / 资源字符串）：
镜像里三个后端齐全，JADX 会加合成类（生成的 R 类），所以比宿主那次多一个类、一个
资源字符串。这个数是前一份调研报告（[docker-examples-gap.md](docker-examples-gap.md)）
按「镜像里三个后端都在」推导出来的，**不是镜像内的实测**——镜像内的实跑在 CI 上。

三条读法上的坑，写在这里是因为它们会决定断言怎么写：

1. **宿主那次没有 JADX 与 Apktool**，分析因此记录了 2 条「后端不可用」的错误
   （`!` 开头的那两行）。镜像里三个后端齐全，所以**镜像内的输出没有那两行警告**，
   而且类数可能比 4 多——JADX 会加合成类（比如生成的 R 类）。这就是 CI 用
   **下界**（`>=`）而不是等值断言的原因：宿主那组数（4/8/23/21）与镜像里那组数
   （5/8/23/21）都落在下界之内。
2. **stdout 会被折行**：Rich 按终端宽度排版，宿主实测那一行在 80 列下断成了三行。
   所以 CI 断言的是 **JSON 报告**里的计数，不是 stdout 的文本。
3. **计数取自 JSON 报告的 `summary`**：`call_sites` 与 `call_edges` 两个键在
   `src/dexatlas/reports/json_report.py:103-110`。

## 4. CI 怎么验

`.github/workflows/ci.yml:453-494` 那一步（`Analyse the bundled sample inside the image`）
按顺序做四件事：

1. **第一遍：什么卷都不挂**。
   `docker run --rm dexatlas:ci dexatlas analyze examples/demo-app/demo.apk`
   —— 不挂样本、不挂工作区、不下载任何东西。这正是 C6 判据 (a) 的字面要求
   （「`docker run` 在**不带卷**的机器上能跑通一个案例」）：
   - **退出码**：`|| status=$?` 把退出码接住，随后显式判它是不是 0——不是 0 就让这一步红；
   - **相对路径**：`examples/demo-app/demo.apk` 在容器里解析（`WORKDIR` 是 `/app`），
     不经过宿主，所以不受 Git Bash 改写「看起来像 Windows 路径」参数的影响。
2. **第二遍：同一遍分析，把报告写出来**。
   `mkdir -p "$RUNNER_TEMP/docker-sample"`，然后
   `docker run --rm -v "$RUNNER_TEMP/docker-sample:/out" dexatlas:ci dexatlas analyze examples/demo-app/demo.apk --json /out/report.json`。
   挂的只是**报告的落点**，不是样本——样本仍然来自镜像内部。
3. **读回 JSON 报告，核四个计数**：
   - `classes >= 4`、`methods >= 8`、`call_sites >= 23`——这三个下界是仓库自己的测试
     为这份样本钉的数（`EXPECTED_METHODS`、`EXPECTED_REFERENCES`、
     `MIN_CLASSES_FROM_DEX` 在 `tests/test_demo_app.py:29-31`）；
     镜像里的 JADX 会在上面再加（合成类），所以是下界不是等值。
   - `call_edges > 0`。
   四个数都会打进 CI 日志。
4. 任何一条不成立，这一步就红——**镜像里能不能跑案例，从此是 CI 验证过的事实，
   而不是文档里的一句话**。

镜像里跑两遍的成本是分钟级 job 里多几秒：容器内三后端齐全的一次分析约 8 秒
（读者实走演练的实测）。

## 5. 核实边界（务必先读）

- **本地没有构建过镜像，也没有在镜像内跑过任何命令。** 本机的 Docker 把镜像层与
  构建缓存写进 C 盘，违反本机「不往 C 盘装任何东西」的约束。所以镜像内的行为
  **只由 CI 的 `docker` job 验证**；本报告描述的镜像内行为是「`Dockerfile` + 同一套
  CLI 的实测行为」的推导，真正的实跑在 CI 上。
- **本报告里的数字是宿主实测**，口径如下：
  - 解释器用主检出的 venv（`E:\Dexatlas\.venv`），`PYTHONPATH` 指向本工作树的 `src/`，
    已核对 `dexatlas.__file__` 落在本工作树内；
  - 工作区指向本工作树的 `.scratch/docker-samples/ws`；
  - 命令：`dexatlas analyze examples/demo-app/demo.apk --workspace .scratch/docker-samples/ws --json .scratch/docker-samples/report.json`；
  - 实测：退出码 0，`classes=4`、`methods=8`、`call_sites=23`、`call_edges=21`，
    耗时 1.0 s。
- **宿主与镜像的差别只有两处**：镜像多两个 Java 后端（JADX、Apktool），样本路径是
  容器内的相对路径。计数本身来自 DEX，两边应当一致或镜像更多（JADX 的合成类）。
- **CI 步骤本身也没有在本地跑过**：它需要构建镜像。步骤里的 Python 只用标准库
  （`json`、`os`、`pathlib`），GitHub 的 `ubuntu-latest` runner 自带 `python3`。

## 6. 需要主会话接手

1. **回归测试（本轮按约束没有加）**：`tests/` 在源码指纹的覆盖范围内，所以本轮
   不动它。建议补两条**只读文件、不跑 Docker**的快测试：
   - 一条读 `Dockerfile`，断言 `COPY examples/ examples/` 出现在最后一次
     `uv sync --no-dev --extra analysis --frozen` 之后；
   - 一条读 `.github/workflows/ci.yml`，断言 `docker` job 里有那条镜像内的
     `analyze examples/demo-app/demo.apk` 与四个计数的断言。
   两条都不需要 Docker，因此不会给 CI 增加分钟级的开销。
2. **本轮不影响源码指纹**：指纹的范围是 `src/` 与 `tests/` 下的 `.py`、
   `pyproject.toml` 与测量脚本自己（`scripts/refresh-report-figures.py:953-976`
   的 `fingerprint_files`）。本轮改动的文件一个都不在这个范围里，所以主会话正在跑
   的那轮测量**不会被本轮作废**。
3. **`docs/status.md` 的 job 计数是陈旧的**（那一节写「九个 workflow job」，表里十行，
   `ci.yml` 里十三个 job 定义）。这是另一处改动带来的陈旧，本轮只改了表里 docker
   那一行，没有动计数——留给主线统一处理。
4. **仓库没有 `.dockerignore`**：构建上下文是整个工作树（含 `.git`）。本轮没有加
   ——加它会改变构建行为（`.git` 变小、上下文变小），需要主会话决定是否单独做。
5. **本轮让两处行号跟着走**：`docs/reports/post-release-rehearsal.md` 里引用
   `measurement` job 的两处行号（`.github/workflows/ci.yml:724` 与 `:771`）因为本轮
   往 `ci.yml` 里加了步骤而漂移，已用 `scripts/remap-citations.py` 重新推导。
   另有一处漂移是 **main 自己的**（提交 `7593574` 改了测量脚本，一处裸行号落到了
   空行上），顺手把它改成显式的文件引用——那一处本来指的就是 `tests/test_docs.py`
   里那个测试函数。
6. **C6 的另一条判据这一轮没做，下一轮做完了**：「选 (a) 要把新的构建时间写回所有引用旧口径的地方」。
   本轮**没有重建镜像**（本地不构建），所以镜像的构建时间口径还是旧的那份
   （调研报告里的冷缓存 18–20 分钟机时）。这一条要等 CI 上那次真实构建的日志出来
   才能写，主会话合并后跑一次 `docker` job 就能拿到。
   **后续（2026年11月18日）已补**：那份日志出来了——**`docker build` 这一步实测 46 秒**
   （run `44334171465` 的 `Docker image builds and analyses a bundled sample` job 里的
   `Build image` 步骤），唯一落点是 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)。
   旧的那个数（读者本机冷缓存、走代理下载，1099 秒）测的是**另一段**，仍然成立，
   但不再是最新的口径——新口径测的是 CI runner。
7. **`tests/test_docs.py` 有 4 条测试在 main 上已经是红的**（执行报告里的覆盖率数字
   与树的语句数对不上：`reports/evidence_package.py` 记录 172、树里 187）。本轮没有碰
   `src/` 与 `docs/reports/phase1-execution-report.md`，所以这 4 条不是本轮造成的
   （`git diff main --name-only` 里没有这两个路径），它们要等主会话那轮完整重测量落盘。
8. **M10 读者包里的那段命令没跟着改**：`docs/reports/m10-reader-package.md` 里
   「**镜像里没有 `examples/`** → 要挂两个卷」那段，写的还是挂卷的办法。那条命令
   **仍然能跑**（它把宿主的 `examples/` 挂到 `/app/examples`，盖住镜像里那份，读的
   仍是同一份样本），但段首那句「镜像里没有 `examples/`」现在是假话，而且它不再是
   唯一跑法。M10 材料归主会话，本轮没动。

## 7. 与既有报告的关系

- [docker-examples-gap.md](docker-examples-gap.md) 是 2026年11月18日的**调研快照**：
  它记录的是「镜像里没有 `examples/`」这个事实，以及方案 A / 方案 B 的建议。
  本报告是它的方案 A 的落地。读它时要记得：它的行号锚在它自己复核的那棵树上。
- 本报告不是只读审计——它当场改了 `Dockerfile`、CI 与文档，所以
  `docs/reports/README.md` §6 里「本轮唯一当场实施了改动的是
  `evidence-package-isolation.md`」那句已同步改成本报告也在内。
- 构建时间的新口径落在 [c6-build-time-from-ci.md](c6-build-time-from-ci.md)——
  本报告 §6 第 6 条留下的那一件，就是它。
