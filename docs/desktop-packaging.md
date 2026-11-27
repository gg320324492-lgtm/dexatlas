# 桌面应用的打包：版本号与修复路径

**最后更新：** 2026-11-27 · **对应版本：** v1.2.0

这份文档回答三个问题：

1. **版本号**——安装包、exe、设置页上的数字各是谁的版本；
2. **修复路径**——装好的东西坏了（快捷方式被删了、文件坏了）怎么修得回来；
3. **怎么自己验**——上面两条怎么复验。

打包用的 WiX 模板是本仓库自己的分支（`desktop/src-tauri/wix/main.wxs`），
不是 tauri-bundler 的原版。分支的原因与改动见 §2.3。

---

## 1. 版本号

### 1.1 三个地方，三个不同的东西

| 地方 | 它说的是什么 | 从哪来 |
|---|---|---|
| 设置页「应用版本」 | 这个桌面应用（exe / MSI 安装包）**自己**的版本号 | Tauri 壳的 `app_info` 命令 → `desktop/src-tauri/Cargo.toml` 的 `version` |
| 设置页「后端版本（分析核心）」 | 侧车分析核心（Python）的版本号 | `GET /api/health` 的 `version` → `src/dexatlas/__init__.py` 的 `__version__` |
| MSI 的 `ProductVersion` | 安装包的版本号 | `desktop/src-tauri/tauri.conf.json` 的 `version` |
| exe 的文件版本（资源管理器 → 属性） | 桌面应用的版本号 | `desktop/src-tauri/Cargo.toml` 的 `version` |

**为什么以前会认错：** 设置页原来只有一条写着「版本」的行，填的是**后端**的号。
装出来的是 DexAtlas Studio 1.2.0，页面上写的却是分析核心的版本号，读者会把
它当成这个应用的版本。现在分成两行，各说各的是谁的版本（`desktop/src/pages/settingsVersion.ts`）。

### 1.2 数字从哪来，谁跟着谁

**发版号只有一处：** `src/dexatlas/__init__.py` 的 `__version__`。
`scripts/check-version-claims.py` 判断文档里「最新版本是 v1.2.0」时读的就是它。

桌面上带着版本号的文件有四个，它们必须与发版号一致：

| 文件 | 它带着什么 |
|---|---|
| `desktop/package.json` | npm 包的版本 |
| `desktop/src-tauri/tauri.conf.json` | 应用版本，**MSI 的 `ProductVersion` 从这里来** |
| `desktop/src-tauri/Cargo.toml` | crate 版本，即 exe 的文件版本资源 |
| `desktop/src-tauri/Cargo.lock` | 同上 |

改版本号的命令：

```bash
uv run --no-sync python scripts/sync-desktop-version.py           # 写入
uv run --no-sync python scripts/sync-desktop-version.py --check   # 只检查，不一致时退出码 1
```

`tests/test_desktop_version.py` 是这件事的门禁：四个文件里任何一个跟发版号对不上，
测试就红。手改其中一个而不改其余的，CI 会拦下来。

### 1.3 待拍板：桌面的版本号要不要跟着发版号走

**这个问题还没有作者拍板。** 代码与本文档现在按 **A** 实现——因为「MSI 的
`ProductVersion` 要跟着发版号走」是这次的要求，而 A 是满足它的最直接做法。
这一节把另外两种做法与各自的代价摆出来，供作者决定；改成 B 或 C 是一次
有意的改动，不是一次漂移。

| 做法 | 好处 | 代价 |
|---|---|---|
| **A. 完全跟随发版号**（现状） | 一个数字贯穿 exe、MSI、设置页、发布说明；升级路径一次说清 | 桌面端跟着核心一起发版，核心发版即桌面发版；桌面端的独立节奏没有了 |
| B. 桌面端自己的号（与发版号并行） | 两边能各自发版 | 读者面前出现两个号；「这是第几版 DexAtlas」变成一道题；升级路径要说明两个号怎么对应 |
| C. 桌面端号 = 发版号 + 后缀（如 `1.2.0-desktop.1`） | 能看出桌面端有自己的迭代 | MSI 的 `ProductVersion` 只吃数字与数字段，后缀进不去；要另想办法写进 `ProductName` 或 ARP 显示名，读者仍可能只看到一半 |

若要改成 B 或 C，改的是 `desktop/src-tauri/tauri.conf.json`、
`desktop/package.json`、`desktop/src-tauri/Cargo.toml` 与
`tests/test_desktop_version.py` 里那条「四处一致」的断言——
`scripts/sync-desktop-version.py` 也随之要改。

