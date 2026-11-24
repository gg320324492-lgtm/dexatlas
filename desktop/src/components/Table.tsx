import { useState, type ReactNode } from "react";
import "./Table.css";

export interface TableColumn<Row> {
  key: string;
  header: ReactNode;
  /** 渲染单元格；缺省显示 row[key] 的字符串形式 */
  render?: (row: Row) => ReactNode;
  /** 排序取值；缺省用 row[key] */
  sortValue?: (row: Row) => string | number;
  align?: "left" | "right" | "center";
  width?: string | number;
}

export interface TableProps<Row> {
  columns: Array<TableColumn<Row>>;
  rows: Row[];
  /** 行唯一键取值 */
  rowKey: (row: Row) => string;
  /** 空数据展示 */
  empty?: ReactNode;
  /** 行点击（详情跳转等），键盘同样可用 */
  onRowClick?: (row: Row) => void;
  /** 紧凑密度（Carbon 风格分级） */
  density?: "default" | "compact";
  caption?: string;
}

type SortState = { key: string; dir: "asc" | "desc" } | null;

/**
 * 数据表：仅受控展示 + 客户端排序，不发请求。
 * 可点击行使用原生 button 语义由调用方决定；这里用 div+tabIndex 保证键盘可达。
 */
export function Table<Row extends Record<string, unknown>>({ columns, rows, rowKey, empty, onRowClick, density = "default", caption }: TableProps<Row>) {
  const [sort, setSort] = useState<SortState>(null);

  const sortedRows = (() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sortValue && !col) return rows;
    const get = (row: Row): string | number => (col?.sortValue ? col.sortValue(row) : String((row as Record<string, unknown>)[col!.key] ?? ""));
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = get(a);
      const vb = get(b);
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb)) * dir;
    });
  })();

  const toggleSort = (key: string) => {
    setSort((prev) => {
      if (prev?.key !== key) return { key, dir: "asc" };
      if (prev.dir === "asc") return { key, dir: "desc" };
      return null;
    });
  };

  if (rows.length === 0 && empty) {
    return <>{empty}</>;
  }

  return (
    <div className={["da-table-wrap", density === "compact" ? "da-table-wrap--compact" : ""].filter(Boolean).join(" ")}>
      <table className="da-table">
        {caption ? <caption className="da-table__caption">{caption}</caption> : null}
        <thead>
          <tr>
            {columns.map((col) => {
              const firstRow: Record<string, unknown> | undefined =
                rows.length > 0 ? (rows[0] as unknown as Record<string, unknown>) : undefined;
              const sortable = Boolean(col.sortValue) || (firstRow !== undefined && col.key in firstRow);
              const active = sort?.key === col.key;
              return (
                <th
                  key={col.key}
                  scope="col"
                  style={{ width: col.width, textAlign: col.align ?? "left" }}
                  aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}
                >
                  {sortable ? (
                    <button type="button" className="da-table__sort" onClick={() => toggleSort(col.key)}>
                      <span>{col.header}</span>
                      <span className={["da-table__sort-arrow", active ? "da-table__sort-arrow--active" : ""].join(" ")} aria-hidden="true">
                        {active && sort!.dir === "desc" ? "▼" : "▲"}
                      </span>
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => {
            const key = rowKey(row);
            const clickable = Boolean(onRowClick);
            return (
              <tr
                key={key}
                className={clickable ? "da-table__row--clickable" : undefined}
                tabIndex={clickable ? 0 : undefined}
                onClick={clickable ? () => onRowClick?.(row) : undefined}
                onKeyDown={
                  clickable
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onRowClick?.(row);
                        }
                      }
                    : undefined
                }
              >
                {columns.map((col) => (
                  <td key={col.key} style={{ textAlign: col.align ?? "left" }}>
                    {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
