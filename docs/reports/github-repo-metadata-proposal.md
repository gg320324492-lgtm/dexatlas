# GitHub 仓库元数据与可发现性复核（只读 + 提案）

日期：2026-11-17 · 仓库：`gg320324492-lgtm/dexatlas` · 复核时的远端状态：`main` = `8f9ddca`

**性质：只读复核。** 本轮没有改动任何 GitHub 设置——没有执行 `gh repo edit`，没有改
description / topics / homepage，没有创建 Release，没有上传任何文件，没有打 tag。
除新增本文件外，仓库内没有改动任何文件。所有对外可见的改动只出现在本报告末尾的
「建议改动清单」里，是否执行、何时执行由作者决定。

**核查基线。** 元数据读自 GitHub API（`gh repo view` / `gh api`，见附录 A），
仓库内事实读自本 worktree 的 `claude/github-repo-metadata-2cd529` 分支（基于 `8f9ddca`）。
GitHub 上的元数据会随作者操作变化；本报告描述的是 2026-11-17 读到的值。

**引用说明。** `scripts/check-doc-citations.py` 只扫描四份文件
（`docs/analysis-provenance.md`、`docs/architecture/public-contracts.md`、
`docs/reports/phase1-execution-report.md`、`docs/benchmarks/large-apk.md`），**不覆盖本文件**，
所以本报告里的 `file:line` 引用是人工核对过的，不是机器门禁保证的。

---

## 0. 一句话结论

元数据整体可用（description 说清了"是什么"、topics 有 16 个、徽章数值与落盘报告一致、
5 个历史 Release 全部公开），但有三个硬伤会直接伤到"读者信不信"：

1. **GitHub 右侧许可证栏显示 `Other`（`spdx_id: NOASSERTION`）**，而 README 徽章与
   `pyproject.toml` 都写 Apache-2.0——同一件事在两处互相打脸。
2. **`v1.0.0` 有 tag、没有 Release**；GitHub Releases 页最新仍停在 `v0.2.0`，而 README 与
   `docs/status.md` 都写「v1.0.0 已发布」。任何点进 Releases 页的访客都会看到矛盾。
3. **"怎么复核"这一跳在首屏断了**：中文 README 全文没有任何 `how-to-verify` 入口，
   英文入口在全文第 83% 处（`README.md:477`）；两份 README 也都没有 `docs/reports/README.md`
   索引入口。项目最强的主张（每条结论可回溯到字节）在首屏没有指路。

这三项加上 social preview、topics 关键词、homepage 走向，构成本报告的 13 项建议。

---

## 1. About 区

