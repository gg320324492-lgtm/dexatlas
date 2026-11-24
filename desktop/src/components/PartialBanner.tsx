import type { ReactNode } from "react";
import "./PartialBanner.css";

export type PartialBannerTone = "warning" | "info" | "danger";

export interface PartialBannerProps {
  /** 部分完成/降级说明，例如“JADX 反编译失败，已降级为仅 Manifest 视图” */
  message: ReactNode;
  /** 可选的失败步骤清单 */
  details?: ReactNode[];
  tone?: PartialBannerTone;
  /** 重试入口 */
  onRetry?: () => void;
  onDismiss?: () => void;
  children?: ReactNode;
}

/**
 * 部分结果横幅：分析链路某一步失败但整体仍有可用输出时展示。
 * 对应规范“部分状态”，与 StatusBadge 的 partial 呼应。
 */
export function PartialBanner({ message, details, tone = "warning", onRetry, onDismiss, children }: PartialBannerProps) {
  return (
    <div className={["da-partial", `da-partial--${tone}`].join(" ")} role="status">
      <span className="da-partial__icon" aria-hidden="true">
        {tone === "danger" ? "✕" : tone === "info" ? "ℹ" : "◐"}
      </span>
      <div className="da-partial__content">
        <div className="da-partial__message">{message}</div>
        {details && details.length > 0 ? (
          <ul className="da-partial__details">
            {details.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        ) : null}
        {children}
      </div>
      <div className="da-partial__actions">
        {onRetry ? (
          <button type="button" className="da-partial__retry" onClick={onRetry}>
            重试
          </button>
        ) : null}
        {onDismiss ? (
          <button type="button" className="da-partial__dismiss" aria-label="关闭提示" onClick={onDismiss}>
            ✕
          </button>
        ) : null}
      </div>
    </div>
  );
}
