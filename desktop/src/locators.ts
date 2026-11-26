/**
 * locator 落点分类 —— 「打开来源」按钮能不能用的依据。
 *
 * 后端对 locator 的定义在 `src/dexatlas/core/locators.py`（`parse_locator` 与
 * `LocatorKind`）。一个 locator 写成 `<工具>:<位置>`，它指向的东西分四类：
 *
 * - `jadx:` / `apktool:` —— 后端输出树里的一个**文件**（可带 `#成员` 后缀）。
 *   只有这一类解析之后有单文件落点（后端 `Resolution.path` 非空）。
 * - `apk-reader:` —— APK 包本身的事实（大小、哈希、DEX 清单）。
 *   解析会成功，但**没有**单文件落点。
 * - `androguard:` —— APK 字节码里的位置（dex 文件 / 类 / 成员 / 字符串）。
 *   同样解析成功，但**没有**单文件落点。
 * - `<工具>:error/...` —— 后端没跑完这件事实本身，也没有单文件落点。
 *
 * 这里只镜像工具前缀这一层词汇（与 `ProjectDetail.tsx` 的 `originOf` 同一套），
 * 用来在还没问过后端之前就知道「这个按钮点了会不会是空的」。文件到底在不在，
 * 仍以后端 `/locators/resolve` 的回答为准，见 {@link openSourceState}。
 *
 * 工具前缀与后端常量一一对应，`tests/test_desktop_locator_open_source.py` 有
 * 守卫测试盯着这份镜像，不许它悄悄漂移。
 */

/** locator 指向的落点类别。 */
export type LocatorTarget = "file" | "package" | "dex" | "error" | "unknown";

/** 读 APK 包自身元数据的后端（core/locators.py 的 `APK_READER`）。 */
export const APK_READER = "apk-reader";

/** 读 DEX 符号图的后端（core/locators.py 的 `DEX_BACKEND`）。 */
export const DEX_BACKEND = "androguard";

/** 写出输出树的后端（core/locators.py 的 `OUTPUT_BACKENDS` 的键）。 */
export const OUTPUT_BACKENDS: readonly string[] = ["jadx", "apktool"];

/** 指向「后端没跑完」的前缀（core/locators.py 的 `ERROR_PREFIX`）。 */
export const ERROR_PREFIX = "error/";

export interface LocatorTargetInfo {
  /** 落点类别 */
  target: LocatorTarget;
  /** 是否指向一个可以打开的文件 */
  openable: boolean;
  /** 不能打开时的中文说明（`openable` 为真时没有） */
  note?: string;
}

/**
 * 判断一个 locator 指向哪一类落点。
 *
 * 规则与后端 `parse_locator` 同序：先看工具是不是 `apk-reader`，再看位置是不是
 * `error/` 开头，最后才落到「输出树里的文件」。
 */
export function classifyLocator(locator: string): LocatorTargetInfo {
  const trimmed = locator.trim();
  if (trimmed === "") {
    return {
      target: "unknown",
      openable: false,
      note: "没有来源定位：这个证据没有记录可打开的来源位置。",
    };
  }

  const separator = trimmed.indexOf(":");
  if (separator <= 0) {
    return {
      target: "unknown",
      openable: false,
      note: "未知来源：没有可打开的文件 —— 这个 locator 不是「工具:位置」的形状，后端不认。",
    };
  }

  const tool = trimmed.slice(0, separator);
  const place = trimmed.slice(separator + 1);

  if (tool === APK_READER) {
    return {
      target: "package",
      openable: false,
      note:
        "包级来源：没有单文件落点 —— 这个 locator 指向 APK 包本身（大小、哈希、DEX 清单），不是包内某个文件。",
    };
  }

  if (tool === DEX_BACKEND) {
    return {
      target: "dex",
      openable: false,
      note:
        "DEX 内位置：没有单文件落点 —— 这个 locator 指向 APK 字节码里的符号，不是可打开的文件。",
    };
  }

  if (!OUTPUT_BACKENDS.includes(tool)) {
    return {
      target: "unknown",
      openable: false,
      note: "未知来源：没有可打开的文件 —— 后端不认这个 locator 的工具前缀。",
    };
  }

  if (place.startsWith(ERROR_PREFIX)) {
    return {
      target: "error",
      openable: false,
      note: "后端未完成：没有可打开的文件 —— 这个 locator 指向的就是「后端没跑完」这个事实。",
    };
  }

  return { target: "file", openable: true };
}

