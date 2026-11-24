# DexAtlas Studio（桌面应用）

DexAtlas 的原创桌面应用，技术栈：**Tauri 2 + React 19 + TypeScript + Vite**。
产品决策与验收标准见 `docs/roadmap/phase4-q2-supplement.md`。

## 结构

| 路径 | 说明 |
| --- | --- |
| `src/` | React 前端（路由、页面骨架、样式 token） |
| `src/styles/tokens.css` | 设计 token：颜色 / 圆角 / 阴影 / 间距 / 字体 |
| `src-tauri/` | Tauri Rust 壳与 `tauri.conf.json` |

页面：首页（拖拽上传 + 最近项目）、分析（阶段进度 / 实时日志 / 后端状态）、
证据、报告、设置。当前为结构与样式骨架，复杂交互由后续里程碑接入。

## 运行

```bash
npm install          # 在 desktop/ 内执行
npm run dev          # 仅前端（Vite，端口 5173）
npm run build        # 前端类型检查 + 产物构建
npm run tauri dev    # Tauri 桌面窗口（开发模式）
npm run tauri build  # 桌面应用打包
```

依赖安装在 `desktop/node_modules`，Rust 构建产物在 `desktop/src-tauri/target`，
均不入库。
