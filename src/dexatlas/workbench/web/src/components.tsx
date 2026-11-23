import { useCallback, useEffect, useRef, type JSX, type ReactNode, type RefObject } from "react";

// The workbench's shared base components (workbench-ui.md §4). Each does one
// thing, takes its data through props, and fetches nothing: the screens own
// the calls to api.ts, the components render what a screen hands them. Every
// class these render is an existing one or a new `wb-` prefixed one; none of
// the screens' existing names are redefined here.

// -- the shell --------------------------------------------------------------

/** The page's outer frame: the top bar, then the content container `main`.
 * `main`'s centering and padding are the CSS's own; this component only
 * names the parts. */
export function AppShell({ children }: { children: ReactNode }): JSX.Element {
  return <div className="workbench">{children}</div>;
}

export interface TopbarWarning {
  missing: string[];
}

/** The fixed top bar: the product name back to the list, the workspace
 * annotation, the nav links and the backends warning slot. */
export function Topbar({
  title,
  workspaceNote,
  nav,
  warning,
}: {
  title: string;
  workspaceNote: string;
  nav: ReactNode;
  warning?: ReactNode;
}): JSX.Element {
  return (
    <header className="topbar">
      <h1>
        <a href="#/">{title}</a>
      </h1>
      <nav className="topnav" aria-label="workbench screens">
        {nav}
      </nav>
      {warning}
      <span className="meta">{workspaceNote}</span>
    </header>
  );
}

export interface Crumb {
  label: string;
  to?: string;
}

/** The hierarchy path: project list → project → subpage. The last crumb is
 * where the reader is, so it is not a link even when it carries a `to`. */
export function Breadcrumbs({ items }: { items: Crumb[] }): JSX.Element | null {
  if (items.length === 0) return null;
  return (
    <nav className="wb-crumbs" aria-label="where you are">
      {items.map((item, index) => {
        const last = index === items.length - 1;
        const label = last ? (
          <span aria-current="page">{item.label}</span>
        ) : item.to ? (
          <a href={item.to}>{item.label}</a>
        ) : (
          <span>{item.label}</span>
        );
        return (
          <span className="wb-crumb" key={`${item.label}-${index}`}>
            {label}
            {!last && <span className="wb-crumb-sep">/</span>}
          </span>
        );
      })}
    </nav>
  );
}

/** The page's title, its subtitle and the actions at its right edge. */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}): JSX.Element {
  return (
    <header className="project-header">
      <div className="wb-page-head-row">
        <h2>{title}</h2>
        {actions && <div className="wb-page-actions">{actions}</div>}
      </div>
      {subtitle && <p className="meta">{subtitle}</p>}
    </header>
  );
}

// -- the containers ---------------------------------------------------------

/** A bordered content section with an optional title. The `aria-label` stays
 * on the section so the existing screens' landmark names keep working. */
export function Panel({
  title,
  ariaLabel,
  children,
}: {
  title?: ReactNode;
  ariaLabel?: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <section className="panel" aria-label={ariaLabel}>
      {title !== undefined && <h3>{title}</h3>}
      {children}
    </section>
  );
}

/** One counting card: the value in the tabular monospace the tables use, and
 * the label that says what was counted. */
export function StatCard({ value, label }: { value: ReactNode; label: string }): JSX.Element {
  return (
    <div className="count">
      <span className="count-value">{value}</span>
      <span className="count-label">{label}</span>
    </div>
  );
}

/** A row of counting cards. */
export function StatGrid({ children }: { children: ReactNode }): JSX.Element {
  return <div className="counts">{children}</div>;
}

// -- the states -------------------------------------------------------------

export type BadgeKind = "ok" | "running" | "failed" | "pending" | "neutral";

/** The badge kinds land on the stylesheet's existing status classes, so a
 * badge and the raw `status-*` spans the screens already render read alike. */
const BADGE_CLASS: Record<BadgeKind, string> = {
  ok: "status-completed",
  running: "status-running",
  failed: "status-failed",
  pending: "status-pending",
  neutral: "status-pending",
};

