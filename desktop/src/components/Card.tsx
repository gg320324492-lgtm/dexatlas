import type { HTMLAttributes, ReactNode } from "react";
import "./Card.css";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** 是否可悬停上浮（可点击卡片用） */
  interactive?: boolean;
  /** 渐变描边语言（首屏/强调卡片） */
  accent?: boolean;
  children?: ReactNode;
}

/** 基础卡片：大圆角 + 一级阴影 + 暖白表面。 */
export function Card({ interactive = false, accent = false, className, children, ...rest }: CardProps) {
  return (
    <div
      className={["da-card", interactive ? "da-card--interactive" : "", accent ? "da-card--accent" : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}

export function CardHeader({ title, subtitle, actions }: CardHeaderProps) {
  return (
    <div className="da-card__header">
      <div className="da-card__heading">
        <div className="da-card__title">{title}</div>
        {subtitle ? <div className="da-card__subtitle">{subtitle}</div> : null}
      </div>
      {actions ? <div className="da-card__actions">{actions}</div> : null}
    </div>
  );
}

export function CardBody({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={["da-card__body", className ?? ""].filter(Boolean).join(" ")} {...rest}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={["da-card__footer", className ?? ""].filter(Boolean).join(" ")} {...rest}>
      {children}
    </div>
  );
}