| 位置/字段 | 当前值 | 建议 | 理由 | 怎么改（命令或操作） |
|---|---|---|---|---|
| About → Description | `Open-source AI-powered Android reverse engineering platform — decompilation, symbol indexing, evidence-based analysis reports.`（126 字符，上限 350） | **改写**：用 §6 的候选 A（242 字符），保留 "APK / static analysis / evidence" 三个搜索词与 "evidence-first" 口径，去掉 "AI-powered" | ① 读者会搜的是 "Android APK analysis"、"static analysis"、"MCP"、"AI agent"——现在一个都没有，"reverse engineering" 不是搜索用词；② "AI-powered" 与项目自己的口径相反：`docs/portfolio.md:90` 写明内置 agent 的产出是 lead 不是 finding，`README.md:5` 的 tagline 用的是 "a **bounded** AI agent" | `gh repo edit gg320324492-lgtm/dexatlas --description "<候选 A 全文>"`（或 Settings → About → Description） |
| About → Homepage | `https://github.com/gg320324492-lgtm/dexatlas#readme` | **改成指向 `docs/how-to-verify.md` 的绝对 URL**；若日后开 GitHub Pages，则改指站点地址 | 现状是"指向本页 README 的锚点"，等于没填——About 区里唯一的外链位置浪费在一个零信息量的跳转上。这个位置是读者做"值不值得信"决定的地方，而"怎么自己复核"是本项目唯一的一键自证入口 | `gh repo edit gg320324492-lgtm/dexatlas --homepage "https://github.com/gg320324492-lgtm/dexatlas/blob/main/docs/how-to-verify.md"` |
| About → Topics | 16 个：`ai-agent`、`androguard`、`android`、`android-security`、`apk-analysis`、`apktool`、`fastapi`、`jadx`、`llm`、`mcp`、`mobile-security`、`open-source`、`python`、`reverse-engineering`、`security-tools`、`static-analysis` | **补 4 个**：`apk`、`model-context-protocol`、`security`、`decompiler`（上限 20，现有空位 4） | `apk` 是精确通用词（3.8k 仓库在用），现在只有 `apk-analysis`；`model-context-protocol` 是 MCP 的规范 topic 名（45k 仓库），比单写 `mcp` 流量大；`security` 是最大泛流量入口（73k）；`decompiler` 命中工具中立受众。详见 §4.2 | `gh repo edit gg320324492-lgtm/dexatlas --add-topic apk --add-topic model-context-protocol --add-topic security --add-topic decompiler` |
| 仓库可见性 | `public`（`private: false`） | 不动 | 作品集定位要求公开；`docs/portfolio.md` 的对外口径也是 open-source | — |
| 默认分支 | `main` | 不动 | 与 tag、`docs/` 引用、CI 一致 | — |
| About → License 识别 | GitHub API：`{"key": "other", "name": "Other", "spdx_id": "NOASSERTION"}`；`gh api repos/…/license` 同样返回 `NOASSERTION` | **让仓库重新被识别为 Apache-2.0**（改动点在仓库文件，不在 GitHub 设置——先改 §8 第 8 项，识别会自动跟上） | 右侧栏现在对访客显示"许可证：Other"。同一仓库的 `README.md:11` 徽章写 `license-Apache--2.0`、`pyproject.toml:10` 写 `license = { text = "Apache-2.0" }`。**矛盾比没有更伤信任**：读者会怀疑两份文件里有一份是错的 | 见 §8 第 8 项（恢复规范 LICENSE 文本 + 新增 `NOTICE`）；改完后用 `gh api repos/gg320324492-lgtm/dexatlas/license --jq .license.spdx_id` 复核应为 `Apache-2.0` |
| 仓库内 `LICENSE` 文件 | 存在，190 行 / 10586 字节，Apache-2.0 文本但**与规范文本有两处不同** | **恢复为规范 Apache-2.0 全文** | 与 `choosealicense` 的规范文本逐行比对，只有两处不同：① §4(d) 的 NOTICE 传播条款被替换成 Apache-1.1 的短版（规范 15 行 → 仓库 4 行，缺"至少下列三处之一"与"NOTICE 内容仅供参考"两段）；② 附录版权行被填成 `Copyright 2026 DexAtlas contributors`（规范文本是 `[yyyy] [name of copyright owner]`）。第一处是**分发出去的许可证文本少了一段条款**，第二处让 Licensee 匹配不上 | 见 §8 第 8 项 |
| Issues | `has_issues: true`；历史上有 3 个 issue/PR（#1 issue、#2/#3 PR，均已关闭），当前 open issues = 0 | 不动 | 开了，且有使用记录；Issue 模板齐全（`.github/ISSUE_TEMPLATE/`） | — |
| Wiki | `has_wiki: true`，但 **wiki 仓库不存在**（`git ls-remote https://github.com/gg320324492-lgtm/dexatlas.wiki.git` → `Repository not found`） | **关掉**，或建一个 wiki 首页 | 访客点进 Wiki 得到一个空页。空标签页比没有这个标签更让人以为"内容在别处"。这个项目已经把计划板放在仓库内 `.github/issues/`，Wiki 没有承载对象 | Settings → General → Features → 关闭 Wiki；或若要保留，则先写 wiki 首页再说明用途 |
| Discussions | `has_discussions: false` | **开启**（或明确在 README 写"提问请走 Issues"） | 项目定位里 Discussions 适合"这套自核口径怎么看""要不要接某个后端"这类不报 bug 的对话；开着但空标签页的问题与 Wiki 相同，所以要开就连同 README 的指路一起开 | Settings → General → Features → 勾选 Discussions；并在 README 的「参与贡献」段指明去处 |
| GitHub Pages | `has_pages: false`；仓库内无站点构建配置（无 `mkdocs.yml`、无 `docs/index.md`） | 本轮**不做**；列为后续可选项 | 作品集若要有一份"自己的网页"，Pages 是零成本入口，但需要先写一个 landing 页或工作流，属于独立的一轮工作，不应混进元数据核对里 | 后续可开 `gh api -X POST repos/…/pages -f source[branch]=main -f source[path]=/docs`（需先有 `docs/index.html`） |

---

## 2. Releases

