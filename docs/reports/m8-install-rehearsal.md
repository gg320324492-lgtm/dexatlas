# M8 — 干净安装与故障恢复演练报告

日期：2026-11-15。依据：`docs/roadmap/phase3-plan.md` §7（M8）前四条工作——
干净工作树安装演练、逐阶段耗时记录、平台矩阵、故障恢复验证。

演练在一个基于 main（bcafc33）的全新 git worktree
（`E:\Dexatlas\.scratch\m8-wt`，分支 `claude/m8-install-rehearsal`）中从零执行；
修复与回归测试落在会话工作树（分支 `claude/charming-kare-2b7516`）。

## 1. 摘要

- 安装链全程可走通：`uv sync`（四 extras）→ 后端检查 → fixtures → 首次分析
  → 检索 → 证据 locator 解析 → 三格式报告 → `dexatlas export` 证据包 →
  `verify_package`。Windows 实测无阻断卡点。
- Docker 路线实测通过：镜像构建约 2 分 16 秒，容器内后端检查、分析、导出全部成功。
- 故障恢复六项实测：坏输入（退出码 2）、后端缺失（记录 `not_installed` 继续）、
  超时（记录 `timeout` 继续）、重复分析幂等（同 project id）、截断（既有测试覆盖，
  退出码 5）、证据隔离（包不含 APK/全源码/未引用字符串）。
- 发现并修复 1 个真实缺陷（M8-1，红→绿，含 2 个回归测试）；另记录 3 个
  不在本轮擅自修改的问题（M8-2/M8-3/M8-4），附复现与建议修法。

## 2. 环境矩阵

