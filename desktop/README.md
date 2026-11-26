# DexAtlas Studio（桌面应用）

DexAtlas 的原创桌面应用，技术栈：**Tauri 2 + React 19 + TypeScript + Vite**。
产品决策与验收标准见 `docs/roadmap/phase4-q2-supplement.md`；侧车接入与
阶段级进度的阶段目标见 `docs/roadmap/phase5-plan.md`（W1/W2），验收记录见
`docs/reports/phase5-acceptance.md`（**安装形态已真机验证**，见该报告 §2；仍然
开放的边界见其 §7）。

## 结构

| 路径 | 说明 |
| --- | --- |
| `src/` | React 前端（路由、页面骨架、样式 token） |
| `src/api/` | REST 客户端（baseUrl 跟随侧车实际端口）与侧车桥接 |
| `src/styles/tokens.css` | 设计 token：颜色 / 圆角 / 阴影 / 间距 / 字体 |
| `src-tauri/` | Tauri Rust 壳、侧车进程管理与 `tauri.conf.json` |

页面：首页（拖拽上传 + 最近项目）、分析（阶段进度 / 实时日志 / 后端状态）、
证据、报告、设置。分析能力全部来自现有 Python 核心（`src/dexatlas/`），
桌面壳不复制分析逻辑、不新增公共契约。

## 侧车进程（Phase 5 W1）

应用启动时，Rust 壳按配置拉起现有 DexAtlas 后端作为**侧车进程**：

- 默认命令 `python -m dexatlas.workbench --port 0`（端口由系统分配）；
- 可在设置页修改后端命令与参数，写入 Tauri 本地配置
  `%APPDATA%\io.github.dexatlas.desktop\backend.json`；
- 壳从后端输出里抓取实际监听端口，通过 `get_sidecar_status` 命令与
  `sidecar:status` 事件告知前端，并为该端口动态放行 HTTP capability；
- 后端退出/崩溃时前端如实显示错误（不造数据）；应用退出时结束整棵
  后端进程树。

**后端不会比宿主活得更久。** 结束后端有三层，一层比一层兜得住：

1. 应用正常退出时，`RunEvent::Exit` 里主动按进程树 kill；
2. 状态被丢弃（应用退出、事件循环异常返回）时，`SidecarState::drop` 兜底；
3. 宿主被 `taskkill /F` **强杀**时，前两层一行也跑不了——Windows 的
   **作业对象**（Job Object）接手：后端在执行第一条指令之前就被放进一个带
   `KILL_ON_JOB_CLOSE` 的作业，宿主进程一死（正常退出、崩溃、被强杀都一样，
   系统会关闭它的全部句柄），作业里的整棵进程树随之被终止。

第 3 条的"第一条指令之前"不是修辞：venv 里的 `python.exe` 是个转发器，它会
再拉起真正的解释器（实测进程树是 exe → venv python → 真解释器），所以后端
必须**挂起创建**（`CREATE_SUSPENDED`）→ 加入作业 → 再恢复主线程，它自己拉出来
的后代才会继承作业身份。否则强杀之后留下的恰恰是那个真正在监听端口的
孙进程。约定见 `docs/architecture/desktop-app.md` §8.1，实现见
`desktop/src-tauri/src/sidecar.rs`。

**工作目录是可选的。** 仓库形态下壳从 exe 位置反推仓库根作为后端工作目录
（`python -m dexatlas.workbench` 需要它才能找到包）；**安装形态反推不出仓库
根时不设工作目录，照样启动**——此时后端命令应当是绝对路径（如 venv 里的
`python.exe`）。起不来时状态里的原因会点名是"命令不在 PATH"还是"那个路径
不存在"，并在设置页给出可执行的下一步。

**端口是事件，不是常量。** 侧车端口由系统分配且在启动之后才存在，所以前端：

- 首次请求前**有界等待**端口出现（壳报告"后端起不来"时立即结束等待）；
- 之后由 `sidecar:status` 事件驱动，端口出现或变化就重新解析 baseUrl；
- 拿不到端口时回退 `http://127.0.0.1:8618/api`（老壳 / 非 Tauri 环境），
  但回退**不是终态**——端口后来出现仍会改写。