| 位置/字段 | 当前值 | 建议 | 理由 | 怎么改（命令或操作） |
|---|---|---|---|---|
| Releases 列表 | 5 个 Release：`v0.1.0`（2026-10-14）、`v0.1.1`、`v0.1.2`、`v0.1.3`、`v0.2.0`（2026-11-14 18:09）；全部 `draft: false`、`prerelease: false` | 不动 | 可见性正确（无草稿、无预发布），正文长度 4.6k–23k 字符，是完整的发版说明不是占位符 | — |
| 最新 Release | `v0.2.0` — "DexAtlas v0.2.0 — The Agent Layer, Open to a Caller" | **发布 `v1.0.0` 的 Release**，让最新指向 `v1.0.0` | `v1.0.0` 的 tag 已经存在且是 annotated tag，指向 `8f9ddca`（= `main` 当前 tip）；`README.md:41` 与 `docs/status.md:22` 都已经写"v1.0.0 已发布"。**GitHub Releases 页停在 `v0.2.0`，等于对外文本自证不了自己** | `HTTPS_PROXY=http://127.0.0.1:7897 gh release create v1.0.0 --title "DexAtlas v1.0.0" --notes-file docs/releases/v1.0.0.md`（命令已在 `docs/reports/v1.0.0-release-checklist.md:155` 与 `docs/reports/v1.0.0-release-runbook.md:254` 备好） |
| Release 正文来源 | 仓库里有两份候选：`docs/releases/v1.0.0.md`（发版说明）与 `docs/reports/v1.0.0-github-release-body.md`（为 GitHub 起草的正文，357 行，含一段标注「不得粘贴进 Release」的附录） | **发布前先定一份**：建议用 `docs/releases/v1.0.0.md`（它是随代码提交的落盘说明，链接可达），附录部分留在报告里 | 两份都存在且都被当成"正文"，容易被误用——`v1.0.0-github-release-body.md` 的开头就写着 "Everything from the `## Appendix` heading onward … must **not** be pasted into the GitHub Release" | 作者二选一；若选后者，按其文档自己的说明裁掉附录 |
| tag 与 Release 的对应 | 远端 8 个 tag：`v0.1.0`–`v0.2.0`、`v1.0.0`，另加两个非版本 tag `phase1-acceptance-2026-10-21`、`handover-2026-11-10` | 非版本 tag 不发 Release（现状正确），**仅补 `v1.0.0`** | 8 个 tag 对 5 个 Release，差的三个里两个是过程标记（本来就不该发），只有 `v1.0.0` 是版本 tag 却缺 Release | 同上 |
| Release 资产 | 5 个 Release 的 `assets` 均为 0 | 本轮不动 | 纯 Python 项目，无二进制产物；`docs/reports/v1.0.0-release-checklist.md` 里"附逐例证据包"是可选增强，不是发版前提 | — |
| 门禁覆盖 | `scripts/check-version-claims.py` 报的 "newest release: v1.0.0" 来自 **git tag**，不是 GitHub Releases | **不指望门禁**：这条差异没有 CI 能发现 | 这解释了为什么"README 说已发布、Releases 页没有"能长期并存：门禁核的是 tag，不是 Release 对象 | — |

---

## 3. 仓库页首屏

