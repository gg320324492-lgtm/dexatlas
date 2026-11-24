import type { ReactNode } from "react";
import "./states.css";

export interface EmptyStateProps {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  actions?: ReactNode;
}

/** 空状态：无数据/无项目时占位。 */
export function EmptyState({ title, description, icon, actions }: EmptyStateProps) {
  return (
    <div className="da-state da-state--empty">
      <div className="da-state__icon" aria-hidden="true">
        {icon ?? "🗂"}
      </div>
      <div className="da-state__title">{title}</div>
      {description ? <div className="da-state__desc">{description}</div> : null}
      {actions ? <div className="da-state__actions">{actions}</div> : null}
    </div>
  );
}
