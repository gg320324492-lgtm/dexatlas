import { useEffect, useRef } from "react";

export interface DismissableOptions {
  /** Escape 关闭 */
  onEscape?: () => void;
  /** 点击遮罩关闭 */
  onBackdrop?: () => void;
  /** 打开时锁定 body 滚动 */
  lockScroll?: boolean;
}

/**
 * 浮层通用行为：Escape 关闭、遮罩点击关闭、body 滚动锁定。
 * 返回遮罩 ref（点击遮罩本身才关闭，点击内容不关闭）。
 */
export function useDismissable({ onEscape, onBackdrop, lockScroll = true }: DismissableOptions) {
  const backdropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onEscape?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onEscape]);

  useEffect(() => {
    if (!lockScroll) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [lockScroll]);

  const onBackdropClick = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) onBackdrop?.();
  };

  return { backdropRef, onBackdropClick };
}

/** 简单焦点陷阱：Tab 循环限制在容器内，关闭时由调用方还原焦点。 */
export function useFocusTrap(active: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const selector =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

    const focusables = () => Array.from(container.querySelectorAll<HTMLElement>(selector)).filter((el) => el.offsetParent !== null || el === document.activeElement);

    // 初始聚焦第一个可聚焦元素
    const first = focusables()[0];
    first?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const list = focusables();
      if (list.length === 0) return;
      const firstEl = list[0];
      const lastEl = list[list.length - 1];
      if (!firstEl || !lastEl) return;
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };

    container.addEventListener("keydown", onKey);
    return () => {
      container.removeEventListener("keydown", onKey);
      previouslyFocused?.focus?.();
    };
  }, [active]);

  return containerRef;
}
