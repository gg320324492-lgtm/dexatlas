/**
 * 设置页「关于」两行版本的单元测试。
 *
 * 装出来的缺陷（2026-11-27 真机复验）：设置页只有一条写着「版本」的行，
 * 填的是**后端**（分析核心）的版本号，而 MSI 里的 ProductVersion 是
 * 桌面应用自己的版本号——两个数各说各的，读者会把后端的号当成这个应用的
 * 版本。修法是分成两行，各说各的是谁。
 *
 * 这里测的是纯函数那一层：两行都在、标题说得清是谁的版本、拿不到时如实
 * 说拿不到（而不是显示一个编出来的号，或者干脆不显示）。
 */

import { describe, expect, it } from "vitest";
import { versionEntries } from "./settingsVersion";
import type { VersionEntry, VersionSubject } from "./settingsVersion";

/** 按「说的是谁」取那一行；少一行或多一行都在这里暴露。 */
function row(rows: VersionEntry[], subject: VersionSubject): VersionEntry {
  const found = rows.find((entry) => entry.subject === subject);
  if (!found) {
    throw new Error(`没有 subject=${subject} 的那一行`);
  }
  return found;
}

describe("versionEntries", () => {
  it("分成两行：应用版本与后端版本，各说各的", () => {
    const rows = versionEntries({
      appVersion: "1.2.0",
      backendVersion: "1.2.0",
      backendWorkspace: "C:/work",
    });

    expect(rows).toHaveLength(2);
    expect(row(rows, "app").version).toBe("1.2.0");
    expect(row(rows, "backend").version).toBe("1.2.0");
  });

  it("两行的标题互不包含：读者一眼能分出哪个是应用、哪个是后端", () => {
    const rows = versionEntries({ appVersion: "1.2.0", backendVersion: "1.1.0" });
    const app = row(rows, "app");
    const backend = row(rows, "backend");

    expect(app.label).toContain("应用");
    expect(backend.label).toContain("后端");
    // 两行不能有一行是光秃秃的「版本」——那正是缺陷本身。
    expect(app.label).not.toBe("版本");
    expect(backend.label).not.toBe("版本");
    expect(app.label).not.toBe(backend.label);
  });

  it("拿不到应用版本时如实说拿不到，不编一个号", () => {
    const rows = versionEntries({ appVersion: null, backendVersion: "1.2.0" });

    expect(row(rows, "app").version).toBeNull();
    expect(row(rows, "app").unavailable).toBeTruthy();
    expect(row(rows, "backend").version).toBe("1.2.0");
  });

  it("拿不到后端版本时把那一条的原因说清楚", () => {
    const rows = versionEntries({
      appVersion: "1.2.0",
      backendVersion: null,
      backendError: "503: 后端未启动",
    });

    expect(row(rows, "backend").version).toBeNull();
    expect(row(rows, "backend").unavailable).toContain("503");
    expect(row(rows, "app").version).toBe("1.2.0");
  });

  it("后端那行带上工作区路径，应用那行不带", () => {
    const rows = versionEntries({
      appVersion: "1.2.0",
      backendVersion: "1.2.0",
      backendWorkspace: "C:/work",
    });

    expect(row(rows, "backend").note).toContain("C:/work");
    expect(row(rows, "app").note).not.toContain("C:/work");
  });
});
