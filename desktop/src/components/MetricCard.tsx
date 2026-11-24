import type { ReactNode } from "react";
import "./MetricCard.css";

export interface MetricCardProps {
  /** 指标名，如“证据条数” */
  label: ReactNode;
  /** 指标值（已格式化的展示字符串） */
  value: ReactNode;
  /** 同比/环比变化，如 “+12%”；正负决定颜色 */
  delta?: ReactNode;
  /** delta 方向：up 好 / down 差 / flat 持平；仅影响颜色 */
  trend?: "up" | "down" | "flat";
  /** 附加说明 */
  hint?: ReactNode;
  icon?: ReactNode;
}

/** 指标卡片：报告页/分析页的关键数字展示。 */
export function MetricCard({ label, value, delta, trend = "flat", hint, icon }: MetricCardProps) {
  return (
    <div className="da-metric">
      <div className="da-metric__head">
        <span className="da-metric__label">{label}</span>
        {icon ? <span className="da-metric__icon" aria-hidden="true">{icon}</span> : null}
      </div>
      <div className="da-metric__value">{value}</div>
      <div className="da-metric__foot">
        {delta ? <span className={`da-metric__delta da-metric__delta--${trend}`}>{delta}</span> : null}
        {hint ? <span className="da-metric__hint">{hint}</span> : null}
      </div>
    </div>
  );
}