| 位置/字段 | 当前值 | 建议 | 理由 | 怎么改（命令或操作） |
|---|---|---|---|---|
| 标题 | `README.md:3` → `# DexAtlas` | 不动 | — | — |
| Tagline（英文） | `README.md:5` → `**From APK to Evidence — Powered by a bounded AI agent.**`（53 字符） | **保留** | "From APK to Evidence" 是这个项目最好的一句话；`bounded` 这个限定词把 agent 的边界写在了承诺里，比任何 "AI-powered" 都值钱 | — |
| Tagline（中文） | `README.zh-CN.md:5` → `**From APK to Evidence — Powered by AI Agents.**` | **改成 `… Powered by a bounded AI agent.`** | 中文版把 `a bounded AI agent` 译成了复数的 `AI Agents`，**丢掉了 "bounded"**——而这正是唯一防止读者把 agent 输出当结论的词。英文有、中文没有，两版承诺强度不同 | 改 `README.zh-CN.md:5` 一行 |
| 一句话说明（英文） | `README.md:7` → "An open-source, evidence-first Android reverse engineering and mobile application analysis platform."（133 字符） | 不动 | 已经说清了"是什么 + 什么原则"，比 About 区的 description 更好 | — |
| 一句话说明（中文） | `README.zh-CN.md:7` → "开源、证据优先的 Android 逆向工程与移动应用分析平台。" | 不动 | 同上 | — |
| 徽章：Tests | `README.md:12` → `tests-1588 passing`，链接落点 `tests`（目录） | 数字不动；**链接落点**可考虑改指测量报告 | 数字与落盘报告一致 ✓（见下） | — |
| 徽章：Coverage | `README.md:13` → `coverage-93.3%`，**链接落点 `pyproject.toml`** | 数字不动；**链接落点改指 `docs/reports/phase1-execution-report.md`** | `93.3%` 这个数字来自执行报告，不来自 `pyproject.toml`；点进去看到的是构建配置，不是 93.3% 的出处。徽章的作用就是把读者送到数字的来源 | 改 `README.md:13` / `README.zh-CN.md:12` 的链接目标 |
| 徽章数值与落盘报告是否一致 | **一致 ✓**：`README.md:12`/`README.zh-CN.md:12` 的 1588 与 `docs/reports/phase1-execution-report.md:76` 的 `1588`（1441 快 + 147 集成）相符；`README.md:13` 的 93.3% 与同文件 `:77` 的 `93.3%`（7117/7631 行）相符；该报告 `:877` 记录 `skipped: 0` | 不动 | 这是整套元数据里最健康的一处：徽章数字由 `scripts/refresh-report-figures.py` 写入，不是手打的；脚本在测量不完整时拒绝写入，所以徽章与报告不会漂 | — |
| 入口：「这是什么」 | `README.md:19-30`（三段：DexAtlas turns an APK into a picture you can verify / 结论分级 / 后端失败被当作值） | 不动 | 首屏第三段就把"证据优先"讲成了具体机制，不是形容词 | — |
| 入口：「怎么装」 | `README.md:190`（Quick start 段直接给 `docs/install.md`）+ `README.md:367`（Install shortcuts：uv / Docker / pipx） | 不动 | 装法有三条路径，且每条都标了完整说明在哪 | — |
| 入口：「怎么复核」 | 英文 `README.md:477`（"How to verify every claim"），位置在「Documentation → Project records」小节，全文 573 行的第 83% 处；**中文 README 全文 446 行，0 处 `how-to-verify` 链接** | **两份 README 都把「怎么复核」上提到首屏可见处**；中文至少要补上 `docs/how-to-verify.zh-CN.md` | `docs/how-to-verify.md` 与 `docs/how-to-verify.zh-CN.md` 都已存在（各约 26 KB）。中文 README 里连一个指向复核页的链接都没有——**中文访客走不了"复核"这一步**，而项目最强的主张恰好在这一步。英文那条入口深埋在第 83% 处，多数访客不会滚到 | 英文：把 `README.md:477` 那条上提到首屏状态块附近；中文：`README.zh-CN.md` 补 `docs/how-to-verify.zh-CN.md` 入口（该页已由 `f0f8636` 落地） |
| 入口：「报告索引」 | 两份 README **都没有** `docs/reports/README.md` 的链接 | **两份 README 都补一条** | 该目录现在有 43 份 `.md`，索引页自称"三十七份"（已过期）；没有入口，读者只能靠 `find` 摸索。（与 `docs/reports/readme-map-audit.md` §7 重复，以那份清单为准） | 在两份 README 的「项目记录」段各加一行指向 `docs/reports/README.md` |

---

## 4. 可发现性

### 4.1 description 的搜索词覆盖

读者在 GitHub 搜索框里会敲的词，与当前 description 的覆盖情况：

| 搜索词 | 当前 description 是否含 | 说明 |
|---|---|---|
| `Android` | ✓ | — |
| `reverse engineering` | ✓ | 是词组，但不是搜索习惯用语；`static analysis` 更常见 |
| `APK` / `Android APK analysis` | **✗** | 最直接的定位词缺席——项目处理的对象是 APK，description 里一次都没出现 |
| `static analysis` | **✗** | `reverse engineering` 是同义替换，不是等价命中 |
| `MCP` / `Model Context Protocol` | **✗** | MCP server 是这个仓库的差异化能力之一，description 完全没提 |
| `AI agent` | △（"AI-powered"） | 有 AI，无 agent；且 "AI-powered" 与项目口径相反 |
| `evidence` | ✓ | 这是应该保留的那个词——它是差异化，不是噪声 |

### 4.2 topics：补什么、不补什么

现状 16 个（上限 20，空位 4）。**建议补的 4 个，按价值排序：**