/** 后端 `/locators/resolve` 的回答里，前端用得上的部分。 */
export interface LocatorResolutionLike {
  resolved: boolean;
  reason: string;
  kind: string | null;
}

export interface OpenSourceState {
  /** 「打开来源」按钮是否可用 */
  openable: boolean;
  /** 不可用时的中文说明（可用时没有） */
  note?: string;
}

/**
 * 「打开来源」按钮的状态。
 *
 * locator 说的是「指向哪一类落点」，后端解析说的是「那个地方在不在这次分析里」。
 * 两个都听：locator 就没有单文件落点时按钮直接不可用；问过后端之后，后端的回答
 * 说了算（它说文件不在，就不该留一个点了没反应的按钮）。
 */
export function openSourceState(
  locator: string,
  resolution?: LocatorResolutionLike | null,
): OpenSourceState {
  const info = classifyLocator(locator);
  if (!info.openable) return { openable: false, note: info.note };
  if (!resolution) return { openable: true };

  if (!resolution.resolved) {
    return {
      openable: false,
      note: `后端说这个来源不在这次分析里：${resolution.reason}`,
    };
  }
  if (!resolution.kind) {
    return {
      openable: false,
      note: `后端解析成功，但没有单文件落点：${resolution.reason}`,
    };
  }
  return { openable: true };
}

// ---------------------------------------------------------------------------
// 「打开来源」的内联源码视图
// ---------------------------------------------------------------------------

/** 后端 UntrustedText（schemas.py:43）—— resolve 响应里源码所在的那层。 */
export interface UntrustedTextLike {
  text: string;
  truncated?: boolean;
  bytes?: number;
  notice?: string;
}

/** {@link inlineSourceOf} 的输入：`/locators/resolve` 的完整响应。 */
export interface LocatorResolutionFull extends LocatorResolutionLike {
  text?: UntrustedTextLike | null;
  provenance?: string[];
}

/** 抽屉内联展示的一份源码，以及它自带的可核对信息。 */
export interface InlineSourceView {
  /** 后端解析出的真实文件路径（成功时 reason 就是它） */
  path: string;
  /** 文件的表示：java 或 smali */
  kind: string;
  /** 源码本身（后端已截到 ≤200 行 / 64 KB） */
  code: string;
  /** 展示的行数 */
  lines: number;
  /** 字节数的人类可读形式（截断前的大小） */
  bytesLabel: string;
  /** 后端是否截断了这段源码 */
  truncated: boolean;
  /** 后端随文本一起给的数据声明（UntrustedText.notice） */
  notice?: string;
}

/**
 * 从 `/locators/resolve` 的响应里取「能内联展示的源码」。
 *
 * 后端（`src/dexatlas/mcp/tools/evidence.py` 的 `resolve_locator`）在 locator
 * 解析到输出树里的一个文件时，`reason` 就是解析出的真实路径，`text` 携带
 * 源码、字节数与截断标记——不需要新端点。解析失败、解析到的不是单文件
 * （DEX 内符号、包级事实）时返回 null：那几种情况抽屉照旧展示状态面板。
 */
export function inlineSourceOf(resolution: LocatorResolutionFull | null): InlineSourceView | null {
  if (!resolution?.resolved || !resolution.kind || !resolution.text) return null;
  const code = resolution.text.text;
  const lines = code === "" ? 0 : (code.endsWith("\n") ? code.slice(0, -1) : code).split("\n").length;
  return {
    path: resolution.reason,
    kind: resolution.kind,
    code,
    lines,
    bytesLabel: formatBytes(resolution.text.bytes ?? 0),
    truncated: resolution.text.truncated ?? false,
    notice: resolution.text.notice,
  };
}

/** 字节数的人类可读形式：999 B → 1.0 KB → 64.0 KB → 1.0 MB。 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  let value = bytes;
  for (const unit of ["KB", "MB", "GB"]) {
    value /= 1024;
    if (value < 1024) return `${value.toFixed(1)} ${unit}`;
  }
  return `${(bytes / 1024 ** 4).toFixed(1)} TB`;
}
