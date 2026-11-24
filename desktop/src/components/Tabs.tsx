import { useId, useState, type ReactNode } from "react";
import "./Tabs.css";

export interface TabItem {
  key: string;
  label: ReactNode;
  badge?: ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  items: TabItem[];
  activeKey?: string;
  onChange?: (key: string) => void;
  children?: (activeKey: string) => ReactNode;
}

/**
 * 标签页：受控/非受控两用。
 * roving tabindex：激活页签 tabIndex=0，其余 -1；左右方向键切换。
 */
export function Tabs({ items, activeKey, onChange, children }: TabsProps) {
  const id = useId();
  const [internal, setInternal] = useState(items[0]?.key ?? "");
  const active = activeKey ?? internal;
  const enabled = items.filter((t) => !t.disabled);
  const current = items.find((t) => t.key === active) ?? items[0];

  const select = (key: string) => {
    if (activeKey === undefined) setInternal(key);
    onChange?.(key);
  };

  const move = (dir: 1 | -1) => {
    const idx = enabled.findIndex((t) => t.key === current?.key);
    const next = enabled[(idx + dir + enabled.length) % enabled.length];
    if (next) select(next.key);
  };

  return (
    <div className="da-tabs">
      <div className="da-tabs__list" role="tablist" aria-label="页签">
        {items.map((item) => {
          const isActive = item.key === current?.key;
          return (
            <button
              key={item.key}
              type="button"
              role="tab"
              id={`da-tab-${id}-${item.key}`}
              aria-selected={isActive}
              aria-controls={`da-tabpanel-${id}-${item.key}`}
              tabIndex={isActive ? 0 : -1}
              disabled={item.disabled}
              className={["da-tabs__tab", isActive ? "da-tabs__tab--active" : "", item.disabled ? "da-tabs__tab--disabled" : ""]
                .filter(Boolean)
                .join(" ")}
              onClick={() => select(item.key)}
              onKeyDown={(e) => {
                if (e.key === "ArrowRight") {
                  e.preventDefault();
                  move(1);
                } else if (e.key === "ArrowLeft") {
                  e.preventDefault();
                  move(-1);
                }
              }}
            >
              <span>{item.label}</span>
              {item.badge !== undefined ? <span className="da-tabs__badge">{item.badge}</span> : null}
            </button>
          );
        })}
      </div>
      {current ? (
        <div
          role="tabpanel"
          id={`da-tabpanel-${id}-${current.key}`}
          aria-labelledby={`da-tab-${id}-${current.key}`}
          className="da-tabs__panel"
        >
          {children ? children(current.key) : null}
        </div>
      ) : null}
    </div>
  );
}