| topic | GitHub 上在用它的仓库数（2026-11-17 实测） | 理由 |
|---|---|---|
| `apk` | 3,784 | 最精确的通用词；现在只有 `apk-analysis`，而"apk"本身被大量项目单独标注 |
| `model-context-protocol` | 45,380 | MCP 的规范 topic 名。`mcp` 已在，但规范名的池子大一个量级，且搜 "model context protocol" 的人找不到 `mcp` 标签的项目 |
| `security` | 73,438 | 泛流量的最大入口。`security-tools`、`mobile-security`、`android-security` 三个都偏窄，`security` 是那个泛词 |
| `decompiler` | 865 | 工具中立，命中"我要反编译"这一类受众，不依赖读者认识 JADX/Apktool |

**不建议补的（附仓库里的依据，避免把话说大）：**

- `malware-analysis` —— `docs/portfolio.md:90` 明写 "It is not a malware classifier or a sandbox"。挂这个标签等于替项目认领它明确否认的身份。
- `owasp` / `masvs` / `mstg` —— 只在 `docs/roadmap/ROADMAP.md:293` 作为未来路线项出现（"Rule-assisted checks mapped to OWASP MASVS / MASTG, scoped initially to storage…"），当前不是主张，也不是能力。
- `ai` —— 太泛，且与 "AI-powered" 已经在 description 里带来的稀释同源；`ai-agent` / `llm` 已经覆盖。

**可选（受众窄，但与项目内核一致）：** `reproducibility`（6,804 仓库在用）。项目的一句话是"可复现"，但搜索"可复现"的人未必在 GitHub 找 topic，所以列入可选项而非建议项。

### 4.3 homepage 该指向哪里

现状 `https://github.com/gg320324492-lgtm/dexatlas#readme`。**建议：改成指向 `docs/how-to-verify.md` 的绝对 URL**，理由有三：

1. 现状 `#readme` 是"指向本页 README 的锚点"，链接出去等于原地不动，About 区唯一的横向链接位被浪费。
2. About 区是读者决定"要不要点进去"的地方，而本项目对外可验证的唯一动作就是"自己复核一遍"——把这一跳放进 About，等于在读者犹豫的那一刻递上证据，而不是等他们滚到第 83% 行。
3. 零成本：`docs/how-to-verify.md` 已在 `main` 上，URL 稳定，不需要新站点。

**两个替代方案，各有代价：**

- **开 GitHub Pages，把 homepage 指向 `https://gg320324492-lgtm.github.io/dexatlas/`** —— 这是唯一能同时补上"自己的网页"和 homepage 的做法，但仓库目前 `has_pages: false` 且没有站点构建配置（无 `mkdocs.yml`、无 `docs/index.md`），要新写一个 landing 页或工作流。建议作为独立一轮工作，不混进本轮。
- **清空 homepage** —— 如果作者认为 About 区不该放仓库内的链接，清空比留 `#readme` 干净（GitHub 不显示空白链接）。次选。

---

## 5. Social preview

| 位置/字段 | 当前值 | 建议 | 理由 | 怎么改（命令或操作） |
|---|---|---|---|---|
| Social preview | **没有自定义图**：`gh repo view --json usesCustomOpenGraphImage` → `false`；`openGraphImageUrl` 指向 GitHub 自动生成的卡片（`https://opengraph.githubassets.com/c51e5658fbeef85fb7dd86e0599924ce2b255a4554f2a163c95b6a0e42765b26/gg320324492-lgtm/dexatlas`） | **做一张 1280×640 的自定义图并上传** | 自动卡片只能显示仓库名 + README 顶部截图 + 语言色块，说不出"APK → 证据"这个主张，也没有任何品牌。这张图是仓库被分享到 X / LinkedIn / Slack / 聊天时给人的**第一印象**，而第一印象目前完全交给 GitHub 的默认模板 | 见下方操作步骤 |
| 生成规格 | — | **1280×640（PNG），< 1 MB**；内容至少包含：仓库名 `DexAtlas`、一行 tagline（建议用 `README.md:5` 那句）、三个关键词（`APK` / `static analysis` / `evidence`）、可选 logo | GitHub 官方要求：格式 PNG/JPG/GIF，**至少 640×320**，**1280×640 最佳**，文件 **< 1 MB** | — |
| 放哪 | — | 先作为候选文件随仓库提交（例如 `docs/assets/social-preview.png`），便于评审、版本化、可重生成 | 放进仓库才能被评审；`docs/assets/` 已有 `demo-quick.gif` / `demo.mp4` 可作素材 | 生成 PNG 后提交到 `docs/assets/social-preview.png` |
| 怎么让 GitHub 用它 | — | **必须在 Settings → General → Social preview → Edit → Upload an image 手动上传** | GitHub **不会**自动采用仓库里的 `.github/assets/social-preview.png` 之类路径的文件（官方文档只提供上传入口）。这是一条容易踩的坑：以为放进仓库就生效 | Settings → General → Social preview → Edit → Upload an image → 选 PNG → 保存 |
| 复核 | — | 上传后跑 `gh repo view gg320324492-lgtm/dexatlas --json openGraphImageUrl,usesCustomOpenGraphImage` | 应变为 `usesCustomOpenGraphImage: true`，且 `openGraphImageUrl` 指向新图（CDN 缓存可能延迟几分钟） | 同上 |

