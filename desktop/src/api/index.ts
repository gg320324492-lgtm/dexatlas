/**
 * API 桥接层出口 — Q2-M2-A。
 *
 * 页面统一从这里 import：`import { dexatlas } from "../api"`。
 * 类型与实现分开导出，方便只取类型的组件做 tree-shaking。
 */

export { DexAtlasClient, ApiError, dexatlas } from "./client";
export type { DexAtlasClientOptions } from "./client";

export type {
  AnalyzeJob,
  BackendInfo,
  CancelResponse,
  Evidence,
  EvidenceKind,
  EvidenceLevel,
  EvidenceList,
  HealthInfo,
  ProjectDetail,
  ProjectStatus,
  ProjectSummary,
  Provenance,
  ReportFormat,
  ReportPayload,
  RunCompleteness,
  RunInfo,
  RunList,
  RunStatus,
  ToolErrorInfo,
  ToolErrorCode,
} from "./types";
