import type { ReactNode } from "react";
import { Button } from "../Button";
import "./states.css";

export interface ErrorStateProps {
  title?: ReactNode;
  description?: ReactNode;
  /** 错误详情（堆栈、错误码） */
  detail?: ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  actions?: ReactNode;
}

/** 错误状态：失败原因 + 重试入口。 */
export function ErrorState({
  title = "出错了",
  description = "操作未能完成，请重试或查看日志。",
  detail,
  onRetry,
  retryLabel = "重试",
  actions,
}: ErrorStateProps) {
  return (
    <div className="da-state da-state--error" role="alert">
      <div className="da-state__icon" aria-hidden="true">
        ⚠
      </div>
      <div className="da-state__title">{title}</div>
      {description ? <div className="da-state__desc">{description}</div> : null}
      {detail ? <pre className="da-state__detail">{detail}</pre> : null}
      <div className="da-state__actions">
        {onRetry ? (
          <Button variant="primary" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        ) : null}
        {actions}
      </div>
    </div>
  );
}