**本轮没有生成、也没有上传任何图片。** 上表只给规格与路径。

---

## 6. 「一句话说明这个项目」的三个候选

字符数按 GitHub description 的计数口径（Unicode 码点）实测；上限 350。

### 候选 A（242 字符）—— 推荐用在 About 区

> Evidence-first static analysis for Android APKs: decompile, index symbols, trace call graphs, and ship a report whose every fact names the tool, version and byte offset behind it. CLI, REST API, MCP server, web workbench, and a bounded agent.

- 含搜索词：`Android APKs`、`static analysis`、`APK`
- 含差异化：`evidence-first`、`bounded agent`（与 `README.md:5` 的 "bounded" 口径一致）
- 含形态：`CLI`、`REST API`、`MCP server`、`web workbench`
- 代价：没有点名三个后端（Apktool / JADX / Androguard）。**这是有意的**——About 区要回答"这是什么"，后端名属于"怎么做到"

### 候选 B（207 字符）—— 用在对外服务页 / 邮件 / 作品集介绍

> Open-source Android APK static analysis with Apktool, JADX and Androguard: a full symbol and call-graph index, plus evidence-backed Markdown/JSON reports. Runs as CLI, REST API, MCP server and web workbench.

- 点名后端 → 对**懂行的读者**更有说服力（"这三条主流链路都接了"）
- 弱项：没有 `evidence-first` 这个内核词，"evidence-backed" 只修饰报告，不修饰整个产品
- 适合对象：已经知道 APK 逆向是什么的工程师

### 候选 C（174 字符）—— 用作 taglines 备选（与 README 首屏呼应）

> From APK to evidence — every conclusion cites the tool, version and byte offset it came from. Open-source Android static analysis: CLI, REST, MCP server, and a bounded agent.

- 与 `README.md:5` 的 "From APK to Evidence" 同源，可作为「项目一句话」在不同上下文复用
- 最短、最好记，但没有说清"能做什么"（不点名反编译/索引/调用图）

**另有一个现成素材，但太长不能直接用：** `docs/portfolio.md` 的 "Short description" 共 601 字符，超过 GitHub 的 350 上限，且是散文体。它的措辞值得借鉴（"turns an APK into a picture you can verify"、"the report names what is missing"），候选 A 借了它的骨架。

---

## 7. 读者从仓库页到信这个项目，路上会缺什么

按影响排序。每条写清"卡在哪"和"补什么"。

