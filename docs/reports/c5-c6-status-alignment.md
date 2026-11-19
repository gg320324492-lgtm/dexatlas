# 第五轮对齐：C5 与 C6 的状态改成与现实一致

- 日期：2026年11月19日
- 工作树：`E:\Dexatlas\.claude\worktrees\nostalgic-kalam-b5df94`
- 分支：`claude/nostalgic-kalam-b5df94`
- **基准树 = `415f522`**（对齐时工作副本的 HEAD；`git rev-parse v1.0.0^{commit}` = `2715aef`，领先 22 个提交）
- 改动的文件：`docs/reports/v1.1.0-candidates.md`（**只改状态、判据对账与计数**）、本文
- **没有改**任何 `.py` → **源指纹不变**，报告里的数字保持有效
- **⚠️ 2026年11月20日起**：本文记的「`not_included` 三个键、`schema_version = 1`」
  描述的是**当时的包**；清单的第四个键（`schema_version = 2`）落地后，
  `docs/case-studies/attachments/` 里的四个包已重打，见
  [c16-manifest-fourth-key.md](c16-manifest-fourth-key.md)。本文其余结论不受影响。

## 0. 结论先说

| 候选 | 改前 | 改后 | 为什么 |
|---|---|---|---|
| **C6** 镜像里能不能跑案例 | ⬜ **未开始**（§0/§2 的分桶里）／ §3 已写成「已完成」 | ✅ **已完成**（两处口径统一） | 走的 (a) **已落地**：镜像自带样本、CI 在镜像内实跑、构建时间的新口径落在唯一一处 |
| **C5** 第三个样本（multi-DEX）的证据包 | ⬜ **未开始** | ✅ **已完成** | **已做完，只是状态没更新**——包、报告三件套、核验与链接全都在 |

**C5 的四条判据逐条满足，C6 的四条判据逐条满足**；两项都从「未开始·仓库内可做」桶
挪进「已完成」桶 → **已完成 5 → 7、未开始·仓库内可做 5 → 3**，
候选项总数仍是 **17**。

> **一句话**：这一轮**没有补任何东西**，只是把两处**早就对不上现实的状态**改成现实，
> 并把因此变动的**计数口径**一处不漏地改齐。

## 1. C6：状态怎么变的，依据是什么

### 1.1 事实（逐条读过原文，不是凭印象）

| 事实 | 出处 |
|---|---|
| 镜像自带样本：`Dockerfile` 末尾 `COPY examples/ examples/` | `Dockerfile` 文件最后（`CMD` 之后）——在最后一次 `uv sync` 与后端安装**之后**，改样本不失效依赖层 |
| CI 在镜像里实跑：**第一遍不挂任何卷**（不挂样本、不挂工作区），核退出码 0 | `.github/workflows/ci.yml` 的 `docker` job，步骤名 `Analyse the bundled sample inside the image` |
| 计数断言取**下界**：`classes >= 4`、`methods >= 8`、`call_sites >= 23`、`call_edges > 0` | 同一 step 里的内嵌 Python；下界是因为镜像里的 JADX 会在 R 类上多出内容 |
| APK 路径是**相对路径** | `analyze examples/demo-app/demo.apk`——在容器里解析，不受宿主改写 Windows 路径的影响 |
| 安装文档有容器内分析命令 | `docs/install.md` 的 Docker 段 |
| 构建时间的新口径落在**唯一一处** | [c6-build-time-from-ci.md](c6-build-time-from-ci.md)：CI run `44334171465` 的 `Build image` 步骤，`2026-11-18T15:18:54Z` → `15:19:40Z` = **46 秒** |

### 1.2 判据逐条对账

