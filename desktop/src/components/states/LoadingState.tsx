import type { ReactNode } from "react";
import "./states.css";

export interface LoadingStateProps {
  label?: ReactNode;
  /** 骨架屏行数 */
  lines?: number;
  /** 卡片式骨架（默认为文本行骨架） */
  variant?: "lines" | "card" | "table";
  children?: ReactNode;
}

/** 加载状态：骨架屏（默认 4 行文本），不遮挡已有内容时可用 spinner。 */
export function LoadingState({ label, lines = 4, variant = "lines", children }: LoadingStateProps) {
  return (
    <div className="da-state da-state--loading" role="status" aria-live="polite">
      <span className="da-visually-hidden">{label ?? "加载中"}</span>
      {variant === "lines" ? (
        <div className="da-skeleton-lines">
          {Array.from({ length: lines }, (_, i) => (
            <div key={i} className={["da-skeleton-line", i === lines - 1 ? "da-skeleton-line--short" : ""].join(" ")} />
          ))}
        </div>
      ) : null}
      {variant === "card" ? (
        <div className="da-skeleton-cards">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="da-skeleton-card">
              <div className="da-skeleton-line da-skeleton-line--title" />
              <div className="da-skeleton-line" />
              <div className="da-skeleton-line da-skeleton-line--short" />
            </div>
          ))}
        </div>
      ) : null}
      {variant === "table" ? (
        <div className="da-skeleton-table">
          {Array.from({ length: lines }, (_, i) => (
            <div key={i} className="da-skeleton-table__row">
              <div className="da-skeleton-line" />
              <div className="da-skeleton-line" />
              <div className="da-skeleton-line da-skeleton-line--short" />
            </div>
          ))}
        </div>
      ) : null}
      {children}
    </div>
  );
}
