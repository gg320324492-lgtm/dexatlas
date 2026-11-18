# GitHub social preview 图：怎么用

> 这份说明回答三件事：**这两张图怎么设成仓库的 social preview**（只能手动做，GitHub
> 没有 API）、**图上每一个字、每一个数是从哪个文件的哪一行读出来的**、以及**图上的数
> 怎么跟着报告走**（绘图脚本已入库，CI 里有一条检查守着）。

## 1. 图文件

| 项 | 英文版 | 中文版 |
|---|---|---|
| 路径 | `.github/social-preview.png` | `.github/social-preview.zh-CN.png` |
| 格式 | PNG、1280×640 | 同左 |
| 生成 | `scripts/make-social-preview.py` | 同左 |
| 挂在 | `README.md` 首屏 | `README.zh-CN.md` 首屏 |

图里没有渐变、没有阴影、没有装饰图形：这是一个文档工具的仓库，卡片要像文档而不像广告。

**一张图只用一种语言。** 英文卡片上的每一个标签都是英文的，中文卡片上的每一个标签都是
中文的——一张图上混着两种语言的标签，等于让一半的读者读不懂图上的数。

体积：几十 KB。确切字节数记在 `.github/social-preview.json` 的 `cards` 一节里，那条
记录由 §6 的检查核对过与文件一致；本文件不抄一个会过期的数。

![DexAtlas social preview 图](../../.github/social-preview.png)

![DexAtlas social preview 图（中文版）](../../.github/social-preview.zh-CN.png)

## 2. 设成 social preview（三步）

1. 打开仓库主页，点顶部的 **Settings**（只有仓库管理员能进）。
2. 左侧栏选 **General**，页面往下滚到 **Social preview** 一节。
3. 点 **Upload an image**，选本地的 `.github/social-preview.png`，上传后点 **Save**。

**这一步只能手动做**：GitHub 没有提供设置 social preview 的 REST/GraphQL 接口，`gh` CLI
也没有对应子命令。在浏览器里点完即生效。

换图之后 GitHub 会缓存旧图，分享链接里可能要过一段时间才看到新图。

## 3. README 里怎么用

英文 `README.md` 在徽章那一行之后写：

```html
<img src='.github/social-preview.png' alt='DexAtlas — From APK to Evidence' width='900'>
```

中文 `README.zh-CN.md` 写自己那一张：

```html
<img src='.github/social-preview.zh-CN.png' alt='DexAtlas — 从 APK 到可核查的证据' width='900'>
```

放在 `docs/` 下的文档里，路径要按文档所在目录相对写（`../../.github/social-preview.png`）。

（上面两段示例用单引号：文档自己的检查会把一段 HTML 里的 img 标签当成一张真的插图，
去按**本文档**的目录解析那个路径——而这里的路径是相对仓库根目录的 README 写的。
README 里用的是双引号，两种都合法。）

**alt 文本里不写数字。** 图上的数会随重测量变，而 alt 文本是手写的：数字写在里面，
就是一个比徽章更安静地过期的数。数字的出处由 §4 的表负责。

## 4. 图上每一句话的出处

| 图上的文字 | 落盘出处 | 说明 |
|---|---|---|
| `DexAtlas` | `README.md:3` | 仓库名，两份 README 同 |
| `From APK to Evidence` | `README.md:5` | 英文 tagline 的前半句，逐字 |
| `An open-source, evidence-first Android reverse engineering and mobile application analysis platform.` | `README.md:7` | 英文定位句，逐字 |
| `early development` | `README.md:50` | README 状态行里的成熟度说法 |
| `从 APK 到可核查的证据` | `README.zh-CN.md:5` | 中文 tagline 的前半句，逐字 |
| `开源、证据优先的 Android 逆向工程与移动应用分析平台。` | `README.zh-CN.md:7` | 中文定位句，逐字 |
| `93.3%` | `docs/reports/phase1-execution-report.md:77` | `<!--fig:coverage.pct-->` |
| `7135/7650 行` | `docs/reports/phase1-execution-report.md:77` | `<!--fig:coverage.covered-->` 与 `<!--fig:coverage.total-->` |
| `1644` | `docs/reports/phase1-execution-report.md:76` | `<!--fig:tests.total-->` |
| `1497 快 + 147 集成` | `docs/reports/phase1-execution-report.md:76` | `<!--fig:tests.fast-->` 与 `<!--fig:tests.slow-->` |
| `28 REST` | `scripts/verify-public-contracts.py:105` | `_rest_requests()` 里的检查调用点数 |
| `6 MCP` | `scripts/verify-public-contracts.py:355` | `mcp_checks()` 里的检查调用点数 |
| `15 CLI` | `scripts/verify-public-contracts.py:429` | `cli_checks()` 里的检查调用点数 |
| `49`（清单条数） | 上面三行之和 | 静态条数，不是任何一次实跑的通过数 |
| `11`（MCP 只读工具） | `src/dexatlas/mcp/server.py:105-328` | `server.tool` 的注册处数 |
| `Apache-2.0` | `pyproject.toml:10` | 许可证标识 |
| `v1.0.0` | `src/dexatlas/__init__.py:11` | 版本号的唯一来源 |