| 判据 | 结果 | 依据 |
|---|---|---|
| (a) `docker run` 在**不带卷**的机器上能跑通一个案例 | ✅ **满足——由 CI 验证** | 见 §1.1 第二行 |
| (a) 构建时间的新口径在材料里只有一处 | ✅ **满足** | 口径的**完整说明**（测的是哪一段、run id、步骤名）只在 `c6-build-time-from-ci.md`；那个数（46 秒）在几份材料里被复述，**每一处都指向那一处落点** |
| 两份材料里的构建时间口径标明测的是哪一段 | ✅ **满足** | 准备包与安装文档各自写明自己那段测的是**读者本机**；两个数**不合并成一个区间** |
| (b) 两份材料里的命令逐字一致 | — **不适用** | 这一支没走（走的是 (a)） |

### 1.3 边界：这一条**没有**本地实跑

**镜像内没有本地实跑**——本机不构建镜像（构建要写 C 盘），所以「镜像里能跑案例」
是**由 CI 的 `docker` job 验证**的，**不是**作者本人在本机验证的。

候选清单的状态栏因此写成：

> **边界（不要写成「本地验证通过」）**：**镜像内没有本地实跑**……所以这一条是
> **由 CI 的 `docker` job 验证**的。

**没有写成「已验证跑通」**——这两句话在读者眼里不是一回事。

## 2. C5：核完了，是「已做完只是状态没更新」

### 2.1 现状

`docs/case-studies/attachments/` 现在是 **16 个文件** = **四个证据包 + 十二份散装报告**
（每个包三件套：`.md` / `.json` / `.html`）——**不是**候选清单初稿里写的 9 个。
multi-DEX 的包**在**：`multidex-evidence-package.zip` + `multidex-report.{md,json,html}`，
入库提交 `92053b0`。

四个包里的 `manifest.json` 自记的 `run_id` **两两不同**
（下表是 2026-11-20 重打前的 id；重打后的当前 id 见
[c16-manifest-fourth-key.md](c16-manifest-fourth-key.md)）：

| 包 | run_id（重打前） |
|---|---|
| `demo-evidence-package.zip` | `run_e8e49384ab5246ab` |
| `api-integration-evidence-package.zip` | `run_fc8e432d4d094350` |
| `obfuscated-evidence-package.zip` | `run_dd897202eba74e28` |
| `multidex-evidence-package.zip` | `run_4fde2fa0b5254ccb` |

### 2.2 判据逐条对账

| 判据 | 结果 | 依据 |
|---|---|---|
| 附件目录里存在 multi-DEX 的包 | ✅ **满足** | `git ls-files docs/case-studies/attachments/` 有它 |
| `verify_package` 返回 manifest 且**逐文件哈希核验通过**，与另几个样本同一口径 | ✅ **满足** | 对齐轮**亲自复算**：读四个包内 `manifest.json` 的 `files`，逐文件算 sha256 与记录值比对 → **四个包全部通过**（各 3 个文件）。`not_included` 三个键（`apk` / `full_sources` / `unrelated_strings`）、`schema_version` = 1 —— 四个包**同一口径** |
| 案例页附件链接可达 | ✅ **满足** | 走查 2 的附录段四个链接（`.md` / `.json` / `.html` / `.zip`）都指向真实存在的文件；`docs/case-studies/README.md` 的附件清单写着「四个包、十二份报告、十六个文件」。相对链接检查在 `tests/test_docs.py::test_all_relative_links_resolve` 里 |
| 报告里引用的计数与工具实际输出**一致** | ✅ **满足** | 附录写的 **4 类 / 11 方法 / 13 调用点 / 10 调用边 / 证据 E-0001…E-0009 / jadx 解出 7 of 11**，与 `multidex-report.json` 的 `summary` **逐项相同**（`evidence_by_level.verified` = 9，`methods_decompiled` ÷ `methods_total` = 7 / 11） |

**一处如实说明**：附录正文引的 **4.8 s** 与包内那次 run 的 **4.7 s** 不同——
走查 2 **自己写明了**（「The counts agree; the run id and the timing do not.」：
附件是同一样本的**另一次** run）。这是**披露过的**，不是对不上的地方。

