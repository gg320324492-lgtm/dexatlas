import { Fragment, type ReactNode } from "react";
import "./Breadcrumbs.css";

export interface BreadcrumbItem {
  key: string;
  label: ReactNode;
  onClick?: () => void;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

/** 面包屑导航：最后一项为当前页（aria-current），其余可点击返回。 */
export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="da-crumbs" aria-label="面包屑">
      <ol className="da-crumbs__list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.key} className="da-crumbs__item">
              {isLast ? (
                <span className="da-crumbs__current" aria-current="page">
                  {item.label}
                </span>
              ) : (
                <button type="button" className="da-crumbs__link" onClick={item.onClick}>
                  {item.label}
                </button>
              )}
              {isLast ? null : (
                <span className="da-crumbs__sep" aria-hidden="true">
                  /
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