---

## 2. 修复路径

### 2.1 缺陷（2026-11-27 真机复验）

装好 MSI 之后删掉安装目录里的 `Uninstall DexAtlas Studio.lnk`，再跑
`msiexec /fa <msi>`：退出码 0，exe 修回来了，**那个快捷方式没有回来**。

安装日志里该找的是这个：**一条 `ShortcutCreate` 操作都没有**。
（`CreateShortcuts` 动作的 `Return value 1` 不能当证据——它重建了快捷方式时
返回的也是 1。上一轮复验把它读成「被跳过」，那一步是错的。）

### 2.2 是什么决定快捷方式能不能被修回来

同一台机器、同一份 MSI，只改重装模式的三组对照（2026-11-27）：

| 命令 | 生效的 `REINSTALLMODE` | 快捷方式回来了吗 | 日志里的 `ShortcutCreate` |
|---|---|---|---|
| `msiexec /fa` | `a` | **没有** | 0 条 |
| `msiexec /fas` | `as` | **回来了** | 3 条 |
| `msiexec /fa`（exe 也删了） | `a` | **没有** | 0 条 |

两件事由此确定：

1. **决定因素是 `REINSTALLMODE` 里的 `s` 标志**（"re-install shortcuts"），
   不是快捷方式所在组件的 KeyPath。第三组对照是为此专门做的：先把卸载快捷方式
   并进以 exe 为 KeyPath 的组件，`/fa` 仍然修不回——KeyPath 不是原因。
2. **标志必须在成本计算之前就位**。「哪些快捷方式要重建」是在
   `CostInitialize`/`FileCost`/`CostFinalize` 阶段定下来的，
   `CreateShortcuts` 动作只是照着做。把标志补在 `CostFinalize` 之后
   （实测：属性值确实变成了 `as`）已经太晚，快捷方式仍然修不回。

而 `msiexec /fa` 会把 `REINSTALLMODE` 设成 `a`——这个值在安装序列开始之前
就写进了属性，属性表里的 `amus` 顶不住它（给属性加 `Secure="yes"` 也一样，
实测最终值仍是 `a`）。

雪上加霜的是 `ARPNOREPAIR=yes`：它把控制面板（程序和功能）里的「修复」入口关掉了，
用户只剩命令行一条路，而命令行这条路当时也修不回来。

### 2.3 现在怎么修得回来

三处改动：

| # | 改动 | 做了什么 | 是修好快捷方式的原因吗 |
|---|---|---|---|
| 1 | `ReinstallShortcutsToo` 自定义动作，排在 `CostInitialize` 之前 | 把用户给的重装模式后面补一个 `s`（`[REINSTALLMODE]s`），保留用户给的口径（`/fp`、`/fv`……），只补「重装快捷方式」这一条 | **是**（实测） |
| 2 | 卸载快捷方式并进 `Path` 组件 | 组件的 KeyPath 从注册表值换成**文件**（exe）。上游那个组件是 per-user 的（KeyPath 在 HKCU），却把快捷方式写进 per-machine 的安装目录 | 不是（实测）。留下它是因为组件的状态与快捷方式的去留不再脱节 |
| 3 | 删掉 `ARPNOREPAIR` | 控制面板的「修复」入口回来 | 与快捷方式无关，是让修复这条路存在 |

改动 1 对**三个**快捷方式都管用：开始菜单与桌面的快捷方式在用户的配置文件里，
不能放进 per-machine 组件（ICE57 禁止一个组件同时装 per-machine 的文件和
per-user 的快捷方式），而 `s` 标志重建的是 `Shortcut` 表里的全部快捷方式。

`ARPNOMODIFY=1` **保留**：这个安装包只有安装目录对话框（`WixUI_InstallDir`），
没有功能选择界面；放开「更改」等于让用户改安装目录，那是另一个产品决定，
不在这次修复范围内。**「修复」才是自愈路径，它必须开着。**

### 2.4 模板分支

`desktop/src-tauri/wix/main.wxs` 是 tauri-bundler 的 `main.wxs` 的分支，
基线是 tauri-bundler 2.9.0（`@tauri-apps/cli` 2.12.x 用的就是它）。
分支里只有上面那三处改动，文件头部的注释写明了每一处。