| 平台 | 结论 | 证据 |
| --- | --- | --- |
| Windows 11 Pro（10.0.26300，本机） | ✅ 全链实测通过 | 本报告 §4–§5 |
| Linux（CI ubuntu-latest） | ✅ 七个 job 全部 success | GitHub Actions run [43690917224](https://github.com/gg320324492-lgtm/dexatlas/actions/runs/43690917224)（main @ bcafc33 之后的「报告数字完整重测量」提交）：Lint and format / Tests (Python 3.12，全后端) / Tests (Python 3.13，无外部后端) / Tests (Apktool only, no JADX) / Docker image builds / Dependency audit / M3 comparison 全部 success |
| macOS | 未验证 | 无 Apple 硬件，如实标注 |

本机关键组件版本：Python 3.12（uv 管理）、uv 0.11.21、Microsoft JDK 21.0.11、
Docker Desktop（Linux 容器）、JADX 1.5.2、Apktool 2.11.1、Androguard 4.1.4。
后端二进制复用本机 `E:\Dexatlas\.scratch\backends\`（约 250 MB，免重复下载）；
完整脚本安装（`scripts/install-backends.sh`）的耗时未在本轮重测——CI 的
Docker 构建每次都走完整下载并在构建期验证后端可运行，其耗时（见 §3）可作为
冷安装的上界参考。

## 3. 逐阶段耗时（Windows 实测）

| 阶段 | 命令 | 耗时 | 结果 |
| --- | --- | --- | --- |
| 创建干净 worktree | `git worktree add .scratch/m8-wt -b claude/m8-install-rehearsal bcafc33` | <1 s | ✅ |
| 依赖安装（冷缓存） | `uv sync --extra dev --extra analysis --extra mcp --extra demo` | 15 s | ✅ 97 包解析、93 包安装 |
| 依赖安装（暖缓存） | 同上（会话工作树） | 0.3 s | ✅ |
| 后端检查 | `dexatlas backends` | <1 s | ✅ 三后端 available |
| 测试夹具 | `bash scripts/fetch-fixtures.sh` | 3.0 s | ✅ TestActivity.apk 174,896 B、multidex.apk 1,233 B |
| 首次分析 | `dexatlas analyze examples/demo-app/demo.apk` | 6.8 s | ✅ 5 classes / 8 methods / 23 call sites / 21 edges |
| 检索 | `dexatlas search <pid> MainActivity` | <1 s | ✅ 类/方法/字段命中 |
| 证据 locator 解析 | `LocatorResolver.resolve(...)`（Python API） | <1 s | ✅ `jadx:`/`apktool:` 文件级定位成功；`androguard:classes.dex#...` 按构造解析（`path=None`） |
| 三格式报告 | `analyze -o r.md --json r.json --html r.html` | 9 s（含重新分析 7 s） | ✅ md 5.3 KB / json 11.7 KB / html 8.6 KB |
| 证据包导出 | `dexatlas export <pid> -o evidence.zip` | <1 s | ✅ 3 files + manifest |
| 包校验 | `verify_package` + `verify_citations` | <1 s | ⚠️ 首测 `citations_resolved=false` → M8-1，修复后 `true` |
| Docker 构建 | `docker build -t dexatlas:m8-rehearsal .` | 2 min 16 s | ✅ |
| Docker 后端检查 | `docker run --rm dexatlas:m8-rehearsal dexatlas backends` | 5 s | ✅ 三后端 available |
| Docker 分析+导出 | 容器内 `analyze` → `export` | ~10 s | ✅（见 M8-2 的 `--workspace` 卡点） |

**试用时间目标实测**：从空目录到第一份报告，暖缓存约 30 秒、冷缓存约 1 分钟
（不含 Docker）。Docker 路线从 clone 到第一份报告约 3 分钟。网络前提：uv 走
本机代理；`fetch-fixtures.sh` 依赖 `gh` CLI 访问 GitHub API（3 秒，2 个文件）。

## 4. 安装链逐阶段记录

1. `uv sync --extra dev --extra analysis --extra mcp --extra demo`：一次成功，
   无缺依赖、无编译失败。venv 建在 worktree 内（遵守「每个 worktree 自己的 venv」）。
2. 后端检查：`DEXATLAS_JADX_PATH`/`DEXATLAS_APKTOOL_JAR` 指向
   `.scratch/backends/` 后三后端全部 available。Windows 下 `DEXATLAS_JADX_PATH`
   必须指向 `jadx.bat`（`env.sh` 已示范）。
3. `scripts/fetch-fixtures.sh`：3 秒完成，写入 `fixtures/apk/` 并生成
   `SOURCES.md`（记录来源与许可证）。
4. 首次分析：6.8 秒完成，退出码 0，计数与 examples/demo-app 的预期一致。
5. 检索与 locator：`search`、`classes` 输出正常；`LocatorResolver` 对文件级
   locator 解析到 run 目录内真实文件；DEX 成员 locator 返回 `path=None`
   （按构造解析，符合设计）。
6. 报告导出：`-o/--json/--html` 三格式一次生成；HTML 报告为单文件、无脚本、
   无外链资源（M7 验收项复验通过）。
7. `dexatlas export`：包内 3 份报告 + `manifest.json`；`verify_package` 通过
   （schema 1、哈希、路径、项目绑定全部通过）。
8. `verify_citations`：**首测失败**（`citations_unresolved=["jadx:sources"]`）——
   见 §6 M8-1。

## 5. 故障恢复演练记录

| 场景 | 操作 | 实测结果 | 结论 |
| --- | --- | --- | --- |
| 坏输入 | 17 字节非 ZIP 文件当 APK 分析 | `Not a usable APK: ... is not a ZIP archive`，**退出码 2**（`EXIT_BAD_REQUEST`） | ✅ |
| 后端缺失 | `DEXATLAS_JADX_PATH="" DEXATLAS_APKTOOL_JAR=""` | `backends` 如实报 `not installed`×2；分析继续，errors 记录 `not_installed`×2，报告照常产出 | ✅ 失败是值不是异常 |
| 超时 | `DEXATLAS_TOOL_TIMEOUT_SECONDS=1` | 三后端各记一条 `timeout` 错误（jadx 被杀进程树、apktool/androguard 的 launcher 已先退出），报告照出 | ⚠️ 见 M8-4 |
| 截断运行 | demo.apk 过小，`DEXATLAS_TOOL_MAX_OUTPUT_BYTES=1MB` 未触发 | 既有测试 `tests/test_cli.py:1229` 以 monkeypatch 覆盖：退出码 5、输出含 "incomplete" 与 "exit code 5" | ✅（已有覆盖，未重复造） |
| 重复分析幂等 | 同一 APK 连续分析两次 | 同一 project id `apk_80a8fe0e81204c9f`，`projects` 仅 1 条，计数一致（8.3 s / 8.1 s） | ✅ |
| 证据隔离 | 检查 `export` 包内容 | 包内仅 3 报告 + manifest；`not_included` 明示 APK、全源码、未引用字符串不在包内 | ✅ |

## 6. 发现的问题

### M8-1（已修复，红→绿）verify_citations 把覆盖率观察的裸树 locator 判为未解析

- **现象**：真实管线导出的证据包，`verify_citations` 返回
  `citations_resolved=false`，`citations_unresolved=["jadx:sources"]`。M7 验收
  的「包搬走后引用仍可解析」对真实分析不成立。
- **根因**：`src/dexatlas/core/pipeline.py` 的 `_record_decompilation` 给覆盖率
  观察写的是 `source_locator(output_dir, sources)`，即裸目录 locator
  `jadx:sources`（指向反编译器整个输出树，不是单个文件）；而
  `verify_citations` 把每个 `jadx:` locator 都当文件引用去包内 `sources/` 树
  匹配，裸树名永远匹配不上。既有测试（`tests/test_evidence_package.py`）手工
  构造 evidence，只含文件级 locator，没覆盖这条真实管线必写的记录。
- **修复**：`verify_citations` 将 `_BARE_TREE_LOCATORS`（`jadx:sources`、
  `jadx:resources`）视为按构造解析（与 DEX locator、tool-error locator 同类）。
- **回归测试**（`tests/test_evidence_package.py`）：
  - fixture 追加真实管线式的裸树覆盖率记录；
  - `test_a_bare_tree_citation_does_not_count_as_unresolved`：修复后通过；
  - `test_a_bare_tree_citation_is_unresolved_without_the_exception`：把规则
    monkeypatch 掉重跑，断言 `jadx:sources` 落入 unresolved——红→绿的可撤回证明。
- **红→绿验证**：恢复旧实现（stash 修复）后新测试失败（1 failed）；恢复修复后
  3 个测试通过；`tests/test_evidence_package.py` 全量 14 passed。
- **E2E 复验**：修复后真实管线 `analyze → search → export → verify_package →
  verify_citations` 全链通过，`citations_resolved=true`、unresolved 为空。

### M8-2（重要，建议修，未在本轮改）CLI 查询命令没有 --workspace 选项

- **现象**：Docker/多 workspace 场景下，`analyze` 支持 `--workspace`，但
  `projects`、`export`、`search`、`classes` 等查询命令不接受该选项
  （`No such option: --workspace`）。容器内完成「分析 → 导出」只能改用
  `DEXATLAS_WORKSPACE` 环境变量，两条路径不一致，首次用户必踩。
- **复现**：`docker run ... dexatlas:m8-rehearsal bash -c 'dexatlas analyze /in/demo.apk --workspace /workspace/ws ...; dexatlas projects --workspace /workspace/ws'`
  → `No such option: --workspace`。
- **建议修法**：为全部接受 project id 的 CLI 命令补 `--workspace` 选项（与
  `analyze` 同一实现：设 `DEXATLAS_WORKSPACE` 后 `get_settings.cache_clear()`）；
  或至少在 `docs/install.md` 的 Docker 一节明示用环境变量。

### M8-3（可选，建议）install.md 的安装命令与推荐 extras 集不一致

- **现象**：`docs/install.md` 的安装节是 `uv venv --python 3.12` +
  `uv pip install -e ".[analysis]"`；而项目实际使用的四 extras 组合
  （dev/analysis/mcp/demo）与 lockfile 驱动的 `uv sync` 未出现。MCP 服务器、
  demo 依赖（Pillow 等）按 install.md 装出来是缺的。
- **建议**：install.md 增补「推荐：`uv sync --extra dev --extra analysis
  --extra mcp --extra demo`」，并说明各 extra 的用途与最小安装
  （仅 `analysis`）的差异；同时说明 `gh` CLI 是 `fetch-fixtures.sh` 的前置。

### M8-4（重要，涉及退出码契约，留主会话决策）全部后端超时后 run 仍 completed、退出码 0

- **现象**：`DEXATLAS_TOOL_TIMEOUT_SECONDS=1` 下三后端全部超时，报告含三条
  `timeout` 错误、classes/methods 计数为 0，但 project status 仍是 `completed`，
  CLI 退出码 0。
- **矛盾**：`docs/status.md` 的承诺是「只看退出码能分辨残缺运行」（截断为 5），
  但「全部后端都失败、索引为空」的运行退出码仍是 0——只看退出码会误判为成功。
  报告内的错误记录是完整的，所以不是「看似完整的成功报告」，但退出码语义有缺口。
- **建议修法**：当 androguard 索引也失败（0 classes）且三后端全部出错时，CLI
  以非零码退出（例如复用 `EXIT_FAILED=3`，或新增「无可用索引」码）。注意这是
  公共契约变更，按项目规则需显式版本化并更新契约表，故本轮只记录不改。

## 7. 对 docs/install.md 的修订建议（只列建议，未改文档）

1. 安装节补 `uv sync --extra dev --extra analysis --extra mcp --extra demo`
   推荐组合及各 extra 用途（对应 M8-3）。
2. Docker 一节补一句：容器内多命令共享 workspace 用
   `DEXATLAS_WORKSPACE=/workspace/ws` 环境变量（查询命令目前无 `--workspace`，
   对应 M8-2）。
3. Windows 提示：`DEXATLAS_JADX_PATH` 指向 `jadx.bat` 而非目录（本机 `env.sh`
   已示范，文档可收录）。
4. 前置依赖表补 `gh` CLI（`fetch-fixtures.sh` 用 `gh api` 下载夹具）。
5. `uv sync` 与 `uv pip install -e` 两条路线的差别（editable + lockfile）各一句。

## 8. 门禁结果

修复提交上跑：ruff check / ruff format --check / mypy strict /
vulture --min-confidence 80 / pytest 全量 / check-doc-citations /
check-version-claims --base auto —— 结果见提交信息与 CI。
