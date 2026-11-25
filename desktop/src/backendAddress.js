/**
 * 后端地址的如实提取 — 供错误文案引用**实际请求**的地址。
 *
 * 桌面应用连的是侧车的动态端口（Tauri 形态），端口由系统分配、每次启动
 * 都可能不同（见 docs/architecture/desktop-app.md §8.1）。所以任何写死的
 * "127.0.0.1:8618" 都可能在指着另一台机器上的另一个后端：8618 只是
 * 侧车端口拿不到时的**回退**地址，只有真的回退过去时它才是真的。
 *
 * 规则：地址只能来自客户端的 effective baseUrl。
 * - 绝对地址（侧车实际端口，或真的回退到 8618）→ 原样给出；
 * - 相对地址（dev 下由 vite 代理转发 "/api"）→ 端口在代理后面，前端无从
 *   得知，如实返回 null，由调用方说「后端地址未知」；
 * - 空值/非法地址 → null，同样不编一个。
 *
 * 纯函数、无依赖、不碰网络；写成普通 ESM 是为了能像 ../stages 一样被
 * tests/test_desktop_stale_copy.py 直接用 Node 执行（CI 的 Python job 不
 * 装 npm 依赖，Node 也早于 TypeScript 类型剥离）。
 */

/**
 * 从 API 基址里取出可以如实展示的后端地址。
 *
 * @param {string | null | undefined} baseUrl API 基址，例如
 *   "http://127.0.0.1:64074/api"（侧车实际端口）或 "/api"（dev 代理）
 * @returns {string | null} 可展示的后端地址；端口未知时为 null
 */
export function backendAddress(baseUrl) {
  if (typeof baseUrl !== "string") return null;
  const text = baseUrl.trim();
  if (!text) return null;
  // 相对地址（dev 的 vite 代理）：端口在代理后面，前端不知道。
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(text)) return null;
  /** @type {URL | null} */
  let url = null;
  try {
    url = new URL(text);
  } catch {
    return null;
  }
  if (!url || !url.hostname) return null;
  return `${url.protocol}//${url.host}`;
}
