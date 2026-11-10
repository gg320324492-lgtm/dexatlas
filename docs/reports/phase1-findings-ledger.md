# DexAtlas 阶段验收：发现的证据台账

每条都在**当前树**上独立复验过（不是采信审核 agent 的自述）。
复验方式标在「怎么验的」一栏。

基线：`8df894b`（P-B 合并后）。行号以该提交的干净副本为准。

> **这份台账记的是复验当时的状态。** 每条发现现在是什么样子，看
> [评审报告](phase1-review-report.md)与
> [Phase 2 issue 清单](phase2-issue-list.md)；这里留下的是**每一条是怎么验的**——
> 那部分在别处没有，而它是这个项目唯一不肯省的一步：不采信审核 agent 的自述，
> 每一条都在当时的树上独立复验过。

## 阻断级

| # | 发现 | 状态 | 怎么验的 |
|---|---|---|---|
| B1 | 上传文件名由客户端决定 → 一个项目的符号表装上另一个 APK 的类 | **确认，复现 3/3** | 构造时序（后台分析在跑 → 同名文件被覆盖）→ 项目哈希 `80a8fe0e8120`（demo.apk），符号表里却是 `com.example.strings.Constants`（strings.apk 的类）。**哈希对、id 对、provenance 对，只有类不对。** |
| B2 | 默认配置下 JADX 的 Java 反编译完全失效，报告照旧写 jadx 版本 | **确认，复现** | 相对工作区（默认 `.dexatlas`）：4 类 / 9 证据 / `source kind: smali`；绝对工作区：5 类 / 10 证据 / `source kind: java`。根因：`jadx/adapter.py` 同时传相对 `--output-dir` 和 `cwd=output_dir` → 双重嵌套 `.dexatlas/.../jadx/.dexatlas/.../jadx/sources/`。**测试抓不到：`tests/conftest.py` 工作区永远是绝对路径。** |
| B3 | `check-version-claims.py` 放过「本次提交造成的失真」 | 已修（`9f59279`） | 自己写复现脚本：clone → commit → tag → `--base HEAD~1` → 修复前 exit 0，修复后 exit 1 |
| B4 | `check-doc-citations.py` 只查 18/94，且 `main()` 永远 return 0 | 已修（`26d921f`） | 现在 94 处引用、93 处带符号校验、0 漂移 |
| B5 | JADX 后端无路径守卫 → 路径穿越 | 已修（`1b63366`） | 28 个新测试在未修复代码上红 |
| B6 | Androguard 一个 dex 解析失败 → 已索引部分的证据一条不生成 | 已修 | `core/pipeline.py` 的证据分支 |

## 重要级（仍成立）

| # | 发现 | 状态 | 怎么验的 |
|---|---|---|---|
| I1 | `analyze()` 无 try/except：异常穿出去，项目停在 `running` | **确认** | 让后端抛异常 → 数据库项目行 `status='running'`、`errors='[]'`、`classes=0`。**再传同一个 APK → 命中已有哈希 → 永不重跑**（端到端实测） |
| I2 | `/health` 每个请求开数据库写锁 | **确认** | `api/app.py:58` `Depends(get_analyzer)` → `Analyzer.__init__` → `Store.open()`（每次 `executescript` + `DELETE/INSERT schema_info`）。并发上传实测第二个 500 |
| I3 | `PRAGMA journal_mode = WAL` 在每次 `transaction()` 里 → 纯读也在写库 | **确认** | `storage.py:375`。栈顶就是这一行：`sqlite3.OperationalError: database is locked` |
| I4 | `cross_references_with_evidence` 数被调方法数，`cross_references` 数边数 | **确认** | `evidence.py:183` 的 `add_cross_references` 按 `by_callee` 分组，一个方法一条记录；`xrefs` 表一行一条边。fan-in=3 → 报 1 |
| I5 | >200 类时反编译覆盖率证据被 200 行窗口挤掉 | **确认（实验）** | 构造 251 条证据（250 类 + 1 条反编译），跑 `_evidence_section` → 反编译那条**不在表里**，报告写「51 further evidence records omitted」 |
| I6 | `xrefs` 表无主键 | **确认** | `storage.py:157-163` 无 `PRIMARY KEY`/`UNIQUE`；`classes`/`methods`/`fields` 都有 |
| I7 | workspace 并发不安全（同 APK 两次分析共用目录） | **确认** | 同 workspace 并发 → `OperationalError: database is locked`。`project.id` 是内容哈希 → 同一 APK 永远撞同一目录 |
| I8 | API 报告写「Analysis time 0.0s」，CLI 写真实耗时 | **确认** | `_rebuild_result` 不设 `duration_seconds`；`projects` 表也没有这一列。API 实测 `| Analysis time | 0.0s |` |
| I9 | 证据等级可提升（docstring 说「机制」，实际是约定） | **确认（探针）** | `Evidence(kind=BEHAVIOUR, level=VERIFIED)` 直接构造 → `verified`；`builder.add()` 同。报告渲染成 "Deterministically established by an analysis tool." |
| I10 | 报告数字只与旁边的 record 自比 | **确认** | 评审的复现：record + 图一起改成 999 → 无新失败。P-B 已修 |

