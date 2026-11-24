/**
 * 页面共享类型 — Q2-M1 三个核心页面用。
 * 当前为受控 mock 数据形状；后续窗口接真实后端时保持字段名不变即可替换数据源。
 * 对应 docs/roadmap/phase4-q2-supplement.md §2.2（信息结构）。
 */

/** 项目状态徽章语义 */
export type ProjectStatus = "idle" | "running" | "done" | "partial" | "error";

/** 最近项目条目（首页列表） */
export interface ProjectSummary {
  id: string;
  name: string;
  /** 展示用包名，如 com.example.app */
  packageName: string;
  /** 文件大小，展示字符串，如 "12.4 MB" */
  sizeLabel: string;
  /** ISO 日期或相对时间展示字符串 */
  updatedLabel: string;
  status: ProjectStatus;
  /** 证据数量，done/partial 时有值 */
  evidenceCount?: number;
}

/** 分析阶段 id（§2-3：左侧阶段进度） */
export type StageId = "collect" | "parse" | "index" | "evidence" | "report";

export type StageState = "pending" | "running" | "done" | "error" | "skipped";

export interface StageInfo {
  id: StageId;
  label: string;
  /** 一句话说明该阶段做什么 */
  description: string;
}

/** 阶段 + 当前状态（分析页左侧时间线） */
export interface StageProgress {
  stage: StageInfo;
  state: StageState;
  /** 已用时间展示字符串，如 "00:12" */
  elapsedLabel?: string;
}

/** 日志级别（分析页中间日志区） */
export type LogLevel = "info" | "debug" | "warn" | "error" | "success";

export interface LogEntry {
  id: number;
  /** HH:MM:SS */
  timeLabel: string;
  level: LogLevel;
  /** 产生日志的阶段，如 "解析" */
  source: string;
  message: string;
}

/** 单个后端工具的运行状态（分析页右侧面板） */
export type BackendState = "queued" | "running" | "done" | "error" | "skipped";

export interface BackendStatus {
  /** JADX / Apktool / Androguard */
  name: string;
  state: BackendState;
  detail: string;
  /** 进度 0-100；queued 时可为 undefined */
  progress?: number;
}

/** 证据种类（详情页左列） */
export type EvidenceKind = "symbol" | "string" | "permission" | "component" | "sink";

export interface EvidenceItem {
  id: string;
  kind: EvidenceKind;
  /** 展示标题，如类名/方法名/权限名 */
  title: string;
  /** 次要说明，如所属类或出现位置 */
  subtitle?: string;
  /** 关联的后端来源 */
  origin: "jadx" | "apktool" | "androguard";
}

/** locator：可跳回来源的定位串（§1-3 证据链可复核） */
export interface EvidenceLocator {
  /** 如 "classes/com.example.app/MainActivity.smali" 或 "MainActivity.java:42" */
  path: string;
  /** 行号，源码视图用 */
  line?: number;
}

/** 证据详情（详情页右侧抽屉内容） */
export interface EvidenceDetail extends EvidenceItem {
  summary: string;
  locator: EvidenceLocator;
  /** 证据正文片段（模拟源码/调用图上下文） */
  snippet: string;
  /** 关联的其他证据 id */
  relatedIds: string[];
}

/** 详情页中间主体视图模式 */
export type DetailViewMode = "source" | "callgraph";

/** 源码预览行 */
export interface SourceLine {
  /** 1-based 行号 */
  line: number;
  text: string;
  /** 该行被证据引用时高亮 */
  highlighted?: boolean;
}
