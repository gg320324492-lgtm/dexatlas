import { useEffect, type ReactNode } from "react";
import { useDismissable, useFocusTrap } from "./useDismissable";
import "./Drawer.css";

export interface DrawerProps {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  /** 打开方向：右滑（默认）或左滑 */
  side?: "right" | "left";
  width?: number;
  footer?: ReactNode;
  children?: ReactNode;
}

/**
 * 抽屉：三栏详情页的"证据抽屉"容器。
 * Escape 关闭、遮罩点击关闭、焦点陷阱、关闭后焦点返回。
 */
export function Drawer({ open, title, onClose, side = "right", width = 420, footer, children }: DrawerProps) {
  const { backdropRef, onBackdropClick } = useDismissable({
    onEscape: open ? onClose : undefined,
    onBackdrop: open ? onClose : undefined,
    lockScroll: open,
  });
  const trapRef = useFocusTrap(open);

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    return () => {
      opener?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="da-drawer__backdrop" ref={backdropRef} onClick={onBackdropClick} role="presentation">
      <aside
        className={["da-drawer", `da-drawer--${side}`].join(" ")}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        style={{ width }}
        ref={trapRef}
      >
        <header className="da-drawer__header">
          <h2 className="da-drawer__title">{title}</h2>
          <button type="button" className="da-drawer__close" aria-label="关闭抽屉" onClick={onClose}>
            ✕
          </button>
        </header>
        <div className="da-drawer__body">{children}</div>
        {footer ? <footer className="da-drawer__footer">{footer}</footer> : null}
      </aside>
    </div>
  );
}