/** A status badge. The project statuses map onto it through `badgeKind`. The
 * mark is the non-color signal the design calls for: every kind reads the
 * same with color away. */
const BADGE_MARK: Record<BadgeKind, string> = {
  ok: "✓",
  running: "…",
  failed: "✕",
  pending: "•",
  neutral: "•",
};

export function StatusBadge({ kind, label }: { kind: BadgeKind; label: string }): JSX.Element {
  return (
    <span className={`status ${BADGE_CLASS[kind]}`}>
      <span className="status-mark" aria-hidden="true">
        {BADGE_MARK[kind]}
      </span>{" "}
      {label}
    </span>
  );
}

/** The existing statuses' colors, in one place: completed is green, a status
 * still moving is amber, a stopped one is red, and anything else is the
 * neutral badge. */
export function badgeKind(status: string): BadgeKind {
  if (status === "completed") return "ok";
  if (status === "running" || status === "planning" || status === "pending") return "running";
  if (status === "failed" || status === "budget_exhausted" || status === "interrupted") {
    return "failed";
  }
  return "neutral";
}

/** A run's or a page's completeness: partial data, said at the top where the
 * reader meets it. The banner states the fact and never invents a metric —
 * the wording describes what the data layer already reported. */
export function PartialBanner({ children }: { children: ReactNode }): JSX.Element | null {
  return (
    <div className="wb-partial-banner" role="status">
      <span className="wb-partial-mark" aria-hidden="true">
        !
      </span>
      <div>{children}</div>
    </div>
  );
}

/** The one error panel every screen's failure renders through: a readable
 * reason and the retry that re-runs the screen's own fetch. `onRetry`
 * repeating the request is the screen's business; the panel only offers the
 * button. */
export function ErrorPanel({
  message,
  onRetry,
  retryLabel = "try again",
  links,
}: {
  message: ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  links?: ReactNode;
}): JSX.Element {
  return (
    <div className="wb-error-panel" role="alert">
      <p className="error">{message}</p>
      {(onRetry !== undefined || links !== undefined) && (
        <p className="wb-error-actions">
          {onRetry && (
            <button type="button" className="link-button" onClick={onRetry}>
              {retryLabel}
            </button>
          )}
          {onRetry !== undefined && links !== undefined && " · "}
          {links}
        </p>
      )}
    </div>
  );
}

/** An empty collection, with the next action a reader can take. */
export function EmptyNote({ children }: { children: ReactNode }): JSX.Element {
  return <p className="empty">{children}</p>;
}

// -- the controls -----------------------------------------------------------

export type ButtonVariant = "primary" | "secondary";

/** A button. The existing `button` element styling is the base; `primary`
 * adds the accent fill. The disabled state is stated by the attribute, so
 * keyboard focus and screen readers see it. */