**升级 tauri 时**：先看 tauri-bundler 的模板有没有变，有变就把上游的改动合进来，
再跑 §3 的验证。合的时候不要把本分支的三处改动改回去。

---

## 3. 怎么自己验

### 3.1 重新打包

```bash
cd desktop
npm ci                 # 第一次
npm run tauri build    # 出 MSI：desktop/src-tauri/target/release/bundle/msi/
```

构建要从 `desktop/` 目录跑（`npm run tauri build` 的工作目录），
但 `tauri.conf.json` 里 WiX 模板的路径是相对 **`desktop/src-tauri/`** 解析的
（打包器从 Tauri 工程目录找它），所以写的是 `"template": "wix/main.wxs"`。

只想重出安装包、不想重编 Rust 时：

```bash
cd desktop
npx tauri bundle
```

### 3.2 验修复路径

这个安装包一共有三个快捷方式（per-machine 安装，所以开始菜单与桌面在**公共**目录下）：

| 快捷方式 | 位置 |
|---|---|
| 卸载 | `C:\Program Files\DexAtlas Studio\Uninstall DexAtlas Studio.lnk` |
| 开始菜单 | `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\DexAtlas Studio\DexAtlas Studio.lnk` |
| 桌面 | `C:\Users\Public\Desktop\DexAtlas Studio.lnk` |

```bash
# 1) 装上（提升的会话里；本机可用 Start-Process -Verb RunAs 静默拿提升令牌）
msiexec /i "<desktop>/src-tauri/target/release/bundle/msi/DexAtlas Studio_1.2.0_x64_en-US.msi" /qn /l*v install.log

# 2) 把三个都删掉
del "C:\Program Files\DexAtlas Studio\Uninstall DexAtlas Studio.lnk"
del "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\DexAtlas Studio\DexAtlas Studio.lnk"
del "C:\Users\Public\Desktop\DexAtlas Studio.lnk"

# 3) 修复
msiexec /fa "<同一份 msi>" /qn /l*v repair.log

# 4) 看两件事：文件回来了吗，日志里有没有 ShortcutCreate
dir "C:\Program Files\DexAtlas Studio\Uninstall DexAtlas Studio.lnk"
findstr /C:"ShortcutCreate" repair.log
```

日志里要看的三处：

- `Executing op: ShortcutCreate(...)` —— 应当**有三条**（开始菜单、桌面、卸载）；
  没有就是没修回来；
- `REINSTALLMODE` 的最终值（`/fa` 之后应当是 `as`：命令行给的 `a` 加上补上的 `s`）；
- `Property (S): ARPNOREPAIR` **不出现**（说明控制面板的修复入口是开着的）。

**2026-11-27 的实测结果**（`DexAtlas Studio_1.2.0_x64_en-US.msi`）：

- 三个快捷方式全删 → `msiexec /fa` 退出码 0 → **三个都回来了**，
  日志里 `ShortcutCreate` 三条（`DexAtlas Studio` ×2 + `Uninstall DexAtlas Studio` ×1）；
- 只删卸载快捷方式 → `/fa` → 回来了；`/fas` → 回来了；
  连 exe 一起删 → `/fa` → exe 与快捷方式都回来了；
- 升级路径：装旧的 0.1.0 再装 1.2.0，退出码 0，exe 的 `ProductVersion` 变成 1.2.0，
  卸载快捷方式在；装完注册表里 `NoRepair` 为空（上游那个包是 `NoRepair=1`）。

`CreateShortcuts` 动作的 `Return value` 是 **1**——它重建了快捷方式时返回的也是 1，
这个返回值不能拿来判断成败。

### 3.3 读 MSI 的表

想知道安装包里到底有什么，用 Windows Installer 的 COM 接口读表：

```powershell
$installer = New-Object -ComObject WindowsInstaller.Installer
$db = $installer.GetType().InvokeMember("OpenDatabase","InvokeMethod",$null,$installer,@("path\to.msi",0))
$view = $db.GetType().InvokeMember("OpenView","InvokeMethod",$null,$db,@('SELECT * FROM `Shortcut`'))
```

`File`、`Component`、`Shortcut`、`Property` 四张表就够说明 §2 的每一条。
建出来的 MSI 上应当看到：

- `Shortcut` 表里 `UninstallShortcut` 那一行的 `Component_` 是 `Path`；
- `Component` 表里 `Path` 的 `KeyPath` 是 `Path`（文件），不再是注册表值；
- `Property` 表里**没有** `ARPNOREPAIR`，`ProductVersion` 是发版号。
