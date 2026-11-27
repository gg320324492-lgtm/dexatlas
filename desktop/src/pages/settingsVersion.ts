/**
 * 设置页「关于」里的两行版本。
 *
 * 两个版本说的是两样东西，不能揉成一条「版本」：
 * - **应用版本**：这个桌面应用（exe / MSI 安装包）自己的版本号；
 * - **后端版本**：侧车分析核心（Python）的版本号。
 *
 * 之前的设置页只有一条写着「版本」，填的是后端的号——读者会以为那就是
 * 这个应用的版本，于是认错（见 docs/desktop-packaging.md）。
 *
 * 这里是纯函数：不碰 DOM、不发请求，所以能在 vitest 里直接测。
 */

/** 这一行说的是谁。 */
export type VersionSubject = "app" | "backend";

/** 一行版本信息。 */
export interface VersionEntry {
  subject: VersionSubject;
  /** 行的标题：必须说清是谁的版本。 */
  label: string;
  /** 版本号（不带 v 前缀）；null 表示这一行拿不到。 */
  version: string | null;
  /** 版本号旁边的补充说明。 */
  note: string | null;
  /** 拿不到版本号时给读者看的话；拿得到时是 null。 */
  unavailable: string | null;
}

/** 组装两行版本所需的输入。 */
export interface VersionEntryInput {
  /** 桌面应用自身的版本；拿不到时是 null。 */
  appVersion: string | null;
  /** 后端（分析核心）的版本；拿不到时是 null。 */
  backendVersion: string | null;
  /** 后端的工作区路径（后端那行的补充说明）。 */
  backendWorkspace?: string | null;
  /** 后端读取失败时的原因（后端那行如实显示）。 */
  backendError?: string | null;
}

/**
 * 组装「关于」里的两行版本。
 *
 * 两条永远都在：拿不到的那条显示拿不到，而不是不显示——空着会让读者
 * 以为这个产品没有版本号。
 */
export function versionEntries(input: VersionEntryInput): VersionEntry[] {
  const app = input.appVersion?.trim() ?? "";
  const backend = input.backendVersion?.trim() ?? "";
  const workspace = input.backendWorkspace?.trim() ?? "";
  const backendError = input.backendError?.trim() ?? "";

  return [
    {
      subject: "app",
      label: "应用版本",
      version: app || null,
      note: "桌面应用（exe 与 MSI 安装包）",
      unavailable: app ? null : "仅在桌面应用内可得",
    },
    {
      subject: "backend",
      label: "后端版本（分析核心）",
      version: backend || null,
      note: workspace ? `工作区 ${workspace}` : null,
      unavailable: backend ? null : backendError || "后端未响应",
    },
  ];
}
