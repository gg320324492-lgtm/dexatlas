import { useId, useState, type ReactNode } from "react";
import "./Panel.css";

export interface PanelProps {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** 初始不折叠；受控折叠由外部传入 collapsed/onToggle */
  defaultCollapsed?: boolean;
  collapsed?: boolean;
  onToggle?: (collapsed: boolean) => void;
  children?: ReactNode;
}

/**
 * 面板：带标题与折叠能力的区块容器。
 * 折叠按钮键盘可达（原生 button），aria-expanded 表达状态。
 */
export function Panel({
  title,
  subtitle,
  actions,
  defaultCollapsed = false,
  collapsed,
  onToggle,
  children,
}: PanelProps) {
  const id = useId();
  const bodyId = `da-panel-body-${id}`;
  const isControlled = collapsed !== undefined;
  const [internalCollapsed, setInternalCollapsed] = useState(defaultCollapsed);
  const isCollapsed = isControlled ? collapsed : internalCollapsed;

  const toggle = () => {
    const next = !isCollapsed;
    if (!isControlled) setInternalCollapsed(next);
    onToggle?.(next);
  };

  return (
    <section className={["da-panel", isCollapsed ? "da-panel--collapsed" : ""].filter(Boolean).join(" ")}>
      <header className="da-panel__header">
        <button
          type="button"
          className="da-panel__toggle"
          aria-expanded={!isCollapsed}
          aria-controls={bodyId}
          onClick={toggle}
        >
          <span
            className={["da-panel__chevron", isCollapsed ? "da-panel__chevron--closed" : ""].join(" ")}
            aria-hidden="true"
          >
            ▾
          </span>
          <span className="da-panel__title">{title}</span>
          {subtitle ? <span className="da-panel__subtitle">{subtitle}</span> : null}
        </button>
        {actions ? <div className="da-panel__actions">{actions}</div> : null}
      </header>
      {isCollapsed ? null : (
        <div id={bodyId} className="da-panel__body">
          {children}
        </div>
      )}
    </section>
  );
}