export function Button({
  variant = "secondary",
  disabled,
  onClick,
  type = "button",
  children,
}: {
  variant?: ButtonVariant;
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
  children: ReactNode;
}): JSX.Element {
  return (
    <button
      type={type}
      className={`wb-button ${variant === "primary" ? "wb-button-primary" : ""}`.trim()}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export interface Tab {
  id: string;
  label: string;
}

/** In-page tabs. The active tab is `aria-selected`; the buttons are the
 * keyboard interface, so tab and arrow keys need no extra handling. */
export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
}): JSX.Element {
  return (
    <div className="wb-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === active}
          className={`wb-tab ${tab.id === active ? "wb-tab-active" : ""}`.trim()}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// -- the loading states -----------------------------------------------------

/** A loading placeholder: shimmering bars in place of the content that is
 * coming. `rows` shapes it to the container — a table asks for more and
 * shorter rows than a panel of prose. Honors `prefers-reduced-motion`
 * through the CSS, which stops the shimmer. */
export function Skeleton({ rows = 3, label }: { rows?: number; label?: string }): JSX.Element {
  return (
    <div className="wb-skeleton" role="status" aria-label={label ?? "loading"}>
      {Array.from({ length: rows }, (_, index) => (
        <span
          key={index}
          className="wb-skeleton-row"
          style={index % 2 === 1 ? { width: "72%" } : undefined}
        />
      ))}
    </div>
  );
}

/** A small spinner for a wait that is already inside visible content — an
 * upload in flight, a question being asked — where a block of skeleton bars
 * would crowd out the text around it. */
export function Spinner({ label }: { label: ReactNode }): JSX.Element {
  return (
    <span className="wb-spinner" role="status">
      <span className="wb-spinner-wheel" aria-hidden="true" />
      <span className="wb-spinner-label">{label}</span>
    </span>
  );
}

// -- the overlays -----------------------------------------------------------

/** A modal dialog. Escape closes it; on open the first focusable element
 * inside receives focus, Tab cycles within the panel (focus trap), and focus
 * is handed back to the trigger through `restoreFocusTo` when it closes. */
export function Dialog({
  open,
  title,
  onClose,
  children,
  restoreFocusTo,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  restoreFocusTo?: HTMLElement | null;
}): JSX.Element | null {
  const panelRef = useRef<HTMLDivElement | null>(null);
  useEscapeCloses(open, onClose);
  useModalFocus(open, panelRef, restoreFocusTo);
  if (!open) return null;
  return (
    <div className="wb-overlay" onClick={onClose}>
      <div
        ref={panelRef}
        className="wb-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="wb-dialog-head">
          <h3>{title}</h3>
          <button type="button" className="link-button" onClick={onClose} aria-label="close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** A side drawer: the same contract as the dialog, arriving from the right. */
export function Drawer({
  open,
  title,
  onClose,
  children,
  restoreFocusTo,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  restoreFocusTo?: HTMLElement | null;
}): JSX.Element | null {
  const panelRef = useRef<HTMLElement | null>(null);
  useEscapeCloses(open, onClose);
  useModalFocus(open, panelRef, restoreFocusTo);
  if (!open) return null;
  return (
    <div className="wb-overlay" onClick={onClose}>
      <aside
        ref={panelRef}
        className="wb-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="wb-dialog-head">
          <h3>{title}</h3>
          <button type="button" className="link-button" onClick={onClose} aria-label="close">
            ✕
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}

function useEscapeCloses(open: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "escape" || event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
}

/** The focusable elements a modal manages: native controls plus anything with
 * a tabindex. Not matching `display: none` contents is good enough here — the
 * panels' children are simple controls, not conditionally hidden subtrees. */
function focusableIn(panel: HTMLElement): HTMLElement[] {
  const candidates = panel.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  );
  return Array.from(candidates).filter((element) => element.offsetParent !== null);
}
/** Open a modal: focus moves into the panel (its first focusable element, or
 * the panel itself when none — the panel carries `tabindex="-1"` for that),
 * and Tab or Shift+Tab cycles within it instead of escaping to the page
 * behind. Close: focus returns to the trigger through `restoreFocusTo`. */
function useModalFocus<T extends HTMLElement>(
  open: boolean,
  panelRef: RefObject<T | null>,
  restoreFocusTo: HTMLElement | null | undefined,
): void {
  const wasOpen = useRef(false);
  const restore = useCallback((): void => {
    if (restoreFocusTo && document.contains(restoreFocusTo)) restoreFocusTo.focus();
  }, [restoreFocusTo]);

  useEffect(() => {
    if (open) {
      wasOpen.current = true;
      const panel = panelRef.current;
      if (panel) {
        const first = focusableIn(panel)[0] ?? panel;
        if (first !== panel) {
          first.focus();
        } else {
          panel.tabIndex = -1;
          panel.focus();
        }
      }
      return;
    }
    if (wasOpen.current) restore();
    wasOpen.current = false;
  }, [open, panelRef, restore]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent): void => {
      if (event.key !== "tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const focusable = focusableIn(panel);
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const current = document.activeElement;
      const index = focusable.indexOf(current as HTMLElement);
      const lastIndex = focusable.length - 1;
      const next =
        event.shiftKey
          ? index <= 0
            ? focusable[lastIndex]
            : focusable[index - 1]
          : index === lastIndex || index === -1
            ? focusable[0]
            : focusable[index + 1];
      event.preventDefault();
      if (next) next.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, panelRef]);
}