**图上的数字不是手抄的**：生成脚本直接解析上面这些文件（§5）。报告里的数字变了
（`scripts/refresh-report-figures.py` 写回），下一次生成的图就跟着变——而且 §6 的检查
会在这中间把漏掉的那一张揪出来。

**图上的标签是脚本自己的措辞**，中英各一套，在 `scripts/make-social-preview.py` 的
`LABELS` 字典里。这张表登记的是**数**的出处；标签的出处是那一个字典。

**「49」是清单的条数，不是接口的数量。** 那三个数是检查调用点的条数
（28 REST + 6 MCP + 15 CLI，合计 49 项），不是接口数：REST 端点另有其数（报告 §1.2 的
`<!--fig:api.endpoints-->`），MCP 工具另有其数（上表第 14 行）。

图上的副行因此写明是**检查项**的条数：英文是
「Static count: 28 REST + 6 MCP + 15 CLI checks」（合计 49 项），中文是
「静态条数：28 REST + 6 MCP + 15 CLI 项检查」（合计 49 项）。

## 5. 重新生成这两张图

脚本已入库：`scripts/make-social-preview.py`。

```bash
uv run --no-sync python scripts/make-social-preview.py
```

它做三件事：

1. 从落盘文件里解析要画的东西（§4 的表）；
2. 画两张图（英文、中文）；
3. 把画进去的那些数写进 `.github/social-preview.json`，连同两张图的 sha256。

字体是 Windows 自带的微软雅黑（`msyh.ttc` 与 `msyhbd.ttc`）：中文与拉丁字母出自同一
套字形。别的机器上没有这两个字体时，脚本会报错，并列出它找过哪些路径：

```
error: the social preview card needs a font, and none was found.
  missing: msyh.ttc (regular), msyhbd.ttc (bold)
  searched: C:/Windows/Fonts
```

用 `--font-dir /path/to/fonts`，或设环境变量 `DEXATLAS_PREVIEW_FONT_DIR`，指到有这两个
字体文件的目录即可。**检查模式（§6）不需要任何字体，也不需要 Pillow。**

画完脚本会打印每一行文字的坐标。哪一行越界——跑出画布，或超出它那一栏的宽度——脚本
就以非零码退出，并且不写图。

## 6. 检查：图上的数跟不跟得上报告

```bash
uv run --no-sync python scripts/make-social-preview.py --check
```

这条检查**不画图、不需要字体、不需要 Pillow**，所以它能在 Linux 的 CI 上跑。它断言六件事：

1. **旁证里的数 == 报告里的数**：`.github/social-preview.json` 里记的每一个数，都等于
   它被读出来的那份文件里现在的数。
2. **旁证里的出处 == 现在的出处**：数是从哪个文件读的，也记在旁证里；来源变了同样要重画。
3. **PNG 就是画进这些数的那一张**：两张图各自的 sha256 与旁证里记的一致。手改过图而没
   重画，哈希就对不上。
4. **徽章与卡片说同一个数**：两份 README 的测试数徽章等于 `<!--fig:tests.total-->`，
   覆盖率徽章等于 `<!--fig:coverage.pct-->`；测量记录里的通过数与收集数必须相等
   （不相等说明测量没做完——那正是徽章写一个数、卡片写另一个数的情形）。
5. **卡片的字还是 README 的字**：headline 与定位句与两份 README 现在的写法一致。
6. **两张图都挂在自己的首屏上**；契约表里写着的清单条数，与脚本里的检查调用点数一致。

CI 上跑的就是这一条（`.github/workflows/ci.yml` 的 `social-preview` job）。

**为什么不比 PNG 的字节。** 同一份代码在 Windows 与 Linux 上画出的 PNG 字节不同
（字体不同，元数据也不同），比字节等于只让画图的那台机器通过。比数才是可移植的：数在
CI 上可以复算，图只能在画它的机器上复现——所以图用哈希认领，数用断言守住。

## 7. 改图之后的清单

- [ ] 跑 `uv run --no-sync python scripts/make-social-preview.py`
- [ ] 跑 `uv run --no-sync python scripts/make-social-preview.py --check`（应退出 0）
- [ ] 打开两张图看一遍：没有截断、没有错行、没有混排
- [ ] 在仓库设置里重新上传 social preview（手动，见 §2）
- [ ] 提交 `.github/social-preview.png`、`.github/social-preview.zh-CN.png` 与
      `.github/social-preview.json` 三件

## 8. 本文件的引用也受检查

本文件在 `scripts/check-doc-citations.py` 的 `DOCS` 列表里：§4 表里的 `file:line`
逐条对着当前树核对，树动了就报错。重新定位用：

```bash
uv run --no-sync python scripts/remap-citations.py
```

它只移动检查器认定已经离开的引用；指向位置而非符号的引用留给检查器报告，留给人决定。
