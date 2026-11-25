import { useRef, type MouseEvent } from "react";
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
  const mainRef = useRef<HTMLElement>(null);

  // HashRouter 下原生 fragment 跳转会污染路由 hash（#main-content 被解析为路径），
  // 因此阻止默认导航，改为显式把焦点移到主内容。
  const handleSkip = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    mainRef.current?.focus();
  };

  return (
    <div className="app-shell">
      {/* 键盘用户可第一跳直接进入主内容，不必穿过整个侧栏（验收 A-7）。 */}
      <a href="#main-content" className="skip-link" onClick={handleSkip}>
        跳到主内容
      </a>
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
      </aside>

      <main id="main-content" ref={mainRef} className="app-main" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
