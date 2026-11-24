import { NavLink, Outlet } from "react-router-dom";
import "./AppLayout.css";

const NAV_ITEMS = [
  { to: "/", label: "项目", icon: "▦", end: true },
  { to: "/analysis", label: "分析", icon: "◈", end: false },
  { to: "/findings", label: "证据", icon: "◆", end: false },
  { to: "/reports", label: "报告", icon: "▤", end: false },
  { to: "/settings", label: "设置", icon: "⚙", end: false },
] as const;

/** 全局布局：左侧栏 + 主内容区。 */
export default function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-logo" aria-hidden="true">
            ◈
          </div>
          <div>
            <div className="sidebar-name">DexAtlas</div>
            <div className="sidebar-tagline">证据链分析工作室</div>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="主导航">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `sidebar-link${isActive ? " is-active" : ""}`
              }
            >
              <span className="sidebar-link-icon" aria-hidden="true">
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="badge badge-muted">v1.0.2</span>
        </div>
      </aside>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
