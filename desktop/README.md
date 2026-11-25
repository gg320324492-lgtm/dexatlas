# DexAtlas Studio（桌面应用）

DexAtlas 的原创桌面应用，技术栈：**Tauri 2 + React 19 + TypeScript + Vite**。
产品决策与验收标准见 `docs/roadmap/phase4-q2-supplement.md`；侧车接入的
阶段目标见 `docs/roadmap/phase5-plan.md`（W1）。

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

前端请求 baseUrl 的解析顺序：Tauri 运行时优先用侧车实际端口；拿不到时
回退 `http://127.0.0.1:8618/api`；dev 浏览器模式走 vite 代理（`/api`）。

## 运行

```bash
npm install          # 在 desktop/ 内执行
npm run dev          # 仅前端（Vite，端口 5173）
npm run build        # 前端类型检查 + 产物构建
npm run tauri dev    # Tauri 桌面窗口（开发模式，自动拉起侧车后端）
npm run tauri build  # 桌面应用打包
```

Windows 上 Rust 构建需要 MSVC 环境：在 cmd 里先
`call "E:\VS2022BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64`
（路径按本机 Build Tools 安装位置调整），再执行 `cargo check` /
`npm run tauri dev`。

依赖安装在 `desktop/node_modules`，Rust 构建产物在 `desktop/src-tauri/target`，
均不入库。