## 重要级（已修）

| # | 发现 | 状态 |
|---|---|---|
| I11 | 版本号每个符号查一次 | 已修（缓存） |
| I12 | 触到上限静默截断，项目照样报「完成」 | 已修（记 `output_truncated`） |
| I13 | 三个上限里两个按 DEX 文件算 | 已修（一 APK 一预算） |
| I14 | 状态页说 3.13 job「一个后端都不装」 | 已修（它装 Androguard） |
| I15 | `evidence` 表从不清空 → 重分析后编号漂移 | 已修 |
| I16 | 文档里的行号引用漂移没人管 | 已修（94 处零漂移） |

## 新发现（成熟度评估 + Phase 2 清单）

| # | 发现 | 严重级 | 状态 |
|---|---|---|---|
| N1 | `base.py:3` 说「subprocess wrappers, never links」，`androguard/adapter.py:11-14` 说 Androguard 是进程内 | 中 | 已确认，修复中 |
| N2 | `storage.py:278`「Additive only」，`:294` 就 `DROP TABLE resources` | 中 | 已确认，修复中 |
| N3 | `ingest.py:6`「rather than by decompressing it」，`_verify_entries` 真的解压读字节 | 中 | 已确认，修复中 |
| N4 | `base.py:4` 拼写错误「a crashing or hangs engine」 | 低 | 修复中 |
| N5 | `README.md:143` xrefs 示例的方法 id 缺返回类型，照抄查不到 | 高 | 修复中 |
| N6 | `README.md:12` 测试数徽章手写（444 vs 实测 773） | 中 | 归我 |
| N7 | `SECURITY.md:31` 把「MCP surface」列为 in-scope，项目没有 MCP | 中 | 归我 |
| N8 | `EvidenceKind.CODE_LOCATED`/`BEHAVIOUR`、`EvidenceLevel.LEAD`/`INSUFFICIENT` 无生产者 | 中 | Phase 2 |
| N9 | `androguard/adapter.py:579,592` locator 截断到 64 字符 → 同前缀长串碰撞 | 中 | Phase 2 |
| N10 | `storage.py:844` 索引里的字符串名截断到 200 字符，未记载 | 中 | Phase 2 |

## 复核后不成立的（我原先的记录有误）

- `docs/status.md` §6 当时是 11 类不是 13 类（我记错了；现已是 21 类）
- #11 loguru 的位置不在 `core/logging.py`（不存在这个文件），在 `tools/androguard/adapter.py:96-119`
- #7 的描述不完整：重复有两个来源（跨 DEX / 同一 DEX 内同一目标被调两次）

## 我没能验证的

- 真实商业 APK、JADX 在 20 万方法下的表现（基准文档自己也说没测）
- GitHub Actions 的真实状态（只看了最近一次 run）
- `pip-audit` 结果、Docker build
- 演示 GIF/MP4 是否与当前代码一致
- POSIX 进程组终止（全部实测在 Windows 上）
