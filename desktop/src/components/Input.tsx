import { forwardRef, type InputHTMLAttributes, type ReactNode, useId } from "react";
import "./Input.css";

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "prefix"> {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  /** 前置内容（单位、图标） */
  prefix?: ReactNode;
  suffix?: ReactNode;
}

/** 文本输入框：label/hint/error 关联完整，键盘可达。 */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, hint, error, prefix, suffix, className, id, required, ...rest },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? `da-input-${autoId}`;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const describedBy = [hint ? hintId : "", error ? errorId : ""].filter(Boolean).join(" ");

  return (
    <div className={["da-field", error ? "da-field--error" : "", className ?? ""].filter(Boolean).join(" ")}>
      {label ? (
        <label className="da-field__label" htmlFor={inputId}>
          {label}
          {required ? <span className="da-field__required" aria-hidden="true"> *</span> : null}
        </label>
      ) : null}
      <div className="da-field__control">
        {prefix ? <span className="da-field__prefix">{prefix}</span> : null}
        <input
          ref={ref}
          id={inputId}
          className="da-field__input"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          required={required}
          {...rest}
        />
        {suffix ? <span className="da-field__suffix">{suffix}</span> : null}
      </div>
      {hint && !error ? (
        <p className="da-field__hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="da-field__error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
});
