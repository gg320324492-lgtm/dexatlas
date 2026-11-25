/**
 * API 桥接层出口 — Q2-M3-T1 统一入口。
 *
 * 页面统一从这里 import：`import { dexatlas, downloadText } from "../api"`。
 * 类型与实现分开导出，方便只取类型的组件做 tree-shaking。
 */

export { DexAtlasClient, ApiError, describeError, dexatlas, downloadText } from "./client";
export type { DexAtlasClientOptions } from "./client";
export {
  loadBackendCommandConfig,
  saveBackendCommandConfig,
  getSidecarStatus,
  isTauriRuntime,
} from "./sidecar";
export type { BackendCommandConfig, SidecarStatus, SaveOutcome } from "./sidecar";

export type {
  AnalyzeAccepted,
  AnalyzeJob,
  BackendInfo,
  CancelResponse,
  Completeness,
  CompletenessError,
  EvidenceKind,
  EvidenceLevel,
  EvidenceList,
  EvidenceRecord,
  HealthInfo,
  LocatorResolution,
  ProjectDetailEnvelope,
  ProjectStatus,
  ProjectSummary,
  ReportFormat,
  RunInfo,
  RunsEnvelope,
  SymbolHit,
  UntrustedText,
  WorkbenchHealth,
} from "./types";
