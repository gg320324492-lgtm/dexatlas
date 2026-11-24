import { useEffect, type ReactNode } from "react";
import { useDismissable, useFocusTrap } from "./useDismissable";
import { Button } from "./Button";
import "./Dialog.css";

export interface DialogProps {
  open: boolean;
  title: ReactNode;
  /** 关闭时说明原因（无障碍） */
  description?: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  /** 危险确认弹窗：确认按钮红色 */
  danger?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm?: () => void;
  width?: number;
  children?: ReactNode;
}

/**
 * 对话框：Escape 关闭、遮罩点击关闭、焦点陷阱、关闭后焦点返回。
 * 纯受控组件，不发起任何请求。
 */
export function Dialog({
  open,
  title,
  description,
  onClose,
  footer,
  danger = false,
  confirmLabel = "确认",
  cancelLabel = "取消",
  onConfirm,
  width = 480,
  children,
}: DialogProps) {
  const { backdropRef, onBackdropClick } = useDismissable({
    onEscape: open ? onClose : undefined,
    onBackdrop: open ? onClose : undefined,
    lockScroll: open,
  });
  const trapRef = useFocusTrap(open);

  // 关闭后焦点返回触发元素（useFocusTrap 清理时已处理，这里兜底 document 级）
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    return () => {
      opener?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="da-dialog__backdrop" ref={backdropRef} onClick={onBackdropClick} role="presentation">
      <div
        className="da-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        style={{ maxWidth: width }}
        ref={trapRef}
      >
        <header className="da-dialog__header">
          <h2 className="da-dialog__title">{title}</h2>
          <button type="button" className="da-dialog__close" aria-label="关闭对话框" onClick={onClose}>
            ✕
          </button>
        </header>
        {description ? <p className="da-dialog__desc">{description}</p> : null}
        <div className="da-dialog__body">{children}</div>
        <footer className="da-dialog__footer">
          {footer ?? (
            <>
              <Button variant="secondary" onClick={onClose}>
                {cancelLabel}
              </Button>
              {onConfirm ? (
                <Button variant={danger ? "danger" : "primary"} onClick={onConfirm}>
                  {confirmLabel}
                </Button>
              ) : null}
            </>
          )}
        </footer>
      </div>
    </div>
  );
}
