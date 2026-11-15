# M6 层级 1 复验（m6-5 修复后）—— scripted 三配置零成本复核

**状态：已完成（2026-11-16）。零模型调用、零费用：复用
`scripts/m6_level1_drill.py --skip-full-set` 的 scripted provider，在
m6-5 修复分支 `claude/m6-level2-rootcause-fixes` @ `5c868a6`（含
`02d4b43` 合并）上重跑冻结 20 题 × A/B/DexAtlas 三配置（60 trace）。
trace 与报告原件在 `E:/Dexatlas/.scratch/m6-level1-recheck-after-fixes/l1/`
（不入库），本文只引用其结论。**

本文回答一个问题：m6-5 五题根因修复与报告数字重测（1492 项测试 /
91.8% 覆盖率）之后，层级 1 scripted 链路是否仍然与
[m6-level3-recheck.md](m6-level3-recheck.md) 的层级 1 记录一致——即
修复没有破坏 comparison harness 的 scripted 路径。这是真实模型复测
（层级 2 重跑）前的最后一道本地验证。

**措辞边界（沿用项目纪律）：与层级 1 基线相同，本链路的数字度量的是
harness 机械（题目下发、工具循环、trace 写入、判分），不是模型能力；
scripted 层 16 道实证题的失败是替身脚本「复述观察」形态与
`must_contain` 判分的固有错位，不能据此推断真实模型的表现。**

## 1. 结论先导

| 配置 | 层级 1 基线 | 本次 | 变化 |
|---|---:|---:|---|
| A | 3/20 | **3/20** | 无变化 |
| B | 3/20 | **3/20** | 无变化 |
| DexAtlas | 3/20 | **3/20** | 无变化 |

- **三配置得分与 `m6-level3-recheck.md` 的层级 1 记录逐题一致**：
  A/B 在 `manifest.package.demo`、`unanswerable.crypto-digestof-has-no-callers`、
  `unanswerable.demo-declares-no-receiver` 三题通过；DexAtlas 在
  `partial.no-apktool-there-is-no-manifest`、
  `partial.no-jadx-the-failure-is-recorded`、
  `xrefs.crypto-sign-call-site-count` 三题通过。
- **修复未破坏 scripted 路径**：m6-5 的五题根因修复不涉及判分谓词与
  comparison harness 的路由/工具面，本次复测的逐题判定与修复前完全
  相同，符合预期。
- 失败形态与基线同构：57 个未过 trace 中 `budget-exhausted` 计 32
  题次（与层级 1 基线 A/B 各 15 的分布一致）、`no-answer`（scripted
  替身 `the script ran out of answers`）计 25 题次，与
  `m6-level3-recheck.md` §3 的形态记录一致。

## 2. 运行配置与复现命令

| 项 | 值 |
|---|---|
| 运行日期 | 2026-11-16 |
| 分支 / commit | `claude/m6-level2-rootcause-fixes` @ `5c868a6` |
| 层级 1 | `scripts/m6_level1_drill.py --skip-full-set`（scripted，零模型调用） |
| 后端 | `DEXATLAS_JADX_PATH=E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat`、`DEXATLAS_APKTOOL_JAR=E:/Dexatlas/.scratch/backends/apktool.jar` |
| 工作区 | `E:/Dexatlas/.scratch/m6-level1-recheck-after-fixes/l1-ws/`（.scratch 内，不入库） |
| 产物 | `l1/service-regression-20-traces.json`（60 trace）、`l1/m6-level1-report.md` |

```bash
export PATH="/e/Dexatlas/.scratch/backends/jadx/bin:$PATH"
export DEXATLAS_APKTOOL_JAR="E:/Dexatlas/.scratch/backends/apktool.jar"
export DEXATLAS_JADX_PATH="E:/Dexatlas/.scratch/backends/jadx/bin/jadx.bat"
uv run --no-sync python scripts/m6_level1_drill.py \
  --workspace E:/Dexatlas/.scratch/m6-level1-recheck-after-fixes/l1-ws \
  --output-dir E:/Dexatlas/.scratch/m6-level1-recheck-after-fixes/l1 --skip-full-set
```

## 3. 逐题判定（60 trace）

| ref | task id | A | B | DexAtlas |
|---|---|---|---|---|
| q001 | manifest.package.demo | PASS | PASS | fail |
| q010 | manifest.permission.count-obfuscated | fail | fail | fail |
| q011 | manifest.permission.name-strings | fail | fail | fail |
| q015 | components.exported.demo | fail | fail | fail |
| q016 | components.exported.obfuscated | fail | fail | fail |
| q019 | overloads.method-identity.crypto-sign | fail | fail | fail |
| q041 | overloads.method-identity.descriptor-distinguishes | fail | fail | fail |
| q046 | ambiguity.declared-type-contradicts-body | fail | fail | fail |
| q022 | xrefs.crypto-sign-callers | fail | fail | fail |
| q027 | xrefs.handler-handle-callers | fail | fail | fail |
| q025 | xrefs.crypto-sign-call-site-count | fail | fail | PASS |
| q029 | strings.api-key.demo | fail | fail | fail |
| q034 | strings.telemetry-url.obfuscated | fail | fail | fail |
| q037 | resources.app-name.demo | fail | fail | fail |
| q083 | wheresource.app-name-resource-file.demo | fail | fail | fail |
| q071 | unanswerable.crypto-digestof-has-no-callers | PASS | PASS | fail |
| q077 | unanswerable.demo-declares-no-receiver | PASS | PASS | fail |
| q067 | partial.no-apktool-there-is-no-manifest | fail | fail | PASS |
| q066 | partial.no-jadx-the-failure-is-recorded | fail | fail | PASS |
| q050 | multidex.dex-file-count | fail | fail | fail |

逐题判定与 [m6-level3-recheck.md](m6-level3-recheck.md) §3 的表格逐行
一致；fail 形态同前（`budget-exhausted` 32 题次 + scripted
`the script ran out of answers` 25 题次）。

## 4. 结论

m6-5 修复分支上的层级 1 scripted 三配置复测与修复前的层级 1 记录
**完全一致**（A/B/DexAtlas 各 3/20，逐题判定无差异），确认五题根因
修复与报告数字重测没有破坏 comparison harness 的 scripted 路径。
真实模型复测（层级 2 重跑）前的本地零成本验证到此闭环。