### 2.3 C5 还缺什么

**判据一条不缺 —— C5 是「已做完，只是状态没更新」。** 但核的过程里撞出两处
**记账与仓库现状对不上**的地方，**都不是 C5 的判据缺口**，本轮**没有改**（见 §4）：

1. **核验记录没有入库**。候选清单 §3 C4 的表格行写着
   「4 个包 + 12 份散装报告 + `verification.json` 入库 `docs/case-studies/attachments/`」，
   但实际入库的是 **16 个文件**（4 包 + 12 报告），`verification.json`
   **留在仓库外的** `.scratch/case3/final/`
   （[case-studies-third-package.md](case-studies-third-package.md) §2.3 与 §4 的入库清单里
   **都没有它**）。读者拿到包只能自己验；仓库里没有一份机器可读的四包核验记录。
   → **C4 那一行的记述**与仓库现状对不上，**不是 C5 欠的账**。
2. **没有回归测试钉住这 16 个附件的哈希**。仓库里有的守护是：
   `tests/test_first_party_samples.py` 守样本本体（multi-DEX 真的有两个 DEX、
   四个类分别在 `smali/` 与 `smali_classes2/`），
   `tests/test_docs.py::test_no_third_party_apk_or_binary_is_committed`
   守「附件目录里的东西只能是从这些第一方样本生成的」。
   **没有**一条测试钉住附件本身的 sha256 —— 附件被换掉，门禁不会红。

## 3. 计数口径：改了哪些地方

候选清单里**好几处写着一个数**。状态一变，这些数都要跟着改，**一处不漏**：

| 位置 | 改前 | 改后 |
|---|---|---|
| §0「这些候选现在是什么状态？」 | 5 项已做完（C1、C3、C4、C7、C14）、11 项未开始 | **7 项已做完**（C1、C3、C4、**C5、C6**、C7、C14）、**9 项未开始** |
| §0「现在就能做的有几项？」 | **5 项**（C5、C6、C15、C16、C17） | **3 项**（C15、C16、C17） |
| §0「排序前三？」 | C4 与 C14 已闭合 | **C4、C5、C6 与 C14** 已闭合 |
| §0「候选总数怎么对得上」 | 17 = 5 + 1 + 5 + 1 + 5 | **17 = 7 + 1 + 3 + 1 + 5** |
| §0.1 分桶表「已完成」 | 5 项：C1、C3、C4、C7、C14 | **7 项**：C1、C3、C4、**C5、C6**、C7、C14 |
| §0.1 分桶表「未开始·仓库内可做」 | 5 项：C5、C6、C15、C16、C17 | **3 项**：C15、C16、C17 |
| §0.1 分桶表「合计」 | 5 + 1 + 5 + 1 + 5 = 17 | **7 + 1 + 3 + 1 + 5 = 17** ✓ |
| §2「已完成的 N 项单列在上方」 | 五项 | **七项** |
| §2 排序表 | C5、C6 那一行是 `P1 / 未开始` | 删掉该行，在 ✅ 组里**新增 C5、C6 两行** |
| §2 结尾「一句话」 | 已完成的有五项；P1 = C15 + C5/C6 | 已完成的有**七项**；P1 **只剩** C15 |
| §3 开头说明 | 已完成的有五项 | 已完成的有**七项** |
| §7.1 树表 | 四棵树 | **五棵树**（加「对齐轮（第五轮）」，基准树 `415f522`） |
| §7.2 的加法说明 | 第四轮之后 5 + 1 + 5 + 1 + 5 = 17 | 追加 **第五轮之后 7 + 1 + 3 + 1 + 5 = 17** |

**没变的**：候选项总数仍是 **17**（C5、C6 是**状态**变了，不是**数量**变了）；
§4 的 **7 行**不变（C5、C6 不在 §4 里）；「未开始·等外部条件」仍是 5 项
（C2、C8、C11、C12、C13）；「要作者的真值」仍是 1 项（C9）；主体完成仍是 1 项（C10）。

