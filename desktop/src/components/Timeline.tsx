import type { ReactNode } from "react";
import "./Timeline.css";

export type TimelineItemStatus = "completed" | "running" | "failed" | "partial" | "pending";

export interface TimelineItem {
  key: string;
  title: ReactNode;
  /** 阶段说明：用时、后端、条数等 */
  meta?: ReactNode;
  detail?: ReactNode;
  status: TimelineItemStatus;
}

export interface TimelineProps {
  items: TimelineItem[];
}

const statusIcon: Record<TimelineItemStatus, string> = {
  completed: "✓",
  running: "◌",
  failed: "✕",
  partial: "◐",
  pending: "•",
};

/** 阶段时间线：分析流水线进度（Apktool → JADX → Androguard → 报告）。 */
export function Timeline({ items }: TimelineProps) {
  return (
    <ol className="da-timeline">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <li key={item.key} className={["da-timeline__item", `da-timeline__item--${item.status}`].join(" ")}>
            <div className="da-timeline__rail" aria-hidden="true">
              <span className="da-timeline__dot">{statusIcon[item.status]}</span>
              {isLast ? null : <span className="da-timeline__line" />}
            </div>
            <div className="da-timeline__content">
              <div className="da-timeline__title">{item.title}</div>
              {item.meta ? <div className="da-timeline__meta">{item.meta}</div> : null}
              {item.detail ? <div className="da-timeline__detail">{item.detail}</div> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
