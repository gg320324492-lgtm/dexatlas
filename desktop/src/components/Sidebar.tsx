import type { ReactNode } from "react";
import "./Sidebar.css";

export interface SidebarItem {
  key: string;
  label: string;
  icon?: ReactNode;
  /** 当前激活项 */
  active?: boolean;
  badge?: ReactNode;
  onSelect?: (key: string) => void;
}

export interface SidebarProps {
  items: SidebarItem[];
  activeKey?: string;
  onSelect?: (key: string) => void;
  header?: ReactNode;
  footer?: ReactNode;
  /** 受控折叠 */
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}

/** 左侧主导航：项目 / 分析 / 证据 / 报告 / 设置。键盘可达，aria-current 标注激活项。 */
export function Sidebar({ items, activeKey, onSelect, header, footer, collapsed = false, onCollapsedChange }: SidebarProps) {
  return (
    <nav className={["da-sidebar", collapsed ? "da-sidebar--collapsed" : ""].filter(Boolean).join(" ")} aria-label="主导航">
      {header ? <div className="da-sidebar__header">{header}</div> : null}
      <ul className="da-sidebar__list">
        {items.map((item) => {
          const active = item.active ?? item.key === activeKey;
          return (
            <li key={item.key}>
              <button
                type="button"
                className={["da-sidebar__item", active ? "da-sidebar__item--active" : ""].filter(Boolean).join(" ")}
                aria-current={active ? "page" : undefined}
                title={collapsed ? String(typeof item.label === "string" ? item.label : item.key) : undefined}
                onClick={() => {
                  item.onSelect?.(item.key);
                  onSelect?.(item.key);
                }}
              >
                {item.icon ? <span className="da-sidebar__icon" aria-hidden="true">{item.icon}</span> : null}
                {collapsed ? null : <span className="da-sidebar__label">{item.label}</span>}
                {collapsed || item.badge === undefined ? null : <span className="da-sidebar__badge">{item.badge}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      <div className="da-sidebar__footer">
        {collapsed ? null : footer}
        <button
          type="button"
          className="da-sidebar__collapse"
          aria-label={collapsed ? "展开侧栏" : "折叠侧栏"}
          aria-expanded={!collapsed}
          onClick={() => onCollapsedChange?.(!collapsed)}
        >
          {collapsed ? "›" : "‹"}
        </button>
      </div>
    </nav>
  );
}
