import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import "./Button.css";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 视觉层级：primary 实心蓝紫 / secondary 描边 / danger 红 / ghost 无底 */
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** 展示加载态：禁点，不触发 onClick */
  loading?: boolean;
  /** 危险操作前的确认文案；非空时点击先弹确认 */
  confirm?: string;
  iconStart?: ReactNode;
  iconEnd?: ReactNode;
  children?: ReactNode;
}

const sizeClass: Record<ButtonSize, string> = {
  sm: "da-btn--sm",
  md: "da-btn--md",
  lg: "da-btn--lg",
};

/**
 * 通用按钮。只做展示与受控行为，不发请求。
 * disabled/loading 均阻止点击；confirm 走 window.confirm（桌面原型阶段）。
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "secondary",
    size = "md",
    loading = false,
    confirm,
    iconStart,
    iconEnd,
    className,
    type = "button",
    disabled,
    onClick,
    children,
    ...rest
  },
  ref,
) {
  const blocked = disabled === true || loading;
  return (
    <button
      ref={ref}
      type={type}
      className={["da-btn", `da-btn--${variant}`, sizeClass[size], loading ? "da-btn--loading" : "", className ?? ""]
        .filter(Boolean)
        .join(" ")}
      disabled={blocked}
      aria-busy={loading || undefined}
      onClick={
        blocked
          ? undefined
          : (event) => {
              if (confirm && !window.confirm(confirm)) return;
              onClick?.(event);
            }
      }
      {...rest}
    >
      {loading ? <span className="da-btn__spinner" aria-hidden="true" /> : iconStart}
      <span className="da-btn__label">{children}</span>
      {iconEnd}
    </button>
  );
});
