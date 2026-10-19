<div align="center">

# DexAtlas

**From APK to Evidence — Powered by AI Agents.**

开源、证据优先的 Android 逆向工程与移动应用分析平台。

</div>

DexAtlas 把 Android 反编译、程序分析、AI Agent 与自动化能力整合进一套模块化、可复现的
工作流，面向开发者、安全研究员，以及对自己拥有或已获授权的应用进行分析的工程师。

> [!IMPORTANT]
> **当前状态：早期开发（Phase 1 — 基础能力）。** CLI、分析内核与报告流水线正在构建中。
> Agent 编排、MCP 与 Web 工作台属于**规划中**的能力，尚未实现——详见
> [路线图](#路线图)。本文档不会声称任何尚未实际可运行的功能。

<p align="center">
  <img src="docs/assets/demo-quick.gif" alt="DexAtlas 分析内置演示 APK：后端发现、分析摘要、manifest 中的导出组件，以及报告中的证据等级" width="900">
</p>

上面每一帧都是针对 [`examples/demo-app/demo.apk`](examples/demo-app/) 的真实运行结果——
该应用由同目录下的 smali 源码构建而成，不是预先编排的录像。

<details>
<summary><b>完整流程</b> —— 代码检索、方法交叉引用、反编译源码与报告</summary>

<p align="center">
  <img src="docs/assets/demo.gif" alt="DexAtlas 完整会话：代码检索、方法交叉引用、反编译的 Java 源码以及生成的分析报告" width="900">
</p>

</details>

---

## 为什么是 DexAtlas？

传统 Android 逆向意味着在 JADX、Apktool、十六进制编辑器和一份记录笔记的表格之间反复切换，
再手工追踪每条结论究竟来自哪个方法。证据散落在各个工具里，会话一结束就消失了。

DexAtlas 要解决的正是这个问题：

- **统一的 Android 分析**——反编译、APK 资源、DEX 元数据与代码导航收敛到同一套接口，
  同时保留各后端的原始输出。
- **证据优先的结论**——每条发现都带有来源工具、工具版本、项目哈希与精确代码位置。
  无法点回原处的结论，不算结论。
- **面向自动化**——CLI 与 REST API 共用同一个分析内核，让分析结果可在 CI 中复现，
  而不是每次手工重敲一遍。
- **为 Agent 而生的架构**——标准化的工具接口与结构化 JSON，是 Phase 2 中 AI Agent 将要消费的
  契约，从第一天就按这个目标设计。
- **可扩展的设计**——分析后端是统一接口之后的适配器，新增引擎无需重写内核。

## 原则

1. 证据优于推测。
2. 可复现性优于炫技演示。
3. 模块化工具优于紧耦合框架。
4. 敏感操作需要人工确认。
5. 开放协作，透明评估。

## 路线图

| 阶段        | 版本      | 主题           | 范围                                                                                              |
| ----------- | --------- | -------------- | ------------------------------------------------------------------------------------------------- |
| **Phase 1** | `v0.1.0`  | 基础能力建设   | APK 导入、JADX/Apktool/Androguard 后端、统一索引、代码检索、CLI、REST API、JSON/Markdown 报告      |
| **Phase 1** | `v0.1.1`  | 基础能力加固   | 修复了此前对任何 APK 都从未生效过的 Smali 回退                                                    |
| **Phase 2** | `v0.5.0`  | Agent 智能分析 | Agent 任务规划、MCP Server、证据校验、可恢复任务、React 工作台                                       |
| **Phase 3** | `v1.0.0`  | 生产级开源平台 | Native（Ghidra）与动态（Frida）分析、插件生态、HTML/PDF 报告、公开 Benchmark                        |

完整内容、退出清单与评审机制：**[docs/roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md)**。

阶段推进依据证据而非日历。每个阶段以一次源码评审结束，下一阶段的任务清单由评审结果
推导而来，而非照搬既有假设。

## 架构

```text
APK 导入 ──► 哈希 + 校验 ──► 任务调度器
                                 │
               ┌─────────────────┼─────────────────┐
               ▼                 ▼                 ▼
             JADX             Apktool          Androguard
        （Java 伪代码）    （Manifest/Smali）  （DEX 元数据/交叉引用）
               └─────────────────┼─────────────────┘
                                 ▼
                         统一符号索引
                                 ▼
                  代码检索 / 方法引用查询
                                 ▼
                           证据关联
                                 ▼
                    JSON / Markdown 报告
```

外部分析引擎以**独立进程**方式调用，绝不内嵌或随仓库分发。它们的输出保持原生形态——
DexAtlas 统一的是索引与元数据接口，而不是抹平不同表示之间的差异。JADX 无法可靠反编译的
方法会被标注为错误，并保留回退到 Smali 的能力。

```
src/dexatlas/
├── core/          模型、索引、证据、存储、流水线
├── tools/         jadx/、apktool/、androguard/ 适配器
├── api/           FastAPI 应用
├── cli/           Typer 应用
├── reports/       JSON / Markdown 渲染器
└── config/        配置与后端工具发现
```

## 快速开始

完整说明（含后端安装与故障排查）：**[docs/install.md](docs/install.md)**。

```bash
git clone https://github.com/gg320324492-lgtm/dexatlas.git
cd dexatlas
uv sync --extra analysis

uv run dexatlas backends              # 哪些后端可用、版本号是多少
uv run dexatlas analyze app.apk -o report.md --json report.json
uv run dexatlas manifest  <project-id>
uv run dexatlas search   <project-id> "yourTerm"
uv run dexatlas xrefs    <project-id> "com.example.Foo.bar(Ljava/lang/String;)V"
```

REST API 是同一套分析内核的 HTTP 接口：

```bash
uv run uvicorn dexatlas.api.app:app --reload
# 交互式文档：http://localhost:8000/docs
```

**后端是可选且互相独立的。** DexAtlas 会报告它用现有后端能做什么，并把做不到的部分
作为证据记录进报告。一个后端都不装时，仍能得到哈希、校验和 APK 自身元数据；三个都装
时，则能获得完整的符号索引、反编译源码和交叉引用。

Docker 镜像已预装 JADX 与 Apktool：

```bash
docker build -t dexatlas . && docker run --rm dexatlas dexatlas backends
```

仓库内已附带一个演示应用，无需下载任何东西：

```bash
uv run dexatlas analyze examples/demo-app/demo.apk -o report.md
```

它由 [`examples/demo-app/`](examples/demo-app/) 下的 smali 源码构建而成，可用
`scripts/build-demo-apk.sh` 重新构建——不是来历不明的二进制文件。体积更大的测试样本
则通过 `scripts/fetch-fixtures.sh` 获取。

## 文档

- **[安装指南](docs/install.md)** —— 每条命令都在全新克隆上验证过
- **[架构说明](docs/architecture/README.md)** —— 项目如何组织，以及为什么这样设计
- **[路线图](docs/roadmap/ROADMAP.md)** —— 三个阶段与当前位置

Phase 1 剩余工作（源码评审，以及由评审结论写出的任务清单）见
[issue #1](https://github.com/gg320324492-lgtm/dexatlas/issues/1)。

## 参与贡献

欢迎提交 Issue、Bug 报告与 Pull Request——详见 [CONTRIBUTING.md](CONTRIBUTING.md)。
当前以 `v0.1.0` milestone 为准，其中 8 个 Phase 1 任务是进行中的工作清单。

请勿提交包含 APK、反编译源码，或任何来自你无权分析的应用程序的代码。参见
[SECURITY.md](SECURITY.md)。

## 预期用途

DexAtlas 用于教育、经授权的软件分析、移动应用安全评估与防御性研究。

本平台不授权访问任何第三方应用、账户、服务或数据。签名伪造、许可证绕过、保护机制
规避与未授权数据提取被明确列为**非目标**——它们不是功能，不是卖点，也不会出现在演示中。

## 许可证

[Apache-2.0](LICENSE)。第三方分析引擎以独立进程方式调用，不随本项目分发；审计说明见
[路线图](docs/roadmap/ROADMAP.md#license)中的许可证章节。
