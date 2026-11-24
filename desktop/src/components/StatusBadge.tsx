import type { ReactNode } from "react";
import "./StatusBadge.css";

export type StatusKind = "completed" | "running" | "failed" | "partial" | "pending";

const kindLabel: Record<StatusKind, string> = {
  completed: "已完成",
  running: "进行中",
  failed: "失败",
  partial: "部分完成",
  pending: "待处理",
};

const kindIcon: Record<StatusKind, string> = {
  completed: "✓",
  running: "◌",
  failed: "✕",
  partial: "◐",
  pending: "•",
};

export interface StatusBadgeProps {
  kind: StatusKind;
  /** 覆盖默认中文文案 */
  label?: ReactNode;
  /** 带呼吸动画（进行中） */
  pulse?: boolean;
}

/** 状态徽章：五态覆盖 completed / running / failed / partial / pending。 */
export function StatusBadge({ kind, label, pulse = false }: StatusBadgeProps) {
  return (
    <span className={["da-badge", `da-badge--${kind}`, pulse && kind === "running" ? "da-badge--pulse" : ""].filter(Boolean).join(" ")}>
      <span className="da-badge__dot" aria-hidden="true">
        {kindIcon[kind]}
      </span>
      {label ?? kindLabel[kind]}
    </span>
  );
}

export { kindLabel as statusKindLabel };
