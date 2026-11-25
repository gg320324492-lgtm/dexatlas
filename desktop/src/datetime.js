/**
 * 后端时间戳的显示 — 本地时区 + 可核对的 UTC 标注。
 *
 * 后端给的是 UTC 时刻的 ISO 串（`created_at` = `datetime.now(UTC).isoformat()`，
 * 例如 "2026-11-25T18:46:07.123456+00:00"，见 src/dexatlas/core/models.py:762
 * `anchor: created_at`）。旧的前端只取前 19 个字符直接显示，等于把 UTC 的
 * 墙上时间当成本地时间显示——打包 exe 二次验收在 UTC+8 的机器上读到的正是
 * 这一点：报告写着 18:46，实际是本地 02:46（次日）。
 *
 * 规则：
 * - 本地时间按运行机器的时区取值（getFullYear() 等本地取值器），并带上该
 *   时刻的 UTC 偏移量（getTimezoneOffset() 在该时刻取值，自动含夏令时）；
 * - 同时给出 UTC 时刻，读者在别的机器、别的时区上也能核对这行数字；
 * - 没有时区标注的输入按 UTC 解释：ECMAScript 把 "2026-11-25T18:46:07" 这
 *   种写法当成本地时间，后端给的一律是 UTC，不补 Z 会平白差一个时区；
 * - 解析不出来就返回 null，由调用方显示「时间未知」，不编一个时间。
 *
 * 纯函数、无依赖、不碰网络；写成普通 ESM 是为了能像 ../stages 一样被
 * tests/test_desktop_stale_copy.py 直接用 Node 执行（CI 的 Python job 不
 * 装 npm 依赖，Node 也早于 TypeScript 类型剥离）。
 */

/**
 * @typedef {{ y: number, m: number, d: number, hh: number, mm: number, ss: number }} WallClock
 * @typedef {{ local: string, utc: string, offset: string }} TimestampParts
 */

/** 结尾带 Z 或 ±HH:MM / ±HHMM 的，才算带了时区。 */
const HAS_TIME_ZONE = /(?:[Zz]|[+-]\d{2}:?\d{2})$/;

/**
 * 解析后端的 ISO 时间串。
 *
 * @param {string | null | undefined} iso
 * @returns {Date | null}
 */
function parseTimestamp(iso) {
  if (typeof iso !== "string") return null;
  const text = iso.trim();
  if (!text) return null;
  const hasTime = text.includes("T") || text.includes(" ");
  // 没带时区的时间一律按 UTC 解释（后端的钟就是 UTC）。
  const candidate = hasTime && !HAS_TIME_ZONE.test(text) ? `${text}Z` : text;
  const date = new Date(candidate);
  return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * @param {number} value
 * @returns {string}
 */
function pad2(value) {
  return String(value).padStart(2, "0");
}

/**
 * @param {WallClock} clock
 * @returns {string}
 */
function formatClock(clock) {
  return (
    `${clock.y}-${pad2(clock.m)}-${pad2(clock.d)} ` +
    `${pad2(clock.hh)}:${pad2(clock.mm)}:${pad2(clock.ss)}`
  );
}

/**
 * 该时刻的本地墙上时间。
 *
 * @param {Date} date
 * @returns {WallClock}
 */
function localClock(date) {
  return {
    y: date.getFullYear(),
    m: date.getMonth() + 1,
    d: date.getDate(),
    hh: date.getHours(),
    mm: date.getMinutes(),
    ss: date.getSeconds(),
  };
}

/**
 * @param {Date} date
 * @returns {WallClock}
 */
function utcClock(date) {
  return {
    y: date.getUTCFullYear(),
    m: date.getUTCMonth() + 1,
    d: date.getUTCDate(),
    hh: date.getUTCHours(),
    mm: date.getUTCMinutes(),
    ss: date.getUTCSeconds(),
  };
}

/**
 * 该时刻的 UTC 偏移量（本地相对 UTC 的分钟差取反）。
 *
 * @param {Date} date
 * @returns {string}
 */
function formatOffset(date) {
  const minutes = -date.getTimezoneOffset();
  const sign = minutes >= 0 ? "+" : "-";
  const absolute = Math.abs(minutes);
  return `UTC${sign}${pad2(Math.floor(absolute / 60))}:${pad2(absolute % 60)}`;
}

/**
 * 把后端的时间戳拆成本地时间、UTC 时间与偏移量三份。
 *
 * @param {string | null | undefined} iso 后端给的 ISO 时间串
 * @returns {TimestampParts | null} 解析不出来时为 null
 */
export function timestampParts(iso) {
  const date = parseTimestamp(iso);
  if (!date) return null;
  return {
    local: formatClock(localClock(date)),
    utc: formatClock(utcClock(date)),
    offset: formatOffset(date),
  };
}