| # | 缺口 | 卡在哪 | 补什么 |
|---|---|---|---|
| 1 | **许可证自相矛盾** | 右侧栏写 `Other`；README 徽章与 `pyproject.toml` 写 Apache-2.0 | 恢复规范 LICENSE 文本 + 新增 `NOTICE`（§8 第 8 项）。这不是"锦上添花"：项目的第一条纪律就是"结论必须能指回来源"，而"自己的许可证都说不清"是这条纪律的第一个反例 |
| 2 | **"已发布"在 Releases 页对不上** | README 与 `docs/status.md` 说 v1.0.0 已发布；而「Releases 页最新是 v0.2.0」 | 发布 `v1.0.0` 的 Release（§8 第 4 项）。正文已经写好了（`docs/releases/v1.0.0.md`），只差一次 `gh release create` |
| 3 | **「怎么复核」在首屏断了** | 中文 README 0 入口；英文入口在第 83% 行 | 两份 README 首屏各补一条（§8 第 9、10 项）。项目的主张是"可回溯"，而验证路径没有指路 = 主张无法兑现给访客 |
| 4 | **报告索引不可达** | 两份 README 都没有 `docs/reports/README.md` 入口；43 份报告只能靠搜 | 补一条索引入口（§8 第 11 项；与 `docs/reports/readme-map-audit.md` §7 重复） |
| 5 | **徽章链接落点不对** | Coverage 徽章指向 `pyproject.toml`（93.3% 的出处其实是 `docs/reports/phase1-execution-report.md`） | 改链接目标（§8 第 12 项） |
| 6 | **分享出去没有第一印象** | social preview 是 GitHub 自动卡片 | 做一张 1280×640 的自定义图并上传（§8 第 5 项） |
| 7 | **空标签页** | Wiki 开着但从未有内容；Discussions 关着 | 关掉 Wiki 或建首页；开 Discussions 并在 README 指路（§8 第 6、7 项） |
| 8 | **搜不到** | topics 缺 `apk` / `model-context-protocol` / `security` / `decompiler`；description 缺 `APK`、`static analysis`、`MCP`、`agent` | §8 第 1、2 项 |
| 9 | **中文版承诺比英文版强** | `README.zh-CN.md:5` 写 "Powered by AI Agents."（复数、无 bounded），`README.md:5` 写 "a bounded AI agent" | 改中文那行（§8 第 13 项）。同一项目两版对 agent 边界的措辞不同，是**文档一致性**问题，不只是文案 |
| 10 | **没有社会证明** | 0 stars / 0 forks / 0 watchers / 1 个 contributor / 30 次提交 | 不在元数据层可解。对个人项目来说正常，但意味着外部可见性几乎全靠搜索与主动分享——这也是为什么第 6、8 项值得做 |
| 11 | **homepage 无效** | `#readme` = 原地跳转 | §8 第 3 项 |

**一个必须说明的边界：** 以上没有一条是"能不能做"的问题，全是"说清楚了没有"的问题。
项目真正的短板不在仓库页——README 已经是这个体量的项目里少见的完整首屏、双语、带证据链文档。
真正的短板是**元数据与落盘事实之间的三处漂移**（许可证、Release 版本、报告份数），
它们让一个本来很扎实的项目在访客眼里露出"文档没跟上"的印象。

---

## 8. 建议改动清单（13 项）

**只列清单，本轮不执行任何一项。** 前 7 项是 GitHub 上的对外可见设置，由作者决定；
后 6 项是仓库内文件改动。标 ⚠️ 的项属于「对外可见」，建议在动手前先确认口径。

### A. GitHub 设置（7 项）

| # | 改动 | 怎么做 |
|---|---|---|
| 1 | ⚠️ About 区 description 换成 §6 候选 A（242 字符） | `gh repo edit gg320324492-lgtm/dexatlas --description "…"` |
| 2 | ⚠️ topics 补 4 个：`apk`、`model-context-protocol`、`security`、`decompiler` | `gh repo edit … --add-topic apk --add-topic model-context-protocol --add-topic security --add-topic decompiler` |
| 3 | ⚠️ homepage 改成 `docs/how-to-verify.md` 的绝对 URL（或开 Pages 后改指站点；或清空） | `gh repo edit … --homepage "https://github.com/gg320324492-lgtm/dexatlas/blob/main/docs/how-to-verify.md"` |
| 4 | ⚠️ 发布 `v1.0.0` 的 GitHub Release（正文用 `docs/releases/v1.0.0.md`，或 `docs/reports/v1.0.0-github-release-body.md` 裁掉附录后的版本） | `HTTPS_PROXY=http://127.0.0.1:7897 gh release create v1.0.0 --title "DexAtlas v1.0.0" --notes-file docs/releases/v1.0.0.md` |
| 5 | ⚠️ 上传自定义 social preview（1280×640 PNG，< 1 MB） | Settings → General → Social preview → Edit → Upload an image；复核用 `gh repo view … --json usesCustomOpenGraphImage` |
| 6 | ⚠️ 关掉空的 Wiki（或先建 wiki 首页再保留） | Settings → General → Features → Wiki |
| 7 | ⚠️ 开启 Discussions，并在 README「参与贡献」段指明去处 | Settings → General → Features → Discussions |

### B. 仓库内文件（6 项）

