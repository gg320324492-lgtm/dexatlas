import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import "./SearchInput.css";

export interface SearchInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  /** 受控清除：清空按钮点击 */
  onClear?: () => void;
  trailing?: ReactNode;
}

/** 搜索输入框：搜索图标 + 可清除，无自动请求（由外部防抖）。 */
export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(function SearchInput(
  { onClear, trailing, className, value, ...rest },
  ref,
) {
  const hasValue = typeof value === "string" ? value.length > 0 : value !== undefined && value !== null;
  return (
    <div className={["da-search", className ?? ""].filter(Boolean).join(" ")}>
      <span className="da-search__icon" aria-hidden="true">
        ⌕
      </span>
      <input ref={ref} type="search" className="da-search__input" value={value} {...rest} />
      {hasValue && onClear ? (
        <button type="button" className="da-search__clear" aria-label="清空搜索" onClick={onClear}>
          ✕
        </button>
      ) : null}
      {trailing}
    </div>
  );
});