dev 浏览器模式走 vite 代理（`/api`），不涉及端口。

**已知边界：** 默认侧车命令是开发形态（`python -m dexatlas.workbench`，工作
目录从 exe 路径上溯找含 `src/dexatlas` 的仓库根）。安装到 Program Files 的
打包产物没有这个仓库根——但**这不是问题**：侧车的工作目录是**可选**的，
推断不出仓库根时照样 spawn，只是**不设 cwd**（PR #20 修掉了此前用短路写法
导致「推断失败 = 根本不启动」的那个缺陷）。真机验收时后端命令配成绝对路径
（`E:\DexAtlas\.venv\Scripts\python.exe -m dexatlas.workbench`）。

**安装形态已真机验证**（`docs/reports/phase5-acceptance.md` §2）：NSIS 安装器
静默安装后启动 exe，侧车自动拉起并监听**自己的端口**（实测 64074），前端
请求打在那个端口上而不是 8618 回退端口——验收全程 8618 无任何监听。上传 →
分析 → 证据 → 导出全链路可用；杀掉侧车后页面显示可读错误而不是白屏；正常
关闭 exe 后整棵进程树被清理。**仍然开放**的边界见该报告 §7（macOS/Linux
不纳入、打包 exe 未跑装了 jadx + apktool 的配置、MSI 安装路径未验证等）。

## 阶段级进度（Phase 5 W2）

后端为每个分析 run 记录 pipeline 阶段事件（`inspect` → `parse-apktool` →
`index-androguard` → `decompile-jadx` → `publish`），桌面分析页轮询只读端点：

```text
GET /api/projects/{project_id}/runs/{run_id}/stages
→ {project_id, run_id, run_status, stages:[{stage, started_at, finished_at}]}
```

- 有 `stages` 时时间线按真实事件渲染；旧 run 没有阶段事实时按 `run.status`
  的粗粒度映射，角标如实标注「后端 run 状态」。前端时间模拟已删除：没有
  任何 run 数据时五格如实显示「待处理」（状态未知），runs 请求失败时显示
  「后端不可用，阶段进度无法取得」并提供重试。
- `finished_at` 为 null 表示该阶段尚未结束：可能正在进行，也可能是 run
  失败/被取消时停在那一阶段。
- 这是**独立只读端点**，既有 run 对象（REST `RunResponse` / workbench
  `RunSummary`）不携带 `stages`，字段集与此前一致。REST 侧的同一端点是
  `GET /projects/{pid}/runs/{rid}/stages`。

## 运行

```bash
npm install          # 在 desktop/ 内执行
npm run dev          # 仅前端（Vite，端口 5173）
npm run build        # 前端类型检查 + 产物构建
npm run test         # 桌面端单元测试（vitest）
npm run test:watch   # 同上，改成监听模式
npm run tauri dev    # Tauri 桌面窗口（开发模式，自动拉起侧车后端）
npm run tauri build  # 桌面应用打包
```

Windows 上 Rust 构建需要 MSVC 环境：在 cmd 里先
`call "E:\VS2022BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64`
（路径按本机 Build Tools 安装位置调整），再执行 `cargo check` /
`npm run tauri dev`。

## 测试

桌面前端的单元测试用 **vitest**，测试文件在 `src/` 旁边（`src/**/*.test.ts`）：

```bash
npm run test         # 跑一遍
npm run test:watch   # 监听
```

被测的是纯逻辑那一层——阶段映射（`src/stages.js`）、locator 落点分类
（`src/locators.ts`）、侧车端口解析（`src/api/sidecarEndpoint.ts` 与
`src/api/client.ts`）。断言的是**行为**（函数返回什么、baseUrl 变没变），
不是源码里有没有某个字符串。

纯函数测试不开 DOM 环境，所以不必装 happy-dom / jsdom；要渲染组件时再在那个
测试文件上加 `// @vitest-environment jsdom`。

这些测试由 CI 的 `desktop` job 跑（`npm ci` → `npm run build` → `npm run test`）；
`npm run build` 里的 `tsc --noEmit` 也会把测试文件一起类型检查一遍。

依赖安装在 `desktop/node_modules`，Rust 构建产物在 `desktop/src-tauri/target`，
均不入库。