| # | 改动 | 怎么做 |
|---|---|---|
| 8 | **恢复规范 Apache-2.0 文本**：把 §4(d) 换回规范 15 行版本；附录版权行恢复为 `[yyyy] [name of copyright owner]`；实际版权声明移到新增的 `NOTICE` 文件（Apache-2.0 §4(d) 本就为此预留了机制）。改完 `gh api repos/…/license --jq .license.spdx_id` 应为 `Apache-2.0` | 重写 `LICENSE`；新增 `NOTICE` |
| 9 | 中文 README 补「怎么复核」入口 → `docs/how-to-verify.zh-CN.md`（该页已落地） | 改 `README.zh-CN.md` |
| 10 | 英文 README 把「How to verify every claim」上提到首屏可见处 | 改 `README.md` |
| 11 | 两份 README 各补一条 `docs/reports/README.md` 索引入口（与 `docs/reports/readme-map-audit.md` §7 重复，以那份为准） | 改 `README.md` / `README.zh-CN.md` |
| 12 | Coverage 徽章链接从 `pyproject.toml` 改指 `docs/reports/phase1-execution-report.md`（徽章数字不动——它由 `scripts/refresh-report-figures.py` 写，脚本只改数字不改链接） | 改两份 README 的徽章行 |
| 13 | `README.zh-CN.md:5` 的 "Powered by AI Agents." 改成与英文版一致的 "a bounded AI agent" | 改 `README.zh-CN.md` |
| — | （附）`docs/reports/README.md` 自称"三十七份"，实际已是 43 份（本文件加入后 44 份） | 同 `docs/reports/readme-map-audit.md` 的清单 |

---

## 附录 A：只读核查命令与门禁结果

**元数据（全部只读）**

```bash
gh repo view gg320324492-lgtm/dexatlas --json name,description,homepageUrl,repositoryTopics, \
  defaultBranchRef,visibility,isPrivate,licenseInfo,hasIssuesEnabled,hasWikiEnabled, \
  hasDiscussionsEnabled,openGraphImageUrl,usesCustomOpenGraphImage,latestRelease
gh api repos/gg320324492-lgtm/dexatlas --jq '{description,homepage,topics,default_branch,visibility, \
  private,has_issues,has_wiki,has_discussions,has_pages,license,stargazers_count,forks_count,open_issues_count}'
gh api repos/gg320324492-lgtm/dexatlas/license --jq '{spdx_id:.license.spdx_id,name:.license.name,key:.license.key}'
gh api repos/gg320324492-lgtm/dexatlas/releases --jq '.[] | {tag_name,draft,prerelease,published_at,assets:(.assets|length)}'
gh api repos/gg320324492-lgtm/dexatlas/git/refs/tags --jq '.[].ref'
gh api repos/gg320324492-lgtm/dexatlas/contents  # 目录清单
git ls-remote https://github.com/gg320324492-lgtm/dexatlas.wiki.git   # → Repository not found
```

**仓库内事实**

```bash
git tag -l --format='%(refname:short) %(creatordate:iso) %(objecttype)'
git rev-parse main v1.0.0^{commit}      # 两者同为 8f9ddcaf…
diff <(gh api repos/github/choosealicense.com/contents/_licenses/apache-2.0.txt --jq .content | tr -d '\n' | base64 -d) LICENSE
```

**只读门禁结果（2026-11-17，本 worktree，`claude/github-repo-metadata-2cd529`）**

| 门禁 | 结果 |
|---|---|
| `python scripts/check-doc-citations.py` | `citations: 221`（162 命名符号 / 59 仅指位置），`unresolved paths: 0`，`drifted: 0` —— exit 0 |
| `python scripts/check-version-claims.py --base auto` | `findings: 2 (2 already in 8f9ddcaf)`：`docs/releases/v0.2.0.md:326` 与 `CHANGELOG.md:1033` 的历史覆盖率数字 —— **本轮未引入**，且不是本报告的范围 |
| `pytest tests/test_docs.py` | 未跑，且**无法在本 worktree 跑**：hard constraint 禁止 `uv sync`，本 worktree 没有 `.venv`，系统 Python 是 3.10.11（项目要求 3.12+）且未安装 pytest。本轮只新增了一个 `.md`，不触及 `src/`，故未触发 CLAUDE.md 规则 4 的引用重锚 |

**未做的事（逐条对照 hard constraint）**：没有 `gh repo edit`；没有创建 Release；没有上传文件或图片；
没有打 tag；没有推送；没有运行 `pytest --cov` / `coverage` / `uv sync` / `scripts/refresh-report-figures.py`；
没有写入 `E:\Dexatlas` 共享树；报告中不含任何 token 或 key（`openGraphImageUrl` 是 GitHub 公网 CDN 地址，非凭据）。