## 4. 哪些是本窗口做的、哪些留给主会话

### 4.1 本窗口做的

- `docs/reports/v1.1.0-candidates.md`：
  **C5、C6 两节的状态与判据对账**、**§0 与 §0.1 的全部计数**、
  **§2 的排序表与两处说明**、**§3 开头说明**、**§7.1 的树表**、
  **新增 §7.2.3（复核方法）与 §7.3.3（没做的事）**、文末附表补四行。
- `docs/reports/c5-c6-status-alignment.md`（本文）。

### 4.2 留给主会话（本窗口**没有自己登记**，也**没有自己改**）

1. **`docs/reports/README.md` 的索引份数**：本文要登记进去。
2. **`scripts/check-doc-citations.py` 的 `DOCS` 名单**：本文要登记进去。
   本文引用了 `src/` 之外的行号（`Dockerfile`、`ci.yml`、`.json` 报告），
   登记后这些引用**有自动门禁在看**。
3. **顺带发现的一处过时**：`docs/reports/README.md` 里本文那一行的描述仍写着
   「**15 项候选**」，而本文现在是 **17 项**——登记时一并改掉。
4. **C4 那一行的记账差**（§2.3 第 1 条）：候选清单 §3 C4 的表格行说
   `verification.json` 入库了，实际它在仓库外。**C4 不是本窗口的活**，
   本窗口只对齐 C5/C6 的状态，没有改 C4 的实质内容——留给主会话裁定。
5. **两处回归测试的缺口**（都是「守护」而不是「判据」）：
   - **C6**：[docker-image-samples.md](docker-image-samples.md) §6 第 1 条建议的两条
     **只读文件、不跑 Docker** 的快测试（读 `Dockerfile` 断言 `COPY` 的位置；
     读 `ci.yml` 断言 `docker` job 里有那条镜像内的 analyze 与四个计数断言）
     **本轮按约束没有加**（`tests/` 在指纹范围内）。
   - **C5**：**没有**一条测试钉住 `docs/case-studies/attachments/` 里那 16 个附件的
     sha256 —— 附件被换掉，门禁不会红。
   两处都要改 `tests/` → 改源指纹 → 要等重测量，**由主会话统一排**。

### 4.3 本窗口明确没做的事

**没有改任何候选项的实质内容**（只改状态、判据对账与计数）；
**没有改** `Dockerfile`、`docs/install.md`、`.github/workflows/ci.yml`、
`src/`、`tests/`、`scripts/`、`CHANGELOG.md`、`README.md`、`README.zh-CN.md`、
`docs/status.md`；**没有构建镜像、没有跑 `docker`**；
**没有跑** `pytest --cov`、没有跑任何 `coverage` 命令、
**没有跑 `scripts/refresh-report-figures.py`**（并发测量会互相污染覆盖率）；
没有登录任何平台；没有发布任何内容。
为跑门禁**在本工作树建了自己的 venv**（`uv sync --frozen --all-extras`；
uv 缓存指向 E 盘的 `UV_CACHE_DIR`，**没有往 C 盘装任何东西**）——
本工作树的 venv 是**独立**的，不复用别的检出的。

## 5. 门禁

| 门禁 | 结果 |
|---|---|
| `ruff check .` / `ruff format --check .` | ✅ |
| `mypy` | ✅ |
| `vulture src/ tests/ scripts/ benchmarks/ --min-confidence 80` | ✅ exit 0 |
| `scripts/check-doc-citations.py` | ✅ `drifted: 0` |
| `scripts/check-version-claims.py --base auto` | ✅ exit 0 |

**没有动 `src/`，所以源指纹不变** —— 报告里已有的数字保持有效，
这一轮**不需要**重测量。
